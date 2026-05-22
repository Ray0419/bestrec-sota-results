"""Publication-grade confirmatory pipeline for BEST-Rec / LC2C++.

This runner intentionally writes outside the exploratory `_bestrec_run`
artifact directory:

    _bestrec_confirmatory/<run_id>/

It freezes the current LC2C++ candidate, evaluates cold items against the full
catalog, writes per-user JSONL records, and gates SOTA/publication claims on
strict manifest, baseline, significance, bootstrap, and Books warm-LOO checks.

The runner is designed to be harsh. If modern baselines are only local proxies
or if any required gate is missing, it writes an internal failure report and
returns non-zero rather than silently weakening the claim.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import pickle
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import Ridge

from artifact_utils import (
    CONFIRMATORY_LC2CPP_CONFIG,
    CONFIRMATORY_ROOT,
    DATASET_LABELS,
    DATASET_STATS,
    DATASETS,
    MANDATORY_SOTA_BASELINES,
    ROOT,
    RUN_DIR,
    append_manifest_run,
    machine_notes,
    metric_fmt,
    p_marker,
    read_json,
    rel,
    utc_now,
    write_json,
)
from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from run_warm_loo import (
    _score_ease,
    _score_higher_order_ease,
    _score_popularity,
    warm_ranking_eval,
)
from v5_utils import (
    NUM_FOLDS,
    SEED,
    TOP_K,
    build_X_sparse,
    content_sim_matrix,
    kcore_filter,
    make_warm_kfold,
    reindex,
)


COLD_METHODS = [
    "popularity",
    "content_direct",
    "blair_text",
    "faithful_dropoutnet",
    "clcrec_contrastive",
    "melt_tail_transfer",
    "lc2c_v2",
    "lc2cpp_validated_margin",
]

WARM_METHODS = ["popularity", "ease_pure", "higher_order_ease", "ease_sbert"]


def parse_csv(value: str, cast: Callable[[str], Any] = str) -> list[Any]:
    return [cast(x.strip()) for x in str(value).split(",") if x.strip()]


def make_run_id(profile: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{profile}_{stamp}"


def load_dataset(dataset: str) -> tuple[list[dict[str, Any]], dict[int, Any], int, int, np.ndarray]:
    k_core = DATASET_KCORE[dataset]
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], k_core)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{k_core}_dedup.pt"
    item_title_emb = torch.load(title_path, weights_only=True)
    return interactions, item_meta, n_users, n_items, item_title_emb


def build_warm_matrix(train_inters: list[dict[str, Any]], n_users: int, warm_indices: np.ndarray) -> tuple[csr_matrix, np.ndarray]:
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
    return X_sparse, X_sparse.toarray().astype(np.float32)


def user_train_and_test(train_inters: list[dict[str, Any]], test_inters: list[dict[str, Any]]) -> tuple[dict[int, set[int]], dict[int, list[int]]]:
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
    train_inters: list[dict[str, Any]],
    test_inters: list[dict[str, Any]],
    n_items: int,
    batch_size: int = 192,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Rank each cold target against the full unseen catalog.

    Only the user's training history is masked. Other held-out positives remain
    in the candidate set, matching the strict "target competes with all unseen
    warm and cold candidates" interpretation.
    """
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
            raise ValueError(f"{method} returned scores with shape {scores.shape}, expected {(len(batch), n_items)}")
        for row_idx, user_id in enumerate(batch):
            seen = user_train[user_id]
            if seen:
                scores[row_idx, list(seen)] = -np.inf
            for target_item in user_test[user_id]:
                target_score = scores[row_idx, target_item]
                rank0 = int((scores[row_idx] > target_score).sum())
                h = 1.0 if rank0 < TOP_K else 0.0
                n = 1.0 / math.log2(rank0 + 2) if rank0 < TOP_K else 0.0
                r = 1.0 / (rank0 + 1)
                ndcg.append(n)
                hr.append(h)
                rr.append(r)
                records.append(
                    {
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
                    }
                )
    return (
        {
            "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
            "HR@10": float(np.mean(hr)) if hr else 0.0,
            "MRR": float(np.mean(rr)) if rr else 0.0,
            "n_eval": len(records),
        },
        records,
    )


