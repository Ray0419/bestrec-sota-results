#!/bin/bash
# PRE-REGISTERED fresh-seed confirmation (see SOTA_CONFIRM_PREREG.md, frozen before launch).
# Primary arm: k16, fresh seeds 20260613-17. Secondary: k8, same seeds.
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --eval-every 1"
for s in 20260613 20260614 20260615 20260616 20260617; do
  O=_bestrec_run/results_SOTACONF_k16_MI_seed${s}.json
  [ -f "$O" ] || $PRE --filter-kernel 16 --seed $s --out "$O" > _bestrec_run/run_SOTACONF_k16_MI_seed${s}.log 2>&1
  echo "k16 seed $s done"
done
for s in 20260613 20260614 20260615 20260616 20260617; do
  O=_bestrec_run/results_SOTACONF_k8_MI_seed${s}.json
  [ -f "$O" ] || $PRE --filter-kernel 8 --seed $s --out "$O" > _bestrec_run/run_SOTACONF_k8_MI_seed${s}.log 2>&1
  echo "k8 seed $s done"
done
echo "SOTA_CONFIRM_DRIVER_COMPLETE"
