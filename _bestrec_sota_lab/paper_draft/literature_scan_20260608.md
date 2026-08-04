# Literature Scan For LC2C Retrieval LTR Draft

Date: 2026-06-08

This scan records the sources used to frame the first paper draft. It favors primary paper pages and official proceedings over secondary summaries.

## Core Cold-Start Baselines

- DropoutNet: NeurIPS 2017, "DropoutNet: Addressing Cold Start in Recommender Systems." The official proceedings page frames DropoutNet as a neural latent model explicitly trained for cold start through dropout and applicable on top of latent models. Source: https://papers.nips.cc/paper/7081-dropoutnet-addressing-cold-start-in-recommender-systems
- CLCRec: arXiv:2107.05315 / ACM Multimedia 2021, "Contrastive Learning for Cold-Start Recommendation." The paper models dependencies between item content and collaborative signals through contrastive learning. Source: https://arxiv.org/abs/2107.05315
- CCFCRec: arXiv:2302.02151 / WWW 2023, "Contrastive Collaborative Filtering for Cold-Start Item Recommendation." The paper targets blurry collaborative embeddings by contrasting content and co-occurrence CF modules. Source: https://arxiv.org/abs/2302.02151

## Text And Language-Item Retrieval

- BLaIR: arXiv:2403.03952, revised 2026 and listed as ACL 2026, "Bridging Language and Items for Retrieval and Recommendation: Benchmarking LLMs as Semantic Encoders." It introduces Amazon Reviews 2023 with over 570M reviews and 48M items and argues that general embedding benchmarks do not necessarily predict recommendation performance. Source: https://arxiv.org/abs/2403.03952
- ColdRAG: arXiv:2505.20773, "Adaptive Candidate Retrieval with Dynamic Knowledge Graph Construction for Cold-Start Recommendation." This is newer adjacent work using dynamic knowledge graphs and LLM-guided retrieval. It is useful context, but not yet a same-protocol baseline in our audit. Source: https://arxiv.org/abs/2505.20773

## Generative And Dense Retrieval

- TIGER: arXiv:2305.05065 / NeurIPS 2023, "Recommender Systems with Generative Retrieval." It predicts semantic item identifiers autoregressively and reports improved retrieval for items with no prior interaction history. Source: https://arxiv.org/abs/2305.05065
- LIGER: arXiv:2411.18814, "Unifying Generative and Dense Retrieval for Sequential Recommendation." It compares generative and dense retrieval and proposes a hybrid that improves cold-start item recommendation in evaluated datasets. Source: https://arxiv.org/abs/2411.18814
- Cold-start generative recommendation reproducibility: arXiv:2603.29845, "Cold-Starts in Generative Recommendation: A Reproducibility Study." This source is especially relevant to our reviewer framing because it highlights that cold-start gains can be hard to interpret when model scale, identifiers, and training strategy change together. Source: https://arxiv.org/abs/2603.29845

## Warm/General Recommendation Context

- iALS implicit feedback: Hu, Koren, and Volinsky, ICDM 2008. Source DOI: 10.1109/ICDM.2008.22
- MultiVAE: arXiv:1802.05814 / WWW 2018, "Variational Autoencoders for Collaborative Filtering." Source: https://arxiv.org/abs/1802.05814
- EASE: arXiv:1905.03375 / WWW 2019, "Embarrassingly Shallow Autoencoders for Sparse Data." Source: https://arxiv.org/abs/1905.03375
- LightGCN: arXiv:2002.02126 / SIGIR 2020, "LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation." Source: https://arxiv.org/abs/2002.02126

## Implication For This Paper

The draft should make a narrow, defensible claim:

- Strong claim: LC2C Retrieval LTR improves full-catalog zero-interaction cold-item ranking under the exact audited protocol.
- Weak/unsupported claim: broad recommender SOTA across warm-start or all LLM/RAG recommendation settings.
- Missing future comparator category: dynamic KG/LLM RAG cold-start systems such as ColdRAG, if a same-split full-catalog implementation is made available.
