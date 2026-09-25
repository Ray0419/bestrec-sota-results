# RAVEL PoC v1: Preregistered Phase-4 Protocol

Status: outcome-blind protocol lock for cycle 3. This document must be committed before any RAVEL `T` label is joined to a prediction. The execution-authoritative parameter record is `src/configs/ravel_poc_ml1m_v1.json`: it contains every tunable scalar, grid, seed, count floor, and latency bound, while the qualitative G1–G10 conjunctions and strict-inequality semantics are source-bound and enumerated below. The runner hashes the protocol, configuration, and source and rejects any numeric or parameter discrepancy. An inconsistency is an integrity failure, not permission to choose between records or repair them after test access.

## Research decision and claim boundary

RAVEL (Residual Alignment via a Validation-gated Exception Layer) tests whether a separately trained, reference-model-free preference residual can be applied only on validation-identified requests while leaving a strong projected linear semantic-collaborative ranker exactly unchanged on every rejected request.

The default policy is the frozen projected linear hybrid. The residual and router are separate: the router may only decide whether a fixed residual proposal is served. It cannot change semantic/collaborative mixture weights, residual weights, item representations, BPR factors, FAISS indexes, or retrieved-union membership.

RAVEL makes no claim of conformal validity, distribution-free risk control, causal uplift, formal policy safety, Pareto optimality, or million-item latency. Its score-regret projection bounds only the frozen linear expert's surrogate. MovieLens ratings are exposed-item observations.

The PoC is promising only when all G1-G10 gates pass. Any failure kills RAVEL immediately, prohibits Phase 5, and returns the sprint to Phase 1. There is no weighted-sum rescue, test-threshold adjustment, cohort substitution, or discretionary override.

## Authenticated source and prospectively disjoint cohort

- Dataset: official GroupLens MovieLens 1M archive, `https://files.grouplens.org/datasets/movielens/ml-1m.zip`.
- Required archive SHA-256: `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`.
- Inputs: ratings from `ratings.dat`; title and genres from `movies.dat`. User demographics are excluded.
- The archive may be reused from the authenticated local cache or obtained once from the registered official URL when absent, but it must be rehashed before parsing. A mismatch fails closed and does not authorize a replacement download during the locked run.
- Extracted inputs, archive, protocol, effective configuration, source, interpreter, installed environment, representations, factor matrices, indexes, manifests, raw metric arrays, deterministic bootstrap seeds/replay configuration, raw latency medians, results, logs, verifier reports, and completion markers are SHA-256 bound.

Eligibility exactly preserves the cycle-2 four-block rules. A user must have at least 50 ratings, at least four distinct timestamp groups, at least 10 events in `A`, at least two `A` ratings of 4 or 5, at least one rating of 4 or 5 in `V`, and at least one rating of 4 or 5 in `T`. Equal-timestamp groups are indivisible. The three cuts are the cumulative-event boundaries nearest 60%, 80%, and 90%, subject to leaving at least one timestamp group in every remaining block; ties choose the earliest legal cut. Blocks must be nonempty and satisfy strict temporal separation.

The eligibility pass may reveal only the predicates and block offsets needed to establish membership; it may not publish item identities, ratings, relevance metrics, pair metrics, or method outcomes from `V` or `T`. After eligibility, all eligible users are ordered by:

```text
primary key   = SHA256("20260817:{user_id}") as lowercase hexadecimal
secondary key = numeric user_id ascending
CAPER slice   = ordered users [0:1000]
RAVEL slice   = ordered users [1000:2000]
```

The runner must independently rederive both slices, persist their user-ID manifests and hashes, assert exactly 1,000 users in each slice, and assert an empty intersection before model fitting. Fewer than 2,000 eligible users, a slice mismatch, or any overlap fails closed before outcome evaluation. The RAVEL user set is not replaceable.

## Temporal blocks and target-blind execution order

For each selected user, interactions are sorted by `(timestamp, original_row_ordinal)` and divided chronologically into `A=60%`, `R=20%`, `V=10%`, and sealed `T=10%` using the eligibility procedure above. The following order is mandatory:

