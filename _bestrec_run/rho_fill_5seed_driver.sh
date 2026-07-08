#!/usr/bin/env bash
# rho_fill_5seed_driver.sh — EXPERIMENT agent, 2026-06-19
# Priority-(1) per SUPERVISOR cycle-8 FIX-#1: bring the load-bearing titration
# rungs rho=0.66 / 0.91 / 0.94 from 2 seeds (s08,s09) to 5 seeds (add s10,s11,s12),
# BOTH arms (text V2 + ID-only), interaction-mode, FULL eval n_eval=94,762.
# rho=0.66 (MI-equivalent density) is the DECISIVE endpoint the tail-causation
# refutation hinges on (drop it => tail rho_s -0.21 -> -0.94), so it runs FIRST.
#
# SAFETY: never starts while the Beauty GPU job (PID 54896) is alive or while the
# card holds >4000 MiB. Runs jobs strictly sequentially (one GPU job at a time).
# Does NOT relaunch Beauty if it dies. Writes only NEW seed files (no overwrite).
set -u
cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
PY="_bestrec_run/.venv/Scripts/python"
LOCK="_bestrec_run/RHO_FILL_DRIVER.lock"
BEAUTY_PID=54896
echo "[driver] start $(date) pwd=$ROOT" > _bestrec_run/rho_fill_driver.log
echo "active since $(date)" > "$LOCK"

pid_alive () { powershell.exe -NoProfile -Command "if (Get-Process -Id $1 -ErrorAction SilentlyContinue) {'Y'} else {'N'}" 2>/dev/null | tr -d '\r\n'; }
gpu_mem () { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' \r'; }

wait_for_free () {
  while true; do
    local alive mem
    alive="$(pid_alive $BEAUTY_PID)"
    mem="$(gpu_mem)"; [ -z "$mem" ] && mem=99999
    if [ "$alive" = "N" ] && [ "$mem" -lt 4000 ] 2>/dev/null; then
      echo "[driver] GPU free (beauty=$alive mem=${mem}MiB) at $(date)" >> _bestrec_run/rho_fill_driver.log
      return 0
    fi
    echo "[driver] waiting (beauty=$alive mem=${mem}MiB) $(date)" >> _bestrec_run/rho_fill_driver.log
    sleep 60
  done
}

PRE="$PY -u _bestrec_run/run_sasrec_sbert.py Video_Games --epochs 40 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu --time-bias --pos-rab --label-smoothing 0.2 --causal-filter --filter-kernel 8"
TEXT_FLAGS="--text-sim-bias --text-prototypes 512"
ID_FLAGS="--no-sbert"

run_one () {  # $1=seedval $2=rho $3=outbase
  local seed="$1" rho="$2" base="$3"
  for arm in text idonly; do
    local out="_bestrec_run/results_${base/ARM/$arm}_VG.json"
    local log="_bestrec_run/run_${base/ARM/$arm}_VG.log"
    if [ -f "$out" ]; then echo "[driver] SKIP exists $out" >> _bestrec_run/rho_fill_driver.log; continue; fi
    local armflags="$TEXT_FLAGS"; [ "$arm" = "idonly" ] && armflags="$ID_FLAGS"
    wait_for_free
    echo "[driver] LAUNCH $out seed=$seed rho=$rho $(date)" >> _bestrec_run/rho_fill_driver.log
    $PRE $armflags --seed "$seed" --subsample-train-frac "$rho" --subsample-mode interaction --subsample-seed 0 --eval-every 10 --out "$out" > "$log" 2>&1
    echo "[driver] DONE   $out rc=$? $(date)" >> _bestrec_run/rho_fill_driver.log
  done
}

# Priority order: rho=0.66 (decisive) -> 0.91 -> 0.94; seeds 10,11,12.
for sd in 10:20260610 11:20260611 12:20260612; do
  s="${sd%%:*}"; sv="${sd##*:}"
  run_one "$sv" 0.66 "TITRATE_ARM_rho066_seed${s}"
done
for sd in 10:20260610 11:20260611 12:20260612; do
  s="${sd%%:*}"; sv="${sd##*:}"
  run_one "$sv" 0.91 "TITR_ARM_rho091_s${s}"
done
for sd in 10:20260610 11:20260611 12:20260612; do
  s="${sd%%:*}"; sv="${sd##*:}"
  run_one "$sv" 0.94 "TITR_ARM_rho094_s${s}"
done

echo "[driver] ALL DONE $(date)" >> _bestrec_run/rho_fill_driver.log
rm -f "$LOCK"
