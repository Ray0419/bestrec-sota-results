# Cold-start POC: results and verdict
### 2026-08-05 · companion to [RESEARCH_QUESTIONS_COLDSTART.md](RESEARCH_QUESTIONS_COLDSTART.md)
### All numbers recomputed from artifacts in `_bestrec_run/poc_out/`. No paper claim, manifest, or main-checkout file was touched.

---

## 0. Verdict

**The original flagship idea failed; a stronger one replaced it, and the replacement is supported by controlled interventions rather than observation.**

The idea as posed — *a derived empirical-Bayes gate beats learned popularity gates* — is **refuted**. Training-free posterior mixing moves overall NDCG@10 by at most +0.0001 (noise), and every imputation strong enough to rescue cold items costs warm items more in aggregate than it earns.

What replaced it is better because it is a *law with a mechanism*, and both were measured interventionally:

1. **The text advantage is caused by collaborative degree, not by text quality.** Holding item identity and text embeddings fixed and capping only training degree destroys the entire text advantage (+0.0051 → −0.0002, n.s.). Same items, same text, different degree.
2. **Cold-start imputation obeys an exchange rate**, and its break-even cold-item prevalence **scales as √N_cold** (exponent 0.48–0.55, R² 0.98–1.00, three independent methods, one dataset, three rungs). The regime where you most need imputation is the regime where it works worst.
3. **The cold-row error is bias, not variance** (68% seed-invariant, aligned on a suppression axis), which is *why* spectral denoising and additive fusion both fail — and it retro-explains two of the repo's own documented negative results (GD1, X1).

**Recommendation: new direction, same program.** Pivot from "a better gate" to "when does cold-start machinery pay for itself, and why usually not." Confidence that this is real and publishable: high on the mechanism and the interventional degree result; medium-high on the scaling law (single seed — replication is the top priority, see §8).

---

## 1. What was run

**Ten GPU training runs** (1 VG × 40 epochs, 9 MI × 20 epochs) plus **7 full-catalog eval passes** (val+test over 57k–95k users each) and 6 CPU analyses — all new; ~75 minutes of GPU total.

| # | Experiment | Compute | Artifact |
|---|---|---|---|
| POC-A | Degree-sliced text-vs-ID from 16 existing runs' sidecars | 0 GPU | `poc_coldstart_VG.json` |
| POC-0 | EB premise diagnostics on trained tables | CPU | `poc_coldstart_VG.json` |
| POC-1 | Training-free posterior map, 15 variants, val-selected (VG text arm) | 6 min | `results_VG_COLDFUSE_base_*.posterior_eval.json` |
| POC-2 | Same on a fresh ID-only arm (text injected post-hoc) | 17+6 min | `results_POC_VG_idonly_*.posterior_eval.json` |
| POC-3 | Exchange-rate / break-even analysis | CPU | `exchange_rate.json` |
| POC-4 | RQ3: 5-seed bias/variance decomposition + spectral denoising | CPU | `rq3_spectral_diag.json` |
| POC-5 | **k-dial**: item-degree knockdown, MI, 2 arms × 3 rungs, paired | 6×4 min | `kdial_analysis.json` |
| POC-6 | Cold-catalog scaling: MI at N_cold ∈ {31, 649, 3121} + evals | 3×(4+2) min | `scaling_fit.json` |

New code (worktree only): `poc_eb_core.py`, `run_poc_coldstart.py`, `poc_posterior_eval.py`, `poc_exchange_rate.py`, `poc_rq3_spectral.py`, `poc_scaling_fit.py`, `run_sasrec_sbert_kdial.py` (patched trainer copy adding `--item-cap-k/--item-cap-frac/--item-cap-seed/--item-cap-min-deg`), `poc_kdial_driver.py`, `poc_kdial_ckpt_run.py`, `poc_kdial_analyze.py`.

---

## 2. The degree-response curve is an inverted U (observational, 8+8 seeds, VG)

