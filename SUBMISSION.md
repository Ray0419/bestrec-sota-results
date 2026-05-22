# BEST-Rec v4 — Submission Package

This directory contains the complete submission package for the paper
**"BEST-Rec v4: SBERT-Augmented EASE with Learned Content-to-CF Mapping
for Cold-Item Recommendation"**.

The submission is structured so a reviewer can (a) read the paper, (b)
inspect the source code that produced every number and figure, and (c)
re-run the entire evaluation pipeline on a fresh machine.

---

## 1. Primary deliverable

| File | Description |
|---|---|
| `BEST_Rec_v4_Full_Paper.pdf` | Full paper, 47 pages, 1.51 MB. Sections 1–8, bibliography, all 7 figures and 11 tables. |

## 2. Reproducibility artifacts

| Path | Description |
|---|---|
| `RUNNING.md` | Step-by-step installation and reproduction guide (uv install → data download → preprocessing → experiments → figures → PDF rebuild). |
| `_bestrec_run/pyproject.toml` | Python project file. Python 3.12, pinned via `uv.lock`. |
| `_bestrec_run/uv.lock` | Exact transitive-dependency lock (PyTorch CUDA 12.8, numpy, scipy, scikit-learn, sentence-transformers, etc.). |
| `_bestrec_run/preprocess_v2.py` | Dedup + k-core preprocessing for the 4 Amazon Reviews 2023 categories. Reads `data/<dataset>/*.jsonl`, writes `cache/<dataset>/raw_data_dedup.pkl` and `cache/<dataset>/v5/item_title_k*_dedup.pt`. |
| `_bestrec_run/ease_efficient.py` | Closed-form EASE solver (Cholesky → LU → pinv fallback). |
| `_bestrec_run/v5_utils.py` | Shared utilities: k-core, reindex, splits, content-similarity, ranking helpers. |
| `_bestrec_run/run_warm_loo.py` | (**NEW round 4**) Standalone warm-LOO evaluation for Popularity / EASE-pure / Higher-Order EASE / EASE+SBERT. Saves both 5-fold summary (`results_warm_loo.json`) and per-(fold, user, ndcg) audit JSON (`results_warm_loo_perfold_<dataset>.json`) so the Table 5.2 Wilcoxon path is end-to-end auditable from released artifacts. Replaces the notebook as the official warm-LOO reproduction path for the four closed-form methods. |
| `_bestrec_run/run_all_confirmatory.py` | Publication-grade confirmatory runner. Freezes `lc2cpp_validated_margin`, evaluates cold targets against the full catalog, writes `_bestrec_confirmatory/<run_id>/{results_final,significance,tables,baseline_audit,results_manifest}.json`, and blocks SOTA/publication claims unless all strict gates pass. |
| `_bestrec_run/run_cold_item.py` | Cold-item evaluation only (`random`, `imputed_pop`, `content_direct`, `ci_ease`, `hybrid_50_50`); legacy. The current cold-item pipeline lives in `run_cold_item_v2.py`. |
| `_bestrec_run/run_cold_item_v2.py` | Cold-item with the headline LC2C method (`lc2c_v2` = V2 direct ridge, no SVD) plus seven other variants. The full method list is: `random`, `content_direct`, `content_rating_weighted`, `content_topk`, `lc2c` (V1 legacy SVD + ridge), `lc2c_v2` (V2 headline), `cf_hybrid`, and `dropoutnet` (the simplified DropoutNet-style baseline; see paper Table 5.4 caption for the explicit deviation list from Volkovs et al., 2017). Eight methods total. |
| `_bestrec_run/consolidate_final.py` | Aggregates per-dataset 5-fold results into `results_FINAL.json`, the **single canonical source of truth** for Tables 5.1, 5.2, 5.3 and for all figures in `make_figures.py`. |
| `_bestrec_run/compute_significance.py` | (**Round 4: expanded**) (a) For Table 5.2 (warm-LOO), recomputes per-USER paired Wilcoxon (Holm-corrected across six baseline comparisons per dataset) from the per-(fold, user, ndcg) records saved by `run_warm_loo.py` for the four closed-form methods; raw p-values for the deep baselines (MultiVAE, iALS, LightGCN) are still consumed from `results_FINAL.json` pending camera-ready saving of their per-user vectors in the same standalone format. (b) For Table 5.4b (cold-item), recomputes per-USER paired Wilcoxon (Holm-corrected across three comparisons: V2 vs content-direct / V1 / DropoutNet-style) from `results_cold_item_v2_perpair_<dataset>.json`. (c) Reports a user-clustered bootstrap 95% CI on the V2 − content-direct cold-item delta. Writes `significance_corrected.json` and `significance_cold_item_corrected.json`. |
| `_bestrec_run/run_lc2c_ablation.py` | Full LC2C ablation (component-wise + latent-dim sensitivity). |
| `_bestrec_run/run_hp_sweep.py` | λ × β hyperparameter sensitivity heatmap (Section 5.4). |
| `_bestrec_run/run_ablation_embeddings.py` | SBERT vs random vs TF-IDF+SVD vs no-content (Section 5.6). |
| `_bestrec_run/case_study.py` | Section 5.8 qualitative case study; produces the per-user JSON underlying Table 5.7. |
| `_bestrec_run/make_figures.py` | (**Round 4: refactored**) Generates all warm-LOO and cold-item figures (Figures 5.1, 5.2, 5.4, 5.7) by reading **only** from `results_FINAL.json` (warm baselines), `results_v7_2_coldstart.json` (cold-user), and `results_ablation_embeddings.json` (Figure 5.7). Earlier rounds also consulted `results_lightgcn.json` and other per-run snapshots, causing the Figure 5.2 vs. Table 5.2 LightGCN-value drift identified in the round-4 review (F4); that source-of-truth split has been removed. |
| `_paper_gen/build_paper_full.py` | Generates the entire 47-page PDF from results, tables, and figures. |
| `_paper_gen/make_arch_v3.py` | Generates the architecture diagram (Figure 3.1). |

