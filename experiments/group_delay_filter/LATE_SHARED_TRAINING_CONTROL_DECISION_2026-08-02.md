# Final-shared training control decision - 2026-08-02

## Decision: supports optimization/deployment reversal

The validation-selected `late_shared` model reaches validation NDCG@10
`0.1171600764` at epoch 42. Under the frozen rule, support required a value no
greater than `0.1204280798`; the pilot therefore supports the reversal by a
clear margin.

| seed-42 model | validation NDCG@10 | difference from full |
|---|---:|---:|
| full filter trained normally | 0.1224280798 | 0 |
| final layer shared throughout training | 0.1171600764 | -0.0052680034 |
| full training, then final channel sharing | 0.1311392350 | +0.0087111552 |

The post-training shared checkpoint exceeds the matched from-scratch
late-shared control by `0.0139791586`. Test was not evaluated.

## Interpretation

This is direct evidence that the late per-channel degrees of freedom are useful
as an optimization scaffold but need not be retained in the deployed solution.
It rules out the simple explanation that the shared architecture is just a
better static regularizer on ML-1M. It does not establish that channel
deviations are pure noise, prove a symmetry theorem, or show cross-dataset
generality.

The result strengthens the narrow optimization/deployment-rank-gap finding. It
does not independently authorize five more training seeds or a large campaign:
generic post-training sharing, gradual tying, structural reparameterization,
and low-rank compression remain close prior art. The frozen interpolation,
norm-matched, and power-preserving controls must still identify what the
projection removes.

## Integrity and provenance

- Preregistration SHA-256:
  `8b2c5bcbee08dae4ce007e2ae34b6258289999ed773c1c2667c607c009fa15ca`.
- Governed artifact:
  `prospective_late_shared/LATE_SHARED_ML-1M_s42.no_test.json`.
- Checkpoint SHA-256:
  `57145c423af42730845918c7a1a18e9290046638305fad26c8b6de6d5f829582`.
- Training script SHA-256 at launch:
  `3bfc652b7baf4028bd0454e2d69a1f759ed453708a0f07384a4db403ffbc7b96`.
- Best epoch: 42, selected only by validation NDCG@20; last epoch: 52.
- The original post-training finalization failed after checkpoint selection and
  validation because an in-place complex-tensor canonicalization aliased its
  real view. The checkpoint and log were intact. A patched finalize-only path
  reloaded that exact checkpoint, repeated validation, and wrote the artifact
  without training or test access. Both launch and finalizer script hashes and
  the reconstruction flag are recorded in the JSON.
