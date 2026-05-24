"""Helper to dump per-pair JSONL records for the CDR_validated baseline.

``run_poc_cdr_books.py`` evaluates CDR_validated but only saves per-fold means;
to do per-USER paired Wilcoxon vs CDR-CL we need per-pair records on the same
splits/seeds. This script reproduces that algorithm and writes JSONL with the
same schema as ``results_cdr_cl_records_<dataset>.jsonl``.

Important: this is the EXACT CDR_validated algorithm — alpha selected on inner
20% item validation, blended z-normalised CD + Ridge LC2C. The only addition is
saving per-pair records.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from sklearn.linear_model import Ridge

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex

CDR_ALPHA_GRID = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0]
SEED = 20260521


def load_dataset(dataset):
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], DATASET_KCORE[dataset])
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{DATASET_KCORE[dataset]}_dedup.pt"
    emb = torch.load(title_path, weights_only=True)
    return interactions, n_users, n_items, emb


def build_warm(train_inters, n_users, warm_indices):
    pos = {int(it): i for i, it in enumerate(warm_indices)}
    rows, cols = [], []
    for x in train_inters:
        p = pos.get(int(x["item_id"]))
        if p is None:
            continue
        rows.append(int(x["user_id"]))
        cols.append(p)
    X_sparse = csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)),
        shape=(n_users, len(warm_indices)),
    )
    return X_sparse, X_sparse.toarray().astype(np.float32)


def _z(x, eps=1e-8):
    m = x.mean(axis=1, keepdims=True)
    s = np.maximum(x.std(axis=1, keepdims=True), eps)
    return (x - m) / s


def make_score_cdr(Xw, B_warm, warm_indices, cold_indices, S_content, emb, n_items, alpha):
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    reg = Ridge(alpha=1.0)
    reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)

    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cd_cold = _z(Xw[uids] @ S_w_c)
        lc_cold = _z(Xw[uids] @ B_hat_cold)
        cold_blend = alpha * cd_cold + (1.0 - alpha) * lc_cold
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_blend
        return out

    return f


def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192,
              meta=None):
    ut = defaultdict(set)
    uts = defaultdict(list)
    for x in train_inters:
        ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters:
        uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, hr, rr = [], [], []
    per_user_ndcg = defaultdict(list)
    per_pair_rows = []
    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        for k, u in enumerate(batch):
            if ut[u]:
                scores[k, list(ut[u])] = -np.inf
            for tgt in uts[u]:
                ts = scores[k, tgt]
                r0 = int((scores[k] > ts).sum())
                h = 1.0 if r0 < TOP_K else 0.0
                n_ = 1.0 / math.log2(r0 + 2) if r0 < TOP_K else 0.0
                r_ = 1.0 / (r0 + 1)
                ndcg.append(n_)
                hr.append(h)
                rr.append(r_)
                per_user_ndcg[int(u)].append(n_)
                row = {
                    "user_id": int(u), "target_item_id": int(tgt),
                    "ndcg10": float(n_), "hr10": float(h), "rr": float(r_),
                }
                if meta is not None:
                    row.update(meta)
                per_pair_rows.append(row)
    summary = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(per_pair_rows),
    }
    per_user = {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}
    return summary, per_user, per_pair_rows


def select_alpha(dataset, outer_train, outer_cold_items, S_content, emb,
                  n_users, n_items, rng):
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32)
    rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters:
        return 0.25, {}
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
    S_w_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_w_in, dtype=np.float32)
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    scores = {}
    for a in CDR_ALPHA_GRID:
        sf = make_score_cdr(Xw_in, B_in, inner_warm, cold_arr, S_content, emb,
                              n_items, alpha=a)
        summary, _, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[float(a)] = summary["NDCG@10"]
    del X_in, Xw_in, B_in
    gc.collect()
    return max(scores, key=scores.get), scores


def append_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def run(dataset, seeds, jsonl_path):
    print(f"\n# CDR_validated baseline (per-pair records): {dataset.upper()}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    perfold = []
    per_user_all = defaultdict(list)
    selected_alphas = []
    if jsonl_path.exists():
        jsonl_path.unlink()
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t0 = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)
            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            a, _ = select_alpha(dataset, train_inters, set(cold), S_content,
                                  emb_np, n_users, n_items, val_rng)
            sf = make_score_cdr(Xw, B_warm, warm_idx, cold_idx, S_content,
                                  emb_np, n_items, alpha=a)
            summary, pu, rows = eval_full(sf, train_inters, test_inters, n_items,
                                           meta={
                                               "dataset": dataset, "seed": seed,
                                               "fold_id": fold_id,
                                               "method": "cdr_validated",
                                               "alpha": float(a),
                                               "candidate_scope": "full_catalog",
                                           })
            append_jsonl(jsonl_path, rows)
            perfold.append(summary["NDCG@10"])
            for u, vs in pu.items():
                per_user_all[u].append(vs)
            selected_alphas.append({"seed": seed, "fold_id": fold_id, "alpha": a})
            dt = time.time() - t0
            print(f"  seed={seed} fold={fold_id} alpha={a:.2f}  NDCG@10={summary['NDCG@10']:.4f}  [{dt:.1f}s]")
            del X_sparse, Xw, B_warm, S_warm
            gc.collect()
    return {
        "perfold_ndcg10": list(map(float, perfold)),
        "mean_ndcg10": float(np.mean(perfold)) if perfold else 0.0,
        "std_ndcg10": float(np.std(perfold)) if perfold else 0.0,
        "per_user_ndcg10": {int(u): float(np.mean(vs)) for u, vs in per_user_all.items()},
        "selected_alphas": selected_alphas,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--out", default="results_cdr_cl_cdr_validated_baseline.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    out = Path(__file__).parent / args.out
    if out.exists():
        try:
            payload = json.load(open(out))
        except Exception:
            payload = {"datasets": {}}
    else:
        payload = {
            "schema_version": 1,
            "candidate_scope": "full_catalog",
            "method": "cdr_validated_per_pair",
            "datasets": {},
        }
    payload["seeds"] = seeds
    for ds in args.datasets:
        jsonl_path = Path(__file__).parent / f"results_cdr_validated_records_{ds}.jsonl"
        payload["datasets"][ds] = run(ds, seeds, jsonl_path)
        with open(out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n=== {ds.upper()} CDR_validated ===\n"
              f"mean+/-std: {payload['datasets'][ds]['mean_ndcg10']:.4f} +/- {payload['datasets'][ds]['std_ndcg10']:.4f}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
