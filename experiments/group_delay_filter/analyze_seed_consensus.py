#!/usr/bin/env python3
"""Measure cross-seed consensus of dominant temporal-filter components."""

from __future__ import annotations

import argparse
import glob
import itertools
import json
from pathlib import Path

import torch


def canonical_matrix(weight: torch.Tensor, spectral: bool) -> torch.Tensor:
    if spectral:
        matrix = torch.view_as_complex(weight.squeeze(0).contiguous()).to(
            torch.complex128
        )
        matrix = matrix.clone()
        matrix[0] = matrix[0].real
        matrix[-1] = matrix[-1].real
        return matrix
    return weight[:, 0, :].T.to(torch.float64)


def cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    numerator = torch.abs(torch.sum(left.conj() * right))
    denominator = torch.linalg.vector_norm(left) * torch.linalg.vector_norm(right)
    return float(numerator / denominator.clamp_min(1e-15))


def distribution(values: list[float]) -> dict[str, float]:
    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-glob", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.checkpoint_glob))]
    if len(paths) < 2:
        raise SystemExit("seed-consensus analysis requires at least two checkpoints")

    layers: dict[str, list[dict]] = {}
    for path in paths:
        state = torch.load(path, map_location="cpu", weights_only=True)
        keys = sorted(
            key
            for key in state
            if key.endswith("layer.complex_weight")
            or key.endswith("layer.causal_conv.weight")
            or key.endswith("fir_conv.weight")
        )
        if not keys:
            raise SystemExit(f"no supported temporal filter in {path}")
        for index, key in enumerate(keys):
            spectral = key.endswith("layer.complex_weight")
            matrix = canonical_matrix(state[key], spectral)
            u, singular_values, vh = torch.linalg.svd(matrix, full_matrices=False)
            rank1 = (u[:, :1] * singular_values[:1]) @ vh[:1]
            tail = matrix - rank1
            uniform = torch.ones_like(vh[0]) / matrix.shape[1] ** 0.5
            layers.setdefault(str(index), []).append(
                {
                    "checkpoint": str(path),
                    "representation": "complex_spectral" if spectral else "real_fir",
                    "rank1": rank1,
                    "tail": tail,
                    "frequency_vector": u[:, 0],
                    "channel_vector": vh[0],
                    "rank1_retained_energy": float(
                        singular_values[0].square() / singular_values.square().sum()
                    ),
                    "dominant_channel_uniform_cosine": cosine(vh[0], uniform),
                }
            )

    layer_records = []
    for layer_index, rows in sorted(layers.items(), key=lambda item: int(item[0])):
        pairs = list(itertools.combinations(rows, 2))
        layer_records.append(
            {
                "layer_index": int(layer_index),
                "representation": rows[0]["representation"],
                "per_checkpoint": [
                    {
                        "checkpoint": row["checkpoint"],
                        "rank1_retained_energy": row["rank1_retained_energy"],
                        "dominant_channel_uniform_cosine": row[
                            "dominant_channel_uniform_cosine"
                        ],
                    }
                    for row in rows
                ],
                "pairwise_consensus": {
                    "rank1_matrix_cosine": distribution(
                        [cosine(left["rank1"], right["rank1"]) for left, right in pairs]
                    ),
                    "dominant_frequency_cosine": distribution(
                        [
                            cosine(
                                left["frequency_vector"], right["frequency_vector"]
                            )
                            for left, right in pairs
                        ]
                    ),
                    "dominant_channel_cosine": distribution(
                        [
                            cosine(left["channel_vector"], right["channel_vector"])
                            for left, right in pairs
                        ]
                    ),
                    "tail_matrix_cosine": distribution(
                        [cosine(left["tail"], right["tail"]) for left, right in pairs]
                    ),
                },
            }
        )

    artifact = {
        "protocol": "TEMPORAL_FILTER_SEED_CONSENSUS_V1",
        "label": args.label,
        "checkpoint_count": len(paths),
        "phase_invariant_similarity": "absolute normalized Frobenius inner product",
        "layers": layer_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "label": args.label,
        "late_layer": layer_records[-1]["pairwise_consensus"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
