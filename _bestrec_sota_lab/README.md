# BEST-Rec SOTA Lab

This directory is intentionally isolated from the existing BEST-Rec pipeline.
It imports `_bestrec_run` modules read-only and writes all outputs under
`_bestrec_sota_lab/runs/<run_id>/`.

The active publication protocol is
`_bestrec_sota_lab/protocols/cold_sota_strict_v2.json`. The old
20260606-20260610 and 20260611-20260615 confirmatory runs are exploratory only
and now fail the strict gate. Active post-repair publication runs must use fresh
seeds `20260701,20260702,20260703,20260704,20260705` and
`mask_seen_in_topm=true`.

## Current Strict Status

The four-dataset cold-item package now passes the strict artifact audit. On
2026-06-10,
`audit_real_fair_reproducible.py` approved
`full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705` for the
full-catalog cold-item claim only. The approved scope is Beauty, Fashion,
Instruments, and Books under `cold_sota_strict_v2`, seeds
`20260701,20260702,20260703,20260704,20260705`, with no Books cap,
`candidate_scope="full_catalog"`, and `mask_seen_in_topm=true`.

This approval is not a broad warm-start or general recommender SOTA claim.
Warm baselines `ials`, `lightgcn`, and `multivae` are not complete in this lab
gate, and the candidate uses DropoutNet-derived evidence as a feature/rerank
anchor. The paper must state the claim as full-catalog cold-item ranking and
must compare directly against fixed and tuned official DropoutNet.

Raw per-user JSONL records remain too large for normal Git. The local
publication package now includes a generated verifier manifest at
`_bestrec_sota_lab/publication_artifacts/raw_record_release/raw_record_release_manifest.json`
covering 5,099,053,650 bytes and 23,357,327 rows. The records are published as
chunked GitHub Release assets at
https://github.com/Ray0419/bestrec-sota-results/releases/tag/bestrec-raw-records-v1
and are described by
`_bestrec_sota_lab/publication_artifacts/raw_record_release/raw_record_upload_parts_manifest.json`.

Use the final public-submission gate to prevent accidental submission unless
the local records, release assets, and manuscript provenance all agree:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/validate_public_submission.py --deep-verify-raw --verify-github-release
```

The frozen Video_Games sparse-RRF repair completed a separate five-seed replay
on seeds `20260801` through `20260805`. It beats the strongest frozen component
baseline (`dev10`) on mean NDCG@10, `0.0764036708` versus `0.0719430616`, with
Holm-significant paired Wilcoxon evidence and a positive user/item/seed-fold
clustered bootstrap CI. The local audit artifacts are:

- `_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/video_games_confirmatory_component_significance.json`
- `_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/STRICT_LOCAL_VIDEO_GAMES_GATE_REPORT.md`
- `_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/video_games_confirmatory_provenance_manifest.json`

This is not a broad publication/SOTA pass. It is Video_Games-only, compares
against frozen components rather than the complete modern baseline suite, and
does not satisfy the four-dataset publication gate.

## Development

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_research.py --datasets beauty,fashion,instruments,books --seeds 101,102,103
```

Smoke test:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_research.py --datasets beauty --seeds 101 --quick --run-id smoke_beauty --allow-negative
```

## Video_Games HSTU Gap Search

The broad sequential Video_Games claim is blocked by HSTU-BLaIR. Use this
isolated runner to test stronger SASRec-style variants without editing the
historical `_bestrec_run` script. Every run writes commands, input hashes,
result hashes, and a pass/fail gap report under `_bestrec_sota_lab/runs/`.

Smoke test:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_video_games_gap_search.py --profile smoke --run-id video_games_gap_search_smoke_20260609 --allow-negative
```

Development sweep:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_video_games_gap_search.py --profile dev --run-id video_games_gap_search_dev_<date> --allow-negative
```

Aggressive sweep:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_video_games_gap_search.py --profile aggressive --run-id video_games_gap_search_aggressive_<date> --allow-negative
```

If a variant beats the HSTU-BLaIR single-run target, it still cannot support a
SOTA claim until the exact config is frozen and rerun with fresh multi-seed
confirmatory per-user records.

## HSTU-BLaIR Per-User Export

The HSTU-BLaIR SM120 compatibility run can be converted from TensorBoard-only
evidence into per-user JSONL records without modifying upstream HSTU files:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_EXPORT_RUN_ID=hstu_blair_eval_export_full_20260609_fg HSTU_EXPORT_LIMIT_BATCHES=0 HSTU_EXPORT_TEACHER_TOP_K=0 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_eval_records_sm120_wsl.sh'
```

Completed export:

- Records: `94,762`
- NDCG@10: `0.0738224142`
- HR@10: `0.1323420780`
- MRR: `0.0654229978`
- JSONL: `_bestrec_sota_lab/runs/hstu_blair_eval_export_full_20260609_fg/warm_full_catalog_records_Video_Games_hstu_blair_sm120.jsonl`

The raw export uses HSTU one-based item ids and the upstream top-2500 rank
proxy. NDCG@10/HR@10 are exact for top-10 membership; MRR follows upstream's
miss rank proxy. This is still an SM120 compatibility-port result, not a
faithful pinned CUDA 12.1 reproduction.

HSTU and BEST-Rec contain the same Video_Games ASIN and raw-user sets, but
their item-id and user-id orders are different. The naive rule
`bestrec_item_id = hstu_item_id - 1` is false for `25,611` of `25,612` items,
and `bestrec_user_id = hstu_user_id` is false for `94,761` of `94,762` users.
Build the explicit ASIN-based item map and raw-user-based user map before using
HSTU exports for paired comparison, distillation, or ensembling:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/build_item_map_sm120_wsl.sh'
wsl -d Ubuntu-20.04 -- bash -lc 'bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/build_user_map_sm120_wsl.sh'
```

Current validated map and converted canonical export:

- Item map: `_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json`
- User map: `_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json`
- Converted JSONL: `_bestrec_sota_lab/runs/hstu_blair_eval_export_full_20260609_fg/warm_full_catalog_records_Video_Games_hstu_blair_sm120_bestrec_ids.jsonl`
- Converted SHA256: `e43c128424b31ca4d3911bd0385cd357c17aa746445ade982b55dc4941204d26`
- Top-50 teacher JSONL: `_bestrec_sota_lab/runs/hstu_blair_eval_export_full_top50_20260609/warm_full_catalog_records_Video_Games_hstu_blair_sm120_bestrec_ids.jsonl`
- Top-50 teacher SHA256: `6e1c7360cd89b8e3c477a5d99c904fd9560395ac7f7147c4358c78d5d8c0be23`

To convert another HSTU JSONL export:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/convert_hstu_export_to_bestrec_ids.py --input-jsonl <hstu_jsonl> --item-map _bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json --user-map _bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json --output-jsonl <bestrec_id_jsonl> --summary <summary_json>
```

## SASRec Per-User Export

Historical SASRec-SBERT runs only saved aggregate JSON summaries. For fair
paired diagnostics against HSTU-BLaIR, use the isolated exporter:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/export_sasrec_sbert_records.py --run-id sasrec_sbert_export_dev_<date> --category Video_Games --epochs 50 --eval-subsample 0 --export-limit-users 0 --export-top-k 50 --seed 101
```

Smoke test completed:

- Run: `_bestrec_sota_lab/runs/sasrec_sbert_export_smoke_20260609`
- Records: `128`
- Record SHA256: `b2ee18be544bb3ebf7f666573320b13586f6962ce38f833eb578517c13d1935b`
- Scope: one-epoch smoke only, not publication evidence.

The exporter writes a validation-selected checkpoint, per-user JSONL records,
input hashes, command metadata, and Python/torch/CUDA environment details. It
does not consume HSTU teacher predictions during training or model selection.

Full dev export completed:

- Run: `_bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_20260609`
- Records: `94,762`
- NDCG@10: `0.0560087095`
- Record SHA256: `4f77dd8e89b2b90283084be68db5d31a1e89783700a653aee4701c5a4c5f1c0e`
- Scope: single-seed development evidence, not publication evidence.

