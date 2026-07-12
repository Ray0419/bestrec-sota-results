# Paper Review Audit

This file is cumulative. Each run should add a timestamped section, keep the
prior rejection-risk list current, and distinguish confirmed problems from
plausible risks.

## Current Prioritized Rejection-Risk List

1. **Confirmed manuscript-scope staleness around FIR-BREADTH.** Both
   pre-registered breadth categories now mechanically adjudicate as
   `CONFIRMED`: Industrial_and_Scientific paired mean `+0.00240`, 95% t-CI
   `[+0.00183, +0.00297]`, 5/5 positive; CDs_and_Vinyl paired mean `+0.00566`,
   95% t-CI `[+0.00493, +0.00639]`, 5/5 positive. The manuscript and TeX table
   still call both rows "outcome pending," say no result from them is claimed,
   and Section 6.4 still says other categories are untested. This is now the
   clearest reviewer-facing contradiction.
2. **Confirmed FIR-BREADTH governance/provenance defect remains active.**
   `FIR_BREADTH_RESULTS.md` now exists with the mechanical adjudication, but it
   is untracked; the adjudicator, driver/prep scripts, raw-data directories,
   and all FIR-BREADTH result JSONs are also untracked. All completed CDs result
   manifests inspected record `git_dirty_tracked=true` at commit `f50c7fdd`.
   A methodology-first paper cannot cite this campaign until the scripts,
   data/provenance boundary, results, adjudication file, manifest scope, and PDF
   are committed and gate-verified together.
3. **Confirmed Office V3 governance change is uncommitted.** `PREREG_OFFICE_V3.md`
   now has an appended Erratum E1 exempting `PAPER_REVIEW_AUDIT.md` and
   `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` from that campaign's clean-tree
   requirement. No Office V3 run artifacts or active processes were found, so
   the erratum appears pre-run, but it must be committed before any V3 run and
   disclosed as a protocol clarification.
4. **Confirmed novelty-boundary gap for causal/local convolutional SR.** The
   manuscript cites FMLP-Rec/BSARec/FEARec/WPGRec for frequency filtering, but
   local search finds no citation to Caser, NextItNet, or the 2022 "Self-
   Attentive Sequential Recommendation with Cheap Causal Convolutions" paper.
   Because the abstract/introduction call the left-causal FIR realization
   "new" mainly against bidirectional frequency filters, a reviewer can object
   that causal convolutional sequence modeling in recommendation is already
   prior art. This is a wording/citation problem, not a leak problem.
5. **Current printed-paper artifact evidence is green.** A fresh strict rebuild
   on this run passes: HSTU core-block parity exact; 164 cells recomputed; 0
   `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared claim families sourced; release
   manifest verification OK for 113 files; MI gate PASS; Office remains
   descriptive/VOID. `paper_tex/hygiene_scan_output.txt` also records 0
   placeholder/forbidden-claim failures for the 39-page TORS PDF.
6. **Confirmed causal-filter implementation matches the leak-free claim.** The
   code applies depthwise Conv1d after left-only padding (`F.pad(xt, (K - 1,
   0))`) on right-padded sequences, so output position t depends only on input
   positions <= t. This supports the paper's core "strictly causal FIR" claim;
   the current rejection risk is novelty boundary and governance, not leakage.
7. **Confirmed prior Section 4.1 dataset/protocol blockers are repaired.** The
   paper now uses a role-based dataset table covering Video_Games,
   Musical_Instruments, Office_Products, Beauty_and_Personal_Care,
   Industrial_and_Scientific, and CDs_and_Vinyl. Counts are labeled as total
   5-core interactions, with the LLOO rule stated inline; local row counts and
   external AR2023 statistics match the table values checked this run.
8. **Plausible residual count-readability risk: Section 5.1 still quotes the
   HSTU-BLaIR Video_Games interaction count as 814,585 while Section 4.1's local
   table reports 814,586.** This is no longer a contradiction because Section
   4.1 says interactions match the comparator pipeline within +/-1, but a
   reviewer may still pause. Label the 814,585 number explicitly as the
   comparator paper's reported count, not the local row count.
9. **Methodology-first novelty/fit risk increased after the reframe.** The
   evaluation-trust problem is real and well cited, but a top-journal reviewer
   may view the "trustworthy-evaluation apparatus" as good artifact practice
   rather than a standalone scientific contribution unless the paper states its
   novelty narrowly: an auditable case study/per-paper discipline, not a new
   general framework. Add a short comparison to standardized benchmarking and
   artifact-evaluation norms, and keep empirical contributions visible.
10. **Plausible recent-literature scope risk: SILLM4Rec still lacks direct
   protocol inspection.** ACM metadata now says SILLM4Rec uses three 5-core
   Amazon Reviews 2023 datasets and reports NDCG@10. The current exclusion may
   still be defensible if the full text does not establish full-catalog LLOO,
   but the paper should either inspect the PDF or soften the sentence to avoid
   implying it is too remote to matter.
11. **Persistent scientific boundary: no broad SOTA, no paired superiority.** Any
   future abstract, conclusion, cover letter, response file, or release note
   must keep Video_Games as competitive but not SOTA; MI as a per-category
   point-estimate comparison; Office as VOID/descriptive only; and any
   FIR-BREADTH wording as an internal paired filter-vs-no-filter result, never a
   comparator or SOTA claim.

## Audit Run - 2026-07-13 06:46 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `f50c7fdd` (`Respond to
  PAPER_REVIEW_AUDIT run 23:39: 4.1 role table + count definitions`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*`, `paper_tex/tables/*`,
  `paper_tex/references.bib`, `PREREG_FIR_BREADTH.md`,
  `FIR_BREADTH_RESULTS.md`, FIR-BREADTH JSON/log artifacts, and the cumulative
  audit.
- Working tree state after this audit's commands: `PAPER_REVIEW_AUDIT.md`
  modified by this audit; `PREREG_OFFICE_V3.md` independently gained an
  uncommitted Erratum E1 at 06:46; `FIR_BREADTH_RESULTS.md`, FIR-BREADTH
  adjudicator/scripts/results, and raw-data directories are untracked. No
  manuscript/TeX source file was edited by this audit.

### Verdict

**The live workspace has outgrown the submitted manuscript.** The printed paper
still passes its strict rebuild and hygiene checks, but the now-complete
FIR-BREADTH campaign makes the current manuscript stale: it says two categories
are pending and unclaimed while the workspace contains a mechanical two-category
confirmation. A top-journal reviewer would treat this as a governance and
scope-boundary failure unless the authors either freeze the submitted package as
pre-breadth, or integrate the campaign cleanly and regenerate every artifact.

The second live rejection risk is unchanged: the causal FIR novelty boundary
still cites frequency filters but not older causal/local convolutional
sequential-recommendation work. The claim can survive only as a narrow
left-causal, zero-init depthwise residual FIR inside this HSTU-style evaluation
apparatus, not as a broad first use of causal/local convolution.

### Commands And Evidence Checked

- `_bestrec_run\.venv\Scripts\python.exe _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - Industrial_and_Scientific: `CONFIRMED`.
  - CDs_and_Vinyl: `CONFIRMED`.
  - Industrial paired deltas: `+0.00243`, `+0.00196`, `+0.00191`, `+0.00287`,
    `+0.00284`; mean `+0.00240`, 95% t-CI `[+0.00183, +0.00297]`, positive
    seeds `5/5`.
  - CDs paired deltas: `+0.00539`, `+0.00638`, `+0.00617`, `+0.00498`,
    `+0.00540`; mean `+0.00566`, 95% t-CI `[+0.00493, +0.00639]`, positive
    seeds `5/5`.
- `FIR_BREADTH_RESULTS.md`
  - Contains the same mechanical adjudication block and frozen claim wording
    for both categories, but the file is currently untracked.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed, 0 mismatches, 0 untraceable; all 12 declared
    claim families sourced.
  - PASS: release manifest verification OK for 113 files.
  - PASS: MI dual gate; Office remains descriptive/VOID under prereg floor
    check.
- `rg "FIR_BREADTH|FIR-BREADTH|Industrial_and_Scientific|CDs_and_Vinyl|outcome pending|pending-campaign"`
  - `PAPER_SUBMISSION.md`, `paper_tex/sections/04-experiments.tex`, and
    `paper_tex/tables/table_datasets41.tex` still label the FIR-BREADTH rows as
    pending and say no result from them is claimed.
  - `PAPER_SUBMISSION.md` / `paper_tex/sections/06-discussion.tex` still say
    other categories are untested.
- Structured JSON parse of completed CDs_and_Vinyl files:
  - Filter NDCG@10 by seed: `0.066173`, `0.066262`, `0.066081`, `0.065990`,
    `0.065889`.
  - No-filter NDCG@10 by seed: `0.060778`, `0.059880`, `0.059913`,
    `0.061013`, `0.060494`.
  - Every inspected result manifest records `git_dirty_tracked=true` at
    `f50c7fdd6eb821a7c4012ea5abcd53662d691424`.
- `paper_tex/hygiene_scan_output.txt`
  - PASS: `PAPER_TORS.pdf`, 39 pages, 0 placeholder/forbidden-claim failures.
- `pdfinfo`
  - Not usable in this shell (`The system cannot find the path specified.`), so
    no fresh external page-count extraction was recorded this run.

### Confirmed Problems

1. **The paper is now stale relative to its own workspace evidence.** Both
   FIR-BREADTH categories are confirmed under the frozen rule, but the
   manuscript still presents the campaign as pending and outside the paper's
   result set.
2. **The campaign cannot yet be cited as top-journal-grade evidence.** The
   adjudication file and underlying scripts/results/raw-data directories are
   untracked, the result manifests record dirty tracked state, and the release
   manifest/artifact gate has not been extended to this campaign.
3. **Office V3's clean-tree rule changed in an uncommitted erratum.** The new
   erratum exempts audit/response logs from the dirty-tree condition. No Office
   V3 run artifacts or live processes were found, so this appears pre-run, but
   it is only defensible if committed before the first V3 run and kept narrow.
4. **The frozen claim wording is narrow and must stay narrow.** The admissible
   wording is only "paired 5-seed improvement on <category>, transplanted with
   zero per-category tuning, positive with a 95% CI excluding zero." It is not a
   comparator claim, not an SOTA claim, and not evidence for all categories.
5. **The causal FIR related-work boundary remains under-cited.** The manuscript
   still needs Caser/NextItNet/cheap causal-convolution SR or equivalent local
   convolutional SR citations before "new left-causal FIR realization" is safe.
6. **SILLM4Rec exclusion is now a paper-readiness risk, not just a TODO.** ACM
   metadata says the paper uses three 5-core Amazon Reviews 2023 datasets and
   reports NDCG@10, so a reviewer may reasonably expect either inspection or a
   more cautious exclusion sentence.

### Confirmed Fixes Since Earlier Runs

- The prior "first to report numbers" / "only published work using AR2023"
  problem no longer appears in the searched manuscript/TeX sources.
- The 2026 AR2023-adjacent paragraph now covers SID-MLP, Latte, GrIT, ReSID,
  ChronoSID, Augment-or-Not, and DiffuReason with explicit comparability
  caveats and no comparative claim against concurrent arXiv work.
- The strict submission rebuild remains green despite the in-progress
  FIR-BREADTH materials being outside the printed-paper artifact graph.

### Plausible Risks Requiring Author Verification

- The authors need a scope decision: submit a pre-FIR-BREADTH snapshot, or make
  FIR-BREADTH a real result section/appendix with committed provenance and a
  regenerated paper/PDF. Leaving the current mixed state is the worst option.
- If FIR-BREADTH is integrated, the main paper must decide whether this is a
  short breadth note in limitations/results or a full result table. The latter
  requires new generated tables and manifest coverage.
- `FIR_BREADTH_RESULTS.md` appeared during/after the final run despite this
  audit using `--no-append`; verify whether the training driver or adjudicator
  created it intentionally before treating it as the official record.
- `PREREG_OFFICE_V3.md` Erratum E1 should be committed before any V3 run starts;
  otherwise the exemption could look like post-hoc relaxation after seeing a
  clean-tree failure.
- SILLM4Rec may still be non-comparable, but "accessible metadata did not
  establish..." is now only partially satisfying because the ACM abstract
  metadata is close enough to the paper's protocol family to invite reviewer
  scrutiny.

### External Fact-Check / Novelty Notes

- GrIT is an arXiv 2026 sequential-recommendation preprint; the manuscript's
  "concurrent arXiv-only" caveat is supported by the arXiv listing as checked in
  this run. Source: https://arxiv.org/abs/2602.19728
- DiffuReason's arXiv listing identifies it as a 2026 sequential-recommendation
  paper; the search/PDF snippet reports the manuscript-cited different
  Video-and-Games universe (`67,658` users, `25,535` items, `654,867`
  interactions), supporting the non-comparability note. Source:
  https://arxiv.org/abs/2602.09744
- Augment-or-Not's arXiv listing confirms it is a 2025 LLM-recommender
  benchmark; the paper's non-interchangeable-protocol citation is directionally
  appropriate. Source: https://arxiv.org/abs/2505.23053
- SILLM4Rec ACM metadata says its experiments use three 5-core Amazon Reviews
  2023 datasets and report NDCG@10, so it should not be dismissed without full
  protocol inspection. Source: https://dl.acm.org/doi/10.1145/3743093.3771011
- The earlier causal-convolution novelty warning still applies: Caser,
  NextItNet, and cheap causal-convolution SR are relevant prior art for any
  broad local/causal convolution phrasing. Sources:
  https://arxiv.org/abs/1809.07426, https://arxiv.org/abs/1808.05163,
  https://arxiv.org/abs/2211.01297

### Concrete Fixes To Make Next

1. Decide the FIR-BREADTH scope boundary before editing prose:
   - **Pre-breadth submission:** remove or archive untracked FIR-BREADTH
     artifacts from the submitted/deposit boundary and keep the paper's pending
     language accurate for the submitted snapshot.
   - **Integrated submission:** commit/adjudicate/manifest the entire campaign,
     regenerate tables/PDFs, and update all pending/untested language.
2. If integrated, add one narrowly worded FIR-BREADTH result paragraph/table:
   Industrial `+0.00240` CI `[+0.00183,+0.00297]`; CDs `+0.00566` CI
   `[+0.00493,+0.00639]`; both 5/5 positive; explicitly "internal paired
   filter-vs-no-filter, zero per-category tuning, no comparator/SOTA claim."
3. Commit or deliberately exclude `FIR_BREADTH_RESULTS.md`,
   `_bestrec_run/adjudicate_fir_breadth.py`, run scripts, prep/encoding
   scripts, raw-data provenance, JSONs, user sidecars if intended, and any
   manifest updates as a single coherent evidence boundary.
4. Commit `PREREG_OFFICE_V3.md` Erratum E1 before any Office V3 execution, or
   remove it and keep the original strict clean-tree rule. Do not run V3 while
   the pre-registration is dirty.
5. Repair causal FIR novelty wording and references by adding convolutional SR
   prior art before FMLP/BSARec, then narrow the claim to this specific
   zero-init left-causal residual FIR in this artifact-gated setting.
6. Obtain/inspect SILLM4Rec full text or soften the exclusion to:
   "SILLM4Rec is adjacent AR2023 5-core work, but we have not yet verified
   full-catalog LLOO comparability; we therefore make no claim against it."

### Open Questions

- Should FIR-BREADTH be incorporated before submission, or treated as future
  work outside the current paper snapshot?
- If incorporated, should Office V3 remain pending in the same paragraph, or
  should the paper separate "confirmed internal breadth" from "Office
  comparator-facing pre-registration still pending/VOID history"?
- Is the Office V3 Erratum E1 author-approved and intentionally pre-run, or was
  it generated by an automated responder that should not define the protocol?
- Is there institutional access to the SILLM4Rec PDF, or should the authors
  contact the authors for protocol details?

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Read automation memory and prior cumulative audit.
- [x] Re-run strict submission rebuild.
- [x] Wait for final CDs_and_Vinyl no-filter seed to finish.
- [x] Re-run FIR-BREADTH mechanical adjudicator after all 20 runs completed.
- [x] Check manuscript/TeX for stale pending/untested language.
- [x] Check current related-work coverage for recent AR2023-adjacent papers.
- [x] Inspect unexpected `PREREG_OFFICE_V3.md` tracked diff.
- [x] Update the cumulative audit with current findings.
- [ ] Decide pre-breadth vs integrated-scope submission boundary.
- [ ] Commit/manifest or deliberately exclude FIR-BREADTH artifacts.
- [ ] Commit or remove Office V3 Erratum E1 before any V3 run.
- [ ] Repair causal-convolution prior-art boundary.
- [ ] Inspect SILLM4Rec full protocol or soften exclusion wording.

## Audit Run - 2026-07-13 05:40 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `f50c7fdd` (`Respond to
  PAPER_REVIEW_AUDIT run 23:39: 4.1 role table + count definitions`).
- Tracked working tree before this run: `PAPER_REVIEW_AUDIT.md` modified; no
  tracked manuscript or TeX edits detected after the 02:41 audit.
- Active untracked FIR-BREADTH artifacts changed after 02:41:
  - CDs_and_Vinyl filter seeds `20260713`-`20260717` are now complete.
  - CDs_and_Vinyl no-filter seeds `20260713`-`20260714` are complete.
  - CDs_and_Vinyl no-filter seed `20260715` appears active: `uv`/`python`
    process started 05:19 and `run_FIRB_CDs_and_Vinyl_nofilter_seed20260715.log`
    was at epoch 14 during inspection.
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*`, `paper_tex/tables/*`,
  `paper_tex/references.bib`, `PREREG_FIR_BREADTH.md`, FIR-BREADTH JSON/log
  artifacts, and the existing cumulative audit.

