# PIVOT PoC v1: Preregistered Protocol

Date: 2026-08-07

Status: outcome-blind Phase-3 protocol

Authority: `literature/research-question-cycle6.md` is the locked Phase-2 gate

## Decision and execution rule

PIVOT tests whether one bounded reference-free partition potential can improve
fixed-work semantic traversal and cross-shard ranking over a balanced geometric
baseline while preserving relevance, semantic coverage, and CPU latency.

The PoC is promising only if a source-bound post-exit verifier independently
recomputes G1-G8 from authenticated raw arrays and the launcher subsequently
publishes the sole authoritative completion marker with G9 true. A runner
candidate is never authoritative and must expose top-level `PROMISING=false`.
Any false or incomplete gate, exception, unsupported cohort, missing artifact,
nonfinite result, absent authoritative marker, or verification failure kills
PIVOT, forbids Phase 5, and returns the sprint to Phase 1. There is no outcome
rerun, resume, post-outcome repair, threshold change, cohort substitution,
partial-seed rescue, weighted rescue, or manual override.

## Data authentication and cohort

- Dataset: official GroupLens MovieLens 10M `ml-10m.zip`.
- Expected size: 65,566,137 bytes.
- Expected SHA-256:
  `813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`.
- Corroborating MD5: `ce571fd55effeba0271552578f2648bd`.
- Allowed members: `ml-10M100K/ratings.dat` and
  `ml-10M100K/movies.dat` only. `ml-10M100K/tags.dat` is forbidden.
- The cycle-5 cohort record must hash to
  `eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126`;
  every listed user is excluded before cycle-6 selection.

Extraction rejects absolute paths, parent traversal, links, duplicate members,
unexpected required-member multiplicity, and overwrite. Parse movies as UTF-8
and ratings as half-star-capable floating point. Preserve the source row ordinal.

The initial streaming pass may retain only user event counts, timestamp-group
counts, and the group layout needed for the split. It may not retain or expose
an item ID or rating payload. Structural eligibility is 80-300 events inclusive
and at least four distinct timestamp groups. After cycle-5 exclusion, order
eligible users by `SHA256("20260861:{user_id}")`, then numeric user ID.

An A-authorized rescan evaluates only whether A contains at least five distinct
items rated at least 4. Retain the first 600 passing users. Fewer than 600 fails
closed. A rejected user is never used for training or evaluation, and selection
may not inspect an R/V/T item identity, rating, positive, pair, candidate, or
metric.

Within user, sort by `(timestamp, source_row_ordinal)`. Keep equal timestamps
indivisible and allocate consecutive groups to A/R/V/T in proportions
60/20/10/10 by nearest cumulative event count, breaking a cutoff tie toward
the earlier block. Adjacent nonempty blocks require strict timestamp increase.
A repeated `(user,item)` event fails closed.

## Mandatory target-blind stage order

1. **Bind execution.** Freeze and hash the authoritative question,
   architecture, protocol, config, future runner, future launcher/verifier,
   interpreter, package versions, fixed environment, archive, and cycle-5
   exclusion record. Run outcome-free synthetic, balanced-shard, and timing
   qualifications. No one-time outcome claim exists yet.
2. **Freeze cohort and representation.** Authenticate and safely extract the
   archive. Run the structural pass, then the A-only eligibility rescan. Freeze
   exactly 600 users and their block layouts. Encode metadata or authenticate
   the registered matrix hash. Construct, serialize, qualify, and hash the 32
   balanced immutable shards. Publish A-only queries, descriptors, raw routes,
   A histories, popularity counts, and every immutable artifact.
3. **Publish R basis before R join.** With the A-only descriptor and A history
   mask, publish/fsync/hash a replay-complete target-blind R basis. Only after
   that durable hash may the selected users' R item/rating payload be joined.
   Enumerate the fixed natural R pairs and train both true-direction and
   shuffled-direction models for all seeds and checkpoints.
