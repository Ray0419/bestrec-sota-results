# Strict Review of Resubmitted Paper

Date: 2026-05-21

Verdict: Reject.

The resubmission is more candid than the previous version, and several claims in the generated paper have been softened. However, the submission still fails the minimum bar for a publishable empirical paper. The remaining problems are not cosmetic. They include unreproducible advertised commands, stale and internally contradictory result files, statistical claims that are still not fully recomputable from the release, inconsistent definitions of the proposed LC2C method, and residual paper/README claims that directly contradict the corrected results.

The strongest reason to reject is simple: the response letter itself admits that multiple defects remain "camera-ready" TODOs. A paper cannot be accepted on the promise that core result files, per-user statistical vectors, LC2C naming, SOTA baselines, the Books score discrepancy, and sampling-cap disclosure will be fixed later.

## What I Checked

I reviewed the resubmitted artifacts, including:

- `BEST_Rec_v4_Full_Paper.pdf`, via `_paper_gen/build_paper_full.py`
- `RESPONSE_TO_STRICT_REVIEW.md`
- `README.md`
- `RUNNING.md`
- `SUBMISSION.md`
- `_bestrec_run/run_cold_item.py`
- `_bestrec_run/run_cold_item_v2.py`
- `_bestrec_run/run_lc2c_ablation.py`
- `_bestrec_run/compute_significance.py`
- `_bestrec_run/results_cold_item_v2.json`
- `_bestrec_run/results_ablation_lc2c.json`
- `_bestrec_run/significance_corrected.json`

I also ran the following checks:

```powershell
cd C:\Users\rayxc\Documents\R\_bestrec_run
uv run python run_cold_item.py --warm-only beauty
uv run python run_cold_item.py --cold-user beauty
uv run python compute_significance.py
uv run python -c "from run_cold_item_v2 import run_cold_item_v2; run_cold_item_v2('beauty')"
```

I also checked current and recent recommendation/cold-start references from primary sources:

- BLaIR, arXiv:2403.03952, revised 2026-04-20: https://arxiv.org/abs/2403.03952
- TIGER / generative retrieval, NeurIPS 2023: https://arxiv.org/abs/2305.05065
- CLCRec cold-start recommendation, ACM MM 2021: https://arxiv.org/abs/2107.05315
- DropoutNet, NeurIPS 2017: https://papers.nips.cc/paper_files/paper/2017/hash/dbd22ba3bd0df8f385bdac3e9f8be207-Abstract.html
- EASE, WWW 2019: https://arxiv.org/abs/1905.03375
- LightGCN, SIGIR 2020: https://arxiv.org/abs/2002.02126

## Improvements Since the Previous Submission

The authors did fix or partially fix a few visible issues:

- The paper now acknowledges that Higher-Order EASE numerically wins on Instruments.
- The paper now reports Holm-corrected significance markers in Table 5.2.
- Some LightGCN significance claims in the body were softened.
- The nonexistent `BEST_Rec_v5.ipynb` reference was mostly corrected to `BEST_Rec_v4.ipynb`.
- The abstract is more cautious and no longer presents the method as established SOTA.

These improvements are not enough. The release still cannot support the paper's claims.

## Fatal Finding 1: The Response Letter Admits the Package Is Not Ready

`RESPONSE_TO_STRICT_REVIEW.md` explicitly acknowledges:

- stale cold-item JSON remains: lines 51-68
- Books 0.1023 vs 0.099 remains unresolved except for an explanatory caption: lines 124-138
- CLCRec and DropoutNet are deferred to camera-ready: lines 178-188
- temporal evaluation is not fixed: lines 198-203
- `RANKING_USERS_CAP = 5000` still needs disclosure: lines 213-225 and 322
- LC2C V1/V2 naming is only partially addressed: lines 247-262
- cold-item paired Wilcoxon is still not possible because per-user vectors are not saved: lines 264-270 and 315-316
- the camera-ready TODO list includes regenerating stale JSON, unifying Books runs, adding SOTA baselines, saving per-user vectors, fixing LC2C names, and disclosing the sampling cap: lines 302-325

