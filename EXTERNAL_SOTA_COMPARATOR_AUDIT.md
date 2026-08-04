# External SOTA Comparator Audit

**Audit date:** 2026-06-08  
**Workspace:** `C:\Users\rayxc\Documents\R`  
**Primary local run:** `_bestrec_confirmatory_sasrec/video_games_sasrec_confirmatory_20260608_5seed/`

## Bottom Line

The fresh SASRec-SBERT confirmatory package is real, reproducible, and internally
significant against the same-run SASRec ablations. It is **not** enough to claim
unqualified SOTA.

The strict blocker is HSTU-BLaIR: the upstream repository reports
`Video Games` NDCG@10 = `0.0760`, while our fresh 5-seed SASRec-SBERT mean is
`0.0550927`. Our completed SM120 compatibility-port HSTU-BLaIR run is also
stronger than SASRec-SBERT, with final full-eval NDCG@10 `0.0738224` and best
full-eval NDCG@10 `0.0740335`. Unless our method beats this reference, or a
faithful pinned-environment audit proves it is not comparable, a broad SOTA
claim would be false.

## Same-Run Confirmatory Comparators

All three methods were run under the same script, splits, full-catalog candidate
scope, seeds, and per-user record schema.

| Method | Seeds | Mean NDCG@10 | Std | Records |
|---|---:|---:|---:|---:|
| `sasrec_sbert` | 5 | 0.0550927 | 0.0003452 | 473,810 |
| `sasrec_blair` | 5 | 0.0545244 | 0.0007472 | 473,810 |
| `sasrec_no_sbert` | 5 | 0.0509659 | 0.0006818 | 473,810 |

Paired per-user/per-seed Wilcoxon tests:

| Comparison | Mean delta NDCG@10 | P-value | Holm p-value |
|---|---:|---:|---:|
| `sasrec_sbert` > `sasrec_blair` | 0.0005682 | 0.0311053 | 0.0311053 |
| `sasrec_sbert` > `sasrec_no_sbert` | 0.0041268 | 5.28049e-32 | 1.05610e-31 |

This supports a narrow claim: under this implementation and this split,
SASRec-SBERT beats the same-run BLaIR-encoder swap and no-text SASRec ablation.
It does not prove overall recommender SOTA.

## HSTU-BLaIR Check

Source cloned locally:

```powershell
git clone https://github.com/snapfinger/HSTU-BLaIR external\HSTU-BLaIR
```

Relevant upstream facts from the README:

- Tested environment: Ubuntu 22.04, Python 3.9, CUDA 12.6, single NVIDIA RTX
  4090 GPU.
- Dependencies include `torch==2.2.2`, `torchrec==1.1.0`, and
  `fbgemm_gpu==0.6.0`.
- Reported `Video Games` result: HSTU-BLaIR NDCG@10 = `0.0760`.

Local feasibility checks:

```powershell
_bestrec_run\.venv\Scripts\python.exe external\HSTU-BLaIR\main.py --help
```

Result:

```text
ModuleNotFoundError: No module named 'fbgemm_gpu'
```

```powershell
@'
import multiprocessing as mp
print(mp.get_all_start_methods())
'@ | _bestrec_run\.venv\Scripts\python.exe -
```

Result: Windows exposes only `spawn`; HSTU-BLaIR hard-codes
`mp.set_start_method("forkserver")`.

The code also imports CUDA-only custom operator paths and asserts CUDA tensors
inside HSTU attention/layer-norm operators. This is not a fair local rejection
of HSTU-BLaIR; it is a reproducibility blocker for this Windows package.

Dependency dry-run:

```powershell
uv pip compile external\HSTU-BLaIR\requirements.txt --python-version 3.9 --python-platform x86_64-pc-windows-msvc --torch-backend cu121
```

Result: unsatisfiable on Windows because `tensorflow-io-gcs-filesystem==0.36.0`
has no matching `win_amd64` wheel.

```powershell
uv pip compile external\HSTU-BLaIR\requirements.txt --python-version 3.9 --python-platform x86_64-manylinux2014 --torch-backend auto
```

Result: resolves for Linux with `torch==2.2.2+cu121`,
`fbgemm-gpu==0.6.0+cu121`, and `torchrec==1.1.0+cpu`. This confirms the next
honest reproduction step is a Linux/CUDA environment, not this Windows run.

WSL repair progress on 2026-06-08:

- WSL2 Ubuntu sees the RTX 5060 Ti and exposes Linux multiprocessing
  `forkserver`.
- A clean native WSL HSTU-BLaIR clone was created at
  `~/.bestrec_hstu_blair/HSTU-BLaIR`, commit
  `40a27879ec22648657b5abc77915a7cc88c66cfd`.
- The faithful pinned environment installed under
  `~/.bestrec_hstu_blair/venv_py39`.
- Faithful pinned smoke failed because `torch==2.2.2+cu121` cannot execute CUDA
  kernels on this RTX 5060 Ti `sm_120` GPU.
- A separate, explicitly non-faithful SM120 compatibility environment installed
  under `~/.bestrec_hstu_blair/venv_py39_sm120` with `torch==2.8.0+cu128`,
  `fbgemm-gpu==1.3.0+cu128`, and `torchrec==1.4.0+cu128`.