Paired HSTU/SASRec diagnostic:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/pair_hstu_sasrec_diagnostics.py --hstu-jsonl _bestrec_sota_lab/runs/hstu_blair_eval_export_full_top50_20260609/warm_full_catalog_records_Video_Games_hstu_blair_sm120_bestrec_ids.jsonl --sasrec-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl --out-dir _bestrec_sota_lab/runs/hstu_sasrec_pair_diagnostics_seed101_20260609 --allow-target-mismatch
```

The paired diagnostic excludes and discloses `2` users whose HSTU and BEST-Rec
test targets differ. On the remaining `94,760` pairs, HSTU NDCG@10 is
`0.0738202133`, SASRec NDCG@10 is `0.0560098916`, and fixed top-50 RRF fusion
does not beat HSTU alone. The oracle best-of-two top-50 upper bound is
`0.0921520091`, so complementarity exists, but naive rank fusion is not the
repair.

Independent target-alignment audit:
`_bestrec_sota_lab/runs/hstu_target_alignment_20260609/hstu_bestrec_target_alignment_audit.json`.
It confirms full `94,762`-user overlap and exactly `2` target mismatches:
raw users `AFZISTRYDPBLS4IDSBZTKRIGKDOQ` and
`AHZ3JSFOITDDEXLQEA3WGAEKEFRA`.

HSTU split-protocol audit:
`_bestrec_sota_lab/runs/hstu_split_protocol_20260609/hstu_split_protocol_audit.json`.
It confirms HSTU's `eval_dataset` target matches BEST-Rec test except the same
`2` mismatches, while HSTU's `train_dataset` target is effectively BEST-Rec
validation, with `6` target-order mismatches. Therefore, the current trained
HSTU checkpoint cannot be used for BEST-Rec-validation-selected fusion without
validation-label leakage. A publishable fusion repair requires either a newly
retrained HSTU-compatible model with a real held-out validation split, or a
fusion rule selected without using HSTU validation-query scores.

Executable fusion protocol gate:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/gate_hstu_fusion_protocol.py --fusion-selection bestrec_validation --out _bestrec_sota_lab/runs/hstu_split_protocol_20260609/fusion_gate_bestrec_validation.json
```

The `bestrec_validation` route correctly fails. The `predeclared` route passes
only as diagnostic/predeclared evidence and still requires disclosure of the two
HSTU-vs-BEST-Rec test-target mismatches.

Strict HSTU-compatible data for future retraining:
`_bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609`.

- Train CSV SHA256: `87dd7d2b480a19fe3be028dade83994f5cd282a8849a3e27dcf4830cb441a658`
- Valid CSV SHA256: `a49f7fb7587cd3a0ca471a684cc99a9437a66c01e437592f050a0580466fdfca`
- Test CSV SHA256: `5a51c1efd7f0aff2a45d1c7199ef7083f4c4755e404ed3b7283840516196d36d`

Validation checks passed: strict valid targets match BEST-Rec validation
exactly, strict test targets match BEST-Rec test exactly, and strict train
final labels are neither BEST-Rec validation nor test targets. These files are
not compatible with the already-trained HSTU checkpoint; they are for a future
retrain with a genuine held-out validation split.

Strict HSTU smoke training lane:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_smoke_20260609 HSTU_STRICT_EPOCHS=1 HSTU_STRICT_MAX_TRAIN_BATCHES=1 HSTU_STRICT_MAX_EVAL_BATCHES=1 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

Smoke run: `_bestrec_sota_lab/runs/hstu_strict_smoke_20260609`.
It trained one batch, evaluated one validation batch and one test batch, saved a
checkpoint, and loaded the checkpoint successfully. Valid NDCG@10 was
`0.0168793627` over `128` smoke records; test NDCG@10 was `0.0097114062` over
`128` smoke records. The checkpoint SHA256 is
`e0299f7df484ad5c02ba5d524bfe959388deb17ffdc9a75fc54f0d498db8f891`.
This is a plumbing smoke only. The SM120/fbgemm caveat remains.

Strict HSTU per-user export lane:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_export_smoke_test_20260609 HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=1 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

Smoke export: `_bestrec_sota_lab/runs/hstu_strict_export_smoke_test_20260609`.
It exported `128` canonical BEST-Rec-id test records with top-50 teacher ids.
The JSONL SHA256 is
`8849a30b86469b119da4ea8bfc4b8f9760ab72bf7d823f41af7f06f6617d3316`.
Recomputed NDCG@10/HR@10/MRR match the strict training smoke test summary.

Strict one-epoch uncapped HSTU development run:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev1_epoch1_20260609 HSTU_STRICT_EPOCHS=1 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

Completed run: `_bestrec_sota_lab/runs/hstu_strict_dev1_epoch1_20260609`.
It trained all `741` batches for one epoch and evaluated all `94,762`
validation/test users. Valid NDCG@10 was `0.0462342899`; test NDCG@10 was
`0.0421865168`. Checkpoint SHA256:
`135745effb26a486f3799e86592e1a165d2e779302fa9054167ff5c5e03235b3`.
This is a strict-lane development result only; after one epoch it is weaker
than SASRec-SBERT and the HSTU SM120 compatibility reference.

Export the one-epoch strict checkpoint to canonical per-user records:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev1_epoch1_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev1_epoch1_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev1_epoch1_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev1_epoch1_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

The regenerated exports pass an independent JSONL audit: `94,762` unique users,
canonical BEST-Rec id ranges, top-50 teacher payloads, summary-hash agreement,
and exact metric recomputation.

- Valid JSONL SHA256:
  `0f143fea172062df6cef55ffc2a01c8d55684d86038305f7716faf7bb7cfc6e0`
- Test JSONL SHA256:
  `167d22b1fa555d1b169746ea6e0852edca0f5478c1c600ad40cb49a49e56a95c`

The first one-epoch checkpoint lacks `best_epoch` metadata. The trainer has
been fixed so future strict checkpoints include `run_id`, `checkpoint_role`,
`best_epoch`, and `saved_at_utc`.

Strict ten-epoch HSTU development rerun:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev2_epoch10_rerun_20260609 HSTU_STRICT_EPOCHS=10 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

Completed run: `_bestrec_sota_lab/runs/hstu_strict_dev2_epoch10_rerun_20260609`.
It selected epoch `10`, reached valid NDCG@10 `0.0678000212`, and reached test
NDCG@10 `0.0624013181` over all `94,762` test users. Checkpoint SHA256:
`f03fca440aa6f0bbb76d582201ff9c20acb5541dafcab43762795df1c3b560a5`.
This improves over the single-seed SASRec-SBERT dev export but still trails the
HSTU SM120 compatibility reference and the upstream HSTU report.

Export the ten-epoch strict checkpoint:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev2_epoch10_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev2_epoch10_rerun_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev2_epoch10_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev2_epoch10_rerun_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

The ten-epoch exports pass the same independent JSONL audit as the one-epoch
exports.

- Valid JSONL SHA256:
  `4522f9572726b9fb6464bd3693353f24650c20ee1446f301d27a620809946ad6`
- Test JSONL SHA256:
  `c0d1432b76e6906f725308d474b2affed04acd637be11929cc4c69cafa99da9e`

Strict thirty-epoch HSTU development run:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev3_epoch30_20260609 HSTU_STRICT_EPOCHS=30 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

Completed run: `_bestrec_sota_lab/runs/hstu_strict_dev3_epoch30_20260609`.
It selected epoch `29`, reached valid NDCG@10 `0.0744242771`, and reached test
NDCG@10 `0.0680150467` over all `94,762` test users. Checkpoint SHA256:
`68bef40bc0d4f0d64f5d19d496310c3963053324a21526ea96ef7a1e7db1d6a1`.
This is the strongest strict fair HSTU retrain so far, but it still trails the
HSTU SM120 final export and upstream HSTU report.

Export the thirty-epoch strict checkpoint:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev3_epoch30_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev3_epoch30_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev3_epoch30_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev3_epoch30_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

The thirty-epoch exports pass the independent JSONL audit.

- Valid JSONL SHA256:
  `23e15f6ef4ca493219c1d1ac521aca0589e7b01a326acfedf5b03794e9d60d6b`
- Test JSONL SHA256:
  `a3c4ecbe8a1b7eca681fad05f5b122a2f4078b4808b6232b58a3e493011bb9b5`

Strict sixty-epoch HSTU development run:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev4_epoch60_direct_20260609 HSTU_STRICT_EPOCHS=60 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EVAL_EVERY=1 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

Completed run:
`_bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_direct_20260609`. It selected
epoch `55`, reached valid NDCG@10 `0.0768460863`, and reached test NDCG@10
`0.0696899323` over all `94,762` test users. Checkpoint SHA256:
`3449ee07daefe30f6f46d587bd0acf8b0b9fbebd2c64b40e361505573cc5d2dc`.
This is the strongest strict fair HSTU retrain so far, but it still trails the
HSTU SM120 final export and upstream HSTU report. A background-launch attempt
under `hstu_strict_dev4_epoch60_20260609` exited without starting WSL training;
the direct run above is the valid scored run.

