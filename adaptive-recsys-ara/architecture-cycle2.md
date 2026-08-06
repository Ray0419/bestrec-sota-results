# Phase 3, Cycle 2: CAPER Architecture

## Design pivot

RIPPLE tried to make a semantic query replace collaborative retrieval. CAPER makes the collaborative branch immutable and additive: semantic retrieval may expand the served support, and preference alignment may propose rank changes, but neither may delete BPR candidates or exceed a per-request collaborative-regret budget.

## System pipeline

```text
MovieLens title + genres ── SentenceTransformer ── normalized semantic item matrix ── FAISS-sem
ratings in core block ── BPR / rating-aware BPR ── user + item factors ─────────────── FAISS-cf
          │                                      │
          └─ positive/negative metadata centroids│
                                                 ▼
request ── parallel FAISS-cf top Kb + FAISS-sem top Ks ── immutable union C(u)
                                                               │
alignment rating-gap pairs from actual earlier unions ── SimPO residual scorer
                                                               │
                                                               ▼
                                           proposed residual ranking over C(u)
                                                               │
                                      collaborative-regret feasible projection
                                                               │
                                                               ▼
                                                        final top 10
```

## Representation

For item metadata `"{title} [SEP] {genres}"`, a frozen `sentence-transformers/all-MiniLM-L6-v2` encoder produces normalized vector `e_sem(i)` in 384 dimensions. Ratings in the chronological core block train two collaborative baselines: implicit BPR and rating-aware BPR. Their item factors `e_cf(i)` and user factors `q_cf(u)` are fixed before preference alignment.

The semantic user state uses only the available prefix:

\[
q_{sem}(u,t)=\operatorname{norm}\left(
\operatorname{mean}_{r\ge4} e_{sem}(i)
-0.25\operatorname{norm}\left(\operatorname{mean}_{r\le2} e_{sem}(i)\right)
\right).
\]

The PoC registers `rho=0.25`; an absent dislike history contributes the zero vector, and no target event enters either centroid. The collaborative query is refreshed from the same available prefix by adding a registered rating-weighted aggregate of frozen item factors to the trained user vector. Item factors and indexes never change.

## Candidate generation with FAISS

Use two immutable maximum-inner-product FAISS indexes:

\[
B_u=\operatorname{FAISS}_{cf}(q_{cf}(u),K_b),\qquad
S_u=\operatorname{FAISS}_{sem}(q_{sem}(u),K_s).
\]

The served union is

\[
C_u=B_u\cup S_u.
\]

Deduplication is stable and never truncates an item from `B_u`. With the registered `K_b=K_s=200`, the variable-size union contains at most 400 items and `B_u` is a subset of `C_u` for every request. Candidate recall is therefore compared as `Recall(C_u)` versus `Recall(B_u)` at the registered collaborative branch budget, not mislabeled as two Recall@200 lists. This is a candidate-set invariant only; true relevance and top-rank safety remain empirical questions.

At MovieLens-1M scale the PoC uses `IndexFlatIP` to remove approximation as a confound. At larger scale the same contract uses IVF/HNSW/Pinecone branches with per-branch recall audits.

## Residual ranker

Let `b(u,i)` be the standardized score from the stronger validation-selected BPR baseline. CAPER constructs target-blind scalar features

```text
[standardized_bpr_score,
 standardized_semantic_score,
 score_product,
 score_difference,
 collaborative_rank_percentile,
 semantic_rank_percentile,
 collaborative_branch_membership,
 semantic_branch_membership,
 log_item_popularity,
 semantic_dislike_cosine,
 log_user_history_length,
 intercept]
```

and predicts a bounded residual

\[
s_\phi(u,i)=b(u,i)+\alpha\tanh(g_\phi(x_{u,i})).
\]

The bounded residual makes `alpha=0` recover BPR and prevents the global geometry shift observed in RIPPLE.

## Natural preference pairs and contradiction mining

For each user, the core model creates a candidate union before labels in the chronological alignment block are consumed. CAPER forms a pair only when both rated items occurred naturally in that union and their ratings differ by at least two. It never injects a labeled target.

A pair is a **BPR contradiction** exactly when the lower-rated item has an equal or higher frozen BPR score. Each training epoch uses a fixed 50/50 mixture of contradiction and ordinary rating-gap pairs, with registered raw-cohort floors and deterministic replacement sampling logged when one stratum is short.

## SimPO-derived preference alignment

For the actual union `C_u`, define

\[
\pi_\phi(i\mid u,C_u)=
\frac{\exp(s_\phi(u,i)/\tau)}
{\sum_{j\in C_u}\exp(s_\phi(u,j)/\tau)}.
\]

For chosen `i+` and rejected `i-`, the shared normalizer cancels. CAPER uses

\[
L_{pref}=-\log\sigma\left[
\frac{\beta}{\tau}(s_\phi(u,i^+)-s_\phi(u,i^-))-\gamma
\right].
\]

