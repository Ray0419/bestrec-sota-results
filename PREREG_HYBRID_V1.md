# PREREG_HYBRID_V1 — E-F EASE Late-Fusion Hybrid, Fresh-Seed Confirmation (FROZEN)

**Status: FROZEN at commit time; committed BEFORE any run is launched
(lifecycle rule in `EXPERIMENT_PROGRAM.md`). Analysis and paper integration
happen ONLY through `_bestrec_run/adjudicate_hybrid_v1.py` and the frozen
wordings in §7. Per the standing claim-boundary rule, results may only NARROW
the paper's claim set; this pre-registration is the sole doorway for any new
hybrid claim. No SOTA wording under any outcome (standing FORBIDDEN list).**

Registered: 2026-07-22. Author-operated automation; mechanical adjudication.

## 1. Provenance and question

The R+ side campaign (author-operated, `Desktop\R+`, 2026-07-22) found on
Musical_Instruments that late z-score fusion of the paper's frozen sequential
stack with a train-only closed-form EASE model (Steck 2019) improved test
NDCG@10 on all 5 historical seeds (mean 0.04396 vs 0.04153; independently
re-verified from raw per-user records). Those runs are **outcome-visible
development** (many probes evaluated on test during that campaign, historical
seeds). This pre-registration is the confirmatory replication with FRESH
seeds, plus two extension categories, under frozen grids and selection rules.

Question: does per-user z-score late fusion with train-only EASE
(`fused = z(seq) + w·z(ease)`, (l2, w) selected on validation only) change
test NDCG@10 at the best-validation checkpoint of the frozen per-category
stack, on seeds never used before?

## 2. Tooling (committed with this file)

- Trainer `--save-ckpt` (best-val weights; ported from R+).
- `_bestrec_run/fuse_ease_eval.py` — per-seed fusion: EASE fit on the 5-core
  TRAIN split only; per-user z-normalization; input-history masking in every
  scorer; val-only (l2, w) selection; single test evaluation at the selected
  pair; per-user paired records written. Ported from R+ with the base import
  switched to `run_sasrec_sbert` (R+ verified this reconstruction reproduces
  recorded results to 6 decimals; adjudicator gate §6.4 re-checks per run).
- `_bestrec_run/ensemble_fuse_eval.py` — MI-only secondary endpoint.
- `_bestrec_run/run_ef_hybrid_v1.py` — sequential driver, chained behind the
  E-A GPU job; skip-if-exists; mechanical command construction from the
  frozen per-category reference configs.

## 3. Design (frozen)

Categories, base stacks (mechanically reproduced from these reference
results JSONs, minus seed/out), and runtimes:

| Tag | Category | Frozen reference (config source) | Epochs |
|---|---|---|---|
| MI | Musical_Instruments | `results_MI_V2_ls02_filter16_seed20260608.json` | 20 |
| IS | Industrial_and_Scientific | `results_FIRB_Industrial_and_Scientific_filter_seed20260713.json` | 20 |
| VG | Video_Games | `results_V2_ls02_filter8_seed20260610_VG.json` | 40 |

- **Fresh seeds (all categories): 20260721–20260725** (5/category; verified
  unused by any existing results file).
- Per seed: train with `--save-ckpt` → fusion eval. Frozen grids:
  l2 ∈ {50, 100, 200, 500}; w ∈ {0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.075,
  0.1}. Selection on validation only; test evaluated once at the selection.
- Output files: `results_{TAG}_HYBRIDV1_base_seed{seed}.json` (+`.best.pt`,
  `.fusion.json`, `.fusion_perusers.npz`); never overwritten.
- **MI ensemble secondary:** `ensemble_fuse_eval.py` over the five MI
  checkpoints; EASE l2 = the **modal** val-selected l2 across the five
  per-seed selections (ties toward smaller); w selected on validation from
  the same frozen grid; single test evaluation
  (`results_MI_HYBRIDV1_ensemble5.json`).
- Scope exclusions (declared now): Office_Products, CDs_and_Vinyl,
  Beauty_and_Personal_Care, Books are NOT part of this experiment — the
  dense closed-form EASE inversion is infeasible or borderline at their
  catalog sizes (77k–208k+ items). Any sparse/kNN variant needs its own
  pre-registration.

## 4. Endpoints (frozen)

Per seed and category, from the fusion report (single eval code path for
both scorers): `delta = test.fused.ndcg − test.seq_only.ndcg`.

- **Primary: MI mean delta** over the 5 fresh seeds; two-sided paired t
  (df = 4), α = 0.05.
- **Secondary: IS and VG mean deltas**, same test; **Holm correction across
  the three category-level tests** (one family).