Export the sixty-epoch strict checkpoint:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev4_epoch60_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_direct_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev4_epoch60_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_direct_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

The sixty-epoch exports pass the independent JSONL audit.

- Valid JSONL SHA256:
  `ebae162085b914afa498b466020823ad6b8ec011e023d920cc2623995a63f446`
- Test JSONL SHA256:
  `27e693d7a1246643fcfb378b3e7d58185b79b9f298aa2e10fa07de9fb3df9c5f`

Strict HSTU hyperparameter repair sweep:

The wrapper supports these lab-only environment overrides:

- `HSTU_STRICT_DROPOUT_RATE`: input preprocessor dropout.
- `HSTU_STRICT_HSTU_LINEAR_DROPOUT_RATE`: explicit
  `hstu_encoder.linear_dropout_rate` gin override.
- `HSTU_STRICT_HSTU_ATTN_DROPOUT_RATE`: explicit
  `hstu_encoder.attn_dropout_rate` gin override.
- `HSTU_STRICT_WEIGHT_DECAY`, `HSTU_STRICT_LEARNING_RATE`,
  `HSTU_STRICT_BATCH_SIZE`, and `HSTU_STRICT_EVAL_BATCH_SIZE`.

Best 30-epoch repair:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev5_epoch30_dropout03_20260609 HSTU_STRICT_EPOCHS=30 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EVAL_EVERY=1 HSTU_STRICT_DROPOUT_RATE=0.3 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

It selected epoch `24`, reached valid NDCG@10 `0.0776297838`, and reached test
NDCG@10 `0.0705495586` over all `94,762` users. Checkpoint SHA256:
`e4559964827d8e46afdfcdd1b501939a27da7505e0071b8a180f6aa2435562c8`.
It was the strongest 30-epoch strict fair run, but still below the HSTU SM120
final export and upstream HSTU report.

Export the dropout-0.3 checkpoint:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev5_dropout03_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev5_epoch30_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev5_dropout03_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev5_epoch30_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

The dropout-0.3 exports pass the independent JSONL audit.

- Valid JSONL SHA256:
  `f848e836ebc57966480d6f3397659a150e08ae9c1b799c2269f2ce08e2b0252e`
- Test JSONL SHA256:
  `9a67a31967b2dca9abf7902fa2d1889c0756c21304166e8b52a3da2060b8b225`

Best repair so far:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev9_epoch60_dropout03_20260609 HSTU_STRICT_EPOCHS=60 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EVAL_EVERY=1 HSTU_STRICT_DROPOUT_RATE=0.3 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

It selected epoch `57`, reached valid NDCG@10 `0.0782165733`, and reached test
NDCG@10 `0.0712181223` over all `94,762` users. Checkpoint SHA256:
`58e21641c3d1dfd0819ed56d1dd0be3d19a0c753634ccb5d90a02bde978f3c31`.
It is the strongest strict fair run so far, but still below the HSTU SM120
final export and upstream HSTU report.

Export the 60-epoch dropout-0.3 checkpoint:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev9_dropout03_epoch60_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev9_epoch60_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev9_dropout03_epoch60_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev9_epoch60_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

The 60-epoch dropout-0.3 exports pass the independent JSONL audit.

- Valid JSONL SHA256:
  `61169fd2b5ef94bbde1c28f48a5b184f589253002e351758353a5d18cb38684f`
- Test JSONL SHA256:
  `a624dc43b479770a945b483cfc77d22e3d67cdd473d270dae403cdf61f1478b5`

Validation-safe dev9 HSTU/SASRec fusion diagnostic:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/export_sasrec_checkpoint_records.py --checkpoint _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_20260609/sasrec_sbert_best_val.pt --run-id sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609 --export-split valid --export-limit-users 0 --export-top-k 50

uv --project _bestrec_run run python _bestrec_sota_lab/export_sasrec_checkpoint_records.py --checkpoint _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_20260609/sasrec_sbert_best_val.pt --run-id sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609 --export-split test --export-limit-users 0 --export-top-k 50

uv --project _bestrec_run run python _bestrec_sota_lab/pair_hstu_sasrec_diagnostics.py --hstu-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl --sasrec-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_valid.jsonl --out-dir _bestrec_sota_lab/runs/hstu_strict_dev9_sasrec_pair_valid_diagnostics_20260609 --posthoc-weights 0.0,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1.0

uv --project _bestrec_run run python _bestrec_sota_lab/pair_hstu_sasrec_diagnostics.py --hstu-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl --sasrec-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl --out-dir _bestrec_sota_lab/runs/hstu_strict_dev9_sasrec_pair_test_diagnostics_20260609 --posthoc-weights 0.0,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1.0
```

The validation-selected fixed top-50 RRF weight is `0.85`, with validation
NDCG@10 `0.0799437627` versus dev9 HSTU alone `0.0782165733`. Applying that
same validation-selected weight to test gives NDCG@10 `0.0727245678`, which is
better than dev9 HSTU alone (`0.0712181223`) but still below the local HSTU
final export by `0.0010978464` and below the upstream HSTU report by
`0.0032754322`. This is a useful development repair, not SOTA evidence.

Fusion artifact hashes:

- SASRec validation JSONL SHA256:
  `2faa718b846f6e7e0af9db543edeb807072fc48c0716f286c2d4bd7c60b77ad7`
- SASRec test JSONL SHA256:
  `4f77dd8e89b2b90283084be68db5d31a1e89783700a653aee4701c5a4c5f1c0e`
- Validation pair diagnostic SHA256:
  `fcf2b23646f042fe84c71bd2bd79276208d20d713a0ccf384f0baa3e791697d2`
- Test pair diagnostic SHA256:
  `65945aa5ade938bc0060d4458f2737c3f70ebbb7af11418d02ab492b30886964`

Validation-trained artifact-level repair attempts:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/train_hstu_sasrec_union_reranker.py --hstu-valid-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl --sasrec-valid-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_valid.jsonl --hstu-test-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl --sasrec-test-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl --out-dir _bestrec_sota_lab/runs/hstu_sasrec_union_ltr_dev1_20260609

uv --project _bestrec_run run python _bestrec_sota_lab/train_hstu_sasrec_adaptive_fusion.py --hstu-valid-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl --sasrec-valid-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_valid.jsonl --hstu-test-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl --sasrec-test-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl --out-dir _bestrec_sota_lab/runs/hstu_sasrec_adaptive_fusion_dev1_20260609
```

The candidate-level union reranker did not beat validation-selected fixed RRF:
its held-out validation selection chose `rrf_hstu_weight_0.85`, and the test
NDCG@10 was `0.0727276183`.

The user-level adaptive fusion did improve the fixed RRF. It selected
`rf_classifier_anchor0.85_shrink0.25` on held-out validation users, reached test
NDCG@10 `0.0729497028`, and improved fixed RRF by `0.0002220846`. It still
trails the local HSTU final export by `0.0008727114` and the upstream HSTU
report by `0.0030502972`. Therefore it is not SOTA evidence.

A validation-learned item-prior calibration probe was also run under
`_bestrec_sota_lab/runs/hstu_sasrec_item_prior_probe_20260609/`. Held-out
validation selected `beta=0.0`, so the item prior did not improve fixed RRF;
test NDCG@10 stayed at `0.0727245678`.

Content-aware repair attempts:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/train_hstu_sasrec_content_reranker.py --hstu-valid-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl --sasrec-valid-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_valid.jsonl --hstu-test-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl --sasrec-test-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl --valid-sequence-csv _bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609/sasrec_format_valid_strict.csv --test-sequence-csv _bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609/sasrec_format_test_strict.csv --item-map-json _bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json --user-map-json _bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json --blair-embedding-pt \\wsl.localhost\Ubuntu-20.04\home\ray\.bestrec_hstu_blair\HSTU-BLaIR\tmp\amzn23_game\item_text_embeddings_blair.pt --out-dir _bestrec_sota_lab/runs/hstu_sasrec_content_reranker_dev1_20260609

