# Software FIR V3 replay erratum

Date recorded: 2026-07-28

Protocol: `PREREG_FIR_PROSPECTIVE_SW_V3`

This erratum narrows replay and evidence-class claims without changing any endpoint,
statistic, decision rule, or the recorded mechanical verdict
`SW-V3-PRACTICAL-POS`.

## Raw-byte reference mismatch

The frozen V3 common module registered the raw SHA-256
`a230d17cd4e1683ac0e07e64702587950baf89374083521850c96daeede1ab72` for
`_bestrec_run/results_MI_V2_ls02_filter16_seed20260608.json`. That digest is the
CRLF worktree representation present during execution. The frozen Git tag stores the
same JSON content with LF line endings; a normal checkout therefore has SHA-256
`37c78ef344dcbe4741d7ea0d487712ff8eb8e10096754a7467e29844989302f8`.

Consequently, a direct fresh checkout of `fir-prospective-sw-v3-freeze` fails the
raw-byte `assert_inputs()` check until the historically executed CRLF representation
is restored. This is a frozen-run portability and preregistration-gate defect. The
reference JSON was not read for runtime configuration or model selection: V3 used the
literal `BASE_ARGS` tuple in the frozen common module. The mismatch therefore does not
alter the 16 training records, 16 sealed endpoint records, paired statistics, or verdict,
but it prevents claiming that the frozen tag alone is byte-for-byte executable on a
fresh checkout.

The descendant repository preserves the CRLF representation with an explicit
`.gitattributes` exception. Future preregistrations must test all raw-byte assertions in
a fresh checkout before launch and must bind canonical JSON content or Git-blob bytes,
not platform-dependent worktree line endings.

## Evidence-class qualification

Tracked evidence also cannot establish whether any investigator observed validation
NDCG printed by the aborted Software V2 trainer before the V3 design, seeds, and
+0.000500 threshold were frozen. Unless the authors supply a signed, dated visibility
and custody statement, the paper therefore classifies V3 as outcome-known/exploratory
same-team robustness. Its protocol-designated adjudicator was invoked by the driver,
but local logs cannot prove that it was the first human or tool to inspect endpoint
content. The local seals are exclusive-created and hash-linked; they are not immutable
external escrow.
