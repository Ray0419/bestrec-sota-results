# Raw Record Release Manifest

Generated UTC: `2026-06-10T09:21:13Z`

This manifest covers the canonical per-record JSONL files required for adversarial reanalysis of the approved full-catalog cold-item claim. It is intentionally small and suitable for Git; the raw JSONL files are not committed because they total more than 5 GB.

- Canonical run id: `confirmatory_masked_candidate_20260701_20260705_candidate_only`
- Independent rebuild run id: `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705`
- Total bytes: `5,099,053,650`
- Total rows: `23,357,327`
- External archive status: `uploaded`
- External archive URL: `https://github.com/Ray0419/bestrec-sota-results/releases/tag/bestrec-raw-records-v1`
- External archive DOI: `pending`

| Dataset | File | Bytes | Rows | SHA256 |
| --- | --- | ---: | ---: | --- |
| Beauty | `cold_full_catalog_records_beauty.jsonl` | 19,003,185 | 88,725 | `57cf6cca51f2649d0235d88396c4e7eb3e79f854ceba4b83a18cf020184ffc63` |
| Fashion | `cold_full_catalog_records_fashion.jsonl` | 28,705,816 | 132,972 | `7e81a5c3bb7ebcf018a4c1f36fbdc974950742547bcafed841c0e77ef046f0ab` |
| Instruments | `cold_full_catalog_records_instruments.jsonl` | 458,668,616 | 2,065,910 | `9c7310b282fa2d7c36327308df8be3aee4182edf1804a86ae07d872ebedfc580` |
| Books | `cold_full_catalog_records_books.jsonl` | 4,592,676,033 | 21,069,720 | `5b8254afc7f6dfb4d3cceb0b8e0829881287f47c31379b2b9657763b46cdf382` |

## Clean-Rebuild Evidence

The independent full clean rebuild can append records in a different order, so byte hashes are not expected to match across runs. The order-independent row-multiset comparison must match:

- `full_clean_rebuild_compare.json` passed: `True`
- `max_metric_abs_diff`: `0.0`
- `record_multisets_match`: `True`

## Verification

After downloading the raw files into the canonical run directory, rerun:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/prepare_raw_record_release.py --verify-only
```

A public submission should replace the pending archive URL/DOI above by rerunning this script with `--archive-url` and/or `--archive-doi` after upload.
