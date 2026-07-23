#!/usr/bin/env bash
# Install the SEAL git hooks (E-G3 custody; audit 2026-07-24). A fresh clone
# runs this once so `.gitignore` is backed by enforced pre-commit/pre-push
# rejection of sequestered endpoint artifacts. CI mirrors the same check via
# cloud/ci_seal_check.sh so a hook-less clone still fails.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HOOKDIR="$(git rev-parse --git-path hooks)"
mkdir -p "$HOOKDIR"
for h in pre-commit pre-push; do
  cp "$ROOT/cloud/hooks/$h" "$HOOKDIR/$h"
  chmod +x "$HOOKDIR/$h" 2>/dev/null || true
done
echo "SEAL hooks installed to $HOOKDIR (pre-commit, pre-push)."
