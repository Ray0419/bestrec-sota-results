# Analysis plan: ML-1M power-preserving channel consensus v1

Frozen on 2026-08-02 before constructing or evaluating this intervention. This
is an outcome-known exploratory mechanism test, not confirmatory evidence.

## Question

Does the validation gain from final-layer channel sharing require reducing the
filter's frequency-dependent energy, or is removing disagreement between
channel responses itself beneficial?

For every frequency row `f` of an eligible final complex filter `W`, define

```text
m_f = mean_c W[f,c]
r_f = sqrt(mean_c |W[f,c]|^2)
u_f = m_f / |m_f|
H[f,c] = r_f u_f  for every channel c.
```

If `m_f` is numerically zero, use the deterministic unit phase `u_f = 1`.
This makes all channels use one response while preserving the original total
energy separately at every frequency:

```text
sum_c |H[f,c]|^2 = sum_c |W[f,c]|^2.
```

Use the same frozen late-layer eligibility rule as channel sharing: rank-1
retained energy at least `0.905` and dominant-channel/uniform cosine at least
`0.97`. Apply no fine-tuning. Evaluate the five existing ML-1M seeds 42-46 on
full-catalog validation only, with strict negative-infinity seen-item masking.
Test access is prohibited.

## Frozen interpretation

- **Energy-independent consensus support:** power-preserving consensus exceeds
  the full checkpoint by at least `0.002` mean validation NDCG@10 and in at
  least four of five seeds.
- **Mean-projection equivalence:** its mean is within `0.0005` of the ordinary
  channel-mean projection.
- **Energy reduction is necessary:** its mean is no more than `0.0005` above
  the full checkpoint while the ordinary mean projection retains its known
  positive effect.
- Otherwise call the result partial or irregular.

Even a positive result does not authorize large-scale training. It would
strengthen the mechanism claim and nominate the power-preserving operator as a
candidate only after the fair late-shared training control and prior-art audit
are also adjudicated.
