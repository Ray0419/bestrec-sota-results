# Phase 3, Cycle 5: CABLE-PREF Architecture

Status: outcome-blind architecture lock. The authoritative Phase-2 record is
`literature/research-question-cycle5.md`. If this document or the JSON
configuration appears to weaken a cohort rule, estimand, comparator, threshold,
or fail-closed condition in that record, the Phase-2 record wins and execution
must stop.

No MovieLens 10M archive member or label was inspected while this architecture
was written.

## Scope and claim boundary

CABLE-PREF is **Cardinality-Assured Boundary Learning for Preference-aligned
retrieval**. It tests whether a small, reference-free semantic-query adapter can
move a preferred item across the exact candidate-admission boundary it will
face at serving time. It keeps the SentenceTransformer item vectors, BPR item
factors, and both serialized FAISS indexes immutable.

The following are infrastructure or prior art, not claimed contributions:

- SentenceTransformer metadata encoding;
- BPR, inner-product search, `faiss.IndexFlatIP`, masked top-k, or filtered ANN;
- semantic/collaborative hybrid retrieval;
- SimPO or scalar pairwise margin learning;
- generic learned user-interest thresholds; and
- exhaustive search as a production-scale ANN method.

The candidate mechanism is narrower: endpoint-leave-out alignment against the
nonparametric 200th order statistic of the *actual request-specific semantic
complement*, followed by exact 200+200 retrieval and end-to-end admission,
served-preference, relevance, safety, stability, and latency tests.

## End-to-end pipeline

```text
movies.dat: UTF-8 title + genres
    -> frozen all-MiniLM-L6-v2 -> normalized float32 E[N,384]
                                  -> immutable semantic IndexFlatIP

ratings.dat, selected users' A only
    -> implicit BPR-MF -> user factors U[2000,64]
                      -> supported item factors Vcf[Ncf,64]
                      -> immutable collaborative IndexFlatIP

available prefix only
    -> liked/disliked metadata centroids -> raw semantic query b_u
    -> shared zero-output bounded adapter -> q_u
    -> frozen BPR query p_u

p_u -> full exact collaborative row -> mask prefix -> stable top-200 B_u
q_u -> full exact semantic row -> mask prefix and B_u -> stable top-200 S_u
                                                       C_u = B_u + S_u (400)

R request rows and masks are published before R labels
    -> natural rating-gap pairs
    -> endpoint-leave-out boundary from already-published score rows
    -> admission loss + order loss, no reference model

C_u -> shared BPR/semantic component normalization
    -> one raw-V-relevance-selected alpha shared by all hybrids
    -> stable score/item-ID sort -> served top 10

sealed T -> ConditionalAdmission@200, NetNewPreferredSupport, sPCE@10,
            NDCG@10, Recall@10, low-rating intrusion, G1-G9
```

The quality path is exact by construction. A later scaled study may replace
the exhaustive row with filtered ANN, but it must measure ANN recall and work
against this exact oracle and may not reinterpret the PoC as a sublinear-search
result.

## Authenticated data and bounded-memory loading

The only allowed inputs are `ratings.dat` and `movies.dat` from the official
MovieLens 10M archive. The zip must have size `65,566,137`, SHA-256
`813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`,
and MD5 `ce571fd55effeba0271552578f2648bd` before extraction. `tags.dat` is
forbidden. Extraction rejects absolute paths, traversal, links, duplicate
members, unexpected required-member multiplicity, and overwrite.

`movies.dat` is decoded as UTF-8. Ratings are parsed as half-star-capable
floating-point values; no integer coercion is allowed. Source-row ordinal is
preserved as an explicit tie-break.

Loading uses bounded streaming passes rather than retaining all ten million
events:

1. Pass 1 accumulates per-user structural summaries and timestamp-group
   boundaries needed for the locked split and count-only predicates. It does
   not retain rating-row payloads and may not publish or use an `R/V/T` item
   identity, rating, positive count, pair, or candidate outcome.
