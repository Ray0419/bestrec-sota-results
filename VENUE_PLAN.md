# Venue plan (maintainer decision, updated 2026-07-31)

## Tier-A constraint added 2026-07-31

The maintainer now requires a journal recognized as Tier A or higher. "Tier A"
is list-dependent, so no agent may claim that a venue satisfies this requirement
until the maintainer names the controlling ranking authority and edition and the
exact journal/ISSN is verified against it. ACM TORS remains the leading
scientific-fit candidate, but its relatively recent launch means its formal
presence/rating cannot be assumed across ABDC, national, or institutional lists.
`TIER_A_PUBLICATION_ROADMAP.md` governs the verification and evidence-upgrade
work; `CODEX_CLAUDE_COLLABORATION_GUIDE.md` governs agent coordination.

**Provisional decision: aim for ACM TORS and the RecSys 2027 Reproducibility track — sequenced, never
simultaneous.** Concurrent submission of the same manuscript to two venues violates both venues'
dual-submission policies, so the plan is:

1. **Scientific-fit primary, pending Tier-A verification: ACM TORS** (Transactions on Recommender Systems). Rolling submissions — typeset
   and submit first. The official author guidelines checked on 2026-07-31 state that original
   research papers are usually **20–35 pages in ACM `acmsmall` style**. Unusual lengths can be
   considered, but length must be commensurate with contribution and readability is explicitly
   part of the initial desk-review decision. The pre-split 52-page `acmsmall` preview exceeded
   that usual range by 17 pages. The focused main article now compiles to 33 `acmsmall` pages,
   while audit chronology, superseded studies, extended tables, and implementation ledgers are
   retained in an 18-page reviewer supplement. Source:
   <https://dl.acm.org/journal/tors/author-guidelines>.
2. **Secondary: RecSys 2027, Reproducibility track** (dates not yet announced; the RecSys 2026 cycle — artifacts required, dual submission prohibited — is precedent only). If TORS has
   rejected (or the maintainer withdraws) before that deadline, submit the
   reproducibility-focused variant there. If TORS review is still pending at the deadline, the
   maintainer decides then; no double submission.

## Typesetting rules (both venues)

- `PAPER_SUBMISSION.md` remains the sole canonical authored source
  (`CANONICAL_SUBMISSION.md` governs). Generated tables are emitted from the canonical
  Markdown/artifact graph, but TeX prose is a separately maintained mirror under semantic,
  numeral, and rendered-PDF parity gates; it is not described as whole-prose generation.
- ACM `acmart` class (TORS: `manuscript`/`acmsmall` journal format, single-blind review per the current TORS author guidelines (corrected 2026-07-21; the earlier double-anonymous assumption was wrong);
  RecSys: `sigconf`).
- **Artifact-gated numbers are never retyped by hand** (standing audit requirement): result
  tables are generated from `_bestrec_run/hstu_tables.json` /
  `_bestrec_run/hstu_results_manifest.json` into `.tex` includes by script; prose numerals are
  conversion-checked against the markdown source.
- Every LaTeX build ends with the same placeholder/claim-hygiene scan as the markdown PDF, plus
  the forbidden-wordings sweep (no broad SOTA, no paired superiority, no
  official/pinned-reproduction language; Office **V1** never presented as passed — its VOID
  is permanent — and Office **V3** only within its frozen wording: per-category
  point-estimate comparison, no paired/distributional superiority, not SOTA).
- The strict gate (`rebuild_hstu_submission.py --strict`) must pass at any commit that changes
  paper content. Generated TeX tables are regenerated from the gated Markdown/graph; separately
  maintained TeX prose must be changed in the same commit and pass the parity gates.

## TORS submission-format decision (official guidance checked 2026-07-31)

- **Paper type:** original research paper, with a modular algorithmic contribution plus an
  unusually strong falsification/reproducibility record. Do not relabel it a reproducibility
  paper merely to justify length: the primary scientific question is the FIR intervention.
- **Main-file target:** 30–35 `acmsmall` pages, including the evidence needed to understand the
  method, matched controls, Amazon boundary, negative MovieLens result, comparator matrix, and
  limitations without opening the supplement.
