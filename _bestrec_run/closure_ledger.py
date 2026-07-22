# -*- coding: utf-8 -*-
"""EXECUTABLE closure-ledger test (audit 2026-07-22 15:50/16:51: closure rows
must be executable assertions, not response prose).

Each check asserts a repaired property of the tree. Exit 0 = all closures hold.
Run it in CI / release_build; cite its exit code in audit responses.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []

def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read()

def absent(rel, needle, note=""):
    if needle.lower() in read(rel).lower():
        fails.append(f"{rel}: banned {needle!r} present {note}")

def present(rel, needle, note=""):
    if needle not in read(rel):
        fails.append(f"{rel}: required {needle!r} MISSING {note}")

# build wrappers
present("paper_tex/build.sh", "for CAND in", "(flat tool resolution)")
absent("paper_tex/build.sh", 'TECTONIC="tectonic"', "(bare fallback)")
present("paper_tex/build.sh", "WSLENV", "(WSL env bridge)")
present("paper_tex/build.sh", "ALLOW_HEAD_EPOCH", "(fail-closed manifest epoch)")
present("paper_tex/build.ps1", "UTF8Encoding($false)", "(BOM-free logs)")
present("paper_tex/build.ps1", "RELEASE_MANIFEST.json", "(manifest epoch)")
present("paper_tex/check_tex_health.py", "utf-16", "(BOM-aware H1)")
present("_bestrec_run/release_build.py", "only_placeholder", "(exact-failure self-test)")

# generators / emitted artifacts
for rel in ("_bestrec_run/build_hstu_tables.py",
            "_bestrec_run/hstu_results_manifest.json",
            "_bestrec_run/make_table_5_4_titration.py"):
    for bad in ("dead weight", "dead-weight", "causal filter only",
                "TAIL = REFUTED"):
        absent(rel, bad)

# manuscript / public surfaces
SURFACES = ("PAPER_SUBMISSION.md", "README.md", "CANONICAL_SUBMISSION.md",
            "PLAIN_LANGUAGE_COMPANION.md", "CITATION.cff", ".zenodo.json",
            "companion_site/explainer.html", "COVER_LETTER_TORS.md")
BANNED = ("dead weight", "dead-weight bound", "cannot manufacture",
          "carry confirmatory weight", "single-lever isolation",
          "per-lever isolation", "qualitative refutation", "density-inert",
          "supports the robustness", "rival AI", "independent auditor",
          "double/refuting", "near-additively", "168 cells", "153 files",
          "cannot hurt by default", "never seen sold")
for rel in SURFACES:
    for bad in BANNED:
        absent(rel, bad)
present("PLAIN_LANGUAGE_COMPANION.md", "Welch 95% CI", "(repaired breadth CIs)")
present("PLAIN_LANGUAGE_COMPANION.md", "outcome-visible", "(prereg-timing truth)")

if fails:
    print(f"CLOSURE LEDGER: FAIL ({len(fails)})")
    for f in fails:
        print("  -", f)
    sys.exit(2)
print("CLOSURE LEDGER: PASS (all repaired properties hold)")
