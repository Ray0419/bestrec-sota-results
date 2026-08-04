#!/bin/bash
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --eval-every 2"
echo "=== MI +LS-only (no filter) ==="
$PRE --label-smoothing 0.2 --out _bestrec_run/results_MI_LSonly.json > _bestrec_run/run_MI_LSonly.log 2>&1
echo "=== MI +filter-only K16 (no LS) ==="
$PRE --causal-filter --filter-kernel 16 --out _bestrec_run/results_MI_filteronly_k16.json > _bestrec_run/run_MI_filteronly_k16.log 2>&1
echo "=== MI PERLEVER DONE ==="