uv --project _bestrec_run run python _bestrec_sota_lab/train_hstu_sasrec_content_adaptive_fusion.py --hstu-valid-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl --sasrec-valid-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_valid.jsonl --hstu-test-jsonl _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl --sasrec-test-jsonl _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl --valid-sequence-csv _bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609/sasrec_format_valid_strict.csv --test-sequence-csv _bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609/sasrec_format_test_strict.csv --item-map-json _bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json --user-map-json _bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json --blair-embedding-pt \\wsl.localhost\Ubuntu-20.04\home\ray\.bestrec_hstu_blair\HSTU-BLaIR\tmp\amzn23_game\item_text_embeddings_blair.pt --out-dir _bestrec_sota_lab/runs/hstu_sasrec_content_adaptive_fusion_dev1_20260609
```

Both scripts translate HSTU sequence histories into BEST-Rec IDs using the
recorded user/item maps before computing BLaIR profile features. The direct
content reranker selected fixed RRF again and did not improve the result. The
content-aware adaptive gate selected `rf_classifier_content_anchor0.85_shrink0.25`
and reached test NDCG@10 `0.0729566691`, improving the prior adaptive gate by
only `0.0000069663`. It remains below the local HSTU final export by
`0.0008657451` and below the upstream report by `0.0030433309`.

Strict HSTU continued fine-tune:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev10_resume_dev9_epoch40_lr3e4_dropout03_20260609 HSTU_STRICT_RESUME_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev9_epoch60_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EPOCHS=40 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EVAL_EVERY=1 HSTU_STRICT_DROPOUT_RATE=0.3 HSTU_STRICT_LEARNING_RATE=0.0003 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

This run resumes the dev9 best-valid checkpoint with a fresh AdamW optimizer,
which is recorded as a continued fine-tune rather than an uninterrupted
training run. It selected additional epoch `5`, reached validation NDCG@10
`0.0794430342`, but held-out test NDCG@10 was only `0.0720202689`.

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev10_resume_export_valid_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev10_resume_dev9_epoch40_lr3e4_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=valid HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'

wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_EXPORT_RUN_ID=hstu_strict_dev10_resume_export_test_20260609 HSTU_STRICT_CHECKPOINT=/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_strict_dev10_resume_dev9_epoch40_lr3e4_dropout03_20260609/strict_hstu_best_valid.pt HSTU_STRICT_EXPORT_SPLIT=test HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EXPORT_TEACHER_TOP_K=50 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh'
```

Validation-safe fixed RRF with SASRec selected HSTU weight `0.9` and produced
test NDCG@10 `0.0728192008`. This is below the previous best content-aware
adaptive fusion (`0.0729566691`) and still below the local HSTU final export by
`0.0010032135`.

Strict HSTU temperature probe:

```powershell
wsl -d Ubuntu-20.04 -- bash -lc 'HSTU_STRICT_RUN_ID=hstu_strict_dev11_epoch40_dropout03_temp003_20260609 HSTU_STRICT_EPOCHS=40 HSTU_STRICT_MAX_TRAIN_BATCHES=0 HSTU_STRICT_MAX_EVAL_BATCHES=0 HSTU_STRICT_EVAL_EVERY=1 HSTU_STRICT_DROPOUT_RATE=0.3 HSTU_STRICT_TEMPERATURE=0.03 bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh'
```

This one-knob test lowered sampled-softmax temperature from the wrapper default
to `0.03` while keeping the dropout `0.3` repair setting. It selected epoch
`29`, reached validation NDCG@10 `0.0767377331`, and held-out test NDCG@10
`0.0705038416`. Because it is clearly worse than dev9, dev10, and the
content-aware adaptive fusion, it was not exported for fusion.

Strict HSTU width probes:

The first `d=128` launch
`hstu_strict_dev12_d128_l4h4_epoch60_dropout03_20260609` was terminated before
completion after the initial background launch exposed impractical epoch
runtime and non-flushed logging. The wrapper now exports `PYTHONUNBUFFERED=1`
and the trainer flushes epoch JSON lines.

```powershell
wsl -d Ubuntu-20.04 -- bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/launch_strict_hstu_dev13_d96_wsl.sh
```

`hstu_strict_dev13_d96_l4h4_epoch60_dropout03_20260609` used
`item_embedding_dim=96`, `hstu_encoder.dv=24`, `hstu_encoder.dqk=24`, four
blocks, four heads, dropout `0.3`, batch size `128`, and no train/eval caps.
It selected epoch `32`, reached validation NDCG@10 `0.0801036992`, but held-out
test NDCG@10 was only `0.0717703219`.

The dev13 exports passed the independent JSONL audit: valid/test/adaptive test
records each contain `94,762` unique users, all required schema fields, and
recomputed metrics matching the summaries. Validation-selected fixed RRF with
SASRec picked HSTU weight `0.8` and reached test NDCG@10 `0.0723664281`.
Histogram-gradient adaptive fusion selected the same fixed RRF weight and
reached test NDCG@10 `0.0723638679`. The full RF adaptive branch and the
content-aware histogram branch were terminated as computationally impractical
in this interactive lane after producing no artifacts. Dev13 is therefore a
useful validation improvement but a negative held-out repair attempt.

Multi-checkpoint RRF fusion:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/train_multi_rrf_fusion.py --valid-input dev9 _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl teacher_top_ids --valid-input dev10 _bestrec_sota_lab/runs/hstu_strict_dev10_resume_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl teacher_top_ids --valid-input dev13 _bestrec_sota_lab/runs/hstu_strict_dev13_d96_export_valid_20260609/warm_full_catalog_records_Video_Games_strict_hstu_valid.jsonl teacher_top_ids --valid-input sasrec _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_valid_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_valid.jsonl top_ids --test-input dev9 _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --test-input dev10 _bestrec_sota_lab/runs/hstu_strict_dev10_resume_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --test-input dev13 _bestrec_sota_lab/runs/hstu_strict_dev13_d96_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --test-input sasrec _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl top_ids --out-dir _bestrec_sota_lab/runs/hstu_dev9_dev10_dev13_sasrec_multi_rrf_fusion_20260609
```

The initial validation-selected multi-RRF fusion over dev9/dev10/dev13/SASRec
selected weights `dev9=0.3`, `dev10=0.3`, `dev13=0.3`, `sasrec=0.1`, reaching
test NDCG@10 `0.0756620168`. Adding older strict HSTU exports dev3/dev4/dev5
selected `dev5=0.25`, `dev10=0.25`, `dev13=0.5`, reaching test NDCG@10
`0.0758262901`. A fixed-weight RRF-k sweep over that three-checkpoint fusion
selected `rrf_k=30` and reached NDCG@10 `0.0759151509`.

The strongest development result now comes from sparse local seven-method RRF
refinement in
`_bestrec_sota_lab/runs/hstu_multi7_k30_sparse_local_refine_r005_20260609`.
It selected `rrf_k=30` with weights `dev13=0.45`, `dev10=0.20`,
`dev5=0.20`, `dev4=0.05`, `dev9=0.05`, and `sasrec=0.05`, reaching validation
NDCG@10 `0.0848013330` and held-out test NDCG@10 `0.0765297735`.

This beats the previous content-aware adaptive best by `0.0035731044`, the
local HSTU SM120 export by `0.0027073593`, and the upstream HSTU report
`0.0760` by `0.0005297735`. It is still not publication evidence: the result
was discovered through iterative development after prior held-out outcomes were
known. The original selected-fusion record is a
`multi_method_top50_union_history_masked` rerank proxy, but the frozen sparse
scoring function has now also been replayed against the full catalog with the
strict sequence history mask. The exact config is frozen only as a future
confirmatory candidate in
`_bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609.json`.
No SOTA/publication claim is allowed until this frozen recipe is rerun on fresh
confirmatory seeds/splits and passes the statistical gates.

Frozen-candidate gate:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/validate_frozen_video_games_candidate.py
```

The gate report
`_bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609_gate.json`
recomputes the streamed metrics and verifies the summary/test-record hashes,
then rejects publication approval for two hard blockers: the candidate is
explicitly development-only, and it has only one development seed instead of
five fresh confirmatory seeds. The sparse full-catalog replay is valid, so the
older scope blocker is no longer the active blocker for this frozen sparse
scoring function.

