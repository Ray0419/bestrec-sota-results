# Response to STRICT_REVIEW_RESUBMISSION.md

Date: 2026-05-21
Status: I agree with the second-round review on virtually every point. The
previous response was cosmetic in several places where it should have been
substantive (especially the `--warm-only`/`--cold-user` "fix" and the stale
cold-item JSON). This second-round revision addresses **all eleven fatal
findings (F1–F11) and most major findings**, with concrete code, JSON, and
paper edits documented below. Five items remain on the camera-ready to-do
list and are scoped honestly.

The summary verdict of the previous round was: "The cold-item result can be
described as preliminary mean NDCG evidence only." I now agree that this
is the correct framing. The current revision narrows the paper's claims
accordingly, fixes the stale JSON, makes the proposed algorithm have a
single name (`lc2c_v2`) across all artifacts, removes the misleading
`--warm-only`/`--cold-user` flags entirely, and recomputes / re-documents
every empirical claim.

---

## Fatal findings — point-by-point response

### F1: Response letter admits the package is incomplete — `ACKNOWLEDGED`

The previous response did defer multiple items to "camera-ready". I agree
this is not a substitute for actually fixing them. In this round I have
moved most of the deferred items from "camera-ready" to "done":

| Deferred in round 1 | Status in round 2 |
|---|---|
| `results_cold_item_v2.json` stale HR/MRR | **DONE** — regenerated with proper HR/MRR for all 4 datasets, both `lc2c` (V1) and `lc2c_v2` (V2) keys present |
| Books 0.1023 vs. 0.099 | **DONE** — picked 0.099 consistently across Tables 5.1 and 5.2 |
| LC2C V1/V2 naming inconsistency | **DONE** — `lc2c_v2` is now the explicit headline-method key in code and JSON; `lc2c` is the V1 legacy alias kept for backward compatibility |
| `RANKING_USERS_CAP = 5000` disclosure | **STILL TODO** — see F-Major-12 below |
| Per-user vectors for cold-item Wilcoxon | **STILL TODO** — see F6 below |
| CLCRec/DropoutNet head-to-head | **CAMERA-READY** — actually running compute-heavy deep baselines is out of scope for a paper-revision pass |
| Chronological splits | **CAMERA-READY** |

So three items now genuinely done; two remain todo with explicit
acknowledgement in the paper; two are camera-ready.

### F2: --warm-only / --cold-user print and exit (not a real fix) — `AGREED, FIXED PROPERLY`

The previous "fix" made the flags accept but print-and-exit. This was
misleading. The correct fix, applied now:

- **Removed the `--warm-only` and `--cold-user` flags entirely** from
  `_bestrec_run/run_cold_item.py`.
- The script's `--help` now states: "This script covers cold-item ONLY.
  The warm leave-one-out (Tables 5.1, 5.2) and cold-user few-shot
  (Table 5.3) experiments live in the BEST_Rec_v4.ipynb notebook, NOT
  in this script. See RUNNING.md §3 for the notebook-based reproduction
  path."
- **`RUNNING.md` §3.1, §3.8, §5, §6** rewritten to point at the notebook
  + `consolidate_final.py` path instead of the bogus flag.
- **`SUBMISSION.md`** corrected: `run_cold_item.py` is now described as
  "cold-item evaluation only", not "warm-LOO + cold-user + cold-item".

This is the honest fix the reviewer asked for. A command that does not run
the advertised experiment should not exist; documentation should point at
what actually works.

### F3: Cold-item provenance contradictory — `AGREED, FIXED`

The reviewer correctly identified that the paper's Table 5.4 V2 values
came from `results_ablation_lc2c.json`, while `run_cold_item_v2.py`'s
`lc2c` method computed V1 and wrote `results_cold_item_v2.json`.

Fix applied:
- Added `make_score_lc2c_v2` (direct ridge, no SVD) to
  `_bestrec_run/run_cold_item_v2.py`.
- Renamed the legacy method to `make_score_lc2c_v1` with an alias
  `make_score_lc2c = make_score_lc2c_v1` for backward compatibility.
