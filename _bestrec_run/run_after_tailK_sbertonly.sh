#!/bin/bash
cd /c/Users/rayxc/Documents/R
# wait for the MI tail@K driver to finish (its last file), then run a CLEAN
# sbert-only on the SAME hstu encoder + same MI cold split as cold-synth, to
# settle "pure-text vs cold-synth on cold items" without the encoder confound.
until [ -f _bestrec_run/results_TAILK_idonly_MI_seed20260612.json ]; do sleep 60; done
sleep 20
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments \
  --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
  --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine \
  --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
  --sbert-only --cold-item-frac 0.15 --cold-item-seed 1 --eval-every 10 \
  --out _bestrec_run/results_COLD_sbertonly_hstu_MI_seed20260608.json \
  > _bestrec_run/run_COLD_sbertonly_hstu_MI.log 2>&1
echo "SBERTONLY_HSTU_COLD_DONE"
