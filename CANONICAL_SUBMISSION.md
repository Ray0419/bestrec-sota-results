# CANONICAL SUBMISSION — single source of truth (full-method audit F1; updated for round-2 audit F1, 2026-07-11)

**The one canonical paper:** the HSTU/FIR manuscript — working copy `PAPER_DRAFT.md`,
submission copy `PAPER_SUBMISSION.md` (+ rendered `PAPER_SUBMISSION.pdf` — page count varies by revision; machine-scanned at every render). The ACM/TORS LaTeX under `paper_tex/` is **generated, derived output** (`VENUE_PLAN.md`): regenerated from the canonical markdown + `hstu_tables.json`, never edited divergently.
Everything else is archived (see `archive_noncanonical/README.md`) or marked non-canonical
(`_bestrec_sota_lab/paper_draft/NONCANONICAL.md`).

## The canonical claim set (nothing broader is claimed anywhere)

1. **MI point-estimate result (externally approved; the first of the two counted
   per-category point-estimate comparisons — see item 3 for Office V3):** fresh 5-seed CI lower bounds exceed the published HSTU-BLaIR Musical_Instruments
   point estimate (0.0406) for both kernels (K=16 CI-LB 0.04096, K=8 CI-LB 0.04083, 10/10 fresh
   seeds above) — per-category point-estimate comparison, not paired superiority, not general
   SOTA. The comparator has additionally been **locally regenerated** by running the reference
   implementation itself (best full-eval epoch NDCG@10 = 0.0406 exactly; environment-caveated
   single run, §5.6 / `THEIRS_ON_OURS_REPORT.md`) — regeneration, never "official reproduction".
   Evidence: `SOTA_CONFIRM_PREREG_V2.md` → `SOTA_CONFIRM_V2_RESULTS.md` (+ errata).
2. **FIR treatment package (filter + initialization + optimizer path):** multi-seed package-arm estimates positive on **four categories** (Video_Games +
   Musical_Instruments in development; Industrial_and_Scientific + CDs_and_Vinyl under the
   pre-declared breadth campaign `PREREG_FIR_BREADTH.md` / `FIR_BREADTH_RESULTS.md` —
   both categories fired the frozen decision rule ("CONFIRMED" per its mechanical
   adjudication), with the rule's *paired interpretation withdrawn* 2026-07-19 (same-seed
   arms are not initialization-paired; manuscript §5.3): the primary supported analysis is
   the post-hoc independent-arm Welch (the earlier 'conservative' characterization is retracted), both 95% CIs excluding zero; the
   treatment is the FIR-plus-initialization/optimizer package). Comparator ablations **complete** (5-seed × 2 arms, manuscript §5.2):
   the fixed moving-average arm keeps ~59% of the gain — an observation confounded by the shared singular start (§3): no learned-shape attribution is claimed; the zero-init gate comparison is confounded by the singular-initialization bootstrap. Artifacts: `results_FIRABL_*` (manifest family `tableV2conf`/FIR
   cells).
3. **Office_Products — V1 VOID stands; V3 PASSED (the second counted per-category
   point-estimate comparison).**
   The V1 pre-declaration is **VOID under its floor check** and stays VOID — descriptive
   only, counted in no claim; the floor anomaly is mechanistically explained (their own
   SASRec run locally lands +13.9% above its published row; their Office HSTU-BLaIR row
   regenerates locally at +1.6%) and no post-hoc result restores a voided pre-declaration
   (`SOTA_CONFIRM_PREREG_OFFICE.md`, `SOTA_CONFIRM_OFFICE_RESULTS.md`, Appendix A.0,
   `THEIRS_ON_OURS_REPORT.md`). The **redesigned V3 pre-declaration PASSED**
   (`PREREG_OFFICE_V3.md` + ERRATUM E1; `OFFICE_V3_RESULTS.md`): fresh never-inspected
   seeds 20260728–32, gate vs the environment-matched local regeneration (0.0279 > published
   0.0271) — K=16 CI-LB **0.03033**, K=8 CI-LB **0.03024**, 10/10 seeds above both
   references. Claim capped at the frozen wording: per-category point-estimate comparison;
   no paired superiority; not SOTA of any kind.
   Also under this item: the **MI frequency-5 tail case** +
   thinning-intervention evidence (intervention-scoped wording) is unchanged.
