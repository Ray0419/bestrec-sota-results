# Response to the Strict Resubmission Audit (2026-07-11)

Audit: `STRICT_RESUBMISSION_AUDIT_2026-07-11.md` (verdict: reject/major revision; MI claim
"conditionally usable"; Office pass rejected under its own prereg). The audit's calls are accepted —
most centrally its **F2 ruling: the Office floor check failed, so Office is VOID under the
pre-registration as written**, regardless of how good its gate numbers look. Every finding below is
addressed with work. The two structural demands (fail-closed build, manifest-backed Office) have
now **landed and pass**: the canonical `_bestrec_run/rebuild_hstu_submission.py --strict` chain —
HSTU parity test → fail-closed artifact build (**0 untraceable, 0 paper mismatches, 139 exact + 19
within-rounding, all 11 claim families sourced**) → MI V2 gate adjudicator (PASS) → Office
adjudicator (reported VOID/descriptive) — exits 0 end-to-end.

## Point-by-point

| # | Finding | Resolution | Status |
|---|---|---|---|
| F1 | Build passes with untraceable/mismatched cells; Table 1a rows still used for observations | **Table 1a's three v1-era rows AND every observation derived from them are REMOVED** from both paper files (the +4%-parity sentence, the MiniLM-vs-BLaIR observation, the seed-tightness note, and the Table-1b comparison column that was computed against 0.0551 — now recomputed against the traceable 0.0673). The build gains a `--submission` mode that **exits nonzero** on any UNTRACEABLE or MISMATCH; removed cells are retired as `REMOVED_FROM_PAPER` (kept for provenance history). The gate is live and **passes**: `--submission` exits 3 on any UNTRACEABLE cell, any printed-numeral MISMATCH, or any declared claim family with no sourced cells — self-tested with doctored manifests — and it caught (and refused to waive) one final real error: the paper printed tail-HR anchor 0.0100 where the recompute gives 0.0099266→0.0099; the manuscript was corrected, the expectation updated, and only then did the gate go green. Two stale sentences referencing the removed rows ("retained in Table 1a", the "3-method ablation" contribution bullet) were also fixed in both papers. | **DONE — gate live and GREEN** |
| F2 | **Office violates its own prereg floor check** (+44%) yet was declared PASS | **Accepted and re-adjudicated honestly**: the Office paragraph in both papers now states the floor check FAILED and the second-category pass is **VOID under the prereg** — gate values reported as provisional/non-confirmatory only; the "two of the three categories" claim is retracted to **Musical_Instruments only**; a limitations bullet added. The repair path the audit demands (a matched comparator-baseline run explaining 0.02208 vs 0.0153) is **running now**: the reference implementation's own SASRec configuration is being executed on our exact Office split via a shimmed local port of their research code (`THEIRS_ON_OURS_REPORT.md` when complete). | VOID re-adjudication **DONE**; matched-baseline run **in flight** |
| F3 | Office not manifest-backed | Office family (per-seed final-epoch full-catalog values for k16/k8/ID-only, the floor run, and the pooled tail contrasts) being added to `hstu_results_manifest.json` + generated tables, with the audit's exact recompute rule (`history[-1].test`, assert n_eval=223,308) and a `VOID under prereg floor check` status note on every gate cell. Build fails if the cells drift or go missing. **Landed**: 10 cells in the `office_confirmation` family, every expected value reproduced exactly (k16 0.03042±0.00008 CI-LB 0.03032; k8 0.03033±0.00018 CI-LB 0.03010; ID-only 0.02840±0.00005; floor 0.02208 = +44.3% vs published 0.0153; pooled tail hits z=3.82/5.45/9.89/13.01 @10/20/50/100); gate cells `confirmatory` with the VOID status note, tail cells `exploratory`; the family is in `REQUIRED_FAMILIES`, so its disappearance fails the submission build. | **DONE** |
| F4 | Office headline has no full-user sidecars | Code fixed: every run now also writes a **final-epoch sidecar** (`*.final.users.jsonl.gz`, hashed into the manifest via `user_records_final_{path,n,sha256}`) whenever the final full-catalog eval differs from the best-by-val checkpoint. The Office arms will be re-run under this code (queued behind the comparator-baseline GPU job) to produce n=223,308 sidecars for k16/k8/ID-only. | code **DONE**; rerun queued |
| F5 | Stale contradictions | All four fixed in both files: the "only Video_Games and Beauty… Books deferred" bullet → the true category list with per-category claim status; the "equation-by-equation only / no numerical parity" bullet → core-block parity **demonstrated** (bitwise-exact) with the correct end-to-end non-claim; the leftover "+17.6%" → +17.5%; the caches-availability line → all four categories, hash-manifested via `RELEASE_MANIFEST.json`. | **DONE** |
| F6 | Residual-gap explanation overclaimed | Accepted — all three sites (abstract, contribution 5, §5.5) rewritten to: *the cause of the residual gap could not be isolated; the official end-to-end stack is not executable on this hardware, so kernel numerics, training recipe, feature pipeline, and other system differences remain unseparated.* | **DONE** |
| F7 | Office tail used as pattern support despite VOID P1 | The tail sentence is explicitly non-confirmatory ("reported as pattern evidence, not as a scored prediction") and sits adjacent to the VOID disclosure; no claim summary uses "out-of-sample prediction" for Office. | **DONE** |
| F8 | ReSID/ChronoSID compressed imprecisely | Rewritten to cite each separately: ReSID 0.0346 (its main ranking table, own filtering); ChronoSID 0.0345 vs its ReSID reproduction 0.0325 (output-level table, five-run averages); explicit statement that metrics/protocols are not interchangeable across the SID and HSTU-BLaIR lines. | **DONE** |
| F9 | Presentation/reference hygiene | "(Format: short style)" removed; the placeholder HSTU-BLaIR reference completed with the full comparator-family annotation. The formalization pass is done (informal register removed throughout: "DEAD"→"Rejected" across Table 2, "killed"→"discontinued", the K=512 sampled-softmax label corrected) and `PAPER_SUBMISSION.pdf` is rendered and machine-inspected (placeholder/lab-language scan clean); the PDF is re-rendered after every manuscript change. | **DONE** |
| F10 | Scripts not release-grade | All three drivers hardened: `set -euo pipefail`, portable `uv --project _bestrec_run run python` invocation (env-overridable `PYBIN`), and explicit `RESUME=0/1` semantics replacing silent skip-if-exists. | **DONE** |
| Repair #9 | DOI/archival release | `RELEASE_MANIFEST.json` (SHA256 for 12 splits, 4 caches, 8 protocol files, 51 result artifacts + licensing/regeneration notes) committed and published as GitHub release **`v0.9-audit-evidence`**. DOI-backed deposit (Zenodo/OSF) remains a maintainer decision, documented as pending. | **DONE** (DOI = user decision) |

## The audit's "fastest path" — adopted

The audit recommends: remove Office from the headline until repaired; fail the build closed; delete
untraceable Table-1a claims; submit the narrower paper (causal FIR + MI confirmation + carefully
scoped tail pattern). **All four are done or in execution** — and the Office repair (matched
comparator baseline via the local shimmed port of the reference implementation) is attempted rather
than deferred, because the same run also addresses the long-standing comparator-limitation finding:
if the reference SASRec/HSTU-BLaIR configurations execute locally, the paper gains its first true
comparator distributions on identical splits.

## New since the audit (relevant evidence)

- **Interactive architecture explainer** (for reviewers/readers): a self-contained page walking the
  pipeline — draggable causal-FIR kernel playground, softmax-vs-silu attention demo, TAPE prototype
  scatter, and the results with per-category claim badges that state the exact claim status
  (approved / provisional-VOID / not claimed) — honesty embedded in the pedagogy.
- FIR comparator ablations (5-seed): learned kernel carries the gain (fixed moving-average keeps
  ~59%); the zero-init gate is a training convenience (§5.2 of the manuscript).