2. An `A`-authorized rescan evaluates the remaining `A`-only eligibility
   predicate. Fully eligible users are ordered by
   `SHA256("20260835:{user_id}")`, then numeric user ID; the streaming reservoir
   retains `A` values only for the smallest 2,000 keys. Fewer fails closed.
3. Separate authorized rescans then parse `R`, a thresholded binary-relevance
   `V` view, exact `V` only after choices freeze, and finally `T`; each parses
   selected-user current-view fields and verifies pass-1 layouts. A later view
   is not parsed before its target-blind predecessor.

Within a user, events sort by `(timestamp, source_row_ordinal)`. Consecutive
timestamp groups are allocated to `A/R/V/T = 60/20/10/10%` by nearest
cumulative event count; a cutoff tie goes to the earlier group. Adjacent
nonempty blocks must have strictly increasing timestamps.

Eligibility is exactly the revised Phase-2 rule: at least 80 events, four
timestamp groups, 20 `A` events, five distinct `A` items rated at least 4, and
the conservative count-only bound
`|C_sem|-(|A|+|R|+|V|) >= 700`. Only counts, times, semantic-catalog capacity,
and `A` values may affect membership; later item identities remain unused. The
source is required and verified to be user-grouped. The estimand is per-user
future ranking, not a global calendar-time split.

## Representation

### Frozen semantic item matrix

Each movie is rendered exactly as

```text
{title} [SEP] {genres}
```

and encoded locally with frozen
`sentence-transformers/all-MiniLM-L6-v2`. The 384-dimensional output is cast
to float32 and L2-normalized:

```text
E_i = normalize(ST(title_i + " [SEP] " + genres_i)).
```

Ratings, tags, popularity, user IDs, target labels, and candidate outcomes do
not enter `E`. Movies are stored in ascending numeric movie-ID order. The
matrix and a serialized `faiss.IndexFlatIP(384)` are hashed before adapter
training and must be byte-identical after evaluation.

### Frozen collaborative representation

One standard implicit BPR-MF model is trained from selected-cohort `A` only.
An `A` event is positive when its rating is at least 4. The collaborative item
catalog contains only items with at least five such interactions. Unobserved
sampled items are optimization negatives, not asserted dislikes.

The BPR model has 64-dimensional user/item factors. Its deterministic training
schedule is fixed in the JSON configuration. At a later request, the query is
the trained user factor plus `0.5` times a rating-weighted aggregate of frozen
item factors from the available prefix. Items outside the supported
collaborative catalog have an all-zero BPR feature for hybrid scoring and can
never enter the BPR candidate branch. The supported item matrix and its
`IndexFlatIP(64)` serialization are immutable after `A` fitting.

At every request, the BPR domain must contain at least 200 prefix-unseen items
and the semantic complement after BPR removal must contain at least 500. This
check occurs before current-block target access.

### Prefix-only raw semantic query

Liked prefix items have rating at least 4; disliked items have rating at most 2.
A repeated `(user, movie)` row anywhere across the available prefix stages is
an integrity failure; the runner does not resolve repeated ratings by selecting
one outcome. Define

```text
l_u = normalize(mean(E_i for distinct liked prefix items))
d_u = normalize(mean(E_j for distinct disliked prefix items)), or zero
b_u = normalize(l_u - 0.25 * d_u).
```

The five-liked-`A` eligibility rule prevents an empty liked set. Neither a
current block item nor any target outcome enters these vectors.

### Capacity-matched bounded adapter

Every semantic method carries the same adapter schema. Raw retrieval keeps its
zero-output artifact unchanged; every learned control performs the same number
of optimizer steps. The input is

```text
h_u = concat(b_u, l_u, d_u, min(prefix_event_count,500)/500)  # 1,153
```

and the network is

```text
Linear(1153,32) -> tanh -> Linear(32,385).
```

The first 384 outputs form the query displacement. The final output is a scalar
boundary slot used only by the UIB-style control; it exists for every method so
learned controls have exactly equal parameter count. The output layer is
initialized to exact zeros. With displacement `a_u`,

```text
q_u = normalize(b_u + 0.25 * a_u / max(1, ||a_u||_2)).
```

