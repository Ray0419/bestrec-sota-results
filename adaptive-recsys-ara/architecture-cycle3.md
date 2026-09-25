# Phase 3, Cycle 3: RAVEL Architecture

## Design objective and boundary

**RAVEL (Residual Alignment via a Validation-gated Exception Layer)** converts a preference residual into a one-sided, post-training exception to a strong default ranker. The default is the validation-selected projected linear semantic-collaborative hybrid. RAVEL does not learn new mixture weights at serving time: it freezes the default, freezes a separately trained residual, constructs a constrained proposal, and lets a small validation-trained selector either accept that proposal or return the default result exactly.

The architectural invariant is

```text
rejected request -> the cached full-union linear object, unchanged (top-10 is its prefix)
accepted request -> a near-tie-only residual proposal satisfying linear-score regret
```

This is an empirical intervention-control mechanism, not a conformal, causal, or formal safety guarantee.

## End-to-end pipeline

```text
offline item metadata
  title + genres -> frozen SentenceTransformer -> normalized 384-d item vectors -> FAISS-sem

chronological interaction block A
  implicit/rating-aware BPR -> dense user/item factors -------------------------> FAISS-cf
  prefix log + cached item vectors -> positive/dislike semantic user vector ---------|
                                                                                     v
request -> parallel immutable FAISS-cf top Kb and FAISS-sem top Ks -> stable union C(u)
                                                                 |
                                                                 v
                                  frozen projected linear hybrid -> default D0(u)
                                                                 |
R-block natural rating-gap pairs -> reference-free SimPO-derived bounded residual ----|
                                                                 |
                                                                 v
                                      residual score over the same immutable union
                                                                 |
                                          near-tie eligibility + linear-regret map
                                                                 |
                                           constrained proposal P(u) and descriptor z(u)
                                                                 |
V-only cross-fitted outcomes -> frozen preference-benefit/harm selector ------------|
                                                                 |
                                      reject -> exact D0(u) | accept -> P(u)
```

There is no catalog re-embedding, FAISS mutation, online LLM call, reward-model call, or DPO reference-policy forward pass after block `A`.

## 1. Dense representation

### Item metadata with SentenceTransformers

For movie `i`, construct one deterministic metadata string

```text
"{title} [SEP] {genres}"
```

and encode it once with the frozen, locally cached `sentence-transformers/all-MiniLM-L6-v2` model. Batched encoding yields `e_sem(i) in R^384`; every vector is converted to `float32`, L2-normalized, cached, hashed, and never changed during residual or selector training. Inner product is therefore cosine similarity on the semantic branch.

### Interaction logs as dense user state

RAVEL does not repeatedly serialize a user's history into text. Each available-prefix interaction inherits its item's cached SentenceTransformer vector, and the log is pooled into a dense semantic state:

\[
q_{sem}(u,t)=\operatorname{norm}\!\left(
\operatorname{mean}_{(i,r)\in H_{u,t},r\ge4} e_{sem}(i)
-\rho\,\operatorname{norm}\!\left(
\operatorname{mean}_{(i,r)\in H_{u,t},r\le2}e_{sem}(i)
\right)\right),
\]

with the registered `rho=0.25`. An empty dislike set contributes the zero vector. Eligibility guarantees a positive `A` history; a missing positive centroid, degenerate final query, or nonfinite norm fails closed rather than consulting a target or changing the registered retrieval policy. Only events strictly in the request prefix enter `H(u,t)`.

The same prefix also produces a collaborative user state `q_cf(u,t)` from the frozen BPR user vector plus the registered rating-weighted aggregate of frozen BPR item factors. Thus the interaction log has two dense views: a semantic centroid derived from SentenceTransformer item vectors and a collaborative latent-factor state derived from interactions. Neither future labels nor item IDs from the target block enter either state.

### Target-blind item/request features

For each naturally retrieved `(u,i)` pair, compute a compact feature vector from the frozen states and union:

```text
[robust_standardized_collaborative_score,
 robust_standardized_semantic_score,
 frozen_linear_fusion_score,
 score_product,
 score_difference,
 collaborative_rank_percentile,
 semantic_rank_percentile,
 collaborative_branch_membership,
 semantic_branch_membership,
 log_item_popularity,
 semantic_dislike_cosine,
 log_prefix_history_length,
 intercept]
```

Feature normalizers are learned without `V` or `T` labels and frozen. Movie IDs, future ratings, future relevance indicators, and whether the base will be correct are not features.

