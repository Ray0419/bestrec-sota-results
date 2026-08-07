# Phase 2, Cycle 8: CODEPATCH-⊥ Research Question and Kill Gate

Date: 2026-08-07

Status: prospectively frozen after independent statistical and algebraic
review; no Cycle-8 user outcome has been opened

## Primary research question

> On a fresh, prospectively selected 5,000-user temporal MovieLens-10M cohort,
> can CODEPATCH-⊥ compile available user feedback into at most 63 sparse
> codeword utilities per request—each exactly orthogonal to every dense-query
> table over a frozen 24-byte FAISS PQ item code—and thereby improve both
> future candidate preference exposure and future-liked Recall@100 by at least
> 0.010 over every matched compressed-code control, while preserving final
> hybrid relevance, using no item re-encoding or index rebuild, no more than
> one eighth of dense semantic-index bytes, and no more than 1.25x the frozen
> zero-patch compact-code scanner's p95 CPU retrieval latency?

The question is novel only at the registered intersection: a sparse user-side
preference program over shared immutable PQ symbols, restricted to the exact
orthogonal complement of the entire dense-query ADC function class and
executed before candidate truncation. It is empirically testable through
future-item candidate membership, pair direction, relevance, bytes, latency,
and exact algebraic audits.

## Claims explicitly excluded

The experiment does not claim novelty for SentenceTransformers, PQ, ADC,
lookup scoring, sparse interaction retrieval, BPR, user-history aggregation,
pairwise logistic losses, SimPO, RecPO, or reranking. It makes no causal,
counterfactual, conformal, distribution-free, formal-safety, million-item
latency, or online-utility claim. MovieLens ratings are exposure-conditioned
observations. The PoC cannot establish production-scale behavior.

## Immutable sources and representation

- Dataset: official MovieLens 10M archive already locked at 65,566,137 bytes
  and SHA-256
  `813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`.
- Allowed archive members: `ml-10M100K/ratings.dat` and
  `ml-10M100K/movies.dat`; `tags.dat` is forbidden.
- Item text is the UTF-8 movie title followed by the pipe-separated genres.
- The representation is the already frozen, L2-normalized
  `sentence-transformers/all-MiniLM-L6-v2` `10,681 x 384` float32 matrix. The
  implementation must bind its ordered movie IDs, bytes, model identifier, and
  package version. It may reuse the prior item-only artifact only after
  verifying the movie order from the locked archive.
- Train one deterministic inner-product `faiss.IndexPQ(384, 24, 8)` on the
  item matrix. Each item has exactly 24 one-byte subquantizer IDs. Freeze and
  hash the centroids, item codes, ordered IDs, serialized FAISS index, and the
  optional exact compact-code scan structure before any Cycle-8 `R`, `V`, or
  `T` label is opened.

No rating may change an item vector, centroid, code, code assignment, index
membership, or catalog order.

## Fresh cohort and temporal split

Before any Cycle-8 rating payload is opened, reconstruct a conservative numeric
user-ID denylist containing every user whose A, R, V, or T payload was opened
in Cycles 1--7. Dataset namespaces are deliberately ignored: a numeric ID seen
in MovieLens 100K or 1M is excluded from MovieLens 10M even though the releases
do not establish cross-release identity. The frozen inputs and SHA-256 values
are:

- Cycle 1 split manifest (801 IDs):
  `cacc93ef5b13b4367cdb3e324a5f02da33c906765873027081166ea5fbf3e23c`;
- Cycle 2/3/4 cohort lock (1,000 CAPER, 1,000 RAVEL, and 2,000 FACET IDs):
  `0f5b2af075cf2850aa8bdd32e7cde577859167148d2459cfe9d5fd327c1a4812`;
- Cycle 5 cohort record (2,000 IDs):
  `eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126`.

Cycles 6 and 7 opened no cohort payload and add no IDs. Sorting the integer
union, encoding it as compact JSON followed by one newline, produces exactly
6,170 IDs and SHA-256
`fb24b4ec2477e9e014c2e63fc16ae50df548e7fa1c2d49e4ef0c2463cf4289bf`.
The runner must independently reconstruct and persist this union before opening
the Cycle-8 archive. A missing source, hash/count mismatch, or inability to
reconstruct the union kills CODEPATCH before A/R/V/T access. No prior history
may be reused.

