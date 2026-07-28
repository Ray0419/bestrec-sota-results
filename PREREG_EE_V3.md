# PREREG_EE_V3 — clean AlphaFuse-style text+ID comparator

**Status: FROZEN BEFORE any V3 training or endpoint exists.** This protocol,
its common module, runner, evaluator, driver, conformance tests, and mechanical
adjudicator must be committed and pushed before launch. Claims may only narrow.

## 1. Evidence class and question

This is a prospectively frozen execution on the already outcome-known AR2023
Video_Games split by the same investigators. It is an **exploratory current-
comparator feasibility study**, not independent confirmation and not a SOTA
test.

Question: under the paper's exact full-catalog candidate set, complete-history
seen-item mask, target exception, strict-greater tie rule, and leave-last-out
targets, how does the official AlphaFuse **representation package** behave on
our data, and how does it compare descriptively with (a) the official
AlphaFuse-repository SASRec ID-only backbone and (b) the paper's existing
six-seed full-model reference?

The ON–OFF contrast is not called a null-space fusion effect. The arms also
differ in text availability, initialization, trainable capacity, and parameter
allocation. The estimand is the whole representation-package contrast.

## 2. Frozen upstream and data identities

- Upstream: `https://github.com/Hugo-Chinn/AlphaFuse.git`
- Commit: `b501a0540b609370df995ad06fb245859b10a18a`
- Governed upstream files and hashes are constants in
  `_bestrec_run/ee_v3_common.py`.
- Dataset: Amazon Reviews 2023 Video_Games 5-core LLOO export, 94,762 users,
  25,612 items. The exporter JSONL/manifest, AlphaFuse-format pickles, and
  MiniLM embedding pickle are hash-frozen in the common module.
- The MiniLM-384 frozen title vectors replace AlphaFuse's OpenAI text vectors.
  This disclosed representation substitution applies to the AlphaFuse arm;
  the result is an AlphaFuse-style MiniLM port, not an exact reproduction of a
  published AlphaFuse table.
- Training uses AlphaFuse's sampled-negative InfoNCE implementation; evaluation
  is full catalog. Published AlphaFuse numbers are never compared directly.

## 3. Arms and fresh seeds

Two arms, each with the same eight fresh seeds
`20262201..20262208` (verified unused at freeze time):

1. `alphafuse_package`: official `AlphaFuse` class, MiniLM-384 text,
   `null_dim=64`, zero-initialized ID residual as distributed/configured.
2. `sasrec_id`: official repository `SASRec` class, pure 128-dimensional ID
   representation under the same backbone/training configuration.

Same-number seeds are labels, not evidence of common-random-number pairing.
All optimizer-seed inference is predeclared as **independent-arm Welch**.

Frozen shared configuration: max input length 50; hidden dimension 128; two
blocks; one head; dropout 0.1; Adam learning rate 0.001, epsilon 1e-8,
weight decay 1e-6; InfoNCE, 64 sampled negatives, temperature 0.07; batch 256;
maximum 500 epochs; patience 50; strict validation improvement; no per-arm or
post-result tuning. Training-row construction remains the disclosed per-prefix
adapter because the upstream offline preprocessing code is unavailable.

## 4. Selection and evaluation estimand

- Model input is left-padded/truncated to the most recent 50 interactions.
- **Masking is separate from model input.** Validation masks every item in the
  user's complete TRAIN history; TEST masks every item in complete TRAIN+VALID
  history. The held-out target is never masked, even if repeated.
- Eligibility is all 25,612 items.
- `rank0 = count(eligible_score > target_score)`; equal scores do not outrank.
- Metrics are exact functions of rank0: HR/NDCG/MRR at 5, 10, 20, and 50.
- Every epoch is selected by the same shared, complete-history-masked VALID
  NDCG@10 evaluator. Training code never loads or hashes TEST.
- TEST is scored once per completed checkpoint, only after a family-wide READY
  record binds all 16 terminal training artifacts and checkpoints.

