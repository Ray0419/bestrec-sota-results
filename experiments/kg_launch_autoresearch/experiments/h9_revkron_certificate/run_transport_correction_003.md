# H9A post-verification transport correction 003

Date: `2026-08-07`

Classification: completion-publication transport failure after successful
primary, exact-replay, and deep-verifier execution; no scientific computation
is rerun by this correction.

The frozen launch `h9_3105834790a84ed2970a` completed its primary runner,
exact replay, and separate deep verifier. Both scientific payloads have
SHA-256
`5D06E54AEDADD5ED2260D005C28A60536E1D06AC7A7CF5C5A63E8E45A2D3C1DC`;
both 91,622,274-byte, 64,443-row manifests have SHA-256
`3728557242572C5ADF76A969B0B2B531B080BF1C67BEBD20CBC0713F5B66A67C`;
and the deep-verification artifact has SHA-256
`6BBFBB8EDDED827382344DA5EEB8C9009AEF7C1925D3B01A3B9B50D6B1B9E83E`.
All three stderr files and asynchronous-error ledgers are empty, all four
recorded process IDs are dead, and both fixed locks are absent.

The launcher failed only while exact-comparing runtime metadata after the deep
verifier had returned. The replay elapsed-time JSON lexeme is
`238.68075969999998`. Invariant binary64 parsing gives bits
`406DD5C8C890FDE9`, while Windows PowerShell `ConvertFrom-Json` gives
`406DD5C8C890FDEA`, a one-ULP transport difference. The primary lexeme
`239.2070628` maps to `406DE6A0422A46FB` through both paths. This defect does
not change either runtime gate: primary and replay are below 300 seconds and
below 2 GiB under both representations.

The prospective recovery program is therefore limited to validating and
attesting the sole already-computed chain. It pins every original artifact,
input, implementation hash, launch identity, process handshake, raw runtime
lexeme, and original-launch Git blob; independently recomputes all eight
scientific gates from persisted integer counts; verifies primary/replay and
deep-verifier agreement; and refuses live processes, locks, reparse points,
unexpected inventory, or overwrite. Audit mode performs zero writes. Recovery
mode requires the exact token frozen in `recovery_lock.md`, writes append-only
attestation and lock-release evidence, and writes a distinctly named recovered
completion marker last. It never invokes the H9 Python runner and never opens
candidate labels.

Recovery script SHA-256:
`FFDED65DCFCE76C62228A2837FF804F94ADB1F96BC02EFFA42352B15AA95137C`.

The recovered decision remains `KILL_H9_KRON_DIRECTION`; recovery cannot turn
the failed certificate-utility gates into a pass.
