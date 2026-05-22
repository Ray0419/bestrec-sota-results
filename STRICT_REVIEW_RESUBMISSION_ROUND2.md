# Strict Review of the Second Resubmission

Date: 2026-05-21

Verdict: Reject / major revision required before reconsideration.

This resubmission is materially better than the previous one. The authors fixed several concrete problems: `lc2c_v2` now exists in code and JSON, the cold-item JSON was regenerated with non-zero HR/MRR, the misleading `--warm-only` / `--cold-user` flags were removed, and the significance script no longer labels V1 as V2. Those fixes are real.

However, the paper still should not pass. The release remains internally inconsistent across the notebook, paper, figure files, scripts, JSON artifacts, and response letter. Several remaining issues are core acceptance issues, not camera-ready polish: missing SOTA baselines, no standalone recomputation of Wilcoxon tests from saved per-user vectors, no cold-item paired significance, unresolved single-pipeline Books inconsistency in `results_FINAL.json`, undisclosed or under-disclosed evaluation caps, stale figures with false claims embedded in the images, and a central notebook that still contains the old claims and old cold-item implementation.

The method is not established as state of the art. At best, the current evidence supports a narrower claim: BEST-Rec is a competitive, simple EASE+SBERT baseline under the authors' protocol, and LC2C V2 improves mean cold-fold-catalog NDCG over a content-direct baseline. The current package does not establish SOTA performance against modern text-augmented retrieval, generative retrieval, or cold-start item representation methods.

## What I Checked

I reviewed the new or modified artifacts:

- `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION.md`
- `BEST_Rec_v4_Full_Paper.pdf`, through `_paper_gen/build_paper_full.py`
- `README.md`
- `RUNNING.md`
- `SUBMISSION.md`
- `BEST_Rec_v4.ipynb`
- `_bestrec_run/run_cold_item.py`
- `_bestrec_run/run_cold_item_v2.py`
- `_bestrec_run/compute_significance.py`
- `_bestrec_run/results_cold_item_v2.json`
- `_bestrec_run/results_FINAL.json`
- `_bestrec_run/make_figures_v3.py`
- `_bestrec_run/run_lc2c_ablation.py`
- `figures/*.png` and `figures/*.pdf` timestamps

I ran:

```powershell
cd C:\Users\rayxc\Documents\R\_bestrec_run
uv run python run_cold_item.py --help
uv run python run_cold_item.py --warm-only beauty
uv run python compute_significance.py
uv run python run_cold_item_v2.py beauty
uv run python run_cold_item_v2.py beauty fashion instruments books
```

Important note: running `run_cold_item_v2.py beauty` overwrote `results_cold_item_v2.json` with only the Beauty entry. I then reran `run_cold_item_v2.py beauty fashion instruments books` to restore the all-dataset JSON. That overwrite behavior is itself a reproducibility bug, discussed below.

I also checked current/recent primary sources relevant to SOTA framing:

- BLaIR: https://arxiv.org/abs/2403.03952
- TIGER / generative retrieval: https://arxiv.org/abs/2305.05065
- LIGER / hybrid generative+dense retrieval: https://arxiv.org/abs/2411.18814
- CLCRec: https://arxiv.org/abs/2107.05315
- DropoutNet: https://papers.nips.cc/paper/7081-dropoutnet-addressing-cold-start-in-recommender-systems
- EASE: https://arxiv.org/abs/1905.03375
- LightGCN: https://arxiv.org/abs/2002.02126

## What Actually Improved

Credit where it is due:

- `_bestrec_run/run_cold_item.py --warm-only` now fails as an unrecognized argument instead of pretending to run an experiment.
- `run_cold_item.py --help` now says the script is cold-item only and points warm/cold-user reproduction to the notebook.
- `_bestrec_run/run_cold_item_v2.py` now includes `make_score_lc2c_v2`, and the `methods` list includes both `lc2c` and `lc2c_v2`.
- Running `uv run python run_cold_item_v2.py beauty` produces `lc2c_v2 = 0.1731`, matching the paper's Beauty Table 5.4 value.
- Running the full cold-item sweep restored all four dataset values in `results_cold_item_v2.json`.
- `_bestrec_run/compute_significance.py` now prints `LC2C V1` and `LC2C V2` separately.
- The cold-item JSON no longer contains the impossible positive-NDCG / zero-HR entries that were present in the previous resubmission.
- The generated paper's conclusion is substantially more honest than before about Holm-corrected LightGCN significance.

These are good fixes, but they do not rescue the submission.

## Fatal Finding 1: The Response Still Admits Core Acceptance Items Are Not Done

