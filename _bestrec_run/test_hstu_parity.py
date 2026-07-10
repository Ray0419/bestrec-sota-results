#!/usr/bin/env python
"""Numerical parity test: our HSTU reimplementation vs the reference implementation.

WHAT IS COMPARED
  OURS : class HSTULayer
         _bestrec_run/run_sasrec_sbert.py  (class at lines 240-318;
         __init__ 260-287, forward 289-318; line numbers as of 2026-07-10)
  REF  : class SequentialTransductionUnitJagged (+ module-level function
         _hstu_attention_maybe_from_cache)
         external/HSTU-BLaIR/generative_recommenders/research/modeling/
         sequential/hstu.py (STU class lines 227-445, attention fn lines
         151-224, RelativePositionalBias lines 67-85), commit
         40a27879ec22648657b5abc77915a7cc88c66cfd of
         https://github.com/snapfinger/HSTU-BLaIR. The file carries Meta
         Platforms' Apache-2.0 header and is the research-mode ("Section
         4.1.1") HSTU implementation of Zhai et al., ICML'24
         (arXiv:2402.17152).

REFERENCE CONFIG USED (the published HSTU pointwise path)
  linear_config="uvqk", linear_activation="silu",
  normalization="rel_bias", concat_ua=False, dropout 0, eval mode.
  d_model D=32, num_heads H=2, attention_dim = linear_dim = D/H = 16
  (our HSTULayer ties d_qk = d_v = D/H; the reference allows them to differ,
  so we instantiate the reference at the tied point).

WEIGHT MIRRORING (reference -> ours)
  ref._uvqk               (D, 4D)  -> ours.uvqk.weight (4D, D) TRANSPOSED
                                      (ref computes x @ W, nn.Linear computes
                                       x @ W.T; split order u,v,q,k and the
                                       head-major per-head layout are already
                                       identical on both sides, so no column
                                       permutation is needed)
  (ref uvqk has NO bias)            -> ours.uvqk.bias   set to 0
  ref._o.weight           (D, D)   -> ours.out.weight   copied as-is
  ref._o.bias             (D,)     -> ours.out.bias     copied as-is
  ref layer norms are NON-AFFINE F.layer_norm (hstu.py lines 277-283)
                                    -> ours.norm_in/.norm_attn affine set to
                                       identity (weight=1, bias=0)
  ref eps = 1e-6 (hstu.py line 241) -> ours .eps attribute set to 1e-6 for the
                                       aligned runs (nn.LayerNorm default is
                                       1e-5; the default-eps effect is
                                       quantified separately in case C).

MASK / NORMALIZATION SEMANTICS (verified identical)
  ref: invalid_attn_mask = 1.0 - triu(ones, diagonal=1)  (hstu.py 627-639,
       709) — lower-triangular-inclusive KEEP mask, multiplied in after
       silu(qk)/n (hstu.py 212-213), n = mask.size(-1) fixed.
  ours: `keep` lower-triangular KEEP mask, multiplied in before /L
       (run_sasrec_sbert.py 314-315), L = seq len fixed.
  For a {0,1} float mask, (silu(s)/n)*m == (silu(s)*m)/n exactly in IEEE-754,
  and n == L here, so the two orderings are numerically identical.

FBGEMM NOTE
  The reference research code is plain PyTorch math, but its jagged<->dense
  padding plumbing calls torch.ops.fbgemm.{jagged_to_padded_dense,
  dense_to_jagged}. fbgemm_gpu is not installed (Windows/CPU), so this test
  registers exact pure-PyTorch fallbacks for those two ops. They are DATA
  MOVEMENT only (pad / unpad); with equal-length sequences (offsets [0,L,2L])
  they reduce to reshapes and are exact. No reference MATH is replaced: the
  reference forward() runs its own unmodified lines.

SCOPE
  This test covers the core HSTU block: input layer norm, fused uvqk
  projection + silu, pointwise silu(qk+rab)*mask/n attention, attn layer
  norm, elementwise-u gating, output projection, residual. Out of scope
  (external to the block on both sides): input feature preprocessors /
  positional embeddings, output postprocessors, multi-block stacking (a plain
  loop), incremental-decode cache path (delta_x_offsets), and variable-length
  jagged batching (ours consumes fixed-length right-padded batches). The
  relative-attention-bias PATHWAY is covered by feeding the same
  RelativePositionalBias output to both sides (case B).

RUN
  _bestrec_run/.venv/Scripts/python _bestrec_run/test_hstu_parity.py
  CPU-only; no CUDA calls are made.
"""
from __future__ import annotations

