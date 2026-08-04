# SASRec-SBERT Implementation Verification

**Audit time:** 2026-06-08 12:31:01 +10:00

## Verdict

The implementation in `_bestrec_run/run_sasrec_sbert.py` is a SASRec-style
PyTorch reimplementation with frozen text-feature augmentation. It is not a
novel backbone and should be described as such in any paper.

## Verified Components

| Component | Status | Notes |
|---|---|---|
| Sequential backbone | SASRec-style | Causal left-to-right Transformer encoder over item sequences. |
| Padding/eval bug fix | Verified in code | Uses right-padding and avoids the left-padding/key-padding-mask NaN trap documented in the writeups. |
| Text features | Prior work | SBERT/MiniLM and BLaIR features are frozen external encoders, not local inventions. |
| MLP adaptor | Prior work | `--mlp-adaptor` follows Hou et al. SASRecText-style `768->300->64` ReLU/dropout adaptor. |
| Loss | Local engineering | Supports full softmax, sampled softmax, in-batch negatives, and chunked full softmax for large item catalogs. |
| Evaluation | Local engineering | Ranks against the full item catalog and masks the user's known input history. |

## Result File Snapshot

| Result file | Dataset | NDCG@10 | HR@10 | MRR | Users | Items |
|---|---|---:|---:|---:|---:|---:|
| `results_sasrec_sbert_Video_Games_v3.json` | Video_Games | 0.0543478 | 0.0983517 | 0.0489073 | 94,762 | 25,612 |
| `results_sasrec_sbert_Video_Games_seed20260522.json` | Video_Games | 0.0497873 | 0.0898672 | 0.0451127 | 94,762 | 25,612 |
| `results_sasrec_sbert_Video_Games_seed20260523.json` | Video_Games | 0.0500020 | 0.0906798 | 0.0452239 | 94,762 | 25,612 |
| `results_sasrec_chunkedfull_Beauty.json` | Beauty_and_Personal_Care | 0.0191144 | 0.0346393 | 0.0177866 | 729,576 | 207,649 |
| `results_sasrec_blair_mlp_drop02_Beauty.json` | Beauty_and_Personal_Care | 0.0192782 | 0.0347202 | 0.0178819 | 729,576 | 207,649 |
| `results_sasrec_blair_richtext_mlp_Beauty.json` | Beauty_and_Personal_Care | 0.0193575 | 0.0348038 | 0.0180004 | 729,576 | 207,649 |
| `results_sasrec_blair_richtext_mlp_seed43_Beauty.json` | Beauty_and_Personal_Care | 0.0195452 | 0.0351396 | 0.0181366 | 729,576 | 207,649 |

## Strict Reviewer Notes

- The Video_Games result is internally reproducible from saved JSON files, but
  the external SOTA claim is still conditional on exact comparator protocol
  verification.
- The Beauty gain is small and not statistically publishable yet because the
  strongest baseline and the BLaIR-rich-text/MLP variant do not have a complete
  matched multi-seed significance test.
- Seed metadata is missing or inconsistent in several historical JSON files.
  Future confirmatory runs must record seed, command, git commit, environment,
  data hashes, and artifact hashes.
- The result files are aggregate JSON, not per-user record files. That is not
  enough for final Wilcoxon/bootstrap publication gates.

