# Claude red-team memo — `TIER_A_NON_AMAZON_SELECTION_GATE.md` (gate A4)

Role: scientific red-team (`CODEX_CLAUDE_COLLABORATION_GUIDE.md` §3).
Reviewed: `TIER_A_NON_AMAZON_SELECTION_GATE.md` at HEAD `62c9326f`.
Date: 2026-07-31. Author: Claude. Advisory only — not external peer review, and
**not a legal opinion**; every licence/terms question below remains human-only.

```text
WORKSTREAM:        A4 external validity — pre-selection red-team of the dataset gate
OBJECTIVE:         does this gate select a dataset that can actually TEST our hypothesis?
EVIDENCE QUESTION: are the eligibility gates and scorecard diagnostic for a short-range
                   causal temporal filter, or only for legal/logistical suitability?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, the gate doc, any prereg, adjudicators,
                   artifact graph, generated tables, manuscript, TeX, release manifest
EXPECTED OUTPUT:   verdict + required additions + candidate-specific findings + sequencing
STOP CONDITION:    memo committed and pushed; no dataset selected, downloaded, or inspected
```

## Verdict: **APPROVE THE STRUCTURE — with two additions REQUIRED before any candidate goes to human legal review**

The hard-gate/scorecard/stop-rule architecture is sound, and three things are notably
right: UNKNOWN blocks rather than permits; the repository-licence-≠-data-licence warning;
and the refusal to substitute a convenient dataset post hoc. I endorse all three.

The gap: the gate optimizes for **lawfulness, logistics, and "distinctness"** but never asks
whether the candidate can *discriminate our actual hypothesis*. Our claim is about a
**short-range causal temporal filter** (`K=16` lags). A dataset can be maximally
"distinct from Amazon retail," fully lawful, and still be scientifically **uninformative or
actively confounded** for that specific mechanism. Two blocking additions follow.

---

## D1 (blocking addition). The scorecard has no mechanism-relevance dimension

"Domain distinctness from Amazon retail" (weight 3) rewards *being different*. But for a
recency/short-range filter, what determines diagnosticity is the **temporal structure** of
the interaction stream, not the product vertical:

- if the new domain has **far stronger** short-range structure than Amazon (dense sessions,
  seconds-scale gaps, autoplay), a positive FIR result is close to guaranteed and therefore
  weak evidence — the filter should trivially help;
- if it has **far weaker** short-range structure (months-long gaps, no sessions), a null is
  equally uninformative — there was nothing for a 16-lag filter to exploit.

Either way we would spend the program's scarcest resource — a genuinely unseen dataset — on
a result that cannot move a reviewer. **A dataset that is "different" is not the same as a
dataset that is "diagnostic."**

**Required addition — a metadata/TRAIN-only temporal-diagnosticity dimension**, frozen
*before* selection and computed **without touching TEST or any target label**:

- inter-event gap distribution (median, IQR, tail);
- session structure / burstiness (share of events within a short gap of the prior event);
- repeat-consumption rate (can the same item recur in a history?);
- sequence-length distribution relative to `K=16`.

Then **pre-declare the interpretation for each regime**, so the outcome is informative in
every direction: e.g. *"in a bursty, session-dominated regime a positive FIR result is
expected and therefore weakly informative; a null there would be strongly informative
against the mechanism."* This is what converts A4 from "a second dataset" into a test.

## D2 (blocking addition). KuaiRand's exposure/policy confound is hypothesis-specific and is currently listed only as an "open question"

The pre-screen names "policy/exposure mixing" among open questions. For **our** claim it is
not a side issue — it is the central threat to validity.

KuaiRand is **recommender-logged**: the next item is largely determined by *what the
platform chose to show*, under an autoplay/ranking policy with its own strong short-range
temporal signature. A learned 16-lag causal filter on such a stream can fit **the logging
policy's temporal autocorrelation** rather than user preference dynamics. A positive result
would then support "the FIR captures the deployed policy's short-range structure" — which
is not the claim we want, and is precisely the objection recsys reviewers raise first about
Kuaishou-family data.

The mitigating fact, which the pre-screen should state explicitly: the KuaiRand family is
distributed **with a randomly-exposed portion**, which exists to address exactly this bias.
Whether an unbiased/random-exposure subset can support a full-catalog next-item task at
usable scale is a **metadata-answerable question that must be settled before selection**,
not after.

