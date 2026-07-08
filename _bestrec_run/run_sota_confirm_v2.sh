#!/bin/bash
# SOTA_CONFIRM_PREREG_V2.md driver — immutable pre-registered confirmation.
# Idempotent clean-rebuild entrypoint (Codex fix #10): from a checkout of the
# prereg commit with data_5core/ + cache_5core/ present, this single script
# regenerates all 10 result JSONs + per-user sidecars + the summary printout.
set -u
cd "$(dirname "$0")/.."
PY=_bestrec_run/.venv/Scripts/python
PRE="$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --eval-every 1"
for ARM in 16 8; do
  for S in 20260618 20260619 20260620 20260621 20260622; do
    O=_bestrec_run/results_SOTACONF_V2_k${ARM}_MI_seed${S}.json
    if [ -f "$O" ]; then echo "skip k${ARM} seed ${S} (exists)"; continue; fi
    $PRE --filter-kernel ${ARM} --seed ${S} --out "$O" \
      > _bestrec_run/run_SOTACONF_V2_k${ARM}_MI_seed${S}.log 2>&1
    echo "k${ARM} seed ${S} done"
  done
done
$PY _bestrec_run/summarize_sota_confirm_v2.py
echo "SOTA_CONFIRM_V2_DRIVER_COMPLETE"
