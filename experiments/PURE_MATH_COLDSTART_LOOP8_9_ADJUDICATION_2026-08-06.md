# Pure-mathematics cold-start loops 8--45: adjudication

Date: 2026-08-06 (Australia/Sydney)

Status: literature-first hostile novelty audit. No outcome experiment was run
for a candidate that failed the novelty gate.

## Ledger

The reconciled portfolio contains **59 screened candidate families, 59
eliminated, and zero verified Tier-A survivors**. Candidates 37--40 were the
first new families adjudicated in this report; candidates 41--43 form the
immediately following graph-mathematics loop, and candidates 44--46 form the
next lifecycle/combinatorial/rigidity loop. Candidates 47--49 form the
graph-signal/graphex/sequential-graduation loop, and candidates 50--52 form the
slate-context/topology-uncertainty/partial-identification loop. Candidates
53--55 form the identifiability/information-theory/certified-robustness loop,
and candidates 56--58 form the clone-invariance/catalog-prefix/semantic-ID
loop. Candidate 59 is the new-user single-peaked top-k query family.
Subvariants are not counted as separate ideas when they share the same claimed
mechanism.

Documentation scope: this file gives row-level adjudications for candidates
37--59. Candidates 1--36 and their experiments are distributed across the
earlier Tier-A portfolio and pure-graph verdict artifacts rather than a single
one-row-per-ID table. The total is a reconciled mechanism-family count, not a
claim that 58 independent paper manuscripts or 58 outcome experiments exist.

| ID | Candidate family | Substantive novelty estimate | Feasibility | Decision |
|---:|---|---:|---:|---|
| 37 | Higher-order graph extension (Whitney jets; graph-WENO fallback) | 5--12% for jets; 25--38% for WENO | Moderate | Eliminate without POC |
| 38 | Laplacian-Coupled Cold-Launch Matching (LC2M) | 41% after independent hostile audit | 80--88% for a small offline POC | Eliminate as a standalone Tier-A method |
| 39 | Kirszbraun/AMLE vector cold extension with sharp rank regions | 17% algorithmic novelty | Point predictor feasible; exact rank endpoints do not scale | Eliminate without POC |
| 40 | BBP-certified semantic-to-collaborative shared-mode transfer | 30% algorithmic novelty | 95% implementation; 25% theory fit to repository | Eliminate without POC |
| 41 | Spectrally safe inverse-Dirichlet topology learning | 32% algorithmic novelty | 90% for support-preserving reweighting; 35--45% for topology change | Eliminate without POC |
| 42 | Degree-constrained spectral probe design | 25--30% Tier-A-ready confidence | 25% near-term theorem/implementation | Eliminate; retain only as a theory moonshot |
| 43 | Commutator-gated common-spectrum cold transfer | 31% algorithmic novelty | 70--80% small POC; 25--35% effect plausibility | Eliminate without POC |
| 44 | Landmark-Covariant Cold-Launch Regression (LCCR/MMOC) | 24% algorithm; 10% theorem | 72% descriptive POC; 28% faithful exposure-corrected study | Eliminate without POC |
| 45 | Hall-Certified Cold-Item Ingress (HCCI) | 30--38% overall; 10--20% algorithm | 85--90% synthetic implementation | Eliminate without POC |
| 46 | Task-/Top-K Rank Rigidity (TKRR) | 34--40% (point 37%) | 88--93% implementation; 20--35% useful query saving | Eliminate without canonical POC |
| 47 | Graph-TV cold-item probing | 15--22% | 90--95% KuaiRec POC | Eliminate without POC |
| 48 | Projective graphex future-vertex recommendation | 24% overall; 22% algorithm | 94% runtime; 82% EB-NeRD POC | Eliminate without POC; retain no-go lemma |
| 49 | Graph-certified cold-to-warm graduation | 10--20% algorithm; 8--18% theorem | 92--97% KuaiRec POC | Eliminate without POC |
| 50 | Strict-cold slate-context hypergraph/choice model | 22--32% | 82--90% predictive EB-NeRD POC; 10--20% causal validation | Eliminate without POC |
| 51 | Random-forest marginalization of uncertain cold edges | 15--25% | 85--90% engineering | Eliminate without POC |
| 52 | Exposure-sensitivity partial identification for strict-cold items | 33% overall | 86% simple implementation; 28% valid EB-NeRD causal verification | Eliminate without POC; retain zero-support lemma |
| 53 | Unified strict-cold identifiability frontier | 34--40% | About 85% for an executable audit; low for causal policy validation | Eliminate as theorem/algorithm; retain only as an audit framework |
| 54 | Information-theoretic semantic ceiling for personalized top-k | 32--38% | Exploratory audit feasible; rigorous algorithm-independent MI ceiling infeasible with current data | Eliminate without POC |
| 55 | Certified robustness to provider-controlled cold content/edges | 39% overall | 95% for embedding-space certificate; 25--32% for a non-vacuous realistic-semantic certificate | Eliminate without POC; retain red-team diagnostic |
| 56 | Graph-quotient invariance to duplicate/clone cold items | 32% overall | 95% for an exact-clone demo; about 50% for a meaningful near-clone study | Eliminate without POC; retain robustness metric only |
| 57 | Catalog-prefix-consistent birth-causal graph operators | 38% after independent hostile audit | 88% for an EB-NeRD audit; about 55--60% for material ranking/metric drift | Eliminate as theorem/algorithm; retain future-vertex contamination audit |
| 58 | Prefix-stable graph-coded semantic IDs | 40% overall | 92% for an index-only implementation; 53% for useful no-retraining end-to-end gain | Eliminate without POC |
| 59 | Gap-k Single-Peak Search for strict new users | 20--34% after two independent hostile audits | 85--95% for a one-sided assumption audit; about 10% for theorem-relevant ML-1M validation | Eliminate without POC; retain only as a supporting lemma |

The continuation threshold was at least 45% substantive novelty after hostile
audit. Exact recommender packaging was not treated as algorithmic novelty when
the estimator, theorem, and optimizer were inherited.

## Candidate 37: higher-order graph extension

The proposed cold-item jet extension collides with vector-field regularization,
Hessian energy, manifold moving least squares, graph trend filtering, and
graph-signal interpolation on expanding graphs. The WENO fallback also has
direct moving-least-squares and nonsmooth graph-interpolation ancestors. The
remaining recommender specialization is too thin for a Tier-A main method.

Representative boundaries:

- Parallel field regularization: https://papers.nips.cc/paper/2011/file/bc6dc48b743dc5d013b1abaebd2faed2-Paper.pdf
- Multi-task vector-field learning: https://papers.nips.cc/paper_files/paper/2012/file/a5e00132373a7031000fd987a3c9f87b-Paper.pdf
- Learning expanding graphs for signal interpolation: https://arxiv.org/abs/2203.07966
- Graph trend-filtering networks for recommendation: https://arxiv.org/abs/2108.05552

## Candidate 38: LC2M

For cold-item content Laplacian `L`, warm-user factor `p_u`, and
`a_ui = e_i tensor p_u`, the proposed objective was

    F(S) = logdet(P0 + sum_(u,i in S) sigma_ui^-2 a_ui a_ui^T)
           - logdet(P0),
    P0 = (alpha I + lambda L) tensor I, alpha > 0,

under upper degree caps at both sides of the user--cold-item bipartite graph.
The determinant lemma gives rank-one gains and PSD inverse order gives
monotone submodularity. These are generic Bayesian D-optimal-design facts. The
caps form a bipartite b-matching/two-system, so the 1/3 greedy guarantee is also
inherited.

The strongest direct collisions are:

- single-item cold-start optimal design and fold-in:
  https://arxiv.org/abs/1406.2431
- Yahoo's explicit multiple-new-item user--item allocation patent:
  https://patents.google.com/patent/US9910898B2/en
- attribute-driven batch active learning and user-burden motivation:
  https://arxiv.org/abs/1805.09023
- graph-regularized active matrix-entry sampling:
  https://arxiv.org/abs/1906.01087
- generic monotone submodular b-matching:
  https://arxiv.org/abs/2107.05793

No exact source was found for the complete conjunction of a cold-item GMRF,
two-sided caps, one offline joint D-optimal objective, and graph-coupled
posterior fold-in. That is a narrow formulation gap, not a new algorithm or
theorem. The independent hostile probability was 41%, below the frozen gate.

KuaiRec could only test reconstruction from masked cells in an unusually dense
historical matrix. It cannot validate counterfactual exposure, response,
fatigue, or causal watch lift. Therefore no dataset download or POC was
authorized. LC2M remains only a possible module if a new matrix-forest/effective
resistance benefit theorem, graph-specific scalable solver, stochastic-response
guarantee, or ranking-regret theorem is first developed.

## Candidate 39: Kirszbraun/AMLE extension

The point estimate

    min_(v,t) t  subject to ||v-v_i|| <= t d(x_c,x_i)

is exactly a one-vertex weighted vector-valued minimal Lipschitz extension.
Vector tight/minimal extensions and the grouped p-energy limit are already
published. Personalized Embedding Region Elicitation also occupies the
embedding-region/Chebyshev-center cold-start pattern.

- vector-valued tight extensions: https://arxiv.org/abs/1006.1741
- weighted vector-valued graph p-energy limit: https://arxiv.org/abs/1903.04873
- personalized embedding regions: https://proceedings.mlr.press/v244/nguyen24a.html

The sharp Kirszbraun identification region and support-function rank bounds are
correct short corollaries, but not enough for a Tier-A theorem. Empirically,
the repository's already-negative p=4 and p=8 path is additional adverse
evidence against the p=infinity endpoint.

## Candidate 40: BBP shared-mode transfer

Whitened semantic/collaborative cross-covariance, a CCA BBP cutoff, and
mode-wise shrinkage reduce to reduced-rank regression/CCA plus standard
spectral shrinkage. LoCo, CB2CF, and NFC already occupy content-to-collaborative
low-rank transfer. The repository has approximately `n=19,300` and `p=q=64`,
so `p/n` is about 0.0033 and the high-dimensional phase-transition premise is
weak. Learned embedding rows also violate the simple iid Gaussian null.

