# Phase 4 Preregistered PoC Protocol — RIPPLE v1

**Status:** frozen before any outcome run.

**Executable configuration:** `../src/configs/ripple_poc_ml100k.json`; `config-v1.yaml` is its human-readable mirror.

**Primary system:** ANN-boundary-trained RIPPLE at fixed `nprobe=4`.

**Exploratory only:** ambiguity-routed `nprobe`; it cannot rescue a failed primary gate.

## 1. Data and temporal separation

Use official GroupLens MovieLens 100K `u.data` and `u.item`. Record the archive and extracted-file SHA-256 hashes. Sort each user's events by `(timestamp, original_row_id)` so tied timestamps are deterministic.

- Positive event: rating at least 4.
- Explicit dislike: rating at most 2.
- Neutral event: rating 3.
- Split each eligible user's ordered events into 80% train, 10% validation window, and 10% untouched test window using floor boundaries.
- Validation target: the first rating at least 4 inside the validation window.
- Test target: the first rating at least 4 inside the test window.
- Adapter examples: positive events inside the training window having at least two earlier training positives.
- Validation query: the training window only.
- Test query: training plus the complete validation window, which is genuinely past at test time.

The test window is never used for pair mining, hyperparameters, router calibration, or early stopping. Catalog metadata for every item is allowed under a declared fixed-catalog transductive setting. Users without at least five total positives, a positive target in each future window, eight training events, and two training positives are excluded prospectively.

## 2. Frozen SentenceTransformer representation

Encode `title [SEP] genres` once using the locally cached `sentence-transformers/all-MiniLM-L6-v2`, CPU inference, normalized float32 outputs, and ascending MovieLens item ID order. The PoC interaction query is the normalized centroid of prefix items rated at least 4. The richer recency/dislike aggregator in the full architecture is deferred to scaled experiments and is not part of this gate.

Write the item matrix once, make the in-memory array read-only, and hash `(ordered item IDs || contiguous matrix bytes)`. SentenceTransformer is never called inside the latency harness.

## 3. Immutable FAISS index

Build one deterministic normalized inner-product `IndexIVFFlat` with `nlist=32`; retain `IndexFlatIP` only as an audit oracle. The gate uses `nprobe=4`, 50 post-filter candidates, identical overfetch, positive-history filtering, and exact dot-product reranking for every dense variant.

The serialized IVF artifact is immutable. Per-query probing uses `SearchParametersIVF` when supported; otherwise `nprobe` is reset in memory but the index is never reserialized. Hash the original serialized bytes before training, before test evaluation, and after latency evaluation.

## 4. Matched preference variants

For each training prefix and chosen future training-positive item, all adapter variants share the same `q0`, chosen item, explicit low-rating pairs, pair count, reliability weights, initialization, batch order, epochs, and optimizer.

- **Random adapter:** select an eligible unobserved item uniformly.
- **Exact-hard adapter:** select the highest-scoring eligible unobserved item from the exact full item matrix.
- **RIPPLE:** query the actual IVF index with `stop_gradient(q_phi)` and select an eligible item at the candidate-admission boundary; if the positive is inside the boundary, select an eligible item ranked above it. Refresh pairs every epoch.

Prefix-rated items and the chosen item are ineligible unobserved negatives. Unobserved items are weak retrieval confusions, not asserted dislikes, and use the lower registered weight/margin. Genuine IVF-sourced pairs must constitute at least 95% of intended RIPPLE confusion pairs; otherwise the mechanism test fails closed. Pair IDs, source, fallback, and epoch are logged.

## 5. SimPO-derived training

The loss is

\[
-w\log\sigma\left[(\beta/\tau)(s^+-s^-)-\gamma\right]
+\lambda(1-q_\phi^\top q_0).
\]

For one-step item ranking this is algebraically a target-margin-shifted BPR/RankNet objective. It is described as SimPO-derived reference-free margin optimization; no new preference-loss claim is made. All constants and three seeds are fixed in `config-v1.yaml`. There is no early stopping and no test-dependent selection.

## 6. Baselines

- Standard BPR-MF trained only on permissible pre-test positive events with the locked settings.
- Frozen SentenceTransformer history centroid + fixed FAISS.
- Matched random-negative query adapter.
- Matched exact full-matrix hard-negative query adapter.
- RIPPLE with fixed probe count (primary).
- Ambiguity routing is specified architecturally but not implemented in PoC v1 and cannot affect its gate.

## 7. Metrics

For the one held-out positive per eligible user:

- NDCG@10 is zero if absent, else `1/log2(rank+1)`.
- Recall@50 is the hit indicator after common filtering/reranking.
- Future-dislike intrusion@10 uses items rated at most 2 anywhere in the untouched test window. These items are absent from the test query history, so the audit is non-degenerate. Report the cohort size and fail closed if fewer than 100 test users have at least one such item.

Also report absolute differences, hit counts, candidate source rates, per-seed values, popularity, BPR-MF, and flat-index oracle results.

## 8. Statistical test

Average each user's metric over the three RIPPLE seeds. Generate 10,000 paired user bootstrap resamples with replacement using seed `20260907`. Report the percentile 95% interval for RIPPLE-minus-frozen NDCG@10. A relative improvement is defined only if its comparator mean is positive; otherwise that criterion fails closed.

## 9. Latency and maintenance test

Precompute identical base history states. Time from immediately before identity/adapter transformation through ANN search, common filtering, exact candidate rerank, and top-10 materialization. Exclude index loading and SentenceTransformer encoding. Use one loaded index, ten untimed full passes, then five repetitions per query in alternating ABBA/BAAB baseline/RIPPLE order. Disable garbage collection during timed blocks and use `perf_counter_ns`.

Report absolute p50, p95, and p99 plus each seed's RIPPLE/frozen p95 ratio; gate on the worst seed. The router, if explored, gets separate low/high-route and routed-fraction statistics.

## 10. Eight-part kill gate

All conditions are mandatory:

1. RIPPLE NDCG@10 is at least 5% relatively above frozen FAISS and the paired-bootstrap absolute-difference lower bound is strictly positive.
2. RIPPLE NDCG@10 is at least 1% relatively above both random-negative and exact-hard-negative adapters.
3. RIPPLE NDCG@10 is at least 90% of BPR-MF NDCG@10.
4. RIPPLE Recall@50 is not below frozen FAISS.
5. RIPPLE future-dislike intrusion@10 is not above frozen FAISS.
6. Every RIPPLE seed's p95 latency is at most 1.25 times frozen FAISS p95.
7. Item-matrix and immutable serialized-index hashes match at every checkpoint.
8. At least two of three RIPPLE seeds individually beat frozen FAISS NDCG@10.

In addition, missing/NaN metrics, a nonempty asynchronous-error ledger, less than 95% genuine boundary-pair sourcing, fewer than 100 dislike-audit users, or a hash mismatch fails closed.

```text
PROMISING = G1 and G2 and G3 and G4 and G5 and G6 and G7 and G8
```

There is no discretionary override. If false, mark RIPPLE `dead_end`, preserve all evidence, forbid Phase 5, and return to Phase 1.

## 11. Windows-safe completion contract

The outcome launcher `src/launch_and_verify.py` invokes the registered venv interpreter directly with `-u`, one thread for every numerical backend, CPU-only execution, persistent stdout/stderr logs, an experiment-specific exclusive lock, asynchronous error hooks, unique append-only run directories, and a completion candidate containing artifact hashes. After child exit, the launcher independently verifies all hashes, the empty error ledger, PID, and lock release, binds stdout/stderr hashes, and writes an immutable external completion marker. Only that marker establishes a completed outcome.
