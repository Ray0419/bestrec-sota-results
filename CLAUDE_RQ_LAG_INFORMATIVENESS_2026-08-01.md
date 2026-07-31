# Claude memo — a candidate Tier-A research question: order-dependence is not lag-informativeness

> **SUPERSEDED 2026-08-01 — DO NOT ACT ON §1–§3.** Phase 0a was run and the §1 dissociation is
> **REFUTED**: it was an artifact of sequence-length confounding. Under matched controls the
> relationship reverses sign. See [`CLAUDE_PHASE0A_RESULT_2026-08-01.md`](CLAUDE_PHASE0A_RESULT_2026-08-01.md).
> The memo is retained unaltered below as the record of a hypothesis that was killed by its own
> pre-committed test. §4 (the novelty sweep) remains valid and reusable.

**STATUS: EXPLORATORY, POST-HOC, NOT PREREGISTERED.** Licenses no manuscript claim. Nothing here
is a countable result. No repo artifact was modified other than this file.

Date: 2026-08-01. Role: scientific red-team. Advisory only.

```text
WORKSTREAM:        find a genuinely novel, Tier-A-publishable research question that reuses
                   the existing FIR evidence surface
OBJECTIVE:         state one question, establish its novelty by sweep, and scope its experiment
EVIDENCE QUESTION: is there a construct the field currently conflates, which our own data
                   already dissociates?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   one question + novelty evidence + experiment scope + kill conditions
STOP CONDITION:    memo committed
```

This memo discharges the sweep that `CLAUDE_DECOMPOSITION_CAVEATS_2026-08-01.md` (Caveat 1)
listed as *required before any prereg*.

---

## 1. The anchoring observation

The field's standard dataset-level sequentiality diagnostic and our own module-level effect
measurements **point in opposite directions**.

**Their diagnostic** (Klimashevskaia et al., *An Analysis of Sequential Patterns in Datasets for
Evaluation of Sequential Recommendations*, **ACM TORS 2025**, `10.1145/3787969`; arXiv 2408.12008)
shuffles user sequences and measures whole-model degradation:

| dataset | SASRec NDCG@10 shuffle Δ | GRU4Rec Δ | Jaccard@10 | their verdict |
|---|---:|---:|---:|---|
| **ML-20m** | **−59%** | **−61%** | **0.12** | **STRONG sequential structure** |
| Beauty | −43% | −26% | 0.24 | moderate |
| Games | −38% | −17% | 0.22 | moderate |
| Sports | −32% | −18% | 0.26 | moderate |

**Our measurements** of a causal FIR lag module under a matched harness
(`fir_controls_adjudication.json`, `fir_efficiency_ml1m_v1_adjudication.json`, verified in-repo):

| corpus | learned FIR − identity | 95% CI | p |
|---|---:|---|---:|
| **MovieLens 1M (r≥4)** | **+0.00000020** | **[−0.0000742, +0.0000746]** | **.995** |
| Musical_Instruments | +0.002116 | [+0.001910, +0.002322] | 5.1e-08 |
| Industrial_and_Scientific | +0.002110 | [+0.001820, +0.002399] | — |
| CDs_and_Vinyl | +0.006150 | [+0.005849, +0.006450] | — |

**The dissociation is not a power failure.** The ML-1M interval excludes any effect larger than
±7.5e-05 — roughly **1/28th** of the Musical_Instruments effect and **1/82nd** of CDs_and_Vinyl.
We can affirmatively rule out an Amazon-sized effect on the corpus the field calls *most*
sequential. That is a positive finding about a boundary, not an absence of evidence.

---

## 2. The construct the field conflates

Shuffle-degradation measures whether **the whole model's accuracy depends on order**. A model can
be almost entirely order-dependent through **recency alone** — which item is last — with no
dependence whatsoever on the **shape of the profile across lags**. Those are different properties
and the field measures only the first.

> **Order-dependence** — does permuting the history change the prediction?
> **Lag-profile informativeness (LPI)** — conditional on the most recent item, do items at lags
> 2..L carry additional, *differentially weightable* signal?