Thus the pre-normalization displacement is bounded by 0.25. No adapter changes
an item vector or index.

## Exact masked retrieval

### Canonical exact operator

For query `q`, immutable index `I`, allowed ID domain `G`, exclusion set `F`,
and requested cardinality `K`, define:

```text
ExactMaskedTopK(I, q, G, F, K):
    score_row = I.search(q, I.ntotal)       # every indexed ID, exact IP
    keep IDs in G and not in F
    sort by (-float32_inner_product, numeric_item_id)
    require at least K survivors
    return first K IDs and their canonical scores
```

Manifest construction processes bounded query batches, so it never holds all
users' full rows simultaneously. Latency uses batch size one. An independent
matrix-dot/full-stable-sort implementation must reproduce every selected ID and
order. FAISS output order is never accepted as a tie-break by itself.

### Collaborative then semantic complement

For prefix history set `H_u`,

```text
B_u = ExactMaskedTopK(I_cf, p_u, collaborative_catalog, H_u, 200)
D_u = semantic_catalog \ (H_u union B_u)
S_u = ExactMaskedTopK(I_sem, q_u, semantic_catalog, H_u union B_u, 200)
C_u = B_u followed by S_u
```

The run asserts `|B_u|=200`, `|S_u|=200`, `B_u intersect S_u=empty`, every ID
is prefix-unseen, and `|C_u|=400` for every request, method, and seed. There is
no append, retry, truncation, branch exchange, target injection, or empirical
depth selection. The semantic slack check requires `|D_u|>=500`, not merely
200.

## Action-consistent endpoint-leave-out target

For an admission-active preferred endpoint `i+` (`i+` is in `D_u`), sort all
of `D_u` by the deployed semantic key `(-score, item_id)`. Let

```text
t_u^(-i+) = the 200th item/score in D_u \ {i+}.
```

Only `i+` is removed; the rejected endpoint is never removed ad hoc. The
boundary is efficiently derived from one exact top-201 row:

- if `i+` is in the original top 200, the leave-out boundary is original rank
  201;
- otherwise it is original rank 200.

The boundary score is detached from autograd. Candidate admission itself uses
the full score-plus-item-ID key: `i+` is in semantic top 200 if and only if its
key precedes the leave-out boundary key. Synthetic and real G1 replay must
verify this equivalence, including exact-score ties.

The wrong-boundary control instead constructs its leave-out cutoff from the
semantic catalog after prefix exclusion but *before* excluding `B_u`. It still
serves from the correct complement, isolating the deployed-boundary mechanism.

## Reference-free alignment

### Target-blind `R` corpus

For `R`, the available prefix is `A`. Before any `R` rating is joined, publish
and hash, for every user and method-independent base request, the prefix/query
descriptor, BPR row and `B_u`, semantic eligibility mask, raw score row, and
top-201 boundary material. Only then join `R` ratings.

Within each user, form all unordered pairs of distinct `R` items with rating
gap at least 2.0. The higher-rated item is preferred. Sort by
`SHA256("20263503:{user_id}:{low_item_id}:{high_item_id}")` and keep at most
32 pairs per user. If more than 30,000 remain, sort first by the pair's
one-based within-user hash rank and then by pair hash, and retain 30,000. This
round-aware global cap gives every pair-bearing user one opportunity before any
user receives its second. Pair IDs and natural directions are identical across
methods and seeds. For admission loss, preferred endpoints are deduplicated
within user after the pair caps, so one item is not multiplied by the number of
items it beats. The capped `R` corpus must still satisfy G6. `V/T` evaluation
pairs use their separately registered cap of 100 per user and no training cap.

### SimPO-style scalar losses

For semantic scores `s+ = q_u dot E_i+`, `s- = q_u dot E_i-`, detached
leave-out cutoff `t`, `beta=5`, admission margin `m_a=0.02`, and order margin
`m_o=0.10`, define

```text
L_admit = softplus(beta * (m_a - (s+ - stop_gradient(t))))
L_order = softplus(beta * (m_o - (s+ - s-)))
```

