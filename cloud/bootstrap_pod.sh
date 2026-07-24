#!/usr/bin/env bash
# RunPod bootstrap (PREREG_TEXTPERM_V1 / cloud campaigns).
# From a bare CUDA pod:  bash <(curl -fsSL <raw-url>/cloud/bootstrap_pod.sh)
# or after manual clone: bash cloud/bootstrap_pod.sh
set -euo pipefail

# HARD-REFUSED (audit 2026-07-24 16:00): PREREG_TEXTPERM_V1 / E-B is VOID (design
# defects: pseudoreplication n=9 from 3 shared seeds, un-normalized random control,
# arm/pod aliasing). This bootstrap cloned + installed + generated caches for the
# voided launcher; it now refuses at entry so the void campaign cannot be revived.
echo "REFUSED: E-B (PREREG_TEXTPERM_V1) is VOID; bootstrap disabled. See cloud/README.md." >&2
exit 3

REPO="https://github.com/Ray0419/bestrec-sota-results.git"
BRANCH="codex/bestrec-sota-results"
WORK="${WORK:-/workspace/R}"

if [ ! -d "$WORK/.git" ]; then
  git clone --depth 50 --branch "$BRANCH" "$REPO" "$WORK"
fi
cd "$WORK"
git checkout "$BRANCH"

python -m pip install --quiet --upgrade pip
# torch: pods usually ship a CUDA torch; install only if missing
python - <<'PY'
import importlib.util, subprocess, sys
if importlib.util.find_spec("torch") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "torch",
                           "--index-url",
                           "https://download.pytorch.org/whl/cu124"])
PY
python -m pip install --quiet numpy scipy pandas

echo "== hash-verified asset bootstrap (release v0.9-audit-evidence) =="
python bootstrap_public_clone.py

echo "== control caches (deterministic; frozen rng) =="
python cloud/make_control_caches.py

echo "== GPU =="
python - <<'PY'
import torch
print("cuda:", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
PY
echo "BOOTSTRAP OK — run:  python cloud/run_shard.py cloud/shards/<shard>.json"
