# Response to the Strict Full Method and Paper Audit (2026-07-10)

Audit: `STRICT_FULL_METHOD_AND_PAPER_AUDIT_2026-07-10.md` (verdict: reject the *package*;
the narrow V2 MI numeric claim "conditionally usable"). The audit's core diagnosis — multiple
overlapping publication candidates with no canonical artifact graph — is correct and is the
organizing fix. **Path A (the HSTU/FIR manuscript) is chosen as canonical.**

## Point-by-point

| # | Finding | Resolution | Status |
|---|---|---|---|
| 1 | **No canonical submission** (4 tracks) | Path A declared in `CANONICAL_SUBMISSION.md` (canonical claim set + artifact graph). Old BEST-Rec v4 generator + PDF + LC2C-era `tables.json`/`results_manifest.json` moved to `archive_noncanonical/` (with README); LC2C lab paper marked `NONCANONICAL.md` (kept as the audit's Path-B future option, with its fairness caveat recorded there). | **DONE** |
| 2 | **Tables not generated from manifests** | `_bestrec_run/hstu_results_manifest.json` (every table cell → source JSONs + recompute rule + evidence class) + `build_hstu_tables.py` (regenerates all tables from source files; exits nonzero on missing sources, >5e-5 drift, or unmanifested cells) + `hstu_tables.json`. | **DONE**: 155 cells / 10 table families manifested with evidence classes (100 confirmatory / 52 exploratory / 3 external); `build_hstu_tables.py` regenerates every table from source JSONs and exits nonzero on missing/drifting/unmanifested values (failure gates proven). The graph immediately caught **6 numeric mismatches + 2 wrong labels + 4 untraceable values** in the hand-written tables — all now fixed in both paper files (+17.6→+17.5, +8.7→+8.3, ±0.0002→±0.0003 U2, −0.0001→−0.00005 text-sim, ±0.000137→±0.000153, 0.07403 best-epoch excluded as unretained, sampled-1024→512, CF1 label; the three v1-era Table-1a rows annotated UNTRACEABLE with the parity argument re-anchored on traceable floor checks). |
| 3 | **Manuscript contradictions + stale notes** | The reframe pass (novelty-audit response) is producing `PAPER_SUBMISSION.md` with drafting notes/changelogs stripped; a dedicated consistency pass (dataset counts incl. the "two categories" contradiction, seeds, metrics) runs after the artifact graph lands so the generated tables are the source of truth. | IN PROGRESS |
| 4 | **HSTU fidelity conflict** (docstring says 1/√dh + row-norm; comments say neither; code divides by L) | (a) The stale docstring was WRONG and is now corrected to the authoritative spec (no 1/√dh, no softmax, no row-count norm; constant-L division for scale stability, absorbed by post-LayerNorm) — `run_sasrec_sbert.py::HSTULayer`. (b) A **numerical parity test vs the reference repo's research implementation** is being built (`test_hstu_parity.py` + `HSTU_PARITY_REPORT.md`): identical weights/inputs into their block and ours, per-stage max-abs-diff. "Faithful" survives only if the parity test demonstrates it; otherwise renamed per the novelty audit. | **DONE — PARITY DEMONSTRATED**: `test_hstu_parity.py` shows EXACT agreement (max abs diff 0.0, every stage, end-to-end) with the reference research implementation; sole divergence anywhere = LayerNorm eps default (1e-5 vs 1e-6, a constant, 0.0 when equalized). See `HSTU_PARITY_REPORT.md`. |
| 5 | **Comparator limitation too central** | Already narrowed to exactly the externally-approved point-estimate wording (no outperform-HSTU-BLaIR implication beyond it). The two stronger options both need user approval: rent compatible GPU to rerun their pinned repo (playbook B9, ~$10–50), or request author-provided per-split results. Flagged as a user decision. | wording DONE; rerun = USER DECISION |
| 6 | **Uneven statistical evidence** | Every manifest cell carries `evidence_class: confirmatory / exploratory / external` — implemented and populated (100/52/3 across 155 cells), enforced by the build. Table-2 power caption in place. | **DONE** (labeling) |
| 7 | **Negative map underpowered** | Already downgraded (novelty-audit N12 fix): only multi-seed pre-declared negatives carry confirmatory weight; single-seed rows labeled exploratory documentation. The FIR comparator ablations (5-seed × 2 arms, running) add properly-powered rows for the paper's central lever. | DONE (labeling) + IN PROGRESS (5-seed ablations) |
| 8 | **Reproducibility polish** | Accepted: gated V2 JSONs predate the sidecar/code-hash manifest fields (disclosed in errata E2; the clean rebuild demonstrates the fields live). Driver polish (portable `uv run` invocation, `set -euo pipefail`, `--resume` semantics) queued for the release pass; the from-raw-to-tables rebuild test becomes runnable once the table generator lands. | PARTIAL (queued) |
| 9 | **Archival release** | Release manifest (preprocessing scripts, split hashes, caches, result JSONs, sidecars, licenses) to be assembled after Office lands; DOI-backed archive (Zenodo/OSF) is an external publication step — **requires user approval/account**. | USER DECISION |
| 10 | **LC2C fairness caveat** | Recorded inside the LC2C track's `NONCANONICAL.md` (DropoutNet-assisted-fusion framing + required ablations) so the caveat travels with that paper if revived. Not part of the canonical submission. | DONE |
| 11 | **Broad SOTA unsupported** | Concurs with the standing position: the canonical claim set (`CANONICAL_SUBMISSION.md`) contains only the narrow, externally-approved claims; broad-SOTA phrasings are on the forbidden list from the third audit. | DONE |
| 12 | **Presentation not submission-clean** | `PAPER_SUBMISSION.md` (in progress) strips notes/placeholders; PDF rendering + visual inspection is the final step before submission. | IN PROGRESS |
| 13 | **Threats-to-validity too mild** | The limitations section being added (novelty-audit fix #9) already covers: confirmatory-vs-exploratory, unrunnable comparator, category scope, small effects, unequal probe power, synthetic interventions, prereg deviation. Will add: the ±1 interaction preprocessing difference and the no-baseline-as-feature statement (the canonical model uses no baseline outputs as inputs). | IN PROGRESS |

## Evidence still landing (all launched before this audit)

- **HSTU parity test** (kills F4's uncertainty factually) — agent building.
- **FIR comparator ablations** (5-seed fixed-avg / no-gate arms) — on GPU.
- **Office_Products pre-registered program** (out-of-sample tail prediction + dual-kernel gate vs
  published 0.0271, zero category-specific tuning) — chained: preprocessing running now.
- **Reframe + submission copy** — agent editing.
- **Artifact graph** (F2) — agent building.

## The two decisions only the user can make

1. **Comparator rerun on rented compatible GPU** (~$10–50, definitive fix for F5 and the
   strongest possible upgrade to the whole comparison story).
2. **DOI-backed artifact archive** (Zenodo/OSF account) for F9.
