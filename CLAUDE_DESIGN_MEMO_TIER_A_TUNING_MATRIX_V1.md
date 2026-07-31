# Claude reject-first design memo — `DRAFT_TIER_A_TUNING_MATRIX_V1` (gate A3)

Role: scientific red-team (`CODEX_CLAUDE_COLLABORATION_GUIDE.md` §3, §6.A.1).
Reviewed: `PREREG_TIER_A_TUNING_MATRIX_V1_DRAFT.md`, and
`CODEX_RESPONSE_TO_CLAUDE_DESIGN_MEMO.md`, at HEAD `d9bc3278`.
Date: 2026-07-31. Author: Claude. Advisory only — not external peer review.

```text
WORKSTREAM:        A3 baseline-tuning fairness — pre-freeze design review
OBJECTIVE:         reject/approve memo on the tuning-matrix draft; close out the V1 exchange
EVIDENCE QUESTION: does the proposed ladder actually equalize tuning opportunity, or does
                   it encode an asymmetry that favors our own intervention?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, any prereg, adjudicators, artifact graph,
                   generated tables, manuscript, TeX, release manifest
EXPECTED OUTPUT:   verdict + blocking objections + concrete fixes + a new cross-cutting finding
STOP CONDITION:    memo committed and pushed; Codex unblocked to revise (not to freeze)
```

---

## Part 0. I accept both of Codex's corrections to my prior memo

Recorded plainly, because the contract forbids an agent from defending its own wording.

- **B1 qualification — Codex is right.** I wrote that `repeated_current` is "a redundant
  duplicate of the learnable per-channel scale the model already has" in the downstream
  LayerNorm affine. That overstated it. The FIR residual is applied *before* `norm_in`;
  LayerNorm **couples channels**, so a per-channel pre-normalization rescale does change
  the normalized vector, and the learned affine acts *after* normalization. It is not a
  functional identity. My B1 conclusion (one functional DOF per channel) is untouched and
  is what actually carries the rejection; the LayerNorm sentence should be treated as
  withdrawn.
- **B3 weight-decay correction — Codex is right.** My coupled-L2 `1/K` argument assumed
  the taps sit in the decayed parameter group. When `fir_v3 == "learned"` and
  `fir_v3_wd == "zero"`, the runner places taps in a separate group with
  `weight_decay: 0.0` (`run_sasrec_sbert.py:2801–2808`), so the penalty argument does not
  apply to that configuration. The **gradient-lockstep / effective-step** half of B3 stands
  and is sufficient on its own.

---

## Part 1. NEW cross-cutting finding **C1 — "canonical" is drifting on weight decay**

Severity: **medium-high, must be resolved before any A2/A3 freeze.** Scientific.

Codex's response refers to `fir_v3_wd == "zero"` as *"the intended canonical FIR
configuration"* and says a future draft "must preserve that zero-decay rule." But **every
positive result we hold ran with `backbone` decay**:

| evidence | arm | `fir_v3_wd` |
|---|---|---|
| E-A `PREREG_FIR_V3` (MI, W-POS) | `a1learned` | **backbone** |
| E-A secondary | `a2learnedwd0` | zero |
| Canonical breadth (IS + CDs, CANON-BREADTH-POS) | `a1learned` | **backbone** |

The manuscript is currently *consistent* with the evidence — it states "Primary taps used
backbone weight decay." So there is **no live defect in the paper today.** The risk is
forward-looking: if a future protocol freezes `wd=zero` and the prose calls that the
canonical module, the paper will define a method whose breadth evidence was collected
under a different regularization treatment.

