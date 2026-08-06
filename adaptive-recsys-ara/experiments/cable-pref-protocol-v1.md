# CABLE-PREF PoC v1: Preregistered Protocol

Date: 2026-08-07  
Status: outcome-blind Phase-3 protocol  
Authority: `literature/research-question-cycle5.md` is the fixed Phase-2 gate

## Decision and execution rule

CABLE-PREF tests whether an action-consistent, reference-free semantic-query
loss can move naturally preferred items across the deployed semantic branch
cutoff under an exact, exclusion-safe 200+200 candidate contract.

The PoC is promising only if a source-bound post-exit verifier independently
replays raw evidence and marks every G1-G9 condition true. The runner is never
authoritative and must publish top-level `PROMISING=false`. Its stored G9 bit
denotes only a completed producer-side handoff; it cannot establish external
G9, which exists only in the verifier report and completion marker. One false or
incomplete gate kills CABLE-PREF, forbids Phase 5, and returns the sprint to
Phase 1. No automatic outcome rerun, post-outcome repair, threshold change,
cohort substitution, partial-seed rescue, or manual override is permitted.

## Data and cohort binding

- Archive: official GroupLens `ml-10m.zip`.
- Bytes: `65,566,137`.
- SHA-256:
  `813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`.
- Corroborating official MD5: `ce571fd55effeba0271552578f2648bd`.
- Parse `movies.dat` as UTF-8 and `ratings.dat` ratings as half-star floats.
- Allow only title, genres, rating, timestamp, and anonymized user/item IDs.
  `tags.dat` is forbidden.
- Use one per-user structural pass, then an `A`-authorized eligibility/value
  rescan over structurally eligible users. That rescan applies the `A`-only
  predicate, retains `A` values only for the hash-top-2,000 reservoir, and
  thereby freezes the final cohort. Later stage-authorized streaming rescans
  join `R`, the binary-relevance `V` view, the later exact-`V` preference view,
  and `T` for selected users only. Every rescan verifies the frozen layout.
  Loading all 10M rows as Python objects or parsing a future stage early is
  prohibited.

Within user, sort `(timestamp, source_row_ordinal)` and keep equal-timestamp
events indivisible. Choose the `A`, then `R`, then `V` nearest cumulative cuts
sequentially subject to leaving one nonempty timestamp group for each later
block; break equal-distance choices toward the earlier group. Require four
nonempty blocks and strict timestamp separation between adjacent blocks. The
source must be user-grouped; the parser verifies that a closed user ID never
reappears.

Eligibility may use counts, timestamps, semantic-catalog size, and `A` only:

- at least 80 total events and four timestamp groups;
- at least 20 `A` events;
- at least five distinct `A` items rated at least 4;
- the count-only lower bound
  `|C_sem|-(|A|+|R|+|V|) >= 700`, without reading later item identities.

It may not use an `R/V/T` item identity, rating, positive count, preference
pair, candidate, or metric. Order eligible users by
`SHA256("20260835:{user_id}")`, then numeric ID, and retain exactly 2,000.
Fewer than 2,000 is a pre-outcome failure.

The semantic catalog is every item with allowed metadata. The collaborative
catalog is frozen from cohort `A` and includes items with at least five
positive (`rating >= 4`) `A` interactions. Before scoring a request, require at
least 200 prefix-unseen collaborative items and at least 500 items in the
semantic complement. A shortfall fails before current-block target access.

## Mandatory target-blind stage order

1. Authenticate archive bytes/digests, path-safe extraction, source, config,
   protocol, interpreter, environment, and an outcome-free synthetic test
   record. Derive structural layouts, apply the `A`-only eligibility rescan,
   and publish the final cohort/block-layout manifest without exposing
   forbidden `R/V/T` fields.
2. Encode movie metadata. From `A` only, fit the single registered implicit
   BPR-MF model, construct every frozen query descriptor needed for the `R`
   stage, build both immutable FAISS indexes, and publish/hash all matrices,
   indexes, BPR factors, masks, and descriptors.
3. Publish the replay-complete target-blind `R` basis: BPR branches, semantic
   domains reconstructible from history plus BPR IDs, raw queries,
   endpoint-independent cutoff identities/scores. Joined only in replay with
   the already durable immutable artifacts and source-bound tie rule, this is
   the complete closure basis. Only after its durable hash exists may `R`
   ratings/items be joined to enumerate the common natural-pair corpus.
4. Train every aligned control from that one `R` corpus, for the registered 12
   epochs and three seeds. Serve the final epoch only. No validation target
   selects a checkpoint, loss weight, margin, or method.
