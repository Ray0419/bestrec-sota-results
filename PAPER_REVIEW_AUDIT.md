# Paper Review Audit

This file is cumulative. Each run should add a timestamped section, keep the
prior rejection-risk list current, and distinguish confirmed problems from
plausible risks.

## Current Prioritized Rejection-Risk List

1. **Confirmed major submission-readiness problem: cited figures are not
   embedded in the compiled PDF.** `PAPER_SUBMISSION.md` cites Fig. 1
   (`figures/fig_tail_law_mechanism`), Fig. 2 (`figures/fig_r1r2_plane`), and
   Fig. 3 (`figures/fig_bbp_irreducibility`), but the Markdown source contains
   no image syntax and the rendered PDF has no image objects. The PDF only
   prints filename references. A top-journal submission cannot rely on absent
   figures.
2. **Confirmed moderate submission-readiness gap: no ethics/privacy/data-use
   section.** The paper has code/data availability and limitations, but no
   ethics, privacy, license, or human-subjects/data-governance statement. This is
   risky because AR2023 includes user review text, timestamps, item metadata,
   images, and user IDs.
3. **Confirmed moderate internal-consistency problem: HSTU parity boundary is
   contradicted inside the manuscript.** Table 0 still says the HSTU base is
   "equation-level verification only, no numerical-parity claim", while
   Section 3.7, Section 6.5, and the strict rebuild all claim exact
   core-block numerical parity against the reference research implementation.
   Fix Table 0 to match the current evidence boundary: core-block parity yes;
   pinned end-to-end system reproduction no.
4. **Confirmed moderate related-work freshness gap: GrIT is still absent.**
   GrIT (arXiv:2602.19728, 2026) reports Amazon Reviews 2023 Video_Games 5-core
   statistics matching this paper's protocol family (94,762 users, 25,612 items,
   814,586 interactions), full-item-set ranking, LLOO, and NDCG@10 0.0588. It
   does not overturn the paper's stronger 0.0673 multi-seed result, but a
   top-journal reviewer can fairly object if it is not cited or scoped out.
5. **Confirmed moderate related-work gap: frequency/time-frequency sequential
   recommender line is under-covered.** The paper positions the causal FIR
   adaptation mainly against FMLP-Rec and BSARec. That narrow claim can survive,
   but top-journal reviewers may expect at least a sentence citing FEARec
   (SIGIR 2023), MUFFIN (CIKM 2025), WEARec (AAAI 2026), and/or WPGRec
   (2026 preprint) as the broader frequency/time-frequency SR line. This is a
   novelty-packaging issue, not a result invalidation.
6. **Confirmed packaging-metadata inconsistency: stale page-count prose remains.**
   `CANONICAL_SUBMISSION.md` still says the rendered PDF is 36 pp, while
   `PAPER_SUBMISSION.pdf` is currently 38 pages. `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`
   also contains older 37-page prose in an earlier response section. Do not use
   those files as release/submission metadata without correction.
7. **Plausible packaging-boundary risk.** `RELEASE_MANIFEST.json` records
   `git_commit = 9ed7be3...`, while current HEAD is `5df3d37...`. The strict
   verifier passes for the declared release set, but a release/deposit bundle cut
   from current HEAD should either regenerate the manifest or explicitly state
   that the venue/DOI decision files are outside the release boundary.
8. **Plausible venue-plan risk.** `VENUE_PLAN.md` correctly sequences TORS and
   RecSys to avoid dual submission, but current official evidence only supports
   RecSys 2026 details. Treat the "RecSys 2027, spring 2027" timing as a
   planning assumption until the 2027 call exists. Also ensure TORS review
   formatting follows ACM's current single-column `manuscript` workflow before
   production `acmsmall`.
9. **Plausible wording risk: "reproduces" vs "regenerates".** The manuscript
   correctly caveats the local reference-implementation runs as unpinned,
   environment-caveated, single-run regenerations. Keep avoiding language that
   implies a faithful official reproduction, especially for the MI best-epoch
   comparator match and the Office HSTU-BLaIR descriptive run.