## 2. Immutable dual-FAISS candidate generation

Build two independent maximum-inner-product indexes:

\[
B_u=\operatorname{FAISS}_{cf}(q_{cf}(u,t),K_b),\qquad
S_u=\operatorname{FAISS}_{sem}(q_{sem}(u,t),K_s).
\]

The MovieLens PoC uses exact `faiss.IndexFlatIP` indexes to remove ANN approximation as a confound. The semantic index contains normalized SentenceTransformer vectors. The collaborative index contains the frozen item factors in exactly the representation used by the selected BPR scorer; it need not be cosine-normalized when raw inner product is the trained score.

After deterministic over-fetching and removal of prefix-seen items, use `K_b=K_s=200` and form

```text
C_u = stable_union(B_u, S_u)  # BPR order first, then unseen semantic additions
```

There is no post-union truncation, so `|C_u| <= 400` and `B_u` is a pointwise subset of `C_u`. Both item matrices, both serialized indexes, and all index parameters are hash-bound before residual training. Hash equality is checked after evaluation. At production scale, each branch can be replaced by a separately audited IVF/HNSW or managed Pinecone index, but the immutable-union and per-branch recall contracts remain unchanged.

## 3. Frozen linear default

Two BPR identities are trained on `A`: implicit BPR and rating-aware BPR. The stronger identity is selected on `V` without test access. For every item in the common union, let `z_cf(u,i)` and `z_sem(u,i)` be robustly standardized collaborative and semantic scores. A registered grid selects

\[
\ell_\omega(u,i)=\omega z_{cf}(u,i)+(1-\omega)z_{sem}(u,i)
\]

on `V`. The already established BPR-anchor projection with budget `epsilon_bpr=0.12` is applied identically to every linear candidate; `V` selects the final `omega` and BPR identity. The projected top-10 is completed into a deterministic full-union order by appending every non-top-10 item in descending frozen linear score, breaking ties by item ID. The full order and scalar `ell` score bits are the frozen default object

```text
D0(u) = (full_union_item_order_0, full_union_score_bit_patterns_0).
```

`D0` is materialized once per request before the RAVEL decision. A rejected request returns this object rather than recomputing the linear ranker. This makes exact fallback an identity property, not an approximate equality claim.

## 4. Uniform natural-pair residual alignment

### Natural pairs only

For block `R`, publish the union made from the `A` prefix before opening any `R` rating. Join labels only after that manifest is persisted. An unordered pair is admissible when both items occurred naturally in that union and their ratings differ by at least two. The higher-rated item is `i+`; the lower-rated item is `i-`. Targets are never inserted into a union.

RAVEL samples uniformly from the admissible natural-pair pool under the registered global cap. It does not oversample base contradictions, correctly ranked pairs, rating gaps, item classes, or users. Sampling seeds, pair caps, replacement behavior, and raw-versus-selected counts are logged. The required alignment floors in the locked research question fail closed before training.

### Bounded residual

Let `g_phi` be a small two-layer MLP. It predicts

\[
r_\phi(u,i)=\alpha\tanh(g_\phi(x_{u,i})),\qquad
s_\phi(u,i)=\ell_\omega(u,i)+r_\phi(u,i).
\]

The bound `alpha` limits the score perturbation and makes the zero residual recover the frozen linear score. The residual is trained to completion and frozen before validation labels are used for **selector** targets. The same `V` block has one earlier, segregated use: after every `V` manifest is persisted, relevance labels lock the BPR identity and linear-fusion weight. The residual is then trained only on the already formed `R` pairs against that fixed linear score. No residual weight is fitted to `V`.

For the actual retrieved union, define the one-step item policy

\[
\pi_\phi(i\mid u,C_u)=
\frac{\exp(s_\phi(u,i)/\tau)}
{\sum_{j\in C_u}\exp(s_\phi(u,j)/\tau)}.
\]

The shared normalizer cancels for a chosen/rejected pair, giving the SimPO-derived objective

\[
\mathcal L_{pref}=-\log\sigma\!\left[
\frac{\beta}{\tau}
\left(s_\phi(u,i^+)-s_\phi(u,i^-)\right)-\gamma
\right].
\]

A registered soft anchor combines bounded-residual L2 with pairwise Bernoulli KL to the frozen linear gap on pairs the linear default already orders correctly. Let `p_ell` and `p_phi` be the logistic probabilities induced by the frozen and adjusted gaps, and let `m=1[ell(i+) > ell(i-)]`:

\[
\mathcal L=\mathcal L_{pref}+\lambda\left[
\lambda_2\left(r_\phi(u,i^+)^2+r_\phi(u,i^-)^2\right)/2
+\lambda_{KL}mD_{KL}(p_\ell\Vert p_\phi)
\right].
\]

This is reference-free preference optimization in the relevant systems sense: the loss directly compares the chosen and rejected scores, and no DPO reference language model, policy log-probability cache, or second model forward pass exists. The frozen linear score is an input anchor, not a trainable or generative reference policy. For one-step item ranking, the loss is algebraically a target-margin-shifted pairwise logistic loss; RAVEL does not claim a new preference objective.

## 5. Constrained residual proposal

The residual never receives unconditional authority over the union. It first creates a deterministic, target-blind proposal relative to `D0`.

### Near-tie eligibility

For request `u`, derive a scale only from frozen linear scores:

\[
R_u=\max\left(Q_{0.95}(\{\ell_\omega(u,i):i\in C_u\})-
Q_{0.05}(\{\ell_\omega(u,i):i\in C_u\}),10^{-6}\right).
\]

A baseline item `i` and proposed item `j` are a near tie only when

\[
|\ell_\omega(u,i)-\ell_\omega(u,j)|/R_u\le\delta_{tie}.
\]

Starting from the default membership, an incoming item may replace a default item only if this condition holds, the residual advantage `r(j)-r(i)` is positive, and the adjusted-score gain `s(j)-s(i)` is strictly positive. Candidate swaps are processed in descending adjusted-score gain with deterministic item-ID tie breaking; an item can enter or leave at most once.

Within the selected set, construct a hard-precedence edge from `i` to `j` whenever `ell(u,i) > ell(u,j) + delta_tie * R_u`. A deterministic priority topological sort uses adjusted score, then full-union linear rank, then item ID. Therefore the residual may invert only a pair not protected by the near-tie rule. A degenerate scale, cycle, nonfinite score, or empty proposal returns an identity proposal.

### Hard linear-anchor regret

Let `L0(u)` be the item set in the top-10 prefix of `D0` and `L` a proposed top-10. Define

\[
\bar\ell(u,i)=\ell_\omega(u,i)/R_u,
\qquad
\mathcal R_{lin,u}(L)=\max\left(0,
\sum_{i\in L_0(u)}\bar\ell(u,i)-
\sum_{j\in L}\bar\ell(u,j)
\right).
\]

Each greedy membership swap is committed only if cumulative regret remains at most the validation-locked `epsilon_lin`. The proposal code asserts the final budget and the near-tie precedence relation. An assertion failure produces the identity proposal and a logged fail-closed reason. This bound protects only the frozen linear score surrogate; it does not guarantee true relevance or NDCG.

The completed proposal contains the constrained top-10 followed by every remaining union item in its unchanged frozen-linear order:

```text
P(u) = (full_projected_item_order, adjusted_score_bits, regret, changed_pairs)
```

and is frozen before the selector decision. The adjusted scalar array is retained for deterministic replay, but it cannot independently reorder the tail. Consequently, full-order preference credit can arise only from the explicitly constrained top-10 intervention rather than arbitrary tail-tail inversions. Projection is not allowed to inspect the selector prediction or any request outcome.

## 6. Validation-gated post-training exception selector

### Request descriptor

The selector receives a small target-blind descriptor `z(u)` computed from the prefix, default, residual, and completed proposal:

```text
[log_history_length,
 union_size,
 collaborative_semantic_overlap,
 default_top10_semantic_only_fraction,
 linear_boundary_gap,
 fraction_of_union_in_near_tie_band,
 proposal_swap_count,
 proposal_top10_jaccard_with_default,
 proposal_default_rank_disagreement,
 mean_and_max_absolute_residual,
 residual_sign_agreement,
 proposed_linear_regret,
 proposed_adjusted_score_gain]
```

At `T`, ratings in `A+R+V` are legitimate prior history and may therefore affect the ordinary semantic/collaborative prefix states. However, `z(u)` never contains the current request's outcome, a realized proposal-versus-linear pair/NDCG delta, a target item ID, or a fold label. A scale-up may add historical reliability summaries only if the analogous training-time feature is produced out of fold from an earlier block; that extension is not part of the PoC or its claim.

### Two validation-only heads

After the residual and proposal mechanism are frozen, split validation users into deterministic hash folds. For each held-out fold:

1. fit a regularized preference-benefit classifier on the other folds using `1[proposal pair accuracy > linear pair accuracy]` as its target;
2. fit a regularized harm classifier on the other folds using `1[proposal NDCG@10 < linear NDCG@10]` as its target;
3. standardize features using only the training folds and persist predictions for the held-out fold.

Users without naturally present validation pairs do not train the preference head, but may train the relevance-harm head. Missing descriptor values fail closed rather than being imputed from test outcomes.

The out-of-fold predictions choose, from a preregistered grid, a preference threshold `t_pref` and maximum harm probability `t_harm`. A combination is eligible only if its validation coverage and minimum accepted counts satisfy the locked support rules and its empirical validation relevance loss is within the registered tolerance. Deterministic selection maximizes held-out preference uplift, then minimizes harmful-intervention rate, maximizes NDCG delta, minimizes coverage, minimizes the regret budget, minimizes the near-tie width, minimizes the harm ceiling, and finally maximizes the benefit threshold. The selected feature set, regularization, thresholds, tie rule, near-tie width, regret budget, and coverage are frozen before `T`. The benefit head is refit only on pair-bearing validation rows and the harm head on all relevance-eligible validation rows. This is **conditional cross-fitting of the router given the globally validation-locked default**; it is not a fully nested out-of-fold estimate of the entire BPR/fusion/residual pipeline.

The online decision is

\[
a(u)=\mathbf 1[P_{1:10}(u)\ne D_{0,1:10}(u)]
\mathbf 1[\widehat{\Delta pref}(z_u)\ge t_{pref}]
\mathbf 1[\widehat p_{harm}(z_u)\le t_{harm}].
\]

The final response is a hard branch:

\[
D(u)=
\begin{cases}
P(u),&a(u)=1,\\
D_0(u),&a(u)=0.
\end{cases}
\]

The selector cannot scale the residual, alter fusion weights, rerank a rejected request, mutate a vector, or request a second model pass. Cross-fitted validation harmful-intervention rate, harm-versus-coverage curves, and conditional uplift are reported as empirical diagnostics only.

### Exact fallback audit

For every rejected request, the runner compares the returned item-ID byte sequence and the IEEE-754 score bytes against the pre-selector `D0` object. The check must hold pointwise for every seed and is bound into the completion artifact. Equality after rounding, equality of sets, or recomputation within a tolerance is insufficient.

## 7. Outcome-blind A/R/V/T sequence

The runner rederives the locked hash order, asserts that the CAPER slice `[0:1000]` and RAVEL slice `[1000:2000]` are disjoint, and fails closed if 2,000 users do not survive the unchanged eligibility rules. Equal-timestamp groups remain indivisible and each selected RAVEL user has chronological blocks `A=60%`, `R=20%`, `V=10%`, and sealed `T=10%`. The required execution order is:

```text
all A fits and immutable-index hashes
  -> all R candidate manifests from A prefixes, persisted and hashed
  -> open R labels; form and freeze every registered natural-pair pool
  -> all V candidate manifests for every registered BPR/default spec from A+R prefixes,
     persisted and hashed
  -> open V relevance labels only to lock the BPR identity and linear-fusion weight
  -> train and freeze the uniform residual on the already formed R pairs against that default
  -> create V defaults/proposals from the persisted candidate contexts; use V outcomes
     to lock proposal settings and train the cross-fitted selector; residual weights stay frozen
  -> freeze selector, thresholds, coverage, near-tie width, regret budget, and controls
  -> all T candidate, default, proposal, descriptor, decision, and output manifests
     from A+R+V prefixes, persisted and hashed
  -> open T labels exactly once for evaluation
```

Because BPR identity and linear fusion are selected on `V`, all registered BPR/fusion candidate contexts must have their target-blind `R` and `V` manifests produced before the corresponding labels are joined. Default selection may not regenerate candidates. Residual weights are subsequently fit only on `R`; selector targets are subsequently computed only from the fixed `V` contexts and frozen residual. No method may append a rated item, replace the disjoint user cohort, or change a threshold after `T` is opened.

## 8. High-level pseudocode