`L_admit` exists only when `i+` is outside `B_u` and inside the semantic
complement. `L_order` retains every preserved natural pair. This is
SimPO-style reference-free scalar margin optimization: there is no DPO
reference policy, second-policy forward pass, language-model probability, or
online decoding.

Admission endpoints are averaged within user and then across active users.
Order pairs are separately averaged within user and then across pair-bearing
users. Full CABLE combines the two already macro-normalized terms as

```text
L_CABLE = 0.5 * mean_user(L_admit) + 0.5 * mean_user(L_order).
```

Order-only and admission-only use weight 1.0 on their sole term, preventing the
full model from winning through doubled gradient magnitude.

All learned variants use 12 fixed epochs, AdamW, learning rate 0.003, weight
decay `1e-4`, gradient clip 1.0, common hash-ordered user groups of 128, and
optimization seeds `{20260835,20260836,20260837}`. The exact final epoch is
served; there is no early stopping or preference-selected checkpoint.

### Matched methods

| ID | Query training | Boundary used at training | Serving domain |
|---|---|---|---|
| `bpr` | none | none | BPR 200 only |
| `raw_hybrid` | zero/raw | none | exact semantic complement |
| `order_only` | `L_order` | none | exact semantic complement |
| `admission_only` | `L_admit` | correct leave-out | exact semantic complement |
| `cable_pref` | `0.5 L_admit + 0.5 L_order` | correct leave-out | exact semantic complement |
| `shuffled_direction` | full loss, deterministic half-reversal | correct for shuffled endpoint | exact semantic complement |
| `uib_boundary` | learned scalar separates preferred/rejected scores | learned scalar | exact semantic complement |
| `wrong_boundary` | full loss | pre-BPR-exclusion leave-out | exact semantic complement |

For `uib_boundary`, the 385th adapter output is a learned request boundary
`c_u`; on admission-active pairs it uses equal-weight softplus penalties for
`s+ >= c_u + 0.02` and `s- <= c_u - 0.02`, separately user-macro normalized,
as its admission term. It then combines that term 0.5/0.5 with the same
`L_order` as CABLE.
The shuffled control orders a user's preserved pair IDs by the registered hash
and reverses even zero-based orientations. Every learned method receives the
same pair presentations, group order, capacity, initialization family,
clipping, steps, and checkpoint rule. Only the named loss mechanism differs.

## Ranking and validation lock

Every hybrid ranks its exact 400-item union. Semantic component score is
`q_u dot E_i`. BPR component score is the shared frozen BPR dot product;
unsupported semantic-only items use the registered all-zero BPR factor.
Independently winsorize each component on that request:

```text
denom = max(Q95 - Q05, 1e-6)
z_i = clip((score_i - Q05) / denom, 0, 1)
fused_i = alpha * z_bpr_i + (1-alpha) * z_sem_i.
```

The raw hybrid's `V` relevance selects one `alpha` from
`[0,0.25,0.5,0.75,1]`, breaking ties by Recall@10 and then larger alpha. The
chosen alpha is shared unchanged by every hybrid and control. Final ties use
ascending numeric item ID. `bpr` serves its own exact BPR top 200 in BPR-score
order.

## Mandatory target-blind stage order

1. Freeze and hash the protocol, config, runner, verifier, environment, and
   SentenceTransformer identifier/package version. Authenticate and safely
   extract the archive.
2. Run the structural pass, then the `A`-authorized eligibility/value rescan;
   freeze the exactly 2,000-user cohort, its retained `A`, and `A/R/V/T`
   layouts without parsing an `R/V/T` value.
3. Encode metadata, fit the one `A`-only BPR model, construct both IndexFlatIP
   indexes, and publish immutable semantic/BPR matrices, indexes, and hashes.
4. From `A` prefixes, publish the replay-complete target-blind `R` request
   basis: history, BPR branch, raw queries, complement count, and cutoff
   identity/score. The already durable immutable artifacts and source-bound
   tie rule complete the replay closure. Join `R` only afterward; create the
   fixed pair corpus.
5. Train every learned method for all three seeds and 12 fixed epochs. Publish
   final model hashes. No `V/T` preference outcome is available.
