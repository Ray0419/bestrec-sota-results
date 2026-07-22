#!/usr/bin/env bash
# Build the TORS LaTeX derivative (two targets, round-8; see VENUE_PLAN.md + BUILD_NOTES.md):
#   1. DEFAULT REVIEW TARGET  : main.tex          [manuscript,screen]      -> PAPER_TORS.pdf (gated artifact)
#   2. PRODUCTION PREVIEW     : main-acmsmall.tex [acmsmall,screen] -> PAPER_TORS_acmsmall.pdf (untracked)
#
# Steps (fail-closed at each stage):
#   [1] regenerate paper_tex/tables/*.tex from the artifact graph
#       (_bestrec_run/emit_latex_tables.py: hstu_tables.json + hstu_results_manifest.json
#        + mechanical pandoc conversion of the canonical md tables; numeric cross-check inside)
#   [2] tectonic compile of BOTH targets (self-contained; vendored acmart.cls v2.19 (2026-06-27; upgraded 2026-07-21) + ACM-Reference-Format.bst)
#   [3] package PAPER_TORS.pdf (review) + PAPER_TORS_acmsmall.pdf (preview)
#   [4] placeholder / forbidden-claim hygiene scan of the REVIEW artifact (scan_pdf.py; nonzero exit on any hit)
#
# Overridable tool locations:
#   PYTHON   (default: ../_bestrec_run/.venv/Scripts/python.exe)
#   TECTONIC (default: ~/AppData/Local/tectonic/tectonic.exe, else `tectonic` on PATH)
set -euo pipefail

# STRICT BY DEFAULT (audit 2026-07-22 12:49 C1: wrappers must not self-waive).
# A draft build needs an explicit, logged reason:  ./build.sh --draft "reason"
if [ "${1:-}" = "--draft" ]; then
  if [ -z "${2:-}" ]; then echo "FATAL: --draft requires a reason"; exit 2; fi
  export DRAFT_WAIVER=1
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  W_LINE="$(date -u +%Y-%m-%dT%H:%M:%SZ) DRAFT BUILD (waiver): $2"
  echo "$W_LINE" >> "$SCRIPT_DIR/draft_waiver.log"
  echo "$W_LINE"
  shift 2
else
  unset DRAFT_WAIVER
fi
cd "$(dirname "$0")"

PYTHON="${PYTHON:-../_bestrec_run/.venv/Scripts/python.exe}"
if [ -z "${TECTONIC:-}" ]; then
  for CAND in "$HOME/AppData/Local/tectonic/tectonic.exe" \
              "${LOCALAPPDATA:-}/tectonic/tectonic.exe" \
              "$(command -v tectonic 2>/dev/null || true)"; do
    if [ -n "$CAND" ] && [ -x "$CAND" ]; then TECTONIC="$CAND"; break; fi
  done
fi
if [ -z "${TECTONIC:-}" ] || [ ! -x "$TECTONIC" ]; then
  echo "FATAL: no executable tectonic found (set TECTONIC) -- refusing (audit 15:50 P1)"
  exit 6
fi
echo "tectonic: $TECTONIC"

# epoch AFTER tool/python resolution (audit 16:51 P1); fail closed on unreadable manifest
SCRIPT_DIR0="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -z "$SCRIPT_DIR0" ]; then SCRIPT_DIR0="$(pwd)"; fi   # already inside the script dir
MANIFEST_COMMIT="$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1])).get('git_commit',''))" "$SCRIPT_DIR0/../RELEASE_MANIFEST.json" 2>/dev/null || true)"
if [ -z "$MANIFEST_COMMIT" ] && [ "${ALLOW_HEAD_EPOCH:-}" != "1" ]; then
  echo "FATAL: cannot read git_commit from RELEASE_MANIFEST.json (set ALLOW_HEAD_EPOCH=1 to override for dev builds)"; exit 7
fi
export SOURCE_DATE_EPOCH="$(git log -1 --format=%ct ${MANIFEST_COMMIT:-HEAD} 2>/dev/null || echo 0)"
# carry env across the WSL->Windows boundary (audit 16:51: exports do not cross by default)
export WSLENV="DRAFT_WAIVER/w:SOURCE_DATE_EPOCH/w:PYTHONIOENCODING/w:${WSLENV:-}"

echo "== [1/4] regenerate table includes from the artifact graph =="
# Strict-submission table build FIRST (audit 2026-07-18 19:20): a TORS PDF must never be
# produced from a default-mode hstu_tables.json; the emitter also fail-closes on mode.
"$PYTHON" ../_bestrec_run/build_hstu_tables.py --submission
"$PYTHON" ../_bestrec_run/emit_latex_tables.py

echo "== [2/4] tectonic compile: review target (manuscript) =="
"$TECTONIC" --keep-logs main.tex 2>&1 | tee main_console.log
echo "== [2/4] tectonic compile: production preview (acmsmall) =="
"$TECTONIC" main-acmsmall.tex

echo "== [3/4] package PAPER_TORS.pdf (review) + PAPER_TORS_acmsmall.pdf (preview, untracked) =="
cp -f main.pdf PAPER_TORS.pdf
cp -f main-acmsmall.pdf PAPER_TORS_acmsmall.pdf

echo "== [4/5] tex health gate (undefined refs / lost sections / mangles / figures) =="
"$PYTHON" check_tex_health.py

echo "== [5/5] hygiene scan of the review artifact =="
"$PYTHON" scan_pdf.py PAPER_TORS.pdf

echo "BUILD OK: paper_tex/PAPER_TORS.pdf (review, manuscript) + paper_tex/PAPER_TORS_acmsmall.pdf (preview)"
