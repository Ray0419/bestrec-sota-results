# Venue plan (maintainer decision, 2026-07-12)

**Decision: aim for both ACM TORS and the RecSys 2027 Reproducibility track — sequenced, never
simultaneous.** Concurrent submission of the same manuscript to two venues violates both venues'
dual-submission policies, so the plan is:

1. **Primary: ACM TORS** (Transactions on Recommender Systems). Rolling submissions — typeset
   and submit first. Journal length accommodates the full apparatus (pre-registrations,
   artifact gate, negative-result map, appendices).
2. **Secondary: RecSys 2027, Reproducibility track** (dates not yet announced; the RecSys 2026 cycle — artifacts required, dual submission prohibited — is precedent only). If TORS has
   rejected (or the maintainer withdraws) before that deadline, submit the
   reproducibility-focused variant there. If TORS review is still pending at the deadline, the
   maintainer decides then; no double submission.

## Typesetting rules (both venues)

- The **markdown files remain canonical** (`CANONICAL_SUBMISSION.md` governs); LaTeX is a
  *generated/derived* submission format under `paper_tex/`.
- ACM `acmart` class (TORS: `manuscript`/`acmsmall` journal format, double-anonymous review;
  RecSys: `sigconf`).
- **Artifact-gated numbers are never retyped by hand** (standing audit requirement): result
  tables are generated from `_bestrec_run/hstu_tables.json` /
  `_bestrec_run/hstu_results_manifest.json` into `.tex` includes by script; prose numerals are
  conversion-checked against the markdown source.
- Every LaTeX build ends with the same placeholder/claim-hygiene scan as the markdown PDF, plus
  the forbidden-wordings sweep (no broad SOTA, no paired superiority, no
  official/pinned-reproduction language, Office never a passed category).
- The strict gate (`rebuild_hstu_submission.py --strict`) must pass at any commit that changes
  paper content; the LaTeX is regenerated *from* the gated markdown, never edited divergently.

## DOI (related decision, same date)

Minting is **deferred** until a venue actually requires it ("skip for now"). The
hash-manifested GitHub releases (`v0.9-audit-evidence`, `v1.0-deposit`) remain the citable
artifact reference; everything needed to mint in ~3 clicks stays prepared
(`DOI_DEPOSIT_INSTRUCTIONS.md`).
