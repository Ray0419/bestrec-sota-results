#!/usr/bin/env python3
"""Aggregate the frozen ML-1M sparse-support interaction experiment."""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np

from paired_projection_eval import sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.input_glob))]
    if len(paths) != 5:
        raise SystemExit(f"expected five seed artifacts, found {len(paths)}")

    records = []
    for path in paths:
        match = re.search(r"s(\d+)\.json$", path.name)
        if match is None:
            raise SystemExit(f"cannot parse seed from {path}")
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if artifact["split"] != "valid":
            raise SystemExit(f"non-validation artifact supplied: {path}")
        strict = artifact["masks"]["strict_negative_infinity"]
        records.append(
            {
                "seed": int(match.group(1)),
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

    arm_names = records[0]["arms"]
    contrast_names = records[0]["contrasts"]
    aggregate_arms = {
        name: float(np.mean([record["arms"][name] for record in records]))
        for name in arm_names
    }
    aggregate_contrasts = {}
    for name in contrast_names:
        values = np.array(
            [record["contrasts"][name]["delta"] for record in records]
        )
        aggregate_contrasts[name] = {
            "mean": float(values.mean()),
            "positive_seeds": int((values > 0).sum()),
            "negative_seeds": int((values < 0).sum()),
            "bootstrap_lower_bound_positive_seeds": int(
                sum(
                    record["contrasts"][name]["bootstrap_95_ci"][0] > 0
                    for record in records
                )
            ),
        }

    contrast = aggregate_contrasts
    rules = {
        "independent_temporal_pruning": {
            "passed": (
                contrast["T_minus_F"]["mean"] >= 0.002
                and contrast["T_minus_F"]["positive_seeds"] >= 4
            ),
            "threshold": "mean T-F >= 0.002 and >=4/5 positive seeds",
        },
        "consensus_pruning_interaction": {
            "passed": (
                contrast["A_minus_S"]["mean"] >= 0.002
                and contrast["T_minus_F"]["mean"] <= 0.0005
                and contrast["interaction"]["mean"] >= 0.0015
                and contrast["interaction"]["positive_seeds"] >= 4
                and contrast["interaction"][
                    "bootstrap_lower_bound_positive_seeds"
                ] >= 3
            ),
            "threshold": "all five frozen interaction conditions",
        },
        "adaptive_support_value": {
            "passed": (
                contrast["A_minus_R"]["mean"] >= 0.0005
                and contrast["A_minus_R"]["positive_seeds"] >= 4
                and contrast["A_minus_B"]["mean"] >= 0.0005
                and contrast["A_minus_B"]["positive_seeds"] >= 4
            ),
            "threshold": "A-R and A-B means >= 0.0005 and >=4/5 positive",
        },
        "fixed_boundary_law": {
            "passed": (
                contrast["B_minus_S"]["mean"] > 0
                and contrast["B_minus_S"]["positive_seeds"] >= 4
                and contrast["A_minus_B"]["mean"] <= 0.0005
            ),
            "threshold": "B-S > 0, >=4/5 positive, and mean A-B <= 0.0005",
        },
        "old_history_contribution": {
            "passed": (
                contrast["B_minus_R"]["mean"] >= 0.0005
                and contrast["B_minus_R"]["positive_seeds"] >= 4
            ),
            "threshold": "mean B-R >= 0.0005 and >=4/5 positive",
        },
    }

    output = {
        "protocol": "ML1M_SPARSE_SUPPORT_INTERACTION_V1_SUMMARY",
        "preregistration": str(args.preregistration),
        "preregistration_sha256": sha256(args.preregistration),
        "primary_metric": "strict_negative_infinity/NDCG@10",
        "arm_labels": {
            "F": "original full late filter",
            "T": "channel-specific aggregate top-8 late filter",
            "S": "channel-mean late filter",
            "A": "shared adaptive top-8 late filter",
            "R": "shared fixed recent-8 late filter",
            "B": "shared fixed boundary-8 late filter",
        },
        "per_seed": records,
        "aggregate_arms": aggregate_arms,
        "aggregate_contrasts": aggregate_contrasts,
        "frozen_decision_rules": rules,
        "test_accessed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "aggregate_arms": aggregate_arms,
        "aggregate_contrasts": aggregate_contrasts,
        "frozen_decision_rules": rules,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

