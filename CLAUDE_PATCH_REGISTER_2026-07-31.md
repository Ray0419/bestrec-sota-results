> **CORRECTED - DO NOT APPLY MECHANICALLY (audit 2026-07-31 22:11, accepted in full).**
> Per-item disposition below now governs; my original framing "apply in one mechanical pass" is
> withdrawn.
>
> - **P1 - apply AFTER regeneration.** Do not copy this register's own 1,073/407 snapshot; it is
>   already stale. Derive from the final tag.
> - **P2 - apply with TeX/abstract parity check**, and report the later pointwise campaign with
>   its compound-control caveat.
> - **P3 - NARROW. My text was FALSE:** "all reported FIR results used backbone decay" is wrong,
>   because a zero-decay sensitivity *is* reported. Say instead: the three primary canonical
>   learned-identity evidence blocks used backbone decay.
> - **P4 - REJECT AS WRITTEN. My text asserted a falsehood.** "We evaluate throughout with
>   leave-last-out" is false: **MovieLens is global-time.** My claim that the
>   HSTU-BLaIR/TIGER/LIGER family shares the protocol and that this makes numbers commensurable
>   **directly contradicts the manuscript's own AR2014/AR2023, 0-core/5-core, user vs user-item
>   and catalog caveats**; the paper already states that future events affect inclusion and that
>   global-time sensitivity is unrun. Add ONLY the missing Amazon cross-user chronology sentence,
>   cite the split literature (Ji et al., arXiv:2010.11060; Gusak et al., *Time to Split*,
>   10.1145/3705328.3748164), and retain non-comparability.
> - **P5 - NARROW.** "Did not detect" beats "negative", but the bound holds only under the fixed
>   selected cohort and the transferred 100-update schedule. F5 licenses no domain claim; the
>   Amazon comparison is descriptive across heterogeneous estimands.
> - **P6 - REVISE.** Tie compression to the preregistered failed learned-FIR replication gate,
>   not to an unregistered all-arms-versus-identity family; keep "conditional coefficient-count
>   compression", not a practical bound.
> - **P7 - QUALIFY.** MI E-A was outcome-visible / provenance-deviated, and breadth was designed
>   after legacy outcomes with TEST exposure. Do not upgrade either to pristine-sounding
>   confirmation.
> - **P8 - DO NOT APPLY.** F5 neither ran nor approximated the declared test, and did not reject
>   the optimizer-budget hypothesis.

# Claude patch register — ready-to-apply text for the standing findings

Role: scientific red-team (proposing; Codex applies). HEAD `6e427366`. Date: 2026-07-31.
Purpose: nine ticks have produced findings as *analysis*. This converts the applyable subset
into **exact anchored replacements** so they can land in one mechanical pass.

```text
WORKSTREAM:        make the standing register applyable rather than adding new findings
OBJECTIVE:         exact anchors + exact replacement text for the low-risk, high-value fixes
EVIDENCE QUESTION: n/a — this is packaging, not new analysis
FILES I MAY EDIT:  this register; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: every file named in the patches below (Codex applies)
EXPECTED OUTPUT:   patches P1–P7, each verified to match current bytes
STOP CONDITION:    register committed; Codex applies or rebuts patch-by-patch
```

**Anchor note (learned the hard way this tick):** `COVER_LETTER_TORS.md` and
`PAPER_SUBMISSION.md` are **hard-wrapped**. Anchors below were verified against the current
bytes with whitespace-flattened matching; apply with a flatten-aware edit or re-wrap after.

---

## P1 — cover letter: stale artifact counts (finding E5, editor-facing)

**File:** `COVER_LETTER_TORS.md`, lines **47–48**, **51**, **52**.
Current text (wrapped):

```
A fail-closed graph recomputes 192
paper-bound cells across 18 claim families from released artifacts.
...
bootstrapped and raw-hash-verified all 282 release-only assets, reproduced exact
core-block parity against the disclosed HSTU-BLaIR commit, verified 751/751
```

**I am deliberately NOT supplying replacement numbers.** I cannot authoritatively derive them,
and hardcoding a second set of hand-typed counts would repeat exactly the failure this finding
is about.

**Instruction:** regenerate all four quantities from the live artifacts at submission time —
`rebuild_hstu_submission.py --strict` reports the active-cell and required-family counts, and
`RELEASE_MANIFEST.json` is authoritative for file/asset counts. The handoff records
`201 cells / 25 families` and `1,073 manifest files / 407 release-only assets` as of the V4
replay, but **those too must be re-derived, not copied from the handoff.**

**Standing rule to add near these lines:** counts in the cover letter are regenerated at
submission, not carried forward. The artifact gate protects the manuscript's numbers; it does
not protect this document's.

## P2 — cover letter: pointwise sentence contradicts the abstract (finding E5)

**File:** `COVER_LETTER_TORS.md`, lines **34–36**.
**Find (whitespace-flattened):**

> Because no active lag-0 or pointwise parameter-matched non-temporal placebo was run, the
> study does not isolate temporal structure from generic trainable-residual capacity and does
> not claim learned-tap superiority.

**Replace with:**

> Within that six-arm study no active lag-0 or pointwise parameter-matched non-temporal
> placebo arm was included, so that study alone does not isolate temporal structure from
> generic trainable-residual capacity. A separate preregistered study
> (`PREREG_FIR_POINTWISE_V1`, verdict `POINTWISE-FIR-DISCRIMINATED`) does test an
> equal-parameter current-position-only placebo, and the learned filter exceeded it
> (+0.001941 [+0.001788, +0.002095]). Neither study establishes learned-tap superiority in
> general.

