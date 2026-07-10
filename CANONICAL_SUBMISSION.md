# CANONICAL SUBMISSION — single source of truth (full-method audit F1)

**The one canonical paper:** the HSTU/FIR manuscript — working copy `PAPER_DRAFT.md`,
submission copy `PAPER_SUBMISSION.md` (generated from it, drafting notes stripped).
Everything else is archived (see `archive_noncanonical/README.md`) or marked non-canonical
(`_bestrec_sota_lab/paper_draft/NONCANONICAL.md`).

## The canonical claim set (nothing broader is claimed anywhere)

1. **MI point-estimate result (externally approved):** fresh 5-seed CIs exceed the published
   HSTU-BLaIR Musical_Instruments point estimate (0.0406) for both kernels — per-category
   point-estimate comparison, not paired superiority, not general SOTA.
   Evidence: `SOTA_CONFIRM_PREREG_V2.md` → `SOTA_CONFIRM_V2_RESULTS.md` (+ errata).
2. **Causal FIR filter:** multi-seed lever on two categories (+ comparator ablations, in flight).
3. **Dataset-conditional long-tail pattern** + thinning-intervention evidence (intervention-scoped
   wording), with the pre-registered Office out-of-sample test in flight
   (`SOTA_CONFIRM_PREREG_OFFICE.md`).
4. TAPE as a modest secondary component; negative results labeled exploratory unless multi-seed.
5. Reproducibility: provenance manifests, per-user sidecars, clean-rebuild demonstration.

## Canonical artifact graph

- Prereg chain: `SOTA_CONFIRM_PREREG_V2.md` (+ `_ERRATA`), `SOTA_CONFIRM_PREREG_OFFICE.md`
- Results of record: `_bestrec_run/results_SOTACONF_V2_*.json` (+ tracked sidecars +
  `SOTACONF_V2_sidecar_manifest.json`), `_bestrec_run/rebuild_v2/`, `results_OFFICE_*` (pending),
  `results_FIRABL_*` (pending), the per-table source families enumerated in
  `_bestrec_run/hstu_results_manifest.json`
- Table generation: `_bestrec_run/build_hstu_tables.py` regenerates every empirical table from
  the manifest and FAILS on any value without a manifested source (audit F2)
- Parity: `_bestrec_run/test_hstu_parity.py` + `HSTU_PARITY_REPORT.md` (audit F4)
- Adjudicators: `summarize_sota_confirm_v2.py`, `office_prereg_tools.py`
- Audits + responses: `CLAUDE_SOTA_*AUDIT*.md`, `STRICT_*AUDIT*.md`, `RESPONSE_TO_*.md`

Old-track artifacts (`archive_noncanonical/`, `_bestrec_sota_lab/paper_draft/`) feed nothing here.
