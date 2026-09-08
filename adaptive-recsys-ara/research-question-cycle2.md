# Phase 2, Cycle 2: CAPER Research Question and Kill Gate

## Primary research question

> **Can a reference-model-free preference residual trained on the actual semantic–collaborative FAISS union improve temporal top-10 relevance and explicit preference accuracy over a strong BPR recommender, while a hard per-request collaborative-regret projection preserves candidate support, ranking safety, and low-latency serving?**

This addresses preference alignment rather than attempting to replace collaborative retrieval. It is empirically testable on an unopened benchmark and distinct from RIPPLE v1.

## Concrete hypothesis

On a chronological MovieLens 1M proof of concept, CAPER will:

1. retrieve the immutable union of BPR-factor and SentenceTransformer candidates, with every BPR anchor candidate retained;
2. use a bounded residual trained by a SimPO-derived chosen/rejected margin loss on rating-gap pairs that were naturally present in the served union;
3. focus half of its training budget on observed BPR contradictions;
4. project its proposed top-10 list into a feasible set whose summed normalized BPR-score regret is below the prospectively fixed `0.12` budget;
5. improve NDCG@10 and held-out preference-pair accuracy without materially lowering Recall@10 or increasing future low-rating intrusion.

## Why it is high impact

- **Alignment:** explicit preference evidence can correct concrete collaborative mistakes rather than act as a generic negative sampler.
- **Safety:** candidate inclusion is deterministic and BPR-surrogate regret is bounded per request; true ranking safety is separately tested.
- **Scale:** both item indexes are immutable during alignment, and the residual operates only on a bounded union.
- **Latency:** the system uses two parallelizable vector searches and a small feature scorer, with no online LLM decode or DPO reference model.

## Non-claims

- CAPER does not claim novelty for hybrid retrieval, BPR, rank preservation, hard-negative mining, or SimPO individually.
- The regret projection bounds a BPR score surrogate, not true user utility; it is not a safe-policy theorem.
- A MovieLens PoC does not establish million-item latency or production impact.
- The one-step ranking loss is SimPO-derived and algebraically related to margin-shifted BPR/RankNet.

## Nine-part promise gate

Phase 5 is allowed only if every condition holds on the sealed test block, aggregating three registered optimization seeds:

1. **Relevance gain:** CAPER NDCG@10 is at least 2% relatively above the stronger of implicit BPR and rating-aware BPR, and the paired user-cluster bootstrap 95% lower bound for the absolute difference is above zero.
2. **Mechanism:** CAPER NDCG@10 exceeds the strongest constraint-matched projected linear-fusion, zero-margin residual, unanchored SimPO, and uniform-pair residual ablation; every comparison uses the same candidate union and hard regret budget, and the paired lower bound versus that strongest feasible ablation is above zero. The unprojected soft-anchor-only model remains a safety diagnostic rather than an unfair raw-relevance hurdle.
3. **Preference accuracy:** on held-out within-user pairs with a rating gap of at least two, CAPER accuracy is at least 3 percentage points above the stronger BPR baseline with a paired lower bound above zero.
4. **Top-rank safety:** the paired-bootstrap lower bound for CAPER-minus-BPR Recall@10 is greater than `-0.005` absolute.
5. **Candidate support:** `B_u ⊆ C_u` holds for every request and candidate recall over the variable-size union `C_u` (at most 400 items) is never below candidate recall over the registered BPR branch `B_u` at `K_b=200`; the union is not mislabeled as a fixed-cutoff Recall@200 list.
6. **Dislike safety:** the paired user-cluster-bootstrap 95% upper bound for CAPER-minus-BPR future low-rating intrusion@10 is no more than `0.002` absolute.
7. **Seed stability:** at least two of three CAPER seeds beat both BPR and the strongest matched ablation on NDCG@10.
8. **Serving budget:** single-thread CPU p95 is at most 20 ms and at most 1.25 times the matched dual-index linear-fusion pipeline, including both searches, deduplication, features, projection, and sorting.
9. **Integrity:** semantic/collaborative item matrices and both FAISS indexes remain hash-identical; candidate targets are never injected; temporal/provenance checks and asynchronous-error ledger all pass.

Missing values, fewer than 500 eligible test users, fewer than 500 held-out preference pairs, fewer than 300 pair-bearing users, fewer than 100 BPR-agreement or 100 BPR-contradiction pairs, an empty comparison cohort, or any integrity failure fails closed. The same 300/100/100 raw-count floors apply to the alignment corpus before replacement sampling.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

If false, CAPER is killed and the sprint returns to Phase 1 again. There is no discretionary override or test-set retuning.
