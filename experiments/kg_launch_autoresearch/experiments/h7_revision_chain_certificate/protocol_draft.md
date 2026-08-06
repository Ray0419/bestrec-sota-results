# H7A Prospective Protocol: Revision-Chain-Derived Interval Certificate

Status: **DRAFT; NOT LOCKED; NOT EXECUTABLE**

Classification: label-blind structural feasibility proof of concept

Draft date: 2026-08-07

## Research question and scope

For a recommender whose external knowledge graph may be stale at serving time,
can actual page revision histories define a useful conservative fault-model
superset and support an exact, low-latency Top-10 invariance certificate for an
additive KG residual?

This experiment tests only structural support, certificate tightness, exactness,
and runtime. It must not parse candidate click suffixes, compute recommendation
outcomes, or select any design choice using labels. A positive result is a gate
to a separately locked outcome experiment; it is not evidence of improved
recommendation quality by itself.

H7A is an exact **revision-chain-derived interval certificate** under a bounded
per-page FIFO staleness model. Its Cartesian product of page states is a
conservative fault-model superset; it is not evidence that the corresponding
asynchronous combinations occurred in Wikidata or in any measured serving
pipeline. H7A is not a provenance-poset or min-cut experiment.

Exact replay dominates this module whenever the exact page revision used for
each recommendation is observable. The certificate is relevant only when page
versions are unresolved but bounded by the stated FIFO fault model. An H7B
dependency experiment would require measured stream partitions, consumer
offsets, or explicit computational lineage from a real materialization system,
and a separately locked protocol.

The mathematical closure/min-cut result is classical. This protocol neither
implements a general min-cut solver nor claims novelty for minimum closure,
partial-order Top-K, temporal recommendation, KG provenance, generic
certification, uncertainty routing, or additive residuals in isolation. The
candidate contribution is only the eventual package of real revision-derived
uncertainty, an exact downstream ranking certificate, and
certificate-controlled KG fusion.

## Fixed existing inputs

- H5 fact ledger:
  `experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/facts.jsonl`,
  SHA-256
  `13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D`.
- H5 entity table:
  `experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/entities.csv`,
  SHA-256
  `45B83B0AFCB6C1348080984B1373CE50912219DFE247F48E97F7FB09009595ED`.
- H6 committed label-free cohort manifest from `coverage_run_002`, SHA-256
  `522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5`.
- MIND-small development `news.tsv`, SHA-256
  `E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822`.
- MIND relation vocabulary, used only as the frozen allowed-property set,
  SHA-256
  `D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A`.
- Transaction-time upper cutoff `tau = 2019-11-15T23:58:03Z`.
- The H5 top-50 QID sample, annotation-confidence threshold `0.90`, final-50
  history rule, and H6 deterministic tie rule remain unchanged.

The H6 manifest is the only allowed impression/candidate source. The H7A
runner must not open `behaviors.tsv`; this prevents access to candidate
suffixes. It may join manifest news IDs to the immutable `news.tsv` only to
recover the already frozen title and abstract entity annotations.

## Prospective real revision-chain acquisition

No acquisition occurs until this draft is finalized, hashed, and changed to a
locked protocol.

### Primary and sensitivity windows

- Primary maximum-ingestion-lag window: 30 days, beginning
  `2019-10-16T23:58:03Z` and ending at `tau`.
- Predeclared sensitivity window: seven days, beginning
  `2019-11-08T23:58:03Z` and ending at `tau`.
- A longer window may not rescue a failed primary experiment. Any later window
  is exploratory and requires a new protocol.