4. TAPE as a modest secondary component; negative results labeled exploratory unless multi-seed.
5. Reproducibility: provenance manifests, per-user sidecars (MI tracked; Office/FIR-breadth
   per-user sidecars local-only/untracked, not part of any counted claim), clean-rebuild
   demonstration, and the fail-closed artifact gate below. **Sidecar deposit policy:** the
   tracked-artifact boundary is the reproducibility contract (every printed claim recomputes
   from tracked, hash-manifested artifacts); local-only per-user sidecars are supplementary
   audit material, hash-pinned in tracked run manifests, provided on editorial/reviewer
   request and deposited as supplementary material upon acceptance (paper §8).

## Canonical artifact graph

- Prereg chain: `SOTA_CONFIRM_PREREG_V2.md` (+ `_ERRATA`), `SOTA_CONFIRM_PREREG_OFFICE.md`,
  `PREREG_OFFICE_V3.md` (+ ERRATA E1/E2; results `OFFICE_V3_RESULTS.md`),
  `PREREG_FIR_BREADTH.md` (results `FIR_BREADTH_RESULTS.md`)
- Results of record: `_bestrec_run/results_SOTACONF_V2_*.json` (+ tracked sidecars +
  `SOTACONF_V2_sidecar_manifest.json`), `_bestrec_run/rebuild_v2/`, `results_OFFICE_*`
  (present; descriptive/VOID), `results_FIRABL_*` (present), `results_OFFICEV3_k{16,8}_seed*.json` (+ per-run tree-state sidecars), `_bestrec_run/results_FIRB_*` (20 tracked breadth runs), the reference-implementation run
  artifacts `_bestrec_run/theirs_runs/*/metrics.jsonl` (+ `run_meta.json`, preprocess
  provenance), and the per-table source families enumerated in
  `_bestrec_run/hstu_results_manifest.json` (15 required claim families)
- Table generation (fail-closed): `_bestrec_run/build_hstu_tables.py` regenerates every
  empirical table from the manifest; **`--submission` exits nonzero** on any UNTRACEABLE cell,
  any printed-numeral MISMATCH, or any required claim family without sourced cells
  (invariants: 0 mismatch / 0 untraceable / all 15 required families sourced; the authoritative cell count is the strict build's own output — 175 at this writing, and it grows as evidence lands)
- Canonical one-command verification: `python _bestrec_run/rebuild_hstu_submission.py --strict`
  (parity test → strict `--submission` build → release-manifest verification → MI V2
  adjudicator → **Office V3 adjudicator (counted; build fails unless CAMPAIGN VERDICT:
  PASS)** → **TFV2 repaired-estimand adjudicator (counted integrity gate; Git-declared frozen rules; outcome-visible — not confirmatory, §5.3 disclosure (vii); ALL PASS required)** → **FIR-breadth frozen-rule adjudicator (artifact-integrity; paired interpretation withdrawn)** →
  Office V1 adjudicator (descriptive/VOID, non-gating)) — passes end-to-end at the
  submitted commit; `update_release_manifest.py --verify-git <intended_deposit_tag>`
  additionally checks the manifest against the git blobs at the deposit tag
- Parity: `_bestrec_run/test_hstu_parity.py` + `HSTU_PARITY_REPORT.md` (bitwise-exact core
  block) and the reference-implementation shim harness `_bestrec_run/fbgemm_shims.py` +
  `theirs_*.py` (`THEIRS_ON_OURS_REPORT.md`)
- Adjudicators: `summarize_sota_confirm_v2.py`, `office_prereg_tools.py` (idempotent appends;
  output carries the VOID banner)
- Release/provenance: `RELEASE_MANIFEST.json` — split/cache/protocol/result AND
  submission-doc/PDF/parity-artifact hashes, kept in sync **mechanically**: the strict
  wrapper runs `update_release_manifest.py --verify` and fails the gate on any drift;
  regenerate with `--regen` (+ commit together) whenever a manifested file changes.
  GitHub releases: `v0.9-audit-evidence` (data/result/parity assets) and the **current
  deposit tag** — `v1.1.11-deposit` at this writing (2026-07-21; supersedes `v1.1.10-deposit`, which went stale to post-tag content commits the same day); each deposit release supersedes the
  previous (`v1.0`→`v1.1`→…→`v1.1.8`→`v1.1.9`), built by the tracked
  `_bestrec_run/build_deposit_bundle.py` (`DOI_DEPOSIT_INSTRUCTIONS.md`)
- Audits + responses: `CLAUDE_SOTA_*AUDIT*.md`, `STRICT_*AUDIT*.md` (incl.
  `STRICT_RESUBMISSION_AUDIT_ROUND2_2026-07-11.md`), `RESPONSE_TO_*.md`

Old-track artifacts (`archive_noncanonical/`, `_bestrec_sota_lab/paper_draft/`) feed nothing here.

## Noncanonical root-level PDFs (disambiguation note, 2026-07-19)

Three legacy PDFs at the repository root are **not** part of this submission and must not be mistaken for submission artifacts: `BERT-Embedded Self-attention Transformer Recommender (BEST-Rec)_ Tackling Sparsity and Cold-Starts.pdf`, `BEST_Rec_v4_Sections_3-8.pdf`, and `BEST_Rec_v4_Sections_3-8_Elaborated.pdf` — they are the maintainer's separate earlier manuscript line (noncanonical, unmanifested, never cited by the canonical papers; disposition is the maintainer's call). The only canonical root PDF is `PAPER_SUBMISSION.pdf` (reader rendering); the venue artifact is `paper_tex/PAPER_TORS.pdf`.