- finite-rank high-dimensional CCA: https://arxiv.org/abs/1704.02408
- optimal singular-value shrinkage: https://arxiv.org/abs/1405.7511
- LoCo: https://ssanner.github.io/papers/aaai17_loco.pdf
- CB2CF: https://www.noamko.org/papers/recsys19-sub1369-CB2CF.pdf

No POC was run because a gain over ridge would not turn an imported rank rule
into a novel recommender algorithm.

## Candidate 41: spectrally safe inverse-Dirichlet learning

This candidate learned content-only graph conductances by differentiating
through pseudo-cold harmonic extension, with a PSD sandwich around a baseline
Laplacian. Learning graph weights through leave-one-out harmonic loss and
implicit gradients is already established. The sandwich yields useful Schur-
complement, conditioning, and Dirichlet perturbation bounds, but not an
accuracy-improvement theorem. A fast edgewise parameterization preserves graph
support; actual topology changes require catalog-dependent semidefinite or
effective-resistance constraints.

- harmonic leave-one-out metric learning: https://papers.nips.cc/paper_files/paper/2006/file/fc325d4b598aaede18b53dca4ecfcb9c-Paper.pdf
- efficient learned graphs for harmonic SSL: https://proceedings.mlr.press/v216/sharma23a.html
- bilevel graph refinement with Laplacian regression: https://openreview.net/forum?id=10YJTIsVYq
- spectral-sparsification stability for graph SSL: https://proceedings.mlr.press/v97/zhu19b.html
- cold content-based graph reconstruction: https://research.google/pubs/content-based-graph-reconstruction-for-cold-start-item-recommendation/

The independent audit assigned 32% substantive algorithm novelty and killed
the candidate before a POC.

## Candidate 42: degree-constrained spectral probe design

Writing `v_ui = e_i tensor x_u`, simultaneous conditioning reduces exactly to
block E-optimal selection under a bipartite b-matching constraint:

    lambda_min(sum_(u,i in S) v_ui v_ui^T)
      = min_i lambda_min(sum_(u assigned to i) x_u x_u^T).

Minimum-eigenvalue selection under matroid constraints, max-min eigenvalue
augmentation, and degree-preserving matrix discrepancy/sparsification already
cover the practical relaxation-and-rounding route. A matrix-Chernoff guarantee
requires item budget on the order of
`d epsilon^-2 log(Md/eta)`, which is vacuous when genuine cold-start budgets
are only on the order of `d`.

- minimum eigenvalue under matroid constraints: https://arxiv.org/abs/2401.14317
- max-min eigenvalue augmentation: https://proceedings.mlr.press/v267/lamperski25a.html
- deterministic matrix discrepancy with linear constraints: https://arxiv.org/abs/2408.06146

An unweighted exact-degree, dimension-log-free spectral rounding theorem for
the bipartite transportation polytope could be new, but the probability of a
minor proof extension and executable algorithm was only 15--25%. This is a
pure-theory moonshot, not an experiment-ready direction.

## Candidate 43: commutator-gated common-spectrum transfer

Approximate joint diagonalization of semantic and collaborative Laplacians,
commutator-based common-mode certification, partial shared eigenspaces,
alternating diffusion for common/private variables, and Nystrom out-of-sample
extension are all established. The proposed commutator/eigengap result is an
existing identity plus Davis--Kahan perturbation, while reconstructing cold
collaborative targets from retained modes reduces to spectral regression or a
fixed projector. A current SIGIR 2026 paper also explicitly advocates
selective shared-factor integration while preserving private semantic and
collaborative information.

- joint diagonalization of Laplacians: https://arxiv.org/abs/1209.2295
- commutator norm and approximate joint diagonalization: https://arxiv.org/abs/1305.2135
- common-manifold alternating diffusion: https://arxiv.org/abs/1602.00078
- semantic/collaborative shared-private framing: https://arxiv.org/abs/2604.22195

The audit assigned 31% substantive novelty and killed the candidate without a
POC.

## Candidate 44: fixed-maturity launch regression

LCCR proposed cross-fitted historical launch episodes, a fixed-horizon
post-publication teacher represented by anchor-user scores, and a one-sided
local-linear content-to-preference operator for the next launch cohort. The
rotation-invariance claim is only the identity
`(U_A Q)(Q^T v_i) = U_A v_i`; arbitrary-user reconstruction also inherits the
conditioning error of `U_A`.

The proposed rate is classical boundary local-linear regression plus omitted
teacher, approximation, ridge, censoring, and calendar-cluster errors. More
importantly, a fixed horizon standardizes item age but does not remove
endogenous exposure. On EB-NeRD it estimates engagement under the historical
serving policy, not policy-invariant relevance. Cross-fitting prevents target
reuse; it does not correct missing-not-at-random exposure.

Direct boundaries include dynamic item-age/selection debiasing, temporal DRO,
warm-teacher alignment and inherited bias, lifetime-value prediction, and
cold-start lifecycle forecasting:

- DANCER: https://arxiv.org/abs/2111.12481
- temporal DRO for cold items: https://arxiv.org/abs/2312.09901
- inherited warm-teacher popularity bias: https://arxiv.org/abs/2510.11402
- item lifetime-value optimization: https://arxiv.org/abs/2108.09141
- cold-start lifecycle forecasting: https://arxiv.org/abs/2604.20370
- content-to-CF mapping: https://arxiv.org/abs/1611.00384

EB-NeRD has genuine publication times and impression logs, so a descriptive
policy-conditioned benchmark is feasible. It lacks randomized item inclusion
or logged inclusion propensities, and its six-week span provides only about 42
strongly correlated calendar blocks for temporal inference. The independent
audit assigned 24% substantive algorithm novelty, 10% theorem novelty, and
less than 10% ex-ante Tier-A package probability. The exact conjunction may be
unoccupied, but it is a composition of existing components; no POC was run.

## Candidate 45: Hall-certified cold-item ingress

HCCI scheduled relevance-eligible new items under exposure lower bounds,
upper capacities, and deadlines with min-cost flow, returning a minimum-cut or
Hall-type infeasibility witness. Both the optimizer and certificate are
standard flow duality. Existing recommender and advertising work already
allocates exposure with lower/upper constraints, including explicit support
for new content:

- MIREC constrained exposure for new content: https://arxiv.org/abs/2305.12319
- global user--item allocation by min-cost max-flow: https://arxiv.org/abs/2009.14474
- targeted allocation with chance constraints: https://arxiv.org/abs/1407.7924
- item-level exploration traffic allocation: https://arxiv.org/abs/2505.09033

The cold-item packaging and human-readable cut witness are useful engineering,
but neither supplies a new algorithm or theorem. The candidate received
30--38% substantive novelty and was eliminated before a synthetic feasibility
experiment.

## Candidate 46: task-/Top-K rank rigidity

For fixed user factors, probes give `y_S = P_S q` and the desired ambiguous-
user scores are `P_A q`. They are identifiable exactly when
`row(P_A) subseteq row(P_S)`, and the minimum noiseless probe count is
`rank(P_A)`. This is linear-functional estimability, or the zero-noise endpoint
of c-/transductive optimal design, rather than a new rigidity theorem. For
generic rank-`d` factors, any ambiguous set with at least `d` users has rank
`d`, so the method usually needs the same number of probes as full fold-in.

The nonlinear completion-fiber version is a local Jacobian row-span lemma. It
follows from established completion rigidity/algebraic closure and does not
give global sign invariance across disconnected completions.

- item-cold optimal design: https://arxiv.org/abs/1406.2431
- matrix-completion rigidity: https://arxiv.org/abs/0902.3846
- algebraic matrix-completion identifiability: https://arxiv.org/abs/1206.6470
- partial matrix completion: https://arxiv.org/abs/2208.12063
- personalized embedding-region elicitation: https://proceedings.mlr.press/v244/nguyen24a.html
- transductive linear experimental design: https://proceedings.neurips.cc/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html

The audit assigned 37% substantive novelty. Implementation is easy, but the
chance of a genuine query saving is only 20--35% because ambiguous user sets
generically saturate the latent dimension. The candidate was eliminated.

## Candidate 47: graph-TV cold-item probing

This candidate treated a new item's user-response residual over a warm user
graph as a graph-total-variation-sparse signal. It would query selected users,
recover the residual with graph fused lasso, and certify top-`k` ingress via a
binary min-cut formulation. The strongest available margin lemma is

    cut_w(sign(f)) <= TV_w(f) / (2 gamma),  when |f_u| >= gamma.

Every cut edge contributes at least `2 gamma w_uv`, so this is a one-line
corollary. Network-lasso recovery conditions, graph-TV sampling, active cut
location, min-marginal uncertainty, and deliberate user selection for a new
item are all established:

- item-cold attribute-driven active learning: https://arxiv.org/abs/1805.09023
- item-cold optimal design: https://arxiv.org/abs/1406.2431
- graph-TV/network-lasso sampling: https://arxiv.org/abs/1709.01402
- graph active cut learning: https://proceedings.mlr.press/v40/Dasarathy15.html
- weighted extension: https://arxiv.org/abs/1605.05710
- general-graph active-learning algorithms/hardness: https://proceedings.mlr.press/v267/cohen-addad25a.html

The content offset and top-`k` semantics do not change the estimator or
theorem. Substantive novelty is 15--22%. KuaiRec would support an unusually
clean dense pseudo-probe experiment, but no run was justified after the
literature gate failed.

## Candidate 48: projective graphex future vertices

For two strict-cold future items with empty neighborhoods and no informative
marks, conditional exchangeability under swapping the items forces identical
Bayes edge probabilities. Any deterministic vertex-permutation-equivariant
scorer must give them equal scores; randomized tie-breaking has expected
pairwise accuracy one half. This is a correct no-go observation, but not a new
recommendation algorithm.

When content marks break the symmetry, the Bayes score is

    eta(u,x) = integral W(z_u, xi) p(d xi | X=x, history),

