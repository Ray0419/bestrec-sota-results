# Phase 3, Cycle 4: FACET-PREF Architecture

Status: outcome-blind architecture lock. This design implements
`research-question-cycle4.md`; that Phase-2 lock is authoritative if any later
artifact appears to weaken its cohort, estimand, comparator, threshold, or
fail-closed rule.

## Scope and claim boundary

FACET-PREF is a fixed-budget upstream retrieval intervention. It asks whether
two deterministic, prefix-only semantic facets can be aligned from natural
rating-gap pairs before nearest-neighbor search, so that the retrieved union
contains more preference-discriminating evidence and the served top 10 exposes
the preferred endpoint more often. It does not claim a new multi-interest
encoder, preference loss, vector index, ranking metric, causal preference
effect, or fairness result. The potentially novel object is the registered
systems intersection: user-by-facet macro reference-free alignment of query
geometry, immutable item geometry, exact 200+200 retrieval, and end-to-end
support, exposure, relevance, and latency tests.

## End-to-end pipeline

```text
title + genres
    -> frozen SentenceTransformer -> normalized 384-d item matrix E
                                      -> immutable FAISS semantic index

A ratings only
    -> implicit BPR and rating-aware BPR -> frozen 64-d item matrices
                                           -> immutable FAISS CF indexes

available user prefix (never current-block targets)
    -> positive metadata vectors -> deterministic spherical two-means
    -> <=2 raw facet queries b_uf
    -> shared bounded adapter g trained only on natural R pairs
    -> aligned facet queries q_uf

q_cf ------------------------> one CF FAISS search -> exactly 200 unseen items B_u
{q_uf}, one batched call ----> semantic FAISS rows -> exactly 200 unseen,
                                                       BPR-novel items S_u
stable concatenation B_u then S_u ----------------> exact 400-item union C_u

per-request quantile-normalized BPR and max-facet semantic scores
    -> shared validation-locked alpha -> one stable sort -> served ranking

sealed T natural pairs -> PairSupport before ranking + sPCE@10 after ranking
sealed T positives/lows -> NDCG@10, Recall@10, union recall, intrusion@10
```

Offline encoding, BPR fitting, adapter training, and index construction are not
part of serving latency. Online serving consists of two FAISS calls (one
collaborative row and one semantic batch of at most two rows), filtering and
fixed-quota backfill, adapter features, vectorized scores, fusion, and one final
sort.

## Representation

### Immutable item metadata vectors

Each movie is rendered exactly as

```text
{title} [SEP] {genres}
```

and encoded locally by the frozen
`sentence-transformers/all-MiniLM-L6-v2` checkpoint. The resulting 384-vector
is converted to float32 and L2-normalized:

```text
E_i = normalize(SentenceTransformer(metadata_i)).
```

Ratings, popularity, user IDs, and demographics do not enter `E_i`. The matrix
and its `faiss.IndexFlatIP` serialization are hashed before any alignment
training and must remain byte-identical through external verification.

### Collaborative representation

Only block `A` trains an implicit BPR model and a rating-aware BPR model. Each
has 64-dimensional user and item factors. For a later request, its collaborative
query combines the frozen trained user factor with the registered rating-
weighted aggregate of item factors from the currently available prefix; the
query-update weight is `0.5`. Both candidate BPR models, their normalizers, and
their indexes are built without `R`, `V`, or `T` labels. Validation relevance
selects one BPR identity; test preference never does. The selected item matrix
and index then remain immutable.

### Deterministic prefix-only facets

Liked prefix items have rating at least 4; disliked prefix items have rating at
most 2; rating-3 items are ignored. Repeated events are reduced to distinct
movie IDs before clustering. Let `P_u` be the liked set and
`F=min(2, |P_u|)`. Zero liked items fail closed; one liked item creates one
facet. For two facets:

1. Compute all liked-item cosine similarities in immutable `E`.
2. Choose the least-similar unordered pair. A tie is resolved by the
   lexicographically smallest ordered movie-ID pair. The lower-ID seed is
   canonical facet 0.
