# Pure-graph cold-start loop: final verdict

Date: 2026-08-06 (Australia/Sydney)

Status: post-experiment synthesis. This report does not alter any frozen
protocol, manifest, source, or outcome artifact.

## Bottom line

The new nonbacktracking harmonic extension (NBHE) proof of concept is valid
and its proposed mechanism is real, but the exact recommender direction is
eliminated. It improved every one of ten folds and its paired intervals exclude
zero, yet its RMSE reductions were only 0.03342% and 0.04471%. Both fail the
prospectively frozen 0.25% continuation gate, and they are 29.9 and 22.4 times
smaller than the separate 1% Tier-A effect flag.

This is a practically negligible result, not an inconclusive one. The
independent audit confidence in killing exact NBHE as a performance
contribution is above 97%. Do not run temporal K1, tune a partial-backtracking
parameter, or create a node-wise beta gate from these outcomes.

More broadly, four distinct pure-operator attempts now agree: the fixed
semantic graph contains a useful cold-start signal, but changing the diffusion
operator does not extract a material additional signal. No high-confidence
Tier-A pure-graph algorithm remains on this fixed topology.

## What was tested

| Mathematical idea | Prospective or isolated result | Decision |
|---|---|---|
| Vector p-harmonic extension | p=4 and p=8 were worse than ordinary p=2 harmonic extension on Beauty and Fashion; p=8 also did not settle reliably in the fixed IRLS budget | Eliminate the nonlinear p>2 direction |
| DIRE plus grounded-effective-resistance uncertainty | Innovation kriging improved ridge by 2.69% on Musical and 0.67% on Industrial, but missed the frozen 5% gate; direct harmonic was stronger, and the proposed resistance certificate was near chance/degree-like | Keep direct harmonic as a baseline; eliminate DIRE/GERU as the claimed contribution |
| Tangent-connection harmonic extension (TCHE) | Lost to scalar harmonic in all ten folds: -0.01918% and -0.01446% | Eliminate exact connection transport |
| Absorbing nonbacktracking harmonic extension (NBHE) | Won all ten folds with positive intervals, but only +0.03342% and +0.04471% | Mechanism confirmed; eliminate exact algorithm |

TCHE showed that global propagation through cold-cold edges is useful but
parallel transport is not. NBHE then isolated immediate two-step echoes and
showed that removing them helps consistently, but by far too little to support
an algorithm paper.

## NBHE mathematical contribution

For a cold directed edge e=(i->j), NBHE solves the absorbing first-hit system

    M_(i->j) = [B_j + sum_(k in C, k != i) w_jk M_(j->k)] / (d_j - w_ij),

and returns

    F_i = [B_i + sum_(j in C) w_ij M_(i->j)] / d_i,

where B_i is direct warm boundary mass and d_i is total weighted degree.
Direct warm support makes the lifted transition substochastic, which gives
uniqueness, almost-sure absorption, constant reproduction, and a maximum
principle.

The main implementation result is an exact reduction from the directed-edge
lift to one sparse node-space solve. For

    Delta_ij = d_i d_j - w_ij(d_i + d_j),

the reduced system K F = B has

    K_ii = d_i [1 + sum_j w_ij^2 / Delta_ij],
    K_ij = -w_ij(d_i - w_ij)d_j / Delta_ij.

When all Delta_ij are positive, K is a strictly row-diagonally-dominant
nonsingular M-matrix and K 1 equals the direct warm mass. In an unweighted
full d-regular graph, the reduction becomes

    K_NB = D_h + [(d-1)/(d-2)] L_CC.

This identity explains the empirical result: relative to ordinary harmonic
extension, nonbacktracking changes the cold-cold coupling by only
1/(d-2)=O(1/d). The theorem, solver, and negative result are worth preserving
as an appendix or an applied-mathematics seed. They are not currently a Tier-A
recommender contribution.

Publication priors after the result are below 3% for a Tier-A recommender
algorithm, 3-8% for Tier-A general ML/mathematics, and roughly 20-35% for a
specialist applied-mathematics/network note if the work is expanded with a
determinant or resolvent identity, a complete Delta=0 treatment, spectral and
conditioning bounds, and solver-complexity guarantees. Nearby weighted
node-space nonbacktracking machinery further narrows the claim.

## Independently recomputed NBHE result

| Domain | Scalar harmonic RMSE | NBHE RMSE | Relative reduction | Frozen bootstrap 95% | Fold wins | Reduced/scalar solve time |
|---|---:|---:|---:|---:|---:|---:|
| Musical Instruments | 0.13399006 | 0.13394528 | 0.03342% | [0.03119%, 0.03551%] | 5/5 | 1.264x |
| Industrial and Scientific | 0.08108989 | 0.08105363 | 0.04471% | [0.04176%, 0.04819%] | 5/5 | 1.304x |

The preregistered immediate-return statistic beta behaves exactly as predicted.
The Q4/Q1 gain ratios are about 4.01 and 4.71. Even the Q4 gains, however, are
only 0.0564% and 0.0819%, still 4.43 and 3.05 times below the 0.25% gate. Beta
therefore explains where the tiny effect occurs but does not define a viable
rescue subgroup.

