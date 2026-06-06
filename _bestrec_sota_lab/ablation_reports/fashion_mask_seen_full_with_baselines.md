# Ablation Pair Summary

Generated: 2026-06-03T15:01:02Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_mask_seen_fashion_20260611_20260615_full

- Ablation: `mask_seen_topm_true`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| fashion | 18980 | 0.133770656690 | 0.131123862314 | -0.002646794375 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| fashion | official_dropoutnet | 0.047763575980 | 1.85556e-66 | 415 | 36 |
| fashion | official_dropoutnet_fixed | 0.048052690178 | 2.43988e-68 | 414 | 35 |
| fashion | official_blair | 0.104595440212 | 1.92849e-67 | 436 | 18 |
| fashion | official_clcrec | 0.085634718281 | 1.23219e-71 | 424 | 40 |
| fashion | content_direct | 0.102094482349 | 2.99002e-72 | 436 | 15 |
