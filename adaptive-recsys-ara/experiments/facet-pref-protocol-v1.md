# FACET-PREF PoC v1: Preregistered Protocol

Status: outcome-blind Phase-3 protocol. This artifact and
`src/configs/facet_pref_poc_ml1m_v1.json` must be committed with the complete
runner, launcher, and verifier before any cycle-4 `V` or `T` item identity,
rating, pair, candidate outcome, or method metric is opened. The locked
`research-question-cycle4.md` is authoritative. Any disagreement that weakens
its cohort, estimand, comparator, threshold, or fail-closed rule is a protocol
failure, not an invitation to repair the run.

## Decision rule

FACET-PREF tests whether macro-balanced, SimPO-inspired reference-free
alignment of at most two facet-conditioned user queries improves preference-
pair support before retrieval and strict preference-consistent exposure after
ranking under an exact 200+200 candidate budget and immutable catalog
geometry.

The PoC is promising only when every G1-G9 condition below is true and a
source-bound post-exit verifier publishes the sole valid external completion
marker. One false gate kills FACET-PREF, prohibits Phase 5, and returns the
research sprint to Phase 1. No weighted score, manual override, threshold
change, cohort substitution, test-time source repair, partial-seed rescue, or
automatic outcome rerun is permitted.

## Authenticated data, split, and fresh cohort

- Source: official GroupLens MovieLens 1M archive at
  `https://files.grouplens.org/datasets/movielens/ml-1m.zip`.
- Required archive SHA-256:
  `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`.
- Inputs: ratings, movie title, and movie genres. Demographics are forbidden as
  inputs and selection variables; no demographic-fairness claim is made.
- Within each user, sort by `(timestamp, original_row_id)` while preserving
  equal-timestamp events as indivisible groups. Allocate chronological groups
  to `A=60%`, `R=20%`, `V=10%`, and sealed `T=10%` using the established
  deterministic splitter. Adjacent nonempty blocks must have strict group
  time order.
- Eligibility requires at least 50 events, at least four timestamp groups, at
  least 10 `A` events, at least two distinct positive `A` items, and at least
  one rating-at-least-4 item in each of `V` and `T`.
- Order eligible users by `SHA256("20260817:{user_id}")` and then numeric user
  ID. Rederive CAPER `[0:1000]`, RAVEL `[1000:2000]`, and FACET-PREF
  `[2000:4000]` manifests; require pairwise disjointness and exactly 2,000
  FACET-PREF users. Fewer than 4,000 eligible users fails closed.

The eligibility pass may disclose only membership predicates and block
offsets. It may not expose a cycle-4 `V/T` item identity, rating, pair, or
outcome. Every manifest and source file is content hashed.

## Mandatory target-blind stage order

1. Authenticate archive, extraction, interpreter, environment, protocol,
   config, source, and all three cohort manifests.
2. On `A` only, fit implicit and rating-aware BPR variants, collaborative query
   normalizers, and any global score normalizers. Encode rating-free metadata.
   Build semantic and collaborative `faiss.IndexFlatIP` indexes. Publish and
   hash all matrices and indexes.
3. From `A` prefixes, construct and publish target-blind `R` facet/query
   descriptors. Only after their durable publication may `R` ratings be joined
   to construct the common natural-pair corpus.
4. Train FACET-PREF and every aligned control from `R` only, for exactly 24
   epochs and the three registered seeds. Serve the final epoch. No `V/T`
   target selects a checkpoint or training choice.
5. From `A+R` prefixes, publish complete target-blind `V` query, candidate,
   component-score, alpha-grid ranking, and top-10 manifests for all methods.
   Join `V` relevance only. Select the BPR identity from BPR-only macro
   NDCG@10, breaking ties by macro Recall@10 and then `implicit` before
   `rating_aware`. With that BPR fixed, select one alpha for the raw
   single-centroid hybrid from `[0, .25, .5, .75, 1]` by macro NDCG@10,
   breaking ties by macro Recall@10 and then larger alpha. Freeze this BPR and
   alpha across every hybrid/control.
6. Freeze and hash all representations, adapters, indexes, budgets,
   normalizers, alpha, and tie-breaks. Open the otherwise unused fixed `V`
   preference labels only for the registered power audit. Failure kills before
   `T`; passage cannot change any choice.
7. From `A+R+V` prefixes, construct, fsync, and hash complete target-blind `T`
   query, candidate, component-score, fused-score, full-order, and top-10
   manifests. Only then join `T` exactly once and compute the fixed estimands,
   bootstrap intervals, G1-G9, and `PROMISING`.

