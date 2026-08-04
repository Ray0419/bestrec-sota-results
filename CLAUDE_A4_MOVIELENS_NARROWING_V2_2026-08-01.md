# Claude A4 v2 — MovieLens external validity: F1 RETRACTED, narrowing now unconditional

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-01. Reviewed commit `a3b5e85b`. Supersedes
[`CLAUDE_A4_MOVIELENS_NARROWING_2026-07-31.md`](CLAUDE_A4_MOVIELENS_NARROWING_2026-07-31.md).

```text
WORKSTREAM:        A4 external validity, second pass
OBJECTIVE:         resolve my own BLOCKING F1, then deliver the narrowing it was blocking
EVIDENCE QUESTION: was the ML-1M module active, and what does the null actually permit?
FILES I MAY EDIT:  this memo; the superseded banner on my own v1 memo; HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist
EXPECTED OUTPUT:   F1 disposition + unconditional permits/forbids + row disposition
STOP CONDITION:    memo committed and pushed
```

All numbers below are read from committed artifacts: `fir_efficiency_ml1m_v1_adjudication.json`,
`adjudicate_fir_efficiency_ml1m_v1.py`, `PREREG_FIR_EFFICIENCY_ML1M_V1.md`, and
`figures/fig_movielens_cohort_flow_data.csv`. **No sealed endpoint was inspected.**

---

## F1 — **RETRACTED. It was never blocking, and my proposed check was wrong.**

My v1 memo declared, as its top **BLOCKING** finding, that the paper *"should not assert what the
MovieLens null means"* until Codex read `fir_v3_final_l2` per seed to rule out an inactive module.
Three errors, all mine:

**1. The check had already been run — by the committed adjudicator, before I raised it.**
`adjudicate_fir_efficiency_ml1m_v1.py` lines 286–288:

```python
if arm == IDENTITY and base.get("fir_control_final_l2") != 0.0:
    die(f"identity taps moved in {paths['run'].name}")
if arm != IDENTITY and not (base.get("fir_control_final_l2", 0.0) > 0.0):
    die(f"active filter did not move in {paths['run'].name}")
```

The adjudicator **fails closed** unless every non-identity arm has a strictly positive final tap
norm. Verdict `ML1M-NO-FIR-REPLICATION` was issued, so those gates passed on all 48 non-identity
runs. **The module was provably active on every seed, including the three bit-identical ones.**
"Explanation 3 (pipeline fault)" was excluded by construction before I proposed testing for it.

**2. I named the wrong field.** ML-1M runs `fir_control=learned` with `fir_v3=off`; the recorded
field is `fir_control_final_l2`. Had Codex executed my request literally, `fir_v3_final_l2` would
have read 0 on *every* ML-1M arm — including the working ones — and I would have manufactured a
**false integrity alarm** against a clean study. This is the error that matters, and it is worth
stating plainly rather than folding into a list.

**3. I used the wrong cohort size.** I wrote *"~6,040 evaluation users"* and concluded *"not one
user's top-10 changed."* The retained primary cohort is **1,033** users (1,102 candidate);
6,040 is the **source population**, stated at `PREREG_FIR_EFFICIENCY_ML1M_V1.md` line 42 — which is
exactly the trap I fell into. Per the 2026-07-31 22:11 audit, **125 / 115 / 109 of 1,033 target
ranks do change** on those three seeds. So ranks moved; they moved **outside the top-10**, leaving
NDCG@10 bit-identical.

**Correct explanation: metric granularity (my explanation 2), with the module demonstrably active.**
Benign. Nothing blocks. *(Minor: the bit-identical seeds are indices 3, 5, 7 — my v1 labelled them
s2/s4/s6.)*

## The budget asymmetry is real, and now derives transparently

`PREREG_FIR_EFFICIENCY_ML1M_V1.md` lines 121–125: 20 epochs, batch size 256, **one example per user
per epoch**. With 1,033 retained users:

> ⌈1033 / 256⌉ × 20 = 5 × 20 = **100 optimizer updates**

against **4,000–9,680** on the Amazon campaigns — a **40×–96.8×** cross-corpus asymmetry,
confirming the audit's corrected figures by independent derivation.

