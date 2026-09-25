# CODEPATCH-⊥ PoC Protocol v1

Date frozen: 2026-08-07

Status: outcome-blind Phase-3 execution lock. No Cycle-8 `A`, `R`, `V`, or
`T` rating payload has been opened. This protocol and
`src/configs/codepatch_poc_ml10m_v1.json` must be source-bound before the
one authorized run starts. The research question in
`literature/research-question-cycle8.md` is the scientific authority; the JSON
configuration is the execution-authoritative scalar and enum record. Any
disagreement, omission, nonfinite value, or unauthorized default fails closed.

## 1. One-shot authority and immediate-kill rule

CODEPATCH-⊥ receives one source/config/protocol-bound execution on one frozen
MovieLens-10M cohort. The launcher must atomically claim the execution
fingerprint before opening any Cycle-8 rating payload. A pre-A authentication
failure may terminate without consuming the cohort, but once any selected-user
`A` payload is opened there is no repair, resume, retry, source substitution,
threshold change, seed change, or second outcome run. Any exception, nonempty
asynchronous-error ledger, drift, missing artifact, failed support floor, or
failed G1–G9 conjunct kills the design and returns the autoresearch outer loop
to Phase 1. Phase 5 remains forbidden unless a separate post-exit verifier
reproduces G1–G8 and publishes the sole authoritative promising marker.

## 2. Immutable inputs and prior-user denylist

The only dataset is the official 65,566,137-byte MovieLens-10M archive at
`adaptive-recsys-ara/data/ml-10m-cycle5/ml-10m.zip`, SHA-256
`813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`.
Only `ml-10M100K/ratings.dat` and `ml-10M100K/movies.dat` may be read;
`tags.dat` is forbidden.

Before opening the Cycle-8 archive, reconstruct the conservative numeric-ID
denylist from these workspace-relative, immutable sources:

| Opened cohort source | Required path | IDs | SHA-256 |
|---|---|---:|---|
| Cycle 1 | `adaptive-recsys-ara/experiments/runs/ripple_poc_runs/ripple-poc-v1-20260806T151915122332Z-3c42fceedbb9/split_manifest_5f1b2f34d028c83b_seq001.json` | 801 | `cacc93ef5b13b4367cdb3e324a5f02da33c906765873027081166ea5fbf3e23c` |
| Cycles 2–4 | `adaptive-recsys-ara/experiments/runs/facet_pref_poc_runs/facet-pref-poc-v1-20260807-prospective-seq001/cohort_lock_2f652fb34c7ac639_seq001.json` | 4,000 | `0f5b2af075cf2850aa8bdd32e7cde577859167148d2459cfe9d5fd327c1a4812` |
| Cycle 5 | `_bestrec_run/cable_pref_poc_runs/cable-pref-poc-v1-cycle5-20260807/cohort.json` | 2,000 | `eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126` |

Ignore release namespaces, take the sorted integer union, and encode it as
compact JSON followed by exactly one newline. It must contain 6,170 IDs and
hash to
`fb24b4ec2477e9e014c2e63fc16ae50df548e7fa1c2d49e4ef0c2463cf4289bf`.
Persist the reconstructed artifact and extraction audit. A missing input,
unexpected schema, source/count/hash mismatch, duplicate within a source, or
union mismatch kills the design before any `A/R/V/T` access. Cycles 6 and 7
contribute no IDs.

## 3. Target-blind cohort construction

The archive is scanned first for user ID, timestamp, source ordinal, and event
count only. For each non-denied user, group equal timestamps and enumerate all
three legal cut triples yielding nonempty, strictly time-ordered `A/R/V/T`
blocks. Minimize total absolute event-count deviation from 60/20/10/10 percent;
ties use the lexicographically earliest cutoff triple. Require 80–300 events,
at least four timestamp groups, at least 20 `A` events, and nonempty `R`, `V`,
and `T`. Persist the structural-layout manifest before reading any rating
value.

Next, read values from `A` only. Require at least five distinct `A` movies
rated at least 4.0 and at least three distinct `A` movies rated at most 2.5.
Do not inspect any selected user's `R/V/T` identity or value. Order eligible
users by `SHA256("20260881:{user_id}")`, then numeric ID, and freeze exactly
the first 5,000. Persist the A-screening/cohort manifest, layouts, hashes, and
the fixed-point-free shuffle derangement before materializing `A` histories or
training tensors. Fewer than 5,000 users kills the project before selected-user
`R/V/T` access. The archive-wide eligible count is neither asserted nor gated.

