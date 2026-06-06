# Ablation Pair Summary

Generated: 2026-06-03T14:43:47Z
Reference run: `confirmatory_strict_v2_candidate_20260611_20260615`
Method: `lc2c_retrieval_ltr`

## Results

### ablation_mask_seen_beauty_seed20260611_fold0

- Ablation: `mask_seen_topm_true`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| beauty | 525 | 0.132276029992 | 0.132276029992 | 0.000000000000 | 0.000000000000 | True |

### ablation_no_dn_beauty_seed20260611_fold0

- Ablation: `no_dropoutnet_feature_or_anchor`
- Publication gate passed: `False`

| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |
|---|---:|---:|---:|---:|---:|---|
| beauty | 525 | 0.132276029992 | 0.125367436739 | -0.006908593253 | 1.000000000000 | False |