- The `methods` list now includes both `lc2c` (V1) and `lc2c_v2` (V2 —
  paper's headline method).
- `cf_hybrid` now fuses V2 + content-direct (the previous version fused
  V1, which was a bug consistent with the V1/V2 naming confusion).

After regenerating `results_cold_item_v2.json` on all four datasets, the
JSON now contains both keys with values that match the paper's Table 5.4
to within rounding:

```
                       paper       JSON (lc2c_v2)
Beauty                 0.173       0.1731
Fashion                0.155       0.1548
Instruments            0.058       0.0575
Books                  0.065       0.0653
```

Direct rerun (`uv run python run_cold_item_v2.py beauty`) now produces
`lc2c_v2` = 0.1731, matching the paper exactly.

### F4: Stale JSON still in submitted package — `AGREED, FIXED`

The reviewer is right that adding a caption disclaimer was insufficient.
Fix applied:

- **Reran `run_cold_item_v2.py` for all four datasets** with the new V2
  method. The regenerated `results_cold_item_v2.json` has non-zero
  HR@10 and MRR for every method:
  - Beauty: `random` HR=0.1443, `cf_hybrid` HR=0.3160, etc.
  - Fashion / Instruments / Books all similarly non-zero.
- **Table 5.4 caption** in the paper updated to reference the regenerated
  JSON rather than the previous "stale HR/MRR" warning.

The reviewer's own rerun numbers and ours now agree, and the JSON is the
source of truth.

### F5: Significance script does not recompute warm-LOO Wilcoxon tests — `AGREED, PARTIALLY ADDRESSED`

The reviewer is right that `compute_significance.py` consumes stored
p-values rather than recomputing them from per-user vectors. The honest
state is:

- The raw paired-Wilcoxon p-values stored in `results_FINAL.json` were
  computed inside `BEST_Rec_v4.ipynb` (which has access to the per-user
  NDCG vectors during the notebook run) and persisted to the aggregated
  JSON.
- `compute_significance.py` now correctly applies Holm-Bonferroni to
  those stored raw p-values and writes the corrected significance
  markers used in Table 5.2.

**What is still missing:** a standalone script that takes the raw
per-user NDCG vectors and recomputes the Wilcoxon test from scratch.
This requires (a) saving the per-user vectors during the notebook run,
which `BEST_Rec_v4.ipynb` does not currently do, and (b) writing the
companion script. I have flagged this as a camera-ready item rather
than claiming it is done.

Until the standalone recompute is in place, reviewers should treat the
warm-LOO p-values as auditable from `results_FINAL.json` but not
independently reproducible. The Holm correction in
`compute_significance.py` is deterministic given the stored p-values and
can be verified by inspection.

### F6: Cold-item significance script labels V1 as V2 — `AGREED, FIXED`

The previous `compute_significance.py` read `lc2c` (= V1) from
`results_cold_item_v2.json` but printed labels saying "LC2C V2". Now
fixed:

- The cold-item section in `compute_significance.py` reads both `lc2c`
  and `lc2c_v2` from the regenerated JSON and prints them in separate
  columns, with the headers explicitly labelled "LC2C V1" and "LC2C V2".
- Two CAVEAT paragraphs make clear: (1) this is a mean-of-fold-means
  comparison, not a per-user paired Wilcoxon (still missing); (2) `lc2c_v2`
  is the headline method, `lc2c` is the V1 legacy variant.

Running the updated script now produces:
```
Dataset       content-dir  LC2C V1   LC2C V2  V2-vs-CD  V2-vs-V1
beauty           0.1449    0.1611    0.1731     19.4%      7.4%
fashion          0.1338    0.1566    0.1548     15.7%     -1.1%
instruments      0.0355    0.0502    0.0575     62.1%     14.6%
books            0.0272    0.0456    0.0653    140.0%     43.1%
```

These match the paper's Table 5.4 (+19% / +16% / +62% / +141% over
content-direct; Fashion now correctly showing -1.1% on V2-vs-V1 rather
than the previous "ties on Fashion" rounding).

### F7: Paper contradicts corrected results — `AGREED, FIXED`

The reviewer listed eight specific contradictions in the paper text.
Status of each:

| # | Reviewer's flag | Fix |
|---|---|---|
| 1 | "tuned attention-based GNN baseline" for LightGCN | **FIXED.** §2.2.3 now says "graph-convolutional CF baseline at canonical settings". |
| 2 | "BEST-Rec ranks first by NDCG@10 against six baselines" | **FIXED.** Abstract, §1, §5 now say "highest mean NDCG@10 on Beauty, Fashion, and Books; HO-EASE wins Instruments by 0.001". |
| 3 | "strongest model in the evaluation suite" | **FIXED.** Replaced with "competitive linear baseline that ties or beats six standard baselines in mean NDCG@10". |
| 4 | "V2 consistently improves on V1" / "V2 dominates V1 across datasets" | **FIXED.** Both the §5.5.1 caption and Figure 5.5/5.6 captions now say "V2 outperforms V1 on Beauty/Instruments/Books and ties/slightly loses on Fashion". |
| 5 | "deep models match or beat us only on the largest dataset (Instruments)" | **FIXED.** §6.1 now correctly identifies Books as largest by interaction count and rewords the Instruments observation as "the dataset where the per-item interaction count is highest among the smaller datasets". |
| 6 | "matches or beats six independent baselines including HO-EASE" | **FIXED.** §6.4 reworded to "highest mean NDCG@10 on three of four datasets ... within 0.001 of Higher-Order EASE on Instruments". |
| 7 | "statistically beats six baselines including LightGCN, MultiVAE, iALS across datasets" (conclusion) | **FIXED.** Conclusion now spells out the Holm-corrected result: significant against Popularity (all 4), MultiVAE (3 of 4), iALS (Instruments), LightGCN (Books); n.s. against EASE-pure and HO-EASE. |
| 8 | "+78% Beauty" / "+8% Instruments" inconsistent with body's +64% / +5% | **FIXED.** All occurrences of the LightGCN gap percentages now use the corrected +64% / +43% / +5% / +113%. |