A target is never appended to a candidate set. Any manifest timestamp or hash
showing that a target join preceded its corresponding query/candidate/ranking
publication fails G9.

## Representation and deterministic facets

Encode `"{title} [SEP] {genres}"` with the locally cached, frozen
`sentence-transformers/all-MiniLM-L6-v2` checkpoint into a float32,
L2-normalized 384-dimensional matrix. No rating enters the encoder. Hash the
matrix and immutable semantic index before training.

The BPR variants are 64-dimensional, use only `A`, and share the registered
optimizer budget in the JSON. A request query is the trained user vector plus
`0.5` times a rating-weighted aggregate of frozen item factors in the available
prefix. The validation-selected item-factor matrix and its index are immutable.

For every prefix, liked items have rating at least 4, disliked items have
rating at most 2, and rating-3 items are ignored. Use distinct liked movie IDs.
Set `F=min(2, liked_count)`. Zero liked items fails closed; one liked item gives
one facet. For two facets, initialize spherical two-means with the least-similar
liked-item pair. Cosine ties use the lexicographically smallest ordered movie-ID
pair. Assign to maximum-cosine center, breaking ties by lower canonical facet
index; update each center to its normalized member mean. Canonicalize clusters
by minimum member movie ID. Stop at assignment stability or after eight
assignment/update iterations. An empty cluster collapses to the normalized mean
of all liked items without re-seeding.

Let `E_i` be a frozen item vector and `d_u` the normalized mean of disliked
vectors, or zero if absent. A raw facet query is

```text
b_uf = normalize(mean(E_i: i in liked facet f) - 0.25 * d_u).
```

The global liked centroid, global dislike centroid, support fraction, and
prefix length `min(number_of_events,200)/200` accompany `b_uf`. No ID,
demographic, current-block item, candidate outcome, or target may enter a query.

Every aligned method uses one shared
`Linear(1154,32)-tanh-Linear(32,384)` adapter family. Its output layer is
initialized to exact zero and

```text
h_uf = [b_uf, global_like, global_dislike,
        facet_liked_count / total_liked_count,
        min(prefix_event_count,200)/200]
q_uf = normalize(b_uf + 0.25 * g(h_uf) / max(1, ||g(h_uf)||_2)).
```

Only the adapter moves; semantic and BPR item matrices and FAISS indexes remain
hash-identical.

## Fixed exact 200+200 retrieval

Every hybrid request uses one collaborative query and one batched semantic call
containing at most two facet queries. Both `IndexFlatIP` searches return a fixed
depth of 700 per query.

1. Scan the collaborative row in order, remove prefix-seen and duplicate items,
   and retain exactly 200 unique unseen items `B_u`.
2. Remove prefix-seen items, all items in `B_u`, and semantic duplicates. For
   one facet, retain its first 200 eligible items. For two facets, first fill
   canonical 100/100 quotas; a cross-row duplicate is owned by the lower
   canonical facet that first encounters it. Then scan only the unconsumed
   portions of the same returned rows in canonical round-robin order until
   exactly 200 semantic items `S_u` exist.
3. Construct `C_u` as `B_u` followed by `S_u`. Do not truncate, append, or
   re-search.

Fewer than 200 eligible items in either branch fails closed. Thus every hybrid
union has exactly 400 unique unseen items, its semantic branch is exactly 200
items and BPR-novel, and final branch overlap is zero. Log pre-exclusion overlap,
facet ownership, quota use, and duplicates, but do not expose multiplicity or
facet ownership to the ranker.

## Shared fusion and selected BPR baseline

For every hybrid union, compute the selected BPR dot product and

```text
semantic_score(u,i) = max_f dot(query_uf, E_i),
```

breaking an exact facet tie by canonical index. Independently transform each
400-score component using its request-level 5th and 95th quantiles:

```text
denom = max(Q95 - Q05, 1e-6)
z_i = clip((score_i - Q05) / denom, 0, 1).
```

All hybrids use the one validation-locked coefficient:

```text
fused_i = alpha * z_bpr_i + (1-alpha) * z_semantic_i.
```

Sort descending fused score, then ascending numeric movie ID. The selected BPR
standard baseline serves its own 200-item collaborative branch by BPR score and
movie-ID tie-break; it is the explicit exception to the 400-item hybrid union.
No method-specific alpha, score map, or tie rule is allowed.

## Common `R` corpus and reference-free alignment

