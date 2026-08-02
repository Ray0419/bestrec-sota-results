# Preregistration: WEARec adaptive-head projection v1

Frozen on 2026-08-02 after label-free checkpoint inspection and after the
separate static-base projection study, but before evaluating this adaptive
projection. Official baseline outcomes and static-projection validation
outcomes are visible. This is retrospective feasibility evidence only.

## Question

Can WEARec's final input-dependent frequency-modulation output be shared
across heads when its learned output map has already converged to a
head-consensus endpoint?

## Fixed source and identities

Use official WEARec revision
`2087335339b1ead87da6e066ce14e2d33880a95e`, source/data/checkpoint identities,
model settings, and strict validation evaluator from
`PREREG_WEAREC_STATIC_BASE_PROJECTION_V1.md`.

## Label-free gate and intervention

For each block, reshape `adaptive_mlp.2.weight` from
`(heads * 26 * 2) x 64` to `26 x 2 x 64 x heads`; reshape its bias to
`26 x 2 x heads`. Treat heads as matrix columns. Compute rank-1 retained
energy and dominant-head/uniform cosine for both tensors.

Only the final block is eligible. Project both tensors to their column means
if both independently satisfy retained energy `>= 0.905` and uniform cosine
`>= 0.97`. Leave every other parameter untouched. Under the frozen gate:

- LastFM is eligible: weight `rho=0.932518`, cosine `0.999240`; bias
  `rho=0.992276`, cosine `0.999980`.
- Sports_and_Outdoors is eligible: weight `rho=0.930313`, cosine `0.999426`;
  bias `rho=0.988239`, cosine `0.998912`.
- Beauty and ML-1M abstain because the final output-weight energies are
  `0.871416` and `0.804424`, respectively. Do not evaluate projected models
  for these abstentions.

The deployable form stores one `26 * 2` output map and bias per final layer
and broadcasts them across heads. This reduces that linear layer's output
width by the head count; the feasibility implementation may expand the mean
back to the original checkpoint shape for unchanged model code.

## Evaluation and decision

Evaluate paired full-catalog validation HR/NDCG at 5, 10, and 20 with strict
negative-infinity history/padding masking, 10,000 paired-user bootstrap
resamples, and seed `314159`. Do not access projected test outcomes.

- **Support:** both NDCG@10 deltas are at least `-0.0005` and their unweighted
  mean is nonnegative.
- **Compression-only support:** both deltas are at least `-0.0005`, but their
  mean is negative.
- **Fail:** either delta is below `-0.0005`.

Even a pass is not a novelty or Tier-A scale-up authorization. It would first
require a narrowed prior-art audit and a from-scratch compact implementation
showing realized parameter/latency savings.