| degree k | text | ID | Δ | rel |
|---|---:|---:|---:|---:|
| 0 | 0.00000 | 0.00000 | 0 | — |
| 1–2 | 0.00081 | 0.00097 | **−0.00016 ± 0.00012** | **−16%** |
| 3–5 | 0.00555 | 0.00565 | −0.00010 | −1.8% |
| 6–10 | 0.01336 | 0.01255 | +0.00081 | +6.4% |
| 21–50 | 0.03838 | 0.03555 | **+0.00283 ± 0.00031** | **+8.0%** |
| 51–150 | 0.06559 | 0.06261 | +0.00299 | +4.8% |
| >500 | 0.25251 | 0.25342 | −0.00092 | −0.4% n.s. |

Text helps *mid*-degree items and is useless-to-harmful at the extremes. The field's premise ("semantics help most where interaction data is scarcest") is inverted where it matters most. Caveat: observational, arms not initialization-paired (different seed ranges) — which is exactly what §5 fixes.

## 3. At k=0 the additive text channel is dead, and the row is actively corrupted

85 VG items have zero train interactions. Both arms score **exactly 0.0** on their 345 eval targets in all 16 runs. Trained ID rows for these items have mean norm **0.32 vs 0.55** warm: the full-catalog softmax sees them only as negatives and pushes them down. Median rank of a k=0 target: **9,463/25,612** (text) and **11,901** (ID) — worse than random.

Post-hoc replacement of those rows by a text-kNN imputation moves median rank to **914** and lifts cold NDCG@10 from 0 to **0.0206**. The information needed *is* present in the frozen text; the architecture cannot use it. **Cold start here is a corrupted-estimate problem, not a missing-information problem** — so additive fusion and learned gates, which *add to* the broken row rather than *replacing* it, cannot fix it by construction.

## 4. The exchange rate, and why per-slice reporting hides it

Any imputation writes a plausible row into a shared full-catalog softmax, where it competes for every query. Measured (ID-only VG arm, per-target NDCG@10):

| variant | cold gain | warm cost | aggregate | break-even p\* |
|---|---:|---:|---:|---:|
| k0orth_t2 | +0.1216 | −0.01843 | −0.01792 | 13.2% |
| k0knn_s1 | +0.0186 | −0.00125 | −0.00117 | 6.3% |
| **k0knn_s0.85** | +0.0033 | −0.00007 | −0.00005 | **2.0%** |
| ebrdg_c2 (EB mix) | +0.0037 | −0.00144 | −0.00142 | 28.0% |

The rule: imputation is aggregate-positive iff **p_cold > p\* = |warm cost| / (cold gain + |warm cost|)**. VG's observed cold prevalence is **0.36%**, below every p\* — so every variant, including the EB posterior mix, is net-negative there.

A paper reporting "cold NDCG 0 → 0.019, warm 0.0661 → 0.0649" reads as a win and is a net loss. Per-slice reporting shows the numerator; only the prevalence-weighted aggregate decides. This is distinct from the sampled-metrics critique (Krichene & Rendle, KDD 2020), which concerns biased estimation of the *same* item's metric; this is a cross-item externality invisible even to unbiased full-catalog per-slice reporting.

## 5. The k-dial: degree *causes* the text advantage (interventional, paired)

Musical_Instruments, 3,090 items capped, eval users/targets/terciles frozen at full density, arms initialization-paired (same seed and config; only the capped interactions differ). Verified identical eval user/target order across all six runs.

**NDCG@10 on the 11,556 eval targets that land on capped items:**

| rung | text | ID | text−ID | 95% CI | vs anchor (text) |
|---|---:|---:|---:|---|---:|
| anchor (uncapped) | 0.04302 | 0.03788 | **+0.00514** | [+0.0031, +0.0072] **excludes 0** | — |
| cap k=4 | 0.00016 | 0.00038 | −0.00022 | [−0.0006, +0.0001] includes 0 | **−0.04286** |
| cap k=0 | 0.00000 | 0.00000 | 0.00000 | — | −0.04302 |

Control (45,883 uncapped targets) stays flat and slightly rises — no eval drift, no capacity collapse: text 0.04085 → 0.04252 → 0.04352.

This is the load-bearing result. **The same items, with the same frozen text embeddings, lose their entire +0.0051 text advantage when their training degree alone is reduced to 4.** The advantage is therefore not an intrinsic property of the text — it is *caused by* collaborative degree. Capping to k=4 destroys ~99.6% of an item's rankability in both arms; text compensates for none of it.