## 4. Frozen representation and compact index

For ascending movie ID, item text is the UTF-8 title followed by the literal
` [SEP] ` delimiter and the original pipe-separated genre string. Reuse the normalized float32
`sentence-transformers/all-MiniLM-L6-v2` matrix only after checking archive
movie order, model ID, package version, shape `10,681 x 384`, byte layout, and
cache SHA-256
`8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768` at
`_bestrec_run/cable_pref_poc_runs/cable-pref-poc-v1-cycle5-20260807/immutable/semantic_vectors.npy`.

Train one deterministic inner-product `faiss.IndexPQ(384,24,8)` with one CPU
thread and the locked FAISS clustering seed. Freeze and hash centroids, the 24
one-byte codes per item, ordered movie IDs, serialized index, and any exact-scan
copy before `R`, `V`, or `T` is opened. A rating may never change an item
vector, centroid, code, assignment, membership, or catalog order.

The canonical semantic scorer is a deterministic exact scan of every compact
item code, masks all prefix-seen movies, and breaks score ties by numeric movie
ID. Every semantic method emits exactly 100 unseen candidates. FAISS
`IndexPQ.search` is reported separately and is never the G7 denominator.

## 5. Stage barriers

1. **A:** Freeze three BPR item models and A-user factors, representation and
   PQ artifacts, prefix histories, CODEPATCH supports, and a target-blind R
   prefix/support manifest. An R score manifest is neither possible nor
   required because R supplies training pairs.
2. **R:** Only after every R prefix/support record is durable, join R ratings,
   form the fixed natural-pair pool, and train all aligned methods with R only.
3. **V:** Build and persist every V candidate/score/support/patch manifest from
   A+R before joining V. V freezes one checkpoint/scale per trainable method
   across all seeds and one hybrid alpha per method. No method, control, or seed
   is dropped.
4. **T:** Freeze all choices, rebuild histories from A+R+V, and persist every T
   candidate, score, ranking, support, patch, latency request ID, and hash before
   joining T. Open T exactly once.

Current-stage identities, labels, pair counts, or outcomes must not influence
current-stage histories, supports, patches, candidates, scores, tie breaks,
work, latency selection, cohort membership, or method identity.

## 6. Prefix features, supports, and exact orthogonal patch

Sort each available prefix by `(timestamp, source_ordinal)`. Let `y=+1` for a
rating at least 4.0, `y=-1` for a rating at most 2.5, and zero otherwise; let
`rho_j=(j+1)/n`. The base query is the L2-normalized positive embedding
centroid minus one half the negative centroid, or the normalized positive
centroid alone if there is no negative. Compute the four exact codeword
features registered in the JSON configuration; they contain no user/movie ID,
current-stage information, BPR score, candidate membership, or outcome count.

For each PQ subquantizer, rank observed codewords by descending
`abs(f1)+abs(f2)`, count, then codeword ID; fill from the fixed catalog-frequency
order. Deterministically replace the weakest fill until the 21-row
`A=[C_m[S],1]` has float64-SVD rank exactly 17 at relative tolerance `1e-6`.
Project `f1` on the final support and select the three eligible subquantizers
with greatest projected L2 norm, ties by subquantizer ID.

The outcome-free frozen-centroid audit establishes that the full 256-row
`[C_m,1]` matrix has rank 16 for zero-based subquantizers 7, 13, and 19, so
those subquantizers are globally ineligible and are never rank-repaired.
Request-specific rank-16 supports in any other subquantizer are likewise
ineligible. Every request must still supply at least three eligible
subquantizers; otherwise the architecture fails before that stage's labels are
opened.

For seed-specific shared parameters `theta[m,4]` with no bias, compute
`r[S]=theta[m]·f(m,S)`. Recompute the float64 SVD and apply
`delta[S]=(I-U[:,0:17]U[:,0:17]^T)r[S]`; all other table entries are exact
zero. Concatenate the three patches and rescale positively only when needed so
the global L2 norm is at most 1.0. Store no more than 63 `(m,k,value)` entries.

