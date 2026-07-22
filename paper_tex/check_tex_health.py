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
    # audit 2026-07-22 14:50 P1: a log is only evidence if the compiler FINISHED
    if not re.search(r"Writing `?main(-acmsmall)?\.pdf", log):
        fails.append("H1: compiler completion marker missing from main_console.log "
                     "(no 'Writing main.pdf' -- stale or failed build)")
    for badpat in ("command not found", "CommandNotFound", "error: cannot open"):
        if badpat in log:
            fails.append(f"H1: tool-error class in log: {badpat!r}")

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
              "CI excl 0)", "paired text-ID", "powered", "tail-win band",
              "crosses to a tail win", "point crosses")
for f in _g2.glob(os.path.join(HERE, "..", "_bestrec_run", "make_fig_*.py")):
    src = io.open(f, encoding="utf-8", errors="replace").read()
    for patb in FIG_BANNED:
        if patb in src:
            i = src.find(patb)
            fails.append(f"H6: retracted/stale string {patb!r} in {os.path.basename(f)}: "
                         f"...{src[max(0, i-40):i+40]!r}...")

# ---- [H10] cascade/stale-phrase gate (added 2026-07-22, audit 10:47 problem 1) ----
# The md->TeX mirror failed silently: withdrawn phrases survived in compiled
# sections while the canonical md moved on. Ban them in BOTH the compiled sources
# and the extracted PDF text. Placeholders are fatal only in submission mode.
H10_BANNED = ("external auditor", "exactly the commit carrying",
              "orthogonal to global density", "regime-dependent on catalog density",
              "every capacity-adding probe was neutral",
              "wins the rare-item tail", "dataset-conditional long-tail pattern",
              "pre-registered",
              # audit 2026-07-22 13:50 problems 3/4:
              "carries the generalization", "carries the cross-category",
              "near-additively", "orthogonal axes", "dead weight confirmed",
              "confirmed under the valid", "cannot manufacture",
              "carry confirmatory weight", "a unidentified",
              "never seen sold", "168 cells", "153 files")
H10_BANNED_RE = (r"residual[^.\n]{0,60}content component",)
_pub10 = [os.path.join(HERE, "..", rel) for rel in (
    "PAPER_SUBMISSION.md", "README.md", "COVER_LETTER_TORS.md", "CANONICAL_SUBMISSION.md",
    "PLAIN_LANGUAGE_COMPANION.md", "CITATION.cff", ".zenodo.json",
    os.path.join("companion_site", "explainer.html"))]
_all10 = "\n".join(io.open(f, encoding="utf-8", errors="replace").read()
                   for f in (_g2.glob(os.path.join(HERE, "sections", "*.tex"))
                             + _g2.glob(os.path.join(HERE, "tables", "*.tex"))
                             + [f for f in _pub10 if os.path.exists(f)]))
_all10_low = _all10.lower()
for _b10 in H10_BANNED:
    if _b10.lower() in _all10_low:
        fails.append(f"H10: stale/withdrawn phrase in compiled sources: {_b10!r}")
for _br10 in H10_BANNED_RE:
    m10 = re.search(_br10, _all10)
    if m10:
        fails.append(f"H10: stale/withdrawn pattern in compiled sources: {m10.group(0)[:60]!r}")
_extra10 = ""
for _p10 in (os.path.join(HERE, "PAPER_TORS_acmsmall.pdf"),
             os.path.join(HERE, "..", "PAPER_SUBMISSION.pdf")):
    if os.path.exists(_p10):
        try:
            from pypdf import PdfReader as _R10
            _extra10 += "\n".join((pg.extract_text() or "")
                                   for pg in _R10(_p10).pages)
        except Exception as _e10:
            fails.append(f"H10: could not extract {os.path.basename(_p10)}: {_e10}")
if os.path.exists(pdf_path):
    _flat10 = re.sub(r"\s+", " ", text + " " + _extra10)
    for _b10 in H10_BANNED:
        if _b10 in _flat10:
            fails.append(f"H10: stale/withdrawn phrase in the compiled PDF: {_b10!r}")
    for _br10 in H10_BANNED_RE:
        m10 = re.search(_br10, _flat10)
        if m10:
            fails.append(f"H10: stale/withdrawn pattern in the compiled PDF: {m10.group(0)[:60]!r}")
    if "[Maintainer:" in _flat10:
        msg10 = ("H10: '[Maintainer:' placeholder present in the PDF (byline/contact "
                 "fields pending) -- strict by default")
        if os.environ.get("DRAFT_WAIVER") == "1":
            print("  NOTE", msg10, "[DRAFT_WAIVER=1 active -- logged, non-fatal]")
        else:
            fails.append(msg10 + " -- set DRAFT_WAIVER=1 to build a draft")

