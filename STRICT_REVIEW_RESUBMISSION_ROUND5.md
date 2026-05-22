# Strict Review of Resubmitted BEST-Rec v4 Paper - Round 5

Date reviewed: 2026-05-21  
Reviewer stance: adversarial, strict, looking for any remaining reason not to pass.

## Verdict

**Reject / do not pass in its current form.**

This round contains real improvements: Figure 5.2 was regenerated from the canonical warm baseline values, the DropoutNet wording is much more honest, cold-item per-user testing is still reproducible, and the new warm-LOO per-user JSONs are a useful addition. However, the resubmission still fails a strict audit. The most serious new problem is that the paper's Table 5.2 no longer matches the output of its own updated significance script. In addition, the claimed standalone reproduction path is broken: `run_warm_loo.py` does not update `results_FINAL.json`, while `consolidate_final.py` still reads old notebook/cache artifacts and would overwrite the new round-4 Books fixes if followed as documented.

The paper is still not state of the art. The authors now admit this in some places, but the experimental package still does not compare against current text-augmented, cold-start, or generative retrieval recommenders.

## What I Checked

I inspected the new round-4 response letter, paper generator, documentation, result JSONs, scripts, and figures. I reran:

```powershell
uv run python compute_significance.py
```

I also checked:

- `results_FINAL.json`
- `results_warm_loo.json`
- `results_warm_loo_perfold_{beauty,fashion,instruments,books}.json`
- `significance_corrected.json`
- `significance_cold_item_corrected.json`
- `significance_cold_item_bootstrap.json`
- `run_warm_loo.py`
- `consolidate_final.py`
- `make_figures.py`
- `build_paper_full.py`
- `README.md`, `RUNNING.md`, and `SUBMISSION.md`
- the current `figures/fig2_vs_lightgcn.png`

For current SOTA context I checked these primary sources:

- BLaIR / Amazon Reviews 2023 benchmark, ACL 2026 revision: https://arxiv.org/abs/2403.03952
- TIGER / generative retrieval recommendation: https://arxiv.org/abs/2305.05065
- LIGER / hybrid generative and dense retrieval: https://arxiv.org/abs/2411.18814
- Purely Semantic Indexing for LLM-based generative recommendation and retrieval: https://arxiv.org/abs/2509.16446
- DIGER / differentiable semantic IDs for generative recommendation, SIGIR 2026: https://arxiv.org/abs/2601.19711
- CLCRec: https://arxiv.org/abs/2107.05315
- MELT: https://arxiv.org/abs/2304.08382
- DropoutNet: https://papers.nips.cc/paper/7081-dropoutnet-addressing-cold-start-in-recommender-systems

## Improvements Since Round 4

Several changes are genuinely positive.

1. **Figure 5.2 is now regenerated from `results_FINAL.json`.**  
   The current `figures/fig2_vs_lightgcn.png` shows +63% / +44% / +5% / +121%, matching the current canonical warm values. The old stale +78% / +8% issue is fixed.

2. **DropoutNet wording is substantially more honest.**  
   The paper now calls it a "simplified DropoutNet-style" baseline and explicitly admits it is not a faithful reproduction of the official DropoutNet architecture.

3. **Cold-item per-user Wilcoxon remains reproducible.**  
   `compute_significance.py` still recomputes cold-item Wilcoxon from `results_cold_item_v2_perpair_<dataset>.json`.

4. **Warm closed-form per-user JSONs now exist.**  
   The new `results_warm_loo_perfold_<dataset>.json` files provide auditable records for the closed-form warm methods.

5. **A user-clustered cold-item bootstrap was added.**  
   This is not a full clustered bootstrap, but it is a useful uncertainty check.

These fixes do not overcome the remaining fatal issues.

## Fatal and Major Findings

### F1. Table 5.2 is wrong relative to the paper's own significance script.

This is the most serious new failure.

Running `_bestrec_run/compute_significance.py` produces these warm-LOO corrected markers:

- Beauty EASE-pure: `***`, p = 8.484e-06 (`significance_corrected.json:8-11`)
- Fashion EASE-pure: `***`, p = 2.108e-04 (`significance_corrected.json:45-48`)
- Books EASE-pure: `***`, p = 6.138e-13 (`significance_corrected.json:119-122`)
- Books Higher-Order EASE: `***`, p = 2.411e-13 (`significance_corrected.json:114-117`)

But the paper hardcodes Table 5.2 as:

- Beauty EASE-pure: `0.063 n.s.`
- Fashion EASE-pure: `0.076 n.s.`
- Instruments EASE-pure: `0.055 n.s.`
- Books EASE-pure: `0.100 ***`

