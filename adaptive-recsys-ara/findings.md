# Research Findings

## Research Question

After two killed global-alignment designs, can a selectively activated, reference-free preference correction improve explicit preference accuracy while retaining the relevance gain of a strong semantic–collaborative linear hybrid under immutable indexes and a millisecond latency budget?

## Current Understanding

Phase 1 found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference freshness versus reindexing cost, and semantic alignment versus online latency. RIPPLE showed that semantic query adaptation cannot replace collaborative structure. CAPER then preserved collaborative support and safety, but global preference residuals still failed to improve relevance or preference accuracy. Cycle 3 is active; no positive benefit claim has been made.

## Key Results

RIPPLE v1 is a verified negative result. NDCG@10 was `0.01135` versus BPR-MF `0.06256`; four of eight mandatory gates failed.

CAPER v1 is also a verified negative result. It preserved candidate support, Recall, dislike safety, immutability, and `2.307 ms` worst-seed p95 latency, but gained only `0.125%` NDCG over BPR, lost `0.55` percentage points of user-macro preference accuracy, lost to projected linear fusion, and was stable in only one of three seeds. G1, G2, G3, and G7 failed, so CAPER was killed and Phase 5 remained forbidden.

## Patterns and Insights

- The candidate generator is an information bottleneck: a downstream aligner cannot recover an item that retrieval censored.
- Many superficially novel ingredients are occupied individually; the defensible hypothesis must live at an end-to-end systems intersection.
- A query-only adapter is operationally attractive, but semantic geometry cannot substitute for collaborative structure.
- Candidate support and a hard surrogate-regret constraint can make hybrid serving safe and fast, but they do not make a weak alignment signal useful.
- Projected linear fusion supplied relevance, while uniform natural-pair residual training supplied preference accuracy; globally applying the residual could not retain both.

## Lessons and Constraints

- Every PoC must compare against a standard baseline on the same temporal split and candidate pool.
- Phase 5 claims are prohibited unless every preregistered promise criterion passes.
- New Windows experiment runners must follow the repository's safe-execution contract.
- Cycle 3 must use a prospectively selected user cohort disjoint from the 1,000 CAPER users.
- The next hypothesis must be selective rather than another global residual.

## Open Questions

- Can a validation-calibrated gate predict when a uniform-pair residual is beneficial and otherwise defer to linear fusion?
- Can this selective policy produce a statistically supported relevance/preference Pareto improvement on a disjoint cohort?
- Does the gate remain cheap enough to preserve the measured millisecond serving envelope?

## Optimization Trajectory

| Cycle | Design | Outcome |
|---|---|---|
| 1 | RIPPLE v1: text-only, query-only, ANN-boundary SimPO | Dead end. Passed latency, index immutability, dislike safety, and seed stability; failed statistical quality, ANN-specific mechanism, BPR relevance, and candidate recall. |
| 2 | CAPER v1: BPR+semantic union, contradiction-focused SimPO residual, hard BPR-regret projection | Dead end. Passed support, Recall, dislike, latency, and integrity; failed material relevance, matched mechanism, preference accuracy, and seed stability. |
