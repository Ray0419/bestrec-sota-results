# PREREG_COLDFUSE_V2 — E-G2: Independent Test-Sequestered Replication of the Sparse-Warm Text-Fusion Finding (FROZEN)

**Status: FROZEN at commit time; committed BEFORE any run is launched.
Analysis and integration ONLY through `_bestrec_run/adjudicate_coldfuse_v2.py`
and the frozen wordings in §7. Claims may only narrow; no SOTA wording. This
is the registered replication that audit 2026-07-23 15:59 required after the
E-G campaign was reclassified outcome-visible/protocol-deviated; every P0/P1
defect of that campaign has a structural countermeasure here.**

Registered: 2026-07-23. Maintainer parallelism directive (2026-07-23,
verbatim intent: "speed up and run more things simultaneously, we have a lot
of cpu/gpu/npu resources idle") is recorded and implemented as a TWO-LANE GPU
schedule; parallelism changes wall-clock only, never analysis.

## 1. Question

Does validation-selected, evaluation-time, history-centroid text fusion
produce a positive **f1–5** (train frequency 1..5) test NDCG@10 change,
relative to the per-category reference system, on fresh optimizer seeds,
under guardrails that forbid buying the tail with mid/head or overall
losses — and is the effect attributable to ALIGNED text rather than to a
frequency prior or generic feature noise (control arms)?

## 2. Structural countermeasures to the E-G deviations

1. **No interim looks, enforced by design, not promise:** training runs use
   `--no-test-eval` (the test split is never scored during training;
   `best_test` is null — an auditable sequestration proof in every base
   JSON); fusion selection uses `--val-only` (no test pass); the confirm
   evaluator `fuse_cold_confirm2.py` writes test metrics ONLY to artifacts
   and prints none. The committed adjudicator is the first reader of any
   test value. Progress monitoring = file counts and ledger events only.
2. **Config gate written prospectively in its normalized, value-checked
   form** (§6.2) and enforced by the committed adjudicator; the literal
   union-equality reading is not used, by declaration, from the start.
3. **OPS:** append-only JSONL ledger with launch commit + dirty-diff SHA-256
   + per-phase events; atomic status writes; atomic (temp+rename)
   checkpoint saves; `best_ckpt_sha256` recorded in every base JSON;
   skip-if-exists resume; per-launch dirty patch snapshot.
4. **f0 removed from every benefit endpoint** (separate diagnostic bin).
5. **Grid bracketed prospectively** above the prior ceiling (motivated by
   the PRIOR campaign's validation ceilings, not this study's data).

## 3. Design (frozen)

- Categories and frozen base references: identical to PREREG_COLDFUSE_V1's
  table (MI/IS/VG with the E-F fused reference; OFFICE/CDS with the
  sequential reference; dense-EASE exclusion carried forward, declared).
- **Eight fresh seeds per category: 20260741–20260748** (verified unused).
- Pipeline per (category, seed): train base (`--no-test-eval --save-ckpt`,
  mechanical config from the reference minus seed/out) → MI/IS/VG:
  `fuse_ease_eval.py --val-only` (frozen grids l2 {50,100,200,500} ×
  w {0.01..0.1}; selection on validation; no test pass) →
  `fuse_cold_confirm2.py` (sequestered).
- Two GPU lanes (A: MI, IS; B: VG, OFFICE, CDS), each sequential inside.
- Candidate grid: profiles {uniform, exp0.9} × monotone triples
  (w_tail, w_mid, w_head), w_tail ∈ {0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.6},
  w_mid, w_head ∈ {0, 0.05, 0.1}, w_tail ≥ w_mid ≥ w_head (84 candidates).
- **Selection (VAL only): maximize val f1–5 NDCG@10 subject to ALL
  guardrails:** overall ≥ ref − 0.0002, mid ≥ ref_mid − 0.0010, head ≥
  ref_head − 0.0005. If no candidate is feasible, the reference is selected
  and the category records a structural null.
- **Control arms**, evaluated once on TEST at the selected policy (no
  selection of their own): C1 frequency-only additive prior (selected
  weights, no text feature); C2 dimension-matched random features (frozen
  rng 12345); C3 within-frequency-bin permuted text (frozen rng 12345);
  C4 pure-text diagnostic. Frozen control rng: 12345.
- Test evaluated ONCE per seed for reference + selected + C1–C4.
- The split limitation is declared: the test partitions are the standard,
  historically exposed fixed splits; sequestration removes fresh exposure
  in THIS campaign but cannot un-expose history. A temporal/catalog-arrival
  holdout is registered as future work (E-G2b), not claimed here.

## 4. Endpoints and analysis (frozen)

Per category, per seed: `f15_delta = test.SEL.f15 − test.REF.f15`;
`overall_delta`, `mid_delta`, `head_delta`, `f0` values recorded.

- **Co-primary (per category): mean f15_delta**, two-sided paired t
  (df = 7), **Holm across the five categories**; α = 0.05. Exact two-sided
  binomial sign test reported alongside (n = 8 floor: 0.0078 — the exact
  test can now reject on unanimity).
- **Equivalence margin (f15): ±0.0005.**
- **Cost gates (reported per category; wording-conditioning):** overall CI
  lower bound > −0.0005; mid CI lower bound > −0.0015; head CI lower bound
  > −0.0008.
- **Attribution contrasts (frozen secondary):** per category, paired t on
  (SEL − C3_permuted) f15 deltas and (SEL − C2_random) f15 deltas;
  C1_freqonly's share = mean(C1 − REF f15) / mean(SEL − REF f15).
- **Semantic falsification rule (frozen):** if on ≥3 of 5 categories the
  permuted arm achieves ≥50% of the selected arm's f15 delta, the
  semantic-alignment interpretation is WITHDRAWN (wording W2-SEM-FAIL) and
  only a frequency-prior effect may be described.
- CIs are optimizer-seed intervals conditional on the fixed split; they are
  labeled as such wherever printed.
- No interim analyses; the adjudicator runs once after all 40 confirm files
  exist.

## 5. Integrity gates (adjudicator-enforced; prospectively frozen)

1. Exact artifact sets: 40 base + 24 fusion (MI/IS/VG) + 40 confirm files
   with exactly the declared names/seeds; undeclared extras are a failure.
2. **Sequestration proof:** every base JSON has `best_test = null`; every
   MI/IS/VG fusion JSON has `val_only = true` and `test = null`.
3. Config echo (normalized, value-checked, prospective): reference-key
   equality minus {seed, out, save_ckpt, no_test_eval, fir_v3*}; extra keys
   must equal the same key's value in the same-era IS reference config and
   be identical across all runs.
4. Candidate-set identity (84 frozen keys) + finiteness of every sweep
   value; guardrail-constrained argmax recomputed from the recorded sweep
   and required to equal the recorded selection.
5. NPZ: unique sorted users; four-bin membership; overall/f15 aggregate
   reconstruction ≤ 1e-6 for every recorded system.
6. `best_ckpt_sha256` present in every base JSON; ledger
   (`attempts/eg2_ledger.jsonl`) contains a campaign_launch event with
   commit + dirty-diff SHA and one done event per non-skipped step.
7. Zero-SD refusal; SciPy required; exact binomial sign test.

## 6. Frozen outcome wordings (the ONLY sentences that may enter the paper)

Per category C with mean f15 delta {est} [{ci}]:

- **[W2-POS]** Holm-significant positive AND all three cost gates pass:
  "Under the test-sequestered fresh-seed replication (PREREG_COLDFUSE_V2,
  8 seeds), the frequency-binned text scorer changed f1–5 test NDCG@10 on
  {C} by {est} [{ci}] (Holm-corrected paired t across five categories;
  exact sign p = {sp}), with overall/mid/head changes inside the
  pre-specified guardrails. Frequency-0 targets are excluded from the
  endpoint and remained a complete retrieval failure. Intervals are
  optimizer-seed intervals conditional on the standard fixed split."
