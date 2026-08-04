# Video_Games Gap Repair Status

Generated from the isolated SOTA lab after the HSTU-BLaIR audit.

## Current Result After Fresh Replay

The frozen sparse full-catalog RRF candidate has now completed the five fresh
Video_Games replay seeds `20260801` through `20260805`. All `30/30` component
exports are present, all five sparse full-catalog replays are present, and the
confirmatory input checker reports `status="ready"`.

Five-seed sparse RRF replay mean:

- NDCG@10: `0.0764036708`
- HR@10: `0.1354530297`
- MRR: `0.0663171886`
- Records per seed: `94,762`
- Target mismatches per replay: `0`

The strongest frozen component comparator by five-seed mean is `dev10`, with
NDCG@10 `0.0719430616`. The candidate's mean NDCG@10 delta versus `dev10` is
`0.0044606092`. A paired per-user Wilcoxon test gives
`p=4.826731875130712e-140` after Holm correction, and the user/item/seed-fold
clustered bootstrap 95% CI for the candidate-minus-`dev10` delta is
`[0.0032460216, 0.0057788981]` with `2000` replicates.

Local gate artifact:
`_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/video_games_confirmatory_component_significance.json`

Strict local report:
`_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/STRICT_LOCAL_VIDEO_GAMES_GATE_REPORT.md`

Confirmatory provenance manifest:
`_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/video_games_confirmatory_provenance_manifest.json`

The provenance packager
`_bestrec_sota_lab/package_video_games_confirmatory.py` streams the five replay
JSONLs, recomputes metrics from ranks, verifies all summaries, hashes all
component and replay artifacts, and records the exact claim boundary. It
preserves the older raw `publication_grade=false` metadata instead of editing
completed outputs after the fact.

This passes the local Video_Games component-comparator gate, but it still does
not authorize a broad SOTA or publication claim. The result is Video_Games-only,
the comparator set is frozen component baselines rather than the complete
modern four-dataset baseline suite, and the existing publication protocol files
still require separate official-baseline evidence and clean publication-grade
metadata.

## Current Blocker

The broad Video_Games SOTA claim remains blocked.

| Reference | NDCG@10 | Status |
|---|---:|---|
| SASRec-SBERT 5-seed mean | 0.0550927 | internal baseline |
| HSTU-BLaIR local SM120 compatibility port, final full eval | 0.0738224 | stronger external comparator evidence |
| HSTU-BLaIR local SM120 compatibility port, best full eval | 0.0740335 | stronger external comparator evidence |
| HSTU-BLaIR upstream report | 0.0760 | strict single-run target |

The final-epoch HSTU-BLaIR SM120 checkpoint is now exported as per-user JSONL:

`_bestrec_sota_lab/runs/hstu_blair_eval_export_full_20260609_fg/warm_full_catalog_records_Video_Games_hstu_blair_sm120.jsonl`

Export metrics match TensorBoard: NDCG@10 `0.0738224142`, HR@10
`0.1323420780`, MRR `0.0654229978` over `94,762` records. This resolves the
"TensorBoard-only" audit weakness for the compatibility-port run, but it does
not remove the SM120/fbgemm caveat or make SASRec-SBERT SOTA.

The raw export's item ids are HSTU one-based ids and its user ids are HSTU
internal zero-based ids, not canonical BEST-Rec ids. Alignment audits found the
same `25,612` ASINs and `94,762` users in both systems, but the naive rule
`bestrec_item_id = hstu_item_id - 1` is false for `25,611` items and
`bestrec_user_id = hstu_user_id` is false for `94,761` users. The repair now
produces complete ASIN-based item and raw-user-based user maps:

`_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json`

`_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json`

The full HSTU export has also been converted to canonical BEST-Rec zero-based
user and item ids:

`_bestrec_sota_lab/runs/hstu_blair_eval_export_full_20260609_fg/warm_full_catalog_records_Video_Games_hstu_blair_sm120_bestrec_ids.jsonl`

Converted export SHA256:
`e43c128424b31ca4d3911bd0385cd357c17aa746445ade982b55dc4941204d26`.
Metrics are unchanged after user/item ID translation.

A full top-50 HSTU teacher export is also available for future distillation or
ensembling:

`_bestrec_sota_lab/runs/hstu_blair_eval_export_full_top50_20260609/warm_full_catalog_records_Video_Games_hstu_blair_sm120_bestrec_ids.jsonl`