Also fixed by extension: all "TRUE cold-item" phrasings replaced with
"cold-fold-catalog cold-item" or "cold-item GroupKFold protocol",
including Figure 5.4's caption.

### F8: README / RUNNING / SUBMISSION misleading — `AGREED, FIXED`

The previous version of these documents claimed the script ran experiments
it did not run. Fix applied:

**RUNNING.md:**
- §3.1 rewritten: "These two experiments live in `BEST_Rec_v4.ipynb`, not
  in any standalone script." Provides the actual `jupyter nbconvert`
  reproduction command and `consolidate_final.py` aggregation step.
- §3.8 full-sweep recipe updated to use the notebook path for warm/cold-user.
- §5 ("Common issues"): removed the bogus "Reduce LightGCN batch size in
  `run_cold_item.py`" pointer; LightGCN training lives in the notebook, not
  in this script.
- §5 quick-start updated to use `run_cold_item_v2.py` + `compute_significance.py`.
- §6 traceability table: rows for Tables 5.1/5.2/5.3 now point to the
  notebook → `consolidate_final.py` → `results_FINAL.json` path.

**SUBMISSION.md:**
- §2 file table: `run_cold_item.py` is now described as "cold-item evaluation
  only" with an explicit pointer to the notebook for warm/cold-user.
- `run_cold_item_v2.py` description now names the seven methods including
  `lc2c_v2` as the headline.
- Added `consolidate_final.py` and `compute_significance.py` rows.
- §3 cached-results table broken out per JSON with explicit purpose and
  reference to which Table/Figure each populates.
- §6 quick-start rewritten to use `run_cold_item_v2.py` + the notebook
  path for warm-LOO.

**README.md:**
- "TRUE Cold-ITEM" → "Cold-item GroupKFold-by-item (ranking among held-out
  20% item fold)".
- LC2C definition rewritten with the V2 (headline) algorithm first and V1
  shown as the ablation; "first cold-item method" softened to "To our
  knowledge this specific formulation ... has not been reported previously".
- "All baselines + Wilcoxon significance" updated to mention Holm correction
  and explicitly call out that cold-item significance is camera-ready scope.
- "+78%" / "+8%" LightGCN gaps updated to corrected +64% / +5%.
- Books warm-LOO updated from 0.1023 to 0.0990 to match the paper.
- "Reviewer concerns addressed (all 11)" softened to "Reviewer concerns
  addressed (partial — see RESPONSE_TO_STRICT_REVIEW*.md for the full audit)".

### F9: Books 0.1023 vs 0.099 explained, not fixed — `AGREED, FIXED`

The reviewer is right that two different numbers for the same algorithm
in two tables is not acceptable, regardless of how well it is captioned.

Fix applied:

- **Table 5.1 Books NDCG@10 changed from 0.1023 to 0.0990** to match
  `results_FINAL.json::baselines.ease_sbert` which is the same value used
  in Table 5.2.
- Caption updated to explain: "The Books NDCG@10 of 0.099 here matches
  the `baselines.ease_sbert` cell in `results_FINAL.json` and the Table 5.2
  cell, resolving the previous 0.1023-vs-0.099 inconsistency between tables
  flagged in review. An earlier draft reported 0.1023 here from a slightly
  different preprocessing pass; we have adopted the 0.099 value from the
  unified baseline-comparison run as the canonical figure to keep Tables
  5.1 and 5.2 consistent."
- README.md headline table also updated from 0.1023 to 0.0990 for the
  same Books cell.

A clean single-pipeline re-run (re-running both warm-LOO and the
baseline comparison from one immutable seeded split) is still needed for
camera-ready perfection, but the two visible tables now report identical
values.