Critically, the same prereg states *"The six arms receive identical budgets."* So **within** ML-1M
the comparison is symmetric; the asymmetry is **cross-corpus only**. This is the same structural
pattern A3 found yesterday: internal contrasts symmetric, external/cross-corpus contrasts not.

## What the ML-1M result permits — **now unconditional**

> Under a preregistration frozen before data acquisition, the causal FIR residual did not improve
> full-catalog NDCG@10 over its matched identity control on MovieLens-1M (learned − identity
> **+0.000000**, 95% CI **[−0.000074, +0.000075]**, eight matched seeds, `p_Holm = .995`). The
> module was active on every seed: the committed adjudicator fails closed unless each non-identity
> arm ends with a strictly positive tap norm. Three seeds returned bit-identical NDCG@10 because
> target-rank changes fell outside the top-10, not because the filter was inert. The interval's
> upper bound is **28× to 82× smaller** than the estimates observed on the Amazon categories
> (+0.002110 to +0.006150), so an effect of the Amazon-observed magnitude is not supported here.
> However, this cohort received approximately **100 optimizer updates** against 4,000–9,680 on the
> Amazon campaigns, so the result is a **failure to replicate under a substantially smaller
> training budget**, not a demonstration that the corpus lacks the effect.

## What it does NOT permit — enumerated

- **Not equivalence.** No margin was pre-declared for the replication contrast; the CI covers zero.
  A CI covering zero is not equivalence.
- **Not a domain moderator.** The budget was not matched. Attributing the null to *MovieLens-ness*
  rather than to 100 updates is unsupported, and this is the single most tempting overread.
- **Not "FIR does not work."** One corpus, one configuration transferred from Amazon, one protocol.
  n=1 domain cannot support a general negative any more than three Amazon categories support a
  general positive.
- **Not a parameter-efficiency claim.** See F2 below.
- **Not a refutation of the Amazon results**, which are separately adjudicated under their own
  frozen rules and stand at their own evidence class.

## F2 — **STANDS.** The compression claim is near-vacuous on this corpus

All six arm means lie in **0.05211643 – 0.05221133**, a total spread of **0.0000949** — about **19%
of the 0.000500 noninferiority margin**. The parsimonious arms are noninferior to per-channel, but
so is doing nothing: no arm separates from identity. Noninferiority among arms that are each
indistinguishable from the identity control carries **no information about parameter efficiency**;
it says several inert parameterizations are equally inert.

The abstract's *"the parsimonious FIR arms support only conditional coefficient-count compression"*
is pre-declared and technically satisfied, and it does carry the word *conditional* — but the
dependency should be visible, or a reviewer reads a salvaged positive. **Verified: the manuscript
already states the conditionality at §5 and §6 (*"met the pre-declared noninferiority margin against
learned FIR only conditionally: the learned-FIR effect gate failed"*). F2 is adequately disclosed;
I recommend no change.**

## Row disposition: **External validity stays OPEN.**

Required closure is a lawful new non-Amazon study frozen before TEST inspection, preferably
externally custodied. That has not happened. Resolving F1 improves the *interpretation* of the
existing negative result; it does not supply new external evidence. **I decline to move the row.**

What *has* changed is that the narrowing text above is now deliverable **unconditionally** — my v1
offered it only conditional on F1, and that condition is discharged.

## Consequences for my own open-findings register

**F1 → RETRACTED** (was listed blocking, severity highest, five ticks). It should be struck from the
register rather than carried, and the v1 memo now carries a superseding banner. I am also recording
the general lesson, because this is the second time this session the same failure mode has bitten:
**before escalating a diagnostic as blocking, check whether a committed adjudicator already gates
it.** Twice now the governance machinery was ahead of my audit.

## Limits

Read committed adjudication and prereg artifacts only; the adjudicator was the first endpoint
reader, as required. The 125/115/109 changed-rank counts are taken from the 2026-07-31 22:11 audit,
not independently recomputed here — the per-run sidecars they derive from are private. The
100-update figure is derived from the prereg's stated batch size, epoch count, and one-example-per-
user rule against the committed retained-cohort count; it is arithmetic on documented values, not a
measured optimizer-step log. Advisory only; no artifact modified.
