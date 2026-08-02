#!/usr/bin/env python3
"""Summarize the frozen ML-1M projection mechanism controls."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SEEDS = range(42, 47)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ndcg(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["masks"]["strict_negative_infinity"]["NDCG@10"]


def paired_group(pattern: str) -> dict:
    rows = []
    for seed in SEEDS:
        path = ROOT / pattern.format(seed=seed)
        metric = ndcg(path)
        rows.append({
            "seed": seed,
            "artifact": str(path),
            "artifact_sha256": sha256(path),
            **metric,
        })
    deltas = [row["delta"] for row in rows]
    return {
        "n": len(rows),
        "mean_delta": statistics.mean(deltas),
        "positive_seeds": sum(value > 0 for value in deltas),
        "rows": rows,
    }


def main() -> int:
    alphas = (0.0, 0.25, 0.5, 0.75, 1.0)
    path_rows = []
    for seed in SEEDS:
        endpoint = ndcg(ROOT / f"paired_channel_shared_ml1m_valid_s{seed}.json")
        values = [endpoint["projected"]]
        for tag in ("0p25", "0p5", "0p75"):
            values.append(ndcg(
                ROOT / f"paired_symmetry_path_a{tag}_valid_s{seed}.json"
            )["projected"])
        values.append(endpoint["baseline"])
        best_index = max(range(len(values)), key=values.__getitem__)
        path_rows.append({
            "seed": seed,
            "values": dict(zip((str(value) for value in alphas), values)),
            "best_alpha": alphas[best_index],
            "nonincreasing_in_alpha": all(
                left >= right for left, right in zip(values, values[1:])
            ),
        })
    path_means = [
        statistics.mean(row["values"][str(alpha)] for row in path_rows)
        for alpha in alphas
    ]

    sparse = {}
    shared_endpoints = {
        seed: ndcg(ROOT / f"paired_channel_shared_ml1m_valid_s{seed}.json")
        for seed in SEEDS
    }
    for taps in (8, 16):
        group = paired_group(
            f"paired_sparse_fir_k{taps}_minus_shared_valid_s{{seed}}.json")
        projection = json.loads((
            ROOT / f"ml1m_sparse_fir_k{taps}_projection_summary.json"
        ).read_text(encoding="ascii"))
        retained = [
            row["layers"][-1]["retained_impulse_energy"]
            for row in projection["checkpoints"]
        ]
        versus_full = []
        for row in group["rows"]:
            seed = row["seed"]
            versus_full.append(
                row["projected"] - shared_endpoints[seed]["baseline"]
            )
        group.update({
            "mean_retained_impulse_energy": statistics.mean(retained),
            "retained_impulse_energy_by_seed": retained,
            "delta_versus_full_by_seed": versus_full,
            "mean_delta_versus_full": statistics.mean(versus_full),
            "positive_versus_full_seeds": sum(value > 0 for value in versus_full),
        })
        sparse[str(taps)] = group

    preregistrations = {}
    for name, filename in {
        "path": "PREREG_ML1M_SYMMETRY_PATH_V1.md",
        "norm": "PREREG_ML1M_CHANNEL_SHARING_NORM_CONTROL_V1.md",
        "power": "PREREG_ML1M_POWER_PRESERVING_CONSENSUS_V1.md",
        "sparse_fir": "PREREG_ML1M_SPARSE_FIR_COMPILER_V1.md",
    }.items():
        path = ROOT / filename
        preregistrations[name] = {"path": str(path), "sha256": sha256(path)}

    cpu = ndcg(ROOT / "paired_symmetry_path_a0p25_valid_s42.json")
    mps = ndcg(ROOT / "paired_symmetry_path_a0p25_valid_s42_mps_check.json")
    artifact = {
        "protocol": "ML1M_PROJECTION_MECHANISM_CONTROLS_SUMMARY_V1",
        "split": "validation",
        "test_access": "none",
        "preregistrations": preregistrations,
        "device_parity": {
            "cpu_metric": cpu,
            "mps_metric": mps,
            "exact_equal": cpu == mps,
        },
        "channel_deviation_path": {
            "alphas": alphas,
            "rows": path_rows,
            "mean_values": dict(zip((str(value) for value in alphas), path_means)),
            "mean_nonincreasing_in_alpha": all(
                left >= right for left, right in zip(path_means, path_means[1:])
            ),
            "best_at_alpha_at_most_0p25_seeds": sum(
                row["best_alpha"] <= 0.25 for row in path_rows
            ),
        },
        "shared_minus_norm_matched_scale": paired_group(
            "paired_norm_control_shared_minus_scale_valid_s{seed}.json"
        ),
        "power_consensus_minus_full": paired_group(
            "paired_power_consensus_minus_full_valid_s{seed}.json"
        ),
        "sparse_fir_minus_shared": sparse,
    }
    output = ROOT / "ml1m_projection_controls_summary.json"
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "output": str(output),
        "path_means": artifact["channel_deviation_path"]["mean_values"],
        "norm_mean_delta": artifact["shared_minus_norm_matched_scale"]["mean_delta"],
        "power_mean_delta": artifact["power_consensus_minus_full"]["mean_delta"],
        "sparse_k8_mean_delta_vs_shared": sparse["8"]["mean_delta"],
        "sparse_k8_mean_delta_vs_full": sparse["8"]["mean_delta_versus_full"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