def zscore_rows(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    return (x - x.mean(axis=1, keepdims=True)) / np.maximum(x.std(axis=1, keepdims=True), eps)


def normalized_embeddings(item_title_emb: Any) -> np.ndarray:
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    return emb / np.maximum(norms, 1e-12)


def make_popularity_full(train_inters: list[dict[str, Any]], n_items: int) -> Callable[[np.ndarray], np.ndarray]:
    pop = np.zeros(n_items, dtype=np.float32)
    for inter in train_inters:
        pop[int(inter["item_id"])] += 1.0

    def score(user_ids: np.ndarray) -> np.ndarray:
        return np.tile(pop, (len(user_ids), 1))

    return score


def make_content_direct_full(Xw: np.ndarray, warm_indices: np.ndarray, S_content: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    S_w_all = S_content[warm_indices, :].astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        return Xw[user_ids] @ S_w_all

    return score


def make_blair_text_full(Xw: np.ndarray, warm_indices: np.ndarray, item_title_emb: Any) -> Callable[[np.ndarray], np.ndarray]:
    """BLaIR-style dual-encoder retrieval proxy using frozen title embeddings.

    This is a same-split, same-catalog retrieval comparator, not an official
    BLaIR checkpoint reproduction. The baseline audit marks that fidelity.
    """
    emb = normalized_embeddings(item_title_emb)
    emb_warm = emb[warm_indices]
    user_counts = np.maximum(Xw.sum(axis=1, keepdims=True), 1.0).astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        profile = (Xw[user_ids] @ emb_warm) / user_counts[user_ids]
        profile = profile / np.maximum(np.linalg.norm(profile, axis=1, keepdims=True), 1e-12)
        return profile @ emb.T

    return score


def make_lc2c_v2_full(
    Xw: np.ndarray,
    B_warm: np.ndarray,
    item_title_emb: Any,
    warm_indices: np.ndarray,
    cold_indices: np.ndarray,
    n_items: int,
    mu: float = 1.0,
    sample_weight: np.ndarray | None = None,
) -> Callable[[np.ndarray], np.ndarray]:
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]
    SBERT_cold = emb[cold_indices]
    reg = Ridge(alpha=mu)
    reg.fit(SBERT_warm, B_warm.T.astype(np.float32), sample_weight=sample_weight)
    B_hat_cold = (SBERT_cold @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        out = np.empty((len(user_ids), n_items), dtype=np.float32)
        out[:, warm_indices] = Xw[user_ids] @ B_warm
        out[:, cold_indices] = Xw[user_ids] @ B_hat_cold
        return out

    return score


def make_z_fusion_full(score_a: Callable[[np.ndarray], np.ndarray], score_b: Callable[[np.ndarray], np.ndarray], weight_a: float) -> Callable[[np.ndarray], np.ndarray]:
    weight_a = float(weight_a)
    weight_b = 1.0 - weight_a

    def score(user_ids: np.ndarray) -> np.ndarray:
        return weight_a * zscore_rows(score_a(user_ids)) + weight_b * zscore_rows(score_b(user_ids))

    return score


def make_melt_tail_transfer_full(
    Xw: np.ndarray,
    B_warm: np.ndarray,
    item_title_emb: Any,
    warm_indices: np.ndarray,
    cold_indices: np.ndarray,
    n_items: int,
) -> Callable[[np.ndarray], np.ndarray]:
    pop = np.maximum(Xw.sum(axis=0), 0.0)
    weights = (1.0 / np.log2(pop + 2.0)).astype(np.float32)
    weights = weights / np.maximum(weights.mean(), 1e-8)
    return make_lc2c_v2_full(
        Xw,
        B_warm,
        item_title_emb,
        warm_indices,
        cold_indices,
        n_items,
        mu=3.0,
        sample_weight=weights,
    )


class _ItemTower(torch.nn.Module):
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


def svd_reference_factors(Xw: np.ndarray, latent_dim: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    k = max(2, min(latent_dim, Xw.shape[0] - 1, Xw.shape[1] - 1))
    svd = TruncatedSVD(n_components=k, random_state=seed)
    U_ref = svd.fit_transform(Xw).astype(np.float32)
    V_ref = svd.components_.T.astype(np.float32)
    return U_ref, V_ref


def make_dropoutnet_full(
    Xw: np.ndarray,
    item_title_emb: Any,
    warm_indices: np.ndarray,
    cold_indices: np.ndarray,
    n_items: int,
    seed: int,
    latent_dim: int = 64,
    epochs: int = 80,
    lr: float = 1e-3,
    dropout_p: float = 0.5,
    batch_size: int = 256,
) -> Callable[[np.ndarray], np.ndarray]:
    """WMF/latent-factor DropoutNet-style item tower for full-catalog cold items.

    The current implementation uses deterministic SVD reference factors as the
    local latent-factor source because this repository does not include a WMF
    solver. The baseline audit records this as a local reimplementation rather
    than an official faithful DropoutNet reproduction.
    """
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    U_ref, V_ref = svd_reference_factors(Xw, latent_dim, seed)
    k = V_ref.shape[1]
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    content_warm = emb[warm_indices]
    content_cold = emb[cold_indices]
    tower = _ItemTower(k + content_warm.shape[1], k).to(device)
    opt = torch.optim.Adam(tower.parameters(), lr=lr)
    V_t = torch.from_numpy(V_ref).to(device)
    C_t = torch.from_numpy(content_warm).to(device)
    rng = np.random.RandomState(seed)
    n_warm = len(warm_indices)
    for _ in range(epochs):
        perm = rng.permutation(n_warm)
        for start in range(0, n_warm, batch_size):
            idx = perm[start:start + batch_size]
            if len(idx) == 0:
                continue
            idx_t = torch.from_numpy(idx).to(device)
            cf = V_t[idx_t].clone()
            drop = (torch.rand((len(idx), 1), device=device) < dropout_p)
            cf = torch.where(drop, torch.zeros_like(cf), cf)
            inp = torch.cat([cf, C_t[idx_t]], dim=1)
            pred = tower(inp)
            loss = ((pred - V_t[idx_t]) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
    tower.eval()
    with torch.no_grad():
        zero_cf = torch.zeros((len(cold_indices), k), device=device)
        cold_t = torch.from_numpy(content_cold).to(device)
        V_cold = tower(torch.cat([zero_cf, cold_t], dim=1)).cpu().numpy().astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        out = np.empty((len(user_ids), n_items), dtype=np.float32)
        out[:, warm_indices] = U_ref[user_ids] @ V_ref.T
        out[:, cold_indices] = U_ref[user_ids] @ V_cold.T
        return out

    return score


def make_contrastive_cold_full(
    Xw: np.ndarray,
    item_title_emb: Any,
    warm_indices: np.ndarray,
    cold_indices: np.ndarray,
    n_items: int,
    seed: int,
    latent_dim: int = 64,
    epochs: int = 60,
    lr: float = 1e-3,
    temperature: float = 0.07,
    batch_size: int = 256,
) -> Callable[[np.ndarray], np.ndarray]:
    """CLCRec/CCFCRec-style contrastive content-to-CF projection.

    This is a local, same-data contrastive comparator. The audit distinguishes it
    from an official CLCRec/CCFCRec codebase run.
    """
    torch.manual_seed(seed + 17)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed + 17)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    U_ref, V_ref = svd_reference_factors(Xw, latent_dim, seed + 17)
    k = V_ref.shape[1]
    emb = normalized_embeddings(item_title_emb)
    C_warm = emb[warm_indices].astype(np.float32)
    C_cold = emb[cold_indices].astype(np.float32)
    tower = _ItemTower(C_warm.shape[1], k).to(device)
    opt = torch.optim.Adam(tower.parameters(), lr=lr)
    C_t = torch.from_numpy(C_warm).to(device)
    V_t = torch.from_numpy(V_ref).to(device)
    V_norm_all = torch.nn.functional.normalize(V_t, dim=1)
    rng = np.random.RandomState(seed + 17)
    n_warm = len(warm_indices)
    for _ in range(epochs):
        perm = rng.permutation(n_warm)
        for start in range(0, n_warm, batch_size):
            idx = perm[start:start + batch_size]
            if len(idx) == 0:
                continue
            idx_t = torch.from_numpy(idx).long().to(device)
            z = tower(C_t[idx_t])
            mse = ((z - V_t[idx_t]) ** 2).mean()
            logits = torch.nn.functional.normalize(z, dim=1) @ V_norm_all.T / temperature
            ce = torch.nn.functional.cross_entropy(logits, idx_t)
            loss = mse + 0.1 * ce
            opt.zero_grad()
            loss.backward()
            opt.step()
    tower.eval()
    with torch.no_grad():
        V_cold = tower(torch.from_numpy(C_cold).to(device)).cpu().numpy().astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        out = np.empty((len(user_ids), n_items), dtype=np.float32)
        out[:, warm_indices] = U_ref[user_ids] @ V_ref.T
        out[:, cold_indices] = U_ref[user_ids] @ V_cold.T
        return out

    return score


def select_lc2cpp_weight(
    dataset: str,
    seed: int,
    fold_id: int,
    outer_train: list[dict[str, Any]],
    outer_cold_items: set[int],
    interactions: list[dict[str, Any]],
    n_users: int,
    n_items: int,
    item_title_emb: Any,
    S_content: np.ndarray,
    lam: float,
    beta: float,
) -> dict[str, Any]:
    all_outer_warm = np.array(sorted(set(range(n_items)) - set(outer_cold_items)), dtype=np.int32)
    rng = np.random.RandomState(seed + 1000 * (fold_id + 1))
    shuffled = all_outer_warm.copy()
    rng.shuffle(shuffled)
    n_val = max(1, int(round(len(shuffled) * CONFIRMATORY_LC2CPP_CONFIG["validation_fraction"])))
    val_items = set(int(x) for x in shuffled[:n_val])
    inner_cold = set(outer_cold_items) | val_items
    inner_warm = np.array(sorted(set(range(n_items)) - inner_cold), dtype=np.int32)
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    if not val_inters:
        return {
            "fold_id": fold_id,
            "selected_weight": 1.0,
            "margin_weight": 1.0,
            "base_val_ndcg10": 0.0,
            "best_val_ndcg10": 0.0,
            "reason": "no_validation_interactions",
        }
    X_sparse, Xw = build_warm_matrix(inner_train, n_users, inner_warm)
    S_warm = S_content[np.ix_(inner_warm, inner_warm)]
    B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
    inner_cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    score_lc = make_lc2c_v2_full(Xw, B_warm, item_title_emb, inner_warm, inner_cold_arr, n_items)
    score_content = make_content_direct_full(Xw, inner_warm, S_content)
    val_scores: dict[str, float] = {}
    best_w = 1.0
    best_score = -1.0
    for weight in CONFIRMATORY_LC2CPP_CONFIG["weights"]:
        score_fn = score_lc if float(weight) == 1.0 else make_z_fusion_full(score_lc, score_content, float(weight))
        result, _ = eval_full_catalog(
            dataset,
            seed,
            fold_id,
            f"lc2cpp_val_{weight}",
            score_fn,
            inner_train,
            val_inters,
            n_items,
        )
        val_scores[f"{float(weight):.3f}"] = result["NDCG@10"]
        if result["NDCG@10"] > best_score:
            best_score = result["NDCG@10"]
            best_w = float(weight)
    base_val = val_scores.get("1.000", best_score)
    margin = CONFIRMATORY_LC2CPP_CONFIG["minimum_validation_margin"]
    margin_w = best_w if best_score - base_val >= margin else 1.0
    del X_sparse, Xw, B_warm
    gc.collect()
    return {
        "fold_id": fold_id,
        "selected_weight": best_w,
        "margin_weight": margin_w,
        "base_val_ndcg10": base_val,
        "best_val_ndcg10": best_score,
        "min_margin": margin,
        "val_scores": val_scores,
    }


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"NDCG@10": None, "HR@10": None, "MRR": None, "n_records": 0}
    return {
        "NDCG@10": float(np.mean([r["ndcg10"] for r in records])),
        "HR@10": float(np.mean([r["hr10"] for r in records])),
        "MRR": float(np.mean([r["rr"] for r in records])),
        "n_records": len(records),
    }


def run_warm_confirmatory_dataset(dataset: str, seeds: list[int], run_dir: Path) -> dict[str, Any]:
    interactions, _, n_users, n_items, item_title_emb = load_dataset(dataset)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    k_core = DATASET_KCORE[dataset]
    lam, beta = HP[dataset]
    jsonl_path = run_dir / f"warm_records_{dataset}.jsonl"
    if jsonl_path.exists():
        jsonl_path.unlink()
    method_records: dict[str, list[dict[str, Any]]] = {m: [] for m in WARM_METHODS}
    fold_counts: dict[str, list[int]] = {m: [] for m in WARM_METHODS}
    for seed in seeds:
        splits = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr_idx, te_idx) in enumerate(splits):
            train_inters = [interactions[i] for i in tr_idx]
            test_inters = [interactions[i] for i in te_idx]
            X_sparse = build_X_sparse(train_inters, n_users, n_items)
            scorers = {
                "popularity": _score_popularity(train_inters, n_items),
                "ease_pure": _score_ease(X_sparse, lam=lam, beta=0.0, S_content=None)[0],
                "higher_order_ease": _score_higher_order_ease(X_sparse, lam=lam, beta=beta, S_content=S_content, alpha=0.3),
                "ease_sbert": _score_ease(X_sparse, lam=lam, beta=beta, S_content=S_content)[0],
            }
            for method, scorer in scorers.items():
                result = warm_ranking_eval(scorer, train_inters, test_inters, n_users, n_items, max_users=0, seed=seed)
                rows = []
                for user_id, target_item, ndcg, hr, rr in zip(
                    result["user_id_per_pair"],
                    result["target_item_id_per_pair"],
                    result["ndcg_per_pair"],
                    result["hr_per_pair"],
                    result["rr_per_pair"],
                ):
                    rows.append(
                        {
                            "dataset": dataset,
                            "fold_id": fold_id,
                            "seed": seed,
                            "method": method,
                            "user_id": int(user_id),
                            "target_item_id": int(target_item),
                            "ndcg10": float(ndcg),
                            "hr10": float(hr),
                            "rr": float(rr),
                        }
                    )
                append_jsonl(jsonl_path, rows)
                method_records[method].extend(rows)
                fold_counts[method].append(len(rows))
                print(f"  warm {dataset} seed={seed} fold={fold_id} {method}: NDCG@10={result['NDCG@10']:.4f} n={len(rows)}")
            del X_sparse
            gc.collect()
    return {
        "dataset": dataset,
        "k_core": k_core,
        "n_users": n_users,
        "n_items": n_items,
        "methods": {m: summarize_records(rows) for m, rows in method_records.items()},
        "fold_counts": fold_counts,
        "record_file": jsonl_path.name,
    }


def run_cold_confirmatory_dataset(dataset: str, seeds: list[int], run_dir: Path, bootstrap_reps: int) -> dict[str, Any]:
    interactions, _, n_users, n_items, item_title_emb = load_dataset(dataset)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k_core = DATASET_KCORE[dataset]
    jsonl_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if jsonl_path.exists():
        jsonl_path.unlink()
    method_records: dict[str, list[dict[str, Any]]] = {m: [] for m in COLD_METHODS}
    selection_log: list[dict[str, Any]] = []
    baseline_errors: dict[str, str] = {}
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
            print(f"  cold {dataset} seed={seed} fold={fold_id}: full catalog |cold|={len(cold_items):,}")
            train_inters = [interactions[i] for i in tr_idx]
            test_inters = [interactions[i] for i in te_idx]
            warm_indices = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
            cold_indices = np.array(sorted(cold_items), dtype=np.int32)
            X_sparse, Xw = build_warm_matrix(train_inters, n_users, warm_indices)
            S_warm = S_content[np.ix_(warm_indices, warm_indices)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
            score_lc = make_lc2c_v2_full(Xw, B_warm, item_title_emb, warm_indices, cold_indices, n_items)
            score_content = make_content_direct_full(Xw, warm_indices, S_content)
            weight_info = select_lc2cpp_weight(
                dataset,
                seed,
                fold_id,
                train_inters,
                set(cold_items),
                interactions,
                n_users,
                n_items,
                item_title_emb,
                S_content,
                lam,
                beta,
            )
            selection_log.append(weight_info | {"seed": seed})
            margin_w = float(weight_info["margin_weight"])
            score_lc2cpp = score_lc if margin_w == 1.0 else make_z_fusion_full(score_lc, score_content, margin_w)
            scorers: dict[str, Callable[[np.ndarray], np.ndarray]] = {
                "popularity": make_popularity_full(train_inters, n_items),
                "content_direct": score_content,
                "blair_text": make_blair_text_full(Xw, warm_indices, item_title_emb),
                "melt_tail_transfer": make_melt_tail_transfer_full(Xw, B_warm, item_title_emb, warm_indices, cold_indices, n_items),
                "lc2c_v2": score_lc,
                "lc2cpp_validated_margin": score_lc2cpp,
            }
            for method, factory in (
                ("faithful_dropoutnet", lambda: make_dropoutnet_full(Xw, item_title_emb, warm_indices, cold_indices, n_items, seed=seed)),
                ("clcrec_contrastive", lambda: make_contrastive_cold_full(Xw, item_title_emb, warm_indices, cold_indices, n_items, seed=seed)),
            ):
                try:
                    scorers[method] = factory()
                except Exception as exc:  # keep the run auditable even if a deep baseline fails
                    baseline_errors[method] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            for method in COLD_METHODS:
                if method not in scorers:
                    continue
                result, rows = eval_full_catalog(
                    dataset,
                    seed,
                    fold_id,
                    method,
                    scorers[method],
                    train_inters,
                    test_inters,
                    n_items,
                )
                append_jsonl(jsonl_path, rows)
                method_records[method].extend(rows)
                print(f"    {method:<26} NDCG@10={result['NDCG@10']:.4f} n={len(rows)}")
            del X_sparse, Xw, B_warm, S_warm
            gc.collect()
    return {
        "dataset": dataset,
        "k_core": k_core,
        "n_users": n_users,
        "n_items": n_items,
        "candidate_scope": "full_catalog",
        "methods": {m: summarize_records(rows) for m, rows in method_records.items()},
        "selected_weights": selection_log,
        "baseline_errors": baseline_errors,
        "record_file": jsonl_path.name,
        "bootstrap_reps": bootstrap_reps,
    }


def user_means(rows: list[dict[str, Any]]) -> dict[int, float]:
    by_user: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        by_user[int(row["user_id"])].append(float(row["ndcg10"]))
    return {u: float(np.mean(vals)) for u, vals in by_user.items()}


def keyed_values(rows: list[dict[str, Any]]) -> dict[tuple[int, int, int, int], float]:
    return {
        (
            int(row["seed"]),
            int(row["fold_id"]),
            int(row["user_id"]),
            int(row["target_item_id"]),
        ): float(row["ndcg10"])
        for row in rows
    }


def holm_adjust(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(comparisons, key=lambda x: x["p_raw"])
    m = len(sorted_rows)
    active = True
    adjusted: list[dict[str, Any]] = []
    for i, row in enumerate(sorted_rows):
        threshold = 0.05 / max(1, m - i)
        sig = bool(active and row["p_raw"] <= threshold)
        if not sig:
            active = False
        adjusted.append(row | {"holm_threshold": threshold, "holm_significant": sig, "marker": p_marker(row["p_raw"]) if sig else "n.s."})
    return sorted(adjusted, key=lambda x: x["comparison"])


def clustered_bootstrap_ci(
    candidate_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    reps: int,
    seed: int = 20260521,
) -> dict[str, Any]:
    cand = keyed_values(candidate_rows)
    base = keyed_values(baseline_rows)
    common = sorted(set(cand) & set(base))
    if not common:
        return {"delta_point": None, "ci_lo_95": None, "ci_hi_95": None, "B_replicates": reps, "resampling_unit": "user/item/fold"}
    diffs = {k: cand[k] - base[k] for k in common}
    users = sorted({k[2] for k in common})
    items = sorted({k[3] for k in common})
    folds = sorted({(k[0], k[1]) for k in common})
    by_tuple = Counter(common)
    point = float(np.mean(list(diffs.values())))
    rng = np.random.RandomState(seed)
    samples: list[float] = []
    for _ in range(reps):
        user_w = Counter(rng.choice(users, size=len(users), replace=True).tolist())
        item_w = Counter(rng.choice(items, size=len(items), replace=True).tolist())
        fold_weight = Counter()
        for idx, count in Counter(rng.choice(len(folds), size=len(folds), replace=True).tolist()).items():
            fold_weight[folds[int(idx)]] += count
        num = 0.0
        den = 0
        for key in common:
            w = user_w[key[2]] * item_w[key[3]] * fold_weight[(key[0], key[1])] * by_tuple[key]
            if w:
                num += w * diffs[key]
                den += w
        if den:
            samples.append(num / den)
    if not samples:
        return {"delta_point": point, "ci_lo_95": None, "ci_hi_95": None, "B_replicates": reps, "resampling_unit": "user/item/fold"}
    return {
        "delta_point": point,
        "ci_lo_95": float(np.percentile(samples, 2.5)),
        "ci_hi_95": float(np.percentile(samples, 97.5)),
        "B_replicates": reps,
        "resampling_unit": "user/item/fold clustered bootstrap",
    }


def compute_significance(cold_records: dict[str, dict[str, list[dict[str, Any]]]], bootstrap_reps: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema_version": 1,
        "correction_family": "Holm within each dataset across LC2C++ vs cold full-catalog baselines",
        "sample_unit": "per-user mean full-catalog cold-item NDCG@10",
        "candidate_method": "lc2cpp_validated_margin",
        "cold_full_catalog": {},
    }
    for dataset, by_method in cold_records.items():
        candidate = by_method.get("lc2cpp_validated_margin", [])
        candidate_mean = summarize_records(candidate)["NDCG@10"]
        baseline_means = {
            method: summarize_records(rows)["NDCG@10"]
            for method, rows in by_method.items()
            if method != "lc2cpp_validated_margin" and rows
        }
        best_baseline = max(baseline_means, key=lambda m: baseline_means[m]) if baseline_means else None
        comparisons: list[dict[str, Any]] = []
        cand_user = user_means(candidate)
        for method, rows in by_method.items():
            if method == "lc2cpp_validated_margin" or not rows:
                continue
            base_user = user_means(rows)
            common = sorted(set(cand_user) & set(base_user))
            diffs = np.array([cand_user[u] - base_user[u] for u in common], dtype=np.float64)
            if len(diffs) == 0 or np.allclose(diffs, 0):
                p_raw = 1.0
            else:
                p_raw = float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
            comparisons.append(
                {
                    "comparison": f"lc2cpp_validated_margin > {method}",
                    "baseline": method,
                    "n_users": len(common),
                    "candidate_ndcg10": candidate_mean,
                    "baseline_ndcg10": summarize_records(rows)["NDCG@10"],
                    "mean_delta": float(np.mean(diffs)) if len(diffs) else None,
                    "positive_users": int((diffs > 0).sum()),
                    "negative_users": int((diffs < 0).sum()),
                    "zero_users": int((diffs == 0).sum()),
                    "p_raw": p_raw,
                }
            )
        adjusted = holm_adjust(comparisons)
        best_boot = clustered_bootstrap_ci(candidate, by_method.get(best_baseline, []), bootstrap_reps) if best_baseline else {}
        out["cold_full_catalog"][dataset] = {
            "candidate_ndcg10": candidate_mean,
            "best_baseline": best_baseline,
            "best_baseline_ndcg10": baseline_means.get(best_baseline) if best_baseline else None,
            "comparisons": adjusted,
            "best_baseline_bootstrap": best_boot,
        }
    return out


def baseline_audit_payload(seeds: list[int], cold_results: dict[str, Any], warm_results: dict[str, Any]) -> dict[str, Any]:
    def cold_method_has_records(method: str) -> bool:
        for dataset in DATASETS:
            if cold_results.get(dataset, {}).get("methods", {}).get(method, {}).get("n_records", 0):
                return True
        return False

    def cold_method_errors(method: str) -> list[str]:
        errors = []
        for dataset in DATASETS:
            err = cold_results.get(dataset, {}).get("baseline_errors", {}).get(method)
            if err:
                errors.append(f"{dataset}: {err}")
        return errors

    def proxy_status(method: str) -> str:
        if cold_method_errors(method):
            return "failed"
        return "proxy_complete" if cold_method_has_records(method) else "not_run"

    baselines: dict[str, Any] = {
        "faithful_dropoutnet": {
            "status": proxy_status("faithful_dropoutnet"),
            "fidelity": "svd_reference_dropoutnet_not_wmf_backed",
            "seeds": seeds,
            "config": {"latent_dim": 64, "epochs": 80, "dropout_p": 0.5},
            "notes": "Runs the DropoutNet item-tower mechanism but uses SVD reference factors because this repository has no WMF solver.",
            "errors": cold_method_errors("faithful_dropoutnet"),
        },
        "clcrec_contrastive": {
            "status": proxy_status("clcrec_contrastive"),
            "fidelity": "local_contrastive_content_to_cf_projection_not_official_clcrec_ccfcrec",
            "seeds": seeds,
            "config": {"latent_dim": 64, "epochs": 60, "temperature": 0.07},
            "errors": cold_method_errors("clcrec_contrastive"),
        },
        "melt_tail_transfer": {
            "status": proxy_status("melt_tail_transfer"),
            "fidelity": "tail_weighted_lc2c_transfer_not_official_melt",
            "seeds": seeds,
            "config": {"sample_weight": "inverse_log_item_popularity", "ridge_alpha": 3.0},
            "errors": cold_method_errors("melt_tail_transfer"),
        },
        "blair_text": {
            "status": proxy_status("blair_text"),
            "fidelity": "frozen_sbert_dual_encoder_profile_not_official_blair_checkpoint",
            "seeds": seeds,
            "config": {"encoder": "cached SBERT title embeddings", "user_profile": "mean interacted item embedding"},
            "errors": cold_method_errors("blair_text"),
        },
        "tiger_liger_retrieval": {
            "status": "not_run",
            "fidelity": "missing_official_generative_retrieval_training_and_tokenizer",
            "seeds": seeds,
            "notes": "No same-split official TIGER/LIGER implementation is present in this repository.",
        },
        "lightgcn": {
            "status": "not_run",
            "fidelity": "missing_tuned_multiseed_confirmatory_warm_run",
            "seeds": seeds,
        },
        "multivae": {
            "status": "not_run",
            "fidelity": "missing_tuned_multiseed_confirmatory_warm_run",
            "seeds": seeds,
        },
        "ials": {
            "status": "not_run",
            "fidelity": "missing_sparse_tuned_multiseed_confirmatory_warm_run",
            "seeds": seeds,
        },
    }
    return {
        "schema_version": 1,
        "baselines": baselines,
        "required_for_publication": list(MANDATORY_SOTA_BASELINES),
        "status_definition": {
            "complete": "official or publication-grade implementation with frozen config, seeds, runtime, and records",
            "proxy_complete": "local comparator generated under same splits but not acceptable as external SOTA evidence",
            "not_run": "required audit item missing",
        },
    }


def build_tables(
    run_dir: Path,
    warm_results: dict[str, Any],
    cold_results: dict[str, Any],
    significance: dict[str, Any],
    baseline_audit: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    protocol_rows = []
    cold_rows = []
    sig_rows = []
    for dataset in DATASETS:
        stats = DATASET_STATS[dataset]
        warm_counts = warm_results.get(dataset, {}).get("fold_counts", {}).get("ease_sbert", [])
        cold_summary = cold_results.get(dataset, {}).get("methods", {})
        protocol_rows.append(
            [
                DATASET_LABELS[dataset],
                ", ".join(str(x) for x in warm_counts[:NUM_FOLDS]) if warm_counts else "-",
                str(cold_summary.get("lc2cpp_validated_margin", {}).get("n_records", "-")),
                "full_catalog",
                "full" if dataset != "books" or (warm_counts and min(warm_counts) >= stats["users"]) else "capped_or_missing",
            ]
        )
        cold_rows.append(
            [
                DATASET_LABELS[dataset],
                *[metric_fmt(cold_summary.get(m, {}).get("NDCG@10")) for m in COLD_METHODS],
            ]
        )
        ds_sig = significance.get("cold_full_catalog", {}).get(dataset, {})
        best = ds_sig.get("best_baseline")
        best_comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == best), {})
        boot = ds_sig.get("best_baseline_bootstrap", {})
        sig_rows.append(
            [
                DATASET_LABELS[dataset],
                best or "-",
                metric_fmt(best_comp.get("mean_delta")),
                best_comp.get("marker", "n.s."),
                metric_fmt(boot.get("ci_lo_95")),
                metric_fmt(boot.get("ci_hi_95")),
            ]
        )
    payload = {
        "schema_version": 1,
        "confirmatory": True,
        "primary_candidate_scope": "full_catalog",
        "algorithm_config": CONFIRMATORY_LC2CPP_CONFIG,
        "sota_claim_allowed": gate["passed"],
        "publication_gate": gate,
        "sources": {
            "results_final": "results_final.json",
            "significance": "significance.json",
            "baseline_audit": "baseline_audit.json",
            "manifest": "results_manifest.json",
        },
        "table_4_2_protocol_sizes": {
            "columns": ["Dataset", "Warm test pairs/fold", "Cold full-catalog records", "Cold candidate scope", "Books warm status"],
            "rows": protocol_rows,
        },
        "table_confirmatory_cold_full_catalog": {
            "columns": ["Dataset", *COLD_METHODS],
            "rows": cold_rows,
        },
        "table_confirmatory_significance": {
            "columns": ["Dataset", "Best baseline", "Delta", "Holm marker", "CI low", "CI high"],
            "rows": sig_rows,
        },
        "baseline_audit": baseline_audit,
    }
    write_json(run_dir / "tables.json", payload)
    return payload


def evaluate_gate(warm_results: dict[str, Any], cold_results: dict[str, Any], significance: dict[str, Any], baseline_audit: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for dataset in DATASETS:
        warm_counts = warm_results.get(dataset, {}).get("fold_counts", {}).get("ease_sbert", [])
        if dataset == "books" and (not warm_counts or min(warm_counts) < DATASET_STATS["books"]["users"]):
            failures.append(f"Books warm-LOO is not full: counts={warm_counts}, required={DATASET_STATS['books']['users']}.")
        if cold_results.get(dataset, {}).get("candidate_scope") != "full_catalog":
            failures.append(f"{dataset} cold-item candidate scope is not full_catalog.")
        ds_sig = significance.get("cold_full_catalog", {}).get(dataset, {})
        best = ds_sig.get("best_baseline")
        if not best:
            failures.append(f"{dataset} has no best baseline comparison.")
            continue
        best_comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == best), None)
        if not best_comp or not best_comp.get("holm_significant"):
            failures.append(f"{dataset} LC2C++ is not Holm-significant against best baseline {best}.")
        boot = ds_sig.get("best_baseline_bootstrap", {})
        if boot.get("ci_lo_95") is None or float(boot.get("ci_lo_95")) <= 0:
            failures.append(f"{dataset} clustered bootstrap lower CI is not above zero against {best}.")
        lc2c_comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == "lc2c_v2"), None)
        if not lc2c_comp or not lc2c_comp.get("holm_significant"):
            failures.append(f"{dataset} LC2C++ is not Holm-significant against LC2C V2.")
    for name in MANDATORY_SOTA_BASELINES:
        entry = baseline_audit.get("baselines", {}).get(name, {})
        if entry.get("status") != "complete":
            failures.append(f"Mandatory baseline {name} is not publication-grade complete: status={entry.get('status')}.")
    macro_candidate = []
    macro_best = []
    all_dataset_wins = True
    for dataset in DATASETS:
        ds = significance.get("cold_full_catalog", {}).get(dataset, {})
        cand = ds.get("candidate_ndcg10")
        best = ds.get("best_baseline_ndcg10")
        if cand is None or best is None:
            all_dataset_wins = False
            continue
        macro_candidate.append(float(cand))
        macro_best.append(float(best))
        if float(cand) <= float(best):
            all_dataset_wins = False
            failures.append(f"{dataset} LC2C++ does not beat the best baseline in NDCG@10.")
    if macro_candidate and macro_best and float(np.mean(macro_candidate)) <= float(np.mean(macro_best)):
        failures.append("LC2C++ does not beat the best baseline on macro-average cold full-catalog NDCG@10.")
    if not all_dataset_wins:
        failures.append("LC2C++ does not win all four datasets on primary cold full-catalog NDCG@10.")
    return {
        "passed": not failures,
        "failures": failures,
        "checked_at_utc": utc_now(),
        "standard": "publication/SOTA gate: full catalog, modern baselines, Holm Wilcoxon, clustered bootstrap, full Books warm LOO",
    }


