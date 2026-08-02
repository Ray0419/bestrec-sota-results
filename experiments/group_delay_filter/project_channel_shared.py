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
    parser.add_argument(
        "--deviation-scale",
        type=float,
        default=0.0,
        help="retain this fraction of the channel-specific deviation from the mean",
    )
    parser.add_argument(
        "--intervention",
        choices=(
            "shared_path",
            "norm_matched_scale",
            "power_preserving_consensus",
            "sparse_fir",
        ),
        default="shared_path",
    )
    parser.add_argument(
        "--sparse-taps",
        type=int,
        help="number of largest impulse-response taps retained by sparse_fir",
    )
    args = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(args.checkpoint_glob))]
    if not paths:
        raise SystemExit(f"no checkpoints match {args.checkpoint_glob!r}")
    if not 0 < args.rank1_energy_threshold <= 1:
        raise SystemExit("--rank1-energy-threshold must lie in (0, 1]")
    if not 0 < args.channel_consensus_threshold <= 1:
        raise SystemExit("--channel-consensus-threshold must lie in (0, 1]")
    if not 0 <= args.deviation_scale <= 1:
        raise SystemExit("--deviation-scale must lie in [0, 1]")
    if args.intervention != "shared_path" and args.deviation_scale != 0:
        raise SystemExit(
            "--deviation-scale is only defined for --intervention shared_path"
        )
    if args.intervention == "sparse_fir":
        if args.sparse_taps is None or args.sparse_taps < 1:
            raise SystemExit("--intervention sparse_fir requires --sparse-taps >= 1")
    elif args.sparse_taps is not None:
        raise SystemExit("--sparse-taps is only defined for sparse_fir")

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
            or key.endswith("fir_conv.weight")
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
            intervention_stats = {}
            if selected:
                shared = matrix.mean(dim=1, keepdim=True).expand_as(matrix)
                if args.intervention == "shared_path":
                    replacement = (
                        shared + args.deviation_scale * (matrix - shared)
                    ).clone()
                elif args.intervention == "norm_matched_scale":
                    replacement = (
                        matrix * (torch.linalg.norm(shared) / torch.linalg.norm(matrix))
                    ).clone()
                elif args.intervention == "power_preserving_consensus":
                    mean = matrix.mean(dim=1, keepdim=True)
                    rms = matrix.abs().square().mean(dim=1, keepdim=True).sqrt()
                    unit = torch.where(
                        mean.abs() > torch.finfo(torch.float64).eps,
                        mean / mean.abs().clamp_min(torch.finfo(torch.float64).eps),
                        torch.ones_like(mean),
                    )
                    replacement = (rms * unit).expand_as(matrix).clone()
                else:
                    if not spectral:
                        raise SystemExit("sparse_fir requires a complex spectral filter")
                    sequence_length = 2 * (matrix.shape[0] - 1)
                    if args.sparse_taps > sequence_length:
                        raise SystemExit(
                            f"--sparse-taps {args.sparse_taps} exceeds "
                            f"sequence length {sequence_length}"
                        )
                    spectrum = matrix.mean(dim=1)
                    impulse = torch.fft.irfft(spectrum, n=sequence_length)
                    ordered = torch.argsort(
                        impulse.abs(), descending=True, stable=True
                    )
                    retained_indices = ordered[:args.sparse_taps]
                    sparse_impulse = torch.zeros_like(impulse)
                    sparse_impulse[retained_indices] = impulse[retained_indices]
                    compiled = torch.fft.rfft(sparse_impulse, n=sequence_length)
                    replacement = compiled[:, None].expand_as(matrix).clone()
                    intervention_stats = {
                        "sequence_length": sequence_length,
                        "sparse_taps": args.sparse_taps,
                        "retained_tap_indices": sorted(
                            int(value) for value in retained_indices
                        ),
                        "retained_impulse_energy": float(
                            sparse_impulse.square().sum() / impulse.square().sum()
                        ),
                        "rfft_reconstruction_max_abs_error": float(
                            (torch.fft.rfft(sparse_impulse, n=sequence_length)
                             - compiled).abs().max()
                        ),
                    }
                if spectral:
                    replacement[0] = replacement[0].real
                    replacement[-1] = replacement[-1].real
                original_row_energy = matrix.abs().square().sum(dim=1)
                replacement_row_energy = replacement.abs().square().sum(dim=1)
                norm_stats = {
                    "replacement_frobenius_norm_ratio": float(
                        torch.linalg.norm(replacement) / torch.linalg.norm(matrix)
                    ),
                    "max_row_energy_relative_error": float(
                        ((replacement_row_energy - original_row_energy).abs()
                         / original_row_energy.clamp_min(torch.finfo(torch.float64).eps))
                        .max()
                    ),
                }
                intervention_stats = {**intervention_stats, **norm_stats}
                projected[key] = as_weight(replacement, state[key], spectral)
            layer_records.append(
                {
                    "key": key,
                    "representation": "complex_spectral" if spectral else "real_fir",
                    "shape": list(matrix.shape),
                    "final_layer": final_layer,
                    "selected": selected,
                    **stats,
                    **intervention_stats,
                }
            )

        if args.intervention == "norm_matched_scale":
            scale_tag = "_norm_matched_scale"
        elif args.intervention == "power_preserving_consensus":
            scale_tag = "_power_consensus"
        elif args.intervention == "sparse_fir":
            scale_tag = f"_sparse_fir_k{args.sparse_taps}"
        else:
            scale_tag = "" if args.deviation_scale == 0 else (
                f"_a{args.deviation_scale:g}".replace(".", "p")
            )
        output = args.output_dir / (
            f"{path.stem}.channel_shared{scale_tag}_projected.pt"
        )
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
        "deviation_scale": args.deviation_scale,
        "intervention": args.intervention,
        "sparse_taps": args.sparse_taps,
        "projection": (
            "shared channel mean plus a fixed fraction of the orthogonal "
            "channel-specific deviation"
            if args.intervention == "shared_path"
            else (
                "scalar rescaling of the original matrix to the Frobenius "
                "norm of its channel-shared projection"
                if args.intervention == "norm_matched_scale"
                else (
                    "channel consensus with the original RMS magnitude "
                    "preserved separately in every temporal row"
                    if args.intervention == "power_preserving_consensus"
                    else "channel-shared spectrum compiled from the fixed "
                    "largest-magnitude real impulse-response taps"
                )
            )
        ),
        "checkpoints": records,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
