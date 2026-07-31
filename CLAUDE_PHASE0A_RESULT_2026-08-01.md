# Claude Phase 0a — the dissociation is REFUTED by my own kill condition

**STATUS: EXPLORATORY, POST-HOC, NOT PREREGISTERED.** Licenses no manuscript claim.
Date: 2026-08-01. Role: scientific red-team.

**Verdict: the §1 headline of [`CLAUDE_RQ_LAG_INFORMATIVENESS_2026-08-01.md`](CLAUDE_RQ_LAG_INFORMATIVENESS_2026-08-01.md)
does not survive. The pre-committed kill condition fires.** The strong form of the research
question is withdrawn. A much weaker form survives and is scoped in §5 below.

All work was scratchpad-only. Record-level artifacts stayed under the gitignored private root.
No repo artifact was modified other than this memo and a status line in the RQ memo.

---

## 1. What was tested

The RQ memo's anchoring claim compared **their ML-20m** shuffle numbers to **our ML-1M (r≥4)**
FIR effect. I flagged that as the weakest link and pre-committed:

> **0a fails** → dissociation is an artifact of comparing ML-20m to ML-1M. **Abandon.**

Phase 0a recomputes the diagnostic on our exact splits.

### Provenance (both verified, not assumed)

| artifact | check | result |
|---|---|---|
| ML-1M (r≥4) split | rebuilt via the frozen `acquire_movielens_fir_efficiency_v1.py` | train sha256 `a1e08583…f6128` — **bit-identical** to `fir_efficiency_ml1m_v1_adjudication.json:673` |
| ML-1M source zip | official MD5 | `c4d9eecf…0906` matches |
| Industrial_and_Scientific 5-core | sha256 vs `provenance_Industrial_and_Scientific.json` | `37dc32e7…9060` — **exact match** |
| Musical_Instruments, CDs_and_Vinyl 5-core | same McAuley Lab benchmark endpoint | downloaded, hashes recorded |

So this is measured on the same bytes the FIR campaigns consumed, not on a re-derivation.

Metric: the **training-free** half of the TORS diagnostic (Klimashevskaia et al. 2025) — count
n-grams surviving a support threshold, before vs after shuffling each user's sequence. Their
reading: relative change **above −90% ⇒ weak** sequential structure.

---

## 2. Native splits — the dissociation appears to reproduce

Sequences exactly as each campaign consumed them.

| corpus | mean len | 2-gram sup≥2 | 3-gram sup≥2 | FIR effect |
|---|---:|---:|---:|---:|
| **MovieLens1M_R4** | **130.8** | −43.08% | **−98.77%** | **+0.0000002** |
| Industrial_and_Scientific | 6.1 | −44.80% | −94.42% | +0.002110 |
| CDs_and_Vinyl | 10.5 | −59.65% | −91.96% | +0.006150 |
| Musical_Instruments | 6.9 | −31.12% | −86.60% | +0.002116 |

Read naively this is exactly the claimed dissociation: ML-1M is the **most** sequential corpus
(−98.77%, deepest in their "strong" tier) and has an **exactly null** FIR effect, while
Musical_Instruments is the **least** sequential (−86.60%, the only one failing their −90% strong
threshold) and shows a large positive effect. Spearman(sequentiality strength, FIR effect) = **−0.80**.

**This is the number that would have gone in the paper. It is an artifact.**

---

## 3. The confound: the metric tracks sequence length

ML-1M sequences are **131 items**; Amazon 5-core sequences are **6–10**. n-gram survival under
shuffling is mechanically length-dependent — a longer sequence has more n-grams, drawn from a
combinatorially larger space, so repeated n-grams are rarer by chance after shuffling and the
destruction rate rises regardless of any real sequential structure.

Controlling it requires matching **both** length and corpus size (support-thresholded counts scale
with corpus size too). Matched design: **1,000 users × last 10 items** per corpus — the ceiling
ML-1M allows — over **20 independent user draws**, 3 shuffles each.

| corpus | matched 2-gram sup≥2 | 95% CI | FIR effect |
|---|---:|---|---:|
| **MovieLens1M_R4** | **−56.70%** | [−57.82, −55.58] | +0.0000002 |
| Industrial_and_Scientific | −59.63% | [−64.39, −54.87] | +0.002110 |
| Musical_Instruments | −59.66% | [−65.30, −54.02] | +0.002116 |
| CDs_and_Vinyl | **−68.81%** | [−74.95, −62.67] | +0.006150 |

**The ordering inverts.** Matched, ML-1M is the **least** sequential of the four, not the most.
Its native −98.77% was largely its 131-item sequences, not its structure.

And the rank correlation flips sign and goes to the ceiling:

