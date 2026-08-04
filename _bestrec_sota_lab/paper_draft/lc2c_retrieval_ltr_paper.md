---
title: "LC2C Retrieval LTR: Full-Catalog Cold-Item Recommendation by Learning to Fuse Text, Collaborative Transfer, and Retrieval Signals"
author:
  - "Anonymous Authors"
date: "Draft: 2026-06-10"
bibliography: references.bib
---

# Abstract

Cold-item recommendation remains difficult because new catalog items have no direct interaction history, while production retrieval must still rank them against the entire unseen catalog rather than against a small cold-only candidate pool. We study this stricter setting on four Amazon Reviews 2023 domains and introduce **LC2C Retrieval LTR**, a frozen learning-to-rank fusion method that combines semantic item retrieval, BLaIR-style language-item encoders, DropoutNet-style latent cold-start transfer, LC2C behavioral projections, popularity, and rank features. The method is selected before a confirmatory run and then evaluated on five fresh seeds, five folds per seed, and full-catalog candidate sets with user training histories masked.

In the confirmatory audit, LC2C Retrieval LTR improves NDCG@10 over the best audited full-catalog cold-start baseline, tuned faithful DropoutNet, on all four datasets: Beauty 0.1488 vs. 0.1321, Fashion 0.1301 vs. 0.0951, Instruments 0.0496 vs. 0.0237, and Books 0.0402 vs. 0.0225. Holm-corrected per-user Wilcoxon tests are significant on all datasets, and user/item/fold clustered bootstrap intervals for the candidate-minus-best-baseline NDCG@10 delta are strictly positive. We release a compact artifact package containing frozen configurations, result manifests, statistical tests, baseline audits, source hashes, a source archive, and an independent clean-rebuild comparison. The claim is deliberately limited to zero-interaction cold-item full-catalog ranking under this protocol.

# 1. Introduction

Modern recommender systems must retrieve newly introduced items before those items accumulate interactions. This is the item cold-start problem: collaborative filtering can model warm items well, but a new item has no edge in the interaction graph and no behavior vector of its own. Content and language features can score such items, yet pure semantic retrieval often misses collaborative intent: users do not merely want textually similar products, but items that fit behaviorally learned substitution, complementarity, quality, price, and category patterns.

The evaluation protocol matters. Many cold-start studies rank cold targets only against a restricted cold-item set or a sampled set of negatives. Such evaluations are useful diagnostics, but they are easier than the retrieval problem faced by a deployed recommender, where a cold target must compete against all unseen warm and cold items after masking the user's training history. This paper therefore focuses on **full-catalog cold-item ranking**. For every test case, the candidate set is the full k-core item catalog minus the user's training items; the target item is cold with respect to training interactions.

We propose LC2C Retrieval LTR, a learned fusion model for this setting. The method is intentionally pragmatic: it does not replace strong text or latent cold-start models, but uses validation labels to learn how to combine them. The feature set includes content-direct retrieval, BLaIR-style semantic retrieval [@hou2024blair], DropoutNet-style cold-start latent predictions [@volkovs2017dropoutnet], LC2C behavioral transfer features, popularity, tail signals, and rank-normalized features. A gradient-boosted regression/ranking fallback learns a per-fold scoring function, with a safety rule that can fall back to a validated baseline if learned fusion does not improve validation performance.

The component attribution is deliberately explicit. LC2C Retrieval LTR is a fusion and audit protocol over prior retrieval signals; it does not claim novelty for BLaIR encoders, DropoutNet, CLCRec-style contrastive learning, TIGER/LIGER-style semantic identifiers, or the Amazon Reviews 2023 dataset. Those components are credited as prior work and are used as comparators or input signals under the same local protocol.

Our contributions are:

1. A retrieval-first LC2C successor for zero-interaction cold items that fuses semantic, collaborative-transfer, and rank evidence under a frozen confirmatory protocol.
2. A strict full-catalog cold-item evaluation on four Amazon Reviews 2023 domains with five confirmatory seeds and 25 seed-folds per dataset.
3. A baseline suite covering tuned faithful DropoutNet, CLCRec-style contrastive cold-start, BLaIR-style language retrieval, TIGER/LIGER-style retrieval, LC2C V2, and direct content retrieval, with explicit audits for method completeness and applicability.
4. A publication gate requiring wins on all four datasets, Holm-corrected per-user significance, and positive user/item/fold clustered bootstrap intervals over the best baseline.
5. A reproducibility package containing manifests, hashes, source archive metadata, finalized tables, significance files, baseline audits, and independent clean-rebuild equivalence.

