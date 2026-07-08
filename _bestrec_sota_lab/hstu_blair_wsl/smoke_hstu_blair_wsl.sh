#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_ENV_DIR:-$WORK_DIR/venv_py39}"

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "HSTU-BLaIR environment missing: $ENV_DIR" >&2
  echo "Run setup_hstu_blair_wsl.sh first." >&2
  exit 2
fi

cd "$SRC"
if [[ -n "$(git status --short)" ]]; then
  echo "Native WSL HSTU-BLaIR clone is dirty; refusing smoke." >&2
  git status --short >&2
  exit 3
fi
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

"$ENV_DIR/bin/python" - <<'PY'
import multiprocessing as mp
import sys

import fbgemm_gpu  # noqa: F401
import gin
import torch

print("python", sys.version)
print("multiprocessing_methods", mp.get_all_start_methods())
print("torch", torch.__version__, "cuda_available", torch.cuda.is_available(), "cuda_count", torch.cuda.device_count())
print("gin", getattr(gin, "__version__", "imported"))

if "forkserver" not in mp.get_all_start_methods():
    raise SystemExit("forkserver unavailable; upstream main.py requires it")
if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
    raise SystemExit("CUDA device unavailable inside WSL")
device_name = torch.cuda.get_device_name(0)
capability = torch.cuda.get_device_capability(0)
print("cuda_device", device_name, "capability", capability)
try:
    x = torch.ones((2, 2), device="cuda")
    y = x @ x
    torch.cuda.synchronize()
    print("cuda_matmul", y.detach().cpu().tolist())
except Exception as exc:
    raise SystemExit(f"CUDA execution failed under pinned HSTU torch: {type(exc).__name__}: {exc}") from exc
PY

"$ENV_DIR/bin/python" main.py --help >/tmp/hstu_blair_main_help.txt 2>&1 || true
if ! grep -q -- "--gin_config_file" /tmp/hstu_blair_main_help.txt; then
  cat /tmp/hstu_blair_main_help.txt
  echo "main.py help did not expose --gin_config_file" >&2
  exit 4
fi

test -f configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin
echo "HSTU-BLaIR WSL smoke passed."
