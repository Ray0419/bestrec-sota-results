# EXPERIMENT_PROGRAM.md — maintainer-authorized improvement experiments (2026-07-21)

Maintainer directive (2026-07-21): respond to the hourly audits, improve the work
either by own judgment or per audit suggestions, and "don't hesitate to change the
algorithm if during the review you find a new way that could possibly improve the
result." This file is the durable worklist the quiet-tick loop services (priority A).

## Standing rules (inherit the loop's HARD RULES)

- ONE GPU job at a time (`nvidia-smi` before every launch); sequential background
  queue across ticks; append-only logs; never overwrite `results_*.json`
  (rename-preserve only); never touch `external/HSTU-BLaIR`.
- Exploratory development probes are allowed and always labeled
  post-hoc/exploratory. Anything claim-bearing requires a NEW pre-registration:
  frozen claim wording + seeds + config + decision rule, AND the mechanical
  adjudicator, committed BEFORE launch (committed-before-existence standard,
  manuscript §5.3 disclosure (ii)). Existing claims still only narrow.
- Negative and failed-improvement outcomes are integrated with the same
  prominence as wins (negative-result map discipline).
- Integration path: results → `build_hstu_tables.py` cells → full ritual
  (render CLEAN, build.sh PASS H1–H10, manifest --regen, strict exit 0) → papers.

## Worklist (top unchecked item first; one lifecycle stage per tick is fine)

- [ ] **E-A. Nonsingular matched-FIR factorial (audit 10:47 design adopted).**
  Question: does learnable causal FIR filtering add value separate from the
  gate/initialization/optimizer package? Design (E-A1 + E-A2): represent the
  kernel as `delta + DELTA` with `DELTA=0` init and the residual multiplier
  FIXED at 1 for the primary contrast (gradient-active from step 0 — no
  zero-gradient gate); arms = learned-DELTA vs identity/1-tap control in the
  same block; factorial cross with weight decay {on, off}; secondary factorial:
  learned-vs-fixed gate. **Common random numbers:** one backbone checkpoint
  cloned to every arm; identical data order, dropout streams, parameter groups,
  stopping rule, checkpoint cadence. Diagnostics: per-step gate/tap gradients,
  impulse/frequency responses, optimizer moments, parameter/FLOP deltas, all
  checkpoints. MI, 20-epoch frozen config, 5 fresh pre-declared seeds/arm.
  Lifecycle: [ ] `PREREG_FIR_V3.md` + adjudicator committed -> [ ] launch ->
  [ ] adjudicate -> [ ] integrate.
- [ ] **E-B. Frequency-stratified item-text permutation + random-feature
  control (audit 10:47 design adopted).** Freeze SEVERAL independent permutation
  maps before training (map uncertainty is real); permute within
  train-frequency bins (frequency 5 especially); cross permutation-map draws
  with optimizer seeds; add a dimension-matched random/orthogonal-feature arm
  so aligned text separates from generic capacity/regularization. Decisive
  contrast: aligned vs frequency-matched permuted text, same split, frequency-5
  interaction pre-declared. No content-mechanism prose until this runs.
- [ ] **E-C. TRAINING-target multiplicity parity (corrected per audit 10:47:
  evaluation already has one held-out test target per user — the open parity
  question is training).** Audit and, if needed, rerun a next-target-only vs
  all-position training factor under the same evaluation universe (example
  construction, masking, loss weighting documented per arm).
- [ ] **E-C2. Thinning-draw replication.** Re-run the interaction-thinning
  ladder across independently sampled subset draws; current intervals condition
  on ONE fixed draw.
- [ ] **E-D. Frequency-conditioned text gate (own-judgment lane; audit 10:47
  constraints adopted: run only AFTER E-A/E-B; train-frequency only — never
  test frequency; monotone/regularized gate; held-out development rule;
  pre-declared head-harm constraint; the frequency-5 finding must never tune
  anything on test).** Stage 1 exploratory (2 seeds MI, labeled post-hoc);
  promote to prereg only on band-consistent dev signal.
- [ ] **E-E. AlphaFuse benchmark-or-exclusion (closest omitted comparator).**
  Adapt the released AlphaFuse code to AR2023 5-core full-catalog LLOO
  (MI first). If the protocol port is infeasible under documented constraints,
  write the executable exclusion note the audits accept instead. Largest item;
  start only when E-A/E-B are queued or done.

## Log

- 2026-07-22: E-A/E-B/E-C/E-D specs upgraded to the audit 10:47 factorial /
  multi-map / training-parity / constraint designs; E-C2 added.


- 2026-07-21: file created; maintainer authorization recorded; v6 cron job
  installed (hourly, `codex-audit-responder-v6`).
