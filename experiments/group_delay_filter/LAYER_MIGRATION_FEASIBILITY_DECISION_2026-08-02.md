# Collapse-routed projection feasibility decision — 2026-08-02

## Frozen outcome

**Inconclusive. Cohort test metrics were not accessed.**

| cohort | selected layer | validation delta NDCG@10 | paired-user 95% CI |
|---:|---|---:|---:|
| 943 users | first | -0.000295 | [-0.002938, +0.002329] |
| 2,000 users | none | abstain | not evaluated |
| 4,000 users | late | +0.002265 | [+0.000598, +0.003966] |

The 943-user delta is negative but remains inside the preregistered `0.0005`
failure tolerance. Because the survive rule required both deltas to be
nonnegative, the result is neither a pass nor a fail.

At 943 users, exactly 39 users improve and 39 are harmed. At 4,000 users, 220
improve and 161 are harmed. Legacy zero masking and strict negative-infinity
masking produce identical rankings in both cohorts.

## Research decision

**Do not promote energy-only collapse routing. Refine the candidate to
depth-conditioned EGSP.**

The coherent surviving rule is: project only a late temporal filter whose
rank-1 retained energy reaches `0.905`; abstain on early-layer collapse. Its
observed activations are positive on five full ML-1M spectral seeds, four
finalized causal-FIR ML-1M seeds, and the 4,000-user validation cohort. The
early-only 943-user result shows why layer position adds information beyond the
energy threshold.

This refinement is still discovery-derived from one dataset family. It is not
ready for a performance scale-up or publication claim. A fresh larger dataset
must prospectively exhibit late-filter collapse and then pass a no-tuning paired
evaluation.

Machine-readable paired results are in
`paired_scale_migration_N943_valid_s47.json` and
`paired_scale_migration_N4000_valid_s47.json`.
