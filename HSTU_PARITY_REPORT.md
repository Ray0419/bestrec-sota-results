# HSTU Reimplementation Numerical Parity Report

**Date:** 2026-07-10
**Purpose:** Convert the paper's "faithful pure-PyTorch HSTU reimplementation" claim from
assertion into executable evidence (novelty-audit finding N9,
`STRICT_NOVELTY_ORIGINALITY_AUDIT_2026-07-10.md`).
**Test:** `_bestrec_run/test_hstu_parity.py`
**Rerun:** `_bestrec_run/.venv/Scripts/python _bestrec_run/test_hstu_parity.py`
(CPU-only, float32, no CUDA calls; exit code 0 = pass.)

## What was compared

| Side | Code | Location |
|---|---|---|
| **Ours** | `class HSTULayer` | `_bestrec_run/run_sasrec_sbert.py` lines 240–318 (`__init__` 260–287, `forward` 289–318; line numbers as of the 2026-07-10 working tree) |
| **Reference** | `class SequentialTransductionUnitJagged` + `_hstu_attention_maybe_from_cache` + `RelativePositionalBias` | `external/HSTU-BLaIR/generative_recommenders/research/modeling/sequential/hstu.py` lines 227–445, 151–224, 67–85; causal-mask construction lines 627–639 and 709 |

