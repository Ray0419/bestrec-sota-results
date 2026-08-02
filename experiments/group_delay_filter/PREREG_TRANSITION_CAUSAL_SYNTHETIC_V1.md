# Preregistration: shared-transition synthetic intervention v1

Frozen on 2026-08-02 before implementing the generator, creating either
synthetic dataset, or training either model.

## Research question

Does population-level reuse of item transitions causally increase late
temporal-filter channel consensus and make post-training channel sharing
beneficial?

## Frozen generator

- Random generator: NumPy PCG64, seed `20260802`.
- Users: 2,000.
- Items: 2,000, partitioned into 10 disjoint topics of 200 items.
- Sequence length: 62 unique items per user.
- Each topic receives one random cyclic permutation, defining a shared
  deterministic successor for every item.
- Each user is assigned one topic and starts at a random item in that topic.
- At every subsequent step, draw one coupled uniform variate. With probability
  `alpha`, append the shared successor of the current item, skipping already
  visited items along the cycle. Otherwise append a uniformly selected unseen
  item from the same topic.
- Generate two datasets from identical topic permutations, user assignments,
  starts, uniform variates, and noise-choice variates:
  `SyntheticTransitionHigh` with `alpha=0.85` and
  `SyntheticTransitionLow` with `alpha=0.15`.
- Write one line per user as `user_id item_1 ... item_62`, with contiguous item
  identifiers starting at one. Assert uniqueness within every sequence.

## Label-safe screen

Apply `TRAIN_WINDOW_TRANSITION_STRUCTURE_V1` to the same last-52/leave-two-out
window used by FMLP-Rec. Continue to model training only if the high condition's
first-order-transition minus popularity validation NDCG@10 exceeds the low
condition by at least `0.10`. This screen may use validation labels but never
the final test item.

## Frozen training

- Model: standard full FMLP-Rec from the existing source revision.
- Seed: 47 for both conditions.
- Hidden size 64, two layers, maximum sequence length 50, batch size 256,
  learning rate 0.001, dropout 0.5, no weight decay.
- Device: MPS if available.
- Up to 120 epochs, patience 10, checkpoint selected only by validation
  NDCG@20.
- Use `TEMPORAL_FILTER_NO_TEST_TRAIN_V2`; no test code path is allowed.
- Train the high condition first. Train the low condition only after the high
  run completes successfully.

## Frozen mechanism decision

Canonicalize DC and Nyquist responses to real values. Let `rho_H` and `rho_L`
be final-layer rank-1 retained energies for high and low transition reuse.

- Mechanism pass: `rho_H >= 0.905` and `rho_H - rho_L >= 0.04`.
- Mechanism fail: `rho_H <= rho_L`.
- Otherwise: inconclusive.

Also report dominant-channel/uniform cosine and early-layer energies; they do
not alter this primary decision.

## Frozen projection feasibility

If a condition's final layer passes both `rho >= 0.905` and dominant-channel
uniform cosine `>= 0.97`, replace only that layer by its column-mean shared
temporal response. Evaluate paired full-catalog **validation** NDCG@10 with
strict seen-item masking and a 10,000-resample paired-user bootstrap interval.
Do not access either synthetic test split in this experiment.

- Projection pass: validation delta is nonnegative.
- Projection fail: validation delta is below `-0.0005`.
- Otherwise: inconclusive.

This controlled experiment can support a mechanism claim but cannot substitute
for a prospective real-domain replication.
