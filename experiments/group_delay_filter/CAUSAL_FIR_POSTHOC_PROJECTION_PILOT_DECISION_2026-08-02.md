# Causal-FIR post-hoc projection pilot decision - 2026-08-02

## Decision

**Do not advance the BEST-Rec transfer.**

The preregistered validation-only screen evaluated the released
Musical Instruments `learned` FIR-control checkpoint for seed `20260901` on
the fixed sample of 10,000 validation users. Test user-target associations were
not loaded or scored. Three test-only candidate identifiers were read solely to
reconstruct the checkpoint's trained catalog, as allowed by the pre-outcome
erratum.

| projection | retained rank-1 energy | delta NDCG@10 | paired bootstrap 95% interval |
|---|---:|---:|---:|
| rank-1 SVD | 0.896998 | -0.000177 | [-0.000804, +0.000460] |
| channel-shared | diagnostic | +0.000091 | [-0.000621, +0.000835] |

The primary rank-1 arm passes the two numerical non-harm screen thresholds,
but its interval crosses zero, its retained energy is below the separately
frozen EGSP activation threshold of `0.905`, and the experiment duplicates an
earlier forced-projection smoke whose eight-seed mean was negative. The result
is therefore a neutral mechanism check, not evidence for transfer or a reason
to tune the gate.

No full-validation expansion and no test evaluation are authorized. The
artifact of record is `causal_fir_projection_pilot_s20260901.json`.
