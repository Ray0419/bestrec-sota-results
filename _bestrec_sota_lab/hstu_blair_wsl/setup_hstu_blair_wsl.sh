#!/usr/bin/env bash
set -euo pipefail

ROOT="${BESTREC_ROOT:-/mnt/c/Users/rayxc/Documents/R}"
WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_ENV_DIR:-$WORK_DIR/venv_py39}"
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
  echo "Cloning HSTU-BLaIR into native WSL storage: $SRC"
  git clone "$HSTU_BLAIR_REPO" "$SRC"
fi

echo "Checking out HSTU-BLaIR ref: $HSTU_BLAIR_REF"
git -C "$SRC" fetch --tags --quiet origin || true
git -C "$SRC" checkout --quiet "$HSTU_BLAIR_REF"

if [[ -n "$(git -C "$SRC" status --short)" ]]; then
  echo "Native WSL HSTU-BLaIR clone is dirty; refusing setup." >&2
  git -C "$SRC" status --short >&2
  exit 4
fi

if [[ ! -x "$UV_BIN" ]]; then
  echo "Installing uv inside WSL..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

echo "uv version:"
uv --version

echo "Installing Python $PYTHON_VERSION with uv if needed..."
uv python install "$PYTHON_VERSION"

if [[ -x "$ENV_DIR/bin/python" ]]; then
  echo "Reusing existing virtual environment: $ENV_DIR"
else
  echo "Creating virtual environment: $ENV_DIR"
  uv venv --python "$PYTHON_VERSION" "$ENV_DIR"
fi

echo "Installing HSTU-BLaIR requirements..."
uv pip install --python "$ENV_DIR/bin/python" -r "$SRC/requirements.txt" --torch-backend auto

echo "Verifying core imports..."
"$ENV_DIR/bin/python" - <<'PY'
import importlib
import sys

import torch

print("python", sys.version)
print("torch", torch.__version__, "cuda_available", torch.cuda.is_available(), "cuda", torch.version.cuda)
for name in ["fbgemm_gpu", "gin", "tensorflow", "transformers"]:
    mod = importlib.import_module(name)
    print(name, getattr(mod, "__version__", "imported"))
PY

echo "HSTU-BLaIR WSL setup complete."
