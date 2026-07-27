"""Structural tests for PREREG_FIR_POINTWISE_V1."""
from __future__ import annotations

import hashlib
import os
import sys

import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_sasrec_sbert_pointwise_v1_frozen import SASRecSBERT
import run_sasrec_sbert_pointwise_v1_frozen as frozen_rsp
import fuse_ease_eval as fee


ARMS = ("identity", "learned", "pointwise")


def backbone_digest(model):
    h = hashlib.sha256()
    for key, value in sorted(model.state_dict().items()):
        if not key.startswith("fir_control_"):
            h.update(key.encode())
            h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def pointwise_delta(model, x):
    features = F.gelu(torch.matmul(
        x, model.fir_control_pointwise_projection.transpose(0, 1)))
    return model.fir_control_module(features)


def main():
    ids = torch.tensor([[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]])
    models = {}
    outputs = {}
    digests = {}
    params = {}
    grads = {}
    for arm in ARMS:
        torch.manual_seed(73022)
        model = SASRecSBERT(
            n_items=12, pad_id=12, max_seq_len=5, d_model=8,
            n_layers=1, n_heads=2, dropout=0.0, sbert_emb=None,
            fir_control=arm, fir_control_kernel=4)
        model.eval()
        models[arm] = model
        digests[arm] = backbone_digest(model)
        params[arm] = sum(
            p.numel() for n, p in model.named_parameters()
            if n.startswith("fir_control_") and p.requires_grad)
        with torch.no_grad():
            outputs[arm] = model.encode(ids).clone()
        if arm != "identity":
            model.zero_grad(set_to_none=True)
            model.encode(ids).square().sum().backward()
            gs = [p.grad for n, p in model.named_parameters()
                  if n.startswith("fir_control_") and p.requires_grad]
            grads[arm] = bool(gs and all(
                g is not None and torch.isfinite(g).all()
                and g.abs().sum() > 0 for g in gs))

    assert len(set(digests.values())) == 1, digests
    for arm in ARMS:
        assert torch.equal(outputs["identity"], outputs[arm]), (
            f"{arm} is not exact identity at initialization")
    assert params["learned"] == params["pointwise"] == 32, params
    assert all(grads.values()), grads

    p = models["pointwise"].fir_control_pointwise_projection
    assert torch.allclose(p @ p.T, torch.eye(4), atol=1e-6), p @ p.T

    # With nonzero weights, changing other positions cannot alter the selected
    # current-position delta. This tests the placebo operation itself, before
    # the shared sequence encoder is allowed to mix positions.
    point = models["pointwise"]
    with torch.no_grad():
        point.fir_control_module.weight.normal_(0, 0.2)
    x1 = torch.randn(2, 5, 8)
    x2 = torch.randn(2, 5, 8)
    x2[:, 3] = x1[:, 3]
    d1, d2 = pointwise_delta(point, x1), pointwise_delta(point, x2)
    assert torch.equal(d1[:, 3], d2[:, 3]), "pointwise arm mixed positions"

    # Positive control: a nonzero FIR can react to a changed preceding value
    # even when the current value is held fixed.
    learned = models["learned"]
    with torch.no_grad():
        learned.fir_control_module.weight.normal_(0, 0.2)
    xa = torch.zeros(1, 5, 8)
    xb = xa.clone()
    xb[:, 2] = 1.0
    xp_a = F.pad(xa.transpose(1, 2), (3, 0))
    xp_b = F.pad(xb.transpose(1, 2), (3, 0))
    fa = learned.fir_control_module(xp_a).transpose(1, 2)
    fb = learned.fir_control_module(xp_b).transpose(1, 2)
    assert not torch.equal(fa[:, 3], fb[:, 3]), "FIR positive control failed"

    # Exercise the exact evaluator reconstruction helper and strict state load.
    fee.rsp = frozen_rsp
    cfg = {
        "max_seq_len": 5, "d_model": 8, "n_layers": 1, "n_heads": 2,
        "dropout": 0.0, "fir_control": "pointwise",
        "fir_control_kernel": 4,
    }
    rebuilt = fee.build_model_from_config(
        cfg, n_items=12, pad_id=12, sbert_emb=None, proto_assign=None)
    rebuilt.load_state_dict(point.state_dict(), strict=True)

    print("FIR POINTWISE V1 STRUCTURAL TEST PASS")
    print("  exact identity at init: 3/3 arms")
    print("  matched backbone digest: 3/3 arms")
    print("  learned/pointwise trainable params: 32/32 (test scale)")
    print("  gradient-active: 2/2 active arms")
    print("  pointwise temporal independence + FIR positive control: PASS")
    print("  frozen evaluator reconstruction + strict state load: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
