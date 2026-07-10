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
| **N9** "faithful HSTU" unproven | Softened to "HSTU-style pure-PyTorch implementation based on the published architecture"; equation-level verification stated, numerical parity explicitly NOT claimed (hardware-impossible, documented). |
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

_(pending — appended by the analysis after `FIR_ABLATIONS_COMPLETE`)_
