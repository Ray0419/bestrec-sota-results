"""Validation-selected component ablation/addition for LC2C++.

The goal is to test whether Beauty can be improved without test-set tuning.
Each outer fold selects one candidate method using only a validation-cold split
inside the outer training items, then evaluates that selected candidate on the
outer held-out cold-item fold.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import pickle
import sys
from collections import defaultdict

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


def _meta_arrays(item_meta, n_items):
    avg = np.zeros(n_items, dtype=np.float32)
    cnt = np.zeros(n_items, dtype=np.float32)
    price = np.zeros(n_items, dtype=np.float32)
    for i in range(n_items):
        m = item_meta.get(i, {})
        avg[i] = float(m.get("avg_rating") or 0.0)
        cnt[i] = float(m.get("rating_num") or 0.0)
        price[i] = float(m.get("price") or 0.0)
    return avg, cnt, price


def make_score_metadata_quality(item_meta, n_items, cold_arr):
    avg, cnt, price = _meta_arrays(item_meta, n_items)
    quality = np.nan_to_num(avg / 5.0 + 0.15 * np.log1p(cnt) / max(np.log1p(cnt.max()), 1e-6))
    cold_score = quality[cold_arr].astype(np.float32)

    def fn(user_ids, cold_items):
        return np.tile(cold_score, (len(user_ids), 1))

    return fn


def make_score_price_affinity(train_inters, item_meta, n_users, n_items, cold_arr):
    _, _, price = _meta_arrays(item_meta, n_items)
    by_user = defaultdict(list)
    for x in train_inters:
        p = price[x["item_id"]]
        if p > 0:
            by_user[x["user_id"]].append(p)
    user_price = np.zeros(n_users, dtype=np.float32)
    global_price = float(np.mean(price[price > 0])) if np.any(price > 0) else 0.0
    for u in range(n_users):
        vals = by_user.get(u)
        user_price[u] = float(np.mean(vals)) if vals else global_price
    cold_price = price[cold_arr].astype(np.float32)
    scale = float(np.std(price[price > 0])) if np.any(price > 0) else 1.0
    scale = max(scale, 1.0)

    def fn(user_ids, cold_items):
        pref = user_price[user_ids][:, None]
        return -np.abs(cold_price[None, :] - pref) / scale

    return fn


def make_score_semantic_pop(train_inters, S_content, warm_indices, cold_arr):
    pop = np.zeros(S_content.shape[0], dtype=np.float32)
    for x in train_inters:
        pop[x["item_id"]] += 1
    pop_w = np.log1p(pop[warm_indices])
    if pop_w.max() > 0:
        pop_w = pop_w / pop_w.max()
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    denom = np.maximum(np.abs(S_wc).sum(axis=0), 1e-6)
    cold_score = (S_wc.T @ pop_w) / denom

    def fn(user_ids, cold_items):
        return np.tile(cold_score, (len(user_ids), 1)).astype(np.float32)

    return fn


def _fit_candidates(train_inters, n_users, n_items, cold_items, item_meta, item_title_emb, S_content, lam, beta):
    warm_indices = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
    cold_arr = np.array(sorted(cold_items), dtype=np.int32)
    X_warm = reindex_warm_only(train_inters, n_users, n_items, set(cold_items))
    X_sparse = csr_matrix(X_warm[:, warm_indices])
    S_warm = S_content[np.ix_(warm_indices, warm_indices)]
    B_aug = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
    B_pure = ease_fast(X_sparse, lam=lam, beta=0.0, S_content=None, dtype=np.float32)

    candidates = {}
    base = make_score_lc2c_v2(X_warm, B_aug, item_title_emb, warm_indices, cold_arr, mu=1.0)
    candidates["lc2c_v2"] = base
    for mu in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0):
        candidates[f"lc2c_mu{mu:g}"] = make_score_lc2c_v2(X_warm, B_aug, item_title_emb, warm_indices, cold_arr, mu=mu)
        candidates[f"lc2c_pure_mu{mu:g}"] = make_score_lc2c_v2(X_warm, B_pure, item_title_emb, warm_indices, cold_arr, mu=mu)

    B_ho = B_aug + 0.3 * (B_aug @ B_aug)
    candidates["lc2c_higher_order"] = make_score_lc2c_v2(X_warm, B_ho, item_title_emb, warm_indices, cold_arr, mu=1.0)
    content = make_score_content_direct(X_warm, S_content, warm_indices, cold_arr)
    topk = make_score_content_topk(train_inters, S_content, n_users, n_items, warm_indices, cold_arr)
    quality = make_score_metadata_quality(item_meta, n_items, cold_arr)
    sempop = make_score_semantic_pop(train_inters, S_content, warm_indices, cold_arr)
    v1 = make_score_lc2c_v1(X_warm, B_aug, item_title_emb, warm_indices, cold_arr)

    candidates.update({
        "content_direct": content,
        "content_topk": topk,
        "metadata_quality": quality,
        "semantic_pop": sempop,
        "lc2c_v1": v1,
        "cf_hybrid": make_score_cf_hybrid(base, content, alpha=0.5),
    })
    for other_name, other_fn in (
        ("content", content),
        ("topk", topk),
        ("quality", quality),
        ("sempop", sempop),
        ("v1", v1),
    ):
        for w in (0.98, 0.95, 0.90, 0.85, 0.75, 0.60):
            candidates[f"z_{other_name}_{w:.2f}"] = make_score_z_fusion([base, other_fn], [w, 1 - w])
    return candidates, B_aug, B_pure, X_warm


def _records(dataset, method, fold_id, res):
    rows = []
    for u, item, val in zip(res.get("user_id_per_pair", []), res.get("item_id_per_pair", []), res.get("ndcg_per_pair", [])):
        rows.append([dataset, fold_id, SEED, method, int(u), int(item), "cold_fold_only", float(val), None, None])
    return rows


def run_dataset(dataset: str, val_frac: float = 0.2, n_splits: int = 5):
    k_core = DATASET_KCORE[dataset]
    lam, beta = HP[dataset]
    print(f"\n{'#' * 70}\n# COMPONENT-VALIDATED LC2C++: {dataset.upper()} (k={k_core})\n{'#' * 70}")
    data = pickle.load(open(os.path.join(ROOT, "cache", dataset, "raw_data_dedup.pkl"), "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = os.path.join(ROOT, "cache", dataset, "v5", f"item_title_k{k_core}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)

    rows = {"lc2c_v2": [], "lc2cpp_component_validated": []}
    perpair = {"lc2c_v2": [], "lc2cpp_component_validated": []}
    chosen = []
    for fi, (tr_idx, te_idx, outer_cold_items) in enumerate(splits):
        outer_train = [interactions[i] for i in tr_idx]
        outer_test = [interactions[i] for i in te_idx]
        outer_warm_items = np.array(sorted(set(range(n_items)) - set(outer_cold_items)), dtype=np.int32)
        rng = np.random.RandomState(SEED + 311 * fi)
        rng.shuffle(outer_warm_items)
        n_val = max(1, int(round(len(outer_warm_items) * val_frac)))
        val_items = set(int(x) for x in outer_warm_items[:n_val])
        inner_train = [x for x in outer_train if x["item_id"] not in val_items]
        val_inters = [x for x in outer_train if x["item_id"] in val_items]

        val_candidates, B1, B2, X1 = _fit_candidates(inner_train, n_users, n_items, val_items, item_meta, item_title_emb, S_content, lam, beta)
        val_scores = {}
        for name, fn in val_candidates.items():
            val_scores[name] = eval_cold_item_ranking(fn, inner_train, val_inters, n_items, val_items)["NDCG@10"]
        best_name = max(val_scores, key=val_scores.get)
        del B1, B2, X1
        gc.collect()

        test_candidates, B1, B2, X1 = _fit_candidates(outer_train, n_users, n_items, outer_cold_items, item_meta, item_title_emb, S_content, lam, beta)
        res_base = eval_cold_item_ranking(test_candidates["lc2c_v2"], outer_train, outer_test, n_items, outer_cold_items)
        res_best = eval_cold_item_ranking(test_candidates[best_name], outer_train, outer_test, n_items, outer_cold_items)
        rows["lc2c_v2"].append(res_base)
        rows["lc2cpp_component_validated"].append(res_best)
        perpair["lc2c_v2"].extend(_records(dataset, "lc2c_v2", fi, res_base))
        perpair["lc2cpp_component_validated"].extend(_records(dataset, "lc2cpp_component_validated", fi, res_best))
        top3 = sorted(val_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
        chosen.append({"fold": fi, "selected": best_name, "top3_validation": top3})
        print(f"  fold {fi}: selected={best_name} val={val_scores[best_name]:.4f} "
              f"test_v2={res_base['NDCG@10']:.4f} test_sel={res_best['NDCG@10']:.4f} top3={top3}")
        del B1, B2, X1
        gc.collect()

    summary = {"selected": chosen, "methods": {}}
    for name, vals in rows.items():
        summary["methods"][name] = {
            "NDCG@10": float(np.mean([x["NDCG@10"] for x in vals])),
            "NDCG@10_std": float(np.std([x["NDCG@10"] for x in vals])),
            "HR@10": float(np.mean([x["HR@10"] for x in vals])),
            "MRR": float(np.mean([x["MRR"] for x in vals])),
        }
        print(f"    {name:<30} NDCG@10={summary['methods'][name]['NDCG@10']:.5f}")
    write_json(RUN_DIR / f"results_lc2cpp_components_validated_perpair_{dataset}.json", {
        "schema": "[dataset, fold_id, seed, method, user_id, target_item_id, candidate_scope, ndcg10, hr10, rr]",
        "methods": perpair,
    })
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    args = ap.parse_args()
    out = RUN_DIR / "results_lc2cpp_components_validated.json"
    payload = {"schema_version": 1, "candidate_scope": "cold_fold_only", "status": "component_validation_selected", "datasets": {}}
    if out.exists():
        payload = json.loads(out.read_text(encoding="utf-8"))
    for ds in args.datasets:
        payload.setdefault("datasets", {})[ds] = run_dataset(ds)
        write_json(out, payload)
    append_manifest_run(
        command=["python", "run_lc2cpp_components_validated.py", *args.datasets],
        inputs=[RUN_DIR / "run_lc2cpp_components_validated.py", RUN_DIR / "run_cold_item_v2.py"],
        outputs=[out, *(RUN_DIR.glob("results_lc2cpp_components_validated_perpair_*.json"))],
        datasets=args.datasets,
        seeds=[SEED],
        note="Component add/remove validation-selected LC2C++ attempt.",
    )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