# 2. Related Work

## 2.1 Cold-Start Recommendation

DropoutNet trains neural latent models for cold-start inference by explicitly dropping collaborative inputs during training, making it a natural comparator for item cold-start recommendation [@volkovs2017dropoutnet]. CLCRec frames cold-start item representation learning through mutual information between content features and collaborative signals, using contrastive learning to preserve collaborative information in content representations [@wei2021clcrec]. CCFCRec further targets blurry collaborative embeddings in cold-start item recommendation by contrasting content-based and co-occurrence collaborative embeddings [@zhou2023ccfcrec].

These methods motivate the central design choice in LC2C Retrieval LTR: cold-item ranking should not choose between content and collaborative transfer. It should learn when each signal is reliable.

## 2.2 Language-Item Encoders

Large language models have made item text a much stronger cold-start signal. BLaIR benchmarks semantic encoders for recommendation and introduces Amazon Reviews 2023, a large-scale corpus with more than 570 million reviews and 48 million items [@hou2024blair]. The BLaIR work is important here for two reasons. First, it makes clear that general embedding benchmarks do not necessarily predict recommendation quality. Second, it provides a strong text-retrieval baseline family for item metadata and review-derived semantics.

Recent work also explores retrieval-augmented LLM and knowledge-graph approaches for cold-start recommendation, including dynamic knowledge construction and LLM-guided retrieval [@yang2025coldrag]. A 2026 reproducibility study argues that generative recommenders often change model scale, identifier design, and training strategy together, making cold-start gains difficult to interpret without unified protocols [@zhang2026coldstarts]. These observations support our emphasis on frozen configurations, full-catalog candidate sets, and independent rebuild checks. Newer LLM/RAG methods remain promising, but their inference costs, candidate-generation assumptions, and protocol differences make direct comparison nontrivial. We therefore position them as adjacent future baselines rather than as completed evidence in the present audit.

## 2.3 Generative and Dense Retrieval

TIGER recasts recommendation as generative retrieval by predicting semantic item identifiers with a sequence-to-sequence model [@rajput2023tiger]. LIGER compares generative and dense retrieval under controlled settings and combines them in a hybrid model, reporting benefits for cold-start item recommendation in evaluated datasets [@yang2024liger]. Because generative retrieval is increasingly relevant to large-catalog recommendation, we include a TIGER/LIGER-style retrieval comparator in the audit. The comparator is weaker than DropoutNet in our zero-interaction full-catalog setting, but it is retained as a modern retrieval reference point.

## 2.4 Warm Collaborative Filtering Baselines

Classic warm-start baselines such as iALS [@hu2008implicit], MultiVAE [@liang2018multivae], EASE [@steck2019ease], and LightGCN [@he2020lightgcn] remain important for general recommendation studies. They are not the basis of our main SOTA claim because the present paper is restricted to zero-interaction cold items. Where a method cannot rank cold items without item content or a cold-start transfer mechanism, it is not a fair primary comparator for the exact setting unless adapted into a cold-item scorer.

# 3. Problem Setting

Let \(U\) be users, \(I\) be the full item catalog, and \(I_u^{train}\) be the items observed for user \(u\) during training. For each test record, the target item \(i^+\) is a cold item: it has no training interactions in the fold. The ranking candidate set is

\[
C_u = I \setminus I_u^{train}.
\]

The model scores every candidate in \(C_u\), so cold targets compete against all unseen warm and cold items. We report NDCG@10 as the primary metric, with HR@10 and MRR as secondary metrics. This differs from cold-fold-only ranking, where the candidate set is restricted to cold items and is therefore easier.

# 4. Method: LC2C Retrieval LTR

LC2C Retrieval LTR is a two-stage full-catalog reranking method. First, multiple cold-item scorers provide candidate evidence. Second, a learned fusion model reranks candidates using validation-fold labels.

## 4.1 Feature Sources

The frozen feature methods are:

