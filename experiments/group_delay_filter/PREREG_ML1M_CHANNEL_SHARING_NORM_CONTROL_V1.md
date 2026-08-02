# Analysis plan: ML-1M channel-sharing norm control v1

Frozen on 2026-08-02 before evaluating a norm-matched control. This is an
outcome-known exploratory mechanism test and does not create confirmatory
evidence.

## Question

Does final-layer channel sharing improve ML-1M ranking because it removes the
channel-specific deviation, or merely because orthogonal projection reduces
the filter's Frobenius norm?

## Frozen control

For each existing ML-1M spectral checkpoint at seeds 42-46, let `P(W)` be the
final filter with its channel mean repeated over channels. Construct

```text
W_scale = W * ||P(W)||_F / ||W||_F.
```

This leaves every channel direction and relative coefficient unchanged while
matching exactly the Frobenius norm of the channel-shared checkpoint. Do not
fine-tune. Evaluate full-catalog validation only with strict negative-infinity
seen-item masking. Test is prohibited.

The comparison of interest is channel-shared minus norm-matched-scale
validation NDCG@10, paired by seed. Existing full and channel-shared endpoints
are outcome-known.

## Frozen interpretation

- **Structure-specific support:** channel sharing exceeds the scale control by
  at least `0.002` on the five-seed mean and in at least four of five seeds.
- **Amplitude explanation:** the absolute mean difference is at most `0.0005`.
- Otherwise call the result partial or irregular.

No training campaign is authorized by this control alone. A structure-specific
result still faces the prior-art and cross-dataset activation gates in
`EGSP_RESEARCH_DECISION_2026-08-02.md`.
