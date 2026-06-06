# Ablation Pair Summary

Generated: 2026-06-03T15:36:47Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_mask_seen_instruments_20260611_20260615_full

- Ablation: `mask_seen_topm_true`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| instruments | 295130 | 0.049103153377 | 0.049060875139 | -0.000042278239 | 1.000000000000 | False |

| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |
|---|---|---:|---:|---:|---:|
| instruments | official_dropoutnet | 0.026930122448 | 0 | 3395 | 136 |
| instruments | official_dropoutnet_fixed | 0.026930122448 | 0 | 3395 | 136 |
| instruments | official_blair | 0.042023387544 | 0 | 3338 | 219 |
| instruments | official_clcrec | 0.027544762427 | 0 | 2978 | 709 |
| instruments | content_direct | 0.039848450362 | 0 | 3340 | 220 |
