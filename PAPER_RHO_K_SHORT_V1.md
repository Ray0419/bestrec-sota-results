# Coverage Was Never the Binding Constraint: Break-Even Arithmetic and a Degree-Indexed Screen for Cold-Start Retrieval

**Draft v1 for the ACM RecSys short-paper track (compressed 2026-09-08 from `PAPER_RHO_K_SKELETON.md` v3).**
Format target per the RecSys 2026 CFP, assumed to carry to 2027: **4 double-column ACM pages for all
technical content (figures, tables, appendices included); references extra; mutually anonymous review;
GenAI use disclosed in Acknowledgments.** Body below is ≈2,900 words plus three compact tables, sized
for that budget. Anonymized: no repository names, no self-identifying protocol file names; the
pre-registration and analyzer are to be linked as an anonymous repository at submission. Every number is
copied unaltered from `SECTION_RHO_K_RESULTS.md` (including the A1 addendum); claims follow
`PREREG_RHO_K_V1.md`. Nothing here is new evidence.

*Provenance notes (2026-09-08).* Body (Abstract–Position) measures 3,147 words plus three tables, so
ACM layout will likely need a further ~10% cut; §5 and §3 are the designated targets. T1's Steam column
is the pre-registered n = 3 confirmatory read; `_bestrec_run/poc_out/RHO_K_analysis.json` on disk now
holds the E3 n = 5 rerun (text k1–2/k3–5/k6–10 = 0.0242/0.0236/0.0442, k21–50 = 0.1487), which is what
the E3 sentence in §4 quotes. MI d=256 values were re-checked against that JSON (0.01542/0.06836/0.13399).

---

## Abstract

A recent multi-domain study measures a retrieval bottleneck in LLM-based cold-start recommendation: a
single retriever places the gold item in a 200-item pool only 4.6–22.9% of the time, and eight
coverage-side mitigations all fail or are modest. We ask what a pool slot is actually worth to a cold
item. Under *forced coverage* (the gold item injected into every pool, so retriever selection bias
cannot enter, and the residual bias runs against our conclusion), the pre-registered conversion ratio
ρ(k) = R_cold(k)/R_warm has its upper confidence bound below 0.5 in every training-degree bucket
k ≤ 10 on two datasets, with ρ(0) ≈ 0.0002. Substituting ρ(k) into the corrected break-even prevalence
π\* = c/(g·ρ + c), with the published coverage trades as constants, gives π\*(k ≤ 10, K=200) of
77–100%: no plausible cold prevalence pays. We then pre-registered an end-to-end validation of the
resulting admission rule on quota-mixed pools, and it **failed on both datasets**: measured deltas are
positive at moderate mixing while the segment-additive prediction is negative. The gain never flows
through the cold items, whose end-to-end success stays ≈ 0 at every mixing level; it comes from
competitor-set displacement among warm targets. Our position is therefore two-sided. Conversion, not
coverage, binds for cold items, and no mixing level rescues them. But coverage × conversion ledgers,
naive or corrected, mispredict the *sign* of mix-level interventions, because conversion is
pool-composition-dependent. π\*(k,K) is a necessary-but-insufficient screen, never a deploy signal;
conversion must be measured in situ.

---

## 1 Introduction

Cold-start evaluation recently acquired a measured bottleneck. Across five domains, a single retriever
puts the gold item into a 200-item candidate pool only 4.6–22.9% of the time, and 32–91% of cold-start
targets are never covered at all [1]. The same study prices the fix: 5× upweighting of item-new
positives buys +10pp new-item coverage on Yelp at −4.5pp warm coverage, and +2.2pp on Video Games at
−4.7pp. It states, and does not attempt to answer, the decision question: at what cold-target
prevalence does that trade pay?