1. Scan only user IDs, timestamps, source ordinals, and event counts to create
   per-user timestamp-group layouts.
2. Split each user into indivisible equal-timestamp blocks nearest
   `A/R/V/T = 60/20/10/10%`, breaking cutoff ties at the earlier legal
   timestamp group and requiring strict time order between blocks.
3. Structural eligibility requires 80–300 total events, at least four distinct
   timestamp groups, at least 20 A events, and nonempty R/V/T blocks.
4. Rescan A values only. A user remains eligible with at least five distinct
   A items rated at least 4.0 and at least three distinct A items rated at most
   2.5. R/V/T identities and values remain unavailable to membership.
5. Order eligible users by SHA-256 of `20260881:{user_id}`, then numeric user
   ID. Select exactly the first 5,000. If fewer exist, fail closed before any
   selected-user R/V/T access; do not assert
   or gate on the archive-wide eligible count.

The runner first persists a structural-layout manifest containing the denylist
binding, per-user timestamp-block boundaries, counts, and structural exclusions
before reading any rating value. It then performs the permitted A-only
eligibility scan and persists a second A-screening/cohort manifest containing
the selected 5,000 IDs, A-eligibility facts, layouts, and selection hashes.
That second manifest must be durable before materializing A histories or
training tensors, and before opening any selected-user R/V/T identity or value.

## Stage barriers

- **A:** construct the three frozen BPR item models, user history states,
  CODEPATCH supports, fixed representation artifacts, and a target-blind R
  prefix/support manifest. A trained CODEPATCH R score manifest is neither
  possible nor required because R supplies the training labels.
- **R:** only after every R prefix/support manifest is durable, join R ratings
  and construct natural preference pairs. Train all aligned models with R only.
- **V:** construct every V candidate/score manifest from A+R history before
  joining V. Use V only to freeze each registered method's checkpoint, patch
  scale, and BPR/hybrid fusion configuration. No control or seed is discarded.
- **T:** freeze all choices, reconstruct every user state from A+R+V, and
  publish all T candidates, scores, rankings, supports, patches, and latency
  request IDs before joining any T rating. Open T once.

Current-stage labels, item identities, pair counts, or outcomes may not affect
current-stage histories, supports, patches, candidates, scores, tie breaks,
work, latency selection, cohort membership, or method identity.

## User history features

For a prefix sorted by `(timestamp, source ordinal)`, define

```text
y(r) = +1  if r >= 4.0
       -1  if r <= 2.5
        0  otherwise
rho_j = (j + 1) / number_of_prefix_events
```

The base semantic query is the L2-normalized difference between the positive
item centroid and one half of the negative item centroid; if no negative is
present, use only the positive centroid. Four fixed codeword features are
computed for each `(m,k)` from the prefix:

```text
f1 = sum_j 1[z_jm=k] * y(r_j) / sqrt(1 + count_mk)
f2 = sum_j 1[z_jm=k] * y(r_j) * rho_j / sqrt(1 + sum rho_j^2)
f3 = sum_j 1[z_jm=k] * (r_j - 3.0) / max(1, count_mk)
f4 = tanh(sum_j 1[z_jm=k] * y(r_j) / 2) * log1p(count_mk)
```

Zeros are exact zeros. Features may not contain user ID, movie ID, a
current-stage item/label, outcome counts, BPR score, candidate membership, or
method outcome.

## Exact sparse orthogonal mechanism

For each subquantizer `m`, rank observed codewords by descending
`abs(f1)+abs(f2)`, then count, then codeword ID. Fill from a fixed
catalog-frequency order. Deterministically replace the weakest fill as needed
until the 21-row matrix

```text
A_u,m = [ C_m[S_u,m], 1 ]
```

has rank 17 under a float64 SVD with relative tolerance
`sigma_j / sigma_1 >= 1e-6`. If rank is below 17, the subquantizer is
ineligible. On the final 21-codeword
support, project the fixed evidence vector `f1` and select the three eligible
subquantizers with largest projected L2 norm, breaking ties by `m`.

