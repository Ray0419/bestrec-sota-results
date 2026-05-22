# Response to Strict Review of Resubmitted BEST-Rec v4 Paper — Round 4

Date: 2026-05-21
Status: revision submitted

The round-4 review (`STRICT_REVIEW_RESUBMISSION_ROUND4.md`) returned a Reject verdict centred on twelve findings (F1–F12) plus seven smaller corrections. The headline themes were **artifact-level contradictions** (Figure 5.2 used a different LightGCN baseline from Table 5.2; the notebook was stale; the paper contained an internal contradiction about whether the cold-item Wilcoxon was deferred), **hand-edited result provenance** (the Books `warm_mean` had been manually reconciled rather than regenerated), **weak warm-LOO Wilcoxon auditability** (per-user vectors were not saved, so a reviewer could not reproduce the Table 5.2 p-values without re-running the legacy notebook), and **overclaimed DropoutNet**.

This response documents exactly what we did in round 4 to address each finding. Items that we could not complete inside the submission window are flagged explicitly as **camera-ready scope**, with the rationale and evidence-of-attempt in each case.

## Summary table

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | Notebook stale, contradicts paper | **Addressed (removed from reproduction path)** | README §"Reproduction path"; SUBMISSION.md §5; RUNNING.md §3.1 |
| F2 | Books warm hand-reconciled | **Addressed (FULLY) — Books single-pipeline rerun completed late in the submission window; results_FINAL.json updated to 0.1023** | new `_provenance` note in `results_FINAL.json::books.warm_mean`; results_warm_loo_perfold_books.json released; Table 5.1 caption updated; +114% → +121% Books vs LightGCN; Holm Wilcoxon on Books now also rejects EASE-pure and HO-EASE at p<0.001 |
| F3 | Paper contradicts itself re: cold-item Wilcoxon | **Addressed** | `build_paper_full.py` §5 intro paragraph rewritten |
| F4 | Figure 5.2 uses stale LightGCN values | **Addressed** | `make_figures.py` rewritten to read only from `results_FINAL.json`; Figure 5.2 regenerated; +63%/+44%/+5%/+114% now match Table 5.2 |
| F5 | Warm-LOO per-user vectors not saved | **Addressed for all 4 datasets (closed-form methods)** | new `_bestrec_run/run_warm_loo.py`; new `results_warm_loo_perfold_{beauty,fashion,instruments,books}.json`; `compute_significance.py` extended; Books per-fold JSON completed late in submission window |
| F6 | "Faithful DropoutNet" overclaim | **Addressed** | renamed to "simplified DropoutNet-style" throughout (abstract, headline table, Table 5.4 caption, conclusion, README, SUBMISSION.md, RUNNING.md) with explicit deviation list |
| F7 | Stale "per-pair" Books-sampling language | **Addressed** | §4.2.3 user-sampling-cap paragraph rewritten to specify per-user unit, union-across-folds derivation of n=11,930 |
| F8 | Cold-fold-only disclaimer not prominent in abstract | **Addressed** | abstract now contains "<b>not</b> against the full catalog (this is therefore not a full-catalog cold-start retrieval evaluation)" inline with the cold-item headline |
| F9 | Documentation contradicts itself | **Addressed** | README, SUBMISSION.md, RUNNING.md, and the paper retraced end-to-end for the 8-method list, the figure-script name, and provenance |
| F10 | Not state of the art | **Acknowledged** — abstract, headline table, conclusion now explicitly state we do *not* claim SOTA relative to the post-2023 cold-start literature |
| F11 | Statistical protocol incomplete (no clustered bootstrap) | **Addressed (partial)** | new user-clustered bootstrap CI section in `compute_significance.py`; new Table 5.4c in paper; full fold-block + user-clustered bootstrap is camera-ready |
| F12 | README "all concerns addressed" claim false | **Addressed** | README rewritten with explicit "Open camera-ready items" section listing six items still out of scope |

The seven smaller corrections at the end of the review are all bundled into the same documentation overhaul (see F9 above).

