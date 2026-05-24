# CDR Variant Exploration: Results

**Task:** Find a closed-form or hybrid cold-start algorithm that materially beats `CDR_validated` under the strict full-catalog cold-item protocol.

**Scope:** Beauty + Fashion + Instruments at 3 seeds × 5 folds; Books at 1 seed × 5 folds.

**Protocol:** identical to `_bestrec_run/run_poc_cdr_books.py::eval_full` (full-catalog candidate set, training history masked, per-(user, target) NDCG@10/HR@10/MRR). Same alpha grid `[0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0]`; same inner 20%-warm validation hold-out with seed `(seed*1000 + fold_id + 7)`.

**Code:** `_bestrec_run/run_cdr_variants.py`. **Outputs:** `_bestrec_run/results_cdr_variants.json`; per-pair JSONL records `_bestrec_run/results_cdr_variants_perpair_<dataset>.jsonl`.

## 1. Variants implemented

| Variant | Where it differs from `CDR_validated` |
|---|---|
| `CDR_validated` | Baseline. Cold blend = α·z(content_direct) + (1-α)·z(LC2C-Ridge). Per-user z-normalize each source. |
| `CDR_Q` | Replace per-user z-norm on the *blended* cold score with **quantile calibration**: per user, map each cold score's rank percentile to the matching percentile of the warm-score distribution via `np.interp`. Cold and warm now share the same distributional shape. |
| `CDR_R2` | **Weighted Ridge**: SBERT → B_warm.T fit with `sample_weight = 1/sqrt(popularity_warm + 1)` (normalized to mean 1). Rare warm items drive the projection. |
| `CDR_K` | **Gaussian RBF kernel ridge** in SBERT space, γ via median heuristic, λ_kernel=1. Exact when n_warm ≤ 4000, Nyström with 1000 anchors otherwise (Books). |
| `CDR_S` | **Top-K sparsification** (K=50): zero all but top-50 |entries| per column of the LC2C-predicted `B_hat_cold`. Sharper, less smoothed. |

All variants share the production CDR Step 1 (closed-form EASE warm-only), Step 4 (validation-selected α-blend), and Step 5 framing (warm via EASE; cold via z-normed blend). Only the cold-pool predictor or calibration changes.

## 2. Per-dataset results

### NDCG@10 (mean ± std across folds × seeds)

| Variant | Beauty (3 seeds) | Fashion (3 seeds) | Instruments (3 seeds) | Books (1 seed) |
|---|---:|---:|---:|---:|
| `CDR_validated` | 0.1483 ± 0.0092 | 0.1374 ± 0.0147 | 0.0537 ± 0.0032 | __TBD__ |
| `CDR_Q` | 0.0928 ± 0.0117 | 0.0761 ± 0.0130 | 0.0298 ± 0.0019 | __TBD__ |
| `CDR_R2` | 0.1480 ± 0.0082 | 0.1371 ± 0.0140 | 0.0541 ± 0.0029 | __TBD__ |
| `CDR_K` | __0.1508 ± 0.0096__ | 0.1380 ± 0.0141 | __0.0564 ± 0.0036__ | __TBD__ |
| `CDR_S` | 0.1440 ± 0.0137 | 0.1356 ± 0.0151 | 0.0551 ± 0.0033 | __TBD__ |

### Per-USER paired Wilcoxon vs `CDR_validated` (two-sided, Holm-corrected)

| Variant | Beauty | Fashion | Instruments | Books |
|---|---|---|---|---|
| `CDR_Q` | Δ=-0.067, p_Holm=2e-39 ***loss*** | Δ=-0.078, p_Holm=8e-66 ***loss*** | Δ=-0.025, p_Holm=0 ***loss*** | __TBD__ |
| `CDR_R2` | Δ=+0.001, p_Holm=0.63 n.s. | Δ=-0.001, p_Holm=0.59 n.s. | Δ=+0.000, p_Holm=0.36 n.s. | __TBD__ |
| `CDR_K` | Δ=+0.003, p_Holm=**0.030 win** | Δ=+0.001, p_Holm=0.53 n.s. | Δ=+0.003, p_Holm=**4e-25 win** | __TBD__ |
| `CDR_S` | Δ=-0.005, p_Holm=0.11 n.s. | Δ=-0.002, p_Holm=0.39 n.s. | Δ=+0.001, p_Holm=**0.023 win** | __TBD__ |

Holm correction within each dataset across 4 non-CDR variants.

Numbers for `delta` are differences in **per-user** mean NDCG@10 (variant − CDR_validated), averaged over users present in both methods. Wilcoxon `p_two_sided` is the raw two-sided test; `Holm` is the Holm step-down adjusted p across the 4 non-CDR variants per dataset.

## 3. Wall-clock cost per fold

Averaged over all folds (includes EASE solve + alpha-grid validation + final scoring):

| Variant | Beauty | Fashion | Instruments | Books |
|---|---:|---:|---:|---:|
| `CDR_validated` | 0.1 s | 0.5 s | 3.7 s | __TBD__ |
| `CDR_Q` | 0.2 s | 0.5 s | 5.4 s | __TBD__ |
| `CDR_R2` | 0.2 s | 0.4 s | 3.8 s | __TBD__ |
| `CDR_K` | 0.3 s | 1.6 s | 7.9 s | __TBD__ |
| `CDR_S` | 0.1 s | 0.4 s | 3.7 s | __TBD__ |

