# GSCE K0 preregistration: semantic-support audit

Status: **FROZEN before GSCE outcomes**  
Protocol: `GSCE_SEMANTIC_SUPPORT_K0_V1`  
Freeze date: 2026-08-06 (Australia/Sydney)

No GSCE outcome has been computed. This file freezes a small, topology-only
proof of concept. It does not authorize recommender retraining or a paper
claim. A valid pass authorizes a separately preregistered K1 evaluation.

## Research question and contribution boundary

Do standard item-cold splits mostly evaluate semantic interpolation because a
nominally cold item retains a close content neighbor among warm items, and is
there enough family-separated mass in the existing domains to support a
controlled extrapolation benchmark?

Working name: **Graph-Separated Cold-Start Evaluation (GSCE)**.

The possible contribution is a recommender-specific evaluation decomposition:

1. build an item-content graph before using collaborative labels;
2. measure every cold target's semantic support in the warm catalog;
3. report natural interpolation, boundary, and extrapolation strata; and
4. construct an optional whole-family holdout that removes all above-threshold
   content-graph paths across the warm/cold boundary while matching the scored
   targets to the original temporal cohort.

GSCE is not claimed to be the first similarity-aware split, clustering method,
OOD benchmark, temporal cold-start split, constrained data split, or leakage
audit. DataSAIL already provides generic similarity-minimizing stratified
splits using clustering and integer programming. GSCE's claim, if K1 succeeds,
must be limited to the cold-start recommendation diagnosis and the paired
interpolation/extrapolation reporting protocol.

A warm semantic neighbor is not called leakage merely because it exists. It is
legitimate interpolation when that warm item was available at prediction time.
`Leakage` is reserved for duplicated underlying items, use of post-cutoff data,
or collaborative information entering the content graph. GSCE measures task
difficulty and support, not misconduct.

## Frozen source boundary

K0 reuses the two RQ4/RQ2 domains:

- `Musical_Instruments`;
- `Industrial_and_Scientific`.

The already frozen source manifest is
`experiments/rq4_support_mass_router/SOURCE_EXTRACTION_MANIFEST.json`, SHA-256
`517929bd7bdbec04678f6f209ac216d1722b62c1f42e1a8ebed583fe95d01a86`.
Its declared content arrays are frozen 64-dimensional projections of aligned
SBERT title representations. K0 uses only content vectors, sorted item indices,
and q60 interaction counts. Collaborative residuals and all prior experiment
outcomes are forbidden.

Because the existing source manifest hashes only q60-warm content rows, the K0
runner must first produce an append-only no-outcome extraction manifest for the
full catalog content matrix and q60 count vector. Two independent single-thread
reconstructions must agree byte-for-byte before any split diagnostic is
computed. A mismatch makes K0 `INVALID`; it cannot be repaired by selecting a
different cache.

The q60 snapshot is a pseudo-cold mechanism screen, not an absolute-time
recommendation result. Items with positive q60 counts are `warm`; zero-count
items are `natural_q60_cold`. No post-q60 relevance, ranking metric, residual,
or model prediction enters K0.

## Content graph and semantic families

Normalize every nonzero full-catalog content row to unit Euclidean norm. A norm
below `1e-8` is invalid. Construct exact directed cosine 10-nearest-neighbor
lists with self-neighbors excluded and ties broken by ascending catalog index.

Two frozen graphs are used:

- **support graph:** the symmetric maximum-union 10-NN graph; and
- **family graph:** retain only mutual-10-NN edges.

Let `S` be the multiset of positive mutual-edge cosine values. The primary
family threshold is `tau_99`, the 0.99 quantile of `S` using NumPy
`method="higher"`. Frozen sensitivity thresholds are `tau_975` and `tau_995`.
Thresholds use content only and are never chosen from counts, interactions,
model errors, or relevance.

At a threshold `tau`, semantic families are connected components of the
thresholded mutual graph. Singletons remain valid families. Report the largest
component fraction, singleton fraction, component-size quantiles, within-family
minimum/median edge similarity, and number of components containing both warm
and natural-q60-cold items. If the largest primary component exceeds 5% of the
catalog, K0 fails feasibility because single-link percolation makes the family
definition unsuitable.

## Random-split exposure theorem

For a graph fixed independently of the cold labels, mark every item cold
independently with probability `p`. Conditional on item `i` being cold and
having degree `d_i`,

`Pr(i has at least one warm graph neighbor | i is cold) = 1 - p**d_i`.

The proof is the complement event that all `d_i` neighbors are independently
cold. For a uniformly selected target item conditional on its being cold, the
mean exposure probability is

`1 - mean_i(p**d_i)`.

For the actual fixed-size pseudo-cold split with `N` items and exactly `m`
cold items, the exact conditional probability is

`1 - choose(m-1, d_i) / choose(N-1, d_i)`,

with the ratio defined as zero when `d_i > m-1`. The Bernoulli expression is
reported as intuition; the hypergeometric expression is the K0 reference.

For a semantic family of size `s`, independent item splitting places at least
one warm member in the family of a cold target with probability
`1 - p**(s-1)`. Holding out whole connected components makes the number of
above-threshold cross-split family edges exactly zero by construction.

These identities are elementary and are not a mathematical-novelty claim.

## Frozen pseudo-cold audit

Use `p=0.20`. For each domain, sort eligible full-catalog indices ascending,
then make 100 fixed-size splits of `m=floor(0.20*N)` items. Stochastic objects
use SHA-256 seed derivation: UTF-8 encode

