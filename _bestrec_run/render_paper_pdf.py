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

# reuse the existing head/style verbatim (+ idempotent additions)
old = io.open(HTML, encoding="utf-8").read()
head = old.split("<body>", 1)[0] + "<body>"
if "break-inside" not in head:  # audit: no dangling table cells across page breaks
    head = head.replace("td,th{", "tr{break-inside:avoid}\ntd,th{", 1)
if "img{" not in head:  # embedded figures scale to text width
    head = head.replace("@page{", "img{max-width:100%;display:block;margin:10px auto}\n@page{", 1)
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

def _count_images(reader):
    n = 0
    for pg in reader.pages:
        try:
            xo = pg["/Resources"].get("/XObject", {})
            n += sum(1 for k in xo if xo[k].get_object().get("/Subtype") == "/Image")
        except Exception:
            pass
    return n
rd = PdfReader(PDF)
text = "\n".join((pg.extract_text() or "") for pg in rd.pages)
pats = [r"\bTODO\b", r"\bTBD\b", r"\bFIXME\b", r"\bXXX\b", r"PLACEHOLDER",
        r"lorem", r"\(v3\.\d\)", r"\[TK", r"\?\?\?", r"\bDEAD\b", r"\bkilled\b",
        r"0\.0100",
        # retracted-claim negative-presence sweep (audits 2026-07-19 17:56 CP-2 /
        # 18:53 CP-1 / 19:56 P1+P3): fail if any retracted claim-form resurfaces.
        r"(?i)powered\s+null", r"(?i)statistically\s+equivalent\s+to\s+zero",
        r"(?i)TOST-equivalent", r"(?i)no\s+representation-side\s+lever",
        r"(?i)spectrally\s+irreducible", r"(?i)binding\s+tail\s+resource",
        r"(?i)connectivity\s+binds", r"(?i)tail\s+law", r"(?i)causal\s+decomposition",
        r"(?i)bitwise-exact", r"(?i)first\s+widely-cited", r"(?i)\(R2\)\s+alone",
        r"(?i)whole\s+double[- ]dissociation"]
hits = []
for p in pats:
    for m in re.finditer(p, text, re.I if p in (r"lorem", r"PLACEHOLDER") else 0):
        hits.append((p, text[max(0, m.start()-60):m.end()+60].replace("\n", " ")))
n_img = _count_images(rd)
if "figures/fig_" in src and n_img == 0:
    hits.append(("figures", "manuscript references figures but the PDF embeds 0 images"))
print("pages:", len(rd.pages), "| images:", n_img,
      "| scan:", "CLEAN" if not hits else "%d HITS" % len(hits))
for p, ctx in hits[:20]:
    print("  HIT", p, "::", ctx)
