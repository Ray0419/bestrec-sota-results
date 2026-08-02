#!/usr/bin/env python3
"""Aggregate the frozen three-dataset sparse-support transfer panel."""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np

from paired_projection_eval import sha256


def aggregate(records: list[dict], contrast: str) -> dict:
    values = np.array([record["contrasts"][contrast]["delta"] for record in records])
    return {
        "mean": float(values.mean()),
        "positive_seeds": int((values > 0).sum()),
        "negative_seeds": int((values < 0).sum()),
        "bootstrap_lower_bound_positive_seeds": int(
            sum(
                record["contrasts"][contrast]["bootstrap_95_ci"][0] > 0
                for record in records
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.input_glob))]
    if len(paths) != 15:
        raise SystemExit(f"expected 15 artifacts, found {len(paths)}")

    records = []
    pattern = re.compile(r"crossdata_sparse_support_(.+)_valid_s(\d+)\.json$")
    for path in paths:
        match = pattern.match(path.name)
        if match is None:
            raise SystemExit(f"cannot parse dataset and seed from {path}")
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if artifact["split"] != "valid":
            raise SystemExit(f"non-validation artifact supplied: {path}")
        strict = artifact["masks"]["strict_negative_infinity"]
        records.append(
            {
                "dataset": match.group(1),
                "seed": int(match.group(2)),
                "artifact": str(path),
                "artifact_sha256": sha256(path),
                "arms": strict["arms"]["NDCG@10"],
                "contrasts": {
                    name: {
                        "delta": values["delta"],
                        "bootstrap_95_ci": values["bootstrap_95_ci"],
                    }
                    for name, values in strict["contrasts"]["NDCG@10"].items()
                },
            }
        )

    dataset_names = sorted({record["dataset"] for record in records})
    contrast_names = records[0]["contrasts"]
    arm_names = records[0]["arms"]
    datasets = {}
    for dataset in dataset_names:
        subset = [record for record in records if record["dataset"] == dataset]
        if len(subset) != 5:
            raise SystemExit(f"expected five seeds for {dataset}, found {len(subset)}")
        datasets[dataset] = {
            "arms": {
                arm: float(np.mean([record["arms"][arm] for record in subset]))
                for arm in arm_names
            },
            "contrasts": {
                contrast: aggregate(subset, contrast)
                for contrast in contrast_names
            },
        }

    macro = {}
    for contrast in contrast_names:
        dataset_means = {
            dataset: datasets[dataset]["contrasts"][contrast]["mean"]
            for dataset in dataset_names
        }
        macro[contrast] = {
            "mean": float(np.mean(list(dataset_means.values()))),
            "positive_datasets": int(sum(value > 0 for value in dataset_means.values())),
            "negative_datasets": int(sum(value < 0 for value in dataset_means.values())),
            "positive_seeds": int(
                sum(
                    datasets[dataset]["contrasts"][contrast]["positive_seeds"]
                    for dataset in dataset_names
                )
            ),
            "negative_seeds": int(
                sum(
                    datasets[dataset]["contrasts"][contrast]["negative_seeds"]
                    for dataset in dataset_names
                )
            ),
            "dataset_means": dataset_means,
        }

    adaptive = macro["A_minus_F"]
    boundary = macro["B_minus_F"]
    boundary_recent = macro["B_minus_R"]
    adaptive_transfer = (
        adaptive["positive_datasets"] >= 2
        and adaptive["mean"] >= 0.001
        and adaptive["positive_seeds"] >= 10
    )
    strong_adaptive = (
        adaptive["positive_datasets"] == 3
        and all(
            datasets[dataset]["contrasts"]["A_minus_F"]["positive_seeds"] >= 4
            for dataset in dataset_names
        )
        and sum(value >= 0.002 for value in adaptive["dataset_means"].values()) >= 2
    )
    boundary_transfer = (
        boundary["positive_datasets"] >= 2
        and boundary["mean"] >= 0.001
        and boundary["positive_seeds"] >= 10
        and macro["A_minus_B"]["mean"] <= 0.0005
    )
    boundary_value = (
        boundary_recent["positive_datasets"] >= 2
        and boundary_recent["mean"] >= 0.0005
        and boundary_recent["positive_seeds"] >= 10
    )
    material_failures = {}
    for arm, contrast in (("A", "A_minus_F"), ("B", "B_minus_F"), ("R", "R_minus_F")):
        material_failures[arm] = [
            dataset
            for dataset in dataset_names
            if datasets[dataset]["contrasts"][contrast]["mean"] <= -0.002
            and datasets[dataset]["contrasts"][contrast]["negative_seeds"] >= 4
        ]

    output = {
        "protocol": "CROSSDATA_SPARSE_SUPPORT_TRANSFER_V1_SUMMARY",
        "preregistration": str(args.preregistration),
        "preregistration_sha256": sha256(args.preregistration),
        "primary_metric": "strict_negative_infinity/NDCG@10",
        "per_seed": records,
        "datasets": datasets,
        "macro_contrasts": macro,
        "frozen_decision_rules": {
            "adaptive_transfer": {"passed": adaptive_transfer},
            "strong_adaptive_transfer": {"passed": strong_adaptive},
            "fixed_boundary_transfer": {"passed": boundary_transfer},
            "boundary_position_value": {"passed": boundary_value},
            "material_dataset_failures": material_failures,
        },
        "test_accessed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "datasets": datasets,
        "macro_contrasts": macro,
        "frozen_decision_rules": output["frozen_decision_rules"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

