"""Train content-aware adaptive HSTU/SASRec fusion weights.

This extends the previous user-level adaptive fusion with BLaIR profile
summaries. It does not rerank candidates directly; it only learns when to move
the RRF weight away from the validation-selected global anchor.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

LAB_DIR = Path(__file__).resolve().parent
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from train_hstu_sasrec_adaptive_fusion import (  # noqa: E402
    USER_FEATURE_NAMES,
    AdaptiveModel,
    best_weight_for_user,
    evaluate_adaptive,
    train_adaptive_model,
    user_features_from_rows,
)
from train_hstu_sasrec_content_reranker import (  # noqa: E402
    load_bestrec_embeddings,
    parse_hstu_sequence_histories,
)
from train_hstu_sasrec_union_reranker import (  # noqa: E402
    build_user_features,
    load_rows,
    sha256_file,
    split_users,
)


CONTENT_GATE_FEATURE_NAMES = [
    "hstu_top1_profile_cos",
    "sasrec_top1_profile_cos",
    "top1_profile_cos_diff",
    "hstu_top10_profile_mean",
    "sasrec_top10_profile_mean",
    "top10_profile_mean_diff",
    "hstu_top10_profile_max",
    "sasrec_top10_profile_max",
    "top10_profile_max_diff",
    "hstu_top50_profile_mean",
    "sasrec_top50_profile_mean",
    "top50_profile_mean_diff",
    "hstu_top1_last_cos",
    "sasrec_top1_last_cos",
    "top1_last_cos_diff",
    "history_profile_norm",
    "history_len_log",
]


@dataclass
class ContentMeta:
    user: Any
    features: np.ndarray
    best_weight: float | None
    best_weight_label: int | None


def _ids(row: dict[str, Any], key: str, top_k: int) -> list[int]:
    return [int(value) for value in row[key][:top_k]]


def _profile(history: list[int], embeddings: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, int]:
    hist = [item for item in history if 0 <= item < embeddings.shape[0]]
    if not hist:
        z = np.zeros(embeddings.shape[1], dtype=np.float32)
        return z, z, 0.0, 0
    hist_emb = embeddings[np.asarray(hist, dtype=np.int64)]
    mean_raw = hist_emb.mean(axis=0)
    norm = float(np.linalg.norm(mean_raw))
    mean = mean_raw / max(norm, 1e-8)
    return mean.astype(np.float32, copy=False), hist_emb[-1].astype(np.float32, copy=False), norm, len(hist)


def _cos_stats(item_ids: list[int], vector: np.ndarray, embeddings: np.ndarray) -> tuple[float, float, float]:
    if not item_ids:
        return 0.0, 0.0, 0.0
    sims = embeddings[np.asarray(item_ids, dtype=np.int64)] @ vector
    return float(sims[0]), float(sims.mean()), float(sims.max())


def content_gate_features(
    hstu_row: dict[str, Any],
    sasrec_row: dict[str, Any],
    history: list[int],
    embeddings: np.ndarray,
    *,
    top_k: int,
) -> np.ndarray:
    profile, last, profile_norm, hist_len = _profile(history, embeddings)
    h_ids = _ids(hstu_row, "teacher_top_ids", top_k)
    s_ids = _ids(sasrec_row, "top_ids", top_k)
    h1p, h50p_mean, _h50p_max = _cos_stats(h_ids[:top_k], profile, embeddings)
    s1p, s50p_mean, _s50p_max = _cos_stats(s_ids[:top_k], profile, embeddings)
    _h10p_first, h10p_mean, h10p_max = _cos_stats(h_ids[:10], profile, embeddings)
    _s10p_first, s10p_mean, s10p_max = _cos_stats(s_ids[:10], profile, embeddings)
    h1l, _h50l_mean, _h50l_max = _cos_stats(h_ids[:1], last, embeddings)
    s1l, _s50l_mean, _s50l_max = _cos_stats(s_ids[:1], last, embeddings)
    return np.asarray(
        [
            h1p,
            s1p,
            h1p - s1p,
            h10p_mean,
            s10p_mean,
            h10p_mean - s10p_mean,
            h10p_max,
            s10p_max,
            h10p_max - s10p_max,
            h50p_mean,
            s50p_mean,
            h50p_mean - s50p_mean,
            h1l,
            s1l,
            h1l - s1l,
            profile_norm,
            float(np.log1p(hist_len)),
        ],
        dtype=np.float32,
    )


def build_content_meta(
    hstu_rows: dict[int, dict[str, Any]],
    sasrec_rows: dict[int, dict[str, Any]],
    histories: dict[int, list[int]],
    embeddings: np.ndarray,
    *,
    weights: list[float],
    top_k: int,
    rrf_k: int,
    seed: int,
) -> list[ContentMeta]:
    if set(hstu_rows) != set(sasrec_rows):
        raise ValueError("HSTU/SASRec user sets differ")
    metas: list[ContentMeta] = []
    for user_id in sorted(hstu_rows):
        user = build_user_features(user_id, hstu_rows[user_id], sasrec_rows[user_id], top_k=top_k, rrf_k=rrf_k)
        base_features = user_features_from_rows(hstu_rows[user_id], sasrec_rows[user_id], top_k=top_k)
        extra = content_gate_features(hstu_rows[user_id], sasrec_rows[user_id], histories.get(user_id, []), embeddings, top_k=top_k)
        weight, label = best_weight_for_user(user, weights, seed)
        metas.append(ContentMeta(user=user, features=np.concatenate([base_features, extra]).astype(np.float32), best_weight=weight, best_weight_label=label))
    return metas


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
    parser.add_argument("--weights", default="0.0,0.1,0.25,0.5,0.65,0.75,0.8,0.85,0.9,0.95,1.0")
    parser.add_argument("--shrinks", default="0.1,0.25,0.5,0.75,1.0")
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
        "valid_sequence_csv": Path(args.valid_sequence_csv),
        "test_sequence_csv": Path(args.test_sequence_csv),
        "item_map_json": Path(args.item_map_json),
        "user_map_json": Path(args.user_map_json),
        "blair_embedding_pt": Path(args.blair_embedding_pt),
    }
    weights = [float(value) for value in args.weights.split(",") if value.strip()]
    shrinks = [float(value) for value in args.shrinks.split(",") if value.strip()]
    model_names = [value.strip() for value in args.models.split(",") if value.strip()]
    embeddings = load_bestrec_embeddings(paths["blair_embedding_pt"], paths["item_map_json"])
    valid_histories = parse_hstu_sequence_histories(paths["valid_sequence_csv"], user_map_path=paths["user_map_json"], item_map_path=paths["item_map_json"])
    test_histories = parse_hstu_sequence_histories(paths["test_sequence_csv"], user_map_path=paths["user_map_json"], item_map_path=paths["item_map_json"])

    hstu_valid = load_rows(paths["hstu_valid"], "teacher_top_ids", "teacher_top_scores")
    sasrec_valid = load_rows(paths["sasrec_valid"], "top_ids", "top_scores")
    hstu_test = load_rows(paths["hstu_test"], "teacher_top_ids", "teacher_top_scores")
    sasrec_test = load_rows(paths["sasrec_test"], "top_ids", "top_scores")
    valid_meta = build_content_meta(hstu_valid, sasrec_valid, valid_histories, embeddings, weights=weights, top_k=args.top_k, rrf_k=args.rrf_k, seed=args.seed)
    test_meta = build_content_meta(hstu_test, sasrec_test, test_histories, embeddings, weights=weights, top_k=args.top_k, rrf_k=args.rrf_k, seed=args.seed)

    valid_users = [meta.user for meta in valid_meta]
    train_users, _select_users = split_users(valid_users, train_fraction=args.train_fraction, seed=args.seed)
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
                "name": f"{name}_content_anchor{args.anchor_weight:g}_shrink{shrink:g}",
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
            "label_distribution": {str(weight): sum(1 for meta in labeled if meta.best_weight == weight) for weight in weights},
        }

    records_path = out_dir / "warm_full_catalog_records_Video_Games_hstu_sasrec_content_adaptive_fusion_test.jsonl"
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
            "user_feature_names": USER_FEATURE_NAMES + CONTENT_GATE_FEATURE_NAMES,
        },
        "embedding_contract": {
            "source_shape": [25613, 768],
            "bestrec_shape": list(embeddings.shape),
            "id_translation": "bestrec_emb[i] = hstu_emb[bestrec_zero_based_to_hstu_one_based[i]]",
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
        "honest_interpretation": "Development-only content-aware adaptive fusion selected on held-out validation users.",
    }
    summary_path = out_dir / "hstu_sasrec_content_adaptive_fusion_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
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