which is ordinary content-conditioned dyadic regression or inductive matrix
completion. Graphex generative projectivity is inherited; pointwise score
projectivity already holds for two-tower models; top-`k` invariance to catalog
growth would prevent useful new items from entering the list.

- sparse-exchangeable bipartite PMF and split bias: https://arxiv.org/abs/1712.02311
- sparse exchangeable graph sampling: https://arxiv.org/abs/1611.00843
- provable inductive matrix completion: https://arxiv.org/abs/1306.0626
- zero-shot new-node all-link prediction: https://arxiv.org/abs/2401.05468
- content-based cold graph reconstruction: https://doi.org/10.1145/3626772.3657801
- temporal inductive graph completion/Shallow-RHS: https://arxiv.org/abs/2606.06225

The no-go lemma is useful supporting material and has high correctness
confidence, but only about 30% Tier-A theorem-novelty probability. Overall
substantive contribution probability is 24%; no POC was run.

## Candidate 49: confidence-certified cold-to-warm graduation

The proposed graph changepoint framing was incorrect: feedback accumulation
reduces epistemic uncertainty but need not change the item's latent preference.
The corrected estimator used a Laplacian Gaussian posterior over a
content-prior residual, certified each user's score against the current
`top-k` cutoff, probed the largest variance-reduction user, and graduated the
item when enough users were certified.

After subtracting the content prior and user cutoff, this is thresholding
graph bandits with a known offset. Existing graph bandits, Gaussian-random-
field sampling, and safe confidence switching already supply the posterior,
radius, probe rule, and stopping logic. Modern cold-to-warm gates also occupy
the application claim:

- thresholding graph bandits: https://proceedings.mlr.press/v108/lejeune20a.html
- Laplacian-regularized graph bandits: https://proceedings.mlr.press/v108/yang20c.html
- GRF active sampling: https://arxiv.org/abs/1209.3694
- PAM streaming cold start: https://arxiv.org/abs/2411.11225
- GateSID: https://arxiv.org/abs/2603.22916
- item-centric exploration: https://arxiv.org/abs/2507.09423

Algorithm novelty is 10--20% and non-inherited theorem novelty is 8--18%.
KuaiRec feasibility is 92--97%, but feasibility cannot rescue the novelty
failure; no experiment was run.

## Candidate 50: strict-cold slate-context choice

The strongest formulation combined a feature-based context-dependent choice
model with a content graph, learning warm low-rank cross-item effects and
harmonically extending their factors to a strict-cold article. Factorized
slate sums give `O(KR)` rather than pairwise `O(K^2 R)` scoring.

Both proposed mathematical angles reduce to known objects. A Möbius expansion
of set utility truncated at pairs is the context-dependent/Halo choice model;
feature-based LCL already generalizes explicitly to unseen items, and
DeepHalo already controls feature-based pair and higher-order inclusion--
exclusion terms. For an antisymmetric pair field, the Hodge gradient component
`q_ij = phi_i - phi_j` contributes `K phi_i` plus a slate constant that cancels
in softmax, leaving only the already-standard cyclic component as genuinely
context-specific.

- feature-context choice and unseen items: https://arxiv.org/abs/2009.03417
- DeepHalo higher-order feature choice: https://papers.neurips.cc/paper_files/paper/2025/hash/c717858997b6b999e58557ef7ff23da6-Abstract-Conference.html
- low-rank self-attention/Halo choice: https://arxiv.org/abs/2311.07607
- slate-aware ranking: https://arxiv.org/abs/2302.12427
- HodgeRank: https://arxiv.org/abs/0811.1067

EB-NeRD can test predictive unordered-slate likelihood, but its shuffled order
and absent logging propensities/randomization do not identify a causal item-
insertion effect. The future seven-day aggregates would also leak. Algorithm
novelty is 18--28%, theorem novelty 10--20%, and overall Tier-A probability
22--32%; no POC was run.

## Candidate 51: uncertain synthetic cold edges

For one cold node attached to clamped warm nodes, Dirichlet interpolation is
exactly the weighted warm barycenter, independent of the warm graph. A rooted
spanning forest chooses warm root `i` with probability proportional to the
same incident weight, so forest expectation reproduces the same estimator.
For cold cohorts, random-forest sampling is an unbiased numerical estimator of
the existing Laplacian solve, not a new population estimator. Bayesian edge-
set averaging is standard topology-posterior model averaging; edge sensitivity
is the Sherman--Morrison formula controlled by effective resistance.

- matrix-forest theorem: https://arxiv.org/abs/math/0602575
- random-forest graph interpolation: https://arxiv.org/abs/2011.10450
- uncertain-topology graph processing: https://doi.org/10.1109/TSP.2020.2976583
- incoming nodes with stochastic unknown connectivity and cold-start CF: https://arxiv.org/abs/2203.07966
- robust recovery under uncertain edge weights: https://doi.org/10.1109/LCSYS.2026.3702187
- certified edge-perturbation robustness: https://papers.neurips.cc/paper_files/paper/2019/hash/e2f374c3418c50bc30d67d5f7454a5b4-Abstract.html

The repository had already tested the relevant mechanism: direct graph
kriging improved ridge by 2.69% and 0.67%, below its frozen 5% gate, while
grounded resistance was near chance and almost a proxy for inverse support
mass. Substantive novelty is 15--25%; no new POC was run.

## Candidate 52: exposure-sensitivity partial identification

Under a finite odds-ratio sensitivity model around nominal exposure propensity
`e0(z)`, a strict-cold cell with `e0(z*) = 0` remains unexposed for every
finite sensitivity value. No outcome is observed and its sharp relevance set
is `[0,1]`: hidden-confounding sensitivity does not bridge a support hole.

Adding an externally specified Lipschitz restriction gives sharp cold bounds
by the McShane--Whitney envelopes of the warm-cell sensitivity intervals. The
identification then comes entirely from an untestable content-transfer metric
and constant. The sensitivity endpoints, no-overlap smoothness bounds, graph
extensions, and minimax-regret policy/ranking rules all have direct ancestors:

- recommender sensitivity analysis: https://doi.org/10.1145/3534678.3539240
- personalized MNAR hidden-confounding robustness: https://arxiv.org/abs/2605.21066
- minimax policy regret under propensity uncertainty: https://proceedings.neurips.cc/paper/2018/hash/3a09a524440d44d7f19870070a5ad42f-Abstract.html
- off-policy bounds beyond overlap via smoothness: https://arxiv.org/abs/2305.11812
- causal matrix completion: https://proceedings.mlr.press/v195/agarwal23c.html

EB-NeRD lacks the full eligible-but-omitted risk set, production inclusion
propensities, and recoverable display order. It can produce sensitivity curves
but cannot verify policy-invariant sharp bounds. Overall substantive Tier-A
probability is 33%; no POC was run.

## Candidate 53: unified strict-cold identifiability frontier

The proposed scalar frontier combined six distinct questions: protocol
validity, graph/topology informativeness, semantic sufficiency, candidate
reachability, causal support, and between-pool calibration. Exact component
statements are available. For example, if an isolated orbit of `m` items and
its target label are conditionally exchangeable, the best measurable top-`k`
success is `min(k,m)/m`; any two-stage ranker is upper-bounded by its frozen
generator's candidate recall; and an unsupported target-policy mass `alpha`
leaves a sharp bounded-reward interval of width `alpha`.

These are not one common impossibility theorem. They constrain different
objects: attainable prediction, deployable action classes, offline
identification, and score calibration. Their combination is a useful vector
audit, but the telescoping performance decomposition is standard Bayes
decision theory over nested information/action classes. Direct boundaries
include:

- deficient-support recommender OPE: https://arxiv.org/abs/2006.09438
- sharp OPE bounds beyond overlap: https://proceedings.mlr.press/v235/khan24b.html
- candidate-generator OPE: https://doi.org/10.1145/3705328.3748057
- support-aware two-stage policy selection: https://arxiv.org/abs/2604.23022
- Bayes-optimal top-k prediction: https://proceedings.mlr.press/v119/yang20f.html
- shared/private semantic--collaborative limits: https://arxiv.org/abs/2604.22195

The exact propositions are highly likely to be correct, and an engineering
audit is about 88% feasible. Substantive novelty is about 31% (25--35%); the
standalone Tier-A probability is 15--25%. Retain a six-dimensional diagnostic
as supporting infrastructure, never a scalar certificate. Existing repository
experiments already show that reachability alone is insufficient, so no new
POC was warranted.

## Candidate 54: information-theoretic semantic ceiling

For an oracle relevant set `S` of size `k` among `m` items and a content-only
prediction `S_hat`, conditional data processing plus lossy Fano yields a valid
lower bound on the probability of more than `t` set misses. With

    B_t = sum_(j=0)^t choose(k,j) choose(m-k,j),

the conditionally uniform form is

    P[misses > t] >=
      1 - (I(S; X | H) + log 2) / (log choose(m,k) - log B_t).

A binary-relevance argument converts the miss event into an NDCG-loss floor,
and `b` adaptive binary observations add at most `b log 2` information. These
are correct specializations of generalized Fano/rate--distortion, rather than
a new recommendation theorem:

- ranking rate--distortion: https://arxiv.org/abs/1401.3093
- multimodal-retrieval rate--distortion: https://arxiv.org/abs/2509.11054
- cold-start mutual-information learning: https://arxiv.org/abs/2107.05315
- cold-target two-stage value-of-information policy: https://arxiv.org/abs/1601.04745
- active cold-start information gain: https://proceedings.mlr.press/v32/houlsby14.html

The fatal empirical issue is directional: a rigorous impossibility certificate
needs an upper bound on `I(S;X|H)`. Contrastive estimators lower-bound mutual
information. CLUB is an upper bound with the exact conditional distribution,
but its learned variational version is explicitly not guaranteed to remain an
upper bound: https://proceedings.mlr.press/v119/cheng20b.html. Cross-fitting
only certifies the chosen model class. Substantive novelty is about 33%, an
exploratory model-class diagnostic is 84% feasible, and an honest
algorithm-independent certificate is about 16% feasible. No POC was run.

