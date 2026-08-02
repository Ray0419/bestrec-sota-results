#!/usr/bin/env bash
# One-shot deployment for the FIR-encoder probe on a fresh CUDA VM
# (Ubuntu 22.04/24.04 image with NVIDIA driver, e.g. Lambda/RunPod/Vast/EC2 g5).
#
#   scp -r fir_encoder_probe/ user@vm:~/ && ssh user@vm 'cd fir_encoder_probe && bash deploy.sh'
#
# Also runs on a CPU/MPS machine (falls back automatically; slower).
# Idempotent: safe to re-run; skips completed steps.
set -euo pipefail
cd "$(dirname "$0")"

echo "== [1/4] python venv"
if [[ ! -d .venv ]]; then
  (command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3) \
    | head -1 | xargs -I{} {} -m venv .venv
fi
source .venv/bin/activate
python -V

echo "== [2/4] dependencies"
pip -q install --upgrade pip
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
  pip -q install torch --index-url https://download.pytorch.org/whl/cu124 || pip -q install torch
else
  echo "no NVIDIA GPU detected - installing default torch (CPU/MPS)"
  pip -q install torch
fi
pip -q install numpy
python - <<'EOF'
import torch
print(f"torch {torch.__version__} cuda={torch.cuda.is_available()}", flush=True)
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))
EOF

echo "== [3/4] MovieLens-1M (official GroupLens archive)"
if [[ ! -f ml-1m/ratings.dat ]]; then
  curl -fLO https://files.grouplens.org/datasets/movielens/ml-1m.zip
  echo "expected md5 c4d9eecfca2ab87c1945afe126590906  (GroupLens-published)"
  md5sum ml-1m.zip || md5 ml-1m.zip || true
  unzip -o -q ml-1m.zip
fi
wc -l ml-1m/ratings.dat

echo "== [4/4] probe"
python fir_encoder_probe.py --data ./ml-1m --out ./results --smoke
echo "-- smoke passed; starting full run (2 arms x 3 seeds + latency scan) --"
rm -rf results && python fir_encoder_probe.py --data ./ml-1m --out ./results
echo "== done. Results: results/probe_results.json (copy back with scp)"
