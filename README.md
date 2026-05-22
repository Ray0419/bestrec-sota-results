# BEST-Rec v5: SBERT-Augmented EASE + Novel Cold-Item Algorithm (LC2C)

A closed-form linear recommender + a **novel content-to-CF mapping (LC2C)** for cold items, evaluated rigorously across four Amazon Reviews 2023 subsets. Multiple rounds of strict adversarial review (see `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND{2,3,4}.md`) have addressed the headline statistical and reproducibility issues, but several items remain explicitly out of scope for this submission and are scoped as camera-ready work: (a) BLaIR / TIGER / LIGER / CLCRec / MELT head-to-head comparisons, (b) a faithful DropoutNet reproduction with hyperparameter sweep and multi-seed variance (we ship a *simplified DropoutNet-style* baseline instead, with explicit deviation list in the paper Table 5.4 caption), (c) chronological / leave-last-out splits, and (d) a clustered-bootstrap uncertainty analysis on cold-item deltas. See "Open camera-ready items" below for the full list.

## Publication-grade confirmatory path

The strict SOTA repair path is now separate from the exploratory artifacts. It freezes `lc2cpp_validated_margin`, evaluates cold targets against the **full item catalog**, writes per-record JSONL files, and blocks publication claims unless all modern-baseline and significance gates pass:

```powershell
uv --project _bestrec_run run python _bestrec_run/run_all_confirmatory.py --profile sota-confirmatory --datasets beauty,fashion,instruments,books --seeds 20260521,20260522,20260523,20260524,20260525 --candidate-scope full_catalog --no-books-cap
uv --project _bestrec_run run python _bestrec_run/validate_artifacts.py --strict-publication
```

Outputs are written to `_bestrec_confirmatory/<run_id>/`. If any gate fails, the runner writes `_bestrec_confirmatory/<run_id>/INTERNAL_SOTA_FAILURE_REPORT.md` and does not build a SOTA paper.

## TL;DR — paper-ready numbers

### Warm leave-one-out (5-fold mean ± std, full-item ranking)

| Dataset | k | \|U\| | \|I\| | \|R\| | NDCG@10 | HR@10 | MAE | RMSE |
|---|---|---|---|---|---|---|---|---|
| Beauty      |  5 |    253 |    356 |   2,535 | **0.0929 ± 0.004** | 0.1652 | 0.6749 | 0.9058 |
| Fashion     |  4 |    513 |    614 |   3,805 | **0.0923 ± 0.006** | 0.1635 | 0.7104 | 0.9599 |
| Instruments | 10 |  3,911 |  2,269 |  59,026 | 0.0564 ± 0.002 | 0.1033 | 0.5983 | 0.9039 |
| Books       | 20 | 14,407 | 13,164 | 601,992 | **0.1023 ± 0.003** | 0.1826 | 0.5840 | 0.8055 |

### Cold-item GroupKFold-by-item (ranking among held-out 20% item fold)

| Method | Beauty | Fashion | Instruments | Books |
|---|---|---|---|---|
| Random | 0.067 | 0.036 | 0.011 | 0.002 |
| Content KNN (X·S) | 0.145 | 0.134 | 0.036 | 0.027 |
| LC2C V1 (SVD k=64 + Ridge) | 0.161 | 0.157 | 0.050 | 0.046 |
| **LC2C V2 (direct Ridge, no SVD — headline)** | **0.173** | **0.155** | **0.058** | **0.065** |
| **Δ V2 vs Content KNN** | **+19%** | **+16%** | **+62%** | **+141%** |

Notes: (1) this is **NOT a full-catalog cold-item ranking** — candidates are restricted to the held-out 20% item fold, so absolute NDCG values and gains are easier than a production cold-start retrieval problem where cold items must compete with all warm and cold catalog items; (2) V2 beats V1 on Beauty/Instruments/Books and ties/slightly loses on Fashion; (3) per-USER paired Wilcoxon with Holm–Bonferroni correction is computed by `_bestrec_run/compute_significance.py` from `results_cold_item_v2_perpair_<dataset>.json` (which stores `(fold, user, item, ndcg)` records); LC2C V2 is Holm-corrected p < 0.001 vs. content-direct and a *simplified DropoutNet-style* baseline on all 4 datasets (n_users = 253 / 512 / 3,911 / 11,930). The DropoutNet row in our tables is **inspired by Volkovs et al., 2017** (SVD-warm-CF + content fallback; item-tower-only; single-config, single-seed) — it is *not* a faithful reproduction of the original architecture, and we do not claim to outperform the official tuned DropoutNet (see `_paper_gen/build_paper_full.py` Table 5.4 caption for the full deviation list).