## Candidate 55: certified provider-content robustness

For a cold embedding `q`, fixed warm points `p_j`, and neighbor set `N_k(q)`,
the largest Euclidean ball that preserves the complete neighbor set is the
distance to the order-`k` Voronoi boundary:

    r(q) = min_(a in N, b not in N)
      (||q-p_b||^2 - ||q-p_a||^2) / (2 ||p_b-p_a||).

This is exact and locally implementable, but not new. Higher-order Voronoi
geometry and exact kNN certification already occupy the core, while ranking,
graph-injection, and recommender poisoning certificates occupy the downstream
top-`k` claim:

- higher-order Voronoi kNN geometry: https://arxiv.org/abs/2011.09719
- certified ranking under word substitutions: https://arxiv.org/abs/2209.06691
- certified top-N recommendation under poisoning: https://www.usenix.org/conference/usenixsecurity23/presentation/jia
- recommender graph-node-injection certificate: https://arxiv.org/abs/2312.03979
- collective graph-injection certification: https://proceedings.mlr.press/v235/lai24a.html

The provider attack is important but also directly occupied for cold-start
images, realistic diffusion images, and text rewriting:

- https://arxiv.org/abs/2006.01888
- https://arxiv.org/abs/2312.15826
- https://arxiv.org/abs/2409.11690

An embedding ball is not a faithful set of platform-valid semantic edits; that
gap makes the useful-looking certificate potentially vacuous. Overall novelty
is 39%. A correct embedding certificate is 95% feasible locally, but a
non-vacuous high-dimensional certificate is about 32% feasible and a realistic
semantic certificate about 25%. Retain only an empirical red-team diagnostic;
no POC was run.

## Candidate 56: graph-quotient clone invariance

This candidate proposed quotienting a cold-item similarity graph by exact or
near-duplicate equivalence classes, assigning mass at class level and dividing
it among class members so provider clone injection cannot multiply exposure.
The exact construction and its desirable invariance are already occupied by
clone-robust aggregation in arbitrary metric spaces:

- clone-robust quotient weighting and approximate-clone bounds:
  https://arxiv.org/abs/2602.24024
- duplicate exposure in recommendation:
  https://arxiv.org/abs/2110.15683

Equitable graph quotients and lumpability also make the exact-clone theorem a
standard symmetry reduction. A local exact-clone demonstration would be about
95% feasible and would almost certainly recover the analytic invariance, but
it could not establish novelty. Realistic near-clone ground truth and semantic
equivalence classes are substantially harder, and a useful result would be a
robustness metric or system module rather than a new recommender algorithm.
The independent audit assigned 32% overall substantive novelty; no POC was
run.

## Candidate 57: catalog-prefix-consistent graph operators

For catalog prefixes `V_s subset V_t`, exact linear restriction consistency
for every input is equivalent to the block identity

    R_s P_t = P_s R_s,
    P_t = [ P_s  0 ; B  C ].

If propagation is symmetric, the zero upper-right block also forces `B=0`.
Thus exact old-state invariance, symmetric propagation, and nonzero old-to-new
transfer cannot coexist. This is correct under the all-input formulation, but
it is coefficient matching plus a one-line symmetry observation rather than a
new graph theorem. It also imposes a stronger condition than causal
non-anticipation: an old representation may legitimately change at a later
query time when new information is then available.

A first audit scored a broader package at 52% and proposed a birth-directed
KL-projected kNN encoder. The required independent hostile audit lowered the
standalone theorem/algorithm probability to 38%, because the main phenomenon
and remedy have close direct ancestors:

- global-timeline recommender leakage:
  https://arxiv.org/abs/2010.11060
- new-node-induced changes to existing GNN outputs:
  https://arxiv.org/abs/2407.09173
- time-respecting temporal graph aggregation:
  https://arxiv.org/abs/2002.07962
- out-of-sample graph embedding without recomputing old embeddings:
  https://jmlr.org/papers/v22/19-852.html
- Firzen's warm-graph training, cold-node expansion, and explicit mask blocking
  strict-cold-to-warm propagation:
  https://arxiv.org/abs/2410.07654

The narrower empirical failure mode remains useful: future unlabeled vertices
can displace old kNN neighbors or change degree/attention denominators even
when their outgoing messages are masked. EB-NeRD has real article publication
and impression times and could support a prefix-only versus full-future graph
audit. Amazon's earliest interaction is not a trustworthy item-birth time.
The audit is about 88% implementable, but its probability of a material
ranking/metric effect is only about 55--60%, and a positive result would not
rescue the claimed algorithmic novelty. The candidate was therefore eliminated
without a POC; retain only the future-vertex contamination audit as a possible
reproducibility study.

## Candidate 58: prefix-stable graph-coded semantic IDs

This candidate replaced an expanding item-token vocabulary with fixed-alphabet
graph/path codes intended to give immutable item identifiers, semantic
locality, bounded prefix load, and no-retraining reachability for future cold
items. The construction faces a simple capacity obstruction. If the decoder
supports `S` prefixes and the resolver can distinguish at most `B` items per
prefix, at most `S B` items are universally reachable at that budget. Hence an
unbounded catalog cannot simultaneously have finite fixed-budget reachability,
bounded collision load, and immutable supported codes.

The remaining engineering space is already densely occupied by semantic-ID,
hierarchical-code, constrained-decoding, and online-reachability systems:

- purely semantic indexing: https://arxiv.org/abs/2509.16446
- CLEVER: https://arxiv.org/abs/2308.14968
- CRID: https://arxiv.org/abs/2607.11392
- temporal cold-item reachability: https://arxiv.org/abs/2607.21101
- item-supported decoding: https://arxiv.org/abs/2607.24995
- RecForest: https://proceedings.neurips.cc/paper_files/paper/2022/hash/2d049d52142b77c7796d71e52a83e1c2-Abstract-Conference.html

The counting obstruction is useful for stating tradeoffs but is not sufficient
as a Tier-A theorem. An index-only implementation is about 92% feasible; a
useful no-retraining end-to-end gain is about 53% feasible. Overall substantive
novelty is 40%, with only 18--25% Tier-A success probability. No POC was run.

## Unnumbered loop 15 mining result

Three independent searches were allowed to abstain before assigning candidate
IDs. All three did so, so the reconciled count remains 58 rather than being
inflated by preliminary formulations:

- An oriented-matroid/polyhedral cold-rank certificate reduced to robust
  ordinal regression and dual-cone/Farkas tests. Existing work already computes
  necessary and possible preferences over compatible value functions, and no
  observable strict-cold assumption links the semantic single-element
  extension to the unseen collaborative extension. Final substantive novelty
  was 20--30%, with only 20--35% probability of a valid nontrivial certificate.
- Protected-terminal navigability repair for a streaming ANN graph collided
  with Wolverine, CleANN, FreshDiskANN, and query-aware routing. It is about
  88% implementable but only 38--42% substantively novel, and is primarily
  vector-index maintenance rather than a recommendation contribution.
- Content-marked Pitman--Yor discovery calibration collapsed algebraically to
  the existing content ranker plus a user-level cold-pool offset. It cannot
  alter within-cold ordering, species-sampling unseen mass is not future
  catalog birth, and the repository's four-domain offset experiment is already
  adverse. Algorithm novelty was 28--35% despite 90--94% implementation
  feasibility.

No code, download, or outcome experiment was run for these unnumbered
near-misses because each failed the literature, identification, or algebraic
gate.

## Unnumbered loop 16 evidence-driven re-audit

Loop 16 deliberately revisited the two strongest evidence-backed remnants
rather than importing another mathematical object. Neither was promoted to
candidate 59:

- The narrow temporal cold-rank-equivalence/retrievability audit is
  mathematically correct but its theorem is a counting identity. Calibrated
  stacking, scale calibration, cross-group interleaving, candidate-set
  evaluation, temporal protocols, and generator-support work occupy every
  component. The existing clean four-domain run found at least one pointwise
  method-order reversal in every domain, but only one domain passed its range
  gate, none passed improvement versus zero, and the warm-safe wrapper had
  zero of four positively separated confidence intervals. The separate
  22-cell fixed-area validation also had zero passing cells. Standalone theorem
  novelty is 10--20% and current Tier-A probability is 3--7%; do not reopen the
  reserved split or run a post-outcome rescue POC.
- The NBHE directed-edge-to-node reduction is exactly a diagonally scaled
  specialization of the weighted Ihara--Bass vertex matrix, not a new general
  resolvent. A residual perturbation identity can express NBHE as ordinary
  harmonic extension plus an immediate-return Laplacian correction and recover
  the `O(1/d)` regular-graph collapse. This may support an appendix or
  specialist network-mathematics note, but estimated Tier-A recommender
  probability is below 1% and no more outcome experiments are warranted.

A feasibility reviewer estimated that a cross-family reversal falsification
POC would be 80--90% executable and proposed strict gates. The independent
novelty/materiality audit is controlling: its probability is below the 45%
gate and the prospective evidence is already adverse, so no POC was run.

## Candidate 59: Gap-k Single-Peak Search

This new-user formulation froze a user-independent item path
`v_1,...,v_n` and assumed a globally tie-free single-peaked utility sequence.
Its exact task was to recover the unordered top-`k` set, not the complete
preference order. If the top-`k` interval starts at `L`, then

    u_j < u_(j+k)  iff  j < L,
    u_j > u_(j+k)  iff  j >= L.

The gap-`k` comparisons therefore form a monotone bit string. Binary search
finds `L` in `ceil(log2(n-k+1))` comparisons, and the bound is minimax optimal
for deterministic exact noiseless binary queries because every one of the
`n-k+1` interval starts is realizable. The result needs a strict total
preference, not merely strict increase and decrease on each side: cross-side
ties otherwise make an unordered top-`k` target non-unique.

A second lemma is also correct. If the class is enlarged to sequences with at
most two local peaks, one unknown item can be raised above an otherwise
monotone baseline. An adversarial comparison transcript eliminates at most one
possible spike per query, so exact top-1 needs `n-1` comparisons; the ordinary
maximum tournament matches the lower bound.