3. Assign every liked item to the center with highest cosine. An exact tie goes
   to the lower canonical facet index.
4. Replace each nonempty center by the normalized mean of its members.
5. Canonicalize nonempty clusters by their minimum member movie ID and repeat
   until assignments are unchanged or eight assignment/update iterations have
   completed.
6. If a cluster becomes empty, collapse to the single normalized mean of all
   liked items; do not re-seed.

Let `d_u` be the normalized mean of disliked item vectors, or the all-zero
vector if no disliked item exists. The raw query for canonical facet `f` is

```text
b_uf = normalize(mean(E_i for i in liked facet f) - 0.25 * d_u).
```

Also compute the normalized global liked centroid `l_u`. No current `R`, `V`,
or `T` item, target outcome, candidate outcome, ID, or demographic feature may
enter clustering or a query.

### Shared bounded query adapter

Every aligned method uses the same adapter family, shared across all users and
facets. Its input is restricted to

```text
h_uf = concat(
    b_uf,                         # 384
    global_liked_centroid,        # 384
    global_dislike_centroid,      # 384, zero when absent
    facet_member_count / liked_count,
    min(prefix_event_count, 200) / 200
)                                # total 1,154 values
```

The adapter is `Linear(1154,32) -> tanh -> Linear(32,384)`. The final weight
and bias are initialized to zero, so every aligned model starts exactly at its
raw query. With adapter output `a_uf=g(h_uf)`, the served aligned query is

```text
q_uf = normalize(b_uf + 0.25 * a_uf / max(1, ||a_uf||_2)).
```

Thus the pre-normalization displacement has norm at most `0.25`. Item vectors
and indexes never move; alignment changes only the request query.

## Fixed exact candidate generation

The PoC uses exact inner-product `faiss.IndexFlatIP` indexes so approximate
index recall cannot confound the result. Each request performs a collaborative
search at depth 700 and one semantic batch search at depth 700 per active
query.

### Collaborative branch

Scan the selected BPR row in returned order, discard prefix-seen and duplicate
movie IDs, and retain the first 200. Fewer than 200 is exhaustion and fails the
request and run; no target may be injected and no data-dependent second search
is permitted.

### Semantic branch

Discard prefix-seen items, every movie already in the collaborative branch,
and duplicates. A one-facet method takes the first 200 eligible items from its
single row. A two-facet method first fills canonical quotas of 100 each.
Duplicates visible to both rows are owned by the lower canonical facet that
first encounters them. From each row's unconsumed cursor, canonical round-
robin backfill (`facet 0`, then `facet 1`) supplies one eligible item at a time
until the total is exactly 200. Only the two already-returned depth-700 rows may
be used. Exhaustion fails closed.

The final candidate union is the stable concatenation

```text
C_u = B_u followed by S_u
```

with no post-union truncation. Therefore every hybrid request has exactly 200
distinct unseen collaborative items, exactly 200 distinct unseen and BPR-novel
semantic items, zero final branch overlap, and exactly 400 union items.
Retrieval multiplicity and the facet that first retrieved an item are logged
but never enter ranking.

## Shared scalar ranking and validation lock

For each 400-item union, compute the selected BPR dot-product score and the
semantic score

```text
sem(u,i) = max_f dot(query_uf, E_i),
```

where an exact max tie uses the lower canonical facet index. Normalize each
score vector independently on that request using a target-blind winsorized
quantile map:

```text
scale(x) = max(Q95(x) - Q05(x), 1e-6)
z(x_i) = clip((x_i - Q05(x)) / scale(x), 0, 1).
```

The single-centroid raw hybrid uses validation relevance to choose one
`alpha` from `[0.0, 0.25, 0.5, 0.75, 1.0]` after the BPR identity is locked.
All hybrid methods and controls then reuse exactly that alpha:

```text
score(u,i) = alpha * z(bpr(u,i)) + (1-alpha) * z(sem(u,i)).
```

