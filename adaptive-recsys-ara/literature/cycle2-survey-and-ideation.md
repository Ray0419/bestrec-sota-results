# Phase 1, Cycle 2: Failure-Driven Survey and Ideation

**Trigger:** RIPPLE v1 failed G1, G2, G3, and G4. It rotated a text-only query space, improved a weak semantic top-10 score, but lost candidate recall and achieved only 18.1% of BPR-MF NDCG.

## Revised bottlenecks

### C2-L1 — Complementarity can become destructive interference

Semantic and collaborative signals fail differently. Parallel integration can preserve their complementary strengths, as Query-to-Recommendation reports [HAN25], while recent semantic–collaborative work explicitly argues against globally forcing the views into one representation. RIPPLE provides project-local evidence that replacing collaborative structure with semantic geometry is unsafe.

### C2-L2 — Preference optimization lacks a strong-baseline floor

SimPO and recommendation-specific variants optimize preference comparisons but do not guarantee non-degradation against a production collaborative ranker. Safe Policy Improvement with Baseline Bootstrapping falls back to the behavior policy in uncertain regions [LAROCHE19], but that theory targets batch RL, not a truncated recommendation union and a SimPO-derived residual ranker.

### C2-L3 — Preserving a rank is not the same as allowing justified rescue

FINEST anchors a recommender with rank-preserving regularization under perturbations [OH24]. Distillation and teacher anchoring are also mature. Pure imitation can suppress a semantic item that explicit feedback strongly supports, while unconstrained residual tuning can destroy BPR relevance. The missing interface is an explicit *regret budget* that permits preference exceptions but limits collaborative-score loss.

### C2-L4 — Candidate-set safety and ranking safety are different

Hybrid/multi-channel union retrieval is established [HAN25; MIC22]. Keeping every BPR candidate guarantees set inclusion, not NDCG or Recall@10 after reranking. A safe architecture needs both an immutable candidate-support invariant and statistically evaluated top-rank non-inferiority.

## Divergent pass: 13 successor directions

| ID | Direction | Creative lens | Collision boundary |
|---|---|---|---|
| C2-I01 | Anchor-and-augment SimPO | Preserve what failed, add what was missing | Hybrid/multi-vector retrieval is established; novelty needs a one-way support contract. |
| C2-I02 | Top-k feasibility projection | Turn a soft loss into a hard constraint | General constrained ranking is broad prior art. |
| C2-I03 | Quota-protected dual FAISS | Negate destructive fusion | Multi-channel quotas/fusion are occupied. |
| C2-I04 | Graph-diffused semantic codes | Bisociate graph smoothing and text | Collaborative-semantic fusion is crowded. |
| C2-I05 | Teacher-support distillation | Reframe BPR as a teacher | Ranking distillation and recommendation distillation are established. |
| C2-I06 | Mass-conserving OT-SimPO | Transport preference mass under floors | OT/diversity reranking is adjacent and costly. |
| C2-I07 | Signed attraction–repulsion retrieval | Encode dislikes as a retrieval view | Signed recommenders are established. |
| C2-I08 | Error-correcting retrieval views | Multiple views as redundancy codes | ANN ensembles increase serving cost. |
| C2-I09 | Collaborative coreset memory | Externalize support as memory | Classical item–item retrieval makes novelty weak. |
| C2-I10 | Cold/warm partitioned retrieval | Split the boundary condition | Standard cold-start hybrid architecture. |
| C2-I11 | Support-bootstrapped residual ranking | Safe-policy bisociation | SPIBB is prior art in RL; recommendation instantiation must be precise. |
| C2-I12 | High-confidence deployment selector | Invert optimization into hypothesis testing | Safe policy testing exists; alone it is not an algorithmic contribution. |
| C2-I13 | Baseline-regret-constrained semantic rescue | Janusian: preserve and override | Strongest whitespace, but must not overclaim a formal true-utility guarantee. |

## Convergent ranking

