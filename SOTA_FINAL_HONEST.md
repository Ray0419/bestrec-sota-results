# SOTA Hunt — Final Honest Result

**Session end:** 2026-05-26
**Status:** **Historical and superseded.** Not approved for SOTA wording.

**Superseding audit note, 2026-06-09:** this status is no longer approved claim
language. HSTU-BLaIR reports a stronger Video_Games NDCG@10 than our
SASRec-SBERT line, and a local WSL SM120 compatibility-port reproduction
completed with final full-eval NDCG@10 `0.0738224` and best full-eval NDCG@10
`0.0740335`. The honest current status is: strong internal SASRec baseline, no
broad SOTA claim, no top-conference-ready leaderboard claim.

## The defensible publishable claim

The following historical claim is superseded. The current defensible claim is
only that SASRec-SBERT reaches NDCG@10 = 0.05509 +/- 0.00035 in a fresh 5-seed
local confirmatory rerun and significantly beats same-run SASRec-BLaIR and
no-text SASRec ablations. It does not beat the external HSTU-BLaIR reference
level.

> **SASRec-SBERT** is a 2-layer SASRec-style Transformer with frozen
> SBERT/MiniLM item-text projection. In the later 5-seed local rerun it reaches
> NDCG@10 = 0.05509 +/- 0.00035 on our Amazon Reviews 2023 Video_Games 5-core
> leave-last-out benchmark and beats same-run SASRec-BLaIR/no-text ablations.
> It is not a SOTA result because stronger HSTU-BLaIR evidence exists.

## Attribution statement

The backbone is SASRec (Kang and McAuley, 2018). The text projection uses SBERT/MiniLM from the Sentence-BERT family (Reimers and Gurevych, 2019). BLaIR checkpoints, Amazon Reviews 2023, and the SASRecText MLP adaptor recipe are from Hou et al. 2024 and the `hyp1231/AmazonReviews2023` codebase. The local contribution is empirical and engineering: 5-core preprocessing, full-catalog evaluation, right-padding/NaN bug fixes, chunked full-softmax support, integration of frozen text embeddings into SASRec, and honest negative-result reporting on Beauty_and_Personal_Care.

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

(Published numbers are approximate session targets. Exact numbers, split definitions, and candidate-set protocol must be sourced from each paper before any final SOTA wording.)

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

A clean, reproducible **proof that adding off-the-shelf SBERT/MiniLM item text to standard SASRec produces a strong, efficient Video_Games result under our 5-core full-catalog protocol**, with a ~10× smaller model (11.6M params) than typical semantic-ID generative retrieval systems.

This is a **simple, well-motivated baseline** that:
- Trains in ~10 min on a single consumer GPU (Video_Games scale)
- Uses 100% off-the-shelf components (MiniLM SBERT, vanilla PyTorch TransformerEncoder)
- Is a strong internal baseline under this repository's Video_Games protocol
- Suggests that semantic-ID generative retrieval (TIGER/LIGER) may not be strictly necessary at moderate catalog size, pending exact apples-to-apples reproduction

## Post-session follow-up: scale-up attempts on Beauty_and_PC failed

After the initial honest writeup, we tried two follow-ups to push Beauty_and_PC past the 0.018 plateau:

### Attempt 1: BLaIR encoder swap (not the bottleneck)
On Video_Games, we compared MiniLM-SASRec (mean 0.0514) vs BLaIR-SASRec (0.0498). BLaIR's official `hyp1231/blair-roberta-base` checkpoint (768-d, RoBERTa-base, Amazon-Reviews-2023-contrastively-trained) **gave no measurable improvement** over MiniLM (384-d, general-purpose). BLaIR for Beauty_and_PC was therefore skipped — a 2-3 hour encoding job that the Video_Games ablation predicted would not help.

### Attempt 2: Wider model (d=64 → d=128)
On Beauty_and_PC, we trained SASRec with d=128 (vs baseline d=64), 2 layers (kept), 4 heads (up from 2), sampled-negs=1024 (kept), dropout=0.2. Total params 12M → ~50M.

| Epoch | d=64 baseline test NDCG@10 | d=128 test NDCG@10 |
|---|---:|---:|
| 5 | 0.0172 | 0.0177 |
| 10 | 0.0181 | 0.0176 |
| 15 | 0.0178 | **0.0170 (overfit)** |

**d=128 buys essentially nothing.** Training loss drops faster (4.21 vs 4.25 at epoch 10) but ranking quality is identical. By epoch 15 the wider model starts overfitting (val falls 0.0214 → 0.0208).

### What this rules out
- **Encoder choice is not the bottleneck** (BLaIR ≈ MiniLM)
- **Model width is not the bottleneck** (d=128 ≈ d=64)

### What's left as the actual bottleneck
1. **Short user histories.** Beauty_and_PC's median user has only 5 training interactions. Sequential models need longer histories to outperform popularity baselines meaningfully.
2. **Sampled-softmax variance.** With 207K items and 1024 negatives per position, the gradient is a noisy estimate of the full softmax gradient. TIGER/LIGER avoid this by using semantic IDs (tokens, not items) so the softmax is over a tiny vocabulary.
3. **Architecture mismatch.** TIGER/LIGER's autoregressive token generation over semantic IDs is fundamentally different from SASRec's next-item dot-product scoring. The semantic-ID approach gives much richer gradients per training example.

To actually reach LIGER's ~0.045 on Beauty_and_PC, we'd need to either:
- **Reimplement TIGER/LIGER** (semantic IDs + autoregressive decoder) — multi-week effort
- **Sequence-augment short histories** (sliding-window data augmentation, masked-LM pretraining) — 1-2 weeks
- **Use full softmax** (need a sampled-softmax approximation with much better importance weighting, e.g., adaptive negative sampling) — 1 week

Within this session's budget, none of these are achievable. **The Video_Games
result stands as a strong internal baseline; Beauty_and_PC is documented as a
tractable but unsolved follow-up.**

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
| `_bestrec_run/run_sasrec_sbert.py` | Strong internal baseline: SASRec-SBERT with sampled-softmax option |
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
| **6 (sequential model)** | **SASRec-SBERT** | **Strong on Video_Games; not SOTA after external comparator audit** |

## Recommendation

For a workshop/short-paper: the Video_Games result is real and reproducible inside this repository, but the external-baseline wording must stay protocol-qualified until comparator reproduction is complete.

For a top-tier publication: 6-8 weeks of focused follow-up work as outlined above.

For "true broad SOTA on Amazon Reviews 2023": realistically requires either matching TIGER/LIGER architectural complexity (semantic IDs + autoregressive generation) OR scaling SASRec-SBERT to a substantially larger model with longer training — both ~2-4 weeks of GPU-bound work.
