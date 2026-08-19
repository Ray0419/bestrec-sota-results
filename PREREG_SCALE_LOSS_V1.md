# PREREG: Does the tail benefit of model scaling survive the loss calibration that scaling requires? (SCALE×LOSS V1)

**Frozen 2026-08-17, before any run on the scale ladder.** No endpoint on any new cell has been
inspected. The single anchor rung (d_model=64) already exists from S6.6/S6.6.1 and its numbers are
reproduced in §3 — they are the *motivation*, and they are explicitly **not** reused as ladder data
(see §4.3, protocol change).

---

## 1. The contradiction this resolves

Two literatures disagree, and each holds fixed exactly the axis the other varies.

| Work | Varies | Holds fixed | Finds |
|---|---|---|---|
| Zhang et al., *Scaling Law of Large Sequential Recommendation Models*, RecSys 2024 ([arXiv:2311.11351](https://arxiv.org/abs/2311.11351)) | model scale × popularity group | one loss | large−small gap **grows** as popularity falls → **tail benefits more from scale** |
| *Ghost* / long-tail generative rec ([arXiv:2605.16825](https://arxiv.org/html/2605.16825v3)) | LLM backbone 0.6B→4B | loss | tail retrieval 7,344 → 9,688 → **scale helps tail** |
| *Cold-Starts in Generative Recommendation: A Reproducibility Study*, SIGIR'26 ([arXiv:2603.29845](https://arxiv.org/abs/2603.29845)) | model scale (t5-small→xl) × cold-start protocol | loss | item-cold improves **monotonically with scale** |
| Ferrari et al., *Evaluating Performance and Bias of Negative Sampling…* ([arXiv:2410.17276](https://arxiv.org/abs/2410.17276)) | negative-sampling **strategy** × popularity band | **model scale** | aggregate metrics **hide** head/mid/tail imbalance; random negatives favour head |
| *Scaling Laws for Behavioral Foundation Models over User Event Sequences* ([arXiv:2606.05257](https://arxiv.org/html/2606.05257)) | compute 10¹⁵–10¹⁹, negative count K∈{0…2M}, batch | **no popularity slicing**, no calibration exponent, no full-softmax control | val-loss↔recall@10 Spearman **flips sign** with compute (+0.93 at 10¹⁵ → −1.00 at 10¹⁸) |
| **Ours, S6.6.1 (this program)** | loss calibration exponent β, with full-CE **and** sampled-CE controls × degree bands | **model scale** | β costs the tail **−85%** (k11-20) while the head **gains +28%**, under a **−7.9% aggregate** dip |

So: *scale helps the tail* and *β starves the tail* are both established, **at different points on the
other's axis, and never crossed.** The crossing matters because β-style overconfidence corrections and
sampled objectives are not optional at scale — full softmax over a large catalogue is what scaling
makes infeasible. If the interaction is negative, the published tail-scaling promise was measured in a
regime that production scaling cannot occupy.

## 2. Novelty position (searched 2026-08-17)

Unoccupied cell: **(model scale) × (loss calibration exponent, with a full-CE control) × (degree-sliced
endpoint)**. No paper found crosses all three. Explicitly **not claimed as ours**, and cited as prior art:

- "aggregate metrics hide popularity-band imbalance" → **arXiv:2410.17276**. Ours is not this claim; ours
  is the *scale-dependence* of the hiding.
- "popularity-sliced scaling analysis" → **arXiv:2311.11351**. Ours is not this; ours is its
  loss-conditionality.
- "sampled loss is an unreliable proxy for full-catalogue ranking" → **arXiv:2606.05257**. Ours is not
  this; ours asks whether the unreliability is *degree-structured*.
- gBCE itself → **gSASRec, Petrov & Macdonald, RecSys 2023 / IJCAI 2024** ([arXiv:2308.07192](https://arxiv.org/abs/2308.07192)), credited, reimplemented. Their claim is gBCE > **sampled BCE (β=1)**, which we do not test. Ours is vs full-CE and sampled-CE — a different and stronger baseline, so **nothing here refutes their result**, and their head gain is genuine.

## 3. Anchor rung (existing, d_model=64, MI, temporal, n=3, `*.degree_eval.json`)

| target degree | full-CE | sampled-CE | gBCE | gBCE/fCE |
|---|---|---|---|---|
| k1–2   | 0.000271 | 0.000368 | 0.000087 | 0.32 |
| k3–5   | 0.000937 | 0.001607 | 0.000160 | 0.17 |
| k6–10  | 0.002218 | 0.002078 | 0.000507 | 0.23 |
| k11–20 | 0.007731 | 0.007665 | 0.001124 | **0.15** |
| k21–50 | 0.018899 | 0.017260 | 0.007013 | 0.37 |
| k51–200| 0.033033 | 0.033441 | 0.030580 | 0.93 |
| k>200  | 0.092354 | 0.087620 | 0.117907 | **1.28** |
| warm (aggregate) | 0.019505 | 0.018927 | 0.017960 | 0.92 |

Aggregate-blindness amplification at this rung: |Δ%(k11–20)| / |Δ%(warm)| = 85.5 / 7.9 ≈ **10.8×**.
k=0 is exactly 0.00000 in every arm (established across 2 loss families × 5 training arms) and is
therefore **excluded from all bands below as degenerate**, not counted as tail damage.

## 4. Design

### 4.1 Axes
- **Loss (3 arms, all already implemented and validated):**
  - `fCE`  = `--chunked-full-softmax --item-chunk 32768`
  - `sCE`  = `--sampled-negs 256`               (CE form, 256 negatives)
  - `gBCE` = `--gbce-t 0.75 --gbce-negs 256`    (β = α(t(1−1/α)+1/α), α = K/(n_items−1))
- **Scale ladder (4 rungs):** `--d-model ∈ {32, 64, 128, 256}`, with `--n-layers 4 --n-heads 2` fixed.
- **Seeds:** 20260736–38 (stage 1), extended to 20260739–40 at stage 2.
- Dataset: `Musical_Instruments`, `--temporal-split`, inner/outer q = 0.60/0.75. Everything not listed
  is copied **verbatim** from `poc_loss_driver.py` BASE.

**β does not drift across the ladder.** α = K/(n_items−1) depends only on the catalogue, which is fixed,
so β = 0.2578 at every rung. The loss is *literally identical* across rungs — the interaction cannot be
contaminated by a moving calibration target.

### 4.2 Cells
Stage 1: 3 losses × 4 rungs × 3 seeds = **36 runs** + 36 degree-sliced evals.
Stage 2 (gated, §6): + seeds 39–40 across all 12 cells = **24 runs** → n=5.
R1 robustness (gated): at d=256, `fCE` and `gBCE` at `--lr 5e-4`, 3 seeds = **6 runs**.
External replication (gated): Steam, 3 losses × d∈{64,256} × 3 seeds = **18 runs**.

### 4.3 Declared protocol change, applied identically to every cell
`--eval-every 5` (not 20 as in `poc_loss_driver.py`), so best-checkpoint-on-validation selection is
meaningful. **Reason:** with `--eval-every 20` the selected checkpoint is effectively the last epoch, and
larger rungs could then be measured while overfitted — which would make the estimand
*overfitting × loss*, not *capacity × loss*. This is fatal to an interaction claim, so the ladder is run
fresh at all four rungs, including d=64. The 9 existing `--eval-every 20` runs at d=64 are retained as a
**protocol-consistency check** (does eval-every move the d=64 contrast?), never merged into ladder data.

### 4.4 Known limitations, stated now rather than discovered by a reviewer
- **d_model scales the item table (24,587 × d) *and* the sequence model together.** This is the standard
  recsys scaling knob and the one arXiv:2311.11351 varied, and its own mechanism claim is memorisation
  capacity — so table growth is part of the construct, not a nuisance. Localisation is still pre-registered
  as exploratory (§5.4, depth-only ladder).
- **Fixed LR, no MuP.** Precedent: arXiv:2606.05257 explicitly retains default initialisation and reports
  no working MuP transfer. R1 is the sensitivity check; "the big rung was mistuned" is the single most
  likely reviewer attack and R1 exists to answer it.
- **Single dataset at stage 1.** A one-dataset interaction claim is not publishable on its own; Steam is
  pre-registered as external replication rather than offered post hoc.
- Ladder spans ~10⁵–10⁶ parameters, far below arXiv:2606.05257's 10¹⁵–10¹⁹ FLOPs. We claim an
  interaction *within our ladder*, and pre-commit to reporting it as a small-scale ladder result.

## 5. Endpoints, estimands, and decision rules

Bands, pre-specified, event-count weighted, from `by_degree` in `*.degree_eval.json`:
**TAIL = k1–50** (pooled k1-2, k3-5, k6-10, k11-20, k21-50), **HEAD = k>200**, **AGG = warm**.
All 7 non-degenerate buckets are additionally reported per-rung as secondary.

For loss ℓ and band b, let `S_ℓ(b)` = OLS slope of NDCG@10 on log₂(d_model) over the 4 rungs, fitted
**per seed** → 3 (later 5) slope estimates per cell. Paired-by-seed t-tests, two-sided, α = 0.05,
**Holm-corrected across H2/H3/H4**. H1 is a gate, not a claim, and is not in the correction family.

- **H1 (replication gate).** `S_fCE(TAIL) > S_fCE(HEAD)` after normalising each band by its own d=32
  level (relative slope), i.e. under full-CE the tail benefits more from scale — arXiv:2311.11351's
  direction. *If H1 fails*, we have failed to replicate the premise in our regime; the paper is rewritten
  as that failed replication and H2 is reported as descriptive only. Reported either way.
- **H2 (PRIMARY — the interaction).** `S_gBCE(TAIL) − S_fCE(TAIL) < 0`, paired by seed.
  **Pre-registered predicted sign: negative.** Reasoning: β = 0.2578 penalises missing a positive ~4×
  less, so upward pressure on rarely-positive items is weak *independently of capacity*, while added
  capacity is preferentially spent on items that do receive positive gradient (the head). Capacity cannot
  supply a gradient that the objective never emits.
- **H3 (attribution holds across scale).** `S_sCE(TAIL) − S_fCE(TAIL)` CI **includes** 0, i.e. cutting
  negatives 24,587→256 remains ~free across the ladder and the damage stays attributable to β. This is a
  pre-registered **null** — passing it is what licenses the causal language in H2.
- **H4 (aggregate blindness, the deployable instrument).** At every rung,
  `|Δ%(gBCE−fCE) on TAIL| / |Δ%(gBCE−fCE) on AGG| > 5`. Anchor rung gives 10.8× on k11–20.
  Secondary: does the amplification factor itself trend with scale?

### 5.4 Exploratory (labelled non-confirmatory, no decision attached)
- **E-A: degree-structured loss↔metric agreement.** Within each band, Spearman ρ between validation loss
  and NDCG@10 across rungs. Candidate mechanistic explanation for arXiv:2606.05257's aggregate sign flip:
  if agreement is head-dominated, an aggregate correlation can inherit the head's sign while the tail
  disagrees. We cannot test their proprietary corpus; we test whether the *structure* that would produce
  such a flip is present.
- **E-B: depth-only ladder.** `--n-layers ∈ {2, 8}` at d=64 grows the sequence model without growing the
  item table. If the interaction appears on the d-ladder but not here, it localises to the item table.

## 6. Stage gate (frozen, no post-hoc seed-adding)

Stage 1 → Stage 2 iff the sign of `S_gBCE(TAIL) − S_fCE(TAIL)` is consistent in **3/3 seeds**.
**No claim of any kind is made at stage 1.** This program has already been burned once by a 3-seed
interim: a 2/3-seed reading showed the k4 text gap significantly *negative* and it did not survive
5 seeds (1/5 positive, CI spanning 0). Stage 1 is a screen; inference happens at n=5 only.
R1 and Steam fire only after stage 2 passes.

## 7. Kill criteria
- No tuning of t, K, β, LR, epochs, or band definitions after any endpoint is seen. R1's LR grid is
  frozen here at {1e-3, 5e-4} and is a sensitivity report, never a selection.
- Any rung whose **aggregate warm** falls >50% below the fCE value at the same rung is declared a failed
  configuration and reported as such, not used as evidence about tail items.
- If ≥2 of the 12 stage-1 cells fail to produce a checkpoint, the ladder is declared infeasible at that
  rung and the ladder is truncated, with the truncation reported.
- The analyser is written against §5's formulas **before** stage-1 completion and frozen; band
  definitions and the OLS-on-log₂(d) estimand are fixed above precisely so the analyser has no freedom.

## 8. Publishability under every outcome
The contribution is the **interaction coefficient**, not its sign.
- H2 negative → published tail-scaling gains are conditional on a loss regime production cannot use.
- H2 ≈ 0 → capacity rescues the tail; β damage is a small-model artifact; this **defends** gSASRec and
  rescopes our own S6.6.1. Reported with equal prominence.
- H2 positive → our β mechanism story is refuted; that is the program's sixth logged failed mechanism
  claim and goes in the corrections log.
H1 failing is also publishable, as a failed replication of a widely cited scaling claim.

## 8a. AMENDMENT A1 — stopping rule for the double null (added 2026-08-18)

**Timing declaration.** Added while stage-1 cell 4 of 36 (`gbce_d32_seed20260736`) was still
training. **No H2 endpoint existed at the time of writing**: H2 is a difference of OLS slopes and
requires gbce *and* fce at ≥2 rungs within a seed, and no gbce cell had completed. The cells observed
so far are `fce_d32`, `fce_d256`, `sce_d32` (seed 736 only) — none of which yields the primary contrast.
This amendment only *removes* future freedom, so it cannot inflate a positive result.

**Why it is needed.** §8 states the paper is publishable under every *single* outcome, which is true,
but says nothing about the one *combination* that leaves nothing standing: **H1 gate fails AND H2 CI
spans 0**. Then neither the premise nor the interaction is present, and the result degenerates to "on
this ladder, nothing much depends on either axis" — a single-dataset null on a ~10⁵–10⁶ parameter
ladder, too thin to carry a standalone submission. Without a rule, the default behaviour is to chase
it across datasets, rungs and seeds. That is forbidden here.

**Decision table, frozen:**

| MI stage-2 (n=5) outcome | Action |
|---|---|
| H1 fails **and** H2 CI spans 0 | **STOP.** Do not run R1. Do not run Steam. Do not extend the ladder or add seeds. Fold the degree-sliced instrument + the anchor-rung 10.8× amplification into `PAPER_COLDSTART_MEASUREMENT_DRAFT.md` as a section, log the null in the corrections log, and close the loop. This becomes a section, not a paper. |
| H1 passes, H2 CI spans 0 | **Steam fires.** "Capacity rescues the tail / β damage is scale-transient" is a real claim that defends gSASRec, and a claim of that form needs a second dataset. |
| H1 fails, H2 significant | **Steam fires.** The interaction exists independently of the premise; report the premise failure prominently as a failed replication alongside it. |
| H1 passes, H2 significant | Full plan: R1 LR-sensitivity at d=256, then Steam. |

**Corollary.** A null is not a reason to spend more compute; it is a reason to spend less. The cheapness
of this ladder (~2-3 GPU-hours for stage 1) is *not* a licence to keep sampling until something moves.

## 8b. AMENDMENT A2 — LR-robustness ladder (added 2026-08-18, POST-HOC IN ORIGIN)

**Honest status label.** This amendment was written *after* seeing R1, i.e. it was triggered by an
observed result. It is therefore **not** an independent confirmatory test, and every number it produces
is reported as a **robustness analysis with a post-hoc label**. What *is* frozen here — before any of
its 54 new cells run — is the prediction and the decision rule below. That is the strongest integrity
guarantee available for an amendment of post-hoc origin, and the label is not removable later.

**Trigger.** R1 (d=256, n=3, pre-registered) showed that lowering LR 1e-3 → 5e-4 moves fCE's HEAD
+0.009996 (CI excl 0, 3/3) and its TAIL −0.002301 (CI excl 0, 0/3), while gBCE is LR-insensitive in
every band. So **LR trades head against tail inside full-CE**, and the H2 magnitude attenuates ~2.5×
(−0.004647 → −0.001851) with the n=3 CI spanning 0. Direction survived; LR-invariance did not.

**Design.** The full ladder re-run at `--lr 5e-4`: 3 losses × 4 rungs × 5 seeds = 60 cells, of which
the 6 R1 cells (fce/gbce, d=256, seeds 736-738) already exist under identical settings and are reused.
**54 new cells**, ~2-3 GPU-hours. Estimands, bands, Holm family and analyser are unchanged — the
analyser takes `--lr 5e-4` and reads the suffixed filenames.

**Frozen prediction (recorded before the 54 runs).** H2 stays negative in direction, with magnitude
**smaller** than at lr=1e-3 — R1 already indicates attenuation at the top rung, and this amendment does
not get to pretend otherwise.

**Frozen decision rule.**
- H2 at lr=5e-4, n=5, CI **excludes** 0 → LR-robustness established: the interaction holds in direction
  *and* significance at two tuning points. The paper's claim stands as a two-LR result.
- H2 at lr=5e-4, n=5, CI **spans** 0 → the claim is **explicitly bounded to lr=1e-3** and stated as
  such in the abstract, not buried in limitations. We would then be reporting an interaction that is
  significant at one tuning point and directionally consistent but underpowered at another.
- Either way the **relative-vs-absolute estimand caveat (§8c) and the H4 failure are reported unchanged**;
  this amendment cannot rescue them.

**Not permitted under this amendment:** adding seeds after seeing the CI, switching the primary estimand
to relative slopes, choosing whichever LR gives the better result, or dropping lr=1e-3 as "mistuned".
Both LRs are reported side by side.

## 8c. Post-hoc note — absolute vs relative estimand (recorded 2026-08-18)

H2 was pre-registered on **absolute** slopes and is supported at n=5 (−0.000777, CI [−0.001427,
−0.000127], 0/5 positive, Holm α=0.0167). The same contrast on **relative** slopes (each band
normalised by its own d=32 level) gives **+0.070, CI [−0.270, +0.410], 3/5 positive — spans 0**;
gBCE's mean relative tail slope (0.3862) is if anything higher than fCE's (0.3161).

**This is a flaw in the prereg, not a finding: §5's H1 used relative slopes while H2 used absolute — an
inconsistent estimand inside one document.** Reported, not buried. The defensible claim is therefore
the bounded one:

> gBCE's tail *does* scale proportionally, but from a base so suppressed that it never converts into
> absolute rankability within this ladder.

The claim "gBCE's tail does not scale" is **not** supported and must not be made.

Separately, **H4 failed as pre-registered** (worst rung d=256: 6.05×, CI on amp−5 spans 0). Its
estimator is a ratio that blows up as its denominator → 0 (d128 returned 38.93× because the aggregate
gBCE−fCE gap there is near zero). No post-hoc rescue; the instrument needs redesign before reuse.

## 9. Cost
Relative per-run cost ≈ ∝ d_model: {0.5, 1, 2, 4} → 7.5 anchor-run-equivalents per (loss, seed);
stage 1 ≈ **67.5 anchor-run-equivalents**. Absolute total is **not estimated here** — one timing
calibration run at d=32 and one at d=256 must be recorded before the campaign is scheduled.
Operational constraints from this program's log: run trainers in the **foreground** with a
per-invocation cap and skip-if-exists resume (detached/background launches get reaped in this
environment), and **never pipe a long-running run through `Select-Object -First N`** — it kills the
upstream process. Redirect to log files.
