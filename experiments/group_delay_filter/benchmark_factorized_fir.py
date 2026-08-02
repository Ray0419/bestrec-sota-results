#!/usr/bin/env python3
"""Benchmark an exact rank-1 FIR deployment against a depthwise Conv1d bank."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import torch
import torch.nn.functional as F


def synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elif device.type == "mps":
        torch.mps.synchronize()


def measure(fn, device: torch.device, warmup: int, repeats: int) -> list[float]:
    for _ in range(warmup):
        fn()
    synchronize(device)
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        synchronize(device)
        timings.append((time.perf_counter() - start) * 1000.0)
    return timings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=1)
    parser.add_argument("--batch-sizes", default="1,32,256")
    parser.add_argument("--sequence-length", type=int, default=50)
    parser.add_argument("--device", choices=("cpu", "mps", "cuda"), default="cpu")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    device = torch.device(args.device)
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    key = f"item_encoder.blocks.{args.layer}.layer.causal_conv.weight"
    weight = state[key].to(device)
    channels, _, taps = weight.shape
    target = weight[:, 0, :].T.to(torch.float64)
    u, s, vh = torch.linalg.svd(target, full_matrices=False)
    shared = (u[:, 0] * s[0]).to(weight.dtype).reshape(1, 1, taps).to(device)
    gain = vh[0, :].to(weight.dtype).reshape(1, channels, 1).to(device)
    projected = (shared.reshape(taps, 1) * gain.reshape(1, channels)) \
        .T.unsqueeze(1).contiguous()

    records = []
    for batch in (int(x) for x in args.batch_sizes.split(",")):
        generator = torch.Generator(device="cpu").manual_seed(1701 + batch)
        x = torch.randn(
            batch, channels, args.sequence_length, generator=generator).to(device)

        def depthwise():
            return F.conv1d(F.pad(x, (taps - 1, 0)), projected, groups=channels)

        def factorized():
            flat = x.reshape(batch * channels, 1, args.sequence_length)
            filtered = F.conv1d(F.pad(flat, (taps - 1, 0)), shared)
            return filtered.reshape(batch, channels, args.sequence_length) * gain

        error = float((depthwise() - factorized()).abs().max().cpu())
        depthwise_ms = measure(depthwise, device, args.warmup, args.repeats)
        factorized_ms = measure(factorized, device, args.warmup, args.repeats)
        records.append({
            "batch_size": batch,
            "max_absolute_error": error,
            "depthwise_median_ms": statistics.median(depthwise_ms),
            "factorized_median_ms": statistics.median(factorized_ms),
            "speedup": statistics.median(depthwise_ms) / statistics.median(factorized_ms),
        })

    artifact = {
        "protocol": "FACTORIZED_RANK1_FIR_BENCHMARK_V1",
        "device": str(device),
        "torch_version": torch.__version__,
        "checkpoint": str(args.checkpoint),
        "layer": args.layer,
        "shape": {"channels": channels, "taps": taps},
        "parameter_count": {
            "depthwise": channels * taps,
            "factorized": channels + taps,
            "reduction": 1.0 - (channels + taps) / (channels * taps),
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
