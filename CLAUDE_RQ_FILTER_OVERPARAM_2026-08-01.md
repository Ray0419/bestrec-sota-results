# Claude memo — candidate RQ #2: is the learnable frequency filter over-parameterised?

**STATUS: EXPLORATORY, NOT PREREGISTERED. EXPERIMENT IN FLIGHT.** Licenses no manuscript claim.
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
