# RAVEL v1 Pre-outcome Audit and Freeze Record

Date: 2026-08-07
Status: passed before any RAVEL `T` outcome access

## Outcome seal

- No RAVEL experiment was launched during protocol design, implementation, or audit.
- No RAVEL held-out `T` item identity, rating, metric, result, or run artifact was opened.
- All audits used source, configuration, protocol text, synthetic fixtures, and cryptographic provenance only.
- The sole authenticated MovieLens archive was streamed only for SHA-256 verification. Its contents were not parsed during this audit.
- The RAVEL cohort remains the prospectively declared SHA-ordered eligible-user slice `[1000:2000]`, disjoint from CAPER `[0:1000]`.

## Audit findings resolved before freeze

1. Replaced a runner-attested completion check with an external scientific replay that reconstructs all validation operating-point selection, raw test summaries, deterministic bootstraps, exact G1-G10, fallback bytes, projection invariants, latency, immutability, and provenance.
2. Bound the launcher/verifier and local archive hashes into the launch and completion records.
3. Corrected the selector descriptor to use top-10 Jaccard overlap and the registered zero-swap sign-agreement convention.
4. Persisted exact float32 query bytes, branch ranks and membership, seen-filter evidence, and immutable index hashes for all R/V/T candidate manifests.
5. Persisted raw per-user latency medians and the registered schedule before the single test join.
6. Preserved the frozen-linear order for every nonselected item in a finite proposal, preventing unconstrained tail inversions from driving the primary preference gate.
7. Defined the always-on G4 comparator as unconditional service of the exact same selected finite proposal, isolating only the selector decision.
8. Defined G5 accepted pair-bearing support as `sum_u mean_s[accepted(u,s) * 1(preference_pairs(u,s)>0)]`, requiring acceptance and pair support in the same seed row.

The final independent source audit found no remaining P0 or P1 issue.

## Outcome-free verification commands

All commands used `C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe` and completed successfully:

```text
python -B -m py_compile adaptive-recsys-ara/src/ravel_poc.py adaptive-recsys-ara/src/launch_ravel_and_verify.py
python -B adaptive-recsys-ara/src/ravel_poc.py --validate-config
python -B adaptive-recsys-ara/src/ravel_poc.py --self-test
python -B adaptive-recsys-ara/src/launch_ravel_and_verify.py --help
python -B adaptive-recsys-ara/src/launch_ravel_and_verify.py --self-test
git diff --check -- adaptive-recsys-ara
```

Runner self-test: all 11 checks true, including `sealed_outcomes_accessed=false`.
Launcher self-test: all 10 checks true, including `outcomes_accessed=false` and `models_rerun=false`.

## Frozen SHA-256 bindings

| Artifact | SHA-256 |
|---|---|
| `src/ravel_poc.py` | `33e28a21cfbd2408b3dde4edfa27023cdc5a4afc02982583584acbd3bb4344be` |
| `src/launch_ravel_and_verify.py` | `a7c008ea35b98c77564ebecd90ad2deb891171dc2d50ea444fa2d69afa80242c` |
| `src/caper_poc.py` | `9ddd41c2db74424dfed8672933144147af6f9c6b49745ada13611c2cbac1588c` |
| `src/configs/ravel_poc_ml1m_v1.json` | `5a7a6a5f5c592648ce3a96ad6632498dba41cb52e353b4954ef6f5917177500e` |
| `experiments/ravel-protocol-v1.md` | `eeaf57472fb5adeaafb8f0d121baafe0f2b3f4ce3c86d67d9efbeb95d79757a2` |
| `research-question-cycle3.md` | `dea1c8960cc0c47de027120ed8c0984f4451793c3243320b31988950ba97a9cc` |
| `literature/cycle3-survey-and-ideation.md` | `ae044349df370a52bf6cc57b58b85d742534357a5fc86f387aac6f320975b9ec` |
| `architecture-cycle3.md` | `99acaf002a8f12b8129886db7e3dd0d33a8732c6972f52553c457fe1468c3be6` |
| repository Windows-safe execution contract | `93cd350b6f9eecd5e1bbbbe0fa430f8f1dbff6137e02128ade3ee8beda6c9af1` |
| authenticated MovieLens 1M archive | `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20` |

## Gate and kill rule

The PoC is promising only if the exact conjunction `G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9 & G10` passes under the inequalities and strictness registered in `ravel-protocol-v1.md`. Any failed gate, missing statistic, provenance failure, nonzero error ledger, or incomplete external replay kills RAVEL v1 immediately. A failure prohibits Phase 5 and returns the sprint to Phase 1 with no outcome rerun, threshold repair, cohort substitution, or discretionary override.
