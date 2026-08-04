#!/usr/bin/env bash
# Beauty cold-synth replication — 3rd-dataset escalation (seeds 08-12, paired).
# Paired text-stack + cold-synth on the IDENTICAL Beauty cold split (frac0.15 seed1), 20ep.
# Sequential ONE-GPU-AT-A-TIME. Matches the confirmed MI/VG cold-synth protocol exactly.
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
base () {
  echo "_bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed $1 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --cold-item-frac 0.15 --cold-item-seed 1 --eval-every 10"
}
for S in 20260608 20260609 20260610 20260611 20260612; do
  echo "=== seed $S ARM text-stack $(date) ==="
  $PY -u $(base $S) --out _bestrec_run/results_COLD_text_Beauty_seed${S}.json
  echo "=== seed $S ARM cold-synth $(date) ==="
  $PY -u $(base $S) --cold-synth-knn 20 --cold-synth-temp 0.07 --out _bestrec_run/results_COLDSYNTH_Beauty_seed${S}.json
done
echo "=== 5SEED DONE $(date) ==="
