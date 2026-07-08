#!/usr/bin/env bash
# VG cold-synth replication — escalation of the MI-confirmed cold-synth mechanism (PROPOSAL 2026-06-23-1)
# to a second, denser catalog. Sequential ONE-GPU-AT-A-TIME: text-stack baseline, then cold-synth.
# Identical cold split (--cold-item-frac 0.15 --cold-item-seed 1), seed 20260608, 20 epochs.
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
PREFIX="-u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --cold-item-frac 0.15 --cold-item-seed 1 --eval-every 10"

echo "=== ARM 1/2: text-stack (paired cold baseline) $(date) ==="
$PY $PREFIX --out _bestrec_run/results_COLD_text_VG_seed20260608.json

echo "=== ARM 2/2: cold-synth (knn=20, temp=0.07) $(date) ==="
$PY $PREFIX --cold-synth-knn 20 --cold-synth-temp 0.07 --out _bestrec_run/results_COLDSYNTH_VG_seed20260608.json

echo "=== DONE $(date) ==="
