# Research Findings

## Research Question

At a fixed 200+200 vector-retrieval budget and with immutable catalog embeddings and indexes, can macro-balanced, SimPO-inspired reference-free alignment of facet-conditioned user queries improve natural preference-pair co-support by at least 0.02 over a single-centroid hybrid and strict preference-consistent exposure@10 by at least 0.005 over both that hybrid and selected BPR, while remaining non-inferior to the hybrid in NDCG@10 and within 1.25x p95 latency?

## Current Understanding

Phase 1 originally found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference freshness versus reindexing cost, and semantic alignment versus online latency. RIPPLE showed that semantic query adaptation cannot replace collaborative structure. CAPER preserved collaborative support and safety, but global preference residuals still failed to retain both relevance and preference quality. RAVEL then showed that selective intervention can preserve relevance and produce positive conditional uplift, yet cannot create enough aggregate preference effect when the underlying constrained proposal changes too little of the evaluated preference surface. A cycle-4 deep-tail continuation idea was rejected after its apparent preference gain vanished on served-page metrics. FACET-PREF now moves alignment before ANN candidate formation while retaining collaborative support. No positive benefit claim has been made.

## Key Results

RIPPLE v1 is a verified negative result. NDCG@10 was `0.01135` versus BPR-MF `0.06256`; four of eight mandatory gates failed.

CAPER v1 is also a verified negative result. It preserved candidate support, Recall, dislike safety, immutability, and `2.307 ms` worst-seed p95 latency, but gained only `0.125%` NDCG over BPR, lost `0.55` percentage points of user-macro preference accuracy, lost to projected linear fusion, and was stable in only one of three seeds. G1, G2, G3, and G7 failed, so CAPER was killed and Phase 5 remained forbidden.

RAVEL v1 is the third killed design. Its source-bound runner produced `+0.000146` user-macro preference gain versus the required `+0.005`, `8.57%` coverage versus the `10%` floor, only `45.67` seed-averaged accepted-and-pair-bearing requests versus `100`, and `1.543x` worst-seed p95 overhead versus `1.25x`. G1, G3, G5, and G9 failed internally. The post-exit verifier also failed closed on nonempty SentenceTransformer progress-bar stderr, so no external completion marker exists and G10 fails. RAVEL was killed without rerun or repair; Phase 5 remains prohibited.

## Patterns and Insights

- The candidate generator is an information bottleneck: a downstream aligner cannot recover an item that retrieval censored.
- Many superficially novel ingredients are occupied individually; the defensible hypothesis must live at an end-to-end systems intersection.
- A query-only adapter is operationally attractive, but semantic geometry cannot substitute for collaborative structure.
- Candidate support and a hard surrogate-regret constraint can make hybrid serving safe and fast, but they do not make a weak alignment signal useful.
- Projected linear fusion supplied relevance, while uniform natural-pair residual training supplied preference accuracy; globally applying the residual could not retain both.
- Full-order preference evaluation is only interpretable when unconstrained tail reranking cannot earn credit; RAVEL therefore preserves the default tail and attributes every order change to its constrained top-10 intervention.
- Generic gating, abstention, safe fallback, semantic-collaborative mixtures, and selective LLM pair regularization are already occupied. RAVEL's only defensible candidate whitespace is post-training control of an already-trained reference-free residual with exact identity fallback and intervention-specific evaluation.
- RAVEL's accepted requests had positive `+0.00224` conditional preference uplift and passed relevance non-inferiority, but only `8.57%` of requests were accepted; proposal support, not harm calibration, limited aggregate effect.
- When the baseline path is roughly `2 ms`, even a tiny residual, projection, and two logistic heads can violate a strict relative latency ratio despite low absolute latency.
- Broad full-union preference accuracy can reward changes in unserved deep ranks. The continuation probe gained `+0.00531` on tail-tail pairs but changed page-2 NDCG/Recall by approximately zero; future evaluations must bind preference estimands to the served surface.
- Positive-item candidate recall and preference-pair co-support are different retrieval properties. FACET-PREF must establish both before attributing any top-10 change to aligned facet retrieval.
- Multi-interest retrieval, SimPO, and fixed-budget vector fusion are individually occupied. The only candidate novelty is macro-balanced reference-free alignment of facet queries before ANN with immutable item geometry and end-to-end preference/support/latency evaluation.

## Lessons and Constraints

- Every PoC must compare against a standard baseline on the same temporal split and candidate pool.
- Phase 5 claims are prohibited unless every preregistered promise criterion passes.
- New Windows experiment runners must follow the repository's safe-execution contract.
- Every successor cycle must use a prospectively selected cohort disjoint from all opened predecessor cohorts.
- Cycle 4 must change preference-relevant candidate support or the list-level learning target rather than add another selector around RAVEL's fixed proposal.
- Cycle 4 must compare FACET-PREF with raw multi-interest, single-query aligned, zero-margin, shuffled-label, single-centroid linear, and selected-BPR controls under a fixed candidate budget.
- Temporal validation is empirical calibration only; conformal, distribution-free, causal, and formal-safety language is prohibited.

## Open Questions

- Can facet-conditioned preference alignment expose useful high/low-rating pairs without target injection or catalog re-embedding?
- Does macro-balanced facet training outperform an unaligned multi-interest retriever and a single aligned query at the same semantic budget?
- Can batched facet search remain within 1.25x of the dual-index single-centroid path?

## Optimization Trajectory

| Cycle | Design | Outcome |
|---|---|---|
| 1 | RIPPLE v1: text-only, query-only, ANN-boundary SimPO | Dead end. Passed latency, index immutability, dislike safety, and seed stability; failed statistical quality, ANN-specific mechanism, BPR relevance, and candidate recall. |
| 2 | CAPER v1: BPR+semantic union, contradiction-focused SimPO residual, hard BPR-regret projection | Dead end. Passed support, Recall, dislike, latency, and integrity; failed material relevance, matched mechanism, preference accuracy, and seed stability. |
| 3 | RAVEL v1: finite preference proposal plus validation-gated exact fallback | Dead end. Passed relevance non-inferiority, selective mechanism, safety, support/fallback, and seed stability; failed strong default, material preference gain, coverage/support, relative latency, and external integrity. |
| 4 | FACET-PREF: macro-balanced preference-aligned facet queries before fixed-budget ANN | Selected after rejecting a deep-tail continuation diagnostic; Phase 2 protocol lock in progress. |
