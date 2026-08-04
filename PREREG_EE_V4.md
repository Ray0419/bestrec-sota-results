# PREREG_EE_V4 — upstream-default-normal-init SASRec sensitivity

**Status: FROZEN BEFORE any V4 training or endpoint exists.** This protocol,
its common module, runner, evaluator, driver, conformance tests, and mechanical
adjudicator must be committed and pushed before launch. Claims may only narrow.

## 1. Evidence class and question

This is a prospectively frozen execution on the already outcome-known Amazon
Reviews 2023 Video_Games split by the same investigators. It is an **outcome-
known comparator-fairness sensitivity**, not independent confirmation, not a
new-dataset replication, and not a SOTA test.

The prior E-E V3 AlphaFuse-style MiniLM package used the upstream AlphaFuse
class with a zero-initialized ID residual and compared it with an upstream-class
SASRec-ID control whose ID table was also forced to zero. The upstream
`train.py` default is instead `ID_embs_init_type="normal"`, implemented as
`Normal(0,1)` in `models/backbone_SASRec.py`. V4 asks whether the V3 package
remains above an upstream-default-normal-init SASRec-ID control under the same
data, evaluator, training loss, schedule, and selection rule.

This is a cross-campaign sensitivity. Phase/date and initialization are
confounded, the AlphaFuse and SASRec architectures/capacities remain unequal,
and the V3 outcome was known before V4 was designed. No causal initialization
effect or independent superiority claim is allowed.

## 2. Frozen identities

- Upstream AlphaFuse repository commit:
  `b501a0540b609370df995ad06fb245859b10a18a`.
- Governed upstream file hashes, AR2023 Video_Games data hashes, and the
  TEST-free full-history input hash are inherited from and rechecked by
  `_bestrec_run/ee_v3_common.py`.
- The public V3 adjudication is frozen by SHA-256
  `978aebe051abdefe3de542856bad6e321f6d581c53edfa9c01594006d24126ef`.
  V4 uses only its already-public aggregate seed vectors for cross-campaign
  contrasts; it does not pool V3 and V4 as one experiment.
- No V4 code path may alter or overwrite a V3 artifact.

## 3. Arm, seeds, and shared budget

One arm, eight fresh optimizer seeds `20262301..20262308`, verified unused at
freeze time:

- `sasrec_normal`: official upstream `SASRec` class, pure 128-dimensional ID
  representation, `ID_embs_init_type="normal"` (the upstream CLI default).

The training configuration is otherwise exactly the V3 SASRec configuration:
maximum input length 50; hidden dimension 128; two blocks; one head; dropout
0.1; Adam learning rate 0.001, epsilon 1e-8, weight decay 1e-6; InfoNCE with 64
sampled negatives and temperature 0.07; batch 256; maximum 500 epochs; patience
50; strict complete-history-masked full-catalog VALID NDCG@10 improvement; no
tuning or post-result configuration change.

The driver launches two seed processes concurrently in four frozen waves:
`(20262301,20262302)`, `(20262303,20262304)`, `(20262305,20262306)`, and
`(20262307,20262308)`. Concurrency makes training wall time and energy unsuitable
for a hardware-efficiency comparison. Parameter counts and evaluator FLOPs are
recorded descriptively only.

## 4. Selection, TEST boundary, and lifecycle

- Training uses only the already-frozen TRAIN/VALID artifacts. The V4 training
  runner never loads, hashes, or scores TEST.
- Model input is the most recent 50 interactions. VALID masks complete TRAIN;
  TEST masks complete TRAIN+VALID; the target is excepted; ties use strict
  greater-than ranking over all 25,612 items.
- TEST is scored exactly once per completed checkpoint only after an exclusive
  family READY record binds all eight terminal training bundles.
- Every arm/seed has exclusive STARTED and terminal records, atomic epoch-boundary
  latest and selected-best checkpoints, and a sealed no-repeat TEST-attempt
  record. Missing, partial, extra, drifted, or non-finite bundles fail closed.
- After all eight endpoints and sidecars exist, the already committed V4
  adjudicator is the first authorized endpoint reader.
- Resumption may continue only an intact schema/identity-consistent epoch-boundary
  checkpoint. Results are never overwritten and seeds are never extended.

## 5. Frozen statistics and verdict

Report the eight-seed mean, sample SD, and ordinary two-sided 95% Student-t
interval for V4 NDCG@10, HR@10, and MRR. Report three descriptive independent-
arm Welch contrasts using the public V3 vectors:

1. V3 AlphaFuse-style package minus V4 normal-init SASRec-ID (primary).
2. V4 normal-init SASRec-ID minus V3 zero-init SASRec-ID (initialization/
   phase sensitivity; explicitly not causal).
3. V4 normal-init SASRec-ID minus the existing six-seed paper reference.

Each direction is mechanically `ABOVE`, `BELOW`, or `OVERLAP` according to its
ordinary 95% Welch interval. P-values are unadjusted descriptive diagnostics;
there is no confirmatory family claim. The primary mechanical verdict is:

- `EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC` if contrast 1 is entirely positive;
- `EEV4-ALPHAFUSE-BELOW-NORMAL-SASREC` if entirely negative;
- `EEV4-ALPHAFUSE-NORMAL-SASREC-OVERLAP` otherwise.

Negative, null, and positive outcomes receive the same prominence. The public
artifact will include the exact V4 seed vectors and endpoint-hash ledger. Rank
sidecars remain private unless a lawful release decision is made.

## 6. Admissible wording

> In a prospectively frozen but outcome-known same-investigator sensitivity,
> the upstream-default-normal-init AlphaFuse-repository SASRec class was trained
> on eight fresh seeds under the V3 data, loss, selection, and evaluator. Its
> cross-campaign contrast with the earlier AlphaFuse-style MiniLM package tests
> whether that whole-package result survives a more standard SASRec
> initialization; it does not isolate initialization, equalize architecture or
> capacity, reproduce a published AlphaFuse table, establish SOTA, or provide
> independent confirmation.

## 7. Stop rules

- No endpoint reading before 8/8 terminal trainings and 8/8 sealed TEST
  evaluations exist.
- No seed extension, configuration change, endpoint rerun, arm redefinition,
  or deletion after launch.
- An integrity failure is reported and resumed only within these frozen rules;
  no artifact is overwritten to repair a result.
- Human author/legal metadata, lawful replay/deposit, modern operator baselines,
  equal-capacity factorial controls, and independent reproduction remain
  separate blockers regardless of outcome.