### Verdict

**The paper itself still builds cleanly, but top-journal readiness is blocked by
two live issues: moving-scope evidence and an incomplete novelty boundary.**
The printed paper can be defended only as a pre-FIR-BREADTH snapshot. If the
new breadth evidence is included, Industrial_and_Scientific must be integrated
with full provenance and CDs_and_Vinyl must remain VOID until all pairs are
complete and mechanically adjudicated. Separately, the causal FIR novelty
boundary needs repair: the manuscript acknowledges bidirectional frequency
filters but not earlier convolutional/causal-convolution sequential
recommenders.

### Commands And Evidence Checked

- `_bestrec_run\.venv\Scripts\python.exe _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - Industrial_and_Scientific: `CONFIRMED`.
  - Paired deltas remain `+0.00243`, `+0.00196`, `+0.00191`, `+0.00287`,
    `+0.00284`; mean `+0.00240`, 95% t-CI `[+0.00183, +0.00297]`, positive
    seeds `5/5`.
  - CDs_and_Vinyl: `VOID(incomplete)` with 7/10 runs present; missing no-filter
    seeds `20260715`-`20260717`.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed, 0 mismatches, 0 untraceable; all 12 declared
    claim families sourced.
  - PASS: release manifest verification OK for 113 files.
  - PASS: MI dual gate; Office remains descriptive/VOID under prereg floor
    check.
- Structured JSON parse of completed CDs_and_Vinyl FIR-BREADTH files:
  - Filter complete: seeds `20260713`-`20260717`, NDCG@10 `0.066173`,
    `0.066262`, `0.066081`, `0.065990`, `0.065889`.
  - No-filter complete: seeds `20260713`-`20260714`, NDCG@10 `0.060778`,
    `0.059880`.
  - Completed paired deltas: seed `20260713` `+0.00539`; seed `20260714`
    `+0.00638`.
  - All completed CDs result manifests inspected here record
    `git_dirty_tracked=true` at commit `f50c7fdd`.
- `rg "FIR_BREADTH|Industrial_and_Scientific|CDs_and_Vinyl|untested|pending"`
  - `PAPER_SUBMISSION.md`, `paper_tex/sections/04-experiments.tex`, and
    `paper_tex/tables/table_datasets41.tex` still label Industrial and CDs as
    pending.
  - `PAPER_SUBMISSION.md` and `paper_tex/sections/06-discussion.tex` still say
    other categories are untested.
- `rg "cheap causal|causal convolution|Caser|NextItNet|2211\.01297|WEARec"`
  - No local citation/prose hit in `PAPER_SUBMISSION.md`, `paper_tex/sections`,
    or `paper_tex/references.bib`.
- `paper_tex/hygiene_scan_output.txt`
  - Latest scan remains PASS: 39 pages, 0 placeholder/forbidden-claim failures.

### Confirmed Problems

1. **CDs_and_Vinyl is still void, despite favorable-looking partials.** The
   frozen rule requires five paired differences. Reporting the two completed
   positive pairs would be selective-peeking, especially because the remaining
   no-filter arm is still running.
2. **The current manuscript is stale relative to the workspace.** Industrial is
   adjudicable and confirmed; CDs is partially run and void. The paper still
   says both are pending and other categories are untested.
3. **The causal FIR novelty paragraph omits convolutional SR prior art.** Caser,
   NextItNet-style holed/dilated convolution, and cheap causal-convolution
   self-attentive SR all weaken a claim that the "left-causal FIR realization"
   is new unless the paper distinguishes its much narrower contribution.
4. **FIR-BREADTH is not yet provenance-clean.** The adjudicator/scripts/results
   remain untracked, no official adjudication record was appended, and all
   completed CDs result manifests inspected in this run have dirty tracked
   state.
5. **The pre-registration's "script committed with the campaign" promise is not
   presently true in the working tree.** `adjudicate_fir_breadth.py` is
   untracked, so the campaign cannot yet support a methodology-first
   submission without repository hygiene work.

### Plausible Risks Requiring Author Verification

- If no-filter seed `20260715` finishes after this audit, the current section
  will immediately become stale. That is fine for an hourly audit, but the paper
  must not be submitted while the evidence boundary is moving.
- The large partial CDs deltas may tempt an early breadth claim. A strict
  reviewer will treat that as cherry-picking unless the official 5-pair
  adjudicator result is recorded and all missing counterparts are accounted for.
- The causal FIR contribution can probably survive if rewritten as "a
  zero-init, depthwise, left-causal residual FIR inserted before an HSTU-style
  stack under all-position full-catalog AR2023 LLOO," but not as a broad first
  use of causal/local convolution for sequential recommendation.
- The methodology-led framing raises the standard for all of the above. A
  normal empirical paper might get away with a late appendix note; this paper's
  stated contribution is that it does not.

### External Fact-Check / Novelty Notes

- `Self-Attentive Sequential Recommendation with Cheap Causal Convolutions`
  (arXiv:2211.01297) explicitly proposes a self-attentive SR model using causal
  convolutions to capture local item context for attention and sequence
  embedding. Source: https://arxiv.org/abs/2211.01297
- Caser (`Personalized Top-N Sequential Recommendation via Convolutional
  Sequence Embedding`, WSDM 2018) uses convolutional filters over recent item
  sequences to learn local sequential patterns. Source:
  https://arxiv.org/abs/1809.07426
- NextItNet (`A Simple Convolutional Generative Network for Next Item
  Recommendation`) uses holed/dilated convolutional layers to model short- and
  long-range item dependencies for next-item recommendation. Source:
  https://arxiv.org/abs/1808.05163
- WEARec (AAAI 2026) lists a broader frequency-SR lineage including FMLP-Rec,
  SLIME4Rec, FEARec, BSARec, and FamouSRec, supporting a broader related-work
  sentence if the manuscript keeps frequency/time-frequency claims prominent.
  Source: https://arxiv.org/html/2511.07028v1
- WPGRec remains a relevant 2026 time-frequency sequential-recommendation
  comparator/context paper and is already cited; it should stay framed as
  related prior art, not an apples-to-apples AR2023 comparator. Source:
  https://arxiv.org/abs/2604.21305

### Concrete Fixes To Make Next

1. Rewrite the FIR novelty boundary everywhere it appears (abstract,
   introduction, Table 0, method, conclusion) to include the convolutional SR
   line. Suggested boundary: "local/causal convolutional sequence modeling and
   frequency filtering are prior art; our contribution is the zero-init gated
   depthwise left-causal FIR residual placed before an HSTU-style stack and
   artifact-gated under AR2023 full-catalog LLOO."
2. Add references and Table 0/prose distinctions for Caser, NextItNet or an
   equivalent dilated-convolution SR source, and cheap causal-convolution SR.
3. Decide the FIR-BREADTH evidence boundary before any submission package:
   either freeze the paper as pre-breadth and exclude these artifacts, or wait
   for all CDs counterparts, run the official adjudicator append, commit/hash
   scripts/results/provenance, and update the manuscript/PDF.
4. Do not mention the two positive CDs pairs in manuscript prose until the
   missing no-filter seeds are complete and the frozen rule returns a category
   verdict.
5. If FIR-BREADTH is integrated, use only the frozen internal-paired wording and
   keep it out of comparator/SOTA claims.

### Open Questions

- Is the current intended submission snapshot pre-FIR-BREADTH, or should the
  paper wait for the active CDs no-filter sequence to finish?
- If FIR-BREADTH is integrated, should dirty-tracked runs be accepted with code
  hashes and disclosure, or rerun from a clean committed boundary?
- Should WEARec/FamouSRec/SLIME4Rec be added only to related work, or also to
  Table 0's novelty-boundary row?

### Running Checklist

- [x] Read automation memory state.
- [x] Locate canonical manuscript source, TeX derivative, PDF, figures/tables,
      preregistration, result files, and cumulative audit.
- [x] Check files modified after the previous audit.
- [x] Re-adjudicate FIR-BREADTH in no-append mode.
- [x] Re-run strict manuscript artifact rebuild.
- [x] Parse completed CDs_and_Vinyl FIR-BREADTH JSONs and paired deltas.
- [x] Confirm manuscript still says Industrial/CDs pending and other categories
      untested.
- [x] Fact-check causal/local-convolution and frequency-SR novelty context
      against primary sources.
- [x] Update this cumulative audit.
- [ ] Add missing causal-convolution/convolutional-SR prior-art citations.
- [ ] Decide whether FIR-BREADTH enters the submission or remains excluded.
- [ ] Complete/officially adjudicate CDs_and_Vinyl before any breadth wording.

## Audit Run - 2026-07-13 02:41 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Tracked working tree: `PAPER_REVIEW_AUDIT.md` modified before this run; no
  manuscript/source edits made by this audit.
- No commits after the previous automation cutoff (`2026-07-12T15:37:31Z`).
- Untracked active files include FIR-BREADTH/Office V3 adjudicators and driver
  scripts, raw-data directories for Industrial/CDs, 10 Industrial FIR-BREADTH
  result JSONs, one CDs filter result, and a smoke result.

### Verdict

**The printed paper still passes its artifact gate, but the workspace has moved
past the paper's stated FIR-BREADTH status.** Industrial_and_Scientific now
mechanically confirms the causal FIR filter under the frozen internal paired
rule. CDs_and_Vinyl is incomplete/void. The top-journal risk is no longer
"partial result contamination"; it is scope and provenance: the paper says
pending/untested while the workspace contains an untracked favorable confirmed
result and an incomplete companion category.

### Commands And Evidence Checked

- `_bestrec_run/.venv/Scripts/python.exe _bestrec_run/adjudicate_fir_breadth.py --no-append`
  - Industrial_and_Scientific: `CONFIRMED`.
  - Per-seed NDCG@10 deltas: `+0.00243`, `+0.00196`, `+0.00191`,
    `+0.00287`, `+0.00284`.
  - Paired mean `+0.00240`, sd `0.00046`, 95% t-CI
    `[+0.00183, +0.00297]`, positive seeds `5/5`.
  - CDs_and_Vinyl: `VOID(incomplete)` with 1/10 runs present.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 mismatch; 0 untraceable; all 12 claim
    families sourced.
  - PASS: release manifest verification for 113 files.
  - PASS: MI V2 dual gate.
  - PASS/VOID-as-designed: Office descriptive adjudication.
- Source/code inspection:
  - `paper_tex/sections/04-experiments.tex` and `paper_tex/tables/table_datasets41.tex`
    still label Industrial_and_Scientific and CDs_and_Vinyl as pending.
  - `paper_tex/sections/06-discussion.tex` still says other categories are
    untested.
  - `_bestrec_run/run_sasrec_sbert.py` implements the FIR as left-padded
    depthwise Conv1d on right-padded sequences, supporting the leak-free claim.
- `git status --short`
  - Confirms the breadth result files, adjudicator, driver/prep scripts, and raw
    data are untracked.
- `paper_tex/hygiene_scan_output.txt`
  - Latest recorded scan passes: 39 pages, 0 placeholder/forbidden failures.

### Confirmed Problems

1. **Stale paper/workspace status.** The paper's pending/untested language is no
   longer true of the workspace if these new artifacts are part of the
   submitted evidence package.
2. **Incomplete paired campaign.** CDs_and_Vinyl is currently void by the
   campaign's own rule; it cannot be quietly ignored if Industrial is used.
3. **Untracked campaign boundary.** FIR-BREADTH evidence is not yet in the
   repository/release manifest/artifact graph. This undercuts a methodology-led
   paper unless fixed or explicitly excluded.
4. **Adjudication not recorded.** I used `--no-append` to avoid changing
   `FIR_BREADTH_RESULTS.md`; that file still does not exist unless another
   process creates it later. The confirmed Industrial verdict is therefore
   audit-observed, not yet campaign-recorded.

### Plausible Risks Requiring Author Verification

- Some FIR-BREADTH result manifests were generated with `git_dirty_tracked=true`
  because this audit file was dirty. The code hashes may still prove training
  identity, but a reviewer will expect a clean explanation if the result becomes
  confirmatory evidence.
- The positive Industrial result strengthens breadth for the FIR module but
  should not be allowed to inflate the paper into a general cross-category
  recommender claim. It is an internal paired filter-vs-no-filter result, not a
  comparator or SOTA result.
- The paper's "trustworthy-evaluation apparatus" framing raises the bar for
  process hygiene. Untracked favorable artifacts are more damaging under this
  framing than they would be in an ordinary empirical paper.

### External Fact-Check / Novelty Notes

- GrIT is a real 2026 arXiv preprint; its table reports Video Games NDCG@10
  `0.0588` under its listed setup. Source:
  https://arxiv.org/html/2602.19728v1
- WPGRec is a real 2026 time-frequency sequential-recommendation paper and the
  arXiv page says accepted to SIGIR 2026. This supports citing it as later
  frequency/time-frequency prior art, not as an apples-to-apples comparator.
  Source: https://arxiv.org/abs/2604.21305
- DiffuReason uses a different AR2023 "Video & Games" universe; the arXiv text
  lists 67,658 users / 25,535 items / 654,867 interactions, supporting the
  manuscript's non-comparability caveat. Source:
  https://arxiv.org/html/2602.09744
- Augment or Not? uses Amazon'23 Musical Instruments and Industrial and
  Scientific under 5-core leave-one-out, supporting the manuscript's
  "AR2023-adjacent, non-interchangeable" framing. Source:
  https://arxiv.org/html/2505.23053v1
- The Amazon Reviews 2023 project page confirms the dataset is collected in
  2023 and includes reviews, metadata, and links, with 571.54M reviews and
  standard splitting resources. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Decide whether FIR-BREADTH is inside or outside the current submission. If
   outside, exclude the untracked result files from the evidence bundle and keep
   the paper frozen as pre-breadth.
2. If FIR-BREADTH is inside, create the official adjudication record, commit the
   scripts/results/provenance, add manifest/artifact-gate coverage, and update
   Section 4.1/6.4 to say Industrial confirmed and CDs incomplete/void.
3. Preserve narrow wording: "Industrial_and_Scientific internal paired 5-seed
   filter-vs-no-filter improvement" only. No external comparator language.
4. Add a provenance note for dirty tracked state or rerun under a clean
   committed boundary if pristine confirmation is required.
5. Re-run PDF hygiene after any manuscript integration of FIR-BREADTH.

### Running Checklist

- [x] Read automation memory state.
- [x] Locate canonical TeX/Markdown/PDF sources and artifact files.
- [x] Inspect current audit file and preserve previous uncommitted sections.
- [x] Check working tree and new untracked campaign artifacts.
- [x] Run FIR-BREADTH adjudicator in no-append mode.
- [x] Run strict manuscript artifact rebuild.
- [x] Inspect FIR implementation for left-causal padding.
- [x] Fact-check recent-literature and dataset framing against primary sources.
- [x] Update this cumulative audit.
- [ ] Decide whether FIR-BREADTH enters the paper or remains excluded.
- [ ] Commit/hash campaign artifacts before any FIR-BREADTH claim is submitted.

## Audit Run - 2026-07-13 01:42 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` /
  `f50c7fdd6eb821a7c4012ea5abcd53662d691424`.
