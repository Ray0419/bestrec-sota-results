#!/usr/bin/env bash
# MI per-lever isolation (supervisor cycle-3 directive #4): which confirmed lever
# carries the MI cross-category win? Base MI-best (no LS, no filter)=0.0383;
# both (MI-V2 K16)=0.04163 seed08. Isolate +filter-only and +LS-only, single seed.
set -u
PY=".venv/Scripts/python"
PRE="$PY -u run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 \
--d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax \
--item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu \
--time-bias --text-sim-bias --text-prototypes 512 --pos-rab --eval-every 1"

echo "=== [1/2] MI +filter-only (causal-filter K16, NO label-smoothing) ==="
$PRE --causal-filter --filter-kernel 16 \
  --out results_MI_filteronly_seed08.json
echo "=== [2/2] MI +LS-only (label-smoothing 0.2, NO causal-filter) ==="
$PRE --label-smoothing 0.2 \
  --out results_MI_lsonly_seed08.json
echo "=== MI per-lever isolation driver DONE ==="
