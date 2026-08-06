# Research Findings

## Research Question

On a prospectively selected temporal MovieLens 10M cohort, under an exact 200 unseen BPR plus 200 BPR-novel semantic output contract, can CABLE-PREF improve BPR-missed preferred-item Admission@200 by at least `+0.020` over raw exact-complement retrieval and `+0.010` over order-only reference-free alignment, and improve sPCE@10 by at least `+0.005` over raw hybrid and BPR, without material relevance, dislike-safety, seed-stability, or p95-latency regression?

## Current Understanding

Phase 1 originally found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference freshness versus reindexing cost, and semantic alignment versus online latency. RIPPLE showed that semantic query adaptation cannot replace collaborative structure. CAPER preserved collaborative support and safety, but global preference residuals still failed to retain both relevance and preference quality. RAVEL then showed that selective intervention can preserve relevance and produce positive conditional uplift, yet cannot create enough aggregate preference effect when the underlying constrained proposal changes too little of the evaluated preference surface. A cycle-4 deep-tail continuation idea was rejected after its apparent preference gain vanished on served-page metrics. FACET-PREF moved alignment before ANN candidate formation, but its fixed post-filter retrieval depth could not guarantee the registered exact candidate budget. Cycle 5 is back in Phase 1. No positive benefit claim has been made.

## Key Results

RIPPLE v1 is a verified negative result. NDCG@10 was `0.01135` versus BPR-MF `0.06256`; four of eight mandatory gates failed.

CAPER v1 is also a verified negative result. It preserved candidate support, Recall, dislike safety, immutability, and `2.307 ms` worst-seed p95 latency, but gained only `0.125%` NDCG over BPR, lost `0.55` percentage points of user-macro preference accuracy, lost to projected linear fusion, and was stable in only one of three seeds. G1, G2, G3, and G7 failed, so CAPER was killed and Phase 5 remained forbidden.

RAVEL v1 is the third killed design. Its source-bound runner produced `+0.000146` user-macro preference gain versus the required `+0.005`, `8.57%` coverage versus the `10%` floor, only `45.67` seed-averaged accepted-and-pair-bearing requests versus `100`, and `1.543x` worst-seed p95 overhead versus `1.25x`. G1, G3, G5, and G9 failed internally. The post-exit verifier also failed closed on nonempty SentenceTransformer progress-bar stderr, so no external completion marker exists and G10 fails. RAVEL was killed without rerun or repair; Phase 5 remains prohibited.

FACET-PREF v1 is the fourth killed design. After all three-seed R-only training completed, the first target-blind V candidate construction raised `The fixed depth-700 collaborative row exhausted before 200`. Because the protocol required exactly 200 unseen BPR candidates and prohibited adaptive deeper search, this is a direct feasibility/G1 failure. V relevance, V preference, and T were never opened. The design was killed without rerun or a post-outcome depth patch.

Cycle-5 Phase 1 selected CABLE-PREF. Exact masked BPR top-200 is followed by exact masked semantic top-200 on the complement of history and the BPR branch, guaranteeing 400 unique unseen candidates for every eligible request. A small query adapter is trained with an admission loss against the detached eligible semantic cutoff plus an order-only reference-free loss. This is a hypothesis, not a positive result.

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
- An ANN depth fixed before exclusion does not imply a fixed candidate budget after excluding an arbitrarily long prefix. Candidate feasibility must be guaranteed by the operator or by a prospective history bound; it cannot be treated as a harmless implementation detail.
- Correctness and scalable latency must be separated: exact masked top-k defines the quality oracle, while filtered ANN or certified probing is evaluated independently for oracle recall, work, and tail latency.
- The next learnable target should be the actual eligible branch-admission cutoff. Pairwise order can improve without moving a preferred item into the fixed candidate set.
- Defining the semantic branch on the complement of history plus the admitted collaborative branch guarantees that every semantic slot expands support rather than duplicating BPR.

## Lessons and Constraints

- Every PoC must compare against a standard baseline on the same temporal split and candidate pool.
- Phase 5 claims are prohibited unless every preregistered promise criterion passes.
- New Windows experiment runners must follow the repository's safe-execution contract.
- Every successor cycle must use a prospectively selected cohort disjoint from all opened predecessor cohorts.
- Cycle 4 must change preference-relevant candidate support or the list-level learning target rather than add another selector around RAVEL's fixed proposal.
- FACET-PREF's consumed cohort cannot be used to tune a deeper collaborative search depth. Cycle 5 must change the feasibility construction and use an unopened evaluation cohort or a dataset/domain allocated prospectively.
- Temporal validation is empirical calibration only; conformal, distribution-free, causal, and formal-safety language is prohibited.

## Open Questions

- Which retrieval operator guarantees an exact unseen-candidate budget while retaining a meaningful scale/latency test?
- Can preference alignment act on that guaranteed-feasible candidate construction without reverting to an expensive online LLM ranker?
- What unopened cohort or domain can test the successor without adapting to FACET-PREF's consumed prefix distribution?

## Optimization Trajectory

| Cycle | Design | Outcome |
|---|---|---|
| 1 | RIPPLE v1: text-only, query-only, ANN-boundary SimPO | Dead end. Passed latency, index immutability, dislike safety, and seed stability; failed statistical quality, ANN-specific mechanism, BPR relevance, and candidate recall. |
| 2 | CAPER v1: BPR+semantic union, contradiction-focused SimPO residual, hard BPR-regret projection | Dead end. Passed support, Recall, dislike, latency, and integrity; failed material relevance, matched mechanism, preference accuracy, and seed stability. |
| 3 | RAVEL v1: finite preference proposal plus validation-gated exact fallback | Dead end. Passed relevance non-inferiority, selective mechanism, safety, support/fallback, and seed stability; failed strong default, material preference gain, coverage/support, relative latency, and external integrity. |
| 4 | FACET-PREF: macro-balanced preference-aligned facet queries before fixed-budget ANN | Dead end. Fixed depth-700 BPR retrieval exhausted before 200 unseen candidates during target-blind V construction; killed before V/T outcomes. |
| 5 | CABLE-PREF: exact masked complement retrieval plus endpoint-leave-out admission-boundary query alignment | Phases 1-2 complete; Phase 3 active on a downloaded but unopened SHA-bound MovieLens 10M archive. |
