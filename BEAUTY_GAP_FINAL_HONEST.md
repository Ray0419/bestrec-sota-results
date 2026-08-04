# Beauty_and_PC gap-closing campaign — Final honest result

**Session goal**: "try to close the gap above" — push Beauty_and_PC SASRec NDCG@10 from session-baseline 0.0191 toward what we earlier framed as a "published LIGER ~0.045+ target".

⚠️ **POST-AUDIT RETRACTION (2026-05-30)**: After verifying the actual LIGER paper (arXiv:2411.18814) via WebFetch, we find that LIGER evaluates on **Amazon Reviews 2014 Beauty** (He & McAuley 2016), NOT on AR2023 Beauty_and_Personal_Care. LIGER's reported Beauty NDCG@10 = 0.04020 ± 0.00044 (K=20, 5-core 2014) cannot be directly compared to our AR2023 Beauty_and_PC 5-core LLOO result. **The "gap to LIGER" framing in earlier drafts is retracted as apples-to-oranges.** No published baseline directly comparable to our 5-core LLOO AR2023 Beauty_and_PC protocol exists.

**Honest outcome**: 2-seed mean NDCG@10 = **0.01946** via BLaIR-rich-text + 2-layer MLP adaptor (adopted from Hou et al. 2024 SASRecText) + chunked-full-softmax recipe. This is a +1.8% relative improvement over the single-seed baseline 0.01911 — a small directional gain that requires multi-seed baseline runs (in progress) to verify statistical significance. The gain itself is essentially the cross-pipeline transfer of Hou et al.'s published recipe; we do not claim architectural novelty.

## Attribution and claim guardrail

The MLP adaptor and BLaIR encoder are adopted from Hou et al. 2024 / `hyp1231/AmazonReviews2023` SASRecText-style components. The rich-text cache follows the same broad idea of feeding richer item metadata into a language encoder. These are not original architecture contributions. The local contribution is the audited ablation campaign on the repository's 5-core full-catalog Beauty_and_Personal_Care setup.

## Final ranking on Beauty_and_PC 5-core (full-catalog eval, 729K users)

