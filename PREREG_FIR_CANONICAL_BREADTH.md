# PREREG — Canonical causal-FIR breadth transfer (frozen before launch)

**Status:** FROZEN 2026-07-25, committed together with the mechanical adjudicator
`_bestrec_run/adjudicate_fir_canonical_breadth.py` and the driver
`_bestrec_run/run_fir_canonical_breadth.py` **before any run of this campaign
exists** (committed-before-existence standard, §5.3 disclosure (ii)). Endpoint
files `results_*_FIRCANON_*` are gitignored until adjudication.

## Question
Does the **canonical** causal FIR residual — the nonsingular, gradient-active,
identity-initialized `--fir-v3` parameterization already isolated on
Musical_Instruments (PREREG_FIR_V3 / E-A, verdict W-POS: +0.002265
[+0.001928, +0.002602], Holm-sig) — also improve test NDCG@10 over a
matched-initialization identity control on categories **not used in the filter's
development**, under **one frozen configuration transferred with zero
per-category tuning**?

This campaign is what upgrades the cross-category FIR evidence from the *legacy
zero-gated package* (the historical breadth campaign, whose arms were not
initialization-paired and whose parameterization was singular) to the **canonical
gradient-active form**.

## Arms (per category, per seed)
- **a0ident**  `--fir-v3 frozen` — the depthwise FIR taps are held at their Δ=0
  initialization (exact identity; no filtering). Control.
- **a1learned** `--fir-v3 learned` — the canonical gradient-active FIR
  (Δ=0 at init, exact identity at init, nonzero gradient on the first task
  update, strictly left-causal pad, no gate). Treatment.

The FIR layer is the **only** treatment difference. Both arms of a
(category, seed) are constructed from one shared backbone initialization; the
adjudicator verifies **per-(category, seed) `init_state_sha256` equality** across
the two arms and rejects otherwise. Pairing is therefore legitimate.

## Frozen configuration (zero per-category tuning)
Mechanically derived by `run_fir_canonical_breadth.py` from the frozen MI primary
reference `results_MI_V2_ls02_filter16_seed20260608.json`, excluding only the
legacy filter component (`causal_filter`, `filter_kernel`), the fir-v3 flags (set
per arm), the positional `category`, and per-run fields (`seed`, `out`). Nothing
category-specific is tuned. Key pins: **kernel K = 16**, `--fir-v3-wd backbone`
(E-A showed weight-decay treatment is immaterial: A2−A1 p = 0.95), label-smoothing
base ε = 0.2, **epochs = 20**, best-by-validation NDCG@10 checkpoint selection.

## Categories (not used in the filter's development)
- **Industrial_and_Scientific**
- **CDs_and_Vinyl**

(The MI development category is not re-counted here; it is covered by E-A. An
additional genuinely-untouched AR2023 category is a separate, later pre-declared
extension, pending split/text-cache availability — not part of this frozen
family.)

## Seeds (fresh, never inspected)
20260810, 20260811, 20260812, 20260813, 20260814, 20260815, 20260816, 20260817
(8 matched-init pairs per category).

## Analysis (frozen)
- **Primary endpoint:** test NDCG@10, best-by-validation. Randomized unit = seed.
- **Primary test (per category):** paired-by-seed difference d = a1learned −
  a0ident; two-sided paired Student-t 95% CI (df = 7).
- **Robustness:** independent-arm Welch, and an exact two-sided sign test.
- **Multiplicity:** Holm correction across the two per-category primary paired
  p-values.
- **Secondary metrics (supportive, not gating):** HR@10, MRR@10, and the full
  HR/NDCG/MRR@{5,10,20,50} family.

## Decision rule (frozen)
Per-category **PASS** iff: paired 95% CI excludes 0 **and** direction positive
**and** Holm-adjusted paired p < 0.05.

Family verdict:
- **CANON-BREADTH-POS** — both categories PASS.
- **CANON-BREADTH-PARTIAL** — exactly one PASSes.
- **CANON-BREADTH-NULL** — neither PASSes.

A negative or partial outcome is reported with **equal prominence** to a positive
one and **narrows** the manuscript claim accordingly. No practical-significance
threshold is derived from these results.

## Claim wording (frozen; what a PASS licenses, nothing broader)
> On each PASSing category, the canonical gradient-active causal-FIR arm's
> matched-initialization improvement over the Δ=0 identity control on test NDCG@10
> is positive with a Holm-corrected 95% CI excluding zero, under one frozen
> configuration transferred with zero per-category tuning.

This is an **internal filter-vs-identity contrast**. It is **not** a comparison
against any published number, **not** SOTA of any kind, **not** a paired/
distributional superiority claim over any external system. The canonical
parameterization's own cross-category confirmation is exactly this family; the
legacy zero-gated package results remain reported as package-level.

## Integrity gates (enforced by the committed adjudicator, fail-closed)
Exact seed set and arm set; frozen-config match (kernel/category/epochs/seed; no
legacy `causal_filter`); control-arm taps remain at L2 = 0; per-(category, seed)
init-hash equality across arms; adjudicator scans its own output for forbidden
tokens (SOTA/superiority/comparator) and fails closed. Verbatim verdict written to
`fir_canonical_breadth_adjudication.json`.