6. From `A+R` prefixes, publish the target-blind `V` replay basis: histories,
   queries, candidates, and raw component scores. The already durable immutable
   artifacts and source-bound alpha grid/tie rule complete the closure basis
   used to reconstruct every ranking. Open only the registered `V` binary
   relevance view to select alpha on `raw_hybrid`.
7. Freeze alpha and every remaining choice. Open the fixed `V` preference view
   only for the centered power audit. Failure kills before `T`; success cannot
   change a model, threshold, or cohort.
8. Treat `V` as history and, from `A+R+V` prefixes, publish and hash the complete
   target-blind `T` replay basis for every method and seed: histories, queries,
   candidates, and raw component scores. The already durable immutable
   artifacts, source-bound tie rule, and separate frozen-choice artifact
   complete the closure basis used to reconstruct full score domains, fused
   order, and top-10 lists.
9. Open `T` exactly once, form the fixed pair/endpoint universes, compute raw
   metrics and user-cluster bootstrap arrays, and evaluate G1-G9. A separately
   bound post-exit verifier alone may publish the authoritative marker.

The validation relevance interface exposes only the relevance view needed for
selection; exact ratings and preference pairs remain unavailable to selection
code. No target is ever appended to a candidate set.

## Fixed metrics and inference

For each stage after its target-blind manifests are durable, natural pairs use
rating gap at least 2.0. `R` uses the registered 32-per-user and 30,000 global
round-aware training caps; `V/T` use 100 per user. For `T`, preferred endpoints
are deduplicated within user. With shared BPR set `B_u`, `P_u` the fixed preferred endpoints, and
`M_u={i in P_u: i not in B_u}`:

```text
ConditionalAdmission@200(u) = mean_{i in M_u} 1[i in S_u]
NetNewPreferredSupport(u)    = mean_{i in P_u} 1[i not in B_u and i in S_u]
```

Users with no denominator are counted and reported, not silently treated as
zeros or dropped before the support gate. Preferred endpoints count once per
user. Net admission advantage is the user-macro mean of
`1[i+ in S]-1[i- in S]` on fixed pairs.

For a fixed pair, assign served rank 1-10 when exposed and 11 otherwise:

```text
sPCE_pair@10 = 1 if rank10(preferred) < rank10(rejected), else 0.
```

Both-unshown and rank ties score zero; tail-only changes earn no credit. Binary
NDCG@10 and Recall@10 use naturally rated items with rating at least 4.
Low-rating intrusion@10 uses only observed items rated at most 2; unobserved
items remain unknown. Preferred-endpoint top-10 exposure is also reported.

Average each user's metric across all three optimization seeds, then use a
paired 10,000-draw percentile bootstrap over users at alpha 0.05 with seed
`20263504`. Never resample endpoints, pairs, or seed rows as independent units.
Bounds are the two-sided 2.5th/97.5th percentiles. The pre-`T` power exception
uses finite common-user method differences, centers them to zero, adds the
registered effect without clipping, draws 1,000 outer user resamples, and tests
each with 1,000 inner user-bootstrap draws using a 2.5th-percentile lower bound
above zero. Every one of the four registered comparisons must detect in at
least 80% of outer experiments.

## G1-G9 all-or-nothing promise gate

1. **G1 - exact feasibility and action consistency.** The shared BPR request
   returns exactly 200 unique unseen items; every hybrid request returns exactly
   200 unique unseen and BPR-novel semantic items and a 400-item union. An independent full-score
   stable-sort replay agrees on every ID and order. Synthetic and real replay
   verify the leave-one-endpoint cutoff/admission equivalence and deterministic
   ties. Item matrices and indexes remain hash-identical.
2. **G2 - material preferred admission.** CABLE-PREF's user-macro conditional
   Admission@200 point gain is at least `+0.020` over raw exact-complement
   retrieval and `+0.010` over order-only alignment, with both paired 95%
   lower bounds above zero. Its unconditional NetNewPreferredSupport gain over
   raw is at least `+0.010`, with lower bound above zero. Its point net admission
   advantage `mean(1[i+ in S]-1[i- in S])` exceeds raw.
