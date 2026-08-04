# Response to the Strict Novelty/Originality Audit (2026-07-10)

Audit: `STRICT_NOVELTY_ORIGINALITY_AUDIT_2026-07-10.md`. Verdict accepted in full: the **result
artifact stays approved** (narrow wording), the **framing overclaimed novelty**. We adopt the
audit's reframe rather than arguing with it — the fastest path is narrowing claims until every
sentence survives contact with FMLP-Rec, BSARec, TIGER, BLaIR, UniSRec, DropoutNet, CLCRec,
MELT, HSTU-BLaIR, ReSID, ChronoSID.

## Point-by-point

| Finding | Resolution |
|---|---|
| **N1** "spectral" is marketing | Renamed everywhere to **"strictly causal FIR temporal filter"**; "spectral" survives only as frequency-response *analysis* language. Title retitled per fix-plan #1. |
| **N2** novelty is a narrow adaptation | Adopted verbatim: explicit "what is new / what is not new" paragraph (not new: filtering sequential representations, frequency motivation, oversmoothing framing; new: the leak-free left-causal FIR realization in an HSTU-style stack under the all-position objective). |
| **N3** unfair to FMLP/BSARec | "Omit" wording replaced with the audit's neutral formulation (bidirectional in their original formulations; our loss requires a causal realization). |
| **N4** "cannot represent" unsupported | Deleted; replaced with "an explicit local temporal bias the baseline does not learn as reliably in our low-capacity setting". |
| **N5** BSARec theorem over-extended | Scoped to vanilla self-attention; HSTU extension stated as our hypothesis, tested empirically. |
| **N6** TAPE oversold | Demoted to a secondary ablation ("simple soft text-prototype additive capacity term… small but not headline gain"); exact-combination novelty sentence removed. |
| **N7** "law" overstated | Renamed to **"dataset-conditional long-tail pattern"** everywhere (title included). |
| **N8** causal language too strong | "confirmed/refuted/partial cause" → intervention-scoped wording ("supported as a driver by controlled thinning interventions", "consistent with a partial causal role under the intervention's assumptions"). |
| **N9** "faithful HSTU" unproven | **ELIMINATED, not conceded:** the reference repo's research-path HSTU is pure PyTorch and runs on CPU — `_bestrec_run/test_hstu_parity.py` mirrors weights/inputs into both blocks and shows **EXACT agreement (max abs diff 0.0) at every stage**; sole difference anywhere is the LayerNorm eps default (constant; 0.0 when equalized). "Faithful" is now demonstrated by executable test (`HSTU_PARITY_REPORT.md`); the softened wording is superseded. |
| **N10** self-contradiction on novelty | Unified: "We do not claim a wholly new recommender architecture. Our architectural additions are deliberately small…" |
| **N11** not submission-clean | `PAPER_SUBMISSION.md` created: status logs, drafting notes, changelog, and audit-narrative prose stripped; authors anonymized; UTF-8 verified (the mojibake was a console-rendering artifact — the file is valid UTF-8; PDF rendering to be checked at typesetting). |
| **N12** negative map unequally powered | Caption + paragraph added: only multi-seed pre-declared negatives carry confirmatory weight; the rest are labeled exploratory documentation; per-probe seed counts stated. |
| **N13** novelty too thin for top-tier | Accepted honestly. Two responses: (a) **new comparator ablations running** (see below) to strengthen the FIR contribution empirically; (b) target framing shifted to what the audit itself says is legitimate — a careful empirical + engineering + reproducibility paper (its five-point reframe adopted as the contribution list). Venue expectations set accordingly (strong reproducibility-track / empirical-track fit; not pitched as a new-algorithm paper). |

## Fix-plan #4 — comparator ablations (EXECUTED, not just promised)

Two new arms, each isolating exactly ONE design element of the causal FIR filter, on the MI k8
confirmation stack, 5 seeds each (20260608–12):

1. `--filter-fixed-avg`: kernel FROZEN at a uniform causal moving average (pure low-pass,
   non-learnable); zero-init gate stays learnable → tests whether kernel *learnability* matters.
2. `--filter-no-gate`: gate FROZEN at 1 (kernel delta-init keeps init a no-op); kernel stays
   learnable → tests whether the zero-init *gate parameterization* matters.

Results appended below when complete. The remaining audit-suggested comparators (a matched
causalized bidirectional filter; a BSARec-style Fourier block adapted to this protocol) are
recorded as future work in the Limitations section (the former is definitionally close to our
filter; the latter is a nontrivial reimplementation we scope out honestly).

## Results of the comparator ablations

**COMPLETE (5 seeds/arm, MI k8 stack; each arm changes exactly one design element):**

| arm | NDCG@10 (5-seed) | gain vs no-filter (LS-only 0.03913 ± 0.00015) |
|---|---|---|
| REAL: learnable kernel + zero-init gate | 0.04138 ± 0.00053 | +0.00225 |
| ABL-A: kernel FROZEN at causal moving average | 0.04046 ± 0.00022 | +0.00133 (~59% of the gain) |
| ABL-B: learnable kernel, gate FROZEN at 1 | 0.04127 ± 0.00046 | +0.00214 (≈ full) |

**Verdicts:** (1) **kernel learnability is load-bearing** — generic fixed smoothing recovers barely
half the effect; the learned kernel shape contributes +0.0009 beyond any fixed low-pass
(non-overlapping bands vs ABL-A). (2) **The zero-init gate is a training-stability convenience,
not the performance driver** — ABL-B matches the full filter. This dissects the contribution the
way the audit demanded and *supports* the narrow novelty claim: the causal FIR module's gain is
specific to its learned response, not to smoothing per se. Files:
`results_FIRABL_{fixedavg,nogate}_MI_seed{08–12}.json`.

## Office_Products program — outcome (N7 + N13 counter-evidence, resolved 2026-07-11)

- **N13 "needs broader wins": ANSWERED WITH DATA.** The pre-registered zero-tuning Office
  confirmation PASSED its dual gate on full-catalog evals: K=16 CI-LB 0.03032 / K=8 CI-LB
  0.03010 vs published 0.0271 (+12%, 10/10 fresh seeds; dataset stats-identical). The paper now
  exceeds the published HSTU-BLaIR point estimate on **two of the comparator paper's three
  AR2023 categories**.
- **N7 "pattern needs a predictive model + replication": PARTIALLY answered, honestly.** The
  pre-registered prediction was scored **VOID** (Office's connectivity 2.89 falls in the
  pre-declared ambiguous zone; a stats-tool formula inconsistency is disclosed in
  `SOTA_CONFIRM_OFFICE_RESULTS.md`). Descriptively, Office's tail contrast is strongly
  text-positive (z=3.8 @10 → z=13.0 @100, full catalog), consistent with the connectivity
  gradient (2.34 win → 2.89 win → 3.51/3.70 null) — reported as a fourth pattern point, not a
  scored out-of-sample confirmation.
