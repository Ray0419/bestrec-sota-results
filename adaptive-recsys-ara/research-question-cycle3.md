# Phase 2, Cycle 3: RAVEL Research Question and Kill Gate

## Primary research question

> **Can post-training, validation-gated application of a reference-free preference residual improve held-out explicit preference accuracy by at least 0.5 percentage points while remaining non-inferior in temporal NDCG@10 to a frozen linear semantic-collaborative vector ranker, with exact fallback, immutable indexes, and at most 25% p95 serving overhead?**

The question is specific to the gap exposed by CAPER: a uniform natural-pair residual was a better preference expert, and projected linear fusion was a better relevance expert, but global residual application could not retain both. It is empirically testable, addresses preference alignment and serving latency, and does not depend on an online LLM or DPO reference policy.

## Concrete hypothesis

RAVEL will use the linear hybrid as the default policy and treat residual alignment as a one-sided exception. On a target-blind request, it will:

1. retrieve the immutable union of collaborative-factor and SentenceTransformer FAISS candidates;
2. score the union with a validation-selected projected linear fusion;
3. obtain a proposal from a separately trained uniform-pair, SimPO-derived bounded residual;
4. expose only near-tie proposal changes to a post-training selector trained with cross-fitted, temporally prior validation outcomes;
5. accept the proposal only when its predicted preference benefit clears a locked threshold and its predicted relevance-harm probability is below a locked ceiling;
6. otherwise return the linear hybrid's ranking exactly, byte-for-byte in item order and scores;
7. constrain accepted lists with a hard linear-anchor score-regret budget.

The selector controls only whether the fixed residual is applied. It does not jointly learn semantic/collaborative mixture weights or mutate the residual, item representations, or FAISS indexes.

## Why this question matters

- **Preference alignment:** it tests whether a stronger pairwise preference signal can be converted into useful list changes rather than being diluted or destructively applied everywhere.
- **Latency:** a small tabular selector and bounded residual replace online LLM decoding and a DPO reference-model forward pass.
- **Operational isolation:** exact fallback gives every rejected request the unchanged, validation-selected production-style ranker.
- **Scale path:** metadata embeddings and both vector indexes remain offline and immutable; online work is bounded by the retrieved union.

## Prospective cohort and outcome seal

Cycle 3 uses the already authenticated official MovieLens 1M archive with SHA-256 `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`. It does **not** claim a fresh dataset. It uses a prospectively declared, outcome-unopened cohort disjoint from CAPER:

```text
eligible users = all users satisfying the unchanged four-block temporal criteria
order key      = SHA256("20260817:{user_id}"), then numeric user_id
CAPER cohort   = ordered users [0:1000]
RAVEL cohort   = ordered users [1000:2000]
```

The runner must rederive both slices and assert that their intersection is empty before training. If fewer than 2,000 users survive the eligibility rules, the RAVEL PoC fails closed. Within each selected user, equal-timestamp groups remain indivisible and blocks are chronological `A=60%`, `R=20%`, `V=10%`, `T=10%`. Cohort derivation is permitted to inspect only the preregistered Boolean predicates “`V` contains a rating of at least 4” and “`T` contains a rating of at least 4,” because those predicates define the fixed relevance cohort; it may not expose target identities, ratings, method scores, or metrics. Beyond that sole eligibility pass, `T` is unavailable until all residual, selector, threshold, coverage, near-tie, and projection choices are frozen and all target-blind test manifests are persisted and hashed.

## Non-claims

- RAVEL does not claim novelty for gating, abstention, personalized reranking, hybrid retrieval, score fusion, SimPO, or hard fallback individually.
- Temporal validation here does not establish exchangeability; RAVEL is not conformal and makes no distribution-free or formal safety guarantee.
- The score-regret constraint bounds the frozen linear expert's surrogate, not true relevance or utility.
- Explicit MovieLens ratings are exposed-item observations; the PoC is not a causal or unbiased-policy evaluation.
- A 3,883-item exact-index PoC cannot establish million-item production latency.

## Ten-part all-or-nothing promise gate

All metrics average each user's outcome over the three registered optimization seeds before a paired 10,000-draw user-cluster bootstrap. Preference accuracy is user-macro over users with naturally present rating-gap pairs and is computed from each method's final served full-union order. The nonselected tail retains frozen-linear order, so pair correctness can change only through the constrained top-10 membership/precedence intervention; a latent score inversion rejected by the near-tie, precedence, or regret rules receives no credit. Ties receive half credit. Missing/nonfinite statistics or an empty paired cohort fail closed.

1. **Strong default relevance.** The frozen projected linear hybrid must exceed the validation-selected BPR baseline by at least `2%` relative NDCG@10, and the paired 95% lower bound of its absolute NDCG difference must be above zero.
2. **Primary relevance non-inferiority.** RAVEL-minus-linear NDCG@10 must have a point estimate at least `-0.0002` and a paired 95% lower bound strictly greater than `-0.001` absolute.
3. **Primary preference gain.** RAVEL user-macro preference-pair accuracy must exceed the linear hybrid by at least `0.005` absolute, with a paired 95% lower bound above zero.
4. **Selective mechanism.** RAVEL must have higher point NDCG@10 than an always-on control that serves the exact same selected finite proposal on every request, and higher point preference accuracy than each validation-locked matched-coverage heuristic control (near-tie-only, uncertainty-only, and deterministic random coverage). It must also achieve positive preference uplift among accepted, pair-bearing requests.
5. **Nontrivial calibrated coverage.** Accepted intervention coverage must lie in `[0.10, 0.60]`; at least 100 seed-averaged accepted test requests and 100 seed-averaged accepted-and-pair-bearing request rows are required, with acceptance and pair availability occurring in the same seed row. The test harmful-intervention rate (accepted users with negative NDCG change) may exceed its validation cross-fitted estimate by at most `0.05` absolute. These are empirical diagnostics, not probabilistic guarantees.
6. **Top-rank and exposure safety.** The paired 95% lower bound for RAVEL-minus-linear Recall@10 must exceed `-0.002`, and the paired 95% upper bound for future low-rating intrusion@10 must be no more than `0.002` above linear.
7. **Candidate support and exact fallback.** The complete collaborative candidate branch must be contained in every served union; union candidate recall must never be below collaborative-branch candidate recall. Every rejected request must exactly match the linear expert's complete full-union order and corresponding scalar-score bytes; its ordered top-10 is therefore identical as a prefix.
8. **Seed stability.** At least two of three seeds must simultaneously have RAVEL-minus-linear NDCG@10 at least `-0.0002` and positive RAVEL-minus-linear preference accuracy.
9. **Serving budget.** Worst-seed single-thread CPU RAVEL p95 must be at most `20 ms` and no more than `1.25x` the identically instrumented dual-index linear hybrid, including both searches, union construction, features, selector, residual scoring, projection, and sorting.
10. **Integrity.** Semantic and collaborative matrices and FAISS indexes remain hash-identical; no target is injected; the cohort-disjointness, temporal order, candidate-manifest publication, source/config hash, completion-marker, process-exit, lock-release, recursive artifact-hash, and empty asynchronous-ledger checks all pass.

The preference cohort must contain at least 500 held-out pairs and 300 pair-bearing users before accepted-coverage filtering. Alignment must likewise contain at least 300 pair-bearing users and 500 natural pairs. The registered seed set is `{20260817, 20260818, 20260819}`.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9 & G10
```

If `PROMISING` is false, RAVEL is killed immediately, Phase 5 remains prohibited, and the sprint returns to Phase 1. No weighted-sum rescue, test-set threshold change, cohort replacement, or discretionary override is allowed.
