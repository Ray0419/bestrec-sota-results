#!/usr/bin/env bash
# Cycle-10-sanctioned FINAL experiment: down-limb seed-replication of the user-mode titration
# (PROPOSAL 2026-06-20-1). Powers rho_user=0.50 and 0.40 from single-seed (s08 on disk) to 5 seeds.
# Guardrails (supervisor cycle-10): ONLY rho050/rho040, BOTH arms, seeds {09-12}, --subsample-seed 0
# fixed, FULL eval, ONE GPU job at a time (sequential), verify n_eval=94762 + tail n=10900 per run.
# This is a DATA-ABLATION, not a model lever or SOTA attempt: expected delta on overall NDCG = 0.
set -u
cd /c/Users/rayxc/Documents/R || exit 1
PY=_bestrec_run/.venv/Scripts/python
COMMON="Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine"

for FRAC in 0.50 0.40; do
  FF=$(echo "$FRAC" | sed 's/0\.//')   # 0.50 -> 50, 0.40 -> 40
  for SEED in 20260609 20260610 20260611 20260612; do
    SS=${SEED: -2}                       # 20260609 -> 09
    # ---- TEXT arm (V2 stack) ----
    TXT_OUT=_bestrec_run/results_USERTITR_text_rho0${FF}_s${SS}_VG.json
    TXT_LOG=_bestrec_run/run_USERTITR_text_rho0${FF}_s${SS}_VG.log
    if [ -f "$TXT_OUT" ]; then
      echo "[skip] $TXT_OUT exists"
    else
      echo "[run ] TEXT rho0${FF} seed${SEED}"
      $PY -u _bestrec_run/run_sasrec_sbert.py $COMMON --seed $SEED \
        --encoder hstu --time-bias --text-sim-bias --text-prototypes 512 --pos-rab \
        --label-smoothing 0.2 --causal-filter --filter-kernel 8 \
        --subsample-mode user --subsample-train-frac $FRAC --subsample-seed 0 \
        --eval-every 10 --out "$TXT_OUT" > "$TXT_LOG" 2>&1
    fi
    # ---- ID-only arm (no text) ----
    ID_OUT=_bestrec_run/results_USERTITR_idonly_rho0${FF}_s${SS}_VG.json
    ID_LOG=_bestrec_run/run_USERTITR_idonly_rho0${FF}_s${SS}_VG.log
    if [ -f "$ID_OUT" ]; then
      echo "[skip] $ID_OUT exists"
    else
      echo "[run ] IDONLY rho0${FF} seed${SEED}"
      $PY -u _bestrec_run/run_sasrec_sbert.py $COMMON --seed $SEED \
        --encoder hstu --time-bias --pos-rab \
        --label-smoothing 0.2 --causal-filter --filter-kernel 8 --no-sbert \
        --subsample-mode user --subsample-train-frac $FRAC --subsample-seed 0 \
        --eval-every 10 --out "$ID_OUT" > "$ID_LOG" 2>&1
    fi
  done
done
echo "ALL_DOWNLIMB_RUNS_COMPLETE"
