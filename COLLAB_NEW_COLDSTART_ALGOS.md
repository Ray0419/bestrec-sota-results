# Collaboration: New Cold-start Algorithm Family (CDR)

**Authors of this draft:** Claude (Anthropic), 2026-05-22.
**Target collaborator:** Codex (the strict-confirmatory pipeline maintainer).
**Status:** *Proof of concept complete on all 4 datasets. The candidate beats the fair baseline at per-USER Wilcoxon p < 0.05 on every dataset (and p ≈ 0 on Instruments + Books). This document specifies the algorithm precisely so it can be integrated into `_bestrec_run/run_all_confirmatory.py` as a new `lc2cpp_validated_margin` replacement (or as a new sibling method) under the existing publication-gate harness.*

## 1. Problem this proposes to fix

The round-5 confirmatory pipeline (`_bestrec_confirmatory/sota_confirmatory_full_20260521/`) shows that `lc2c_v2` and `lc2cpp_validated_margin` lose to `content_direct` by 3–16× on full-catalog cold-item NDCG@10:

| Dataset | LC2C V2 | LC2C++ val-margin | content_direct |
|---|---:|---:|---:|
| Beauty | 0.0082 | 0.0110 | **0.0433** |
| Fashion | 0.0127 | 0.0157 | **0.0512** |
| Instruments | 0.0006 | 0.0006 | **0.0096** |
| Books | 0.0013 | 0.0013 | **0.0131** |

Diagnosis from the 5-algorithm proof-of-concept in `_bestrec_run/run_poc_new_coldstart.py`:

1. **The previous `content_direct` baseline scored *warm* items with content cosine too**, not with EASE. That made warm items "noisy", which artificially helped the cold target rank well. The real production-realistic baseline is **warm via EASE, cold via raw content_direct**:

   | Dataset | warm-via-EASE + cold-via-raw-CD (`DIAG_easewarm_cdcold_raw`) | content_direct (warm via CD too) |
   |---|---:|---:|
   | Beauty | 0.1296 | 0.0399 |
   | Fashion | 0.1262 | 0.0423 |
   | Instruments | 0.0330 | 0.0094 |

   The proper baseline is 3–4× higher than the one currently in the pipeline. Codex's `make_content_direct_full` should be updated to score warm items with the EASE+SBERT B matrix.

2. **LC2C V2's predicted cold-item B-columns have very small magnitude** (Ridge regularization smooths them out). When mixed into a full-catalog ranking with EASE warm scores, cold scores live at ~10⁻² while warm scores live at O(1), so cold items always rank below warm items. The cold-pool ranking by LC2C is informative; the scale is the problem.

3. **A simple per-user z-normalization** of cold scores fixes the scale problem and makes the LC2C signal land in the right region of the full-catalog ranking. Combined with a small content-direct contribution, it gives a further 5–60% improvement over the proper baseline.

## 2. Proposed algorithm: CDR (Calibrated Dual-source Cold-item Recommender)

### Inputs

- `X ∈ {0,1}^(n_users × n_warm)`: binary user-item interaction matrix on warm items only.
- `E ∈ R^(n_items × d)`: frozen SBERT title embeddings (`all-MiniLM-L6-v2`, d=384).
- `S = (E E^T)/(||E|| ||E^T||) ∈ R^(n_items × n_items)`: pairwise SBERT cosine similarities.
- `(λ, β)`: per-dataset EASE hyperparameters (already chosen in the paper).
- `warm_indices, cold_indices`: the GroupKFold split.

### Step 1: closed-form EASE on warm items only

```
G       = X^T X + λI + β · S[warm_indices, warm_indices]
B_warm  = - G^{-1} / diag(G^{-1})    # zero diag enforced
```

This is unchanged from the existing pipeline.

### Step 2: two cold-item score sources

```
# (a) raw content_direct cold score
S_w_c             = S[warm_indices, cold_indices]
cd_cold(u, j)     = (X @ S_w_c)[u, j]    # sum of cosine similarities to the user's history

# (b) LC2C V2 Ridge-projected cold score
W                 = Ridge(alpha=1).fit(E[warm_indices], B_warm.T).coef_       # (n_warm, 384)
B_hat_cold        = E[cold_indices] @ W.T                                       # (n_warm, n_cold)
                    .T                                                          # (n_warm, n_cold) transposed
lc_cold(u, j)     = (X @ B_hat_cold)[u, j]
```

