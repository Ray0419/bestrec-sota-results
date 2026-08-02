#!/usr/bin/env python3
"""Verify and benchmark a compact head-shared WEARec adaptive output layer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from torch import nn


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_projection_module(path: Path):
    spec = importlib.util.spec_from_file_location("wearec_projection", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HeadSharedAdaptiveMLP(nn.Module):
    """Compute one dynamic frequency response, then broadcast it to all heads."""

    def __init__(self, original: nn.Sequential, heads: int, freq_bins: int):
        super().__init__()
        self.input = copy.deepcopy(original[0])
        self.activation = copy.deepcopy(original[1])
        hidden_size = original[2].in_features
        self.output = nn.Linear(hidden_size, freq_bins * 2)
        self.heads = heads
        self.freq_bins = freq_bins

        source = original[2]
        with torch.no_grad():
            self.output.weight.copy_(
                source.weight.reshape(
                    heads, freq_bins * 2, hidden_size
                ).mean(dim=0)
            )
            self.output.bias.copy_(
                source.bias.reshape(heads, freq_bins * 2).mean(dim=0)
            )

    def forward(self, context: torch.Tensor) -> torch.Tensor:
        shared = self.output(self.activation(self.input(context)))
        return shared.view(context.shape[0], 1, self.freq_bins, 2).expand(
            -1, self.heads, -1, -1
        )


def model_args(
    item_size: int,
    batch_size: int,
    heads: int,
    alpha: float,
    max_seq_length: int,
    hidden_size: int,
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


def synchronize(device: torch.device) -> None:
    if device.type == "mps":
        torch.mps.synchronize()


@torch.inference_mode()
def timed_forward(
    models: dict[str, nn.Module],
    input_ids: torch.Tensor,
    warmup: int,
    repeats: int,
    device: torch.device,
) -> dict[str, dict]:
    for _ in range(warmup):
        for model in models.values():
            model(input_ids)
    synchronize(device)

    samples = {name: [] for name in models}
    names = list(models)
    for repeat in range(repeats):
        order = names if repeat % 2 == 0 else list(reversed(names))
        for name in order:
            model = models[name]
            synchronize(device)
            started = time.perf_counter()
            model(input_ids)
            synchronize(device)
            samples[name].append(time.perf_counter() - started)
    return {
        name: {
            "median_seconds": float(np.median(values)),
            "mean_seconds": float(np.mean(values)),
            "p10_seconds": float(np.quantile(values, 0.1)),
            "p90_seconds": float(np.quantile(values, 0.9)),
        }
        for name, values in samples.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--heads", type=int, required=True)
    parser.add_argument("--alpha", type=float, required=True)
    parser.add_argument("--max-seq-length", type=int, default=50)
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--seed", type=int, default=271828)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    if args.device == "mps" and not torch.backends.mps.is_available():
        raise SystemExit("MPS requested but unavailable")
    device = torch.device(args.device)

    sys.path.insert(0, str(args.source_dir))
    from model.wearec import WEARecModel

    state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    item_size = int(state["item_embeddings.weight"].shape[0])
    config = model_args(
        item_size,
        args.batch_size,
        args.heads,
        args.alpha,
        args.max_seq_length,
        args.hidden_size,
    )
    freq_bins = args.max_seq_length // 2 + 1
    projection_path = Path(__file__).with_name(
        "paired_wearec_static_projection_eval.py"
    )
    projection_module = load_projection_module(projection_path)
    projected_state, records = projection_module.project_adaptive_state(
        state,
        args.heads,
        0.905,
        0.97,
        freq_bins,
        args.hidden_size,
    )
    if sum(row["selected"] for row in records) != 2:
        raise SystemExit("checkpoint does not pass the frozen adaptive gate")

    expanded = WEARecModel(config)
    expanded.load_state_dict(projected_state, strict=True)
    compact = WEARecModel(config)
    compact.load_state_dict(state, strict=True)
    final_layer = compact.item_encoder.blocks[-1].layer
    final_layer.adaptive_mlp = HeadSharedAdaptiveMLP(
        final_layer.adaptive_mlp, args.heads, freq_bins
    )
    models = {
        "expanded_projected": expanded.to(device).eval(),
        "compact_shared": compact.to(device).eval(),
    }

    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    input_ids = torch.randint(
        1,
        item_size,
        (args.batch_size, args.max_seq_length),
        generator=generator,
        dtype=torch.long,
    ).to(device)
    with torch.inference_mode():
        expanded_output = models["expanded_projected"](input_ids)
        compact_output = models["compact_shared"](input_ids)
    difference = (expanded_output - compact_output).abs()
    parity = {
        "max_abs": float(difference.max().cpu()),
        "mean_abs": float(difference.mean().cpu()),
        "allclose_at_1e_6": bool(
            torch.allclose(expanded_output, compact_output, atol=1e-6, rtol=1e-6)
        ),
    }
    if not parity["allclose_at_1e_6"]:
        raise SystemExit(f"compact parity failed: {parity}")

    parameter_counts = {
        name: int(sum(parameter.numel() for parameter in model.parameters()))
        for name, model in models.items()
    }
    original_output_parameters = (
        args.heads * freq_bins * 2 * (args.hidden_size + 1)
    )
    compact_output_parameters = freq_bins * 2 * (args.hidden_size + 1)
    benchmark = timed_forward(
        models, input_ids, args.warmup, args.repeats, device
    )
    result = {
        "protocol": "WEAREC_COMPACT_ADAPTIVE_HEAD_BENCHMARK_V1",
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256(args.checkpoint),
        "projection_script_sha256": sha256(projection_path),
        "heads": args.heads,
        "alpha": args.alpha,
        "max_seq_length": args.max_seq_length,
        "hidden_size": args.hidden_size,
        "device": args.device,
        "threads": args.threads,
        "batch_size": args.batch_size,
        "warmup": args.warmup,
        "repeats": args.repeats,
        "parity": parity,
        "parameter_counts": parameter_counts,
        "parameters_saved": (
            parameter_counts["expanded_projected"]
            - parameter_counts["compact_shared"]
        ),
        "whole_model_fraction_saved": 1.0
        - parameter_counts["compact_shared"]
        / parameter_counts["expanded_projected"],
        "final_output_parameters": {
            "original": original_output_parameters,
            "compact": compact_output_parameters,
            "fraction_saved": 1.0
            - compact_output_parameters / original_output_parameters,
        },
        "final_output_linear_macs_per_example": {
            "original": (
                args.heads * freq_bins * 2 * args.hidden_size
            ),
            "compact": freq_bins * 2 * args.hidden_size,
        },
        "benchmark": benchmark,
        "median_speedup": benchmark["expanded_projected"]["median_seconds"]
        / benchmark["compact_shared"]["median_seconds"],
        "system_load_average": list(os.getloadavg()),
        "warning": "End-to-end encoder timing; interpret only on an idle device.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