For the selected subquantizers, a shared seed-specific linear generator with
parameters `theta[m,4]` and no bias produces

```text
r_u,m[k] = sum_{ell=1}^4 theta[m,ell] * f_ell(u,m,k),  k in S_u,m.
```

The final patch is

```text
U, sigma, Vt = svd_float64(A_u,m, full_matrices=false)
P_u,m = I_21 - U[:,0:17] @ U[:,0:17].T
delta_u,m[S] = P_u,m @ r_u,m[S]
delta_u,m[not S] = 0
```

Concatenate the three selected support vectors as `delta_raw`. Apply the fixed
global cap

```text
delta = delta_raw * min(1, 1.0 / max(||delta_raw||_2, 1e-12)).
```

Thus `||delta||_2 <= 1.0`; positive rescaling preserves orthogonality.
Non-selected subquantizers have zero patch. Every request stores at most
`3 x 21 = 63` `(m,k,value)` entries.

Required numeric invariants are finite values, exactly 17 retained singular
directions, `max_m ||A_u,m^T delta_u,m[S]||_inf <= 1e-5`, zero values outside
support, at most 63 entries, immutable item/index hashes, and score replay
within `1e-5` absolute tolerance. The runner must reconstruct every projector
from serialized supports and centroids at serving precision and repeat the rank,
orthogonality, sparsity, and score audits after serialization. Failure is not
converted to a zero patch; it kills the design.

The formal nonrepresentability claim is deliberately table-level: a nonzero
support-restricted patch is outside the 17-dimensional codeword table class
`col([C_m,1])`. The experiment will additionally report, without using it as a
claim or gate, the relative residual of each aggregate catalog patch-score
vector after projection onto `[PQ_reconstruction, 1]`. It will not infer
catalog-score nonrepresentability from table orthogonality alone.

## Score and reference-free alignment

The base ADC table is `B_u,m[k] = dot(q_u[m], C_m[k])`. CODEPATCH scores every
eligible unseen item directly from its compact code:

```text
s_cp(u,i) = sum_m B_u,m[z_i,m] + lambda * delta_u,m[z_i,m]
```

Train `theta` independently for seeds `20260881`, `20260882`, and `20260883`
with user-macro weighting and

```text
loss = softplus(beta * (gamma
                        - s(u, chosen)
                        + s(u, rejected)))
```

using `beta=2`, `gamma=0.10`, Adam, learning rate `0.02`, weight decay `1e-4`,
gradient clipping at 1.0, and at most 64 hash-ordered R pairs per user. Train
20 epochs at `lambda_train=1.0` and retain checkpoints at epochs 5, 10, and 20.
No lambda-specific retraining is allowed. For each trainable method separately,
V first selects one common `(epoch, lambda)` across seeds from epochs
`{5,10,20}` and inference scales `{0.05,0.10,0.20,0.40}` by seed-averaged
user-macro full-catalog pair accuracy, breaking ties by smaller epoch and then
smaller lambda. With that pair frozen, V selects `alpha` solely by
seed-averaged NDCG@10, breaking ties by smaller alpha. No DPO reference model,
online LLM call, item update, or full-tuple utility is allowed.

## Candidate generation and ranking

The canonical compact-code scorer is a deterministic exact scan over all item
PQ codes, with prefix-seen items masked and ties ordered by numeric movie ID.
Its latency control is the identical scanner invoked with `delta=0`: same ADC
table construction, code array, mask, stable top-k, materialization, thread
count, timing boundaries, and interleaved request schedule. FAISS
`IndexPQ.search` supplies an additional separately reported library baseline;
it is never the denominator of the G7 relative-latency gate. A code-domain
scan accelerator may be used only if its outputs agree
with the canonical scorer within the registered score tolerance and its full
serialized/in-memory bytes are charged.

