# PREREG_TEXTPERM_V1 — E-B: Training-Level Text-Permutation and Random-Feature Controls (FROZEN; CLOUD EXECUTION DECLARED)

**Status: FROZEN at commit time; committed BEFORE any run is launched.
Analysis and integration ONLY through `_bestrec_run/adjudicate_textperm_v1.py`
and the frozen wordings in §5. Claims may only narrow; no SOTA wording.**

Registered: 2026-07-23. **Execution environment (declared prospectively):
rented cloud GPU pods (RunPod), sharded by `cloud/make_shards_eb.py` and
executed by `cloud/run_shard.py`; per-run environment (hostname, GPU, torch/
CUDA, commit, dirty-diff SHA) is captured in the shard ledgers; environment
is NOT a frozen parameter and heterogeneous pods are permitted. Maintainer
parallelism directive 2026-07-23 applies.**

## 1. Question

Does the TRAINED text stack's benefit require semantically ALIGNED item text,
or does frequency-matched permuted text (same marginal embedding
distribution per train-frequency bin) or generic random features reproduce
it? This is the training-level counterpart of E-G2's evaluation-time C2/C3
controls, addressing the audits' standing "no content-mechanism prose until
this runs" constraint.

## 2. Design (frozen)

- Categories and frozen base references: MI
  (`results_MI_V2_ls02_filter16_seed20260608.json`) and VG
  (`results_V2_ls02_filter8_seed20260610_VG.json`).
- Arms (training-level; every run `--no-test-eval --save-ckpt`; command
  constructed mechanically from the reference config minus
  seed/out/encoder_cache):
  - **aligned**: the canonical MiniLM title cache (reference behavior);
  - **permA/permB/permC**: `--encoder-cache` pointing at a within-train-
    frequency-bin row permutation of the canonical cache (bins f0 / f1–5 /
    6–20 / >20; map rngs 1001/1002/1003; generator
    `cloud/make_control_caches.py`, deterministic across platforms — the
    adjudicator re-derives the caches locally and hash-matches every run's
    recorded `cache_sha256`);
  - **random**: dimension/dtype-matched N(0,1) rows (rng 2001).
- Optimizer seeds: **20260749, 20260750, 20260751** (3 per arm-cell; fresh).
- 30 training pipelines total; each followed by the sequestered
  `cloud/eval_final_model.py` single test pass (four-bin: f0 / f1–5 / mid /
  head; metric values never printed; the adjudicator is the first reader).
- Test sequestration is structural (`best_test = null` in every base JSON).

## 3. Endpoints and analysis (frozen)

Per category: `f15(aligned)` (n=3) vs `f15(permuted)` (n=9, three maps
pooled; map identity recorded) via two-sided Welch t; **primary family =
{MI, VG} aligned-vs-permuted, Holm(2), α=0.05**. Secondary (reported with
CIs, no test): aligned-vs-random, overall/mid/head/f0 deltas, per-map
means. Exact-test note: with 3v9 the design leans on effect size; the MDE
is large (≈1 seed-SD × 2.5) and W-TP-INC is the expected outcome unless
alignment carries a large share of the trained-text effect — stated here so
an inconclusive result cannot be spun. Margin for W-TP-PERMEQ: ±0.0005 on
the f1–5 difference. CIs are optimizer-seed intervals conditional on the
standard fixed split.

## 4. Integrity gates (adjudicator-enforced)

1. Exactly the 30 declared base + 30 finaleval files; undeclared extras
   fail. 2. Sequestration proof per base (`best_test = null`). 3. Cache
   provenance: adjudicator regenerates all control caches locally with the
   frozen rngs and hash-matches each run's recorded `cache_sha256`; the
   aligned arm's sha must equal the canonical cache's. 4. Config echo vs
   reference minus {seed, out, save_ckpt, no_test_eval, encoder_cache,
   fir_v3*}; extras value-checked against the same-era IS reference.
   5. NPZ: unique sorted users; overall/f15 reconstruction ≤1e-6.
   6. `best_ckpt_sha256` present; shard ledgers present with env capture.
   7. SciPy required; zero-SD refusal; exact binomial sign test reported.

## 5. Frozen outcome wordings

- **[W-TP-SEM]** Holm-significant aligned>permuted on {C}: "Under the
  pre-declared training-level control study (PREREG_TEXTPERM_V1), aligned
  item text exceeded frequency-matched permuted text on the f1–5 endpoint
  by {est} [{ci}] on {C}; semantic alignment contributes at training time
  beyond a frequency-matched text prior on this category."
- **[W-TP-PERMEQ]** CI within ±0.0005: "…aligned and frequency-matched
  permuted text were indistinguishable at the ±0.0005 margin on {C}; the
  trained-text benefit on this category is not attributable to semantic
  alignment at this precision."
- **[W-TP-INC]** otherwise: "…inconclusive at the available precision
  ({est} [{ci}]; 3v9 design, MDE stated in the pre-declaration)."
- Random-arm and overall/mid/head findings are reported descriptively with
  CIs under **[W-TP-CTRL]**; no cold-start language (f0 tracked, expected
  null); no component claim beyond the wordings above.

## 6. Budget

≈8.2 GPU-hours total (MI ≈16 min + VG ≈15 min per pipeline incl. final
eval). On 8 pods ≈ 65 min wall; on 4 pods ≈ 2.2 h. Results return as one
hashed tar per shard (`cloud/run_shard.py`); the adjudicator verifies
SHA256SUMS before reading anything.