This is not a rebuttal that resolves the original review. It is an admission that the release remains incomplete. A reviewer should not accept a submission whose own response letter says core empirical and reproducibility issues are future work.

## Fatal Finding 2: The Advertised Warm and Cold-User Commands Still Do Not Reproduce Results

The prior review found that the reproduction commands failed. The resubmission "fixes" this by making the arguments parse, but the commands now simply print instructions and exit without running the experiment.

Evidence:

- `_bestrec_run/run_cold_item.py` lines 276-319 add argparse.
- Lines 295-310 show that `--warm-only` prints a message and returns.
- Lines 314-319 show that `--cold-user` prints a message and returns.

I ran:

```powershell
uv run python run_cold_item.py --warm-only beauty
```

The command exited successfully but did not run warm leave-one-out and did not produce `results_v6_baselines.json`. It printed that the numbers were produced by `BEST_Rec_v4.ipynb`.

I also ran:

```powershell
uv run python run_cold_item.py --cold-user beauty
```

This also exited successfully without running the cold-user experiment.

This is a serious reproducibility failure because the documentation still says the opposite:

- `RUNNING.md` line 157 advertises `uv run python run_cold_item.py --warm-only beauty fashion instruments books`.
- `RUNNING.md` line 160 says this produces `results_v6_baselines.json`.
- `RUNNING.md` line 165 advertises the cold-user command.
- `RUNNING.md` lines 308-309 say Tables 5.1, 5.2, and 5.3 come from these commands.
- `SUBMISSION.md` line 29 says `_bestrec_run/run_cold_item.py` contains warm-LOO, cold-user, and cold-item experiments with all baselines.
- `SUBMISSION.md` lines 83-93 present the warm-only command as a single-experiment rerun path.

This is not a valid fix. A command that silently becomes a documentation pointer is not a reproducibility command.

## Fatal Finding 3: The Cold-Item Result Provenance Is Internally Contradictory

The resubmission still cannot provide a clean source of truth for Table 5.4 / Figure 5.4.

The paper now claims LC2C-direct V2 values:

- Beauty: 0.173
- Fashion: 0.155
- Instruments: 0.058
- Books: 0.065

These are the `V2_lc2c_no_svd` values from `_bestrec_run/results_ablation_lc2c.json`, not the `lc2c` values in `_bestrec_run/results_cold_item_v2.json`.

But `_bestrec_run/run_cold_item_v2.py` still defines `lc2c` as the older V1 method:

- lines 6-7: LC2C is described as SBERT to SVD(B_warm)
- lines 43-65: `make_score_lc2c` uses `TruncatedSVD` and `Ridge`
- lines 165-166: the method list contains `lc2c`, with no V2/direct method
- line 223: this script writes `results_cold_item_v2.json`

I reran Beauty:

```powershell
uv run python -c "from run_cold_item_v2 import run_cold_item_v2; run_cold_item_v2('beauty')"
```

It produced:

- `lc2c` NDCG@10 = 0.1611
- `cf_hybrid` NDCG@10 = 0.1618
- no LC2C-direct V2 value of 0.1731

Therefore the function cited in the response as verifying the NDCG does not verify the paper's reported V2 number. It verifies the older V1 result.

## Fatal Finding 4: The Stored Cold-Item JSON Is Still Mathematically Impossible

The response admits the JSON is stale, but the stale JSON is still in the resubmitted package.

In `_bestrec_run/results_cold_item_v2.json`:

- Beauty random has `NDCG@10 = 0.0672` but `HR@10 = 0.0` and `MRR = 0.0` at lines 3-7.
- Beauty content-rating-weighted has `NDCG@10 = 0.1058` but `HR@10 = 0.0` and `MRR = 0.0` at lines 16-19.
- Beauty content-topk has `NDCG@10 = 0.1486` but `HR@10 = 0.0` and `MRR = 0.0` at lines 21-25.
- Beauty cf-hybrid has `NDCG@10 = 0.1618` but `HR@10 = 0.0` and `MRR = 0.0` at lines 33-37.

This cannot be correct. If NDCG@10 is positive for single-positive top-10 ranking, HR@10 cannot be zero.

