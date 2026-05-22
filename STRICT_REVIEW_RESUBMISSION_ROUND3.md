# Strict Review of the Third Resubmission

Date: 2026-05-21

Verdict: Reject / major revision required.

This resubmission contains real new work. The authors added a DropoutNet-labeled cold-start baseline, saved cold-item per-pair NDCG vectors, added a cold-item Wilcoxon section, fixed the single-dataset JSON merge bug, corrected the legacy `run_cold_item.py` help text, and regenerated some figures. These are genuine improvements.

I still would not let the paper pass. The current package remains internally inconsistent, and the new statistical and baseline claims are too weak to support the stronger conclusion now being made. The biggest new problem is that the "DropoutNet" baseline is not a faithful DropoutNet implementation and is so weak that it underperforms random on Beauty. The biggest statistical problem is that the new Wilcoxon test treats every `(user, cold-item)` pair as an independent sample even though pairs are clustered by user, fold, candidate set, and trained model. This creates pseudo-replication and produces absurd p-values such as zero underflow on Books.

The paper is closer, but it is still not acceptable and is not state of the art as submitted.

## What I Checked

I reviewed the new or modified files:

- `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND2.md`
- `BEST_Rec_v4_Full_Paper.pdf`, via `_paper_gen/build_paper_full.py`
- `_bestrec_run/run_cold_item_v2.py`
- `_bestrec_run/compute_significance.py`
- `_bestrec_run/significance_cold_item_corrected.json`
- `_bestrec_run/results_cold_item_v2.json`
- `_bestrec_run/results_cold_item_v2_perpair_*.json`
- `_bestrec_run/run_cold_item.py`
- `_bestrec_run/make_figures_v3.py`
- `BEST_Rec_v4.ipynb`
- `README.md`
- `RUNNING.md`
- `SUBMISSION.md`
- root `figures/` timestamps

I ran:

```powershell
cd C:\Users\rayxc\Documents\R\_bestrec_run
uv run python run_cold_item.py --help
uv run python compute_significance.py
uv run python run_cold_item_v2.py beauty
```

I also checked that the single-dataset Beauty rerun preserved the four dataset keys in `results_cold_item_v2.json`.

Relevant primary-source context:

- DropoutNet: https://papers.nips.cc/paper/7081-dropoutnet-addressing-cold-start-in-recommender-systems
- BLaIR: https://arxiv.org/abs/2403.03952
- TIGER: https://arxiv.org/abs/2305.05065
- LIGER: https://arxiv.org/abs/2411.18814
- CLCRec: https://arxiv.org/abs/2107.05315
- EASE: https://arxiv.org/abs/1905.03375
- LightGCN: https://arxiv.org/abs/2002.02126

## Improvements Since the Last Round

The following fixes are real:

- `run_cold_item.py --help` now clearly says it is a legacy cold-item script and not the current Table 5.4 source.
- `run_cold_item_v2.py beauty` no longer deletes Fashion/Instruments/Books from `results_cold_item_v2.json`; after my rerun, the JSON still contained all four keys.
- `run_cold_item_v2.py` now writes per-pair vectors to `results_cold_item_v2_perpair_<dataset>.json`.
- `compute_significance.py` now recomputes cold-item Wilcoxon tests from those per-pair vectors.
- `significance_cold_item_corrected.json` is generated and contains Holm-corrected cold-item markers.
- Root `figures/fig7_cold_item_v2.*` and `figures/fig9_lc2c_latentdim.*` were regenerated on 2026-05-21.
- The paper now discloses `RANKING_USERS_CAP = 5000` in `_paper_gen/build_paper_full.py` lines 1434-1442.

These changes reduce some previous reproducibility failures. They do not resolve the remaining fatal issues.

## Fatal Finding 1: The New DropoutNet Baseline Is Not a Faithful DropoutNet Baseline

The paper now treats DropoutNet as a canonical cold-start deep baseline and claims LC2C V2 beats it on all four datasets. I do not accept that claim because the implementation is not faithful enough to carry that name.

Evidence from `_bestrec_run/run_cold_item_v2.py`:

- Lines 80-106 describe a "dual-tower" DropoutNet.
- Lines 162-163 instantiate both `user_tower` and `item_tower`.
- Line 165 puts both towers into the optimizer.
- But the training loop at lines 178-194 only calls `item_tower`.
- The `user_tower` is never used in a forward pass and never receives gradients.
- The target at line 187 is just `I_cf_t[sl]`, an SVD item embedding.
- The loss at line 193 is MSE reconstruction of item SVD embeddings, not a user-item recommendation loss.
- Inference at line 206 scores with raw `U_cf @ I_cold_emb.T`, not with the trained user tower.

