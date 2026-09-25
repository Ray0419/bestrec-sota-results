# PAPER SKELETON: ρ(k) / π*(k,K) position paper

**Assembled 2026-08-19 from DERIVATION_COVERAGE_BREAKEVEN.md, DESIGN_RHO_K_MATCHED_COVERAGE.md,
PREREG_RHO_K_V1.md, SECTION_RHO_K_RESULTS.md, SECTION_RHO_K_RELATED_WORK.md. Target: short/position
track of a rigor-friendly venue (TORS position; RecSys short). Numbers are copied from
SECTION_RHO_K_RESULTS.md (including the Amendment A1 addendum) and are authoritative; claims follow
PREREG_RHO_K_V1.md.**

**v3 (2026-08-19).** The pre-registered A1 validation (PREREG_RHO_K_V1.md §5a) ran after v2 was
assembled. E2's frozen prediction P1 FAILED on both datasets; per the frozen consequence, the
headline is demoted to the measurement claims and the admission rule is demoted to a
necessary-but-insufficient screen. This skeleton executes that consequence throughout.

---

## Title (DECIDED 2026-08-19)

**Coverage Was Never the Binding Constraint: Break-Even Arithmetic and a Degree-Indexed
Screen for Cold-Start Retrieval**

*(E2 confirms the claim for cold items — their end-to-end success stays ≈ 0 at every mixing level,
so coverage alone never rescues them; conversion binds. Former candidates "When Is a Cold Item
Worth a Pool Slot?" and "The Ledger Gets the Sign Wrong" are retired; the latter's competition-
displacement phrase survives as §4/§7 framing.)*

**Target venue (DECIDED): ACM RecSys, short-paper track.** Next submission window is RecSys 2027
(historically ~April; the RecSys 2026 cycle closed April 2026). Format target: ACM single-column,
short-paper page budget — the current ~5,000-word skeleton must shed roughly a third at layout
time; §2 and §5 are the designated compression targets. The paper claims the break-even
arithmetic, the screen, and the pre-registered refutation; it does not claim the
coverage × conversion decomposition, which is standard two-stage analysis — see §5.

---

## Abstract (~230 words)

arXiv:2606.29947 measures a coverage bottleneck in LLM-based cold-start recommendation — a single
retriever places the gold item in a 200-item pool only 4.6–22.9% of the time — and reports eight
coverage-side mitigations that all fail or are modest. We measure what a pool slot is worth to a
cold item. Under *forced coverage* — the gold item injected into every pool, so retriever
selection bias (which we measure at roughly 2×) cannot enter, and the residual bias is one-sided
in our disfavour — the pre-registered conversion ratio ρ(k ≤ 10) has its upper confidence bound
below 0.5 in every training-degree bucket on both datasets (re-confirmed at Steam n = 5), with
ρ(k=0) ≈ 0.0002. The break-even arithmetic follows as arithmetic: substituting ρ(k) into
π\* = c/(g·ρ + c) with the cited coverage trades gives π\*(k ≤ 10, 200) = 77–100%; our
pre-registered 90% bar on π\* partially failed under the Yelp trade and is reported as failed. We
then pre-registered a sign-agreement validation of the resulting admission rule on quota-mixed
pools, and it FAILED on both datasets: measured end-to-end deltas are positive at moderate mixing
while the segment-additive prediction is negative; the gain never comes through the cold items —
their end-to-end success stays ≈ 0 at every mixing level — but from competitor-set displacement
among warm targets. The revised position: conversion, not coverage, is still the binding
constraint for cold items, and no mixing level rescues them; but coverage × conversion ledgers —
naive or corrected — mispredict the sign of mix-level interventions because conversion is
pool-composition-dependent. π\*(k,K) is a necessary-but-insufficient screen, never a deploy
signal; conversion must be measured in situ under the deployed pool composition.

---

## 1 Introduction (~500 words)

Cold-start evaluation has recently acquired a measured bottleneck. arXiv:2606.29947 shows, across
five domains, that a single retriever places the gold item into a 200-item candidate pool only
4.6–22.9% of the time, and that 32–91% of cold-start targets are never covered at all. The same
paper quantifies the cost of fixing this by coverage-aware training: 5× upweighting of item-new
positives buys +10pp of new-item coverage on Yelp at −4.5pp warm, and +2.2pp on Video Games at
−4.7pp warm. What the paper does not supply — and states it does not supply — is a decision
formalism: at what cold-target prevalence does that trade pay? This paper supplies the arithmetic,
and the arithmetic returns an answer the coverage framing did not anticipate.