See `_paper_gen/build_paper_full.py:1751`.

The paper caption says the closed-form p-values are now recomputed from `results_warm_loo_perfold_<dataset>.json`, but the displayed table does not use those recomputed values. This is an internal contradiction between the script, the JSON output, and the PDF source. A reviewer cannot accept a paper whose main statistical table is already stale relative to its own recomputation script.

Required fix: regenerate Table 5.2 directly from `significance_corrected.json`, or at minimum update the hardcoded table to match the script output. Then rerun the PDF and verify every narrative statement that depends on Table 5.2.

### F2. The narrative around EASE-pure and Higher-Order EASE is now inconsistent.

The paper says:

- Figure 5.1 caption: "the only baseline that is not significantly worse is Higher-Order EASE (n.s. on Beauty/Fashion/Instruments)" (`_paper_gen/build_paper_full.py:1793-1796`).
- Section 5.2 narrative: the comparison with EASE-pure and Higher-Order EASE is significant on Books but not on the three smaller datasets (`_paper_gen/build_paper_full.py:1814-1816`).

But `compute_significance.py` says EASE-pure is significant on Beauty and Fashion too. Therefore either the updated script is wrong, or the paper narrative is wrong. The submission does not resolve this.

Required fix: decide which statistical protocol is authoritative, explain why it changed from the prior version, and make the table, captions, JSON, and prose all agree.

### F3. The documented reproduction path is broken and can overwrite the new round-4 fixes.

The response claims the notebook was removed and every table/figure is now reproducible by standalone scripts. The documented pipeline includes:

```bash
uv run python run_warm_loo.py beauty fashion instruments books
uv run python compute_significance.py
uv run python consolidate_final.py
uv run python make_figures.py
```

But this does not work as claimed.

`run_warm_loo.py` writes only:

- `results_warm_loo.json`
- `results_warm_loo_perfold_<dataset>.json`

It does **not** update `results_FINAL.json`, despite its own docstring saying Books `results_FINAL.json` is updated (`_bestrec_run/run_warm_loo.py:24-28`, `_bestrec_run/run_warm_loo.py:229-248`).

`consolidate_final.py` is still the old script. It reads:

- `cache/<dataset>/v5/v5_results.json` (`_bestrec_run/consolidate_final.py:19`)

and writes:

- `_bestrec_run/results_FINAL.json` (`_bestrec_run/consolidate_final.py:49`)

It does not read `results_warm_loo.json` or the new per-fold JSONs. Worse, `cache/books/v5/v5_results.json` still contains the old Books baseline cells:

- `baselines.ease_sbert.NDCG@10 = 0.099015...` (`cache/books/v5/v5_results.json:123`)
- old EASE-pure and Higher-Order p-values (`cache/books/v5/v5_results.json:120`, `cache/books/v5/v5_results.json:133`)

So following the documented reproduction path can destroy the new `results_FINAL.json` round-4 state and reintroduce the old inconsistency. This is a fatal reproducibility bug.

Required fix: rewrite `consolidate_final.py` so it consumes `results_warm_loo.json`, `results_warm_loo_perfold_<dataset>.json`, and the current deep-baseline/cold-user sources explicitly. Add a noninteractive test that runs the documented pipeline and diffs the regenerated `results_FINAL.json` against the submitted one.

### F4. The paper still says to use the notebook, despite claiming it was removed.

The response says the notebook has been removed from the official reproduction path. Some documentation says this too. But the paper still contains old notebook instructions:

- `_paper_gen/build_paper_full.py:2483-2495`: says the reproduction surface is split between a notebook for warm-LOO, cold-user, and warm baselines, and scripts for cold-item.
- `_paper_gen/build_paper_full.py:2490`: explicitly labels a "Notebook path (warm-LOO, cold-user, warm baselines)".
- `_paper_gen/build_paper_full.py:2712`: tells researchers to set `DATASET` in the notebook config cell and run all cells.

`RUNNING.md` also still contradicts itself:

- `RUNNING.md:156-175`: says no notebook is required.
- `RUNNING.md:313-316`: the quick start still says to run `make_figures_v3.py` and says the notebook path is needed for warm-LOO + cold-user numbers.

The notebook itself remains stale:

- `BEST_Rec_v4.ipynb:1437` still claims the method statistically beats Popularity, MultiVAE, iALS, and LightGCN on every dataset.
- `BEST_Rec_v4.ipynb:1782` still contains the old "TRUE Cold-ITEM" section.
- It still has no `lc2c_v2` or DropoutNet.

