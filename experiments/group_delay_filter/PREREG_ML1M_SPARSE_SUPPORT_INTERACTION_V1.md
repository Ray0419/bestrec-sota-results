# ML-1M sparse-support interaction preregistration V1

Date frozen: 2026-08-02

## Question

Does the validation gain from the top-8 consensus-sparse FIR require channel
consensus before temporal pruning, and is its learned support more useful than
a fixed recency window?

The already observed cells are the original full late filter, its channel-mean
projection, and the channel-mean projection followed by adaptive top-8 impulse
pruning. No result from the new controls below may be inspected before this
file is hashed.

## Frozen data and checkpoints

- Dataset: `ML-1M`.
- Split: full-catalog validation only with strict negative-infinity seen-item
  masking. Legacy zero-mask metrics are recorded but cannot drive a decision.
- Seeds: `42, 43, 44, 45, 46`.
- Sequence length: `50`.
- Original checkpoints: the five selected `LADDER_ML-1M_full_s*.pt` models.
- Shared checkpoints: their existing final-layer channel-mean projections.
- Adaptive checkpoints: their existing shared, top-8 compiled checkpoints.
- No training, fine-tuning, calibration, support search, or test access.

Only the collapsed final spectral filter may be changed. Embeddings, the first
filter block, normalization, feed-forward layers, and scoring remain byte-for-
byte inherited from the input checkpoint.

## New intervention cells

### T: channel-specific aggregate top-8

Inverse-rFFT every channel of the original final filter. Score impulse lag
`t` by the sum of squared coefficients across channels, retain the eight lags
with largest aggregate energy, zero all other coefficients in every channel,
and rFFT back. Channel-specific coefficient values are preserved at retained
lags. Stable descending sort and increasing index order break exact ties.

This is temporal pruning without channel consensus.

### R: shared fixed recent-8

Starting from the channel-mean checkpoint, retain fixed impulse indices
`{0,1,2,3,4,5,6,7}` and zero all others.

### B: shared fixed boundary-8

Starting from the channel-mean checkpoint, retain fixed impulse indices
`{0,1,2,3,4,5,48,49}` and zero all others. This support is frozen from the
cross-seed support pattern of the learned filters, before evaluating either
fixed-support control; it is therefore a mechanistic control, not an
independent discovery result.

The existing adaptive cell A retains the independently selected eight largest
absolute coefficients of each shared impulse response.

## Integrity checks

For every compiled checkpoint, record source and output SHA-256 values, selected
indices, retained impulse energy, excluded-tap residual after float32 storage,
and maximum storage quantization error. Fixed-support inputs must be channel-
shared to tolerance `1e-7`. Abort rather than silently modifying an unexpected
checkpoint.

## Metrics and uncertainty

Primary metric: strict-mask validation `NDCG@10`.

Report HR and NDCG at 5, 10, and 20 for all six cells: original full F, pruned
full T, shared S, adaptive shared A, recent shared R, and boundary shared B.
Use a deterministic 10,000-resample paired-user bootstrap with seed `314159`
for each pairwise contrast and for the factorial interaction

`I = (A - S) - (T - F)`.

Aggregate decisions use the unweighted mean across the five training seeds and
the number of seed-level signs. Bootstrap intervals are descriptive evidence;
no seed or arm may be removed based on its outcome.

## Frozen decision rules

1. **Independent temporal-pruning effect:** supported if mean `T-F >= +0.0020`
   NDCG@10 and at least 4/5 seeds are positive.
2. **Consensus-pruning interaction:** supported if the already frozen adaptive
   effect remains `A-S >= +0.0020`, mean `T-F <= +0.0005`, mean interaction
   `I >= +0.0015`, at least 4/5 seed interactions are positive, and at least
   3/5 interaction bootstrap lower bounds exceed zero.
3. **Adaptive-support value:** supported if A exceeds both R and B by at least
   `+0.0005` mean NDCG@10 and is higher in at least 4/5 seeds for each contrast.
4. **Fixed boundary law:** supported if `B-S > 0`, at least 4/5 seeds are
   positive, and `A-B <= +0.0005` in mean. Because B was selected from observed
   weight supports, this may motivate a prospective rule but is not treated as
   independent validation.
5. **Old-history contribution:** supported if B exceeds R by at least `+0.0005`
   mean and in at least 4/5 seeds.

Values between thresholds are inconclusive. A failed mechanistic rule does not
erase the already frozen adaptive compiler result, but it narrows the claim.
No ML-1M test evaluation is authorized until all new artifacts and the decision
memo are written and hashed.