For G6, the denominator is exactly the serialized raw float32 semantic matrix,
`10,681 * 384 * 4 = 16,406,016` bytes. The numerator is the byte length of the
serialized `IndexPQ` plus every additional serving artifact needed by the
canonical scan (extracted code arrays, CSR/inverted structures, lookup metadata,
or duplicated centroids); a byte is counted again if execution requires a
second materialized copy. Ordered movie IDs, prefix-seen masks, and BPR data
are common non-semantic metadata, so they are reported separately and excluded
symmetrically from numerator and denominator. User patches are also reported
separately with exact support, `(m,k)`, float value, length, and container
overhead bytes; the 63-entry constraint is not a payload-only estimate.

Every semantic method emits exactly 100 unseen candidates. CODEPATCH also has
a rerank-only control that obtains the canonical top 512 frozen-PQ unseen
items, applies the identical patch only within that set, and emits 100.

A standard BPR-MF comparator uses 64-dimensional item factors trained from A
positives only: eight AdamW epochs, batch size 2,048, learning rate 0.025,
weight decay `1e-4`, one deterministic uniform unobserved sample per positive,
normal initialization with standard deviation 0.05, and the same three seeds
`20260881`--`20260883`. Unobserved items are samples, not asserted dislikes.
Each seed's item and trained A-user factors freeze after A. At later stages the
request vector is the trained user factor plus 0.5 times the rating-weighted
available-prefix item-factor mean, where
`weight=clip((rating-3)/2,-1,1)`. Semantic seed `s` is paired only with BPR
seed `s` for hybrid construction. BPR emits 100 unseen items per seed.

For final ranking, union a method's 100 semantic candidates with BPR's 100,
standardize each score using only prefix/catalog scores, and combine them with
`alpha * BPR + (1-alpha) * semantic`. Under the V ordering above, alpha is
selected from `{0, .25, .5, .75, 1}` separately for each registered method.
Missing branch
membership receives the registered branch floor, never an outcome-dependent
imputation. The final list has 10 items.

## Registered controls

1. Popularity and 64-dimensional BPR-MF standard baselines.
2. Full-float exact SentenceTransformer query and frozen FAISS PQ/ADC.
3. A rank-4 low-rank dense query adapter trained on the identical R pairs.
4. A globally dense pQCF-style table. For each support, compute
   `eta = pinv(A_u,m) @ r_u,m[S]` using the same float64 SVD and `1e-6`
   relative tolerance, then assign all 256 entries as
   `delta_dense = [C_m,1] @ eta`. This table is explicitly representable by a
   dense query plus a constant; projecting only on S and zero-filling is
   forbidden.
5. The unprojected sparse 63-entry LUT with identical supports and training.
   It is the closest no-orthogonalization ablation, not a claimed strict
   parameter superset because `P_u,m` varies by user.
6. A rank-matched random support-subspace control. A support-hashed Gaussian
   `21 x 4` matrix is float64-QR orthonormalized, and `Q Q^T r[S]` replaces the
   orthogonal projection. It matches CODEPATCH's four-dimensional per-support
   output capacity and sparsity without enforcing orthogonality to
   `[C_m,1]`. Its NumPy `PCG64` seed is the first unsigned little-endian
   64 bits of `SHA256("CODEPATCH-RANDOM4-20260884:m:k1,...,k21")`; QR column
   signs are canonicalized so each column's first nonzero entry is positive.
7. A label-blind user-shuffled CODEPATCH-⊥ control with identical parameters
   and density. Before any stage score is computed, cohort users are ordered by
   `SHA256("CODEPATCH-SHUFFLE-20260885:user_id")`, then numeric ID, and each
   user receives the same-stage precompiled patch of the next user in a cyclic
   rotation. This fixed-point-free derangement is frozen in the cohort manifest
   and never depends on R/V/T labels or outcomes.
8. CODEPATCH-⊥ rerank-only over the frozen PQ top 512.
9. Patch-only scoring without ADC.

All trainable controls use the same seeds, R pair pool, user-macro weighting,
optimizer budget, checkpoint set, V access, and T barrier. V freezes one
configuration for every control; no T control or seed selection is permitted.
Parameter counts, candidate work, and bytes are reported, not assumed equal.

## Natural pairs and metrics

