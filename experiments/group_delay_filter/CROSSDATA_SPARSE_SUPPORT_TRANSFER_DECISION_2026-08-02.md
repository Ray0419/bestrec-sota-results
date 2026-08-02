# Cross-dataset sparse-support transfer decision - 2026-08-02

## Decision

**Reject universal fixed-K=8 sparse compilation.** The ML-1M gain does not
transfer at a publishable magnitude to Beauty, Toys and Games, or LastFM.
Do not access test splits and do not scale fixed-K training.

Pursue one bounded follow-up: replace the universal tap count with a validation-
free impulse-energy retention rule, then require both cross-dataset
noninferiority and a useful sparse execution budget.

## Frozen transfer result

Mean strict-mask validation NDCG@10 delta over five seeds:

| dataset | adaptive top-8 | fixed boundary-8 | fixed recent-8 |
|---|---:|---:|---:|
| Beauty | +0.0001490932 | +0.0002672070 | +0.0001472496 |
| Toys and Games | +0.0000459011 | +0.0001615176 | +0.0000785715 |
| LastFM | **-0.0012531990** | **-0.0015168457** | **-0.0013885919** |
| dataset macro | **-0.0003527349** | **-0.0003627070** | **-0.0003875903** |

Adaptive top-8 is positive in 7/15 seeds. Fixed boundary-8 is positive in
10/15 because it is consistently but very slightly positive on Beauty and
Toys; it is negative in all five LastFM seeds. All four preregistered transfer
rules fail. No arm crosses the separately frozen material-failure threshold,
but none supports a general method claim.

## Mechanistic clue

The fraction of channel-specific impulse energy retained by adaptive K=8 is:

| dataset | mean retained energy | mean K=8 delta |
|---|---:|---:|
| ML-1M | 0.8900 | +0.0081634781 |
| Beauty | 0.7943 | +0.0001490932 |
| Toys and Games | 0.8032 | +0.0000459011 |
| LastFM | 0.8067 | -0.0012531990 |

Across all 20 checkpoints, retained energy and delta have Pearson correlation
`0.8822` and Spearman correlation `0.5459`. A retrospective `0.88` gate selects
only the five ML-1M checkpoints, all beneficial, while the 15 abstained
checkpoints have negative macro delta.

This gate is not confirmed: seeds are nested within only four datasets and the
threshold was chosen after observing outcomes. It motivates a prospective
dataset-level test later. Its immediate use is to replace fixed K with the
smallest K that preserves a frozen energy fraction.

## Research implication

The broad claim "weak impulse taps are universally harmful" is false. The
defensible emerging claim is conditional: late filters vary in intrinsic
impulse compressibility, and compilation should expose a controlled
accuracy-efficiency frontier rather than impose a single support size.

This is potentially useful for an efficiency paper only if an energy-adaptive
compiler can satisfy three requirements together:

1. no material ranking loss across the current heterogeneous panel;
2. a substantially sparse support on every dataset; and
3. numerical parity plus measured speedup for direct final-output execution.

Generic energy-based pruning remains a close prior, so even a successful
follow-up needs a recommendation-specific deployment result and prospective
dataset confirmation before novelty/value confidence can approach 95%.

## Provenance

- Preregistration SHA-256:
  `78a7c066c8cf886767af53cb7ead259379ccf037d994a56425e5d3ecb5d087e0`.
- Compact transfer record: `crossdata_sparse_support_transfer_summary.json`.
- Exploratory mechanism record: `sparse_compressibility_gate_analysis.json`.
- All results are validation-only; no new test split was accessed.