5. From `A+R` prefixes, publish the full target-blind `V` replay basis for every
   method/seed: histories, BPR/semantic queries, candidates, raw component
   scores. Together with the already durable immutable artifacts and
   source-bound alpha grid/tie rule, these form the closure basis from which the
   verifier reconstructs every alpha-grid ranking and top-10 list.
   Join `V` relevance only and select one alpha for the raw hybrid by macro
   NDCG@10, then macro Recall@10, then larger alpha. Share it across all
   hybrids. Select the stronger relevance comparator between raw hybrid and
   BPR by the same relevance ordering.
6. Freeze/hash alpha, comparator, adapters, representations, indexes, budgets,
   and all choices. Open fixed `V` preference labels only for the registered
   centered support/power audit. Failure terminates before `T`; passage cannot
   change any choice.
7. From `A+R+V` prefixes, publish/fsync/hash the complete target-blind `T`
   replay basis: histories, queries, BPR branches, candidates, raw component
   scores. Together with the already durable immutable artifacts, source-bound
   tie rule, and separate pre-`T` frozen-choice artifact, these form the closure
   basis. Fused scores, full rankings, and top-10 lists are deterministically
   reconstructed and verified rather than duplicated. Only then join `T`
   exactly once, compute raw arrays, bootstrap intervals and runner-candidate
   G1-G9, and exit.
8. After runner exit and lock release, a separate source-bound process must
   authenticate the full artifact closure and independently replay G1-G9 before
   authorizing the launcher to publish exactly one
   `run_directory/CABLE_EXTERNAL_COMPLETE_<execution_fp16>.json` with schema
   `cable-pref-external-complete-v1`. Runner and verifier cannot publish it.

Replacing current-block item/rating fields with arbitrary values must leave the
already published candidate and ranking manifest byte-identical. A target is
never appended, force-included, or used to choose search work.

## Representation

Encode

```text
"{title} [SEP] {genres}"
```

with the frozen local
`sentence-transformers/all-MiniLM-L6-v2` checkpoint. Produce contiguous
float32, L2-normalized 384-dimensional vectors `E_i`. Ratings, tags, user IDs,
candidate outcomes, and current-block targets never enter the encoder. Build an
immutable `faiss.IndexFlatIP` over `E` and hash both matrix and serialized index
before adapter training.

The raw user semantic query is

```text
l_u = normalize(mean(E_liked))
d_u = normalize(mean(E_disliked)), or zero
q0_u = normalize(l_u - 0.25 * d_u),
```

where liked means prefix rating at least 4 and disliked means at most 2. A
missing dislike centroid is zero. Query features concatenate `q0`, liked
centroid, dislike centroid, and prefix length capped at 500 then divided by
500 (1,153 total inputs). A shared `linear -> tanh -> linear` adapter has hidden size 32 and an
exact-zero output layer at initialization. Its normalized displacement from
`q0` is bounded by 0.25. Every served query and item vector is unit normalized;
query-norm inflation cannot satisfy the loss.

## Collaborative anchor

Fit one 64-dimensional implicit BPR-MF model on `A` positives (`rating >= 4`)
with uniformly sampled unseen negatives from the collaborative catalog.
Deterministically hash-sort A-positive `(user,item)` rows and retain the first
200,000; use that fixed corpus in all 8 epochs, batches of 2,048, normal
`std=0.05` initialization, AdamW learning rate 0.025, weight decay `1e-4`,
gradient clip 5.0, and seed `20260835`. No `R/V/T` label is used. At request
time the trained user factor **is** updated by 0.5 times the absolute-weight-
normalized mean of supported prefix factors with weight
`clip((rating-3)/2,-1,1)`; item factors and their `IndexFlatIP` never change.

## Exact complement retrieval

For prefix history `H_u`:

```text
B_u = ExactMaskedTopK(BPR_score(u), domain=C_cf \\ H_u, k=200)
D_u = C_sem \\ (H_u union B_u)
S_u = ExactMaskedTopK(q_u dot E, domain=D_u, k=200)
C_u = B_u concatenated with S_u
```

The main path asks each `IndexFlatIP` for its complete row, removes the exact
mask, and reorders by `(score descending, numeric movie ID ascending)` before
taking 200. It performs no depth retry or target-dependent work. An independent
oracle computes float32 dense matrix scores, applies the same mask, and
stable-sorts the complete catalog. Every selected ID and order must agree;
corresponding scores use `rtol=2e-6, atol=2e-6`, but tolerance can never rescue
an ID/order mismatch. Thus exact masked search is
the correctness foundation; it is not claimed as an ANN invention.

Every semantic control uses byte-identical `B_u` and `D_u`. The branches are
disjoint by construction and every eligible union has exactly 400 unique unseen
items. Work (complete score rows) is reported separately from output count.

## Endpoint-leave-out alignment

For an `R` natural pair `(i+, i-)`, retain the rejected endpoint in the deployed
domain and define

