# PREREG_FIR_V3 — E-A Nonsingular Matched-Arm FIR Factorial (FROZEN)

**Status: FROZEN at commit time. This file is committed BEFORE any run is
launched (lifecycle rule in `EXPERIMENT_PROGRAM.md`). Analysis and integration
happen ONLY through `_bestrec_run/adjudicate_fir_v3.py` and the frozen outcome
wordings in §6. Per the standing claim-boundary rule, results may only NARROW
the paper's claim set; any broadening requires a new frozen pre-registration.**

Registered: 2026-07-22 (Australia/Sydney date of the enclosing commit).
Author-operated automation; adjudication is mechanical (script committed
alongside this file, before launch).

## 1. Question

Does the learnable causal-FIR component — in a **nonsingular, gradient-active
parameterization** with **truly matched arms** — produce a detectable
NDCG@10 difference on Musical_Instruments at the frozen V2 configuration?

This is the component-attribution question the manuscript currently leaves
open (§3 initialization caveat; "FIR treatment package … attribution open").
The historical package arm is confounded: singular init (gate=0 AND delta
kernel ⇒ both gradients zero at step 0), weight-decay bootstrap, and unshared
initial states. E-A removes all three confounds.

## 2. Intervention (implemented at `_bestrec_run/run_sasrec_sbert.py`, flags `--fir-v3*`)

Parameterization: `x' = x + conv_Δ(x)`, depthwise causal Conv1d
(groups = d_model, left-pad K−1, no bias), **Δ = 0 at init**.

- Exact identity at step 0 (verified property).
- Gradient-active at the zero point: ∂L/∂Δ ≠ 0 from step 0 — no gate, no
  weight-decay bootstrap (verified property).
- The **control arm registers the SAME module frozen at 0**, so both arms share
  parameter registration order, RNG consumption, and (per seed) the exact same
  initial state (verified property; enforced per run by `init_state_sha256`).

## 3. Design (frozen)

Three arms × eight seeds = 24 runs, Musical_Instruments 5-core LLOO,
full-catalog evaluation (train+val masked), the frozen V2-ls02 stack
(hstu encoder, d=64, 4 layers, 2 heads, dropout 0.5, 20 epochs, lr 1e-3
warmup_cosine, batch 256, chunked full softmax, label smoothing 0.2, pos_rab,
time_bias, text_sim_bias, text_prototypes 512, max_seq_len 50) **without**
the legacy `--causal-filter`; kernel K = 16 (the historical primary length).
The driver constructs every command mechanically from the frozen reference
config `results_MI_V2_ls02_filter16_seed20260608.json` (excluding only
`causal_filter`, `filter_kernel`, `seed`, `out`) so no argument is
hand-transcribed.

| Arm | `--fir-v3` | `--fir-v3-wd` | Meaning |
|---|---|---|---|
| A0 `a0ident` | `frozen` | `backbone` | identity control (taps frozen at 0) |
| A1 `a1learned` | `learned` | `backbone` | learned taps, tap decay = backbone 1e-5 |
| A2 `a2learnedwd0` | `learned` | `zero` | learned taps, taps excluded from decay |

Seeds (frozen, fresh — never used in any prior result file):
20260713, 20260714, 20260715, 20260716, 20260717, 20260718, 20260719, 20260720.
Same eight seeds in every arm (common random numbers; per-seed shared init is
real by construction and verified by hash equality).

Output files: `_bestrec_run/results_MI_FIRV3_{arm}_seed{seed}.json`.
The driver never overwrites an existing results file (resume = skip).

## 4. Endpoint and analysis (frozen)

- **Primary endpoint:** `best_test["NDCG@10"]` (test NDCG@10 at the
  best-by-validation epoch), one number per run.
- **Primary contrast:** A1 − A0. **Secondary:** A2 − A0, A2 − A1.
- **Test:** two-sided Welch t on the 8-vs-8 per-arm endpoint values;
  **Holm correction across the three contrasts** (one family). α = 0.05.
- **95% Welch CIs** reported for all three contrasts.
- **Pre-specified equivalence margin (primary contrast only): ±0.0008
  NDCG@10** — 25% of the historical MI package-arm combined lift (+0.0032).
  Rationale: a FIR-specific effect smaller than a quarter of the package
  effect cannot rescue a component-level story even if real.
- **MDE note (design honesty):** with the historical MI seed SD ≈ 0.0004,
  8v8 Welch at α=.05 has ≈80% power for a true |Δ| ≈ 0.0006.
- **Paired-by-seed sensitivity:** mean of per-seed (A1−A0) differences with a
  paired t — **descriptive only**, never confirmatory (shared init is exact,
  but CUDA nondeterminism decouples trajectories after step 0).
- No interim looks: adjudication runs once, after all 24 files exist.

## 5. Integrity gates (adjudicator-enforced, run refused otherwise)

1. Exactly the 24 declared files exist; each config echoes the declared arm,
   kernel 16, category Musical_Instruments, epochs 20.
2. For every seed, all three arms report the **same `init_state_sha256`**.
3. A0 reports `fir_v3_final_l2 == 0` (taps never moved).
4. Endpoint values are read mechanically from `best_test["NDCG@10"]`; no
   hand-entered numbers.

## 6. Frozen outcome wordings (the ONLY sentences that may enter the paper)

- **[W-POS] Holm-significant positive primary contrast:** "In the nonsingular
  matched-arm replication (E-A, 8 seeds/arm, shared verified initial states),
  learned FIR taps produced a Holm-significant NDCG@10 difference of
  {est} [{ci}] over the identity control on Musical_Instruments at the frozen
  V2 configuration. This supports a FIR-specific component within the
  historical package-arm difference; it does not retroactively decompose the
  historical package estimate, whose arms were not initialization-matched."
- **[W-NEG] Holm-significant negative primary contrast:** as W-POS with
  "produced a Holm-significant NDCG@10 *deficit* of {est} [{ci}] relative to
  the identity control", plus: "This is evidence against a beneficial
  FIR-specific component at this configuration."
- **[W-EQUIV] non-significant AND primary 95% CI ⊆ (−0.0008, +0.0008):**
  "In the nonsingular matched-arm replication (E-A), the learned-FIR arm was
  statistically indistinguishable from the identity control within the
  pre-specified ±0.0008 margin ({est} [{ci}]). The historical package-arm
  difference therefore cannot be attributed to the FIR component at this
  configuration; component attribution for the historical stack remains open
  and the package-arm framing stands."
- **[W-INC] otherwise:** "The E-A replication was inconclusive at the
  available precision ({est} [{ci}]; pre-specified margin ±0.0008); the
  package-arm framing stands unchanged."
- A2 results enter only as weight-decay-sensitivity commentary attached to
  whichever wording above fires, never as a standalone claim.
- Under no outcome does any wording revive component-level causal language
  for the HISTORICAL runs, alter the two counted comparisons, or create a new
  cross-category claim.

## 7. Budget and operations

≈24 × 10 min ≈ 4 h wall-clock, strictly one GPU job at a time (sequential
driver `_bestrec_run/run_ea_fir_v3.py`; `nvidia-smi` checked before start;
driver skips completed outputs, so it is resumable across loop ticks).
Diagnostics recorded per run: `init_state_sha256`, final tap L2, per-lag
mean |tap| profile, full validation history.
