#!/usr/bin/env bash
# One-command pod orchestrator (E-B): bootstrap, run all 8 shards with a
# concurrency cap, then serve cloud/returns over HTTP:8000 for exfil.
#   bash cloud/run_all_pod.sh [concurrency]     (default 4)
set -uo pipefail
cd "$(dirname "$0")/.."
CONC="${1:-4}"

bash cloud/bootstrap_pod.sh || { echo "BOOTSTRAP FAILED"; exit 1; }

echo "== running 8 shards, $CONC concurrent =="
pids=()
run_one() { python cloud/run_shard.py "cloud/shards/eb_shard$1.json" \
              > "cloud/returns/shard$1.log" 2>&1; }
mkdir -p cloud/returns
for i in 0 1 2 3 4 5 6 7; do
  while [ "$(jobs -rp | wc -l)" -ge "$CONC" ]; do sleep 5; done
  run_one "$i" &
  echo "launched shard $i (pid $!)"
done
wait
echo "== ALL SHARDS DONE =="
ls -la cloud/returns/*.tar.gz 2>/dev/null

echo "== serving cloud/returns on :8000 (open the pod proxy URL) =="
cd cloud/returns && python -m http.server 8000
