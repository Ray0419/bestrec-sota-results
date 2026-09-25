# When Does Cold-Start Intervention Pay?
## Offset degeneracy, offset-invariant instruments, and a predictive break-even criterion for new-item recommendation

**Draft v0.1, 2026-08-12 — TOIS target (fallbacks IP&M, TORS).**
**Mode: absorb-with-credit** (companion workstream's theorem + protocol cited as in-repo artifacts; upgrade to co-drafted merge if that workstream resumes before submission — reversibility documented in the coordination log).
**Every number in this draft traces to an artifact in `_bestrec_run/poc_out/`; pre-registrations frozen before each campaign: `PREREG_DOSE_RESPONSE_V1`, `PREREG_SCALING_V1`, `PREREG_TEMPORAL_V1`, `PREREG_STEAM_V1`.**

---

### Abstract (draft)

Cold-start evaluation in recommender systems rewards an intervention that learns nothing. We build on a target-conditioned *offset degeneracy* proposition [companion artifact, credited]: adding a constant to every cold item's score leaves the ordering *within* the cold pool exactly invariant, yet monotonically inflates cold-target full-catalog metrics while deflating warm-target ones. We confirm the proposition empirically — within-cold NDCG@10 invariant to five decimal places across offsets while cold-target NDCG rises from 0.000 to 0.022 — and show its consequence: ~93% of a standard content-imputation method's cold-target top-10 metric gain on Amazon data is this nuisance offset (98.9% when measured in rank-displacement units), even though the method simultaneously carries substantial genuine *coarse* relevance within the cold pool (§6.2) — the offset dominates because the cold pool is a small fraction of the catalog. We contribute two offset-invariant instruments — within-pool AUC (replacing rank-among-cold protocols, which we show degenerate on small pools) and the *offset-matched efficiency ratio*, a scalar that reads 1.0 for any method that merely shifts the pool. Applying them under a temporally valid protocol with first-availability constraints [companion design, credited], we establish: (i) genuinely new items are unrankable (NDCG exactly 0) across three datasets; (ii) content imputation carries real but *coarse* relevance (within-pool AUC gains +0.02 to +0.12, all seeds, CIs excluding zero) at efficiency 1.5–2.7× a parameter-free offset; (iii) the break-even cold prevalence follows p\* ∝ N_cold^0.84, so catalog growth cannot outrun the cost; and (iv) the resulting criterion — compare measured p\* to observed cold prevalence π_t — holds by construction in-sample, so we test it **out-of-sample in time**: p\* estimated on an earlier window predicts the later window's aggregate sign correctly when the margin is large (Steam), fails when it is small (Musical Instruments), and we identify why — **p\* drifts upward by 19–31 percentage points between adjacent windows on all three datasets**, always in the optimistic direction. The deployable criterion is therefore π_t > p\* + drift budget, with the drift measurable from historical windows; we quantify the drift's mechanism (warm-margin-driven invasion propensity varying 5× across platforms) and provide the first measurement of this stability budget.

---

## 1. Introduction

- The seesaw between cold and warm performance is known; what is not known is that the *metrics themselves* cannot distinguish genuine cold learning from a pool-level score shift (§3), and that the field's cold-target gains are largely the latter (§6.1).
- Contributions, in order of load-bearing weight:
  1. Empirical confirmation of offset degeneracy on a trained sequential backbone (the proposition's first large-scale test).
  2. Two offset-invariant instruments + the demonstration that rank-among-cold-items protocols degenerate on small pools (a 658% "genuine share" from within-pool NDCG@10 at N=85).
  3. The decomposition: ≈6.5% (CI [3.4, 9.7]) of measured cold benefit is genuine at N_cold≈3k; efficiency ratio 1.61 ± 0.07.
  4. The break-even law p\* ∝ N^0.843 ± 0.015 (controlled nested-pool sweep; an earlier √N estimate is retracted in §8 as an eligibility confound).
  5. The three-regime crossover under temporal validity (the headline, Table 5).
- Explicitly *not* contributed: any new architecture; the degeneration mechanism (representation degeneration is prior art, cited in §2); the temporal protocol (companion artifact, credited).

## 2. Related work

- **Learned popularity/maturity gates** (GateSID, DCGL, SPARK, FAERec): all tune what our instruments measure; none report offset-invariant quantities.
- **Cold-start families** (DropoutNet, Heater, CLCRec, ALDI, content-init "Let It Go", Warmer-for-Less, stochastic gates, DiffCold's seesaw): report cold-target gains our §6.1 shows are offset-dominated.
- **Representation degeneration** (Gao et al. 2019; "Rare Tokens Degenerate All Tokens" ACL 2022; popularity-direction in BPR, arXiv:2512.10688): the *mechanism* behind unrankability — cited, not claimed; our contribution is the bridge to evaluation (a shared direction cancels within-pool but not cross-pool, which is why the offset repair is so effective and so misleading).
- **Evaluation-rigor tradition** (Dacrema et al.; diffusion-reproducibility TORS 2026; BERT4Rec replicability): we extend it from "baselines are undertuned" to "the metric credits a nuisance transformation."
- **Interventional degree work** ("Recommendation Is a Dish Better Served Warm", 2508.07856): closest prior intervention; differs in per-level retraining vs our within-run multi-dose design, dynamic vs frozen eval, and no text-vs-ID contrast.
- **Companion artifacts** (this repository): offset-degeneracy proposition and the global-time protocol with first-availability constraints; full credit and provenance in §9.

## 3. Offset degeneracy, and its empirical confirmation

- Proposition restated [credited]. Empirical test (Table 1): MI, 3,121-item cold pool — within-cold NDCG@10 = 0.02329 at every offset δ ∈ {0,…,8} (invariant to 5 dp); cold-target full-catalog NDCG 0.00000 → 0.02165; warm 0.04362 → 0.01025 (−76%).
- Consequence: any evaluation conditioning targets on cold status and ranking against the full catalog is gameable by one parameter.

## 4. Instruments

- **Within-pool AUC** = 1 − r/(N−1): cutoff-free, pool-size-free, exactly offset-invariant. Table 2: the metric it replaces (within-pool NDCG@10) reads 6.6% / 70% / 658% "genuine share" at N = 3121 / 649 / 85 — the last mathematically impossible — while AUC gains are stable (+0.02 to +0.12) across a 37× pool range.
- **Offset-matched efficiency ratio** = (warm cost per unit cold gain of the best pure offset) ÷ (same for the method). =1.0 for a disguised offset; >1.0 iff genuine relevance. Includes the coarse-vs-fine caveat: content improves AUC ≈4× more than top-rank precision (§6.2).

## 5. Experimental setup

- Backbone: HSTU-style sequential model, chunked full softmax, MiniLM text channel (house configuration, unchanged across all campaigns).
- Datasets: Amazon Musical Instruments (57k users / 24.6k items), Amazon Video Games (95k / 25.6k), **Steam** (334,325 / 12,012 / 4.21M actions after 5-core; adapter reproduces the published SASRec-paper shape; sanity gate: LLOO NDCG@10 = 0.0578, inside the published full-ranking implementation band 0.0546–0.156).
- Temporal protocol [credited]: pooled-quantile cutoffs (0.60 selection / 0.75 reporting), cold = first appearance after cutoff, per-event histories, first-availability candidate masking (bucketed monotone implementation, O(buckets × items)).
- Discipline: frozen preregs with kill criteria; across-seed t-intervals with sign counts; 5-seed gates on every reported endpoint; corrections logged (§8).

## 6. Results

### 6.1 The decomposition (LOO, MI, 5 seeds × 2 pool configs)
Genuine share of the cold-target gain, by unit: **6.6% ± 2.2** (top-10 NDCG units, CI [3.8, 9.3]) and **1.1% ± 0.1** (rank-displacement units — the share of the target's total upward rank movement that passes *cold* competitors, CI [1.0, 1.2]). The offset component dominates in every unit; the two shares differ 6× because top-10 metrics weight the pool head. Efficiency ratio 1.609 ± 0.067 (CI [1.513, 1.704]) and 1.736 ± 0.189 — 10/10 seed-runs, both CIs exclude 1.0.

### 6.2 Coarse vs fine
AUC gain +0.0348 ± 0.0022 (N=3121) / +0.0333 ± 0.0091 (N=455), 10/10. Within-pool NDCG@10 gain +0.00095 (CI excl. 0) at the larger pool but sign-unstable at the smaller — content's top-rank benefit is real but ≈4× weaker than its coarse discrimination gain, explaining the literature's strong-recall/weak-NDCG pattern for content methods.

### 6.3 The break-even law (controlled nested-pool sweep, 4 sizes × 3 seeds)
p\* ∝ N^0.843 ± 0.015 (CI [0.806, 0.881], 3/3); components c ∝ N^0.72, g ∝ N^−0.34, ratio ∝ N^−0.35 (3.2 → 1.5 across 243 → 2,153). Since prevalence grows ≈ linearly, the margin improves only ≈ N^0.16: **more cold items never make imputation free**.

### 6.4 The break-even criterion: in-sample identity, out-of-sample stability (temporal protocol, all n=5)

**In-sample accounting (holds by construction).** Because E4 = π_t·g − (1−π_t)·|c| and p\* is defined as its zero, the same-window comparison of p\* to π_t cannot disagree with E4's sign; we report it as the decomposition it is:

| dataset | π_t | p\*_same-window (CI) | measured E4 (CI) | seeds |
|---|---:|---:|---|---|
| MI | 38.2% | 55.4% [54.1, 56.6] | **−0.00234** [−0.00242, −0.00227] | 0/5 |
| VG | 77.8% | 77.0% [75.9, 78.1] | +0.00017 [−0.00004, +0.00037] | 4/5 |
| Steam | 40.2% | 26.0% [24.5, 27.5] | **+0.00099** [+0.00088, +0.00111] | 5/5 |

**Out-of-sample test (the real question).** p\* estimated on the earlier 0.60–0.75 window, applied to the later reporting window:

| dataset | p\*_inner (CI, n=5) | drift to p\*_outer | π_t | predicts | outcome |
|---|---:|---:|---:|---|---|
| MI | 30.8% [29.9, 31.8] | **+24.5pp** | 38.2% | pay | **wrong** (E4 < 0) |
| VG | 46.4% [42.7, 50.1] | +30.6pp | 77.8% | pay | boundary (E4 CI spans 0) |
| Steam | 7.2% [6.4, 8.0] | +18.9pp | 40.2% | pay | **correct** (E4 > 0) |

The criterion predicts correctly **iff the margin |π_t − p\*| exceeds the temporal drift of p\***, which rose 19–31pp between adjacent windows on all three datasets — always optimistically. The deployable rule is π_t > p\* + drift budget, the budget measurable from historical windows. **Mechanism (exploratory, n=3 datasets):** the warm cost behind p\* is margin-driven — under imputation, cold items invade 81.5pp of MI's warm-event top-10s but only 12.2pp of Steam's (per-cold-item propensity 0.154 vs 0.032 per 1k, a 5× gap that catalog share cannot explain, tracking stock warm NDCG 0.020 vs 0.150). Strong-baseline platforms tolerate cold promotion cheaply; weak-baseline catalogs cannot.

E1 (AUC gain) and E2 (efficiency ratio) confirmed on all three datasets (Steam: +0.113 ± 0.012; 2.74, CI [1.18, 4.30] — exceeds 1.0, magnitude imprecise at n=5); stock cold NDCG exactly 0.00000 on all three.

### 6.5 Method family under the instruments (Steam, temporal protocol, n = 5)

| arm | Δ within-pool AUC (CI) | seeds | Δ overall NDCG@10 (CI) | seeds | verdict |
|---|---|---|---|---|---|
| text-kNN imputation | **+0.1129** [+0.0977, +0.1281] | 5/5 | **+0.000994** [+0.00088, +0.00111] | 5/5 | genuine signal **and** net gain |
| ridge imputation | **+0.1063** [+0.0898, +0.1227] | 5/5 | **0.000000** [0, 0] | 0/5 | genuine signal, **zero realized benefit** |
| z-fusion (w=0.2, transferred untuned) | **−0.0827** [−0.0913, −0.0742] | 0/5 | **−0.0105** [−0.0142, −0.0067] | 0/5 | harmful off-domain |
| pure offset (any δ) | 0 by construction | — | see §3 | — | the null model |

Three findings the instruments produce that a cold-target metric cannot:
1. **Knowledge ≠ rankability.** Ridge and kNN carry statistically indistinguishable genuine coarse signal, yet ridge converts *none* of it into top-10 ranking (its calibrated-but-generic rows never enter the rankable region), while kNN converts its signal into the only net-positive aggregate in the family. A cold-target NDCG table would call ridge "useless" and miss that its information content equals the winner's — the correct engineering response to ridge is a rescoring stage, not abandonment.
2. **The fusion arm's harm is the method's, not the transfer's.** A tuned-weight control (inner-window selection over w ∈ {0.05, …, 1.0}, monotone decreasing, selecting w = 0.05) recovers only 8% of the damage: even the tuned weight is decisively harmful on the outer window (−0.0097 vs stock; transferred w = 0.2: −0.0105). Global score-level z-fusion injects text noise into a strong base ranker regardless of weight. *(This replaces an earlier "hyperparameter transfer is unsafe" reading — retracted after the control isolated the cause; corrections log #6.)*
3. **The ranking of methods by cold-target NDCG and by genuine signal differ**, which is the practical face of offset degeneracy (§3).

### 6.6 Trained cold-start methods: a stronger form of the unrankability result (MI, temporal protocol, 3 seeds/arm)

Three *trained* arms on the identical backbone, pre-registered ([PREREG_TRAINED_V1.md](PREREG_TRAINED_V1.md)) before running: **T1** content-anchor (frozen text base + norm-clipped trainable delta; "Let It Go"-style, credited), **T2a** pseudo-cold replacement dropout (15% of items represented by text each epoch; DropoutNet-style, credited, adapted to *replace* rather than augment per §6.x), and **T2b** = T2a plus a **within-pool cross-entropy** auxiliary — our offset-invariant evaluation quantity used directly as a training objective, restricting the softmax competitor set to the simulated cold pool so cross-pool offsets cancel in the gradient (no prior work found doing this).

| arm | cold NDCG@10 | warm NDCG@10 | within-pool AUC | +post-hoc kNN: cold | +kNN: overall Δ |
|---|---:|---:|---:|---:|---:|
| B0 stock | **0.00000** | 0.01972 | 0.76373 | 0.00609 | −0.00234 |
| T1 content-anchor | **0.00000** | 0.01908 | **0.77187** | 0.00200 | −0.00029 |
| T2a pseudo-cold dropout | **0.00000** | 0.02014 | 0.76129 | 0.00566 | −0.00171 |
| T2b + within-pool CE | **0.00000** | 0.01986 | 0.75529 | 0.00526 | −0.00118 |

**Every trained arm produces exactly zero rankable cold items.** Not "few" — zero, across three architectures and nine runs, under temporal validity. Only *post-hoc row replacement* ever achieves nonzero cold NDCG. This is the paper's unrankability result in its strongest form: the failure is not that these methods lack information but that **training cannot place a never-positive item into the rankable region at all**, because gradient descent on a full-catalog objective has no mechanism to raise an item that is only ever a negative.

**T1 sharpens the knowledge-vs-rankability dissociation.** The content anchor achieves the *best* within-pool AUC of any arm (0.77187 vs B0's 0.76373) — it genuinely knows more about cold items than the baseline — while converting **none** of it into ranking. This reproduces, in a trained method, exactly the pattern §6.5 found for ridge imputation, and it rules out the obvious objection that the dissociation is an artifact of post-hoc table edits.

**H2 (the metric-as-loss hypothesis) is NOT CONFIRMED.** T2b − T2a on cold NDCG@10 = 0.000000 (0/3 seeds; both are identically zero), and the pre-registered H3 mechanism check goes the wrong way: within-pool AUC *fell* (−0.0060, CI [−0.0129, +0.0009]). Optimizing the offset-invariant metric directly neither created rankability nor improved the quantity it targets. The likely reason is visible in the design: a within-pool objective cannot, by construction, adjust the cross-pool calibration that determines rankability — the same invariance that makes the metric honest makes it unusable as the sole training signal. *This is recorded as the program's fifth failed algorithmic attempt (corrections log #7); the 0-for-4 prior was stated in the prereg before running.*

**The result is loss-family-invariant** ([PREREG_LOSS_V1.md](PREREG_LOSS_V1.md), prediction frozen before the runs). The obvious objection — that unrankability is an artifact of our chunked full cross-entropy — was tested by swapping in **gBCE**, the current SOTA sequential-recommendation loss (gSASRec, Petrov & Macdonald, RecSys 2023 / IJCAI 2024, credited and reimplemented; negative-sampling BCE with the positive term raised to power β; t = 0.75, K = 256 ⇒ β = 0.2578), holding backbone, text channel, protocol and seeds fixed:

| loss family | n | cold NDCG@10 | warm NDCG@10 | within-pool AUC | +post-hoc kNN: cold |
|---|---:|---:|---:|---:|---:|
| full cross-entropy (B0) | 5 | **0.00000** | 0.01972 | 0.76373 | 0.00609 |
| **gBCE (SOTA, L1)** | 3 | **0.00000** (3/3 seeds) | 0.01854 (94% of B0) | **0.78171** | 0.00103 |

Cold NDCG@10 is **exactly zero in every seed of both loss families** — five training arms across two fundamentally different objectives (full-catalog softmax vs sampled-negative calibrated BCE). The pre-registered falsification path was live and specific: gBCE exists to reduce overconfidence, compressing the positive score range, which could plausibly have narrowed the warm-to-cold gap enough to admit cold items. It did not. Notably gBCE achieves the **highest within-pool AUC of any arm** (0.78171) — the third independent reproduction of the knowledge-versus-rankability dissociation, now across a change of *loss function* rather than architecture. Warm performance lands at 94% of the full-CE baseline, consistent with gBCE's own claim of matching full-CE quality with cheaper sampling rather than exceeding it.

**Cold start and sparsity are structurally different problems, and the SOTA loss separates them sharply.** The structural argument for k=0 (never a positive ⇒ no objective can lift it) does *not* extend to k≥1, where an item is occasionally a positive and gradients can move it. We therefore sliced the same gBCE-vs-full-CE comparison by the target item's pre-cutoff training degree (3 seeds each, MI, temporal protocol, stride 2):

| target degree | n/seed | full-CE | gBCE | Δ | signs |
|---|---:|---:|---:|---:|---|
| k = 0 (cold) | 12,281 | 0.00000 | 0.00000 | ±0.00000 | — |
| k = 1–2 | 2,460 | 0.00027 | 0.00009 | −0.00018 | 1/3 |
| k = 3–5 | 2,738 | 0.00094 | 0.00016 | −0.00078 | 0/3 |
| k = 6–10 | 2,806 | 0.00222 | 0.00051 | −0.00171 | 0/3 |
| k = 11–20 | 2,804 | 0.00773 | 0.00112 | **−0.00661** | 0/3, CI excl. 0 |
| k = 21–50 | 3,560 | 0.01890 | 0.00701 | **−0.01189** | 0/3, CI excl. 0 |
| k = 51–200 | 3,641 | 0.03303 | 0.03058 | −0.00245 | 0/3, CI excl. 0 |
| k > 200 (head) | 1,820 | 0.09235 | **0.11791** | **+0.02555** | **3/3, CI excl. 0** |

**The SOTA loss does not fix sparsity — it redistributes performance from tail to head.** Relative changes: −85% at k=11–20, −63% at k=21–50, **+28% at the head**. Every sparse bucket is negative in 3/3 seeds; only the head is positive. §6.6.1 isolates the cause.

**This is the paper's thesis in miniature.** The aggregate warm figure was 94% of baseline — a modest-looking 6% dip that entirely conceals a −85%/+28% internal redistribution. One degree-sliced evaluation pass makes it visible. Aggregate metrics do not merely under-report where performance goes; they actively hide reallocations of this magnitude.

### 6.6.1 Attribution: the calibration exponent, not negative sampling

The §6.6 comparison varies three things at once — loss form, negative count, and β. A **sampled-CE** control (256 negatives, CE form, 3 seeds, identical otherwise) separates them:

| degree | full-CE | sampled-CE | gBCE | sampled-CE − full-CE | gBCE − full-CE |
|---|---:|---:|---:|---:|---:|
| k = 6–10 | 0.00222 | 0.00208 | 0.00051 | −0.00014 | −0.00171 |
| k = 11–20 | 0.00773 | 0.00767 | 0.00112 | −0.00007 | **−0.00661** (CI excl. 0) |
| k = 21–50 | 0.01890 | 0.01726 | 0.00701 | −0.00164 | **−0.01189** (CI excl. 0) |
| k > 200 | 0.09235 | 0.08762 | 0.11791 | −0.00473 | **+0.02555** (CI excl. 0) |
| **tail mean (k = 6–50)** | 0.00962 | **0.00900 (94%)** | **0.00288 (30%)** | | |

**Negative sampling is not the cause.** Reducing negatives from the full 24,587-item catalog to 256 leaves the tail at 94% of full-CE and produces *no* bucket whose CI excludes zero. gBCE, with the same 256 negatives, leaves the tail at 30%.

**The cause is the calibration exponent β.** gBCE optimises `β·softplus(−s⁺) + mean softplus(s⁻)` with β = 0.2578, so failing to rank a positive highly is penalised ≈4× less than under CE, and optimisation pressure shifts toward pushing negatives down. Items that are rarely positives receive almost no upward pressure; head items appear as positives often enough that even β-discounted gradient accumulates. **The overconfidence correction preserves the head by starving the tail** — a mechanism invisible to any aggregate metric.

*Correction (log #8): §6.6 initially attributed the redistribution to gradient starvation from negative sampling. This control refutes that explanation — the arm run to be fair to the cited work is what falsified our own mechanism claim.*

**Fairness to the cited work.** gSASRec's published claim is gBCE > **sampled BCE** (β = 1), which we do not test; our comparison uses sampled-CE and full-CE, a different and stronger baseline, so this is not a refutation of their result. And gBCE's head gain is genuine (+28%, 3/3 seeds, CI excluding zero): for head-dominated traffic it is a real improvement — one costing 70% of tail performance, which a practitioner should choose knowingly rather than inherit by default.

**Consequence for practice.** Combined with §6.4, the operational advice is: cold-start rankability is a *scoring-time* problem, not a training-time one. Train for within-pool knowledge if you like — several methods deliver it — but the decision of whether to expose cold items, and at what cost, is made by the offset/imputation stage, governed by π_t versus p\* plus drift.

### 6.7 Scope of validity
One backbone family; text-kNN as the primary method (family breadth in 6.5); first-appearance as arrival proxy; 5-core computed globally (declared, per protocol origin); two Amazon categories + one non-Amazon platform.

## 7. Practitioner's procedure (the prescriptive core)

1. Measure cold gain g and warm cost c for your candidate intervention on a **calibration window strictly earlier than the traffic you are deciding about** — same-window comparison is an accounting identity, not a prediction (§6.4).
2. p\* = |c| / (g + |c|). Measure observed π_t on the target window.
3. Estimate the drift budget: recompute p\* on ≥2 adjacent historical windows; take the observed shift (we measured +19 to +31pp per window step; direction was consistently optimistic).
4. Deploy iff **π_t > p\* + drift budget**; π_t below p\* ⇒ don't; inside the budget ⇒ expect a wash (VG) and decide on other grounds.
5. Report within-pool AUC and the efficiency ratio alongside any cold-target metric — the latter alone is gameable by one parameter (§3).

## 8. Corrections log (kept in the paper, per this repository's reporting standard)

1. "Text actively hurts at k=4" — reported at 2–3 seeds, retracted at 5 (1/5 positive).
2. "p\* ∝ √N (R² 0.99)" — retracted as an eligibility confound; the controlled sweep gives N^0.843.
3. "Content improves coarse but *not* top-rank" — corrected to a ≈4× asymmetry; the strict version failed at 5 seeds.
4. Multi-dose capset bug (cold pool 2,575 → 455) — caught before any conclusion depended on it.
5. "The framework predicted the sign in all three regimes" — retracted as near-tautological (same-window p\* vs E4 is an identity); replaced by the out-of-sample stability analysis of §6.4, in which the prediction fails on MI and the drift budget becomes the finding. Caught by internal epistemic review before submission.
6. "Cross-domain hyperparameter transfer is measurably unsafe" (fusion arm) — retracted after the tuned-weight control showed the harm is weight-independent; the method, not the transfer, is at fault (§6.5).
8. **"Gradient starvation from negative sampling" (§6.6): refuted by our own control.** The sampled-CE arm (256 negatives, CE form) leaves the tail at 94% of full-CE, so sampling is not the cause; the calibration exponent β is (§6.6.1). The arm was run to be fair to the cited work and falsified our mechanism claim instead.
7. **Metric-as-loss (§6.6, H2): failed.** Using the offset-invariant within-pool objective as a training signal produced no rankable cold items and *reduced* the within-pool AUC it targets. Pre-registered with its 0-for-4 prior stated in advance; reported as the program's fifth failed algorithmic attempt rather than dropped.

## 9. Provenance and credit

Offset-degeneracy proposition, global-time protocol design, and their All_Beauty proof-of-concept: companion workstream artifacts in this repository (`TIER_A_COLDSTART_RESEARCH_AGENDA_2026-08-05.md`, `run_poc_temporal_lc2c_v1.py`, `experiments/cold_pool_prior_poc`), ported here to a sequential backbone at ~70× catalog scale with full credit. All campaign artifacts, preregistrations, adjudication scripts, and per-seed records: `_bestrec_run/poc_out/`.

---
## TODO before submission
- [x] §6.5 family table — integrated 2026-08-12 (`steam_family_aggregate.json`, 5 seeds)
- [x] Merge-vs-absorb re-check at draft completion — their cold-start workstream files untouched since 2026-08-05 and no repo commits in >3 days at final check; **absorb-with-credit stands**, reversible if they resume before submission
- [ ] Related-work citations finalized with full references (all verified in session logs; mechanical)
- [ ] TOIS LaTeX conversion + venue checklist (mechanical)
- [x] **F04 trained cold-start baselines** — done 2026-08-12 (§6.6): T1 content-anchor + T2a pseudo-cold dropout, credited reimplementations, 3 seeds each under the temporal protocol; plus the pre-registered metric-as-loss test (T2b, failed and logged)
- [ ] **Maintainer items (human-only): authorship, institutional ranking verification (gate A0), AI-use disclosure**
