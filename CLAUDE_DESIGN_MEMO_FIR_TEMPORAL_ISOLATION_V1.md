# Claude reject-first design memo — `DRAFT_FIR_TEMPORAL_ISOLATION_V1`

Role: scientific red-team (per `CODEX_CLAUDE_COLLABORATION_GUIDE.md` §3, §6.A.1).
Reviewed: `PREREG_FIR_TEMPORAL_ISOLATION_V1_DRAFT.md` (100 lines, DRAFT).
Date: 2026-07-31. Author: Claude. Advisory only — not external peer review.

```text
WORKSTREAM:        A2 core temporal isolation — pre-freeze design review
OBJECTIVE:         reject/approve memo on the matched-input temporal-isolation draft
EVIDENCE QUESTION: does the proposed repeated-current control identify temporal access,
                   and is it worth the GPU budget relative to gates A3/A4?
FILES I MAY EDIT:  this memo only
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, the draft prereg, frozen preregs,
                   adjudicators, manuscript, TeX, artifact graph, any endpoint
EXPECTED OUTPUT:   verdict + blocking objections + superior design + priority judgment
STOP CONDITION:    memo committed; Codex unblocked to revise (not to freeze as drafted)
```

## Verdict: **REVISE — do not freeze as drafted**

Not a rejection of the intent. The draft's motivation is correct and its honesty is
good (it self-discloses the functional collapse rather than hiding it). But as written
the primary contrast is **near-deterministic in outcome, strictly weaker than a control
we have already defeated, and mis-specified in one factual claim**. Freezing it would
spend GPU-days to re-derive a known number under a new name.

Three blocking objections, then a design that fixes all three.

---

## B1 (blocking). The control collapses to one effective DOF — and it duplicates a
## parameter the model already has

The draft's own algebra:

```text
repeated_current[t,c] = sum_k w[c,k] * x[t,c] = ( sum_k w[c,k] ) * x[t,c] = W_c * x[t,c]
```

`W_c` is **a single scalar per channel**. So the arm's function class is
`{x ↦ a·x}` per channel — **1 effective degree of freedom**, not `K`.

The draft states this preserves "parameter count and optimization surface dimensions."
Parameter count: true. **Optimization surface dimensions: false.** The ambient
dimension is `K`; the functional dimension is `1`. That sentence must be corrected
before any freeze — it is the load-bearing justification for calling the arms
"matched," and it is not accurate.

Worse, the residual makes the arm `x + W_c·x = (1 + W_c)·x` — a **per-channel diagonal
rescale of the sequence representation**. The network already contains a learnable
per-channel scale immediately downstream (the LayerNorm affine `γ`; `norm_in`,
`run_sasrec_sbert.py:265`). So `repeated_current` is a *redundant reparameterization of
capacity the model already possesses*. Its expected effect is ≈0 **by construction,
not by experiment** — and an outcome that is knowable from the architecture before
running is not evidence.

## B2 (blocking). It is strictly weaker than the control we already beat

`PREREG_FIR_POINTWISE_V1` is complete, adjudicated `POINTWISE-FIR-DISCRIMINATED`:

| contrast | mean | 95% CI | p |
|---|---|---|---|
| `pointwise − identity` | −0.000069 | [−0.000200, +0.000061] | 0.25 |
| `learned − identity` | +0.001872 | [+0.001737, +0.002007] | 6.2e-09 |
| `learned − pointwise` | +0.001941 | [+0.001788, +0.002095] | 1.2e-08 |

The `pointwise` arm is a **DCT-16 → GELU → learned 64×16** map of the current position:
1,024 parameters, **nonlinear**, channel-mixing. It is a *strictly richer* function
class than a per-channel scalar — and it landed indistinguishable from identity.

So we have already shown: a rich, nonlinear, parameter-matched, current-only residual
does not move the metric, while the FIR does. The proposed study asks the same question
against a **weaker** opponent. A reviewer's response writes itself: *"You already beat a
nonlinear rank-16 current-only projection. Beating a per-channel scalar adds nothing."*