| | Spearman | Kendall |
|---|---:|---:|
| native 3-gram | −0.80 | — |
| **matched 2-gram** | **+1.000** | **+1.000** |
| matched 3-gram | +0.800 | +1.000 |

Under the correct controls, sequentiality **positively** and monotonically tracks the FIR
effect — the ordinary hypothesis, not a dissociation. My §2 mechanistic story ("high
order-dependence, low lag-informativeness") predicted the opposite and is **not supported**.

*(Matched 3-gram is degenerate here — all three Amazon corpora saturate at −100% and only 2–7 of
20 draws yield a non-empty base. It is reported for completeness and should not be leaned on.)*

---

## 4. What the matched numbers do *not* establish

Perfect rank correlation on **n=4** with large draw-noise is far weaker than it looks. Welch
contrasts against ML-1M:

| contrast | diff | se | t | verdict |
|---|---:|---:|---:|---|
| ML-1M − Musical_Instruments | +2.96 | 2.94 | +1.01 | **not distinguishable** |
| ML-1M − Industrial_and_Scientific | +2.93 | 2.50 | +1.17 | **not distinguishable** |
| ML-1M − CDs_and_Vinyl | +12.11 | 3.18 | +3.81 | distinguishable |

So the +1.000 Spearman rests on two rank orderings that are pure noise. Only the CDs contrast is
real. The honest statement is: **CDs_and_Vinyl is measurably more sequential than ML-1M and has
the largest FIR effect; MI and IS are indistinguishable from ML-1M on this diagnostic.**

---

## 5. What survives, stated at its true (much smaller) size

**Refuted and withdrawn:**
- "The dataset the field calls most sequential is where the temporal module provably does nothing."
  ML-1M is not the most sequential under controls.
- The negative/anti-predictive relationship (§1 of the RQ memo).
- The "order-dependence vs lag-informativeness" mechanism as motivated (§2 of the RQ memo). It may
  still be a real distinction, but the evidence I offered for it was the artifact.

**Survives, weakly — a resolution claim, not a dissociation claim:**
> The matched diagnostic cannot distinguish Musical_Instruments or Industrial_and_Scientific from
> MovieLens-1M (t = 1.01, 1.17), yet the FIR effect differs decisively between them — **+0.0021 with
> a tight CI versus a null whose CI excludes ±7.5e-05**. Where the diagnostic has no resolution, the
> module effect has plenty.

That is *insufficiency*, not *anti-prediction*, and it is a materially smaller contribution. On
n=4 it is an observation, not a finding. It would need Phase 1 breadth (N≥12) even to be stated.

**Survives, and is independently solid — a methodological note:**
> The TORS n-gram sequentiality metric is strongly confounded by sequence length. ML-1M reads
> −98.77% native and −95.77%/−56.70% matched. The published analysis compares 15 datasets whose
> mean sequence lengths differ by more than an order of magnitude without matching on length or
> corpus size.

This is real, cheap, and reproducible — but it is a short note or a reproducibility-track
contribution, **not a Tier-A paper**, and it critiques others' work rather than advancing ours.

---

## 6. Recommendation

**Do not preregister the RQ as written.** The kill condition fired; honouring it is the point of
having written it down first.

On whether to run the **model-based** half of the diagnostic (SASRec/GRU4Rec NDCG@10 degradation
and Jaccard@10): that is the metric §1 actually quoted, so there is a fair-test argument for it.
But the training-free metric has already answered under the correct controls, and the model-based
metric is confounded by length in the *same direction* — SASRec on a 131-item history loses far
more to shuffling than on a 6-item one, mechanically. Running metric after metric until one agrees
with the hypothesis is precisely the metric-mining this repository's discipline forbids, and I
would be doing it with the outcome already visible. **If it is run, it should be pre-declared
first, with the matched design fixed in advance and the ML-1M-vs-MI/IS contrast named as the
primary endpoint.** I do not expect it to rescue the strong form.

The decomposition question in `CLAUDE_DECOMPOSITION_CAVEATS_2026-08-01.md` is unaffected by this
result and reverts to being the strongest available direction.

## Limits

Training-free metric only; the model-based half was not run. n=4 corpora. One matched design
(1,000 × 10) — the ML-1M user count caps the match and a different ceiling could shift the
ordering. Amazon LLOO histories vs ML-1M's global time-cutoff split is an uncontrolled protocol
difference between the two families. Three of the four FIR effects are outcome-known. Nothing here
licenses a manuscript claim.

**Correction to my own prior framing, recorded explicitly:** I told the maintainer the dissociation
was the anchoring observation and that Phase 0a was cheap insurance. Phase 0a refuted it, and the
sign of the relationship is the opposite of what I predicted. The §1 table was correct as
arithmetic and wrong as evidence.
