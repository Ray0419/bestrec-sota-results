# Step 1: can p* be ported from NDCG units to coverage units?

**Pure derivation, 2026-08-18. No GPU. Answer: the naive port is WRONG, and the corrected form
produces a sharper claim than the one we set out to make.**

## 1. The original p\*

An intervention produces cold gain `g > 0` and warm cost `|c| > 0` in NDCG@10; `π` is the prevalence
of cold-target events. Because NDCG is an average of a per-event quantity and the event set partitions
into cold and warm,

```
E  =  π·g − (1−π)·|c|                    (exact, an arithmetic identity)
p* =  |c| / (g + |c|)                    (E = 0)
```

Deploy iff `π > p*`. Our F01 result adds the deployable correction: `p*` drifts **+19–31pp** between
adjacent windows and is **always optimistic**, so the rule is `π > p* + drift budget`.

## 2. The naive port to coverage — and why it is wrong

Coverage is `P(gold ∈ pool)`, also an average of a per-event indicator over the same partition, so the
identity carries over exactly:

```
ΔCov  =  π·g_cov − (1−π)·c_cov
π*_cov =  c_cov / (g_cov + c_cov)
```

Plugging in arXiv:2606.29947's measured trade (5× upweighting of item-new positives):

| domain | g_cov | c_cov | naive π\*_cov |
|---|---|---|---|
| Yelp | +10 pp | −4.5 pp | **31.0%** |
| Video Games | +2.2 pp (1.6→3.8) | −4.7 pp (24.1→19.4) | **68.1%** |

**This is wrong, and the error is not in the algebra.** NDCG is (approximately) the objective. Coverage
is **not** — it is an upper bound on what the downstream ranker can reach. Being in the pool is
necessary, not sufficient. Maximising aggregate coverage is only equivalent to maximising end-to-end
quality if a covered cold item converts to a top-k hit at the same rate as a covered warm item. It does
not.

## 3. The corrected form: coverage × conversion

Let `R_s = P(ranked into top-k | gold in pool)` be segment `s`'s **conditional conversion rate**.
End-to-end success on segment `s` is `S_s = Cov_s · R_s`, so

```
S   =  π·Cov_cold·R_cold  +  (1−π)·Cov_warm·R_warm
ΔS  =  π·g_cov·R_cold − (1−π)·c_cov·R_warm          (holding R fixed — see §5.1)
```

Setting `ΔS = 0` and dividing through by `R_warm`, with the **conversion ratio** `ρ = R_cold / R_warm`:

```
                c_cov
π*  =  ───────────────────────
        g_cov·ρ  +  c_cov
```

The naive form is the special case `ρ = 1`. Everything hinges on `ρ`.

## 4. Why this matters: our own evidence says ρ ≈ 0

This program's most replicated finding is that **strictly cold items are unrankable** — cold NDCG@10 is
*exactly* 0.00000 across 2 loss families × 5 training arms, and independently in semantic-ID generative
retrieval (arXiv:2607.21101, cold NDCG@20 = 0.00000 on Beauty/Sports/Toys/WeiboTech). That is
`R_cold ≈ 0`, i.e. `ρ ≈ 0`. Then `π* → 1`:

| ρ | Yelp π\* | Video Games π\* |
|---|---|---|
| 1 (naive) | 31.0% | 68.1% |
| 0.1 | 81.8% | 95.5% |
| 0.01 | 97.8% | 99.5% |
| → 0 | **→ 100%** | **→ 100%** |

**No cold prevalence, however high, justifies buying cold coverage while ρ ≈ 0.** Note that even at the
naive `ρ = 1`, Video Games already needs 68% cold prevalence — implausible on its own.

This is a mechanism for arXiv:2606.29947's own negative results. They tried eight mitigations — LLM
scale 8B→70B, dense retrievers, two-tower, RRF fusion, CARA static allocation, graph-evidence prompts,
tail-prior injection, LLM reranking — and every one failed or was modest. **All eight attack `Cov`.
None attacks `R`.** The decomposition says the binding constraint is the factor they did not touch.

Two of their own measurements corroborate it:
- *"where coverage is non-trivial, LLM reranking removes more correct top-10 items than it adds"* —
  low conversion, not low coverage.
- their **positive-controlled regime**, in which the gold item is *guaranteed present* (i.e. coverage
  forced to 1), still finds calibrated LLM rerankers failing to beat CF/content baselines. That is a
  direct read on `R` with `Cov` held at ceiling, and it is low.

## 5. What is wrong with this derivation — stated now, not discovered by a reviewer

**5.1 `R` is not intervention-invariant (the serious one).** I held `R` fixed. But coverage-aware
retraining changes *which* cold items get covered — plausibly the easier ones first — so `R_cold |
covered` can rise as coverage rises. That is a selection effect and it biases `π*` in the direction
that favours our conclusion. The honest fix is to measure `R` **at matched coverage**, or to bound the
selection effect, before any claim.

**5.2 ρ ≈ 0 holds for strictly cold (k=0), not for "item-new".** Their `item-new` segment is not
guaranteed to be k=0. Our own dose-response puts rankability switching on around k ≈ 16, and
arXiv:2508.07856 reports item cold-warm thresholds of 6–15. So the correct object is **ρ(k)**, and
therefore **π\*(k)**. This is not a weakness so much as the actual deliverable: it yields a
**degree-indexed admission rule** — buy coverage only for items above the rankability threshold, and
never below it. That is directly actionable and it is exactly what our degree-slicing instrument
measures.

**5.3 Pool size K is a free parameter.** The displacement cost `c_cov` is a function of K; at larger K
the trade softens. `π*` must be reported as `π*(k, K)`, not a scalar.

**5.4 Cross-setup transfer of ρ is not automatic.** Their metric is coverage@200 with top-10
correctness; our conversion evidence is NDCG@10 under a different protocol. ρ must be re-measured in
the target setup, not imported.

**5.5 The decomposition itself is NOT novel.** Coverage × conversion is standard two-stage retrieval
analysis, and **arXiv:2604.16318 already separates reranking quality from retrieval coverage** via a
dual-regime protocol. We must not claim the decomposition. What is unclaimed is (a) folding ρ into a
**break-even prevalence rule** to turn it into an allocation *decision*, (b) the **degree-indexed**
ρ(k) → admission threshold, and (c) the resulting explanation of why eight coverage-side mitigations
failed. The novelty search must be run against exactly those three, not against "coverage×conversion".

## 6. Verdict on step 1

**The port succeeds, but only after correction, and the corrected result changes the thesis.** The
question is no longer "what is the break-even cold prevalence for coverage allocation?" but:

> **Coverage was never the binding constraint. Conversion was. Therefore coverage-aware allocation
> cannot pay until rankability is fixed at the scoring stage — and the break-even rule π\*(k, K) says
> exactly which items are worth a pool slot at all.**

That claim is falsifiable (measure ρ(k) at matched coverage; if ρ is not near zero for their item-new
segment, it dies), it is grounded in someone else's published measurements across five domains, and it
predicts a negative result that has already been observed eight times.

**Next, in order:** (1) novelty search against the three unclaimed items in §5.5; (2) design the
matched-coverage measurement of ρ(k) that answers §5.1; only then (3) prereg.
