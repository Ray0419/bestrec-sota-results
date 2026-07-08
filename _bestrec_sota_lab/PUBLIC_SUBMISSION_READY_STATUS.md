# Public Submission Ready Status

Generated from local and GitHub Release evidence after the raw-record archival repair.

## Decision

The narrow full-catalog cold-item claim is now public-submission ready under the lab's strict gate.

This does not authorize a broad recommender-system SOTA claim. The allowed claim remains:

> LC2C Retrieval LTR is the best audited method in this package for zero-interaction full-catalog cold-item ranking on the four Amazon 2023 datasets under the frozen protocol.

## Evidence

- Public submission gate: `approve_public_submission`.
- Gate report: `_bestrec_sota_lab/publication_artifacts/PUBLIC_SUBMISSION_GATE.md`.
- Gate JSON SHA256: `24bd0f30f2cd8e2a3df05f1268bbe751ad4f55c32225bc289d8443385af8e940`.
- Gate Markdown SHA256: `3a97a327251d2a9d8a7d90dbf4047e43243eea91283af78eedeee57cfed9c36d`.
- Gate generated UTC: `2026-06-10T09:27:10Z`.
- Strict artifact audit: `_bestrec_sota_lab/runs/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md`.
- Source archive SHA256: `e4a7c1527f482e66b869b34403c7cd2087032f65ca76997f1082aefc8313b724`.
- Rendered PDF SHA256: `a8c76bbfd2bf64081d88063ffe6ba346a282bb8b56bab8ddf02337ab34d0d7f6`.

## Raw-Record Release

- Release URL: https://github.com/Ray0419/bestrec-sota-results/releases/tag/bestrec-raw-records-v1
- Raw manifest: `_bestrec_sota_lab/publication_artifacts/raw_record_release/raw_record_release_manifest.json`.
- Raw manifest SHA256: `09367ee4b94b68619a4f341b65b497c552812b34140ebc745bc197ea7b343257`.
- Upload-parts manifest: `_bestrec_sota_lab/publication_artifacts/raw_record_release/raw_record_upload_parts_manifest.json`.
- Upload-parts manifest SHA256: `1fe28b830f99e5d273aff3c6fc03aeda83c46f614c00ef3f461262c4faed8a7c`.
- Raw rows: `23,357,327`.
- Raw bytes: `5,099,053,650`.
- Upload parts: `7`.
- Release assets verified by `validate_public_submission.py --deep-verify-raw --verify-github-release`: `11` expected, `11` actual, no missing assets, no unexpected assets, no size/digest mismatches.

## Commands Re-run

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/prepare_raw_record_release.py --archive-url https://github.com/Ray0419/bestrec-sota-results/releases/tag/bestrec-raw-records-v1
uv --project _bestrec_run run python _bestrec_sota_lab/package_raw_record_release.py --overwrite
uv --project _bestrec_run run python _bestrec_sota_lab/package_raw_record_release.py --verify-parts
uv --project _bestrec_run run python _bestrec_sota_lab/archive_source.py --run-id full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705
uv --project _bestrec_run run python _bestrec_sota_lab/audit_real_fair_reproducible.py --run-id full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705 --out _bestrec_sota_lab/runs/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md
uv --project _bestrec_run run python _bestrec_sota_lab/validate_public_submission.py --deep-verify-raw --verify-github-release
```

## Remaining Caveats

- A Zenodo, OSF, or institutional DOI mirror would be stronger for camera-ready archival permanence.
- Do not claim broad warm-start/general recommender SOTA.
- Do not claim DropoutNet-independent superiority; the candidate uses DropoutNet-derived evidence as a feature/rerank anchor.
- LightGCN, MultiVAE, and iALS are not completed cold-item full-catalog baselines in this lab gate.
