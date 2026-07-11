# -*- coding: utf-8 -*-
"""Re-render PAPER_SUBMISSION.md -> _paper_render.html -> PAPER_SUBMISSION.pdf
(Edge headless), then placeholder/lab-language scan + page count."""
import io, os, re, subprocess, sys, time

ROOT = r"C:\Users\rayxc\Documents\R"
MD = os.path.join(ROOT, "PAPER_SUBMISSION.md")
HTML = os.path.join(ROOT, "_paper_render.html")
PDF = os.path.join(ROOT, "PAPER_SUBMISSION.pdf")

import markdown  # noqa: E402

src = io.open(MD, encoding="utf-8").read()
body = markdown.markdown(src, extensions=["tables", "fenced_code", "toc"])

# reuse the existing head/style verbatim
old = io.open(HTML, encoding="utf-8").read()
head = old.split("<body>", 1)[0] + "<body>"
io.open(HTML, "w", encoding="utf-8").write(head + body + "</body></html>")
print("html written:", len(body), "chars body")

edge = None
for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
          r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
    if os.path.exists(p):
        edge = p
        break
assert edge, "Edge not found"

if os.path.exists(PDF):
    os.remove(PDF)
r = subprocess.run([edge, "--headless", "--disable-gpu",
                    "--print-to-pdf=" + PDF, "--no-pdf-header-footer",
                    "file:///" + HTML.replace("\\", "/")],
                   capture_output=True, text=True, timeout=180)
for _ in range(30):
    if os.path.exists(PDF) and os.path.getsize(PDF) > 10000:
        break
    time.sleep(1)
assert os.path.exists(PDF), "PDF not produced: " + (r.stderr or "")[-400:]
print("pdf bytes:", os.path.getsize(PDF))

from pypdf import PdfReader  # noqa: E402
rd = PdfReader(PDF)
text = "\n".join((pg.extract_text() or "") for pg in rd.pages)
pats = [r"\bTODO\b", r"\bTBD\b", r"\bFIXME\b", r"\bXXX\b", r"PLACEHOLDER",
        r"lorem", r"\(v3\.\d\)", r"\[TK", r"\?\?\?", r"\bDEAD\b", r"\bkilled\b",
        r"0\.0100"]
hits = []
for p in pats:
    for m in re.finditer(p, text, re.I if p in (r"lorem", r"PLACEHOLDER") else 0):
        hits.append((p, text[max(0, m.start()-60):m.end()+60].replace("\n", " ")))
print("pages:", len(rd.pages), "| scan:", "CLEAN" if not hits else "%d HITS" % len(hits))
for p, ctx in hits[:20]:
    print("  HIT", p, "::", ctx)
