#!/usr/bin/env python3
"""Fit low-rank manifolds to trained FMLP spectral or causal FIR filters."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_spectral_filter(weight: torch.Tensor) -> torch.Tensor:
    """Return (frequency, channel) complex response with valid real endpoints."""
    response = torch.view_as_complex(weight.squeeze(0).contiguous()).to(torch.complex128)
    response = response.clone()
    response[0] = response[0].real
    response[-1] = response[-1].real
    return response


def canonical_fir_filter(weight: torch.Tensor) -> torch.Tensor:
    """Return a (tap, channel) matrix from a depthwise Conv1d weight."""
    if weight.ndim != 3 or weight.shape[1] != 1:
        raise ValueError(f"expected depthwise FIR weight (channel, 1, tap), got {weight.shape}")
    return weight[:, 0, :].T.to(torch.float64)


def rank_projection(target: torch.Tensor, rank: int) -> torch.Tensor:
    u, s, vh = torch.linalg.svd(target, full_matrices=False)
    rank = min(rank, len(s))
    return (u[:, :rank] * s[:rank]) @ vh[:rank, :]


def relative_error(estimate: torch.Tensor, target: torch.Tensor) -> float:
    return float(torch.linalg.vector_norm(estimate - target)
                 / torch.linalg.vector_norm(target).clamp_min(1e-15))


def fit_group_delay(
    target: torch.Tensor,
    sequence_length: int,
    steps: int,
    restarts: int,
    seed: int,
) -> tuple[torch.Tensor, dict]:
    frequencies, channels = target.shape
    omega = (2.0 * math.pi / sequence_length) \
        * torch.arange(frequencies, dtype=torch.float64)
    u, s, vh = torch.linalg.svd(target, full_matrices=False)
    root = torch.sqrt(s[0])
    base0 = (u[:, 0] * root).clone()
    gain0 = (vh[0, :] * root).clone()
    generator = torch.Generator().manual_seed(seed)

    best_loss = float("inf")
    best = None
    best_tau = None
    for restart in range(restarts):
        base = torch.nn.Parameter(base0.clone())
        gain = torch.nn.Parameter(gain0.clone())
        if restart == 0:
            tau0 = torch.zeros(channels, dtype=torch.float64)
        else:
            tau0 = (torch.rand(channels, generator=generator, dtype=torch.float64) - 0.5) \
                * sequence_length * 0.25
        raw_tau = torch.nn.Parameter(
            torch.atanh((2.0 * tau0 / sequence_length).clamp(-0.99, 0.99)))
        optimizer = torch.optim.Adam([base, gain, raw_tau], lr=0.03)
        denominator = target.abs().square().mean().clamp_min(1e-15)
        for _ in range(steps):
            tau = 0.5 * sequence_length * torch.tanh(raw_tau)
            phase = torch.exp(-1j * omega[:, None] * tau[None, :])
            estimate = base[:, None] * gain[None, :] * phase
            loss = (estimate - target).abs().square().mean() / denominator
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        with torch.no_grad():
            tau = 0.5 * sequence_length * torch.tanh(raw_tau)
            estimate = base[:, None] * gain[None, :] \
                * torch.exp(-1j * omega[:, None] * tau[None, :])
            loss = float((estimate - target).abs().square().mean() / denominator)
            if loss < best_loss:
                best_loss = loss
                best = estimate.clone()
                best_tau = tau.clone()

    assert best is not None and best_tau is not None
    best[0] = best[0].real
    best[-1] = best[-1].real
    return best, {
        "relative_frobenius_error": relative_error(best, target),
        "tau_mean": float(best_tau.mean()),
        "tau_std": float(best_tau.std()),
        "tau_min": float(best_tau.min()),
        "tau_max": float(best_tau.max()),
    }


def as_spectral_weight(response: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    value = torch.view_as_real(response.to(torch.complex64)).unsqueeze(0)
    return value.to(dtype=reference.dtype)


def as_fir_weight(response: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    value = response.T.unsqueeze(1)
    return value.to(dtype=reference.dtype)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint-glob", required=True)
    ap.add_argument("--sequence-length", type=int, default=50)
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--restarts", type=int, default=4)
    ap.add_argument("--ranks", default="1",
                    help="comma-separated truncated-SVD ranks to save")
    ap.add_argument("--energy-thresholds", default="",
                    help="comma-separated rank-1 retained-energy thresholds")
    ap.add_argument(
        "--energy-final-layer-only",
        action="store_true",
        help="apply energy-gated projections only to the final temporal-filter layer",
    )
    ap.add_argument("--skip-group-delay", action="store_true")
    ap.add_argument("--seed", type=int, default=271828)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--summary", type=Path, required=True)
    args = ap.parse_args()
    ranks = sorted({int(x) for x in args.ranks.split(",") if x.strip()})
    energy_thresholds = sorted({
        float(x) for x in args.energy_thresholds.split(",") if x.strip()})
    if not ranks or ranks[0] < 1:
        raise SystemExit("--ranks must contain positive integers")
    if any(x <= 0 or x > 1 for x in energy_thresholds):
        raise SystemExit("--energy-thresholds values must lie in (0,1]")

    paths = [Path(x) for x in sorted(glob.glob(args.checkpoint_glob))]
    if not paths:
        raise SystemExit(f"no checkpoints match {args.checkpoint_glob!r}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for checkpoint_index, path in enumerate(paths):
        state = torch.load(path, map_location="cpu", weights_only=False)
        projected_delay = None if args.skip_group_delay else {
            k: v.clone() for k, v in state.items()}
        projected_ranks = {
            rank: {k: v.clone() for k, v in state.items()} for rank in ranks}
        projected_energy = {
            threshold: {k: v.clone() for k, v in state.items()}
            for threshold in energy_thresholds}
        layer_records = []
        filter_keys = sorted(
            k for k in state
            if k.endswith("layer.complex_weight")
            or k.endswith("layer.causal_conv.weight")
        )
        if not filter_keys:
            raise SystemExit(f"no FMLP spectral or causal FIR filters in {path}")
        for layer_index, key in enumerate(filter_keys):
            is_spectral = key.endswith("layer.complex_weight")
            target = canonical_spectral_filter(state[key]) if is_spectral \
                else canonical_fir_filter(state[key])
            rank_estimates = {
                rank: rank_projection(target, rank) for rank in ranks}
            if not args.skip_group_delay:
                if not is_spectral:
                    raise SystemExit(
                        "group-delay fitting applies only to complex spectral filters; "
                        "pass --skip-group-delay for causal FIR checkpoints")
                delay, delay_stats = fit_group_delay(
                    target, args.sequence_length, args.steps, args.restarts,
                    args.seed + 1000 * checkpoint_index + layer_index,
                )
                projected_delay[key] = as_spectral_weight(delay, state[key])
            else:
                delay_stats = None
            for rank, estimate in rank_estimates.items():
                projected_ranks[rank][key] = as_spectral_weight(estimate, state[key]) \
                    if is_spectral else as_fir_weight(estimate, state[key])
            rank1 = rank_projection(target, 1)
            rank1_error = relative_error(rank1, target)
            rank1_energy = 1.0 - rank1_error ** 2
            depth_eligible = not args.energy_final_layer_only \
                or layer_index == len(filter_keys) - 1
            for threshold, projected in projected_energy.items():
                if depth_eligible and rank1_energy >= threshold:
                    projected[key] = as_spectral_weight(rank1, state[key]) \
                        if is_spectral else as_fir_weight(rank1, state[key])
            layer_records.append({
                "key": key,
                "representation": "complex_spectral" if is_spectral else "real_fir",
                "shape": list(target.shape),
                "rank_relative_frobenius_error": {
                    str(rank): relative_error(estimate, target)
                    for rank, estimate in rank_estimates.items()},
                "rank1_retained_energy": rank1_energy,
                "energy_projection": {
                    str(threshold): depth_eligible and rank1_energy >= threshold
                    for threshold in energy_thresholds},
                "energy_depth_eligible": depth_eligible,
                "group_delay": delay_stats,
            })

        rank_paths = {}
        for rank, projected in projected_ranks.items():
            rank_path = args.output_dir / f"{path.stem}.rank{rank}_projected.pt"
            torch.save(projected, rank_path)
            rank_paths[str(rank)] = str(rank_path)
        energy_paths = {}
        for threshold, projected in projected_energy.items():
            label = f"{threshold:.4f}".rstrip("0").rstrip(".").replace(".", "p")
            energy_path = args.output_dir / \
                f"{path.stem}.energy{label}_projected.pt"
            torch.save(projected, energy_path)
            energy_paths[str(threshold)] = str(energy_path)
        delay_path = None
        if projected_delay is not None:
            delay_path = args.output_dir / f"{path.stem}.group_delay_projected.pt"
            torch.save(projected_delay, delay_path)
        records.append({
            "checkpoint": str(path),
            "checkpoint_sha256": sha256(path),
            "rank_projected": rank_paths,
            "energy_projected": energy_paths,
            "group_delay_projected": None if delay_path is None else str(delay_path),
            "layers": layer_records,
        })
        print(path.name)
        for layer in layer_records:
            rank_text = " ".join(
                f"rank{rank}={error:.4f}" for rank, error in
                layer["rank_relative_frobenius_error"].items())
            delay_text = "" if layer["group_delay"] is None else \
                f" group_delay={layer['group_delay']['relative_frobenius_error']:.4f}"
            print(
                f"  {layer['key']}: {rank_text}{delay_text}"
            )

    scalar_factor = 2 if records[0]["layers"][0]["representation"] \
        == "complex_spectral" else 1
    full_params = scalar_factor * records[0]["layers"][0]["shape"][0] \
        * records[0]["layers"][0]["shape"][1]
    frequencies, channels = records[0]["layers"][0]["shape"]
    artifact = {
        "protocol": "GROUP_DELAY_MANIFOLD_FEASIBILITY_V1",
        "sequence_length": args.sequence_length,
        "parameter_counts_per_layer": {
            "full": full_params,
            **{
                f"rank{rank}": scalar_factor * rank * (frequencies + channels)
                for rank in ranks},
            "group_delay": 2 * frequencies + 3 * channels,
        },
        "fit": {"steps": args.steps, "restarts": args.restarts, "seed": args.seed},
        "energy_final_layer_only": args.energy_final_layer_only,
        "checkpoints": records,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
