#!/bin/bash
# Multi-seed confirmation of the MID-regime TAPE attribution (supervisor cycle-3 directive #3:
# "multi-seed only the component that shows a mid signal"). TAPE shows the mid signal
# (+0.00186, ~85% of the text mid-win, single-seed08). Here we multi-seed BOTH arms at
# seeds 09-12 so the TAPE marginal (TAPE-only minus SBERT-only) in the mid tercile gets a band.
# seed08 already on disk: results_TAIL_comp_sbertonly_VG.json / results_TAIL_comp_tapeonly_VG.json.
# Existing flags only (no code change, no new mechanism). One GPU job at a time, sequential.
cd /c/Users/rayxc/Documents/R
PRE="_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 10"
for S in 20260609 20260610 20260611 20260612; do
  echo "=== seed $S : +SBERT-only ==="
  $PRE --seed $S --out _bestrec_run/results_TAIL_comp_sbertonly_seed${S}_VG.json > _bestrec_run/run_TAIL_comp_sbertonly_seed${S}_VG.log 2>&1
  echo "=== seed $S : +TAPE-only ==="
  $PRE --seed $S --text-prototypes 512 --out _bestrec_run/results_TAIL_comp_tapeonly_seed${S}_VG.json > _bestrec_run/run_TAIL_comp_tapeonly_seed${S}_VG.log 2>&1
done
echo "=== TAPE MID MULTISEED DONE ==="
