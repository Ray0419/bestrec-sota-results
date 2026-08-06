# Phase 2, Cycle 6: PIVOT Research Question and PoC Gate

Date drafted: 2026-08-07

Status: **PROSPECTIVELY LOCKED AFTER INDEPENDENT CONSTRUCT REVIEW**

Phase 5 status: forbidden unless every registered gate passes on the sealed test

## Primary research question

> On a prospectively selected, cycle-5-disjoint 600-user temporal MovieLens 10M
> cohort, can PIVOT reuse one fixed-margin, reference-free user-to-partition
> potential for both four-shard FAISS probing and cross-shard ranking, improving
> future-liked-item Recall@100 and fixed-pair candidate preference exposure by at
> least `+0.010` over an equal-shard-search-work balanced geometric baseline,
> while
> retaining at least 90% aligned-oracle top-100 overlap, at least 95% of raw
> full-exact future-liked recall, using exactly 1,336 shard-item dot products,
> and avoiding material NDCG@10 or p95-latency regression?

This question is novel only at the shared routing/ranking interface identified
in Phase 1. It is empirically testable and targets a specific scale/alignment
gap: ordinary IVF spends a fixed probe budget on geometric proximity, while an
aligned downstream ranker cannot recover items in unprobed cells.

## Hypothesis and mechanism

For immutable item vector `E_i`, immutable cell assignment `c(i)`, normalized
prefix-only user query `q_u`, and a bounded 32-way offset `o_theta(h_u)`, define

```text
route_theta(u,c) = dot(q_u, centroid_c) + o_theta(h_u)[c]
score_theta(u,i) = dot(q_u, E_i)       + o_theta(h_u)[c(i)]
```

PIVOT probes the four cells with greatest `route_theta`, then ranks their unseen
items with `score_theta`. The same learned scalar for a cell therefore controls
whether the cell is searched and how its items compare with items from other
searched cells. A pair from distinct cells trains that scalar with

```text
softplus(beta * (gamma - score_theta(u, chosen)
                       + score_theta(u, rejected))).
```

There is no DPO reference model, query rotation, learned item embedding, index
update, dynamic margin, admission cutoff, fallback selector, or online LLM.

## Dataset and fresh cohort

- Official MovieLens 10M archive, size `65,566,137`, SHA-256
  `813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`,
  MD5 `ce571fd55effeba0271552578f2648bd`.
- Allowed inputs: `ratings.dat` and `movies.dat`; `tags.dat` is forbidden.
- The prior cycle-5 cohort record has SHA-256
  `eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126`.
  Every listed user is excluded before cycle-6 selection.
- Structural eligibility: 80-300 events inclusive and at least four distinct
  timestamp groups. This was checked without item/rating parsing; 21,931 users
  satisfy it after the cycle-5 exclusion.
- Order structurally eligible users by
  `SHA256("20260861:{user_id}")`, then numeric user ID. In that immutable order,
  retain the first 600 whose `A` block contains at least five distinct items
  rated at least 4. Fewer than 600 fails closed; rejected users are never used in
  training or evaluation.
- The `A`-only filter is fixed prospectively. It may not inspect `R`, `V`, or `T`
  identities, ratings, positives, pairs, candidates, or metrics.

Within each retained user, sort by `(timestamp, source_row_ordinal)`, keep equal
timestamps indivisible, and allocate consecutive timestamp groups to
`A/R/V/T = 60/20/10/10%` by nearest cumulative event count, breaking a cutoff
tie toward the earlier block. Adjacent nonempty blocks require strict timestamp
increase. Repeated `(user,item)` events fail closed.

`A` supplies one fixed query and descriptor used for training, validation, and
test; only the chronological history mask grows. `R` supplies training pairs.
`V` may select one checkpoint from the prospectively fixed epoch set
`{5,10,20,40}` by the mean cross-cell pair accuracy across all three
optimization seeds, with an earlier-epoch tie break. All seeds therefore use
the same selected epoch. `T` remains sealed until the selected epoch, indexes,
and all method artifacts are frozen.

Validation checkpoint pairs use the same rating-gap definition restricted to
cross-cell pairs, capped at 64 per user by ascending
`SHA256("20260867:{user_id}:{low_item_id}:{high_item_id}")`. A separate fixed
validation estimand pair set matches the test CPE construction exactly: all
distinct unseen `V` endpoint pairs with a rating gap of at least 2, capped at
100 per user by ascending
`SHA256("20260869:{user_id}:{low_item_id}:{high_item_id}")`. Its cross-cell
subset is diagnostic only. Before joining `V`, the complete candidate/score
bank for every registered checkpoint, seed, and method is published; `V` may
choose only the common epoch and stronger raw relevance comparator named below.

