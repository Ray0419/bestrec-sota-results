#!/usr/bin/env python3
"""Compile frozen sparse-support controls for a final spectral filter."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import torch

from project_channel_shared import as_weight, canonical_matrix, sha256


def support_indices(
    impulse: torch.Tensor,
    mode: str,
    taps: int,
    oldest_taps: int,
    retained_energy: float | None,
) -> torch.Tensor:
    sequence_length = impulse.shape[0]
    if mode != "energy_threshold" and taps > sequence_length:
        raise ValueError(f"{taps} taps exceed sequence length {sequence_length}")
    if mode in ("aggregate_topk", "energy_threshold"):
        energy = impulse.square().sum(dim=1)
        ordered = torch.argsort(energy, descending=True, stable=True)
        if mode == "aggregate_topk":
            return ordered[:taps]
        if retained_energy is None:
            raise ValueError("energy_threshold requires retained_energy")
        cumulative = torch.cumsum(energy[ordered], dim=0)
        target = retained_energy * energy.sum()
        count = int(torch.searchsorted(cumulative, target, right=False)) + 1
        return ordered[:count]
    if mode == "fixed_recent":
        return torch.arange(taps)
    if oldest_taps < 1 or oldest_taps >= taps:
        raise ValueError("oldest_taps must lie in [1, taps)")
    recent_taps = taps - oldest_taps
    return torch.cat(
        (
            torch.arange(recent_taps),
            torch.arange(sequence_length - oldest_taps, sequence_length),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-glob", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "aggregate_topk",
            "energy_threshold",
            "fixed_recent",
            "fixed_boundary",
        ),
        required=True,
    )
    parser.add_argument("--taps", type=int, default=8)
    parser.add_argument("--oldest-taps", type=int, default=2)
    parser.add_argument("--shared-tolerance", type=float, default=1e-7)
    parser.add_argument(
        "--retained-energy",
        type=float,
        help="minimum impulse energy retained by energy_threshold",
    )
    parser.add_argument(
        "--allow-channel-specific-fixed",
        action="store_true",
        help="allow fixed support modes to preserve channel-specific values",
    )
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.checkpoint_glob))]
    if not paths:
        raise SystemExit(f"no checkpoints match {args.checkpoint_glob!r}")
    if args.taps < 1:
        raise SystemExit("--taps must be positive")
    if args.shared_tolerance < 0:
        raise SystemExit("--shared-tolerance must be nonnegative")
    if args.mode == "energy_threshold":
        if args.retained_energy is None or not 0 < args.retained_energy <= 1:
            raise SystemExit(
                "energy_threshold requires --retained-energy in (0, 1]"
            )
    elif args.retained_energy is not None:
        raise SystemExit("--retained-energy is only defined for energy_threshold")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for path in paths:
        state = torch.load(path, map_location="cpu", weights_only=False)
        projected = {key: value.clone() for key, value in state.items()}
        filter_keys = sorted(
            key for key in state if key.endswith("layer.complex_weight")
        )
        if not filter_keys:
            raise SystemExit(f"no spectral temporal filter in {path}")
        key = filter_keys[-1]
        matrix = canonical_matrix(state[key], spectral=True)
        sequence_length = 2 * (matrix.shape[0] - 1)
        channel_mean = matrix.mean(dim=1, keepdim=True)
        max_channel_deviation = float((matrix - channel_mean).abs().max())
        if (
            args.mode in ("fixed_recent", "fixed_boundary")
            and not args.allow_channel_specific_fixed
            and max_channel_deviation > args.shared_tolerance
        ):
            raise SystemExit(
                f"{path} is not channel-shared: max deviation "
                f"{max_channel_deviation:.3g} > {args.shared_tolerance:.3g}"
            )

        impulse = torch.fft.irfft(matrix, n=sequence_length, dim=0)
        try:
            indices = support_indices(
                impulse,
                args.mode,
                args.taps,
                args.oldest_taps,
                args.retained_energy,
            )
        except ValueError as error:
            raise SystemExit(str(error)) from error
        keep = torch.zeros(sequence_length, dtype=torch.bool)
        keep[indices] = True
        sparse_impulse = torch.zeros_like(impulse)
        sparse_impulse[keep] = impulse[keep]
        replacement = torch.fft.rfft(sparse_impulse, n=sequence_length, dim=0)
        replacement[0] = replacement[0].real
        replacement[-1] = replacement[-1].real
        projected[key] = as_weight(replacement, state[key], spectral=True)

        stored = canonical_matrix(projected[key], spectral=True)
        stored_impulse = torch.fft.irfft(stored, n=sequence_length, dim=0)
        excluded_residual = (
            float(stored_impulse[~keep].abs().max()) if (~keep).any() else 0.0
        )
        support_tag = (
            f"energy{args.retained_energy:g}".replace(".", "p")
            if args.mode == "energy_threshold"
            else f"{args.mode}_k{args.taps}"
        )
        output = args.output_dir / f"{path.stem}.{support_tag}.pt"
        torch.save(projected, output)
        records.append(
            {
                "checkpoint": str(path),
                "checkpoint_sha256": sha256(path),
                "projected": str(output),
                "projected_sha256": sha256(output),
                "filter_key": key,
                "filter_count": len(filter_keys),
                "sequence_length": sequence_length,
                "channels": matrix.shape[1],
                "retained_taps": int(len(indices)),
                "max_input_channel_deviation": max_channel_deviation,
                "retained_tap_indices": sorted(int(value) for value in indices),
                "retained_impulse_energy": float(
                    sparse_impulse.square().sum() / impulse.square().sum()
                ),
                "storage_quantization_max_abs_error": float(
                    (stored - replacement).abs().max()
                ),
                "excluded_tap_max_abs_after_storage": excluded_residual,
            }
        )
        print(
            f"{path.name}: {sorted(int(value) for value in indices)} "
            f"energy={records[-1]['retained_impulse_energy']:.6f}"
        )

    artifact = {
        "protocol": "ML1M_SPARSE_SUPPORT_INTERACTION_V1",
        "mode": args.mode,
        "taps": args.taps,
        "oldest_taps": args.oldest_taps,
        "retained_energy_threshold": args.retained_energy,
        "shared_tolerance": args.shared_tolerance,
        "allow_channel_specific_fixed": args.allow_channel_specific_fixed,
        "checkpoints": records,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
