#!/usr/bin/env bash
# PROPOSAL 2026-06-22-1 cold-item centerpiece — 3 arms, IDENTICAL cold split
# (--cold-item-frac 0.15 --cold-item-seed 1), seed 20260608, MI, 20 epochs.
# Sequential => ONE GPU job at a time (never concurrent). Cold-item NDCG@10 is
# the headline; conn-gate > text-stack on COLD targets is the pre-registered
# novel test. ID-only DROPS the text flags (incompatible with --no-sbert).
set -e
PY=_bestrec_run/.venv/Scripts/python
PREFIX="$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --cold-item-frac 0.15 --cold-item-seed 1 --eval-every 10"

echo "=== ARM 1/3: ID-only (--no-sbert, text dropped) ==="
$PREFIX --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --no-sbert \
  --out _bestrec_run/results_COLD_idonly_MI_seed20260608.json > _bestrec_run/run_COLD_idonly_MI_seed20260608.log 2>&1

echo "=== ARM 2/3: text-stack ==="
$PREFIX --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
  --out _bestrec_run/results_COLD_text_MI_seed20260608.json > _bestrec_run/run_COLD_text_MI_seed20260608.log 2>&1

echo "=== ARM 3/3: text-stack + conn-gate ==="
$PREFIX --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --conn-gate \
  --out _bestrec_run/results_COLD_conngate_MI_seed20260608.json > _bestrec_run/run_COLD_conngate_MI_seed20260608.log 2>&1

echo "=== ALL 3 ARMS DONE ==="
