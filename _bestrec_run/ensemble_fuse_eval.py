"""Full-system eval: z-score ensemble of N trained seq checkpoints + EASE.

PROVENANCE: ported 2026-07-22 from the R+ side campaign
(R+\\code\\ensemble_fuse_eval.py) for E-F (PREREG_HYBRID_V1); base import
switched to run_sasrec_sbert (model reconstruction via fuse_ease_eval).

    fused(u) = (1/N) * sum_i z(seq_i(u)) + w * z(ease(u))

- Each seq model contributes its per-user z-normalized full-catalog scores
  (equal weights; no per-model tuning).
- EASE fit on TRAIN only (l2 fixed from the single-hybrid val selection).
- The single fusion weight w is selected on the VALIDATION split only.
- Test is evaluated once at the selected w. Same masking/protocol as
  fuse_ease_eval.py (val: input=train; test: input=train+val).

Usage:
  python ensemble_fuse_eval.py run1.json run2.json ... [--ease-l2 100]
      [--fusion-weights ...] [--out out.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_sasrec_sbert as rsp
from fuse_ease_eval import build_model_from_config, ease_B

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def batch_inputs(batch_users, user_seqs, extra, user_times, xtimes, max_seq_len,
                 pad_id, use_times):
    Bn = len(batch_users)
    input_ids = torch.full((Bn, max_seq_len), pad_id, dtype=torch.long,
                           device=DEVICE)
    times_t = (torch.zeros((Bn, max_seq_len), dtype=torch.long, device=DEVICE)
               if use_times else None)
    train_items, real_len = [], []
    for k, u in enumerate(batch_users):
        seq = list(user_seqs.get(u, []))
        if u in extra:
            seq = seq + list(extra[u])
        train_items.append(seq)
        truncated = seq[-max_seq_len:]
        if truncated:
            input_ids[k, :len(truncated)] = torch.tensor(
                truncated, dtype=torch.long, device=DEVICE)
        if use_times:
            tms = list(user_times.get(u, []))
            if u in xtimes:
                tms = tms + list(xtimes[u])
            trunc_t = tms[-max_seq_len:]
            if trunc_t:
                times_t[k, :len(trunc_t)] = torch.tensor(
                    trunc_t, dtype=torch.long, device=DEVICE)
        real_len.append(len(truncated))
    return input_ids, times_t, train_items, real_len


def z(x):
    return (x - x.mean(dim=1, keepdim=True)) \
           / x.std(dim=1, keepdim=True).clamp_min(1e-8)


def seq_z_matrix(model, users, user_seqs, extra, user_times, xtimes,
                 max_seq_len, pad_id, n_items, batch_size=512):
    """(n_users_eval, n_items) float32 CPU matrix of per-user z-scores."""
    out = np.empty((len(users), n_items), dtype=np.float32)
    use_times = getattr(model, "use_time_bias", False) and user_times is not None
    with torch.no_grad():
        all_items = model.all_item_features()
        for s in range(0, len(users), batch_size):
            bu = users[s:s + batch_size]
            input_ids, times_t, train_items, real_len = batch_inputs(
                bu, user_seqs, extra, user_times, xtimes, max_seq_len, pad_id,
                use_times)
            hidden = model.encode(input_ids, times=times_t)
            Bn = len(bu)
            last_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                    device=DEVICE)
            last_h = hidden[torch.arange(Bn, device=DEVICE), last_pos, :]
            out[s:s + Bn] = z(last_h @ all_items.T).cpu().numpy()
    return out


def ease_z_matrix(B_gpu, users, user_seqs, extra, n_items, batch_size=1024):
    out = np.empty((len(users), n_items), dtype=np.float32)
    with torch.no_grad():
        for s in range(0, len(users), batch_size):
            bu = users[s:s + batch_size]
            Bn = len(bu)
            xu = torch.zeros((Bn, n_items), device=DEVICE)
            items_list = []
            for k, u in enumerate(bu):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                items_list.append(seq)
                if seq:
                    xu[k, torch.tensor(seq, dtype=torch.long, device=DEVICE)] = 1.0
            out[s:s + Bn] = z(xu @ B_gpu).cpu().numpy()
    return out


def rank_metrics(fused, users, user_seqs, extra, eval_dict, top_k=10):
    """fused: (n_users_eval, n_items) numpy. Mask history, rank targets."""
    ndcg = hr = rr = 0.0
    per_user = np.zeros(len(users), dtype=np.float32)
    for k, u in enumerate(users):
        row = fused[k]
        seq = list(user_seqs.get(u, []))
        if u in extra:
            seq = seq + list(extra[u])
        tgt = eval_dict[u]
        tgt_score = row[tgt]
        seen = np.asarray(seq, dtype=np.int64)
        # rank = strictly-better count, with history removed from contention
        r0 = int((row > tgt_score).sum()) - int((row[seen] > tgt_score).sum())
        if r0 < top_k:
            nd = 1.0 / math.log2(r0 + 2)
            ndcg += nd
            per_user[k] = nd
            hr += 1
        rr += 1.0 / (r0 + 1)
    n = len(users)
    return {"ndcg": ndcg / n, "hr": hr / n, "rr": rr / n}, per_user


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_jsons", nargs="+")
    ap.add_argument("--ease-l2", type=float, default=100.0)
    ap.add_argument("--fusion-weights", type=str,
                    default="0.0,0.01,0.02,0.03,0.04,0.05,0.075,0.1")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg0 = json.load(open(args.run_jsons[0]))["config"]
    category = cfg0["category"]
    max_seq_len = cfg0["max_seq_len"]
    print(f"=== ensemble fusion: {category}, {len(args.run_jsons)} seq models, "
          f"EASE l2={args.ease_l2} ===")

    train_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    valid_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    test_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = rsp.reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    user_seqs = rsp.build_user_sequences(train_inters)
    user_times = (rsp.build_user_time_sequences(train_inters)
                  if cfg0.get("time_bias") else None)
    val_extra, val_extra_times = {}, {}
    for u, i, _, t in valid_inters:
        val_extra.setdefault(u, []).append(i)
        val_extra_times.setdefault(u, []).append(t // 1000)
    val_dict = {u: i for u, i, _, _ in valid_inters}
    test_dict = {u: i for u, i, _, _ in test_inters}
    val_users = sorted(val_dict.keys())
    test_users = sorted(test_dict.keys())

    # Accumulate mean seq z-scores over models (load one model at a time).
    val_sum = np.zeros((len(val_users), n_items), dtype=np.float32)
    test_sum = np.zeros((len(test_users), n_items), dtype=np.float32)
    for rj in args.run_jsons:
        run = json.load(open(rj))
        cfg = run["config"]
        ckpt = torch.load(Path(rj).with_suffix(".best.pt"),
                          map_location="cpu", weights_only=False)
        proto_assign = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
        enc_cache = cfg.get("encoder_cache")
        sbert_npy = Path(enc_cache) if enc_cache else \
            rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
        sbert_emb = np.load(sbert_npy).astype(np.float32)[:n_items]
        model = build_model_from_config(cfg, n_items, pad_id, sbert_emb,
                                        proto_assign)
        model.load_state_dict(ckpt["state_dict"], strict=False)
        model.to(DEVICE).eval()
        t0 = time.time()
        val_sum += seq_z_matrix(model, val_users, user_seqs, {}, user_times, {},
                                max_seq_len, pad_id, n_items)
        test_sum += seq_z_matrix(model, test_users, user_seqs, val_extra,
                                 user_times, val_extra_times, max_seq_len,
                                 pad_id, n_items)
        print(f"  {Path(rj).stem}: ckpt epoch {ckpt['epoch']} "
              f"(val {ckpt['val_NDCG10']:.5f}) scored in {time.time()-t0:.0f}s")
        del model
        torch.cuda.empty_cache()
    val_sum /= len(args.run_jsons)
    test_sum /= len(args.run_jsons)

    _, B = ease_B(train_inters, n_users, n_items, args.ease_l2)
    B_gpu = torch.from_numpy(B).to(DEVICE)
    del B
    val_ease = ease_z_matrix(B_gpu, val_users, user_seqs, {}, n_items)
    test_ease = ease_z_matrix(B_gpu, test_users, user_seqs, val_extra, n_items)
    del B_gpu
    torch.cuda.empty_cache()

    weights = [float(w) for w in args.fusion_weights.split(",")]
    report = {"category": category, "runs": list(args.run_jsons),
              "ease_l2": args.ease_l2, "val": {}, "n_items": n_items}
    best = None
    for w in weights:
        m, _ = rank_metrics(val_sum + w * val_ease, val_users, user_seqs, {},
                            val_dict)
        report["val"][str(w)] = m
        print(f"  w={w}: VAL ensemble-fused NDCG@10={m['ndcg']:.5f}")
        if best is None or m["ndcg"] > best[0]:
            best = (m["ndcg"], w)
    val_ndcg, w_sel = best
    print(f"=== selected on VAL: w={w_sel} (val NDCG@10={val_ndcg:.5f}) ===")

    tm, per_user = rank_metrics(test_sum + w_sel * test_ease, test_users,
                                user_seqs, val_extra, test_dict)
    tm_seq, per_user_seq = rank_metrics(test_sum, test_users, user_seqs,
                                        val_extra, test_dict)
    print(f"TEST ensemble seq-only NDCG@10={tm_seq['ndcg']:.5f} "
          f"HR@10={tm_seq['hr']:.5f}")
    print(f"TEST ensemble+EASE (w={w_sel}) NDCG@10={tm['ndcg']:.5f} "
          f"HR@10={tm['hr']:.5f} MRR={tm['rr']:.5f}")
    report["selected_w"] = w_sel
    report["test"] = {"ensemble_seq_only": tm_seq, "ensemble_fused": tm,
                      "n_eval": len(test_users)}
    out = Path(args.out) if args.out else \
        Path(r"C:\Users\rayxc\Desktop\R+\runs\ensemble_fusion.json")
    json.dump(report, open(out, "w"), indent=1)
    np.savez_compressed(out.with_suffix(".perusers.npz"),
                        users=np.array(test_users, dtype=np.int64),
                        fused_ndcg=per_user,
                        ensemble_seq_ndcg=per_user_seq)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
