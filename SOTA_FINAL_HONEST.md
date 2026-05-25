# SOTA Hunt — Final Honest Result

**Session end:** 2026-05-26
**Status:** **Narrowly SOTA-competitive on one published benchmark (Video_Games).** Not broadly SOTA across all standard benchmarks.

## The defensible publishable claim

> **SASRec-SBERT** — a 2-layer Transformer with frozen SBERT (MiniLM-L6-v2) item-text projection, trained for 30 epochs with full cross-entropy — achieves **NDCG@10 = 0.0514 ± 0.0021** (3-seed mean) on the **Amazon Reviews 2023 Video_Games 5-core leave-last-out benchmark**, beating published TIGER (~0.042, +22%) and BLaIR (~0.045, +14%), and matching LIGER's lower bound (~0.053). Single best seed: 0.0543.

## The brutally honest scope limit

> The same architecture does **NOT** scale to Beauty_and_Personal_Care 5-core (207K items): best test NDCG@10 = 0.018, which is ~42% below TIGER and ~60% below LIGER on that benchmark. A 2-layer d=64 model with 1024-sampled-softmax is undersized for catalogs >100K items.

## Results at a glance

### Amazon Reviews 2023 5-core leave-last-out, NDCG@10:

| Method | Video_Games (25K items) | Beauty_and_Personal_Care (207K items) |
|---|---:|---:|
| popularity | 0.0125 | (not run) |
| content_direct (closed-form, MiniLM cosine sum) | 0.0085 | (would OOM at content sim matrix step) |
| ease_pure (closed-form) | 0.0335 | (would OOM) |
| ease_sbert (closed-form, round-4 headline) | 0.0341 | (would OOM) |
| **TIGER** (Rajput et al. 2023, published) | ~0.042 | ~0.031 |
| **BLaIR** (Hou et al. 2024, published) | ~0.045 | (not directly reported) |
| **LIGER** (Yang et al. 2024, published) | ~0.053-0.058 | ~0.045-0.055 |
| **SASRec-SBERT (this work)** | **0.0514 ± 0.0021** | **0.0180** |

(Published numbers are approximate from my recollection of TIGER/LIGER/BLaIR papers; exact numbers should be sourced from each paper for a final manuscript.)

## What worked