The naive answer is one line. An intervention with cold gain g and warm cost c pays iff prevalence π
exceeds π\* = c/(g + c). Coverage is a per-event average over the same cold/warm partition as NDCG, so
the identity transfers exactly and the published trades give 31.0% (Yelp) and 68.1% (Video Games).
This is wrong, and not in the algebra. NDCG is (approximately) the objective; coverage is an upper
bound on it. Writing end-to-end success as coverage times the conditional conversion rate
R = P(top-k | in pool), standard two-stage analysis that we do not claim, and setting the change in
success to zero gives

> π\* = c / (g·ρ + c),  ρ = R_cold / R_warm,

of which the naive form is the special case ρ = 1. Everything hinges on ρ. The most replicated finding
of our own earlier measurements is that strictly cold items are unrankable: cold NDCG@10 is exactly
0.00000 across two loss families and five training arms, and semantic-ID generative retrieval
independently reports exactly 0.00000 [2]. If ρ ≈ 0 then π\* → 1 and no prevalence justifies the trade.

But "strictly cold" is k = 0, not the item-new segments of published benchmarks, so the right object is
the degree-indexed curve ρ(k). Measuring it naively is biased in our own favour: a retriever covers the
easy cold items first, so conversion conditional on *natural* coverage is computed on a favourable
subset. We measure that inflation at roughly 2× in mid buckets. The instrument therefore forces
coverage, injecting the gold item into every pool, which removes retriever selection entirely. The
residual bias is one-sided and runs against us: forced coverage averages over items no real retriever
reaches, so it overestimates ρ and underestimates π\*. If even this optimistic ρ yields π\* near 1, the
conclusion holds a fortiori.

All results were pre-registered with frozen falsification rules, and three frozen predictions failed:
the 90% bar on π\* (partially); the end-to-end validation of the admission rule (on both datasets); and
a drift prediction, in the instrument's favour. We report all three unsoftened and execute the frozen
consequence: the headline demotes to the measurement claims and the admission rule to a
necessary-but-insufficient screen. Our contribution is the arithmetic, the degree-resolved
measurement of its inputs, and the measured boundary of its validity.

---

## 2 The break-even rule

**Original form.** With cold gain g > 0 and warm cost |c| > 0 in NDCG@10 and cold prevalence π, the
expected change E = π·g − (1−π)·|c| is an arithmetic identity, and E = 0 at π\* = |c|/(g + |c|).

**Naive port to coverage.** Coverage is P(gold ∈ pool), also a per-event average over the same
partition, so π\*_cov = c_cov/(g_cov + c_cov): 31.0% for Yelp and 68.1% for Video Games under the
published trades [1]. The port is wrong because maximising coverage equals maximising end-to-end
quality only if a covered cold item converts at the warm rate.

**Corrected form.** Let R_s = P(top-k | gold ∈ pool) for segment s, so end-to-end success is
S_s = Cov_s · R_s. Holding R fixed (an assumption we bound in §3 and then falsify on the warm side in
§4) and setting ΔS = 0 gives π\* = c_cov/(g_cov·ρ + c_cov). Its sensitivity to ρ is the whole point:

| ρ | Yelp π\* | Video Games π\* |
|---|---|---|
| 1 (naive) | 31.0% | 68.1% |
| 0.1 | 81.8% | 95.5% |
| 0.01 | 97.8% | 99.5% |
| → 0 | → 100% | → 100% |

Even at ρ = 1, Video Games already needs 68% cold prevalence. This also gives a single mechanism for
the eight failed mitigations in [1]: every one attacks Cov, none attacks R, and their own
positive-controlled regime (coverage forced to ceiling) still finds LLM rerankers failing to beat
CF/content baselines, a direct and low read on R. Two empirical questions remain: ρ(k), degree by
degree, and whether the segment-additive form survives a real intervention. §4 answers the first
affirmatively and the second negatively.

---

## 3 The instrument

**Target.** ρ(k) = R(k)/R_warm with R = P(gold ∈ top-10 of the pool | gold ∈ pool), sliced by the
target item's pre-cutoff training degree in buckets 0, 1–2, 3–5, 6–10, 11–20, 21–50, 51–200, >200.

