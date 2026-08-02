#!/usr/bin/env python3
"""Measure label-safe transition structure in sequential-recommendation data."""

from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path


def entropy(counts: collections.Counter) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum(
        (count / total) * math.log(count / total)
        for count in counts.values()
    )


def rank_metrics(ranked: list[int], target: int, k: int = 10) -> tuple[float, float]:
    try:
        rank = ranked[:k].index(target)
    except ValueError:
        return 0.0, 0.0
    return 1.0, 1.0 / math.log2(rank + 2.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--max-sequence-length", type=int, default=50)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sequences = []
    with args.data_file.open(encoding="utf-8") as handle:
        for line in handle:
            fields = [int(value) for value in line.split()]
            if len(fields) < 4:
                continue
            sequences.append(fields[1:])
    if not sequences:
        raise SystemExit("no usable user sequences")

    item_counts: collections.Counter[int] = collections.Counter()
    previous_counts: collections.Counter[int] = collections.Counter()
    next_counts: collections.Counter[int] = collections.Counter()
    transition_counts: dict[int, collections.Counter[int]] = collections.defaultdict(
        collections.Counter
    )
    pair_counts: collections.Counter[tuple[int, int]] = collections.Counter()
    train_lengths = []
    for sequence in sequences:
        train = sequence[-(args.max_sequence_length + 2):-2]
        train_lengths.append(len(train))
        item_counts.update(train)
        for previous, following in zip(train, train[1:]):
            previous_counts[previous] += 1
            next_counts[following] += 1
            transition_counts[previous][following] += 1
            pair_counts[(previous, following)] += 1

    transition_total = sum(pair_counts.values())
    joint_entropy = entropy(pair_counts)
    previous_entropy = entropy(previous_counts)
    next_entropy = entropy(next_counts)
    mutual_information = previous_entropy + next_entropy - joint_entropy
    conditional_entropy = joint_entropy - previous_entropy

    popularity = [item for item, _ in item_counts.most_common()]
    popularity_rank = {item: index for index, item in enumerate(popularity)}
    transition_rankings = {
        previous: [item for item, _ in counts.most_common()]
        for previous, counts in transition_counts.items()
    }

    popularity_metrics = []
    transition_metrics = []
    validation_pair_seen = 0
    validation_pair_support = []
    validation_target_popularity = []
    for sequence in sequences:
        previous, target = sequence[-3], sequence[-2]
        pair_support = pair_counts[(previous, target)]
        validation_pair_seen += pair_support > 0
        validation_pair_support.append(pair_support)
        validation_target_popularity.append(item_counts[target])

        popularity_metrics.append(rank_metrics(popularity, target))
        ranked = transition_rankings.get(previous, [])
        if len(ranked) < 10:
            present = set(ranked)
            ranked = ranked + [item for item in popularity if item not in present]
        transition_metrics.append(rank_metrics(ranked, target))

    item_entropy = entropy(item_counts)
    artifact = {
        "protocol": "TRAIN_WINDOW_TRANSITION_STRUCTURE_V1",
        "label": args.label,
        "data_file": str(args.data_file.resolve()),
        "test_access": "none",
        "window": {
            "max_sequence_length": args.max_sequence_length,
            "held_out_items_per_user": 2,
        },
        "counts": {
            "users": len(sequences),
            "training_window_interactions": sum(train_lengths),
            "training_transitions": transition_total,
            "unique_training_items": len(item_counts),
            "unique_training_pairs": len(pair_counts),
            "mean_training_window_length": sum(train_lengths) / len(train_lengths),
        },
        "entropy_nats": {
            "item": item_entropy,
            "item_normalized_by_uniform": item_entropy / math.log(max(len(item_counts), 2)),
            "previous": previous_entropy,
            "next": next_entropy,
            "next_given_previous": conditional_entropy,
            "previous_next_mutual_information": mutual_information,
            "normalized_mutual_information_by_next_entropy": (
                mutual_information / next_entropy if next_entropy else 0.0
            ),
        },
        "validation_label_safe_diagnostics": {
            "pair_seen_in_training_fraction": validation_pair_seen / len(sequences),
            "mean_pair_training_support": sum(validation_pair_support) / len(sequences),
            "mean_target_training_popularity": (
                sum(validation_target_popularity) / len(sequences)
            ),
            "popularity_HR@10": sum(value[0] for value in popularity_metrics)
            / len(sequences),
            "popularity_NDCG@10": sum(value[1] for value in popularity_metrics)
            / len(sequences),
            "first_order_transition_HR@10": sum(
                value[0] for value in transition_metrics
            )
            / len(sequences),
            "first_order_transition_NDCG@10": sum(
                value[1] for value in transition_metrics
            )
            / len(sequences),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "label": args.label,
        **artifact["entropy_nats"],
        **artifact["validation_label_safe_diagnostics"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
