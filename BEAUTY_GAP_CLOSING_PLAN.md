# Beauty_and_PC gap-closing plan

**Goal**: Push Beauty_and_PC SASRec NDCG@10 from current best 0.0191 toward published LIGER ~0.045 (currently 58% short).

**Strategy this session**: Test 3 encoder hypotheses, then 1 architecture-scale experiment.

## Decision matrix

| Experiment | Hypothesis | Expected Result | If wins | If ties baseline |
|---|---|---|---|---|
| 1. BLaIR encoder (running) | Amazon-domain text > general MiniLM | NDCG@10 = 0.020-0.024 | Run #3 (fusion) | Skip to #4 |
| 2. Rich-text MiniLM | Category context helps cryptic SKU titles | NDCG@10 = 0.020-0.024 | Run #3 (fusion) | Skip to #4 |
| 3. Fusion (BLaIR + rich-text) | Additive gains | NDCG@10 = 0.022-0.028 | Stop & write up | Skip to #4 |
| 4. d=128 + augment-2 + best-encoder | Capacity bottleneck | NDCG@10 = 0.022-0.030 | Stop & write up | Architectural ceiling confirmed |

## Reference baselines (full 729K eval)

| Method | Beauty NDCG@10 | Notes |
|---|---:|---|
| popularity | (not run) | trivial floor |
| BERT4Rec | 0.0160 | |
| SASRec d=64 sampled-1024 | 0.0180 | original baseline |
| SASRec d=128 sampled-1024 | 0.0176 | no width gain |
| SASRec d=64 chunked-full | 0.0191 | proper-softmax baseline (best to date) |
| SASRec d=128 chunked-full | 0.0186 | width doesn't help |
| SASRec d=64 long (25e) | 0.0189 | length doesn't help |
| SASRec d=64 in-batch+aug2 | 0.0036 | train-test shift |
| SASRec d=64 hybrid+aug3 | 0.0106 | better than in-batch, still bad |
| TIGER minimal | 0.008 | undertuned |
| SBERT-only | killed | 3.3× slower, worse loss → falsified |
| **TIGER (published)** | **~0.031** | target #1 |
| **LIGER (published)** | **~0.045+** | target #2 |

## Time budget

- BLaIR encoder swap: ~3-4 hrs (running, ETA ~4 PM today)
- Rich-text encoder: ~2 hrs (queue after BLaIR)
- Fusion (1152-d): ~3 hrs (queue after rich-text if either shows gain)
- d=128 + augment: ~6-8 hrs (only if encoder experiments tie baseline)

## What was already ruled out

From earlier session work:
- **Sampled softmax variance is not the bottleneck** (chunked-full only gave +6%)
- **Encoder choice on Video_Games**: BLaIR ≈ MiniLM (tied at 0.050-0.051)
- **Model width**: d=128 ≈ d=64 (tied at 0.018)
- **Training length**: 25e ≈ 15e (tied)
- **In-batch/hybrid losses**: train-test shift makes worse
- **SBERT-only embedding**: too slow + worse loss

## Honest assessment

The 58% gap reflects an architectural limit: SASRec's d=64 per-item embeddings cannot match TIGER/LIGER's shared-vocabulary semantic IDs at 207K-item catalogs. The text encoder experiments here are unlikely to bridge that gap entirely, but every 0.001 increment matters for the publication claim.

Realistic best-case for this session: **0.025 NDCG@10** (fusion + augment-2), closing ~25% of the gap.
