#!/usr/bin/env bash
# PREREG_RHO_K_V1 AMENDMENT A1: E3 trainings -> E3/E1/E2/E4/appendix evals.
set -u
cd "C:/Users/rayxc/Documents/R/.claude/worktrees/brave-rhodes-0a7d09/_bestrec_run"
PY="C:/Users/rayxc/Documents/R/_bestrec_run/.venv/Scripts/python.exe"
echo "== PHASE 1: Steam stage-2 trainings (12 cells) =="
"$PY" -u poc_scale_loss_driver.py --steam --stage2 24 || exit 1
echo "== PHASE 2: E3 pool_conv Steam seeds 739/740 =="
for s in 20260739 20260740; do
  r="poc_out/results_SXL_fce_d256_STEAM_seed${s}.json"
  o="${r%.json}.pool_conv.json"
  [ -f "$o" ] || { "$PY" -u poc_pool_conversion.py "$r" --event-stride 2 > "${r%.json}.pool_conv.log" 2>&1 || exit 1; }
  echo "[done] $o"
done
echo "== PHASE 3: E1/E2 cov_trade (MI n=5 + Steam n=5) =="
for s in 20260736 20260737 20260738 20260739 20260740; do
  for ds in MI STEAM; do
    r="poc_out/results_SXL_fce_d256_${ds}_seed${s}.json"
    o="${r%.json}.cov_trade.json"
    [ -f "$o" ] || { "$PY" -u poc_coverage_trade.py "$r" --event-stride 2 > "${r%.json}.cov_trade.log" 2>&1 || exit 1; }
    echo "[done] $o"
  done
done
echo "== PHASE 4: E4 inner-window pool_conv (MI n=5) =="
for s in 20260736 20260737 20260738 20260739 20260740; do
  r="poc_out/results_SXL_fce_d256_MI_seed${s}.json"
  o="poc_out/results_SXL_fce_d256_MI_seed${s}.pool_conv_inner.json"
  [ -f "$o" ] || { "$PY" -u poc_pool_conversion.py "$r" --event-stride 2 --window inner --out "$o" > "${o%.json}.log" 2>&1 || exit 1; }
  echo "[done] $o"
done
echo "== PHASE 5: appendix gbce/sce pool_conv (MI d256 n=5) =="
for loss in gbce sce; do
  for s in 20260736 20260737 20260738 20260739 20260740; do
    r="poc_out/results_SXL_${loss}_d256_MI_seed${s}.json"
    o="${r%.json}.pool_conv.json"
    [ -f "$o" ] || { "$PY" -u poc_pool_conversion.py "$r" --event-stride 2 > "${r%.json}.pool_conv.log" 2>&1 || exit 1; }
    echo "[done] $o"
  done
done
echo "A1 CAMPAIGN ALL DONE"