Serving reconstructs every projector from serialized supports and centroids
and repeats the finite, rank-17, `||A^T delta||_inf <= 1e-5`, outside-support
zero, entry-count, immutable-hash, and `1e-5` score-replay audits. Any failure
kills; it may not become a zero patch. Table-level nonrepresentability is the
only formal claim. Catalog patch-score residual against
`[PQ_reconstruction,1]` is descriptive and ungated.

## 7. Scores and reference-free training

For code `z_i`, use

```text
s_cp(u,i) = sum_m dot(q_u[m], C_m[z_i,m])
            + lambda * delta_u,m[z_i,m].
```

Train independently at seeds 20260881, 20260882, and 20260883 with at most 64
hash-ordered R natural pairs per user, user-macro weighting, and
`softplus(2 * (0.10 - s(chosen) + s(rejected)))`. Use Adam, learning rate
0.02, weight decay `1e-4`, gradient clip 1.0, 20 epochs, training scale 1.0,
and checkpoints 5/10/20. No DPO reference model is used.

For each trainable method, V selects one common `(epoch,lambda)` across seeds
from epochs `{5,10,20}` and scales `{.05,.10,.20,.40}` using seed-averaged
user-macro full-catalog preference accuracy, ties by lower epoch then scale.
With that pair fixed, V selects alpha from `{0,.25,.5,.75,1}` by seed-averaged
NDCG@10, ties by lower alpha. T chooses no seed, comparator, checkpoint, scale,
or alpha.

## 8. BPR, hybrid ranking, and registered controls

BPR-MF uses 64-dimensional factors trained from A positives only for eight
AdamW epochs, batch 2,048, learning rate .025, weight decay `1e-4`, normal
initialization SD .05, one deterministic uniformly sampled unobserved item per
positive, and the three registered seeds. Item and A-user factors freeze after
A. At R/V/T, the request vector adds 0.5 times the available-prefix item-factor
mean weighted by `clip((rating-3)/2,-1,1)`. Semantic seed `s` pairs only with
BPR seed `s`.

Each semantic branch and BPR emits 100 unseen items. Their union is ranked by
`alpha*BPR_z + (1-alpha)*semantic_z`, where each z-score uses that request's
prefix-unseen catalog distribution. Missing branch membership receives the
registered target-blind branch floor. The final list contains 10 unique unseen
items with movie-ID tie breaking.

The complete fixed method registry is:

1. A-only popularity and 64-dimensional BPR-MF.
2. Exact full-float SentenceTransformer query and frozen PQ/ADC.
3. Rank-4 dense query adapter on the identical R pairs.
4. Globally dense pQCF-style table: `eta=pinv([C[S],1])r[S]`, followed by
   `[C_all,1]eta` at all 256 codes; projection on S followed by zero fill is
   forbidden.
5. Unprojected sparse 63-entry LUT with identical supports and budget.
6. Rank-matched support-hashed random four-dimensional subspace using the
   exact PCG64 seed and QR-sign rule in the configuration.
7. Label-blind cyclic user-shuffled CODEPATCH patch using the fixed cohort
   order `SHA256("CODEPATCH-SHUFFLE-20260885:{user_id}")`.
8. Identical CODEPATCH patch reranking only the frozen-PQ top 512.
9. Patch-only full-code scan without ADC.

All trainable controls use the same seeds, R pair pool, user-macro loss,
optimizer/checkpoint budget, V access, and T barrier. V freezes every control.
Parameter counts, candidate work, and bytes are reported.

## 9. Targets, metrics, bootstrap, and prospective power

Within R/V/T, remove prefix-observed endpoints, keep the latest repeated
user-item event, form a natural pair only for rating gap at least 1.5, choose
the higher rating, and retain at most 64 pairs per user by the fixed
stage-specific hash. Report user-macro FutureLikedRecall@100, CPE@100,
full-catalog pair accuracy, binary NDCG@10, Recall@10, and explicit-dislike
intrusion@10 exactly as defined in the configuration.