- `content_direct`: direct semantic/content similarity scoring.
- `blair_text`: BLaIR-style text retrieval using recommendation-specialized item text encoders.
- `faithful_dropoutnet`: a DropoutNet-style latent cold-start predictor.
- `official_dropoutnet`: tuned faithful DropoutNet evidence used as a strong baseline and anchor.
- `lc2c_v2`: the prior LC2C behavior-vector projection.
- `lc2cpp_validated_margin`: the prior validated LC2C++ candidate.
- `melt_tail_transfer`: a tail-transfer feature where applicable, not used as an official MELT SOTA baseline.
- `popularity`: global item prior.
- Rank-normalized and tail indicators.

For every dataset, the DropoutNet feature configuration is frozen before confirmatory evaluation. The confirmatory run uses the following LTR hyperparameters: learning rate 0.04, maximum depth 3, 120 estimators, 60,000 maximum training examples, 32 negative samples per positive, z-sigmoid rank features, top-M reranking with \(M=512\), and training-history masking during top-M construction.

## 4.2 Learning and Safety Rule

For each training fold, validation labels are generated from held-out cold targets. A gradient-boosted regression/ranking fallback learns a scoring function over feature scores and rank features. The validation safety rule prevents a learned fusion model from replacing a stronger baseline when it fails to improve validation performance. In the confirmatory configuration, the fallback and validation baseline are tuned faithful DropoutNet.

This design is intentionally conservative. It treats strong text and DropoutNet models as evidence providers rather than adversaries, and only claims an improvement when the final frozen reranker beats them under held-out confirmatory seeds.

# 5. Experimental Protocol

## 5.1 Datasets

We evaluate on four Amazon Reviews 2023 domains: Beauty, Fashion, Instruments, and Books. The Books run uses the full 14,407-user warm/cold evaluation population in the confirmatory artifacts, with no cap in the approval run. All reported cold-item results use full-catalog candidate scope.

## 5.2 Splits and Seeds

The confirmatory run uses five fresh seeds: 20260701, 20260702, 20260703, 20260704, and 20260705. Each dataset has five folds per seed, for 25 seed-folds per dataset. The run id is `confirmatory_masked_candidate_20260701_20260705_candidate_only`.

## 5.3 Baselines

The primary cold full-catalog baselines are:

- `official_dropoutnet`: tuned faithful DropoutNet with WMF-style latent factors and frozen dataset-specific hyperparameters.
- `official_dropoutnet_fixed`: the exact DropoutNet configuration consumed by LC2C Retrieval LTR.
- `official_clcrec`: a CLCRec-style contrastive cold-start comparator imported under the same full-catalog protocol.
- `official_blair`: a BLaIR-style language retrieval comparator.
- `tiger_liger_retrieval`: a TIGER/LIGER-style retrieval comparator.
- `lc2c_v2`: the prior LC2C baseline.
- `content_direct`: direct content retrieval, used in audits and ablations.

The baseline audit marks official MELT as not applicable to the zero-interaction item-cold protocol because MELT's item branch requires train item contexts, and the strict folds give cold items zero train context. Warm-only methods such as LightGCN, MultiVAE, and iALS are not claimed as completed full-catalog cold-item baselines in the publication gate.

## 5.4 Statistical Testing

For each dataset, LC2C Retrieval LTR is compared against every cold-start baseline using per-user Wilcoxon signed-rank tests. Holm correction controls the familywise error rate across baseline comparisons within a dataset [@holm1979]. The publication gate additionally requires the user/item/fold clustered bootstrap 95% confidence interval for LC2C Retrieval LTR minus the best baseline to be strictly above zero.

## 5.5 Reproducibility Artifacts

The compact artifact package contains `run_config.json`, `results_manifest.json`, `results_final.json`, `significance.json`, `tables.json`, `publication_gate.json`, baseline audit files, source hashes, and source archive metadata. The current strict audit report is `_bestrec_sota_lab/runs/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md`. The independent clean rebuild reports `max_metric_abs_diff=0.0` and `record_multisets_match=true`. Raw JSONL record files total more than 5 GB and are not stored in normal Git; their byte sizes, row counts, and SHA256 hashes are recorded in the artifact README.

# 6. Results

Table 1 reports the primary full-catalog cold-item NDCG@10 results. LC2C Retrieval LTR beats every recorded cold-start baseline on all four datasets. The strongest baseline is tuned faithful DropoutNet in every domain.

