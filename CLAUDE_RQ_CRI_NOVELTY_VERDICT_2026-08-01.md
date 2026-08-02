# CLAUDE — Cross-Relation Influence (CRI) RQ: adversarial novelty verdict — 2026-08-01

**Status:** Novelty gate PASSED at the exact conjunction — but the RQ was subsequently **REFUTED at pilot scale** (2026-08-01, G2 stability gate failure; see `PREREG_CRI_PILOT_V1.md` §ADJUDICATION). Novelty map below remains valid for future reformulations.
**Method:** 102-agent deep-research workflow (5 angles → 20 sources fetched → 98 claims extracted → 25 adversarially verified, 3-vote panels). 23 confirmed 3-0, 2 refuted. Full machine-readable result: session task `wfko4i2l0`.

## The RQ (as it survived)

> Does cross-relation inconsistency — disagreement between **relation-specific influence estimates** in a multi-behavior GNN recommender — provide a **per-interaction** noise-detection signal that pooled (homogeneous) self-influence cannot?

Lineage: the original framing ("machine unlearning in heterogeneous GNN to identify user noise and improve rating prediction") was killed in pre-screening (FDRU 2024 occupies unlearning+denoising; Koh–Liang 2017 occupies influence-as-noise-detector; rating/RMSE target deprecated). This RQ is the surviving reformulation.

## Verdict detail

**Unoccupied (verified, high confidence):** no paper computes relation/behavior-specific influence estimates, and none uses agreement/disagreement between per-relation influence scores as an interaction-level noise signal. Full-text grep-level verification across the nearest 10 neighbors found zero occurrences of influence functions / Hessians / Koh–Liang in the multi-behavior denoising family.

**Occupied — novelty may NOT be claimed on any of these:**
| Territory | Occupant | Note |
|---|---|---|
| Problem framing (auxiliary-behavior noise misleads target prediction; GNN message passing amplifies it) | CIDER (TOIS 2026, [10.1145/3801153](https://dl.acm.org/doi/10.1145/3801153)); SpectraMB (KDD 2026, [arXiv:2606.02417](https://arxiv.org/pdf/2606.02417)); RMBRec (WWW 2026, [arXiv:2601.08705](https://arxiv.org/pdf/2601.08705)) | Differentiate on mechanism only |
| "Consistency reveals noise in multi-behavior graphs" concept | DPT (WWW 2023, [10.1145/3543507.3583513](https://dl.acm.org/doi/abs/10.1145/3543507.3583513)) | Closest ancestor; **mandatory baseline**; uses reconstruction-loss thresholding |
| Generic "disagreement between two estimators as noise signal" | DC4SR ([arXiv:2604.24048](https://arxiv.org/html/2604.24048)) | LLM-vs-backbone disagreement, sequential, no graphs/relations |
| Coarse cross-behavior agreement as reliability diagnostic | RMBRec's BAR statistic | One scalar per behavior per dataset — NOT per-interaction |
| Edge-level influence functions in non-convex GNNs | Heo et al. (NeurIPS 2025, [arXiv:2506.04694](https://arxiv.org/pdf/2506.04694)) | Substrate exists; "edge influence in GNNs" is not a contribution; validated only on small homogeneous node-classification graphs |
| Multi-relational graph unlearning | GraphDPO (WWW 2026, [arXiv:2507.20566](https://arxiv.org/abs/2507.20566)); FedLU (WWW 2023); MetaEU (2024) | **Never claim "first heterogeneous unlearning"** — position as relation-level influence for multi-behavior GNN recommenders |

**Refuted claims (do NOT cite these framings):**
- "UIPL occupies cross-behavior-disagreement-as-noise" — refuted 1-2 (UIPL is IRM-invariance at representation level, but the framing overlap claim did not survive).
- "RMBRec's authors declared the per-interaction cell open as future work" — refuted 0-3. Do not use.

## Risks carried forward
1. **Convergence velocity:** RMBRec (Jan 2026), DC4SR (Apr 2026), GCIB (May 2026), SpectraMB (Jun 2026) — four near-misses in seven months. **Re-screen immediately before any submission.**
2. **Feasibility unproven:** Heo et al. machinery tested on Cora-scale graphs with warm-start PBRF ground truth; per-relation extension at recommender scale is unquantified engineering risk; Basu et al. fragility critique ([arXiv:2006.14651-lineage](https://arxiv.org/abs/2210.07441)) is an available reviewer attack.
3. **The most likely collapse mode** (workflow open question #4): cheap representation-level signals (GCIB/SpectraMB-style compatibility, or plain loss ranking) capture the same noise at a fraction of the cost. The pilot's G4 gate targets exactly this.
4. **Evaluation protocol:** RecSys 2025 audit ("Are We Really Making Recommendations Robust?", [10.1145/3705328.3748153](https://dl.acm.org/doi/10.1145/3705328.3748153)) audited 12 denoising papers (2021–2025) and found a properly tuned trivial ERM baseline competitive with published denoisers. Any downstream claim must include a properly tuned ERM control. HGCLD full text unverified (paywalled) — residual risk of a buried instance-level module judged low.

## Datasets (feasibility angle, resolved locally)
Local Amazon data is single-relation — unusable for this RQ. Standard multi-behavior benchmarks obtained (scratchpad, MB-CGCN + CRGCN official releases):
- **Taobao** (MB-CGCN): 15,448 users × 11,953 items; view/cart/buy. Pilot dataset.
- **Tmall** (CRGCN): 41,738 users; click/collect/cart/buy. Scale-up.
- **Jdata** (CRGCN): 93,334 users; 4 behaviors. Scale-up.
(Provenance note: the MB-CGCN `Data/README` says "Tmall" while the literature calls this release "Taobao" — record both names in any paper artifact table.)

## Decision
Proceed to pre-registered feasibility pilot (`PREREG_CRI_PILOT_V1.md`). Large-scale program is **gated** on pilot G1–G4. The 95%-confidence checkpoint for the user sits after the pilot, not before.
