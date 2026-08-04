#!/usr/bin/env bash
# Complete the per-component TAIL decomposition: text-sim-only at seeds 09-12
# (seed08 already on disk: results_TAIL_comp_textsimonly_VG.json).
# Replicates the seed08 config EXACTLY (SBERT on, text-sim on, NO text-prototypes,
# time-bias, pos-rab, LS0.2, causal-filter k8). Existing validated flags only.
# Single GPU job, sequential. Analyst missing-ablation #2 (ANALYSIS 2026-06-17-2).
set -e
cd "$(dirname "$0")/.."
PY=_bestrec_run/.venv/Scripts/python
PRE="$PY -u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 \
--d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 \
--lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --pos-rab \
--label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10"
for S in 20260609 20260610 20260611 20260612; do
  OUT=_bestrec_run/results_TAIL_comp_textsimonly_seed${S}_VG.json
  LOG=_bestrec_run/run_TAIL_comp_textsimonly_seed${S}_VG.log
  echo "=== textsim-only seed ${S} -> ${OUT} ==="
  $PRE --seed ${S} --out ${OUT} > ${LOG} 2>&1
done
echo "=== textsim-only multiseed driver DONE ==="
