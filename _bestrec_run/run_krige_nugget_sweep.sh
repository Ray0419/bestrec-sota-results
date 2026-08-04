#!/usr/bin/env bash
# KRIGE nugget-robustness sweep (SUPERVISOR cycle-19 CONTINUE #1).
# Bit-identical to results_KRIGE_cold_hstu_MI_seed20260608.json except --krige-nugget.
# PASS = cold hit@10 > 7 AND warm N@10 >= 0.040 at all three nuggets.
set -u
PY=_bestrec_run/.venv/Scripts/python
cd /c/Users/rayxc/Documents/R
declare -A TAGS=( ["0.001"]="0p001" ["0.05"]="0p05" ["0.1"]="0p1" )
for NUG in 0.001 0.05 0.1; do
  TAG=${TAGS[$NUG]}
  OUT=_bestrec_run/results_KRIGENUG_${TAG}_MI_seed20260608.json
  LOG=_bestrec_run/run_KRIGENUG_${TAG}_MI_seed20260608.log
  echo "=== RUNNING krige-nugget=$NUG -> $OUT ==="
  "$PY" -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
    --cold-item-frac 0.15 --cold-item-seed 1 --cold-synth-knn 20 --cold-synth-temp 0.07 \
    --krige-cold --krige-nugget "$NUG" --eval-every 10 \
    --out "$OUT" > "$LOG" 2>&1
  echo "=== DONE krige-nugget=$NUG (exit $?) ==="
done
echo "=== SWEEP COMPLETE ==="