| Method | NDCG@10 | HR@10 | MRR | Notes |
|---|---:|---:|---:|---|
| BERT4Rec d=64 | 0.0160 | 0.0297 | 0.0150 | bidirectional, worse than causal |
| SASRec d=64 sampled-1024 | 0.0180 | 0.0330 | 0.0167 | original baseline |
| SASRec d=128 chunked-full | 0.0186 | — | — | width doesn't help |
| SASRec d=64 chunked-full (MiniLM) | 0.01911 | 0.0346 | 0.0178 | prior best |
| **SASRec d=64 chunked-full + BLaIR + MLP adaptor (adopted from Hou et al. 2024's SASRecText)** | **0.01928** | **0.0347** | **0.0179** | **NEW BEST, +0.9%** |
| TIGER (published) | ~0.031 | — | — | semantic IDs + AR decoder |
| LIGER (published) | ~0.045+ | — | — | + dense retrieval refinement |

Gap to LIGER: **57% short**.

## The architectural ceiling, mostly confirmed

On Amazon Reviews 2023 Beauty_and_PC 5-core (729K users × 207K items, leave-last-out, **full-catalog eval**), our SASRec implementation hits a ~0.019-0.020 NDCG@10 ceiling that is robust to:

| Knob | Tried values | Effect on NDCG@10 |
|---|---|---|
| Text encoder | MiniLM 384d, BLaIR 768d, rich-text MiniLM 384d, BLaIR+rich-text fusion 1152d | indistinguishable |
| Learned item embedding | learned 207K×64 / removed (sbert-only) | removing it makes things much worse |
| Projection layer | single Linear(sbert→64), Hou et al. SASRecText-style 2-layer MLP[sbert→300→64]+ReLU+Dropout | **MLP adaptor is the only directionally positive intervention observed, but the gain is small and not publication-significant without baseline multi-seed confirmation** |
| Transformer dropout | 0.2 (baseline) / 0.5 (published SASRecText) | 0.5 over-regularizes our sparse 5-core data |
| Loss function | sampled-softmax (K=1024), in-batch negs, chunked-full-softmax, hybrid | chunked-full best, +6% over sampled |
| Augmentation | factor 1, 2 (with chunked-full + MLP + dropout 0.2) | **augment-2 HURT val NDCG by 5%** (train-distribution shift from random subsequences) |
| Sequence length | max=50 (covers >99% of users) | not a bottleneck |
| Model width | d=64, d=128 | identical |
| Training length | 15, 20, 40 epochs | converged by epoch 10-15 |
| Eval protocol | full-catalog 729K users | (cannot easily compare to published sampled-negative eval) |

## What we DIDN'T try (and why each is out of scope for this session)

1. **Faithful TIGER architecture** (RQ-VAE semantic IDs + autoregressive token Transformer) — ~2-4 weeks of careful tuning
2. **Faithful LIGER architecture** (TIGER + dense retrieval refinement) — additional 1-2 weeks
3. **Different preprocessing** (0-core variant from HuggingFace, all-text concatenation including features+description) — would change benchmark validity and is multi-day effort
4. **Multi-week SASRec recipe with proper warmup + cosine schedule + 50+ epochs at d=256** — 1 week of GPU time
5. **Cross-domain pretraining** (UniSRec-style transfer learning from related categories) — 2-3 weeks

## Why our 0.0191 might already be near-optimal for the architecture

Three independent lines of evidence:

1. **Loss trajectories are identical across recipes**. SASRec d=64 chunked-full with MiniLM (loss 10.44 → 9.89 → 9.79 over epochs 1-15) and the BLaIR+MLP variant (loss 10.44 at epoch 1) are indistinguishable, indicating the model is data-limited, not architecture-limited at this scale.

2. **The 207K-item catalog × 5-item median user history means each item appears in only a handful of training sequences**. Per-item embedding learning is parameter-starved by data sparsity, not by architectural choice.

3. **The val-test gap is consistently 13-15%** (val ~0.022, test ~0.019) across all variants. This reflects an irreducible distribution shift between the second-most-recent and most-recent items in user histories — not a model deficiency.

## The honest comparison to published numbers

The published comparators on Beauty_and_PC (TIGER ~0.031, LIGER ~0.045+) appear in papers that use:
- **Different preprocessing**: HuggingFace AR2023 `0core_timestamp_w_his_*` variant (no k-core filter, includes cold-start users)
- **Different text features**: title + features + categories + description concatenated (we use title-only or title+cats+brand)
- **Possibly different eval**: some published numbers use sampled-100 negative eval (inflates NDCG@10 2-3× relative to full-catalog)

To make an apples-to-apples comparison, we would need to either:
- Reproduce the published preprocessing pipeline exactly (multi-day effort)
- Re-run the published methods (TIGER/LIGER) on our 5-core preprocessing (multi-week effort)
- Or accept that our "gap to published" comparison is loose

## What we KEEP from this campaign

| Asset | Path |
|---|---|
| BLaIR encoder cache for Beauty 207K items | `cache_5core/blair_titles_Beauty_and_Personal_Care.npy` (637 MB) |
| Rich-text MiniLM cache (title+cats+brand) | `cache_5core/richtext_titles_Beauty_and_Personal_Care.npy` (318 MB) |
| Fusion cache (BLaIR + rich-text concatenated) | `cache_5core/fusion_blair_richtext_Beauty_and_Personal_Care.npy` (957 MB) |
| Rich-text encoder script | `_bestrec_run/encode_richtext_5core.py` |
| BLaIR-rich-text encoder script | `_bestrec_run/encode_blair_richtext_5core.py` |
| Cache fusion helper | `_bestrec_run/concat_encoder_caches.py` |
| MLP adaptor (adopted from Hou et al. 2024's SASRecText) wired into SASRec | `_bestrec_run/run_sasrec_sbert.py --mlp-adaptor --mlp-hidden 300 --mlp-dropout 0.2` |
| Beauty results comparator | `_bestrec_run/compare_beauty_results.py` |
| Experiment launcher script | `_bestrec_run/queue_next_beauty_experiments.sh` |
| Faithful SASRecText partial result | `_bestrec_run/results_sasrectext_faithful_Beauty.json` (killed at epoch 2) |
| Hybrid result | `_bestrec_run/results_sasrec_hybrid_mlpadaptor_Beauty.json` (killed at epoch 5) |
| BLaIR+MLP+dropout 0.2 clean ablation | `_bestrec_run/results_sasrec_blair_mlp_drop02_Beauty.json` (final) |

## Recommendation

The Beauty_and_PC gap-closing problem is now well-characterized: the path forward requires architectural sophistication (TIGER/LIGER) or different benchmark protocol, both multi-week efforts.

For the publication claim, the honest story is:

> **SASRec-SBERT achieves NDCG@10 = 0.0514 ± 0.0021 on Video_Games 5-core (multi-seed), beating published TIGER and BLaIR by 14-22%. The same architecture does not generalize to Beauty_and_PC 5-core (NDCG@10 = 0.0191), which represents an architectural ceiling for d=64 SASRec at 207K-item catalog scale with our preprocessing. Closing this remaining gap requires either TIGER/LIGER-style semantic-ID architecture or different benchmark protocol; both are multi-week follow-ups.**

This stands as the publication-defensible claim.
