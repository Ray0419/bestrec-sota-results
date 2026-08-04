# Upload Parts Manifest

Generated UTC: `2026-06-10T09:21:33Z`

These files are deterministic binary chunks of the canonical raw JSONL records. Upload every part, `raw_record_release_manifest.json`, and `raw_record_upload_parts_manifest.json` to the same public archive/release.

- Part byte limit: `1,500,000,000`
- Total parts: `7`
- Total part bytes: `5,099,053,650`
- Raw manifest SHA256: `09367ee4b94b68619a4f341b65b497c552812b34140ebc745bc197ea7b343257`

| Dataset | Source | Source bytes | Parts | Source SHA256 |
| --- | --- | ---: | ---: | --- |
| beauty | `cold_full_catalog_records_beauty.jsonl` | 19,003,185 | 1 | `57cf6cca51f2649d0235d88396c4e7eb3e79f854ceba4b83a18cf020184ffc63` |
| books | `cold_full_catalog_records_books.jsonl` | 4,592,676,033 | 4 | `5b8254afc7f6dfb4d3cceb0b8e0829881287f47c31379b2b9657763b46cdf382` |
| fashion | `cold_full_catalog_records_fashion.jsonl` | 28,705,816 | 1 | `7e81a5c3bb7ebcf018a4c1f36fbdc974950742547bcafed841c0e77ef046f0ab` |
| instruments | `cold_full_catalog_records_instruments.jsonl` | 458,668,616 | 1 | `9c7310b282fa2d7c36327308df8be3aee4182edf1804a86ae07d872ebedfc580` |

## Part Files

| Dataset | Part | Bytes | SHA256 |
| --- | --- | ---: | --- |
| beauty | `cold_full_catalog_records_beauty.jsonl.part001of001` | 19,003,185 | `57cf6cca51f2649d0235d88396c4e7eb3e79f854ceba4b83a18cf020184ffc63` |
| books | `cold_full_catalog_records_books.jsonl.part001of004` | 1,500,000,000 | `ce238771c54d88d3917ba6d39902bf43d47fb2daff9b5f58b61db5a27eb412e1` |
| books | `cold_full_catalog_records_books.jsonl.part002of004` | 1,500,000,000 | `955dcf74cf374a139e6909a4e5aef31bf903d0545e723b924cb53a854424c44b` |
| books | `cold_full_catalog_records_books.jsonl.part003of004` | 1,500,000,000 | `c7d1440a3fbfcfb80037934f32eacea385acce200883a4e09295eb3c52bfb6f9` |
| books | `cold_full_catalog_records_books.jsonl.part004of004` | 92,676,033 | `de15f29d59d1c6a3fcafc54b736d7b871ad2db8afb0aed03fe1a7255c42992c1` |
| fashion | `cold_full_catalog_records_fashion.jsonl.part001of001` | 28,705,816 | `7e81a5c3bb7ebcf018a4c1f36fbdc974950742547bcafed841c0e77ef046f0ab` |
| instruments | `cold_full_catalog_records_instruments.jsonl.part001of001` | 458,668,616 | `9c7310b282fa2d7c36327308df8be3aee4182edf1804a86ae07d872ebedfc580` |

## Verify After Download

Place the parts under the recorded `upload_parts` directory and run:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/package_raw_record_release.py --verify-parts
```

The verifier checks each part hash and streams the parts in order to confirm that they reconstruct the exact raw JSONL SHA256 values from `raw_record_release_manifest.json`.
