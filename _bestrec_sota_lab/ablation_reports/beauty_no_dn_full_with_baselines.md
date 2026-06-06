# Ablation Pair Summary

Generated: 2026-06-03T14:53:27Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_no_dn_beauty_20260611_20260615_full

- Ablation: `no_dropoutnet_feature_or_anchor`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| beauty | 12660 | 0.144102822835 | 0.132223455258 | -0.011879367577 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| beauty | official_dropoutnet | 0.008975167023 | 0.017874 | 136 | 112 |
| beauty | official_dropoutnet_fixed | 0.032195956711 | 1.04475e-10 | 162 | 86 |
| beauty | official_blair | 0.090447624110 | 6.48215e-36 | 221 | 19 |
| beauty | official_clcrec | 0.079675559838 | 7.36811e-36 | 215 | 28 |
| beauty | content_direct | 0.092576439616 | 1.33984e-40 | 234 | 1 |