import os
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))          # _bestrec_run
ROOT = os.path.dirname(HERE)                               # repo root

# ---------------------------------------------------------------------------
# fbgemm data-movement fallbacks (see FBGEMM NOTE in the module docstring).
# Registered BEFORE importing the reference module. If a real fbgemm_gpu is
# installed, its ops are used instead and nothing is registered.
# ---------------------------------------------------------------------------
_FBGEMM_LIB = None  # keep a module-global ref: a GC'd Library deregisters ops


def _register_fbgemm_fallbacks() -> None:
    global _FBGEMM_LIB
    try:
        torch.ops.fbgemm.jagged_to_padded_dense  # noqa: B018  (probe)
        return  # real fbgemm available; use it
    except AttributeError:
        pass

    lib = torch.library.Library("fbgemm", "DEF")
    lib.define(
        "jagged_to_padded_dense(Tensor values, Tensor[] offsets, "
        "int[] max_lengths, float padding_value=0.0) -> Tensor"
    )
    lib.define(
        "dense_to_jagged(Tensor dense, Tensor[] x_offsets, int? total_L=None)"
        " -> (Tensor, Tensor[])"
    )

    def jagged_to_padded_dense(values, offsets, max_lengths, padding_value=0.0):
        off = offsets[0].long()
        n = int(max_lengths[0])
        B = off.numel() - 1
        out = values.new_full((B, n) + tuple(values.shape[1:]), padding_value)
        for b in range(B):
            s, e = int(off[b]), int(off[b + 1])
            out[b, : e - s] = values[s:e]
        return out

    def dense_to_jagged(dense, x_offsets, total_L=None):
        off = x_offsets[0].long()
        B = off.numel() - 1
        vals = torch.cat(
            [dense[b, : int(off[b + 1] - off[b])] for b in range(B)], dim=0
        )
        return vals, list(x_offsets)

    lib.impl("jagged_to_padded_dense", jagged_to_padded_dense,
             "CompositeExplicitAutograd")
    lib.impl("dense_to_jagged", dense_to_jagged, "CompositeExplicitAutograd")
    _FBGEMM_LIB = lib


_register_fbgemm_fallbacks()

# ---------------------------------------------------------------------------
# Imports of both implementations (unmodified).
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(ROOT, "external", "HSTU-BLaIR"))
sys.path.insert(0, HERE)

from generative_recommenders.research.modeling.sequential.hstu import (  # noqa: E402
    RelativePositionalBias,
    SequentialTransductionUnitJagged,
    _hstu_attention_maybe_from_cache,
)
from run_sasrec_sbert import HSTULayer  # noqa: E402

# ---------------------------------------------------------------------------
# Test configuration (CPU, float32, dropout 0, eval mode).
# ---------------------------------------------------------------------------
D = 32          # embedding dim
H = 2           # heads
DH = D // H     # per-head dim; reference attention_dim = linear_dim = DH
B = 2           # batch
L = 8           # sequence length (all sequences full length -> jagged==dense)
TOL = 1e-5      # pass threshold on max abs diff (float32)


def stats(a: torch.Tensor, b: torch.Tensor):
    d = (a - b).abs()
    return d.max().item(), d.mean().item()


def build_reference(seed: int):
    torch.manual_seed(seed)
    rel_bias = RelativePositionalBias(max_seq_len=L)
    ref = SequentialTransductionUnitJagged(
        embedding_dim=D,
        linear_hidden_dim=DH,
        attention_dim=DH,
        dropout_ratio=0.0,
        attn_dropout_ratio=0.0,
        num_heads=H,
        linear_activation="silu",
        relative_attention_bias_module=rel_bias,
        normalization="rel_bias",
        linear_config="uvqk",
        concat_ua=False,
    )
    ref.eval()
    return ref, rel_bias


