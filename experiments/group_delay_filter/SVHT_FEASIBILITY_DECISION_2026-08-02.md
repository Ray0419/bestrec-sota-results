# Late-filter SVHT feasibility decision — 2026-08-02

## Candidate

Apply the Gavish-Donoho unknown-noise singular-value hard threshold to the final
complex temporal filter only. The rule chooses rank from the matrix aspect ratio
and median singular value, uses no recommendation labels, and leaves all earlier
layers unchanged.

## First-seed falsification

| dataset | split | selected rank | delta NDCG@10 | paired-user 95% CI |
|---|---|---:|---:|---:|
| ML-1M seed 42 | validation | 2 | +0.005454 | [+0.003573, +0.007321] |
| LastFM seed 42 | validation | 1 | -0.001449 | [-0.003086, +0.000119] |

On the identical ML-1M seed, frozen-threshold EGSP rank-1 projection improves
validation NDCG@10 by `+0.009302`, so SVHT preserves less of the useful
regularization effect. On LastFM, unlike EGSP, SVHT activates and incurs a loss
larger than the `0.0005` feasibility tolerance. Only 8 users improve while 24
are harmed among the 32 whose NDCG@10 changes.

## Decision

**Kill as a broader replacement for EGSP.** The method is neither outcome-safe
across the first two datasets nor more effective on the positive MovieLens
case. Beauty and Toys evaluations were not run after the fixed first-seed gate
failed. Generated checkpoints and all rank-selection summaries remain in the
artifact tree.

The rank rule is established matrix-denoising prior art; see
[Gavish and Donoho, 2014](https://arxiv.org/abs/1405.7511). This branch therefore
would also offer less algorithmic novelty than a mechanism-gated filter result.
