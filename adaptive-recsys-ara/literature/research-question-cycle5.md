# Phase 2, Cycle 5: CABLE-PREF Research Question and Promise Gate

Date locked: 2026-08-07  
Status: prospectively locked before archive extraction or label parsing  
Phase 5 status: forbidden unless every registered gate passes

## Primary research question

> On a prospectively selected temporal MovieLens 10M cohort, with immutable
> SentenceTransformer item vectors and an exact output contract of 200 unseen
> BPR candidates plus 200 BPR-novel semantic candidates, can CABLE-PREF's
> endpoint-leave-out, SimPO-style admission-boundary alignment improve
> user-macro admission@200 of BPR-missed preferred items by at least `+0.020`
> over raw exact-complement retrieval and `+0.010` over order-only
> reference-free alignment, while improving strict preference-consistent
> exposure@10 by at least `+0.005` over both the raw hybrid and BPR, without
> material relevance, dislike-safety, seed-stability, or p95-latency regression?

The question is empirically testable and addresses a specific preference-
alignment/latency gap. It does **not** claim that exhaustive masked search is a
sublinear or production-scale ANN contribution.

## Narrow hypothesis

Ordinary pairwise alignment can improve `score(chosen) - score(rejected)` while
neither endpoint crosses a fixed retrieval cutoff. CABLE-PREF instead trains a
bounded, normalized semantic query against the exact request-specific admission
decision it will face at serving time.

For preferred endpoint `i+`, the target is

```text
t_u^(-i+) = Kth score in D_u \\ {i+}, K=200,
```

where `D_u` is the semantic catalog after removing the user's prefix and the
frozen BPR top-200. The rejected endpoint remains a real competitor. With the
deployed score-plus-item-ID tie rule, `i+` enters semantic top-200 if and only if
its ordering key beats this leave-one-endpoint-out boundary. This
action-consistency property—not generic interest-threshold learning—is the
mechanistic claim.

## Authenticated unopened dataset

- Official GroupLens MovieLens 10M archive:
  `https://files.grouplens.org/datasets/movielens/ml-10m.zip`.
- Required size: `65,566,137` bytes.
- Required SHA-256:
  `813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862`.
- Corroborating official-sidecar MD5:
  `ce571fd55effeba0271552578f2648bd`.
- Allowed inputs: `ratings.dat` and `movies.dat`; `tags.dat` is forbidden
  because tags are interaction-derived metadata.
- At Phase-2 lock time the zip had only been downloaded and hashed. It had not
  been extracted, listed, parsed, or inspected.

The official README reports 10,000,054 ratings, 95,580 tags, 10,681 movies, and
71,567 users. The study is explicitly an offline, exposure-conditioned
warm-user PoC; it makes no causal, fairness, or counterfactual-exposure claim.

## Prospectively fixed cohort and time semantics

- Within each user, sort events by `(timestamp, source_row_ordinal)` and keep
  equal-timestamp events in one indivisible group.
- Allocate consecutive groups to `A=60%`, `R=20%`, `V=10%`, and sealed `T=10%`
  by nearest cumulative event count, breaking cutoff ties toward the earlier
  group. Adjacent nonempty blocks must have strict timestamp order.
- Structural eligibility uses counts, times, catalog capacity, and `A` only:
  at least 80 total events, at least four timestamp groups, at least 20 `A`
  events, at least five distinct `A` items rated at least 4, and at least 700
  catalog items unseen at the longest prefix. No `R/V/T` item identity, rating,
  positive count, pair, or candidate outcome may affect cohort membership.
- Order eligible users by
  `SHA256("20260835:{user_id}")`, then numeric user ID, and take exactly 2,000.
  Fewer than 2,000 eligible users fails closed.
- This is a per-user future-ranking estimand, not a global calendar-time
  deployment split. That limitation must remain explicit.