Top-50 converted export SHA256:
`6e1c7360cd89b8e3c477a5d99c904fd9560395ac7f7147c4358c78d5d8c0be23`.
All `94,762` rows have translated user ids and teacher top-k item ids.

## Repair Work Started

A new isolated runner was added:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_video_games_gap_search.py --profile dev --run-id video_games_gap_search_dev_<date> --allow-negative
```

It launches `_bestrec_run/run_sasrec_sbert.py` read-only, writes outputs under
`_bestrec_sota_lab/runs/<run_id>/`, hashes code/data inputs, records exact
commands, and refuses to translate exploratory results into SOTA claims.

A separate SASRec-SBERT per-user exporter now exists because the historical
SASRec summaries did not contain records needed for paired strict review:

`_bestrec_sota_lab/export_sasrec_sbert_records.py`

Smoke run:
`_bestrec_sota_lab/runs/sasrec_sbert_export_smoke_20260609`.
It trained for one epoch, exported `128` test records with top-20 scores, saved
a checkpoint and environment metadata, and is explicitly marked
non-publication-grade. It does not consume HSTU teacher predictions during
training or model selection.

Full dev run:
`_bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_20260609`.
It trained for `50` epochs with full validation every `5` epochs, exported all
`94,762` test records with top-50 scores, and achieved NDCG@10
`0.0560087095`. This is still single-seed development evidence, not a SOTA
claim.

A paired HSTU/SASRec diagnostic now exists:
`_bestrec_sota_lab/runs/hstu_sasrec_pair_diagnostics_seed101_20260609`.
It found `2` same-user target mismatches between HSTU and BEST-Rec/SASRec and
excluded them. On the remaining `94,760` pairs, HSTU NDCG@10 is
`0.0738202133`, SASRec NDCG@10 is `0.0560098916`, and fixed top-50 RRF fusion
does not beat HSTU alone. The oracle best-of-two top-50 upper bound is
`0.0921520091`, so there is complementarity, but simple rank fusion is not an
honest repair.

Independent HSTU-vs-BEST-Rec target audit:
`_bestrec_sota_lab/runs/hstu_target_alignment_20260609/hstu_bestrec_target_alignment_audit.json`.
It confirms full `94,762`-user overlap and exactly `2` target mismatches:
BEST-Rec user `46968` raw user `AFZISTRYDPBLS4IDSBZTKRIGKDOQ` and BEST-Rec
user `94075` raw user `AHZ3JSFOITDDEXLQEA3WGAEKEFRA`.

HSTU split-protocol audit:
`_bestrec_sota_lab/runs/hstu_split_protocol_20260609/hstu_split_protocol_audit.json`.
It confirms HSTU `eval_dataset` targets match BEST-Rec test except the same
`2` mismatches, but HSTU `train_dataset` targets are effectively BEST-Rec
validation targets, with `6` target-order mismatches. This blocks
BEST-Rec-validation-selected HSTU/SASRec fusion using the current HSTU
checkpoint, because the checkpoint has already trained on those validation
labels. A fair repair needs a retrained HSTU-compatible model with a genuine
held-out validation split, or a predeclared fusion rule selected without HSTU
validation-query scores.

Executable gate:
`_bestrec_sota_lab/gate_hstu_fusion_protocol.py`.
The gate passes `--fusion-selection predeclared` with mismatch disclosure and
fails `--fusion-selection bestrec_validation`, as it should.

Strict HSTU-compatible sequence splits for a future fair retrain now exist:
`_bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609`.
They cover all `94,762` users. Validation checks passed: strict valid targets
match BEST-Rec validation exactly, strict test targets match BEST-Rec test
exactly, and strict train final labels are neither validation nor test targets.
These files do not retrofit the already-trained HSTU checkpoint; they are the
input contract for a clean retrain/select/test protocol.

Strict HSTU smoke training lane now exists:
`_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120.py` with wrapper
`_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh`.
Smoke run `_bestrec_sota_lab/runs/hstu_strict_smoke_20260609` trained one
batch, evaluated one validation batch and one test batch, saved a checkpoint,
and loaded it successfully. Valid NDCG@10 was `0.0168793627` over `128` smoke
records; test NDCG@10 was `0.0097114062` over `128` smoke records. This proves
the strict data flows through the HSTU/BLaIR stack, but it is not evidence of a
competitive model. The SM120/fbgemm autograd caveat remains.

Strict HSTU per-user export lane now exists:
`_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records.py` with wrapper
`_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh`.
Smoke export `_bestrec_sota_lab/runs/hstu_strict_export_smoke_test_20260609`
wrote `128` canonical BEST-Rec-id test records with top-50 teacher ids. JSONL
SHA256: `8849a30b86469b119da4ea8bfc4b8f9760ab72bf7d823f41af7f06f6617d3316`.
Recomputed metrics match the strict training smoke test summary exactly.

Strict HSTU one-epoch uncapped development run now exists:
`_bestrec_sota_lab/runs/hstu_strict_dev1_epoch1_20260609`. It trained all
`741` batches for one epoch on the strict train split and evaluated all
`94,762` validation and test users. Valid NDCG@10 was `0.0462342899`; test
NDCG@10 was `0.0421865168`. Checkpoint SHA256:
`135745effb26a486f3799e86592e1a165d2e779302fa9054167ff5c5e03235b3`.
This run validates the strict full-scale lane but is not competitive with
SASRec-SBERT (`0.0560087`) or the HSTU SM120 compatibility reference
(`0.0738224` final / `0.0740335` best full eval).

Full strict per-user exports from that one-epoch checkpoint:

- Valid JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev1_epoch1_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl`
- Valid SHA256:
  `0f143fea172062df6cef55ffc2a01c8d55684d86038305f7716faf7bb7cfc6e0`
