"""Fast structural tests for the Phase-3 causal-filter control arms."""
import hashlib
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_sasrec_sbert import SASRecSBERT


ARMS = ("identity", "learned", "fixed_ma", "fixed_hp", "shared", "nonlinear")


def digest_backbone(model):
    h = hashlib.sha256()
    for key, value in sorted(model.state_dict().items()):
        if not key.startswith("fir_control_"):
            h.update(key.encode())
            h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def main():
    backbones = {}
    outputs = {}
    grads = {}
    ids = torch.tensor([[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]])
    for arm in ARMS:
        torch.manual_seed(73021)
        model = SASRecSBERT(
            n_items=12, pad_id=12, max_seq_len=5, d_model=8,
            n_layers=1, n_heads=2, dropout=0.0, sbert_emb=None,
            fir_control=arm, fir_control_kernel=4)
        model.eval()
        backbones[arm] = digest_backbone(model)
        with torch.no_grad():
            outputs[arm] = model.encode(ids).clone()
        if arm != "identity":
            model.zero_grad(set_to_none=True)
            loss = model.encode(ids).square().sum()
            loss.backward()
            control_grads = [p.grad for n, p in model.named_parameters()
                             if n.startswith("fir_control_") and p.requires_grad]
            grads[arm] = bool(control_grads and all(
                g is not None and torch.isfinite(g).all() and g.abs().sum() > 0
                for g in control_grads))

    assert len(set(backbones.values())) == 1, backbones
    ref = outputs["identity"]
    for arm, value in outputs.items():
        assert torch.equal(ref, value), f"{arm} is not exact identity at init"
    assert all(grads.values()), grads
    print("FIR-CONTROL STRUCTURAL TEST PASS")
    print("  exact identity at init: 6/6 arms")
    print("  matched backbone digest: 6/6 arms")
    print("  gradient-active: 5/5 active arms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
