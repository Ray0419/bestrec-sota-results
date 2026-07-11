# Response to the Strict Resubmission Audit — Round 3 (2026-07-12)

Audit: `STRICT_RESUBMISSION_AUDIT_ROUND3_2026-07-12.md`. Verdict received: **"Minor revision for
the narrowed paper"** — scientific core approved for the second consecutive round; all remaining
findings are artifact-packaging items. **All five required fixes are executed**, and the
recurring finding class (manifest staleness, F1 in two consecutive rounds) is now **structurally
eliminated** rather than patched again.

## The audit's five required fixes

| # | Required fix | Done |
|---|---|---|
| 1 | Regenerate/supplement `RELEASE_MANIFEST.json` at HEAD incl. pinned-parity evidence and paper/PDF hashes | ✅ **Structural fix, not another one-shot regen**: new tracked tool `_bestrec_run/update_release_manifest.py` (`--regen` / `--verify`); the manifest now carries a `submission_docs` section (both papers, the PDF, all three evidence reports, the parity/shim/wrapper scripts — every file the audit listed) and a `pinned_parity_artifacts` section (9 hashed outputs). **`rebuild_hstu_submission.py --strict` now runs `--verify` as a gate step** — 96 files verified file-by-file, and any future edit to a manifested file fails the strict gate until the manifest is regenerated and committed with it. Staleness can no longer wait for an audit to notice. `CANONICAL_SUBMISSION.md` and `DOI_DEPOSIT_INSTRUCTIONS.md` point at the new boundary. |
| 2 | `--mode pinned` must fail if real fbgemm is unavailable | ✅ Fail-closed: without `fbgemm_gpu`, `--mode pinned` prints a FATAL explanation and **exits 3** (re-verified with the auditor's exact accidental invocation on Windows). A dev fallback exists only behind the explicit `--allow-shim-fallback-for-dev` flag, prints NON-PUBLICATION banners at start and at the gate line, and marks the saved metadata `SHIM-FALLBACK-DEV-NONPUBLICATION`. |
| 3 | Decide the fate of the active Office HSTU-BLaIR run | ✅ **Complete and disclose** (option 1): `THEIRS_ON_OURS_REPORT.md` §4.3 now discloses the run (launched 2026-07-11, in progress, run dir + config named) and pre-commits the outcome handling: it will be integrated as **descriptive/non-confirmatory evidence with the same VOID caveat regardless of where it lands** — it is not and will not be part of any counted claim. **Completed and integrated the same day**: final-epoch NDCG@10 **0.0275** (+1.6%) / best full eval **0.0279** (+2.8%) vs published 0.0271 — **the published Office HSTU-BLaIR row regenerates here**, refuting our own earlier extrapolation that it would be conservative like the SASRec row (+13.9%); the correction is stated in the report (§4.3 + a post-run correction under the original prediction), both papers (§5.6 table row + A.0 addendum), and a new manifest cell (`theirs.office_hstu.ndcg`). Descriptively our (VOID) gate values still sit ≈+9% above both readings; **the VOID stands on procedural grounds** — no post-hoc result, favorable or not, restores a voided pre-registration. |
| 4 | Clean stale notes in `hstu_results_manifest.json` | ✅ All three updated at the source (the note text lives in `build_hstu_tables.py` cell definitions) and the manifest regenerated: the K=1024 and comparator-rerun notes now record their resolutions with dates. The CF1 note deserved special handling — **its complaint was still true and the paper was wrong**: Table 2's CF1 base column printed "V2 / Beauty" while the artifact family is Musical_Instruments. The paper row is corrected to "V2 / MI" in both papers (the manifest note now records the resolution). |
| 5 | Rerun the strict build and re-render the PDF | ✅ PDF re-rendered (37 pp, placeholder scan clean) and the full chain re-run **with the new manifest-verify step included**: parity OK → SUBMISSION BUILD GREEN (163 cells, 0 mismatch, 0 untraceable, 12/12 families) *(cell count as of this response's date; it grows as evidence lands — the strict build's own output is authoritative, 164 at the round-4 update)* → **RELEASE MANIFEST VERIFY: OK (96 files)** → MI dual gate PASS → Office VOID/descriptive → `SUBMISSION REBUILD: PASS`, exit 0. |

## Non-blocking findings

- **F3 (parity artifacts)**: both remedies applied — the report now states the scratch files are
  reproducible intermediates (source of truth = script + the three-leg commands) **and** they are
  archived (`pinned_env_parity_artifacts.zip` on `v0.9-audit-evidence`, SHA256
  `f469d3d8…159fec4b`) and hash-manifested under `pinned_parity_artifacts`.
- **F6 (venue template)**: acknowledged as the final pre-submission step once the maintainer
  picks the venue; table values will continue to be generated from JSON, never retyped.
- **External spot check**: concurred — the paper's explicit non-claims over
  TIGER/LIGER/BLaIR/HSTU-BLaIR stay, and the "Claims I Would Allow / Not Allow" lists match the
  manuscript's claim set exactly (nothing in the allowed list is weakened; nothing in the
  not-allowed list appears anywhere).

## Standing discipline

The claim set can only narrow. The comparator runs remain "environment-caveated single-run
regenerations"; no broad SOTA, no paired superiority, no pinned reproduction, no Office pass.
Every future manuscript or protocol edit must survive `rebuild_hstu_submission.py --strict`,
which now also enforces manifest freshness mechanically.
