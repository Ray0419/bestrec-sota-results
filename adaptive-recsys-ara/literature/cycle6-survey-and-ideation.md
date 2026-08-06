# Phase 1, Cycle 6: Preference-Aligned Partition Routing

Date: 2026-08-07

Status: complete; Phase 2 may begin

Quality-outcome access: none for the cycle-6 cohort. The target-blind checks in
this phase used only frozen item vectors, catalog size, user event counts, and
timestamp-group counts. No cycle-6 item identity, rating, preference pair,
candidate, validation metric, or test metric was read.

## Why a sixth Phase 1 was required

CABLE-PREF was killed on its only authorized run before `R`, `V`, or `T` target
access. Its batched FAISS scores and independent dense-matrix scores were within
the preregistered numerical tolerance, but a within-tolerance difference changed
at least one masked top-200 ID or order. That falsified CABLE's exact
cross-backend identity gate.

This failure does not establish that FAISS retrieval is ineffective. It exposes
a measurement error: two valid floating-point kernels were forced to produce one
total order even near numerical ties. Cycle 6 therefore separates three claims:

1. one named FAISS path defines deployed candidate semantics;
2. an exhaustive scorer measures retrieval recall and score error with an
   explicit tolerance, without demanding identical tie resolution; and
3. preference utility and scanned work determine whether the learned mechanism
   is useful.

Cycle 6 is not a repair of CABLE. It cannot reuse the consumed claim, cohort,
admission loss, branch complement, endpoint leave-out target, or outcome path.

## Current frontier and collision map

The state of the art now makes several individual ingredients unavailable as
novelty claims.

