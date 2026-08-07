# Research Findings

## Research Question

Cycle 8 has returned to Phase 1. The next question must claim an architecture-level mechanism, not only a preference-aware heuristic for an occupied mixed-precision cache.

## Current Understanding

Phase 1 originally found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference freshness versus reindexing cost, and semantic alignment versus online latency. Six designs were killed under prospective gates. Cycle 7 isolated a real compression bottleneck, but its selected MARGIN-CACHE architecture failed a deeper novelty audit: mixed-precision embedding caches, learned heterogeneous precision, ranking-aware quantization, and multi-tier vector systems already occupy the design. Only a preference-sensitivity cache-allocation criterion remained. Cycle 8 has returned to Phase 1 with no positive claim.

## Key Results

RIPPLE v1 is a verified negative result. NDCG@10 was `0.01135` versus BPR-MF `0.06256`; four of eight mandatory gates failed.

CAPER v1 is also a verified negative result. It preserved candidate support, Recall, dislike safety, immutability, and `2.307 ms` worst-seed p95 latency, but gained only `0.125%` NDCG over BPR, lost `0.55` percentage points of user-macro preference accuracy, lost to projected linear fusion, and was stable in only one of three seeds. G1, G2, G3, and G7 failed, so CAPER was killed and Phase 5 remained forbidden.

RAVEL v1 is the third killed design. Its source-bound runner produced `+0.000146` user-macro preference gain versus the required `+0.005`, `8.57%` coverage versus the `10%` floor, only `45.67` seed-averaged accepted-and-pair-bearing requests versus `100`, and `1.543x` worst-seed p95 overhead versus `1.25x`. G1, G3, G5, and G9 failed internally. The post-exit verifier also failed closed on nonempty SentenceTransformer progress-bar stderr, so no external completion marker exists and G10 fails. RAVEL was killed without rerun or repair; Phase 5 remains prohibited.

FACET-PREF v1 is the fourth killed design. After all three-seed R-only training completed, the first target-blind V candidate construction raised `The fixed depth-700 collaborative row exhausted before 200`. Because the protocol required exactly 200 unseen BPR candidates and prohibited adaptive deeper search, this is a direct feasibility/G1 failure. V relevance, V preference, and T were never opened. The design was killed without rerun or a post-outcome depth patch.

CABLE-PREF v1 is the fifth killed design. Its one-time run completed structural/A data handling, SentenceTransformer encoding, BPR fitting, and immutable index publication, then failed during target-blind R candidate generation because batched full-row FAISS retrieval disagreed with the matrix lexsort oracle. The R manifest had not yet been published, so R/V/T targets remained unopened. G1 and external integrity failed; the design was killed without repair or rerun.

Cycle-6 Phase 2 locked PIVOT after independent construct review. The item-only balanced partition has 25 shards with 334 real items and seven with 333 plus one filtered sentinel, so every fixed-work method searches exactly four complete 334-slot FAISS shards. One SimPO-trained, centered cell potential is reused in route logits and item scores; route-only, rerank-only, shuffled-direction, raw-exact, and exhaustive aligned controls isolate its mechanism. This is a hypothesis, not a positive result.

PIVOT Phase 3 is complete. Two independent executable audits found no remaining P0/P1 issue after seven prospective corrections. On the frozen item matrix, repeated construction produced identical assignments, centroids, and all 32 serialized indexes; the adversarial maximum-history query retained 100 candidates. Worst measured PIVOT p95 was `0.938390 ms` and `1.235943x` the equal-work geometric comparator, inside the locked `3.0 ms` and `1.5x` limits. These are outcome-free feasibility results, not evidence of recommendation benefit.

