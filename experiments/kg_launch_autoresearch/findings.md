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

No confirmatory experiment has run. H1 is next; its metric and decision gate will be committed before execution.

