# H5 Aborted Run 001

Status: aborted before result publication

Date: 2026-08-07

The committed first implementation (`eedeb563`) was launched with separate
stdout and stderr capture. During execution, an independent static audit found
three protocol-critical issues:

1. a no-revision response could be classified as substantive historical
   absence without first validating the current entity and query page;
2. historical revision IDs and timestamps were recorded but not validated,
   including the required timestamp-at-or-before-cutoff condition; and
3. entity-valued facts were not explicitly restricted to Wikidata item/QID
   targets.

The launcher was terminated immediately and the exact child PowerShell process
was stopped. No `run_001/` result directory, fact ledger, metric, completion
marker, standard output, or standard error was produced. The two zero-byte log
files are retained. No API response cache exists or will be reused, and no
current-versus-historical outcome was inspected.

`run_002` fixes those conditions, adds exact fact-set partition and selected-
frequency cross-checks, validates current revision metadata, expands the
network-free self-test, and leaves the locked entity sample, cutoff, facts,
metrics, and effect thresholds unchanged. It is the first admissible H5 result
attempt.