4. **Publish all V candidates before V join.** Using the unchanged A-only
   descriptor and `A union R` history mask, publish/fsync/hash the complete V
   route, score, candidate, work, and checkpoint bank for every registered
   method, seed, and epoch. Replacing V identities or ratings must not change
   the already durable bank.
5. **Open only registered V views.** Join V after publication. Select one
   common epoch by mean cross-cell pair accuracy across the three seeds, with
   earlier-epoch tie break. Select the stronger V NDCG@10 relevance comparator
   from balanced geometric IVF and raw full exact. Freeze both choices and all
   selected model hashes. Construct the separate fixed all-pair V estimand set.
6. **Run V support/power audit.** With all choices frozen, execute the exact G6
   centered power simulation. Any support, finiteness, or power failure kills
   PIVOT before T. Passing may not change a model, epoch, comparator, threshold,
   cohort, pair set, representation, index, or candidate.
7. **Publish T candidates before the sole T join.** Using the fixed A-only
   descriptor and `A union R union V` history mask, publish/fsync/hash every T
   route, canonical FAISS score, candidate, work ledger, and method artifact.
   Only then join T exactly once, form the fixed pair set, calculate raw metric
   arrays, bootstrap intervals, and a non-authoritative runner G1-G8 candidate.
8. **Verify after process exit.** The runner exits and releases its lock. A
   separate source-bound verifier authenticates the recursive artifact closure,
   reconstructs fixed pair IDs and rankings, and independently recomputes G1-G8.
   After verifier exit and lock release, only the launcher may atomically
   publish the authoritative external marker that establishes G9.

Current-stage identities or ratings may not affect descriptors, routes,
candidates, work, cohort selection, or hyperparameters before the registered
join. A target is never appended, force-included, or used to choose a shard.

## SentenceTransformer representation

Render every movie in ascending numeric movie-ID order as

```text
{title} [SEP] {genres}
```

and encode with local-only frozen
`sentence-transformers/all-MiniLM-L6-v2`, producing contiguous normalized
float32 `E[10681,384]`. Ratings, tags, popularity, user IDs, pairs, candidate
outcomes, and current-stage targets are prohibited encoder inputs. Reuse is
allowed only for matrix SHA-256
`8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768`;
otherwise re-encode before target access.

From A only:

```text
liked_u    = normalize(mean(E_i for distinct A items rated >= 4))
disliked_u = normalize(mean(E_i for distinct A items rated <= 2)), or zero
q_u        = normalize(liked_u - 0.25 * disliked_u)
h_u        = concat(q_u, liked_u, disliked_u, min(A_count,300)/300)
```

`q_u`, `liked_u`, and `disliked_u` are 384-dimensional; `h_u` is 1,153-
dimensional. The query/descriptor stays fixed across R, V, and T. Only the
chronological history exclusion mask grows.

## Capacity-balanced FAISS construction

Before cycle-6 target access:

1. Run one-thread MiniBatchKMeans with 32 clusters, seed `20260861`, batch size
   1,024, `n_init=5`, `max_iter=100`, and `reassignment_ratio=0` under
   scikit-learn `1.8.0`.
2. Normalize initial centroids and canonicalize labels by ascending SHA-256 of
   canonical float32 centroid bytes, then original label.
3. Set real-item capacities to 334 for canonical cells 0-24 and 333 for cells
   25-31.
4. Sort every item-cell edge by descending float32 inner product, numeric movie
   ID, then canonical cell ID. Greedily accept an edge only if the item is
   unassigned and the cell is nonfull. Require all capacities exactly filled.
5. Recompute and normalize centroids once without reassignment.
6. Add one zero-vector forbidden-negative-ID sentinel to each 333-real-item
   shard and build one immutable `faiss.IndexFlatIP(384)` for each cell.

Require 32 nonempty cells, 334 physical slots per shard, 10,681 real items
assigned exactly once, seven filtered sentinels, finite normalized centroids,
and unchanged assignment/centroid/sentinel/index hashes before and after the
run. Repeat the balanced construction in an outcome-free qualification and
require identical hashes before authorization.