If the paper still points to the notebook, the notebook remains part of the submission. Therefore F1 from the previous round is not actually closed.

### F5. The claimed standalone pipeline still does not reproduce every table.

The new standalone warm script covers only four closed-form methods:

- Popularity
- EASE-pure
- Higher-Order EASE
- EASE+SBERT

It does not reproduce:

- MultiVAE
- iALS
- LightGCN
- cold-user Table 5.3
- rating prediction metrics in Table 5.1
- deep-baseline per-user vectors

The paper and submission documents still call `results_FINAL.json` the single canonical source of truth for Tables 5.1-5.3, but much of that file is still inherited from the old notebook/cache pipeline. `RUNNING.md:328` even references `run_cold_user.py`, but no such file exists in `_bestrec_run`.

This is not a clean notebook-free reproduction path. It is a hybrid of new scripts, old cache outputs, hardcoded PDF values, and manually updated JSON fields.

Required fix: either truly implement all missing standalone scripts or stop claiming that the notebook was removed from the reproduction path.

### F6. Warm-LOO Books is silently sampled to 5,000 users, but the paper presents it as the full 14,407-user Books dataset.

`run_warm_loo.py` caps evaluated users at 5,000:

- `_bestrec_run/run_warm_loo.py:57`
- `_bestrec_run/run_warm_loo.py:75-77`

The submitted `results_warm_loo_perfold_books.json` has:

- 25,000 records total
- 5,000 unique users
- 5,000 evaluated records per fold

But the paper and README present Books as a 14,407-user warm-LOO dataset (`README.md:14`, `_paper_gen/build_paper_full.py:1370`). The user-sampling discussion in the paper is limited to the cold-item protocol (`_paper_gen/build_paper_full.py:1440-1456`) and does not disclose that the new warm-LOO Books recomputation also uses a cap.

This matters because the new round-4 Books result and Books p-values are being used as headline evidence. If only 5,000 users are evaluated, the paper must say so in Table 5.1, Table 5.2, and the statistical section.

Required fix: either evaluate all 14,407 Books users for warm-LOO or prominently disclose the 5,000-user cap and report sensitivity to different user samples.

### F7. Table 4.2 test-set sizes are wrong relative to the new warm per-fold JSONs.

The paper's Table 4.2 says warm-LOO test pairs per fold are approximately:

- Beauty: ~50
- Fashion: ~75
- Instruments: ~780
- Books: ~3,000

See `_paper_gen/build_paper_full.py:1468-1473`.

But `results_warm_loo.json` reports the actual `ease_sbert` evaluated pairs per fold as:

- Beauty: 253 / 253 / 253 / 253 / 253
- Fashion: 513 / 513 / 513 / 513 / 341
- Instruments: 3911 / 3911 / 3911 / 3911 / 3911
- Books: 5000 / 5000 / 5000 / 5000 / 5000

The test-set-size table is therefore not describing the new reproduction artifacts. This is not cosmetic; it changes the reader's interpretation of the evaluation protocol and statistical sample size.

Required fix: regenerate Table 4.2 from the actual split/evaluation records, not from a hand estimate.

### F8. `build_paper_full.py` still hardcodes main empirical tables rather than reading source JSONs.

Despite repeated "single source of truth" claims, the paper generator does not load `results_FINAL.json`, `significance_corrected.json`, or `results_warm_loo.json` to build the main tables. For example, Table 5.2 is a hardcoded Python list in `_paper_gen/build_paper_full.py:1745-1754`.

This is exactly how the new mismatch happened: `compute_significance.py` was updated, `significance_corrected.json` was updated, but the paper table stayed stale.

Required fix: the paper build must load the same JSON artifacts that the scripts write. Hardcoded result tables should be removed.

### F9. The response letter contradicts itself on the new Figure 5.2 values.

`RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND4.md:17` says Figure 5.2 was regenerated as:

- +63% / +44% / +5% / +114%

But later:

- `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND4.md:65` says Books rises to +121%.
- `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND4.md:229` says Figure 5.2 shows +63% / +44% / +5% / +121%.

The actual figure shows +121%, so the response summary table is stale. This is a smaller issue than the Table 5.2 mismatch, but it is another sign that the artifact set was patched without a final consistency pass.

### F10. The cold-item bootstrap uses a different estimand than Table 5.4 and should be clearer.

`compute_significance.py` reports bootstrap per-user means:

- Beauty V2 mean = 0.1695, content mean = 0.1472

Table 5.4 reports fold means:

- Beauty V2 = 0.1731, content-direct = 0.1449

