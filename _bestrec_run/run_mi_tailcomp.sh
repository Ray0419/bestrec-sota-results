#!/bin/bash
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 16 --eval-every 2"
echo "=== MI +SBERT-only ==="
$PRE --out _bestrec_run/results_MI_tailcomp_sbertonly.json > _bestrec_run/run_MI_tailcomp_sbertonly.log 2>&1
echo "=== MI +TAPE-only ==="
$PRE --text-prototypes 512 --out _bestrec_run/results_MI_tailcomp_tapeonly.json > _bestrec_run/run_MI_tailcomp_tapeonly.log 2>&1
echo "=== MI +text-sim-only ==="
$PRE --text-sim-bias --out _bestrec_run/results_MI_tailcomp_textsimonly.json > _bestrec_run/run_MI_tailcomp_textsimonly.log 2>&1
echo "=== MI TAILCOMP DONE ==="
