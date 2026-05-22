"""Validation-selected LC2C++ z-fusion.

For each outer cold-item fold:
1. Split the outer training items into inner-train and validation-cold items.
2. Fit LC2C V2 on inner-train items only.
3. Select the z-fusion weight on validation-cold NDCG@10.
4. Refit on all outer warm items and evaluate the selected weight on the
   held-out outer cold fold.

This avoids choosing the LC2C++ fusion weight from the test fold. The metric is
still the existing cold_fold_only candidate scope; full-catalog cold-item
ranking remains required for a SOTA claim.
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

from artifact_utils import RUN_DIR, append_manifest_run, write_json
from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, eval_cold_item_ranking, make_item_kfold, reindex_warm_only
from run_cold_item_v2 import make_score_content_direct, make_score_lc2c_v2, make_score_z_fusion
from v5_utils import ROOT, SEED, content_sim_matrix, kcore_filter, reindex


def _fit_lc2c_and_content(train_inters, n_users, n_items, cold_items, item_title_emb, S_content, lam, beta):
    warm_items = sorted(set(range(n_items)) - set(cold_items))
    warm_indices = np.array(warm_items, dtype=np.int32)
    cold_arr = np.array(sorted(cold_items), dtype=np.int32)
    X_warm = reindex_warm_only(train_inters, n_users, n_items, set(cold_items))
    X_sparse = csr_matrix(X_warm[:, warm_indices])
    S_warm = S_content[np.ix_(warm_indices, warm_indices)]
    B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
    sf_lc = make_score_lc2c_v2(X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
    sf_content = make_score_content_direct(X_warm, S_content, warm_indices, cold_arr)
    return sf_lc, sf_content, cold_arr, B_warm, X_warm


def _perpair_records(dataset, seed, method, fold_id, fold_res):
    records = []
    ndcg = fold_res.get("ndcg_per_pair", [])
    users = fold_res.get("user_id_per_pair", [])
    items = fold_res.get("item_id_per_pair", [])
    hrs = fold_res.get("hr_per_pair", [None] * len(ndcg))
    rrs = fold_res.get("rr_per_pair", [None] * len(ndcg))
    for u, it, val, h, rr in zip(
        users,
        items,
        ndcg,
        hrs,
        rrs,
    ):
        records.append([dataset, fold_id, seed, method, u, it, "cold_fold_only", val, h, rr])
    return records


def run_dataset(dataset: str, weights: list[float], val_frac: float = 0.2,
                n_splits: int = 5, min_margin: float = 0.001) -> dict:
    k_core = DATASET_KCORE[dataset]
    lam, beta = HP[dataset]
    print(f"\n{'#' * 70}\n# VALIDATED LC2C++: {dataset.upper()} (k={k_core})\n{'#' * 70}")
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    print(f"  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters")

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{k_core}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)

    outer_rows = {"lc2c_v2": [], "lc2cpp_validated": [], "lc2cpp_validated_margin": []}
    perpair = {"lc2c_v2": [], "lc2cpp_validated": [], "lc2cpp_validated_margin": []}
    selected = []

    for fi, (tr_idx, te_idx, outer_cold_items) in enumerate(splits):
        outer_train = [interactions[i] for i in tr_idx]
        outer_test = [interactions[i] for i in te_idx]
        outer_warm_items = np.array(sorted(set(range(n_items)) - set(outer_cold_items)), dtype=np.int32)

        rng = np.random.RandomState(SEED + 1000 * fi)
        shuffled = outer_warm_items.copy()
        rng.shuffle(shuffled)
        n_val = max(1, int(round(len(shuffled) * val_frac)))
        val_items = set(int(x) for x in shuffled[:n_val])
        inner_cold = set(outer_cold_items) | val_items
        inner_train = [x for x in outer_train if x["item_id"] not in val_items]
        val_inters = [x for x in outer_train if x["item_id"] in val_items]

        sf_lc_val, sf_content_val, _, B_inner, X_inner = _fit_lc2c_and_content(
            inner_train, n_users, n_items, val_items, item_title_emb, S_content, lam, beta)
        best_w = 1.0
        best_score = -1.0
        val_scores = {}
        for w in weights:
            sf = sf_lc_val if w == 1.0 else make_score_z_fusion([sf_lc_val, sf_content_val], [w, 1 - w])
            r = eval_cold_item_ranking(sf, inner_train, val_inters, n_items, val_items)
            val_scores[f"{w:.2f}"] = r["NDCG@10"]
            if r["NDCG@10"] > best_score:
                best_score = r["NDCG@10"]
                best_w = w
        base_val = val_scores.get("1.00", best_score)
        margin_w = best_w if best_score - base_val >= min_margin else 1.0
        del B_inner, X_inner
        gc.collect()

        sf_lc, sf_content, _, B_outer, X_outer = _fit_lc2c_and_content(
            outer_train, n_users, n_items, outer_cold_items, item_title_emb, S_content, lam, beta)
        sf_selected = sf_lc if best_w == 1.0 else make_score_z_fusion([sf_lc, sf_content], [best_w, 1 - best_w])
        sf_margin = sf_lc if margin_w == 1.0 else make_score_z_fusion([sf_lc, sf_content], [margin_w, 1 - margin_w])
        res_v2 = eval_cold_item_ranking(sf_lc, outer_train, outer_test, n_items, outer_cold_items)
        res_sel = eval_cold_item_ranking(sf_selected, outer_train, outer_test, n_items, outer_cold_items)
        res_margin = eval_cold_item_ranking(sf_margin, outer_train, outer_test, n_items, outer_cold_items)
        outer_rows["lc2c_v2"].append(res_v2)
        outer_rows["lc2cpp_validated"].append(res_sel)
        outer_rows["lc2cpp_validated_margin"].append(res_margin)
        perpair["lc2c_v2"].extend(_perpair_records(dataset, SEED, "lc2c_v2", fi, res_v2))
        perpair["lc2cpp_validated"].extend(_perpair_records(dataset, SEED, "lc2cpp_validated", fi, res_sel))
        perpair["lc2cpp_validated_margin"].extend(_perpair_records(dataset, SEED, "lc2cpp_validated_margin", fi, res_margin))
        selected.append({
            "fold": fi,
            "weight": best_w,
            "margin_weight": margin_w,
            "val_ndcg10": best_score,
            "base_val_ndcg10": base_val,
            "min_margin": min_margin,
            "val_scores": val_scores,
        })
        print(f"  fold {fi}: selected w={best_w:.2f} val={best_score:.4f} "
              f"margin_w={margin_w:.2f} test_v2={res_v2['NDCG@10']:.4f} "
              f"test_validated={res_sel['NDCG@10']:.4f} test_margin={res_margin['NDCG@10']:.4f}")
        del B_outer, X_outer
        gc.collect()

    summary = {
        "selected_weights": selected,
        "methods": {},
    }
    for name, rows in outer_rows.items():
        summary["methods"][name] = {
            "NDCG@10": float(np.mean([r["NDCG@10"] for r in rows])),
            "NDCG@10_std": float(np.std([r["NDCG@10"] for r in rows])),
            "HR@10": float(np.mean([r["HR@10"] for r in rows])),
            "MRR": float(np.mean([r["MRR"] for r in rows])),
        }
        print(f"    {name:<18} NDCG@10={summary['methods'][name]['NDCG@10']:.5f} "
              f"+- {summary['methods'][name]['NDCG@10_std']:.5f}")

    perpair_path = RUN_DIR / f"results_lc2cpp_validated_perpair_{dataset}.json"
    write_json(perpair_path, {
        "schema": "[dataset, fold_id, seed, method, user_id, target_item_id, candidate_scope, ndcg10, hr10, rr]",
        "methods": perpair,
    })
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="*", default=["beauty", "fashion", "instruments", "books"])
    ap.add_argument("--weights", default="1.0,0.98,0.95,0.90,0.85,0.75")
    ap.add_argument("--min-margin", type=float, default=0.001)
    args = ap.parse_args()
    weights = [float(x) for x in args.weights.split(",") if x.strip()]
    payload = {
        "schema_version": 1,
        "candidate_scope": "cold_fold_only",
        "status": "validation_selected_secondary_metric",
        "weights": weights,
        "datasets": {},
    }
    for dataset in args.datasets:
        payload["datasets"][dataset] = run_dataset(dataset, weights, min_margin=args.min_margin)
        write_json(RUN_DIR / "results_lc2cpp_validated.json", payload)
    append_manifest_run(
        command=["python", "run_lc2cpp_validated.py", *args.datasets, "--weights", args.weights],
        inputs=[RUN_DIR / "run_lc2cpp_validated.py", RUN_DIR / "run_cold_item_v2.py"],
        outputs=[RUN_DIR / "results_lc2cpp_validated.json", *(RUN_DIR.glob("results_lc2cpp_validated_perpair_*.json"))],
        datasets=args.datasets,
        seeds=[SEED],
        note="Validation-selected LC2C++ z-fusion on secondary cold-fold-only metric.",
    )
    print(f"Wrote {RUN_DIR / 'results_lc2cpp_validated.json'}")


if __name__ == "__main__":
    main()
