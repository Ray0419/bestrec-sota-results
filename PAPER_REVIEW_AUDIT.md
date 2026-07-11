# Paper Review Audit

This file is cumulative. Each run should add a timestamped section, keep the
prior rejection-risk list current, and distinguish confirmed problems from
plausible risks.

## Current Prioritized Rejection-Risk List

1. **Confirmed moderate literature/novelty wording problem: stale "first to
   report numbers" / "only published AR2023" claims.** `PAPER_SUBMISSION.md`
   line 282 still says "where we are the first to report numbers" for AR2023
   5-core LLOO, and Appendix A.3 line 619 says BLaIR is the only published work
   using AR2023. This is no longer defensible as written: HSTU-BLaIR is already
   the manuscript's own AR2023 5-core reference; 2026 SID-line papers such as
   SID-MLP and Latte report AR2023 5-core leave-one-out numbers on the same
   MI/VG dataset statistics; ReSID/ChronoSID report a nearby but different
   filtered AR2023 universe. Fix by deleting "first" language and replacing it
   with a precise protocol-family comparison.
2. **Confirmed citation/readiness problem: named prior-art methods are missing
   from References.** The paper names TiSASRec, VQ-Rec, ProtoMF, MELT,
   DropoutNet, CLCRec, ReSID, ChronoSID, and SASRecText-related artifacts in
   the body/table, but the References section does not contain bibliographic
   entries for those named works. Add full references before submission,
   especially for any method used in the novelty-boundary table.
3. **Plausible moderate related-work coverage gap: the 2026 semantic-ID /
   generative-retrieval paragraph is too narrow.** It says "two recent" methods
   and only discusses ReSID/ChronoSID. At minimum, add SID-MLP (arXiv
   2605.12617) and Latte (arXiv 2605.06331), and state that their reported
   MI/VG numbers do not overturn the HSTU-BLaIR-family comparison but do
   invalidate any "first report" framing.
4. **Plausible wording risk: "reproduces" vs "regenerates".** The manuscript
   correctly caveats the local reference-implementation runs as unpinned,
   environment-caveated, single-run regenerations. Keep avoiding language that
   implies a faithful official reproduction, especially for the MI best-epoch
   comparator match and the Office HSTU-BLaIR descriptive run.
5. **Persistent scientific boundary: no broad SOTA, no paired superiority.**
   The current paper respects this boundary. Any future abstract, conclusion,
   release note, or venue cover letter must keep Video_Games as competitive but
   not SOTA; MI as a per-category point-estimate comparison; and Office as VOID
   / descriptive only.
6. **Submission-readiness risk: venue formatting remains unresolved.** The PDF
   is readable and regenerated, but not yet in a target venue template.

## Audit Run - 2026-07-12 07:28 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `a889053` (`Respond to PAPER_REVIEW_AUDIT run 1 (cumulative format): all 3 confirmed problems fixed, open questions answered`)
- Tracked working tree after verification: clean.
- Automation last-run cutoff supplied by the runner: `2026-07-11T20:24:42.912Z`
  (= 2026-07-12 06:24:42 Australia/Sydney). Only
  `_bestrec_run/hstu_tables.json` had a newer mtime; strict rebuild rewrote it
  and the tracked tree remained clean.
