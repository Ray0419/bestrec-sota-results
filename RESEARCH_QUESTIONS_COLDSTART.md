# Research Questions: Cold-Start as an Estimation Problem
## Tier-A candidate research questions answerable with this repo's machinery
### 2026-08-05 · status: literature-verified + POC executed · artifacts: `_bestrec_run/poc_out/`

> **SUPERSEDED IN PART — read [POC_RESULTS_COLDSTART.md](POC_RESULTS_COLDSTART.md) first.**
> The full experiment program below was executed the same day. Outcome: **RQ1 as posed
> (a derived EB gate beating learned gates) is refuted** — posterior mixing is noise-level
> and every cold-rescuing imputation is aggregate-negative at realistic cold prevalence.
> **RQ2 is confirmed and strengthened**: an interventional degree-knockdown shows the text
> advantage is *caused by* collaborative degree (same items, same text, +0.0051 → −0.0002).
> **RQ3 is a null with a mechanism** (the cold-row error is bias, not variance).
> The flagship is now **RQ1′: the cold-start exchange rate and its √N_cold break-even law**.
> This document is retained as the literature map and the original hypothesis record.

---

## 0. Executive summary

Four research questions, ordered by confidence × payoff. RQ1+RQ2 form one flagship paper; RQ3/RQ4 are modular attachments. A zero-GPU proof-of-concept was executed against existing artifacts (§1) and **produced three unpublished empirical observations that materially de-risk the program**.

| # | Question (one line) | Contribution type | Confidence after POC |
|---|---|---|---|
| **RQ1** | Is the optimal per-item ID↔text fusion a *derived* empirical-Bayes posterior mean — with degree-indexed weights α(k) and CLOSE-corrected (precision-dependent) prior moments — rather than a learned or grid-searched gate? | New modular algorithm; zero gate parameters; training-free variant | **High** (premise confirmed empirically; gap verified open) |
| **RQ2** | What is the *causal* degree-response curve A(k) of the text-vs-ID advantage, measured by graded item-degree knockdown with frozen eval — and is the observed non-monotonicity (sign reversal at low k) causal or confounded? | New evaluation methodology + an empirical law; completes the titration program's third axis | **High** (the observational curve already shows structure worth explaining) |
| **RQ3** | Does degree-aware (heteroscedastic) spectral denoising fix trained tables post-hoc where homoscedastic Gavish–Donoho failed (documented GD1/X1 negatives)? | Training-free modular procedure | **Medium** (POC shows the noise geometry is more interesting than the textbook model — see §1.3) |
| **RQ4** | Does text side information shift the spectral detectability of tail signal (correlated-spike BBP, Oct-2025 theory) — done *properly*, where the retracted single-view Fig-3 claim could not be? | Theory-backed science result | **Medium** (higher risk; now also a redemption arc for a retraction) |

**Flagship pitch:** the field hand-designs or learns popularity gates between ID and text (GateSID, DCGL, SPARK, FAERec — 2025-26); this repo itself grid-searches per-bin fusion weights (COLDFUSE, Holm-significant across 5 categories). Nobody *derives* the weight. Two 2024–2026 statistics results — covariate-powered EB and precision-dependent EB (Econometrica Mar 2026, never applied to ML embeddings) — supply the derivation, our POC confirms their premises hold in trained tables, and the titration machinery can validate the resulting α(k) law *interventionally*, which no other group's infrastructure does credibly.

---

## 1. What the proof-of-concept found (2026-08-05, zero GPU, existing artifacts only)

Setup: Video_Games 5-core. Degree = target item's train-split interaction count. POC-A compares the TFV2 campaign's text arm (8 seeds, 20260841-48) vs ID-only arm (8 seeds, 20260851-58) from their per-user `*.users.jsonl.gz` sidecars — same frozen eval users/targets; arms **not initialization-paired** (Welch across per-seed bucket means; outcome-visible campaign, so treat as exploratory). POC-0 runs estimation diagnostics on a trained text-arm checkpoint's *effective* item embedding E = item_emb + proj(text) + TAPE.