1. **Source authentication and cohort lock.** Verify archive and source hashes; derive the eligible order and both cohort manifests; assert disjointness. Seal item-level `V` and `T` targets from all downstream components except their declared selection/evaluation stages.
2. **A-only fit.** From `A` interactions only, fit both registered BPR variants, compute popularity, construct user-prefix statistics, and fit any feature normalization. Encode catalog metadata without rating targets. Build the semantic and collaborative indexes.
3. **R candidate and pair-pool publication.** For every seed and BPR variant, construct the `R` request from `A` history, retrieve the candidate union, and publish the complete candidate and feature manifest before joining any `R` rating. Then join naturally present `R` ratings and persist the registered pair pool for each still-possible default. Targets are never appended, and no residual is fit until the default is locked.
4. **V candidate publication.** Build and hash the `V` candidate manifests for both BPR identities from `A+R` histories before any `V` target access.
5. **Default relevance lock.** Expose only the `V` relevance labels needed to compute NDCG@10 and Recall@10 for the registered BPR identities and linear-weight grid. Lock the stronger BPR identity, linear `alpha`, and base projection using relevance only. The base-selection stage may not compute preference-pair outcomes or any residual/router outcome.
6. **Residual fit and V proposal publication.** Train the fixed residual against the selected frozen linear score using only its already persisted `R` natural-pair pool; residual hyperparameters are not selected with `V`. Freeze residual weights. In a target-blind proposal stage that receives the locked base and candidate manifests but no `V` target object, compute and publish the linear outputs, proposal and router descriptor for every registered `(rho, tau)` pair and all control descriptors.
7. **Cross-fitted router and operating point.** Join the full `V` labels to the already published proposal rows, create the declared benefit and harm targets for each registered proposal specification, obtain user-disjoint out-of-fold router predictions, and choose one registered operating point and matched-control thresholds. Refit the selected specification's benefit head only on pair-bearing `V` rows and its harm head on all relevance-eligible `V` rows. Freeze BPR identity, linear weight, base projection, residual weights, router definitions and weights, near-tie width, proposal linear-regret budget, benefit threshold, harm-probability ceiling, coverage target, control thresholds, and all tie-breaks.
8. **T manifest and prediction publication.** Using `A+R+V` only as legitimate prefix history, construct and hash the complete target-blind `T` candidate manifests. Produce and persist the full-union default and proposal orders and scalar-score bit patterns, every method's ordered top-10 and acceptance alias, router probabilities, aggregate projection diagnostics, fallback record, and latency schedule before any `T` item identity or rating is joined to a method output.
9. **Single test opening.** Open `T` once, compute the preregistered metrics, the fixed 10,000 user-cluster bootstrap, G1-G10, and `PROMISING`. No model, threshold, candidate, cohort, or metric definition may change afterward.

All stage transitions are append-only, sequence-numbered, protocol-fingerprinted, and hash-bound. A target-aware object may not be passed to a target-blind stage. The target-injection counter must remain zero.

## Representation and immutable dual retrieval

Each movie is encoded as:

```text
"{title} [SEP] {genres}"
```

The frozen, locally cached `sentence-transformers/all-MiniLM-L6-v2` model produces L2-normalized 384-dimensional `float32` item vectors in offline-only mode, batch size 128. A semantic user query is the mean of prefix items rated at least 4 minus `0.25` times the L2-normalized mean of prefix items rated at most 2, followed by L2 normalization. An absent dislike set contributes zero. A missing positive centroid or degenerate final query is an eligibility/integrity failure rather than permission to inspect the target.

Two A-only BPR backbones are trained for each registered seed `{20260817, 20260818, 20260819}`:

- implicit BPR with ratings at least 4 as positives;
- rating-aware BPR using natural within-user pairs with a rating gap of at least 2 and a registered 0.70 natural-pair fraction.