## PIVOT potential and reference-free training

The network is

```text
Linear(1153,32) -> tanh -> Linear(32,32) -> tanh.
```

Initialize the last linear layer weight and bias to exact zero. If the final
tanh output is `z_u`, use

```text
o_u = 0.05 * (z_u - mean(z_u)).
route(u,c) = dot(q_u, centroid_c) + o_u[c]
score(u,i) = dot(q_u, E_i) + o_u[cell(i)].
```

Natural R pairs have distinct endpoints and rating gap at least 2; the
higher-rated endpoint is chosen. Keep same-cell pairs for diagnostics but
exclude their zero-gradient contribution from optimization. Order cross-cell
pairs by `SHA256("20260862:{user_id}:{low_item_id}:{high_item_id}")` and cap at
64 per user. Average pair losses within user, then users:

```text
softplus(beta * (gamma - score(u,chosen) + score(u,rejected)))
```

Use `beta=5`, `gamma=0.05`, Adam, learning rate 0.003, weight decay `1e-4`,
gradient-norm clip 1.0, seeds `{20260861,20260862,20260863}`, and checkpoints
at epochs `{5,10,20,40}`. There is no reference model, query update, item
update, dynamic margin, early target access, or online LLM.

The shuffled-direction model uses the same pair IDs and caps, initialization
schedule, optimizer steps, checkpoints, and selected epoch. Interpret
`SHA256("20260863:{user_id}:{low_item_id}:{high_item_id}")` as one big-endian
integer and independently flip the canonical pair direction exactly when that
integer's least-significant bit is one.

Checkpoint-selection V pairs are cross-cell pairs with rating gap at least 2,
capped at 64 per user by
`SHA256("20260867:{user_id}:{low_item_id}:{high_item_id}")`. Select one common
epoch by mean pair accuracy across all three seeds, then earlier epoch. The
fixed V estimand set instead uses all distinct unseen V endpoint pairs with gap
at least 2, capped at 100 per user by
`SHA256("20260869:{user_id}:{low_item_id}:{high_item_id}")`.

## Canonical fixed-work retrieval

For fixed-work methods 3-7:

```text
route_logits = q_u @ centroids.T + route_flag * o_u
cells = first 4 after stable sort (-route_logit, numeric_cell_id)

rows = concatenate(
    shard[c].search(q_u, 334) for c in cells
)
remove sentinel IDs and chronological prefix IDs
adjusted_score = canonical_float32_faiss_score + rank_flag * o_u[cell]
stable sort by (-adjusted_score, numeric_movie_id)
return exactly first 100 unique unseen real items
```

Each method must use exactly four distinct cells, four complete-shard searches,
1,336 physical shard-slot dot products, 32 coarse dot products, and exactly 100
unique unseen outputs. There is no adaptive depth, backfill, retry, fallback,
target injection, or shard exchange. The work ledger reports 1,368 vector dot
products, 12.81% of the real catalog count, plus MLP FLOPs and sentinel/real
slot counts separately.

Canonical FAISS float32 scores define deployment. Equal canonical scores sort
by numeric movie ID. Exhaustive aligned scoring searches all 32 shards through
the same FAISS path and produces `AlignedOracleTop100`. The independent matrix
oracle aligns scores by item ID and requires `rtol=2e-6, atol=2e-6`; it reports
rank-100/101 margins and tolerance-defined near-tie sets. Exact ID/order
identity across numerical kernels is not a gate, and matrix results cannot
replace FAISS outputs.

## Registered methods and controls

1. `popularity`: prefix-unseen global A-only item popularity.
2. `raw_full_exact_semantic`: all 32 shards, raw query and cosine score.
3. `balanced_geometric_ivf`: geometric four-cell route and raw ranking; primary
   equal-shard-search-work baseline.
4. `pivot_route_only`: PIVOT route and raw ranking.
5. `pivot_rerank_only`: geometric route and PIVOT-adjusted ranking.
6. `pivot_full`: PIVOT route and PIVOT-adjusted ranking.
7. `shuffled_pivot`: full mechanism trained with registered hash-randomized
   directions.
