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
| 3 | **Manuscript contradictions + stale notes** | `PAPER_SUBMISSION.md` produced (drafting notes/changelogs stripped) and the consistency pass is now *mechanical*: the artifact-graph build recomputes every printed numeral from source artifacts and fails closed on any mismatch (`--submission` mode, currently 163 cells / 0 mismatch / 0 untraceable). The specific contradictions (category list, parity-claim wording, +17.6%, caches line) were fixed under strict-resubmission-audit F5. | **DONE** |
| 4 | **HSTU fidelity conflict** (docstring says 1/√dh + row-norm; comments say neither; code divides by L) | (a) The stale docstring was WRONG and is now corrected to the authoritative spec (no 1/√dh, no softmax, no row-count norm; constant-L division for scale stability, absorbed by post-LayerNorm) — `run_sasrec_sbert.py::HSTULayer`. (b) A **numerical parity test vs the reference repo's research implementation** is being built (`test_hstu_parity.py` + `HSTU_PARITY_REPORT.md`): identical weights/inputs into their block and ours, per-stage max-abs-diff. "Faithful" survives only if the parity test demonstrates it; otherwise renamed per the novelty audit. | **DONE — PARITY DEMONSTRATED**: `test_hstu_parity.py` shows EXACT agreement (max abs diff 0.0, every stage, end-to-end) with the reference research implementation; sole divergence anywhere = LayerNorm eps default (1e-5 vs 1e-6, a constant, 0.0 when equalized). See `HSTU_PARITY_REPORT.md`. |
| 5 | **Comparator limitation too central** | Already narrowed to exactly the externally-approved point-estimate wording (no outperform-HSTU-BLaIR implication beyond it). **Since materially strengthened**: the reference implementation now runs end-to-end locally (research path, three pure-PyTorch data-movement shims, unpinned env — `THEIRS_ON_OURS_REPORT.md`), and its MI HSTU-BLaIR **reproduces the published 0.0406 exactly at its best full-eval epoch** (final 0.0391) — the comparator is a locally-regenerated number, not just a transcribed constant (manuscript §5.6, claim wording unchanged). The remaining stronger option — a pinned-environment rerun on rented compatible GPU (playbook B9, ~$10–50) — stays a user decision. | wording DONE + local regeneration DONE; pinned rerun = USER DECISION |
| 6 | **Uneven statistical evidence** | Every manifest cell carries `evidence_class: confirmatory / exploratory / external` — implemented and populated (100/52/3 across 155 cells), enforced by the build. Table-2 power caption in place. | **DONE** (labeling) |
| 7 | **Negative map underpowered** | Already downgraded (novelty-audit N12 fix): only multi-seed pre-declared negatives carry confirmatory weight; single-seed rows labeled exploratory documentation. The FIR comparator ablations (5-seed × 2 arms) completed and are in the manuscript (§5.2): the learned kernel carries the effect — a frozen causal moving-average recovers only +0.00133 of the filter's +0.00225 gain (non-overlapping bands); freezing the gate at 1 matches the full filter, so the zero-init gate is a training convenience. Both arms manifest-backed. | **DONE** |
| 8 | **Reproducibility polish** | Accepted: gated V2 JSONs predate the sidecar/code-hash manifest fields (disclosed in errata E2; the clean rebuild demonstrates the fields live). Driver polish landed (all three drivers: `set -euo pipefail`, portable `uv --project` invocation with `PYBIN` override, explicit `RESUME=0/1` semantics — strict-resubmission-audit F10). The from-raw-to-tables rebuild test exists as the canonical one-command gate `_bestrec_run/rebuild_hstu_submission.py --strict` (parity test → fail-closed artifact build, 163 cells / 0 mismatch / 0 untraceable / 12 families → MI adjudicator → Office adjudicator) and **passes end-to-end**. | **DONE** |
| 9 | **Archival release** | Release manifest assembled and published: `RELEASE_MANIFEST.json` (SHA256 for 12 splits, 4 caches, 8 protocol files, 51 result artifacts + licensing/regeneration notes) shipped as GitHub release `v0.9-audit-evidence`. The remaining step — a DOI-backed archive (Zenodo/OSF) — is an external publication step that **requires user approval/account**. | **DONE** (DOI = user decision) |
| 10 | **LC2C fairness caveat** | Recorded inside the LC2C track's `NONCANONICAL.md` (DropoutNet-assisted-fusion framing + required ablations) so the caveat travels with that paper if revived. Not part of the canonical submission. | DONE |
| 11 | **Broad SOTA unsupported** | Concurs with the standing position: the canonical claim set (`CANONICAL_SUBMISSION.md`) contains only the narrow, externally-approved claims; broad-SOTA phrasings are on the forbidden list from the third audit. | DONE |
| 12 | **Presentation not submission-clean** | `PAPER_SUBMISSION.md` is the canonical clean copy (notes/placeholders stripped; informal register formalized — "DEAD"→"Rejected", "killed"→"discontinued"); `PAPER_SUBMISSION.pdf` is rendered (36 pp), machine-scanned for placeholders/lab language (clean), and re-rendered after every manuscript change. | **DONE** |
| 13 | **Threats-to-validity too mild** | The limitations section (§6.5) landed covering confirmatory-vs-exploratory, the comparator limitation (now with the §5.6 shimmed-execution scope), category scope, small effects, unequal probe power, synthetic interventions, and the prereg deviation; the ±1 interaction preprocessing difference is disclosed (errata E1, cited in §5.2), and the model-input-hygiene statement (no baseline outputs/scores/embeddings as inputs anywhere in the canonical pipeline) is now a limitations bullet in both papers. | **DONE** |

## Evidence that has since landed (all launched before this audit; statuses final)

- **HSTU parity test** — LANDED: bitwise-exact vs the reference research implementation
  (`HSTU_PARITY_REPORT.md`; finding 4 above).
- **FIR comparator ablations** — LANDED: learned kernel carries the effect; gate is a
  training convenience (manuscript §5.2; finding 7 above).
- **Office_Products pre-registered program** — LANDED with an honest verdict: dual-kernel gate
  values exceed 0.0271 numerically but the prereg is **VOID** (floor check failed); the floor
  anomaly was later fully explained by running the reference implementation's own SASRec locally
  (+13.9% above its published row) and the VOID deliberately retained — manuscript Appendix A.0,
  `THEIRS_ON_OURS_REPORT.md`.
- **Reframe + submission copy** — LANDED: `PAPER_SUBMISSION.md`/`.pdf` (finding 12).
- **Artifact graph** — LANDED and fail-closed: 163 cells, 0 mismatch / 0 untraceable, 12
  required claim families, canonical gate `rebuild_hstu_submission.py --strict` passes.

## The two decisions only the user can make

1. **Comparator rerun on rented compatible GPU** (~$10–50, definitive fix for F5 and the
   strongest possible upgrade to the whole comparison story).
2. **DOI-backed artifact archive** (Zenodo/OSF account) for F9.