Predicted outcome, stated now so it is on the record before any run:
`repeated_current − identity` ≈ 0 (tighter to 0 than pointwise's −0.000069), and
`lagged − repeated_current` ≈ +0.0019 ≈ the known `learned − identity`. If the study
runs as drafted and returns those numbers, it will have added no discriminating evidence.

## B3 (blocking). Undisclosed optimization asymmetry between the arms

Because every `w[c,k]` in `repeated_current` receives the **identical** gradient
(`∂L/∂w[c,k] = Σ_t (∂L/∂out[t,c])·x[t,c]`, independent of `k`), the K weights remain
exactly equal from a zero init under Adam. Consequences the draft does not address:

- the single functional DOF is driven by `K` redundant Adam-normalized updates, so its
  **effective step size is ~K× that of any single tap** in `lagged_fir`;
- under **coupled** L2 (this codebase's setting), K weights of size `a/K` incur total
  penalty `a²/K` — the effective regularization on the functional parameter is
  **weaker by ~1/K** than on a single scalar.

The arms therefore differ in effective learning rate and effective weight decay on the
parameter that actually matters. That is a second confound layered on B1. A null result
would be uninterpretable; a positive result would be attributable to optimization
geometry rather than temporal access.

---

## What each outcome would license, as drafted

- **lagged > repeated_current** (expected): licenses only *"the FIR beat a per-channel
  rescale"* — weaker than what the pointwise study already licenses. Not temporal
  isolation, not per-channel necessity, not generalization.
- **interval overlaps zero**: would contradict the completed pointwise result and most
  likely indicate an implementation or budget fault, not equivalence.
- **repeated_current > lagged**: would be genuinely informative (and would falsify the
  mechanism story), but B3 means it could equally be an optimization artifact.

None of these outcomes moves gate A2 to a defensible "temporal isolation" claim.

---

## Proposed replacement design (fixes B1–B3, higher information per GPU-hour)

Keep the draft's correct instinct — hold the parameterization fixed and vary only the
**inputs supplied to the taps**. Replace the degenerate arm with controls that retain
`K` genuine degrees of freedom.

**Arms (all zero-init, exact identity at init, gradient-active, shared per-seed backbone
init hash, one frozen config, no arm-specific normalization):**

1. `identity` — frozen zero residual (replication diagnostic; retained).
2. `lagged_fir` — K true causal lags (the canonical method).
3. **`donor_lags`** — taps read `x_donor[t−k, c]`, where the donor is a different
   sequence in the batch, paired by a seeded, fixed, per-example rule. **K real DOF,
   real input variance, correct marginal statistics, no access to *this user's* past.**
   This is the control that actually isolates "the user's own history" from "generic
   temporal statistics of the representation."
4. **`order_scramble`** — taps read this user's own last-K states in a **per-example,
   per-epoch re-randomized** order. Isolates *temporal order* from *window membership*.
   ⚠️ Technical requirement: the permutation must be re-drawn per example per epoch. A
   **fixed** permutation is absorbed into the learned weights
   (`Σ_k w[c,k]·x[t−σ(k),c] = Σ_j w[c,σ⁻¹(j)]·x[t−j,c]`) and would be an identical
   function class — i.e. a fixed-permutation control is *no control at all*. This is a
   trap worth writing into the prereg explicitly.

**Free by-product:** run the primary at a small **K-dose-response** (`K ∈ {1,2,4,8,16}`).
`K=1` **is** the draft's `repeated_current` arm functionally (a per-channel scalar × the
current state) — so the draft's entire question is answered as the first rung of a curve,
at no extra cost, without the B3 redundancy artifact. A monotone-ish dose-response over K
is far more persuasive mechanism evidence to a reviewer than one placebo contrast.

**Primary contrast:** `lagged_fir − donor_lags` (temporal-access identification).
**Secondary:** `lagged_fir − order_scramble` (order necessity); `K` dose-response.
Multiplicity: one predeclared Holm family. Inferential unit: matched optimizer-seed
blocks. All negative/null outcomes publishable and pre-worded.

**Claim ceiling even if everything lands positive:** *"On the tested split(s) and backbone,
taps reading this user's own ordered causal history outperform matched-capacity taps
reading donor history or scrambled order."* Not universal temporal necessity, not causal
claims about users, not generalization, not SOTA.

---

## Priority judgment (venue-methodology role)

I am obliged to say this even though it argues against my own workstream: **A2 is not
the gate most limiting Tier-A acceptance.** Per the gate table, A3 (baseline tuning
fairness) and A4 (non-Amazon external validity) are OPEN, and the handoff records a
**negative MovieLens replication** as a live residual risk.

A reviewer weighing a Tier-A decision will ask, in order: *does it generalize?* (A4),
*are the baselines fairly tuned?* (A3), *is the mechanism identified?* (A2). Running a
third mechanism study on outcome-known Musical_Instruments while a negative external
replication sits unresolved optimizes the third question at the expense of the first.

Recommended ordering:
1. **A4** — resolve the MovieLens negative honestly (it may narrow the claim; that is an
   acceptable and publishable outcome) and settle the lawful non-Amazon domain.
2. **A3** — symmetric, documented tuning budgets and a strong current baseline.
3. **A2** — the revised temporal design above, ideally on a category whose FIR outcome
   is genuinely unseen rather than on MI again.

## Limits of this memo

I did not inspect any sealed endpoint, did not run anything, and edited no file but this
one. B1/B3 are analytic (algebra and optimizer semantics) and should be confirmed by
Codex with a structural unit test — specifically: assert all `K` `repeated_current`
weights remain exactly equal through training, and assert a fixed-permutation control is
numerically indistinguishable from `lagged_fir` in function class. B2 is empirical and
rests on the committed `fir_pointwise_v1_adjudication.json`. My audit is advisory
evidence, not external peer review, and cannot make any result "independent."

**Codex is unblocked to revise the draft against B1–B3. It is not authorized to freeze
or launch the protocol as currently drafted.**
