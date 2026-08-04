# PREREG_COLDFUSE_V1 — E-G Stage 2: Cold/Sparse-Tail Text Scorer, Full-Dataset Confirmation (FROZEN)

**Status: FROZEN at commit time; committed BEFORE any run is launched.
Analysis and integration happen ONLY through
`_bestrec_run/adjudicate_coldfuse_v1.py` and the frozen wordings in §6.
Claims may only narrow; no SOTA wording under any outcome. Maintainer
directive 2026-07-23: "add element that help cold start or sparse dataset
problem … once there's evidence of improvement verify with all full
datasets" — this is that verification.**

Registered: 2026-07-23. Author-operated automation; mechanical adjudication.

## 1. Provenance and question

E-G stage 1 (exploratory, disclosed as such; development on E-F checkpoints
seeds 20260721–22 only) found that a training-free text-kNN scorer fused
with train-frequency-binned weights lifted the MI tail-bin test NDCG@10
≈2.5× (0.0014→0.0037 and 0.0016→0.0034) at ≤0.00004 overall cost, and both
seeds passed the pre-stated VAL-only promotion rule
(`eg_coldfuse_explore_verdict.json`). Question: does the element replicate
on fresh seeds, and does it transfer across ALL paper categories —
including the large catalogs where dense EASE is infeasible?

## 2. System under test (frozen)

- Text scorer: `score_text(u,i) = profile(u) · e_i` over the frozen MiniLM
  title embeddings, rows L2-normalized; profile = uniform mean or
  exp-0.9-recency-weighted mean of the user's input-history embeddings.
- Fusion per user (z = per-user z-normalization over the full catalog):
  `fused3 = z(seq) + w_e·z(EASE) + w_t(bin)·z(text)`, where
  `w_t(bin)` is per TRAIN-frequency bin of the scored item
  (tail ≤5 / mid 6–20 / head >20; never test frequency), constrained
  monotone nonincreasing in frequency.
- Reference system per category: MI/IS/VG = `fused2` (the E-F system:
  z(seq)+w·z(EASE), (l2,w) selected on validation by the frozen
  PREREG_HYBRID_V1 procedure re-run on the new seeds); Office/CDs = the
  sequential model alone with `w_e = 0` (dense EASE is infeasible at
  77k/89k+ items — declared exclusion, carried from PREREG_HYBRID_V1).
- Candidate grid (frozen, narrowed from the stage-1 sweep): profile ∈
  {uniform, exp0.9} × monotone triples (w_tail, w_mid, w_head) with each
  weight ∈ {0, 0.05, 0.1, 0.2} and w_tail ≥ w_mid ≥ w_head (20 triples;
  includes the null triple (0,0,0) = reference).
- Selection (frozen, VAL only): among candidates whose validation overall
  NDCG@10 ≥ reference − 0.0002, pick the maximum validation tail-bin
  NDCG@10. Test is evaluated once, for the reference and the selected
  candidate only.

## 3. Design (frozen)

Five categories × five FRESH seeds **20260736–20260740** (verified unused;
the 20260728–32 block is consumed by the Office V3 campaign):

| Tag | Category | Frozen base reference (config source) | EASE |
|---|---|---|---|
| MI | Musical_Instruments | `results_MI_V2_ls02_filter16_seed20260608.json` | yes |
| IS | Industrial_and_Scientific | `results_FIRB_Industrial_and_Scientific_filter_seed20260713.json` | yes |
| VG | Video_Games | `results_V2_ls02_filter8_seed20260610_VG.json` | yes |
| OFFICE | Office_Products | `results_OFFICEV3_k16_seed20260728.json` | no |
| CDS | CDs_and_Vinyl | `results_FIRB_CDs_and_Vinyl_filter_seed20260713.json` | no |

