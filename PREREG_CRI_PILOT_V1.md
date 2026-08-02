# PREREG — CRI Pilot V1 (Cross-Relation Influence disagreement, feasibility) — declared 2026-08-01

**Declared BEFORE any pilot training run. Gates and kill criteria are frozen as written; any deviation must be logged as an erratum, per repo convention.**

## Hypothesis under test

H1: For an interaction e=(u,i) in behavior b, the disagreement between e's behavior-b influence gradient and the user's influence-gradient field in the *other* behaviors separates injected-noise edges from genuine edges **better than pooled self-influence does**.

H0: disagreement ≤ pooled self-influence (the decomposition adds nothing beyond estimator variance).

## Design

**Dataset:** Taobao 3-behavior (MB-CGCN release; 15,448 users, 11,953 items; view/cart/buy). Fixed splits as released.

**Model:** shared-base-embedding multi-behavior LightGCN, d=64, 2 propagation layers per behavior graph, per-behavior BPR losses (1 sampled negative per positive), target behavior = buy, joint loss = mean of behavior losses. Adam lr 1e-3, no weight decay on embeddings beyond 1e-4 L2. 40 epochs. Checkpoints at epochs {10, 20, 30, 40} for TracIn-style accumulation.

**Control model (pooled):** identical LightGCN on the UNION graph of all behaviors (single relation), same hyperparameters — the Koh–Liang homogeneous control.

**Influence estimator (pilot-grade, declared simplification):** gradients taken w.r.t. post-propagation (final) embeddings, not base parameters — representation-space approximation; TracIn accumulation over the 4 checkpoints. PBRF-grade estimation (Heo et al. 2025) is deferred to the full program.

**Scores computed per edge e=(u,i) in behavior b:**
1. `D(e)` (the RQ): 1 − mean over other behaviors b′ (where u has ≥1 edge) of cos(g_b(e), U_b′(u)), where g_b(e) = ∂L_BPR(e)/∂z_u^b and U_b′(u) = normalized mean gradient of u's edges in b′; summed over checkpoints.
2. `SI_pooled(e)`: Σ_ckpt ‖g(e)‖² from the pooled control model (primary control).
3. `SI_b(e)`: Σ_ckpt ‖g_b(e)‖² per-relation magnitude WITHOUT disagreement (ablation: does decomposition alone suffice?).
4. `Loss(e)`: mean BPR loss of e over checkpoints (the cheap ADT-style competitor).
5. Random baseline.

**Noise injection (before training; noise IDs recorded):** per behavior, add fake edges equal to 10% of |E_b|:
- N1 uniform-random items;
- N2 popularity-proportional items (harder, realism proxy).
One run per noise type per seed; seeds {13, 42, 2026}. 2×3 = 6 training runs of each model.

**Detection metric:** ROC-AUC (and AP) of each score ranking injected vs genuine edges, per behavior.

## Pre-declared gates

- **G1 Computability:** full pipeline (train + all scores) completes < 4 h total on M4 Max. FAIL → redesign approximation before any claim.
- **G2 Stability:** Spearman ρ of `D(e)` across the 3 seeds ≥ 0.5 (per behavior, genuine edges). FAIL → Basu-style fragility confirmed at pilot scale; RQ signal is estimator variance ⇒ REFUTED as posed.
- **G3 Signal:** AUC(`D`) − AUC(`SI_pooled`) ≥ +0.03 absolute, on ≥1 noise type, on BOTH auxiliary behaviors (view, cart), in all 3 seeds. FAIL → H0 stands ⇒ RQ REFUTED at pilot scale.
- **G4 Non-triviality:** AUC(`D`) > AUC(`Loss`) under the same conditions as G3. FAIL → cheap competitor wins ⇒ contribution collapses regardless of G3.

**Escalation rule:** ALL of G1–G4 pass ⇒ report to user as the 95%-confidence checkpoint and propose the large-scale program (Tmall + Jdata; PBRF-grade influence; DPT/GCIB/RMBRec/SpectraMB + tuned-ERM baseline suite per the RecSys 2025 audit; downstream remove-and-retrain endpoints). ANY gate fails ⇒ log result honestly, return to RQ hunting with the failure as evidence.

**Explicitly out of scope for the pilot:** downstream remove-and-retrain accuracy, real-noise (non-injected) evaluation, unlearning-efficiency claims, statistical-significance claims beyond the seed-consistency checks above. Injected-noise AUC is a feasibility signal, not a publishable endpoint (synthetic-noise caveat acknowledged; see verdict memo risk #4).

**Artifacts:** code `experiments/cri_pilot/`, results JSON per run `experiments/cri_pilot/results/`, adjudication appended to this file as `## ADJUDICATION` after all runs complete.

## ADJUDICATION — 2026-08-01 (all 6 runs complete; mechanical, `experiments/cri_pilot/adjudicate.py`)

| Gate | Result | Evidence |
|---|---|---|
| G1 computability | **PASS** | 1.52 h total (< 4 h) |
| G2 stability | **FAIL** | min cross-seed Spearman of D on genuine edges 0.051–0.074 vs declared ≥ 0.5, every noise type × behavior |
| G3 signal | PASS (see hollow-pass note) | AUC(D)−AUC(SI_pooled) = +0.054…+0.077, both aux behaviors, all seeds, BOTH noise types |
| G4 non-triviality | PASS | AUC(D) > AUC(Loss) everywhere (+0.047…+0.131) |

**VERDICT (per frozen escalation rule): GATE FAILURE — the RQ is REFUTED at pilot scale as posed.** Per-interaction cross-relation influence disagreement does separate injected noise at the population level, but the per-edge scores do not replicate across seeds; a detector whose flags are seed-dependent is not a per-interaction detector.

### Post-hoc diagnostics (labeled post-hoc; non-confirmatory; ran after the verdict)
1. **Instability is real, not a test artifact:** all-edge Spearman ≈ 0.05–0.075; top-10% flag Jaccard across seeds ≈ 0.056 vs ≈ 0.053 expected under random selection. Per-run separation is z ≈ 0.2 (population shift on massively overlapping distributions).
2. **G3's uniform arm is hollow:** a zero-cost `−itemdegree` heuristic scores AUC 0.65–0.74 on uniform noise, dominating D (0.56–0.58). Degree was absent from the prereg baseline set — design blind spot, logged here.
3. **The popularity arm shows the signal is real and degree-independent:** degree heuristic ≈ chance (0.44–0.53) while D holds 0.555–0.579. The mechanism is not vacuous; it is weak.
4. **User-level aggregation does not rescue it:** per-user mean-D cross-seed stability only reaches ρ ≈ 0.10–0.20; user-level detection AUC 0.54–0.60. The run-to-run variance is correlated within a training trajectory, so √n aggregation does not apply.
5. Loss baseline caveat: our `Loss` score (checkpoint-averaged, epochs 10–40) understates ADT-style early-loss methods; with noise memorized by epoch 40 it even ranks below chance on uniform noise. G4 should not be quoted as "beats loss-based denoising."

### Disposition
Evidence carried forward to the RQ hunt: (a) cross-relation gradient geometry carries a small (z≈0.2), real, degree-independent noise signal at population level; (b) single-run influence-style per-interaction scores at TracIn/representation grade are trajectory-noise-dominated — any future per-interaction claim needs either a fundamentally stronger estimator (PBRF-grade) or an explicitly population/distribution-level claim; (c) trivial degree heuristics must be in every future baseline set. A V2 is NOT pre-registered; CRI returns to the hunt queue as refuted-at-pilot-scale.
