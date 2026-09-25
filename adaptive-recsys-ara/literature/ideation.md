# Phase 1 Structured Ideation

This document records the required divergent and convergent passes. It applies tension, boundary-failure, constraint-removal, adjacent-possible, negation, bisociation, reformulation, and Janusian-thinking lenses from the two ideation skills.

## Problem reformulations

1. **From ranking to censoring:** the first error is often not a wrong order but a relevant item never entering the slate.
2. **From model freshness to state estimation:** user intent and catalog state evolve at different rates; updates should be treated as a control problem.
3. **From ANN depth to budgeted sensing:** each additional probe buys information at a measurable latency cost.
4. **From a negative label to a missing-data event:** non-interaction is conditional on exposure and position.
5. **From LLM inference to amortized alignment:** semantic reasoning can supervise a compact retrieval policy rather than execute on every request.

## Divergent pass: 12 raw directions

| ID | Direction | Generative lens | Central mechanism |
|---|---|---|---|
| I01 | Decision-aware ANN | Negate “geometric recall is the goal” | Allocate probes to aligned utility or decision uncertainty. |
| I02 | Index-boundary SimPO | Boundary failure | Mine comparisons from candidates that the deployed ANN actually confuses. |
| I03 | Query-only preference adapter | Remove reindex constraint | Update a low-rank user/query adapter while item vectors remain fixed. |
| I04 | Exposure-aware reference-free PO | Missing-data reformulation | Weight comparisons by logged exposure propensity and pair reliability. |
| I05 | Multi-timescale drift controller | Control-theory bisociation | Fast user-state loop, slow model/index loop, event-triggered updates. |
| I06 | Uncertainty-gated LLM reranker | Budgeted-sensing analogy | Invoke semantic reranking only when vector and collaborative signals disagree. |
| I07 | Belief-state user retrieval | Negate single-vector user | Retrieve from a posterior over short- and long-term interests. |
| I08 | Preference-compatible index upgrades | Compatibility tension | Preserve aligned ordering during asynchronous embedding migrations. |
| I09 | Permutation-consistent slate alignment | Set/sequence contradiction | Penalize candidate-order sensitivity in an LLM/list ranker. |
| I10 | Delayed-satisfaction SimPO | Multi-horizon reformulation | Learn margins from retention/regret, not only immediate clicks. |
| I11 | Dual-control recommendation | Bandit bisociation | Choose items for utility and preference-information gain. |
| I12 | Full-stack temporal benchmark | Measurement inversion | Jointly measure utility, candidate censoring, staleness, tail exposure, and tail latency. |

## Convergent pass

Scoring: 1 (weak) to 5 (strong). “Collision risk” is reverse-scored: 5 means relatively open after the targeted literature scan.

| Rank | Candidate | Novelty | Testability | Scale/latency impact | PoC feasibility | Collision risk | Total /25 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | I02 + I03 + I01: index-conditioned query-only SimPO with budgeted ANN | 5 | 5 | 5 | 5 | 4 | **24** |
| 2 | I05: event-triggered multi-timescale controller | 5 | 4 | 5 | 4 | 4 | **22** |
| 3 | I04: exposure-aware reference-free PO | 4 | 5 | 5 | 4 | 3 | **21** |
| 4 | I06: uncertainty-gated semantic reranking | 4 | 5 | 5 | 5 | 2 | **21** |
| 5 | I07: belief-state user retrieval | 3 | 4 | 4 | 4 | 2 | **17** |

## Collision checks on the winner

- **Query-only fixed-index adaptation is not new by itself:** ANCE-PRF and index-preserving search adaptation are adjacent prior work.
- **Hard-negative mining is not new by itself:** many retrieval and preference methods use hard or dynamic negatives.
- **Reference-free PO is not new by itself:** SimPO establishes it.
- **Adaptive ANN is not new by itself:** Quake adapts effort for geometric recall.
- **Retrieval-conditioned loss is not new by itself:** stochastic retrieval-conditioned reranking couples a reranker to candidate sampling.

The surviving hypothesis is compositional but nontrivial: treat the immutable, approximate serving index as part of preference training; update only the query policy; use the resulting preference-margin uncertainty to spend ANN work. The test is end-to-end and requires gains under a latency/index-maintenance constraint, so a superficial recombination will fail the gate.

## Selected direction

**Working name:** RIPPLE — **R**etrieval-**I**ndex-conditioned **P**reference **P**olicy **L**earning for **E**fficient recommendation.

RIPPLE trains a compact query adapter with a SimPO-derived score-difference loss. Chosen items are paired with reliable rejected items and hard confusions sampled from the exact FAISS serving boundary. The item encoder and FAISS index are frozen. At inference, a pilot ANN search estimates ambiguity; only ambiguous requests receive additional probes. Exact dot-product reranking of the retrieved set uses the same aligned query, avoiding an always-on LLM.

## Rejected directions and why

- **Always-on LLM reranking:** directly conflicts with the intended millisecond serving envelope.
- **Pure dynamic-margin SimPO:** RecPO and NAPO already occupy this neighborhood.
- **Pure multi-negative/listwise PO:** S-DPO, LiPO, and KPO make the novelty claim weak.
- **Rebuild item embeddings after preference tuning:** does not address the update-cost bottleneck.
- **A router alone:** adaptive compute routing is an active field; without retrieval-stage alignment it is incremental.

## Phase 1 decision

Advance RIPPLE to Phase 2. Its claim will be bounded to the intersection above, and its PoC must report full-catalog temporal metrics, actual FAISS candidate recall, tail latency, and zero catalog re-embedding during alignment.