### vs LightGCN (most-cited modern baseline) on warm split

Raw mean NDCG@10 gaps: Beauty **+63%**, Fashion **+44%**, Instruments **+5%**, Books **+121%** (all four numbers regenerated from the canonical `results_FINAL.json::datasets.<ds>.baselines` in this revision; the figure at `_bestrec_run/figures/fig2_vs_lightgcn.png` reads from the same source). Under one-sided paired Wilcoxon with Holm–Bonferroni correction across six baselines per dataset, the gap is significant only on Books; the small-dataset gaps fail Holm correction. **Round-4 upgrade:** the Books single-pipeline rerun moved EASE+SBERT from 0.0990 → 0.1023, so the Books-vs-LightGCN gap rose from +114% to +121% and the per-USER Wilcoxon now also Holm-rejects EASE-pure and Higher-Order EASE on Books at p < 0.001.

## Two algorithms

### Warm/known-item ranking — SBERT-augmented EASE

```
G  = X^T X + λI + βS_content       # X = binary user-item, S = SBERT cosine sim of titles
B  = -G^{-1}/diag(G^{-1}); diag(B)=0
score(u, i) = (X B)[u, i]
```

Closed-form, no learned parameters, sub-second fit on small datasets.

### Cold-item ranking — Learned Content-to-CF (LC2C)

For an item never seen in training, EASE's `B[:, j_cold]` is undefined. The headline LC2C method (V2 — direct ridge, no SVD) learns a dataset-specific linear map from SBERT title embeddings directly to the full collaborative behaviour vector:

```
HEADLINE LC2C (V2):
1. EASE on warm items                          B_warm ∈ R^{n_warm × n_warm}
2. Ridge:  SBERT_warm @ W ≈ B_warm.T            (W ∈ R^{384 × n_warm})
3. Predict cold B-columns                       B_hat[:, j] = (SBERT_cold[j] @ W).T
4. Score: X[u, warm] @ B_hat[:, j]
```

A legacy SVD-compressed variant (V1) is kept as an ablation:

```
LC2C V1 (SVD-compressed, kept as ablation):
1. EASE on warm items                          B_warm
2. SVD(B_warm) → E_cf_warm                       (k=64 collaborative latent)
3. Ridge:  SBERT_warm @ W ≈ E_cf_warm            (content → CF latent map)
4. Predict cold latents                         E_cf_cold = SBERT_cold @ W
5. Score: (X_u @ E_cf_warm) @ E_cf_cold[j].T
```

LC2C V2 improves over content-KNN by **+19% / +16% / +62% / +141%** across Beauty/Fashion/Instruments/Books in mean NDCG@10. V2 also outperforms V1 on Beauty/Instruments/Books (+7%/+15%/+43%) and ties/slightly loses on Fashion.

### Per-dataset hyperparameters

| Dataset | k-core | λ | β | LC2C dim |
|---|---|---|---|---|
| Beauty      |  5 | 100 | 10 | 64 |
| Fashion     |  4 |  30 | 10 | 64 |
| Instruments | 10 | 200 | 10 | 64 |
| Books       | 20 | 200 | 10 | 64 |

## Open camera-ready items (NOT addressed in this submission)

The round-4 strict review (`STRICT_REVIEW_RESUBMISSION_ROUND4.md`) identified the following items as still out of scope; the round-4 response (`RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND4.md`) documents the rationale for deferring each to camera-ready:

1. **Notebook retirement** — `BEST_Rec_v4.ipynb` has moved to `archive/legacy_notebooks/` and is explicitly *removed* from the official reproduction path. Tables and figures are reproduced by standalone scripts under `_bestrec_run/` (see `RUNNING.md`).
2. **Faithful DropoutNet reproduction** — we ship a simplified DropoutNet-style baseline (single config, single seed, SVD-warm-CF + content fallback); a full DropoutNet with multi-seed and hyperparameter sweep is camera-ready scope.
3. **Modern cold-start / text-augmented comparators** — BLaIR, TIGER, LIGER, CLCRec, MELT are not run.
4. **Clustered bootstrap on cold-item deltas** — we report a simple user-clustered bootstrap CI in `_bestrec_run/compute_significance.py` (round 4); a full fold-block + user-clustered bootstrap that respects all three dependency axes is camera-ready scope.
5. **Chronological / temporal splits** — we use random GroupKFold by user / by item; a temporal-validity protocol is camera-ready scope.
6. **iALS on Books** — still out-of-memory on our hardware; iALS row is missing for Books in Table 5.2.
7. **Per-user warm-LOO vectors for the three deep baselines** (MultiVAE, iALS, LightGCN) saved in the same standalone JSON format so the entire Table 5.2 Wilcoxon path is auditable from released artifacts. Round 4 covers the four closed-form methods (Popularity, EASE-pure, Higher-Order EASE, EASE+SBERT) on all four datasets via `results_warm_loo_perfold_<ds>.json`.

## Reviewer concerns addressed (partial — see `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND{2,3,4}.md` for the full audit)

| Original concern | Fix in v5 |
|---|---|
| SVD computed on full data before train/test split | EASE refit per fold (closed-form, leakage-free) |
| User text from full reviews including held-out | Per-fold encoding; few-shot context-only for cold |
| KFold on interactions allows same (u,i) in train+test | Per-user leave-one-out + GroupKFold by user |
| Multi-rating duplicates inflate k-core counts | (user, item) deduplication, latest rating kept |
| Sampled 99-negative ranking inflates NDCG to ~0.997 | Full-item ranking against ALL unseen items |
| `clamp(score, 1, 5)` ties items at boundary | EASE outputs raw scores, no clamp |
| Only Beauty + Books reported | Beauty + Fashion + Instruments + Books (all 4) |
| Deep model with 270K params overfits 3K interactions | EASE: 0 trainable params, closed-form |
| No statistical significance reported | Paired Wilcoxon vs every baseline, all 4 datasets |
| No deep baseline comparison | LightGCN, MultiVAE, iALS added |
| **No true cold-start (only thresholds)** | **GroupKFold-by-item; LC2C novel algorithm** |
| **Item-side signals risk leakage in user-only CV** | **Per-fold per-side splits; SBERT computed once from titles only (external metadata)** |

## Repository layout

```
archive/legacy_notebooks/BEST_Rec_v4.ipynb          ← historical notebook only; not part of the official reproduction path
README.md                                           ← this file
RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND{2,3,4}.md ← responses to successive strict-review rounds

_bestrec_run/
├── ease_efficient.py                               ← Cholesky-based EASE solver
├── preprocess_v2.py                                ← dedup-aware dataset loader
├── v5_utils.py                                     ← shared helpers
├── make_paper_table.py                             ← 4-dataset paper table generator
├── consolidate_final.py                            ← merges per-dataset results
├── make_figures.py                                 ← warm/cold figures (round 4: reads ONLY from results_FINAL.json)
├── run_warm_loo.py                                 ← (NEW round 4) standalone warm-LOO; saves per-(fold, user, ndcg) JSON for Table 5.2 audit
├── run_ablation_embeddings.py                      ← SBERT vs random vs BoW ablation
├── run_hp_sweep.py                                 ← λ × β heatmap
├── run_cold_item.py                                ← cold-item evaluation harness
├── run_cold_item_v2.py                             ← novel methods: LC2C V1/V2, content_topk, DropoutNet-style, etc.
├── compute_significance.py                         ← Holm-corrected per-USER Wilcoxon for both warm-LOO (round 4) and cold-item
├── results_FINAL.json                              ← SINGLE CANONICAL warm-LOO source (4 datasets × 7 baselines + ours)
├── results_warm_loo.json                           ← (NEW round 4) single-pipeline warm-LOO summary
├── results_warm_loo_perfold_<ds>.json              ← (NEW round 4) per-(fold, user, ndcg) records for Wilcoxon audit
├── results_cold_item_v2.json                       ← cold-ITEM 5-fold summary on 4 datasets
├── results_cold_item_v2_perpair_<ds>.json          ← per-(fold, user, item, ndcg) cold-item records
├── results_v7_2_coldstart.json                     ← cold-USER on 4 datasets
├── results_ablation_embeddings.json                ← embedding ablation
├── results_hp_sweep.json                           ← λ × β grids
├── results_lightgcn.json, results_v6_baselines.json, results_books_warm.json ← historical per-run snapshots; NOT consulted by figures or paper builder (kept for provenance only)
├── figures/                                        ← publication-ready figures (PNG + PDF)
│   ├── fig1_warm_methods_x_datasets.{png,pdf}      ← grouped bar: 7 methods × 4 datasets
│   ├── fig2_vs_lightgcn.{png,pdf}                  ← headline: EASE+SBERT vs LightGCN (round 4: regenerated from results_FINAL.json)
│   ├── fig3_ablation_embeddings.{png,pdf}          ← SBERT vs random vs BoW vs none
│   ├── fig4_cold_start.{png,pdf}                   ← cold-USER NDCG@10
│   ├── fig5_size_vs_ndcg.{png,pdf}                 ← method NDCG vs dataset size
│   ├── fig6_hp_sensitivity_*.{png,pdf}             ← λ × β heatmap
│   └── fig7_cold_item_v2.{png,pdf}                 ← LC2C cold-ITEM
├── pyproject.toml + uv.lock                        ← reproducible Python env
└── ...

cache/<dataset>/                                    ← preprocessed datasets
├── raw_data_dedup.pkl                              ← dedup'd interactions + metadata
├── v5/item_title_k{K}_dedup.pt                     ← SBERT title embeddings
└── v5/v5_results.json                              ← per-dataset 5-fold results

data/<dataset>/                                     ← raw Amazon Reviews 2023 .jsonl files
```

