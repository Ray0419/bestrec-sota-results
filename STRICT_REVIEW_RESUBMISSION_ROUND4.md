# Strict Review of Resubmitted BEST-Rec v4 Paper - Round 4

Date reviewed: 2026-05-21  
Reviewer stance: adversarial, strict, looking for any remaining reason not to pass.

## Verdict

**Reject / do not pass in its current form.**

This resubmission fixes two major prior failures: the cold-item Wilcoxon test is now computed at a per-user unit of analysis, and the new DropoutNet baseline is no longer the obviously broken near-random baseline from the previous round. However, the submission still fails a strict reproducibility and claims audit. The paper, notebook, figures, JSON source-of-truth files, and submission notes do not agree with each other. Several remaining issues are not cosmetic: they affect whether the reported warm results can be reproduced, whether the official notebook matches the paper, whether Figure 5.2 uses the same LightGCN numbers as Table 5.2, and whether the DropoutNet comparison is fairly described.

My decision would be reject, or at minimum major revision with no acceptance until the authors resubmit a single coherent artifact set.

## What I Checked

I inspected the resubmitted response letter, paper generator, notebook, Markdown documentation, result JSONs, figure files, and scripts. I also reran the current significance script and a single cold-item experiment:

```powershell
uv run python compute_significance.py
uv run python run_cold_item_v2.py beauty
```

Key verified outputs:

- `compute_significance.py` confirms the new cold-item per-user Wilcoxon results:
  - Beauty: V2 > content p = 9.518e-06, V2 > V1 p = 0.02061, V2 > DropoutNet p = 2.483e-07.
  - Fashion: V2 > content p = 1.231e-06, V2 > V1 p = 0.7365 n.s., V2 > DropoutNet p = 3.962e-09.
  - Instruments: all three cold-item comparisons significant.
  - Books: all three cold-item comparisons reported as `<1e-300`.
- `run_cold_item_v2.py beauty` reproduces the Beauty cold-item means:
  - content-direct = 0.1449
  - LC2C V1 = 0.1611
  - LC2C V2 = 0.1731
  - DropoutNet = 0.1409
- `results_cold_item_v2_perpair_<dataset>.json` now has the schema `[[fold_id, user_id, item_id, ndcg], ...]` and eight methods for all four datasets.

I also checked current literature sources for the state-of-the-art question:

- DropoutNet: https://papers.nips.cc/paper/7081-dropoutnet-addressing-cold-start-in-recommender-systems
- BLaIR: https://arxiv.org/abs/2403.03952
- TIGER: https://arxiv.org/abs/2305.05065
- LIGER: https://arxiv.org/abs/2411.18814
- CLCRec: https://arxiv.org/abs/2107.05315
- MELT: https://arxiv.org/abs/2304.08382
- EASE: https://arxiv.org/abs/1905.03375
- LightGCN: https://arxiv.org/abs/2002.02126

## Summary of Improvements

The resubmission is materially better than the prior one.

1. **Cold-item per-user Wilcoxon is now implemented.**  
   `_bestrec_run/compute_significance.py:163-245` now aggregates cold-item NDCG by user before running Wilcoxon. This is a real correction of the previous pseudo-replication problem.

2. **Per-pair metadata is now saved.**  
   `_bestrec_run/run_cold_item_v2.py:357-388` writes `(fold_id, user_id, item_id, ndcg)` records. This allows a reviewer to reaggregate by user, fold, or item.

3. **DropoutNet is no longer an obviously invalid near-random baseline.**  
   Rerunning Beauty gives DropoutNet NDCG@10 = 0.1409, which is plausible and well above random = 0.0672.

4. **The paper no longer claims general state of the art outright in the strongest places.**  
   It now admits missing BLaIR, TIGER, CLCRec, MELT, and LIGER comparisons in `_paper_gen/build_paper_full.py:1802-1828`.

These fixes matter. Unfortunately, they do not make the paper pass.

## Fatal and Major Findings

### F1. The official notebook is still stale and contradicts the paper.

The paper says the notebook remains the official source for warm-LOO, cold-user, and warm baseline results:

- `_paper_gen/build_paper_full.py:2384-2405`
- `RUNNING.md:156-167`
- `README.md:159-167`

But `BEST_Rec_v4.ipynb` is still the old artifact. It still contains:

- Books warm NDCG = `0.1023`, while the resubmitted paper and JSON now use `0.099015...` (`BEST_Rec_v4.ipynb:55`).
- The false claim that "Ours statistically beats Popularity, MultiVAE, iALS, LightGCN on every dataset" (`BEST_Rec_v4.ipynb:1437`).
- Old "TRUE Cold-ITEM" language and an old cold-item path (`BEST_Rec_v4.ipynb:1782-1986`).
- No `lc2c_v2`.
- No DropoutNet.
- No current cold-item per-user Wilcoxon pipeline.