- **Equivalence margin (per category): ±0.0005** — if the 95% CI of the mean
  delta lies entirely within (−0.0005, +0.0005), the adjudicated conclusion
  is "no material fusion effect" for that category.
- **MI ensemble (secondary, descriptive):** the ensemble-fused test NDCG@10
  is reported as a single evaluation with no test attached.
- **Published-comparator descriptive rows (frozen wording §7):** MI fused
  5-seed mean vs the published single-run 0.0406; VG fused 5-seed mean vs
  the published single-run 0.0760. No such row for IS. These are
  point-estimate comparisons under the standing environment caveats, in the
  same class as the paper's existing counted comparisons; they do NOT create
  paired/distributional superiority claims.

## 5. Expectations (stated for honesty, not binding)

R+ historical-seed deltas on MI were +0.0018…+0.0028 (mean +0.0024). With
that delta variance (sd ≈ 0.0004), a 5-seed paired t has power ≈ 1 for a
true +0.0024 effect; the design's risk is transfer failure on IS/VG, which
the Holm family and per-category wordings handle.

## 6. Integrity gates (adjudicator-enforced)

1. Exactly the declared 15 base + 15 fusion files (+1 ensemble) exist; seeds
   exactly {20260721…20260725} per category.
2. Fusion-selected l2/w lie inside the frozen grids; the fusion report's
   grids match the declared grids.
3. Fusion `n_eval` equals the base run's test `n_eval` (canonical
   populations; MI must be 57,439).
4. Reconstruction sanity: |fusion seq_only NDCG@10 − base recorded
   best_test NDCG@10| < 0.0005 per seed (checkpoint/eval-path fidelity).
5. Base config echo equals the reference config on every key except
   seed/out/save_ckpt/fir_v3* (mechanical dict comparison).
6. Endpoint values are read mechanically from the JSONs.

## 7. Frozen outcome wordings (the ONLY sentences that may enter the paper)

Per category C ∈ {MI, IS, VG} with mean delta {est} and 95% CI {ci}:

- **[W-H-POS]** Holm-significant positive: "Under the pre-registered
  fresh-seed replication (PREREG_HYBRID_V1, 5 seeds), late z-score fusion
  with a train-only EASE model changed test NDCG@10 on {C} by {est} [{ci}]
  (Holm-corrected paired t across three categories). The hybrid is a
  two-scorer system; published comparator numbers are single-scorer,
  single-run values and the comparison below remains a point-estimate
  comparison under the environment caveats of §3."
- **[W-H-NEG]** Holm-significant negative: same with "reduced".
- **[W-H-EQUIV]** CI within ±0.0005: "…fusion produced no material change on
  {C} ({est} [{ci}]; pre-specified margin ±0.0005)."
- **[W-H-INC]** otherwise: "…inconclusive on {C} at the available precision
  ({est} [{ci}]; margin ±0.0005)."
- **[W-H-PUB-MI]** (only if the MI fused 5-seed mean exceeds 0.0406):
  "The fused system's five-fresh-seed mean test NDCG@10 on
  Musical_Instruments, {mean}, exceeds the published single-run HSTU-BLaIR
  point estimate 0.0406 under our environment-caveated regeneration
  protocol (point-estimate comparison; no distributional claim)."
- **[W-H-PUB-VG]**: analogous sentence for VG against 0.0760, stating
  "exceeds" or "remains below" as the numbers dictate.
- **[W-H-ENS]** (descriptive): "A five-checkpoint ensemble of the same
  frozen stack, fused with EASE under the same validation-only rule, scored
  {x} on Musical_Instruments (single evaluation; ensemble frame — comparable
  only to other ensembles)."
- Under no outcome: SOTA wording, paired/distributional superiority over the
  published comparator, any change to the two counted comparisons, or any
  component-attribution claim (the hybrid is a system-level contrast).

## 8. Attribution and citation obligations

EASE is Steck (2019), "Embarrassingly Shallow Autoencoders for Sparse Data"
(WWW 2019). A bib entry MUST accompany any paper-integration commit (H9
fails the build otherwise). The fusion machinery originates in the
author-operated R+ side campaign (2026-07-22) and is ported with provenance
headers; the R+ historical-seed results remain outcome-visible development
and are citable in the paper only as such.

## 9. Budget and operations

Estimated GPU: MI ≈ 5×(13 min train + ~8 min fusion) ≈ 1.8 h; IS ≈
5×(8 + 6) ≈ 1.2 h; VG ≈ 5×(40 + 20) ≈ 5 h; ensemble ≈ 0.3 h. Total ≈ 8 h,
strictly one job at a time, chained behind E-A via its status file. The
driver is resumable (skip-if-exists) across audit-loop ticks.
