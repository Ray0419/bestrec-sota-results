> **ERRATUM (2026-07-20).** The frozen decision rule this record adjudicates is a paired
> Student-t whose pairing premise is now known to be false: same-numbered seeds are not
> initialization-paired (the optional Conv1d is constructed before the shared encoder;
> manuscript §5.3). The 'CONFIRMED' verdicts below stand as mechanical outcomes of the
> frozen rule executed as written; their **paired interpretation is withdrawn**, and the
> manuscript's primary analysis is the independent-arm Welch (both 95% CIs exclude zero;
> graphed as `firb.*.welch`, exploratory class). This record is preserved unmodified below.

# FIR-BREADTH campaign results (PREREG_FIR_BREADTH.md)

Mechanical adjudication blocks appended by `_bestrec_run/adjudicate_fir_breadth.py`.
Decision rule (frozen before any run): per category, paired 5-seed
d_s = filter - nofilter on best-by-val FULL-catalog NDCG@10; CONFIRMED iff the
two-sided 95% Student-t CI excludes 0 AND >=4/5 seeds are positive; NULL
otherwise; VOID on protocol violation. Nulls are published with the same
prominence as confirmations.

---

## Adjudication 2026-07-13 06:44:54 (block-id 9a38ad66bd75)
Seeds [20260713, 20260714, 20260715, 20260716, 20260717]; rule frozen in PREREG_FIR_BREADTH.md.

### Industrial_and_Scientific -- **CONFIRMED**
- n_users (full-catalog n_eval, all 10 runs) = 50,985; test.csv rows = 50,985
- seed 20260713: filter 0.03377  nofilter 0.03134  d = +0.00243
- seed 20260714: filter 0.03341  nofilter 0.03145  d = +0.00196
- seed 20260715: filter 0.03294  nofilter 0.03103  d = +0.00191
- seed 20260716: filter 0.03343  nofilter 0.03057  d = +0.00287
- seed 20260717: filter 0.03379  nofilter 0.03095  d = +0.00284
- paired d: mean +0.00240  sd 0.00046  95% t-CI [+0.00183, +0.00297]  positive seeds 5/5
- rule: CI excludes 0 -> True; >=4/5 positive -> True
- frozen claim wording applies: "the causal FIR filter's paired 5-seed improvement on Industrial_and_Scientific (transplanted with zero per-category tuning) is positive with a 95% CI excluding zero." Nothing broader; no SOTA language; no comparator statement.

### CDs_and_Vinyl -- **CONFIRMED**
- n_users (full-catalog n_eval, all 10 runs) = 123,876; test.csv rows = 123,876
- seed 20260713: filter 0.06617  nofilter 0.06078  d = +0.00539
- seed 20260714: filter 0.06626  nofilter 0.05988  d = +0.00638
- seed 20260715: filter 0.06608  nofilter 0.05991  d = +0.00617
- seed 20260716: filter 0.06599  nofilter 0.06101  d = +0.00498
- seed 20260717: filter 0.06589  nofilter 0.06049  d = +0.00540
- paired d: mean +0.00566  sd 0.00059  95% t-CI [+0.00493, +0.00639]  positive seeds 5/5
- rule: CI excludes 0 -> True; >=4/5 positive -> True
- frozen claim wording applies: "the causal FIR filter's paired 5-seed improvement on CDs_and_Vinyl (transplanted with zero per-category tuning) is positive with a 95% CI excluding zero." Nothing broader; no SOTA language; no comparator statement.

**Campaign verdicts:** Industrial_and_Scientific: CONFIRMED; CDs_and_Vinyl: CONFIRMED

## Data boundary (release/deposit; added 2026-07-13)

- The raw rating archives (`data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`) are **local downloads of the public
  Amazon Reviews 2023 release** and are intentionally untracked — the repository does not
  redistribute raw AR2023 data (same policy as the four original categories).
- The derived 5-core LLOO splits are likewise untracked but **fully pinned**: every tracked
  run JSON (`_bestrec_run/results_FIRB_*.json`, 20 files) embeds the exact split SHA256s under
  `provenance.data_sha256` (train/valid/test), and the preprocessing code that regenerates
  them from the public raw files is tracked. Dataset identity for every printed breadth cell
  is therefore byte-verifiable without raw-data redistribution.
- Per-user evaluation sidecars for these runs remain local-only with SHA256s embedded in each
  run's tracked manifest, under the same deposit policy as Office V3 (paper §8): provided on
  editorial/reviewer request; deposited as supplementary material upon acceptance.