The naive port is one line. NDCG-style break-even analysis says: an intervention with cold gain g
and warm cost c pays iff prevalence π exceeds π\* = c/(g + c). Coverage is also an average of a
per-event indicator over the same cold/warm partition, so the identity transfers exactly, and the
published trades give naive break-evens of 31.0% (Yelp) and 68.1% (Video Games). This is wrong,
and the error is not in the algebra. NDCG is (approximately) the objective; coverage is not — it
is an upper bound on what the downstream ranker can reach. Being in the pool is necessary, not
sufficient. Writing end-to-end success as coverage times the conditional conversion rate R =
P(top-k | in pool) — standard two-stage analysis, claimed by no one here — and setting the change
in success to zero yields the corrected break-even

> π\* = c / (g·ρ + c),   ρ = R_cold / R_warm.

The naive form is the special case ρ = 1. Everything hinges on ρ, and our program's most
replicated finding is that strictly cold items are unrankable: cold NDCG@10 is exactly 0.00000
across two loss families and five training arms, independently replicated at 0.00000 in semantic-ID
generative retrieval (arXiv:2607.21101). If ρ ≈ 0, then π\* → 1 and no prevalence justifies the
trade. But "strictly cold" is k = 0, not the item-new segments of published benchmarks, so the
correct object is the degree-indexed curve ρ(k) — and measuring it naively is biased in our own
favour: a retriever covers the easy cold items first, so conversion conditional on *natural*
coverage is computed on a favourable subset. We measure that inflation directly at roughly 2× in
mid buckets. The instrument therefore forces coverage — the gold item is injected into every pool —
which removes retriever selection entirely. The residual bias is one-sided and runs *against* us:
forced coverage averages over items no real retriever would reach, so it overestimates the marginal
item's conversion, overestimates ρ, and underestimates π\*. If even this optimistic ρ yields π\*
near 1, the conclusion holds a fortiori.

The results (§4) were pre-registered with frozen falsification rules, and three frozen predictions
failed: C2's 90% bar on π\* (partially, reported as failed); the end-to-end validation of the
admission rule (E2, on both datasets — measured deltas positive at moderate mixing, segment-additive
prediction negative, the gain arriving through warm competitor-set displacement, never through the
cold items); and E4's drift prediction, in the instrument's favour (π\*(k) stable to ≤ 1.7pp). We
report all three unsoftened and execute the frozen consequence: the headline demotes to the
measurement claims and the admission rule to a necessary-but-insufficient screen. The position (§7)
is correspondingly two-sided: conversion, not coverage, binds for cold items — but segment-additive
coverage ledgers mispredict the sign of mix-level interventions, so conversion must be measured in
situ under the deployed pool composition.

---

## 2 The break-even rule (~400 words)

**The original rule.** An intervention produces cold gain g > 0 and warm cost |c| > 0 in NDCG@10;
π is the prevalence of cold-target events. Because NDCG is an average of a per-event quantity and
the event set partitions into cold and warm,

```
E  =  π·g − (1−π)·|c|          (exact, an arithmetic identity)
p* =  |c| / (g + |c|)          (E = 0)
```

Deploy iff π > p\*. In the coverage units used in this paper, the pre-registered E4 check found
π\*(k) temporally stable to **≤ 1.7pp** between adjacent windows (§4): temporal drift is not what
limits the rule here. What limits it is structural, and pre-registered: the E2 validation (§4)
shows the segment-additive form mispredicts the *sign* of a real mix intervention, so π\* functions
as a screen, not a deploy threshold.

**The naive port to coverage.** Coverage is P(gold ∈ pool), also a per-event average over the same
partition, so the identity carries over: π\*_cov = c_cov/(g_cov + c_cov). Plugging in
arXiv:2606.29947's measured trade gives 31.0% (Yelp: g = +10pp, c = −4.5pp) and 68.1% (Video
Games: g = +2.2pp, c = −4.7pp). The port is wrong because coverage is not the objective: it is an
upper bound. Maximising aggregate coverage is equivalent to maximising end-to-end quality only if a
covered cold item converts at the warm rate.

**The corrected form.** Let R_s = P(ranked into top-k | gold in pool) be segment s's conditional
conversion rate; end-to-end success is S_s = Cov_s · R_s. Setting ΔS = 0 (holding R fixed — the
bias of that assumption is bounded in §3) and writing ρ = R_cold/R_warm:

```
π*  =  c_cov / (g_cov·ρ + c_cov)
```

**Why it matters: the ρ-sensitivity of π\*.** The published trades under varying ρ:

| ρ | Yelp π\* | Video Games π\* |
|---|---|---|
| 1 (naive) | 31.0% | 68.1% |
| 0.1 | 81.8% | 95.5% |
| 0.01 | 97.8% | 99.5% |
| → 0 | **→ 100%** | **→ 100%** |