**Forced coverage.** The gold item is injected into every pool; this is the positive-controlled regime
of [3] used as a measurement instrument rather than a benchmark condition, and gold-injection itself
is the sampled-metrics tradition [4]. Natural-coverage conditioning is disqualifying, not merely
untidy: it computes R on the subset the retriever already found easy, which rises artificially as
coverage expands. Forced coverage removes that selection; its residual bias overestimates ρ.

**Vacuity in single-stage scorers.** A pool built from the ranker's own top-(K−1) plus gold is
degenerate: pool-hit@10 reduces to full-catalogue hit@10. Coverage and conversion are separable only
when retriever and ranker are different models, which is why [1], whose generators and rerankers are
distinct, could see the split at all.

**Design.** Retriever Q ≠ ranker M. Pool = top_{K−1}(Q) ∪ {gold}; M scores the pool; the endpoint is
gold's hit@10 within the pool. Two retrievers, both reported: Q_text (frozen sentence-embedding
title kNN, the cold-capable family) and Q_pop (global popularity, which structurally cannot reach
cold items). K ∈ {100, 200, 500, 1000}, K = 200 primary (the setting of [1]); π\* is always reported
as π\*(k, K). R_warm is the event-weighted pooled hit@10 over k ≥ 51 within the same retriever's
pools; ρ is never transported across retrievers. The ranker is a sequential recommender (HSTU-style
encoder with frozen text features, chunked full cross-entropy), evaluated only; no training.
Datasets: Amazon Musical Instruments (MI; n = 5 seeds) and Steam (n = 3, raised to 5 in the
validation stage), under a global-time protocol. Two structural gates must pass in every run: G1,
pool-hit ≥ full-catalogue hit; G2, pool-hit monotone in K. The falsification rule was frozen before
any evaluation: the thesis is refuted if ρ(k) > 0.5 in any bucket at k ≤ 10 on either dataset.

**Amendment A1 (frozen before any validation run).** Because the confirmatory π\* table transplants
the trades of [1] onto our ρ, we added an own-dataset end-to-end validation: E1, own quota-mix
coverage trades; E2 (primary), frozen prediction P1 that sign(ΔS_meas) = sign(ΔS_pred) at every
mixing level λ above seed noise, with the frozen consequence that a P1 failure refutes deployability
and demotes the headline; E3, Steam at n = 5; E4, coverage-unit temporal drift.

---

## 4 Results

Text retriever, K = 200, event-stride 2, two-sided t CIs at α = 0.05; both structural gates passed in
all 13 confirmatory runs; the analyzer was frozen before any result was read.

**T1. Conversion ratio ρ(k) under forced coverage.**

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

**C1 (primary, pre-registered): supported.** Every k ≤ 10 bucket has its upper CI bound below 0.5 on
every set. Free coverage buys a sub-threshold item at most 13% of a warm item's conversion (MI k6–10)
and under 4% at k ≤ 2. ρ rises monotonically in k and head items exceed the pooled warm reference, as
they must. E3 (Steam n = 5) reproduced every n = 3 bucket inside its CI
(k0/k1–2/k3–5/k6–10 = 0.0001/0.0242/0.0236/0.0442).

**T2. Break-even prevalence π\*(k, 200) = c/(g·ρ(k) + c)** with the cited trades (Yelp g=+10pp,
c=4.5pp; Video Games g=+2.2pp, c=4.7pp):

| bucket | MI×Yelp | MI×VG | Steam×Yelp | Steam×VG |
|---|---|---|---|---|
| k=0 | 100.0% | 100.0% | 100.0% | 100.0% |
| k1–2 | 96.7% | 99.3% | 93.2% | 98.5% |
| k3–5 | **86.8%** | 96.9% | 94.7% | 98.8% |
| k6–10 | **77.1%** | 94.1% | **89.8%** | 97.7% |
| k11–20 | 64.9% | 89.8% | 81.3% | 95.4% |
| k21–50 | 49.3% | 82.2% | 74.3% | 93.2% |