## 3. Cached intermediate results

The following directories hold cached artifacts so a reviewer can verify the
paper's numbers without running the entire 90-minute preprocessing + training
pipeline from scratch:

| Path | Description |
|---|---|
| `cache/<dataset>/raw_data_dedup.pkl` | Deduplicated (user, item) interactions per dataset. |
| `cache/<dataset>/v5/item_title_k*_dedup.pt` | SBERT title embeddings (one-time precomputed, frozen). |
| `_bestrec_run/results_FINAL.json` | **Single canonical source of truth** for Tables 5.1, 5.2, 5.3 and all warm figures (warm-LOO + cold-user + all six warm baselines + EASE+SBERT, plus per-(baseline, dataset) Wilcoxon p-values). |
| `_bestrec_run/results_warm_loo.json` | (**NEW round 4**) Single-pipeline warm-LOO summary for Popularity / EASE-pure / Higher-Order EASE / EASE+SBERT, written by `run_warm_loo.py`. |
| `_bestrec_run/results_warm_loo_perfold_<dataset>.json` × 4 | (**NEW round 4**) Per-(fold_id, user_id, ndcg) records for every warm-LOO test pair, for the four closed-form methods. Schema documented in the file's top-level `schema` field. Read by `compute_significance.py` to recompute per-USER Wilcoxon for Table 5.2 from released artifacts. |
| `_bestrec_run/results_cold_item_v2.json` | Source of truth for Table 5.4 (cold-item NDCG, HR@10, MRR for eight cold-item methods, including the headline `lc2c_v2` and the simplified DropoutNet-style `dropoutnet` baseline). |
| `_bestrec_run/results_cold_item_v2_perpair_<dataset>.json` × 4 | Per-(fold_id, user_id, item_id, ndcg) records for every cold-item test pair, for every method. Schema is documented in the file's top-level `schema` field. Used by `compute_significance.py` to compute per-USER paired Wilcoxon with Holm correction. |
| `_bestrec_run/significance_cold_item_corrected.json` | Per-USER paired Wilcoxon p-values for V2 vs. content-direct, V1, simplified DropoutNet-style on all 4 datasets, with Holm correction (Table 5.4b). Round 4 adds a user-clustered bootstrap 95% CI on the V2 − content-direct cold-item delta. |
| `_bestrec_run/results_ablation_lc2c.json` | Source of truth for Figures 5.5 + 5.6 (LC2C component + latent-dimension ablations). |
| `_bestrec_run/results_hp_sweep.json` | Source of truth for Figure 5.3 ((λ, β) heatmap, 6×6 primary grid on Beauty/Fashion/Instruments). |
| `_bestrec_run/results_ablation_embeddings.json` | Source of truth for Table 5.5 + Figure 5.7 (SBERT vs random vs TF-IDF). |
| `_bestrec_run/significance_corrected.json` | Holm–Bonferroni-corrected significance markers for Table 5.2, produced by `compute_significance.py`. |
| `_bestrec_run/case_study_output.json` | Per-user JSON for Table 5.7 (8 walked-through users on Books fold 0). |

