# Validation Run Status

**Audit time:** 2026-06-08 12:31:01 +10:00

## Commands Run In This Audit

```powershell
_bestrec_run\.venv\Scripts\python.exe _bestrec_run\run_sasrec_confirmatory.py --category Video_Games --methods sasrec_sbert --seeds 20260608,20260609,20260610,20260611,20260612 --epochs 30 --eval-every 5 --run-id video_games_sasrec_confirmatory_20260608_5seed --resume
```

Result: completed five fresh seeds and wrote
`_bestrec_confirmatory_sasrec/video_games_sasrec_confirmatory_20260608_5seed/`.
Mean NDCG@10 is `0.0550927 ± 0.0003452`; total per-user records: `473,810`.

```powershell
_bestrec_run\.venv\Scripts\python.exe _bestrec_run\run_sasrec_confirmatory.py --category Video_Games --methods sasrec_sbert,sasrec_blair,sasrec_no_sbert --seeds 20260608,20260609,20260610,20260611,20260612 --epochs 30 --eval-every 5 --run-id video_games_sasrec_confirmatory_20260608_5seed --resume
```

Result: completed/validated same-run comparators without retraining completed
seeds. `sasrec_sbert` mean NDCG@10 = `0.0550927`, `sasrec_blair` =
`0.0545244`, and `sasrec_no_sbert` = `0.0509659`. Holm-adjusted paired
Wilcoxon p-values are `0.0311053` and `1.05610e-31`, respectively.

```powershell
_bestrec_run\.venv\Scripts\python.exe external\HSTU-BLaIR\main.py --help
```

Result: failed before training with `ModuleNotFoundError: No module named
'fbgemm_gpu'`. The upstream HSTU-BLaIR code also hard-codes multiprocessing
`forkserver`, while this Windows environment exposes only `spawn`.

```powershell
uv pip compile external\HSTU-BLaIR\requirements.txt --python-version 3.9 --python-platform x86_64-pc-windows-msvc --torch-backend cu121
```

Result: dependency resolution failed on Windows because
`tensorflow-io-gcs-filesystem==0.36.0` has no matching `win_amd64` wheel.

```powershell
uv pip compile external\HSTU-BLaIR\requirements.txt --python-version 3.9 --python-platform x86_64-manylinux2014 --torch-backend auto
```

Result: dependency resolution succeeded for Linux, confirming HSTU-BLaIR should
be reproduced on a Linux/CUDA environment.

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage inspect --run-id hstu_blair_wsl_inspect_20260608
```

Result: WSL2 Ubuntu is available, sees the RTX 5060 Ti, exposes
`fork,spawn,forkserver`, and can access the HSTU-BLaIR source. The mounted
Windows checkout appears dirty from WSL due line-ending behavior, so setup uses
a clean native WSL clone.

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage setup --run-id hstu_blair_wsl_setup_20260608
```

Result: faithful pinned HSTU-BLaIR Linux environment installed with
`torch==2.2.2+cu121` and `fbgemm-gpu==0.6.0+cu121`.

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage smoke --run-id hstu_blair_wsl_smoke_20260608
```

Result: failed for the scientifically important reason that pinned
`torch==2.2.2+cu121` cannot execute CUDA kernels on the RTX 5060 Ti `sm_120`
GPU: `CUDA error: no kernel image is available for execution on the device`.

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage setup-sm120 --run-id hstu_blair_wsl_setup_sm120_20260608

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage smoke-sm120 --run-id hstu_blair_wsl_smoke_sm120_20260608
```

Result: SM120 compatibility environment installed and smoke passed with
`torch==2.8.0+cu128`, `fbgemm-gpu==1.3.0+cu128`, `torchrec==1.4.0+cu128`, CUDA
matmul on the RTX 5060 Ti, and upstream HSTU-BLaIR `main.py` entrypoint checks.
This is a compatibility port, not yet faithful publication evidence.

2026-06-09 wrapper hardening: `_bestrec_sota_lab/run_hstu_blair_wsl_audit.py`
now records per-command timing, post-stage HSTU artifact hashes/sizes, dataset
counts, checkpoint/event-file probes, and parsed upstream `eval @ epoch`
metrics. `py_compile`, WSL `bash -n`, and a representative metric-parser smoke
passed. The artifact-probe dry run also passed and reported native HSTU-BLaIR
commit `40a27879ec22648657b5abc77915a7cc88c66cfd`; dataset counts are empty
because preprocessing had not run yet at that point. HSTU preprocessing/training
was then delayed until the separate tuned SASRec seed `20260612` process
released the GPU.

2026-06-09 follow-up: `preprocess-game-sm120` completed in
`_bestrec_sota_lab/runs/hstu_blair_wsl_preprocess_game_sm120_20260609_r3/`.
The artifact probe recorded `94,762` sequence rows, `25,612` unique items,
`sasrec_format.csv` SHA-256
`5d1977fbae42057f53d849bfb3219100ed5d4285ec64c94b6e14865657addad8`, and
BLaIR embedding shape `[25613, 768]`. The preprocessing stage required a
runtime-only repair of the upstream `saved_name` typo (`Video_Games.csv` ->
`Video_Games.csv.gz`) because the official URL is a gzip archive. No upstream
source file was edited.

