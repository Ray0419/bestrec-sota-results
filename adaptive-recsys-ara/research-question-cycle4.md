# Phase 2, Cycle 4: Locked FACET-PREF Research Question

Status: **outcome-blind Phase-2 protocol lock**. This record becomes
authoritative when committed. The Phase-3 configuration and source must
implement it without weakening, substituting, or reinterpreting an estimand,
comparator, threshold, or cohort. No `T` item identity, rating, candidate
outcome, or method metric from the cycle-4 cohort may be opened before the
complete Phase-3 source lock.

## Primary research question

> At a fixed 200+200 vector-retrieval budget and with immutable catalog
> embeddings and indexes, can macro-balanced, SimPO-inspired reference-free
> alignment of facet-conditioned user queries improve natural preference-pair
> co-support by at least 0.02 over a single-centroid semantic–collaborative
> hybrid and improve strict preference-consistent exposure at top 10 by at
> least 0.005 over both that hybrid and selected BPR, while remaining
> non-inferior to the hybrid in temporal
> NDCG@10 and within 1.25x of the hybrid's single-thread CPU p95 latency?

The question is novel only at the registered systems intersection. It does not
claim a new multi-interest encoder, preference loss, vector index, or ranking
metric. It is empirically falsifiable: every numeric threshold and comparator
below is conjunctive, and one failure kills FACET-PREF.

## Authenticated data and fresh cohort

- Dataset: official GroupLens MovieLens 1M archive.
- Required SHA-256:
  `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`.
- Ratings, title, and genres are used. User demographics are forbidden as
  inputs and selection variables and no demographic-fairness claim is made.
- Preserve the established per-user, indivisible-timestamp-group blocks:
  `A=60%`, `R=20%`, `V=10%`, and sealed `T=10%`.
- Preserve the established eligibility rules: at least 50 events, four
  timestamp groups, 10 `A` events, two positive `A` items, and at least one
  positive item in each of `V` and `T`.
- Order eligible users by
  `SHA256("20260817:{user_id}")`, then numeric user ID. CAPER used `[0:1000]`,
  RAVEL used `[1000:2000]`, and FACET-PREF prospectively receives
  **`[2000:4000]`**, exactly 2,000 users. All three manifests must be rederived
  and pairwise disjoint. Fewer than 4,000 eligible users fails closed.

The eligibility pass may reveal only membership predicates and block offsets.
It may not expose cycle-4 `V/T` item identities, ratings, pairs, or outcomes.

## Target-blind temporal order

1. Authenticate source, code, configuration, environment, and cohort.
2. Fit BPR variants and all global normalizers on `A` only. Encode item
   metadata without ratings and build immutable semantic and collaborative
   FAISS indexes.
3. Form target-blind `R` requests from `A` prefixes. Only after their facet and
   query descriptors are published may `R` ratings be joined to create the
   natural training-pair corpus.
4. Train FACET-PREF and all matched aligned controls from `R` only with fixed
   hyperparameters and epochs. No `V/T` target participates.
5. Publish target-blind `V` candidate/ranking manifests for every method. Use
   `V` **relevance only** to lock the BPR identity and one shared fusion
   coefficient on the single-centroid baseline; freeze both across every
   hybrid/control. `V` preference
   pairs may be reported only after all choices are locked and may not select a
   checkpoint, margin, facet count, quota, control, or threshold.
6. Freeze every representation, model, index, candidate budget, fusion weight,
   and tie-break. Open the otherwise unused `V` preference labels only for the
   registered power audit below. A failed audit kills FACET-PREF before `T`; a
   passed audit cannot alter any choice. Construct and hash complete
   target-blind `T` query, candidate, scalar-score, and top-10 manifests from
   `A+R+V` prefixes.
7. Open `T` exactly once, compute the fixed estimands, user-cluster bootstrap,
   G1–G9, and `PROMISING`. No test-time repair or rerun is permitted.

## Fixed retrieval budget and registered comparators

Every hybrid method uses one immutable 384-dimensional normalized
SentenceTransformer item matrix and one immutable BPR item-factor matrix.
Each request receives:

```text
collaborative branch: 200 unique unseen items
semantic branch:      200 unique unseen items total across all facet queries
stable union:         BPR first, then semantic; no post-union truncation
exact union size:     400
```

The collaborative branch contains exactly 200 distinct unseen items. The
semantic branch contains exactly 200 additional distinct unseen items that are
not in the collaborative branch, so every hybrid union contains exactly 400
items. Exhaustion fails closed. FACET-PREF batches at most two facet queries in
one FAISS call at a fixed search depth of 700 per query. It starts with equal
`100/100` facet quotas, removes seen/BPR/duplicate items, and uses canonical
round-robin backfill from those same rows until exactly 200 remain. A one-facet
request uses one 200-item quota. Candidate multiplicity never enters the
ranker.

