# H1 Protocol: Launch-Time Graph Support Audit

Status: locked before execution  
Run: `run_001`  
Classification: confirmatory unless explicitly marked exploratory below  
Dataset: Amazon Reviews 2023, Digital Music  
Date locked: 2026-08-07

## Limitation under test

Strict-cold KG papers commonly hold out random items, low-frequency items, or item IDs while constructing side graphs from a completed catalog. The proposed limitation is that this supplies synthetic cold items with graph connectivity that a genuinely future-born, zero-interaction item did not have at the prediction cutoff.

## Hypothesis and prediction

H1: conventional random or low-frequency cold protocols overstate usable graph support.

Prediction: an equal-size bottom-frequency cohort evaluated on the completed item-attribute graph will have at least a 10 percentage-point higher exact typed-attribute link rate than the future-born cohort evaluated against the prefix-visible warm graph, **or** at least 20 percent of future-born items will be linkable only through items unavailable at the cutoff.

This first-domain gate decides whether an outcome-level KG experiment is warranted. A paper-level claim will later require the effect in at least two of three preregistered domains: Digital Music, Video Games, and Office Products.

## Inputs

- Metadata: `C:/Users/rayxc/Documents/R/data_raw_proper/digital_music/meta_Digital_Music.jsonl`
- Interactions: `C:/Users/rayxc/Documents/R/data_raw_proper/digital_music/Digital_Music.jsonl`
- Item key: `parent_asin`
- Interaction key: unique `(user_id, parent_asin)`
- Interaction time: millisecond Unix `timestamp`, converted to UTC
- Listing time: `details["Date First Available"]`

No review text, ratings, average rating, rating count, bought-together field, co-view/co-buy relation, or post-cutoff interaction is permitted in graph construction.

## Cohort construction

1. Merge duplicate metadata rows by item: union eligible attributes and keep the earliest parsable listing date.
2. Keep items with a parsable listing date and at least one deduplicated interaction.
3. Set cutoff `t` to the empirical 90th percentile of listing dates in that universe, using sorted index `ceiling(0.9*n)-1`.
4. Prefix-warm items satisfy listing date `<= t` and have at least one interaction at or before `t`.
5. Launch-cold items satisfy listing date `> t`, have zero interactions at or before `t`, and have at least one interaction after `t`.
6. Construct a bottom-frequency synthetic-cold cohort of exactly the same size, excluding launch-cold items, by ascending deduplicated interaction count with deterministic item-ID tie breaking.
7. Construct a deterministic random synthetic-cold cohort of the same size from the same eligible pool using seed `20260807`.

If the eligible pool is too small for an equal-size cohort, report the shortfall and invalidate the comparison.

## Launch-safe graph

Build a typed bipartite item-attribute graph from fields that could plausibly exist on the listing page:

- `store`
- `details.Manufacturer`
- `details.Label`
- `details.Brand`
- `categories`
- `features`

Values are Unicode-trimmed, whitespace-collapsed, and lowercased. Relation type is part of the attribute key. Constant `main_category` is excluded. No fuzzy matching, language-model enrichment, title tokenization, or inferred relation is allowed in the confirmatory graph.

The prefix graph contains attributes of prefix-warm items only. The completed graph contains eligible metadata items other than the evaluated cohort. Cold-item attributes themselves are observed at insertion time, but other future items are not visible in the prefix graph.

## Locked metrics

For a cold item, `linked=1` when at least one of its exact typed attributes is also attached to an allowed warm item.

Primary:

1. `total_support_gap_pp = 100 * (bottom_frequency_completed_link_rate - launch_prefix_link_rate)`
2. `future_graph_only_rate = launch_completed_link_rate - launch_prefix_link_rate`

Secondary confirmatory:

- random completed link rate and its gap from launch-prefix link rate;
- launch, bottom-frequency, and random empty-attribute rates;
- median and mean number of allowed warm neighbors, counted as distinct items sharing at least one attribute;
- relation-specific link rates for store, manufacturer, label, brand, category, and feature.

Exploratory only:

- alternative date quantiles;
- cleaned artist/store parsing;
- tokenized title or description attributes;
- degree-weighted support or multi-hop reachability.

## Decision rule

- **Advance H1 to the outcome POC** if `total_support_gap_pp >= 10` or `future_graph_only_rate >= 0.20`, with at least 500 launch-cold items and no failed sanity check.
- **Refute this version of H1 and pivot to H4** if both effects miss their gates with valid data.
- **Inconclusive** if there are fewer than 500 launch-cold items, listing-date coverage among interacted metadata items is below 80 percent, cohort construction fails, or a sanity check fails.

No post hoc relaxation of these thresholds is confirmatory.

## Sanity checks

- Report raw lines, parsed lines, parse failures, unique items, duplicate metadata rows, and duplicate interaction pairs.
- Verify every launch-cold item has listing time after the cutoff, zero deduplicated interactions at/before cutoff, and at least one after cutoff.
- Verify every prefix-warm support item has at least one interaction at/before cutoff.
- Verify evaluated cohorts are disjoint where required and have identical sizes.
- Spot-print five deterministic items from each cohort with dates, counts, attributes, and link flags.
- Treat any nonempty PowerShell error stream or premature termination as invalid.

## Runtime and Windows safety

This is a read-only structural POC. It will use a single PowerShell process and streaming file reads; Python, PyTorch, BLAS, multiprocessing, and worker threads are not used. Results are written only after all sanity checks complete. A later outcome experiment must use the repository's hardened Windows launcher contract.