No cold prevalence, however high, justifies buying cold coverage while ρ ≈ 0 — and even at the
naive ρ = 1, Video Games already needs 68% cold prevalence. This is also a mechanism for
arXiv:2606.29947's own negative results: all eight of their mitigations attack Cov, none attacks R,
and their own positive-controlled regime (coverage forced to ceiling) still finds calibrated LLM
rerankers failing to beat CF/content baselines — a direct read on R, and it is low. Two empirical
questions remain: ρ(k), degree by degree — what the instrument measures — and whether the
segment-additive form survives a real intervention. It does not: the corrected rule still holds
each segment's R fixed, and E2 (§4) shows R is pool-composition-dependent enough that naive and
corrected ledgers alike mispredict the sign of a quota-mix intervention. §2's arithmetic is
therefore read in v3 as a screen — the condition under which an item's *own* conversions could pay
for a slot — never as a predictor of a mix intervention's end-to-end effect.

---

## 3 The instrument (~350 words)

**Target.** ρ(k) = R(k)/R_warm with R = P(gold ∈ top-10 of the pool | gold ∈ pool), sliced by the
target item's pre-cutoff training degree k using the program's standard buckets
(0), (1–2), (3–5), (6–10), (11–20), (21–50), (51–200), (>200).

**Why natural coverage is disqualifying, not merely untidy.** A retriever covers the easy cold
items first, so R conditional on natural coverage is computed on a favourable subset and rises
artificially as coverage expands — a bias *toward* our conclusion. Fix: **force coverage to 1**
by injecting the gold item into every pool. This is the positive-controlled regime of
arXiv:2604.16318 used as a measurement instrument rather than a benchmark. The residual bias is
one-sided and in our disfavour: forced coverage averages R over items a real retriever would never
reach, which are plausibly harder than the marginal covered item, so it overestimates ρ and
underestimates π\*; if even this optimistic ρ yields π\* near 1, the conclusion holds a fortiori.

**The single-stage vacuity lesson.** The first design built the pool from the ranker's own
top-(K−1) plus the injected gold. That is degenerate: pool-hit@10 reduces to full-catalogue
hit@10 and R carries no new information. Coverage and conversion are only separable when retriever
and ranker are different models; in a single-stage full-catalogue scorer they are the same event.
This is why the decomposition is a statement about two-stage pipelines — and why arXiv:2606.29947,
whose generators and rerankers are distinct, could see the split at all.

