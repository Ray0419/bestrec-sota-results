#!/bin/bash
set -euo pipefail
# Novelty-audit fix-plan #4 comparator ablations: each arm changes exactly ONE
# design element of the causal FIR filter, on the MI k8 confirmation stack.
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 1"
for s in 20260608 20260609 20260610 20260611 20260612; do
  O=_bestrec_run/results_FIRABL_fixedavg_MI_seed${s}.json
  [ -f "$O" ] || $PRE --filter-fixed-avg --seed $s --out "$O" > _bestrec_run/run_FIRABL_fixedavg_MI_seed${s}.log 2>&1
  echo "fixedavg $s done"
done
for s in 20260608 20260609 20260610 20260611 20260612; do
  O=_bestrec_run/results_FIRABL_nogate_MI_seed${s}.json
  [ -f "$O" ] || $PRE --filter-no-gate --seed $s --out "$O" > _bestrec_run/run_FIRABL_nogate_MI_seed${s}.log 2>&1
  echo "nogate $s done"
done
echo "FIR_ABLATIONS_COMPLETE"