`RESPONSE_TO_STRICT_REVIEW_RESUBMISSION.md` still lists the following as TODO or camera-ready:

- `RANKING_USERS_CAP = 5000` disclosure: lines 35 and 372-374.
- Per-user vectors for cold-item Wilcoxon: lines 36, 364-366.
- CLCRec and DropoutNet head-to-head baselines: lines 37, 368-370.
- Chronological splits: line 38.
- Full LC2C naming unification in `run_lc2c_ablation.py` and `make_figures_v3.py`: lines 268-273 and 375-376.
- Standalone Wilcoxon recomputation from saved per-user vectors: lines 378-379.
- Single-pipeline warm-LOO rerun so `results_FINAL.json` values agree internally: lines 381-383.

This is not acceptable as a final empirical submission. The missing items are directly connected to the paper's statistical validity, reproducibility, cold-start validity, and SOTA positioning.

## Fatal Finding 2: The Central Notebook Is Still Stale and Contradicts the Revised Paper

The notebook is still a central reproduction artifact. `RUNNING.md` lines 154-167 say the warm-LOO and cold-user experiments live in `BEST_Rec_v4.ipynb`, and `SUBMISSION.md` line 51 says `results_FINAL.json` is aggregated from per-dataset notebook runs.

But `BEST_Rec_v4.ipynb` still contains old claims and old implementation details:

- Line 10 says the model beats LightGCN, MultiVAE, and iALS and that LC2C beats content-KNN by 11-68% on "truly held-out cold items." That is not the current paper's claim.
- Lines 20, 45, 1782, 1861, 1869, and 1879 still use "true cold-item" / "TRUE cold-ITEM" language.
- Line 1437 says the method statistically beats Popularity, MultiVAE, iALS, and LightGCN on every dataset. This is false under the corrected Holm table.
- Line 2029 still computes `ours_ndcg` using `ci_results["lc2c (ours)"]`, i.e. the old cold-item method, not the new `lc2c_v2` method.
- Lines 2086-2088 include an unchecked checklist item expecting Wilcoxon p-values vs LightGCN below 0.05 on at least 3 of 4 datasets, which the corrected results disprove.

The notebook is not merely stale prose. It is part of the stated reproduction path and still encodes the older cold-item story. A reviewer cannot accept a paper whose main notebook, paper, and standalone cold-item script disagree.

## Fatal Finding 3: The Paper's Reproducibility Section Is False

`_paper_gen/build_paper_full.py` lines 2278-2286 claim:

- `BEST_Rec_v4.ipynb` runs the entire pipeline end-to-end, including preprocessing, warm-LOO, cold-user, cold-item, all baselines, and every table and figure.
- Standalone scripts reproduce each individual experiment in isolation.

This contradicts the new documentation and the actual scripts:

- `RUNNING.md` says warm/cold-user live in the notebook and cold-item lives in standalone scripts.
- `run_cold_item.py` is now cold-item only.
- `run_cold_item_v2.py` is cold-item only.
- There is no standalone warm-LOO script equivalent to the notebook.
- The notebook still contains stale cold-item content and does not match the new `lc2c_v2` story.
- Figures are not regenerated by the PDF build; they are read from the existing `figures/` directory.

This is a core reproducibility defect. The paper tells reviewers one reproduction surface; the release actually contains another.

## Fatal Finding 4: The Figure Files Were Not Regenerated and Still Contain False Claims

The PDF was rebuilt on 2026-05-21, but the figure files in `figures/` are still dated 2026-04-30. The paper build script embeds those pre-existing files from the root `figures/` directory.

The figure generator still contains false titles:

- `_bestrec_run/make_figures_v3.py` line 53: title starts with "TRUE Cold-ITEM Evaluation".
- `_bestrec_run/make_figures_v3.py` lines 124-125: title says "V2 is uniformly better across datasets".

Both are contradicted by the revised text:

- The cold-item protocol is not full-catalog and should not be called "TRUE" cold-item.
- V2 is not uniformly better than V1; on Fashion, V2 = 0.1548 and V1 = 0.1566.

The captions in `_paper_gen/build_paper_full.py` were softened, but the embedded images themselves are stale. That is not a cosmetic issue because figures are part of the paper's claims.

## Fatal Finding 5: Single-Dataset Reruns Can Destroy the All-Dataset JSON Source of Truth

`_bestrec_run/run_cold_item_v2.py` lines 252-262 set `datasets = sys.argv[1:]`, initialize `all_results = {}`, and write `results_cold_item_v2.json` inside the loop.

Therefore:

```powershell
uv run python run_cold_item_v2.py beauty
```

