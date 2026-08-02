# Preregistration: long-sequence WEARec adaptive-head collapse v1

Frozen on 2026-08-02 after the length-50 adaptive-head feasibility study and
label-free inspection of every official long-sequence checkpoint, but before
evaluating either projected length-200 checkpoint on validation. Official log
metrics are visible. No projected test metric has been accessed.

## Question

Does the final adaptive frequency-generator output become head-redundant in
long-sequence WEARec, where collapsing it can remove a material fraction of
the complete model without degrading ranking quality?

## Fixed source and checkpoints

- Official repository: `https://github.com/xhy963319431/WEARec.git`.
- Revision: `2087335339b1ead87da6e066ce14e2d33880a95e`.
- `src/model/wearec.py` SHA-256:
  `da12a6cc4c7da12eb0045b9f20ee158a757e7fe00ae5de7b0acd55e10f298e4f`.
- `src/dataset.py` SHA-256:
  `4395e9f7087674c00bfa09ea8a03773e70ab5b6f075ea93406008a57bb2133b7`.

| dataset | length | heads | alpha | data SHA-256 | checkpoint SHA-256 |
|---|---:|---:|---:|---|---|
| Foursquare | 200 | 8 | 0.9 | `95e9c3bccaec1e51cad828e3eca84c637720cd5e01717908be1493f051ace7ef` | `4db52a316f2ade4a412dd018dcf4baece18149d80db18e6637de6690987ba598` |
| LastFM | 200 | 2 | 0.1 | `9ded486adb5b0fe9dc761950afa0a9a05e93ff018992e0c52bf11afec529f802` | `693da906117679dbb6499b61a87d83a6a970137b51231ee70bd4870409ea37df` |

These are the official length-200 configurations reported in the repository's
long-sequence benchmark. The extra Foursquare alpha-0.6 checkpoint is excluded
to avoid treating two hyperparameters on the same users as independent
datasets.

## Label-free gate and intervention

Let `F = 200 / 2 + 1 = 101`. In each block, reshape
`adaptive_mlp.2.weight` from `(heads * F * 2) x 64` to
`F x 2 x 64 x heads` and its bias to `F x 2 x heads`. Treat heads as matrix
columns. Compute rank-1 retained energy and the absolute cosine between the
dominant right singular vector and the uniform-head vector.

Only the final block is eligible. Replace all head columns by their mean only
when both weight and bias independently have retained energy `>= 0.905` and
uniform cosine `>= 0.97`. Otherwise abstain. The frozen label-free statistics
are:

| dataset | weight energy | weight cosine | bias energy | bias cosine |
|---|---:|---:|---:|---:|
| Foursquare | 0.916954 | 0.995338 | 0.972147 | 0.994000 |
| LastFM | 0.913507 | 0.995425 | 0.960561 | 0.997413 |

Both checkpoints are eligible. Leave the first block and every other tensor
unchanged. The deployable implementation computes one `101 x 2` output and
broadcasts it across heads without materializing a copy.

## Frozen efficiency quantities

The compact final output map removes `(heads - 1) * 101 * 2 * (64 + 1)`
parameters and the same head fraction of its matrix multiply:

| dataset | parameters saved | whole checkpoint | output-layer MAC reduction |
|---|---:|---:|---:|
| Foursquare | 91,910 | 9.640% | 87.5% |
| LastFM | 13,130 | 3.389% | 50.0% |

These are exact structural counts, not latency claims. A compact model must
match the expanded projected model to tolerance `atol=rtol=1e-6` before any
timing result is accepted.

## Frozen evaluation

- Validation only; do not evaluate a projected checkpoint on test.
- Full catalog, with padding item zero and all training-history items masked
  to negative infinity.
- Paired per-user HR and NDCG at 5, 10, and 20.
- Primary endpoint: projected minus baseline validation NDCG@10.
- Uncertainty: 10,000 paired-user bootstrap resamples, seed `314159`.

## Frozen decision

- **Accuracy-improving support:** both NDCG@10 point deltas are nonnegative,
  their unweighted mean is positive, and at least one paired 95% confidence
  interval has a positive lower endpoint.
- **Accuracy-neutral efficiency support:** both point deltas are at least
  `-0.0005`, both confidence-interval lower endpoints are at least `-0.0015`,
  and the stronger rule fails.
- **Fail:** either point delta is below `-0.0005` or either confidence-interval
  lower endpoint is below `-0.0015`.

Even strong support is not an authorization for a paper-scale claim by itself.
It must be combined with exact compact parity, uncontended latency evidence,
additional independently trained seeds or datasets, and a novelty analysis
against DirectShare/PostShare and generic post-training parameter sharing.