- SM120 smoke passed CUDA execution and upstream `main.py` entrypoint checks.
- On 2026-06-09 the WSL audit wrapper was hardened for the long run: it now
  records command timing, probes HSTU-BLaIR dataset/checkpoint/event-file
  hashes after preprocessing/training, and parses upstream `eval @ epoch`
  metrics into `reported_metric_from_stdout`. These parsed metrics remain
  upstream-protocol evidence only, not canonical BEST-Rec JSONL records.
- The new artifact probe passed in dry mode before preprocessing; it verified
  native HSTU-BLaIR commit `40a27879ec22648657b5abc77915a7cc88c66cfd` and
  correctly found no processed `amzn23_game` dataset counts yet.
- HSTU-BLaIR `preprocess-game-sm120` completed on 2026-06-09 in
  `_bestrec_sota_lab/runs/hstu_blair_wsl_preprocess_game_sm120_20260609_r3/`.
  The audited processed dataset has `94,762` sequence rows, `25,612` unique
  sequence items, and BLaIR embeddings with shape `[25613, 768]`. The wrapper
  applied a runtime-only repair for the upstream gzip filename typo
  (`Video_Games.csv` -> `Video_Games.csv.gz`) without editing source files.
- Full `train-game-sm120` completed in
  `_bestrec_sota_lab/runs/hstu_blair_wsl_train_game_sm120_20260609/`.
  The run wrote an epoch-100 checkpoint and TensorBoard event file. Parsed
  upstream-protocol metrics are:
  - final full eval, epoch 100: NDCG@10 `0.0738224`, HR@10 `0.1323421`,
    MRR `0.0654230`;
  - best full eval, epoch 95: NDCG@10 `0.0740335`, HR@10 `0.1320466`,
    MRR `0.0658713`;
  - best epoch/partial eval, epoch 68: NDCG@10 `0.0777197`, HR@10
    `0.1386719`, MRR `0.0687304`.
  The final/best full-eval values do not exactly reproduce the upstream README
  `0.0760`, but they are far above the SASRec-SBERT 5-seed mean `0.0550927`.
  The run therefore still blocks any broad SASRec-SBERT SOTA claim.
- The completed run remains a compatibility-port result, not faithful upstream
  publication evidence. Logs show fbgemm autograd-kernel warnings from the CUDA
  12.8 compatibility stack, and metrics are parsed from upstream TensorBoard
  event files rather than canonical BEST-Rec per-user JSONL records.

Audit artifacts:

- `_bestrec_sota_lab/runs/hstu_blair_wsl_setup_20260608/hstu_blair_wsl_audit.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_smoke_20260608/hstu_blair_wsl_audit.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_setup_sm120_20260608/hstu_blair_wsl_audit.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_smoke_sm120_20260608/hstu_blair_wsl_audit.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_preprocess_game_sm120_20260609_r3/hstu_blair_wsl_audit.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_train_game_sm120_20260609/hstu_blair_wsl_audit.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_train_game_sm120_20260609/hstu_blair_posthoc_metric_summary.json`
- `_bestrec_sota_lab/runs/hstu_blair_wsl_train_game_sm120_20260609/HSTU_BLAIR_POSTHOC_SUMMARY.md`

This still does not authorize a SASRec-SBERT SOTA claim. It upgrades the
blocker from "unreproduced stronger external report" to "completed stronger
compatibility-port external comparator evidence, with validity caveats."

## TIGER/LIGER Check

Local checkout:

```text
external/liger/
```

The provided scripts run:

- `Beauty`
- `Toys_and_Games`
- `Sports_and_Outdoors`
- `steam`

The Amazon preprocessing URLs are the older SNAP Amazon productGraph 5-core
files, not the Amazon Reviews 2023 `Video_Games` split used by our current
confirmatory run. The LIGER environment also trains RQ-VAE semantic IDs and a
TIGER/LIGER model for up to 200,000 steps, so a protocol-matched run is a real
adaptation project, not a quick command rerun.

Entrypoint smoke check:

```powershell
..\..\_bestrec_run\.venv\Scripts\python.exe run.py --help
```

Result: Hydra help prints successfully, but the default config is still
`dataset.name: Beauty`, `content_model: sentence-t5-xxl`, RQ-VAE `epochs: 8000`,
and TIGER trainer `steps: 200000`.

## Strict Reviewer Verdict

I would **reject** any paper that says SASRec-SBERT is broad SOTA today.

I would allow a guarded internal/workshop claim:

> On our Amazon Reviews 2023 `Video_Games` 5-core leave-last-out full-catalog
> protocol, SASRec-SBERT achieves `0.0550927 +/- 0.0003452` NDCG@10 across five
> fresh seeds and significantly beats same-run SASRec-BLaIR and no-text SASRec
> ablations.

The manuscript must not claim SASRec-SBERT SOTA. HSTU-BLaIR is stronger in the
completed compatibility-port run and in the upstream README. A future paper can
use the SASRec-SBERT result only as a reproducibility/ablation baseline unless a
new method beats HSTU-BLaIR under a protocol-matched, publication-grade audit.