- **[W2-POS-COST]** Holm-significant positive but any cost gate fails: as
  W2-POS with "…but the {overall|mid|head} cost gate failed
  ({values}), so the redistribution cost is stated as exceeding the
  pre-specified limit."
- **[W2-NEG] / [W2-EQUIV] / [W2-INC]**: analogous to V1's forms on the
  f1–5 endpoint with margin ±0.0005.
- **[W2-SEM-FAIL]** (family-level): "Permuted-text controls achieved ≥50%
  of the selected arm's f1–5 effect on {k} of 5 categories; the
  semantic-alignment interpretation is withdrawn and the result is
  described as a frequency-prior effect only."
- **[W2-CTRL]** (family-level, always printed): "Attribution: the
  frequency-only prior accounts for {share}% of the selected arm's f1–5
  effect on average; random-feature and permuted-text contrasts are
  {summary}."
- Standing: no SOTA wording; no cold-start language (f0 excluded and
  null); the E-G descriptive study remains classified as before; this
  campaign alone can grant the sparse-warm finding counted status.

## 7. Budget and operations

Two-lane wall-clock ≈ max(lane A ≈ 8×(13+8+~8) min ≈ 3.9 h, lane B ≈
8×(40+14+12+~15) min ≈ 10.8 h) ≈ 11 h. EASE fits served by the verified
cache after first computation per (category, λ). Driver:
`run_eg2_parallel.py`; resumable; failure aborts a lane after 3 errors.
Progress checks during the campaign are restricted to file counts and
ledger events (no endpoint values exist outside artifacts until
adjudication).
