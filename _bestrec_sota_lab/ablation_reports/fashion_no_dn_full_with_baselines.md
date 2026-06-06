# Ablation Pair Summary

Generated: 2026-06-03T15:07:20Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_no_dn_fashion_20260611_20260615_full

- Ablation: `no_dropoutnet_feature_or_anchor`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| fashion | 18980 | 0.133770656690 | 0.122716255128 | -0.011054401562 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| fashion | official_dropoutnet | 0.041167423540 | 1.11245e-26 | 315 | 118 |
| fashion | official_dropoutnet_fixed | 0.041456537738 | 1.37753e-26 | 315 | 118 |
| fashion | official_blair | 0.097999287772 | 7.56552e-64 | 393 | 22 |
| fashion | official_clcrec | 0.079038565841 | 1.97686e-56 | 366 | 81 |
| fashion | content_direct | 0.095498329909 | 3.17086e-69 | 410 | 0 |
