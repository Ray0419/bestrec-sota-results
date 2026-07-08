#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${BESTREC_WORKSPACE_ROOT:-/mnt/c/Users/rayxc/Documents/R}"
WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
RUN_ID="${HSTU_ITEM_MAP_RUN_ID:-hstu_item_alignment_20260609}"
OUT_DIR="${HSTU_ITEM_MAP_OUT_DIR:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/$RUN_ID}"

cd "$SRC"
source "$ENV_DIR/bin/activate"
mkdir -p "$OUT_DIR"

python "$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl/build_hstu_bestrec_item_map.py" \
  --hstu-data-maps "$SRC/tmp/amzn23_game/data_maps" \
  --bestrec-asin2idx "$WORKSPACE_ROOT/cache_5core/asin2idx_Video_Games.json" \
  --out "$OUT_DIR/hstu_bestrec_item_map.json"

echo "HSTU/BEST-Rec item map complete: $OUT_DIR/hstu_bestrec_item_map.json"