After target-blind `R` descriptors are published, enumerate every unordered
pair of distinct naturally rated `R` items with absolute rating gap at least
two. The higher-rated endpoint is `chosen`. Pair endpoints are training labels,
not candidate injections. Fail before training unless the uncapped corpus has
at least 5,000 pairs from at least 1,000 pair-bearing users.

Order each user's pairs by
`SHA256("20263116:{user_id}:{low_movie_id}:{high_movie_id}")` and retain at
most 32. If the retained total exceeds 30,000, sort by within-user hash rank
and then pair hash and retain 30,000. This cap, pair IDs, natural directions,
and batch schedule are shared. Assign a pair to the raw facet closest by cosine
to the chosen item; ties use canonical facet index.

For each optimization seed in `{20260827, 20260828, 20260829}`, train every
aligned variant for 24 epochs with AdamW, learning rate `0.003`, weight decay
`0.0001`, gradient-norm clip `1.0`, and deterministic user groups of 128. The
full method uses

```text
Delta = max_f(q_uf dot E_i+) - max_f(q_uf dot E_i-)
loss  = softplus(2.0 * (0.20 - Delta)).
```

User-by-facet macro aggregation first averages preserved pairs within assigned
facet, then active facets within user, then pair-bearing users. At epoch `e`,
order users by
`SHA256("20263116:train:{seed}:{e}:{user_id}")` and numeric user ID, and split
that order into consecutive groups of 128. This is a
SimPO-inspired reference-free scalar margin objective: there is no reference
policy, reference-model pass, or language-model decoding. The final epoch is
served; early stopping and `V/T` preference checkpoint selection are forbidden.

## Registered methods and controls

1. validation-selected implicit or rating-aware BPR;
2. raw single-centroid semantic+BPR linear hybrid;
3. raw multi-facet retrieval with no learned alignment;
4. single-query aligned retrieval using the same adapter and natural pairs;
5. multi-facet zero-margin alignment, changing only margin `0.20 -> 0`;
6. multi-facet shuffled-direction alignment, hash-ordering pairs within user and
   reversing exactly even zero-based orientations;
7. multi-facet pair-micro alignment, changing only loss aggregation;
8. full FACET-PREF: multi-facet, natural directions, positive margin, and
   user-by-facet macro aggregation.

The mechanism core is `{single,multi} x {raw,aligned}`. All hybrid methods have
identical catalog vectors, indexes, selected BPR, shared alpha, quantile map,
200+200 budgets, search depth, candidate merge, fusion family, and latency
instrumentation. All aligned methods additionally share adapter capacity,
zero-output initialization, pair identities and cap, batch order, epochs,
optimizer, and seeds. Only the named factor may differ. Raw methods perform no
training by definition.

## Fixed validation preference power audit

Only after every choice is frozen may the unused fixed `V` preference cohort be
opened. Construct the same method-independent natural-pair universe used for
`T`, capped at 100 pairs per user by ascending
`SHA256("20263121:{user_id}:{low_movie_id}:{high_movie_id}")`.
For FACET-PREF versus (a) the raw single-centroid hybrid and (b) selected BPR:

1. average each user's sPCE difference over the three optimization seeds;
2. center the per-user differences and add the registered alternative
   `delta=0.005`;
3. simulate 2,000 experiments, each sampling 500 users with replacement;
4. within each experiment, estimate a two-sided 95% percentile lower bound with
   1,000 user bootstrap draws;
5. use seed `20263119` for the hybrid comparison and `20263120` for BPR.

Both comparisons require at least `0.80` probability that the lower bound is
above zero. Failure kills before `T`; passage cannot tune or replace anything.

## Sealed-test estimands

### Fixed natural pair universe

After target-blind `T` manifests are durable, form every within-user unordered
pair of naturally rated `T` items with absolute rating gap at least two. The
higher-rated endpoint is chosen. If a user has more than 100, retain 100 by
ascending
`SHA256("20263118:{user_id}:{low_movie_id}:{high_movie_id}")`. Pair identities
are method-independent. Require at least 2,000 fixed pairs and 500 pair-bearing
users.

### Natural preference-pair co-support

For a hybrid candidate union `C_u`,

```text
PairSupport(u) = mean_pairs 1[chosen in C_u and rejected in C_u].
```

This is computed before ranking and user-macro averaged. It is not conditional
on retrieval and both absent endpoints score zero.

### Strict preference-consistent exposure at 10

Let `r10(i)` be a movie's 1-based served rank when it is in the top 10, and 11
otherwise. For each fixed pair,