- Test JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev1_epoch1_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl`
- Test SHA256:
  `167d22b1fa555d1b169746ea6e0852edca0f5478c1c600ad40cb49a49e56a95c`

An independent end-to-end JSONL check passed for both exports: `94,762`
unique users, canonical BEST-Rec user/item id ranges, top-50 teacher payloads,
summary-hash agreement, and exact metric recomputation. A provenance defect was
also found and fixed for future runs: the one-epoch checkpoint loads correctly
but does not include `best_epoch`; the strict trainer now writes `run_id`,
`checkpoint_role`, `best_epoch`, and `saved_at_utc` in future checkpoints.

Strict HSTU ten-epoch development rerun:
`_bestrec_sota_lab/runs/hstu_strict_dev2_epoch10_rerun_20260609`. The first
ten-epoch attempt reached validation epoch 10 but failed at checkpoint save
because the newly added `run_id` metadata was not yet wired into the parser.
The trainer/wrapper were fixed and the run was repeated under the rerun id.
The completed rerun trained all `741` batches for `10` epochs, selected epoch
`10`, and evaluated all `94,762` users. Valid NDCG@10 was `0.0678000212`;
test NDCG@10 was `0.0624013181`. Checkpoint SHA256:
`f03fca440aa6f0bbb76d582201ff9c20acb5541dafcab43762795df1c3b560a5`.

Full ten-epoch strict per-user exports:

- Valid JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev2_epoch10_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl`
- Valid SHA256:
  `4522f9572726b9fb6464bd3693353f24650c20ee1446f301d27a620809946ad6`
- Test JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev2_epoch10_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl`
- Test SHA256:
  `c0d1432b76e6906f725308d474b2affed04acd637be11929cc4c69cafa99da9e`

The ten-epoch exports pass the same independent JSONL audit as the one-epoch
exports. The result now beats the single-seed SASRec-SBERT dev export
(`0.0560087`) but remains below the HSTU SM120 compatibility reference
(`0.0738224` final / `0.0740335` best full eval) and below the upstream HSTU
report (`0.0760`).

Strict HSTU thirty-epoch development run:
`_bestrec_sota_lab/runs/hstu_strict_dev3_epoch30_20260609`. It trained all
`741` batches for `30` epochs, selected epoch `29`, and evaluated all `94,762`
users. Valid NDCG@10 was `0.0744242771`; test NDCG@10 was `0.0680150467`.
Checkpoint SHA256:
`68bef40bc0d4f0d64f5d19d496310c3963053324a21526ea96ef7a1e7db1d6a1`.

Full thirty-epoch strict per-user exports:

- Valid JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev3_epoch30_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl`
- Valid SHA256:
  `23e15f6ef4ca493219c1d1ac521aca0589e7b01a326acfedf5b03794e9d60d6b`
