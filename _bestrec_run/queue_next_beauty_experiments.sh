#!/bin/bash
# Pre-built commands for the next gap-closing experiments on Beauty_and_PC.
# Manually invoke one at a time; do not run together (GPU contention).

# === EXP B: Rich-text MiniLM (title + categories + brand) ===
# ETA: ~2 hrs (20 epochs * ~6 min/epoch)
# Expected: +5-15% over baseline 0.0191
cmd_richtext() {
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.2 \
    --chunked-full-softmax --item-chunk 32768 \
    --encoder-cache cache_5core/richtext_titles_Beauty_and_Personal_Care.npy \
    --eval-every 5 --eval-subsample 10000 \
    --out _bestrec_run/results_sasrec_richtext_Beauty.json \
    > _bestrec_run/run_sasrec_richtext_Beauty.log 2>&1
}

# === EXP C: Fusion (BLaIR 768d + rich-text MiniLM 384d = 1152d) ===
# ETA: ~3 hrs (20 epochs * ~9 min/epoch; 1152d encoder slower)
# Expected: +10-25% over baseline 0.0191
cmd_fusion() {
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.2 \
    --chunked-full-softmax --item-chunk 32768 \
    --encoder-cache cache_5core/fusion_blair_richtext_Beauty_and_Personal_Care.npy \
    --eval-every 5 --eval-subsample 10000 \
    --out _bestrec_run/results_sasrec_fusion_Beauty.json \
    > _bestrec_run/run_sasrec_fusion_Beauty.log 2>&1
}

# === EXP D: BLaIR + augment-2 (more training data via subsequence sampling) ===
# ETA: ~6 hrs (25 epochs * ~14 min/epoch; augment doubles data per epoch)
# Expected: +5-20% over BLaIR baseline
cmd_blair_aug2() {
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
    --epochs 25 --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.2 \
    --chunked-full-softmax --item-chunk 32768 \
    --encoder-cache cache_5core/blair_titles_Beauty_and_Personal_Care.npy \
    --augment-factor 2 --eval-every 5 --eval-subsample 10000 \
    --out _bestrec_run/results_sasrec_blair_aug2_Beauty.json \
    > _bestrec_run/run_sasrec_blair_aug2_Beauty.log 2>&1
}

# === EXP E: Fusion + d=128 (scaled fusion) ===
# ETA: ~5 hrs
# Expected: depends on fusion outcome
cmd_fusion_d128() {
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
    --epochs 20 --batch-size 256 --d-model 128 --n-layers 2 --n-heads 4 --dropout 0.3 \
    --chunked-full-softmax --item-chunk 16384 \
    --encoder-cache cache_5core/fusion_blair_richtext_Beauty_and_Personal_Care.npy \
    --eval-every 5 --eval-subsample 10000 \
    --out _bestrec_run/results_sasrec_fusion_d128_Beauty.json \
    > _bestrec_run/run_sasrec_fusion_d128_Beauty.log 2>&1
}

# === EXP H: Hybrid (item_emb + MLP adaptor + dropout 0.5 + BLaIR) augment-2 ===
# ETA: ~4-5 hrs (25 epochs * 12 min/epoch)
# Expected: +5-15% over hybrid baseline if augmentation adds signal
cmd_hybrid_aug2() {
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
    --epochs 25 --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 \
    --encoder-cache cache_5core/blair_titles_Beauty_and_Personal_Care.npy \
    --mlp-adaptor --mlp-hidden 300 --mlp-dropout 0.2 \
    --augment-factor 2 --eval-every 5 --eval-subsample 10000 \
    --out _bestrec_run/results_sasrec_hybrid_aug2_Beauty.json \
    > _bestrec_run/run_sasrec_hybrid_aug2_Beauty.log 2>&1
}

# === EXP J: Hybrid + d=128 (wider with MLP+dropout 0.5) ===
# ETA: ~3 hrs
# Expected: +5-15% if width helps with proper dropout regularization
cmd_hybrid_d128() {
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
    --epochs 20 --batch-size 256 --d-model 128 --n-layers 2 --n-heads 4 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 16384 \
    --encoder-cache cache_5core/blair_titles_Beauty_and_Personal_Care.npy \
    --mlp-adaptor --mlp-hidden 300 --mlp-dropout 0.2 \
    --eval-every 5 --eval-subsample 10000 \
    --out _bestrec_run/results_sasrec_hybrid_d128_Beauty.json \
    > _bestrec_run/run_sasrec_hybrid_d128_Beauty.log 2>&1
}

# Dispatch by argument
case "${1:-help}" in
  richtext)   cmd_richtext   ;;
  fusion)     cmd_fusion     ;;
  blair_aug2) cmd_blair_aug2 ;;
  fusion_d128) cmd_fusion_d128 ;;
  hybrid_aug2) cmd_hybrid_aug2 ;;
  hybrid_d128) cmd_hybrid_d128 ;;
  *)
    echo "Usage: $0 {richtext|fusion|blair_aug2|fusion_d128|hybrid_aug2|hybrid_d128}"
    exit 2
    ;;
esac