Both use 64 dimensions, 8 epochs, batch size 2,048, Adam-style learning rate `0.025`, L2 coefficient `0.0001`, gradient norm cap `5.0`, and at most 120,000 training pairs. A test-time collaborative query is the trained A user vector plus `0.5` times a rating-weighted aggregate of frozen item factors from the available prefix. Item factors never change after A-only fitting.

Create two immutable `faiss.IndexFlatIP` indexes: one over normalized SentenceTransformer vectors and one over the raw trained frozen BPR item-factor matrix. Collaborative item factors are **not** L2-normalized: raw inner-product geometry is part of the registered BPR architecture and must be hash-identical after A-only fitting. For every request, deterministically over-fetch 700 items, remove every prefix-seen item, and obtain:

```text
B_u = collaborative top 200
S_u = semantic top 200
C_u = stable_union(B_u, S_u), BPR order first, no post-union truncation
```

Thus `|C_u| <= 400` and `B_u` must be a subset of `C_u` for every stage, seed, and user. Candidate recall for `C_u` uses its actual variable size and is never called Recall@200. Candidate manifests record queries, branch ranks, membership, seen filtering, and index hashes without target labels.

## Frozen projected linear default

For each request, BPR and semantic scores are normalized using their own prefix-only branch statistics:

```text
z_b(i) = (b(i) - Q05({b(j): j in B_u})) /
         max(Q95({b(j): j in B_u}) - Q05({b(j): j in B_u}), 1e-6)
z_s(i) = (s(i) - Q05({s(j): j in S_u})) /
         max(Q95({s(j): j in S_u}) - Q05({s(j): j in S_u}), 1e-6)
l_raw(i; alpha) = alpha * z_b(i) + (1 - alpha) * z_s(i)
```

No clipping is applied; movie ID ascending breaks equal scores. The stronger BPR identity is the one with the highest seed-averaged `V` NDCG@10, breaking ties by Recall@10, then implicit BPR. The linear weight is selected from `{0.00, 0.25, 0.50, 0.75, 1.00}` by seed-averaged `V` NDCG@10, breaking ties by Recall@10, then larger `alpha`. No V preference outcome participates in this default lock.

The default list is the deterministic CAPER-style projection of `l_raw` under a cumulative normalized BPR-score regret budget of `0.12`. It starts from BPR top-10 and greedily admits positive-linear-gain swaps in proposed order only while summed BPR-anchor loss divided by the prefix-only `Q95-Q05` BPR span remains at most `0.12`; movie ID resolves ties. The selected BPR identity, `alpha`, projection rule, and resulting scalar linear scores are then frozen. A degenerate BPR span returns BPR exactly.

The projected top-10 is completed into a full-union default order by appending every non-top-10 item in descending `l_raw`, breaking ties by movie ID. The canonical fallback record is the entire full-union item order as little-endian `int32`, followed by the corresponding `l_raw` values as little-endian IEEE-754 `float32`; the served top-10 is its prefix. Rejected RAVEL requests must reuse this canonical record. Re-serialization is verified by byte equality and SHA-256 equality, not approximate numeric comparison.

## Uniform-pair SimPO residual

Only unordered pairs of `R` items that were both naturally present in the pre-published `C_u` and differ by at least two rating points are eligible. The higher-rated item is chosen. The raw uniform pool is deterministically capped at 18,000 pairs by `SHA256("ravel-R-pair-v1:{seed}:{user_id}:{low_item_id}:{high_item_id}")`; there is no contradiction balancing, target injection, replacement sampling, or V/T pair use.

Before fitting, the raw `R` pool must contain at least 300 pair-bearing users and 500 unique natural pairs. Counts before and after the cap are published.

The residual is a 13-input, one-hidden-layer MLP with hidden width 24, a `tanh` hidden activation, and a scalar `0.25*tanh(.)` output. PyTorch's default linear-layer initialization is used after `torch.manual_seed(seed+2100001)` under deterministic algorithms. Its target-blind item features are the normalized BPR score, normalized semantic score, frozen `l_raw`, score product, score difference, normalized collaborative and semantic branch ranks, both branch-membership indicators, A-only log-popularity, dislike-centroid cosine, `min(1, log1p(prefix_length)/8)`, and a bias term. It adjusts the frozen linear scalar:

```text
p_phi(u,i) = l_raw(u,i) + 0.25 * tanh(g_phi(x_ui)).
```

For chosen `i+` and rejected `i-`, the reference-free objective is:

```text
L_pref = -log sigmoid(2.0 * ((p_phi(i+) - p_phi(i-)) / 0.15) - 0.20).
```

The total loss adds `0.08` times the registered soft anchor: residual L2 plus, at relative weight `1.0`, pairwise Bernoulli KL to the frozen linear gap on pairs the frozen linear default already orders correctly. This anchor scope does not alter the uniform sampling distribution. Training uses AdamW, 18 epochs, batch size 512, learning rate `0.003`, weight decay `0.0001`, gradient norm cap `1.0`, and the three registered seeds. The residual is frozen before router training. There is no DPO reference policy or online LLM.

## Near-tie proposal and hard linear-anchor projection

For every request define the frozen-linear scale

```text
R_l = max(Q95({l_raw(i): i in C_u}) - Q05({l_raw(i): i in C_u}), 1e-6).
```

The near-tie width `tau` is selected from `{0.025, 0.050, 0.100, 0.200}` using cross-fitted V outcomes. Starting from the default top-10 membership, an incoming item `j` may replace a current default item `i` only when

```text
abs(l_raw(i) - l_raw(j)) / R_l <= tau
residual(j) - residual(i) > 0
p_phi(j) - p_phi(i) > 0.
```

Eligible membership swaps are considered once in descending adjusted-score gain, then incoming movie ID ascending and outgoing movie ID ascending. An item may enter or leave at most once. For a tentative top-10 set `L`, define

```text
regret(L) = max(0,
    sum_{i in L_default} l_raw(i) / R_l
  - sum_{j in L}         l_raw(j) / R_l).
```

The swap is committed only if `regret(L) <= rho`, where `rho` is selected from `{0.01, 0.03, 0.06, 0.12}` using cross-fitted V outcomes. Within the selected membership, add a hard precedence edge `i -> j` whenever `l_raw(i) > l_raw(j) + tau*R_l`. A deterministic priority topological sort chooses among zero-indegree items by `p_phi` descending, full-union frozen-linear rank ascending, then movie ID ascending. Complete the proposal's full-union order by appending every item outside the constrained top-10 in its unchanged frozen-linear order. Thus every served order change is induced by the explicitly constrained top-10 intervention; the preference metric cannot earn credit from unconstrained tail-tail residual inversions. The adjusted scalar array is still persisted for replay, but it grants no independent tail-order authority. A non-near-tie inversion cannot occur inside the served top-10 and the locked unweighted top-10 linear-regret budget cannot be exceeded.

The runner persists the complete frozen-linear and adjusted score arrays, full default and proposal orders, selected membership changes, aggregate swap/tightness/regret diagnostics, and the source/config hashes needed for deterministic replay. The proposal routine checks its precedence and budget invariants while materializing each output. A nonfinite score, raw scale at or below the configured `1e-6` floor, duplicate item, precedence cycle, or budget violation makes that proposal the identity proposal and returns the canonical linear record if selected for service.

## Post-training router and operating-point lock

The router receives one target-blind request row per user, seed, and registered `(rho, tau)` proposal specification. Its fixed descriptor is:

1. `log1p(prefix_length)` and `|C_u| / 400`;
2. `|B_u intersection S_u| / |C_u|`;
3. fraction of default top-10 items present only in the semantic branch;
4. the frozen-linear rank-10 versus rank-11 margin divided by `R_l`;
5. fraction of union items within the specification's normalized near-tie width of any default top-10 item;
6. proposal membership-swap count;
7. Jaccard overlap of proposal and default top-10 membership;
8. normalized pairwise rank disagreement between proposal and default on their common top-10 items;
9. mean and maximum absolute residual on the union;
10. fraction of considered membership swaps on which residual sign agrees with adjusted-score-gain sign;
11. proposal linear regret divided by `rho`;
12. total positive adjusted-score gain of committed swaps divided by `R_l`.

