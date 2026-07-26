#!/usr/bin/env python
"""Canonical one-command submission rebuild (acceptance-repair-plan Phase 9).

    uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict

Runs the HSTU parity test, fail-closed artifact graph, release-manifest check,
all counted or paper-printed campaign adjudicators, and the descriptive Office
V1 adjudicator. Exits nonzero if any strict step fails."""
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
    if STRICT:
        # audit 2026-07-19 13:47 CP-2: the counted MI gate must be verdict-parsed too
        def run_mi_verdict():
            r = subprocess.run([PY, "_bestrec_run/summarize_sota_confirm_v2.py"],
                               cwd=str(ROOT), capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
            good = r.returncode == 0 and "DUAL GATE VERDICT: PASS" in out
            print(f"--- MI V2 gate adjudication (counted; must PASS): "
                  f"{'OK' if good else 'FAILED (verdict not confirmed)'}")
            if not good:
                print(out[-2000:])
            return good
        ok &= run_mi_verdict()
    else:
        ok &= run("MI V2 gate adjudication", ["_bestrec_run/summarize_sota_confirm_v2.py"])
    if STRICT:
        # audit 2026-07-18 21:30 CP-3: every COUNTED campaign's live adjudicator must
        # gate the strict build (exit codes alone don't carry the verdict -- parse it).
        def run_verdict(label, args, needles):
            r = subprocess.run([PY] + args, cwd=str(ROOT), capture_output=True, text=True)
            out = (r.stdout or "") + (r.stderr or "")
            good = r.returncode == 0 and all(n in out for n in needles)
            print(f"--- {label}: {'OK' if good else 'FAILED (verdict not confirmed)'}")
            if not good:
                print(out[-2000:])
            return good
        ok &= run_verdict("Office V3 adjudication (counted; must PASS)",
                          ["_bestrec_run/adjudicate_office_v3.py", "--no-append"],
                          ["CAMPAIGN VERDICT: PASS"])
        ok &= run_verdict("TFV2 repaired-estimand adjudication (counted integrity gate; "
                          "Git-declared frozen rules; outcome-visible per S5.3(vii); ALL PASS required)",
                          ["_bestrec_run/adjudicate_tfv2.py"],
                          ["PRIMARY FAMILY VERDICT: ALL PASS"])
        ok &= run_verdict("FIR-breadth frozen-rule adjudication (artifact-integrity: verifies the recorded pre-declared rule fired; its paired interpretation is withdrawn, manuscript S5.2)",
                          ["_bestrec_run/adjudicate_fir_breadth.py", "--no-append"],
                          ["Industrial_and_Scientific: ARTIFACT-PASS",
                           "CDs_and_Vinyl: ARTIFACT-PASS"])
        # audit 2026-07-23 15:59: printed E-F/E-G results must be graph-gated.
        ok &= run_verdict("E-A FIR_V3 matched-arm adjudication (pre-declared; "
                          "W-POS required)",
                          ["_bestrec_run/adjudicate_fir_v3.py"],
                          ["VERDICT: W-POS"])
        ok &= run_verdict("Canonical FIR breadth adjudication (pre-declared; "
                          "matched-init CANON-BREADTH-POS required)",
                          ["_bestrec_run/adjudicate_fir_canonical_breadth.py"],
                          ["VERDICT: CANON-BREADTH-POS",
                           "Industrial_and_Scientific: Holm",
                           "CDs_and_Vinyl: Holm"])
        ok &= run_verdict("E-F HYBRID_V1 fresh-seed adjudication (pre-declared; "
                          "W-H-POS x3 required)",
                          ["_bestrec_run/adjudicate_hybrid_v1.py"],
                          ["VERDICT MI: W-H-POS", "VERDICT IS: W-H-POS",
                           "VERDICT VG: W-H-POS"])
        ok &= run_verdict("E-G COLDFUSE sensitivity adjudication (outcome-visible/"
                          "protocol-deviated; artifact-reproduction gate ONLY, "
                          "no confirmatory status)",
                          ["_bestrec_run/adjudicate_coldfuse_v1.py"],
                          ["CLASSIFICATION: post-outcome sensitivity "
                           "adjudication (v3)"])
    # Office is VOID/descriptive under its prereg floor check — report, non-gating
    run("Office adjudication (descriptive; VOID under prereg floor check)",
        ["_bestrec_run/office_prereg_tools.py", "adjudicate"], required=False)
    print(f"\n=== SUBMISSION REBUILD: {'PASS' if ok else 'FAIL'} ===")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
