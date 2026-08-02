# Preregistration: channel-shared KuaiRec secondary pilot v1

Frozen on 2026-08-02 while the seed-47 KuaiRec training run was still in
progress, before inspecting any KuaiRec checkpoint spectrum and before any
KuaiRec test evaluation. Validation learning-curve values through epoch 9 had
been observed. This is a prospective secondary mechanism test, not an
independent confirmation of the training protocol.

## Hypothesis

When the final learned temporal filter has both dominant rank-1 energy and a
nearly uniform dominant channel direction, channel-specific residuals are
dispensable. Replacing the full channel bank by one shared temporal response
should be non-inferior and may improve generalization.

## Frozen input

- Dataset and training checkpoint: the validation-selected seed-47 KuaiRec
  FMLP-Rec checkpoint governed by `PREREG_DEPTH_EGSP_KUAIREC_V1.md`.
- No new training or checkpoint selection is allowed for this secondary test.
- Canonicalize the spectral filter by constraining DC and Nyquist responses to
  be real before all calculations.

## Frozen gate and intervention

For only the final temporal-filter matrix `W` with shape frequency by channel:

1. Compute `rho1 = sigma1(W)^2 / sum_j sigma_j(W)^2`.
2. Compute `c = |v1^H 1/sqrt(C)|`, where `v1` is the dominant right singular
   vector and `C` is the number of channels.
3. Activate only if `rho1 >= 0.905` and `c >= 0.97`.
4. On activation, replace `W` by its orthogonal channel-shared projection:
   every column becomes the mean of the original columns. Leave every other
   parameter, including the early temporal filter, byte-identical.

If either gate fails, record an abstention and do not evaluate this variant on
the KuaiRec test split.

## Frozen evaluation and decision

On activation, hash the baseline and projected checkpoints before evaluation.
Evaluate paired full-catalog next-item ranking on the untouched test split with
seen items masked by negative infinity. The primary metric is NDCG@10; report
HR and NDCG at 5, 10, and 20, plus a 10,000-resample paired-user bootstrap
interval.

- Pass: projected minus baseline NDCG@10 is nonnegative.
- Fail: delta is below `-0.0005`.
- Otherwise: inconclusive.

The pass/fail rule concerns feasibility only. A pass does not authorize a
Tier-A claim without fresh-seed replication and another independent dataset.
