# Ablation Pair Summary

Generated: 2026-06-03T14:53:27Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_mask_seen_beauty_20260611_20260615_full

- Ablation: `mask_seen_topm_true`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| beauty | 12660 | 0.144102822835 | 0.144102822835 | 0.000000000000 | 0.000000000000 | True |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| beauty | official_dropoutnet | 0.015958253153 | 1.38892e-09 | 161 | 90 |
| beauty | official_dropoutnet_fixed | 0.039179042841 | 1.73048e-37 | 221 | 26 |
| beauty | official_blair | 0.097430710241 | 5.63791e-38 | 231 | 16 |
| beauty | official_clcrec | 0.086658645969 | 5.19445e-42 | 240 | 7 |
| beauty | content_direct | 0.099559525747 | 3.44057e-42 | 241 | 6 |