3. **G3 - served preference utility.** CABLE-PREF's user-macro sPCE@10 gain is
   at least `+0.005` over both raw hybrid and BPR, with both paired 95% lower
   bounds above zero. Preferred-endpoint top-10 exposure has positive point gain
   over raw.
4. **G4 - relevance and dislike safety.** Against the validation-selected
   stronger relevance baseline of raw hybrid and BPR: NDCG@10 point delta is at
   least `-0.0002` and its lower bound is strictly above `-0.001`; Recall@10
   lower bound is strictly above `-0.002`. Against raw hybrid, the low-rating
   intrusion increase upper bound is at most `+0.002`.
5. **G5 - matched mechanism controls.** Full CABLE-PREF has strictly greater
   point Admission@200 than order-only, UIB-style, wrong-boundary, and shuffled-
   direction controls, and strictly greater point sPCE@10 than admission-only,
   order-only, UIB-style, wrong-boundary, and shuffled-direction controls.
6. **G6 - nondegenerate support and power.** `R` supplies at least 20,000 fixed
   pairs from 1,000 users; `T` supplies at least 5,000 fixed natural pairs and
   5,000 unique BPR-missed preferred endpoints, each from at least 1,000 users.
   Admission membership differs from raw on at least 5% of fixed user-endpoint-
   seed rows and sPCE differs on at least 2% of fixed user-pair-seed rows. A
   centered fixed-`V` audit, after all choices freeze, detects injected `+0.020`
   admission and `+0.005` sPCE effects in at least 80% of 1,000 bootstrap
   experiments; failure kills before `T`.
7. **G7 - seed stability.** All seeds `{20260835,20260836,20260837}` complete
   and enter the aggregate. At least two independently show positive admission
   gain over raw and order-only, positive sPCE gain over raw, and NDCG delta at
   least `-0.0002` versus raw. No seed's CABLE-minus-raw NDCG delta is below
   `-0.001`.
8. **G8 - serving latency.** For 512 prospectively hash-selected requests, one
   CPU thread, resident matrices, 32 warm-ups, seven AB/BA-interleaved
   repetitions, and per-request medians, worst-seed CABLE p95 is at most `10 ms`
   and at most `1.25x` the identically instrumented raw exact-complement hybrid.
   Timing includes query construction/adapter, both full score paths,
   mask/complement construction, stable top-k, fusion, and sorting; it excludes
   training, encoding, disk I/O, and metric joins.
9. **G9 - provenance and external replay.** Archive/extraction, cohort,
   temporal order, target blindness, candidate manifests, source, protocol,
   config, environment, interpreter, model, matrices, indexes, raw arrays,
   bootstrap, process exit, lock release, empty stderr/error ledgers, and
   recursive hashes all verify. A separately source-bound post-exit verifier
   recomputes G1-G9 before publishing the sole authoritative marker.

The marker is exactly
`run_directory/CABLE_EXTERNAL_COMPLETE_<execution_fp16>.json`, schema
`cable-pref-external-complete-v1`. Exactly one may exist; only the launcher may
publish it after the verifier exits and releases its lock.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

Any false gate, support failure, power failure, process failure, or incomplete
external verification kills CABLE-PREF immediately. No outcome rerun, source
repair, threshold change, cohort substitution, partial-seed rescue, weighted
score, or manual override is authorized.

## High-level pseudocode