## Running

### Setup (one-time)

```bash
# Requires Python 3.12 + uv
cd _bestrec_run
uv sync                              # installs PyTorch CUDA + sentence-transformers + sklearn + matplotlib
```

### Preprocess a dataset (only needed once per dataset)

```bash
uv run python preprocess_v2.py beauty
uv run python preprocess_v2.py fashion
uv run python preprocess_v2.py instruments
# Books has its own memory-efficient streaming preprocessor (see code)
```

### Reproduction path (round 4: STANDALONE SCRIPTS, no notebook)

The historical notebook has been moved to `archive/legacy_notebooks/` because it had drifted from the paper. Reproducing every table and figure in the paper requires only the standalone scripts below.

Expected runtimes (RTX 5060 Ti, 64GB RAM):

| Dataset | Time | Bottleneck |
|---|---|---|
| Beauty | ~5 minutes | LightGCN training on tiny graph |
| Fashion | ~5 minutes | LightGCN training |
| Instruments | ~12 minutes | LightGCN on 60K interactions |
| Books | ~30 minutes baselines + several hours for higher-order EASE | LightGCN + 13K-item EASE Cholesky + B@B for HO-EASE |

### Reproducing all paper materials

```bash
# 1. Preprocess all four datasets (one-time)
for ds in beauty fashion instruments; do
    uv run python _bestrec_run/preprocess_v2.py $ds
done
# Books preprocessing: see existing cache/books/raw_data_dedup.pkl in repo

# 2. Warm-LOO baselines (single canonical pipeline, round 4) — writes
#    results_warm_loo.json (summary) and
#    results_warm_loo_perfold_<ds>.json (per-(fold, user, ndcg) audit JSON)
uv run python _bestrec_run/run_warm_loo.py beauty fashion instruments books

# 3. Cold-item + LC2C + DropoutNet-style baselines (per-pair audit JSON saved)
uv run python _bestrec_run/run_cold_item_v2.py beauty fashion instruments books

# 4. Ablations + hyperparameter sensitivity sweeps
uv run python _bestrec_run/run_hp_sweep.py beauty fashion instruments
uv run python _bestrec_run/run_ablation_embeddings.py beauty fashion instruments

# 5. Per-USER paired Wilcoxon (Holm-corrected) for both warm-LOO and cold-item,
#    re-aggregated from the per-pair / per-fold JSON files saved above
uv run python _bestrec_run/compute_significance.py

# 6. Consolidate results into results_FINAL.json (the single canonical source)
uv run python _bestrec_run/consolidate_final.py
uv run python _bestrec_run/make_paper_table.py
uv run python _bestrec_run/make_figures.py            # reads ONLY results_FINAL.json + results_v7_2_coldstart.json + results_ablation_embeddings.json
uv run python _paper_gen/build_paper_full.py          # rebuilds the PDF
```

