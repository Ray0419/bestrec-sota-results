# H6/H7 Novelty Audit: Transaction-Time KG Drift and Certified Residuals

Audit date: 2026-08-07

Status: qualified literature-search conclusion through the audit date; absence
of a located paper is not proof of priority.

## Binary claim audit

The audit did **not** locate a paper combining all four defining axes:

1. external-KG transaction-time or version provenance;
2. a strict cold-start recommendation target;
3. an exact Top-K or pairwise-margin certificate over correlated,
   provenance-consistent revisions; and
4. a residual that is activated, shrunk, or rejected by that certificate.

| Candidate claim | Binary verdict | Defensible interpretation |
| --- | --- | --- |
| **H6 snapshot-ranking diagnostic** | **YES, qualified** | A controlled evaluation package that holds the recommender and candidate set fixed while intervening only on an external KG's as-of snapshot, then tests cold-item score/order/Top-K consequences against relation/degree-matched nulls. |
| H6 is the first temporal or point-in-time recommender | **NO** | Temporal recommendation and point-in-time graph training are occupied. |
| H6 is an algorithm contribution by itself | **NO** | It is a diagnostic/benchmark contribution unless it unlocks and validates H7. |
| The H7 min-weight-closure/min-cut solver is new | **NO** | Maximum closure, causal down-sets, and partial-order Top-K are established mathematics. |
| H7A page-chain interval certificate is a Tier-A algorithm by itself | **NO** | With independent page-prefix uncertainty and a separable score, each page compiles to a scalar interval; online certification is standard interval-robust linear Top-K arithmetic. Revision histories can still provide tighter extrema and real witnesses. |
| **H7B materialization-lineage certificate package** | **YES, qualified** | The surviving stronger hypothesis requires measured stream partitions, consumer offsets, or real computational prerequisite lineage, then combines provenance-consistent ideals, exact worst additive recommendation margins, exact Top-K membership, and certificate-triggered KG residual control. |

Here, `YES, qualified` means "no exact collision found in this search," not a
priority proof. A positive empirical result still requires a reproducible
systematic review and author-level related-work check before submission.

## Nearest 2024--2026 collisions

