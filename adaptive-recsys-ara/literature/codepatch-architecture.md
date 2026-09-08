# Phase 3, Cycle 8: CODEPATCH-⊥ Algorithmic Architecture

Date: 2026-08-07

Status: architecture specification derived from the prospectively frozen
Phase-2 question; it does not authorize outcome access

## 1. Design objective and non-negotiable boundary

CODEPATCH-⊥ is a two-stage recommender in which the catalog representation and
its product-quantized index are immutable, while each user receives a tiny
compiled score-table patch. The patch participates in full-catalog candidate
generation rather than only reranking an already truncated list.

The architecture is intended to test one narrow mechanism:

> Can prefix-only feedback be compiled into a sparse utility program over
> frozen PQ codewords that is provably outside the score-table class reachable
> by every ordinary dense ADC query, and can that program improve admission of
> future preferred items within a strict byte and CPU-latency budget?

The novelty claim does not attach to SentenceTransformers, FAISS, product
quantization, table lookup, sparse interactions, user-history aggregation,
BPR, the pairwise loss, SimPO, or hybrid ranking. It attaches only to the
combination of:

1. a frozen item encoder, PQ codebook, code assignment, and catalog order;
2. a prefix-conditioned, support-restricted codeword patch;
3. exact projection of that patch outside the dense-query ADC table subspace;
4. execution of the patch during compact-code candidate generation; and
5. reference-free preference learning without an item/index rebuild.

No item vector, centroid, PQ code, index membership, or catalog order may
depend on a rating. No online LLM is in the serving path. Full PQ tuples may
not be used as item identifiers or utility-table keys.

## 2. System overview

The system has four data planes and two materially different clocks:

~~~text
IMMUTABLE CATALOG BUILD (offline, outcome-free)
 movies.dat
     -> canonical title + genre text
     -> frozen SentenceTransformer -> normalized 384-D item vectors
     -> FAISS IndexPQ(384, 24, 8)
     -> frozen centroids C, item codes z, ordered IDs, serialized index
                                     |
                                     v
INTERACTION UPDATE / PATCH COMPILATION (after a legal prefix changes)
 prefix-only user log
     -> rating-weighted aggregation of frozen item vectors -> dense query q_u
     -> signed/recency codeword statistics f1..f4
     -> deterministic 21-codeword supports
     -> shared generator theta -> raw utilities
     -> support-restricted orthogonal projection -> <=63-entry patch delta_u
                                     |
                                     v
REQUEST-TIME CANDIDATE GENERATION (no encoder, training, or LLM)
 q_u + delta_u + frozen C,z + seen mask
     -> exact compact-code scan -> 100 semantic candidates
                                     |
                                     +------> metrics on pre-label candidates
                                     |
                                     v
FINAL RANKING
 semantic top 100 UNION BPR-MF top 100
     -> prefix/catalog-only score standardization
     -> validation-frozen alpha fusion
     -> final top 10

REFERENCE-FREE TRAINING (R only)
 natural chosen/rejected pairs + target-blind prefix states
     -> fixed-margin SimPO-derived logistic loss
     -> one theta checkpoint per registered seed and method
~~~

The expensive sentence encoder and patch compiler are absent from a warmed
retrieval request. A request loads the already compiled dense query, sparse
patch, seen-item mask, and frozen serving artifacts.

## 3. Representation with SentenceTransformers

### 3.1 Item representation

For movie i, construct one canonical UTF-8 string:

~~~text
item_text_i = title_i + " [SEP] " + pipe_separated_genres_i
~~~

Encode strings in frozen catalog order with
sentence-transformers/all-MiniLM-L6-v2. The encoder is in evaluation mode;
weights, tokenizer, pooling rule, package version, input bytes, batch order,
and output order are bound in the artifact manifest. Let the encoder output be
x_i in R^384. Store:

~~~text
e_i = x_i / max(||x_i||_2, epsilon)
E = [e_1; ...; e_N] in float32, N = 10,681
~~~

The frozen dense matrix is 10,681 x 384 x 4 = 16,406,016 bytes and is the
registered semantic-storage denominator. It is retained as a build/audit
artifact but is not required by the compact-code request path.

### 3.2 Interaction-log representation

