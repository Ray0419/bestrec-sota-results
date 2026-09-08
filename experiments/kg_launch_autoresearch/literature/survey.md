# Literature Survey: Knowledge Graphs for Cold-Start Recommendation

Cutoff: 2026-08-07. Sources are primary papers or official proceedings pages.

## Mature algorithm families

- Embedding and multitask integration: MKR, KGCN, KGAT.
- Path reasoning: KPRN, PGPR, TPRec, TKGRec.
- Intent, geometry, and GNN propagation: KGIN, HAKG, LightKG.
- Denoising, contrastive learning, invariance, and diffusion: KGCL, KGRec, KRDN, DiffKG, KGIL.
- Strict cold and inductive models: MetaKG, ColdGPT, SimpleRec, Firzen.
- LLM-KG systems: CIKGRec, CoLaKG, K-RagRec, ColdRAG, SPiKE.

The architecture space is crowded. A new aggregator, contrastive view, temporal walker, or LLM description generator does not clear a Tier-A novelty bar by itself.

## Critical evidence

- KG4RecEval reports that removing, decreasing, or randomly distorting KG information often does not reduce recommendation accuracy, including its reported cold-user setting.
- Ji et al. show that ignoring the global timeline causes interaction and candidate leakage and can reverse model ordering, but they do not audit external KG fact availability.
- ColdGPT provides a real strict-ID-cold protocol, but filters metadata-poor items and constructs Home-SCS so that 2,867 test items introduce only one new attribute. This is mostly shared-vocabulary interpolation.
- Firzen randomly selects 20 percent of items as cold and constructs the graph from the completed benchmark; it is not a prospective launch cohort.
- ColdRAG core-filters data, labels the least frequent 10 percent as cold, and tests 500 sequences ending in a cold item. It is not zero-interaction strict launch.

## Qualified gap

No located work simultaneously requires:

1. a global prediction cutoff;
2. future-born, zero-precutoff-interaction items;
3. time-eligible full-catalog candidates;
4. item/entity links and relation edges observable by the cutoff;
5. launch-available metadata only; and
6. explicit evaluation of unlinked or weakly linked items.

This is a qualified literature-search conclusion, not a proof that no such paper exists.

## Core URLs

- KGAT: https://arxiv.org/abs/1905.07854
- KGIN: https://arxiv.org/abs/2102.07057
- KGCL: https://arxiv.org/abs/2205.00976
- MetaKG: https://arxiv.org/abs/2202.03851
- ColdGPT: https://arxiv.org/abs/2306.14462
- Firzen: https://arxiv.org/abs/2410.07654
- KG4RecEval: https://arxiv.org/abs/2404.03164
- ColdRAG: https://arxiv.org/html/2505.20773
- LightKG: https://arxiv.org/abs/2506.10347
- Timeline leakage study: https://doi.org/10.1145/3569930

