"""Train validation-only adaptive HSTU/SASRec fusion weights.

This development script asks a narrower question than the candidate reranker:
can per-user confidence/overlap features decide when to move away from the
globally best HSTU-heavy RRF weight?

It splits validation users into train/selection users, trains user-level
classifiers/regressors to predict a fusion weight, selects by held-out
validation NDCG@10, retrains on all validation users, and evaluates test once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings(
    "ignore",
    message="`sklearn.utils.parallel.delayed` should be used with `sklearn.utils.parallel.Parallel`.*",
    category=UserWarning,
)

LAB_DIR = Path(__file__).resolve().parent
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from train_hstu_sasrec_union_reranker import (  # noqa: E402
    build_user_features,
    load_rows,
    metric_from_rank,
    rank_user,
    sha256_file,
    split_users,
)


USER_FEATURE_NAMES = [
    "hstu_top1_score",
    "hstu_top2_margin",
    "hstu_top10_margin",
    "hstu_score_mean",
    "hstu_score_std",
    "hstu_score_span",
    "sasrec_top1_score",
    "sasrec_top2_margin",
    "sasrec_top10_margin",
    "sasrec_score_mean",
    "sasrec_score_std",
    "sasrec_score_span",
    "top1_same",
    "top10_jaccard",
    "top50_jaccard",
    "union_size_norm",
    "hstu_top1_sasrec_rank_strength",
    "sasrec_top1_hstu_rank_strength",
    "common_rank_absdiff_mean",
    "common_rank_absdiff_std",
    "common_count_norm",
    "hstu_score_cv",
    "sasrec_score_cv",
]


@dataclass
class UserMeta:
    user: Any
    features: np.ndarray
    best_weight: float | None
    best_weight_label: int | None


def _scores(row: dict[str, Any], key: str, top_k: int) -> np.ndarray:
    return np.asarray([float(value) for value in row[key][:top_k]], dtype=np.float32)


def _ids(row: dict[str, Any], key: str, top_k: int) -> list[int]:
    return [int(value) for value in row[key][:top_k]]


def _safe_stats(values: np.ndarray) -> tuple[float, float, float, float]:
    if values.size == 0:
        return 0.0, 0.0, 0.0, 0.0
    return float(values.mean()), float(values.std()), float(values.min()), float(values.max())


def user_features_from_rows(hstu: dict[str, Any], sasrec: dict[str, Any], *, top_k: int) -> np.ndarray:
    h_ids = _ids(hstu, "teacher_top_ids", top_k)
    s_ids = _ids(sasrec, "top_ids", top_k)
    h_scores = _scores(hstu, "teacher_top_scores", top_k)
    s_scores = _scores(sasrec, "top_scores", top_k)
    h_mean, h_std, h_min, h_max = _safe_stats(h_scores)
    s_mean, s_std, s_min, s_max = _safe_stats(s_scores)
    h_rank = {item_id: idx + 1 for idx, item_id in enumerate(h_ids)}
    s_rank = {item_id: idx + 1 for idx, item_id in enumerate(s_ids)}
    h_top10 = set(h_ids[:10])
    s_top10 = set(s_ids[:10])
    h_top50 = set(h_ids[:top_k])
    s_top50 = set(s_ids[:top_k])
    common = sorted(h_top50 & s_top50)
    if common:
        absdiff = np.asarray([abs(h_rank[item] - s_rank[item]) / float(top_k) for item in common], dtype=np.float32)
        diff_mean = float(absdiff.mean())
        diff_std = float(absdiff.std())
    else:
        diff_mean = 1.0
        diff_std = 0.0
    h_top1_sas = s_rank.get(h_ids[0], top_k + 1) if h_ids else top_k + 1
    s_top1_h = h_rank.get(s_ids[0], top_k + 1) if s_ids else top_k + 1
    h_span = max(0.0, h_max - h_min)
    s_span = max(0.0, s_max - s_min)
    h_top2_margin = float(h_scores[0] - h_scores[1]) if h_scores.size >= 2 else 0.0
    s_top2_margin = float(s_scores[0] - s_scores[1]) if s_scores.size >= 2 else 0.0
    h_top10_margin = float(h_scores[0] - h_scores[min(9, h_scores.size - 1)]) if h_scores.size else 0.0
    s_top10_margin = float(s_scores[0] - s_scores[min(9, s_scores.size - 1)]) if s_scores.size else 0.0
    union_size_norm = len(h_top50 | s_top50) / float(max(1, 2 * top_k))
    return np.asarray(
        [
            float(h_scores[0]) if h_scores.size else 0.0,
            h_top2_margin,
            h_top10_margin,
            h_mean,
            h_std,
            h_span,
            float(s_scores[0]) if s_scores.size else 0.0,
            s_top2_margin,
            s_top10_margin,
            s_mean,
            s_std,
            s_span,
            1.0 if h_ids and s_ids and h_ids[0] == s_ids[0] else 0.0,
            len(h_top10 & s_top10) / float(max(1, len(h_top10 | s_top10))),
            len(h_top50 & s_top50) / float(max(1, len(h_top50 | s_top50))),
            union_size_norm,
            (top_k + 1 - h_top1_sas) / float(top_k) if h_top1_sas <= top_k else 0.0,
            (top_k + 1 - s_top1_h) / float(top_k) if s_top1_h <= top_k else 0.0,
            diff_mean,
            diff_std,
            len(common) / float(top_k),
            h_std / max(1e-8, abs(h_mean)),
            s_std / max(1e-8, abs(s_mean)),
        ],
        dtype=np.float32,
    )


def rrf_config(weight: float, seed: int) -> dict[str, Any]:
    return {"name": f"rrf_hstu_weight_{weight:g}", "type": "rrf", "hstu_weight": float(weight), "seed": seed}


def metric_for_weight(user: Any, weight: float, seed: int) -> tuple[dict[str, float], int | None]:
    ranked, _scores, rank0, metrics = rank_user(user, config=rrf_config(weight, seed), model=None)
    return metrics, rank0


def best_weight_for_user(user: Any, weights: list[float], seed: int) -> tuple[float | None, int | None]:
    if user.target_item_id not in set(user.item_ids):
        return None, None
    scored = []
    for idx, weight in enumerate(weights):
        metrics, rank0 = metric_for_weight(user, weight, seed)
        rank_value = 10**9 if rank0 is None else rank0
        scored.append((metrics["ndcg10"], metrics["rr"], -rank_value, -abs(weight - 0.85), idx, weight))
    best = max(scored)
    return float(best[-1]), int(best[-2])


def build_meta(
    hstu_rows: dict[int, dict[str, Any]],
    sasrec_rows: dict[int, dict[str, Any]],
    *,
    weights: list[float],
    top_k: int,
    rrf_k: int,
    seed: int,
) -> list[UserMeta]:
    if set(hstu_rows) != set(sasrec_rows):
        raise ValueError("HSTU/SASRec user sets differ")
    rows: list[UserMeta] = []
    for user_id in sorted(hstu_rows):
        user = build_user_features(user_id, hstu_rows[user_id], sasrec_rows[user_id], top_k=top_k, rrf_k=rrf_k)
        weight, label = best_weight_for_user(user, weights, seed)
        rows.append(UserMeta(user=user, features=user_features_from_rows(hstu_rows[user_id], sasrec_rows[user_id], top_k=top_k), best_weight=weight, best_weight_label=label))
    return rows


@dataclass
class AdaptiveModel:
    name: str
    kind: str
    model: Any
    scaler: StandardScaler | None = None
    weights: list[float] | None = None


def train_adaptive_model(name: str, metas: list[UserMeta], *, weights: list[float], seed: int) -> AdaptiveModel:
    labeled = [meta for meta in metas if meta.best_weight_label is not None]
    if not labeled:
        raise ValueError("No labeled users available")
    x = np.vstack([meta.features for meta in labeled]).astype(np.float32, copy=False)
    if name == "histgb_classifier":
        y = np.asarray([int(meta.best_weight_label) for meta in labeled], dtype=np.int64)
        model = HistGradientBoostingClassifier(max_iter=120, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=0.05, random_state=seed)
        model.fit(x, y)
        return AdaptiveModel(name=name, kind="classifier", model=model, weights=weights)
    if name == "rf_classifier":
        y = np.asarray([int(meta.best_weight_label) for meta in labeled], dtype=np.int64)
        model = RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=20, n_jobs=-1, random_state=seed, class_weight="balanced_subsample")
        model.fit(x, y)
        return AdaptiveModel(name=name, kind="classifier", model=model, weights=weights)
    if name == "histgb_regressor":
        y = np.asarray([float(meta.best_weight) for meta in labeled], dtype=np.float32)
        model = HistGradientBoostingRegressor(max_iter=120, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=0.05, random_state=seed)
        model.fit(x, y)
        return AdaptiveModel(name=name, kind="regressor", model=model, weights=weights)
    raise ValueError(f"Unknown adaptive model: {name}")


def predict_weight(model: AdaptiveModel, features: np.ndarray, *, anchor: float, shrink: float) -> float:
    x = features.reshape(1, -1)
    if model.kind == "classifier":
        label = int(model.model.predict(x)[0])
        raw = float(model.weights[label])
    else:
        raw = float(model.model.predict(x)[0])
        raw = min(1.0, max(0.0, raw))
    return (1.0 - shrink) * anchor + shrink * raw


def evaluate_adaptive(
    metas: list[UserMeta],
    *,
    config: dict[str, Any],
    model: AdaptiveModel | None,
    write_records: Path | None = None,
) -> dict[str, Any]:
    sums = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    predicted_weights: list[float] = []
    target_in_union = 0
    handle = write_records.open("w", encoding="utf-8") if write_records else None
    try:
        for meta in metas:
            if config["type"] == "rrf":
                weight = float(config["hstu_weight"])
            else:
                if model is None:
                    raise ValueError("Adaptive config requires a model")
                weight = predict_weight(model, meta.features, anchor=float(config["anchor_weight"]), shrink=float(config["shrink"]))
            predicted_weights.append(weight)
            ranked, scores, rank0, metrics = rank_user(meta.user, config=rrf_config(weight, int(config["seed"])), model=None)
            if meta.user.target_item_id in set(meta.user.item_ids):
                target_in_union += 1
            for key in sums:
                sums[key] += metrics[key]
            if handle is not None:
                handle.write(
                    json.dumps(
                        {
                            "dataset": "Video_Games",
                            "fold_id": 0,
                            "seed": int(config["seed"]),
                            "method": "hstu_sasrec_adaptive_fusion_dev",
                            "user_id": meta.user.user_id,
                            "target_item_id": meta.user.target_item_id,
                            "candidate_scope": "hstu_sasrec_top50_union_history_masked",
                            "ndcg10": metrics["ndcg10"],
                            "hr10": metrics["hr10"],
                            "rr": metrics["rr"],
                            "rank": None if rank0 is None else rank0 + 1,
                            "hstu_rrf_weight": weight,
                            "top_ids": ranked[:50],
                            "top_scores": scores[:50],
                            "publication_grade": False,
                            "development_note": "Validation-trained adaptive fusion; requires frozen confirmatory rerun before any claim.",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
    finally:
        if handle is not None:
            handle.close()
    n = len(metas)
    arr = np.asarray(predicted_weights, dtype=np.float32)
    return {
        "n": n,
        "ndcg10": sums["ndcg10"] / n,
        "hr10": sums["hr10"] / n,
        "rr": sums["rr"] / n,
        "target_in_union_rate": target_in_union / n,
        "predicted_weight_mean": float(arr.mean()),
        "predicted_weight_std": float(arr.std()),
        "predicted_weight_min": float(arr.min()),
        "predicted_weight_max": float(arr.max()),
    }


def sha256_json(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


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
    parser.add_argument("--weights", default="0.0,0.1,0.25,0.5,0.65,0.75,0.8,0.85,0.9,0.95,1.0")
    parser.add_argument("--shrinks", default="0.25,0.5,0.75,1.0")
    parser.add_argument("--models", default="histgb_classifier,histgb_regressor,rf_classifier")
    parser.add_argument("--anchor-weight", type=float, default=0.85)
    args = parser.parse_args()

    started = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "hstu_valid": Path(args.hstu_valid_jsonl),
        "sasrec_valid": Path(args.sasrec_valid_jsonl),
        "hstu_test": Path(args.hstu_test_jsonl),
        "sasrec_test": Path(args.sasrec_test_jsonl),
    }
    weights = [float(value) for value in args.weights.split(",") if value.strip()]
    shrinks = [float(value) for value in args.shrinks.split(",") if value.strip()]
    model_names = [value.strip() for value in args.models.split(",") if value.strip()]

    hstu_valid = load_rows(paths["hstu_valid"], "teacher_top_ids", "teacher_top_scores")
    sasrec_valid = load_rows(paths["sasrec_valid"], "top_ids", "top_scores")
    hstu_test = load_rows(paths["hstu_test"], "teacher_top_ids", "teacher_top_scores")
    sasrec_test = load_rows(paths["sasrec_test"], "top_ids", "top_scores")
    valid_meta = build_meta(hstu_valid, sasrec_valid, weights=weights, top_k=args.top_k, rrf_k=args.rrf_k, seed=args.seed)
    test_meta = build_meta(hstu_test, sasrec_test, weights=weights, top_k=args.top_k, rrf_k=args.rrf_k, seed=args.seed)
    valid_users = [meta.user for meta in valid_meta]
    train_users, select_users = split_users(valid_users, train_fraction=args.train_fraction, seed=args.seed)
    train_ids = {user.user_id for user in train_users}
    train_meta = [meta for meta in valid_meta if meta.user.user_id in train_ids]
    select_meta = [meta for meta in valid_meta if meta.user.user_id not in train_ids]

    candidate_results: list[dict[str, Any]] = []
    for weight in weights:
        config = {"name": f"rrf_hstu_weight_{weight:g}", "type": "rrf", "hstu_weight": weight, "seed": args.seed}
        candidate_results.append({"config": config, "selection_metrics": evaluate_adaptive(select_meta, config=config, model=None)})

    trained: dict[str, AdaptiveModel] = {}
    for name in model_names:
        model = train_adaptive_model(name, train_meta, weights=weights, seed=args.seed)
        trained[name] = model
        for shrink in shrinks:
            config = {
                "name": f"{name}_anchor{args.anchor_weight:g}_shrink{shrink:g}",
                "type": "adaptive",
                "model_name": name,
                "anchor_weight": args.anchor_weight,
                "shrink": shrink,
                "seed": args.seed,
            }
            candidate_results.append({"config": config, "selection_metrics": evaluate_adaptive(select_meta, config=config, model=model)})

    selected = max(candidate_results, key=lambda row: (row["selection_metrics"]["ndcg10"], row["selection_metrics"]["hr10"], row["selection_metrics"]["rr"]))
    selected_config = dict(selected["config"])
    final_model = None
    final_train_summary = None
    if selected_config["type"] == "adaptive":
        final_model = train_adaptive_model(str(selected_config["model_name"]), valid_meta, weights=weights, seed=args.seed)
        labeled = [meta for meta in valid_meta if meta.best_weight_label is not None]
        final_train_summary = {
            "labeled_users": len(labeled),
            "total_validation_users": len(valid_meta),
            "label_distribution": {
                str(weight): sum(1 for meta in labeled if meta.best_weight == weight)
                for weight in weights
            },
        }

    records_path = out_dir / "warm_full_catalog_records_Video_Games_hstu_sasrec_adaptive_fusion_test.jsonl"
    test_metrics = evaluate_adaptive(test_meta, config=selected_config, model=final_model, write_records=records_path)
    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(time.time() - started, 3),
        "inputs": {name: sha256_file(path) for name, path in paths.items()},
        "parameters": {
            "top_k": args.top_k,
            "rrf_k": args.rrf_k,
            "seed": args.seed,
            "train_fraction": args.train_fraction,
            "weights": weights,
            "shrinks": shrinks,
            "models": model_names,
            "anchor_weight": args.anchor_weight,
            "user_feature_names": USER_FEATURE_NAMES,
        },
        "validation_split": {
            "train_users": len(train_meta),
            "selection_users": len(select_meta),
            "total_validation_users": len(valid_meta),
            "labeled_train_users": sum(1 for meta in train_meta if meta.best_weight_label is not None),
            "labeled_selection_users": sum(1 for meta in select_meta if meta.best_weight_label is not None),
        },
        "candidate_results": candidate_results,
        "selected_config": selected_config,
        "selected_selection_metrics": selected["selection_metrics"],
        "final_train_summary": final_train_summary,
        "test_metrics": test_metrics,
        "comparators": {
            "strict_dev9_hstu_test_ndcg10": 0.07121812232925798,
            "validation_selected_fixed_rrf_test_ndcg10": 0.07272761825417069,
            "local_hstu_sm120_final_export_ndcg10": 0.07382241421701587,
            "upstream_hstu_report_ndcg10": 0.076,
            "gap_to_strict_dev9_hstu": test_metrics["ndcg10"] - 0.07121812232925798,
            "gap_to_validation_selected_fixed_rrf": test_metrics["ndcg10"] - 0.07272761825417069,
            "gap_to_local_hstu_sm120_final_export": test_metrics["ndcg10"] - 0.07382241421701587,
            "gap_to_upstream_hstu_report": test_metrics["ndcg10"] - 0.076,
        },
        "records": sha256_file(records_path),
        "honest_interpretation": "Development-only adaptive fusion selected on held-out validation users; SOTA remains blocked unless test beats HSTU comparator and is later confirmed on fresh frozen seeds.",
    }
    summary_path = out_dir / "hstu_sasrec_adaptive_fusion_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "selected_config": selected_config,
        "selection_ndcg10": selected["selection_metrics"]["ndcg10"],
        "test_ndcg10": test_metrics["ndcg10"],
        "gap_to_fixed_rrf": summary["comparators"]["gap_to_validation_selected_fixed_rrf"],
        "gap_to_local_hstu": summary["comparators"]["gap_to_local_hstu_sm120_final_export"],
        "summary": str(summary_path),
        "records": str(records_path),
        "records_sha256": summary["records"].get("sha256"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