## 4. Figures

All figures are available in both PNG (for inspection) and PDF (vector,
embedded in the paper):

| Figure | File |
|---|---|
| Figure 3.1 — Architecture diagram | `figures/fig_architecture_overview.{png,pdf}` |
| Figure 5.1 — Warm methods × datasets | `figures/fig1_warm_methods_x_datasets.{png,pdf}` |
| Figure 5.2 — vs. LightGCN | `figures/fig2_vs_lightgcn.{png,pdf}` |
| Figure 5.3 — (λ, β) sensitivity heatmap | `figures/fig6_hp_sensitivity_*.{png,pdf}` |
| Figure 5.4 — Cold-item v2 | `figures/fig7_cold_item_v2.{png,pdf}` |
| Figure 5.5 — LC2C component ablation | `figures/fig8_lc2c_ablation.{png,pdf}` |
| Figure 5.6 — LC2C latent-dim | `figures/fig9_lc2c_latentdim.{png,pdf}` |
| Figure 5.7 — Content embedding ablation | `figures/fig3_ablation_embeddings.{png,pdf}` |

## 5. What is NOT included and why

| Artifact | Reason |
|---|---|
| Raw Amazon Reviews 2023 JSONL files (~70 GB) | Not redistributed. Download from <https://amazon-reviews-2023.github.io/> and place under `data/<dataset>/` per `RUNNING.md §2.1`. |
| Faithful DropoutNet reproduction with hyperparameter sweep and multi-seed variance | A **simplified DropoutNet-style** baseline (inspired by Volkovs et al., 2017; SVD-warm-CF + content fallback; item-tower-only; single-config, single-seed) IS included in this submission with per-USER paired Wilcoxon (LC2C V2 wins all 4 datasets at Holm-corrected p < 0.001). See paper Table 5.4 caption for the explicit list of deviations from the original architecture. A faithful reproduction is camera-ready scope. |
| BLaIR / TIGER / LIGER / CLCRec / MELT baseline runs | Camera-ready follow-up. CLCRec is the next priority. |
| iALS on Books | OOM under our implementation; flagged with †footnote in Table 5.2. To be re-run with sparse iALS for camera-ready. |
| `archive/legacy_notebooks/BEST_Rec_v4.ipynb` | Historical notebook only. It is retired from the official reproduction path; standalone scripts under `_bestrec_run/` reproduce the generated artifacts consumed by the paper. |

## 6. Reviewer quick-start

To verify the paper's headline numbers without running anything:

1. Open `BEST_Rec_v4_Full_Paper.pdf` and read it. Table 5.0 (page 28) gives the empirical landscape at a glance.
2. Cross-reference any specific number against the JSON in `_bestrec_run/results_*.json`.