Stage barriers are mandatory. Publish and hash the `A`-only query/descriptor,
raw routes, history, and target-blind `R` basis before joining `R` item/rating
payload. After `R` training, publish the `A`-descriptor plus `A union R`-mask
validation routes/candidates before joining `V`. Freeze the common epoch and all
model hashes, then publish the `A`-descriptor plus `A union R union V`-mask test
routes/candidates before the sole `T` join. Current-stage identities or ratings
may not affect descriptors, routes, candidates, work, cohort selection, or
hyperparameters before the registered join.

MovieLens is exposure-conditioned. No causal, unbiased-exposure, fairness,
long-term-utility, or online-engagement claim is allowed.

## Fixed representation and vector partitions

Movies are rendered as `{title} [SEP] {genres}` and encoded by local frozen
`sentence-transformers/all-MiniLM-L6-v2` into normalized 384-dimensional
float32 vectors in ascending numeric movie-ID order. The already produced,
target-independent matrix may be reused only if its SHA-256 is exactly
`8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768`;
otherwise the runner must re-encode before any cycle-6 target access.

Construct 32 capacity-balanced spherical shards before cycle-6 target access:

1. run `MiniBatchKMeans` with seed `20260861`, batch size 1,024, five
   initializations, 100 maximum iterations, zero reassignment ratio, one thread,
   and the prospectively bound scikit-learn version;
2. L2-normalize the initial centroids and canonicalize their labels by ascending
   SHA-256 of canonical float32 centroid bytes, then original label;
3. set capacities to 334 real items for canonical cells 0-24 and 333 for cells
   25-31;
4. compute every item-centroid inner product, sort all edges by descending
   float32 score, numeric movie ID, then canonical cell ID, and greedily assign
   an unassigned item to a nonfull cell until all capacities are met;
5. recompute and normalize each centroid once from its assigned real items,
   without reassignment; and
6. add one zero-vector sentinel with a forbidden negative ID to each 333-item
   shard, so every immutable `faiss.IndexFlatIP` contains exactly 334 physical
   slots.

This is a balanced spherical partition, not ordinary unbalanced IVF. Geometric
routing is exactly `dot(q_u, centroid_c)` for both the baseline and PIVOT before
the latter adds its offset. Cell assignments, centroids, sentinels, and 32 shard
indexes remain immutable. The real-embedding qualification must be rerun on this
final balanced construction before authorization; it may not inspect user
outcomes.

From `A` only, define normalized liked (`rating >= 4`) and disliked
(`rating <= 2`) centroids, using zero for an empty disliked set:

```text
liked_u    = normalize(mean(E_i for liked A items))
disliked_u = normalize(mean(E_i for disliked A items)), or zero
q_u        = normalize(liked_u - 0.25 * disliked_u)
h_u        = concat(q_u, liked_u, disliked_u, min(A_count,300)/300)
```

The five-liked `A` predicate makes `q_u` defined. No current-block identity or
rating enters the descriptor.

## Fixed model and training

The offset network is `Linear(1153,32) -> tanh -> Linear(32,32) -> tanh`. If its
last tanh output is `z_u`, the identifiable centered potential is
`o_u = 0.05 * (z_u - mean_c z_u[c])`, so every pairwise offset difference is at
most 0.10 in magnitude. The last layer is initialized to exact zero.
Training uses seeds `{20260861,20260862,20260863}`, Adam, learning rate `0.003`,
weight decay `1e-4`, gradient norm clip `1.0`, `beta=5`, fixed margin
`gamma=0.05`, and checkpoints after epochs `{5,10,20,40}`.

Natural `R` pairs require distinct items and a rating gap of at least 2. The
higher-rated item is chosen. Pairs in the same cell are retained for diagnostics
but have no offset gradient. Cross-cell pairs are deterministically capped at 64
per user by ascending
`SHA256("20260862:{user_id}:{low_item_id}:{high_item_id}")`. Losses are averaged
within user before averaging users. A shuffled-direction model independently
flips each canonical low/high direction with the fixed hash coin
`SHA256("20260863:{user_id}:{low_item_id}:{high_item_id}")`; it uses the same
pairs, initialization schedule, optimizer steps, and selected epoch.

## Canonical retrieval and fixed work

For every request evaluated under fixed-work method 3-7:

1. calculate the 32 route logits and select exactly four distinct cells by
   descending logit, then numeric cell ID;
2. ask each selected immutable `IndexFlatIP` for all 334 physical slots;
3. remove sentinels and chronological prefix items;
4. add the method's constant cell offset to each canonical float32 FAISS score;
5. stable-sort by descending adjusted score, then numeric movie ID; and
6. return exactly 100 unique unseen items.

