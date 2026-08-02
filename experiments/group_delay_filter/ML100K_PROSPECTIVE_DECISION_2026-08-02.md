# Prospective EGSP ML-100K decision — 2026-08-02

## Outcome

**Completed mechanism abstention. No test metric was accessed.**

The preregistered seed-47 FMLP-Rec run early-stopped after zero-based epoch 53.
The validation-selected checkpoint is epoch 43 with validation NDCG@10
`0.103584` and checkpoint-selection NDCG@20 `0.131742`.

| layer | rank-1 retained energy | frozen threshold | selected |
|---|---:|---:|---:|
| block 0 spectral filter | 0.837085 | 0.905 | no |
| block 1 spectral filter | 0.832779 | 0.905 | no |

The sequential decision rule therefore prohibits projection and test
evaluation. This is a completed abstention, not a performance pass or fail.

## Integrity record

- Preregistration SHA-256:
  `c10aecfe9a51cfa3d386fbfb6c8c461bb85d77a0b0d95408c03e8398e128a526`
- Sequence file SHA-256:
  `32bec7e018ff9c50a5d116186a952cfdc8237b54e31d8f853255e5f1e9e8dbd7`
- Selected checkpoint SHA-256:
  `9214471a0cdaa3cf04287c41051da8b27393d74ebba323c5522097d1c78b293b`
- Training log SHA-256:
  `a26ad0090e96bd63f65521de644aadfcd14f4331d66ca02859854a82a5264d62`
- Test access recorded by the no-test runner: `none`.

Machine-readable provenance, full singular values, source-file hashes, and the
validation record are in
`prospective_ml100k/EGSP_ML100K_full_s47.no_test.json`.
The runner's original spectrum record included otherwise inert imaginary DC and
Nyquist coefficients; `ml100k_canonical_spectra.json` corrects that diagnostic
to match the established projector. The correction is below `0.0004` energy and
does not change abstention.

## Interpretation

After the fixed 5-core transform, ML-100K has 99,287 interactions, mean user
sequence length 105.3, and 7.80% matrix density. It is denser than the ML-1M
sequence matrix, yet neither late nor early filter approaches the activation
threshold. The current evidence therefore rejects **matrix density alone** as
the explanation for ML-1M rank collapse.

The remaining credible mechanism is a data-scale or independent-trajectory
effect: ML-1M supplies roughly six times as many users and ten times as many
interactions. That hypothesis now requires a controlled nested-user scaling
study before any larger-dataset performance campaign is justified.