- Test JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev3_epoch30_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl`
- Test SHA256:
  `a3c4ecbe8a1b7eca681fad05f5b122a2f4078b4808b6232b58a3e493011bb9b5`

The thirty-epoch exports pass the independent JSONL audit. The result is the
strongest strict fair retrain so far, but it still trails the HSTU SM120 final
export by `0.0058073676` NDCG@10 and the upstream report by `0.0079849533`.

Strict HSTU sixty-epoch development run:
`_bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_direct_20260609`. A
background-launch attempt under `hstu_strict_dev4_epoch60_20260609` exited
without starting WSL training and left only launcher logs; the direct run is
the valid scored run. The direct run trained all `741` batches for `60` epochs,
selected epoch `55`, and evaluated all `94,762` users. Valid NDCG@10 was
`0.0768460863`; test NDCG@10 was `0.0696899323`. Checkpoint SHA256:
`3449ee07daefe30f6f46d587bd0acf8b0b9fbebd2c64b40e361505573cc5d2dc`.

Full sixty-epoch strict per-user exports:

- Valid JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl`
- Valid SHA256:
  `ebae162085b914afa498b466020823ad6b8ec011e023d920cc2623995a63f446`
- Test JSONL:
  `_bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl`
- Test SHA256:
  `27e693d7a1246643fcfb378b3e7d58185b79b9f298aa2e10fa07de9fb3df9c5f`

The sixty-epoch exports pass the independent JSONL audit. The result improves
over thirty epochs, but it still trails the HSTU SM120 final export by
`0.0041324819` NDCG@10 and the upstream report by `0.0063100677`.

Strict HSTU dropout/regularization repair sweep:

- `hstu_strict_dev5_epoch30_dropout03_20260609`: input-preprocessor dropout
  `0.3`, HSTU encoder linear dropout left at the original gin value `0.5`.
  It selected epoch `24`, reached valid NDCG@10 `0.0776297838`, and reached
  test NDCG@10 `0.0705495586`. Checkpoint SHA256:
  `e4559964827d8e46afdfcdd1b501939a27da7505e0071b8a180f6aa2435562c8`.
  Full exported records passed the independent JSONL audit:
  valid SHA256 `f848e836ebc57966480d6f3397659a150e08ae9c1b799c2269f2ce08e2b0252e`;
  test SHA256 `9a67a31967b2dca9abf7902fa2d1889c0756c21304166e8b52a3da2060b8b225`.
- `hstu_strict_dev6_epoch30_dropout01_20260609`: input dropout `0.1`, test
  NDCG@10 `0.0688288595`, worse than dropout `0.3`.
- `hstu_strict_dev7_epoch30_dropout03_linear03_20260609`: input dropout `0.3`
  and explicit `hstu_encoder.linear_dropout_rate=0.3`. It reached higher
  validation NDCG@10 `0.0782288699` but lower test NDCG@10 `0.0697376693`,
  so reducing encoder linear dropout is not the repair.
- `hstu_strict_dev8_epoch30_dropout03_wd1e4_20260609`: input dropout `0.3`
  with weight decay `1e-4`, test NDCG@10 `0.0701996145`, below the no-weight
  decay dropout `0.3` run.

The sweep also found a real experimental-control issue: earlier dropout runs
changed only the input preprocessor dropout, while the HSTU encoder linear
dropout remained pinned by gin at `0.5`. The strict trainer now supports
explicit `--hstu-linear-dropout-rate` and `--hstu-attn-dropout-rate` overrides
and records the effective gin config. The corrected matched-dropout run did
not improve held-out test performance.

## Runs Completed