**Design.** Retriever Q ≠ ranker M. Pool = top_{K−1}(Q) ∪ {gold}; M scores the pool; endpoint is
gold's hit@10 within the pool. Two pre-registered retrievers, both reported: Q_text (frozen SBERT
title-embedding kNN; the cold-capable family) and Q_pop (global popularity; structurally cannot
reach cold items). K ∈ {100, 200, 500, 1000}, K = 200 primary (2606.29947's setting); π\* is
reported as π\*(k, K), never a scalar. R_warm = event-weighted hit@10 pooled over k ≥ 51 within
the same retriever's pools; ρ is never transported across retrievers. Checkpoints: existing fCE
arm at the primary LR (n = 5 MI, n = 3 Steam), eval-only, no training. **Two structural gates**
must pass in every run or the run is dropped and reported: G1, pool-hit ≥ full-catalogue hit; G2,
pool-hit monotone in K. The falsification rule was frozen before any evaluation ran
(PREREG_RHO_K_V1.md): the thesis is refuted if ρ(k) > 0.5 in any bucket at k ≤ 10 on either
dataset — in which case coverage-side allocation can pay and the position paper is not written.

**Amendment A1 (frozen 2026-08-19, before any E-run; PREREG_RHO_K_V1.md §5a).** Because the
confirmatory π\* table transplants 2606.29947's trades onto our ρ — the move weakness 5.4 forbids —
A1 added an own-dataset end-to-end validation: E1 (quota-mix coverage trades), E2 (primary; frozen
P1: sign(ΔS_meas) = sign(ΔS_pred) at every λ above seed noise, with the frozen consequence that a
P1 failure refutes deployability and demotes the headline to the measurement claims), E3 (Steam
n = 5), E4 (coverage-unit drift). P1 failed on both datasets (§4); this paper executes the frozen
consequence.

---

## 4 Results

*(Imported from SECTION_RHO_K_RESULTS.md; numbers authoritative and unaltered.)*

All numbers: text retriever (primary), K=200, fCE checkpoints at the primary LR, event-stride 2,
n=5 seeds (MI) / n=3 (Steam), CIs two-sided t at α=0.05. Both structural gates (pool-hit ≥
full-catalog-hit; monotone in K) passed in all 13 runs. Analyzer frozen before any result was read
(`poc_rho_k_analyze.py`); prereg `PREREG_RHO_K_V1.md`.

### T1. The conversion ratio ρ(k) = R(k)/R_warm, forced coverage

| bucket | MI d=256 (primary) | MI d=64 | Steam d=256 |
|---|---|---|---|
| k=0 | 0.0002 [0.0000, 0.0004] | 0.0003 [0.0000, 0.0007] | 0.0001 [−0.0001, 0.0003] |
| k1–2 | 0.0154 [0.0132, 0.0176] | 0.0093 [0.0053, 0.0134] | 0.0328 [0.0142, 0.0515] |
| k3–5 | 0.0684 [0.0597, 0.0770] | 0.0469 [0.0192, 0.0747] | 0.0253 [−0.0139, 0.0644] |
| k6–10 | 0.1340 [0.1216, 0.1463] | 0.1110 [0.0613, 0.1607] | 0.0511 [0.0423, 0.0599] |
| k11–20 | 0.2437 | 0.2192 | 0.1036 |
| k21–50 | 0.4636 | 0.4770 | 0.1559 |
| k51–200 | 0.7729 | 0.7950 | 0.2411 |
| k>200 | 1.4544 | 1.4101 | 1.0871 |

**C1 (primary, pre-registered): SUPPORTED.** Every k ≤ 10 bucket has its upper CI bound below 0.5 on
every set. Handing a sub-threshold item free coverage buys, at best, 13% of a warm item's conversion
(MI k6–10), and at k ≤ 2 under 4%. The pre-registered falsification rule (any k ≤ 10 bucket with
ρ > 0.5) did not fire anywhere.

Sanity structure: ρ rises monotonically in k on every set; head items exceed the pooled warm
reference (ρ = 1.09–1.45), as they must.

### T2. Break-even prevalence π*(k, 200) = c/(g·ρ(k) + c), cited constants from arXiv:2606.29947

Trades: Yelp (g = +10pp, c = 4.5pp), Video Games (g = +2.2pp, c = 4.7pp).

| bucket | MI×Yelp | MI×VG | Steam×Yelp | Steam×VG |
|---|---|---|---|---|
| k=0 | 100.0% | 100.0% | 100.0% | 100.0% |
| k1–2 | 96.7% | 99.3% | 93.2% | 98.5% |
| k3–5 | **86.8%** | 96.9% | 94.7% | 98.8% |
| k6–10 | **77.1%** | 94.1% | **89.8%** | 97.7% |
| k11–20 | 64.9% | 89.8% | 81.3% | 95.4% |
| k21–50 | 49.3% | 82.2% | 74.3% | 93.2% |

**C2 (pre-registered as π\*(k≤10, 200) > 90% under both trades): PARTIALLY FAILED — reported as
failed, corrections-log entry, no post-hoc rescue.** The bar holds everywhere under the VG trade
(94.1–100%) but fails under the Yelp trade at MI k3–5 (86.8%) and k6–10 (77.1%), and marginally at
Steam k6–10 (89.8%). The substantive point survives — a break-even prevalence of 77–100% still
exceeds any plausible cold-target share — but the pre-registered round-number bar was mis-set, and
the honest lesson is that C2's threshold should have been derived from a stated prevalence ceiling
rather than chosen at 90%. We report the failure; we do not restate the bar.

### T3. The selection bias of natural coverage (C3, descriptive): CONFIRMED

R_nat (conversion conditional on the retriever *naturally* covering gold) versus R_forced, MI d=256:

| bucket | R_forced | R_nat | inflation |
|---|---|---|---|
| k11–20 | 0.1063 | 0.2333 | **2.2×** |
| k21–50 | 0.2024 | 0.3947 | **2.0×** |
| k51–200 | 0.3377 | 0.6080 | 1.8× |

Conditioning on natural coverage — which is what any evaluation does when it measures conversion at
each arm's own coverage — inflates apparent mid-bucket cold conversion by about 2×. This is
weakness 5.1 of the derivation made measurable, and it is the reason the instrument forces coverage
instead.

### The screen k̂(K): necessary but not sufficient

k̂ binds only against a stated prevalence. Illustration at π = 40% (inside the 38–78% range of
observed cold-target prevalence in our temporal windows): under the Yelp trade, MI's smallest
bucket passing the screen is k51–200 (π* ≈ 37% < 40%, while π\*(k21–50) = 49.3% > 40%) → k̂ ≈ 51;
under the VG trade even k21–50 fails (82.2%) → k̂ > 50. v2 delivered this as the rule "admit
bucket k iff π > π\*(k, K) + drift budget". E2 below refutes that rule's deployability, and the
drift budget was not confirmed (E4: π\*(k) moves ≤ 1.7pp between windows in coverage units). What
survives is a **screen**: a bucket with π < π\*(k, K) cannot pay for its slot *through its own
conversions* — E2 confirms this side directly, cold end-to-end success staying ≈ 0 at every mixing
level — but passing the screen licenses nothing, because the end-to-end effect of a mix
intervention is dominated by a displacement term segment-additive accounting does not contain.

### Two structural observations the paper must state

1. **ρ is pool-composition-relative.** Under the popularity retriever the same gold items convert
   very differently (e.g. MI head R_forced 0.29 vs 0.64 under text pools): R measures gold against
   the pool's competitors, so ρ must always be computed against the same-retriever warm reference —
   as the prereg specifies — and never transported across retrievers.
2. **In a single-stage scorer the decomposition is vacuous.** Pool-hit under a pool built from the
   ranker's own top-(K−1) reduces to full-catalogue hit (design doc §2). Coverage and conversion
   are separable only when retriever and ranker differ; this is why the coverage/conversion split is
   a statement about two-stage pipelines.

### A1 results: own-dataset trades, and the pre-registered validation that failed

Frozen rules: PREREG_RHO_K_V1 §5a. All cells ran to completion (12 Steam trainings + 30 evals).

**E3 — Steam at n=5: CONFIRMED.** New-seed ρ(k) falls inside every n=3 CI
(k0/k1–2/k3–5/k6–10 = 0.0001/0.0242/0.0236/0.0442). C1 unchanged.

**E1 — own-dataset trades (replacing the cross-dataset transplant).** Deterministic across seeds
(coverage depends only on the frozen retrievers). MI, λ=0.2: each sub-k50 bucket gains +1.3–2.1pp
coverage while k51–200 loses −5.36pp; Steam similar with the head paying −2.13pp. These trades feed
the E2 prediction below; the cited Yelp/VG constants are retained only for the historical C2 table,
which stays failed as registered.

**E2 — P1 sign-agreement: REFUTED on both datasets.** Quota-mix pools (text priority, popularity
fill, K=200, no forced gold), λ ∈ {0…1}:

| λ | MI ΔS_meas | MI ΔS_pred | Steam ΔS_meas | Steam ΔS_pred |
|---|---|---|---|---|
| 0.2 | **+0.00129 ± 0.00050** | −0.00124 ± 0.00011 | **+0.00140 ± 0.00003** | −0.00540 ± 0.00017 |
| 0.4 | **+0.00195 ± 0.00057** | −0.00261 ± 0.00022 | +0.00108 ± 0.00021 | −0.01476 ± 0.00046 |
| 1.0 | −0.00722 ± 0.00047 | −0.03480 ± 0.00140 | −0.01771 ± 0.00178 | −0.07190 ± 0.00220 |

Sign agreement 0/5 seeds at every λ ≤ 0.5 on both datasets; agreement only at the pure-text
endpoint λ=1.0 (5/5). P2 also fails (prediction 4–5× over-pessimistic). **Per the frozen
consequence: forced-coverage R does not transfer to realistic mixed pools, and π\*(k,K) is not
deployable as a slot-mix predictor. The headline demotes to the measurement claims.**

**What the failure reveals (E2's actual finding).** Mixing text slots into a popularity pool
*improves* end-to-end success at moderate λ even though every marginal covered cold item converts
at ρ ≈ 0 — cold end-to-end success stays ≈ 0 at every λ. The gain comes from the swap changing the
**competitor set** for still-covered warm targets: R is pool-composition-dependent (structural
observation 1), so segment-additive coverage × conversion accounting mispredicts even the sign. A
third term — competition displacement — dominates at realistic mixing levels. This indicts the
naive coverage ledger and our corrected break-even equally, and it is the strongest argument in the
paper for measuring conversion *in situ* rather than importing it.

**E4 — coverage-unit drift: prediction NOT confirmed, in the instrument's favour.** π\*(k) moves
≤ 1.7pp between the inner (0.60–0.75) and outer windows on MI (predicted: >5pp in half the buckets,
by analogy with the +19–31pp NDCG-unit drift). ρ(k) is temporally stable in coverage units; the
deployability failure above is structural, not drift. The drift-budget clause is replaced by this
measured-stability statement.

**Appendix — loss-arm robustness.** ρ(k) is nearly loss-invariant at d=256 (gBCE slightly lower in
the lowest buckets: 0.0050 vs 0.0154 at k1–2). The instrument's readings are not an artifact of the
full-CE objective.

---

## 5 Related work and claims

*(Imported from SECTION_RHO_K_RELATED_WORK.md; organized by claim boundary, not by topic: each
cluster states what the prior work does and the exact residual we claim on top of it.)*

### 5.1 The coverage bottleneck and its failed mitigations

arXiv:2606.29947 measures the retrieval bottleneck in LLM-based cold-start recommendation across
five domains: a single retriever places the gold item in a 200-item pool only 4.6–22.9% of the
time, and 32–91% of cold-start targets are never covered. They then evaluate eight mitigations —
LLM scale (8B→70B), dense retrievers, two-tower models, reciprocal-rank fusion, CARA static
allocation, graph-evidence prompts, tail-prior injection, and LLM reranking — and report that
every one fails or is modest. All eight act on coverage; none acts on the conditional conversion
rate of a covered item. They also quantify the regime conflict of coverage-aware training as a
measured trade (5× upweighting of item-new positives: Yelp +10pp new-item coverage for −4.5pp
warm; Video Games +2.2pp for −4.7pp) and state it strictly as a measurement finding — no
break-even analysis, Pareto frontier, or constrained optimization is presented. Their conditional
metrics are stratified by coarse coldness buckets (item-new, item-cold, long-tail, user-cold,
warm), not by training degree. Our relationship to this paper is deliberately parasitic: we take
their measured coverage trade as cited constants, unmodified, and supply the decision formalism
they do not attempt — the break-even prevalence π\*(k,K) that says when, if ever, that trade pays.
Their eight negative results are then not eight independent facts but one fact: every mitigation
attacked Cov while R was the binding factor (§5.5 and the Discussion).

### 5.2 Separating coverage from conversion

The decomposition of end-to-end success into coverage × conditional conversion is standard
two-stage retrieval analysis, and we claim no part of it. arXiv:2604.16318 already separates
reranking quality from retrieval coverage with a dual-regime protocol whose positive-controlled
regime guarantees the gold item is present in the pool; forcing coverage to 1 in order to read
conversion directly is their instrument, and injecting the gold item into a sampled candidate set
is older still — it is the sampled-metrics evaluation tradition, whose properties and pitfalls
are analyzed by Ekstrand et al. (arXiv:2309.11723). What these works do not produce is the object
we measure: the degree-resolved conversion curve R(k) under forced coverage, its warm-normalized
ratio ρ(k) = R(k)/R_warm, and the chain that carries ρ(k) into an allocation decision via
π\*(k,K) = c_cov/(g_cov·ρ(k) + c_cov). arXiv:2604.16318 uses the positive-controlled regime as a
benchmark condition; we use it as a measurement instrument and read a curve off it.

### 5.3 Allocation of retrieval budget

Learned and operational allocation of candidate-generation budget exists and is not ours. CAPTS
(arXiv:2602.12564) coordinates trigger-to-channel assignment under per-channel retrieval budgets
with a learned value-attribution scorer and an explicit downstream-utility objective; it owns the
"downstream-utility-aware allocation" framing, provides no closed form, and its setting contains
no cold content (its users average roughly a thousand interactions). MIREC (arXiv:2305.12319)
allocates exposure shares across channels by an online-LP dual-price threshold — a data-driven
dual variable, not an analytic break-even. Multi-Decoder OneRec (arXiv:2607.26500) assigns
explicit per-route quotas to objective-specific retrieval routes; RealRoute (arXiv:2604.20860)
uses manually configured per-category caps with no cost-benefit derivation. These works allocate
along the channel or route axis, by learned or hand-set mechanisms; we derive a closed-form
break-even on the cold/warm axis, from cited constants plus one measured curve, and pair it with a
pre-registered end-to-end validation whose failure we report as a first-class result: the closed
form's inputs are temporally stable in coverage units (π\*(k) moves ≤ 1.7pp between adjacent
windows, E4) but not composition-transportable (E2), so the form is a screen, not a deployable
allocator. The contribution is the arithmetic, its measured inputs, and the measured boundary of
its validity — not an allocation system.

### 5.4 Production admission gates

Derived thresholds must be distinguished from tuned ones, and tuned ones are published. Google's
multi-funnel fresh-content system (KDD'23, arXiv:2306.01720) applies a graduation filter that
removes an item from the dedicated fresh funnel after ≥ n consumptions, with n set operationally;
Kuaishou's cold-start pipeline (WWW'25, 10.1145/3701716.3715205) gates items through
exposure-threshold growth phases. Admission rules for cold items therefore exist in production
practice. What does not exist, to our knowledge, is a gate whose threshold is derived from a
measurement: our k̂(K) is the smallest training degree at which π\*(k,K) falls below a plausible
deployment prevalence — an output of the ρ(k) instrument plus published constants, not a tuned
hyperparameter. The claim is "first measurement-derived", never "first" — and after the E2
refutation it is a necessary-but-insufficient *screen*, not an admission rule: production gates
decide deployment; k̂(K) only says which items cannot pay through their own conversions.

### 5.5 Cold-warm thresholds and the unrankability floor

arXiv:2508.07856 varies per-item training degree interventionally and measures the item cold-warm
transition at 6–15 interactions; it characterizes the threshold and proposes no rule for acting
on it. We cite it twice: as independent corroboration that the interesting structure in k is
below ~16, and as the foil that motivates a derived screen where the literature offers measured
transition points and ad hoc cutoffs. The floor that makes the screen bite — strictly cold items
are unrankable — is our program's most replicated finding (cold NDCG@10 exactly 0.00000 across
two loss families and five training arms) and is independently replicated in semantic-ID
generative retrieval by arXiv:2607.21101, which reports cold NDCG@20 = 0.00000 on
Beauty/Sports/Toys/WeiboTech. That is R_cold ≈ 0 in a third architecture family, measured by
authors with no stake in our thesis.

