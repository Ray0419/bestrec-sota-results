#!/usr/bin/env python3
"""Refit a sparse final FIR from unlabeled calibration hidden states."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset

from paired_projection_eval import model_args, sha256
from project_channel_shared import as_weight, canonical_matrix


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def fit_coefficients(
    lagged: torch.Tensor,
    target: torch.Tensor,
    support: list[int],
    ridge_relative: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    design = lagged[:, support, :].permute(2, 0, 1).contiguous()
    gram = torch.einsum("cnk,cnj->ckj", design, design)
    rhs = torch.einsum("cnk,nc->ck", design, target)
    ridge = ridge_relative * torch.diagonal(gram, dim1=1, dim2=2).sum(1)
    ridge = ridge / len(support)
    ridge = ridge.clamp_min(torch.finfo(gram.dtype).eps)
    identity = torch.eye(len(support), dtype=gram.dtype).unsqueeze(0)
    coefficients = torch.linalg.solve(
        gram + ridge[:, None, None] * identity,
        rhs.unsqueeze(-1),
    ).squeeze(-1)
    prediction = torch.einsum("cnk,ck->nc", design, coefficients)
    return coefficients.T.contiguous(), prediction


def greedy_support(
    lagged: torch.Tensor,
    target: torch.Tensor,
    taps: int,
    ridge_relative: float,
) -> tuple[list[int], torch.Tensor, torch.Tensor]:
    selected: list[int] = []
    residual = target.clone()
    lag_energy = lagged.square().sum(dim=0)
    coefficients = torch.empty(0, target.shape[1], dtype=target.dtype)
    prediction = torch.zeros_like(target)
    for _ in range(taps):
        correlation = torch.einsum("nlc,nc->lc", lagged, residual)
        score = (correlation.square() / lag_energy.clamp_min(
            torch.finfo(lagged.dtype).eps
        )).sum(dim=1)
        if selected:
            score[selected] = -torch.inf
        winner = int(torch.argmax(score))
        selected.append(winner)
        coefficients, prediction = fit_coefficients(
            lagged, target, selected, ridge_relative
        )
        residual = target - prediction
    return selected, coefficients, prediction


def compile_arm(
    state: dict[str, torch.Tensor],
    key: str,
    matrix: torch.Tensor,
    impulse: torch.Tensor,
    lagged: torch.Tensor,
    target: torch.Tensor,
    support: list[int],
    selection_order: list[int],
    coefficients: torch.Tensor,
    prediction: torch.Tensor,
    ridge_relative: float,
    output: Path,
) -> dict:
    sequence_length = impulse.shape[0]
    unrefit_prediction = torch.einsum(
        "nkc,kc->nc", lagged[:, support, :], impulse[support]
    )
    unrefit_mse = float((unrefit_prediction - target).square().mean())
    refit_mse = float((prediction - target).square().mean())

    sparse_impulse = torch.zeros_like(impulse)
    sparse_impulse[support] = coefficients
    replacement = torch.fft.rfft(sparse_impulse, n=sequence_length, dim=0)
    replacement[0] = replacement[0].real
    replacement[-1] = replacement[-1].real

    projected = {name: value.clone() for name, value in state.items()}
    projected[key] = as_weight(replacement, state[key], spectral=True)
    stored = canonical_matrix(projected[key], spectral=True)
    stored_impulse = torch.fft.irfft(stored, n=sequence_length, dim=0)
    stored_prediction = torch.einsum(
        "nkc,kc->nc", lagged[:, support, :], stored_impulse[support]
    )
    keep = torch.zeros(sequence_length, dtype=torch.bool)
    keep[support] = True

    torch.save(projected, output)
    target_energy = float(target.square().mean())
    return {
        "output": str(output),
        "output_sha256": sha256(output),
        "support": sorted(support),
        "selection_order": selection_order,
        "taps": len(support),
        "ridge_relative": ridge_relative,
        "target_mean_square": target_energy,
        "unrefit_mse": unrefit_mse,
        "refit_mse": refit_mse,
        "refit_relative_mse": refit_mse / max(target_energy, 1e-30),
        "mse_reduction_vs_unrefit": (
            (unrefit_mse - refit_mse) / max(unrefit_mse, 1e-30)
        ),
        "coefficient_norm_ratio": float(
            torch.linalg.norm(sparse_impulse) / torch.linalg.norm(impulse)
        ),
        "storage_quantization_max_abs_error": float(
            (stored - replacement).abs().max()
        ),
        "stored_calibration_mse": float(
            (stored_prediction - target).square().mean()
        ),
        "excluded_tap_max_abs_after_storage": float(
            stored_impulse[~keep].abs().max()
        ),
    }


@torch.inference_mode()
def collect_final_inputs(
    model: torch.nn.Module,
    dataloader: DataLoader,
    device: torch.device,
) -> torch.Tensor:
    batches = []
    model.eval()
    for batch in dataloader:
        _, input_ids, _, _, _ = batch
        hidden = model.add_position_embedding(input_ids.to(device))
        for block in model.item_encoder.blocks[:-1]:
            hidden = block(hidden)
        batches.append(hidden.cpu())
    return torch.cat(batches, dim=0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-name", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--calibration-samples", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--taps", type=int, default=8)
    parser.add_argument("--ridge-relative", type=float, default=1e-4)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    args = parser.parse_args()

    if args.device == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("MPS was requested but is unavailable")
    if args.calibration_samples < 1 or args.taps < 1:
        raise SystemExit("calibration samples and taps must be positive")
    if args.ridge_relative <= 0:
        raise SystemExit("ridge relative strength must be positive")
    device = torch.device(args.device)

    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    sys.path.insert(0, str(args.source_dir))
    from dataset import RecDataset, get_user_seqs
    from model.fmlprec import FMLPRecModel

    data_path = args.source_dir / "data" / f"{args.data_name}.txt"
    user_seq, max_item, _ = get_user_seqs(str(data_path))
    config = model_args(max_item + 1, "full", 16, args.batch_size)
    dataset = RecDataset(config, user_seq, data_type="train")
    count = min(args.calibration_samples, len(dataset))
    indices = np.linspace(0, len(dataset) - 1, num=count, dtype=np.int64)
    if len(np.unique(indices)) != count:
        raise SystemExit("calibration index construction produced duplicates")
    dataloader = DataLoader(
        Subset(dataset, indices.tolist()),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )

    state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = FMLPRecModel(config)
    model.load_state_dict(state)
    hidden = collect_final_inputs(model.to(device), dataloader, device).to(torch.float64)
    del model
    if device.type == "mps":
        torch.mps.empty_cache()

    filter_keys = sorted(
        key for key in state if key.endswith("layer.complex_weight")
    )
    if not filter_keys:
        raise SystemExit(f"no final spectral filter in {args.checkpoint}")
    key = filter_keys[-1]
    matrix = canonical_matrix(state[key], spectral=True)
    sequence_length = 2 * (matrix.shape[0] - 1)
    if hidden.shape[1:] != (sequence_length, matrix.shape[1]):
        raise SystemExit(
            f"hidden/filter shape mismatch: {hidden.shape} vs {matrix.shape}"
        )
    if args.taps > sequence_length:
        raise SystemExit("tap count exceeds sequence length")

    impulse = torch.fft.irfft(matrix, n=sequence_length, dim=0)
    lag_order = (sequence_length - 1 - torch.arange(sequence_length)) % sequence_length
    lagged = hidden[:, lag_order, :]
    target = torch.einsum("nlc,lc->nc", lagged, impulse)

    energy = impulse.square().sum(dim=1)
    magnitude_order = torch.argsort(energy, descending=True, stable=True)
    magnitude_selection = [int(value) for value in magnitude_order[:args.taps]]
    magnitude_coefficients, magnitude_prediction = fit_coefficients(
        lagged,
        target,
        magnitude_selection,
        args.ridge_relative,
    )
    greedy_selection, greedy_coefficients, greedy_prediction = greedy_support(
        lagged,
        target,
        args.taps,
        args.ridge_relative,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    magnitude_output = args.output_dir / (
        f"{args.checkpoint.stem}.magnitude_refit_k{args.taps}.pt"
    )
    greedy_output = args.output_dir / (
        f"{args.checkpoint.stem}.greedy_refit_k{args.taps}.pt"
    )
    arms = {
        "M8-R": compile_arm(
            state,
            key,
            matrix,
            impulse,
            lagged,
            target,
            magnitude_selection,
            magnitude_selection,
            magnitude_coefficients,
            magnitude_prediction,
            args.ridge_relative,
            magnitude_output,
        ),
        "G8-R": compile_arm(
            state,
            key,
            matrix,
            impulse,
            lagged,
            target,
            greedy_selection,
            greedy_selection,
            greedy_coefficients,
            greedy_prediction,
            args.ridge_relative,
            greedy_output,
        ),
    }
    artifact = {
        "protocol": "ACTIVATION_AWARE_SPARSE_REFIT_PILOT_V1",
        "script_sha256": sha256(Path(__file__)),
        "data_name": args.data_name,
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256(args.checkpoint),
        "filter_key": key,
        "filter_count": len(filter_keys),
        "device": str(device),
        "calibration_dataset": "train_prefixes",
        "calibration_population": len(dataset),
        "calibration_samples": count,
        "calibration_indices_sha256": array_sha256(indices),
        "calibration_hidden_sha256": array_sha256(hidden.numpy()),
        "sequence_length": sequence_length,
        "channels": matrix.shape[1],
        "taps": args.taps,
        "ridge_relative": args.ridge_relative,
        "arms": arms,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({name: {
        "support": values["support"],
        "refit_relative_mse": values["refit_relative_mse"],
        "mse_reduction_vs_unrefit": values["mse_reduction_vs_unrefit"],
    } for name, values in arms.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

