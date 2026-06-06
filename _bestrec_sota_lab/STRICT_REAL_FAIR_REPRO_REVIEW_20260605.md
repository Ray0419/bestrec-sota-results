# Strict Reality, Fairness, And Reproducibility Review

Generated UTC: 2026-06-06T12:27:08Z

Run reviewed: `C:\Users\rayxc\Documents\R\_bestrec_sota_lab\runs\confirmatory_masked_candidate_20260701_20260705_candidate_only`

Decision: **Approve for full publication/reproducibility approval.**

Algorithmic cold-start SOTA gate: **Passed**

## Short Answer

The primary cold-start result is artifact-backed, fair under the frozen full-catalog protocol, and reproducible to the level checked by this audit.
The claim must still be limited to cold-item full-catalog ranking; broad warm/general recommender SOTA is not supported by this lab run.

## Artifact Checks

| Artifact | Present |
|---|---:|
| `run_config.json` | yes |
| `results_final.json` | yes |
| `significance.json` | yes |
| `baseline_audit.json` | yes |
| `publication_gate.json` | yes |
| `tables.json` | yes |
| `results_manifest.json` | yes |
| `cold_full_catalog_records_beauty.jsonl` | yes |
| `cold_full_catalog_records_fashion.jsonl` | yes |
| `cold_full_catalog_records_instruments.jsonl` | yes |
| `cold_full_catalog_records_books.jsonl` | yes |

## Publication Gate

- Gate passed: `True`
- Stage: `confirmatory`
- Protocol: `cold_sota_strict_v2`
- Candidate scope: `full_catalog`
- Seeds: `[20260701, 20260702, 20260703, 20260704, 20260705]`

## Primary Cold Full-Catalog Result

| Dataset | Candidate NDCG@10 | Best available baseline | Baseline NDCG@10 | User delta | Holm | Cluster delta | 95% CI | Bootstrap reps |
|---|---:|---|---:|---:|---|---:|---:|---:|
| Beauty | 0.148825868265 | `official_dropoutnet` | 0.132136507692 | 0.022093434722 | *** | 0.016689360142 | [0.0061, 0.0279] | 2000 |
| Fashion | 0.130137817674 | `official_dropoutnet` | 0.095089227114 | 0.047860950697 | *** | 0.035048592836 | [0.0271, 0.0434] | 2000 |
| Instruments | 0.049575215957 | `official_dropoutnet` | 0.023654099528 | 0.027021055101 | *** | 0.025921115652 | [0.0239, 0.0279] | 2000 |
| Books | 0.040225492558 | `official_dropoutnet` | 0.022519558968 | 0.021338635520 | *** | 0.017705932260 | [0.0158, 0.0196] | 2000 |

## Mandatory Evidence Methods

| Method | Status | Records on all datasets | Evidence file |
|---|---|---:|---|
| `official_dropoutnet_fixed` | `complete` | yes | `official_dropoutnet_fixed_audit.json` |
| `official_dropoutnet` | `complete` | yes | `official_dropoutnet_audit.json` |
| `official_blair` | `complete` | yes | `official_blair_audit.json` |
| `official_clcrec` | `complete` | yes | `official_clcrec_audit.json` |
| `official_melt` | `not_applicable_to_zero_interaction_item_cold` | no | `official_melt_audit.json` |
| `tiger_liger_retrieval` | `complete` | yes | `tiger_liger_retrieval_audit.json` |

## Ablation Status

| Dataset | Ablation | Status | Reference NDCG | Ablation NDCG | Delta | Records |
|---|---|---|---:|---:|---:|---:|
| Beauty | `mask_seen_topm_true` | `complete` | 0.144102822835 | 0.144102822835 | 0.000000000000 | 12660 |
| Beauty | `no_dropoutnet_feature_or_anchor` | `complete` | 0.144102822835 | 0.132223455258 | -0.011879367577 | 12660 |
| Fashion | `mask_seen_topm_true` | `complete` | 0.133770656690 | 0.131123862314 | -0.002646794375 | 18980 |
| Fashion | `no_dropoutnet_feature_or_anchor` | `complete` | 0.133770656690 | 0.122716255128 | -0.011054401562 | 18980 |
| Instruments | `mask_seen_topm_true` | `complete` | 0.049103153377 | 0.049060875139 | -0.000042278239 | 295130 |
| Instruments | `no_dropoutnet_feature_or_anchor` | `complete` | 0.049103153377 | 0.038788602097 | -0.010314551280 | 295130 |
| Books | `mask_seen_topm_true` | `complete` | 0.040656206936 | 0.040993031185 | 0.000336824249 | 3009960 |
| Books | `no_dropoutnet_feature_or_anchor` | `complete` | 0.040656206936 | 0.036918209844 | -0.003737997092 | 3009960 |

## Findings

No blocking findings were detected by this artifact audit.
## What Is Real And Fair

- The key empirical values are generated from JSONL records rather than hardcoded paper tables.
- The finalizer validates required record fields, metric ranges, dataset identity, and `candidate_scope="full_catalog"`.
- The run uses the active post-repair confirmatory seeds.
- Books cold full-catalog records are uncapped in this run.
- The repaired candidate records `mask_seen_in_topm=true`; the old unmasked variant is retired by protocol.
- Required cold evidence methods are either complete or explicitly non-applicable under the frozen zero-interaction item-cold protocol.
- `tiger_liger_retrieval` has full-catalog scored records on all four datasets, all five seeds, and all 25 seed/fold combinations per dataset.
- Source archive verified: `_bestrec_sota_lab\source_archives\bestrec_sota_lab_source_confirmatory_masked_candidate_20260701_20260705_candidate_only.zip` (62 files, sha256 `1742da4a713b550b58ea860249ba8ccf96e3309d4bbbda1869f0b119d7c83e85`).
- Record-level clean rebuild passed in `confirmatory_masked_candidate_20260701_20260705_candidate_only__record_rebuild`: derived summaries, significance, tables, gate, and manifest were regenerated from canonical JSONL records.
- Proxy/local diagnostic methods are excluded from the paper-facing cold table.

## Claim Boundaries

- The supported claim is cold-item full-catalog recommendation only.
- Broad warm/general recommender SOTA is unsupported because these warm baselines are not complete in this lab gate: `ials`, `lightgcn`, `multivae`.
- The candidate uses DropoutNet-derived evidence as a feature/rerank anchor, so the paper must not claim DropoutNet independence; the fair comparison is against both fixed-config and tuned official DropoutNet.
- Official MELT status is `not_applicable_to_zero_interaction_item_cold`; any paper must disclose the zero-interaction item-cold non-applicability rationale instead of reporting a proxy MELT result as official.

## Required Repair Path

1. No blocking repair steps were generated by the artifact audit.

## Reviewer Verdict

I would approve the cold-start full-catalog claim, with the claim boundaries above, because this audit found no blocking artifact, fairness, or reproducibility findings.

Paper-facing cold table methods: `lc2c_v2`, `lc2c_retrieval_ltr`, `official_dropoutnet_fixed`, `official_dropoutnet`, `official_blair`, `official_clcrec`, `tiger_liger_retrieval`

`tables.json` says algorithmic `sota_claim_allowed=True` with scope `algorithmic cold-item full-catalog gate only`.

Latest manifest input hash count: `101`.
Latest manifest output hash count: `5`.
