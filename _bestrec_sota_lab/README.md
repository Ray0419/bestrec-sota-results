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

## Development

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_research.py --datasets beauty,fashion,instruments,books --seeds 101,102,103
```

Smoke test:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_research.py --datasets beauty --seeds 101 --quick --run-id smoke_beauty --allow-negative
```

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
uv --project _bestrec_run run python _bestrec_sota_lab/audit_real_fair_reproducible.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --out _bestrec_sota_lab/STRICT_REAL_FAIR_REPRO_REVIEW_20260605.md
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
from records. It does not rerun model training/scoring or regenerate JSONL
records; `strict_clean_rebuild_passed` remains `false` until the full
experiment pipeline is rerun from documented commands.

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

This export is not a LIGER/TIGER score. It creates LIGER-compatible processed
sequence, item-text, embedding, and target-map files, and verifies each fold
with LIGER's own `process_data_split` parser. The publication gate remains
failed until official LIGER/TIGER predictions are converted to canonical
full-catalog JSONL records.

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
must still reject this source because it is partial, capped, and below the
publication-grade training thresholds.

Publication-grade LIGER/LIGER-style evidence remains unrun. The guarded full
shape is:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_liger_same_split_eval.py --run-id <full_liger_run_id> --export-run-id liger_export_post_repair_20260701_20260705 --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --train-steps 1000 --rqvae-epochs 100 --codebook-size 32 --latent-dim 64 --d-model 64 --batch-size 64 --eval-batch-size 128 --resume
```

This command is expected to be expensive. It is not publication-grade unless it
finishes all four datasets, all strict seeds/folds, no fold cap, no target cap,
and writes `publication_grade_records=true`.
