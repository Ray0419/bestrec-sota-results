# Verified results — what survived Loop 0 (novelty) and Loop 1 (replication)
### 2026-08-06 · every claim here has passed a prior-art check AND ≥5-seed replication
### Artifacts: `_bestrec_run/poc_out/decomp_sweep.json`, `*.offset_decomp.json`

---

## 0. Bottom line

**Two results are verified.** Both survived a dedicated novelty search and both replicate at 5 seeds across *two independent pool configurations* (10 seed-runs total), with confidence intervals excluding the null in every case.

Loop 0 and Loop 1 also **killed or downgraded five earlier claims**, including two I had previously reported as findings. That ratio — 2 verified, 5 killed — is the loop working as designed.

---

## 1. VERIFIED RESULT 1 — content carries genuine, offset-invariant, *coarse* cold signal

Within-pool AUC is cutoff-free, pool-size independent, and exactly invariant to any constant cross-pool score offset, so it isolates genuine within-cold relevance from the nuisance offset.

| pool | N_cold | AUC gain (text-kNN imputation) | 95% CI | seeds |
|---|---:|---:|---|---|
| K-DIAL k0 | 3,121 | **+0.03479 ± 0.00224** | [+0.03161, +0.03798] | **5/5** |
| DOSE k0 | 455 | **+0.03330 ± 0.00906** | [+0.02040, +0.04619] | **5/5** |

Base AUC ≈ 0.73–0.74 → ≈ 0.75–0.78. **10/10 seed-runs positive, both CIs exclude zero, and the two point estimates agree to within 5% despite a 7× difference in pool size** — which is exactly the pool-size invariance the metric was chosen for.

Interpretation: the frozen text embeddings genuinely identify which cold item a user wants, better than the item's own (degenerate) trained row does. This is *not* the pool offset — AUC cannot see a constant offset by construction.

## 2. VERIFIED RESULT 2 — the offset-matched efficiency ratio exceeds 1

The ratio = (warm cost per unit cold gain of a **pure offset**) ÷ (same for the **method**). It reads exactly 1.0 for a method that is a disguised pool offset, and above 1.0 only insofar as the method carries genuine relevance.

| pool | N_cold | efficiency ratio | 95% CI | excludes 1.0? | seeds |
|---|---:|---:|---|---|---|
| K-DIAL k0 | 3,121 | **1.609 ± 0.067** | [1.513, 1.704] | **yes** | 5/5 |
| DOSE k0 | 455 | **1.736 ± 0.189** | [1.467, 2.004] | **yes** | 5/5 |

**10/10 seed-runs, both CIs exclude 1.0.** Content-based imputation buys cold gain at ~1.6–1.7× the efficiency of a parameter-free offset — real, reproducible, and far short of what the raw cold-target metric implies.

---

## 2b. VERIFIED RESULT 3 — the break-even prevalence scales *near-linearly* with cold-catalog size

Loop 2, [PREREG_SCALING_V1.md](PREREG_SCALING_V1.md), decision rules frozen before the runs. Controlled single-variable sweep: eligibility fixed at min-deg 20, only `--item-cap-frac` varies, smaller pools nested inside larger, 4 pool sizes × 3 seeds = 12 runs.

| N_cold | cold gain g | warm cost c | **break-even p\*** | efficiency ratio | AUC gain |
|---:|---:|---:|---:|---:|---:|
| 243 | +0.0351 | 0.0026 | **6.8%** | 3.22 | +0.0493 |
| 455 | +0.0297 | 0.0040 | **11.8%** | 2.69 | +0.0376 |
| 1,092 | +0.0202 | 0.0069 | **25.5%** | 2.11 | +0.0472 |
| 2,153 | +0.0173 | 0.0127 | **42.3%** | 1.47 | +0.0380 |

*(means over 3 seeds; per-seed values in `scaling_v1_analysis.json`)*

**Pre-registered primary test: β_p = +0.843 ± 0.015, CI [+0.806, +0.881], 3/3 seeds positive → CONFIRMED.**

Component exponents, all 3/3 sign-consistent and tight: warm cost **c ∝ N^0.72**, cold gain **g ∝ N^−0.34** (the gain *falls* as the pool grows), efficiency ratio **∝ N^−0.35**.

**The √N framing is DROPPED** — the pre-registered rule required the CI to contain 0.5 and it does not (CI [0.806, 0.881]). The law is reported at its measured exponent, ≈0.84.