The first audit assigned 48--55% novelty and nominated the package. Two
independent hostile audits rejected it at 34% and 20% substantive novelty.
Their objection is controlling: the upper bound is the conjunction of two
known facts--top-`k` upper-contour sets of a single-peaked order are intervals,
and a threshold can be found by binary search. Conitzer already binary-searches
the peak on a known single-peaked axis, while later social-choice work uses
top-`k` contiguity explicitly:

- single-peaked comparison elicitation: https://arxiv.org/abs/1401.3449
- tree single-peaked elicitation: https://arxiv.org/abs/1604.04403
- graph/path structure learned for neighborhood recommendation:
  https://arxiv.org/abs/2004.13602
- pairwise/attribute cold-start decision trees:
  https://arxiv.org/abs/2510.27342

The exact indexed lemma may be unpublished verbatim, but it is an elementary
corollary rather than a new algorithmic framework. MovieLens-1M cannot
validate the strict oracle because all ratings lie on a five-value scale;
arbitrary tie-breaking would manufacture preferences. Its sparse MNAR rows
can only provide one-sided violations of a frozen path. KuaiRec's 99.6%-dense
small matrix could simulate queries, but its implicit watch-ratio label and
lack of a natural one-dimensional item axis remain material limitations. A
positive experiment could not rescue the standalone novelty, so no POC or
dataset download was run. Retain the two lemmas only inside a genuinely new
noisy/robust learned-axis method.

## Unnumbered loop 17 companion abstentions

The other two loop-17 searches abstained before receiving IDs:

- Catalog-selection-adjusted cold promotion used simultaneous tail envelopes
  and post-selection safe swaps at the warm top-`k` boundary. It was 85--90%
  implementable locally but only 38--44% substantively novel. The top-`k`
  zoom correction, selected-winner inference, distribution-free recommender
  reliability, uncertainty-aware cold ranking, and conservative selection are
  already occupied. Existing strict-cold retrieval evidence also makes
  nontrivial certified coverage unlikely. No experiment was run.
- Shared-user-weighted ancestry-preserving partial homomorphism between Amazon
  category forests was 72% feasible but only 37% novel. The local domains
  genuinely share 1,490--4,026 stable user IDs per pair, yet CCDR, COUPLE,
  CATN, cross-domain knowledge graphs, and hierarchical-hypergraph transfer
  already occupy the recommendation mechanism, while maximum common-subtree
  matching supplies the graph primitive. No experiment was run.

## Unnumbered loop 18 partial mining result

Two further graph-mathematics formulations were eliminated before IDs:

- A bounded-Dirichlet-energy new-user signal with harmonic interpolation,
  sharp grounded-effective-resistance top-`k` intervals, boundary-aware
  queries, and Schur rank-one updates is mathematically sound and 90--95%
  feasible on KuaiRec. It is only 18--25% novel. Spectral Bandits already uses
  a disjoint-user MovieLens item graph; best-arm spectral bandits and GRUB
  already combine Laplacian smoothness, confidence elimination, effective
  resistance, and inverse updates; generic top-m linear-bandit identification
  supplies the top-`k` extension. No experiment was run.
- Robinson/Monge/single-crossing cold insertion was below 20% Tier-A novelty.
  Monge structure alone does not imply within-row unimodality. Adding the
  required one-dimensional ideal-point assumption returns to established
  single-peaked elicitation and metric/ideal-point learning; active noisy
  Robinson seriation, forbidden-pattern certificates, and path/tree
  recommendation structures are also occupied. Sparse MNAR data can falsify
  but cannot validate the structure. No experiment was run.

## Unnumbered loop 19 result

All three formulations failed before receiving candidate IDs:

- Tree-factorized one-step value of information for a binary audience tree was
  algebraically correct, but its objective is already the decision-theoretic
  graphical value-of-information/active-search objective. The remaining path
  product is standard tree inference. Substantive novelty was about 27%.
- Distributionally robust graph onboarding was defeated by a two-user hidden-
  spike construction: with no observable support at the new entity, an
  adversary can place the preferred user outside every proposed local graph
  neighborhood. A useful nonvacuous guarantee therefore requires an inherited
  realizability or overlap assumption, and the proposed robust wrapper was
  only about 35% novel.
- Electrical-budget few-shot exposure selection had a valid Laplacian dual,
  but reduced to graph experimental design, effective-resistance sampling, and
  fixed-confidence top-m identification. The recommender packaging did not
  create a new electrical theorem; novelty was about 35--40%.

No POC or dataset download was run.

## Unnumbered loop 20 result

Four graph-mathematics formulations were screened; none earned candidate ID 60:

- Semantic error-correcting catalog identifiers were only 10--18% novel after
  collision with error-correcting output codes, semantic IDs, and robust ANN
  indexing.
- Metric-dimension top-k onboarding was 30--40% novel. Its identifying-code
  primitive and active preference elicitation objective are both established,
  while realistic ratings do not supply the exact distance oracle required by
  the theorem.
- Spectral Panel Paving was independently rated 28% and 34% novel. Krause et
  al. already construct disjoint rotating informative sensor panels and
  optimize balanced/worst-panel prediction; spectral scheduling, A-optimal
  cold-item selection, and interlacing/paving results occupy the other pieces.
- Tree-ENS considered a binary Markov audience tree, one exposure/reward probe,
  and deployment to the posterior top `K-1` users. The Bernoulli path-affinity
  identity and a centroid/range-hull index give a plausible deterministic
  `O(n log^3 n + n K log^2 n)` all-actions algorithm (with real-RAM and
  nondegeneracy qualifications). Two independent reviews nevertheless placed
  substantive novelty at 42% and 27%. ENS already supplies the exact objective;
  graphical VOI and active new-item user selection supply the application; and
  centroid decomposition, upper envelopes, and generic top-k linear-ranking
  data structures supply the speedup. A strengthened general indexing theorem
  appears bibliographically unique with about 68% probability, but remains a
  short composition rather than a Tier-A recommender contribution. It also
  needs category-conditioned audience-tree estimates that are poorly
  identified at KuaiRec scale, and optimized quadratic brute force is likely
  faster at `n=1,411`.

No public-data utility POC was justified. The Tree-ENS index is retained only
as a possible synthetic algorithms note if a future linear-space, dynamic-
update, sharper-batch, or genuine lower-bound theorem is found.

## Unnumbered loop 21 result

All three formulations failed their gates:

- Online availability-aware spectral allocation cannot guarantee an
  informative panel for every arriving item under adversarial eligibility: a
  two-user/two-item construction can hide the only informative user whenever
  the relevant item arrives. The achievable stochastic version collides with
  online set cover, PSD resource allocation, sensor scheduling, discrepancy
  rounding, and current item-exploration work. Estimated novelty was 32--42%
  for the theorem and at most 42--48% for the full package, with only 18--27%
  conditional Tier-A probability.
- High-temperature Ising localization of the ENS action score was 25--35%
  novel. Chen and Mossel already prove total-influence localization and a
  deterministic near-linear additive approximation for influence maximization
  in bounded-degree uniqueness-regime Ising models; localized Dobrushin
  inference and ENS occupy the remaining machinery. A correct derivation needs
  total-influence decay and a buffered two-radius construction, not a single
  induced ball. Moreover, the uniqueness regime that makes computation fast
  also bounds the possible value of a probe, making a material cold-item lift
  unlikely.
- Availability-constrained, misspecification-robust graph probe-then-route has
  a sound resolvent certificate under a relative spectral precision sandwich,
  but the certificate is a standard ellipsoidal perturbation bound and its
  scalable top-k relaxation is conservative. Robust/decision-targeted
  experimental design, robust graph active learning, cold-item user selection,
  and sleeping bandits occupy the package; a July-2026 paper directly studies
  adversarially robust decision-aware Bayesian experimental design. Arbitrary
  unknown future availability also admits a two-continuation constant-regret
  counterexample. The exact package was rated 35--43% novel and 18--25% Tier-A
  conditional on an ordinary positive POC.

No POC or download was run. A narrower minimax-tight safe-to-probe/abstain
certificate, with matching lower bounds and a tree/bounded-treewidth algorithm,
is being treated as a materially different theorem candidate in the next loop.

## Unnumbered loop 22 result

All three graph-mathematics proposals were eliminated before POC:

- Minimum-cut-lattice audience probing correctly uses the Picard--Queyranne
  distributive lattice of all optimal cuts to propagate a queried label. With
  ordinary continuous unary and edge weights, however, the minimum cut is
  unique almost surely, so the lattice has no useful ambiguity and every query
  gain is zero. Quantization manufactures ties, while near-minimum cuts lose
  the compact lattice representation. Substantive novelty was 32--42% and
  conditional Tier-A probability 10--20%.
- Fractional-color safe launch applies valid dependency-graph concentration,
  but an observational user-similarity edge set is not a dependency or
  interference graph. Its missing-edge independence premise is therefore not
  identifiable in the available recommender data. Independent-set network
  experimental design and chromatic PAC bounds also occupy the method. Novelty
  was 25--35%, with 10--18% conditional Tier-A probability.
- Discrete-convex graph-community traffic allocation reduces either to
  classical separable concave optimization over a polymatroid or, with
  overlapping communities, to online submodular assignment. Google's 2025
  item-level exploration traffic allocator directly occupies the cold-item
  application. Novelty was 15--25%, with 8--15% conditional Tier-A probability.

A separate online graph-feedback `b`-matching formulation also failed. Its
conceptual core collides with 2026 Bayesian Probing on Graphs, volatile
combinatorial GP bandits, graph-feedback semi-bandits, and industrial cold-item
traffic allocation. Positive correlation destroys adaptive submodularity even
at arbitrarily weak coupling; correlation decay localizes inference but not
finite-horizon planning. Its exact problem package was 42--48% novel, but its
substantive algorithm/theorem only 30--40%, with 15--22% conditional Tier-A
probability. KuaiRec could provide only a synthetic availability/load replay.

