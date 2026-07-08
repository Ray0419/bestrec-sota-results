# Public Submission Gate

Generated UTC: `2026-06-10T09:27:10Z`

Run id: `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705`

Decision: **approve_public_submission**

## Checks

| Check | Passed | Detail |
| --- | ---: | --- |
| `strict_artifact_audit_approved` | `True` | _bestrec_sota_lab\runs\full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705\STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md |
| `raw_records_externally_archived` | `True` | external archive URL/DOI present |
| `github_release_assets_match_manifests` | `True` | GitHub release assets match local manifests by name, size, and available SHA256 digest |
| `raw_record_manifest_deep_verify` | `True` |  |
| `paper_rendered_outputs_present_and_fresh` | `True` |  |
| `paper_claim_boundaries_present` | `True` |  |
| `paper_no_stale_rejection_or_provenance_text` | `True` |  |

This gate is intentionally stricter than the local artifact audit. Passing means the strict artifact report, local raw records, external release assets, rendered paper, and claim-boundary language all agreed at generation time.