| Rank | Direction | Novelty | Fresh PoC feasibility | Impact | Latency/scale | Total /20 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | C2-I13 + I01: collaborative-regret-constrained anchor-and-augment | 4.5 | 4.7 | 4.9 | 4.2 | **18.3** |
| 2 | C2-I02: top-k feasibility projection in one hybrid index | 4.2 | 4.0 | 4.6 | 5.0 | **17.8** |
| 3 | C2-I11: support-bootstrapped residual ranking | 4.0 | 4.5 | 4.5 | 4.5 | **17.5** |
| 4 | C2-I06: mass-conserving OT-SimPO | 4.6 | 3.5 | 4.4 | 3.5 | **16.0** |

## Selected direction: CAPER

**CAPER — Coverage-Anchored Preference-Exception Reranking.**

CAPER uses two immutable FAISS branches: BPR collaborative factors and SentenceTransformer item metadata. Their union contains the complete BPR candidate set by construction. A bounded residual ranker is trained with a SimPO-derived, reference-model-free margin loss on explicit rating-gap pairs sampled from the actual served union. It focuses on *BPR contradictions*: cases where BPR ranks a lower-rated item above a higher-rated one.

At inference, a hard feasible-ranking projection admits semantic/preference swaps only while the cumulative loss in normalized BPR score remains below a preregistered per-request regret budget. Thus CAPER can rescue semantically supported items but cannot freely destroy the collaborative backbone. The budget bounds a BPR surrogate, not true user utility; true NDCG/Recall non-inferiority remains an empirical gate.

## Collision checks

- **Not novel:** dual semantic/collaborative retrieval or adaptive fusion; Query-to-Recommendation and multi-channel retrieval already cover these.
- **Not novel:** rank-preserving regularization; FINEST covers stabilization through reference ranks.
- **Not novel:** conventional-recommender preference oracles; RosePO and newer work use them.
- **Not novel:** SimPO or margin pairwise ranking.
- **Not claimed:** a formal safe-policy-improvement theorem for recommendation.
- **Targeted whitespace:** reference-free preference residual learning on the actual served hybrid union, coupled to a hard per-request collaborative-regret projection and an explicit candidate-support invariant.

## Fresh evaluation choice

Cycle 2 uses the unopened, stable MovieLens 1M benchmark, not the already opened MovieLens 100K test split. GroupLens documents one million ratings from roughly 6,000 users on 4,000 movies. The PoC uses only titles, genres, ratings, and timestamps; it excludes demographics.

## Primary sources added in cycle 2

- [HAN25] Han, Song, & Yi. *Rethinking LLM-Based Recommendations: A Personalized Query-Driven Parallel Integration*. Findings of EMNLP 2025. DOI 10.18653/v1/2025.findings-emnlp.446. https://aclanthology.org/2025.findings-emnlp.446/
- [LAROCHE19] Laroche, Trichelair, & Tachet des Combes. *Safe Policy Improvement with Baseline Bootstrapping*. ICML 2019. https://proceedings.mlr.press/v97/laroche19a.html
- [OH24] Oh et al. *FINEST: Stabilizing Recommendations by Rank-Preserving Fine-Tuning*. 2024. https://arxiv.org/abs/2402.03481
- [COPL25] Choi et al. *Collaborative Preference Learning for Personalizing LLMs*. EMNLP 2025. DOI 10.18653/v1/2025.emnlp-main.650. https://aclanthology.org/2025.emnlp-main.650/
- [RECPO26] Ouyang et al. *What Makes LLMs Effective Sequential Recommenders?* ACL 2026. DOI 10.18653/v1/2026.acl-long.656. https://aclanthology.org/2026.acl-long.656/
- [MIC22] *Multi-Interest-Aware User Modeling for Large-Scale Sequential Recommendations*. CIKM 2022. DOI 10.1145/3511808.3557081. https://arxiv.org/abs/2110.11570
- MovieLens 1M official benchmark page: https://grouplens.org/datasets/movielens/1m/