## 6. The cold-catalog scaling law (three rungs, one dataset, controlled)

Same dataset, architecture, seed, and code; only the number of cold items differs.

| rung | N_cold items | cold targets | p_obs | k0knn_s1: gain / cost / p\* |
|---|---:|---:|---:|---|
| anchor | 31 | 106 | 0.18% | +0.0064 / −0.00033 / **4.96%** |
| cap 5% | 649 | 2,686 | 4.68% | +0.0259 / −0.00532 / **17.07%** |
| cap 25% | 3,121 | 11,662 | 20.30% | +0.0148 / −0.01326 / **47.32%** |

Log-log fits vs N_cold:

| method | cold gain ~N^a | warm cost ~N^b | **break-even p\* ~N^c** |
|---|---|---|---|
| k0knn_s1 | a=+0.22 (R² 0.53) | b=+0.81 (R² 0.99) | **c=+0.48 (R² 0.98)** |
| k0dev_t1.4 | a=−0.07 (R² 0.13) | b=+0.58 (R² 0.97) | **c=+0.49 (R² 1.00)** |
| k0orth_t2 | a=−0.32 (R² 0.85) | b=+0.42 (R² 0.94) | **c=+0.55 (R² 0.99)** |

**p\*(N) ∝ √N_cold**, with near-perfect fit and the same exponent across three methods whose gain profiles differ by an order of magnitude — while the gain per cold target barely scales at all. Because actual prevalence grows roughly linearly in N_cold, the margin p_obs/p\* improves only as √N: imputation eventually pays, but far more slowly than the naive expectation, and only for heavily damped variants (`k0knn_s0.7` pays at 4.68% and 20.30%; every aggressive variant still loses at 20.30%). **The optimal imputation strength must shrink as the cold catalog grows** — the opposite of what a fixed hyperparameter or a learned-once gate provides.

## 7. RQ3: the cold-row error is bias, and spectral denoising fails explainably

Five same-config VG checkpoints, Procrustes-aligned:

| bucket | across-seed variance | ‖mean row‖ | proj. on suppression axis | cos to warm mean |
|---|---:|---:|---:|---:|
| k=0 | 0.0107 | 0.304 | **+0.158** | +0.283 |
| 1–2 | 0.0853 | 0.419 | **+0.160** | +0.241 |
| 21–50 | 0.0998 | 0.522 | +0.060 | +0.143 |
| >500 | 0.0257 | 0.505 | **−0.224** | −0.461 |

The shared, seed-invariant component is **68% of row energy at k=1–2**, and cold rows align with a common suppression axis that head rows anti-align with, monotonically — the fingerprint of negative-sampling suppression.

