#!/usr/bin/env bash
# Text-sim DROP on V2 (V2 stack MINUS --text-sim-bias), seeds 09-12, to complete a
# 5-seed ablation directly comparable to V2 5-seed (0.0674+/-0.0003).
# seed08 already on disk = results_ABL_no_textsim_VG.json (test 0.06721).
# Analyst ANALYSIS 2026-06-16-3 missing-ablation #1: justify dropping text-sim-bias.
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
for SEED in 20260609 20260610 20260611 20260612; do
  echo "=== START seed ${SEED} $(date) ==="
  $PY -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed ${SEED} --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
    --eval-every 10 --out _bestrec_run/results_NOTEXTSIM_seed${SEED}_VG.json
  echo "=== DONE seed ${SEED} $(date) ==="
done
echo "=== ALL SEEDS COMPLETE $(date) ==="
