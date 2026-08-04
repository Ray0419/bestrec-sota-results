#!/usr/bin/env bash
# EXPERIMENT hourly (2026-07-02): 5-seed completion of the VG --sbert-only --encoder hstu
# cold diagnostic (ANALYST 2026-07-02-2 missing-ablation #1: VG replication of the MI-confirmed
# cold/warm tension). Config byte-matched to results_COLD_sbertonly_hstu_VG_seed20260608.json
# (seed08 already banked). SEQUENTIAL — one GPU job at a time. Skips any seed already on disk.
# No new mechanism (--sbert-only already ran clean at seed08) => no smoke needed.
set -u
PY=_bestrec_run/.venv/Scripts/python
cd "$(dirname "$0")/.." || exit 1
for SEED in 20260609 20260610 20260611 20260612; do
  OUT="_bestrec_run/results_COLD_sbertonly_hstu_VG_seed${SEED}.json"
  LOG="_bestrec_run/run_COLD_sbertonly_hstu_VG_seed${SEED}.log"
  if [ -f "$OUT" ]; then
    echo "[driver] SKIP $OUT (exists)"
    continue
  fi
  echo "[driver] START seed=$SEED -> $OUT"
  "$PY" -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
    --sbert-only --cold-item-frac 0.15 --cold-item-seed 1 \
    --seed "$SEED" --eval-every 10 --out "$OUT" > "$LOG" 2>&1
  echo "[driver] DONE seed=$SEED rc=$?"
done
echo "[driver] ALL SEEDS COMPLETE"
