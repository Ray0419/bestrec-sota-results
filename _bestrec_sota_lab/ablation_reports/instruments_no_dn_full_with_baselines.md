# Ablation Pair Summary

Generated: 2026-06-03T16:03:27Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_no_dn_instruments_20260611_20260615_full

- Ablation: `no_dropoutnet_feature_or_anchor`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| instruments | 295130 | 0.049103153377 | 0.038788602097 | -0.010314551280 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| instruments | official_dropoutnet | 0.016889123872 | 1.57226e-163 | 2432 | 1034 |
| instruments | official_dropoutnet_fixed | 0.016889123872 | 1.57226e-163 | 2432 | 1034 |
| instruments | official_blair | 0.031982388968 | 0 | 2973 | 292 |
| instruments | official_clcrec | 0.017503763851 | 7.18516e-147 | 2363 | 1228 |
| instruments | content_direct | 0.029807451786 | 0 | 3117 | 42 |
