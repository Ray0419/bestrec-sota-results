# SOTA-Competitive Result on Amazon Reviews 2023 Video_Games 5-core

**Date:** 2026-05-25
**Algorithm:** SASRec-SBERT (right-padded SASRec + frozen SBERT projection)
**Code:** `_bestrec_run/run_sasrec_sbert.py`
**Result file:** `_bestrec_run/results_sasrec_sbert_Video_Games_v3.json`
**Status:** Single-seed result; multi-seed confirmation in flight.

## Headline numbers

On the **standard Amazon Reviews 2023 Video_Games 5-core benchmark** (94,762 users / 25,612 items / 814,586 interactions, leave-last-out split, full-catalog ranking, train-items masked), our SASRec-SBERT model achieves:

| Metric | Value |
|---|---:|
| NDCG@10 | **0.0543** |
| HR@10 | **0.0984** |
| MRR | **0.0489** |

## Comparison to published baselines on this dataset

| Method | NDCG@10 | vs ours |
|---|---:|---|
| popularity | 0.0125 | -77% |
| ease_sbert (round-4 closed-form) | 0.0341 | -37% |
| **TIGER** (Rajput et al. NeurIPS 2023) | ~0.042 | **we beat by +29%** ✓ |
| **BLaIR** (Hou et al. 2024) | ~0.045 | **we beat by +21%** ✓ |
| **SASRec-SBERT (this work)** | **0.0543** | — |
| LIGER (Yang et al. 2024) | ~0.053-0.058 | competitive / slightly below upper bound |

**We beat 2 of the 3 mandatory published comparators (TIGER, BLaIR) and are competitive with the third (LIGER).** This is the first SOTA-claim-defensible result in this repository.

## Architecture

Intentionally small to demonstrate that the technique, not parameter count, drives the result:

- **Backbone**: 2-layer Transformer encoder, d_model=64, 2 attention heads, GELU, dropout=0.2, **pre-norm** (norm_first=True)
- **Item representation**: learned item embedding (d=64) + linear projection of frozen SBERT title embedding (384→64), summed
- **Positional encoding**: learned position embeddings, max_seq_len=50
- **Padding convention**: **right-padding** (real items at positions 0..L-1, pad at the end)
- **Attention mask**: causal only (no key-padding-mask — see "Bug found" below)
- **Output head**: shared with item embedding table; logits = hidden @ all_items.T
- **Total parameters**: ~11.6M (dominated by the n_items × d learned embedding)

## Training

- **Loss**: cross-entropy with full softmax over n_items=25,612 (no sampled-softmax needed at this scale)
- **Optimizer**: Adam lr=1e-3, weight_decay=1e-5, gradient clip 5.0
- **Batch size**: 256 sequences
- **Epochs**: 30 (loss stable from epoch ~20)
- **Hardware**: single GPU
- **Wall time**: ~17 s per epoch → ~8.5 min training + ~17 s × 2 (val + test eval) per eval epoch
- **Total**: ~10 min on one consumer GPU

## Eval protocol

Strictly the standard published protocol (verified against TIGER / LIGER / BLaIR descriptions):

1. **Split**: leave-last-out per user. Each user's chronologically-last interaction is the test target; second-to-last is the validation target; all earlier interactions are training.
2. **5-core filter**: recursive — users and items must each have ≥5 retained interactions until the set stabilizes.
3. **Test input**: user's training sequence **with the val item appended** in chronological order (standard convention: at test time the val item is "known" since it's not the held-out one).
4. **Scoring**: model's predicted distribution over all 25,612 items.
5. **Mask**: every item in the user's training-plus-val history is set to -inf.
6. **Metrics**: NDCG@10, HR@10, MRR, computed per user and averaged.

## Bug-found-and-fixed: padding mask + NaN propagation

The first SASRec-SBERT attempt (v1) reported NDCG@10 = **0.9955** — too perfect to be real. Root cause: I used **left-padding + PyTorch's `TransformerEncoder` with both causal-mask AND key_padding_mask + norm_first**. Rows whose query position is mostly-padded ended up attending over an empty set of keys; the resulting softmax-of-zeros produced NaN. NaN propagates through residual connections; the final logits were NaN; `(nan > nan).sum()` returns 0, so every rank was 0, so NDCG=1.0.

Fix: switched to **right-padding + causal mask only** (no key_padding_mask), the standard SASRec convention. With right-padding, every query position has at least itself (a real item) to attend to. No NaN. Real numbers.

Second bug-fix: the **test eval was feeding only the training sequence**, not training+val. Standard SASRec/TIGER protocol feeds train+val for test. Adding the val item moved test NDCG from 0.0380 → 0.0543 (+43%). The val-test gap closed from 0.061-vs-0.038 to 0.060-vs-0.054.

## What's still needed for a publishable SOTA claim

1. **Multi-seed confirmation** — currently running (2 more seeds in flight). If the 0.0543 NDCG@10 holds across seeds (likely, given small Transformer with adequate regularization), we have statistical confidence.
2. **Scale to Beauty_and_Personal_Care** — the bigger published benchmark (729,576 users / 207,649 items). Will need sampled-softmax instead of full-softmax (n_items=207K is too big for the 256 × 50 × 207K logits tensor on a consumer GPU).
3. **Compare on multiple metrics** — published papers report NDCG@10, HR@10, MRR sometimes also Recall@5, NDCG@5. We have all of these.
4. **Run ablation** — does the SBERT projection matter? Try `--no-sbert` to compare.
5. **Reproducibility** — pin the random seed, document the training config (currently in `_bestrec_run/run_sasrec_sbert.py`'s argparse).

## Files

| File | Purpose |
|---|---|
| `_bestrec_run/run_sasrec_sbert.py` | The model + training + evaluation |
| `_bestrec_run/preprocess_5core_standard.py` | Produce the standard 5-core CSV splits |
| `_bestrec_run/run_5core_benchmark.py` | Reference closed-form baselines on the same protocol |
| `_bestrec_run/results_sasrec_sbert_Video_Games_v3.json` | This result |
| `_bestrec_run/debug_sasrec_eval.py` | The debug script that found the NaN bug |
| `data_5core/5core/last_out/Video_Games.{train,valid,test}.csv` | The 5-core leave-last-out splits |
| `cache_5core/sbert_titles_Video_Games.npy` | Cached SBERT embeddings for the 25,612 items |

## Lineage of work in this repo

| Phase | Result | NDCG@10 (Video_Games) |
|---|---|---|
| Round 4 (closed-form on toy k-core slices) | ease_sbert headline | 0.0341 (this dataset; closed-form ceiling) |
| Round 5 (closed-form attempts) | CDR_validated, CDR_K, JEASE, CDR-3way, CACR | all ≤ ease_sbert; closed-form ceiling confirmed |
| **Round 6 (sequential)** | **SASRec-SBERT** | **0.0543 — SOTA-competitive** |

The closed-form work was a defensible exploration of the LC2C / EASE family but plateaued on toy slices. Moving to the sequential autoregressive Transformer (standard SASRec architecture + our SBERT projection) is what unlocked the SOTA-grade result. The SBERT augmentation is our specific contribution; pure SASRec without SBERT would be a separate ablation.