def write_internal_failure_report(run_dir: Path, gate: dict[str, Any], significance: dict[str, Any]) -> None:
    lines = [
        "# Internal SOTA Failure Report",
        "",
        f"Run directory: `{run_dir}`",
        f"Generated: {utc_now()}",
        "",
        "## Decision",
        "",
        "Reject for SOTA/publication claims under the strict confirmatory standard.",
        "",
        "## Blocking Failures",
        "",
    ]
    for item in gate.get("failures", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Cold Full-Catalog Summary", ""])
    for dataset, block in significance.get("cold_full_catalog", {}).items():
        lines.append(
            f"- {dataset}: LC2C++={metric_fmt(block.get('candidate_ndcg10'))}, "
            f"best_baseline={block.get('best_baseline')} ({metric_fmt(block.get('best_baseline_ndcg10'))})"
        )
    lines.extend(
        [
            "",
            "## Required Next Action",
            "",
            "Do not claim SOTA. Replace proxy or missing comparators with publication-grade official/same-split runs, rerun the frozen confirmatory command, and rebuild only from this confirmatory directory.",
            "",
        ]
    )
    (run_dir / "INTERNAL_SOTA_FAILURE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="sota-confirmatory")
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default="20260521,20260522,20260523,20260524,20260525")
    parser.add_argument("--candidate-scope", choices=["full_catalog"], default="full_catalog")
    parser.add_argument("--no-books-cap", action="store_true")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--skip-warm", action="store_true")
    parser.add_argument("--skip-cold", action="store_true")
    parser.add_argument("--bootstrap-reps", type=int, default=500)
    parser.add_argument("--allow-failure-report", action="store_true", help="Return 0 after writing a failure report.")
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    if set(datasets) != set(DATASETS):
        print("WARNING: publication gate expects all four datasets; partial runs will fail strict validation.")
    if not args.no_books_cap:
        print("ERROR: confirmatory publication run requires --no-books-cap.")
        return 2
    run_id = args.run_id or make_run_id(args.profile)
    run_dir = CONFIRMATORY_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Confirmatory run: {run_id}")
    print(f"Writing artifacts to: {run_dir}")
    write_json(
        run_dir / "run_config.json",
        {
            "schema_version": 1,
            "profile": args.profile,
            "datasets": datasets,
            "seeds": seeds,
            "candidate_scope": args.candidate_scope,
            "no_books_cap": args.no_books_cap,
            "lc2cpp_config": CONFIRMATORY_LC2CPP_CONFIG,
            "started_utc": utc_now(),
            "machine": machine_notes(),
        },
    )

    warm_results: dict[str, Any] = {}
    cold_results: dict[str, Any] = {}
    cold_records: dict[str, dict[str, list[dict[str, Any]]]] = {}
    t0 = time.time()
    if not args.skip_warm:
        for dataset in datasets:
            print(f"\n{'=' * 80}\nWARM CONFIRMATORY: {dataset}\n{'=' * 80}")
            warm_results[dataset] = run_warm_confirmatory_dataset(dataset, seeds, run_dir)
            write_json(run_dir / "results_final.json", {"warm": warm_results, "cold_full_catalog": cold_results})
    if not args.skip_cold:
        for dataset in datasets:
            print(f"\n{'=' * 80}\nCOLD FULL-CATALOG CONFIRMATORY: {dataset}\n{'=' * 80}")
            cold_results[dataset] = run_cold_confirmatory_dataset(dataset, seeds, run_dir, args.bootstrap_reps)
            # Read back records by method from in-memory JSONL to keep the significance
            # path identical to what an auditor sees on disk.
            by_method: dict[str, list[dict[str, Any]]] = {m: [] for m in COLD_METHODS}
            with (run_dir / f"cold_full_catalog_records_{dataset}.jsonl").open("r", encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    by_method.setdefault(row["method"], []).append(row)
            cold_records[dataset] = by_method
            write_json(run_dir / "results_final.json", {"warm": warm_results, "cold_full_catalog": cold_results})

    significance = compute_significance(cold_records, args.bootstrap_reps) if cold_records else {"schema_version": 1, "cold_full_catalog": {}}
    write_json(run_dir / "significance.json", significance)
    baseline_audit = baseline_audit_payload(seeds, cold_results, warm_results)
    write_json(run_dir / "baseline_audit.json", baseline_audit)
    gate = evaluate_gate(warm_results, cold_results, significance, baseline_audit)
    write_json(run_dir / "publication_gate.json", gate)
    tables = build_tables(run_dir, warm_results, cold_results, significance, baseline_audit, gate)
    write_json(
        run_dir / "results_final.json",
        {
            "schema_version": 1,
            "confirmatory": True,
            "run_id": run_id,
            "algorithm_config": CONFIRMATORY_LC2CPP_CONFIG,
            "warm": warm_results,
            "cold_full_catalog": cold_results,
            "publication_gate": gate,
            "elapsed_seconds": time.time() - t0,
        },
    )

    outputs = [
        run_dir / "run_config.json",
        run_dir / "results_final.json",
        run_dir / "significance.json",
        run_dir / "baseline_audit.json",
        run_dir / "tables.json",
        run_dir / "publication_gate.json",
        *(run_dir.glob("cold_full_catalog_records_*.jsonl")),
        *(run_dir.glob("warm_records_*.jsonl")),
    ]
    append_manifest_run(
        command=[
            "uv",
            "run",
            "python",
            "_bestrec_run/run_all_confirmatory.py",
            "--profile",
            args.profile,
            "--datasets",
            ",".join(datasets),
            "--seeds",
            ",".join(str(x) for x in seeds),
            "--candidate-scope",
            args.candidate_scope,
            "--no-books-cap",
        ],
        inputs=[
            RUN_DIR / "run_all_confirmatory.py",
            RUN_DIR / "run_cold_item.py",
            RUN_DIR / "run_cold_item_v2.py",
            RUN_DIR / "run_warm_loo.py",
            *[Path(ROOT) / "cache" / d / "raw_data_dedup.pkl" for d in datasets],
        ],
        outputs=outputs,
        datasets=datasets,
        seeds=seeds,
        note=f"Confirmatory full-catalog run; publication_gate_passed={gate['passed']}",
        manifest_path=run_dir / "results_manifest.json",
    )
    if gate["passed"]:
        py_cmd = ["uv", "--project", str(RUN_DIR), "run", "python"]
        subprocess.run([*py_cmd, str(ROOT / "_paper_gen" / "build_paper_full.py"), "--confirmatory-run", run_id], cwd=ROOT, check=True)
        append_manifest_run(
            command=["python", "build_paper_full.py", "--confirmatory-run", run_id],
            inputs=[run_dir / "tables.json", run_dir / "results_manifest.json"],
            outputs=[ROOT / "BEST_Rec_v4_Full_Paper.pdf"],
            datasets=datasets,
            seeds=seeds,
            note="Confirmatory paper build after publication gate passed.",
            manifest_path=run_dir / "results_manifest.json",
        )
    else:
        write_internal_failure_report(run_dir, gate, significance)
        append_manifest_run(
            command=["write_internal_failure_report"],
            inputs=[run_dir / "publication_gate.json", run_dir / "significance.json"],
            outputs=[run_dir / "INTERNAL_SOTA_FAILURE_REPORT.md"],
            datasets=datasets,
            seeds=seeds,
            note="Publication gate failed; SOTA paper build blocked.",
            manifest_path=run_dir / "results_manifest.json",
        )
        print("\nPUBLICATION GATE FAILED")
        for item in gate["failures"]:
            print(f"- {item}")
        print(f"\nFailure report: {run_dir / 'INTERNAL_SOTA_FAILURE_REPORT.md'}")
        return 0 if args.allow_failure_report else 1
    print("\nPUBLICATION GATE PASSED")
    print(f"Run directory: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
