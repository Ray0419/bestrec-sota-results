#!/bin/bash
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10"
for S in 20260609 20260610 20260611 20260612; do
  echo "=== TEXT seed $S ==="
  $PRE --text-sim-bias --text-prototypes 512 --seed $S --out _bestrec_run/results_TAIL_V2_text_seed${S}_VG.json > _bestrec_run/run_TAIL_V2_text_seed${S}_VG.log 2>&1
  echo "=== IDONLY seed $S ==="
  $PRE --no-sbert --seed $S --out _bestrec_run/results_TAIL_idonly_seed${S}_VG.json > _bestrec_run/run_TAIL_idonly_seed${S}_VG.log 2>&1
done
echo "=== TAIL CONTRAST 5-SEED DONE ==="