- Tracked manuscript/PDF/LaTeX diff since the 00:40 audit: none.
- Tracked working tree: `PAPER_REVIEW_AUDIT.md` modified.
- Untracked active-program files include the FIR-BREADTH and Office V3
  adjudicators, driver/prep scripts, raw-data provenance, 5 filter result JSONs,
  3 no-filter result JSONs, and the smoke result.
- Active process observed: `run_impact_program.sh` had advanced to
  `FIRB Industrial_and_Scientific nofilter seed 20260716`; I did not stop or
  modify it.

### Verdict

**The manuscript still has no new printed contradiction: it says the
FIR-BREADTH campaign is pending, and no breadth result is claimed.** The
rejection risk is now process contamination. Partial outcomes have been observed
before the untracked-tooling and dirty-tree defects were repaired. In a
methodology-first paper, that is central: the campaign can still be reported
honestly, but it should not be sold as a pristine confirmatory extension unless
it is restarted or accompanied by a blunt provenance erratum.

### Commands And Evidence Checked

- `git status --short --untracked-files=all`
  - Confirms only `PAPER_REVIEW_AUDIT.md` is tracked-dirty, while the impact
    driver, adjudicators, raw-data provenance, and FIR-BREADTH results are
    untracked.
- `git diff --name-only -- PAPER_SUBMISSION.md PAPER_DRAFT.md
  PAPER_SUBMISSION.pdf CANONICAL_SUBMISSION.md paper_tex`
  - Empty: the printed paper sources/artifacts have not changed since the 00:40
    strict rebuild/PDF-hygiene check.
- `_bestrec_run/impact_program.log`
  - The program began at `2026-07-13 00:25:03` from a dirty tracked tree
    containing manuscript, PDF, LaTeX, table, and reference changes.
  - Later FIR-BREADTH runs continued with `PAPER_REVIEW_AUDIT.md` dirty.
  - As of this audit, seed 20260716 no-filter was running.
- FIR-BREADTH JSON manifests:
  - Filter seeds 20260713-17 are present; no-filter seeds 20260713-15 are
    present.
  - Full-catalog `n_eval=50,985` for all observed Industrial_and_Scientific
    results checked.
  - Observed paired best-test NDCG@10:
    - seed 20260713: filter `0.033774047`, no-filter `0.031343612`,
      delta `+0.002430`.
    - seed 20260714: filter `0.033409370`, no-filter `0.031453663`,
      delta `+0.001956`.
    - seed 20260715: filter `0.032943585`, no-filter `0.031031976`,
      delta `+0.001912`.
  - Manifest dirtiness: filter 20260713 records `git_dirty_tracked=false`;
    filter 20260714-17 and no-filter 20260713-15 record
    `git_dirty_tracked=true`.
- `FIR_BREADTH_RESULTS.md`
  - Not present at audit time, so no mechanical adjudication block has been
    recorded yet.

### External Fact-Check / Source Notes

- The official AR2023 5-core page lists the relevant rounded category
  statistics: Industrial_and_Scientific 51.0K users / 25.8K items / 412.9K
  ratings; CDs_and_Vinyl 123.9K / 89.4K / split rows 1.3M train plus 123.9K
  validation/test; Musical_Instruments 57.4K / 24.6K / 511.8K; Office_Products
  223.3K / 77.6K / 1.8M; Video_Games 94.8K / 25.6K / 814.6K. Source:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- The AmazonReviews2023 benchmark README defines `last_out` as leave-last-out:
  latest review for test, second-latest for validation, rest for training, and
  `rating_only` as deduplicated user/item/rating/timestamp records with 0-core
  or 5-core filtering. Source:
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md
- HSTU-BLaIR's repository reports the comparator values used in the manuscript:
  Video_Games HSTU-BLaIR NDCG@10 `0.0760`, Office_Products `0.0271`, and
  Musical_Instruments `0.0406`, with a warning that reproduction can vary
  within a small margin. Source: https://github.com/snapfinger/HSTU-BLaIR

### Confirmed Problems

1. **The active FIR-BREADTH campaign is already result-exposed while its
   adjudication/run tooling is outside the committed boundary.** This violates
   the spirit, and likely the literal reviewer reading, of the prereg's
   "adjudication script committed with the campaign" sentence.
2. **The run driver intentionally allows dirty tracked state for FIR-BREADTH.**
   That may have been acceptable engineering convenience before the paper led
   with methodology; it is not strong enough for a top-journal confirmatory
   claim.
3. **Partial positive results are now known.** Even if the final 5-seed rule
   later confirms, the decision to keep, report, or expand the campaign is now
   post-outcome unless the authors explicitly freeze that choice or restart.
4. **The same dirty audit file will likely block Office V3.** The driver uses a
   hard clean-tree check for Office V3; unless the tracked tree is cleaned
   before the FIR-BREADTH segment completes, Office V3 should exit under its
   own condition 3 rather than run.

### Concrete Fixes To Make Next

1. For a pristine confirmatory claim: stop after the current run family,
   classify these Industrial/CDs outputs as contaminated/exploratory, commit
   the driver/adjudicators/prep scripts/provenance, and restart with new seeds.
2. For a less conservative but honest route: write a provenance erratum before
   any paper edit, listing the dirty launch state, the untracked tooling, every
   result manifest's `git_dirty_tracked` flag, code hashes, and the exact point
   at which partial results became visible.
3. Do not update `PAPER_SUBMISSION.md`, release notes, or responses with
   FIR-BREADTH numbers until all 5 paired seeds are complete and the mechanical
   adjudicator has run under a committed version.
4. If Office V3 is intended to proceed in the current driver, clean the tracked
   tree first; otherwise let the hard check stop it and record that stop as
   designed behavior.

### Open Questions

- Will the authors prefer a clean restart over a provenance erratum for
  FIR-BREADTH?
- Should FIR-BREADTH's driver be changed to hard-fail on dirty tracked state,
  matching Office V3, now that process integrity is the lead contribution?
- Should the pre-registration be amended to say "embedded code hashes" are
  sufficient, or is that amendment itself post-outcome and therefore a reason
  to restart?

### Running Checklist

- [x] Read automation memory state.
- [x] Preserve the existing 00:40 audit section.
- [x] Recheck active workspace and untracked artifacts.
- [x] Inspect current FIR-BREADTH result manifests and log.
- [x] Verify no tracked manuscript/PDF/LaTeX diff since the 00:40 artifact
      gate.
- [x] Fact-check AR2023 split/stat claims and HSTU-BLaIR comparator values
      against external sources.
- [ ] Resolve FIR-BREADTH governance before using any breadth result.
- [ ] Re-run strict build/PDF hygiene after the active GPU program is stopped
      or finished.
- [ ] Decide whether Office V3 should be allowed to stop on the clean-tree hard
      check or be relaunched from a clean boundary.

## Audit Run - 2026-07-13 00:40 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `f50c7fdd`
- Supplied last-run cutoff: `2026-07-12T13:35:29.596Z`.
- Commits after cutoff:
  - `a7d6733d` Impact-revision program: pre-registrations committed BEFORE any
    run.
  - `791de36a` Approach (C): methodology-first reframe -- retitled, apparatus
    leads, claims unchanged.
  - `14c3df2b` Regenerate RELEASE_MANIFEST at the reframe boundary.
  - `bbb728fe` Round-15: Section 4.1 rewritten as role-based dataset table;
    count definitions fixed; brittle phrasing.
  - `8ccd04f1` Regenerate RELEASE_MANIFEST at round-15 boundary.
  - `f50c7fdd` Respond to PAPER_REVIEW_AUDIT run 23:39.
- Tracked working tree at audit time: clean.
- Untracked/currently outside git boundary: impact-program scripts, two
  adjudicators, first FIR-BREADTH result, smoke result, and new raw-data
  downloads/provenance files.
- A FIR-BREADTH run was active during this audit:
  `Industrial_and_Scientific filter seed 20260714` (Python process observed at
  00:40, log at epoch 3/20). I did not stop or modify it.

### Verdict

**The previous hard manuscript defect is fixed, and the printed paper still
passes its strict artifact gate.** Section 4.1 now describes the dataset roles
and total counts clearly. The new top-journal rejection risk is not a table
value; it is governance around the newly launched impact/FIR-BREADTH program.
After the methodology-first reframe, process integrity is now part of the
paper's lead claim. The campaign currently has untracked adjudication/run
tooling and a start-of-run dirty-tree ambiguity. Those defects must be resolved
before any breadth result is printed as confirmatory.

### Commands And Evidence Checked

- `git log --oneline --decorate --since='2026-07-12T13:35:29Z'`
  - Shows the impact pre-registrations, methodology reframe, Section 4.1 repair,
    manifest regenerations, and response commit after the supplied cutoff.
- `git status --short --untracked-files=all`
  - Tracked tree clean, but untracked:
    `_bestrec_run/adjudicate_fir_breadth.py`,
    `_bestrec_run/adjudicate_office_v3.py`,
    `_bestrec_run/encode_impact_titles.py`,
    `_bestrec_run/prep_impact_data.py`,
    `_bestrec_run/run_impact_program.sh`,
    `_bestrec_run/results_FIRB_Industrial_and_Scientific_filter_seed20260713.json`,
    `_bestrec_run/smoke_FIRB_IS_seed1.json`, and new raw-data provenance files.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 claim
    families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office
    descriptive/VOID adjudication.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 39 pages; 0 placeholder/forbidden-claim failures.
- Source inspection:
  - `paper_tex/sections/04-experiments.tex` now states total 5-core
    interactions and the LLOO count rule.
  - `paper_tex/tables/table_datasets41.tex` includes all active/pending
    categories with roles and total counts.
  - `rg "two AR2023|~830k|5.17M|unreviewed concurrent"` no longer finds the old
    Section 4.1 defects or brittle "unreviewed concurrent" phrasing.
  - `rg "814,585"` still finds the comparator-paper count in Section 5.1; treat
    as a labeling/readability risk, not a reopened Section 4.1 defect.
- Local row-count checks:
  - Industrial_and_Scientific: total 412,947; train 310,977; valid 50,985; test
    50,985.
  - CDs_and_Vinyl: total 1,552,764; train 1,305,012; valid 123,876; test
    123,876.
- Impact-program evidence:
  - `_bestrec_run/impact_program.log` says preconditions passed, then printed a
    dirty tracked tree at `2026-07-13 00:25:03`, warned, and began
    `FIRB Industrial_and_Scientific filter k8 seed 20260713`.
  - `_bestrec_run/results_FIRB_Industrial_and_Scientific_filter_seed20260713.json`
    records `git_commit=f50c7fdd`, `git_dirty_tracked=false`, full-catalog
    `n_eval=50,985`, and best-by-validation test NDCG@10 0.033774. Because the
    run started before the commit boundary but recorded clean status at write
    time, the manifest does not by itself prove clean start-state provenance.
  - `_bestrec_run/adjudicate_fir_breadth.py` implements a sensible mechanical
    paired 5-seed rule, but it is untracked, contradicting
    `PREREG_FIR_BREADTH.md`'s statement that adjudication is committed with the
    campaign.

### Confirmed Fixes Since Prior Audit

1. **Section 4.1 role/scope inconsistency is fixed.**
   - The old "two categories" phrasing is gone.
   - Office is explicitly descriptive/VOID, not confirmatory.
   - Industrial_and_Scientific and CDs_and_Vinyl are explicitly pending, with no
     result claimed in this version.
