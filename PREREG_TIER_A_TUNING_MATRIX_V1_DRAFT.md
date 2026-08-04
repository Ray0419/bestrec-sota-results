# Draft preregistration: Tier-A baseline tuning matrix

Protocol identifier: `DRAFT_TIER_A_TUNING_MATRIX_V1`

Status: **DRAFT ONLY — NOT FROZEN, NOT AUTHORIZED, AND NO TRAINING OR TEST
EVALUATION MAY START.** Existing outcomes are known. Claude must audit baseline
selection and search-space fairness; the human maintainer must approve compute,
data, licensing, and the target venue before freeze.

## 1. Purpose and claim ceiling

Test whether the paper's FIR intervention remains competitive when strong simple,
backbone, and current sequential-recommendation baselines receive symmetric,
documented validation-only selection opportunities under the same task semantics.

This matrix can support a fair-comparison claim within the tested datasets. It
cannot establish SOTA, universal superiority, equal capacity, equal wall-clock
cost, causal effects, or independence.

## 2. Dataset blocks

The final freeze must name each block and its evidence class. Proposed structure:

1. one existing Amazon category used only as an outcome-known calibration block;
2. the existing MovieLens block, retaining its negative FIR result;
3. one lawful new non-Amazon block chosen through
   `TIER_A_NON_AMAZON_SELECTION_GATE.md` before target-outcome inspection.

No dataset may be added or removed after its tuning outcomes are visible. All
methods within a block use the same raw-source version, cohort, split, history
cutoff, candidate universe, exclusion rules, evaluator, and primary metric.

## 3. Method families

The frozen matrix must contain:

- deterministic `MostPop` as a no-tuning floor;
- one strong classical personalized baseline appropriate to the task;
- `GRU4Rec` or an equally established recurrent sequential baseline;
- `SASRec` with normal initialization;
- the paper's HSTU-style identity backbone;
- the learned FIR intervention on that backbone;
- one current frequency/long-convolution/state-space recommender selected from a
  primary-source literature and implementation audit.

Claude must approve exact inclusions and exclusions. A method whose official code
cannot implement the same full-catalog leave-one-out task is contextual only and
cannot populate a direct-comparison cell.

## 4. Symmetric validation-only selection ladder

Proposed ladder for every tunable method in every dataset block:

### Stage S0 — compatibility, outside the search count

One tiny TRAIN/VALID-only smoke run verifies shape, masking, candidate semantics,
finite loss, deterministic resume, and metric wiring. It may not be used to choose
a hyperparameter or inspect TEST. Failure permits an implementation repair followed
by a new frozen source hash, not extra search information.

### Stage S1 — broad search

- exactly 12 pre-generated configurations per method;
- one frozen tuning seed per configuration;
- method-specific spaces justified from official code/papers, with the same number
  of selection opportunities rather than artificial identical parameter ranges;
- identical dataset split, maximum epochs, validation cadence, patience, metric,
  tie handling, and non-finite/OOM rule;
- no TEST access and no replacement configuration after outcomes are visible.

Use a committed low-discrepancy schedule or complete discrete grid generated before
launch. The configuration list and hashes are frozen, not sampled adaptively.

### Stage S2 — stability selection

- promote exactly the top three S1 configurations by validation NDCG@10;
- retrain each on three fresh, shared optimizer-seed blocks;
- choose the highest mean validation NDCG@10;
- if means tie at the frozen numeric precision, choose lower measured search cost,
  then fewer trainable parameters, then lexical configuration identifier.

No method-specific rescue, extra seed, extended patience, or post-hoc search-space
expansion is permitted.

### Stage S3 — sealed evaluation

Train the selected configuration on eight fresh shared seed blocks. Require all
terminal TRAIN/VALID records and family READY before a sealed evaluator can read
TEST. A committed adjudicator is the first endpoint reader. Report every seed,
mean, sample SD, paired interval, raw and adjusted tests, parameters, training
time, peak memory, energy data if available, and total search cost.

## 5. Fairness and compute rules

Equal search opportunities do not imply equal runtime. The freeze must report both:

- selection budget: configurations, seeds, epochs, validation calls;
- realized resource cost: accelerator type, wall-clock, GPU-hours, peak memory,
  failed runs, and total search plus final-training cost.

If one method cannot complete the common maximum on available hardware, its fixed
OOM/timeout disposition applies to every method. Reducing only that model, giving it
more hardware, or silently excluding failures is forbidden unless the entire matrix
is refrozen before any outcome is visible.

Deterministic/no-tuning methods do not receive fake trials; their zero search budget
is reported explicitly. Official defaults may be included as one of the 12 S1
configurations but are not automatically selected.

## 6. Search-space record

Before freeze, every tunable method needs a table containing:

```text
METHOD + IMPLEMENTATION COMMIT:
LOCAL PATCH + JUSTIFICATION:
TRAINABLE PARAMETERS:
PARAMETER / DOMAIN / SAMPLING RULE:
OFFICIAL SOURCE FOR DOMAIN:
12 CONFIGURATION IDS + HASH:
TUNING SEED / STABILITY SEEDS / FINAL SEEDS:
MAX EPOCHS / VALIDATION CADENCE / PATIENCE:
OOM / NON-FINITE / INTERRUPT RULE:
EXPECTED RESOURCE ENVELOPE:
```

## 7. Inference and reporting

The primary family compares FIR with the frozen identity backbone and the selected
strong current baseline within each dataset. Cross-dataset synthesis, if any, must
be declared before TEST and treat datasets—not optimizer seeds—as the generalization
unit. Seed-level intervals on one fixed split remain conditional on that split.

All registered outcomes are retained. A baseline win narrows or falsifies the paper's
claim; it does not trigger extra FIR tuning. An FIR win supports only the tested
protocol-compatible comparisons, not SOTA.

## 8. Prelaunch blockers

- exact ranking authority, journal, and method shortlist;
- lawful dataset and redistribution decisions;
- search-space tables and generated configuration manifest;
- resource ceiling and failure policy;
- fresh unused seed blocks and proof of no target artifacts;
- common trainer/evaluator semantics and structural tests;
- sealed endpoint custody and first-reader adjudicator;
- Claude's dated reject/approve memo;
- human approval.

Until all are resolved, no directory, seed, checkpoint, or endpoint may be created
under this protocol identifier.
