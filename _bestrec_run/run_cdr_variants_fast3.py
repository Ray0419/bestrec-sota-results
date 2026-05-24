"""Optimized CDR variant driver with B_hat_cold caching AND batched-eval-over-alpha.

The key insight: warm_scores, cd_cold, lc_cold are all independent of alpha.
Only `cold_blend = alpha * z(cd_cold) + (1-alpha) * z(lc_cold)` depends on alpha.

We thus do ONE batch eval over all uids, score all alphas at once per batch,
and pay the (n_users * n_warm) and (n_users * n_cold) work ONCE per fold per
variant instead of 9 times.

This drops Books inner-validation cost from O(9 evals) to O(1 eval),
saving ~9x time on the dominant cost.

Same eval semantics; same per-pair records; same Wilcoxon as
run_cdr_variants_fast2.py.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from scipy.stats import wilcoxon

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix
from run_cdr_variants import (
    CDR_ALPHA_GRID, SEED, DEFAULT_VARIANTS,
    _ridge_b_hat, _weighted_ridge_b_hat, _kernel_ridge_b_hat,
    _topk_sparsify, _z, _quantile_calibrate,
    load_dataset, build_warm, eval_full,
)
from run_cdr_variants_fast2 import compute_b_hat_cold


def eval_alphas_at_once(variant_name, Xw, B_warm, warm_indices, cold_indices,
                          S_w_c, B_hat_cold, n_items, alphas, train_inters,
                          test_inters, batch_size=192,
                          record_rows=False, method_name=None, seed=None,
                          fold_id=None, dataset=None):
    """Like eval_full but evaluates all alphas in one pass.

    Returns:
      results: dict { alpha -> {NDCG@10, HR@10, MRR, n_eval} }
      per_user: dict { alpha -> { user_id -> mean_ndcg } }
      rows: dict { alpha -> list of per-(user,target) records } (only if record_rows)
    """
    ut = defaultdict(set); uts = defaultdict(list)
    for x in train_inters: ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters: uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    alphas = [float(a) for a in alphas]
    n_alphas = len(alphas)
    ndcg = {a: [] for a in alphas}
    hr = {a: [] for a in alphas}
    rr = {a: [] for a in alphas}
    per_user = {a: defaultdict(list) for a in alphas}
    rows = {a: [] for a in alphas} if record_rows else None

    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        uids = np.array(batch, dtype=np.int32)
        # Compute the alpha-independent pieces once
        warm_scores = Xw[uids] @ B_warm                   # (b, n_warm)
        cd_cold_raw = Xw[uids] @ S_w_c                     # (b, n_cold)
        lc_cold_raw = Xw[uids] @ B_hat_cold                # (b, n_cold)
        cd_z = _z(cd_cold_raw)
        lc_z = _z(lc_cold_raw)

        # For CDR_Q we also need warm to remain plain for quantile calibration
        for a in alphas:
            cold_blend = a * cd_z + (1.0 - a) * lc_z
            if variant_name == "CDR_Q":
                cold_blend = _quantile_calibrate(cold_blend, warm_scores)
            scores = np.empty((len(batch), n_items), dtype=np.float32)
            scores[:, warm_indices] = warm_scores
            scores[:, cold_indices] = cold_blend
            # Now per-user / per-target rank
            for k, u in enumerate(batch):
                if ut[u]:
                    # in-place: mask training items
                    # WARNING: we'd want to avoid clobbering scores[k] across alphas
                    # but each alpha gets its own `scores` allocation, so safe.
                    scores[k, list(ut[u])] = -np.inf
                for tgt in uts[u]:
                    ts = scores[k, tgt]
                    r0 = int((scores[k] > ts).sum())
                    n_ = 1.0 / math.log2(r0 + 2) if r0 < TOP_K else 0.0
                    h_ = 1.0 if r0 < TOP_K else 0.0
                    r_ = 1.0 / (r0 + 1)
                    ndcg[a].append(n_); hr[a].append(h_); rr[a].append(r_)
                    per_user[a][int(u)].append(n_)
                    if record_rows:
                        rows[a].append({"candidate_scope": "full_catalog",
                                          "dataset": dataset, "fold_id": fold_id,
                                          "hr10": float(h_), "method": method_name,
                                          "ndcg10": float(n_), "rr": float(r_),
                                          "seed": seed, "target_item_id": int(tgt),
                                          "user_id": int(u)})
    results = {a: {"NDCG@10": float(np.mean(ndcg[a])) if ndcg[a] else 0.0,
                    "HR@10":   float(np.mean(hr[a])) if hr[a] else 0.0,
                    "MRR":     float(np.mean(rr[a])) if rr[a] else 0.0,
                    "n_eval":  len(ndcg[a])} for a in alphas}
    pu = {a: {u: float(np.mean(vs)) for u, vs in per_user[a].items()} for a in alphas}
    return results, pu, rows


def build_inner_cache(dataset, outer_train, outer_cold_items, S_content,
                       n_users, n_items, rng):
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters: return None
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
    S_w_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_w_in, dtype=np.float32)
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    return {"inner_warm": inner_warm, "inner_train": inner_train,
             "val_inters": val_inters, "B_in": B_in,
             "X_in": X_in, "Xw_in": Xw_in, "cold_arr": cold_arr}


def run(dataset, seeds, variants, perpair_out=None):
    print(f"\n{'#'*70}\n# CDR variants (fast3 / alpha-batched eval): {dataset.upper()}\n{'#'*70}",
            flush=True)
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}",
            flush=True)

    perfold = {v: {"NDCG@10": [], "HR@10": [], "MRR": [], "fit_time": []} for v in variants}
    per_user_all = {v: defaultdict(list) for v in variants}
    selected_alphas = {v: [] for v in variants}

    perpair_records: dict[str, list] = {v: [] for v in variants}

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t_fold0 = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)
            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            t_ease = time.time()
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
            t_ease = time.time() - t_ease
            print(f"  seed={seed} fold={fold_id} outer EASE done [{t_ease:.1f}s]", flush=True)

            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            t_inner_ease = time.time()
            cache_in = build_inner_cache(dataset, train_inters, set(cold), S_content,
                                            n_users, n_items, val_rng)
            t_inner_ease = time.time() - t_inner_ease
            print(f"  seed={seed} fold={fold_id} inner EASE done [{t_inner_ease:.1f}s]", flush=True)

            S_w_c_outer = S_content[np.ix_(warm_idx, cold_idx)].astype(np.float32)
            SBERT_w_outer = emb_np[warm_idx].astype(np.float32)
            SBERT_c_outer = emb_np[cold_idx].astype(np.float32)

            if cache_in is not None:
                S_w_c_inner = S_content[np.ix_(cache_in["inner_warm"], cache_in["cold_arr"])].astype(np.float32)
                SBERT_w_inner = emb_np[cache_in["inner_warm"]].astype(np.float32)
                SBERT_c_inner = emb_np[cache_in["cold_arr"]].astype(np.float32)

            for variant_name in variants:
                t_var = time.time()
                # Inner validation: build B_hat_cold once for inner; eval all alphas in one pass
                if cache_in is None:
                    a = 0.25; val_scores = {}
                else:
                    t_b_inner = time.time()
                    B_hat_cold_inner = compute_b_hat_cold(
                        variant_name, SBERT_w_inner, SBERT_c_inner, cache_in["B_in"],
                        X_sparse_warm=cache_in["X_in"],
                        rng_seed=(seed * 100 + fold_id + 7) & 0xFFFFFFFF)
                    t_b_inner = time.time() - t_b_inner
                    t_eval_in = time.time()
                    val_res, _, _ = eval_alphas_at_once(
                        variant_name, cache_in["Xw_in"], cache_in["B_in"],
                        cache_in["inner_warm"], cache_in["cold_arr"],
                        S_w_c_inner, B_hat_cold_inner, n_items, CDR_ALPHA_GRID,
                        cache_in["inner_train"], cache_in["val_inters"])
                    t_eval_in = time.time() - t_eval_in
                    val_scores = {a: val_res[a]["NDCG@10"] for a in CDR_ALPHA_GRID}
                    a = max(val_scores, key=val_scores.get)
                t_val = time.time() - t_var

                # Outer: build B_hat_cold once, eval ONLY chosen alpha
                t_b_outer = time.time()
                B_hat_cold_outer = compute_b_hat_cold(
                    variant_name, SBERT_w_outer, SBERT_c_outer, B_warm,
                    X_sparse_warm=X_sparse,
                    rng_seed=(seed * 200 + fold_id + 11) & 0xFFFFFFFF)
                t_b_outer = time.time() - t_b_outer
                t_eval_out = time.time()
                outer_res, outer_pu, outer_rows = eval_alphas_at_once(
                    variant_name, Xw, B_warm, warm_idx, cold_idx,
                    S_w_c_outer, B_hat_cold_outer, n_items, [a],
                    train_inters, test_inters,
                    record_rows=(perpair_out is not None),
                    method_name=variant_name, seed=seed, fold_id=fold_id,
                    dataset=dataset)
                t_eval_out = time.time() - t_eval_out
                summ = outer_res[a]
                pu = outer_pu[a]
                rows = outer_rows[a] if outer_rows else []
                t_var = time.time() - t_var

                selected_alphas[variant_name].append({
                    "seed": seed, "fold_id": fold_id, "alpha": a,
                    "val_scores": val_scores, "val_time_s": t_val})
                perfold[variant_name]["NDCG@10"].append(summ["NDCG@10"])
                perfold[variant_name]["HR@10"].append(summ["HR@10"])
                perfold[variant_name]["MRR"].append(summ["MRR"])
                perfold[variant_name]["fit_time"].append(t_var + t_ease + t_inner_ease)
                for u, vs in pu.items():
                    per_user_all[variant_name][u].append(float(vs))
                if perpair_out is not None and rows:
                    perpair_records[variant_name].extend(rows)
                print(f"  seed={seed} fold={fold_id} variant={variant_name:>14s} "
                      f"alpha={a:.2f} NDCG@10={summ['NDCG@10']:.4f} "
                      f"HR@10={summ['HR@10']:.4f} TOTAL={t_var:.1f}s",
                      flush=True)

            if cache_in is not None: del cache_in
            del X_sparse, Xw, B_warm, S_warm, S_w_c_outer, SBERT_w_outer, SBERT_c_outer
            gc.collect()
            print(f"  seed={seed} fold={fold_id} FOLD TOTAL = {time.time()-t_fold0:.1f}s",
                    flush=True)

    if perpair_out is not None:
        with open(perpair_out, "a") as fh:
            for v in variants:
                for r in perpair_records[v]:
                    fh.write(json.dumps(r) + "\n")
        print(f"  appended per-pair records -> {perpair_out}", flush=True)

    print(f"\n=== {dataset.upper()} per-fold NDCG@10 means ===", flush=True)
    for name in variants:
        vs = perfold[name]["NDCG@10"]
        ts = perfold[name]["fit_time"]
        print(f"  {name:>16s}: NDCG@10 = {np.mean(vs):.4f} +/- {np.std(vs):.4f}  "
              f"avg fit time = {np.mean(ts):.1f}s", flush=True)

    print(f"\n=== {dataset.upper()} per-USER Wilcoxon vs CDR_validated ===", flush=True)
    def _pu_mean(name):
        return {u: float(np.mean(vs)) for u, vs in per_user_all[name].items()}
    cdr_pu = _pu_mean("CDR_validated") if "CDR_validated" in per_user_all else {}
    wilcox = {}
    pvalues = {}
    for vname in variants:
        if vname == "CDR_validated": continue
        vpu = _pu_mean(vname)
        common = sorted(set(cdr_pu) & set(vpu))
        diffs = np.array([vpu[u] - cdr_pu[u] for u in common])
        if np.allclose(diffs, 0): p_two = 1.0; p_g = 1.0
        else:
            p_two = float(wilcoxon(diffs, alternative='two-sided', zero_method='wilcox').pvalue)
            p_g = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
        marker = '***' if p_two < 0.001 else '**' if p_two < 0.01 else '*' if p_two < 0.05 else 'n.s.'
        wilcox[vname] = {"n_users": len(common),
                         "variant_mean": float(np.mean([vpu[u] for u in common])) if common else 0.0,
                         "cdr_mean": float(np.mean([cdr_pu[u] for u in common])) if common else 0.0,
                         "delta": float(np.mean(diffs)) if len(diffs) else 0.0,
                         "p_two_sided": p_two, "p_greater": p_g, "marker": marker}
        pvalues[vname] = p_two
        print(f"  {vname:<16s} vs CDR_validated: n={len(common):>6} "
              f"variant={wilcox[vname]['variant_mean']:.4f} "
              f"CDR={wilcox[vname]['cdr_mean']:.4f} "
              f"delta={wilcox[vname]['delta']:+.4f} "
              f"p2s={p_two:.3e} p_greater={p_g:.3e} {marker}", flush=True)
    sorted_v = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(sorted_v)
    holm = {}
    for rank, (vn, p) in enumerate(sorted_v):
        holm[vn] = min(1.0, p * (m - rank))
    for vn in wilcox:
        wilcox[vn]["p_two_sided_holm"] = float(holm.get(vn, wilcox[vn]["p_two_sided"]))
    return {"perfold": {n: {k: list(map(float, v)) for k, v in d.items()}
                          for n, d in perfold.items()},
            "selected_alphas": selected_alphas,
            "wilcoxon_vs_cdr_validated": wilcox}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty", "fashion"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    ap.add_argument("--out", default="results_cdr_variants.json")
    ap.add_argument("--perpair", action="store_true")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    out = Path(__file__).parent / args.out
    if out.exists():
        try: payload = json.load(open(out))
        except Exception: payload = {"datasets": {}}
    else:
        payload = {"schema_version": 1, "candidate_scope": "full_catalog",
                    "status": "cdr_variant_exploration", "datasets": {}}
    payload["seeds"] = seeds
    payload["variants"] = variants
    for ds in args.datasets:
        perpair_out = None
        if args.perpair:
            perpair_out = str(Path(__file__).parent /
                                f"results_cdr_variants_perpair_{ds}.jsonl")
            open(perpair_out, "w").close()
        if "datasets" not in payload: payload["datasets"] = {}
        payload["datasets"][ds] = run(ds, seeds, variants, perpair_out=perpair_out)
        with open(out, "w") as f: json.dump(payload, f, indent=2)
    print(f"\nwrote {out}", flush=True)


if __name__ == "__main__":
    main()