Every descriptor is computed and persisted before its stage's targets are joined. A missing or nonfinite descriptor fails closed; it is never imputed from a target. Continuous features are standardized within each router training fold. Item IDs, user IDs, ratings, V/T item identities, fold labels, and outcome-derived features are forbidden.

For a proposal with no committed membership swap, proposal tightness and residual-sign agreement are both defined as `0.0`. Rank disagreement is `0.0` when fewer than two common top-10 items exist. These conventions also cover reorder-only top-10 proposals and are applied before selector standardization.

The router features and labels always refer to the exact, already published `(rho, tau)` proposal that the corresponding heads would gate. Proposal specifications are trained and evaluated separately and are never mixed. Joint validation locking over their out-of-fold rows therefore selects a proposal mechanism and selector together without using `T` or redefining a target after observing an operating point.

For each registered `(rho, tau)`, two independent L2 logistic heads use scikit-learn `LogisticRegression` with `C=1`, `solver="lbfgs"`, balanced class weights, fold seed `20261017`, fold-local standardization, and maximum 500 iterations; reaching the iteration limit fails closed. Validation preference pairs use the same rating-gap rule, 100-pair-per-user cap, seed `20261118`, and hash order later used for `T`:

- **preference-benefit head:** among naturally pair-bearing V requests, target 1 iff the projected residual proposal's user-macro pair accuracy is strictly higher than the linear default; ties are 0;
- **relevance-harm head:** among V requests with a positive item, target 1 iff proposal NDCG@10 is strictly lower than linear NDCG@10; ties are 0.

All three seed rows for a user belong to the same one of five folds, assigned by `int(SHA256("20261017:{user_id}"), 16) mod 5`. Each fold trains on the other four folds and publishes out-of-fold probabilities for its held-out users. Every training split must contain both target classes; otherwise the run fails before T is opened. After the operating point is locked, the selected `(rho, tau)` specification's benefit head and standardizer are refit only on pair-bearing V rows; its harm head and standardizer are refit on all relevance-eligible V rows.

The common operating point searches the Cartesian grid:

```text
rho, linear-regret budget in {0.01, 0.03, 0.06, 0.12}
tau, near-tie width       in {0.025, 0.050, 0.100, 0.200}
benefit threshold         in {0.45, 0.50, 0.55, 0.60, 0.65, 0.70}
maximum harm probability in {0.20, 0.30, 0.40, 0.50}
```

A request is accepted only if the projected proposal changes at least one top-10 position, the benefit probability is at least its threshold, and the predicted harm probability is at most the locked maximum. Nonfinite router output means rejection and an integrity diagnostic.

A grid point is feasible on out-of-fold V predictions only when acceptance coverage is in `[0.10, 0.60]`, at least 50 accepted request rows and 30 distinct accepted pair-bearing users exist, mean RAVEL-minus-linear NDCG@10 is at least `-0.001`, and accepted pair-bearing preference uplift is positive. Among feasible points, choose highest overall user-macro preference accuracy; break ties by lower harmful-intervention rate, higher NDCG@10, lower coverage, smaller `rho`, smaller `tau`, lower maximum-harm ceiling, then higher benefit threshold. No feasible point fails closed before T access.

The locked V acceptance coverage is the target coverage for heuristic controls; it is not retuned on T.

## Matched controls

Every hybrid/residual method shares the same union candidates, base scores, residual weights, target-blind descriptors, projection code, seeds, and tie-breaking wherever applicable. The standard BPR baseline is the explicit exception: its relevance list is its registered 200-item collaborative branch, while its full-union BPR-score order is used only for the same preference diagnostic.

