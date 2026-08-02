# Prospective depth-conditioned EGSP KuaiRec protocol V1

Frozen before downloading KuaiRec, preprocessing its interactions, training a
checkpoint, or inspecting any KuaiRec recommendation metric or filter spectrum.

## Question

Does beneficial late-filter rank collapse transfer from MovieLens ratings to a
larger, cross-domain short-video interaction sequence?

## Data

- Source: official KuaiRec 2.0 `big_matrix.csv`, Zenodo record 18164998.
- License: CC BY 4.0 as recorded by Zenodo.
- Use `user_id`, `video_id`, and `timestamp` from every logged viewing event;
  do not threshold on watch ratio or use side information.
- Sort by `(user_id, timestamp, video_id)`.
- If a user-video pair repeats, retain its earliest event so a held-out target
  cannot already be masked as seen.
- Retain users with at least five unique videos after deduplication.
- Remap retained users and videos in ascending original-ID order, one-indexed.
- Use repository leave-last-two-out splitting.
- Record archive MD5/SHA-256, sequence-file SHA-256, duplicate count, retained
  cardinalities, and sequence-length statistics before training.

This protocol predicts the next logged video exposure/consumption event. It does
not reinterpret the sequence as an unbiased preference label.

## Fixed training

- Standard two-layer full-filter FMLP-Rec.
- Seed 47; sequence length 50; hidden size 64; batch size 256.
- Adam at `0.001`, no weight decay, repository-default dropout.
- Maximum 200 epochs, patience 10, validation NDCG@20 checkpoint selection.
- Use `train_no_test.py` and verify the prepared data SHA-256 before startup.
- Device placement may be MPS or CPU.

Training may access validation for checkpoint selection but has no test loader
or test evaluation path.

## Frozen algorithm

Depth-conditioned EGSP examines only the final temporal-filter matrix:

1. Canonicalize complex DC and Nyquist responses to real values.
2. Compute `rho_1 = sigma_1^2 / sum_j sigma_j^2`.
3. If `rho_1 >= 0.905`, replace the final filter by its exact rank-1 SVD
   projection, leave every other parameter unchanged, and do not fine-tune.
4. Ignore early-layer energy for intervention.

## Sequential decision rule

1. **Mechanism abstention:** if the final filter does not reach `0.905`, record
   its spectrum and do not inspect test performance.
2. If it activates, hash baseline and projected states before test access.
3. Run one paired full-catalog test evaluation with strict negative-infinity
   seen-item masking and 10,000 paired-user bootstrap samples.
4. **Feasibility pass:** projected test NDCG@10 is at least baseline.
5. **Feasibility fail:** delta is below `-0.0005`.
6. A delta in `[-0.0005, 0)` is performance-inconclusive.

A pass authorizes four additional KuaiRec seeds and causal-FIR replication. It
does not establish a Tier-A claim by itself.

## Integrity constraints

- Do not change event filtering, split, seed, threshold, rank, layer, model
  capacity, checkpoint metric, or primary test metric after an outcome.
- Do not inspect test labels, predictions, or aggregate test metrics before the
  mechanism decision is recorded.
- Report abstention, negative, and inconclusive outcomes alongside positives.
