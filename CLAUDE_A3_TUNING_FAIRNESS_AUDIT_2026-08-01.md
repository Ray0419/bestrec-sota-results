# Claude A3 audit — baseline tuning fairness, quantified

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-01. Reviewed commit: `a9a87cee` (working tree dirty; manuscript/TeX/cover letter
carry uncommitted Codex edits, audited as-is).

Discharges checklist queue item **A3**: *"are search spaces, budgets, and epoch budgets symmetric
and documented for every comparator? Name specific asymmetries."* Last tick I rated this the
weakest row in the package and the most likely reviewer-1 rejection ground, so it is now audited
with counts rather than adjectives.

```text
WORKSTREAM:        A3 baseline-tuning-fairness audit
OBJECTIVE:         quantify search-space / budget / epoch-budget asymmetry per comparator
EVIDENCE QUESTION: is the asymmetry documented, and does it invalidate any counted claim?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json,
                   TORS_METHODOLOGY_CHECKLIST.md
EXPECTED OUTPUT:   named asymmetries with numbers + row disposition + proposed disclosure
STOP CONDITION:    memo committed and pushed
```

Method: read-only mining of the committed run record (1,105 `results_*.json`), the WEARec
selection record, the comparator matrix, and §4–§5 of the manuscript.

---

## The asymmetry, in numbers

| side | distinct hyperparameter configurations | seeds | epoch budgets |
|---|---:|---:|---|
| **our model family** (whole project record) | **56** | 1,105 result files across 427 campaign families | **12 distinct**: 1, 2, 5, 15, 20, 30, 40, 50, 60, 80, 100, 101 |
| **WEARec** (official code) | **2** presets, **1** tuning seed | 8 assessment | official recipe |
| **AlphaFuse-style package** | **1** frozen configuration | 8 fresh | official recipe |
| **upstream-class SASRec-ID** | **1** (V3 zero-init) **+1** (V4 normal-init, *cross-campaign*) | 8 + 8 | official recipe |
| **published/local HSTU-BLaIR reference** | **0** local tuning; single-run published | 1 (unpaired) | pinned env unavailable |

**The search-breadth ratio against external comparators is between 28× and 56×.**

### Being fair to the paper about what that number means

The 56 configurations span the **entire project history** — encoder studies, the pre-FIR
BEST-Rec/LC2C line, capacity and dropout sweeps — not 56 attempts aimed at the FIR contrasts. It
would be an overstatement to call it "56 tuning trials for the FIR model," and I am not making
that claim. What it does establish is that **our model family arrived at every external comparison
carrying a long accumulated tuning history, while each comparator arrived with one or two
configurations.** That is the asymmetry, and it runs in the direction that favours us.

## Where the package is genuinely symmetric — this should be said plainly

The **internal** FIR contrasts are symmetric by construction and I found no defect in them:

- every FIR campaign family resolves to **one configuration plus an arm flag** (`FIRCTRL`,
  `FIRPOINTV1`, `FIRPROSPV3` each show 2 config signatures across 8 seeds = identity/learned arm
  toggle, not a search);
- **8 seeds per arm**, same seed blocks, **exact per-seed backbone initialization shared** across
  arms (`init_state_sha256` equality is adjudicator-enforced);
- **20 epochs** for every Musical_Instruments / Industrial_and_Scientific / Software campaign,
  **40** for Video_Games — held constant within each comparison.

So the counted internal contrasts do **not** suffer a tuning-fairness defect. The problem is
confined to the external-comparator rows.

## Named asymmetries

**A3-1 — WEARec preset selection was effectively a coin flip.** The selection record
(`wearec_baseline_v1_selection.json`) shows two presets scored on one tuning seed (20262000):
`official_beauty` **0.06844665** vs `official_sports` **0.06812966** — a validation gap of
**0.000317**. A two-point search separated by three ten-thousandths is not meaningful tuning. The
protocol is clean (TEST not read, tie order pre-declared), but *"validation-only preset selection"*
should not be read as WEARec having been tuned.

