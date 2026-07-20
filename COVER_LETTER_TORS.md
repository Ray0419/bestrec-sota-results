# Cover letter — ACM Transactions on Recommender Systems (TORS)

Dear Editors,

We submit "BEST-Rec: an artifact-gated evaluation study of text-augmented
HSTU-style sequential recommendation on Amazon Reviews 2023" for consideration as
a full research article.

**What the paper is.** An evaluation-first study built around a fail-closed
apparatus: version-controlled pre-declarations, a build gate that recomputes all
**175 artifact-gated table cells** from released, hash-manifested artifacts before
any PDF can be produced (prose numbers outside those cells are conventional
manuscript text), comparator regeneration under disclosed environment caveats, and
symmetric self-VOIDing adjudication — one campaign (Office_Products V1) remains
VOID by its own frozen rule and is reported as such, permanently.

**The findings, at their exact strength.**

1. Two pre-registered per-category point-estimate comparisons pass against the
   published HSTU-BLaIR numbers (Musical_Instruments and Office_Products V3, the
   latter also against an environment-matched local regeneration). These are
   point-estimate comparisons under our reproduced protocol — not SOTA claims of
   any kind and not paired or distributional superiority.
2. A leak-free causal FIR filter is supported on four categories **as the
   FIR-plus-initialization/optimizer package** — the bundle our design can
   attribute (a singular zero-gradient initialization means Adam's weight decay
   participates in the mechanism; §3). No filter-only causal attribution is
   claimed; the nonsingular matched control that could isolate it is stated as
   open, unrun work.
3. The Musical_Instruments tail advantage of frozen text features survives a
   repaired estimand (tie-safe cohorts, zero-exposure targets separated) but is
   **frequency-5-heavy**: excluding the boundary-frequency group the tail delta is
   null, the cross-dataset contrast did not replicate, and zero-exposure targets
   record zero hits through rank 100 in all four rerun categories — no cold-start
   capability is claimed. An interaction-thinning titration is reported as a
   **refuting** keystone (the head effect tracks thinning; the tail effect does
   not, and the density-matched rung does not reproduce the tail advantage).

**Evidence taxonomy, stated plainly.** Statements in the paper are pre-declared,
exploratory, post-hoc development analyses (labeled as such — e.g. the §5.1
attribution rungs), or explicitly retracted; retractions and defects are reported
in full in the manuscript, not in supplementary material. The TFV2 repaired-
estimand campaign is pre-declared in Git but **outcome-visible**, and its
OpenTimestamps proofs' earliest independently verifiable Bitcoin attestation
(block 958749, 2026-07-20 01:48:23 AEST) postdates its first completed result
(≈ 01:36 AEST) — we therefore do not claim independent external timestamping
before launch and do not label that campaign confirmatory (§5.3, disclosure
(vii); the frozen pre-registration carries a dated chronology erratum). Same-seed
arms are **not** initialization-paired (§5.3 randomization disclosure); no paired
inference appears anywhere, and formerly paired analyses are retracted in place.

**Data and artifacts.** The public repository releases code, derived
interaction-split CSVs, frozen text caches, and per-user evaluation sidecars as
hash-manifested assets (the raw dataset is not re-shipped, but we state plainly
that derived interaction-level splits are redistributed, that the dataset
maintainers' public statement is not an affirmative permission grant, and that
the redistribution basis is flagged for venue-level review with immediate
takedown honored — manuscript §10). Dense sidecar identifiers are
deterministically linkable to the platform's pseudonymous identifiers through the
released splits, a linkage surface §10 states rather than obscures. The
manuscript PDF is anonymized for double-anonymous review; the named public
repository and deposit are the post-acceptance record, and we will follow the
journal's current instructions on anonymized artifact access at review time.

**Adversarial review disclosure.** Throughout preparation the manuscript was
subjected to an hourly adversarial audit by an **author-operated automation**
(a separate coding agent instructed to falsify our claims against the public
artifacts); every round and every point-by-point response is preserved verbatim
in the repository. We describe this as tooling we ran on ourselves — it is not
independent review, and we do not present it as such.

**Open work stated as open.** The closest-comparator benchmark (AlphaFuse), the
item-text permutation control, the sequence-split/target-multiplicity parity
control, and the nonsingular matched-FIR initialization control are identified,
scoped, and unrun; the paper's claims are drawn narrowly enough to stand without
them, and §6.5 lists them as the decision-relevant next experiments.

Suggested reviewers / excluded reviewers: [Maintainer: optional.]

Thank you for your consideration.

[Author name(s) and contact — withheld in the anonymized review copy; TORS review is
double-anonymous and the manuscript PDF carries no identifying information.]
