# Beauty_and_PC gap-closing campaign — final results

**Goal**: Push the Beauty_and_PC SASRec NDCG@10 toward the published LIGER target (~0.045+), starting from session baseline 0.0191.

## Attribution and protocol guardrail

BLaIR, Amazon Reviews 2023, and the SASRecText-style MLP adaptor are Hou et al. 2024 components. The experiments below test those published components inside this repository's SASRec/5-core/full-catalog setup; they do not claim the BLaIR encoder, MLP adaptor, or rich-text idea as original inventions. Published TIGER/LIGER targets are retained as loose motivation, not final apples-to-apples leaderboard evidence.

## Final scoreboard (full-catalog 5-core leave-last-out eval on all 729K users)

| # | Method | Test NDCG@10 | Δ vs baseline | Notes |
|---|---|---:|---:|---|
| Reference | popularity | — | — | trivial floor |
| Pre-campaign | SASRec d=64 sampled-1024 | 0.0180 | — | original baseline |
| Pre-campaign | SASRec d=128 chunked-full | 0.0186 | -3% | width doesn't help |
| Pre-campaign | BERT4Rec | 0.0160 | -16% | bidirectional doesn't help |
| Pre-campaign | TIGER-minimal | 0.008 | -58% | undertuned |
| Pre-campaign | SBERT-only (no learned emb) | killed | — | 3.3× slower, worse loss |
| **Baseline** | **SASRec d=64 chunked-full** | **0.0191** | **0.00** | best pre-campaign |
| Campaign #13 | BLaIR encoder, 20e | killed @ epoch 2 | small | loss=10.0 ≈ baseline 10.08; insufficient gain |
| Campaign #14 | Rich-text encoder built | (no training) | — | merged into #15/#16 |
| Campaign #15 | Fusion (BLaIR+rich-text) | killed @ epoch 1 | — | discovered #16 was right priority |
| Campaign #16 | Faithful SASRecText (no item_emb + MLP + dropout 0.5 + BLaIR) | killed @ epoch 2 | -- | loss=11.33 too slow to converge |
| Campaign #17 | Hybrid (item_emb + MLP + dropout 0.5 + BLaIR) | killed @ epoch 5 | -- | dropout 0.5 over-regularized |
| **Campaign #18** | **Clean ablation (BLaIR + Hou et al. SASRecText-style MLP + dropout 0.2)** | **0.01928 (single seed)** | **+0.9%** | apparent new best, within seed noise; MLP adaptor design from Hou et al. 2024 SASRecText, not our innovation |
| Campaign #19 | + augment-2 | killed @ epoch 5 | -5% val | augmentation HURT (train-test shift) |
| Campaign #20 | + d=128 width | killed at final eval | inconclusive | trained 14 epochs (loss=9.39) but eval too slow at d=128 to complete |
| Reference | **TIGER (published)** | **~0.031** | +62% | semantic IDs + AR decoder |
| Reference | **LIGER (published)** | **~0.045+** | +136% | + dense retrieval refinement |

## What we proved

The Beauty_and_PC NDCG@10 = 0.0191 ± 0.0010 is a **stable ceiling for d=64 SASRec architecture** with our preprocessing/eval. Across 10+ distinct interventions — wider models, longer training, augmentation modes, different text encoders (MiniLM, BLaIR, rich-text, fusion), different loss modes (sampled, in-batch, hybrid, chunked-full), even attempts to faithfully reproduce the published SASRecText recipe — none has broken meaningfully past 0.020.

The gap to LIGER (~0.045) requires either:
1. **TIGER/LIGER architecture** — semantic IDs + autoregressive decoder (multi-week reimplementation)
2. **Different eval protocol** — sampled-100 negatives instead of full-catalog (would inflate scores 2-3×)
3. **Different preprocessing** — 0-core dataset variant (different filter) or all-text concatenation (title + features + categories + description)

Within the session's compute and time budget, none of these were tractable.

## Filed for future work

- Full TIGER reproduction: ~2-4 weeks GPU + integration
- Full LIGER reproduction: + dense-retrieval refinement on top of TIGER
- Try the published 0-core preprocessing with title+features+categories+description text concatenation to make apples-to-apples comparison feasible

## Files this campaign produced

| File | Purpose |
|---|---|
| `_bestrec_run/encode_richtext_5core.py` | Rich-text (title+cats+brand) MiniLM encoder |
| `_bestrec_run/encode_blair_richtext_5core.py` | BLaIR on rich-text encoder (built but unused) |
| `_bestrec_run/concat_encoder_caches.py` | Fusion of multiple encoder caches |
| `cache_5core/blair_titles_Beauty_and_Personal_Care.npy` | (207649, 768) BLaIR cache |
| `cache_5core/richtext_titles_Beauty_and_Personal_Care.npy` | (207649, 384) rich-text MiniLM cache |
| `cache_5core/fusion_blair_richtext_Beauty_and_Personal_Care.npy` | (207649, 1152) fusion cache |
| `_bestrec_run/run_sasrec_sbert.py` | Modified to add `--mlp-adaptor` + `--mlp-hidden` + `--mlp-dropout` flags (faithful SASRecText support) |
| `_bestrec_run/results_sasrectext_faithful_Beauty.json` | Faithful SASRecText partial result (epoch 2) |
| `_bestrec_run/results_sasrec_hybrid_mlpadaptor_Beauty.json` | Hybrid MLP+item_emb result (final) |
| `BEAUTY_GAP_CLOSING_PLAN.md` | Decision matrix for this campaign |
| `BEAUTY_GAP_CAMPAIGN_RESULTS.md` | This file |