```text
sPCE_pair = 1.0 if r10(chosen) < r10(rejected) else 0.0.
```

Both-unshown pairs score zero; hiding only the rejected endpoint without
showing the chosen endpoint earns no credit; order changes below rank 10 earn
no credit. `sPCE@10(u)` is the user's fixed-pair mean and the primary aggregate
is user macro. Half-tie, candidate-conditional, full-union, and pair-micro
accuracies are diagnostics only.

### Relevance, exposure, and diagnostics

- binary NDCG@10 and Recall@10 against every naturally rated `T` item with
  rating at least 4;
- positive-item recall of the complete candidate union before ranking;
- low-rating intrusion@10: the fraction of top-10 items that occur in that
  user's `T` with rating at most 2; unobserved items remain unknown;
- exact union size, raw and final branch overlap, PairSupport, and fraction of
  fixed pair outcomes changed relative to each primary baseline;
- active facets, minimum facet size, quota utilization, prefix history length,
  item-popularity profile, and genre-diversity slices. Slices are descriptive
  only and cannot tune or gate a method.

MovieLens ratings are exposure-conditioned and missing-not-at-random.
PairSupport and sPCE@10 are offline observed-rating estimands, not causal
preference, counterfactual exposure, or fairness measures.

## Inference, cohorts, and latency

First average each user's outcome across optimization seeds
`{20260827,20260828,20260829}`. Then perform a paired 10,000-draw percentile
bootstrap over users at alpha `0.05` with seed `20263117`. Resample users, never
pairs or seed rows. Methods in a comparison use identical users and pair IDs;
missing or nonfinite values in a fixed cohort fail closed.

Seed-invariant raw hybrids and BPR are computed once and copied identically onto
each aligned-seed row; this is bookkeeping for paired arrays, not three
independent baseline observations.

- PairSupport and sPCE use the fixed pair-bearing cohort.
- NDCG, Recall, and positive-union recall use the fixed relevance-eligible
  cohort.
- Intrusion uses all 2,000 evaluation users and records zero for users with no
  observed low-rating item exposed.

For the G6 common-support statistic, average
`1[pair endpoints are both in C_FACET and C_hybrid]` over fixed
user-pair-seed rows. For the changed-outcome statistic, average
`1[sPCE_pair_FACET != sPCE_pair_hybrid]` over those same rows. For G7, evaluate
each seed separately with point estimates and no bootstrap rescue.

Latency is CPU-only and single-threaded. Use the first 500 FACET-PREF users in
numeric user-ID order; the first 50 are one untimed warm-up pass and remain in
the measured cohort. Use three AB/BA-interleaved repetitions per method and
seed, take each user's median first, and then p95 across users. The timed path
includes both FAISS calls, filtering, deterministic quota/backfill and merge,
feature construction and adapter inference, component scores, quantile fusion,
and final sorting. It excludes encoding, BPR/adapter training, index building,
target joins, disk I/O, and metric calculation. G8 uses the worst seed and the
identically instrumented raw single-centroid dual-index hybrid.

## G1-G9 all-or-nothing promise gate

1. **G1 - fixed-budget upstream intervention.** Every semantic method returns
   exactly 200 unique unseen BPR-novel semantic candidates, every collaborative
   branch returns exactly 200, every hybrid union has exactly 400 items, no
   query uses its current block's target, and semantic/BPR matrices and FAISS
   indexes are hash-identical before and after evaluation.
2. **G2 - material retrieval support.** FACET-PREF minus the raw
   single-centroid hybrid has user-macro PairSupport point gain at least
   `+0.020` and a paired 95% lower bound above zero. Its positive-item union
   recall point gain is at least `+0.020` and its lower bound is above zero.
3. **G3 - primary served preference gain.** FACET-PREF sPCE@10 exceeds both the
   raw single-centroid hybrid and selected BPR by at least `+0.005` absolute,
   and both paired 95% lower bounds are above zero.
4. **G4 - relevance and dislike safety.** Against the raw single-centroid
   hybrid, FACET-PREF-minus-baseline NDCG@10 has point estimate at least
   `-0.0002` and lower bound strictly above `-0.001`; Recall@10 lower bound is
   strictly above `-0.002`; and low-rating-intrusion increase upper bound is at
   most `+0.002`.
5. **G5 - facet/alignment mechanism.** FACET-PREF has strictly higher point
   PairSupport and sPCE@10 than each raw multi-facet, single-query aligned,
   zero-margin, shuffled-direction, and pair-micro control. This supports only
   the registered joint mechanism; point diagnostics do not establish component
   necessity and no PoC-scale significance claim is made for them.