| Work | Exact publication | Collision and remaining distinction |
| --- | --- | --- |
| GraphMatch | [*GraphMatch: Fusing Language and Graph Representations in a Dynamic Two-Sided Work Marketplace*](https://proceedings.mlr.press/v322/sacha26a.html), UniReps workshop, PMLR 322, 2026 | Uses point-in-time subgraph training and historical feature reconstruction for recommendation. It blocks a broad point-in-time novelty claim, but does not model external-KG revision provenance or certify Top-K membership. |
| ColdRAG | [*Cold-Start Recommendation with Knowledge-Guided Retrieval-Augmented Generation*](https://arxiv.org/abs/2505.20773), arXiv:2505.20773, 2025 preprint | Dynamically builds a domain KG and ranks cold items with evidence-grounded LLM retrieval. It lacks source-version provenance and formal ranking guarantees. |
| DCKG | [*Meta-Learning on Dynamic Node Clustering Knowledge Graph for Cold-Start Recommendation*](https://doi.org/10.1016/j.neucom.2024.128192), *Neurocomputing* 602, 2024, DOI `10.1016/j.neucom.2024.128192` | Directly occupies dynamic-KG cold-start recommendation, but "dynamic" means learned node clustering/aggregation rather than transaction-time source revisions; it provides no certificate. |
| TKGRec | [*Temporal Knowledge Graph Recommendation with Sequence-Aware and Path Reasoning*](https://doi.org/10.1016/j.datak.2025.102522), *Data & Knowledge Engineering* 161, 2026, DOI `10.1016/j.datak.2025.102522` | Integrates interaction timestamps with sequence and path reasoning. Its time axis is user interaction/preference time, not transaction-time versions of an external KG; it has no certificate. |
| SKGRec | [*SKGRec: Unifying Temporal Dynamics and Knowledge Graphs for Robust Recommendations*](https://doi.org/10.1016/j.eswa.2025.129354), *Expert Systems with Applications* 297A, 2026, DOI `10.1016/j.eswa.2025.129354` | Combines temporal social dynamics, KG semantics, contrastive learning, and distillation. It does not use source revision histories or exact ranking certificates. |
| DRAR | [*DRAR: Diffusion-Based Relation Augmentation for Knowledge-Aware Recommendation*](https://doi.org/10.1145/3787454), *ACM Transactions on Information Systems* 44(5), 2026, DOI `10.1145/3787454` | Handles interaction noise and irrelevant KG connections by diffusion and relation augmentation. It has neither transaction-time uncertainty nor exact downstream certification. |
| Robust KGE via denoising | [*Robust Knowledge Graph Embedding via Denoising*](https://doi.org/10.1007/978-3-032-25156-5_22), ESWC 2026, pp. 417--435, DOI `10.1007/978-3-032-25156-5_22` | Gives randomized-smoothing robustness metrics for perturbed KGE embeddings. It is not recommendation, revision provenance, or an exact Top-K certificate. |
| PROV-STAR traceability | [*Full Traceability and Provenance for Knowledge Graphs*](https://doi.org/10.3233/FAIA241309), FOIS 2024, pp. 223--237, DOI `10.3233/FAIA241309` | Tracks triple-level changes with provenance and reconstructs arbitrary past KG versions. It blocks novelty for KG change provenance/version recovery itself, but has no recommendation or certificate. |
| CascadeKG | [*Risk-Controlled Event-Driven Cascading Updates for Knowledge Graph Consistency Restoration*](https://doi.org/10.18653/v1/2026.findings-acl.2111), Findings of ACL 2026, DOI `10.18653/v1/2026.findings-acl.2111` | Models dependency-aware KG update cascades and conformal coverage. It does not optimize over version-consistent down-sets or certify recommendation ranks. |
| AGNNCert | [*AGNNCert: Defending Graph Neural Networks against Arbitrary Perturbations with Deterministic Certification*](https://www.usenix.org/conference/usenixsecurity25/presentation/li-jiate), USENIX Security 2025 | Gives deterministic certificates for edge, node, and feature perturbations in node/graph classification. It lacks KG provenance, recommendation, and the proposed fallback. |
| Exact GNN label certification | [*Exact Certification of (Graph) Neural Networks Against Label Poisoning*](https://proceedings.iclr.cc/paper_files/paper/2025/hash/401aa72e0e3be680348a5b0ffdb1a5aa-Abstract-Conference.html), ICLR 2025 | Uses an exact MILP certificate for label poisoning. It concerns training-label attacks and classification rather than source revisions and Top-K recommendation. |
| RobustMask | [*RobustMask: Certified Robustness against Adversarial Neural Ranking Attack via Randomized Masking*](https://arxiv.org/abs/2512.23307), arXiv:2512.23307, 2025 preprint | Certifies pairwise and Top-K neural ranking under text perturbations. It blocks "first certified Top-K ranker," but has no KG, transaction-time provenance, or cold-start residual. |
| Node-aware bi-smoothing | [*Node-Aware Bi-Smoothing: Certified Robustness against Graph Injection Attacks*](https://doi.org/10.1109/SP54263.2024.00241), IEEE S&P 2024, DOI `10.1109/SP54263.2024.00241` | Includes a recommender application and certified graph-injection robustness. It uses randomized smoothing against injected nodes, not correlated transaction-time revisions or an exact additive-margin certificate. |
| KG4RecEval | [*KG4RecEval: Does Knowledge Graph Really Matter for Recommender Systems?*](https://doi.org/10.1145/3713071), *ACM Transactions on Information Systems* 43(3), 2025, DOI `10.1145/3713071` | Tests KG removal and random corruption, including cold-start settings. It motivates H6's matched-null audit but does not use observed source histories or certify rankings. |
| EUMR | [*Embedding Uncertainty Modeling for Cold-Start Item Recommendation*](https://doi.org/10.1016/j.neucom.2025.132144), *Neurocomputing* 665, 2026, DOI `10.1016/j.neucom.2025.132144` | Supplies a model-agnostic uncertainty module for distribution-shifted cold items. Its Gaussian embedding uncertainty is empirical rather than a version-provenance set with an exact certificate. |
| RankDist | [*A Rank-Based Approach to Recommender System's Top-K Queries with Uncertain Scores*](https://doi.org/10.1145/3709655), *Proceedings of the ACM on Management of Data* 3(1), SIGMOD 2025, DOI `10.1145/3709655` | Computes item-position probabilities from uncertain score distributions and proves expected-quality optimality for rank-based recommendation. It blocks a broad claim to be the first uncertainty-aware Top-K recommender; H7 instead uses a provenance-constrained set of feasible graph versions and certifies worst-case membership exactly rather than optimizing expectation under score distributions. |
| CertDR | [*Certified Robustness to Word Substitution Ranking Attack for Neural Ranking Models*](https://doi.org/10.1145/3511808.3557256), CIKM 2022, DOI `10.1145/3511808.3557256` | Defines certified Top-K robustness for a ranker and protects selected-versus-unselected membership using randomized smoothing. It blocks novelty for Top-K-set certification itself; the remaining distinction is the external-KG version fault model and exact provenance witness. |
| GUIDER | [*GUIDER: Uncertainty Guided Dynamic Re-ranking for Large Language Models Based Recommender Systems*](https://doi.org/10.1609/aaai.v40i19.38639), AAAI 2026, pp. 16049--16057 | Uses predictive-uncertainty decomposition to dynamically adapt recommendation ranking. It blocks generic uncertainty-controlled reranking novelty, but has no KG revision provenance or exact invariance certificate. |
| K-RagRec | [*Knowledge Graph Retrieval-Augmented Generation for LLM-based Recommendation*](https://arxiv.org/abs/2501.02226), ACL 2025 | Retrieves up-to-date structured KG information to augment LLM recommendation. It blocks a broad up-to-date KG retrieval claim, but does not model source revision fault sets or certify a recommendation list. |
| X-KGRank | [*X-KGRank: A Knowledge Graph RAG Framework for Explainable Recommendations via Pattern Mining and LLM Re-Ranking*](https://arxiv.org/abs/2608.01732), arXiv:2608.01732, 2026 preprint | Selectively routes long-tail items through KG paths before LLM reranking. It blocks selective KG routing for long-tail items as novelty; it lacks transaction-time provenance and a worst-case certificate. |

The closest recent works each cover one or two axes, not the four-way
intersection. In particular, no located work makes a certificate result itself
route an additive external-KG residual. This is the most specific surviving
novelty statement; claims such as "first temporal KG recommender," "first
robust KG recommender," "first use of KG provenance," "first cold-start
uncertainty module," "first certified recommender," or "first certified Top-K
ranker" are false.

## Surviving research question

For cold-start recommendation at cutoff `tau`, can a plug-in KG residual use
only pre-cutoff revision provenance to define admissible external-KG versions,
certify Top-K membership across those versions, and selectively shrink the KG
contribution when a list is uncertified, improving worst-snapshot accuracy and
stability without sacrificing point-in-time accuracy?

The potentially defensible contribution is the package:

1. a held-fixed external-KG transaction-time leakage audit;
2. a provenance-constrained graph uncertainty set based on actual revision
   histories or correlated edit groups;
3. an exact downstream pairwise/Top-K certificate for an additive KG residual;
4. a certificate-triggered residual gate for strict cold items; and
5. full-catalog, point-in-time and worst-snapshot evaluation.

No located paper combined all five. None of the components alone is new.

## Binding collisions

- Dynamic or temporal KG recommendation is occupied by TPRec, TKG-SRec,
  SKGRec, MTRDKG, DynaKG, and TKGRec. These mainly temporalize interaction,
  preference, social, path, or event signals; that distinction does not make a
  generic new temporal encoder novel.
- Generic noisy-KG invariance is occupied by
  [KGIL](https://openreview.net/forum?id=R7m416IMZj),
  [KGCL](https://arxiv.org/abs/2205.00976), and
  [KRDN](https://arxiv.org/abs/2304.14987).
- Generic graph-recommender distributional robustness is occupied by
  [DR-GNN](https://arxiv.org/abs/2402.12994),
  [TDRO](https://ojs.aaai.org/index.php/AAAI/article/view/28721), and
  [DRGO](https://arxiv.org/abs/2501.15555).
- Generic recommender certificates are occupied by
  [PORE](https://www.usenix.org/conference/usenixsecurity23/presentation/jia)
  and [node-aware bi-smoothing](https://arxiv.org/abs/2312.03979).
- Uncertain-score recommendation and probabilistic rank semantics are occupied
  by [RankDist](https://doi.org/10.1145/3709655) and the older uncertain-database
  Top-K literature. H7 must claim neither the first uncertain recommender nor
  the first possible-world ranking method; its distinction is exact worst-case
  certification over provenance-consistent revision histories.
- Certified Top-K-set invariance is occupied by
  [CertDR](https://doi.org/10.1145/3511808.3557256), while uncertainty-guided
  dynamic reranking and selective KG routing are occupied by
  [GUIDER](https://doi.org/10.1609/aaai.v40i19.38639),
  [K-RagRec](https://arxiv.org/abs/2501.02226), and
  [X-KGRank](https://arxiv.org/abs/2608.01732). A certificate-triggered residual
  is therefore defensible only as part of the full provenance-constrained
  package, not as a routing contribution in isolation.
- Generic structural graph certificates are occupied by
  [certifiable robustness to graph perturbations](https://papers.neurips.cc/paper_files/paper/2019/hash/e2f374c3418c50bc30d67d5f7454a5b4-Abstract.html)
  and [certified robust graph contrastive learning](https://arxiv.org/abs/2310.03312).
- Bitemporal KG models and revision reconstruction are established by
  [Time-Aware Probabilistic Knowledge Graphs](https://doi.org/10.4230/LIPIcs.TIME.2019.8)
  and [Wikidated](https://arxiv.org/abs/2112.05003).
- [KG4RecEval](https://doi.org/10.1145/3713071) already tests KG removal and
  random corruption and often finds little accuracy loss. A matched random
  perturbation baseline is therefore mandatory.
- [MIND](https://aclanthology.org/2020.acl-main.331/) includes Wikidata-linked
  entities, triples, and TransE embeddings but does not document a point-in-time
  Wikidata revision for each impression.

Consequently, do not claim novelty for temporal KG recommendation, stable
intersection, snapshot ensembling, confidence gating, DRO, graph robustness,
or certification in isolation.

## Candidate module: TxKG-Cert / Bitemporal Budgeted Robust Residual

Let a graph-independent base score be `b(u,i)`. Split facts for item `i` into
facts `K_i` definitely observable by the cutoff and frontier facts `U_i` whose
transaction-time state is unresolved. Use an edge-additive residual

`s(u,i;z) = b(u,i) + p_u^T h_i^K + sum_{e in U_i} z_e p_u^T v_e`,

where `z_e` is binary, persistent terms are cached, and `v_e` is a small
relation-conditioned contribution. Partition uncertain edges into
source-by-relation or observed edit-batch blocks `b`, with provenance-derived
cardinality bounds

`L_b <= sum_{e in b} z_e <= U_b`.

For a positive/negative pair, merge shared edge variables and write

`m(z) = m_K + sum_b sum_{e in b} z_e c_e`.

Within each block sort contributions
`c_(1) <= ... <= c_(M)`. If `n_-` is the number of negative contributions, the
minimizing admissible cardinality is

`k_b = min(U_b, max(L_b, n_-))`,

so the exact worst-case margin is

`m_lower = m_K + sum_b sum_{r=1}^{k_b} c_(r)`.

### Guarantee

For every graph satisfying the block bounds, `m(z) >= m_lower`. Therefore
`m_lower > 0` certifies the pairwise order under every admissible graph. A
nominal Top-K set is certified when every selected-versus-unselected robust
margin is positive. Robust BPR trains with `softplus(-m_lower)`.

This is exact for the edge-separable residual and costs
`O(|U| log |U|)` by sorting, or linear time with selection. It avoids repeated
GNN encoding and can serve as a small reranking module.

The narrow novelty hypothesis is not the algebraic robust margin. It is the
combination of transaction-time-derived, correlated source/relation/edit-group
constraints with a downstream cold-start ranking certificate and selective KG
residual.

The current H7A proof-of-concept deliberately does **not** yet instantiate the
correlated case. Under its conservative product of independently stale page
prefixes, an event-additive score compiles each page chain to an exact scalar
minimum and maximum, after which certification is interval arithmetic. H7A can
test whether real revision states materially tighten bounds over an
independent-fact mask and can return auditable revision witnesses, but it is a
mechanism study rather than a standalone poset algorithm. The stronger H7B
claim below is unlocked only by measured cross-stream partitions, consumer
checkpoints, or real materialization-task lineage.

## Preferred stronger variant: revision-poset certificate

Actual revision histories provide more structure than an unordered
cardinality budget. Let each atomic edit event `e` have a signed additive
increment `c_e` to a held-fixed pairwise recommendation margin. If `e < f`
means that edit `f` can occur only after `e`, then every feasible incomplete
history is a down-set (order ideal) of the free edit poset after definitely-in
and definitely-out events are fixed. The exact adverse margin is

`m_lower = m_0 + min_{I is an ideal} sum_{e in I} c_e`.

This is a minimum-weight closure problem. Equivalently negate the weights and
solve a maximum closure with an `s-t` min-cut, using an infinite-capacity arc
from each dependent edit to its prerequisite. For a single revision chain it
reduces to one prefix scan:

`m_lower = m_0 + min_t sum_{r <= t} c_r`.

The causal constraint can make a certificate much less vacuous than arbitrary
masking. For event increments `(+100,-90,-90)`, the worst feasible prefix is
`-80`; an unconstrained two-edge adversary incorrectly selects both negative
events and reports `-180`. A nominal Top-K set is invariant in every feasible
history exactly when every selected-versus-unselected worst-case margin is
strictly positive. A failed strict inequality is uncertified, and the min-cut
itself supplies an interpretable adverse version witness.

The closure/min-cut result is classical and **not** a novelty claim; see
[Picard, *Maximal Closure of a Graph and Applications to Combinatorial
Problems* (1976)](https://doi.org/10.1287/mnsc.22.11.1268), DOI
`10.1287/mnsc.22.11.1268`. Consistent global snapshots in distributed systems
already use causal down-sets and network-flow optimization; see Chen and Wu,
[*On the Complexity of the Minimum and Maximum Global Snapshot
Problems*](https://doi.org/10.1109/CMPSAC.1997.624733), COMPSAC 1997, DOI
`10.1109/CMPSAC.1997.624733`, and its *Information Processing Letters* version,
DOI [`10.1016/S0020-0190(98)00100-8`](https://doi.org/10.1016/S0020-0190(98)00100-8).
Partial-order and uncertain-database Top-K are also mature; see Amarilli et al.,
[*Top-k Querying of Unknown Values under Order Constraints*](https://doi.org/10.4230/LIPIcs.ICDT.2017.5),
ICDT 2017, DOI `10.4230/LIPIcs.ICDT.2017.5`, and Mouratidis and Tang,
[*Exact Processing of Uncertain Top-k Queries in Multi-Criteria
Settings*](https://doi.org/10.14778/3204028.3204031), PVLDB 2018, DOI
`10.14778/3204028.3204031`.
The 2026 [risk-controlled cascading KG-update framework](https://aclanthology.org/2026.findings-acl.2111/)
is a further near boundary because it models dependency-aware update cascades
with conformal guarantees, although it does not certify downstream
recommendation ranks across transaction-time-consistent versions.

The remaining candidate contribution is therefore only the package:
revision-provenance-consistent cuts, exact downstream cold-start Top-K margins,
and a certificate-triggered additive KG residual. It requires an exactly
event-additive residual. Normalized embeddings, degree recomputation, arbitrary
cardinality constraints, mutually exclusive edits, and nonlinear message
passing do not inherit the one-min-cut theorem. If the cutoff and every
transaction timestamp are already known, exact replay dominates this module.
Likewise, routing or abstaining on uncertainty is not independently new; reject
option theory already formalizes this behavior, for example
[*Optimal Strategies for Reject Option Classifiers*](https://jmlr.org/papers/v24/21-0048.html),
JMLR 2023. Only the use of this specific exact revision certificate to control
an additive external-KG residual remains a defensible routing claim.

## Conditional H8 fallback: revision-circulation residual

**Binary verdict: CONDITIONAL KEEP as a cheap third pivot; NO to broad Hodge,
cycle, simplicial, or basis-invariant graph-learning novelty.** The closest
collision is already an inductive KG cycle model, and cycle projectors are
established. The only surviving formulation is narrower: turn signed
transaction-time KG revisions into a conserved cycle-space signal and use it
as an untuned residual/router for strict cold-start ranking.

On the union anchor--fact graph, orient the vertex--edge incidence matrix `B`
and encode historical-to-current triple changes as an edge signal `d`, with
positive additions and negative deletions. Define

`P_C = I - B^T (B B^T)^dagger B` and `h = P_C d`.

For anchor weights `u`, candidate-fact features `z_i`, and masked edge query
`q_(u,i),(a,f) = u_a z_(i,f)`, use the normalized residual

`r(u,i) = <h,q_(u,i)> / (||h|| ||P_C q_(u,i)||)`.

This residual is basis-invariant, bounded by one in magnitude, and exactly zero
when the edited graph is a forest or the edit signal is a node-potential flow
in `im(B^T)`. It therefore isolates non-node-separable coupled revision
structure rather than repeating a degree or entity-frequency feature. The
anchor--fact graph is bipartite and triangle-free, however, so it admits only a
gradient plus harmonic-cycle decomposition. A three-way
gradient/curl/harmonic claim would be mathematically false.

Binding collisions are:

- [*Statistical Ranking and Combinatorial Hodge Theory*](https://doi.org/10.1007/s10107-010-0419-x),
  *Mathematical Programming* 127, 2011, DOI
  `10.1007/s10107-010-0419-x`, for Hodge decomposition of ranking edge flows;
- [*Cycle Representation Learning for Inductive Relation Prediction*](https://proceedings.mlr.press/v162/yan22a.html),
  ICML 2022, for cycle-basis GNNs in inductive KG completion;
- [*Cycle Invariant Positional Encoding for Graph Representation Learning*](https://proceedings.mlr.press/v231/yan24b.html),
  Learning on Graphs 2023 proceedings, PMLR 231, published 2024, for the
  basis-invariant cycle-space projector used by CycleNet;
- [*How Does Topology Bias Distort Message Passing in Graph Recommender? A
  Dirichlet Energy Perspective*](https://proceedings.neurips.cc/paper_files/paper/2025/hash/40b5237c3e025c72c02dd8b6716dac76-Abstract-Conference.html),
  NeurIPS 2025, for test-time simplicial propagation in recommendation; and
- [*HLSAD: Hodge Laplacian-Based Simplicial Anomaly Detection*](https://doi.org/10.1145/3711896.3736998),
  KDD 2025, DOI `10.1145/3711896.3736998`, for Hodge-based change detection in
  evolving complexes.

[DBpedia-TKG](https://doi.org/10.5281/zenodo.14532571) additionally establishes
that transaction-time KG revision data itself is available. No located paper
feeds the harmonic component of signed source revisions into a cold-start
ranker, but this narrow combination has only moderate novelty confidence and
low pre-result Tier-A confidence.

A label-blind structural POC found genuine geometry after the H6 metadata and
hub exclusions: current-only edits retained cycle rank `beta_1 = 39`, whereas
historical-only edits had `beta_1 = 0`. This shows that the residual is not
identically zero; it does **not** show recommendation value. Do not inspect
outcomes or advance the branch unless a preregistered no-tune test also passes
all of these gates:

- harmonic energy `||h||^2 / ||d||^2 >= 0.10` and above the 95th percentile of
  999 deterministic relation-, sign-count-, and degree-bin-preserving edit
  placement nulls;
- `||B h||_infinity <= 1e-10` and independent solver/basis replay agreement;
- a fixed equal-energy blend changes at least 20% of score vectors; and
- it changes at least 5% of complete candidate orders or 2% of Top-10 lists
  under the existing deterministic tie rule.

Failing any gate eliminates H8. Current confidence is approximately `0.65`
that the exact narrow combination is unoccupied and only `0.30` that it can
support a Tier-A paper before ranking evidence. It is therefore a fallback,
not the lead contribution.

## Identifiability limit

If two KG histories share the same current snapshot but have different cutoff
graphs, any method observing only the current snapshot emits the same score
vector for both. For true score vectors `s_0` and `s_1`, every such estimator
must satisfy

`max(||s_hat-s_0||_inf, ||s_hat-s_1||_inf) >= 0.5 ||s_0-s_1||_inf`.

Exact point-in-time reconstruction therefore dominates whenever all required
transaction timestamps are available. TxKG-Cert is justified for missing,
lagged, batched, or otherwise unresolved provenance—not as a replacement for
an available exact as-of join.

## Evidence and gates

H5 supplies problem evidence only: on the fixed MIND top-50 sample, 24.9421%
of news-frequency-weighted present facts were absent at the 2019 cutoff. The
rate remained 23.7184% inside MIND's 1,091-relation vocabulary. This does not
establish ranking impact or algorithm value.

H6 must first pass its separately committed label-blind rank-coverage gate and
then its held-fixed outcome gate. Only then may a TxKG-Cert POC open.

For that follow-on POC, compare entity/content-only, exact historical oracle,
current plug-in, persistent intersection, snapshot averaging, actual-snapshot
margin invariance, and the robust residual. Advance only if the residual:

- improves worst-snapshot nDCG@10 by at least 0.005 over every non-oracle
  baseline;
- reduces snapshot-induced Top-10 changes by at least 30 percent;
- retains at least 90 percent of historical-oracle KG gain over the base;
- adds less than 15 percent reranking latency; and
- retains direction after removing `Q30` and `Q22686`.

A top-journal claim would still require multiple point-in-time datasets and
cutoffs, representative KG recommenders, adapted KGIL/DRO/certification
baselines, certified coverage, worst-version accuracy, and runtime evidence.
