# H1 Pre-Run Implementation Notes

Status: locked before execution

Run: `run_001`

Date locked: 2026-08-07

The confirmatory protocol uses day-resolution listing dates and deduplicated
`(user_id, parent_asin)` interactions. The following deterministic choices
resolve details that were not explicit in the protocol and are fixed before
reading any result:

1. When the same user-item pair occurs more than once, its interaction time is
   the earliest parsable timestamp. Its deduplicated interaction count remains
   one.
2. A listing-date cutoff is interpreted through 23:59:59.9999999 UTC on that
   calendar day. Thus an interaction on the cutoff date counts as observable
   at or before the cutoff.
3. Interactions with an unparseable timestamp are counted in input diagnostics
   but cannot establish prefix visibility or post-cutoff eligibility. Cohort
   sanity checks must still pass from parsable timestamps.
4. Metadata values that are null, empty after normalization, or not scalar
   strings in the locked fields contribute no attribute.
5. The deterministic random cohort is defined by sorting eligible item IDs by
   `SHA-256("20260807" + U+001F + item_id)` and taking the first cohort-sized
   prefix. Bottom-frequency and random cohorts are sampled independently from
   the same non-launch pool and may overlap one another.
6. Relation-specific link-rate denominators include every item in the cohort,
   including items with no attribute of that relation.

These rules are implementation disambiguations, not exploratory variants. Any
other departure from `protocol.md` invalidates `run_001`.