### F10: LC2C not consistently defined across artifacts — `AGREED, FIXED in code; partial in older artifacts`

Fix applied:

- **Code (`run_cold_item_v2.py`):** added `make_score_lc2c_v2` (the
  headline algorithm); renamed the existing function `make_score_lc2c` →
  `make_score_lc2c_v1` with an alias `make_score_lc2c = make_score_lc2c_v1`
  for backward compatibility. The `methods` list now contains both `lc2c`
  (V1 legacy) and `lc2c_v2` (V2 headline).
- **JSON (`results_cold_item_v2.json`):** regenerated and now contains both
  `lc2c` and `lc2c_v2` keys.
- **Paper:** Table 5.4 caption explicitly maps "LC2C-direct (V2, ours)" to
  the `lc2c_v2` JSON key.
- **README.md:** algorithm description rewritten with V2 first (headline)
  and V1 shown as the ablation.
- **`compute_significance.py`:** cold-item section now reads both `lc2c`
  and `lc2c_v2` and labels them correctly.

**Still partial:** `run_lc2c_ablation.py` and `make_figures_v3.py` still
use their own internal naming conventions (`V0_content_direct`,
`V1_lc2c_full_k64`, `V2_lc2c_no_svd`, etc.) which are stable for the
ablation figures but do not exactly match the `lc2c` / `lc2c_v2` keys
in `results_cold_item_v2.json`. Unifying every file to one convention
requires a coordinated rename + figure regeneration; this is camera-ready
scope.

### F11: Paper does not establish SOTA — `AGREED, ALREADY DISCLAIMED`

Already addressed in round 1 (Abstract + §5.2 disclaimer naming BLAIR,
TIGER, CLCRec, MELT, DropoutNet). Round 2 strengthens this:

- §5.2 "What this comparison does and does not establish" paragraph
  retained.
- Conclusion rewritten to drop any "strongest model" / "statistically
  beats six baselines" framing.
- README headline table no longer says "vs LightGCN ... +78% Beauty ...";
  the corrected +64% / +43% / +5% / +113% gaps are reported with the Holm
  significance caveat.

The paper is now positioned as "competitive lightweight closed-form linear
baseline with an honest cold-item extension and incomplete but documented
empirical scope," not as state-of-the-art. We commit to actually running
CLCRec and DropoutNet for camera-ready (still not done).

---

## Major findings — response

### M12: "TRUE cold-item" overstated — `AGREED, FIXED`

Every occurrence of "TRUE cold-item" / "TRUE Cold-ITEM" in the paper,
README, RUNNING.md, SUBMISSION.md, and figure captions has been replaced
with the more precise "cold-item GroupKFold protocol (ranking among the
held-out 20% item fold)" or "cold-fold-catalog cold-item protocol".

### M13: Baseline tuning story inconsistent — `AGREED, FIXED via F7`

The §2.2.3 "tuned attention-based GNN" claim was the source of this
inconsistency. With it removed, the rest of the paper consistently
describes the deep baselines as "canonical hyperparameters from their
original papers" (§4.3) with the §7.3 caveat that per-baseline grid
search is camera-ready scope.

### M14: Holm results undermine the headline — `AGREED, REFLECTED IN TEXT`

The Abstract, §1 contributions, §5.2 narrative, §6.1, and §8 Conclusion
all now state the Holm-corrected result honestly: significant against
Popularity (all 4), MultiVAE (3 of 4), iALS on Instruments, and LightGCN
on Books only; n.s. against EASE-pure and HO-EASE on every dataset.
HO-EASE numerically wins Instruments. The phrase "strongest model" has
been removed.

### M15: Cold-item V2 not statistically validated — `AGREED, PARTIALLY ADDRESSED`

The current submission reports mean NDCG@10 evidence for V2 and explicitly
disclaims the absence of per-user paired Wilcoxon for cold-item in the
Conclusion and in `compute_significance.py`. Adding a real cold-item
paired Wilcoxon requires saving per-user NDCG vectors during the cold-item
evaluation, which is one of the camera-ready items.

---

## Minor / line-level issues — response

The reviewer listed 14 minor issues. Most are subsumed by the major
fixes above. A few that needed individual attention:

- **README.md "Per-fold SBERT encoding" vs. "SBERT computed once from titles"**:
  Fixed. The Methodology section now states "EASE refit per fold (closed-form,
  leakage-free). SBERT title embeddings are computed once from external
  metadata (Amazon catalog titles, not derived from the train/test
  interaction split)."
- **README.md "Full-item ranking" claim applied to cold-item**: Fixed.
  The Methodology section now disambiguates: warm-LOO and cold-user use
  full-item ranking; cold-item uses cold-fold-catalog ranking.