No code, data, or outcome experiment was run in loop 22.

## Unnumbered loop 23 result

Minimax-safe graph probing was eliminated before POC.  Under the relative
precision band

```
(1-delta) P0 <= Q <= (1+delta) P0,
```

the exact worst-case covariance between a deployment contrast `c` and a probe
`i` is

```
[ |c' Sigma0 e_i| - delta sqrt((c' Sigma0 c) Sigma0_ii) ]_+
----------------------------------------------------------------,
                         1 - delta^2
```

so the adversary erases that probe exactly when its normalized correlation is
at most `delta`.  This is a correct regularized-effective-resistance lemma and
yields a conservative pair-switch certificate.  It does not yield the claimed
full minimax algorithm: outcome-wise robustification rectangularizes the
ambiguity set; the Loewner band destroys tree sparsity; exact cardinality-
constrained covariance selection contains Max-Bisection; and honest spectral
uncertainty is likely to force near-total abstention.  Robust experimental
design, robust information gain, safe recommendation, and Bayesian probing on
graphs also occupy the package.  Substantive novelty was 45%, conditional
Tier-A probability 22%, and useful-coverage probability 15--20%.

No code, data, or outcome experiment was run.

## Unnumbered loop 24 result

Two formulations were eliminated:

- A relative-sheaf/holonomy cold-extension certificate reused standard Schur,
  relative-Hodge, and gauge-invariance machinery.  More decisively, holonomy
  certifies internal transport consistency rather than cold-item accuracy:
  two worlds can have the same warm graph, content, maps, zero residual,
  trivial holonomy, and positive Dirichlet gap while assigning arbitrary and
  different collaborative embeddings to the cold item.  The intended
  certificate is therefore unidentifiable without a semantic-to-collaborative
  realizability assumption.  Novelty was below 50% and Tier-A probability
  below 30%.
- KS-Launch attempted to gate cold-item probing at the stochastic-block-model
  Kesten--Stigum threshold.  Its central below-threshold impossibility is
  false for reward-bearing adaptive exposure.  In a two-block SBM, probing a
  random user and, after a positive reward, exposing a graph neighbor achieves
  positive-reward rate `1/2 + beta^2 theta/6` for every assortativity
  `theta > 0`, including below KS.  KS blocks global community recovery, not
  local reward harvesting; label side-information can also remove the
  threshold.  Active SBM querying, graph active search/probing, sequential
  tests, and cold-item user selection occupy the remainder.  Substantive
  novelty was 33%, conditional Tier-A probability 20%.  KuaiRec is unusually
  feasible for this family because it has a social graph, dense rewards,
  upload dates, and content, but feasibility cannot rescue a false theorem.

No code, data, or outcome experiment was run.

## Unnumbered loop 25 result

Frustration-certified signed cold search was eliminated.  Removing frustrated
couplings of total absolute mass `B_s` from a signed Ising audience model and
gauging the balanced core gives the valid uniform decision bound

```
TV(P,Q_s) <= tanh(B_s),
regret_P(policy optimal for Q_s) <= 2 K tanh(B_s).
```

A signed-Laplacian Gaussian analogue follows from ridge edge leverage and a
relative precision sandwich, but does not hold for arbitrary graphical-lasso
edge deletion.  The global certificate is generally vacuous as `B_s` grows.
More importantly, TPAMI 2025 signed graph sampling already performs sparse
signed inverse-covariance learning, balance/gauge approximation, and
informative node sampling while exploiting anti-correlations; 2025 balanced
signed-precision learning, correlated-normal knowledge gradient, ENS, and
online signed graph sampling occupy the other components.  Strong balance is
also an implausible global model of multidimensional taste, and within-item
centering can manufacture negative correlations.  Substantive novelty was
30--40%, conditional Tier-A probability 12--22%, and probability of stable,
nearly balanced KuaiRec residual structure 15--25%.

No code, data, or outcome experiment was run.

## Unnumbered loop 26 result

Two apparent successors were eliminated without experiment:

- Decision-only graph-TV top-`K` probing was not materially different from
  candidate 47.  Its exact confidence envelopes are standard graph-TV
  min-marginals/linear programs, with parametric min-cut as a solver.  A path
  counterexample also kills a boundary-only query theorem: hide a high-response
  `K`-block among `floor(n/K)` disjoint blocks.  Every instance has only two
  boundary edges and constant TV, but `m` adaptive point probes succeed with
  probability at most `(m+1)/floor(n/K)`, hence require `Omega(n/K)` probes.
  Substantive novelty was 10--18%.
- Provider-side ontology metadata elicitation reduces exactly to equivalence-
  class determination when complete metadata assignments inducing the same
  deployed top-`K` form a class, and to decision-region determination under
  epsilon-regret.  EC2, HEC/DRD, decision-focused value-of-information,
  adaptive submodular ranking, and a June-2026 top-`K` active-feature-
  acquisition paper occupy the algorithm and guarantees.  Ontology constraints
  merely restrict the hypothesis/test map absent a new laminar/DAG theorem.
  KuaiRec has too few authentic provider fields, while masking Amazon metadata
  would validate only a synthetic missing-feature task.  Substantive novelty
  was 15--25% and real-setting feasibility 30--45%.

No code, data, or outcome experiment was run.

## Unnumbered loop 27 result

Two topology/flow formulations were eliminated:

- Exact top-`K` certification under uncertain new-node attachment has a
  one-line dual-norm solution only for a linearized ellipsoid.  For actual
  star insertion, a three-node path already admits endpoint-order reversal as
  one middle attachment varies.  Exact box certification reduces to
  multiaffine cofactor corners/interval inverse problems, while two-solve
  effective-resistance intervals are conservative.  This repeats candidate 51
  and generic robust ranking/certified graph perturbation.  Substantive novelty
  was 15--25%.
- CUTLINE minimized `gamma cut(S)-a(S)-beta |S|` over a user graph and ranked
  users by their parametric min-cut entry breakpoints.  Under `|S|=K`, the
  scalar `beta` cancels, so probes of global appeal have exactly zero fixed-
  budget top-`K` value.  More fundamentally, the nested cuts are precisely the
  level sets of the ordinary graph-TV proximal solution, so the breakpoint
  ranking is graph-TV-denoised unary ranking with a classical parametric-flow
  solver.  Variable-size use is only threshold/graduation; two-parameter
  escape can have exponentially many optimal cuts.  Algorithm novelty was
  8--15% and conditional Tier-A probability 3--8%.

No code, data, or outcome experiment was run.

## Unnumbered loop 28 result

Graph-local harm certification defined a capped adversarial user reweighting
with degree-normalized graph-TV radius.  It correctly upper-bounds average
harm for every minimum-mass, low-conductance user set, admits an LP/CVaR dual,
and supports a coordinatewise Hoeffding upper certificate.  The result is an
immediate intersection of graph-scan relaxations, minimum-mass latent-group
DRO, no-demographic subgroup auditing, topology-aware adversarial reweighting,
and high-confidence novel-action recommendation.  The exact ambiguity set may
be absent verbatim, but substantive novelty was only 38--44% and conditional
Tier-A probability 18--25%.

Feasibility also failed at the scientific rather than optimizer layer.  Only
146 of KuaiRec's 1,411 users have social edges; degree weighting drops isolates
and uniform weighting can degenerate toward CVaR.  Sparse Amazon logs lack
paired counterfactual outcomes, propensities, and per-user replication needed
for the advertised certificate.

No code, data, or outcome experiment was run.

## Unnumbered loop 29 result

Anytime-valid graph calibration of synthetic cold-item users was eliminated.
For binary outcomes, the likelihood-ratio process

```
E_t = product_s (q_s/p_s)^Y_s ((1-q_s)/(1-p_s))^(1-Y_s)
```

is a nonnegative martingale, and Ville's inequality remains valid under
adaptive user selection, but only under the strong sequential null
`P(Y_t=1 | F_(t-1), u_t)=p_u`. Ordinary marginal calibration does not imply
that null: two graph communities with response probabilities `0.75` and
`0.25` can both be assigned `p=0.5` while remaining marginally calibrated.
Failure to reject is also not a safety certificate. A path with a hidden
positive block gives constant graph boundary but requires `Omega(n/K)` point
probes. Sequential calibration e-values, safe calibration tests, active
testing, calibrated graph scans, off-policy confidence sequences, conservative
bandits, safe novel-action recommendation, and 2026 calibration-gated LLM
pseudo-observations occupy the package. Substantive novelty was 35--45% and
conditional Tier-A probability 12--22%.

No code, data, or outcome experiment was run.

## Unnumbered loop 30 result

Cartesian-product graph tomography was eliminated. Existing 2018 work already
studies sampling and reconstruction of product-graph signals, including an
active-learning formulation for recommendation. More decisively, the exact
bandlimited subspace on a product graph has dimension `product_j k_j`, not
`sum_j k_j`; fewer scalar probes leave a nullspace containing indistinguishable
signals with different top-`K` decisions. Escaping through additive or rank-one
structure reduces to classical factored/tensor models. The required observable
factor graphs are also brittle or absent on the current public datasets.
Substantive novelty was 8--18% and conditional Tier-A probability 5--12%.

No code, data, or outcome experiment was run.

## Unnumbered loop 31 result

Append-only temporal-prefix cold-item retrieval was eliminated as a Tier-A
algorithm. Dynamic navigating nets, persistent cover trees, online spanners,
streaming and range-filtered ANN, and content-only cold-item ANN recommenders
already occupy the algorithmic core. Metric stretch does not imply top-`K`
recall: true neighbors at distance `1` and arbitrarily many distractors at
`1+epsilon/2` permit zero recall under a valid `(1+epsilon)` ANN answer. With
unchanged warm scores, the exact merge identity is

```
|W_K minus R_K| = |R_K intersect C|,
```

so a quota certificate merely restates the number of cold items returned; a
nontrivial recall-versus-displacement guarantee needs margins or distributional
assumptions. HNSW implementation feasibility was 85--95%, but substantive
algorithm novelty was 28--38% and conditional Tier-A probability 10--18%.

