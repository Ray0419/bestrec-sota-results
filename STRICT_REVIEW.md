# Strict Review of BEST-Rec v4/v5 Submission

Date: 2026-05-21  
Reviewer stance: very strict, adversarial-methods review  
Decision: Reject

## Summary Verdict

I would not let this paper pass in its current form.

The submission contains promising engineering ideas, especially the use of an EASE-style closed-form model with a title-embedding prior and a cold-item content-to-behavior mapping. However, the paper overclaims, the reproducibility package is internally inconsistent, several reported numbers contradict their own result files, some significance claims are false under the stored p-values, and the method is not demonstrated to be state of the art.

The most serious problems are not cosmetic. They affect the validity of the central claims:

- The documented reproduction commands for warm and cold-user experiments do not run.
- The repository references a missing `BEST_Rec_v5.ipynb`.
- Stored JSON results contain mathematically impossible metric combinations.
- The paper claims "highest mean NDCG@10" where its own result file shows a baseline is higher.
- The paper marks LightGCN on Instruments as significant, but the stored p-value is 0.299.
- The paper claims Holm-Bonferroni corrected significance, but the stored borderline raw p-values could not remain significant after Holm correction.
- The claimed SOTA status is not supported, and the paper itself admits missing contemporary baselines.

## What I Audited

Local artifacts inspected:

- `README.md`
- `RUNNING.md`
- `SUBMISSION.md`
- `_paper_gen/build_paper_full.py`
- `_bestrec_run/run_cold_item.py`
- `_bestrec_run/run_cold_item_v2.py`
- `_bestrec_run/run_lc2c_ablation.py`
- `_bestrec_run/run_hp_sweep.py`
- `_bestrec_run/run_ablation_embeddings.py`
- `_bestrec_run/ease_efficient.py`
- `_bestrec_run/v5_utils.py`
- `_bestrec_run/preprocess_v2.py`
- `_bestrec_run/results_*.json`

Commands/experiments run:

- `uv --version`
- `uv run python -c "import torch, numpy, scipy, sklearn; print('env ok')"`
- `uv run python run_cold_item.py --warm-only beauty`
- `uv run python run_cold_item.py --cold-user beauty`
- Direct function rerun: `run_cold_item_v2('beauty')`
- Direct function rerun: `run_ablation('beauty')` from `run_lc2c_ablation.py`

The managed Python referenced by the `uv` environment was initially missing. I repaired that with `uv python install 3.12.13` to test whether the package was otherwise runnable. After repair, imports worked, but the documented experiment commands still failed.

## Fatal Findings

### F1. The documented reproduction commands fail

`RUNNING.md` tells reviewers to run:

- `uv run python run_cold_item.py --warm-only beauty fashion instruments books` at `RUNNING.md:157`
- `uv run python run_cold_item.py --cold-user beauty fashion instruments books` at `RUNNING.md:165`
- the same commands again in the full sweep at `RUNNING.md:220-221`

But `_bestrec_run/run_cold_item.py` has no argparse handling for those flags. Its `main()` assigns `datasets = sys.argv[1:]` and then calls `run_cold_item(ds)` (`_bestrec_run/run_cold_item.py:275-282`). `run_cold_item()` immediately indexes `DATASET_KCORE[dataset]` (`_bestrec_run/run_cold_item.py:200-201`).

Observed result after repairing the `uv` Python:

```text
KeyError: '--warm-only'
KeyError: '--cold-user'
```

This invalidates the reviewer quick-start and the claimed reproducibility path for Tables 5.1, 5.2, and 5.3.

### F2. The main notebook named in the README does not exist

`README.md` says the main paper notebook is `BEST_Rec_v5.ipynb` (`README.md:84`) and instructs reviewers to open it (`README.md:147`) or execute it via nbconvert (`README.md:175`).

There is no `BEST_Rec_v5.ipynb` in the workspace. The available notebook is `BEST_Rec_v4.ipynb`. This is not a small typo: the README presents `BEST_Rec_v5.ipynb` as the primary reproduction artifact.

### F3. Stored cold-item metrics are mathematically impossible

`_bestrec_run/results_cold_item_v2.json` reports positive NDCG with zero HR and/or zero MRR for multiple methods. Example:

- Random Beauty: NDCG@10 = 0.0672, HR@10 = 0.0, MRR = 0.0 (`results_cold_item_v2.json:4-7`)
- `content_rating_weighted` Beauty: NDCG@10 = 0.1058, HR@10 = 0.0, MRR = 0.0 (`results_cold_item_v2.json:15-19`)
- `content_topk` Beauty: NDCG@10 = 0.1486, HR@10 = 0.0, MRR = 0.0 (`results_cold_item_v2.json:21-25`)
- `cf_hybrid` Beauty: NDCG@10 = 0.1618, HR@10 = 0.0, MRR = 0.0 (`results_cold_item_v2.json:33-37`)

