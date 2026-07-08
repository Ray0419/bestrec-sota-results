# LC2C Retrieval LTR Paper Draft

This directory is a first publishable-paper source package for the strict cold-item full-catalog BEST-Rec / LC2C retrieval experiment.

Files:

- `lc2c_retrieval_ltr_paper.md`: main manuscript draft.
- `data_processing_appendix.md`: generated data-processing appendix inserted into the manuscript.
- `data_processing_appendix.json`: machine-readable source for the generated appendix.
- `generate_data_processing_appendix.py`: regenerates Appendix A from cached data and approved artifacts.
- `references.bib`: BibTeX entries used by the manuscript.
- `literature_scan_20260608.md`: source notes from the literature scan.
- `submission_blockers.md`: strict reviewer checklist before public submission.
- `build/`: rendered paper outputs.

The manuscript is intentionally narrow. It supports a full-catalog cold-item ranking claim only. It does not claim broad warm-start or general recommender SOTA.

Successful local render commands:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
pandoc _bestrec_sota_lab/paper_draft/lc2c_retrieval_ltr_paper.md --standalone --citeproc --bibliography _bestrec_sota_lab/paper_draft/references.bib -o _bestrec_sota_lab/paper_draft/build/lc2c_retrieval_ltr_paper.html
pandoc _bestrec_sota_lab/paper_draft/lc2c_retrieval_ltr_paper.md --standalone --citeproc --bibliography _bestrec_sota_lab/paper_draft/references.bib -o _bestrec_sota_lab/paper_draft/build/lc2c_retrieval_ltr_paper.docx
pandoc _bestrec_sota_lab/paper_draft/lc2c_retrieval_ltr_paper.md --standalone --citeproc --bibliography _bestrec_sota_lab/paper_draft/references.bib --pdf-engine=typst -o _bestrec_sota_lab/paper_draft/build/lc2c_retrieval_ltr_paper.pdf
```

Local build tools installed:

- Pandoc 3.10
- Typst 0.14.2

Primary empirical source:

`_bestrec_sota_lab/publication_artifacts/confirmatory_masked_candidate_20260701_20260705_candidate_only/`

Independent rebuild source:

`_bestrec_sota_lab/publication_artifacts/full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705/`

Raw-record release manifest:

`_bestrec_sota_lab/publication_artifacts/raw_record_release/raw_record_release_manifest.json`

Final public-submission gate:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/validate_public_submission.py --deep-verify-raw --verify-github-release
```
