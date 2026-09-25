# Results: ρ(k) under forced coverage, and what the break-even arithmetic says

All numbers: text retriever (primary), K=200, fCE checkpoints at the primary LR, event-stride 2,
n=5 seeds (MI) / n=3 (Steam), CIs two-sided t at α=0.05. Both structural gates (pool-hit ≥
full-catalog-hit; monotone in K) passed in all 13 runs. Analyzer frozen before any result was read
(`poc_rho_k_analyze.py`); prereg `PREREG_RHO_K_V1.md`.

## T1. The conversion ratio ρ(k) = R(k)/R_warm, forced coverage

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

## T2. Break-even prevalence π*(k, 200) = c/(g·ρ(k) + c), cited constants from arXiv:2606.29947

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

## T3. The selection bias of natural coverage (C3, descriptive): CONFIRMED

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

## The admission rule k̂(K): a function, not a constant

k̂ binds only against a stated prevalence. Illustration at π = 40% (inside the 38–78% range of
observed cold-target prevalence in our temporal windows): under the Yelp trade, MI's smallest
admissible bucket is k51–200 (π* ≈ 37% < 40%, while π\*(k21–50) = 49.3% > 40%) → k̂ ≈ 51; under the
VG trade even k21–50 fails (82.2%) → k̂ > 50. The deliverable is therefore the table above plus the
rule "admit bucket k iff π > π\*(k, K) + drift budget", with the +19–31pp always-optimistic drift
correction measured in our F01 out-of-sample analysis carried over unchanged.

## Two structural observations the paper must state

1. **ρ is pool-composition-relative.** Under the popularity retriever the same gold items convert
   very differently (e.g. MI head R_forced 0.29 vs 0.64 under text pools): R measures gold against
   the pool's competitors, so ρ must always be computed against the same-retriever warm reference —
   as the prereg specifies — and never transported across retrievers.
2. **In a single-stage scorer the decomposition is vacuous.** Pool-hit under a pool built from the
   ranker's own top-(K−1) reduces to full-catalogue hit (design doc §2). Coverage and conversion
   are separable only when retriever and ranker differ; this is why the coverage/conversion split is
   a statement about two-stage pipelines.

---

# Addendum (Amendment A1): own-dataset trades, and the pre-registered validation that failed

Frozen rules: PREREG_RHO_K_V1 §5a. All cells ran to completion (12 Steam trainings + 30 evals).

## E3 — Steam at n=5: CONFIRMED
New-seed ρ(k) falls inside every n=3 CI (k0/k1–2/k3–5/k6–10 = 0.0001/0.0242/0.0236/0.0442).
C1 unchanged.

## E2 — P1 sign-agreement: REFUTED on both datasets
Quota-mix pools (text priority, popularity fill, K=200, no forced gold), λ ∈ {0…1}:

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

## E4 — coverage-unit drift: prediction NOT confirmed, in the instrument's favour
π\*(k) moves ≤ 1.7pp between the inner (0.60–0.75) and outer windows on MI (predicted: >5pp in
half the buckets, by analogy with the +19–31pp NDCG-unit drift). ρ(k) is temporally stable in
coverage units; the deployability failure above is structural, not drift. The drift-budget clause
is replaced by this measured-stability statement.

## E1 — own-dataset trades (replacing the cross-dataset transplant)
Deterministic across seeds (coverage depends only on the frozen retrievers). MI, λ=0.2: each
sub-k50 bucket gains +1.3–2.1pp coverage while k51–200 loses −5.36pp; Steam similar with the head
paying −2.13pp. These trades feed the E2 prediction above; the cited Yelp/VG constants are retained
only for the historical C2 table, which stays failed as registered.

## Appendix — loss-arm robustness
ρ(k) is nearly loss-invariant at d=256 (gBCE slightly lower in the lowest buckets: 0.0050 vs
0.0154 at k1–2). The instrument's readings are not an artifact of the full-CE objective.
