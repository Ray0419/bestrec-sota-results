# Paper Review Audit

This file is cumulative. Each run should add a timestamped section, keep the
prior rejection-risk list current, and distinguish confirmed problems from
plausible risks.

## Current Prioritized Rejection-Risk List

1. **Confirmed minor submission-readiness problem: the 2026 concurrent-preprint
   references are still bare arXiv identifiers.** `PAPER_SUBMISSION.md` now
   cites ReSID, ChronoSID, SID-MLP, and Latte and correctly removes priority
   claims, but the References entries for those four works are not yet full
   bibliographic entries. Before top-journal submission, add authors/titles and
   venue/preprint status, or move them to a clearly labeled "recent preprints"
   note if the venue discourages unreviewed references.
2. **Plausible moderate related-work freshness gap.** A fresh search confirms
   SID-MLP, Latte, ReSID, and ChronoSID are now covered, but AR2023
   recommendation preprints are appearing quickly. Triage other 2026 AR2023
   papers before submission and explicitly explain why they are non-comparable
   if they use different splits, tasks, candidate sets, or LLM-reasoning
   protocols.
3. **Plausible wording risk: "reproduces" vs "regenerates".** The manuscript
   correctly caveats the local reference-implementation runs as unpinned,
   environment-caveated, single-run regenerations. Keep avoiding language that
   implies a faithful official reproduction, especially for the MI best-epoch
   comparator match and the Office HSTU-BLaIR descriptive run.
4. **Persistent scientific boundary: no broad SOTA, no paired superiority.**
   The current paper respects this boundary. Any future abstract, conclusion,
   release note, or venue cover letter must keep Video_Games as competitive but
   not SOTA; MI as a per-category point-estimate comparison; and Office as VOID
   / descriptive only.
5. **Working-tree packaging risk.** This run regenerated
   `PAPER_SUBMISSION.pdf` and `RELEASE_MANIFEST.json` after the branch advanced
   to `9ed7be3`; they are modified and should be committed together with this
   audit if this state is kept.
6. **Submission-readiness risk: venue formatting remains unresolved.** The PDF
   is readable and regenerated, but not yet in a target venue template.

## Audit Run - 2026-07-12 08:31 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD at final verification: `codex/bestrec-sota-results` /
  `9ed7be3` (`Respond to PAPER_REVIEW_AUDIT run 07:28: literature framing
  fixed (no priority claims), references completed`)
- Note: the branch advanced during this automation run from `a889053` to
  `9ed7be3` via commits at 2026-07-12 08:29-08:30 Australia/Sydney. I treated
  the new HEAD as the current workspace state and did not revert it.
- Current modified tracked files after this audit:
  `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`, and this audit file.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/rebuild_hstu_submission.py`, `_bestrec_run/render_paper_pdf.py`,
  and the cumulative audit.

### Verdict

**The previous literature-framing rejection risk is now fixed in the source and
the regenerated PDF.** The stale "first to report numbers", "only published work
using AR2023", and "first such reported number" phrases are gone. The paper now
separates same-statistics AR2023 5-core LLOO preprints (SID-MLP, Latte), the
ReSID/ChronoSID filtered SID universe, and older Amazon-2014 TIGER/LIGER
protocols.

**Scientific core remains conditionally defensible under the narrowed claim
boundary.** The strict gate still passes; Video_Games is not claimed as SOTA,
Musical_Instruments remains a per-category point-estimate comparison, and Office
remains VOID/descriptive.

**Main remaining top-journal risk is polish, not result invalidation.** Full
metadata for the 2026 arXiv-only references and venue formatting remain open.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    claim families sourced.
  - PASS: release manifest verification after regeneration: 111 files verified.
  - PASS: MI V2 gate. K=16 mean 0.04152, CI-LB 0.04096; K=8 mean 0.04120,
    CI-LB 0.04083; both above the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic gates pass, but Office remains descriptive and
    VOID because the preregistered floor check failed.
- `uv --project _bestrec_run run python _bestrec_run/render_paper_pdf.py`
  - Regenerated `PAPER_SUBMISSION.pdf`: 827,780 bytes, 38 pages, placeholder
    scan clean.
- PDF text extraction using `pypdf`:
  - `first to report numbers`: absent.
  - `only published work using AR2023`: absent.
  - `where we are the first`: absent.
  - `first such reported number`: absent.
  - `SID-MLP`, `Latte`, and the revised BLaIR/AR2023 historical note: present.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py --verify`
  - Initially failed only because the regenerated PDF hash differed from the
    manifest.
  - `--regen` refreshed `RELEASE_MANIFEST.json` to `git_commit =
    9ed7be3ee79822fd1bca59fedd29618539aded4b`; final strict verification
    passed.

### Confirmed Fixes Since The 07:28 Audit

