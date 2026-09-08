# Phase 1, Cycle 4: Action-Surface Survey and Creative Ideation

**Trigger.** RAVEL v1 is dead. Its sealed runner changed only 3 of 1,862
pair-bearing seed-user rows after selection (19 for the always-on proposal),
yielded only `+0.000146` user-macro preference accuracy against the frozen
linear hybrid, covered `8.57%` of requests, and cost `1.543x` the baseline p95.
G1, G3, G5, G9, and external-integrity G10 failed. This cycle therefore does
not add another gate around RAVEL. It changes the region over which the
preference model has authority.

This phase repeated the two registered ideation procedures. The brainstorming
pass extracted contradictions from the three killed PoCs and separated them
from generic field-wide problems. The creative-thinking pass used assumption
reversal, constraint removal, bisociation, boundary analysis, and an explicit
12-direction divergence before convergence. Current primary literature was
collision-checked before selecting a direction. All analysis of opened CAPER
or RAVEL cohorts is hypothesis-generating only.

## Four revised bottlenecks

### C4-L1 — Preference quality is useless without a preference-relevant action surface

RAVEL's uniform natural-pair residual had positive held-out discrimination, but
its finite proposal altered almost none of the evaluated pair relations. A
selector can suppress harmful actions; it cannot create useful actions. Modern
preference optimization, hard-negative construction, and listwise ranking do
not by themselves specify which part of a deployed list should be allowed to
move.

### C4-L2 — A single semantic centroid erases multi-modal preference geometry

Averaging all liked items into one query can land between distinct interests,
especially when dislikes and rating gaps are informative. Multi-interest
recommenders already address representation collapse, but commonly optimize
click or next-item objectives. The narrower open interface is to align each
facet query from macro-balanced natural preference pairs before ANN, without
moving the catalog vectors or using a reference policy at inference.

### C4-L3 — Millisecond baselines make online alignment structure dominate latency

RAVEL's residual, projection, request descriptor, selector heads, assertions,
and second ordering path added only about one millisecond, yet that was more
than 50% overhead over a roughly two-millisecond baseline. An online LLM,
request router, repeated ANN search, or combinatorial tournament is therefore
unlikely to satisfy the registered relative budget. Facet queries must be
searched as one fixed-budget batch, and the aligned facet scores must feed one
vectorized fusion and one final sort.

### C4-L4 — Ordinary candidate recall does not measure preference-pair support

The semantic union raised positive-item candidate recall by `+0.08737` in
RAVEL, yet the aligned proposal could act on almost no preference relations.
This is not proof that retrieval is solved: a union can retrieve isolated
positives without co-retrieving the higher/lower-rated witnesses needed for
preference learning and evaluation. The next PoC must measure candidate recall
and natural-pair co-support *before ranking* on a method-independent target
cohort.

## Hypothesis-generating continuation probe

No model was fitted or rerun. The already opened RAVEL artifacts were rescored
once to ask whether its frozen residual would have been more useful below an
exact linear top-10. The adjusted continuation improved full-order preference
accuracy by `+0.005109` over linear (95% user-cluster bootstrap interval
`[-0.004891, +0.014827]`) and continuation-only pair accuracy by `+0.005306`
(`[-0.005719, +0.016461]`). Under the same frozen head it exceeded a BPR-ordered
continuation by only `+0.001682` (`[-0.015471, +0.019397]`). It changed `9.02%`
of evaluated pair relations.

The broad tail statistic was misleading. On outcomes tied to the actually
served second page, adjusted-minus-linear was `-0.000022` NDCG@20 (95% CI
`[-0.000323, +0.000253]`), `-0.000102` page-2 Recall
(`[-0.000896, +0.000686]`), `-0.000057` graded NDCG@20
(`[-0.000378, +0.000236]`), and only `+0.000110` preference accuracy for pairs
touching baseline ranks 11–20 (`[0, +0.000329]`). No model was fitted or rerun;
these are read-only, hypothesis-generating diagnostics over opened artifacts.
TAILOR/HECA is therefore rejected before consuming a fresh cohort: its apparent
gain lives in deep, likely unserved order relations rather than page-2 utility.