```text
t_u^(-i+) = score of the 200th item in D_u \\ {i+}
L_admit = 1[i+ in D_u] * softplus(5 * (t_u^(-i+) + 0.02 - score(i+)))
L_order = softplus(5 * (0.10 - score(i+) + score(i-)))
L_CABLE = 0.5 * macro_normalize(L_admit) + 0.5 * macro_normalize(L_order)
```

The target cutoff is detached from gradient computation but recomputed from the
current adapter query. With the deployed deterministic tie key, the endpoint
membership equivalence is synthetically and empirically replayed. Admission
first deduplicates active preferred endpoints within user after the pair cap;
order retains every fixed pair. Each term averages within user and then users.
The objective uses no reference
policy, reference-model forward pass, DPO partition function, or online LLM
decoding; it is a query-ranking adaptation of SimPO's reference-free principle.

Natural `R` pairs have rating gap at least 2.0. Cap 32 per user by hash and
30,000 globally with round-aware user interleaving. Require at least 20,000 raw
pairs from 1,000 users. Train 12 epochs with AdamW, learning rate 0.003, weight
decay 0.0001, gradient clipping 1.0, user groups of 128, seeds
`{20260835,20260836,20260837}`, final epoch only, and no early stopping.

## Methods and controls

The exact registered order is:

```text
bpr
raw_hybrid
order_only
admission_only
cable_pref
shuffled_direction
uib_boundary
wrong_boundary
```

- `order_only` removes only `L_admit`.
- `admission_only` removes only `L_order`.
- `shuffled_direction` reverses every even hash-ordered pair orientation within
  user but preserves pair IDs and all other computation. Its admission-active
  endpoint set is deduplicated only after this orientation change.
- `uib_boundary` replaces the nonparametric order statistic with a learned
  user-context scalar. Its admission term equally averages preferred-above and
  rejected-below softplus penalties, then combines that term 0.5/0.5 with the
  same `L_order` as CABLE.
- `wrong_boundary` computes the leave-one-endpoint top-200 cutoff after history
  exclusion but before removing `B_u`.

Trainable controls match pair corpus, optimizer steps, features, hidden width,
initialization family, clipping, seeds, epoch count, and checkpoint policy.
Boundary and order terms are separately macro-normalized to prevent a larger
raw gradient budget from explaining the full method.

## Ranking and validation lock

For every union item, compute raw BPR and method-specific semantic scores.
Normalize each component per request with NumPy `linear`-interpolated
5th/95th-percentile affine scaling and a `1e-6` scale floor, clip to `[0,1]`,
and rank by

```text
alpha * normalized_BPR + (1-alpha) * normalized_semantic.
```

Choose alpha from `[0, .25, .5, .75, 1]` using only raw-hybrid `V` NDCG@10,
then Recall@10, then larger alpha. Apply it to every hybrid/control. BPR ranks
its shared top-200 by raw BPR score. Final ties use numeric movie ID ascending.

## Fixed outcomes and inference

For each joined stage, enumerate all within-user unordered naturally rated item
pairs with rating gap at least 2.0 and higher rating preferred. `R` uses 32 per
user then the round-aware 30,000 global cap; `V/T` use 100 per user. The hash
uses ascending numeric movie IDs, and identity is `(stage,user,low_id,high_id)`.
Repeated user/movie rows fail closed. Pair IDs are method- and seed-independent.

The primary admission universe deduplicates preferred `T` endpoints per user,
then fixes the BPR-missed subset before any semantic comparison. Report both
conditional Admission@200 and unconditional NetNewPreferredSupport. Also report
net preferred-minus-rejected admission, preferred top-10 exposure, sPCE@10,
NDCG@10, Recall@10, and low-rating intrusion. The raw closure also records
fixed-pair and missed-endpoint support, admission/sPCE changed-surface counts,
leave-out tie counts, history counts, semantic-complement counts, and the
metric-specific NaN denominators needed for independent exclusion replay.

Strict sPCE@10 assigns one only when the preferred endpoint's served rank is
strictly better than the rejected endpoint's, treating an unshown item as rank
11. Both absent scores zero. NDCG@10/Recall@10 use naturally rated positives
(`>=4`), omit only that metric's users with zero positives, and use binary IDCG
through `min(10, positive_count)`. Intrusion is the count of naturally observed
ratings `<=2` in the served top 10 divided by 10. Preferred exposure averages
the fixed deduplicated preferred endpoints. Every paired comparison uses the
finite common-user intersection fixed by that metric.

Average optimization seeds within user, then use a paired 10,000-draw
user-cluster two-sided percentile interval (2.5th/97.5th percentiles) with seed
`20263504`. Resample users, never endpoints/pairs. The V power procedure is the
explicit 1,000-outer by 1,000-inner centered, unclipped common-user algorithm
defined in the Phase-2 artifact; it is not governed by the final 10,000 draws.

