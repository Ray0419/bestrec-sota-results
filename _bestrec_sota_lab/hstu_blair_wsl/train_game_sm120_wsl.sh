#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"
MASTER_PORT="${HSTU_BLAIR_MASTER_PORT:-12345}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export CUDA_VISIBLE_DEVICES

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "SM120 environment missing: $ENV_DIR" >&2
  exit 2
fi

cd "$SRC"
SOURCE_STATUS="$(git status --short -- . ':(exclude)tmp' ':(exclude)exps' ':(exclude)ckpts')"
if [[ -n "$SOURCE_STATUS" ]]; then
  echo "Native WSL HSTU-BLaIR source/config files are dirty; refusing training." >&2
  echo "$SOURCE_STATUS" >&2
  exit 3
fi

test -f tmp/amzn23_game/sasrec_format.csv
test -f tmp/amzn23_game/item_text_embeddings_blair.pt

export PYTHONPATH="$SRC:${PYTHONPATH:-}"
"$ENV_DIR/bin/python" main.py \
  --gin_config_file=configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin \
  --master_port="$MASTER_PORT"
