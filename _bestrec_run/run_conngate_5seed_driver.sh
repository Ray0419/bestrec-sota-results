#!/usr/bin/env bash
# Pre-registered conn-gate 5-seed MI confirmation (SUPERVISOR cycle-14 sanctioned).
# MI only, k8 (V2 stack), 20 epochs, FULL eval. s08 already banked
# (results_CONNGATE_MI_k8_seed20260608.json). This driver runs the 4 NEW seeds
# sequentially (ONE GPU job at a time). Matched control = MI_TAIL_V2_text_seed*.
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
for SEED in 20260609 20260610 20260611 20260612; do
  echo "==== conn-gate MI k8 seed $SEED START ===="
  $PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed $SEED --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 8 --conn-gate --eval-every 10 \
    --out _bestrec_run/results_CONNGATE_MI_k8_seed${SEED}.json
  echo "==== conn-gate MI k8 seed $SEED DONE ===="
done
echo "ALL_CONNGATE_SEEDS_DONE"
