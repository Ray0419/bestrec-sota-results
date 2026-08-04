#!/usr/bin/env bash
# ⛔ DISABLED (audit 2026-07-24 03:59): E-B / PREREG_TEXTPERM_V1 is VOID,
# and this orchestrator's `git add -f` + push of PLAINTEXT ENDPOINT JSON/NPZ
# before adjudication is exactly the exposure pattern that must not exist.
# Endpoint git-push and pod self-stop-on-push are REMOVED. A corrected E-B V2
# (new code namespace) must store endpoints OUTSIDE git behind a sealed
# importer with hooks/CI, never `git add -f`.
echo "DISABLED: run_all_pod.sh is void (audit 2026-07-24 03:59). E-B V1 is tombstoned; endpoint git-push removed. Use the sealed E-B V2 importer."
exit 3
