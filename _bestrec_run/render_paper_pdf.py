# -*- coding: utf-8 -*-
"""Re-render PAPER_SUBMISSION.md -> _paper_render.html -> PAPER_SUBMISSION.pdf
(Edge headless), then placeholder/lab-language scan + page count."""
import io, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "PAPER_SUBMISSION.md")
HTML = os.path.join(ROOT, "_paper_render.html")
PDF = os.path.join(ROOT, "PAPER_SUBMISSION.pdf")

import markdown  # noqa: E402

src = io.open(MD, encoding="utf-8").read()
body = markdown.markdown(src, extensions=["tables", "fenced_code", "toc"])

# Reuse an existing local shell when present, but remain self-contained in a
# pristine clone.  The fallback is the canonical reader-edition style.
if os.path.exists(HTML):
    old = io.open(HTML, encoding="utf-8").read()
    head = old.split("<body>", 1)[0] + "<body>"
else:
    head = """<!doctype html><html><head><meta charset='utf-8'><style>
body{font-family:Charter,Georgia,serif;font-size:10.5pt;line-height:1.5;color:#111;
max-width:17.2cm;margin:0 auto;padding:1.2cm 0}
h1{font-size:19pt;line-height:1.2;font-family:'Segoe UI',sans-serif}
h2{font-size:14pt;margin-top:22pt;font-family:'Segoe UI',sans-serif}
h3{font-size:11.5pt;font-family:'Segoe UI',sans-serif}
code{font-family:Consolas,monospace;font-size:9pt;background:#f4f4f4;padding:0 2px}
pre{background:#f6f6f6;border:1px solid #ddd;padding:8px;font-size:8.5pt;
overflow-x:hidden;white-space:pre-wrap}
table{border-collapse:collapse;font-size:8.6pt;margin:10px 0;width:100%}
td,th{border:1px solid #ccc;padding:3px 6px;text-align:left;vertical-align:top}
th{background:#f0f0f0;font-family:'Segoe UI',sans-serif}
blockquote{border-left:3px solid #bbb;margin-left:0;padding-left:12px;color:#444}
@page{margin:1.6cm}
</style></head><body>"""
if "break-inside" not in head:  # audit: no dangling table cells across page breaks
    head = head.replace("td,th{", "tr{break-inside:avoid}\ntd,th{", 1)
if "img{" not in head:  # embedded figures scale to text width; never slice across pages
    head = head.replace("@page{", "img{max-width:100%;max-height:92vh;display:block;"
                        "margin:10px auto;page-break-inside:avoid;"
                        "break-inside:avoid}\n@page{", 1)
# The supplemental FIR diagnostic otherwise leaves its concise printed caption
# alone on a nearly blank final page. Canonicalize this targeted rule even when
# reusing a previously generated HTML head, then keep the image/caption spacing
# compact without changing global figure typography.
head = re.sub(r"img\[src\$='fig_fir_response\.png'\]\{[^}]*\}\s*", "", head)
_fir_s1_css = ("img[src$='fig_fir_response.png']{max-width:75%;margin-bottom:2px}\n"
               "p:has(> img[src$='fig_fir_response.png']){margin-bottom:0}\n"
               "p:has(> img[src$='fig_fir_response.png']) + p{margin-top:2px;margin-bottom:0}\n")
head = head.replace("@page{", _fir_s1_css + "@page{", 1)
# Keep the new supplemental Software heading with its figure instead of leaving
# the heading alone below the preceding full-page table.
head = re.sub(r"h3:has\(\+ p > img\[src\$='fig_software_v3_pairs\.png'\]\)\{[^}]*\}\s*", "", head)
_software_s1_css = ("h3:has(+ p > img[src$='fig_software_v3_pairs.png'])"
                    "{break-after:avoid;page-break-after:avoid}\n")
head = head.replace("@page{", _software_s1_css + "@page{", 1)
# Chromium's paged-media margin boxes provide visible reader-edition folios.
# Keep the venue PDFs under acmart control; this affects only the HTML reader.
if "@bottom-center" not in head:
    head = head.replace(
        "@page{margin:1.6cm}",
        "@page{margin:1.6cm;@bottom-center{content:counter(page);"
        "font:8pt 'Segoe UI',sans-serif;color:#555}}",
        1,
    )