Under the evaluator, if NDCG@10 is positive, the target is in the top 10, so HR@10 must also be positive. MRR also cannot be zero if any target is ranked.

I reran `run_cold_item_v2('beauty')` directly. The rerun produced:

| Method | NDCG@10 | HR@10 | MRR |
|---|---:|---:|---:|
| random | 0.0672 | 0.1443 | 0.0711 |
| content_direct | 0.1449 | 0.2891 | 0.1277 |
| content_rating_weighted | 0.1058 | 0.2178 | 0.0978 |
| content_topk | 0.1486 | 0.2965 | 0.1297 |
| lc2c | 0.1611 | 0.3113 | 0.1424 |
| cf_hybrid | 0.1618 | 0.3143 | 0.1417 |

The rerun confirms the NDCG values but proves the stored HR/MRR values are corrupt or stale. A paper cannot claim "every number traces to JSON" when the JSON contains impossible metric values.

### F4. The paper claims BEST-Rec has the highest mean NDCG on all four warm datasets, but its own results say otherwise

The generated paper claims:

- "BEST-Rec v4 attains the highest mean NDCG@10 on every warm-LOO setting" (`_paper_gen/build_paper_full.py:154-155`)
- "BEST-Rec v4 ranks first by mean NDCG@10 on all four warm-LOO datasets" (`_paper_gen/build_paper_full.py:278`)
- Table 5.2 bolds BEST-Rec on Instruments as `0.056` (`_paper_gen/build_paper_full.py:1676`)

But `_bestrec_run/results_FINAL.json` and `_bestrec_run/results_v6_baselines.json` report:

- Instruments `ease_sbert`: NDCG@10 = 0.0563607075 (`results_FINAL.json:249-250`)
- Instruments `higher_order`: NDCG@10 = 0.0569891143 (`results_FINAL.json:255-256`)

Higher-Order EASE is numerically higher than BEST-Rec on Instruments. The paper may say the difference is not significant, but then it cannot also claim "highest mean" or bold BEST-Rec as the numerical winner.

### F5. LightGCN significance claims are false or unsupported

The paper marks LightGCN as significant on Instruments in Table 5.2:

- LightGCN row has Instruments `0.052*` (`_paper_gen/build_paper_full.py:1673`)

But `_bestrec_run/results_FINAL.json` reports the Instruments LightGCN p-value as:

- `p_vs_ease_sbert = 0.2993680759972811` (`results_FINAL.json:235-240`)

That is not significant at 0.05. The paper also says LightGCN is beaten with `p < 0.05 on every dataset` (`_paper_gen/build_paper_full.py:467`) and repeats the headline "p < 0.05" claim (`_paper_gen/build_paper_full.py:1572-1573`). This is directly contradicted by the stored results.

### F6. Holm-Bonferroni correction is claimed but not evidenced, and borderline raw p-values would not survive it

The paper claims paired Wilcoxon with Holm-Bonferroni correction (`_paper_gen/build_paper_full.py:155-156`, `1498-1507`, `1691`). I found no script implementing Wilcoxon or Holm correction in `_bestrec_run/`; searching the code finds only p-value consumption in `make_paper_table.py`, not computation.

Even taking the stored p-values at face value, several raw p-values around 0.04 to 0.05 would not remain significant after Holm correction across six baseline comparisons. Example:

- Beauty LightGCN raw p = 0.049954707853206125 (`results_FINAL.json:75-80`)
- Fashion LightGCN raw p = 0.03987002313910495 (`results_FINAL.json:155-160`)

With six comparisons, such values are not credible as Holm-corrected significant results. The paper's significance markers and text should be treated as unreliable.

### F7. The paper and result files disagree on key numbers

Examples:

- `results_lightgcn.json` reports Beauty LightGCN NDCG@10 = 0.0521430697, but `results_FINAL.json` reports 0.0568378623 (`results_lightgcn.json:3`, `results_FINAL.json:75-76`).
- `results_lightgcn.json` reports Instruments LightGCN NDCG@10 = 0.0523991520, but `results_FINAL.json` reports 0.0538370556 (`results_lightgcn.json:15`, `results_FINAL.json:235-236`).
- Books `warm_mean` in `results_FINAL.json` is 0.1023213557 (`results_FINAL.json:265-266`), but Books baseline `ease_sbert` in the same file is 0.0990150509 (`results_FINAL.json:322-323`).
- Table 5.1 uses Books 0.1023, while Table 5.2 uses BEST-Rec Books 0.099 (`_paper_gen/build_paper_full.py:1643`, `1676`).