An FIR filter is a device that can exploit only the second. It is a weighted sum over lags; if the
optimal weighting is a delta at lag 1, the filter's best achievable behaviour **is** identity — which
is exactly what we measure on ML-1M, including seeds where arms are bit-identical to identity.

This makes the dissociation mechanistically expected rather than anomalous:

- **ML-1M (r≥4)**: dense, long, session-like histories; heavy popularity mass; order matters
  enormously via recency, so shuffle-degradation is huge — but the lag profile beyond lag 1 is
  flat, so FIR has nothing to fit. **High order-dependence, low LPI.**
- **Amazon categories**: sparse, long inter-event gaps, weaker overall order-dependence — but what
  structure exists is *distributed across lags* (co-purchase cascades, accessory-after-instrument),
  which is precisely FIR-shaped. **Moderate order-dependence, high LPI.**

**Corroborating internal evidence for the low-dimensionality half of the story:** our `shared`
filter (**16** trainable parameters) matches or beats `learned` (**1,024**) on both MI validation
(0.04619 vs 0.04600) and the MI controls campaign (0.041524 vs 0.041442). If the informative lag
structure were rich and channel-specific, 16 parameters could not do this. It is consistent with
the informative part of the lag profile being **low-dimensional and shared across channels** — a
result `CLAUDE_F6` already flagged as under-sold, and which this framing finally gives a job to do.

---

## 3. The research question

> **RQ.** Does a dataset's order-dependence — as measured by the field's standard shuffle-based
> sequentiality diagnostics — predict whether an explicit temporal-lag module improves a sequential
> recommender? If it does not, what training-free property does, and does that property's
> prediction hold **prospectively** on corpora whose outcomes were never inspected?

Decomposed:

- **RQ1 (dissociation).** Across N corpora under one matched harness, is the FIR effect size
  statistically unrelated to — or inversely related to — shuffle-based sequentiality, after
  controlling for density, catalog size, and mean history length?
- **RQ2 (construct).** Define and validate **lag-profile informativeness**, a training-free
  statistic that separates recency-only order-dependence from distributed-lag structure. It must
  be computable from the training split alone, with no model fit.
- **RQ3 (prospective validation).** Freeze an LPI-based point prediction with an interval for the
  FIR effect on K held-out corpora *before acquiring their outcomes*; run; adjudicate. Pre-declare
  that shuffle-sequentiality is the competing predictor and that it is expected to fail.

**Falsifiable and pre-registrable in one sentence:** *LPI predicts the sign and magnitude of a
temporal module's effect out-of-sample; shuffle-based sequentiality does not.*

### Candidate LPI operationalisations (RQ2 must pre-declare one primary)

1. **Conditional lag gain.** `I(target ; item_{t-k} | item_{t-1})` for k=2..L, estimated by counts
   with shrinkage. Primary summary: the mass above lag 1. Directly encodes "beyond recency".
2. **Residual-lag predictive gain.** Fit a lag-1-only linear item-item model; measure the
   incremental fit from adding lags 2..L. Cheap, closed-form, no SGD — and reuses the EASE
   machinery already validated in this repo.
3. **Spectral flatness** of the lag-autocorrelation of the frozen SBERT item-embedding sequence.
   Ties LPI to the FIR transfer function directly; the most mechanistically faithful, the most
   sensitive to preprocessing.

A shuffle-based *placebo* for LPI (recompute on shuffled sequences; LPI must collapse) is the
natural internal validity check and mirrors the active-control discipline already used in `FIRCTRL`.

---

## 4. Novelty — sweep performed and what it found

Searches run across arXiv listings, TORS/TOIS/SIGIR/RecSys 2025–2026, and the frequency-filtering
lineage (FMLP-Rec → BSARec → successors), as Caveat 1 required.