6. **G6 - nondegenerate fixed support.** The `R` floor of 5,000 natural pairs
   and 1,000 pair-bearing users, the `T` floor of 2,000 fixed pairs and 500
   pair-bearing users, and both pre-`T` power audits pass. Common FACET/hybrid
   pair-endpoint co-support across fixed user-pair-seed rows is at least `0.10`,
   and the fraction with different sPCE pair outcomes is at least `0.02`.
7. **G7 - seed stability.** At least two of three seeds independently have
   positive FACET-PREF-minus-hybrid PairSupport, sPCE@10, and positive-item
   union recall, plus NDCG@10 delta at least `-0.0002`.
8. **G8 - serving budget.** Worst-seed single-thread CPU FACET-PREF p95 is at
   most `5 ms` and at most `1.25x` the identically instrumented dual-index raw
   single-centroid hybrid.
9. **G9 - provenance and external replay.** Archive, extraction, cohort,
   temporal order, target blindness, source, protocol, config, environment,
   interpreter, model, matrix, index, manifest, raw array, bootstrap,
   process-exit, lock-release, recursive artifact hash, empty stderr, and empty
   asynchronous-ledger checks all pass. A separately bound post-exit verifier
   recomputes G1-G9 from raw arrays before publishing the sole external marker.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

## Fail-closed conditions

In addition to any false gate, fail on an archive/config/protocol/source or
interpreter hash mismatch; wrong or overlapping cohort; any temporal violation;
opening a forbidden `V/T` field early; insufficient raw `R` or fixed `T`
support; a missing pair cohort; semantic or collaborative exhaustion; a
duplicate, seen item, branch overlap, wrong quota, or nonfinite score; a changed
matrix/index/model/choice; a method-specific alpha; a missing control; any
target injection; a partial-seed result; a power-audit failure; a runner or
verifier asynchronous exception; nonempty stderr; or incomplete external
verification. Scientific failure is a valid negative result and does not
authorize an outcome rerun.

## Windows-safe launch and authoritative completion

The bound launcher invokes the workspace virtual-environment Python directly
with `-B -u`. Before numerical or ML imports it sets
`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, and `BLIS_NUM_THREADS` to `1`,
sets `CUDA_VISIBLE_DEVICES=-1`, uses offline Hugging Face/Transformers mode,
sets `HF_HUB_DISABLE_PROGRESS_BARS=1`, `TQDM_DISABLE=1`, and suppresses library
progress bars at their API, not by ignoring stderr after the fact. PyTorch
intra-op and inter-op threads are 1 and all data loaders use `num_workers=0`.

The launcher creates a unique append-only run directory and persistent
stdout/stderr files, holds an outer exclusive launch lock for the entire
runner-verifier-marker chain, and starts one hidden child with file-owned logs.
The runner holds its own owner-PID lock, installs `threading.excepthook` and
`sys.unraisablehook`, and writes a fresh append-only asynchronous-error ledger.
Any ledger entry forces nonzero exit. No automatic retry is allowed.

All progress snapshots, manifests, models, raw arrays, and results are
protocol-fingerprinted, monotonically named, fsynced, append-only artifacts.
Resume is disabled for the outcome run. After raw arrays and provisional final
JSON are durable, the runner publishes exactly one no-overwrite completion
candidate binding every recursive artifact hash and declaring lock release
pending. It is not authoritative.

The outer launcher waits on the actual process handle and verifies both launcher
child PID and Python-recorded PID are dead, then verifies runner-lock release.
It launches a separately source/config/protocol-bound verifier with its own
lock and empty asynchronous ledger. The verifier recursively rehashes artifacts,
replays target-blind ordering and exact retrieval invariants, recomputes fixed
pair cohorts, bootstrap intervals, power audit, latency summaries, and G1-G9
from raw arrays, checks all process exits and lock releases, and requires clean-
run stderr to be exactly zero bytes. Only then may the launcher atomically
publish one unique
`EXTERNAL_COMPLETE_<execution_fingerprint>.json` binding every hash, log,
candidate, verifier report, final result, exit, lock release, and verdict.

A result is complete only when the outcome and verifier processes have exited,
the unique external marker exists, recursive hashes verify, both locks are
released, and every asynchronous ledger and stderr file is empty. A runner
final JSON alone cannot authorize Phase 5 or a rerun.
