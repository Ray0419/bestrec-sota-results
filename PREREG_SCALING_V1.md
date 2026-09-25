# PREREG: cold-catalog scaling of the break-even prevalence (V1)

**Frozen 2026-08-06 before any run of this design.** Loop 2 of [PROJECT_LOOP_PLAN.md](PROJECT_LOOP_PLAN.md).

## 1. Novelty gate (passed)

Searched 2026-08-06. The cold/warm trade-off ("seesaw dilemma") is established qualitatively (DiffCold; [Tunable Stochastic Gates](https://arxiv.org/abs/2112.07615); [Warmer for Less](https://arxiv.org/html/2512.17277)), and catalog-size effects on overall performance are studied ([Cold-Starts in Generative Recommendation](https://arxiv.org/html/2603.29845)). **No work reports how the break-even point itself scales with the size of the cold catalog.** Claim clears the gate, conditional on being real.

## 2. Question

For a fixed imputation method, how do the cold gain g, the warm cost c, and the break-even cold prevalence

  **p\*(N) = |c| / (g + |c|)**

scale with the number of cold items N? Prior estimate (3 points, 1 seed, uncontrolled eligibility): **p\* ∝ N^0.5**. That estimate is explicitly *not* evidence; this design tests it.

## 3. Design — controlled single-variable sweep

The earlier 3-point estimate mixed two different eligibility criteria (min-deg 8 vs 20), so item populations differed across pool sizes and the exponent was confounded. Here **only the cold-pool size varies**:

- Eligibility fixed: `--item-cap-min-deg 20` (eligible pool 4,243 items, identical every run).
- `--item-cap-frac` ∈ **{0.05, 0.10, 0.25, 0.50}** → ≈ 212 / 424 / 1,061 / 2,122 capped items (+31 natural cold). A 10× span.
- Single dose `--item-cap-k 0`, so every capped item is genuinely cold.
- `--item-cap-seed 7` fixed, so smaller pools are nested subsets of larger ones.
- Text arm only (the decomposition needs no ID table). **Seeds: 3** (20260736–38). **Runs: 12.** Dataset: MI.
- Eval frozen at full density, as always.

## 4. Endpoints and decision rules

Per seed, fit log-log slopes over the 4 pool sizes:

- **β_p — primary:** exponent in p\*(N) ∝ N^β.
- β_c: exponent in |c|(N); β_g: exponent in g(N).
- **r(N)** — offset-matched efficiency ratio, tested for N-dependence (observed 1.74 at N=455 vs 1.61 at N=3,121 suggests a mild decline; that comparison was confounded by eligibility and is not evidence).

**Confirmed iff** β_p is positive in **3/3 seeds** *and* the across-seed 95% CI on β_p excludes 0. **√N specifically** is claimed only if that CI also contains 0.5.

**Pre-declared kill criteria.** If β_p is sign-inconsistent across seeds, the scaling law is **withdrawn** and demoted to the qualitative statement "warm cost grows with cold-catalog size" — no re-fitting on a subset of pool sizes, no switching to a different response variable, no adding seeds to rescue it. If β_p is consistent but its CI excludes 0.5, the law is reported at its measured exponent and the "√N" framing is dropped.

## 5. Complexity budget

12 runs × ~4 min ≈ 50 min GPU, plus 12 decompositions (~2.5 min each, one encode pass each) ≈ 30 min. Total ≈ 1.3 GPU-h, inside the 4 GPU-h loop cap. Text-arm checkpoints only (~95 MB × 12, deletable after decomposition). GPU probe before every launch; the parallel session's lock is untouched.

## 6. What this cannot establish

Temporal validity (leave-one-out throughout), cross-dataset generality (MI only), or any claim about methods other than text-kNN imputation.
