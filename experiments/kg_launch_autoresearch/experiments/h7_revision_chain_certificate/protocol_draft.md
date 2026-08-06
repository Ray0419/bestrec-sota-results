# H7 Prospective Protocol: Revision-Chain-Certified KG Residual

Status: **draft; not locked and not authorized for execution**

Classification: label-blind structural feasibility proof of concept

Draft date: 2026-08-07

## Research question and scope

For a cold-item recommender whose external knowledge graph may be incompletely
materialized at serving time, can actual source revision histories define a
non-vacuous uncertainty set and support an exact, low-latency Top-10
invariance certificate for an additive KG residual?

This experiment tests only structural support, certificate tightness, exactness,
and runtime. It must not parse candidate click suffixes, compute recommendation
outcomes, or select any design choice using labels. A positive result is a gate
to a separately locked outcome experiment; it is not evidence of improved
recommendation quality by itself.

The mathematical closure/min-cut result is classical. This protocol neither
implements a general min-cut solver nor claims novelty for minimum closure,
partial-order Top-K, temporal recommendation, KG provenance, generic
certification, uncertainty routing, or additive residuals in isolation. The
candidate contribution is only the eventual package of real revision
provenance, an exact downstream ranking certificate, and certificate-controlled
KG fusion.

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

The H6 manifest is the only allowed impression/candidate source. The H7
phase-A runner must not open `behaviors.tsv`; this prevents access to candidate
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

For each fixed H5 QID, acquire from the official Wikidata/MediaWiki revisions
API:

1. the last revision at or before the lower-window timestamp;
2. every subsequent revision through the exact H5 upper revision at or before
   `tau`; and
3. for every returned revision, the QID/title, revision ID, parent revision ID,
   UTC timestamp, source SHA-1, and main-slot JSON content.

Do not request or retain editor identity or edit comments. Respect API
continuation and the content-response limit, use a descriptive user agent,
throttle sequential requests, and cache every raw response immutably with its
SHA-256. Retries and waits must be logged. Acquisition time is reported
separately from certificate compute time.

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
deletions may not be selected independently. The only admitted dependency is
the observed page-local parent chain. Shared entities, timestamps, edit tags,
similar comments, and apparent batches are not evidence of cross-page
causality. With independently lagging page shards, the feasible graph state is
the Cartesian product of one prefix position per intact page chain.

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

### Base, residual, and nominal score

For candidate news `j`, define the graph-independent entity base

`B_ij = sum_q a_j(q) * wE_i(q)`.

For page QID `q` at revision-chain state `t`, define

`G_iq(t) = sum_{f in F_q(t)} wF_i(f)`.

The additive KG residual and total score are

`R_ij(t) = sum_q a_j(q) * G_iq(t_q)`

and

`score_ij(t) = B_ij + R_ij(t)`.

The primary residual strength is exactly one. Descriptive, non-gating
sensitivities may use strengths `1/4`, `1/2`, and `2`, evaluated with a common
integer denominator; they cannot rescue a failed primary gate. A candidate
with no retained anchor has base and residual zero.

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

`lower_margin(j,k) = B_ij - B_ik`

`  + sum_{q: d_q >= 0} d_q * L_iq`

`  + sum_{q: d_q < 0}  d_q * U_iq`.

This follows by separability across page chains. The corresponding cached
argmin or argmax revision for every nonzero `d_q` is an explicit feasible
adverse-version witness. Shared QIDs cancel through `d_q`; they must not be
optimized independently for the two candidates.

Let `T` be the nominal top-`min(10,m)` candidate set. `T` is certified invariant
if, for every `j` in `T` and `k` outside `T`, either:

1. `lower_margin(j,k) > 0`; or
2. `lower_margin(j,k) == 0` and the fixed tie hash ranks `j` before `k`.

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
   This is an explicitly unsafe heuristic. Report false certifications against
   the full chain; never describe it as certified.
6. **Deterministic Monte Carlo:** 1,000 product states per impression. For
   replicate `b` and page `q`, select
   `int(SHA256("20260807|H7MC|" + b + "|" + impression_id + "|" + q), 16)
   mod number_of_chain_states(q)`. Sampling is diagnostic only.

For exact validation, identify boundary pairs whose Cartesian product of
relevant page-state counts is at most 100,000. Sort them by SHA-256 of
`20260807|H7ENUM|impression_id|selected_news_id|unselected_news_id` and
exhaustively enumerate the first 100, or all if fewer than 100 exist. The
enumerated minimum margin and earliest lexicographic revision witness must
match the compiled certificate exactly.

## Metrics

Report at minimum:

- raw and collapsed revision counts per QID;
- fact-changing QIDs, additions, deletions, reverts, and distinct fact states;
- QIDs and impressions surviving the two frozen robustness views;
- zero-lower-fact-profile impressions;
- impressions with at least one candidate whose feasible score range is
  nonzero (`structurally affected`);
- nominal-versus-safe score, total-order, Top-1, and Top-10 changes;
- exact Top-10 certified rate overall and among structurally affected
  impressions;
- independent-fact certified rate and paired difference from the chain rate;
- endpoint-only false-certificate rate;
- relevant boundary pairs for which an intermediate state is strictly worse
  than both endpoints;
- exact-witness replay and exhaustive-enumeration results;
- Monte Carlo false-assurance rate relative to the exact certificate;
- compile time, total compute time, peak resident memory, and median, p95, and
  p99 per-impression certificate latency; and
- all metrics for the seven-day window, metadata/navigation property
  blocklist, and removal of QIDs `Q30` and `Q22686` as non-gating sensitivity
  views unless explicitly included in the gates below.

For the primary difference between chain and independent-fact certification,
use 2,000 paired user-cluster bootstrap replicates. Sample users with
replacement, retain all their sampled impressions, use identical resamples for
both methods, and seed each replicate by SHA-256 of
`20260807|H7BOOT|replicate_id`.

## Advance gate

The sole positive verdict is `ADVANCE_H7_TO_LABELLED_OUTCOME_POC`. It requires
all integrity and exactness checks plus every condition below on the primary
30-day, residual-strength-one experiment:

1. all 50 page chains pass the integrity contract;
2. at least 10 of 50 QIDs contain at least two distinct retained fact states;
3. after removing `Q30` and `Q22686`, at least five QIDs still contain at least
   two distinct retained fact states;
4. at least 10 percent of the 5,000 impressions are structurally affected;
5. at least 100 relevant boundary pairs, and at least one percent of affected
   relevant boundary pairs, have a full-chain adverse state strictly worse
   than both endpoints;
6. among structurally affected impressions, the exact chain Top-10 certified
   rate is at least 20 percent;
7. at least five percent of structurally affected impressions remain
   uncertified, so certificate routing is non-degenerate;
8. the chain Top-10 certified rate exceeds the independent-fact rate by at
   least 0.05 absolute, and the paired user-bootstrap 95 percent interval for
   that difference lies strictly above zero;
9. after removing `Q30` and `Q22686`, at least five percent of impressions are
   structurally affected and the chain certificate retains at least a 0.02
   absolute advantage over the independent-fact certificate;
10. every exhaustively enumerated minimum and every replayed adverse witness
    agrees exactly with the compiled result;
11. primary chain projection, nominal ranking, and exact certificate
    computation for all 5,000 impressions completes within 60 seconds in one
    process, excluding network acquisition, immutable-input hashing, bootstrap,
    Monte Carlo diagnostics, and the exhaustive verifier;
12. p95 per-impression certificate latency is at most 10 milliseconds; and
13. no result, ledger, or log contains a candidate click suffix or aggregate
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
  provenance-structure direction is killed even if nominal and safe rankings
  differ.
- If the primary effect depends on `Q30` or `Q22686`, the direction is killed.
- General min-cut development is not unlocked by a chain-only pass. It requires
  a new protocol, explicit real cross-stream prerequisite provenance, and a
  demonstrated material loss from the product-of-chains relaxation. Synthetic
  semantic rules, timestamps, or shared graph neighborhoods are insufficient.

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

The scorer should compile sparse revision deltas once. For each user and page,
update `G_iq(t)` only on facts present in the sparse user profile and cache its
minimum, maximum, upper value, and witnesses. At inference, evaluate only the
`K(m-K)` nominal boundary pairs and only QIDs with nonzero anchor-weight
difference. Cartesian snapshot enumeration is prohibited outside the locked
small-case verifier.

## Strict-coldness limitation and next stage

The current workspace contains MIND-small development data but no immutable
MIND training split. H6 structural eligibility does not prove that a candidate
is a strict cold item. Therefore this POC must be described as a label-blind
revision-certificate feasibility experiment on news recommendation, not as a
strict cold-start result.

If and only if H7 advances, a separate protocol may acquire and hash the
official training split, define strict item coldness entirely before outcome
comparison, and then open labels on a frozen cohort. That outcome protocol must
compare the always-on residual, no-KG base, safe-lower residual,
certificate-gated residual, a random gate matched on activation rate, and an
uncertainty-magnitude gate matched on activation rate. Publication-level claims
would additionally require at least one independent dataset with real source
revision histories and representative learned recommenders.
