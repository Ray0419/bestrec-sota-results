#!/usr/bin/env python
"""Pure-PyTorch fallbacks for the fbgemm ops used by the HSTU-BLaIR research path.

WHY THIS EXISTS
  The reference implementation (external/HSTU-BLaIR, commit 40a27879) calls
  three `torch.ops.fbgemm.*` operators. fbgemm_gpu has no Windows wheels and
  its pinned version (0.6.0, paired with torch 2.2.2) predates sm_120 GPUs,
  so we register pure-PyTorch implementations under the same operator names.

WHAT IS (AND IS NOT) SHIMMED
  Exhaustive inventory of fbgemm/torchrec usage under
  external/HSTU-BLaIR/generative_recommenders/research/ (grep 2026-07-11):

    torch.ops.fbgemm.asynchronous_complete_cumsum   (lengths -> offsets)
    torch.ops.fbgemm.jagged_to_padded_dense         (jagged rows -> padded [B,N,...])
    torch.ops.fbgemm.dense_to_jagged                (padded [B,N,...] -> jagged rows)

  Nothing else. torchrec is NOT imported anywhere under research/ (only under
  dlrm_v3/ and modules/, which the research trainer never imports).
  `import fbgemm_gpu` appears only in their main.py, which we do not use
  (our launcher calls generative_recommenders.research.trainer.train.train_fn
  directly).

  All three ops are DATA MOVEMENT only (cumulative sum of lengths; pad/unpad
  between jagged and dense layouts). No model math (matmul, activation,
  normalization, attention, loss) is replaced: those run in the reference
  repo's own unmodified lines.

AUTOGRAD
  Registered with dispatch key "CompositeImplicitAutograd", so autograd
  differentiates through the pure-torch gather/scatter implementation.
  install() runs a self-test (forward parity vs. a slow loop reference +
  gradient flow) unless skip_selftest=True.

USAGE
  import fbgemm_shims
  fbgemm_shims.install()          # no-op if a real fbgemm_gpu is importable

Only standard PyTorch is used. CPU and CUDA both supported.
"""
from __future__ import annotations

from typing import List, Optional

import torch

_FBGEMM_LIB = None  # keep module-global ref: a GC'd Library deregisters ops


# ---------------------------------------------------------------------------
# Implementations (vectorized; autograd flows through index ops).
# ---------------------------------------------------------------------------

def _asynchronous_complete_cumsum(t_in: torch.Tensor) -> torch.Tensor:
    """fbgemm semantics: complete (inclusive-with-leading-zero) cumsum.

    [L0, L1, ..., L_{B-1}] -> [0, L0, L0+L1, ..., sum(L)]  (dtype preserved).
    Research path only passes 1-D lengths.
    """
    assert t_in.dim() == 1, f"only 1-D supported, got {t_in.dim()}-D"
    out = torch.zeros(t_in.numel() + 1, dtype=t_in.dtype, device=t_in.device)
    torch.cumsum(t_in, dim=0, out=out[1:])
    return out


def _valid_mask(offsets: torch.Tensor, n: int, device) -> torch.Tensor:
    """[B, n] bool: position p of row b is a real (non-pad) element."""
    off = offsets.to(torch.long)
    lengths = (off[1:] - off[:-1]).clamp(min=0, max=n)  # truncate rows > n
    pos = torch.arange(n, device=device).unsqueeze(0)   # [1, n]
    return pos < lengths.unsqueeze(1)                   # [B, n]


def _jagged_to_padded_dense(
    values: torch.Tensor,
    offsets: List[torch.Tensor],
    max_lengths: List[int],
    padding_value: float = 0.0,
) -> torch.Tensor:
    """values: [sum_L, ...]; offsets: [B+1]; -> [B, N, ...] padded/truncated."""
    off = offsets[0].to(torch.long)
    B = off.numel() - 1
    n = int(max_lengths[0])
    valid = _valid_mask(off, n, values.device)                    # [B, n]
    pos = torch.arange(n, device=values.device).unsqueeze(0)      # [1, n]
    src_idx = (off[:-1].unsqueeze(1) + pos)[valid]                # [K]
    out = values.new_full((B, n) + tuple(values.shape[1:]), padding_value)
    out[valid] = values.index_select(0, src_idx)                  # differentiable
    return out


def _dense_to_jagged(
    dense: torch.Tensor,
    x_offsets: List[torch.Tensor],
    total_L: Optional[int] = None,
):
    """dense: [B, N, ...]; offsets: [B+1]; -> (values [sum_L, ...], offsets)."""
    off = x_offsets[0].to(torch.long)
    n = dense.size(1)
    valid = _valid_mask(off, n, dense.device)  # [B, n]
    values = dense[valid]                      # row-major -> concat order; differentiable
    return values, list(x_offsets)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def _real_fbgemm_present() -> bool:
    try:
        torch.ops.fbgemm.jagged_to_padded_dense  # noqa: B018 (probe)
        return True
    except AttributeError:
        return False