- validation-selected implicit or rating-aware BPR;
- frozen projected linear hybrid;
- **always-on residual:** the exact same selected finite-`rho`, finite-`tau` proposal as RAVEL on every request, including no-op proposals, with only the router decision removed; this is the G4 selector-isolation control;
- **near-tie-only:** serve the selected-`rho`, locked-`tau` proposal according to a validation-locked proposal-tightness cutoff, but no learned router;
- **uncertainty-only:** serve the same selected-`rho`, locked-`tau` proposal according to a validation-locked cutoff on Shannon entropy of the unit-temperature softmax of `l_raw/R_l` over the frozen-linear top 20;
- **deterministic random coverage:** serve the same selected-`rho`, locked-`tau` proposal according to a validation-locked cutoff on `int(SHA256("20261018:{seed}:{user_id}"),16) / 2^256`;
- **single-head selector diagnostic:** one validation-trained logistic head predicts the conjunction of positive preference benefit and no NDCG harm from the same target-blind descriptor. It accepts or rejects the same fixed proposal. This isolates the two-head decision rule from an ordinary one-head post-training selector; it is not mislabeled as a gate jointly trained with the residual.

Let `K_V` be RAVEL's accepted out-of-fold V request-row count. For each heuristic control, only V rows whose locked proposal changes the top 10 are eligible, and fewer than `K_V` such rows fails closed. Near-tie tightness is the maximum normalized frozen-linear gap `abs(l_raw(i)-l_raw(j))/R_l` among committed membership swaps, with smaller values preferred. The near-tie and entropy controls order eligible V rows respectively by `(tightness ascending, SHA256("20261018:{seed}:{user_id}") ascending)` and `(entropy descending, SHA256("20261018:{seed}:{user_id}") ascending)`; the random control orders by its registered hash value ascending. Each accepts exactly the first `K_V` rows. Its boundary descriptor and boundary hash are then frozen as a lexicographic predicate and applied unchanged to T. This gives exact V coverage matching without an outcome-derived heuristic feature or a T-time rematch. Realized T coverage is reported and is not forced to equal RAVEL after seeing T. All rejected heuristic-control requests use the canonical linear record; accepted controls return the same constrained proposal order as RAVEL.

The single-head selector diagnostic is also matched to exactly `K_V` validation rows by sorting proposal-changing rows by its out-of-fold probability descending and then the same request hash ascending. Its probability/hash boundary is frozen and applied unchanged to `T`; it is diagnostic and is not part of G4.

## Outcomes, inference, and latency

- **Relevance:** binary NDCG@10 and Recall@10 against every naturally held-out `T` item rated at least 4. The relevance cohort is the fixed 1,000-user RAVEL slice, already required to contain a positive T item by eligibility.
- **Preference:** within-user unordered pairs of naturally retrieved `T` items with rating gap at least two. If a user has more than 100 eligible pairs, retain 100 by `SHA256("20261118:{user_id}:{low_item_id}:{high_item_id}")`. User-macro accuracy is primary and pair-micro accuracy diagnostic. A pair is correct exactly when the chosen item precedes the rejected item in the method's final served full-union order. The nonselected tail remains in frozen-linear order, so any preference change must be induced by the constrained top-10 membership or precedence intervention; a true tied position, if an integrity-preserving implementation ever permits one, receives 0.5. Latent residual score inversions rejected by the top-10 near-tie, precedence, or regret rules receive no credit.
- **Low-rating intrusion:** fraction of returned top-10 items that occur in that user's `T` with rating at most 2. Unobserved items are not labeled dislikes.
- **Intervention diagnostics:** acceptance coverage; count of accepted and accepted pair-bearing requests; conditional preference uplift; harmful-intervention rate `P(delta NDCG@10 < 0 | accepted)`; mean negative NDCG regret among harmful interventions; top-10 substitution/inversion counts; projected linear regret; and no-op acceptance count.
- **Candidate support:** pointwise `B_u subset C_u` and pointwise union-candidate recall no lower than collaborative-candidate recall.
- **Exact fallback:** full-union item arrays, corresponding scalar-score arrays, canonical bytes, and SHA-256 must match the frozen linear output for every rejected request; top-10 equality follows as a prefix check.

Before accepted-coverage filtering, each seed's retrieved T union must contain at least 500 eligible preference pairs and 300 pair-bearing users. R must independently contain at least 500 natural pairs and 300 pair-bearing users. Empty paired cohorts, missing values, or nonfinite statistics fail closed.

