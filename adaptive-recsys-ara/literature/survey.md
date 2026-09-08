# Phase 1 Literature Survey: Modern Recommendation Retrieval and Preference Alignment

**Cutoff:** 2026-08-07

**Scope:** dense/vector candidate retrieval, generative and LLM-assisted recommendation, and preference optimization for ranking.

**Evidence rule:** venue papers and primary project pages are treated as established evidence; 2025–2026 arXiv-only results are marked provisional.

## Current architecture frontier

Modern large-catalog recommenders usually separate candidate generation from ranking. A two-tower or sentence-embedding model maps a user context and item metadata into a shared vector space; an approximate-nearest-neighbor (ANN) index reduces millions of items to a tractable candidate set. Richer rankers or LLMs then reason over those candidates. This decomposition delivers scale, but it also means that no downstream aligner can recover a relevant item that ANN retrieval removed.

Sentence-BERT demonstrated the efficiency of independently encoded text embeddings [D19-1410]. FAISS and ScaNN made billion-scale similarity search practical [FAISS17; GUO20]. Recommender Forest, TIGER, OneRec, and GRank explore stronger coupling or generative alternatives [ZHU22; RAJPUT23; ONE25; GRANK26], but autoregressive IDs, constrained decoding, or joint structures introduce new latency, grounding, and update costs.

Preference optimization has simultaneously moved from reference-relative DPO to reference-free SimPO and recommendation-specific variants [RAF23; MENG24; RECPO26]. SimPO's length-normalized policy reward and target margin remove the reference-model forward pass. Yet a preference loss can improve response generation without learning a reliable ordering: Song et al. report that most tested preference-tuned models remain below 60% ranking accuracy [SONG24]. Recommendation variants cover multi-negative comparisons, smoothing, temporal margins, and causal invariance, but generally optimize a small, already constructed candidate list rather than the full served retrieval funnel [SDPO24; ROSE24; RECPO26; CAUSAL26].

## Four critical bottlenecks

### L1 — Objective mismatch across the retrieval funnel

ANN systems are tuned for geometric Recall@k or reconstruction error; preference optimizers are tuned on chosen/rejected responses or preconstructed slates; online systems care about user utility under a latency SLO. The three objectives are not equivalent. ScaNN shows that generic quantization error is already misaligned with maximum inner-product search [GUO20]. Retrieval-conditioned reranking shows that training a reranker in isolation from its retriever is suboptimal [JAIN22]. Quake adapts ANN effort to a geometric-recall target under dynamic workloads, not downstream personalized utility [MOHONEY25].

**Unresolved question:** can preference supervision shape the retrieval decision itself, rather than only reorder survivors, without rebuilding the item index?

### L2 — Implicit feedback is censored by the serving policy

An unclicked item can mean dislike, non-exposure, low position, or missed opportunity. Treating all non-interactions as negatives creates false labels. Recommendations-as-Treatments formalizes selection by both the user and the serving recommender [SCHNABEL16]. Recent preference methods reduce damage through sampling, smoothing, or causal invariance, but do not jointly model the actual ANN exposure boundary and a reference-free retrieval policy [ROSE24; RECPO26; CAUSAL26].

**Unresolved question:** how should preference pairs be selected and weighted when the retriever itself determines what could be observed?

### L3 — Fresh personalization conflicts with catalog-scale update cost

User intent can change within a session, while catalog embeddings and ANN indexes update much more slowly. Re-encoding or rebuilding a large item index after every alignment update is operationally infeasible. Index-preserving query adapters exist for generic information retrieval [ANCEPRF21; IPA26], and Drift-Adapter studies cross-model embedding compatibility [VEJENDLA25], but those works do not optimize personalized recommendation utility from interaction feedback.

**Unresolved question:** can a query-only preference adapter update rapidly while keeping item vectors, index topology, and memory footprint fixed?

### L4 — Semantic reasoning and alignment remain coupled to online cost

Reference-free objectives reduce training overhead, not necessarily serving latency. LLM rerankers still serialize candidates, incur prompt/decoder costs, and exhibit order or popularity bias. Even accelerated generative recommenders pay token-generation or constrained-search costs [ATSPEED25]. Industrial systems often precompute LLM outputs or use cascades to avoid per-request cost [WANG25].

**Unresolved question:** can most preference alignment be distilled into millisecond vector operations, reserving expensive reasoning only for uncertain requests?

## Novelty boundaries established by the scan

The proposed work must **not** claim novelty for any of the following in isolation:

- reference-free preference optimization (SimPO already provides it);
- multiple or hard negatives (S-DPO, NAPO, and DynamicPO cover variants);
- preference intensity or recency-aware margins (RecPO);
- personalized label smoothing (RosePO);
- listwise or top-k preference optimization (LiPO and KPO);
- causal or OOD preference optimization (CausalDPO);
- retrieval-conditioned reranking (Jain et al.);
- query-only, fixed-index adaptation in generic search (ANCE-PRF and index-preserving adaptation);
- adaptive ANN effort for geometric recall (Quake);
- query-level compute routing by itself (adaptive reranking work exists).

The targeted whitespace is their **full-stack intersection**: a reference-free, recommendation-specific query adapter trained on pairs drawn from the actual serving ANN boundary, coupled to uncertainty-budgeted ANN effort, while keeping catalog embeddings and the index immutable. This is a literature-scan finding, not a proof that no unpublished or differently named method exists.

## Phase 1 conclusion

The most consequential bottleneck is the interface between retrieval and alignment. Downstream preference tuning cannot repair candidate censoring; rebuilding the catalog for every preference update is expensive; and always-on LLM ranking violates tight latency budgets. A promising direction is therefore to move a compact form of preference alignment upstream into the query vector while treating the deployed ANN index as part of the training environment.

## Primary sources

- [D19-1410] Reimers & Gurevych. *Sentence-BERT*. EMNLP-IJCNLP 2019. https://aclanthology.org/D19-1410/
- [FAISS17] Johnson, Douze, & Jégou. *Billion-scale similarity search with GPUs*. 2017. https://arxiv.org/abs/1702.08734
- [GUO20] Guo et al. *Accelerating Large-Scale Inference with Anisotropic Vector Quantization*. ICML 2020. https://proceedings.mlr.press/v119/guo20h.html
- [ZHU22] Zhu et al. *Learning Tree-based Deep Model for Recommender Systems*. NeurIPS 2022. https://proceedings.neurips.cc/paper_files/paper/2022/hash/fe2fe749d329627f161484876630c689-Abstract-Conference.html
- [RAJPUT23] Rajput et al. *Recommender Systems with Generative Retrieval*. NeurIPS 2023. https://proceedings.neurips.cc/paper_files/paper/2023/hash/20dcab0f14046a5c6b02b61da9f13229-Abstract-Conference.html
- [RAF23] Rafailov et al. *Direct Preference Optimization*. 2023. https://arxiv.org/abs/2305.18290
- [MENG24] Meng, Xia, & Chen. *SimPO*. NeurIPS 2024. https://proceedings.neurips.cc/paper_files/paper/2024/hash/e099c1c9699814af0be873a175361713-Abstract-Conference.html
- [SONG24] Song et al. *Preference Learning Algorithms Do Not Learn Preference Rankings*. NeurIPS 2024. https://openreview.net/forum?id=YkJ5BuEXdD
- [SDPO24] Chen et al. *Softmax-DPO*. 2024. https://arxiv.org/abs/2406.09215
- [ROSE24] Zhang et al. *RosePO*. 2024. https://arxiv.org/abs/2410.12519
- [RECPO26] Zhang et al. *What Makes LLMs Effective Sequential Recommenders?* ACL 2026. https://aclanthology.org/2026.acl-long.656/
- [CAUSAL26] *CausalDPO for Generative Recommendation*. 2026 preprint. https://arxiv.org/abs/2603.22335
- [JAIN22] Jain et al. *Stochastic Retrieval-Conditioned Reranking*. ICTIR 2022. https://research.google/pubs/stochastic-retrieval-conditioned-reranking/
- [SCHNABEL16] Schnabel et al. *Recommendations as Treatments*. ICML 2016. https://proceedings.mlr.press/v48/schnabel16.html
- [ANCEPRF21] Yu et al. *ANCE-PRF*. 2021. https://arxiv.org/abs/2108.13454
- [IPA26] *Succeeding at Scale: Index-Preserving Adaptation*. 2026 preprint. https://arxiv.org/abs/2601.04646
- [VEJENDLA25] Vejendla. *Drift-Adapter*. EMNLP 2025. https://aclanthology.org/2025.emnlp-main.805/
- [MOHONEY25] Mohoney et al. *Quake*. OSDI 2025. https://www.usenix.org/system/files/osdi25-mohoney.pdf
- [ONE25] *OneRec*. 2025 preprint. https://arxiv.org/abs/2502.18965
- [GRANK26] *GRank*. WWW 2026. https://arxiv.org/abs/2510.15299
- [ATSPEED25] *AtSpeed*. ICLR 2025. https://arxiv.org/abs/2410.05165
- [WANG25] Wang et al. *User Feedback Alignment for LLM-powered Exploration*. ACL Industry 2025. https://aclanthology.org/2025.acl-industry.70/
