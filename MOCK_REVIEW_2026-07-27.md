# Mock review — modular-contribution submission audit (2026-07-27)

## Executive verdict

**Recommendation: major revision before submission.** The paper is now coherent
as an incremental modular-contribution article. It does not need a brand-new
end-to-end algorithm to be publishable. The strongest editorial story is: a
small causal residual, carefully bounded active controls, and an unusually
inspectable evidence record. The remaining weakness is scientific identification,
not manuscript positioning.

There are two different “current acceptance” questions:

- **Literal package today: 0% submittable.** Author identity, affiliation,
  country, short-author metadata, declarations, and legal/redistribution checks
  are unresolved. The release build requires a draft waiver.
- **Scientific manuscript after those administrative fields are completed:** a
  subjective **25–40% eventual TORS acceptance range**, midpoint about **32%**.
  TORS does not publish an authoritative acceptance rate that can convert this
  into a calibrated probability. This range is therefore a risk assessment, not
  a venue statistic.

The present paper is more likely to receive “major revision” or “reject and
resubmit” than acceptance without another experiment cycle. Reaching a
defensible **55–65%** range requires favorable results from the priority studies
below; editing and artifact polish alone cannot produce that increase.

## Editorial screen

### Fit

**Pass.** The contribution concerns an algorithmic component and its evaluation
in recommender systems. The manuscript now consistently calls the work modular
and incremental, not a new architecture. The audit/rebuild apparatus supports
the scientific contribution rather than replacing it.

### Novelty

**Borderline but viable.** A causal depthwise FIR residual is a recognizable,
detachable design contribution. Novelty comes from the exact adaptation,
identity-active initialization, controls, and empirical boundary—not from
inventing finite-impulse-response filtering. This is sufficient in principle
for a journal article if the evaluation identifies what the module adds.

### Submission readiness

**Fail until human metadata and legal checks are complete.** Placeholders alone
can cause an administrative return or prevent submission. The current mutable
evidence release must not be described as the final archival deposit.

## Mock reviewer A — method and novelty

**Strengths**

1. The method is simple, detachable, and easy to implement.
2. The distinction between the canonical gradient-active residual and the
   historical zero-gated package is now clear.
3. Positive matched-initialization contrasts occur on three categories under
   one untuned breadth configuration.
4. Negative and statistically unseparated controls are reported rather than
   hidden.

**Major concern**

The active-control study does not identify a temporal FIR mechanism. Shared and
nonlinear causal controls recover similar gains, while no active lag-0 or
pointwise parameter-matched non-temporal residual was tested. The present
wording correctly narrows the claim, but that narrowing also weakens the reason
to prefer this module over generic residual capacity.

**Recommendation: major revision.** Add a preregistered active non-temporal
placebo and an efficiency-oriented shared/grouped/low-rank comparison. The paper
can remain publishable if a simpler arm matches FIR, but the contribution must
then become “a low-cost trainable residual family and its boundary,” not
learned temporal mixing.

## Mock reviewer B — evaluation and statistics

**Strengths**

1. The manuscript distinguishes Welch and paired analyses correctly.
2. All nine active-control adjusted p-values and both frozen Holm families are
   disclosed.
3. The paper does not interpret nonsignificance as equivalence.
4. Fixed-split, seed-level inference and outcome visibility are stated plainly.

**Major concerns**

1. Every headline FIR estimate is outcome-known or test-exposed; none is an
   untouched confirmation.
2. Inference is over optimizer seeds on fixed splits, not over temporal cutoffs,
   users, or items.
3. Current equal-protocol baselines such as FreqRec and WEARec are cited but not
   executed; the AlphaFuse port is correctly noncountable.
4. Construct sensitivities—ratings, verified purchases, event definitions,
   duplicate handling, global time, and query-time catalog—remain unrun.

**Recommendation: reject and resubmit unless one untouched evaluation is
added.** The existing results are useful development evidence, but a skeptical
reviewer can reasonably treat them as hypothesis-generating.

## Mock reviewer C — reproducibility and artifact quality

**Strengths**

1. The strict graph recomputes 192 cells across 18 claim families with no
   mismatch or untraceable cell.
2. A clean deep-path clone bootstrapped and raw-hash-verified 282/282
   release-only assets, verified 751/751 manifested files, reproduced exact
   aligned core-block parity, retained the permanent Office V1 VOID, and passed
   the strict rebuild.
3. The paper preserves null, deviated, refuting, and VOID results.
4. The PDF has been rendered and visually checked without clipping.

**Major concerns**

1. One campaign ran across a dirty evolving tree and lacked independent sidecar
   custody.
2. The public evidence release is mutable and the deposit tag is stale.
3. Dataset-derivative redistribution permission, privacy/linkage surfaces, and
   final licenses require human/legal confirmation.
4. PDF tagging, bookmarks, and complete accessibility text are incomplete.

**Recommendation: minor scientific revision, major release/legal revision.**

## Audit reconciliation

### Closed in wording, graph, or build

- E-A is correctly Welch/Satterthwaite; paired-by-seed is descriptive.
- Hybrid intervals are ordinary paired intervals; Holm adjusts decisions and
  p-values only.
- All control multiplicity results are printed.
- Stale transfer, confirmation, temporal-mechanism, and theorem claims are
  removed and guarded by health checks.
