"""BERT4Rec (Sun et al., CIKM 2019) — bidirectional Transformer with
masked-item language modeling for sequential recommendation.

Different from SASRec:
  - Bidirectional attention (no causal mask) — each item sees full context
  - Training: mask 15% of items per sequence, predict masked items via
    cross-entropy over the catalog
  - Eval: append [MASK] token at the end of the training sequence,
    predict the masked item (the test target)

Why this might beat SASRec on Beauty_and_PC:
  - More gradient signal per user — each user contributes ~0.15*L training
    targets per epoch (vs SASRec's L-1 targets, but SASRec only has the
    autoregressive constraint that limits which positions can attend where).
  - The bidirectional context lets the model use both past and future
    items to predict the masked item, which is more informative for
    sparse-history users.

Uses the same chunked-full-softmax + subsampled-eval machinery as
run_sasrec_sbert.py. Targets the 0.019 NDCG@10 ceiling on Beauty_and_PC.

Usage:
    uv run python run_bert4rec.py Beauty_and_Personal_Care \\
        --epochs 25 --d-model 64 --n-layers 2 --n-heads 2 \\
        --mask-prob 0.15 --eval-every 5 --eval-subsample 10000
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
EMB_CACHE_DIR = ROOT / "cache_5core"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_split_csv(path):
    rows = []
    with path.open("r", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            rows.append((r["user_id"], r["parent_asin"],
                          float(r["rating"]), int(r["timestamp"])))
    return rows


def reindex(train_rows, valid_rows, test_rows):
    all_rows = train_rows + valid_rows + test_rows
    users = sorted({r[0] for r in all_rows})
    items = sorted({r[1] for r in all_rows})
    u2idx = {u: i for i, u in enumerate(users)}
    i2idx = {a: j for j, a in enumerate(items)}
    def cvt(rows):
        return [(u2idx[u], i2idx[a], r, t) for u, a, r, t in rows]
    return cvt(train_rows), cvt(valid_rows), cvt(test_rows), users, items


def build_user_sequences(train_inters):
    by_user = defaultdict(list)
    for u, i, _, t in train_inters:
        by_user[u].append((t, i))
    user_seqs = {}
    for u, lst in by_user.items():
        lst.sort()
        user_seqs[u] = [i for (_, i) in lst]
    return user_seqs


class BERT4RecDataset(Dataset):
    """Each example is a user sequence (right-padded). At training time we
    randomly mask `mask_prob` of the items; the model predicts the masked items."""
    def __init__(self, user_seqs, max_seq_len, n_items, pad_id, mask_id,
                  mask_prob=0.15):
        self.examples = []
        for u, seq in user_seqs.items():
            if len(seq) < 2:
                continue
            # Truncate to max_seq_len most recent
            self.examples.append((u, seq[-max_seq_len:]))
        self.max_seq_len = max_seq_len
        self.pad_id = pad_id
        self.mask_id = mask_id
        self.mask_prob = mask_prob
        self.n_items = n_items

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        u, seq = self.examples[idx]
        L = len(seq)
        pad_amount = self.max_seq_len - L
        input_ids = list(seq) + [self.pad_id] * pad_amount
        # Random masking
        target_ids = [self.pad_id] * self.max_seq_len  # pad_id means ignore in loss
        for k in range(L):
            if np.random.random() < self.mask_prob:
                target_ids[k] = input_ids[k]      # save original as target
                input_ids[k] = self.mask_id       # replace with [MASK]
        # Ensure at least 1 masked position (or model gets no gradient)
        n_masked = sum(1 for t in target_ids if t != self.pad_id)
        if n_masked == 0 and L > 0:
            k = int(np.random.randint(0, L))
            target_ids[k] = seq[k]
            input_ids[k] = self.mask_id
        return (torch.tensor(input_ids, dtype=torch.long),
                torch.tensor(target_ids, dtype=torch.long))


def collate_batch(batch):
    inputs = torch.stack([b[0] for b in batch])
    targets = torch.stack([b[1] for b in batch])
    return inputs, targets


class BERT4Rec(nn.Module):
    def __init__(self, n_items, pad_id, mask_id, max_seq_len, d_model=64,
                  n_layers=2, n_heads=2, dropout=0.2, sbert_emb=None):
        super().__init__()
        self.n_items = n_items
        self.pad_id = pad_id
        self.mask_id = mask_id
        self.d_model = d_model
        self.max_seq_len = max_seq_len

        # Item embedding: n_items + 2 (one for pad, one for [MASK])
        self.item_emb = nn.Embedding(n_items + 2, d_model, padding_idx=pad_id)
        nn.init.normal_(self.item_emb.weight, std=0.02)

        self.use_sbert = sbert_emb is not None
        if self.use_sbert:
            sbert_dim = sbert_emb.shape[1]
            sbert_with_pad = np.zeros((n_items + 2, sbert_dim), dtype=np.float32)
            sbert_with_pad[:n_items] = sbert_emb
            self.sbert_table = nn.Embedding.from_pretrained(
                torch.from_numpy(sbert_with_pad), freeze=True, padding_idx=pad_id)
            self.sbert_proj = nn.Linear(sbert_dim, d_model, bias=False)

        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        nn.init.normal_(self.pos_emb.weight, std=0.02)
        self.drop = nn.Dropout(dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=4 * d_model,
            dropout=dropout, activation="gelu", batch_first=True, norm_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.ln_final = nn.LayerNorm(d_model)

    def item_features(self, item_ids):
        e = self.item_emb(item_ids)
        if self.use_sbert:
            s = self.sbert_table(item_ids)
            e = e + self.sbert_proj(s)
        return e

    def all_item_features(self):
        ids = torch.arange(self.n_items, device=self.item_emb.weight.device)
        return self.item_features(ids)

    def encode(self, input_ids):
        """No causal mask — bidirectional attention."""
        B, L = input_ids.shape
        device = input_ids.device
        x = self.item_features(input_ids)
        positions = torch.arange(L, device=device).unsqueeze(0).expand(B, L)
        x = x + self.pos_emb(positions)
        x = self.drop(x)
        # NO causal mask — BERT-style bidirectional
        h = self.transformer(x)
        h = self.ln_final(h)
        return h


def train_one_epoch(model, loader, opt, pad_id, device, grad_clip=5.0,
                      item_chunk=32768):
    """Cross-entropy over masked positions with chunked full softmax."""
    model.train()
    total_loss = 0.0
    n_batches = 0
    for inputs, targets in loader:
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        hidden = model.encode(inputs)
        B, L, d = hidden.shape
        valid = (targets != pad_id)
        n_valid = valid.sum().item()
        if n_valid == 0:
            continue
        h_v = hidden[valid]                       # (n_valid, d)
        pos_ids = targets[valid]                  # (n_valid,)

        # Chunked full softmax: compute log-sum-exp incrementally over item chunks
        n_items = model.n_items
        pos_emb = model.item_features(pos_ids)
        pos_logits = (h_v * pos_emb).sum(dim=-1)  # (n_valid,)

        # max-logit running max + log-sum-exp
        max_logit = torch.full((n_valid,), float("-inf"), device=device)
        sum_exp = torch.zeros((n_valid,), device=device)
        for s in range(0, n_items, item_chunk):
            e = min(s + item_chunk, n_items)
            chunk_ids = torch.arange(s, e, device=device)
            chunk_emb = model.item_features(chunk_ids)  # (chunk_size, d)
            chunk_logits = h_v @ chunk_emb.T            # (n_valid, chunk_size)
            chunk_max = chunk_logits.max(dim=1).values
            new_max = torch.maximum(max_logit, chunk_max)
            sum_exp = sum_exp * torch.exp(max_logit - new_max) \
                     + torch.exp(chunk_logits - new_max.unsqueeze(1)).sum(dim=1)
            max_logit = new_max
        log_sum_exp = max_logit + torch.log(sum_exp + 1e-20)
        loss = (log_sum_exp - pos_logits).mean()

        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        opt.step()
        total_loss += loss.item()
        n_batches += 1
    return total_loss / max(1, n_batches)


def evaluate(model, user_seqs, test_inters, n_items, pad_id, mask_id,
              max_seq_len, device, top_k=10, batch_size=256,
              extra_history=None, subsample_users=0, subsample_seed=0):
    """For each (u, target): build u's training sequence (+ optional val item),
    append [MASK] at the end, predict it. Score against all items, mask train+val."""
    model.eval()
    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    if subsample_users and subsample_users < len(users):
        rng = np.random.RandomState(subsample_seed)
        users = sorted(rng.choice(users, subsample_users, replace=False).tolist())
    extra = extra_history or {}
    n_eval = len(users)
    ndcg, hr, rr = [], [], []
    print(f"  evaluating {n_eval:,} users in batches of {batch_size}...")
    t0 = time.time()
    with torch.no_grad():
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            input_ids = torch.full((len(batch_users), max_seq_len), pad_id,
                                     dtype=torch.long, device=device)
            train_items = []
            for u in batch_users:
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                train_items.append(seq)
            mask_pos_per_user = []
            for k, items in enumerate(train_items):
                if not items:
                    mask_pos_per_user.append(0); continue
                truncated = items[-(max_seq_len - 1):]  # leave room for [MASK]
                input_ids[k, :len(truncated)] = torch.tensor(truncated,
                                                                dtype=torch.long,
                                                                device=device)
                input_ids[k, len(truncated)] = mask_id
                mask_pos_per_user.append(len(truncated))
            hidden = model.encode(input_ids)
            B = len(batch_users)
            mask_pos = torch.tensor(mask_pos_per_user, device=device)
            mask_h = hidden[torch.arange(B, device=device), mask_pos, :]
            all_items = model.all_item_features()
            final = mask_h @ all_items.T
            if torch.isnan(final).any():
                raise RuntimeError(f"NaN logits at batch starting {s}")
            for k, items in enumerate(train_items):
                if items:
                    final[k, items] = -float("inf")
            for k, u in enumerate(batch_users):
                tgt = test_dict[u]
                tgt_score = final[k, tgt].item()
                rank0 = int((final[k] > tgt_score).sum().item())
                if rank0 < top_k:
                    ndcg.append(1.0 / math.log2(rank0 + 2))
                    hr.append(1.0)
                else:
                    ndcg.append(0.0); hr.append(0.0)
                rr.append(1.0 / (rank0 + 1))
            if (s // batch_size) % 20 == 0:
                print(f"    [{s + len(batch_users):,}/{n_eval:,}  elapsed {time.time()-t0:.1f}s]")
    print(f"  eval done in {time.time()-t0:.1f}s")
    return {
        "NDCG@10": float(np.mean(ndcg)),
        "HR@10":   float(np.mean(hr)),
        "MRR":     float(np.mean(rr)),
        "n_eval":  len(users),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("category")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-seq-len", type=int, default=50)
    ap.add_argument("--d-model", type=int, default=64)
    ap.add_argument("--n-layers", type=int, default=2)
    ap.add_argument("--n-heads", type=int, default=2)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--mask-prob", type=float, default=0.15)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--no-sbert", action="store_true")
    ap.add_argument("--item-chunk", type=int, default=32768)
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--eval-subsample", type=int, default=10000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_path = Path(args.out) if args.out else (Path(__file__).parent /
                                                  f"results_bert4rec_{args.category}.json")
    train_csv = SPLIT_DIR / f"{args.category}.train.csv"
    valid_csv = SPLIT_DIR / f"{args.category}.valid.csv"
    test_csv = SPLIT_DIR / f"{args.category}.test.csv"
    sbert_npy = EMB_CACHE_DIR / f"sbert_titles_{args.category}.npy"

    print(f"=== {args.category}: load splits ===")
    train_rows = load_split_csv(train_csv)
    valid_rows = load_split_csv(valid_csv)
    test_rows = load_split_csv(test_csv)
    train_inters, valid_inters, test_inters, user_list, item_list = reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    mask_id = n_items + 1
    print(f"  n_users={n_users:,}  n_items={n_items:,}  pad_id={pad_id}  mask_id={mask_id}")

    user_seqs = build_user_sequences(train_inters)
    print(f"  built sequences for {len(user_seqs):,} users")

    sbert_emb = None
    if not args.no_sbert:
        print(f"  loading SBERT from {sbert_npy}...")
        sbert_emb = np.load(sbert_npy).astype(np.float32)

    print(f"\n=== BERT4Rec (d={args.d_model}, layers={args.n_layers}, heads={args.n_heads}, mask_prob={args.mask_prob}) ===")
    model = BERT4Rec(n_items=n_items, pad_id=pad_id, mask_id=mask_id,
                       max_seq_len=args.max_seq_len,
                       d_model=args.d_model, n_layers=args.n_layers,
                       n_heads=args.n_heads, dropout=args.dropout,
                       sbert_emb=sbert_emb).to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  total params: {n_params:,}  device={DEVICE}")

    dataset = BERT4RecDataset(user_seqs, args.max_seq_len, n_items, pad_id,
                                mask_id, mask_prob=args.mask_prob)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                          num_workers=0, collate_fn=collate_batch, drop_last=False)
    print(f"  {len(dataset):,} training examples / {len(loader):,} batches per epoch")
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)

    best_val_ndcg = 0.0
    best_test_metrics = None
    history = []
    print(f"\n=== Train for {args.epochs} epochs ===")
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss = train_one_epoch(model, loader, opt, pad_id, DEVICE,
                                        item_chunk=args.item_chunk)
        ep_time = time.time() - t0
        log = {"epoch": epoch, "train_loss": train_loss, "epoch_time_s": ep_time}
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            subs = args.eval_subsample if epoch < args.epochs else 0
            val_metrics = evaluate(model, user_seqs, valid_inters, n_items,
                                     pad_id, mask_id, args.max_seq_len, DEVICE,
                                     subsample_users=subs)
            valid_dict = {u: i for u, i, _, _ in valid_inters}
            test_extra = {u: [i] for u, i in valid_dict.items()}
            test_metrics = evaluate(model, user_seqs, test_inters, n_items,
                                      pad_id, mask_id, args.max_seq_len, DEVICE,
                                      extra_history=test_extra,
                                      subsample_users=subs)
            log["val"] = val_metrics
            log["test"] = test_metrics
            print(f"  epoch {epoch:>3d}  loss={train_loss:.4f}  val_NDCG={val_metrics['NDCG@10']:.4f}  "
                  f"test_NDCG={test_metrics['NDCG@10']:.4f}  test_HR={test_metrics['HR@10']:.4f}  "
                  f"({ep_time:.1f}s)")
            if val_metrics["NDCG@10"] > best_val_ndcg:
                best_val_ndcg = val_metrics["NDCG@10"]
                best_test_metrics = test_metrics
        else:
            print(f"  epoch {epoch:>3d}  loss={train_loss:.4f}  ({ep_time:.1f}s)")
        history.append(log)

    print(f"\n=== Best by val NDCG@10 ===")
    print(f"  val_NDCG={best_val_ndcg:.4f}")
    if best_test_metrics:
        print(f"  test: {best_test_metrics}")

    out = {
        "category": args.category, "config": vars(args),
        "n_users": n_users, "n_items": n_items, "n_params": n_params,
        "history": history,
        "best_val_NDCG10": best_val_ndcg,
        "best_test": best_test_metrics,
    }
    with out_path.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
