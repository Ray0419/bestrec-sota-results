#!/bin/bash
# SOTA_CONFIRM_PREREG_OFFICE.md driver — 4th-category program (16 runs total).
set -euo pipefail
cd /c/Users/rayxc/Documents/R
PY="${PYBIN:-}"
if [ -z "$PY" ]; then
  if command -v uv >/dev/null 2>&1; then PY="uv --project _bestrec_run run python";
  else PY=_bestrec_run/.venv/Scripts/python; fi
fi
echo "[office] waiting for downloads..."
for f in data_raw_proper/office/Office_Products.jsonl.gz data_raw_proper/office/meta_Office_Products.jsonl.gz; do
  until gzip -t "$f" 2>/dev/null; do sleep 60; done; echo "[office] $f OK"
done
[ -f data_raw_proper/office/Office_Products.jsonl ] || gunzip -k data_raw_proper/office/Office_Products.jsonl.gz
[ -f data_raw_proper/office/meta_Office_Products.jsonl ] || gunzip -k data_raw_proper/office/meta_Office_Products.jsonl.gz
echo "[office] preprocessing (5-core LLOO)..."
[ -f data_5core/5core/last_out/Office_Products.train.csv ] || $PY -u _bestrec_run/preprocess_5core_standard.py Office_Products > _bestrec_run/preprocess_Office_Products.log 2>&1
echo "[office] waiting for GPU (FIR ablations)..."
until grep -q "FIR_ABLATIONS_COMPLETE" _bestrec_run/run_fir_ablations_driver.log 2>/dev/null; do sleep 120; done
echo "[office] encoding titles..."
[ -f cache_5core/sbert_titles_Office_Products.npy ] || $PY -u _bestrec_run/run_5core_benchmark.py Office_Products --encode-titles > _bestrec_run/encode_Office_Products.log 2>&1
echo "[office] stats + P1 prediction (before any training)..."
$PY _bestrec_run/office_prereg_tools.py stats
PRE="$PY -u _bestrec_run/run_sasrec_sbert.py Office_Products --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --eval-every 2 --eval-subsample 30000"
for s in 20260623 20260624 20260625 20260626 20260627; do
  O=_bestrec_run/results_OFFICE_k16_seed${s}.json
  [ -f "$O" ] || $PRE --text-sim-bias --text-prototypes 512 --filter-kernel 16 --seed $s --out "$O" > _bestrec_run/run_OFFICE_k16_seed${s}.log 2>&1
  echo "[office] k16 $s done"
done
for s in 20260623 20260624 20260625 20260626 20260627; do
  O=_bestrec_run/results_OFFICE_k8_seed${s}.json
  [ -f "$O" ] || $PRE --text-sim-bias --text-prototypes 512 --filter-kernel 8 --seed $s --out "$O" > _bestrec_run/run_OFFICE_k8_seed${s}.log 2>&1
  echo "[office] k8 $s done"
done
for s in 20260623 20260624 20260625 20260626 20260627; do
  O=_bestrec_run/results_OFFICE_idonly_seed${s}.json
  [ -f "$O" ] || $PRE --no-sbert --filter-kernel 8 --seed $s --out "$O" > _bestrec_run/run_OFFICE_idonly_seed${s}.log 2>&1
  echo "[office] idonly $s done"
done
O=_bestrec_run/results_OFFICE_sasrecfloor_seed20260623.json
[ -f "$O" ] || $PY -u _bestrec_run/run_sasrec_sbert.py Office_Products --epochs 20 --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.2 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder transformer --no-sbert --eval-every 2 --eval-subsample 30000 --seed 20260623 --out "$O" > _bestrec_run/run_OFFICE_sasrecfloor.log 2>&1
echo "[office] floor done"
$PY _bestrec_run/office_prereg_tools.py adjudicate
echo "OFFICE_PROGRAM_COMPLETE"