The structural suite must pass synthetic long-history masking/tie/target tests
and a real-data conformance check against the rank arithmetic used in
`run_sasrec_sbert.py` before launch.

## 5. Lifecycle and custody

- Private campaign root: `_bestrec_run/ee_v3_private/` (ignored until sealed
  release decisions). Every arm/seed has an exclusive STARTED record, atomic
  latest checkpoint, atomic best checkpoint, and exclusive terminal training
  JSON. A valid terminal bundle is skipped; an interrupted attempt resumes only
  from its hash/schema-validated epoch-boundary latest checkpoint.
- Terminal training JSONs state `test_read_or_scored=false` and contain source,
  data, environment, config, checkpoint, parameter, wall-time, and selected-
  epoch identities.
- The family READY record is create-new and contains all 16 terminal/checkpoint
  hashes. No evaluator may run without an exact READY match.
- Each TEST attempt first creates an exclusive no-repeat STARTED seal, then
  atomically writes a compressed rank sidecar and endpoint JSON. An incomplete
  sealed TEST attempt is an integrity failure; it is never deleted or rerun.
- The driver creates an ENDPOINTS-COMPLETE status and immediately invokes the
  already committed adjudicator. The adjudicator is the first authorized reader
  of endpoint JSON/sidecar contents after the evaluators write them.
- Exact schemas and exact artifact sets are fail-closed. Missing, duplicate,
  extra, non-finite, hash-drifted, or non-reconstructive artifacts exit nonzero.

## 6. Frozen statistics

For each arm, report the eight-seed mean, sample SD, and ordinary two-sided 95%
Student-t interval for NDCG@10, HR@10, and MRR.

Two descriptive independent-arm Welch contrasts (unadjusted; no confirmatory
family claim):

1. AlphaFuse package minus AlphaFuse-repository SASRec ID backbone.
2. AlphaFuse package minus the existing six-seed paper full-model reference.

The mechanical directional vocabulary is `ABOVE`, `BELOW`, or `OVERLAP`
according to whether the ordinary 95% Welch interval is entirely positive,
entirely negative, or crosses zero. These labels describe the recorded sample;
they are not SOTA or causal-superiority claims.

Fixed-dataset sensitivity: average each arm's per-user NDCG@10 over its eight
seeds, difference those user-level averages, and compute 2,000-replicate
percentile intervals by (a) resampling users and (b) resampling target-item
clusters, frozen RNG seed `20262299`. These are sensitivity intervals conditional
on the fixed split and trained seed sets, not population or optimizer inference.

## 7. Resource reporting

Per seed and arm record total/trainable parameters, training wall time, selected
epoch, evaluation wall time, examples/second, CUDA peak allocated bytes, and
PyTorch-profiler-accounted forward-plus-full-catalog-score FLOPs per user for a
fixed probe batch. Profiler FLOPs are explicitly operator-accounted lower-bound
instrumentation, not a complete hardware-energy measure.

## 8. Admissible wording

The paper may report the exact arm estimates and bounded contrasts with this
boundary:

> Under a prospectively frozen but outcome-known, same-investigator execution,
> an AlphaFuse-style MiniLM representation package was trained on eight fresh
> seeds and evaluated with the paper's complete-history-masked full-catalog
> evaluator. The comparison equalizes the data/evaluator and freezes the
> training configuration; it does not reproduce AlphaFuse's published text
> encoder, equalize architecture with our model, isolate null-space fusion,
> establish SOTA, or provide independent confirmation.

Negative, null, and positive outcomes receive the same prominence. V2 remains
`OUTCOME_VISIBLE_PROTOCOL_DEVIATED_NONCOUNTABLE` and is never pooled with V3.

## 9. Stop rules

- No endpoint reading before 16/16 training terminals and 16/16 sealed TEST
  evaluations exist.
- No seed extension, configuration change, arm deletion, or redefinition after
  launch. A failed integrity gate is reported; it is not repaired by overwriting.
- Human author/byline metadata and the independent-reproduction gap remain
  separate external blockers regardless of this result.
