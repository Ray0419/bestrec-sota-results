#!/usr/bin/env python3
"""Summarize train-time versus post-training channel-sharing outcomes."""

from __future__ import annotations

import argparse
import ast
import glob
import hashlib
import json
import math
import re
from pathlib import Path

from scipy.stats import t as student_t


SEED_PATTERN = re.compile(r"_s(\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_from(path: Path) -> int:
    match = SEED_PATTERN.search(path.name)
    if not match:
        raise ValueError(f"cannot parse seed from {path}")
    return int(match.group(1))


def final_log_metric(path: Path, metric: str) -> float:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            payload = line.split(" - ", 1)[-1].strip()
            if not payload.startswith("{'Epoch':"):
                continue
            record = ast.literal_eval(payload)
            if metric in record:
                records.append(float(record[metric]))
    if not records:
        raise ValueError(f"no {metric} record in {path}")
    return records[-1]


def distribution(values: list[float]) -> dict[str, float | int | list[float]]:
    mean = sum(values) / len(values)
    if len(values) == 1:
        sample_sd = 0.0
        interval = [mean, mean]
    else:
        sample_sd = math.sqrt(
            sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        )
        half_width = float(student_t.ppf(0.975, len(values) - 1)) \
            * sample_sd / math.sqrt(len(values))
        interval = [mean - half_width, mean + half_width]
    return {
        "n_seeds": len(values),
        "mean": mean,
        "sample_sd": sample_sd,
        "paired_t_95_ci": interval,
        "positive_seeds": sum(value > 0 for value in values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection-glob", required=True)
    parser.add_argument("--trained-shared-log-glob", required=True)
    parser.add_argument("--metric", default="NDCG@10")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    projection_paths = [Path(path) for path in sorted(glob.glob(args.projection_glob))]
    shared_paths = [
        Path(path) for path in sorted(glob.glob(args.trained_shared_log_glob))
    ]
    projections = {seed_from(path): path for path in projection_paths}
    shared_logs = {seed_from(path): path for path in shared_paths}
    if not projections or projections.keys() != shared_logs.keys():
        raise SystemExit(
            f"seed mismatch: projections={sorted(projections)}, "
            f"trained_shared={sorted(shared_logs)}"
        )

    rows = []
    for seed in sorted(projections):
        projection_path = projections[seed]
        paired = json.loads(projection_path.read_text(encoding="utf-8"))
        metric = paired["masks"]["strict_negative_infinity"][args.metric]
        full = float(metric["baseline"])
        posthoc = float(metric["projected"])
        shared = final_log_metric(shared_logs[seed], args.metric)
        rows.append(
            {
                "seed": seed,
                "full_trained": full,
                "all_layers_shared_trained_from_scratch": shared,
                "full_then_final_layer_posthoc_shared": posthoc,
                "full_minus_all_layers_trained_shared": full - shared,
                "final_posthoc_minus_full": posthoc - full,
                "final_posthoc_minus_all_layers_trained_shared": posthoc - shared,
                "projection_artifact": str(projection_path.resolve()),
                "projection_artifact_sha256": sha256(projection_path),
                "trained_shared_log": str(shared_logs[seed].resolve()),
                "trained_shared_log_sha256": sha256(shared_logs[seed]),
            }
        )

    contrasts = {
        key: distribution([row[key] for row in rows])
        for key in (
            "full_minus_all_layers_trained_shared",
            "final_posthoc_minus_full",
            "final_posthoc_minus_all_layers_trained_shared",
        )
    }
    artifact = {
        "protocol": "TRAIN_TIME_POSTHOC_CHANNEL_SHARING_REVERSAL_V1",
        "status": "retrospective_exploratory",
        "split": "test",
        "test_access": "outcome_known",
        "metric": args.metric,
        "rows": rows,
        "contrasts": contrasts,
        "interpretation": (
            "The all-layers shared train-time arm loses while final-layer-only "
            "posthoc sharing improves. This is a preliminary ablation reversal, not an "
            "exact optimization-path comparison, because the depth allocations differ."
        ),
        "required_control": (
            "Train an early-full/final-shared model from scratch under the same selection "
            "protocol before attributing the contrast to optimization rather than depth."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps(contrasts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
