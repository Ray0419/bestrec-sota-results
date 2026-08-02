# Analysis plan: final-shared training control v1

Frozen on 2026-08-02 before implementing `late_shared` or training its first
model. This is a retrospective, outcome-known mechanism control, not a
confirmatory experiment.

## Question

Does final-layer-only channel sharing fail when imposed throughout training,
even though imposing the same constraint after full-model training improves
ML-1M validation ranking?

The existing trained-shared comparator ties both temporal-filter layers and is
therefore not an exact optimization-path control for the final-only post-hoc
intervention.

## Frozen implementation

- Add FMLP-Rec mode `late_shared`: layer 0 remains the standard full
  frequency-by-channel filter; layer 1 uses one frequency response shared by
  all channels.
- Preserve the existing encoder's cloned-block initialization for all common
  parameters. Initialize the final shared response from the first channel of
  the cloned full response, preserving the original `N(0, 0.02)` marginal.
- Do not change behavior or initialization for any existing filter mode.
- Training data and model: existing ML-1M preparation and FMLP-Rec source.
- Pilot seed: 42.
- Hidden size 64, two layers, maximum sequence length 50, batch size 256,
  learning rate 0.001, dropout 0.5, no weight decay.
- Up to 200 epochs, patience 10, checkpoint selected only by validation
  NDCG@20.
- Use the no-test trainer. No test code path is allowed.

## Frozen references

For seed 42 under strict seen-item masking:

- Existing full checkpoint validation NDCG@10: `0.1224280798`.
- Existing full-then-final-shared validation NDCG@10: `0.1311392350`.
- Existing post-hoc delta: `+0.0087111552`, paired-user 95% bootstrap interval
  `[+0.0063563122, +0.0110630719]`.

These values are outcome-known and are frozen here only to prevent a moving
pilot decision.

## Frozen pilot decision

Let `m_late` be the validation NDCG@10 of the validation-selected
`late_shared` checkpoint.

- Supports an optimization/deployment reversal pilot if
  `m_late <= 0.1204280798` (at least `0.002` below full).
- Refutes the reversal pilot if `m_late >= 0.1219280798` (within `0.0005` of
  full or better).
- Otherwise inconclusive.

Do not launch seeds 43-46 from this pilot alone. A multiseed control requires a
separate resource and decision review after the pilot and the prospective
synthetic mechanism experiment finish.
