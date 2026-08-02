# Analysis plan: causal-FIR post-hoc projection pilot v1

Frozen on 2026-08-02 before the first projected causal-FIR checkpoint was
evaluated. This is an outcome-visible, exploratory mechanism screen. It cannot
license a confirmatory or generalization claim.

## Question

Does the train-rich/deploy-structured reversal observed retrospectively in an
FMLP-Rec frequency filter transfer to the paper's left-causal additive FIR?

## Frozen screen

- Source checkpoint: the validation-selected `learned` FIR-control checkpoint
  for Musical_Instruments seed `20260901`.
- Evaluation data: validation targets only. Test targets and test history are
  not loaded or scored.
- Users: a fixed uniform sample of 10,000 validation users selected with NumPy
  `RandomState(314159)` from sorted validation user IDs.
- Candidate set, seen-item masking, model reconstruction, and ranking tie rule
  are inherited unchanged from the original evaluator.
- Project only `fir_control_module.weight`, interpreted as a 64 by 16 matrix of
  learned additive causal taps. Do not alter the fixed identity residual.
- `rank1`: its best Frobenius rank-1 SVD approximation.
- `shared`: the row mean repeated over all 64 channels.
- No fine-tuning and no test evaluation.

The primary screen is `rank1`. `shared` is a diagnostic because the trained
shared arm already establishes that sharing from initialization can work on
this corpus.

## Frozen decision

Advance `rank1` to all eight existing checkpoints and full validation only if:

1. projected minus baseline validation NDCG@10 is at least `-0.0005` on the
   fixed sample;
2. the paired-user 95% bootstrap lower bound is above `-0.0010`; and
3. no evaluator-integrity or catalog-reconstruction check fails.

Otherwise reject this transfer. The screen does not inspect or optimize a
projection threshold. Any full-validation pass remains exploratory and needs a
new decision memo before launch.

## Pre-outcome catalog erratum

Initial frozen file SHA-256 before this erratum:
`b6e443f8d8f06b0875fa0b064edc018e584ae60e50949840797fa41b6f0cee1e`.

The first evaluator invocation stopped before model construction or scoring:
train plus validation contain 24,584 item IDs while the frozen checkpoint has
24,587 item rows. The missing three identifiers occur only in the test split.
To reproduce the checkpoint's candidate ordering, the repaired evaluator may
read the `parent_asin` column of the test CSV solely to form the sorted candidate
ID set. It must not read or retain test user IDs, ratings, timestamps, or
user-target associations, and it must not score a test row. The artifact records
this metadata-only access explicitly. All decision thresholds above are
unchanged.
