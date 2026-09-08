# Phase 1, Cycle 8: Orthogonal Preference Programs over Frozen PQ Codes

Date: 2026-08-07

Status: complete; `CODEPATCH-⊥` advances to Phase 2

Outcome access: none for a Cycle-8 user cohort. This phase used primary
literature, predecessor failure records, and the already frozen item-only
`10,681 x 384` SentenceTransformer matrix. The feasibility probe trained an
item-only FAISS product quantizer and timed random lookup tables; it did not
select a user, parse a rating, construct a preference pair, or inspect a
recommendation outcome.

## Why an eighth Phase 1 was required

MARGIN-CACHE passed an item-only byte-feasibility check but failed its
architecture-level novelty gate. Mixed-precision embedding caches, learned
heterogeneous precision, ranking-aware quantization, and multi-tier vector
systems already occupy the architecture; an exact-vector cache is also
algebraically the same as a full-residual cache. Only its allocation heuristic
remained potentially new, which is insufficient for the requested novel
recommendation system.

Cycle 8 therefore restarts from the serving representation itself. The design
must change what can be expressed over an immutable compressed catalog, not
merely choose which ordinary vector, cache entry, graph edge, or search cell to
use.

## Current frontier and collision map

- SentenceTransformer-style independent item encoding enables offline catalog
  representation, while FAISS product quantization (PQ) replaces every item
  vector with a short tuple of codeword IDs and scores it through asymmetric
  distance-computation (ADC) tables. Ordinary ADC tables are induced by a dense
  query and the fixed PQ centroids. ([FAISS](https://github.com/facebookresearch/faiss),
  [quantization-based MIPS](https://proceedings.mlr.press/v51/guo16a.html))
- Product Quantized Collaborative Filtering (pQCF) already learns compressed
  user/item latent factors and computes preference by table lookup. Its
  asymmetric user-to-codeword scores remain inner products between a user
  vector and codewords. ([pQCF](https://doi.org/10.1109/TKDE.2020.2964232))
- SparCode already learns discrete codes and a sparse inverted index for
  retrievable cross-interactions. A new system cannot claim generic sparse
  code interaction or code-based recommendation retrieval.
  ([SparCode](https://arxiv.org/abs/2311.18213))
- Supervised, differentiable, ranking-aware, and query-aware quantization
  already learn codebooks, item codes, or query encoders. A method that changes
  those objects is not new merely because it uses preference pairs.
  ([Differentiable PQ](https://proceedings.mlr.press/v119/chen20l.html),
  [supervised PQ](https://openaccess.thecvf.com/content_CVPR_2019/html/Klein_End-To-End_Supervised_Product_Quantization_for_Image_Search_and_Retrieval_CVPR_2019_paper.html),
  [query/PQ joint optimization](https://arxiv.org/abs/2108.00644))
- SimPO supplies a reference-free fixed-margin preference objective and RecPO
  specializes preference optimization for recommendation. Applying either loss
  to scalar item scores is useful engineering, but it is not itself a novelty
  claim. ([SimPO](https://proceedings.neurips.cc/paper_files/paper/2024/hash/e099c1c9699814af0be873a175361713-Abstract-Conference.html),
  [RecPO](https://aclanthology.org/2026.acl-long.656/))
- Binary preference-preserving recommendation, query-adaptive hashing, and
  error-corrected hashing are occupied by CIGAR, NeuHash-CF, query-adaptive
  hash ranking, and CMH-ECC. A free query-bit update is just supervised hashing;
  adding parity bits does not by itself create a new retrieval architecture.
  ([CIGAR](https://arxiv.org/abs/1909.05475),
  [NeuHash-CF](https://arxiv.org/abs/2006.00617),
  [query-adaptive hashing](https://arxiv.org/abs/1904.08623),
  [CMH-ECC](https://arxiv.org/abs/1902.04139))

## Four critical bottlenecks

### C8-L1: dense-query adaptation has a strict PQ-table expressivity ceiling

For subquantizer `m`, let `C_m in R^(K x d_m)` contain the fixed PQ
centroids. An inner-product ADC query can create only

```text
B_u[m, :] = C_m q_u[m] + b_m 1.
```

Thus every query adapter, no matter how it produced `q_u`, is confined to the
at-most-`d_m + 1` dimensional column space of `A_m = [C_m, 1]` inside a
`K`-entry score table. With the qualified `M=24`, `K=256`, `d_m=16` setting,
ordinary dense queries occupy at most 17 of 256 table directions per
subquantizer. Current pipelines rarely expose or exploit the complement.

### C8-L2: post-retrieval alignment cannot repair compressed candidate censorship

An LLM or preference ranker applied after top-k retrieval cannot promote an
item that PQ/ANN never admitted. Deeper over-retrieval moves the cost rather
than aligning the retrieval function. The preference correction must be
executable while scanning compact codes so that it can change candidate
membership before a rich ranker.

### C8-L3: joint preference training conflicts with immutable-catalog operation

Joint hashing, learned codebooks, dense query encoders, and sparse interaction
indexes can improve matching, but preference updates may require catalog
re-encoding or index rebuilds. Fast-changing user feedback and slow-changing
catalog infrastructure need a separation: item vectors, PQ centroids, code
tuples, and index membership remain frozen while only a tiny user-side program
changes.

### C8-L4: apparently novel code scoring can collapse to old models

An unprojected lookup table can be another dense query in disguise. A lookup
on the complete PQ tuple is almost an item-ID table when tuples are nearly
unique. Sparsifying after projection can also silently destroy the claimed
orthogonality. A defensible architecture must prove non-collapse, preserve the
constraint after support selection, evaluate unseen items, and charge every
code, accelerator, patch, and metadata byte.

## Structured brainstorming pass

1. **Assumption reversal:** treat the ADC distance table—not the dense query or
   item vector—as the serving-time personalization interface.
2. **Dimensional analysis:** identify the low-rank subspace reachable by every
   dense query, then operate only in its orthogonal complement.
3. **Boundary analysis:** let the preference program participate in the compact
   code scan so it may rescue a future-liked item before top-k truncation.
4. **Constraint removal:** remove item re-encoding, catalog rebuilds, full-vector
   reranking, online LLM calls, and full-tuple memorization.

## Creative-thinking pass

- **Bisociation:** combine compiler-style tiny user programs with PQ's
  cache-resident lookup execution.
- **Janusian view:** the same frozen code remains a geometric approximation for
  ADC and a symbolic feature address for preference correction.
- **Subtraction:** remove every learned catalog object; only the per-user table
  residual is mutable.
- **Extreme case:** a zero patch is ordinary FAISS PQ; a patch inside
  `col([C_m,1])` is an ordinary dense query and must count as a control; a full
  tuple patch is item memorization and is forbidden.

## Divergent concepts and convergence

| Concept | Core mechanism | Disposition |
|---|---|---|
| **CODEPATCH-⊥** | User-conditioned sparse utility program over fixed PQ codewords, constrained outside all dense-query ADC tables | **Selected:** architecture-level non-collapse plus a clean immutable-index and latency hypothesis. |
| PARITY-ECC | Decode noisy preference votes into a valid error-correcting query codeword | Rejected: ECC hashing is occupied; useful codes spread semantic neighbors, while distance-preserving repetition adds no information. |
| Sparse query-bit repair | SimPO-trained XOR changes to an immutable binary query | Rejected algebraically as ordinary query-side supervised hashing. |
| CERT-ALIGN | Preference score bounds stop an exact/progressive scan | Rejected: branch-and-bound MIPS and learned termination are occupied. |
| TRACE-ANN | Preference-trained graph edge policy | Rejected: learned similarity-graph routing is directly occupied and needs custom per-edge inference. |
| GRAD-CORE | Gradient-diverse preference coreset | Rejected as a training-data-selection contribution, not a serving architecture. |
| CHARGE | Partial-OT matching of liked/disliked embeddings before one query | Rejected symbolically: fixed transport marginals collapse the query to weighted Rocchio. |

## Selected architecture: CODEPATCH-⊥

Let `z_i,m` be item `i`'s immutable FAISS PQ code in subquantizer `m`. A
prefix-only user log is encoded into dense history state `H_u` and per-codeword
evidence such as signed rating mass, positive/negative counts, confidence, and
recency. A small shared network produces a raw utility table `r_theta(H_u)`.

For a fixed support `S_u,m`, chosen only from the available history and
target-independent fill rules, construct the support-restricted matrix
`A_u,m = [C_m[S_u,m], 1]` and project:

```text
delta_u,m[S] = (I - A_u,m A_u,m^+) r_theta(H_u)[m,S]
delta_u,m[not S] = 0
```

Support size must exceed `rank(A_u,m)`; otherwise the patch is identically zero.
Because projection occurs *inside the final fixed support*, both exact sparsity
and `A_m^T delta_u,m = 0` are preserved. The served compact-code score is

```text
score(u, i) = sum_m (
    dot(q_u[m], C_m[z_i,m])
    + lambda * delta_u,m[z_i,m]
)
```

The patch parameters are trained with a user-macro, fixed-margin,
reference-free SimPO-derived loss on naturally observed chosen/rejected pairs:

```text
L = mean_user mean_pair softplus(
      beta * (gamma - score(u, chosen) + score(u, rejected)))
    + sparsity_and_scale_penalties
```

The item embeddings, centroids, codes, and code index never change. Candidate
generation scans the compact codes with the personalized table; an unchanged
BPR branch is retained as a standard collaborative comparator and optional
union branch. No full-precision metadata vector or online LLM is required in
the scoring loop.

## Narrow novelty boundary

CODEPATCH-⊥ does **not** claim novelty for SentenceTransformers, PQ, ADC,
lookup-table scoring, sparse interaction retrieval, user history aggregation,
BPR, SimPO, or candidate reranking. Its candidate whitespace is:

> compiling temporally available recommendation feedback into a sparse,
> user-conditioned utility program over an immutable PQ catalog, with every
> correction constrained to the orthogonal complement of all dense-query ADC
> tables and executed during compact-code candidate generation.

pQCF is the mandatory closest baseline because its user/codeword scores are
dense-inner-product representable. SparCode is the mandatory systems baseline
because it already supports sparse code interactions, but jointly learns its
codes and inverted structure. If the final projection, frozen-index contract,
user conditioning, unseen-item generalization, or candidate-generation effect
is absent, the novelty claim fails and the project must be killed.

## Target-blind item-only feasibility

On the previously frozen `10,681 x 384` normalized SentenceTransformer item
matrix, one CPU thread and FAISS 1.15.0 produced:

| Check | Observation | Interpretation |
|---|---:|---|
| `IndexPQ`, `M=24`, 8 bits | 649,646 serialized bytes | 3.9598% of the 16,406,016-byte dense matrix. |
| PQ code size | 24 bytes/item | Large compression headroom before user patches and an optional scan accelerator are charged. |
| Random LUT residual after removing `[C_m,1]` span | mean 0.9672; min 0.9429 | Confirms implementation geometry only; the random expectation is about `sqrt(1-17/256)=0.966`. It is not preference evidence. |
| Random LUT rerank of 512 PQ codes | p50 0.0518 ms; p95 0.0715 ms | Establishes only small-shortlist feasibility. |
| Exact CSR code scan, including uint8 data | p50 0.1539 ms; p95 0.1958 ms | PQ index plus accelerator consumed 12.03% of dense bytes, below one eighth, in this item-only probe. |

No quality, cohort, pair-support, or user-side latency conclusion follows from
these checks.

## Phase-2 handoff

Phase 2 must lock a fresh cohort disjoint from Cycle 5's opened A histories,
the final support-restricted projection, patch generator, pair construction,
FAISS parameters, code-scan implementation and full byte accounting, matched
controls, candidate and ranking metrics, three seeds, bootstrap estimands,
latency protocol, and a conjunctive kill gate before any Cycle-8 rating is
opened.

Any material gain that disappears under the orthogonal projection, appears
only on previously consumed items, fails against pQCF-style and tuned dense
controls, or exceeds the registered latency/storage budget kills CODEPATCH-⊥
and returns the sprint to Phase 1. Phase 5 remains forbidden.