The same item embedding space represents the semantic content of the user
log; there is no separately fine-tuned user-text encoder. For a legal prefix
H_u sorted by timestamp and source ordinal, define positive and negative sets
using only available ratings:

~~~text
y(r) = +1 for r >= 4.0
       -1 for r <= 2.5
        0 otherwise
~~~

The dense log feature is the normalized rating-aware aggregation of the
constituent SentenceTransformer item vectors:

~~~text
mu_pos = mean(e_i for prefix events with y(r)=+1)
mu_neg = mean(e_i for prefix events with y(r)=-1)
h_u    = mu_pos - 0.5 * mu_neg
q_u    = h_u / max(||h_u||_2, epsilon)
~~~

If the prefix contains no negative, h_u = mu_pos. Structural/A-screening
requirements guarantee positive evidence for every selected user. This gives
the FAISS ADC branch a 384-dimensional dense user-log vector while keeping
every catalog embedding frozen.

The prefix is also encoded in the discrete PQ domain. For prefix event j,
rho_j = (j+1)/|H_u| and z_jm is the immutable codeword of its item in
subquantizer m. For each (m,k), compute exactly the four registered features:

~~~text
count_mk = sum_j 1[z_jm=k]
f1 = sum_j 1[z_jm=k] y(r_j) / sqrt(1 + count_mk)
f2 = sum_j 1[z_jm=k] y(r_j) rho_j /
     sqrt(1 + sum_j 1[z_jm=k] rho_j^2)
f3 = sum_j 1[z_jm=k] (r_j - 3.0) / max(1, count_mk)
f4 = tanh(sum_j 1[z_jm=k] y(r_j) / 2) * log1p(count_mk)
~~~

Together, q_u and f_u in R^(24 x 256 x 4) are the complete semantic/log
representation used by CODEPATCH. Exact zeros stay zero. User ID, movie ID,
current-stage identity or rating, candidate membership, BPR score, and outcome
counts are forbidden features.

## 4. Frozen product-quantized catalog

Train one deterministic inner-product FAISS IndexPQ with:

~~~text
D = 384 dimensions
M = 24 subquantizers
K = 256 codewords per subquantizer (8 bits)
d_m = D/M = 16 dimensions
code size = M bytes = 24 bytes per item
~~~

Let C_m in R^(256 x 16) be subquantizer m's centroid matrix and
z_i in {0,...,255}^24 be item i's code. Freeze and hash:

- canonical movie IDs and item texts;
- the normalized item matrix and encoder identity;
- all C_m and z_i;
- the serialized IndexPQ;
- every extracted code array or scan accelerator;
- package versions, thread settings, and build configuration.

Each unpatched ADC table is:

~~~text
B_u,m[k] = dot(q_u[m], C_m[k])
~~~

Allowing a subquantizer-specific constant, every dense-query score table lies
in col(A_m), where A_m = [C_m, 1] has at most 17 columns. CODEPATCH uses the
orthogonal complement of this table class.

The canonical candidate generator is not approximate FAISS search. It is an
exact deterministic scan of all frozen item codes. FAISS IndexPQ.search is
still run as a separately reported library baseline, but it is not the
latency-ratio denominator and cannot replace the canonical scorer.

An outcome-free API replay on the frozen item matrix found that the complete
`[C_m,1]` matrices for subquantizers 7, 13, and 19 have numerical rank 16 at
the registered tolerance; no support replacement can raise them to 17. They
are therefore globally ineligible exactly as the Phase-2 rule requires. The
other subquantizers remain candidates, and every request must still supply at
least three rank-17 supports. This observation uses item geometry only and is
not recommendation evidence.

## 5. Prefix-to-patch compiler

### 5.1 Support construction

For every subquantizer m:

1. rank observed codewords by descending |f1|+|f2|, then descending count,
   then ascending codeword ID;
2. extend the list using catalog frequency descending, then codeword ID
   ascending, skipping duplicates, and take the first 21 as the initial ordered
   support;
3. if its rank is below 17, traverse unused codewords in that same frozen
   frequency order and, for each, test replacement positions from weakest to
   strongest support priority. Accept the first replacement that strictly
   increases rank, restart the unused traversal, and stop at rank 17. If no
   rank-increasing replacement exists, reject the subquantizer. Rank is always
   computed by float64 SVD with relative tolerance
   sigma_j/sigma_1 >= 1e-6;
