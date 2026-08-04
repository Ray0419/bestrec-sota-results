# PREREG_FIR_EFFICIENCY_ML1M_V1

**Status: FROZEN DESIGN—NOT AUTHORIZED TO ACQUIRE DATA OR LAUNCH UNTIL THE
HASH-FILLED FREEZE COMMIT IS PUSHED.**  The frozen adjudicator digests, clean
preflight, and remote commit must all exist before the first download of
MovieLens records.  Until then, only the official public README, aggregate
dataset description, code, and structural tests may be inspected.

## 1. Question and claim boundary

The audit identified two linked gaps: all current FIR results use Amazon review
categories, and the 1,024-parameter per-channel FIR did not separate from a
16-parameter channel-shared FIR.  This prospective study asks, on one previously
uninspected non-Amazon dataset:

1. Does the per-channel causal FIR improve full-catalog next-item NDCG@10 over
   its matched identity control?
2. Are shared, grouped, or low-rank causal FIR parameterizations noninferior to
   the per-channel FIR within an absolute margin of **0.000500 NDCG@10**?
3. How do the six frozen arms compare in trainable filter parameters, measured
   FLOPs, inference latency, peak GPU memory, and training time?
4. Does the result persist when all 1–5-star ratings, rather than ratings at
   least 4, are treated as positive events?

The 0.000500 margin is a frozen measurement-scale smallest effect of interest:
it matches the paper's earlier prospective practical-reporting threshold, is
0.05 percentage points on the bounded NDCG scale, and is deliberately stricter
than the 0.001-level alternative considered during design.  It is **not** an
externally validated product or business KPI.

Permitted language is “prospectively frozen same-investigator non-Amazon
robustness/efficiency evidence.”  One MovieLens dataset, local custody, and the
same code lineage do **not** provide independent confirmation or population-wide
generalization.  A retained superiority test is not equivalence; noninferiority
is claimed only under the exact frozen margin and test family below.

## 2. Source, license, and untouched boundary

Source: GroupLens MovieLens 1M, official archive
<https://files.grouplens.org/datasets/movielens/ml-1m.zip>.  The official archive
MD5 is `c4d9eecfca2ab87c1945afe126590906`.  The official README reports 1,000,209
anonymous 1–5-star ratings from 6,040 users, timestamps in epoch seconds, and at
least 20 ratings per included user:
<https://files.grouplens.org/datasets/movielens/ml-1m-README.txt>.  Dataset use
will be acknowledged with Harper and Konstan (2015), DOI 10.1145/2827872.

Before the freeze commit, no `ml-1m.zip`, `ratings.dat`, transformed split,
per-user endpoint, or experimental outcome may exist in the campaign's private
root.  Viewing the official README, its checksum, and aggregate source
description is not outcome inspection.  The acquisition script must validate
the official MD5 before extraction and record SHA-256 digests after acquisition.

The ML-1M README prohibits redistribution without separate permission.  Raw
records, transformed splits, per-user sidecars, checkpoints, and sealed endpoint
files therefore remain in ignored `_bestrec_run/private_ml1m_v1/`.  Public
artifacts may contain code, aggregate counts, cryptographic digests, aggregate
statistics, and the adjudication only.  This license boundary must be stated in
the manuscript and release README; no fail-closed release rule may silently
upload record-level MovieLens artifacts.

## 3. Deterministic data construction

Two views are built from the same validated archive without manual inspection:

- **Primary `MovieLens1M_R4`:** retain ratings ≥4 as positive preference events.
- **Sensitivity `MovieLens1M_ALL`:** retain all ratings ≥1 as implicit events.

For each view independently:

1. Sort qualifying records by `(timestamp,user_id,movie_id,rating)`.
2. Let the global cutoff be the timestamp at zero-based index
   `ceil(0.90*N)-1`; records at or before it are pre-cutoff.
3. For each user, require at least six pre-cutoff events and one post-cutoff
   event.  The last pre-cutoff event is the validation target; all earlier
   pre-cutoff events are candidate training history; the first post-cutoff
   event is the sealed TEST target.
4. Build the eligible catalog using candidate-training events only and retain
   items with at least five candidate-training events.
5. Retain a user only if at least five of their candidate-training events and
   both their validation and TEST targets are in that training-observed catalog.
6. Recompute the ≥5-event catalog over retained users' training events and
   repeat user/catalog filtering to a fixed point.  Assert that every retained
   validation and TEST user/item occurs in the final TRAIN file.
7. Training contains the retained in-catalog history, validation contains one
   last-pre-cutoff target per user, and TEST contains one first-post-cutoff
   target per user.  Validation-only checkpoint selection appends the validation
   event to history for the later sealed TEST query.

This design makes the primary estimand the next ≥4-star movie after a global
time boundary, conditional on at least five eligible pre-cutoff positive events
and a training-observed item.  It addresses the earlier rating-agnostic,
per-user-only, and future-catalog concerns.  It does not model unobserved
exposure, dislike, watch completion, or deployment engagement.

## 4. Frozen arms

All arms insert one residual immediately before the sequence encoder.  Temporal
arms use a length-16 left-padded depthwise causal convolution; no output at time
`t` may depend on an input after `t`.  Every active arm is the exact identity map
at initialization and has a nonzero gradient path at that point.  The structural
test must verify parameter counts, exact identity, gradients, and causality.

| Arm | Frozen construction | Trainable filter parameters |
|---|---|---:|
| identity | registered zero per-channel kernel, frozen | 0 |
| shared | one learned length-16 kernel broadcast to 64 channels | 16 |
| grouped | eight learned kernels, one per fixed contiguous 8-channel group | 128 |
| lowrank | `W=A V0 + U0 B`, rank `R=4`, fixed orthonormal DCT bases `U0,V0`, zero-init learned `A,B`; realized rank ≤8 | 320 |
| learned | one learned length-16 kernel per channel | 1,024 |
| pointwise | current-position-only DCT/GELU/linear residual | 1,024 |

