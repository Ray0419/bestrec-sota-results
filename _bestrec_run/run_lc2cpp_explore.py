"""Exploratory LC2C++ combination sweep.

This is an internal algorithm-development script, not a paper-valid tuning
path. It tries current cold-start ideas inspired by text retrieval, contrastive
content-CF alignment, rank fusion, and long-tail/popularity calibration. A
variant should only be promoted to the paper pipeline after validation-only
selection is implemented.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from scipy.stats import rankdata

from artifact_utils import RUN_DIR, append_manifest_run, write_json
from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, eval_cold_item_ranking, make_item_kfold, reindex_warm_only
from run_cold_item_v2 import (
    make_score_content_direct,
    make_score_content_topk,
    make_score_lc2c_v2,
    make_score_lc2cpp_kernel,
)
from v5_utils import ROOT, SEED, content_sim_matrix, kcore_filter, reindex


def _zscore(x: np.ndarray) -> np.ndarray:
    mu = x.mean(axis=1, keepdims=True)
    sd = x.std(axis=1, keepdims=True)
    return (x - mu) / np.maximum(sd, 1e-6)


def make_z_fusion(fns, weights):
    weights = np.asarray(weights, dtype=np.float32)
    weights = weights / weights.sum()

    def fn(user_ids, cold_arr):
        out = None
        for w, score_fn in zip(weights, fns):
            z = _zscore(score_fn(user_ids, cold_arr).astype(np.float32))
            out = w * z if out is None else out + w * z
        return out

    return fn


def make_rrf_fusion(fns, weights=None, k: float = 60.0):
    if weights is None:
        weights = [1.0] * len(fns)
    weights = np.asarray(weights, dtype=np.float32)
    weights = weights / weights.sum()

    def fn(user_ids, cold_arr):
        fused = None
        for w, score_fn in zip(weights, fns):
            s = score_fn(user_ids, cold_arr)
            desc_rank = s.shape[1] + 1 - np.apply_along_axis(rankdata, 1, s).astype(np.float32)
            rrf = 1.0 / (k + desc_rank)
            fused = w * rrf if fused is None else fused + w * rrf
        return fused

    return fn


def make_semantic_popularity(train_inters, S_content, warm_indices, cold_arr, n_users):
    pop = np.zeros(S_content.shape[0], dtype=np.float32)
    for inter in train_inters:
        pop[inter["item_id"]] += 1.0
    pop_w = pop[warm_indices]
    if pop_w.max() > 0:
        pop_w = np.log1p(pop_w) / np.log1p(pop_w.max())
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    denom = np.maximum(np.abs(S_wc).sum(axis=0), 1e-6)
    cold_pop = (S_wc.T @ pop_w) / denom
    cold_pop = cold_pop.astype(np.float32)

    def fn(user_ids, cold_arr):
        return np.tile(cold_pop, (len(user_ids), 1))

    return fn


def run_dataset(dataset: str, n_splits: int = 5) -> dict:
    k_core = DATASET_KCORE[dataset]
    lam, beta = HP[dataset]
    print(f"\n{'#' * 70}\n# LC2C++ EXPLORE: {dataset.upper()} (k={k_core})\n{'#' * 70}")
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    print(f"  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters")

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{k_core}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)

    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)
    methods = {}

    for fi, (tr_idx, te_idx, cold_items) in enumerate(splits):
        train_inters = [interactions[i] for i in tr_idx]
        test_inters = [interactions[i] for i in te_idx]
        warm_items = sorted(set(range(n_items)) - cold_items)
        warm_indices = np.array(warm_items, dtype=np.int32)
        cold_arr = np.array(sorted(cold_items), dtype=np.int32)

        X_warm = reindex_warm_only(train_inters, n_users, n_items, cold_items)
        X_sparse = csr_matrix(X_warm[:, warm_indices])
        S_warm = S_content[np.ix_(warm_indices, warm_indices)]
        B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)

        sf_lc = make_score_lc2c_v2(X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
        sf_content = make_score_content_direct(X_warm, S_content, warm_indices, cold_arr)
        sf_topk = make_score_content_topk(train_inters, S_content, n_users, n_items, warm_indices, cold_arr)
        sf_pop = make_semantic_popularity(train_inters, S_content, warm_indices, cold_arr, n_users)

        fold_fns = {
            "lc2c_v2": sf_lc,
            "content_direct": sf_content,
            "content_topk": sf_topk,
            "semantic_pop": sf_pop,
        }
        for w in (0.6, 0.75, 0.9):
            fold_fns[f"z_lc_content_{w:.2f}"] = make_z_fusion([sf_lc, sf_content], [w, 1 - w])
            fold_fns[f"z_lc_topk_{w:.2f}"] = make_z_fusion([sf_lc, sf_topk], [w, 1 - w])
            fold_fns[f"z_lc_pop_{w:.2f}"] = make_z_fusion([sf_lc, sf_pop], [w, 1 - w])
        fold_fns["z_lc_content_topk_7030"] = make_z_fusion([sf_lc, sf_content, sf_topk], [0.7, 0.15, 0.15])
        fold_fns["z_lc_content_pop_8020"] = make_z_fusion([sf_lc, sf_content, sf_pop], [0.8, 0.1, 0.1])
        fold_fns["rrf_lc_content_topk"] = make_rrf_fusion([sf_lc, sf_content, sf_topk], [0.7, 0.15, 0.15])
        fold_fns["rrf_lc_content_pop"] = make_rrf_fusion([sf_lc, sf_content, sf_pop], [0.8, 0.1, 0.1])

        for gamma in (0.05, 0.1, 0.25, 0.5):
            for mu in (0.3, 1.0, 3.0, 10.0):
                key = f"kernel_g{gamma:g}_mu{mu:g}"
                fold_fns[key] = make_score_lc2cpp_kernel(
                    X_warm, B_warm, item_title_emb, warm_indices, cold_arr,
                    mu=mu, n_rff=512, gamma=gamma, seed=SEED)

        for name, score_fn in fold_fns.items():
            r = eval_cold_item_ranking(score_fn, train_inters, test_inters, n_items, cold_items)
            methods.setdefault(name, []).append(r)

        best_fold = sorted(
            ((name, methods[name][-1]["NDCG@10"]) for name in fold_fns),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        print("  fold", fi, " ".join(f"{n}={v:.4f}" for n, v in best_fold))
        del B_warm, X_warm, X_sparse
        gc.collect()

    summary = {}
    for name, rows in methods.items():
        summary[name] = {
            "NDCG@10": float(np.mean([r["NDCG@10"] for r in rows])),
            "NDCG@10_std": float(np.std([r["NDCG@10"] for r in rows])),
            "HR@10": float(np.mean([r["HR@10"] for r in rows])),
            "MRR": float(np.mean([r["MRR"] for r in rows])),
        }
    ranked = sorted(summary.items(), key=lambda kv: kv[1]["NDCG@10"], reverse=True)
    print("\nTop 15 exploratory variants:")
    for name, vals in ranked[:15]:
        print(f"  {name:<28} NDCG@10={vals['NDCG@10']:.4f}+-{vals['NDCG@10_std']:.4f} HR={vals['HR@10']:.4f} MRR={vals['MRR']:.4f}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    args = ap.parse_args()
    out = RUN_DIR / "results_lc2cpp_explore.json"
    if out.exists():
        prior = json.loads(out.read_text(encoding="utf-8"))
        all_results = prior.get("datasets", {})
    else:
        all_results = {}
    for dataset in args.datasets:
        all_results[dataset] = run_dataset(dataset)
    write_json(out, {
        "schema_version": 1,
        "status": "exploratory_test_set_sweep_not_paper_valid",
        "warning": "Do not report a winning variant from this file unless it is rerun under validation-only selection.",
        "datasets": all_results,
    })
    append_manifest_run(
        command=["python", "run_lc2cpp_explore.py", *args.datasets],
        inputs=[RUN_DIR / "run_lc2cpp_explore.py", RUN_DIR / "run_cold_item_v2.py"],
        outputs=[out],
        datasets=args.datasets,
        seeds=[SEED],
        note="Exploratory LC2C++ combination sweep; not a valid paper selection path.",
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