Average each method's three seed outcomes within user before aggregate paired
tests. For each endpoint reinitialize NumPy `Generator(PCG64(20260981))` and
run 10,000 paired user-bootstrap replicates. Draw exactly the contributor count
with replacement; use raw percentile bounds via
`numpy.quantile(method="linear")`. The co-primary best-control statistic
recomputes the maximum over frozen PQ plus controls 3–9 inside every replicate.
G1/G2 use Bonferroni-adjusted one-sided 97.5% lower bounds. Report point means,
medians, denominators, nonzero paired differences, all per-control deltas, and
descriptive history/popularity slices; slices cannot rescue a gate.

Before T, from frozen V outcomes compute for each co-primary endpoint
`sigma=max(.20,max_j SD(CODEPATCH-control_j,ddof=1))` and
`n_required=ceil(((1.959964+1.281552)*sigma/.010)^2)`. Kill before T if either
value exceeds 5,000. On T require each endpoint contributor count to meet its
own `n_required`, at least 3,000 future-positive users, 1,800 pair-bearing
users, 15,000 retained pairs, at least 750 changed-candidate users for at least
two seeds, and at least 250 for every seed. Every metric must be finite.

## 10. Storage and latency accounting

G6 denominator is exactly `10,681*384*4 = 16,406,016` serialized float32
semantic bytes. The numerator is serialized IndexPQ plus every separately
materialized serving artifact required by the canonical scan; duplicated
codes/centroids are charged twice. Ordered IDs, seen masks, and BPR data are
reported as common metadata and excluded symmetrically. Patch serialization
reports payload, support, codes, float values, lengths, metadata, and container
overhead; the 63-entry limit is exact, not an estimate.

G7 compares warmed single-query p95 CODEPATCH latency with the identical
canonical scanner at `delta=0`, using the same table construction, code array,
mask, stable top-k, materialization, thread count, timing boundary, and
interleaved target-blind request schedule. Timing begins before ADC-table
construction and ends after top-100 materialization. CODEPATCH p95 must be at
most 1.25 times control p95 and at most 1.0 ms; precompiled patch generation
p95 must be at most 10 ms. The machine/environment fingerprint, request IDs,
raw timings, warmups, and schedule are immutable. IndexPQ library-search
latency is descriptive only.

## 11. Conjunctive G1–G9 promise gate

- **G1 Preference admission:** max-control CPE delta at least +.010 and its
  simultaneous one-sided 97.5% lower bound above zero.
- **G2 Future-liked rescue:** max-control FutureLikedRecall delta at least
  +.010, its simultaneous one-sided 97.5% lower bound above zero, and
  CODEPATCH Recall at least 95% of exact full-float Recall.
- **G3 Mechanism:** full scan beats identical top-512 rerank by at least +.005
  FutureLikedRecall; projected gain over PQ is at least half unprojected gain;
  CODEPATCH beats dense-pQCF, random-rank4, and shuffled controls in both
  co-primary metrics.
- **G4 Final relevance/safety:** relative to BPR and every frozen non-CODEPATCH
  hybrid, CODEPATCH+BPR max-control delta is at least -.002 NDCG and -.005
  Recall, and its min-control dislike-intrusion delta is at most +.005. The
  corresponding one-sided 95% bootstrap bounds remain inside the margins with
  max/min recomputed in each replicate.
- **G5 Exact architecture:** all algebraic, serialization, replay, cardinality,
  prefix exclusion, stage, hash, finite, and candidate-turnover invariants pass.
- **G6 Storage:** charged serving bytes are at most 2,050,752 bytes (one eighth
  of 16,406,016), every patch has at most 63 entries, and all patch bytes are
  reported.
- **G7 Latency:** canonical ratio at most 1.25, retrieval p95 at most 1.0 ms,
  and patch-compilation p95 at most 10 ms.
- **G8 Seed stability/power:** the prospective power and support floors pass;
  at least two seeds have positive per-seed best-control deltas for both
  endpoints, and no seed/endpoint delta is below -.002.
- **G9 Provenance/one shot:** every named source and artifact is recursively
  hash-bound; all exits, locks, logs, ledgers, stage times, and completion
  markers authenticate; the independent verifier alone publishes the verdict.

The verdict is `PROMISING=true` only for the strict conjunction G1 through G9.
A false, missing, nonfinite, unsupported, or unauthenticated conjunct is
failure. Failed CODEPATCH-⊥ is discarded immediately; no Phase-5 artifact may
be drafted from runner-candidate evidence.
