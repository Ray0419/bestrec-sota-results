# Frozen preparation protocol: prospective Software FIR confirmation V2

Protocol identifier: `PREREG_FIR_PROSPECTIVE_SW_V2_PREPARATION`

Freeze stage: **A (selection, acquisition, split, and deterministic text-cache
preparation only)**. At this freeze, no Software raw/processed data, cache,
training run, checkpoint, validation trajectory, TEST artifact, or model
endpoint exists in the project. Recommender training and evaluation remain
forbidden until a stage-B execution preregistration, trainer, driver, sealed
evaluator, and adjudicator are committed and pushed with exact prepared-input
hashes.

Digital Music V1 ended `DM-V1-FEASIBILITY-VOID` under its frozen gate. V2 is a
new protocol, not a fallback within V1.

## Deterministic untouched-category selection

The candidate universe is the 28 nonempty categories in the McAuley Lab
Amazon Reviews 2023 official pre-split 5-core table. Public user/item/rating
counts are structural feasibility information, not model outcomes.

A category is eligible only if:

1. the official 5-core table reports at least 50,000 users, 10,000 items, and
   400,000 interactions;
2. this project has no retained split, cache, feasibility output, model result,
   or prior category-specific inspection for it; and
3. it is not Digital Music V1.

Among eligible categories, minimize the public product `#users × #items`, the
dominant size term in full-catalog evaluation; break an exact tie
lexicographically. The rule selects `Software`: 146.4K users, 17.6K items,
and 1.3M interactions, or approximately 2.58 billion user-item pairs. The
already-used Video Games, Industrial and Scientific, Musical Instruments,
CDs and Vinyl, Office Products, and Beauty and Personal Care categories are
ineligible. The smaller All Beauty, Gift Cards, and Magazine Subscriptions
fail the scale floors. Baby Products is the next-lowest eligible untouched
burden at approximately 5.43 billion pairs.

Source table:
`https://amazon-reviews-2023.github.io/data_processing/5core.html#statistics`.

## Frozen upstream inputs

1. Official deduplicated pre-split 5-core ratings:
   `https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/benchmark/5core/rating_only/Software.csv.gz`
   (observed before freeze: `Content-Length: 19079096`,
   `Last-Modified: Thu, 16 Jan 2025 21:47:51 GMT`,
   `ETag: "1231fb8-62bd9beebcd77"`). The acquisition manifest records the
   downloaded SHA-256; the script also requires these frozen response fields.
2. Item metadata from `McAuley-Lab/Amazon-Reviews-2023` revision
   `2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e`, path
   `raw/meta_categories/meta_Software.jsonl`: 256,220,771 bytes, SHA-256
   `7c52cce1bf3bff33f965fe117e3e8fac18a1839f88b215efa50b31a8230a5f58`.

`_bestrec_run/acquire_software_prospective.py` must refuse replacement of any
mismatching existing object and write a hash manifest. Upstream data remain
ignored and are not redistributed.

## Frozen split preparation and feasibility

`_bestrec_run/prepare_software_official_5core.py` reads the official gzip CSV,
requires exactly `user_id,parent_asin,rating,timestamp`, rejects duplicate
`(user,item)` pairs, retains all supplied 5-core rows, orders each user by
integer timestamp with stable source-row tie breaking, and writes:

- the decompressed rating-only CSV;
- first `N-2` interactions to training;
- interaction `N-1` to validation; and
- interaction `N` to TEST.

Users are emitted in lexicographic ID order. No additional filtering,
subsampling, repair, or outcome-dependent choice is permitted.

`_bestrec_run/verify_software_feasibility.py` may inspect only file hashes,
counts, user/item keys, timestamps, uniqueness, and split invariants. V2 is
feasible only if the processed data have at least 50,000 users, 10,000 items,
and 400,000 interactions; every user has at least three training interactions
and exactly one validation and TEST interaction; user sets are identical;
split pairs are disjoint; and their union equals rating-only.

Any failure yields `SW-V2-FEASIBILITY-VOID`. No fallback category, repaired
file, threshold relaxation, or alternative split is permitted under V2.

## Frozen deterministic title cache

Only after `SW-V2-FEASIBLE`, `_bestrec_run/encode_software_titles_frozen.py`
may encode item titles. It uses:

- sorted union of split `parent_asin` values;
- the first metadata record for each retained `parent_asin`;
- stripped `title`, joining a list with one ASCII space, or the empty string
  when absent;
- `sentence-transformers/all-MiniLM-L6-v2` at exact model revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`;
- `batch_size=256`, no embedding normalization, float32 output; and
- no stochastic augmentation or text-dependent filtering.

The encoder refuses overwrite and records cache/item-map hashes, dimensions,
metadata coverage, package versions, model revision, and prepared-split
hashes. It may not train or import a recommender, read a validation/test model
outcome, or rank any item.

## Custody boundary

Permitted stage-A observations are limited to acquisition headers/digests,
preparation logs, structural counts/invariants, title coverage, cache shape,
package versions, and artifact hashes. These files must be committed and
pushed before acquisition. If preparation passes, its manifests and the exact
execution protocol/code must be committed and pushed in stage B before the
first recommender process starts.

If all preparation gates pass, the non-scientific verdict is
`SW-V2-PREPARED`; it licenses only the stage-B freeze. It is not evidence for
or against FIR and must not be reported as a model result.