4. reject m if a legal rank-17 support cannot be formed.

On each final support S_u,m, project f1 and select the three eligible
subquantizers with largest projected L2 norm, breaking ties by m. Support
selection uses only the prefix and frozen catalog statistics. It is completed
before the current-stage labels are opened.

### 5.2 Shared generator and exact orthogonalization

For seed s, learn one shared no-bias generator theta_s in R^(24 x 4). On a
selected support:

~~~text
r_u,m[k] = sum_(ell=1)^4 theta_s[m,ell] f_ell(u,m,k)
~~~

Compute the projector only after the final support is known:

~~~text
A_u,m = [C_m[S_u,m], 1] in R^(21 x 17)
U, sigma, Vt = svd_float64(A_u,m, full_matrices=false)
P_u,m = I_21 - U[:,0:17] U[:,0:17]^T
delta_u,m[S_u,m] = P_u,m r_u,m[S_u,m]
delta_u,m[not in S_u,m] = 0
~~~

Projecting globally and pruning afterward is forbidden because pruning can
destroy orthogonality. Since each chosen support has rank 17, P_u,m has rank
four. For zero-filled delta:

~~~text
A_m^T delta_u,m = A_u,m^T delta_u,m[S_u,m] = 0
~~~

Concatenate the three active subquantizer patches and apply the fixed cap:

~~~text
delta_u = delta_raw * min(1, 1 / max(||delta_raw||_2, 1e-12))
~~~

This positive scalar preserves orthogonality. A request contains at most
3 x 21 = 63 (m,k,value) entries. A nonzero patch is therefore outside every
dense-query-plus-constant score table at the codeword-table level. A separate
catalog-restricted residual audit projects the induced N-vector of patch
scores onto [PQ_reconstruction, 1], but that diagnostic is not promoted into
a formal catalog-level claim.

### 5.3 Serialization and replay

Persist the selected subquantizers, ordered supports, float patch values,
generator/checkpoint identity, prefix hash, and cap factor. On load, reconstruct
each projector from serialized supports and serving centroids, then repeat:

- finite-value and exactly-17-direction checks;
- max_m ||A_u,m^T delta_u,m[S]||_inf <= 1e-5;
- exact zero outside support and at most 63 stored entries;
- ||delta_u||_2 <= 1;
- immutable catalog/index hash checks;
- score replay within 1e-5 absolute error.

A compiler or replay violation is fatal. The system must not silently replace
an invalid patch with a zero patch.

## 6. Reference-free SimPO-derived alignment

CODEPATCH uses the fixed-margin, reference-free idea from SimPO but applies it
to scalar recommendation scores. It does not train or serve a DPO reference
model and does not require reference-policy log probabilities.

Within R, construct only natural prefix-unseen preference pairs whose ratings
differ by at least 1.5. The higher-rated endpoint is chosen. Deduplicate
user-item observations by retaining the latest R event, hash-order the pairs,
and retain at most 64 per user.

For chosen item i+ and rejected item i-, optimize:

~~~text
margin_u = score_theta(u,i+) - score_theta(u,i-)
loss_u,pair = softplus(beta * (gamma - margin_u))

beta  = 2
gamma = 0.10
~~~

Average within user before averaging across users so prolific raters do not
dominate. Train independent seeds 20260881, 20260882, and 20260883 with Adam,
learning rate 0.02, weight decay 1e-4, gradient clipping at 1.0, 20 epochs,
lambda_train=1, and checkpoints at epochs 5, 10, and 20.

Validation selects one common (epoch, lambda) across seeds for each trainable
method using seed-averaged user-macro full-catalog pair accuracy:

~~~text
epoch in {5,10,20}
lambda in {0.05,0.10,0.20,0.40}
~~~

Ties prefer the smaller epoch, then smaller lambda. No lambda-specific
retraining and no seed selection are allowed. The loss supplies preference
alignment without DPO's extra frozen-reference forward pass, but SimPO itself
is not claimed as a research contribution.

## 7. Candidate generation and final ranking

For every prefix-unseen catalog item:

~~~text
s_cp(u,i) = sum_(m=1)^24 [
    dot(q_u[m], C_m[z_i,m])
    + lambda * delta_u,m[z_i,m]
]
~~~

