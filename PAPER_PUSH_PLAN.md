# Paper-push plan — maximize acceptance (maintainer directive 2026-07-24)

Directive: "finish all experiments with max local compute, then write up the
paper to maximize acceptance rate; add more evaluation metrics (MSE, RMSE, NDCG,
and more) and compare to models to show our improvement and elements."

This plan translates that into what actually raises acceptance while keeping the
rigor that is the paper's only real asset. Ordered by acceptance impact.

## Honest metric decision (READ FIRST)
Our task is **implicit-feedback, leave-last-out, full-catalog next-item
ranking**. The correct metric family is ranking metrics — all exact functions of
per-user `rank0` (see `_bestrec_run/metrics_family.py`, selftest passing):
**HR@{5,10,20,50}, NDCG@{5,10,20,50}, MRR** (Recall@k = HR@k for a single
target; Precision@k = HR@k/k).
- **MSE / RMSE / MAE are NOT added.** They are rating-prediction
  (explicit-feedback) error metrics; this protocol has no held-out numeric
  rating to square-error against, so they are undefined here, and reporting them
  is a task/metric mismatch a competent reviewer flags — it would LOWER
  acceptance, the opposite of the goal. If explicit-rating prediction is ever
  wanted it is a different task/paper.
- Adding cutoffs is **descriptive enrichment**, not a new counted claim. The two
  counted comparisons stay frozen at NDCG@10 (this reproduces them bit-for-bit
  from the same ranks).

## Guardrails (unchanged, non-negotiable)
Counted set = MI V2 + Office V3 only (frozen wordings). FORBIDDEN: SOTA of any
kind, significance-vs-HSTU-BLaIR, paired/distributional superiority, official
reproduction, Office V1 as passed, TFV2 as confirmatory. Any NEW claim needs a
NEW frozen pre-registration + committed adjudicator BEFORE launch. One GPU job
at a time (RTX 5060 Ti). Never weaken a caveat to close a finding.

## Workstreams (GPU runs in background WHILE writing proceeds — that is "max compute")

### WS1 — Richer metric family for every reported model  [enabler DONE]
- [x] `metrics_family.py` (rank0 -> exact HR/NDCG/MRR family; selftest passes)
- [ ] `reeval_rank0.py`: for each reported model (per-category base SASRec-SBERT,
      the EASE-fused variant, the FIR arm), load-or-retrain at its FROZEN config
      and dump the per-user `rank0` sidecar; assert NDCG@10 reproduces the
      recorded value (consistency gate). GPU, one at a time.
- [ ] Build the richer-metrics table cell-set in build_hstu_tables.py; integrate
      via the full ritual (descriptive columns; counted claims untouched).

### WS2 — Honest comparison table (positioning + elements)
- [ ] One table: our stack per category + each ELEMENT ablation (FIR arm E-A;
      EASE late-fusion E-F) + the closest external comparator (E-E:
      AlphaFuse-on-our-data), all as environment-caveated point estimates with
      the richer metric family. NO superiority/SOTA wording; "element" rows show
      what each component adds under the frozen ablation wordings.

### WS3 — Finish the designed experiments (sequential, prereg-before-launch)
- [~] E-E: adapter built + validated; **local smoke test PASSED 2026-07-24**
      (AlphaFuse trains + full-catalog-evals on our VG data end-to-end, ~2s/eval
      — full local runs are feasible, no rental needed). NEXT: FREEZE PREREG_EE +
      adjudicate_ee (pin AlphaFuse's own recommended config + seeds + metric + 3
      disclosed deviations + caveated wording), then run AlphaFuse + our stack on
      VG (+ Office counted); adjudicate; integrate as a caveated closest-comparator
      row (no superiority). Smoke numbers are a dev probe, NOT recorded.
- [ ] E-C / E-C2 / E-D: robustness/ablation studies — each freeze prereg +
      adjudicator, run, adjudicate, integrate (negative outcomes reported with
      equal prominence).

### WS4 — Synthesis rewrite (BIGGEST acceptance lever) — STARTED 2026-07-24
- [~] **Spine blueprint done: `PAPER_SPINE.md`** (target structure, per-section
  word budgets, content-migration map, submission-readiness fix list, section-at-
  a-time execution order). Next: execute the spine section by section, each its
  own commit + full ritual (render CLEAN, tex H1–H9, strict exit 0).
- [ ] Restructure to a tight scientific spine (20–35pp acmsmall): method +
      elements + honest empirics + the negative/rigor findings as the
      contribution; move the correction-ledger/forensics to a supplement; remove
      the "delete before submission" block; fix the R1/R2 legend nonsignificance
      mislabel; reframe explicitly as a **rigor / reproducibility** contribution
      (pre-registration, test sequestration, a VOIDed failed pre-registration, a
      reclassified negative finding) — the framing that fits the evidence and the
      right venue (TORS / reproducibility track).

## Sequencing
GPU queue (background): WS1 reeval -> WS3 E-E -> WS3 E-C/C2/D.
Writing (foreground, parallel): WS4 rewrite + WS2 table, slotting WS1/WS3
numbers in as they land. Compute is NOT the acceptance bottleneck (the rewrite
is) — but idle GPU is used on properly-registered work so nothing is wasted.
