# Software prospective FIR V2 - terminal integrity record

Protocol: `PREREG_FIR_PROSPECTIVE_SW_V2`

Verdict: **`SW-V2-INTEGRITY-FAIL` (VOID; no scientific verdict)**

Detected and stopped: 2026-07-28 10:24:46 Australia/Sydney.

## Reason

The frozen protocol states that all 16 best-validation checkpoints must exist
before the first TEST access and makes early TEST access a terminal integrity
failure. The frozen implementation violated that literal rule before producing
an endpoint:

- `_bestrec_run/run_fir_prospective_sw_v2.py` preflight opened
  `Software.test.csv` while constructing the item set;
- `_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py`, imported by the V2
  custody wrapper, loaded train, validation, and TEST rows and passed all three
  to `reindex()` before training;
- `--no-test-eval` suppressed TEST scoring and metric emission, but it did not
  suppress TEST-file access.

The contradiction was identified from source inspection during the campaign.
It is not repaired or reinterpreted after launch. V2 is permanently VOID under
its own decision tree, regardless of any eventual numerical result.

## Outcome-visibility boundary at termination

No final-evaluation seal, endpoint JSON, or per-user endpoint sidecar existed.
No training JSON or checkpoint content was opened during diagnosis. Process,
file-name, size, timestamp, and digest metadata only were inspected. The driver
and its active training child were terminated without deleting or overwriting
any partial artifact.

Observed partial artifacts in the clean execution clone at termination:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `results_Software_FIRPROSPV2_identity_seed20261201.best.pt` | 68,252,613 | `8b3854fe9e2afa1f915fd69031daaa8c306ca794697b4e9689379115844b3e4c` |
| `results_Software_FIRPROSPV2_identity_seed20261201.json` | 36,347 | `1d82433f979361e67eccfd8d5ec8469f1cdf1be9edf0e330213631cf28bc4c84` |
| `results_Software_FIRPROSPV2_learned_seed20261201.best.pt` | 68,252,562 | `d6518fe300ad2ab991fcd19f39cddfef42e225fa7d9bdd7eae5b9a4fd5c8f270` |

Counts at termination: one completed training JSON, two checkpoint files, zero
started-evaluation seals, zero final-evaluation JSONs, and zero endpoint
sidecars. The execution clone remained at exact frozen HEAD
`c1048ba652c3ca2958c8aabc98f45702e51bfc75` with no tracked modification.

## Consequence

These partial V2 artifacts are retained only as custody evidence and are not
eligible for the manuscript's numerical graph, release result families, or any
scientific claim. A successor protocol must be frozen at a new commit before
launch, use new seeds, state any transductive-catalog access explicitly, and
mechanically bind the complete configuration, executable dependency set,
environment, exact commit, attempt state, and endpoint boundary.
