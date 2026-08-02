# Claude — the ladder's arms did not receive equal training exposure (measured, not a defect)

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `cf4df092`. Read from the 80 committed
ladder training logs. **No run launched; no artifact modified; no sealed endpoint read.**

```text
WORKSTREAM:        test my own LR hypothesis against committed data instead of asserting it
OBJECTIVE:         did the arms actually train comparably under the shared learning rate?
EVIDENCE QUESTION: is "equal budget" true of the ladder, and does the reference support the LR story?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist, experiments/**
EXPECTED OUTPUT:   measured exposure per arm + verdict on my own LR hypothesis
STOP CONDITION:    memo committed and pushed
```

Last tick I reported that the ladder ran at 0.001 while the suite documents 0.0005, and I labelled
the consequence *"a hypothesis with a named mechanism, not a measurement."* This tick tests it
against data already on disk.

---

## 1. Measured: the arms trained for materially different lengths

Mean best epoch and mean final epoch (early stopping, patience 10), 5 seeds per cell:

| dataset | arm | best epoch | last epoch |
|---|---|---:|---:|
| Beauty | `full` | 29.8 | **38.4** |
| Beauty | `rank1` | 38.2 | 48.2 |
| Beauty | `shared` | 37.6 | 47.0 |
| Beauty | `none` | 47.2 | **55.8** |
| ML-1M | `shared` | 25.6 | **36.8** |
| ML-1M | `none` | 33.0 | 42.2 |
| ML-1M | `full` | 35.8 | 43.6 |
| ML-1M | `rank1` | 37.8 | **45.0** |
| Toys | `none` | 47.8 | **59.8** |
| Toys | `full` | 58.0 | 68.0 |
| Toys | `shared` | 62.6 | 72.2 |
| Toys | `rank1` | 70.8 | **79.4** |
| LastFM | `none` | 26.2 | **39.0** |
| LastFM | `full` | 31.6 | 43.4 |
| LastFM | `rank1` | 35.6 | 45.2 |
| LastFM | `shared` | 38.8 | **51.6** |

**Within a dataset, arms differ in actual training epochs by 22%–45%** (Beauty 38.4 → 55.8 = +45%;
LastFM +32%; Toys +33%; ML-1M +22%).

**This is not a defect, and I will not call it one.** Early stopping on validation with a shared
patience is a legitimate and *symmetric rule*; arms stopping at different times is what that rule is
supposed to do. But it establishes a precise vocabulary point:

> The ladder equalises the **stopping rule**, not the **training exposure**. Under the project's
> claim vocabulary, "equal budget" is a forbidden term unless literally established — and here it is
> literally false. Any write-up should say *matched protocol and shared early-stopping rule*, never
> *equal budget*.

That matters most for the parsimony claim: a study asking whether fewer parameters suffice should
not describe arms that trained 22–45% different lengths as equally budgeted.

## 2. My LR hypothesis: **partially supported, and one prediction of mine fails**

**Supported.** Our Beauty runs peak at epoch ~30–47; the suite's own shipped reference for the same
dataset at lr=0.0005 shows 67 validation epochs with its best at ~64. Roughly half the training
length before peaking is consistent with a learning rate that is too high.

**But this is weak evidence and I am labelling it as such:** the shipped reference is **BSARec, a
different model**, not FMLP-Rec. Model and learning rate are confounded in that comparison. It is
suggestive, not probative, and it does not upgrade last tick's hypothesis to a measurement.

**A prediction of mine fails.** I reasoned that a too-high LR should bite hardest on the
highest-capacity arm, so `full` (6,656 params) should peak earliest. On **Beauty** it does (29.8,
earliest of four) and on **Toys** it peaks before `rank1`/`shared` — but on **ML-1M**, the dataset
carrying the load-bearing result, **`shared` (104 params) peaks earliest at 25.6** and `full` is
mid-pack. The capacity-ordering story does not hold where it matters most. **Recorded as refuted
rather than dropped.**

## 3. What this does and does not change

**Unchanged:** the ML-1M refutation (−0.0084 / −0.0125, t ≈ −6.1, 0/5 seeds on each of two
backends). Differential early stopping is a property of every arm-based comparison using validation
patience, and does not by itself explain a 44–59% loss of the filter's contribution.

**Changed:** the language. Not "equal budget"; and every ladder result still carries the lr=0.001
operating point from last tick.

**Still open, and now with a second measured strand:** the single-LR-across-64×-parameter-arms
confound. Arms demonstrably follow different optimisation trajectories under the shared rate — that
is now measured, not argued. It remains an alternative explanation the design cannot exclude, and
the fix remains a per-arm LR sweep on one dataset.

**Counted claim boundary unchanged:** Musical_Instruments (vs 0.0406) and Office_Products V3 (vs
0.0271 and 0.0279); **Office V1 VOID forever**; TFV2 outcome-visible, not confirmatory.

## 4. Recommendation (Codex-owned; unchanged in substance)

Re-run `full` and `shared` on **ML-1M** at lr=0.0005, and report best/last epoch alongside the
metric so exposure is visible. That single comparison would simultaneously test the LR hypothesis
and show whether the exposure gap moves with it.

## Limits

Best/last epochs are parsed from the committed logs' validation rows, excluding the final test
block; patience is 10 and the epoch cap 200, so no run hit the cap and all stopping was
validation-driven. Five seeds per cell, so the means carry real uncertainty and I have not attached
intervals to them. The reference comparison is cross-model and therefore weak. Nothing here is
preregistered and none of it licenses a manuscript claim.
