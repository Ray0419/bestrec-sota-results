# Artifact-Gated Evaluation of a Causal FIR Module for Sequential Recommendation

**A narrow modular contribution with outcome-known Amazon studies, a negative prospective MovieLens 1M test, and an artifact-gated audit trail.**

This repository is the working artifact repository for the manuscript (ACM TORS submission format; **public** — 407 release-only assets totaling 9,489,409,339 bytes, including the Software V3 endpoint/sidecar/checkpoint set, are deposited as hash-manifested release assets; `bootstrap_public_clone.py` reconstructs a fresh clone's full evidence boundary):
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
(**all 199 artifact-gated cells across 23 families recomputed from public source artifacts**; exits
nonzero on any mismatch, untraceable cell, or missing claim family) → release-manifest hash
verification (the live gate reports the authoritative file count) → the pre-declared Musical_Instruments gate adjudicator → the TFV2 repaired-estimand adjudicator (outcome-visible — §5.3 chronology) → **the
Office V3 adjudicator (counted; the build fails unless the campaign verdict is PASS)** →
**the FIR-breadth adjudicator (artifact-integrity: the frozen rule's legacy CONFIRMED tokens are checked mechanically; the paired premise is withdrawn and no inferential confirmation is implied)** → the Office V1
adjudicator (descriptive/VOID). Each public campaign's live or recorded verdict gates the build (MI V2, Office V3, TFV2, FIR breadth, E-A, canonical FIR breadth, FIR active controls, FIR pointwise placebo, Software V3, MovieLens `ML1M-NO-FIR-REPLICATION`, E-F; the E-G adjudicator also gates as an artifact-reproduction check but confers no confirmatory status — see PAPER_SUBMISSION.md §5.8). The MovieLens gate recomputes aggregate seed-vector arithmetic because private record-level endpoints are not redistributable; it does not claim independent endpoint replay.
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
- **The canonical gradient-active left-causal FIR residual has positive internal estimates on
  three outcome-visible categories:** Musical_Instruments +0.002265 (ordinary Welch 95% CI
  [+0.001928,+0.002602]), Industrial_and_Scientific +0.002110 (ordinary paired 95% CI
  [+0.001820,+0.002399]), and CDs_and_Vinyl +0.006150 (ordinary paired 95% CI
  [+0.005849,+0.006450]). Active controls show that trainable causal residual arms beat frozen
  identity. A subsequent equal-parameter current-position-only placebo is not detectably
  different from identity (−0.000069 [−0.000200,+0.000061]), while learned FIR beats it
  (+0.001941 [+0.001788,+0.002095]). This discriminates learned FIR from that compound placebo
  but does not isolate temporal access because basis/rank, activation, channel mixing, and
  temporal access change together;
  the competitive shared causal filter prevents per-channel-tap attribution. These are
  outcome-known internal mechanism estimates, never an independent-confirmation or comparator claim.
- **The prospectively frozen non-Amazon result is negative:** on MovieLens 1M rating≥4,
  learned FIR−identity is +0.000000 [−0.000074,+0.000075] (`p_Holm=.995`) and
  learned FIR−pointwise is +0.000035 [−0.000057,+0.000127] (`p_Holm=.796`), yielding
  `ML1M-NO-FIR-REPLICATION`. Shared/grouped/low-rank arms (16/128/320 parameters) meet
  the pre-declared noninferiority margin versus learned FIR (1,024), but only as
  conditional numerical compression because the learned-FIR effect gate failed. This is
  same-investigator evidence on one split, not independent confirmation or generalization.
- **Pre-declared fresh-seed hybrid (E-F, 2026-07-23):** late z-score fusion with train-only EASE (Steck 2019) lifted test NDCG@10 on all three categories tested (MI +0.0024, IS +0.0026, VG +0.0032; ordinary paired 95% CIs with Holm-adjusted decisions, fresh seeds 20260721-25); the MI fused five-seed mean 0.04399 exceeds the published single-run 0.0406 (point-estimate comparison, environment-caveated; see PAPER_SUBMISSION.md §5.7).
- **Sparse-warm text-fusion study (E-G, 2026-07-23; OUTCOME-VISIBLE, PROTOCOL-DEVIATED — descriptive only):** a validation-selected history-centroid text scorer raised tail-bin test NDCG@10 on all five categories (+0.0011 to +0.0048) at aggregate cost within margin, BUT the campaign's no-interim clause was violated, the literal config gate fails MI/VG, and the gate was amended after outcomes; no confirmatory status is claimed. Its intended clean replication (E-G2) was itself EXPOSED (a git add -A committed 14 in-progress confirm artifacts before adjudication, audit 2026-07-23 22:00); the sole remaining counted path is a future repository-sequestered E-G3 (PAPER_SUBMISSION.md §5.8).
- **Text tail benefit: one MI frequency-5-heavy case** (cross-dataset heterogeneity not established, interaction p = 0.13; the thinning intervention did NOT explain it — one fixed draw; mechanism unresolved).
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

- **`v1.2.0-deposit` (intended candidate; not yet tagged or published).** The current 908-entry
  candidate bundle is prepared locally and explicitly refuses a normal/tagged build while
  creator placeholders remain. `v1.1.11-deposit` is a historical snapshot and is stale
  relative to the present manuscript; it must not be uploaded as current.
- **`v0.9-audit-evidence`** — the mutable audit-evidence store used by the bootstrap path, not the final archival deposit. It contains the pinned-parity files/ZIP, all 21 split CSVs, six text/cache-map assets, 107 TFV2 per-user sidecars, 144 FIR-control endpoint/sidecar/checkpoint files, 72 FIR-pointwise endpoint/sidecar/checkpoint files, and 48 Software V3 endpoint/sidecar/checkpoint files. The authoritative current bootstrap inventory is **407 release-only assets / 9,489,409,339 bytes (about 8.84 GiB)**. A fresh HTTPS clone downloaded and raw-hash-verified all 407 assets with zero local reuse on 2026-07-28, and the public `RELEASE_MANIFEST.json` was uploaded last. Fresh clones: `python bootstrap_public_clone.py` before the strict gate; `git submodule update --init` is optional because the parity test can hydrate the exact pinned HSTU reference commit into its isolated cache.
- **`bestrec-raw-records-v1`** — the historical LC2C project's raw records (see `README_LC2C_HISTORICAL.md`).

Data: the Amazon Reviews 2023 dataset (McAuley Lab) is **not redistributed**; derived
splits/caches are pinned by SHA256 with regeneration scripts. MovieLens 1M record rows,
transformed splits, checkpoints, endpoints, and per-user sidecars are also not
redistributed under the ML-1M README; only aggregate provenance, statistics, code, and
adjudication enter the public graph.

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
immediately on maintainer, platform, or venue request. TORS review is single-blind (per the current author guidelines), so this named repository is cited directly from the manuscript; author metadata in the manuscript is a maintainer-supplied field before submission.
