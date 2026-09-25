# H9A synthetic self-test transport correction 001

Date: `2026-08-07`

Classification: launcher transport failure; not a scientific or completed
self-test result.

The first synthetic-only launch used runner
`F9FD57FBF558A0A992906CA3E9056636F35F34006B5DF3520F77D02BDD37C2FB`
and launcher
`654058AB665D7195440064452FC8D8B0DF51504923CFDC4C7CBE7A118A32B68C`.
The authenticated child PID `8468` emitted `H9A_SELFTEST_COMPLETE`; its start
record, acknowledgement, authorization, and token identities agree. Standard
error and the asynchronous-error ledger are both empty. The summary states
`real_input_files_opened=false` and `candidate_labels_opened=false`. The outer
lock was fail-retired, both child and launcher PIDs are dead, no fixed lock
remains, and no self-test completion marker or real result directory exists.

The launcher then rejected a zero/unavailable post-exit
`Process.PeakWorkingSet64`. The correction samples the exact authenticated
process handle before acknowledgement, while the child is necessarily alive,
and takes the maximum of subsequent 100 ms live samples and any valid post-exit
sample. Stopwatch scope, exact PID wait/termination, stdout/stderr, error-ledger,
locks, hash checks, and completion-last semantics are unchanged. Independent
static audit found no remaining P0/P1 issue.

Amended launcher SHA-256:
`798861EC6D81386D40C4C90F139FD85E848A978BE7C28EA18A2FECB42549304A`.

Preserved failed-attempt directory:
`selftest_artifacts/h9st_2b496365c0534dea8565`

Artifact hashes:

- `selftest_authorization.json`: `59676C02548BD4F50148005BC07D6010EA2DC85C4F3199588686218697C5B283`
- `selftest_process_start.json`: `A9119094193A5C63E7DB186B47A2E009D9B5E214B36874EDEFFB1BA2B7843070`
- `selftest_process_ack.json`: `7083BF9ACC9F885FC83804E629343ABDE642652A5B719D2A2E23326B3475AF85`
- `selftest_stdout.log`: `301A22F815895D8F61EA6F08C2F394C24A84407526E2B2B34D15F03E9DF670B6`
- `selftest_stderr.log`: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- `selftest_async_errors.jsonl`: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- `outer_fail_382d2c5a5d8848ecbac8.json`: `9978B26F3A7EDB73061C4AF426529EE050833D1239E644BCC896AB344E11905D`