Frozen replay:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_frozen_multi_rrf_candidate.py --manifest _bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609.json --input dev4 _bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev5 _bestrec_sota_lab/runs/hstu_strict_dev5_dropout03_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev9 _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev10 _bestrec_sota_lab/runs/hstu_strict_dev10_resume_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev13 _bestrec_sota_lab/runs/hstu_strict_dev13_d96_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input sasrec _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl top_ids --out-dir _bestrec_sota_lab/runs/video_games_frozen_multi_rrf_replay_ordered_20260609 --dataset Video_Games --seed 20260609 --fold-id 0 --stage development_replay
```

The ordered replay uses method iteration order
`dev4,dev5,dev9,dev10,dev13,sasrec` and exactly reproduces the frozen
development metrics: NDCG@10 `0.0765297735`, HR@10 `0.1356239843`, and RR
`0.0663678067`.

Sparse full-catalog replay:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_sparse_rrf_full_catalog_replay.py --manifest _bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609.json --input dev4 _bestrec_sota_lab/runs/hstu_strict_dev4_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev5 _bestrec_sota_lab/runs/hstu_strict_dev5_dropout03_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev9 _bestrec_sota_lab/runs/hstu_strict_dev9_dropout03_epoch60_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev10 _bestrec_sota_lab/runs/hstu_strict_dev10_resume_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input dev13 _bestrec_sota_lab/runs/hstu_strict_dev13_d96_export_test_20260609/warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl teacher_top_ids --input sasrec _bestrec_sota_lab/runs/sasrec_sbert_export_dev_seed101_test_from_checkpoint_20260609/warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl top_ids --sequence-csv _bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609/sasrec_format_test_strict.csv --out-dir _bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_replay_20260609 --dataset Video_Games --seed 20260609 --fold-id 0 --split test
```

This replay defines every unlisted unmasked catalog item as score `0.0`, masks
the strict sequence history, and breaks ties by ascending BEST-Rec item id. It
produces `94,762` `candidate_scope="full_catalog"` records with no target
mismatches and metrics: NDCG@10 `0.0765303383`, HR@10 `0.1356239843`, RR
`0.0664394155`. It is still development-only.

Confirmatory input inventory:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/check_sparse_rrf_confirmatory_inputs.py
```

The inventory report
`_bestrec_sota_lab/frozen_candidates/video_games_sparse_rrf_confirmatory_input_check.json`
uses the candidate-specific fresh seeds
`20260801,20260802,20260803,20260804,20260805`. The previously listed
`20260701-20260705` seed set is retired for this sparse-RRF candidate because
seed `20260701` was already used in the development HSTU components. The
current report has `0` missing component files: all `30/30` component exports
exist, and all five sparse full-catalog replays are complete.

Five fresh replay folders:

- `_bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_confirmatory_seed20260801`
- `_bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_confirmatory_seed20260802`
- `_bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_confirmatory_seed20260803`
- `_bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_confirmatory_seed20260804`
- `_bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_confirmatory_seed20260805`

Replay metrics:

| Seed | NDCG@10 | HR@10 | MRR | Strongest component | Delta |
|---:|---:|---:|---:|---|---:|
| `20260801` | `0.0770383292` | `0.1361832802` | `0.0669132996` | `dev13` | `0.0044737751` |
| `20260802` | `0.0766969853` | `0.1358666976` | `0.0666409075` | `dev13` | `0.0040459207` |
| `20260803` | `0.0762134069` | `0.1352651907` | `0.0660623364` | `dev10` | `0.0035376646` |
| `20260804` | `0.0762357099` | `0.1351280049` | `0.0662150492` | `dev10` | `0.0048157662` |
| `20260805` | `0.0758339226` | `0.1348219751` | `0.0657543502` | `dev10` | `0.0033358961` |

Five-seed mean NDCG@10 is `0.0764036708`, versus `0.0719430616` for the
strongest frozen component baseline (`dev10`). The paired per-user Wilcoxon
test versus `dev10` is Holm-significant (`p=4.826731875130712e-140`), and the
user/item/seed-fold clustered bootstrap 95% CI for the NDCG@10 delta is
`[0.0032460216, 0.0057788981]` with `2000` replicates.

Detailed hashes and comparison statistics are in
`_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/video_games_confirmatory_component_significance.json`.
The provenance manifest
`_bestrec_sota_lab/runs/video_games_sparse_rrf_confirmatory_20260801_20260805_audit/video_games_confirmatory_provenance_manifest.json`
is the canonical record for this local evidence package; it verifies all replay
JSONLs and component artifacts without rewriting older raw outputs.

This passes a local Video_Games component-comparator gate, but it is not a
publication or broad SOTA pass.

Confirmatory component job manifest:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_sparse_rrf_confirmatory_component_jobs.py --preflight --seed 20260801 --component dev4
```

The job manifest
`_bestrec_sota_lab/frozen_candidates/video_games_sparse_rrf_confirmatory_jobs.json`
contains all `30` fresh-seed component jobs and passed preflight: local strict
sequence inputs exist and the WSL HSTU environment is reachable. The runner
does not execute a full sweep unless `--execute --seed <seed> --component <component>`
are provided together.

Artifact-level repair hashes:

- Union LTR summary SHA256:
  `2fb31a5ebbb85ea52565653ce5f144407457a7ab2dad0359695404011570417a`
- Union LTR test records SHA256:
  `22d93dd41ae9da5fe365d71d65df5f443ce63c6ed5783b4e848f44f783d7fc71`
- Adaptive fusion summary SHA256:
  `d06ed8fc99a2275fa427fd8b3738d272b97cd02dca0c5ea8127e203a813c66cf`
- Adaptive fusion test records SHA256:
  `573a620edf8f9a741ca4a8227df74519246c553b0738e4579070933e6826cef4`
- Item-prior probe summary SHA256:
  `9e058729bd160e3ff5666dcab6f80947c6c809ba880aff934c5e30dd4a02e88e`
- Content reranker summary SHA256:
  `74b0e323375d64b3239a930248651fbff4870b01aea3ad97f84d01169229d2e1`
- Content reranker test records SHA256:
  `1ca126ea8e377f6fb919618869d1afd4c4b3eae7d2d7e70ad214bf669a2cbd52`
- Content adaptive fusion summary SHA256:
  `6a739d628fc21055e865b2d49598a91879c4d05cad609b203b9ec2649bf4e461`
- Content adaptive fusion test records SHA256:
  `e72c059dfa0337cdc4f487c8377a3f7d9afa911f76cf132e7d0b3cf612fc5d0a`
- Multi-seven sparse local RRF summary SHA256:
  `d6df46546a6180baf82941014ca057e64d31d31cee6d4314209ce258f4308298`
- Multi-seven sparse local RRF test records SHA256:
  `859171de2415c7331a526c64b33f20a94f068d5cd6fcee86ac9344f6d44f4635`
- Frozen Video_Games candidate manifest SHA256:
  `a97888c17d7449c8bbfb5be145ad354e76fac64323f24e4edd4c49fffca0d6a6`
- Frozen Video_Games gate report SHA256:
  `df26917cbbc7e0552c4a5f675c2231bf26cd53cba54036ab1290bc5bf5d1f0ec`
- Frozen Video_Games gate script SHA256:
  `018b40d547d1f0b4b3c7e990d25d25194168ed0ce8c24c00d2af9a07d1ae385b`
- Frozen multi-RRF replay script SHA256:
  `cb90273579fe64cc5bfb893688cf3b3a4bd26217c11053e7dcd721dd439a61b1`
- Ordered frozen multi-RRF replay summary SHA256:
  `9026f9d9eb3245b8d4cb0dbb839686b8e30292f2ab0bc7b3d87f9751251d1b9a`
- Ordered frozen multi-RRF replay records SHA256:
  `01384902d405c2a9e95c6ffbb791daa93046d5e378ae7228e215b187f4dc0d00`
- Sparse full-catalog replay script SHA256:
  `16a747e479ca12f107a191609a858a5f957f1f6ae841ec2c131f722e99172fcd`
- Sparse full-catalog replay summary SHA256:
  `5a28de92092d8f9970761bcded74992e7753e3b7459ef4b0f5c10b512b9eeddc`
- Sparse full-catalog replay records SHA256:
  `c539344eedc7383126e08aa0f503b5b3f82f7a782a29e685a0b09add07cd8bd7`
- Sparse-RRF confirmatory input checker SHA256:
  `c2c9319fe1ca8fa095d521f7cd425ff4b15bd73ded5c0aaa284a5a34652394b4`
- Sparse-RRF confirmatory input report SHA256:
  `851cc785d800af99ad43f3010b9bfbbc2c79ed80bb9dd900a415045549736f0f`
