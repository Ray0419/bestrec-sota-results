# Draft preregistration: matched-input FIR temporal-isolation study

Protocol identifier: `DRAFT_FIR_TEMPORAL_ISOLATION_V1`

Status: **DRAFT ONLY — NOT FROZEN, NOT AUTHORIZED, AND NO RUN MAY START.** The
prior FIR and pointwise outcomes are known. This document exists for Claude's
reject-first design review and human approval. It confers no prospective status.

## 1. Question and admissible estimand

Does the canonical learned depthwise FIR using K distinct left-causal states
outperform an otherwise identical learned residual whose K tap inputs are all
the current state?

The comparison changes the input geometry supplied to the same parameterization.
It does not establish universal temporal necessity, causal effects in users,
cross-domain generalization, independent confirmation, or SOTA.

## 2. Matched arms

Both active arms use one zero-initialized `D × K` tap tensor, the same residual
location, activation, normalization, optimizer treatment, and training budget.
Within a seed block they share the exact backbone initialization hash.

For state `x[t,c]` and tap weights `w[c,k]`:

```text
lagged_fir[t,c]       = sum_k w[c,k] * x[t-k,c]
repeated_current[t,c] = sum_k w[c,k] * x[t,c]
```

Left padding and padding masks are identical. Neither arm can read future
positions. `repeated_current` deliberately retains K trainable weights per
channel even though its inputs are repeated; this preserves parameter count and
optimization surface dimensions while removing earlier-state access. The
functional collapse of the repeated inputs is part of the estimand and must be
discussed, not hidden.

Proposed arms:

1. `identity`: frozen zero residual, used only as a replication diagnostic;
2. `lagged_fir`: K true causal lag inputs;
3. `repeated_current`: K copies of the current state.

No DCT basis, GELU-only placebo, channel mixing, rank projection, or arm-specific
normalization is allowed. The prior pointwise study remains reported separately.

## 3. Design items that must be resolved before freeze

- dataset(s), lawful source, exact split/candidate universe, and whether any
  outcome is genuinely unseen;
- `D`, `K`, backbone configuration, training epochs, tuning/search budget, and
  fresh unused seed blocks;
- whether weights receive identical regularization and whether repeated-current
  degeneracy creates an optimization objection requiring an additional
  diagnostic, without changing the primary estimand;
- TEST custody and whether an external collaborator can control the endpoint;
- primary endpoint, inferential unit, multiplicity family, minimum reporting
  threshold, and complete negative/null decision tree;
- resource budget and one-GPU concurrency policy;
- exact artifact-release and data-license boundary.

## 4. Proposed inference skeleton

Use matched optimizer-seed blocks on each fixed split. The primary contrast is
`lagged_fir - repeated_current`; `lagged_fir - identity` and
`repeated_current - identity` are diagnostics in one predeclared multiplicity
family. Report every paired seed difference, mean, sample SD, ordinary paired
95% interval, raw p-value, and the chosen multiplicity-adjusted decision.

Dataset-level claims require multiple datasets and a predeclared synthesis;
seed-level inference on one fixed split does not quantify dataset, cutoff, user,
or population sampling uncertainty. A fixed-split user/item bootstrap may be a
sensitivity analysis only.

## 5. Outcome-conditional wording

- If lagged FIR is positive under the frozen rule: "The lagged-input FIR
  outperformed the tested repeated-current control under matched
  parameterization and budget."
- If the interval overlaps zero: "The study did not discriminate the lagged and
  repeated-current arms; this is not equivalence."
- If repeated-current is positive: "The repeated-current control outperformed
  the lagged arm; temporal-input benefit is not supported in this setting."
- If the replication diagnostic fails: report the failure and do not interpret
  the primary contrast as a replication of the earlier FIR effect.

No outcome is called independent unless a genuinely independent team executes
the study under documented external custody.

## 6. Required prelaunch artifacts

Before any launch, Codex must provide a frozen common module, runner, structural
test, TEST-free trainer, READY builder, sealed evaluator, driver, and mechanical
adjudicator. Claude must provide a signed reject/approve design memo. The human
must approve dataset/legal/custody choices. All artifacts and hashes must be
committed and pushed, and a no-target-artifact scan must pass.

Until those conditions are met, this file must remain `DRAFT` and no seed,
checkpoint, or endpoint may be created under this protocol identifier.
