#!/usr/bin/env python3
"""Post-hoc cycle-4 probe over the already opened RAVEL cohort.

This is hypothesis-generating analysis, not a new PoC and not evidence for a
claim.  It never fits or reruns a model.  It asks what the frozen RAVEL residual
would have done if its adjusted score had been granted explicit authority only
over the continuation below the exact linear top 10.
"""

from __future__ import annotations

import gc
import json
import math
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

import ravel_poc as ravel

core = ravel.core
np = ravel.np


def decode_float32_bits(bits: str) -> float:
    return float(struct.unpack("<f", bytes.fromhex(bits))[0])


def graded_ndcg_at_20(
    ranking: tuple[int, ...], ratings_by_item: Mapping[int, int]
) -> float:
    discounts = [1.0 / math.log2(rank + 2.0) for rank in range(20)]
    dcg = sum(
        ((2.0 ** float(ratings_by_item.get(item, 0))) - 1.0) * discounts[rank]
        for rank, item in enumerate(ranking[:20])
    )
    gains = sorted(
        ((2.0 ** float(rating)) - 1.0 for rating in ratings_by_item.values()),
        reverse=True,
    )
    ideal = sum(gain * discount for gain, discount in zip(gains[:20], discounts))
    return float(dcg / ideal) if ideal > 0.0 else float("nan")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    run_directory = (
        project_root
        / "experiments"
        / "runs"
        / "ravel_poc_runs"
        / "ravel-poc-v1-20260806T180639143183Z-f9e6c2ffb44c"
    )
    config = json.loads(
        (project_root / "src" / "configs" / "ravel_poc_ml1m_v1.json").read_text(
            encoding="utf-8"
        )
    )
    extracted = run_directory / "sha_locked_ml1m_extracted"
    item_ids, _metadata = core.load_movie_metadata(
        extracted / "movies.dat", str(config["embedding"]["metadata_template"])
    )
    item_to_index = {item_id: index for index, item_id in enumerate(item_ids)}
    interactions = core.load_ratings(extracted / "ratings.dat", item_to_index)
    splits, diagnostics = ravel.derive_ravel_cohort(interactions, config["dataset"])
    split_by_user = {split.user_id: split for split in splits}

    methods = (
        "linear",
        "selected_bpr",
        "bpr_continuation",
        "adjusted_continuation",
    )
    rows_by_seed: dict[int, dict[str, list[Mapping[str, Any]]]] = {}
    changed_pair_relations = 0
    total_pair_relations = 0
    for seed in map(int, config["replicate_seeds"]):
        manifest_path = next(
            run_directory.glob(f"test_output_manifest_seed{seed}_*_seq001.json")
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        per_method = {method: [] for method in methods}
        for record in manifest["entries"]:
            user_id = int(record["user_id"])
            split = split_by_user[user_id]
            union = tuple(map(int, record["union_candidates_C"]))
            linear = tuple(map(int, record["linear_full_union_ranking"]))
            top = linear[:10]
            top_set = set(top)
            linear_rank = {item: rank for rank, item in enumerate(linear)}
            adjusted = {
                item: decode_float32_bits(bits)
                for item, bits in zip(
                    union, record["proposal_union_score_bits_by_union_item"], strict=True
                )
            }
            continuation = tuple(
                sorted(
                    (item for item in union if item not in top_set),
                    key=lambda item: (-adjusted[item], linear_rank[item], item),
                )
            )
            continuation_order = (*top, *continuation)
            bpr_order = tuple(map(int, record["selected_bpr_full_union_ranking"]))
            bpr_rank = {item: rank for rank, item in enumerate(bpr_order)}
            bpr_continuation_order = (
                *top,
                *sorted(
                    (item for item in union if item not in top_set),
                    key=lambda item: (bpr_rank[item], linear_rank[item], item),
                ),
            )
            pairs, _raw = ravel.preference_pairs_by_movie_id(
                [event for event in split.test if event.item_index in set(union)],
                int(config["dataset"]["preference_pair_minimum_rating_gap"]),
                int(config["evaluation"]["maximum_preference_pairs_per_user"]),
                int(config["evaluation"]["preference_pair_subsample_seed"]),
                user_id,
                item_ids,
            )
            continuation_pairs = tuple(
                (chosen, rejected)
                for chosen, rejected in pairs
                if chosen not in top_set and rejected not in top_set
            )
            baseline_page_2 = set(linear[10:20])
            page_2_touching_pairs = tuple(
                (chosen, rejected)
                for chosen, rejected in pairs
                if chosen not in top_set
                and rejected not in top_set
                and (chosen in baseline_page_2 or rejected in baseline_page_2)
            )
            ratings_by_item = {event.item_index: event.rating for event in split.test}
            positives = frozenset(
                item
                for item, rating in ratings_by_item.items()
                if rating >= int(config["dataset"]["positive_rating_min"])
            )
            if pairs:
                base_index = {item: rank for rank, item in enumerate(linear)}
                continuation_index = {
                    item: rank for rank, item in enumerate(continuation_order)
                }
                changed_pair_relations += sum(
                    (base_index[chosen] < base_index[rejected])
                    != (continuation_index[chosen] < continuation_index[rejected])
                    for chosen, rejected in pairs
                )
                total_pair_relations += len(pairs)
            for method, ranking in (
                ("linear", linear),
                ("selected_bpr", bpr_order),
                ("bpr_continuation", bpr_continuation_order),
                ("adjusted_continuation", continuation_order),
            ):
                accuracy, correct = ravel._pair_accuracy(pairs, ranking)
                continuation_accuracy, continuation_correct = ravel._pair_accuracy(
                    continuation_pairs, ranking
                )
                page_2_touching_accuracy, page_2_touching_correct = (
                    ravel._pair_accuracy(page_2_touching_pairs, ranking)
                )
                per_method[method].append(
                    {
                        "user_id": user_id,
                        "preference_pair_accuracy": accuracy,
                        "preference_pairs": float(len(pairs)),
                        "preference_correct": float(correct),
                        "continuation_preference_pair_accuracy": continuation_accuracy,
                        "continuation_preference_pairs": float(len(continuation_pairs)),
                        "continuation_preference_correct": float(continuation_correct),
                        "binary_ndcg_at_20": core.binary_ndcg(ranking, positives, 20),
                        "page_2_recall": float(
                            len(set(ranking[10:20]) & set(positives)) / len(positives)
                        ),
                        "graded_ndcg_at_20": graded_ndcg_at_20(
                            tuple(ranking), ratings_by_item
                        ),
                        "page_2_touching_preference_pair_accuracy": (
                            page_2_touching_accuracy
                        ),
                        "page_2_touching_preference_pairs": float(
                            len(page_2_touching_pairs)
                        ),
                        "page_2_touching_preference_correct": float(
                            page_2_touching_correct
                        ),
                    }
                )
        rows_by_seed[seed] = per_method
        del manifest
        gc.collect()

    averaged: dict[str, list[Mapping[str, Any]]] = {}
    summaries: dict[str, Mapping[str, Any]] = {}
    for method in methods:
        grouped: dict[int, list[float]] = defaultdict(list)
        continuation_grouped: dict[int, list[float]] = defaultdict(list)
        extra_grouped: dict[str, dict[int, list[float]]] = {
            metric: defaultdict(list)
            for metric in (
                "binary_ndcg_at_20",
                "page_2_recall",
                "graded_ndcg_at_20",
                "page_2_touching_preference_pair_accuracy",
            )
        }
        for seed in rows_by_seed.values():
            for row in seed[method]:
                value = float(row["preference_pair_accuracy"])
                if math.isfinite(value):
                    grouped[int(row["user_id"])].append(value)
                continuation_value = float(
                    row["continuation_preference_pair_accuracy"]
                )
                if math.isfinite(continuation_value):
                    continuation_grouped[int(row["user_id"])].append(
                        continuation_value
                    )
                for metric, metric_grouped in extra_grouped.items():
                    metric_value = float(row[metric])
                    if math.isfinite(metric_value):
                        metric_grouped[int(row["user_id"])].append(metric_value)
        all_user_ids = sorted(
            set(grouped)
            | set(continuation_grouped)
            | {
                user_id
                for metric_grouped in extra_grouped.values()
                for user_id in metric_grouped
            }
        )
        averaged[method] = [
            {
                "user_id": user_id,
                "preference_pair_accuracy": (
                    float(np.mean(grouped[user_id]))
                    if user_id in grouped
                    else float("nan")
                ),
                "continuation_preference_pair_accuracy": (
                    float(np.mean(continuation_grouped[user_id]))
                    if user_id in continuation_grouped
                    else float("nan")
                ),
                **{
                    metric: (
                        float(np.mean(metric_grouped[user_id]))
                        if user_id in metric_grouped
                        else float("nan")
                    )
                    for metric, metric_grouped in extra_grouped.items()
                },
            }
            for user_id in all_user_ids
        ]
        summaries[method] = {
            "pair_bearing_users": len(grouped),
            "user_macro_preference_accuracy": float(
                np.mean(
                    [
                        value
                        for row in averaged[method]
                        if math.isfinite(
                            value := float(row["preference_pair_accuracy"])
                        )
                    ]
                )
            ),
            "continuation_pair_bearing_users": len(continuation_grouped),
            "user_macro_continuation_preference_accuracy": float(
                np.mean(
                    [
                        value
                        for row in averaged[method]
                        if math.isfinite(
                            value := float(
                                row["continuation_preference_pair_accuracy"]
                            )
                        )
                    ]
                )
            ),
            **{
                metric: float(
                    np.mean(
                        [
                            value
                            for row in averaged[method]
                            if math.isfinite(value := float(row[metric]))
                        ]
                    )
                )
                for metric in extra_grouped
            },
            "page_2_touching_pair_bearing_users": len(
                extra_grouped["page_2_touching_preference_pair_accuracy"]
            ),
        }

    comparisons = {}
    for baseline, offset in (
        ("linear", 0),
        ("selected_bpr", 1),
        ("bpr_continuation", 2),
    ):
        for metric, metric_offset in (
            ("preference_pair_accuracy", 0),
            ("continuation_preference_pair_accuracy", 10),
        ):
            comparisons[
                f"adjusted_continuation_minus_{baseline}_{metric}"
            ] = core.paired_user_cluster_bootstrap(
                averaged["adjusted_continuation"],
                averaged[baseline],
                metric,
                10000,
                0.05,
                20261217 + offset + metric_offset,
            )
    for metric, offset in (
        ("binary_ndcg_at_20", 0),
        ("page_2_recall", 2),
        ("graded_ndcg_at_20", 3),
        ("page_2_touching_preference_pair_accuracy", 5),
    ):
        comparisons[f"adjusted_continuation_minus_linear_{metric}"] = (
            core.paired_user_cluster_bootstrap(
                averaged["adjusted_continuation"],
                averaged["linear"],
                metric,
                10000,
                0.05,
                20263000 + offset,
            )
        )
    print(
        json.dumps(
            {
                "schema": "ravel-opened-cohort-continuation-posthoc-v1",
                "scientific_status": "hypothesis_generating_only_not_a_poc",
                "models_fit_or_rerun": False,
                "opened_ravel_cohort_reused": True,
                "exact_linear_top10_by_construction": True,
                "eligible_users": diagnostics["eligible_before_hash_slice"],
                "summaries": summaries,
                "comparisons": comparisons,
                "fraction_of_evaluated_pair_relations_changed": (
                    changed_pair_relations / total_pair_relations
                    if total_pair_relations
                    else None
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