- **Supplement target:** protocol chronology, VOID/deviated histories, full probe and titration
  ladders, extended diagnostics, detailed custody/hash ledgers, and additional tables. TORS
  permits supplementary material to be shared with reviewers; the main paper must remain
  scientifically self-contained.
- **Review mode:** single-blind. Real authors, affiliations, corresponding-author identity, and
  contact metadata belong in the submission; placeholders remain a literal blocker.
- **LaTeX mode:** TORS instructs authors not to include their own review line numbers. The local
  submission class/options must match the official `acmart` manuscript guidance and leave portal
  line numbering to the submission system.
- **Cover letter:** required. It must declare originality, unpublished status, and no concurrent
  review; extensions of earlier own work must be disclosed. The existing draft remains
  human-incomplete until identity, conflicts, preprint/overlap, and corresponding-author fields
  are supplied.
- **Open access:** ACM states that it became fully open access on 2026-01-01. APC eligibility,
  institutional coverage, waiver/discount status, and corresponding-author affiliation require
  a human check before submission; do not infer them from the repository.

## DOI (related decision, same date)

Minting is **deferred** until a venue actually requires it ("skip for now"). The
hash-manifested GitHub releases (`v0.9-audit-evidence` + **the current deposit tag**,
recorded in `DOI_DEPOSIT_INSTRUCTIONS.md`; each deposit release supersedes the previous)
remain the citable
artifact reference; everything needed to mint in ~3 clicks stays prepared
(`DOI_DEPOSIT_INSTRUCTIONS.md`).

## Pre-submission freeze checklist

Status legend: **DONE** = locally verified; **HUMAN** = requires maintainer information or
authenticated publication access.

1. **SILLM4Rec full-paper inspection — CLOSED WITH ACCESS LIMITATION (2026-07-28).** The current exclusion rationale rests on the
   public repository's own workflow (image-to-text descriptions, user preference summaries,
   candidate-product ranking, SFT/DPO data — not established full-catalog LLOO). ACM metadata
   confirms the title, venue, DOI (`10.1145/3743093.3771011`), and eight-page extent, but
   repeated unauthenticated ACM full-text/PDF retrieval returned 403 and no author preprint
   or public source was located. The paper therefore does **not** claim full-text protocol
   inspection; its non-comparability statement remains limited to public metadata/repository
   evidence. An institutional copy may be checked by the maintainer, but lack of one does not
   silently become a positive protocol claim.
2. **Final literature sweep — DONE (2026-07-28).** Official AAAI records for FreqRec and
   WEARec remain the current frequency-system anchors. The sweep also found SISA-Rec
   (arXiv:2607.11168) and ASER (arXiv:2603.02709), now cited in §2.3 as concurrent modular
   content-integration work. Their experiments use Amazon Reviews 2014 rather than this
   paper's AR2023 item universes, so no numerical comparison is imported. No new exact
   AR2023 5-core/full-catalog comparator that changes the existing claim boundary was found.
3. **Cover letter — DRAFT DONE; HUMAN FIELDS REMAIN.** `COVER_LETTER_TORS.md` contains originality +
   not-under-review declarations and the claim boundary restated; at freeze the maintainer
   fills the bracketed fields (COI, reviewers, author identity, preprint status)
   (two counted per-category point-estimate comparisons; outcome-visible FIR internal
   evidence; no SOTA of any kind; Office V1 VOID permanent).
4. **Table layout — DONE.** The current split/generated table layout is the chosen TORS
   manuscript realization; it passes the render inspection without unreadable scaling.
5. **acmart/template verification — DONE (2026-07-28).** The vendored class is acmart
   v2.19 (2026-06-27), the current CTAN production class identified in the audit. Tectonic
   compiles the journal manuscript and the first page, tables, references, and appendix have
   been rendered and inspected. The final portal upload may still be recompiled by ACM's
   service, but there is no known local template blocker.
6. **DOI/release publication — HUMAN.** A deterministic current candidate is prepared and
   explicitly marked unpublished. Do not tag, upload, or mint until real creator metadata,
   license/redistribution decisions, and archive authentication are supplied.
