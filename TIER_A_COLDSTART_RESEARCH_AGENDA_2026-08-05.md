# Tier-A Cold-Start Research Agenda

> **Superseded after prospective testing.** All four mechanism screens have
> now returned `NEW_DIRECTION`. The current ranked recommendation is
> `experiments/TIER_A_COLDSTART_RESEARCH_VERDICT_2026-08-05.md`. This document
> is retained as the pre-experiment rationale and must not be cited as the
> final decision.

**Date:** 2026-08-05

**Repository:** `C:\Users\rayxc\Documents\R` at `7105cd29e0872702cc53495a5b5e84ccd282d332`

**Status:** research scouting and exploratory proof of concept; no result below is confirmatory or paper-bound

## Executive decision

There is one direction I would actively pursue, one algorithmic direction I
would give a bounded GPU screen, and one recent-mathematics moonshot that is
novel but much less likely to beat simple regression.

| Rank | Research question | Exact defensible contribution | Gap confidence | Chance of a strong main-track paper if the stated gates pass | Decision |
|---:|---|---|---:|---:|---|
| 1 | Can a cold-start benchmark reward catalog-wide cold promotion without learning any cold relevance, and can catalog onboarding be certified against warm-user tail harm? | Cold-specific target-conditioned offset-degeneracy theorem; diagnostic decomposition; global-time mixed-target protocol; user-level OCE/CVaR-certified integration wrapper | 0.70–0.75 | about 0.55–0.60 at SIGIR/RecSys; lower at general ML | **GO** |
| 2 | Under a content-anchored decomposition, do semantic and collaborative components require different temporal transfer functions? | Representation-conditioned temporal dynamics: semantic-only causal FIR, collaborative innovation bypass, an excess-risk result, and a branch-predictability diagnostic under strict temporal cold start | about 0.70 that the exact method is unoccupied; only 0.20–0.25 for the bare architecture | about 0.45–0.55 **for the mechanism package if the interaction replicates** | **CHEAP SCREEN, THEN GO/NO-GO** |
| 3 | Under content/collaborative contamination, can partially anchored cost-regularized unbalanced OT reject genuinely unmatched semantics and improve strict-cold ranking? | First identity-anchored, out-of-sample CR-UOT adapter for strict item cold start, with a recovery result under partial pairing/contamination | about 0.70–0.75 for literal use; much lower for substantive value | about 0.25 | **MOONSHOT ONLY** |

No responsible literature audit can give high confidence of Tier-A acceptance
before the multi-domain results exist. The high-confidence claim is narrower:
the first question exposes a real and consequential measurement defect, its
exact cold-start form appears unoccupied, and the repository has already
produced the predicted intervention curve. Calling a score scaler, gate,
generic uncertainty model, OT mapper, or EASE side-feature model novel would
not survive review.

## Why this repository is unusually well positioned

The most useful existing nucleus is not the current FIR manuscript. It is the
combination of:

- timestamped Amazon data and cached text representations;
- a fast Cholesky EASE core;
- LC2C/content/DropoutNet-style strict-cold adapters;
- the exploratory CDR per-user calibration code;
- a full-catalog evaluator and a neural SASRec/HSTU harness with cold-item
  synthesis, kriging/BLUP, dual heads, and chunked 207k-item scoring;
- strong reproducibility, causality, parity, and user-bootstrap machinery.

The old random item-fold LC2C experiments ask how well a model ranks a target
known to be cold. The new timestamped experiments can instead ask the actual
deployment question: at a particular time, among the items then available,
what should be shown when the next target may be warm or new? That distinction
is the source of the leading contribution.

The repository audit also found an independent mechanism clue for the second
line of work: causal FIR helps several semantically initialized Amazon models,
but is null on MovieLens-1M and harmful on a new plain-ID Beauty run. The
interesting hypothesis is not that FIR is universally useful. It is that
semantic features contain transferable lag structure while item-specific
collaborative residuals can behave more like innovations and should bypass the
same lag operator.

---

## RQ1 — Target-conditioned offset degeneracy and risk-certified catalog onboarding

### Exact research question

> Can current strict-cold evaluation report large full-catalog gains for an
> intervention that changes no ordering among cold items at all, and can an
> arbitrary cold adapter be integrated into live mixed traffic while placing a
> high-probability bound on warm-user tail loss?

