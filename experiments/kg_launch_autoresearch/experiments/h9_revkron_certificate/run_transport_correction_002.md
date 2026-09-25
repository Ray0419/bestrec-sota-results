# H9A label-blind run transport correction 002

Date: `2026-08-07`

Classification: runner telemetry failure before publication; not a scientific
pass, rejection, or completed primary result.

The failed launch used runner
`F9FD57FBF558A0A992906CA3E9056636F35F34006B5DF3520F77D02BDD37C2FB`
and launcher
`798861EC6D81386D40C4C90F139FD85E848A978BE7C28EA18A2FECB42549304A`.
The label-blind computation returned internally, then the first untyped Windows
`GetProcessMemoryInfo` call returned false before the stage could be published.
Stdout and the asynchronous-error ledger are empty; stderr contains only that
traceback. The temporary stage was removed, fixed primary/replay/completion
paths do not exist, both PIDs are dead, all fixed locks are absent, and all six
immutable inputs retain their locked hashes. No scores, gates, row manifest, or
candidate labels were published or exposed.

The correction replaces only Windows peak-memory telemetry with typed
`GetCurrentProcess` and `K32GetProcessMemoryInfo` calls, a typed `psapi`
fallback, preserved `GetLastError`, positive-peak validation, and a synthetic
self-test assertion that invokes the exact API. The scientific scorer,
certificate, thresholds, row serialization, and adjudication are unchanged.
Independent static audit found no remaining P0/P1 issue.

Amended runner SHA-256:
`F16034E938A2C228887B517831F10DD2E799312D53F4220F4DEBF507A4351D8E`.

Preserved failed-launch directory:
`results/h9_9cf09c436ef648e2b671`

Artifact hashes:

- `primary_authorization.json`: `1C96F205D634BEC2B3AAB8DD564B944FA455E250E2921157FF8242CE09DBC3D3`
- `primary_process_start.json`: `854457EAA1874018C695CAAD2F3FB63858CB531CDDDC05F0A9B823AD5377B8EB`
- `primary_process_ack.json`: `F53202F567F6B5E769D2DDE7C50796FAB892E53BE3A0F5CEDFD09B9829E1FF15`
- `primary_stdout.log`: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- `primary_stderr.log`: `74CCF577AEF481EC0809FD179CC4493CC64C67DD1F4DF2B6E6D3128E3FA8B024`
- `primary_async_errors.jsonl`: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- `inner_fail_primary_7298a7fdb1b240d4a014.json`: `A83491F2E64D1EA8D83BFDAC93E91B2C2B053C157679A29957A529E2C6CA5250`
- `outer_fail_3367704e7b2241c3b723.json`: `81DD8DE8EF0817DE98A2CF0438936312BC6FFF62EEC4D71927E6AE22783D65C3`