```python
# A: representations and immutable retrieval
E_sem = l2_normalize(
    SentenceTransformer("all-MiniLM-L6-v2").encode(item_metadata, batch_size=B)
).astype(float32)
bpr_candidates = {
    "implicit": train_implicit_bpr(A_events),
    "rating_aware": train_rating_aware_bpr(A_events),
}
I_sem = faiss.IndexFlatIP(384)
I_sem.add(E_sem)
I_cf = {name: faiss.IndexFlatIP(model.dim) for name, model in bpr_candidates.items()}
for name, model in bpr_candidates.items():
    I_cf[name].add(model.item_factors)
freeze_hash_and_make_read_only(E_sem, bpr_candidates, I_sem, I_cf)

def retrieve(user, prefix, bpr_identity):
    q_cf = collaborative_prefix_state(user, prefix, bpr_candidates[bpr_identity])
    q_sem = semantic_prefix_state(prefix, E_sem, dislike_weight=0.25)
    B_u = search_unseen(I_cf[bpr_identity], q_cf, k=200)
    S_u = search_unseen(I_sem, q_sem, k=200)
    C_u = stable_union(B_u, S_u)       # no post-union truncation
    assert set(B_u).issubset(C_u) and len(C_u) <= 400
    return CandidateManifest(B_u, S_u, C_u, prefix_hash(prefix))

# R manifests exist before this label join; retain natural pairs, but the
# residual needs the V-locked linear default and is not fit yet.
for candidate_spec in REGISTERED_BPR_FUSION_SPECS:
    R_manifest[candidate_spec] = persist_hash(
        retrieve_all(prefix=A, spec=candidate_spec)
    )
R_pairs = uniform_natural_rating_gap_pairs(
    manifests=R_manifest,
    labels=R_labels,
    minimum_gap=2,
    inject_targets=False,
)
# Every V candidate context exists before any V label is joined. V relevance
# first locks only the default identity and fusion weight.
V_candidates = persist_hash(build_all_candidate_contexts(prefix=A_plus_R))
selected_default = lock_bpr_and_linear_weight_from_V_relevance(V_candidates)

# Fit only on R labels, now scoring pairs relative to the fixed default.
residual_by_seed = train_registered_bounded_residuals(
    pairs=R_pairs,
    frozen_linear_default=selected_default,
    loss=simpo_margin_loss_without_reference_model,
)
freeze(residual_by_seed)

# Materialize every registered proposal from the persisted V contexts before
# joining full V outcomes. V then supervises a joint, deterministic lock over
# proposal specification and selector thresholds, never the residual weights.
V_manifest_by_spec = persist_hash(
    build_all_registered_defaults_proposals_descriptors(
        V_candidates, residual_by_seed, proposal_grid=REGISTERED_RHO_TAU_GRID
    )
)
oof_by_spec = {
    spec: crossfit_selector_predictions(
        target_blind_descriptors=manifest.descriptors,
        preference_uplift=natural_pair_delta(V_labels, manifest),
        relevance_harm=ndcg_harm(V_labels, manifest),
    )
    for spec, manifest in V_manifest_by_spec.items()
}
locked = select_joint_operating_point(oof_by_spec, REGISTERED_THRESHOLD_GRID)
tie_delta, epsilon_lin = locked.tie_width, locked.linear_regret_budget
t_pref, t_harm = locked.benefit_threshold, locked.harm_ceiling
selector = refit_frozen_selector_on_all_allowed_V(locked.specification)

def serve(user, prefix):
    manifest = retrieve(user, prefix, selected_default.bpr_identity)
    D0 = materialize_cached_linear_default(manifest, selected_default)
    residual_scores = residual_by_seed[current_seed](item_features(manifest, prefix))
    P = near_tie_linear_regret_proposal(
        default=D0,
        residual=residual_scores,
        delta=tie_delta,
        epsilon=epsilon_lin,
    )
    assert P.nonselected_tail == D0.nonselected_items_in_linear_order
    z = target_blind_request_descriptor(manifest, D0, P, prefix)
    accept = (
        P.top10 != D0.top10
        and selector.benefit_probability(z) >= t_pref
        and selector.harm_probability(z) <= t_harm
    )
    if not accept:
        result = D0                         # return cached object, do not recompute
        assert byte_identical(result, D0)
        return result
    assert P.linear_regret <= epsilon_lin
    assert P.respects_near_tie_precedence
    return P

# T remains sealed through all target-blind output construction.
T_outputs = persist_hash(serve_all(prefix=A_plus_R_plus_V))
results = evaluate_once(T_outputs, open_test_labels_once())
```

## 9. Complexity and latency contract

Let `N` be catalog size, `d_sem=384`, `d_cf` the BPR dimension, `M=|C_u|<=400`, `h` the residual hidden width, and `p` the selector descriptor dimension.

