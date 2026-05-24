"""CDR variants: explores alternatives to the production CDR_validated baseline.

Variants implemented (all share Step 1 EASE warm + Step 4 validation-selected
alpha-blend structure of CDR_validated; only the cold-pool predictor or
calibration changes):

  CDR_validated     - production baseline (re-evaluated for paired comparison)
                      cold = alpha * z(content_direct) + (1-alpha) * z(LC2C-Ridge)

  CDR_Q             - replace per-user z-normalization with quantile calibration.
                      Per user, map each cold score to the warm-score quantile
                      at the same rank percentile. Identical alpha-grid /
                      validation protocol.

  CDR_R2            - replace MSE Ridge with weighted Ridge using inverse
                      sqrt(popularity) item weights. Popular warm items get
                      down-weighted so they don't dominate fit; rare warm items
                      drive the SBERT->B mapping for cold extrapolation.

  CDR_K             - Replace linear Ridge with Gaussian RBF kernel regression.
                      Closed-form: alpha = (K + lambda*I)^-1 B_warm.T
                      B_hat_cold = K(SBERT_cold, SBERT_warm) @ alpha
                      With Nystrom approximation when n_warm > 4000 (Books).
                      gamma chosen by median heuristic over pairwise distances.

  CDR_S             - Top-K sparsification: zero all but top-K entries per
                      column of B_hat_cold (LC2C output). K=50.

Eval protocol: identical to run_poc_cdr_books.py (full-catalog, mask training
items, per-(user, target) NDCG@10 / HR@10 / MRR). Same alpha grid, same
validation hold-out logic.

Output:
  _bestrec_run/results_cdr_variants.json     - fold means + per-USER Wilcoxon
  _bestrec_run/results_cdr_variants_perpair_<dataset>.jsonl - per-pair records

Run order: POC Beauty + Fashion first (smallest); only scale to Instruments /
Books if variants survive.
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
from typing import Callable

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

# Variants to evaluate (CDR_validated always included for paired comparison)
DEFAULT_VARIANTS = ["CDR_validated", "CDR_Q", "CDR_R2", "CDR_K", "CDR_S"]


# ---------------------------------------------------------------------------
# Shared utilities (copy of run_poc_cdr_books.py minimal infrastructure)
# ---------------------------------------------------------------------------
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


def _z(x):
    """Per-user z-normalization."""
    m = x.mean(axis=1, keepdims=True)
    s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
    return (x - m) / s


def _quantile_calibrate(cold_scores, warm_scores):
    """For each user (row), map each cold score to the value of the warm
    score at the matching rank percentile.

    cold_scores: (b, n_cold)
    warm_scores: (b, n_warm)
    returns: (b, n_cold) calibrated cold scores

    For each user:
      sort warm scores ascending into warm_sorted (length n_warm)
      sort cold scores ascending; rank percentile p_i = i/(n_cold-1)
      map to warm_sorted at idx round(p_i * (n_warm - 1))

    Equivalently: per user use np.interp:
      sorted_warm = np.sort(warm_scores)
      sorted_cold = np.sort(cold_scores)
      For each cold value v, find its rank in the cold array (0..n_cold-1),
      then take warm_sorted at the same rank percentile.
    """
    b, n_cold = cold_scores.shape
    n_warm = warm_scores.shape[1]
    out = np.empty_like(cold_scores, dtype=np.float32)
    # x positions for cold quantiles
    cold_p = np.linspace(0.0, 1.0, n_cold, dtype=np.float32) if n_cold > 1 else np.array([0.5], dtype=np.float32)
    warm_p = np.linspace(0.0, 1.0, n_warm, dtype=np.float32) if n_warm > 1 else np.array([0.5], dtype=np.float32)
    for k in range(b):
        # sorted warm values (ascending)
        ws = np.sort(warm_scores[k]).astype(np.float32)
        # rank of each cold value within the cold distribution: argsort^-1
        order = np.argsort(cold_scores[k])
        ranks = np.empty(n_cold, dtype=np.int64)
        ranks[order] = np.arange(n_cold, dtype=np.int64)
        # rank percentile in [0, 1]
        if n_cold > 1:
            p = ranks.astype(np.float32) / float(n_cold - 1)
        else:
            p = np.array([0.5], dtype=np.float32)
        # interp warm CDF at percentile p
        out[k] = np.interp(p, warm_p, ws).astype(np.float32)
    return out


# ---------------------------------------------------------------------------
# Cold-score predictors
# ---------------------------------------------------------------------------

def _ridge_b_hat(SBERT_w, SBERT_c, B_warm, alpha=1.0):
    """Linear Ridge: SBERT -> B_warm.T."""
    reg = Ridge(alpha=alpha); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    return B_hat_cold


def _weighted_ridge_b_hat(SBERT_w, SBERT_c, B_warm, X_sparse_warm, alpha=1.0):
    """Weighted Ridge with inverse sqrt(popularity) sample weights.

    Popular warm items get downweighted in the fit.
    sample_weight has shape (n_warm,).
    """
    pop = np.asarray(X_sparse_warm.sum(axis=0)).flatten().astype(np.float32)
    # weights = 1 / sqrt(pop + 1) -- rare items get more weight in the fit
    w = 1.0 / np.sqrt(pop + 1.0)
    # normalize so weights have mean 1 (preserves regularization scale)
    w = w / np.maximum(w.mean(), 1e-8)
    reg = Ridge(alpha=alpha)
    reg.fit(SBERT_w, B_warm.T.astype(np.float32), sample_weight=w.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    return B_hat_cold


def _kernel_ridge_b_hat(SBERT_w, SBERT_c, B_warm, lam_kernel=1.0,
                         nystrom_anchors=None, rng=None):
    """Gaussian RBF kernel ridge: B_hat_cold = K(c, w) (K(w,w) + lam I)^-1 B_warm.T

    K(x, y) = exp(-gamma * ||x - y||^2). gamma via median heuristic.

    If n_warm > nystrom_anchors, use Nystrom approximation:
      sample `nystrom_anchors` anchor rows from warm
      K_wa = kernel(warm, anchors), K_aa = kernel(anchors, anchors)
      train mapping: alpha_a = (K_aa + lam I)^-1 K_aw B_warm.T
      predict: B_hat_cold = K(c, a) @ alpha_a
    """
    n_warm, d = SBERT_w.shape

    # Median heuristic for gamma: use a sample of pairwise distances
    rng_s = rng if rng is not None else np.random.RandomState(0)
    sample_n = min(500, n_warm)
    idx = rng_s.choice(n_warm, sample_n, replace=False)
    Xs = SBERT_w[idx]
    # pairwise sq distances
    sq_diff = np.sum(Xs * Xs, axis=1, keepdims=True) + \
              np.sum(Xs * Xs, axis=1, keepdims=True).T - 2 * Xs @ Xs.T
    sq_diff = np.maximum(sq_diff, 0.0)
    iu = np.triu_indices(sample_n, k=1)
    med_sq = float(np.median(sq_diff[iu]))
    gamma = 1.0 / max(med_sq, 1e-8)

    def _rbf(A, B):
        # A: (na, d), B: (nb, d) -> K (na, nb)
        AA = np.sum(A * A, axis=1, keepdims=True)
        BB = np.sum(B * B, axis=1, keepdims=True).T
        D2 = AA + BB - 2 * (A @ B.T)
        D2 = np.maximum(D2, 0.0)
        return np.exp(-gamma * D2, dtype=np.float32).astype(np.float32)

    if nystrom_anchors is not None and n_warm > nystrom_anchors:
        # Nystrom
        a_idx = rng_s.choice(n_warm, nystrom_anchors, replace=False)
        SBERT_a = SBERT_w[a_idx]
        K_wa = _rbf(SBERT_w, SBERT_a)            # (n_warm, n_a)
        K_aa = _rbf(SBERT_a, SBERT_a)            # (n_a, n_a)
        # solve (K_aa + lam I) alpha_a = K_wa.T B_warm.T (over-determined LS via normal eqns)
        # alpha_a has shape (n_a, n_warm); B_warm.T is (n_warm, n_warm)
        # Use full Nystrom regression: alpha_a = (K_wa.T K_wa + lam K_aa)^-1 K_wa.T B_warm.T
        LHS = (K_wa.T @ K_wa).astype(np.float32) + lam_kernel * K_aa
        RHS = (K_wa.T @ B_warm.T).astype(np.float32)
        try:
            alpha_a = np.linalg.solve(LHS, RHS).astype(np.float32)
        except np.linalg.LinAlgError:
            alpha_a = np.linalg.lstsq(LHS, RHS, rcond=None)[0].astype(np.float32)
        K_ca = _rbf(SBERT_c, SBERT_a)
        B_hat_cold_T = (K_ca @ alpha_a).astype(np.float32)   # (n_cold, n_warm)
        return B_hat_cold_T.T.astype(np.float32)
    else:
        # Exact kernel
        K_ww = _rbf(SBERT_w, SBERT_w)
        K_ww[np.arange(n_warm), np.arange(n_warm)] += lam_kernel
        # alpha = (K + lam I)^-1 B_warm.T  -> (n_warm, n_warm)
        try:
            alpha_mat = np.linalg.solve(K_ww, B_warm.T.astype(np.float32)).astype(np.float32)
        except np.linalg.LinAlgError:
            alpha_mat = np.linalg.lstsq(K_ww, B_warm.T.astype(np.float32), rcond=None)[0].astype(np.float32)
        K_cw = _rbf(SBERT_c, SBERT_w)
        B_hat_cold_T = (K_cw @ alpha_mat).astype(np.float32)  # (n_cold, n_warm)
        return B_hat_cold_T.T.astype(np.float32)


def _topk_sparsify(B_hat_cold, K=50):
    """Zero all but top-K (by magnitude) entries per column of B_hat_cold."""
    n_warm, n_cold = B_hat_cold.shape
    K_eff = min(K, n_warm)
    if K_eff >= n_warm:
        return B_hat_cold
    abs_vals = np.abs(B_hat_cold)
    # partition along axis 0 per column
    part = np.partition(abs_vals, n_warm - K_eff, axis=0)
    thresh = part[n_warm - K_eff, :][None, :]
    mask = abs_vals >= thresh
    out = np.where(mask, B_hat_cold, 0.0).astype(np.float32)
    return out


# ---------------------------------------------------------------------------
# Scorer factories
# ---------------------------------------------------------------------------

def make_score_cdr_validated(Xw, B_warm, warm_indices, cold_indices, S_content,
                              emb, n_items, alpha, X_sparse_warm=None):
    """Production CDR_validated. Re-implemented for paired comparison."""
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    B_hat_cold = _ridge_b_hat(SBERT_w, SBERT_c, B_warm)
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


def make_score_cdr_Q(Xw, B_warm, warm_indices, cold_indices, S_content,
                      emb, n_items, alpha, X_sparse_warm=None):
    """CDR with quantile calibration replacing per-user z-norm.

    For each user, map each cold score (cd + lc, blended after z) to a
    warm-score quantile. We blend in z-space first to keep the alpha
    interpretable, then map the blended cold scores onto the warm
    distribution per user.
    """
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    B_hat_cold = _ridge_b_hat(SBERT_w, SBERT_c, B_warm)
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def f(uids):
        warm_scores = Xw[uids] @ B_warm                    # (b, n_warm)
        cd_cold = _z(Xw[uids] @ S_w_c)                     # (b, n_cold) in z-space
        lc_cold = _z(Xw[uids] @ B_hat_cold)                # (b, n_cold) in z-space
        cold_blend = alpha * cd_cold + (1.0 - alpha) * lc_cold  # (b, n_cold)
        # Now quantile-map cold_blend to warm distribution per user
        cold_cal = _quantile_calibrate(cold_blend, warm_scores)
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_cal
        return out
    return f


def make_score_cdr_R2(Xw, B_warm, warm_indices, cold_indices, S_content,
                       emb, n_items, alpha, X_sparse_warm):
    """CDR with weighted Ridge (inverse sqrt popularity) for LC2C step."""
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    B_hat_cold = _weighted_ridge_b_hat(SBERT_w, SBERT_c, B_warm, X_sparse_warm)
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


def make_score_cdr_K(Xw, B_warm, warm_indices, cold_indices, S_content,
                      emb, n_items, alpha, X_sparse_warm=None,
                      nystrom_anchors=1000, rng_seed=0):
    """CDR with Gaussian RBF kernel ridge for LC2C step."""
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    rng = np.random.RandomState(rng_seed)
    n_warm = SBERT_w.shape[0]
    # Use Nystrom for n_warm > 4000 to fit in memory / compute
    anchors_k = nystrom_anchors if n_warm > 4000 else None
    B_hat_cold = _kernel_ridge_b_hat(SBERT_w, SBERT_c, B_warm,
                                       lam_kernel=1.0,
                                       nystrom_anchors=anchors_k, rng=rng)
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


def make_score_cdr_S(Xw, B_warm, warm_indices, cold_indices, S_content,
                      emb, n_items, alpha, X_sparse_warm=None, K_sparse=50):
    """CDR with top-K sparsification of LC2C B_hat_cold columns."""
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    B_hat_cold = _ridge_b_hat(SBERT_w, SBERT_c, B_warm)
    B_hat_cold = _topk_sparsify(B_hat_cold, K=K_sparse)
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


VARIANT_FACTORIES = {
    "CDR_validated": make_score_cdr_validated,
    "CDR_Q": make_score_cdr_Q,
    "CDR_R2": make_score_cdr_R2,
    "CDR_K": make_score_cdr_K,
    "CDR_S": make_score_cdr_S,
}


# ---------------------------------------------------------------------------
# Evaluation (full-catalog, same as production)
# ---------------------------------------------------------------------------
def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192,
              record_rows=False, method=None, seed=None, fold_id=None,
              dataset=None):
    ut = defaultdict(set); uts = defaultdict(list)
    for x in train_inters: ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters: uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, hr, rr = [], [], []
    per_user_ndcg = defaultdict(list)
    rows = []
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
                r_ = 1.0 / (r0 + 1)
                ndcg.append(n_); hr.append(h_); rr.append(r_)
                per_user_ndcg[int(u)].append(n_)
                if record_rows:
                    rows.append({"candidate_scope": "full_catalog",
                                 "dataset": dataset, "fold_id": fold_id,
                                 "hr10": float(h_), "method": method,
                                 "ndcg10": float(n_), "rr": float(r_),
                                 "seed": seed, "target_item_id": int(tgt),
                                 "user_id": int(u)})
    summary = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10":   float(np.mean(hr))   if hr else 0.0,
        "MRR":     float(np.mean(rr))   if rr else 0.0,
        "n_eval":  len(ndcg),
    }
    pu = {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}
    return summary, pu, rows


# ---------------------------------------------------------------------------
# Inner-validation alpha selection (per-variant, mirrors run_poc_cdr_books)
# ---------------------------------------------------------------------------
def select_alpha(dataset, outer_train, outer_cold_items, S_content, emb,
                  n_users, n_items, rng, variant_name, variant_factory,
                  factory_kwargs=None):
    factory_kwargs = factory_kwargs or {}
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
        sf = variant_factory(Xw_in, B_in, inner_warm, cold_arr, S_content,
                              emb, n_items, alpha=a, X_sparse_warm=X_in,
                              **factory_kwargs)
        summ, _, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[float(a)] = float(summ["NDCG@10"])
    del X_in, Xw_in, B_in; gc.collect()
    return max(scores, key=scores.get), scores


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def run(dataset, seeds, variants, perpair_out=None):
    print(f"\n{'#'*70}\n# CDR variants: {dataset.upper()}\n{'#'*70}")
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

            for variant_name in variants:
                factory = VARIANT_FACTORIES[variant_name]
                # alpha selection on inner validation
                val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
                t_val = time.time()
                a, val_scores = select_alpha(dataset, train_inters, set(cold),
                                              S_content, emb_np, n_users, n_items,
                                              val_rng, variant_name, factory)
                t_val = time.time() - t_val
                selected_alphas[variant_name].append({
                    "seed": seed, "fold_id": fold_id, "alpha": a,
                    "val_scores": val_scores, "val_time_s": t_val})

                # final evaluation
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
                      f"HR@10={summ['HR@10']:.4f} fit={t_fit:.1f}s val={t_val:.1f}s")
            del X_sparse, Xw, B_warm, S_warm; gc.collect()

    if perpair_out is not None:
        # Append-write per-pair records: jsonl
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

    # Per-USER paired Wilcoxon vs CDR_validated
    print(f"\n=== {dataset.upper()} per-USER Wilcoxon (two-sided, variant != CDR_validated) ===")
    def _pu_mean(name):
        return {u: float(np.mean(vs)) for u, vs in per_user_all[name].items()}
    cdr_pu = _pu_mean("CDR_validated") if "CDR_validated" in per_user_all else {}
    wilcox = {}
    pvalues = {}
    for vname in variants:
        if vname == "CDR_validated":
            continue
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

    # Holm correction on two-sided p-values across non-CDR variants
    sorted_v = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(sorted_v)
    holm = {}
    for rank, (vn, p) in enumerate(sorted_v):
        holm_p = min(1.0, p * (m - rank))
        holm[vn] = holm_p
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
    ap.add_argument("--perpair", action="store_true",
                     help="Write per-pair JSONL records per dataset.")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    out = Path(__file__).parent / args.out
    if out.exists():
        try:
            payload = json.load(open(out))
        except Exception:
            payload = {"datasets": {}}
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
            # clear any prior file (we re-write)
            open(perpair_out, "w").close()
        if "datasets" not in payload: payload["datasets"] = {}
        payload["datasets"][ds] = run(ds, seeds, variants, perpair_out=perpair_out)
        with open(out, "w") as f: json.dump(payload, f, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