This should be framed as an evaluation/theory paper with a transparent repair
and safety wrapper. It should **not** be framed as the first warm/cold tradeoff,
the first mixed evaluation, the first gate, or a new hierarchical probability
model.

### Proposition: target-conditioned offset degeneracy

At query time \(t\), partition the available catalog into warm and cold pools
\(W_t\) and \(C_t\). For any base scorer \(s\), consider the intervention

\[
s_\delta(u,i,t)=s(u,i,t)+\delta(u,t)\mathbf 1[i\in C_t].
\]

For a cold target \(y\), ignoring a deterministic tie term for readability,

\[
r_y(\delta)
=1+\sum_{j\in C_t\setminus\{y\}}\mathbf 1[s_j\ge s_y]
 +\sum_{j\in W_t}\mathbf 1[s_j\ge s_y+\delta].
\]

Therefore:

1. Every within-cold ordering and every cold-only-candidate rank metric is
   invariant to \(\delta\).
2. With full-catalog candidates but targets conditioned to be cold,
   \(r_y(\delta)\) is non-increasing. Recall, MRR, and NDCG can improve all the
   way to their within-cold value without learning one bit of additional cold
   relevance.
3. Warm-target ranks move in the opposite direction.
4. The deployment optimum depends on the time- and context-dependent target
   mixture \(\pi_t=P(Y_t\in C_t)\). A cold-conditioned benchmark discards this
   quantity and supplies a one-sided objective.

For full-catalog/cold-target evaluation, **offset degeneracy** is more precise
than saying the metric is invariant: the metric changes, but monotonically
rewards a nuisance pool offset. For cold-only candidates, the cross-pool offset
really is non-identifiable.

The algebra is short. Its value must come from demonstrating that it changes
scientific conclusions, not from pretending the proof is technically deep.

### Closest work and the claim that remains

