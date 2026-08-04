#!/usr/bin/env bash
# 5-seed the strongest cold arm: --sbert-only --encoder hstu on MI cold-start split.
# seed 20260608 already on disk; this adds 09-12 sequentially (ONE GPU job at a time).
set -u
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
for SEED in 20260609 20260610 20260611 20260612; do
  OUT=_bestrec_run/results_COLD_sbertonly_hstu_MI_seed${SEED}.json
  LOG=_bestrec_run/run_COLD_sbertonly_hstu_MI_seed${SEED}.log
  if [ -f "$OUT" ]; then
    echo "[driver] $OUT exists, skipping"
    continue
  fi
  echo "[driver] launching seed $SEED at $(date)"
  "$PY" -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
    --sbert-only --cold-item-frac 0.15 --cold-item-seed 1 \
    --seed ${SEED} --eval-every 10 \
    --out "$OUT" > "$LOG" 2>&1
  echo "[driver] seed $SEED done at $(date) rc=$?"
done
echo "[driver] all seeds complete at $(date)"