**Table 1. Full-catalog cold-item NDCG@10. Higher is better.**

| Dataset | LC2C Retrieval LTR | DropoutNet | DropoutNet fixed | CLCRec | BLaIR | TIGER/LIGER | LC2C V2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Beauty | **0.148826** | 0.132137 | 0.118583 | 0.064611 | 0.043254 | 0.012125 | 0.012967 |
| Fashion | **0.130138** | 0.095089 | 0.093990 | 0.060061 | 0.037732 | 0.020011 | 0.017566 |
| Instruments | **0.049575** | 0.023654 | 0.023654 | 0.022389 | 0.007166 | 0.000278 | 0.000790 |
| Books | **0.040225** | 0.022520 | 0.021044 | 0.003949 | 0.007794 | 0.000970 | 0.000849 |

Table 2 gives effect sizes and clustered bootstrap intervals against the best baseline.

**Table 2. LC2C Retrieval LTR minus best baseline on NDCG@10.**

| Dataset | Best baseline | Delta | 95% clustered bootstrap CI |
| --- | --- | ---: | --- |
| Beauty | official_dropoutnet | 0.016689 | [0.006146, 0.027866] |
| Fashion | official_dropoutnet | 0.035049 | [0.027089, 0.043449] |
| Instruments | official_dropoutnet | 0.025921 | [0.023949, 0.027942] |
| Books | official_dropoutnet | 0.017706 | [0.015805, 0.019633] |

Table 3 reports secondary metrics for the candidate method.

**Table 3. LC2C Retrieval LTR secondary metrics.**

| Dataset | Test records | Seed-folds | HR@10 | MRR |
| --- | ---: | ---: | ---: | ---: |
| Beauty | 12,675 | 25 | 0.283393 | 0.131284 |
| Fashion | 18,996 | 25 | 0.252895 | 0.110923 |
| Instruments | 295,130 | 25 | 0.098363 | 0.046376 |
| Books | 3,009,960 | 25 | 0.079446 | 0.035489 |

The best-baseline Wilcoxon comparisons remain significant after Holm correction. Beauty is the narrowest win: 175 users favor LC2C Retrieval LTR, 75 favor tuned DropoutNet, and 3 are tied, with raw \(p=5.73 \times 10^{-13}\). The other datasets have substantially larger margins and raw p-values reported as 0.0 by the numerical test implementation due to underflow.

# 7. Ablation Evidence

The ablation suite is diagnostic rather than confirmatory, but it helps explain the mechanism. Removing DropoutNet as both feature and rerank anchor reduces NDCG@10 on all four development-era full runs:

**Table 4. Diagnostic ablation: remove DropoutNet feature and anchor.**

| Dataset | Reference NDCG@10 | Ablated NDCG@10 | Delta |
| --- | ---: | ---: | ---: |
| Beauty | 0.144103 | 0.132223 | -0.011879 |
| Fashion | 0.133771 | 0.122716 | -0.011054 |
| Instruments | 0.049103 | 0.038789 | -0.010315 |
| Books | 0.040656 | 0.036918 | -0.003738 |

This suggests that the final method is not merely a language-retrieval model. The DropoutNet-derived collaborative transfer signal provides consistent lift, particularly on Beauty, Fashion, and Instruments. The `mask_seen_topm_true` diagnostic has no effect on Beauty, a small negative effect on Fashion and Instruments, and a small positive effect on Books, indicating that the confirmatory win is not explained by a simple train-history leakage artifact in top-M pool construction.

# 8. Discussion

The main empirical pattern is that tuned DropoutNet is the hardest baseline, not BLaIR or TIGER/LIGER. This is plausible in a zero-interaction item-cold protocol: language encoders can identify semantically similar items, but DropoutNet is trained to map item content into a latent collaborative space. LC2C Retrieval LTR improves over DropoutNet by adding direct text, LC2C behavior projections, popularity/tail priors, and validation-trained rank interactions. The learned model therefore behaves less like a new standalone recommender and more like a robust retrieval arbitration layer.

The Books result is especially important because it uses 14,407 users and over three million cold test records across 25 seed-folds. The clean-rebuild comparison reports exact aggregate metric agreement and order-invariant raw-record multiset agreement. This substantially reduces the chance that the result is an artifact of stale caches or one-off record ordering.

