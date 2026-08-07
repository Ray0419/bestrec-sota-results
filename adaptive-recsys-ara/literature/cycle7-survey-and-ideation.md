# Phase 1, Cycle 7: Preference-Critical Precision Allocation

Date: 2026-08-07

Status: complete; Phase 2 may begin

Outcome access: none for the Cycle-7 cohort. This phase used published work, frozen source records, and the already qualified item-only SentenceTransformer matrix. It did not select a Cycle-7 cohort or open any Cycle-7 A/R/V/T item, rating, pair, candidate, or metric.

## Why a seventh Phase 1 was required

PIVOT's sole append-only launch failed closed before cohort construction. The canonical scan found 21,928 structurally eligible users rather than the preview-derived literal 21,931. No A/R/V/T outcome was opened, but the one-shot integrity conjunction is false; PIVOT is killed and cannot be repaired or rerun.

The methodological lesson is separate from the discarded mechanism. A protocol should lock eligibility logic, deterministic ordering, a required cohort size, and a fail-if-insufficient rule. An observed archive-wide count may be recorded diagnostically, but a preview implementation's exact aggregate count is not a scientific hypothesis.

## Current frontier and collision map

- Product quantization (PQ) and FAISS already provide compressed vector search; ordinary PQ minimizes geometric reconstruction error, while FAISS supports asymmetric distance computation and compressed indexes. ([FAISS](https://github.com/facebookresearch/faiss), [FAISS additive quantizers](https://github.com/facebookresearch/faiss/wiki/Additive-quantizers))
- Ranking-oriented and query-aware quantization already optimize codebooks or query encoders for retrieval order. A new design cannot claim generic ranking-aware PQ. ([Joint query/PQ optimization](https://arxiv.org/abs/2108.00644), [Query-Aware Quantization for MIPS](https://ojs.aaai.org/index.php/AAAI/article/view/25613))
- Exact reranking of an over-retrieved compressed shortlist is standard, but it retains full vectors and cannot rescue an item that compressed retrieval never admits. ([FAISS FastScan and reranking](https://github.com/facebookresearch/faiss/wiki/Fast-accumulation-of-PQ-and-AQ-codes-%28FastScan%29))
- SimPO establishes a reference-free fixed-margin preference objective; RecPO adds recommendation-specific intensity and recency. Neither fixed margins nor recommendation preference optimization are new. ([SimPO](https://proceedings.neurips.cc/paper_files/paper/2024/hash/e099c1c9699814af0be873a175361713-Abstract-Conference.html), [RecPO](https://aclanthology.org/2026.acl-long.656/))
- DFTopK directly relaxes the top-k operator for cascade training, while Quake adapts vector-index structure and work under dynamic workloads. The selected idea must not claim differentiable top-k or adaptive indexing. ([DFTopK](https://arxiv.org/abs/2510.11472), [Quake](https://www.usenix.org/conference/osdi25/presentation/mohoney))
- Distributional retrieval and probabilistic recommendation explicitly represent embedding uncertainty. DINOSAUR expands an ANN index with stochastic item samples; probabilistic metric learning represents users/items as Gaussians. Uncertainty-aware retrieval is occupied. ([DINOSAUR](https://arxiv.org/abs/2606.04603), [Probabilistic metric learning](https://arxiv.org/abs/2101.04849))

## Four critical bottlenecks

### C7-L1: average reconstruction error is not preference damage

PQ optimizes a catalog-level geometric distortion. Recommendation failure is caused by the smaller, query-dependent residual component that reverses a chosen/rejected margin or moves a future-liked item across the candidate boundary. Two indexes with similar mean reconstruction error can therefore have different user-macro preference loss.

### C7-L2: exact reranking cannot recover censored items

Storing every full vector for reranking erases the memory benefit of compression. Reranking only a compressed shortlist also acts too late: if PQ error excludes a preference-critical item, no downstream ranker can restore it. Precision must be available as a retrieval branch, not only after candidate truncation.

### C7-L3: current alignment usually mutates the model or the whole index

Query adapters, jointly trained codebooks, distributional copies, and learned indexes can improve retrieval, but they require model retraining, catalog re-encoding, index rebuilding, larger indexes, or heavier online logic. An underexplored alternative is to keep vectors and the ordinary PQ codebook immutable and learn only where a tiny exact-precision budget should be spent.

### C7-L4: memory claims are easily confounded with quality and popularity

A learned high-precision tier can merely memorize popular items. A valid systems test needs actual serialized byte accounting, equal-byte cache controls, user-macro training/evaluation, a shuffled-preference control, a head-decile exclusion analysis, fixed candidate quotas, and latency measured on the exact serving path.

## Structured brainstorming pass

1. **Assumption reversal:** instead of adapting every vector or every query to preferences, adapt which item residuals remain exact.
2. **Boundary analysis:** target pairs whose preference margin is reversed by PQ, not average vector distortion.
3. **Constraint removal:** remove full-catalog exact storage but retain a small, explicit precision budget.
4. **Analogy transfer:** combine mixed-precision caching from systems with reference-free preference optimization from alignment.

## Creative-thinking pass

- **Bisociation:** a cache admission decision becomes a preference-alignment policy.
- **Janusian view:** the semantic catalog remains immutable, while a few items simultaneously exist in compressed and exact form.
- **Subtraction:** remove query rotation, learned routing, dynamic work, request selectors, multi-interest fusion, online LLM inference, full-vector reranking, and codebook retraining.
- **Extreme case:** at budget zero the method is ordinary PQ; when every item is cached it converges to full-precision retrieval. The useful hypothesis lives between those endpoints.

## Divergent concepts and convergence

| Concept | Core mechanism | Disposition |
|---|---|---|
| **MARGIN-CACHE** | SimPO-trained global exact-vector cache over an immutable PQ catalog | **Selected:** strongest scale/latency/alignment intersection and clean byte-matched controls. |
| GRAD-CORE | Gradient-diverse user-macro coreset for preference training | Reserve; primarily training efficiency, not a new serving architecture. |
| CERT-ALIGN | Preference-score bounds stop progressive scanning | Reserve; compelling but harder to certify without a custom index. |
| FLIP-MINE | Train only preference pairs reversed by the compressed path | Reserve; useful ablation but weaker than precision allocation. |
| PREF-REPLICA | Replicate preference-critical items across geometric cells | Reserve; introduces index-routing confounds and extra memory bookkeeping. |
| ORDER-PQ | Learn codebooks for pair-margin preservation | Rejected as primary novelty; ranking-aware/query-aware quantization is occupied. |
| TRACE-ANN | SimPO-trained preference edge policy for fixed-work graph traversal | Reserve; learned ANN navigation is crowded and implementation-heavy. |
| CHARGE | Partial optimal-transport cancellation of local likes/dislikes before one MIPS query | Reserve; risks algebraic collapse to a signed centroid. |
| PARITY-REC | Preference-syndrome binary retrieval | Reserve; potentially transformative but close to supervised hashing. |
| ECLIPSE | Diagonal preference uncertainty compiled into a lifted MIPS score | Rejected as primary novelty after DINOSAUR/probabilistic-retrieval collision; useful future comparison. |

## Selected direction: MARGIN-CACHE

Let `E_i` be the immutable SentenceTransformer item vector, `Ehat_i` its reconstruction under a frozen FAISS PQ index, and `r_i = E_i - Ehat_i`. A global cache gate `z_i` decides whether item `i` also has an exact vector in a small high-precision tier.

For an A-only user query `q_u`, the served score is:

```text
score_z(u, i) = dot(q_u, Ehat_i + z_i * r_i)
```

The cache logits are trained on R-only natural rating-gap pairs using a fixed-margin, reference-free SimPO loss with user-macro weighting:

```text
L = mean_user mean_pair softplus(
      beta * (gamma
              - score_z(u, chosen)
              + score_z(u, rejected)))
```

A hard top-`B` projection freezes exactly `B` cached item IDs before test. Serving searches an ordinary PQ branch and a small exact-cache FAISS branch, removes history, unions IDs, scores each item with its stored precision, and emits a fixed 100-item list. Querying at least `100 + |history(u)|` distinct PQ IDs guarantees 100 unseen PQ candidates whenever the catalog contains 100 unseen items; no guessed post-filter depth is used.

The item vectors, PQ codebooks, and query construction never change. Actual serialized PQ-index bytes, exact-cache-index bytes, cache IDs, and required metadata are charged to one budget.

## Narrow novelty boundary

MARGIN-CACHE does not claim novelty for PQ, residual vectors, mixed precision, exact caches, hybrid retrieval, top-k projection, SimPO, or ranking-aware quantization individually. Its candidate whitespace is:

> user-macro reference-free preference-loss allocation of a fixed exact-vector tier over an otherwise immutable compressed recommender index, evaluated end to end under equal serialized bytes, fixed candidate work, popularity controls, and sealed future preference outcomes.

Unlike ranking-aware PQ, it does not retrain a query encoder or codebook. Unlike exact reranking, it does not retain all full vectors and its exact tier participates in candidate generation. Unlike DINOSAUR, it does not replicate stochastic embedding samples or optimize exploration; it spends deterministic precision on observed preference-margin damage.

## Phase-2 handoff

Phase 2 should lock a fresh cohort selected from one canonical archive scan, but only require that enough eligible users exist. It must freeze PQ parameters, cache size, actual byte accounting, continuous-gate optimization, hard projection/checkpoint selection, candidate cardinality construction, equal-byte heuristic and shuffled controls, pair/metric estimands, three seeds, latency protocol, and one-shot authority before any Cycle-7 R/V/T outcome is opened.

Any false, missing, nonfinite, underpowered, or unauthenticated gate kills MARGIN-CACHE and returns the sprint to Phase 1. Phase 5 remains forbidden.
