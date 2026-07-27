#!/usr/bin/env python
"""Fail-closed no-future-leakage tests for every FIR/residual implementation.

The test changes only tokens strictly after a prefix boundary and checks that
all encoded prefix states are invariant.  Filter parameters are moved away from
their identity initialization so a zero/no-op implementation cannot pass by
accident.  Both encoder paths used by the experiment driver are exercised.
"""
from __future__ import annotations

import sys

import torch

from run_sasrec_sbert import SASRecSBERT


ATOL = 1e-7
PREFIX = 4
LEFT = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]], dtype=torch.long)
RIGHT = torch.tensor([[1, 2, 3, 4, 14, 15, 16, 17]], dtype=torch.long)


def make_model(encoder: str, arm: str) -> SASRecSBERT:
    kwargs = {}
    if arm == "canonical":
        kwargs["fir_v3"] = "learned"
        kwargs["fir_v3_kernel"] = 4
    elif arm == "legacy":
        kwargs["causal_filter"] = True
        kwargs["filter_kernel"] = 4
    else:
        kwargs["fir_control"] = arm
        kwargs["fir_control_kernel"] = 4

    torch.manual_seed(20260727)
    model = SASRecSBERT(
        n_items=24,
        pad_id=24,
        max_seq_len=8,
        d_model=8,
        n_layers=1,
        n_heads=2,
        dropout=0.0,
        encoder=encoder,
        **kwargs,
    )
    model.eval()

    # Move every tested treatment away from its exact-identity initialization.
    # This makes the test sensitive to padding direction and kernel application.
    with torch.no_grad():
        if arm == "canonical":
            model.fir_v3.weight.normal_(mean=0.0, std=0.15)
        elif arm == "legacy":
            model.causal_filter.weight.normal_(mean=0.0, std=0.15)
            model.filter_gate.fill_(0.7)
        elif arm in {"learned", "nonlinear", "shared"}:
            model.fir_control_module.weight.normal_(mean=0.0, std=0.15)
        elif arm in {"fixed_ma", "fixed_hp"}:
            model.fir_control_alpha.fill_(0.7)
    return model


def check(encoder: str, arm: str) -> tuple[float, float]:
    model = make_model(encoder, arm)
    with torch.inference_mode():
        a = model.encode(LEFT)
        b = model.encode(RIGHT)
    prefix_error = float((a[:, :PREFIX] - b[:, :PREFIX]).abs().max().item())
    suffix_change = float((a[:, PREFIX:] - b[:, PREFIX:]).abs().max().item())
    if prefix_error > ATOL:
        raise AssertionError(
            f"future leakage: encoder={encoder} arm={arm} "
            f"prefix_max_abs={prefix_error:.3e} > {ATOL:.1e}"
        )
    if suffix_change <= ATOL:
        raise AssertionError(
            f"non-operative test perturbation: encoder={encoder} arm={arm} "
            f"suffix_max_abs={suffix_change:.3e}"
        )
    return prefix_error, suffix_change


def main() -> int:
    arms = [
        "canonical",
        "legacy",
        "identity",
        "learned",
        "fixed_ma",
        "fixed_hp",
        "shared",
        "nonlinear",
    ]
    for encoder in ("transformer", "hstu"):
        for arm in arms:
            prefix_error, suffix_change = check(encoder, arm)
            print(
                f"PASS encoder={encoder:<11} arm={arm:<9} "
                f"prefix_max_abs={prefix_error:.3e} "
                f"suffix_max_abs={suffix_change:.3e}"
            )
    print(f"FIR CAUSALITY: PASS ({len(arms) * 2} active code-path checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