The scanner computes the base 24 table lookups plus a zero/default or sparse
patch lookup for each item, masks prefix-seen items, and returns exactly 100.
Equal scores are ordered by numeric movie ID. Because the patch is evaluated
before top-k truncation, it can change candidate membership.

An unchanged 64-dimensional BPR-MF branch provides a standard collaborative
comparator and hybrid component. It is trained from A positives only for eight
AdamW epochs, batch size 2,048, learning rate 0.025, weight decay 1e-4, one
deterministic uniformly sampled unobserved item per positive, factor
initialization standard deviation 0.05, and the same three seeds. Unobserved
items are sampled negatives, not asserted dislikes.

At a later prefix, BPR's request vector is the frozen A-user factor plus 0.5
times the rating-weighted mean of available-prefix item factors, with weight
clip((rating-3)/2,-1,1). Semantic seed s pairs only with BPR seed s.

For each registered semantic method:

1. union its 100 candidates with the corresponding BPR top 100;
2. standardize each branch using prefix/catalog scores only;
3. assign the registered floor to missing branch membership;
4. score alpha * BPR + (1-alpha) * semantic;
5. return ten items with numeric-ID tie breaking.

After (epoch, lambda) freezes, V selects alpha from {0,.25,.5,.75,1} for each
method by seed-averaged NDCG@10, with ties favoring the smaller alpha. T never
selects a seed, method, control, checkpoint, scale, or fusion weight.

## 8. Exact registered controls

The implementation must retain every control; a weak or failed control may not
be removed after validation or test access.

1. Popularity and the specified 64-dimensional BPR-MF standard baselines.
2. Full-float exact SentenceTransformer retrieval and frozen PQ/ADC.
3. A rank-4 low-rank dense query adapter trained on the same R pairs.
4. A globally dense pQCF-style table. On support S, compute
   eta = pinv(A_u,m) r_u,m[S] with the same SVD tolerance, then set all 256
   entries to [C_m,1] eta. Project-on-S followed by zero-fill is forbidden.
5. An unprojected sparse 63-entry LUT with identical support and training.
   This is the closest no-orthogonalization ablation, not a strict parameter
   superset because CODEPATCH's projector varies by user.
6. A rank-matched sparse random four-dimensional support subspace using the
   frozen support-hashed PCG64 seed, float64 QR, and canonical column signs.
7. A label-blind user-shuffled CODEPATCH patch under the prospectively frozen
   fixed-point-free cohort permutation.
8. CODEPATCH rerank-only: frozen PQ retrieves 512, then the identical patch
   reranks only that set and returns 100.
9. Patch-only scoring with the ADC term removed.

All trainable semantic controls use the same seeds, natural pair pool,
user-macro weighting, optimizer budget, checkpoints, validation access, and
test barrier. Report each method's parameter count, candidate work, bytes, and
latency. SparCode remains an architectural collision/system reference rather
than a quietly substituted matched control: it jointly learns codes and an
interaction index, whereas this experiment freezes both.

## 9. High-level pseudocode

~~~python
def build_frozen_catalog(movies, encoder):
    texts, movie_ids = canonicalize_title_genres(movies)
    E = l2_normalize(encoder.encode(texts)).astype(float32)
    pq = train_deterministic_indexpq(E, d=384, M=24, nbits=8,
                                     metric="inner_product")
    codes = extract_codes(pq, E)               # uint8 [N,24]
    C = extract_centroids(pq)                  # float32 [24,256,16]
    freeze_hash_bind(texts, movie_ids, E, pq, codes, C)
    return FrozenCatalog(movie_ids, pq, codes, C)


def encode_prefix(prefix, frozen):
    # Every identity/rating below is already legal in the available prefix.
    events = stable_timestamp_ordinal_sort(prefix)
    pos = [frozen.embedding[e.item] for e in events if e.rating >= 4.0]
    neg = [frozen.embedding[e.item] for e in events if e.rating <= 2.5]
    h = mean(pos) - (0.5 * mean(neg) if neg else 0)
    q = l2_normalize(h)
    f = exact_codeword_features(events, frozen.codes)  # [24,256,4]
    return q, f


