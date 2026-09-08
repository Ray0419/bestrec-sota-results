# Tier-A cold-start research verdict after four prospective screens

> Later graph-mathematics supplement: the p-harmonic, DIRE/GERU,
> tangent-connection, and nonbacktracking harmonic loop is adjudicated in
> `PURE_GRAPH_COLDSTART_LOOP_VERDICT_2026-08-06.md`. It found a real but
> practically negligible NBHE mechanism and stops fixed-topology operator
> swaps.

Date: 2026-08-05 (Australia/Sydney)

## Bottom line

There is no experimentally validated new cold-start algorithm in the current
portfolio. Four prospective mechanism screens rejected their proposed main
claims. The highest-confidence publishable direction is now a **measurement
and evaluation contribution**, while one substantially different algorithmic
idea deserves a small preregistered screen.

The recommended order is:

1. pursue a cold-start rank-equivalence and reachability audit as the main
   research program;
2. give identifiability-bounded shared/private transfer one cheap screen;
3. keep reachability-controlled candidate injection as a conditional systems
   module; and
4. defer corrupted-anchor repair.

The numerical confidence below estimates whether the *exact gap* remains
defensible after the current targeted search. It is not an acceptance
probability. A focused systematic Scholar/DBLP review is still mandatory
before a first/novel claim.

| Rank | Research question | Exact contribution to defend | Gap confidence | Decision |
|---:|---|---|---:|---|
| 1 | When can a cold-start benchmark reward a score change that learns no new cold-item relevance, and when is the target structurally unreachable before ranking? | Rank-equivalence theorem and audit suite decomposing candidate reachability, between-pool calibration, and within-cold ranking under global time | 0.60 | Main program |
| 2 | Which collaborative directions are actually identifiable from content for a zero-interaction item? | Cross-fitted shared-subspace certificate that reconstructs only estimable collaborative factors and preserves view-private factors | 0.55 | One bounded screen |
| 3 | Can new-item candidate injection guarantee reachability with a certified warm-traffic displacement budget? | Model-agnostic semantic candidate union plus finite-policy risk certificate and temporal reachability metrics | 0.45 | Conditional module |
| 4 | Can corrupted warm semantic/collaborative correspondences be detected without mistaking legitimate private signal for corruption? | Cross-fitted anchor validation/repair with clean-safety and corruption-identification tests | 0.35 | Defer |

## Evidence from this repository

| Screen | Prospective result | What survives |
|---|---|---|
| RQ1: cold-pool offset plus warm-safe wrapper | Wrapper failed in all four domains; no positive paired confidence interval | Exact offset/rank-equivalence theorem, intervention curves, and method-order reversals |
| RQ2: representation-selective semantic FIR | Identity selected in both domains; full-catalog strict-cold gains exactly zero | Evidence of a full-catalog retrieval floor and a semantic/collaborative identifiability problem |
| RQ3: learned-cost anchored UOT | Failed safety, shift, unmatched-retrieval, recovery, and runtime gates | Anchoring is necessary; synthetic retained mass was only a clue |
| RQ4: fixed-UOT retained-mass router | AUROC 0.507 and 0.486; Spearman 0.017 and -0.010; all efficacy gates failed | A clean falsification: retained mass is not a useful natural-data failure score here |

These are complementary failures. They rule out a uniform score wrapper, a
minor FIR variant, learned-cost UOT mapping, and UOT-mass routing. They point
toward the boundary between *being scoreable/retrievable* and *learning
relevance*, and toward estimating only the cross-view information that content
can identify.

## RQ-A: Cold-start Rank-Equivalence and Reachability Audit

### Research question

> Under a global-time catalog, when do candidate construction or pool-wise
> score transformations improve reported cold-target metrics without changing
> any ordering among cold items, and how much apparent model failure is instead
> structural target unreachability?

### Contribution