The response letter explicitly admits the notebook rewrite is deferred. That is not acceptable when the paper itself still identifies the notebook as the reproduction path for Tables 5.1-5.3. A reviewer following the submitted reproduction instructions lands in an artifact that does not match the paper.

Required fix: either remove the notebook from the official reproduction path or update and execute it so it matches the paper exactly.

### F2. The Books warm result was manually edited, not regenerated from a single immutable pipeline.

`_bestrec_run/results_FINAL.json:271` contains this note:

> Original warm_mean NDCG@10=0.1023213557 differed from baselines.ease_sbert.NDCG@10=0.0990150510 by ~0.003 due to two independent preprocessing passes... this field has been manually updated to match. A single-pipeline rerun... is on the camera-ready to-do list.

This is fatal for a strict reproducibility audit. The source-of-truth result JSON has been hand-reconciled after the fact, and the actual rerun that would prove the corrected value is still deferred. The manuscript repeats this reconciliation in `_paper_gen/build_paper_full.py:1694-1702`, but documenting a manual edit does not make the result reproducible.

Required fix: delete the hand reconciliation, rerun the full pipeline from immutable splits, regenerate the JSON, notebook, tables, and figures, and include hashes or split IDs proving the tables came from one run.

### F3. The paper still contradicts itself about cold-item Wilcoxon.

The paper now reports per-user cold-item Wilcoxon in Section 5.5.3:

- `_paper_gen/build_paper_full.py:1998-2043`

But an earlier headline summary still says the opposite:

- `_paper_gen/build_paper_full.py:1593-1597`: "per-user paired Wilcoxon for cold-item is deferred to camera-ready (per-user vectors not currently saved)."

This is a direct internal contradiction in the submitted paper. It makes the reviewer wonder which version of the experiment the authors actually intend to defend.

Required fix: remove all stale "deferred" language and audit the entire paper for old round-2/round-3 text.

### F4. Figure 5.2 is stale and uses different LightGCN numbers from Table 5.2.

This is a serious consistency failure.

The paper text reports LightGCN gaps as +64% / +43% / +5% / +113%:

- `_paper_gen/build_paper_full.py:2574-2576`
- `_paper_gen/build_paper_full.py:1786-1794`

However, the actual figure file `figures/fig2_vs_lightgcn.png` visually annotates +78% / +43% / +8% / +114%.

I traced the cause:

- `_bestrec_run/make_figures.py:25` loads `results_lightgcn.json`.
- `_bestrec_run/make_figures.py:64-65` inserts that file's LightGCN values into the warm figure data.
- `_bestrec_run/make_figures.py:116-130` computes the plotted percentage labels from those values.
- `results_lightgcn.json` has Beauty LightGCN = 0.052143 and Instruments LightGCN = 0.052399.
- `results_FINAL.json` has Beauty LightGCN = 0.056838 and Instruments LightGCN = 0.053837.

The table and the figure are therefore not using the same baseline values. This is not a rounding issue. For Beauty, the difference changes the headline gap from about +64% to about +78%.

Required fix: regenerate Figure 5.2 from `results_FINAL.json`, not from stale intermediate files. Then rebuild the PDF and verify the actual embedded figure annotations match the text.

### F5. Warm-LOO significance is still not independently reproducible from released per-user vectors.

The cold-item significance path is improved, but the warm-LOO significance remains weakly auditable.

`_bestrec_run/compute_significance.py:1-9` states that raw p-values are computed externally in `BEST_Rec_v4.ipynb`; the script only applies Holm-Bonferroni correction to stored raw p-values. Since the notebook is stale and no per-user warm NDCG vectors are saved, a reviewer cannot independently recompute the Table 5.2 Wilcoxon tests from the submitted non-notebook artifacts.

This is especially damaging because the paper's warm significance claims are nuanced and central:

- LightGCN significant only on Books.
- EASE-pure and Higher-Order EASE not significant on any dataset.
- MultiVAE significant on only some datasets.

Required fix: save per-user warm NDCG vectors for every method, every dataset, every fold, and recompute Table 5.2 p-values from those vectors in a standalone script.

### F6. The DropoutNet baseline is improved but still over-described as "faithful."

The new implementation is much better than before, but the paper and response letter overstate it.

The code itself admits important deviations:

- `_bestrec_run/run_cold_item_v2.py:105-110`: uses SVD instead of WMF, does not train a user tower, and uses only SBERT content features.
- `_bestrec_run/run_cold_item_v2.py:125-130`: computes `U_ref` and `V_ref` with `TruncatedSVD` on the warm interaction matrix.
- `_bestrec_run/run_cold_item_v2.py:140-186`: trains only an item tower and scores `U_ref @ V_cold_pred.T`.