## Methodology highlights

- **Per-(user, item) deduplication** before k-core filtering (critical: Fashion/Beauty/Instruments preprocessing inflated counts because reviewers repeat items).
- **Per-dataset k-core** chosen so each dataset retains ≥200 users post-dedup: k=5 (Beauty), k=4 (Fashion), k=10 (Instruments), k=20 (Books).
- **EASE refit per fold** (closed-form, leakage-free). SBERT title embeddings are computed once from external metadata (Amazon catalog titles, not derived from the train/test interaction split).
- **Three evaluation protocols**:
  - Warm leave-one-out per user — full-item ranking against unseen catalog items.
  - Cold-USER (GroupKFold by user) + few-shot text context — full-item ranking.
  - Cold-ITEM (GroupKFold by item) + LC2C — ranking among the held-out 20% item fold only (NOT full catalog; see SUBMISSION.md and the paper §4.2.3 for the precise protocol).
- **Statistical significance for warm-LOO**: paired Wilcoxon signed-rank on per-user NDCG@10 with Holm–Bonferroni correction across the six baseline comparisons per dataset, implemented in `_bestrec_run/compute_significance.py`. As of round 4, raw p-values are recomputed from per-(fold, user, ndcg) JSONs saved by `run_warm_loo.py` for the four closed-form methods (Popularity, EASE-pure, Higher-Order EASE, EASE+SBERT) so the Wilcoxon path is end-to-end auditable from the released artifacts. Deep-baseline (MultiVAE, iALS, LightGCN) per-user vectors are still consumed from the prior pipeline; saving them in the same standalone format is camera-ready scope.
- **Statistical significance for cold-item**: per-USER paired Wilcoxon signed-rank with Holm–Bonferroni correction across three head-to-head comparisons (V2 vs content-direct, V1, simplified DropoutNet-style). Implemented in `_bestrec_run/compute_significance.py` reading the `(fold, user, item, ndcg)` records from `results_cold_item_v2_perpair_<dataset>.json`. LC2C V2 is Holm-corrected p < 0.001 vs content-direct and the simplified DropoutNet-style baseline on all 4 datasets; p < 0.05 vs V1 on Beauty, p < 0.001 vs V1 on Instruments and Books, n.s. on Fashion. Round 4 additionally reports a simple user-clustered bootstrap 95% CI on the V2 − content-direct cold-item delta to give a non-asymptotic uncertainty quantification that respects the user dependency unit.
- **6 baselines**: Popularity, MultiVAE (Liang 2018), iALS (Hu 2008), LightGCN (He 2020), EASE-pure (Steck 2019), Higher-Order EASE (Steck 2020).
- **3 ablations**:
  - **Content embedding type**: SBERT vs random Gaussian vs TF-IDF+SVD vs none.
  - **Hyperparameter sensitivity**: 6×6 (λ, β) heatmap (primary) plus a follow-up 1D λ sweep for λ = 200 on Instruments / Books.
  - **LC2C variants**: V0 (content-direct), V1 (SVD + ridge), V2 (direct ridge, headline), V3 (nearest-warm, no ridge).
- **Proposed algorithm**: LC2C V2 (Learned Content-to-CF, direct ridge with no SVD). To our knowledge this specific formulation — direct ridge regression from a frozen sentence encoder into the column space of a closed-form item-item recommender — has not been reported previously; see §2.6 of the paper for the literature search. A *simplified DropoutNet-style* baseline inspired by Volkovs et al. (2017) is now run head-to-head (single-config, single-seed, SVD-warm-CF + content fallback; not a faithful reproduction); a faithful DropoutNet with hyperparameter sweep and multi-seed variance, plus CLCRec, MELT, BLaIR, TIGER, LIGER, are camera-ready scope.

## Citation

```bibtex
@inproceedings{steck2019ease,
  author    = {Harald Steck},
  title     = {Embarrassingly Shallow Autoencoders for Sparse Data},
  booktitle = {WWW},
  year      = {2019},
}
```

## License

[Your chosen license here.]
