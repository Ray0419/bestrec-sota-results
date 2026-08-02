# Analysis plan: FMLP-Rec causalization pilot v1

Frozen on 2026-08-02 before the first causalized FMLP-Rec model was trained.
This is an exploratory, outcome-visible method screen and not a confirmatory
experiment.

## Question

Can the published-form bidirectional circular frequency filter in FMLP-Rec be
replaced by a strictly left-causal K=16 depthwise FIR without materially losing
ML-1M validation ranking?

The motivation is correctness under the all-position next-item objective:
future inputs can change earlier outputs of the circular FFT mixer, whereas a
left-padded causal FIR is prefix invariant. Causal convolution itself is prior
art; this screen tests the specific correctness/accuracy trade-off in the
FMLP-Rec filter position.

## Frozen implementation and protocol

- Use the existing official-suite FMLP-Rec harness and ML-1M preparation.
- Replace both frequency-filter layers with per-channel K=16 causal FIR layers.
- Each causal filter is initialized to a current-position delta and used inside
  the existing residual and layer-normalization path.
- Seed 42, hidden size 64, two layers, maximum sequence length 50, batch size
  256, learning rate 0.001, dropout 0.5, no weight decay.
- Up to 200 epochs, patience 10, checkpoint selected only by validation
  NDCG@20.
- Use the no-test trainer. No test code path is allowed.
- Before training, the frozen prefix-perturbation test must show a nonzero past
  change for `full` and no past change above `1e-6` for `causal_full` and
  `causal_shared`.

## Frozen reference and decision

Existing full-filter seed-42 validation NDCG@10 is `0.1224280798` under the same
seen-item masking protocol.

- Support a useful causalization pilot if causal-full validation NDCG@10 is at
  least `0.1204280798` (within 0.002 of full).
- Refute the pilot if it is below `0.1174280798` (more than 0.005 below full).
- Otherwise call it inconclusive.

Do not evaluate test or launch additional seeds from this pilot alone. A useful
pilot still requires a novelty decision because causal convolution and compact
sequence mixers are established prior art.

