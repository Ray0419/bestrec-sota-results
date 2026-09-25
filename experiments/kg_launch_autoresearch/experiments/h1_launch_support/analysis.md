# H1 Launch-Support Analysis

## Outcome

H1 is refuted under its preregistered Digital Music test. The valid corrected
run is `run_002`; `run_001` is retained as an immutable implementation-
adjudication artifact.

| Quantity | Locked gate | Observed |
|---|---:|---:|
| Launch-cold items | at least 500 | 6,430 |
| Listing-date coverage | at least 80% | 96.36% |
| Total support gap | at least +10 pp | -2.675 pp |
| Future-graph-only rate | at least 0.20 | 0.06081 |
| PowerShell stderr | empty | empty |
| Sanity checks | all pass | all pass |

The primary gap has the opposite sign: future-born items linked to the legal
prefix graph at 63.50 percent, while bottom-frequency synthetic items linked to
the completed graph at 60.82 percent. The deterministic random cohort was
similar at 60.26 percent.

## Relation pattern

For launch items against the prefix graph, store links covered 43.70 percent,
manufacturer 37.00 percent, and label 36.91 percent. Category and feature links
were zero in this domain because those fields are nearly universally empty.
The completed graph raised launch coverage primarily through store,
manufacturer, and label links, but the incremental total was only 6.08
percentage points.

Mean distinct-neighbor counts are highly skewed (1,018.8 for launch-prefix,
versus median 3), so mean graph degree is not an adequate proxy for usable cold
support. Later tests must report item-macro results and support strata.

## Validity correction

PowerShell 5.1 cannot convert eight otherwise valid metadata rows because their
objects contain duplicate keys under case-insensitive comparison. `run_001`
mistakenly made zero parser failures a sanity requirement, although the locked
protocol only required the count to be reported. `run_002` changed only that
extra validity condition. It exactly reproduced all effect estimates and had
an empty process error stream. Because `run_001` estimates were already seen,
`run_002` is a corrected deterministic adjudication, not an independent
replication.

## Decision

Do not run H2 or tune the graph-support threshold. Activate H4 as a new inner
loop. Its target population is the 36.50 percent of real launch items without
an exact prefix-graph link, but its patch must beat strong semantic/content
baselines and cannot be a generic gate, content fusion block, or point-in-time
replay wrapper.
