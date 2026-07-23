"""Hybrid score fusion: sequential HSTU-style model + closed-form EASE.

PROVENANCE: ported 2026-07-22 from the R+ side campaign
(R+\\code\\fuse_ease_eval.py, author-operated environment) for E-F
(PREREG_HYBRID_V1). Changes vs the R+ original: base module import switched
to this repo's run_sasrec_sbert; R+-only architecture kwargs dropped from
build_model_from_config; fir_v3 passthrough added. EASE is Steck (2019) --
bib entry required at any paper-integration commit (H9 enforces).

Algorithm (R+ campaign, 2026-07-22):
  1. Load a trained best-val checkpoint of the sequential model (run_seqrec_plus
     --save-ckpt) and reproduce its full-catalog masked eval scores.
  2. Fit EASE (Steck 2019, "Embarrassingly Shallow Autoencoders") on the SAME
     5-core TRAIN split only (binary user-item matrix; closed form
     B = I - P diag(1/diag(P)), P = (X^T X + l2 I)^{-1}, diag(B) = 0).
  3. Late-fuse per user with per-user z-normalized scores:
         fused = z(seq) + w * z(ease)
     (l2, w) are selected on the VALIDATION split only; the test metric is
     reported once at the selected pair. Leak-free:
       - EASE consults train interactions only.
       - Test-time user vector includes train+val items (input-side history,
         the standard SASRec test convention already used by the base model).
       - No test label is consulted for any tuning decision.

Attribution: EASE is Steck (2019); z-score late fusion is standard; the
contribution here is the hybrid of the paper's HSTU-style text-augmented
sequential model with a closed-form item-item linear model under the
5-core LLOO full-catalog protocol.

Usage:
  python fuse_ease_eval.py <run.json> [--ckpt path] [--ease-l2 50,100,200,500]
      [--fusion-weights 0:1:0.05] [--out out.json]
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

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def build_model_from_config(cfg, n_items, pad_id, sbert_emb, proto_assign):
    return rsp.SASRecSBERT(
        n_items=n_items, pad_id=pad_id,
        max_seq_len=cfg["max_seq_len"], d_model=cfg["d_model"],
        n_layers=cfg["n_layers"], n_heads=cfg["n_heads"],
        dropout=cfg["dropout"], sbert_emb=sbert_emb,
        sbert_only=cfg.get("sbert_only", False),
        mlp_adaptor=cfg.get("mlp_adaptor", False),
        mlp_hidden=cfg.get("mlp_hidden", 300),
        mlp_dropout=cfg.get("mlp_dropout", 0.2),
        time_bias=cfg.get("time_bias", False),
        text_sim_bias=cfg.get("text_sim_bias", False),
        proto_assign=proto_assign,
        encoder=cfg.get("encoder", "transformer"),
        pos_rab=cfg.get("pos_rab", False),
        time_decay_kernel=cfg.get("time_decay_kernel", False),
        time_decay_bases=cfg.get("time_decay_bases", 8),
        n_experts=cfg.get("expert_heads", 0),
        causal_filter=cfg.get("causal_filter", False),
        filter_kernel=cfg.get("filter_kernel", 50),
        causal_filter_fixed_avg=cfg.get("filter_fixed_avg", False),
        causal_filter_no_gate=cfg.get("filter_no_gate", False),
        fir_v3=cfg.get("fir_v3", "off"),
        fir_v3_kernel=cfg.get("fir_v3_kernel", 16),
    )


def ease_B(train_inters, n_users, n_items, l2):
    """Closed-form EASE item-item weight matrix (float64 CPU solve).

    VERIFIED CACHE (audit 2026-07-23 15:59 optimization, adopted): keyed by
    SHA-256 of the exact (rows, cols) interaction arrays + n_items + l2; the
    stored matrix's own digest is verified on load. Identical inputs ->
    identical matrix, ~70s saved per repeat fit."""
    import hashlib
    import scipy.sparse as sp
    rows = np.fromiter((u for (u, _, _, _) in train_inters), dtype=np.int64,
                       count=len(train_inters))
    cols = np.fromiter((i for (_, i, _, _) in train_inters), dtype=np.int64,
                       count=len(train_inters))
    X = sp.csr_matrix((np.ones(len(rows), dtype=np.float64), (rows, cols)),
                      shape=(n_users, n_items))
    h = hashlib.sha256()
    h.update(rows.tobytes())
    h.update(cols.tobytes())
    h.update(f"|{n_users}|{n_items}|{float(l2)}|f32v1".encode())
    key = h.hexdigest()[:24]
    cdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "ease_cache")
    os.makedirs(cdir, exist_ok=True)
    bpath = os.path.join(cdir, f"ease_{key}.npy")
    mpath = os.path.join(cdir, f"ease_{key}.meta.json")
    if os.path.exists(bpath) and os.path.exists(mpath):
        meta = json.load(open(mpath, encoding="utf-8"))
        bh = hashlib.sha256(open(bpath, "rb").read()).hexdigest()
        if (meta.get("input_key") == key and meta.get("b_sha256") == bh
                and meta.get("n_items") == n_items):
            B = np.load(bpath)
            print(f"  EASE l2={l2}: verified cache hit ({key})")
            return X, B
        print(f"  EASE l2={l2}: cache verification FAILED ({key}); refitting")
    G = np.asarray((X.T @ X).todense(), dtype=np.float64)
    G[np.diag_indices(n_items)] += l2
    t0 = time.time()
    P = np.linalg.inv(G)
    print(f"  EASE l2={l2}: inverted {n_items}x{n_items} in {time.time()-t0:.1f}s")
    B = -P / np.diag(P)[None, :]          # B_ij = -P_ij / P_jj
    B[np.diag_indices(n_items)] = 0.0
    B = B.astype(np.float32)
    tmp = bpath + ".tmp"
    np.save(tmp, B)
    os.replace(tmp + ".npy" if os.path.exists(tmp + ".npy") else tmp, bpath)
    json.dump({"input_key": key, "n_items": n_items, "l2": float(l2),
               "b_sha256": hashlib.sha256(open(bpath, "rb").read()).hexdigest()},
              open(mpath, "w", encoding="utf-8"))
    return X, B


def fused_eval(model, user_seqs, eval_inters, n_items, pad_id, max_seq_len,
               B_gpu, weights, extra_history=None, user_times=None,
               extra_times=None, batch_size=512, top_k=10):
    """Evaluate seq-only, ease-only, and fused (per w in weights) NDCG@10/HR/MRR.
    Mirrors run_seqrec_plus.evaluate() input construction exactly."""
    model.eval()
    test_dict = {u: i for u, i, _, _ in eval_inters}
    users = sorted(test_dict.keys())
    n_eval = len(users)
    extra = extra_history or {}
    xtimes = extra_times or {}
    use_times = getattr(model, "use_time_bias", False) and user_times is not None
    res = {w: {"ndcg": 0.0, "hr": 0.0, "rr": 0.0} for w in weights}
    res["seq"] = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0}
    res["ease"] = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0}
    per_user = {}          # key -> [ndcg@10 per user, in `users` order]
    t0 = time.time()
    with torch.no_grad():
        all_items = model.all_item_features()
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            Bn = len(batch_users)
            input_ids = torch.full((Bn, max_seq_len), pad_id, dtype=torch.long,
                                   device=DEVICE)
            times_t = (torch.zeros((Bn, max_seq_len), dtype=torch.long,
                                   device=DEVICE) if use_times else None)
            train_items = []
            real_len = []
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
            hidden = model.encode(input_ids, times=times_t)
            last_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                    device=DEVICE)
            last_h = hidden[torch.arange(Bn, device=DEVICE), last_pos, :]
            seq_scores = last_h @ all_items.T                     # (B, n_items)

            # EASE scores: x_u @ B, x_u = binary over the SAME input history
            xu = torch.zeros((Bn, n_items), device=DEVICE)
            for k, items in enumerate(train_items):
                if items:
                    xu[k, torch.tensor(items, dtype=torch.long,
                                       device=DEVICE)] = 1.0
            ease_scores = xu @ B_gpu                              # (B, n_items)

            def z(x):
                return (x - x.mean(dim=1, keepdim=True)) \
                       / x.std(dim=1, keepdim=True).clamp_min(1e-8)
            zs, ze = z(seq_scores), z(ease_scores)

            # Mask input history in every scorer
            for k, items in enumerate(train_items):
                if items:
                    idx = torch.tensor(items, dtype=torch.long, device=DEVICE)
                    zs[k, idx] = -float("inf")
                    ze[k, idx] = -float("inf")

            tgt = torch.tensor([test_dict[u] for u in batch_users],
                               dtype=torch.long, device=DEVICE)
            ar = torch.arange(Bn, device=DEVICE)

            def accumulate(key, scores):
                ts = scores[ar, tgt]
                rank0 = (scores > ts.unsqueeze(1)).sum(dim=1)      # (B,)
                hit = rank0 < top_k
                nd = torch.where(hit, 1.0 / torch.log2(rank0.float() + 2.0),
                                 torch.zeros_like(rank0, dtype=torch.float))
                res[key]["ndcg"] += float(nd.sum())
                res[key]["hr"] += float(hit.sum())
                res[key]["rr"] += float((1.0 / (rank0.float() + 1.0)).sum())
                per_user.setdefault(key, []).extend(
                    nd.cpu().numpy().tolist())

            accumulate("seq", zs)
            accumulate("ease", ze)
            for w in weights:
                accumulate(w, zs + w * ze)
            if (s // batch_size) % 20 == 0:
                print(f"    [{s + Bn:,}/{n_eval:,} elapsed {time.time()-t0:.1f}s]")
    for key in res:
        for m in res[key]:
            res[key][m] /= n_eval
    return res, n_eval, per_user, users


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--ease-l2", type=str, default="50,100,200,500")
    ap.add_argument("--fusion-weights", type=str,
                    default="0.1,0.2,0.3,0.4,0.5,0.6,0.8,1.0,1.5,2.0")
    ap.add_argument("--out", default=None)
    ap.add_argument("--val-only", action="store_true",
                    help="E-G2 sequestration: run the validation sweep and "
                         "record the selected (l2, w) WITHOUT any test pass; "
                         "the frozen confirmatory evaluator scores test once.")
    args = ap.parse_args()

    run = json.load(open(args.run_json))
    cfg = run["config"]
    category = cfg["category"]
    ckpt_path = Path(args.ckpt) if args.ckpt else \
        Path(args.run_json).with_suffix(".best.pt")
    print(f"=== fusion eval: {category}  ckpt={ckpt_path.name} ===")

    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])

    train_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    valid_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    test_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = rsp.reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    print(f"  n_users={n_users:,} n_items={n_items:,}")

    user_seqs = rsp.build_user_sequences(train_inters)
    user_times = (rsp.build_user_time_sequences(train_inters)
                  if cfg.get("time_bias") else None)
    # Val item appended for the test pass (standard convention, as in main()).
    val_extra = {}
    val_extra_times = {}
    for u, i, _, t in valid_inters:
        val_extra.setdefault(u, []).append(i)
        val_extra_times.setdefault(u, []).append(t // 1000)

    enc_cache = cfg.get("encoder_cache")
    sbert_npy = Path(enc_cache) if enc_cache else \
        rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    sbert_emb = np.load(sbert_npy).astype(np.float32)[:n_items]

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto_assign = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, n_items, pad_id, sbert_emb, proto_assign)
    missing, unexpected = model.load_state_dict(ckpt["state_dict"], strict=False)
    unexpected = [k for k in unexpected if not k.startswith("proto_assign")]
    missing = [k for k in missing
               if not (k.startswith("sbert_table") or k.startswith("proto_assign")
                       or k in ("time_boundaries",))]
    if missing or unexpected:
        print(f"  WARN state_dict mismatch: missing={missing} unexpected={unexpected}")
    model.to(DEVICE).eval()
    print(f"  ckpt from epoch {ckpt['epoch']} (val NDCG@10 {ckpt['val_NDCG10']:.5f})")

    weights = [float(w) for w in args.fusion_weights.split(",")]
    l2_list = [float(x) for x in args.ease_l2.split(",")]

    report = {"category": category, "run_json": str(args.run_json),
              "ckpt_epoch": ckpt["epoch"], "l2_sweep": {}, "n_items": n_items,
              "recorded_best_test": run.get("best_test")}
    best = None            # (val_fused_ndcg, l2, w)
    B_cache = {}
    for l2 in l2_list:
        print(f"\n--- EASE l2={l2}: fit + VAL sweep ---")
        _, B = ease_B(train_inters, n_users, n_items, l2)
        B_gpu = torch.from_numpy(B).to(DEVICE)
        del B
        val_res, n_val, _, _ = fused_eval(model, user_seqs, valid_inters, n_items,
                                          pad_id, cfg["max_seq_len"], B_gpu, weights,
                                          extra_history=None, user_times=user_times)
        entry = {"val_seq": val_res["seq"], "val_ease": val_res["ease"],
                 "val_fused": {str(w): val_res[w] for w in weights}}
        report["l2_sweep"][str(l2)] = entry
        print(f"  VAL seq NDCG@10={val_res['seq']['ndcg']:.5f}  "
              f"ease={val_res['ease']['ndcg']:.5f}")
        for w in weights:
            print(f"    w={w}: val fused NDCG@10={val_res[w]['ndcg']:.5f}")
            if best is None or val_res[w]["ndcg"] > best[0]:
                best = (val_res[w]["ndcg"], l2, w)
        del B_gpu
        torch.cuda.empty_cache()

    val_ndcg, l2_sel, w_sel = best
    print(f"\n=== selected on VAL: l2={l2_sel}, w={w_sel} "
          f"(val fused NDCG@10={val_ndcg:.5f}) ===")
    if args.val_only:
        report["selected"] = {"l2": l2_sel, "w": w_sel,
                              "val_fused_ndcg": val_ndcg}
        report["test"] = None
        report["val_only"] = True
        out = Path(args.out) if args.out else \
            Path(args.run_json).with_name(Path(args.run_json).stem
                                          + ".fusion.json")
        json.dump(report, open(out, "w"), indent=1)
        print(f"wrote {out} (VAL-ONLY; test sequestered)")
        return
    _, B_sel = ease_B(train_inters, n_users, n_items, l2_sel)
    B_gpu = torch.from_numpy(B_sel).to(DEVICE)
    del B_sel
    test_res, n_test, per_user, users_order = fused_eval(
        model, user_seqs, test_inters, n_items,
        pad_id, cfg["max_seq_len"], B_gpu, [w_sel],
        extra_history=val_extra, user_times=user_times,
        extra_times=val_extra_times)
    # Per-user paired records (seq vs fused) for Wilcoxon-style significance.
    np.savez_compressed(
        Path(args.run_json).with_suffix(".fusion_perusers.npz"),
        users=np.array(users_order, dtype=np.int64),
        seq_ndcg=np.array(per_user["seq"], dtype=np.float32),
        fused_ndcg=np.array(per_user[w_sel], dtype=np.float32),
        ease_ndcg=np.array(per_user["ease"], dtype=np.float32))
    print(f"\nTEST seq-only  NDCG@10={test_res['seq']['ndcg']:.5f} "
          f"HR@10={test_res['seq']['hr']:.5f} MRR={test_res['seq']['rr']:.5f}")
    print(f"TEST ease-only NDCG@10={test_res['ease']['ndcg']:.5f} "
          f"HR@10={test_res['ease']['hr']:.5f}")
    print(f"TEST FUSED (w={w_sel}) NDCG@10={test_res[w_sel]['ndcg']:.5f} "
          f"HR@10={test_res[w_sel]['hr']:.5f} MRR={test_res[w_sel]['rr']:.5f}")
    report["selected"] = {"l2": l2_sel, "w": w_sel, "val_fused_ndcg": val_ndcg}
    report["test"] = {"seq_only": test_res["seq"], "ease_only": test_res["ease"],
                      "fused": test_res[w_sel], "n_eval": n_test}

    out = Path(args.out) if args.out else \
        Path(args.run_json).with_name(Path(args.run_json).stem + ".fusion.json")
    json.dump(report, open(out, "w"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