2026-06-09 follow-up: `train-game-sm120` completed under
`_bestrec_sota_lab/runs/hstu_blair_wsl_train_game_sm120_20260609/` in
`19,378.391` seconds. The posthoc metric summary is
`_bestrec_sota_lab/runs/hstu_blair_wsl_train_game_sm120_20260609/hstu_blair_posthoc_metric_summary.json`.
Parsed upstream TensorBoard metrics:

- final full eval, epoch 100: NDCG@10 `0.0738224`, HR@10 `0.1323421`,
  MRR `0.0654230`;
- best full eval, epoch 95: NDCG@10 `0.0740335`, HR@10 `0.1320466`,
  MRR `0.0658713`;
- best epoch/partial eval, epoch 68: NDCG@10 `0.0777197`, HR@10 `0.1386719`,
  MRR `0.0687304`.

The run wrote checkpoint SHA-256
`815e7712b6775dce5c79117c76f0a2936a2aef2a4125ed13869707ff0d1a9f7c` and event
file SHA-256
`69e18d8bffc47a1d69ea424969a2ad499e07f252a4a8851c98ebecccb06f65e3`. This is
stronger than SASRec-SBERT but is still a CUDA 12.8 SM120 compatibility-port
result, not faithful pinned upstream evidence. The training log contains fbgemm
autograd-kernel warnings for `dense_to_jagged` and `jagged_to_padded_dense`;
these must be treated as validity caveats unless resolved or justified.

```powershell
..\..\_bestrec_run\.venv\Scripts\python.exe run.py --help
```

Run from `external\liger`. Result: Hydra config printed successfully, but the
default configuration targets Amazon 2014 `Beauty` with RQ-VAE `epochs: 8000`
and TIGER trainer `steps: 200000`, not this AR2023 `Video_Games` protocol.

```powershell
_bestrec_run\.venv\Scripts\python.exe _bestrec_run\compare_beauty_results.py
```

Result: the script completed successfully and ranked the saved Beauty artifacts.
The best saved Beauty result is:

- `_bestrec_run/results_sasrec_blair_richtext_mlp_seed43_Beauty.json`
- NDCG@10 = 0.0195452
- HR@10 = 0.0351396
- MRR = 0.0181366

```powershell
_bestrec_run\.venv\Scripts\python.exe -c "import pypdf; print(pypdf.__version__)"
```

Result: `pypdf 6.10.2`, used for PDF citation/text extraction.

```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader
```

Result: NVIDIA GeForce RTX 5060 Ti, 16,311 MiB total memory.

## Commands Not Re-Run In The Initial Audit

Most long GPU training runs were not started during the initial audit because:

- Existing JSON artifacts already record the historical results.
- The bulletproof plan says not to overwrite existing numeric results or rerun
  experiments that already have JSON outputs.
- A publication-grade rerun must first add per-user records, seed metadata,
  command logging, environment capture, and artifact hashing. The historical
  scripts do not yet satisfy that manifest requirement for every output.

The later HSTU-BLaIR WSL compatibility-port training run is an exception: it
completed on 2026-06-08 UTC and is documented below and in
`EXTERNAL_SOTA_COMPARATOR_AUDIT.md`.

## Existing Saved Results Checked

| Result file | Dataset | NDCG@10 | HR@10 | MRR |
|---|---|---:|---:|---:|
| `_bestrec_run/results_sasrec_sbert_Video_Games_v3.json` | Video_Games | 0.0543478 | 0.0983517 | 0.0489073 |
| `_bestrec_run/results_sasrec_sbert_Video_Games_seed20260522.json` | Video_Games | 0.0497873 | 0.0898672 | 0.0451127 |
| `_bestrec_run/results_sasrec_sbert_Video_Games_seed20260523.json` | Video_Games | 0.0500020 | 0.0906798 | 0.0452239 |
| `_bestrec_run/results_sasrec_blair_Video_Games.json` | Video_Games | 0.0497834 | 0.0900466 | 0.0451320 |
| `_bestrec_run/results_tiger_minimal_Video_Games.json` | Video_Games | 0.0200877 | 0.0380216 | 0.0174863 |
| `_bestrec_run/results_sasrec_chunkedfull_Beauty.json` | Beauty_and_Personal_Care | 0.0191144 | 0.0346393 | 0.0177866 |
| `_bestrec_run/results_sasrec_blair_mlp_drop02_Beauty.json` | Beauty_and_Personal_Care | 0.0192782 | 0.0347202 | 0.0178819 |
| `_bestrec_run/results_sasrec_blair_richtext_mlp_Beauty.json` | Beauty_and_Personal_Care | 0.0193575 | 0.0348038 | 0.0180004 |
| `_bestrec_run/results_sasrec_blair_richtext_mlp_seed43_Beauty.json` | Beauty_and_Personal_Care | 0.0195452 | 0.0351396 | 0.0181366 |
| `_bestrec_run/results_bert4rec_Beauty.json` | Beauty_and_Personal_Care | 0.0159913 | 0.0297077 | 0.0149891 |

## Strict Publication Status

The saved SASRec-SBERT results are useful for drafting and internal audit. They
are not sufficient for a strict final SOTA claim. HSTU-BLaIR is stronger in the
completed compatibility-port run, and neither HSTU-BLaIR nor SASRec-SBERT has
been converted into a shared canonical per-user JSONL comparator package.