The direct rerun confirms the stale values:

- random HR@10 = 0.1443, MRR = 0.0711
- content-rating-weighted HR@10 = 0.2178, MRR = 0.0978
- content-topk HR@10 = 0.2965, MRR = 0.1297
- cf-hybrid HR@10 = 0.3143, MRR = 0.1417

The authors cannot leave corrupted result files in the submission and ask reviewers to trust that the paper text is correct.

## Fatal Finding 5: The Significance Script Does Not Recompute the Claimed Warm-LOO Tests

`_bestrec_run/compute_significance.py` is not a self-contained statistical reproduction script.

Evidence:

- Lines 3-4 state that raw p-values were computed externally in `BEST_Rec_v4.ipynb`.
- The script loads stored raw p-values and applies Holm correction.
- It imports `wilcoxon` only in the cold-item section, not to recompute the warm-LOO raw p-values.

This means the package still lacks a standalone script that recomputes per-user paired Wilcoxon tests from saved per-user vectors. It only corrects previously computed p-values. That is not enough for an audit-grade reproduction package.

The corrected Holm output also weakens the paper:

- Beauty vs LightGCN: not significant.
- Fashion vs LightGCN: not significant.
- Instruments vs LightGCN: not significant.
- Books vs LightGCN: significant.
- Higher-Order EASE: not significantly worse than BEST-Rec on all four datasets.
- On Instruments, Higher-Order EASE numerically beats BEST-Rec.

The conclusion and documentation have not fully absorbed these facts.

## Fatal Finding 6: The Cold-Item Significance Section Labels V1 as V2

The cold-item section of `_bestrec_run/compute_significance.py` is misleading.

Evidence:

- Line 126 says it is testing LC2C V2 vs content-direct.
- Line 130 prints "LC2C (V2) vs. content-direct".
- Lines 151-153 read `ci_data[ds].get('lc2c', {})` from `results_cold_item_v2.json`.
- In `run_cold_item_v2.py`, `lc2c` is V1 SVD+Ridge, not V2/direct.

The script therefore prints V1 values while labeling them as V2:

- Beauty printed as V2: 0.1611, but actual V2 in `results_ablation_lc2c.json` is 0.1731.
- Fashion printed as V2: 0.1566, but actual V2 is 0.1548.
- Instruments printed as V2: 0.0502, but actual V2 is 0.0575.
- Books printed as V2: 0.0456, but actual V2 is 0.0653.

The same script then admits that per-user vectors are absent and the paired Wilcoxon test cannot be run:

- lines 132-136: only 5-fold means are available.
- lines 160-163: per-user vectors are not stored and regeneration is TODO.

This invalidates any cold-item significance claim in the current submission.

## Fatal Finding 7: The Paper Still Contains Claims That Contradict Its Own Corrected Results

The generated paper is more cautious in places, but still contains old or false claims.

Examples from `_paper_gen/build_paper_full.py`:

- Line 452 calls LightGCN "a tuned attention-based GNN baseline." LightGCN is not attention-based; the LightGCN paper describes a simplified GCN using neighborhood aggregation, with feature transformation and nonlinear activation removed. The resubmitted paper also later admits the deep baselines are canonical and not fully tuned.
- Lines 1771-1773 say BEST-Rec ranks first by NDCG@10 against six baselines. This is false because Higher-Order EASE numerically wins on Instruments.
- Lines 1801-1802 say BEST-Rec is the strongest model in its evaluation suite. This is false on the raw means because Higher-Order EASE is stronger on Instruments.
- Lines 1934-1936 and 1950 say V2 consistently improves on or dominates V1. This is false for Fashion: `results_ablation_lc2c.json` has V1 = 0.1566 and V2 = 0.1548.
- Lines 2138-2140 contain a confused statement that deep models match or beat the method only on "the largest dataset (Instruments)" and then say Books is largest by interaction count. Instruments is not the largest by interactions in the paper's own setup.
- Lines 2247-2248 say the method matches or beats six independent baselines including Higher-Order EASE. Numerically, it does not beat Higher-Order EASE on Instruments.
- Lines 2436-2444 in the conclusion say BEST-Rec statistically beats six baselines including LightGCN, MultiVAE, and iALS across datasets. That is false under the Holm-corrected table.
- Lines 2438-2439 repeat outdated LightGCN percentage claims of +78% on Beauty and +8% on Instruments, while the corrected body elsewhere says +64% on Beauty and +5% on Instruments.
- Line 2441 still uses "true cold-item evaluation" framing even though the protocol ranks among cold-fold items only and lacks temporal validation.