def build_ours_mirrored(ref: SequentialTransductionUnitJagged,
                        align_eps: bool = True) -> HSTULayer:
    ours = HSTULayer(d_model=D, n_heads=H, dropout=0.0, n_experts=0)
    with torch.no_grad():
        ours.uvqk.weight.copy_(ref._uvqk.t())   # (4D,D) <- (D,4D)^T
        ours.uvqk.bias.zero_()                  # reference has no uvqk bias
        ours.out.weight.copy_(ref._o.weight)
        ours.out.bias.copy_(ref._o.bias)
        ours.norm_in.weight.fill_(1.0)          # reference norms are
        ours.norm_in.bias.zero_()               # non-affine -> identity affine
        ours.norm_attn.weight.fill_(1.0)
        ours.norm_attn.bias.zero_()
    if align_eps:
        # nn.LayerNorm stores eps as a plain attribute; align to ref's 1e-6.
        # (No source modification: this is instance configuration.)
        ours.norm_in.eps = ref._eps
        ours.norm_attn.eps = ref._eps
    ours.eval()
    return ours


def main() -> int:
    assert not torch.cuda.is_initialized() or True  # never allocate CUDA below
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))

    ref, rel_bias = build_reference(seed=1234)
    ours = build_ours_mirrored(ref, align_eps=True)

    torch.manual_seed(4321)
    x = torch.randn(B, L, D, dtype=torch.float32)          # dense input
    xj = x.reshape(B * L, D)                               # jagged (full-len)
    offsets = torch.tensor([0, L, 2 * L], dtype=torch.int32)
    keep = 1.0 - torch.triu(torch.ones(L, L), diagonal=1)  # (L,L) keep mask,
    # identical construction to reference hstu.py lines 627-639 + 709.

    rows = []       # (name, max_abs, mean_abs)
    failures = []

    def record(name, a, b, tol=TOL):
        mx, mn = stats(a, b)
        rows.append((name, mx, mn))
        if mx > tol:
            failures.append((name, mx, tol))
        return mx, mn

    with torch.no_grad():
        # ============ CASE A: end-to-end block, no relative bias =========
        ref_out_a, _ = ref(
            x=xj, x_offsets=offsets, all_timestamps=None,
            invalid_attn_mask=keep,
        )
        our_out_a = ours(x, None, keep)
        record("A. end-to-end (no rab)", ref_out_a.view(B, L, D), our_out_a)

        # ============ CASE B: end-to-end with relative position bias =====
        # The same RelativePositionalBias instance drives both sides:
        # reference consumes it internally (hstu.py lines 210-211); ours
        # consumes its precomputed output as the additive `bias` argument.
        # RelativePositionalBias ignores timestamp VALUES (hstu.py line 80),
        # so a zeros tensor only serves to enable the bias branch.
        ts = torch.zeros(B, L, dtype=torch.int64)
        rab = rel_bias(ts)                                  # (1, L, L)
        ref_out_b, _ = ref(
            x=xj, x_offsets=offsets, all_timestamps=ts,
            invalid_attn_mask=keep,
        )
        our_out_b = ours(x, rab.unsqueeze(1), keep)         # (1,1,L,L) bias
        record("B. end-to-end (with rab)", ref_out_b.view(B, L, D), our_out_b)

        # ============ STAGE-WISE ISOLATION (case A input) =================
        # Reference stages use the reference's own bound methods/functions;
        # our stages recompose forward() lines 298-317 from ours' submodules
        # (validated below by an exact match against the real forward).
        # -- stage 1: input layer norm
        ref_n = ref._norm_input(xj)                         # hstu.py 277-278
        our_n = ours.norm_in(x)                             # run_...py 298
        record("  stage 1: norm_in", ref_n.view(B, L, D), our_n)

        # -- stage 2: fused uvqk projection + silu + split
        ref_g = F.silu(torch.mm(ref_n, ref._uvqk))          # hstu.py 322-324
        ru, rv, rq, rk = torch.split(
            ref_g, [DH * H, DH * H, DH * H, DH * H], dim=1) # hstu.py 327-336
        our_g = F.silu(ours.uvqk(our_n))                    # run_...py 299
        ou, ov, oq, ok = our_g.chunk(4, dim=-1)             # run_...py 300
        for nm, r_, o_ in (("u", ru, ou), ("v", rv, ov),
                           ("q", rq, oq), ("k", rk, ok)):
            record(f"  stage 2: uvqk split [{nm}]", r_.view(B, L, D), o_)

        # -- stage 3: pointwise silu attention (reference's own function)
        ref_attn, _, _ = _hstu_attention_maybe_from_cache(  # hstu.py 151-224
            num_heads=H, attention_dim=DH, linear_dim=DH,
            q=rq, k=rk, v=rv, cached_q=None, cached_k=None,
            delta_x_offsets=None, x_offsets=offsets, all_timestamps=None,
            invalid_attn_mask=keep, rel_attn_bias=rel_bias,
        )
        q_ = oq.view(B, L, H, DH).transpose(1, 2)           # run_...py 308-310
        k_ = ok.view(B, L, H, DH).transpose(1, 2)
        v_ = ov.view(B, L, H, DH).transpose(1, 2)
        scores = q_ @ k_.transpose(-2, -1)                  # run_...py 311
        a_ = F.silu(scores) * keep                          # run_...py 314
        a_ = a_ / L                                         # run_...py 315
        our_attn = (a_ @ v_).transpose(1, 2).reshape(B, L, D)  # run_...py 316
        record("  stage 3: attention output", ref_attn.view(B, L, D), our_attn)

        # -- stage 4: attn layer norm + elementwise u gate
        ref_gate = ru * ref._norm_attn_output(ref_attn)     # hstu.py 424
        our_gate = ours.norm_attn(our_attn) * ou            # run_...py 317
        record("  stage 4: norm_attn * u gate",
               ref_gate.view(B, L, D), our_gate)

        # -- stage 5: output projection + residual
        ref_fin = ref._o(ref_gate) + xj                     # hstu.py 426-435
        our_fin = x + ours.out(our_gate)                    # run_...py 317-318
        record("  stage 5: out proj + residual",
               ref_fin.view(B, L, D), our_fin)

        # -- recomposition sanity: staged pipelines == real forward outputs
        record("  (sanity) ref staged == ref.forward",
               ref_fin, ref_out_a, tol=0.0)
        record("  (sanity) ours staged == ours.forward",
               our_fin, our_out_a, tol=0.0)

        # ============ CASE C: eps sensitivity (informational) =============
        # Our layer's only differing numerical CONSTANT: nn.LayerNorm default
        # eps=1e-5 vs reference F.layer_norm eps=1e-6. Not asserted; reported
        # to quantify the effect of running ours at its default.
        ours_default_eps = build_ours_mirrored(ref, align_eps=False)
        our_out_c = ours_default_eps(x, None, keep)
        mx_c, mn_c = stats(ref_out_a.view(B, L, D), our_out_c)
        rows.append(("C. eps 1e-5 vs 1e-6 (informational)", mx_c, mn_c))

    print(f"torch {torch.__version__} | CPU | float32 | "
          f"D={D} H={H} B={B} L={L} | dropout=0 eval")
    print(f"reference commit 40a27879 (HSTU-BLaIR, Meta research hstu.py)")
    print("-" * 74)
    print(f"{'comparison':46s} {'max|diff|':>12s} {'mean|diff|':>12s}")
    print("-" * 74)
    for name, mx, mn in rows:
        print(f"{name:46s} {mx:12.3e} {mn:12.3e}")
    print("-" * 74)

    if failures:
        for name, mx, tol in failures:
            print(f"FAIL: {name}: max abs diff {mx:.3e} > tol {tol:.1e}")
        return 1
    print(f"PASS: all asserted stages agree within {TOL:.0e} "
          f"(cases A, B end-to-end; stages 1-5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