- Sentence-BERT and FAISS already establish independent dense encoding and
  efficient vector search. FAISS IVF partitions the database and probes the
  `nprobe` cells selected by a geometric coarse quantizer; the work/accuracy
  tradeoff comes from scanning only those lists.
  ([Sentence-BERT](https://aclanthology.org/D19-1410/),
  [FAISS indexes](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes))
- Learning to Index replaces centroid-distance cell ordering with learned
  nearest-neighbor probabilities, while LIRA learns query-aware partitions and
  per-query probing. Learned cell routing is therefore established systems
  territory.
  ([Learning to Index](https://arxiv.org/abs/1807.02962),
  [LIRA](https://arxiv.org/abs/2503.23409))
- RecForest jointly learns recommendation embeddings and a tree index with a
  user-context routing network. Generic personalized routing or a learned tree
  is not new.
  ([RecForest](https://proceedings.neurips.cc/paper_files/paper/2022/hash/fe2fe749d329627f161484876630c689-Abstract-Conference.html))
- Quake adapts vector-index structure and query effort to geometric recall and
  latency objectives. Adaptive `nprobe` or index maintenance is not new.
  ([Quake](https://www.usenix.org/conference/osdi25/presentation/mohoney))
- SimPO removes DPO's reference-model pass and adds a target margin. RecPO adds
  recommendation-specific preference intensity and recency. Cycle 6 must use a
  fixed, ordinary reference-free margin and cannot claim either ingredient.
  ([SimPO](https://proceedings.neurips.cc/paper_files/paper/2024/hash/e099c1c9699814af0be873a175361713-Abstract-Conference.html),
  [RecPO](https://aclanthology.org/2026.acl-long.656/))
- Active preference selection, permutation-invariant list ranking, robust
  preference elicitation, and setwise recommendation are occupied neighboring
  areas. They remain controls or reserve directions, not the selected claim.
  ([Active Preference Learning](https://proceedings.mlr.press/v235/muldrew24a.html),
  [InvariRank](https://arxiv.org/abs/2604.27599),
  [SetRank](https://arxiv.org/abs/1912.05891))

## Four critical bottlenecks

### C6-L1: vector partitions are routed for proximity, not preference utility

Standard IVF probes cells whose centroids are closest to a query. Learned ANN
routing predicts cells containing geometric nearest neighbors. Neither target
asks which immutable semantic region contains items the user prefers. A system
can achieve high geometric recall while spending its fixed probe budget on a
region whose candidates are semantically close but explicitly disliked.

### C6-L2: routing and ranking can implement different utilities

A downstream aligned ranker cannot score an item in an unprobed partition.
Training one model to route cells and another to rank survivors recreates the
cross-stage objective mismatch from earlier cycles. A useful mechanism should
make one low-cost preference potential control both decisions, so training
cannot improve a score that serving never uses.

### C6-L3: actionable support and work must be measured together

RIPPLE, CAPER, and RAVEL showed that correct pair direction or safe conditional
uplift can act on too little of the served surface. Conversely, probing more
partitions can manufacture candidate gains by spending more work. The next
experiment needs a fixed `nprobe`, item-score count, and candidate quota, then
must measure both changed preference support and retrieval utility.

### C6-L4: backend identity is not retrieval correctness

Near-tie score differences can reorder IDs across FAISS and BLAS kernels even
when scores agree within tolerance. Bitwise or total-order equality is too
brittle for a scientific gate. One canonical serving implementation, durable
near-tie diagnostics, explicit candidate-set recall, and bounded score error are
needed. Exact output cardinality remains a property; exact cross-kernel tie
resolution does not.

## Structured brainstorming pass

The required brainstorming operations were applied as follows.

1. **Constraint removal:** remove the requirement that every numerical backend
   produce one total order; retain a canonical FAISS output and tolerant oracle.
2. **Assumption reversal:** instead of routing partitions to recover geometric
   neighbors and aligning later, train the partition utility from preferences.
3. **Boundary analysis:** place the intervention at the discrete shard boundary,
   a high-support decision made for every request, rather than at a sparse item
   swap or top-k cutoff.
4. **Analogy transfer:** borrow additive random-utility potentials from choice
   models and use them as cell-level biases in an immutable vector index.

## Creative-thinking pass

- **Bisociation:** combine reference-free preference optimization with IVF
  coarse routing. The shared object is a user-conditioned partition potential.
- **Reformulation:** treat `nprobe` as a scarce allocation of semantic attention,
  not only a geometric search knob.
- **Janusian thinking:** item geometry remains fixed while effective regional
  utility changes per user; one partition can be geometrically near yet
  preference-distant.
- **Subtraction:** remove query rotation, LLM online inference, item re-encoding,
  index rebuilding, dynamic margins, per-request fallback gates, and explicit
  admission thresholds.

## Divergent concepts

| Concept | Core mechanism | Disposition |
|---|---|---|
| ROBUST-CONE | Set-valued user-query uncertainty and lower-quantile scoring | Reserve; novel but likely trades mean relevance for tail stability. |
| JANUS-SET | Permutation-equivariant candidate-set contextual ranking | Rejected; crowded by SetRank and InvariRank, and does not address retrieval work. |
| CURL-MIPS | Potential plus low-rank cyclic preference flow | Reserve; scientifically interesting but explicit scalar ratings weakly identify cycles. |
| SHIFT-MD | Online mirror-descent user state under drift | Reserve; requires a credible intervention/shift benchmark. |
| ONE-QUESTION | Active pair query minimizing worst-case top-k regret | Rejected; active elicitation is crowded and changes the interaction protocol. |
| RULE-FIRST | Hard natural-language constraints followed by dense ranking | Rejected; public offline data do not identify constraint compliance. |
| EXPOSURE-DR | Doubly robust reference-free preference loss | Rejected for MovieLens; no logged exposure propensities. |
| TAIL-CVaR | Optimize worst-user preference inconsistency | Rejected; robust objectives are occupied and do not solve retrieval scale. |
| MIPS-COMPILE | Distill an expressive teacher into a bilinear retrieval score | Reserve; strong latency story, weak novelty against ranking distillation. |
| **PIVOT** | One preference-trained partition offset reused for probing and ranking | **Selected.** Directly couples fixed-work vector routing to aligned utility. |

Independent reviews disagreed on the pure novelty ranking: ROBUST-CONE scored
higher as an unconstrained research idea, while PIVOT scored highest on the
requested joint scale/latency/alignment objective and was most structurally
different from cycles 1-5. The selection therefore follows the user's systems
objective, not the unweighted novelty rank.

## Target-blind real-embedding qualification

The already frozen SentenceTransformer matrix contains 10,681 normalized
384-dimensional movie vectors. A read-only `MiniBatchKMeans` check used seed
`20260861`, batch 1,024, five initializations, 100 maximum iterations, and zero
reassignment ratio. For 32 partitions:

- smallest partition: 225 items;
- 10th percentile: 240 items;
- median: 312 items;
- largest partition: 531 items;
- sum of the four smallest partitions: 932 items; and
- sum of the eight smallest partitions: 1,964 items.

Therefore any four distinct partitions contain at least 932 items. Restricting
the cycle-6 cohort to at most 300 total historical events leaves at least 632
unseen items in any four-partition union, which certifies a semantic output of
100 without adaptive backfill. Even the loose four-times-largest upper bound
scans at most 2,124 of 10,681 items (`19.89%`).

A separate structural-only pass found 21,931 users with 80-300 events and at
least four timestamp groups after excluding every cycle-5 user. The minimum
timestamp-group count was 16. This establishes feasibility for a fresh 600-user
cohort without reading their item or rating outcomes.

These checks qualify shape and capacity only. They do not predict whether PIVOT
will improve recommendation quality.

## Selected direction: PIVOT

**PIVOT** means **Preference-Informed Vector-partition Offsets for Traversal**.

Let immutable SentenceTransformer item vectors be partitioned into 32 fixed
cells with centroids `mu_c`. From prefix-only interaction embeddings, construct
a raw user query `q_u` and descriptor `h_u`. A small bounded network outputs one
offset per cell:

```text
o_u = a * tanh(MLP(h_u))                         # 32 bounded offsets
route_u(c) = dot(q_u, mu_c) + o_u[c]
score_u(i) = dot(q_u, E_i) + o_u[cell(i)]
P_u = four cells with largest route_u(c)
C_u = FAISS top-100 by score_u(i), i in union(P_u) \ history(u)
```

The same offset is the only learned term in both the probe logit and item score.
On a real chosen/rejected pair in different cells, train it with a fixed
SimPO-style reference-free margin:

```text
L_PIVOT = mean_user mean_pair softplus(
    beta * (gamma - score_u(chosen) + score_u(rejected))
)
```

Same-cell pairs are evaluation evidence but provide no partition-offset
gradient. There is no reference model, item update, query adapter, dynamic
margin, cutoff loss, selection gate, or online LLM.

## Narrow novelty boundary

PIVOT does **not** claim novelty for clustering, IVF, learned ANN routing,
personalized routing, adaptive probing, SimPO, or additive score calibration in
isolation. Its candidate whitespace is the following shared interface:

> a single reference-free, feedback-trained user-to-partition potential that
> jointly determines fixed-budget probing and cross-partition candidate ranking
> over immutable SentenceTransformer shards.

LIRA predicts partitions containing geometric nearest neighbors and can vary
`nprobe`; PIVOT keeps `nprobe=4` and learns from explicit preferences. RecForest
jointly learns embeddings and a tree; PIVOT freezes vectors, assignments, and
FAISS shard indexes. Quake adapts work to geometric recall; PIVOT holds work
fixed and changes which regions receive it. RIPPLE rotated one query and
adapted ANN effort; PIVOT never changes the query and broadcasts a discrete
regional potential to every item in a probed cell.

## Phase-2 handoff

Phase 2 must lock a fresh disjoint cohort, one fixed `nprobe=4` work contract,
one 100-item semantic candidate quota, and a sealed temporal test. The primary
comparators are geometric-IVF at equal work, PIVOT rerank-only, PIVOT route-only,
full exact semantic search, raw exact semantic search, and shuffled preference
directions. Promise must require a material preference/candidate gain over the
equal-work geometric baseline, dominance over both single-use controls, a
nontrivial changed surface, relevance non-inferiority, fixed-work/capacity
compliance, seed stability, and independent provenance. Any failure kills PIVOT
and returns to Phase 1; Phase 5 remains forbidden.

