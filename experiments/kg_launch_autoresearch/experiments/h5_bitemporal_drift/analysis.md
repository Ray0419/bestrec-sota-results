# H5 Bitemporal Drift Analysis

## Run 002: inconclusive due to API rate limiting

`run_002` completed in 162.4 seconds with exit code 0, an empty PowerShell
error stream, and an atomic result bundle. All 50 current entities were
returned, but Wikidata responded with HTTP 429 for 22 historical queries after
the locked retries. Only 28 historical snapshots resolved, so two mandatory
sanity checks failed and the registered verdict is `INCONCLUSIVE`.

The valid subset produced a 0.24362 news-frequency-weighted current-only edge
fraction and a 0.75 affected-selected-news rate. These exceed the structural
gates, but they are not admissible H5 evidence: missingness is ordered by the
request sequence, not random, and unresolved entities were excluded from the
weighted metrics. They are reported only to explain why no conclusion is
drawn.

The next attempt must query all 50 entities again and may not reuse the 28
successful snapshots. A transport-only correction may add proactive pacing
and honor server-directed cooldowns; it may not change the entity sample,
cutoff, fact representation, metric, or effect thresholds.