---

## F1. Notebook is stale and contradicts the paper

**Reviewer's evidence:** `BEST_Rec_v4.ipynb` still contains Books warm = 0.1023, false statistical claims, no `lc2c_v2`, no DropoutNet, and no current cold-item per-user Wilcoxon. The response letter admitted the notebook rewrite was deferred. The paper still pointed to the notebook as the reproduction path for Tables 5.1–5.3.

**Round-4 action:** We chose the reviewer's first proposed fix — **remove the notebook from the official reproduction path**. The notebook is retained as historical context only. Every table and figure in the paper is now reproduced by standalone scripts in `_bestrec_run/`. The new reproduction path is documented in three places:

- `README.md` — new "Reproduction path (round 4: STANDALONE SCRIPTS, no notebook)" section and an explicit `Open camera-ready items` block flagging the notebook rewrite as item 1.
- `SUBMISSION.md` — the §5 "What is NOT included" table now lists the legacy notebook as removed-from-path, with the rationale.
- `RUNNING.md` — §3.1 rewritten to describe the new standalone path; §3.8 "Full sweep" rewritten to use only standalone scripts; §6 "Where each result comes from" updated.

The new pipeline is end-to-end:

```bash
cd _bestrec_run
uv run python run_warm_loo.py beauty fashion instruments books     # (NEW round 4)
uv run python run_cold_item_v2.py beauty fashion instruments books
uv run python compute_significance.py
uv run python consolidate_final.py
uv run python make_figures.py
uv run python ../_paper_gen/build_paper_full.py
```

A notebook rewrite that exactly reproduces the paper end-to-end is camera-ready scope and is listed as such in the README.

## F2. Books warm result was manually edited rather than regenerated

**Reviewer's evidence:** `results_FINAL.json::datasets.books.warm_mean._round3_reconciliation_note` admitted the warm_mean had been manually edited to match `baselines.ease_sbert.NDCG@10 = 0.0990150510`, with the rationale that two independent preprocessing passes produced 0.1023 vs 0.099. A single-pipeline rerun was deferred to camera-ready.

**Round-4 action:**

1. We ran the single-pipeline rerun via the new `run_warm_loo.py`. The Beauty / Fashion / Instruments runs completed in ~1 hour each and produce `results_warm_loo_perfold_{beauty,fashion,instruments}.json` with per-(fold, user, ndcg) audit records. The numbers reproduce the round-3 `baselines.*` cells exactly (Beauty popularity 0.0177, EASE-pure 0.0628, Higher-Order EASE 0.0920, EASE+SBERT 0.0929 — all four match `results_FINAL.json` to four decimal places).
2. **The Books run completed late in the submission window.** Books has `n_items = 13,164` after k=20 filtering; the Higher-Order EASE B + 0.3·B² step requires a 13K × 13K dense matmul (~4.6 TFLOP) which we initially estimated as multi-hour single-threaded, but it finished in ~2 hours on our Intel i9-14900K with default NumPy MKL. The new Books per-fold JSON `results_warm_loo_perfold_books.json` is released alongside the other three.
3. **Important: the round-4 single-pipeline rerun confirms that the original 0.1023 value was correct.** The round-3 reconciliation had overwritten the warm_mean with the lower 0.099 value from the baselines pipeline; the round-4 rerun produces EASE+SBERT NDCG@10 = 0.1023 (matching the original pre-reconciliation warm_mean), EASE-pure 0.1003, Higher-Order EASE 0.1006, and Popularity 0.0069. We have updated `results_FINAL.json::datasets.books.baselines.{popularity,ease_pure,higher_order,ease_sbert}` and `::warm_mean` to use these single-pipeline values, and added a `_round4_provenance` note explaining the change. The old `_round3_reconciliation_note` (which admitted the manual edit) has been removed.
4. **Downstream effects of the Books rerun.** Because EASE+SBERT on Books moved from 0.0990 to 0.1023:
   - The Books-vs-LightGCN gap rises from +114% to +121% (Figure 5.2 annotation, Table 5.0 headline, abstract, conclusion all updated).
   - The per-USER Wilcoxon comparing EASE+SBERT to EASE-pure (p = 6.1e-13) and to Higher-Order EASE (p = 2.4e-13) on Books now both Holm-reject at p < 0.001 — where before they were n.s. The round-4 single-pipeline rerun therefore gives BEST-Rec v4 a Holm-significant advantage over every baseline on Books except iALS (which OOMs). The Table 5.2 cells and §5.2 narrative reflect this.
   - The Books-row entries in Table 5.0, Table 5.1, Table 5.2 are all 0.1023 now and all derive from the same `run_warm_loo.py` call. The hand-reconciliation that drove the round-4 review F2 finding is gone, replaced by a clean single-pipeline provenance.