# 9. Reproducibility Statement

The experiment is designed to be auditable from generated artifacts rather than notebook state. The compact publication package contains the frozen configuration, result manifests, final tables, statistical tests, and baseline audits. The canonical run was finalized with:

```powershell
python _bestrec_sota_lab/finalize.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --bootstrap-reps 2000
```

The user-facing confirmatory command associated with the protocol is:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --candidate-scope full_catalog --no-books-cap
```

The clean rebuild is represented by run id `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705`. Its comparison file reports:

- `passed=true`.
- `rebuilt_gate_passed=true`.
- `max_metric_abs_diff=0.0`.
- `record_multisets_match=true`.
- Raw JSONL byte hashes differ because record append order is not fixed, but order-invariant row-multiset fingerprints match for every dataset.

The run manifest records Windows 11, Python 3.12.13, the working directory, processor string, command, timestamps, seed list, input hashes, and output hashes. The source archive manifest records 226 source files and archive SHA256 `e4a7c1527f482e66b869b34403c7cd2087032f65ca76997f1082aefc8313b724`.

## 9.1 Raw Record Inventory

The raw per-user JSONL records are necessary for an adversarial reanalysis, but are too large for ordinary Git. They are documented by the generated manifest `_bestrec_sota_lab/publication_artifacts/raw_record_release/raw_record_release_manifest.json`, which records total size 5,099,053,650 bytes and 23,357,327 rows. The raw-record archive is published as chunked GitHub Release assets at <https://github.com/Ray0419/bestrec-sota-results/releases/tag/bestrec-raw-records-v1>; `raw_record_upload_parts_manifest.json` records the seven part files, sizes, and SHA256 digests. The canonical files are:

| Dataset | Raw record file | Local bytes | Row count | Canonical raw SHA256 |
| --- | --- | ---: | ---: | --- |
| Beauty | `cold_full_catalog_records_beauty.jsonl` | 19,003,185 | 88,725 | `57cf6cca51f2649d0235d88396c4e7eb3e79f854ceba4b83a18cf020184ffc63` |
| Fashion | `cold_full_catalog_records_fashion.jsonl` | 28,705,816 | 132,972 | `7e81a5c3bb7ebcf018a4c1f36fbdc974950742547bcafed841c0e77ef046f0ab` |
| Instruments | `cold_full_catalog_records_instruments.jsonl` | 458,668,616 | 2,065,910 | `9c7310b282fa2d7c36327308df8be3aee4182edf1804a86ae07d872ebedfc580` |
| Books | `cold_full_catalog_records_books.jsonl` | 4,592,676,033 | 21,069,720 | `5b8254afc7f6dfb4d3cceb0b8e0829881287f47c31379b2b9657763b46cdf382` |

For a camera-ready venue deposit, a DOI mirror on Zenodo, OSF, or institutional storage would be preferable to relying solely on GitHub Release retention. The current release is still checksum-verifiable from the local manifests:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/prepare_raw_record_release.py --verify-only
uv --project _bestrec_run run python _bestrec_sota_lab/package_raw_record_release.py --verify-parts
uv --project _bestrec_run run python _bestrec_sota_lab/validate_public_submission.py --deep-verify-raw --verify-github-release
```

# 10. Threats to Validity

**Validation-trained fusion.** LC2C Retrieval LTR learns to combine multiple strong feature providers. This is a legitimate retrieval architecture, but it can overfit if validation folds are reused after seeing test outcomes. We reduce this risk by freezing the selected configuration before the confirmatory seeds and by not altering the algorithm after the confirmatory run starts.

**Comparator coverage.** The main cold-start comparator set is strong for zero-interaction item cold-start: tuned faithful DropoutNet, BLaIR-style retrieval, CLCRec-style contrastive cold-start, TIGER/LIGER-style retrieval, and LC2C V2. It does not exhaust all 2025--2026 LLM/RAG recommender systems, especially dynamic KG/LLM methods whose protocols and compute profiles differ substantially. The claim should therefore remain protocol-specific.

**MELT applicability.** MELT is a long-tail sequential recommendation method rather than a zero-interaction item-cold scorer. The audit marks official MELT as not applicable because cold items have no train item context in the strict folds. A modified MELT-style baseline could be informative, but would be an adaptation and should not be described as official MELT without a separate audit.

