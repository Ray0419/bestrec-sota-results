# Frozen preregistration: official WEARec current equal-evaluation comparator

Protocol identifier: `PREREG_WEAREC_BASELINE_V1`

Status at freeze: the two validation-only tuning runs, eight assessment runs,
assessment checkpoints, TEST seals, TEST endpoints, per-user TEST sidecars, and
adjudication do not exist. The already outcome-known split and existing full-
model results do exist. A pre-freeze transductive catalog identity map was made
from the three fixed split files because 12 TEST items do not occur in
TRAIN+VALID. It contains item identities only, is private, and is hash-bound by
`_bestrec_run/wearec_baseline_v1_catalog_manifest.json`; no endpoint value was
computed while making it.

This is a prospectively frozen execution on an outcome-known dataset by the
same investigators. It is not independent confirmation, a new held-out-dataset
test, or a state-of-the-art claim.

## Question and contribution

Where does the official 2026 WEARec system fall when it is trained on this
paper's exact AR2023 Video_Games leave-last-two-out split and evaluated with the
same full-catalog history mask and tie rule as the paper's models?

The phase closes one specific audit gap: the paper currently discusses recent
frequency-domain recommenders but does not execute a current method under its
own protocol. It does not test WEARec on its authors' datasets, reproduce the
paper's published table, or establish broad superiority over WEARec.

## Frozen upstream identity and adapter boundary

- Official repository: `https://github.com/xhy963319431/WEARec.git`.
- Commit: `2087335339b1ead87da6e066ce14e2d33880a95e`.
- The source files imported at runtime and all four SHA-256 identities are
  frozen in `_bestrec_run/wearec_baseline_v1_common.py` and verified before
  every run. Tracked upstream files must be clean; runtime `__pycache__` files
  are ignored and the imported source files are verified byte-for-byte.
- The official `WEARecModel`, parameter initialization, prefix construction,
  full-softmax loss, Adam optimizer, maximum length 50, 64-dimensional hidden
  state, two layers, 200-epoch ceiling, and patience 10 are retained.
- The adapter replaces evaluation only. The official evaluator masks prior
  items by assigning score zero and obtains top-k with `argpartition`, which is
  not candidate- or tie-equivalent to this paper. The shared adapter instead
  removes padding, masks the complete history with negative infinity, and uses
  `rank0 = count(candidate_score > target_score)`, exactly matching the paper's
  evaluator. This difference is disclosed whenever the result is reported.
- The adapter does not copy or modify upstream source. The repository has no
  license file, so the release distributes only acquisition/verification and
  adapter code, not WEARec source.

## Frozen data, candidates, and TEST custody

- Data: repository-fixed Amazon Reviews 2023 `Video_Games` 5-core LLOO CSVs.
- Split SHA-256 identities:
  - TRAIN `536866c7b3cb21ff4a1c2139ecb1e393c2ea468c4efe63ff1cfde51b0bcaa8d3`;
  - VALID `b70d195ab3b9f76082854671e0e6a94c444302db6169d4074f112695d1467711`;
  - TEST `5a21bbcb5106d48cca21e90bbb6c417e1b95ac406321cd300c7800759dbaa496`.
- Population: 94,762 users, 25612 catalog items, one VALID and one TEST target
  per user. Item zero is reserved for WEARec padding and is never a candidate.
- Training reads TRAIN and VALID only. The private pre-freeze catalog map lets
  the trainer allocate rows for all 25612 items without reading TEST user-target
  associations. The 12 test-only item rows therefore remain randomly
  initialized, as they do in the paper's transductive catalog construction.
- VALID input is the last 50 TRAIN items and the complete TRAIN history is
  masked. TEST input is the last 50 TRAIN+VALID items and the complete
  TRAIN+VALID history is masked.
- No TEST CSV byte may be opened by training. All eight selected-preset
  checkpoints must exist before any TEST evaluation. Each TEST access creates
  an exclusive irreversible `*.finaleval.started.json` seal; repeat access and
  overwrite are forbidden. The evaluator writes endpoint JSON and compressed
  per-user records atomically and prints no endpoint value. The committed
  adjudicator is the first authorized endpoint reader.

## Frozen validation-only selection and assessment seeds

Two configurations copied exactly from official Amazon-domain checkpoint names
and logs compete on one tuning seed, `20262000`:

1. `official_sports`: learning rate 0.001, dropout 0.5, alpha 0.3, four heads;
2. `official_beauty`: learning rate 0.0005, dropout 0.5, alpha 0.2, eight heads.

Every other setting is identical. The preset with maximum best VALID NDCG@10
is selected; an exact tie selects the earlier listed preset. There is no TEST-
based tuning, rescue configuration, or per-seed selection.

The selected preset is trained from scratch on eight fresh optimizer seeds,
`20262001` through `20262008`. Model selection is the maximum shared-evaluator
VALID NDCG@10, checked every epoch, with strict improvement and patience 10.
Each seed is one experimental unit. Intervals quantify optimizer-seed scatter
on this fixed split, not user, split, dataset, or population sampling.

## Frozen endpoints and interpretation

Primary endpoint: full-catalog TEST NDCG@10 at each seed's best-VALID
checkpoint. HR@10, MRR, parameter count, best epoch, training time, TEST
evaluation time, and peak allocated CUDA memory are secondary/descriptive.

The adjudicator reports the WEARec eight-seed vector, mean, sample standard
deviation, and ordinary 95% t interval. It also reports the already-known
six-seed full-model reference vector from the exact files and hashes embedded
in the adjudicator and a descriptive Welch interval for WEARec minus that
reference. The two systems were not randomized as paired arms, did not receive
equal historical tuning budgets, and the reference was selected outcome-
visibly. The contrast is therefore descriptive and cannot be upgraded to a
confirmatory superiority claim regardless of p-value.

Frozen mechanical labels:

1. any missing, duplicate, overwritten, schema-invalid, hash-invalid, or
   arithmetically inconsistent artifact: `WEAREC-INTEGRITY-FAIL`;
2. descriptive Welch 95% interval entirely above zero:
   `WEAREC-ABOVE-EXISTING-REFERENCE`;
3. interval entirely below zero: `WEAREC-BELOW-EXISTING-REFERENCE`;
4. otherwise: `WEAREC-REFERENCE-OVERLAP`.

All labels receive equal prominence. “Equal-protocol” is narrowed to equal
split, target, candidate catalog, complete-history mask, cutoff, and tie rule;
it does not mean equal architecture, loss, training schedule, parameter count,
or tuning history.

## Frozen executable artifacts

- `_bestrec_run/acquire_wearec_baseline_v1.py`
- `_bestrec_run/prepare_wearec_baseline_v1.py`
- `_bestrec_run/wearec_baseline_v1_common.py`
- `_bestrec_run/test_wearec_baseline_v1.py`
- `_bestrec_run/run_wearec_baseline_v1.py`
- `_bestrec_run/eval_wearec_baseline_v1.py`
- `_bestrec_run/run_wearec_campaign_v1.py`
- `_bestrec_run/adjudicate_wearec_baseline_v1.py`
- `_bestrec_run/wearec_baseline_v1_catalog_manifest.json`

These files, this preregistration, the catalog manifest, and their release-
manifest hashes must be committed before either validation-only tuning run.