It adds a soft anchor on observed pair structure. Let `p_b` and `p_phi` be the Bernoulli probabilities induced by the base and adjusted pair gaps. The KL term is masked on BPR contradictions so explicit evidence can override the base ordering, while the bounded-residual L2 term applies globally:

\[
L=L_{pref}+\lambda\left[
\lambda_{KL}\mathbf{1}_{\mathrm{noncontradiction}}D_{KL}(p_b\Vert p_\phi)
+\lambda_2\|s_\phi-b\|_2^2
\right].
\]

There is no language-model reference policy and no second reference-model forward pass. For one-step item ranking, the preference term is algebraically a target-margin-shifted RankNet/BPR loss.

## Hard collaborative-regret projection

The learned score proposes a ranking, then a deterministic feasible projection enforces a BPR-surrogate budget. Normalize BPR scores by the anchor-only scale `R_u=max(Q_0.95(B_u)-Q_0.05(B_u), 10^-6)` and let `A_u` be the BPR top-10. For any candidate top-10 set `L`, define

\[
\mathcal{R}_u(L)=\max\left(0,
\sum_{i\in A_u}\bar b(u,i)-\sum_{j\in L}\bar b(u,j)
\right).
\]

The scale is computed only from immutable BPR-anchor scores. Semantic candidates never influence it, so an extremely weak semantic item cannot make regret artificially cheap. Starting from `A_u`, scan incoming candidates in descending proposed-score order. For each incoming candidate, choose its feasible displaced item by proposal-gain per incremental BPR cost with deterministic tie breaking; accept only a strictly positive-gain swap, permanently retire the displaced item, and maintain

\[
\mathcal{R}_u(L)\le\epsilon.
\]

Then order the feasible set by the proposed score, with deterministic item-ID tie breaking. The PoC fixes `epsilon=0.12` before test access and applies it to every projected method. The projection guarantees feasibility only under the selected summed BPR-score surrogate; it need not recover exact BPR membership or order when zero-cost ties exist. It is a greedy feasible map, not an optimal constrained solver, and it does not guarantee true NDCG.

## High-level pseudocode

```python
# Core block
E_sem = normalize(SentenceTransformer.encode(title_and_genres))
bpr_implicit = train_bpr(core_events, unknown_negatives=True)
bpr_rating = train_bpr(core_events, explicit_lows=True)
bpr = stronger_on_validation_without_test(bpr_implicit, bpr_rating)
I_sem = faiss.IndexFlatIP(E_sem)
I_cf = faiss.IndexFlatIP(bpr.item_factors)
freeze_and_hash(E_sem, bpr.item_factors, I_sem, I_cf)

def union(user, prefix):
    B = I_cf.search(bpr.user_factor[user], K_bpr)
    S = I_sem.search(semantic_history(prefix), K_sem)
    C = stable_union(B, S)
    assert set(B).issubset(C)
    return B, C

# Alignment block only
pairs = []
for user in users:
    B, C = union(user, core_history[user])
    labeled = [event for event in alignment_block[user] if event.item in C]
    pairs += rating_gap_pairs(labeled, gap=2, target_injection=False)
pairs = half_bpr_contradictions_half_uniform(pairs)

# Residual alignment variants
for variant in [zero_margin, unanchored_simpo, soft_anchor, caper]:
    train_bounded_residual(pairs, simpo_loss, variant.anchor)

# Serving and CAPER projection
B, C = union(user, prefix)
features = construct_features(user, C, prefix)
proposed = bpr_scores(C) + bounded_residual(features)
top10 = regret_project(B, C, proposed, epsilon_preregistered_0_12)
assert cumulative_normalized_bpr_regret(top10) <= epsilon
return top10
```

## Complexity and latency

- Metadata encoding and BPR fitting are offline.
- Online retrieval is two independent vector searches that can run in parallel.
- Residual inference is `O(|C|h)` for a tiny hidden dimension.
- Greedy regret projection is `O(|C| log |C|)`.
- No catalog vector or FAISS index changes during preference alignment.

## Required controls

1. Popularity and semantic-only retrieval diagnostics.
2. Implicit BPR and rating-aware BPR; the stronger is the primary baseline.
3. Tuned linear BPR/semantic fusion on the identical union and under the identical hard projection budget.
4. Same projected residual with zero target margin.
5. Projected SimPO residual without the soft anchor.
6. Projected uniform-pair residual to isolate contradiction mining.
7. Full CAPER with contradiction mining and hard projection.
8. Unprojected soft-anchor-only and unanchored models as safety diagnostics, not unfair raw-NDCG mechanism hurdles.

## Failure conditions

CAPER is killed if its gains come from target injection, a different candidate budget, test-tuned regret, or weak-baseline comparison; if the hard projection fails to beat the strongest matched ablation; if true NDCG/preference accuracy do not improve; or if support, Recall, dislike, latency, seed, or hash gates fail.