8. `aligned_full_exact`: all 32 shards with PIVOT-adjusted ranking, used only
   for aligned-oracle overlap.

Methods 3-7 share vectors, shards, indexes, history, four-probe budget,
candidate quota, calls, tie semantics, work accounting, and latency harness.
The four factorial cells use the same selected PIVOT checkpoint. Methods 2 and
8 scan all 10,688 physical slots and do not enter equal-work or G8 comparisons.

## Fixed estimands

Before T ratings are joined, publish every method's candidate IDs and scores.
A T item is relevant when rating is at least 4. Construct method-independent
T pairs from distinct unseen endpoints with rating gap at least 2, cap at 100
per user by
`SHA256("20260865:{user_id}:{low_item_id}:{high_item_id}")`, and use identical
pair IDs and directions across methods and seeds.

- `FutureLikedRecall@100`: per-user fraction of unique relevant T items among
  the 100 candidates.
- `CPE@100`: per-user pair mean of
  `1[chosen in C] - 1[rejected in C]`. Both-in and neither-in are zero. All
  fixed pairs are primary; cross-cell-only is diagnostic.
- `AlignedOracleOverlap@100`: PIVOT/aligned-exhaustive top-100 set intersection
  divided by 100.
- `RawExactRetention`: PIVOT FutureLikedRecall divided by raw-full-exact
  FutureLikedRecall. Report denominator and supported users; zero aggregate
  support fails closed.
- `sPCE@10`: one only if the chosen endpoint has strictly better served top-10
  rank; unshown endpoints have rank 11.
- `NDCG@10` and `Recall@10`: binary relevance over observed T items.
- `LowRatingIntrusion@10`: count of top-10 items observed in T with rating at
  most 2, divided by 10. Unobserved items remain unknown.
- Changed surface: route-set difference, candidate-set difference, mean
  candidate Jaccard distance, and fixed-pair endpoint-membership XOR.
- Work/latency: coarse and shard-slot dots, real/sentinel slots, MLP FLOPs, and
  single-thread batch-1 distributions.

All metrics are user-macro. Paired intervals use 5,000 user-cluster bootstrap
draws with seed `20260864`, fixed finite common-user intersections, and explicit
missing-user/sample counts. Average all three optimization seeds within user
before the primary G2 bootstrap.

## Locked all-or-nothing gate

### G1 - construction and provenance

Require exactly 600 fresh users; 32 immutable balanced cells; 334 physical
slots per shard; 10,681 real items assigned once; seven correctly filtered
sentinels; unchanged source, archive, vector, assignment, centroid, sentinel,
and index hashes; correct stage barriers; finite canonical scores; all three
seeds; and a complete recursive artifact inventory. Every fixed-work method
must use four distinct probes, exactly 1,336 searched shard slots, and exactly
100 unique unseen real candidates.

### G2 - material equal-search-work gain

After averaging all three seeds within user, `pivot_full -
balanced_geometric_ivf` must be at least +0.010 for both
FutureLikedRecall@100 and CPE@100. Both paired 95% user-bootstrap lower bounds
must be above zero on fixed common-user denominators.

### G3 - shared-mechanism evidence

Geometric `(0,0)`, route-only `(1,0)`, rerank-only `(0,1)`, and full `(1,1)`
must use the same selected PIVOT checkpoint. Full PIVOT must exceed each
single-use control by at least +0.002 on both primary metrics, with every paired
lower bound above zero. Its CPE gain over shuffled PIVOT must be at least +0.010
with lower bound above zero.

### G4 - routing fidelity and semantic retention

Mean AlignedOracleOverlap@100 must be at least 0.90. PIVOT
FutureLikedRecall@100 must be at least 95% of raw full exact. Score-error and
near-tie diagnostics must be finite and complete. Cross-kernel ID/order equality
is neither required nor credited.

### G5 - served relevance and preference safety

