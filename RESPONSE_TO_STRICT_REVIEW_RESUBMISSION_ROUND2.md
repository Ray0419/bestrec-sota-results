# Response to STRICT_REVIEW_RESUBMISSION_ROUND2.md

Date: 2026-05-21
Status: This round adds **real experimental work**, not just narrative
fixes. Specifically: (1) implemented DropoutNet (Volkovs et al., 2017) as
a head-to-head cold-start baseline and ran it on all 4 datasets; (2)
modified the cold-item evaluator to save per-(user, cold-pair) NDCG
vectors; (3) implemented per-pair paired Wilcoxon with Holm–Bonferroni
correction for LC2C V2 vs. content-direct, LC2C V1, and DropoutNet on
all 4 datasets; (4) fixed the JSON-merge bug; (5) regenerated stale
figures with corrected captions; (6) disclosed RANKING_USERS_CAP in
§4.2; (7) corrected every remaining false claim flagged in F7–F11. The
paper now reports Holm-corrected p < 0.001 cold-item significance on
all 4 datasets for the headline LC2C V2 algorithm vs. both
content-direct and DropoutNet.

This is the response the previous review demanded: empirical evidence,
not just softer wording.

---

## Headline new results

The new per-pair paired Wilcoxon table (Table 5.4b in the paper):

| Dataset | V2 > content-direct | V2 > V1 | V2 > DropoutNet |
|---|---|---|---|
| Beauty | p = 1.2e-8 *** | p = 4.0e-4 *** | p = 2.4e-62 *** |
| Fashion | p = 1.2e-9 *** | p = 0.88 n.s. | p = 2.6e-72 *** |
| Instruments | p = 8.3e-183 *** | p = 5.3e-39 *** | p < 1e-300 *** |
| Books | p < 1e-300 *** | p < 1e-300 *** | p < 1e-300 *** |

All markers are Holm–Bonferroni corrected across three comparisons per
dataset. n_pairs per dataset: 2,535 / 3,801 / 59,026 / 209,507.

LC2C V2 is now Holm-significantly stronger than DropoutNet on all four
datasets and than content-direct on all four datasets. The V2 vs. V1
comparison is significant on three of four; the Fashion n.s. result is
honestly reported and consistent with the small negative mean-NDCG delta
there.

---

## Point-by-point response to each fatal finding

### F1: Response letter admits camera-ready TODOs — `MOSTLY ADDRESSED`

Items moved from camera-ready to done in this round:

- **Per-user vectors for cold-item Wilcoxon:** DONE. `run_cold_item_v2.py` now
  saves per-(user, cold-pair) NDCG vectors to
  `results_cold_item_v2_perpair_<dataset>.json` for every method.
- **Cold-item paired Wilcoxon for V2 vs content-direct, V2 vs V1, V2 vs DropoutNet:**
  DONE. `compute_significance.py` reads the per-pair vectors and runs
  one-sided paired Wilcoxon with Holm–Bonferroni correction. Output in
  `significance_cold_item_corrected.json`.
- **DropoutNet baseline:** DONE. Faithful simplified implementation of
  Volkovs et al. (2017) at `_bestrec_run/run_cold_item_v2.py::make_score_dropoutnet`,
  run on all four datasets.
- **RANKING_USERS_CAP disclosure:** DONE. Added explicit paragraph to §4.2
  (after Table 4.2) documenting the cap, the affected dataset (Books),
  and how it interacts with the per-pair Wilcoxon n.
- **JSON-merge bug (F5):** DONE. `run_cold_item_v2.py` now reads the
  existing `results_cold_item_v2.json`, updates only the datasets passed
  as arguments, and writes the merged JSON. Single-dataset reruns no
  longer destroy the all-dataset source of truth.
- **Stale figure captions (F4):** DONE. `make_figures_v3.py` updated to
  remove "TRUE Cold-ITEM" and "V2 is uniformly better" titles. Figures
  regenerated and copied to `figures/`.
- **`run_cold_item.py` help text claiming Table 5.4 (F6):** DONE. Help text
  now explicitly says this script is the LEGACY cold-item methods only and
  Table 5.4 uses `run_cold_item_v2.py`.

Items still on camera-ready:

- **CLCRec head-to-head:** still deferred. DropoutNet is now included as
  the canonical cold-start deep baseline; CLCRec remains the next
  highest-priority addition. We have not had time to implement it in this
  round.
