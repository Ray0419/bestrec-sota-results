# Preregistration: prospective Software causal-FIR V3

Protocol identifier: `PREREG_FIR_PROSPECTIVE_SW_V3`

Freeze mechanism: immutable Git tag `fir-prospective-sw-v3-freeze`, created
immediately after the commit containing this complete protocol and every V3
executable. Every process must run at exactly the tag target, from a clean
tracked tree, and byte-compare the complete frozen dependency list against the
tagged Git objects.

Status at freeze: V2 has the permanent non-scientific verdict
`SW-V2-INTEGRITY-FAIL` because its literal no-TEST-access rule contradicted its
transductive data loader. At V3 freeze, no V2 training JSON/checkpoint content,
Software TEST ranking, per-user endpoint, V3 training trajectory, or V3 model
outcome has been inspected. V2 partial outputs are not reused. Software's
prepared structural counts, catalog identifiers, split hashes, and text-cache
coverage are known from the outcome-free preparation phase.

## Question and scope

On the prospectively held-out Software category, does the canonical learned
depthwise causal-FIR residual improve full-catalog next-item TEST NDCG@10 over
the same backbone with a frozen identity FIR control?

This is a same-investigator, same-code-lineage, same-Amazon-family category
confirmation attempt. It is not institutionally independent, is not a
non-Amazon replication, does not estimate category/population uncertainty, and
does not compare against a published system or establish state of the art.

## Explicit transductive-catalog boundary

Unlike V2, V3 explicitly permits the frozen trainer and preflight to open all
three split files before training solely to:

1. verify their registered SHA-256 digests;
2. construct the deterministic shared user/item reindex and full candidate
   catalog; and
3. record structural row/user/item counts.

This is a **transductive catalog**. TEST item identifiers, user identifiers, and
timestamps therefore enter the reindexing boundary. During training, TEST rows
may not be ranked or scored; no TEST metric, rank, hit, per-user record, or
model-selection signal may be computed or emitted. Validation NDCG@10 alone
selects the checkpoint. The manuscript must say "TEST scoring suppressed under
a transductive all-split catalog," never "TEST disabled" or "no TEST access."

## Frozen inputs and lineage

The registered split/cache digests are:

| Input | SHA-256 |
|---|---|
| `Software.train.csv` | `731c567c20b9cc58ee1270c3e281720f1a50b6e5d24c0494fa31861f17798246` |
| `Software.valid.csv` | `3f42eb8e0fe8b54cc4ad854755da29f455540c4a787eaa2744f36864944733c3` |
| `Software.test.csv` | `9e520fff20359a0fc130c8df7c4898f448aa140a90dffd82a64a60192574f863` |
| title cache | `2a1d09dea26c9c619a6d52ba2082c58ac23c03a04a7f02be30f5e9441098aa38` |
| sorted item map | `62e6a129e39dcead62922e096d6a36eef2527668a7bb8791822127440d36c7ae` |

Prepared counts remain 146,396 users, 17,591 items, 984,048 training rows,
146,396 validation rows, and 146,396 TEST rows. The preparation protocol,
feasibility record, acquisition manifest, title-cache manifest, and the exact MI
reference artifact from which V2's configuration lineage was originally
obtained are separately digest-bound by the V3 common module. Runtime V3 uses a
literal argument tuple and does not read that result artifact for configuration.

## Frozen model, configuration, and environment

Two arms differ only in `--fir-control`:

- `identity`: K=16 depthwise residual taps fixed at zero;
- `learned`: K=16 depthwise residual taps initialized at zero and trainable.

Both are exact identity at initialization. Each matched seed must have identical
backbone initialization hashes across arms; identity final tap norm must be zero
and learned final tap norm positive.

All other arguments are the literal ordered `BASE_ARGS` tuple in
`_bestrec_run/fir_prospective_sw_v3_common.py`: HSTU-style encoder, 20 epochs,
d=64, four layers, two heads, dropout 0.5, TAPE-512, time/text-similarity/
relative-position biases, label smoothing 0.2, warmup-cosine LR 0.001, batch
size 256, chunked full softmax, full-catalog validation, and best-validation
NDCG@10 checkpoint selection. The exact argv is checked before execution and
embedded in each result.

