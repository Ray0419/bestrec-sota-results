#!/bin/bash
cd /c/Users/rayxc/Documents/R
for S in 20260609 20260610 20260611 20260612; do
  echo "=== SEED $S START ==="
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed $S --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10 \
    --out _bestrec_run/results_V2_ls02_filter8_seed${S}_VG.json \
    > _bestrec_run/run_V2_ls02_filter8_seed${S}_VG.log 2>&1
  echo "=== SEED $S DONE ==="
done
echo "=== ALL SEEDS DONE ==="