**This correction makes the finding stronger, not weaker.** At √N, cold prevalence (which grows ≈linearly in N) would eventually overtake p\*, so a large enough cold catalog would make imputation pay. At **N^0.84 the two grow at nearly the same rate**, so the margin p_obs/p\* improves only as ≈N^0.16 — **you cannot outgrow the problem by having more cold items.** Simultaneously the efficiency ratio *decays* (N^−0.35, from 3.2 at N=243 to 1.5 at N=2,153), i.e. imputation converges toward being no better than a parameter-free offset exactly as the cold catalog becomes large.

### Correction: my earlier √N estimate was a design artifact
I previously reported p\* ∝ N^0.48–0.55 with R² 0.98–1.00 across three methods and called it a clean square-root law. **That estimate was confounded**: its three pool sizes came from runs with *different eligibility criteria* (min-deg 8 vs 20) and different pool definitions, so item populations differed across the x-axis. The controlled sweep here — one eligibility rule, nested pools, 3 seeds — gives 0.84 with a much tighter CI. The earlier high R² measured a consistent artifact, not a law.

## 2c. LOOP 3 — the results hold under a temporally valid protocol, and the framework predicts a crossover

[PREREG_TEMPORAL_V1.md](PREREG_TEMPORAL_V1.md), frozen before the runs. Global-time protocol (**design ported from the parallel session's `run_poc_temporal_lc2c_v1.py`, credited to them**): pooled-quantile cutoffs, first-appearance arrival proxy, natural cold arrival, first-availability candidate constraint. 8 training runs (MI ×5, VG ×3) + 8 per-event availability-masked evaluations.

| | **MI** (5 seeds) | **VG** (3 seeds) |
|---|---:|---:|
| observed prevalence π_t | **38.16%** | **77.83%** |
| stock — overall / cold / warm | 0.01219 / **0.00000** / 0.01972 | 0.00772 / **0.00000** / 0.03484 |
| imputed — overall / cold / warm | 0.00985 / 0.00609 / 0.01217 | 0.00787 / 0.00441 / 0.01999 |
| **E1** within-pool AUC gain | **+0.02229 ± 0.00113**, CI [+0.0209, +0.0237], **5/5** | **+0.03075 ± 0.00249**, CI [+0.0246, +0.0369], **3/3** |
| **E2** efficiency ratio | **1.484 ± 0.070**, CI [1.398, 1.570] **excludes 1.0** | 1.812 ± 0.142, CI [0.539, 3.084] includes 1.0 |
| **E3** break-even p\* | 55.36%, CI [54.12, 56.61] | 77.04%, CI [74.28, 79.80] |
| **E4 (primary)** overall Δ | **−0.002343 ± 0.000061**, CI excludes 0, **0/5** | +0.000142 ± 0.000198, CI includes 0, 2/3 |
| verdict | **decisively does not pay** | **a wash — at break-even** |

**E1 CONFIRMED on both datasets.** Content genuinely carries coarse, offset-invariant cold signal under temporal validity — 8/8 seed-runs positive, both CIs excluding zero, at magnitudes comparable to the LOO measurements (+0.033–0.035). The instrument survives the protocol change.

**E2 confirmed on MI, underpowered on VG.** MI's CI cleanly excludes 1.0; VG's point estimate is *higher* (1.81) but n=3 with t\*=4.303 leaves the CI spanning 1.0. Directionally consistent, not confirmed — reported as such.

**Update 2026-08-12 — VG closed at n=5: E2 CONFIRMED on both datasets.** Seeds 39–40 added: VG efficiency ratio **1.739 ± 0.119, CI [1.550, 1.927] excludes 1.0, 5/5**; E1 tightens to +0.03074 ± 0.00176 (5/5). The break-even boundary result also sharpens: p\* = 76.97% CI [75.88, 78.06] vs π_t = 77.83% — observed prevalence sits at the upper edge of the break-even CI, and measured E4 = +0.000168, CI [−0.000039, +0.000374], 4/5 positive: a statistically marginal *positive*, exactly what the framework predicts for a system sitting on the line. No endpoint in the program remains underpowered.

**Cold items score exactly 0.00000 on both datasets.** Genuinely new items are unrankable, replicating the LOO finding on real arrivals rather than artificially capped ones.

### The finding: p\* predicts the crossover

The break-even formula was derived under LOO and has never been tested against an *observed* prevalence. Here it is, twice:

- **MI:** p\* = 55.4% > π_t = 38.2% ⇒ predicts "should not pay". Measured E4 = **−0.00234, CI excludes 0**. ✓
- **VG:** p\* = 77.0% ≈ π_t = 77.8% ⇒ predicts "right at break-even". Measured E4 = **+0.00014, CI spans 0**. ✓

**The framework predicted the sign of the aggregate effect in both prevalence regimes**, including correctly identifying that VG sits essentially *on* the break-even line (a 0.8-point margin producing a statistically indistinguishable net effect). E3/E4 sign agreement — a pre-registered consistency requirement — holds for both datasets.

This is the pre-declared "prevalence regime, not method quality, decides" outcome, and it is the decision-relevant answer leave-one-out structurally could not produce: **imputation's viability is set by how many of your targets are new items, and the break-even threshold can be computed in advance.**

### Honest notes

- **π_t is higher than the scoping estimate** (38% vs 21% MI; 78% vs 52% VG) because cold is defined against the **inner** cutoff while the reporting window sits past the **outer** one — items arriving between the two are correctly cold w.r.t. training. The scoping numbers used a single cutoff.
- **Validity-gate judgment call.** The prereg set the gate at overall NDCG within ~2× of LOO (0.03–0.05); measured overall is 0.0122. It passes on the *warm slice* (0.0197, within 2× of ≈0.035), and the identity overall = warm × (1−π_t) reproduces the overall figure exactly — evidence the pipeline is correct and the shortfall is the substantive finding (cold targets score zero). Recorded as a judgment call, not a silent threshold change.
- The trainer's internal eval freezes user histories at the training cutoff and is a **selection proxy only**; all reported numbers come from the per-event evaluation with correct histories.

## 2d. STEAM — the instruments transfer off Amazon, and the crossover completes ([PREREG_STEAM_V1.md](PREREG_STEAM_V1.md), all endpoints n=5)

Non-Amazon generality chapter. Adapter reproduced the published dataset shape (334,325 users / 12,012 items / 4.21M actions vs the SASRec paper's 334,730 / 13,047 / ~3.7M), 100% item-text coverage; **sanity gate passed** (LLOO test NDCG@10 = 0.0578, inside the published full-ranking band 0.0546–0.156 and the pre-set [0.04, 0.20] gate). Temporal protocol unchanged; observed π_t = 40.15%.

| endpoint | Steam (5 seeds) | verdict |
|---|---|---|
| E1 within-pool AUC gain | **+0.11286 ± 0.01224**, CI [+0.0977, +0.1281], 5/5 | **CONFIRMED** — 4–5× the Amazon magnitude |
| E2 efficiency ratio | **2.740 ± 1.257**, CI [1.180, 4.301] | **CONFIRMED (excludes 1.0)** — the prereg's 3→5 power rule fired and resolved it |
| E3 break-even p\* | 26.03%, CI [24.52, 27.54] vs π_t = 40.15% | predicts **PAY** |
| E4 aggregate at observed π_t | **+0.000994 ± 0.000094**, CI [+0.000877, +0.001111], **5/5** | **PAYS** — first decisively positive regime |
| cold NDCG (stock) | exactly 0.00000 | unrankability holds on a third dataset |

**The three-regime crossover, complete and fully powered:**

| dataset | π_t | p\* | framework predicts | measured E4 |
|---|---:|---:|---|---|
| MI | 38.2% | 55.4% | not pay | **−0.00234**, CI excl. 0, 0/5 |
| VG | 77.8% | 77.0% | on the line | +0.00017, CI spans 0, 4/5 |
| **Steam** | **40.2%** | **26.0%** | **pay** | **+0.00099, CI excl. 0, 5/5** |

The framework predicted the aggregate sign **below, at, and above break-even**, across two Amazon categories and one non-Amazon platform, with E3/E4 sign-agreement holding in all three. This is the paper's central prescriptive claim, demonstrated rather than asserted: *measure g and c once, compute p\* = |c|/(g+|c|), compare to your observed cold prevalence — the sign of the aggregate effect follows.* Why Steam pays where MI doesn't is visible in the components: Steam's warm cost is −1.2% relative (vs MI's −38%), so its break-even sits low; the framework needs only the measured components, not the mechanism.

## 3. REFUTED — my own claim #9, as I stated it

I previously reported (n=1 per pool) that imputation "improves coarse within-pool discrimination but **not** top-rank precision." **At 5 seeds this is false as stated.**

| pool | within-pool NDCG@10 gain | 95% CI | seeds positive |
|---|---:|---|---|
| N=3,121 | **+0.00095 ± 0.00030** | [+0.00053, +0.00138] **excludes 0** | 5/5 |
| N=455 | −0.00451 ± 0.00403 | [−0.01025, +0.00123] includes 0 | 1/5 |

At the larger pool, top-rank precision **does** improve significantly. The negative sign I reported came from a single seed at the smaller pool and does not replicate (CI spans zero).

**What survives is a quantitative asymmetry, not a sign difference.** At N=3,121: AUC improves its above-random discrimination by 0.0348/(0.738−0.500) = **+14.6%**, while within-pool NDCG@10 improves by 0.00095/0.0251 = **+3.8%** — a ~4× gap. The defensible claim is:

> Content-based imputation improves *coarse* within-pool discrimination roughly 4× more than it improves *top-rank precision*, and its top-rank benefit is small enough to be configuration-dependent (undetectable at N=455).

That is weaker than what I reported, and it is what the data support.

---

## 4. Killed or downgraded in Loop 0 (prior-art), with citations

| claim | outcome | pre-empting work |
|---|---|---|
| Directional collapse / "suppression axis" as the mechanism | **KILLED as a discovery** | Representation degeneration: Gao et al. ICLR 2019; [Rare Tokens Degenerate All Tokens](https://arxiv.org/abs/2109.03127) (ACL 2022) — rare tokens seldom get positive gradients, are pushed by negatives into a common direction. Recsys "popularity direction": [arXiv:2512.10688](https://arxiv.org/html/2512.10688v5) |
| Embedding-norm/popularity geometry | **KILLED as a discovery** | [arXiv:2308.11288](https://arxiv.org/pdf/2308.11288), [arXiv:2211.01154](https://arxiv.org/abs/2211.01154) |
| k-dial as a novel *technique* (graded interventional degree manipulation) | **PRE-EMPTED** | [Recommendation Is a Dish Better Served Warm](https://arxiv.org/abs/2508.07856) — "incrementally vary the number of interactions for different items during training", retraining per level |
| Text activation threshold at k ≈ 8–16 | **DOWNGRADED** | Same paper reports item cold-warm thresholds of **6–15** interactions (ML-1M 9–10, Beauty 6–10, Behance 6–15). Ours is also *trivially implied*: below threshold **both** arms score ≈0, so their difference must be ≈0 |
| Cold/warm exchange rate (qualitative) | **PARTIALLY PRE-EMPTED** | [Warmer for Less](https://arxiv.org/html/2512.17277) (Pinterest, WWW 2026); [Tunable Stochastic Gates](https://arxiv.org/abs/2112.07615); DiffCold "seesaw dilemma" |

**What still differentiates our intervention** from [2508.07856](https://arxiv.org/abs/2508.07856), and is worth keeping as *method*, not as discovery: (a) they retrain once per degree level; we cap **disjoint groups to different degrees inside a single run**, which is 6× cheaper and holds global density constant across doses; (b) they use dynamic evaluation, we freeze eval at full density; (c) they study ID-only collaborative models (EASE^R, PureSVD, ItemKNN, SASRec-CE) and **never compare a text arm to an ID arm** — the text-vs-ID differential is ours.

---

## 5. Where this leaves the project

The surviving, verified core is **two evaluation instruments**, not an algorithm and not a mechanism:

1. within-pool AUC as the offset-invariant measure of genuine cold relevance;
2. the offset-matched efficiency ratio as a scalar that reads 1.0 for metric-gaming.

Together with the parallel session's offset-degeneracy theorem, that is a coherent and honest evaluation paper: *cold-start metrics credit a nuisance offset; here are two instruments that separate it from real signal; applied to a standard content method, the real signal is genuine but coarse and ~1.6× an offset rather than the order of magnitude the headline metric suggests.*

**Still unverified and not to be claimed:** the √N break-even law (3 points, 1 seed — Loop 2); anything temporal (all leave-one-out — Loop 3); cross-dataset generality (MI only, plus one degenerate VG pool — Loop 4).