| nearest work | what it occupies | why the RQ survives |
|---|---|---|
| **Klimashevskaia et al., TORS 2025** (2408.12008) | dataset-level sequentiality via shuffle; 15 datasets | **Whole-model only** — explicitly does not isolate any architectural component; **explicitly no out-of-sample or prospective claim**. Its own stated future work is whether algorithm conclusions change once datasets are properly selected. We are the counterexample to its implicit premise. |
| **MUFFIN**, CIKM 2025 (2508.13670) | user-adaptive frequency filtering, MoE gating over shared base filters | A *method* paper. Occupies the "user-adaptive" axis of the older decomposition question. No failure-mode or null-effect analysis; no dataset-level predictor. |
| **WEARec** (2511.07028), **HyTiFRec**, **TV-Rec** (2510.25259), FEARec/SLIME4Rec lineage | better filters, more expressive filters, time-variant filters | All pursue "our filter wins". None asks *when a filter can win at all*. TV-Rec reports no corpus where its filter fails. |
| **"Does It Look Sequential?" successors**; **shortcut-heuristic benchmark critique** (2605.07125) | benchmark difficulty, shortcut-solvability | Diagnoses *benchmarks*, not *module–dataset interaction*. Same genre, different object. |
| **Bradley-Terry rankings across dataset taxonomies** (2606.07492) | model ranking shifts by dataset taxonomy incl. a Sequentiality axis | **Whole-model ranking**, retrospective. Confirms rankings are dataset-dependent; does not decompose to components or predict prospectively. |
| **Algorithm selection via meta-learning** (2508.04419, 2409.05461) | meta-features → pick best *algorithm* | Algorithm selection, not component necessity. Retrospective CV, not frozen prospective prediction. |
| **AdaCap** (2511.20170) | meta-predictor of *when a method helps*, from dataset characteristics — 85 tabular regression datasets | **The strongest precedent, and it helps us.** It proves the genre is publishable and the design is sound, in a different field, retrospectively. The recommender instantiation is unoccupied, and no version of it anywhere is prospectively frozen. |

**What is genuinely unoccupied, stated narrowly:**

1. No work relates a **dataset statistic** to the **effect size of a specific architectural
   component** in sequential recommendation. Every diagnostic paper stops at whole-model accuracy.
2. No work distinguishes **order-dependence** from **lag-profile informativeness**; the field's
   diagnostics silently assume they are the same quantity.
3. No preregistered, prospectively adjudicated predictive claim exists anywhere in sequential
   recommendation. Our sweep for preregistration in IR/RecSys returned only information-systems
   and psychology methodology — the practice is effectively absent from this field.

**Honest limits on the novelty claim.** This is a broad sweep, not an exhaustive one. Absence from
search results is not proof of absence; I did not read every 2026 proceedings volume, and
non-English and workshop venues were not covered. Points 1–3 should be re-checked immediately
before any prereg is frozen, and again at submission.

---

## 5. Why this is Tier-A shaped, and why it fits *this* repository

1. **It needs no architectural novelty.** The FIR control ladder — identity / fixed_ma / fixed_hp /
   nonlinear / learned / shared / grouped / lowrank / pointwise-placebo — already exists, is
   already adjudicated, and becomes the **measurement instrument** rather than the contribution.
   The costly, risky part is already built and audited.
2. **It converts the repository's biggest liability into its load-bearing asset.** The ML-1M null
   is currently a caveat the manuscript must survive. Under this RQ it is the anchor datapoint —
   and it is *prospectively frozen*, which is exactly what makes it credible as one.
3. **It gives the 16-parameter result a job.** `shared ≥ learned` stops being an oddity and becomes
   a prediction of the low-dimensional-LPI hypothesis.
4. **It plays to the one thing this repo has that no competing lab does**: version-controlled
   pre-declaration, fail-closed artifact gating, and symmetric self-VOIDing. RQ3 is not merely
   compatible with that machinery — it is **impossible to do credibly without it**, and the
   machinery is already built, exercised, and adversarially audited.
5. **Venue fit is direct.** TORS published the very diagnostic paper this question extends, and
   publishes measurement/reproducibility work as first-class contributions. The paper is a
   measurement contribution with a prospective validation — not a leaderboard entry, which is
   fortunate, since §5 of the current manuscript already concedes we do not win leaderboards.

