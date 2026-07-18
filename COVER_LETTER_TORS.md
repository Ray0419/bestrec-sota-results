# Cover letter — ACM Transactions on Recommender Systems (draft; maintainer review required before submission)

> Tracked workspace draft created per audit 2026-07-18 06:13 (freeze-checklist item; the
> maintainer signs off and fills the bracketed fields at submission time). The claim
> boundary below is copied from `CANONICAL_SUBMISSION.md` and must never be broadened here.

Dear Editors-in-Chief,

We submit the manuscript **"Pre-Registered, Artifact-Gated Evaluation for Sequential
Recommendation: Causal FIR Filtering and Dataset-Conditional Text Benefits on Amazon
Reviews 2023"** for consideration at ACM Transactions on Recommender Systems.

## Declarations

- **Originality.** This manuscript is original work by the listed author(s). It has not been
  published previously, in whole or in part, in any archival venue.
- **Not under review elsewhere.** The manuscript is not under consideration at any other
  journal, conference, or workshop, and will not be submitted elsewhere while under review
  at TORS (per the venue's dual-submission policy; see also our sequenced venue plan in the
  artifact repository, `VENUE_PLAN.md`).
- **Prior/concurrent versions.** No preprint of this manuscript has been posted as of this
  submission. [Maintainer: update if an arXiv preprint is posted before submission.]
- **Conflicts of interest.** [Maintainer: list, or state none.]
- **Data and artifacts.** The public Amazon Reviews 2023 dataset (McAuley Lab) is used and
  not redistributed; the complete artifact (code, immutable pre-registrations, results of
  record, hash manifest, fail-closed build gate, and the full adversarial audit chain —
  the live hourly chain is git-tracked in every tagged tree) is
  available in the anonymized/named repository and its archival deposit release — the
  current deposit tag, recorded in `DOI_DEPOSIT_INSTRUCTIONS.md`. A single command
  re-verifies every printed empirical number.

## What the paper claims — stated exactly, for reviewer calibration

To pre-empt ambiguity, the claim boundary the paper enforces mechanically (a build-time scan
rejects broader wording) is:

1. **Two counted pre-registered per-category point-estimate comparisons** against published
   HSTU-BLaIR values, which are single-run comparators: Musical_Instruments (fresh 5-seed
   95% CI lower bounds 0.04096 / 0.04083 vs published 0.0406) and Office_Products under the
   redesigned V3 pre-registration (CI lower bounds 0.03033 / 0.03024 vs both the
   environment-matched local regeneration 0.0279 and the published 0.0271). **No paired or
   distributional superiority is claimed, and no state-of-the-art claim of any kind is
   made** (on Video_Games our headline sits below the published comparator and is described
   as competitive, not SOTA).
2. **The earlier Office V1 campaign is VOID** by its own pre-registered comparability
   tripwire and counts in no claim; the VOID is reported permanently and symmetrically
   alongside the passed V3 redesign.
3. **A leak-free, left-causal, zero-initialized depthwise FIR filter** improves results on
   all four categories tested — an internal paired filter-vs-no-filter contrast (two
   categories under a dedicated pre-registration with zero per-category tuning), never a
   comparator claim.
4. **Dataset-conditional text benefits**: frozen-text features help sparse categories and
   are ≈null on dense ones, supported by controlled thinning interventions.
5. **The evaluation apparatus itself** — immutable pre-registration, a fail-closed
   artifact gate that recomputes all printed numbers from source artifacts at every build,
   comparator regeneration, and symmetric self-VOIDing adjudication — is presented as a
   reusable per-paper discipline, demonstrated end to end on the claims above.

## Fit to TORS

The manuscript is a full-length evaluation-methodology + empirical study aimed at TORS's
scope on rigorous, reproducible recommender-systems research: every empirical statement is
pre-registered or explicitly labeled exploratory, all 168 printed numbers rebuild from
hash-pinned artifacts, and the repository includes the complete adversarial audit trail
(dozens of hourly audit rounds by an independent system, each answered point-by-point in
writing).

Suggested reviewers / excluded reviewers: [Maintainer: optional.]

Thank you for your consideration.

[Author name(s) and contact — withheld in the anonymized review copy; TORS review is
double-anonymous and the manuscript PDF carries no identifying information.]
