# Cross-backend reconciliation of the filter ladder: headline replicates, percentages do not

**STATUS: EXPLORATORY, NOT PREREGISTERED. Licenses no manuscript claim.**
Date: 2026-08-02. Branch `claude/filter-overparam-experiments`, merge `ca779a5d`.

Two independent executions of the **same** pre-declared protocol now exist on this branch:

| run | backend | source |
|---|---|---|
| **A** | LastFM on CPU, Beauty / Toys / ML-1M on **MPS** (Apple Silicon) | `f314f663`, recorded in `CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md` §7–8 |
| **B** | **all four datasets on CPU** (Windows, 20 cores) | `6390ff3f`, per-run scores in `experiments/filter_overparam/results_ladder_2026-08-02.csv` |

Same harness (BSARec `c80bdc0`), same patch, same arm parameter counts, same seeds 42–46, same
decision rules declared at 0/80. This is therefore a **backend replication**, and it is worth more
than either run alone.

---

## 1. Mean NDCG@10 side by side

| dataset | arm | run A (MPS) | run B (CPU) | Δ |
|---|---|---:|---:|---:|
| LastFM | full | 0.0324 | 0.0347 | +0.0023 |
| | shared | 0.0345 | 0.0332 | −0.0013 |
| | none | 0.0290 | 0.0290 | 0.0000 |
| Beauty | full | 0.0300 | 0.0286 | −0.0014 |
| | shared | 0.0286 | 0.0290 | +0.0004 |
| | none | 0.0243 | 0.0237 | −0.0006 |
| Toys | full | 0.0375 | 0.0377 | +0.0002 |
| | shared | 0.0360 | 0.0365 | +0.0005 |
| | none | 0.0275 | 0.0272 | −0.0003 |
| ML-1M | full | 0.1095 | 0.1064 | −0.0031 |
| | shared | 0.0970 | 0.0980 | +0.0010 |
| | none | 0.0883 | 0.0875 | −0.0008 |

## 2. What replicates — the verdict

| finding | run A | run B | agree? |
|---|---|---|---|
| LastFM **VOID** under the validity gate | yes | yes | **yes** |
| `shared` (64×) fails on **ML-1M** | −0.0125 | −0.0084, t=−6.11, 0/5 seeds | **yes** |
| ML-1M has the **largest** filter effect | +0.0212 | +0.0189 | **yes** |
| Noninferiority established on **no** dataset | yes | yes | **yes** |
| `rank1` (18×) loses less than `shared` | yes | yes | **yes** |
| Filter is low-rank (SVD) | yes | eff. rank 1.19–1.64 / 26 | **yes** |

**The core conclusion is backend-independent: the 64× channel-tied claim is refuted, and ML-1M is
where it dies.** That is a stronger basis than one run, and it survives.

## 3. What does NOT replicate — the per-dataset percentages

Run A reports channel-tying costing a fixed share of the filter's contribution: **Beauty 24%,
Toys 15%, ML-1M 59%**. Recomputing the same ratio from run B:

| dataset | run A "tying cost" | run B tying cost | agree? |
|---|---:|---:|---|
| Beauty | **−24%** | **+8%** (i.e. `shared` *above* `full`) | **NO — sign flips** |
| Toys | −15% | −11% | roughly |
| ML-1M | −59% | −44% | direction yes, magnitude loose |
| LastFM | +62% (VOID) | −25% (VOID) | moot — both VOID |

**Beauty's sign inverts between backends.** Run A has `shared − full` = −0.0014 (t = −1.68); run B
has **+0.0004** (t = +0.48). Run A's own text concedes the point — *"the losses are not
individually significant at n=5 (t = −1.68, −1.18)"* — and run B shows what that non-significance
means in practice: on a different backend the same contrast changes sign.

**Consequence for reporting.** The table framing "channel-tying costs 15–59% of the filter's
contribution" reads as four measurements of one quantity. Only **ML-1M's is robust** (significant in
B, large in A). Beauty's is not reproducible even in sign, Toys' is directionally stable but
non-significant in both, and LastFM's is VOID. **The honest headline is a single decisive failure on
ML-1M, not a 15–59% range across benchmarks.** I recommend run A's summary table carry the
significance of each cell, or drop the percentages for the non-significant datasets.

## 4. Why the backends differ — and why it does not rescue anything

Differences of 0.001–0.003 NDCG@10 between MPS and CPU on identical seeds are unremarkable:
non-deterministic reduction order, different BLAS/kernel paths, and fused-op differences. They are
**smaller than the effects the study cares about on ML-1M** (−0.0084 to −0.0125) and **larger than
the effects on Beauty** (±0.0004 to −0.0014). That is precisely the diagnosis: the study is
adequately powered for ML-1M and underpowered everywhere else, so backend noise dominates exactly
where the conclusions were weakest.

This does **not** rescue the 64× claim. It refines *which* refutation is trustworthy.

## 5. Reproduction anchor — the two runs disagree here too

Published FMLP-Rec Beauty HR@10 is **0.0618**. Run A gets **0.0575** (≈7% low); run B gets
**0.0553** (≈10.5% low). Neither matches, both are low, and the pre-declared anchor still states no
numeric tolerance, so "near" cannot be applied mechanically by either run. **The gap is real,
consistent in direction across two backends, and unresolved.** Every conclusion above remains
conditional on `full` being a faithful FMLP-Rec.

## 6. Standing

Nothing here changes the counted claim boundary of the FIR manuscript, and nothing here is
preregistered. What it establishes is narrower and useful: **the ladder's central negative result
replicates across two backends, while its quantitative per-dataset framing does not.** Report the
former; qualify the latter.

## Limits

Run A's per-run scores were not available to me as a machine-readable file, so its arm means are
read from its own recorded summary table rather than recomputed from logs; run B's 80 per-run scores
are committed as CSV. Seed-level pairing across backends was therefore not possible — this compares
arm means, not paired differences. Both runs are same-investigator and neither is independent
confirmation.