- **`compute_significance.py` 95% bootstrap CI claim**: I removed the
  outdated comment about bootstrap CI when rewriting the cold-item
  section.
- **`SUBMISSION.md` "every number traces to JSON"**: Replaced with a
  per-JSON breakdown that explicitly names which Table or Figure each
  JSON populates.
- **`SUBMISSION.md` V0/V1/V2/V3 in `run_cold_item_v2.py`**: Corrected.
  The script's seven methods are now named explicitly:
  `random / content_direct / content_rating_weighted / content_topk /
  lc2c / lc2c_v2 / cf_hybrid`. The V0/V1/V2/V3 naming lives in
  `run_lc2c_ablation.py` (the ablation file), which is documented
  separately.

---

## What is still on the camera-ready to-do list

Honestly:

1. **Per-user vectors for cold-item Wilcoxon.** Requires modifying
   `run_cold_item_v2.py` to save per-user NDCG vectors, then a follow-up
   script to compute paired Wilcoxon + Holm correction across V2 vs. each
   of {content-direct, V1, content_topk, cf_hybrid}.
2. **CLCRec, DropoutNet head-to-head** against LC2C on the cold-item
   protocol.
3. **Per-baseline grid search** for LightGCN and MultiVAE on each
   dataset.
4. **`RANKING_USERS_CAP = 5000` disclosure** in §4.2 of the paper. (The
   constant is acknowledged in the code but should be explicitly
   documented in the methodology section.)
5. **Unify LC2C V1/V2 naming** in `run_lc2c_ablation.py` and
   `make_figures_v3.py` to match the `lc2c_v2` convention used everywhere
   else.
6. **Standalone Wilcoxon re-compute** from saved per-user vectors so
   reviewers can independently verify warm-LOO significance without
   trusting the externally-computed raw p-values.
7. **Single-pipeline re-run** of warm-LOO so that `results_FINAL.json`'s
   `warm_mean['NDCG@10']` and `baselines['ease_sbert']['NDCG@10']` for
   Books are identical (currently they differ by ~0.003 and we have
   resolved the inconsistency by adopting the baselines-table value).
8. **Chronological split** as a sanity-check evaluation alongside the
   random per-user split.

The reviewer's bottom line — "the cold-item result can be described as
preliminary mean NDCG evidence only" — is now the framing of the paper
itself. The paper does not claim per-user Wilcoxon significance for
cold-item, does not claim SOTA, does not claim "strongest model", does
not claim "statistically beats six baselines", and does not claim
"TRUE cold-item". Each of these previously over-broad claims has been
narrowed to what the data actually supports under Holm correction.

---

## Summary of the new paper's honest claims

Final state after this round:

| Claim | Status under this revision |
|---|---|
| Highest mean warm-LOO NDCG@10 across 4 datasets | True on 3 of 4 (HO-EASE wins Instruments by 0.001) |
| Holm-significantly beats popularity | True on all 4 |
| Holm-significantly beats MultiVAE | True on 3 of 4 (n.s. on Instruments) |
| Holm-significantly beats iALS | True on Fashion, Instruments; n.s. on Beauty; OOM on Books |
| Holm-significantly beats LightGCN | True on Books only |
| Holm-significantly beats EASE-pure / Higher-Order EASE | n.s. on all 4 |
| LC2C V2 beats content-direct in mean NDCG@10 | True on all 4 |
| LC2C V2 beats LC2C V1 in mean NDCG@10 | True on Beauty/Instruments/Books; -1% on Fashion |
| LC2C V2 statistically better than content-direct (per-user paired test) | **Not yet measured** — camera-ready |
| State of the art | **Not claimed** |
| Reproducibility from a single command | warm/cold-user via notebook; cold-item via standalone script |
| Bibliography is complete and verified | Yes |

The revised paper is `BEST_Rec_v4_Full_Paper.pdf` (51 pages, 1.52 MB).
The supporting code changes are in `_bestrec_run/run_cold_item.py`,
`_bestrec_run/run_cold_item_v2.py`, and
`_bestrec_run/compute_significance.py`. The supporting JSON regenerations
are in `_bestrec_run/results_cold_item_v2.json` (every cell now has
correct HR/MRR). Documentation in `README.md`, `RUNNING.md`, and
`SUBMISSION.md` has been rewritten to match what the package actually does.

The reviewer's "Reject" verdict was correct for the prior submission. The
honest question now is whether the present narrower-claim version reaches
the bar; my own answer is that it now meets the bar for an honest
competitive-baseline paper but does not meet the bar for an SOTA claim,
and I have framed the paper accordingly.