| Run | Variant | NDCG@10 | Gap to 0.0760 | Verdict |
|---|---|---:|---:|---|
| `video_games_gap_search_smoke_20260609` | `smoke_sbert_d64_e1` | 0.0318128 | -0.0441872 | smoke only |
| `video_games_gap_search_dev1_20260609` | `sbert_d64_e50_dropout03_warmcos` | 0.0564861 | -0.0195139 | still blocked |
| `video_games_gap_search_dev2_d128_l2_20260609` | `sbert_d128_l2_h4_e60_dropout03` | 0.0539754 | -0.0220246 | worse than 64-d tuned |
| `video_games_gap_search_dev3_blair_mlp_20260609` | `blair_mlp_d128_l2_h4_e60` | 0.0526784 | -0.0233216 | worse than 64-d tuned |
| `sasrec_sbert_export_dev_seed101_20260609` | `sbert_d64_e50_dropout03_warmcos_export` | 0.0560087 | -0.0199913 | per-user export, still blocked |
| `hstu_strict_dev1_epoch1_20260609` | `strict_hstu_sm120_one_epoch` | 0.0421865 | -0.0338135 | strict full-scale lane, too undertrained |
| `hstu_strict_dev2_epoch10_rerun_20260609` | `strict_hstu_sm120_ten_epoch` | 0.0624013 | -0.0135987 | improves over SASRec dev, still below HSTU target |
| `hstu_strict_dev3_epoch30_20260609` | `strict_hstu_sm120_thirty_epoch` | 0.0680150 | -0.0079850 | strongest strict retrain, still below HSTU target |
| `hstu_strict_dev4_epoch60_direct_20260609` | `strict_hstu_sm120_sixty_epoch` | 0.0696899 | -0.0063101 | strongest strict retrain, still below HSTU target |
| `hstu_strict_dev5_epoch30_dropout03_20260609` | `strict_hstu_sm120_input_dropout03` | 0.0705496 | -0.0054504 | strongest strict retrain, still below HSTU target |
| `hstu_strict_dev6_epoch30_dropout01_20260609` | `strict_hstu_sm120_input_dropout01` | 0.0688289 | -0.0071711 | worse than dropout 0.3 |
| `hstu_strict_dev7_epoch30_dropout03_linear03_20260609` | `strict_hstu_sm120_input_dropout03_linear03` | 0.0697377 | -0.0062623 | higher validation, lower test |
| `hstu_strict_dev8_epoch30_dropout03_wd1e4_20260609` | `strict_hstu_sm120_input_dropout03_wd1e-4` | 0.0701996 | -0.0058004 | weight decay did not help |
| `hstu_strict_dev9_epoch60_dropout03_20260609` | `strict_hstu_sm120_input_dropout03_epoch60` | 0.0712181 | -0.0047819 | strongest strict retrain, still below HSTU target |

The 50-epoch 64-d SASRec-SBERT repair run improves modestly over the earlier
5-seed mean but does not change the publication decision. The first larger
plain d=128 run is worse, and the BLaIR+MLP branch is also worse, so simple
width scaling and text-adaptor swaps are not the fix. The first strict HSTU
retrain is useful as protocol repair, but after one epoch it is clearly
undertrained and cannot support a SOTA claim. The ten-epoch strict HSTU rerun
is stronger and beats the SASRec dev export, but it is still not a SOTA repair.
The thirty-epoch strict HSTU run is stronger again and validates that longer
training matters, but held-out test performance remains below HSTU-BLaIR. The
sixty-epoch run continues the improvement but still does not clear the
comparator, so the honest next step is not to claim SOTA; it is either more
HSTU hyperparameter tuning under the strict split or an architectural
distillation/ensemble that is selected without validation leakage.
The dropout sweep narrows the gap but still leaves the best strict test result
below the HSTU SM120 final export by `0.0032728556` NDCG@10 and below the
upstream report by `0.0054504414`.

Strict HSTU best-setting longer run:
`hstu_strict_dev9_epoch60_dropout03_20260609` extended the best dropout `0.3`
setting to `60` epochs. It selected epoch `57`, reached valid NDCG@10
`0.0782165733`, and reached test NDCG@10 `0.0712181223`. Checkpoint SHA256:
`58e21641c3d1dfd0819ed56d1dd0be3d19a0c753634ccb5d90a02bde978f3c31`.
Full exported records passed the independent JSONL audit:
valid SHA256 `61169fd2b5ef94bbde1c28f48a5b184f589253002e351758353a5d18cb38684f`;
test SHA256 `a624dc43b479770a945b483cfc77d22e3d67cdd473d270dae403cdf61f1478b5`.

This is now the strongest strict fair HSTU result in the lab. It still trails
the HSTU SM120 final export by `0.0026042919` NDCG@10, the HSTU SM120 best
full-eval score by `0.0028153392`, and the upstream report by `0.0047818777`.

Validation-safe dev9 HSTU/SASRec fusion diagnostic:

- SASRec validation and test records were re-exported from the existing
  `sasrec_sbert_best_val.pt` checkpoint with
  `_bestrec_sota_lab/export_sasrec_checkpoint_records.py`.
- The validation grid selected fixed top-50 RRF HSTU weight `0.85`, giving
  validation NDCG@10 `0.0799437627` versus dev9 HSTU alone `0.0782165733`.
- Applying the validation-selected `0.85` weight to the held-out test records
  gives test NDCG@10 `0.0727245678`.
- This beats dev9 HSTU alone (`0.0712181223`) but still trails the HSTU SM120
  final export by `0.0010978464` and the upstream HSTU report by
  `0.0032754322`.

