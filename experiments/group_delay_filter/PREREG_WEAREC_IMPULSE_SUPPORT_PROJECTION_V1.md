# Preregistration: WEARec impulse-support generator projection v1

Frozen on 2026-08-02 after label-free impulse analysis of the official WEARec
checkpoints, but before projecting or evaluating any checkpoint under this
intervention. Official baseline logs and outcomes from the separate head-
collapse studies are visible. No projected test outcome will be accessed.

## Question

Can a trained, sequence-conditioned frequency-response generator be converted
to a compact symmetric FIR generator by deleting distant impulse lags, while
preserving recommendation quality and head-specific behavior?

## Fixed source and checkpoints

Use official WEARec revision
`2087335339b1ead87da6e066ce14e2d33880a95e`, source identities from
`PREREG_WEAREC_STATIC_BASE_PROJECTION_V1.md`, and the following checkpoints:

| dataset | length | heads | alpha | data SHA-256 | checkpoint SHA-256 |
|---|---:|---:|---:|---|---|
| Beauty | 50 | 8 | 0.2 | `226cce9c3105299ca0db9615d7d3fb32b3175e90da43100ae352599f0f0107b8` | `be46edc77f2833ca882cd113b99dbc62605cb43cc9b13c2b9764b6769c25f1cc` |
| Sports_and_Outdoors | 50 | 4 | 0.3 | `2a095e0648872beb9982408958290f5d655db5be2911c3756b5446de9f0b8de2` | `d5bd261ff5c973dbf0ac57e480545484da1f09e40ebef9b550ffd10b3a74a387` |
| Foursquare | 200 | 8 | 0.9 | `95e9c3bccaec1e51cad828e3eca84c637720cd5e01717908be1493f051ace7ef` | `4db52a316f2ade4a412dd018dcf4baece18149d80db18e6637de6690987ba598` |

## Frozen transform and gate

For each `adaptive_mlp.2.weight` and bias, reshape the output axis to
`heads x frequencies x 2` (and input width 64 for the weight). Move frequency
first and interpret every real frequency sequence as an `rfft` spectrum with
zero imaginary part. Apply an orthonormal `irfft` of the configured sequence
length.

For an impulse radius `r`, retain lag zero, positive lags `1..r`, and their
circular negative-lag mirrors; zero every other lag. Find the smallest radius
that retains at least 95% of each tensor's impulse energy. For a layer, use the
larger of its weight and bias radii. Only the final layer is eligible, and only
if this common radius is no greater than 20% of sequence length. Project both
final tensors at the common radius and leave every other parameter unchanged.

The projected impulse is symmetric. Its compact form stores only lags `0..r`,
mirrors positive lags, and obtains the real frequency response with `rfft`.
This preserves heads rather than tying them.

The frozen label-free decisions are:

| dataset | weight radius / energy | bias radius / energy | common radius | decision |
|---|---:|---:|---:|---|
| Beauty | 9 / 0.952002 | 2 / 0.973868 | 9 | project |
| Sports_and_Outdoors | 9 / 0.953440 | 0 / 0.968400 | 9 | project |
| Foursquare | 40 / 0.950632 | 2 / 0.951019 | 40 | project |
| LastFM, length 50 | 16 / 0.951600 | 3 / 0.955264 | 16 | abstain |
| ML-1M, length 50 | 24 / 0.972579 | 3 / 0.966290 | 24 | abstain |
| LastFM, length 200 | 71 / 0.952336 | 8 / 0.950524 | 71 | abstain |

Do not evaluate abstaining checkpoints.

## Frozen structural savings

The compact final output map stores
`heads * (r + 1) * 2 * (64 + 1)` scalars. Before any runtime transform, this
gives:

| dataset | output-map reduction | complete-model parameters saved |
|---|---:|---:|
| Beauty | 61.538% | 16,640 (1.827%) |
| Sports_and_Outdoors | 61.538% | 8,320 (0.648%) |
| Foursquare | 59.406% | 62,400 (6.545%) |

These are structural counts, not latency claims. A compact implementation and
timing study require a feasibility pass.

## Frozen evaluation and decision

- Validation only, full catalog, strict negative-infinity masking of padding
  and training-history items.
- Paired per-user HR/NDCG at 5, 10, and 20.
- Primary endpoint: projected minus baseline NDCG@10.
- 10,000 paired-user bootstrap resamples, seed `314159`.

- **Support:** every point delta is at least `-0.0005`, at least two are
  nonnegative, and their unweighted mean is nonnegative.
- **Accuracy-neutral efficiency support:** every point delta is at least
  `-0.0005`, every confidence-interval lower endpoint is at least `-0.0015`,
  and the stronger rule fails.
- **Fail:** either noninferiority condition fails.

A pass would establish retrospective feasibility for Impulse-Support Generator
Projection (ISGP), not novelty or a state-of-the-art result. Before scale-up it
must be audited against TV-Rec's time-variant graph-filter taps, generic dynamic
filter networks, temporal-kernel pruning, and post-training structured
projection.

