# WEARec long-sequence adaptive collapse decision

Date: 2026-08-02

## Decision: fail

The preregistered length-200 extension of Depth-Gated Adaptive Head Collapse
fails its accuracy-neutral efficiency rule. Both official checkpoints passed
the label-free weight-consensus gate and both compact implementations matched
their expanded projections, but validation ranking quality did not satisfy the
frozen noninferiority bounds.

| dataset | baseline NDCG@10 | delta | paired 95% CI | decision |
|---|---:|---:|---:|---|
| Foursquare | 0.015109 | -0.001644 | [-0.003743, +0.000187] | fail |
| LastFM | 0.070474 | -0.000362 | [-0.003528, +0.002960] | fail |

Foursquare violates the `-0.0005` point-delta bound. Both datasets violate the
`-0.0015` confidence-interval lower bound. No projected test split was
evaluated.

## Efficiency result

The structural implementation is valid but does not rescue the quality
failure. It reduces the final generator output map from one map per head to a
single map and broadcasts a stride-based view:

| dataset | whole-model parameters saved | output-layer MAC reduction | compact parity |
|---|---:|---:|---:|
| Foursquare | 91,910 (9.640%) | 87.5% | within `atol=rtol=1e-6` |
| LastFM | 13,130 (3.389%) | 50.0% | exact in the smoke input |

The two-repeat CPU smoke timings were deliberately contended and are not
latency evidence. A proper timing study is not warranted for this rejected
variant.

## Interpretation

High rank-1 energy and alignment of the dominant right singular vector with a
uniform head vector are not sufficient to certify that head-specific residuals
are functionally dispensable. This is especially clear on sparse Foursquare:
only 24 of 1,083 users changed NDCG@10, but harmful changes dominated 17 to 7,
producing a large relative loss.

The supported length-50 LastFM/Sports result therefore does not extrapolate to
the regime where adaptive-head collapse would provide the largest whole-model
saving. DAHC remains a narrow retrospective regularization observation, not a
general efficiency algorithm and not a Tier-A scale-up candidate.

## Provenance

- Preregistration SHA-256:
  `2859ab4a5f7a5ec9e3708cf25e7adda9c6db0396e4b1d251bf2bf5de1da88cf1`.
- Foursquare validation artifact SHA-256:
  `701c3cfda9598c46e9b70095f47e44a955e17a438f185a2ca85baa2dcbadb1b5`.
- LastFM validation artifact SHA-256:
  `e8b835453ba2bb155b5dc8d5b633e7e9838223ec542b48ff0c7cfb854754906c`.
- Foursquare compact smoke artifact SHA-256:
  `92e51756fa1b92287f5cd25c3e9bf9a8ee7011483b8ba1e707d1a4aa61bc6b3f`.
- LastFM compact smoke artifact SHA-256:
  `a36b96170f2a8e451e346e87a01adc90daf1e0dfe8e44077a97e4da02053364e`.