- Sparse-RRF confirmatory protocol SHA256:
  `bf966bc249c64f200be5cb917be8979a8ea2eb648d9d7d582bccdac4711c53c2`
- Sparse-RRF confirmatory job runner SHA256:
  `d85c5100dfa8b92c0a2fc4b64a89360d06763fc96d7ec3cdc08a91a703bdbcd5`
- Sparse-RRF confirmatory job manifest SHA256:
  `928835dec01f59fd7da76479b5e8f601b5e6725de0ab7e794cc8fc73ad9a8fc9`
- Sparse-RRF confirmatory queue helper SHA256:
  `2bb8d5acdac5f5c81246e248bf2eebe8653da56359708c48ff537f08b4dd97bc`
- Sparse-RRF confirmatory queue plan SHA256:
  `6f10b8de24f7603ed1f4599973e630a43fa2f85eef4ef060a69c32deb997ead9`
- Sparse-RRF confirmatory job-status log SHA256:
  `70922b1ce3b9ee5fedc6180e03fc5878a48e4e1697bd06e81e00cf134d81dea5`
- Sparse-RRF seed20260801 full-catalog replay summary SHA256:
  `a4ab9dfdb6c692439d9c0b4d309c18f9ab52b961707895dc597a1eb3a640d797`
- Sparse-RRF seed20260801 full-catalog replay records SHA256:
  `a4594a836709979863c6ba73f8d9d8a3dfe96e7468b8a07ce11e375d1f71c4d9`
- Sparse-RRF seed20260802 full-catalog replay summary SHA256:
  `020996f741932a36be6428635275e168ebb3462a83513f0b5a41376d3d3d047d`
- Sparse-RRF seed20260802 full-catalog replay records SHA256:
  `7b2ee9b9f6638516c67b71d6dfab50b32f96daf18cb0f4160923b7d0acaf734f`
- Sparse-RRF seed20260803 full-catalog replay summary SHA256:
  `f7c7adb4689613365742c3a9d70d674eababefc0dac4a6c1c7889d6213771c22`
- Sparse-RRF seed20260803 full-catalog replay records SHA256:
  `06e56a085737d9902959c254cced14567bb6121ce67ab3aa15d3b96f144a5129`
- Sparse-RRF seed20260804 full-catalog replay summary SHA256:
  `be9217ffe1764ff446e198479ddb170f891b21cab3dfb81dcf466c0a305c5774`
- Sparse-RRF seed20260804 full-catalog replay records SHA256:
  `4b07bc2697f8d573fcee359a7fac29ff2fdb773fafe8c59c333f64c30d3f3989`
- Dev10 resume checkpoint SHA256:
  `c9edf3bd9c253d1165b9ab18f412be021fc2f21d1d4dea91f70cf27e4bc50c90`
- Dev10 train summary SHA256:
  `14b066395ce1a11cd013e54a5778bb0da7d6568b464f99a2345dd0928ea3efbe`
- Dev10 valid records SHA256:
  `1ecbdeeae5e2b33f102013d3c341457c5e6b2d05703b03584a070c4ad2af74cf`
- Dev10 test records SHA256:
  `75c532db1a0fd423d113518248eb9f573e5d22ac4167852078dec480043e18f7`
- Dev10 valid pair diagnostic SHA256:
  `c0f674eb358ef25cb8d131cc8d3a04776e8334b69ccda928c0fa0c8dc3eac151`
- Dev10 test pair diagnostic SHA256:
  `de4944270300eb4cad934fff0dd009b9d02bc89bb5f1a6d6bf47323ab48dd520`
- Dev11 temperature-probe checkpoint SHA256:
  `519623eb12e0727faa1f769c550f91d3b52934a8a7afab1c149b6848c2de8fbc`
- Dev11 temperature-probe summary SHA256:
  `feb19b589bb35a427944424d05bae7855670e7eeafa2a1e1783930cf8da7a57e`
- Dev11 temperature-probe run config SHA256:
  `d90f11daf4ba786e69723db513a20dc0ea4068e765bed36a399eb919aa810239`
- Dev13 d96 checkpoint SHA256:
  `6a4d030d0a2bf7c9f9e795159276b0ffa79391ee38e47b9a443a9e2e7a168bee`
- Dev13 d96 train summary SHA256:
  `816eb706e0edfe7fc7777af4e332e8b88584dbf733eaecdccf743973de38a383`
- Dev13 d96 run config SHA256:
  `34396c14f60341cb906106fd52e92f42f1603dc887fa31057dfd3ec16b4c3780`
- Dev13 d96 valid records SHA256:
  `c159d25ab31026f5e14a21fe575e178f35c0adb105f9edb25ac10fdf5af75747`
- Dev13 d96 test records SHA256:
  `6eb69ee69d96696e8da9ef90af8bbccbc21d90d857bb307d40f559d80d29689c`
- Dev13 valid pair diagnostic SHA256:
  `c387f400b12df752ec9581571763d1c8e35e2319bfff58014508b93ba06ce437`
- Dev13 test pair diagnostic SHA256:
  `2558e753c67ba3bee25e085fe2a1bcb14d1bd6f21475a37cf8632e1608d5ac1c`
- Dev13 histogram adaptive fusion summary SHA256:
  `24da2c96bcb8db2951bf2dec25ee0e727c9122ef40dcc5d4a37ee31a53ed04b8`
- Dev13 histogram adaptive fusion test records SHA256:
  `d5bf633e47de4437ee3b5a7dfa29d198f79cc74470f640af7497ccf4a1bdb623`
- Multi-RRF dev9/dev10/dev13/SASRec summary SHA256:
  `f00a3de12337db2b312f9577d851aac9e3cbf9b42e2ba59f3dff5cc2bfbd5ede`
- Multi-RRF dev9/dev10/dev13/SASRec test records SHA256:
  `572d99cebf6d1271c359b41a40ead40961f0d0a7620a7447508ee006db0feff2`
- Multi-RRF refined dev9/dev10/dev13/SASRec summary SHA256:
  `52ff3e11cfb2ebcbbf91dbc33881d75cbfa6a862f5a7136799eed1a05dca4904`
- Multi-RRF refined dev9/dev10/dev13/SASRec test records SHA256:
  `07f826be3915a136db91689fdb9b32609bbaf09a586baee791e22c067e639853`
- Multi-RRF dev3/dev4/dev5/dev9/dev10/dev13/SASRec summary SHA256:
  `2776d9c959b00636886c3e237d6572483768eebbfeb887a6f2f144375ed356eb`
- Multi-RRF dev3/dev4/dev5/dev9/dev10/dev13/SASRec test records SHA256:
  `7ff5b84ac84940b36cc59618d0fa1df61c494bb19a1e901065f6da0137f552bc`
- Multi-RRF dev5/dev10/dev13 refined summary SHA256:
  `4c44cb7618dcca1cdaee62bc6367c71e8a5afe9ba04b99fca51c546a8e63e384`
- Multi-RRF dev5/dev10/dev13 refined test records SHA256:
  `7ff5b84ac84940b36cc59618d0fa1df61c494bb19a1e901065f6da0137f552bc`
- Multi-RRF dev5/dev10/dev13 k-sweep summary SHA256:
  `3c0948d3b8d19d4a552db75c396fbd45eb17af64abf5c106ab50a42da41503c6`
- Multi-RRF dev5/dev10/dev13 k-sweep test records SHA256:
  `ba53609f6950eefff90f50d3e0d17014fe91bd4bf7d58717657852b7f23254fa`
- Multi-RRF dev5/dev10/dev13 fine k-sweep summary SHA256:
  `21cd510678fba2e9aec82975cd916e054551b8517701ef4477cbf5302b95308d`
- Multi-RRF dev5/dev10/dev13 fine k-sweep test records SHA256:
  `42d217291fb36a2226f3f2b8ee5841d701ace106fd891aa83697b9dfa0bca83b`
- Multi-RRF dev5/dev10/dev13 k30 weight-refinement summary SHA256:
  `ab7447782415a078f6d2dbe66e8d4142d29940bd053af494447808ea3398dff0`
- Multi-RRF dev5/dev10/dev13 k30 weight-refinement test records SHA256:
  `a93510cc1d2b2613f9cf8e4739f28798ffacde6d668b3ab14fe9ce4d724ba735`
- Multi-RRF sparse local seven-method summary SHA256:
  `d6df46546a6180baf82941014ca057e64d31d31cee6d4314209ce258f4308298`
- Multi-RRF sparse local seven-method test records SHA256:
  `859171de2415c7331a526c64b33f20a94f068d5cd6fcee86ac9344f6d44f4635`
