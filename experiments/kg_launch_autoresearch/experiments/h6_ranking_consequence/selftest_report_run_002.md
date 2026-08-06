# H6 Run-002 Isolated Self-Test Report

Date: 2026-08-07

Final verdict: `PASS`

The final prospective implementation hashes are:

- Python runner:
  `7B5F9A71787EEFE1C2149597DCF401DDD455CC3B3222366750735DC11657D874`;
- PowerShell launcher:
  `9BE9A5BB44A7E4EDF8052BAC19210B38B7BB08653CD01C353CF8B10B2C000AC0`.

The isolated launcher used a disjoint self-test root and outer lock. The child
PID was `36028`; its recorded exit code was `0`. Standard error and the
asynchronous-error ledger were both zero bytes. The child reproduced the
runner, launcher, protocol, correction, base-interpreter, venv-launcher,
venv-config, and immutable-input hashes. The outer lock was released, no H6
lock remained, and none of `coverage_run_002`, `coverage_run_002_replay`, or
`coverage_run_002_completion.json` existed after the test.

The completion marker was written last at
`selftest_artifacts/st_67ac5348790148a5a621/selftest_completion.json`; its
SHA-256 is
`FA456A351F4292758B3F4324AA58EE0ADE849F46DDDB53B45DFB8CAB83995096`.
Raw self-test launch artifacts remain local and are ignored by Git; this report
and the implementation lock retain the decision-bearing provenance.

Two preceding isolated attempts did not publish completion markers. In the
first, the Python test passed but a 272-character failure-release pathname
masked the initiating launcher error. After shortening all dynamic paths, the
second exposed the initiating cause: Windows PowerShell 5.1 returned a null
`ExitCode` for a redirected `Start-Process` object even though the exact child
had exited cleanly. A harmless redirected `cmd.exe` diagnostic independently
reproduced that behavior. The final launcher materializes `.Handle`
immediately, rejects a null exit code, retries and verifies exact termination,
and preserves original plus cleanup exceptions. These were execution-safety
corrections before confirmatory data execution, not scientific reruns.
