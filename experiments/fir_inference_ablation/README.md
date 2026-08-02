# FIR inference ablation

This probe asks whether the causal FIR control's gain is carried by its
inference-time computation or only by the training trajectory it induces.
It operates on the released best-validation checkpoints and evaluates a fixed,
deterministic subset of the **validation** split. It does not score the test
split.

For one checkpoint, the probe compares:

- `normal`: the checkpoint as trained;
- `zero`: delete the FIR residual at inference;
- `current_only`: retain only the current-position tap;
- `lag_only`: retain only strict-history taps;
- `channel_mean`: replace every channel kernel with their mean (the learned
  arm only).
- `orthogonal_history`: project the FIR residual away from the current item
  vector at each position;
- `orthogonal_lag`: combine strict-history taps with that projection.
- `terminal_only`: apply the trained FIR residual only at the last real input
  token, leaving all earlier encoder inputs unfiltered;
- `terminal_lag_only`: combine terminal-only execution with strict-history taps.
- `position_only`: retain only the FIR response to the deterministic positional
  embedding table;
- `item_only`: retain only the FIR response to item/content embeddings.
- `rank1_projection`: replace the learned tap-by-channel bank by its best
  post-training rank-1 SVD approximation.

The terminal modes are functional checkpoint-surgery probes. The hook still
computes the full convolution, so its wall time is not an efficiency
measurement; a surviving mode would require a direct `O(Kd)` terminal kernel
to realize the expected `O(LKd) -> O(Kd)` FIR inference reduction.
If `position_only` survives, its convolution is deterministic and can be folded
exactly into the learned positional embedding table for convolution-free
deployment. The component modes are evaluated with dropout disabled, as in all
checkpoint evaluations.

The output includes paired bootstrap confidence intervals because every mode
uses exactly the same users. The predeclared deployment non-inferiority margin
is 0.0005 NDCG@10. A smoke run is diagnostic only; any apparent result must be
repeated on the complete validation set and across all eight released seeds.
The orthogonal modes are checkpoint-surgery feasibility probes. A positive
result would still require from-scratch training and a dedicated novelty gate.

## Feasibility outcomes

- Orthogonal-history FIR is negative across eight seeds on the 5,000-user
  validation subsample (mean delta about `-0.00086`, two-sided paired sign
  `p=0.00391`).
- Terminal-only and positional-only execution lose too much ranking quality.
- Item-only execution was positive in one smoke run but negative across all
  eight 5,000-user shared-FIR seeds (mean about `-0.00034`).
- Post-training rank-1 projection of the released learned BEST-Rec FIR is
  negative on the fixed 1,000-user smoke sample (mean `-0.000295`, 3/8 seeds
  positive). The frozen 90.5% energy gate in the related EGSP study correctly
  abstains on all eight checkpoints, so this branch is closed without test
  evaluation.

```bash
python fir_inference_ablation.py \
  --arm learned --seed 20260901 --subsample-users 1000 \
  --out smoke_learned_s20260901.json
```
