"""Train a validation-only reranker over HSTU/SASRec top-k unions.

This is a development repair attempt, not publication evidence. It uses the
strict HSTU dev9 and SASRec checkpoint exports as frozen candidate generators:

1. Split validation users into train/selection users.
2. Train candidate-level rerankers on validation-train labels only.
3. Select one reranker/blend by validation-selection NDCG@10.
4. Retrain that selected config on all validation users.
5. Evaluate once on held-out test records.

The output records and summary explicitly mark the run as development-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler


USER_ID_CONVENTIONS = {"bestrec_zero_based_user_ids", "BEST-Rec canonical user_id"}
ITEM_ID_CONVENTIONS = {"bestrec_zero_based_item_ids", "BEST-Rec canonical item_id"}
FEATURE_NAMES = [
    "hstu_present",
    "sasrec_present",
    "both_present",
    "hstu_rrf",
    "sasrec_rrf",
    "rrf_equal",
    "hstu_rank_strength",
    "sasrec_rank_strength",
    "hstu_inv_rank",
    "sasrec_inv_rank",
    "hstu_top10",
    "sasrec_top10",
    "rank_abs_diff_norm",
    "rank_min_strength",
    "rank_max_strength",
    "hstu_score_z",
    "sasrec_score_z",
    "hstu_score_minmax",
    "sasrec_score_minmax",
    "score_z_sum",
    "score_z_diff",
    "union_size_norm",
    "hstu_score_span",
    "sasrec_score_span",
]


def sha256_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    record.update({"sha256": digest.hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return record


def load_rows(path: Path, top_key: str, score_key: str) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            user_id = int(row["user_id"])
            if user_id in rows:
                raise ValueError(f"Duplicate user_id={user_id} in {path} at line {line_number}")
            if row.get("user_id_convention") not in USER_ID_CONVENTIONS:
                raise ValueError(f"{path} line {line_number} has noncanonical user_id convention: {row.get('user_id_convention')}")
            if row.get("item_id_convention") not in ITEM_ID_CONVENTIONS:
                raise ValueError(f"{path} line {line_number} has noncanonical item_id convention: {row.get('item_id_convention')}")
            if top_key not in row or score_key not in row:
                raise ValueError(f"{path} line {line_number} missing {top_key}/{score_key}")
            rows[user_id] = row
    return rows


def metric_from_rank(rank0: int | None) -> dict[str, float]:
    if rank0 is None:
        return {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    return {
        "ndcg10": 1.0 / math.log2(rank0 + 2) if rank0 < 10 else 0.0,
        "hr10": 1.0 if rank0 < 10 else 0.0,
        "rr": 1.0 / float(rank0 + 1),
    }


def average_metrics(records: Iterable[dict[str, Any]]) -> dict[str, float]:
    totals = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    n = 0
    for row in records:
        n += 1
        for key in totals:
            totals[key] += float(row[key])
    if n == 0:
        raise ValueError("No records to average")
    return {key: value / n for key, value in totals.items()} | {"n": n}


def top_list(row: dict[str, Any], key: str, top_k: int) -> list[int]:
    return [int(value) for value in row[key][:top_k]]


def score_list(row: dict[str, Any], key: str, top_k: int) -> list[float]:
    return [float(value) for value in row[key][:top_k]]


@dataclass
class UserFeatures:
    user_id: int
    target_item_id: int
    item_ids: list[int]
    features: np.ndarray
    equal_rrf: np.ndarray
    hstu_weighted_rrf: np.ndarray
    sasrec_weighted_rrf: np.ndarray


def _stats(values: list[float]) -> tuple[float, float, float, float]:
    arr = np.asarray(values, dtype=np.float32)
    mean = float(arr.mean()) if arr.size else 0.0
    std = float(arr.std()) if arr.size else 0.0
    min_v = float(arr.min()) if arr.size else 0.0
    max_v = float(arr.max()) if arr.size else 0.0
    return mean, std if std > 1e-8 else 1.0, min_v, max_v


def build_user_features(
    user_id: int,
    hstu: dict[str, Any],
    sasrec: dict[str, Any],
    *,
    top_k: int,
    rrf_k: int,
) -> UserFeatures:
    hstu_target = int(hstu["target_item_id"])
    sasrec_target = int(sasrec["target_item_id"])
    if hstu_target != sasrec_target:
        raise ValueError(f"Target mismatch for user_id={user_id}: hstu={hstu_target} sasrec={sasrec_target}")

    h_ids = top_list(hstu, "teacher_top_ids", top_k)
    s_ids = top_list(sasrec, "top_ids", top_k)
    h_scores = score_list(hstu, "teacher_top_scores", top_k)
    s_scores = score_list(sasrec, "top_scores", top_k)
    h_rank = {item_id: idx + 1 for idx, item_id in enumerate(h_ids)}
    s_rank = {item_id: idx + 1 for idx, item_id in enumerate(s_ids)}
    h_score = {item_id: h_scores[idx] for idx, item_id in enumerate(h_ids)}
    s_score = {item_id: s_scores[idx] for idx, item_id in enumerate(s_ids)}
    h_mean, h_std, h_min, h_max = _stats(h_scores)
    s_mean, s_std, s_min, s_max = _stats(s_scores)
    h_span = max(1e-8, h_max - h_min)
    s_span = max(1e-8, s_max - s_min)
    item_ids = sorted(set(h_ids) | set(s_ids))
    union_size_norm = len(item_ids) / float(max(1, 2 * top_k))
    features: list[list[float]] = []
    equal_rrf: list[float] = []
    hstu_rrf_values: list[float] = []
    sasrec_rrf_values: list[float] = []
    for item_id in item_ids:
        hr = h_rank.get(item_id)
        sr = s_rank.get(item_id)
        hp = 1.0 if hr is not None else 0.0
        sp = 1.0 if sr is not None else 0.0
        h_rrf = 1.0 / (rrf_k + hr) if hr is not None else 0.0
        s_rrf = 1.0 / (rrf_k + sr) if sr is not None else 0.0
        h_strength = (top_k + 1 - hr) / float(top_k) if hr is not None else 0.0
        s_strength = (top_k + 1 - sr) / float(top_k) if sr is not None else 0.0
        h_inv = 1.0 / hr if hr is not None else 0.0
        s_inv = 1.0 / sr if sr is not None else 0.0
        diff_norm = abs(hr - sr) / float(top_k) if hr is not None and sr is not None else 1.0
        ranks_present = [value for value in (hr, sr) if value is not None]
        min_strength = (top_k + 1 - min(ranks_present)) / float(top_k) if ranks_present else 0.0
        max_strength = (top_k + 1 - max(ranks_present)) / float(top_k) if ranks_present else 0.0
        hz = (h_score[item_id] - h_mean) / h_std if item_id in h_score else 0.0
        sz = (s_score[item_id] - s_mean) / s_std if item_id in s_score else 0.0
        h_mm = (h_score[item_id] - h_min) / h_span if item_id in h_score else 0.0
        s_mm = (s_score[item_id] - s_min) / s_span if item_id in s_score else 0.0
        features.append(
            [
                hp,
                sp,
                1.0 if hp and sp else 0.0,
                h_rrf,
                s_rrf,
                0.5 * h_rrf + 0.5 * s_rrf,
                h_strength,
                s_strength,
                h_inv,
                s_inv,
                1.0 if hr is not None and hr <= 10 else 0.0,
                1.0 if sr is not None and sr <= 10 else 0.0,
                diff_norm,
                min_strength,
                max_strength,
                hz,
                sz,
                h_mm,
                s_mm,
                hz + sz,
                hz - sz,
                union_size_norm,
                h_span,
                s_span,
            ]
        )
        equal_rrf.append(0.5 * h_rrf + 0.5 * s_rrf)
        hstu_rrf_values.append(h_rrf)
        sasrec_rrf_values.append(s_rrf)
    return UserFeatures(
        user_id=user_id,
        target_item_id=hstu_target,
        item_ids=item_ids,
        features=np.asarray(features, dtype=np.float32),
        equal_rrf=np.asarray(equal_rrf, dtype=np.float32),
        hstu_weighted_rrf=np.asarray(hstu_rrf_values, dtype=np.float32),
        sasrec_weighted_rrf=np.asarray(sasrec_rrf_values, dtype=np.float32),
    )


def select_training_rows(
    users: list[UserFeatures],
    *,
    max_negatives_per_user: int,
    max_train_rows: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    sample_weights: list[float] = []
    for user in users:
        labels = np.asarray([1 if item == user.target_item_id else 0 for item in user.item_ids], dtype=np.int8)
        positive_idx = np.flatnonzero(labels == 1)
        negative_idx = np.flatnonzero(labels == 0)
        if max_negatives_per_user >= 0 and negative_idx.size > max_negatives_per_user:
            order = negative_idx[np.argsort(-user.equal_rrf[negative_idx], kind="mergesort")]
            negative_idx = order[:max_negatives_per_user]
        chosen = np.concatenate([positive_idx, negative_idx])
        if chosen.size == 0:
            continue
        xs.append(user.features[chosen])
        ys.extend(labels[chosen].astype(int).tolist())
        sample_weights.extend([1.0] * chosen.size)
    if not xs:
        raise ValueError("No training rows selected")
    x = np.vstack(xs).astype(np.float32, copy=False)
    y = np.asarray(ys, dtype=np.int8)
    weights = np.asarray(sample_weights, dtype=np.float32)
    positives = int(y.sum())
    negatives = int(y.size - positives)
    if positives:
        weights[y == 1] = min(50.0, max(1.0, negatives / float(positives)))
    if max_train_rows > 0 and y.size > max_train_rows:
        rng = np.random.default_rng(17)
        pos_idx = np.flatnonzero(y == 1)
        neg_idx = np.flatnonzero(y == 0)
        keep_pos = pos_idx
        max_neg = max(0, max_train_rows - keep_pos.size)
        keep_neg = rng.choice(neg_idx, size=max_neg, replace=False) if neg_idx.size > max_neg else neg_idx
        keep = np.concatenate([keep_pos, keep_neg])
        rng.shuffle(keep)
        x = x[keep]
        y = y[keep]
        weights = weights[keep]
    return x, y, weights


@dataclass
class ModelBundle:
    name: str
    kind: str
    model: Any
    scaler: StandardScaler | None = None


def fit_model(name: str, x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray, *, seed: int) -> ModelBundle:
    if name.startswith("sgd_log_alpha"):
        alpha = float(name.replace("sgd_log_alpha", ""))
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)
        model = SGDClassifier(
            loss="log_loss",
            alpha=alpha,
            penalty="l2",
            max_iter=2000,
            tol=1e-4,
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(x_scaled, y, sample_weight=sample_weight)
        return ModelBundle(name=name, kind="sgd_log", model=model, scaler=scaler)
    if name.startswith("histgb_"):
        parts = dict(part.split("=") for part in name.removeprefix("histgb_").split("_"))
        model = HistGradientBoostingClassifier(
            learning_rate=float(parts["lr"]),
            max_iter=int(parts["iter"]),
            max_leaf_nodes=int(parts["leaf"]),
            l2_regularization=float(parts["l2"]),
            random_state=seed,
        )
        model.fit(x, y, sample_weight=sample_weight)
        return ModelBundle(name=name, kind="histgb", model=model)
    raise ValueError(f"Unknown model config: {name}")


def model_scores(bundle: ModelBundle, x: np.ndarray) -> np.ndarray:
    if bundle.scaler is not None:
        x = bundle.scaler.transform(x)
    if hasattr(bundle.model, "predict_proba"):
        return bundle.model.predict_proba(x)[:, 1].astype(np.float32)
    return bundle.model.decision_function(x).astype(np.float32)


def _rank_percentile(scores: np.ndarray) -> np.ndarray:
    if scores.size <= 1:
        return np.ones_like(scores, dtype=np.float32)
    order = np.argsort(-scores, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float32)
    ranks[order] = np.arange(scores.size, dtype=np.float32)
    return 1.0 - ranks / float(scores.size - 1)


def final_scores_for_user(
    user: UserFeatures,
    *,
    config: dict[str, Any],
    model: ModelBundle | None,
) -> np.ndarray:
    if config["type"] == "rrf":
        weight = float(config["hstu_weight"])
        return weight * user.hstu_weighted_rrf + (1.0 - weight) * user.sasrec_weighted_rrf
    if model is None:
        raise ValueError("Model config requires a fitted model")
    pred = model_scores(model, user.features)
    blend = float(config["rrf_blend"])
    if blend <= 0:
        return pred
    pred_pct = _rank_percentile(pred)
    rrf_pct = _rank_percentile(user.equal_rrf)
    return (1.0 - blend) * pred_pct + blend * rrf_pct


def rank_user(
    user: UserFeatures,
    *,
    config: dict[str, Any],
    model: ModelBundle | None,
) -> tuple[list[int], list[float], int | None, dict[str, float]]:
    scores = final_scores_for_user(user, config=config, model=model)
    order = sorted(range(len(user.item_ids)), key=lambda idx: (-float(scores[idx]), -float(user.equal_rrf[idx]), user.item_ids[idx]))
    ranked_items = [user.item_ids[idx] for idx in order]
    ranked_scores = [float(scores[idx]) for idx in order]
    try:
        rank0 = ranked_items.index(user.target_item_id)
    except ValueError:
        rank0 = None
    return ranked_items, ranked_scores, rank0, metric_from_rank(rank0)


def evaluate_users(
    users: list[UserFeatures],
    *,
    config: dict[str, Any],
    model: ModelBundle | None,
    write_records: Path | None = None,
    method_name: str | None = None,
) -> dict[str, Any]:
    sums = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    target_in_union = 0
    handle = write_records.open("w", encoding="utf-8") if write_records else None
    try:
        for user in users:
            ranked_items, ranked_scores, rank0, metrics = rank_user(user, config=config, model=model)
            if user.target_item_id in user.item_ids:
                target_in_union += 1
            for key in sums:
                sums[key] += metrics[key]
            if handle is not None:
                row = {
                    "dataset": "Video_Games",
                    "fold_id": 0,
                    "seed": int(config.get("seed", 0)),
                    "method": method_name or config["name"],
                    "user_id": user.user_id,
                    "target_item_id": user.target_item_id,
                    "candidate_scope": "hstu_sasrec_top50_union_history_masked",
                    "ndcg10": metrics["ndcg10"],
                    "hr10": metrics["hr10"],
                    "rr": metrics["rr"],
                    "rank": None if rank0 is None else rank0 + 1,
                    "top_ids": ranked_items[:50],
                    "top_scores": ranked_scores[:50],
                    "publication_grade": False,
                    "development_note": "Validation-trained HSTU/SASRec union reranker; requires frozen confirmatory rerun before any claim.",
                }
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    finally:
        if handle is not None:
            handle.close()
    n = len(users)
    return {
        "n": n,
        "ndcg10": sums["ndcg10"] / n,
        "hr10": sums["hr10"] / n,
        "rr": sums["rr"] / n,
        "target_in_union_rate": target_in_union / n,
    }


def build_users(hstu_rows: dict[int, dict[str, Any]], sasrec_rows: dict[int, dict[str, Any]], *, top_k: int, rrf_k: int) -> list[UserFeatures]:
    if set(hstu_rows) != set(sasrec_rows):
        raise ValueError(f"User sets differ: hstu_only={len(set(hstu_rows) - set(sasrec_rows))} sasrec_only={len(set(sasrec_rows) - set(hstu_rows))}")
    return [
        build_user_features(user_id, hstu_rows[user_id], sasrec_rows[user_id], top_k=top_k, rrf_k=rrf_k)
        for user_id in sorted(hstu_rows)
    ]


def split_users(users: list[UserFeatures], *, train_fraction: float, seed: int) -> tuple[list[UserFeatures], list[UserFeatures]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(len(users))
    rng.shuffle(indices)
    split = int(round(len(users) * train_fraction))
    train_idx = set(indices[:split].tolist())
    train = [user for idx, user in enumerate(users) if idx in train_idx]
    select = [user for idx, user in enumerate(users) if idx not in train_idx]
    return train, select


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-valid-jsonl", required=True)
    parser.add_argument("--sasrec-valid-jsonl", required=True)
    parser.add_argument("--hstu-test-jsonl", required=True)
    parser.add_argument("--sasrec-test-jsonl", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--max-negatives-per-user", type=int, default=24)
    parser.add_argument("--max-train-rows", type=int, default=1500000)
    parser.add_argument("--model-configs", default="sgd_log_alpha0.0001,sgd_log_alpha0.00003,histgb_lr=0.05_iter=80_leaf=15_l2=0.01,histgb_lr=0.08_iter=80_leaf=31_l2=0.01")
    parser.add_argument("--rrf-weights", default="0.0,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1.0")
    parser.add_argument("--model-rrf-blends", default="0.0,0.25,0.5")
    args = parser.parse_args()

    start = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "hstu_valid": Path(args.hstu_valid_jsonl),
        "sasrec_valid": Path(args.sasrec_valid_jsonl),
        "hstu_test": Path(args.hstu_test_jsonl),
        "sasrec_test": Path(args.sasrec_test_jsonl),
    }
    hstu_valid = load_rows(paths["hstu_valid"], "teacher_top_ids", "teacher_top_scores")
    sasrec_valid = load_rows(paths["sasrec_valid"], "top_ids", "top_scores")
    hstu_test = load_rows(paths["hstu_test"], "teacher_top_ids", "teacher_top_scores")
    sasrec_test = load_rows(paths["sasrec_test"], "top_ids", "top_scores")

    valid_users = build_users(hstu_valid, sasrec_valid, top_k=args.top_k, rrf_k=args.rrf_k)
    test_users = build_users(hstu_test, sasrec_test, top_k=args.top_k, rrf_k=args.rrf_k)
    train_users, select_users = split_users(valid_users, train_fraction=args.train_fraction, seed=args.seed)

    rrf_weights = [float(value) for value in args.rrf_weights.split(",") if value.strip()]
    model_names = [value.strip() for value in args.model_configs.split(",") if value.strip()]
    model_blends = [float(value) for value in args.model_rrf_blends.split(",") if value.strip()]
    candidate_results: list[dict[str, Any]] = []

    for weight in rrf_weights:
        config = {"name": f"rrf_hstu_weight_{weight:g}", "type": "rrf", "hstu_weight": weight, "seed": args.seed}
        metrics = evaluate_users(select_users, config=config, model=None)
        candidate_results.append({"config": config, "selection_metrics": metrics})

    x_train, y_train, w_train = select_training_rows(
        train_users,
        max_negatives_per_user=args.max_negatives_per_user,
        max_train_rows=args.max_train_rows,
    )
    train_matrix_stats = {
        "rows": int(y_train.size),
        "features": int(x_train.shape[1]),
        "positives": int(y_train.sum()),
        "negatives": int(y_train.size - y_train.sum()),
        "positive_weight": float(w_train[y_train == 1][0]) if int(y_train.sum()) else None,
    }
    fitted: dict[str, ModelBundle] = {}
    for model_name in model_names:
        model = fit_model(model_name, x_train, y_train, w_train, seed=args.seed)
        fitted[model_name] = model
        for blend in model_blends:
            config = {
                "name": f"{model_name}_rrfblend{blend:g}",
                "type": "model",
                "model_name": model_name,
                "rrf_blend": blend,
                "seed": args.seed,
            }
            metrics = evaluate_users(select_users, config=config, model=model)
            candidate_results.append({"config": config, "selection_metrics": metrics})

    selected = max(
        candidate_results,
        key=lambda row: (row["selection_metrics"]["ndcg10"], row["selection_metrics"]["hr10"], row["selection_metrics"]["rr"]),
    )
    selected_config = dict(selected["config"])

    final_model: ModelBundle | None = None
    final_train_stats: dict[str, Any] | None = None
    if selected_config["type"] == "model":
        x_all, y_all, w_all = select_training_rows(
            valid_users,
            max_negatives_per_user=args.max_negatives_per_user,
            max_train_rows=args.max_train_rows,
        )
        final_train_stats = {
            "rows": int(y_all.size),
            "features": int(x_all.shape[1]),
            "positives": int(y_all.sum()),
            "negatives": int(y_all.size - y_all.sum()),
            "positive_weight": float(w_all[y_all == 1][0]) if int(y_all.sum()) else None,
        }
        final_model = fit_model(str(selected_config["model_name"]), x_all, y_all, w_all, seed=args.seed)

    records_path = out_dir / "warm_full_catalog_records_Video_Games_hstu_sasrec_union_ltr_test.jsonl"
    test_metrics = evaluate_users(
        test_users,
        config=selected_config,
        model=final_model,
        write_records=records_path,
        method_name="hstu_sasrec_union_ltr_dev",
    )
    records_hash = sha256_file(records_path)
    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(time.time() - start, 3),
        "inputs": {name: sha256_file(path) for name, path in paths.items()},
        "parameters": {
            "top_k": args.top_k,
            "rrf_k": args.rrf_k,
            "seed": args.seed,
            "train_fraction": args.train_fraction,
            "max_negatives_per_user": args.max_negatives_per_user,
            "max_train_rows": args.max_train_rows,
            "feature_names": FEATURE_NAMES,
            "model_configs": model_names,
            "rrf_weights": rrf_weights,
            "model_rrf_blends": model_blends,
        },
        "validation_split": {
            "train_users": len(train_users),
            "selection_users": len(select_users),
            "total_validation_users": len(valid_users),
        },
        "train_matrix_stats": train_matrix_stats,
        "candidate_results": candidate_results,
        "selected_config": selected_config,
        "selected_selection_metrics": selected["selection_metrics"],
        "final_train_stats": final_train_stats,
        "test_metrics": test_metrics,
        "comparators": {
            "strict_dev9_hstu_test_ndcg10": 0.07121812232925798,
            "local_hstu_sm120_final_export_ndcg10": 0.07382241421701587,
            "upstream_hstu_report_ndcg10": 0.076,
            "gap_to_strict_dev9_hstu": test_metrics["ndcg10"] - 0.07121812232925798,
            "gap_to_local_hstu_sm120_final_export": test_metrics["ndcg10"] - 0.07382241421701587,
            "gap_to_upstream_hstu_report": test_metrics["ndcg10"] - 0.076,
        },
        "records": records_hash,
        "honest_interpretation": (
            "Development-only reranker trained from validation labels. It can motivate a frozen confirmatory "
            "candidate only if it beats the HSTU comparator; otherwise SOTA remains blocked."
        ),
    }
    summary_path = out_dir / "hstu_sasrec_union_ltr_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "out_dir": str(out_dir),
        "selected_config": selected_config,
        "selection_ndcg10": selected["selection_metrics"]["ndcg10"],
        "test_ndcg10": test_metrics["ndcg10"],
        "gap_to_local_hstu": summary["comparators"]["gap_to_local_hstu_sm120_final_export"],
        "summary": str(summary_path),
        "records": str(records_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