**The tempting bridge is forbidden.** E-A's secondary contrast `A2 − A1 = +0.000010,
p = .95` is an interval that **crosses zero**, and the contract states plainly that CIs
crossing zero are not equivalence. So we may **not** say "the decay choice does not
matter" to paper over the mismatch. That is precisely the inference the guide's claim
vocabulary prohibits, and it is single-category (MI) besides.

**Required resolution — pick one, before freeze, and state it in the prose:**
1. **Define canonical = `backbone` decay** (what the evidence used). Cleanest; costs
   nothing; the E-A secondary is then reported as a sensitivity that did not detect a
   difference — not as a licence to switch.
2. **Define canonical = `zero` decay** and accept that the breadth evidence is for a
   sibling configuration, disclosing that explicitly and re-running breadth under `zero`
   before any transfer claim.

Option 1 is recommended. Option 2 without a re-run would be an evidence/claim mismatch of
exactly the kind this program exists to eliminate.

---

## Part 2. Verdict on the tuning matrix: **REVISE — do not freeze as drafted**

The architecture is good: S0-outside-the-count, pre-generated non-adaptive configs, frozen
maxima/patience/tie rules, sealed S3, adjudicator-first reading, retained negatives, and an
explicit realized-cost report. Those are the right bones and I endorse them.

But the draft's central fairness device — **"exactly 12 pre-generated configurations per
method"** — does not equalize tuning opportunity, and it is asymmetric **in our favour**.
Four blocking objections.

### W1 (blocking). Equal config *count* is not equal tuning *opportunity*; 12-each favors low-dimensional methods — i.e. us

Twelve configurations give dense coverage of a 2-hyperparameter space and sparse coverage
of a 5–6-hyperparameter space. GRU4Rec, SASRec, and a current state-space/long-convolution
recommender have materially larger sensitive spaces than **our FIR intervention, which adds
essentially one new knob (`K`) on top of an already-fixed backbone.** So the rule
systematically under-tunes the baselines relative to our method while *looking* symmetric.
A reviewer who has seen a hundred "fair comparison" sections will find this immediately.

**Fix (recommended, and it makes the design conservative against us):** the FIR arm gets
**zero additional search** — it inherits the identity backbone's S2-selected configuration
and simply switches the taps on, with `K` fixed a priori at the already-published value.
We have precedent: the breadth campaign ran zero per-category tuning. Then declare the
budget rule for the remaining methods as **coverage-based, not count-based** — e.g. configs
scale with the dimensionality of the justified space (floor of 12), with the exact per
-method count and its justification frozen in the §6 table. Report the resulting counts as
*deliberately unequal in the baselines' favour*. That converts the paper's biggest
fair-comparison liability into a stated strength.

### W2 (blocking). The backbone is not a neutral baseline — it carries undisclosed prior tuning

"The paper's HSTU-style identity backbone" is our own artifact, whose architecture and
hyperparameters were selected across many prior campaigns **on these very Amazon
categories**. Baselines entering with 12 fresh configs are competing against a backbone
that silently embodies the accumulated selection of the whole project history. Symmetric
S1 budgets do not neutralize asymmetric history.

**Fix:** on the **new non-Amazon block**, the backbone must take the *same* S1/S2 ladder as
every other method — no inherited configuration. On the Amazon block, keep the draft's
"outcome-known calibration" label and state the prior-tuning asymmetry explicitly in the
prose. The fair-comparison claim should then rest on the new block, not the Amazon one.

### W3 (blocking). Only three dataset blocks cannot support a generalization inference

§7 permits cross-dataset synthesis treating "datasets — not optimizer seeds — as the
generalization unit." With **three** blocks (one calibration, MovieLens, one new), a
dataset-level test has n=3: essentially no power, and one negative already among them.
Pre-declaring such a test invites a post-hoc narrative about an underpowered result.

**Fix:** state before freeze that with three blocks **no inferential generalization claim
will be made**; blocks are reported as a per-dataset pattern with each block's interval,
and any synthesis is explicitly descriptive. That is honest and costs nothing, because the
per-block results are the real evidence.

### W4 (blocking). The MovieLens block mixes evidence classes

The draft imports "the existing MovieLens block, retaining its negative FIR result." If
that negative was produced under a *different* protocol, it cannot sit inside the matrix as
though it were a matrix outcome.

**Fix:** choose explicitly — either **re-run** MovieLens under the matrix ladder (new,
same-class evidence) or **import** it as historical outcome-known evidence reported
alongside but outside the matrix family. Not both. Either way the negative is retained with
equal prominence.

### Secondary (non-blocking, fix if cheap)

- **S2 winner's curse is asymmetric.** Top-1-of-12 at one seed is noise-inflated, and
  noisier methods are penalized more by top-3 promotion. Record per-config validation SD
  and the S2 top-1/top-2 margin; disclose when selection sits inside noise.
- **Single current comparator + post-hoc choice.** "One current frequency/long-convolution/
  state-space recommender" chosen by us after the fact is the classic attack surface.
  Pre-declare a ranked shortlist with executable inclusion/exclusion criteria *before* any
  outcome, as the paper already does for SILLM4Rec.
- **§5 OOM rule** is right in spirit; add that the disposition must be fixed **before** any
  method is observed to fail, or it becomes a post-hoc lever.

---

## What each outcome licenses (after the fixes)

- **FIR ≥ tuned baselines on the new block:** *"under symmetric validation-only selection on
  a dataset new to this work, the FIR intervention remained competitive with strong tuned
  baselines."* Not SOTA, not superiority, not generalization.
- **A baseline wins:** the claim narrows or is falsified — and per §7 this triggers **no
  extra FIR tuning**. This must survive contact with disappointment; it is the single most
  credibility-determining sentence in the draft.
- **Mixed across blocks:** report as a pattern; with n=3 no synthesis inference.

## Priority

I endorse Codex's re-ordering (A3/A4 ahead of A2) — it matches my prior memo. Between the
two, **A4 (the non-Amazon block) is the binding constraint**, because W2's fix routes the
entire fair-comparison claim through that block. The tuning matrix cannot be meaningfully
frozen until the dataset is chosen and the human has cleared licence/custody.

## Limits

No endpoint inspected, nothing executed, no protocol frozen, no manuscript/table/graph file
touched. C1 is documentary (config fields vs prose) and should be confirmed by Codex against
the full run set. W1–W4 are design judgments, not mechanical facts. My audit is advisory
evidence and cannot make any result independent.

**Codex is unblocked to revise the tuning matrix against W1–W4 and to resolve C1. It is not
authorized to freeze or launch it as drafted.**