Conclusion: the fusion is an honest development improvement, but it is still
not enough to support a SOTA claim. It should not be used as publication-grade
confirmatory evidence without a frozen rerun and without beating the HSTU
comparator.

Validation-trained artifact-level repair attempts:

1. `_bestrec_sota_lab/train_hstu_sasrec_union_reranker.py` trains
   candidate-level models over the HSTU/SASRec top-50 union using a split of
   validation users for train/selection and then evaluates once on test. The
   held-out validation selection still chose fixed RRF `hstu_weight=0.85`;
   test NDCG@10 was `0.0727276183`.
2. `_bestrec_sota_lab/train_hstu_sasrec_adaptive_fusion.py` trains user-level
   confidence/overlap models to adapt the RRF weight, again using only a
   validation-user train/selection split before one test evaluation. It selected
   `rf_classifier_anchor0.85_shrink0.25`, reached test NDCG@10
   `0.0729497028`, and improved fixed RRF by `0.0002220846`.

The adaptive fusion is now the strongest repair attempt in this lane, but it
still trails the local HSTU SM120 final export by `0.0008727114` NDCG@10 and
the upstream HSTU report by `0.0030502972`. SOTA remains blocked.

Item-prior calibration probe:
`_bestrec_sota_lab/runs/hstu_sasrec_item_prior_probe_20260609/item_prior_probe_summary.json`
tested validation-train item target/appearance priors over the same
HSTU/SASRec top-50 union. Held-out validation selected `beta=0.0`, leaving test
NDCG@10 at `0.0727245678`; this does not improve the fixed RRF or adaptive
fusion.

Content-aware repair attempts:

- `_bestrec_sota_lab/train_hstu_sasrec_content_reranker.py` adds BLaIR
  embedding/profile features to the candidate-level union reranker. It converts
  HSTU sequence histories through the recorded user/item maps before feature
  construction. Held-out validation still selected fixed RRF `hstu_weight=0.85`;
  test NDCG@10 was `0.0727276183`.
- `_bestrec_sota_lab/train_hstu_sasrec_content_adaptive_fusion.py` adds BLaIR
  profile summary features to the user-level adaptive fusion gate. It selected
  `rf_classifier_content_anchor0.85_shrink0.25`, reached test NDCG@10
  `0.0729566691`, and improved the previous adaptive gate by only
  `0.0000069663`.

The content-aware adaptive gate is now the strongest development result in this
lane, but it still trails the local HSTU SM120 final export by `0.0008657451`
NDCG@10 and the upstream HSTU report by `0.0030433309`. SOTA remains blocked.

Strict HSTU continued fine-tune:
`hstu_strict_dev10_resume_dev9_epoch40_lr3e4_dropout03_20260609` resumed the
dev9 best-valid checkpoint with a fresh AdamW optimizer at learning rate
`3e-4` for `40` additional epochs. The run is correctly labelled as a
continued fine-tune, not an uninterrupted training run. It selected additional
epoch `5`, reached validation NDCG@10 `0.0794430342`, and held-out test
NDCG@10 `0.0720202689`.

Full exported records passed the independent JSONL audit:
valid SHA256 `1ecbdeeae5e2b33f102013d3c341457c5e6b2d05703b03584a070c4ad2af74cf`;
test SHA256 `75c532db1a0fd423d113518248eb9f573e5d22ac4167852078dec480043e18f7`.
Validation-safe fixed RRF with SASRec selected HSTU weight `0.9` and reached
test NDCG@10 `0.0728192008`. This is below the content-aware adaptive best
`0.0729566691` and below the local HSTU SM120 final export by `0.0010032135`.
SOTA remains blocked.

Strict HSTU temperature probe:
`hstu_strict_dev11_epoch40_dropout03_temp003_20260609` kept the input dropout
`0.3` recipe but lowered sampled-softmax temperature to `0.03`. It selected
epoch `29`, reached validation NDCG@10 `0.0767377331`, and held-out test
NDCG@10 `0.0705038416`. This is worse than dev9, dev10, and the
content-aware adaptive best, so it is recorded as a negative repair attempt and
was not exported for fusion. SOTA remains blocked.

