#!/usr/bin/env bash
# MI (Musical_Instruments) tail-contrast MULTI-SEED driver — replicate the VG tail finding on a 2nd dataset.
# seed08 already on disk (text wins tail +0.00032 single-seed — OPPOSITE of VG's tail-negative; tiny ~32-hit bucket => needs multi-seed).
# Existing validated flags only (no new mechanism). ONE GPU job at a time: runs sequentially.
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
PREFIX="$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 1"

for S in 20260609 20260610 20260611 20260612; do
  echo "=================== MI TEXT seed $S ==================="
  $PREFIX --seed $S --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
     --out _bestrec_run/results_MI_TAIL_V2_text_seed${S}.json \
     > _bestrec_run/run_MI_TAIL_V2_text_seed${S}.log 2>&1
  echo "=================== MI ID-ONLY seed $S ==================="
  $PREFIX --seed $S --time-bias --pos-rab --no-sbert \
     --out _bestrec_run/results_MI_TAIL_idonly_seed${S}.json \
     > _bestrec_run/run_MI_TAIL_idonly_seed${S}.log 2>&1
done
echo "ALL MI TAIL MULTISEED RUNS COMPLETE"