These are not harmless wording issues. They affect the paper's main claimed contribution.

## Fatal Finding 8: The README, RUNNING, and SUBMISSION Files Remain Misleading

The resubmission package still tells users and reviewers things that are not true.

Examples from `README.md`:

- Line 3 says the release addresses all prior reviewer concerns. It does not.
- Line 16 says "TRUE Cold-ITEM," an overclaim for a random item GroupKFold protocol that ranks only among cold-fold items.
- Lines 25-27 still present outdated LightGCN headline gains.
- Lines 41-50 define LC2C as V1 SVD+Ridge, while the paper now treats V2/direct as the headline method.
- Line 64 says "Reviewer concerns addressed (all 11)," contradicted by the response letter's own TODO list.
- Line 76 says paired Wilcoxon vs every baseline on all four datasets, but the cold-item LC2C comparison does not have paired Wilcoxon.
- Line 193 says "Per-fold SBERT encoding," but the package describes SBERT title embeddings as computed once from external metadata.
- Line 198 says "Full-item ranking," but the cold-item protocol ranks within the cold-fold catalog, not the full catalog.
- Line 205 claims LC2C is "the first cold-item method" of this kind without adequate comparison to prior cold-start representation-learning methods.

Examples from `RUNNING.md`:

- Lines 157-160 claim `run_cold_item.py --warm-only` produces warm-LOO results. It does not.
- Lines 165 and 221 claim `run_cold_item.py --cold-user` runs cold-user results. It does not.
- Line 278 tells users to reduce LightGCN batch size in `run_cold_item.py`, but the updated script no longer contains LightGCN training or a `batch_size` control for that path.
- Lines 308-309 map Tables 5.1-5.3 to commands that now only print notebook instructions.

Examples from `SUBMISSION.md`:

- Line 29 says `_bestrec_run/run_cold_item.py` contains warm-LOO, cold-user, and cold-item experiments. It now contains only cold-item plus non-executing stubs for warm/cold-user.
- Line 49 says every number in the paper traces to result JSON files. The actual Table 5.4 story mixes stale `results_cold_item_v2.json`, V2 values from `results_ablation_lc2c.json`, and a verification function that returns V1 values.
- Lines 83-93 present the warm-only command as a one-command reproduction path. It is not.

The release is therefore not just imperfect; it actively misleads reviewers about what is executable and what is cached.

## Fatal Finding 9: The Books 0.1023 vs 0.099 Discrepancy Is Explained, Not Fixed

The response acknowledges that the same algorithm has two different Books NDCG@10 values:

- `warm_mean['NDCG@10'] = 0.1023`
- `baselines['ease_sbert']['NDCG@10'] = 0.0990`

The paper now explains this as coming from slightly different seeded runs / an accidental reshuffle. That is not a fix.

For a final empirical table, the same method on the same split must have one number. The authors need to regenerate the relevant tables from a single immutable split file and a single result artifact. A caption explaining the inconsistency is insufficient.

## Fatal Finding 10: The Proposed Algorithm Is Not Clearly Defined Across Artifacts

LC2C still changes identity depending on which file the reviewer reads.

- `README.md` lines 41-50 define LC2C as SBERT -> SVD(B_warm) -> Ridge -> latent EASE space.
- `_bestrec_run/run_cold_item_v2.py` lines 43-65 implement that same V1 SVD+Ridge method as `lc2c`.
- `_bestrec_run/results_ablation_lc2c.json` calls V1 "sensitivity" and V2 "ablation: no SVD."
- `_paper_gen/build_paper_full.py` now presents V2/direct as the headline method.
- `RESPONSE_TO_STRICT_REVIEW.md` lines 247-262 admits this is only partially addressed and defers the rename/migration to camera-ready.