This is not a trained dual-tower DropoutNet recommendation model. It is closer to a neural content-to-SVD-item-embedding mapper, and even that mapper is trained only with item reconstruction. Calling it "DropoutNet" is misleading.

The weakness shows in the results:

- Beauty random NDCG@10 = 0.0672.
- Beauty "dropoutnet" NDCG@10 = 0.0551.

A baseline that loses to random on Beauty should not be used to claim a decisive win over a canonical cold-start deep method.

The original DropoutNet paper proposes a neural latent model trained for cold start through dropout on top of latent recommendation models. The submitted implementation does not demonstrate that baseline faithfully. The paper must rename it to "simplified DropoutNet-inspired content-to-SVD baseline" or implement a real DropoutNet baseline.

## Fatal Finding 2: The New Per-Pair Wilcoxon Test Is Pseudo-Replication

The new `compute_significance.py` reports extremely small p-values by treating every `(user, cold-item)` pair as an independent Wilcoxon sample:

- Beauty: 2,535 pairs.
- Fashion: 3,801 pairs.
- Instruments: 59,026 pairs.
- Books: 209,507 pairs.

Evidence:

- `_bestrec_run/run_cold_item.py` lines 110-125 appends an NDCG value for every test item of every user.
- Lines 130-134 store those values as `ndcg_per_pair`.
- `_bestrec_run/run_cold_item_v2.py` lines 389-392 concatenate these vectors across folds.
- `_bestrec_run/compute_significance.py` lines 199-207 run Wilcoxon directly on the pair-level arrays.

This violates the likely independence structure of the evaluation. Pairs share:

- the same user history,
- the same fold-trained model,
- the same cold candidate set,
- the same item split,
- and often multiple test items per user.

The correct statistical unit should be per user, per fold, or a clustered/block bootstrap that respects user/fold grouping. At minimum, the released vectors must include `(fold_id, user_id, item_id)` so a reviewer can aggregate or block the test. The current JSON stores only arrays of NDCG values, so the grouping information needed for a proper audit has been discarded.

Therefore the new claims like "p < 1e-300" and "audit-grade evidence" are not valid. They are artifacts of using an inflated sample size.

## Fatal Finding 3: The Per-Pair JSON Is Not Sufficiently Auditable

The new per-pair files contain method-name keys mapped to raw NDCG arrays. They do not store:

- fold id,
- user id,
- item id,
- candidate set size,
- target rank,
- whether a user appears multiple times,
- or any stable row identifier proving alignment across methods.

`compute_significance.py` lines 194-200 simply truncates both arrays to the same length and assumes row alignment. That may be true because the same loop generated them, but it is not auditable from the JSON itself.

This is not an acceptable statistical artifact for a paper whose main new claim now rests on those p-values.

## Fatal Finding 4: The README, RUNNING, and SUBMISSION Files Were Not Updated for This Round

The response letter says DropoutNet and cold-item significance are now included, but the public-facing documentation still says the opposite.

Examples:

- `README.md` line 26 still says cold-item paired Wilcoxon is camera-ready because per-user vectors are not saved.
- `README.md` line 167 repeats that cold-item paired Wilcoxon is deferred to camera-ready.
- `README.md` line 212 says cold-item significance is on the camera-ready to-do list.
- `README.md` line 218 says DropoutNet, CLCRec, and MELT are not yet run head-to-head.
- `RUNNING.md` line 177 still says `run_cold_item_v2.py` produces seven methods and omits DropoutNet.
- `RUNNING.md` line 324 maps Table 5.4 only to `results_cold_item_v2.json`, with no mention of per-pair JSON or Table 5.4b.
- `SUBMISSION.md` line 52 still says `results_cold_item_v2.json` covers seven methods.
- `SUBMISSION.md` line 80 still lists DropoutNet baseline runs as not included.
- `SUBMISSION.md` lines 144-146 still names DropoutNet as a missing comparison.

This is a major release-integrity problem. The paper, response letter, README, RUNNING guide, and submission manifest do not describe the same package.

## Fatal Finding 5: The Central Notebook Is Still Stale

The response admits the notebook is still stale, but the notebook remains part of the warm/cold-user reproduction path.

Evidence from `BEST_Rec_v4.ipynb`:

- Line 10 still claims the model beats LightGCN, MultiVAE, and iALS and that LC2C beats content-KNN by 11-68% on "truly held-out cold items."
- Lines 20, 45, 1782, 1861, 1869, and 1879 still use "true cold-item" language.
- Line 55 still reports Books NDCG@10 = 0.1023, while the paper now uses 0.0990.
- Line 1437 still says the method statistically beats Popularity, MultiVAE, iALS, and LightGCN on every dataset.
- The notebook still lacks the new `lc2c_v2`/DropoutNet/per-pair cold-item workflow.

The authors cannot keep telling reviewers that the notebook is the reproduction path while leaving it with old claims and old code paths.

## Fatal Finding 6: The Books 0.1023 vs 0.099 Conflict Remains in the Source JSON

The visible paper table uses 0.099 for Books. The source JSON still contains two inconsistent values:

- `_bestrec_run/results_FINAL.json` line 266: `warm_mean["NDCG@10"] = 0.10232135573267423`.
- `_bestrec_run/results_FINAL.json` line 323: `baselines["ease_sbert"]["NDCG@10"] = 0.09901505095929222`.

The response admits the single-pipeline rerun is still deferred. A paper table choosing one value while the source artifact contains both is still not clean reproducibility.

## Fatal Finding 7: Warm-LOO Significance Is Still Not Recomputable

The new cold-item significance script improved, but warm-LOO significance remains only partially auditable.

`_bestrec_run/compute_significance.py` lines 1-8 still say the raw p-values were computed externally in the notebook and that the script only applies Holm-Bonferroni correction to those stored p-values. The per-user vectors for warm-LOO are still not saved.

So the paper still lacks a standalone script that recomputes the warm-LOO Wilcoxon tests from released raw per-user vectors.

## Fatal Finding 8: The Paper Contradicts Itself About DropoutNet

The generated paper has an internal contradiction:

- `_paper_gen/build_paper_full.py` lines 165-166 say the paper does not compare against specialized cold-item methods including DropoutNet and leaves those head-to-head comparisons to future work.
- Lines 173-175 then say LC2C V2 beats the DropoutNet cold-start baseline.
- Lines 1816-1818 again say DropoutNet was added.
- Lines 1824-1825 then say "We commit to running CLCRec and DropoutNet as baselines for the camera-ready version."

DropoutNet is simultaneously absent, present, and future work. This is a direct contradiction in the paper text.

## Fatal Finding 9: The Paper Overstates the New Significance Evidence

The paper says:

- `_paper_gen/build_paper_full.py` line 2045: "audit-grade evidence."
- Lines 2046-2048: every claim about LC2C V2 vs content-direct and DropoutNet is statistically backed.
- Lines 2558-2561: cold-item gains are significant on all four datasets and beat DropoutNet by 3x to 13x.

Because the test uses dependent pair-level observations and a weak DropoutNet-like baseline, these claims are too strong. At most, the current test is an exploratory pair-level test under an independence assumption. It should not be framed as audit-grade evidence.

## Fatal Finding 10: The SOTA Claim Is Still Not Established

The response is more careful about not claiming full SOTA, but the paper still positions the result too strongly relative to the missing literature.

Missing direct comparisons remain:

- CLCRec,
- MELT,
- BLaIR,
- TIGER,
- LIGER-style hybrid retrieval/generative methods,
- and properly tuned deep cold-start/retrieval baselines.

Adding one weak, simplified DropoutNet-inspired baseline does not close this gap. The method can be described as competitive within the authors' limited baseline suite. It is not state of the art.

## Major Finding 11: The Figure Pipeline Is Still Not Fully Current

Some figures were regenerated:

- root `figures/fig7_cold_item_v2.*`
- root `figures/fig9_lc2c_latentdim.*`

But many root figures still have 2026-04-30 timestamps, including `fig8_lc2c_ablation.*`. The paper's reproducibility section says `make_figures_v3.py` regenerates every figure from current result JSONs, but the script only saves `fig7`, `fig8`, and `fig9`. It does not regenerate the whole paper figure suite.

Evidence:

- `_bestrec_run/make_figures_v3.py` only calls `savefig` for `fig7_cold_item_v2`, `fig8_lc2c_ablation`, and `fig9_lc2c_latentdim`.
- `_paper_gen/build_paper_full.py` lines 2386-2388 say `make_figures_v3.py` regenerates every figure from current result JSONs.

That statement is false.

## Major Finding 12: LC2C Naming Is Still Inconsistent in Ablation Code

`_bestrec_run/run_lc2c_ablation.py` still labels V1 as "ours":