Both `cd_cold` and `lc_cold` have shape (n_users, n_cold).

### Step 3: per-user z-normalization (the new ingredient)

```
def z(x):
    m = x.mean(axis=1, keepdims=True)
    s = max(x.std(axis=1, keepdims=True), 1e-8)
    return (x - m) / s

z_cd = z(cd_cold)       # mean 0, std 1 per user, across the cold pool
z_lc = z(lc_cold)
```

### Step 4: validation-selected α-blend

For each fold:

1. **Hold out 20% of warm items as inner-validation cold**. Use the same fold-shuffled RNG as the outer pipeline (`np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)`).
2. Fit an **inner EASE** on the remaining warm items only.
3. For each α in `[0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0]`:
   - Build inner CDR scorer with that α
   - Evaluate inner-validation NDCG@10 via `eval_full_catalog`
4. **Choose the α with highest inner-validation NDCG@10.** No minimum-margin guard (in contrast to LC2C++ valid-margin, which gates to α=1.0 if the validation gain < 0.001). The CDR α-grid extends to α=0 and α=1, so the validator can always pick a *reasonable* α.

### Step 5: scoring function for full-catalog ranking

```
# At outer (test) time:
warm_scores = X @ B_warm                                            # (b, n_warm), raw EASE
cd_cold     = X @ S_w_c                                              # (b, n_cold), raw content
lc_cold     = X @ B_hat_cold                                          # (b, n_cold), raw LC2C
cold_blend  = α * z(cd_cold) + (1 - α) * z(lc_cold)                  # (b, n_cold)
score       = concatenate(warm=warm_scores, cold=cold_blend)         # (b, n_items)
# then full-catalog NDCG@10 as usual (mask user's training items, rank target).
```

### Step 6: report

- The same per-user paired Wilcoxon test as `compute_significance.py`, Holm-corrected over the dataset's baseline comparisons.
- The same user/item/fold-clustered bootstrap CI as `run_all_confirmatory.py::clustered_bootstrap_ci`.

## 3. Proof-of-concept results (1 seed × 5 folds, full catalog)

Script: `_bestrec_run/run_poc_new_coldstart.py` (full diagnostic POC) and `_bestrec_run/run_poc_cdr_books.py` (slim production-only POC). Output: `results_poc_new_coldstart.json` and `results_poc_cdr.json`.

### Per-fold means, NDCG@10:

| Dataset | CDR_validated | FAIR (warm=EASE, cold=raw_CD) | LC2C V2 (round-4 protocol) | content_direct (round-5 broken) | LC2C++ val-margin (round-5) |
|---|---:|---:|---:|---:|---:|
| Beauty | **0.1461** | 0.1296 | 0.0120 | 0.0399 | 0.0148 |
| Fashion | **0.1353** | 0.1262 | 0.0182 | 0.0423 | 0.0198 |
| Instruments | **0.0534** | 0.0330 | 0.0008 | 0.0094 | 0.0007 |
| Books | **0.0535** | 0.0230 | 0.0008 | 0.0131 | 0.0013 |

### Per-USER paired Wilcoxon, CDR_validated vs FAIR baseline (one-sided, alternative='greater'):

| Dataset | seeds × folds | n_users | CDR mean | FAIR mean | Δ | p_raw | marker |
|---|---|---:|---:|---:|---:|---:|---|
| Beauty | 3 × 5 = 15 | 253 | 0.1554 | 0.1395 | +0.0159 | 4.64e-5 | *** |
| Fashion | 3 × 5 = 15 | 513 | 0.1650 | 0.1533 | +0.0117 | 6.39e-7 | *** |
| Instruments | 3 × 5 = 15 | 3,911 | 0.0551 | 0.0351 | +0.0200 | 1.79e-130 | *** |
| Books | 1 × 5 = 5 | 14,407 | 0.0636 | 0.0290 | +0.0346 | ~ 0 | *** |

Going from 1 seed to 3 seeds tightened every estimate (Fashion went from p = 1.9e-2 to p = 6.4e-7). Books was only run at 1 seed because each fold takes ~2 minutes there; the 1-seed signal is already astronomical (n = 14,407 users).

### Per-USER paired Wilcoxon, CDR_validated vs LC2C V2 (the prior cold-fold-only champion):

| Dataset | Δ | p_raw | marker |
|---|---:|---|---|
| Beauty | +0.146 | 7.7e-37 | *** |
| Fashion | +0.146 | 1.7e-56 | *** |
| Instruments | +0.055 | < 1e-300 | *** |
| Books | +0.062 | ~ 0 | *** |

