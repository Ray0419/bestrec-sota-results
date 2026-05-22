"""Proof of concept: new closed-form cold-item algorithms targeting the
full-catalog regime where LC2C/LC2C++ lose to content_direct.

Diagnosis (from the round-5 confirmatory run):
  - content_direct(u, j) = sum_w in user_history of cos(SBERT_w, SBERT_j)
    wins by 3 to 16x on full-catalog cold-item ranking.
  - LC2C V2 trains a Ridge map W: SBERT -> B_warm.T, then predicts
    B_hat[:, j_cold] = SBERT_cold[j] @ W.T. The predicted column is too
    smooth/flat compared to the sharper raw content cosine, so cold scores
    sit below warm scores in the full catalog and rank poorly.

Hypotheses tested here (closed form, no neural training):

  CD_pow_T          - content_direct with a sharper kernel:
                      score(u,j) = sum_w in hist of max(cos,0)**T
                      Hypothesis: a sharper kernel separates similar from
                      dissimilar items more strongly under full catalog.

  CD_topk           - top-K per cold item:
                      score(u,j) = sum_{w in user_history AND in top-K of j}
                      Hypothesis: only the few most similar user items matter.

  CWA_B_pow         - content weighted aggregation of B-columns
                      (replaces LC2C's Ridge with a kernel-smoothed nearest
                       neighbor in SBERT space using actual warm B columns):
                      B_hat[:,j_cold] = sum_w (cos+)**p . B[:,w] / Z
                      Hypothesis: preserves B_warm sharpness lost by Ridge.

  PZC_LC2C          - per-user z-score calibration of LC2C cold scores so
                      they share the per-user warm-score distribution before
                      the full-catalog rank is computed.
                      Hypothesis: fixes the magnitude bias only.

  CDR_blend         - content_direct + small calibrated LC2C residual,
                      with a single global weight alpha learned on inner
                      validation. The fusion search includes alpha = 0
                      (pure content_direct) so the variant cannot lose.
                      Hypothesis: any residual signal LC2C contributes
                      survives on top of the dominant content_direct.

Methodology:
  - Same protocol as run_all_confirmatory.py::eval_full_catalog (full catalog
    candidate set, mask only user training items, paired per-(user, target)).
  - 1 seed x 5 folds on Beauty + Fashion (smallest two datasets) for the
    proof of concept. If any algorithm beats content_direct on both, scale
    to Instruments + Books with 5 seeds.
  - All NDCG@10 numbers reported as fold means and per-USER means so we
    can also do paired Wilcoxon against content_direct.

Usage:
    cd _bestrec_run
    uv run python run_poc_new_coldstart.py beauty fashion
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
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from sklearn.linear_model import Ridge

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import (
    NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex,
)


SEED = 20260521


def load_dataset(dataset: str) -> tuple[list[dict], dict, int, int, np.ndarray]:
    k_core = DATASET_KCORE[dataset]
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{k_core}_dedup.pt"
    item_title_emb = torch.load(title_path, weights_only=True)
    return interactions, item_meta, n_users, n_items, item_title_emb


def normalized_embeddings(item_title_emb) -> np.ndarray:
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    return emb / np.maximum(norms, 1e-12)


def build_warm_matrix(train_inters, n_users, warm_indices) -> tuple[csr_matrix, np.ndarray]:
    warm_pos = {int(it): pos for pos, it in enumerate(warm_indices)}
    rows, cols = [], []
    for inter in train_inters:
        pos = warm_pos.get(int(inter["item_id"]))
        if pos is None:
            continue
        rows.append(int(inter["user_id"])); cols.append(pos)
    vals = np.ones(len(rows), dtype=np.float32)
    X_sparse = csr_matrix((vals, (rows, cols)), shape=(n_users, len(warm_indices)))
    return X_sparse, X_sparse.toarray().astype(np.float32)


def user_train_test(train_inters, test_inters) -> tuple[dict, dict]:
    user_train: dict[int, set] = defaultdict(set)
    user_test: dict[int, list] = defaultdict(list)
    for i in train_inters:
        user_train[int(i["user_id"])].add(int(i["item_id"]))
    for i in test_inters:
        user_test[int(i["user_id"])].append(int(i["item_id"]))
    return user_train, user_test


def eval_full_catalog(score_fn: Callable[[np.ndarray], np.ndarray],
                      train_inters, test_inters, n_items, batch_size=192
                      ) -> tuple[dict[str, float], list[dict]]:
    user_train, user_test = user_train_test(train_inters, test_inters)
    users = sorted(u for u in user_test if user_test[u] and user_train[u])
    rows: list[dict] = []
    ndcg, hr, rr = [], [], []
    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        if scores.shape != (len(batch), n_items):
            raise ValueError(f"bad shape {scores.shape}, expected {(len(batch), n_items)}")
        for k, u in enumerate(batch):
            seen = user_train[u]
            if seen:
                scores[k, list(seen)] = -np.inf
            for tgt in user_test[u]:
                ts = scores[k, tgt]
                rank0 = int((scores[k] > ts).sum())
                h = 1.0 if rank0 < TOP_K else 0.0
                n_ = 1.0 / math.log2(rank0 + 2) if rank0 < TOP_K else 0.0
                r_ = 1.0 / (rank0 + 1)
                ndcg.append(n_); hr.append(h); rr.append(r_)
                rows.append({"user_id": int(u), "target_item_id": int(tgt), "ndcg10": n_})
    return ({"NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
             "HR@10":   float(np.mean(hr))   if hr   else 0.0,
             "MRR":     float(np.mean(rr))   if rr   else 0.0,
             "n_eval":  len(rows)},
            rows)


# ---------------------------------------------------------------------------
# Baselines (mirroring run_all_confirmatory.py)
# ---------------------------------------------------------------------------

def make_popularity(train_inters, n_items):
    pop = np.zeros(n_items, dtype=np.float32)
    for i in train_inters:
        pop[int(i["item_id"])] += 1.0
    def f(uids):
        return np.tile(pop, (len(uids), 1))
    return f


def make_content_direct(Xw, warm_indices, S_content):
    S_w_all = S_content[warm_indices, :].astype(np.float32)
    def f(uids):
        return Xw[uids] @ S_w_all
    return f


def make_lc2c_v2(Xw, B_warm, item_title_emb, warm_indices, cold_indices, n_items, mu=1.0):
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]; SBERT_cold = emb[cold_indices]
    reg = Ridge(alpha=mu)
    reg.fit(SBERT_warm, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_cold @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    def f(uids):
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = Xw[uids] @ B_warm
        out[:, cold_indices] = Xw[uids] @ B_hat_cold
        return out
    return f


# ---------------------------------------------------------------------------
# Five new candidate algorithms
# ---------------------------------------------------------------------------

def make_cd_pow(Xw, warm_indices, item_title_emb, T: float):
    """A. CD_pow_T: sharpened content_direct.
       score(u, j) = sum_w in hist of max(cos(SBERT_w, SBERT_j), 0)**T."""
    emb = normalized_embeddings(item_title_emb)
    emb_warm = emb[warm_indices]                       # (n_warm, d)
    # full S_w_all (n_warm, n_items) but with sharpened nonneg cos
    Sraw = (emb_warm @ emb.T).astype(np.float32)
    Sraw = np.maximum(Sraw, 0.0)
    S_pow = np.power(Sraw, T, dtype=np.float32)
    def f(uids):
        return Xw[uids] @ S_pow
    return f


def make_cd_topk(Xw, warm_indices, item_title_emb, K: int):
    """B. CD_topk: top-K per ITEM mask.
       score(u, j) = sum_{w in user_history AND in top-K most similar warm items of j}
                          cos(SBERT_w, SBERT_j).
       Sharpens by restricting which warm items contribute per cold item."""
    emb = normalized_embeddings(item_title_emb)
    emb_warm = emb[warm_indices]
    Sraw = (emb_warm @ emb.T).astype(np.float32)
    Sraw = np.maximum(Sraw, 0.0)
    # For each ITEM column (j), keep only the top-K rows
    K_eff = min(K, Sraw.shape[0])
    # We need the threshold per column
    if K_eff < Sraw.shape[0]:
        # partition along axis 0 per column
        part = np.partition(Sraw, -K_eff, axis=0)
        thresh = part[-K_eff, :][None, :]              # (1, n_items)
        Sk = np.where(Sraw >= thresh, Sraw, 0.0).astype(np.float32)
    else:
        Sk = Sraw
    def f(uids):
        return Xw[uids] @ Sk
    return f


def make_cwa_B(Xw, B_warm, warm_indices, cold_indices, item_title_emb, n_items, p: float):
    """C. CWA_B_pow: content weighted aggregation of B-columns.
       B_hat[:, j_cold] = sum_w (cos+(SBERT_w, SBERT_j_cold))**p * B[:, w] / Z."""
    emb = normalized_embeddings(item_title_emb)
    SBERT_w = emb[warm_indices]; SBERT_c = emb[cold_indices]
    S = np.maximum(SBERT_w @ SBERT_c.T, 0.0).astype(np.float32)  # (n_warm, n_cold)
    if p != 1.0:
        S = np.power(S, p, dtype=np.float32)
    Z = np.maximum(S.sum(axis=0, keepdims=True), 1e-8)
    W = (S / Z).astype(np.float32)                                # (n_warm, n_cold)
    # B_hat_cold = B_warm @ W   -> (n_warm, n_cold)
    B_hat_cold = (B_warm @ W).astype(np.float32)
    def f(uids):
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = Xw[uids] @ B_warm
        out[:, cold_indices] = Xw[uids] @ B_hat_cold
        return out
    return f


def make_pzc_lc2c(Xw, B_warm, warm_indices, cold_indices, item_title_emb, n_items, mu=1.0):
    """D. PZC_LC2C: per-user z-score calibration of LC2C cold scores."""
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_w = emb[warm_indices]; SBERT_c = emb[cold_indices]
    reg = Ridge(alpha=mu); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    def f(uids):
        warm_scores = Xw[uids] @ B_warm                            # (b, n_warm)
        cold_raw = Xw[uids] @ B_hat_cold                           # (b, n_cold)
        # per-user calibration
        w_mean = warm_scores.mean(axis=1, keepdims=True)
        w_std = warm_scores.std(axis=1, keepdims=True)
        c_mean = cold_raw.mean(axis=1, keepdims=True)
        c_std = np.maximum(cold_raw.std(axis=1, keepdims=True), 1e-8)
        cold_cal = (cold_raw - c_mean) / c_std * w_std + w_mean
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_cal
        return out
    return f


def make_cdr_blend(Xw, B_warm, warm_indices, cold_indices, S_content, item_title_emb, n_items, alpha: float):
    """E. CDR_blend (alpha): for cold items only,
            cold_score = alpha * content_direct + (1 - alpha) * LC2C_v2_raw
        Both inputs are per-user z-normalized first so the alpha-grid is interpretable.

        For warm items we always use the EASE+SBERT warm score (Xw @ B_warm).
        alpha is selected on inner validation in the calling code; the
        returned scorer uses the chosen alpha."""
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_w = emb[warm_indices]; SBERT_c = emb[cold_indices]
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    S_w_cold = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def _z(x):
        m = x.mean(axis=1, keepdims=True); s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
        return (x - m) / s
    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cd_cold = _z(Xw[uids] @ S_w_cold)
        lc_cold = _z(Xw[uids] @ B_hat_cold)
        cold_blend = alpha * cd_cold + (1.0 - alpha) * lc_cold
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_blend
        return out
    return f


# Diagnostic variants to isolate where the gain comes from
def make_diag_random_cold_z(Xw, B_warm, warm_indices, cold_indices, n_items, rng_seed: int):
    """Sanity check: warm = EASE, cold = random z-scores. If this beats
       content_direct, the gain is from the scale trick, not the signal."""
    rng = np.random.RandomState(rng_seed)
    n_cold = len(cold_indices)
    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cold = rng.standard_normal(size=(len(uids), n_cold)).astype(np.float32)
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold
        return out
    return f


def make_diag_easewarm_cdcold_raw(Xw, B_warm, warm_indices, cold_indices, S_content, n_items):
    """Diagnostic: warm = EASE, cold = raw (non-normalized) content_direct.
       If this is much worse than CDR_blend_a=1.0 (z-normalized content),
       then the z-normalization is doing the work, not the warm-EASE scoring."""
    S_w_cold = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cold = Xw[uids] @ S_w_cold
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold
        return out
    return f


def make_diag_zwarm_zcold(Xw, B_warm, warm_indices, cold_indices, S_content, item_title_emb, n_items, alpha: float):
    """Diagnostic: z-normalize BOTH warm and cold (per-user). Warm via EASE,
       cold via blend. If this matches CDR_blend, the trick is real; if it
       collapses, the trick was about preferring cold above warm via scale."""
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_w = emb[warm_indices]; SBERT_c = emb[cold_indices]
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    S_w_cold = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def _z(x):
        m = x.mean(axis=1, keepdims=True); s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
        return (x - m) / s
    def f(uids):
        warm_z = _z(Xw[uids] @ B_warm)
        cd_cold = _z(Xw[uids] @ S_w_cold)
        lc_cold = _z(Xw[uids] @ B_hat_cold)
        cold_blend = alpha * cd_cold + (1.0 - alpha) * lc_cold
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_z
        out[:, cold_indices] = cold_blend
        return out
    return f


def make_diag_perpool_rank_fusion(Xw, B_warm, warm_indices, cold_indices, S_content, item_title_emb, n_items, alpha: float):
    """Diagnostic: per-user RANK PERCENTILE (in [0, 1]) within each pool
       (warm / cold), then concatenate. Pure rank-based, no scale trick.
       The pool a target lives in determines its absolute percentile; the
       cross-pool ranking is then driven by these percentiles."""
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_w = emb[warm_indices]; SBERT_c = emb[cold_indices]
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    S_w_cold = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def _pct(x):
        # rank along axis 1 -> 0..1 percentile (high score -> high percentile)
        order = x.argsort(axis=1)
        ranks = np.empty_like(order, dtype=np.float32)
        rows = np.arange(x.shape[0])[:, None]
        ranks[rows, order] = np.arange(x.shape[1], dtype=np.float32)
        return ranks / max(1, x.shape[1] - 1)
    def f(uids):
        warm_pct = _pct(Xw[uids] @ B_warm)
        cd_pct = _pct(Xw[uids] @ S_w_cold)
        lc_pct = _pct(Xw[uids] @ B_hat_cold)
        cold_blend = alpha * cd_pct + (1.0 - alpha) * lc_pct
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_pct
        out[:, cold_indices] = cold_blend
        return out
    return f


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

CD_POW_T_GRID = [1.0, 4.0, 16.0]
CD_TOPK_GRID = [3, 5, 10]
CWA_B_P_GRID = [4.0, 8.0]
CDR_ALPHA_GRID = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0]


def select_alpha_on_validation(dataset, outer_train, outer_cold_items, S_content,
                                item_title_emb, n_users, n_items, rng):
    """Inner validation hold-out on warm items: pick CDR_blend alpha.
    Returns (best_alpha, val_scores_dict). Used by CDR_validated_margin."""
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters:
        return 0.25, {}
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_sparse_in, Xw_in = build_warm_matrix(inner_train, n_users, inner_warm)
    S_warm_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_warm_in = ease_fast(X_sparse_in, lam=lam, beta=beta, S_content=S_warm_in, dtype=np.float32)
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    val_scores: dict[float, float] = {}
    for a in CDR_ALPHA_GRID:
        sf = make_cdr_blend(Xw_in, B_warm_in, inner_warm, cold_arr, S_content,
                              item_title_emb, n_items, alpha=a)
        res, _ = eval_full_catalog(sf, inner_train, val_inters, n_items)
        val_scores[float(a)] = float(res["NDCG@10"])
    del X_sparse_in, Xw_in, B_warm_in; gc.collect()
    best_alpha = max(val_scores, key=val_scores.get)
    return best_alpha, val_scores


def run_dataset(dataset: str, seeds: list[int]) -> dict:
    print(f"\n{'#' * 70}\n# POC: {dataset.upper()}\n{'#' * 70}")
    interactions, _, n_users, n_items, item_title_emb = load_dataset(dataset)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k_core = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k_core}  lambda={lam}  beta={beta}")

    method_records: dict[str, list[float]] = defaultdict(list)
    method_perfold: dict[str, list[float]] = defaultdict(list)
    method_per_user: dict[str, dict[tuple[int, int], list[float]]] = defaultdict(lambda: defaultdict(list))

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
            train_inters = [interactions[i] for i in tr_idx]
            test_inters = [interactions[i] for i in te_idx]
            warm_indices = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
            cold_indices = np.array(sorted(cold_items), dtype=np.int32)
            X_sparse, Xw = build_warm_matrix(train_inters, n_users, warm_indices)
            S_warm = S_content[np.ix_(warm_indices, warm_indices)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)

            # --- Baselines ---
            scorers: dict[str, Callable] = {
                "popularity": make_popularity(train_inters, n_items),
                "content_direct": make_content_direct(Xw, warm_indices, S_content),
                "lc2c_v2": make_lc2c_v2(Xw, B_warm, item_title_emb, warm_indices, cold_indices, n_items),
            }
            # --- Candidate algorithms ---
            # A. CD_pow_T
            for T in CD_POW_T_GRID:
                scorers[f"CD_pow_T={T}"] = make_cd_pow(Xw, warm_indices, item_title_emb, T)
            # B. CD_topk
            for K in CD_TOPK_GRID:
                scorers[f"CD_topk={K}"] = make_cd_topk(Xw, warm_indices, item_title_emb, K)
            # C. CWA_B_pow
            for p in CWA_B_P_GRID:
                scorers[f"CWA_B_p={p}"] = make_cwa_B(Xw, B_warm, warm_indices, cold_indices, item_title_emb, n_items, p)
            # D. PZC_LC2C
            scorers["PZC_LC2C"] = make_pzc_lc2c(Xw, B_warm, warm_indices, cold_indices, item_title_emb, n_items)
            # E. CDR_blend (with alpha grid)
            for a in CDR_ALPHA_GRID:
                scorers[f"CDR_blend_a={a}"] = make_cdr_blend(Xw, B_warm, warm_indices, cold_indices,
                                                              S_content, item_title_emb, n_items, alpha=a)
            # E'. CDR_blend with alpha selected on inner validation (no test-set tuning)
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            chosen_alpha, val_scores = select_alpha_on_validation(
                dataset, train_inters, set(cold_items), S_content,
                item_title_emb, n_users, n_items, val_rng)
            scorers["CDR_validated"] = make_cdr_blend(Xw, B_warm, warm_indices, cold_indices,
                                                       S_content, item_title_emb, n_items, alpha=chosen_alpha)
            # Diagnostics
            scorers["DIAG_random_cold_z"] = make_diag_random_cold_z(
                Xw, B_warm, warm_indices, cold_indices, n_items, rng_seed=seed * 100 + fold_id)
            scorers["DIAG_easewarm_cdcold_raw"] = make_diag_easewarm_cdcold_raw(
                Xw, B_warm, warm_indices, cold_indices, S_content, n_items)
            for a in [0.0, 0.5, 1.0]:
                scorers[f"DIAG_pctfusion_a={a}"] = make_diag_perpool_rank_fusion(
                    Xw, B_warm, warm_indices, cold_indices, S_content, item_title_emb, n_items, alpha=a)

            for name, sf in scorers.items():
                res, rows = eval_full_catalog(sf, train_inters, test_inters, n_items)
                method_perfold[name].append(res["NDCG@10"])
                for r in rows:
                    method_per_user[name][(seed, fold_id, r["user_id"], r["target_item_id"])].append(r["ndcg10"])
            print(f"  seed={seed} fold={fold_id}  n_cold={len(cold_items)}  "
                  f"content_direct={method_perfold['content_direct'][-1]:.4f}  "
                  f"lc2c_v2={method_perfold['lc2c_v2'][-1]:.4f}  "
                  f"CDR_a=0.25={method_perfold['CDR_blend_a=0.25'][-1]:.4f}  "
                  f"CDR_valid(a={chosen_alpha})={method_perfold['CDR_validated'][-1]:.4f}  "
                  f"val_scores={val_scores}")
            del X_sparse, Xw, B_warm, S_warm; gc.collect()

    print(f"\n=== {dataset.upper()} fold means ({len(seeds)} seed(s) x {NUM_FOLDS} folds, full-catalog cold-item NDCG@10) ===")
    summary = {}
    for name, vs in sorted(method_perfold.items(), key=lambda kv: -np.mean(kv[1])):
        m, s = float(np.mean(vs)), float(np.std(vs))
        summary[name] = {"NDCG@10": m, "NDCG@10_std": s, "n_fold": len(vs)}
        print(f"  {name:>30s}: NDCG@10 = {m:.4f} +/- {s:.4f}")

    # Per-USER Wilcoxon: CDR_validated vs the FAIR baseline (DIAG_easewarm_cdcold_raw)
    # and vs LC2C V2.
    from scipy.stats import wilcoxon as _wilcoxon
    def _per_user(name):
        pu = method_per_user[name]
        by_user: dict[int, list[float]] = defaultdict(list)
        for (seed, fold, uid, tgt), vs in pu.items():
            for v in vs:
                by_user[uid].append(v)
        return {u: float(np.mean(vs)) for u, vs in by_user.items()}
    print(f"\n=== Per-USER paired Wilcoxon (one-sided, target > baseline) ===")
    wilcox = {}
    cand_pu = _per_user("CDR_validated")
    for baseline in ["DIAG_easewarm_cdcold_raw", "content_direct", "lc2c_v2"]:
        bpu = _per_user(baseline)
        common = sorted(set(cand_pu) & set(bpu))
        if not common: continue
        diffs = np.array([cand_pu[u] - bpu[u] for u in common])
        cand_m = float(np.mean([cand_pu[u] for u in common]))
        base_m = float(np.mean([bpu[u] for u in common]))
        if np.allclose(diffs, 0):
            p = 1.0
        else:
            p = float(_wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
        marker = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
        wilcox[baseline] = {"n_users": len(common), "candidate": cand_m, "baseline": base_m,
                              "delta": float(np.mean(diffs)), "p_raw": p, "marker": marker}
        print(f"  CDR_validated > {baseline:<28} : n={len(common)} cand={cand_m:.4f} base={base_m:.4f} delta={np.mean(diffs):+.4f} p={p:.3e} {marker}")
    return {"summary": summary,
            "perfold": {k: list(map(float, v)) for k, v in method_perfold.items()},
            "wilcoxon_cdr_validated": wilcox}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty", "fashion"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--out", default="results_poc_new_coldstart.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    out_path = Path(__file__).parent / args.out
    payload = {"schema_version": 1, "candidate_scope": "full_catalog",
                "status": "proof_of_concept",
                "seeds": seeds, "datasets": {}}
    t0 = time.time()
    for ds in args.datasets:
        payload["datasets"][ds] = run_dataset(ds, seeds)
        with out_path.open("w") as f:
            json.dump(payload, f, indent=2)
    print(f"\n[done in {time.time()-t0:.1f}s] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