2. **Dataset counts in the main table are now total counts.**
   - The table's Industrial/CDs counts match official rounded AR2023 statistics
     and the local exact row counts.
   - The LLOO relationship `train = total - 2 * users` is stated in Section 4.1.
3. **Brittle "unreviewed concurrent work" wording is removed.**
   - The paper now uses "concurrent arXiv-only work" and "status as of the
     access date" style phrasing.
4. **Current printed-paper artifact gate remains green.**
   - The methodology reframe and Section 4.1 table did not break the 164-cell
     rebuild or TORS hygiene scan.

### Confirmed Problems

1. **The FIR-BREADTH adjudication and run tooling are not frozen in git even
   though the pre-registration says the adjudication script is committed with
   the campaign.**
   - This undermines the paper's lead process claim if any breadth result is
     later used.
   - Concrete fix: commit/hash the adjudicator, driver, data-prep script,
     encoder script, and raw-data provenance before adjudication; update
     `RELEASE_MANIFEST.json` once any result is printed. If strict confirmatory
     purity is required, void/restart with new seeds under a clean committed
     tooling boundary.
2. **The first FIR-BREADTH campaign run has start-state provenance ambiguity.**
   - Program log: dirty tracked tree at run launch.
   - Result JSON: clean tracked tree at result write.
   - Concrete fix: either treat the existing FIR-BREADTH run family as
     exploratory/contaminated, or add an explicit erratum proving that the dirty
     tracked diffs were documentation-only and that training-code hashes were
     identical from launch through write. A top-journal reviewer will likely
     prefer the former.
3. **Partial results exist while the paper says the campaign outcome is
   pending.**
   - This is currently acceptable because no breadth result is claimed, but the
     paper must not be edited to exploit the observed first seed. Once the
     campaign finishes, report confirmed/null/void symmetrically and manifest
     every printed value.

### Plausible Risks Requiring Author Verification

- **The methodology-first reframe raises the standard for process evidence.**
  It makes the paper more coherent, but also turns any process blemish into a
  central weakness. If the authors want this framing, they should harden the
  new campaign rules rather than allow warn-and-proceed dirty-tree behavior.
- **The 814,585 vs 814,586 interaction-count split may still annoy reviewers.**
  Keep the +/-1 comparator-pipeline caveat, but label Section 5.1's 814,585 as
  the HSTU-BLaIR-reported comparator count.
- **SILLM4Rec remains a direct-inspection item.** The current exclusion sentence
  is narrow enough, but final submission should either inspect the paper or keep
  the exclusion carefully metadata-scoped.
- **The currently running seed may finish while this audit section is being
  read.** Re-run the status checks before making any release/deposit decision.

### External Fact-Check / Novelty Notes

- Official Amazon Reviews 2023 5-core statistics list
  Industrial_and_Scientific at 51.0K users / 25.8K items / 412.9K ratings,
  CDs_and_Vinyl at 123.9K / 89.4K / 1.6M, Musical_Instruments at 57.4K /
  24.6K / 511.8K, Office_Products at 223.3K / 77.6K / 1.8M, and Video_Games at
  94.8K / 25.6K / 814.6K. Source:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- The AmazonReviews2023 benchmark README defines `rating_only` as user/item/
  rating/timestamp records, removes duplicate user-item reviews, applies
  k-core filtering, and defines `last_out` as leave-last-out with latest review
  for test, second-latest for validation, and the rest for train. Source:
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md
- HSTU-BLaIR's repository reports the comparator rows used by the paper:
  Video_Games HSTU-BLaIR NDCG@10 0.0760, Office_Products 0.0271, and
  Musical_Instruments 0.0406; it also warns that reproduction may vary by a
  small margin. Source: https://github.com/snapfinger/HSTU-BLaIR
- Ferrari Dacrema et al. support the paper's evaluation-trust motivation: their
  abstract says only 7 of 18 neural recommender algorithms were reproducible
  with reasonable effort, and 6 of those could often be beaten by simple
  heuristics. Source: https://arxiv.org/abs/1907.06902

### Concrete Fixes To Make Next

1. Decide whether the current FIR-BREADTH campaign is confirmatory or
   exploratory. For a top-journal confirmatory claim, the safest action is
   VOID/restart with a clean committed tool boundary and new seeds.
2. Commit the impact-program tooling and adjudicators before any further
   adjudication or Office V3 run is used as evidence.
3. Add a provenance erratum if any current FIR-BREADTH artifacts are retained:
   exact start/end commit, dirty tracked files at launch, code hashes, and why
   start-dirty did or did not void the claim.
4. Keep all breadth numbers out of the paper until the full paired 5-seed rule
   is adjudicated and the values are added to the artifact gate/manifest.
5. Label the Section 5.1 `814,585` interaction count as comparator-reported, or
   add a short parenthetical: local row total is 814,586; comparator pipeline
   reports 814,585.
6. Add one sentence in the methodology-reframe paragraph that this is an
   auditable case-study discipline, not a claim to have invented
   pre-registration, artifact evaluation, or standardized benchmarking.

### Open Questions

- Are the maintainers willing to void/restart FIR-BREADTH to preserve a clean
  confirmatory story, or should it be downgraded to exploratory evidence?
- Was the dirty tracked tree at FIR-BREADTH launch entirely documentation/PDF
  state, or did any code or generated table script that could affect claims
  differ from the eventual commit?
- Should the run driver enforce clean tracked tree for FIR-BREADTH just as it
  already does for Office V3, given the paper's new methodology-first framing?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript sources and PDFs.
- [x] Check commits and working-tree state after the supplied cutoff.
- [x] Verify strict rebuild/provenance gate.
- [x] Verify TORS PDF hygiene scan.
- [x] Confirm Section 4.1 role table and total-count repair.
- [x] Verify new Industrial/CDs local row counts.
- [x] Fact-check AR2023 count/split claims and HSTU-BLaIR comparator values
      against external sources.
- [x] Inspect new impact pre-registration, driver, adjudicator, logs, and first
      result manifest.
- [ ] Resolve FIR-BREADTH untracked-tooling and start-dirty provenance risk
      before claiming any breadth result.
- [ ] Re-run audit after the active FIR-BREADTH job completes or is stopped.

## Audit Run - 2026-07-12 23:39 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `8d060297`
- Supplied last-run cutoff: `2026-07-12T12:35:58.679Z`.
- `git log --since="2026-07-12T12:35:58Z"` returned no commits. The tracked
  working tree was clean before and after this audit.
- Automation memory at start still described the 21:37 run's top watch items:
  the Section 3.2 HSTU/SASRec contradiction and stale WPGRec metadata.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/sections/01-introduction.tex`,
  `paper_tex/sections/03-method.tex`,
  `paper_tex/sections/04-experiments.tex`,
  `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/07-conclusion.tex`, `paper_tex/references.bib`,
  `paper_tex/tables/table0_novelty.tex`, local AR2023 5-core CSV splits, and
  the strict rebuild/provenance scripts.

### Verdict

**The two prior top blockers are repaired, and the artifact graph remains
green.** The remaining reviewer-facing problem is Section 4.1: it understates
the experimental scope ("two" categories) and mixes total interaction counts
with train-only counts. A strict reviewer can read this as sloppy protocol
description, even though the downstream results/provenance are internally
traceable.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T12:35:58Z" --oneline --decorate --name-status`
  - No commits after the supplied cutoff.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office descriptive/
    VOID adjudication.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures.
  - SOTA/paired-superiority mentions are negated or informational.
- PDF text extraction with `pypdf` through the repo `uv` environment
  - Both PDFs no longer contain "Our base model" or "2-layer Transformer
    encoder".
  - Both PDFs contain the new "Headline encoder" text.
  - Both PDFs contain WPGRec in references with non-stale accepted/SIGIR 2026
    wording, though not always in the exact same extracted string.
  - `PAPER_SUBMISSION.pdf` contains "partially resolves the open mechanism";
    the TORS PDF uses the more scoped "partial causal role" conclusion wording.
- Local CSV counts with `Measure-Object -Line`
  - Video_Games `rating_only`: 814,587 lines including header -> 814,586 rows.
  - Video_Games split rows: 625,062 train + 94,762 valid + 94,762 test =
    814,586.
  - Musical_Instruments `rating_only`: 511,837 lines including header ->
    511,836 rows.
  - Musical_Instruments split rows: 396,958 train + 57,439 valid + 57,439 test
    = 511,836.
  - Beauty_and_Personal_Care `rating_only`: 6,624,442 lines including header ->
    6,624,441 rows.
  - Beauty split rows: 5,165,289 train + 729,576 valid + 729,576 test =
    6,624,441.
  - Office_Products `rating_only`: 1,800,879 lines including header ->
    1,800,878 rows.
  - Office split rows: 1,354,262 train + 223,308 valid + 223,308 test =
    1,800,878.

### Confirmed Fixes Since Prior Audit

1. **Section 3.2 method contradiction is repaired.**
   - Source now describes shared item-feature construction, then the HSTU-style
     headline encoder, then the SASRec-SBERT baseline.
   - Section 4.3 points to the HSTU-style encoder and uses the same 4-layer
     configuration.
   - Rendered PDFs no longer expose the stale SASRec-as-headline wording.
2. **WPGRec metadata is repaired.**
   - `paper_tex/references.bib` now says WPGRec is accepted to SIGIR 2026.
   - `PAPER_SUBMISSION.pdf` renders "SIGIR 2026 (accepted; arXiv:2604.21305)".
   - `paper_tex/PAPER_TORS.pdf` renders "Accepted to SIGIR 2026".
