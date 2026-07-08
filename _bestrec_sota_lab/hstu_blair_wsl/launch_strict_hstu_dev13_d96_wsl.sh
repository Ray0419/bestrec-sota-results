#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${BESTREC_WORKSPACE_ROOT:-/mnt/c/Users/rayxc/Documents/R}"
RUN_ID="hstu_strict_dev13_d96_l4h4_epoch60_dropout03_20260609"
OUT_DIR="$WORKSPACE_ROOT/_bestrec_sota_lab/runs/$RUN_ID"
mkdir -p "$OUT_DIR"

export HSTU_STRICT_RUN_ID="$RUN_ID"
export HSTU_STRICT_EPOCHS=60
export HSTU_STRICT_MAX_TRAIN_BATCHES=0
export HSTU_STRICT_MAX_EVAL_BATCHES=0
export HSTU_STRICT_EVAL_EVERY=1
export HSTU_STRICT_DROPOUT_RATE=0.3
export HSTU_STRICT_ITEM_EMBEDDING_DIM=96
export HSTU_STRICT_HSTU_NUM_BLOCKS=4
export HSTU_STRICT_HSTU_NUM_HEADS=4
export HSTU_STRICT_HSTU_DV=24
export HSTU_STRICT_HSTU_DQK=24
export HSTU_STRICT_BATCH_SIZE=128
export HSTU_STRICT_EVAL_BATCH_SIZE=128

{
  echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  bash "$WORKSPACE_ROOT/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh"
  echo "finished_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$OUT_DIR/nohup.log" 2>&1