- Frozen Video_Games candidate manifest SHA256:
  `a97888c17d7449c8bbfb5be145ad354e76fac64323f24e4edd4c49fffca0d6a6`
- Frozen Video_Games gate report SHA256:
  `df26917cbbc7e0552c4a5f675c2231bf26cd53cba54036ab1290bc5bf5d1f0ec`
- Frozen Video_Games gate script SHA256:
  `018b40d547d1f0b4b3c7e990d25d25194168ed0ce8c24c00d2af9a07d1ae385b`
- Frozen multi-RRF replay script SHA256:
  `cb90273579fe64cc5bfb893688cf3b3a4bd26217c11053e7dcd721dd439a61b1`
- Ordered frozen multi-RRF replay summary SHA256:
  `9026f9d9eb3245b8d4cb0dbb839686b8e30292f2ab0bc7b3d87f9751251d1b9a`
- Ordered frozen multi-RRF replay records SHA256:
  `01384902d405c2a9e95c6ffbb791daa93046d5e378ae7228e215b187f4dc0d00`
- Sparse full-catalog replay script SHA256:
  `16a747e479ca12f107a191609a858a5f957f1f6ae841ec2c131f722e99172fcd`
- Sparse full-catalog replay summary SHA256:
  `5a28de92092d8f9970761bcded74992e7753e3b7459ef4b0f5c10b512b9eeddc`
- Sparse full-catalog replay records SHA256:
  `c539344eedc7383126e08aa0f503b5b3f82f7a782a29e685a0b09add07cd8bd7`
- Sparse-RRF confirmatory input checker SHA256:
  `c2c9319fe1ca8fa095d521f7cd425ff4b15bd73ded5c0aaa284a5a34652394b4`
- Sparse-RRF confirmatory input report SHA256:
  `851cc785d800af99ad43f3010b9bfbbc2c79ed80bb9dd900a415045549736f0f`
- Sparse-RRF confirmatory protocol SHA256:
  `bf966bc249c64f200be5cb917be8979a8ea2eb648d9d7d582bccdac4711c53c2`
- Sparse-RRF confirmatory job runner SHA256:
  `d85c5100dfa8b92c0a2fc4b64a89360d06763fc96d7ec3cdc08a91a703bdbcd5`
- Sparse-RRF confirmatory job manifest SHA256:
  `928835dec01f59fd7da76479b5e8f601b5e6725de0ab7e794cc8fc73ad9a8fc9`
- Sparse-RRF confirmatory queue helper SHA256:
  `2bb8d5acdac5f5c81246e248bf2eebe8653da56359708c48ff537f08b4dd97bc`
- Sparse-RRF confirmatory queue plan SHA256:
  `6f10b8de24f7603ed1f4599973e630a43fa2f85eef4ef060a69c32deb997ead9`
- Sparse-RRF confirmatory job-status log SHA256:
  `70922b1ce3b9ee5fedc6180e03fc5878a48e4e1697bd06e81e00cf134d81dea5`

Negative repair checks:

- `hstu_strict_dev6_epoch30_dropout01_20260609`: input dropout `0.1`, test
  NDCG@10 `0.0688288595`.
- `hstu_strict_dev7_epoch30_dropout03_linear03_20260609`: input dropout `0.3`
  plus `hstu_encoder.linear_dropout_rate=0.3`, test NDCG@10 `0.0697376693`.
- `hstu_strict_dev8_epoch30_dropout03_wd1e4_20260609`: input dropout `0.3`
  plus weight decay `1e-4`, test NDCG@10 `0.0701996145`.
- `hstu_strict_dev11_epoch40_dropout03_temp003_20260609`: input dropout `0.3`
  plus sampled-softmax temperature `0.03`, test NDCG@10 `0.0705038416`.
- `hstu_strict_dev13_d96_l4h4_epoch60_dropout03_20260609`: wider HSTU
  (`d=96`, `dv=dqk=24`) improved validation to `0.0801036992` but selected
  checkpoint test NDCG@10 was `0.0717703219`; validation-selected fusion was
  only `0.0723638679`, below the current content-aware best.
- `hstu_dev5_dev10_dev13_multi_rrf_fusion_k_sweep_20260609`: multi-checkpoint
  RRF selected `dev5=0.25`, `dev10=0.25`, `dev13=0.5`, `rrf_k=30` and reached
  test NDCG@10 `0.0759151509`; this is now a surpassed development milestone.
- `hstu_multi7_k30_sparse_local_refine_r005_20260609`: sparse local
  seven-method RRF selected `dev13=0.45`, `dev10=0.20`, `dev5=0.20`,
  `dev4=0.05`, `dev9=0.05`, `sasrec=0.05`, `rrf_k=30` and reached test
  NDCG@10 `0.0765297735`. It is numerically above the upstream HSTU report but
  remains non-claimable development evidence; the frozen manifest is
  `_bestrec_sota_lab/frozen_candidates/video_games_multi_rrf_candidate_20260609.json`.

DropoutNet-assisted candidate development should use the fixed component
feature path:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_research.py --datasets beauty,fashion,instruments,books --seeds 101,102,103 --use-official-dropoutnet --rank-feature-scope zsigmoid --rerank-anchor-method official_dropoutnet --extra-rerank-anchor-methods official_dropoutnet,content_direct --rerank-output-mode rank_blend --rerank-prediction-weight 0.5
```

## Fixed DropoutNet Comparator

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_official_dropoutnet_fixed.py --run-id <confirmatory_run_id> --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705
```

## Confirmatory

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/publication_candidate_mask_seen_v2.json
```

Full confirmatory refuses configs not created under the active strict protocol.
After the masking ablation audit, publication candidates must use
`mask_seen_in_topm=true`. The repaired frozen config is:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/publication_candidate_mask_seen_v2.json --run-id <masked_confirmatory_run_id>
```

The old `confirmatory_strict_v2_candidate_20260611_20260615` run is now
explicitly rejected by `finalize.py` because it used
`mask_seen_in_topm=false` and because those seeds are retired.

For long repaired candidate runs, use the chunk-safe runner. It writes one
full four-dataset `run_config.json` and then fills selected datasets without
overwriting the run config:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory_chunk.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --datasets beauty,fashion,instruments --finalize-bootstrap-reps 200

uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory_chunk.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --datasets books --finalize-bootstrap-reps 200
```

This chunked run is not publication-grade until all datasets have all 25
seed/folds, all required baselines are imported, and finalization is rerun with
the protocol minimum bootstrap replicates.

For expensive Books resumes, use a bounded chunk so the process stops only
after a completed fold:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory_chunk.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --datasets books --max-new-folds 1 --finalize-bootstrap-reps 200
```

The runner also accepts `--fold-ids 0,1,2` to target specific fold IDs for every
selected seed.

## Finalize Existing Run

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/finalize.py --run-id <run_id> --bootstrap-reps 2000
```

If the gates fail, the lab writes `INTERNAL_SOTA_FAILURE_REPORT.md` rather
than allowing a SOTA claim.

## Strict Reality/Fairness/Reproducibility Audit

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/audit_real_fair_reproducible.py --run-id full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705 --out _bestrec_sota_lab/runs/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md
```

This audit exits non-zero whenever the publication gate fails or a Major/Reject
reproducibility finding remains. The Markdown report is generated from
artifacts, not from paper prose.

## Clean Rebuild Audits

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/clean_rebuild_audit.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only
```

This verifies required artifacts, manifest output hashes, table/significance
consistency, and proxy exclusion from `tables.json`.

For the stronger record-level rebuild, regenerate derived artifacts from the
canonical JSONL records in a scratch run:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/clean_rebuild_audit.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --record-level-rebuild --bootstrap-reps 2000
```

This proves summaries, significance, tables, gate, and manifest are rebuildable
from records. By itself it does not rerun model training/scoring or regenerate
JSONL records; strict full-rebuild approval also requires the independent full
experiment rebuild below.

Run the full experiment rebuild in a separate run directory:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_full_clean_rebuild.py --run-id full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705 --stages all --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --bootstrap-reps 2000 --device cpu
```

The command is resumable by stage. For example, a bounded candidate chunk:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_full_clean_rebuild.py --run-id full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705 --stages candidate --datasets books --max-new-folds 1 --bootstrap-reps 200
```