Before T, V selects the stronger NDCG@10 comparator from balanced geometric IVF
and raw full exact, breaking an exact NDCG tie toward balanced geometric IVF.
Against that fixed comparator, PIVOT T NDCG@10 point delta
must be at least -0.002 with lower bound above -0.005; Recall@10 point delta at
least -0.005 with lower bound above -0.010; and sPCE@10 point delta nonnegative.
Against balanced geometric IVF, the paired upper bound on
LowRatingIntrusion@10 increase must be at most +0.002.

### G6 - support, power, and action surface

- R: at least 5,000 cross-cell pairs from at least 400 users.
- V: relevant endpoints for at least 400 users and at least 1,500 fixed pairs
  from at least 300 users.
- T: relevant endpoints for at least 400 users and at least 1,500 fixed pairs
  from at least 300 users.
- Form finite common-user, three-seed-averaged PIVOT-minus-geometric V vectors
  for both primary metrics after checkpoint/comparator freeze but before T.
  Subtract each vector's finite mean and add +0.010 without clipping. With seed
  `20260866`, perform 500 outer user resamples; within each, perform the
  registered 500-draw paired bootstrap. Detection means the inner 2.5th
  percentile is above zero. Detection must be at least 80% for each metric.
  CPE uses the fixed all-pair V estimand, not checkpoint-selection pairs.
- Across all seed-by-user rows, at least 10% of PIVOT four-cell sets differ from
  geometric. Across every seed-by-endpoint row from unique fixed-T-pair endpoint
  IDs, candidate-membership XOR must be one on at least 5%.

Any empty, nonfinite, or unsupported cohort kills. A V support or power failure
kills before T.

### G7 - seed stability without rescue

All three seeds complete and enter the seed-averaged primary statistic. At
least two seeds individually have positive PIVOT-over-geometric deltas for both
primary metrics. No seed may have a negative delta on either primary metric or
an NDCG@10 delta below -0.005 versus the fixed stronger relevance comparator.

### G8 - serving cost

Every fixed-work method performs exactly 32 coarse and 1,336 shard-slot dot
products. Select exactly 512 requests by ascending
`SHA256("20260868:{user_id}")`, then numeric user ID. Use one pinned CPU core,
one FAISS/Torch/BLAS thread, 32 warmups, and seven repetitions numbered 0-6.
Even repetitions execute geometric then PIVOT; odd repetitions execute PIVOT
then geometric, each in the deterministic request order. Reduce to a median for
each request, then compute p95 with NumPy quantile `method="linear"`; evaluate
the worst PIVOT seed. PIVOT p95 must be at most 3 ms and at most 1.5 times
balanced-geometric p95.

Timing includes A descriptor/query construction, uncached per-test-user offset
inference, 32 coarse scores, four complete-shard searches, sentinel/history
masking, merge, and stable top-100. It excludes training, metadata encoding,
index construction, disk I/O, and target/metric joining. Record hardware,
interpreter, package versions, affinity, numerical thread settings, power
metadata, and peak RSS. The current pre-outcome machine is bound; an
outcome-free timing qualification must pass before authorization.

### G9 - falsification authority

The runner publishes only a non-authoritative candidate with top-level
`PROMISING=false`. After runner exit and lock release, a separate source-bound
verifier authenticates raw arrays and the recursive artifact closure and
independently replays G1-G8 from fixed pair IDs. Only after verifier completion
and lock release may the launcher publish the sole authoritative external
marker. Exactly one such marker may exist. Its authoritative `PROMISING` value
is the conjunction of independently verified G1-G8 and G9 integrity.

```text
PROMISING = G1 and G2 and G3 and G4 and G5 and G6 and G7 and G8 and G9
```

## Runner, verifier, and launcher artifact contract

All JSON uses UTF-8, sorted keys, compact separators, finite numbers only, and
atomic create-without-overwrite followed by fsync. Every artifact has `schema`,
`run_id`, `execution_fingerprint_sha256`, and `self_sha256` or appears in a
parent hash inventory that authenticates its exact bytes. Raw arrays use
non-pickle formats with explicit dtype, shape, byte order, row-key schema, and
SHA-256 sidecars.

