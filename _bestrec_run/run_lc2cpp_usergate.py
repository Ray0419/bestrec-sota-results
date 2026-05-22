"""Validation user-gated LC2C++ selector.

For each outer cold-item fold, this script holds out validation-cold items from
the outer training items, evaluates several candidate scorers on that validation
set, and assigns each user the candidate that produced the highest validation
NDCG for that user. Users without validation evidence fall back to the globally
best validation candidate. The selected gate is then evaluated on the untouched
outer cold-item fold.

This is a validation-selected secondary cold_fold_only metric. It is not a
full-catalog SOTA evaluation.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import pickle
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix

from artifact_utils import RUN_DIR, append_manifest_run, write_json
from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, eval_cold_item_ranking, make_item_kfold, reindex_warm_only
from run_cold_item_v2 import (
    make_score_cf_hybrid,
    make_score_content_direct,
    make_score_content_topk,
    make_score_lc2c_v1,
    make_score_lc2c_v2,
    make_score_z_fusion,
)
from v5_utils import ROOT, SEED, content_sim_matrix, kcore_filter, reindex


def _fit_candidates(train_inters, n_users, n_items, cold_items, item_title_emb, S_content, lam, beta):
    warm_indices = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
    cold_arr = np.array(sorted(cold_items), dtype=np.int32)
    X_warm = reindex_warm_only(train_inters, n_users, n_items, set(cold_items))
    X_sparse = csr_matrix(X_warm[:, warm_indices])
    S_warm = S_content[np.ix_(warm_indices, warm_indices)]
    B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
    lc2c_v2 = make_score_lc2c_v2(X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
    content = make_score_content_direct(X_warm, S_content, warm_indices, cold_arr)
    topk = make_score_content_topk(train_inters, S_content, n_users, n_items, warm_indices, cold_arr)
    lc2c_v1 = make_score_lc2c_v1(X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
    return {
        "lc2c_v2": lc2c_v2,
        "z_0.98": make_score_z_fusion([lc2c_v2, content], [0.98, 0.02]),
        "z_0.95": make_score_z_fusion([lc2c_v2, content], [0.95, 0.05]),
        "z_0.90": make_score_z_fusion([lc2c_v2, content], [0.90, 0.10]),
        "z_0.75": make_score_z_fusion([lc2c_v2, content], [0.75, 0.25]),
        "cf_hybrid": make_score_cf_hybrid(lc2c_v2, content, alpha=0.5),
        "content_topk": topk,
        "content_direct": content,
        "lc2c_v1": lc2c_v1,
    }, B_warm, X_warm


def _user_means(fold_res):
    by = defaultdict(list)
    for u, val in zip(fold_res.get("user_id_per_pair", []), fold_res.get("ndcg_per_pair", [])):
        by[int(u)].append(float(val))
    return {u: float(np.mean(v)) for u, v in by.items()}


def _make_gate(candidates, user_choice, fallback):
    def fn(user_ids, cold_arr):
        uid_list = [int(u) for u in user_ids]
        out = None
        # Compute each candidate once for the batch, then copy selected rows.
        mats = {name: score_fn(user_ids, cold_arr) for name, score_fn in candidates.items()}
        selected = []
        for row_idx, uid in enumerate(uid_list):
            name = user_choice.get(uid, fallback)
            selected.append(mats[name][row_idx])
        out = np.vstack(selected).astype(np.float32)
        return out
    return fn


def _records(dataset, method, fold_id, fold_res):
    out = []
    ndcg = fold_res.get("ndcg_per_pair", [])
    for u, item, val in zip(fold_res.get("user_id_per_pair", []), fold_res.get("item_id_per_pair", []), ndcg):
        out.append([dataset, fold_id, SEED, method, int(u), int(item), "cold_fold_only", float(val), None, None])
    return out


def run_dataset(dataset: str, val_frac: float = 0.2, n_splits: int = 5) -> dict:
    k_core = DATASET_KCORE[dataset]
    lam, beta = HP[dataset]
    print(f"\n{'#' * 70}\n# USER-GATED LC2C++: {dataset.upper()} (k={k_core})\n{'#' * 70}")
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = os.path.join(cache_dir, "v5", f"item_title_k{k_core}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)

    rows = {"lc2c_v2": [], "lc2cpp_usergate": []}
    perpair = {"lc2c_v2": [], "lc2cpp_usergate": []}
    gate_meta = []

    for fi, (tr_idx, te_idx, outer_cold_items) in enumerate(splits):
        outer_train = [interactions[i] for i in tr_idx]
        outer_test = [interactions[i] for i in te_idx]
        outer_warm_items = np.array(sorted(set(range(n_items)) - set(outer_cold_items)), dtype=np.int32)
        rng = np.random.RandomState(SEED + 1777 * fi)
        rng.shuffle(outer_warm_items)
        n_val = max(1, int(round(len(outer_warm_items) * val_frac)))
        val_items = set(int(x) for x in outer_warm_items[:n_val])
        inner_train = [x for x in outer_train if x["item_id"] not in val_items]
        val_inters = [x for x in outer_train if x["item_id"] in val_items]

        cand_val, B_inner, X_inner = _fit_candidates(inner_train, n_users, n_items, val_items, item_title_emb, S_content, lam, beta)
        val_by_candidate = {}
        global_scores = {}
        for name, fn in cand_val.items():
            res = eval_cold_item_ranking(fn, inner_train, val_inters, n_items, val_items)
            val_by_candidate[name] = _user_means(res)
            global_scores[name] = res["NDCG@10"]
        fallback = max(global_scores, key=global_scores.get)
        all_val_users = set().union(*(set(x) for x in val_by_candidate.values()))
        user_choice = {}
        for uid in all_val_users:
            best_name = fallback
            best_val = -1.0
            for name, vals in val_by_candidate.items():
                if uid in vals and vals[uid] > best_val:
                    best_name = name
                    best_val = vals[uid]
            user_choice[uid] = best_name
        del B_inner, X_inner
        gc.collect()

        cand_test, B_outer, X_outer = _fit_candidates(outer_train, n_users, n_items, outer_cold_items, item_title_emb, S_content, lam, beta)
        gate_fn = _make_gate(cand_test, user_choice, fallback)
        res_v2 = eval_cold_item_ranking(cand_test["lc2c_v2"], outer_train, outer_test, n_items, outer_cold_items)
        res_gate = eval_cold_item_ranking(gate_fn, outer_train, outer_test, n_items, outer_cold_items)
        rows["lc2c_v2"].append(res_v2)
        rows["lc2cpp_usergate"].append(res_gate)
        perpair["lc2c_v2"].extend(_records(dataset, "lc2c_v2", fi, res_v2))
        perpair["lc2cpp_usergate"].extend(_records(dataset, "lc2cpp_usergate", fi, res_gate))
        choice_counts = dict(Counter(user_choice.values()))
        gate_meta.append({"fold": fi, "fallback": fallback, "global_val": global_scores, "choice_counts": choice_counts})
        print(f"  fold {fi}: fallback={fallback} choices={choice_counts} "
              f"test_v2={res_v2['NDCG@10']:.4f} gate={res_gate['NDCG@10']:.4f}")
        del B_outer, X_outer
        gc.collect()

    summary = {"gate_meta": gate_meta, "methods": {}}
    for name, vals in rows.items():
        summary["methods"][name] = {
            "NDCG@10": float(np.mean([x["NDCG@10"] for x in vals])),
            "NDCG@10_std": float(np.std([x["NDCG@10"] for x in vals])),
            "HR@10": float(np.mean([x["HR@10"] for x in vals])),
            "MRR": float(np.mean([x["MRR"] for x in vals])),
        }
        print(f"    {name:<18} NDCG@10={summary['methods'][name]['NDCG@10']:.5f}")
    write_json(RUN_DIR / f"results_lc2cpp_usergate_perpair_{dataset}.json", {
        "schema": "[dataset, fold_id, seed, method, user_id, target_item_id, candidate_scope, ndcg10, hr10, rr]",
        "methods": perpair,
    })
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="*", default=["beauty", "fashion", "instruments", "books"])
    args = ap.parse_args()
    payload = {
        "schema_version": 1,
        "candidate_scope": "cold_fold_only",
        "status": "validation_user_gated_secondary_metric",
        "datasets": {},
    }
    for dataset in args.datasets:
        payload["datasets"][dataset] = run_dataset(dataset)
        write_json(RUN_DIR / "results_lc2cpp_usergate.json", payload)
    append_manifest_run(
        command=["python", "run_lc2cpp_usergate.py", *args.datasets],
        inputs=[RUN_DIR / "run_lc2cpp_usergate.py", RUN_DIR / "run_cold_item_v2.py"],
        outputs=[RUN_DIR / "results_lc2cpp_usergate.json", *(RUN_DIR.glob("results_lc2cpp_usergate_perpair_*.json"))],
        datasets=args.datasets,
        seeds=[SEED],
        note="Validation user-gated LC2C++ selector on secondary cold-fold-only metric.",
    )
    print(f"Wrote {RUN_DIR / 'results_lc2cpp_usergate.json'}")


if __name__ == "__main__":
    main()