Within R, V, or T, first remove every endpoint already observed in the prefix;
the evaluation target is a future unseen item, never a repeat. Among remaining
naturally rated items, form an unordered pair only when ratings differ by at
least 1.5. The higher-rated endpoint is chosen. Deduplicate repeated user-item
observations within the stage by retaining the latest event before pair
construction; cap at 64 pairs per user using a fixed stage-specific hash.

Primary metrics are user-macro:

- `FutureLikedRecall@100`: fraction of naturally rated, prefix-unseen stage
  items with rating at least 4.0 that appear in the pre-label candidate set.
- `CPE@100`: for each preference pair, `+1` when only the chosen endpoint is in
  candidates, `-1` when only the rejected endpoint is in candidates, and `0`
  otherwise; average within user, then across pair-bearing users.
- full-catalog preference accuracy from pre-label scores, with movie-ID tie
  breaking fixed before labels.
- binary NDCG@10, Recall@10, and explicit-dislike intrusion@10 for final lists.

All confidence bounds use a fixed 10,000-replicate paired user bootstrap. The
contributor unit is method-independent: future-positive users for
FutureLikedRecall, natural pair-bearing users for CPE, and all users with a
defined metric for the final-list endpoints. For each registered endpoint,
reinitialize NumPy `Generator(PCG64(20260981))`, draw exactly `n` contributor
indices with replacement per replicate, and recompute the complete statistic.
Bounds are raw percentile intervals using `numpy.quantile(method="linear")`:
`q=0.025` for a one-sided 97.5% lower bound, `q=0.05` for a one-sided 95%
lower bound, and `q=0.95` for a one-sided 95% upper bound. Basic, centered,
studentized, BCa, and post-hoc interval choices are forbidden. Selection and
reporting use the same prospectively named contributor unit. Report means,
medians, denominators, nonzero paired differences, and descriptive
history/popularity slices. Slices cannot rescue a gate.

For each method, first average its three seed-level outcomes within user; a
seed is never selected. Let `J` be the frozen-PQ scanner plus every frozen
matched semantic control in items 3--9 above. Separately for CPE@100 and
FutureLikedRecall@100, the registered best-control statistic is

```text
Delta_e = mean_u CODEPATCH_e(u) - max_{j in J} mean_u control_{j,e}(u).
```

Every user-bootstrap replicate resamples users jointly, recomputes each
method mean, and recomputes the maximum over `J`; it may not reuse the
point-estimate winner. The two co-primary endpoints use Bonferroni-adjusted
one-sided 97.5% lower bounds (therefore also exceeding the requested one-sided
95% standard). V freezes every method configuration, while T selects neither
a comparator nor a seed. Per-control deltas and ordinary 95% intervals are
reported descriptively in addition to the registered max-control statistic.

## Support and power floor

The fixed 5,000-user design was chosen before Cycle-8 outcomes using a paired
planning-SD assumption of 0.20; at that reference dispersion, a
0.010 effect and one-sided 97.5% bound require 4,203 users for
90% power. After V configurations freeze but before T access, use the same
endpoint-specific contributor unit and seed-averaged per-user outcomes to
define `sigma_V,e = max(0.20, max_j SD_u(CODEPATCH_e-control_j,e))`, with
sample standard deviation `ddof=1`, and compute
`n_required,e = ceil(((1.959964+1.281552)*sigma_V,e/0.010)^2)`. If either
required count exceeds 5,000, or if 5,000 fresh eligible users are unavailable,
abort before T and kill rather than weaken the effect or confidence
requirement.
Before interpreting effects, the endpoint-specific T denominator must satisfy
`n_T,e >= n_required,e`: in particular, T must contain at least
`max(3000, n_required(Recall))` future-positive users and
`max(1800, n_required(CPE))` natural pair-bearing users, as well as 15,000
retained preference pairs, and
for at least two of three seeds at least 750 users whose CODEPATCH candidate set
differs from that seed's frozen-PQ candidate set; no seed may have fewer than
250 such users. Every metric must be finite. Insufficient support kills the
design; it does not authorize a new cohort, threshold, or pair rule.

## Conjunctive promise gate

CODEPATCH-⊥ is empirically promising only if every condition below passes on
the single frozen T opening, aggregated over the three registered seeds where
applicable.