The independent audit recomputed every pooled and per-fold RMSE, the frozen
400-resample fold-stratified bootstrap, beta quartiles, all central gates, and
the decision directly from the two row NPZ files. It also reconstructed the
source, residual, graph, component, and fold hashes; verified the 20-file
manifest; established exact parent-comparator parity; and confirmed one unique
accepted run. Stderr and the asynchronous-exception ledger are empty, both
locks were released, and no Windows thread or unraisable exception occurred.

## Why further operator swaps should stop

Partial-backtracking tuning is both post-hoc on these domains and weakly novel.
Backtrack-downweighted walks already have a mature matrix-function theory, and
recent walk-based Laplacians explicitly interpolate between ordinary and
nonbacktracking diffusion.

Two apparent next operators also fail a literature-and-structure gate:

1. A grounded Bethe Hessian is an established deformed-Laplacian and
   nonbacktracking surrogate. At r=1 it returns the ordinary Laplacian; away
   from r=1 it loses constant reproduction, while a row-sum correction
   collapses to a scalar multiple of L. Estimated Tier-A prior: 3-8%.
2. Quadratic hypergraph propagation is classical and can be graph-equivalent;
   the node-valued simplicial 0-Laplacian B1 B1^T is exactly an ordinary graph
   Laplacian. Nonlinear hypergraph p-Laplacians and cold-item hypergraph
   recommenders are already occupied. Estimated Tier-A prior: 2-6%.

Grounded biharmonic, curvature reweighting, another p value, and another sheaf
or connection should likewise not receive experiment budget without genuinely
new information or a much sharper theorem.

## Research questions that remain worth discussing

### RQ-G1: Spectrally safe inverse-Dirichlet topology learning

Can collaborative supervision on warm items learn a content-only conductance
function for newly inserted items, while a spectral-equivalence constraint
guarantees that the learned graph remains connected, stable, and efficiently
solvable under strict pseudo-cold splits?

This changes the topology rather than the operator. A defensible version would
cross-fit all collaborative supervision, learn conductances usable from content
alone at inference, and constrain

    (1-epsilon)L_0 <= L_theta <= (1+epsilon)L_0

in PSD order. The mathematical contribution would be an adjoint/Schur
inverse-Dirichlet estimator plus a prediction-stability or excess-risk bound
under the spectral sandwich. The empirical gate should require at least 1%
improvement over fixed-graph harmonic extension on two fresh domains, wins
over generic metric learning and Content-based Graph Reconstruction, and no
warm/rank-calibration harm.

This is the only coherent graph-specific pivot, but it is not high confidence:
generic graph learning and cold graph reconstruction already occupy much of the
territory. Current Tier-A prior is only about 15-25% unless the precise
identifiability/stability theorem survives a deeper novelty audit. It merits a
new literature-first loop, not an immediate outcome-driven tweak on the two
used domains.

### RQ-A: Cold rank-equivalence and reachability

The highest-confidence modular contribution in the full portfolio remains the
evaluation question: when can a cold-start benchmark reward a group-constant
score change that learns no within-cold relevance, and when is a target absent
from the retriever's support before ranking? The existing intervention curves
support the theorem and the repository can audit discriminative, two-stage,
and generative recommenders under absolute time. This is an evaluation/theory
paper rather than a new graph algorithm; exact-gap confidence is about 60%.

### RQ-B: Identifiability-bounded shared/private transfer

The best remaining algorithmic bet is to reconstruct only semantic-to-
collaborative directions that clear an out-of-fold estimability threshold, and
route the unidentifiable private component to a content expert instead of
hallucinating a full collaborative embedding. This is not primarily a graph
operator contribution, but it addresses the bottleneck exposed by every failed
graph screen. Exact-gap confidence is about 55%; it deserves one bounded
prospective screen against ridge, reduced-rank regression/PLS, CCA, and modern
strict-cold baselines.

## Literature boundary used for the stopping decision

- Arrigo, Higham, and Noferini, backtrack-downweighted walks:
  https://doi.org/10.1137/20M1384725
- Arrigo and Durastante, walk-based Laplacians interpolating ordinary and
  nonbacktracking diffusion: https://arxiv.org/abs/2601.11338
- Nearby weighted nonbacktracking node-space machinery:
  https://doi.org/10.1137/23M155219X
- Bethe Hessian spectral method:
  https://papers.neurips.cc/paper/5520-spectral-clustering-of-graphs-with-the-bethe-hessian
- Deformed Laplacian for semi-supervised learning:
  https://doi.org/10.1109/TNNLS.2014.2376936
- Classical hypergraph SSL:
  https://papers.neurips.cc/paper_files/paper/2006/hash/dff8e9c2ac33381546d96deea9922999-Abstract.html
- Limits/equivalences of hypergraph learning:
  https://mlanthology.org/icml/2006/agarwal2006icml-higher/
- Efficient learned graphs for SSL:
  https://proceedings.mlr.press/v216/sharma23a.html
- Content-based Graph Reconstruction for cold items:
  https://doi.org/10.1145/3626772.3657801

## Final allocation decision

Stop the fixed-topology graph-operator loop. Preserve NBHE as a rigorous
negative result and theorem, but do not promote it to K1 or tune it. If another
graph loop is authorized, begin with a literature and identifiability audit of
RQ-G1 and use fresh domains. For the main publication program, prioritize
rank-equivalence/reachability; for the next bounded algorithm screen,
prioritize identifiability-bounded shared/private transfer.