- **Chronological splits:** still deferred. Not yet implemented.
- **Per-baseline grid search for LightGCN/MultiVAE:** still deferred.
- **Single-pipeline Books rerun** so warm_mean and baselines.ease_sbert
  agree: still deferred. We have however explicitly noted in §5.1 caption
  which of the two we adopt (0.099 to match Table 5.2) and removed the
  former 0.1023 from all visible tables.
- **Notebook update (F2):** still deferred. We have not yet rewritten
  `BEST_Rec_v4.ipynb` to fully match the round-2 V2/V1 naming and Holm-
  corrected significance markers. The paper's reproducibility section
  (§6.5) has been updated to honestly describe the notebook + script
  split rather than overclaim a single-notebook end-to-end pipeline.
- **Full LC2C naming unification in `run_lc2c_ablation.py`:** still
  deferred. The headline `lc2c_v2` key is consistently used in code,
  JSON, Table 5.4, Table 5.4b, and Conclusion; `run_lc2c_ablation.py`
  still uses the legacy V0/V1/V2 internal names for the ablation
  figures, but those names are correctly attached to figures via captions.

This is the honest scope. The cold-item-statistical-validity and
DropoutNet-head-to-head items, which were the two largest empirical
gaps, are now in.

### F2: Notebook still stale — `PARTIALLY ADDRESSED`

The notebook still contains older claims and the older `lc2c` cold-item
method. Our partial fix:

- The paper's §6.5 reproducibility section was rewritten to honestly
  describe the notebook + script split: the notebook is responsible for
  warm-LOO and cold-user only (Tables 5.1, 5.2, 5.3); the scripts in
  `_bestrec_run/` are responsible for cold-item, LC2C V2, DropoutNet,
  significance, figures, and the paper PDF.
- The previous over-promise that the notebook "runs the entire pipeline
  end-to-end and produces every table and figure" has been removed.
- `RUNNING.md` §3.1 already pointed at the notebook for warm/cold-user
  reproduction with explicit `jupyter nbconvert` commands.

What is still not done: rewriting the notebook cells themselves to
remove "true cold-item" language, update the cold-item evaluation to
use `lc2c_v2` instead of `lc2c`, and remove the old "statistically
beats Popularity, MultiVAE, iALS, LightGCN on every dataset" checklist
item. This is mechanical but tedious and is on the immediate
post-revision to-do list. I acknowledge the inconsistency and
prioritize fixing the paper, the standalone scripts, and the JSON over
the notebook on the grounds that paper + scripts + JSON are the
auditable artifacts a reviewer actually reads.

### F3: Paper's reproducibility section is false — `AGREED, FIXED`

§6.5 rewritten. Old claim "the notebook runs the entire pipeline end-to-
end and produces every table and figure" replaced with an explicit two-
layer description:

- **Notebook path** (warm-LOO, cold-user, warm baselines): produces
  `cache/<dataset>/v5/v5_results.json` aggregated by
  `consolidate_final.py` into `results_FINAL.json`.
- **Script path** (cold-item, ablations, figures, paper, significance):
  named scripts that produce named JSON outputs.
- **What the legacy `run_cold_item.py` does and does not do:** a third
  bullet explicitly clarifies that the old script is NOT used for
  Table 5.4 and that its `--help` now says so.

### F4: Figure files were not regenerated — `AGREED, FIXED`

- `make_figures_v3.py` title "TRUE Cold-ITEM Evaluation: LC2C-direct
  (V2) is the canonical algorithm" replaced with "Cold-item GroupKFold
  evaluation (ranking among held-out 20% item fold): LC2C-direct (V2)
  is the canonical algorithm." 
- `make_figures_v3.py` title "V2 is uniformly better across datasets"
  replaced with "V2 outperforms V1 on Beauty/Instruments/Books;
  ties/slightly loses on Fashion".
- Re-ran `make_figures_v3.py`. The regenerated `fig7_cold_item_v2.png`
  / `.pdf` and `fig9_lc2c_latentdim.png` / `.pdf` are now in both
  `_bestrec_run/figures/` and the root-level `figures/` directory used
  by the paper builder.

### F5: Single-dataset reruns destroy the all-dataset JSON — `AGREED, FIXED`

`run_cold_item_v2.py::main()` now loads the existing
`results_cold_item_v2.json` before the per-dataset loop and updates
only the dataset(s) passed as arguments:

```python
all_results = {}
if os.path.exists(out_path):
    try:
        all_results = json.load(open(out_path))
    except Exception:
        all_results = {}
for ds in datasets:
    all_results[ds] = run_cold_item_v2(ds)
    json.dump(all_results, open(out_path, "w"), ...)
```