Every fixed-work method 3-7 searches exactly `4 * 334 = 1,336` shard slots.
With at least 333 real items per cell and at most 300 total user events, any
four cells leave at least 1,032 unseen real items, so top-100 underfill is
impossible for a valid request. The coarse route adds 32 centroid dot products,
for 1,368 vector dot products or 12.81% of full-catalog item count. The MLP
FLOPs and seven sentinel slots are reported separately. Underfill or unequal
physical shard work in methods 3-7 is a construction/integrity failure.

FAISS scores define deployed ordering. Exhaustive aligned scoring searches all
32 immutable shards with the same FAISS score path, adds the same offsets, and
forms an `AlignedOracleTop100`. A separate matrix implementation aligns scores
by item ID, checks `rtol=2e-6, atol=2e-6`, and reports the rank-100/101 margin and
tolerance-defined near-tie set. Exact ID/order equality across numerical kernels
is not a gate, and no oracle may silently replace the canonical FAISS result.

## Registered methods and controls

1. **Popularity:** prefix-unseen global `A`-only popularity.
2. **Raw full exact semantic:** all 32 shards with raw `q_u` and raw cosine;
   quality/work upper reference, not an equal-search-work comparator.
3. **Balanced geometric IVF:** four cells by spherical query-centroid similarity
   and raw item cosine; the primary equal-shard-search-work baseline.
4. **PIVOT route-only:** PIVOT cells, raw item cosine ranking.
5. **PIVOT rerank-only:** geometric cells, PIVOT adjusted item ranking.
6. **PIVOT full:** PIVOT cells and PIVOT adjusted item ranking.
7. **Shuffled PIVOT:** full mechanism trained on the registered hash-randomized
   pair directions.
8. **Aligned full exact:** all 32 shards with PIVOT adjusted scoring; diagnostic
   ceiling used only for `AlignedOracleOverlap@100`.

Fixed-work methods 3-7 share vectors, cells, indexes, `nprobe=4`, history mask,
candidate quota, FAISS calls, tie rule, work accounting, and latency harness.
Full-exact methods 2 and 8 scan all 10,688 physical shard slots and are excluded
from the equal-search-work and G8 latency comparisons.

## Fixed test estimands

For `T`, candidates and rankings are published before joining ratings. A
relevant item has rating at least 4. The method-independent sealed pair set uses
distinct unseen `T` endpoints with a rating gap of at least 2 and a deterministic
cap of 100 per user by ascending
`SHA256("20260865:{user_id}:{low_item_id}:{high_item_id}")`. Pair IDs and
directions are identical across methods and seeds.

- **FutureLikedRecall@100:** per-user fraction of unique relevant `T` items in
  the method's 100 candidates.
- **CandidatePreferenceExposure@100 (CPE):** per-user mean over the fixed pairs
  of `1[chosen in C] - 1[rejected in C]`; both-in and neither-in contribute zero.
  The all-pair value is primary; a cross-cell-only value is diagnostic.
- **AlignedOracleOverlap@100:** per-user set overlap between PIVOT top-100 and
  the exhaustive aligned top-100, divided by 100.
- **RawExactRetention:** PIVOT FutureLikedRecall@100 divided by raw full-exact
  FutureLikedRecall@100; the denominator and supported-user count are reported,
  and zero aggregate support fails closed.
- **sPCE@10:** 1 only when the chosen endpoint has a strictly better served
  top-10 rank than the rejected endpoint; unshown endpoints receive rank 11.
- **NDCG@10 / Recall@10:** binary relevance over observed `T` items.
- **LowRatingIntrusion@10:** count of top-10 items observed in `T` with rating at
  most 2, divided by 10; unobserved items remain unknown.
- **Changed surface:** fraction of users whose PIVOT route/candidate set differs
  from balanced geometric IVF and mean candidate-set Jaccard distance.
- **Work and latency:** coarse dot products, physical shard-slot dot products,
  real items, sentinel count, MLP FLOPs, and single-thread batch-1 p95.

Metrics are user-macro. Paired uncertainty uses 5,000 user-cluster bootstrap
draws with seed `20260864`; missing-user intersections and sample sizes are
reported explicitly.

## All-or-nothing PoC promise gate

1. **G1 - construction and provenance.** Exactly 600 fresh users, 32 immutable
   balanced cells, 334 physical slots per shard, unchanged
   source/archive/vector/assignment/index hashes, correct stage barriers,
   finite canonical FAISS scores, all three seeds, and a complete artifact
   inventory. Every fixed-work method 3-7 uses four distinct probes, exactly
   1,336 searched shard slots, and 100 unique unseen real candidates. Every
   333-item shard contributes exactly one filtered sentinel.