The pointwise arm is the same equal-parameter compound non-temporal placebo used
in the prior phase; it changes temporal access, basis/rank, activation, and
channel mixing together.  It can discriminate this compound placebo but cannot
alone isolate temporal access.

## 5. Frozen optimization and run family

No MovieLens hyperparameter tuning is permitted.  The configuration is
transferred unchanged from the existing canonical Musical Instruments FIR
configuration: 20 epochs, batch size 256, maximum sequence length 50, `d=64`,
four Transformer layers, two heads, dropout 0.5, Adam learning rate 0.001 and
weight decay 1e-5, full-catalog chunked softmax, label smoothing 0.2, one training
example per user per epoch, warmup-cosine schedule, validation every epoch, and
no text features.  The six arms receive identical budgets.

Seeds are `20261101` through `20261108`.  Both views run all six arms at all
eight seeds: **96 training runs**.  Within each `(view,seed)` block, every arm
must have the same `backbone_init_sha256`.  The filter-specific parameter names
are excluded from that backbone digest; all other initialized parameters and
buffers must match.

Every training run uses
`--no-test-eval --sequester-test-load --save-ckpt`.  Its history and summary
must contain no TEST metric.  Training must not open or hash TEST bytes: its
user/item mapping is constructed from TRAIN+VALID, and provenance must record
TEST interactions as zero and the TEST digest as null.  The driver finishes all
96 training runs before it
invokes any TEST evaluator.  Each selected checkpoint receives exactly one
sealed TEST evaluation.  Existing run, checkpoint, STARTED seal, final endpoint,
or sidecar files are never overwritten.  An incomplete STARTED seal is a hard
stop requiring diagnosis under this frozen protocol, not deletion or rerun.

## 6. Endpoints and efficiency measurement

The primary accuracy endpoint is mean full-catalog TEST NDCG@10 across retained
users in `MovieLens1M_R4`.  HR@10 and MRR are descriptive.  The all-rating view
is a named construct sensitivity and cannot change the primary verdict.

The frozen evaluator also benchmarks end-to-end next-item scoring on the first
256 sorted TEST users: encode a length-50 history and score the query against the
full catalog.  After 20 warmups it records 50 synchronized repetitions, median
and p95 latency, PyTorch operation-count FLOPs, and peak allocated CUDA memory.
Training JSON records total wall time and peak allocated CUDA memory.  The
adjudicator reports medians across eight seeds.  Hardware/software identity must
be recorded.  Latency and memory are descriptive because a single local device
does not support hardware-general efficiency inference.

## 7. Frozen inference and verdict

### 7.1 FIR replication and placebo family

On primary per-seed NDCG@10, compute ordinary paired two-sided t-tests and 95%
confidence intervals for `learned−identity` and `learned−pointwise`.  Apply Holm
at family α=.05.  A contrast is positive only if its mean and CI lower bound are
above zero and Holm rejects.  Failure of `learned−identity` yields
`ML1M-NO-FIR-REPLICATION`, regardless of the parsimony tests.  A positive
`learned−pointwise` permits discrimination from that named compound placebo but
not a general temporal-access claim.

### 7.2 Parsimony noninferiority family

For shared, grouped, and lowrank, let `d = candidate−learned`.  Test the one-sided
null `H0: mean(d) ≤ −0.000500` with a paired t statistic across eight seeds.
Apply Holm to the three one-sided p-values.  Also compute a one-sided
Bonferroni-simultaneous lower bound using confidence `1−.05/3`.  A candidate
passes only if Holm rejects **and** its simultaneous lower bound is strictly
greater than −0.000500.  The verdict selects the smallest passing arm in this
fixed order:

1. `ML1M-SHARED-NI`
2. `ML1M-GROUPED-NI`
3. `ML1M-LOWRANK-NI`
4. otherwise, if learned replicated, `ML1M-PERCHANNEL-ONLY`.

Passing noninferiority does not establish equality or superiority.  Filter
parameter reduction is exact; measured FLOPs/latency/memory remain descriptive
and may show no advantage.

### 7.3 Cluster sensitivities

For each parsimony candidate, average the paired per-user NDCG difference over
the eight seeds, then compute a deterministic 10,000-replicate percentile
bootstrap over users.  Separately average those differences within TEST target
item and bootstrap target items for an item-macro interval.  RNG seed is
`20261190`.  These are fixed-dataset sensitivity intervals, do not alter the
verdict, and do not convert users or items into independent dataset replications.

## 8. First reader, custody, failure, and reporting

The committed `adjudicate_fir_efficiency_ml1m_v1.py` is the first authorized
endpoint reader, and only after the status file says all 96 training and 96
sealed evaluations are complete.  It must verify frozen LF hashes, exact config,
clean tracked checkout, shared backbone initialization, checkpoint and seal
bindings, split hashes, per-user reconstruction, parameter counts, resource
fields, and all required artifacts before printing or writing any outcome.

This is local same-investigator custody.  A first-reader rule and hashes do not
prove non-visibility to the investigator and are not external escrow.  The paper
must report the exact mechanical verdict, negative and neutral outcomes with the
same prominence as positive ones, and the all-rating and cluster sensitivities.
No seed extension, margin change, arm substitution, data filtering change, or
outcome-dependent rerun is permitted.  Infrastructure failure may resume only
from intact non-overwritten artifacts under the frozen code and design.