There may be an explanation involving different runs, but the submission does not explain it. A reviewer cannot trust a table when the same method/dataset has conflicting values across official artifacts.

### F8. The embedding ablation contradicts the paper's own claim

The paper's checklist claims:

- "SBERT > TF-IDF+SVD > no-prior > random" (`_paper_gen/build_paper_full.py:1576`)

But `_bestrec_run/results_ablation_embeddings.json` reports:

- Beauty `bow_svd` = 0.0934664073, `sbert (ours)` = 0.0928652502 (`results_ablation_embeddings.json:13-19`)
- Instruments `bow_svd` = 0.0572545158, `sbert (ours)` = 0.0563607075 (`results_ablation_embeddings.json:57-63`)

SBERT is not better than TF-IDF+SVD on Beauty or Instruments in the stored ablation. The more cautious text later in the paper says they are "roughly comparable" on simple-title datasets (`_paper_gen/build_paper_full.py:1926-1939`), but the headline checklist overclaims.

### F9. Hyperparameter sweep claims do not match the code or JSON

`RUNNING.md` says `run_hp_sweep.py beauty fashion instruments books` produces a 7 x 6 grid (`RUNNING.md:189-192`).

But `_bestrec_run/run_hp_sweep.py` defines:

- `LAMBDAS = [10, 30, 100, 300, 1000, 3000]` (`run_hp_sweep.py:22`)
- `BETAS = [0, 1, 3, 10, 30, 100]` (`run_hp_sweep.py:23`)

That is 6 x 6, not 7 x 6. It also omits lambda = 200, even though the selected hyperparameter for Instruments and Books is 200. The script default skips Books (`run_hp_sweep.py:116`) and uses only three folds (`run_hp_sweep.py:51`, `123`). The stored `results_hp_sweep.json` contains only Beauty, Fashion, and Instruments.

This undermines the robustness claim around selected hyperparameters.

## Major Methodological Concerns

### M1. The paper does not establish state of the art

As of 2026-05-21, the paper does not compare against several relevant contemporary recommendation/cold-start/generative-retrieval methods. The paper itself admits missing BLAIR, TIGER, CLCRec, MELT, and DropoutNet (`SUBMISSION.md:73`; `_paper_gen/build_paper_full.py:1738-1759`).

Current literature checks:

- BLaIR explicitly targets LLM semantic encoders for recommendation and is built around Amazon Reviews 2023 scale and recommendation-specific benchmarks: https://arxiv.org/abs/2403.03952
- TIGER proposes generative retrieval for recommendation and reports gains over current SOTA models, including improved handling for items with no prior interaction history: https://arxiv.org/abs/2305.05065
- CLCRec is a direct cold-start recommendation method that preserves collaborative signal in content representations and reports improvements over SOTA cold-start approaches: https://arxiv.org/abs/2107.05315
- DropoutNet is a direct cold-start recommender baseline from NeurIPS 2017 and remains a relevant comparison for feature-to-latent cold-start modeling: https://papers.nips.cc/paper_files/paper/2017/hash/dbd22ba3bd0df8f385bdac3e9f8be207-Abstract.html
- LETTER and ETEGRec are newer generative-recommendation/item-tokenization methods that claim SOTA progress in LLM/generative recommendation: https://arxiv.org/abs/2405.07314 and https://arxiv.org/abs/2409.05546
- General item representation learning for cold-start content recommendation is also an active 2024 direction: https://arxiv.org/abs/2404.13808

EASE itself is a 2019 method that already showed shallow linear models can beat deep collaborative filtering on sparse data: https://arxiv.org/abs/1905.03375. LightGCN is a 2020 graph baseline: https://arxiv.org/abs/2002.02126. Beating lightly tuned or canonical LightGCN/MultiVAE/iALS on four small Amazon subsets is not enough to claim SOTA in 2026.

Correct claim: "Competitive lightweight baseline under our limited benchmark suite."  
Incorrect claim: "State of the art algorithm."

### M2. Baselines are not sufficiently tuned

The paper admits LightGCN, MultiVAE, iALS, and Higher-Order EASE are run at canonical rather than per-dataset tuned settings (`_paper_gen/build_paper_full.py:2288-2295`). For a top-venue SOTA claim, this is not acceptable.

The strongest comparison should include:

- tuned LightGCN
- tuned MultiVAE
- tuned iALS / implicit ALS
- EASE and variants
- DropoutNet
- CLCRec
- BLaIR-style encoders
- at least one modern generative retrieval baseline such as TIGER/LETTER/ETEGRec when making broad SOTA claims

### M3. The cold-item protocol is not "true" cold-start in the strongest sense

The code applies k-core filtering before item holdout:

- `filtered = kcore_filter(...)` in `run_cold_item_v2.py:156`
- `splits = make_item_kfold(...)` in `run_cold_item_v2.py:164`

This means "cold" items are selected after observing the full dataset enough to pass k-core. They are unseen by the model in the training fold, but their inclusion depends on future/full-data interaction counts. That is a valid transductive benchmark if described carefully, but it is not the same as production new-item cold start.

The paper's "TRUE Cold-ITEM" phrasing is too strong.

### M4. The evaluation ignores time

The raw data contains timestamps and preprocessing keeps the latest duplicate (`preprocess_v2.py:54`, `62-63`). But reindexing drops timestamp fields (`v5_utils.py:29-30`; `preprocess_v2.py:127-128`). Warm splits and item splits are random rather than chronological.

For recommendation, random splits can leak future preference structure into train/test definitions. A strict recommender-systems reviewer would expect at least one chronological split, especially when the paper discusses production-style cold-start behavior.

### M5. Cold-item ranking only ranks among held-out cold items, not the full catalog

The evaluator builds `cold_arr` and scores only cold items (`run_cold_item.py:79`, `106-109`). The paper acknowledges that cold-item candidate pool is the cold fold, not full catalog (`_paper_gen/build_paper_full.py:1417-1430`).

That is a reasonable diagnostic, but the results should not be framed as full-catalog recommendation performance. A real system must decide among warm and cold items together.

### M6. User caps mean not all users are evaluated on large datasets

`RANKING_USERS_CAP = 5000` (`v5_utils.py:11`) and the evaluator samples users if there are more (`run_cold_item.py:96`). On Books, this means cold-item evaluation is sampled, not exhaustive over all eligible users. The paper should report the sampling and confidence intervals.

### M7. The qualitative case study is explicitly cherry-picked

`case_study.py` preselects a pool and sorts by V2-over-V1 gain (`case_study.py:142-156`). The paper admits Table 5.7 surfaces the users where V2 most strictly improves over V1 (`_paper_gen/build_paper_full.py:1980-1983`, `2047-2058`).

That can be acceptable as a mechanism illustration, but it should not be used rhetorically as representative evidence.

## Algorithmic Concerns

### A1. EASE+SBERT no longer has the clean EASE convex guarantee

The solver adds a content similarity matrix directly into the Gram matrix:

- `G += beta * S_content` (`ease_efficient.py:30`)

The code itself notes that the content similarity term can make `G` indefinite (`ease_efficient.py:35-36`) and falls back to generic solve or pseudoinverse (`ease_efficient.py:45`). If `G` is indefinite, the classic EASE derivation and closed-form ridge interpretation are not automatically valid. The paper should either prove the modified objective remains well-posed under its chosen lambda/beta values or report eigenvalue diagnostics for every fold.

### A2. LC2C novelty is overstated

LC2C V1 is a ridge map from SBERT title embeddings to SVD-compressed collaborative behavior (`run_cold_item_v2.py:43-65`). V2 is ridge regression from SBERT directly to EASE B-row behavior vectors (`run_lc2c_ablation.py:61-75`).

This is a plausible and useful lightweight method. But feature-to-latent or feature-to-collaborative mapping is a well-known cold-start theme. DropoutNet, CLCRec, NFC-style methods, and other content-to-collaborative representation methods are close enough that the novelty claim must be narrow:

Acceptable: "A simple ridge-regression content-to-EASE-row instantiation."  
Not acceptable: "The first cold-item method to learn content-to-CF mapping."

### A3. The final LC2C definition is inconsistent across artifacts

`run_cold_item_v2.py` defines LC2C as SVD plus Ridge (`run_cold_item_v2.py:43-65`). `run_lc2c_ablation.py` initially labels V1 as "ours" and V2 as an ablation (`run_lc2c_ablation.py:5-6`, `125`). But `make_figures_v3.py` calls V2 "ours" (`make_figures_v3.py:21-22`, `54`) and says V2 is uniformly better (`make_figures_v3.py:125`).

The paper eventually calls LC2C-direct V2 the final algorithm (`_paper_gen/build_paper_full.py:1853`), while README still presents the SVD version as the algorithm (`README.md:41-50`). The method definition should be unified.

