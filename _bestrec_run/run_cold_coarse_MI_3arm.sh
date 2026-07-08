#!/usr/bin/env bash
# 2026-06-23 EXPERIMENT agent: re-run the PROPOSAL 2026-06-22-1 3-arm MI cold-item
# centerpiece with COARSE cold cutoffs (NDCG/HR@{20,50,100} + MRR + n_hit@K) added
# to by_coldstart. Rationale: the original 3-arm run (01:13-01:21) floored at
# NDCG@10=0 / 0 hits for ALL arms over 8748 cold targets => zero resolving power.
# The proposal's own DONE-note flagged a coarser-cutoff confirm as PENDING. New
# output filenames (_coarse) — originals are PRESERVED (never overwritten).
# IDENTICAL cold split: --cold-item-frac 0.15 --cold-item-seed 1, seed 20260608.
# Sequential (ONE GPU job at a time); each MI 20ep run ~4 min.
set -e
cd "C:/Users/rayxc/Documents/R"
PY="_bestrec_run/.venv/Scripts/python"
# BASE = config shared by all arms (no text-dependent flags here).
BASE="--epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --seed 20260608 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8 --cold-item-frac 0.15 --cold-item-seed 1 --eval-every 10"
# TEXT = the text-stack flags (text/conn-gate arms only; ID-only omits them, matching
# the original idonly config: text_sim_bias=False, text_prototypes=0).
TEXT="--text-sim-bias --text-prototypes 512"

echo "=== ARM 1/3: ID-only (--no-sbert, no text flags) ==="
$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments $BASE --no-sbert \
  --out _bestrec_run/results_COLD_idonly_MI_seed20260608_coarse.json \
  > _bestrec_run/run_COLD_idonly_MI_coarse.log 2>&1

echo "=== ARM 2/3: text-stack ==="
$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments $BASE $TEXT \
  --out _bestrec_run/results_COLD_text_MI_seed20260608_coarse.json \
  > _bestrec_run/run_COLD_text_MI_coarse.log 2>&1

echo "=== ARM 3/3: conn-gate ==="
$PY -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments $BASE $TEXT --conn-gate \
  --out _bestrec_run/results_COLD_conngate_MI_seed20260608_coarse.json \
  > _bestrec_run/run_COLD_conngate_MI_coarse.log 2>&1

echo "=== ALL 3 ARMS DONE ==="
