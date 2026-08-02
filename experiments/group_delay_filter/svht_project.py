#!/usr/bin/env python3
"""Project only the final temporal filter using label-free optimal SVHT rank."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path

import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_filter(value: torch.Tensor) -> torch.Tensor:
    matrix = torch.view_as_complex(value.squeeze(0).contiguous()).to(torch.complex128)
    matrix = matrix.clone()
    matrix[0] = matrix[0].real
    matrix[-1] = matrix[-1].real
    return matrix


def as_weight(matrix: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    return torch.view_as_real(matrix.to(torch.complex64)).unsqueeze(0).to(reference.dtype)


def svht_rank(singular_values: torch.Tensor, rows: int, columns: int) -> tuple[int, float]:
    """Unknown-noise optimal hard threshold using the published cubic approximation."""
    beta = min(rows, columns) / max(rows, columns)
    omega = 0.56 * beta ** 3 - 0.95 * beta ** 2 + 1.82 * beta + 1.43
    threshold = omega * float(torch.median(singular_values))
    rank = int((singular_values > threshold).sum())
    return max(rank, 1), threshold


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-glob", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.checkpoint_glob))]
    if not paths:
        raise SystemExit(f"no checkpoints match {args.checkpoint_glob!r}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for path in paths:
        state = torch.load(path, map_location="cpu", weights_only=False)
        keys = sorted(key for key in state if key.endswith("layer.complex_weight"))
        if not keys:
            raise SystemExit(f"no complex temporal filters in {path}")
        key = keys[-1]
        matrix = canonical_filter(state[key])
        u, singular_values, vh = torch.linalg.svd(matrix, full_matrices=False)
        rank, threshold = svht_rank(singular_values, *matrix.shape)
        estimate = (u[:, :rank] * singular_values[:rank]) @ vh[:rank]
        projected = {name: value.clone() for name, value in state.items()}
        projected[key] = as_weight(estimate, state[key])
        output = args.output_dir / f"{path.stem}.late_svht_rank{rank}.pt"
        torch.save(projected, output)
        retained = float(
            singular_values[:rank].square().sum() / singular_values.square().sum())
        records.append({
            "checkpoint": str(path),
            "checkpoint_sha256": sha256(path),
            "projected": str(output),
            "projected_sha256": sha256(output),
            "selected_parameter": key,
            "matrix_shape": list(matrix.shape),
            "selected_rank": rank,
            "threshold": threshold,
            "threshold_over_leading_singular_value": threshold / float(singular_values[0]),
            "retained_energy": retained,
            "singular_values": singular_values.tolist(),
        })

    artifact = {
        "protocol": "LATE_FILTER_SVHT_FEASIBILITY_V1",
        "label_access": "none",
        "selection": "final complex temporal filter only",
        "rank_rule": (
            "Gavish-Donoho unknown-noise optimal hard threshold; "
            "omega(beta)=0.56 beta^3-0.95 beta^2+1.82 beta+1.43 times median singular value"
        ),
        "checkpoints": records,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps([
        {"checkpoint": Path(row["checkpoint"]).name, "rank": row["selected_rank"]}
        for row in records
    ], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
