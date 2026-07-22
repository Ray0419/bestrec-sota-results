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

- [x] **E-A. Nonsingular matched-FIR factorial (audit 10:47 design adopted).**
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
  Lifecycle: [x] `PREREG_FIR_V3.md` + `adjudicate_fir_v3.py` +
  `run_ea_fir_v3.py` committed 2026-07-22 (this commit, BEFORE launch;
  preflight validated 38 flags against the trainer) -> [x] launched
  2026-07-22 immediately after this commit (sequential background driver;
  ~24 x 10 min) -> [x] adjudicated 2026-07-22: **W-POS** (A1-A0 +0.002265 [+0.001928, +0.002602], Welch t=14.4, Holm-SIG; A2-A1 +0.000010 p=.95 -> no weight-decay pathway; integrity gates passed, adjudicator exit 0)
  -> [x] integrated 2026-07-22 (frozen W-POS wording, §5.2 of the papers + PLC; historical package framing unchanged).
  Implementation: `--fir-v3 {learned,frozen}` nonsingular y=x+conv_DELTA(x),
  DELTA=0 init; unit-verified: identical cross-arm init per seed, exact
  identity at init, gradient-active at the zero point, frozen control.
- [x] **E-F. EASE late-fusion hybrid, fresh-seed confirmation (adopted from
  the R+ side campaign 2026-07-22 per maintainer instruction).** R+ found on
  MI (historical seeds, outcome-visible) that z-score late fusion with
  train-only EASE (Steck 2019) lifted test NDCG@10 from 0.04153 to
  0.04396±0.00035 (all 5 seeds; independently re-verified from raw per-user
  records). E-F is the confirmatory replication: 3 categories (MI primary;
  IS, VG secondary) x 5 FRESH seeds 20260721-25, frozen l2/w grids, val-only
  selection, paired-by-construction seq-vs-fused contrast, Holm across
  categories, +/-0.0005 equivalence margin, frozen wordings incl.
  published-comparator point-estimate rows (no SOTA wording ever).
  Office/CDs/Beauty/Books excluded (dense EASE infeasible at catalog size;
  sparse/kNN variant would need its own prereg).
  Lifecycle: [x] `PREREG_HYBRID_V1.md` + `adjudicate_hybrid_v1.py` +
  `run_ef_hybrid_v1.py` + ported `fuse_ease_eval.py`/`ensemble_fuse_eval.py`
  + trainer `--save-ckpt` committed 2026-07-22 (this commit, BEFORE launch)
  -> [x] launched 2026-07-22 chained behind E-A's GPU job (driver waits on
  `ea_fir_v3_status.json`; ran 264 min, 31/31 jobs, 0 failures) -> [x] adjudicated 2026-07-23: **W-H-POS on all three categories** (MI +0.00244 [+0.00219,+0.00268]; IS +0.00261 [+0.00211,+0.00310]; VG +0.00317 [+0.00286,+0.00348]; all Holm-SIG; W-H-PUB-MI fires: fused mean 0.04399 > published 0.0406; VG 0.07031 < 0.0760 stated honestly; ensemble5 0.04557; integrity gates passed, adjudicator exit 0)
  -> [x] integrated 2026-07-23 (papers §5.7 + Steck 2019 bib entry + PLC + README + CANONICAL post-deposit ledger; frozen-wording deviation DISCLOSED: 'pre-registered' -> 'pre-declared', the manuscript's uniform term, gate-enforced synonym).
- [ ] **E-G. Cold-start / sparse-tail fusion element (maintainer directive
  2026-07-23: "add element that help cold start or sparse dataset problem,
  keep running experiments, once there's evidence of improvement verify
  with all full datasets").** Element: training-free **text-kNN third
  scorer** (frozen MiniLM embeddings, L2-normalized; user profile =
  uniform or exp-0.9-decayed mean of input-history embeddings; score =
  profile . e_i) fused as `z(seq) + w_e z(ease) + w_t(bin) z(text)`, with
  w_t global or per TRAIN-frequency bin (tail <=5 / mid 6-20 / head >20;
  never test frequency; monotone nonincreasing in frequency per the E-D
  constraint). Needs no item-item inversion -> scales to EVERY catalog
  incl. Office/CDs/Beauty where dense EASE is infeasible, and can score
  near-zero-exposure items, which the zero-exposure study showed the
  sequential model cannot rank. Honesty anchor: the paper's zero-hit
  cold-item finding (sequential model) stands; this element is a different
  retrieval mechanism and must earn its own evidence.
  **Stage 1 (exploratory, post-hoc label):** `fuse_cold_eval.py` on TWO E-F
  MI checkpoints (seeds 20260721-22), all selection on VAL; frozen grids
  w_e {0,.02,.03,.04,.06}+selected, w_t {0,.01,.02,.05,.1,.2}; per-bin
  target-frequency NDCG reported; test evaluated once per reported system.
  **Promotion rule (VAL-only, mechanical, `run_eg_coldfuse_explore.py`):**
  promote iff on BOTH seeds some selected system has (a) val overall >=
  fused2 val overall - 0.0002 AND (b) val tail-bin NDCG@10 gain >= +0.0005.
  **Stage 2 (only if promoted): PREREG_COLDFUSE_V1** -- frozen wording +
  fresh seeds + mechanical adjudicator committed BEFORE launch; scope =
  the maintainer's full-dataset verification: MI/IS/VG (seq+EASE+text vs
  seq+EASE) AND Office_Products/CDs_and_Vinyl with new base checkpoints
  (seq+text vs seq; EASE dropped where the dense inversion is infeasible
  -- declared, not silent); per-category Holm; tail-bin co-primary
  endpoint; no SOTA wording.
  Lifecycle: [x] element + exploratory driver committed 2026-07-23 ->
  [x] stage-1 launched 2026-07-23 chained behind E-F (both seeds ran;
  driver filename fix for the precheck path, evals untouched) ->
  [x] promotion precheck 2026-07-23: **PROMOTE** (VAL rule passed on both
  seeds; binned tail gains +0.00207 / +0.00222 vs fused2, overall
  noninferior; TEST tail 0.00140->0.00374 and 0.00160->0.00336 at
  overall cost <= 0.00004 -- `eg_coldfuse_explore_verdict.json`) ->
  [x] PREREG_COLDFUSE_V1 frozen + `fuse_cold_confirm.py` (streaming, all
  catalog sizes) + `run_coldfuse_confirm.py` + `adjudicate_coldfuse_v1.py`
  committed 2026-07-23 BEFORE launch; 5 categories x 5 FRESH seeds
  20260736-40 (20260728-32 block consumed by Office V3); MI/IS/VG vs
  fused2, OFFICE/CDS vs seq (EASE infeasible, declared); co-primary
  tail-bin delta, Holm(5), tail margin +/-0.0005, cost margin -0.0005 ->
  [x] launched 2026-07-23 (~10 h sequential, resumable) ->
  [ ] adjudicate -> [ ] integrate (frozen wordings W-C-* only).
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

- 2026-07-22 (late): E-A COMPLETE -- 24/24 runs, adjudicated W-POS (+0.002265 [+0.001928, +0.002602] Holm-SIG; wd-pathway ruled out), integrated under the frozen wording; E-F launched (chained, running).

- 2026-07-22: E-A/E-B/E-C/E-D specs upgraded to the audit 10:47 factorial /
  multi-map / training-parity / constraint designs; E-C2 added.


- 2026-07-21: file created; maintainer authorization recorded; v6 cron job
  installed (hourly, `codex-audit-responder-v6`).
