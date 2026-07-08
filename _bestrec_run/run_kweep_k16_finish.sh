#!/usr/bin/env bash
# Complete the k16 kernel-size 5-seed (analyst ANALYSIS 2026-06-16-4 missing-ablation #1).
# k16 already has seeds {08,09,10}; this fills 11 and 12 for a 5-seed head-to-head vs k8.
# V2 stack, only difference vs the promoted V2 is --filter-kernel 16 (vs 8). Existing config, clean.
set -e
PY=_bestrec_run/.venv/Scripts/python
cd /c/Users/rayxc/Documents/R
for SEED in 20260611 20260612; do
  echo "=== KSWEEP k16 seed ${SEED} ==="
  $PY -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed ${SEED} --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 16 --eval-every 10 \
    --out _bestrec_run/results_KSWEEP_k16_seed${SEED}_VG.json
done
echo "=== KSWEEP k16 5-seed COMPLETE ==="
