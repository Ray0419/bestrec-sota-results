# Merged cold-start agenda — reconciling the two 2026-08-05 sessions
### Written 2026-08-05 in worktree `claude/brave-rhodes-0a7d09`
### Inputs: `TIER_A_COLDSTART_RESEARCH_AGENDA_2026-08-05.md` + `POC_TEMPORAL_LC2C_V1.md` (main checkout, other session, untracked) · [POC_RESULTS_COLDSTART.md](POC_RESULTS_COLDSTART.md) + `_bestrec_run/poc_out/` (this worktree)
### Neither session's files were modified. This document is the reconciliation only.

---

## 0. Headline: the two agendas are the same discovery, and merging them produces a mechanism neither had

Two sessions independently converged on one phenomenon on the same day:

- **Theory session** proved *target-conditioned offset degeneracy*: adding a constant δ to every cold item's score leaves within-cold ordering exactly invariant while monotonically inflating cold-target full-catalog metrics and deflating warm-target ones. Their conclusion: **a cold-target metric gain is not evidence of cold learning.**
- **This session** measured the *exchange rate*: cold gain g, warm cost c, break-even prevalence p\* = |c|/(g+|c|), with **p\* ∝ √N_cold** (R² 0.98–1.00). Its conclusion: **cold rescue has a price, and the price scales.**

I ran the experiment that joins them (§2). The result: **their degeneracy is confirmed exactly, and ~95% of a content-based imputation's measured cold-start benefit is nuisance pool offset rather than learned cold relevance.** Both agendas were describing one underlying mechanism, which the third result — the suppression-axis bias — explains (§3).

**Verdict: merge into one paper. Do not run either agenda's GPU plan as written.**

---

## 1. Where the two agendas map onto each other

| quantity | theory session | this session | reconciliation |
|---|---|---|---|
| cold target mixture | π_t = P(Y_t ∈ C_t) | p_cold (observed cold prevalence) | **identical quantity**, different notation → adopt π_t |
| "deployment optimum depends on π_t" | qualitative claim | **p\* = \|c\|/(g+\|c\|)** | my law is the quantitative solution to their open statement |
| how the threshold behaves | not addressed | **p\* ∝ √N_cold** | new; makes their certification threshold a moving target |
| the nuisance intervention | constant offset δ (learns nothing) | not modelled | **their δ is the null model for my g** |
| genuine cold learning | assumed possible, not measured | text-kNN imputation | §2 measures how much is genuine: ~5% |
| why cold items fail | not addressed | suppression-axis bias (68% shared) | **explains why degeneracy exists at all** (§3) |
| statistical power | 604 events / 185 users (All_Beauty) — their own kill criterion flags this | 57k–95k users (MI/VG), 10 GPU runs | mine supplies power, theirs supplies protocol |
| temporal validity | global-time cutoffs, first-availability | leave-one-out, no time protocol | **theirs is correct; adopt it** |

**Non-overlap worth keeping from each:** their offset proposition, global-time mixed-target protocol, OCE/CVaR certification, and literature audit (30–50 papers, already partly done, with real citations to *Tunable Stochastic Gates*, FEASE, *Warmer for Less*, DiffCold, OCE-RCPS). Mine: the k-dial degree intervention, the √N scaling law, the bias/variance decomposition, and the offset-matched efficiency ratio (§2).

---

## 2. The reconciliation experiment (new, run 2026-08-05)

`_bestrec_run/poc_offset_decomp.py` → `results_KDIALCK_text_k0_MI_seed20260736.offset_decomp.json`.
Musical_Instruments, HSTU-style backbone, 3,121 cold items (12.69% of catalog), 11,662 cold targets, one frozen eval. Three metrics per variant: cold-target NDCG@10 over the **full catalog** (what benchmarks report), cold-target NDCG@10 ranked **within the cold pool only** (offset-invariant, so it isolates genuine learning), and warm-target NDCG@10.

