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
| 8 | 2026-08-07 | invalid_attempt | First execution produced child artifacts, but the external verifier looked one directory above the runner's documented `ripple_poc_runs/` namespace. No external completion marker exists; metrics were not inspected and the attempt is excluded. Patched only the verifier path binding before rerun. |
| 9 | 2026-08-07 | verifier_patch | The second runner completed, but Windows used a venv shim PID distinct from the actual Python PID recorded in the marker. Patched verification to require that both processes have exited rather than require PID equality, and added a verifier for the untouched existing run so no scientific rerun is needed. |
| 10 | 2026-08-07 | completed_outcome | Externally verified the untouched PoC: all artifact hashes, logs, PID exit, lock release, and empty error ledger passed. The preregistered promise gate returned false. |
| 11 | 2026-08-07 | kill_decision | Killed RIPPLE v1 immediately. Failed G1 (CI), G2 (exact-hard control), G3 (BPR non-inferiority), and G4 (Recall@50). Phase 5 prohibited; outer loop reset to Phase 1 cycle 2. |
