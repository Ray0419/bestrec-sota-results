# H6/H7 Novelty Audit: Transaction-Time KG Drift and Certified Residuals

Audit date: 2026-08-07

Status: qualified literature-search conclusion through the audit date; absence
of a located paper is not proof of priority.

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
- Generic structural graph certificates are occupied by
  [certifiable robustness to graph perturbations](https://papers.neurips.cc/paper_files/paper/2019/hash/e2f374c3418c50bc30d67d5f7454a5b4-Abstract.html)
  and [certified robust graph contrastive learning](https://arxiv.org/abs/2310.03312).
- Bitemporal KG models and revision reconstruction are established by
  [Time-Aware Probabilistic Knowledge Graphs](https://doi.org/10.4230/LIPIcs.TIME.2019.8)
  and [Wikidated](https://arxiv.org/abs/2112.05003).
- [KG4RecEval](https://arxiv.org/abs/2404.03164) already tests KG removal and
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
