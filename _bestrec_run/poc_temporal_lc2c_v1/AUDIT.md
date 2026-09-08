# Temporal-LC2C V1 proof-of-concept audit

Classification: exploratory, same-investigator proof of concept. The result is
outcome-known and must not be described as confirmation.

## Outcome

The proposed combination did **not** pass its directional feasibility checks.
The inner development period selected the normalized eight-tap `exp085` kernel.
On the later outer period (456 cold-target events, 161 users, 76 cold items):

| Endpoint | LC2C boxcar-8 | LC2C + exp085 FIR | Event-weighted delta |
|---|---:|---:|---:|
| Cold-pool NDCG@10 | 0.211069 | 0.206852 | -0.004217 |
| Raw full-catalog NDCG@10 | 0.001384 | 0.001365 | -0.000019 |
| PZC full-catalog NDCG@10 | 0.032223 | 0.029683 | -0.002540 |

The primary equal-user contrast for cold-pool NDCG@10 was -0.005653 with a
descriptive user-bootstrap interval [-0.016384, +0.004211]. The PZC
full-catalog equal-user contrast was -0.000532 [-0.005220, +0.005375]. The
cold-pool factorial interaction relative to content-direct was -0.000578
[-0.011055, +0.010359]. None supports LC2C-specific FIR synergy.

## Independent arithmetic check

The six printed arm means were recomputed directly from all 456 JSONL records
and match `results.json` to floating-point precision. There are 161 unique users
and 76 unique target items. The input files, cached embeddings, and runner are
SHA-256 bound in `results.json`.

## Post-outcome sensitivities

These checks are diagnostic only and were performed after the primary result
was known.

All four predeclared exponential kernels were worse than boxcar-8 for LC2C on
both cold-pool and PZC full-catalog NDCG@10:

| Kernel | Cold-pool | PZC full catalog |
|---|---:|---:|
| boxcar8 | 0.211069 | 0.032223 |
| exp050 | 0.196952 | 0.019937 |
| exp070 | 0.202971 | 0.021544 |
| exp085 | 0.206852 | 0.029683 |
| exp095 | 0.208181 | 0.031036 |

Early catalog-arrival events sometimes contain very small cold candidate pools.
Requiring at least 10, 20, or 40 available cold candidates leaves the
event-weighted LC2C FIR-minus-boxcar cold-pool contrasts negative (-0.003453,
-0.004548, and -0.000789 respectively). Corresponding PZC full-catalog
contrasts are also negative (-0.002691, -0.004425, and -0.003536).

## Audit concerns and scope

1. This is a scalar recency FIR over the last eight warm interactions, not the
   paper's depthwise FIR residual operating on HSTU hidden states. A negative
   result does not refute every possible neural FIR+LC2C architecture.
2. `All_Beauty` is a very small, single-domain catalog. First observed review is
   only a proxy for catalog arrival.
3. The selected development advantage was small, and development performance
   did not transfer to the outer period.
4. Event-weighted arm means and equal-user contrasts are different estimands.
   `results.json` reports and labels both after the audit correction.
5. Raw content-direct full-catalog NDCG equals its cold-pool NDCG in this run,
   showing that its cold scores dominate the warm EASE scale. The PZC endpoint
   is therefore the more relevant full-catalog diagnostic; neither is a final
   deployment-valid calibration study.

## Decision

Do not pivot the main paper from FIR to Temporal-LC2C based on this experiment.
The simplest interpretable combination--a shared causal recency kernel applied
to the LC2C history--failed to improve the later cold-item ranking. A different
neural shared-embedding combination remains possible, but it requires a new
design and cannot inherit a positive claim from this run.