3. **Mechanism rhetoric is materially toned down.**
   - The abstract now says the user-mode titration "partially resolves the open
     mechanism (under the thinning intervention's assumptions)".
   - The conclusion states that collaborative connectivity is "consistent with
     a partial causal role" and repeats that these are controlled interventions,
     not causal identification of the real-world generative process.

### Confirmed Problems

1. **Section 4.1 does not match the paper's current experimental scope.**
   - It says "We evaluate on two AR2023 5-core categories" and lists only
     Video_Games and Beauty_and_Personal_Care.
   - The abstract, Section 5, and conclusion make Musical_Instruments a
     headline cross-category confirmation. Office_Products also appears as a
     descriptive/VOID pre-registration result.
   - Concrete fix: rewrite Section 4.1 as a role-based dataset table with all
     categories used anywhere in the paper, including which are confirmatory,
     exploratory, appendix-only, or VOID/descriptive.
2. **Section 4.1 mixes interaction-count definitions.**
   - Video_Games is listed as "~830k interactions" while later Section 5.1 says
     814,585 and local data give 814,586 rows after header.
   - Beauty is listed as 5.17M interactions, which matches train-only rows, not
     total 5-core rows (6,624,441). A reader will not know whether counts mean
     total rating-only interactions or train interactions after LLOO.
   - Concrete fix: state both totals and split counts, or state only totals in
     Section 4.1 and move train counts to an appendix/protocol table.

### Plausible Risks Requiring Author Verification

- **SILLM4Rec is closer than a metadata-only footnote suggests.** ACM metadata
  says the paper experiments on three AR2023 5-core subdatasets, including
  Video_Games, and the GitHub repo describes generation of candidate product
  ranking tasks. That still does not prove identical full-catalog LLOO
  comparability, but it does make "excluded pending direct protocol inspection"
  the right stance.
- **"Unreviewed concurrent work" is a brittle phrase.** SID-MLP, Latte, and
  GrIT still look like arXiv-only works in the sources checked here, but peer
  review status can change. Prefer "concurrent arXiv works" if the sentence does
  not need a review-status claim.
- **Reader burden remains high.** The abstract is now more defensible, but it
  still carries many p-values, caveats, and mechanism claims. Table 2 remains
  valuable but dense.

### External Fact-Check / Novelty Notes

- WPGRec arXiv confirms the title, wavelet-packet/graph-enhanced framing, and
  "Accepted to SIGIR 2026" comment:
  https://arxiv.org/abs/2604.21305
- The SIGIR 2026 accepted-papers page also lists WPGRec:
  https://sigir2026.org/en-AU/pages/program/accepted-papers
- SID-MLP arXiv page shows only arXiv metadata and no accepted-venue comment in
  the opened page:
  https://arxiv.org/abs/2605.12617
- Latte arXiv page shows only arXiv metadata and no accepted-venue comment in
  the opened page:
  https://arxiv.org/abs/2605.06331
- GrIT search/open metadata remains arXiv-preprint style:
  https://arxiv.org/abs/2602.19728
- SILLM4Rec ACM/GitHub pages confirm MMAsia 2025 publication context and
  AR2023 5-core / candidate-ranking relevance, but not full-catalog LLOO
  equivalence from accessible metadata:
  https://dl.acm.org/doi/10.1145/3743093.3771011
  https://github.com/MKC-Lab/SILLM4Rec
- Official Amazon Reviews 2023 5-core statistics list Video_Games at 94.8K
  users, 25.6K items, 814.6K ratings; Musical_Instruments at 57.4K users,
  24.6K items, 511.8K ratings; Beauty_and_Personal_Care at 729.6K users,
  207.6K items, 6.6M ratings; Office_Products at 223.3K users, 77.6K items,
  1.8M ratings:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- The AmazonReviews2023 benchmark scripts define 5-core `rating_only` and
  `last_out` leave-last-out splits, with latest interaction as test,
  second-latest as validation, and remaining interactions as train:
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md

### Concrete Fixes To Make Next

1. Rewrite Section 4.1 as a dataset/protocol table with category role, total
   rows, train/valid/test rows, users, items, and which paper claims depend on
   the category.
2. Replace Video_Games "~830k" and later "814,585" with one consistent value:
   814,586 local rows, or 814.6K when rounded.
3. Decide whether Beauty's 5.17M should be labeled "train interactions" or
   replaced by total 6.62M in the dataset list.
4. Keep SILLM4Rec excluded only under the narrow protocol-inspection caveat, or
   inspect the ACM full text and add a short non-comparability sentence.
5. Before final submission, recheck whether SID-MLP, Latte, or GrIT acquired
   accepted-venue metadata; otherwise avoid "unreviewed" in favor of
   "concurrent arXiv".

### Open Questions

- Should Office_Products appear in the main dataset table as "VOID/descriptive"
  or be moved entirely to appendix/pre-registration material?
- Should the paper report both total and train-only interaction counts, or only
  totals in the main dataset description?
- Can the authors access the full SILLM4Rec ACM paper to audit candidate-set
  construction, ranking universe, and whether metrics are full-catalog LLOO?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript sources and PDFs.
- [x] Check commits and tracked tree after the supplied last-run cutoff.
- [x] Verify strict rebuild/provenance gate.
- [x] Verify TORS PDF hygiene scan.
- [x] Confirm prior Section 3.2 methods fix in source and PDFs.
- [x] Confirm WPGRec SIGIR 2026 status in source and rendered references.
- [x] Fact-check current concurrent-work and SILLM4Rec status with external
  sources.
- [x] Verify local AR2023 category row counts and identify Section 4.1 scope/
  count inconsistency.

## Audit Run - 2026-07-12 21:37 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `3a346d86`
- Automation memory at start: no prior memory content was present at
  `$CODEX_HOME/automations/hourly-strict-paper-audit/memory.md`.
- Supplied last-run cutoff: `2026-07-12T10:34:56.879Z`.
- `git log --since="2026-07-12T10:34:56Z"` returned no commits; tracked working
  tree was clean before and after the strict rebuild.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/sections/03-method.tex`,
  `paper_tex/sections/04-experiments.tex`, `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`, `paper_tex/sections/appendix-a.tex`,
  `paper_tex/references.bib`, `paper_tex/tables/TABLES_PROVENANCE.json`,
  `paper_tex/tables/table0_novelty.tex`, `_bestrec_run/hstu_results_manifest.json`,
  and representative result JSONs for VG/MI headline runs.

### Verdict

**Artifact/provenance gates are green and the previous MLP-adaptor contradiction
is repaired, but the current manuscript has a new high-salience methods
contradiction.** The paper's numerical story is traceable; the problem is that
Section 3.2 still reads like the headline model is a 2-layer SASRec/Transformer,
while every headline run and the artifact graph say the model is a 4-layer
HSTU-style encoder. A top-journal reviewer can cite this as an unclear or stale
method description even if all results are valid.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T10:34:56Z" --oneline --decorate --name-status`
  - No commits after the supplied cutoff.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office descriptive/
    VOID adjudication.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures.
  - SOTA mentions are informational and negated/non-claim contexts.
- PDF text extraction with `pypdf`
  - Both PDFs contain the repaired Section 6.1 language ("text content, not the
    projection layer") and Appendix A.1's "MLP adaptor by itself does NOT help".
  - Both PDFs no longer contain the stale phrase "only consistently-positive
    intervention".
  - Both PDFs still contain WPGRec; neither mentions SIGIR 2026 acceptance.
- Targeted source/result sweeps
  - `paper_tex/sections/03-method.tex`: "Our base model, SASRec-SBERT" and
    "2-layer Transformer encoder".
  - `paper_tex/sections/04-experiments.tex`: headline runs use HSTU-style
    encoder with `d_model 64, 4 layers, 2 heads, dropout 0.5`.
  - Representative result JSONs confirm `encoder: hstu`, `n_layers: 4`,
    `n_heads: 2`, `dropout: 0.5`.

### Confirmed Problems

1. **Method architecture description is internally inconsistent.**
   - Source conflict: Section 3.2 presents the "base model" as SASRec-SBERT
     with a 2-layer Transformer; Section 3.7 says the additions are defined on
     top of HSTU-style; Section 4.3 says all headline results use HSTU-style
     `4 layers`; result JSONs confirm HSTU/4-layer for the headline runs.
   - Why this matters: the paper asks reviewers to trust fine-grained
     architectural deltas. A stale method section undermines reproducibility and
     makes it unclear whether Table 1 is a SASRec or HSTU-style ablation.
   - Concrete fix: rewrite Section 3.2 as "Item-feature construction and
     scoring" plus "Headline HSTU-style encoder"; demote SASRec-SBERT to
     baseline/protocol-parity wording; move the HSTU equation into Section 3.2
     or point Section 4.3 to the exact HSTU subsection; state `4 layers, 2
     heads, d=64, dropout=0.5` once in the method and once in experiments.
2. **WPGRec reference metadata is stale.**
   - `PAPER_SUBMISSION.md` and `paper_tex/references.bib` still put WPGRec under
     an "unreviewed at the time of writing" preprint framing.
   - arXiv metadata for `2604.21305` says WPGRec was accepted to SIGIR 2026.
   - Concrete fix: remove WPGRec from the unreviewed-preprint umbrella or revise
     the note to "accepted to SIGIR 2026; arXiv:2604.21305"; keep it as broader
     frequency/time-frequency prior art, not an apples-to-apples AR2023
     comparator.

### Confirmed Fixes Since Prior Audit

- **Section 6.1 / Appendix A.1 MLP-adaptor contradiction is repaired.** The
  current source and both PDFs now say the Beauty signal is attributable to
  BLaIR/rich text as a bundle, while the clean MiniLM+MLP adaptor ablation is
  negative.
- **SILLM4Rec tooling-language leak remains fixed.** The manuscript no longer
  says a paper was inaccessible to "our tooling"; the current sentence says
  accessible metadata did not establish apples-to-apples protocol comparability.
- **Artifact gates remain green.** Strict rebuild, table provenance, release
  manifest, PDF hygiene scan, and tracked working tree all pass.

### Plausible Risks Requiring Author Verification

- **SILLM4Rec direct protocol inspection is still open.** The public GitHub repo
  instructs users to download Amazon Reviews 2023 5-core files and generate
  candidate ranking tasks, which makes the paper more relevant than a metadata-
  only mention. However, the accessible repo does not establish full-catalog
  LLOO equivalence, so exclusion remains defensible only if narrowly worded.
- **"Resolves the open mechanism" overstates the tail evidence.** The user-mode
  titration supports a partial mechanism under synthetic thinning assumptions;
  it does not fully resolve the real data-generating mechanism. This is a
  rhetoric risk, not a numeric contradiction.
- **Reader burden remains high.** The abstract, Section 5, and Table 2 are
  unusually dense. The honesty is useful, but a reviewer may miss the core
  contribution behind caveats and negative-result detail.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv HTML confirms the AR2023 5-core statistics and comparator
  constants used by the manuscript: Video Games 25,612 items / 94,762 users /
  814,585 interactions, NDCG@10 0.0760; Musical Instruments NDCG@10 0.0406;
  Office Products NDCG@10 0.0271. Source:
  https://arxiv.org/html/2504.10545v3
- SID-MLP's arXiv HTML confirms same-statistics AR2023 5-core LLOO datasets for
  MI/VG: Musical Instruments 57,439 users / 24,587 items / 511,836
  interactions and Video Games 94,762 users / 25,612 items / 814,586
  interactions. Source: https://arxiv.org/html/2605.12617v1
- WPGRec's arXiv page confirms it is a wavelet-packet, graph-enhanced
  sequential recommendation paper and says "Accepted to SIGIR 2026"; this
  supports the manuscript's broader frequency/time-frequency boundary but
  invalidates the "unreviewed" metadata note. Source:
  https://arxiv.org/abs/2604.21305
- The SILLM4Rec public repo confirms relevance to Amazon Reviews 2023 5-core
  data preparation and generated ranking tasks, but the accessible README does
  not establish full-catalog LLOO comparability. Source:
  https://github.com/MKC-Lab/SILLM4Rec
- The official Amazon Reviews 2023 site remains the correct dataset source and
  documents the 5-core processing caveats and category statistics. Sources:
  https://amazon-reviews-2023.github.io/ and
  https://amazon-reviews-2023.github.io/data_processing/5core.html

### Concrete Fixes To Make Next

1. Repair Section 3.2 / 3.7 / 4.3 architecture wording before any submission:
   make the headline HSTU-style 4-layer encoder the main method and label
   SASRec-SBERT as baseline/protocol-parity only.
2. Rebuild both PDFs and rerun text extraction for the phrases "2-layer
   Transformer encoder" and "4 layers" after the method fix.
3. Update WPGRec metadata to SIGIR 2026 accepted status, and remove it from any
   blanket "unreviewed" preprint sentence.
4. Keep SILLM4Rec excluded unless the full paper is inspected; if mentioned,
   keep the current narrow "not established as apples-to-apples full-catalog
   LLOO" wording.
5. Tone down "resolves the open mechanism" to "partially resolves" or "supports
   a partial mechanism under the thinning intervention."

### Open Questions

- Should the Method section be organized around the headline HSTU-style stack
  only, with SASRec-family details moved to baselines/appendix, or should it
  explicitly describe two model families?
- Can the authors obtain SILLM4Rec's full ACM PDF to inspect its exact
  evaluation protocol?
- Is WPGRec's SIGIR 2026 acceptance enough to move it from a reference note into
  the related-work prose, or is the current one-sentence boundary sufficient?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript sources and PDFs.
- [x] Check commits and tracked tree after the supplied last-run cutoff.
- [x] Verify strict rebuild/provenance gate.
- [x] Verify TORS PDF hygiene scan.
- [x] Verify prior Section 6.1 MLP-adaptor contradiction is absent from PDFs.
- [x] Fact-check selected novelty/comparator claims against external sources.
- [x] Identify new confirmed methods inconsistency.
- [x] Identify stale WPGRec bibliographic metadata.
- [ ] Rewrite Method architecture section for HSTU-style 4-layer headline stack.
- [ ] Update WPGRec SIGIR 2026 metadata and rerender references.
- [ ] Protocol-inspect SILLM4Rec full text if accessible before freeze.

## Audit Run - 2026-07-12 18:37 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `395d472f` (`Respond to
  PAPER_REVIEW_AUDIT run 17:35: tooling-leak removed, artifact roles explicit`)
- Automation memory at start: no prior memory file found at
  `$CODEX_HOME/automations/hourly-strict-paper-audit/memory.md`.
- Working tree before writing this audit: clean.
- Files modified after the supplied cutoff (`2026-07-12T07:32:54.215Z`):
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`,
  `_paper_render.html`, `paper_tex/sections/05-results.tex`,
  `paper_tex/tables/*`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_tables.json`, and `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`, `paper_tex/sections/appendix-a.tex`,
  `paper_tex/tables/table0_novelty.tex`, `paper_tex/tables/table1.tex`,
  `paper_tex/tables/tableV2conf.tex`, `paper_tex/tables/table56_theirs.tex`,
  `paper_tex/references.bib`, `paper_tex/hygiene_scan_output.txt`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, and this audit file.

### Verdict

**Strict artifact/provenance gate remains green, but the manuscript has a
confirmed self-contradiction that a top-journal reviewer can cite directly.**
The contradiction is not numerical: it is the interpretation of the Beauty
cross-pipeline scan. Section 6.1 says the MLP adaptor is the only consistently
positive intervention and hypothesizes why it helps; Appendix A.1 later says the
clean MiniLM-only MLP-adaptor ablation drops performance and that the observed
gain comes from changing the text encoder and content, not the projection layer.

This should be fixed before any submission freeze. It is a high-salience
internal-consistency defect because both statements are in the rendered PDFs.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results` before writing this audit.
- Modified-since-cutoff scan from `2026-07-12T07:32:54.215Z`
  - Confirms the latest substantive changes are the manuscript/PDF/table rebuild
    and response files after the previous audit response.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py
  --verify`
  - PASS: 113 files verified.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office
    descriptive/VOID adjudication.
- `pdfinfo` via bundled Poppler direct executable
  - `PAPER_SUBMISSION.pdf`: 41 pages, letter, generated 2026-07-12 18:27.
  - `paper_tex/PAPER_TORS.pdf`: 36 pages, letter, generated 2026-07-12 18:27.
- PDF text extraction with `pypdf` under `uv`
  - `PAPER_SUBMISSION.pdf`: Section 6.1 contradiction on page 30; appendix
    clean-ablation correction on page 39.
  - `paper_tex/PAPER_TORS.pdf`: same contradiction on page 27 and appendix
    correction on page 35.
- Poppler page renders inspected visually
  - `tmp/pdfs/audit_20260712_1830/paper_submission_p-30.png`: Section 6.1
    visibly says "only consistently-positive intervention is the MLP-adaptor."
  - `tmp/pdfs/audit_20260712_1830/paper_tors_27_single.png`: same text visible
    in the TORS PDF.
  - `tmp/pdfs/audit_20260712_1830/paper_tors_p-35.png`: appendix visibly says
    "The MLP adaptor by itself does NOT help on this protocol."
- Targeted `rg` sweeps
  - `not accessible to our tooling` is gone.
  - SILLM4Rec is now excluded using neutral protocol-auditability wording.
  - `\keywords{...}` is present in `paper_tex/paper-shared.tex`.

### Confirmed Problems

1. **Section 6.1 contradicts Appendix A.1 on the MLP adaptor.**
   - Section 6.1: "the only consistently-positive intervention is the
     MLP-adaptor design" and "the 2-layer MLP can also denoise the BLaIR
     features."
   - Appendix A.1: the clean MiniLM + MLP adaptor row is 0.01889, worse than
     the MiniLM + Linear baseline around 0.0190; the text says the MLP adaptor
     by itself does not help and the observed +1.3-2.3% comes from MiniLM ->
     BLaIR plus titles -> rich text, not projection-layer form.
   - Why this matters: the current paper asks reviewers to trust an unusually
     complex artifact/provenance story. A direct internal contradiction in the
     discussion weakens that trust even though the numeric artifact gate passes.

### Plausible Risks Requiring Author Verification

- **The Beauty cross-pipeline scan may not deserve body discussion anymore.**
  The paper already frames it as appendix/supporting material, and the headline
  spine is causal FIR + tail pattern. Consider deleting Sections 6.1-6.2 or
  replacing them with a shorter "superseded supporting scan" paragraph.
- **SILLM4Rec may still need a freeze-time full-paper inspection.** Search/ACM
  metadata confirms the paper exists and says it uses three 5-core AR2023
  subdatasets, but accessible metadata did not establish the exact
  full-catalog-LLOO protocol needed for apples-to-apples comparison.
- **The abstract remains very dense.** Its caveats are mostly correct, but a
  reviewer may still see too many results, p-values, and mechanism claims before
  the method is introduced. This is a readability/reviewer-fatigue risk, not a
  contradiction.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv HTML confirms the paper uses AR2023 5-core subsets and
  reports the comparator constants the manuscript relies on: Video Games
  HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271, and Musical Instruments
  0.0406; its dataset statistics match the paper's quoted users/items for the
  HSTU-BLaIR-family protocol. Source:
  https://arxiv.org/html/2504.10545v3
- GrIT (arXiv:2602.19728) reports AR2023 Video Games with 94,762 users, 25,612
  items, 814,586 interactions, 5-core filtering, full-item-set evaluation, and
  NDCG@10 0.0588 for GrIT. The manuscript's "numerically higher but no
  comparative claim" framing is appropriate. Source:
  https://arxiv.org/html/2602.19728v1
- Latte (arXiv:2605.06331) reports Amazon Reviews 2023 Instruments/Scientific/
  Games and includes Latte NDCG@10 values 0.0331 (Instruments) and 0.0515
  (Games) in the RQ-KMeans row, supporting the manuscript's values. Source:
  https://arxiv.org/pdf/2605.06331
- SILLM4Rec metadata confirms a real MMAsia 2025 paper with DOI
  `10.1145/3743093.3771011`; search snippets from ACM state experiments use
  three 5-core Amazon Reviews 2023 subdatasets, but the accessible metadata
  checked here did not establish full-catalog LLOO comparability. Source:
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Concrete Fixes To Make Next

1. Rewrite `PAPER_SUBMISSION.md` Section 6.1 from "MLP adaptor transfer" to
   "BLaIR/rich-text content transfer, with MLP alone negative in the clean
   ablation." Remove the denoising hypothesis unless it is clearly scoped to
   BLaIR-rich-text + MLP as an inseparable bundle.
2. Apply the same correction to `PAPER_DRAFT.md` and the LaTeX twin
   `paper_tex/sections/06-discussion.tex`.
3. Rerender both PDFs and confirm extraction no longer contains the phrase
   "only consistently-positive intervention is the MLP-adaptor."
4. Optional: collapse Sections 6.1-6.2 into one short appendix-pointer paragraph
   to keep the body focused on the headline results.
5. Before freeze, obtain/inspect the SILLM4Rec full text if available; otherwise
   keep the current neutral exclusion sentence.

### Open Questions

- Does the author want to preserve the Beauty scan as interpretive discussion,
  or retain it only as an appendix/provenance record?
- Is SILLM4Rec full text available through institutional access? If yes, it
  should be protocol-inspected, not left as metadata-only.

### Running Checklist

- [x] Locate canonical manuscript source and PDFs.
- [x] Read prior audit and response trail.
- [x] Check files changed after the supplied last-run cutoff.
- [x] Verify release manifest.
- [x] Run strict rebuild/provenance gate.
- [x] Inspect latest PDF page counts and rendered pages.
- [x] Fact-check key comparator/recent-literature claims against primary or
      reliable sources.
- [x] Identify a new confirmed reviewer-facing contradiction.
- [ ] Rewrite Section 6.1 / LaTeX discussion to match Appendix A.1.
- [ ] Rerender PDFs after the prose fix.
- [ ] Protocol-inspect SILLM4Rec full text if accessible before submission
      freeze.

## Audit Run - 2026-07-12 17:35 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `a53a9013` (`Respond to
  PAPER_REVIEW_AUDIT run 16:32: coverage clause (iv), CCS/keywords closed`)
- Working tree before writing this audit: clean.
- Commits since supplied last-run cutoff (`2026-07-12T06:31:53Z`):
  `2fcfb06f` (AR2023-adjacent clause, CCS concepts, keywords, references, PDF
  rebuild), `8fb5c21a` (manifest regeneration), `a53a9013` (response log).
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `CANONICAL_SUBMISSION.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `paper_tex/paper-shared.tex`, `paper_tex/sections/05-results.tex`,
  `paper_tex/references.bib`, `paper_tex/tables/tableA1.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/hygiene_scan_output.txt`, and
  `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No numerical, provenance, or claim-boundary rejection defect found.** The
strict rebuild remains green, and the new recent-literature paragraph materially
improves the prior coverage risk. The only new confirmed problem is writing and
submission-polish level: the paper should not tell reviewers that a paper was
excluded because it was inaccessible to "our tooling." Also, the metadata fix is
closed for the TORS LaTeX artifact but not for the markdown-rendered PDF, so the
submission role of `PAPER_SUBMISSION.pdf` should stay explicit.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T06:31:53Z" --oneline --decorate --name-status`
  - Confirms the three expected commits after the prior audit cutoff.
- `git diff --stat` and targeted `git diff`
  - No uncommitted manuscript or artifact drift before this audit edit.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate.
  - PASS/VOID: Office remains descriptive and VOID under the preregistered floor
    check.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py
  paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures.
  - Informational SOTA list remains negated/non-claim contexts.
- PDF text extraction via `pypdf` under the project `uv` runtime
  - `paper_tex/PAPER_TORS.pdf`: 36 pages; contains `CCS Concepts`, DiffuReason,
    SILLM4Rec, "full text was not accessible", and the new AR2023-adjacent
    clause. Extraction did not find the literal string `Keywords`, likely
    because acmart renders the keyword label differently.
  - `PAPER_SUBMISSION.pdf`: 41 pages; contains Augment or Not, DiffuReason,
    SILLM4Rec, "full text was not accessible", and the new AR2023-adjacent
    clause; extraction did not find `CCS Concepts` or `Keywords`.
- Targeted wording sweep
  - `PAPER_SUBMISSION.md` / `paper_tex/sections/05-results.tex` no longer have
    the old first/only AR2023 wording and still keep Video_Games as non-SOTA.
  - `paper_tex/sections/05-results.tex` now contains the audit-requested clause
    `(iv) Other AR2023-adjacent, non-interchangeable protocols`.

### Confirmed Problems

1. **Manuscript leaks audit/tooling process into the SILLM4Rec sentence.**
   Current wording: "A further candidate (SILLM4Rec) is not cited pending direct
   protocol inspection (its full text was not accessible to our tooling at the
   time of writing)." A journal paper can say protocol details were not available
   in the accessible metadata; it should not mention "our tooling." This is a
   small but real reviewer-confidence issue.
2. **The CCS/keyword closure is artifact-specific.** The TORS LaTeX source and
   `PAPER_TORS.pdf` now contain ACM CCS concepts, but `PAPER_SUBMISSION.pdf`
   does not. If the markdown PDF remains a public reader artifact, this is fine;
   if it is treated as a submission artifact, the prior metadata finding is not
   fully closed.

### Plausible Risks Requiring Author Verification

- **SILLM4Rec may be relevant but is not protocol-audited from accessible
  metadata.** Search/ACM/ResearchGate metadata confirms the paper exists
  (`SILLM4Rec: Self-Improving with Chain of Thought Enhanced Preference
  Optimization for Multimodal Recommendation`, MMAsia 2025, DOI
  `10.1145/3743093.3771011`), but the accessible metadata did not provide enough
  protocol detail to decide whether it belongs in the AR2023 5-core paragraph.
  Keep it excluded unless the PDF can be inspected directly; if mentioned, use a
  neutral note such as "excluded pending direct protocol inspection."
- **The response log overstates the metadata verification.**
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` says both PDFs had CCS/keywords verified
  in extraction, but the extraction check here finds that only the TORS artifact
  carries CCS. This is not a paper defect if the response log is historical
  correspondence, but it should not be copied into submission metadata.
- **Table 2 and first-page review-mode text remain standing polish risks.**
  Nothing in this run worsens them.

### External Fact-Check / Novelty Notes

- `Augment or Not?` is correctly AR2023-adjacent but non-interchangeable: it
  uses Amazon'23 Musical Instruments and Industrial and Scientific under 5-core
  leave-one-out, and its table reports LETTER-TIGER Musical Instruments
  NDCG@10 = 0.0282. Source:
  https://arxiv.org/html/2505.23053v1
- `DiffuReason` is correctly non-comparable to this paper's Video_Games result:
  it reports a different AR2023 Video & Games universe (67,658 users / 25,535
  items / 654,867 interactions), full ranking, and HSTU/DiffuReason-H NDCG@10
  0.0945 / 0.1041. Source: https://arxiv.org/html/2602.09744v1
- Amazon Reviews 2023 remains the correct primary dataset source. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec metadata confirms existence and venue/DOI, but not protocol details
  in the accessible pages used here. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://www.researchgate.net/publication/398412502_SILLM4Rec_Self-Improving_with_Chain_of_Thought_Enhanced_Preference_Optimization_for_Multimodal_Recommendation

### Concrete Fixes To Make Next

1. Replace the SILLM4Rec sentence with neutral wording:
   "A further candidate, SILLM4Rec (MMAsia 2025), is excluded pending direct
   protocol inspection; accessible metadata did not establish an
   apples-to-apples AR2023 5-core full-catalog LLOO setting."
   Or simply delete the sentence until the paper is inspectable.
2. Decide whether `PAPER_SUBMISSION.pdf` should gain a short metadata front
   matter block or be explicitly described as non-venue reader output. Do not
   claim that both PDFs contain CCS/keywords unless extraction verifies it.
3. Keep the current AR2023-adjacent paragraph's non-comparability framing for
   `Augment or Not?` and `DiffuReason`; it is source-supported.
4. Leave Table 2 dense only if completeness is the intended reviewer-facing
   tradeoff; otherwise move most negative-result rows to appendix.
5. Re-run one final literature/protocol sweep at freeze.

### Open Questions

- Is `PAPER_SUBMISSION.pdf` still intended for public/reader consumption after
  TORS submission, and if so should it carry venue metadata for consistency?
- Can the authors obtain SILLM4Rec's full PDF through institutional access or an
  author copy before freeze?

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Read prior automation memory and prior cumulative audit.
- [x] Check files/commits after the automation last-run cutoff.
- [x] Verify strict rebuild and release manifest.
- [x] Verify TORS PDF hygiene scan.
- [x] Fact-check new Augment/DiffuReason coverage against external sources.
- [x] Check CCS/keyword presence in generated PDFs.
- [x] Identify reviewer-facing SILLM4Rec tooling-language defect.
- [ ] Rewrite or remove the SILLM4Rec sentence.
- [ ] Clarify metadata expectations for `PAPER_SUBMISSION.pdf`.
- [ ] Final freeze-time literature/protocol sweep.

## Audit Run - 2026-07-12 16:32 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `555f566` (`Respond to
  PAPER_REVIEW_AUDIT run 15:31: header collision fixed (visually verified);
  regenerates-wording aligned`)
- Working tree before writing this audit: clean.
- Commits since the supplied last-run cutoff (`2026-07-12T05:30:22Z`):
  `15b7dbaf` (short running title and regenerates wording), `d7846db4`
  (manifest regen), `555f5669` (response log).
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `CANONICAL_SUBMISSION.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/references.bib`,
  `paper_tex/sections/*`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, and `PAPER_REVIEW_AUDIT.md`.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 17, 18, 22,
  23, 24, 29, and 35 with `pypdfium2` through the project `uv` runtime into
  `tmp/pdfs/hourly_audit_20260712_1632_tors/`.

### Verdict

**No new hard rejection defect found in this run.** The prior two confirmed
defects are closed: the TORS running title no longer collides with page numbers,
and the unpinned comparator language is aligned to "regenerates" rather than
"reproduces." The scientific/provenance gate remains green. The highest current
risks are now submission-readiness and reviewer-perception risks: recent-work
coverage, Table 2 density, CCS/keyword metadata, and one minor first-page
layout-polish check.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T05:30:22Z" --oneline --name-status`
  - Confirms the expected three commits after the previous audit response.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 claim
    families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI dual gate.
  - PASS/VOID: Office remains descriptive and VOID under the preregistered floor
    check.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py
  paper_tex/PAPER_TORS.pdf`
  - PASS: 35 pages; 0 placeholder/forbidden-claim failures.
  - Informational SOTA list contains only explicit non-claim contexts.
- PDF text/object extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 35 pages, 426,626 bytes; contains WPGRec and
    "regenerates"; no `CCS Concepts`.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 36 pages, 433,961 bytes; contains
    WPGRec and "regenerates"; no `CCS Concepts`.
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,311,606 bytes; contains WPGRec and
    "regenerates"; no `CCS Concepts`.
- Wording sweep
  - `paper_tex/sections/05-results.tex` now has
    `The Musical_Instruments comparator regenerates locally` and
    `Caveats (why these are regenerations, not reproductions)`.
  - Remaining `reproduce*` hits are either negated pinned-reproduction caveats
    or internal "does not reproduce MI's tail win" thinning-language, not an
    official-comparator claim.
- Visual spot check
  - Page 23: short running title and page number are separated; Fig. 3 remains
    readable.
  - Page 24: Table 2 is legible but still dense.
  - Page 29: short running title and page number are separated; ethics/data
    governance section is readable.
  - Page 1: content is readable; note the duplicated-looking acmart
    "Manuscript submitted to ACM" topmatter/footer text as a freeze-time polish
    check.

### Confirmed Fixes Since Prior Audit

1. **Running-header collision fixed.** The optional short title in
   `paper_tex/paper-shared.tex` is present and the previously failing pages
   visually render cleanly.
2. **Comparator wording fixed.** The MI local reference-implementation run is
   now described as an environment-caveated local regeneration, not an official
   or pinned reproduction.
3. **Strict gate remains healthy after those fixes.** The rebuild, manifest
   verification, MI gate, Office VOID adjudication, and PDF hygiene scan all
   pass on the current HEAD.

### Confirmed Problems

- **No new confirmed numerical, provenance, or claim-boundary defect was found.**
- **Confirmed submission metadata still absent:** the active PDFs and TeX source
  do not include ACM CCS concepts or keywords. This is acceptable only if it is
  intentionally deferred until the actual TORS submission form/template pass.

### Plausible Risks Requiring Author Verification

- **Recent AR2023 literature coverage may still look selective.** The manuscript
  currently cites the main same-statistics and SID-family 2026 preprints, but a
  fresh search found additional AR2023-adjacent work not in the bibliography:
  `Augment or Not?` (2025) evaluates AR2023 Musical Instruments / Industrial
  and Scientific under 5-core leave-one-out; `DiffuReason` (2026) evaluates
  AR2023 Video & Games with an HSTU backbone but a different filtered universe;
  and SILLM4Rec has an ACM DOI page claiming three AR2023 5-core datasets. None
  of the inspected results overturn the paper's MI comparator choice or
  no-Video-Games-SOTA boundary, but a reviewer may expect an explicit
  non-comparability note.
- **DiffuReason deserves special handling if cited.** It reports Video & Games
  HSTU NDCG@10 0.0945 and DiffuReason-H 0.1041, far above this manuscript's
  Video_Games number, but its Video & Games universe is 67,658 users / 25,535
  items / 654,867 interactions and it filters positive ratings differently from
  the HSTU-BLaIR-family universe here (94,762 / 25,612 / about 814,586). This
  is not an apples-to-apples defeat, but it is a reason to keep avoiding broad
  Video_Games claims.
- **`Augment or Not?` is relevant but not threatening.** Its AR2023 Musical
  Instruments table reports best listed NDCG@10 0.0282 (LETTER-TIGER), well
  below HSTU-BLaIR's 0.0406 comparator, but it is a modern AR2023 5-core
  LOO LLM-recommender benchmark and should be considered for the final
  recent-work paragraph.
- **SILLM4Rec needs direct inspection before citation.** Search/ACM metadata
  indicate AR2023 5-core experiments, but this audit did not fully inspect the
  paper text because the ACM PDF page was not accessible through the tool.
- **First-page ACM footer/topmatter repetition may be harmless.** Verify against
  final TORS instructions rather than changing acmart blindly.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR still reports the paper's key comparator points: Video Games
  HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271, Musical Instruments
  0.0406, with AR2023 5-core framing. Sources:
  https://github.com/snapfinger/HSTU-BLaIR and
  https://arxiv.org/html/2504.10545v3
- SID-MLP remains a same-statistics AR2023 5-core LLOO concurrent-preprint
  comparator context for MI/VG dataset statistics. Source:
  https://arxiv.org/html/2605.12617v1
- WPGRec is real and supports the manuscript's statement that later
  time-frequency/wavelet-packet SR work exists; an ACM DOI search result now
  also appears, so bibliography metadata should be checked at freeze. Sources:
  https://arxiv.org/abs/2604.21305 and
  https://dl.acm.org/doi/10.1145/3805712.3809907
- `Augment or Not?` uses Amazon'23 Musical Instruments / Industrial and
  Scientific, 5-core leave-one-out, and reports MI NDCG@10 values up to 0.0282
  in its Table 2. Source: https://arxiv.org/html/2505.23053
- `DiffuReason` uses AR2023 Video & Games only among its Amazon review
  datasets, with 67,658 users / 25,535 items / 654,867 interactions and full
  ranking; its HSTU-backbone result is on a different universe and should not be
  mixed with HSTU-BLaIR-family numbers. Source:
  https://arxiv.org/html/2602.09744
- Amazon Reviews 2023 remains the correct primary dataset source for public
  review, metadata, and link facts. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Add a compact recent/concurrent-work note covering additional
   AR2023-adjacent but non-interchangeable protocols, or document why they are
   excluded from the main related-work paragraph. Include at least
   `Augment or Not?` and `DiffuReason`; inspect SILLM4Rec directly if adding it.
2. Decide whether to split Table 2 before submission or leave the dense
   complete negative-result map in the main text.
3. Add ACM CCS concepts and keywords before the actual TORS submission freeze.
4. Verify the first-page acmart "Manuscript submitted to ACM" repetition against
   final TORS formatting guidance.
5. Run one more targeted literature sweep at the freeze timestamp, especially
   for AR2023 5-core, HSTU, semantic-ID/generative, LLM/reasoning, and
   frequency/time-frequency sequential-recommendation work.

### Open Questions

- Should the paper cite `Augment or Not?` and `DiffuReason` in the main
  related-work paragraph, or in a short appendix/concurrent-work note?
- Is SILLM4Rec close enough to the paper's protocol to warrant inclusion after
  direct inspection?
- Is the dense Table 2 intended as a deliberate top-journal evidence table, or
  should it be condensed for first-pass review readability?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical source and compiled artifacts.
- [x] Check commits since the supplied last-run cutoff.
- [x] Verify strict numerical/provenance rebuild.
- [x] Run TORS PDF hygiene scan.
- [x] Render and visually inspect the prior failure pages.
- [x] Verify the prior header-collision fix.
- [x] Verify the prior "reproduces" wording fix.
- [x] Run a targeted external literature sweep.
- [x] Update the cumulative audit with current risk priorities.
- [ ] Add/freeze final recent-work coverage.
- [ ] Decide Table 2 split vs dense main-table presentation.
- [ ] Add ACM CCS concepts and keywords before submission.
- [ ] Verify final TORS first-page/footer formatting.

## Audit Run - 2026-07-12 15:31 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `c580f48` (`Respond to
  PAPER_REVIEW_AUDIT run 14:34: manifest boundary healed + dirty-file gate;
  WPGRec; BUILD_NOTES`)
- Working tree before writing this audit: clean.
- Manifest source boundary: `RELEASE_MANIFEST.json` records `git_commit =
  d76ef6436b60e6feab7b28d067172786ab8eaf0c`. `git diff --name-status
  5ce2d91..HEAD` shows only `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, so the
  manifest/source boundary is deliberate rather than new drift.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/main.tex`, `paper_tex/paper-shared.tex`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/references.bib`, `paper_tex/sections/*`, `paper_tex/tables/*`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `RELEASE_MANIFEST.json`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, and
  `CANONICAL_SUBMISSION.md`.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 17, 18, 22,
  23, 24, 29, and 35 with `pypdfium2` into
  `tmp/pdfs/hourly_audit_20260712_1531_tors/`.

### Verdict

**Numerical/provenance package: currently green. Submission formatting: not yet
green.** The prior manifest blocker, stale build-note class paragraph, and
uncited WPGRec/time-frequency related-work issue are closed. The strict rebuild
passes and the TORS PDF hygiene scanner passes. However, the rendered ACM
manuscript has a visible running-header/page-number collision on odd pages, and
the "reproduces" wording around the MI comparator still risks overstating an
unpinned local regeneration.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean at `c580f48`.
- `git log --oneline --decorate -5`
  - Shows `d76ef64` content commit, `5ce2d91` manifest child, then `c580f48`
    response-log commit.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    declared claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate.
  - PASS/VOID: Office arithmetic remains descriptive and VOID under the
    preregistered floor-check failure.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py
  --verify`
  - PASS: 113 files verified, 0 release-asset files not local.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py
  paper_tex/PAPER_TORS.pdf`
  - PASS: 35 pages; 0 placeholder/forbidden-claim failures.
  - Review list contains only explicit SOTA/non-claim contexts.
- PDF object/text inspection with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 35 pages, 427,696 bytes, US-letter media box,
    0 image XObjects, 3 vector Form XObjects; contains `ETHICS`, `GrIT`,
    `FEARec`, `WPGRec`, and the pinned-reproduction caveat; no `CCS Concepts`.
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,311,601 bytes, US-letter media box, 3
    image XObjects; contains `GrIT`, `FEARec`, and `WPGRec`.
- Visual spot check
  - Page 1: title/abstract readable in ACM manuscript review format.
  - Page 23: Fig. 3 page readable, but running title collides with page number.
  - Page 24: Table 2 is legible but crowded.
  - Page 29: ethics/data-governance text readable, but running title again
    collides with page number.

### Confirmed Fixes Since Prior Audit

1. **Manifest/source-boundary blocker fixed.** The previously dirty
   `emit_latex_tables.py` change is committed, the manifest was regenerated at
   a clean boundary, and the strict verify now includes the dirty-file gate.
2. **`BUILD_NOTES.md` class contradiction fixed.** The notes now state that
   `main.tex` is the gated `manuscript,review,anonymous` target and
   `main-acmsmall.tex` is an untracked production preview.
3. **Time-frequency related-work gap mostly fixed.** The novelty-boundary
   paragraph now cites WPGRec with a bibliography entry and no longer leaves the
   broader "subsequent time-frequency" phrase unsupported.
4. **Prior core scientific boundaries still hold.** Figures, ethics/data
   governance, GrIT, FEARec, WPGRec, Office VOID language, and no-Video-Games
   SOTA language remain present in the active artifacts.

### Confirmed Problems

1. **Running header overlaps page number in the TORS review PDF.** This is
   visible in the rendered review artifact, not just an extraction artifact.
   `paper_tex/paper-shared.tex` sets a long `\title{...}` and
   `\renewcommand{\shortauthors}{Anonymized}` but does not provide an optional
   short running title, so acmart uses the full title in the running head.
2. **Comparator wording remains stronger than the paper's own caveat boundary.**
   The section heading "The Musical_Instruments comparator reproduces" and the
   sentence "a local regeneration by the generating code reproduces it" should
   be softened. The evidence supports a local, environment-caveated regeneration
   of the published point estimate, not a faithful pinned reproduction.

### Plausible Risks Requiring Author Verification

- Whether to split Table 2 before initial TORS submission or wait for reviewer
  pressure. It is now technically readable but dense enough to slow review.
- Whether to add ACM CCS concepts and keywords now or only at submission-freeze.
- Whether to cite one more representative 2025 time-frequency SR paper such as
  HyTiFRec/CTF4Rec, or keep WPGRec as the representative recent example. WPGRec
  is enough to support the current sentence, but the literature is moving fast.
- Whether `PAPER_SUBMISSION.pdf` remains a live deliverable or only a markdown
  render. The TORS artifact is cleaner on ethics/formatting and appears to be
  the real submission target.

### External Fact-Check / Novelty Notes

- ACM author guidance and venue examples support the `manuscript,review` /
  `manuscript,review,anonymous` review build direction. Sources:
  https://www.acm.org/publications/authors/submissions and
  https://chi2026.acm.org/chi-publication-formats/
- ACM TORS author guidelines require originality / not-under-review
  declaration in the cover letter; this supports keeping the TORS-specific venue
  plan explicit. Source: https://dl.acm.org/journal/tors/author-guidelines
- WPGRec is a real 2026 arXiv preprint in the time-frequency sequential
  recommendation line and is now a reasonable representative citation for the
  novelty-boundary paragraph. Source: https://arxiv.org/abs/2604.21305
- HyTiFRec is a 2025 hybrid time-frequency sequential-recommendation paper,
  relevant as an optional additional recent citation but not strictly required
  after WPGRec was added. Source:
  https://www.techscience.com/cmc/v83n2/60583
- HSTU-BLaIR remains the stronger external AR2023 5-core comparator family for
  the manuscript's Video_Games / Musical_Instruments / Office framing. Sources:
  https://github.com/snapfinger/HSTU-BLaIR and
  https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023 is a large public dataset with user reviews, item
  metadata, and links; the paper's ethics section correctly scopes the risk to
  public/pseudonymized review and metadata use rather than human-subject
  intervention. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Add an optional short title in `paper_tex/paper-shared.tex`, rebuild both
   TeX targets, rerun `paper_tex/scan_pdf.py`, and visually inspect pages with
   running heads.
2. Replace the `paper_tex/sections/05-results.tex` and `PAPER_SUBMISSION.md`
   "comparator reproduces" wording with "regenerates locally under the unpinned
   shimmed research path" language.
3. Decide Table 2 presentation: leave as dense complete main-table evidence, or
   move long rows to appendix and keep a compact main summary.
4. Add ACM CCS concepts and keywords at submission freeze.
5. Run one final literature sweep immediately before TORS submission.

### Open Questions

- Is `PAPER_SUBMISSION.pdf` still intended to be submitted anywhere, or is
  `paper_tex/PAPER_TORS.pdf` now the only review artifact?
- Should the response log remain outside the manifest boundary by policy, or
  should deposits include response/audit correspondence as ancillary files?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical source and compiled artifacts.
- [x] Verify clean git state and manifest boundary.
- [x] Run strict numerical/provenance rebuild.
- [x] Run release-manifest verification.
- [x] Run TORS PDF hygiene scan.
- [x] Render and visually inspect representative PDF pages.
- [x] Fact-check current venue/literature/comparator claims against external
      sources.
- [x] Confirm prior 14:34 blockers are mostly fixed.
- [ ] Fix TORS running-header/page-number collision.
- [ ] Soften "reproduces" wording for unpinned local comparator runs.
- [ ] Decide Table 2 split vs dense main-table presentation.
- [ ] Add ACM CCS concepts and keywords before submission.
- [ ] Final targeted literature sweep at freeze.

## Audit Run - 2026-07-12 14:34 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `6719bb3` (`Close round-8 row 1
  with phase-B landing details`)
- Working tree before writing this audit: dirty only in
  `_bestrec_run/emit_latex_tables.py`.
- Dirty change inspected: one added typography rule,
  `Beauty\_and\_PC -> Beauty\_and\_\allowbreak PC`, at
  `_bestrec_run/emit_latex_tables.py:109`.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `CANONICAL_SUBMISSION.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `VENUE_PLAN.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/emit_latex_tables.py`,
  `paper_tex/main.tex`, `paper_tex/main-acmsmall.tex`,
  `paper_tex/build.ps1`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/references.bib`, `paper_tex/sections/*`,
  `paper_tex/tables/*`, `paper_tex/PAPER_TORS.pdf`, and
  `paper_tex/PAPER_TORS_acmsmall.pdf`.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 17, 18, 22,
  23, 24, 29, and 35 with `pypdfium2` into
  `tmp/pdfs/hourly_audit_20260712_1430_tors/`.

### Verdict

**The TORS review-format issue is substantially fixed, but the release boundary
is not yet clean enough for a top-journal artifact package.** The current
review PDF is now a 35-page ACM `manuscript,review,anonymous` build; the hygiene
scanner passes; figures, ethics, GrIT, FEARec, and the no-SOTA wording all remain
present; and the strict numerical gate passes. The serious new blocker is
provenance: the manifest hash for `_bestrec_run/emit_latex_tables.py` matches an
uncommitted working-tree edit, not the committed file at either `HEAD` or the
manifest's recorded source boundary.

### Commands And Evidence Checked

- `git status --short --branch`; `git log --oneline -5`
  - HEAD is `6719bb3`.
  - Only tracked dirty file before this audit was
    `_bestrec_run/emit_latex_tables.py`.
- `git diff -- _bestrec_run/emit_latex_tables.py`
  - One-line typography-only `Beauty_and_PC` allowbreak addition.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and
    VOID under the preregistered floor-check failure.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 35 pages; 0 placeholder/forbidden-claim failures.
  - Review list contains only explicit SOTA/non-claim contexts.
- `update_release_manifest.py --verify`
  - PASS in the dirty working tree because the manifest hash matches the dirty
    generator file.
- Manifest/hash cross-check:
  - Working-tree `_bestrec_run/emit_latex_tables.py` SHA256 =
    `1ac6b422b12416a893c8eb9f79e21729801435d9af4202a84b43f8ecd2e60f86`.
  - `RELEASE_MANIFEST.json` entry for that file =
    `1ac6b422b12416a893c8eb9f79e21729801435d9af4202a84b43f8ecd2e60f86`.
  - `HEAD:_bestrec_run/emit_latex_tables.py` SHA256 =
    `2d631b7a785f734704cbc90756a5a2a5c879ff3d5f9cb2d6bdbbbc36196a08d6`.
  - `7a627ef:_bestrec_run/emit_latex_tables.py` SHA256 =
    `2d631b7a785f734704cbc90756a5a2a5c879ff3d5f9cb2d6bdbbbc36196a08d6`.
  - Therefore the manifest does not describe the committed source state it says
    it describes.
- PDF object/text inspection:
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,310,455 bytes, letter mediabox, 3 image
    XObjects.
  - `paper_tex/PAPER_TORS.pdf`: 35 pages, 427,335 bytes, letter mediabox
    `(612, 792)`, 3 vector Form XObjects.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 36 pages, 433,983 bytes,
    `(486, 720)` mediabox, 3 vector Form XObjects.
  - TORS PDF contains `10 ETHICS`, `GrIT`, and `FEARec`.
- Visual spot check:
  - Figures 1-3 render and remain readable.
  - Table 2 is no longer broken across a bad page transition; page 24 is
    readable, though dense.
  - Ethics/data-governance text is readable on page 29.

### Confirmed Fixes Since Prior Audit

1. **ACM review format was changed to the safer default.** `paper_tex/main.tex`
   now uses `\documentclass[manuscript,review,anonymous]{acmart}` and produces
   the manifest-gated `PAPER_TORS.pdf`. `main-acmsmall.tex` is now a separate
   production-preview target.
2. **Response staleness is reduced.** `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` now
   begins with a historical-log banner and closes the prior "in flight" wording
   with landing commits.
3. **Deposit/source-boundary prose exists.** `RELEASE_MANIFEST.json` now states
   that `paper_tex` source is governed by Git at the recorded `git_commit`, while
   the manifest hashes the rendered TORS PDF.
4. **Bibliography metadata was improved.** `paper_tex/BUILD_NOTES.md` documents
   registry-verified metadata fills and explicitly lists entries left untouched
   because no authoritative record was found.
5. **Prior scientific blockers remain closed.** Figures, ethics/data governance,
   Table 0 parity wording, GrIT, and FEARec remain present in the inspected
   artifacts.

### Confirmed Problems

1. **Manifest/source-boundary inconsistency is now the top blocker.** The working
   tree passes `update_release_manifest.py --verify`, but only because a
   manifest-hashed file is dirty. A clean clone at `HEAD` would have the
   committed generator content, whose hash does not match the committed manifest
   entry. This contradicts the manifest's "hashes describe repository files as
   of git_commit" rule.
2. **`paper_tex/BUILD_NOTES.md` contradicts itself about the document class.**
   Lines 11-29 and the actual `main.tex` say the review build is `manuscript`;
   lines 84-91 still say the document class is
   `acmsmall,screen,review,anonymous`. Fix the stale paragraph to name both
   targets correctly.
3. **Related-work prose has an uncited "subsequent time-frequency architectures"
   phrase.** The paper cites FEARec, but not the later wavelet/time-frequency
   works that make the phrase true. This is a reviewer-polish issue, not a
   result invalidation.

### Plausible Risks Requiring Author Verification

- Whether the dirty `Beauty_and_PC` line is intended. It appears consistent with
  `BUILD_NOTES.md`'s overfull-box claim, but it must be committed or removed.
- Whether the manifest `git_commit` should advance beyond `7a627ef` after the
  response-only commits. If response files remain outside the deposit boundary,
  this can be acceptable, but the boundary should be explicit.
- Whether TORS requires CCS concepts and keywords at initial submission. The
  current build notes defer them as new content.
- Whether to split Table 2 before submission freeze despite the manuscript build
  being visually acceptable.
- Which representative 2025-2026 time-frequency SR works to cite in the
  novelty-boundary paragraph.

### External Fact-Check / Novelty Notes

- ACM's current author workflow says review submissions should be single-column
  and says LaTeX authors should use the `manuscript` option with
  `\documentclass[manuscript]{acmart}`. This supports the new `main.tex`
  review target. Source: https://www.acm.org/publications/authors/submissions
- The current `acmart` documentation says the `review` option is useful when
  combined with `manuscript`, and that `anonymous` obscures author information.
  It also notes ACM submission samples for both manuscript and acmsmall. Source:
  https://mirrors.ctan.org/macros/latex/contrib/acmart/acmart.pdf
- SID-MLP remains a relevant 2026 AR2023 5-core comparator-context paper: it
  reports AR2023 5-core leave-last-out statistics matching the MI/VG universes
  and NDCG@10 values below the manuscript's MI/VG values. Source:
  https://arxiv.org/html/2605.12617v1
- GrIT remains a relevant same-statistics AR2023 Video_Games 5-core related-work
  item: its table reports Video Games NDCG@10 0.0588. Source:
  https://arxiv.org/html/2602.19728v1
- The time-frequency SR line is broader than FEARec. WPGRec (2026) explicitly
  frames frequency/time-frequency modeling as active, cites FEARec and WaveRec,
  and proposes wavelet-packet subband modeling with graph propagation. Source:
  https://arxiv.org/html/2604.21305v1
- HyTiFRec (2025) is another time-frequency sequential-recommendation example,
  proposing a hybrid time-frequency dual-branch transformer and reporting
  experiments on five datasets. Source:
  https://www.sciencedirect.com/org/science/article/pii/S1546221825003388

### Concrete Fixes To Make Next

1. Commit `_bestrec_run/emit_latex_tables.py` if the `Beauty_and_PC` line is
   intended, then regenerate/commit `RELEASE_MANIFEST.json` at the intended
   boundary and verify from a clean working tree. If the line is not intended,
   remove it and regenerate the manifest instead.
2. Fix `paper_tex/BUILD_NOTES.md` lines 84-91 so the document-class section
   describes the default `manuscript` review target and the separate `acmsmall`
   preview target.
3. Add one sentence and 1-3 representative citations for later
   frequency/time-frequency SR work (for example WaveRec/WPGRec and HyTiFRec),
   or remove the phrase "subsequent time-frequency architectures."
4. Decide whether Table 2 should be split for readability before submission
   freeze.
5. Add ACM CCS concepts / keywords if TORS requires them at initial submission.

### Open Questions

- Was the manifest regenerated while `_bestrec_run/emit_latex_tables.py` was
  dirty and then committed without the generator edit?
- Should `RELEASE_MANIFEST.json` describe the latest source commit, or only the
  committed artifact boundary for the TORS PDF?
- Is the current Table 2 density an acceptable TORS tradeoff, or should the
  main paper carry only a summarized negative-result map?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript source and TORS artifacts.
- [x] Check files modified since the previous automation cutoff.
- [x] Inspect current git status and recent commits.
- [x] Verify strict numerical/provenance gate.
- [x] Verify TORS hygiene scan.
- [x] Inspect PDF page count, media box, figures, and ethics section.
- [x] Render visual spot-check pages.
- [x] Fact-check ACM review-format guidance against external sources.
- [x] Run targeted AR2023/generative and time-frequency related-work searches.
- [x] Identify manifest/dirty-source contradiction.
- [ ] Commit or remove dirty generator change and align the manifest boundary.
- [ ] Fix stale `BUILD_NOTES.md` document-class paragraph.
- [ ] Cite or remove uncited later time-frequency architecture wording.
- [ ] Decide whether to split Table 2.

## Audit Run - 2026-07-12 12:34 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `9cb7fcb` (`Regenerate
  RELEASE_MANIFEST: TORS artifacts enter the drift gate`)
- Working tree before writing this audit: clean.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `CANONICAL_SUBMISSION.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `VENUE_PLAN.md`,
  `RELEASE_MANIFEST.json`, `paper_tex/main.tex`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/sections/*`, `paper_tex/tables/*`, `paper_tex/references.bib`,
  and the strict rebuild wrapper.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 18, 22, 24,
  25, 26, 30, 31, and 36 with `pypdfium2` into
  `tmp/pdfs/hourly_audit_20260712_1140_tors/`.

### Verdict

**Material progress since 10:31: the prior top blockers are closed in the
current artifacts, and the numerical/provenance gate still passes.** The paper
is now much closer to a real TORS submission package: figures are embedded,
ethics/data governance exists, the Table 0 HSTU-parity contradiction is fixed,
GrIT/FEARec are cited/scoped, the TORS PDF is built and scanned, and the release
manifest includes the TORS PDF. The main remaining top-journal risks are
format-policy ambiguity, source/deposit boundary clarity, table readability, and
final literature/bibliography polish.

### Commands And Evidence Checked

- `git status --porcelain=v1 -uall`
  - Clean before writing this audit.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate. K=16 CI-LB 0.04096 and K=8 CI-LB 0.04083 both exceed
    the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and
    VOID under the preregistered floor-check failure.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures. SOTA/paired/pinned
    mentions are listed as review items and appear in explicit non-claim
    contexts.
- `pypdf` object/text inspection:
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,310,455 bytes, 3 image XObjects.
  - `paper_tex/PAPER_TORS.pdf`: 36 pages, 430,794 bytes, 3 vector Form XObjects.
  - Both PDFs contain Fig. 1, Fig. 2, Fig. 3, GrIT, and FEARec; neither contains
    the stale phrase `no numerical-parity claim`.
  - The TORS PDF text extraction finds the ethics section as uppercase
    `10 ETHICS AND DATA GOVERNANCE`; its body includes public/pseudonymized
    AR2023 use, no review bodies/images, no raw-data redistribution, no
    re-identification, and IRB/human-subjects non-applicability.
- Visual spot check:
  - Fig. 1, Fig. 2, and Fig. 3 render and are readable.
  - Ethics/data-governance text is visible and readable on page 30.
  - The old Table 2 dangling continuation-cell defect is gone in the TORS PDF;
    the table remains very dense on page 25.
- Manifest/release check:
  - `RELEASE_MANIFEST.json` now records `git_commit =
    7a8607b280173d0ac15de242044f56bac6c5ccbd`, the immediate parent of current
    HEAD `9cb7fcb...`, which matches the manifest's "cannot hash itself"
    boundary rule.
  - `submission_docs` now includes `paper_tex/PAPER_TORS.pdf`; the manifest diff
    also adds `_bestrec_run/emit_latex_tables.py`.

### Confirmed Fixes Since Prior Audit

1. **Figures are embedded.** The Markdown PDF has 3 image XObjects and the TORS
   PDF has 3 vector Form XObjects. The old "filename reference only" blocker is
   closed.
2. **Ethics/data governance exists.** `PAPER_SUBMISSION.md` and the TORS PDF now
   include an ethics/data-governance statement with AR2023 provenance, data-use
   scope, no raw redistribution, no review-body/image processing, no
   re-identification, and IRB/human-subjects non-applicability.
3. **Table 0 HSTU parity contradiction is fixed.** The row now says
   equation-level verification plus bitwise core-block parity, while still
   refusing a pinned end-to-end reproduction claim.
4. **GrIT is cited and scoped.** The paper records GrIT's Video_Games NDCG@10
   0.0588 as a same-statistics AR2023 5-core point estimate and explicitly does
   not make a comparative claim against unreviewed concurrent work.
5. **Frequency/time-frequency related work is broader.** FEARec is cited as a
   representative wider line, and the paper narrows its causal-FIR contribution.
6. **RecSys 2027 timing is no longer overstated.** `VENUE_PLAN.md` now says
   dates are not announced and treats RecSys 2026 only as precedent.
7. **TORS smoke artifacts are triaged.** `paper_tex/` is now tracked as a
   derived ACM/TORS build; `_smoke.*` is gone and `PAPER_TORS.pdf` is manifest
   covered.

### Confirmed Problems

1. **The TORS build may not match ACM's review-submission option.** ACM's
   current general author workflow says LaTeX review submissions should use
   `\documentclass[manuscript]{acmart}` for single-column review, but
   `paper_tex/main.tex` uses `acmsmall,screen,review,anonymous`. This may still
   be acceptable if TORS explicitly wants the journal template at initial
   submission; otherwise switch the review build to `manuscript,review,anonymous`
   and keep `acmsmall` for accepted-production formatting.
2. **Response prose is stale.** `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` still has
   historical rows saying the TORS round-7 deltas are being applied / will be
   committed and older 37/38-page statements. Do not include that file in a
   submission bundle without either updating or clearly labeling it historical.

### Plausible Risks Requiring Author Verification

- Whether TORS initial submission should use ACM `manuscript` review format or
  the current `acmsmall,screen,review,anonymous` build.
- Whether the DOI/deposit archive should hash/package the full `paper_tex`
  source tree, not only the rendered `paper_tex/PAPER_TORS.pdf`.
- Whether Table 2 should be split into a compact main-paper table plus appendix
  detail before TORS submission.
- Whether BibTeX metadata warnings accepted by `BUILD_NOTES.md` should be fixed
  now for production-quality references.
- Whether to do one final targeted literature sweep for 2026 AR2023 5-core and
  frequency/time-frequency SR papers before freezing the TORS reference list.

### External Fact-Check / Novelty Notes

- ACM's current author workflow says review submissions should be single-column
  and, for LaTeX, use the `manuscript` option; the same page says ACM journals
  use `acmsmall` except listed exceptions. This creates the current TORS-format
  ambiguity. Source: https://www.acm.org/publications/authors/submissions
- ACM's simultaneous-submission policy says ACM normally does not permit a
  manuscript under review in an ACM journal/proceeding to be simultaneously
  under review elsewhere, and violation can cause rejection. This supports the
  sequenced TORS -> RecSys plan. Source:
  https://www.acm.org/publications/policies/simultaneous-submissions
- The TORS author-guidelines page indicates authors must submit a cover letter
  declaring originality, unpublished status, and not-currently-under-review
  status. Source: https://dl.acm.org/journal/tors/author-guidelines
- AR2023's official documentation confirms the dataset includes user reviews,
  item metadata including raw image fields, links, newer interactions through
  Sep. 2023, fine-grained timestamps, and standard splits. This supports keeping
  the ethics/data-governance statement. Source:
  https://amazon-reviews-2023.github.io/
- GrIT (arXiv:2602.19728) reports Video Games NDCG@10 0.0588 in its overall
  table; citing/scoping it remains necessary. Source:
  https://arxiv.org/html/2602.19728v1
- FEARec (arXiv:2304.09184 / SIGIR 2023) frames self-attention SR as low-pass
  and proposes a frequency-enhanced hybrid-attention model, so it is an
  appropriate representative of the broader frequency/time-frequency SR line.
  Source: https://arxiv.org/abs/2304.09184

### Concrete Fixes To Make Next

1. Decide and document the TORS initial-submission class option; preferably add a
   `manuscript,review,anonymous` build target if TORS does not override ACM's
   general review guidance.
2. Clarify the deposit boundary: hash/package `paper_tex` sources or explicitly
   state that Git commit `7a8607b...` is the source boundary and the manifest
   hashes only the rendered TORS artifact.
3. Update or quarantine stale `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` prose before
   any public release bundle.
4. Consider splitting Table 2 for readability.
5. Fill missing BibTeX production metadata where available.
6. Run a final targeted literature sweep immediately before TORS submission.

### Running Checklist

- [x] Read automation memory.
- [x] Inspect current HEAD, git status, canonical Markdown, TORS LaTeX, manifest,
      and response files.
- [x] Re-run the strict submission gate.
- [x] Run the TORS PDF hygiene scanner.
- [x] Inspect PDF object counts and key extracted text.
- [x] Render representative TORS pages and visually inspect figures, ethics, and
      Table 2 continuation.
- [x] Fact-check ACM submission format, ACM simultaneous-submission policy,
      TORS cover-letter requirement, AR2023 data fields, GrIT, and FEARec.
- [ ] Resolve ACM/TORS `manuscript` vs `acmsmall` review-format ambiguity.
- [ ] Clarify or expand manifest coverage for the `paper_tex` source package.
- [ ] Update stale response prose or keep it out of public bundles.
- [ ] Improve Table 2 readability.
- [ ] Complete final literature and bibliography metadata sweep.

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
