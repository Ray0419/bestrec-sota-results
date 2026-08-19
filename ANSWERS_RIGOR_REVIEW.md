# Answers to the rigor review's four questions — with evidence
### 2026-08-12 · campaign: 20 evaluation passes (15 inner-window, 5 outer sweeps) + 5 re-instrumented LOO decompositions · artifacts `q_answers.json`, `*.inner_eval.json`, `*.outer_sweep.json`, re-run `*.offset_decomp.json`
### Strides declared: MI 1, VG 2, STEAM 4 (deterministic every-Nth-event thinning)

---

## Q1 — Does the prediction survive out-of-sample? **PARTIALLY — and the failure is the finding.**

p\* estimated on the inner window (0.60–0.75 band, disjoint from and prior to the reporting window), applied to the outer window:

| dataset | p\*_inner (CI, n=5) | p\*_outer | **drift** | π_t_outer | predicts | measured E4_outer | **verdict** |
|---|---:|---:|---:|---:|---|---|---|
| MI | 30.8% [29.9, 31.8] | 55.4% | **+24.5pp** | 38.2% | pay | −0.00234, CI excl. 0 | **WRONG** |
| VG | 46.4% [42.7, 50.1] | 77.0% | **+30.6pp** | 77.8% | pay | +0.00017, CI spans 0 | boundary |
| Steam | 7.2% [6.4, 8.0] | 26.0% | **+18.9pp** | 40.2% | pay | +0.00099, CI excl. 0 | **CORRECT** |

Three facts, in order of importance:

1. **The reviewer's F01 concern is empirically vindicated, not just algebraically.** The in-sample "3/3 sign agreement" was an identity; the honest out-of-sample test goes 1 correct, 1 wrong, 1 boundary.
2. **p\* is temporally non-stationary with a consistent direction:** it *rose* +19 to +31pp between adjacent windows on all three datasets. The drift direction is the dangerous one — the criterion errs toward "pay" when estimated early.
3. **The criterion works exactly when the margin exceeds the drift.** Steam: π_t (40%) exceeded even the *drifted* p\* (26%) → prediction survived. MI: the drift (+24.5pp) carried p\* across π_t → prediction flipped. The usable form of the criterion is therefore: **deploy only if π_t > p\* + drift budget**, where the drift budget is measurable from adjacent historical windows — which is itself a new, quantified caution no prior work states.

**Paper consequence (F01 fix):** Table 5 reframed from "predicted all three regimes" to the in-sample identity + this out-of-sample stability analysis. Weaker headline, stronger paper.

## Q2 — Is the 93% figure metric-stable? **NO — and the principled unit makes offset dominance *stronger*.**

New instrument: full-catalog AUC in the LOO decomposition enables the **rank-displacement decomposition** — of the cold target's total upward rank movement, the share past *cold* competitors (offset-invariant, genuine) vs past *warm* competitors (offset-achievable):

| unit | genuine share (n=5, CI) |
|---|---:|
| top-10 NDCG (original) | 6.6% [3.8, 9.3] |
| **rank displacement (AUC units)** | **1.1% [1.0, 1.2]** |

The two disagree by 6× — the 93% was metric-specific, as suspected. But the correction cuts the *other* way: in pure rank-movement terms, **98.9% of imputation's effect is cross-pool displacement**. Reconciliation with E1's large coarse-signal gains: the genuine within-pool reordering is real and substantial *within its pool*, but the pool is ~13% of the catalog, so its contribution to total rank movement is numerically tiny beside the offset component. **F02 fix:** the abstract reports both units, scoped, with the coarse-signal qualifier pointing to §6.2.

## Q3 — Would a tuned fusion weight rescue the fusion arm? **NO — the harm is the method's, not the transfer's.**

Inner-window selection over w ∈ {0.05, 0.1, 0.2, 0.5, 1.0} on Steam is monotone decreasing and picks the *smallest* weight (w=0.05). On the outer window:

| arm | overall Δ vs stock |
|---|---:|
| tuned (w=0.05) | **−0.0097** |
| transferred (w=0.2) | −0.0105 |

Even the tuned weight is decisively harmful; tuning recovers only 8% of the damage. **The F03 confound resolves against my original claim:** "hyperparameter transfer is unsafe" was wrong — global score-level z-fusion is harmful on Steam at *any* tested weight (it injects text noise into a strong base ranker). §6.5 finding 2 rewritten accordingly.

## Q4 — Catalog share or score scale behind the warm-cost variation? **Score margins, decisively.**

New instrumentation: fraction of warm events whose top-10 gains ≥1 cold item under imputation (Δ vs stock), normalized per cold item:

| dataset | warm events invaded | cold items | **propensity per 1k cold items** | cold catalog share | stock warm NDCG |
|---|---:|---:|---:|---:|---:|
| MI | +81.5pp | 5,304 | **0.154** | 21.6% | 0.020 |
| VG | +80.1pp | 9,483 | 0.085 | 37.0% | 0.035 |
| Steam | +12.2pp | 3,804 | **0.032** | 31.7% | 0.150 |

Catalog share cannot explain it: Steam's cold share (31.7%) *exceeds* MI's (21.6%) yet its per-item invasion propensity is **5× lower**. The ordering tracks the margin proxy (stock warm NDCG 0.150 vs 0.020): strong warm rankings resist displacement. So p\*'s cross-dataset variation is margin-driven — which also predicts *where* the criterion has headroom: strong-baseline platforms tolerate cold promotion cheaply; weak-baseline catalogs cannot. (Exploratory: n=3 datasets; labeled as such in the draft.)

---

## Disposition

| review finding | disposition |
|---|---|
| F01 (critical) | **Confirmed empirically; draft reframed** — identity + stability analysis + drift-budget rule; correction #5 added to the in-paper log |
| F02 (major) | **Resolved with a new instrument** — both units reported; offset dominance strengthened (98.9% in rank units) |
| F03 (major) | **Resolved by the control; original claim retracted** — method-level harm, not transfer harm |
| Q4 | Mechanism quantified; margin-driven; added as exploratory |