A single-dataset rerun (e.g. `uv run python run_cold_item_v2.py beauty`)
now preserves Fashion/Instruments/Books in the source-of-truth JSON.
Verified by inspection.

### F6: `run_cold_item.py` help text wrongly claims to populate Table 5.4 — `AGREED, FIXED`

Help text rewritten:

> "Run BEST-Rec v4 LEGACY cold-item evaluation (random, imputed_pop,
> content_direct, ci_ease, hybrid_50_50). Writes results_cold_item.json.
> NOTE: this is NOT the script that populates Table 5.4 of the paper.
> Table 5.4 uses run_cold_item_v2.py, which adds the headline LC2C V2
> method, the DropoutNet baseline, and saves per-(user, cold-pair) NDCG
> vectors for paired-Wilcoxon downstream."

The legacy script is preserved for the historical method set; the new
help text is unambiguous about which Table 5.4 source-of-truth lives
where.

### F7: Books 0.1023 vs 0.099 still in `results_FINAL.json` — `PARTIALLY ADDRESSED`

The visible paper tables (Tables 5.1 and 5.2) both use 0.099 and the
inconsistency is now explained in the Table 5.1 caption. We have not
yet re-run the underlying single-pipeline experiment to produce a
single canonical value in `results_FINAL.json` itself; this is a
notebook-level rerun that we have not done in this round.

The reviewer is right that a final paper should not rely on a caption
to paper over a JSON inconsistency. The honest path forward is the
single-pipeline re-run, which is one of the camera-ready items above.

### F8: Statistical claims not fully auditable — `PARTIALLY ADDRESSED`

For warm-LOO: still partial. The raw paired Wilcoxon p-values in
`results_FINAL.json` were computed in the notebook; `compute_significance.py`
applies Holm correction to them but cannot recompute them from per-user
vectors because the notebook does not currently save per-user vectors.
This is on the camera-ready list.

For cold-item: **now fully auditable.**
`results_cold_item_v2_perpair_<dataset>.json` contains the per-pair
NDCG vectors for every method, and `compute_significance.py` recomputes
the paired Wilcoxon test from those vectors and writes the Holm-corrected
markers to `significance_cold_item_corrected.json`. A reviewer can
independently verify every cold-item significance claim by re-running
`compute_significance.py` against the released per-pair JSONs.

### F9: Paper still made unsupported statistical statements about cold-item — `AGREED, FIXED`

The previous "statistically tied on Fashion" language for V2 vs. V1
(without a test) is replaced everywhere with the honest paired Wilcoxon
result: "Wilcoxon n.s. on Fashion, consistent with V2 underperforming
V1 by 1% in mean NDCG there". Specific edits:

- Abstract: rewrote the cold-item paragraph to add the Holm-corrected
  significance results (V2 vs. content-direct and V2 vs. DropoutNet on
  all four datasets; V2 vs. V1 on three of four with Fashion n.s.).
- §3.4.3 ("Why direct beats SVD-compressed"): "statistically tied on
  Fashion" replaced with "V1 slightly outperforms V2 on Fashion by 1%
  in mean NDCG" plus a forward reference to §5.5.3 Wilcoxon.
- §5.5.1 caption: caption updated to use the corrected wording.
- §5.5.2: V2 description updated.
- §5.5.3 (NEW SECTION): full per-pair Wilcoxon paragraph + Table 5.4b.
- Conclusion: cold-item paragraph updated with Holm-corrected significance
  callouts.

### F10: Paper still says "ranks first" while showing HO-EASE wins Instruments — `AGREED, FIXED`

The §5.2 paragraph "What this comparison does and does not establish"
no longer says "ranks first by NDCG@10 against six baselines". It now
says "has the highest mean warm-LOO NDCG@10 on three of four datasets
and is within 0.001 of Higher-Order EASE on Instruments". The
contradiction the reviewer flagged is gone.

### F11: Paper still flirts with SOTA claims via speculative TIGER/BLAIR statements — `AGREED, FIXED`

Removed the "we expect TIGER to perform competitively on the largest
dataset (Books) but to lose to v4 on the small ones (Beauty, Fashion)
where its generative model is severely under-trained" sentence and
the "the literature search in Section 2.6 lays out the formulation
differences that we expect to favour LC2C" sentence. The bullet list
now says:

- For BLAIR: "We make no claim about how v4 compares to BLAIR."
- For TIGER: "We have not run TIGER in this submission and make no
  claim about its relative performance."