The runtime must exactly match
`_bestrec_run/fir_prospective_sw_v3_environment.json`: CPython 3.12.13,
PyTorch 2.11.0+cu128/CUDA 12.8, NumPy 2.4.4, SciPy 1.17.1, and NVIDIA GeForce
RTX 5060 Ti. The tagged `pyproject.toml` and `uv.lock` byte digests are checked.

## Seeds, order, and budget

Eight new optimizer seeds are fixed: 20261301--20261308. V2 seed numbers and
partial artifacts are excluded. There are exactly 16 20-epoch training runs.
Arm order alternates by seed to remove a fixed identity-first order: odd-indexed
blocks run identity then learned; even-indexed blocks run learned then identity.
No hyperparameter, seed, epoch, failed run, or order may be replaced, tuned, or
extended.

The eight-block budget is resource-based. No prospective power guarantee is
claimed. The +0.000500 threshold is the smallest effect the paper will call
practically positive; V3 strengthens V2 by requiring the confidence lower bound,
not merely the point estimate, to exceed this threshold.

## Custody and state machine

1. Before the first run, the driver exclusively creates an immutable ATTEMPT
   seal containing the tagged HEAD, environment, exact ordered jobs/argv hashes,
   input/reference hashes, and frozen-file hashes. An exclusive process lock
   prevents a second driver.
2. Every process rechecks exact tag/HEAD equality, clean tracked status,
   byte identity for the full frozen dependency set (including the model builder
   and adjudicator itself), environment, inputs, attempt, and exact argv.
3. Training uses `--no-test-eval --save-ckpt`. `best_test` must be null and no
   history entry may contain a TEST metric.
4. Only after all 16 JSON/checkpoint pairs pass validation does the driver
   exclusively create READY with every pair's digest.
5. The evaluator requires READY, creates an exclusive started seal before
   scoring, refuses repeats, emits endpoint JSON/per-user NPZ atomically, and
   prints no metric values.
6. After all 16 endpoint pairs exist, the driver hashes their bytes into an
   immutable ENDPOINTS-COMPLETE digest inventory and immediately invokes the
   committed adjudicator. The driver does not semantically parse endpoint files
   or inspect endpoint metrics; the adjudicator is the first intentional
   endpoint-content interpreter.

This is local same-user operational custody, not external escrow or independent
custody. A local administrator could bypass it; no claim of cryptographically
or institutionally enforced blindness is made. Attempt/READY/seal hashes and
the immediate driver handoff make deviations mechanically visible.

Any tag/HEAD/tree/environment/input/config/argv/hash mismatch, missing or
duplicate state seal, early TEST scoring, overwrite attempt, incomplete
evaluation seal, nonfinite endpoint, unmatched initialization, or V2-artifact
reuse is terminal `SW-V3-INTEGRITY-FAIL`; no scientific verdict follows.

## Endpoint and inference

Primary endpoint: per-seed full-catalog TEST NDCG@10 at the checkpoint with
maximum validation NDCG@10 over the fixed 20 epochs.

Sole inferential contrast: paired `learned - identity` across the eight matched
seed blocks. Report all eight differences, mean, sample SD, paired t statistic
(df=7), two-sided p-value, and ordinary two-sided 95% paired-t interval. Alpha
is .05; there is one test. HR@10 and MRR are descriptive only. The experimental
unit is optimizer seed on one fixed category/split. The interval does not cover
users, items, cutoffs, splits, categories, domains, or investigators. A retained
null is not equivalence.

## Frozen decision tree

1. Any integrity failure: `SW-V3-INTEGRITY-FAIL`; no scientific verdict.
2. If the ordinary 95% CI lower bound exceeds **+0.000500** and two-sided
   p<.05: `SW-V3-PRACTICAL-POS`.
3. If the CI lower bound exceeds zero and p<.05 but does not exceed +0.000500:
   `SW-V3-POS-BELOW-PRACTICAL`.
4. If the mean is negative, the CI upper bound is below zero, and p<.05:
   `SW-V3-NEG`.
5. Otherwise: `SW-V3-INCONCLUSIVE`.

Only outcome-neutral interpretation is permitted: report the exact verdict and
interval, preserve null/negative outcomes, and do not call the result
independent confirmation, generalization, or SOTA.
