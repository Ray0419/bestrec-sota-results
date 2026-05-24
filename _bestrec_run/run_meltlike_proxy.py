"""MELT-inspired closed-form proxy (Kim et al., SIGIR 2023).

Faithful MELT (Mutually Enhanced Learning for Long-Tail Recommendation) uses
a transformer with joint head-tail dual mutual training. This script ships a
DOCUMENTED CLOSED-FORM PROXY that captures MELT's "transfer head -> tail"
idea in a single closed-form pass: tail-favoring content kNN combined with a
content-derived head-popularity boost for cold items whose nearest warm
neighbours are popular. It is NOT a faithful reproduction.

Fidelity tag:
    meltinspired_tail_favoring_content_knn_not_official_melt

Algorithm:

  1. Compute warm-item interaction count pop[w] for each warm item.
  2. Tail weight  w[w] = 1 / (1 + log(1 + pop[w]))  in [~0.06, 1.0] for
     typical Amazon kcore data; favors tail warm items.
  3. Tail-favoring content kNN (cold scoring):
        S_w_c    = cosine(SBERT_w, SBERT_c)                  (n_warm, n_cold)
        warm_w   = w[w]                                       (n_warm,)
        weighted = S_w_c * warm_w[:, None]                    (n_warm, n_cold)
     For each cold item j, a pop-neighbor boost picks up the average
     popularity of j's top-K warm neighbours, normalised to [0, 1].
        boost[j] = mean(pop_norm[top-K warm neighbours of cold j])
     (This emulates MELT's transfer-from-head-to-tail: cold items whose
     content neighbourhood already contains popular warm items get the
     gentle popularity bump.)
        score_cold(u, j) = (Xw[u] @ weighted)[j] * (1 + gamma * boost[j])
  4. Per-user z-normalise the cold scores (same trick CDR uses) so they're
     comparable to warm EASE scores in the full catalog.
  5. Warm head: EASE (regularised closed form), same as CDR_validated /
     FAIR baseline.
  6. Final score for user u over all items:
        out[u, warm] = Xw[u] @ B_warm
        out[u, cold] = zscore_per_user(weighted_cold) * (1 + gamma * boost)

Eval: full-catalog cold-item (run_poc_cdr_books.eval_full pattern), one
seed on books and three seeds on beauty/fashion/instruments.

Usage:
    _bestrec_run/.venv/Scripts/python _bestrec_run/run_meltlike_proxy.py \
        beauty fashion instruments books \
        --seeds 20260521,20260522,20260523

References:
- Kim et al., SIGIR 2023, "Mutually Enhanced Learning for Long-Tail
  Recommendation" (MELT).
- RESEARCH_MELT or the plan file curried-fluttering-salamander.md (gap 8).
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
from scipy.stats import wilcoxon

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex


# ---------- Hyperparameters ----------
TOP_K_NBRS = 20      # for pop-neighbor boost
GAMMA = 0.3          # boost magnitude (cold items in popular neighbourhoods get a +30% bump cap)
DEFAULT_SEEDS = [20260521, 20260522, 20260523]


def load_dataset(dataset: str):
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], DATASET_KCORE[dataset])
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{DATASET_KCORE[dataset]}_dedup.pt"
    emb = torch.load(title_path, weights_only=True)
    emb_np = emb.cpu().numpy().astype(np.float32) if hasattr(emb, "cpu") else np.asarray(emb, dtype=np.float32)
    return interactions, n_users, n_items, emb_np


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


def _zscore_rows(x: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    m = x.mean(axis=1, keepdims=True)
    s = np.maximum(x.std(axis=1, keepdims=True), eps)
    return (x - m) / s


def make_score_meltlike_proxy(
    Xw: np.ndarray,
    B_warm: np.ndarray,
    warm_indices: np.ndarray,
    cold_indices: np.ndarray,
    S_content: np.ndarray,
    n_items: int,
    *,
    top_k_nbrs: int = TOP_K_NBRS,
    gamma: float = GAMMA,
):
    """Build the MELT-inspired score function.

    Inputs (warm_indices, cold_indices) are GLOBAL item ids. S_content is the
    full n_items x n_items cosine matrix (zero-diagonal).
    """
    n_warm = len(warm_indices)
    n_cold = len(cold_indices)

    # Step 1: warm popularity (interaction count per warm item).
    pop_warm = Xw.sum(axis=0).astype(np.float32)   # (n_warm,)

    # Step 2: tail weight on warm items, favours rare items.
    tail_w = (1.0 / (1.0 + np.log(1.0 + pop_warm))).astype(np.float32)   # (n_warm,)

    # Step 3a: content sim between warm and cold items.
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)  # (n_warm, n_cold)
    weighted_w_c = S_w_c * tail_w[:, None]                                    # (n_warm, n_cold)

    # Step 3b: pop-neighbor boost per cold item.
    # For each cold j pick top_k_nbrs warm neighbours by raw cosine,
    # take the mean of their (popularity-normalised) pop and use that as a
    # gentle (1 + gamma * boost) multiplier.
    if pop_warm.max() > 0:
        pop_norm = pop_warm / max(float(pop_warm.max()), 1.0)
    else:
        pop_norm = np.zeros_like(pop_warm, dtype=np.float32)
    k_use = int(min(top_k_nbrs, max(1, n_warm)))
    # argpartition is O(n_warm) per cold item; n_cold * n_warm operations is fine.
    boost_cold = np.zeros(n_cold, dtype=np.float32)
    if k_use > 0 and n_warm > 0:
        # Process in batches over cold to limit memory of the partition arrays.
        batch = max(1, min(2048, n_cold))
        for s in range(0, n_cold, batch):
            sl = slice(s, s + batch)
            S_blk = S_w_c[:, sl]                         # (n_warm, b)
            # Take top-k_use neighbours per cold column.
            if k_use < n_warm:
                top_idx = np.argpartition(-S_blk, kth=k_use - 1, axis=0)[:k_use]   # (k, b)
                boost_cold[sl] = pop_norm[top_idx].mean(axis=0).astype(np.float32)
            else:
                boost_cold[sl] = pop_norm.mean()
    boost_mult = (1.0 + gamma * boost_cold).astype(np.float32)                # (n_cold,)

    def score(user_ids: np.ndarray) -> np.ndarray:
        out = np.empty((len(user_ids), n_items), dtype=np.float32)
        # Warm side: EASE.
        out[:, warm_indices] = Xw[user_ids] @ B_warm
        # Cold side: tail-weighted content kNN with pop-neighbor boost, then z-norm per user.
        cold_raw = Xw[user_ids] @ weighted_w_c                                # (B, n_cold)
        cold_boosted = cold_raw * boost_mult[None, :]
        cold_z = _zscore_rows(cold_boosted)
        out[:, cold_indices] = cold_z
        return out

    diag = {
        "n_warm": int(n_warm),
        "n_cold": int(n_cold),
        "pop_warm_mean": float(pop_warm.mean()),
        "pop_warm_max": float(pop_warm.max()),
        "tail_w_min": float(tail_w.min()),
        "tail_w_max": float(tail_w.max()),
        "tail_w_mean": float(tail_w.mean()),
        "boost_cold_min": float(boost_cold.min()),
        "boost_cold_max": float(boost_cold.max()),
        "boost_cold_mean": float(boost_cold.mean()),
        "top_k_nbrs": int(k_use),
        "gamma": float(gamma),
    }
    return score, diag


def eval_full(score_fn, train_inters, test_inters, n_items, batch_size: int = 192):
    """Full-catalog cold-item eval — same pattern as run_poc_cdr_books.eval_full
    but also returning per-pair (u, tgt, n, h, rr) records for jsonl."""
    ut = defaultdict(set)
    uts = defaultdict(list)
    for x in train_inters:
        ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters:
        uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, hr, rr = [], [], []
    per_user_ndcg = defaultdict(list)
    per_pair_records = []
    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        for k, u in enumerate(batch):
            if ut[u]:
                scores[k, list(ut[u])] = -np.inf
            for tgt in uts[u]:
                ts = scores[k, tgt]
                r0 = int((scores[k] > ts).sum())
                n_ = 1.0 / math.log2(r0 + 2) if r0 < TOP_K else 0.0
                h_ = 1.0 if r0 < TOP_K else 0.0
                rr_ = 1.0 / (r0 + 1)
                ndcg.append(n_)
                hr.append(h_)
                rr.append(rr_)
                per_user_ndcg[int(u)].append(n_)
                per_pair_records.append((int(u), int(tgt), float(n_), float(h_), float(rr_)))
    metrics = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(ndcg),
    }
    return metrics, per_user_ndcg, per_pair_records


def run(dataset: str, seeds: list[int], perpair_path: Path) -> dict:
    print(f"\n{'#' * 70}\n# MELT-inspired proxy: {dataset.upper()}\n{'#' * 70}")
    interactions, n_users, n_items, emb_np = load_dataset(dataset)
    S_content = content_sim_matrix(emb_np, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}")

    perfold = []   # list of {seed, fold_id, NDCG@10, HR@10, MRR, n_eval, diag}
    per_user_all = defaultdict(list)

    perpair_path.parent.mkdir(parents=True, exist_ok=True)
    with open(perpair_path, "w") as f:
        pass

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t_fold = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)

            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)

            sf, diag = make_score_meltlike_proxy(
                Xw, B_warm, warm_idx, cold_idx, S_content, n_items,
                top_k_nbrs=TOP_K_NBRS, gamma=GAMMA,
            )
            metrics, per_user_ndcg, records = eval_full(sf, train_inters, test_inters, n_items)

            with open(perpair_path, "a") as f:
                for u, tgt, nd, h_, rr_ in records:
                    f.write(json.dumps({
                        "dataset": dataset,
                        "seed": int(seed),
                        "fold": int(fold_id),
                        "method": "meltlike_proxy",
                        "user_id": int(u),
                        "target_item_id": int(tgt),
                        "candidate_scope": "full_catalog",
                        "ndcg10": float(nd),
                        "hr10": float(h_),
                        "rr": float(rr_),
                    }) + "\n")

            for u, vs in per_user_ndcg.items():
                per_user_all[int(u)].extend(vs)

            row = {
                "seed": int(seed),
                "fold_id": int(fold_id),
                **{k: v for k, v in metrics.items()},
                "diag": diag,
                "fold_seconds": float(time.time() - t_fold),
            }
            perfold.append(row)
            print(f"    seed={seed} fold={fold_id}  NDCG@10={metrics['NDCG@10']:.4f}  "
                  f"HR@10={metrics['HR@10']:.4f}  MRR={metrics['MRR']:.4f}  "
                  f"n_eval={metrics['n_eval']}  [{row['fold_seconds']:.1f}s]")
            del X_sparse, Xw, B_warm, S_warm
            gc.collect()

    nd_arr = [r["NDCG@10"] for r in perfold]
    hr_arr = [r["HR@10"] for r in perfold]
    mrr_arr = [r["MRR"] for r in perfold]
    means = {
        "NDCG@10_mean": float(np.mean(nd_arr)),
        "NDCG@10_std": float(np.std(nd_arr)),
        "HR@10_mean": float(np.mean(hr_arr)),
        "HR@10_std": float(np.std(hr_arr)),
        "MRR_mean": float(np.mean(mrr_arr)),
        "MRR_std": float(np.std(mrr_arr)),
        "n_folds": len(perfold),
    }
    # E2E recipe key: also expose mean_ndcg10 (alongside NDCG@10_mean) so the
    # validator's `v.get('mean_ndcg10') or v.get('NDCG@10_mean')` accepts either.
    means["mean_ndcg10"] = means["NDCG@10_mean"]
    means["std_ndcg10"] = means["NDCG@10_std"]
    print(f"\n  === {dataset.upper()} summary over {len(perfold)} folds ===")
    print(f"    NDCG@10 = {means['NDCG@10_mean']:.4f} +/- {means['NDCG@10_std']:.4f}")
    print(f"    HR@10   = {means['HR@10_mean']:.4f} +/- {means['HR@10_std']:.4f}")
    print(f"    MRR     = {means['MRR_mean']:.4f} +/- {means['MRR_std']:.4f}")

    per_user_mean = {u: float(np.mean(vs)) for u, vs in per_user_all.items()}
    return {
        "perfold": perfold,
        "means": means,
        "mean_ndcg10": means["NDCG@10_mean"],   # top-level for the E2E recipe
        "std_ndcg10": means["NDCG@10_std"],
        "per_user_mean_ndcg10": per_user_mean,
        "n_users_eval": len(per_user_mean),
        "fidelity": "meltinspired_tail_favoring_content_knn_not_official_melt",
        "hp": {"top_k_nbrs": TOP_K_NBRS, "gamma": GAMMA},
    }


def _holm(pvals: dict[str, float]) -> dict[str, float]:
    if not pvals:
        return {}
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    holm = {}
    running_max = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running_max = max(running_max, adj)
        holm[name] = running_max
    return holm


def compare_to_cdr_validated(payload: dict) -> dict:
    """Per-user paired Wilcoxon vs CDR_validated baseline (if perpair file exists)."""
    here = Path(__file__).parent
    out = {}
    for ds, info in payload["datasets"].items():
        per_user_target = {int(k): float(v) for k, v in info.get("per_user_mean_ndcg10", {}).items()}
        cmp = {
            "meltlike_ndcg10_mean": info["means"]["NDCG@10_mean"],
            "meltlike_ndcg10_std": info["means"]["NDCG@10_std"],
        }
        # CDR fold-mean comparison
        cdr_path = here / "results_cdr_cl_cdr_validated_baseline.json"
        if cdr_path.exists():
            try:
                cdr_data = json.load(open(cdr_path))
                cdr_ds = cdr_data.get("datasets", {}).get(ds, {})
                if cdr_ds:
                    cmp["CDR_validated_baseline"] = {
                        "cdr_ndcg10_mean": float(cdr_ds.get("mean_ndcg10", 0.0)),
                        "cdr_ndcg10_std": float(cdr_ds.get("std_ndcg10", 0.0)),
                        "delta_mean": (info["means"]["NDCG@10_mean"] - float(cdr_ds.get("mean_ndcg10", 0.0))),
                    }
                    cdr_user = {int(k): float(v) for k, v in cdr_ds.get("per_user_ndcg10", {}).items()}
                    common = sorted(set(per_user_target) & set(cdr_user))
                    if common:
                        diffs = np.array([per_user_target[u] - cdr_user[u] for u in common])
                        if np.allclose(diffs, 0):
                            p_raw = 1.0
                        else:
                            p_raw = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
                        cmp["CDR_validated_baseline"].update({
                            "n_users_paired": int(len(common)),
                            "meltlike_user_mean": float(np.mean([per_user_target[u] for u in common])),
                            "cdr_user_mean": float(np.mean([cdr_user[u] for u in common])),
                            "delta_user_mean": float(np.mean(diffs)),
                            "p_raw_one_sided_greater": float(p_raw),
                        })
            except Exception as exc:
                cmp["CDR_validated_baseline_load_error"] = str(exc)
        out[ds] = cmp
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS))
    ap.add_argument("--out", default="results_meltlike_proxy.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    here = Path(__file__).parent
    out_path = here / args.out
    if out_path.exists():
        try:
            payload = json.load(open(out_path))
        except Exception:
            payload = {}
    else:
        payload = {}
    payload.setdefault("schema_version", 1)
    payload.setdefault("status", "meltinspired_proxy_complete")
    payload["fidelity"] = "meltinspired_tail_favoring_content_knn_not_official_melt"
    payload["candidate_scope"] = "full_catalog"
    payload["seeds"] = seeds
    payload["hp"] = {"top_k_nbrs": TOP_K_NBRS, "gamma": GAMMA}
    payload.setdefault("datasets", {})

    for ds in args.datasets:
        perpair_path = here / f"results_meltlike_proxy_perpair_{ds}.jsonl"
        per_ds_seeds = seeds
        # Books: single seed by default (compute budget) unless overridden.
        if ds == "books" and len(seeds) > 1 and not os.environ.get("MELTLIKE_BOOKS_ALL_SEEDS"):
            per_ds_seeds = [seeds[0]]
            print(f"  [books] using single seed {per_ds_seeds[0]} per budget; "
                  f"set MELTLIKE_BOOKS_ALL_SEEDS=1 to override")
        payload["datasets"][ds] = run(ds, per_ds_seeds, perpair_path)
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)

    payload["baseline_comparisons"] = compare_to_cdr_validated(payload)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