No code, data, or outcome experiment was run.

## Unnumbered loop 32 result

Median-graph/CAT(0)-cube cold-user elicitation was eliminated. On a partial
cube, comparing endpoints of an edge in one Theta class reveals the target's
corresponding halfspace under a weighted-Hamming ideal-point model. This is
exactly established graph binary search/noisy edge-query search. Medianity does
not imply logarithmic elicitation: on a star, a negative center-versus-leaf
comparison eliminates only that leaf, so exact top-1 needs `n-1` queries in the
worst case. Ordinary distance top-`K` sets need not even be convex on a median
graph. Substantive algorithm novelty was 18--25%, faithful catalog feasibility
15--25%, and conditional Tier-A probability 5--10%.

A read-only PowerShell structural diagnostic, not an outcome POC, found that
12,101 Beauty items collapse to 254 category-incidence vectors. Only 49.665%
of 5,080 sampled triples had their coordinatewise-median vector present,
versus 100% for a median-closed code; the largest Hamming-one component had
56 vectors and 58 were isolated. A synthetic cube experiment was therefore
not authorized.

## Unnumbered loop 33 result

Multiscale diffusion-source localization for a cold item's audience was
eliminated. Sparse mixtures of heat kernels at multiple scales, recovery of
sparse diffusion sources from partial samples, and adaptive graph sampling are
already established. Bernoulli top-`K` probing then reduces to sparse linear or
generalized-linear pure exploration. The hoped-for universal `O(s log n)`
bound is false: on `K_n`,

```
exp(-t L) = J/n + exp(-nt) (I-J/n),
```

so every non-source probe has the same mean and exact localization of even one
source requires `n-1` distinct point probes in the worst case. Meaningful
bounds must depend on graph automorphisms, dictionary coherence, source
amplitude, KL separation, and decision margins. Overall Tier-A probability
was 3--8%.

No code, data, or outcome experiment was run.

## Unnumbered loop 34 result

The separately executed claim `p*(N) proportional to N^0.843` was eliminated
as a verified law. The saved 12-run curve is arithmetically reproducible, but

```
p* = c/(g+c),       p*/(1-p*) = c/g.
```

Because `p*` is bounded, it cannot follow a global power law. The component
fits instead imply break-even odds `c/g` proportional locally to approximately
`N^1.06`; the reported `0.843` is a range-dependent slope of the saturating
map `a N^gamma/(1+a N^gamma)`. A pure nuisance offset in the same artifacts
already produces `p*` slopes 0.458--0.475.

The experiment also kept the total 24,587-item catalog fixed and converted
warm items into synthetic cold items. Retained training interactions fell from
385,175 to 276,746 of 396,958, so cold-pool size was bundled with training
density, donor availability, calibration, target composition, and a growing
train/evaluation mismatch. One fixed nested capset and three optimizer seeds
provide no item-set replication. The untracked direct-Python run also lacked
the mandatory Windows-safe locks, handshakes, ledgers, and completion marker,
so it is noncanonical evidence. Narrow diagnostic novelty was 45--55%, but
current Tier-A probability only 5--8%.

No root-owned outcome experiment was run.

## Unnumbered loop 35 result

Seeded content--collaborative graph alignment was eliminated. Paired warm-node
alignment is established semisupervised manifold/functional-map alignment, and
content-to-collaborative transfer is crowded in recommendation. More
fundamentally, the observables `(G_content, G_collab[W], warm interactions)` do
not identify missing collaborative rows for cold items. Two worlds can agree
on every observable while reversing two cold-item preferences, forcing top-1
error at least `1/2` under their equal mixture. If a content-graph automorphism
fixes all warm nodes and exchanges two cold nodes, every equivariant method
must also treat them identically. In functional-map regression, any nonzero
`N` with `Phi_W N=0` and `Phi_C N!=0` produces the same warm fit and different
cold predictions. Dirichlet-energy assumptions yield tight resistance bounds,
but their required cold energy budget is unobservable. Substantive algorithm
novelty was 8--18% and conditional Tier-A probability 3--8%.

No code, data, or outcome experiment was run.

## Unnumbered loop 36 result

Menger-robust cold extension was eliminated.  For any desired local
connectivity, one may hold the observed content graph and every warm embedding
fixed while choosing two observationally identical strict-cold worlds with
latent cold embedding `Rv` and `-Rv`.  The same path aggregator is returned in
both worlds and has error at least `R` in one of them.  Connectivity therefore
does not identify cold preference even with no adversary.  The realistic
provider-content attack is worse: corrupting the common cold source changes
every path and may rebuild its incident kNN edges, so `2f+1` internally
disjoint routes do not represent `2f+1` independent information channels.

A valid but conditional residue remains.  If the cold source and graph are
trusted, paths terminate at distinct trusted anchors, at most `f` non-source
paths are corrupted, and every clean path estimate is already within a known
`epsilon` of the unknown cold embedding, the geometric median of more than
`2f` paths inherits a standard robust-median error bound.  Node-splitting plus
integral max-flow computes the route packing.  This directly composes Menger,
Byzantine multipath, and robust graph aggregation; the fatal `epsilon` is not
observable from path agreement.  Mathematical novelty was 15--25%, real-
threat scientific feasibility 30--42%, and standalone Tier-A probability
5--12%.

No code, data, or outcome experiment was run.  A synthetic path-corruption POC
would merely reconfirm the assumed median breakdown model and could not repair
preference identification or the source-corruption mismatch.

## Unnumbered loop 37 result

The existing offset/rank-equivalence package was eliminated as a verified
survivor.  Its narrow theorem is correct: with a fixed candidate set and
masks, adding a context-specific constant to all cold scores preserves
within-cold order, monotonically helps a cold single target, and monotonically
hurts a warm single target.  The identity `p*=c/(g+c)` also holds for fixed
conditional means, but it is descriptive rather than a causal deployment
threshold.

The sibling exploratory evidence did not validate the proposed empirical
decomposition.  Its quantity called within-cold AUC awards ties as full wins
and leaves masked seen-cold competitors in the denominator.  Its claimed
offset-matched efficiency ratio instead chooses the first active point from a
coarse offset grid: in all ten runs this was `delta=8`, whose cold gain was
1.37--1.47 times the method gain in one pool and 2.38--2.74 times it in the
other.  The operating points were therefore not matched.  Full-catalog and
cold-only NDCG also do not form an additive decomposition.  The artifacts are
exploratory and noncanonical, while the root-owned four-domain temporal audit
found material improvement over zero in zero of four domains and a positive
wrapper confidence interval in zero of four.

The theorem-only application has about 30% package-level substantive novelty
and 3--8% Tier-A probability as-is.  A future evaluation study would have to
use eligibility- and tie-correct within-cold AUC, cross-pool AUC, exact score-
margin offset frontiers, a context-adaptive offset null, and at least three
true global-time datasets.  It is not candidate 60 and no corrective outcome
POC is authorized in this loop.

## Unnumbered loop 38 result

Schur-resolved cold-node insertion was eliminated.  The exact block inverse
for a regularized combinatorial-Laplacian resolvent is sound, and sparse fixed
attachments admit ordinary Woodbury updates using old-factorization solves.
This is established expanding-graph filtering rather than a new algorithm.
For the exact updated solution, Laplacian conservation gives

```
1^T Delta + x_c = h/tau,
```

so every unit of graph-induced cold lift beyond the isolated content term is
balanced by aggregate warm-score displacement.  Exact preservation of all
warm scores therefore forces zero graph-induced cold lift.  Full displayed
warm top-`K` preservation is also logically incompatible with a cold item
entering that list; preserving only the warm-only order reduces to a standard
score-margin check.

Choosing at most `b` attachment edges to make the cold score cross a threshold
for as many users as possible contains Maximum Coverage even in a simplified
binary instance, so the advertised exact near-linear optimizer cannot exist
in general.  Existing expanding-graph prediction/filtering, vertex-insertion
updates, graph-filtering recommenders, and cold-item link promotion closely
occupy the remainder.  Standalone algorithm novelty was 15--25%, meaningful
strict-cold empirical feasibility 40--55%, and Tier-A probability 5--12%.

No code, data, or outcome experiment was run.  The block formula and
conservation identity may be retained as an implementation/audit lemma inside
a different main method.

## Unnumbered loop 39 result

Transport-matched temporal pseudo-cold evaluation was eliminated.  If a
method's conditional mean loss is invariant from a historical pseudo-cold
source to the future-cold target and is Lipschitz in a fixed metadata-graph
metric, Kantorovich--Rubinstein plus weighted concentration yields an ordinary
Wasserstein covariate-shift risk bound.  The same inherited argument can bound
a pairwise method-loss difference.  Under conditional shift, however, the
bound requires an additional unobservable conditional-risk discrepancy.

The identification failure is exact.  Let metadata contain one point, so the
source and target covariate marginals have Wasserstein distance zero.  Two
future worlds can agree on every observed covariate and reverse the losses of
methods A and B.  A metadata-only selector must return the same ordering in
both and is wrong in one.  User, slate, competing-item, and serving-policy
context create further shift not repaired by matching item marginals.

Wasserstein source reweighting, unlabeled-target performance estimation and
model selection, temporal-shift model selection, graph-OT source selection,
OT site/coreset selection, and dense-ground-truth recommender evaluation
already occupy the algorithmic core.  Exact cold-recommender packaging may be
40--50% novel, but substantive algorithm novelty was 15--25%, theorem novelty
5--10%, valid full-catalog feasibility 15--25%, and Tier-A probability 5--12%.

No code, data, or outcome experiment was run.  A policy-conditioned EB-NeRD
description would not rescue either the inherited method or the full-catalog
identification failure.

## Unnumbered loop 40 result

Grounded-Laplacian/effective-resistance allocation of first cold-item feedback
was eliminated as a duplicate of candidate 38, LC2M.  With pair feature
`a_(u,i)=e_i tensor p_u`, Gaussian precision `Q0`, and selected exposures `S`,

