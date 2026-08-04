# SASRec-SBERT Confirmatory Rerun Report

**Run date:** 2026-06-08  
**Run directory:** `_bestrec_confirmatory_sasrec/video_games_sasrec_confirmatory_20260608_5seed/`  
**Dataset:** Amazon Reviews 2023 `Video_Games` 5-core leave-last-out  
**Candidate scope:** full catalog, user history masked  
**Methods:** `sasrec_sbert`, `sasrec_blair`, `sasrec_no_sbert`  
**Fresh seeds:** `20260608,20260609,20260610,20260611,20260612`

## Command

```powershell
_bestrec_run\.venv\Scripts\python.exe _bestrec_run\run_sasrec_confirmatory.py `
  --category Video_Games `
  --methods sasrec_sbert,sasrec_blair,sasrec_no_sbert `
  --seeds 20260608,20260609,20260610,20260611,20260612 `
  --epochs 30 `
  --eval-every 5 `
  --run-id video_games_sasrec_confirmatory_20260608_5seed `
  --resume
```

The run ID was new when launched, so `--resume` did not skip any seed during
the actual training pass. It was used again after completion to refresh derived
summaries and the manifest without rerunning training.

## Primary Result

| Seed | Best epoch | NDCG@10 | HR@10 | MRR | Per-user records |
|---:|---:|---:|---:|---:|---:|
| 20260608 | 15 | 0.0546930 | 0.0985100 | 0.0493902 | 94,762 |
| 20260609 | 10 | 0.0551649 | 0.1009687 | 0.0493300 | 94,762 |
| 20260610 | 10 | 0.0553428 | 0.1002723 | 0.0498045 | 94,762 |
| 20260611 | 10 | 0.0547804 | 0.0992064 | 0.0493729 | 94,762 |
| 20260612 | 10 | 0.0554822 | 0.0999979 | 0.0501063 | 94,762 |

**Mean NDCG@10:** `0.0550927`  
**Sample std NDCG@10:** `0.0003452`  
**Total per-user records:** `473,810`

## Same-Run Comparator Result

| Method | Mean NDCG@10 | Std | Total records |
|---|---:|---:|---:|
| `sasrec_sbert` | 0.0550927 | 0.0003452 | 473,810 |
| `sasrec_blair` | 0.0545244 | 0.0007472 | 473,810 |
| `sasrec_no_sbert` | 0.0509659 | 0.0006818 | 473,810 |

Paired per-user/per-seed Wilcoxon tests:

| Comparison | Mean delta NDCG@10 | P-value | Holm p-value |
|---|---:|---:|---:|
| `sasrec_sbert` > `sasrec_blair` | 0.0005682 | 0.0311053 | 0.0311053 |
| `sasrec_sbert` > `sasrec_no_sbert` | 0.0041268 | 5.28049e-32 | 1.05610e-31 |

## Artifacts

- `results_final.json`: aggregate summary.
- `publication_gate.json`: strict publication gate, including external SOTA blockers.
- `results_manifest.json`: command, environment, input hashes, output hashes.
- `result_Video_Games_sasrec_sbert_seed*.json`: per-seed training/eval traces.
- `warm_full_catalog_records_Video_Games_sasrec_sbert_seed*.jsonl`: canonical
  per-user records.

## Validation Checks

- Per-user record schema: **passed**.
- Record count per seed: **94,762 / 94,762 passed**.
- Candidate scope: **all `full_catalog`**.
- Manifest output hashes: **passed** after excluding mutable process logs.
- `git diff --check`: **passed**, with Windows line-ending warnings only.

## Strict Reviewer Verdict

The confirmatory rerun supports the claim that the SASRec-SBERT Video_Games
result is real and stable under fresh seeds. The fresh 5-seed mean is slightly
stronger than the old exploratory mean.

However, this still does **not** authorize an unqualified SOTA publication claim.
HSTU-BLaIR reports `Video Games` NDCG@10 = `0.0760`, far above our
`0.0550927`, and was not reproduced under this exact protocol. TIGER/LIGER-style
generative retrieval is also not protocol-matched in the local checkout. The
correct wording remains:

> SASRec-SBERT achieves a stable `0.05509 ± 0.00035` NDCG@10 on our
> full-catalog Amazon Reviews 2023 Video_Games 5-core protocol and significantly
> beats same-run SASRec-BLaIR and no-text SASRec ablations. Final SOTA wording
> requires protocol-matched reproduction of stronger external comparators.
