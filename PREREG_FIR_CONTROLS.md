# Frozen preregistration: canonical causal-FIR active controls

Protocol identifier: `PREREG_FIR_CONTROLS`

Status at freeze: no campaign run or final-test artifact exists

Scope: internal, outcome-known Musical Instruments mechanism/control study

## Question and claim boundary

The canonical nonsingular causal FIR has already been developed and observed on
Musical Instruments. This campaign therefore does **not** provide an independent
external comparison, a new-dataset confirmation, or evidence of state-of-the-art
performance. It asks a narrower mechanism question: under one matched backbone,
does the learned per-channel linear FIR separate from identity and from simple
causal active controls?

Nonsignificance never establishes equivalence. If a fixed control improves over
identity while the learned-minus-control contrast is retained, the permitted
wording is: “the simple causal control also improved over identity; a
learned-specific advantage over that control was not established.”

## Frozen data, backbone, and budget

- Dataset/category: `Musical_Instruments` only.
- Split files: the repository's existing fixed train/validation/test CSVs.
- Backbone/config: constructed mechanically from
  `_bestrec_run/results_MI_V2_ls02_filter16_seed20260608.json`, with the legacy
  gated filter removed. All remaining values are unchanged, including 20 epochs,
  HSTU encoder, `d=64`, four layers, two heads, dropout 0.5, time and text-similarity
  bias, position-relative bias, TAPE prototypes 512, label smoothing 0.2,
  warmup-cosine learning rate 0.001, batch size 256, and full-catalog validation.
- Kernel length: 16 for every arm.
- Seeds: `20260901` through `20260908` (eight matched blocks).
- No per-arm hyperparameter search, early-budget change, or rescue run.
- Model selection: highest validation NDCG@10 among the 20 scheduled epochs.
- TEST is disabled throughout training. After all 48 best-validation checkpoints
  exist, each checkpoint receives exactly one full-catalog final TEST evaluation.

## Frozen arms

All filters are strictly causal (left padding only), operate after item/position
embedding dropout and before the encoder, and are exact identity maps at step 0.
RNG state is restored after arm construction, so the later backbone initialization
is arm-invariant. The adjudicator requires one shared `backbone_init_sha256` per
seed across all six arms.

1. `identity`: `x + Conv_delta(x)`, zero kernel frozen. This is the no-filter
   reference with the same depthwise module shape as the learned arm.
2. `learned`: `x + Conv_delta(x)`, zero-initialized learned depthwise linear FIR;
   `64 x 16` learned control parameters.
3. `fixed_ma`: `x + alpha * (MA16(x) - x)`, fixed uniform causal moving average,
   with learned scalar `alpha=0` at initialization.
4. `fixed_hp`: `x + alpha * (x - MA16(x))`, fixed causal high-pass residual, with
   learned scalar `alpha=0` at initialization.
5. `shared`: `x + Conv_shared(x)`, one zero-initialized learned 16-tap kernel
   shared across all 64 channels.
6. `nonlinear`: `x + GELU(Conv_delta(x))`, zero-initialized learned depthwise
   causal convolution. It has exactly the learned arm's `64 x 16` control
   parameters but introduces a nonlinear response.

The five non-identity arms are gradient-active at step 0. The committed structural
test must verify exact initial identity, active gradients, and a common backbone
digest before launch. The nonlinear arm and learned FIR must have identical
trainable-parameter counts; the adjudicator enforces this.

## Sequestration and integrity gates

Training uses `--no-test-eval --save-ckpt`. A successful run JSON must contain no
test metric in its history and `best_test` must be null. Checkpoints are written
atomically and bound by SHA-256 in the run JSON.

The final evaluator creates an exclusive `*.finaleval.started.json` seal before
loading the TEST split. If either a seal or final artifact already exists it
refuses to run. Metrics are not printed; they and compressed per-user records are
written atomically. The committed adjudicator is the first reader. It must verify:

- all 48 training JSONs, best checkpoints, seals, final artifacts, and per-user
  sidecars exist;
- frozen category, seeds, arms, kernel, epoch budget, TEST-disabled training, and
  all non-arm/non-seed config values;
- checkpoint, run JSON, seal, evaluator, trainer, TEST split, and sidecar digests;
- per-user NDCG reconstructs the stored aggregate;
- identity taps remain exactly zero;
- one backbone initialization digest is shared by all arms in every seed block;
- learned and nonlinear arms have equal trainable-parameter counts.

Any failed gate yields no scientific verdict.

## Frozen endpoint and inference

Primary endpoint: full-catalog TEST NDCG@10 at the best-validation checkpoint.
The experimental unit is a seed block. Every contrast uses the eight paired seed
differences and a two-sided paired t test. The reported 95% CI is the ordinary
unadjusted paired-t interval. Multiplicity is handled by Holm-adjusted p-values and
decisions, reported separately; no interval may be called “Holm-corrected.”

Two families are frozen:

- Family A (five tests): each active arm minus identity.
- Family B (four tests): learned minus each of `fixed_ma`, `fixed_hp`, `shared`,
  and `nonlinear`.

A contrast is “positive” only when its mean is positive, its ordinary 95% CI lower
bound is above zero, and its Holm-adjusted p-value is below 0.05 in its family.

## Frozen decision tree

1. If `learned - identity` is not positive: `CTRL-NO-REPLICATION`.
2. Otherwise, if all four learned-minus-control contrasts are positive:
   `CTRL-LEARNED-DISCRIMINATED`.
3. Otherwise, if at least one simple active control is positive versus identity:
   `CTRL-ACTIVE-CONTROL-SUPPORTED`; list every such control and state that a
   learned-specific advantage was not established for any retained
   learned-minus-control contrast.
4. Otherwise: `CTRL-INCONCLUSIVE`.

All four outcomes receive equal prominence. None changes the boundary that this is
an internal, outcome-known active-control study. Integration may narrow the paper's
mechanism wording, but may not create an external-comparator, SOTA, or independent
distributional-superiority claim.

## Frozen executable artifacts

- `_bestrec_run/run_sasrec_sbert.py`
- `_bestrec_run/test_fir_controls.py`
- `_bestrec_run/run_fir_controls.py`
- `_bestrec_run/eval_fir_controls.py`
- `_bestrec_run/adjudicate_fir_controls.py`

These files and this preregistration must be committed before any campaign launch.
