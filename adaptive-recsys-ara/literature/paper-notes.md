# Key Paper Notes

Each note records only what the cited primary source supports and how it constrains this project.

## Sentence-BERT (Reimers & Gurevych, 2019)

- **Source:** https://aclanthology.org/D19-1410/; DOI 10.18653/v1/D19-1410.
- **Supported result:** siamese/triplet encoders make semantic comparison practical by independently encoding texts; the paper contrasts about 65 hours for 10,000 pairwise BERT comparisons with about 5 seconds using SBERT embeddings.
- **Constraint for RIPPLE:** item text can be encoded once and cached; this does not establish personalized recommendation quality.

## FAISS (Johnson, Douze, & Jégou, 2017)

- **Source:** https://arxiv.org/abs/1702.08734.
- **Supported result:** product quantization, inverted files, and GPU implementations enable billion-scale similarity search.
- **Constraint for RIPPLE:** the PoC can use exact inner product for audit and IVF for serving simulation; scale claims require ANN quality/latency reporting, not only ranking metrics.

## ScaNN (Guo et al., 2020)

- **Source:** https://proceedings.mlr.press/v119/guo20h.html.
- **Supported result:** anisotropic quantization better preserves maximum inner-product search than ordinary reconstruction-error objectives.
- **Constraint for RIPPLE:** index approximation changes decision boundaries and must be present when training/evaluating hard confusions.

## Retrieval-conditioned reranking (Jain et al., 2022)

- **Source:** https://research.google/pubs/stochastic-retrieval-conditioned-reranking/.
- **Supported result:** a reranker trained independently of the stochastic retriever can be mismatched; the paper derives a retrieval-conditioned objective.
- **Constraint for RIPPLE:** coupling loss data to retrieval is prior art. The differentiated claim must involve reference-free query adaptation, an immutable catalog index, and latency-budgeted ANN effort.

## TIGER (Rajput et al., 2023)

- **Source:** https://proceedings.neurips.cc/paper_files/paper/2023/hash/20dcab0f14046a5c6b02b61da9f13229-Abstract-Conference.html.
- **Supported result:** semantic IDs and autoregressive generation offer an alternative to conventional dense retrieval.
- **Constraint for RIPPLE:** generative retrieval is a relevant baseline class, but token decoding and ID grounding are different system costs than ANN.

## SimPO (Meng, Xia, & Chen, 2024)

- **Source:** https://proceedings.neurips.cc/paper_files/paper/2024/hash/e099c1c9699814af0be873a175361713-Abstract-Conference.html; DOI 10.52202/079017-3946.
- **Supported result:** average log probability is used as an implicit reward; a target margin is added; no reference model is required. The paper reports gains over DPO on its chat benchmarks.
- **Constraint for RIPPLE:** reference-free alignment is established. RIPPLE adapts its score-difference geometry to retrieval, not its language-model benchmark claim.

## Preference algorithms do not learn rankings (Song et al., 2024)

- **Source:** https://openreview.net/forum?id=YkJ5BuEXdD.
- **Supported result:** most examined preference-tuned models achieved less than 60% preference-ranking accuracy; DPO struggled to repair mild reference-model ranking errors.
- **Constraint for RIPPLE:** measure item-order accuracy and NDCG directly instead of assuming a lower preference loss implies a better recommender.

## RecPO (Zhang et al., ACL 2026)

- **Source:** https://aclanthology.org/2026.acl-long.656/; DOI 10.18653/v1/2026.acl-long.656.
- **Supported result:** recommendation feedback has intensity and temporal context that a binary pair loses; adaptive margins improve results on five datasets.
- **Constraint for RIPPLE:** recency/intensity margins cannot be claimed as novel. RecPO evaluates constructed candidate sets rather than an online ANN funnel.

## Recommendations as Treatments (Schnabel et al., 2016)

- **Source:** https://proceedings.mlr.press/v48/schnabel16.html.
- **Supported result:** observed recommendation logs are selected by users and the existing serving policy; propensity methods can correct evaluation/training under stated assumptions.
- **Constraint for RIPPLE:** non-interactions are not automatically valid rejected items. The PoC separates explicit low ratings from index-mined unlabeled confusions and reports this limitation.

## Quake (Mohoney et al., OSDI 2025)

- **Source:** https://www.usenix.org/system/files/osdi25-mohoney.pdf.
- **Supported result:** dynamic partitioning and per-query effort can target ANN recall under skew and updates, with large latency reductions in the reported workloads.
- **Constraint for RIPPLE:** adaptive effort is prior art for geometric recall. RIPPLE's controller must use decision/preference uncertainty and be evaluated on downstream recommendation utility.

## Drift-Adapter (Vejendla, EMNLP 2025)

- **Source:** https://aclanthology.org/2025.emnlp-main.805/.
- **Supported result:** a compatibility adapter approximates full reindexing after embedding-model upgrades on generic retrieval tasks with low query-time overhead.
- **Constraint for RIPPLE:** fixed-index compatibility is adjacent prior art, but it does not personalize from interaction preferences or optimize the recommendation funnel.

## OneRec and GRank (2025–2026, provisional)

- **Sources:** https://arxiv.org/abs/2502.18965 and https://arxiv.org/abs/2510.15299.
- **Supported result:** their abstracts describe attempts to unify retrieval and ranking through generative architectures and report improvements in their settings.
- **Constraint for RIPPLE:** joint retrieval/ranking is not novel as a slogan. The proposed contribution is a lightweight fixed-index path with an explicit latency and maintenance gate.