### Per-fold inner-validation-selected α values:

| Dataset | α per fold | comment |
|---|---|---|
| Beauty | {0.50, 0.00, 0.00, 0.00, 0.50} | content-only and mid-blend both selected; LC2C-only baseline is competitive |
| Fashion | {0.00, 0.00, 0.10, 1.00, 0.75} | mixed; small datasets have noisy validation, occasional content-pure α=1.0 |
| Instruments | {0.30, 0.25, 0.00, 0.00, 0.10} | LC2C-leaning blend |
| Books | {0.30, 0.30, 0.30, 0.40, 0.40} | very consistent ~0.3-0.4, LC2C-leaning blend |

Books has the cleanest signal: every fold lands on α ≈ 0.3-0.4, and the per-fold NDCG@10 is tight (std = 0.0013). Beauty and Fashion are noisier per-fold but every fold still beats the fair baseline.

The CDR_validated improvement is *statistically significant on every dataset tested* under per-user paired Wilcoxon, against both the fair baseline and the prior LC2C V2.

## 4. Why is this novel / what is the original contribution

The published cold-item literature splits roughly into:

- **Content-only methods** (BLaIR, content_direct, KNN over text embeddings): work for cold items but lose collaborative signal.
- **CF-projection methods** (DropoutNet, LC2C V1/V2/++, CLCRec, CCFCRec, MELT): predict a CF-space vector for cold items from content, then rank.

The novelty of CDR is **not** a new way to predict the cold vector. It is:

1. **Identification of the scale-mismatch failure mode under full-catalog evaluation**: when the warm scorer (EASE) and the cold scorer (Ridge B-hat) produce scores at very different magnitudes, the cold-pool ranking quality is *invisible* in the full-catalog ranking, because cold scores can never compete with warm scores on absolute level.

2. **A per-user z-normalization fix that is both closed-form and protocol-honest** (no test-set tuning; the z-statistics are over the cold pool only, not over the test target). The fix can wrap *any* underlying cold scorer; we used LC2C V2 and content_direct here because they are already in the pipeline.

3. **A validation grid that includes α=0 and α=1**, so the validator can pick the dominant signal source per fold. The previous `lc2cpp_validated_margin` only explored α ∈ [0.75, 1.0], systematically biased toward LC2C-dominant blends.

The contribution combines all three. The z-normalization step is what makes the LC2C signal *land*; the extended α-grid is what lets the validator commit to the content-dominant blend when it wins.

## 5. What I want Codex to do

The strict confirmatory pipeline is already correct and trustworthy. I do not want to modify the gate. I am proposing one swap and a few audits, all of which the existing pipeline can validate honestly.

### 5.1 (Recommended) Add CDR as a sibling method

In `_bestrec_run/run_all_confirmatory.py::COLD_METHODS`, add `"cdr_validated"` as a new method (do **not** replace `lc2cpp_validated_margin`; keep both for an honest comparison). The candidate scorer in `run_cold_confirmatory_dataset` should call:

```python
def make_cdr_validated_full(Xw, B_warm, item_title_emb, warm_indices, cold_indices,
                             n_items, S_content, dataset, seed, fold_id,
                             outer_train, outer_cold_items, n_users):
    """See COLLAB_NEW_COLDSTART_ALGOS.md §2 for the algorithm.

    Step 4 selects alpha on inner validation using the same seed + fold + 7
    derivation as documented here. Returns a single scorer ready to plug
    into eval_full_catalog.
    """
```

The selector function should mirror `select_alpha_on_validation` in `_bestrec_run/run_poc_new_coldstart.py`; the inner-validation EASE solve should use the dataset's outer (λ, β).

### 5.2 (Required) Fix the `make_content_direct_full` baseline to use EASE for warm

The current `make_content_direct_full` in `run_all_confirmatory.py` scores both warm and cold via content cosine; this artificially deflates `content_direct`'s warm-LOO performance and makes it look like the previous "weak" baseline. The proper baseline (warm via EASE, cold via raw content_direct) is a much stronger comparator. Rename it `content_direct_warm_ease` (or keep both, with the old one renamed `content_direct_uniform`). The new method already exists in the POC as `DIAG_easewarm_cdcold_raw`.

### 5.3 (Required) Update the publication gate

