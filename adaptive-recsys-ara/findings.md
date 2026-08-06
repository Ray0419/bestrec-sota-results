# Research Findings

## Research Question

Under a fixed catalog index and p95 serving-latency budget, can a query-only, index-conditioned SimPO policy improve temporal full-catalog recommendation over frozen SentenceTransformer–FAISS retrieval and ordinary random-negative query adaptation, without re-encoding any item?

## Current Understanding

Phase 1 found four coupled bottlenecks: cross-stage objective mismatch, exposure-censored feedback, preference-freshness versus reindexing cost, and semantic alignment versus online latency. The selected direction is RIPPLE, but no empirical benefit claim has been made.

## Key Results

RIPPLE v1 is a verified negative result. NDCG@10 was 0.01135 versus 0.00573 for frozen semantic FAISS, 0.01155 for exact-hard adaptation, and 0.06256 for BPR-MF. Recall@50 fell from 0.09363 to 0.06866. Four of eight mandatory gates failed, so the design was killed and Phase 5 was forbidden.

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

| Cycle | Design | Outcome |
|---|---|---|
| 1 | RIPPLE v1: text-only, query-only, ANN-boundary SimPO | Dead end. Passed latency, index immutability, dislike safety, and seed stability; failed statistical quality, ANN-specific mechanism, BPR relevance, and candidate recall. |
