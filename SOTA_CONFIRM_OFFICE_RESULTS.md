
## STATS + P1 PREDICTION (recorded BEFORE any training run)

- splits sha256: train `95d3db37ab29157c...` valid `a0bd9331846c56e0...` test `92a9a602dd6fa73c...`
- full hashes: train 95d3db37ab29157c4e6922270a282f72c43c3c4ccd01cd95385aa852d1469c58 / valid a0bd9331846c56e005d13911f785fcf79938284bb81d04dd72a1b9bb75ca8876 / test 92a9a602dd6fa73c3271ed69d37da5c7e8c63ecb1a928ab59c5085af4188c1ed
- text cache sha256: MISSING
- n interactions: train 1,354,262 / valid 223,308 / test 223,308 (total 1,800,878); n_users(test rows) = 223,308; n_items(train) = 77,225
- **U = mean distinct users/item (TRAIN) = 17.537**
- **P1 mechanical application: PREDICT tail Delta ~ 0 / null (VG/Beauty-like regime)** (rule frozen in SOTA_CONFIRM_PREREG_OFFICE.md; reference points MI 2.34 / VG 3.70 / Beauty 3.51)

### CORRECTION 2026-07-11 — U-definition inconsistency in the stats tool (disclosed, not papered over)

The prereg's P1 text defines U as "mean distinct-users-per-item," and the stats tool computed
exactly that from train interactions (U = 17.537). However, the prereg's own REFERENCE POINTS
(MI 2.34 / VG 3.70 / Beauty 3.51) are unambiguously **n_users/n_items ratios** — the campaign's
original connectivity metric — making the rule internally inconsistent as written. Under the
reference-consistent formula, Office = 223,308 / 77,225 = **2.89**, which falls in the
pre-declared **VOID zone [2.5, 3.0)**. Both readings agree on the operative point (NO tail win
is predicted for Office); the discrepancy changes only whether P1 is scored as "predicted null"
(tool's literal formula) or "VOID/unscored" (reference-consistent formula). Per the
strictest-interpretation principle, **P1 for Office is scored as VOID** — the out-of-sample
prediction test remains decided by the MI/VG/Beauty triple plus any future category falling
OUTSIDE the ambiguous zone. The tail contrast is still run and reported descriptively.
Also recorded: the text-encode step initially failed (missing Office metadata mapping in
`run_5core_benchmark.py`; fixed and re-run), so the k16/k8 gate arms execute after the ID-only
arm rather than before it — arm ORDER carries no significance (config and seeds unchanged).
