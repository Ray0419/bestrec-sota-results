"""Slimmer POC: only the production CDR_validated variant + fair-baseline
diagnostic + LC2C V2 baseline, on Books. Designed to finish in ~30 min.

Same algorithm as run_poc_new_coldstart.py::make_cdr_blend with
validation-selected alpha, but without the dozen exploratory variants
that made the full POC take hours on Books.
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
        if p is None: continue
        rows.append(int(x["user_id"])); cols.append(p)
    X_sparse = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)),
                           shape=(n_users, len(warm_indices)))
    return X_sparse, X_sparse.toarray().astype(np.float32)


def make_score_cdr(Xw, B_warm, warm_indices, cold_indices, S_content, emb, n_items, alpha):
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def _z(x):
        m = x.mean(axis=1, keepdims=True); s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
        return (x - m) / s
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


def make_score_fair_baseline(Xw, B_warm, warm_indices, cold_indices, S_content, n_items):
    """Warm via EASE, cold via raw content_direct."""
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def f(uids):
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = Xw[uids] @ B_warm
        out[:, cold_indices] = Xw[uids] @ S_w_c
        return out
    return f


def make_score_lc2c_v2(Xw, B_warm, warm_indices, cold_indices, emb, n_items):
    """Round-3/4 LC2C V2 baseline (warm via EASE, cold via Ridge-predicted B)."""
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    def f(uids):
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = Xw[uids] @ B_warm
        out[:, cold_indices] = Xw[uids] @ B_hat
        return out
    return f


def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192):
    ut = defaultdict(set); uts = defaultdict(list)
    for x in train_inters: ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters: uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, per_user_ndcg = [], defaultdict(list)
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
                ndcg.append(n_); per_user_ndcg[int(u)].append(n_)
    return float(np.mean(ndcg)) if ndcg else 0.0, {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}


def select_alpha(dataset, outer_train, outer_cold_items, S_content, emb, n_users, n_items, rng):
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters: return 0.25, {}
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
        sf = make_score_cdr(Xw_in, B_in, inner_warm, cold_arr, S_content,
                              emb if isinstance(emb, np.ndarray) else emb.cpu().numpy().astype(np.float32),
                              n_items, alpha=a)
        m, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[float(a)] = m
    del X_in, Xw_in, B_in; gc.collect()
    return max(scores, key=scores.get), scores


def run(dataset, seeds):
    print(f"\n{'#'*70}\n# CDR POC: {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}")

    perfold = {"CDR_validated": [], "FAIR_easewarm_cdcold_raw": [], "LC2C_V2": []}
    per_user_all = {"CDR_validated": defaultdict(list),
                    "FAIR_easewarm_cdcold_raw": defaultdict(list),
                    "LC2C_V2": defaultdict(list)}
    selected_alphas = []

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

            # inner-validation alpha selection
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            a, val_scores = select_alpha(dataset, train_inters, set(cold), S_content,
                                            emb_np, n_users, n_items, val_rng)
            selected_alphas.append({"seed": seed, "fold_id": fold_id, "alpha": a,
                                      "val_scores": val_scores})

            # final evaluation
            sf_cdr = make_score_cdr(Xw, B_warm, warm_idx, cold_idx, S_content, emb_np, n_items, alpha=a)
            sf_fair = make_score_fair_baseline(Xw, B_warm, warm_idx, cold_idx, S_content, n_items)
            sf_lc = make_score_lc2c_v2(Xw, B_warm, warm_idx, cold_idx, emb_np, n_items)

            m, pu = eval_full(sf_cdr, train_inters, test_inters, n_items)
            perfold["CDR_validated"].append(m)
            for u, vs in pu.items(): per_user_all["CDR_validated"][u].extend([vs])

            m_f, pu_f = eval_full(sf_fair, train_inters, test_inters, n_items)
            perfold["FAIR_easewarm_cdcold_raw"].append(m_f)
            for u, vs in pu_f.items(): per_user_all["FAIR_easewarm_cdcold_raw"][u].extend([vs])

            m_l, pu_l = eval_full(sf_lc, train_inters, test_inters, n_items)
            perfold["LC2C_V2"].append(m_l)
            for u, vs in pu_l.items(): per_user_all["LC2C_V2"][u].extend([vs])

            dt = time.time() - t_fold
            print(f"  seed={seed} fold={fold_id} alpha={a:.2f}  CDR_validated={m:.4f}  "
                  f"FAIR={m_f:.4f}  LC2C_V2={m_l:.4f}  [{dt:.1f}s]")
            del X_sparse, Xw, B_warm, S_warm; gc.collect()

    print(f"\n=== {dataset.upper()} fold means ===")
    for name, vs in perfold.items():
        print(f"  {name:>26}: {np.mean(vs):.4f} +/- {np.std(vs):.4f}")

    print(f"\n=== {dataset.upper()} per-USER Wilcoxon (one-sided, target > baseline) ===")
    def _pu_mean(method):
        return {u: float(np.mean(vs)) for u, vs in per_user_all[method].items()}
    cand = _pu_mean("CDR_validated")
    wilcox = {}
    for base in ["FAIR_easewarm_cdcold_raw", "LC2C_V2"]:
        bpu = _pu_mean(base)
        common = sorted(set(cand) & set(bpu))
        diffs = np.array([cand[u] - bpu[u] for u in common])
        if np.allclose(diffs, 0): p = 1.0
        else: p = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
        marker = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
        wilcox[base] = {"n_users": len(common),
                          "cand_mean": float(np.mean([cand[u] for u in common])),
                          "base_mean": float(np.mean([bpu[u] for u in common])),
                          "delta": float(np.mean(diffs)),
                          "p_raw": p, "marker": marker}
        print(f"  CDR_validated > {base:<28}: n={len(common):>6} cand={wilcox[base]['cand_mean']:.4f} "
              f"base={wilcox[base]['base_mean']:.4f} delta={wilcox[base]['delta']:+.4f} p={p:.3e} {marker}")
    return {"perfold": {k: list(map(float, v)) for k, v in perfold.items()},
            "selected_alphas": selected_alphas,
            "wilcoxon_cdr_validated": wilcox}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["books"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--out", default="results_poc_cdr.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    out = Path(__file__).parent / args.out
    if out.exists():
        try: payload = json.load(open(out))
        except Exception: payload = {"datasets": {}}
    else:
        payload = {"schema_version": 1, "candidate_scope": "full_catalog",
                    "status": "proof_of_concept_cdr", "datasets": {}}
    payload["seeds"] = seeds
    for ds in args.datasets:
        payload["datasets"][ds] = run(ds, seeds)
        with open(out, "w") as f: json.dump(payload, f, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