10. **Persistent scientific boundary: no broad SOTA, no paired superiority.**
    The current paper respects this boundary. Any future abstract, conclusion,
    release note, or venue cover letter must keep Video_Games as competitive but
    not SOTA; MI as a per-category point-estimate comparison; and Office as VOID
    / descriptive only.
11. **Submission-readiness risk: venue formatting remains unresolved.** The PDF
    is readable and regenerated, but not yet in a target venue template.

## Audit Run - 2026-07-12 10:31 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `5df3d37` (`Record venue + DOI
  decisions: TORS primary, RecSys 2027 repro secondary (sequenced); DOI
  deferred`)
- Pre-existing working tree state: `PAPER_REVIEW_AUDIT.md` was already modified
  with the 09:37/09:40 audit content. I preserved it and appended this current
  section plus the risk-list refresh above.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `_paper_render.html`, `CANONICAL_SUBMISSION.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `RELEASE_MANIFEST.json`,
  `VENUE_PLAN.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`, `figures/*`, and the strict
  rebuild wrapper.
- Visual PDF check: rendered pages 1, 14, 24, 25, 26, 34, and 38 with
  `pypdfium2` into `tmp/pdfs/hourly_audit_20260712_1030_pypdfium/`. The bundled
  Poppler wrappers (`pdfinfo.cmd`, `pdftoppm.cmd`) are discoverable but still
  fail at runtime with "The system cannot find the path specified."

### Verdict

**No numerical regression; the submission blockers are still presentation,
ethics/data governance, and literature/venue hygiene.** The strict result gate
passes. The current HEAD mostly adds venue/DOI planning, not manuscript
substance, so the previously identified top blockers remain open. A fresh
external check adds one sharper related-work risk: GrIT is a same-protocol-family
2026 AR2023 Video_Games sequential-recommendation paper and is not cited.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 111 files verified.
  - PASS: MI V2 dual gate. K=16 CI-LB 0.04096 and K=8 CI-LB 0.04083 both exceed
    the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and VOID.
- `pypdf` extraction / PDF metadata:
  - `PAPER_SUBMISSION.pdf` has 38 pages, 830,097 bytes, and 0 embedded image
    objects.
  - Extracted PDF text contains `Fig. 1`, `Fig. 2`, and `Fig. 3`, but does not
    contain `Ethics`, `privacy`, `data-use`, `FEARec`, `MUFFIN`, `WEARec`,
    `WPGRec`, or `GrIT`.
- `_paper_render.html` and `PAPER_SUBMISSION.md` scan:
  - No `<img>` tags or Markdown image inclusions for the three cited figures.
  - The figure files exist on disk under `figures/`.
- Visual rendering:
  - Page 1 is readable and not visibly clipped.
  - Table 2 still has the page-break polish defect: page 26 starts with a
    dangling continuation cell (`dv=dqk=16 spec`) before the next row.
- Git/release metadata:
  - Current HEAD is `5df3d37`; `RELEASE_MANIFEST.json` still records
    `git_commit = 9ed7be3...`; `CANONICAL_SUBMISSION.md` still says 36 pp.
  - Final `git status` also shows untracked `paper_tex/` smoke artifacts
    (`acmart.cls`, `ACM-Reference-Format.bst`, `_smoke.tex`, `_smoke.pdf`)
    timestamped during this run window. I did not treat them as canonical paper
    source; they should be triaged before committing or deleting.

### Confirmed Problems

1. **Fig. 1-3 are absent from the PDF.** This is still the single clearest
   top-journal desk/reviewer-facing defect. Add real figure inclusion syntax or
   convert the figures into the generated LaTeX flow, then verify the compiled
   PDF has image/XObject content and sane placement.