Final score ties use ascending numeric movie ID. No method may tune a separate
fusion coefficient, normalizer, quota, margin, or checkpoint. The selected BPR
baseline serves its own 200-item collaborative ranking and is the explicit
non-hybrid exception.

## Reference-free preference alignment

### Method-independent natural pair corpus

For every cycle-4 user, publish the `R` request descriptor from the `A` prefix
before joining any `R` rating. After publication, form every unordered pair of
distinct naturally rated `R` items with an absolute rating gap of at least two;
the higher-rated endpoint is `chosen`. These items are not appended to a
candidate set. Pair IDs and directions are common to every aligned method.

Within each user, order pairs by
`SHA256("20263116:{user_id}:{low_movie_id}:{high_movie_id}")` and retain at
most 32. If more than 30,000 remain globally, order by within-user hash rank
first and then that pair hash, and retain 30,000. This round-aware cap gives
each pair-bearing user one opportunity before any user receives its second
pair. The uncapped corpus must independently satisfy the registered 5,000-pair
and 1,000-user floor. A pair is assigned to the raw facet with greatest cosine
to its chosen item; an exact tie uses the canonical facet index.

### Objective and weighting

For aligned queries and a natural pair `(i+,i-)`, define

```text
Delta = max_f dot(q_uf, E_i+) - max_f dot(q_uf, E_i-)
L_pair = softplus(beta * (margin - Delta)),
beta = 2.0, margin = 0.20.
```

This is a SimPO-inspired reference-free scalar margin objective. It has no DPO
reference policy, no reference-model forward pass, and no language-model
decoding. On each epoch the full objective first averages pair losses within
their assigned facet, then averages active facets within a user, then averages
pair-bearing users. At each epoch, users are ordered by
`SHA256("20263116:train:{seed}:{epoch}:{user_id}")` and numeric user ID, then
split into consecutive groups of 128; all aligned variants share the group
order, pair cap,
24 fixed epochs, AdamW schedule, learning rate `0.003`, weight decay `1e-4`,
and gradient-norm clip `1.0`. The final epoch is always served; there is no
early stopping or preference-based checkpoint selection.

The zero-margin control changes only `margin` to zero. The shuffled-direction
control orders a user's preserved pair IDs by the registered hash and reverses
exactly the even zero-based orientations, leaving odd orientations natural.
The pair-micro control changes only aggregation to one mean over all pairs.

## Registered methods and controls

| Method | Facets | Adapter | Training direction / weighting | Candidate budget |
|---|---:|---|---|---:|
| selected BPR | 0 | none | `A`-only BPR | 200 |
| single-centroid hybrid | 1 | raw | none | 200+200 |
| raw multi-facet | up to 2 | raw | none | 200+200 |
| single-query aligned | 1 | learned | natural, user-macro | 200+200 |
| multi-facet zero-margin | up to 2 | learned | natural, user-by-facet macro, margin 0 | 200+200 |
| multi-facet shuffled-direction | up to 2 | learned | alternating reversed, user-by-facet macro | 200+200 |
| multi-facet pair-micro | up to 2 | learned | natural, pair-micro | 200+200 |
| **FACET-PREF** | up to 2 | learned | natural, user-by-facet macro, margin 0.20 | 200+200 |

The mechanism core is the fixed `{single,multi} x {raw,aligned}` factorial.
Aligned controls share capacity, initialization rule, optimizer, batches,
epochs, item geometry, and pair IDs. All hybrids share BPR identity, alpha,
quantile map, retrieval depths, exact branch budgets, union rule, scalar fusion,
tie-breaking, and latency instrumentation. Raw methods intrinsically perform no
adapter training; that is their named factor.

## High-level pseudocode