### A4. Cold-item improvements lack statistical tests

Cold-item tables report mean and standard deviation, but I did not find p-values or paired tests for LC2C versus content_direct in the cold-item setting. Given that cold-item is the core new contribution, this is a major omission.

## Reproduction Rerun Notes

### Environment

Initial `uv run` failed because the virtual environment pointed at a missing managed Python:

```text
No Python at "C:\Users\rayxc\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
```

After `uv python install 3.12.13`, environment imports succeeded:

```text
env ok
```

This means the shipped environment was stale, though repairable.

### Documented warm/cold-user commands

After environment repair:

```text
uv run python run_cold_item.py --warm-only beauty
KeyError: '--warm-only'

uv run python run_cold_item.py --cold-user beauty
KeyError: '--cold-user'
```

### Beauty cold-item v2 rerun

Direct function rerun:

```text
run_cold_item_v2('beauty')
```

Result:

| Method | NDCG@10 | HR@10 | MRR |
|---|---:|---:|---:|
| random | 0.0672 | 0.1443 | 0.0711 |
| content_direct | 0.1449 | 0.2891 | 0.1277 |
| content_rating_weighted | 0.1058 | 0.2178 | 0.0978 |
| content_topk | 0.1486 | 0.2965 | 0.1297 |
| lc2c | 0.1611 | 0.3113 | 0.1424 |
| cf_hybrid | 0.1618 | 0.3143 | 0.1417 |

This supports the cold-item NDCG trend on Beauty but exposes corrupt stored HR/MRR values.

### Beauty LC2C ablation rerun

Direct function rerun:

```text
run_ablation('beauty')
```

Result:

| Variant | NDCG@10 | HR@10 |
|---|---:|---:|
| V0_content_direct | 0.1449 | 0.2891 |
| V1_lc2c_full_k64 | 0.1611 | 0.3113 |
| V2_lc2c_no_svd | 0.1731 | 0.3368 |
| V3_lc2c_no_ridge_k64 | 0.1610 | 0.3185 |
| V1_lc2c_full_k16 | 0.1563 | 0.3067 |
| V1_lc2c_full_k256 | 0.1615 | 0.3137 |

The Beauty ablation supports V2 over V1 and content_direct, but the paper needs tests across datasets and a unified definition of the final algorithm.

## Required Fixes Before Resubmission

1. Make the reproduction package actually runnable.
   - Add argparse to `run_cold_item.py` or correct `RUNNING.md`.
   - Provide the missing `BEST_Rec_v5.ipynb` or remove all references to it.
   - Rebuild the virtual environment or document `uv python install`.

2. Regenerate every JSON from source and remove stale/corrupt result files.
   - Fix `results_cold_item_v2.json`.
   - Resolve `results_lightgcn.json` versus `results_FINAL.json`.
   - Resolve Books 0.1023 versus 0.099 for `ease_sbert`.

3. Recompute all statistical tests from stored per-user/per-fold raw metrics.
   - Store the raw vectors used for Wilcoxon.
   - Apply Holm-Bonferroni correctly.
   - Remove significance stars that are not supported.
   - Report effect sizes, not only p-values.

4. Remove false claims.
   - Do not claim highest mean NDCG on Instruments.
   - Do not claim LightGCN is significant on every dataset.
   - Do not claim SBERT beats TF-IDF+SVD on every dataset.
   - Do not claim SOTA.

5. Strengthen the experimental protocol.
   - Add chronological splits.
   - Add a full-catalog cold-item evaluation.
   - Report sampling caps and confidence intervals.
   - Avoid k-core selection leakage language; call it transductive cold-item holdout if that is what it is.

6. Add missing baselines.
   - At minimum: tuned LightGCN, tuned MultiVAE, DropoutNet, CLCRec.
   - For broader SOTA claims: BLaIR-style encoders and one generative retrieval baseline such as TIGER/LETTER/ETEGRec.

7. Clean up the method definition.
   - Decide whether LC2C means SVD+Ridge V1 or direct B-row Ridge V2.
   - Update README, code comments, figures, and paper text accordingly.

8. Validate the modified EASE objective.
   - Report whether `X^T X + lambda I + beta S_content` is positive definite per fold.
   - If it is not, do not claim the classic EASE closed-form convex solution.

## Final Reviewer Recommendation

Reject.

The core idea may be salvageable as a lightweight, reproducible baseline paper if the authors substantially reduce the claims and fix the evaluation package. In its present form, the paper does not meet the bar for correctness, reproducibility, or SOTA validation.

