# EGSP nested-user scale mechanism protocol V1

Frozen after the completed ML-100K abstention and before generating or training
the nested ML-1M cohorts below. This is an exploratory mechanism study; it does
not use or confer confirmatory recommendation performance evidence.

## Question

Is the late-filter rank collapse seen on full ML-1M driven by the number of
independent user trajectories, rather than by matrix density alone?

## Fixed cohorts

- Source: the exact processed `ML-1M.txt` used by the five-seed discovery runs.
- Select users by ascending SHA-256 of `"20260802:<original user id>"`.
- Construct nested cohorts of 943 and 4,000 users.
- Preserve every selected user's full chronological item sequence and original
  item IDs; only reindex output user IDs consecutively.
- Record source, output, and selected-user-list SHA-256 hashes.

The 943-user cohort matches ML-100K's user count while retaining ML-1M's sequence
distribution. The 4,000-user cohort probes approach to the full 6,040-user
regime. No recommendation test metric will be evaluated for either cohort.

## Fixed training and diagnostic

- Standard two-layer full-filter FMLP-Rec.
- Seed 47; sequence length 50; hidden size 64; batch size 256.
- Adam at `0.001`, no weight decay, repository-default dropout.
- Maximum 200 epochs, patience 10, validation NDCG@20 checkpoint selection.
- Use `train_no_test.py`; device placement may be MPS or CPU.
- Canonicalize the complex DC and Nyquist filter responses to real values before
  SVD, matching the EGSP projector.
- Primary diagnostic: final-layer rank-1 retained energy at the
  validation-selected checkpoint.
- Secondary diagnostic: first-layer retained energy.

The known full-ML-1M late-layer discovery range across seeds 42–46 is
`[0.905536, 0.916679]`; this interval was observed before this protocol.

## Decision rule

- **Scale mechanism supported:** the final-layer energy rises by at least `0.04`
  from 943 to 4,000 users and reaches at least `0.895` at 4,000 users.
- **Scale-only mechanism falsified:** the rise is below `0.02` and the 4,000-user
  energy remains below `0.88`.
- **Inconclusive:** every other outcome. An inconclusive result authorizes a
  predeclared 2,000-user interpolation point, not threshold revision.

Even a support outcome only authorizes a preregistered larger-dataset
activation test. It does not authorize test-set projection experiments or a
Tier-A claim.

## Integrity constraints

- Do not select users by activity, sequence length, item coverage, or outcome.
- Do not inspect interim spectra; use only validation-selected checkpoints after
  fixed early stopping.
- Do not access cohort test metrics.
- Keep aborted attempts, preprocessing manifests, checkpoints, logs, and hashes.
