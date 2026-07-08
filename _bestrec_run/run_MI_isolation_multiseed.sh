#!/usr/bin/env bash
# MI per-lever isolation, multi-seed extension (analyst 2026-06-17-2 missing-ablation #1).
# Extends the single-seed (seed08) MI filter-only / LS-only contrast to a full 5-seed
# to lock the paper claim: the causal spectral filter carries the cross-category (MI)
# generalization (92% of lift @ seed08), LS is VG-specific. One GPU job at a time;
# runs are sequential. NO new code — both flags already implemented & validated @ seed08.
set -u
cd "C:/Users/rayxc/Documents/R"
VENV=_bestrec_run/.venv/Scripts/python
COMMON="Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --eval-every 1"

for S in 20260609 20260610 20260611 20260612; do
  echo "=================== SEED $S : filter-only (k16, ls0) ==================="
  $VENV -u _bestrec_run/run_sasrec_sbert.py $COMMON --causal-filter --filter-kernel 16 \
    --seed $S --out _bestrec_run/results_MI_filteronly_seed${S}.json
  echo "=================== SEED $S : LS-only (ls0.2, no filter) ==============="
  $VENV -u _bestrec_run/run_sasrec_sbert.py $COMMON --label-smoothing 0.2 \
    --seed $S --out _bestrec_run/results_MI_lsonly_seed${S}.json
done
echo "=================== ALL MI ISOLATION MULTISEED RUNS COMPLETE ==================="
