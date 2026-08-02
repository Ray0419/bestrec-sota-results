# KuaiRec prospective decision — 2026-08-02

## Decision

**Completed double abstention. No KuaiRec test metric was accessed.**

The preregistered seed-47 FMLP-Rec run stopped at epoch 42 after ten
non-improvements. Validation selected epoch 32 by NDCG@20. Its canonical
temporal-filter spectra did not activate either prospective intervention.

| layer | rank-1 retained energy | dominant channel/uniform cosine | decision |
|---|---:|---:|---|
| early | 0.803890 | 0.927265 | unchanged |
| final | 0.859988 | 0.960661 | unchanged |

- Depth-conditioned EGSP required final-layer energy at least `0.905`.
- The secondary channel-shared rule additionally required dominant-channel
  cosine at least `0.97`.
- Both final-layer statistics failed their frozen gates. No projected model was
  evaluated on test.

## Audit trail

- Original preregistration: `PREREG_DEPTH_EGSP_KUAIREC_V1.md`
- Secondary preregistration: `PREREG_CHANNEL_SHARED_KUAIREC_SECONDARY_V1.md`
- Secondary preregistration SHA-256:
  `d7ec854c5b0261de6a4c7d5458f0c7b014d3ddcac76a7f5e1726616247e850e7`
- Prepared sequence data SHA-256:
  `9888dd1a1068a369accff58323767ede5a2b3b893e7eaac0419361d693597228`
- Validation-selected checkpoint SHA-256:
  `6a083e71229a9247b25ee4d1675e9b51161a98aee48d39a1fa2987119df5b730`
- No-test artifact SHA-256:
  `6131d58d665198c6b1d345d5e04dfc169d324670d107770900bfe0b128ae75e2`
- Training log SHA-256:
  `ccea404da45ea7ee4c3c553f0175fe50e3797e8121db87dcca926ee410564f99`
- Best validation epoch: 32
- Best validation NDCG@10: `0.105563`
- Best validation NDCG@20: `0.123078`
- Test access: none

## Interpretation

KuaiRec is denser and has much longer raw histories than MovieLens, yet it does
not exhibit the late-filter collapse seen on ML-1M. Dataset density, user count,
and sequence length are therefore not sufficient activation explanations. The
result narrows the open question to the data-generating process or target
structure that makes channel-specific temporal responses redundant.

The retrospective ML-1M channel-shared result remains useful as a mechanism and
algorithmic lead, but this abstention blocks any broad cross-domain or Tier-A
performance claim. A next experiment should vary temporal predictability or
repeat-transition structure directly instead of adding indiscriminate datasets.
