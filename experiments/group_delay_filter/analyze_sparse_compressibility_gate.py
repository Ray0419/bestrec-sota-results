#!/usr/bin/env python3
"""Relate frozen K=8 impulse compressibility to ranking deltas."""

from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np


def rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    result = np.empty(len(values), dtype=np.float64)
    result[order] = np.arange(len(values), dtype=np.float64)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ml1m-projection", type=Path, required=True)
    parser.add_argument("--ml1m-evaluation", type=Path, required=True)
    parser.add_argument("--crossdata-projection-glob", required=True)
    parser.add_argument("--crossdata-evaluation", type=Path, required=True)
    parser.add_argument("--exploratory-threshold", type=float, default=0.88)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    ml1m_projection = json.loads(args.ml1m_projection.read_text(encoding="utf-8"))
    ml1m_evaluation = json.loads(args.ml1m_evaluation.read_text(encoding="utf-8"))
    ml1m_delta = {
        record["seed"]: record["contrasts"]["T_minus_F"]["delta"]
        for record in ml1m_evaluation["per_seed"]
    }
    for record in ml1m_projection["checkpoints"]:
        match = re.search(r"_s(\d+)\.pt$", record["checkpoint"])
        if match is None:
            raise SystemExit(f"cannot parse ML-1M seed from {record['checkpoint']}")
        seed = int(match.group(1))
        rows.append(
            {
                "dataset": "ML-1M",
                "seed": seed,
                "retained_energy_k8": record["retained_impulse_energy"],
                "ndcg10_delta": ml1m_delta[seed],
            }
        )

    crossdata_evaluation = json.loads(
        args.crossdata_evaluation.read_text(encoding="utf-8")
    )
    cross_delta = {
        (record["dataset"], record["seed"]): record["contrasts"]["A_minus_F"][
            "delta"
        ]
        for record in crossdata_evaluation["per_seed"]
    }
    for projection_path_string in sorted(glob.glob(args.crossdata_projection_glob)):
        projection_path = Path(projection_path_string)
        match = re.match(
            r"(.+)_sparse_transfer_adaptive_summary\.json$", projection_path.name
        )
        if match is None:
            raise SystemExit(f"cannot parse dataset from {projection_path}")
        dataset = match.group(1)
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        for record in projection["checkpoints"]:
            seed_match = re.search(r"_s(\d+)\.pt$", record["checkpoint"])
            if seed_match is None:
                raise SystemExit(f"cannot parse seed from {record['checkpoint']}")
            seed = int(seed_match.group(1))
            rows.append(
                {
                    "dataset": dataset,
                    "seed": seed,
                    "retained_energy_k8": record["retained_impulse_energy"],
                    "ndcg10_delta": cross_delta[(dataset, seed)],
                }
            )

    if len(rows) != 20:
        raise SystemExit(f"expected 20 checkpoint rows, found {len(rows)}")
    energy = np.array([row["retained_energy_k8"] for row in rows])
    delta = np.array([row["ndcg10_delta"] for row in rows])
    selected = energy >= args.exploratory_threshold
    dataset_summary = {}
    for dataset in sorted({row["dataset"] for row in rows}):
        subset = [row for row in rows if row["dataset"] == dataset]
        dataset_summary[dataset] = {
            "mean_retained_energy_k8": float(
                np.mean([row["retained_energy_k8"] for row in subset])
            ),
            "mean_ndcg10_delta": float(
                np.mean([row["ndcg10_delta"] for row in subset])
            ),
            "positive_seeds": int(sum(row["ndcg10_delta"] > 0 for row in subset)),
        }

    output = {
        "protocol": "EXPLORATORY_K8_COMPRESSIBILITY_GATE_V1",
        "rows": rows,
        "checkpoint_level": {
            "pearson_energy_delta": float(np.corrcoef(energy, delta)[0, 1]),
            "spearman_energy_delta": float(
                np.corrcoef(rank(energy), rank(delta))[0, 1]
            ),
        },
        "dataset_summary": dataset_summary,
        "exploratory_gate": {
            "threshold": args.exploratory_threshold,
            "selected_checkpoints": int(selected.sum()),
            "selected_positive": int(((delta > 0) & selected).sum()),
            "selected_negative": int(((delta < 0) & selected).sum()),
            "abstained_positive": int(((delta > 0) & ~selected).sum()),
            "abstained_negative": int(((delta < 0) & ~selected).sum()),
            "selected_mean_delta": float(delta[selected].mean()),
            "abstained_mean_delta": float(delta[~selected].mean()),
            "retrospective": True,
        },
        "interpretation_limit": (
            "Seeds share datasets; checkpoint-level correlation is descriptive "
            "and the threshold requires prospective dataset validation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="ascii")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

