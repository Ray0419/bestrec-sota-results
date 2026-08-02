#!/usr/bin/env python3
"""Project a collapsed final temporal filter onto one shared channel response."""

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
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_matrix(weight: torch.Tensor, spectral: bool) -> torch.Tensor:
    if spectral:
        matrix = torch.view_as_complex(weight.squeeze(0).contiguous()).to(
            torch.complex128
        )
        matrix = matrix.clone()
        matrix[0] = matrix[0].real
        matrix[-1] = matrix[-1].real
        return matrix
    if weight.ndim != 3 or weight.shape[1] != 1:
        raise ValueError(f"expected depthwise FIR weight, got {weight.shape}")
    return weight[:, 0, :].T.to(torch.float64)


def as_weight(
    matrix: torch.Tensor, reference: torch.Tensor, spectral: bool
) -> torch.Tensor:
    if spectral:
        return torch.view_as_real(matrix.to(torch.complex64)).unsqueeze(0).to(
            reference.dtype
        )
    return matrix.T.unsqueeze(1).to(reference.dtype)


def matrix_stats(matrix: torch.Tensor) -> dict[str, float]:
    _, singular_values, vh = torch.linalg.svd(matrix, full_matrices=False)
    energy = singular_values.square()
    rank1_energy = float(energy[0] / energy.sum())
    uniform = torch.ones_like(vh[0]) / matrix.shape[1] ** 0.5
    channel_consensus = float(torch.abs(torch.sum(vh[0].conj() * uniform)))
    shared = matrix.mean(dim=1, keepdim=True).expand_as(matrix)
    shared_energy = float(shared.abs().square().sum() / matrix.abs().square().sum())
    return {
        "rank1_retained_energy": rank1_energy,
        "dominant_channel_uniform_cosine": channel_consensus,
        "channel_shared_retained_energy": shared_energy,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-glob", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--rank1-energy-threshold", type=float, default=0.905)
    parser.add_argument("--channel-consensus-threshold", type=float, default=0.97)
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.checkpoint_glob))]
    if not paths:
        raise SystemExit(f"no checkpoints match {args.checkpoint_glob!r}")
    if not 0 < args.rank1_energy_threshold <= 1:
        raise SystemExit("--rank1-energy-threshold must lie in (0, 1]")
    if not 0 < args.channel_consensus_threshold <= 1:
        raise SystemExit("--channel-consensus-threshold must lie in (0, 1]")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for path in paths:
        state = torch.load(path, map_location="cpu", weights_only=False)
        projected = {key: value.clone() for key, value in state.items()}
        filter_keys = sorted(
            key
            for key in state
            if key.endswith("layer.complex_weight")
            or key.endswith("layer.causal_conv.weight")
        )
        if not filter_keys:
            raise SystemExit(f"no supported temporal filter in {path}")

        layer_records = []
        for index, key in enumerate(filter_keys):
            spectral = key.endswith("layer.complex_weight")
            matrix = canonical_matrix(state[key], spectral)
            stats = matrix_stats(matrix)
            final_layer = index == len(filter_keys) - 1
            selected = (
                final_layer
                and stats["rank1_retained_energy"] >= args.rank1_energy_threshold
                and stats["dominant_channel_uniform_cosine"]
                >= args.channel_consensus_threshold
            )
            if selected:
                shared = matrix.mean(dim=1, keepdim=True).expand_as(matrix).clone()
                if spectral:
                    shared[0] = shared[0].real
                    shared[-1] = shared[-1].real
                projected[key] = as_weight(shared, state[key], spectral)
            layer_records.append(
                {
                    "key": key,
                    "representation": "complex_spectral" if spectral else "real_fir",
                    "shape": list(matrix.shape),
                    "final_layer": final_layer,
                    "selected": selected,
                    **stats,
                }
            )

        output = args.output_dir / f"{path.stem}.channel_shared_projected.pt"
        torch.save(projected, output)
        records.append(
            {
                "checkpoint": str(path),
                "checkpoint_sha256": sha256(path),
                "projected": str(output),
                "projected_sha256": sha256(output),
                "layers": layer_records,
            }
        )
        selected_keys = [row["key"] for row in layer_records if row["selected"]]
        print(f"{path.name}: {selected_keys or 'abstain'}")

    artifact = {
        "protocol": "DEPTH_GATED_CHANNEL_SHARED_PROJECTION_EXPLORATORY_V1",
        "rank1_energy_threshold": args.rank1_energy_threshold,
        "channel_consensus_threshold": args.channel_consensus_threshold,
        "projection": "orthogonal projection onto equal temporal response across channels",
        "checkpoints": records,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