The reference file is the research-mode HSTU of Zhai et al. (ICML'24, arXiv:2402.17152),
carrying Meta Platforms' Apache-2.0 copyright header, as vendored at commit
`40a27879ec22648657b5abc77915a7cc88c66cfd` of https://github.com/snapfinger/HSTU-BLaIR.
Its module docstring states it implements HSTU for "the traditional sequential recommender
setting (Section 4.1.1)" — i.e., the published block this parity test targets. It is plain
PyTorch math; only its jagged↔dense **padding plumbing** calls
`torch.ops.fbgemm.{jagged_to_padded_dense, dense_to_jagged}`. Since `fbgemm_gpu` is not
installed (Windows/CPU), the test registers exact pure-PyTorch fallbacks for those two ops
before import. They are data movement only (pad/unpad); with equal-length sequences
(offsets `[0, L, 2L]`) they reduce to reshapes and are exact. **No reference math was
replaced or copied — the reference module is imported unmodified and its own `forward()`
lines execute.**

Reference configuration used (the published HSTU pointwise path, and the block our layer
reimplements): `linear_config="uvqk"`, `linear_activation="silu"`,
`normalization="rel_bias"`, `concat_ua=False`, dropout 0, eval mode,
`embedding_dim=32`, `num_heads=2`, `attention_dim = linear_hidden_dim = 16`
(our layer ties d_qk = d_v = D/H; the reference is instantiated at that tied point).

## Weight mapping (reference → ours)

| Reference parameter | Shape | Ours | Transform |
|---|---|---|---|
| `_uvqk` (hstu.py 256–265; used as `x @ W`, no bias) | (D, 4D) | `uvqk.weight` (nn.Linear, computes `x @ W.T`) | **transpose** |
| — (reference uvqk has no bias) | — | `uvqk.bias` | set to 0 |
| `_o.weight` (hstu.py 270–274) | (D, H·d_v) | `out.weight` | identity copy |
| `_o.bias` | (D,) | `out.bias` | identity copy |
| non-affine `F.layer_norm` input norm (hstu.py 277–278) | — | `norm_in` (affine `nn.LayerNorm`) | weight←1, bias←0 |
| non-affine `F.layer_norm` attn norm (hstu.py 280–283) | — | `norm_attn` | weight←1, bias←0 |
| `_eps = 1e-6` (hstu.py 241, 275) | — | `.eps` attribute (default 1e-5) | set to 1e-6 for aligned runs; default quantified separately (case C) |

No column permutation is needed: both sides use split order **u, v, q, k** with
head-major per-head layout (`view(B, L, H, d_h)` on both sides), verified from
hstu.py 327–336 / 205–209 / 218–221 vs run_sasrec_sbert.py 300 / 308–310 / 316.

Mask/normalization semantics were verified identical before testing: the reference's
`invalid_attn_mask` is `1.0 − triu(ones, diagonal=1)` — a lower-triangular-inclusive
**keep** mask multiplied in after `silu(qk)/n` (hstu.py 212–213); ours multiplies the same
keep mask before `/L` (run_sasrec_sbert.py 314–315). For a {0,1} float mask these
orderings are exactly equal in IEEE-754, and `n = L` here.

## Input setup

`B=2, L=8, D=32, H=2`, float32, CPU, fixed seeds (1234 weights / 4321 inputs), identical
`randn` input fed dense to ours and flattened-jagged (`offsets=[0, 8, 16]`, all sequences
full length, so jagged ≡ dense) to the reference; identical full causal keep mask; dropout
0 and `eval()` on both sides. Case B feeds the **same** `RelativePositionalBias` module
instance to both sides: the reference consumes it internally (hstu.py 210–211); ours
receives its precomputed `(1, L, L)` output as the additive `bias` argument
(run_sasrec_sbert.py 312–313) — this exercises the rab-addition pathway itself.

## Numerical results

```
torch 2.11.0+cu128 | CPU | float32 | D=32 H=2 B=2 L=8 | dropout=0 eval
comparison                                        max|diff|   mean|diff|
A. end-to-end (no rab)                            0.000e+00    0.000e+00
B. end-to-end (with rab)                          0.000e+00    0.000e+00
  stage 1: norm_in                                0.000e+00    0.000e+00
  stage 2: uvqk split [u]                         0.000e+00    0.000e+00
  stage 2: uvqk split [v]                         0.000e+00    0.000e+00
  stage 2: uvqk split [q]                         0.000e+00    0.000e+00
  stage 3: attention output                       0.000e+00    0.000e+00
  stage 4: norm_attn * u gate                     0.000e+00    0.000e+00
  stage 5: out proj + residual                    0.000e+00    0.000e+00
  (sanity) ref staged == ref.forward              0.000e+00    0.000e+00
  (sanity) ours staged == ours.forward            0.000e+00    0.000e+00
C. eps 1e-5 vs 1e-6 (informational)               1.663e-02    3.367e-03
```
(stage 2 `[k]` also 0.000e+00; elided above for width.)

With weights mirrored and the LayerNorm eps constant aligned, outputs are **bitwise
identical** (max abs diff exactly 0.0) end-to-end and at every stage, with and without
the relative attention bias — far exceeding the ~1e-5 float32 target. The stage-wise
sanity rows confirm the staged decompositions reproduce each side's real `forward()`
bit-for-bit, so the stage attributions are valid.

**Case C (the only differing numerical constant):** our `nn.LayerNorm` default
`eps=1e-5` vs the reference's `1e-6`. At this random std-0.02 initialization the
attention output has variance ~1e-9–1e-8 (silu of near-zero scores, /L), so
`sqrt(var+eps)` is eps-dominated in `norm_attn` and the constant matters
(probe: `norm_attn` stage max diff 0.459, shrinking to 1.66e-2 at the block output after
gating and projection; `norm_in`, whose input has variance ~1, shows only 2.3e-5).
Setting eps to 1e-6 makes the difference exactly 0.0, proving the divergence is entirely
this one constant, not the math. The HSTU paper does not prescribe an eps; this is an
implementation constant, and the eps-dominated regime only arises when the pre-norm
activations are pathologically small (untrained std-0.02 weights); trained activations
have far larger variance, where the relative effect is O(eps/var).

## Parameterization differences that are not math differences

Ours is a strict superset parameterization of the reference at the tied configuration;
each item below has an exact reference-equivalent setting (used in the test):

1. **Affine LayerNorms** — ours has learnable γ, β; reference norms are non-affine.
   Reference = (γ=1, β=0) point.
2. **uvqk bias** — ours has a learnable bias (zero-initialized); reference `x @ _uvqk`
   has none. Reference = (bias=0) point.
3. **eps default** — 1e-5 vs 1e-6 (quantified above; our trained runs use 1e-5).
4. **Dropout placement** — reference applies dropout to the gated tensor before `_o`
   (hstu.py 426–433); ours after `out` (run_sasrec_sbert.py 318). Identity at p=0/eval;
   a training-time regularization-placement choice, not eval math. (The reference's
   `attn_dropout_ratio` is stored but never applied in its rel_bias path.)
5. **/n constant** — both divide `silu(qk)` by a *fixed global* constant (not per-row
   counts): reference uses its mask size (`max_seq_len + max_output_len` in their
   encoder), ours uses the padded length `max_seq_len`. Identical role and, in this
   test, identical value (n = L = 8).
6. **d_qk = d_v tie** — ours fixes both to D/H; the reference also supports untied dims.
7. **`concat_ua`** — ours implements only the reference default (`False`) path.
8. **Optional expert branch** — ours has an `n_experts` extension (disabled at 0 and
   zero-initialized ⇒ exact no-op; the test uses 0 and the paper's HSTU claim concerns
   the base layer).

Note: an earlier version of the `HSTULayer` class docstring wrongly described
`1/sqrt(d_h)` scaling and per-row-count normalization (the code never did either). The
docstring was corrected in the current working tree (run_sasrec_sbert.py 246–258) and
now states the authoritative no-scaling, fixed-1/L math that this test verifies; the
forward-comments (lines 292–296, 311–315) match the code exactly.

## Scoped out (external to the block on both sides)

- **Input feature preprocessors / positional embeddings and output postprocessors** —
  in the reference these are separate injected modules outside
  `SequentialTransductionUnitJagged`; ours likewise handles embeddings outside
  `HSTULayer`.
- **`RelativeBucketedTimeAndPositionBasedBias`** — ours takes the additive bias tensor
  as an input rather than owning a bias module; the bias-addition pathway itself is
  covered (case B) using the reference's `RelativePositionalBias` output on both sides.
- **Jagged variable-length batching** — ours consumes fixed-length right-padded dense
  batches; the reference's jagged plumbing is data movement around the same math
  (exact for the full-length sequences tested).
- **Incremental-decode cache path** (`delta_x_offsets`) and **multi-block stacking**
  (`HSTUJagged` is a plain loop over identical blocks).

## Verdict

**Parity demonstrated.** With the documented weight mapping (one transpose, zeroed
extra bias, identity affine norms) and the eps constant aligned, our `HSTULayer` and the
Meta research HSTU block (`SequentialTransductionUnitJagged`, uvqk/silu/rel_bias/
`concat_ua=False`) produce **bitwise-identical** float32 outputs on CPU — end-to-end and
at every intermediate stage (input norm, fused uvqk+silu split, pointwise silu attention
with causal mask and fixed 1/N normalization, attention norm + u-gating, output
projection + residual), both with and without a relative attention bias, with the
reference module imported unmodified and executing its own forward. The only numerical
deviation under our defaults is the LayerNorm eps constant (1e-5 vs 1e-6), quantified in
case C and reducible to exactly zero by aligning one scalar. "Faithful reimplementation
of the published HSTU block" is therefore no longer an assertion: it is demonstrated by
an executable test (`_bestrec_run/test_hstu_parity.py`), scoped precisely to the core
attention block, with all extra learnable degrees of freedom (affine norms, uvqk bias)
and configuration constants documented above.
