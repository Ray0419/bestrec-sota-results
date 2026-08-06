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

## Run 003: structural gate passed

`run_003` queried a fresh snapshot for all 50 entities under the committed
transport-only pacing correction. It completed in 329.6 seconds with exit code
0, empty stderr, all 50 current entities present, all 50 historical revisions
resolved, no API or parse errors, and every registered sanity check passing.

- News-frequency-weighted current-only edge fraction: `0.2494205852`
  (gate: at least `0.15`).
- Affected selected-news rate: `1.0` (`12,060/12,060`; gate: at least `0.50`).
- Entities with at least one current-only fact: `50/50`.
- Mean and median current-only facts per entity: `32.26` and `27`.
- News-frequency-weighted historical-only edge fraction: `0.0491232254`.

The registered verdict is therefore `ADVANCE_H5_TO_OUTCOME_POC`. This is
evidence of material external-KG transaction-time drift, not yet evidence that
recommendation quality or rankings change.

An exploratory, label-blind diagnostic retained only properties present in
MIND's supplied `relation_embedding.vec` vocabulary (1,091 relation IDs). The
weighted current-only fraction remained `0.2371843326`; all 50 entities still
had a current-only fact. This reduces, but does not eliminate, the concern that
the structural result is driven solely by relations outside MIND's native KG
representation. The H6 protocol must still predeclare a click-label-free
relation policy and demonstrate that snapshot choice changes candidate scores
before any outcome analysis.
