#!/usr/bin/env python3
"""Paired validation evaluation of a gated WEARec static-base projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from torch.utils.data import DataLoader, SequentialSampler


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_matrix(weight: torch.Tensor) -> torch.Tensor:
    if weight.ndim != 3 or weight.shape[-1] != 1:
        raise ValueError(f"expected heads x frequencies x 1, got {weight.shape}")
    return weight.squeeze(-1).T.to(torch.float64)


def projection_stats(matrix: torch.Tensor) -> dict[str, float]:
    _, singular_values, vh = torch.linalg.svd(matrix, full_matrices=False)
    energy = singular_values.square()
    uniform = torch.ones_like(vh[0]) / math.sqrt(matrix.shape[1])
    shared = matrix.mean(dim=1, keepdim=True).expand_as(matrix)
    return {
        "rank1_retained_energy": float(energy[0] / energy.sum()),
        "dominant_head_uniform_cosine": float(abs(vh[0] @ uniform)),
        "head_shared_retained_energy": float(
            shared.square().sum() / matrix.square().sum()
        ),
    }


def project_state(
    state: dict[str, torch.Tensor],
    rank1_threshold: float,
    consensus_threshold: float,
) -> tuple[dict[str, torch.Tensor], list[dict]]:
    projected = {key: value.clone() for key, value in state.items()}
    keys = sorted(
        key
        for key in state
        if key.endswith("layer.base_filter") or key.endswith("layer.base_bias")
    )
    if len(keys) != 4:
        raise ValueError(f"expected four static-base tensors, found {keys}")

    records = []
    for index, key in enumerate(keys):
        matrix = canonical_matrix(state[key])
        stats = projection_stats(matrix)
        final_layer = index >= len(keys) - 2
        selected = (
            final_layer
            and stats["rank1_retained_energy"] >= rank1_threshold
            and stats["dominant_head_uniform_cosine"] >= consensus_threshold
        )
        if selected:
            shared = matrix.mean(dim=1, keepdim=True).expand_as(matrix)
            projected[key] = shared.T.unsqueeze(-1).to(state[key].dtype)
        records.append(
            {
                "key": key,
                "shape_frequency_by_head": list(matrix.shape),
                "final_layer": final_layer,
                "selected": selected,
                **stats,
            }
        )
    return projected, records


def project_adaptive_state(
    state: dict[str, torch.Tensor],
    heads: int,
    rank1_threshold: float,
    consensus_threshold: float,
    freq_bins: int = 26,
    hidden_size: int = 64,
) -> tuple[dict[str, torch.Tensor], list[dict]]:
    projected = {key: value.clone() for key, value in state.items()}
    keys = sorted(
        key
        for key in state
        if key.endswith("layer.adaptive_mlp.2.weight")
        or key.endswith("layer.adaptive_mlp.2.bias")
    )
    if len(keys) != 4:
        raise ValueError(f"expected four adaptive-output tensors, found {keys}")

    records = []
    for index, key in enumerate(keys):
        value = state[key].to(torch.float64)
        is_weight = key.endswith("weight")
        if is_weight:
            tensor = value.reshape(heads, freq_bins, 2, hidden_size)
            matrix = tensor.permute(1, 2, 3, 0).reshape(-1, heads)
        else:
            tensor = value.reshape(heads, freq_bins, 2)
            matrix = tensor.permute(1, 2, 0).reshape(-1, heads)
        stats = projection_stats(matrix)
        final_layer = index >= len(keys) - 2
        selected = (
            final_layer
            and stats["rank1_retained_energy"] >= rank1_threshold
            and stats["dominant_head_uniform_cosine"] >= consensus_threshold
        )
        if selected:
            shared = matrix.mean(dim=1, keepdim=True).expand_as(matrix)
            if is_weight:
                estimate = shared.reshape(
                    freq_bins, 2, hidden_size, heads
                ).permute(3, 0, 1, 2)
            else:
                estimate = shared.reshape(freq_bins, 2, heads).permute(2, 0, 1)
            projected[key] = estimate.reshape_as(state[key]).to(state[key].dtype)
        records.append(
            {
                "key": key,
                "shape_rows_by_head": list(matrix.shape),
                "final_layer": final_layer,
                "selected": selected,
                **stats,
            }
        )
    return projected, records


def impulse_view(
    value: torch.Tensor,
    heads: int,
    freq_bins: int,
    hidden_size: int,
) -> torch.Tensor:
    if value.ndim == 2:
        return value.reshape(heads, freq_bins, 2, hidden_size).permute(1, 0, 2, 3)
    return value.reshape(heads, freq_bins, 2).permute(1, 0, 2)


def impulse_radius_stats(
    value: torch.Tensor,
    heads: int,
    sequence_length: int,
    hidden_size: int,
    energy_threshold: float,
) -> dict[str, float | int]:
    freq_bins = sequence_length // 2 + 1
    spectrum = impulse_view(
        value.to(torch.float64), heads, freq_bins, hidden_size
    )
    impulse = torch.fft.irfft(
        spectrum, n=sequence_length, dim=0, norm="ortho"
    )
    total = impulse.square().sum().clamp_min(1e-30)
    for radius in range(sequence_length // 2 + 1):
        retained = impulse[: radius + 1].square().sum()
        if radius:
            retained = retained + impulse[-radius:].square().sum()
        fraction = float(retained / total)
        if fraction >= energy_threshold:
            return {
                "minimum_radius": radius,
                "retained_impulse_energy": fraction,
            }
    raise AssertionError("full impulse support did not retain all energy")


def project_impulse_tensor(
    value: torch.Tensor,
    heads: int,
    sequence_length: int,
    hidden_size: int,
    radius: int,
) -> torch.Tensor:
    freq_bins = sequence_length // 2 + 1
    spectrum = impulse_view(
        value.to(torch.float64), heads, freq_bins, hidden_size
    )
    impulse = torch.fft.irfft(
        spectrum, n=sequence_length, dim=0, norm="ortho"
    )
    compact = torch.zeros_like(impulse)
    compact[0] = impulse[0]
    if radius:
        symmetric = 0.5 * (impulse[1 : radius + 1] + impulse[-radius:].flip(0))
        compact[1 : radius + 1] = symmetric
        compact[-radius:] = symmetric.flip(0)
    projected = torch.fft.rfft(
        compact, n=sequence_length, dim=0, norm="ortho"
    ).real
    if value.ndim == 2:
        restored = projected.permute(1, 0, 2, 3).reshape_as(value)
    else:
        restored = projected.permute(1, 0, 2).reshape_as(value)
    return restored.to(value.dtype)


def project_impulse_adaptive_state(
    state: dict[str, torch.Tensor],
    heads: int,
    sequence_length: int,
    hidden_size: int,
    energy_threshold: float,
    max_radius_ratio: float,
) -> tuple[dict[str, torch.Tensor], list[dict]]:
    projected = {key: value.clone() for key, value in state.items()}
    prefixes = sorted(
        key.removesuffix(".weight")
        for key in state
        if key.endswith("layer.adaptive_mlp.2.weight")
    )
    if len(prefixes) != 2:
        raise ValueError(f"expected two adaptive output layers, found {prefixes}")

    records = []
    for index, prefix in enumerate(prefixes):
        keys = [f"{prefix}.weight", f"{prefix}.bias"]
        stats = {
            key: impulse_radius_stats(
                state[key],
                heads,
                sequence_length,
                hidden_size,
                energy_threshold,
            )
            for key in keys
        }
        common_radius = max(row["minimum_radius"] for row in stats.values())
        final_layer = index == len(prefixes) - 1
        selected = (
            final_layer
            and common_radius / sequence_length <= max_radius_ratio
        )
        for key in keys:
            if selected:
                projected[key] = project_impulse_tensor(
                    state[key],
                    heads,
                    sequence_length,
                    hidden_size,
                    common_radius,
                )
            records.append(
                {
                    "key": key,
                    "final_layer": final_layer,
                    "selected": selected,
                    "energy_threshold": energy_threshold,
                    "common_radius": common_radius,
                    "common_radius_ratio": common_radius / sequence_length,
                    **stats[key],
                }
            )
    return projected, records


def model_args(
    item_size: int,
    batch_size: int,
    heads: int,
    alpha: float,
    max_seq_length: int = 50,
    hidden_size: int = 64,
):
    return SimpleNamespace(
        item_size=item_size,
        batch_size=batch_size,
        max_seq_length=max_seq_length,
        hidden_size=hidden_size,
        num_hidden_layers=2,
        hidden_act="gelu",
        num_attention_heads=2,
        attention_probs_dropout_prob=0.5,
        hidden_dropout_prob=0.5,
        initializer_range=0.02,
        num_heads=heads,
        alpha=alpha,
        model_type="WEARec",
    )


def topk_indices(scores: np.ndarray, k: int) -> np.ndarray:
    candidates = np.argpartition(scores, -k, axis=1)[:, -k:]
    values = scores[np.arange(len(scores))[:, None], candidates]
    order = np.argsort(values, axis=1)[:, ::-1]
    return candidates[np.arange(len(scores))[:, None], order]


@torch.inference_mode()
def evaluate(
    model: torch.nn.Module,
    dataloader: DataLoader,
    rating_matrix,
    device: torch.device,
) -> dict[str, np.ndarray]:
    model.eval()
    answers = []
    predictions = []
    for batch in dataloader:
        user_ids, input_ids, batch_answers, _, _ = batch
        sequence = model.predict(
            input_ids.to(device), user_ids.to(device)
        )[:, -1, :]
        scores = torch.matmul(sequence, model.item_embeddings.weight.T)
        scores = scores.cpu().numpy()
        seen = rating_matrix[user_ids.numpy()].toarray() > 0
        scores[seen] = -math.inf
        scores[:, 0] = -math.inf
        predictions.append(topk_indices(scores, 20))
        answers.append(batch_answers.numpy())

    answer = np.concatenate(answers)
    predicted = np.concatenate(predictions)
    metrics = {}
    for k in (5, 10, 20):
        matches = predicted[:, :k] == answer[:, None]
        hit = matches.any(axis=1).astype(np.float64)
        ranks = np.argmax(matches, axis=1)
        metrics[f"HR@{k}"] = hit
        metrics[f"NDCG@{k}"] = np.where(
            hit > 0, 1.0 / np.log2(ranks + 2.0), 0.0
        )
    return metrics


def paired_stats(
    baseline: np.ndarray,
    projected: np.ndarray,
    seed: int,
    bootstrap_samples: int,
) -> dict:
    delta = projected - baseline
    generator = np.random.default_rng(seed)
    boot = np.empty(bootstrap_samples, dtype=np.float64)
    for start in range(0, bootstrap_samples, 100):
        size = min(100, bootstrap_samples - start)
        indices = generator.integers(0, len(delta), size=(size, len(delta)))
        boot[start:start + size] = delta[indices].mean(axis=1)
    nonzero = delta[delta != 0]
    return {
        "n_users": int(len(delta)),
        "baseline": float(baseline.mean()),
        "projected": float(projected.mean()),
        "delta": float(delta.mean()),
        "bootstrap_95_ci": [
            float(np.quantile(boot, 0.025)),
            float(np.quantile(boot, 0.975)),
        ],
        "users_improved": int((delta > 0).sum()),
        "users_harmed": int((delta < 0).sum()),
        "users_unchanged": int((delta == 0).sum()),
        "nonzero_win_rate": None
        if len(nonzero) == 0
        else float((nonzero > 0).mean()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-name", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--heads", type=int, required=True)
    parser.add_argument("--alpha", type=float, required=True)
    parser.add_argument("--max-seq-length", type=int, default=50)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument(
        "--projection-target",
        choices=("static", "adaptive", "impulse"),
        default="static",
    )
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument("--rank1-threshold", type=float, default=0.905)
    parser.add_argument("--consensus-threshold", type=float, default=0.97)
    parser.add_argument("--impulse-energy-threshold", type=float, default=0.95)
    parser.add_argument("--max-radius-ratio", type=float, default=0.2)
    parser.add_argument("--expected-data-sha256")
    parser.add_argument("--expected-checkpoint-sha256")
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)

    data_path = args.source_dir / "data" / f"{args.data_name}.txt"
    identities = {
        "data_sha256": sha256(data_path),
        "checkpoint_sha256": sha256(args.checkpoint),
        "preregistration_sha256": sha256(args.preregistration),
    }
    expected = {
        "data_sha256": args.expected_data_sha256,
        "checkpoint_sha256": args.expected_checkpoint_sha256,
    }
    for key, value in expected.items():
        if value is not None and identities[key] != value:
            raise SystemExit(f"{key} mismatch: {identities[key]} != {value}")

    sys.path.insert(0, str(args.source_dir))
    from dataset import (
        RecDataset,
        generate_rating_matrix_valid,
        get_user_seqs,
    )
    from model.wearec import WEARecModel

    user_seq, max_item, num_users = get_user_seqs(str(data_path))
    config = model_args(
        max_item + 1,
        args.batch_size,
        args.heads,
        args.alpha,
        args.max_seq_length,
        args.hidden_size,
    )
    dataset = RecDataset(config, user_seq, data_type="valid")
    dataloader = DataLoader(
        dataset,
        sampler=SequentialSampler(dataset),
        batch_size=args.batch_size,
        num_workers=0,
    )
    rating_matrix = generate_rating_matrix_valid(
        user_seq, num_users, max_item + 1
    )

    baseline_state = torch.load(
        args.checkpoint, map_location="cpu", weights_only=False
    )
    if args.projection_target == "static":
        projected_state, projection = project_state(
            baseline_state, args.rank1_threshold, args.consensus_threshold
        )
    elif args.projection_target == "adaptive":
        projected_state, projection = project_adaptive_state(
            baseline_state,
            args.heads,
            args.rank1_threshold,
            args.consensus_threshold,
            args.max_seq_length // 2 + 1,
            args.hidden_size,
        )
    else:
        projected_state, projection = project_impulse_adaptive_state(
            baseline_state,
            args.heads,
            args.max_seq_length,
            args.hidden_size,
            args.impulse_energy_threshold,
            args.max_radius_ratio,
        )
    selected = [row["key"] for row in projection if row["selected"]]
    if len(selected) != 2:
        raise SystemExit(f"expected both final static bases to select, got {selected}")

    if args.device == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("MPS requested but unavailable")
    device = torch.device(args.device)
    models = []
    for state in (baseline_state, projected_state):
        model = WEARecModel(config)
        model.load_state_dict(state, strict=True)
        models.append(model.to(device))

    baseline = evaluate(models[0], dataloader, rating_matrix, device)
    projected = evaluate(models[1], dataloader, rating_matrix, device)
    metrics = {
        metric: paired_stats(
            baseline[metric], projected[metric], args.seed, args.bootstrap_samples
        )
        for metric in baseline
    }
    artifact = {
        "protocol": (
            "WEAREC_STATIC_BASE_PROJECTION_VALIDATION_V1"
            if args.projection_target == "static"
            else "WEAREC_IMPULSE_SUPPORT_PROJECTION_VALIDATION_V1"
            if args.projection_target == "impulse"
            else (
            "WEAREC_ADAPTIVE_HEAD_PROJECTION_VALIDATION_V1"
            if args.max_seq_length == 50
            else "WEAREC_LONG_SEQUENCE_ADAPTIVE_COLLAPSE_VALIDATION_V1"
            )
        ),
        "data_name": args.data_name,
        "split": "valid",
        "mask": "strict_negative_infinity_including_padding",
        "source_revision": "2087335339b1ead87da6e066ce14e2d33880a95e",
        "checkpoint": str(args.checkpoint),
        "heads": args.heads,
        "alpha": args.alpha,
        "max_seq_length": args.max_seq_length,
        "hidden_size": args.hidden_size,
        "impulse_energy_threshold": args.impulse_energy_threshold,
        "max_radius_ratio": args.max_radius_ratio,
        "rank1_threshold": args.rank1_threshold,
        "consensus_threshold": args.consensus_threshold,
        "projection_target": args.projection_target,
        "projection": projection,
        "metrics": metrics,
        "identities": identities,
        "test_access": "none",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps(metrics["NDCG@10"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
