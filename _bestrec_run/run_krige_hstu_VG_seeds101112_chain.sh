#!/usr/bin/env bash
# Sequential (ONE GPU job at a time) chain to COMPLETE the kriging-hstu VG 5-seed.
# Seeds 08,09 already on disk (clear the deployable @10 gate). This finishes 10,11,12
# so the analyst can compute a seed-paired kriging - cold-synth VG delta (blocker #1).
# Config is BIT-IDENTICAL to results_KRIGE_cold_hstu_VG_seed20260608/09.json.
set -e
cd "C:/Users/rayxc/Documents/R"
PY="_bestrec_run/.venv/Scripts/python"
for SEED in 20260610 20260611 20260612; do
  OUT="_bestrec_run/results_KRIGE_cold_hstu_VG_seed${SEED}.json"
  LOG="_bestrec_run/run_KRIGE_cold_hstu_VG_seed${SEED}.log"
  if [ -e "$OUT" ]; then
    echo "[chain] $OUT exists, skipping (no overwrite)."
    continue
  fi
  echo "[chain] === launching seed ${SEED} ==="
  "$PY" -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed ${SEED} --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
    --cold-item-frac 0.15 --cold-item-seed 1 --cold-synth-knn 20 --cold-synth-temp 0.07 \
    --krige-cold --krige-nugget 0.01 \
    --eval-every 10 --out "$OUT" > "$LOG" 2>&1
  echo "[chain] === seed ${SEED} DONE -> $OUT ==="
done
echo "[chain] ALL DONE: VG kriging-hstu seeds 10,11,12 complete."
