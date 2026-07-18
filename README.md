# Pre-Registered, Artifact-Gated Evaluation for Sequential Recommendation

**Causal FIR Filtering and Dataset-Conditional Text Benefits on Amazon Reviews 2023.**

This repository is the complete artifact for the manuscript (ACM TORS submission format):
code, pre-registrations, results of record, provenance manifests, the fail-closed build
gate, and the full adversarial audit chain. The canonical paper is
[`PAPER_SUBMISSION.md`](PAPER_SUBMISSION.md) (reader PDF: `PAPER_SUBMISSION.pdf`); the
venue manuscript is `paper_tex/PAPER_TORS.pdf` (generated from the canonical markdown —
[`CANONICAL_SUBMISSION.md`](CANONICAL_SUBMISSION.md) governs). A non-technical companion
with analogies and interactive demos: [`PLAIN_LANGUAGE_COMPANION.md`](PLAIN_LANGUAGE_COMPANION.md).

## Verify everything with one command

```powershell
uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict
```

This runs, fail-closed: the bitwise HSTU core-block parity test → the artifact-graph build
(**every one of the 168 printed empirical numbers recomputed from source artifacts**; exits
nonzero on any mismatch, untraceable cell, or missing claim family) → release-manifest hash
verification (153 files) → the pre-registered Musical_Instruments gate adjudicator → the
Office V1 adjudicator (descriptive/VOID). Separate mechanical adjudicators:
`_bestrec_run/adjudicate_office_v3.py`, `_bestrec_run/adjudicate_fir_breadth.py`.

## What is claimed (exactly this, nothing broader)

- **Two counted pre-registered per-category point-estimate comparisons** vs published
  HSTU-BLaIR values (single-run comparators; no paired or distributional superiority is
  claimed, and no SOTA claim of any kind is made):
  - **Musical_Instruments**: fresh 5-seed 95% CI lower bounds **0.04096** (K=16) / **0.04083**
    (K=8) vs published 0.0406; 10/10 seeds above (`SOTA_CONFIRM_PREREG_V2.md`).
  - **Office_Products (V3)**: CI lower bounds **0.03033** (K=16) / **0.03024** (K=8) vs both
    the environment-matched local regeneration 0.0279 and the published 0.0271; 10/10 seeds
    above (`PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`).
- **The leak-free causal FIR filter helps on all four categories tested** — an internal
  paired filter-vs-no-filter contrast (never a comparator claim). Two categories under a
  dedicated pre-registration with zero per-category tuning: Industrial_and_Scientific
  paired Δ **+0.0024** (95% CI [+0.0018, +0.0030]), CDs_and_Vinyl **+0.0057**
  (95% CI [+0.0049, +0.0064]), 5/5 seeds each (paper-printed precision; full values in the
  results file) (`PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`).
- **Text benefits are dataset-conditional** (help on sparse categories, ≈null on dense ones),
  supported by controlled thinning interventions.
- **The evaluation apparatus itself** — immutable pre-registration, fail-closed artifact
  gate, comparator regeneration, symmetric self-VOIDing — demonstrated end to end.

**Explicitly not claimed:** state-of-the-art on anything (on Video_Games our 0.0673 sits
below the published 0.0760 — "competitive, not SOTA"); statistical superiority over
single-run comparators; anything from the Office **V1** campaign, whose pre-registered
floor check failed and whose **VOID stands permanently** (Appendix A.0) — the redesigned V3
campaign above is a separate pre-registration that passed under its frozen wording.

## Layout

| Path | What |
|---|---|
| `PAPER_SUBMISSION.md` / `.pdf`, `PAPER_DRAFT.md` | Canonical paper (reader edition) and working draft with status history |
| `paper_tex/` | Generated ACM TORS LaTeX twin + `PAPER_TORS.pdf` + hygiene scanner |
| `_bestrec_run/` | All preprocessing/training/eval code, gates, adjudicators, result JSONs of record |
| `SOTA_CONFIRM_PREREG_V2.md`, `PREREG_OFFICE_V3.md`, `PREREG_FIR_BREADTH.md` (+ results files) | Immutable pre-registrations and their adjudicated outcomes |
| `RELEASE_MANIFEST.json` | Self-policing SHA256 manifest (verified inside the strict gate) |
| `PAPER_REVIEW_AUDIT.md` / `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` | The hourly adversarial audit chain (a second AI system) and point-by-point responses |
| `DOI_DEPOSIT_INSTRUCTIONS.md`, `VENUE_PLAN.md` | Archival/deposit and venue decisions |
| `PLAIN_LANGUAGE_COMPANION.md`, `companion_site/` | Non-technical explainer (documentation, not submission material) |
| `README_LC2C_HISTORICAL.md` | Preserved README of the repository's **earlier, unrelated LC2C/EASE cold-item project** (releases up to `bestrec-raw-records-v1`); nothing in it is claimed by the current paper |

## Releases

- **`v1.1.3-deposit`** (current archival bundle; each deposit release supersedes the previous) — the deposit zip + sidecar hash + manifest + both PDFs, upload verified by download-hash round trip.
- **`v0.9-audit-evidence`** — immutable data assets (splits, text caches, historical result families) pinned by `RELEASE_MANIFEST.json`.
- **`bestrec-raw-records-v1`** — the historical LC2C project's raw records (see `README_LC2C_HISTORICAL.md`).

Data: the Amazon Reviews 2023 dataset (McAuley Lab) is **not redistributed**; derived
splits/caches are pinned by SHA256 with regeneration scripts.

License: MIT (`LICENSE`). Citation metadata: `CITATION.cff` / `.zenodo.json`.