```python
# A only; no R/V/T labels
E = l2_normalize(sentence_transformer.encode(title_sep_genres))
bpr_candidates = [train_implicit_bpr(A), train_rating_aware_bpr(A)]
I_sem = faiss.IndexFlatIP(384); I_sem.add(E)
I_cf = [faiss.IndexFlatIP(64).add(m.item_factors) for m in bpr_candidates]
freeze_hash(E, bpr_candidates, I_sem, I_cf)

def raw_facets(prefix, mode):
    liked = distinct(prefix.items_with_rating_at_least(4))
    disliked = distinct(prefix.items_with_rating_at_most(2))
    clusters = [liked] if mode == "single" else deterministic_spherical_2means(
        liked, least_similar_seed=True, max_iterations=8
    )
    d = normalize_or_zero(mean(E[disliked]))
    global_like = normalize(mean(E[liked]))
    return [normalize(mean(E[c]) - 0.25 * d) for c in clusters], global_like, d

def queries(prefix, mode, adapter=None):
    b, global_like, d = raw_facets(prefix, mode)
    if adapter is None:
        return b
    out = []
    for facet, b_f in enumerate(b):
        h = concat(b_f, global_like, d,
                   len(facet_members[facet]) / len(liked),
                   min(len(prefix), 200) / 200)
        a = adapter(h)
        out.append(normalize(b_f + 0.25 * a / max(1, norm(a))))
    return out

# Publish target-blind R descriptors before joining R ratings.
R_descriptors = publish_descriptors(prefix=A)
R_pairs = natural_rating_gap_pairs(join_R_after_publish(R_descriptors), gap=2)
R_pairs = prospective_round_aware_hash_cap(R_pairs, per_user=32, total=30000)

for seed in [20260827, 20260828, 20260829]:
    for variant in aligned_variants:
        adapter = zero_output_initialized_adapter(seed)
        for epoch in range(24):
            for user_group in common_hash_shuffled_user_groups(R_pairs, 128, seed, epoch):
                loss = variant_macro_loss(user_group, beta=2.0,
                                          margin=variant.margin)
                adamw_step(adapter, loss, lr=0.003, weight_decay=1e-4,
                           clip_norm=1.0)
        freeze_hash(adapter.final_epoch)

def retrieve_and_rank(user, prefix, method, alpha, selected_bpr):
    B_rows = I_cf[selected_bpr].search(cf_query(user, prefix), 700)
    B = first_exact_unique_unseen(B_rows, 200)
    Q = queries(prefix, method.facet_mode, method.adapter)
    S_rows = I_sem.search(stack(Q), 700)       # one batched semantic call
    S = fixed_quota_semantic(S_rows, seen=prefix.items, exclude=B,
                             quotas=[100, 100] if len(Q) == 2 else [200],
                             total=200)
    C = B + S
    assert len(B) == 200 and len(S) == 200 and len(C) == 400
    z_bpr = request_quantile_normalize(bpr_score(C), .05, .95)
    z_sem = request_quantile_normalize(max_facet_dot(Q, E[C]), .05, .95)
    score = alpha * z_bpr + (1-alpha) * z_sem
    return C, stable_sort(C, key=(-score, movie_id))

# V relevance only: lock selected_bpr, then one alpha on raw single-centroid.
# Freeze all choices; fix V pairs with the independent 20263121 hash and audit
# preference power without changing any choice.
# Publish and hash target-blind T manifests; then open T once.
raw = evaluate_fixed_T_pairs_and_relevance()
gates = recompute_G1_to_G9(raw)
PROMISING = all(gates.values())
```

## Evaluation surfaces and safety interpretation

Candidate quality is measured before ranking by user-macro natural-pair
co-support and positive-item union recall. Served preference is measured by
strict preference-consistent exposure at 10, where both-unshown pairs score
zero and tail-only reorderings earn no credit. Relevance and low-rating
intrusion remain independent gates. These are offline, exposure-conditioned
MovieLens estimands; missing items are unknown, not negative, and none of the
metrics is interpreted causally.

FACET-PREF is killed if any registered G1-G9 condition fails, including exact
budget, mechanism-control, support, power, seed, latency, or provenance gates.
There is no weighted rescue, threshold repair, or automatic outcome rerun.
