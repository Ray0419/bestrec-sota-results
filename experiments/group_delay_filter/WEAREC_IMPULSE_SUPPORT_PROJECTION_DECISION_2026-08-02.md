# WEARec impulse-support projection decision

Date: 2026-08-02

## Decision: fail

Impulse-Support Generator Projection (ISGP) passes on the two length-50
checkpoints but fails decisively on the materially efficient length-200 case.
It therefore does not satisfy the preregistered cross-regime noninferiority
rule and is not a scale-up candidate.

| dataset | baseline NDCG@10 | delta | paired 95% CI | whole-model saving |
|---|---:|---:|---:|---:|
| Beauty | 0.073344 | +0.000131 | [-0.000147, +0.000412] | 1.827% |
| Sports_and_Outdoors | 0.043127 | +0.000313 | [-0.000053, +0.000691] | 0.648% |
| Foursquare, length 200 | 0.015109 | -0.002045 | [-0.003776, -0.000676] | 6.545% |

Foursquare violates both frozen noninferiority conditions. Its point loss is
four times the allowed `-0.0005` bound, and the paired interval is entirely
negative. No projected test split was evaluated.

## Interpretation

The label-free 95%-energy support gate removes 61.5% of the final adaptive
output map on Beauty and Sports while leaving 98.4% and 96.7% of user NDCG@10
values unchanged. This preserves head diversity and is a cleaner short-
sequence result than hard head sharing.

It does not transfer to the setting where the saving matters most. On
Foursquare, retaining 95.1% of aggregate impulse energy at radius 40 changes
only 16 of 1,083 users, but 14 are harmed and only 2 improve. Low-energy remote
lags can therefore be ranking-critical in sparse long-sequence data. Aggregate
weight energy is not a reliable functional importance measure.

The exact post-training FIR-generator projection appears unoccupied in the
target literature, but an unoccupied failed method is not a contribution.
Calibration-weighted impulse importance is a possible research question; it
would need to abstain on this checkpoint or preserve its rankings while still
showing material savings. Generic activation-aware pruning and TV-Rec's graph-
filter taps make that follow-up's novelty uncertain, so it is not yet
authorized for large-scale work.

## Provenance

- Preregistration SHA-256:
  `5e6df6feb3d7fd3ea29d6fda6f15e045ea9a84a2a773ac174e71a061c6050130`.
- Beauty artifact SHA-256:
  `486bf16fa77f370e44df0b6b03b666607584656568a814ee0a6888ab9a16e957`.
- Sports artifact SHA-256:
  `c5dea3624af595a4fb1c93a89339ebbf038a42dbc0d3a861c27cbc8a9c6867ce`.
- Foursquare artifact SHA-256:
  `265a6e5f7b22271a674e8fb793e4311eef0f596082b96b48cfa59e693449df10`.

