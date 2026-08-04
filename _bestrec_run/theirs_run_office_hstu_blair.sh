#!/usr/bin/env bash
# Stretch goal: THEIR HSTU-BLaIR on Office_Products (published NDCG@10 .0271)
set -e
cd "$(dirname "$0")/.."
_bestrec_run/.venv/Scripts/python _bestrec_run/theirs_train.py \
  --gin external/HSTU-BLaIR/configs/amzn23_office/hstu-sampled-softmax-n512-blair.gin \
  --run-name office_hstu_blair \
  --workers0 --port 12413 \
  > _bestrec_run/theirs_runs/office_hstu_blair.log 2>&1
echo "OFFICE_HSTU_BLAIR_EXIT=$?"
