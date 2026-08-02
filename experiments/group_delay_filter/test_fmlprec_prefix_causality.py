#!/usr/bin/env python3
"""Future-perturbation check for full and causal FMLP-Rec filter layers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import torch


def max_past_change(layer, seed: int = 1729) -> tuple[float, float]:
    torch.manual_seed(seed)
    inputs = torch.randn(2, 50, 64)
    altered = inputs.clone()
    altered[:, 25:, :] += 3.0 * torch.randn_like(altered[:, 25:, :])
    with torch.no_grad():
        baseline = layer(inputs)
        changed = layer(altered)
    past = float((baseline[:, :25] - changed[:, :25]).abs().max())
    future = float((baseline[:, 25:] - changed[:, 25:]).abs().max())
    return past, future


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source_dir.resolve()))
    from model.fmlprec import (  # pylint: disable=import-error,import-outside-toplevel
        FMLPRecLayer,
    )

    results = {}
    for mode in ("full", "causal_full", "causal_shared"):
        torch.manual_seed(31415)
        config = SimpleNamespace(
            filter_mode=mode,
            max_seq_length=50,
            hidden_size=64,
            hidden_dropout_prob=0.0,
            causal_k=16,
        )
        layer = FMLPRecLayer(config).eval()
        results[mode] = max_past_change(layer)
    for mode, (past, future) in results.items():
        print(f"{mode}: max_past_change={past:.9g} max_future_change={future:.9g}")
    if results["full"][0] <= args.tolerance:
        raise RuntimeError("full circular filter unexpectedly passed prefix invariance")
    for mode in ("causal_full", "causal_shared"):
        if results[mode][0] > args.tolerance:
            raise RuntimeError(f"{mode} violates prefix invariance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

