# Prospective EGSP Feasibility Protocol V1

Frozen before training or inspecting any Sports & Outdoors or Yelp checkpoint.

## Hypothesis

Full-rank training can discover a stable low-rank filter solution that is harder to
optimize directly. Post-training rank-1 projection should improve generalization
only for layers whose learned tap-by-channel or frequency-by-channel matrix is
already strongly rank-1 dominated.

## Fixed algorithm

For each filter layer independently:

1. Compute its singular values from the trained weight matrix.
2. Compute retained rank-1 energy `s1^2 / sum_i(si^2)`.
3. Apply the exact rank-1 SVD projection only when retained energy is at least
   `0.905`; otherwise leave the layer unchanged.
4. Do not fine-tune and do not use validation or test labels for projection.

The threshold and rank were frozen from the prior ML-1M/Beauty/Toys discovery
study. They must not be changed in response to this experiment.

## Prospective pilot

- Dataset: `Sports_and_Outdoors`
- Architecture: standard FMLP-Rec spectral filter
- Seed: `47`
- Training: repository evaluator defaults, with early stopping on validation
- Primary metric: full test-catalog `NDCG@10`
- Comparator: byte-equivalent unprojected state passed through the same export
  and evaluation path

## Decision rule

- **Feasibility pass:** at least one layer is selected and projected
  `NDCG@10 >= baseline NDCG@10`.
- **Feasibility fail:** at least one layer is selected and projected
  `NDCG@10 < baseline NDCG@10 - 0.0005`.
- **Inconclusive:** no layer is selected, or the delta lies in `[-0.0005, 0)`.

A pass authorizes a five-seed Sports replication and then a causal-FIR
replication. It does not by itself establish publication readiness.

## Integrity constraints

- Do not inspect test results during training.
- Do not substitute a checkpoint selected on the test set.
- Do not alter the dataset split, rank, threshold, or metric after the run.
- Report negative and inconclusive outcomes alongside positive outcomes.

## Execution record

Status: **aborted and incomplete; not eligible for the decision rule above**.

The seed-47 run completed epoch 30 and began epoch 31, but repeated host
scheduling stalls made completion impractical. It was interrupted during epoch
31. No test metric was accessed. At abort, the validation-selected epoch-30
checkpoint had rank-1 energies `0.874167943` and `0.790125882`; neither layer
met the frozen `0.905` intervention threshold. The observed state is therefore
an incomplete mechanism-gate abstention, not a performance pass, fail, or
completed inconclusive result.

The exact checkpoint diagnostics and SHA-256 hashes are recorded in
`sports_pilot_aborted.json`.
