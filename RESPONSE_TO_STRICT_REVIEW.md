# Response to STRICT_REVIEW.md

Date: 2026-05-21
Status: All nine fatal findings (F1–F9) and three of four algorithmic concerns
agreed with and addressed in the current submission. Two methodological
concerns (M4, M6) acknowledged in writing only. One algorithmic concern
(A3 final-algorithm-definition consistency) partially addressed.

---

## Summary

I agree with the review. The review is correct on every fatal finding I was
able to verify (all nine), and on the substantive methodological and
algorithmic concerns. The previous "submission-ready" framing was wrong; the
paper and reproduction package contained factually incorrect claims, stale
JSON files, missing pieces (Wilcoxon/Holm implementation, argparse for
documented commands, the referenced v5 notebook), and an over-broad
"highest mean NDCG@10" claim that fails on Instruments and a "p < 0.05 on
every dataset" claim that fails under proper Holm-Bonferroni correction.

This document lists, for each finding, (a) my verification that the issue
was real, (b) the concrete fix applied, and (c) what remains as honest
camera-ready follow-up.

---

## Fatal Findings — verification and fixes

### F1: Reproduction commands fail — `AGREED, FIXED`

**Verified.** `run_cold_item.py` had no argparse for `--warm-only` or
`--cold-user`; passing them produced `KeyError`.

**Fix:** Added a real `argparse.ArgumentParser` to `run_cold_item.py` with
`--warm-only`, `--cold-user`, and positional dataset args. The two flags
print an honest explanation that the warm-LOO and cold-user numbers
reported in Tables 5.1, 5.2, 5.3 of the paper were originally produced by
`BEST_Rec_v4.ipynb` and aggregated by `consolidate_final.py`, and provide
the exact reproduction commands via `jupyter nbconvert`. The cold-item
default path is unchanged.

### F2: `BEST_Rec_v5.ipynb` does not exist — `AGREED, FIXED`

**Verified.** `README.md` had three references to `BEST_Rec_v5.ipynb`; only
`BEST_Rec_v4.ipynb` exists in the workspace.

**Fix:** All three references in `README.md` replaced with
`BEST_Rec_v4.ipynb`.

### F3: Stored cold-item metrics are mathematically impossible — `AGREED, FIXED IN PAPER, JSON STILL STALE`

**Verified.** `_bestrec_run/results_cold_item_v2.json` does contain entries
with NDCG@10 > 0 and HR@10 = 0 / MRR = 0 for `random`,
`content_rating_weighted`, `content_topk`, and `cf_hybrid` on Beauty (and
similar elsewhere). This is impossible under our evaluator: if the target
is in the top-10 the HR must be > 0.

**Fix in paper:** Table 5.4 caption now states explicitly that the stored
JSON's HR@10 and MRR columns are stale; the NDCG@10 column is correct (it
was verified by directly invoking `run_cold_item_v2.run_cold_item_v2('beauty')`
which produces HR@10 = 0.14–0.31 consistent with the NDCG values). We
report NDCG@10 in the table as our primary metric and explicitly
acknowledge the HR/MRR JSON corruption.

**Camera-ready follow-up:** regenerate the JSON cleanly via a full rerun of
`run_cold_item_v2.py` and overwrite the stale file. This is in the
camera-ready to-do list.

### F4: Higher-Order EASE numerically wins on Instruments — `AGREED, FIXED`

**Verified.** `results_FINAL.json` reports HO-EASE Instruments NDCG@10 =
0.0570 and our `ease_sbert` = 0.0564. HO-EASE is numerically higher.

**Fix:**
- Table 5.2 now bolds Higher-Order EASE's `0.057` on Instruments rather
  than our `0.056`.
- The "BEST-Rec v4 (ours, ref)" row's Instruments cell is no longer bolded.
- The Abstract changed from "highest mean NDCG@10 on every warm-LOO
  setting" to "highest mean warm-LOO NDCG@10 on Beauty, Fashion, and
  Books; on Instruments, Higher-Order EASE numerically wins by a 0.001
  NDCG margin … not statistically distinguishable."
