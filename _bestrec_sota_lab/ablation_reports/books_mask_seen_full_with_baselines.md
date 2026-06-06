# Ablation Pair Summary

Generated: 2026-06-03T19:45:03Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_mask_seen_books_20260611_20260615_full

- Ablation: `mask_seen_topm_true`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| books | 3009960 | 0.040656206936 | 0.040993031185 | 0.000336824249 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| books | official_dropoutnet | 0.023983416399 | 0 | 12188 | 1230 |
| books | official_dropoutnet_fixed | 0.023983416399 | 0 | 12188 | 1230 |
| books | official_blair | 0.036556902521 | 0 | 12836 | 629 |
| books | official_clcrec | 0.043228260256 | 0 | 13044 | 486 |
| books | content_direct | 0.033817860855 | 0 | 12800 | 644 |