- FreqRec/WEARec citations and the BSARec theorem scope are corrected.
- E-A is represented in the evidence graph.
- The paper's contribution spine is consistently modular.
- Bootstrap coverage, clean-clone replay, table readability, and PDF overflow
  defects are repaired.

### Still open and acceptance-relevant

- Untouched one-shot confirmation.
- Active parameter-matched non-temporal placebo.
- Current equal-protocol baseline execution.
- Repeated temporal-cutoff or hierarchical inference.
- Construct/deployment sensitivities and cache/item-map binding.
- Final immutable versioned release and DOI deposit.
- Author, portal, ethics, privacy, licensing, and redistribution verification.
- Further body-length reduction and accessibility remediation.

## Step-by-step route toward a 55–65% risk estimate

### Gate 1 — make the package legally and administratively submittable

1. Fill real author names, affiliations, countries, emails, and short-author
   metadata.
2. Confirm author order, contribution statements, funding, conflicts, ethics,
   privacy treatment, dataset licenses, and derivative-redistribution authority.
3. Confirm the current TORS article type, review mode, length expectations, and
   portal declarations rather than relying on old notes.
4. Build without `DRAFT_WAIVER`; require every health and PDF hygiene check to
   pass.

**Effect:** removes the literal 0% submission blocker but does not materially
repair the scientific probability.

### Gate 2 — identify whether temporal structure matters

1. Freeze a new preregistration before any run or TEST inspection.
2. Use matched initialization and equal tuning budgets for identity, active
   lag-0/pointwise non-temporal residual, shared FIR, grouped/low-rank FIR,
   per-channel FIR, and the existing nonlinear causal comparator.
3. Predeclare one primary contrast: per-channel FIR versus the active
   non-temporal placebo. Predeclare a noninferiority margin for the cheaper
   shared/grouped arms.
4. Record parameter count, training time, inference latency, peak memory, and
   quality. Report a Pareto frontier rather than accuracy alone.
5. Adjudicate mechanically even if the placebo matches or wins; narrow the claim
   immediately in that case.

**Effect if favorable:** closes the largest mechanism objection and can move the
risk estimate by roughly 8–12 percentage points. If unfavorable, it still yields
a publishable simpler-component story only if efficiency is compelling.

### Gate 3 — add genuinely untouched confirmation

1. Select a temporal cutoff, category, or preferably a non-Amazon dataset using
   a rule fixed without looking at candidate outcomes.
2. Freeze preprocessing, hyperparameters, seeds, exclusions, primary endpoint,
   and failure rules.
3. Place final-evaluation artifacts under independent or automated one-shot
   custody so no author or coding agent sees outcomes during training.
4. Run once, adjudicate once, and retain the result regardless of sign.
5. Keep development evidence and confirmation evidence visually and verbally
   separate in the paper.

**Effect if favorable:** the single largest credibility gain, plausibly 10–15
percentage points. A null result does not invalidate the development study, but
it prevents a general robustness claim.

### Gate 4 — close comparator relevance

1. Implement official or author-validated equal-protocol versions of FreqRec and
   WEARec where technically possible.
2. Give each baseline the same data, candidate set, tuning budget, seed policy,
   and stopping rule.
3. Preserve AlphaFuse as noncountable unless its official protocol can be made
   comparable without silently changing it.
4. Frame the test as incremental value/cost of the FIR module, not a broad SOTA
   contest.

**Effect if competitive:** reduces the “dated or weak baselines” rejection path
by roughly 5–8 percentage points.

### Gate 5 — strengthen inference and construct validity

1. Repeat at several preregistered temporal cutoffs or splits.
2. Add user/item-aware or hierarchical uncertainty where the estimand supports
   it; do not treat more optimizer seeds as replacement for data resampling.
3. Run the smallest decision-relevant sensitivity set: duplicate policy,
   rating/verified-purchase filtering, event definition, query-time catalog, and
   global-time construction.
4. Bind caches and item maps cryptographically to the exact split/configuration.
5. Clearly separate robustness checks from new primary hypotheses.

**Effect:** addresses reviewers who accept the module but distrust fixed-split
seed inference or the Amazon-review construct.

### Gate 6 — finish the submission artifact

1. Reduce the venue body further by moving chronology and secondary titrations
   to a clearly linked supplement while retaining all claim-critical controls in
   the main article.
2. Add bookmarks, tagged-PDF/accessibility support where the production path
   permits, and complete figure/table alternative descriptions.
3. Freeze a manuscript-matched versioned tag only after all metadata and legal
   decisions are final.
4. Repeat the bootstrap and strict rebuild from a fresh clone; then create the
   archival DOI deposit and record exact digests in the availability statement.
5. Run one final hostile read using only the PDF and public repository, with no
   private explanation from the authors.

**Effect:** reduces desk, artifact, and trust failures. It cannot substitute for
Gates 2–5.

## Stop/go rule

Do not claim a 65% acceptance probability merely because all files build. A
55–65% subjective range becomes defensible only if Gates 1 and 6 are complete,
the untouched study in Gate 3 is valid, and at least two of Gates 2, 4, and 5
produce evidence that supports the final narrowed claim. If the untouched result
is null or the active placebo matches FIR without an efficiency advantage, keep
the paper honest and lower the estimate rather than changing the threshold.
