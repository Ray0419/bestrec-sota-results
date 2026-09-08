# H5 Transport Correction for Run 003

Status: locked before execution

Run: `run_003`

Date locked: 2026-08-07

`run_002` was scientifically inconclusive because 22 of 50 historical
revision requests exhausted the original one- and two-second retries with HTTP
429. The missing suffix is not treated as random, and its preliminary metrics
are not reused.

`run_003` makes transport-only changes:

1. query all 50 current and historical snapshots again from the APIs;
2. wait four seconds proactively between historical entity requests;
3. retain the maximum of three request attempts;
4. retain one- and two-second waits for non-rate-limit failures;
5. for HTTP 429 only, honor a numeric `Retry-After` header capped at 60
   seconds, or wait 60 seconds if the header is absent or unparseable; and
6. record proactive and retry wait time in the result ledger.

No cached API response is used. Entity selection, cutoff, claim filtering,
fact signatures, metrics, sanity conditions, and effect thresholds are
unchanged.