The paper caption says DropoutNet is "implemented per Volkovs et al. (2017)" in `_paper_gen/build_paper_full.py:1928-1936`. That phrasing is too strong. The original DropoutNet paper describes a neural latent model explicitly trained for cold start through dropout and applicable on top of latent models; it is not simply "SVD item-factor regression with a content-only item tower." The current implementation should be called a **DropoutNet-style item-side cold-start baseline**, not a faithful reproduction.

Also, DropoutNet hyperparameters are not swept and no multi-seed variance is reported. The response letter admits this remains camera-ready scope. For a deep baseline used to establish a method advantage, a single default configuration is not enough.

Required fix: either run the official DropoutNet code or describe this as a simplified DropoutNet-style baseline, tune it fairly, run multiple seeds, and report uncertainty.

### F7. The paper still has stale "per-pair" language around Books user sampling.

The paper's cold-item sampling section says:

- `_paper_gen/build_paper_full.py:1435-1443`: the Books cap samples 5000 users per fold and says the "per-(user, cold-pair) Wilcoxon test" is computed over the resulting ~210K test pairs.

That wording is now stale and conflicts with Section 5.5.3, which says each user contributes one mean NDCG observation. It also obscures a subtle issue: Books has `n_users = 11,930` in the Wilcoxon table because the test uses the union of users sampled across folds, not one fixed 5000-user sample and not necessarily all eligible users.

Required fix: state exactly how Books users are sampled across folds, how the union of 11,930 users arises, and remove all "per-pair Wilcoxon" language.

### F8. The cold-item protocol is still not full-catalog ranking.

The paper does disclose this, which is good:

- `_paper_gen/build_paper_full.py:1448-1452`
- `_paper_gen/build_paper_full.py:1928-1929`
- `_paper_gen/build_paper_full.py:1944-1949`
- `README.md:26`

However, this limitation should be more prominent in the abstract-level cold-item claim. The cold-item task ranks among the held-out 20% item fold only, not the full catalog. This makes the absolute NDCG values and gains easier than a production cold-start retrieval problem where cold items must compete with all warm and cold catalog items.

Required fix: every cold-item headline should say "cold-fold-only candidate set" or "not full-catalog cold-start retrieval." The abstract currently says "cold-item GroupKFold" but does not make the candidate-set limitation visible enough.

### F9. The documentation still contradicts itself.

Examples:

- `SUBMISSION.md:30` says `run_cold_item_v2.py` has `lc2c_v2` plus six other variants, but the actual method list has eight total methods: random, content_direct, content_rating_weighted, content_topk, lc2c, lc2c_v2, cf_hybrid, dropoutnet.
- `SUBMISSION.md:32` describes `compute_significance.py` only as Table 5.2 Holm correction, omitting that it now also computes cold-item per-user Wilcoxon for Table 5.4b.
- `SUBMISSION.md:82` says DropoutNet is included, but `SUBMISSION.md:146-148` still lists DropoutNet as a missing SOTA comparison.
- `README.md:197` still instructs `make_figures_v2.py` while the newer figure text and submission docs refer to `make_figures_v3.py`.
- `RUNNING.md:330-331` says Figures 5.1 and 5.2 are generated by `make_figures_v3.py`, but `make_figures_v3.py` does not generate those figures. The warm figures come from `make_figures.py`, which is exactly why Figure 5.2 is stale.

These are not fatal alone, but taken together they show the resubmission was patched in pieces rather than rebuilt as a coherent artifact.

Required fix: run a full documentation consistency audit after regenerating all artifacts.

### F10. The paper is not state of the art, and the evaluation cannot establish SOTA.

The authors now largely admit this, but the user specifically asked whether the algorithm is state of the art. My answer is **no**.

Reasons:

- BLaIR has a 2026 ACL version and directly concerns language/item semantic encoders for recommendation on Amazon Reviews 2023.
- TIGER and LIGER represent modern semantic-ID/generative retrieval recommendation methods, including cold-start generalization claims.
- CLCRec is a direct cold-start recommendation competitor that explicitly targets preservation of collaborative signals in content representations for warm and cold-start items.
- MELT is a modern long-tail/sequential recommender baseline relevant to the claimed cold/long-tail regime.
- The paper still does not run BLaIR, TIGER, LIGER, CLCRec, or MELT.
- DropoutNet is the only newly added cold-start neural baseline, and it is a simplified single-seed implementation.
- iALS is still missing on Books due to OOM (`SUBMISSION.md:83`).
- There is no chronological split, no multi-seed deep baseline protocol, and no broad hyperparameter fairness report for the newly added deep baseline.

