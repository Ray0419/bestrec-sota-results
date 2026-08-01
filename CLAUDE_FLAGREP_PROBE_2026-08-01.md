# CLAUDE — Flag-replication exploratory probe result — 2026-08-01

**Status: EXPLORATORY (not pre-registered; no confirmatory claims).** Run to calibrate the headline uncertainty of the planned seed-stability audit (Candidate A of the 2026-08-01 screening, task `wqnz0f2qa`), per that screening's own recommendation. Code: `experiments/flagrep_pilot/run_flagrep.py`; artifacts: `experiments/flagrep_pilot/results/`.

## Setup (deliberately minimal)
ADT/T-CE-style truncated-loss denoising (linear ramp to 20% drop rate) on an MF-BCE backbone (d=64, 4 negatives, 30 epochs), Taobao `buy` (92,180 edges) + 10% popularity-matched injected noise (bit-identical injection to the CRI pilot's popularity arm), seeds {13, 42, 2026}. Flags = top-10% by drop frequency over final 10 epochs; contrast = top-10% by plain mean loss (no truncation). Total wall time 41 s on M4 Max.

## Result
| | T-CE flags | plain-loss flags | random |
|---|---|---|---|
| cross-seed flag Jaccard (3 pairs) | .071 / .109 / .071 | .063 / .063 / .063 | .053 |
| cross-seed score Spearman | .389 / .411 / .392 | .012 / .013 / .015 | 0 |
| injected-noise capture precision @10% | 0.0 (all seeds) | .091–.099 (≈ base rate) | .092 |
| detection AUC vs injected | .500–.504 | .506–.507 | .500 |

## Reading (exploratory)
1. **Flag sets do not replicate.** Plain-loss flags are indistinguishable from random subsets (Jaccard .063 vs .053); the loss ranking itself is trajectory-dominated (ρ≈.013). T-CE's truncation feedback partially self-stabilizes the *score* (ρ≈.39 — path dependence + a persistent always-dropped set) but flag overlap stays near random.
2. **The one replicable property is a systematic miss:** 0/9,218 popularity-matched fakes captured, all seeds — truncation drops high-loss niche edges while popularity-shaped noise sits in the low-loss region. "Stable-in-aim, random-in-detail, aimed away from popularity-shaped noise."
3. Parallels the CRI pilot refutation (per-edge trajectory noise dominance) and the general-ML fragility stack — but here for **loss-based** flags, which the screening flagged as the genuinely uncertain case.

## Caveats (all material)
- One backbone (simplified MF-BCE, not the papers' GMF/NeuMF with their schedules), one dataset, one noise model, one operating point. Official-code reproduction may be materially more stable — this is the audit's first task, not an afterthought.
- Popularity-matched injection makes capture≈0 partly definitional (low-loss by construction); uniform/exposure noise arms are needed.
- Headline replication claim requires NO injected noise (measurable on clean data) — the audit should lead with clean-data replication and use injection only for the "what do flags select" arm, sidestepping the synthetic-noise critique.

## Disposition
Probe supports Candidate A's strong-headline branch. Draft prereg: `PREREG_FLAGREP_AUDIT_V1_DRAFT.md` — **DRAFT, not frozen; user go/no-go pending** per the standing 95%-checkpoint rule.
