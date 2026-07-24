#!/usr/bin/env bash
# E-E setup: build an ISOLATED environment for external baselines (AlphaFuse,
# LLM2Emb) so their dependencies never pollute the pinned main _bestrec_run
# venv. Clones AlphaFuse next to (not under) our tree, into ee_baselines/, which
# is gitignored (external third-party code is not part of our governed release).
#
#   bash ee_baselines/setup_ee_env.sh
#
# Idempotent: re-running updates the clone and re-checks deps.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# 1) isolated python venv (separate from _bestrec_run/.venv)
if [ ! -d ".venv_ee" ]; then
  python -m venv .venv_ee || { echo "venv creation failed"; exit 1; }
fi
# shellcheck disable=SC1091
PY=".venv_ee/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv_ee/bin/python"
"$PY" -m pip install --quiet --upgrade pip

# 2) clone AlphaFuse (public, SIGIR 2025) if absent
if [ ! -d "AlphaFuse/.git" ]; then
  git clone --depth 1 https://github.com/Hugo-Chinn/AlphaFuse.git AlphaFuse \
    || { echo "clone failed (network?)"; exit 1; }
fi

# 3) install AlphaFuse deps if it ships a requirements file
if [ -f "AlphaFuse/requirements.txt" ]; then
  "$PY" -m pip install --quiet -r AlphaFuse/requirements.txt || \
    echo "WARN: some AlphaFuse deps failed; inspect AlphaFuse/requirements.txt"
else
  echo "NOTE: AlphaFuse has no requirements.txt at repo root -- read its README"
  echo "      and install its stack into .venv_ee manually (torch, etc.)."
fi

# 4) GPU check in the isolated env
"$PY" - <<'PY'
try:
    import torch
    print("ee env torch:", torch.__version__, "cuda:",
          torch.cuda.is_available())
except Exception as e:
    print("torch not yet in ee env:", e)
PY

echo ""
echo "SETUP DONE. Next (see README_EE.md):"
echo "  1) python export_ar2023_for_baselines.py --categories Office_Products Video_Games --verify"
echo "  2) adapt AlphaFuse's data loader to ee_baselines/export/<cat>/*.jsonl"
echo "     (same users/items/LLOO targets/full-catalog universe as our runs)"
echo "  3) run AlphaFuse on Office_Products + Video_Games; record NDCG@10/HR@10"
echo "  4) freeze PREREG_EE (benchmark) BEFORE reporting any head-to-head number,"
echo "     OR write the documented protocol-exclusion note (README_EE.md rule)."