**C2 (pre-registered: π\*(k ≤ 10, 200) > 90% under both trades): partially failed, reported as
failed.** The bar holds under the VG trade (94.1–100%) but fails under the Yelp trade at MI k3–5
(86.8%), MI k6–10 (77.1%) and marginally at Steam k6–10 (89.8%). The substantive point survives, since
77–100% exceeds any plausible cold share, but the round-number bar was mis-set; it should have been
derived from a stated prevalence ceiling. We do not restate it.

**T3. Selection bias of natural coverage (C3, descriptive): confirmed.** On MI d=256,
R_nat/R_forced = 0.2333/0.1063 = 2.2× at k11–20, 0.3947/0.2024 = 2.0× at k21–50, and 1.8× at k51–200.
Conditioning on natural coverage, which is what an evaluation does when it measures conversion at each
arm's own coverage, inflates apparent mid-bucket cold conversion by about 2×.

**The screen k̂(K).** At an illustrative π = 40% (inside the 38–78% cold-target prevalence range of
our temporal windows), the smallest MI bucket passing under the Yelp trade is k51–200
(π\* ≈ 37%), so k̂ ≈ 51; under the VG trade even k21–50 fails (82.2%). A bucket with
π < π\*(k, K) cannot pay for its slot through its own conversions. E2 shows that passing the screen
licenses nothing further.

**E1. Own-dataset trades.** Deterministic across seeds (coverage depends only on the frozen
retrievers). MI at λ = 0.2: every sub-k50 bucket gains +1.3–2.1pp coverage while k51–200 loses
−5.36pp; Steam is similar with the head paying −2.13pp.

**E2. Sign-agreement validation P1: refuted on both datasets.** Quota-mixed pools (text priority,
popularity fill, K = 200, no forced gold), λ ∈ {0…1}, ΔS = change in end-to-end hit@10:

| λ | MI ΔS_meas | MI ΔS_pred | Steam ΔS_meas | Steam ΔS_pred |
|---|---|---|---|---|
| 0.2 | **+0.00129 ± 0.00050** | −0.00124 ± 0.00011 | **+0.00140 ± 0.00003** | −0.00540 ± 0.00017 |
| 0.4 | **+0.00195 ± 0.00057** | −0.00261 ± 0.00022 | +0.00108 ± 0.00021 | −0.01476 ± 0.00046 |
| 1.0 | −0.00722 ± 0.00047 | −0.03480 ± 0.00140 | −0.01771 ± 0.00178 | −0.07190 ± 0.00220 |

Sign agreement is 0/5 seeds at every λ ≤ 0.5 on both datasets, and 5/5 only at the pure-text
endpoint λ = 1.0; the secondary magnitude prediction also fails (4–5× over-pessimistic). Per the frozen
consequence, forced-coverage R does not transfer to realistic mixed pools and π\*(k,K) is not
deployable as a slot-mix predictor.

**What the failure reveals.** Mixing text slots into a popularity pool *improves* end-to-end success at
moderate λ even though every marginal covered cold item converts at ρ ≈ 0; cold end-to-end success
stays ≈ 0 at every λ. The gain comes from the swap changing the competitor set for still-covered warm
targets. R is pool-composition-dependent (the same gold items convert at 0.29 under popularity pools
versus 0.64 under text pools at the head), so segment-additive coverage × conversion accounting
mispredicts even the sign; a competition-displacement term dominates at realistic mixing. This
indicts the naive ledger and our corrected break-even equally.

**E4. Coverage-unit drift: not confirmed, in the instrument's favour.** π\*(k) moves ≤ 1.7pp between
adjacent temporal windows on MI (predicted > 5pp in half the buckets, by analogy with the +19–31pp
NDCG-unit drift we had measured earlier). The deployability failure is structural, not drift.
ρ(k) is also nearly loss-invariant (gBCE 0.0050 vs full-CE 0.0154 at k1–2).

---

## 5 Related work and claims

