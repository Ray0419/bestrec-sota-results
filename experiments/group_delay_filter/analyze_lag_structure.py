#!/usr/bin/env python3
"""Measure validation predictability from train-window item lags."""

from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path


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
    parser.add_argument("--max-lag", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sequences = []
    with args.data_file.open(encoding="utf-8") as handle:
        for line in handle:
            fields = [int(value) for value in line.split()]
            if len(fields) >= 4:
                sequences.append(fields[1:])
    if not sequences:
        raise SystemExit("no usable user sequences")

    item_counts: collections.Counter[int] = collections.Counter()
    lag_counts = {
        lag: collections.defaultdict(collections.Counter)
        for lag in range(1, args.max_lag + 1)
    }
    for sequence in sequences:
        train = sequence[-(args.max_sequence_length + 2):-2]
        item_counts.update(train)
        for lag, mappings in lag_counts.items():
            for index in range(lag, len(train)):
                mappings[train[index - lag]][train[index]] += 1

    popularity = [item for item, _ in item_counts.most_common()]
    lag_rankings = {
        lag: {
            source: [item for item, _ in counts.most_common()]
            for source, counts in mappings.items()
        }
        for lag, mappings in lag_counts.items()
    }

    rows = []
    for lag in range(1, args.max_lag + 1):
        metrics = []
        target_support = []
        for sequence in sequences:
            if len(sequence) < lag + 2:
                continue
            source = sequence[-2 - lag]
            target = sequence[-2]
            target_support.append(lag_counts[lag][source][target])
            ranked = lag_rankings[lag].get(source, [])
            if len(ranked) < 10:
                present = set(ranked)
                ranked = ranked + [item for item in popularity if item not in present]
            metrics.append(rank_metrics(ranked, target))
        if not metrics:
            raise SystemExit(f"no users have enough history for lag {lag}")
        rows.append(
            {
                "lag": lag,
                "evaluated_users": len(metrics),
                "excluded_short_history_users": len(sequences) - len(metrics),
                "validation_pair_seen_fraction": sum(value > 0 for value in target_support)
                / len(metrics),
                "mean_validation_pair_training_support": sum(target_support)
                / len(metrics),
                "validation_HR@10": sum(value[0] for value in metrics) / len(metrics),
                "validation_NDCG@10": sum(value[1] for value in metrics) / len(metrics),
            }
        )

    artifact = {
        "protocol": "TRAIN_WINDOW_LAG_STRUCTURE_V1",
        "label": args.label,
        "data_file": str(args.data_file.resolve()),
        "test_access": "none",
        "window": {
            "max_sequence_length": args.max_sequence_length,
            "held_out_items_per_user": 2,
        },
        "counts": {
            "users": len(sequences),
            "unique_training_items": len(item_counts),
        },
        "validation_label_safe_lag_diagnostics": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({"label": args.label, "lags": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