**Raw record archival.** Compact artifacts are sufficient to verify reported tables, manifests, significance tests, gates, source hashes, and clean-rebuild equivalence. They are not a substitute for public raw per-record release. A hostile reviewer can reasonably ask for the raw JSONL files.

**Catalog/domain scope.** The experiments cover four Amazon Reviews 2023 domains. They do not prove transfer to media, news, short-video, or industrial catalogs with different metadata quality and popularity dynamics.

# 11. Limitations and Submission Requirements

This draft supports a strict but narrow claim. It does not establish general recommender SOTA, warm-start SOTA, or superiority over all recent LLM/RAG recommenders under their own protocols. Two limitations should be resolved before submission:

1. Raw per-user JSONL files should be archived outside normal Git, for example with Git LFS, Zenodo, OSF, or institutional storage. The current repository records hashes, row counts, sizes, rebuild fingerprints, and a generated raw-release manifest, but not the 5+ GB raw files themselves.
2. If the target venue expects broad recommender comparisons, warm-start LightGCN, MultiVAE, iALS, and EASE results should be reported only as secondary warm diagnostics, not as part of the cold-item SOTA claim unless adapted and audited for zero-interaction cold items.

# 12. Conclusion

LC2C Retrieval LTR shows that full-catalog cold-item recommendation benefits from learned arbitration among language, content, collaborative-transfer, and rank signals. Under a frozen five-seed confirmatory protocol on four Amazon Reviews 2023 domains, it beats the best audited modern cold-start baseline on NDCG@10 in every dataset, with Holm-corrected per-user significance and positive clustered-bootstrap intervals. The result is publication-worthy as a cold-item full-catalog ranking study, provided the raw records are archived and the claim remains scoped to the evaluated protocol.

# Artifact Availability

The compact artifact package is located at `_bestrec_sota_lab/publication_artifacts/`. The canonical confirmatory files are under `confirmatory_masked_candidate_20260701_20260705_candidate_only/`; independent rebuild files are under `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/`. The raw-release manifest and upload-part manifest are under `raw_record_release/`. The GitHub repository contains the compact package and source archive metadata; raw per-user records are published as release assets rather than committed to the Git tree due to size.

# Appendix A. Data Processing and Split Construction

<!-- DATA_PROCESSING_APPENDIX:START -->
This appendix is generated by `_bestrec_sota_lab/paper_draft/generate_data_processing_appendix.py` from the raw deduplicated caches, `_bestrec_run/run_cold_item.py`, `_bestrec_run/v5_utils.py`, and the approved confirmatory artifacts.

The raw Amazon Reviews 2023 category mapping is inherited from `_bestrec_run/preprocess_5core_standard.py`. The strict cold-item pipeline then applies dataset-specific recursive k-core filtering with `v5_utils.kcore_filter`, reindexes users/items with `v5_utils.reindex`, partitions items into five cold folds with `run_cold_item.make_item_kfold`, and evaluates full-catalog candidates after masking each user's training history.

**Raw deduplicated cache before strict k-core filtering.**

| Dataset | Amazon Reviews 2023 category | Review file | Users | Items | Interactions |
| --- | --- | --- | ---: | ---: | ---: |
| Beauty | `All_Beauty` | `data/beauty/All_Beauty.jsonl` | 631,986 | 112,565 | 693,929 |
| Fashion | `Amazon_Fashion` | `data/fashion/Amazon_Fashion.jsonl` | 2,035,490 | 825,869 | 2,474,375 |
| Instruments | `Musical_Instruments` | `data/instruments/Musical_Instruments.jsonl` | 1,762,679 | 213,571 | 2,975,551 |
| Books | `Books` | `data/books/Books.jsonl` | 10,297,355 | 4,446,065 | 29,139,329 |

**Strict evaluation graph after recursive k-core filtering.**

| Dataset | k-core threshold | Users | Items | Interactions |
| --- | ---: | ---: | ---: | ---: |
| Beauty | 5 | 253 | 356 | 2,535 |
| Fashion | 4 | 513 | 614 | 3,805 |
| Instruments | 10 | 3,911 | 2,269 | 59,026 |
| Books | 20 | 14,407 | 13,164 | 601,992 |

**Confirmatory item-fold and record construction.**