## Conjunctive G1-G9 gate

The exact thresholds and comparisons in
`literature/research-question-cycle5.md` are incorporated by reference and may
not be weakened. In summary:

1. G1: the shared BPR branch is exact 200; every hybrid has exact/replayed
   200+200 feasibility, leave-out action consistency, and immutable geometry.
2. G2: conditional admission gains `+0.020` vs raw and `+0.010` vs order-only,
   unconditional net-new support gain `+0.010` vs raw, positive lower bounds,
   and improved net admission advantage.
3. G3: sPCE@10 gain `+0.005` vs raw and BPR with positive lower bounds, plus
   positive preferred top-10 exposure gain.
4. G4: NDCG point `>=-0.0002`, NDCG lower bound `>-0.001`, Recall lower bound
   `>-0.002`, and intrusion upper bound `<=+0.002` against the registered
   comparators.
5. G5: full-method point dominance over every named matched mechanism control.
6. G6: registered R/T support; 5% admission-change and 2% sPCE-change fractions
   micro-aggregated over fixed user-endpoint-seed and user-pair-seed rows; and
   80% centered V power for the registered effects.
7. G7: all seeds complete, at least two directionally stable versus raw, and no
   seed's CABLE-minus-raw NDCG delta below `-0.001`.
8. G8: worst-seed single-thread p95 `<=10 ms` and `<=1.25x` raw.
9. G9: complete provenance and independent external replay.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

## Latency protocol

Select 512 users by ascending `SHA256("20263509:latency:{user_id}")`. Use one
resident CPU thread, 32 warm-up requests per method and seed, seven repetitions
per request, and method order `(raw,cable)` when
`(user_row+repetition+seed_row)` is even and reversed otherwise. Reduce to each
request's median before p50/p95/p99. Include
query/adapter construction, both complete FAISS score paths, masks, complement,
stable top-k, fusion, and sorting. Exclude encoding, training, index building,
disk I/O, target joins, and metric computation. Record CPU model, logical-core
count, process affinity, Python/FAISS/BLAS versions, and power-policy-visible
metadata; the preselected current machine is authoritative and may not be
changed after an outcome. Report vectors scored, bytes read, and peak resident
memory. Batched throughput is diagnostic only.

## Required outcome-free property tests

Before authorization, synthetic tests must prove:

1. a ranking whose first 501 rows are seen still yields exact unseen top-200;
2. 200 prefix-unseen collaborative items plus a semantic complement of 500
   succeeds, while either 199 collaborative or 499 semantic items fails before
   target access;
3. future/seen targets are masked even when highest scoring;
4. a repeated source user/movie row fails before request construction;
5. branch disjointness and union length 400;
6. full-row FAISS output plus tie rerank equals dense stable-sort oracle;
7. random, boundary-tied, and all-equal scores obey numeric-ID ties;
8. a registered batch of 64 queries plus a one-query tail is identical to 65
   independent single-query FAISS/matrix-oracle results;
9. leave-one-preferred-out cutoff exactly predicts top-200 membership;
10. current-block target poisoning leaves the complete pre-join `R` manifest
    array basis unchanged and the manifest API accepts no target argument;
11. zero-output adapter is raw-query identity;
12. all trainable controls take matched optimizer steps and final checkpoints;
13. pure metric/bootstrap/G1-G9 replay is deterministic; an empty required
    metric cohort yields finite replay evidence and false gates rather than a
    warning, nonfinite record, or arbitrary choice;
14. offline metadata encoding uses the registered local-only constructor with
    no API fallback that can relax that contract.

## Fail-closed integrity and Windows execution

Use the workspace virtual-environment interpreter directly with `-B -u` and
all BLAS/OpenMP thread variables set to one before numerical imports. Redirect
stdout/stderr to persistent files; never use a short foreground pipe. Use
exclusive outer and runner locks, append-only no-overwrite fsynced publication,
PID acknowledgements, async exception/unraisable ledgers, hashes of runner,
launcher, config, protocol, question, cycle-5 survey, architecture, and
interpreter, recursive artifact closure, and post-exit process/lock/log
verification. Runner closure excludes its candidate; launcher/verifier logs,
locks, reports, and the later marker are outside that closure. The launcher
checks verifier-lock release only after the verifier process exits.

Fail on any archive/config/protocol/source mismatch; unsafe extraction;
malformed half-star rating; cohort/split leak; early target join; insufficient
support/capacity/power; nonfinite score; wrong quota, duplicate, seen item, or
branch overlap; oracle mismatch; method-specific alpha; missing control or seed;
changed representation/index; target injection; stderr/error-ledger content;
partial output; missing process exit; live lock; or incomplete external marker.
