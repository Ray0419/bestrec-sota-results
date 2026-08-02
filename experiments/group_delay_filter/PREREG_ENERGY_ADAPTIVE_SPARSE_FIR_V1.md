# Energy-adaptive sparse FIR feasibility preregistration V1

Date frozen: 2026-08-02

## Question

Can a label-free impulse-energy rule replace the failed universal K=8 budget
with a sparse late-filter compiler that is noninferior across heterogeneous
recommendation datasets while retaining the ML-1M regularization benefit?

The current panel has already been used to diagnose fixed-K failure. This is a
calibration/feasibility experiment, not independent confirmation. No E90 or
E95 ranking result may be inspected before this file is hashed.

## Frozen panel

- Datasets: `ML-1M`, `Beauty`, `Toys_and_Games`, and `LastFM`.
- Seeds: `42, 43, 44, 45, 46` for every dataset.
- Source checkpoints: existing selected `LADDER_<dataset>_full_s*.pt` models.
- Split: full-catalog validation only, strict negative-infinity seen-item
  masking for all decisions.
- No training, fine-tuning, calibration labels, support search, or test access.

## Compiler

For the final spectral filter only:

1. inverse-rFFT every channel to a length-50 impulse response;
2. score each lag by summed squared coefficient magnitude over channels;
3. order lags by descending aggregate energy with stable increasing-index tie
   breaking;
4. retain the shortest prefix whose cumulative energy reaches the frozen
   fraction `rho` of total impulse energy;
5. preserve all selected channel-specific coefficients, set all other lags to
   zero, and rFFT back.

Two frozen cells are evaluated:

- **E90:** `rho = 0.90`;
- **E95:** `rho = 0.95`.

K is chosen separately from each checkpoint's weights and is never selected
from ranking outcomes. Record actual K, retained energy, support indices,
source/output hashes, float32 storage error, and excluded-tap residual.

## Evaluation

Report HR and NDCG at 5, 10, and 20 for original F, E90, and E95. Primary
endpoint: strict-mask validation NDCG@10. For E90-F and E95-F, run a
deterministic 10,000-resample paired-user bootstrap with seed `314159` on the
primary endpoint.

Aggregate first over five seeds within each dataset, then macro-average the
four dataset means. Report mean, maximum, and per-checkpoint K. No seed or
dataset may be excluded after outcomes are observed.

## Frozen decision rules

### Ranking safety

An energy level is **panel-safe** if all conditions hold:

1. every dataset mean delta is `>= -0.0005` NDCG@10;
2. four-dataset macro delta is `>= -0.0002`;
3. no seed point delta is `<= -0.0020`; and
4. at least 16/20 paired bootstrap lower bounds exceed `-0.0010`.

### Sparse utility

- E90 is **usefully sparse** if mean K is at most 20 and maximum K is at most
  25.
- E95 is **usefully sparse** if mean K is at most 25 and maximum K is at most
  32.

### ML-1M regularization retention

- E90 retains the effect if mean ML-1M delta is at least `+0.0020` and at
  least 4/5 seeds are positive.
- E95 retains the effect if mean ML-1M delta is nonnegative and at least 3/5
  seeds are positive.

### Selection

Select E90 for direct compilation only if it is panel-safe, usefully sparse,
and retains the ML-1M effect. Otherwise select E95 only if it passes its three
corresponding rules. If neither passes, stop the energy-adaptive direction.

Passing is not independent evidence and does not authorize test access or a
large training campaign. It authorizes only exact direct-output implementation,
idle-device benchmarking, and a prospectively trained fresh-dataset gate.