**The coverage bottleneck [1]** is measured across five domains with eight mitigations (LLM scale
8B→70B, dense retrievers, two-tower, rank fusion, static cold-aware allocation, graph-evidence
prompts, tail-prior injection, LLM reranking), all failing or modest, and prices the regime conflict as
a measured trade with, in its own words, no break-even analysis, Pareto frontier or constrained
optimisation. Its conditional metrics are stratified by coarse coldness bucket, not training degree.
We take its trade as cited constants and supply the decision formalism it does not attempt.

**Coverage versus conversion.** The decomposition is standard two-stage analysis; [3] already
separates reranking quality from retrieval coverage with a positive-controlled regime, and gold
injection is the sampled-metrics tradition analysed by [4]. We claim neither; we claim the
degree-resolved curve R(k), its warm-normalised ratio ρ(k), and the chain into π\*(k,K).

**Allocation of retrieval budget.** Learned, downstream-utility-aware allocation of candidate-generation
budget across channels exists [5], as do online-LP exposure duals [6], explicit per-route quotas [7] and
hand-set per-category caps [8]. These allocate on the channel or route axis by learned or tuned
mechanisms; we derive a closed form on the cold/warm axis from cited constants plus one measured
curve, and pair it with a pre-registered validation whose failure is a first-class result: the inputs
are temporally stable in coverage units (E4) but not composition-transportable (E2).

**Production admission gates** exist and are tuned: a graduation filter after ≥ n consumptions with n
set operationally [9], and exposure-threshold growth phases [10]. Ours is, to our knowledge, the first
*measurement-derived* screen, and after E2 it is a screen, not a gate.

**Thresholds and the unrankability floor.** Interventional per-item degree variation places the
cold-warm transition at 6–15 interactions and proposes no rule for acting on it [11]; we cite it as
corroboration that the structure in k lies below ~16. The floor that makes the screen bite (strictly
cold items unrankable) is replicated in semantic-ID generative retrieval at exactly 0.00000 [2], i.e.
R_cold ≈ 0 in a third architecture family measured by authors with no stake in our thesis.

**Claims.** (1) The measurements: ρ(k) under forced coverage with its pre-registered outcome and the
~2× natural-coverage selection bias. (2) The closed form π\*(k,K) and the induced screen k̂(K),
demoted per the frozen consequence from admission rule to necessary-but-insufficient screen. (3) The
pre-registered refutation: segment-additive coverage × conversion ledgers, naive or corrected,
mispredict the sign of quota-mix interventions because R is pool-composition-dependent. (4) A
single mechanism for the eight failures in [1]: all attack coverage while cold conversion binds, with
the caveat that mix interventions can still pay through warm-side displacement.
**Non-claims:** the decomposition, the forced-coverage protocol, the allocation framing of [5], and
any algorithmic fix. This is a measurement, a screen and a refutation, not a method.

---

## 6 Limitations

(1) R is not intervention-invariant: the instrument's bound covers only the cold segment's own R, and
E2 shows warm R shifts with composition strongly enough to flip the sign of end-to-end effects.
(2) The k = 0 bucket is degenerate (prior work already reports exact zero there) and is flagged, not
leaned on. (3) K is free; c_cov depends on pool size, so all headline numbers are K = 200. (4) ρ is
pool-composition-relative and must be re-measured in any target setup, never imported. (5) The trade
constants are one paper's setup. (6) One ranker family; generative rankers untested here.
(7) Two datasets, n = 3 in the Steam confirmatory matrix (raised to 5 in E3), so one bucket's lower
bound crosses zero in T1. (8) One intervention family: E2 mixes retrievers at evaluation time;
coverage-aware *retraining*, the intervention of [1], changes which items are covered and how they
are scored and could have different composition effects. Corrections log: three frozen predictions
failed (C2 partial, P1, E4) and are reported without post-hoc rescue.

---

## 7 Position

