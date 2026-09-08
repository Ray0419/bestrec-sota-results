# Phase 1, Cycle 3: Failure-Driven Survey and Ideation

**Trigger.** CAPER v1 failed its relevance, mechanism, preference-accuracy, and seed-stability gates. Its projected linear semantic-collaborative fusion was the relevance specialist (`0.064846` NDCG@10), while its uniformly sampled natural-pair residual was the preference specialist (`0.636662` user-macro pair accuracy). Applying either preference residual globally could not retain both strengths.

This cycle used the brainstorming and creative-thinking procedures again: extract the strongest empirical contradiction, generate mechanisms under multiple lenses, perform an explicit prior-art collision scan, and only then converge. All analyses of CAPER's opened cohort below are hypothesis-generating; the successor is evaluated on a prospectively selected, disjoint user cohort.

## Revised bottlenecks

### C3-L1 — Pairwise preference quality does not identify safe list interventions

The uniform residual was a better held-out pair discriminator than both BPR and linear fusion, yet it reduced NDCG when applied to every candidate. K-order preference optimization and ordinary pairwise/listwise learning already study preference aggregation, so the missing systems interface is narrower: determine when a learned pair signal should be permitted to modify a strong list and when it should abstain.

### C3-L2 — Global fusion assumes that complementary experts help on the same requests

Semantic, collaborative, and preference experts have request-dependent errors. Mixture-of-experts, personalized reranking, MMoE, PLE, and recent semantic-collaborative gates already establish adaptive fusion. CAPER's exploratory opened-cohort analysis nevertheless exposes a sharper failure mode: linear and uniform rankings tied on per-user NDCG in `77.7%` of seed-user rows, preference and relevance deltas had only `r=0.076` correlation, and uniform alignment improved preference without an observed NDCG loss in `23.8%` of pair-bearing rows. The research problem is therefore not generic fusion; it is one-sided permission for an already-trained correction relative to an unchanged default expert.

### C3-L3 — Reliability calibration does not transfer automatically to temporal recommendation

SelectiveNet, ranking with abstention, and conformal risk-control methods already formalize risk-coverage trade-offs. Recommendation-specific work provides distribution-free FDR control and two-stage retrieval/ranking calibration. Those guarantees rely on assumptions that a per-user temporal MovieLens split does not establish. A successor must use strictly prior validation feedback, report risk, coverage, conditional uplift, and harmful interventions, and say *validation-calibrated* or *empirically conservative*—not conformal, distribution-free, or guaranteed safe.

### C3-L4 — Exact fallback is different from a jointly trained gate, but its novelty boundary is narrow

Selective LLM-Guided Regularization (S-LLMR) already gates within-user pairwise LLM guidance during training, while GateSID and mature recommender MoE methods gate semantic/collaborative signals. SPIBB and robust counterfactual ranking already use baseline fallback or constrain policy deviation. Defensible whitespace, if confirmed empirically, is a post-training, inference-time selector over a frozen hybrid and a separately trained reference-free residual, with exact identity fallback and no catalog re-embedding, index mutation, or online LLM call.

## Divergent pass: 13 successor directions

| ID | Direction | Failure-driven mechanism | Collision boundary |
|---|---|---|---|
| C3-I01 | Calibrated selective preference exceptions | Default to linear fusion; allow a trained residual only on validated low-risk requests | Generic abstention, learning-to-defer, and S-LLMR are occupied; novelty must be post-training one-sided intervention with exact fallback |
| C3-I02 | Near-tie preference resolver | Apply preference evidence only inside a linear-score indifference band | Local reranking and near-tie methods are mature; useful as a control or eligibility constraint |
| C3-I03 | Pair-to-list constrained tournament | Aggregate residual pair edges only inside certified local components | Pairwise/listwise LTR and K-order preference optimization are close |
| C3-I04 | Relevance-shell lexicographic ranking | Optimize preference only among lists equivalent under a relevance uncertainty shell | Lexicographic and Pareto reranking are occupied; shell construction would carry the contribution |
| C3-I05 | Orthogonal preference residual | Project preference updates into a local null space of the base top-k score | Gradient surgery and rank-preserving fine-tuning create a substantial collision |
| C3-I06 | User-regime routing | Route collaborative-stable, semantic-rescue, and preference-correctable users | Personalized fusion and MoE make novelty weak without one-sided semantics |
| C3-I07 | Doubly robust swap uplift | Treat each proposed swap as a treatment and require a positive lower bound | Causal/off-policy recommendation is established; MovieLens lacks logged propensities |
| C3-I08 | Agreement-first SimPO | Favor natural pairs already compatible with relevance | FocalPO is a close collision; retain only as an ablation |
| C3-I09 | Two-timescale alignment | Separate transient relevance from stable preference | Short/long-term interest models and RecPO are adjacent |
| C3-I10 | Substitute-only correction | Permit swaps only between semantically interchangeable items | Category-aware and constrained reranking are established |
| C3-I11 | Personalized Pareto selection | Generate and route over relevance-preference frontier points | PE-LTR, PMORS, and related multiobjective recommenders occupy the core idea |
| C3-I12 | Exposure-debiased uniform alignment | IPS/DR-weight preference pairs before residual training | Recommendations-as-Treatments and off-policy correction occupy the mechanism |
| C3-I13 | Adaptive margin by intensity/recency | Condition SimPO margin on rating gap and age | RecPO directly occupies this direction |