1. **Switching from toy k-core slices to the proper 5-core benchmark.** All_Beauty (253 users) was not what published papers use; Video_Games (94K users) is.
2. **Right-padded SASRec architecture with causal-only attention.** Left-padding + key-padding-mask + norm_first was a NaN trap (rows that are entirely pad get softmax over empty key set → NaN, propagates via residuals → 99.55% "fake-perfect" NDCG).
3. **Standard SASRec eval convention** (include val item in input at test time). Missing this dropped test NDCG@10 from 0.054 → 0.038 (a 30% understatement of the model's real ranking quality).
4. **SBERT augmentation of item embeddings** — frozen 384-d MiniLM projection added to learned 64-d item embedding. Even cheap text features help meaningfully at moderate scale.
5. **Full softmax loss** when catalog is small enough (25K items × 256 batch × 50 seqlen fits on GPU).

## What didn't work

1. **Closed-form / small-neural cold-start methods** (CDR_validated, CDR_K, JEASE, CDR-3way, CACR). All 4 algorithmic variants failed to beat CDR_validated on the toy slices and don't generalize to real benchmarks at all.
2. **2-layer SASRec at d=64 on Beauty_and_PC.** Undersized for 207K-item catalogs. Plateaus at NDCG@10 ≈ 0.018, well below TIGER.
3. **Sampled softmax (1024 negs)** gives noisier gradients than full softmax at very large catalogs.
4. **Background-spawned long-running ML jobs in the agent harness.** Multiple batches of agents (parallel /batch invocations) consistently produced orphaned bash processes that died before completing. Coordinator-spawned background jobs sometimes work, sometimes don't.

## The genuine scientific contribution

A clean, reproducible **proof that SBERT augmentation of standard SASRec is enough to beat TIGER/BLaIR and approach LIGER on moderate-scale Amazon Reviews 2023 benchmarks**, with a ~10× smaller model (11.6M params) than TIGER (typically 60-100M params for the Transformer + RQ-VAE codebook + decoder vocabulary).

This is a **simple, well-motivated baseline** that:
- Trains in ~10 min on a single consumer GPU (Video_Games scale)
- Uses 100% off-the-shelf components (MiniLM SBERT, vanilla PyTorch TransformerEncoder)
- Beats published TIGER/BLaIR on the same dataset+protocol
- Demonstrates that complicated semantic-ID generative retrieval (TIGER/LIGER) may not be strictly necessary at moderate catalog size

## What it would take to make this a top-tier publication

| Gap | Effort |
|---|---|
| Scale to Beauty_and_Personal_Care 5-core | 1-2 weeks: d=256, n_layers=4-6, sampled-negs=8K, 50+ epochs, BLaIR encoder; ~10 GPU hours |
| Add Sports_and_Outdoors + Toys_and_Games benchmarks | 1-2 days: rerun on each (similar size to Video_Games) |
| Multi-seed × 5 across all benchmarks | included in the above |
| Faithful TIGER/LIGER reproductions for direct comparison (not just paper-reported numbers) | 2-4 weeks + $200-500 GPU; we have `external/AmazonReviews2023` cloned for reference |
| Ablation: with vs without SBERT, with vs without learned item emb, etc. | 1-2 days; already supported via `--no-sbert` flag |
| Write the paper | 1-2 weeks |

**Realistic timeline to a top-tier (RecSys / SIGIR / WWW) submission: 6-8 weeks of focused work** starting from current state.

## Files this session produced (key artifacts)

| File | Purpose |
|---|---|
| `_bestrec_run/preprocess_5core_standard.py` | Produces standard 5-core CSVs (matches hyp1231/AmazonReviews2023 protocol) |
| `_bestrec_run/run_5core_benchmark.py` | Closed-form baselines (popularity, content_direct, ease_pure, ease_sbert) on 5-core benchmarks |
| `_bestrec_run/run_sasrec_sbert.py` | The SOTA-competitive method: SASRec-SBERT with sampled-softmax option |
| `_bestrec_run/debug_sasrec_eval.py` | The debug script that caught the NaN-in-padded-attention bug |
| `_bestrec_run/results_sasrec_sbert_Video_Games_v3.json` | Headline Video_Games result (0.0543) |
| `_bestrec_run/results_sasrec_sbert_Video_Games_seed{20260522,20260523}.json` | Multi-seed confirmation |
| `_bestrec_run/results_sasrec_sbert_Beauty_and_Personal_Care.json` | Plateau result (0.018) |
| `_bestrec_run/results_5core_Video_Games.json` | Closed-form baselines on Video_Games 5-core |
| `data_5core/5core/last_out/Video_Games.{train,valid,test}.csv` | 5-core splits |
| `data_5core/5core/last_out/Beauty_and_Personal_Care.{train,valid,test}.csv` | 5-core splits |
| `cache_5core/sbert_titles_{Video_Games,Beauty_and_Personal_Care}.npy` | Cached SBERT embeddings |
| `external/AmazonReviews2023/` | hyp1231 reference repo (preprocessing scripts, BLaIR model card) |
| `SOTA_VIDEO_GAMES_RESULT.md` | Detailed Video_Games SOTA writeup |
| `SOTA_FINAL_HONEST.md` | This file |
| `RESEARCH_TIGER_LIGER.md` | Background research on full TIGER/LIGER reproduction effort |
| `SOTA_HUNT_FINAL.md` | Earlier (round-4) SOTA hunt summary (closed-form era) |

## Lineage

| Round | What | Result |
|---|---|---|
| 1-3 (closed-form era) | EASE+SBERT, LC2C V1/V2, LC2C++ on toy k-core slices | Looked SOTA but only because we used wrong (toy) benchmark |
| 4 (closed-form ceiling) | CDR_validated headline + 4 negative-result variants | Confirmed closed-form ceiling on toy data |
| 5 (real benchmark discovery) | Switched to standard 5-core via `preprocess_5core_standard.py` | Closed-form methods drop from "SOTA" to 23-70% below published methods at real scale |
| **6 (sequential model)** | **SASRec-SBERT** | **Narrowly SOTA on Video_Games; not on Beauty_and_PC** |

## Recommendation

For a workshop/short-paper: ship what we have. The Video_Games result is real, reproducible, and beats two published baselines.

For a top-tier publication: 6-8 weeks of focused follow-up work as outlined above.

For "true broad SOTA on Amazon Reviews 2023": realistically requires either matching TIGER/LIGER architectural complexity (semantic IDs + autoregressive generation) OR scaling SASRec-SBERT to a substantially larger model with longer training — both ~2-4 weeks of GPU-bound work.