### 1.1 The degree-response curve is non-monotonic with a sign reversal (unpublished shape)

| target-item train degree k | text NDCG@10 | ID NDCG@10 | Δ (text−ID) | rel. |
|---|---:|---:|---:|---:|
| **0** | **0.00000** | **0.00000** | ±0.00000 | — |
| 1–2 | 0.00081 | 0.00097 | **−0.00016 ± 0.00012** | **−16.3%** |
| 3–5 | 0.00555 | 0.00565 | −0.00010 ± 0.00013 | −1.8% |
| 6–10 | 0.01336 | 0.01255 | +0.00081 ± 0.00021 | +6.4% |
| 11–20 | 0.02471 | 0.02309 | +0.00162 ± 0.00038 | +7.0% |
| 21–50 | 0.03838 | 0.03555 | **+0.00283 ± 0.00031** | **+8.0%** |
| 51–150 | 0.06559 | 0.06261 | +0.00299 ± 0.00040 | +4.8% |
| 151–500 | 0.11603 | 0.11338 | +0.00265 ± 0.00058 | +2.3% |
| >500 | 0.25251 | 0.25342 | −0.00092 ± 0.00097 | −0.4% n.s. |

The text advantage is an **inverted-U in degree**: negative at k≤5, peaking around k≈21–150, gone at the head. The field's implicit model ("text helps most where data is least") is wrong *in the additive-fusion architecture* — the extreme tail is where text-as-additive-channel fails. The published tercile-level tail results average over a sign change. No paper we checked reports this curve; observational caveat (degree confounds item age/text quality) is exactly what RQ2's intervention removes.

### 1.2 At k=0 the additive text channel is completely dead (both arms 0.0, 16/16 runs)

VG naturally contains **85 zero-train-degree items** (≈345 eval targets/seed hit them). Both arms score **exactly 0.0** NDCG@10 on them, every seed. Mechanism visible in the checkpoint: never-target items still enter the chunked-full-softmax as negatives every step, so their ID rows are *actively pushed down* (mean row norm 0.32 vs 0.55 warm — moved from init, in the wrong direction). Adding proj(text) to a corrupted row cannot rescue ranking. **Cold-start in this stack is not a missing-information problem but a corrupted-estimate problem** — the estimator must *replace* the row (α(0)=0 ⇒ e = m(x)), not augment it. This is precisely the EB posterior-mean behavior and precisely what additive/learned-gate architectures don't do at init.

### 1.3 The CLOSE premise holds; textbook EB is misspecified here (as the 2026 theory predicts)