Facets are deterministic and prefix-only. Let `F=min(2, number of distinct
positive-prefix items)`. Spherical two-means is initialized by the least-similar
positive-item pair; cosine ties use lexicographic movie IDs, assignment ties use
canonical facet index, and updates stop at assignment stability or after eight
iterations. An empty cluster collapses, and facets are canonicalized by minimum
member movie ID. Rating-3 items are ignored. With frozen item vector `E_i`, raw
query

```text
b_uf = normalize(mean(E_i: liked item i in facet f)
                 - 0.25 * normalize(mean(E_j: disliked prefix item j))).
```

The global dislike term is zero when absent. No ID, demographic, candidate
outcome, current-block item, or target enters a query.

Registered baselines and controls are:

1. selected implicit/rating-aware BPR;
2. single-centroid semantic + BPR linear hybrid;
3. raw multi-facet retrieval with no learned alignment;
4. single-query aligned retrieval using the same adapter and training pairs;
5. multi-facet zero-margin reference-free training;
6. multi-facet deterministically shuffled pair direction;
7. pair-micro rather than user×facet-macro training.

All hybrid controls have the same branch budgets, item vectors, indexes, BPR
identity, training-pair cap, optimizer schedule, facet builder where applicable,
candidate merge, scalar fusion family, and latency instrumentation. Only the
named mechanism may differ. The mechanism core is the fixed 2×2 factorial
`{single,multi} × {raw,aligned}`; zero-margin, shuffled-direction, and
pair-micro variants are diagnostics.

All aligned methods use the same bounded, shared adapter across users and
facets:

```text
q_uf = normalize(b_uf + 0.25 * g(h_uf) / max(1, ||g(h_uf)||_2)).
```

The output layer of `g` is initialized to zero. Its inputs are restricted to
`b_uf`, the global liked centroid, global dislike centroid, facet-support
fraction, and normalized prefix length. The aligned semantic item score is
`max_f q_uf·E_i`; max ties use canonical facet index. Every method uses the
same quantile normalization, the one shared validation-locked fusion
coefficient, and ascending movie ID for final score ties.

One method-independent `R` corpus contains all naturally observed `R` pairs
with rating gap at least two, prospectively hash-capped before any aligned
model trains. Pair IDs, directions, cap, batch schedule, epochs, optimizer, and
seeds are identical. Assign a pair to the raw facet closest to its chosen item,
with canonical facet tie-break. The full method uses

```text
Delta = max_f(q_uf·E_i+) - max_f(q_uf·E_i-)
loss  = softplus(beta * (margin - Delta)).
```

User×facet macro weighting first averages pairs within a facet, then facets
within a user, then users. The shuffled control hash-orders pairs within user
and reverses exactly alternating orientations, preserving pair identities and
near-balanced directions.

## Method-independent preference estimands

For each cycle-4 user, form every unordered pair of naturally rated `T` items
with an absolute rating gap of at least two. The higher-rated endpoint is
`chosen`. If more than 100 pairs exist, retain 100 by ascending
`SHA256("20263118:{user_id}:{low_movie_id}:{high_movie_id}")`. This universe is
defined from sealed ratings without reference to any method's retrieval set.

### Natural preference-pair co-support

For candidate union `C_u`,

```text
PairSupport(u) = mean_(i+,i-) [ 1{i+ in C_u and i- in C_u} ].
```

This measures whether retrieval exposes preference-discriminating witnesses.
It is computed before ranking and user-macro averaged.

### Strict preference-consistent exposure at 10 (sPCE@10)

For served ranking `pi`, define `r10(i)` as its 1-based position when the item
is in the top 10 and `11` otherwise. For every fixed natural pair:

```text
1.0  if r10(chosen) < r10(rejected)
0.0  otherwise
```

`sPCE@10(u)` is the mean over that user's fixed pairs and is user-macro
averaged. Both-unshown pairs receive zero, so hiding a rejected item without
exposing its chosen counterpart earns no gain; rearranging ranks 11+ also earns
no credit. Half-tie accuracy, candidate-conditional accuracy, full-union
accuracy, and pair-micro accuracy are diagnostics only.

### Relevance, exposure, and retrieval outcomes

- binary NDCG@10 and Recall@10 over every naturally rated `T` item with rating
  at least four;
- low-rating intrusion@10 over naturally rated `T` items with rating at most
  two, treating unobserved items as unknown rather than dislikes;
- positive-item recall of the complete union before ranking;
- union size, branch overlap, pair co-support, and fraction of pair outcomes
  changed relative to each baseline.
- active-facet count, minimum facet size, quota utilization, and descriptive
  performance slices by prefix-history length, item-popularity profile, and
  genre diversity. These slices cannot enter a gate or tune a method.

MovieLens ratings are exposure-conditioned and missing-not-at-random.
PairSupport and sPCE@10 are offline observed-rating estimands, not causal
preference, counterfactual exposure, or fairness measures.