1. **G1 — preference-relevant admission.** The registered max-control
   CPE@100 point delta is at least `+0.010` and its simultaneous one-sided
   97.5% lower bound is above zero. CODEPATCH must therefore beat every member
   of `J` in the point estimate; no T comparator is selected.
2. **G2 — future-liked rescue.** The registered max-control
   FutureLikedRecall@100 point delta is at least `+0.010`, its simultaneous
   one-sided 97.5% lower bound is above zero, and CODEPATCH retains at least
   95% of full-float exact semantic Recall@100.
3. **G3 — non-dense candidate mechanism.** Full-scan CODEPATCH improves
   FutureLikedRecall@100 by at least `+0.005` over its identical top-512
   rerank-only control. Its gain over frozen PQ after orthogonal projection is
   at least half the unprojected LUT's gain over frozen PQ. CODEPATCH beats the
   globally dense pQCF-style, rank-matched random-subspace, and shuffled
   controls in both primary metrics.
4. **G4 — final relevance and dislike safety.** Against BPR and every frozen
   non-CODEPATCH hybrid, the validation-selected CODEPATCH+BPR hybrid has
   `mean(CP)-max_j mean(control_j) >= -0.002` for NDCG@10,
   `mean(CP)-max_j mean(control_j) >= -0.005` for Recall@10, and
   `mean(CP)-min_j mean(control_j) <= +0.005` for dislike intrusion@10. The
   relevant maximum or minimum is recomputed within each user-bootstrap
   replicate. The one-sided 95% lower bounds for NDCG/Recall and upper bound
   for dislike intrusion must also remain inside the stated margin.
5. **G5 — exact architecture.** Every support, rank, sparsity, orthogonality,
   score-replay, candidate-cardinality, prefix-exclusion, stage-barrier,
   immutable-hash, and finite-value invariant passes. The per-seed
   frozen-PQ candidate-turnover floor defined above passes.
6. **G6 — storage.** Serialized FAISS PQ index plus every serving-required
   compact-code scan structure is at most one eighth the frozen float32
   semantic-index bytes. Each cached user patch has at most 63 entries; code,
   value, support, and metadata bytes are all reported.
7. **G7 — latency.** With patches precompiled on interaction update, warmed
   single-query p95 from ADC-table construction through masking and top-100
   materialization is at most `1.25x` the identical `delta=0` canonical
   full-code scanner and at most `1.0 ms` on the registered CPU. Patch
   compilation p95 is at most 10 ms. `IndexPQ.search` latency is reported
   separately and cannot satisfy or fail the ratio.
8. **G8 — seed stability and power.** The support floor passes. For seed `s`
   and endpoint `e`, define
   `d_s,e = mean_u(CODEPATCH_s,e) - max_{j in J} mean_u(control_j,s,e)`.
   At least two of three seeds have `d_s,e > 0` for both co-primary endpoints;
   no `d_s,e` is below `-0.002`. The prospective V-based required-sample
   calculation also passes before T is opened.
9. **G9 — provenance and one-shot authority.** Source, config, protocol,
   archive, all three denylist-source artifacts, the reconstructed 6,170-ID
   denylist, cohort, embeddings, factors, indexes, codes, supports,
   checkpoints, manifests, results, environment, stdout/stderr, and completion
   markers are hash-bound. A separate post-exit verifier reproduces G1–G8 and
   alone may publish the final promising marker. Any exception, nonempty async
   error ledger, source drift, missing artifact, or unauthorized run fails.

The gate is a strict conjunction. A false, missing, nonfinite, unsupported, or
unauthenticated condition is failure.

## Immediate kill and loop rule

Any failed gate kills CODEPATCH-⊥ immediately. In particular, kill if the gain
exists only for already consumed items, disappears under exact orthogonal
projection, is explained by the dense-parallel or unprojected control, occurs
only after unchanged-candidate reranking, violates the byte/latency budget, or
cannot be externally authenticated. Do not change thresholds, seeds, support,
cohort, pair rules, source, or code after T access; do not repair, resume, or
rerun. Record the negative result and return to Phase 1 with a new architecture.

Phase 5 and the paper-writing/compiler skills remain forbidden until the
external G1–G9 conjunction is true.
