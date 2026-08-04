#!/usr/bin/env bash
# PREREG_TAIL_FIR_V2 sequential campaign runner (one GPU job at a time; resumable).
# Runs the frozen command list in order; skips any run whose output JSON already exists
# (never overwrites results_*.json). Logs per run under _bestrec_run/tfv2_logs/.
set -uo pipefail
cd "$(dirname "$0")/.."

mkdir -p _bestrec_run/tfv2_logs
n=0
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  n=$((n+1))
  out=$(echo "$cmd" | sed -n 's/.*--out \([^ ]*\).*/\1/p')
  name=$(basename "$out" .json)
  if [ -f "$out" ]; then
    echo "[$n/64] SKIP (exists): $name"
    continue
  fi
  echo "[$n/64] RUN: $name  ($(date '+%H:%M:%S'))"
  echo "==== attempt $(date '+%F %H:%M:%S') ====" >> "_bestrec_run/tfv2_logs/${name}.log"
  if ! PYTHONIOENCODING=utf-8 bash -c "$cmd" >> "_bestrec_run/tfv2_logs/${name}.log" 2>&1; then
    echo "[$n/64] FAILED: $name (see log)" | tee -a _bestrec_run/tfv2_logs/FAILURES.log
  fi
done < _bestrec_run/tfv2_commands.txt

echo "TFV2 CAMPAIGN QUEUE COMPLETE ($(date '+%F %H:%M:%S'))"
touch _bestrec_run/TFV2_CAMPAIGN.DONE