Define two recommenders as cold-rank-equivalent for a query when they induce
the same ordering inside the available cold pool. Any score transformation
constant on that pool—including a cold offset—leaves cold relevance unchanged
but can monotonically improve full-catalog metrics conditioned on a cold
target by moving the whole pool above warm items. Separately, a target absent
from a retriever's representable candidate support cannot be repaired by its
ranker.

The publishable package is not the failed RQ1 wrapper. It is:

1. a theorem and taxonomy of rank-equivalent nuisance transformations;
2. a decomposition into target reachability, between-pool selection, and
   within-pool relevance;
3. an audit that applies cold offsets and candidate-support probes to existing
   methods and measures method-order reversals;
4. absolute-time catalog availability and mixed cold/warm demand; and
5. a reporting standard with reachability@K, conditional-on-reachable ranking,
   within-cold NDCG, pool calibration, mixed NDCG, and warm-user tail harm.

### Why it is the strongest direction

RQ1 already proves and demonstrates the rank-equivalence defect. RQ2 then
produced exactly zero full-catalog cold gain despite a small semantic signal,
showing why retrieval and ranking should be separated. Recent work independently
raises the same evaluation boundary from another angle:
[Cold-Starts in Generative Recommendation](https://arxiv.org/abs/2603.29845)
calls for unified cold protocols, while
[Can Generative Recommendation Reach Cold Items?](https://arxiv.org/abs/2607.21101)
finds that unseen tokens or unsupported semantic-ID paths can make future items
unreachable. Neither paper, based on the current audit, supplies the exact
rank-equivalence theorem plus cross-pool nuisance intervention and mixed-
traffic decomposition.

Broad evaluation claims are already occupied. Schein et al.'s classic
[Methods and Metrics for Cold-Start Recommendations](https://doi.org/10.1145/564376.564421)
compares cold-start test methodologies;
[On Target Item Sampling](https://doi.org/10.1145/3383313.3412259) shows that
target-set choices can contradict or invert comparative conclusions;
[Cold Item Integration](https://arxiv.org/abs/2112.07615) studies the conflict
between promoting cold items and preserving warm accuracy; and Cold Items
Precision already measures the fraction of cold recommendations
([Parambath and Chawla, 2020](https://doi.org/10.1007/s10618-020-00708-6)).
Accordingly, this project cannot claim the first cold-start metric, mixed
warm/cold evaluation, target-set critique, or warm/cold trade-off. Its claim
must remain the exact group-constant rank-equivalence result, its intervention
audit, and the joint reachability/between-pool/within-pool decomposition under
absolute time.

### Tier-A bar and kill rule

Use at least four global-time datasets, including an impression/slate dataset,
and reproduce at least eight discriminative, two-stage, and generative methods.
The paper becomes strong only if nuisance offsets materially change several
reported conclusions or method rankings, and the decomposition explains those
changes across domains. Kill the main-paper claim if the effect is confined to
one small Amazon split or if existing papers already report the same theorem
and stress test.

## RQ-B: Identifiability-Bounded Shared/Private Transfer

### Research question

> Can a zero-interaction item's content identify only a low-dimensional shared
> component of its collaborative representation, and does reconstructing only
> those certified directions improve temporal retrieval over unrestricted
> content-to-collaborative mapping?

### Candidate algorithm

On warm item pairs `(semantic x_i, collaborative z_i)`, estimate whitened
cross-covariance inside each training fold. Compare its singular spectrum with
a permutation/noise spectrum and retain only directions whose out-of-fold
predictability clears a prospective threshold. Map content into this certified
shared subspace, shrink weak directions to zero, and leave the view-private
component to a content expert instead of hallucinating a full collaborative
embedding. Fusion weights come from direction-level estimability, not an
item-level learned gate.

The theoretical target is a finite-sample excess-risk or lower-bound statement:
unrestricted recovery of the private collaborative component is impossible
without interactions, while thresholded recovery is safe on identifiable
directions under explicit covariance-shift assumptions.

This directly answers the structural diagnosis in the SIGIR 2026 paper
[Rethinking Semantic-Collaborative Integration: Why Alignment Is Not Enough](https://arxiv.org/abs/2604.22195),
which models shared and view-private factors and reports that low-capacity
mappings recover shared but not full collaborative geometry. The claim must be
narrow because [GateSID](https://arxiv.org/abs/2603.22916) already performs
adaptive semantic/collaborative gating, and
[Shallow-RHS](https://arxiv.org/abs/2606.06225) already learns a standalone
content tower for temporal zero-interaction retrieval. The novelty would be
the *estimability certificate plus selective directional reconstruction*, not
alignment, gating, or content-to-CF transfer itself.

### Cheap prospective screen

Reuse the two frozen q60 warm representation tables and their temporal test
interfaces. With five item folds and fixed ranks selected only from training
folds, compare thresholded shared-subspace transfer against ridge, reduced-rank
ridge/PLS, CCA, the content expert, and the existing adapters. Stop unless both
domains achieve at least 5% lower out-of-fold collaborative residual NRMSE than
ridge and a nonzero full-catalog temporal cold gain. Only then build the full
onset experiment.

This is the best algorithmic shot, not a high-confidence contribution yet.
Shared/private multi-view learning is a crowded area, so the exact theorem and
temporal protocol must survive a broader literature audit.

## RQ-C: Reachability-Controlled Cold Candidate Injection

### Research question

> Can a model-agnostic cold-item candidate generator guarantee useful temporal
> reachability while bounding displacement of warm candidates and warm-user
> tail risk?

Construct a semantic user-query-to-new-item ANN channel and union its top
candidates with an existing collaborative retriever. Select the cold quota
from a finite policy family using a separate temporal calibration window; the
ranker remains unchanged. The claimed contribution would combine a target-
reachability guarantee, a warm-displacement/risk certificate, and global-time
evaluation—not merely "add a content retriever."

This direction is crowded. [Next-User Retrieval](https://arxiv.org/abs/2506.15267)
already targets cold-item exposure/retrieval,
[GenRecEdit](https://arxiv.org/abs/2603.14259) injects cold items into
generative recommenders while preserving original quality, and Shallow-RHS
already supports ANN retrieval for newly ingested content. It is worth keeping
only if the explicit reachability-versus-warm-displacement certificate is both
new and empirically nontrivial.

## RQ-D: Robust Anchor Validation and Repair

RQ3 showed a promising ground-map point estimate under 20% synthetic anchor
corruption, but its downstream NRMSE interval crossed zero. The core
identification problem is severe: a semantic/collaborative discrepancy may be
legitimate view-private signal rather than a bad correspondence. A future
screen would need known corruption regimes, negative controls with genuine
private factors, robust-regression and trimmed-OT baselines, and a clean-data
safety gate. It is lower priority than RQ-B.

## Explicit no-go list

Do not spend the next experiment budget on:

- the RQ1 warm-safe scalar wrapper;
- another small semantic FIR or lag-depth variant;
- learned-cost CR-UOT;
- fixed-UOT retained mass as an item router or abstention score;
- a generic uncertainty gate, semantic/collaborative gate, or content-to-CF
  projector; or
- a generic candidate-injection module without temporal reachability and warm-
  displacement guarantees.

Current work already occupies broad gating, confidence, and transfer claims.
For example, BrainPICM uses UOT assignments as per-sample confidence outside
recommendation ([paper](https://arxiv.org/abs/2606.29695)); thus RQ4 could not
have claimed generic UOT confidence even if it had passed.

## Recommended next move

Write RQ-A as the primary paper plan and run its broad reproduction audit. In
parallel, spend only one bounded CPU/GPU screen on RQ-B. Do not run RQ4 K1 and
do not tune any of the four rejected mechanisms. This allocation gives the
repository one highest-confidence modular contribution and one genuinely new
algorithmic bet without confusing novelty with a positive result.
