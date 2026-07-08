#!/usr/bin/env bash
# Multi-seed DECOMP single-flag decomposition on the faithful HSTU (Table-1 spine).
# Upgrades the single-seed (seed08) per-component attribution to 5-seed.
# Baseline J1-plain (HSTU + additive SBERT, all novel flags OFF) + 3 single-flags,
# each adding exactly ONE existing flag. No code change; existing flags ran clean at seed08.
# Sequential => exactly ONE GPU job at a time.
set -u
PY="_bestrec_run/.venv/Scripts/python"
RUN="_bestrec_run/run_sasrec_sbert.py"
COMMON="Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --eval-every 10"
SEEDS="20260609 20260610 20260611 20260612"

# name|extra-flags
CONFIGS=(
  "J1plain|"
  "timebias|--time-bias"
  "posrab|--pos-rab"
  "tapeonly|--text-prototypes 512"
)

cd /c/Users/rayxc/Documents/R || exit 1
echo "DECOMP5 driver START $(date)"
for entry in "${CONFIGS[@]}"; do
  name="${entry%%|*}"
  flags="${entry#*|}"
  for s in $SEEDS; do
    out="_bestrec_run/results_DECOMP5_${name}_seed${s}_VG.json"
    if [ -f "$out" ]; then echo "SKIP existing $out"; continue; fi
    echo "=== RUN ${name} seed ${s} $(date) ==="
    $PY -u $RUN $COMMON --seed $s $flags --out "$out"
    echo "=== DONE ${name} seed ${s} rc=$? $(date) ==="
  done
done
echo "DECOMP5 driver COMPLETE $(date)"