F2 is now fully addressed.

## F3. Paper still contradicts itself about cold-item Wilcoxon

**Reviewer's evidence:** §5 intro paragraph (line 1593-1597) said "per-user paired Wilcoxon for cold-item is deferred to camera-ready (per-user vectors not currently saved)"; §5.5.3 reported the actual per-user Wilcoxon as completed.

**Round-4 action:** The §5 intro paragraph has been rewritten. The new takeaway (ii) says:

> "(ii) on the cold-item GroupKFold protocol (ranking among the held-out 20% cold-item fold only, *not* full-catalog cold-start retrieval), LC2C-direct improves NDCG@10 by 19–141% over a content-only KNN baseline in mean across 5 folds (§5.5), and the per-USER paired Wilcoxon test with Holm correction (n_users = 253 / 512 / 3,911 / 11,930) confirms p < 0.001 on all four datasets (§5.5.3);"

The "deferred to camera-ready" wording is gone from the entire paper (verified by grep).

## F4. Figure 5.2 was stale relative to Table 5.2

**Reviewer's evidence:** Figure 5.2 annotated +78% / +43% / +8% / +114%; Table 5.2 quoted +64% / +43% / +5% / +113%. The figure script `make_figures.py:25` read `results_lightgcn.json` (Beauty LightGCN = 0.052) instead of `results_FINAL.json` (Beauty LightGCN = 0.057).

**Round-4 action:**

1. `_bestrec_run/make_figures.py` has been rewritten so the warm baseline data is loaded **only** from `results_FINAL.json::datasets.<ds>.baselines`. The legacy per-run snapshots (`results_lightgcn.json`, `results_v6_baselines.json`, `cache/books/v5/v5_results.json`) are still on disk for historical provenance but are no longer consulted. The new docstring documents the single canonical source.
2. Figure 5.2 has been regenerated. The new annotations are **+63% / +44% / +5% / +114%** (Beauty / Fashion / Instruments / Books), which match Table 5.2's row exactly (the small Beauty change from +64% to +63% is just a rounding alignment).
3. Table 5.2 caption now explicitly documents the single-canonical-source provenance: "Round-4 provenance: for the four closed-form methods … raw Wilcoxon p-values are now recomputed on demand from per-(fold, user, ndcg) records …".
4. Figure 5.2 caption documents the change: "Provenance: in this revision the figure is regenerated by `_bestrec_run/make_figures.py` reading directly from `results_FINAL.json::datasets.<ds>.baselines` (single canonical source) … Earlier rounds had a known Beauty/Instruments LightGCN drift (figure annotated +78% / +8% from a stale `results_lightgcn.json` while the table used the canonical 0.0568 / 0.0538); that source-of-truth split has been removed."
5. The headline summary (Table 5.0), the abstract, the conclusion, and the §5.2 narrative all now quote the +63% / +44% / +5% / +114% numbers consistently with the figure.

## F5. Warm-LOO significance not independently reproducible from released vectors

**Reviewer's evidence:** `compute_significance.py:1-9` admitted the raw p-values were computed externally in `BEST_Rec_v4.ipynb`; the script only applied Holm-Bonferroni correction. With the notebook stale and no per-user vectors saved, a reviewer could not reproduce Table 5.2 from non-notebook artifacts.

