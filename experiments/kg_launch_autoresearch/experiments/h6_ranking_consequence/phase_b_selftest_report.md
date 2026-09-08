# H6 Phase-B synthetic self-test report

Date: 2026-08-07 (Australia/Sydney)

Status: `PASS`

The frozen Phase-B launcher was executed only in its default synthetic
`SelfTest` mode. The self-test did not open MIND, H5, Phase-A, outcome-result,
or candidate-label inputs.

## Frozen implementation

- Runner SHA-256: `34222A71AE69C699F8CC9F72A00B25C0DA17941AEEC452EC3B229D986824958D`
- Launcher SHA-256: `3D982668C2563B1062191C713DC313840F10E09F8102DE27E2B1ABDD1DE5CEA3`
- Implementation-lock SHA-256: `A67FC07B7C16B2EDA6AAD01BCF243133BBD29D3F6980324734C148A0D9BEB19F`
- Locked protocol SHA-256: `53EAE6D5D19982DD5E6926F563A6D327A5A1AF47DFC5CF58DA4D54D1D61DB0A4`

## Execution result

- Launcher status: `H6_PHASE_B_SELFTEST_COMPLETE`
- Launcher PID: `26860`
- Hidden child PID: `36824`
- Child exit code: `0`
- Completion-marker SHA-256: `DF2017FDFAE0F0EE54A0485029D9905E9A1D681D29AE7F65C66C034B736EFA1B`
- Child stderr bytes: `0`
- Asynchronous-error-ledger bytes: `0`
- Candidate labels opened: `false`
- Real inputs opened: `false`
- Stale outer lock retired: `false`
- Outer, confirmatory outer, and inner locks present after completion: `false`
- Completion marker written last: `true`

The self-test covered sparse pattern-Gram scoring against a direct fact-space
construction, frozen tolerance/hash ranking, the distinction between grouped
AUC and deterministic micro pair accuracy, deterministic shared PCG64
user-cluster bootstrap resampling, and deterministic relation-stratified
SHA-256 sampling without replacement.

The first shell attempt was rejected by the machine-wide PowerShell execution
policy before the launcher loaded. The valid run used a process-scoped
`-ExecutionPolicy Bypass`; this affected script loading only and did not alter
the launcher's environment, provenance, PID, locking, logging, or no-label
guards.
