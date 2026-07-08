# BEST-Rec / LC2C++ Publication Artifact Package

Packaged UTC: 2026-06-06T13:57:54Z

Strict audit refreshed UTC: 2026-06-10T08:01:10Z

This directory contains the compact, commit-visible empirical artifact package for the strict full-catalog cold-item SOTA audit. It was added after the initial GitHub push because `_bestrec_sota_lab/runs/*` is intentionally ignored to avoid committing multi-GB per-user JSONL records to normal Git.

## Scope

- Claim covered: cold-item full-catalog ranking on Beauty, Fashion, Instruments, and Books.
- Claim not covered: broad warm-start or general recommender SOTA.
- Canonical run id: `confirmatory_masked_candidate_20260701_20260705_candidate_only`.
- Independent rebuild run id: `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705`.
- Protocol id: `cold_sota_strict_v2`.
- Candidate scope: `full_catalog`.
- Confirmatory seeds: `20260701, 20260702, 20260703, 20260704, 20260705`.
- Finalization command recorded by manifest: `python _bestrec_sota_lab/finalize.py --run-id confirmatory_masked_candidate_20260701_20260705_candidate_only --bootstrap-reps 2000`.

## Included Artifacts

The canonical confirmatory directory includes:

- `run_config.json`: frozen algorithm config, datasets, seeds, candidate scope, and protocol path.
- `results_manifest.json`: timestamps, command, machine notes, Python/platform, input hashes, output hashes, and seed list.
- `results_final.json`: final aggregate results.
- `significance.json`: Holm-corrected Wilcoxon and clustered bootstrap evidence.
- `tables.json`: publication table values.
- `publication_gate.json`: strict pass/fail gate.
- `baseline_audit.json` and method audit files: baseline status, evidence files, seeds, and applicability notes.

The independent rebuild directory includes:

- `full_clean_rebuild_audit.json`.
- `full_clean_rebuild_compare.json`.
- Rebuilt `results_final.json`, `significance.json`, `tables.json`, `publication_gate.json`, and `results_manifest.json`.

The source package outside this directory includes:

- `_bestrec_sota_lab/source_archive_manifest.json`.
- `_bestrec_sota_lab/source_archives/bestrec_sota_lab_source_full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705.zip`.
- Source archive SHA256 and source file count are authoritative in
  `_bestrec_sota_lab/source_archive_manifest.json` and repeated in the current
  strict review report.

## Primary Result Summary

Strict gate status: passed.

| Dataset | LC2C retrieval LTR NDCG@10 | Best baseline | Best baseline NDCG@10 | Clustered bootstrap 95% CI for delta |
| --- | ---: | --- | ---: | --- |
| Beauty | 0.148825868265 | official_dropoutnet | 0.132136507692 | [0.0061, 0.0279] |
| Fashion | 0.130137817674 | official_dropoutnet | 0.095089227114 | [0.0271, 0.0434] |
| Instruments | 0.049575215957 | official_dropoutnet | 0.023654099528 | [0.0239, 0.0279] |
| Books | 0.040225492558 | official_dropoutnet | 0.022519558968 | [0.0158, 0.0196] |

The current review decision in `_bestrec_sota_lab/runs/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md` approves only the cold-item full-catalog claim under this protocol.

## Key Frozen Parameters

From `run_config.json`:

- Method: `lc2c_retrieval_ltr`.
- Fallback method: `official_dropoutnet`.
- Feature methods: `content_direct`, `blair_text`, `faithful_dropoutnet`, `lc2c_v2`, `lc2cpp_validated_margin`, `melt_tail_transfer`, `popularity`, `official_dropoutnet`.
- Learning rate: `0.04`.
- Max depth: `3`.
- Estimators: `120`.
- Max train examples: `60000`.
- Negative samples per positive: `32`.
- Rank feature scope: `zsigmoid`.
- `mask_seen_in_topm`: `true`.
- Bootstrap repetitions for approval: `2000`.

DropoutNet frozen configs are recorded per dataset in `run_config.json` and `baseline_run_config_official_dropoutnet_fixed.json`.

## Machine And Setup Notes

From `results_manifest.json`:

- Working directory: `C:\Users\rayxc\Documents\R`.
- Platform: `Windows-11-10.0.26200-SP0`.
- Processor: `Intel64 Family 6 Model 198 Stepping 2, GenuineIntel`.
- Python: `3.12.13`.
- Experiment base git commit recorded by run manifest: `f05c139`.
- External LIGER revision recorded by source archive manifest: `b6ccc37af5ee623ddc1d1ead3490c31aaeaf4524`.
- MELT dependency is recorded as a gitlink in `.gitmodules` and the repository tree.

## Raw Record Inventory

The canonical per-user records are not committed to Git because the largest file is 4.59 GB. They remain local under `_bestrec_sota_lab/runs/confirmatory_masked_candidate_20260701_20260705_candidate_only/`, and their reproducibility evidence is captured in `full_clean_rebuild_compare.json`.

A generated raw-record release manifest is available under
`_bestrec_sota_lab/publication_artifacts/raw_record_release/`. It streams the
canonical JSONL files, verifies byte sizes, row counts, SHA256 hashes, and links
them to the independent clean-rebuild multiset evidence. Current status:
`uploaded` to the GitHub Release archive at
https://github.com/Ray0419/bestrec-sota-results/releases/tag/bestrec-raw-records-v1.
The release uses seven deterministic chunk files described by
`raw_record_upload_parts_manifest.json`.

The public-submission gate is recorded in
`_bestrec_sota_lab/publication_artifacts/PUBLIC_SUBMISSION_GATE.md`. It should
be rerun with `--deep-verify-raw --verify-github-release` before submission so
that the local raw records, release assets, checksums, and paper text are all
checked together.

| Dataset | Raw record file | Local bytes | Row count | Canonical raw SHA256 |
| --- | --- | ---: | ---: | --- |
| Beauty | `cold_full_catalog_records_beauty.jsonl` | 19,003,185 | 88,725 | `57cf6cca51f2649d0235d88396c4e7eb3e79f854ceba4b83a18cf020184ffc63` |
| Fashion | `cold_full_catalog_records_fashion.jsonl` | 28,705,816 | 132,972 | `7e81a5c3bb7ebcf018a4c1f36fbdc974950742547bcafed841c0e77ef046f0ab` |
| Instruments | `cold_full_catalog_records_instruments.jsonl` | 458,668,616 | 2,065,910 | `9c7310b282fa2d7c36327308df8be3aee4182edf1804a86ae07d872ebedfc580` |
| Books | `cold_full_catalog_records_books.jsonl` | 4,592,676,033 | 21,069,720 | `5b8254afc7f6dfb4d3cceb0b8e0829881287f47c31379b2b9657763b46cdf382` |

The independent rebuild has different raw JSONL byte hashes because records can be appended in a different order, but `full_clean_rebuild_compare.json` reports `max_metric_abs_diff=0.0`, `record_multisets_match=true`, and identical row-multiset fingerprints for all four datasets.

## Reviewer Caveats

- Normal GitHub Git is not a proper home for the 5+ GB raw record set, so the raw records are stored as release assets rather than committed files. A Zenodo/OSF DOI mirror would be stronger for camera-ready archival permanence.
- Run `uv --project _bestrec_run run python _bestrec_sota_lab/validate_public_submission.py --deep-verify-raw --verify-github-release` before any public submission.
- The pushed Git tree plus GitHub Release assets are enough to audit code, configs, hashes, summarized results, significance, gates, clean rebuild equivalence, and raw per-record data.
- Any paper must state the claim as full-catalog cold-item ranking only.