does not merely verify Beauty. It overwrites `_bestrec_run/results_cold_item_v2.json` with a JSON file containing only Beauty.

I observed this directly:

- Before restore, `results_cold_item_v2.json` length dropped to 1301 bytes.
- It contained only the `"beauty"` key.
- I then reran all four datasets to restore the file.

This is a reproducibility hazard. The response letter itself recommends a direct Beauty rerun as evidence that V2 now matches the paper. That command mutates the source-of-truth artifact and removes Fashion/Instruments/Books unless the full sweep is rerun afterward.

## Fatal Finding 6: `run_cold_item.py` Still Claims to Populate Table 5.4, But It Does Not

The help text was improved but remains wrong in a different way.

`_bestrec_run/run_cold_item.py` lines 276-294 describe the script as a cold-item evaluation that "populates Table 5.4 of the paper." But the methods in that script are:

- `random`
- `imputed_pop`
- `content_direct`
- `ci_ease`
- `hybrid_50_50`

The current Table 5.4 uses `run_cold_item_v2.py` and reports:

- `random`
- `content_direct`
- `V1: LC2C with SVD k=64`
- `V2: LC2C-direct`

So the old script is still advertised as populating the current paper table when it actually writes `results_cold_item.json`, not the V2 table source. This is another source-of-truth conflict.

## Fatal Finding 7: The Books 0.1023 vs 0.099 Problem Is Still in `results_FINAL.json`

The visible paper table now uses 0.099 for Books, which makes Table 5.1 and Table 5.2 visually consistent. But the actual JSON still contains both numbers:

- `_bestrec_run/results_FINAL.json` line 266: `warm_mean["NDCG@10"] = 0.10232135573267423`
- `_bestrec_run/results_FINAL.json` line 323: `baselines["ease_sbert"]["NDCG@10"] = 0.09901505095929222`

`SUBMISSION.md` line 51 says `results_FINAL.json` is the source of truth for Tables 5.1, 5.2, and 5.3. The response letter itself admits a single-pipeline rerun is still needed.

Changing the paper table to one of the two JSON values is not a true fix. The source artifact remains internally inconsistent for the same method on Books.

## Fatal Finding 8: Statistical Claims Are Still Not Fully Auditable

`_bestrec_run/compute_significance.py` lines 1-8 say the raw p-values were computed externally in the notebook and that this script only applies Holm-Bonferroni correction to stored raw p-values.

This means:

- The warm-LOO Wilcoxon tests cannot be recomputed from saved per-user vectors.
- The reviewer cannot audit whether the raw per-user vectors, user caps, or exclusions used in the notebook match the reported p-values.
- The cold-item LC2C results have no paired Wilcoxon test at all because the required per-user vectors are not saved.

The script is useful, but it is not a complete statistical reproduction.

## Fatal Finding 9: The Paper Still Makes Unsupported Statistical Statements About Cold-Item Results

The authors correctly added caveats in some places, but unsupported statistical language remains.

Examples:

- `_paper_gen/build_paper_full.py` lines 171-172 say LC2C-direct and V1 are "statistically tied on Fashion." No per-user paired cold-item test was run, so this is not established.
- `_paper_gen/build_paper_full.py` lines 244-245 again say V2 "ties on Fashion." This is not a statistical result; the point estimate is actually lower for V2.
- `_paper_gen/build_paper_full.py` line 258 says significance is established with paired Wilcoxon signed-rank tests against six baselines and every reported number is averaged over five folds. This is too broad: cold-item significance is not established.

The proper wording is: "V2 slightly underperforms V1 on Fashion in mean NDCG, and no paired cold-item significance test is currently available."

## Fatal Finding 10: The Paper Still Overstates Baseline Ranking

The corrected table shows Higher-Order EASE numerically wins on Instruments. Yet `_paper_gen/build_paper_full.py` lines 1768-1772 still say Table 5.2 establishes that BEST-Rec "ranks first by NDCG@10 against six baselines."

That is false. On Instruments:

- Higher-Order EASE: 0.0570
- BEST-Rec: 0.0564

The paragraph later says HO-EASE wins Instruments by 0.001, but the first sentence is still wrong. A strict reviewer should not accept a paragraph that asserts both "ranks first" and "another method wins."

## Fatal Finding 11: The Paper Is Still Not a SOTA Paper

The resubmission is more explicit that it does not claim full SOTA, which is good. But the remaining language still flirts with a broader claim than the evidence supports.

Examples:

- `_paper_gen/build_paper_full.py` lines 1783-1787 speculates that TIGER would lose to v4 on small datasets without running it.
- `_paper_gen/build_paper_full.py` lines 1792-1794 say the authors expect LC2C's formulation to favor their method over CLCRec/DropoutNet-style competitors, without experiments.
- `_paper_gen/build_paper_full.py` lines 2464-2466 say deep alternatives do not yet justify their complexity at this data scale, even though several modern deep/text/cold-start baselines are missing.

Current/recent relevant primary sources make the missing comparisons material:

- BLaIR is trained for recommendation-specific language-item representations on Amazon Reviews 2023.
- TIGER introduced semantic-ID generative retrieval and reports cold-item generalization claims.
- LIGER explicitly studies generative vs dense retrieval and reports cold-start improvements.
- CLCRec directly targets cold-start item representation via contrastive learning.
- DropoutNet is a direct cold-start baseline for using content to support latent models.

Without at least some of these comparisons, the method is not established as state of the art.

## Fatal Finding 12: `RANKING_USERS_CAP = 5000` Is Still Not Properly Disclosed in the Paper

The evaluation cap exists:

- `_bestrec_run/v5_utils.py` line 11: `RANKING_USERS_CAP = 5000`
- `BEST_Rec_v4.ipynb` line 189 documents `RANKING_USERS = 5000`
- Several evaluation functions use the cap.

But the response letter still lists paper disclosure as TODO. A ranking cap changes evaluation cost and potentially metric variance. It must be disclosed in the methods section and table captions wherever it affects reported numbers.

## Major Finding 13: README Still Contains Overclaims

`README.md` improved substantially, but it still contains misleading statements:

- Line 3 says the project addresses all prior reviewer concerns. The same README later says the audit is only partial, and the response letter lists several TODOs.
- Line 90 says "Paired Wilcoxon vs every baseline, all 4 datasets" without clearly restricting this to the warm-LOO baseline table.
- Line 92 still phrases the original issue as "No true cold-start" and the fix as GroupKFold-by-item plus LC2C. This keeps the "true cold-start" framing alive.
- Line 218 claims novelty of the proposed algorithm while acknowledging that closely related cold-start methods have not been run head-to-head.

The README is still ahead of the evidence.

## Major Finding 14: LC2C Naming Is Still Inconsistent in Older Artifacts

The main V2 code is cleaner now, but not all artifacts were updated:

- `_bestrec_run/run_lc2c_ablation.py` line 5 still calls V1 "ours."
- Line 44 says "Ours: SVD(B_warm) + Ridge(SBERT -> CF latent)."
- Lines 124-125 label V1 as "ours" and V2 as "ablation."
- `_bestrec_run/make_figures_v3.py` still uses the older V0/V1/V2 naming and false V2 title language.

The response letter admits this is still partial. Because these artifacts produce paper figures, this inconsistency remains material.

## Major Finding 15: The Case Study Is Cherry-Picked by Construction

`_bestrec_run/case_study.py` lines 143-155 explicitly triage users by V2-over-V1 gain and sort descending. This is not inherently wrong if labeled as illustrative, but it must not be presented as representative evidence.

The paper text around `_paper_gen/build_paper_full.py` lines 2104-2107 is more honest than before because it says the table reports the eight Books-fold-0 users where V2 most strictly outperforms V1, and also reports that V1 and V2 tie on 72.5% of the 200-user pool. That caveat should remain prominent in the table caption and not be buried.

## Major Finding 16: The Determinism Claim Is Still Too Strong

The release makes strong reproducibility claims:

- `BEST_Rec_v4.ipynb` line 203 says running the same dataset twice on the same machine produces bit-identical results.
- `_paper_gen/build_paper_full.py` lines 2482-2484 say runs produce NDCG@10 identical to around 1e-8.
- `RUNNING.md` line 298 says two runs of the same script on the same machine produce bit-identical results, then says different machines may differ in the last 2-3 decimals.

But the notebook enables GPU/TF32 settings:

- `BEST_Rec_v4.ipynb` line 161: `torch.backends.cuda.matmul.allow_tf32 = True`
- line 162: `torch.backends.cudnn.allow_tf32 = True`
- line 163: `torch.backends.cudnn.benchmark = True`

Those settings are not a convincing basis for bit-identical deep baseline claims. The deterministic claim should be narrowed to the closed-form EASE portions, with GPU baselines treated separately unless deterministic PyTorch settings and environment controls are actually enforced.

## Major Finding 17: The Figures and Paper Build Are Not a Reproducible Pipeline

The PDF build reads existing figure files from `figures/`. The figure files were not regenerated after the resubmission, and their generator still contains stale titles. Therefore, `BEST_Rec_v4_Full_Paper.pdf` is not produced from a clean end-to-end current result pipeline.

