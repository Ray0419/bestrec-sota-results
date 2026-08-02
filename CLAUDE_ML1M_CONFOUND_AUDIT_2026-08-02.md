# Claude audit — the ML-1M "narrower scope" finding: right conclusion, confounded evidence

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed commit `a066da0b` on `codex/bestrec-sota-results`; evidence read from
`claude/filter-overparam-experiments` @ `489ef1ca`.

```text
WORKSTREAM:        audit the ML-1M finding proposed against the manuscript
OBJECTIVE:         test the claim that two explanations were ELIMINATED
EVIDENCE QUESTION: were the eliminating experiments run at a comparable training budget?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist
EXPECTED OUTPUT:   confound verdict + corrected candidate list + corrected scope sentence
STOP CONDITION:    memo committed and pushed
```

The filter-ladder work raised a finding it says "bears directly on the manuscript": ML-1M shows the
**largest** filter effect of four benchmarks (+0.0212, ~24% relative) in FMLP-Rec, while
`PREREG_FIR_EFFICIENCY_ML1M_V1` measured an exact null for our FIR there. It concludes the honest
scope is narrower than the manuscript states.

**I agree with the conclusion. I do not accept the evidence for it as stated, and I am the reason
the correction matters.**

---

## 1. The claimed eliminations

> 1. *"MovieLens resists temporal filtering"* — **ELIMINATED.** The circular filter gives +0.0212.
> 2. *"Causal short kernels are too weak on ML-1M"* — **ELIMINATED.** A causal 16-tap depthwise
>    filter in the same harness gives **+0.01877, t=+7.84, 3/3 seeds**.

Remaining candidates named: **backbone** and **split**.

## 2. The confound: a 283×–555× training-budget gap

Both eliminating experiments ran inside the **BSARec harness**. Read from that harness's own logs
on this machine (`LADDER_ML-1M_*`):

| | examples/epoch | batches/epoch | epochs | **optimizer updates** |
|---|---:|---:|---:|---:|
| BSARec harness (their eliminating tests) | 268,032 | **1,047** | 27–53 | **≈28,000 – 55,000** |
| `PREREG_FIR_EFFICIENCY_ML1M_V1` (our null) | 1,033 | **5** | 20 | **≈100** |

> **283× to 555× more optimizer updates, and 259× more examples per epoch.**

The prereg specifies 20 epochs, batch 256, and **one example per user per epoch** over a **1,033**
retained-user cohort — hence ⌈1033/256⌉ × 20 = 100 updates. BSARec trains on **all prefixes**, hence
1,047 batches per epoch on the same corpus.

**Consequence.** Experiment 2 does not eliminate *"causal short kernels are too weak on ML-1M."* It
eliminates the much weaker *"causal short kernels are too weak on ML-1M **when trained for ~28,000+
updates on all prefixes**."* Our null was measured at ~100 updates on one example per user. The two
are not on a common axis, so the second elimination **does not hold as stated**.

Experiment 1 (circular filter, +0.0212) carries the same confound and additionally changes the
operator class, so it eliminates even less than claimed.

## 3. The candidate list is missing its most likely entry

Named: backbone, split. **Missing: training budget and example construction** — which is the
largest measured difference between the two settings by two orders of magnitude, and which is
already documented on this branch: the ML-1M cohort receives ~100 updates against **4,000–9,680** on
the Amazon campaigns (40×–96.8×), recorded in
[`CLAUDE_A4_MOVIELENS_NARROWING_V2_2026-08-01.md`](CLAUDE_A4_MOVIELENS_NARROWING_V2_2026-08-01.md).

The corrected list, ordered by measured magnitude:

1. **Training budget / example construction** — 283×–555× in updates, 259× in examples per epoch.
2. **Split** — 1,033 users at rating≥4 under a global cutoff vs 6,040 under LLOO.
3. **Backbone** — the filter is the only sequence mixer in FMLP-Rec; the FIR is a residual on
   self-attention in ours. *(The memo already notes FMLP-Rec's own Figure 3 shows their filter
   improving SASRec, which argues against this one before it is tested.)*

Note that (1) and (2) are not independent: the cohort restriction is what makes one-example-per-user
yield only 5 batches.

## 4. This lands on the test in flight — before it finishes

The memo announces a SASRec ladder on ML-1M to decide the backbone question: *"If FIR helps SASRec
there, the backbone explanation dies and the null is a property of the split."*

**That inference is not valid unless the budget is matched.** If the SASRec arms run at BSARec-like
budgets and FIR helps, the result is equally consistent with "the budget explains it" — the
conclusion "the null is a property of the split" would not follow. If they run at ~100 updates and
FIR does not help, that is consistent with the budget explanation and again does not isolate the
backbone.

**Recommendation (Codex-owned):** run the SASRec ladder at **both** budgets — ~100 updates and the
harness default — as an explicit 2×2 against arm. That converts a confounded one-way test into one
that can actually separate budget from backbone, at roughly double the cost of a test that currently
cannot answer its own question.

## 5. What the manuscript should say

The proposed narrowing:

> *"A causal FIR residual adds nothing given this backbone and this split."*

is an improvement on the current framing but is **still not supported**, because the budget was
never held fixed. The supported sentence adds one clause:

> A causal FIR residual adds nothing **given this backbone, this split, and this training budget**
> (~100 optimizer updates on a 1,033-user cohort). Filters reported in the ML-1M literature — and in
> our own harness runs — are trained for two to three orders of magnitude more updates on all
> prefixes; our null is therefore not evidence that temporal filtering fails on MovieLens.

**This strengthens rather than weakens the manuscript's position.** The current text reports the
ML-1M result as a failure to replicate, and the reviewer question the memo anticipates — *"the
literature shows ~25% relative filter gains on ML-1M, why is yours exactly zero?"* — is answered
better by a measured 283×–555× budget gap than by conceding a narrower scope. It converts an
apparent contradiction into a stated protocol difference.

## 6. What does NOT change

- The **counted claim boundary** is unchanged: Musical_Instruments (vs 0.0406) and Office_Products
  V3 (vs 0.0271 and 0.0279); **Office V1 VOID forever**; TFV2 outcome-visible, not confirmatory.
- The ML-1M verdict `ML1M-NO-FIR-REPLICATION` stands exactly as adjudicated. Nothing here reopens a
  sealed endpoint or revises a frozen analysis — this is about how the result is *narrated*.
- The null still **does not** license equivalence, and still **does not** license a domain moderator.
  It now licenses even less: it is a failure to replicate under a budget that is 283×–555× smaller
  than the setting the comparison invokes.

## Limits

Budget figures for the BSARec side are read from this machine's own `LADDER_ML-1M_*` logs (seed 42:
53 epochs `full`, 27 `shared`, 1,047 batches/epoch); the other run's causal-16-tap runs were not
available to me as logs, so I assume they used the same harness defaults as stated — if they did
not, the ratio changes but the confound remains until the budget is reported. The ~100-update figure
is arithmetic on the prereg's stated batch size, epoch count, and one-example-per-user rule against
the committed retained-cohort count, not a measured optimizer-step log. Advisory only; no artifact
modified, no sealed endpoint inspected.
