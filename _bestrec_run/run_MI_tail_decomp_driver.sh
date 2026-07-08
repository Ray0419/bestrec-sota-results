#!/usr/bin/env bash
# MI per-component TAIL decomposition (gate cleared: MI 5-seed tail Δ +0.000335, CI excludes 0).
# Mirrors the VG per-component decomp semantics exactly: each arm keeps SBERT on
# (prototypes/text-sim require it), nested idonly -> +sbert -> +{tape|textsim}.
# Single-seed (20260608) initial attribution per supervisor cycle-4 escalation. ONE GPU job (sequential).
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python
PREFIX="$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 1"

echo "[$(date)] === MI decomp arm 1/3: sbertonly (base + SBERT features) ==="
$PREFIX --out _bestrec_run/results_MI_comp_sbertonly_seed20260608.json

echo "[$(date)] === MI decomp arm 2/3: tapeonly (base + SBERT + TAPE prototypes) ==="
$PREFIX --text-prototypes 512 --out _bestrec_run/results_MI_comp_tapeonly_seed20260608.json

echo "[$(date)] === MI decomp arm 3/3: textsimonly (base + SBERT + text-sim bias) ==="
$PREFIX --text-sim-bias --out _bestrec_run/results_MI_comp_textsimonly_seed20260608.json

echo "[$(date)] === MI per-component tail decomp COMPLETE ==="
