#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"
PYTHON_VERSION="${HSTU_BLAIR_PYTHON_VERSION:-3.9.25}"
HSTU_BLAIR_REPO="${HSTU_BLAIR_REPO:-https://github.com/snapfinger/HSTU-BLaIR.git}"
HSTU_BLAIR_REF="${HSTU_BLAIR_REF:-40a27879ec22648657b5abc77915a7cc88c66cfd}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi is not visible inside WSL; CUDA reproduction cannot start." >&2
  exit 3
fi

mkdir -p "$WORK_DIR"

if [[ ! -d "$SRC/.git" ]]; then
  git clone "$HSTU_BLAIR_REPO" "$SRC"
fi
git -C "$SRC" fetch --tags --quiet origin || true
git -C "$SRC" checkout --quiet "$HSTU_BLAIR_REF"
if [[ -n "$(git -C "$SRC" status --short)" ]]; then
  echo "Native WSL HSTU-BLaIR clone is dirty; refusing setup." >&2
  git -C "$SRC" status --short >&2
  exit 4
fi

if [[ ! -x "$UV_BIN" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

uv python install "$PYTHON_VERSION"

if [[ -x "$ENV_DIR/bin/python" ]]; then
  echo "Reusing existing SM120 compatibility environment: $ENV_DIR"
else
  echo "Creating SM120 compatibility environment: $ENV_DIR"
  uv venv --python "$PYTHON_VERSION" "$ENV_DIR"
fi

FILTERED_REQ="$WORK_DIR/requirements_without_torch_stack.txt"
grep -Ev '^(torch|torchrec|fbgemm[-_]gpu)==' "$SRC/requirements.txt" > "$FILTERED_REQ"

echo "Installing HSTU-BLaIR non-torch requirements..."
uv pip install --python "$ENV_DIR/bin/python" -r "$FILTERED_REQ" --torch-backend auto

echo "Installing SM120-compatible CUDA 12.8 torch stack..."
uv pip install --python "$ENV_DIR/bin/python" \
  "torch==2.8.0" \
  "fbgemm-gpu==1.3.0" \
  "torchrec==1.4.0" \
  --torch-backend cu128

"$ENV_DIR/bin/python" - <<'PY'
import importlib
import sys

import torch

print("python", sys.version)
print("torch", torch.__version__, "cuda_available", torch.cuda.is_available(), "cuda", torch.version.cuda)
print("cuda_device", torch.cuda.get_device_name(0), "capability", torch.cuda.get_device_capability(0))
x = torch.ones((2, 2), device="cuda")
y = x @ x
torch.cuda.synchronize()
print("cuda_matmul", y.detach().cpu().tolist())
for name in ["fbgemm_gpu", "torchrec", "gin", "tensorflow", "transformers"]:
    mod = importlib.import_module(name)
    print(name, getattr(mod, "__version__", "imported"))
PY

echo "HSTU-BLaIR SM120 compatibility setup complete."