---

## 6. Experiment scope

**Phase 0 — kill-or-continue, cheap, before any prereg is drafted.**

- **0a.** Recompute the TORS shuffle diagnostic (SASRec + GRU4Rec, NDCG@10 Δ, Jaccard@10) on
  **our exact ML-1M (r≥4) split and our exact Amazon splits**. *Their number is ML-**20m**, not
  ML-**1M**, and not rating-filtered.* If our ML-1M is not in the strong tier under our own
  preprocessing, **the headline dissociation evaporates and this RQ dies here.** This is the single
  highest-value check in the memo and must be run first.
- **0b.** Compute all three candidate LPI statistics on the four corpora with known FIR effects.
  Continue only if at least one orders `{ML-1M} < {MI, IS, CDs}` and its shuffled placebo collapses.
- **0c.** Confirm the bit-identical-seed pattern on ML-1M is filter-output degeneracy and not a
  logging or seeding artifact. A trivial explanation here would be fatal and cheap to find now.

**Phase 1 — breadth (the real cost).** N ≥ 12 corpora. Four exist. Eight or more must be acquired
across genuinely different regimes — e-commerce, music/streaming, POI/check-in, and at least two
non-Amazon, non-MovieLens sources — since a predictor fitted on 4 points is not a predictor.
The existing `TIER_A_NON_AMAZON_SELECTION_GATE.md` metadata/legal/custody gate governs selection
and must run **before** outcomes are visible.

**Phase 2 — prereg + prospective test.** Freeze the primary LPI definition, the predictive model,
the point predictions with intervals, and the competing shuffle-sequentiality predictions, for
K ≥ 4 held-out corpora. Then run. Then adjudicate through the existing fail-closed gate.

### Kill conditions (pre-committed, so they cannot be renegotiated later)

- **0a fails** → dissociation is an artifact of comparing ML-20m to ML-1M. **Abandon.**
- LPI's shuffled placebo does **not** collapse → the statistic measures something other than lag
  structure. **Abandon or redefine before Phase 1.**
- LPI's apparent effect is fully explained by density / catalog size / mean history length →
  **downgrade** to "a known confound explains module benefit", which is a much smaller paper and
  should be reported as such rather than dressed up.
- Prospective predictions in Phase 2 miss their intervals → **report the miss**. Under this design
  a failed prediction is still a publishable, and honest, result — which is the entire point of
  freezing it in advance.

---

## 7. Risks I judge material

- **Corpus acquisition is the schedule risk**, not the science. Eight-plus new corpora with legal
  and custody clearance is the dominant cost, and this repository's history suggests acquisition
  timelines are consistently underestimated.
- **Three of four current effect estimates are outcome-known.** Only ML-1M was prospective. The
  predictor's fitting set is therefore partly outcome-contaminated and this must be declared in the
  prereg, with the held-out set genuinely sequestered. Reviewers of this repository have caught
  exactly this class of leakage before (E-G, E-G2).
- **One backbone, one metric.** Generality beyond the SASRec+SBERT harness at NDCG@10 is asserted,
  not shown. Either add a second backbone in Phase 1 or scope the claim explicitly to the harness.
- **Sequencing.** Caveat 3 of the decomposition memo stands unchanged and applies here identically:
  the FIR manuscript should be **submitted or explicitly abandoned** before this prereg is frozen.
  This RQ is stronger than the decomposition question, which makes it *more* likely to become the
  next reason nothing ships. That is a decision for the maintainer, and it should be a stated
  decision rather than drift.

## Limits

Exploratory, post-hoc, not preregistered. The dissociation in §1 compares **their ML-20m numbers to
our ML-1M numbers** and is therefore **suggestive only until Phase 0a is run** — this is the
memo's weakest link and I have not hidden it. Prior-art sweep is broad but not exhaustive. No LPI
statistic has been computed on anything yet; §2's mechanistic story is a hypothesis with a
consistency argument, not a measurement. Nothing here licenses a manuscript claim; it licenses only
a decision about whether to spend Phase 0.