This is exactly the kind of artifact drift that led to the previous stale JSON problems. The authors fixed the JSON but did not fix the figure generation path.

## Detailed Experiment Outcomes

### `run_cold_item.py --help`

Result: exits 0 and says the script is cold-item only. This is improved.

Remaining issue: the help text says it populates Table 5.4, but this script is the old cold-item method set and does not produce the current V2 table.

### `run_cold_item.py --warm-only beauty`

Result: exits 1 with "unrecognized arguments: --warm-only." This is the correct behavior after removing the fake flag.

### `compute_significance.py`

Result: exits 0 and prints the corrected Holm markers. It also prints cold-item mean-NDCG comparisons:

- Beauty: content 0.1449, V1 0.1611, V2 0.1731
- Fashion: content 0.1338, V1 0.1566, V2 0.1548
- Instruments: content 0.0355, V1 0.0502, V2 0.0575
- Books: content 0.0272, V1 0.0456, V2 0.0653

Remaining issue: the script explicitly says cold-item is a mean-of-fold-means comparison, not a per-user paired Wilcoxon test. It also cannot recompute warm-LOO raw p-values from saved per-user vectors.

### `run_cold_item_v2.py beauty`

Result: exits 0 and reproduces Beauty V2 = 0.1731. This part is fixed.

New issue: it overwrites `results_cold_item_v2.json` with only Beauty.

### `run_cold_item_v2.py beauty fashion instruments books`

Result: exits 0 in about 2.8 minutes and restores the all-dataset JSON. Values match the paper's current Table 5.4 rounding.

This supports the cold-item mean-NDCG table, but not cold-item statistical significance or SOTA status.

## SOTA Assessment

This is not a state-of-the-art algorithm as submitted.

The warm result is competitive with the authors' chosen baseline suite, but under Holm correction:

- It is not significantly better than LightGCN on Beauty, Fashion, or Instruments.
- It is not significantly better than EASE-pure or Higher-Order EASE on any dataset.
- Higher-Order EASE numerically wins on Instruments.
- The strongest LightGCN claim is only on Books.

The cold-item result is promising but preliminary:

- V2 beats content-direct in mean NDCG on all four datasets.
- V2 does not beat V1 on Fashion.
- No per-user paired significance is available.
- No head-to-head is run against CLCRec, DropoutNet, BLaIR-style encoders, TIGER/LIGER-style retrieval, or other modern cold-start/text-augmented recommenders.

Therefore, the proper claim is "competitive simple baseline with a promising cold-item extension," not SOTA.

## Required Fixes Before Reconsideration

1. Update `BEST_Rec_v4.ipynb` so it matches the current paper, current LC2C V2 method, current significance claims, and current cold-item terminology.
2. Either make the notebook truly reproduce every table/figure or remove that claim from the paper.
3. Regenerate all figures from current data and remove stale titles from `make_figures_v3.py`.
4. Fix `run_cold_item_v2.py` so single-dataset reruns do not silently delete other datasets from `results_cold_item_v2.json`, or write to a dataset-specific output.
5. Fix `run_cold_item.py` help text so it no longer claims to populate the current Table 5.4.
6. Resolve `results_FINAL.json` so Books has one canonical NDCG value for the same method, not both 0.1023 and 0.099.
7. Save per-user vectors for warm-LOO and cold-item.
8. Recompute all Wilcoxon tests from saved vectors in a standalone script.
9. Add paired cold-item significance tests for V2 vs content-direct and V2 vs V1.
10. Disclose `RANKING_USERS_CAP = 5000` in the paper methods and any affected captions.
11. Run at least direct cold-item baselines such as CLCRec and DropoutNet before making any strong cold-item contribution claim.
12. Remove speculative claims about TIGER/BLaIR/LIGER performance unless experiments are run.
13. Eliminate all "true cold-item" phrasing from notebook, figures, README, and paper images.
14. Make LC2C naming consistent in `run_lc2c_ablation.py`, figure generation code, JSON keys, README, and paper.
15. Narrow determinism claims to what is actually controlled and tested.

## Final Recommendation

Reject.

The second resubmission is no longer the same obviously broken package as before; several fixes are real. But the release still has too many unresolved contradictions to pass a strict review. The authors fixed the most visible stale JSON problem, but the deeper issue remains: the paper is assembled from artifacts that do not all describe the same experiment.

The work may become publishable after a clean end-to-end rebuild, updated notebook, regenerated figures, saved per-user statistical vectors, corrected JSON provenance, and head-to-head cold-start baselines. It is not ready now, and it is not state of the art as submitted.