Strict HSTU width probe:
`hstu_strict_dev13_d96_l4h4_epoch60_dropout03_20260609` added lab-only
architecture overrides and ran a wider HSTU with `item_embedding_dim=96`,
`dv=dqk=24`, four blocks, four heads, dropout `0.3`, batch size `128`, and no
train/eval caps. It improved validation to NDCG@10 `0.0801036992` at epoch
`32`, but held-out test NDCG@10 was only `0.0717703219`. Validation-selected
fixed RRF with SASRec chose HSTU weight `0.8` and reached test NDCG@10
`0.0723664281`; histogram-gradient adaptive fusion selected the same fixed
weight and reached `0.0723638679`. These are below the current
content-aware adaptive best `0.0729566691` and below the local HSTU SM120 final
export `0.0738224142`. The wider-HSTU path is therefore a negative held-out
repair despite stronger validation. SOTA remains blocked.

Multi-checkpoint RRF fusion:
`train_multi_rrf_fusion.py` now supports validation-selected fixed RRF fusion
across arbitrary per-user record files, local weight refinement, fixed configs,
and validation-selected `rrf_k` sweeps. The strongest development result uses
sparse local seven-method refinement with `rrf_k=30` and weights
`dev13=0.45`, `dev10=0.20`, `dev5=0.20`, `dev4=0.05`, `dev9=0.05`, and
`sasrec=0.05`. It reaches validation NDCG@10 `0.0848013330` and held-out test
NDCG@10 `0.0765297735`.

This beats the previous content-aware adaptive best (`0.0729566691`), the
local HSTU SM120 final export (`0.0738224142`), and the upstream HSTU report
`0.0760` by `0.0005297735`. Because this was found through iterative
development after earlier held-out outcomes were known, it is still not a
publication/SOTA result. The original selected-fusion record is a
`multi_method_top50_union_history_masked` proxy, but an explicit sparse
full-catalog replay now exists for the frozen scoring function: listed
component top-50 items receive weighted RRF scores, all other unmasked catalog
items receive score `0.0`, strict sequence histories are masked, and ties are
broken by ascending BEST-Rec item id. That replay reaches NDCG@10
`0.0765303383`, HR@10 `0.1356239843`, and RR `0.0664394155` over `94,762`
records with zero target mismatches. It has been frozen only as a future
confirmatory candidate in
`_bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609.json`
with manifest SHA256
`a97888c17d7449c8bbfb5be145ad354e76fac64323f24e4edd4c49fffca0d6a6`.
The rejecting gate report is
`_bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609_gate.json`
with SHA256
`df26917cbbc7e0552c4a5f675c2231bf26cd53cba54036ab1290bc5bf5d1f0ec`.
The gate now rejects publication approval for two remaining blockers: the
candidate is explicitly development-only, and it has one development seed
rather than five fresh confirmatory seeds.
The frozen no-selection replay script
`_bestrec_sota_lab/run_frozen_multi_rrf_candidate.py` uses the recorded method
iteration order `dev4,dev5,dev9,dev10,dev13,sasrec` and exactly reproduces the
development metrics in
`_bestrec_sota_lab/runs/video_games_frozen_multi_rrf_replay_ordered_20260609`:
NDCG@10 `0.0765297735`, HR@10 `0.1356239843`, RR `0.0663678067`.
Replay script SHA256:
`cb90273579fe64cc5bfb893688cf3b3a4bd26217c11053e7dcd721dd439a61b1`.
Replay summary SHA256:
`9026f9d9eb3245b8d4cb0dbb839686b8e30292f2ab0bc7b3d87f9751251d1b9a`.
Replay records SHA256:
`01384902d405c2a9e95c6ffbb791daa93046d5e378ae7228e215b187f4dc0d00`.
Sparse full-catalog replay script SHA256:
`16a747e479ca12f107a191609a858a5f957f1f6ae841ec2c131f722e99172fcd`.
Sparse full-catalog replay summary SHA256:
`5a28de92092d8f9970761bcded74992e7753e3b7459ef4b0f5c10b512b9eeddc`.
Sparse full-catalog replay records SHA256:
`c539344eedc7383126e08aa0f503b5b3f82f7a782a29e685a0b09add07cd8bd7`.
The confirmatory input checker
`_bestrec_sota_lab/check_sparse_rrf_confirmatory_inputs.py` now reports that
candidate-specific fresh seeds `20260801` through `20260805` are ready:
`30` of `30` required component exports are present. Five sparse full-catalog
replays have been produced, one per seed, with `candidate_scope="full_catalog"`,
strict sequence history masking, `94,762` records per seed, and `0` target
mismatches per replay.