`GSCE_SEMANTIC_SUPPORT_K0_V1|20260806|split|<domain>|<draw>`

take the first eight digest bytes as an unsigned big-endian integer, and seed
`numpy.random.PCG64`. Draw identifiers are zero-based. Python `hash()` is
forbidden.

For every cold item and draw, record:

- support-graph degree;
- number of warm support-graph neighbors;
- maximum cosine to a warm item;
- warm neighbors above each family threshold; and
- whether its primary semantic family contains a warm member.

Compare observed exposed fractions with the item-averaged hypergeometric
reference. Absolute discrepancy must be at most `1e-12`; this is a correctness
identity, not a scientific gate.

Apply the same support diagnostics once to the natural-q60-cold versus q60-warm
partition. This natural snapshot is descriptive because it was not randomized.

## Family-separated cohort feasibility

K0 does not train a model. It tests whether K1 can construct a controlled
family-extrapolation cohort without silently changing the target population.

At `tau_99`, take every natural-q60-cold item from a component containing at
least one q60-warm item as an interpolation anchor. Its K1 family-separated
counterfactual would remove all q60-warm members of that component from model
training while continuing to score the same cold target. This keeps target
identity fixed; no matching is needed for the primary paired contrast.

For an optional independent family-holdout cohort, choose at most one scored
anchor per component. Match anchors to the original natural cold cohort using
minimum-cost bipartite flow with unit-capacity anchors and controls. The fixed
cost is the sum of:

- absolute difference in `log1p` of the component's total q60 warm count,
  divided by the domain median absolute deviation with floor `1e-8`;
- a penalty of 10 for a q60-count-decile mismatch; and
- absolute normalized catalog-index difference as a deterministic proxy only
  when no item onset timestamp is available.

This flow matches scored anchors only. Selecting indivisible families while
simultaneously satisfying several aggregate quotas is a grouped integer
program, not min-cost flow, and must not be described otherwise. A temporal K1
must replace catalog index with absolute item onset time and add category and
popularity constraints through a frozen ILP or exact within-stratum matching.

## Reported K0 quantities

Per domain and threshold report:

1. family-size and percolation statistics;
2. random pseudo-cold exposed fraction and exact reference;
3. natural-q60-cold support distribution;
4. fraction of natural cold items in mixed warm/cold families;
5. counts in interpolation (`>=1` warm edge above `tau_99`), boundary
   (`no tau_99 edge` but at least one warm support-graph neighbor), and
   extrapolation (`no warm support-graph neighbor`) strata;
6. number of paired family-purge anchors and warm items that K1 would remove;
7. standardized differences in frozen matching covariates for the optional
   independent family cohort; and
8. peak RSS and wall-clock runtime.

No recommender metric, target relevance, prior model score, or residual error
may be loaded or reported.

## All-or-nothing K0 gates

K0 passes only if all conditions hold in both domains:

1. all source hashes, independent extractions, graph symmetry, neighbor count,
   tie order, and finite-value checks pass;
2. the largest `tau_99` family is at most 5% of the catalog;
3. at least 250 natural-q60-cold targets belong to mixed warm/cold primary
   families, providing paired family-purge anchors for K1;
4. at least 250 natural-q60-cold targets have no primary-threshold warm edge,
   providing a non-interpolation comparison stratum;
5. median random-split warm-neighbor exposure across draws is at least 0.80;
6. the optional matched cohort, if feasible, has at least 200 pairs and an
   absolute standardized difference at most 0.10 for every frozen covariate;
7. the result is qualitatively stable at `tau_975` and `tau_995`: each has at
   least 100 mixed-family cold anchors and at least 100 no-threshold-edge cold
   targets; and
8. runtime is at most 120 seconds per domain, peak RSS at most 2 GiB, and no
   dense catalog-squared matrix is allocated.

Verdicts:

- `K0_PASS_FREEZE_GSCE_K1`: all mandatory gates pass;
- `NEW_DIRECTION`: a valid scientific or feasibility gate fails; or
- `INVALID`: provenance, source, numerical, or execution integrity fails.

The optional matching gate applies only if at least 200 feasible pairs exist;
otherwise K0 may still pass the primary paired-target design, and the optional
independent cohort is removed from K1 before outcomes.

## Authorized K1 only after a pass

K1 must use an absolute global-time cutoff and item availability. It will
evaluate the same temporally cold targets under:

1. the natural catalog, stratified by warm semantic support; and
2. a family-purged training catalog in which all pre-cutoff members of the
   target's primary semantic family are removed before any recommender is fit.

At minimum K1 must include a pure content nearest-neighbor baseline, a linear
content-to-CF baseline, one strong strict-cold model already available in the
repository, and one generative/textual model if runtime permits. The main
result must be a paired change in model ranking or a substantial performance
gap between interpolation and extrapolation; merely showing that the latter is
harder is insufficient for a Tier-A claim.

## Windows-safe execution

Any later runner must follow
`experiments/WINDOWS_SAFE_EXECUTION_CONTRACT_2026-08-05.md`. In particular it
must use the workspace interpreter directly with unbuffered output, set all six
BLAS/OpenMP thread variables to one before importing numerical libraries, use
one process and no captured child pipes, write persistent stdout/stderr files,
install `threading.excepthook` and `sys.unraisablehook`, hold an
experiment-specific lock, and publish only append-only fingerprinted
artifacts. No outcome run is launched by this preregistration.

