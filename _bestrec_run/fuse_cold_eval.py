# -*- coding: utf-8 -*-
"""E-G STAGE-1 EXPLORATORY: cold/sparse third scorer for the fusion system.

Maintainer directive 2026-07-23: add an element targeting the cold-start /
sparse-data problem; on evidence of improvement, verify on all full datasets.

Element: a training-free text-kNN scorer over the frozen MiniLM item
embeddings -- score_text(u, i) = profile(u) . e_i with profile(u) a
(uniform or recency-decayed) mean of the user's input-history embeddings,
rows L2-normalized. It needs NO item-item inversion (scales to every
catalog) and scores items with near-zero training exposure, exactly where
the sequential model and EASE are weakest. Fused per user:

    fused = z(seq) + w_e * z(ease) + w_t(bin) * z(text)

with w_t either global or per TRAIN-frequency bin (tail <=5 / mid 6-20 /
head >20; never test frequency), constrained monotone nonincreasing in
frequency. All selection on the VALIDATION split only; test evaluated once
per reported system. EXPLORATORY LABEL: this stage is post-hoc development
on E-F checkpoints; nothing here is claim-bearing (promotion to a frozen
pre-registration is governed by the rule in EXPERIMENT_PROGRAM.md E-G).

Usage:
  python fuse_cold_eval.py <base_run.json> [--fusion-json f] [--out o]
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_sasrec_sbert as rsp
from fuse_ease_eval import build_model_from_config, ease_B
from ensemble_fuse_eval import seq_z_matrix, ease_z_matrix

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TAIL_MAX = 5
MID_MAX = 20
WE_GRID = (0.0, 0.02, 0.03, 0.04, 0.06)
WT_GRID = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2)
NONINF = 0.0002          # overall non-inferiority slack vs fused2 (val)


def text_z_matrix(users, user_seqs, extra, E_gpu, n_items, decay=None,
                  batch=2048):
    """(n_users, n_items) z-scored text-kNN scores. profile = (decayed) mean
    of history embeddings; score = profile @ E^T."""
    out = np.empty((len(users), n_items), dtype=np.float32)
    d = E_gpu.shape[1]
    with torch.no_grad():
        for s in range(0, len(users), batch):
            bu = users[s:s + batch]
            P = torch.zeros((len(bu), d), device=DEVICE)
            for k, u in enumerate(bu):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                if not seq:
                    continue
                idx = torch.tensor(seq, dtype=torch.long, device=DEVICE)
                V = E_gpu[idx]
                if decay is None:
                    P[k] = V.mean(dim=0)
                else:
                    w = torch.pow(torch.tensor(decay, device=DEVICE),
                                  torch.arange(len(seq) - 1, -1, -1,
                                               device=DEVICE, dtype=torch.float))
                    P[k] = (V * (w / w.sum()).unsqueeze(1)).sum(dim=0)
            S = P @ E_gpu.T
            mu = S.mean(dim=1, keepdim=True)
            sd = S.std(dim=1, keepdim=True).clamp_min(1e-8)
            out[s:s + len(bu)] = ((S - mu) / sd).cpu().numpy()
    return out


def rank_by_bin(F, users, user_seqs, extra, eval_dict, bin_idx, chunk=4096):
    """Overall + per-target-bin NDCG@10/HR@10 with input-history masking via
    the strictly-better-count subtraction (no -inf materialization)."""
    n = len(users)
    nd = np.zeros(n, dtype=np.float32)
    hit = np.zeros(n, dtype=np.float32)
    tbin = np.zeros(n, dtype=np.int64)
    tgt_all = np.fromiter((eval_dict[u] for u in users), dtype=np.int64,
                          count=n)
    for s in range(0, n, chunk):
        e = min(s + chunk, n)
        M = F[s:e]
        tgt = tgt_all[s:e]
        ts = M[np.arange(e - s), tgt]
        base = (M > ts[:, None]).sum(axis=1)
        for k in range(e - s):
            u = users[s + k]
            seq = list(user_seqs.get(u, []))
            if u in extra:
                seq = seq + list(extra[u])
            r0 = int(base[k])
            if seq:
                seen = np.asarray(seq, dtype=np.int64)
                r0 -= int((M[k, seen] > ts[k]).sum())
            if r0 < 10:
                nd[s + k] = 1.0 / math.log2(r0 + 2)
                hit[s + k] = 1.0
            tbin[s + k] = bin_idx[tgt[k]]
    res = {"ndcg": float(nd.mean()), "hr": float(hit.mean()), "n": n}
    for b, name in ((0, "tail"), (1, "mid"), (2, "head")):
        m = tbin == b
        res[name] = {"ndcg": float(nd[m].mean()) if m.any() else None,
                     "n": int(m.sum())}
    return res, nd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--fusion-json", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    run = json.load(open(args.run_json, encoding="utf-8"))
    cfg = run["config"]
    category = cfg["category"]
    fusion_json = args.fusion_json or args.run_json[:-5] + ".fusion.json"
    fus = json.load(open(fusion_json, encoding="utf-8"))
    l2_star = float(fus["selected"]["l2"])
    we_star = float(fus["selected"]["w"])
    print(f"=== E-G exploratory cold-fusion: {category} seed {cfg['seed']} "
          f"(fused2 ref l2={l2_star}, w={we_star}) ===")

    train_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    valid_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    test_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = rsp.reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    user_seqs = rsp.build_user_sequences(train_inters)
    user_times = (rsp.build_user_time_sequences(train_inters)
                  if cfg.get("time_bias") else None)
    val_extra, val_extra_times = {}, {}
    for u, i, _, t in valid_inters:
        val_extra.setdefault(u, []).append(i)
        val_extra_times.setdefault(u, []).append(t // 1000)
    val_dict = {u: i for u, i, _, _ in valid_inters}
    test_dict = {u: i for u, i, _, _ in test_inters}
    val_users = sorted(val_dict.keys())
    test_users = sorted(test_dict.keys())

    freq = np.zeros(n_items, dtype=np.int64)
    for _, i, _, _ in train_inters:
        freq[i] += 1
    bin_idx = np.where(freq <= TAIL_MAX, 0,
                       np.where(freq <= MID_MAX, 1, 2))
    print(f"  train-freq bins: tail(<= {TAIL_MAX}) {int((bin_idx == 0).sum()):,} "
          f"items (freq==0: {int((freq == 0).sum()):,}), "
          f"mid {int((bin_idx == 1).sum()):,}, head {int((bin_idx == 2).sum()):,}")

    enc_cache = cfg.get("encoder_cache")
    sbert_npy = Path(enc_cache) if enc_cache else \
        rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    E = np.load(sbert_npy).astype(np.float32)[:n_items]
    norms = np.linalg.norm(E, axis=1, keepdims=True)
    E = E / np.clip(norms, 1e-8, None)
    E_gpu = torch.from_numpy(E).to(DEVICE)

    ckpt = torch.load(Path(args.run_json).with_suffix(".best.pt"),
                      map_location="cpu", weights_only=False)
    proto_assign = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
    sbert_emb = np.load(sbert_npy).astype(np.float32)[:n_items]
    model = build_model_from_config(cfg, n_items, pad_id, sbert_emb,
                                    proto_assign)
    model.load_state_dict(ckpt["state_dict"], strict=False)
    model.to(DEVICE).eval()

    t0 = time.time()
    print("  [val] seq z-matrix ...")
    zs = seq_z_matrix(model, val_users, user_seqs, {}, user_times, {},
                      cfg["max_seq_len"], pad_id, n_items)
    print(f"  [val] ease z-matrix (l2={l2_star}) ...")
    _, B = ease_B(train_inters, n_users, n_items, l2_star)
    B_gpu = torch.from_numpy(B).to(DEVICE)
    del B
    ze = ease_z_matrix(B_gpu, val_users, user_seqs, {}, n_items)

    ref_val, _ = rank_by_bin(zs + we_star * ze, val_users, user_seqs, {},
                             val_dict, bin_idx)
    print(f"  fused2 VAL: overall {ref_val['ndcg']:.5f} "
          f"tail {ref_val['tail']['ndcg']:.5f} (n={ref_val['tail']['n']:,})")

    report = {"exploratory": True, "category": category, "seed": cfg["seed"],
              "run_json": str(args.run_json), "fused2": {"l2": l2_star,
              "w": we_star, "val": ref_val},
              "bins": {"tail_max": TAIL_MAX, "mid_max": MID_MAX},
              "sweep_global": [], "sweep_binned": []}

    best_global = None      # (val_tail, combo, val_res) under non-inferiority
    best_overall = None
    for decay in (None, 0.9):
        pname = "uniform" if decay is None else f"exp{decay}"
        print(f"  [val] text z-matrix ({pname}) ...")
        zt = text_z_matrix(val_users, user_seqs, {}, E_gpu, n_items,
                           decay=decay)
        for we in sorted(set(WE_GRID) | {we_star}):
            base_m = zs + we * ze
            for wt in WT_GRID:
                r, _ = rank_by_bin(base_m + wt * zt, val_users, user_seqs,
                                   {}, val_dict, bin_idx)
                combo = {"profile": pname, "we": we, "wt": wt}
                report["sweep_global"].append({**combo, "val": r})
                if best_overall is None or r["ndcg"] > best_overall[0]:
                    best_overall = (r["ndcg"], combo, r)
                if (r["ndcg"] >= ref_val["ndcg"] - NONINF
                        and (best_global is None
                             or r["tail"]["ndcg"] > best_global[0])):
                    best_global = (r["tail"]["ndcg"], combo, r)
        del zt
    print(f"  global sweep done ({time.time()-t0:.0f}s). "
          f"tail-best under non-inferiority: {best_global[1]} "
          f"tail {best_global[0]:.5f}")

    # binned refinement around the tail-best profile/we
    pname = best_global[1]["profile"]
    decay = None if pname == "uniform" else 0.9
    we = best_global[1]["we"]
    zt = text_z_matrix(val_users, user_seqs, {}, E_gpu, n_items, decay=decay)
    base_m = zs + we * ze
    wt_item = np.empty(n_items, dtype=np.float32)
    best_binned = None
    for wt_t in WT_GRID:
        for wt_m in WT_GRID:
            if wt_m > wt_t:
                continue
            for wt_h in WT_GRID:
                if wt_h > wt_m:
                    continue
                wt_item[bin_idx == 0] = wt_t
                wt_item[bin_idx == 1] = wt_m
                wt_item[bin_idx == 2] = wt_h
                r, _ = rank_by_bin(base_m + zt * wt_item[None, :], val_users,
                                   user_seqs, {}, val_dict, bin_idx)
                combo = {"profile": pname, "we": we, "wt_tail": wt_t,
                         "wt_mid": wt_m, "wt_head": wt_h}
                report["sweep_binned"].append({**combo, "val": r})
                if (r["ndcg"] >= ref_val["ndcg"] - NONINF
                        and (best_binned is None
                             or r["tail"]["ndcg"] > best_binned[0])):
                    best_binned = (r["tail"]["ndcg"], combo, r)
    del zs, ze, zt
    print(f"  binned sweep done. tail-best: {best_binned[1]} "
          f"tail {best_binned[0]:.5f}")
    report["selected_global"] = {"combo": best_global[1],
                                 "val": best_global[2]}
    report["selected_binned"] = {"combo": best_binned[1],
                                 "val": best_binned[2]}
    report["val_overall_best"] = {"combo": best_overall[1],
                                  "val": best_overall[2]}

    # ---- single TEST evaluation per reported system ----
    print("  [test] building matrices ...")
    zs = seq_z_matrix(model, test_users, user_seqs, val_extra, user_times,
                      val_extra_times, cfg["max_seq_len"], pad_id, n_items)
    ze = ease_z_matrix(B_gpu, test_users, user_seqs, val_extra, n_items)
    del B_gpu
    torch.cuda.empty_cache()
    out_npz = {}
    r_seq, nd_seq = rank_by_bin(zs, test_users, user_seqs, val_extra,
                                test_dict, bin_idx)
    r_f2, nd_f2 = rank_by_bin(zs + we_star * ze, test_users, user_seqs,
                              val_extra, test_dict, bin_idx)
    report["test_seq_only"] = r_seq
    report["test_fused2"] = r_f2
    out_npz["seq_ndcg"] = nd_seq
    out_npz["fused2_ndcg"] = nd_f2
    for label, sel in (("global", report["selected_global"]),
                       ("binned", report["selected_binned"])):
        c = sel["combo"]
        decay = None if c["profile"] == "uniform" else 0.9
        zt = text_z_matrix(test_users, user_seqs, val_extra, E_gpu, n_items,
                           decay=decay)
        if label == "global":
            F = zs + c["we"] * ze + c["wt"] * zt
        else:
            wt_item[bin_idx == 0] = c["wt_tail"]
            wt_item[bin_idx == 1] = c["wt_mid"]
            wt_item[bin_idx == 2] = c["wt_head"]
            F = zs + c["we"] * ze + zt * wt_item[None, :]
        r, nd = rank_by_bin(F, test_users, user_seqs, val_extra, test_dict,
                            bin_idx)
        report[f"test_fused3_{label}"] = r
        out_npz[f"fused3_{label}_ndcg"] = nd
        del zt, F
        print(f"  TEST fused3-{label}: overall {r['ndcg']:.5f} "
              f"(fused2 {r_f2['ndcg']:.5f}) tail {r['tail']['ndcg']:.5f} "
              f"(fused2 tail {r_f2['tail']['ndcg']:.5f})")

    out = Path(args.out) if args.out else \
        Path(args.run_json).with_name(
            f"results_{category}_COLDFUSE_explore_seed{cfg['seed']}.json")
    tbin = np.array([bin_idx[test_dict[u]] for u in test_users],
                    dtype=np.int64)
    np.savez_compressed(str(out)[:-5] + ".perusers.npz",
                        users=np.array(test_users, dtype=np.int64),
                        target_bin=tbin, **out_npz)
    json.dump(report, open(out, "w", encoding="utf-8"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
