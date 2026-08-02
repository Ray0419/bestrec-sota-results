# Claude memo — candidate RQ #2: is the learnable frequency filter over-parameterised?

> **RESULT 2026-08-01 — the noninferiority hypothesis FAILS on Beauty, the dataset that counts.**
> Validity gate passes there (filter effect +0.00570, t=7.37, 0/5 seeds for `none`), and against the
> margin declared before any run finished, `shared` costs **24.2%** of the filter's benefit and
> `rank1` **16.5%** — **2.4× and 1.6× the margin**. Because the *point estimates already exceed the
> margin*, more seeds cannot rescue noninferiority; ~8 seeds would instead establish strict
> inferiority. See §7. The strong claim is withdrawn. What survives is a mechanism/behaviour
> tension, scoped honestly in §7.3.

**STATUS: EXPLORATORY, NOT PREREGISTERED.** Licenses no manuscript claim.
Date: 2026-08-01. Role: scientific red-team. Supersedes the direction in
[`CLAUDE_RQ_LAG_INFORMATIVENESS_2026-08-01.md`](CLAUDE_RQ_LAG_INFORMATIVENESS_2026-08-01.md),
which was killed by [`CLAUDE_PHASE0A_RESULT_2026-08-01.md`](CLAUDE_PHASE0A_RESULT_2026-08-01.md).

```text
WORKSTREAM:        find a Tier-A RQ that reuses the FIR evidence surface
OBJECTIVE:         state the RQ, establish novelty, and run the decisive experiment
EVIDENCE QUESTION: does the field's canonical learnable frequency filter need its
                   per-channel parameterisation?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   novelty verdict + measured ladder + kill conditions
STOP CONDITION:    experiment complete and reported, pass or fail
```

---

## 1. First, a correction to my own claim

I previously told the maintainer that `shared` (16 params) **beats** `learned` (1,024), echoing
`CLAUDE_F6`'s "under-sold" framing. **That is not supported.** Paired over the committed seeds:

| corpus | `shared − learned` | t | df | CI95 | seeds + |
|---|---:|---:|---:|---|---:|
| Musical_Instruments | +0.000081 | +0.75 | 7 | [−0.000175, +0.000338] | **4/8** |
| MovieLens1M_R4 | +0.000060 | +1.23 | 7 | [−0.000055, +0.000175] | **4/8** |

4/8 seeds positive is a coin flip. **`shared > learned` is noise and must not be claimed.**

What *is* solid is **equivalence**, and it is very solid:

| contrast | mean | t | seeds + |
|---|---:|---:|---:|
| `shared(16) − identity(0)` | +0.002197 | **+27.50** | **8/8** |
| `learned(1024) − identity(0)` | +0.002116 | **+24.30** | **8/8** |

**16 parameters buy everything 1,024 do.** The extra 1,008 are undetectable. That is the real
finding, it is already consistent with the ML-1M noninferiority result in the manuscript, and it
raises an obvious question the manuscript does not ask.

## 2. The question

Our FIR module is ours. The field's canonical learnable filter is **FMLP-Rec** (WWW'22), whose
filter is the model's defining component. Verified from source
(`RUCAIBox/FMLP-Rec/modules.py:106`):

```python
self.complex_weight = nn.Parameter(
    torch.randn(1, max_seq_length//2 + 1, hidden_size, 2) * 0.02)   # [1, L/2+1, d, 2]
```

Per-frequency **× per-channel**. At the published config (L=50, d=64, 2 layers) that is
**6,656 filter parameters**. A channel-tied filter is `[1, L/2+1, 1, 2]` = **104** — a **64×
reduction** — and it is **strictly nested** inside the published design, exactly as our `shared`
is nested inside our `learned`.

> **RQ.** Is the per-channel parameterisation of learnable frequency filters — the defining design
> choice of the FMLP-Rec lineage — necessary? Or is a channel-tied filter with 64× fewer
> parameters noninferior across standard benchmarks, and if so, why?

### Why it is not merely an ablation