1. **Priority/novelty wording fixed.** The manuscript no longer claims to be
   first to report AR2023 5-core LLOO numbers, and Appendix A.3 no longer says
   BLaIR is the only published work using AR2023.
2. **2026 AR2023 coverage expanded.** The related-work/comparability paragraph
   now includes SID-MLP and Latte in addition to ReSID and ChronoSID, and keeps
   the protocol families separate.
3. **Named prior-art references mostly filled.** The References section now has
   entries for TiSASRec, VQ-Rec, ProtoMF, MELT, DropoutNet, and CLCRec, plus
   arXiv-identifier entries for ReSID, ChronoSID, SID-MLP, and Latte.
4. **PDF and manifest refreshed.** The compiled PDF no longer contains the stale
   phrases, and the manifest verifies the regenerated PDF hash.

### Confirmed Problems

1. **Bare references for four recent preprints.** ReSID, ChronoSID, SID-MLP, and
   Latte are currently listed by name + arXiv ID only. That is acceptable for an
   internal audit but weak for a top-journal bibliography.
2. **Working tree is intentionally dirty.** `PAPER_SUBMISSION.pdf` and
   `RELEASE_MANIFEST.json` changed during this run. Keep or commit them with the
   audit; do not mix the regenerated PDF with an older manifest boundary.

### Plausible Risks Requiring Author Verification

- The paper says Latte reports MI NDCG@10 0.0331 and VG 0.0515. I confirmed
  Latte uses the same MI/VG dataset statistics from its arXiv HTML, but the
  exact two NDCG values should be checked once more against the paper's table
  before final submission because the table extraction is brittle.
- The phrase "The Musical_Instruments comparator reproduces" is defensible only
  because the surrounding paragraphs caveat the run as environment-caveated and
  unpinned. If space edits shorten Section 5.6, preserve the caveat.
- The related-work freshness scan was broad, not exhaustive. Triage additional
  2026 AR2023 recommender preprints for relevance before a real submission.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public repository reports the exact comparator values used by the
  paper: Video_Games HSTU-BLaIR NDCG@10 0.0760, Office_Products 0.0271, and
  Musical_Instruments 0.0406, with expected small run variability. Source:
  https://github.com/snapfinger/HSTU-BLaIR
- SID-MLP (arXiv:2605.12617) uses Amazon Reviews 2023 5-core last-out splits and
  reports the same MI/VG dataset statistics as this paper's HSTU-BLaIR-family
  universe: MI 57,439 / 24,587 / 511,836 and VG 94,762 / 25,612 / 814,586.
  Source: https://arxiv.org/html/2605.12617v1
- Latte (arXiv:2605.06331) uses Amazon Reviews 2023 Instruments/Scientific/Games
  leave-one-out and reports the same statistics for Instruments and Games.
  Source: https://arxiv.org/html/2605.06331v1
- ReSID (arXiv:2602.02338) evaluates Amazon-2023 subsets under its own filtered
  universe: MI 57,359 / 23,742 / 490,522 and VG 94,515 / 24,685 / 772,218.
  Source: https://arxiv.org/html/2602.02338v1
- ChronoSID (arXiv:2607.03918) reports an output-level MI comparison with ReSID
  0.0325 vs ChronoSID 0.0345 NDCG@10 and paired-bootstrap confidence intervals.
  Source: https://arxiv.org/html/2607.03918v1
- Amazon Reviews 2023's official site describes the dataset and standard
  processing resources; it is the correct source for dataset-level facts.
  Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Expand the four 2026 preprint references from bare arXiv IDs to full
   author/title entries.
2. Decide whether to include a short "recent preprints" paragraph for other
   2026 AR2023 recommendation papers found by fresh search, or explicitly scope
   the paper to the HSTU-BLaIR/SID-protocol families.
3. Commit `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`, and this audit file
   together if this regenerated artifact state is accepted.
4. Move the manuscript into the target venue template and rerun the PDF visual
   check after formatting.

### Open Questions

- What is the target venue? The current Markdown/Chrome PDF is readable but not
  venue-formatted.
- Does the author want to cite all very recent 2026 arXiv preprints in the main
  paper, or keep only those that directly threaten priority/comparability?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript source and PDF.
- [x] Detect branch advancement and audit the final HEAD.
- [x] Verify stale first/only AR2023 phrases are absent from source.
- [x] Regenerate `PAPER_SUBMISSION.pdf`.
- [x] Verify stale phrases are absent from extracted PDF text.
- [x] Regenerate `RELEASE_MANIFEST.json`.
- [x] Rerun strict submission gate after PDF/manifest refresh.
- [x] Fact-check the key novelty/comparator literature against primary sources.
- [ ] Expand 2026 preprint references to full bibliographic entries.
- [ ] Commit the regenerated PDF, manifest, and audit if this state is kept.
- [ ] Move to target venue formatting.

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