For inferential metrics, average each user's outcome over the three registered optimization seeds, then run a paired 10,000-draw user-cluster percentile bootstrap with seed `20261117` and alpha `0.05`. Resample users, never pairs or seed rows. Report two-sided 95% intervals. Relevance metrics use all three seed rows. For preference metrics, a user is included if at least one seed retrieves an eligible pair; that user's value is the mean over only the pair-bearing seeds, with RAVEL and its comparator evaluated on the identical pairs within every included seed. Pair-micro diagnostics average seed-level pair counts and correct counts before pooling. For G5, coverage is the mean of the seed-averaged per-user acceptance indicator and accepted-request counts are the sums of those fractional indicators. Accepted pair-bearing support is instead `sum_u mean_s[accepted(u,s) * 1(preference_pairs(u,s)>0)]`, so acceptance and pair availability must occur in the same seed row. Harmful-intervention rate is the sum of seed-averaged harmful-and-accepted indicators divided by the sum of seed-averaged accepted indicators. The out-of-fold V transfer estimate uses the identical aggregation. Router cross-fitting is conditional on the globally V-locked default and is not described as nested cross-fitting of the full pipeline.

Latency is measured single-threaded on CPU on the first 500 RAVEL-cohort users in numeric user-ID order. The first 50 of those same users are run once as warm-up and remain in the 500-user measured cohort. Each method/seed then receives three AB/BA-interleaved repetitions; each user's median is formed first and p95 is taken across users. The timed RAVEL path includes both FAISS searches, seen filtering, stable union, feature construction, linear scoring, residual scoring, proposal projection and assertions, router descriptor and heads, and final sorting. It excludes offline encoding, BPR/residual/router training, index construction, target join, and disk I/O. The comparison linear path is identically instrumented through union and linear ranking. Worst-seed p95 is used for G9.

## G1-G10 all-or-nothing promise gate

1. **G1 - strong default relevance.** The frozen projected linear hybrid exceeds the validation-selected BPR by at least `2%` relative NDCG@10, and the paired 95% lower bound of its absolute NDCG difference is above zero.
2. **G2 - primary relevance non-inferiority.** RAVEL-minus-linear NDCG@10 has point estimate at least `-0.0002` and paired 95% lower bound strictly greater than `-0.001` absolute.
3. **G3 - primary preference gain.** RAVEL user-macro preference accuracy exceeds linear by at least `0.005` absolute, with paired 95% lower bound above zero.
4. **G4 - selective mechanism.** RAVEL has higher point NDCG@10 than the always-on control serving the exact same selected finite proposal, and higher point preference accuracy than each locked matched-coverage heuristic control: near-tie-only, uncertainty-only, and deterministic random coverage. Accepted pair-bearing requests have positive point preference uplift over linear.
5. **G5 - nontrivial calibrated coverage.** T intervention coverage is in `[0.10, 0.60]`; at least 100 accepted test requests and 100 accepted pair-bearing test requests exist. T harmful-intervention rate exceeds the locked out-of-fold V estimate by at most `0.05` absolute.
6. **G6 - top-rank and exposure safety.** The paired 95% lower bound for RAVEL-minus-linear Recall@10 is strictly greater than `-0.002`, and the paired 95% upper bound for RAVEL-minus-linear future low-rating intrusion@10 is at most `0.002`.
7. **G7 - candidate support and exact fallback.** The complete collaborative branch is contained in every served union; union candidate recall is never below collaborative candidate recall; every rejected request exactly matches linear's complete full-union item order and corresponding scalar scores at array, byte, and SHA-256 levels. Top-10 equality follows as a prefix check.
8. **G8 - seed stability.** At least two of three seeds simultaneously have RAVEL-minus-linear NDCG@10 at least `-0.0002` and strictly positive RAVEL-minus-linear preference accuracy.
9. **G9 - serving budget.** Worst-seed single-thread CPU RAVEL p95 is at most `20 ms` and at most `1.25x` the identically instrumented dual-index projected-linear hybrid.
10. **G10 - integrity.** Semantic and collaborative matrices and both FAISS indexes remain hash-identical; target injection is zero; source archive and cohort hashes match; temporal order and target-blind stage assertions pass; all candidate and prediction manifests predate their target joins; the completion marker, process-exit, lock-release, recursive artifact-hash, and empty asynchronous-ledger checks pass.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9 & G10
```

The boolean is recomputed from bound raw user/seed arrays by the post-exit verifier. The runner may not supply an unverified override.

## Fail-closed conditions

In addition to any failed gate, the run fails closed on an archive/config/protocol/source/interpreter hash mismatch; fewer than 2,000 eligible users; cohort overlap or wrong slice; a split or temporal violation; fewer than the registered R or T pair/user minima; an invalid router fold or single-class router training split; no feasible V operating point; target injection; candidate support failure; duplicate/nonfinite scores; a missing comparison cohort; mutation of a representation, factor matrix, index, manifest, or locked choice; an automatic retry after an asynchronous exception; a partial-fold resume attempting to pass latency; or incomplete external verification. Scientific gate failure is a valid negative result and does not authorize an outcome rerun.

## Windows-safe launch and authoritative completion

The bound launcher must invoke the workspace virtual-environment interpreter directly with `-B -u`; it may not nest the outcome run in `uv run`. Before importing NumPy, SciPy, scikit-learn, FAISS, or PyTorch, it sets `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, and `BLIS_NUM_THREADS` to `1`, sets `CUDA_VISIBLE_DEVICES=-1`, and enables offline Hugging Face/Transformers operation. PyTorch sets intra-op and inter-op threads to 1, and every loader uses `num_workers=0`.

