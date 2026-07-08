#!/bin/bash
cd /c/Users/rayxc/Documents/R
for S in 20260609 20260610 20260611 20260612; do
  echo "=== MI TAPE-only seed $S ==="
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed $S --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 16 --text-prototypes 512 --eval-every 2 --out _bestrec_run/results_MI_tailcomp_tapeonly_seed${S}.json > _bestrec_run/run_MI_tailcomp_tapeonly_seed${S}.log 2>&1
done
echo "=== MI TAPEONLY 5SEED DONE ==="
