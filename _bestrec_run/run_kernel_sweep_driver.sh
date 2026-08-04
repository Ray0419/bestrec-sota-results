#!/usr/bin/env bash
# Filter kernel-size sweep on the confirmed V2 VG stack (supervisor cycle-2 directive (ii):
# defend the promoted k8 hyperparameter with multi-seed k4/k16/k50). k8 already has 5 seeds (V2).
# Proven config, existing flags only -> no smoke test needed (hyperparameter sweep, no new mechanism).
set -u
PY=_bestrec_run/.venv/Scripts/python
cd "$(dirname "$0")/.." || exit 1
COMMON="Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 \
--dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine \
--encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
--label-smoothing 0.2 --causal-filter --eval-every 10"
for K in 4 16 50; do
  for S in 20260608 20260609 20260610; do
    echo "=== KSWEEP k${K} seed ${S} START ==="
    $PY -u _bestrec_run/run_sasrec_sbert.py $COMMON --filter-kernel ${K} --seed ${S} \
      --out _bestrec_run/results_KSWEEP_k${K}_seed${S}_VG.json \
      > _bestrec_run/run_KSWEEP_k${K}_seed${S}_VG.log 2>&1
    echo "=== KSWEEP k${K} seed ${S} DONE ==="
  done
done
echo "=== KSWEEP ALL DONE ==="
