# Research Log

Chronological, append-only record of research decisions and actions.

| # | Date | Type | Summary |
|---|---|---|---|
| 1 | 2026-08-07 | bootstrap | Initialized an isolated autoresearch workspace. Registered a hard PoC gate: a failed design is killed and the sprint returns to Phase 1; Phase 5 is forbidden without measured promise. |
| 2 | 2026-08-07 | literature | Completed three parallel evidence scans covering vector retrieval, LLM/preference alignment, and integrated system gaps; verified primary sources and marked 2025–2026 preprints as provisional. |
| 3 | 2026-08-07 | ideation | Generated 12 candidate directions using constraint manipulation, negation, boundary-failure analysis, bisociation, and reformulation. |
| 4 | 2026-08-07 | decision | Selected RIPPLE: a query-only SimPO adapter trained against the deployed ANN boundary, paired with uncertainty-budgeted search. Explicitly rejected novelty claims already occupied by SimPO, RecPO, S-DPO, RosePO, retrieval-conditioned reranking, Quake, and generic index-preserving adaptation. |
| 5 | 2026-08-07 | preregistration | Locked the Phase 2 research question and a six-part PoC promise gate covering NDCG uplift, matched-mechanism uplift, Recall@50, dislike intrusion, p95 latency, and immutable index fingerprints. |
| 6 | 2026-08-07 | rigor_revision | Before any outcome run, strengthened the gate to eight criteria: added an exact-hard-negative mechanism control, BPR-MF non-inferiority, three-seed stability, and a non-degenerate future-dislike definition. |
| 7 | 2026-08-07 | implementation | Completed the Phase 3 CPU runner with SentenceTransformer item encoding, real FAISS IVF retrieval, random/exact/ANN-boundary SimPO-derived adapters across three seeds, BPR-MF, bootstrap, interleaved latency, immutable hashes, and explicit G1–G8 evaluation. Syntax and CLI validation passed; no outcome was run. |