PIVOT v1 is the sixth killed design. Its sole claimed launch reproduced the frozen item geometry but observed 21,928 structurally eligible users rather than the preview-derived exact count 21,931. The fail-closed guard stopped before cohort construction and before any A/R/V/T stage; no recommendation-quality metric exists. Because the one-shot integrity conjunction is false and no external marker exists, PIVOT was killed without repair or rerun.

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
- Bitwise or total-order identity across FAISS and an independently accumulated matrix product is not a robust scientific invariant: floating-point backends may differ near ties even when retrieval quality is equivalent. A future protocol must name one canonical ranking semantics and audit other backends using explicit score/set tolerances.
- IVF and learned ANN routing ordinarily optimize geometric neighbor recovery. PIVOT's candidate gap is to use one preference-trained partition offset for both fixed-budget probe selection and cross-partition ranking, avoiding separate routing/ranking utilities.
- On the frozen 10,681-item SentenceTransformer matrix, any four of 32 target-blind clusters contain at least 932 items; a 300-event history therefore leaves a construction-level floor of 632 unseen items for a 100-candidate PoC.
- Exact aggregate cardinalities derived in a preview implementation are brittle protocol invariants: the scientific rule should lock eligibility logic and deterministic ordering, then fail only if fewer than the required prospective cohort size exists. Preview counts may be recorded diagnostically, not used as equality gates.

## Lessons and Constraints

- Every PoC must compare against a standard baseline on the same temporal split and candidate pool.
- Phase 5 claims are prohibited unless every preregistered promise criterion passes.
- New Windows experiment runners must follow the repository's safe-execution contract.
- Every successor cycle must use a prospectively selected cohort disjoint from all opened predecessor cohorts.
- Cycle 4 must change preference-relevant candidate support or the list-level learning target rather than add another selector around RAVEL's fixed proposal.
- FACET-PREF's consumed cohort cannot be used to tune a deeper collaborative search depth. Cycle 5 must change the feasibility construction and use an unopened evaluation cohort or a dataset/domain allocated prospectively.
- Temporal validation is empirical calibration only; conformal, distribution-free, causal, and formal-safety language is prohibited.
- CABLE-PREF's consumed claim and cohort cannot be reused. Cycle 6 must test a distinct mechanism on a prospectively disjoint cohort and must cover real frozen-embedding retrieval arithmetic before any quality launch.

## Open Questions

- Which item-level PQ residuals cause the largest user-macro preference-margin damage, and are they distinct from popular or high-residual-norm items?
- Can a learned exact tier improve future candidate preference exposure over every equal-byte cache heuristic while retaining at least 97% of full-float future-liked recall?
- Does the two-tier PQ-plus-cache serving path preserve a meaningful memory reduction without material NDCG or p95-latency regression?

## Optimization Trajectory

| Cycle | Design | Outcome |
|---|---|---|
| 1 | RIPPLE v1: text-only, query-only, ANN-boundary SimPO | Dead end. Passed latency, index immutability, dislike safety, and seed stability; failed statistical quality, ANN-specific mechanism, BPR relevance, and candidate recall. |
| 2 | CAPER v1: BPR+semantic union, contradiction-focused SimPO residual, hard BPR-regret projection | Dead end. Passed support, Recall, dislike, latency, and integrity; failed material relevance, matched mechanism, preference accuracy, and seed stability. |
| 3 | RAVEL v1: finite preference proposal plus validation-gated exact fallback | Dead end. Passed relevance non-inferiority, selective mechanism, safety, support/fallback, and seed stability; failed strong default, material preference gain, coverage/support, relative latency, and external integrity. |
| 4 | FACET-PREF: macro-balanced preference-aligned facet queries before fixed-budget ANN | Dead end. Fixed depth-700 BPR retrieval exhausted before 200 unseen candidates during target-blind V construction; killed before V/T outcomes. |
| 5 | CABLE-PREF: exact masked complement retrieval plus endpoint-leave-out admission-boundary query alignment | Dead end. Batched FAISS and matrix lexsort disagreed during target-blind R construction; no R/V/T target opened, but G1 and external integrity failed. |
| 6 | PIVOT: one preference-trained partition potential jointly controls fixed-work FAISS probing and cross-shard ranking | Dead end. Sole launch observed 21,928 rather than exactly 21,931 structurally eligible users and failed closed before cohort/A/R/V/T access; killed without repair or rerun. |
| 7 | MARGIN-CACHE: SimPO-trained sparse exact-vector tier over immutable PQ retrieval | Rejected before PoC. Architecture-level novelty collapsed to a cache-allocation heuristic after collision with mixed-precision embedding caches, learned precision allocation, ranking-aware PQ, and multi-tier vector systems. |
| 8 | Architecture-level successor | Phase 1 restarted; no cohort or outcome has been opened. |
