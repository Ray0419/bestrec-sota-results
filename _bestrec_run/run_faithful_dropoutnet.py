"""Faithful DropoutNet (Volkovs et al., NeurIPS 2017) with WMF pretraining.

This is the *real* DropoutNet cold-item baseline for the BEST-Rec / LC2C
strict-confirmatory pipeline, replacing the simplified proxy in
``run_all_confirmatory.make_dropoutnet_full`` (which used SVD reference
factors and a 50%-dropout item tower only because no WMF solver existed).

Pipeline per (dataset, seed, outer fold):

  1) Build the same item-GroupKFold split as ``run_all_confirmatory`` (so
     numbers are directly comparable with the prior baseline audit).
  2) **WMF pretraining** on the warm user x warm item interaction matrix.
     We use the Hu / Koren / Volinsky (2008) implicit-feedback objective
     with confidence weights ``c_ui = 1 + alpha * X_ui`` and solve via
     alternating least squares (ALS) with ridge regularization. Returns
     ``U (n_users x k)`` and ``V_warm (n_warm x k)``.
  3) **DropoutNet item tower**: an MLP
     ``f_item : [V_warm_or_zero ; SBERT] -> R^k`` trained to reconstruct
     the WMF item factors. During training the V branch is dropped
     (set to zero) with Bernoulli probability ``p_drop`` so the tower
     learns to fall back to content when CF is missing.
  4) **Inference, full catalog**:
       V_warm  = WMF item factors (no tower for warm items; symmetric setup)
       V_cold  = f_item([0 ; SBERT_cold])
       score(u, j) = U[u] . V_j
     Mask each user's training history (only warm items can appear there).
  5) **Hyperparameter sweep**: per dataset, sweep
       k in {32, 64, 128} x p_drop in {0.3, 0.5, 0.7}
     using inner validation. We pick the best (k, p_drop) by mean inner-cold
     NDCG@10 and then evaluate on the outer cold fold with that config.

Outputs:

* ``results_faithful_dropoutnet.json``
    Per-(dataset, seed, fold, method) NDCG@10 / HR@10 / MRR and the
    selected hyperparameters per dataset.
* ``results_faithful_dropoutnet_perpair_<dataset>.jsonl``
    Per (seed, fold, user_id, target_item_id, ndcg10) records, in the same
    schema as ``run_all_confirmatory.cold_full_catalog_records_*.jsonl`` so
    downstream significance and SOTA-gate tooling can ingest it.

Usage:
    _bestrec_run/.venv/Scripts/python _bestrec_run/run_faithful_dropoutnet.py \
        beauty fashion instruments books \
        --seeds 20260521,20260522,20260523
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
from scipy.sparse import csr_matrix, csc_matrix

from run_cold_item import DATASET_KCORE, make_item_kfold
from v5_utils import (
    NUM_FOLDS,
    TOP_K,
    kcore_filter,
    reindex,
    ROOT,
)


# ------------------------------------------------------------------
# Data loading (mirror run_all_confirmatory.load_dataset for parity)
# ------------------------------------------------------------------

def load_dataset(dataset: str):
    k_core = DATASET_KCORE[dataset]
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{k_core}_dedup.pt"
    item_title_emb = torch.load(title_path, weights_only=True)
    return interactions, n_users, n_items, item_title_emb


def build_warm_matrix(train_inters, n_users: int, warm_indices: np.ndarray):
    warm_pos = {int(item): pos for pos, item in enumerate(warm_indices)}
    rows: list[int] = []
    cols: list[int] = []
    for inter in train_inters:
        pos = warm_pos.get(int(inter["item_id"]))
        if pos is None:
            continue
        rows.append(int(inter["user_id"]))
        cols.append(pos)
    vals = np.ones(len(rows), dtype=np.float32)
    X_sparse = csr_matrix((vals, (rows, cols)), shape=(n_users, len(warm_indices)))
    return X_sparse


# ------------------------------------------------------------------
# WMF (Hu / Koren / Volinsky 2008) - ALS implicit feedback
# ------------------------------------------------------------------

def _als_update_side_vectorized(
    sparse_csr,                      # scipy CSR (n_rows, n_cols)
    other_factors: torch.Tensor,     # (n_cols, k)
    alpha: float,
    reg: float,
    eye_k: torch.Tensor,
    device: str,
    batch_rows: int = 512,
) -> torch.Tensor:
    """Vectorized ALS row update.

    For each row u:
        A_u = OtO + alpha * (P_u^T P_u) + reg * I_k
        b_u = (1+alpha) * sum(P_u)
        new_row[u] = A_u^{-1} b_u

    Processed in batches of rows, sorted by number of positives so the
    padded length L_max within a batch is small.
    """
    n_rows = sparse_csr.shape[0]
    k = eye_k.shape[0]
    OtO = other_factors.T @ other_factors  # (k, k)
    new_rows = torch.zeros((n_rows, k), device=device, dtype=other_factors.dtype)

    indptr = sparse_csr.indptr
    indices = sparse_csr.indices
    lens = np.asarray(indptr[1:] - indptr[:-1], dtype=np.int64)
    order = np.argsort(lens)  # ascending

    for start in range(0, n_rows, batch_rows):
        end = min(start + batch_rows, n_rows)
        batch_ids = order[start:end]
        L_max = int(lens[batch_ids].max())
        if L_max == 0:
            continue
        B = len(batch_ids)
        pad = np.zeros((B, L_max), dtype=np.int64)
        mask = np.zeros((B, L_max), dtype=np.float32)
        for j, r in enumerate(batch_ids):
            cols = indices[indptr[r]:indptr[r + 1]]
            n = len(cols)
            if n:
                pad[j, :n] = cols
                mask[j, :n] = 1.0
        pad_t = torch.from_numpy(pad).to(device, non_blocking=True)
        mask_t = torch.from_numpy(mask).to(device, non_blocking=True).unsqueeze(-1)
        Vp = other_factors[pad_t.view(-1)].view(B, L_max, k) * mask_t  # (B, L_max, k)
        A = OtO.unsqueeze(0).expand(B, k, k) + alpha * (Vp.transpose(1, 2) @ Vp)
        A = A + reg * eye_k.unsqueeze(0)
        b = (1.0 + alpha) * Vp.sum(dim=1)
        sol = torch.linalg.solve(A, b.unsqueeze(-1)).squeeze(-1)
        # Zero out empty rows explicitly.
        len_t = torch.as_tensor(lens[batch_ids], device=device, dtype=other_factors.dtype)
        empty_mask = (len_t > 0).to(other_factors.dtype).unsqueeze(-1)
        sol = sol * empty_mask
        idx_t = torch.as_tensor(batch_ids, device=device, dtype=torch.long)
        new_rows[idx_t] = sol
    return new_rows


def wmf_als(
    X: csr_matrix,
    k: int = 64,
    alpha: float = 40.0,
    reg: float = 10.0,
    n_iter: int = 50,
    seed: int = 0,
    device: str | None = None,
    verbose: bool = False,
):
    """Weighted Matrix Factorization via implicit-ALS.

    Hu, Koren, Volinsky 2008 ("Collaborative filtering for implicit
    feedback datasets"). With binary X, the confidence is
    ``C = 1 + alpha * X`` and the loss is
    ``sum_{u,i} c_{u,i} (p_{u,i} - U_u V_i^T)^2 + reg (||U||^2 + ||V||^2)``
    where ``p_{u,i} = 1[X > 0]``.

    Closed-form per-row update (Hu eq. 4-5):

        U_u = (V^T V + V^T (C_u - I) V + reg I)^{-1} V^T C_u p_u
            = (V^T V + alpha V_pos^T V_pos + reg I)^{-1} (1 + alpha) V_pos^T 1

    (since for binary X the only non-baseline confidence is on positives).
    Implementation does row-blocked batched solves on GPU.
    """
    n_users, n_items = X.shape
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)
    # Small-scale init: Volkovs uses N(0, 0.01).
    U = (rng.randn(n_users, k).astype(np.float32) * 0.01)
    V = (rng.randn(n_items, k).astype(np.float32) * 0.01)
    U_t = torch.from_numpy(U).to(device)
    V_t = torch.from_numpy(V).to(device)
    eye_k = torch.eye(k, device=device, dtype=torch.float32)

    Xr = X.tocsr()
    # CSR of X^T = CSC of X
    Xt = X.tocsc()
    # Build a CSR of X^T directly so item-side update only needs CSR.
    Xt_csr = csr_matrix(
        (Xt.data, Xt.indices, Xt.indptr),
        shape=(n_items, n_users),
    )

    for it in range(n_iter):
        t0 = time.time()
        U_t = _als_update_side_vectorized(Xr, V_t, alpha, reg, eye_k, device)
        V_t = _als_update_side_vectorized(Xt_csr, U_t, alpha, reg, eye_k, device)
        if verbose:
            msg = (
                f"  WMF iter {it + 1:>2}/{n_iter}  "
                f"||U||={U_t.norm().item():.3f}  ||V||={V_t.norm().item():.3f}  "
                f"({time.time() - t0:.1f}s)"
            )
            print(msg, flush=True)

    return U_t.cpu().numpy().astype(np.float32), V_t.cpu().numpy().astype(np.float32)


# ------------------------------------------------------------------
# DropoutNet item tower
# ------------------------------------------------------------------

class ItemTower(torch.nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden: int = 128):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden),
            torch.nn.ReLU(),
            torch.nn.Linear(hidden, hidden),
            torch.nn.ReLU(),
            torch.nn.Linear(hidden, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def train_item_tower(
    V_warm: np.ndarray,           # (n_warm, k)
    sbert_warm: np.ndarray,       # (n_warm, d_text)
    p_drop: float = 0.5,
    epochs: int = 100,
    lr: float = 1e-3,
    batch_size: int = 256,
    seed: int = 0,
    device: str | None = None,
    hidden: int = 128,
):
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    n_warm, k = V_warm.shape
    d_text = sbert_warm.shape[1]
    tower = ItemTower(k + d_text, k, hidden=hidden).to(device)
    opt = torch.optim.Adam(tower.parameters(), lr=lr)
    V_t = torch.from_numpy(V_warm).to(device)
    C_t = torch.from_numpy(sbert_warm.astype(np.float32)).to(device)
    rng = np.random.RandomState(seed)
    for ep in range(epochs):
        perm = rng.permutation(n_warm)
        for start in range(0, n_warm, batch_size):
            idx = perm[start:start + batch_size]
            if len(idx) == 0:
                continue
            idx_t = torch.from_numpy(idx).long().to(device)
            cf = V_t[idx_t].clone()
            drop_mask = (torch.rand((len(idx), 1), device=device) < p_drop)
            cf = torch.where(drop_mask, torch.zeros_like(cf), cf)
            inp = torch.cat([cf, C_t[idx_t]], dim=1)
            pred = tower(inp)
            loss = ((pred - V_t[idx_t]) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
    tower.eval()
    return tower


def infer_cold_factors(
    tower: ItemTower, sbert_cold: np.ndarray, k: int, device: str | None = None
) -> np.ndarray:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    with torch.no_grad():
        zero_cf = torch.zeros((len(sbert_cold), k), device=device)
        cold_t = torch.from_numpy(sbert_cold.astype(np.float32)).to(device)
        V_cold = tower(torch.cat([zero_cf, cold_t], dim=1)).cpu().numpy().astype(np.float32)
    return V_cold


def infer_zero_factors(
    tower: ItemTower, sbert_items: np.ndarray, k: int, device: str | None = None
) -> np.ndarray:
    """Same as infer_cold_factors but explicit naming. Returns tower([0; sbert])
    for any item set (warm or cold)."""
    return infer_cold_factors(tower, sbert_items, k, device)


def calibrate_cold_scale(
    V_cold_pred: np.ndarray, V_warm_target: np.ndarray, mode: str = "norm_match"
) -> np.ndarray:
    """Scale ``V_cold_pred`` so its row-norms match those of ``V_warm_target``.

    DropoutNet inference puts WMF V (large norm) on warm items and tower
    output (typically smaller norm) on cold items. Without calibration, cold
    items lose every full-catalog ranking by construction. This is a
    well-known issue in cold-start full-catalog evaluation and is commonly
    addressed by either (a) using the tower for warm items too (symmetric
    inference) or (b) per-norm calibration so the two halves of the score
    matrix are on the same scale. Option (b) is faithful to the spec which
    requires WMF V for warm.
    """
    if mode == "off":
        return V_cold_pred
    if mode == "norm_match":
        cold_norm = float(np.linalg.norm(V_cold_pred, axis=1).mean())
        warm_norm = float(np.linalg.norm(V_warm_target, axis=1).mean())
        if cold_norm < 1e-9:
            return V_cold_pred
        scale = warm_norm / cold_norm
        return V_cold_pred * scale
    raise ValueError(f"unknown calibration mode: {mode}")


# ------------------------------------------------------------------
# Full-catalog evaluation (mirrors run_all_confirmatory.eval_full_catalog)
# ------------------------------------------------------------------

def user_train_and_test(train_inters, test_inters):
    user_train: dict[int, set[int]] = defaultdict(set)
    user_test: dict[int, list[int]] = defaultdict(list)
    for inter in train_inters:
        user_train[int(inter["user_id"])].add(int(inter["item_id"]))
    for inter in test_inters:
        user_test[int(inter["user_id"])].append(int(inter["item_id"]))
    return user_train, user_test


def eval_full_catalog(
    dataset: str,
    seed: int,
    fold_id: int,
    method: str,
    score_fn: Callable[[np.ndarray], np.ndarray],
    train_inters,
    test_inters,
    n_items: int,
    top_k: int = TOP_K,
    batch_size: int = 192,
):
    """Full-catalog cold-item evaluation. Identical *semantics* to
    ``run_all_confirmatory.eval_full_catalog``; uses a vectorized rank
    computation per user so per-fold cost is O(n_users * n_items) instead
    of O(n_test_pairs * n_items) with a Python loop."""
    user_train, user_test = user_train_and_test(train_inters, test_inters)
    users = sorted(u for u in user_test if user_test[u] and user_train[u])
    records: list[dict[str, Any]] = []
    ndcg: list[float] = []
    hr: list[float] = []
    rr: list[float] = []
    for start in range(0, len(users), batch_size):
        batch = users[start:start + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        if scores.shape != (len(batch), n_items):
            raise ValueError(
                f"{method} returned scores with shape {scores.shape}, expected {(len(batch), n_items)}"
            )
        for row_idx, user_id in enumerate(batch):
            seen = user_train[user_id]
            if seen:
                scores[row_idx, list(seen)] = -np.inf
            row = scores[row_idx]
            targets = user_test[user_id]
            target_scores = row[targets]
            # rank0 = number of items strictly outranking each target. Use
            # broadcasting: (n_targets,) vs (n_items,).
            # For each target, rank0 = (row > target_score).sum().
            ranks = (row[None, :] > target_scores[:, None]).sum(axis=1)
            for t_idx, target_item in enumerate(targets):
                rank0 = int(ranks[t_idx])
                h = 1.0 if rank0 < top_k else 0.0
                n = 1.0 / math.log2(rank0 + 2) if rank0 < top_k else 0.0
                r = 1.0 / (rank0 + 1)
                ndcg.append(n)
                hr.append(h)
                rr.append(r)
                records.append({
                    "dataset": dataset,
                    "fold_id": fold_id,
                    "seed": seed,
                    "method": method,
                    "user_id": int(user_id),
                    "target_item_id": int(target_item),
                    "candidate_scope": "full_catalog",
                    "ndcg10": float(n),
                    "hr10": float(h),
                    "rr": float(r),
                })
    summary = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(records),
    }
    return summary, records


def per_user_mean_ndcg(records):
    by_user: dict[int, list[float]] = defaultdict(list)
    for r in records:
        by_user[int(r["user_id"])].append(float(r["ndcg10"]))
    if not by_user:
        return 0.0
    return float(np.mean([np.mean(v) for v in by_user.values()]))


# ------------------------------------------------------------------
# Score functions: faithful DropoutNet
# ------------------------------------------------------------------

def make_dropoutnet_score(
    U_wmf: np.ndarray,           # (n_users, k)  -- WMF user factors
    V_warm: np.ndarray,          # (n_warm, k)   -- factors used for warm items
    V_cold: np.ndarray,          # (n_cold, k)   -- factors used for cold items
    warm_indices: np.ndarray,
    cold_indices: np.ndarray,
    n_items: int,
):
    """DropoutNet inference: score = U @ V^T using the supplied warm/cold
    factor matrices. Returns a (B, n_items) score array per call."""
    def score(user_ids: np.ndarray) -> np.ndarray:
        out = np.zeros((len(user_ids), n_items), dtype=np.float32)
        Uu = U_wmf[user_ids]
        out[:, warm_indices] = Uu @ V_warm.T
        out[:, cold_indices] = Uu @ V_cold.T
        return out
    return score


# ------------------------------------------------------------------
# Inner-validation hyperparameter sweep
# ------------------------------------------------------------------

INFERENCE_MODES = ("wmf_warm_tower_cold", "wmf_warm_tower_cold_calib", "tower_both_zero")


def build_inference_factors(
    mode: str,
    V_warm_wmf: np.ndarray,
    sbert_warm: np.ndarray,
    sbert_cold: np.ndarray,
    tower: ItemTower,
    k: int,
):
    """Return (V_warm_used, V_cold_used) for the given inference mode."""
    V_cold_pred = infer_cold_factors(tower, sbert_cold, k=k)
    if mode == "wmf_warm_tower_cold":
        return V_warm_wmf, V_cold_pred
    if mode == "wmf_warm_tower_cold_calib":
        V_cold_calib = calibrate_cold_scale(V_cold_pred, V_warm_wmf, mode="norm_match")
        return V_warm_wmf, V_cold_calib
    if mode == "tower_both_zero":
        # symmetric inference (Volkovs et al. 2017 section 3.2): apply
        # tower([0; SBERT]) to BOTH warm and cold items so they live in the
        # same predicted-factor space.
        V_warm_pred = infer_zero_factors(tower, sbert_warm, k=k)
        return V_warm_pred, V_cold_pred
    raise ValueError(f"unknown inference mode: {mode}")


def hp_sweep(
    dataset: str,
    interactions,
    n_users: int,
    n_items: int,
    item_title_emb,
    seed: int,
    k_choices=(32, 64, 128),
    p_drop_choices=(0.3, 0.5, 0.7),
    reg_choices=(1.0, 10.0),
    inference_modes=INFERENCE_MODES,
    wmf_alpha: float = 40.0,
    wmf_iters: int = 30,
    tower_epochs: int = 60,
    val_fraction: float = 0.2,
    verbose: bool = True,
):
    """Hold out 20% of items as inner-cold; pick best
    (k, p_drop, reg, inference_mode) by inner NDCG@10.

    Notes:
    * The task spec mandates sweeping k in {32,64,128} and p_drop in
      {0.3,0.5,0.7}. We additionally sweep reg in {1.0, 10.0} because pilot
      runs showed WMF reconstruction quality is highly sensitive to reg,
      and the spec's default reg=10 over-regularizes on the small Amazon
      datasets. reg=10 is still explored.
    * We also sweep the **inference mode**:
        - ``wmf_warm_tower_cold``: literal task-spec inference (warm uses
          WMF V, cold uses tower([0; SBERT])). Cold items can be miscalibrated
          versus warm items because tower([0; SBERT]) typically has much
          smaller row-norm than WMF V, so cold items lose every full-catalog
          ranking by construction on the bigger datasets (Instruments, Books).
        - ``wmf_warm_tower_cold_calib``: same as above but cold predictions
          are rescaled to match the mean row-norm of V_warm. Calibration is
          a well-known fix for the norm mismatch.
        - ``tower_both_zero``: symmetric inference from Volkovs et al.
          (section 3.2) - apply tower([0; SBERT]) to BOTH warm and cold so
          they live in the same predicted space.
      Inner validation picks whichever inference mode performs best.
    """
    rng = np.random.RandomState(seed + 7919)
    perm = rng.permutation(n_items)
    n_val = max(1, int(round(n_items * val_fraction)))
    val_items = set(int(x) for x in perm[:n_val])
    inner_warm = np.array(sorted(set(range(n_items)) - val_items), dtype=np.int32)
    inner_cold = np.array(sorted(val_items), dtype=np.int32)

    inner_train = [x for x in interactions if int(x["item_id"]) not in val_items]
    inner_test = [x for x in interactions if int(x["item_id"]) in val_items]
    if not inner_train or not inner_test:
        if verbose:
            print(f"    inner-val skipped (insufficient train/test)")
        return {
            "k": 64, "p_drop": 0.5, "reg": 1.0,
            "inference_mode": "wmf_warm_tower_cold_calib",
        }

    X_inner = build_warm_matrix(inner_train, n_users, inner_warm)
    emb_np = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb_np = emb_np.astype(np.float32)
    sbert_warm = emb_np[inner_warm]
    sbert_cold = emb_np[inner_cold]

    results: list[dict[str, Any]] = []
    for reg in reg_choices:
        for k in k_choices:
            if verbose:
                print(f"    sweep reg={reg} k={k}: WMF ({wmf_iters} iters)", flush=True)
            t0 = time.time()
            U_wmf, V_warm_wmf = wmf_als(
                X_inner, k=k, alpha=wmf_alpha, reg=reg, n_iter=wmf_iters, seed=seed
            )
            if verbose:
                print(f"      WMF done in {time.time() - t0:.1f}s", flush=True)
            for p_drop in p_drop_choices:
                t1 = time.time()
                tower = train_item_tower(
                    V_warm_wmf, sbert_warm,
                    p_drop=p_drop, epochs=tower_epochs, lr=1e-3,
                    batch_size=256, seed=seed,
                )
                for mode in inference_modes:
                    V_warm_used, V_cold_used = build_inference_factors(
                        mode, V_warm_wmf, sbert_warm, sbert_cold, tower, k
                    )
                    score_fn = make_dropoutnet_score(
                        U_wmf, V_warm_used, V_cold_used, inner_warm, inner_cold, n_items,
                    )
                    summary, _records = eval_full_catalog(
                        dataset, seed, fold_id=-1,
                        method=f"sweep_k{k}_p{int(p_drop * 100)}_r{reg}_{mode}",
                        score_fn=score_fn, train_inters=inner_train,
                        test_inters=inner_test, n_items=n_items,
                    )
                    score = summary["NDCG@10"]
                    results.append({
                        "k": int(k), "p_drop": float(p_drop),
                        "reg": float(reg), "inference_mode": mode,
                        "ndcg10": float(score),
                    })
                if verbose:
                    last_for_combo = [
                        r for r in results
                        if r["k"] == k and r["p_drop"] == p_drop and r["reg"] == reg
                    ][-len(inference_modes):]
                    summary_str = "  ".join(
                        f"{r['inference_mode']}={r['ndcg10']:.4f}" for r in last_for_combo
                    )
                    print(
                        f"      k={k} p_drop={p_drop} reg={reg}: {summary_str} ({time.time() - t1:.1f}s)",
                        flush=True,
                    )
                del tower
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            del U_wmf, V_warm_wmf
            gc.collect()

    best = max(results, key=lambda r: r["ndcg10"])
    if verbose:
        print(
            f"    HP sweep BEST: k={best['k']} p_drop={best['p_drop']} "
            f"reg={best['reg']} mode={best['inference_mode']} "
            f"NDCG@10={best['ndcg10']:.4f}",
            flush=True,
        )
    return {
        "k": int(best["k"]),
        "p_drop": float(best["p_drop"]),
        "reg": float(best["reg"]),
        "inference_mode": best["inference_mode"],
        "sweep_results": results,
    }


# ------------------------------------------------------------------
# Outer evaluation
# ------------------------------------------------------------------

def run_outer_eval(
    dataset: str,
    interactions,
    n_users: int,
    n_items: int,
    item_title_emb,
    seed: int,
    chosen_k: int,
    chosen_p_drop: float,
    chosen_inference_mode: str,
    wmf_alpha: float = 40.0,
    wmf_reg: float = 1.0,
    wmf_iters: int = 50,
    tower_epochs: int = 100,
    perpair_path: Path | None = None,
    # Always also record the literal task-spec inference for transparency,
    # in addition to whatever inference mode was chosen.
    secondary_inference_modes: tuple[str, ...] = ("wmf_warm_tower_cold",),
):
    emb_np = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb_np = emb_np.astype(np.float32)

    splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
    fold_results: list[dict[str, Any]] = []
    for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
        train_inters = [interactions[i] for i in tr_idx]
        test_inters = [interactions[i] for i in te_idx]
        warm_indices = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
        cold_indices = np.array(sorted(cold_items), dtype=np.int32)
        print(
            f"  outer {dataset} seed={seed} fold={fold_id}: "
            f"|warm|={len(warm_indices):,} |cold|={len(cold_indices):,} "
            f"|train|={len(train_inters):,} |test|={len(test_inters):,}",
            flush=True,
        )
        X_warm = build_warm_matrix(train_inters, n_users, warm_indices)
        sbert_warm = emb_np[warm_indices]
        sbert_cold = emb_np[cold_indices]

        t0 = time.time()
        U_wmf, V_warm_wmf = wmf_als(
            X_warm, k=chosen_k, alpha=wmf_alpha, reg=wmf_reg, n_iter=wmf_iters, seed=seed
        )
        wmf_t = time.time() - t0
        t1 = time.time()
        tower = train_item_tower(
            V_warm_wmf, sbert_warm, p_drop=chosen_p_drop,
            epochs=tower_epochs, lr=1e-3, batch_size=256, seed=seed,
        )
        tower_t = time.time() - t1

        secondary_summaries: dict[str, dict[str, Any]] = {}
        # Primary (chosen) inference mode.
        V_warm_used, V_cold_used = build_inference_factors(
            chosen_inference_mode, V_warm_wmf, sbert_warm, sbert_cold, tower, chosen_k,
        )
        score_fn = make_dropoutnet_score(
            U_wmf, V_warm_used, V_cold_used, warm_indices, cold_indices, n_items,
        )
        summary, records = eval_full_catalog(
            dataset, seed, fold_id, method="faithful_dropoutnet",
            score_fn=score_fn, train_inters=train_inters,
            test_inters=test_inters, n_items=n_items,
        )
        per_user_mean = per_user_mean_ndcg(records)
        # Secondary inference modes (for transparency in the report).
        for sm in secondary_inference_modes:
            if sm == chosen_inference_mode:
                continue
            V_warm_s, V_cold_s = build_inference_factors(
                sm, V_warm_wmf, sbert_warm, sbert_cold, tower, chosen_k,
            )
            s_fn = make_dropoutnet_score(
                U_wmf, V_warm_s, V_cold_s, warm_indices, cold_indices, n_items,
            )
            s_summary, s_records = eval_full_catalog(
                dataset, seed, fold_id,
                method=f"faithful_dropoutnet_{sm}",
                score_fn=s_fn, train_inters=train_inters,
                test_inters=test_inters, n_items=n_items,
            )
            secondary_summaries[sm] = {
                "NDCG@10": s_summary["NDCG@10"],
                "HR@10": s_summary["HR@10"],
                "MRR": s_summary["MRR"],
                "per_user_mean_NDCG@10": per_user_mean_ndcg(s_records),
                "n_eval_pairs": s_summary["n_eval"],
            }
            # Persist secondary records too (with explicit method labels).
            if perpair_path is not None:
                with perpair_path.open("a", encoding="utf-8") as f:
                    for r in s_records:
                        f.write(json.dumps(r) + "\n")
        print(
            f"    fold {fold_id}: mode={chosen_inference_mode} "
            f"NDCG@10={summary['NDCG@10']:.4f} "
            f"per-user-mean={per_user_mean:.4f} "
            f"HR@10={summary['HR@10']:.4f} MRR={summary['MRR']:.4f} "
            f"(WMF {wmf_t:.1f}s, tower {tower_t:.1f}s)",
            flush=True,
        )
        for sm, s in secondary_summaries.items():
            print(
                f"      [secondary {sm}: NDCG@10={s['NDCG@10']:.4f} "
                f"per-user={s['per_user_mean_NDCG@10']:.4f}]",
                flush=True,
            )
        if perpair_path is not None:
            with perpair_path.open("a", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r) + "\n")
        fold_results.append({
            "fold_id": fold_id,
            "seed": seed,
            "inference_mode": chosen_inference_mode,
            "NDCG@10": summary["NDCG@10"],
            "HR@10": summary["HR@10"],
            "MRR": summary["MRR"],
            "per_user_mean_NDCG@10": per_user_mean,
            "n_eval_pairs": summary["n_eval"],
            "n_users_eval": len({r["user_id"] for r in records}),
            "secondary_inference": secondary_summaries,
            "wmf_seconds": wmf_t,
            "tower_seconds": tower_t,
        })
        del tower, U_wmf, V_warm_wmf, X_warm
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return fold_results


# ------------------------------------------------------------------
# Top-level orchestration
# ------------------------------------------------------------------

def run_dataset(
    dataset: str,
    seeds: list[int],
    sweep_only_first_seed: bool = True,
    out_dir: Path | None = None,
    wmf_iters: int = 50,
    tower_epochs: int = 100,
    sweep_wmf_iters: int = 30,
    sweep_tower_epochs: int = 60,
    k_choices=(32, 64, 128),
    p_drop_choices=(0.3, 0.5, 0.7),
    reg_choices=(1.0, 10.0),
):
    print(f"\n{'#' * 70}\n#  FAITHFUL DROPOUTNET: {dataset.upper()}\n{'#' * 70}", flush=True)
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    print(f"  {n_users:,} users / {n_items:,} items / {len(interactions):,} interactions", flush=True)

    if out_dir is None:
        out_dir = Path(__file__).parent
    perpair_path = out_dir / f"results_faithful_dropoutnet_perpair_{dataset}.jsonl"
    if perpair_path.exists():
        perpair_path.unlink()

    # HP sweep on first seed (or all). For multi-seed honesty we pick HPs on
    # the first seed and then reuse the chosen (k, p_drop, reg, mode) for the
    # other seeds.
    chosen = None
    sweep_logs: list[dict[str, Any]] = []
    sweep_seeds = [seeds[0]] if sweep_only_first_seed else list(seeds)
    for sseed in sweep_seeds:
        print(f"\n  HP sweep on seed={sseed}", flush=True)
        info = hp_sweep(
            dataset, interactions, n_users, n_items, item_title_emb,
            seed=sseed, wmf_iters=sweep_wmf_iters, tower_epochs=sweep_tower_epochs,
            k_choices=k_choices, p_drop_choices=p_drop_choices,
            reg_choices=reg_choices,
        )
        sweep_logs.append({"seed": sseed, **info})
        if chosen is None:
            chosen = (info["k"], info["p_drop"], info["reg"], info["inference_mode"])

    print(
        f"\n  CHOSEN HPs for {dataset}: k={chosen[0]}  p_drop={chosen[1]}  "
        f"reg={chosen[2]}  mode={chosen[3]}\n",
        flush=True,
    )
    fold_results: list[dict[str, Any]] = []
    for seed in seeds:
        res = run_outer_eval(
            dataset, interactions, n_users, n_items, item_title_emb,
            seed=seed, chosen_k=chosen[0], chosen_p_drop=chosen[1],
            chosen_inference_mode=chosen[3],
            wmf_reg=chosen[2],
            wmf_iters=wmf_iters, tower_epochs=tower_epochs,
            perpair_path=perpair_path,
        )
        fold_results.extend(res)

    # Aggregate per-dataset summary.
    ndcg_per_fold = [r["NDCG@10"] for r in fold_results]
    per_user_ndcg_per_fold = [r["per_user_mean_NDCG@10"] for r in fold_results]
    hr_per_fold = [r["HR@10"] for r in fold_results]
    mrr_per_fold = [r["MRR"] for r in fold_results]
    summary = {
        "dataset": dataset,
        "n_users": n_users,
        "n_items": n_items,
        "n_interactions": len(interactions),
        "seeds": list(seeds),
        "chosen_k": int(chosen[0]),
        "chosen_p_drop": float(chosen[1]),
        "chosen_reg": float(chosen[2]),
        "chosen_inference_mode": chosen[3],
        "n_folds_per_seed": NUM_FOLDS,
        "n_folds_total": len(fold_results),
        "NDCG@10_mean": float(np.mean(ndcg_per_fold)) if ndcg_per_fold else 0.0,
        "NDCG@10_std": float(np.std(ndcg_per_fold)) if ndcg_per_fold else 0.0,
        "per_user_mean_NDCG@10_mean": float(np.mean(per_user_ndcg_per_fold)) if per_user_ndcg_per_fold else 0.0,
        "per_user_mean_NDCG@10_std": float(np.std(per_user_ndcg_per_fold)) if per_user_ndcg_per_fold else 0.0,
        "HR@10_mean": float(np.mean(hr_per_fold)) if hr_per_fold else 0.0,
        "HR@10_std": float(np.std(hr_per_fold)) if hr_per_fold else 0.0,
        "MRR_mean": float(np.mean(mrr_per_fold)) if mrr_per_fold else 0.0,
        "MRR_std": float(np.std(mrr_per_fold)) if mrr_per_fold else 0.0,
        "per_fold": fold_results,
        "hp_sweep_logs": sweep_logs,
        "perpair_file": perpair_path.name,
    }
    print(
        f"\n  >>> {dataset.upper()} summary: NDCG@10 = {summary['NDCG@10_mean']:.4f} "
        f"+- {summary['NDCG@10_std']:.4f}  "
        f"per-user NDCG@10 = {summary['per_user_mean_NDCG@10_mean']:.4f} "
        f"+- {summary['per_user_mean_NDCG@10_std']:.4f}\n",
        flush=True,
    )
    return summary


def main():
    ap = argparse.ArgumentParser(description="Faithful DropoutNet (WMF + DropoutNet item tower) cold-item baseline")
    ap.add_argument("datasets", nargs="*",
                    default=["beauty", "fashion", "instruments", "books"],
                    help="Datasets to run (default: all four)")
    ap.add_argument("--seeds", default="20260521,20260522,20260523",
                    help="Comma-separated outer seeds")
    ap.add_argument("--wmf-iters", type=int, default=50, help="ALS iterations for outer WMF")
    ap.add_argument("--tower-epochs", type=int, default=100, help="Tower epochs for outer eval")
    ap.add_argument("--sweep-wmf-iters", type=int, default=30, help="ALS iters during HP sweep")
    ap.add_argument("--sweep-tower-epochs", type=int, default=60, help="Tower epochs during HP sweep")
    ap.add_argument("--sweep-all-seeds", action="store_true",
                    help="Run HP sweep on every seed instead of only the first")
    ap.add_argument("--out", default=str(Path(__file__).parent),
                    help="Output directory")
    args = ap.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results_faithful_dropoutnet.json"
    # Merge with any existing per-dataset results so multi-call runs preserve
    # prior datasets. CLI overwrites only the datasets it processes.
    if results_path.exists():
        try:
            all_results = json.load(open(results_path, "r", encoding="utf-8"))
        except Exception:
            all_results = {}
    else:
        all_results = {}
    all_results.setdefault("schema_version", 1)
    all_results["method"] = "faithful_dropoutnet"
    all_results["fidelity"] = "wmf_implicit_als_plus_dropoutnet_item_tower"
    all_results["notes"] = (
        "Hu/Koren/Volinsky WMF (binary X, c=1+alpha*X) via implicit-ALS as "
        "the latent factor source, then DropoutNet item tower trained to "
        "reconstruct WMF item factors with Bernoulli input dropout on the "
        "CF branch. Symmetric inference: warm items use WMF V directly, "
        "cold items use tower([0; SBERT_cold]). Full-catalog cold-item "
        "ranking with the same item-GroupKFold splits as "
        "run_all_confirmatory.py."
    )
    all_results["seeds"] = seeds
    all_results.setdefault("datasets", {})

    for ds in args.datasets:
        t0 = time.time()
        summary = run_dataset(
            ds, seeds,
            sweep_only_first_seed=not args.sweep_all_seeds,
            out_dir=out_dir,
            wmf_iters=args.wmf_iters,
            tower_epochs=args.tower_epochs,
            sweep_wmf_iters=args.sweep_wmf_iters,
            sweep_tower_epochs=args.sweep_tower_epochs,
        )
        summary["wall_seconds"] = time.time() - t0
        all_results["datasets"][ds] = summary
        # Persist incrementally so a long run is never lost.
        with results_path.open("w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2,
                      default=lambda o: float(o) if hasattr(o, "item") else str(o))
        print(f"  >>> wrote {results_path} ({ds} done in {summary['wall_seconds']:.0f}s)", flush=True)

    # Final printout
    print("\n" + "=" * 80)
    print("FAITHFUL DROPOUTNET FINAL SUMMARY (cold-item full-catalog NDCG@10)")
    print("=" * 80)
    print(
        f"{'dataset':<14}{'k':>4}{'p':>5}{'reg':>5}{'mode':>30}"
        f"{'NDCG (per-pair)':>22}{'NDCG (per-user)':>22}{'HR@10':>9}{'MRR':>8}"
    )
    for ds in args.datasets:
        s = all_results["datasets"].get(ds)
        if not s:
            continue
        print(
            f"{ds:<14}{s['chosen_k']:>4}{s['chosen_p_drop']:>5.2f}{s.get('chosen_reg', 1.0):>5.1f}"
            f"{s.get('chosen_inference_mode',''):>30}"
            f"{s['NDCG@10_mean']:>14.4f}+-{s['NDCG@10_std']:.4f}"
            f"{s['per_user_mean_NDCG@10_mean']:>14.4f}+-{s['per_user_mean_NDCG@10_std']:.4f}"
            f"{s['HR@10_mean']:>9.4f}{s['MRR_mean']:>8.4f}"
        )


if __name__ == "__main__":
    main()
