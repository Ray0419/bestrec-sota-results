# Collapse-routed projection feasibility protocol V1

Frozen after the nested-user spectra were recorded and before creating or
evaluating their projected checkpoints.

## Question

Does the already frozen layer-local EGSP rule improve validation ranking when
rank collapse appears in different depths as ML-1M cohort size changes?

## Fixed states and interventions

- 943-user seed-47 checkpoint SHA-256:
  `08ce3ba1040fc21a7f0d0f6f4d512150448258d6c4dbd2dd59e3811bb0c8a744`.
  Project its first filter only (`rho_1 = 0.905805`).
- 2,000-user checkpoint: no layer crosses `0.905`; abstain without evaluation.
- 4,000-user seed-47 checkpoint SHA-256:
  `59aa14c6eda31ce37a14d2ecef8e911a375d803da65b1dbd93d50e3c0483bde4`.
  Project its late filter only (`rho_1 = 0.909011`).
- Projection is exact rank-1 SVD, layer-local, and training-free. All other
  parameters remain byte-equivalent.

## Fixed evaluation

- Split: validation only. Cohort test metrics remain inaccessible.
- Full item catalog with strict negative-infinity seen-item masking.
- Primary metric: paired-user NDCG@10 delta.
- Report a 10,000-sample paired-user bootstrap 95% interval.
- Use the same baseline and projected evaluation path for each cohort.

## Decision rule

- **Survive:** both cohort deltas are nonnegative and at least one paired-user
  interval excludes zero on the positive side.
- **Fail:** either cohort delta is below `-0.0005`.
- **Inconclusive:** every other outcome.

A survive result only supports a within-dataset mechanism hypothesis. It does
not authorize a cross-dataset claim, test-set result, threshold change, or
large-scale campaign. A fail closes energy-only layer routing as the algorithm.

## Integrity constraints

- Do not change threshold, rank, selected layers, evaluator, split, or metric.
- Do not evaluate the abstaining 2,000-user checkpoint against an identical
  state and count that deterministic zero as evidence.
- Do not inspect cohort test metrics.
