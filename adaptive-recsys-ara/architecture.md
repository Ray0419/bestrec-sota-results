# Phase 3: RIPPLE Algorithm and System Architecture

## Design objective

RIPPLE moves a compact, reference-free preference policy into the dense-retrieval query path. Item vectors and the FAISS index are immutable during preference updates. Training samples the confusions produced by the deployed index; serving uses one adapted query for both ANN candidate generation and exact candidate reranking.

## Pipeline

```text
item title + genres ── frozen SentenceTransformer ── normalize ── item matrix V
                                                                      │
                                                                      ├── train-once FAISS IVF-IP index
                                                                      │
chronological interaction log ── rating/recency aggregation ── q0(u,t)│
                                                       │              │
                                                       └─ low-rank adapter Aφ ── qφ(u,t)
                                                                 │
                       actual FAISS boundary ── hard confusions ──┤
                       explicit ratings ── chosen/rejected pairs ─┤
                                                                 ▼
                                                     reference-free SimPO loss
                                                                 │
                                                                 ▼
request ── qφ ── ambiguity router ── FAISS(nprobe low/high) ── top K candidates
                                                              │
                                                              └─ exact qφ·vi rerank ── top N
```

The prototype uses FAISS locally. Pinecone is a deployment substitute when managed sharding, replication, namespaces, and online catalog updates are required; the logical API remains `upsert(frozen_item_id, vector)` followed by metadata-filtered maximum-inner-product query. The experiment uses FAISS so the index bytes, `nprobe`, and latency are directly controlled.

## 1. Representation with Sentence Transformers

For item (i), construct metadata text

\[
x_i = \texttt{title}_i\;[\mathrm{SEP}]\;\texttt{genres}_i.
\]

A frozen `sentence-transformers/all-MiniLM-L6-v2` encoder produces

\[
v_i = \operatorname{normalize}(f_\theta(x_i)) \in \mathbb{R}^{384}.
\]

The PoC caches the float32 matrix and its SHA-256 fingerprint. At scale, embeddings are produced in batches, versioned by model and text-template hash, and stored once per item.

An interaction log is encoded through its referenced item vectors. For user (u) at time (t), let (P_{u,t}) contain earlier ratings at least four and (D_{u,t}) contain ratings at most two. The full architecture permits the base user vector

\[
q^0_{u,t} = \operatorname{normalize}\left(
 \sum_{j\in P_{u,t}} w^+_{ujt}v_j
 - \rho\sum_{j\in D_{u,t}} w^-_{ujt}v_j
\right),
\]

where weights combine rating strength and an optional exponential recency decay. To keep the first falsification test minimal, PoC v1 fixes (rho=0) and uniform positive weights: a normalized positive-item centroid. Scaled experiments must restore and ablate recency and negative terms. This satisfies the representation requirement without serializing a user's entire history through an online LLM.

## 2. Query-only preference policy

The trainable policy is a low-rank residual adapter:

\[
q^\phi_{u,t}=\operatorname{normalize}\left(q^0_{u,t}+
U\tanh(Vq^0_{u,t})\right),
\]

where (V\in\mathbb{R}^{r\times d}), (U\in\mathbb{R}^{d\times r}), and (r\ll d). Only (2dr) parameters change. An anchor penalty limits destructive rotation:

\[
\mathcal{L}_{anchor}=1-\langle q^\phi,q^0\rangle.
\]

The item encoder (f_\theta), matrix (V), IVF centroids, inverted lists, and item IDs are frozen.

## 3. FAISS candidate generation and index-conditioned pairs

All normalized (v_i) are added once to an `IndexIVFFlat` using inner product. Cosine ranking is therefore maximum inner product. A flat inner-product index is retained as an audit oracle on the PoC catalog.

At the start of each training refresh, the current (q^\phi) queries the same IVF configuration used by serving. For each known positive (i^+):

1. use explicit ratings (\le 2) as high-confidence rejected items when available;
2. collect unobserved high-scoring candidates returned by FAISS as *retrieval confusions*, not asserted dislikes;
3. form a matched number of pairs for the random-negative ablation;
4. log the fraction of pairs actually obtained from the ANN boundary and all fallbacks.

This makes approximation artifacts and candidate censoring visible to training. The nondifferentiable retrieval step is outside backpropagation; gradients flow through query and item scores only.

## 4. Ranking and reference-free SimPO alignment

Define a one-step item policy over any comparison set (C):

\[
\pi_\phi(i\mid u,C)=
\frac{\exp(s_\phi(u,i)/\tau)}{\sum_{j\in C}\exp(s_\phi(u,j)/\tau)},
\quad s_\phi(u,i)=\langle q^\phi_u,v_i\rangle.
\]

For a chosen/rejected pair, the log-normalizer cancels:

\[
\log\pi_\phi(i^+\mid u,C)-\log\pi_\phi(i^-\mid u,C)
=\frac{s_\phi(u,i^+)-s_\phi(u,i^-)}{\tau}.
\]

RIPPLE applies the SimPO target-margin objective without a reference policy:

\[
\mathcal{L}_{pref}=-a_{u,+,-}\log\sigma\left(
\beta\frac{s_\phi(u,i^+)-s_\phi(u,i^-)}{\tau}-\gamma_{+,-}
\right).
\]

Here (a_{u,+,-}) is a preregistered reliability weight. Explicit low ratings use the highest weight; unobserved retrieval confusions use a lower weight because non-exposure is not proof of dislike. The total loss is

\[
\mathcal{L}=\mathbb{E}[\mathcal{L}_{pref}]+\lambda\mathcal{L}_{anchor}.
\]

Unlike DPO, no reference-model scores or reference-model memory are required. Unlike an LLM reranker, the online rank score is one dot product. The formulation is an adaptation of SimPO to a one-step retrieval policy; SimPO itself is not claimed as novel.

## 5. Decision-aware ANN effort

Before retrieval, compute an ambiguity feature from information already available in the query path:

\[
a(u,t)=\alpha\left(1-\langle q^\phi,q^0\rangle\right)
 +(1-\alpha)\operatorname{dispersion}(\{v_j:j\in P_{u,t}\}).
\]

A small router is fit only on training/validation prefixes to predict the measured benefit of high versus low probing from adapter displacement, history dispersion, and history length. Validation users set a threshold (T) and high-probe fraction under the registered latency budget. Serving makes exactly one ANN call:

\[
nprobe(u)=
\begin{cases}
n_{high}, & a(u,t)>T\\
n_{low}, & \text{otherwise}.
\end{cases}
\]

The retrieved (K) items are exactly reranked by (q^\phi\cdot v_i), excluding observed positive-history items. The router is deliberately simple: the research question is whether preference uncertainty is a useful budget-allocation signal, not whether a large router can overfit a small benchmark.

## High-level pseudocode

```python
# OFFLINE: immutable catalog representation
V = normalize(SentenceTransformer.encode(item_title_and_genres))
index = faiss.IndexIVFFlat(IP, nlist)
index.train(V)
index.add_with_ids(V, item_ids)
catalog_fingerprint = sha256(V, serialize(index))

# TEMPORAL training examples
for user in users:
    for next_positive in train_positive_events(user):
        q0 = history_vector(events_before(next_positive), V)
        chosen = next_positive.item
        random_rejected = matched_random_negative(user)
        boundary_rejected = retrieve_confusion(index, adapter(q0))
        save_matched_pair(q0, chosen, random_rejected, boundary_rejected)

# MATCHED alignment variants
for variant in [RANDOM_NEGATIVE, INDEX_BOUNDARY]:
    initialize_same_adapter_seed()
    for epoch in range(E):
        if variant == INDEX_BOUNDARY:
            refresh_pairs_from_serving_index()
        for q0, chosen, rejected, reliability in batches:
            q = normalize(q0 + U @ tanh(W @ q0))
            delta = dot(q, V[chosen]) - dot(q, V[rejected])
            loss = -reliability * logsigmoid(beta * delta / tau - gamma)
            loss += anchor_weight * (1 - dot(q, q0))
            update(U, W)

# ONLINE
q0 = history_vector(user_history, V)
q = adapter(q0)
nprobe = high if ambiguity(q0, q, user_history) > threshold else low
candidates = index.search(q, K, nprobe=nprobe)
ranking = exact_dot_product_rerank(q, V[candidates])
assert sha256(V, serialize(index)) == catalog_fingerprint
return ranking[:N]
```

## Computational profile

| Operation | Frozen dense baseline | RIPPLE |
|---|---:|---:|
| Item encoding | (O(|I|\,C_{ST})), once | identical, once |
| Index build | once | identical, no alignment rebuild |
| User transform | (O(d)\) aggregation | (O(d)+O(dr)) adapter |
| ANN | fixed `nprobe` | one query, routed low/high `nprobe` |
| Candidate rerank | (O(Kd)) | (O(Kd)) |
| Reference policy during training | none | none |
| Online LLM decode | none | none |

## Required ablations

1. Frozen history-centroid SentenceTransformer + FAISS.
2. Popularity and BPR matrix-factorization standard baselines.
3. Matched random-negative low-rank adapter.
4. Matched exact full-matrix hard-negative adapter.
5. RIPPLE with boundary pairs but fixed `nprobe`.
6. Full RIPPLE with ambiguity-routed `nprobe`.
7. Exact flat search versus IVF to isolate ANN approximation.
8. Optional removal of the target margin, anchor penalty, and explicit-negative reliability weighting.

## Failure conditions

RIPPLE is not useful if gains disappear against matched random or exact hard-negative training, arise only under sampled-candidate evaluation, trail BPR-MF by more than the registered tolerance, require index mutation, violate the p95 budget, increase future-window dislike intrusion, or depend on test-informed thresholds. Any such result triggers the Phase 4 kill rule.

For a one-step item policy, the SimPO-derived objective is algebraically a target-margin-shifted BPR/RankNet loss. The work therefore claims a systems composition and training protocol, not a new preference-loss family.
