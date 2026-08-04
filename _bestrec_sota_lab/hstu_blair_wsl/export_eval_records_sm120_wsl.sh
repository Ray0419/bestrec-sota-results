#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
WORKSPACE_ROOT="${BESTREC_WORKSPACE_ROOT:-/mnt/c/Users/rayxc/Documents/R}"
RUN_ID="${HSTU_EXPORT_RUN_ID:-hstu_blair_eval_export_sm120_$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${HSTU_EXPORT_OUT_DIR:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/$RUN_ID}"
CHECKPOINT="${HSTU_EXPORT_CHECKPOINT:-$SRC/ckpts/amzn23_game-l50/HSTU-b4-h4-dqk16-dv16-lsilud0.5-ad0.0_blair_DotProduct_local_text-l2-eps1e-06_ssl-t0.05-n512-b128-lr0.001-wu0-wd0-2026-06-09-fe5_ep100}"
LIMIT_BATCHES="${HSTU_EXPORT_LIMIT_BATCHES:-0}"
TEACHER_TOP_K="${HSTU_EXPORT_TEACHER_TOP_K:-0}"

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "SM120 environment missing: $ENV_DIR" >&2
  exit 2
fi

cd "$SRC"
test -f "$CHECKPOINT"
test -f tmp/amzn23_game/sasrec_format.csv
test -f tmp/amzn23_game/item_text_embeddings_blair.pt
mkdir -p "$OUT_DIR"

export PYTHONPATH="$SRC:${PYTHONPATH:-}"
"$ENV_DIR/bin/python" "$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl/export_hstu_eval_records.py" \
  --checkpoint "$CHECKPOINT" \
  --out-jsonl "$OUT_DIR/warm_full_catalog_records_Video_Games_hstu_blair_sm120.jsonl" \
  --summary-json "$OUT_DIR/hstu_blair_eval_export_summary.json" \
  --gin-config-file configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin \
  --limit-batches "$LIMIT_BATCHES" \
  --teacher-top-k "$TEACHER_TOP_K"

echo "HSTU-BLaIR eval export complete: $OUT_DIR"