So spectral denoising cannot help, and does not: reconstruction error against the 5-seed mean is **0.097 untouched → 0.239 homoscedastic Gavish–Donoho (the repo's documented GD1 lever) → 0.218 degree-whitened**. Degree-whitening (the 2024 heteroscedastic-theory upgrade) beats GD1 by **9%**, confirming the noise model *was* misspecified — but both lose badly to identity, because the dominant term is bias and no variance-shrinkage operator removes bias. **RQ3 is retired as a fix and promoted to an explanation**, independently corroborating the repo's GD1 and X1 negatives with a mechanism.

---

## 7b. Independent convergence with a parallel session (read this before planning)

While this POC ran, a **separate session** wrote `TIER_A_COLDSTART_RESEARCH_AGENDA_2026-08-05.md` (untracked, in the main checkout, same repo, same day). Its **#1-ranked GO question** is, in its words, whether a cold-start benchmark can "reward catalog-wide cold promotion without learning any cold relevance," and whether "catalog onboarding [can] be certified against warm-user tail harm" — proposing an offset-degeneracy theorem, a global-time mixed-target protocol, and a CVaR-certified integration wrapper.

That is **the same phenomenon this POC measured**, reached independently from the theory/protocol side while this one came from measurement. Two independent derivations of the same gap is strong evidence the gap is real and unoccupied. The two halves are complementary, not duplicative:

| their agenda (theory-first) | this POC (measurement-first) |
|---|---|
| offset-degeneracy theorem; why the benchmark can be gamed | the exchange rate: the quantitative cost of cold promotion |
| global-time mixed-target protocol | the k-dial: a causal degree intervention with frozen eval |
| CVaR/OCE certification wrapper against warm harm | **p\* ∝ √N_cold** — the certification threshold's actual scaling |

Their document also notes the repository "has already produced the predicted intervention curve" — §5 and §6 here are that curve, measured.

**Reconciled 2026-08-05: see [MERGED_COLDSTART_AGENDA.md](MERGED_COLDSTART_AGENDA.md).** A joining experiment (`poc_offset_decomp.py`) confirmed their offset-degeneracy proposition *exactly* (within-cold NDCG invariant to 5 dp across every δ, while cold-target full-catalog NDCG rose 0.00000 → 0.02165 and warm fell 76%) and showed that **~95% of text-kNN imputation's measured cold benefit is that nuisance offset, not learned cold relevance** (within-cold gain only +0.00072 of a +0.01476 full-catalog gain). Content is not worthless — imputation is ~1.7× more efficient per unit of warm harm than a pure offset — and that ratio becomes the merged paper's central instrument. §7's suppression-axis bias explains *why* degeneracy exists: a shared direction cancels within-pool but not cross-pool.

*(Also note: that session placed a `PAUSE_EXPERIMENTS` sentinel in this worktree's root at 12:25 to serialize GPU access. It is left in place, untouched. It will block `run_sasrec_sbert_kdial.py` until its owner removes it — relevant to the 5-seed replication in §9.)*

## 8. Honest limitations (what a reviewer will attack first)

1. **Single seed** for the k-dial and all three scaling rungs. The scaling exponents are 3-point fits from one seed. **Top priority: 5 seeds × 3 rungs (~2 GPU-hours) before any of this is claimable.**
2. **One dataset** for the causal results (MI); the observational curve and exchange rate are VG. Cross-dataset replication needed — Office/CDs/IS caches are on disk, BLaIR is not available for all.
3. **Post-hoc imputation only.** An in-training variant (imputed rows receiving gradient) may sit on a different frontier; untested.
4. **Two cap values** (k∈{0,4}) for the degree curve. The full dose-response needs k∈{0,1,2,4,8,16}.
5. **Architecture scope**: one HSTU-style backbone with additive text fusion and full-catalog softmax. The suppression mechanism should generalize to any shared-softmax retrieval model, but that is an argument, not a measurement. Sampled-softmax and two-tower variants may differ — worth one run to check.
6. The TFV2 observational arms are not initialization-paired, and that campaign is outcome-visible.

## 9. What to do next, in order

1. **Replicate the k-dial at 5 seeds** (paired arms) — converts §5 from suggestive to claimable. ~2 GPU-h.
2. **Fill the dose-response** k∈{0,1,2,4,8,16} at 5 seeds, one dataset. ~6 GPU-h. This is the paper's central figure.
3. **Second dataset** for the scaling law (VG or Office at 3 rungs × 3 seeds). ~4 GPU-h.
4. **Damping-schedule test**: does the √N law predict the optimal imputation strength out-of-sample? Derive s\*(N) from rungs 1–2, predict rung 3, verify. This is the strongest possible form of the contribution.
5. Only then: in-training variant, sampled-softmax control, and the paper.

## 10. Verdict per research question

| RQ | Status |
|---|---|
| RQ1 — derived EB gate beats learned gates | **Refuted as posed.** Posterior mixing is noise-level; at realistic cold prevalence no variant pays. Survives only in the k=0 *replacement* limit. |
| RQ1′ — **exchange rate + √N break-even law** | **Promoted to flagship.** Novel, quantitative, actionable, mechanistically explained, interventionally measured. |
| RQ2 — interventional degree-response | **Confirmed and strengthened.** Degree *causes* the text advantage; machinery built and validated. Needs seeds. |
| RQ3 — heteroscedastic spectral denoising | **Null with mechanism.** Whitening beats GD1 by 9%; both lose to identity. Publishable as a boundary result. |
| RQ4 — two-view detectability | **Deprioritized.** §7's bias finding explains the same phenomena more directly and with less theoretical risk. |
