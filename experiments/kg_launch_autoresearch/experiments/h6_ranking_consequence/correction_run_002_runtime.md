# H6 Phase-A Runtime-Engine Correction

Status: locked before `coverage_run_002`

Date locked: 2026-08-07

## Why run 001 was stopped

The committed PowerShell runner was launched through explicit 64-bit Windows
PowerShell 5.1 with persistent stdout/stderr files. The exact child PID was
`35388`. After 738.6 seconds it remained responsive and single-core, but had
read only a small fraction of `behaviors.tsv`; observed throughput projected a
multi-hour Phase-A run and replay. It was terminated before publication.

At termination:

- stdout: 0 bytes;
- stderr: 0 bytes;
- final `coverage_run_001` directory: absent;
- result JSON: absent; and
- partial label-blind manifest: 33,554,432 bytes, preserved locally as
  `results/aborted_runtime_run_001/cohort_manifest.jsonl` and excluded from
  Git.

No metric, gate, cohort total, click label, or partial manifest content was
inspected. Run 001 is an implementation/runtime abort, not scientific evidence.

## Locked correction

`coverage_run_002` may replace only the execution engine with a vectorized
single-process Python implementation. The committed H6 protocol remains
binding without change to:

- input files or hashes;
- H5 top-50 anchors and confidence threshold;
- MIND relation vocabulary and both sensitivity views;
- last-50 history and all-candidate cohort rules;
- shared-fact kernel and normalization;
- SHA-256 tie rule and `1e-12` tolerance;
- reported coverage/rank-change metrics; or
- any advance/kill threshold.

The implementation must use the repository Windows-safe execution contract:
direct workspace-venv interpreter image, `-B -u`, all numerical thread bounds
set to one before NumPy import, persistent stdout/stderr, hidden process, PID
handshake, inner and outer locks, asynchronous exception ledger, atomic
no-overwrite artifacts, post-exit verification, and a completion marker written
last. `coverage_run_002` is accepted only if an exact second replay produces an
identical cohort-manifest hash and result metrics.

The correction is invalid if code opens or aggregates candidate click suffixes.
