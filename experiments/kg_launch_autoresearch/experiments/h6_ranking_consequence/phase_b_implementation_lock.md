# H6 Phase-B Held-Fixed Outcome Implementation Lock

Status: prospective; implementation complete but neither synthetic self-test nor real labels have been executed

Date locked: 2026-08-07

## Authorization and immutable cohort

Phase B is forbidden unless the launcher verifies the exact Phase-A result commit
`b1f247abf3185a2eaec8588b358c488af8f78342`, result SHA-256
`B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF`,
completion SHA-256
`AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06`,
and cohort manifest SHA-256
`522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5`
(224,785,295 bytes). The real mode additionally requires the literal confirmation
token encoded in the safe launcher. The manifest and `behaviors.tsv` are consumed
in lockstep. A label suffix is decoded only after the impression, user, final-50
history, and complete lexicographically ordered candidate-ID set exactly match the
next committed manifest row. There is no post-label filtering.

Expected dimensions are 64,443 impressions, 43,374 users, 2,422,258 candidates,
and 35,445 primary rank-affected impressions. The affected subset is exactly the
set for which any primary historical rank differs from its current rank in the
committed Phase-A manifest.

## Fixed arms and aggregation

Every arm uses the exact Phase-A top-50 anchor universe. An annotation is retained
once per news row across title and abstract when its QID is in that universe and
its finite confidence is at least 0.90.

1. Historical/current shared-fact arms use the committed Phase-A scores, after a
   mandatory independent pattern-engine reconstruction matches every score within
   absolute `1e-12` and every rank exactly.
2. Entity-only uses an identity Gram matrix on the same top-50 anchors. It applies
   the frozen news-sum L2 normalization and history-sum L2 normalization.
3. MIND TransE uses the supplied raw `entity_embedding.vec` rows for those same
   anchors, then only the frozen news-sum and history-sum L2 normalizations. It is
   diagnostic and secondary-only. All 50 anchors are present. Read-only validation
   found raw row norms 0.4208201748-0.9967149145 (mean 0.7280099525); per-row
   normalization was explicitly rejected as an unplanned material transform.
   The file has 22,893 unique 100-dimensional rows and SHA-256
   `F1A0818A7C0136DD94F22AC003841C6DCCBAC2287C668B35402BB436EB400FB9`.
4. The two robustness comparisons retain the locked metadata blocklist and the
   removal of `Q30` and `Q22686` exactly as Phase A.

The optimized engine maps 42,416 news rows to 812 unique top-50 anchor-incidence
patterns. For each graph it computes normalized pattern similarities once. Each
impression stores a sparse vector of history-pattern counts and scores only its
distinct candidate patterns using

`score(t) = c^T S[:,t] / sqrt(c^T S c)`.

Candidates sharing a pattern inherit the same score. This is algebraically exact;
the committed-score/rank parity check is a hard integrity gate, not a diagnostic.

With `A=50` anchors, `P=812` patterns, per-impression distinct history and
candidate-pattern counts `h_i,c_i`, and a null batch of `B=10`, graph work is
`O(B(P^2 A + sum_i(h_i^2+h_i c_i)))`, followed by metric work over the fixed
candidate lists. The label-blind audit found mean `h_i=6.81` (max 29) and mean
`c_i=7.64` (max 52), versus 26.25 history articles and 37.59 candidates, so the
kernel never performs candidate-by-50 scoring. Peak scientific storage is the
`100 x 64,443 x 7` float64 null sufficient-statistic tensor (about 361 MB), not
candidate scores for 100 graphs.

## Metrics

The primary estimate is the impression mean nDCG@10. nDCG@5 and MRR also average
over every fixed impression; an impression with zero positives contributes zero
and is counted. Their total order uses the Phase-A first-score-anchored absolute
`1e-12` tolerance groups, then ascending SHA-256 of
`20260807|impression_id|news_id`.

Impression AUC is the mean of per-impression pairwise AUC over impressions with
both classes. A positive-negative pair receives one when the positive's tolerance
group is better, one half when both scores occupy the same frozen tolerance group,
and zero otherwise. Clicked-versus-unclicked pair accuracy is micro accuracy over
all positive-negative pairs under the frozen SHA-expanded deterministic total
rank. The report separately gives the fraction of all eligible pairs whose order
was resolved only inside a tolerance group by the SHA tie rule. This distinction
prevents AUC and pair accuracy from collapsing to the same statistic.

