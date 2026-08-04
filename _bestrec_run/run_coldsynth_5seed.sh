#!/usr/bin/env bash
# PROPOSAL 2026-06-23-1 cold-synth 5-seed paired escalation (sanctioned by the
# pre-registered gate: seed 08 first showed a real cold floor-lift => 5-seed it).
# Sequential, ONE GPU job at a time. Pairs cold-synth vs text-stack on the
# IDENTICAL cold split (--cold-item-frac 0.15 --cold-item-seed 1), seeds 09-12
# (seed 08 already on disk). Both arms use the new code; text-stack = knn 0 (OFF).
set -e
PY=_bestrec_run/.venv/Scripts/python
COMMON="Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --cold-item-frac 0.15 --cold-item-seed 1 --eval-every 10"
for S in 20260609 20260610 20260611 20260612; do
  echo "=== text-stack seed $S ==="
  $PY -u _bestrec_run/run_sasrec_sbert.py $COMMON --seed $S \
    --out _bestrec_run/results_COLD_text_MI_seed${S}.json \
    > _bestrec_run/run_COLD_text_MI_seed${S}.log 2>&1
  echo "=== cold-synth seed $S ==="
  $PY -u _bestrec_run/run_sasrec_sbert.py $COMMON --seed $S --cold-synth-knn 20 --cold-synth-temp 0.07 \
    --out _bestrec_run/results_COLDSYNTH_MI_seed${S}.json \
    > _bestrec_run/run_COLDSYNTH_MI_seed${S}.log 2>&1
done
echo "=== 5-seed paired escalation COMPLETE ==="
