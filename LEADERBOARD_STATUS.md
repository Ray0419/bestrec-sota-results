# Leaderboard Status

**Audit time:** 2026-06-08 12:31:01 +10:00

## Video_Games

| Method/source | NDCG@10 | Status |
|---|---:|---|
| HSTU-BLaIR upstream README | 0.0760 | Stronger external reported result; not locally reproduced/protocol-verified |
| SASRec-SBERT, fresh 5-seed confirmatory mean | 0.05509 ± 0.00035 | New auditable rerun with 473,810 per-user records |
| SASRec-BLaIR, same-run 5-seed confirmatory mean | 0.05452 ± 0.00075 | Same protocol; loses to SASRec-SBERT, Holm p = 0.0311053 |
| SASRec no-text, same-run 5-seed confirmatory mean | 0.05097 ± 0.00068 | Same protocol; loses to SASRec-SBERT, Holm p = 1.05610e-31 |
| SASRec-SBERT, seed/result `v3` | 0.0543478 | Saved repository result |
| SASRec-SBERT, seed/result `20260522` | 0.0497873 | Saved repository result |
| SASRec-SBERT, seed/result `20260523` | 0.0500020 | Saved repository result |
| BLaIR encoder ablation in local SASRec | 0.0497834 | Saved repository result |
| Minimal TIGER local prototype | 0.0200877 | Negative local prototype, not official TIGER |
| TIGER/LIGER local checkout | not comparable | Targets Amazon 2014 Beauty/Toys/Sports and Steam, not AR2023 Video_Games |

Strict interpretation: SASRec-SBERT is internally strong and beats same-run
ablations. The external SOTA statement is blocked by HSTU-BLaIR and unresolved
generative-retrieval comparators.

## Beauty_and_Personal_Care

| Method/source | NDCG@10 | Status |
|---|---:|---|
| SASRec d=64 chunked full-softmax | 0.0191144 | Saved repository baseline |
| SASRec + BLaIR + Hou et al. MLP | 0.0192782 | Saved repository result |
| SASRec + BLaIR-rich-text + Hou et al. MLP, seed/result 42 | 0.0193575 | Saved repository result |
| SASRec + BLaIR-rich-text + Hou et al. MLP, seed 43 | 0.0195452 | Saved repository result |
| BERT4Rec d=64 | 0.0159913 | Saved negative baseline |
| TIGER published target range | ~0.031 | Approximate session target, not yet source-locked |
| LIGER published target range | ~0.045+ | Approximate session target, not yet source-locked |

Strict interpretation: Beauty_and_Personal_Care SOTA is not achieved. The
positive BLaIR-rich-text/MLP direction is too small to claim significance
without matched multi-seed per-user tests.

## Final Reviewer Position

The leaderboard is good enough for an internal research note and a guarded
workshop draft. It is not yet good enough for an unqualified "state of the art"
paper.