The semantic catalog is every movie with allowed metadata. The collaborative
catalog is prospectively frozen from cohort `A` only and requires at least five
positive (`rating >= 4`) `A` interactions per item. At every request the BPR
domain must contain at least 200 prefix-unseen items and the semantic complement
must contain at least 500 items; otherwise the run fails before current-block
target access.

## Fixed preference and relevance estimands

After a stage's complete target-blind query, mask, candidate, score, and ranking
manifests are durable and hashed, form natural pairs from that stage only:

- pair distinct items whose rating gap is at least 2.0;
- the higher-rated endpoint is preferred;
- cap at 100 pairs per user by ascending
  `SHA256("20263503:{user_id}:{low_item_id}:{high_item_id}")`;
- pair IDs and directions are fixed across methods and seeds;
- bootstrap users, never pair rows.

For `T`, deduplicate the preferred endpoints within each user. Let `P_u` be
those endpoints and let `M_u={i in P_u: i not in B_u}`, where the one shared
target-blind BPR branch is fixed before any semantic method. Define:

```text
ConditionalAdmission@200(u) = mean_{i in M_u} 1[i in S_u]
NetNewPreferredSupport(u)    = mean_{i in P_u} 1[i not in B_u and i in S_u]
```

Users without the relevant fixed denominator do not silently disappear: their
count is reported, and the registered support floor below must pass. Each
preferred endpoint is counted once regardless of how many rejected endpoints
it beats.

For every fixed natural pair, let `r10(i)` be its served rank when in the top
10 and 11 otherwise:

```text
sPCE_pair@10 = 1 if r10(preferred) < r10(rejected), else 0.
```

Both-unshown pairs score zero. Pair-order changes below rank 10 earn no credit.
Binary NDCG@10 and Recall@10 use every naturally rated item with rating at
least 4. Low-rating intrusion@10 uses observed items rated at most 2; unobserved
items remain unknown.

## Registered controls

Every semantic control shares the exact same BPR branch, complement mask,
candidate quotas, item matrices/indexes, optimizer steps, parameter count,
initialization family, pair presentations, clipping, checkpoint rule, fusion
coefficient, ranking rule, and latency instrumentation.

1. BPR only.
2. Raw SentenceTransformer exact-complement hybrid.
3. Order-only reference-free alignment.
4. Admission-only alignment.
5. Full CABLE-PREF.
6. Deterministically shuffled chosen/rejected directions with the full loss.
7. UIB-style learned-boundary control.
8. Wrong-boundary control using the pre-BPR-exclusion semantic cutoff.

The loss terms are separately user-macro normalized before their registered
weights are combined, so the full method does not merely receive twice the
gradient magnitude. Validation relevance may select one fusion coefficient
for the raw hybrid; it is then shared by all hybrids. No validation preference
outcome may select an epoch, loss weight, margin, boundary, cohort, or gate.

## G1-G9 all-or-nothing promise gate

1. **G1 — exact feasibility and action consistency.** Every eligible request
   returns exactly 200 unique unseen BPR items, exactly 200 unique unseen and
   BPR-novel semantic items, and a 400-item union. An independent full-score
   stable-sort replay agrees on every ID and order. Synthetic and real replay
   verify the leave-one-endpoint cutoff/admission equivalence and deterministic
   ties. Item matrices and indexes remain hash-identical.
2. **G2 — material preferred admission.** CABLE-PREF's user-macro conditional
   Admission@200 point gain is at least `+0.020` over raw exact-complement
   retrieval and `+0.010` over order-only alignment, with both paired 95%
   lower bounds above zero. Its unconditional NetNewPreferredSupport gain over
   raw is at least `+0.010`, with lower bound above zero. Its point net admission
   advantage `mean(1[i+ in S]-1[i- in S])` exceeds raw.
3. **G3 — served preference utility.** CABLE-PREF's user-macro sPCE@10 gain is
   at least `+0.005` over both raw hybrid and BPR, with both paired 95% lower
   bounds above zero. Preferred-endpoint top-10 exposure has positive point gain
   over raw.
