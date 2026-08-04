#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${BESTREC_WORKSPACE_ROOT:-/mnt/c/Users/rayxc/Documents/R}"
WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
RUN_ID="${HSTU_STRICT_RUN_ID:-hstu_strict_smoke_$(date +%Y%m%d_%H%M%S)}"
STRICT_DATA_DIR="${HSTU_STRICT_DATA_DIR:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609}"
OUT_DIR="${HSTU_STRICT_OUT_DIR:-$WORKSPACE_ROOT/_bestrec_sota_lab/runs/$RUN_ID}"

EPOCHS="${HSTU_STRICT_EPOCHS:-1}"
EVAL_EVERY="${HSTU_STRICT_EVAL_EVERY:-1}"
MAX_TRAIN_BATCHES="${HSTU_STRICT_MAX_TRAIN_BATCHES:-1}"
MAX_EVAL_BATCHES="${HSTU_STRICT_MAX_EVAL_BATCHES:-1}"
SEED="${HSTU_STRICT_SEED:-20260701}"
LEARNING_RATE="${HSTU_STRICT_LEARNING_RATE:-0.001}"
WEIGHT_DECAY="${HSTU_STRICT_WEIGHT_DECAY:-0.0}"
DROPOUT_RATE="${HSTU_STRICT_DROPOUT_RATE:-0.5}"
TEMPERATURE="${HSTU_STRICT_TEMPERATURE:-0.05}"
NUM_NEGATIVES="${HSTU_STRICT_NUM_NEGATIVES:-512}"
ITEM_EMBEDDING_DIM="${HSTU_STRICT_ITEM_EMBEDDING_DIM:-64}"
HSTU_LINEAR_DROPOUT_RATE="${HSTU_STRICT_HSTU_LINEAR_DROPOUT_RATE:-}"
HSTU_ATTN_DROPOUT_RATE="${HSTU_STRICT_HSTU_ATTN_DROPOUT_RATE:-}"
HSTU_NUM_BLOCKS="${HSTU_STRICT_HSTU_NUM_BLOCKS:-}"
HSTU_NUM_HEADS="${HSTU_STRICT_HSTU_NUM_HEADS:-}"
HSTU_DV="${HSTU_STRICT_HSTU_DV:-}"
HSTU_DQK="${HSTU_STRICT_HSTU_DQK:-}"
RESUME_CHECKPOINT="${HSTU_STRICT_RESUME_CHECKPOINT:-}"
BATCH_SIZE="${HSTU_STRICT_BATCH_SIZE:-128}"
EVAL_BATCH_SIZE="${HSTU_STRICT_EVAL_BATCH_SIZE:-128}"

EXTRA_ARGS=()
if [[ -n "$HSTU_LINEAR_DROPOUT_RATE" ]]; then
  EXTRA_ARGS+=(--hstu-linear-dropout-rate "$HSTU_LINEAR_DROPOUT_RATE")
fi
if [[ -n "$HSTU_ATTN_DROPOUT_RATE" ]]; then
  EXTRA_ARGS+=(--hstu-attn-dropout-rate "$HSTU_ATTN_DROPOUT_RATE")
fi
if [[ -n "$HSTU_NUM_BLOCKS" ]]; then
  EXTRA_ARGS+=(--hstu-num-blocks "$HSTU_NUM_BLOCKS")
fi
if [[ -n "$HSTU_NUM_HEADS" ]]; then
  EXTRA_ARGS+=(--hstu-num-heads "$HSTU_NUM_HEADS")
fi
if [[ -n "$HSTU_DV" ]]; then
  EXTRA_ARGS+=(--hstu-dv "$HSTU_DV")
fi
if [[ -n "$HSTU_DQK" ]]; then
  EXTRA_ARGS+=(--hstu-dqk "$HSTU_DQK")
fi
if [[ -n "$RESUME_CHECKPOINT" ]]; then
  EXTRA_ARGS+=(--resume-checkpoint "$RESUME_CHECKPOINT")
fi

cd "$SRC"
source "$ENV_DIR/bin/activate"
mkdir -p "$OUT_DIR"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

python "$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120.py" \
  --train-csv "$STRICT_DATA_DIR/sasrec_format_train_strict.csv" \
  --valid-csv "$STRICT_DATA_DIR/sasrec_format_valid_strict.csv" \
  --test-csv "$STRICT_DATA_DIR/sasrec_format_test_strict.csv" \
  --out-dir "$OUT_DIR" \
  --run-id "$RUN_ID" \
  --gin-config-file "$SRC/configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin" \
  --text-embeddings "$SRC/tmp/amzn23_game/item_text_embeddings_blair.pt" \
  --epochs "$EPOCHS" \
  --eval-every "$EVAL_EVERY" \
  --max-train-batches "$MAX_TRAIN_BATCHES" \
  --max-eval-batches "$MAX_EVAL_BATCHES" \
  --learning-rate "$LEARNING_RATE" \
  --weight-decay "$WEIGHT_DECAY" \
  --dropout-rate "$DROPOUT_RATE" \
  --temperature "$TEMPERATURE" \
  --num-negatives "$NUM_NEGATIVES" \
  --item-embedding-dim "$ITEM_EMBEDDING_DIM" \
  --batch-size "$BATCH_SIZE" \
  --eval-batch-size "$EVAL_BATCH_SIZE" \
  --seed "$SEED" \
  "${EXTRA_ARGS[@]}"

echo "Strict HSTU train lane complete: $OUT_DIR"
