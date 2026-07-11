# Response to the Strict Resubmission Audit — Round 2 (2026-07-11)

Audit: `STRICT_RESUBMISSION_AUDIT_ROUND2_2026-07-11.md`. Verdict received: **"Scientific core:
approve the narrow claim set"** — the first approval of the scientific core by this audit line —
with final sign-off withheld on five artifact-hygiene items. **All five are fixed** (commits
`31ca137` + `978ea9f`), the strict wrapper re-passes end-to-end, and the two non-blocking items
(F6 presentation, F7 watch item) are addressed below.

## The audit's 8-step "Required Final Fixes" checklist — all executed

| # | Required fix | Done |
|---|---|---|
| 1 | Update `CANONICAL_SUBMISSION.md` | ✅ rewritten: MI = the only counted per-category comparator win; Office descriptive/VOID with the anomaly explained and VOID retained; FIR ablations complete; the fail-closed gate is `--submission` (163 cells / 0 / 0 / 12 families); `results_OFFICE_*` and `results_FIRABL_*` present, nothing "pending"/"in flight"; theirs-on-ours artifacts and both releases enumerated |
| 2 | Regenerate/scope `RELEASE_MANIFEST.json` | ✅ regenerated at the submitted commit (`git_commit = 31ca137`, `supersedes_git_commit = 5efb3e9`): **all 67 data entries (12 splits, 4 caches, 51 result-family files) re-verified byte-identical** to the v0.9-audit-evidence release assets; `protocol_code` hashes recomputed — exactly the two files the audit flagged had changed (`build_hstu_tables.py`, `office_prereg_tools.py`), the other six unchanged; an explicit `manifest_scope` field states the self-hash boundary (the manifest's own commit is the immediate child of `git_commit`); regenerated manifest also uploaded to the `v0.9-audit-evidence` release assets |
| 3 | Fix the stale "pending a matched comparator-baseline explanation" line | ✅ limitations bullet now reads *"VOID under the prereg **despite the completed** matched comparator-baseline explanation (§5.6, Appendix A.0) — the published Office comparator row appears conservative in this environment"*; the A.0 sentence with the same leftover construction smoothed as well (both papers) |
| 4 | Fix the sidecar-coverage sentence | ✅ replaced with the audit's suggested scoping in both papers: MI confirmation JSONs + per-user sidecars tracked with hashes; Office descriptive summary JSONs manifest-backed; Office per-user sidecars local-only (untracked) and part of no counted claim |
| 5 | Top-level FINAL STATUS note in `SOTA_CONFIRM_OFFICE_RESULTS.md` | ✅ the file now opens with a blockquote banner: **OFFICE IS VOID UNDER THE PRE-REGISTERED FLOOR CHECK; every `P2 DUAL GATE: PASS` below is arithmetic-only historical append, not a claim approval** (in addition to the earlier mid-file context note and the adjudicator's own in-block banner) |
| 6 | Re-render `PAPER_SUBMISSION.pdf` | ✅ re-rendered after the edits: **37 pages**, placeholder/lab-language scan clean |
| 7 | Rerun the strict wrapper | ✅ `rebuild_hstu_submission.py --strict` → parity OK → strict build **SUBMISSION BUILD GREEN** → MI dual gate **PASS** → Office adjudicated VOID/descriptive (idempotent, no duplicate append) → **SUBMISSION REBUILD: PASS**, exit 0 |
| 8 | Verify UNTRACEABLE=0 / MISMATCH=0 / manifest scoped / no stale language | ✅ 163 cells recomputed, **0 untraceable, 0 mismatches, 12/12 claim families**; manifest hashes match the submitted tree with the self-scope stated; a final grep sweep of the source-of-truth docs finds no stale "pending"/"in flight" language |

## Finding-by-finding

| # | Finding | Resolution |
|---|---|---|
| F1 | `CANONICAL_SUBMISSION.md` stale while claiming source-of-truth status | Fixed (checklist 1). The file now matches the paper, the artifact graph, and the release state exactly. |
| F2 | `RELEASE_MANIFEST.json` stale vs HEAD; two protocol hashes mismatched | Fixed (checklist 2) by the audit's first option — regenerate at the submitted commit — plus the explicit scope note. The two mismatches were precisely the strict-gate/Office-adjudicator files this audit round caused to change; the data evidence is proven unchanged. |
| F3 | Sidecar-coverage sentence overbroad | Fixed with the audit's own suggested wording (checklist 4). We chose scoping over tracking the Office sidecars: they are large, local, and back no counted claim; if Office is ever restored, the sidecar rerun + tracking obligation revives with it. |
| F4 | One stale Office "pending" sentence | Fixed in both sites (checklist 3). |
| F5 | Office results log easy to misquote | Fixed (checklist 5): triple-fenced now — top-of-file FINAL STATUS banner, mid-file context note over the historical blocks, and the VOID banner inside every future adjudicator append (the tool is also idempotent, so the historical duplication cannot recur). |
| F6 | PDF readable but not conference-polished | Partially fixed now; template deferred deliberately. The specific defect named (the "Explicit non-claims" list rendering as inline dashes) was a missing blank line before the list — fixed, and the same bug class swept across both papers (5 sites); the PDF re-render confirms proper list rendering (now 37 pp). Venue-template typesetting (LaTeX equations, conference class) is deferred until the target venue is chosen — a maintainer decision — and is acknowledged as required before actual submission. |
| F7 | Shim run must stay caveated (watch item) | Agreed and enforced. The claim wording is frozen at "environment-caveated single-run regeneration"; the artifact-graph cell notes carry the same language, and `CANONICAL_SUBMISSION.md` now states the non-strengthening rule explicitly ("regeneration, never 'official reproduction'"). Two further evidence streams are running **within** this constraint: (a) their HSTU-BLaIR Office configuration is currently training locally (tests whether the published 0.0271 is also conservative here — either outcome further cements the retained VOID or sharpens its wording; result will be integrated with the same caveats), and (b) the pinned-environment CPU parity check is **complete** (`PINNED_ENV_PARITY_REPORT.md`): under the pinned torch 2.2.2 itself, the real `fbgemm-gpu(-cpu)==0.6.0` operators match our shims **bit-exactly — max abs diff 0.0, forward (23/23 accepted cases) and gradient (5/5)**; the reference block under {pinned torch + real fbgemm} vs {pinned torch + shims} is bit-exact at every stage; the torch 2.2.2→2.11 block drift is bounded at 4.8e-07/stage (2.4e-07 end-to-end); negative controls detect 1-ulp perturbations, so the zeros are not vacuous. The shim objection is thereby closed on CPU; the pinned stack's cu121 **GPU** kernels remain the single locally untestable component (exactly the rented-GPU residual), and single-run training-level equivalence remains unclaimed. Neither stream is or will be cited as a pinned reproduction. |

## Standing items outside the audit's blocking set

- **DOI**: deposit fully prepared locally (`v1.0-deposit` release bundle, `.zenodo.json`,
  `CITATION.cff`, `LICENSE`, `DOI_DEPOSIT_INSTRUCTIONS.md`); minting requires the maintainer's
  Zenodo/OSF login (~3 clicks).
- **Venue template (F6)**: awaits the maintainer's venue choice.
- **Pinned-GPU rerun**: remains the one upgrade only rentable hardware can provide; the CPU
  parity check above is its local approximation, honestly scoped.
