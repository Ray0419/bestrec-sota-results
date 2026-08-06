# H5 Protocol: Bitemporal Wikidata Drift in MIND

Status: locked before Wikidata snapshot comparison

Run: `run_001`

Classification: confirmatory structural proof of concept

Date locked: 2026-08-07

## Limitation under test

A knowledge-aware recommender evaluated at time `t` must not consume an
external-KG fact merely because the fact is present in today's snapshot. The
fact must have been observable to the system by `t`. Static entity IDs or a
valid-time qualifier do not establish that transaction-time condition.

H5 asks whether this is a material rather than hypothetical distinction on a
real recommendation benchmark: how many entity-to-entity Wikidata edges now
attached to MIND entities were absent from Wikidata at the latest MIND-small
development impression?

This does not assert that the embeddings supplied with MIND are leaked. It
tests the risk faced when a present Wikidata snapshot is joined to historical
MIND interactions.

## Inputs

- Dataset: MIND-small development archive, public `gamusa/MIND` mirror.
- Archive SHA-256:
  `B315CDE1C9B9D45008B5A7C4B2E1F87647659F09F74892AE3899C0005D5D6155`.
- News file: `data/MINDsmall_dev/MINDsmall_dev/news.tsv`.
- Behaviors file: `data/MINDsmall_dev/MINDsmall_dev/behaviors.tsv`.
- Historical source: Wikidata MediaWiki revision API.
- Current source: Wikidata `wbgetentities` API.

The cutoff is the maximum parsable UTC impression time in `behaviors.tsv`.
The runner must verify it equals `2019-11-15T23:58:03Z`.

## Deterministic entity sample

1. Parse title and abstract entity annotations from all news rows.
2. Retain annotations whose `WikidataId` matches `^Q[1-9][0-9]*$` and whose
   numeric confidence is at least 0.90.
3. Count each retained QID at most once per news row.
4. Sort QIDs by descending news-row count, with ordinal QID tie breaking.
5. Select the first 50 QIDs.

The 50-QID sample is fixed from MIND alone before any Wikidata result is read.

## Point-in-time snapshots

For each selected QID:

- Historical snapshot: the latest entity-page revision with timestamp at or
  before the MIND cutoff, using `rvstart=cutoff`, `rvdir=older`, and
  `rvlimit=1`.
- Current snapshot: the entity returned by one batched `wbgetentities` request
  during the run. Record `lastrevid` and `modified` for every entity.
- If the current entity exists but has no revision at/before the cutoff, treat
  the historical entity as absent and its fact set as empty; report this
  separately rather than treating it as an API failure.

Requests are sequential, identify the research user agent, and retry at most
three times with waits of one and two seconds. No request or parsed response
from an earlier exploratory call may be used as a confirmatory cache.

## Locked fact representation

A fact is a direct entity-valued Wikidata claim with:

- property ID matching `^P[1-9][0-9]*$`;
- claim rank other than `deprecated`;
- `mainsnak.snaktype == "value"`;
- `mainsnak.datavalue.type == "wikibase-entityid"`; and
- positive numeric target entity ID.

Its signature is `property_id|Qtarget`. Duplicate statements collapse to one
signature. Qualifiers, references, labels, literal-valued claims, external
identifiers, and inferred transitive edges are excluded.

For historical set `H_i` and current set `C_i`, define current-only facts as
`C_i \ H_i` and historical-only facts as `H_i \ C_i`.

## Locked metrics

Primary:

1. News-frequency-weighted current-only edge fraction

   `sum_i frequency_i * |C_i \ H_i| / sum_i frequency_i * |C_i|`.

2. Affected selected-news rate: among news rows containing at least one of the
   50 selected QIDs, the fraction containing a selected QID with at least one
   current-only fact.

Secondary:

- fraction of selected entities with at least one current-only fact;
- median and mean current-only facts per selected entity;
- weighted historical-only edge fraction;
- per-entity Jaccard similarity between historical and current fact sets;
- number of selected entities absent at cutoff;
- current and historical revision IDs and timestamps;
- deterministic per-entity fact signatures in a machine-readable ledger.

## Decision rule

- **Advance to an outcome-level snapshot-ranking POC** only if all 50 current
  entities are returned, every historical query resolves as a revision or a
  substantive pre-cutoff absence, all parsing/sanity checks pass, the weighted
  current-only edge fraction is at least 0.15, and the affected selected-news
  rate is at least 0.50.
- **Refute H5 as the main direction** if the run is valid but either effect
  threshold is missed.
- **Inconclusive** on any unresolved API failure, sample/cohort mismatch,
  nonempty PowerShell error stream, premature termination, or cutoff mismatch.

No alternate confidence threshold, sample size, fact type, or cutoff is
confirmatory after this lock.

## Runtime and output safety

The runner is a single PowerShell 5.1 process. It uses no Python, BLAS,
multiprocessing, or worker threads. It writes the result bundle only after all
requests, fact extraction, metrics, and sanity checks complete, and it refuses
to overwrite an existing run directory. Standard output and error are captured
separately by the hidden launcher.