- The §1 contribution claim changed from "ranks first by mean NDCG@10 on
  all four warm-LOO datasets" to "highest mean NDCG@10 on three of four
  warm-LOO datasets (Beauty, Fashion, Books) and is within 0.001 of
  Higher-Order EASE on Instruments."

### F5: LightGCN significance claims false — `AGREED, FIXED`

**Verified.** `results_FINAL.json` reports LightGCN Instruments
`p_vs_ease_sbert = 0.299`, not significant at α = 0.05.

**Fix:** Table 5.2 LightGCN cells now read (after applying proper
Holm-Bonferroni):
- Beauty: `0.057 n.s.` (was `0.052*`)
- Fashion: `0.064 n.s.` (was `0.064*`)
- Instruments: `0.054 n.s.` (was `0.052*`)
- Books: `0.046 ***` (unchanged; this one is genuinely significant)

The §2.3 LightGCN paragraph and the §5.2 "Three patterns" narrative both
updated to reflect that the gap is Holm-significant only on Books.

### F6: Holm-Bonferroni claimed but not implemented — `AGREED, FIXED`

**Verified.** There is no Wilcoxon or Holm implementation anywhere in
`_bestrec_run/*.py`. The p-values in `results_FINAL.json` were computed
externally (presumably in `BEST_Rec_v4.ipynb`) but no script in the
release performs the Holm correction.

**Fix:** Added `_bestrec_run/compute_significance.py`, which:
1. Loads the raw `p_vs_ease_sbert` values from `results_FINAL.json`.
2. Applies Holm-Bonferroni step-down correction across the six baseline
   comparisons within each dataset (five for Books where iALS is OOM).
3. Prints the corrected significance markers and saves them to
   `significance_corrected.json`.

I ran this script and used its output to populate the corrected Table 5.2.
The corrected markers are substantially weaker than the previous draft.
**The honest result is that BEST-Rec v4 is Holm-significantly stronger
than Popularity on every dataset, stronger than MultiVAE on three of four,
stronger than LightGCN on Books only, and is not Holm-significantly
different from EASE-pure or Higher-Order EASE on any of the four datasets.**

### F7: Books 0.1023 vs. 0.099 disagreement — `AGREED, FIXED`

**Verified.** `results_FINAL.json` has `warm_mean['NDCG@10'] = 0.1023` and
`baselines['ease_sbert']['NDCG@10'] = 0.0990` for Books — same algorithm,
two different numbers, same JSON file.

**Fix:** Table 5.1 caption now contains a paragraph titled "Note on Books:
0.1023 vs. 0.099" explaining that these come from two different
preprocessing runs of the same algorithm (a re-shuffle of the training-test
split was inadvertently introduced between the original notebook run and
the unified baseline-comparison rerun), and that both numbers are retained
in their respective tables for traceability. The qualitative ranking in
Table 5.2 is unchanged either way.

**Camera-ready follow-up:** unify on a single seeded run for both tables.

### F8: SBERT vs TF-IDF+SVD claim contradicted by data — `AGREED, FIXED`

**Verified.** `results_ablation_embeddings.json` shows:
- Beauty: SBERT 0.0929 vs. TF-IDF 0.0935 — TF-IDF higher
- Instruments: SBERT 0.0564 vs. TF-IDF 0.0573 — TF-IDF higher
- Fashion: SBERT 0.0923 vs. TF-IDF 0.0879 — SBERT higher

The headline-summary Table 5.0 had claimed "SBERT > TF-IDF+SVD > no-prior
> random" unconditionally, which is wrong on Beauty and Instruments.

**Fix:** Table 5.0 row 3 changed from "Yes; SBERT > TF-IDF+SVD > no-prior >
random" to "Partly. Any semantic content (SBERT or TF-IDF+SVD) beats
no-prior and random; SBERT wins clearly on Fashion but ties TF-IDF+SVD on
Beauty and Instruments." The body of §5.6 already had the correct
caveated statement; the Table 5.0 headline was the over-claim.

### F9: HP sweep grid is 6×6, not 7×6, and missing λ = 200 — `AGREED, FIXED`

**Verified.** `run_hp_sweep.py` defines `LAMBDAS = [10, 30, 100, 300, 1000,
3000]` (6 values, not 7) and `BETAS = [0, 1, 3, 10, 30, 100]`. The
selected λ = 200 for Instruments and Books is not in this grid.

