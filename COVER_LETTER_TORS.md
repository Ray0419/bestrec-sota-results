# Cover letter — ACM Transactions on Recommender Systems (TORS)

Dear Editors,

We submit “Artifact-Gated Evaluation of a Causal FIR Module for Sequential
Recommendation” for consideration as a full research article in *ACM
Transactions on Recommender Systems*.

**Required author declarations — verify at submission.** [Maintainer: confirm
that the work is original, has not been published previously, and is not under
review or submitted elsewhere; complete authorship, affiliation, funding,
conflict-of-interest, ethics/privacy, licensing, and corresponding-author
metadata in the manuscript and submission portal.]

**Fit and contribution.** The paper evaluates a small, detachable, strictly
left-causal finite-impulse-response residual for sequential recommendation. It
is an incremental modular contribution, not a new recommender architecture. We
believe it fits TORS's interest in recommender-system algorithms and rigorous
evaluation: the module, its mechanism boundary, and an artifact-gated reporting
workflow are assessed together.

**Main result at its exact strength.** Matched-initialization internal estimates
for the trainable causal residual over frozen identity are positive on three
Amazon Reviews 2023 categories: Musical_Instruments (+0.002265, ordinary Welch
95% CI [0.001928, 0.002602]), Industrial_and_Scientific (+0.002110 [0.001820,
0.002399]), and CDs_and_Vinyl (+0.006150 [0.005849, 0.006450]). All are
outcome-known or test-exposed internal studies, not independent confirmation.

A pre-declared, likewise outcome-known six-arm control study narrows the
interpretation. Every temporally active arm improves identity after its frozen
Holm procedures. Learned taps outperform two algebraically redundant fixed
filter parameterizations, but advantages over a shared-filter control and a
parameter-matched nonlinear causal control are not established. Because no
active lag-0 or pointwise parameter-matched non-temporal placebo was run, the
study does not isolate temporal structure from generic trainable-residual
capacity and does not claim learned-tap superiority.

**Secondary results.** Two per-category point estimates exceed published
HSTU-BLaIR values under explicitly environment-caveated reproduced protocols;
these are neither general system-ranking claims nor paired/distributional
superiority claims. A repaired text-tail analysis finds a small
Musical_Instruments effect concentrated at interaction frequency 5, no hits for
zero-exposure targets through rank 100, and no replicated cross-dataset
contrast. We therefore make no cold-start, transfer, or general state-of-the-art
claim.

**Why the evidence is inspectable.** A fail-closed graph recomputes 192
paper-bound cells across 18 claim families from released artifacts. The release
manifest and strict rebuild preserve positive, null, deviated, and permanently
VOID outcomes under the same reporting rule. A fresh deep-path Windows clone
bootstrapped and raw-hash-verified all 282 release-only assets, reproduced exact
core-block parity against the disclosed HSTU-BLaIR commit, verified 751/751
manifested files, and completed the strict rebuild. The public repository is
https://github.com/Ray0419/bestrec-sota-results.

**Material limitations and disclosure.** The manuscript reports outcome
visibility, dirty-tree execution during one campaign, incomplete independent
custody, fixed-split seed-level inference, construct/deployment sensitivities
that were not run, and the absence of untouched confirmation. An author-operated
adversarial audit and its point-by-point response are preserved in the
repository; we do not present that tooling as independent peer review. The
current evidence release is not represented as the final immutable archival
deposit. [Maintainer: create the final versioned release and DOI deposit only
after author/legal metadata and redistribution permission have been verified.]

Suggested reviewers / excluded reviewers: [Maintainer: optional; verify no
conflicts under the current portal rules.]

Thank you for your consideration.

[Maintainer: real author name(s), affiliation(s), country, and corresponding-
author contact required.]