**Required addition — an exposure-bias gate** (new hard gate 11): *for any
recommender-logged candidate, either an unbiased/random-exposure subset is usable for the
primary or sensitivity evaluation, or the policy confound is explicitly accepted and the
claim is pre-narrowed to "under logged-exposure conditions."* UNKNOWN blocks.

---

## Candidate-specific findings

**KuaiRand-Pure — strongest technical candidate; two additional flags beyond D2.**
- *Catalog scale.* A ~7.6k-video pool is far smaller than our Amazon catalogs (≈25k–78k).
  Full-catalog ranking is therefore *easier*, and metric magnitudes are **not comparable
  across blocks**. Pre-declare that cross-block comparison is of **direction and
  significance only**, never of effect size.
- *Repeat consumption.* Short-video permits re-watching; Amazon 5-core LLOO effectively does
  not. Repeats change what "next item" means and interact directly with a recency filter
  (a filter can exploit "recently seen ⇒ likely again"). The positive-event definition and
  repeat policy must be frozen before selection — the gate lists positive-event definition
  as open, but not its interaction with the mechanism.

**MIND-small — recommend upgrading from "risk" to hard exclusion, for a hypothesis-specific
reason the doc does not give.** Beyond the impression-candidate/task mismatch already noted,
news has **time-varying item availability**: an article cannot be clicked before publication
or long after it goes stale. A causal temporal filter would partly learn *availability*
rather than preference dynamics — a confound that sits directly on top of our claimed
mechanism. That is an estimand failure, not a preprocessing inconvenience.

**Yelp — the doc's legal/sparsity concerns are right; add a mechanism-relevance failure.**
Business-review inter-event gaps are typically weeks-to-months, so a 16-lag short-range
filter plausibly has little to exploit. Under D1 this scores poorly on diagnosticity even
if the licence question resolves favourably.

## D3 (non-blocking). "External custody" needs a definition that matches the claim vocabulary

The scorecard awards 2 points for "named willing custodian and written procedure," but the
guide reserves `externally custodied` for "a named external party [who] controlled the
boundary and supplies a dated attestation." Those are not the same bar. Specify that the
custodian **is not an author, is not supervised by an author, and attests in dated writing
to exactly which artifacts they controlled and when** — otherwise we will score custody
points that cannot be cashed as an evidence-class upgrade.

## D4 (non-blocking). Gate 6 is necessary but not sufficient — the *method* is Amazon-derived

"No target label previously inspected" protects the dataset. It does not change the fact
that `K`, the backbone, epochs, and schedule were all selected on Amazon. The new block
therefore tests **transfer of an Amazon-selected configuration**, which is honest and
publishable — but it must be pre-declared, and it interacts with my A3 finding W2 (the
backbone should take the full tuning ladder on the new block). Decide and freeze which of
these the new block is: a test of the *mechanism*, or of the *configuration's transfer*.

---

## Sequencing recommendation (this is the actionable part)

The human's decision cycles are the scarcest resource in this program, and A0/A1 are
already queued on them. **Do not send KuaiRand to human legal review yet.** Resolve D1 and
D2 first — both are metadata-only and need no licence decision:

1. Codex adds the temporal-diagnosticity dimension (D1) and the exposure-bias hard gate
   (D2) to the selection gate.
2. Score all three candidates on the revised scorecard from public metadata only.
3. **Then** send the single surviving top candidate to the human for terms/licence/custody
   review, with the exposure question already answered.

Otherwise we risk spending a human legal review on a dataset we subsequently reject on
scientific grounds — and A4 is already the binding constraint on A3, because my W2 fix
routes the entire fair-comparison claim through this block.

## Limits

No dataset was selected, downloaded, accessed, or inspected; no candidate interaction data
was touched. Statements about candidate datasets are drawn from the descriptions in the
gate document and are **not** independent verification of any dataset's contents, scale, or
terms — Codex/the human must verify against the authoritative sources. Nothing here is a
licence opinion. My audit is advisory evidence and cannot make any result independent.

**Codex is unblocked to add D1/D2 to the gate and re-score from metadata. No candidate is
approved, and no acquisition may begin.**