After all stages finish, consume the independent rebuild as strict evidence:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/clean_rebuild_audit.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --full-rebuild-run-id full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705 --record-level-rebuild --bootstrap-reps 2000
```

The current approved strict audit accepts
`_bestrec_sota_lab/runs/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/full_clean_rebuild_compare.json`
as run-local full rebuild evidence.

## Diagnostic Ablations

Generate frozen ablation configs:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/make_ablation_configs.py
```

Run the rerank-pool masking diagnostic smoke:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty --seeds 20260611 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/mask_seen_topm_true.json --run-id ablation_mask_seen_beauty_seed20260611_fold0 --skip-warm --max-folds 1 --finalize-bootstrap-reps 50 --allow-failure-report
```

Run the no-DropoutNet-dependence diagnostic smoke:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty --seeds 20260611 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/no_dropoutnet_feature_or_anchor.json --run-id ablation_no_dn_beauty_seed20260611_fold0 --skip-warm --max-folds 1 --finalize-bootstrap-reps 50 --allow-failure-report
```

Run the full Beauty diagnostics:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/mask_seen_topm_true.json --run-id ablation_mask_seen_beauty_20260611_20260615_full --skip-warm --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/no_dropoutnet_feature_or_anchor.json --run-id ablation_no_dn_beauty_20260611_20260615_full --skip-warm --finalize-bootstrap-reps 200 --allow-failure-report
```

Summarize paired ablation records:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_mask_seen_beauty_20260611_20260615_full --datasets beauty --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/beauty_mask_seen_full_with_baselines.json

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_no_dn_beauty_20260611_20260615_full --datasets beauty --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/beauty_no_dn_full_with_baselines.json
```

Run and summarize the Fashion diagnostics:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets fashion --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/mask_seen_topm_true.json --run-id ablation_mask_seen_fashion_20260611_20260615_full --skip-warm --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets fashion --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/no_dropoutnet_feature_or_anchor.json --run-id ablation_no_dn_fashion_20260611_20260615_full --skip-warm --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_mask_seen_fashion_20260611_20260615_full --datasets fashion --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/fashion_mask_seen_full_with_baselines.json

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_no_dn_fashion_20260611_20260615_full --datasets fashion --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/fashion_no_dn_full_with_baselines.json
```

Run and summarize the Instruments diagnostics:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets instruments --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/mask_seen_topm_true.json --run-id ablation_mask_seen_instruments_20260611_20260615_full --skip-warm --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_mask_seen_instruments_20260611_20260615_full --datasets instruments --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/instruments_mask_seen_full_with_baselines.json

uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets instruments --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/no_dropoutnet_feature_or_anchor.json --run-id ablation_no_dn_instruments_20260611_20260615_full --skip-warm --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_no_dn_instruments_20260611_20260615_full --datasets instruments --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/instruments_no_dn_full_with_baselines.json
```

Run and summarize the Books masking diagnostic. This uses candidate-only mode
because the paired ablation report needs only `lc2c_retrieval_ltr` rows; the
candidate's required feature scorers are still built.

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets books --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/mask_seen_topm_true.json --run-id ablation_mask_seen_books_20260611_20260615_full --skip-warm --candidate-only --resume --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_mask_seen_books_20260611_20260615_full --datasets books --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/books_mask_seen_full_with_baselines.json
```

Run and summarize the Books no-DropoutNet diagnostic:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets books --seeds 20260611,20260612,20260613,20260614,20260615 --candidate-scope full_catalog --no-books-cap --config _bestrec_sota_lab/ablation_configs/no_dropoutnet_feature_or_anchor.json --run-id ablation_no_dn_books_20260611_20260615_full --skip-warm --candidate-only --finalize-bootstrap-reps 200 --allow-failure-report

uv --project _bestrec_run run python _bestrec_sota_lab/summarize_ablation.py --ablation-runs ablation_no_dn_books_20260611_20260615_full --datasets books --baseline-methods official_dropoutnet,official_dropoutnet_fixed,official_blair,official_clcrec,content_direct --out _bestrec_sota_lab/ablation_reports/books_no_dn_full_with_baselines.json
```

Ablations are diagnostics. `finalize.py` rejects them for publication unless a
future config explicitly marks itself as a publication candidate under a frozen
protocol.

## MELT Applicability Audit

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_melt_same_split_audit.py --run-id melt_audit_post_repair_20260701_20260705 --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705
```

This does not produce MELT scores. It audits whether official MELT has the
train item-contexts required by its item branch under the strict item-held-out
protocol. The strict gate accepts MELT only as a documented non-applicable
method with exact status `not_applicable_to_zero_interaction_item_cold`; proxy
MELT evidence remains disallowed.

## LIGER/TIGER Same-Split Export

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_liger_same_split_export.py --run-id liger_export_post_repair_20260701_20260705 --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705
```

This export is not itself a LIGER/TIGER score. It creates LIGER-compatible
processed sequence, item-text, embedding, and target-map files, and verifies
each fold with LIGER's own `process_data_split` parser. The approved
four-dataset cold-item run now includes imported `tiger_liger_retrieval`
full-catalog JSONL records for all strict datasets, seeds, and folds.

## LIGER Dense Evaluation Smoke

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_liger_same_split_eval.py --run-id liger_eval_beauty_fold0_200step --datasets beauty --seeds 20260611 --max-folds 1 --train-steps 200 --rqvae-epochs 5 --codebook-size 32 --latent-dim 64 --d-model 64 --batch-size 64 --eval-batch-size 128
```

This uses official LIGER modules to produce canonical full-catalog records, but
the command above is still a partial smoke run. Do not import it into the
publication gate.

Resume-safe tiny adapter smoke:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_liger_same_split_eval.py --run-id liger_resume_smoke_beauty_fold0_5targets --datasets beauty --seeds 20260611 --fold-ids 0 --max-targets-per-fold 5 --train-steps 1 --rqvae-epochs 1 --codebook-size 8 --latent-dim 16 --d-model 32 --batch-size 16 --eval-batch-size 16 --device cpu

uv --project _bestrec_run run python _bestrec_sota_lab/run_liger_same_split_eval.py --run-id liger_resume_smoke_beauty_fold0_5targets --datasets beauty --seeds 20260611 --fold-ids 0 --max-targets-per-fold 5 --train-steps 1 --rqvae-epochs 1 --codebook-size 8 --latent-dim 16 --d-model 32 --batch-size 16 --eval-batch-size 16 --device cpu --resume
```

The second command must skip the existing complete fold. `import_liger_records.py`
must reject this partial smoke source because it is capped and below the
publication-grade training thresholds.

The historical guarded full shape for regenerating publication-grade
LIGER/LIGER-style evidence is:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_liger_same_split_eval.py --run-id <full_liger_run_id> --export-run-id liger_export_post_repair_20260701_20260705 --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --train-steps 1000 --rqvae-epochs 100 --codebook-size 32 --latent-dim 64 --d-model 64 --batch-size 64 --eval-batch-size 128 --resume
```

This command is expected to be expensive. A regenerated source is not
publication-grade unless it finishes all four datasets, all strict seeds/folds,
no fold cap, no target cap, and writes `publication_grade_records=true`.

## HSTU-BLaIR WSL Reproduction

HSTU-BLaIR is a separate external blocker for broad Video_Games SOTA wording.
The Windows venv cannot run it, so the lab now has a WSL/Linux reproduction
lane:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage inspect --run-id hstu_blair_wsl_inspect

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage setup --run-id hstu_blair_wsl_setup

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage smoke --run-id hstu_blair_wsl_smoke

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage setup-sm120 --run-id hstu_blair_wsl_setup_sm120

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage smoke-sm120 --run-id hstu_blair_wsl_smoke_sm120

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage preprocess-game-sm120 --run-id hstu_blair_wsl_preprocess_game_sm120 --timeout 21600

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage train-game-sm120 --run-id hstu_blair_wsl_train_game_sm120 --timeout 86400
```

The full upstream command remains intentionally explicit and runs from the clean
native WSL clone, not the mounted Windows checkout:

```bash
cd ~/.bestrec_hstu_blair/HSTU-BLaIR
source ~/.bestrec_hstu_blair/venv_py39/bin/activate
mkdir -p tmp
python preprocess_public_data.py
CUDA_VISIBLE_DEVICES=0 python main.py --gin_config_file=configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin --master_port=12345
```

This is not yet a canonical BEST-Rec result. SOTA claims remain blocked until
HSTU-BLaIR is either reproduced and converted to canonical per-user records or
excluded by a source-backed protocol mismatch.