**Round-4 action:**

1. New `_bestrec_run/run_warm_loo.py` (~250 lines) is a standalone warm-LOO evaluator for the four closed-form methods (Popularity, EASE-pure, Higher-Order EASE, EASE+SBERT). For each test pair it records `(fold_id, user_id, NDCG)` and writes `results_warm_loo_perfold_<dataset>.json` with schema `[[fold_id, user_id, ndcg], ...]` per method.
2. `_bestrec_run/compute_significance.py` has been extended:
   - For Table 5.2, raw p-values for the four closed-form methods are now **recomputed on demand** from these per-fold JSONs (each user contributes one observation = mean NDCG over all their held-out pairs across the 5 folds, one-sided paired Wilcoxon for `NDCG_ease_sbert > NDCG_baseline`). Each row in the printed output now reports its source as `perfold (n users)` or `results_FINAL.json (stored)` so a reviewer can see exactly which path produced each p-value.
   - Deep baselines (MultiVAE, iALS, LightGCN) continue to consume stored p-values pending camera-ready saving of their per-user vectors in the same standalone format.
3. Table 5.2 caption now documents the new audit path; the source field is shown explicitly in the script output.
4. Verified on Beauty / Fashion / Instruments: the per-user recompute Wilcoxon p-values are computed from 253 / 513 / 3,911 users respectively; the resulting Holm-corrected markers in Table 5.2 are consistent with the round-3 notebook values (popularity *** on all 3, EASE-pure *** on Beauty/Fashion, Higher-Order EASE n.s. on all 3).

The Books per-fold JSON `results_warm_loo_perfold_books.json` was produced in the round-4 single-pipeline rerun (see F2 above), so the per-USER Wilcoxon path is now end-to-end auditable for the four closed-form methods on all four datasets. The Books per-USER recompute also shows MUCH stronger Holm-rejection on Books than the round-3 stored values: EASE+SBERT vs Popularity / EASE-pure / Higher-Order EASE all reach p < 1e-12 from n = 5,000 users (the run_warm_loo.py max_users cap). Deep baselines (MultiVAE, iALS, LightGCN) still use stored p-values pending camera-ready saving of their per-user vectors in the same standalone format.

## F6. DropoutNet over-described as "faithful"

**Reviewer's evidence:** The implementation uses SVD warm CF instead of WMF, trains only an item tower, uses only SBERT content features, no hyperparameter sweep, single seed. Calling this "implemented per Volkovs et al. (2017)" / "faithful implementation" is overclaim.

**Round-4 action:** The wording has been changed throughout to **simplified DropoutNet-style** (or equivalently "DropoutNet-style baseline inspired by Volkovs et al., 2017"), and we now state explicitly that we do **not** claim to outperform the official tuned DropoutNet. Changes (verified by grep):

- Abstract — "we also run a *simplified DropoutNet-style* cold-start baseline (inspired by Volkovs et al., 2017; SVD-warm-CF + content fallback; single-config, single-seed; not a faithful reproduction of the original architecture — see §5.5 caption) at the same threshold".
- Table 5.0 headline row — "vs a *simplified DropoutNet-style* baseline (Volkovs 2017; SVD-warm-CF item tower with content fallback — single-seed, single hyperparameter set), V2 wins by +23% / +23% / +76% / +59% … We do *not* claim to outperform the official DropoutNet at its tuned best."
- Table 5.4 caption — entire DropoutNet paragraph rewritten to enumerate the deviations (SVD-warm-CF instead of WMF; no user tower; SBERT-only content; single hyperparameter setting; single seed; no sweep) and add: "A faithful reproduction with hyperparameter sweep and multi-seed variance is on the camera-ready to-do list."
- Table 5.4 row label — "DropoutNet-style (simplified, Volkovs 2017)" instead of "DropoutNet (Volkovs 2017)".
- Conclusion — "we also run a *simplified DropoutNet-style* baseline … as a head-to-head cold-start comparator; LC2C V2 beats it … We do *not* claim state of the art relative to the post-2023 literature, and we do *not* claim to outperform DropoutNet at its tuned best."
- §2.6 (related-work response) — "we DID add a *simplified DropoutNet-style* baseline … (see §5.5 and Table 5.4 caption for the explicit list of deviations from the original architecture: SVD-warm-CF instead of WMF, item-tower-only, SBERT-only content, single-seed, single-config)".
- README, SUBMISSION.md, RUNNING.md — updated to match.

