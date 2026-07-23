#!/usr/bin/env bash
# One-command pod orchestrator (E-B): bootstrap, run all 8 shards with a
# concurrency cap, then EITHER push results to a git branch (if GIT_PUSH_TOKEN
# is set) or serve cloud/returns over HTTP:8888 for the exposed proxy.
#   GIT_PUSH_TOKEN=<pat> bash cloud/run_all_pod.sh [concurrency]   (default 4)
set -uo pipefail
cd "$(dirname "$0")/.."
CONC="${1:-4}"

bash cloud/bootstrap_pod.sh || { echo "BOOTSTRAP FAILED"; exit 1; }

echo "== running 8 shards, $CONC concurrent =="
mkdir -p cloud/returns
run_one() { python cloud/run_shard.py "cloud/shards/eb_shard$1.json" \
              > "cloud/returns/shard$1.log" 2>&1; }
for i in 0 1 2 3 4 5 6 7; do
  while [ "$(jobs -rp | wc -l)" -ge "$CONC" ]; do sleep 5; done
  run_one "$i" &
  echo "launched shard $i (pid $!)"
done
wait
echo "== ALL SHARDS DONE =="
ls -la cloud/returns/*.tar.gz 2>/dev/null

if [ -n "${GIT_PUSH_TOKEN:-}" ]; then
  echo "== pushing results to branch eb-cloud-results =="
  git checkout -b eb-cloud-results 2>/dev/null || git checkout eb-cloud-results
  git add -f cloud/returns _bestrec_run/attempts/cloud_shard*.jsonl \
      _bestrec_run/results_*_TEXTPERM_*.json \
      _bestrec_run/results_*_TEXTPERM_*.finaleval.json \
      _bestrec_run/results_*_TEXTPERM_*.perusers.npz 2>/dev/null
  git -c user.email=pod@runpod -c user.name=runpod-eb \
      commit -m "E-B cloud results (pod $(hostname))" || true
  git push "https://${GIT_PUSH_TOKEN}@github.com/Ray0419/bestrec-sota-results.git" \
      eb-cloud-results && echo "== RESULTS PUSHED: branch eb-cloud-results ==" \
      || echo "PUSH FAILED (check token)"
else
  echo "== no GIT_PUSH_TOKEN; serving cloud/returns on :8888 =="
  echo "   (stop Jupyter first, then open the 8888 proxy URL to download)"
  cd cloud/returns && python -m http.server 8888
fi
