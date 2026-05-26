"""SASRec-SBERT: SBERT-augmented sequential recommender.

Goal: compete with TIGER/LIGER/BLaIR on the standard Amazon Reviews 2023
5-core leave-last-out benchmark. Our closed-form ease_sbert was 23-70% below
those published methods on Video_Games (NDCG@10 0.034 vs TIGER 0.042 / LIGER
0.053). The gap is autoregressive sequence modelling; closed-form bag-of-items
methods plateau when n_items > ~10K and the temporal signal becomes large.

Architecture (SASRec + SBERT, ~simple-as-possible):
  - Item embedding: learned[d_model] + SBERT-projection (384 -> d_model)
                    summed; the SBERT branch lets cold items get a sensible
                    initialisation from their text alone.
  - Positional embedding: learned, max_seq_len=50.
  - Transformer encoder: n_layers=2 layers, n_heads=2, d_ff=4*d_model, GELU.
  - Causal mask (autoregressive next-item prediction).
  - Output: dot product with full item-embedding table (shared with input).
  - Loss: cross-entropy with full softmax (n_items <= 50K so full softmax fits
          on GPU comfortably).
  - Optimiser: Adam lr=1e-3, weight_decay=1e-5, gradient clip 5.
  - Dropout=0.2 on input embeddings and attention.

Training data construction:
  - Each user's training sequence (sorted chronologically). For each
    position 1..L-1, predict the item at that position from the prefix.
  - We use the standard "left-to-right" prefix prediction, not BERT-style
    masking (SASRec, not BERT4Rec).

Evaluation:
  - Same leave-last-out protocol as in run_5core_benchmark.py.
  - For each user: build their training sequence, run the encoder, get the
    final hidden state, score every item via dot product, mask training items,
    rank the test item, compute NDCG@10/HR@10/MRR.

Usage:
    uv run python run_sasrec_sbert.py Video_Games --epochs 30
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


def load_split_csv(path: Path) -> list[tuple]:
    rows = []
    with path.open("r", encoding="utf-8") as fp:
        rdr = csv.DictReader(fp)
        for r in rdr:
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
    """For each user, return their training items sorted by timestamp."""
    by_user = defaultdict(list)
    for u, i, _, t in train_inters:
        by_user[u].append((t, i))
    user_seqs = {}
    for u, lst in by_user.items():
        lst.sort()
        user_seqs[u] = [i for (_, i) in lst]
    return user_seqs


class SASRecDataset(Dataset):
    """For each user with seq [i1, i2, ..., iL], emits one training example
    with RIGHT-padding (standard SASRec convention):
      input  = [i1, i2, ..., i_{L-1}, pad ... pad]  (length max_seq_len)
      target = [i2, i3, ..., iL,       pad ... pad]  (length max_seq_len)
    Loss only counts positions where target != pad.
    Right-padding + causal mask (no key padding mask) avoids the NaN-trap.

    augment_factor: number of training examples per user per epoch. If > 1,
    additional examples use random subsequence starting positions, giving the
    model multiple "views" of the same user history per epoch.
    """
    def __init__(self, user_seqs, max_seq_len, n_items, pad_id, augment_factor=1):
        self.examples = []
        self.max_seq_len = max_seq_len
        self.pad_id = pad_id
        self.n_items = n_items
        self.augment_factor = augment_factor
        for u, seq in user_seqs.items():
            if len(seq) < 2:
                continue
            for _ in range(augment_factor):
                self.examples.append((u, seq))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        u, seq = self.examples[idx]
        # If augmentation enabled, pick a random subsequence end position.
        # The subsequence is seq[start:end+1] with end uniformly in [1, L-1].
        if self.augment_factor > 1 and len(seq) > 2:
            end = np.random.randint(1, len(seq))
            sub = seq[:end + 1]
        else:
            sub = seq
        # Truncate to most-recent max_seq_len+1 items
        if len(sub) > self.max_seq_len + 1:
            sub = sub[-(self.max_seq_len + 1):]
        input_ids = sub[:-1]
        target_ids = sub[1:]
        # Right-pad
        L = len(input_ids)
        pad_amount = self.max_seq_len - L
        input_ids = input_ids + [self.pad_id] * pad_amount
        target_ids = target_ids + [self.pad_id] * pad_amount
        return (torch.tensor(input_ids, dtype=torch.long),
                torch.tensor(target_ids, dtype=torch.long))


def collate_batch(batch):
    inputs = torch.stack([b[0] for b in batch])
    targets = torch.stack([b[1] for b in batch])
    return inputs, targets


class SASRecSBERT(nn.Module):
    def __init__(self, n_items, pad_id, max_seq_len, d_model=64, n_layers=2,
                  n_heads=2, dropout=0.2, sbert_emb=None):
        super().__init__()
        self.n_items = n_items
        self.pad_id = pad_id
        self.d_model = d_model
        self.max_seq_len = max_seq_len

        # Item embedding (learned). pad_id has its own slot.
        self.item_emb = nn.Embedding(n_items + 1, d_model, padding_idx=pad_id)
        nn.init.normal_(self.item_emb.weight, std=0.02)

        # SBERT projection (frozen embeddings, learned projection)
        self.use_sbert = sbert_emb is not None
        if self.use_sbert:
            sbert_dim = sbert_emb.shape[1]
            # Frozen SBERT, including a zero row for the pad slot
            sbert_with_pad = np.zeros((n_items + 1, sbert_dim), dtype=np.float32)
            sbert_with_pad[:n_items] = sbert_emb
            self.sbert_table = nn.Embedding.from_pretrained(
                torch.from_numpy(sbert_with_pad), freeze=True, padding_idx=pad_id)
            self.sbert_proj = nn.Linear(sbert_dim, d_model, bias=False)

        # Position embedding (learned)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        nn.init.normal_(self.pos_emb.weight, std=0.02)
        self.drop = nn.Dropout(dropout)

        # Transformer encoder (causal mask applied manually in forward)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=4 * d_model,
            dropout=dropout, activation="gelu", batch_first=True, norm_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.ln_final = nn.LayerNorm(d_model)

        # Output projection: tied to item_emb + optional SBERT bridge
        # We compute logits as hidden @ item_emb.T (full softmax over catalog).

    def item_features(self, item_ids):
        """Combine learned item embedding with frozen SBERT projection."""
        e = self.item_emb(item_ids)                     # (..., d_model)
        if self.use_sbert:
            s = self.sbert_table(item_ids)              # (..., sbert_dim)
            e = e + self.sbert_proj(s)
        return e

    def all_item_features(self):
        """(n_items, d_model) item-embedding table for scoring."""
        ids = torch.arange(self.n_items, device=self.item_emb.weight.device)
        return self.item_features(ids)

    def encode(self, input_ids):
        """Encode an input sequence into hidden states (no item-scoring).
        Returns (B, L, d_model). Useful for sampled-softmax training."""
        B, L = input_ids.shape
        device = input_ids.device

        x = self.item_features(input_ids)                # (B, L, d)
        positions = torch.arange(L, device=device).unsqueeze(0).expand(B, L)
        x = x + self.pos_emb(positions)
        x = self.drop(x)

        causal_mask = torch.triu(torch.ones(L, L, dtype=torch.bool, device=device), diagonal=1)
        h = self.transformer(x, mask=causal_mask)
        h = self.ln_final(h)                             # (B, L, d)
        return h

    def forward(self, input_ids):
        """input_ids: (B, L). Returns logits (B, L, n_items).
        Uses causal mask only (no key padding mask). Right-padded sequences
        keep the standard SASRec convention; pad positions still get computed
        but their outputs are masked-out by ignore_index in cross-entropy."""
        h = self.encode(input_ids)
        all_items = self.all_item_features()             # (n_items, d)
        logits = h @ all_items.T                         # (B, L, n_items)
        return logits


def train_one_epoch(model, loader, opt, pad_id, device, grad_clip=5.0,
                      sampled_negs: int = 0, in_batch_negs: bool = False):
    """Training loss modes (in priority order):
      - in_batch_negs=True: use all items in the batch as negatives per
        position (12K+ negs per step at batch=256, much more than sampled-1024;
        free compute since batch items are already in memory).
      - sampled_negs > 0: sampled softmax with K random negatives.
      - default: full softmax over all n_items."""
    model.train()
    total_loss = 0.0
    n_batches = 0
    n_valid_positions = 0
    for inputs, targets in loader:
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        if in_batch_negs:
            # In-batch negative sampling: all target items in this batch
            # act as negatives. Each position gets ~n_unique_items_in_batch
            # negatives (typically 5K-12K at batch=256, seq=50). The
            # softmax denominator is over: pos + all other batch items.
            hidden = model.encode(inputs)                # (B, L, d)
            B, L, d = hidden.shape
            valid = (targets != pad_id)                   # (B, L)
            n_valid = valid.sum().item()
            if n_valid == 0:
                continue
            # Flatten valid positions
            h_v = hidden[valid]                           # (n_valid, d)
            pos_ids = targets[valid]                      # (n_valid,)
            # Unique candidate item set: all target items (positives + neg pool)
            uniq_items, inv = torch.unique(pos_ids, return_inverse=True)  # (n_uniq,), (n_valid,)
            uniq_emb = model.item_features(uniq_items)    # (n_uniq, d)
            logits = h_v @ uniq_emb.T                     # (n_valid, n_uniq)
            # target = position of each (now in compact uniq space)
            loss = F.cross_entropy(logits, inv, reduction="mean")
        elif sampled_negs == 0:
            # Full softmax
            logits = model(inputs)                       # (B, L, n_items)
            B, L, n_items = logits.shape
            loss = F.cross_entropy(logits.reshape(B * L, n_items),
                                     targets.reshape(B * L),
                                     ignore_index=pad_id,
                                     reduction="mean")
        else:
            # Sampled softmax: produce hidden states, sample K negatives,
            # compute cross-entropy over (1 positive + K negatives)
            hidden = model.encode(inputs)                # (B, L, d)
            B, L, d = hidden.shape
            # Valid positions are where target != pad
            valid = (targets != pad_id)
            n_valid = valid.sum().item()
            if n_valid == 0:
                continue
            # Sample K random items per valid position
            sampled = torch.randint(0, model.n_items, (n_valid, sampled_negs),
                                     device=device)
            # Pos item ids + sampled neg ids
            h_v = hidden[valid]                          # (n_valid, d)
            pos_ids = targets[valid]                     # (n_valid,)
            cand_ids = torch.cat([pos_ids.unsqueeze(1), sampled], dim=1)  # (n_valid, 1 + K)
            cand_emb = model.item_features(cand_ids)     # (n_valid, 1+K, d)
            logits = (cand_emb @ h_v.unsqueeze(-1)).squeeze(-1)  # (n_valid, 1+K)
            # Cross-entropy with target=0 (first column is positive)
            target = torch.zeros(n_valid, dtype=torch.long, device=device)
            loss = F.cross_entropy(logits, target, reduction="mean")

        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        opt.step()
        total_loss += loss.item()
        n_batches += 1
        n_valid_positions += (targets != pad_id).sum().item()
    return total_loss / max(1, n_batches), n_valid_positions


def evaluate(model, user_seqs, test_inters, n_items, pad_id, max_seq_len,
              device, top_k=10, batch_size=512, extra_history=None):
    """For each (u, target) in test_inters, encode u's training sequence and
    score the target item against all items. Mask training items. Compute
    NDCG@K, HR@K, MRR.

    Right-padding convention: real items are placed at positions 0..L-1, then
    pad at positions L..max_seq_len-1. The 'next-item prediction' is taken
    from position L-1 (the last REAL item).

    extra_history: optional dict {user_id: [extra_item_ids]} appended to the
    user's training sequence in chronological order. Used for test eval where
    the val item is included in the input."""
    model.eval()
    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    n_eval = len(users)
    extra = extra_history or {}
    ndcg, hr, rr = [], [], []
    print(f"  evaluating {n_eval:,} users in batches of {batch_size}...")
    t0 = time.time()
    with torch.no_grad():
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            # Right-padded inputs (train + optional extra_history)
            input_ids = torch.full((len(batch_users), max_seq_len), pad_id,
                                     dtype=torch.long, device=device)
            train_items = []
            for u in batch_users:
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                train_items.append(seq)
            real_len = []
            for k, items in enumerate(train_items):
                if not items:
                    real_len.append(0); continue
                truncated = items[-max_seq_len:]
                input_ids[k, :len(truncated)] = torch.tensor(truncated,
                                                                dtype=torch.long,
                                                                device=device)
                real_len.append(len(truncated))
            # Memory-efficient: compute hidden states then score ONLY the
            # last real position against all items. Avoids materializing the
            # full (B, L, n_items) logits tensor — critical for n_items >> 50K.
            hidden = model.encode(input_ids)             # (B, L, d)
            B = len(batch_users)
            last_real_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                          device=device)
            last_h = hidden[torch.arange(B, device=device), last_real_pos, :]  # (B, d)
            all_items = model.all_item_features()        # (n_items, d)
            final = last_h @ all_items.T                 # (B, n_items)

            # Sanity: detect NaN (should never happen now)
            if torch.isnan(final).any():
                raise RuntimeError(f"NaN logits at batch starting {s}; check architecture.")

            # Mask the user's full input history (train + any extras like val)
            # — train_items above already concatenates them.
            for k, items in enumerate(train_items):
                if items:
                    final[k, items] = -float("inf")
            # Rank the target
            for k, u in enumerate(batch_users):
                if real_len[k] == 0:
                    # No training history — skip (shouldn't happen with 5-core)
                    ndcg.append(0.0); hr.append(0.0); rr.append(0.0); continue
                tgt = test_dict[u]
                tgt_score = final[k, tgt].item()
                rank0 = int((final[k] > tgt_score).sum().item())
                if rank0 < top_k:
                    ndcg.append(1.0 / math.log2(rank0 + 2))
                    hr.append(1.0)
                else:
                    ndcg.append(0.0); hr.append(0.0)
                rr.append(1.0 / (rank0 + 1))
            if (s // batch_size) % 10 == 0:
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
    ap.add_argument("category", help="Category (Video_Games, Beauty_and_Personal_Care, ...)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-seq-len", type=int, default=50)
    ap.add_argument("--d-model", type=int, default=64)
    ap.add_argument("--n-layers", type=int, default=2)
    ap.add_argument("--n-heads", type=int, default=2)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--no-sbert", action="store_true", help="Disable SBERT augmentation")
    ap.add_argument("--encoder-cache", default=None,
                     help="Override the default sbert_titles_<cat>.npy cache "
                          "path (e.g. cache_5core/blair_titles_<cat>.npy for BLaIR).")
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--sampled-negs", type=int, default=0,
                     help="If >0, use sampled softmax with this many negatives "
                          "per position (avoids OOM when n_items is huge). "
                          "0 = full softmax over all n_items.")
    ap.add_argument("--in-batch-negs", action="store_true",
                     help="Use all batch items as negatives per position "
                          "(much denser gradient than --sampled-negs at no extra cost). "
                          "Overrides --sampled-negs.")
    ap.add_argument("--augment-factor", type=int, default=1,
                     help="Number of random subsequences sampled per user per epoch "
                          "(1 = original SASRec, 2-5 = standard augmentation). "
                          "Each subsequence has start position uniformly sampled within "
                          "the user's history.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_path = Path(args.out) if args.out else (Path(__file__).parent /
                                                  f"results_sasrec_sbert_{args.category}.json")

    train_csv = SPLIT_DIR / f"{args.category}.train.csv"
    valid_csv = SPLIT_DIR / f"{args.category}.valid.csv"
    test_csv = SPLIT_DIR / f"{args.category}.test.csv"
    sbert_npy = (Path(args.encoder_cache) if args.encoder_cache
                  else EMB_CACHE_DIR / f"sbert_titles_{args.category}.npy")
    for p in (train_csv, valid_csv, test_csv):
        if not p.exists():
            print(f"ERROR: {p} missing")
            return 2
    if not args.no_sbert and not sbert_npy.exists():
        print(f"ERROR: SBERT cache {sbert_npy} missing. Run run_5core_benchmark.py --encode-titles first.")
        return 2

    print(f"=== {args.category}: load splits ===")
    train_rows = load_split_csv(train_csv)
    valid_rows = load_split_csv(valid_csv)
    test_rows = load_split_csv(test_csv)
    train_inters, valid_inters, test_inters, user_list, item_list = reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    print(f"  n_users={n_users:,}  n_items={n_items:,}  pad_id={pad_id}")

    # Build user training sequences
    user_seqs = build_user_sequences(train_inters)
    print(f"  built sequences for {len(user_seqs):,} users")

    # Load SBERT embeddings (aligned with item_list order from reindex())
    sbert_emb = None
    if not args.no_sbert:
        print(f"  loading SBERT embeddings from {sbert_npy}...")
        sbert_emb = np.load(sbert_npy).astype(np.float32)
        if sbert_emb.shape[0] != n_items:
            print(f"  WARN: SBERT cache has {sbert_emb.shape[0]} items but split has {n_items}; aligning by index")
            sbert_emb = sbert_emb[:n_items]

    # Build SASRec model
    print(f"\n=== Build SASRec-SBERT (d={args.d_model}, layers={args.n_layers}, heads={args.n_heads}) ===")
    model = SASRecSBERT(n_items=n_items, pad_id=pad_id,
                         max_seq_len=args.max_seq_len,
                         d_model=args.d_model, n_layers=args.n_layers,
                         n_heads=args.n_heads, dropout=args.dropout,
                         sbert_emb=sbert_emb).to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  total params: {n_params:,}  device={DEVICE}")

    # DataLoader
    dataset = SASRecDataset(user_seqs, args.max_seq_len, n_items, pad_id,
                              augment_factor=args.augment_factor)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                          num_workers=0, collate_fn=collate_batch, drop_last=False)
    print(f"  {len(dataset):,} training examples / {len(loader):,} batches per epoch")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)

    # Train
    print(f"\n=== Train for {args.epochs} epochs ===")
    best_val_ndcg = 0.0
    best_test_metrics = None
    history = []
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss, n_pos = train_one_epoch(model, loader, opt, pad_id, DEVICE,
                                              sampled_negs=args.sampled_negs,
                                              in_batch_negs=args.in_batch_negs)
        ep_time = time.time() - t0
        log = {"epoch": epoch, "train_loss": train_loss, "epoch_time_s": ep_time}
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            val_metrics = evaluate(model, user_seqs, valid_inters, n_items, pad_id,
                                     args.max_seq_len, DEVICE)
            # For test eval: standard SASRec/TIGER convention is to include
            # the val item in the input sequence so test predicts the
            # immediate-next item (matching what the model was trained on).
            valid_dict = {u: i for u, i, _, _ in valid_inters}
            test_extra = {u: [i] for u, i in valid_dict.items()}
            test_metrics = evaluate(model, user_seqs, test_inters, n_items, pad_id,
                                      args.max_seq_len, DEVICE, extra_history=test_extra)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