The launcher creates a unique append-only run directory and persistent stdout/stderr files, holds a separate outer launch lock for the entire runner-verifier-marker chain, and starts one hidden child with file-owned stdout/stderr. The runner holds its own owner-PID exclusive lock. No long-running pipe capture or short foreground timeout is allowed. Cancellation must terminate and wait for the child before closing logs.

The runner installs `threading.excepthook` and `sys.unraisablehook`, writes a fresh append-only asynchronous-error ledger, and exits nonzero if that ledger is nonempty. Checkpoints and progress snapshots are protocol-fingerprinted, monotonically numbered, append-only files. Resume accepts only the newest recursively hash-valid snapshot with identical protocol, runner, input, and configuration hashes; any partial resume makes G9 false.

After writing raw arrays and a provisional final JSON, the runner publishes exactly one fsynced, no-overwrite runner-completion candidate that binds every artifact hash and declares its lock release pending. This candidate is not an authoritative completion marker. The outer launcher waits for its actual process handle and separately verifies that both the launcher child PID and the PID recorded by Python have exited; a Windows venv-shim PID mismatch is allowed only when both are independently dead. It then verifies runner-lock release and launches a separately bound post-exit verifier with a fresh asynchronous-error ledger.

The verifier recursively rehashes all artifacts, replays candidate support, projection, exact fallback, bootstrap, and G1-G10 from raw arrays, verifies immutable matrix/index hashes, confirms target-manifest ordering, checks that runner and verifier locks are released, and requires all asynchronous ledgers and clean-run stderr to be zero bytes. Only after successful verification may the launcher atomically publish one unique `EXTERNAL_COMPLETE_<execution-fingerprint>.json` marker binding the protocol/config/source/archive/interpreter hashes, logs, runner candidate, verifier report, final result, process exits, lock releases, and verdict.

A run is `COMPLETE` only when the outcome PID has exited, the unique external marker exists, every declared and recursive hash verifies, both locks are released, and all asynchronous ledgers are empty. A final JSON without that marker is uncommitted and cannot authorize Phase 5 or an outcome rerun. Recovery may commit one sole deeply valid uncommitted final without recomputation only under the Windows contract's dead-PID, hash-bound log, empty-stderr, empty-ledger, and singular-final rules; multiple or malformed finals fail closed.