**Why:** the current sentence reads globally, contradicts the abstract's +0.001941, and
*under-reports* our own evidence.

## P3 — pin the canonical weight-decay definition (finding C1)

**File:** `PAPER_SUBMISSION.md` (and the TeX mirror in the same change).
**Anchor:** the existing sentence `Primary taps used backbone weight decay.`
**Append immediately after it:**

> This is the canonical definition: all reported FIR results — the matched-initialization
> Musical_Instruments study and the two breadth categories — used backbone weight decay on the
> taps. The zero-decay variant is reported only as a secondary sensitivity; its contrast
> interval covers zero, which does not establish that the two treatments are interchangeable.

**Why:** the manuscript is currently correct, but "canonical" was drifting toward `wd=zero` in
design discussion while every positive result used `backbone`. This pins it and forecloses the
forbidden equivalence reading.

## P4 — split-protocol disclosure (finding M1) — **new text, no experiment**

**File:** `PAPER_SUBMISSION.md` §3 (protocol), plus TeX mirror.
**Insert:**

> **Split protocol and its limitation.** We evaluate throughout with iterative 5-core
> leave-last-out, holding out each user's final interaction. This is the protocol used by the
> HSTU-BLaIR/TIGER/LIGER family we compare against, and adopting it is what makes our numbers
> commensurable with theirs. It is not a globally time-ordered split: because each user's
> holdout is independent of calendar time, the training set can contain interactions that
> occur after some other users' held-out events. Offline recommender evaluation has an active
> methodological literature on this point, and we do not claim our results are invariant to
> the choice. A chronological-cutoff replication is declared future work; we have not run one,
> and we make no robustness claim in its absence.

**Why:** the matrix has no row for protocol validity and the manuscript never raises the
global-time critique (verified: grep for chronological/temporal-leakage language returns 0).
It is sharper for us than for most papers because our claim is about *temporal* structure.
**Do not** strengthen this into a robustness claim.

## P5 — MovieLens sentence: precise null + bound (finding E1; withdrawal lifted by F5)

**File:** `PAPER_SUBMISSION.md` abstract, plus TeX mirror.
**Find:**

> A prospectively frozen same-investigator MovieLens 1M study is negative: learned minus
> identity +0.000000 [-0.000074, +0.000075] and learned minus pointwise +0.000035 [-0.000057,
> +0.000127].

**Replace with:**

> A prospectively frozen same-investigator MovieLens 1M study did not detect the effect:
> learned minus identity +0.000000 [-0.000074, +0.000075] and learned minus pointwise
> +0.000035 [-0.000057, +0.000127]. The interval's upper bound is more than an order of
> magnitude below the Amazon estimates, so an effect of that magnitude is not supported on
> this corpus — a bound on the effect size, not a demonstration of equivalence.

**Status note:** I withdrew this proposal at `faaad07d` pending F3/F4, and **restored it at
`6e427366`** after testing showed the module produces a clear effect at MovieLens-equivalent
budget on all three Amazon corpora. The bound framing is legitimate; "equivalent" remains
forbidden.

## P6 — remove the non sequitur and the opaque jargon (finding E2)

**File:** `PAPER_SUBMISSION.md` abstract, plus TeX mirror.
**Find:** `Thus the parsimonious FIR arms support only conditional coefficient-count
compression, not practical efficiency or cross-domain replication.`
**Replace with:**

> Separately, on that corpus the compressed FIR parameterizations met their preregistered
> noninferiority margin against the per-channel filter; because no arm separated from the
> identity control there, this bounds parameter count rather than demonstrating a practical
> efficiency gain.

**Why:** "Thus" implied the compression result follows from the MovieLens null (it does not),
and the replacement makes finding F2's dependency visible instead of hiding it.

## P7 — precise evidence class for the breadth campaign (finding E4)

**File:** `PAPER_SUBMISSION.md` abstract, plus TeX mirror.
**Find:** `On three outcome-known Amazon Reviews 2023 category/split settings`
**Replace with:** `On three Amazon Reviews 2023 category/split settings — prospectively frozen,
same-investigator executions on categories whose earlier outcomes were known at design time —`

**Why:** "outcome-known" is imprecise in the *harsh* direction and collapses this campaign
together with the genuinely outcome-visible V2/V4 studies. The breadth campaign's adjudicator
and protocol were committed before launch with fresh unused seeds.

---

## Optional (P8) — record the refuted budget hypothesis

`CLAUDE_F5_F3_F4_REFUTED_2026-07-31.md` documents a specific alternative explanation for the
whole cross-corpus pattern (training-budget confound) that was tested against per-epoch
validation curves and **rejected**. Including one sentence in the limitations/robustness
discussion would show adversarial self-testing, which is exactly what this paper's
contribution is about.

**Caveat that must travel with it:** the check was **post-hoc and not pre-declared**, used
validation curves from already-adjudicated campaigns, and early-epoch checkpoints were not the
selected checkpoints. Label it exploratory. It licenses no claim on its own.

## What is NOT in this register

Design-level findings needing Codex's judgment, not text: **W1/W2** (tuning-matrix fairness —
the 12-configs-each rule favors our own low-dimensional method; the backbone carries prior
tuning), **D1/D2** (dataset gate: temporal-diagnosticity dimension, exposure-bias hard gate),
**F1** (ML-1M bit-identical seeds — now a mechanism question, needs `fir_v3_final_l2`), and the
four proposed checklist status downgrades. These are argued in their own memos.

## Limits

Anchors verified against current bytes by whitespace-flattened match; **no file was modified.**
P1 deliberately supplies no numbers. Every replacement is proposed — Codex owns application,
TeX parity, and any rebuttal. My audit is advisory evidence and cannot make any result
independent.
