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
  (render CLEAN, build.sh PASS H1–H9, manifest --regen, strict exit 0) → papers.

## Worklist (top unchecked item first; one lifecycle stage per tick is fine)

- [ ] **E-A. Nonsingular matched-FIR + weight-decay control (the attribution
  blocker; every audit since 19:56 demands it).** Question: is the FIR gain the
  filter mechanism or the initialization/optimizer package? Design: Musical
  Instruments, 20-epoch frozen config, 5 fresh never-inspected seeds per arm.
  Arms: (1) full filter, nonsingular common parameterization (gate g init 1.0,
  delta kernel — removes the zero-gradient start); (2) no-filter baseline,
  identical init/optimizer path; (3) full filter, singular start (current
  parameterization) with `weight_decay=0` — if learning never bootstraps, the
  §3 mechanism account is confirmed causally. Endpoint: overall NDCG@10 Welch
  (1) vs (2); secondary: (3)'s gate/kernel trajectory. ~15 GPU runs. Lifecycle:
  [ ] design frozen in `PREREG_FIR_V3.md` + adjudicator committed → [ ] launch
  → [ ] adjudicate → [ ] integrate.
- [ ] **E-B. Item-text permutation control (semantic-attribution test the
  manuscript itself calls provisional).** Question: does the text stack's
  benefit (overall +2.7% VG; MI freq-5 tail) require semantically ALIGNED text,
  or only the extra parameters/regularization? Design: permute the item→text-
  embedding assignment within category (marginals preserved), rerun the text arm,
  MI + VG, 5 seeds each. If permuted ≈ aligned, semantic attribution is refuted
  (and the paper narrows further — that is a win for the paper either way).
  ~10 GPU runs. Prereg `PREREG_TEXTPERM.md` before launch.
- [ ] **E-C. Eval-geometry / target-multiplicity parity control.** Question: does
  any part of the MI-vs-VG contrast trace to evaluation-population geometry
  (user/target multiplicity) rather than the model? Design: recompute both arms'
  metrics on parity-enforced target sets (single-target-per-user subsample,
  seeded); CPU-only sidecar reanalysis — no training. Cheap; prereg the rule.
- [ ] **E-D. NEW ALGORITHM PROBE — frequency-conditioned text gate (own-judgment
  lane, motivated by the paper's own frequency-5-heavy finding).** Hypothesis:
  if frozen-text benefit concentrates at the low-frequency boundary band, an
  explicit train-frequency-conditioned gate on the text pathway (per-item scalar
  from a small frequency-bucket embedding, zero-init NON-singular) could amplify
  tail benefit without hurting the head. Stage 1 exploratory: 2 seeds MI
  (labeled post-hoc); promote to prereg only if the dev signal is
  band-consistent. Honest failure mode: another Table-2 row — acceptable.
- [ ] **E-E. AlphaFuse benchmark-or-exclusion (closest omitted comparator).**
  Adapt the released AlphaFuse code to AR2023 5-core full-catalog LLOO
  (MI first). If the protocol port is infeasible under documented constraints,
  write the executable exclusion note the audits accept instead. Largest item;
  start only when E-A/E-B are queued or done.

## Log

- 2026-07-21: file created; maintainer authorization recorded; v6 cron job
  installed (hourly, `codex-audit-responder-v6`).
