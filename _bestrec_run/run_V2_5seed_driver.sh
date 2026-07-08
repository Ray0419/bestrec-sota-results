#!/usr/bin/env bash
# 5-seed escalation of V2 (label-smoothing 0.2 + causal-filter K=8) — crossed 0.0660 gate at seed 08 (test 0.0673).
# seed 20260608 already done (results_V2_ls02_filter8_VG.json). Run remaining 4 seeds sequentially (ONE GPU job).
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
for SEED in 20260609 20260610 20260611 20260612; do
  echo "=== V2 5-seed: launching seed $SEED ==="
  $PY -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed $SEED \
    --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias \
    --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
    --eval-every 10 --out _bestrec_run/results_V2_ls02_filter8_seed${SEED}_VG.json \
    > _bestrec_run/run_V2_ls02_filter8_seed${SEED}_VG.log 2>&1
  echo "=== seed $SEED done ==="
done
echo "=== ALL V2 5-seed runs complete ==="