This is fatal for novelty and reproducibility. Reviewers cannot evaluate a proposed algorithm if the code, README, ablation file, significance script, and paper do not agree on what "LC2C" is.

## Fatal Finding 11: The Paper Does Not Establish State of the Art

The paper is now more careful in some places and says it is not verified against the entire recent literature. However, the package still contains SOTA-adjacent framing and "strongest model" language, while not running modern cold-start or retrieval baselines.

The baseline suite includes useful older baselines:

- EASE, a strong shallow CF model from 2019.
- LightGCN, a graph CF model from 2020.
- MultiVAE and iALS.
- Higher-Order EASE.

This is not enough to establish state of the art in 2026. At minimum, the cold-item claim should be compared against representative cold-start and text/item representation methods such as DropoutNet and CLCRec, and the text encoder framing should acknowledge BLaIR-style recommendation-specific semantic encoder evaluation. The generative retrieval literature, including TIGER, also demonstrates that modern retrieval recommenders are a different competitive class from the paper's current baselines.

The paper does not need to beat every modern method to be publishable, but it cannot claim or imply SOTA without these comparisons. The response letter itself admits CLCRec and DropoutNet are deferred to camera-ready.

## Major Finding 12: The "True Cold-Item" Claim Is Overstated

The item GroupKFold protocol is better than the previous threshold-only setup, but the wording remains too strong.

Problems:

- The split is random by item, not temporal. It does not test newly arriving catalog items under a realistic deployment timeline.
- The cold-item evaluation ranks among cold-fold items, not the full item catalog.
- The response letter admits `RANKING_USERS_CAP = 5000` is not properly disclosed.
- Cold-item paired significance is not computed because per-user vectors are missing.

A defensible description would be "random held-out item split with ranking over the held-out item fold." The current "TRUE cold-item" phrasing exaggerates the external validity of the experiment.

## Major Finding 13: The Baseline Tuning Story Is Internally Inconsistent

The paper calls LightGCN "tuned" at line 452, but later admits the deep baselines use canonical settings and are not fully tuned. The conclusion then converts raw mean gaps into broad statistical claims.

This matters because the corrected Holm output shows that the method is not significantly better than LightGCN on Beauty, Fashion, or Instruments. A strict reviewer should not allow strong deep-baseline language unless the tuning budget, search space, early stopping, negative sampling, and validation protocol are described and applied comparably.

## Major Finding 14: Corrected Holm Results Undermine the Headline Warm-LOO Claim

The corrected warm-LOO picture is:

- BEST-Rec beats popularity and weak baselines.
- BEST-Rec is not Holm-significantly better than LightGCN on 3 of 4 datasets.
- BEST-Rec is not Holm-significantly better than EASE-pure or Higher-Order EASE.
- Higher-Order EASE numerically wins on Instruments.
- The Books gain over LightGCN is real in this package, but Books iALS is OOM and the Books BEST-Rec score itself has an unresolved 0.1023 vs 0.099 inconsistency.

This supports a narrower claim: a simple EASE+SBERT linear model is competitive with several baselines and beats LightGCN on Books under the authors' protocol. It does not support "statistically beats six baselines" or "strongest model in the evaluation suite."

## Major Finding 15: The Cold-Item V2 Claim Is Not Statistically Validated

The reported V2 direct-B-row method is interesting, but the current validation is incomplete:

- V2 is pulled from an ablation JSON, not from the advertised `run_cold_item_v2.py` result file.
- V2 does not dominate V1 on Fashion.
- No per-user vectors are saved.
- No paired Wilcoxon is available.
- The significance script mislabels V1 as V2.
- The JSON file associated with cold-item v2 is stale for HR/MRR.

The cold-item result can be described as preliminary mean NDCG evidence only.

## Minor and Line-Level Issues

