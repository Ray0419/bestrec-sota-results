# PRE-REGISTRATION — fresh-seed confirmation of the Musical_Instruments per-category SOTA claim

**Written:** 2026-07-06, BEFORE launching any run listed here. This document is the pre-registered
protocol; it is append-only after launch (results get appended below, the protocol text is frozen).

## Motivation (audit Finding 4)

Existing evidence: MI V2-stack k16, 5 seeds {20260608–12} → NDCG@10 = 0.04153 ± 0.00018, every seed
above the published HSTU-BLaIR MI target **0.0406** (Liu 2025, arXiv:2504.10545, single seed, same
AR2023 5-core LLOO full-catalog protocol). The independent statistical audit (2026-07-06) flagged
this as tainted: K was promoted 8→16 *after* observing per-seed comparisons against 0.0406, and
k16 vs k8 is statistically indistinguishable (Welch p=0.49). The cure is a confirmation on seeds
never used in ANY tuning or selection decision.

## Frozen protocol

- **Dataset/protocol:** AR2023 Musical_Instruments, 5-core, leave-last-out, full-catalog masked
  eval, NDCG@10, n_eval=57,439 (all users), best-by-val (val = overall NDCG@10), identical
  preprocessing to all prior runs. No code changes between arms.
- **Frozen config (verbatim from `results_MI_V2_ls02_filter16_seed20260608.json`):** epochs 20,
  batch 256, d_model 64, n_layers 4, n_heads 2, dropout 0.5, lr 1e-3 warmup_cosine, encoder hstu,
  chunked-full-softmax (item-chunk 32768), time-bias, text-sim-bias, text-prototypes 512, pos-rab,
  label-smoothing 0.2, causal-filter kernel **16**, eval-every 1.
- **Fresh seeds:** 20260613, 20260614, 20260615, 20260616, 20260617 — disjoint from every seed
  ever used in tuning/selection on MI (20260608–12). Chosen as the next consecutive integers
  (no seed shopping possible).
- **Secondary robustness arm (non-gating):** identical config with filter-kernel **8** on the same
  fresh seeds.

## Pre-registered decision rule (declared before results)

- **PRIMARY GATE (k16 fresh arm):** the two-sided 95% CI lower bound of the fresh 5-seed mean
  (mean − t₀.₉₇₅,₄ · sd/√5, t₀.₉₇₅,₄ = 2.776) must exceed **0.0406**.
- **SECONDARY:** at least 4 of 5 fresh seeds individually > 0.0406.
- **If PRIMARY passes:** the claim "exceeds the published HSTU-BLaIR number on AR2023
  Musical_Instruments under the same protocol (multi-seed, selection-free confirmation)" is
  declared supported, and a scoped SOTA_ACHIEVED.md is written after a strict-review checklist
  (masking/leakage/n_eval/attribution re-verified — already covered by the six-audit sweep of
  2026-07-06, which found the underlying pipeline leak-free and numbers exact).
- **If PRIMARY fails:** the claim is downgraded permanently to "statistical near-tie with the
  published single-seed 0.0406"; no SOTA claim; result recorded either way.

## Honest caveats that will accompany ANY claim

1. The published comparator is **single-seed** with unknown variance; our claim is that our
   multi-seed mean and CI exceed *the published number*, not a distributional comparison.
2. Split parity evidence: our preprocessing matches the official kcore script; our VG SASRec
   reproduces published VG SASRec within 4%; floor check — our plain MI SASRec (0.0264) is BELOW
   their published MI SASRec (0.0356), so our split is not easier.
3. VG remains explicitly NOT a SOTA claim (0.0673 < published 0.0760; hardware-blocked kernels).
4. k16-vs-k8 remains statistically indistinguishable; k16 is claimed only as "a configuration
   that clears the bar under selection-free confirmation," not as superior to k8.

## Results (appended after runs complete — protocol above frozen at launch)

**2026-07-06 — PRIMARY ARM COMPLETE. GATE: PASS.**

k16 fresh seeds (never used in tuning), full-catalog n_eval=57,439 every run:

| seed | NDCG@10 | HR@10 | > 0.0406 |
|---|---|---|---|
| 20260613 | 0.04111 | 0.07429 | ✓ |
| 20260614 | 0.04184 | 0.07542 | ✓ |
| 20260615 | 0.04177 | 0.07424 | ✓ |
| 20260616 | 0.04161 | 0.07521 | ✓ |
| 20260617 | 0.04122 | 0.07443 | ✓ |

- **Fresh 5-seed: mean 0.04151, sd 0.00033, 95% CI [0.04111, 0.04191].**
- **PRIMARY GATE: PASS** — CI lower bound 0.04111 > 0.0406 (margin of the *lower bound* itself: +1.26%).
- **SECONDARY: PASS** — 5/5 fresh seeds individually > 0.0406 (worst +1.26%, mean +2.24%).
- Pooled 10-seed (5 tuning + 5 fresh): **0.04152 ± 0.00025**.
- Files: `_bestrec_run/results_SOTACONF_k16_MI_seed2026061{3-7}.json` (+ logs).
- **k8 robustness arm (non-gating) — COMPLETE, ALSO CLEARS THE GATE:** fresh seeds
  {0.04155, 0.04197, 0.04162, 0.04173, 0.04108} → mean **0.04159 ± 0.00033**, 95% CI lower bound
  **0.04118 > 0.0406**, 5/5 seeds individually clear. The claim is therefore **kernel-robust**:
  both k8 and k16 exceed the published number under selection-free confirmation — the original
  k16-selection concern is fully dissolved (the result does not depend on the kernel choice).
  Files: `_bestrec_run/results_SOTACONF_k8_MI_seed2026061{3-7}.json`.

Per the pre-registered decision rule, the claim **"exceeds the published HSTU-BLaIR number on AR2023
Musical_Instruments under the same protocol (multi-seed, selection-free confirmation)"** is declared
SUPPORTED, with the four caveats above attached verbatim. → `SOTA_ACHIEVED.md`.
