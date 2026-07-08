#!/usr/bin/env bash
# Complete Table-1's per-component column: multi-seed the ONE missing single-flag
# decomposition cell — --text-sim-bias (seeds 09-12; seed08 already on disk as
# results_DECOMP_textsim_VG.json). Plain HSTU + additive SBERT + only --text-sim-bias,
# matching the seed08 DECOMP_textsim config exactly. No code change (existing flag,
# ran clean at seed08) => no NaN smoke. Sequential => exactly ONE GPU job at a time.
set -u
PY="_bestrec_run/.venv/Scripts/python"
RUN="_bestrec_run/run_sasrec_sbert.py"
COMMON="Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --eval-every 10"
SEEDS="20260609 20260610 20260611 20260612"

cd /c/Users/rayxc/Documents/R || exit 1
echo "DECOMP5 textsim driver START $(date)"
for s in $SEEDS; do
  out="_bestrec_run/results_DECOMP5_textsim_seed${s}_VG.json"
  if [ -f "$out" ]; then echo "SKIP existing $out"; continue; fi
  echo "=== RUN textsim seed ${s} $(date) ==="
  $PY -u $RUN $COMMON --seed $s --text-sim-bias --out "$out"
  echo "=== DONE textsim seed ${s} rc=$? $(date) ==="
done
echo "DECOMP5 textsim driver COMPLETE $(date)"
