# Pre-Declared, Artifact-Gated Evaluation for Sequential Recommendation

**Causal FIR Filtering and Dataset-Conditional Text Benefits on Amazon Reviews 2023.**

This repository is the working artifact repository for the manuscript (ACM TORS submission format; **public** — the split CSVs (now 18 incl. Industrial_and_Scientific and CDs_and_Vinyl), four text caches, and the 107 TFV2 per-user sidecars are deposited as hash-manifested release assets; `bootstrap_public_clone.py` reconstructs a fresh clone's full evidence boundary):
code, pre-declarations, results of record, provenance manifests, the fail-closed build
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
(**every one of the 175 artifact-gated cells recomputed from source artifacts**; exits
nonzero on any mismatch, untraceable cell, or missing claim family) → release-manifest hash
verification (269 files at the current manifest) → the pre-declared Musical_Instruments gate adjudicator → the TFV2 repaired-estimand adjudicator (outcome-visible — §5.3 chronology) → **the
Office V3 adjudicator (counted; the build fails unless the campaign verdict is PASS)** →
**the FIR-breadth adjudicator (counted; both categories must be CONFIRMED)** → the Office V1
adjudicator (descriptive/VOID). Every counted campaign's live adjudicator gates the build
(hardened 2026-07-18); `update_release_manifest.py --verify-git <commit|tag>` additionally
checks the manifest against the git blobs. **Hash-check rule:** verify digests against the
tag blob (`git show <tag>:FILE`), the release asset, or the bundle payload — never raw
Windows worktree bytes, whose CRLF line endings legitimately differ from the LF-pinned
blobs (`DOI_DEPOSIT_INSTRUCTIONS.md` has the full rule).

## What is claimed (exactly this, nothing broader)

- **Two counted pre-declared per-category point-estimate comparisons** vs published
  HSTU-BLaIR values (single-run comparators; no paired or distributional superiority is
  claimed, and no SOTA claim of any kind is made):
  - **Musical_Instruments**: fresh 5-seed 95% CI lower bounds **0.04096** (K=16) / **0.04083**
    (K=8) vs published 0.0406; 10/10 seeds above (`SOTA_CONFIRM_PREREG_V2.md`).
  - **Office_Products (V3)**: CI lower bounds **0.03033** (K=16) / **0.03024** (K=8) vs both
    the environment-matched local regeneration 0.0279 and the published 0.0271; 10/10 seeds
    above (`PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`).
- **The leak-free causal FIR filter is supported on all four categories tested** — an internal
  same-seed filter-vs-no-filter contrast (never a comparator claim; same-numbered seeds are
  NOT initialization-paired — the frozen breadth rule's paired interpretation is withdrawn,
  and the primary analysis is independent-arm Welch, both 95% CIs excluding zero:
  Industrial_and_Scientific Δ **+0.0024** [+0.0019, +0.0029], CDs_and_Vinyl **+0.0057**
  [+0.0050, +0.0063]; the treatment is the FIR-plus-initialization/optimizer package)
  (`PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md` + its 2026-07-20 erratum).
- **Text benefits are dataset-conditional** (help on sparse categories, ≈null on dense ones),
  supported by controlled thinning interventions.
- **The evaluation apparatus itself** — version-controlled pre-declaration (the TFV2 campaign carries OpenTimestamps proofs whose earliest Bitcoin attestation postdates its first result — the pre-launch freeze rests on Git history alone, a disclosed limitation stated exactly in §5.3 disclosure (vii)), fail-closed artifact
  gate, comparator regeneration, symmetric self-VOIDing — demonstrated end to end.

**Explicitly not claimed:** state-of-the-art on anything (on Video_Games our 0.0673 sits
below the published 0.0760 — "competitive, not SOTA"); statistical superiority over
single-run comparators; anything from the Office **V1** campaign, whose pre-declared
floor check failed and whose **VOID stands permanently** (Appendix A.0) — the redesigned V3
campaign above is a separate pre-declaration that passed under its frozen wording.

## Layout

| Path | What |
|---|---|
| `PAPER_SUBMISSION.md` / `.pdf`, `PAPER_DRAFT.md` | Canonical paper (reader edition) and working draft with status history |
| `paper_tex/` | Generated ACM TORS LaTeX twin + `PAPER_TORS.pdf` + hygiene scanner |
| `_bestrec_run/` | All preprocessing/training/eval code, gates, adjudicators, result JSONs of record |
| `SOTA_CONFIRM_PREREG_V2.md`, `PREREG_OFFICE_V3.md`, `PREREG_FIR_BREADTH.md` (+ results files) | Immutable pre-declarations and their adjudicated outcomes |
| `RELEASE_MANIFEST.json` | Self-policing SHA256 manifest (verified inside the strict gate) |
| `PAPER_REVIEW_AUDIT.md` / `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` | The hourly adversarial audit chain (a second AI system) and point-by-point responses |
| `DOI_DEPOSIT_INSTRUCTIONS.md`, `VENUE_PLAN.md` | Archival/deposit and venue decisions |
| `PLAIN_LANGUAGE_COMPANION.md`, `companion_site/` | Non-technical explainer (documentation, not submission material) |
| `README_LC2C_HISTORICAL.md` | Preserved README of the repository's **earlier, unrelated LC2C/EASE cold-item project** (releases up to `bestrec-raw-records-v1`); nothing in it is claimed by the current paper |

## Releases

- **`v1.1.11-deposit`** (current archival bundle, cut 2026-07-21; each deposit release supersedes the previous) — the 66-entry deposit zip + sidecar hash + manifest + both PDFs. Supersedes `v1.1.10-deposit`, which went stale the same day it was cut (four post-tag content commits — the 22:57 audit's measured drift; the deposition gate now refuses to rebuild a version whose tag no longer matches the tree). The from-zero public-clone verification is re-executed at each pushed tag and its transcript committed to the branch.
- **`v0.9-audit-evidence`** — the pinned-parity ZIP, `RELEASE_MANIFEST.json`, all 18 split CSVs, four text caches, and the 107 TFV2 per-user sidecars (all hash-manifested; uploaded 2026-07-20; the manifest inventory is authoritative for counts). Fresh clones: `git submodule update --init && python bootstrap_public_clone.py` before the strict gate.
- **`bestrec-raw-records-v1`** — the historical LC2C project's raw records (see `README_LC2C_HISTORICAL.md`).

Data: the Amazon Reviews 2023 dataset (McAuley Lab) is **not redistributed**; derived
splits/caches are pinned by SHA256 with regeneration scripts.

License: MIT (`LICENSE`). Citation metadata: `CITATION.cff` / `.zenodo.json`.

## License scope (stated exactly; added 2026-07-21)

The repository's MIT license covers **the code in this repository only**. It does
not and cannot assign a license to the Amazon Reviews 2023 dataset or to the
derived interaction-split CSVs / text caches / per-user sidecars distributed as
release assets: those derive from the McAuley Lab's public research release,
whose maintainers state they are not in a position to assign a license or dictate
usage terms (that statement is not an affirmative permission grant, and we do not
treat it as one — manuscript §10). Derived data assets are redistributed on the
dataset's public research availability with attribution, takedown honored
immediately on maintainer, platform, or venue request. For double-anonymous
review, the manuscript PDF is anonymized; this named repository is the
post-acceptance record, and anonymized artifact access at review time follows the
journal's current instructions.