The paper may establish that LC2C V2 is competitive against the authors' chosen closed-form and older baseline suite under their custom cold-fold protocol. It does not establish state of the art.

### F11. The statistical protocol is improved but still incomplete.

Cold-item per-user Wilcoxon is a real improvement, but it is not the final word:

- Users are not the only dependency unit; cold items also induce shared difficulty across users.
- Books uses user sampling per fold, and the Wilcoxon `n = 11,930` should be interpreted carefully.
- The paper does not report a fold-block bootstrap or a user/item clustered bootstrap.
- The cold-item p-values on Books are essentially guaranteed to be tiny at this sample size, so practical effect sizes and confidence intervals should be emphasized more than stars.

Required fix: add a clustered bootstrap or randomization test that respects users, items, and folds, and report confidence intervals for the key cold-item deltas.

### F12. The claimed "all prior reviewer concerns addressed" framing is false.

`README.md:3` says the repository addresses "all" prior reviewer concerns. That is not true. The response letter itself admits remaining camera-ready items:

- notebook rewrite
- single-pipeline Books rerun
- warm-LOO per-user vector saving
- CLCRec/MELT/BLaIR/TIGER/LIGER comparisons
- chronological splits
- DropoutNet hyperparameter sweep and multi-seed runs

This should not be phrased as all concerns addressed.

## Smaller Issues and Required Corrections

1. The paper should not use "faithful DropoutNet" unless it runs the actual method or a much closer reproduction.
2. The abstract should not imply cold-item results are directly comparable to full-catalog ranking.
3. Table 5.0 should be audited for stale statements, especially the line saying cold-item Wilcoxon was deferred.
4. The README repository layout still foregrounds old scripts and figure paths.
5. The submission package should include a single `make all` or equivalent that rebuilds tables, figures, JSON, and PDF from the same sources.
6. Every figure should have a machine-readable provenance line: source JSON, script, command, timestamp, and commit/hash.
7. The authors should stop using manual "canonical" result reconciliation. Reproducibility requires regeneration, not reconciliation.

## Algorithmic Assessment

LC2C V2 is a plausible and interesting closed-form cold-item extension: direct ridge regression from frozen title embeddings into the EASE column space is simple, efficient, and empirically better than content-direct on the submitted cold-fold protocol. The result is worth studying.

But the algorithmic claim must be narrowed:

- It is a cold-fold candidate-set method, not a full-catalog cold-start retrieval system.
- It is validated mainly against content baselines, EASE-family baselines, LightGCN/MultiVAE/iALS in warm ranking, and a simplified DropoutNet-style cold-start baseline.
- It has not been tested against the current text-augmented, contrastive cold-start, long-tail, or generative retrieval literature.
- The warm-ranking advantage over tuned EASE variants is not statistically significant.

So the defensible claim is: **LC2C V2 is a simple closed-form method that improves cold-fold item ranking over content-direct and a simplified DropoutNet-style baseline on four Amazon Reviews 2023 subsets.**

The indefensible claim is: **LC2C V2 is state of the art.**

## Acceptance Conditions

I would not reconsider acceptance until all of the following are done:

1. Update and execute `BEST_Rec_v4.ipynb` so it matches the paper, or remove it from the reproduction path.
2. Rerun Books warm-LOO from a single immutable preprocessing/split pipeline and remove the manual reconciliation note.
3. Save per-user warm NDCG vectors and recompute Table 5.2 p-values from those vectors in a standalone script.
4. Regenerate Figure 5.2 from `results_FINAL.json` and verify the image annotations match the manuscript.
5. Remove the cold-item Wilcoxon contradiction in `_paper_gen/build_paper_full.py:1593-1597`.
6. Replace "faithful DropoutNet" with accurate wording or run a true official DropoutNet reproduction with tuning and multiple seeds.
7. Fix all stale documentation in `README.md`, `RUNNING.md`, and `SUBMISSION.md`.
8. Add at least one modern cold-start/text/generative comparator, with CLCRec and BLaIR being the most urgent.
9. Add a clustered bootstrap or fold-block uncertainty analysis for cold-item deltas.
10. Rebuild the entire PDF from scratch and verify that every table and figure has the same source JSON.

## Final Recommendation

Reject. The authors fixed some important statistical and baseline flaws, but the resubmission still has artifact-level contradictions, stale official reproduction code, hand-edited result provenance, a stale LightGCN figure, and an overclaimed DropoutNet implementation. Under a strict review standard, this paper should not pass until the full artifact set is regenerated coherently and the SOTA/evaluation claims are narrowed.