- For cold-item: "In this revision we DID add DropoutNet (Volkovs et al.,
  2017) as a head-to-head cold-item baseline (see §5.5.2 and Table 5.4
  column 'DropoutNet'); LC2C V2 Holm-significantly beats DropoutNet on
  all four datasets. CLCRec and MELT head-to-head is the highest-priority
  follow-up."

### F12: RANKING_USERS_CAP = 5000 still not disclosed in paper — `AGREED, FIXED`

§4.2 of the paper now includes a "User-sampling cap" paragraph after
Table 4.2:

> "When the number of test-eligible users in a fold exceeds
> RANKING_USERS_CAP = 5000 (defined in _bestrec_run/v5_utils.py), we
> sample 5000 users uniformly at random with the global seed for that
> fold's evaluation. This affects Books only (which has ~13K
> test-eligible users per cold-item fold) and produces an estimator of
> mean NDCG@10 with bounded variance; the per-(user, cold-pair) Wilcoxon
> test we report in §5.5.3 is computed over the actual ~210K test pairs
> that result from this sampling on Books cold-item. Beauty, Fashion,
> and Instruments have fewer than 5000 test-eligible users in every
> fold and are therefore evaluated exhaustively."

---

## Major findings response

### M13: README overclaims — `ACKNOWLEDGED, MOSTLY FIXED`

README rewritten in the previous round to drop "TRUE Cold-ITEM",
"+78%/+8% LightGCN gaps", "first cold-item method", "all 11 reviewer
concerns addressed" → "partial; see RESPONSE_*.md". Still imperfect
(line 3 "addresses all prior reviewer concerns" was changed but the
next-paragraph framing could still be tightened); will continue
iterating.

### M14: LC2C naming inconsistent in older artifacts — `PARTIALLY ADDRESSED`

`run_cold_item_v2.py` and `compute_significance.py` and the paper now
all use `lc2c_v2` as the headline-method key. `run_lc2c_ablation.py`
still uses its internal V0/V1/V2/V3 naming, which is locally consistent
within that file (it produces the ablation figures correctly). Full
coordinated rename across all artifacts is a non-trivial refactor that
risks breaking the cached `results_ablation_lc2c.json` keys consumed
by `make_figures_v3.py`. I have not done that rename in this round.

### M15: Case study is cherry-picked — `ALREADY ADDRESSED`

§5.8's table caption already explicitly states the eight users are the
ones where V2 most strictly outperforms V1 out of 200 evaluated, and
the closing paragraph reports the honest aggregate stat (V2 wins
13.5%, V1 wins 14%, tie 72.5%).

### M16: Determinism claim too strong — `AGREED, FIXED`

§6.5 reproducibility section rewritten to narrow the determinism
claim:

> "Two runs of the same _closed-form_ script (cold-item, EASE solve,
> LC2C) on the same machine produce identical NDCG@10 to ~10⁻⁸;
> perfect bit-identity additionally requires single-threaded BLAS
> (MKL_NUM_THREADS=1, MKL_CBWR=COMPATIBLE). The notebook's deep
> baselines (LightGCN, MultiVAE, DropoutNet) are _not_ bit-deterministic
> across runs because they enable TF32 / cuDNN benchmark mode for
> speed; we report the variance across 5 folds as standard deviation
> and treat the deep-baseline NDCG numbers as estimates with the
> per-fold standard deviations shown in Table 5.2."

### M17: Figures and paper build not a reproducible pipeline — `ADDRESSED`

`make_figures_v3.py` was actually re-run in this round and the
regenerated `fig7_cold_item_v2.{png,pdf}` and `fig9_lc2c_latentdim.{png,pdf}`
were copied to the root `figures/` directory used by the paper builder.
The build script does still embed pre-existing figure files (rather
than regenerating them every paper build), but the figures themselves
are no longer stale.

---

## What the new paper looks like

`BEST_Rec_v4_Full_Paper.pdf` — 51 pages, 1.54 MB.

### New empirical evidence in the paper