These are not identical because one is per-user aggregated and the other is fold/pair weighted. The bootstrap is useful, but the paper should explicitly explain that Table 5.4 and Table 5.4c use different weighting schemes. Otherwise readers may think the bootstrap table is a confidence interval around the exact Table 5.4 mean difference.

### F11. Deep baselines remain weakly auditable.

The authors now honestly state that MultiVAE, iALS, and LightGCN still use stored p-values from the prior pipeline. That is better than hiding it, but the result remains a limitation:

- no released per-user vectors for deep baselines
- no full standalone rerun
- no per-dataset hyperparameter grid
- no multi-seed variance
- iALS still missing on Books

The warm-LOO statistical story is therefore only partially auditable. It is not "end-to-end reproducible from released non-notebook artifacts" as claimed in `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND4.md:248`.

### F12. The paper is still not state of the art.

The authors now mostly acknowledge this, but the answer to "is it state of the art?" remains no.

As of this review date, relevant missing comparators include:

- BLaIR, now revised for ACL 2026 and explicitly benchmarked on Amazon Reviews 2023 semantic encoders.
- TIGER, a semantic-ID generative retrieval recommender with cold-item generalization claims.
- LIGER, a 2024 hybrid generative/dense retrieval method that explicitly discusses cold-start item recommendation.
- Purely Semantic Indexing, a 2025 LLM-based generative recommendation/retrieval method that reports cold-start improvements.
- DIGER, a SIGIR 2026 differentiable semantic-ID recommendation method.
- CLCRec and MELT, both directly relevant to cold-start/long-tail recommendation.

The paper does not run these. It also does not run a faithful tuned DropoutNet, does not run iALS on Books, and does not run chronological splits. The defensible claim remains narrow: LC2C V2 improves a cold-fold-only candidate-set task over content-direct and a simplified DropoutNet-style baseline. It is not SOTA.

## Additional Smaller Issues

1. `SUBMISSION.md:156-158` still says the SOTA disclaimer names DropoutNet as a missing comparison, even though the rest of the package says a simplified DropoutNet-style baseline is included.
2. `RUNNING.md:313` still tells users to run `make_figures_v3.py` in the quick start, while the new canonical figure builder is supposedly `make_figures.py`.
3. `RUNNING.md:328` references `run_cold_user.py`, which does not exist.
4. `figures/fig2_vs_lightgcn.png` now has the correct values, but the +63% Beauty label overlaps the legend and is hard to read.
5. `run_warm_loo.py` docstring claims it updates `results_FINAL.json`; it does not.
6. The paper still says "Total notebook execution time" in Table 5.6 discussion (`_paper_gen/build_paper_full.py:2212`) despite the "no notebook" claim.

## Algorithmic Assessment

LC2C V2 remains a reasonable and interesting closed-form idea. The cold-item evidence is stronger than it was two rounds ago because the per-user Wilcoxon and the user-clustered bootstrap both support the content-direct delta. The simplified DropoutNet-style baseline is no longer misrepresented as a faithful reproduction.

But the experimental package is still not coherent enough for acceptance. The warm significance results changed, the table did not; the reproduction instructions invoke a stale consolidator; the paper still points to the notebook; Books warm evaluation silently caps users; and key deep baselines remain non-auditable.

## Required Changes Before Reconsideration

1. Make `build_paper_full.py` load tables directly from JSON outputs instead of hardcoding empirical cells.
2. Regenerate Table 5.2 from `significance_corrected.json` and make the prose agree.
3. Rewrite `consolidate_final.py` so the documented pipeline reproduces the submitted `results_FINAL.json`.
4. Remove all notebook reproduction instructions from the paper, or update the notebook so it actually matches.
5. Disclose or remove the 5,000-user warm Books cap.
6. Regenerate Table 4.2 from actual split/evaluation records.
7. Provide per-user vectors for MultiVAE, iALS, and LightGCN or clearly mark their p-values as legacy/non-auditable.
8. Add a real cold-user standalone script or stop claiming Table 5.3 is standalone reproducible.
9. Run at least CLCRec plus one modern semantic/generative recommender comparator before making any broad competitiveness claim.
10. Run the entire documented reproduction path in a clean directory and include a manifest proving every submitted table/figure comes from the generated artifacts.

## Final Recommendation

Reject. This is a substantive revision, but not a passable one. The new warm-LOO audit files are useful, yet they expose a fresh inconsistency between the updated significance script and the paper's main table. The standalone reproduction path is still partly fictional, and the paper remains below the evidentiary standard required for a SOTA or strong empirical claim.
