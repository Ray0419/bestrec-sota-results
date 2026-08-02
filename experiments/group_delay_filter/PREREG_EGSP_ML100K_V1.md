# Prospective EGSP ML-100K Protocol V1

Frozen before downloading ML-100K, training its checkpoint, or inspecting any
ML-100K filter spectrum or recommendation metric.

## Question

Does the ML-1M late-filter rank-collapse phenomenon reproduce on an independent,
high-density sequential-recommendation dataset under the already frozen EGSP
rule?

## Data and split

- Dataset: official GroupLens MovieLens 100K archive.
- Include all ratings, matching the repository's ML-1M treatment.
- Apply deterministic iterative 5-core filtering to users and items.
- Sort each user's interactions by `(timestamp, original item id)`.
- Remap retained user and item IDs in ascending original-ID order.
- Use the repository's leave-last-two-out protocol: training excludes the last
  two interactions, validation predicts the penultimate interaction, and test
  predicts the final interaction.
- The preparation script must record the official archive MD5, archive SHA-256,
  generated sequence-file SHA-256, and resulting cardinalities before training.

## Fixed model and training

- Architecture: standard two-layer FMLP-Rec with full complex spectral filters.
- Sequence length: 50; hidden size: 64; batch size: 256.
- Dropout: repository defaults (`0.5` hidden and attention dropout).
- Optimizer: Adam, learning rate `0.001`, no weight decay.
- Seed: `47`.
- Maximum epochs: 200; patience: 10.
- Checkpoint selection: repository-default validation `NDCG@20`.
- Device may be CPU or MPS because it changes only execution placement.

Training must use `train_no_test.py`, which has no test evaluation path. Test
metrics remain inaccessible until the mechanism decision below is written.

## Frozen intervention

For each trained complex frequency-by-channel filter matrix independently:

1. Compute `rho_1 = sigma_1^2 / sum_j sigma_j^2`.
2. Select a layer only if `rho_1 >= 0.905`.
3. Replace each selected layer with its exact rank-1 SVD projection.
4. Leave all other parameters byte-equivalent and do not fine-tune.

Rank and threshold were fixed by the earlier ML-1M discovery study and must not
be changed for this protocol.

## Sequential decision rule

1. If no layer is selected, record **mechanism abstention** and do not inspect
   ML-100K test performance.
2. If at least one layer is selected, hash the baseline and projected states,
   then run one paired full-catalog test evaluation with strict negative-infinity
   seen-item masking.
3. **Feasibility pass:** projected `NDCG@10 >= baseline NDCG@10`.
4. **Feasibility fail:** projected `NDCG@10 < baseline NDCG@10 - 0.0005`.
5. A delta in `[-0.0005, 0)` is performance-inconclusive.

A pass authorizes four additional fresh ML-100K seeds and one larger dense
MovieLens dataset. It does not authorize a cross-domain or Tier-A claim by
itself. Every outcome, including abstention, remains in the audit trail.

## Integrity constraints

- Do not inspect test labels, predictions, or aggregate test metrics during
  training or before the mechanism decision.
- Do not change preprocessing, rank, threshold, seed, model capacity, split,
  checkpoint rule, or metric after seeing an outcome.
- Do not use ML-100K to tune a soft-shrinkage alternative; that alternative is
  governed by a separate protocol.
