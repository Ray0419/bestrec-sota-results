# Phase 2: Research Question and Falsification Contract

## Primary research question

> **Under a fixed catalog index and a p95 serving-latency budget, can a query-only, index-conditioned SimPO policy improve temporal full-catalog recommendation quality over frozen SentenceTransformer–FAISS retrieval and ordinary random-negative query adaptation, without re-encoding any item?**

The question is instantiated as the following measurable claim:

> On a chronological MovieLens proof of concept, can RIPPLE deliver at least a **5% relative gain in NDCG@10** over a frozen dense-vector baseline, outperform otherwise identical **random-negative and exact-hard-negative adapters by at least 1% relative**, remain within 10% of a standard BPR-MF baseline, preserve or improve Recall@50, keep **p95 retrieval-plus-rerank latency no greater than 1.25×** the frozen FAISS baseline, and leave the item-vector/index fingerprint unchanged?

## Why this question is high-impact

- **Scale:** catalog vectors are encoded and indexed once; preference updates are proportional to adapter size rather than catalog size.
- **Latency:** the aligned query is served by ordinary ANN plus an exact top-k dot-product rerank, rather than an always-on decoder LLM.
- **Alignment:** preference optimization acts before candidate censoring and sees confusions sampled from the deployed ANN boundary.
- **Falsifiability:** quality, mechanism, latency, and index immutability are all independently testable.

## Hypotheses

### H1 — Retrieval-stage alignment

For a temporally held-out relevant item, a low-rank query adapter trained with the SimPO score-difference objective will increase NDCG@10 and Recall@50 relative to a frozen history-centroid query.

### H2 — Index conditioning matters

Holding architecture, parameter count, optimizer, epochs, and positive examples constant, mining rejected/hard-confusion items from the deployed FAISS candidate boundary will outperform both uniform random-negative training and exact full-matrix hard-negative training.

### H3 — Alignment need not trigger reindexing

Because RIPPLE changes only the user/query transformation, precomputed item embeddings and serialized FAISS index bytes will have identical SHA-256 fingerprints before and after preference training.

### H4 — Decision-aware effort is budgetable

A pre-search ambiguity score derived from the divergence between the semantic history centroid and the adapted query can route only uncertain users to a larger IVF `nprobe`, preserving the registered p95 latency ratio while improving or preserving candidate Recall@50.

### H5 — The method remains competitive with collaborative filtering

RIPPLE will not trail a train-only BPR matrix-factorization baseline by more than 10% relative NDCG@10. This prevents a weak content baseline from making an unusable system appear promising.

## PoC promise gate

The project may enter Phase 5 only if **all** of the following hold on the untouched temporal test set, aggregated over three registered optimization seeds:

1. **Primary quality:** RIPPLE NDCG@10 is at least 5% relatively above frozen SentenceTransformer–FAISS, and a paired user bootstrap 95% confidence interval for the absolute difference excludes zero.
2. **ANN-specific mechanism:** RIPPLE NDCG@10 is at least 1% relatively above both the matched random-negative adapter and the matched exact full-matrix hard-negative adapter.
3. **Collaborative relevance:** RIPPLE NDCG@10 is at least 90% of a train-only BPR-MF baseline's NDCG@10.
4. **Candidate safety:** Recall@50 is not lower than the frozen vector baseline.
5. **Preference safety:** intrusion@10 by low-rated items in the untouched future test window is not worse than the frozen vector baseline.
6. **Serving budget:** p95 retrieval-plus-rerank latency is at most 1.25× the frozen FAISS baseline under the same process, index, query set, warmup, repetition count, filtering, and rerank wrapper.
7. **Maintenance:** item-matrix and immutable serialized-index fingerprints are unchanged across alignment training.
8. **Optimization stability:** at least two of three registered RIPPLE seeds individually exceed the frozen baseline on NDCG@10.

If any criterion fails, this exact design is marked a dead end, Phase 5 is forbidden, and the sprint returns to Phase 1 with the failed mechanism recorded.

## Scope and non-claims

- The PoC tests *promise*, not billion-item production readiness.
- MovieLens titles and genres are only a small metadata proxy for real catalog text.
- Explicit low ratings are treated as reliable rejections; unobserved index neighbors are treated as hard confusions, not asserted dislikes.
- The PoC does not claim that a small query adapter reproduces all reasoning capacity of an LLM.
- Novelty is claimed only for the evaluated systems intersection, not for SimPO, low-rank adapters, hard-negative mining, fixed indexes, or adaptive ANN independently.

## Decision table

| Outcome | Action |
|---|---|
| All eight criteria pass | Proceed to Phase 5; limit claims to measured evidence. |
| Quality passes but random/exact-hard mechanism control fails | Kill RIPPLE as an ANN-conditioning contribution; return to Phase 1. |
| Vector-baseline gate passes but BPR non-inferiority fails | Kill RIPPLE as not practically competitive; return to Phase 1. |
| Quality passes but latency/index safety fails | Kill the deployability claim and return to Phase 1. |
| Quality fails | Kill the design immediately and return to Phase 1. |
