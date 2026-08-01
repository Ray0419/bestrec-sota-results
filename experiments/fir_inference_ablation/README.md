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

The output includes paired bootstrap confidence intervals because every mode
uses exactly the same users. The predeclared deployment non-inferiority margin
is 0.0005 NDCG@10. A smoke run is diagnostic only; any apparent result must be
repeated on the complete validation set and across all eight released seeds.
The orthogonal modes are checkpoint-surgery feasibility probes. A positive
result would still require from-scratch training and a dedicated novelty gate.

```bash
python fir_inference_ablation.py \
  --arm learned --seed 20260901 --subsample-users 1000 \
  --out smoke_learned_s20260901.json
```