To re-run a single cold-item experiment (Beauty, ~5 min on a CPU):

```bash
# install uv if not already (see RUNNING.md §1)
cd _bestrec_run
uv sync
# you must have data/beauty/{All_Beauty,meta_All_Beauty}.jsonl downloaded
uv run python preprocess_v2.py beauty
uv run python run_cold_item_v2.py beauty
# inspect results - now contains both lc2c (V1) and lc2c_v2 (V2 headline)
cat results_cold_item_v2.json
```

For the warm-LOO + cold-user tables (Tables 5.1, 5.2, 5.3), the round-4 reproduction path is the standalone script (no notebook required):

```bash
cd _bestrec_run
# (NEW round 4) reproduces Table 5.2 for Popularity / EASE-pure / Higher-Order EASE / EASE+SBERT
# and saves both 5-fold summary and per-(fold, user, ndcg) audit JSON
uv run python run_warm_loo.py beauty fashion instruments books
# recompute per-USER Wilcoxon for both warm and cold from the released per-(fold, user, ndcg) JSON
uv run python compute_significance.py
# regenerate the canonical results_FINAL.json
uv run python consolidate_final.py
# inspect: results_FINAL.json holds the headline numbers; results_warm_loo_perfold_<ds>.json
# holds the per-user vectors that the Wilcoxon is computed from
```

To reproduce Section 5.8's Table 5.7 case study (Books, ~10 min):

```bash
cd _bestrec_run
uv run python case_study.py --dataset books --n-users 8 --n-cands 5
cat case_study_output.json
```

To regenerate the entire 47-page PDF from the existing result JSONs and figures:

```bash
uv run python _paper_gen/build_paper_full.py
# produces BEST_Rec_v4_Full_Paper.pdf at the repo root
```

## 7. Reviewer-facing changelog (revisions made during preparation)

The submitted PDF is the result of three review-iteration passes (a self-review
in the strong-accept-reviewer voice). Major changes between the initial draft
and the submission:

- **Bibliography** added (31 verified entries; initial draft had inline-only citations).
- All seven internal-consistency mismatches (R1–R7) resolved; abstract claims
  now exactly match Tables 5.1–5.7.
- **Hyperparameter grid widened to 7×6** to include the actual selected λ = 200.
- **Statistical protocol upgraded**: pooled paired Wilcoxon with
  Holm–Bonferroni correction across the 6 baseline comparisons within each dataset.
- **§3.4.5 Theoretical Convergence of LC2C** added (formal asymptotic argument
  via Hsu, Kakade & Zhang 2014 and Wainwright 2019).
- **§5.8 Qualitative Case Study** populated with real measured numbers from
  `case_study.py` on Books fold 0 (replaces an earlier illustrative-only sketch).
- **§5.2 SOTA disclaimer** added: explicitly states that the comparison establishes
  best-in-paradigm-baselines but not SOTA-vs-contemporary-LLM-recommenders;
  names BLAIR, TIGER, CLCRec, MELT, DropoutNet as missing comparisons.
- **§7.7 Ethics, Fairness, and Filter-Bubble Risk** added.
- **Table 5.0 Headline Summary** added at top of §5.
- **Table 5.2 (ref) annotation** added to clarify that significance markers
  measure the gap vs. our reference method (resolves potential reviewer confusion
  about why our row has no p-value).
- iALS Books OOM justification corrected (the original explanation
  misdescribed iALS memory behaviour).
- "Bit-identical" reproducibility claim qualified with required MKL settings.
- Citations: removed unverifiable references (Najafabadi et al. 2017/2019/2025,
  Hasan et al. 2024, Steck & Liang 2021, etc.); replaced with real
  peer-reviewed sources.
- Equation typesetting moved from Courier to Times-Italic; pseudocode kept
  in Courier.

## 8. Contact / licence

All code and results are released under the MIT licence. The paper itself is
licensed under CC BY 4.0. For correspondence, see the author block on the
title page of the PDF.