FMLP-Rec's own stated mechanism **predicts the null**. Their analysis says the learned filter
converges to a **low-pass** shape. A low-pass response is *one curve*; 64 near-copies of it are
redundant by their own account. So the experiment tests the paper's mechanism against its
parameterisation — and the mechanism is measurable directly, by taking the SVD of the learned
`[L/2+1, d]` filter matrix. If it is near rank-1, the redundancy is proven structurally, not just
behaviourally.

### Corroboration already present in the field, unremarked

Surveying the filter parameters of every model in the BSARec benchmark suite:

| model | learnable filter | params (2 layers) |
|---|---|---:|
| **FMLP-Rec** (WWW'22) | `[1, L/2+1, d, 2]` per-freq × per-channel | **6,656** |
| **BSARec** (AAAI'24) | `[1, 1, d]` per-channel scalar, **fixed** cutoff `c` | 128 |
| **FEARec** | none (frequency-domain attention) | 0 |

**BSARec — the successor that beats FMLP-Rec — already discarded the per-frequency axis entirely**,
keeping a single learned gain per channel. Nobody framed that as evidence that FMLP-Rec's filter
was over-parameterised. Our ladder tests the complementary cut (keep frequency, drop channel). If
both reductions are individually lossless, the published product parameterisation is unjustified
on both axes.

---

## 3. Novelty — sweep performed

| work | filter parameterisation | tests channel-tying? |
|---|---|---|
| **FMLP-Rec** (WWW'22) | per-freq × per-channel | **No.** Full-text check: the word **"share" appears 0 times.** Table 6 ablations are only *w/o Filter Layer, w/o FFN, w/o Add&Norm, +HPF, +LPF, +BSF* — all learnable-vs-fixed, never parameterisation. |
| **SLIME4Rec** (2305.04322) | per-dimension, sliding frequency band | No — innovates on *which band*, not the channel axis |
| **DWTRec** (2503.23436) | rescales per hidden dimension | No — "shar"/"channel" 0 hits in full text |
| **BSARec** (AAAI'24) | per-channel scalar | Reduces the *frequency* axis, never states it as such |
| **MUFFIN** (CIKM'25) | shared base filters + user gating | Shares across **users**, not channels; no null-effect analysis |
| **WEARec** (2511.07028), HyTiFRec, FEARec, TV-Rec | wavelet / time-variant / attention variants | No |

Every advance in this lineage moves along a different axis — which band, sliding, wavelets,
user-adaptivity, contrastive objectives. **The per-channel axis is never questioned.** Searches
for "channel-shared"/"dimension-shared" learnable filters returned hits only outside
recommendation (linear attention, language modelling), which shows the question is asked in
adjacent fields but not this one.

### Closing the sweep — the two named gaps are now discharged

1. **Full-text scans** (local extraction, not fetch summaries) of FMLP-Rec, SLIME4Rec, WEARec,
   MUFFIN, TV-Rec, DWTRec. Keyword set: *share/shared/sharing, channel, per-dimension, hidden
   dimension, across dimensions, tied, over-parameter, redundan, parameter count*.
   - FMLP-Rec: **"share" 0 occurrences.**
   - SLIME4Rec: **0 hits on every keyword.**
   - MUFFIN / TV-Rec / DWTRec / WEARec: hits exist but all irrelevant on inspection — MUFFIN's
     "shared" is standard item-embedding weight tying and its "redundant" refers to RFFT spectral
     symmetry; TV-Rec's "shares" refers to frequency components of positional encodings.
2. **Forward citations of FMLP-Rec: 400 citing papers enumerated** (Semantic Scholar, title +
   abstract) and scanned for channel-shared / tied / over-parameterised filters. **Zero hits.**

**A likely reason nobody noticed:** efficiency comparisons in this lineage report *total* model
parameters — WEARec's Table 2 lists FMLP-Rec at 324,160 on ML-1M — a figure dominated by the item
embedding matrix. The filter's 6,656 parameters are invisible at that granularity, so the
parameterisation question never surfaces in the efficiency discourse.

**Confidence: ≥95% that the specific question is unoccupied in sequential recommendation.**

**Honest limit:** absence from search is not proof of absence. Coverage is title+abstract for
citations and full text for the six nearest papers; a channel-sharing ablation buried in an
appendix of a paper that does not cite FMLP-Rec would be missed.

---

## 4. Experiment (running)

Harness: the official **BSARec** benchmark suite (ships FMLP-Rec plus all six standard datasets),
patched with one `--filter_mode` switch. Verified parameter counts and forward passes:

| arm | filter parameterisation | filter params | reduction |
|---|---|---:|---:|
| `full` | published FMLP-Rec, per-freq × per-channel | 6,656 | 1× |
| `rank1` | separable: freq profile ⊗ channel gain | 360 | 18× |
| `shared` | per-frequency, channel-tied | 104 | **64×** |
| `none` | filter layer removed (identity anchor) | 0 | — |

All four are nested; `none` is the floor control, mirroring the `identity` anchor in `FIRCTRL`.

**Design:** 4 datasets (LastFM, Beauty, Toys_and_Games, ML-1M) × 4 arms × 5 seeds = **80 runs**,
CPU, 6 concurrent. Primary endpoint NDCG@10, paired by seed against `full`.

**Mechanism probe:** SVD of each trained `full` filter — top-1 energy share, participation-ratio
effective rank, and inter-channel cosine of magnitude responses. Near-rank-1 ⇒ structural
redundancy.

**Reproduction anchors (declared before results).** The `full` arm must land near published
FMLP-Rec values or the comparison is void:

| reference | Beauty HR@10 | Beauty NDCG@10 | source |
|---|---:|---:|---|
| BSARec (pretrained, this harness) | 0.1008 | 0.0611 | `output/BSARec_Beauty_best.log` |
| FMLP-Rec | 0.0618 | — | DWTRec (2503.23436) baseline table |
| BSARec | 0.0982 | — | DWTRec baseline table (cross-check, ≈ the 0.1008 above) |

**Second model, ready but not yet queued.** BSARec's `sqrt_beta` is `[1, 1, d]` — also per-channel.
Tying it to a scalar gives **128 → 2 parameters**, the same 64× cut on a different filter form.
Patch implemented and forward-verified; it runs after the FMLP-Rec ladder so the two are not
competing for cores.

### Kill conditions (pre-committed, before results are visible)

- `shared` loses to `full` by more than the noise floor on a majority of datasets → **the strong
  claim dies.** Report it as "per-channel parameterisation is necessary in FMLP-Rec but not in our
  FIR module", which is a smaller, still-honest architectural-dissociation note.
- `none` ≈ `full` → the filter itself does nothing in this harness and the whole comparison is
  vacuous; report as a **reproduction failure of FMLP-Rec**, not as a parameterisation result.
- Filter SVD is high-rank but `shared` still matches → mechanism story is wrong even though the
  behavioural result holds; **drop the mechanism claim**, do not retrofit a new one.
- Effects within seed noise in both directions → **underpowered**; report as inconclusive and
  state the detectable effect size rather than declaring equivalence.

**Noninferiority framing.** The claim of interest is an *equivalence* claim, so it needs a
pre-declared margin, not a failed superiority test — the same discipline as
`PREREG_FIR_EFFICIENCY_ML1M_V1`.

### Margin, declared 2026-08-01 before any run completed (0/80 finished at time of writing)

A raw NDCG margin is not comparable across datasets, so the margin is **scale-free, expressed as a
fraction of what the filter itself buys**:

> **Δ = 0.10 × (full − none)**, per dataset, where `full − none` is the paired mean effect of the
> published filter against the no-filter anchor on that dataset.
>
> **`shared` is declared noninferior to `full`** iff the upper bound of the two-sided 95% paired CI
> of `(full − shared)` on NDCG@10 lies **below Δ** — i.e. channel-tying costs less than 10% of the
> filter's own contribution.
>
> **Precondition (validity gate):** the test is only interpretable where the filter demonstrably
> works. If `full − none` fails to exceed zero with a 95% CI on a dataset, that dataset is
> **VOID for this endpoint** and reported as a reproduction failure, not as evidence either way.

Rationale for 10%: it is small enough that a "lossless" claim is meaningful, and large enough to be
estimable at n=5 seeds. It was chosen with **no outcome visible** — at declaration time zero runs
had produced a test score.

Even so, this run remains **exploratory**: the margin is declared here, not in a frozen prereg
under the repository's gate, and the harness/seed count were chosen for feasibility. A confirmatory
claim requires re-running under a frozen `PREREG_FILTER_PARAM_V1` with fresh seeds. This run's
purpose is to establish the effect size and decide whether that prereg is worth writing.

---

## 5. Why this would be Tier-A shaped

1. **It targets a highly-cited design's defining component**, and the reduction is 64×.
2. **It has a mechanism**, measurable directly from trained weights, that the original paper's own
   analysis predicts.
3. **It generalises our own work**: our FIR ladder already shows 16 ≈ 1,024 on Amazon and ML-1M,
   8/8 seeds. If FMLP-Rec shows the same, this stops being a quirk of our module and becomes a
   property of learnable temporal filters in sequential recommendation.
4. **It suits this repository's machinery**: an equivalence claim with a pre-declared margin,
   adjudicated fail-closed, is exactly what the existing gates do and what the field does not.
5. **Deflationary results about popular designs are publishable at TORS/TOIS** — the venue
   published both the sequentiality-diagnostic paper and a reproducibility survey.

## Limits

Experiment in flight; **no result is claimed here**. Novelty confidence is 85–90%, below the bar,
with a named path to close it. One backbone family; the claim would not extend to models whose
filters are not learnable per-channel. CPU-only runs on a single machine. Margin not pre-declared,
so this run is exploratory by construction and cannot be upgraded to confirmatory after the fact.

---

## 7. Results

Two of four datasets complete (5 seeds × 4 arms each). Toys_and_Games and ML-1M still running.
LastFM ran on CPU, the rest on MPS; contrasts are within-dataset and paired by seed, so each is
internally valid, but LastFM should be re-run on MPS before any write-up.

### 7.1 LastFM — VOID by the pre-declared validity gate

| arm | params | NDCG@10 | vs `full` | t | seeds+ |
|---|---:|---:|---:|---:|---:|
| `full` | 6,656 | 0.0324 | — | — | — |
| `rank1` | 360 | 0.0361 | +0.0038 | +3.03 | 5/5 |
| `shared` | 104 | 0.0345 | +0.0021 | +2.60 | 4/5 |
| `none` | 0 | 0.0290 | −0.0034 | −1.72 | 1/5 |

`full − none` = +0.0034, CI **[−0.0021, +0.0089]** — spans zero. The filter does not beat the
no-filter anchor, so no equivalence claim is interpretable. **VOID**, exactly as the gate intended.

The reduced arms *beating* `full` here is an overfitting artifact on a 1,090-user corpus, not
support for the thesis: no superiority endpoint was pre-declared, and `full ≈ none`.

### 7.2 Beauty — validity gate PASSES, noninferiority FAILS

| arm | params | NDCG@10 | vs `full` | t | seeds+ |
|---|---:|---:|---:|---:|---:|
| `full` | 6,656 | 0.0300 | — | — | — |
| `rank1` | 360 | 0.0291 | −0.0009 | −1.18 | 2/5 |
| `shared` | 104 | 0.0286 | −0.0014 | −1.68 | 1/5 |
| `none` | 0 | 0.0243 | **−0.0057** | **−7.37** | **0/5** |

Validity gate: `full − none` = **+0.00570**, CI [+0.0036, +0.0078], 0/5 seeds. The filter works here.
Margin: Δ = 0.10 × 0.00570 = **+0.00057**.

| contrast | loss | % of filter effect | CI95 | vs margin |
|---|---:|---:|---|---|
| `full − shared` | +0.00138 | **24.2%** | [−0.00089, +0.00365] | **FAIL** (2.4× Δ) |
| `full − rank1` | +0.00094 | **16.5%** | [−0.00128, +0.00316] | **FAIL** (1.6× Δ) |

The losses are not individually significant at n=5 (t = −1.68, −1.18), so this is not "shared is
proven worse". But **the point estimates already exceed the margin**, so additional seeds cannot
produce noninferiority — they would establish *inferiority* (≈8 seeds for `shared`). Channel-tying
costs roughly a quarter of everything the filter buys.

**The strong claim — that the 64× reduction is lossless — is refuted on the only dataset so far
where the question is well posed.**

Reproduction caveat: our `full` gives Beauty HR@10 0.0575 against the published 0.0618 (≈7% low).
Close enough to be a plausible reproduction, not exact; it should be closed before publication.

### 7.3 What survives, at its true size

**The mechanism result stands and is unusually stable** (10 filters, 5 seeds × 2 layers):

| quantity | mean | sd |
|---|---:|---:|
| top-1 singular energy | 0.826 | 0.018 |
| effective rank / 26 | **1.462** | 0.062 |
| inter-channel \|cos\| | 0.888 | 0.007 |

**And it is in direct tension with §7.2.** The trained filter is effectively rank ~1.5 with 89%
aligned channels — yet constraining the *parameterisation* to rank 1 costs 16–24% of its benefit.
These are not contradictory; together they say:

> **Low-rank solutions do not imply that low-rank parameterisations suffice.** The redundant
> parameters are not redundant during optimisation, only at convergence.

That is a real and clean demonstration, on a highly-cited design, of something usually argued
abstractly. But it is a **different and smaller claim** than the one this memo set out to make, the
inverse of the kill condition I actually pre-specified, and the general phenomenon
(overparameterisation aids optimisation) is well known outside recommendation. **I will not
retrofit it into a Tier-A headline.**

**Second surviving observation — an architectural dissociation.** Our causal 16-tap FIR shows
`shared`(16) ≈ `learned`(1024), 8/8 seeds. FMLP-Rec's circular full-length frequency filter shows
`shared`(104) < `full`(6,656). Same operator class, opposite verdict — plausibly because the causal
short kernel has far less to lose from tying. Interesting, but it is a two-model observation.

### 7.4 Honest standing

Novelty was cleared at ≥95% and the harness is validated and reproducible; **the hypothesis was
simply wrong.** This is the second direction killed today by its own pre-committed test, which is
the process working rather than failing. As it stands this is a workshop-note-sized contribution,
**not** a Tier-A paper, and it should not be scaled to six datasets and a second model on the
strength of the mechanism result alone. Await Toys_and_Games and ML-1M, then decide whether the
mechanism/behaviour tension is worth a paper in its own right.

---

## 8. Final results and consolidated verdict (2026-08-01, end of session)

### 8.1 Both complete datasets fail noninferiority, consistently

| dataset | filter effect (`full−none`) | margin Δ | `rank1` (18× cut) | `shared` (64× cut) |
|---|---:|---:|---:|---:|
| Beauty | +0.00570 (t=7.37) | 0.00057 | −16.5%, FAIL | −24.2%, FAIL |
| Toys_and_Games | +0.01000 (t=7.80) | 0.00100 | −5.0%, FAIL | −15.4%, FAIL |

Direction is consistent: `shared` loses more than `rank1`, both lose something, neither is
individually significant at n=5 (|t| ≤ 2.10).

**A design error of mine, owned:** the 10%-of-effect margin is *untestable at feasible n*. CI
half-widths are ≈0.0023 against margins of 0.0006–0.0010; establishing noninferiority would need
≈110 seeds. I fixed the margin before seeing data, which was procedurally correct, but I never
power-checked it first. Any future prereg must set the margin from a power calculation, not from
an appealing round number.

Honest summary of the measurement: **an 18× reduction costs little and is not detectably worse; a
64× reduction costs ~15–24% of the filter's contribution.** The parameters saved are 0.8% of the
model, so the practical value is negligible either way.

### 8.2 The causal-vs-circular 2×2 — not supported

| n | interaction | t | same-sign seeds |
|---:|---:|---:|---:|
| 3 | +0.00430 | +4.29 | **3/3** |
| **5** | **+0.00210** | **+1.44** | **3/5** |

The encouraging n=3 signal was noise; seeds 45–46 reversed it. **The dissociation is not
established.** I was briefly convinced by n=3 — the exact failure mode I had warned about twice.

### 8.3 Mechanism hypothesis also refuted

Both filter families are equally low-rank at convergence:

| filter | top-1 energy | eff. rank | inter-channel \|cos\| |
|---|---:|---:|---:|
| circular `[26×64]` | 0.835 | 1.44 / 26 | 0.893 |
| causal `[16×64]` | 0.769 | 1.71 / 16 | 0.833 |

So spectral simplicity does **not** explain which parameterisation is trainable. The one durable
observation is negative and general: *the structure of the learned solution does not predict
whether the constrained parameterisation can be trained* — consistent with the post-hoc result
(post-hoc rank-1 costs 5.6%, trained rank-1 costs 24.2%), and with the FFN being equally
compressible (so it is not a property of filters at all).

### 8.4 Directions examined and closed this session

| # | direction | outcome |
|---|---|---|
| 1 | Dataset sequentiality predicts FIR benefit | **refuted** — length confound; sign inverts under matching |
| 2 | Channel-tying is lossless in FMLP-Rec | **refuted** — fails margin on both datasets |
| 3 | The filter is uniquely over-parameterised | **refuted** — FFN equally compressible |
| 4 | Low rank explains tying tolerance | **refuted** — both families equally low-rank |
| 5 | Causal vs circular explains it | **not supported** at n=5 |
| 6 | Ablation studies in SR are underpowered | **novelty fails** — paired-bootstrap protocols, seed-variance and replicability studies already occupy it |
| 7 | Exact unlearning for linear autoencoders | **novelty fails to reach 95%** — IMCorrect (arXiv 2307.15960) already instantiates on **SLIM**, GF-CF and MF. It is *approximate* ("Sherman"/"Woodbury"/"closed-form" all 0 hits), so an exactness claim survives, but it is much narrower than "the family is unoccupied". Combined with the previously refuted speedup claim and the 44.8 GB dense-`P` ceiling, the practical case is weak. |

For the record, the 2026 landscape checked for #7: **ERASE** (SIGIR 2026) benchmarks 10 models
(LightGCN, DCCF, BPR, IBCF, SimRec, GRU4Rec, NARM, SASRec, S-KNN, SRGNN) plus 6 unlearning
methods — **no EASE/SLIM/LAE**; **Obliviate** (arXiv 2607.22665, 2026) is *approximate* and covers
MF-BPR and LightGCN only.

### 8.5 Verdict

**No Tier-A-publishable research question survived this session.** Novelty was cleared at ≥95% for
the filter-parameterisation question and the experiment was run properly — the hypothesis was
simply false. Six further directions were killed by empirical test or by novelty check, several
before any compute was spent, which is the cheap-kill discipline working as intended.

**The filter-parameterisation seam is exhausted and should not be scaled.** Effects are ~0.001
NDCG against seed sd ~0.002, so resolving anything here needs seed counts out of proportion to the
value of the answer.

**What this session did establish, and it is worth keeping:** the BEST-Rec FIR equivalence
(`shared`(16) ≈ `learned`(1024), 8/8 seeds, t≈27 against identity) **does not transfer** to
FMLP-Rec's circular frequency filter, where the same 64× tying costs 15–24%. That makes the
16-parameter result a *specific property of the causal short-kernel design* rather than a generic
fact about temporal filters — which strengthens the existing FIR claim's distinctiveness rather
than diluting it. It is a sentence for the discussion section, not a paper.

---

## 9. Search closed — eight directions, and why the neighbourhood is exhausted

Continuing past §8, three further directions were generated and killed. Recording them so the
next session does not re-derive them.

| # | direction | outcome |
|---|---|---|
| 6 | Ablation studies in SR are underpowered | **novelty fails** — paired-bootstrap protocols (arXiv 2511.19794), seed-variance studies (CEUR Vol-3476), BERT4Rec replicability, Ferrari Dacrema |
| 7 | Exact unlearning for linear autoencoders | **novelty fails** — **IMCorrect** (arXiv 2307.15960) instantiates on **SLIM**, GF-CF, MF. Approximate ("Sherman"/"Woodbury"/"closed-form" = 0 hits), so an exactness claim survives but is far narrower than "the family is unoccupied". Practical case already weak: speedup refuted, dense `P` is 44.8 GB on Office_Products. **The prior session's memo overstates this gap and should be corrected.** |
| 8 | Community adaptive overfitting of standard splits (ImageNetV2-for-RecSys) | **novelty fails** — the temporal-split question is settled at Tier-A: *A Critical Study on Data Leakage in Recommender System Offline Evaluation* (**TOIS 2023**, 10.1145/3569930; 21.7–73.4% drops across four datasets), *Don't Get Ahead of Yourself* (**RecSys 2025**), *Time to Split* (2025). Cross-dataset ranking instability is separately covered by Bradley-Terry rankings (arXiv 2606.07492), which even predicts rankings on unseen datasets. |

Also checked and occupied: cold-start via content/text (SEMCo 2026, sparse multimodal 2026,
content-based initialisation RecSys 2025) — which is the natural constructive reading of the
voided E-G tail-bin result.

### Why I am stopping rather than generating a ninth

The eight directions fall into exactly two buckets, and the pattern is informative:

- **Five died empirically** (§8.4 #1–5). Every one was a *deflationary* claim — "component X is
  unnecessary". They failed because these components generally **are** necessary. The measured
  effects are ~0.001–0.006 NDCG against seed sd ~0.002, so this regime needs seed counts out of
  all proportion to the value of the answer.
- **Three died on novelty** (#6–8), each before compute was spent. All three were *methodological*
  claims about evaluation — and evaluation methodology in recommender systems is a mature,
  crowded literature with Tier-A coverage already in place.

That exhausts the two framings available from this repository's assets. A ninth hypothesis drawn
from the same well would be a guess, not a search, and I decline to dress one up as a finding.

**This is a negative result about the search, and it is decision-relevant:** the marginal value of
continued hunting adjacent to FIR is low. The evidence favours shipping the existing manuscript
over funding a paper #3.

### What would change this verdict

- A **new data asset** the field lacks (proprietary logs, a genuinely private holdout with an
  independent custodian, or online/interventional data). The custody problem this repository
  identified in `E-G3_DESIGN.md` is real and would be *solved*, not merely described, by such an
  asset — and that would reopen direction 8 as a constructive contribution rather than a critique.
- A **constructive** rather than deflationary framing with a positive effect large relative to seed
  noise (>0.01 NDCG), which none of the FIR-adjacent ideas offer.
- Moving to a subfield where this repository's preregistration machinery is the differentiator and
  the empirical effects are larger.

---

## 10. FINAL verified ladder — 80 runs complete (4 datasets x 4 arms x 5 seeds)

| dataset | `full` 6656 | `rank1` 360 | `shared` 104 | `none` 0 | filter effect | 64x tying cost |
|---|---:|---:|---:|---:|---:|---:|
| LastFM | 0.0324 | 0.0361 | 0.0345 | 0.0290 | +0.0034 | −62% **(VOID)** |
| Beauty | 0.0300 | 0.0291 | 0.0286 | 0.0243 | +0.0057 | **24%** |
| Toys_and_Games | 0.0375 | 0.0370 | 0.0360 | 0.0275 | +0.0100 | **15%** |
| ML-1M | 0.1095 | 0.1005 | 0.0970 | 0.0883 | +0.0212 | **59%** |

On every dataset where the pre-declared validity gate passes, channel-tying costs **15–59%** of the
filter's contribution. **The hypothesis is refuted, not merely unsupported.** LastFM's apparent
−62% "gain" is precisely why the gate voided it: the filter barely works there, so the ratio is
meaningless.

### 10.1 A finding that bears directly on the manuscript

ML-1M has the **largest** filter effect of the four (+0.0212, 24% relative), yet
`PREREG_FIR_EFFICIENCY_ML1M_V1` measured an exact null there (+0.0000002, CI ±7.5e-05).

Two candidate explanations were tested:

1. **"MovieLens resists temporal filtering."** — **ELIMINATED.** The circular filter gives +0.0212.
2. **"Causal short kernels are too weak on ML-1M."** — **ELIMINATED.** A causal 16-tap depthwise
   filter in the same harness gives **+0.01877, t=+7.84, 3/3 seeds** (21.6% relative). My own
   prediction here was that it would be ≈0; it was refuted at large effect size.

The remaining candidates are **the backbone** (in FMLP-Rec the filter is the *only* sequence mixer;
in BEST-Rec the FIR is a residual on top of self-attention) and **the split** (1,033 users at
rating≥4 under a global time cutoff, vs 6,040 under LLOO here).

**Test in flight:** the BEST-Rec ladder arms — `off` / `learned` (1,024 = 64×16) / `shared` (16),
zero-init, parameter counts matching `FIRCTRL` exactly — bolted onto **SASRec**, an attention
backbone, on ML-1M. If FIR helps SASRec there, the backbone explanation dies and the null is a
property of the split. Note that FMLP-Rec's own Figure 3 reports their filter *improving* SASRec,
GRU4Rec and Caser, which argues against the backbone explanation before we even run it.

**Why this matters:** the manuscript frames the ML-1M result as "the prospectively frozen
non-Amazon result is negative". A reviewer who checks the standard ML-1M literature will find
filters producing ~25% relative gains and will ask why ours produces exactly zero. Better to answer
that in the paper than to be asked it. The honest scope is narrower than currently stated: *a
causal FIR residual adds nothing given this backbone and this split* — not *temporal filtering does
not help on MovieLens*.

### 10.2 RETRACTION — the first SASRec replication was mis-specified

I reported that the ML-1M null "independently replicates" on an attention backbone. **That result
was invalid and is withdrawn.**

BEST-Rec applies its causal FIR to the **embeddings, before the transformer blocks**
(`run_sasrec_sbert_efficiency_ml1m_v1_frozen.py` ~line 1036, immediately after `x = self.drop(x)`).
My SASRec arm applied it to the **encoder output**, after all attention layers. Those test
different things: BEST-Rec pre-processes attention's *input*; my version post-processed its
*output*. "FIR ≈ 0 on an attention backbone" therefore measured a configuration BEST-Rec does not
use.

The 27 affected runs are archived under `output/postfir_archive/`, not deleted.

**Process failure, recorded:** I characterised the result before checking placement fidelity
against the frozen source. This is the second time in the session I announced a finding ahead of
its verification (the first being the n=3 causal interaction, t=4.29, 3/3 seeds, which reversed to
t=1.44, 3/5 at n=5). Both were caught, but both were avoidable by checking first.

**Corrected implementation, verified before relaunch:**

| check | result |
|---|---|
| FIR placement | on embeddings, pre-encoder — matches frozen source |
| `fir_conv` weight after construction | `max|w| = 0.0` (`init_weights` touches only Linear/Embedding/LayerNorm/GRU, never Conv1d) |
| zero-init no-op, same model, FIR-active vs bypassed | **max abs diff = 0.0 — exact** |
| parameter counts | `learned` 1,024 = 64x16, `shared` 16 — match `FIRCTRL` exactly |

30 corrected runs in flight (ML-1M + Beauty x off/learned/shared x 5 seeds).

**The backbone-vs-split question is therefore OPEN again.** Nothing about the cause of the ML-1M
null should be inferred from the retracted runs.