## Convergent ranking

| Rank | Direction | Novelty boundary | PoC feasibility | Expected impact | Latency fit | Total /20 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | C3-I01 + I02: validation-gated exceptions with near-tie eligibility | 4.2 | 4.8 | 4.8 | 4.8 | **18.6** |
| 2 | C3-I03: pair-to-list constrained tournament | 4.4 | 3.5 | 4.6 | 4.1 | **16.6** |
| 3 | C3-I07: doubly robust swap uplift | 4.5 | 2.1 | 4.9 | 3.8 | **15.3** |
| 4 | C3-I05: orthogonal preference residual | 3.5 | 3.3 | 4.2 | 4.0 | **15.0** |

## Selected direction: RAVEL

**RAVEL — Residual Alignment via a Validation-gated Exception Layer.**

RAVEL retains the validation-selected projected linear hybrid as an exact default. It trains a separate uniform natural-pair SimPO residual on an earlier temporal block. A target-blind request descriptor and an out-of-fold validation procedure estimate whether applying that already-trained residual is likely to improve explicit pair decisions without material relevance loss. At inference, the residual may act only on eligible near-tie candidates and only when the selector accepts; rejection returns the linear hybrid identically.

The closest analogy is learning to defer with the direction reversed: the reliable fixed ranker is the default, and the preference expert must earn permission to intervene. RAVEL does **not** claim novelty for gating, abstention, hybrid retrieval, SimPO, or fallback individually.

## Collision-safe claim boundary

- **Not novel:** selective prediction, a reject option, risk-coverage curves, or a learned router.
- **Not novel:** semantic-collaborative gating, personalized reranking, or multiobjective scalarization.
- **Not novel:** LLM-derived or pairwise margin regularization; S-LLMR already combines both with a reliability gate.
- **Not claimed:** conformal validity, distribution-free guarantees, causal uplift, formal policy safety, or a Pareto theorem.
- **Candidate whitespace:** post-training selection of a separately trained reference-free residual over a frozen linear semantic-collaborative ranker, with exact identity fallback, temporally prior empirical calibration, immutable dual-vector indexes, and intervention-specific evaluation.

## Required controls and measurements

The PoC must compare RAVEL with the frozen projected linear hybrid, always-on residual, near-tie-only residual, uncertainty-only residual, a one-head post-training selector, and a deterministic matched-coverage random gate. It must report overall NDCG/Recall, explicit pair accuracy, intervention coverage, conditional uplift, harmful-intervention rate, regret, dislike intrusion, latency, and exact-fallback checks. A truly jointly trained gate belongs in the scaled study: pretending that a validation-trained combined-label head was jointly optimized with the residual would be an invalid control.

## Primary sources added in cycle 3

- Geifman & El-Yaniv. *SelectiveNet: A Deep Neural Network with an Integrated Reject Option*. ICML 2019. https://proceedings.mlr.press/v97/geifman19a.html
- Mao, Mohri, & Zhong. *Learning to Defer to a Set of Experts*. ICML 2025. https://proceedings.mlr.press/v267/mao25c.html
- *Ranking with Abstention*. 2023. https://arxiv.org/abs/2307.02035
- Angelopoulos et al. *Recommendation Systems with Distribution-Free Reliability Guarantees*. UAI 2023. https://proceedings.mlr.press/v204/angelopoulos23a.html
- Angelopoulos et al. *Conformal Risk Control*. ICLR 2024. https://openreview.net/forum?id=33XGfHLtZg
- Xu et al. *Two-stage Risk Control with Application to Ranked Retrieval*. IJCAI 2025. https://www.ijcai.org/proceedings/2025/1012
- Yang et al. *Selective LLM-Guided Regularization for Recommendation*. WSDM GenAIRecP 2026. https://genai-personalization.github.io/assets/papers/GenAIRecP2026/Selective_LLM_Guided_Regularization.pdf
- *GateSID: Adaptive Gating of Semantic and Collaborative Signals*. 2026 preprint; treated only as a priority alert. https://arxiv.org/abs/2603.22916
- Ma et al. *Modeling Task Relationships in Multi-task Learning with Multi-gate Mixture-of-Experts*. KDD 2018. https://doi.org/10.1145/3219819.3220007
- Tang et al. *Progressive Layered Extraction*. RecSys 2020. https://doi.org/10.1145/3383313.3412236
- Lin et al. *Pareto-Efficient Learning to Rank*. RecSys 2019. https://doi.org/10.1145/3298689.3346998
- *PMORS: Personalized Multi-Objective Recommender System*. CIKM 2024. https://doi.org/10.1145/3627673.3680080
- Laroche et al. *Safe Policy Improvement with Baseline Bootstrapping*. ICML 2019. https://proceedings.mlr.press/v97/laroche19a.html
- *Practical and Robust Safety Guarantees for Advanced Counterfactual Learning to Rank*. CIKM 2024. https://doi.org/10.1145/3627673.3679531
- Zhao et al. *FocalPO: Efficient Preference Alignment via Correctly Ranked Preference Pairs*. ACL 2025. https://aclanthology.org/2025.acl-short.21/
- *K-order Ranking Preference Optimization*. Findings of ACL 2025. https://aclanthology.org/2025.findings-acl.250/