def install(skip_selftest: bool = False) -> str:
    """Register the three ops under torch.ops.fbgemm. Returns a status string."""
    global _FBGEMM_LIB
    if _real_fbgemm_present():
        return "real fbgemm ops present; shims NOT installed"
    if _FBGEMM_LIB is not None:
        return "shims already installed"

    lib = torch.library.Library("fbgemm", "DEF")
    lib.define("asynchronous_complete_cumsum(Tensor t_in) -> Tensor")
    lib.define(
        "jagged_to_padded_dense(Tensor values, Tensor[] offsets, "
        "int[] max_lengths, float padding_value=0.0) -> Tensor"
    )
    lib.define(
        "dense_to_jagged(Tensor dense, Tensor[] x_offsets, int? total_L=None)"
        " -> (Tensor, Tensor[])"
    )
    # CompositeImplicitAutograd: the python body is traced by autograd, so
    # gradients flow through index_select / masked assignment / masked select.
    lib.impl("asynchronous_complete_cumsum", _asynchronous_complete_cumsum,
             "CompositeImplicitAutograd")
    lib.impl("jagged_to_padded_dense", _jagged_to_padded_dense,
             "CompositeImplicitAutograd")
    lib.impl("dense_to_jagged", _dense_to_jagged,
             "CompositeImplicitAutograd")
    _FBGEMM_LIB = lib

    if not skip_selftest:
        _selftest()
    return "pure-PyTorch fbgemm shims installed (3 ops) + selftest passed"


# ---------------------------------------------------------------------------
# Self-test: forward parity vs. slow loop reference; gradient flow.
# ---------------------------------------------------------------------------

def _loop_j2pd(values, off, n, pad):
    off = off.long()
    B = off.numel() - 1
    out = values.new_full((B, n) + tuple(values.shape[1:]), pad)
    for b in range(B):
        s, e = int(off[b]), int(off[b + 1])
        take = min(e - s, n)
        out[b, :take] = values[s : s + take]
    return out


def _loop_d2j(dense, off):
    off = off.long()
    B = off.numel() - 1
    return torch.cat([dense[b, : int(off[b + 1] - off[b])] for b in range(B)], dim=0)


def _selftest() -> None:
    devices = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])
    g = torch.Generator().manual_seed(0)
    for dev in devices:
        for dtype_off in (torch.int32, torch.int64):
            lengths = torch.tensor([3, 0, 7, 5, 1], dtype=dtype_off, device=dev)
            off = torch.ops.fbgemm.asynchronous_complete_cumsum(lengths)
            assert off.dtype == dtype_off and off.device.type == dev
            assert off.tolist() == [0, 3, 3, 10, 15, 16]

            total = int(off[-1])
            n = 6  # forces truncation of the length-7 row and padding of others
            vals = torch.randn(total, 4, generator=g).to(dev).requires_grad_(True)
            padded = torch.ops.fbgemm.jagged_to_padded_dense(vals, [off], [n], 0.0)
            ref = _loop_j2pd(vals.detach(), off, n, 0.0)
            assert torch.equal(padded.detach(), ref), "j2pd mismatch"
            padded.sum().backward()
            gr = vals.grad
            assert gr is not None, "no grad through jagged_to_padded_dense"
            # rows kept (first min(len,n) of each sequence) get grad 1, else 0
            expect = torch.zeros_like(gr)
            offl = off.long()
            for b in range(offl.numel() - 1):
                s, e = int(offl[b]), int(offl[b + 1])
                expect[s : s + min(e - s, n)] = 1.0
            assert torch.equal(gr, expect), "wrong grad pattern (j2pd)"

            # dense_to_jagged (consistent offsets, lengths <= N)
            lengths2 = torch.tensor([2, 4, 0, 3], dtype=dtype_off, device=dev)
            off2 = torch.ops.fbgemm.asynchronous_complete_cumsum(lengths2)
            dense = torch.randn(4, 5, 3, generator=g).to(dev).requires_grad_(True)
            jag, off_out = torch.ops.fbgemm.dense_to_jagged(dense, [off2])
            assert torch.equal(jag.detach(), _loop_d2j(dense.detach(), off2))
            assert torch.equal(off_out[0], off2)
            jag.sum().backward()
            gd = dense.grad
            assert gd is not None, "no grad through dense_to_jagged"
            for b, L in enumerate([2, 4, 0, 3]):
                assert torch.equal(
                    gd[b, :L], torch.ones_like(gd[b, :L])
                ) and torch.equal(gd[b, L:], torch.zeros_like(gd[b, L:]))

            # int64 values path (candidate_index uses ids)
            ids = torch.arange(1, total + 1, dtype=torch.int64, device=dev).unsqueeze(-1)
            pid = torch.ops.fbgemm.jagged_to_padded_dense(ids, [off], [n], 0)
            assert torch.equal(pid, _loop_j2pd(ids, off, n, 0))

            # round-trip: j2pd then d2j is identity when lengths <= n
            vals3 = torch.randn(int(off2[-1]), 7, generator=g).to(dev)
            rt = torch.ops.fbgemm.dense_to_jagged(
                torch.ops.fbgemm.jagged_to_padded_dense(vals3, [off2], [5], 0.0),
                [off2],
            )[0]
            assert torch.equal(rt, vals3), "round-trip failed"


if __name__ == "__main__":
    print(install())
    print("fbgemm shim self-test: PASS (cpu%s)" %
          (" + cuda" if torch.cuda.is_available() else ""))