```
F(S) = (1/2) logdet(Q0 + sum_(e in S) tau_e a_e a_e^T)
       - (1/2) logdet(Q0)
```

is ordinary Bayesian D-optimal information gain.  The determinant lemma and
PSD inverse order give inherited monotonicity and submodularity; cardinality
greedy has `1-1/e`, while simple greedy under two-sided user/item capacity has
the familiar `1/3` guarantee.  In the scalar grounded-Laplacian special case,
the leverage score is exactly a resistance-to-ground quantity.  A-, E-, and
G-optimal criteria do not receive a blanket submodularity guarantee, and the
personalized block precision does not automatically inherit a nearly-linear
scalar Laplacian solver.

Item-only resistance also misses personalized identification.  If queried
user factors span a strict subspace `H`, an arbitrary cold-factor component in
`H`'s orthogonal complement leaves every queried rating unchanged but alters
an unqueried user's score.  Direct cold-item optimal design, attribute-driven
active user selection, graph-regularized matrix-entry sampling, Gaussian-
field/graph-signal design, and production item-centric exploration occupy the
package.  Standalone algorithm novelty was 15--25%, honest causal feasibility
25--40%, and Tier-A probability 8--15%.

No POC was run.  A dense KuaiRec masking study would test reconstruction, not
the counterfactual exposure, nonresponse, fatigue, or welfare claim.

## Unnumbered loop 41 result

Graph-symmetry-breaking cold probes were eliminated.  A correct invariant-
score lemma needs a typed/feature-preserving automorphism that maps the two
items while fixing the target user and scoring context.  For an `L`-layer
shared node-MPNN, equal initial features and equal `L`-round 1-WL color are a
sufficient architecture-specific tie certificate.  These are standard GNN
equivariance/expressivity facts, including prior recommendation-specific
automorphism analyses.

For deterministic tests whose complete item response codes are known in
advance, selecting tests that separate every cold-item pair is exactly Test
Cover.  Greedy inherits its logarithmic Set-Cover approximation, and budgeted
pair coverage inherits `1-1/e`.  Click probes do not meet that model: outcomes
are unknown and stochastic, a common user test costs one impression per item,
and adaptive information gain needs explicit likelihood and adaptive-
submodularity conditions.  Arbitrary unique IDs can break numerical symmetry
without adding preference information.  Two swap-related latent worlds remain
observationally identical with reversed relevance, giving minimax pairwise
error at least `1/2`.

The contribution therefore reduces to a cheap WL-collision diagnostic followed
by established active cold-item learning or abstention.  Substantive novelty
was 12--22%, meaningful experimental feasibility 20--35%, and standalone
Tier-A probability 2--6%.

No code, data, or outcome experiment was run.  The architecture-specific WL
diagnostic can be retained only as an auxiliary audit.

## Unnumbered loop 42 result

Graph missing-mass cold exploration was eliminated.  Classical Good--Turing
estimates the probability mass of species absent from IID draws from a fixed
distribution; it does not estimate relevance of policy-unexposed or future-
born items.  Recommendation histories are contextual, policy-censored,
dependent, and nonstationary.  Even stationary Markov sampling needs explicit
mixing-time corrections.

The identification failure is exact.  Two strict-cold graph-automorphic cells
can have identical observed histories and graph energy while their reward
means are swapped.  Any observable exploration rule acts identically in both
worlds and has worst-case success at most `1/2`, or `1/K` across `K` equivalent
cells.  Positive-only logs also confound exposure and relevance without known
propensities and displayed non-clicks.

Under no-repeat strict-cold exploration, every clicked item is a singleton, so
the cell statistic `F1_c/n_c` is simply empirical cell click-through rate and
the proposed policy reduces to category UCB.  Overlapping multiscale graph
cells invalidate Good-UCB's disjoint-support theorem; restricting to leaf
cells restores the existing theorem and removes the claimed multiscale
mechanism.  Graph smoothing then becomes an ordinary spectral/content bandit,
and adding a warm-safety wrapper composes with established conservative
bandits.

Implementation feasibility was 90--95%, but faithful identification/theorem
feasibility 12--22%, substantive novelty 12--20%, and Tier-A probability
2--6%.  No POC was run: dense or synthetic replay would merely recover
category-CTR UCB or assumptions built into the simulator.

## Unnumbered loop 43 result

One-release user-private graph cold extension (DP-GCE) was eliminated.  The
privacy claim is correct but standard: if `V_tilde_W=M(D)` is one
`(epsilon,delta)` user-level-DP release and the public content graph is
partitioned into warm and cold blocks, then

```
H = -L_CC^(-1) L_CW,       V_hat_C = H V_tilde_W
```

and any finite or adaptive transcript of public harmonic extensions has the
same privacy guarantee by post-processing.  Cortes' collective-MF cold
formula and RecSys 2023 DP-CMF with public features/similarities nearly imply
this system directly.  A harmonic public encoder changes the feature map, not
the private mechanism.

The conditional residue is mathematically sound.  Under graph energy at most
`S`, the misspecification at cold node `v` is bounded by `S g_v`, with
`g_v=(L_CC^(-1))_vv`; iid warm-factor noise adds
`d sigma^2 ||h_v||_2^2`.  This is not catalog-independent: `Q` cold leaves
attached to one warm anchor give `||H||_F^2=Q`, and weakly grounded or
disconnected items remain unidentifiable.  The graph cannot use new private
telemetry without more privacy accounting.

Substantive algorithm novelty was 12--22%, narrow adapter novelty 25--35%,
implementation feasibility 85--92%, and standalone Tier-A probability 3--8%.
No POC was run.  The existing canonical DIRE/GERU evidence had already shown
that resistance was almost only inverse boundary mass and barely predicted
error, so a new run would not rescue the novelty failure.

## Unnumbered loop 44 result

Side-information AMP for strict-cold zero-observation rows (SI-AMP-ZR) was
eliminated.  In the standard exchangeable collective model, a cold item has no
rating factor incident to it, hence, conditional on shared parameters,

```
p(B_C | D, theta) = product_(c in C) p(B_c | X_c, theta).
```

With unknown `theta`, warm ratings help only through the posterior over that
shared parameter.  A joint AMP and an exact two-stage Bayesian method
integrating the same posterior therefore target the same cold estimator.  In
state evolution the cold type simply has zero rating-channel precision and
uses the content denoiser.  For the scalar Gaussian channel, the MMSE is
`1/(1+gamma)`, so no generic nonzero covariate threshold exists; making the
shared loading unknown returns to the already occupied CCA/BBP regime.

Multitype AMP, AMP with side information, multimodal AMP uncertainty,
collective-MF zero-row prediction, minimax transfer with entirely missing
rows/columns, and covariate empirical-Bayes matrix factorization occupy all
substantive pieces.  The repository's constant-degree-like, positive-only,
temporal-MNAR graph is also far outside the dense iid-Gaussian asymptotic
regime, while the raw feature term would dominate runtime.

Algorithm novelty was 5--12%, zero-row theorem novelty 2--8%, faithful
repository theorem feasibility 10--20%, and Tier-A probability 1--4%.  No POC
was run because a synthetic result would only reproduce established state
evolution.

## Unnumbered loop 45 result

Extreme-value-calibrated cold injection (EVCI) was eliminated.  Under iid warm
scores with CDF `F`, the probability that cold score `c` reaches top `K` is a
classical binomial/order-statistic expression.  When the warm scores are
already available, the exact `K`th threshold is known and EVT replaces an
exact computation by an estimate.  A shared monotone tail transform preserves
the complete within-cold order and only alters cross-pool reach.  Item-local
tail maps can reorder cold items but no longer share the distribution required
by the proposed guarantee and still do not identify relevance.

Marginal tails do not determine catalog competition under dependence.  For
`K=1`, identical warm-score marginal `F` yields maximum-below-`c` probability
`F(c)^N` under independence but `F(c)` under perfect dependence.  If scores
are calibrated relevance probabilities, ordinary top-`K` is already Bayes
optimal; if only poolwise calibration holds, cross-pool ordering is
unidentified.  Existing EVT retrieval, rank-specific recommendation
calibration, learned top-`K` thresholds, cold-score regularization, cold/warm
gating, recommendation FDR control, and graph-fused tail estimation occupy
the package.

Exact theorem novelty was 3--8%, algorithm novelty 12--22%, faithful temporal
risk-validation feasibility 25--40%, and Tier-A probability 3--6%.  No POC was
run.  Retain only the empirical warm `K`th threshold or normalized reach as a
diagnostic, not as a new recommender.

## Experimental status

These loops added no **canonical outcome experiment**. A read-only exploratory
diagnostic for candidate 46 was run once in CPU-only, single-threaded WSL and
exited without an exception, but it produced no source/result manifest,
persistent logs, locks, or completion record and bypassed the hardened Windows
launcher. It is therefore explicitly excluded from reproducible evidence and
will not be rerun.

Earlier pure-graph POCs remain valid evidence:
p-harmonic `p=4,8` lost to `p=2`; tangent-connection extension lost every fold;
innovation kriging missed its frozen 5% gate; and nonbacktracking harmonic
extension improved all folds but by only 0.03342% and 0.04471%, far below its
0.25% continuation gate. See
`experiments/PURE_GRAPH_COLDSTART_LOOP_VERDICT_2026-08-06.md`.

## Next novelty-first loop

The privacy/AMP/EVT loop failed all novelty and identification gates.  The
next loop begins with a benchmark-level graph question: whether recursive
`k`-core filtering on the complete interaction graph before a chronological
split conditions future-cold inclusion on post-cutoff outcomes, and whether a
prefix-causal protocol can expose and prevent resulting cohort and method-rank
distortion.  Two additional independent graph-mathematics candidates will be
generated and audited in parallel. A proposal will receive ID 60 only after it has an
exact research question, mathematical mechanism, executable falsification
test, explicit nearest-prior boundary, an observable target, and independent
hostile-review support. An untestable semantic-to-collaborative or exposure
assumption is an immediate rejection. No experiment is authorized until the
proposal clears the literature, identification, theorem, and independent-
hostile-review gates.
