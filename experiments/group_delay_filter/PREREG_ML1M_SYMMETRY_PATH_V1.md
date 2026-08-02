# Analysis plan: ML-1M channel-symmetry path v1

Frozen on 2026-08-02 before evaluating an interior point on the path. This is
an outcome-known exploratory mechanism test, not confirmatory evidence.

## Question

Is the validation gain from final-layer channel sharing a stable contraction
toward the shared-filter subspace, or an isolated endpoint effect?

For each of the existing ML-1M spectral checkpoints at seeds 42-46, decompose
the final temporal-filter matrix as

```text
W = P(W) + D,
```

where `P(W)` repeats the channel mean and `D` is the channel-specific
deviation. Evaluate `P(W) + alpha D` at fixed interior values
`alpha in {0.25, 0.50, 0.75}`. The already evaluated endpoints are
`alpha=0` (shared projection) and `alpha=1` (original checkpoint).

Use the existing full-catalog validation evaluator, strict negative-infinity
seen-item masking, no fine-tuning, and no test access. Do not add an alpha or
drop a seed after inspecting an interior result.

## Frozen interpretation

- Call the path **ordered toward sharing** if the mean validation NDCG@10 is
  non-increasing in `alpha` over `{0, 0.25, 0.50, 0.75, 1}` and at least four
  of five individual seeds have their best value at `alpha <= 0.25`.
- Call it **interior shrinkage** if the best mean occurs at an interior alpha
  and exceeds both endpoints by at least `0.0005`.
- Otherwise call the path irregular and do not motivate an annealed projection
  from this experiment.

Even an ordered path does not authorize a new training campaign. It only
supports one preregistered single-seed annealing pilot after the exact
early-full/final-shared training control is adjudicated.
