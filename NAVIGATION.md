# Repository navigation

**Start here.** This repository backs one manuscript: an artifact-gated evaluation of a causal FIR
module for sequential recommendation. Its distinguishing property is that **null, deviated, retracted
and VOID outcomes are preserved under the same reporting rule as positive ones** — so a large part of
what looks like clutter is the contribution, not residue. See [§6](#6-what-must-not-be-deleted).

---

## 1. Read in this order

| # | file | what it is |
|---|---|---|
| 1 | `CANONICAL_SUBMISSION.md` | **single source of truth** — the canonical claim set; nothing broader is claimed anywhere |
| 2 | `PAPER_SUBMISSION.md` | the canonical authored manuscript (reader edition) |
| 3 | `CLAIM_ARTIFACT_MAP.md` | every paper-bound cell → the artifact that recomputes it |
| 4 | `RELEASE_MANIFEST.json` | hash-pinned release contents |
| 5 | `TORS_METHODOLOGY_CHECKLIST.md` | submission-readiness matrix, row by row |
| 6 | `TIER_A_PUBLICATION_ROADMAP.md` | phase plan and gates |

`PAPER_SUBMISSION.pdf` is the reader rendering. `paper_tex/` is the **venue mirror**
(`PAPER_TORS.pdf`, `PAPER_TORS_acmsmall.pdf`, `PAPER_TORS_SUPPLEMENT.pdf`). The reader edition is
intentionally longer — it retains the full evidence record; the TeX package is the focused submission.

## 2. Directory map

| path | contents | keep? |
|---|---|---|
| `_bestrec_run/` | runners, adjudicators, and **all `results_*.json`** — the evidence base | **yes, permanently** |
| `paper_tex/` | venue mirror: sections, generated tables, built PDFs | yes |
| `figures/` | figures + their `*_data.csv` provenance | yes |
| `_bestrec_sota_lab/`, `_bestrec_confirmatory_sasrec/` | earlier campaign code | yes (provenance) |
| `archive_noncanonical/` | superseded drafts, explicitly marked non-canonical | **yes — see §6** |
| `retracted_archive/` | retracted analyses, retained deliberately | **yes — see §6** |
| `ee_baselines/`, `external/` | comparator code; `external/HSTU-BLaIR` is upstream, never modified | yes |
| `cloud/`, `data_raw_proper/` | infrastructure and raw-input handling | yes |
| `_bestrec_run/tmp/` | **scratch** — clean-clone / replay verification workspaces | no — reproducible |

## 3. Preregistrations and their verdicts

Every counted claim traces to a frozen preregistration plus a mechanical adjudicator that was the
**first reader** of the sealed endpoint.

| prereg | adjudication artifact |
|---|---|
| `PREREG_OFFICE_V3.md` | `_bestrec_run/*office*` / `OFFICE_V3_RESULTS.md` |
| `PREREG_FIR_CANONICAL_BREADTH.md` | `_bestrec_run/fir_canonical_breadth_adjudication.json` |
| `PREREG_FIR_CONTROLS.md` | `_bestrec_run/fir_controls_adjudication.json` |
| `PREREG_FIR_POINTWISE_V1.md` | `_bestrec_run/fir_pointwise_v1_adjudication.json` |
| `PREREG_FIR_EFFICIENCY_ML1M_V1.md` | `_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json` |
| `PREREG_WEAREC_BASELINE_V1.md` | `_bestrec_run/wearec_baseline_v1_adjudication.json` |
| `PREREG_EE_V3.md` / `PREREG_EE_V4.md` | `_bestrec_run/ee_v3_adjudication.json`, `ee_v4_adjudication.json` |

**Frozen preregs and freeze commits are immutable.** Do not edit or re-date them.

## 4. The counted claim boundary

Only **two** comparisons are counted:

1. **Musical_Instruments** vs published 0.0406
2. **Office_Products V3** vs 0.0271 **and** 0.0279

**Office_Products V1 is VOID forever** — it failed its own pre-declared floor check and no later
result restores it. **TFV2 is outcome-visible, not confirmatory.** Everything else is context.

Forbidden vocabulary unless literally established: *SOTA, causal isolation, equal capacity, equal
budget, independent confirmation, generalizes, equivalent.* **A confidence interval crossing zero is
not equivalence.**

## 5. Side investigations (not manuscript evidence)

Branch `claude/filter-overparam-experiments` holds exploratory work that licenses **no** manuscript
claim: the FMLP-Rec filter-parameterisation ladder (80 runs; the 64× channel-tying hypothesis was
**refuted** on ML-1M), a cross-backend reproducibility study, and a SASRec probe. Per-run scores are
committed as CSV; the upstream BSARec suite is **cloned, not vendored** — reproduce via
`experiments/filter_overparam/setup.sh`, which pins commit `c80bdc0`.

`CLAUDE_*.md` in the repo root are dated red-team memos. Several are **superseded** and carry banners
saying so — the banner is the record; the memo is not deleted.

## 6. What must NOT be deleted

Deleting any of the following destroys the paper's central contribution or its provenance chain:

1. **`results_*.json`** — never delete or overwrite. Rename-preserve only.
2. **VOID / NONCOUNTABLE / EXPOSED / integrity-failure records**, including the Office V1 VOID and
   `retracted_archive/`. The manuscript's claim is that it preserves these under one reporting rule;
   removing them while retaining positive results *is* the selective-reporting asymmetry it claims to
   have eliminated.
3. **Superseded memos and their banners** — the correction trail is the audit evidence.
4. **Frozen preregs and freeze commits** — immutable.
5. **Git history.** `RELEASE_MANIFEST.json` hash-pins **90 `.pt` checkpoint references**, and the
   manuscript and adjudications cite commit hashes. A history rewrite (BFG / `filter-repo`) to shrink
   `.git` would orphan those references and invalidate every cited hash. **Do not rewrite or
   force-push.**

## 7. Housekeeping that *is* safe

- `_bestrec_run/tmp/` clean-clone and replay workspaces — reproducible, deletable, git-ignored.
- Screenshot/QA scratch (`qa_final*/`, `temp/`) — deletable, git-ignored.
- The BSARec clone under `experiments/` — 1.9 GB, git-ignored, re-created by `setup.sh`.

**Note on repository size:** `.git` is ~24 GB, caused by ~95 MB model checkpoints committed earlier
in history. They are no longer tracked in the working tree, but remain in history and **cannot be
removed without a history rewrite**, which §6.5 forbids. If shrinking the clone becomes necessary,
the safe route is a *fresh* archival repository containing the release artifacts, published alongside
the existing history rather than replacing it.
