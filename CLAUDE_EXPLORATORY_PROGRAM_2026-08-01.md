# Claude exploratory program — 2026-08-01

**STATUS: EXPLORATORY, POST-HOC, NOT PREREGISTERED.** Nothing here is a countable claim, nothing
is integrated, and no repo artifact was modified. All runs are scratchpad-only. Every
`results_*.json` was backed up and restored; verified clean against HEAD.

Role: scientific red-team. Prompted by maintainer questions about alternative directions.
Advisory only — not peer review, not independent evidence.

```text
WORKSTREAM:        evaluate candidate research directions before any prereg is written
OBJECTIVE:         cheap, decisive checks on five proposed directions + one prior-art gate
EVIDENCE QUESTION: which direction, if any, survives a novelty AND a validity check?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   recorded findings incl. my own refuted predictions
STOP CONDITION:    memo committed and pushed
```

---

## 1. Content-channel measurement (the "richer text + modern encoder" proposal)

Encoder held FIXED (`all-MiniLM-L6-v2`), only the encoded text varied, so differences isolate
the **channel**. Beauty, 5 folds, committed pipeline reused verbatim.

**Validity anchor:** `beta=10, title-only` reproduced **0.17311** — bit-identical to the
committed `lc2c_v2` value. Harness faithful.

| variant | chars | LC2C-V2 | vs title-only |
|---|---:|---:|---:|
| A title only | 150 | 0.17311 | — |
| B + store + main_category | 175 | 0.17142 | −0.98% |
| C + details | 328 | 0.16745 | −3.27% |
| D + description + features | 379 | 0.17317 | +0.03% |
| E all | 582 | 0.16949 | −2.09% |

**Finding 1 — richer text does nothing; more channels slightly hurt.** ~4x text length,
flat-to-negative effect, all inside the ±0.015 fold noise. **This is a negative result for the
encoder/text-enrichment plan**, obtained in ~15 min CPU.

**Raw-metadata coverage (beauty, 20k sampled records)** — itself a finding, since it
contradicts the assumption that rich text is available:
`title` 99.9% · `main_category` 100% · `details` 97.2% · `store` 90.1% ·
**`description` 18.1%** · `features` 16.7% · **`categories` 0.0% (entirely empty)**.

**Finding 2 (more important) — most of LC2C's reported margin is a beta artifact.**
`ease_fast` computes `G = X^T X + beta*S_content + lam*I` with **beta=10**, so the EASE target
`B` already contains SBERT similarity before LC2C regresses SBERT onto it.

| | LC2C − content_direct |
|---|---:|
| beta=10 (content injected into Gram) | **+0.0282** |
| beta=0 (pure collaborative EASE) | **+0.0073** |

**Removing content from the target destroys ~74% of LC2C's advantage.** The residual +0.0073 is
what the content→collaborative mapping genuinely contributes. This **materially undercuts my
earlier statement to the maintainer that the cold-item direction looked stronger than FIR** —
recorded here as a correction to my own framing.

## 2. Exact unlearning for EASE — the one positive result

**Claim tested:** because EASE is closed-form, deleting a user is an exact rank-one Gram
downdate, not an approximation.

```
G = X^T X + beta*S + lam*I     (only X^T X depends on users)
remove u:  G' = G - x_u x_u^T
Sherman-Morrison:  (G - x x^T)^-1 = P + (P x x^T P)/(1 - x^T P x)
B = -P/diag(P), diag <- 0
```

**Scale ladder** (float64, victim = densest user, verified against full retrain):

| dataset | n items | dense P | retrain | unlearn | speedup | max\|dB\| |
|---|---:|---:|---:|---:|---:|---:|
| beauty k=5 | 356 | 0.00 GB | 0.036 s | 0.001 s | 63.7x | 6.3e-17 |
| beauty k=4 | 851 | 0.01 GB | 0.073 s | 0.005 s | 15.2x | 7.6e-17 |
| beauty k=3 | 1,463 | 0.02 GB | 0.279 s | 0.013 s | 22.3x | 6.3e-17 |
| instruments | 2,269 | 0.04 GB | 0.253 s | 0.031 s | 8.1x | 2.4e-16 |
| beauty k=2 | 12,105 | 1.09 GB | 14.906 s | 0.900 s | 16.6x | 2.5e-16 |
| **Video_Games** | **25,527** | **4.86 GB** | **71.94 s** | **4.582 s** | **15.7x** | **4.30e-16** |

Video_Games: 94,762 users, 625,062 interactions, lambda=200, victim = densest user (471
interactions), peak ~33.7 GB, total runtime ~2.5 min.

**Finding 3 — exactness holds across a 72x range of catalog size** (6.3e-17 → 4.3e-16). Error
growth is consistent with float64 accumulation, not method breakdown. This is the load-bearing
result.