def choose_supports(f, C, frozen_frequency_order):
    eligible = []
    for m in range(24):
        S = history_first_fill_to_21(f[m], frozen_frequency_order[m])
        S = deterministic_repair_until_rank17(S, C[m], rtol=1e-6)
        if S is None:
            continue
        A = append_ones(C[m, S]).astype(float64)        # [21,17]
        P = eye(21) - svd_rank17_U(A) @ svd_rank17_U(A).T
        eligible.append((norm(P @ f[m,S,0]), m, S))
    return largest_three_with_m_tiebreak(eligible)


def compile_patch(prefix, theta, frozen):
    q, f = encode_prefix(prefix, frozen)
    patch = zeros([24,256], dtype=serving_float)
    supports = choose_supports(f, frozen.C, frozen.frequency_order)
    require(len(supports) == 3)
    for _, m, S in supports:
        A = append_ones(frozen.C[m,S]).astype(float64)
        U, sigma, Vt = svd(A, full_matrices=False)
        require(retained_rank(sigma, relative_tol=1e-6) == 17)
        P = eye(21) - U[:,:17] @ U[:,:17].T
        raw = f[m,S,:] @ theta[m,:]
        patch[m,S] = cast_serving(P @ raw)
    patch *= min(1.0, 1.0 / max(l2_norm(patch), 1e-12))
    serialized = serialize_sparse(q, patch, supports, prefix_hash(prefix))
    reconstruct_and_audit(serialized, frozen, atol=1e-5)
    return serialized


def score_all_codes(compiled, frozen, lambda_):
    q, sparse_patch, seen = load_and_verify(compiled)
    base_table = einsum("md,mkd->mk", q.reshape(24,16), frozen.C)
    scores = zeros(frozen.N)
    for i in range(frozen.N):
        scores[i] = sum(
            base_table[m, frozen.codes[i,m]]
            + lambda_ * sparse_patch.get((m, frozen.codes[i,m]), 0.0)
            for m in range(24)
        )
    scores[seen] = -infinity
    return stable_topk(scores, k=100, secondary_key=frozen.movie_ids)


def train_reference_free(seed, R_pairs, A_prefix_states, frozen):
    theta = initialize_registered_theta(seed)
    for epoch in range(1, 21):
        for users in deterministic_user_macro_batches(R_pairs, seed):
            loss = 0
            for u in users:
                compiled = differentiable_compile(
                    A_prefix_states[u], theta, frozen)
                pair_losses = []
                for chosen, rejected in capped_pairs(R_pairs[u], 64):
                    gap = score(compiled, chosen) - score(compiled, rejected)
                    pair_losses.append(softplus(2.0 * (0.10 - gap)))
                loss += mean(pair_losses)
            loss /= len(users)
            adam_step(theta, loss, lr=0.02, weight_decay=1e-4,
                      gradient_clip=1.0)
        if epoch in {5,10,20}:
            hash_bound_checkpoint(theta, seed, epoch)
    return checkpoints
~~~

Implementation note: support selection and SVD projectors are functions of the
prefix and frozen catalog, not trainable parameters. Gradients flow through the
fixed projector into theta. A production implementation should batch table
construction and vectorize the code scan; it must reproduce the canonical
loop's scores and ordering.

## 10. Complexity, storage, and latency contract

Use N=10,681, D=384, M=24, K=256, d=16, support S=21, active
subquantizers J=3, and output k=100.

| Operation/artifact | Asymptotic cost or size | Registered interpretation |
|---|---:|---|
| Offline item encoding | O(N * encoder cost) | Build-only; no request-time encoder. |
| Dense item matrix | N D 4 = 16,406,016 bytes | Exact G6 denominator. |
| Raw item codes | N M = 256,344 bytes | Charged if separately materialized. |
| Raw float32 centroids | M K d 4 = 393,216 bytes | Charged for every serving copy. |
| Observed serialized IndexPQ | 649,646 bytes | Must be remeasured and hash-bound. |
| Base ADC table | M K dot products of width d | Request-local scratch; table construction is timed. |
| Canonical scan | O(NM + N log k) | Exact all-code scoring and stable top 100. |
| Patch lookup work | O(NJ) effective nonzero-table additions | Still execute/replay via the identical canonical scan. |
| Patch support/value payload | at most 63 entries | Report exact payload and container/metadata bytes. |
| Patch compilation | O(M S 17^2) small SVD work plus prefix aggregation | Precompiled on update; p95 must be <=10 ms. |
| Pair training | O(epochs * retained pairs * M) score-table work | Offline R-only training. |

