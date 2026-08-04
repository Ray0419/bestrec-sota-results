#!/usr/bin/env bash
# Goal 2: THEIR HSTU-BLaIR on Musical_Instruments, their gin unmodified
# (only Windows dataloader override, recorded in run_meta.json).
set -e
cd "$(dirname "$0")/.."
_bestrec_run/.venv/Scripts/python _bestrec_run/theirs_train.py \
  --gin external/HSTU-BLaIR/configs/amzn23_music/hstu-sampled-softmax-n512-blair.gin \
  --run-name music_hstu_blair \
  --workers0 --port 12412 \
  > _bestrec_run/theirs_runs/music_hstu_blair.log 2>&1
echo "MUSIC_HSTU_BLAIR_EXIT=$?"