**A3-2 — epoch budgets are per-recipe, not common.** Our arms use 20 or 40 epochs; each external
comparator uses its own official schedule. This is defensible — forcing our schedule onto official
code would be worse — but it means **no comparison in the package holds training budget constant
across method families**, and the manuscript should not be read as if any did. It does not claim
to.

**A3-3 — the baseline tuning record is not publicly checkable.** Zero of the 1,105 public
`results_*.json` files correspond to WEARec/EEV3/EEV4 runs; those endpoints are private by design.
Consequently checklist §2 items **5** (attempted/completed configuration counts) and **9**
(failed/OOM/non-finite trials) **cannot be verified for the baselines from public artifacts** —
only selection summaries and adjudications are public. This is a *documentation* gap, not evidence
of misconduct, and §5 already says private endpoint extraction is not publicly replayed.

**A3-4 — V4 confounds phase/date with initialization.** The normal-init SASRec-ID sensitivity ran
as a separate later campaign, so its +0.004042 improvement over the zero-init control is
cross-campaign. The manuscript states this.

## Does any counted claim need to change? **No.**

I checked every affected row against the claim vocabulary. The manuscript already labels each
external comparison *"architecture, loss, schedule, capacity, and tuning budget unequal,"*
*"whole-package,"* *"equal-evaluation feasibility baseline only,"* and *"the equal-budget factorial
remains open."* It nowhere asserts equal budget, equal capacity, or SOTA. **The asymmetry is
disclosed, and no counted claim depends on it being absent.** The counted boundary — MI (vs 0.0406)
and Office V3 (vs 0.0271 / 0.0279) — is a point-estimate comparison against published values, not a
tuning-matched contest, and is labelled as such.

## Row disposition: **stays OPEN.** I am not moving it.

The checklist's required closure is *"Freeze symmetric validation-only search spaces, configuration
counts, seeds, early stopping, resource budgets, failed trials, and selected values."* That work has
not been done. `PREREG_TIER_A_TUNING_MATRIX_V1_DRAFT.md` exists and is explicitly **DRAFT ONLY —
NOT FROZEN, NOT AUTHORIZED**; it awaits human approval of compute, data, licensing, and venue. Until
it is frozen and run, the row is OPEN regardless of how well the gap is disclosed.

**Consistency note:** I said last tick this row stays OPEN. Auditing it in detail has not changed
that, and I decline to soften it just because the disclosure is good.

## The one improvement available without new runs

The manuscript currently discloses the asymmetry **qualitatively** ("tuning budget unequal"). It
could disclose it **quantitatively** at no experimental cost. Proposed addition for §4 or the
comparator matrix — **Codex-owned; I did not edit any file:**

> Tuning opportunity is not symmetric across method families. Our model family was developed over
> 56 distinct hyperparameter configurations recorded across the project history, whereas the
> official-code WEARec baseline received two presets selected on a single tuning seed (validation
> NDCG@10 0.068447 vs 0.068130), and the AlphaFuse-style and upstream-class SASRec-ID arms each
> received one frozen configuration. Epoch budgets follow each method's own recipe (20 or 40 for our
> arms) rather than a common budget. All external-comparator contrasts are therefore reported as
> whole-package, unequal-budget comparisons; no equal-budget factorial has been run.

A reviewer who computes this ratio themselves and finds it undisclosed will treat it as concealment.
The same reviewer, reading it stated first by the authors, will treat it as candour. **The number
is going to be found either way — state it.**

## Limits

Configuration counts are derived from hyperparameter keys present in committed result JSONs; runs
whose configs were not serialized under those keys are undercounted, so 56 is a **lower bound** on
our side, which strengthens rather than weakens the finding. I did not read private endpoints and
did not attempt to — no sealed endpoint was inspected. This audit is advisory same-team evidence,
not peer review, and creates no independent confirmation.
