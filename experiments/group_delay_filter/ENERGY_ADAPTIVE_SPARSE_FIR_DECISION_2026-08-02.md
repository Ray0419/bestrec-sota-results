# Energy-adaptive sparse FIR decision - 2026-08-02

## Decision

**Stop weight-energy-only sparse compilation.** Neither E90 nor E95 passes the
frozen joint ranking-safety and sparse-utility gate. Do not evaluate tests or
train new models for this branch.

Authorize a small activation-aware sparse-refit pilot because the failure mode
is now precise: energy identifies a useful support on ML-1M, but coefficient
deletion does not preserve final-layer outputs on LastFM even at 95% retained
impulse energy.

## Frozen result

Mean strict-mask validation NDCG@10 delta and mean retained taps:

| dataset | E90 delta | E90 K | E95 delta | E95 K |
|---|---:|---:|---:|---:|
| ML-1M | **+0.0074748929** | 9.4 | **+0.0042106568** | 22.4 |
| Beauty | -0.0000373578 | 24.8 | -0.0000399995 | 36.6 |
| Toys and Games | -0.0000092463 | 24.8 | +0.0000311582 | 36.2 |
| LastFM | **-0.0005577179** | 19.2 | **-0.0005661093** | 31.0 |

E90 has macro delta `+0.0017176427`, mean K `19.55`, and maximum K `27`.
E95 has macro delta `+0.0009089265`, mean K `31.55`, and maximum K `37`.
Both retain the ML-1M effect, but both fail panel safety on LastFM and have only
15/20 bootstrap lower bounds above the frozen noninferiority margin. E90 also
exceeds its maximum-support bound; E95 exceeds both support bounds.

## Implication

Increasing retained coefficient energy from 90% to 95% does not rescue LastFM.
The missing quantity is therefore not simply more weight energy. A plausible
next mechanism is input covariance: low-energy taps can matter if they align
with common hidden-state directions, while retained taps can be refit to
compensate for deleted ones on the actual sequence distribution.

The bounded next pilot may use unlabeled training-prefix activations to select
a shared lag support and solve channel-wise ridge regressions that reconstruct
the dense final-position filter output. It must be compared with unrefit K=8
and must rescue LastFM without erasing ML-1M's gain before any expansion.

This is not a broad novelty claim. Calibration-based least-squares compensation
is occupied by methods such as GRAIL and output-error pruning. The research gap
is the recommendation-specific combination of final-position temporal
reconstruction, shared-lag FIR support, and exact direct execution.

## Provenance

- Preregistration SHA-256:
  `4adaaee4e1c2a91f0320a1d970b39a692b0877e4aa823c02dc797348af44de52`.
- Compact record: `energy_adaptive_sparse_summary.json`.
- All results are validation-only; no new test split was accessed.

