# Analysis plan: ML-1M sparse-FIR compiler feasibility v1

Frozen on 2026-08-02 before constructing or evaluating a sparse-tap spectral
checkpoint. This is an outcome-known exploratory feasibility test, not
confirmatory evidence.

## Motivation and question

The five existing post-training channel-shared ML-1M filters improve validation
ranking. After inverse real FFT, their final responses place approximately
`95.5%-95.9%` of energy in the eight largest taps and `98.7%-99.0%` in the
sixteen largest taps. Can that learned spectral response be compiled into a
sparse real FIR that retains the accuracy gain and permits direct last-item
inference without a final FFT?

## Frozen intervention

Start from each existing seed-42--46 channel-mean projected checkpoint. For its
final shared spectrum `H`, compute `h = irfft(H, n=50)`. Construct two nested
label-free variants by retaining the `K` largest-absolute taps of `h`, setting
the remainder to zero, and transforming back with `rfft`:

```text
K in {8, 16}.
```

Break exact magnitude ties by the lower tap index. Do not fine-tune. Evaluate
full-catalog validation only with strict negative-infinity seen-item masking.
The comparison of interest is sparse FIR minus the ordinary channel-shared
projection, paired by seed. Test access is prohibited.

Record retained impulse energy and tap indices. Verify numerically that the
stored spectrum is the real FFT of the sparse impulse response. Do not add a
tap budget after seeing ranking outcomes.

## Frozen interpretation

- **K=8 compiler support:** mean validation NDCG@10 loss versus ordinary
  sharing is no worse than `-0.0005`, at least four of five seeds are no worse
  than `-0.001`, and the compiled model still exceeds the original full model
  by at least `0.002` on the five-seed mean.
- **K=16 compiler support:** the corresponding bounds are `-0.00025`, four of
  five no worse than `-0.0005`, and at least `+0.002` versus full.
- If only K=16 passes, retain K=16 as the sole implementation candidate.
- If neither passes, close magnitude-only sparse-tap compilation; low-energy
  remote taps are functionally important in this setting, as already observed
  for long-sequence WEARec.

Only a passing arm authorizes an idle-device implementation benchmark of the
final mixer. That benchmark must compare encoder outputs for numerical parity
and report encoder-only and end-to-end batch latency; operation counts alone
do not license an efficiency claim.

## Novelty boundary

The exact conversion of a trained frequency-domain sequential recommender into
a sparse direct last-item FIR was not found in the targeted search. Broad
novelty is unavailable: sparse filter pruning is established, Flash Inference
accelerates convolutional sequence models, AIRE-Prune scores states by impulse
response energy, and the local WEARec ISGP experiment already tested
energy-based impulse-support pruning of a dynamic generator. This pilot can
establish usefulness, but cannot raise novelty confidence to 95% by itself.
