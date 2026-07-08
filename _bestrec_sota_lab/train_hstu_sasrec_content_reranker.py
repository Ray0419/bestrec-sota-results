"""Train a content-aware reranker over HSTU/SASRec top-k unions.

This is a development repair attempt. It adds BLaIR text-embedding/user-profile
features to the frozen HSTU/SASRec union features, using only validation users
for training/selection and evaluating held-out test once.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

LAB_DIR = Path(__file__).resolve().parent
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from train_hstu_sasrec_union_reranker import (  # noqa: E402
    FEATURE_NAMES as UNION_FEATURE_NAMES,
    ModelBundle,
    average_metrics,
    build_user_features,
    final_scores_for_user,
    fit_model,
    load_rows,
    metric_from_rank,
    model_scores,
    rank_user,
    sha256_file,
    split_users,
)


CONTENT_FEATURE_NAMES = [
    "profile_cosine",
    "last_item_cosine",
    "recent5_max_cosine",
    "recent5_mean_cosine",
    "recent10_max_cosine",
    "recent10_mean_cosine",
    "history_mean_norm",
    "history_len_log",
    "history_len_clip",
    "candidate_pop_in_history",
]


@dataclass
class ContentUserFeatures:
    user_id: int
    target_item_id: int
    item_ids: list[int]
    features: np.ndarray
    equal_rrf: np.ndarray
    hstu_weighted_rrf: np.ndarray
    sasrec_weighted_rrf: np.ndarray


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_bestrec_embeddings(embedding_path: Path, item_map_path: Path) -> np.ndarray:
    raw = torch.load(str(embedding_path), map_location="cpu")
    if not isinstance(raw, torch.Tensor):
        raise TypeError(f"Expected tensor in {embedding_path}, got {type(raw)}")
    item_map = load_json(item_map_path)
    bestrec_to_hstu = item_map["bestrec_zero_based_to_hstu_one_based"]
    emb = raw.detach().cpu().numpy().astype(np.float32, copy=False)
    mapped = emb[np.asarray(bestrec_to_hstu, dtype=np.int64)]
    norms = np.linalg.norm(mapped, axis=1, keepdims=True)
    mapped = mapped / np.maximum(norms, 1e-8)
    return mapped.astype(np.float32, copy=False)


def parse_hstu_sequence_histories(
    csv_path: Path,
    *,
    user_map_path: Path,
    item_map_path: Path,
) -> dict[int, list[int]]:
    user_map = load_json(user_map_path)
    item_map = load_json(item_map_path)
    hstu_user_to_bestrec = user_map["hstu_zero_based_to_bestrec_zero_based"]
    hstu_item_to_bestrec = item_map["hstu_one_based_to_bestrec_zero_based"]
    histories: dict[int, list[int]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hstu_user_id = int(row["user_id"])
            bestrec_user_id = int(hstu_user_to_bestrec[hstu_user_id])
            seq = [int(value) for value in row["sequence_item_ids"].split(",") if value != ""]
            # CSV rows include the held-out target as the last item. Evaluation
            # history is therefore all preceding HSTU zero-based item IDs.
            hist_hstu_zero = seq[:-1]
            hist_bestrec: list[int] = []
            for item in hist_hstu_zero:
                one_based = item + 1
                if one_based <= 0 or one_based >= len(hstu_item_to_bestrec):
                    continue
                mapped = hstu_item_to_bestrec[one_based]
                if mapped is not None:
                    hist_bestrec.append(int(mapped))
            histories[bestrec_user_id] = hist_bestrec
    return histories


def _content_features_for_candidates(
    candidate_ids: list[int],
    history_ids: list[int],
    embeddings: np.ndarray,
) -> np.ndarray:
    n = len(candidate_ids)
    if n == 0:
        return np.zeros((0, len(CONTENT_FEATURE_NAMES)), dtype=np.float32)
    cand = embeddings[np.asarray(candidate_ids, dtype=np.int64)]
    hist = [item for item in history_ids if 0 <= item < embeddings.shape[0]]
    hist_len = len(hist)
    if hist_len == 0:
        return np.zeros((n, len(CONTENT_FEATURE_NAMES)), dtype=np.float32)
    hist_emb = embeddings[np.asarray(hist, dtype=np.int64)]
    mean_vec_raw = hist_emb.mean(axis=0)
    mean_norm = float(np.linalg.norm(mean_vec_raw))
    profile = mean_vec_raw / max(mean_norm, 1e-8)
    last_vec = hist_emb[-1]
    recent5 = hist_emb[-5:]
    recent10 = hist_emb[-10:]
    pcos = cand @ profile
    lcos = cand @ last_vec
    r5 = cand @ recent5.T
    r10 = cand @ recent10.T
    hist_set = set(hist)
    return np.column_stack(
        [
            pcos,
            lcos,
            r5.max(axis=1),
            r5.mean(axis=1),
            r10.max(axis=1),
            r10.mean(axis=1),
            np.full(n, mean_norm, dtype=np.float32),
            np.full(n, math.log1p(hist_len), dtype=np.float32),
            np.full(n, min(hist_len, 50) / 50.0, dtype=np.float32),
            np.asarray([1.0 if item in hist_set else 0.0 for item in candidate_ids], dtype=np.float32),
        ]
    ).astype(np.float32, copy=False)


def build_content_user(
    base: Any,
    histories: dict[int, list[int]],
    embeddings: np.ndarray,
) -> ContentUserFeatures:
    content = _content_features_for_candidates(base.item_ids, histories.get(base.user_id, []), embeddings)
    features = np.hstack([base.features, content]).astype(np.float32, copy=False)
    return ContentUserFeatures(
        user_id=base.user_id,
        target_item_id=base.target_item_id,
        item_ids=base.item_ids,
        features=features,
        equal_rrf=base.equal_rrf,
        hstu_weighted_rrf=base.hstu_weighted_rrf,
        sasrec_weighted_rrf=base.sasrec_weighted_rrf,
    )


def build_users_with_content(
    hstu_rows: dict[int, dict[str, Any]],
    sasrec_rows: dict[int, dict[str, Any]],
    histories: dict[int, list[int]],
    embeddings: np.ndarray,
    *,
    top_k: int,
    rrf_k: int,
) -> list[ContentUserFeatures]:
    if set(hstu_rows) != set(sasrec_rows):
        raise ValueError("HSTU/SASRec user sets differ")
    users: list[ContentUserFeatures] = []
    for user_id in sorted(hstu_rows):
        base = build_user_features(user_id, hstu_rows[user_id], sasrec_rows[user_id], top_k=top_k, rrf_k=rrf_k)
        users.append(build_content_user(base, histories, embeddings))
    return users


def select_training_rows(
    users: list[ContentUserFeatures],
    *,
    max_negatives_per_user: int,
    max_train_rows: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    weights: list[float] = []
    for user in users:
        labels = np.asarray([1 if item == user.target_item_id else 0 for item in user.item_ids], dtype=np.int8)
        pos = np.flatnonzero(labels == 1)
        neg = np.flatnonzero(labels == 0)
        if max_negatives_per_user >= 0 and neg.size > max_negatives_per_user:
            # Keep the hard negatives the fixed fusion would rank highest.
            hard = neg[np.argsort(-user.equal_rrf[neg], kind="mergesort")]
            neg = hard[:max_negatives_per_user]
        chosen = np.concatenate([pos, neg])
        if chosen.size == 0:
            continue
        xs.append(user.features[chosen])
        ys.extend(labels[chosen].astype(int).tolist())
        weights.extend([1.0] * chosen.size)
    if not xs:
        raise ValueError("No training rows selected")
    x = np.vstack(xs).astype(np.float32, copy=False)
    y = np.asarray(ys, dtype=np.int8)
    w = np.asarray(weights, dtype=np.float32)
    positives = int(y.sum())
    negatives = int(y.size - positives)
    if positives:
        w[y == 1] = min(100.0, max(1.0, negatives / float(positives)))
    if max_train_rows > 0 and y.size > max_train_rows:
        rng = np.random.default_rng(seed)
        pos_idx = np.flatnonzero(y == 1)
        neg_idx = np.flatnonzero(y == 0)
        max_neg = max(0, max_train_rows - pos_idx.size)
        keep_neg = rng.choice(neg_idx, size=max_neg, replace=False) if neg_idx.size > max_neg else neg_idx
        keep = np.concatenate([pos_idx, keep_neg])
        rng.shuffle(keep)
        x, y, w = x[keep], y[keep], w[keep]
    return x, y, w


def fit_content_model(name: str, x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray, *, seed: int) -> ModelBundle:
    if name.startswith("sgd_log_alpha"):
        alpha = float(name.replace("sgd_log_alpha", ""))
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x)
        model = SGDClassifier(
            loss="log_loss",
            alpha=alpha,
            penalty="l2",
            max_iter=2500,
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


def final_scores_for_content_user(user: ContentUserFeatures, config: dict[str, Any], model: ModelBundle | None) -> np.ndarray:
    if config["type"] == "rrf":
        weight = float(config["hstu_weight"])
        return weight * user.hstu_weighted_rrf + (1.0 - weight) * user.sasrec_weighted_rrf
    if model is None:
        raise ValueError("Model config requires fitted model")
    pred = model_scores(model, user.features)
    blend = float(config["rrf_blend"])
    if pred.size <= 1:
        pred_pct = np.ones_like(pred, dtype=np.float32)
    else:
        order = np.argsort(-pred, kind="mergesort")
        ranks = np.empty_like(order, dtype=np.float32)
        ranks[order] = np.arange(pred.size, dtype=np.float32)
        pred_pct = 1.0 - ranks / float(pred.size - 1)
    if user.equal_rrf.size <= 1:
        rrf_pct = np.ones_like(user.equal_rrf, dtype=np.float32)
    else:
        order = np.argsort(-user.equal_rrf, kind="mergesort")
        ranks = np.empty_like(order, dtype=np.float32)
        ranks[order] = np.arange(user.equal_rrf.size, dtype=np.float32)
        rrf_pct = 1.0 - ranks / float(user.equal_rrf.size - 1)
    return (1.0 - blend) * pred_pct + blend * rrf_pct


def rank_content_user(
    user: ContentUserFeatures,
    *,
    config: dict[str, Any],
    model: ModelBundle | None,
) -> tuple[list[int], list[float], int | None, dict[str, float]]:
    scores = final_scores_for_content_user(user, config, model)
    order = sorted(range(len(user.item_ids)), key=lambda idx: (-float(scores[idx]), -float(user.equal_rrf[idx]), user.item_ids[idx]))
    ranked = [user.item_ids[idx] for idx in order]
    ranked_scores = [float(scores[idx]) for idx in order]
    try:
        rank0 = ranked.index(user.target_item_id)
    except ValueError:
        rank0 = None
    return ranked, ranked_scores, rank0, metric_from_rank(rank0)


def evaluate_users(
    users: list[ContentUserFeatures],
    *,
    config: dict[str, Any],
    model: ModelBundle | None,
    write_records: Path | None = None,
) -> dict[str, Any]:
    sums = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    target_in_union = 0
    handle = write_records.open("w", encoding="utf-8") if write_records else None
    try:
        for user in users:
            ranked, scores, rank0, metrics = rank_content_user(user, config=config, model=model)
            if user.target_item_id in set(user.item_ids):
                target_in_union += 1
            for key in sums:
                sums[key] += metrics[key]
            if handle is not None:
                handle.write(
                    json.dumps(
                        {
                            "dataset": "Video_Games",
                            "fold_id": 0,
                            "seed": int(config.get("seed", 0)),
                            "method": "hstu_sasrec_content_reranker_dev",
                            "user_id": user.user_id,
                            "target_item_id": user.target_item_id,
                            "candidate_scope": "hstu_sasrec_top50_union_blair_profile_history_masked",
                            "ndcg10": metrics["ndcg10"],
                            "hr10": metrics["hr10"],
                            "rr": metrics["rr"],
                            "rank": None if rank0 is None else rank0 + 1,
                            "top_ids": ranked[:50],
                            "top_scores": scores[:50],
                            "publication_grade": False,
                            "development_note": "Validation-trained content-aware HSTU/SASRec union reranker; requires frozen confirmatory rerun.",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-valid-jsonl", required=True)
    parser.add_argument("--sasrec-valid-jsonl", required=True)
    parser.add_argument("--hstu-test-jsonl", required=True)
    parser.add_argument("--sasrec-test-jsonl", required=True)
    parser.add_argument("--valid-sequence-csv", required=True)
    parser.add_argument("--test-sequence-csv", required=True)
    parser.add_argument("--item-map-json", required=True)
    parser.add_argument("--user-map-json", required=True)
    parser.add_argument("--blair-embedding-pt", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--max-negatives-per-user", type=int, default=32)
    parser.add_argument("--max-train-rows", type=int, default=1800000)
    parser.add_argument("--model-configs", default="sgd_log_alpha0.0001,sgd_log_alpha0.00003,histgb_lr=0.04_iter=120_leaf=15_l2=0.05,histgb_lr=0.06_iter=120_leaf=31_l2=0.05")
    parser.add_argument("--rrf-weights", default="0.75,0.8,0.85,0.9,0.95")
    parser.add_argument("--model-rrf-blends", default="0.0,0.25,0.5,0.75")
    args = parser.parse_args()

    started = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "hstu_valid": Path(args.hstu_valid_jsonl),
        "sasrec_valid": Path(args.sasrec_valid_jsonl),
        "hstu_test": Path(args.hstu_test_jsonl),
        "sasrec_test": Path(args.sasrec_test_jsonl),
        "valid_sequence_csv": Path(args.valid_sequence_csv),
        "test_sequence_csv": Path(args.test_sequence_csv),
        "item_map_json": Path(args.item_map_json),
        "user_map_json": Path(args.user_map_json),
        "blair_embedding_pt": Path(args.blair_embedding_pt),
    }

    embeddings = load_bestrec_embeddings(paths["blair_embedding_pt"], paths["item_map_json"])
    valid_histories = parse_hstu_sequence_histories(paths["valid_sequence_csv"], user_map_path=paths["user_map_json"], item_map_path=paths["item_map_json"])
    test_histories = parse_hstu_sequence_histories(paths["test_sequence_csv"], user_map_path=paths["user_map_json"], item_map_path=paths["item_map_json"])
    hstu_valid = load_rows(paths["hstu_valid"], "teacher_top_ids", "teacher_top_scores")
    sasrec_valid = load_rows(paths["sasrec_valid"], "top_ids", "top_scores")
    hstu_test = load_rows(paths["hstu_test"], "teacher_top_ids", "teacher_top_scores")
    sasrec_test = load_rows(paths["sasrec_test"], "top_ids", "top_scores")

    valid_users = build_users_with_content(hstu_valid, sasrec_valid, valid_histories, embeddings, top_k=args.top_k, rrf_k=args.rrf_k)
    test_users = build_users_with_content(hstu_test, sasrec_test, test_histories, embeddings, top_k=args.top_k, rrf_k=args.rrf_k)
    base_valid_users = [user for user in valid_users]
    train_base, select_base = split_users(base_valid_users, train_fraction=args.train_fraction, seed=args.seed)
    train_ids = {user.user_id for user in train_base}
    train_users = [user for user in valid_users if user.user_id in train_ids]
    select_users = [user for user in valid_users if user.user_id not in train_ids]

    rrf_weights = [float(value) for value in args.rrf_weights.split(",") if value.strip()]
    model_names = [value.strip() for value in args.model_configs.split(",") if value.strip()]
    blends = [float(value) for value in args.model_rrf_blends.split(",") if value.strip()]
    candidate_results: list[dict[str, Any]] = []
    for weight in rrf_weights:
        config = {"name": f"rrf_hstu_weight_{weight:g}", "type": "rrf", "hstu_weight": weight, "seed": args.seed}
        candidate_results.append({"config": config, "selection_metrics": evaluate_users(select_users, config=config, model=None)})

    x_train, y_train, w_train = select_training_rows(
        train_users,
        max_negatives_per_user=args.max_negatives_per_user,
        max_train_rows=args.max_train_rows,
        seed=args.seed,
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
        model = fit_content_model(model_name, x_train, y_train, w_train, seed=args.seed)
        fitted[model_name] = model
        for blend in blends:
            config = {
                "name": f"{model_name}_rrfblend{blend:g}",
                "type": "model",
                "model_name": model_name,
                "rrf_blend": blend,
                "seed": args.seed,
            }
            candidate_results.append({"config": config, "selection_metrics": evaluate_users(select_users, config=config, model=model)})

    selected = max(candidate_results, key=lambda row: (row["selection_metrics"]["ndcg10"], row["selection_metrics"]["hr10"], row["selection_metrics"]["rr"]))
    selected_config = dict(selected["config"])
    final_model: ModelBundle | None = None
    final_train_stats = None
    if selected_config["type"] == "model":
        x_all, y_all, w_all = select_training_rows(
            valid_users,
            max_negatives_per_user=args.max_negatives_per_user,
            max_train_rows=args.max_train_rows,
            seed=args.seed,
        )
        final_train_stats = {
            "rows": int(y_all.size),
            "features": int(x_all.shape[1]),
            "positives": int(y_all.sum()),
            "negatives": int(y_all.size - y_all.sum()),
            "positive_weight": float(w_all[y_all == 1][0]) if int(y_all.sum()) else None,
        }
        final_model = fit_content_model(str(selected_config["model_name"]), x_all, y_all, w_all, seed=args.seed)

    records_path = out_dir / "warm_full_catalog_records_Video_Games_hstu_sasrec_content_reranker_test.jsonl"
    test_metrics = evaluate_users(test_users, config=selected_config, model=final_model, write_records=records_path)
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
            "max_negatives_per_user": args.max_negatives_per_user,
            "max_train_rows": args.max_train_rows,
            "feature_names": UNION_FEATURE_NAMES + CONTENT_FEATURE_NAMES,
            "model_configs": model_names,
            "rrf_weights": rrf_weights,
            "model_rrf_blends": blends,
        },
        "embedding_contract": {
            "source_shape": [25613, 768],
            "bestrec_shape": list(embeddings.shape),
            "id_translation": "bestrec_emb[i] = hstu_emb[bestrec_zero_based_to_hstu_one_based[i]]",
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
            "fixed_rrf_test_ndcg10": 0.07272761825417069,
            "adaptive_fusion_test_ndcg10": 0.07294970284697865,
            "local_hstu_sm120_final_export_ndcg10": 0.07382241421701587,
            "upstream_hstu_report_ndcg10": 0.076,
            "gap_to_strict_dev9_hstu": test_metrics["ndcg10"] - 0.07121812232925798,
            "gap_to_fixed_rrf": test_metrics["ndcg10"] - 0.07272761825417069,
            "gap_to_adaptive_fusion": test_metrics["ndcg10"] - 0.07294970284697865,
            "gap_to_local_hstu_sm120_final_export": test_metrics["ndcg10"] - 0.07382241421701587,
            "gap_to_upstream_hstu_report": test_metrics["ndcg10"] - 0.076,
        },
        "records": sha256_file(records_path),
        "honest_interpretation": "Development-only content-aware reranker trained on validation users. It must beat HSTU and later survive frozen confirmatory reruns before any claim.",
    }
    summary_path = out_dir / "hstu_sasrec_content_reranker_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "out_dir": str(out_dir),
        "selected_config": selected_config,
        "selection_ndcg10": selected["selection_metrics"]["ndcg10"],
        "test_ndcg10": test_metrics["ndcg10"],
        "gap_to_adaptive": summary["comparators"]["gap_to_adaptive_fusion"],
        "gap_to_local_hstu": summary["comparators"]["gap_to_local_hstu_sm120_final_export"],
        "summary": str(summary_path),
        "records": str(records_path),
        "records_sha256": summary["records"].get("sha256"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