| Seed | Sparse RRF NDCG@10 | Strongest frozen component | Delta |
|---:|---:|---|---:|
| `20260801` | `0.0770383292` | `dev13` | `0.0044737751` |
| `20260802` | `0.0766969853` | `dev13` | `0.0040459207` |
| `20260803` | `0.0762134069` | `dev10` | `0.0035376646` |
| `20260804` | `0.0762357099` | `dev10` | `0.0048157662` |
| `20260805` | `0.0758339226` | `dev10` | `0.0033358961` |

Across the five fresh seeds, the strongest frozen component by mean NDCG@10 is
`dev10` (`0.0719430616`). The sparse RRF candidate mean is `0.0764036708`.
The paired user-level Wilcoxon test versus `dev10` is Holm-significant
(`p=4.826731875130712e-140`), and the clustered bootstrap 95% CI for the
candidate-minus-`dev10` NDCG@10 delta is
`[0.0032460216, 0.0057788981]`.

This is useful local Video_Games confirmatory evidence, not a publication-grade
broad SOTA result.

The earlier `20260701-20260705` seed set is retired for this candidate because
seed `20260701` was already used in development HSTU components. Checker
SHA256:
`c2c9319fe1ca8fa095d521f7cd425ff4b15bd73ded5c0aaa284a5a34652394b4`.
Input-check report SHA256:
`851cc785d800af99ad43f3010b9bfbbc2c79ed80bb9dd900a415045549736f0f`.
Job-status log SHA256:
`70922b1ce3b9ee5fedc6180e03fc5878a48e4e1697bd06e81e00cf134d81dea5`.
The job runner
`_bestrec_sota_lab/run_sparse_rrf_confirmatory_component_jobs.py` wrote a
30-job manifest and passed preflight for local inputs plus WSL HSTU environment.
Runner SHA256:
`d85c5100dfa8b92c0a2fc4b64a89360d06763fc96d7ec3cdc08a91a703bdbcd5`.
Job manifest SHA256:
`928835dec01f59fd7da76479b5e8f601b5e6725de0ab7e794cc8fc73ad9a8fc9`.
The queue-safe launcher
`_bestrec_sota_lab/run_sparse_rrf_confirmatory_queue.py` now plans next
runnable jobs, skips existing outputs, and refuses to launch while the status
log contains an unfinished `job_started` event. Its guarded execute smoke test
correctly refused to start a second job while `seed20260801_dev10` was active.
Queue helper SHA256:
`2bb8d5acdac5f5c81246e248bf2eebe8653da56359708c48ff537f08b4dd97bc`.
The latest queue plan and input checker now show no active component jobs and
no missing component files. SOTA remains blocked by scope and comparator
evidence: this local result covers Video_Games frozen components only, not the
complete four-dataset modern-baseline publication gate.

## Next Algorithmic Step

Do not spend more time on the same 64-d SASRec setting. The measured gap is too
large. The next repair sweep should prioritize:

- `sbert_d128_l3_h4_e60_dropout03` only if we need to complete the planned
  grid, but it is now lower priority.
- `sbert_mlp_d128_l2_h4_aug2_e60` only if we want one final SASRecText-adaptor
  check.
- a fresh confirmatory rerun of the frozen sparse local RRF candidate before
  any additional exploratory tuning. The development score now clears the
  upstream HSTU report numerically, so the main risk has shifted from raw score
  to honest evidence quality, fresh seeds/splits, and comparator statistics.
- avoid simple low-LR continuation from the dev9 checkpoint as the next main
  path; dev10 improved validation but did not improve the best held-out
  repair. A materially different HSTU training recipe or a stronger
  distillation source is needed.
- avoid further one-knob temperature lowering in the same HSTU recipe; dev11
  lowered temperature to `0.03` and regressed test NDCG@10 to `0.0705038416`.
- avoid relying on wider HSTU capacity alone; dev13 improved validation but
  still failed held-out test and validation-selected fusion.
- keep the frozen multi-checkpoint RRF candidate untouched for fresh
  confirmatory seeds/splits; do not claim the development score as SOTA,
  because it was discovered through iterative held-out feedback even though it
  is numerically above the upstream report. The sparse full-catalog replay
  removes the narrow scope ambiguity for this scoring function, but it does not
  repair the post-hoc development bias or incomplete confirmatory evidence.

If none of these exploratory variants clears the HSTU single-run target, the
paper must stay a strong-baseline or negative-result paper, not a SOTA paper.
