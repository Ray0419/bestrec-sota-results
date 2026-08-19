#!/usr/bin/env bash
# PREREG_RHO_K_V1 S3 confirmatory matrix: 13 eval passes, stride 2, skip-if-exists.
set -u
cd "C:/Users/rayxc/Documents/R/.claude/worktrees/brave-rhodes-0a7d09/_bestrec_run"
PY="C:/Users/rayxc/Documents/R/_bestrec_run/.venv/Scripts/python.exe"
RUNS=""
for s in 20260736 20260737 20260738 20260739 20260740; do
  RUNS="$RUNS poc_out/results_SXL_fce_d256_MI_seed${s}.json poc_out/results_SXL_fce_d64_MI_seed${s}.json"
done
for s in 20260736 20260737 20260738; do
  RUNS="$RUNS poc_out/results_SXL_fce_d256_STEAM_seed${s}.json"
done
for r in $RUNS; do
  out="${r%.json}.pool_conv.json"
  if [ -f "$out" ]; then echo "[skip] $out"; continue; fi
  echo "[eval] $r"
  "$PY" -u poc_pool_conversion.py "$r" --event-stride 2 > "${r%.json}.pool_conv.log" 2>&1
  rc=$?
  if [ $rc -ne 0 ] || [ ! -f "$out" ]; then echo "FAILED rc=$rc $r"; exit 1; fi
done
echo "ALL DONE"