Per seed: (1) train the base stack with `--save-ckpt` (commands constructed
mechanically from the reference config minus seed/out); (2) MI/IS/VG only:
run the frozen PREREG_HYBRID_V1 fusion procedure (`fuse_ease_eval.py`,
frozen grids) to fix the per-seed (l2, w_e); (3) run the streaming
confirmatory evaluator `fuse_cold_confirm.py` (VAL sweep over the frozen
candidate grid → single TEST evaluation of reference + selected).
Outputs `results_{TAG}_COLDFUSE_base_seed{seed}.json` (+ `.best.pt`,
`.fusion.json` where applicable, `_confirm.json`, per-user records);
nothing is ever overwritten.

## 4. Endpoints (frozen)

Per category, per seed, from the confirm report (identical eval code path
for both systems): `tail_delta = test.selected.tail − test.reference.tail`
and `overall_delta = test.selected.overall − test.reference.overall`
(NDCG@10; tail = users whose held-out target has train frequency ≤ 5).

- **Co-primary (per category): mean tail_delta** over the 5 seeds,
  two-sided paired t (df = 4); **Holm across the five categories**
  (one family). α = 0.05.
- **Overall-cost check (per category):** the no-material-cost sentence may
  be used iff the 95% CI lower bound of mean overall_delta > −0.0005.
- **Equivalence margin (tail): ±0.0005** for the W-C-EQUIV wording.
- No interim looks; adjudication runs once, after all 25 confirm files
  exist.

## 5. Integrity gates (adjudicator-enforced)

1. Exactly the declared 25 confirm files (+15 fusion files for MI/IS/VG)
   exist; seeds exactly {20260736…20260740} per category.
2. Selected candidate lies inside the frozen grid; selection echo shows the
   VAL-only rule (constraint value −0.0002; recorded sweep).
3. `n_eval` equals the base run's test `n_eval`.
4. Reconstruction fidelity: |test reference overall − expected| < 0.0005,
   where expected = the `.fusion.json` fused test NDCG@10 (MI/IS/VG) or the
   base recorded `best_test` NDCG@10 (Office/CDs).
5. Base config echo equals the reference config on every key except
   seed/out/save_ckpt/fir_v3* (mechanical dict comparison).

## 6. Frozen outcome wordings (the ONLY sentences that may enter the paper)

Per category C with mean tail delta {est} [{ci}] and mean overall delta
{oest} [{oci}]:

- **[W-C-POS]** Holm-significant positive tail delta: "Under the
  pre-declared fresh-seed confirmation (PREREG_COLDFUSE_V1, 5 seeds), the
  frequency-binned text scorer changed tail-bin test NDCG@10 (targets with
  train frequency ≤5) on {C} by {est} [{ci}] relative to the {reference
  system} (Holm-corrected paired t across five categories), with overall
  test NDCG@10 change {oest} [{oci}]{, i.e. no material overall cost at the
  pre-specified −0.0005 margin | — an overall cost exceeding the
  pre-specified margin, stated plainly}. Weights were selected on
  validation only from frozen grids; the tail-bin population is defined by
  TRAIN frequency."
- **[W-C-NEG]** Holm-significant negative tail delta: as W-C-POS with
  "reduced".
- **[W-C-EQUIV]** tail CI within ±0.0005: "…the text scorer produced no
  material tail-bin change on {C} ({est} [{ci}]; margin ±0.0005)."
- **[W-C-INC]** otherwise: "…inconclusive on {C} at the available
  precision ({est} [{ci}]; margin ±0.0005)."
- Standing sentence (all outcomes): "The element is evaluation-time and
  training-free; the sequential model's zero-exposure finding (§5.3.1)
  is unaffected: content-based retrieval is a different mechanism, and
  items with literally zero training interactions remain outside every
  counted claim."
- Under no outcome: SOTA wording, distributional superiority over any
  published comparator, or any change to the counted comparisons.

## 7. Budget and operations

Training ≈ 5 × (MI 13 + IS 8 + VG 40 + OFFICE 14 + CDS 12) ≈ 7.3 h; EASE
fits + streaming evals ≈ 2–3 h. Strictly one GPU job at a time; the driver
(`run_coldfuse_confirm.py`) refuses to start while any earlier campaign
status file reports running, skips existing outputs, and is resumable
across loop ticks. Steck (2019) is already in the bibliography (E-F
integration commit).
