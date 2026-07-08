# `_bestrec_run` Attribution And Reproducibility Notes

This directory contains the experimental scripts and result artifacts for the
SASRec-SBERT / Beauty gap-closing work. Treat `_bestrec_run/CITATIONS.md` as
the source of truth for prior work attribution.

## Strict Claim Scope

- SASRec-SBERT is a SASRec-style sequential recommender with frozen text
  features; it is not a new Transformer backbone.
- SBERT/MiniLM, BLaIR, Amazon Reviews 2023, TIGER, LIGER, BERT4Rec,
  DropoutNet, CLCRec, EASE, LightGCN, iALS, and MultiVAE are prior work.
- The Hou et al. SASRecText-style MLP adaptor used by `--mlp-adaptor` is
  adopted from `external/AmazonReviews2023/seq_rec_results/model/sasrectext.py`.
- The local contribution is empirical and engineering: 5-core preprocessing,
  full-catalog evaluation, bug fixes, cached evaluation, chunked full-softmax,
  integration experiments, and negative-result reporting.

## Primary Artifacts

- `_bestrec_run/run_sasrec_sbert.py`: SASRec-style sequential model with
  optional SBERT/BLaIR feature projection and optional Hou et al. MLP adaptor.
- `_bestrec_run/encode_blair_5core.py`: BLaIR title embedding cache builder.
- `_bestrec_run/encode_richtext_5core.py`: MiniLM rich-text cache builder.
- `_bestrec_run/encode_blair_richtext_5core.py`: BLaIR rich-text cache builder.
- `_bestrec_run/compare_beauty_results.py`: lightweight Beauty result
  comparison from generated JSON files.

## Reproducibility Commands

Run from repository root using the `_bestrec_run` uv project:

```powershell
uv --project _bestrec_run run python _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 30
uv --project _bestrec_run run python _bestrec_run/compare_beauty_results.py
```

Long GPU runs should write new output filenames and must not overwrite existing
published JSON artifacts unless the experiment is explicitly being regenerated.

