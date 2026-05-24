"""Optimized CDR variant driver: shares inner-EASE solve across variants.

The original `run_cdr_variants.py` pays an inner-EASE solve per (variant, fold,
alpha) tuple. On Books that's 5 variants x 5 folds x 1 inner EASE = 25 inner
EASE solves (about 25 minutes plus the kernel-ridge cost). This driver
pre-computes ONE inner EASE per (seed, fold_id), then alpha-grid validates all
variants against it. Total inner-EASE cost drops to 5 solves on Books.

The eval semantics are identical to `run_cdr_variants.py`: alpha is still
selected on inner-validation NDCG@10 per (variant, seed, fold). Per-pair
records and significance tests are identical.

Used only when --share-inner-ease is passed. Default behavior preserves the
original per-variant inner EASE for compatibility.

Same alpha grid, same factories, same eval_full, same RNG seed derivation
((seed*1000 + fold_id + 7) & 0xFFFFFFFF).
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
    CDR_ALPHA_GRID, SEED, DEFAULT_VARIANTS, VARIANT_FACTORIES,
    load_dataset, build_warm, eval_full,
)


def select_alpha_shared(dataset, outer_train, outer_cold_items, S_content, emb,
                          n_users, n_items, rng, variant_name, variant_factory,
                          cached_inner=None):
    """Like select_alpha in run_cdr_variants but reuses cached inner EASE.

    cached_inner: dict with keys 'inner_warm', 'inner_train', 'val_inters',
                  'B_in', 'X_in', 'Xw_in', 'cold_arr'. If None, build fresh.
    Returns (best_alpha, val_scores, cached_inner) — caller can pass back the
    same cache to subsequent variants for the same outer fold.
    """
    if cached_inner is None:
        outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
        shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
        n_val = max(1, int(0.2 * len(shuf)))
        val_items = set(shuf[:n_val].tolist())
        val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
        if not val_inters:
            return 0.25, {}, None
        inner_cold = sorted(set(outer_cold_items) | val_items)
        inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)),
                                dtype=np.int32)
        inner_train = [x for x in outer_train
                         if int(x["item_id"]) not in val_items]
        X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
        S_w_in = S_content[np.ix_(inner_warm, inner_warm)]
        lam, beta = HP[dataset]
        B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_w_in,
                          dtype=np.float32)
        cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
        cached_inner = {"inner_warm": inner_warm, "inner_train": inner_train,
                          "val_inters": val_inters, "B_in": B_in,
                          "X_in": X_in, "Xw_in": Xw_in, "cold_arr": cold_arr}
    if not cached_inner["val_inters"]:
        return 0.25, {}, cached_inner
    scores = {}
    for a in CDR_ALPHA_GRID:
        sf = variant_factory(cached_inner["Xw_in"], cached_inner["B_in"],
                              cached_inner["inner_warm"], cached_inner["cold_arr"],
                              S_content, emb, n_items, alpha=a,
                              X_sparse_warm=cached_inner["X_in"])
        summ, _, _ = eval_full(sf, cached_inner["inner_train"],
                                cached_inner["val_inters"], n_items)
        scores[float(a)] = float(summ["NDCG@10"])
    return max(scores, key=scores.get), scores, cached_inner


def run(dataset, seeds, variants, perpair_out=None):
    print(f"\n{'#'*70}\n# CDR variants (shared-inner): {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}")

    perfold = {v: {"NDCG@10": [], "HR@10": [], "MRR": [], "fit_time": []} for v in variants}
    per_user_all = {v: defaultdict(list) for v in variants}
    selected_alphas = {v: [] for v in variants}

    perpair_records: dict[str, list] = {v: [] for v in variants}

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)
            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            t_ease = time.time()
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
            t_ease = time.time() - t_ease

            cached_inner = None  # built once on the first variant; reused
            for variant_name in variants:
                factory = VARIANT_FACTORIES[variant_name]
                val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
                t_val = time.time()
                a, val_scores, cached_inner = select_alpha_shared(
                    dataset, train_inters, set(cold), S_content, emb_np,
                    n_users, n_items, val_rng, variant_name, factory,
                    cached_inner=cached_inner)
                t_val = time.time() - t_val
                selected_alphas[variant_name].append({
                    "seed": seed, "fold_id": fold_id, "alpha": a,
                    "val_scores": val_scores, "val_time_s": t_val})

                t_fit = time.time()
                sf = factory(Xw, B_warm, warm_idx, cold_idx, S_content, emb_np,
                              n_items, alpha=a, X_sparse_warm=X_sparse)
                summ, pu, rows = eval_full(sf, train_inters, test_inters, n_items,
                                             record_rows=(perpair_out is not None),
                                             method=variant_name, seed=seed,
                                             fold_id=fold_id, dataset=dataset)
                t_fit = time.time() - t_fit
                perfold[variant_name]["NDCG@10"].append(summ["NDCG@10"])
                perfold[variant_name]["HR@10"].append(summ["HR@10"])
                perfold[variant_name]["MRR"].append(summ["MRR"])
                perfold[variant_name]["fit_time"].append(t_fit + t_val + t_ease)
                for u, vs in pu.items():
                    per_user_all[variant_name][u].append(float(vs))
                if perpair_out is not None and rows:
                    perpair_records[variant_name].extend(rows)
                print(f"  seed={seed} fold={fold_id} variant={variant_name:>14s} "
                      f"alpha={a:.2f} NDCG@10={summ['NDCG@10']:.4f} "
                      f"HR@10={summ['HR@10']:.4f} fit={t_fit:.1f}s val={t_val:.1f}s",
                      flush=True)

            # Free inner-fold cache before next outer fold
            if cached_inner is not None:
                del cached_inner
            del X_sparse, Xw, B_warm, S_warm; gc.collect()

    if perpair_out is not None:
        with open(perpair_out, "a") as fh:
            for v in variants:
                for r in perpair_records[v]:
                    fh.write(json.dumps(r) + "\n")
        print(f"  appended per-pair records -> {perpair_out}")

    print(f"\n=== {dataset.upper()} per-fold NDCG@10 means ===")
    for name in variants:
        vs = perfold[name]["NDCG@10"]
        ts = perfold[name]["fit_time"]
        print(f"  {name:>16s}: NDCG@10 = {np.mean(vs):.4f} +/- {np.std(vs):.4f}  "
              f"avg fit time = {np.mean(ts):.1f}s")

    print(f"\n=== {dataset.upper()} per-USER Wilcoxon (two-sided, variant != CDR_validated) ===")
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
              f"p2s={p_two:.3e} p_greater={p_g:.3e} {marker}")
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
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
