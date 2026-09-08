# H1 Corrected Adjudication Note

Status: locked before corrected execution

Run: `run_002`

Date locked: 2026-08-07

## Why a correction is required

`run_001` completed with an empty PowerShell error stream and atomically
published all requested diagnostics. It was nevertheless labeled
`INCONCLUSIVE` because the implementation incorrectly required zero JSON parse
failures. The locked protocol required parse failures to be reported; it did
not define them as an invalidity condition. Its actual invalidity conditions
were a nonempty PowerShell error stream, premature termination, failed cohort
semantics, inadequate listing-date coverage, fewer than 500 launch-cold items,
or an insufficient comparison pool.

PowerShell 5.1 rejected eight of 70,537 metadata rows (0.0113 percent). Six
contain case-insensitive duplicate `details` keys (`Number Of Discs` and
`Number of discs`), and two trigger the same legacy object-key conversion
limitation. These are parser compatibility failures, not process errors. The
interaction file had zero parse failures. Listing-date coverage remained
96.36 percent.

## Locked correction

For `run_002`, metadata and interaction parse-failure counts remain mandatory
diagnostics but are not themselves sanity gates. Every cohort, graph, metric,
threshold, randomization rule, and other validity gate is unchanged. The
runner remains deterministic and continues to skip any row that PowerShell 5.1
cannot convert.

The `run_001` effect estimates were already visible before this correction.
Therefore `run_002` is a transparent deterministic correction, not an
independent replication. No effect threshold or cohort definition is being
relaxed.
