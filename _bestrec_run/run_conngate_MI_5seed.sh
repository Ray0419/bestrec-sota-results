#!/bin/bash
# 5-seed confirmation of the connectivity-gate (--conn-gate) on Musical_Instruments.
# seed 20260608 already on disk (results_CONNGATE_MI_k8_seed20260608.json); this
# fills 09-12. Compare 5v5 vs the additive baseline results_MI_TAIL_V2_text_seed*.
# Config is IDENTICAL to that baseline except --conn-gate (clean isolation, k8).
cd /c/Users/rayxc/Documents/R
for s in 20260609 20260610 20260611 20260612; do
  OUT=_bestrec_run/results_CONNGATE_MI_k8_seed${s}.json
  if [ -f "$OUT" ]; then echo "skip $s (exists)"; continue; fi
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --seed $s --lr-schedule warmup_cosine \
    --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
    --label-smoothing 0.2 --causal-filter --filter-kernel 8 --conn-gate \
    --eval-every 10 --out "$OUT" \
    > _bestrec_run/run_CONNGATE_MI_k8_seed${s}.log 2>&1
  echo "done seed $s"
done
echo "CONNGATE_MI_5SEED_DRIVER_COMPLETE"
