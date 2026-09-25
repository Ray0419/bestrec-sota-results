# H6 Phase-A Run-002 Implementation Lock

Status: frozen before confirmatory `coverage_run_002`

Date locked: 2026-08-07

## Bound implementation

- Scientific runner: `code/run_h6_phase_a_coverage.py`
- Runner SHA-256:
  `7B5F9A71787EEFE1C2149597DCF401DDD455CC3B3222366750735DC11657D874`
- Windows-safe launcher: `code/run_h6_phase_a_coverage_safe.ps1`
- Launcher SHA-256:
  `9BE9A5BB44A7E4EDF8052BAC19210B38B7BB08653CD01C353CF8B10B2C000AC0`
- Locked protocol SHA-256:
  `53EAE6D5D19982DD5E6926F563A6D327A5A1AF47DFC5CF58DA4D54D1D61DB0A4`
- Runtime-engine correction SHA-256:
  `FE9E092F9A4C310FE3951123ADDD4451E342BEB969A021F7BCA137098A5B8BE6`
- Workspace venv launcher SHA-256:
  `BAD34B1F39DAD6A375E594AAF006FE84CD96A7AE46F6F2FA84C0536003234AC9`
- Base CPython image SHA-256:
  `4F461F0C0DE64E82EB54FBCED0FD1D678D79D34EDA38660B07781E2BBA8064D6`
- `pyvenv.cfg` SHA-256:
  `A59AE8BCAFF3472F99A259F89DFF2BE70AB8674AADEB5B26D574A237A7FF2426`

The launcher invokes the bound base CPython image directly so that
`Start-Process` owns the real child PID, and sets the bound
`__PYVENV_LAUNCHER__` path. The child must reproduce the workspace venv as
`sys.executable` and `sys.prefix`, and the bound base image/home as
`sys._base_executable` and `sys.base_prefix`. This is the operational meaning
of the runtime correction's direct-workspace-venv requirement on native
Windows; both images and the venv configuration are independently hash-bound.

## Frozen execution and outputs

- Primary output ID: `coverage_run_002`, role `primary`.
- Exact replay output ID: `coverage_run_002_replay`, role `exact_replay`.
- Final marker: `results/coverage_run_002_completion.json`.
- Direct base-image launch with `-B -u`, hidden window, persistent stdout and
  stderr, `PYTHONHASHSEED=0`, all six numerical thread bounds equal to one,
  and `CUDA_VISIBLE_DEVICES=-1`.
- Exact PID/token/SHA handshake, separate empty asynchronous-error ledgers,
  share-none outer lock, per-run inner lock, atomic no-overwrite artifacts,
  exact second replay, deep post-exit verification, and completion marker last.
- Candidate suffixes remain unopened. A click label may be read only by a
  later, separately locked Phase B if this run returns
  `PASS_COVERAGE_AND_OPEN_LABELS` and the complete Phase-A result is committed.

The NumPy Gram engine claims semantic and algebraic parity with the locked
sparse shared-fact formula, not byte-for-byte floating-point parity with the
aborted PowerShell implementation. Its exhaustive synthetic test compares
entity, news, user, score, tolerance, tie, manifest, and verifier behavior with
direct fact-space constructions. The confirmatory result is accepted only if
the independent same-engine replay has an identical cohort-manifest hash and
metric-payload hash and the verifier independently reconstructs the label-free
cohort and reranks every manifest row.

## Pre-run validation

The final isolated self-test completed with child PID `36028`, exit code zero,
zero-byte stderr, a zero-byte asynchronous-error ledger, no remaining lock,
and no confirmatory result artifact. Its completion marker is
`selftest_artifacts/st_67ac5348790148a5a621/selftest_completion.json`, SHA-256
`FA456A351F4292758B3F4324AA58EE0ADE849F46DDDB53B45DFB8CAB83995096`.

Two earlier isolated launcher attempts are implementation evidence only. Both
Python children passed, but one PowerShell failure path exceeded legacy
`MAX_PATH` and masked the initiating error; the next exposed Windows
PowerShell 5.1 returning a null `ExitCode` for redirected `Start-Process`.
Launch paths were shortened, original and cleanup exceptions are now
aggregated, bounded Windows sharing-error retries were added, and the native
process handle is materialized immediately per PowerShell issue `#5421`.
Neither attempt created a primary, replay, result, completion marker, or label
aggregate. No scientific parameter, cohort rule, metric, gate, or graph view
changed during these launcher-only corrections.
