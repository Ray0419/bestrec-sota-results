#!/bin/bash
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --eval-every 10"
echo "=== DECOMP +time-bias ==="
$PRE --time-bias --out _bestrec_run/results_DECOMP_timebias_VG.json > _bestrec_run/run_DECOMP_timebias_VG.log 2>&1
echo "=== DECOMP +text-sim-bias ==="
$PRE --text-sim-bias --out _bestrec_run/results_DECOMP_textsim_VG.json > _bestrec_run/run_DECOMP_textsim_VG.log 2>&1
echo "=== DECOMP +pos-rab ==="
$PRE --pos-rab --out _bestrec_run/results_DECOMP_posrab_VG.json > _bestrec_run/run_DECOMP_posrab_VG.log 2>&1
echo "=== DECOMP BATCH DONE ==="