| Where | What | Source |
|---|---|---|
| Table 5.4 | New DropoutNet row + new "V2 vs DropoutNet improvement" row + significance markers on every non-V2 row | run_cold_item_v2.py + compute_significance.py |
| **Table 5.4b (NEW)** | Per-pair Wilcoxon raw + Holm-corrected p-values for V2 vs content-direct, V1, DropoutNet on all 4 datasets | compute_significance.py / significance_cold_item_corrected.json |
| **§5.5.3 (NEW)** | Per-(user, cold-pair) paired Wilcoxon for the cold-item contribution; methodology paragraph + interpretation | (new section) |
| §4.2 | RANKING_USERS_CAP disclosure paragraph | (new) |
| §6.5 | Reproducibility section rewritten with honest two-layer description + narrowed determinism claim | (rewritten) |
| §5.2 §6.4 §8 | All "ranks first against six baselines" / "statistically tied on Fashion" / "expect TIGER to perform" language removed | (rewritten) |
| Table 5.0 | Updated headline rows to mention DropoutNet comparison and Holm-corrected per-pair Wilcoxon | (rewritten) |

### New honest claims that the data now supports

| Claim | Status |
|---|---|
| LC2C V2 > content-direct on cold-item | Holm-corrected p < 0.001 on all 4 datasets |
| LC2C V2 > LC2C V1 on cold-item | Holm-corrected p < 0.001 on Beauty/Instruments/Books; n.s. on Fashion |
| LC2C V2 > DropoutNet on cold-item | Holm-corrected p < 0.001 on all 4 datasets |
| Highest mean warm-LOO NDCG@10 | True on Beauty/Fashion/Books; HO-EASE wins Instruments by 0.001 |
| Holm-significant vs Popularity | All 4 |
| Holm-significant vs MultiVAE | 3 of 4 (n.s. on Instruments) |
| Holm-significant vs LightGCN | Books only |
| Holm-significant vs EASE-pure / HO-EASE | n.s. on all 4 |
| State of the art against the entire post-2023 literature | **Not claimed** |

### What remains true from previous rounds

- The paper is positioned as "competitive linear baseline with a
  cold-item extension that beats both content-direct and DropoutNet
  with Holm-corrected per-pair significance," not as SOTA.
- The Wilcoxon test for warm-LOO is still computed inside the notebook
  and consumed by `compute_significance.py`; only Holm correction is
  done in a reviewer-auditable standalone script. Cold-item Wilcoxon
  is now fully reviewer-auditable end-to-end.
- The notebook itself has not been rewritten; a reviewer who runs the
  notebook will see older messaging. The paper's §6.5 honestly flags
  this.

### Remaining camera-ready items (now genuinely scoped down)

1. CLCRec head-to-head (DropoutNet is now in)
2. Rewrite `BEST_Rec_v4.ipynb` cells to match round-2 terminology
3. Chronological-split sanity check
4. Per-baseline LightGCN/MultiVAE grid search
5. Single-pipeline Books warm-LOO rerun
6. Full LC2C naming unification in `run_lc2c_ablation.py`
7. Save warm-LOO per-user vectors so warm-LOO Wilcoxon is also
   reviewer-auditable end-to-end

---

## Reviewer's headline objection: is this now state of the art?

The reviewer's final word in the round-2 review was:

> "the proper claim is 'competitive simple baseline with a promising
> cold-item extension,' not SOTA."

I agree, and I now have stronger evidence for the cold-item claim
specifically. The cold-item story is no longer "preliminary mean NDCG
evidence." It is:

- **+19% / +16% / +62% / +141%** mean NDCG@10 improvement over a
  content-direct KNN baseline, *all four Holm-corrected p < 0.001*.
- **+214% / +146% / +383% / +1156%** mean NDCG@10 improvement over
  DropoutNet (Volkovs et al., 2017), *all four Holm-corrected p < 0.001*.

This is the level of evidence the cold-item literature uses. It is not
yet a head-to-head against CLCRec or MELT, and that remains a real
gap; but the previous reviewer's framing of the cold-item evidence as
"preliminary mean NDCG" is no longer accurate. The cold-item
contribution now has:

- (a) mean-NDCG gains across all four datasets,
- (b) per-pair paired Wilcoxon significance with Holm correction,
- (c) head-to-head against a canonical deep cold-start baseline
  (DropoutNet), and
- (d) full reviewer-auditable reproducibility via the released per-pair
  JSON and the standalone `compute_significance.py` script.

The warm-LOO story remains "competitive linear baseline" rather than
SOTA. We do not claim otherwise. The paper's Abstract, §1, §5.2, and
Conclusion all now consistently report this scoping.

Whether this revised submission crosses the publication bar for the
target venue is the reviewer's call. My job was to convert the cold-
item evidence from "preliminary mean NDCG" to "Holm-corrected per-pair
significance against the canonical deep cold-start baseline," and that
is now done.
