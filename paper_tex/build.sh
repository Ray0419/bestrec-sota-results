#!/usr/bin/env bash
# Build the TORS LaTeX derivative (two targets, round-8; see VENUE_PLAN.md + BUILD_NOTES.md):
#   1. DEFAULT REVIEW TARGET  : main.tex          [manuscript,review,anonymous]      -> PAPER_TORS.pdf (gated artifact)
#   2. PRODUCTION PREVIEW     : main-acmsmall.tex [acmsmall,screen,review,anonymous] -> PAPER_TORS_acmsmall.pdf (untracked)
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
cd "$(dirname "$0")"

PYTHON="${PYTHON:-../_bestrec_run/.venv/Scripts/python.exe}"
if [ -z "${TECTONIC:-}" ]; then
  if [ -x "$HOME/AppData/Local/tectonic/tectonic.exe" ]; then
    TECTONIC="$HOME/AppData/Local/tectonic/tectonic.exe"
  else
    TECTONIC="tectonic"
  fi
fi

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
