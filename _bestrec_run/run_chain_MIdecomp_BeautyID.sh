#!/usr/bin/env bash
# Sequential GPU chain (ONE job at a time), serving supervisor cycle-4 directive #2 (MI gate PASSED):
#   PART A — MI per-component TAIL decomposition (3 single-seed arms, ~25 min total):
#            attribute WHICH text piece drives the confirmed MI tail win (+27.6%, 5-seed, CI excludes 0).
#            Mirrors VG decomp semantics: each arm keeps SBERT on; nested idonly -> +sbert -> +{tape|textsim}.
#   PART B — Beauty (3rd-dataset LAW test) ID-only arm seed08 (~2 hr): completes the paired tail
#            contrast vs the already-finished Beauty TEXT arm. Pre-registered prediction: tail-NULL
#            (Beauty = dense / lowest text-distinctiveness => ID-density law predicts VG-like null).
set -e
cd /c/Users/rayxc/Documents/R
PY=_bestrec_run/.venv/Scripts/python

# ---- PART A: MI per-component tail decomp (Musical_Instruments, 20ep, eval-every 1) ----
MI="$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 1"

echo "[$(date)] === PART A 1/3: MI sbertonly (base + SBERT) ==="
$MI --out _bestrec_run/results_MI_comp_sbertonly_seed20260608.json

echo "[$(date)] === PART A 2/3: MI tapeonly (base + SBERT + TAPE-512) ==="
$MI --text-prototypes 512 --out _bestrec_run/results_MI_comp_tapeonly_seed20260608.json

echo "[$(date)] === PART A 3/3: MI textsimonly (base + SBERT + text-sim) ==="
$MI --text-sim-bias --out _bestrec_run/results_MI_comp_textsimonly_seed20260608.json

echo "[$(date)] === PART A COMPLETE — MI per-component tail decomp done ==="

# ---- PART B: Beauty ID-only arm seed08 (3rd-dataset LAW test contrast) ----
# Mirror the Beauty TEXT arm exactly, minus text: add --no-sbert, drop --text-prototypes/--text-sim-bias.
echo "[$(date)] === PART B: Beauty_and_Personal_Care ID-only seed08 (20ep, eval-every 10, full eval) ==="
$PY -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --no-sbert --eval-every 10 --out _bestrec_run/results_Beauty_TAIL_idonly_seed20260608.json

echo "[$(date)] === PART B COMPLETE — Beauty paired tail contrast ready (text+idonly seed08) ==="
echo "[$(date)] === CHAIN COMPLETE ==="