**Arm A — pure score offset on the stock table (their intervention; learns nothing):**

| δ | cold FULL | cold WITHIN | warm FULL |
|---:|---:|---:|---:|
| 0 | 0.00000 | 0.02329 | 0.04362 |
| 2 | 0.00000 | 0.02329 | 0.04362 |
| 4 | 0.00000 | 0.02329 | 0.04362 |
| **8** | **0.02165** | **0.02329** | **0.01025** |

**Their proposition is confirmed exactly**: within-cold NDCG is invariant to five decimal places across every δ, while cold-target full-catalog NDCG rises from 0.00000 to 0.02165 — *without one bit of additional cold relevance* — and warm utility falls by 76%. The response is threshold-like rather than smooth because these rows are suppressed so far down that nothing enters the top-10 until δ≈8 (see §3).

**Arm B — text-kNN row imputation (this session's informative intervention):**

| δ | cold FULL | cold WITHIN | warm FULL |
|---:|---:|---:|---:|
| 0 | 0.01476 | 0.02402 | 0.03037 |
| 8 | 0.02402 | 0.02402 | 0.00000 |

**The decomposition:**

| quantity | value |
|---|---:|
| imputation cold gain, full catalog | **+0.01476** |
| imputation warm cost, full catalog | **−0.01326** |
| imputation **within-cold** gain (the only offset-invariant part) | **+0.00072** (0.02329 → 0.02402) |
| genuine share of measured benefit | **≈ 5%** |

So **~95% of what a content-based cold-start method appears to deliver is the nuisance pool offset their theorem predicts.** This is the strongest available support for their RQ1, and it comes from a different architecture, dataset, and protocol than their All_Beauty PoC — which answers their own kill criterion *"the effect exists only on the tiny All_Beauty overlap corpus."*

**But content is not worthless — and this is the nuance neither agenda had.** At matched cold gain, the two interventions differ in price:

| intervention | cold gain | warm cost | **warm cost per unit cold gain** |
|---|---:|---:|---:|
| pure offset (δ=8) | +0.02165 | −0.03337 | **1.54** |
| text-kNN imputation | +0.01476 | −0.01326 | **0.90** |

Imputation is **~1.7× more efficient** than the naive offset. That ratio — call it the **offset-matched efficiency ratio** — is the honest instrument the field lacks: it is exactly 1.0 for a method that only shifts the pool, and above 1.0 only to the extent the method learns real cold relevance. It converts "did this cold-start paper actually learn anything?" into a single measurable number.

---

## 3. The unifying mechanism (why both results are true at once)

This session's bias decomposition supplies the missing *why*:

1. Cold rows share a common **suppression direction** — 68% of a low-degree row's energy is seed-invariant, projecting +0.16 on a shared axis at k≤2 versus −0.22 at the head. Full-catalog softmax trains never-target rows only as negatives, so it pushes them all the same way (norms 0.32 vs 0.55 warm).
2. **A shared direction cancels in within-pool comparisons but not in cross-pool ones.** Hence within-cold ordering survives (stock within-cold NDCG 0.02329 — comparable to warm's 0.04362), while cross-pool ranking is destroyed (cold FULL = exactly 0.00000, ranks worse than random).
3. Therefore the *efficient repair is a pool offset*, which learns nothing — which is precisely why degeneracy is so easy to trigger, and why content methods that mostly re-shift the pool look so good.
4. And the cost of that offset scales as **√N_cold**, so the repair gets more expensive exactly as the cold catalog grows.

That is one coherent thesis with a theorem, a mechanism, a measured law, and a diagnostic instrument. Neither agenda had all four.

---

## 4. What each agenda should drop

**Drop from the theory agenda:**
- **RQ3 (CR-UOT moonshot)** — they self-rate it 0.25. This session independently killed its own moonshot (two-view BBP detectability) for the same reason. One merged paper should carry zero moonshots.
- **The claim that the repair baseline is the contribution.** Their own text already says the nested-logit prior "is not the main algorithmic novelty" — §2 confirms that instinct: the offset *is* the mechanism, so a prior-calibrated integrator is a packaging choice, not a finding.

**Drop from this session's agenda:**
- **RQ1 as posed (derived EB gate)** — refuted; ≤+0.0001, noise.
- **RQ3 as a fix** (heteroscedastic spectral denoising) — keep one paragraph as the bias explanation; no further GPU.
- **RQ4** (two-view BBP) — killed; the suppression-axis mechanism explains the same phenomena with less theoretical risk, and this repo has already retracted a BBP-based claim.

**Keep from both, merged:** their offset proposition + global-time protocol + OCE/CVaR certificate + literature audit; my k-dial intervention + √N law + bias decomposition + offset-matched efficiency ratio.

**Their RQ2 (representation-conditioned temporal dynamics / selective FIR) should stay a separate paper.** It is a genuinely different question and their design is sound. One finding from this session is directly useful to it: their spec already requires normalizing branch scores "so that r_j=0 for cold candidates does not turn an embedding-norm disadvantage into the apparent mechanism." §3 here is the empirical proof that this precaution is *necessary*, not hypothetical — the norm gap is 0.32 vs 0.55 and it drives cold NDCG to exactly zero. Cite it as the justification. Conversely, this session's k-dial result (text advantage is *caused by* collaborative degree and vanishes at k≤4) predicts their semantic-FIR branch will not rescue strict-cold items in an additively-fused architecture — worth pre-registering as a risk on their RQ2 gate.

---

## 5. Merged experimental plan (supersedes both)

Ordered; each step is gated on the previous.

| # | Step | Why it is first | Cost |
|---|---|---|---|
| 1 | ~~5-seed replication of the k-dial~~ | **DONE 2026-08-05 — PASSED.** anchor gap +0.00465 ± 0.00081, 5/5; dd vs k4 +0.00473 ± 0.00064, t=16.5, CI excludes 0. See §5b (incl. a correction to the interim claim). | spent |
| 2 | ~~Offset-decomposition sweep across seeds~~ | **DONE 2026-08-05 — PASSED.** genuine share 6.55% ± 2.22%; efficiency ratio 1.61 ± 0.07. Also surfaced the small-pool metric degeneracy. See §5c. | spent |
| 2b | **Pool-size-normalized offset-invariant metric** (within-cold NDCG@⌈αN⌉ or MRR/AUC), then re-run the N_cold sweep | New, forced by §5c: the current diagnostic cannot be compared across cold-pool sizes, which blocks the "does genuine share fall with N_cold?" question | ~1 GPU-h |
| 3 | **Adopt their global-time protocol** and re-run steps 1–2 under it (first-availability constraints, mixed warm/cold targets) | Their protocol is correct and mine is not temporally valid; my power fixes their n=185 problem | ~4 GPU-h |
| 4 | **Full dose-response** k ∈ {0,1,2,4,8,16} × 5 seeds | The paper's central figure | ~6 GPU-h |
| 5 | **Scaling law replication** on a second dataset, 3 rungs × 3 seeds | √N is currently 3 points, 1 seed, 1 dataset | ~4 GPU-h |
| 6 | **Intervention audit** (their step): add a constant offset to reproduced methods; measure inflation and order reversals, now reported as efficiency ratios | Converts the theorem into a field-wide claim | ~4 GPU-h |
| 7 | Certification wrapper (OCE/CVaR) with p\*(N) as the threshold | The applied payoff; only meaningful once 1–6 hold | modest |

**Do not start step 7, EB-NeRD, or the four-domain expansion before steps 1–3.** Both agendas currently plan breadth on top of single-seed foundations.

---

## 5b. Execution log — step 1 (5-seed k-dial replication)

Running as of 2026-08-05. Grid: 5 seeds × {text, id} × {anchor, k4, k0} = 30 MI runs, arms initialization-paired within seed, capped-item set identical across every run (`--item-cap-seed 7`). Driver `poc_kdial5_driver.py`; readout `poc_kdial5_analyze.py` → `kdial5_analysis.json`.

**COMPLETE — 5 of 5 seeds, all 30 runs (`kdial5_analysis.json`):**

| rung | text | ID | text−ID gap | t | 95% CI | signs |
|---|---:|---:|---:|---:|---|---|
| anchor | 0.04244 | 0.03778 | **+0.00465 ± 0.00081** | +12.9 | [+0.00350, +0.00580] **excludes 0** | **5/5** |
| cap k=4 | 0.00021 | 0.00028 | −0.00007 ± 0.00020 | −0.8 | [−0.00035, +0.00021] includes 0 | 1/5 |
| cap k=0 | 0.00000 | 0.00000 | 0.00000 | — | — | 0/5 |

Per-seed anchor gaps: +0.00468, +0.00430, +0.00409, +0.00416, +0.00604.

**The causal contrast (difference of gaps) is robust:** anchor − k4 = **+0.00473 ± 0.00064, t = +16.5, CI [+0.00382, +0.00564], 5/5 positive**; anchor − k0 = +0.00465 ± 0.00081, 5/5 positive. **Step 1 passes: the single-seed result replicates.**

**Correction to the interim readout.** At 2 and 3 seeds the k=4 gap looked *significantly negative* (0/3 positive, t = −4.2), and that was written up here as "text actively hurts at low degree." **It does not survive 5 seeds**: seed 20260740 came in at +0.00026, giving 1/5 positive and a CI spanning zero. The correct statement is the weaker one — **at k≤4 the text advantage is abolished, not reversed.** This is exactly the failure mode the 5-seed gate exists to catch, and it is why the load-bearing claim is the difference of gaps (t = 16.5) rather than the k=4 level.

**Control (uncapped targets) is not flat, and must be reported:** the text−ID gap on *uncapped* items *rises* from +0.00355 (anchor) to +0.00591 (k4) and +0.00515 (k0), 5/5 seeds. Removing capped items from training reallocates capacity to the rest. It does not touch the capped-item contrast, which is within-item and within-seed, but it forbids naive cross-rung comparison of absolute levels.

## 5c. Execution log — step 2 (offset-degeneracy decomposition across seeds)

`poc_decomp_sweep.py` → `decomp_sweep.json`. Eight decompositions.

| run | N_cold | genuine share | method cost/gain | offset cost/gain | **efficiency ratio** |
|---|---:|---:|---:|---:|---:|
| K5 seed 20260736 | 3,121 | 4.9% | 0.90 | 1.54 | 1.72 |
| K5 seed 20260737 | 3,121 | 6.4% | 1.00 | 1.58 | 1.57 |
| K5 seed 20260738 | 3,121 | 5.6% | 0.98 | 1.51 | 1.54 |
| K5 seed 20260739 | 3,121 | 10.4% | 1.06 | 1.68 | 1.59 |
| K5 seed 20260740 | 3,121 | 5.5% | 0.98 | 1.60 | 1.63 |
| **5-seed aggregate** | 3,121 | **6.55% ± 2.22%**, CI [3.4%, 9.7%] | | | **1.61 ± 0.07**, CI [1.51, 1.70] |
| cap 5% rung | 649 | 70.4% | 0.21 | 0.47 | 2.29 |
| VG natural cold | 85 | *658%* (degenerate — see below) | 0.07 | 0.07 | 1.04 |

**Step 2 passes on the headline.** At a large cold pool, **93.5% of a content-based imputation's measured cold benefit is the nuisance pool offset** (genuine share 6.55%, 95% CI [3.4%, 9.7%]), and the **offset-matched efficiency ratio is 1.61 ± 0.07** — remarkably stable across seeds (1.54–1.72). So content-based cold start is real but delivers ~1.6× the cold gain per unit of warm harm that a parameter-free offset delivers, not the order-of-magnitude the raw cold-target metric implies.

**New methodological finding — the within-cold metric degenerates on small cold pools.** The genuine share is not constant in N_cold: 6.6% at 3,121 cold items, 70% at 649, and a nonsensical 658% at 85. The last two are inflated by a metric artifact: within-cold NDCG@10 asks the target to rank in the top 10 of the cold pool, which is 0.3% of the pool at N=3,121 but 12% at N=85 — nearly free. **Any protocol that ranks cold targets only among cold items (e.g. the *Fairness among New Items* family the theory session cites) is degenerate at small cold-pool sizes**, and the offset-invariant diagnostic must be pool-size-normalized (within-cold NDCG@⌈αN⌉, or MRR/AUC) before it can be compared across datasets. This is a direct, unplanned contribution to the theory session's protocol design, and it means the N=649 and N=85 rows above are *not* evidence that genuine share falls with catalog size — that question needs the normalized metric before it can be asked.

## 5d. Scope test — does the mechanism survive a different negative-sampling regime?

The largest un-tested risk to the whole thesis was that cold-row suppression is an artifact of **full-catalog softmax**, where every cold item is a negative at every step. Most industrial two-tower retrieval trains with sampled or in-batch negatives instead, where a cold item is drawn only occasionally — so its row might simply stay near initialization (uninformative) rather than being driven somewhere systematic (corrupted). Same symptom, different disease, different cure, and a much narrower paper.

One run settles it (`poc_negatives_control.py`, MI, k0 cap, text arm, `--sampled-negs 1024` replacing chunked full softmax; overall test NDCG@10 0.03258 vs 0.03477, so the comparison model is healthy):

| training objective | cold ‖v‖ | warm ‖v‖ | ratio | **cold-row coherence** | warm coherence |
|---|---:|---:|---:|---:|---:|
| full-catalog softmax | 0.3688 | 0.4497 | 0.820 | **+0.603** | −0.061 |
| sampled negatives (1024) | 0.5010 | 0.4519 | **1.109** | **+0.935** | −0.116 |

**The mechanism is not an artifact of full-catalog softmax — it is stronger without it.** The *norm* signature reverses (under sampled negatives cold rows end up slightly **larger** than warm, not smaller), so "suppression by norm shrinkage" is the wrong description. The invariant is **directional collapse**: cold rows converge onto a single shared direction, with coherence rising from +0.603 to **+0.935** when negatives are sampled rather than exhaustive. Never being a positive is what matters; how often you are sampled as a negative only changes how tightly the rows collapse.

This materially widens the claim and simplifies it. The right statement is not "full-softmax suppresses cold rows" but **"items that are never positives collapse to a shared direction, and a shared direction is exactly what a pool offset corrects"** — which is why offset degeneracy exists, why it should generalize across negative-sampling regimes, and why content methods that mostly re-shift the pool look so effective. It also means §7's norm-based framing in [POC_RESULTS_COLDSTART.md](POC_RESULTS_COLDSTART.md) needs rewording to the directional form.

## 6. Honest status

- The §2 decomposition is **one seed, one dataset, one architecture**. It is the most important number in this document and it needs steps 1–2 before it is quotable.
- The 95%-nuisance figure is specific to text-kNN imputation on a suppressed table; other method families (retrieval-augmented, generative, meta-learned) may decompose differently. That is exactly what step 6 measures.
- Their PoC and mine agree in direction but differ in magnitude (their warm utility collapses to 0.0000 at a 0.25 prior; mine degrades smoothly), most likely because their base scorer is LC2C/EASE on 604 events and mine is a trained sequential model on 57k users. Reconciling that magnitude gap is a step-3 deliverable, not a discrepancy to paper over.
- A `PAUSE_EXPERIMENTS` sentinel from the theory session is live in this worktree root. It was left untouched; it blocks `run_sasrec_sbert_kdial.py` (trainer copy) until removed by its owner. §2 was eval-only and ran while the GPU was idle at 2%.