# ---- [H9] citation-graph parity (added 2026-07-21, audit 22:57 fix 6) ------------
# Every bib entry must be cited by a real citation command; \nocite{*} is banned
# (it masked 37 orphan/prose-only entries until this round).
_bib9 = io.open(os.path.join(HERE, "references.bib"), encoding="utf-8",
                errors="replace").read()
_keys9 = re.findall(r"@\w+\{([^,\s]+),", _bib9)
_tex9 = ""
for f in (_g2.glob(os.path.join(HERE, "sections", "*.tex"))
          + _g2.glob(os.path.join(HERE, "tables", "*.tex"))
          + _g2.glob(os.path.join(HERE, "*.tex"))):
    _tex9 += io.open(f, encoding="utf-8", errors="replace").read()
if re.search(r"^[^%\n]*\\nocite\{\*\}", _tex9, re.M):
    fails.append("H9: blanket \\nocite{*} present (masks orphan bib entries)")
_cited9 = set()
for c in re.findall(r"\\cite(?:p|t|alp|alt|author|year)?\*?(?:\[[^\]]*\])?\{([^}]+)\}",
                    _tex9):
    for k in c.split(","):
        _cited9.add(k.strip())
_orph9 = [k for k in _keys9 if k not in _cited9]
if _orph9:
    fails.append(f"H9: {len(_orph9)} bib entr{'y' if len(_orph9) == 1 else 'ies'} "
                 f"never cited by any command: {_orph9[:6]}")
# reverse direction (audit 01:01: the one-way check missed an undefined citation
# that visibly rendered as '?'): every cited key must have a bib entry, and the
# BibTeX 'didn't find a database entry' warning is fatal.
_undef9 = sorted(set(_cited9) - set(_keys9))
if _undef9:
    fails.append(f"H9: {len(_undef9)} citation key(s) with NO bib entry "
                 f"(renders as '?'): {_undef9[:6]}")
_log9 = os.path.join(HERE, "main_console.log")
if os.path.exists(_log9):
    _lt9 = io.open(_log9, encoding="utf-8", errors="replace").read()
    for _w9 in re.findall(r"didn't find a database entry for \"([^\"]+)\"", _lt9):
        fails.append(f"H9: BibTeX undefined-entry warning for {_w9!r} (fatal)")

# ---- [H8] duplicated prose sentences (source AND compiled PDF) -------------------
# Added 2026-07-20 (audit 17:54): the generated Ethics section carried interleaved
# duplicate/triplicate sentences that H1-H7 could not see. Any sentence >= 60 chars
# appearing twice in one section/table source, or in the PDF text, is corruption.
def _sentences(txt):
    flatt = re.sub(r"(?m)^%.*$", "", txt)
    flatt = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", flatt)
    flatt = re.sub(r"[{}&$~^]", " ", flatt)
    flatt = re.sub(r"\s+", " ", flatt)
    return [x.strip() for x in re.split(r"(?<=\.)\s+", flatt) if len(x.strip()) >= 60]

for f in sorted(_g2.glob(os.path.join(HERE, "sections", "*.tex"))
                + _g2.glob(os.path.join(HERE, "tables", "*.tex"))):
    sents = _sentences(io.open(f, encoding="utf-8", errors="replace").read())
    seen8 = {}
    for sN in sents:
        seen8[sN] = seen8.get(sN, 0) + 1
    dups = [sN for sN, cN in seen8.items() if cN > 1]
    if dups:
        fails.append(f"H8: {len(dups)} duplicated sentence(s) in "
                     f"{os.path.basename(f)}: {dups[0][:80]!r}...")
if os.path.exists(pdf_path):
    # body prose only: the References section legitimately repeats a verbatim
    # concurrent-preprint disclosure note on several entries
    flat8 = re.sub(r"\s+", " ", text)
    mref8 = None
    for mref8 in re.finditer(r"(?i)\bReferences\b", flat8):
        pass
    if mref8 is not None and mref8.start() > len(flat8) // 2:
        flat8 = flat8[:mref8.start()]
    psents = [x.strip() for x in re.split(r"(?<=\.)\s+", flat8)
              if len(x.strip()) >= 80]
    seen8 = {}
    for sN in psents:
        seen8[sN] = seen8.get(sN, 0) + 1
    dups = [sN for sN, cN in seen8.items() if cN > 1]
    if dups:
        fails.append(f"H8: {len(dups)} duplicated sentence(s) in the compiled PDF: "
                     f"{dups[0][:80]!r}...")

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