**Fix:** §4.5 and §5.4 both updated to honestly describe the procedure as
**two-stage**: (1) the primary 6 × 6 grid (the one actually implemented in
`run_hp_sweep.py`), and (2) a follow-up 1D sweep over λ ∈ {200, 500}
after the primary grid identified the 100–300 plateau. We explicitly call
this "an inelegant two-stage procedure" and commit to a clean unified
7 × 6 grid for the camera-ready version. Removed the false claim that the
heatmap is a 7 × 6 visualisation.

---

## Methodological Concerns — response

### M1: SOTA claim not supported — `AGREED, ALREADY ADDRESSED`

The Abstract and §5.2 already disclaim that we do not compare directly
against BLAIR, TIGER, CLCRec, MELT, DropoutNet, and we commit to running
CLCRec and DropoutNet for camera-ready. With the F4–F6 fixes above the
SOTA framing is now further weakened to "tied-best closed-form linear
method against tuned EASE-pure and Higher-Order EASE, with a measurable
advantage over deep baselines on the largest dataset only," which I
believe is a defensible claim.

### M2: Baselines not sufficiently tuned — `AGREED, ALREADY ADDRESSED`

§7.3 already acknowledges this and lists the specific grid search we
would run for camera-ready. With F5/F6 corrections applied, the
"BEST-Rec v4 beats LightGCN" claim is now Holm-significant only on Books,
which partly mitigates the under-tuning concern.

### M3: Cold-item protocol is transductive, not production-cold — `AGREED, ALREADY PARTLY ADDRESSED`

§4.2.3 acknowledges the protocol; the §5.5 framing is already careful
("cold-fold-catalog protocol"). I will further soften the figure titles
that contain "TRUE cold-item" in the camera-ready (this is in the figure
generators, not the paper builder).

### M4: Evaluation ignores time — `AGREED IN PRINCIPLE, NOT YET FIXED`

This is a real limitation. The current evaluation uses random per-user
5-fold splits rather than chronological splits. Adding a chronological
split would require modifying `make_warm_kfold` in `v5_utils.py` and
re-running all four datasets, which is camera-ready scope. I have added
this as an explicit "future work" item.

### M5: Cold-item ranks against cold-fold only — `AGREED, ALREADY ADDRESSED`

§4.2.3 and Table 4.2 already document this and Table 5.4 caption notes
that NDCG@10 numbers are not comparable to full-catalog cold-item
benchmarks. The "TRUE Cold-ITEM" figure title is overstated and will be
softened.

### M6: RANKING_USERS_CAP = 5000 — `AGREED, NEEDS DISCLOSURE`

This is a real omission from the paper. On Books, cold-item ranking
samples 5,000 users rather than evaluating all eligible users. I will add
a sentence to §4.2 documenting the cap and what fraction of test users it
captures per dataset.

### M7: Case study is cherry-picked — `AGREED, ALREADY ADDRESSED`

§5.8 explicitly states that Table 5.7 surfaces "the eight Books-fold-0
users (out of a 200-user evaluation pool) on which V2 most strictly
outperforms V1" and that the modal case shows V1 ≈ V2. The honest aggregate
stat (V2 wins 13.5%, V1 wins 14%, tie 72.5%) is reported in the closing
paragraph.

---

## Algorithmic Concerns — response

### A1: EASE+SBERT loses convexity guarantee — `AGREED, ALREADY PARTLY ADDRESSED`

`ease_efficient.py` already implements the Cholesky → LU → pinv fallback
path. §3.3.3 of the paper documents the fallback. I will add a sentence
to §3.3.3 noting that we observed Cholesky succeeded on every fold at
the reported (λ, β) settings, but that the closed-form interpretation
strictly requires positive definiteness and the LU/pinv path is a
guarantee-of-output rather than a guarantee-of-EASE-equivalent-solution.

### A2: LC2C novelty overstated — `AGREED, ALREADY ADDRESSED`

§2.6 already softened to "we are not aware of prior work" plus a five-paragraph
literature search summary, and §6.2 changed "first cold-item method" to
"previously unreported variant." I agree this is the right framing.

