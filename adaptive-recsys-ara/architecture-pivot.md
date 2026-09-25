# Phase 3, Cycle 6: PIVOT Architecture

Status: outcome-blind architecture lock. The authoritative Phase-2 record is
`literature/research-question-cycle6.md`. If this document, the protocol, or
the JSON configuration weakens or conflicts with a Phase-2 cohort rule, stage
barrier, estimand, comparator, threshold, or fail-closed condition, the
Phase-2 record wins and execution must stop.

No MovieLens 10M `R`, `V`, or `T` identity, rating, pair, candidate, or quality
outcome was inspected while this document was written.

## Scope and claim boundary

PIVOT is **Preference-Informed Vector-partition Offsets for Traversal**. It
tests one narrow systems hypothesis: a single bounded, reference-free
user-to-partition potential can jointly decide which four immutable semantic
shards receive work and how survivors from those shards are ranked.

The following are infrastructure or prior art and are not claimed as novel:

- SentenceTransformer metadata embeddings;
- MiniBatchKMeans, balanced assignment, FAISS, `IndexFlatIP`, or exact
  inner-product search;
- generic personalized routing or additive score calibration;
- SimPO or fixed-margin pairwise preference learning; and
- exhaustive search, popularity, or geometric retrieval baselines.

The candidate contribution is the shared interface: the same learned scalar
for a shard controls fixed-budget traversal and cross-shard ranking while item
vectors, assignments, centroids, sentinels, and indexes remain immutable.

MovieLens evidence is exposure-conditioned. The PoC makes no causal,
unbiased-exposure, fairness, long-term-utility, or online-engagement claim.

## End-to-end pipeline

```text
movies.dat: UTF-8 title + genres
    -> frozen local all-MiniLM-L6-v2
    -> normalized float32 item matrix E[10681,384]
    -> seeded MiniBatchKMeans centroids
    -> canonical labels + capacity-balanced greedy assignment
    -> 32 immutable IndexFlatIP shards, 334 physical slots each

selected user's A block only
    -> liked/disliked item-vector centroids
    -> fixed semantic query q_u and descriptor h_u[1153]

R target-blind basis published and hashed
    -> join R only
    -> fixed natural cross-cell preference pairs
    -> three-seed reference-free offset training
    -> checkpoints at epochs {5,10,20,40}

h_u -> centered bounded 32-way shard potential o_u
q_u, o_u -> 32 route logits -> stable top four cells
four shards -> 4 x 334 canonical FAISS scores
            -> sentinel/history mask
            -> raw or offset-adjusted stable merge
            -> exactly 100 unique unseen candidates

V candidate/score bank published before V join
    -> select one common checkpoint and one relevance comparator
    -> fixed support/power audit; failure kills before T

T routes/candidates published before sole T join
    -> FutureLikedRecall, CPE, aligned-oracle overlap, retention,
       sPCE, NDCG, Recall, intrusion, action surface, work, latency
    -> runner candidate -> post-exit independent G1-G9 replay
```

## Authenticated data and stage-isolated loading

The only allowed archive members are `ml-10M100K/ratings.dat` and
`ml-10M100K/movies.dat` from the official MovieLens 10M archive. The archive
must have exactly 65,566,137 bytes, SHA-256
`813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`,
and MD5 `ce571fd55effeba0271552578f2648bd`. `tags.dat` is forbidden.

The loader first derives per-user event counts, timestamp-group counts, and
block layouts without retaining item or rating payload. A user is structurally
eligible with 80-300 events and at least four distinct timestamp groups, after
excluding every user in the cycle-5 cohort record whose SHA-256 is
`eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126`.
Structurally eligible users are ordered by
`SHA256("20260861:{user_id}")`, then numeric user ID. An A-authorized rescan
retains the first 600 whose A block contains at least five distinct items rated
at least 4. Fewer than 600 fails closed; rejected users never enter training or
evaluation.

Within user, rows sort by `(timestamp, source_row_ordinal)`. Equal timestamps
are indivisible. Consecutive groups are allocated to A/R/V/T in proportions
60/20/10/10 by nearest cumulative event count; a cutoff tie goes to the earlier
block. Adjacent nonempty blocks require strict timestamp increase. A repeated
`(user,item)` event fails closed.

The query and descriptor are computed once from A and never updated. Only the
history mask grows: A for R, `A union R` for V, and `A union R union V` for T.
No current-stage identity or rating may affect a descriptor, route, candidate,
work allocation, membership decision, or hyperparameter before its registered
join.

## Frozen SentenceTransformer representation

In ascending numeric movie-ID order, render each movie exactly as

```text
{title} [SEP] {genres}
```

and encode it using the locally cached, frozen
`sentence-transformers/all-MiniLM-L6-v2`. The encoder runs offline and returns
contiguous, L2-normalized, 384-dimensional float32 vectors:

```text
E_i = normalize(ST(title_i + " [SEP] " + genres_i)).
```

