#!/bin/bash
cd /c/Users/rayxc/Documents/R
echo "=== CF1 on VG (k8) ==="
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --cue-fusion --cue-fusion-mode sum2 --cue-fusion-nbr 20 --eval-every 10 --out _bestrec_run/results_CF1_cuefusion_VG.json > _bestrec_run/run_CF1_cuefusion_VG.log 2>&1
echo "=== CF1 on MI (k16) ==="
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 16 --cue-fusion --cue-fusion-mode sum2 --cue-fusion-nbr 20 --eval-every 2 --out _bestrec_run/results_CF1_cuefusion_MI.json > _bestrec_run/run_CF1_cuefusion_MI.log 2>&1
echo "=== CF1 BOTH DONE ==="
