# H9A RevKron-Cert implementation lock

Status: frozen before synthetic self-test or real H9A execution

Frozen-Date: `2026-08-07`

Runner-SHA256: `F9FD57FBF558A0A992906CA3E9056636F35F34006B5DF3520F77D02BDD37C2FB`

Launcher-SHA256: `654058AB665D7195440064452FC8D8B0DF51504923CFDC4C7CBE7A118A32B68C`

Protocol-SHA256: `B1D52DE0A454F8B29A1DB4A6E0627EFC6A60E96010730C7D9427276D6D4C11C9`

The runner implements the locked label-blind H9A mechanism and certificate
coverage test. The launcher binds the exact implementation, protocol, runtime,
input hashes, process identities, locks, stdout/stderr, asynchronous-error
ledgers, primary replay, deep verification, runtime gates, and final completion
marker. The implementation was statically audited before this lock was written.

No Python process, synthetic self-test, or real H9A experiment had been executed
from these frozen implementation bytes when this lock was created.