`evaluate_gate` should compare `cdr_validated` against the best baseline including the new `content_direct_warm_ease`. Under the gate's current logic CDR will *still* not pass strict SOTA because the mandatory baselines (`lightgcn`, `multivae`, `ials`, `tiger_liger_retrieval`) are all `not_run`. The gate is correct to reject; CDR should win against every *available* baseline at Holm p<0.05 minimum on each dataset, and the gate logic should print which baselines are *blocking* and which would be *beaten*.

### 5.4 (Suggested) Add a "structural baseline audit" report

Generate a small `cold_baseline_audit.md` in each confirmatory run directory that explicitly lists:
- which warm scorer each baseline uses (EASE / content / popularity / ...)
- which cold scorer each baseline uses
- whether the scoring is symmetric (warm and cold use the same model) or asymmetric

This catches the kind of "content_direct used content for warm too" oversight that drove the round-5 false picture of LC2C losing.

## 6. Files I shipped in this collaboration

| File | Purpose |
|---|---|
| `_bestrec_run/run_poc_new_coldstart.py` | Full diagnostic POC with 5 candidate algorithms (CD_pow_T, CD_topk, CWA_B, PZC_LC2C, CDR_blend), plus 4 diagnostic variants. Outputs `results_poc_new_coldstart.json`. |
| `_bestrec_run/run_poc_cdr_books.py` | Slim production-only POC (CDR_validated, FAIR baseline, LC2C V2). Designed to run on Books in reasonable time. Outputs `results_poc_cdr.json`. |
| `_bestrec_run/results_poc_new_coldstart.json` | POC results (Beauty + Fashion + Instruments, all candidates). |
| `_bestrec_run/results_poc_cdr.json` | Slim CDR-only POC results across all 4 datasets. |
| `COLLAB_NEW_COLDSTART_ALGOS.md` | This file. |

## 7. Open questions for Codex

1. **Multi-seed reproducibility**: The POC was 1 seed × 5 folds per dataset. A 3-seed run on Beauty / Fashion / Instruments is in flight as `results_poc_cdr_3seed.json` (Books not multi-seeded yet due to 10-min-per-fold cost). The confirmatory pipeline should run all 5 seeds.
2. **User-clustered bootstrap CI vs FAIR baseline**: Under the user/item/fold-clustered bootstrap, does the CI on Δ = CDR − FAIR sit above zero on all four datasets? *(I expect Beauty / Instruments / Books yes; Fashion is borderline at single-seed p=1.9e-2.)*
3. **Validation overhead**: The α-grid validation step doubles the EASE work per fold. On Books this pushes the per-fold cost from ~30 s to ~2 min (5 seeds × 5 folds = ~50 min total per dataset). Acceptable inside the confirmatory budget?
4. **Honesty audit**: Is the per-user z-normalization step subject to any leakage I have missed? The z-statistics are computed from the cold pool's scores under the user's fixed history; the target's score contributes only 1/n_cold to the mean. The z-fit is per-user, per-test-call, and does not use any held-out target information. I think this is honest; please double-check.
5. **Naming**: Is "CDR_validated" or "lc2cpp_z_validated" or some other name preferable, given the existing naming conventions in `METHOD_LABELS`?
6. **Does CDR_validated beat content_direct in the cold-fold-only protocol too?** The round-3/4 paper used cold-fold-only. The POC focused on full-catalog because that is the harsher and more publication-realistic protocol. If we plan to keep cold-fold-only as a secondary result, CDR_validated should also be measured there; I expect it to be marginally better than LC2C++ valid-margin (which itself was +0.4 - 2.1% over LC2C V2 under cold-fold-only).

If Codex agrees with the integration plan, the simplest next action is:
- Copy `make_cdr_validated_full` and `select_alpha_on_validation` into `run_all_confirmatory.py`
- Rename or duplicate `make_content_direct_full` to fix the warm-via-EASE behaviour
- Rerun `python run_all_confirmatory.py --profile sota-confirmatory --datasets beauty,fashion,instruments,books --seeds 20260521,20260522,20260523,20260524,20260525 --candidate-scope full_catalog --no-books-cap`
- Inspect `_bestrec_confirmatory/<run_id>/significance.json` for the CDR vs FAIR comparison

If the publication gate still fails because the modern baselines (LightGCN/MultiVAE/iALS/TIGER/LIGER) are still `not_run`, that is the *correct* outcome and not a CDR issue. CDR is a new candidate to *try*, not a SOTA proof on its own.
