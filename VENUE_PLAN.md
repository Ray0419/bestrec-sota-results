# Venue plan (maintainer decision, 2026-07-12)

**Decision: aim for both ACM TORS and the RecSys 2027 Reproducibility track — sequenced, never
simultaneous.** Concurrent submission of the same manuscript to two venues violates both venues'
dual-submission policies, so the plan is:

1. **Primary: ACM TORS** (Transactions on Recommender Systems). Rolling submissions — typeset
   and submit first. Journal length accommodates the full apparatus (pre-declarations,
   artifact gate, negative-result map, appendices).
2. **Secondary: RecSys 2027, Reproducibility track** (dates not yet announced; the RecSys 2026 cycle — artifacts required, dual submission prohibited — is precedent only). If TORS has
   rejected (or the maintainer withdraws) before that deadline, submit the
   reproducibility-focused variant there. If TORS review is still pending at the deadline, the
   maintainer decides then; no double submission.

## Typesetting rules (both venues)

- The **markdown files remain canonical** (`CANONICAL_SUBMISSION.md` governs); LaTeX is a
  *generated/derived* submission format under `paper_tex/`.
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
  paper content; the LaTeX is regenerated *from* the gated markdown, never edited divergently.

## DOI (related decision, same date)

Minting is **deferred** until a venue actually requires it ("skip for now"). The
hash-manifested GitHub releases (`v0.9-audit-evidence` + **the current deposit tag**,
recorded in `DOI_DEPOSIT_INSTRUCTIONS.md`; each deposit release supersedes the previous)
remain the citable
artifact reference; everything needed to mint in ~3 clicks stays prepared
(`DOI_DEPOSIT_INSTRUCTIONS.md`).

## Pre-submission freeze checklist (maintainer go-signal required; none started unprompted)

Status legend: **PENDING** = not yet done, blocks the freeze when reached.

1. **SILLM4Rec full-paper inspection — PENDING.** The current exclusion rationale rests on the
   public repository's own workflow (image-to-text descriptions, user preference summaries,
   candidate-product ranking, SFT/DPO data — not established full-catalog LLOO). ACM metadata
   (AR2023 5-core, NDCG@K) means a reviewer may ask for direct protocol inspection: before
   freeze, inspect the ACM full text (`10.1145/3743093.3771011`) if accessible and record the
   verdict here; if inaccessible, the exclusion stands on repo evidence and this item is
   disclosed as inspection-pending. (Access attempts on record: the external auditor's
   direct ACM full/PDF fetch returned 403 on 2026-07-19; responder-side non-interactive
   access is likewise unavailable — an institutional route at freeze is the remaining path.)
2. Final literature sweep (new AR2023 sequential-rec results since the last audit round).
3. Cover letter: tracked draft exists (`COVER_LETTER_TORS.md`) with originality +
   not-under-review declarations and the claim boundary restated; at freeze the maintainer
   fills the bracketed fields (COI, reviewers, author identity, preprint status)
   (two counted per-category point-estimate comparisons; FIR internal contrast on four
   categories; no SOTA of any kind; Office V1 VOID permanent).
4. Table-2 split preference (single wide table vs split) — venue-template decision.
5. First-page acmart format verification against current TORS author guidelines, **including
   refreshing the vendored `acmart.cls` (currently v2.03, 2024) against ACM's current Primary
   Article Template — deciding explicitly between the ACM submission portal's LaTeX package
   (v2.16, 2025-08-28) and CTAN production acmart (v2.19, 2026-06-27; per the 2026-07-18
   13:16 audit)** and re-running the full build + hygiene scan; decide then whether the
   Tectonic-based build compiles the latest class or whether final packaging moves to
   TeX Live/Overleaf (audit 2026-07-18 06:13, deliberate deferred decision — class upgrades
   are freeze-scope, not loop-scope).
6. DOI minting (currently deferred by maintainer decision — see above).
