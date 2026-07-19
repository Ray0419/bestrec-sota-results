# -*- coding: utf-8 -*-
"""Placeholder / claim-hygiene scan for the TORS LaTeX build (PAPER_TORS.pdf).

Mirrors the markdown pipeline's scan (_bestrec_run/render_paper_pdf.py) and adds the
forbidden-claim-wording sweep required by VENUE_PLAN.md:
  - hard-fail placeholder tokens (TODO/TBD/FIXME/XXX/PLACEHOLDER/lorem/???/DEAD/killed/0.0100/...)
  - hard-fail forbidden claim wordings UNLESS they appear in an explicit negation context
    ("statistically significantly better than HSTU-BLaIR" always fails; "paired superiority",
     "official reproduction", "pinned[-...] reproduction" fail without a preceding negation cue --
     the paper legitimately contains these ONLY inside explicit NON-claims)
  - SOTA / state-of-the-art occurrences are FLAGGED with +-80 chars of context and listed for
    manual review (never hard-fail: the paper contains explicit SOTA NON-claims by design)

Usage: python scan_pdf.py [pdf_path]   (default: PAPER_TORS.pdf next to this script)
Exit codes: 0 = pass (review list may be non-empty), 1 = hygiene failure.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "PAPER_TORS.pdf")

from pypdf import PdfReader  # noqa: E402

rd = PdfReader(PDF)
pages = [(pg.extract_text() or "") for pg in rd.pages]
raw = "\n".join(pages)

# normalize: de-hyphenate line breaks, collapse whitespace (PDF extraction artifacts)
norm = re.sub(r"-\n(?=[a-z])", "", raw)
norm = re.sub(r"\s+", " ", norm)

def ctx(text, m, w=80):
    return text[max(0, m.start() - w):m.end() + w].replace("\n", " ")

failures = []
review = []

# ---- 1. placeholder tokens (same family as render_paper_pdf.py) --------------------
PLACEHOLDER_PATS = [
    (r"\bTODO\b", 0), (r"\bTBD\b", 0), (r"\bFIXME\b", 0), (r"\bXXX\b", 0),
    (r"PLACEHOLDER", re.I), (r"lorem", re.I), (r"\(v3\.\d\)", 0), (r"\[TK", 0),
    (r"\?\?\?", 0), (r"\bDEAD\b", 0), (r"\bkilled\b", 0), (r"0\.0100", 0),
]
for pat, flags in PLACEHOLDER_PATS:
    for m in re.finditer(pat, norm, flags):
        failures.append(("placeholder:" + pat, ctx(norm, m)))

# ---- 2. forbidden claim wordings ---------------------------------------------------
# always-fatal (no legitimate negated use exists in the canonical paper):
for m in re.finditer(r"statistically\s+significantly\s+better\s+than\s+HSTU-?BLaIR", norm, re.I):
    failures.append(("forbidden-claim: statistically significantly better than HSTU-BLaIR", ctx(norm, m)))

# fatal unless preceded by a negation cue within a 90-char window
NEG = re.compile(r"\b(not?|no|never|non|nor|without|blocks?|cannot|can't|impossible|rather than|"
                 r"does not|do not|isn'?t|aren'?t|remains?\s+future|instead of|neither)\b", re.I)
NEGATABLE = [
    r"paired\s+superiority",
    r"official\s+reproduction",
    r"pinned(?:[-\s]\w+)?[-\s]reproduction",   # incl. "pinned-environment ... reproduction"
    r"pinned\s+reproduction",
]
for pat in NEGATABLE:
    for m in re.finditer(pat, norm, re.I):
        window = norm[max(0, m.start() - 90):m.start()]
        if NEG.search(window):
            review.append(("negated-ok: " + pat, ctx(norm, m)))
        else:
            failures.append(("forbidden-claim (no negation context): " + pat, ctx(norm, m)))

# ---- 2b. retracted-claim negative-presence sweep (2026-07-19; audits 17:56/18:53/19:56) --
RETRACTED_PATS = [
    r"powered\s+null", r"statistically\s+equivalent\s+to\s+zero", r"TOST-equivalent",
    r"no\s+representation-side\s+lever", r"spectrally\s+irreducible",
    r"binding\s+tail\s+resource", r"connectivity\s+binds", r"tail\s+law",
    r"causal\s+decomposition", r"bitwise-exact", r"first\s+widely-cited",
    r"\(R2\)\s+alone", r"whole\s+double[- ]dissociation",
]
for pat in RETRACTED_PATS:
    for m in re.finditer(pat, norm, re.I):
        failures.append(("retracted-claim: " + pat, ctx(norm, m)))

# ---- 3. SOTA / state-of-the-art sweep (flag + list, manual review; never hard-fail) -
for m in re.finditer(r"state[-\s]of[-\s]the[-\s]art|\bSOTA\b", norm, re.I):
    review.append(("SOTA-mention", ctx(norm, m)))

# ---- report -------------------------------------------------------------------------
out = io.StringIO()
print("hygiene scan:", os.path.basename(PDF), "| pages:", len(rd.pages), file=out)
print("placeholder+forbidden failures:", len(failures), file=out)
for tag, c in failures:
    print("  FAIL", tag, "::", c, file=out)
print("review list (SOTA mentions + negated claim-wordings):", len(review), file=out)
for tag, c in review:
    print("  REVIEW", tag, "::", c, file=out)
print("verdict:", "FAIL" if failures else "PASS (review list above is informational)", file=out)

report = out.getvalue()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
print(report)
io.open(os.path.join(HERE, "hygiene_scan_output.txt"), "w", encoding="utf-8", newline="\n").write(report)
sys.exit(1 if failures else 0)
