# HSTU-BLaIR WSL Reproduction Lane

This directory is the isolated reproduction lane for the external HSTU-BLaIR
comparator. It exists because the Windows Python environment cannot run the
upstream HSTU-BLaIR stack: the dependency set is Linux-oriented, and the code
uses Linux multiprocessing plus CUDA operator paths.

The goal is not to make a proxy. The goal is to reproduce the official
HSTU-BLaIR code on Linux/WSL with GPU visibility, then either:

- import protocol-matched full-catalog records into the SOTA lab, or
- keep publication/SOTA claims blocked with exact failure evidence.

## Inspect

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage inspect --run-id hstu_blair_wsl_inspect
```

## Setup

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage setup --run-id hstu_blair_wsl_setup
```

This installs `uv` inside WSL if needed, creates a clean native-Linux clone of
HSTU-BLaIR under `~/.bestrec_hstu_blair/HSTU-BLaIR`, creates a Python 3.9
virtual environment under WSL home, and installs the upstream HSTU-BLaIR
requirements.

## Smoke

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage smoke --run-id hstu_blair_wsl_smoke
```

Smoke checks imports, CUDA visibility, the upstream entrypoint, and the exact
published config path. It does not run full training.

## RTX 5060 Ti / SM120 Compatibility Port

The faithful pinned upstream environment installs `torch==2.2.2+cu121`, which
does not support the RTX 5060 Ti `sm_120` GPU. The compatibility port keeps the
same HSTU-BLaIR source commit but replaces the torch stack with CUDA 12.8
wheels. This is not a faithful reproduction until separately justified; it is a
practical route to execute the model on this machine.

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage setup-sm120 --run-id hstu_blair_wsl_setup_sm120

uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage smoke-sm120 --run-id hstu_blair_wsl_smoke_sm120
```

After SM120 smoke passes, run only the `Video_Games`/`amzn23_game` preprocessing:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage preprocess-game-sm120 --run-id hstu_blair_wsl_preprocess_game_sm120 --timeout 21600
```

Then run upstream HSTU-BLaIR training:

```powershell
uv --project _bestrec_run run python _bestrec_sota_lab/run_hstu_blair_wsl_audit.py --stage train-game-sm120 --run-id hstu_blair_wsl_train_game_sm120 --timeout 86400
```

The audit wrapper writes `_bestrec_sota_lab/runs/<run_id>/hstu_blair_wsl_audit.json`.
For preprocessing/training stages it also records HSTU-BLaIR source status,
dataset artifact hashes/sizes, available checkpoints and TensorBoard event
files, and parsed upstream `eval @ epoch` metrics. These parsed metrics are
upstream-protocol evidence only; publication-grade BEST-Rec claims still need
canonical per-user JSONL records or a documented protocol-mismatch decision.

## Full Upstream Reproduction

After setup and smoke pass, the equivalent manual upstream commands are:

```bash
cd ~/.bestrec_hstu_blair/HSTU-BLaIR
source ~/.bestrec_hstu_blair/venv_py39/bin/activate
mkdir -p tmp
python - <<'PY'
from generative_recommenders.research.data.preprocessor import get_common_preprocessors
get_common_preprocessors(text_embedding_model="blair")["amzn23_game"].preprocess_rating()
PY
CUDA_VISIBLE_DEVICES=0 python main.py --gin_config_file=configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin --master_port=12345
```

This is expected to be expensive. A broad SOTA claim remains blocked until the
result is converted to canonical per-user JSONL records under the exact
BEST-Rec protocol or the protocol mismatch is formally justified.