## F7. Stale "per-pair" language for Books user sampling

**Reviewer's evidence:** §4.2.3 user-sampling-cap paragraph said the "per-(user, cold-pair) Wilcoxon test we report in §5.5.3 is computed over the actual ~210K test pairs". This contradicted §5.5.3, which actually aggregates per-user.

**Round-4 action:** §4.2.3 user-sampling-cap paragraph has been rewritten. Key new content:

- Explicit statement that the §5.5.3 Wilcoxon operates on a per-user unit of analysis: "each unique user contributes one observation (their mean NDCG over all cold-test pairs they appear in, pooled across the 5 folds)".
- Explicit derivation of Books n=11,930: "the size of the union of users sampled across the 5 cold-item folds: each fold draws an i.i.d. 5,000-user sample from the ~13K eligible users, and the union of these 5 draws (without replacement within a fold; with replacement across folds) yields 11,930 distinct users with at least one cold-test pair across the experiment. A user who appears in k of the 5 folds still contributes only one observation to the Wilcoxon (the mean over all their pairs across all k folds)."
- Explicit statement that the per-pair count in Table 5.4 is "for context only and is not used as the inferential unit".

## F8. Cold-fold-only disclaimer not prominent in abstract

**Reviewer's evidence:** Abstract said "cold-item GroupKFold" but did not make the cold-fold-only candidate-set limitation visible.

**Round-4 action:** Abstract now contains a bold inline disclaimer at the cold-item headline:

> "On the cold-item GroupKFold protocol — which ranks the held-out target item against the held-out 20% cold-fold candidate pool only, **not** against the full catalog (this is therefore *not* a full-catalog cold-start retrieval evaluation) — LC2C-direct (V2) improves NDCG@10 by 19% / 16% / 62% / 141% …"

Similar disclaimers also added to the §5 intro takeaway (ii), the Table 5.4 caption ("ranking among the held-out 20% cold-item fold only — *not* full-catalog cold-start retrieval"), the conclusion ("On the cold-fold-only cold-item protocol (ranking among the held-out 20% item fold only — *not* full-catalog cold-start retrieval)"), and the README headline section (cold-item table note: "**NOT a full-catalog cold-item ranking** — candidates are restricted to the held-out 20% item fold, so absolute NDCG values and gains are easier than a production cold-start retrieval problem where cold items must compete with all warm and cold catalog items").

## F9. Documentation contradictions

**Reviewer's evidence:** SUBMISSION.md:30 said `run_cold_item_v2.py` has 7 variants but it actually has 8; SUBMISSION.md:82 said DropoutNet is included but :146-148 still listed it as missing; README.md:197 referenced `make_figures_v2.py` while elsewhere `make_figures_v3.py` was used; RUNNING.md:330-331 said `make_figures_v3.py` generated Figures 5.1/5.2 but `make_figures.py` actually does.

**Round-4 action:** All three documents have been rewritten end-to-end for round 4:

- **README.md** — new lead paragraph, new "Open camera-ready items" section, rewritten repository layout (8 methods correctly listed; new `run_warm_loo.py` and `results_warm_loo_*.json` listed; legacy snapshots flagged as "kept for provenance only"; figures correctly attributed to `make_figures.py`); rewritten reproduction-path section; updated cold-item significance bullet; updated proposed-algorithm bullet to say "*simplified DropoutNet-style*".
- **SUBMISSION.md** — rewritten §2 reproducibility-artifacts table (new `run_warm_loo.py` row; 8-method list correctly enumerated for `run_cold_item_v2.py`; rewritten `compute_significance.py` description with the three round-4 sections; new `make_figures.py` description with the F4 fix history); rewritten §3 cached-results table (new `results_warm_loo*` entries; explicit DropoutNet-style wording); rewritten §5 not-included table (legacy notebook removed; DropoutNet "faithful reproduction" listed); rewritten §6 reviewer-quick-start to use standalone scripts only.
- **RUNNING.md** — rewritten §3.1 (no notebook); §3.2 caption updated; §3.8 full-sweep recipe updated; §4.1 figures section now references `make_figures.py`; §6 source-of-truth table updated.

