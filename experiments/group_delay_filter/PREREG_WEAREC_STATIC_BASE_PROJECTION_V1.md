# Preregistration: WEARec static-base projection v1

Frozen on 2026-08-02 after label-free inspection of the official WEARec
checkpoint tensors and before evaluating any projected checkpoint. The
official checkpoint logs and their baseline validation/test metrics are
already public and outcome-visible. This is therefore a retrospective
cross-architecture feasibility test, not independent confirmation.

## Research question

Does the depth-gated channel-sharing endpoint found in FMLP-Rec extend to the
static part of WEARec's adaptive frequency filter without removing WEARec's
input-dependent modulation?

## Frozen source and checkpoints

- Official repository: `https://github.com/xhy963319431/WEARec.git`.
- Revision: `2087335339b1ead87da6e066ce14e2d33880a95e`.
- `src/model/wearec.py` SHA-256:
  `da12a6cc4c7da12eb0045b9f20ee158a757e7fe00ae5de7b0acd55e10f298e4f`.
- `src/model/_abstract_model.py` SHA-256:
  `9d8539a1edfb388ce28079ff9e7b5d147d5c2117eba652649afdb31ef9e2e824`.
- `src/model/_modules.py` SHA-256:
  `65f75781f02dcbac835813b4769d5d23194e7746c8a81d9e52672935e53141b9`.
- `src/dataset.py` SHA-256:
  `4395e9f7087674c00bfa09ea8a03773e70ab5b6f075ea93406008a57bb2133b7`.

| dataset | heads | alpha | data SHA-256 | checkpoint SHA-256 |
|---|---:|---:|---|---|
| Beauty | 8 | 0.2 | `226cce9c3105299ca0db9615d7d3fb32b3175e90da43100ae352599f0f0107b8` | `be46edc77f2833ca882cd113b99dbc62605cb43cc9b13c2b9764b6769c25f1cc` |
| LastFM | 2 | 0.3 | `9ded486adb5b0fe9dc761950afa0a9a05e93ff018992e0c52bf11afec529f802` | `0eedb6ac9203677400f3fa0946e06a4d3d9c9356afdb7d0b20a9e113b4d00ca8` |
| ML-1M | 2 | 0.3 | `c3fa8abcfcdc8824e6b54fe5fdb50c5fac8316e7ef2bc00973f8dd69ba76163d` | `4e26ef8a3efb8852dd61052de6a8649eb170c45869ec844d8e02fbe1c4ca2f69` |
| Sports_and_Outdoors | 4 | 0.3 | `2a095e0648872beb9982408958290f5d655db5be2911c3756b5446de9f0b8de2` | `d5bd261ff5c973dbf0ac57e480545484da1f09e40ebef9b550ffd10b3a74a387` |

## Frozen intervention

For the final encoder block only, treat each `base_filter` and `base_bias` as
a frequency-by-head matrix. Canonicalize it by transposing the stored
`heads x frequencies x 1` tensor to `frequencies x heads`.

For each matrix, compute rank-1 retained energy `rho` and the absolute cosine
between its dominant right singular vector and the uniform head vector. If
`rho >= 0.905` and uniform cosine `>= 0.97`, replace every head column by the
column mean. Otherwise leave the matrix untouched. Do not alter the wavelet
detail weights, adaptive MLP, embeddings, feed-forward network, or earlier
block. Both final static matrices must select on all four checkpoints for the
cross-architecture test to proceed.

This is an orthogonal projection onto a head-shared static frequency response.
It deliberately preserves WEARec's input-dependent per-head scale and bias
outputs, so the intervention does not assert that the complete adaptive filter
is channel-independent.

## Frozen evaluation

- Split: validation only. Do not evaluate the projected model on test.
- Full catalog with padding item zero and every training-history item masked
  to negative infinity.
- Metrics: paired per-user HR and NDCG at 5, 10, and 20.
- Primary endpoint: projected minus baseline validation NDCG@10.
- Uncertainty: deterministic 10,000-resample paired-user bootstrap, seed
  `314159`.
- Use official maximum length 50, hidden size 64, two layers, and the
  checkpoint-specific head count and alpha above.

## Frozen feasibility decision

- **Support:** all four NDCG@10 deltas are at least `-0.0005`, at least three
  are nonnegative, and their unweighted mean is nonnegative.
- **Compression-only support:** all four deltas are at least `-0.0005`, but
  the stronger support rule fails.
- **Fail:** any dataset delta is below `-0.0005`.

This experiment can establish architecture breadth for a static-base sharing
endpoint. It cannot establish a state-of-the-art improvement, whole-model
efficiency, or prospective evidence.
