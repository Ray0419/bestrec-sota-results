#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
WORKSPACE_ROOT="${BESTREC_WORKSPACE_ROOT:-/mnt/c/Users/rayxc/Documents/R}"

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "SM120 environment missing: $ENV_DIR" >&2
  exit 2
fi

cd "$SRC"
"$ENV_DIR/bin/python" "$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl/audit_hstu_item_alignment.py"