**Finding 4 — MY PREDICTION WAS WRONG.** I predicted the speedup would grow ~linearly in n
(O(n^3)/O(n^2)). Measured: **flat and noisy, 8-64x, no trend**; VG (15.7x) is *lower* than
beauty k=5 (63.7x). Both operations are memory-bandwidth-bound at these sizes — LAPACK's inverse
is BLAS-3 and multithreaded, the rank-one update is BLAS-2 writing a full n^2 array.
**"Unlearning scales better than retraining" is REFUTED by measurement.**

**Finding 5 — memory ceiling.** Dense `P` is the binding constraint, inherited from EASE itself:
VG 4.86 GB; **Office_Products (77,551 items) 44.8 GB**; beauty un-k-cored (112,565) 94.4 GB.
The method cannot reach the scale where sparse-index methods operate.

## 3. Why neural recommenders structurally cannot match this

L-hop blast radius of deleting ONE user (real bipartite graphs):

| GCN layers | beauty: items touched | instruments: items touched |
|---:|---:|---:|
| 1 | 2.8% | 0.6% |
| 2 | 77.6% | 92.0% |
| **3** | **100.0%** | **100.0%** |

At LightGCN's standard L=3, one deletion perturbs **every** node. No local correction exists and
parameters were fit iteratively. **Finding 6:** adding a GNN/GCN (or HSTU) *removes* the property
that makes the EASE result work. This is a supporting figure for direction 2, not a direction.

## 4. Prior art — two full-text reads

| work | venue | model class | mechanism | covers LAE? |
|---|---|---|---|---|
| Unlearn-ALS (arXiv:2302.06676) | 2023 | MF `M = XY^T`, ALS | Sherman-Morrison on the **k x k** ALS subproblem; exact **at the fixed point**, iterative | **NO** — 0 hits for SLIM/linear autoencoder/item-item; 6 "EASE" hits all false positives (`increase`/`decrease`) |
| Caboose / "Forget Me Now" (deem.berlin) | **SIGIR 2023** | item/user **kNN** | sparse top-k **index** patching; exact; millions of items | **NO** — 0 hits for SLIM/linear autoencoder/matrix inversion/Sherman/Woodbury/closed-form |
| Rec-unlearning survey (arXiv:2412.12836) | Dec 2024 | MF, bi-linear, KNN, GNN, KG, LLM, session | taxonomy | **absent** |
| ERASE benchmark (arXiv:2603.08341) | **SIGIR 2026** | LightGCN, DCCF, BPR, IBCF, SimRec, GRU4Rec, NARM, SASRec, S-KNN, SRGNN | benchmark | **absent** |

Both nearest methods were read in full and verified by local text extraction, **not** by fetch
summary. They sit on either side of the linear-autoencoder family: one handles low-rank
factorization, the other sparse neighbourhood indexes. **Neither handles the dense-inverse
item-item case**, and a 2026 SIGIR benchmark still omits the family.

**Correction to my own earlier framing:** Sherman-Morrison/Woodbury in recommender unlearning is
**already published** (Unlearn-ALS, 2023). The technique is not new to the field and must be
cited prominently. What is unoccupied is narrower: the **linear-autoencoder family**, where the
parameter *is* the dense item-item matrix and the update is **single-step with no iteration and
no fixed point**.

## 5. Directions evaluated and rejected

| proposal | verdict | reason |
|---|---|---|
| FIR + LC2C | **rejected** | type mismatch — EASE has no time axis (timestamp is dropped at preprocessing); the embedding-dim variant is absorbed by the ridge (`SBERT @ F @ W' = SBERT @ W`); and the coherent version was already run as `z-fusion` and swept to a documented impossibility boundary |
| modern encoder + text cleaning | **rejected** | §1 measured flat-to-negative; and beeFormer's thesis is that better *semantic* similarity is not the bottleneck |
| MUL for efficiency/storage/accuracy | **rejected** | unlearning is a compliance operation; it does not shrink models, and cannot raise accuracy — the 1.5e-16 result proves it returns *exactly* the retrained model |
| GNN/GCN + MUL | **rejected** | §3 — destroys exactness; most crowded corner of the field |
| HSTU + MUL | **rejected** | same as GNN, plus the pinned HSTU env is not installable on sm_120, so a scale claim has no hardware |

**Pattern worth recording:** five consecutive "combine X with Y for novelty" proposals, all
negative. The single positive came from *exploiting* existing structure (EASE's closed form),
not from stacking.

## Limits

Exploratory, post-hoc, **not preregistered**; single victim per scale rung; one dataset for the
channel study (253 users); no multiplicity control; no privacy-attack evaluation (exactness
proves deletion, but a paper needs membership-inference or similar); no measurement of what
unlearning does to recommendation *quality*. Prior-art search is not exhaustive — absence from
surveys/benchmarks is absence of evidence, not evidence of absence.

**Discrepancy to reconcile before any write-up:** the VG train split yields **25,527** items,
not the **25,612** in the FIR result JSONs (~85 items appear only in valid/test). Immaterial
here; material for any manuscript number.

**These findings license one decision only:** that exact LAE unlearning is the sole direction
worth a preregistration, and that the encoder/text-enrichment and combination directions are
not. They license no claim in the manuscript.
