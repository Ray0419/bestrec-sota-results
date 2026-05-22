"""Fast LC2C++ z-fusion weight grid.

Evaluates fixed per-user z-score fusion weights:

    score = w * z(LC2C V2) + (1 - w) * z(content_direct)

This is still exploratory unless the chosen weight is selected on validation
folds, but it avoids expensive kernel/dropout reruns and gives a clean view of
the LC2C/content tradeoff.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix

from artifact_utils import RUN_DIR, append_manifest_run, write_json
from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, eval_cold_item_ranking, make_item_kfold, reindex_warm_only
from run_cold_item_v2 import make_score_content_direct, make_score_lc2c_v2, make_score_z_fusion
from v5_utils import ROOT, SEED, content_sim_matrix, kcore_filter, reindex


def run_dataset(dataset: str, weights: list[float], n_splits: int = 5) -> dict:
    k_core = DATASET_KCORE[dataset]
    lam, beta = HP[dataset]
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    print(f"\n{dataset.upper()}: {n_users:,} users / {n_items:,} items / {len(interactions):,} inters")

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{k_core}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)
    rows = {"lc2c_v2": [], "content_direct": []}
    for w in weights:
        rows[f"z_{w:.2f}"] = []

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

        rows["lc2c_v2"].append(eval_cold_item_ranking(sf_lc, train_inters, test_inters, n_items, cold_items))
        rows["content_direct"].append(eval_cold_item_ranking(sf_content, train_inters, test_inters, n_items, cold_items))
        fold_msg = [f"lc2c={rows['lc2c_v2'][-1]['NDCG@10']:.4f}"]
        for w in weights:
            key = f"z_{w:.2f}"
            sf = make_score_z_fusion([sf_lc, sf_content], [w, 1 - w])
            rows[key].append(eval_cold_item_ranking(sf, train_inters, test_inters, n_items, cold_items))
            fold_msg.append(f"{key}={rows[key][-1]['NDCG@10']:.4f}")
        print(f"  fold {fi}: " + " ".join(fold_msg))
        del B_warm, X_warm, X_sparse
        gc.collect()

    summary = {}
    for key, vals in rows.items():
        summary[key] = {
            "NDCG@10": float(np.mean([v["NDCG@10"] for v in vals])),
            "NDCG@10_std": float(np.std([v["NDCG@10"] for v in vals])),
            "HR@10": float(np.mean([v["HR@10"] for v in vals])),
            "MRR": float(np.mean([v["MRR"] for v in vals])),
        }
    for key, vals in sorted(summary.items(), key=lambda kv: kv[1]["NDCG@10"], reverse=True):
        print(f"  {key:<14} {vals['NDCG@10']:.5f} +- {vals['NDCG@10_std']:.5f}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="*", default=["beauty", "fashion", "instruments", "books"])
    ap.add_argument("--weights", default="0.75,0.85,0.90,0.95,0.98")
    args = ap.parse_args()
    weights = [float(x) for x in args.weights.split(",") if x.strip()]
    all_results = {ds: run_dataset(ds, weights) for ds in args.datasets}
    out = RUN_DIR / "results_lc2cpp_zgrid.json"
    write_json(out, {
        "schema_version": 1,
        "status": "exploratory_test_set_weight_grid_not_paper_valid",
        "weights": weights,
        "datasets": all_results,
    })
    append_manifest_run(
        command=["python", "run_lc2cpp_zgrid.py", *args.datasets, "--weights", args.weights],
        inputs=[RUN_DIR / "run_lc2cpp_zgrid.py", RUN_DIR / "run_cold_item_v2.py"],
        outputs=[out],
        datasets=args.datasets,
        seeds=[SEED],
        note="Exploratory LC2C++ z-fusion weight grid; not validation-selected.",
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