- Offline metadata encoding is `O(N * encoder_cost)` and cached; BPR fitting and residual/selector training are also offline.
- The exact PoC searches cost `O(N d_cf + N d_sem)` per request and can run in parallel. Production ANN substitutes change this term without changing the union contract.
- Stable union and feature construction cost `O(M)`.
- Residual scoring costs `O(Mh)` with one tiny MLP pass.
- Near-tie swap enumeration costs `O(10(M-10))`; deterministic constrained ordering is at most `O(10^2)` for the final set. Sorting retrieval/fusion candidates is `O(M log M)`.
- The two selector heads cost `O(p)` and require no catalog access.
- Memory is dominated by the two immutable item matrices and indexes: `O(N(d_sem+d_cf))` before index overhead.

The measured serving path includes both searches, seen filtering, union, feature construction, frozen linear scoring, residual scoring, proposal, selector, projection assertions, and sorting. It excludes offline encoding, fitting, index construction, and disk I/O. Worst-seed single-thread CPU p95 must satisfy the locked `<=20 ms` and `<=1.25x` matched-linear conditions.

## 10. Matched controls and ablations

All hybrid/residual controls use the same disjoint cohort, temporal blocks, candidate manifests, union, top-10 budget, seeds, and target-blind outputs. The standard BPR baseline evaluates its registered 200-item collaborative branch for relevance; it is not mislabeled as a union reranker.

1. **Implicit and rating-aware BPR:** the validation-selected stronger BPR is the primary collaborative baseline.
2. **Frozen projected linear hybrid:** `D0`, the relevance default and exact fallback.
3. **Always-on uniform residual:** the exact same validation-selected finite near-tie/regret proposal is served on every request, including no-op proposals, with only the selector removed; this isolates selector value.
4. **Near-tie-only residual:** accept the same proposal by a validation-locked proposal-tightness cutoff at RAVEL's locked validation coverage, without learned outcome prediction; this isolates near-tie eligibility.
5. **Uncertainty-only gate:** accept the same proposal using only a validation-locked Shannon-entropy heuristic over the frozen-linear top 20 at RAVEL's locked validation coverage.
6. **Deterministic random-coverage gate:** accept the same proposal by a user/request hash at the same locked coverage; no outcome-dependent randomness is drawn at test time.
7. **Single-head selector diagnostic:** one validation-trained logistic head predicts the conjunction of positive preference benefit and no NDCG harm from the same descriptor and controls the same frozen proposal. This isolates the two-head decision rule from an ordinary one-head post-training selector. A gate jointly optimized with residual weights is reserved for the scaled study because it changes both the training interface and exact-fallback semantics; it is not falsely presented as a capacity-matched PoC control.
8. **Full RAVEL:** uniform residual, near-tie eligibility, linear-regret proposal, and validation-only exception selector.

For matched-coverage controls, the target rate and deterministic tie rule are fixed from `V`; test labels never determine who is accepted. Report realized test coverage rather than silently resampling to improve an outcome.

## 11. Measurements and failure conditions

RAVEL reports overall NDCG@10 and Recall@10, user-macro and pair-micro explicit preference accuracy, candidate recall by branch and union, intervention coverage, accepted-request conditional uplift, harmful-intervention rate, linear-score regret, future low-rating intrusion, seed dispersion, per-stage and end-to-end latency, and pointwise exact-fallback/hash audits. Preference-pair correctness is determined by the final served full-union order, but the nonselected tail retains frozen-linear order; therefore only the constrained top-10 membership/precedence intervention can change pair correctness. A latent residual inversion rejected by the near-tie or regret projection receives no credit.

The project is killed immediately if any part of the ten-part gate in `research-question-cycle3.md` fails. In architectural terms, failure includes:

- the frozen linear default is not a strong baseline, or RAVEL is relevance-inferior to it;
- preference improvement is below the locked effect and confidence thresholds;
- always-on or matched-coverage heuristic controls explain the result;
- coverage is trivial, accepted pair support is insufficient, or validation harm does not transfer within tolerance;
- Recall, dislike intrusion, seed stability, or serving latency misses its bound;
- a collaborative candidate disappears from the union, an outcome target is injected, or a test choice is changed after unsealing;
- a rejected request differs by even one item-order byte or score byte from `D0`;
- a matrix/index hash changes, temporal/cohort/provenance checks fail, or completion verification is incomplete.

There is no weighted-sum rescue, threshold retuning on `T`, cohort substitution, or discretionary override. A failed PoC returns the sprint to Phase 1 and prohibits Phase 5.