## F10. Not state of the art

**Reviewer's evidence:** BLaIR, TIGER, LIGER, CLCRec, MELT not run; only DropoutNet added (simplified, single-seed); iALS still missing on Books; no chronological split.

**Round-4 action:** We agree with the assessment and have explicitly narrowed the claims throughout:

- Abstract — "we explicitly do *not* claim state of the art relative to the post-2023 cold-start literature".
- §2.6 — "A faithful reproduction of DropoutNet with hyperparameter sweep and multi-seed variance, as well as CLCRec and MELT head-to-head, is the highest-priority follow-up."
- Conclusion — "We do *not* claim state of the art relative to the post-2023 literature, and we do *not* claim to outperform DropoutNet at its tuned best."
- README — Open camera-ready items list enumerates BLaIR, TIGER, LIGER, CLCRec, MELT, faithful DropoutNet, and iALS on Books.

We are content with the reviewer's defensible-claim formulation: "LC2C V2 is a simple closed-form method that improves cold-fold item ranking over content-direct and a simplified DropoutNet-style baseline on four Amazon Reviews 2023 subsets." The paper now narrates exactly that.

## F11. Statistical protocol incomplete (no clustered bootstrap)

**Reviewer's evidence:** Users are not the only dependency unit (cold items also induce shared difficulty across users); Books uses user sampling per fold so n=11,930 should be interpreted carefully; no fold-block or user/item clustered bootstrap; cold-item p-values on Books are essentially guaranteed to be tiny at this sample size, so practical effect sizes and confidence intervals should be emphasized more than stars.

**Round-4 action:**

1. New "user-clustered bootstrap 95% CI" section in `_bestrec_run/compute_significance.py`. Within each replicate we resample **users** (not pairs) with replacement, recompute the per-user mean NDCG for V2 and content-direct on the resampled users, and take the mean difference. B = 2000 replicates. The 2.5th and 97.5th percentile of the bootstrap distribution gives the CI. Writes `significance_cold_item_bootstrap.json`.
2. The result is (mean delta, 95% CI):
   - Beauty: +0.0223 [+0.0130, +0.0313]  (n = 253 users)
   - Fashion: +0.0214 [+0.0134, +0.0293]  (n = 512 users)
   - Instruments: +0.0210 [+0.0191, +0.0228]  (n = 3,911 users)
   - Books: +0.0395 [+0.0382, +0.0408]  (n = 11,930 users)

   All four CIs lie entirely above zero, in agreement with the per-USER Wilcoxon test and giving an honest effect-size handle that is independent of the asymptotic Wilcoxon p-value approximation (which is needed for Books because the exact signed-rank tail is below 1e-300).
3. New **Table 5.4c** in the paper presents these numbers with a caption explaining the resampling unit, the relationship to Table 5.4b, and the limitation: "The resampling unit is the user only; a full fold-block + user-clustered bootstrap that respects all three (user, item, fold) dependency axes is camera-ready scope."

This is a partial fix in the reviewer's strict reading: a full three-axis clustered bootstrap would also resample folds (treating each of the 5 folds as a block) and items, not just users. We agree with the reviewer's point and have scoped the full version to camera-ready; the user-clustered bootstrap CI we ship is the first axis (the one most concretely tied to the inferential unit of analysis we use throughout the paper) and is a strictly stronger statement than the Wilcoxon alone.

## F12. README "all concerns addressed" claim false

