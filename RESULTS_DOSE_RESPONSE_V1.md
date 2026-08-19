# RESULTS — PREREG_DOSE_RESPONSE_V1
### Executed 2026-08-05/06 · 10 MI training runs + 3 decompositions · artifacts `_bestrec_run/poc_out/dose_analysis.json`, `*.offset_decomp.json`
### Analysis plan frozen in [PREREG_DOSE_RESPONSE_V1.md](PREREG_DOSE_RESPONSE_V1.md) before any run

---

## 1. Pre-registered verdict: all three hypotheses PASS

| test | result | verdict |
|---|---|---|
| **H1** monotone dose-response, Spearman ρ(k, gap), 5/5 seeds positive | ρ per seed +0.371, +0.029, +0.143, +0.200, +0.943; mean **+0.337**, 5/5 positive | **PASS** |
| **H2** gap(k=0) CI includes 0 **and** gap(k=16) CI excludes 0 | k=0: exactly 0.00000; k=16: +0.00417, CI [+0.00296, +0.00537] | **PASS** |
| **H3** dd = gap(16) − gap(0) > 0, 5/5, CI excludes 0 | **+0.00417 ± 0.00097, t = +9.58**, CI [+0.00296, +0.00537], 5/5 | **PASS** |

## 2. But the shape is a THRESHOLD, not a ramp — and that matters more than the passes

| dose k | text−ID gap | sd | 95% CI | seeds positive |
|---:|---:|---:|---|---|
| 0 | +0.00000 | 0.00000 | — | 0/5 |
| 1 | −0.00008 | 0.00012 | [−0.00022, +0.00007] incl 0 | 1/5 |
| 2 | −0.00001 | 0.00008 | [−0.00011, +0.00009] incl 0 | 1/5 |
| 4 | +0.00025 | 0.00040 | [−0.00024, +0.00074] incl 0 | 3/5 |
| 8 | −0.00046 | 0.00057 | [−0.00116, +0.00025] incl 0 | 1/5 |
| **16** | **+0.00417** | 0.00097 | **[+0.00296, +0.00537] excl 0** | **5/5** |
| control (uncapped, deg ≥ 20) | **+0.01591** | 0.00165 | [+0.01386, +0.01796] | 5/5 |

**H1 passed as specified, but the specified test was a weak instrument for the actual shape.** The curve is flat at zero across k ∈ {0,1,2,4,8} — every one of those doses has a CI spanning zero, and k=8 is *negative* in 4 of 5 seeds — and then switches on at k=16. Two of the five per-seed Spearman ρ values are essentially zero (+0.029, +0.143); the positive mean is carried almost entirely by the k=16 anchor. Reporting this as "a monotone graded dose-response" would be true to the pre-registered test and false to the data.

The honest reading: **text contributes nothing measurable until an item has somewhere between 8 and 16 training interactions, then switches on.** There is an activation threshold, not a gradient.

And it is **far from saturated at k=16**: the uncapped control group (same eligibility pool, degree ≥ 20, untouched) shows +0.01591 — **3.8× the k=16 gap**. So the interesting part of the curve lies *above* the range this experiment sampled. A follow-up should extend to k ∈ {24, 32, 64}; the current design cannot say whether the rise from 16 to full degree is linear, saturating, or another step.

**Design note that worked.** Because all doses live in one training run at constant global density, the capacity-reallocation confound from the earlier per-rung design is gone: the control group is measured inside the same models, so cross-dose comparison is within-run, within-seed, and within-item-pool.

## 3. Secondary endpoint: the scale-free metric changes the conclusion

The pre-registered replacement for within-pool NDCG@10 was **within-pool AUC** (cutoff-free, pool-size independent, exactly offset-invariant). Measured on three cold pools spanning 37×:

| cold pool N | within-pool AUC, stock → imputed | AUC gain | old within-pool NDCG@10 verdict |
|---:|---|---:|---|
| 85 (VG) | 0.5462 → 0.6640 | **+0.1177** | "658% genuine" (degenerate) |
| 455 (MI dose) | 0.7304 → 0.7509 | **+0.0205** | −0.0098 → "no genuine gain" |
| 3,121 (MI k-dial) | 0.7380 → 0.7760 | **+0.0381** | +0.0007 → "6.6% genuine" |

**The pre-registered prediction is confirmed** — AUC yields bounded, comparable values (+0.02 to +0.12) across pool sizes where NDCG@10 produced 6.6% / 70% / 658%, including a mathematically impossible share. Any protocol ranking cold targets only among cold items (the *Fairness among New Items* family) needs this correction.

**And it materially revises the headline.** The two metrics disagree *in sign*: on the N=455 pool, imputation gains +0.0205 AUC while *losing* 0.0098 within-pool NDCG@10, and its within-pool MRR also falls (0.0741 → 0.0698). The resolution is that these measure different resolutions of the same ranking:

> **Text-kNN imputation genuinely improves *coarse* within-pool discrimination but not *fine* top-rank precision.** A cold target moves from outranking ~74% of the cold pool to ~78% — a real, substantial content signal — yet it is no more likely to reach the pool's top 10, and its full-catalog top-10 gain still comes predominantly from the pool offset.

This supersedes the earlier "≈95% of the benefit is nuisance offset / genuine share 6.55% ± 2.22%" figure, which was computed with the top-weighted, small-pool-degenerate metric and **understated the real content signal**. The **offset-matched efficiency ratio (1.61 ± 0.07)** is unaffected — it is derived from full-catalog cold gain and warm cost, not from the within-pool metric — and still stands.

It also explains a real pattern in the literature: content-based cold-start methods report strong AUC and recall@large-K but disappoint on NDCG@10. Both are correct measurements of different things.

## 4. Errors found and corrected during execution

- **Multi-dose capset bug (caught and fixed).** The decomposition initially applied the scalar `item_cap_k` to *every* capped item, marking the k=1…16 groups as cold and inflating the pool to 2,575. Fixed to apply per-group doses; the corrected pool is 455. All numbers above are post-fix.
- **Interim claim withdrawn (earlier campaign).** At 2–3 seeds the k=4 gap appeared significantly negative ("text actively hurts"); it did not survive 5 seeds (1/5 positive, CI spans zero). The correct claim is abolition, not reversal.

## 5. What this does and does not license

**Licensed:** degree causally gates the text advantage in this architecture, with a threshold near k≈8–16 (5 seeds, within-run, CI excludes zero); the scale-free within-pool metric is required for cross-dataset comparison; content carries real coarse signal but not top-rank precision.

**Not licensed:** anything about deployment-time cold start (still leave-one-out, not the global-time protocol); cross-dataset generality (MI only); the √N break-even law (untouched here, still 3 points at 1 seed); the shape above k=16 (unsampled).