2. **G2 - material equal-search-work gain.** After averaging all three seeds within
   user, PIVOT minus balanced geometric IVF is at least `+0.010` for both
   FutureLikedRecall@100 and CPE@100, with paired 95% user-bootstrap lower bounds
   above zero on fixed common-user denominators.
3. **G3 - shared-mechanism evidence.** The four factorial cells use the same
   selected PIVOT checkpoint: geometric `(route=0,rank=0)`, route-only `(1,0)`,
   rerank-only `(0,1)`, and PIVOT `(1,1)`. PIVOT exceeds each single-use control
   by at least `+0.002` on both FutureLikedRecall@100 and CPE@100, with every
   paired lower bound above zero. Its CPE gain over shuffled PIVOT is at least
   `+0.010`, with lower bound above zero.
4. **G4 - routing fidelity and semantic retention.** Mean
   AlignedOracleOverlap@100 is at least `0.90`, and PIVOT
   FutureLikedRecall@100 is at least 95% of raw full-exact semantic
   FutureLikedRecall@100. Score error and near-tie diagnostics are finite and
   complete; cross-kernel ID/order equality is neither required nor credited.
5. **G5 - served relevance and preference safety.** Validation chooses the
   stronger NDCG@10 comparator from balanced geometric IVF and raw full exact,
   before `T`. Against that fixed comparator, PIVOT's T NDCG@10 point delta is
   at least `-0.002` with paired lower bound above `-0.005`, Recall@10 point
   delta is at least `-0.005` with lower bound above `-0.010`, and sPCE@10 point
   delta is nonnegative. Against balanced geometric IVF, the paired upper bound
   on LowRatingIntrusion@10 increase is at most `+0.002`.
6. **G6 - support, power, and action surface.** `R` supplies at least 5,000
   cross-cell pairs from 400 users. `T` has relevant endpoints for at least 400
   users and at least 1,500 fixed pairs from 300 users. `V` must independently
   have relevant endpoints for at least 400 users and at least 1,500 fixed pairs
   from 300 users. After checkpoint and comparator choices freeze but before
   `T`, form finite common-user, three-seed-averaged PIVOT-minus-geometric V
   vectors for both primary metrics. Subtract each vector's mean and add
   `+0.010` without clipping. For each of 500 outer user resamples, run the
   registered 500-draw paired inner bootstrap; detection means its 2.5th
   percentile is above zero. Seed `20260866` must yield at least 80% detection
   for both effects. The CPE vector uses the fixed all-pair V estimand set, not
   the checkpoint-selection subset. Any V support/power failure kills before
   `T`. Averaged over all three seed-by-user rows, PIVOT's selected four-cell set
   differs from balanced geometric IVF on at least 10%. Averaged over every
   seed-by-endpoint row formed from the unique fixed-T-pair endpoint IDs, the
   XOR of PIVOT and geometric candidate-membership indicators is one on at
   least 5%. Empty, nonfinite, or unsupported cohorts fail closed.
7. **G7 - seed stability without rescue.** All three seeds complete and enter
   the seed-averaged primary statistic. At least two individually have positive
   PIVOT-over-geometric deltas for both primary metrics. No seed has a negative
   delta on either primary metric or an NDCG@10 delta below `-0.005` versus the
   fixed stronger relevance comparator.
8. **G8 - serving cost.** Every fixed-work method 3-7 performs exactly 32 coarse
   and 1,336 shard-slot dot products. Select 512 requests by ascending
   `SHA256("20260868:{user_id}")`, then user ID. On one pinned CPU core, one
   FAISS/Torch/BLAS thread, 32 warmups, and seven deterministic AB/BA
   repetitions, worst-seed PIVOT batch-1 p95 is at most 3 ms and at most 1.5
   times balanced-geometric p95. Per-request medians time `A` descriptor/query
   construction, offset inference, coarse scores, four complete-shard searches,
   sentinel/history masking, merge, and stable top-100; no test-user offset may
   be cached. Hardware, interpreter, packages, affinity, threads, and peak RSS
   are bound. An outcome-free timing qualification must pass before launch.
9. **G9 - falsification authority.** The runner publishes only a non-authoritative
   candidate. After runner exit and lock release, a separate source-bound
   verifier authenticates the raw arrays and recursive artifact closure,
   independently replays G1-G8 from fixed pair IDs, and alone may publish the
   authoritative completion marker. `PROMISING` is the conjunction of all gates.
   Any exception, unsupported cohort, false gate, missing marker/artifact, or
   incomplete result kills PIVOT without repair/rerun and returns the sprint to
   Phase 1.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

Only `PROMISING=true` authorizes Phase 5.