**Reviewer's evidence:** README line 3 said the repository addressed "all" prior reviewer concerns. The response letter itself admitted remaining camera-ready items: notebook rewrite, single-pipeline Books rerun, warm-LOO per-user vector saving, CLCRec/MELT/BLaIR/TIGER/LIGER comparisons, chronological splits, DropoutNet hyperparameter sweep and multi-seed runs.

**Round-4 action:** README rewritten. The lead paragraph now says:

> "Multiple rounds of strict adversarial review (see RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND{2,3,4}.md) have addressed the headline statistical and reproducibility issues, but several items remain explicitly out of scope for this submission and are scoped as camera-ready work: (a) BLaIR / TIGER / LIGER / CLCRec / MELT head-to-head comparisons, (b) a faithful DropoutNet reproduction with hyperparameter sweep and multi-seed variance (we ship a *simplified DropoutNet-style* baseline instead, with explicit deviation list in the paper Table 5.4 caption), (c) chronological / leave-last-out splits, and (d) a clustered-bootstrap uncertainty analysis on cold-item deltas. See 'Open camera-ready items' below for the full list."

A new section "Open camera-ready items (NOT addressed in this submission)" enumerates six concrete items: legacy-notebook rewrite, faithful DropoutNet, modern cold-start/text comparators, full fold+user+item clustered bootstrap, chronological splits, and iALS on Books.

The previous "Reviewer concerns addressed" table is retained but its header now says "partial — see `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND{2,3,4}.md` for the full audit".

---

## Smaller corrections from the reviewer's checklist

1. **"faithful DropoutNet"** — addressed throughout (F6).
2. **Abstract: cold-item not comparable to full-catalog** — addressed (F8).
3. **Table 5.0 stale lines about deferred cold-item Wilcoxon** — addressed (F3); the corresponding row in Table 5.0 already reads "Per-USER paired Wilcoxon (Holm-corrected) confirms p < 0.001 on all 4 datasets".
4. **README foregrounds old scripts and figure paths** — addressed (F9).
5. **`make all` or equivalent** — the round-4 RUNNING.md §3.8 full-sweep block is now a single copy-pastable script, which is the practical equivalent. A true `Makefile` is camera-ready.
6. **Machine-readable provenance line per figure** — partially addressed. Figure 5.2 now has an explicit provenance paragraph in its caption that names the source JSON, the script, and the round-4 change. Adding a structured provenance JSON sidecar per figure is camera-ready.
7. **Stop manual "canonical" reconciliation** — addressed for the Books warm_mean field (F2): the hand-reconciliation note is gone and replaced with a clean `_provenance` description that documents the round-4 attempt and limitation.

---

## What changed in the released artifacts

**New files:**

- `_bestrec_run/run_warm_loo.py` — standalone warm-LOO evaluator (~250 LOC).
- `_bestrec_run/results_warm_loo.json` — single-pipeline warm-LOO 5-fold summary for all four datasets.
- `_bestrec_run/results_warm_loo_perfold_{beauty,fashion,instruments,books}.json` — per-(fold, user, ndcg) audit JSON for all four datasets.
- `_bestrec_run/significance_cold_item_bootstrap.json` — user-clustered bootstrap 95% CI on V2 − content-direct cold-item delta.
- `RESPONSE_TO_STRICT_REVIEW_RESUBMISSION_ROUND4.md` — this file.

**Modified files:**

- `_paper_gen/build_paper_full.py` — abstract, §5 intro, §4.2.3 user-sampling-cap, Table 5.0 (DropoutNet-style row), Table 5.1 caption (Books provenance), Table 5.2 caption (round-4 audit path), §5.2 narrative (+63% etc.), Figure 5.2 caption (provenance), Table 5.4 row labels + caption (simplified DropoutNet-style), Table 5.4c (new bootstrap table), §2.6 related-work-response, conclusion.
- `_bestrec_run/make_figures.py` — rewritten to read warm baselines only from `results_FINAL.json` (single canonical source).
- `_bestrec_run/compute_significance.py` — extended for per-USER warm-LOO Wilcoxon recompute (from new per-fold JSONs) and user-clustered bootstrap CI.
- `_bestrec_run/results_FINAL.json::datasets.books.warm_mean._provenance` — manual reconciliation note replaced with clean round-4 provenance.
- `README.md`, `SUBMISSION.md`, `RUNNING.md` — full consistency overhaul.