## Inference and support

Use optimization seeds `{20260827, 20260828, 20260829}`. First average every
user's outcome across all three seeds, then run a paired 10,000-draw percentile
bootstrap over users with alpha `0.05` and seed `20263117`. Never resample
pairs or treat seed rows as independent. PairSupport/sPCE use the fixed
pair-bearing cohort; NDCG/Recall/positive-union recall use the fixed
relevance-eligible cohort; intrusion uses all evaluation users and records zero
when no observed low-rating item is exposed. Within a metric, paired methods
always use identical users and pair IDs. Missing values inside a fixed cohort
fail closed.

Before any gate is evaluated, `R` must contain at least 5,000 eligible natural
pairs from at least 1,000 pair-bearing users after the prospective cohort is
fixed. `T` must contain at least 2,000 fixed natural pairs and at least 500
pair-bearing users. These are support floors, not evidence of efficacy.

After every choice is frozen and before `T` is opened, run a power audit on the
previously unused fixed `V` pair cohort. For FACET-PREF versus each primary
baseline, center the per-user, seed-averaged paired sPCE differences, add the
registered alternative `delta=0.005`, and simulate 2,000 experiments of 500
users sampled with replacement. Each experiment estimates a two-sided 95%
percentile lower bound with 1,000 user bootstrap draws. Both comparisons must
have at least 80% probability of a lower bound above zero. Seeds are
`20263119` and `20263120`. Failure kills before `T`; results cannot alter a
method, threshold, or cohort.

## G1–G9 all-or-nothing promise gate

1. **G1 — fixed-budget upstream intervention.** Every semantic method returns
   exactly 200 unique unseen BPR-novel semantic candidates, every collaborative
   branch returns exactly 200, every union has exactly 400 items, no
   query uses its current block's target, and semantic/BPR matrices and FAISS indexes are
   hash-identical before and after evaluation.
2. **G2 — material retrieval support.** FACET-PREF minus the single-centroid
   hybrid has user-macro natural-pair co-support point gain at least `+0.020`
   and a paired 95% lower bound above zero. Its positive-item union recall point
   gain is at least `+0.020` with lower bound above zero.
3. **G3 — primary served preference gain.** FACET-PREF sPCE@10 exceeds both the
   single-centroid hybrid and selected BPR by at least `+0.005` absolute, and
   both paired 95% lower bounds are above zero.
4. **G4 — relevance and dislike safety.** Against the single-centroid hybrid,
   FACET-PREF-minus-baseline NDCG@10 has point estimate at least `-0.0002` and
   lower bound strictly above `-0.001`; Recall@10 lower bound is strictly above
   `-0.002`; and the low-rating-intrusion increase upper bound is at most
   `+0.002`.
5. **G5 — facet/alignment mechanism.** FACET-PREF has strictly higher point
   PairSupport and sPCE@10 than each raw-multi-facet, single-query-aligned,
   zero-margin, shuffled-direction, and pair-micro control. It must therefore
   support the registered joint mechanism involving multiple facets, natural
   pair direction, a positive margin, and user×facet macro balancing. Point
   diagnostics do not establish component necessity, and no significance claim
   is made for them at PoC scale.
6. **G6 — nondegenerate fixed support.** The registered `R/T` pair and user
   floors and the pre-`T` power audit pass. Across the fixed user–pair–seed
   rows, `mean 1[pair endpoints are both in C_FACET and C_hybrid]` is at least
   `0.10`; and `mean 1[sPCE_FACET != sPCE_hybrid]` is at least `0.02`.
7. **G7 — seed stability.** At least two of three seeds independently have
   positive FACET-PREF-minus-hybrid PairSupport, sPCE@10, and union positive-item
   recall, plus NDCG@10 delta at least `-0.0002`.
8. **G8 — serving budget.** Worst-seed, single-thread CPU FACET-PREF p95 is at
   most `5 ms` and at most `1.25x` the identically instrumented dual-index
   single-centroid hybrid. Timing includes both FAISS searches, filtering,
   deterministic backfill/merge, feature construction, fusion, and sorting; it
   excludes offline encoding, training, index construction, targets, and I/O.
9. **G9 — provenance and external replay.** Archive, cohort, temporal-order,
   target-blindness, source, config, model, matrix, index, manifest, raw-array,
   bootstrap, process-exit, lock-release, recursive-hash, empty-stderr, and
   empty-asynchronous-ledger checks all pass. A source-bound post-exit verifier
   must recompute G1–G9 from raw arrays before publishing the sole external
   completion marker.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

Any false gate kills FACET-PREF immediately. Weighted sums, threshold changes,
test-cohort substitution, post-outcome source repair, partial-seed rescue, and
an automatic outcome rerun are forbidden. Phase 5 may begin only from a valid
external marker with `PROMISING=true`.
