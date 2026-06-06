# Ablation Pair Summary

Generated: 2026-06-03T22:51:33Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_no_dn_books_20260611_20260615_full

- Ablation: `no_dropoutnet_feature_or_anchor`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| books | 3009960 | 0.040656206936 | 0.036918209844 | -0.003737997092 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| books | official_dropoutnet | 0.021829773621 | 0 | 9140 | 3919 |
| books | official_dropoutnet_fixed | 0.021829773621 | 0 | 9140 | 3919 |
| books | official_blair | 0.034403259743 | 0 | 11500 | 766 |
| books | official_clcrec | 0.041074617477 | 0 | 11478 | 1085 |
| books | content_direct | 0.031664218076 | 0 | 11658 | 361 |
