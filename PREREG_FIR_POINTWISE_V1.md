# Frozen preregistration: parameter-matched non-temporal placebo

Protocol identifier: `PREREG_FIR_POINTWISE_V1`

Status at freeze: no training run, checkpoint, final-test seal, final-test
artifact, or per-user sidecar exists for this protocol.

Scope: internal, outcome-known Musical Instruments mechanism study. The split,
the earlier FIR outcomes, and the active-control outcomes are already known.
This campaign cannot provide independent confirmation, cross-dataset
generalization, or a state-of-the-art comparison.

## Question

Does the canonical learned depthwise FIR outperform a trainable residual with
the same parameter count and initialization properties but no access to earlier
sequence positions?

The result can discriminate the two tested arms. It cannot prove that temporal
structure is generally necessary, because the pointwise placebo uses one fixed
feature basis and one configuration. Nonsignificance is not equivalence.

## Frozen data, backbone, budget, and seeds

- Category: `Musical_Instruments`.
- Split: the repository's existing fixed AR2023 5-core train/validation/test
  CSVs; hashes are checked by the evaluator/adjudicator.
- Base configuration: mechanically reconstructed from
  `_bestrec_run/results_MI_V2_ls02_filter16_seed20260608.json` after removing the
  legacy gated filter. All non-arm settings remain fixed: HSTU-style encoder,
  20 epochs, `d_model=64`, four layers, two heads, dropout 0.5, TAPE-512, time,
  text-similarity and relative-position biases, label smoothing 0.2,
  warmup-cosine learning rate 0.001, batch size 256, and full-catalog
  validation/evaluation.
- Width/kernel: 16.
- Fresh optimizer-seed blocks: `20261001` through `20261008`.
- Model selection: maximum validation NDCG@10 over the 20 scheduled epochs.
- No per-arm tuning, rescue run, seed replacement, or budget change.

The experimental unit is an optimizer-seed block on one fixed split. Intervals
do not quantify user, split, category, or dataset sampling uncertainty.

## Frozen arms

All arms are exact identity maps at initialization. Arm construction restores
the CPU RNG state before later backbone initialization, and the adjudicator
requires one shared backbone-initialization hash within every seed block.

1. `identity`: frozen zero depthwise 16-tap residual; no active residual
   parameters.
2. `learned`: zero-initialized learned depthwise 16-tap FIR,
   `64 × 16 = 1,024` trainable parameters, using left padding only.
3. `pointwise`: the current-position vector is projected onto the first 16
   orthonormal DCT-II features, passed through GELU, and mapped back to 64
   channels by a zero-initialized learned `64 × 16` matrix. The DCT projection
   is a deterministic frozen buffer. The arm therefore has exactly 1,024
   trainable parameters, is gradient-active at the identity initialization,
   and cannot read any prior or future position.

The placebo changes both temporal access and representation basis relative to
the FIR; therefore even a positive learned-minus-pointwise contrast licenses
only “the learned FIR outperformed this tested parameter-matched pointwise
placebo,” not a universal temporal-specificity claim.

## Outcome sequestration and immutable attempts

Training uses `--no-test-eval --save-ckpt`; training JSONs must contain no test
metric and `best_test` must be null. All 24 best-validation checkpoints must
exist before any TEST evaluation begins.

The final evaluator uses exclusive `*.finaleval.started.json` seals and refuses
any repeat TEST access. It writes metrics and compressed per-user records
atomically without printing endpoint values. The campaign driver checks only
file existence and exit codes. The committed adjudicator is the first program
authorized to read final endpoints.

No existing output may be overwritten. A partial started seal is a terminal
integrity failure for that attempt; it is not deleted or reused.

## Endpoint and inference

Primary endpoint: full-catalog TEST NDCG@10 at the best-validation checkpoint.

Three paired contrasts form one Holm family:

1. `learned - identity` (replication gate),
2. `pointwise - identity` (generic trainable-residual diagnostic), and
3. `learned - pointwise` (primary placebo discrimination).

For each contrast, report the eight paired seed differences, mean difference,
sample standard deviation, paired-t statistic with 7 degrees of freedom, raw
two-sided p-value, Holm-adjusted p-value/decision, and ordinary unadjusted 95%
paired-t confidence interval. A contrast is positive only if its mean and
ordinary CI lower bound are above zero and its Holm-adjusted p-value is below
0.05. The confidence interval must never be called Holm-corrected.

## Frozen decision tree

1. Any artifact/config/provenance failure: `POINTWISE-INTEGRITY-FAIL`; no
   scientific verdict.
2. If `learned - identity` is not positive: `POINTWISE-NO-REPLICATION`.
3. If `learned - pointwise` is positive:
   `POINTWISE-FIR-DISCRIMINATED`; wording is limited to the tested placebo.
4. Otherwise, if `pointwise - identity` is positive:
   `POINTWISE-GENERIC-RESIDUAL-SUPPORTED`; the tested non-temporal residual is
   sufficient to reproduce an improvement and FIR-specific advantage is not
   established.
5. Otherwise: `POINTWISE-INCONCLUSIVE`; neither equivalence nor absence of a
   temporal effect is claimed.

All outcomes receive equal prominence. No outcome changes the campaign's
outcome-known internal evidence class.

## Frozen executable artifacts

- `_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py`
- `_bestrec_run/test_fir_pointwise_v1.py`
- `_bestrec_run/run_fir_pointwise_v1.py`
- `_bestrec_run/eval_fir_pointwise_v1.py`
- `_bestrec_run/adjudicate_fir_pointwise_v1.py`

These files, their SHA-256 hashes, and this preregistration must be committed
before campaign launch.
