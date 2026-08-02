# Cross-dataset sparse-support transfer preregistration V1

Date frozen: 2026-08-02

## Question

Does post-training sparse impulse support improve a learned late spectral
filter beyond ML-1M, and does the ML-1M boundary support transfer without
dataset-specific support selection?

No projection outcome on the datasets below may be inspected before this file
is hashed.

## Frozen panel

- Datasets: `Beauty`, `Toys_and_Games`, and `LastFM`.
- Seeds: `42, 43, 44, 45, 46` for each dataset.
- Source models: the existing selected `LADDER_<dataset>_full_s*.pt`
  checkpoints.
- Split: full-catalog validation only.
- Primary masking: strict negative infinity for seen items.
- Sequence length: `50`.
- No training, fine-tuning, calibration, support search, or test access.

ML-1M is not included in any transfer aggregate. All hyperparameters and fixed
supports below are inherited from the sealed ML-1M experiment.

## Frozen cells

Only the final spectral filter changes. Every retained impulse coefficient
keeps its original channel-specific value.

### F: original full filter

The unmodified source checkpoint.

### A: adaptive aggregate top-8

Inverse-rFFT every channel of the final filter. Score lag `t` by summed squared
coefficient magnitude across channels, retain the eight highest-energy lags,
zero all remaining lags in all channels, and rFFT back. Stable descending sort
and increasing index order break exact ties.

### B: fixed boundary-8

Retain indices `{0,1,2,3,4,5,48,49}` in every channel and zero all others.
This support is transferred unchanged from the sealed ML-1M weight analysis.

### R: fixed recent-8

Retain indices `{0,1,2,3,4,5,6,7}` in every channel and zero all others.

## Integrity checks

Record all input/output SHA-256 values, selected indices, retained impulse
energy, float32 storage error, and excluded-tap residual. Abort if the expected
final spectral filter is absent. Non-filter parameters must be inherited
unchanged.

## Evaluation and uncertainty

Report full-catalog validation HR and NDCG at 5, 10, and 20 for all four cells.
For `A-F`, `B-F`, `R-F`, `A-B`, and `B-R`, use a deterministic 10,000-resample
paired-user bootstrap with seed `314159`.

Primary endpoint: strict-mask `NDCG@10`. Aggregate results first within each
dataset over five seeds, then macro-average the three dataset means. Also
report the number of positive seed-level effects out of 15. No dataset or seed
may be excluded based on its outcome.

## Frozen decision rules

1. **Adaptive transfer:** passes if `A-F` has positive mean on at least 2/3
   datasets, macro mean `>= +0.0010`, and at least 10/15 seed effects are
   positive.
2. **Strong adaptive transfer:** passes if all three dataset means are
   positive, every dataset has at least 4/5 positive seeds, and at least two
   dataset means are `>= +0.0020`.
3. **Fixed-boundary transfer:** passes if `B-F` meets the adaptive-transfer
   rule and B is within `0.0005` macro NDCG@10 of A (`A-B <= +0.0005`).
4. **Boundary-position value:** passes if `B-R` is positive on at least 2/3
   datasets, macro mean `>= +0.0005`, and at least 10/15 seed effects are
   positive.
5. **Material dataset failure:** declared for an arm if any dataset has mean
   delta `<= -0.0020` and at least 4/5 seeds are negative.

Values between thresholds are inconclusive. Passing rule 1 establishes a
cross-dataset feasibility result, not Tier-A sufficiency. Rule 2 or 3 plus a
material direct-execution speedup is required before authorizing fresh large-
scale training. All test splits remain sealed regardless of the outcome of
this validation panel.

