# Phase 1, Cycle 5: Cardinality-Safe Retrieval and Boundary-Aligned Ideation

Date: 2026-08-07  
Status: complete; Phase 2 may begin  
Outcome access: no cycle-5 dataset, validation label, or test label was opened

## Why a fifth Phase 1 was required

FACET-PREF was killed before its first validation candidate manifest. A fixed
depth-700 collaborative search did not leave the required 200 unseen items after
removing a long interaction prefix. This is not an unlucky hyperparameter. For a
request with history set `H`, any retrieve-`D`-then-filter operator can return
fewer than `K` eligible items whenever more than `D-K` retrieved items lie in
`H`. For arbitrary histories, no fixed `D < |I|` guarantees `K` survivors.

This exposes a systems invariant that the prior ideation missed: **candidate
cardinality must be guaranteed by the retrieval construction before preference
quality is evaluated.** Tuning 700 upward on the consumed cohort would not solve
the general problem and is prohibited.

## Current-state collision scan

The scan focused on primary sources and official implementation documentation.

- FAISS documents `IndexFlat` as exact exhaustive search and documents ID
  filtering, over-fetch-and-post-filter workarounds, and `-1` outputs when fewer
  than `k` results are available. Its public issue tracker also records the
  practical limitation that batched searches do not naturally accept an
  independent selector for every query. These establish exact search and
  filtering as known infrastructure, not a novelty claim.
  ([FAISS index guide](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index),
  [FAQ](https://github.com/facebookresearch/faiss/wiki/FAQ),
  [per-query selector issue](https://github.com/facebookresearch/faiss/issues/3046))
- Filtered-DiskANN and ACORN build filtered ANN indexes, while approximate window
  search studies predicate-aware retrieval. Therefore “filtered ANN” or
  adaptive probing alone is occupied systems territory.
  ([Filtered-DiskANN](https://harsha-simhadri.org/pubs/Filtered-DiskANN23.pdf),
  [ACORN](https://doi.org/10.1145/3654923),
  [Approximate window search](https://proceedings.mlr.press/v235/engels24a.html))
- SimPO removes the reference model and uses a length-normalized reward and
  target margin, but its ordinary pairwise objective supervises relative order,
  not whether a preferred item crosses the deployed candidate-admission cutoff.
  ([SimPO](https://arxiv.org/abs/2405.14734))
- User Interest Boundary learns a user-specific interest boundary, and CIGAR
  learns candidate-oriented recommendation stages. Consequently neither a
  generic interest threshold nor candidate-aware learning is new by itself.
  ([User Interest Boundary](https://arxiv.org/abs/2111.11026),
  [CIGAR](https://arxiv.org/abs/1909.05475))
- Speculative generation/retrieval already uses draft-and-verify structure.
  A guaranteed base plus optional semantic swaps is therefore a weak novelty
  position and also repeats the sparse-intervention failure seen in RAVEL and
  CAPER. ([SpecGR](https://arxiv.org/abs/2410.02939))

## Four critical bottlenecks

### C5-L1 — Post-filter depth is not a cardinality certificate

The common pattern “retrieve top `D`, remove history, keep `K`” confuses a work
budget with an output contract. Under long or highly concentrated histories it
can silently underfill or require unregistered retries. Exact masked top-k,
predicate-aware indexes, or a depth bound that explicitly includes the excluded
set are needed to make feasibility a construction-level invariant.

### C5-L2 — Pairwise alignment optimizes order, not branch admission

For a two-branch hybrid, a semantic item has value only if it crosses the
semantic branch's `K`th eligible score after collaborative candidates and history
are excluded. A SimPO-style chosen-versus-rejected margin can improve pair order
while moving neither endpoint across that boundary. This objective/action
mismatch helps explain why earlier residual and selector mechanisms changed too
little of the served preference surface.

### C5-L3 — Overlapping branches spend budget without adding support

Independent collaborative and semantic top-k searches can return the same items.
Deduplication then shrinks the union or triggers backfill. Defining the semantic
domain as the exact complement of history plus the already admitted collaborative
branch makes every semantic slot additive and makes ownership auditable.

### C5-L4 — Correctness and scalable latency are different claims

Exact masked search supplies the reference semantics, but a production system
may require filtered ANN or cardinality-certified probing. Quality experiments
must use an exact oracle so approximation cannot masquerade as alignment; the
systems experiment must separately measure recall, work, and tail latency of an
approximate implementation against that oracle.

## Structured brainstorming pass

The brainstorming skill's four operations were applied explicitly.

1. **Constraint removal:** remove the assumption that a fixed pre-filter depth
   is the serving budget; keep the exact post-filter output budget instead.
2. **Assumption reversal:** rather than aligning a query and hoping a chosen item
   enters top-k, train against the actual eligible `K`th admission boundary.
3. **Boundary analysis:** make the exclusion set and branch complement first-class
   domains, so the failure condition is impossible for eligible requests.
4. **Analogy transfer:** borrow stop-gradient target construction from
   reference-free alignment, but use the deployed retrieval cutoff as the
   reference-free target rather than a second policy model.

## Creative-thinking pass

The creative-thinking skill was used to widen and then contract the search.

- **Bisociation:** combine cardinality-certified database retrieval with
  reference-free preference alignment. Their intersection suggests a learning
  target defined by the database operator's decision boundary.
- **Reformulation:** recast candidate generation as constrained admission rather
  than similarity ranking. The question becomes “does the chosen item clear the
  eligible branch cutoff?”
- **Failure inversion:** FACET-PREF's underfilled row becomes a property test that
  every successor must pass under adversarial history saturation.
- **Subtraction:** remove online LLM inference, item re-embedding, index rebuilds,
  learned request gates, and optional swap selectors. The remaining learnable
  object is a small user-query adapter.

## Divergent candidates and disposition

| Rank | Candidate | Disposition |
|---:|---|---|
| 1 | **CABLE-PREF**: cardinality-assured boundary learning | Selected. Couples exact complement retrieval to the actual semantic admission cutoff. |
| 2 | Complement-conditioned query adapter with a reserve lane | Reserve. Feasible but the reserve is an extra hand-designed budget. |
| 3 | Private-view residual semantic index | Reserve. Strong disjointness, but index duplication weakens the immutable-index advantage. |
| 4 | Single product-space top-400 search | Rejected. Generic hybrid embedding with no branch-specific causal test. |
| 5 | Pair-witness twin-head retrieval | Rejected. Can game co-support without improving served utility. |
| 6 | SAFE-SWAP guaranteed base plus semantic speculation | Rejected. Repeats sparse selection and overlaps draft/verify retrieval. |
| 7 | Progressive filtered-ANN probing | Systems baseline only. Occupied by filtered ANN and does not solve alignment. |
| 8 | Flexible union/backfill | Rejected. Hides branch underfill and makes the action surface variable. |
| 9 | Submodular preference diversification | Rejected. Adds online combinatorial selection and changes the target. |
| 10 | Disjoint semantic/collaborative lanes | Rejected. Hard lane censorship can discard the best item. |
| 11 | Bound or truncate user history | Rejected. Changes the user task to accommodate the implementation. |

## Selected direction: CABLE-PREF

**CABLE-PREF** stands for **Cardinality-Assured Boundary Learning for
Preference-aligned retrieval**.

For an eligible request `u` with at least 400 unseen catalog items:

```text
B_u = ExactMaskedTopK(BPR(u), exclude=history(u), k=200)
D_u = catalog \\ (history(u) union B_u)
S_u = ExactMaskedTopK(semantic(q_u), domain=D_u, k=200)
C_u = B_u union S_u                         # exactly 400 unique unseen items

t_u = stop_gradient(200th eligible semantic score in D_u)
L_admit = I[chosen not in B_u] * softplus(beta * (t_u + delta - score(chosen)))
L_order = softplus(beta * (margin - score(chosen) + score(rejected)))
L_CABLE = L_admit + lambda * L_order
```

The exact masked operator is a feasibility foundation, not the claimed
contribution. At scale it becomes the oracle against which filtered-ANN or
cardinality-bound over-fetch implementations are tested. SentenceTransformer
item embeddings and their FAISS index stay immutable; only a small semantic
query adapter is trained.

## Narrow novelty boundary

The candidate claim is **not** masked top-k, filtered ANN, multi-branch hybrid
retrieval, SimPO, candidate-oriented learning, or user-interest thresholds.
The defensible intersection is:

> branch-complement, admission-boundary alignment of an immutable dense retriever,
> with exact cardinality certification and end-to-end preference, relevance, and
> latency evaluation.

Unlike User Interest Boundary, the target is the detached `K`th score of the
actual eligible semantic branch after request-specific exclusions. Unlike
CIGAR, learning changes a dense query so preferred endpoints cross that deployed
cutoff. Unlike ordinary SimPO, admission—not merely pair order—is directly
penalized. This is a candidate whitespace pending broader review, not an
exhaustive novelty proof.

## Phase 2 handoff

Phase 2 must lock one falsifiable question on an unopened dataset. Its primary
mechanism outcome must test preferred-item semantic admission, and its utility
outcome must test strict preference-consistent exposure on the served top 10.
Mandatory controls are raw exact-masked hybrid retrieval, order-only
reference-free alignment, admission-only alignment, and collaborative BPR. The
gate must also require exact 200+200 cardinality, relevance non-inferiority,
changed-surface support, seed stability, latency, immutable-index integrity, and
an external source-bound verdict. Any failed conjunct kills CABLE-PREF and returns
the sprint to Phase 1.

