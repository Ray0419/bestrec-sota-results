#!/usr/bin/env python3
"""Measure item-embedding spectral concentration without accessing labels."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path

import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def spectrum(matrix: torch.Tensor) -> dict[str, float | int]:
    singular_values = torch.linalg.svdvals(matrix.to(torch.float64))
    squared = singular_values.square()
    probabilities = squared / squared.sum().clamp_min(1e-30)
    positive = probabilities[probabilities > 0]
    top_energy = float(probabilities[0])
    return {
        "rows": matrix.shape[0],
        "dimensions": matrix.shape[1],
        "top_singular_energy": top_energy,
        "stable_rank": 1.0 / top_energy,
        "entropy_effective_rank": float(
            torch.exp(-(positive * positive.log()).sum())
        ),
        "participation_ratio": float(1.0 / probabilities.square().sum()),
    }


def summarize(records: list[dict]) -> dict[str, dict[str, float]]:
    views = ("raw", "centered", "row_normalized", "row_normalized_centered")
    metrics = (
        "top_singular_energy",
        "stable_rank",
        "entropy_effective_rank",
        "participation_ratio",
    )
    result = {}
    for view in views:
        result[view] = {}
        for metric in metrics:
            values = [record["spectra"][view][metric] for record in records]
            mean = sum(values) / len(values)
            result[view][metric] = {
                "mean": mean,
                "population_std": math.sqrt(
                    sum((value - mean) ** 2 for value in values) / len(values)
                ),
                "min": min(values),
                "max": max(values),
            }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-glob", action="append", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = sorted(
        {
            Path(match)
            for pattern in args.checkpoint_glob
            for match in glob.glob(pattern)
        }
    )
    if not paths:
        raise SystemExit("checkpoint glob matched no files")

    records = []
    for path in paths:
        state = torch.load(path, map_location="cpu", weights_only=True)
        keys = [key for key in state if key.endswith("item_embeddings.weight")]
        if len(keys) != 1:
            raise SystemExit(f"expected one item embedding in {path}, found {keys}")
        embedding = state[keys[0]][1:].detach().to(torch.float64)
        if embedding.ndim != 2 or embedding.shape[0] < 2:
            raise SystemExit(f"invalid item embedding shape in {path}: {embedding.shape}")
        centered = embedding - embedding.mean(dim=0, keepdim=True)
        normalized = embedding / torch.linalg.vector_norm(
            embedding, dim=1, keepdim=True
        ).clamp_min(1e-15)
        normalized_centered = normalized - normalized.mean(dim=0, keepdim=True)
        records.append(
            {
                "checkpoint": str(path.resolve()),
                "checkpoint_sha256": sha256(path),
                "embedding_key": keys[0],
                "padding_row_excluded": True,
                "spectra": {
                    "raw": spectrum(embedding),
                    "centered": spectrum(centered),
                    "row_normalized": spectrum(normalized),
                    "row_normalized_centered": spectrum(normalized_centered),
                },
            }
        )

    artifact = {
        "protocol": "ITEM_EMBEDDING_SPECTRAL_CONCENTRATION_V1",
        "label": args.label,
        "label_access": "none",
        "checkpoint_count": len(records),
        "records": records,
        "aggregate": summarize(records),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(
        json.dumps(
            {
                "label": args.label,
                "checkpoint_count": len(records),
                "raw": artifact["aggregate"]["raw"],
                "centered": artifact["aggregate"]["centered"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