- `README.md` line 7 says warm leave-one-out is full-item ranking. This may be true for warm-LOO, but the same phrase is later used more broadly and becomes false for cold-item.
- `README.md` line 69 says "Per-fold encoding" while line 79 says SBERT is computed once from titles only. These need to be reconciled.
- `README.md` line 152 says "All baselines + Wilcoxon significance" but cold-item LC2C does not have a Wilcoxon test.
- `README.md` line 153 says "TRUE Cold-ITEM"; use a more precise protocol name.
- `README.md` line 193 says "Per-fold SBERT encoding and EASE refit"; SBERT title embeddings are not per-fold if computed once from external metadata.
- `README.md` line 198 says "Full-item ranking at evaluation"; this is not true for cold-item.
- `_paper_gen/build_paper_full.py` line 1073 says V2 dominates V1 on Beauty/Instruments/Books and ties Fashion, but the point estimate on Fashion is lower for V2.
- `_paper_gen/build_paper_full.py` line 1572 says "previously under-studied true cold-item GroupKFold protocol"; "true" should be removed.
- `_paper_gen/build_paper_full.py` line 1747 says the LightGCN gain is +113% on Books and statistically significant only on Books. This is fine, but it conflicts with the later conclusion.
- `_paper_gen/build_paper_full.py` line 1880 says Table 5.4 reports the four cold-item methods of Section 3.4, but the actual result provenance mixes multiple files and LC2C versions.
- `_paper_gen/build_paper_full.py` line 1908 says "TRUE cold-item"; again, too strong.
- `_paper_gen/build_paper_full.py` line 2104 calls the protocol "full cold-fold-catalog," which is more accurate and should replace "true cold-item" throughout.
- `_paper_gen/build_paper_full.py` lines 2479 onward cite tuned linear baselines as competitive with SOTA deep methods, but the paper itself did not tune all baselines or compare against modern cold-start methods.
- `_bestrec_run/compute_significance.py` line 134 says it reports a 95% bootstrap CI using fold means, but the printed output I observed reports only mean differences and percent improvements, not CIs.
- `_bestrec_run/compute_significance.py` imports `wilcoxon` in the cold-item section but does not run it for cold-item due to missing vectors.
- `RUNNING.md` line 278 references a LightGCN `batch_size` in `run_cold_item.py`; the updated script no longer contains that workflow.
- `SUBMISSION.md` line 30 says `run_cold_item_v2.py` contains variants V0/V1/V2/V3, but the script itself only runs `random`, `content_direct`, `content_rating_weighted`, `content_topk`, `lc2c`, and `cf_hybrid`. V2/V3 are in a separate ablation artifact.

## Required Fixes Before the Paper Can Be Reconsidered

1. Regenerate every result table from one clean, versioned pipeline.
2. Remove stale JSON files or regenerate them so all metrics are mutually consistent.
3. Make advertised commands actually run the advertised experiments, or remove those commands from the documentation.
4. Save per-user NDCG vectors for all paired statistical tests.
5. Recompute raw Wilcoxon tests from saved vectors in a standalone script; do not merely load external p-values.
6. Add Holm correction in the same standalone script.
7. Run proper cold-item paired tests for LC2C V2 vs content-direct, V1, and other relevant baselines.
8. Rename LC2C variants consistently across code, JSON, figures, README, and paper.
9. Decide whether V1 or V2 is the proposed method, and make the executable code match that decision.
10. Fix the Books 0.1023 vs 0.099 discrepancy by using one immutable split/result artifact.
11. Remove "true cold-item" language or replace it with the exact protocol name.
12. Disclose `RANKING_USERS_CAP = 5000` and any other ranking subsampling.
13. Stop claiming "statistically beats six baselines"; report the corrected Holm outcomes exactly.
14. Remove the false "attention-based" description of LightGCN.
15. Add modern cold-start/retrieval baselines or explicitly scope the claim away from SOTA.
16. Update README, RUNNING, SUBMISSION, paper text, figures, and captions so they all match the same results.

## Final Assessment

The resubmission is a partial cleanup, not a corrected paper. The authors have acknowledged many of the original review's objections, but they have not completed the work needed to resolve them. The package still contains corrupted results, non-executing reproduction commands, mislabeled statistical output, an inconsistent algorithm definition, and paper claims that contradict corrected tables.

I would not let this paper pass. At best, it should be resubmitted after a full reproduction rebuild and a substantially narrower claims section.
