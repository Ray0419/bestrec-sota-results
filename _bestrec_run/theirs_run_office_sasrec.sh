#!/usr/bin/env bash
# Goal 1: THEIR SASRec baseline on Office_Products, their gin unmodified
# (only Windows dataloader override, recorded in run_meta.json).
set -e
cd "$(dirname "$0")/.."
_bestrec_run/.venv/Scripts/python _bestrec_run/theirs_train.py \
  --gin external/HSTU-BLaIR/configs/amzn23_office/sasrec-sampled-softmax-n512-final.gin \
  --run-name office_sasrec_final \
  --workers0 --port 12411 \
  > _bestrec_run/theirs_runs/office_sasrec_final.log 2>&1
echo "OFFICE_SASREC_EXIT=$?"
