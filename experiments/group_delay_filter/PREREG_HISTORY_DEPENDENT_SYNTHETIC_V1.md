# Preregistration: history-dependent synthetic intervention v1

Frozen on 2026-08-02 before implementing the generator, creating either
dataset, inspecting either generated dataset, or training either model.

## Research question

Does a population-shared temporal dependency that cannot be solved from the
most recent item cause FMLP-Rec's learned temporal filter to become
channel-shared?

## Frozen coupled generator

- Random generator: NumPy PCG64, seed `20260803`.
- Users: 2,000.
- Items: 2,000, partitioned into 10 disjoint topics of 200 items.
- Split each topic into two streams, A and B, with 100 items each, and draw one
  random cyclic permutation per stream.
- Draw one topic, one A-stream start, and one B-stream start independently for
  every user.
- Sequence length: 62 unique items. Alternate A and B items throughout.
- `SyntheticCoupledPhase`: use the A start for both streams. The next item is a
  deterministic function of the most recent item, and also of the item two
  steps back.
- `SyntheticIndependentPhase`: use the independent A and B starts. Across
  users, the next item is not determined by the most recent item, while it is
  the deterministic cyclic successor of the item two steps back.
- Use identical stream permutations, user topics, A starts, and B starts for
  both conditions. Assert uniqueness within every sequence and equal item
  histograms between conditions.

## Label-safe screen

Using only the last-52/leave-two-out window used by FMLP-Rec, estimate
train-window lag-1 and lag-2 item-to-next-item tables and evaluate them on the
validation item. Continue only if all conditions hold:

- Independent-phase lag-2 NDCG@10 is at least `0.75`.
- Independent-phase lag-2 minus lag-1 NDCG@10 is at least `0.50`.
- Coupled-phase lag-1 NDCG@10 is at least `0.75`.

Validation labels are allowed for this screen. The final test item is never
accessed.

## Frozen training

- Model: standard full FMLP-Rec from source revision used by the preceding
  synthetic experiment.
- Seed: 47 for both conditions.
- Hidden size 64, two layers, maximum sequence length 50, batch size 256,
  learning rate 0.001, dropout 0.5, no weight decay.
- Device: MPS if available.
- Up to 120 epochs, patience 10, checkpoint selected only by validation
  NDCG@20.
- Use `TEMPORAL_FILTER_NO_TEST_TRAIN_V2`; no test code path is allowed.
- Train independent phase first. Train coupled phase only after the independent
  run completes successfully.

## Frozen mechanism decision

Canonicalize DC and Nyquist responses to real values. Let `rho_2` be the
final-layer rank-1 retained energy for independent phase and `rho_1` the value
for coupled phase.

- Optimization sanity requires independent-phase validation NDCG@10 at least
  `0.50`; otherwise the mechanism result is inconclusive.
- Mechanism pass: `rho_2 >= 0.905` and `rho_2 - rho_1 >= 0.04`.
- Mechanism fail: `rho_2 <= rho_1`.
- Otherwise: inconclusive.

Also report dominant-channel/uniform cosine, early-layer energy, selected
epoch, and item-embedding spectra. They do not alter the primary decision.

## Frozen projection feasibility

If the independent-phase final layer passes both `rho >= 0.905` and
dominant-channel/uniform cosine `>= 0.97`, replace only that layer by its
column-mean shared temporal response. Evaluate paired full-catalog validation
NDCG@10 with strict seen-item masking and a 10,000-resample paired-user
bootstrap interval. Do not access either synthetic test split.

- Projection pass: validation delta is nonnegative.
- Projection fail: validation delta is below `-0.0005`.
- Otherwise: inconclusive.

This intervention tests a mechanism. It does not count as prospective
real-domain evidence for the algorithm.
