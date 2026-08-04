#!/usr/bin/env bash
# Kriging nugget-robustness sweep (SUPERVISOR cycle-19 CONTINUE directive).
# MI single-seed 20260608, HSTU, bit-identical to results_KRIGE_cold_hstu_MI_seed20260608.json
# except --krige-nugget in {0.001, 0.05, 0.1}. ONE GPU job at a time (sequential).
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
COMMON="Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --cold-item-frac 0.15 --cold-item-seed 1 --cold-synth-knn 20 --cold-synth-temp 0.07 --krige-cold --eval-every 10"

run_one () {
  local NUG=$1 TAG=$2
  echo "=== KRIGENUG sweep: nugget=$NUG -> $TAG ==="
  $PY -u _bestrec_run/run_sasrec_sbert.py $COMMON --krige-nugget $NUG \
    --out _bestrec_run/results_KRIGENUG_${TAG}_MI_seed20260608.json \
    > _bestrec_run/run_KRIGENUG_${TAG}_MI_seed20260608.log 2>&1
  echo "=== done nugget=$NUG ==="
}

run_one 0.001 0p001
run_one 0.05  0p05
run_one 0.1   0p1
echo "=== KRIGENUG SWEEP COMPLETE ==="
