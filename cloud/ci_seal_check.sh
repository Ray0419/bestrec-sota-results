#!/usr/bin/env bash
# CI seal check (audit 2026-07-24): fail if the current HEAD tree tracks any
# NEW sequestered-endpoint artifact beyond the frozen pre-exposure forensic
# allowlist (the 54 E-G1/E-G2 COLDFUSE2 artifacts committed before the fix,
# preserved as the exposure record). Hook-less clones still get caught here.
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel)"
. "$ROOT/cloud/hooks/seal_patterns.sh"
ALLOW="$ROOT/cloud/hooks/seal_forensic_allowlist.txt"
tracked="$(git -C "$ROOT" ls-files | grep -E "$SEAL_PATTERNS" || true)"
if [ -z "$tracked" ]; then echo "CI SEAL: clean (no tracked endpoint files)."; exit 0; fi
if [ -f "$ALLOW" ]; then
  new="$(comm -23 <(printf '%s\n' "$tracked" | sort -u) <(sort -u "$ALLOW"))"
else
  new="$tracked"
fi
if [ -n "$new" ]; then
  echo "CI SEAL FAIL: tracked endpoint artifact(s) outside the frozen allowlist:" >&2
  printf '  %s\n' $new >&2
  exit 1
fi
echo "CI SEAL: only frozen pre-exposure forensic artifacts tracked (OK)."