Use the official [MediaWiki revisions
API](https://www.mediawiki.org/wiki/API:Revisions) and interpret entity content
under the official [Wikibase JSON
format](https://doc.wikimedia.org/Wikibase/master/php/docs_topics_json.html).
Wikidata's [stable-interface
policy](https://www.wikidata.org/wiki/Wikidata:Stable_Interface_Policy/en)
does not treat raw revision content as a stable interface, so every retained
response, content model, slot hash, parser version, and independent endpoint
fact check is part of the reproducibility boundary.
The sole endpoint is `https://www.wikidata.org/w/api.php`, using
`action=query`. For each fixed H5 QID, acquisition has two noninterchangeable
passes:

1. **Metadata pass.** Query the single page with `titles=<QID>`,
   `prop=revisions`,
   `rvslots=main`, and
   `rvprop=ids|timestamp|sha1|slotsha1|contentmodel`. First obtain the lower
   checkpoint with `rvdir=older`, `rvstart=<lower timestamp>`, and `rvlimit=1`.
   If it exists, enumerate the locked chain with `rvdir=newer`,
   `rvstartid=<lower revision ID>`, `rvendid=<H5 upper revision ID>`, and
   `rvlimit=max`. If no lower checkpoint exists, enumerate from page creation
   with `rvdir=newer`, `rvendid=<H5 upper revision ID>`, and `rvlimit=max` and
   prepend the verified empty state. Follow every returned continuation object
   exactly, and log the request parameters and continuation object for every
   page.
2. **Content pass.** Request the exact metadata-pass revision IDs in ascending
   page-chain order, in batches of at most 50 IDs, with `revids`,
   `rvslots=main`, and
   `rvprop=ids|timestamp|sha1|slotsha1|contentmodel|content`. Content discovery
   from a second time-range query is forbidden. The returned revision-ID set
   and order-independent set hash must equal the requested batch exactly.

Every request uses `format=json`, `formatversion=2`, `maxlag=5`, a descriptive
user agent, and a 60-second transport timeout. A successful content batch is
followed by a one-second proactive wait. Retry only a transport timeout, HTTP
429, HTTP 5xx, or a MediaWiki `maxlag` response, for at most six total attempts.
After failed attempt `a` in `1..5`, wait

`min(120, max(Retry-After if valid else 0, 2^a))` seconds.

There is no random jitter. A missing or nonnumeric `Retry-After` is zero; a
server-required wait above 120 seconds ends acquisition as inconclusive rather
than silently shortening it. All attempts, statuses, response headers, waits,
and continuation tokens are logged. A repeated continuation token, a token
that does not add a revision, premature termination, or revisions outside the
locked endpoints is an integrity failure.

Do not request or retain editor identity, user ID, or edit comments. For every
revision, retain the QID/title, revision ID, parent revision ID, UTC timestamp,
revision SHA-1, main-slot SHA-1, main-slot content model, and main-slot JSON.
The metadata and content passes must agree exactly on these shared fields. The
main-slot content model must be `wikibase-item`; hidden SHA or content fields
are invalid. Cache every raw response immutably with its SHA-256. Acquisition
time is reported separately from certificate compute time.

### Page-chain integrity

For every QID, the implementation must verify all of the following before
collapsing any score-equivalent revisions:

1. revision IDs are unique and timestamps are nondecreasing;
2. each included non-initial revision's `parentid` equals the immediately
   preceding acquired revision ID;
3. no required revision or main-slot content is hidden, suppressed, malformed,
   or missing;
4. every content document identifies the expected entity;
5. the final revision ID equals the H5 historical revision ID; and
6. the final extracted fact set equals the corresponding H5 historical fact
   set exactly.

An entity absent at the lower timestamp may begin with a verified empty state
followed by its actual creation revision. Redirects, merges, hidden content,
unexplained parent gaps, or an H5 endpoint mismatch make the confirmatory run
`INCONCLUSIVE_REVISION_CHAIN_INTEGRITY`; they may not be interpolated or
silently dropped.

First extract the raw H5-policy fact set from every revision: all
non-deprecated direct entity-valued `property_id|Qtarget` statements. The final
raw set must equal the corresponding H5 historical fact set exactly. Then form
the scorer fact set by retaining only properties in the frozen MIND relation
vocabulary. Qualifiers, references, labels, descriptions, and sitelinks remain
outside the scorer. Consecutive revisions with identical scorer fact sets may
be collapsed only after the full raw parent chain and raw endpoint check pass,
and the collapsed state must retain the complete list of source revision IDs
that it represents.

One page revision is one atomic multi-fact state transition. Its additions and
deletions may not be selected independently. The only admitted ordering is the
observed page-local parent chain. Shared entities, timestamps, edit tags,
similar comments, and apparent batches are not evidence of cross-page
causality. H7A assumes a conservative bounded per-page FIFO staleness fault
model: each page is at one prefix position in its intact chain, and page
positions vary independently. The Cartesian product is exact for this declared
fault-model superset, not for an observed asynchronous ingestion trace.

This is a transaction-time ingestion model, not a valid-time model.

## Frozen label-blind POC cohort

From the committed H6 manifest, compute

`sample_key(i) = SHA256(UTF8("20260807|H7A|" + impression_id))`.

Sort by ascending hexadecimal `sample_key`, then ascending impression ID, and
take exactly the first 5,000 distinct impressions. Cohort construction may use
only manifest fields `i`, `u`, `h`, and candidate news IDs `c[*].n`; H6
structural scores may be ignored but no other field may be added. The ordered
5,000-impression ID list and its SHA-256 must be written before any certificate
metric is aggregated.

The committed full H6 cohort has 16,021 of 64,443 impressions with `m <= 10`
candidates. For such an impression, top-`min(10,m)` contains every candidate,
so Top-10 set invariance is vacuous. Report the sampled `m <= 10` count and its
non-Top-10 structural diagnostics separately, but exclude these impressions
from every Top-10 coverage, gate, bootstrap, endpoint false-assurance, and
Monte Carlo false-assurance denominator. Every such denominator is restricted
to `m > 10` and must be emitted explicitly with its numerator.

For every news row, let `A(n)` be the sorted set of distinct H5 top-50 QIDs in
the title or abstract annotations with confidence at least `0.90`. Candidate
and history order do not alter `A(n)`.

## Exact fixed-point additive scorer

All primary scorer and certificate arithmetic is signed integer arithmetic.
Set the fixed-point mass

`S = 2^20 = 1,048,576`.

Every use of `int64` must be preceded by a deterministic worst-case bound check;
otherwise use exact arbitrary-width integers. Floating-point arithmetic is
forbidden in primary scores, margins, certificates, and gates.

### Deterministic mass allocation

For nonnegative counts `c(k)` with positive total `C`, define integer weights
that sum exactly to `S`:

1. `w0(k) = floor(S * c(k) / C)`;
2. `rem(k) = (S * c(k)) mod C`;
3. distribute the remaining `S - sum_k w0(k)` units to keys in descending
   `rem(k)`, breaking ties by ascending canonical key; and
4. set `w(k)` to the resulting integer.

For a nonempty candidate anchor set, use the same rule with equal count one for
every QID, tied by ascending QID. Denote the resulting candidate anchor mass by
`a_i(q)`; it is fixed across all graph states and sums to `S`.

### Fixed user profiles

For impression `i` with supplied final-50 history `H_i`, define lower-checkpoint
counts

`cE_i(q) = sum_{h in H_i} 1[q in A(h)]`

and

`cF_i(f) = sum_{h in H_i} sum_{q in A(h)} 1[f in F_q(0)]`,

where `F_q(0)` is the primary-window lower-checkpoint fact state. Allocate
entity weights `wE_i(q)` and fact weights `wF_i(f)` with the exact mass rule.
H6 eligibility guarantees a positive entity total. If the fact total is zero,
set every fact weight and KG residual to zero and report the impression as
`zero_lower_fact_profile`; do not drop it.

The profile is deliberately frozen at the definitely ingested lower
checkpoint. Recomputing or renormalizing it at a feasible revision state would
destroy the additive certificate and is forbidden.

This lower-only profile narrows H7A materially. A fact added after the lower
checkpoint has zero score weight whenever that signature was absent from the
user's lower-checkpoint history profile. H7A can therefore test uncertainty in
the retention, deletion, reappearance, or cross-entity reuse of facts already
represented in that profile; it is not a general scorer for wholly novel KG
facts. Report this limitation rather than imputing a weight from future states.

For each QID and impression, classify a changing fact as `score_relevant` when
its `wF_i(f) > 0`. For every `m > 10` impression, also report:

- `revision_exposed`: at least one nominal boundary pair has a QID with
  nonzero anchor-weight difference whose page chain contains more than one
  scorer fact state before applying `wF`;
- `score_relevant_revision_exposed`: at least one such changing fact has
  positive `wF` and nonzero candidate anchor-weight difference; and
- `zero_weight_only_revision_exposed`: revision-exposed but not
  score-relevant-revision-exposed.

Report the number and mass of post-lower additions with zero `wF`, distinct
score-relevant changing signatures, and all three impression counts. No
zero-weight addition or impression may be dropped.

### Base, residual, and nominal score

For candidate news `j`, define the graph-independent entity base

`B_ij = sum_q a_j(q) * wE_i(q)`.

For page QID `q` at revision-chain state `t`, define

`G_iq(t) = sum_{f in F_q(t)} wF_i(f)`.

The additive KG residual and total score are

`R_ij(t) = sum_q a_j(q) * G_iq(t_q)`

and

`score_ij(t) = B_ij + R_ij(t)`.

The primary arithmetic bounds follow from nonnegative mass vectors that each
sum to `S`:

- `0 <= G_iq(t) <= S`;
- `0 <= B_ij <= S^2` and `0 <= R_ij(t) <= S^2`;
- `0 <= score_ij(t) <= 2*S^2 = 2^41`;
- any final pair margin lies in `[-2*S^2, 2*S^2]`; and
- the direct bound accumulator is at most `3*S^2 < 2^42` in absolute value,
  because `sum_q |a_j(q)-a_k(q)| <= 2*S`.

For the rational-strength sensitivities, compare scores after multiplying the
base by four and using residual numerators in `{1,2,4,8}`. The most conservative
intermediate accumulator bound is `20*S^2 < 2^45`. Every multiplication and
addition must be checked against these symbolic bounds and the observed sparse
support before casting to signed `int64`.

The primary residual strength is exactly one. Descriptive, non-gating
sensitivities may use strengths `1/4`, `1/2`, and `2`, evaluated with a common
integer denominator; they cannot rescue a failed primary gate. A candidate
with no retained anchor has base and residual zero.

As a quantization audit, repeat the primary structural ranking and certificate
calculation with `S_hi = 2^24`, using the same largest-remainder rule. Its
largest sensitivity accumulator is below `2^53` and signed-`int64` safe. For
every `m > 10` impression, compare the nominal Top-10 set and boolean
certificate status at the two scales. Report both agreement rates, their joint
agreement, the certified-rate difference over all `m > 10` impressions, and
every discordant impression ID. It is an integrity gate: joint agreement must
be at least 99 percent, the absolute certified-rate difference must be at most
0.005, and no overflow or scientific gate decision may change.

The nominal state is the upper revision of every page. Sort by descending
integer score, breaking equal scores by ascending hexadecimal SHA-256 of
`20260807|impression_id|news_id`, exactly as in H6.

### Exact pair and Top-10 certificate

For every user/impression and QID, cache

- `L_iq = min_t G_iq(t)` and its earliest source revision-ID witness;
- `U_iq = max_t G_iq(t)` and its earliest source revision-ID witness; and
- the nominal upper-state value.

For candidates `j` and `k`, let `d_q = a_j(q) - a_k(q)`. The exact worst
feasible pair margin over the product of real page chains is

`chain_lower(j,k) = B_ij - B_ik`

`  + sum_{q: d_q >= 0} d_q * L_iq`

`  + sum_{q: d_q < 0}  d_q * U_iq`.

Define the exact upper feasible margin symmetrically:

`chain_upper(j,k) = B_ij - B_ik`

`  + sum_{q: d_q >= 0} d_q * U_iq`

`  + sum_{q: d_q < 0}  d_q * L_iq`.

For the endpoint-only heuristic, let `Lend_iq` and `Uend_iq` be the minimum and
maximum of only the lower and upper page projections, and define
`endpoint_lower(j,k)` by substituting `Lend` and `Uend` into the
`chain_lower` formula.

For an impression with `m > 10`, a **boundary pair** is an ordered pair with
nominally selected `j` and nominally unselected `k`. It is an **affected
boundary pair** exactly when

`chain_upper(j,k) - chain_lower(j,k) > 0`.

The impression is **boundary-affected** when it has at least one affected
boundary pair. An affected boundary pair is **interior-worse** exactly when

`chain_lower(j,k) < endpoint_lower(j,k)`.

All comparisons are exact integer comparisons. `Interior-worse` means that an
intermediate real page revision produces a stricter adverse bound than both
window endpoints; a numerical tolerance or nominal-score change is not a
substitute for this definition.

This follows by separability across page chains. For each nonzero `d_q`, choose
the earliest chronological chain state attaining `L_iq` when `d_q > 0` and
the earliest attaining `U_iq` when `d_q < 0`; for `d_q == 0`, choose the lower
checkpoint. Within a collapsed scorer state, choose its earliest raw source
revision. Serialize the global witness as ascending QID followed by chain
index and revision ID. This deterministic state vector is the canonical
adverse witness. Shared QIDs cancel through `d_q`; they must not be optimized
independently for the two candidates.

Replay every canonical witness from the raw cached revision contents, using an
independent fact extractor and scorer implementation. It must reproduce every
per-page projection, both candidate scores, and the exact compiled lower
margin. For an uncertified impression, the canonical list witness is the
failing boundary pair with smallest `chain_lower`, tied by selected news ID and
then unselected news ID.

For `m > 10`, let `T` be the nominal Top-10 candidate set. `T` is certified
invariant if, for every `j` in `T` and `k` outside `T`, either:

1. `chain_lower(j,k) > 0`; or
2. `chain_lower(j,k) == 0` and the fixed tie hash ranks `j` before `k`.

No sampled-state success may be called a certificate.

## Required baselines

1. **Nominal upper state:** score and rank using every page's upper revision.
2. **Safe lower state:** score and rank using every primary-window lower
   checkpoint.
3. **Revision-chain certificate:** the proposed exact bound and revision-ID
   witness above.
4. **Independent-fact mask:** for each page, facts in every feasible state are
   definitely present and facts in any feasible state are possibly present.
   Because `wF` is nonnegative, use the definitely-present sum as its lower
   projection and the possibly-present sum as its upper projection. This is a
   safe provenance-blind superset, not a matched stochastic model.
5. **Endpoint-only envelope:** use only the lower and upper page projections.
   Evaluate it only for `m > 10`. This is an explicitly unsafe heuristic.
   Report false certifications against the full chain; never describe it as
   certified. Its impression-level
   false-assurance denominator is boundary-affected `m > 10` impressions that
   the endpoint heuristic declares Top-10 stable. The numerator is those same
   impressions that the exact chain certificate does not certify. If the
   denominator is zero, report `NA` and the zero count.
6. **Deterministic Monte Carlo:** 1,000 product states per boundary-affected
   `m > 10` impression. For replicate `b` and ascending page `q`, hash
   successive counters as
   `SHA256("20260807|H7MC|" + b + "|" + impression_id + "|" + q + "|" + counter)`.
   For `n` chain states, accept the first unsigned big-endian digest
   `x < floor(2^256/n)*n` and choose state `x mod n`. Sampling is diagnostic
   only. Call an impression `MC-stable` when none of its 1,000 sampled states
   changes the nominal Top-10 set. The Monte Carlo false-assurance denominator is
   boundary-affected `m > 10` impressions that are MC-stable; its numerator is
   those same impressions that the exact chain certificate does not certify.
   If the denominator is zero, report `NA` and the zero count.

For exact validation, identify boundary pairs whose Cartesian product of
relevant page-state counts is at most 100,000. Sort them by SHA-256 of
`20260807|H7ENUM|impression_id|selected_news_id|unselected_news_id` and
exhaustively enumerate the first 100, or all if fewer than 100 exist. The
enumerated minimum margin must match the compiled certificate exactly. Among
equal minima, choose the lexicographically smallest canonical witness
serialization defined above; that witness must also match exactly.

## Frozen robustness-view reconstruction

The metadata/navigation blocklist is the H6 list `P1343, P1424, P5008, P6104,
P7867, P8744, P9241, P2354, P8402, P10280, P1889`. Its view removes those
properties from every page state, then recomputes lower fact counts and
reallocates each positive user fact mass to sum exactly to `S` by the same
largest-remainder rule.

The hub-excluded view removes QIDs `Q30` and `Q22686` from every news anchor
set, then recomputes user entity counts, lower fact counts, candidate anchor
weights, base scores, residuals, nominal rankings, boundary pairs, and
certificates. Every nonempty mass vector is reallocated to sum exactly to `S`.
A now-empty candidate anchor set receives base and residual zero; a now-empty
user entity profile receives a zero base; and a now-empty user fact profile
receives a zero residual. No impression, history article, or candidate is
dropped, and candidate count `m` is unchanged in either view.

All view-specific Top-10 rates use that view's own `m > 10`
boundary-affected cohort. The chain and independent-fact methods within a view
must use the identical cohort and bootstrap resamples. Primary-view membership
may not be reused to improve a robustness result.

## Metrics

Report at minimum:

- raw and collapsed revision counts per QID;
- fact-changing QIDs, additions, deletions, reverts, and distinct fact states;
- nonzero-support QIDs and impressions in the two frozen robustness views;
- sampled impression counts for `m <= 10` and `m > 10`, with 16,021/64,443
  retained as the independently known full-cohort vacuity check;
- zero-lower-fact-profile impressions;
- revision-exposed, score-relevant-revision-exposed, and
  zero-weight-only-revision-exposed `m > 10` impressions;
- distinct and occurrence-weighted score-relevant changing facts and
  post-lower zero-weight additions;
- impressions with at least one candidate whose feasible score range is
  nonzero, reported as a non-Top-10 structural diagnostic for both `m` strata;
- nominal-versus-safe score, total-order, and Top-1 changes for both `m`
  strata, but Top-10 changes only for `m > 10`;
- boundary pairs, affected boundary pairs, interior-worse pairs, and
  boundary-affected `m > 10` impressions, with every denominator explicit;
- exact Top-10 certified rate on all `m > 10` impressions and separately on
  the boundary-affected `m > 10` denominator;
- independent-fact certified rate and its paired difference from the chain
  rate on the identical boundary-affected `m > 10` denominator;
- endpoint-only and Monte Carlo false-assurance numerators and denominators;
- exact-witness replay and exhaustive-enumeration results;
- primary-versus-high-scale quantization agreement and all discordant IDs;
- compile time, total compute time, peak resident memory, and median, p95, and
  p99 per-impression certificate latency; and
- all metrics for the seven-day window, metadata/navigation property
  blocklist, and removal of QIDs `Q30` and `Q22686` as non-gating sensitivity
  views unless explicitly included in the gates below.

For the primary difference between chain and independent-fact certification,
use 2,000 paired user-cluster bootstrap replicates on the locked
boundary-affected `m > 10` denominator. Sort its `N` distinct user IDs
lexicographically. In replicate `b`, make exactly `N` draws with replacement.
For draw `d`, hash successive nonnegative counters as

`SHA256("20260807|H7BOOT|" + b + "|" + d + "|" + counter)`.

Interpret the digest as an unsigned 256-bit big-endian integer `x`. Accept the
first `x < floor(2^256/N)*N` and select sorted user index `x mod N`; this avoids
modulo bias. A selected user retains every one of that user's eligible sampled
impressions, with multiplicity. Use the identical weighted impressions for the
chain and independent-fact indicators, and record their mean difference.

Sort the 2,000 replicate differences ascending. The fixed percentile interval
uses the nearest-rank order statistics `x_(50)` and `x_(1950)`, indexed from
one. Emit the user count, impression count, all replicate differences, and both
endpoints. If `N == 0`, the relevant gate fails; it is not `NA`.

## Advance gate

The sole positive verdict is `ADVANCE_H7_TO_LABELLED_OUTCOME_POC`. It requires
all integrity and exactness checks plus every condition below on the primary
30-day, residual-strength-one experiment:

1. all 50 page chains pass the integrity contract;
2. at least 10 of 50 QIDs contain at least two distinct retained fact states;
3. after removing `Q30` and `Q22686`, at least five QIDs still contain at least
   two distinct retained fact states;
4. among sampled `m > 10` impressions, at least 10 percent are
   boundary-affected and at least 10 percent are
   score-relevant-revision-exposed; among revision-exposed `m > 10`
   impressions, fewer than 90 percent are zero-weight-only; and at least 10
   distinct changing fact signatures, including at least one post-lower
   addition, are score-relevant in at least one boundary-affected impression;
5. at least 100 affected boundary pairs are interior-worse, and
   interior-worse pairs constitute at least one percent of all affected
   boundary pairs;
6. on the boundary-affected `m > 10` denominator, the exact chain Top-10
   certified rate is at least 20 percent;
7. on that same denominator, at least five percent remain uncertified, so
   certificate routing is non-degenerate;
8. on that same boundary-affected `m > 10` denominator, the chain Top-10
   certified rate exceeds the independent-fact rate by at least 0.05 absolute,
   and the paired user-bootstrap 95 percent interval for that difference lies
   strictly above zero;
9. in the hub-excluded view's own boundary-affected `m > 10` denominator, at
   least five percent of all hub-view `m > 10` impressions are
   boundary-affected and the chain certificate retains at least a 0.02
   absolute advantage over the independent-fact certificate;
10. the `S_hi = 2^24` audit has at least 99 percent per-impression Top-10 and
    certificate-status agreement, at most 0.005 absolute certified-rate
    difference, no overflow, and the same pass/fail result for every
    scientific gate;
11. every exhaustively enumerated minimum and every replayed adverse witness
    agrees exactly with the compiled result;
12. primary chain projection, nominal ranking, and exact certificate
    computation for all 5,000 impressions completes within 60 seconds in one
    process, excluding network acquisition, immutable-input hashing, bootstrap,
    Monte Carlo diagnostics, high-scale audit, robustness views, witness
    replay, and the exhaustive verifier;
13. p95 per-impression certificate latency is at most 10 milliseconds; and
14. no result, ledger, or log contains a candidate click suffix or aggregate
    outcome statistic.

Bootstrap, Monte Carlo, and exhaustive-verification runtimes must still be
reported separately and remain subject to the single-process safety boundary.

## Kill and inconclusive rules

- A valid run that fails any scientific support, tightness, non-degeneracy,
  hub-robustness, exactness, or runtime gate receives
  `KILL_H7_REVISION_CHAIN_DIRECTION`.
- A primary miss cannot be rescued by changing the window, fixed-point scale,
  residual strength, sample, relation policy, profile construction, baseline,
  or threshold after inspection.
- A transport failure, immutable hash mismatch, page-chain gap, endpoint fact
  mismatch, malformed source response, unexpected overwrite, stderr output,
  asynchronous-error entry, or incomplete process/lock ledger is
  `INCONCLUSIVE`, never a scientific failure or pass.
- If endpoint-only bounds match the full-chain bounds, or the chain certificate
  gains less than the locked threshold over independent-fact masking, the
  revision-chain interval direction is killed even if nominal and safe rankings
  differ.
- If the primary effect depends on `Q30` or `Q22686`, the direction is killed.
- General min-cut development is not unlocked by a chain-only pass. It requires
  an H7B protocol, measured stream partitions/consumer offsets or explicit
  real computational lineage, and a demonstrated material loss from the
  product-of-chains relaxation. Synthetic semantic rules, timestamps, or shared
  graph neighborhoods are insufficient.
- If exact page versions or consumer checkpoints are available for the serving
  decision, H7A is killed for that regime because exact replay dominates.

## Runtime and Windows safety boundary

The eventual implementation must comply with
`experiments/WINDOWS_SAFE_EXECUTION_CONTRACT_2026-08-05.md`.

- Use one bounded process with no multiprocessing, worker pool, or application
  threads.
- Before importing numerical libraries, set every BLAS/OpenMP/thread-count
  environment variable to one and set `CUDA_VISIBLE_DEVICES=-1`.
- Invoke the workspace interpreter directly with `-B -u`; never use `uv run`.
- Use a hidden child process with persistent, separate stdout, stderr, and
  asynchronous-error ledgers.
- Require authorization, start, acknowledgement, exact-PID, inner-lock, and
  outer-lock handshakes. Kill and wait for the exact child on any rejection or
  failure.
- Cache immutable API responses and compiled chains; never refetch inside the
  scoring process.
- Refuse to overwrite a run directory. Write artifacts atomically and write a
  hash-binding completion marker only after all child processes exit, every
  ledger is verified empty, locks are released, and exact replay succeeds.
- Any nonempty stderr or asynchronous-error ledger invalidates the run.

### Runtime measurement contract

Use a monotonic high-resolution clock and record integer nanoseconds. Report
three disjoint timings:

1. acquisition, retry waits, and raw-response publication;
2. immutable hashing, file loading, JSON parsing, raw fact extraction, and
   global page-chain compilation; and
3. primary per-impression scorer/certificate computation.

For timing 3, load and validate the compiled page chains, frozen news mapping,
and ordered 5,000-impression IDs first. Start the core timer immediately before
constructing the first impression's user profiles and stop only after all
5,000 primary nominal rankings, chain bounds, independent-fact bounds,
certificates, canonical witnesses, and primary counters are in memory. It
includes profile construction and all `m <= 10` structural diagnostics, but
excludes serialization, bootstrap, Monte Carlo, high-scale quantization audit,
robustness views, and exhaustive verification. Do not exclude warm-up
impressions, trigger garbage collection, change process priority, or discard an
observed run.

Record one latency for each impression from the start of its profile
construction through completion of its primary counters and certificate (or
its explicit `m <= 10` vacuity record). Sort all 5,000 integer latencies and
report nearest-rank median, p95, and p99 using indices `ceil(p*N)`, indexed from
one. Both the primary and exact-replay core timings must independently satisfy
the total and p95 gates. Also report launcher-to-completion wall time, CPU
model, logical-core count, RAM, operating-system build, interpreter and package
hashes, and whether the input files were already resident in the OS cache if
that fact is observable. No timing may be selected from repeated trials.

Bootstrap, Monte Carlo, high-scale, each robustness view, witness replay, and
exhaustive enumeration receive separate timers. They remain single-process
and are never included selectively in the core number.

The scorer should compile sparse revision deltas once. For each user and page,
update `G_iq(t)` only on facts present in the sparse user profile and cache its
minimum, maximum, upper value, and witnesses. At inference, evaluate only the
`K(m-K)` nominal boundary pairs and only QIDs with nonzero anchor-weight
difference. Cartesian snapshot enumeration is prohibited outside the locked
small-case verifier.

## Recommendation-scope limitation and next stage

The current workspace contains MIND-small development data but no immutable
MIND training split. H7A therefore does not define or stratify items by prior
interaction status, and no claim about that status may appear in its result. It
is a label-blind revision-certificate feasibility experiment on news
recommendation.

If and only if H7A advances, a separate protocol may acquire and hash the
official training split, define any zero-prior-interaction subgroup entirely
before outcome comparison, and then open labels on a frozen cohort. That
outcome protocol must compare the always-on residual, no-KG base, safe-lower
residual, certificate-gated residual, a random gate matched on activation rate,
and an uncertainty-magnitude gate matched on activation rate.
Publication-level claims would additionally require at least one independent
dataset with real source revision histories and representative learned
recommenders.