### 5.6 Non-threats

Two adjacent works are structurally unrelated and are noted only to pre-empt the association.
arXiv:1601.04745 budgets exploration for a single cold target via a two-stage POMDP — a
per-target probe/batch schedule, not pool allocation and not prevalence-indexed. arXiv:2605.27439
audits LLM assistants nominating brands, stratified by prominence tiers; prominence there is an
externally sourced awareness footprint, not training interaction degree, its conversion rates run
25–52% (nowhere near ρ ≈ 0), and it derives no decision rule — we cite it only as independent
evidence that coverage and conversion dissociate by popularity tier.

### 5.7 Claims and non-claims

**We claim four things.** (1) The measurement claims: the degree-resolved curve ρ(k) under forced
coverage with its pre-registered outcome (upper CI < 0.5 in every k ≤ 10 bucket on both datasets),
and the ~2× natural-coverage selection bias. (2) The closed-form break-even
π\*(k,K) = c_cov/(g_cov·ρ(k) + c_cov) and the degree-indexed screen k̂(K) it induces — demoted, per
the frozen consequence of the failed E2 validation, from admission rule to necessary-but-
insufficient screen (the smallest degree at which a slot could even in principle pay through the
item's own conversions; coverage-unit inputs stable to ≤ 1.7pp, E4). To our knowledge the first
measurement-derived screen of its kind; tuned operational gates precede it (arXiv:2306.01720;
10.1145/3701716.3715205). (3) The pre-registered refutation itself: segment-additive
coverage × conversion ledgers — naive or corrected — mispredict the sign of quota-mix
interventions, because R is pool-composition-dependent and competition displacement is first-order
(E2). (4) An explanation of arXiv:2606.29947's eight failed mitigations from the cold side: all
eight attack coverage while cold conversion binds — with the E2 caveat that mix interventions can
still pay end-to-end through warm-side displacement, never through the cold items themselves.

**We do not claim** the coverage × conversion decomposition (standard two-stage analysis;
arXiv:2604.16318), the gold-injection / forced-coverage protocol (sampled-metrics tradition;
arXiv:2309.11723; arXiv:2604.16318), the "downstream-utility-aware allocation" framing
(arXiv:2602.12564), or any algorithmic fix — this paper is a measurement, a screen, and a
pre-registered refutation of the screen's rule form; it is not a method.

---

## 6 Limitations and threats to validity

Stated here as they were stated in the derivation before any measurement ran, plus the scope
limits of the instrument itself.

1. **R is not intervention-invariant (the serious one — now measured, and worse than the bound).**
   The break-even holds R fixed, but interventions change pool composition, and the instrument's
   one-sided bound (forced coverage overestimates the marginal item's ρ, so π\* is underestimated
   and the cold-side conclusion holds a fortiori) covers only the cold segment's own R. E2 turned
   the warm side of this threat from a caveat into a measured refutation: warm R shifts with pool
   composition strongly enough to flip the sign of the end-to-end effect (§4).
2. **ρ(k), not ρ.** The exact-zero unrankability result is a k = 0 fact; everything above k = 0 is
   a measured curve with CIs, and the k = 0 bucket itself is degenerate (prior work already has
   cold NDCG exactly 0 there) and is reported flagged, not leaned on.
3. **K is a free parameter.** The displacement cost c_cov is a function of pool size K, and the
   trade softens at larger K; π\* is only meaningful as π\*(k, K), and all headline numbers here
   are K = 200 (the cited paper's setting).
4. **Cross-setup transfer of ρ is not automatic.** ρ is pool-composition-relative (T3 and the
   structural observations in §4): it is defined against a same-retriever warm reference and must
   be re-measured in any target setup, never imported.
5. **The constants are one paper's setup.** g_cov and c_cov are arXiv:2606.29947's published
   Yelp/Video Games trades, used as-is and cited; a different coverage intervention has a
   different trade and needs its own π\* table.
6. **Single-architecture ranker.** All conversion measurements use one ranker family: a sequential
   recommender with an HSTU-style encoder (relative time-bucket attention bias, positional RAB,
   causal filtering) over learned item embeddings augmented with frozen-SBERT text features and
   text-anchored prototype embeddings (K = 512), trained with chunked full cross-entropy at the
   primary LR. d = 64 and the other loss arms are robustness appendix material, not independent
   architectures; generative/SID rankers are untested here (though arXiv:2607.21101's exact-zero
   cold NDCG suggests ρ(0) ≈ 0 transfers).
7. **Two datasets, small n on one.** MI (n = 5 seeds) and Steam (n = 3 in the confirmatory matrix;
   raised to n = 5 by E3, whose new-seed ρ(k) fell inside every n=3 CI); the original n=3 CIs are
   correspondingly wide (one bucket's lower bound crosses zero in T1).
8. **Corrections log — P1 (E2) refuted.** Frozen: sign(ΔS_meas) = sign(ΔS_pred) at every λ above
   seed noise, both datasets. Outcome: 0/5 seeds agree at every λ ≤ 0.5 on both datasets;
   agreement only at λ = 1.0; P2 also failed (prediction 4–5× over-pessimistic). Consequence
   executed as registered: forced-coverage R does not transfer to realistic mixed pools, the
   rule's deployability is refuted, the headline demotes to the measurement claims. Lesson: the
   ledger omitted a first-order competition-displacement term no segment-additive correction
   recovers.
9. **Corrections log — E4 not confirmed.** Frozen: π\*(k) moves by >5pp in at least half the
   k ≤ 20 buckets between windows, by analogy with F01's +19–31pp NDCG-unit drift. Outcome:
   ≤ 1.7pp on MI. The failure is in the instrument's favour — ρ(k) is temporally stable in
   coverage units — but the analogy was wrong and is logged; the drift-budget clause is replaced
   everywhere by the measured-stability statement.
10. **One intervention family tested.** The E2 refutation is measured on quota-mix retriever
    mixing at eval time. Coverage-aware RETRAINING (arXiv:2606.29947's actual intervention)
    changes *which* items are covered and how they are scored, and could have different
    composition effects — untested; the refutation licenses no claim about its sign.

---

## 7 Position (~300 words)

The v3 position has two halves, and both are pre-registered outcomes, not readings.

**First: the cold items' binding constraint is conversion, and no mixing level rescues them.**
Under forced coverage, ρ(k ≤ 10) never reaches half the warm rate (upper CI < 0.5 everywhere);
and in E2's realistic quota-mixed pools, cold end-to-end success stays ≈ 0 at every mixing level
λ, on both datasets. Handing cold items coverage — free, forced, or bought — does not make them
convert. Title 1's claim survives its own validation on this half.

**Second: the ledger is wrong anyway.** Segment-additive coverage × conversion accounting — the
naive π\* = c/(g+c) *and* our corrected π\* = c/(g·ρ+c) — mispredicts the *sign* of mix-level
interventions, because R is pool-composition-dependent: swapping pool slots changes the competitor
set for still-covered warm targets, and that displacement term is first-order at moderate λ (E2:
measured deltas positive, predictions negative, 0/5 seeds in sign agreement at every λ ≤ 0.5).
A mix intervention can pay end-to-end while every marginal covered cold item converts at ρ ≈ 0 —
the gain simply never flows through the cold items.

**For practitioners.** Measure conversion in situ, under the actual pool composition you would
deploy — never imported from another setup, retriever, or a forced-coverage read. The instrument
here is the cheap first pass (eval-only, gold-injection, two structural gates), and it yields
k̂(K) as a **necessary-but-insufficient screen**: an item failing it cannot pay for its slot
through its own conversions (no bucket below k ≈ 51 clears a 40% prevalence bar under either
trade), but passing it is never a deploy signal. The end-to-end effect of a pool-mix change must
be measured, not ledgered.

**For researchers.** Report coverage gains only with conversion-conditioning *and* composition
controls. A coverage number is an upper bound, not an outcome: T3 shows conversion at natural
coverage flatters the mid buckets by ~2×, and E2 shows even correctly measured per-segment
conversion does not add across segments once pool composition shifts. Eight published
coverage-side mitigations failed in one benchmark; our arithmetic says the cold items could not
pay — and our validation says the arithmetic itself must be composition-checked before it is
trusted with a sign.

---

## References

All arXiv identifiers cited across the components, deduplicated:

- arXiv:1601.04745
- arXiv:2305.12319
- arXiv:2306.01720
- arXiv:2309.11723
- arXiv:2508.07856
- arXiv:2602.12564
- arXiv:2604.16318
- arXiv:2604.20860
- arXiv:2605.27439
- arXiv:2606.29947
- arXiv:2607.21101
- arXiv:2607.26500

Non-arXiv: DOI 10.1145/3701716.3715205 (Kuaishou cold-start pipeline, WWW'25).
