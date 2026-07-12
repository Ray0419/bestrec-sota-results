# CANONICAL SUBMISSION — single source of truth (full-method audit F1; updated for round-2 audit F1, 2026-07-11)

**The one canonical paper:** the HSTU/FIR manuscript — working copy `PAPER_DRAFT.md`,
submission copy `PAPER_SUBMISSION.md` (+ rendered `PAPER_SUBMISSION.pdf` — page count varies by revision; machine-scanned at every render). The ACM/TORS LaTeX under `paper_tex/` is **generated, derived output** (`VENUE_PLAN.md`): regenerated from the canonical markdown + `hstu_tables.json`, never edited divergently.
Everything else is archived (see `archive_noncanonical/README.md`) or marked non-canonical
(`_bestrec_sota_lab/paper_draft/NONCANONICAL.md`).

## The canonical claim set (nothing broader is claimed anywhere)

1. **MI point-estimate result (externally approved; the only counted per-category comparator
   win):** fresh 5-seed CI lower bounds exceed the published HSTU-BLaIR Musical_Instruments
   point estimate (0.0406) for both kernels (K=16 CI-LB 0.04096, K=8 CI-LB 0.04083, 10/10 fresh
   seeds above) — per-category point-estimate comparison, not paired superiority, not general
   SOTA. The comparator has additionally been **locally regenerated** by running the reference
   implementation itself (best full-eval epoch NDCG@10 = 0.0406 exactly; environment-caveated
   single run, §5.6 / `THEIRS_ON_OURS_REPORT.md`) — regeneration, never "official reproduction".
   Evidence: `SOTA_CONFIRM_PREREG_V2.md` → `SOTA_CONFIRM_V2_RESULTS.md` (+ errata).
2. **Causal FIR filter:** multi-seed lever confirmed on two categories (Video_Games +
   Musical_Instruments). Comparator ablations **complete** (5-seed × 2 arms, manuscript §5.2):
   the learned kernel carries the effect (fixed moving-average keeps ~59%); the zero-init gate
   is a training convenience. Artifacts: `results_FIRABL_*` (manifest family `tableV2conf`/FIR
   cells).
3. **Dataset-conditional long-tail pattern** + thinning-intervention evidence
   (intervention-scoped wording). The pre-registered Office out-of-sample program **completed
   with an honest verdict**: gate arithmetic passed numerically but the pre-registration is
   **VOID under its floor check** — Office is **descriptive only, counted in no claim**; the
   floor anomaly is mechanistically explained (their own SASRec run locally lands +13.9% above
   its published row; their Office HSTU-BLaIR row, by contrast, regenerates locally at +1.6%,
   reported descriptively) and the VOID is retained on procedural grounds — the floor check
   failed as written, and no post-hoc result restores a voided pre-registration
   (`SOTA_CONFIRM_PREREG_OFFICE.md`, `SOTA_CONFIRM_OFFICE_RESULTS.md`, paper Appendix A.0,
   `THEIRS_ON_OURS_REPORT.md`).
4. TAPE as a modest secondary component; negative results labeled exploratory unless multi-seed.
5. Reproducibility: provenance manifests, per-user sidecars (MI tracked; Office sidecars
   local-only/untracked, not part of any counted claim), clean-rebuild demonstration, and the
   fail-closed artifact gate below.

## Canonical artifact graph

- Prereg chain: `SOTA_CONFIRM_PREREG_V2.md` (+ `_ERRATA`), `SOTA_CONFIRM_PREREG_OFFICE.md`
- Results of record: `_bestrec_run/results_SOTACONF_V2_*.json` (+ tracked sidecars +
  `SOTACONF_V2_sidecar_manifest.json`), `_bestrec_run/rebuild_v2/`, `results_OFFICE_*`
  (present; descriptive/VOID), `results_FIRABL_*` (present), the reference-implementation run
  artifacts `_bestrec_run/theirs_runs/*/metrics.jsonl` (+ `run_meta.json`, preprocess
  provenance), and the per-table source families enumerated in
  `_bestrec_run/hstu_results_manifest.json` (12 required claim families)
- Table generation (fail-closed): `_bestrec_run/build_hstu_tables.py` regenerates every
  empirical table from the manifest; **`--submission` exits nonzero** on any UNTRACEABLE cell,
  any printed-numeral MISMATCH, or any required claim family without sourced cells
  (invariants: 0 mismatch / 0 untraceable / all 12 required families sourced; the authoritative cell count is the strict build's own output — 164 at this writing, and it grows as evidence lands)
- Canonical one-command verification: `python _bestrec_run/rebuild_hstu_submission.py --strict`
  (parity test → strict `--submission` build → MI V2 adjudicator → Office adjudicator
  (descriptive/VOID, non-gating)) — passes end-to-end at the submitted commit
- Parity: `_bestrec_run/test_hstu_parity.py` + `HSTU_PARITY_REPORT.md` (bitwise-exact core
  block) and the reference-implementation shim harness `_bestrec_run/fbgemm_shims.py` +
  `theirs_*.py` (`THEIRS_ON_OURS_REPORT.md`)
- Adjudicators: `summarize_sota_confirm_v2.py`, `office_prereg_tools.py` (idempotent appends;
  output carries the VOID banner)
- Release/provenance: `RELEASE_MANIFEST.json` — split/cache/protocol/result AND
  submission-doc/PDF/parity-artifact hashes, kept in sync **mechanically**: the strict
  wrapper runs `update_release_manifest.py --verify` and fails the gate on any drift;
  regenerate with `--regen` (+ commit together) whenever a manifested file changes.
  GitHub releases: `v0.9-audit-evidence` (data/result/parity assets) and `v1.0-deposit`
  (DOI-ready archival bundle; `DOI_DEPOSIT_INSTRUCTIONS.md`)
- Audits + responses: `CLAUDE_SOTA_*AUDIT*.md`, `STRICT_*AUDIT*.md` (incl.
  `STRICT_RESUBMISSION_AUDIT_ROUND2_2026-07-11.md`), `RESPONSE_TO_*.md`

Old-track artifacts (`archive_noncanonical/`, `_bestrec_sota_lab/paper_draft/`) feed nothing here.
