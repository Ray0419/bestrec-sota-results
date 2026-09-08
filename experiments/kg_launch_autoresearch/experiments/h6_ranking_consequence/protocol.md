# H6 Protocol: Does Transaction-Time KG Drift Change Rankings?

Status: locked before any click-label aggregation or outcome computation

Phase-A run: `coverage_run_001`

Classification: confirmatory label-blind feasibility gate

Date locked: 2026-08-07

## Claim under test

Holding news, entity annotations, user histories, candidates, and the scoring
rule fixed, does replacing the Wikidata fact set observable at the final MIND
development timestamp with a present snapshot materially change a
deterministic knowledge-aware ranking?

This POC isolates Wikidata **transaction-time** censoring. It is not a full
bitemporal test: H5 did not reconstruct fact-level valid-time intervals or
qualifiers. Its single end-of-day cutoff is also conservative for impressions
earlier on 2019-11-15. A positive POC justifies per-impression replay and real
KG recommender experiments; it is not publication evidence by itself.

## Immutable inputs

- MIND-small development `news.tsv`, SHA-256
  `E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822`.
- MIND-small development `behaviors.tsv`, SHA-256
  `B6C460E33B1A8693252DED6E626DA7D3CCF78920EEA2EC11889020BB7D8443EF`.
- H5 `run_003/facts.jsonl`, SHA-256
  `13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D`.
- H5 `run_003/entities.csv`, SHA-256
  `45B83B0AFCB6C1348080984B1373CE50912219DFE247F48E97F7FB09009595ED`.
- MIND `relation_embedding.vec`, used only as a frozen relation-ID vocabulary,
  SHA-256
  `D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A`.
- Cutoff: `2019-11-15T23:58:03Z`.
- H5 top-50 QID sample and confidence threshold `0.90`, unchanged.

The phase-A runner must verify every hash and reproduce 42,416 news rows,
73,152 behavior rows, 50 distinct sampled QIDs, and 1,091 distinct relation
IDs. It may not call Wikidata or expand the H5 sample.

## Frozen graph views

For sampled anchor QID `q` and snapshot `s` in `{historical,current}`, let
`F_s(q)` be the H5 `property|Qtarget` fact set after retaining only properties
present in MIND's frozen relation-ID vocabulary. This click-label-free policy
matches the relation family supplied for MIND KG models and avoids selecting
relations by outcome effect.

The following conservative metadata/navigation blocklist is frozen for a
secondary sensitivity analysis only:

`P1343, P1424, P5008, P6104, P7867, P8744, P9241, P2354, P8402, P10280, P1889`.

It may not replace the primary vocabulary result. A second robustness analysis
removes anchors `Q30` and `Q22686`; neither robustness result controls the
phase-A gate.

## Frozen news and cohort construction

1. Parse title and abstract annotations exactly as in H5.
2. Retain valid QIDs with confidence at least `0.90`, once per news row.
3. For the graph scorer, retain only QIDs in the fixed H5 top-50 anchor set.
4. For each impression, use at most the final 50 articles in its supplied
   click history. No click from any impression is added to a history.
5. A structural impression is eligible when it has at least two unique,
   known candidate news IDs and at least one retained history article with a
   top-50 anchor. All supplied candidates are ranked; candidates without an
   anchor receive graph score zero.

Phase A may recover a candidate news ID only by validating a token against
`^N[0-9]+-[01]$` and discarding everything after the final hyphen. It must
never store, count, branch on, or output the suffix. Cohort membership cannot
depend on whether any candidate is clicked.

Duplicate candidate IDs, unknown history/candidate news IDs, malformed tokens,
nonfinite scores, input-hash mismatch, or cohort nondeterminism invalidate the
run rather than silently dropping rows.

## Primary parameter-free shared-fact kernel

The coordinate space is the union of allowed `property|Qtarget` signatures.
For snapshot `s`, anchor `q` has vector

`e_s(q)[f] = 1 / sqrt(|F_s(q)|)` if `f` is in `F_s(q)`, else `0`.

Thus every nonempty anchor vector has unit L2 norm and high-degree entities do
not receive greater total mass merely because they have more statements.

For news `n`, sum the vectors of its retained anchors and L2-normalize the
result to obtain `v_s(n)`. A news row without a retained anchor has the zero
vector. For an eligible impression, sum `v_s(h)` over the retained last-50
history articles and L2-normalize to obtain `u_s`. Candidate score is

`score_s(u,n) = dot(u_s, v_s(n))`.