## Divergent pass: 12 successor directions

Scores are 1–5 for defensible novelty boundary (N), failure-evidence fit (E),
PoC feasibility (F), and latency fit (L).

| ID | Direction | N | E | F | L | Total /20 | Collision or rejection boundary |
|---|---|---:|---:|---:|---:|---:|---|
| C4-I01 | **Facet-conditioned preference retrieval (FACET-PREF)** | 4.7 | 4.6 | 4.4 | 4.2 | **17.9** | Multi-interest retrieval is mature; claim only macro-balanced reference-free facet geometry before ANN |
| C4-I02 | BPR-stable semantic rescue below the head | 3.8 | 4.5 | 4.6 | 4.7 | 17.6 | Hybrid retrieval is mature; rescue rule would carry the claim |
| C4-I03 | BPR tie-breaking inside relevance shells | 3.2 | 4.4 | 4.8 | 4.9 | 17.3 | Near-tie and constrained reranking are occupied |
| C4-I04 | Tail pairwise-DAG ordering | 4.1 | 4.5 | 3.5 | 3.5 | 15.6 | Pair aggregation is mature and sorting overhead is risky |
| C4-I05 | Position-aware aligned-score distillation | 3.7 | 4.0 | 3.8 | 4.7 | 16.2 | Ranking distillation is occupied; exact-head contract must remain explicit |
| C4-I06 | Head-exact aligned continuation | 4.1 | 2.0 | 4.8 | 4.8 | 15.7 | Rejected: opened-cohort page-2 metrics show the apparent deep-tail gain is not served utility |
| C4-I07 | Parallel multi-facet ANN retrieval | 3.3 | 3.2 | 3.2 | 2.3 | 12.0 | Strong collision and likely latency failure |
| C4-I08 | Preference-regret adaptive ANN depth | 4.0 | 2.8 | 3.1 | 3.4 | 13.3 | Query-adaptive search is occupied and ordering is the observed bottleneck |
| C4-I09 | Invariant-teacher geometry distillation | 4.1 | 3.0 | 3.0 | 4.2 | 14.3 | Distillation and ranking consistency are crowded 2026 priority alerts |
| C4-I10 | Exposure-corrected continuation SimPO | 3.0 | 3.8 | 2.0 | 4.5 | 13.3 | IPS/causal recommendation is established; MovieLens lacks propensities |
| C4-I11 | Preference-aligned generative candidate creation | 2.7 | 2.8 | 1.8 | 1.8 | 9.1 | OneRec/RankGR occupy the core and violate the CPU PoC budget |
| C4-I12 | Validation-selected listwise scalarization | 2.4 | 2.1 | 4.5 | 4.3 | 13.3 | CAPER and RAVEL already falsified nearby variants |

## Selected direction: FACET-PREF

**FACET-PREF — Facet-Conditioned Preference Retrieval.** A single mean user
vector collapses distinct interests and can censor preference-discriminating
items before ranking. FACET-PREF clusters positive prefix interactions into a
small fixed number of semantic facets, then adapts the facet queries from
macro-balanced natural rating pairs using a reference-free margin objective.
The catalog vectors and FAISS index remain immutable. All facet queries are
searched as one batch under the same total semantic candidate budget as the
single-centroid baseline, merged with the unchanged BPR branch, and scored by
the same aligned facet geometry plus the validation-locked collaborative blend.

```text
E_i      = frozen SentenceTransformer metadata vector for item i
c_uf     = target-blind centroid of liked prefix items in facet f
q_uf     = normalize(c_uf + bounded_adapter(c_uf, user-prefix features))
L_pair   = -log sigmoid(beta * ((q_uf·E_i+ - q_uf·E_i-)/tau) - margin)

S_u      = fixed_quota_union(batch_FAISS({q_uf}), total_budget=200)
B_u      = FAISS_BPR(q_bpr(u), budget=200)
C_u      = stable_union(B_u, S_u), |C_u| <= 400
score(i) = alpha * normalized_BPR(i)
           + (1-alpha) * max_f normalized(q_uf·E_i)
serve(u) = stable_sort(C_u, score)
```

