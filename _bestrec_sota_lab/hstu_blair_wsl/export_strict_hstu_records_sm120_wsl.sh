#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${BESTREC_WORKSPACE_ROOT:-/mnt/c/Users/rayxc/Documents/R}"
WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
RUN_ID="${HSTU_STRICT_EXPORT_RUN_ID:-hstu_strict_export_smoke_$(date +%Y%m%d_%H%M%S)}"
STRICT_DATA_DIR="${HSTU_STRICT_DATA_DIR:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609}"
OUT_DIR="${HSTU_STRICT_EXPORT_OUT_DIR:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/$RUN_ID}"
CHECKPOINT="${HSTU_STRICT_CHECKPOINT:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/hstu_strict_smoke_20260609/strict_hstu_best_valid.pt}"
SPLIT="${HSTU_STRICT_EXPORT_SPLIT:-test}"
MAX_EVAL_BATCHES="${HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES:-1}"
TEACHER_TOP_K="${HSTU_STRICT_EXPORT_TEACHER_TOP_K:-50}"

case "$SPLIT" in
  valid) CSV="$STRICT_DATA_DIR/sasrec_format_valid_strict.csv" ;;
  test) CSV="$STRICT_DATA_DIR/sasrec_format_test_strict.csv" ;;
  *) echo "Unsupported HSTU_STRICT_EXPORT_SPLIT=$SPLIT" >&2; exit 2 ;;
esac

cd "$SRC"
source "$ENV_DIR/bin/activate"
mkdir -p "$OUT_DIR"
export PYTHONPATH="$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl:$SRC:${PYTHONPATH:-}"

python "$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records.py" \
  --checkpoint "$CHECKPOINT" \
  --csv "$CSV" \
  --split "$SPLIT" \
  --out-jsonl "$OUT_DIR/warm_full_catalog_records_Video_Games_strict_hstu_${SPLIT}.jsonl" \
  --summary-json "$OUT_DIR/strict_hstu_export_${SPLIT}_summary.json" \
  --gin-config-file "$SRC/configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin" \
  --text-embeddings "$SRC/tmp/amzn23_game/item_text_embeddings_blair.pt" \
  --max-eval-batches "$MAX_EVAL_BATCHES" \
  --teacher-top-k "$TEACHER_TOP_K"

echo "Strict HSTU export complete: $OUT_DIR"
