# Research Findings

## Research Question

Does knowledge-graph lift survive for future-born, zero-interaction items when every relation, candidate, and metadata field is restricted to information observable at recommendation time?

## Current Understanding

Knowledge graphs are widely claimed to mitigate sparsity and cold start, but the model family is mature and a recent systematic evaluation shows that KG removal or corruption often does not hurt accuracy. The credible unresolved issue is narrower: many cold-start evaluations make items interaction-cold while leaving them knowledge-rich, globally linkable, and embedded in a graph built from the completed catalog. That differs from a product at actual launch.

The candidate contribution is therefore a launch-safe evaluation and a lightweight modular patch, not another deep KG encoder. A prediction at cutoff `t` must be a function only of the information filtration available by `t`; two completed datasets with the same prefix must produce identical predictions at `t`.

## Key Results

- Literature audit: no located primary paper jointly enforces a global cutoff over interactions, item eligibility, entity alignment, KG relations, and metadata for full-catalog zero-interaction item recommendation.
- Local data feasibility: explicit Amazon listing dates cover about 96.4 percent of Digital Music metadata, 93.6 percent of Video Games, and 90.8 percent of Office Products.
- Digital Music is a useful stress case: 70,530/70,537 items have empty category lists, 70,465/70,537 have empty feature lists, and 42,405/70,537 have empty descriptions. This prevents an artificially easy, uniformly rich item-attribute graph.

These are bootstrap observations, not yet outcome evidence.

### H1 confirmatory result: refuted

The corrected deterministic run used 67,938 interacted items with parsable
listing dates, 6,430 future-born zero-prefix-interaction items, and 48,083
prefix-warm items. All locked sanity checks passed and the PowerShell error
stream was empty.

- Launch-cold link rate against the prefix graph: 0.63499.
- Launch-cold link rate against the completed graph: 0.69580.
- Bottom-frequency link rate against its completed graph: 0.60824.
- Deterministic-random link rate against its completed graph: 0.60264.
- Locked total support gap: -2.675 percentage points, below the +10 pp gate.
- Locked future-graph-only rate: 0.06081, below the 0.20 gate.

The hypothesized overstatement of graph support is therefore false in Digital
Music under the locked construction. In fact, launch items were slightly more
exact-linkable than either synthetic cohort. No outcome experiment should be
used to rescue H1.

The negative result still exposes a different measurable population: 36.50
percent of real launch items have no exact typed attribute link to a
prefix-visible warm item, and 4.93 percent have no eligible attribute at all.
This motivates the predeclared H4 only if a non-generic mechanism and outcome
gain can be demonstrated.

### H4 literature/feasibility gate: eliminated

The natural frozen-cutoff outcome cohort contains only 355 evaluable unlinked
pairs across 278 users. More importantly, semantic-support stratification and
generic content fallback are already occupied; a positive BLaIR fallback test
would not isolate a new KG mechanism. H4 is retained only as a diagnostic and
receives no outcome compute.

### H5 confirmatory structural result: supported

MIND-small provides timestamped impressions and Wikidata-linked news entities,
allowing a direct bounded comparison between the facts observable at the 2019
cutoff and a present Wikidata snapshot. This addresses a limitation Amazon
metadata cannot test. On the complete fresh `run_003` replay, all 50 historical
revisions resolved and all registered sanity checks passed. The
news-frequency-weighted current-only edge fraction was 0.24942, and all 12,060
selected news items were attached to an entity with at least one current-only
fact. Both locked structural gates passed.

The drift remained large after an exploratory label-blind restriction to the
1,091 relation IDs supplied by MIND: the weighted current-only fraction was
0.23718 and all 50 sampled entities remained affected. This does not show that
the changed facts alter recommendation rankings. H6 is now active: a locked
label-blind coverage audit must first establish that historical versus present
facts change enough candidate scores to justify an outcome POC.

## Patterns and Insights

- Algorithmic complexity is not the current bottleneck: LightKG-style simplification and KG4RecEval both weaken the case for another attention or denoising block.
- "Cold" has several non-equivalent meanings: low frequency, random unseen ID, future-born item, and unlinked item. Only the last two match the proposed limitation.
- Relation provenance matters. Catalog fields can be available at listing time; reviews, co-view, co-buy, and interaction-derived neighbors are endogenous and may arise only after exposure.

## Lessons and Constraints

- Do not claim broad temporal-KG novelty; temporal interaction/path models already exist.
- Do not call a relation leaked without source and timestamp evidence. Untimestamped relations must be excluded or reported as unknown.
- Do not use harmonic extension or effective-resistance uncertainty as the main patch; those directions were already tested locally and eliminated.
- Do not run Python directly on this Windows host. Structural experiments use single-process PowerShell. Any later Python outcome experiment must use the hardened launcher and validation contract.
- A benchmark-only result is insufficient unless it produces a substantial lift collapse, rank reversal, or new full-catalog failure pattern across domains.

## Open Questions

1. Are real future-born cold items less connected to prefix-visible warm evidence than conventional synthetic cold items?
2. How much apparent KG ranking lift survives after removing post-launch and endogenous relations?
3. Can a simple support/provenance gate use KG residuals only where the launch graph contains reliable evidence?
4. Does the result replicate outside Amazon item-attribute graphs on a dataset with publication-time entity annotations?

## Optimization Trajectory

H1 was refuted by `run_002`; H4 was eliminated before outcome compute. H5
passed its structural gate, and H6 is the active direction. Broad historical
point-in-time replay is not a novel algorithm after the GraphMatch collision.
Any surviving contribution must be narrower than generic content fusion,
support gating, or graph replay and must be locked before an outcome run.
