#!/usr/bin/env bash
# Decomposition ablation on FAITHFUL HSTU (supervisor cycle-2 TOP-PRIORITY FIX).
# Three single-flag runs on the J1_plain config (encoder hstu, 4L/d64/h2, dropout 0.5,
# 40ep, seed 20260608, chunked-full-softmax, all novel flags OFF -> test 0.0588).
# Each adds exactly ONE novel flag. Single-seed is fine for attribution.
# Runs SEQUENTIALLY -> never two concurrent GPU jobs.
set -u
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
PREFIX="-u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu"

echo "=== DECOMP driver start $(date) ==="

echo "--- [1/3] time-bias ---"
$PY $PREFIX --time-bias --eval-every 10 --out _bestrec_run/results_DECOMP_timebias_VG.json
echo "--- [1/3] done rc=$? ---"

echo "--- [2/3] text-sim-bias ---"
$PY $PREFIX --text-sim-bias --eval-every 10 --out _bestrec_run/results_DECOMP_textsim_VG.json
echo "--- [2/3] done rc=$? ---"

echo "--- [3/3] pos-rab ---"
$PY $PREFIX --pos-rab --eval-every 10 --out _bestrec_run/results_DECOMP_posrab_VG.json
echo "--- [3/3] done rc=$? ---"

echo "=== DECOMP driver end $(date) ==="