4. **G4 — relevance and dislike safety.** Against the validation-selected
   stronger relevance baseline of raw hybrid and BPR: NDCG@10 point delta is at
   least `-0.0002` and its lower bound is strictly above `-0.001`; Recall@10
   lower bound is strictly above `-0.002`. Against raw hybrid, the low-rating
   intrusion increase upper bound is at most `+0.002`.
5. **G5 — matched mechanism controls.** Full CABLE-PREF has strictly greater
   point Admission@200 than order-only, UIB-style, wrong-boundary, and shuffled-
   direction controls, and strictly greater point sPCE@10 than admission-only,
   order-only, UIB-style, wrong-boundary, and shuffled-direction controls.
6. **G6 — nondegenerate support and power.** `R` supplies at least 20,000 fixed
   pairs from 1,000 users; `T` supplies at least 5,000 fixed natural pairs and
   5,000 unique BPR-missed preferred endpoints, each from at least 1,000 users.
   Admission membership differs from raw on at least 5% of fixed missed
   endpoints and sPCE pair outcomes differ on at least 2% of fixed pairs. A
   centered fixed-`V` audit, after all choices freeze, detects injected `+0.020`
   admission and `+0.005` sPCE effects in at least 80% of 1,000 bootstrap
   experiments; failure kills before `T`.
7. **G7 — seed stability.** All seeds `{20260835,20260836,20260837}` complete
   and enter the aggregate. At least two independently show positive admission
   gain over raw and order-only, positive sPCE gain over raw, and NDCG delta at
   least `-0.0002`. No seed's NDCG delta is below `-0.001`.
8. **G8 — serving latency.** For 512 prospectively hash-selected requests,
   one CPU thread, resident matrices, 32 warm-ups, seven AB/BA-interleaved
   repetitions, and per-request medians, worst-seed CABLE p95 is at most
   `10 ms` and at most `1.25x` the identically instrumented raw exact-complement
   hybrid. Timing includes query construction/adapter, both full score paths,
   mask/complement construction, stable top-k, fusion, and sorting; it excludes
   training, encoding, disk I/O, and metric joins.
9. **G9 — provenance and external replay.** Archive/extraction, cohort,
   temporal order, target blindness, candidate manifests, source, protocol,
   config, environment, interpreter, model, matrices, indexes, raw arrays,
   bootstrap, process exit, lock release, empty stderr/error ledgers, and
   recursive hashes all verify. A separately source-bound post-exit verifier
   recomputes G1-G9 before publishing the sole authoritative marker.

Use a paired 10,000-draw user-cluster percentile bootstrap at alpha 0.05 with
seed `20263504`, after averaging the three optimization seeds within user.

```text
PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9
```

Any false gate, support failure, power failure, process failure, or incomplete
external verification kills CABLE-PREF immediately. No outcome rerun, source
repair, threshold change, cohort substitution, partial-seed rescue, weighted
score, or manual override is authorized. A killed design returns to Phase 1;
only a fully verified `PROMISING=true` authorizes Phase 5.

## Novelty and scope constraints

- Masked/exact retrieval and filtered ANN are infrastructure, not contributions.
- SimPO supplies the reference-free pairwise idea; CABLE's candidate claim is
  the exact leave-one-endpoint admission target on the deployed branch
  complement.
- UIB learns a personalized interest boundary; CABLE must beat its matched
  learned-boundary control to support the narrower nonparametric order-statistic
  claim.
- CIGAR occupies generic candidate-oriented training. CABLE's claim is limited
  to action-consistent dense-query alignment with immutable catalog geometry.
- The MovieLens-scale p95 result is a PoC latency claim. A later paper must
  separately test filtered ANN against the exact oracle at substantially larger
  catalogs before making a scale claim.

