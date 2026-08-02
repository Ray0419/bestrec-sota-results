# Post-training FIR adapter probe

This exploratory probe asks whether the released identity backbone can acquire
the FIR benefit without retraining the backbone. It replaces the frozen
per-channel zero FIR in an identity checkpoint with a zero-initialized,
16-parameter channel-shared causal FIR, freezes every other parameter, and fits
only those 16 taps on the training split.

The test split is loaded only to reproduce the immutable item-ID mapping and is
never scored. Results are validation-only and post-hoc. A successful pilot
would motivate a fresh, frozen comparison against full fine-tuning; it would
not establish a parameter-efficient training claim by itself because gradient
propagation still traverses the frozen backbone.

```bash
python posthoc_adapter.py --seed 20260901 --train-users 5000 --epochs 5 \
  --sampled-negs 512 --eval-users 5000 --out pilot_s20260901.json
```