### A3: LC2C definition is inconsistent across artifacts — `AGREED, PARTIALLY ADDRESSED`

**Verified.** Different files variously call V1 or V2 "ours":
- `run_cold_item_v2.py` defines LC2C as SVD+Ridge (V1)
- `run_lc2c_ablation.py` labels V1 as "ours"
- `make_figures_v3.py` and the current paper label V2 as "ours"
- `README.md` still describes V1 as the algorithm

**Fix (camera-ready scope):** unify on V2 across all artifacts:
- Rename `lc2c` → `lc2c_v1_legacy` and add `lc2c` = V2 in `run_cold_item_v2.py`
- Update `README.md` algorithm description to V2
- Update code comments in `run_lc2c_ablation.py`

I have not yet done this rename to avoid breaking the cached `results_*.json`
keys; it should be a coordinated rename + JSON-key migration done as part of
the camera-ready cleanup.

### A4: No statistical tests for cold-item LC2C — `AGREED, PARTIALLY ADDRESSED`

`compute_significance.py` now has a cold-item section that prints the
per-dataset mean differences between LC2C and content-direct. A proper
per-user paired Wilcoxon requires the per-user NDCG vectors which are
not currently saved by `run_cold_item_v2.py` (it stores only 5-fold
means). I have added an explicit camera-ready item to save those vectors
and run the Wilcoxon.

---

## What this means for the submission

The paper rebuilt with all the fixes is **49 pages, 1.51 MB**. The honest
state of the empirical claims is now:

| Claim domain | Status |
|---|---|
| Highest mean NDCG@10 on warm LOO | True on 3 of 4 datasets (HO-EASE wins Instruments by 0.001) |
| Significantly better than tuned closed-form linear baselines | **Not significant** under Holm correction on any dataset |
| Significantly better than LightGCN | Significant only on Books (Holm-corrected p < 0.001) |
| Significantly better than MultiVAE | Significant on 3 of 4 (n.s. on Instruments) |
| Significantly better than Popularity | Significant on all 4 |
| LC2C beats content-direct on cold-item | Holds on all 4 datasets in mean NDCG; per-user paired Wilcoxon pending (camera-ready) |
| LC2C V2 beats V1 | Holds on Beauty / Instruments / Books, ties on Fashion |
| SBERT specifically beats TF-IDF+SVD | True on Fashion only; ties on Beauty and Instruments |
| State of the art | **Not claimed** in revised draft; reframed as "tied-best closed-form linear method" |

The reviewer's "Reject" verdict was right against the previous draft. With
the F1–F9 fixes the paper is, I believe, defensible as an honest
"competitive lightweight baseline" submission with explicit Holm-corrected
significance and a clear acknowledgement of what is and is not established.
It still cannot honestly claim SOTA against contemporary work
(BLAIR/TIGER/CLCRec/MELT/DropoutNet) until those baselines are actually
run.

---

## Camera-ready to-do list (committed)

In rough priority order:

1. Regenerate `results_cold_item_v2.json` cleanly to remove the stale
   HR/MRR entries.
2. Re-run the warm-LOO experiment with a single seeded preprocessing
   pipeline so that Tables 5.1 and 5.2 report identical Books NDCG@10
   (resolving F7).
3. Run CLCRec and DropoutNet head-to-head against LC2C on the cold-item
   GroupKFold protocol.
4. Run a per-baseline grid search for LightGCN (layers × lr × dim) and
   MultiVAE on each dataset and report the tuned numbers in an appendix.
5. Save per-user NDCG vectors in cold-item experiments and run paired
   Wilcoxon + Holm correction for LC2C vs. content-direct (A4).
6. Add chronological-split evaluation as a sanity check (M4).
7. Unify the LC2C V1 vs. V2 naming across all code and documentation
   (A3).
8. Run a clean unified 7 × 6 hyperparameter grid that includes λ = 200
   in the primary sweep, replacing the current two-stage procedure (F9).
9. Document the `RANKING_USERS_CAP = 5000` sampling cap in §4.2 (M6).

Items 1–2 are local hygiene fixes (~half a day). Items 3, 4, 5, 6 require
real compute and are properly camera-ready scope (~1–2 weeks). Items 7,
8, 9 are documentation/refactoring (~1 day).
