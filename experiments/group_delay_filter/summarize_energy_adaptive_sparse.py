#!/usr/bin/env python3
"""Aggregate the frozen E90/E95 sparse FIR feasibility panel."""

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
    parser.add_argument("--evaluation-glob", required=True)
    parser.add_argument("--projection-glob", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    k_lookup = {}
    projection_pattern = re.compile(
        r"(.+)_energy_adaptive_e(0p90|0p95)_summary\.json$"
    )
    for path_string in sorted(glob.glob(args.projection_glob)):
        path = Path(path_string)
        match = projection_pattern.match(path.name)
        if match is None:
            raise SystemExit(f"cannot parse projection artifact {path}")
        dataset, rho_tag = match.groups()
        arm = "E90" if rho_tag == "0p90" else "E95"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        for record in artifact["checkpoints"]:
            seed_match = re.search(r"_s(\d+)\.pt$", record["checkpoint"])
            if seed_match is None:
                raise SystemExit(f"cannot parse seed from {record['checkpoint']}")
            k_lookup[(dataset, int(seed_match.group(1)), arm)] = record[
                "retained_taps"
            ]

    paths = [Path(path) for path in sorted(glob.glob(args.evaluation_glob))]
    if len(paths) != 20:
        raise SystemExit(f"expected 20 evaluation artifacts, found {len(paths)}")
    pattern = re.compile(r"energy_adaptive_(.+)_valid_s(\d+)\.json$")
    records = []
    for path in paths:
        match = pattern.match(path.name)
        if match is None:
            raise SystemExit(f"cannot parse evaluation artifact {path}")
        dataset, seed_string = match.groups()
        seed = int(seed_string)
        artifact = json.loads(path.read_text(encoding="utf-8"))
        strict = artifact["masks"]["strict_negative_infinity"]
        records.append(
            {
                "dataset": dataset,
                "seed": seed,
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
                "retained_taps": {
                    arm: k_lookup[(dataset, seed, arm)]
                    for arm in ("E90", "E95")
                },
            }
        )

    datasets = {}
    for dataset in sorted({record["dataset"] for record in records}):
        subset = [record for record in records if record["dataset"] == dataset]
        datasets[dataset] = {}
        for arm in ("E90", "E95"):
            contrast = f"{arm}_minus_F"
            values = np.array(
                [record["contrasts"][contrast]["delta"] for record in subset]
            )
            taps = np.array([record["retained_taps"][arm] for record in subset])
            datasets[dataset][arm] = {
                "mean_delta": float(values.mean()),
                "positive_seeds": int((values > 0).sum()),
                "negative_seeds": int((values < 0).sum()),
                "mean_taps": float(taps.mean()),
                "max_taps": int(taps.max()),
            }

    panel = {}
    for arm in ("E90", "E95"):
        contrast = f"{arm}_minus_F"
        deltas = np.array(
            [record["contrasts"][contrast]["delta"] for record in records]
        )
        taps = np.array([record["retained_taps"][arm] for record in records])
        lower_bounds = np.array(
            [record["contrasts"][contrast]["bootstrap_95_ci"][0] for record in records]
        )
        dataset_means = {
            dataset: datasets[dataset][arm]["mean_delta"] for dataset in datasets
        }
        panel[arm] = {
            "macro_delta": float(np.mean(list(dataset_means.values()))),
            "dataset_mean_deltas": dataset_means,
            "seed_point_delta_le_minus_0p002": int((deltas <= -0.002).sum()),
            "bootstrap_lower_bound_gt_minus_0p001": int(
                (lower_bounds > -0.001).sum()
            ),
            "mean_taps": float(taps.mean()),
            "max_taps": int(taps.max()),
        }

    rules = {}
    for arm in ("E90", "E95"):
        row = panel[arm]
        safe = (
            min(row["dataset_mean_deltas"].values()) >= -0.0005
            and row["macro_delta"] >= -0.0002
            and row["seed_point_delta_le_minus_0p002"] == 0
            and row["bootstrap_lower_bound_gt_minus_0p001"] >= 16
        )
        sparse = (
            row["mean_taps"] <= (20 if arm == "E90" else 25)
            and row["max_taps"] <= (25 if arm == "E90" else 32)
        )
        ml1m = datasets["ML-1M"][arm]
        effect = (
            ml1m["mean_delta"] >= (0.002 if arm == "E90" else 0.0)
            and ml1m["positive_seeds"] >= (4 if arm == "E90" else 3)
        )
        rules[arm] = {
            "panel_safe": safe,
            "usefully_sparse": sparse,
            "ml1m_effect_retained": effect,
            "selected": safe and sparse and effect,
        }

    output = {
        "protocol": "ENERGY_ADAPTIVE_SPARSE_FIR_V1_SUMMARY",
        "preregistration": str(args.preregistration),
        "preregistration_sha256": sha256(args.preregistration),
        "primary_metric": "strict_negative_infinity/NDCG@10",
        "per_seed": records,
        "datasets": datasets,
        "panel": panel,
        "frozen_decision_rules": rules,
        "selected_arm": next(
            (arm for arm in ("E90", "E95") if rules[arm]["selected"]), None
        ),
        "test_accessed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "datasets": datasets,
        "panel": panel,
        "frozen_decision_rules": rules,
        "selected_arm": output["selected_arm"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

