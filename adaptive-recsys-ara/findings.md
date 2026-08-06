# Research Findings

## Research Question

After two killed global-alignment designs, can post-training, validation-gated application of a reference-free preference residual improve explicit preference accuracy by at least 0.5 percentage points while remaining non-inferior in temporal NDCG@10 to a frozen semantic–collaborative linear hybrid?

## Current Understanding

Phase 1 originally found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference freshness versus reindexing cost, and semantic alignment versus online latency. RIPPLE showed that semantic query adaptation cannot replace collaborative structure. CAPER then preserved collaborative support and safety, but global preference residuals still failed to retain both relevance and preference quality. Cycle 3 reframes this as a selective-intervention problem: RAVEL keeps projected linear fusion as an exact default and lets a separately trained residual act only after temporally prior validation grants permission. No positive benefit claim has been made.

## Key Results

RIPPLE v1 is a verified negative result. NDCG@10 was `0.01135` versus BPR-MF `0.06256`; four of eight mandatory gates failed.

CAPER v1 is also a verified negative result. It preserved candidate support, Recall, dislike safety, immutability, and `2.307 ms` worst-seed p95 latency, but gained only `0.125%` NDCG over BPR, lost `0.55` percentage points of user-macro preference accuracy, lost to projected linear fusion, and was stable in only one of three seeds. G1, G2, G3, and G7 failed, so CAPER was killed and Phase 5 remained forbidden.

RAVEL v1 has completed Phase 3 and is prospectively preregistered for one disjoint-cohort PoC. Its finite proposal may alter only the constrained top-10 intervention while preserving the frozen-linear nonselected tail; rejection reuses the complete linear record exactly. The primary always-on control serves the identical finite proposal without a selector, and an external verifier independently replays validation selection, raw test statistics, deterministic bootstrap intervals, G1-G10, provenance, and exact fallback. All outcome-free audits passed, but no RAVEL benefit claim exists until the single held-out run clears every gate.

## Patterns and Insights

- The candidate generator is an information bottleneck: a downstream aligner cannot recover an item that retrieval censored.
- Many superficially novel ingredients are occupied individually; the defensible hypothesis must live at an end-to-end systems intersection.
- A query-only adapter is operationally attractive, but semantic geometry cannot substitute for collaborative structure.
- Candidate support and a hard surrogate-regret constraint can make hybrid serving safe and fast, but they do not make a weak alignment signal useful.
- Projected linear fusion supplied relevance, while uniform natural-pair residual training supplied preference accuracy; globally applying the residual could not retain both.
- Full-order preference evaluation is only interpretable when unconstrained tail reranking cannot earn credit; RAVEL therefore preserves the default tail and attributes every order change to its constrained top-10 intervention.
- Generic gating, abstention, safe fallback, semantic-collaborative mixtures, and selective LLM pair regularization are already occupied. RAVEL's only defensible candidate whitespace is post-training control of an already-trained reference-free residual with exact identity fallback and intervention-specific evaluation.

## Lessons and Constraints

- Every PoC must compare against a standard baseline on the same temporal split and candidate pool.
- Phase 5 claims are prohibited unless every preregistered promise criterion passes.
- New Windows experiment runners must follow the repository's safe-execution contract.
- Cycle 3 must use a prospectively selected user cohort disjoint from the 1,000 CAPER users.
- The next hypothesis must be selective rather than another global residual.
- Temporal validation is empirical calibration only; conformal, distribution-free, causal, and formal-safety language is prohibited.

## Open Questions

- Can a cross-fitted validation selector identify useful preference exceptions on the prospectively disjoint hash slice `[1000:2000]`?
- Can RAVEL clear the locked `+0.005` preference gate while meeting its NDCG non-inferiority bounds?
- Does exact fallback plus a small selector stay within `1.25x` projected-linear p95 latency?

## Optimization Trajectory

| Cycle | Design | Outcome |
|---|---|---|
| 1 | RIPPLE v1: text-only, query-only, ANN-boundary SimPO | Dead end. Passed latency, index immutability, dislike safety, and seed stability; failed statistical quality, ANN-specific mechanism, BPR relevance, and candidate recall. |
| 2 | CAPER v1: BPR+semantic union, contradiction-focused SimPO residual, hard BPR-regret projection | Dead end. Passed support, Recall, dislike, latency, and integrity; failed material relevance, matched mechanism, preference accuracy, and seed stability. |
