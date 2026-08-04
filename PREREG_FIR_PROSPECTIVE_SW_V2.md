# Frozen execution protocol: prospective Software canonical-FIR confirmation V2

Protocol identifier: `PREREG_FIR_PROSPECTIVE_SW_V2`

Status at freeze: Software preparation passed `SW-V2-PREPARED`. No Software
recommender training, validation trajectory, checkpoint, TEST ranking,
per-user endpoint, or scientific model outcome has been computed or inspected.

This is a preregistered untouched-category confirmation attempt. It is not
institutionally independent: the investigators, Amazon Reviews 2023 dataset
family, backbone lineage, and repository are shared with earlier work.

## Question and claim boundary

On the untouched Software category, does adding the canonical causal learned
depthwise FIR module improve full-catalog next-item TEST NDCG@10 over the same
backbone with an identity FIR control?

This protocol tests module-versus-identity transfer to one new category. It
does not compare against published systems, establish state of the art, prove
that FIR is necessary or universally beneficial, or estimate uncertainty over
datasets, categories, or data splits.

## Frozen inputs

Category: `Software`, official Amazon Reviews 2023 deduplicated 5-core data and
chronological per-user leave-last-out split. Preparation protocol:
`PREREG_FIR_PROSPECTIVE_SW_V2_PREPARATION`.

| input | bytes | SHA-256 |
|---|---:|---|
| official `Software.csv.gz` | 19,079,096 | `a3ab7484436ac9034d1399b501fd2f6f5e82cfe096aeb2c4361ebfa1a5db494e` |
| `meta_Software.jsonl` | 256,220,771 | `7c52cce1bf3bff33f965fe117e3e8fac18a1839f88b215efa50b31a8230a5f58` |
| train CSV | 57,075,093 | `731c567c20b9cc58ee1270c3e281720f1a50b6e5d24c0494fa31861f17798246` |
| validation CSV | 8,491,035 | `3f42eb8e0fe8b54cc4ad854755da29f455540c4a787eaa2744f36864944733c3` |
| TEST CSV | 8,491,035 | `9e520fff20359a0fc130c8df7c4898f448aa140a90dffd82a64a60192574f863` |
| title embeddings (`17591 × 384`, float32) | 27,019,904 | `2a1d09dea26c9c619a6d52ba2082c58ac23c03a04a7f02be30f5e9441098aa38` |
| sorted item map | 358,302 | `62e6a129e39dcead62922e096d6a36eef2527668a7bb8791822127440d36c7ae` |

Prepared counts: 146,396 users, 17,591 items, 984,048 training rows,
146,396 validation rows, and 146,396 TEST rows. All 17,591 retained items have
a nonempty title. No row, user, item, or title is removed after this freeze.

## Frozen model and budget

The configuration is mechanically reconstructed from
`_bestrec_run/results_MI_V2_ls02_filter16_seed20260608.json`, excluding only
category, output path, seed, and obsolete/filter-arm selectors. This file has
SHA-256 `a230d17cd4e1683ac0e07e64702587950baf89374083521850c96daeede1ab72`.
There is no Software tuning or pilot.

The resulting fixed settings include the HSTU-style encoder, 20 epochs,
`d_model=64`, four layers, two heads, dropout 0.5, TAPE-512, time,
text-similarity and relative-position biases, label smoothing 0.2,
warmup-cosine learning rate 0.001, batch size 256, full-catalog validation, and
best-validation-NDCG@10 checkpoint selection. The frozen base trainer is
`_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py`; its canonical-LF
digest is checked mechanically. No hyperparameter, epoch, seed, or failed run
may be replaced or extended.

Fresh matched optimizer-seed blocks: `20261201` through `20261208`.

## Frozen arms

Both arms use left-only padding, kernel width 16, the same parameter
registration order, and matched per-seed backbone initialization.

1. `identity`: a frozen zero depthwise 16-tap residual, hence the exact
   identity map and no active FIR parameter.
2. `learned`: a zero-initialized, gradient-active depthwise 16-tap residual
   with `64 × 16 = 1,024` trainable tap parameters.

No other arm is trained. Within each seed, the adjudicator requires identical
backbone-initialization hashes. Identity taps must remain exactly zero.

## Sequestration and commit custody

Execution occurs in a dedicated clean clone. The driver records one Git HEAD,
requires no tracked modification, and rechecks the unchanged HEAD and clean
tracked tree before every child process. The wrapper records that HEAD and the
frozen trainer/wrapper digests in each training JSON.

Training uses `--no-test-eval --save-ckpt`; `best_test` must remain null and no
history entry may contain a TEST metric. All 16 best-validation checkpoints
must exist before the evaluator permits the first TEST access.

The evaluator creates an exclusive `*.finaleval.started.json` seal before
loading a checkpoint, refuses repeats, writes endpoint and compressed per-user
artifacts atomically, and does not print endpoint values. The campaign driver
may inspect training JSONs, existence, hashes, return codes, and status, but
not final endpoint contents. The committed adjudicator is the first authorized
reader of final endpoint artifacts.

An incomplete seal, input/hash/config/custody mismatch, missing run, nonfinite
endpoint, changed Git HEAD, dirty tracked tree, or early TEST access is a
terminal integrity failure for V2. Existing outputs are never overwritten.

## Frozen endpoint and inference

Primary endpoint: per-seed full-catalog TEST NDCG@10 at the checkpoint with
maximum validation NDCG@10 over the fixed 20 epochs.

Sole confirmatory contrast: paired `learned - identity` across the eight
matched optimizer-seed blocks. Report the eight differences, mean, sample
standard deviation, paired-t statistic with 7 degrees of freedom, two-sided
p-value, and ordinary two-sided 95% paired-t confidence interval. Alpha is
0.05. There is one test, so no multiplicity correction is needed. HR@10 and
MRR are descriptive only. A retained null is not equivalence.

The experimental unit is the optimizer seed on one fixed category and split.
The interval does not cover user, split, category, dataset, or investigator
sampling uncertainty.

## Frozen decision tree

1. Any integrity failure: `SW-V2-INTEGRITY-FAIL`; no scientific verdict.
2. If the mean difference is at least `+0.000500`, the ordinary 95% CI lower
   bound is above zero, and the two-sided p-value is below 0.05:
   `SW-V2-CONFIRM-POS`.
3. If the CI lower bound is above zero and p < 0.05, but the mean is below
   `+0.000500`: `SW-V2-STATISTICAL-SMALL`.
4. If the mean is below zero, the CI upper bound is below zero, and p < 0.05:
   `SW-V2-CONFIRM-NEG`.
5. Otherwise: `SW-V2-INCONCLUSIVE`.

All outcomes receive equal prominence. No outcome licenses a SOTA claim.

## Frozen executable boundary

- `_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py` (base trainer)
- `_bestrec_run/run_sasrec_sbert_software_v2_frozen.py` (custody wrapper)
- `_bestrec_run/test_fir_pointwise_v1.py` (structural/gradient test)
- `_bestrec_run/run_fir_prospective_sw_v2.py` (driver)
- `_bestrec_run/eval_fir_prospective_sw_v2.py` (one-shot evaluator)
- `_bestrec_run/adjudicate_fir_prospective_sw_v2.py` (first reader)

These files, this preregistration, the preparation manifests, and their
digests must be committed and pushed before the first recommender process.
