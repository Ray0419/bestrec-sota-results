#!/bin/bash
cd /c/Users/rayxc/Documents/R
BASE="--epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --text-prototypes 512 --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10"
PY="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games"

echo "=== LOO drop time-bias ==="
$PY $BASE --text-sim-bias --pos-rab --out _bestrec_run/results_ABL_no_timebias_VG.json > _bestrec_run/run_ABL_no_timebias_VG.log 2>&1
echo "=== LOO drop text-sim-bias ==="
$PY $BASE --time-bias --pos-rab --out _bestrec_run/results_ABL_no_textsim_VG.json > _bestrec_run/run_ABL_no_textsim_VG.log 2>&1
echo "=== LOO drop pos-rab ==="
$PY $BASE --time-bias --text-sim-bias --out _bestrec_run/results_ABL_no_posrab_VG.json > _bestrec_run/run_ABL_no_posrab_VG.log 2>&1
echo "=== LOO ABLATION BATCH DONE ==="