- [Cold Item Integration via Tunable Stochastic Gates](https://arxiv.org/abs/2112.07615)
  already identifies conflicting warm/cold objectives and tunes promotion in a
  unified catalog.
- [FEASE](https://arxiv.org/abs/2504.02288) diagnoses the EASE cold/warm score
  gap, rescales cold scores, and exposes a cold multiplier.
- [Fairness among New Items](https://doi.org/10.1145/3404835.3462948) normalizes
  scores and ranks targets only among new items.
- [Warmer for Less](https://arxiv.org/abs/2512.17277), accepted at WWW 2026,
  regularizes cold/warm score distributions at Pinterest and reports fresh and
  aggregate outcomes.
- [DiffCold](https://arxiv.org/abs/2606.12245) calls the warm/cold conflict the
  seesaw dilemma and reports overall, cold, and warm metrics.
- [On Target Item Sampling](https://castells.github.io/papers/recsys2020.pdf)
  establishes that target/candidate choices can reverse recommender
  comparisons in general.
- The March 2026 work on
  [risk-controlling recommender systems](https://arxiv.org/abs/2603.28476)
  blocks a generic “first risk-controlled recommender” claim.

The remaining claim is the exact cold-group/target-conditioning theorem, an
offset stress-test and metric decomposition, a temporally valid mixed-demand
benchmark, and a *user-level tail-risk certificate* for catalog integration.
The 2026 generative reproducibility study explicitly scores the full catalog
while focusing evaluation on cold targets, making the issue current rather
than historical: [Cold-Starts in Generative Recommendation](https://arxiv.org/abs/2603.29845).
The July 2026 study
[Can Generative Recommendation Reach Cold Items?](https://arxiv.org/abs/2607.21101)
uses an absolute-time protocol and carefully diagnoses seen/unseen reachability,
so “first temporal cold-start audit” is also unavailable. It still evaluates
the cold mechanism rather than proving the pool-offset defect or certifying
mixed warm/cold traffic.

### Repair baseline: Temporal Prior-Calibrated Integration

Let \(q_C(i\mid u,t)\) and \(q_W(i\mid u,t)\) be normalized within-pool
rankers. Use

\[
\ell(i\mid u,t)=
\begin{cases}
\log \pi_C(u,t)+\log q_C(i\mid u,t),& i\in C_t,\\
\log(1-\pi_C(u,t))+\log q_W(i\mid u,t),& i\in W_t.
\end{cases}
\]

This is a nested/hierarchical choice baseline, not the main algorithmic
novelty. The useful additions are:

- global-time catalog snapshots and first-availability constraints;
- cross-fitted, context- and age-dependent \(\pi_C\), shrunk toward a temporal
  category prior;
- prior/label-shift correction when the validation arrival rate differs from
  deployment;
- separate reporting of pool selection and within-pool relevance;
- a finite family of integration policies selected with simultaneous or split
  selection/certification.

For user- or time-block loss \(L_u(\theta)\in[0,1]\), choose a policy that
maximizes new-item utility subject to

\[
\operatorname{OCE}_\phi(L(\theta))\le \epsilon
\]

with a high-probability upper confidence bound. The recent
[OCE-RCPS](https://arxiv.org/abs/2602.13660) framework supplies modern tools for
CVaR and entropic-risk control, but its theorem is for prediction sets. A paper
here must prove the finite-policy recommender version and must not reuse the
same observations naively for unconstrained selection and certification.
Under temporal drift, guarantees need explicit block/weighting assumptions;
“distribution free for future traffic” would be indefensible.

### Completed proof of concept

Artifact: `experiments/cold_pool_prior_poc`.

On timestamped All_Beauty, training at the 60% global time cutoff and evaluating
after the 75% cutoff produced 604 eligible successive events from 185 users:
456 cold targets and 148 warm targets. The only intervention in the prior sweep
was a uniform log pool prior; candidates and all within-pool scores and ranks
were held fixed.

| Cold prior | Cold-target NDCG@10 | Warm-target NDCG@10 |
|---:|---:|---:|
| 0.001 | 0.0000 | 0.0556 |
| 0.050 | 0.0239 | 0.0517 |
| 0.100 | 0.0810 | 0.0436 |
| 0.250 | 0.1947 | 0.0000 |
| 0.500 | 0.2111 | 0.0000 |

Thus cold NDCG moved from 0 to 0.2111 with **no change whatsoever in the
within-cold ranking**, while warm utility collapsed to zero. This is the exact
failure mode predicted by the proposition.

A validation-selected policy constrained to retain at least 90% of inner warm
NDCG chose a cold prior of 0.0445. On the outer window, relative to raw LC2C:

- all-event-weighted NDCG difference: +0.01463; user-weighted difference:
  +0.01503 with user-bootstrap 95% CI [+0.00380, +0.03005];
- cold-event-weighted difference: +0.01943; cold-user-weighted difference:
  +0.01541 with user-bootstrap CI [-0.00031, +0.03495];
- warm-event-weighted difference: -0.00016; warm-user-weighted difference:
  -0.00071 with user-bootstrap CI [-0.00333, +0.00135].

This is directional, not confirmatory. Only 6.5% of users improved overall and
the cold-user CI barely crosses zero. The strong result is the intervention
curve, not a claim that the current selector is already a new SOTA method.

### Minimum Tier-A package

1. **Theory:** offset proposition; decomposition into pool-selection and
   within-pool ranks; dependence of the deployment objective on \(\pi_t\);
   valid user/time-block OCE bound for a finite policy class.
2. **Literature/code audit:** 30–50 recent strict-cold papers, recording target
   conditioning, candidate pool, temporal validity, arrival mixture, and
   availability leakage.
3. **Intervention audit:** add only a constant cold offset to every reproduced
   method; measure metric inflation and method-order reversals.
4. **At least four temporal domains:** three Amazon Reviews 2023 categories
   plus an impression dataset. [EB-NeRD](https://recsys.eb.dk/) is especially
   valuable because it has article publish times, impression timestamps,
   exposed candidates, and clicks. Amazon tests open-catalog retrieval;
   EB-NeRD tests exposed-slate calibration without claiming unobserved
   preferences are known.
5. **Metrics:** mixed-traffic NDCG/Recall; cold and warm target strata;
   within-pool NDCG; pool-label log loss/Brier; item age buckets; coverage;
   mean and OCE/CVaR user harm; runtime.
6. **Baselines:** constant offset; raw and per-user z-score fusion; FEASE;
   CWH; Warmer ScoreReg; Platt/MLPlatt; empirical prior; nested logit; LC2C/CDR;
   strong cold adapters such as CCFCRec/Firzen/DiffCold where code permits.

### Kill criteria

- Constant offsets do not erase or reverse apparently meaningful gains across
  several methods and domains.
- A scalar offset tuned on mixed validation matches the contextual prior model.
- The OCE wrapper gives no advantage over a mean-loss constraint.
- Gains disappear on EB-NeRD exposed slates.
- The effect exists only on the tiny All_Beauty overlap corpus.

---

## RQ2 — Representation-conditioned temporal dynamics

### Exact research question

> Under a content-anchored decomposition \(e_i=c_i+r_i\), do semantic and
> collaborative components require different temporal transfer functions—
> specifically, does causal filtering of \(c_{1:t}\) with an identity path for
> \(r_{1:t}\) improve strict temporal zero-interaction recommendation without
> sacrificing warm-item accuracy?

This is the best bounded algorithmic screen because it directly tests the
repository's semantic-versus-ID FIR reversal and adds negligible work beside
attention. It must be presented as **representation-conditioned temporal
dynamics**, not as another two-stream architecture or another generic FIR.

### Proposed module: subspace-selective causal filtering

Use a frozen, pre-availability content encoder and a shared projection:

\[
c_i=P f_{\text{text}}(i),\qquad e_i=c_i+r_i,
\]

where \(r_i\) is a bounded item-specific collaborative delta and \(r_i=0\) for
a truly unseen item. In the sequence path, apply an identity-initialized short
causal filter only to the anchored semantic component:

\[
\widetilde e_t=F_\theta(c_{1:t})+r_{i_t},\qquad
e_j=c_j+r_j
\]

for target candidate \(j\). Constrain \(r_i\) by norm and, preferably,
decorrelate it from \(c_i\); otherwise the decomposition is non-identifiable
and the semantic-only interpretation is weak. Normalize branch scores or use
RQ1's transparent pool integration so that \(r_j=0\) for cold candidates does
not turn an embedding-norm disadvantage into the apparent mechanism.

### The theorem-shaped claim and diagnostic

Suppose target-relevant semantic features have nonzero lag covariance, while
the collaborative residual is conditionally temporally white beyond the
current position. In the corresponding linear prediction problem, the optimal
lag coefficients on the residual are zero. Applying shared nonzero lag taps to
the early-fused representation then adds an excess-risk term governed by the
residual covariance and tap norms. A formal result should state the precise
conditioning assumptions and show when selective filtering strictly dominates
early-fused filtering.

The empirical contribution is stronger if a pre-declared branch statistic—lag
covariance, partial autocorrelation, or spectral predictability—forecasts the
gain from filtering across datasets. The decisive interaction is

\[
\Delta_{\text{semantic FIR}}>0,\qquad
\Delta_{\text{collaborative FIR}}\le 0,\qquad
\text{selective FIR}>\text{early-fused FIR}.
\]

A win by one architecture without that interaction is not enough for a strong
paper.

### Closest work and remaining gap

- [Let It Go? Not Quite](https://arxiv.org/abs/2507.19473), RecSys 2025,
  already uses frozen content plus a bounded trainable item delta under global
  temporal splits and reports cold/warm/full outcomes. It blocks any claim to
  invent the content-base/collaborative-residual decomposition.
- [PAD](https://arxiv.org/abs/2412.04107), SIGIR 2025, already retains textual,
  collaborative, and aligned sequential experts with frequency-aware fusion.
  It blocks a generic separate-path claim.
- [FreLLM4Rec](https://arxiv.org/abs/2508.10312), KDD 2026, is the strongest
  conceptual challenge: it argues for signal-specific spectral treatment and
  filters combined semantic/collaborative information, with emphasis on
  collaborative low frequencies. The proposed work must explain and measure
  why pretrained collaborative embeddings, learned ID residuals, and different
  temporal filters are not interchangeable.
- [MCD4SR](https://doi.org/10.1016/j.knosys.2026.116174) uses parallel ID,
  text, and visual paths with causal sequence encoders; [DiscRec](https://arxiv.org/abs/2506.15576)
  uses different semantic and collaborative branches; and
  [MuSTRec](https://arxiv.org/abs/2602.07207) applies frequency-aware processing
  after combining multimodal and collaborative graph embeddings. These block
  broad multimodal-disentanglement claims.
- [GateSID](https://arxiv.org/abs/2603.22916) adaptively balances semantic and
  collaborative signals by item maturity, while Tubi's
  [Shallow-RHS](https://arxiv.org/abs/2606.06225) deliberately gives new target
  items a content-only tower in a temporal graph retriever. These block broad
  semantic/collaborative asymmetry and cold-routing claims, but neither tests a
  semantic lag operator against a collaborative innovation bypass.
- [Temporal DRO](https://arxiv.org/abs/2312.09901) already addresses temporal
  feature shift in cold-start transfer. The claim here is about different
  within-sequence dynamics of anchored subspaces, not first use of time in
  cold-start recommendation.

No audited paper applies a causal FIR only to a content-anchored semantic path
while requiring the collaborative residual to bypass it. Confidence that this
exact method is unoccupied is about 0.70. The bare module is only 0.20–0.25
likely to be Tier-A novel; the mechanism, theorem, diagnostic, and strict-cold
package is roughly a 0.45–0.55 paper opportunity if the interaction replicates.

### Runtime-optimized screen

1. Reuse `_bestrec_run/run_sasrec_sbert.py`, the existing FIR implementation,
   cached content embeddings, and chunked full-catalog scorer.
2. On All_Beauty and one larger metadata-rich category, run one fixed seed for
   split-without-FIR, semantic-only FIR, collaborative-only FIR, early-fused
   FIR, and an equal-parameter identity/placebo. Use identical negative samples
   and checkpoints where possible.
3. Measure strict global-time cold, warm, and mixed full-catalog ranking;
   within-cold ordering; histories containing newly introduced items; branch
   lag statistics; and random-projection/shuffled-content controls.
4. Advance only if the directional interaction above appears on both domains,
   the selective model beats the early-fused model, and warm utility remains
   within a predeclared non-inferiority floor.

For filter width \(K=3\)–5, the added work is \(O(KLd_s)\), normally negligible
beside self-attention. A one-seed screen should fit comfortably on the local
16 GB GPU. Only after it passes should the study expand to 3–5 seeds, four
temporal domains, and Let-It-Go/PAD/MuSTRec plus FMLP/BSARec controls.

### Kill criteria

- Collaborative-only and semantic-only filtering behave the same after equal
  parameterization and calibration.
- Early-fused FIR matches or beats the selective model.
- Branch lag diagnostics do not predict the cross-domain gain.
- The apparent cold gain is a uniform pool offset, vanishes within the cold
  pool, or is reproduced by shuffled content.
- The interaction exists only in random item folds or costs material warm
  utility under global time.

---

## RQ3 — Partially anchored CR-UOT under semantic contamination

### Exact research question

> When some item content is genuinely non-predictive of collaborative behavior,
> can an identity-anchored cost-regularized unbalanced transport map learn the
> cross-space geometry while rejecting unmatched mass, and does that rejection
> help rather than suppress niche cold items?

[Cost-Regularized Unbalanced Optimal Transport](https://arxiv.org/abs/2511.19075)
is a 2025/2026 mathematical development that jointly learns a cross-space cost
while allowing mass creation and deletion. Its demonstrated application is
heterogeneous single-cell alignment with missing correspondences, not
recommendation.

### The fatal issue a valid paper must solve

Warm content and collaborative embeddings are already paired by item identity.
Marginal OT discards those correspondences and is permutation-non-identifiable:
two point clouds can match perfectly while every item is sent to the wrong
behavior. Restoring all anchors risks reducing the method to an expensive
robust regression wrapper.

Therefore a credible method must be *partially anchored*, and the paper needs
both a negative result for unanchored recovery and a positive recovery or
generalization statement under anchored contamination. A possible objective is

\[
\min_{M,P}\langle C_M,P\rangle
+\varepsilon\operatorname{KL}(P\|a\otimes b)
+\rho\operatorname{KL}(P\mathbf1\|a)
+\rho\operatorname{KL}(P^\top\mathbf1\|b)
+\lambda\mathcal L_{\text{anchors}}(M,P),
\]

followed by an out-of-sample map for a new content point. Use block/low-rank
Sinkhorn; a dense \(n^2\) coupling violates the runtime objective.

### Collision set

- [Wasserstein Collaborative Filtering](https://arxiv.org/abs/1909.04266)
  already applies Wasserstein structure to item cold start.
- [Stein-path distribution alignment](https://proceedings.neurips.cc/paper/2021/hash/a0443c8c8c3372d662e9173c18faaa2c-Abstract.html)
  is a NeurIPS cold-start method.
- UEDMCF uses unbalanced distribution OT for cold-start cross-domain
  recommendation: [OpenReview](https://openreview.net/forum?id=YeEPnd4lIT).
- A UAI 2025 method uses OT and barycentric preference alignment:
  [OpenReview](https://openreview.net/forum?id=tRljM2Jc14).
- [CARec](https://arxiv.org/abs/2310.09400) and
  [DiffCold](https://arxiv.org/abs/2606.12245) directly address the
  semantic/collaborative manifold gap.

Literal first use of CR-UOT is plausible. A substantive contribution is not
yet established.

### Required cheap screen and kill criteria

Use synthetic paired manifolds with controlled unmatched/outlier rates before
touching a large recommender. Compare ridge, robust ridge, Procrustes, balanced
OT, fixed-cost UOT, and anchored CR-UOT. Then run strict temporal cold tests.

Kill immediately if:

- ridge/Procrustes matches it on clean paired data;
- benefit exists only after unrealistic synthetic corruption;
- discarded mass correlates with niche/tail relevance;
- the out-of-sample map collapses toward the warm convex hull;
- block Sinkhorn is not competitive in wall-clock cost.

This is worth a small mathematical experiment, not a main campaign.

---

## Ideas explicitly demoted or killed

### Nonlinear vector p-harmonic extension — demoted by a cheap POC

The attractive idea was to put EASE behavior columns on warm boundary nodes of
a text kNN graph and extend them to cold items with a vector \(p\)-Laplacian.
For \(p>2\), the few-label graph theory can avoid ordinary harmonic collapse:
[Flores, Calder, and Lerman](https://arxiv.org/abs/1901.05031).

The isolated POC used five item folds and within-cold candidates, so no
warm/cold pool shift could improve the result. It completed in about 13 seconds
wall time for Beauty and Fashion.

| Dataset | content | LC2C ridge | harmonic \(p=2\) | \(p=4\) | \(p=8\) |
|---|---:|---:|---:|---:|---:|
| Beauty | 0.13439 | **0.15353** | 0.14922 | 0.14656 | 0.14100 |
| Fashion | 0.12269 | **0.13828** | 0.13752 | 0.13549 | 0.13237 |

Ordinary harmonic extension is competitive, but \(p=4\) is worse than \(p=2\)
on both datasets. The \(p=8\) IRLS updates also failed to settle within the
fixed 12-step budget on several folds and produced still worse ranks. This does
not prove that no solver or graph can make \(p>2\) work; it does falsify the
claimed cheap, runtime-friendly advantage in the repository's actual
80%-warm-boundary regime. Do not pursue it unless a materially different
mechanism appears.

### Schur/PSD-safe EASE expansion — killed as a standalone algorithm

For warm Gram \(A\), predicted cross block \(K\), and cold block \(D\), PSD
requires \(D-K^\top A^{-1}K\succeq0\). But the augmented EASE warm-to-cold
coefficient is simply \(A^{-1}K\) (for a diagonal Schur residual), and any
desired coefficient can be made PSD-realizable by choosing \(K=Ab\). The PSD
condition is therefore largely a reparameterization of direct ridge/LC2C, not
a calibration or relevance guarantee. FEASE/collective EASE already occupy the
closed-form side-information territory. Keep the algebra as a stability note,
not a Tier-A claim. A more defensible residual variant could predict each cold
item's held-out warm explained-energy ratio
\(\rho_i=1-(P_{ii}G_{ii})^{-1}\) and use it to rescale a content-predicted
cross-Gram column. That is a cheap calibration ablation worth retaining, but it
must beat energy-rescaled direct LC2C and FEASE; otherwise it is still only
score-scale estimation dressed as PSD completion.

### Literal strict-cold BFT precision propagation — structurally ineffective

[Precision Tracked Transformer](https://arxiv.org/abs/2605.18832) tracks the
precision of history tokens. In SASRec-style full-catalog scoring, a truly
unseen target candidate is not a history token, so its predicted precision
never enters the Transformer. The literal “propagate cold target precision
through BFT” proposal is therefore a no-op. Making every target condition the
sequence encoder would also destroy efficient catalog scoring.

One can instead combine a BFT Gaussian user state with a heteroscedastic
content posterior in an analytic two-tower score distribution. That is a
different sequential model, and it collides closely with BFT's own
content-conditional precision/rare-item claim plus cold-start uncertainty work
such as [CREU](https://arxiv.org/abs/2502.16256). Keep it below RQ3 unless a
simple score-level uncertainty screen clearly beats scalar calibration.

### Standalone score calibration, z-normalization, or a pool gate — occupied

The repository's CDR results are useful diagnostics, but z-normalization and
cold promotion collide with SIGIR 2021 new-item fairness, FEASE, CWH, Warmer for
Less, and broad calibration/rank-fusion work. They can be baselines or the
transparent repair in RQ1, not the headline algorithm.

### Simple temporal recency in LC2C — locally falsified

The existing Temporal-LC2C experiment failed every directional gate; selected
recency weighting slightly worsened the relevant cold and full-catalog metrics.
Do not scale it without a different mechanism.

### Christoffel exposure selection — too crowded for a lead

Recent Christoffel adaptive sampling is elegant, but cold-item optimal design,
active learning, and the 2026 information-aware content-promotion work already
occupy the core idea. It may be an anchor-selection ablation, not a standalone
paper. See [Christoffel adaptive sampling](https://arxiv.org/abs/2603.18251) and
[information-aware content promotion](https://arxiv.org/abs/2601.20422).

## Recommended sequence and compute budget

### Week 1: make or break RQ1

1. Generalize the offset audit from All_Beauty to three timestamped Amazon 2023
   domains using a cheap content/CF scorer.
2. Add the same offset intervention to existing CDR, LC2C, and neural cold
   output records.
3. Measure leaderboard reversals and pool-selection/within-pool decomposition.
4. Download and preprocess EB-NeRD only if the Amazon result generalizes.

This stage is CPU-friendly and should finish in hours to a few days, not weeks.

### Week 2: bounded subspace-selective FIR screen

1. Add the anchored semantic base plus bounded collaborative residual to the
   existing SASRec/SBERT harness.
2. Run semantic-only, collaborative-only, early-fused, no-FIR, and placebo
   arms on two domains with one fixed seed and shared data/checkpoints.
3. Enforce the predeclared interaction, within-cold, and warm-floor gates; do
   not hyperparameter-sweep a failed mechanism into existence.

Stop if the mechanism gates fail. If they pass, isolate a clean worktree before
multi-seed runs; the current worktree is materially dirty and contains protected
paper artifacts.

### Only after a pass

- Run four temporal domains, 3–5 seeds, user/time-block inference, and modern
  baselines.
- Freeze hypotheses and endpoints before confirmatory runs.
- Treat CR-UOT as an independent 1–2 day synthetic screen, never as a reason to
  delay the leading paper.

## New exploratory artifacts

- `experiments/cold_pool_prior_poc/run_pool_prior_poc.py`
- `experiments/cold_pool_prior_poc/results.json`
- `experiments/cold_pool_prior_poc/outer_records.jsonl`
- `experiments/p_harmonic_cold_poc/run_p_harmonic_poc.py`
- `experiments/p_harmonic_cold_poc/results.json`

Both scripts are isolated from frozen campaigns, label their outputs
exploratory, record input hashes, and compile under the repository's `uv`
environment.

## Final recommendation

Lead with RQ1. It is the only direction currently supported by a precise gap,
a theorem-shaped claim, a consequential local intervention, cheap runtime, and
a path to a strong benchmark/method paper. Run RQ2 as the algorithmic companion
because it converts the repository's semantic-versus-ID reversal into a direct,
cheap mechanism test. Keep RQ3 behind a strict synthetic gate.

Do not spend the main budget trying to rescue CDR as a novel scaler, p-harmonic
extension, Schur-safe EASE, or scalar recency. The audit evidence is already
strong enough to say no.