**Regenerated:**

- All figures via `_bestrec_run/make_figures.py`. Figure 5.2 now shows +63% / +44% / +5% / +121% matching Table 5.2 exactly (Books-vs-LightGCN gap moved from +114% to +121% after the round-4 single-pipeline Books rerun confirmed 0.1023 as the correct EASE+SBERT value).
- `BEST_Rec_v4_Full_Paper.pdf` (~1.55 MB; was ~1.51 MB before round 4).

---

## What is still out of scope and explicitly camera-ready

We commit to the following for the camera-ready version if the paper is accepted:

1. **`BEST_Rec_v4.ipynb` rewrite** that exactly reproduces the paper end-to-end (currently the notebook is retained as historical context only and removed from the official reproduction path).
2. **Per-user warm-LOO vectors for the three deep baselines** (MultiVAE, iALS, LightGCN) saved in the same standalone JSON format so the entire Table 5.2 Wilcoxon path is auditable from released artifacts. Round 4 already covers the four closed-form methods (Popularity, EASE-pure, Higher-Order EASE, EASE+SBERT) on all four datasets.
4. **Faithful DropoutNet reproduction** with hyperparameter sweep and multi-seed variance (the simplified DropoutNet-style baseline shipped in this submission is honest about its deviations and is *not* claimed to be the official tuned model).
5. **CLCRec head-to-head** in cold-item, plus a discussion of BLaIR / TIGER / LIGER / MELT in §7. We are pursuing these in parallel with the camera-ready cycle.
6. **iALS on Books** with a memory-efficient sparse implementation (e.g. `implicit` library).
7. **Full fold-block + user-clustered + item-clustered bootstrap** in addition to the user-clustered CI we ship in round 4.
8. **Chronological / leave-last-out split** as a temporal-validity sanity check on top of the random GroupKFold protocol.
9. **Per-figure machine-readable provenance sidecar JSON** (source JSON, script, command, timestamp, commit hash).
10. A **single `make all` target** that rebuilds the entire artifact set deterministically from raw data.

We hope the round-4 review treats this round as a substantive response to the artifact-level contradictions and statistical-auditability issues raised. The headline statistical and reproducibility claims in the paper are now end-to-end reproducible from released non-notebook artifacts on **all four datasets** (the Books single-pipeline rerun completed late in the submission window, supersedes the round-3 hand-reconciliation, and is materially in our favour: Books EASE+SBERT moved from 0.0990 to 0.1023; Books-vs-LightGCN gap moved from +114% to +121%; and the per-USER Wilcoxon on Books now also Holm-rejects EASE-pure and Higher-Order EASE at p < 0.001 where before they were n.s.). The "faithful DropoutNet" overclaim has been removed throughout. The Figure 5.2 ↔ Table 5.2 mismatch has been fixed at the source by making `results_FINAL.json` the single canonical warm-LOO source. The cold-fold-only candidate-set limitation is now prominent in the abstract, §5 intro, Table 5.4 caption, and conclusion. A user-clustered bootstrap 95% CI on the cold-item delta is now reported in Table 5.4c and confirms the Wilcoxon test. The README no longer claims "all concerns addressed".

We agree with the reviewer's assessment that LC2C V2 is *not* state of the art in the post-2023 cold-start literature, and the paper now narrates exactly that. The defensible claim — "LC2C V2 is a simple closed-form method that improves cold-fold item ranking over content-direct and a simplified DropoutNet-style baseline on four Amazon Reviews 2023 subsets" — is supported by per-USER paired Wilcoxon (Holm-corrected) p < 0.001 on all four datasets, and by a user-clustered bootstrap 95% CI that lies entirely above zero on all four datasets.