- line 5: V1 is "ours."
- line 44: "Ours: SVD(B_warm) + Ridge."
- line 124: `V1_lc2c_full_k64` is "ours: SVD k=64 + Ridge."
- line 125: V2 is still described as an ablation.

The paper now says V2 is the headline method. The ablation artifact still says V1 is ours. This should have been fixed once the authors changed the proposed method.

## Major Finding 13: The New DropoutNet Result Is Not Reproducible Enough

The DropoutNet-like baseline is trained with PyTorch, but the paper does not report:

- validation protocol,
- hyperparameter search,
- multiple seeds,
- sensitivity to latent dimension,
- sensitivity to dropout probability,
- training loss convergence,
- CPU/GPU determinism controls,
- or whether the same baseline was tuned comparably to LC2C.

The paper cannot use a single under-tuned run of a weak baseline to claim "canonical deep cold-start baseline" coverage.

## Major Finding 14: Table 5.4 Significance Markers Are Easy to Misread

In Table 5.4, the non-V2 rows carry markers for the test "V2 > that row," not for the row's own performance. The caption explains this, but the table is still unusual and likely to be misread. A cleaner presentation would put significance in Table 5.4b only and leave Table 5.4 as means/stds.

## Major Finding 15: `p = 0` Should Not Be Reported as a Numerical Result

`significance_cold_item_corrected.json` stores several raw p-values as `0.0` due to numerical underflow. The paper translates these to `p < 1e-300`, which is better, but the JSON should not present zero p-values as if they were literal probabilities. The script should format underflow explicitly and store a lower bound or string.

## Experiment Results I Verified

`uv run python run_cold_item.py --help` now correctly says:

- the script is legacy,
- it writes `results_cold_item.json`,
- it is not Table 5.4,
- Table 5.4 uses `run_cold_item_v2.py`.

`uv run python compute_significance.py` exits successfully and prints:

- warm Holm markers unchanged from the prior review,
- cold-item V2 vs content-direct significant on all four datasets under the pair-level test,
- V2 vs V1 not significant on Fashion,
- V2 vs DropoutNet significant on all four datasets under the pair-level test.

`uv run python run_cold_item_v2.py beauty` exits successfully and preserves all four dataset keys in `results_cold_item_v2.json`. The JSON merge bug appears fixed.

The Beauty rerun produced:

- random NDCG@10 = 0.0672,
- content_direct = 0.1449,
- lc2c = 0.1611,
- lc2c_v2 = 0.1731,
- dropoutnet = 0.0551.

The fact that DropoutNet is below random on Beauty reinforces that this baseline is not a credible canonical cold-start benchmark.

## Required Fixes Before Reconsideration

1. Replace the current DropoutNet-like implementation with a faithful, tuned DropoutNet baseline, or rename it honestly as a simplified content-to-SVD neural baseline.
2. Report multiple seeds and tuning details for the DropoutNet-like model.
3. Redo cold-item significance with a proper unit of analysis: per-user, per-fold, clustered bootstrap, or hierarchical model.
4. Save `(fold_id, user_id, item_id, rank, NDCG)` for each cold-item observation so the statistical test is auditable.
5. Update README, RUNNING, and SUBMISSION so they match the new DropoutNet/per-pair claims.
6. Update `BEST_Rec_v4.ipynb` or remove it as a claimed reproduction artifact.
7. Resolve the Books 0.1023 vs 0.099 conflict in `results_FINAL.json` with a single-pipeline rerun.
8. Save warm-LOO per-user vectors and recompute warm Wilcoxon tests from released data.
9. Fix the paper's DropoutNet contradiction in the abstract and SOTA discussion.
10. Remove "audit-grade" language for the pair-level Wilcoxon test.
11. Run CLCRec and MELT, or narrow the cold-start literature claim further.
12. Correct `run_lc2c_ablation.py` so V2 is consistently the proposed method and V1 is consistently the ablation.
13. Fix figure-generation documentation so it does not claim `make_figures_v3.py` regenerates every paper figure.
14. Remove or isolate old figures that are no longer part of the current paper.
15. Stop using p-value underflow as `0.0` in JSON.

## Final Assessment

Reject.

This is the strongest resubmission so far, and the authors have made real progress. But the new evidence does not support acceptance. The DropoutNet comparison is not reliable, the cold-item p-values are inflated by pair-level pseudo-replication, the warm significance remains unreproducible from released vectors, the notebook and release docs remain stale, and the source JSON still contains the unresolved Books inconsistency.

The work is promising as a simple EASE+SBERT baseline with a cold-item extension, but it is still not a clean, reproducible, state-of-the-art paper.
