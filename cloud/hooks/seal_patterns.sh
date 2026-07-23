#!/usr/bin/env bash
# Single source of truth for sequestered-endpoint path patterns (audit
# 2026-07-24: `.gitignore` alone was bypassed by `git add -f`). Both hooks and
# the test source this. A path matching ANY of these must never enter git
# before a sealed one-time adjudication.
SEAL_PATTERNS='results_.*COLDFUSE[23].*|results_.*TEXTPERM.*|\.finaleval\.json$|\.finaleval\.perusers\.npz$|(^|/)eg3_labels|_sealed(/|_|\.)|(^|/)cloud/returns/'
export SEAL_PATTERNS