- **Precision–parameter dependence is strong**: spearman(k, ‖E‖) = **+0.47** — the "true" item vector's scale grows with degree, so the textbook EB assumption (parameters ⊥ precision) fails, which is exactly the setting of Chen's CLOSE (Econometrica 2026).
- **The residual second moment vs a cross-fitted text prior is non-monotone in k**: 0.0032 (k=0) → 0.0086 (peak, k≈6–20) → 0.0047 (head). A naive `τ² + σ²/k` fit collapses (σ̂²→0): the *prior variance τ²(k) itself is degree-dependent* (cold items huddle near small-norm/unrecommendable; warm items develop large idiosyncratic collaborative identities text can't predict).
- Consequences for the estimator (now design requirements, not guesses): (a) prior moments m(x,k), τ²(k) must be fit *per degree bin* (CLOSE-lite, implemented in `poc_eb_core.py`); (b) a norm-calibration step is needed when imputing cold rows (the repo's own `--cold-synth-norm` trick, now theoretically motivated); (c) the naive global James–Stein form was doomed independent of how c was chosen — which reframes the X1 negative (§2).

POC artifacts: [poc_coldstart_VG.json](_bestrec_run/poc_out/poc_coldstart_VG.json), runner [run_poc_coldstart.py](_bestrec_run/run_poc_coldstart.py), estimator core [poc_eb_core.py](_bestrec_run/poc_eb_core.py) (all in the worktree; read-only against main-repo artifacts).

---

## 2. Position relative to this repo's own program (verified against main @ `7105cd29`)

The main checkout has moved past this worktree's snapshot; everything below was checked against the current state.

- **The manuscript is now a bounded FIR-module paper** (two counted claims: MI vs 0.0406; Office V3 vs 0.0271/0.0279) with a Tier-A roadmap (`TIER_A_PUBLICATION_ROADMAP.md`) focused on fair tuning, a non-Amazon domain, and temporal controls. **The cold-start program proposed here does not collide with that roadmap** — it is the natural *next* paper, reusing the artifact-gate/prereg/adjudicator discipline that is this repo's distinctive strength.
- **COLDFUSE V1 is adjudicated W-C-POS on all 5 categories** (`coldfuse_v1_adjudication_v2run_20260723.json`, Holm-significant, no-material-cost): validation-grid-selected, per-tercile-bin score fusion (EASE/text; selected profile exp0.9, wt_tail=0.2, wt_mid=wt_head=0) roughly doubles tail NDCG (e.g. VG 0.0046→0.0080). **This proves large tail headroom exists in this stack** — and defines RQ1's gap sharply: COLDFUSE *searches* 3 coarse bin weights on validation; EB *derives* per-item continuous weights, needs no validation signal (hence works at k=0 where validation has nothing to select on), and predicts what the search should find. "Does the derived α(k), bin-averaged, reproduce the grid-selected wt profile?" is a free, elegant validation.
- **Five dead levers in the negative map are hand-shaped versions of the same gate** — X1 James–Stein (λ=c/(c+n), SGD-learned global c → 0), CF1 cue-fusion (inverse-variance, hand-set precisions), Z1 fitness-gate (sigmoid in log-freq), conn-gate (learned sigmoid on users/item), cold-synth-kNN (text-neighbor imputation). The autopsy under §1.3's findings: X1's c was learned by SGD *on the warm-dominated training loss* (which cannot reward cold-slice gains) with a constant-τ² form the data reject; CF1's precisions were guessed, not estimated. **The levers failed for identifiable estimation-theoretic reasons, not because shrinkage is wrong** — the redemption story is testable and is RQ1's H5.
- **Retractions to respect** (main @ current): the Fig-3 BBP "spectral irreducibility" *claim* is retracted (`retracted_archive/`; the per-tercile BBP-ρ diagnostic in the trainer survives); the user-titration *connectivity attribution* is retracted because arms were not initialization-paired; VG tail equivalence is not claimed. Nothing in this document builds on a retracted claim; RQ2 mandates initialization-paired arms as a design rule learned from that retraction, and RQ4 exists partly *because* the single-view analysis could not support the retracted conclusion.
- **Natural k=0 items exist in-protocol** (85 in VG; §1.2) — so a "true cold" slice is measurable *today* without protocol changes; the graded k-dial intervention extends it to a curve.

---

## 3. Literature map (verified 2026-08-05)

### 3.1 Occupied (cite and differentiate)

- **LLM-ESR** (NeurIPS 2024 spotlight, [arXiv:2405.20646](https://arxiv.org/abs/2405.20646)): dual-view semantic+collaborative, self-distillation for tail users. No derived weighting, no interventions.
- **Learned popularity gates**: **GateSID** ([arXiv:2603.22916](https://arxiv.org/abs/2603.22916)) — gating network on item maturity, purely empirical; **DCGL** ([arXiv:2605.07314](https://arxiv.org/pdf/2605.07314)) — frequency-aware ID/LLM gate; **SPARK** ([arXiv:2509.11094](https://arxiv.org/pdf/2509.11094)) — parameterized-sigmoid popularity gate; **FAERec** ([arXiv:2604.03688](https://arxiv.org/pdf/2604.03688)). All learn or hand-shape the gate; none derive it; all evaluate observationally.
- **Content-based init** ("Let It Go? Not Quite", RecSys 2025, [arXiv:2507.19473](https://arxiv.org/abs/2507.19473)): frozen content embedding + trainable delta. Full-text verified: uniform δmax norm-clip, **not** degree-conditioned; no EB/shrinkage framing; cold = test-only items. Implicit shrinkage with a hand-tuned uniform radius — EB derives their δmax as a per-item posterior radius.
- **ID-text ensembling** ([arXiv:2512.17820](https://arxiv.org/abs/2512.17820), Jan 2026): independent ID and text models, score-sum. Full-text verified: **no popularity stratification, global weights only**.
- **SID cold-item collapse** ([arXiv:2607.21101](https://arxiv.org/html/2607.21101v1), Jul 2026): TIGER-style generative recommenders get near-zero recall on unseen items (reachability wall). Motivation exhibit for dense-retrieval stacks; note our §1.2 shows dense stacks have their *own* k=0 wall — corrupted rows, not unreachable tokens. That contrast (two different cold-start failure mechanisms, one shared fix direction) is publishable framing on its own.
- **Classic cold-item line** (baselines): DropoutNet, Heater, CLCRec, ALDI, GAR/MetaEmb/GoRec, DiffCold, ColdLLM ([survey](https://github.com/YuanchenBei/Awesome-Cold-Start-Recommendation)). Binary cold/warm protocols.
- **Scalar EB in industry**: Amazon CIKM 2022 (product-search cold start via EB on scalar stats) — sanity precedent; vector/embedding case open.

### 3.2 Verified open

1. Derived closed-form degree-indexed fusion with optimality reasoning (vs learned gates).
2. Graded interventional degree-titration (dose-response) for cold start; binary hiding is the standard.
3. EB/James–Stein shrinkage of neural embedding *tables* (exists only for batch-norm, bandit scalars, SPD matrices).
4. RMT/heteroscedastic optimal shrinkage on recommender embedding tables (exists for MRI/finance/transformer-weights).
5. Side-information spike-detectability theory applied to recommendation (correlated-spike BBP / PLS thresholds, 2024–25, theory-only).
6. The degree-response curve itself: no neighbor paper stratifies ID-vs-text performance by item degree at all (§1.1 appears to be new).

### 3.3 The math imports ("newest math, first application")

| Import | Source | Status |
|---|---|---|
| **CLOSE / precision-dependent EB** — shrink toward E[θ\|σ] when precision predicts parameters | Chen, **Econometrica 94(2), Mar 2026** ([arXiv:2212.14444](https://arxiv.org/abs/2212.14444)); replication package on Zenodo | Applied to Census-tract mobility; never to ML embeddings. **Premise empirically confirmed in our tables (§1.3)** |
| **Covariate-powered EB (EBCF)** — cross-fitted shrinkage toward a covariate-predicted prior mean, heteroscedasticity-robust regret guarantees | Ignatiadis & Wager, NeurIPS 2019 ([arXiv:1906.01611](https://arxiv.org/abs/1906.01611)) | Biostat/econ only; text-embedding covariates unexplored |
| **Heteroscedastic optimal spectral shrinkage** — whitening + data-driven shrinkers (eOptShrink); rank-1 doubly-heteroscedastic fundamental limits | eOptShrink (ACHA 2024); Leeb ([arXiv:1811.02201](https://arxiv.org/pdf/1811.02201)); [arXiv:2405.13912](https://arxiv.org/abs/2405.13912) (limits anchor, rank-1) | Signal processing only; embedding tables untouched |
| **Correlated-spike / PLS spectral thresholds** — when a correlated second view shifts detectability | [arXiv:2510.17561](https://arxiv.org/html/2510.17561) (Oct 2025, AISTATS 2026); Mergny et al. 2024 | Pure theory, no applied use found |

---

## 4. RQ1 (flagship): the derived gate

**RQ1.** Is the optimal per-item fusion of a trained ID row v̂ᵢ and a text-conditional prior mean m(xᵢ, kᵢ) the CLOSE-corrected empirical-Bayes posterior mean

  **v̂ᵢᵖᵒˢᵗ = αᵢ·v̂ᵢ + (1−αᵢ)·m(xᵢ, kᵢ),  αᵢ = τ̂²(kᵢ) / (τ̂²(kᵢ) + σ̂²(kᵢ)/kᵢ)**, plus norm re-calibration at low k,

with all quantities estimated from the trained table by cross-fitted moments (no gate parameters, no validation grid) — and does it match/beat learned gates, COLDFUSE's grid-searched bin weights, uniform mixing, content-init, and DropoutNet-style training on cold/tail slices without head regression?

Hypotheses:
- **H1 (form):** the oracle per-bucket optimal mixing weight follows precision-weighting in k (now with the §1.3 refinement: τ²(k) rising in k), not a sigmoid-in-log-popularity.
- **H2 (zero-param competitiveness):** derived α matches learned gates within noise on warm slices and beats every additive/learned variant at k ≤ 5 — where §1.1 shows additive text is *negative* — and is the only method scoring >0 at k=0.
- **H3 (CLOSE matters):** constant-τ² EB (textbook) underperforms k-binned CLOSE-lite moments; predicted by §1.3's non-monotone residual curve.
- **H4 (training-free):** applying the posterior map post-hoc to an existing checkpoint recovers most of the cold/tail gain of retraining with the layer. (Runtime story: O(1)/item, closed form, no inference cost.)
- **H5 (redemption):** X1's own λ=c/(c+n) form, with c estimated by moments instead of SGD-on-train-loss and the target upgraded from TAPE-cluster-mean to m(x,k), turns a documented negative into a positive on cold slices — an estimation-theory autopsy of a negative result, in the repo's signature honest-reporting style.
- **H6 (theory-predicts-search):** bin-averaging the derived α(k) reproduces COLDFUSE's grid-selected profile (wt_tail≈0.2, wt_mid≈wt_head≈0) — the theory explains the repo's own tuned constants.

Falsification is informative: if the oracle weights are flat in k under intervention, the entire learned-gate literature is optimizing a phantom — publishable either way given RQ2's data.

## 5. RQ2: the k-dial — an interventional degree-response law

**RQ2.** Measure A(k) = text−ID advantage as a *causal* function of item train degree via graded knockdown: for a random item subset, cap train interactions at k ∈ {0, 1, 2, 4, 8, 16} (keep the k most recent; catalog membership, eval targets, tercile boundaries frozen at full density), **initialization-paired arms** (the retraction lesson), ≥5 seeds. Does the observational inverted-U (§1.1) survive intervention — i.e., is the low-k sign reversal a property of degree itself (architecture-induced) or of what low-degree items *are* (age/content confounds)?

- Implementation is a small patch at the existing thinning hook (`run_sasrec_sbert.py:2427–2445` in main; same frozen-eval contract), plus a degree-bucket slice next to `by_popularity` (L1805–1820) — and the slice is *retroactively computable* for all 378 existing sidecars, which is how §1.1 was produced.
- The natural-k0 slice (85 VG items) is a free intervention-adjacent rung already in every past run.
- A(k) measured for: ID-only, additive text (current), the RQ1 posterior layer, and COLDFUSE — the money figure overlays the derived α(k) prediction on the measured curves.
- Power notes: pre-register knockdown fraction so each rung keeps ≥5k eval targets; report per-seed signs + paired stats per house style; TFV2-style unpaired arms are not acceptable here.

## 6. RQ3: training-free heteroscedastic denoising (the GD1/X1 redemption, revised)

The homoscedastic negatives (GD1 spectral shrink; X1 global JS) used the wrong noise model. But §1.3 shows the geometry is not textbook-heteroscedastic either: cold rows are *biased* (pushed down as easy negatives), not merely noisy, and τ²(k) rises with k. So RQ3 is two-stage: (a) diagnose — decompose per-degree row error into bias (mean shift toward the "unrecommendable" region) vs variance, using seed ensembles of checkpoints (5× COLDFUSE bases exist per category); (b) correct — degree-aware spectral shrinkage (row-whitening + eOptShrink family; [arXiv:2405.13912](https://arxiv.org/abs/2405.13912) as rank-1 limits anchor) for the variance part, explicit debias/norm-recalibration for the bias part. Training-free, minutes per table. A null here still sharpens the honest boundary: "post-hoc spectral repair cannot undo negative-sampling suppression" would itself be a citable finding for the SID-collapse conversation.

## 7. RQ4: side-information detectability, done properly

The retracted Fig-3 claim tried to conclude tail *irreducibility* from a single-view BBP analysis — an inference the theory doesn't license (undetectability in one view says nothing about a correlated second view). Correlated-spike/PLS threshold theory (Oct 2025) analyzes exactly the two-view case: interaction spectrum × text spectrum with partial alignment. **RQ4:** estimate the view-correlation and per-tercile SNR on VG vs MI item tables (the trainer's surviving BBP-ρ diagnostic + text Grams), apply the 2510.17561 thresholds, and test whether the theory predicts the measured dataset-conditional pattern (MI tail rescuable, VG tail not) and the §1.1 curve's peak location. Scoped as the theory section of the flagship; standalone only if it lands cleanly. The retraction history makes the honest-reporting frame stronger, not weaker: the repo already documented what the single-view analysis could not conclude.

---

## 8. Experiment plan and budget (runtime-optimized)

| Stage | What | Cost |
|---|---|---|
| Done | POC-A/POC-0 (§1) | 0 GPU-min (sidecar mining + CPU checkpoint diagnostics) |
| Next-1 | **Posterior-map re-eval** (H4): load COLDFUSE base ckpt, swap item table for v̂ᵖᵒˢᵗ, re-run `evaluate()` — VG ≈ 53 s/pass | ~5 min/seed CPU-GPU |
| Next-2 | ID-arm diagnostic ckpt (one `--save-ckpt` VG ID-only run) | ~8 min GPU |
| Next-3 | Mini k-dial: one rung (k=0 cap, 10% of items), init-paired arms, MI | ~2×8 min GPU |
| Paper | Full k-dial grid 6 rungs × 2 arms × 5 seeds on MI + VG (≈17/8 min per VG/MI run) + 1 held-out category (Office or CDs; caches on disk) + baselines (COLDFUSE exists; learned-gate reimpl.; DropoutNet-style; content-init) | ~30–60 GPU-hours total, fits the 16 GB RTX 5060 Ti |
| External validity | +1 non-Amazon text-rich dataset (aligns with roadmap Phase C's selection gate; needs BLaIR/MiniLM encoding pass) | days, optional for v1 |

House rules carried over: initialization-paired arms, frozen eval/terciles, per-seed sign counts, prereg + mechanical adjudicator, artifact manifest, negative results reported under the same rule.

## 9. Publication targeting and honest confidence

- **Venue:** RecSys/SIGIR/WSDM full paper for the flagship; TORS fits the house methodology-first style (and the team's venue plan); NeurIPS/ICLR viable if the CLOSE→embeddings bridge carries the theory section.
- **Why confidence is high on contribution:** (a) the gap is verified open in six specific senses (§3.2); (b) the estimator's premises are now *measured facts* in this stack (§1.3), not hopes; (c) the headroom is proven by the repo's own adjudicated COLDFUSE result; (d) both directions of every hypothesis are publishable under the repo's honest-reporting brand (the field lacks credible negative/boundary results on exactly these questions).
- **Main risks:** the low-k reversal may be architecture-specific (additive fusion) — mitigated because that itself is an RQ2 finding; cold-slice power (85 natural k0 items is thin — the k-dial manufactures more); text-prior weakness on sparse-text categories (dataset-conditionality is a result, not a failure, in this program).
- **What was deliberately not proposed:** semantic-ID/generative architectures (crowded, reachability-wall papers landing monthly), LLM-as-recommender fine-tuning (compute-prohibitive here), and anything building on the retracted claims.
