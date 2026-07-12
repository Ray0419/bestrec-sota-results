#!/usr/bin/env bash
# Build PAPER_TORS.pdf (ACM TORS LaTeX derivative of the canonical PAPER_SUBMISSION.md).
#
# Steps (fail-closed at each stage):
#   1. regenerate paper_tex/tables/*.tex from the artifact graph
#      (_bestrec_run/emit_latex_tables.py: hstu_tables.json + hstu_results_manifest.json
#       + mechanical pandoc conversion of the canonical md tables; numeric cross-check inside)
#   2. compile with tectonic (self-contained; vendored acmart.cls v2.03 + ACM-Reference-Format.bst)
#   3. rename to PAPER_TORS.pdf
#   4. placeholder / forbidden-claim hygiene scan (scan_pdf.py; nonzero exit on any hit)
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
"$PYTHON" ../_bestrec_run/emit_latex_tables.py

echo "== [2/4] tectonic compile (acmart TORS, review+anonymous) =="
"$TECTONIC" main.tex

echo "== [3/4] package PAPER_TORS.pdf =="
cp -f main.pdf PAPER_TORS.pdf

echo "== [4/4] hygiene scan (placeholders + forbidden claim wordings + SOTA review list) =="
"$PYTHON" scan_pdf.py PAPER_TORS.pdf

echo "BUILD OK: paper_tex/PAPER_TORS.pdf"
