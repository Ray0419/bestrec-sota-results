#!/usr/bin/env bash
# Multi-seed tail contrast driver (supervisor cycle-3 TOP-PRIORITY directive).
# Re-runs the confirmed V2 stack (TEXT) and the ID-only variant at seeds 09-12.
# seed08 already on disk (results_TAIL_V2_text_VG.json / results_TAIL_idonly_VG.json).
# ONE GPU job at a time, sequential. Interleaved by seed so partial completion = complete pairs.
set -u
cd "C:/Users/rayxc/Documents/R"
PY=_bestrec_run/.venv/Scripts/python
PREFIX="-u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10"

for S in 20260609 20260610 20260611 20260612; do
  # TEXT (full V2 stack: + text-sim-bias + TAPE-512 + SBERT)
  TO=_bestrec_run/results_TAIL_V2_text_seed${S}_VG.json
  if [ ! -f "$TO" ]; then
    echo "=== TEXT seed $S START $(date) ==="
    $PY $PREFIX --text-sim-bias --text-prototypes 512 --seed $S --out "$TO" > _bestrec_run/run_TAIL_V2_text_seed${S}_VG.log 2>&1
    echo "=== TEXT seed $S DONE rc=$? $(date) ==="
  else
    echo "=== TEXT seed $S SKIP (exists) ==="
  fi
  # ID-only (drop text-sim-bias + TAPE; --no-sbert)
  IO=_bestrec_run/results_TAIL_idonly_seed${S}_VG.json
  if [ ! -f "$IO" ]; then
    echo "=== IDONLY seed $S START $(date) ==="
    $PY $PREFIX --no-sbert --seed $S --out "$IO" > _bestrec_run/run_TAIL_idonly_seed${S}_VG.log 2>&1
    echo "=== IDONLY seed $S DONE rc=$? $(date) ==="
  else
    echo "=== IDONLY seed $S SKIP (exists) ==="
  fi
done
echo "=== ALL DONE $(date) ==="