## Pre-declared post-v1.1.11 additions (2026-07-22/23)

Registered here so the claim ledger stays canonical; each entered ONLY through its frozen pre-declaration committed before launch, and each may only narrow further. The FORBIDDEN wordings above remain in force unchanged.

1. **E-A (PREREG_FIR_V3, verdict W-POS):** learned FIR taps vs identity control, +0.002265 [+0.001928, +0.002602] NDCG@10 (MI, frozen V2 config, 8 fresh seeds/arm, per-seed init-state hash equality verified; weight-decay pathway ruled out, A2−A1 p=.95). Supports a FIR-specific component; does NOT retroactively decompose the historical package estimate. Artifacts: results_MI_FIRV3_*, fir_v3_adjudication.json.
2. **E-F (PREREG_HYBRID_V1, verdicts W-H-POS on MI/IS/VG):** late z-score fusion with train-only EASE changed test NDCG@10 by +0.00244 [+0.00219, +0.00268] (MI), +0.00261 [+0.00211, +0.00310] (IS), +0.00317 [+0.00286, +0.00348] (VG); five fresh seeds each; significance attaches to fused-vs-sequential only. Pre-declared point-estimate rows: MI fused five-seed mean 0.04399 exceeds the published single-run 0.0406; VG 0.07031 remains below 0.0760; MI ensemble5 0.04557 (ensemble frame). Artifacts: results_*_HYBRIDV1_*, hybrid_v1_adjudication.json.
3. **E-G (PREREG_COLDFUSE_V1) — OUTCOME-VISIBLE, PROTOCOL-DEVIATED; NO confirmatory status; descriptive estimates only (reclassified per audit 2026-07-23 15:59).** The no-interim clause was violated (mid-campaign endpoint commits/reports); the LITERAL frozen Gate 5 FAILS MI and VG and governs; the amended gate/adjudicator postdate 24/25 outcome visibility (sensitivity only; v1/v2/v3 all preserved with hashes). Descriptive tail-bin estimates: +0.00217 (MI), +0.00243 (IS), +0.00337 (VG), +0.00114 (Office), +0.00481 (CDs); near-threshold sparse-warm redistribution (frequency-0 never moved; mid/head means negative); intervals are optimizer-seed intervals on one exposed split. NOTHING here is counted. E-G2 (the intended clean replication) is ALSO now EXPOSED/protocol-deviated — a git add -A on commit df5afc9f swept 14 in-progress COLDFUSE2 confirm artifacts to the public branch before its one-time adjudication (audit 2026-07-23 22:00) — so it cannot be counted either; the sole remaining path is a future repository-sequestered E-G3. Artifacts: results_*_COLDFUSE_*, coldfuse_v1_adjudication.json (+ preserved v1/v2 outputs), GATE5_CONFORMANCE_DECISION.md.
