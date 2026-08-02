# Activation-aware sparse FIR refit pilot preregistration V1

Date frozen: 2026-08-02

## Question

Can unlabeled calibration activations compensate an eight-lag final spectral
filter so that direct sparse execution preserves a hard dataset while retaining
the regularization gain on a compressible dataset?

This is a two-checkpoint feasibility pilot, not independent confirmation. No
refitted checkpoint or ranking outcome may be inspected before this file is
hashed.

## Frozen checkpoints and data

- Hard case: `LADDER_LastFM_full_s42.pt`.
- Positive control: `LADDER_ML-1M_full_s42.pt`.
- Calibration source: at most 4,096 training prefixes, selected at evenly
  spaced deterministic indices over each expanded training-prefix dataset.
- Calibration uses input item sequences only; answers, negatives, validation
  data, and test data are not used.
- Ranking evaluation: full-catalog validation only with strict negative-
  infinity seen-item masking.
- No gradient training or task labels.

## Reconstruction target

Run the original model in evaluation mode and capture the hidden sequence that
enters the final spectral filter. For each calibration sequence and channel,
the target is the original dense filter's pre-residual, pre-normalization
output at position 49.

The circular lag design for coefficient `t` is hidden position
`(49 - t) mod 50`. All sparse filters preserve channel-specific coefficients
and share one lag support across channels.

## Frozen arms

### M8-R: magnitude support plus refit

Select the eight lags with largest aggregate impulse energy over channels.
Holding this support fixed, solve an independent ridge least-squares problem
for each channel to reconstruct the dense target.

### G8-R: greedy activation support plus refit

Starting with an empty shared support, repeat eight times:

1. compute each remaining lag's aggregate normalized squared correlation with
   the current channel-wise residual;
2. select the largest score with increasing-index tie breaking;
3. refit all selected coefficients channel-wise by ridge least squares; and
4. update the residual.

This is a simultaneous group-OMP-style output reconstruction rule.

For both arms, ridge strength is

`lambda_c = 1e-4 * trace(X_c^T X_c) / K`

for channel `c` and current support size K. No intercept is fitted. The sparse
impulse is rFFT-compiled back into the existing checkpoint for ordinary model
evaluation.

## Integrity and diagnostics

Record source/output hashes, calibration indices hash, support, coefficient
norm, dense target energy, unrefit support MSE, refit MSE, relative MSE, and
float32 checkpoint reconstruction error. Abort on a missing or unexpected
final spectral filter.

## Frozen gates

1. **Reconstruction feasibility:** a refitted arm must reduce calibration MSE
   by at least 75% relative to zeroing the same support without refit.
2. **LastFM rescue:** strict validation NDCG@10 delta versus original must be
   `>= -0.0005`, with paired bootstrap lower bound above `-0.0015`.
3. **ML-1M preservation:** strict validation NDCG@10 delta versus original must
   be nonnegative.
4. **Expansion:** expand one arm to all four datasets and five seeds only if it
   passes gates 1-3. If both pass, choose lower calibration relative MSE; ties
   within 5% choose M8-R as the simpler rule.

Use 10,000 paired-user bootstrap resamples with seed `314159`. Values between
thresholds are inconclusive. No test access or large training is authorized by
this pilot.

