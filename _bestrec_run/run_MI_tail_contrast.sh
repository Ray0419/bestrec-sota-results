#!/usr/bin/env bash
# MI (Musical_Instruments) text-vs-ID TAIL contrast — 2nd-dataset replication of the VG
# mission finding (text gives NO long-tail advantage; tail<head<mid ordering).
# Mission win-condition explicitly wants the tail result "replicated on >=2 datasets".
# Mirrors the VG TAIL_V2_text vs TAIL_idonly CLEAN controlled toggle EXACTLY: only the
# text bundle (sbert / text-sim-bias / text-prototypes) differs; all architectural levers
# (time-bias, pos-rab, LS0.2, causal-filter k8, hstu) held identical. by_popularity is
# auto-emitted (train-frequency terciles, leak-free). One GPU job at a time (sequential).
# NO new code — all flags pre-existing & validated. seed08 single-seed = initial signal
# (per mission directive: single-seed fine for initial signal; multi-seed only if a tail
# effect appears). MI 20ep convention (matches all prior MI runs). ~5 min/run, ~10 min total.
set -u
cd "C:/Users/rayxc/Documents/R"
VENV=_bestrec_run/.venv/Scripts/python
S=20260608
COMMON="Musical_Instruments --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --eval-every 1 --seed $S"

echo "=================== MI TEXT (V2 stack, +sbert +text-sim +TAPE-512) ==================="
$VENV -u _bestrec_run/run_sasrec_sbert.py $COMMON --text-sim-bias --text-prototypes 512 \
  --out _bestrec_run/results_MI_TAIL_V2_text_seed${S}.json

echo "=================== MI ID-only (--no-sbert, no text-sim, no TAPE) ==================="
$VENV -u _bestrec_run/run_sasrec_sbert.py $COMMON --no-sbert \
  --out _bestrec_run/results_MI_TAIL_idonly_seed${S}.json

echo "=================== MI TAIL CONTRAST COMPLETE ==================="
