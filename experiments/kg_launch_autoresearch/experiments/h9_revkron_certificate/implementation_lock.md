# H9A RevKron-Cert implementation lock

Status: frozen after launcher-only transport amendment 001 and before any
completed synthetic self-test or real H9A execution

Frozen-Date: `2026-08-07`

Runner-SHA256: `F9FD57FBF558A0A992906CA3E9056636F35F34006B5DF3520F77D02BDD37C2FB`

Launcher-SHA256: `798861EC6D81386D40C4C90F139FD85E848A978BE7C28EA18A2FECB42549304A`

Protocol-SHA256: `B1D52DE0A454F8B29A1DB4A6E0627EFC6A60E96010730C7D9427276D6D4C11C9`

The runner implements the locked label-blind H9A mechanism and certificate
coverage test. The launcher binds the exact implementation, protocol, runtime,
input hashes, process identities, locks, stdout/stderr, asynchronous-error
ledgers, primary replay, deep verification, runtime gates, and final completion
marker. The implementation was statically audited before this lock was written.

The first synthetic-only attempt under launcher
`654058AB665D7195440064452FC8D8B0DF51504923CFDC4C7CBE7A118A32B68C`
produced a successful Python self-test summary but no completion marker because
Windows returned no usable post-exit `PeakWorkingSet64`. Amendment 001 changes
only launcher peak-memory observation: it samples the authenticated exact child
while the child is blocked at the PID-ack barrier and continues sampling the
same process handle until exact exit. The runner and protocol are unchanged.
The failed attempt is hash-recorded in `selftest_transport_correction_001.md`.

No real H9A input, candidate label, primary run, replay, or deep verification
had been opened or executed when this amended lock was created.