The design is chosen over another selector because RAVEL showed that gating
cannot repair a sparse action set; over a continuation layer because its broad
tail signal vanished on served-page metrics; and over a combinatorial
tournament because the relative latency budget demands batched matrix scoring
and one final sort. FACET-PREF is unproven—the point of the PoC is to learn
whether aligned facets can change candidate support and top-10 preference
without repeating RIPPLE's loss of collaborative structure.

## Collision-safe novelty boundary

- **Not novel:** SimPO, margin Bradley–Terry/BPR losses, reference-free
  preference optimization, multi-interest representation, semantic/
  collaborative retrieval, fixed candidate quotas, FAISS, or reranking.
- **Not claimed:** optimality, causal preference identification, formal safety,
  conformal validity, or a new multi-interest architecture.
- **Terminology constraint:** SimPO's original reward is a length-normalized
  sequence log-probability. On scalar recommendation scores, FACET-PREF uses a
  *SimPO-inspired reference-free margin ranking objective*; it does not claim a
  new SimPO loss.
- **Explicit collisions:** MIND/MIP/ULIM/GemiRec occupy multi-interest
  retrieval; OneRec/RankGR and DynamicPO/RoDPO occupy preference-aligned
  generation or preference-pair construction. These ingredients may not be
  presented as new.
- **Candidate whitespace:** macro-balanced reference-free pairwise alignment of
  facet-conditioned user queries *before* fixed-budget ANN retrieval, with
  immutable item geometry and end-to-end evaluation of preference-pair
  candidate support, served top-10 preference, relevance, and latency. Novelty
  is the constrained systems intersection and empirical finding, not a new
  component or loss.

## Metric-gaming safeguards required before Phase 4

The PoC must preregister (1) the same total budget of at most 400 candidates,
immutable catalog vectors/indexes, and no target-conditioned query; (2) union
candidate Recall and natural preference-pair support before ranking; (3)
user-macro top-10 preference accuracy on a fixed, method-independent pair
cohort; (4) NDCG@10, Recall@10, and low-rating intrusion; (5) selected BPR and
single-centroid linear baselines; (6) raw multi-interest, zero-margin,
shuffled-label, and single-query aligned controls under the same budget; (7)
three-seed stability and minimum pair support; and (8) absolute and relative
p95 latency. Phase 5 remains forbidden unless every prospective criterion
passes on a fresh cohort.

## Primary-source collision map

- SimPO: https://arxiv.org/abs/2405.14734
- BPR: https://arxiv.org/abs/1205.2618
- Learning-to-Rank with Partitioned Preference: https://proceedings.mlr.press/v130/ma21a.html
- FINEST rank-preserving fine-tuning: https://arxiv.org/abs/2402.03481
- OneRec: https://arxiv.org/abs/2502.18965
- RankGR: https://arxiv.org/abs/2602.08575
- DynamicPO and RoDPO hard/boundary preference construction: https://arxiv.org/abs/2605.00327 and https://arxiv.org/abs/2603.29259
- MIND multi-interest retrieval: https://arxiv.org/abs/1904.08030
- MIP, ULIM, and GemiRec: https://arxiv.org/abs/2207.06652, https://arxiv.org/abs/2507.10097, and https://arxiv.org/abs/2510.14626
- Exposure-aware recommendation: https://arxiv.org/abs/1510.07025, https://proceedings.mlr.press/v48/schnabel16.html, and https://arxiv.org/abs/2204.12176
- LLM-to-recommender distillation priority alerts: https://arxiv.org/abs/2405.00338, https://arxiv.org/abs/2603.07107, and https://arxiv.org/abs/2604.19269
- Query-adaptive vector search priority alert: https://arxiv.org/abs/2607.29606
- Candidate-order consistency priority alerts: https://arxiv.org/abs/2604.27599 and https://arxiv.org/abs/2608.03091

Items dated 2025–2026 are treated as provisional priority/novelty alerts rather
than settled evidence. A broader systematic review is required before any
paper-level priority claim.