- `CDR_K` cost grows fastest because the inner validation loop also pays a kernel-ridge solve at every α grid point. The kernel size at α=1 vs α=0 doesn't differ (we cache K outside the α loop in practice; here we re-fit per α). Even so, ~2× the cost is acceptable.
- `CDR_S` is essentially free over `CDR_validated`.
- `CDR_Q` is slightly slower because of the per-user `np.interp` step.

## 4. Outcome by dataset

| Dataset | Winner over `CDR_validated`? | By how much? |
|---|---|---|
| Beauty | **CDR_K (yes)** | +0.003 NDCG@10, Holm p=0.030 (per-user n=253) |
| Fashion | **None** | CDR_K tied (Δ=+0.001, p=0.53); CDR_R2 tied; CDR_S tied; CDR_Q lost |
| Instruments | **CDR_K (strongly)** | +0.003 NDCG@10, Holm p=4e-25 (per-user n=3911) |
| Books | __TBD; run in flight__ | __see results_cdr_variants.json after completion__ |

(Books, 1 seed × 5 folds on n_warm ≈ 10500 items + Nyström RBF with 1000 anchors, is the slowest configuration and runs separately. The summary table will be updated when the run completes.)

## 5. Discussion

### Why CDR_K wins (when it does)

The linear Ridge in LC2C learns a single low-rank linear map from 384-d SBERT space to n_warm-d B-columns. Two SBERT-similar items can map to substantially different B columns if their warm interactions diverge. The RBF kernel ridge implicitly uses **all warm items as basis functions, weighted by SBERT-locality**, which captures non-linear local structure: a cold item near a warm "cluster" in SBERT space gets a B-column predicted from a weighted blend of just that cluster's warm B-columns, not from a globally-linear projection.

The gain is small but consistent — sub-1% absolute NDCG@10 — but the per-user signal is large enough (Instruments: +0.003 over CDR_validated, n=3911 users) that the Holm-corrected paired Wilcoxon is highly significant.

Evidence that the kernel produces a better cold predictor: the inner-validation **α selection consistently shifts toward LC2C-leaning** for CDR_K. On Instruments, CDR_K picks α=0 in 8/15 folds (LC2C-only), whereas CDR_validated picks α≥0.25 in 8/15 folds (content-leaning). The validator is finding that the kernel-LC2C signal alone is stronger than content_direct, so less content weight is needed.

### Why CDR_Q breaks the model

Quantile calibration maps cold scores onto the **warm** score distribution. This destroys the protective ordering: under CDR_validated, the per-user z-norm produces cold scores with mean 0 and σ=1 — they sit *below* most warm EASE scores in absolute level, so the warm scorer continues to dominate top-of-list except for cold items that happen to be highly relevant. Under CDR_Q, the top cold scores reach the max warm score, so they routinely outrank legitimate warm recommendations — collapsing the warm precision that drives most of the NDCG@10. The fact that CDR_Q **chose α≈0–0.5 on validation but still tanked** means it's a fundamentally bad inductive bias, not a tuning problem.

### Why CDR_R2 ties

Inverse-sqrt-popularity sample weights mildly redistribute the regression target, but B_warm is already learned from a sparse interaction matrix that under-weights popular items via the closed-form (1/diag(G⁻¹)) re-scaling. The redundancy explains the near-zero delta on every dataset.

### Why CDR_S has mixed results

Top-K sparsification (K=50) recovers a modest gain on Instruments (Δ=+0.0014, Holm p=0.023) but hurts Beauty (Δ=-0.005). On small catalogs, K=50 is a large fraction of n_warm so the sparsification is mild; on larger catalogs (Instruments) it's selective enough to denoise without losing signal. Sensitivity to K, not tuned per-dataset.

## 6. Recommendation

**Integrate `CDR_K` as a sibling method in `_bestrec_run/run_all_confirmatory.py`.**

Beauty + Instruments show statistically significant gains (Holm-corrected p < 0.05) with no regressions; Fashion ties (no harm); Books TBD pending the 1-seed run. The cost is ~2× CDR_validated per fold (kernel ridge with Nyström for Books). The implementation is closed-form, deterministic, and shares the inner-validation α protocol.

Suggested method label: `cdr_kernel_validated` (or `cdr_k_validated` for brevity).

**Do not pursue** `CDR_Q` (broken inductive bias), `CDR_R2` (no signal), or `CDR_S` (inconsistent across datasets).

## 7. Files

| File | Purpose |
|---|---|
| `_bestrec_run/run_cdr_variants.py` | Driver implementing all five variants + alpha-grid validator. |
| `_bestrec_run/results_cdr_variants.json` | Per-fold NDCG@10/HR@10/MRR per dataset, selected α, Wilcoxon vs CDR_validated. |
| `_bestrec_run/results_cdr_variants_perpair_beauty.jsonl` | Per-(user, target) records for each variant. Schema matches `_bestrec_confirmatory/sota_confirmatory_full_20260521/cold_full_catalog_records_<ds>.jsonl`. |
| `_bestrec_run/results_cdr_variants_perpair_fashion.jsonl` | (same) |
| `_bestrec_run/results_cdr_variants_perpair_instruments.jsonl` | (same) |
| `_bestrec_run/results_cdr_variants_perpair_books.jsonl` | (same) |
| `RESULTS_CDR_VARIANTS.md` | This report. |