The runner-owned run directory must contain at least:

```text
RUN_STARTED.json                         schema pivot-run-started-v1
environment.json                         schema pivot-environment-v1
source_inventory.json                    schema pivot-source-inventory-v1
archive_and_extraction.json              schema pivot-archive-v1
cohort_and_layout.json                   schema pivot-cohort-layout-v1
representation_and_shards.json           schema pivot-representation-v1
stage_A_manifest.json                     schema pivot-stage-a-v1
stage_R_basis_manifest.json               schema pivot-stage-r-basis-v1
training_manifest.json                    schema pivot-training-v1
stage_V_candidate_bank_manifest.json      schema pivot-stage-v-bank-v1
frozen_choices.json                       schema pivot-frozen-choices-v1
power_audit.json                          schema pivot-power-audit-v1
stage_T_candidate_bank_manifest.json      schema pivot-stage-t-bank-v1
raw_metric_arrays_manifest.json           schema pivot-raw-arrays-v1
latency_raw_manifest.json                 schema pivot-latency-raw-v1
runner_completion_candidate.json          schema pivot-runner-candidate-v1
runner_recursive_inventory.json           schema pivot-runner-inventory-v1
```

The runner completion candidate contains raw producer-side `G1`-`G8` booleans
and details, `candidate_all_G1_G8`, `external_G9=false`, and top-level
`PROMISING=false`. It cannot contain or predict an authoritative success marker.

After runner exit, the verifier writes
`PIVOT_VERIFIER_REPORT_<execution_fp16>.json` with schema
`pivot-verifier-report-v1`. It records authenticated source/environment/archive
hashes, reconstructed pair and metric row keys, independently recomputed metric
values/intervals, independent `G1`-`G8` booleans/details, producer/verifier
comparisons, recursive-closure checks, lock/process checks, stderr/error-ledger
checks, and `verifier_passed`. It is not itself the authoritative completion
marker and cannot be written by the runner.

Only the outer launcher, after successful verifier exit and lock release, may
atomically create exactly one
`PIVOT_EXTERNAL_COMPLETE_<execution_fp16>.json` with schema
`pivot-external-complete-v1`. It binds the launcher digest authorization, claim,
launch record, source inventory, runner candidate, verifier report, full
recursive inventory, `G1`-`G9`, and authoritative `PROMISING`. If verification
fails, the launcher may write a separately named external failure record, but
must not create a completion marker.

## One-time authorization template

Preflight and self-tests never create the one-time claim. The exact launcher
bytes must be frozen and SHA-256 hashed first. The authorized launch supplies
that lowercase digest explicitly; the launcher atomically creates a persistent
`PIVOT_ONE_TIME_LAUNCH_CLAIM.json` before outcome access and refuses any second
claim, existing run directory, resume, or overwrite.

```powershell
& '<PYTHON_EXE>' -B -u '<WORKSPACE>\adaptive-recsys-ara\src\launch_pivot_and_verify.py' `
  --authorized-launcher-sha256 <64_LOWERCASE_HEX_SHA256> `
  --config '<WORKSPACE>\adaptive-recsys-ara\src\configs\pivot_poc_ml10m_v1.json' `
  --protocol '<WORKSPACE>\adaptive-recsys-ara\experiments\pivot-protocol-v1.md' `
  --output-root '<EXTERNAL_OUTPUT_ROOT>' `
  --local-dataset-archive '<WORKSPACE>\adaptive-recsys-ara\data\ml-10m-cycle5\ml-10m.zip' `
  --run-id '<FRESH_PIVOT_RUN_ID>'
```

Before authorization, replace every placeholder once and record the resulting
single-line command, exact launcher digest, fresh run ID, absent run directory,
absent claim path, source hashes, and outcome-free qualification results in a
committed pre-outcome audit. The CLI digest must equal the claim, launch record,
source inventory, verifier expectation, and current launcher-file digest.
