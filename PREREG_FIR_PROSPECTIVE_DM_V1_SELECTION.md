# Frozen selection and feasibility protocol: prospective Digital Music FIR confirmation

Protocol identifier: `PREREG_FIR_PROSPECTIVE_DM_V1_SELECTION`

Freeze stage: **A (selection/acquisition/feasibility only)**. At this freeze,
the repository has no Digital Music raw files, processed split, embedding
cache, training run, checkpoint, validation trajectory, final-test artifact,
or model outcome. No Digital Music endpoint may be computed until a later
stage-B execution preregistration, executable trainer, sealed evaluator, and
mechanical adjudicator are committed and pushed.

This protocol is intended to create a genuinely prospective category-level
confirmation attempt for the canonical FIR module. It is not independent in
the institutional sense: the same investigators, code lineage, dataset family,
and repository are used. If completed without a custody violation, it may be
described only as a preregistered untouched-category confirmation.

## Deterministic category selection

The candidate universe is the 33 named Amazon Reviews 2023 categories in the
McAuley Lab public category table. A category is eligible only if:

1. its public raw table reports at least 100,000 ratings and at least 10,000
   items; and
2. this repository contains no retained split, model result, cache, feasibility
   output, or earlier category-specific outcome for it, and the category has
   not previously been inspected for this project.

Among eligible categories, choose the one with the fewest reported raw
ratings; break an exact tie lexicographically by category name. There is no
discretionary substitution.

The rule selects `Digital_Music`: the public table reports 130.4K ratings,
101.0K users, and 70.5K items. `Subscription_Boxes` and
`Magazine_Subscriptions` fail the rating threshold; `Gift_Cards` fails the
item threshold. Categories already used or inspected in this project,
including `All_Beauty`, are ineligible regardless of their public size.

Source table:
`https://amazon-reviews-2023.github.io/main.html#grouped-by-category`.

## Frozen upstream objects and acquisition

Upstream repository: `McAuley-Lab/Amazon-Reviews-2023`, Git revision
`2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e`.

The only permitted raw objects are:

| role | repository path | bytes | SHA-256 |
|---|---|---:|---|
| reviews | `raw/review_categories/Digital_Music.jsonl` | 78,823,304 | `9ac137137e55e34fce290670fdf44acee5afa2ffae541f4f3b366a835930a7c3` |
| metadata | `raw/meta_categories/meta_Digital_Music.jsonl` | 67,097,002 | `7f5387e99b70631d919c87005269c555e8886ae9a60c4c59a9b6ed7881acbbec` |

`_bestrec_run/acquire_digital_music_prospective.py` must download the revision-
pinned objects, verify byte count and SHA-256, refuse to replace a mismatching
existing file, and write a hash manifest. Raw objects remain ignored and are
not redistributed.

## Frozen preprocessing

Run `_bestrec_run/preprocess_5core_standard.py Digital_Music` without code or
argument changes after this freeze:

1. read `user_id`, `parent_asin`, `rating`, and timestamp;
2. order each user's interactions chronologically;
3. deduplicate each `(user,item)` pair, retaining its earliest interaction;
4. recursively filter until every retained user and item has at least five
   interactions; and
5. perform per-user chronological leave-last-out: last item to TEST,
   penultimate item to validation, and all earlier items to training.

The raw rating threshold is a selection rule, not evidence that the processed
split will be usable.

## Frozen feasibility gate

`_bestrec_run/verify_digital_music_feasibility.py` may inspect only raw/split
hashes, row counts, user/item counts, key uniqueness, and split invariants. It
must not import a model, encode text, train, score recommendations, rank test
items, or calculate any model endpoint.

The category is feasible only if all of the following hold:

- the processed 5-core contains at least 1,000 users, 1,000 items, and 10,000
  interactions;
- each retained user occurs exactly once in validation and once in TEST and
  has at least three training interactions;
- the train, validation, and TEST user sets are identical;
- `(user,item)` pairs do not overlap across splits; and
- the three split row counts sum exactly to the rating-only row count.

If any gate fails, the verdict is `DM-V1-FEASIBILITY-VOID`. No fallback
category, relaxed threshold, alternative core, or repaired split is permitted
under V1. A new attempt would require a new identifier and preregistration.

If all gates pass, the verdict is `DM-V1-FEASIBLE`. This licenses only a new
stage-B preregistration. It is not a scientific result and it does not license
training by itself.

## Information boundary and custody

Before stage B is frozen, permitted observations are limited to acquisition
success, file digests/sizes, preprocessing logs, and the feasibility fields
listed above. Digital Music model validation or TEST outcomes are forbidden.

The stage-A files must be committed and pushed before acquisition. The
generated acquisition and feasibility manifests, exact split digests, frozen
embedding recipe/model revision, exact seeds/configuration, trainer, driver,
sealed evaluator, and adjudicator must then be committed and pushed in stage B
before the first model process starts.
