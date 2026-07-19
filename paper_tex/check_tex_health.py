# -*- coding: utf-8 -*-
"""Fail-closed TeX health gate (added 2026-07-19; audits 17:56 CP-1 / 19:56 QA).

The prior hygiene scan checked placeholder/claim wordings only, so a compiled PDF
could silently lose a whole section, carry unresolved references, or print mangled
control sequences. This gate makes those states build failures:

  [H1] main.log contains no undefined references/citations ("LaTeX Warning: Reference",
       "LaTeX Warning: Citation", "There were undefined references").
  [H2] every \\ref/\\cref/\\autoref target used in sections/ + tables/ + main.tex has a
       matching \\label somewhere on the compiled path.
  [H3] no mangled control sequences (a backslash eaten by tooling leaves e.g. "extbf{"
       with no preceding backslash) in any .tex source.
  [H4] required structural labels exist in the sources (the 5.4 mechanism spine and
       both figures -- the content the TORS derivative silently lost once).
  [H5] the compiled PDF embeds >= 2 images and its extracted text contains no "??"
       reference placeholders.

Usage: python check_tex_health.py   (run from paper_tex/, after tectonic --keep-logs)
Exit codes: 0 = pass, 2 = fail.
"""
import glob
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
fails = []

# ---- [H1] log scan -------------------------------------------------------------
log_path = os.path.join(HERE, "main_console.log")
if not os.path.exists(log_path):
    fails.append("H1: main_console.log missing (build.sh must tee the tectonic output)")
else:
    log = io.open(log_path, encoding="utf-8", errors="replace").read()
    for pat in (r"Reference `[^']+' on page \d+ undefined", r"Citation `[^']+'[^\n]*undefined",
                r"There were undefined references"):
        for m in re.finditer(pat, log):
            fails.append("H1: " + log[m.start():m.start() + 90].replace("\n", " "))

# ---- collect sources on the compiled path --------------------------------------
srcs = {}
for pat in ("main.tex", "paper-shared.tex", os.path.join("sections", "*.tex"),
            os.path.join("tables", "*.tex")):
    for f in glob.glob(os.path.join(HERE, pat)):
        srcs[f] = io.open(f, encoding="utf-8", errors="replace").read()
all_src = "\n".join(srcs.values())

# ---- [H2] ref/label cross-check ------------------------------------------------
labels = set(re.findall(r"\\label\{([^}]+)\}", all_src))
refs = set(re.findall(r"\\(?:ref|cref|autoref|pageref)\{([^}]+)\}", all_src))
for r in sorted(refs - labels):
    fails.append(f"H2: reference target has no label: {r}")

# ---- [H3] mangled control sequences --------------------------------------------
for f, s in srcs.items():
    for m in re.finditer(r"(?<![\\A-Za-z])(?:extbf|extit|exttt|mph|itemize|numerate|ef|abel|nput|ection|aption|egin)\{", s):
        ln = s.count("\n", 0, m.start()) + 1
        fails.append(f"H3: mangled control sequence in {os.path.basename(f)}:{ln}: "
                     f"{s[max(0, m.start()-30):m.end()+20]!r}")

# ---- [H4] required structural labels -------------------------------------------
REQUIRED = ("sec:5.4", "sec:5.4.1", "sec:5.4.2", "sec:5.5", "sec:5.6",
            "fig:tail_law_mechanism", "fig:r1r2_plane")
for lab in REQUIRED:
    if lab not in labels:
        fails.append(f"H4: required label missing from sources: {lab}")

# ---- [H5] compiled-PDF checks --------------------------------------------------
pdf_path = os.path.join(HERE, "PAPER_TORS.pdf")
if not os.path.exists(pdf_path):
    fails.append("H5: PAPER_TORS.pdf missing")
else:
    from pypdf import PdfReader
    rd = PdfReader(pdf_path)
    n_img = 0
    for pg in rd.pages:
        try:
            xo = pg["/Resources"].get("/XObject", {})
            n_img += sum(1 for k in xo if xo[k].get_object().get("/Subtype") == "/Image")
        except Exception:
            pass
    n_form = 0
    for pg in rd.pages:
        try:
            xo = pg["/Resources"].get("/XObject", {})
            n_form += sum(1 for k in xo if xo[k].get_object().get("/Subtype") == "/Form")
        except Exception:
            pass
    if n_img + n_form < 2:
        fails.append(f"H5: PDF embeds {n_img} images + {n_form} form XObjects "
                     f"(< 2 required: both figures)")
    text = "\n".join((pg.extract_text() or "") for pg in rd.pages)
    for m in re.finditer(r"(?:§|Fig\.|Figure|Table|Section)\s*\?\?", text):
        fails.append("H5: unresolved '??' reference in PDF text: "
                     + text[max(0, m.start() - 50):m.end() + 20].replace("\n", " "))

# ---- [H6] figure-generator sources must not carry retracted statistics ----------
import glob as _g2
FIG_BANNED = ("t=3.47", "-0.000018", '"0/2"', "binding", "tail law", "causal decomposition",
              "CI excl 0)", "paired text-ID", "powered")
for f in _g2.glob(os.path.join(HERE, "..", "_bestrec_run", "make_fig_*.py")):
    src = io.open(f, encoding="utf-8", errors="replace").read()
    for patb in FIG_BANNED:
        if patb in src:
            i = src.find(patb)
            fails.append(f"H6: retracted/stale string {patb!r} in {os.path.basename(f)}: "
                         f"...{src[max(0, i-40):i+40]!r}...")

# ---- [H7] duplicated load-bearing table titles in the compiled PDF ---------------
if os.path.exists(pdf_path):
    UNIQUE_TITLES = ("interaction-thinning density-titration ladder",)
    flat = re.sub(r"\s+", " ", text)
    for tt in UNIQUE_TITLES:
        cnt = flat.count(tt)
        if cnt > 1:
            fails.append(f"H7: table title appears {cnt}x in the PDF (duplicate caption): {tt!r}")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
print(f"tex health: {len(srcs)} sources, {len(labels)} labels, {len(refs)} ref targets")
for x in fails[:40]:
    print("  FAIL", x)
print("tex health verdict:", "FAIL (%d)" % len(fails) if fails else "PASS")
sys.exit(2 if fails else 0)