Ratings, tags, popularity, user IDs, pairs, target labels, candidate outcomes,
and later-stage fields never enter item encoding. A previously produced matrix
may be reused only if its SHA-256 is exactly
`8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768`;
otherwise it is re-encoded before cycle-6 target access. Matrix order, shape,
dtype, finiteness, unit norms, and bytes are verified and hashed.

## Deterministic capacity-balanced FAISS shards

Partition only the frozen item matrix, before cycle-6 target access:

1. Run one-thread MiniBatchKMeans with 32 clusters, seed `20260861`, batch size
   1,024, five initializations, at most 100 iterations, and reassignment ratio
   zero under the prospectively bound scikit-learn version.
2. L2-normalize the initial centroids. Canonicalize labels by ascending SHA-256
   of canonical float32 centroid bytes, then original label.
3. Give canonical cells 0-24 capacity 334 real items and cells 25-31 capacity
   333.
4. Compute every item-centroid float32 inner product. Sort all edges by score
   descending, numeric movie ID ascending, then canonical cell ID ascending.
   Traverse once; assign an edge only when its item is unassigned and its cell
   is nonfull. Completion with the exact capacities is mandatory.
5. Recompute and L2-normalize each centroid once from its assigned real items.
   Do not reassign.
6. Add one zero-vector sentinel with a forbidden negative ID to each 333-real-
   item shard. Build one immutable `faiss.IndexFlatIP(384)` per shard.

Thus all 32 physical indexes have `ntotal=334`; 25 contain 334 real items and
seven contain 333 real items plus one filtered sentinel. Hash the initial and
final centroids, canonical-label map, assignment array, sentinel map, and every
serialized index. Recheck these hashes before and after evaluation. The final
balanced construction must pass a real-embedding, outcome-free qualification
before launch.

This is a manually routed balanced spherical partition, not ordinary
unbalanced IVF. `nprobe=4` denotes the orchestration layer's exact selection of
four distinct shard indexes.

## Fixed A-only user representation

For A ratings only, liked means rating at least 4 and disliked means rating at
most 2. Define

```text
liked_u    = normalize(mean(E_i for distinct liked A items))
disliked_u = normalize(mean(E_i for distinct disliked A items)), or zero
q_u        = normalize(liked_u - 0.25 * disliked_u)
h_u        = concat(q_u, liked_u, disliked_u, min(A_count,300)/300)
```

The five-liked-A predicate makes the 384-dimensional `q_u` well-defined.
`h_u` has 1,153 float32 values. Query, component centroids, descriptor, raw
32-cell route scores, A history, and the target-blind R basis are published and
hashed before the R item/rating join.

## Shared bounded potential and SimPO-style training

The offset network is

```text
Linear(1153,32) -> tanh -> Linear(32,32) -> tanh.
```

The last linear layer has exact-zero weights and bias at initialization. For
the final tanh output `z_u`, center and bound the potential:

```text
o_u[c] = 0.05 * (z_u[c] - mean_c z_u[c]).
```

The common shift is removed and every pairwise offset difference is at most
0.10. Item vectors, user query, centroids, assignments, and indexes receive no
gradient.

R natural pairs contain two distinct items whose rating gap is at least 2; the
higher-rated endpoint is chosen. Same-cell pairs are retained as diagnostics
but cannot update partition offsets. Cross-cell pairs are ordered by
`SHA256("20260862:{user_id}:{low_item_id}:{high_item_id}")` and capped at 64
per user. Each user's pair loss is averaged before users are averaged:

```text
s_theta(u,i) = dot(q_u,E_i) + o_u[cell(i)]
L_u = mean_pair softplus(5 * (0.05 - s_theta(u,chosen)
                                  + s_theta(u,rejected)))
L = mean_user L_u.
```

This is SimPO-style because it is a fixed-margin, reference-free preference
objective. It has no reference model, DPO reference forward pass, language
model decoding, learned item geometry, dynamic margin, or cutoff loss.

Train independent seeds `{20260861,20260862,20260863}` with Adam, learning rate
0.003, weight decay `1e-4`, gradient-norm clip 1.0, `beta=5`, and `gamma=0.05`.
Save epochs `{5,10,20,40}`. Before V is joined, publish every checkpoint and
the complete V candidate/score bank for every registered checkpoint, seed, and
method. Select one epoch for all seeds by mean V cross-cell pair accuracy over
the three seeds, breaking ties toward the earlier epoch.

The shuffled model uses identical pairs, initialization schedule, optimizer
steps, and selected epoch. Its direction is independently flipped by the fixed
hash coin `SHA256("20260863:{user_id}:{low_item_id}:{high_item_id}")`.

## Canonical retrieval and fixed work

For method-specific route flag `r` and rank flag `k`, with learned potential
`o_u`, define:

```text
route_score[c] = dot(q_u, centroid[c]) + r * o_u[c]
cells = stable_top4(route_score, key=(-score, numeric_cell_id))

rows = []
for c in cells:
    score_c, id_c = shard[c].search(q_u, 334)
    rows.extend((id, float32(score), c) for every physical slot)

rows = remove_sentinels_and_chronological_history(rows)
rows = [(id, float32(score + k * o_u[c])) for (id,score,c) in rows]
rows = stable_sort(rows, key=(-adjusted_score, numeric_movie_id))
require at least 100 unique unseen real IDs
return rows[:100]
```

Every fixed-work method searches four distinct shards and exactly 1,336
physical slots. Any four cells contain at least 1,332 real items; with at most
300 total user events, at least 1,032 real items remain unseen. Underfill,
duplicate candidates, a visible sentinel, or unequal physical work is an
integrity failure, never a backfill or retry trigger.

The route computes 32 centroid dot products, so the vector-work ledger is
exactly 32 coarse plus 1,336 shard-slot dot products: 1,368 total, or 12.81% of
the 10,681-item catalog count. MLP FLOPs, seven catalog-wide sentinel slots, and
real items in the selected shards are reported separately.

Canonical float32 FAISS scores define deployment. Stable item-ID sorting, not
FAISS return order, resolves equal canonical scores. Exhaustive aligned scoring
uses the same FAISS path over all 32 shards and adds the same offsets. A separate
matrix scorer aligns by item ID and checks only `rtol=2e-6, atol=2e-6`, plus
finite rank-100/101 margins and tolerance-defined near-tie sets. Cross-kernel
ID/order identity is neither required nor credited, and an oracle may never
replace the deployed FAISS result.

## Registered methods

The fixed order is:

```text
popularity
raw_full_exact_semantic
balanced_geometric_ivf
pivot_route_only
pivot_rerank_only
pivot_full
shuffled_pivot
aligned_full_exact
```

Methods 3-7 share item vectors, cell assignments, centroids, shard indexes,
four-probe budget, history mask, candidate quota, FAISS calls, tie rule, work
ledger, and latency harness. The factorial cells use one selected PIVOT
checkpoint: geometric `(route=0,rank=0)`, route-only `(1,0)`, rerank-only
`(0,1)`, and full `(1,1)`. Methods 2 and 8 search all 10,688 physical shard
slots and are excluded from equal-search-work and G8 latency comparisons.

Popularity uses global A-only counts and the chronological history mask. Raw
full exact uses all shards, raw query, and raw cosine. Aligned full exact uses
all shards and PIVOT-adjusted scores only to construct
`AlignedOracleTop100`.

## Target-blind validation and test barriers

Checkpoint-selection V pairs are cross-cell rating-gap-at-least-2 pairs capped
at 64 per user by
`SHA256("20260867:{user_id}:{low_item_id}:{high_item_id}")`. The distinct fixed
V estimand pairs use all unseen endpoints with rating gap at least 2, capped at
100 per user by
`SHA256("20260869:{user_id}:{low_item_id}:{high_item_id}")`; its cross-cell
subset is diagnostic only.

After the V candidate bank is durable, V may select only the common checkpoint
and the stronger NDCG@10 relevance comparator between balanced geometric IVF
and raw full exact. Freeze those choices and every model hash. Then conduct the
registered V support/power audit. Failure kills PIVOT before T and cannot alter
a choice.

Only after passing that audit may the system publish and hash every T route,
score, candidate, mask, and method artifact using the fixed A descriptor and
`A union R union V` history mask. The method-independent T pair set is joined
only afterward: distinct unseen endpoints, rating gap at least 2, at most 100
per user by
`SHA256("20260865:{user_id}:{low_item_id}:{high_item_id}")`. Pair IDs and
directions are identical across methods and seeds.

## Evaluation and decision

The fixed estimands are FutureLikedRecall@100, all-pair CPE@100,
AlignedOracleOverlap@100, RawExactRetention, sPCE@10, NDCG@10, Recall@10,
LowRatingIntrusion@10, changed route/candidate surface, work, and latency.
Metrics are user-macro. Paired intervals use 5,000 user-cluster bootstrap draws
with seed `20260864` on fixed finite common-user intersections.

The exact G1-G9 thresholds and support/power construction are specified in
`experiments/pivot-protocol-v1.md` and
`src/configs/pivot_poc_ml10m_v1.json`. They are direct encodings of the
authoritative Phase-2 gate and cannot be tuned after outcomes.

The runner may publish only a non-authoritative completion candidate. After
runner exit and lock release, a separate source-bound verifier authenticates
the recursive artifact closure and independently replays G1-G8 from raw arrays.
It alone may establish G9 and publish the authoritative marker.

```text
PROMISING = G1 and G2 and G3 and G4 and G5 and G6 and G7 and G8 and G9
```

Any exception, unsupported cohort, nonfinite value, false gate, missing
artifact or marker, or incomplete result kills PIVOT without repair or rerun,
forbids Phase 5, and returns the sprint to Phase 1.