All fixed-arm metrics are reported on the full and rank-affected cohorts. All 100
null arms retain point values for every metric on both cohorts.

## Matched nulls

Replicates are indexed `b=0,...,99`. For every source anchor `q` and relation `p`,
the sampler selects exactly the historical number of unique targets from the
historical/current union without replacement. Its stratum seed is the 32-byte
SHA-256 digest of `20260807|b|q|p`; targets are ordered by
`SHA256(seed_digest || "|" || target)`, with target text only as a digest-collision
tie-break, and the first required count is retained. This version-independent
hash-priority sampler preserves every source/property degree and never reads a
label.

## Inference and exact gates

The bootstrap uses `numpy.random.Generator(PCG64(20260807))` directly-not a hash
of that integer. Each of 5,000 replicates samples the 43,374 users with replacement
and retains all impressions of each draw. The identical draw matrix serves every
arm. All fixed-arm metrics receive percentile 95% intervals on both scopes. Every
null arm receives an nDCG@10 interval on the full cohort. Secondary null intervals
are prospectively omitted; their point estimates remain retained.

Let `D_H = nDCG10_current - nDCG10_historical`. Advance to replication only when:

1. `|D_H| >= 0.005` and its paired user-cluster percentile interval excludes zero;
2. the rank-affected `D_H` has the same nonzero sign;
3. `|D_H|` strictly exceeds the linearly interpolated 95th percentile of the 100
   absolute `current-null_b` point contrasts, or current and historical lie on
   opposite sides of entity-only, each gap has magnitude at least 0.002 and a
   paired interval excluding zero, and at most five nulls lie opposite current
   relative to entity-only. A null reproduces that reversal whenever
   `(C-E)*(N_b-E)<0`, with no null-side magnitude or CI exemption;
4. metadata-blocklist and removed-anchor current-minus-historical effects have the
   same nonzero sign as primary; and
5. all integrity/leakage checks pass.

The pass verdict is `ADVANCE_H6_TO_REPLICATION`; the valid miss is
`KILL_H6_OUTCOME_DIRECTION`. TransE and secondary metrics never control a gate.

## Windows execution and artifacts

The separate launcher defaults to synthetic `SelfTest`; only explicit `Run` plus
the exact confirmation token can open labels. It uses the bound base CPython image
directly with `-B -u`, retains the workspace venv via `__PYVENV_LAUNCHER__`, fixes
`PYTHONHASHSEED=0`, all six numerical thread variables to one, and CUDA to `-1`.
It holds disjoint share-none outer locks, uses an exact child-start/launcher-ack PID
handshake, persistent stdout/stderr, fresh async ledgers, an inner computation
lock, no-overwrite publication, exact replay, raw-array gate recomputation, and a
deep verifier. A completion marker is written only after every child exits, all
stderr/async ledgers are empty, both locks are released, and all hashes match; it
is the last filesystem mutation.

Bound implementation hashes are filled only after final static audit:

Runner-SHA256: `34222A71AE69C699F8CC9F72A00B25C0DA17941AEEC452EC3B229D986824958D`

Launcher-SHA256: `3D982668C2563B1062191C713DC313840F10E09F8102DE27E2B1ABDD1DE5CEA3`
- protocol: `53EAE6D5D19982DD5E6926F563A6D327A5A1AF47DFC5CF58DA4D54D1D61DB0A4`
- workspace venv launcher: `BAD34B1F39DAD6A375E594AAF006FE84CD96A7AE46F6F2FA84C0536003234AC9`
- base CPython: `4F461F0C0DE64E82EB54FBCED0FD1D678D79D34EDA38660B07781E2BBA8064D6`
- `pyvenv.cfg`: `A59AE8BCAFF3472F99A259F89DFF2BE70AB8674AADEB5B26D574A237A7FF2426`

No Phase-B candidate label, aggregate outcome, synthetic Python self-test, or real
Python process was opened or executed while preparing this lock.