```python
# Authenticate first; structural pass plus stage-sealed rescans; never load tags.dat.
layouts = structural_pass_1(ratings_stream, split_by_timestamp_groups)
cohort, A = authorized_A_eligibility_rescan_and_hash_reservoir(
    ratings_stream, layouts, k=2000, key="20260835:{user_id}")

E = l2_normalize(sentence_transformer.encode(title_sep_genres, local_only=True))
I_sem = faiss.IndexFlatIP(384); I_sem.add(E)
bpr = train_one_implicit_bpr(A, dim=64, positive_rating_min=4)
I_cf = faiss.IndexFlatIP(64); I_cf.add(bpr.supported_item_factors)
freeze_hash(E, I_sem, bpr, I_cf)

def stable_masked_full_row(index, query, allowed_ids, excluded_ids, k):
    scores, rows = index.search(query[None, :], index.ntotal)
    triples = [(float32(s), numeric_item_id(row))
               for s, row in zip(scores[0], rows[0])
               if row in allowed_ids and row not in excluded_ids]
    triples.sort(key=lambda x: (-x[0], x[1]))
    assert len(triples) >= k
    return triples[:k], triples

def retrieve(prefix, raw_or_aligned_query):
    B, _ = stable_masked_full_row(I_cf, bpr_query(prefix), CF_IDS,
                                  prefix.item_ids, 200)
    S, full_sem = stable_masked_full_row(I_sem, raw_or_aligned_query,
                                         SEM_IDS, prefix.item_ids | ids(B), 200)
    assert_exact_200_plus_200(B, S)
    return B, S, full_sem

# Publish A-prefix R score/mask rows before joining R ratings.
R_base = publish_R_target_blind_rows(A)
R_pairs = fixed_natural_pairs(join_R_after_publish(R_base), gap=2.0,
                              per_user_cap=32, global_cap=30000,
                              global_order="within_user_rank_then_pair_hash",
                              hash_seed=20263503)

for seed in [20260835, 20260836, 20260837]:
    for method in LEARNED_METHODS:
        model = zero_output_capacity_matched_adapter(seed)
        for epoch in range(12):
            for users in common_hash_user_groups(R_pairs, seed, epoch, 128):
                q = model.query(users.prefix)
                sem_top201 = exact_semantic_complement_topk(q, k=201)
                t_leaveout = derive_endpoint_leaveout_boundaries(sem_top201)
                admit = user_macro_admission_loss(q, t_leaveout,
                                                  beta=5, margin=.02)
                order = user_macro_order_loss(q, R_pairs,
                                              beta=5, margin=.10)
                loss = method.fixed_combination(admit, order)
                adamw_step(model, loss, lr=.003, weight_decay=1e-4,
                           clip_norm=1.0)
        freeze_final_epoch(model)

# Publish V alpha-grid manifests before the relevance join. Select alpha on
# raw_hybrid relevance only, freeze all choices, then run the fixed V power audit.
# Publish complete T manifests before opening T once.
raw_arrays = evaluate_fixed_T()
runner_candidate_promising = all(internal_G1_to_G9(raw_arrays).values())
PROMISING = False  # runner is deliberately non-authoritative
# Only the post-exit launcher may publish the sole external marker after
# an independent verifier derives all(gates.values()).
```

## Complexity and systems interpretation

Let `N_s` be semantic-catalog size, `N_c` collaborative-catalog size, semantic
dimension `d=384`, BPR dimension `r=64`, and union size `K_u=400`.

- Metadata encoding is offline and linear in `N_s` encoder evaluations.
- The registered full-result-row implementation costs
  `O(N_c r + N_s d)` inner-product work plus `O(N_c log N_c + N_s log N_s)`
  result ordering/filtering and `O(K_u log K_u)` final sorting. A future
  streaming heap implementation could reduce the ordering term to
  `O(N_c log 200 + N_s log 200)` without changing exact semantics, but it is
  not the registered main path.
- A bounded batch stores `O(batch*(N_c+N_s))` score/ID values. Batch-one latency
  uses `O(N_c+N_s)` row storage. Streaming top-k can reduce auxiliary memory to
  `O(201)` while preserving the same exact stable order.
- One top-201 semantic row supplies every endpoint-leave-out cutoff for that
  user; boundary extraction is `O(1)` per deduplicated preferred endpoint, not
  another catalog scan per pair.
- Adapter serving work is `O(1153*32 + 32*385)`, small relative to the full
  semantic scan.

These are MovieLens-scale exhaustive-search costs. G8 is an empirical PoC
latency test, not evidence of sublinear catalog scaling. Any paper-level scale
claim requires a separate, larger-catalog filtered-ANN study against this exact
operator.