The byte numerator is the serialized IndexPQ plus every additional
serving-required code array, centroid copy, CSR/inverted accelerator, lookup
metadata, or duplicate. It must be at most:

~~~text
16,406,016 / 8 = 2,050,752 bytes
~~~

Common ordered IDs, prefix-seen masks, and BPR data are reported separately
and excluded symmetrically. User patch storage is also reported separately,
including support, (m,k), values, length fields, alignment, and container
overhead; a payload-only estimate is insufficient.

For latency, use one registered CPU thread, warmed artifacts, an interleaved
request schedule, and identical timing boundaries from ADC-table construction
through seen masking and top-100 materialization. The zero-patch denominator
uses the same scanner, code array, stable top-k, thread count, and
materialization. CODEPATCH must achieve:

~~~text
p95_CODEPATCH <= 1.25 * p95_identical_zero_patch_scan
p95_CODEPATCH <= 1.0 ms
p95_patch_compilation <= 10 ms
~~~

FAISS IndexPQ.search latency is reported separately. It cannot satisfy or fail
the relative-latency gate.

## 11. Leakage-safe stage execution

The runner is a one-way state machine:

~~~text
SOURCE/DENYLIST VERIFY
  -> STRUCTURAL LAYOUT MANIFEST
  -> A-ONLY SCREENING + 5,000-USER COHORT MANIFEST
  -> A ARTIFACTS + R PREFIX/SUPPORT MANIFESTS
  -> R JOIN + PAIRS + TRAINING
  -> V PRE-LABEL CANDIDATE/SCORE MANIFESTS
  -> V JOIN + FREEZE ALL METHOD CONFIGURATIONS
  -> PROSPECTIVE POWER CHECK
  -> T PRE-LABEL CANDIDATE/SCORE/LATENCY MANIFESTS
  -> ONE T JOIN
  -> SEALED RESULT
  -> INDEPENDENT POST-EXIT VERIFIER
~~~

- Before A/R/V/T, reconstruct and verify the 6,170-ID conservative prior-user
  denylist and every registered source hash. Any mismatch stops before cohort
  access.
- A builds BPR item models, user states, supports, representation artifacts,
  and target-blind R prefix/support manifests.
- R supplies training labels only after all R prefix/support manifests are
  durable.
- V candidate and score manifests use A+R history and must exist before V is
  joined. V freezes a configuration for every method; no method is dropped.
- The prospective V-based power calculation must pass before T access.
- T states use A+R+V. All T candidates, scores, rankings, supports, patches,
  latency request IDs, and immutable hashes become durable before the one T
  join.

Current-stage item identities, ratings, pair counts, and outcomes may not
affect current-stage work, support, candidates, tie breaks, latency sampling,
or method identity.

## 12. Failure semantics and authorization

The PoC is an authenticated falsification test, not an iterative benchmark.
Only the separate post-exit verifier may publish a promising marker. It must
recompute the entire frozen G1-G9 conjunction, including:

- at least +0.010 simultaneous-bound gains over the best matched compressed
  control in both CPE@100 and FutureLikedRecall@100;
- future-liked retention, pre-truncation rescue, projection, closest-control,
  hybrid safety, seed-stability, support, and power requirements;
- every representation, support, rank, orthogonality, replay, candidate,
  prefix, stage, finite-value, source, byte, and latency invariant;
- complete hash-bound provenance and an empty asynchronous error ledger.

False, missing, nonfinite, underpowered, unsupported, or unauthenticated means
failure. Exceptions and partial outputs mean failure. A failed projector is
not replaced, a threshold is not weakened, a cohort is not enlarged, a control
is not removed, and the test is not resumed or rerun after T is opened.

If any gate fails, CODEPATCH-⊥ is killed immediately, its negative result is
recorded, Phase 5 remains forbidden, and the research sprint returns to Phase
1 with a materially different architecture. Phase 5 becomes permissible only
when the external verifier authenticates every gate as true.
