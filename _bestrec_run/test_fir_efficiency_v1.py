# -*- coding: utf-8 -*-
"""Structural tests for the prospective FIR efficiency arms."""
from __future__ import annotations

import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_sasrec_sbert_efficiency_ml1m_v1_frozen import SASRecSBERT  # noqa: E402
import eval_fir_efficiency_ml1m_v1 as evaluator  # noqa: E402


ARMS = {
    "identity": 0,
    "shared": 16,
    "grouped": 128,
    "lowrank": 320,
    "learned": 1024,
    "pointwise": 1024,
}


def build(arm: str):
    torch.manual_seed(90210)
    model = SASRecSBERT(
        n_items=40, pad_id=40, max_seq_len=8, d_model=64,
        n_layers=1, n_heads=2, dropout=0.0,
        fir_control=arm, fir_control_kernel=16,
        fir_control_groups=8, fir_control_rank=4)
    model.eval()
    return model


def filter_parameters(model):
    return [(name, parameter) for name, parameter in model.named_parameters()
            if name.startswith("fir_control_") and parameter.requires_grad]


def main():
    ids = torch.tensor([
        [1, 2, 3, 4, 5, 6, 7, 8],
        [2, 5, 4, 8, 1, 9, 3, 7],
    ], dtype=torch.long)
    probe = torch.Generator().manual_seed(7766)
    direction = torch.randn((2, 8, 64), generator=probe)

    reference = build("identity")
    with torch.no_grad():
        expected = reference.encode(ids)

    for arm, expected_count in ARMS.items():
        model = build(arm)
        params = filter_parameters(model)
        count = sum(parameter.numel() for _, parameter in params)
        if count != expected_count:
            raise AssertionError(f"{arm}: {count} params, expected {expected_count}")

        with torch.no_grad():
            observed = model.encode(ids)
        if not torch.equal(observed, expected):
            maximum = float((observed - expected).abs().max())
            raise AssertionError(f"{arm}: not exact identity at init (max={maximum})")

        if arm != "identity":
            model.zero_grad(set_to_none=True)
            loss = (model.encode(ids) * direction).sum()
            loss.backward()
            missing = [name for name, parameter in params
                       if parameter.grad is None
                       or not torch.isfinite(parameter.grad).all()
                       or float(parameter.grad.abs().sum()) == 0.0]
            if missing:
                raise AssertionError(f"{arm}: inactive filter gradient(s): {missing}")

        perturbed = ids.clone()
        perturbed[:, 6:] = torch.tensor([[12, 13], [14, 15]])
        with torch.no_grad():
            before = model.encode(ids)
            after = model.encode(perturbed)
        if not torch.equal(before[:, :6], after[:, :6]):
            maximum = float((before[:, :6] - after[:, :6]).abs().max())
            raise AssertionError(f"{arm}: future-token leakage (max={maximum})")
        print(f"PASS {arm:9s} params={count:4d} identity+gradient+causality")

    # Frozen evaluator reconstruction and resource instrumentation smoke test.
    config = {
        "max_seq_len": 8, "d_model": 64, "n_layers": 1, "n_heads": 2,
        "dropout": 0.0, "fir_control": "lowrank",
        "fir_control_kernel": 16, "fir_control_groups": 8,
        "fir_control_rank": 4,
    }
    source = build("lowrank")
    rebuilt = evaluator.build_model(config, n_items=40, pad_id=40)
    rebuilt.load_state_dict(source.state_dict(), strict=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rebuilt.to(device).eval()
    bench_ids = ids.to(device)
    last = torch.full((len(ids),), ids.shape[1] - 1,
                      dtype=torch.long, device=device)
    measured = evaluator.measure(rebuilt, bench_ids, last)
    for key in ("latency_ms_median", "latency_ms_p95", "flops_per_user"):
        if not (measured[key] > 0):
            raise AssertionError(f"resource smoke missing positive {key}")
    if device.type == "cuda" and not (measured["peak_cuda_memory_bytes"] > 0):
        raise AssertionError("resource smoke missing peak CUDA memory")
    print("PASS frozen evaluator reconstruction+resource instrumentation")

    print("FIR EFFICIENCY V1 STRUCTURAL TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
