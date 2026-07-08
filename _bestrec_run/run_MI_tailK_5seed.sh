#!/bin/bash
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10"
for s in 20260608 20260609 20260610 20260611 20260612; do
  # TEXT arm (full stack)
  O=_bestrec_run/results_TAILK_text_MI_seed${s}.json
  [ -f "$O" ] || $PRE --seed $s --text-sim-bias --text-prototypes 512 --out "$O" > _bestrec_run/run_TAILK_text_MI_seed${s}.log 2>&1
  # ID-only arm
  O=_bestrec_run/results_TAILK_idonly_MI_seed${s}.json
  [ -f "$O" ] || $PRE --seed $s --no-sbert --out "$O" > _bestrec_run/run_TAILK_idonly_MI_seed${s}.log 2>&1
  echo "seed $s done"
done
echo "MI_TAILK_5SEED_DONE"