- Canonical manuscript source/artifact found:
  `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, `PAPER_DRAFT.md`,
  `CANONICAL_SUBMISSION.md`, `RELEASE_MANIFEST.json`, `_bestrec_run/*`.
- PDF artifact exists (`PAPER_SUBMISSION.pdf`, 813,880 bytes, last written
  2026-07-12 04:26:17). Fresh `pdfinfo` inspection failed on this Windows
  environment with "The system cannot find the path specified"; this run did
  not perform a fresh visual PDF render.

### Verdict

**Scientific core remains conditionally defensible, but the literature framing
needs revision before top-journal submission.** The strict artifact gate passes
and the paper still avoids broad SOTA / paired-superiority claims. However, the
current source contains stale priority/novelty wording that a reviewer can
falsify quickly from current AR2023 generative-recommendation papers.

**Artifact package: improved since the prior audit.** The previous cell-count
and manifest-scope problems are resolved.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU parity OK.
  - PASS: submission table build green, **164 cells**, 0 `MISMATCH`, 0
    `UNTRACEABLE`, all 12 declared claim families sourced.
  - PASS: `RELEASE MANIFEST VERIFY: OK (111 files verified, 0 release-asset
    files not local)`.
  - PASS: MI V2 dual gate.
  - PASS: Office adjudication remains descriptive/VOID.
- `git status --short`
  - Clean before and after strict rebuild.
- `rg`/`Select-String` checks:
  - Confirmed no stale "163 cells" in `CANONICAL_SUBMISSION.md`.
  - Confirmed `RELEASE_MANIFEST.json` has a `reference_runs` section hashing
    local reference-run artifacts, including `office_hstu_blair`.
  - Confirmed `.gitignore` excludes `/_paper_render.html` and `/tmp/` under a
    "never release-swept" scratch comment.
  - Located stale literature wording in `PAPER_SUBMISSION.md:282` and
    `PAPER_SUBMISSION.md:619`.
  - Located missing-reference candidates in body/table mentions:
    TiSASRec, VQ-Rec, ProtoMF, MELT, DropoutNet, CLCRec, ReSID, ChronoSID,
    SASRecText.

### Confirmed Fixes Since Prior Audit

1. **Stale table-cell count fixed in canonical source.** `CANONICAL_SUBMISSION.md`
   now points to strict-build invariants and says the authoritative count is the
   build output; the current strict output is 164 cells.
2. **Office HSTU-BLaIR reference-run artifacts are now manifest-scoped.**
   `RELEASE_MANIFEST.json` contains a `reference_runs` section with hashes for
   the three local reference-implementation runs, including
   `_bestrec_run/theirs_runs/office_hstu_blair/*`; strict verification now
   checks 111 files.
3. **Render scratch is explicitly ignored.** `.gitignore` excludes
   `/_paper_render.html` and `/tmp/`, reducing accidental release-sweep risk.

### Confirmed Problems

1. **Stale "first to report numbers" claim.** `PAPER_SUBMISSION.md:282` says:
   "Among methods evaluated on the AR2023 5-core LLOO protocol (where we are
   the first to report numbers)..." This conflicts with:
   - HSTU-BLaIR, already used as the paper's own AR2023 5-core comparator.
   - SID-MLP (arXiv:2605.12617), which reports AR2023 5-core LLOO statistics
     matching this paper's MI/VG universe (MI 57,439 / 24,587 / 511,836; VG
     94,762 / 25,612 / 814,586).
   - Latte (arXiv:2605.06331), which reports the same MI/VG/Scientific
     statistics and AR2023 LLOO setup.
   Fix: delete the parenthetical or narrow it to the exact model/artifact claim
   being made; do not claim first protocol numbers.
2. **Appendix A.3 contradicts the body and current literature.**
   `PAPER_SUBMISSION.md:619` says "BLaIR ... is the only published work using
   AR2023." The body itself cites HSTU-BLaIR as the relevant AR2023 5-core
   reference, and the 2026 literature now includes additional AR2023 papers.
   Fix: rewrite this appendix note as historical/superseded and say no
   *comparable Beauty_and_Personal_Care 5-core number* was found, rather than
   saying BLaIR is the only AR2023 work.
3. **References section is incomplete relative to named prior art.** Any
   top-journal reviewer checking Table 0 will expect full bibliographic entries
   for every named method. Add full references for all named methods or remove
   names that are not essential.

### Plausible Risks Requiring Author Verification

- The ChronoSID sentence says its output-level MI table is "five-run averages."
  The source table reports paired-bootstrap confidence intervals for the
  ReSID-vs-ChronoSID output-level comparison; verify whether "five-run averages"
  is supported elsewhere or delete that phrase.
- The phrase "A faithful HSTU implementation" in `PAPER_SUBMISSION.md:264`
  could be misread against the later "HSTU-style pure-PyTorch implementation"
  and shimmed reference-regeneration discussion. Consider rephrasing to
  "faithful pinned-environment HSTU-BLaIR reproduction" to keep the boundary
  precise.
- `pdfinfo`/visual PDF check was not completed in this run. If this audit is
  used for final submission readiness, rerender or visually inspect the PDF
  after the literature/reference edits.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public repository reports the key comparator rows used in the
  manuscript: Video Games HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271,
  and Musical Instruments 0.0406; it also states expected small reproduction
  variability. Source: https://github.com/snapfinger/HSTU-BLaIR
- ReSID (arXiv:2602.02338) evaluates Amazon Reviews 2023 subsets and reports a
  different MI filtered universe (57,359 users / 23,742 items / 490,522
  interactions) plus MI N@10 0.0346 in its main results table. Source:
  https://arxiv.org/html/2602.02338v1
- ChronoSID (arXiv:2607.03918) uses the same ReSID-style MI/VG universe and
  reports MI N@10 0.0346 in its main table, plus an output-level table with
  ReSID 0.0325 vs ChronoSID 0.0345. Source:
  https://arxiv.org/html/2607.03918v1
- SID-MLP (arXiv:2605.12617) is a relevant 2026 generative-recommendation
  paper using AR2023 5-core leave-one-out; its dataset statistics match the
  HSTU-BLaIR-family MI/VG statistics in this manuscript. Its N@10 numbers are
  lower than this paper's MI/VG results, so it does not overturn the claimed
  empirical margin, but it does invalidate "first report" wording. Source:
  https://arxiv.org/html/2605.12617v1
- Latte (arXiv:2605.06331) also uses AR2023 Instruments/Scientific/Games LLOO
  statistics matching the same MI/VG universe and reports N@10 0.0331
  (Instruments) and 0.0515 (Games). Source:
  https://arxiv.org/html/2605.06331v1

### Concrete Fixes To Make Next

1. Replace `PAPER_SUBMISSION.md:282` with a protocol-scoped statement such as:
   "Among our HSTU-style full-catalog AR2023 5-core LLOO runs, the model is a
   compact, reproducible baseline..." Do not use "first to report numbers."
2. Rewrite Appendix A.3 item 4 to remove "BLaIR is the only published work using
   AR2023"; preserve only the narrower Beauty_and_Personal_Care comparability
   point if still true after a fresh search.
3. Add full reference entries for TiSASRec, VQ-Rec, ProtoMF, MELT, DropoutNet,
   CLCRec, ReSID, ChronoSID, SID-MLP, Latte, and any other named method in
   Table 0/body prose.
4. Expand the 2026 semantic-ID/generative-retrieval paragraph to include
   SID-MLP and Latte, explicitly separating:
   - HSTU-BLaIR-family same-stat AR2023 5-core LLOO comparators.
   - ReSID/ChronoSID filtered-universe SID-line comparators.
   - Older Amazon 2014 TIGER/LIGER results.
5. Rerender and visually inspect `PAPER_SUBMISSION.pdf` after these text edits.

### Open Questions

- Is the Beauty_and_Personal_Care "first such reported number" claim still
  intended? It may be defensible only under a very narrow exact-universe
  definition; otherwise it should be softened to "we did not find a comparable
  public number."
- Should the paper cite very recent arXiv-only 2026 work in the main related
  work, or move it to a "concurrent and recent preprints" paragraph to avoid
  over-weighting unreviewed papers while still being complete?

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Read prior automation memory and prior cumulative audit.
- [x] Check files modified after the automation last-run cutoff.
- [x] Verify strict rebuild and release manifest.
- [x] Confirm prior audit's cell-count and manifest findings are resolved.
- [x] Fact-check comparator and novelty claims against current primary sources.
- [x] Identify stale first/only AR2023 wording.
- [x] Identify missing-reference candidates.
- [ ] Remove/soften stale first/only AR2023 claims.
- [ ] Add missing bibliographic references.
- [ ] Rerender and visually inspect the PDF after text edits.

## Audit Run - 2026-07-12 04:28 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch: `codex/bestrec-sota-results`
- HEAD at final verification: `3ca9617` (`Regenerate RELEASE_MANIFEST after Office HSTU-BLaIR integration`)
- Manifest boundary: `RELEASE_MANIFEST.json` records `git_commit =
  815259016ca78c11077e7834040eb25a76f3873a`, which is the parent of current
  HEAD. This matches the manifest's stated "manifest cannot hash itself;
  containing commit is immediate child" rule.
- Tracked working tree after verification: clean.
- Untracked scratch still present: `_paper_render.html`, `tmp/pdfs/...`.

### Verdict

**Narrow scientific core: still conditionally acceptable.** The paper now has a
defensible claim boundary: causal FIR as an incremental, leak-free adaptation;
dataset-conditional text/tail pattern; MI per-category point-estimate
comparison; Office descriptive/VOID; no Video_Games or broad SOTA claim.

**Artifact package: minor revision.** The strict rebuild passes, the manifest
verification passes, and the completed Office HSTU-BLaIR run is disclosed with
the right caveat. The remaining issues are documentation/manifest hygiene rather
than result invalidation.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU parity OK.
  - PASS: submission table build green, **164 cells**, 0 `MISMATCH`, 0
    `UNTRACEABLE`, 12/12 families sourced.
  - PASS: `RELEASE MANIFEST VERIFY: OK (96 files verified)`.
  - PASS: MI V2 dual gate.
  - PASS: Office adjudication remains descriptive/VOID.
- `uv --project _bestrec_run run python _bestrec_run/test_pinned_env_parity.py --mode pinned`
  - Correctly fails closed on Windows without real `fbgemm_gpu` instead of
    silently using shims.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py --verify`
  - PASS at final state.
- `git ls-files _bestrec_run/theirs_runs/office_hstu_blair ...`
  - Confirms `office_hstu_blair.log`, `metrics.jsonl`, `run_meta.json`, gin
    config, and intended TensorBoard-log pointer are tracked.
- `rg "163 cells|164 cells|cells recomputed" ...`
  - Finds stale `163 cells` text in `CANONICAL_SUBMISSION.md` and
    `RESPONSE_TO_RESUBMISSION_AUDIT_ROUND3_2026-07-12.md`.
- `rg "office_hstu_blair|theirs_runs/office" RELEASE_MANIFEST.json`
  - No explicit top-level manifest entry for the completed Office HSTU-BLaIR
    run artifacts.

### Confirmed Fixes Since Prior Audit

- The active Office HSTU-BLaIR run is no longer hidden local state. It completed
  and is integrated into `PAPER_SUBMISSION.md`, `THEIRS_ON_OURS_REPORT.md`, and
  `_bestrec_run/hstu_results_manifest.json`.
- The completed Office HSTU-BLaIR result is reported cautiously:
  final NDCG@10 0.0275, best full eval 0.0279, vs published 0.0271. The paper
  correctly says this regenerates the published row within a small margin and
  **does not** un-void the preregistered Office result.
- The earlier inference that all published Office rows might be conservative is
  corrected: the local Office SASRec row is conservative relative to its
  published row (+13.9%), but Office HSTU-BLaIR only regenerates at +1.6%.
- The release manifest is current at the committed boundary and the strict
  wrapper now verifies it.
- The pinned-parity script's dangerous fallback is fixed: pinned mode refuses to
  treat shim fallback as publication evidence.

### Confirmed Problems

1. **Stale 163-cell text.** Update both stale locations to 164 cells or remove
   the exact cell count from prose. This is low effort and should be fixed before
   another release/deposit bundle.
2. **Top-level artifact manifest coverage is incomplete for the new local
   Office HSTU-BLaIR run.** This is not caught by `update_release_manifest.py
   --verify` because those run files are not currently in the top-level manifest
   scope. Either add hashes for:
   `_bestrec_run/theirs_runs/office_hstu_blair/metrics.jsonl`,
   `run_meta.json`, `hstu-sampled-softmax-n512-blair.gin`,
   `tb_logdir_intended.txt`, and `office_hstu_blair.log`; or add an explicit
   manifest note that these are git-tracked source artifacts governed by
   `_bestrec_run/hstu_results_manifest.json`, not release-manifest assets.
3. **Untracked render scratch remains.** `_paper_render.html` and `tmp/pdfs/*`
   are acceptable as local scratch, but should not be accidentally swept into a
   release unless intentionally archived.

### Plausible Risks Requiring Author Verification

- `CANONICAL_SUBMISSION.md` line describing the table generator says the
  "current state" is 163 cells. Because strict build now prints 164 cells, this
  could be read as a stale canonical state declaration.
- The paper's Section 5.6 table is now stronger, but the surrounding wording
  must continue to separate three concepts: published comparator point,
  unpinned local regeneration, and faithful pinned reproduction. The current
  caveat is adequate; do not shorten it for space without preserving that
  distinction.
- The DOI/deposit bundle should be checked after any manifest-scope change. The
  strict gate verifies current repo files, but the external release asset
  contents are only as good as the archived bundle.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR is a real 2025 comparator source and reports the key Amazon Reviews
  2023 5-core numbers used by the manuscript: Video_Games HSTU-BLaIR NDCG@10
  0.0760, Office_Products 0.0271, and Musical_Instruments 0.0406 in its results
  table. Source: https://arxiv.org/html/2504.10545v3
- HSTU is the relevant base architecture source and makes strong claims about
  generative recommenders and HSTU efficiency/quality. Source:
  https://arxiv.org/abs/2402.17152
- BLaIR introduced Amazon Reviews 2023 and the recommendation-specialized text
  encoders used by the comparator family. Source:
  https://arxiv.org/abs/2403.03952
- BSARec explicitly frames Transformer self-attention in sequential
  recommendation as low-pass / oversmoothing and uses Fourier-transform
  inductive bias. This supports the paper's claim that the frequency motivation
  is prior work, not novel. Source:
  https://ojs.aaai.org/index.php/AAAI/article/view/28747
- FMLP-Rec already used learnable frequency-domain filters for sequential
  recommendation. This supports the manuscript's narrow novelty boundary for
  the FIR module. Source: https://arxiv.org/abs/2202.13556
- TIGER uses semantic IDs for generative retrieval and reports SOTA claims on
  earlier Amazon review benchmarks, but those are not the same AR2023 5-core
  protocol. Source:
  https://papers.neurips.cc/paper_files/paper/2023/file/20dcab0f14046a5c6b02b61da9f13229-Paper-Conference.pdf
- LIGER is a relevant generative/dense retrieval comparator family, but its
  contribution is a hybrid retrieval method and not an apples-to-apples AR2023
  5-core LLOO comparator for this manuscript's main numbers. Source:
  https://arxiv.org/abs/2411.18814

### Open Questions

- Should `RELEASE_MANIFEST.json` explicitly include all local
  reference-implementation run artifacts, or is git tracking plus
  `_bestrec_run/hstu_results_manifest.json` the intended provenance layer?
- Will the next deposited release include the completed Office HSTU-BLaIR run
  artifacts, or are those repository-only descriptive artifacts?
- What target venue/template is intended? The current PDF is useful for review,
  but the paper is not yet venue-formatted.

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Inspect current claim boundary and prior response.
- [x] Verify strict rebuild.
- [x] Verify release manifest gate.
- [x] Verify pinned-mode fail-closed behavior.
- [x] Inspect completed Office HSTU-BLaIR disclosure.
- [x] Spot-check novelty/comparator claims against primary sources.
- [ ] Replace stale `163 cells` prose with `164 cells` or remove exact count.
- [ ] Decide whether to top-level hash-manifest the new Office HSTU-BLaIR run
      artifacts.
- [ ] Remove or intentionally archive render scratch files before release.
- [ ] Move to venue template when target venue is chosen.