| Dataset | Seed-folds | Cold items/fold | Train interactions/fold | Cold test interactions/fold | Candidate records/fold | Candidate records total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Beauty | 25 | 71-72 | 1,993-2,050 | 485-542 | 485-542 | 12,675 |
| Fashion | 25 | 122-123 | 2,949-3,108 | 697-856 | 693-852 | 18,996 |
| Instruments | 25 | 453-454 | 45,384-48,662 | 10,364-13,642 | 10,364-13,642 | 295,130 |
| Books | 25 | 2,632-2,633 | 478,234-487,000 | 114,992-123,758 | 114,992-123,758 | 3,009,960 |

The confirmatory seeds are `20260701, 20260702, 20260703, 20260704, 20260705`. Each seed uses five item folds. For every test record, the target item is in the held-out cold item set, and the ranking candidate set is the full strict item catalog minus the user's training items.

The documented user-facing command for the approved protocol is:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --candidate-scope full_catalog --no-books-cap
```

The independently rebuilt approval run is `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705`, compared against canonical run `confirmatory_masked_candidate_20260701_20260705_candidate_only`.
<!-- DATA_PROCESSING_APPENDIX:END -->

# Appendix B. Frozen Configuration Summary

The candidate model is `lc2c_retrieval_ltr`. The frozen LTR configuration uses:

| Parameter | Value |
| --- | --- |
| Fallback method | `official_dropoutnet` |
| Validation baseline | `official_dropoutnet` |
| Feature methods | `content_direct`, `blair_text`, `faithful_dropoutnet`, `lc2c_v2`, `lc2cpp_validated_margin`, `melt_tail_transfer`, `popularity`, `official_dropoutnet` |
| Learning rate | 0.04 |
| Maximum depth | 3 |
| Number of estimators | 120 |
| Maximum train examples | 60,000 |
| Negative samples per positive | 32 |
| Rank feature scope | `zsigmoid` |
| Rerank top-M | 512 |
| Rerank output mode | `rank_blend` |
| Rerank prediction weight | 0.5 |
| Score batch items | 2,048 |
| Mask seen items in top-M | true |

The frozen DropoutNet feature configuration is:

| Dataset | k | p_drop | reg | mode |
| --- | ---: | ---: | ---: | --- |
| Beauty | 128 | 0.5 | 10.0 | `wmf_warm_tower_cold_calib` |
| Fashion | 128 | 0.5 | 10.0 | `wmf_warm_tower_cold_calib` |
| Instruments | 128 | 0.7 | 1.0 | `wmf_warm_tower_cold_calib` |
| Books | 64 | 0.7 | 1.0 | `wmf_warm_tower_cold_calib` |

# Appendix C. Baseline Audit Summary

| Baseline | Status in gate | Evidence file | Notes |
| --- | --- | --- | --- |
| `official_dropoutnet` | complete | `official_dropoutnet_audit.json` | Tuned faithful DropoutNet with full-catalog records on all datasets. |
| `official_dropoutnet_fixed` | complete | `official_dropoutnet_fixed_audit.json` | Exact DropoutNet config consumed by LC2C Retrieval LTR. |
| `official_blair` | complete | `official_blair_audit.json` | BLaIR-style text retrieval records present on all datasets. |
| `official_clcrec` | complete | `official_clcrec_audit.json` | CLCRec-style same-protocol records present on all datasets. |
| `tiger_liger_retrieval` | complete | `tiger_liger_retrieval_audit.json` | Official LIGER modules used; canonical record coverage complete. |
| `official_melt` | not applicable | `official_melt_audit.json` | Official item branch requires train item contexts; strict cold items have zero train context. |
| LightGCN, MultiVAE, iALS | not run | `baseline_audit.json` | Warm/general recommenders, not full-catalog zero-interaction cold-item evidence. |

# Appendix D. Publication Checklist

Before submission:

1. Re-run `validate_public_submission.py --deep-verify-raw --verify-github-release` and attach `PUBLIC_SUBMISSION_GATE.md`.
2. Regenerate Appendix A with `generate_data_processing_appendix.py` after any data or split change.
3. Replace anonymous author metadata and add affiliation/funding/conflict statements.
4. Add a rendered pipeline figure and a bootstrap-delta figure if the target venue expects visual summaries.
5. Rebuild the manuscript from Markdown with Pandoc and attach the rendered PDF plus source package.
