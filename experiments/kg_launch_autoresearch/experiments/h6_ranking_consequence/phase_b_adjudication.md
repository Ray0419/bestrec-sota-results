# H6 Phase-B outcome adjudication

Date: 2026-08-07 (Australia/Sydney)

Classification: one-shot confirmatory held-fixed outcome test

Verdict: `KILL_H6_OUTCOME_DIRECTION`

## Integrity

- Frozen implementation commit: `fe655df3`
- Total launcher wall time: 873.2 seconds
- Primary, exact replay, and deep-verifier exit codes: `0`
- Every child stderr and asynchronous-error ledger: empty
- Primary scientific-payload SHA-256: `9340CB3B51BBCFA9D759016427D1D5016758218C86F806D35E33DD85DEAB4259`
- Replay scientific-payload SHA-256: `9340CB3B51BBCFA9D759016427D1D5016758218C86F806D35E33DD85DEAB4259`
- Raw-artifact-payload SHA-256: `494A216AFDB656523C6214579C71E8A2EC413C2DF659162ED975276C02C3735B`
- Primary result SHA-256: `230FE5FFE90F88BED589BD4D3577018A7E13E8C9A00FB30A2E8A14AE374FD2E9`
- Replay result SHA-256: `0B0D805EE5D3C14FE9C19D240E70683D639F0DB784AC8A652B7841805E4F9500`
- Deep-verification SHA-256: `3C07DB577F7F4EA3AC51FCEDA00FD7EC342141253D64823487C221779450BB28`
- Completion-marker SHA-256: `57BE94438E094B69B87416C410E26615080975957DDB9E6C37BF83CECE86406A`
- Pattern-engine maximum score error over the six shared-fact arms:
  `5.551115123125783e-16`; every committed rank was reproduced exactly.
- Candidate labels were opened only after the Phase-A manifest and frozen
  implementation checks. There was no post-label filtering.

## Primary result

The exact cohort contains 64,443 impressions, 43,374 users, 2,422,258
candidates, and the pre-label rank-affected subset of 35,445 impressions.

| Quantity | Historical | Current | Current minus historical |
|---|---:|---:|---:|
| Full nDCG@10 | 0.3032686000 | 0.3009009047 | -0.0023676952 |
| Rank-affected nDCG@10 | 0.1742099608 | 0.1699052243 | -0.0043047365 |
| Full nDCG@5 | 0.2420919388 | 0.2393825340 | -0.0027094049 |
| Full MRR | 0.2644577135 | 0.2616571007 | -0.0028006128 |
| Full impression AUC | 0.5107970280 | 0.50827899997 | -0.0025180280 |
| Full micro pair accuracy | 0.5151493988 | 0.5124760823 | -0.0026733165 |

The paired user-cluster 95 percent interval for the primary nDCG@10 contrast is
`[-0.0028224524, -0.0019211763]`. The difference is statistically resolved but
is smaller than the prospectively required absolute magnitude of `0.005`.

## Gate adjudication

| Gate | Result | Evidence |
|---|---|---|
| Magnitude and paired cluster interval | fail | `abs(D_H)=0.0023677 < 0.005`, although its interval excludes zero |
| Rank-affected same sign | pass | `D_H,affected=-0.0043047` |
| Matched-null attribution or entity reversal | fail | `abs(D_H)=0.0023677` does not exceed null `q95=0.0027244`; all 100 nulls lie on the entity-opposite side relative to current, and the fixed entity gaps do not meet the reversal conditions |
| Robustness direction | pass | blocklist delta `-0.0011170`; Q30/Q22686-removal delta `-0.0021828` |
| Integrity and leakage | pass | exact replay/deep verification, frozen cohort, empty failure channels |

## Scientific interpretation

The current external-KG snapshot is modestly worse than the historical snapshot
for this deliberately simple kernel, and the sign is stable in both structural
robustness views. However, the effect is below the locked practical threshold
and is not stronger than relation/property-degree-matched rewiring. Therefore
the experiment does **not** support a lead claim that transaction-time semantic
fact leakage materially explains recommendation quality on this cohort.

H6 is eliminated without rescue tuning. H5 remains a valid structural finding
(large external-KG revision drift), and H6 Phase A remains a valid ranking
sensitivity finding, but neither is sufficient for a Tier-A outcome claim.
H7A is not advanced as the main algorithm because it was outcome-contingent and
already red-teamed as a certificate-feasibility mechanism rather than standalone
algorithmic novelty.

The next independent direction is a label-blind graph-mathematical POC: a
regularized Laplacian/Rayleigh cold-item residual with provenance-derived
Loewner score bounds. It targets the limitation that the additive shared-fact
kernel ignores global paths while ordinary KG encoders lack deterministic
transaction-time ranking certificates.