All entity, news, and user vectors are sparse. Entity and news vectors must be
cached so runtime is linear in observed sparse coordinates rather than in the
full entity-by-fact universe.

Ties use ascending hexadecimal SHA-256 of
`20260807|impression_id|news_id`. File order and candidate order may not break
ties. Numerical equality uses absolute tolerance `1e-12`.

## Phase A: label-blind coverage gate

The phase-A executable contains no outcome-metric function. It writes an
immutable cohort manifest containing only impression IDs, user IDs, history
news IDs, candidate news IDs, and structural scores/ranks. The manifest hash
is the only cohort accepted by Phase B.

Report:

- eligible impressions and distinct users;
- candidate-level nonzero-score rates in each snapshot;
- score-vector-changed rate (`max_i |score_C-score_H| > 1e-12`);
- total-order-changed rate after the frozen tie rule;
- top-1-changed rate;
- top-`min(10,m)` set-changed rate;
- score-delta quantiles; and
- the two predeclared robustness analyses.

`PASS_COVERAGE_AND_OPEN_LABELS` requires all sanity checks plus:

1. at least 5,000 eligible impressions;
2. at least 2,000 distinct users;
3. score vectors change in at least 20 percent of eligible impressions; and
4. either total order changes in at least 5 percent or the top-10 set changes
   in at least 2 percent.

A valid miss is `KILL_H6_SHARED_FACT_DIRECTION`; click labels remain unopened
and no sample, scorer, relation policy, tolerance, or threshold may be tuned as
a rescue. A transport, parse, hash, or integrity failure is `INCONCLUSIVE`.

## Phase B: held-fixed outcome test

Phase B is forbidden unless Phase A passes and its result is committed. It
must consume the exact committed cohort-manifest hash, then parse the suffixes
of the already fixed candidate tokens. No post-label filtering is allowed.

Primary outcome is impression-mean nDCG@10. Secondary outcomes are nDCG@5,
MRR, impression AUC on impressions containing both classes, clicked-versus-
unclicked pair accuracy, and the same metrics on the phase-A rank-affected
subset. Impressions with zero positives receive MRR and nDCG zero and are
counted explicitly.

Required fixed comparisons:

1. historical shared-fact kernel;
2. current shared-fact kernel;
3. entity-only kernel using one-hot annotated QIDs with identical aggregation;
4. MIND-supplied TransE entity vectors as a provenance-unknown diagnostic;
5. 100 relation-stratified matched null graphs.

For null replicate `b`, source anchor `q`, and property `p`, sample exactly the
historical count of targets without replacement from the union of historical
and current targets for `(q,p)`. Seeds are hashes of
`20260807|b|q|p`. This preserves source/property degrees and never uses labels.

Inference uses 5,000 paired user-cluster bootstrap replicates with seed
`20260807`; sampled users retain all their impressions, and identical resamples
serve every arm. Report percentile 95 percent confidence intervals.

Let `D_H = nDCG10_current - nDCG10_historical`, and let `D_R,b` be the
corresponding current-minus-null contrast. Advance only if all hold:

1. `|D_H| >= 0.005` and its paired user-cluster 95 percent interval excludes
   zero;
2. the pre-label rank-affected subset has the same sign;
3. `|D_H|` exceeds the 95th percentile of `|D_R,b|`, or current versus
   historical reverses ordering against entity-only with both differences at
   least `0.002`, confidence intervals excluding zero, and at most 5 of 100
   nulls reproducing the reversal;
4. the direction is unchanged under the frozen metadata blocklist and after
   removing anchors `Q30` and `Q22686`; and
5. every integrity and leakage check passes.

Otherwise the valid verdict is `KILL_H6_OUTCOME_DIRECTION`. No metric,
threshold, cohort, or graph-policy tuning is confirmatory after this lock.

## Interpretation and next scale

Neither this kernel, historical snapshot replay, nor temporal KG recommendation
is claimed as a new algorithm. The potentially novel contribution is a held-
fixed external-KG transaction-time intervention with relation/degree-matched
null attribution. A positive POC must next replicate with per-impression
snapshots, at least two datasets/cutoffs, and at least three representative KG
recommenders before it can support a top-tier claim.

## Runtime and output safety

Phase A is a single PowerShell 5.1 process with no Python, BLAS,
multiprocessing, or worker threads. It precomputes sparse entity/news vectors,
streams behaviors once, writes results atomically only after all checks, and
refuses to overwrite a run. Standard output and error are captured separately
by a hidden launcher.
