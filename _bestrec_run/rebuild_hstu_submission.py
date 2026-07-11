#!/usr/bin/env python
"""Canonical one-command submission rebuild (acceptance-repair-plan Phase 9).

    uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict

Runs, in order: (1) the HSTU core-block parity test, (2) the artifact-graph
table build (strict/fail-closed mode when --strict), (3) the MI V2 gate
adjudicator, (4) the Office adjudicator (reported as VOID/descriptive under its
prereg floor check). Exits nonzero if any strict step fails."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
STRICT = "--strict" in sys.argv


def run(label, args, required=True):
    print(f"\n=== {label} ===")
    r = subprocess.run([PY] + args, cwd=str(ROOT))
    ok = r.returncode == 0
    print(f"--- {label}: {'OK' if ok else f'FAILED (exit {r.returncode})'}")
    return ok or not required


def main():
    ok = True
    ok &= run("HSTU core-block parity test", ["_bestrec_run/test_hstu_parity.py"])
    build_args = ["_bestrec_run/build_hstu_tables.py"]
    if STRICT:
        # accept either flag spelling of the fail-closed mode
        import io
        src = io.open(ROOT / "_bestrec_run" / "build_hstu_tables.py", encoding="utf-8").read()
        build_args.append("--strict-submission" if "--strict-submission" in src else "--submission")
    ok &= run("Artifact-graph table build" + (" (strict)" if STRICT else ""), build_args)
    if STRICT:
        # round-3 audit F1: the release manifest must describe the submitted
        # tree; verify file-by-file, fail closed on any drift
        ok &= run("Release-manifest verification",
                  ["_bestrec_run/update_release_manifest.py", "--verify"])
    ok &= run("MI V2 gate adjudication", ["_bestrec_run/summarize_sota_confirm_v2.py"])
    # Office is VOID/descriptive under its prereg floor check — report, non-gating
    run("Office adjudication (descriptive; VOID under prereg floor check)",
        ["_bestrec_run/office_prereg_tools.py", "adjudicate"], required=False)
    print(f"\n=== SUBMISSION REBUILD: {'PASS' if ok else 'FAIL'} ===")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