**Conversion, not coverage, binds for cold items, and no mixing level rescues them.** Under forced
coverage ρ(k ≤ 10) never reaches half the warm rate, and in realistic quota-mixed pools cold
end-to-end success stays ≈ 0 at every λ on both datasets. Coverage handed to cold items, free or
bought, does not make them convert.

**The ledger is wrong anyway.** Both the naive π\* = c/(g+c) and our corrected π\* = c/(g·ρ+c)
mispredict the sign of mix-level interventions, because swapping pool slots changes the competitor set
for still-covered warm targets, and that displacement term is first-order at moderate λ. A mix
intervention can pay end-to-end while every marginal covered cold item converts at ρ ≈ 0.

**For practitioners:** measure conversion in situ, under the pool composition you would deploy. The
instrument here is the cheap first pass (eval-only, gold injection, two structural gates) and yields
k̂(K) as a screen: an item failing it cannot pay for its slot through its own conversions; passing it
is never a deploy signal. **For researchers:** report coverage gains only with conversion-conditioning
and composition controls. A coverage number is an upper bound, not an outcome; natural-coverage
conversion flatters the mid buckets by ~2×, and even correctly measured per-segment conversion does
not add across segments once pool composition shifts.

---

## Acknowledgments

*[GenAI disclosure required by the RecSys CFP in this section: state the extent and nature of
generative-AI use in analysis code, drafting and literature search; the human authors verified every
number against the released artifacts and retain full responsibility. Fill from
`AUTHORSHIP_AI_STATEMENT.md` short form.]*

## References (to be formatted in ACM style; arXiv identifiers as recorded)

1. Diagnosing and Mitigating Retrieval Bottlenecks in LLM-Based Cold-Start Recommendation. arXiv:2606.29947.
2. Can Generative Recommendation Reach Cold Items? A Temporal Perspective on Semantic-ID Generation. arXiv:2607.21101.
3. LLM-reranker dual-regime evaluation protocol. arXiv:2604.16318.
4. Ekstrand et al. Sampled metrics and their pitfalls. arXiv:2309.11723.
5. CAPTS: Channel-Aware, Preference-Aligned Trigger Selection for Multi-Channel Item-to-Item Retrieval. arXiv:2602.12564.
6. MIREC: Multi-channel Integrated Recommendation with Exposure Constraints. arXiv:2305.12319.
7. Multi-Decoder OneRec. arXiv:2607.26500.
8. RealRoute (Adaptive Cap). arXiv:2604.20860.
9. Multi-funnel fresh-content recommendation, KDD 2023. arXiv:2306.01720.
10. Kuaishou cold-start pipeline, WWW 2025. DOI 10.1145/3701716.3715205.
11. Recommendation Is a Dish Better Served Warm. arXiv:2508.07856.

*Retained from the skeleton but cut for space: arXiv:1601.04745 and arXiv:2605.27439 (non-threats); the
brand-audit dissociation citation may return in the camera-ready if space allows.*

---

## Compression ledger (not part of the manuscript)

| section | skeleton words | v1 words (approx.) | what was cut |
|---|---|---|---|
| Abstract | 283 | 230 | none substantive |
| 1 Intro | 603 | 450 | duplicated §2/§3 exposition |
| 2 Rule | 513 | 300 | E2 forward-references merged into one sentence |
| 3 Instrument | 509 | 330 | prose gates and lesson narrative shortened |
| 4 Results | 1,331 | 830 | T3 to one sentence; screen paragraph halved; loss-arm appendix to one clause |
| 5 Related | 1,253 | 420 | §5.6 non-threats removed; per-cluster residuals compressed to one clause each |
| 6 Limits | 609 | 200 | numbered clauses only |
| 7 Position | 370 | 200 | practitioner/researcher paragraphs merged |
| **Total** | **5,471 (body)** | **≈2,960** | |

Open human items before submission: author metadata; final GenAI statement; anonymous repository with
the pre-registration, analyzer and result JSONs; ACM template layout to confirm the 4-page fit (three
tables consume roughly 0.6 pages); reference titles/authors completed from the arXiv records.