2. **No ethics/privacy/data-use section.** AR2023's own documentation describes
   user review text, timestamps, metadata, images, and user IDs, so the paper
   should explicitly state data provenance, public-dataset status, privacy/PII
   handling, license/terms boundary, and whether human-subjects/IRB review is
   not applicable or was not required.
3. **Table 0 still contradicts the HSTU parity evidence.** Change the row from
   "no numerical-parity claim" to the actual boundary: exact core-block parity
   against the reference research implementation; no pinned end-to-end official
   system reproduction.
4. **GrIT is an uncited same-protocol-family comparator.** GrIT's AR2023
   Video_Games statistics match the paper's 5-core family and it reports
   NDCG@10 0.0588. The manuscript should cite it and explain that the present
   0.0673 multi-seed result is higher, while protocol/training details still
   need careful comparability wording.
5. **Venue planning needs a source boundary.** The TORS-first / RecSys-later
   sequence is consistent with ACM no-dual-submission policy, but RecSys 2027
   deadlines are not yet verifiable. Use RecSys 2026 only as precedent, not as a
   hard 2027 claim.

### Plausible Risks Requiring Author Verification

- Whether `VENUE_PLAN.md` should be amended now to say "RecSys 2027 dates TBD"
  instead of "`deadline ~spring 2027`".
- Whether the deposit/release manifest should be regenerated for HEAD `5df3d37`
  or explicitly scoped to the earlier paper-artifact commit.
- Whether GrIT's reported preprocessing/evaluation is close enough to Table 1b
  to include in a numerical comparator table, or only in related work.
- Whether untracked `paper_tex/` smoke artifacts are intended derived-output
  scaffolding for the TORS conversion or should be removed before packaging.

### External Fact-Check / Novelty Notes

- ACM's current author workflow says review submissions should use the
  single-column `manuscript` option of `acmart`; its ACM template page also says
  ACM journals use `acmsmall` except listed exceptions. Source:
  https://www.acm.org/publications/authors/submissions
- ACM policy says manuscripts under review are generally not allowed to be
  simultaneously under review elsewhere without explicit permission, supporting
  the non-simultaneous venue sequence in `VENUE_PLAN.md`. Source:
  https://www.acm.org/publications/policies/simultaneous-submissions
- RecSys 2026 required reproducibility/resource submissions to provide relevant
  artifacts, source code/data, installation instructions, and hardware
  documentation; it also prohibited dual submissions. This is precedent only;
  RecSys 2027 details are not yet established. Source:
  https://recsys.acm.org/recsys26/call/
- AR2023 documentation confirms user review text, timestamps, metadata, images,
  and user IDs, which supports the ethics/data-use concern. Source:
  https://amazon-reviews-2023.github.io/
- GrIT (arXiv:2602.19728) reports AR2023 Video_Games 5-core statistics matching
  this protocol family (94,762 users, 25,612 items, 814,586 interactions), uses
  full-item-set ranking, and reports NDCG@10 0.0588. Source:
  https://arxiv.org/abs/2602.19728 and
  https://arxiv.org/html/2602.19728v1

### Concrete Fixes To Make Next

1. Embed and visually verify Fig. 1-3.
2. Add an ethics/privacy/data-use statement.
3. Fix Table 0 HSTU parity wording.
4. Cite/scope GrIT and add the broader frequency/time-frequency SR references.
5. Correct stale page-count metadata in `CANONICAL_SUBMISSION.md` and avoid
   reusing older response prose as submission metadata.
6. Amend `VENUE_PLAN.md` to mark RecSys 2027 dates as TBD, or cite the eventual
   official 2027 CFP once available.
7. Resolve whether `RELEASE_MANIFEST.json` should be regenerated for current
   HEAD before any release/deposit bundle.
8. Triage untracked `paper_tex/` smoke artifacts before commit/release.

### Running Checklist

- [x] Read automation memory.
- [x] Preserve existing uncommitted audit content.
- [x] Re-run the strict submission gate.
- [x] Inspect manuscript source, compiled PDF, render HTML, figures, manifest,
      venue plan, and DOI note.
