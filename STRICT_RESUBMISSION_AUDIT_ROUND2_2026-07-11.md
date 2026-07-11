# Strict Resubmission Audit Round 2

Date: 2026-07-11

Submission audited: current `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, HSTU/FIR artifact graph, Office VOID repair, official-comparator shim run, release manifest, and strict rebuild wrapper at commit `e6b5c79`.

Reviewer stance: strict, skeptical, and looking for remaining reasons to block publication.

## Verdict

Scientific core: approve the narrow claim set.

Submission package: minor-to-moderate revision required before I would sign off.

This is a major improvement over the previous resubmission. The main scientific blockers from the last audit are addressed:

- HSTU core-block parity passes.
- strict artifact table build passes with zero untraceable values and zero paper mismatches.
- Office_Products is no longer counted as a passed second category; it is explicitly VOID/descriptive.
- Table 1a untraceable rows have been removed from the paper claim path.
- the new reference-implementation run materially improves the comparator story for Musical_Instruments and explains the Office floor anomaly.
- `PAPER_SUBMISSION.pdf` exists and basic placeholder/lab-language checks pass.

I would not reject the paper on the method/result anymore if the claim remains narrow. However, I still would not approve the package as final because several source-of-truth and release-provenance documents are stale or overbroad.

## Commands Rerun

### HSTU parity

```powershell
uv --project _bestrec_run run python _bestrec_run/test_hstu_parity.py
```

Result: PASS. Max absolute difference is 0.0 end-to-end and at each checked stage when epsilon is aligned.

### Strict table build

```powershell
uv --project _bestrec_run run python _bestrec_run/build_hstu_tables.py --submission
```

Result: PASS.

Summary:

- mode: submission
- cells recomputed OK: 163
- retired cells: 4 `REMOVED_FROM_PAPER`
- `MISMATCH`: 0
- `UNTRACEABLE`: 0
- declared claim families sourced: 12

Note: the previously proposed flag `--strict-submission` does not exist. The working strict flag is `--submission`, and the wrapper handles this correctly.

### Full submission rebuild wrapper

```powershell
uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict
```

Result: PASS.

The wrapper reran:

- HSTU core-block parity.
- strict artifact table build.
- MI V2 gate adjudication.
- Office adjudication as descriptive/VOID.

### PDF checks

`PAPER_SUBMISSION.pdf` exists and reports:

- 36 pages
- letter page size
- no PDF encryption
- generated from `_paper_render.html`

I rendered sample pages 1, 3, 10, and 30. The PDF is readable and does not show obvious broken glyphs on sampled pages. Text extraction found no `TBD`, `Format: short`, `killed`, `UNTRACEABLE`, or `MISMATCH` strings.

## What Now Passes

### P1. Fail-closed table build is real

The prior audit's biggest blocker was that the table builder printed warnings but still exited green. This is now fixed for the actual submission mode. The current generated table artifact records:

- `UNTRACEABLE = 0`
- `MISMATCH = 0`
- retired untraceable rows are no longer paper claims

This is a real publication-grade improvement.

### P2. Office is correctly voided

The paper no longer counts Office_Products as a passed confirmatory category. The generated `office_confirmation` table states that Office is VOID under the preregistered floor check, and `PAPER_SUBMISSION.md` keeps Office in Appendix A.0 as descriptive evidence.

This resolves the previous fatal overclaim.

### P3. Office anomaly is now explained without reviving the claim

`THEIRS_ON_OURS_REPORT.md` documents a local run of the reference implementation's own Office SASRec configuration. It lands above the published Office SASRec row, supporting the conclusion that the Office published row is conservative in this environment. The paper correctly keeps Office VOID despite the numerical gate values.

This is the right scientific posture.

### P4. Musical_Instruments comparator story is stronger

The local reference-path run regenerates the Musical_Instruments HSTU-BLaIR NDCG@10 point estimate at best full-eval epoch 0.0406. This improves the MI comparison: the comparator is no longer just a transcribed external number, although the paper correctly caveats the run as environment-caveated and single-run.

### P5. Main claim scope is now defensible

The paper no longer claims broad SOTA. It says:

- Video_Games is competitive, not SOTA.
- MI is a per-category point-estimate comparison, not paired superiority.
- Office is descriptive/VOID.
- tail claims are empirical and AR2023-limited.
- TAPE is minor.

That scope is much closer to publishable.

## Remaining Blocking Or Near-Blocking Findings

### F1. `CANONICAL_SUBMISSION.md` is stale even though it calls itself the source of truth

`CANONICAL_SUBMISSION.md` still says:

- FIR comparator ablations are "in flight."
- Office out-of-sample test is "in flight."
- `results_OFFICE_*` are "pending."
- `results_FIRABL_*` are "pending."

This conflicts with the current paper and artifact graph. Because the file explicitly says it is the "single source of truth," a reviewer or artifact evaluator could reasonably treat the package as internally inconsistent.

Required fix: update `CANONICAL_SUBMISSION.md` to match the current state:

- MI point-estimate claim is the only counted per-category comparator win.
- Office is descriptive/VOID.
- FIR ablations are complete.
- strict table build uses `--submission`.
- results are no longer pending.

Severity: blocking for final artifact submission, easy to fix.

### F2. `RELEASE_MANIFEST.json` is stale relative to current HEAD

`RELEASE_MANIFEST.json` records `git_commit = 5efb3e9`, but current HEAD is `e6b5c79`.

Hash check against current files:

- `_bestrec_run/office_prereg_tools.py`: manifest hash mismatch.
- `_bestrec_run/build_hstu_tables.py`: manifest hash mismatch.

This is expected because later commits changed the strict gate and Office adjudication, but the paper now cites `RELEASE_MANIFEST.json` as the release evidence. A strict artifact reviewer will fail a hash audit if they assume the manifest describes the submitted HEAD.

Required fix: either regenerate `RELEASE_MANIFEST.json` at current HEAD and retag the evidence release, or change the paper wording to say the manifest is for the earlier `v0.9-audit-evidence` artifact snapshot and provide a current-head manifest separately.

Severity: blocking for reproducibility/release claim, easy to fix.

### F3. The paper overstates tracked sidecar coverage

`PAPER_SUBMISSION.md` says:

> result JSONs and per-user sidecars are tracked in the repository with per-file hashes.

This is not fully true for the current package. The Office sidecars exist locally but are ignored and untracked:

- `results_OFFICE_*users.jsonl.gz`: `Tracked=False`, `Ignored=True`.

The MI sidecars are tracked, but the Office sidecars are not. Since Office is descriptive/VOID this is not a scientific blocker, but the sentence is overbroad.

Required fix: rewrite the availability sentence:

> MI confirmation result JSONs and per-user sidecars are tracked with hashes; Office descriptive summary JSONs are manifest-backed, while Office per-user sidecars are local/ignored and not part of the counted claim.

Or track/hash the Office sidecars if the paper wants the broader sentence.

Severity: near-blocking wording/provenance issue.

### F4. The paper still contains one stale Office limitation

`PAPER_SUBMISSION.md` says:

> the second-category pass is VOID under the prereg pending a matched comparator-baseline explanation

But Appendix A.0 and `THEIRS_ON_OURS_REPORT.md` say the matched comparator-baseline explanation is now complete.

Required fix: replace "pending a matched comparator-baseline explanation" with:

> despite the completed matched comparator-baseline explanation; no claim counts Office because the published Office comparator row appears conservative in this environment.

Severity: minor, but embarrassing if left.

### F5. `SOTA_CONFIRM_OFFICE_RESULTS.md` remains noisy and confusing

The Office result file still contains multiple historical `P2 DUAL GATE: PASS` blocks, followed by a note explaining that those are arithmetic-only and that the preregistration is VOID overall.

The final interpretation is now clear enough, but this file remains easy to quote incorrectly.

Required fix: prepend a top-level red-box-style note:

> FINAL STATUS: OFFICE IS VOID UNDER THE PREREGISTERED FLOOR CHECK. Any `P2 DUAL GATE: PASS` lines below are arithmetic-only historical append blocks and are not claim approvals.

Better: move superseded append blocks under an explicit "Historical append log" heading.

Severity: minor-to-moderate artifact hygiene issue.

### F6. PDF formatting is readable but not conference-polished

The PDF is readable and sample pages do not show broken glyphs. However:

- "Explicit non-claims" renders as inline dash-separated bullets on page 30.
- Equations and formulas are Markdown/HTML-style rather than polished LaTeX.
- There are no obvious conference template elements.

This may be fine for an internal submission draft, but not for a top conference camera-ready or journal submission.

Required fix: typeset in the target venue template or at least improve list and equation rendering before actual submission.

Severity: presentation risk, not a scientific rejection.

### F7. The official-comparator shim run is useful but must stay caveated

The reference implementation run is a strong addition, but it is not a pinned-environment reproduction:

- torch 2.11 vs pinned torch 2.2
- RTX 5060 Ti / sm_120 hardware
- pure-PyTorch fbgemm shims
- world-size-1 DDP identity wrapper
- single runs

The paper does caveat this. Do not strengthen the claim beyond "environment-caveated regeneration."

Required fix: none if the current caveats remain. Reject any future edit that turns this into "official reproduction" or "paired superiority."

Severity: watch item.

## Claim Decisions

| Claim | Current decision | Reason |
|---|---:|---|
| Core HSTU block parity | Accept | Exact parity test passes |
| Strict artifact table build | Accept | `--submission` passes with 0 untraceable and 0 mismatch |
| Video_Games result | Accept as competitive, not SOTA | Correctly framed below HSTU-BLaIR |
| MI per-category point-estimate comparison | Accept with caveats | Fresh CI lower bounds exceed 0.0406; comparator locally regenerated at best full eval |
| Office as second-category pass | Reject | Correctly VOID; do not count it |
| Office descriptive evidence | Accept | Manifest-backed, but not counted |
| Tail pattern | Weak accept / cautious | Small effect, AR2023-limited, but now framed as empirical |
| Broad SOTA | Reject | Not claimed cleanly, should remain forbidden |
| Final artifact package | Not yet | stale canonical doc, stale release manifest, sidecar wording |

## Required Final Fixes Before Submission

1. Update `CANONICAL_SUBMISSION.md`.
2. Regenerate or clearly scope `RELEASE_MANIFEST.json` so current-head protocol hashes do not mismatch.
3. Fix `PAPER_SUBMISSION.md` Office limitation line that says the comparator-baseline explanation is pending.
4. Fix the code/data availability sentence about tracked sidecars.
5. Add a top-level final-status note to `SOTA_CONFIRM_OFFICE_RESULTS.md`.
6. Re-render `PAPER_SUBMISSION.pdf` after these edits.
7. Rerun:

   ```powershell
   uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict
   ```

8. Verify:

   - `UNTRACEABLE = 0`
   - `MISMATCH = 0`
   - release manifest hashes match the submitted code or are explicitly scoped
   - no stale `pending` / `in flight` language remains in source-of-truth docs

## Final Reviewer Position

I would no longer reject the narrow paper on scientific grounds.

The paper is not a broad SOTA paper and should never be marketed as one. But as a careful empirical/reproducibility paper about a small causal FIR adaptation, a dataset-conditional tail pattern, and a narrow MI point-estimate comparison, it is now close to passable.

I still withhold final approval of the submission package until the stale canonical file, stale release manifest, sidecar wording, and one stale Office sentence are fixed. These are not deep algorithmic failures anymore; they are final artifact hygiene issues. Fix them, rerun the strict wrapper, and I would approve the narrow submission.
