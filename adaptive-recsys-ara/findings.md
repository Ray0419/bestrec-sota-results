# Research Findings

## Research Question

Under a fixed catalog index and p95 serving-latency budget, can a query-only, index-conditioned SimPO policy improve temporal full-catalog recommendation over frozen SentenceTransformer–FAISS retrieval and ordinary random-negative query adaptation, without re-encoding any item?

## Current Understanding

Phase 1 found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference-freshness versus reindexing cost, and semantic alignment versus online latency. The selected direction is RIPPLE, but no empirical benefit claim has been made.

## Key Results

None yet.

## Patterns and Insights

- The candidate generator is an information bottleneck: a downstream aligner cannot recover an item that ANN retrieval censored.
- Many superficially novel ingredients are occupied individually; the defensible hypothesis is at their end-to-end systems intersection.
- Treating the deployed ANN index as part of the training environment provides a concrete bridge between geometric retrieval and preference alignment.
- A query-only adapter is operationally attractive because preference updates need not re-encode the catalog.

## Lessons and Constraints

- The PoC must compare against a standard baseline on the same temporal split and candidate pool.
- Phase 5 claims are prohibited unless every preregistered promise criterion passes.
- New Windows experiment runners must follow the repository's safe-execution contract.

## Open Questions

- Can reference-free retrieval-stage alignment improve temporal full-catalog NDCG while the item index remains fixed?
- Does mining comparisons from the actual ANN boundary outperform ordinary random-negative pairwise training?
- Can a pilot-probe uncertainty signal allocate ANN effort without violating a p95 latency budget?

## Optimization Trajectory

No runs yet.