- [x] Render representative PDF pages with `pypdfium2`.
- [x] Fact-check ACM submission/dual-submission policy, RecSys reproducibility
      precedent, AR2023 data fields, and GrIT.
- [ ] Embed and visually verify Fig. 1-3.
- [ ] Add ethics/privacy/data-use statement.
- [ ] Fix Table 0 HSTU parity wording.
- [ ] Cite/scope GrIT and frequency/time-frequency SR papers.
- [ ] Fix stale page-count and manifest-boundary metadata.
- [ ] Move to target TORS/ACM formatting.
- [ ] Triage untracked `paper_tex/` smoke artifacts.

## Audit Run - 2026-07-12 09:40 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `9686cfb` (`Respond to
  PAPER_REVIEW_AUDIT run 08:31: preprint references completed with fetched
  metadata`)
- Note: before this section was written, `PAPER_REVIEW_AUDIT.md` was already
  modified with an uncommitted 09:37 audit section. I preserved that section and
  added only this incremental audit plus the risk-list updates above.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `CANONICAL_SUBMISSION.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`, `THEIRS_ON_OURS_REPORT.md`,
  `figures/*`, and the strict rebuild wrapper.
- Visual PDF check: rendered selected pages 1, 14, 15, 16, 18, 23, 24, 25, 26,
  28, 34, 35, and 38 with Poppler `pdftoppm.exe` into
  `tmp/pdfs/hourly_audit_20260712_0625/`.

### Verdict

**The numerical/artifact core still passes, but the submission package remains
not top-journal-ready.** The strict gate recomputes all manuscript numbers and
passes. The remaining rejection risks are now mostly presentation, consistency,
and literature-positioning issues: missing embedded figures, no ethics/data-use
statement, a contradicted HSTU-parity sentence in Table 0, and an under-covered
frequency/time-frequency related-work line.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 111 files verified.
  - PASS: MI V2 dual gate. K=16 CI-LB 0.04096 and K=8 CI-LB 0.04083 both exceed
    the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and VOID.
- `pypdf` extraction / PDF metadata:
  - `PAPER_SUBMISSION.pdf` has 38 pages and no image objects.
  - Non-ASCII extraction warnings were math/typographic symbols only, not
    mojibake.
- Visual rendering:
  - Tables are readable overall.
  - Table 2 has a polish defect: the page break leaves an isolated continuation
    cell ("dv=dqk=16 spec") at the top of page 26.
  - Fig. 1-3 are still not embedded in the rendered PDF.
- Text/source scan:
  - Confirmed contradiction: `PAPER_SUBMISSION.md` Table 0 says "no
    numerical-parity claim"; Section 3.7 and limitations say the core block is
    exactly parity-tested.
  - Confirmed omission: `PAPER_SUBMISSION.md` does not mention FEARec, MUFFIN,
    WEARec, WPGRec, or equivalent broader frequency/time-frequency SR coverage.

### Confirmed Problems

1. **HSTU fidelity wording contradicts itself.** Fix Table 0's HSTU-base row so
   it no longer says "no numerical-parity claim". Suggested boundary:
   "core-block parity demonstrated against the reference research
   implementation; no pinned end-to-end system reproduction."
2. **Frequency-filter related work is too narrow.** Add a short sentence and
   references around the FMLP/BSARec novelty-boundary paragraph acknowledging
   the broader frequency/time-frequency SR line. The causal FIR contribution can
   still be framed as narrower: left-causal, depthwise FIR, HSTU-style stack,
   all-position next-item objective, full-catalog AR2023 LLOO.
3. **PDF page-count statements are stale in response/canonical files.**
   `CANONICAL_SUBMISSION.md` still says the PDF is 36 pp; the newest PDF is
   38 pp. `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` contains both corrected 38 pp
   language and older 37 pp language in older response sections. This is not a
   scientific problem, but do not use stale response prose as submission-package
   metadata.
4. **Table 2 page break needs polishing.** The isolated continuation cell is not
   data-corrupting, but a reviewer-facing PDF should avoid dangling table cells.

### Plausible Risks Requiring Author Verification

- The 09:37 audit's missing-figures and no-ethics findings remain the dominant
  submission-readiness blockers.
- The broader frequency/time-frequency literature may contain additional
  directly relevant work beyond the four examples checked here. A venue-format
  pass should do one final targeted search before freezing the references.
- The release manifest boundary still depends on whether the next package is
  cut from `9ed7be3` assets or from current HEAD `9686cfb`.

### External Fact-Check / Novelty Notes

- FEARec (SIGIR 2023) explicitly frames self-attention SR as low-pass and
  proposes a frequency-enhanced hybrid attention network. Source:
  https://arxiv.org/abs/2304.09184
- MUFFIN (CIKM 2025) is a user-adaptive frequency-filtering SR model and frames
  itself against limitations of earlier frequency-domain SR models. Source:
  https://arxiv.org/abs/2508.13670
- WEARec (AAAI 2026) proposes dynamic frequency-domain filtering plus wavelet
  feature enhancement for sequential recommendation. Source:
  https://arxiv.org/abs/2511.07028
- WPGRec (2026 preprint) proposes wavelet-packet guided graph-enhanced
  sequential recommendation. Source: https://arxiv.org/abs/2604.21305

### Concrete Fixes To Make Next

1. Embed and visually verify Fig. 1-3.
2. Add the ethics/privacy/data-use statement.
3. Fix the HSTU-base row in Table 0.
4. Add the frequency/time-frequency related-work sentence and references.
5. Fix the Table 2 page break during venue-template formatting.
6. Decide whether to update the release-manifest boundary from `9ed7be3` to
   current HEAD before the next deposit/release bundle.

### Running Checklist

- [x] Read automation memory.
- [x] Re-read the current cumulative audit and preserve existing uncommitted
      audit content.
- [x] Re-run the strict submission gate.
- [x] Inspect canonical source, response, manifest, PDF, and figure assets.
- [x] Render representative PDF pages.
- [x] Fact-check the broader frequency/time-frequency SR line.
- [ ] Embed and visually verify Fig. 1-3.
- [ ] Add ethics/privacy/data-use statement.
- [ ] Fix Table 0 HSTU parity wording.
- [ ] Add frequency/time-frequency related-work coverage.
- [ ] Triage/cite GrIT and any other same-statistics AR2023 5-core papers.
- [ ] Resolve release-manifest boundary if cutting a new release.
- [ ] Move to target venue formatting.

## Audit Run - 2026-07-12 09:37 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `9686cfb` (`Respond to
  PAPER_REVIEW_AUDIT run 08:31: preprint references completed with fetched
  metadata`)
- Tracked working tree after verification and before writing this audit section:
  clean. After this audit update, only `PAPER_REVIEW_AUDIT.md` is modified.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `_paper_render.html`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/rebuild_hstu_submission.py`,
  `_bestrec_run/render_paper_pdf.py`, `figures/*`, prior cumulative audit and
  response files.
- Visual PDF check: rendered selected pages 1, 14, 19, 23, 32, and 34 with
  `pypdfium2` into `tmp/pdfs/hourly-strict-paper-audit-visual/`. Poppler wrapper
  commands (`pdfinfo.cmd`, `pdftoppm.cmd`) were present but failed with "The
  system cannot find the path specified", so `pypdfium2` was used instead.

### Verdict

**The prior 2026-reference problem is fixed.** The four recent preprints now
have full bibliographic entries, and the compiled PDF contains SID-MLP, Latte,
ChronoSID, ReSID, and the new author/title metadata. The stale first/only
AR2023 phrases remain absent from the PDF.

**The strict result/artifact gate still passes.** The build recomputes 164 paper
cells, reports 0 mismatches and 0 untraceable cells, verifies 111 manifest files,
passes MI dual-gate arithmetic, and keeps Office descriptive/VOID.

**New top-journal risk: the paper refers to figures that are not actually in the
PDF.** The figure files exist on disk, but `PAPER_SUBMISSION.md` uses prose
references such as `Fig. 1 (figures/fig_tail_law_mechanism)` rather than image
inclusion syntax, `_paper_render.html` has no `<img>` tags for them, and a PDF
page-image scan found no embedded image objects. This is a confirmed
submission-readiness defect, not a scientific-result defect.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    claim families sourced.
  - PASS: release manifest verification, 111 files verified.
  - PASS: MI V2 dual gate. K=16 mean 0.04152, CI-LB 0.04096; K=8 mean 0.04120,
    CI-LB 0.04083; both above the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and VOID.
- PDF text extraction using `pypdf`:
  - 38 pages, 830,097 bytes.
  - `first to report numbers`, `only published work using AR2023`, and `first
    such reported number`: absent.
  - `SID-MLP`, `Latte`, `ChronoSID`, `ReSID`, and the author/title strings for
    Guo/Hou/Huang/Liang entries: present.
- Visual/layout sampling with `pypdfium2`:
  - Selected text/table pages are readable and not visibly clipped.
  - No venue template, page numbers, headers, or journal formatting were added.
  - Confirmed missing embedded figures: source contains no Markdown image
    syntax, `_paper_render.html` has no image tags for Fig. 1-3, and `pypdf`
    found no page images.
- `git status --short`
  - Clean after strict rebuild and audit inspection, before writing this audit
    section.

### Confirmed Fixes Since The 08:31 Audit

1. **Bare 2026 preprint references fixed.** `PAPER_SUBMISSION.md` now gives
   author/title metadata for SID-MLP, Latte, ChronoSID, and ReSID, with an
   explicit unreviewed-concurrent-work fence.
2. **Latte MI/VG numbers rechecked.** Latte's Table 1 reports the values quoted
   by the manuscript: Instruments NDCG@10 0.0331 and Games NDCG@10 0.0515.
3. **PDF/manifest/audit dirty state resolved.** The branch is clean at HEAD
   `9686cfb`; the prior dirty regenerated PDF/manifest state has been committed.

### Confirmed Problems

1. **Figures absent from the compiled paper.** The paper's live scientific story
   relies on Fig. 1-3, but the PDF currently contains only prose references to
   figure filenames. Fix by embedding the PNG/PDF figure assets in the manuscript
   source and rerendering. Then visually inspect pages containing each figure.
2. **No ethics/privacy/data-use section.** The paper uses a large public review
   dataset that includes user review text, timestamps, item metadata/images, and
   pseudonymous user IDs. A submission should include a short ethics/data-use
   statement covering public-data use, privacy/PII handling, license/terms,
   limitations of recommender deployment, and whether IRB/human-subjects review
   was not required.
3. **Current release manifest commit does not equal current HEAD.**
   `RELEASE_MANIFEST.json` records `git_commit = 9ed7be3...`, while the current
   HEAD is `9686cfb...`. Strict verification passes because the response-only
   commit does not affect the release assets, but this distinction should be
   explicit if cutting a release from HEAD.

### Plausible Risks Requiring Author Verification

- **GrIT related-work coverage.** GrIT is not currently cited. It reports on
  Amazon Reviews 2023 Video_Games with the same 94,762 users / 25,612 items /
  814,586 interactions statistics and NDCG@10 0.0588. It is below this paper's
  0.0673 and below HSTU-BLaIR's 0.0760, so it does not invalidate the result,
  but a reviewer could object that a same-statistics 2026 AR2023 sequential
  recommender was missed.
- **RPORec and other 2026 LLM/generative AR2023 papers are non-comparable but
  should be triaged.** RPORec explicitly omits the 5-core filter and uses a
  one-year temporal truncation, so it should not be compared numerically. It may
  still belong in a "recent non-comparable AR2023 protocols" sentence if the
  venue expects very fresh coverage.
- **Mechanism wording remains close to the line.** The paper repeatedly scopes
  "driver" and "partial causal role" to synthetic thinning interventions, which
  is good. Preserve those caveats if the abstract/introduction is shortened.
- **Page design is readable but not journal-ready.** The sampled PDF pages are
  legible, but the document is a Markdown/HTML render without target venue
  layout, headers/footers, figure placement, or formal caption formatting.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR reports AR2023 5-core statistics and comparator values used by the
  manuscript: Video_Games HSTU-BLaIR NDCG@10 0.0760, Office_Products 0.0271,
  Musical_Instruments 0.0406. Source: https://arxiv.org/html/2504.10545v3
- Latte reports Instruments NDCG@10 0.0331 and Games NDCG@10 0.0515 in its
  Table 1. Source: https://arxiv.org/html/2605.06331v1
- SID-MLP reports same-family Instruments/Games numbers, including Sid-Mlp
  Instruments NDCG@10 0.0332 and Games NDCG@10 0.0512. Source:
  https://arxiv.org/html/2605.12617v1
- ReSID reports MI NDCG@10 0.0346 under its own filtered universe. Source:
  https://arxiv.org/html/2602.02338v1
- ChronoSID's output-level MI table reports ReSID 0.0325 vs ChronoSID 0.0345
  NDCG@10 with paired-bootstrap confidence intervals. Source:
  https://arxiv.org/html/2607.03918v1
- GrIT uses Amazon Reviews 2023 Video_Games with 94,762 users, 25,612 items, and
  814,586 interactions, and reports Video_Games NDCG@10 0.0588. Source:
  https://arxiv.org/html/2602.19728v1
- RPORec uses the latest Amazon source but states it omits 5-core filtering and
  uses a one-year temporal truncation, making it non-comparable to the paper's
  fixed 5-core LLOO protocol. Source: https://arxiv.org/html/2605.21967
- Amazon Reviews 2023's official site states the dataset includes user reviews,
  item metadata, and links, with 571.54M reviews and interactions through
  September 2023. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Embed Fig. 1-3 in `PAPER_SUBMISSION.md` with real captions, rerender
   `PAPER_SUBMISSION.pdf`, and visually inspect every figure page.
2. Add a short ethics/privacy/data-use section before Code and Data Availability
   or inside Limitations.
3. Add GrIT to the 2026 AR2023 related-work paragraph, or explicitly scope it
   out as non-text/non-HSTU but same-statistics Video_Games context.
4. If preparing a release/deposit from current HEAD, regenerate
   `RELEASE_MANIFEST.json` or document why the manifest boundary remains
   `9ed7be3`.
5. Move the manuscript into the target venue template after the figure/ethics
   fixes, then repeat full visual QA.

### Open Questions

- What is the target venue/template? This now blocks final submission readiness.
- Should GrIT be cited in the main text as same-statistics AR2023 Video_Games
  context, or confined to a recent-preprints footnote?
- Are the three figure files intended as main-paper figures or supplementary
  figures? The current text treats them as main-paper figures.

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript source and PDF.
- [x] Verify current HEAD and clean working tree.
- [x] Rerun strict submission gate.
- [x] Check compiled PDF text for stale novelty phrases and new references.
- [x] Fact-check the 2026 preprint metadata/numbers against primary sources.
- [x] Perform a fresh AR2023-related-work search.
- [x] Render selected PDF pages for visual inspection.
- [x] Detect missing embedded figures.
- [ ] Embed and visually verify Fig. 1-3 in the compiled PDF.
- [ ] Add ethics/privacy/data-use statement.
- [ ] Triage/cite GrIT and any other same-statistics AR2023 5-core papers.
- [ ] Resolve release-manifest boundary if cutting a new release.
- [ ] Move to target venue formatting.

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