# PDF metadata title comes from <title> (audit 10:47: it advertised the html filename)
TITLE = next((ln.lstrip("# ").strip() for ln in src.split("\n") if ln.startswith("# ")),
             "BEST-Rec artifact-gated evaluation study")
import re as _re
if "<title>" in head:
    head = _re.sub(r"<title>.*?</title>", "<title>" + TITLE + "</title>", head,
                   count=1, flags=_re.S)
else:
    head = head.replace("<body>", "<title>" + TITLE + "</title>\n<body>", 1)
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

# Edge stamps wall-clock metadata into otherwise identical output. Normalize
# before pypdf rewrites the object graph for navigation; pypdf preserves the
# normalized values but encodes strings in a form the byte-level normalizer is
# intentionally not expected to rewrite a second time.
from normalize_pdf_metadata import normalize_pdf  # noqa: E402
normalize_pdf(PDF)

# Edge does not emit a document outline for this HTML print path. Add one from
# the canonical level-2 Markdown headings and fail if any target is ambiguous.
# This is deterministic navigation metadata; it does not alter page content.
from pypdf import PdfReader, PdfWriter  # noqa: E402

def _heading_title(line):
    title = line[3:].strip()
    # Strip Markdown emphasis/code delimiters but preserve literal underscores;
    # the Appendix A.0 heading intentionally prints Office_Products.
    return title.replace("`", "").replace("**", "").replace("*", "")

def _norm_text(value):
    return re.sub(r"\s+", " ", value).strip()

_headings = [_heading_title(line) for line in src.splitlines()
             if re.match(r"^## (?!#)", line)]
_pre_outline = PdfReader(PDF)
_page_text = [_norm_text(pg.extract_text() or "") for pg in _pre_outline.pages]
_targets = []
for _title in _headings:
    _probe = _norm_text(_title)
    _candidates = [i for i, value in enumerate(_page_text) if _probe in value]
    if not _candidates:
        _prefix = _probe.split("—", 1)[0].strip()
        _candidates = [i for i, value in enumerate(_page_text)
                       if _prefix and _prefix in value]
    if len(_candidates) != 1:
        raise AssertionError(
            f"reader outline target must resolve exactly once: {_title!r} -> {_candidates}")
    _targets.append((_title, _candidates[0]))

_writer = PdfWriter()
_writer.clone_document_from_reader(_pre_outline)
_writer.page_mode = "/UseOutlines"
for _title, _page_index in _targets:
    _writer.add_outline_item(_title, _page_index)
_outline_tmp = PDF + ".outline.tmp"
with open(_outline_tmp, "wb") as _stream:
    _writer.write(_stream)
os.replace(_outline_tmp, PDF)
print("outline entries:", len(_targets))
print("pdf bytes:", os.path.getsize(PDF))

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
if len(rd.outline) != len(_targets):
    raise AssertionError(f"reader outline count drift: {len(rd.outline)} != {len(_targets)}")
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
# cell-count parity gate (audit 2026-07-20 00:01): the manuscript's printed
# artifact-gated cell count must equal the manifest's recomputed-cell count.
import json as _json
_man = _json.load(open(os.path.join(os.path.dirname(__file__), "hstu_results_manifest.json"),
                       encoding="utf-8"))
_nrec = sum(1 for c in _man["cells"] if c.get("recompute") is not None)
_mm = re.search(r"(\d{3})\s+(?:artifact-gated|cells across)", src)
if not _mm:
    hits.append(("cell-count", "manuscript lacks an 'NNN cells across' count statement"))
elif int(_mm.group(1)) != _nrec:
    hits.append(("cell-count", f"manuscript says {_mm.group(1)} but manifest recomputes {_nrec}"))
n_img = _count_images(rd)
if "figures/fig_" in src and n_img == 0:
    hits.append(("figures", "manuscript references figures but the PDF embeds 0 images"))
print("pages:", len(rd.pages), "| images:", n_img,
      "| scan:", "CLEAN" if not hits else "%d HITS" % len(hits))
for p, ctx in hits[:20]:
    print("  HIT", p, "::", ctx)
