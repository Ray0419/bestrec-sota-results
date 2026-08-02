# FMLP-Rec causalization pilot decision - 2026-08-02

## Decision

**Do not launch the planned training run. The proposed experiment is redundant,
and the leakage motivation does not apply to the evaluated objective.**

The frozen structural test behaved as expected:

| layer | maximum change in an earlier output after a future-input perturbation |
|---|---:|
| circular frequency filter (`full`) | 0.274439 |
| left-causal FIR (`causal_full`) | 0 |
| channel-shared left-causal FIR (`causal_shared`) | 0 |

This proves prefix invariance of the causal implementations. It does **not**
establish target leakage in FMLP-Rec. Both the local BSARec-suite harness and
the original FMLP-Rec release construct a separate prefix example, exclude its
next-item target from the input, and apply loss only to the final sequence
output. The earlier outputs affected by the perturbation test are not supervised
or used for ranking. The circular filter can therefore use every item in the
observed prefix without seeing the held-out target.

After freezing the pilot, existing five-seed ML-1M `causal_full` checkpoints and
their projection analyses were located in the repository. They already answer
the proposed accuracy feasibility question with broader evidence than the new
single-seed run. Launching it would spend compute without creating an
independent estimand.

The prefix test remains a useful implementation test for models trained with an
all-position objective. Causal FIR itself, however, is established prior art,
and this check does not support a new FMLP-Rec correctness claim.
