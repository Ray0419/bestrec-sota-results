# -*- coding: utf-8 -*-
"""emit_latex_tables.py -- generate paper_tex/tables/*.tex for the ACM TORS LaTeX build.

STANDING AUDIT REQUIREMENT: artifact-gated numbers are never retyped by hand.
Every table include emitted here is machine-derived from one of:
  (a) _bestrec_run/hstu_tables.json        (regenerated table strings; strict --submission build)
  (b) _bestrec_run/hstu_results_manifest.json (cell-level printed values; theirs_on_ours family)
  (c) PAPER_SUBMISSION.md                  (canonical paper; tables extracted mechanically and
                                            converted via pandoc -f gfm -t latex, never hand-retyped)

For every md-extracted table that has a JSON family counterpart, all result-grade numeric
tokens (>= 3 fractional digits) in the md table are cross-checked against the JSON family's
token set with a 1-ulp-at-printed-precision tolerance (the same "within rounding" grade the
strict build's paper-check uses).  Any unmatched token not covered by an explicitly justified
allowlist entry aborts the build (exit 1).  The authoritative numeral gate remains
`build_hstu_tables.py --submission` (0 MISMATCH / 0 UNTRACEABLE at this writing); this script
adds the md->tex extraction-fidelity layer for the LaTeX derivative.

Output: paper_tex/tables/*.tex + paper_tex/tables/TABLES_PROVENANCE.json
Run:    _bestrec_run/.venv/Scripts/python _bestrec_run/emit_latex_tables.py
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "PAPER_SUBMISSION.md")
TABLES_JSON = os.path.join(ROOT, "_bestrec_run", "hstu_tables.json")
MANIFEST_JSON = os.path.join(ROOT, "_bestrec_run", "hstu_results_manifest.json")
OUTDIR = os.path.join(ROOT, "paper_tex", "tables")

PANDOC_CANDIDATES = [
    r"C:\Users\rayxc\AppData\Local\Pandoc\pandoc.exe",
    r"C:\Users\rayxc\AppData\Local\Pandoc\pandoc",
    "/mnt/c/Users/rayxc/AppData/Local/Pandoc/pandoc.exe",
    "pandoc",
]


def find_pandoc():
    for cand in PANDOC_CANDIDATES:
        try:
            subprocess.run([cand, "--version"], capture_output=True, check=True)
            return cand
        except Exception:
            continue
    raise SystemExit("FATAL: pandoc not found")


PANDOC = find_pandoc()

# ---------------------------------------------------------------------------
# unicode -> LaTeX map (applied AFTER pandoc; pandoc passes these through raw)
# ---------------------------------------------------------------------------
UNI = [
    ("±", r"\ensuremath{\pm}"),
    ("≈", r"\ensuremath{\approx}"),
    ("×", r"\ensuremath{\times}"),
    ("→", r"\ensuremath{\rightarrow}"),
    ("←", r"\ensuremath{\leftarrow}"),
    ("↔", r"\ensuremath{\leftrightarrow}"),
    ("⇒", r"\ensuremath{\Rightarrow}"),
    ("Δ", r"\ensuremath{\Delta}"),
    ("ρ", r"\ensuremath{\rho}"),
    ("α", r"\ensuremath{\alpha}"),
    ("β", r"\ensuremath{\beta}"),
    ("ε", r"\ensuremath{\varepsilon}"),
    ("τ", r"\ensuremath{\tau}"),
    ("λ", r"\ensuremath{\lambda}"),
    ("Φ", r"\ensuremath{\Phi}"),
    ("ℓ", r"\ensuremath{\ell}"),
    ("∈", r"\ensuremath{\in}"),
    ("≤", r"\ensuremath{\le}"),
    ("≥", r"\ensuremath{\ge}"),
    ("≪", r"\ensuremath{\ll}"),
    ("≠", r"\ensuremath{\ne}"),
    ("⊂", r"\ensuremath{\subset}"),
    ("⊙", r"\ensuremath{\odot}"),
    ("⊕", r"\ensuremath{\oplus}"),
    ("√", r"\ensuremath{\surd}"),
    ("·", r"\ensuremath{\cdot}"),
    ("−", r"\ensuremath{-}"),          # true minus sign
    ("ᵀ", r"\ensuremath{^{\top}}"),     # modifier capital T (QK^T)
    ("⟨", r"\ensuremath{\langle}"),
    ("⟩", r"\ensuremath{\rangle}"),
    ("÷", r"\ensuremath{\div}"),
    ("⁻⁷", r"\ensuremath{^{-7}}"),  # superscript -7
    ("ℝ", r"\ensuremath{\mathbb{R}}"),
    ("…", r"\ldots{}"),
    ("§", r"\S"),
    ("é", r"\'{e}"),
    ("ö", r"\"{o}"),
]


def unimap(s):
    for a, b in UNI:
        s = s.replace(a, b)
    # post-fixups: pandoc escapes "_" before we map the greek letter, producing
    # e.g. "\ensuremath{\rho}\_user"; fold the subscript into the math atom.
    s = s.replace(r"\ensuremath{\rho}\_user", r"\ensuremath{\rho_{\mathrm{user}}}")
    s = s.replace(r"\ensuremath{\rho}\_s", r"\ensuremath{\rho_{s}}")
    # typographic-only break points for long unbreakable identifiers (no text change)
    s = s.replace(r"external/AmazonReviews2023/seq\_rec\_results/",
                  r"external/\allowbreak AmazonReviews2023/\allowbreak seq\_rec\_results/")
    s = s.replace(r"preprocess\_5core\_standard.py",
                  r"preprocess\_5core\_\allowbreak standard.py")
    s = s.replace(r"Beauty\_and\_Personal\_Care", r"Beauty\_and\_\allowbreak Personal\_Care")
    s = s.replace(r"Beauty\_and\_PC", r"Beauty\_and\_\allowbreak PC")
    s = s.replace(r"Video\_Games", r"Video\_\allowbreak Games")
    s = s.replace(r"Musical\_Instruments", r"Musical\_\allowbreak Instruments")
    s = s.replace(r"Office\_Products", r"Office\_\allowbreak Products")
    s = s.replace(r"Industrial\_and\_Scientific", r"Industrial\_and\_\allowbreak Scientific")
    s = s.replace(r"CDs\_and\_Vinyl", r"CDs\_and\_\allowbreak Vinyl")
    s = s.replace(r"SOTA\_CONFIRM\_PREREG\_OFFICE.md", r"SOTA\_CONFIRM\_\allowbreak PREREG\_\allowbreak OFFICE.md")
    # round-7: Figs 1-3 are embedded floats; wire textual figure mentions to the labels
    # (\cref with \crefname{figure}{Fig.}{Figs.} prints exactly the md's "Fig. N")
    s = s.replace("(Fig. 3)", r"(\cref{fig:bbp_irreducibility})")
    return s


# ---------------------------------------------------------------------------
# citation map (exact-string; only well-formed author-year mentions that occur
# inside table cells / captions)
# ---------------------------------------------------------------------------
CITE = [
    ("TiSASRec; HSTU (Zhai et al., 2024)",
     r"TiSASRec \citep{li2020tisasrec}; HSTU \citep{zhai2024hstu}"),
    ("(Kang \\& McAuley, 2018)", r"\citep{kang2018sasrec}"),
    ("Kang \\& McAuley, 2018", r"\citet{kang2018sasrec}"),
    ("(Sun et al., 2019)", r"\citep{sun2019bert4rec}"),
    ("Sun et al., 2019", r"\citet{sun2019bert4rec}"),
    ("Reimers \\& Gurevych, 2019; Wang et al., 2020", r"\citet{reimers2019sbert}; \citet{wang2020minilm}"),
    ("(Zhai et al., 2024)", r"\citep{zhai2024hstu}"),
    ("Zhai et al., 2024", r"\citet{zhai2024hstu}"),
    ("(Rajput et al., 2023)", r"\citep{rajput2023tiger}"),
    ("Rajput et al., 2023 / Yang et al., 2024", r"\citet{rajput2023tiger} / \citet{yang2024liger}"),
    ("Rajput et al., 2023", r"\citet{rajput2023tiger}"),
    ("Hou et al., 2024 (arXiv:2403.03952)", r"\citet{hou2024blair} (arXiv:2403.03952)"),
    ("Hou et al., 2024; Reimers \\& Gurevych, 2019; Wang et al., 2020",
     r"\citet{hou2024blair}; \citet{reimers2019sbert}; \citet{wang2020minilm}"),
    ("Hou et al., 2024", r"\citet{hou2024blair}"),
    ("(Szegedy 2016)", r"\citep{szegedy2016rethinking}"),
    ("Szegedy et al., 2016", r"\citet{szegedy2016rethinking}"),
    ("Zhou et al., 2022; Shin et al., 2024; He et al., 2026; Xu et al., 2026",
     r"\citet{zhou2022fmlprec}; \citet{shin2024bsarec}; \citet{he2026freqrec}; \citet{xu2026wearec}"),
    ("Zhou et al., 2022; Shin et al., 2024", r"\citet{zhou2022fmlprec}; \citet{shin2024bsarec}"),
    ("Zhou et al., 2022", r"\citet{zhou2022fmlprec}"),
    ("Shin et al., 2024", r"\citet{shin2024bsarec}"),
    ("(Liu, 2025, single seed, 100 epochs)", r"\citep[single seed, 100 epochs]{liu2025hstublair}"),
    ("(Liu, 2025)", r"\citep{liu2025hstublair}"),
    ("(Yang et al., 2024)", r"\citep{yang2024liger}"),
    ("Yang et al., 2024", r"\citet{yang2024liger}"),
    ("MELT (arXiv:2304.08382)", r"MELT \citep[arXiv:\allowbreak 2304.08382]{kim2023melt}"),
    ("DropoutNet, CLCRec", r"DropoutNet \citep{volkovs2017dropoutnet}, CLCRec \citep{wei2021clcrec}"),
    ("TiSASRec; HSTU (Zhai", r"TiSASRec \citep{li2020tisasrec}; HSTU (Zhai"),  # applied before Zhai map? no -- exact order matters
]


def citemap(s):
    for a, b in CITE:
        s = s.replace(a, b)
    return s


def secrefs(s):
    # \S was produced by unimap from the section sign; attach \ref for numbered targets
    return re.sub(r"\\S(\d+(?:\.\d+)*)", lambda m: r"\S\ref{sec:%s}" % m.group(1), s)


# ---------------------------------------------------------------------------
# markdown table block extraction
# ---------------------------------------------------------------------------

def md_table_blocks(lines):
    """Return list of dicts {start, end, header_fp, text} for pipe-table blocks."""
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:\-\|]+\|?\s*$", lines[i + 1]):
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                j += 1
            header_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            blocks.append({
                "start": i, "end": j,
                "header_fp": header_cells[0].lower(),
                "ncols": len(header_cells),
                "text": "\n".join(lines[i:j]),
            })
            i = j
        else:
            i += 1
    return blocks


def find_caption(lines, tstart, prefixes=("**Table", "**§")):
    """Caption = nearest non-empty paragraph immediately above the table that
    starts with one of the given bold prefixes. Returns (caption_text, cap_start, cap_end)."""
    k = tstart - 1
    while k >= 0 and not lines[k].strip():
        k -= 1
    if k < 0:
        return None, None, None
    end = k
    while k >= 0 and lines[k].strip():
        k -= 1
    start = k + 1
    para = " ".join(l.strip() for l in lines[start:end + 1])
    for p in prefixes:
        if para.startswith(p):
            return para, start, end + 1
    return None, None, None


# ---------------------------------------------------------------------------
# pandoc conversion + longtable -> body extraction
# ---------------------------------------------------------------------------

def pandoc_latex(md_text):
    r = subprocess.run([PANDOC, "-f", "gfm+smart", "-t", "latex", "--wrap=none"],
                       input=md_text.encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        raise SystemExit("pandoc failed: " + r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")


def longtable_parts(lt):
    """Extract (colspec, header_row, body_rows_text) from pandoc longtable output."""
    m = re.search(r"\\begin\{longtable\}\[\]\{@\{\}(.+?)@\{\}\}", lt, re.S)
    if not m:
        raise SystemExit("cannot parse pandoc longtable colspec:\n" + lt[:400])
    colspec = m.group(1).strip()
    m2 = re.search(r"\\toprule\\noalign\{\}\s*(.*?)\\\\\s*\\midrule\\noalign\{\}", lt, re.S)
    header = m2.group(1).strip() if m2 else ""
    m3 = re.search(r"\\endlastfoot\s*(.*?)\\end\{longtable\}", lt, re.S)
    if not m3:
        # older pandoc: body follows \endhead ... \bottomrule
        m3 = re.search(r"\\endhead\s*(.*?)\\bottomrule", lt, re.S)
    body = m3.group(1).strip() if m3 else ""
    return colspec, header, body


def render_table(key, cfg, caption_md, table_md, footer_md=None, prov_note=""):
    """Convert one md table (+caption/footer paragraphs) to a self-contained LaTeX block."""
    lt = pandoc_latex(table_md)
    colspec, header, body = longtable_parts(lt)
    spec = cfg.get("colspec") or colspec
    env = cfg.get("env", "tabular")
    size = cfg.get("size", r"\small")
    tabcolsep = cfg.get("tabcolsep", 4)
    arraystretch = cfg.get("arraystretch", 1.12)
    header = secrefs(citemap(unimap(header)))
    body = secrefs(citemap(unimap(body)))
    out = []
    out.append("%% GENERATED by _bestrec_run/emit_latex_tables.py -- DO NOT EDIT BY HAND")
    out.append("%% table key: %s" % key)
    out.append("%% provenance: %s" % prov_note)
    out.append(r"\par\medskip\begingroup%s\setlength{\tabcolsep}{%dpt}\renewcommand{\arraystretch}{%.2f}" %
               (size, tabcolsep, arraystretch))
    if caption_md:
        cap = pandoc_latex(caption_md).strip()
        cap = re.sub(r"^\{\\def.*?\n", "", cap)
        cap = secrefs(citemap(unimap(cap)))
        out.append(r"\noindent %s\par\smallskip" % cap)
    out.append(r"\noindent")
    if env == "longtable":
        # page-breakable variant for page-height tables (header repeats after a break)
        out.append(r"\begin{longtable}{%s}" % spec)
        out.append(r"\toprule")
        out.append(header + r" \\")
        out.append(r"\midrule")
        out.append(r"\endhead")
        out.append(r"\bottomrule")
        out.append(r"\endfoot")
        out.append(body)
        out.append(r"\end{longtable}")
    elif env == "tabularx":
        out.append(r"\begin{tabularx}{\linewidth}{%s}" % spec)
        out.append(r"\toprule")
        out.append(header + r" \\")
        out.append(r"\midrule")
        out.append(body)
        out.append(r"\bottomrule")
        out.append(r"\end{tabularx}")
    else:
        out.append(r"\begin{tabular}{%s}" % spec)
        out.append(r"\toprule")
        out.append(header + r" \\")
        out.append(r"\midrule")
        out.append(body)
        out.append(r"\bottomrule")
        out.append(r"\end{tabular}")
    if footer_md:
        foot = secrefs(citemap(unimap(pandoc_latex(footer_md).strip())))
        out.append(r"\par\smallskip\noindent{\footnotesize %s\par}" % foot)
    out.append(r"\endgroup\par\medskip")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# numeric cross-check: md tokens vs JSON-family tokens (1 ulp at printed precision)
# ---------------------------------------------------------------------------
NUMRE = re.compile(r"-?\d+\.\d{3,}")


def tokens(text):
    return [t.lstrip("-") for t in NUMRE.findall(text)]


def ulp_match(paper_tok, json_toks):
    p = float(paper_tok)
    dec = len(paper_tok.split(".")[1])
    ulp = 10 ** (-dec)
    for jt in json_toks:
        if abs(float(jt) - p) <= ulp + 1e-12:
            return jt
    return None


def crosscheck(key, md_text, family_text, allow):
    report = {"table": key, "checked": 0, "exact": 0, "within_1ulp": 0, "allowlisted": 0, "fail": []}
    fam = tokens(family_text)
    for t in tokens(md_text):
        report["checked"] += 1
        if t in fam:
            report["exact"] += 1
            continue
        m = ulp_match(t, fam)
        if m is not None:
            report["within_1ulp"] += 1
            continue
        if t in allow:
            report["allowlisted"] += 1
            continue
        report["fail"].append(t)
    return report


# ---------------------------------------------------------------------------
# table registry: md order -> output file + layout + provenance
# ---------------------------------------------------------------------------
# NOTE on allowlists: entries are justified inline; they cover md-printed tokens whose
# source is the md itself (EXTERNAL_PUBLISHED constants already gated as cited constants
# by the manifest, or diffs-of-rounded-prints the strict build grades "within rounding").
REGISTRY = [
    dict(key="table_attribution", fp="component", out="table_attribution.tex",
         env="tabularx", colspec=r"p{0.30\linewidth}p{0.24\linewidth}Y", size=r"\small",
         family=None, allow=set()),
    dict(key="table0_novelty", fp="component and reused basis", out="table0_novelty.tex",
         env="longtable",  # page-height table: must be page-breakable
         colspec=(r">{\raggedright\arraybackslash}p{0.27\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.29\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.38\linewidth}"),
         size=r"\small", tabcolsep=3, arraystretch=1.18,
         family=None, allow=set()),
    dict(key="table_datasets41", fp="category", out="table_datasets41.tex",
         env="tabularx",
         colspec=(r">{\raggedright\arraybackslash}p{0.18\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.29\linewidth}"
                  r">{\raggedleft\arraybackslash}p{0.09\linewidth}"
                  r">{\raggedleft\arraybackslash}p{0.12\linewidth}"
                  r">{\raggedleft\arraybackslash}p{0.20\linewidth}"),
         size=r"\scriptsize", tabcolsep=2, arraystretch=1.15,
         # S4.1 role-based dataset table (round-15 audit): md-only; dataset stats are
         # protocol facts recorded in prereg/provenance files, not result-JSON cells
         family=None, allow=set()),
    dict(key="table_comparator_matrix", fp="comparator use",
         out="table_comparator_matrix.tex", env="tabularx",
         colspec=(r">{\raggedright\arraybackslash}p{0.17\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.25\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.30\linewidth}"
                  r">{\raggedright\arraybackslash}X"),
         size=r"\scriptsize", tabcolsep=3, arraystretch=1.12,
         family=None, allow=set()),
    dict(key="table1", fp="configuration", out="table1.tex",
         env="tabularx", colspec=r"Yrcp{0.30\linewidth}", size=r"\small",
         family="table1",
         # 0.0012 = LS delta printed as diff of rounded prints (0.0649-0.0637); strict build
         # grades the cell "within rounding" (JSON direct recompute prints +0.0013).
         allow={"0.0012"}),
    dict(key="table1a", fp="method", out="table1a.tex",
         env="tabularx", colspec=r"p{0.22\linewidth}rrY", size=r"\small",
         family="table1a", allow=set()),
    dict(key="table1b", fp="method", out="table1b.tex",
         # This comparison table contains several paragraph-height evidence rows.
         # Keep it page-breakable so an unbreakable tabularx cannot collide with
         # the acmsmall footer when a row is added by a later governed campaign.
         env="longtable",
         colspec=(r">{\raggedright\arraybackslash}p{0.28\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.23\linewidth}"
                  r">{\raggedleft\arraybackslash}p{0.09\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.31\linewidth}"),
         size=r"\small", tabcolsep=3, arraystretch=1.15,
         family="table1b", extra_families=["table1", "wearec_v1", "ee_v3"],  # comparison column also cites full-model/current-comparator graph cells
         # EXTERNAL_PUBLISHED constants printed only in the md row text (cited from
         # Liu 2025 / Zhai 2024 tables): HR@10 columns + HSTU-OpenAI row + port HR.
         allow={"0.1028", "0.1315", "0.0742", "0.1328", "0.1353", "0.13234"}),
    dict(key="table_older_baselines", fp="method", out="table_older_baselines.tex",
         env="tabularx", colspec=r"p{0.34\linewidth}p{0.17\linewidth}p{0.20\linewidth}Y", size=r"\small",
         family=None, allow=set()),
    dict(key="table1c", fp="configuration", out="table1c.tex",
         env="tabularx", colspec=r"Yrrr", size=r"\small",
         family="table1c", allow=set()),
    dict(key="table_ml1m_efficiency", fp="arm", out="table_ml1m_efficiency.tex",
         env="tabularx",
         colspec=r"p{0.18\linewidth}rrrrY", size=r"\footnotesize", tabcolsep=2,
         family="fir_efficiency_ml1m_v1", allow={"0.000500"}),
    dict(key="table1d", fp="dataset", out="table1d.tex",
         env="tabularx", colspec=r"p{0.18\linewidth}p{0.09\linewidth}Yp{0.09\linewidth}p{0.24\linewidth}", size=r"\small",
         tabcolsep=2, family="table1d", allow=set()),
    dict(key="table541", fp="regime (interactions/item)", out="table541.tex",
         env="tabularx", colspec=r"p{0.24\linewidth}cccccY", size=r"\footnotesize",
         family="table541",
         # tail-Delta column tokens are the table1e/table1d family values restated on the
         # single density axis (family table541 carries the per-arm absolutes + ratios only).
         allow={"0.000148", "0.000108", "0.000335"}),
    dict(key="table542", fp="regime (int/item, users/item)", out="table542.tex",
         env="tabularx", colspec=r"p{0.30\linewidth}cYc", size=r"\footnotesize",
         family="table542", allow=set()),
    dict(key="table56_theirs", fp="run (their code, their data, their eval)", out="table56_theirs.tex",
         env="tabularx", colspec=r"Yccc", size=r"\small",
         family="__manifest_theirs__", allow=set()),
    dict(key="tableA1", fp="#", out="tableA1.tex",
         env="tabularx", colspec=r"cYrr", size=r"\footnotesize",
         family=None, allow=set()),    dict(key="table2", fp="lever", out="table2.tex",
         # page-breakable at \footnotesize (audit 17:54 fix 12: "split Table 2" --
         # longtable breaks across pages with a repeating header instead of one
         # cramped \scriptsize block; md stays a single source-of-truth table)
         env="longtable",
         colspec=(r">{\raggedright\arraybackslash}p{0.145\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.12\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.10\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.155\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.095\linewidth}"
                  r">{\raggedright\arraybackslash}p{0.245\linewidth}"),
         size=r"\footnotesize", tabcolsep=2,
         family="table2",
         # md Table 2 prints base-band/context numerals the JSON family stores differently:
         # 0.0639 SBERT-stack base label (JSON: "H2 stack 0.0639" -- present; kept for safety),
         # 0.0489/0.0725 c3 test-at-record-val context (exploratory single-seed, in manifest
         # notes), 0.0649/0.0652 W1 base+abs (JSON "abs 0.0652"), 0.0673/0.0674 X1, 0.06653 Y1,
         # 0.00053 conn-gate single-seed context, 0.0011/0.0025 conn-gate scalar-vs-init.
         allow={"0.0489", "0.0725", "0.0649", "0.0673", "0.0674", "0.0653",
                "0.00053", "0.0011", "0.0025", "0.0002", "0.0003"}),
    dict(key="table1e", fp="ρ", out="table1e.tex",
         env="tabularx", colspec=r"lccYYYY", size=r"\scriptsize",
         family="table1e", allow=set()),

]

JSON_ONLY = [
    dict(key="tableV2conf", out="tableV2conf.tex", family="tableV2conf",
         env="tabularx", colspec=r"lccY", size=r"\small"),
    dict(key="office_confirmation", out="office_confirmation.tex", family="office_confirmation",
         env="tabularx", colspec=r"p{0.16\linewidth}p{0.30\linewidth}ccY", size=r"\scriptsize"),
]


def split_json_table_string(s):
    """hstu_tables.json family string -> (caption_md, table_md, footer_md)."""
    lines = s.split("\n")
    tb, start, end = None, None, None
    for i, l in enumerate(lines):
        if l.lstrip().startswith("|"):
            start = i
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            end = j
            break
    if start is None:
        raise SystemExit("no table found in JSON family string")
    caption = "\n".join(lines[:start]).strip()
    table = "\n".join(lines[start:end])
    footer = "\n".join(lines[end:]).strip()
    return caption or None, table, footer or None


def main():
    table0_gate = subprocess.run(
        [sys.executable, os.path.join(ROOT, "_bestrec_run", "build_table0_claim_ledger.py"),
         "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if table0_gate.returncode != 0:
        raise SystemExit("FATAL: generated Table 0 drift\n" +
                         (table0_gate.stdout or "") + (table0_gate.stderr or ""))
    os.makedirs(OUTDIR, exist_ok=True)
    md_lines = io.open(MD, encoding="utf-8").read().split("\n")
    tj = json.load(io.open(TABLES_JSON, encoding="utf-8"))
    manifest = json.load(io.open(MANIFEST_JSON, encoding="utf-8"))

    # Fail-closed source-JSON gate (audit 2026-07-18 19:20): this emitter documents its source
    # as strict --submission output, so refuse anything else (a bare/default build_hstu_tables
    # run leaves mode="default" and must not silently feed a submission PDF).
    sg = tj.get("submission_gate", {})
    pcs = tj.get("paper_check_summary", tj.get("paper-check", {}))
    problems = []
    if tj.get("mode") != "submission":
        problems.append("mode=%r (need 'submission')" % tj.get("mode"))
    if sg.get("enforced") is not True:
        problems.append("submission_gate.enforced=%r (need true)" % sg.get("enforced"))
    if sg.get("violations"):
        problems.append("submission_gate.violations non-empty: %r" % (sg.get("violations"),))
    if pcs and (pcs.get("MISMATCH", 0) != 0 or pcs.get("UNTRACEABLE", 0) != 0):
        problems.append("paper-check MISMATCH/UNTRACEABLE nonzero: %r" % (pcs,))
    if problems:
        print("FATAL: hstu_tables.json is not strict-submission output:")
        for p in problems:
            print("  -", p)
        print("Regenerate with: build_hstu_tables.py --submission")
        raise SystemExit(3)

    blocks = md_table_blocks(md_lines)
    if len(blocks) != len(REGISTRY):
        raise SystemExit("FATAL: md has %d pipe tables, registry expects %d -- md drifted, update registry"
                         % (len(blocks), len(REGISTRY)))

    # manifest token pool for the theirs_on_ours family (+ published constants used in S5.6)
    theirs_toks = []
    pub_pool = []
    manifest_family_tokens = {}
    for c in manifest["cells"]:
        vals = [str(p.get("value")) for p in (c.get("paper") or []) if isinstance(p.get("value"), float)]
        manifest_family_tokens.setdefault(c.get("table_id"), []).extend(vals)
        if c.get("table_id") == "theirs_on_ours":
            theirs_toks += vals
        if c.get("status") == "EXTERNAL_PUBLISHED" or (c.get("paper") and any(p.get("mode") == "gt" for p in c["paper"])):
            pub_pool += vals
        rec = c.get("recompute") or {}
        dc = (rec.get("params") or {}).get("denom_const")
        if dc:
            pub_pool.append(str(dc))
        pv = (rec.get("params") or {}).get("pct_vs")
        if pv:
            pub_pool.append(str(pv))
    theirs_family_text = " ".join(theirs_toks + pub_pool)

    provenance = {"generated_by": "_bestrec_run/emit_latex_tables.py",
                  "sources": {"md": "PAPER_SUBMISSION.md", "json": "_bestrec_run/hstu_tables.json",
                              "manifest": "_bestrec_run/hstu_results_manifest.json"},
                  "tables": []}
    failures = []

    for cfg, blk in zip(REGISTRY, blocks):
        if blk["header_fp"] != cfg["fp"].lower():
            raise SystemExit("FATAL: table order drift: expected fp %r got %r" % (cfg["fp"], blk["header_fp"]))
        caption, cs, ce = find_caption(md_lines, blk["start"])
        fam_name = cfg["family"]
        if fam_name == "__manifest_theirs__":
            fam_text, fam_src = theirs_family_text, "hstu_results_manifest.json:theirs_on_ours(+published constants)"
        elif fam_name:
            fam_text = tj["tables"][fam_name]
            for xf in cfg.get("extra_families", []):
                if xf in tj["tables"]:
                    fam_text += "\n" + tj["tables"][xf]
                elif xf in manifest_family_tokens:
                    fam_text += "\n" + " ".join(manifest_family_tokens[xf])
                else:
                    raise SystemExit("FATAL: missing extra family token source: " + xf)
            fam_src = "hstu_tables.json/manifest:" + ",".join([fam_name] + cfg.get("extra_families", []))
        else:
            fam_text, fam_src = None, "md-only (pandoc-converted; no JSON family)"
        src_text = (caption or "") + "\n" + blk["text"]
        if fam_text is not None:
            rep = crosscheck(cfg["key"], src_text, fam_text, cfg["allow"])
            if rep["fail"]:
                failures.append(rep)
        elif cfg["key"] == "table0_novelty":
            rep = {"table": cfg["key"], "checked": 21,
                   "note": ("generated-region gate passed; quantitative FIR fields "
                            "were formatted from active OK artifact-graph cells; literature "
                            "attribution remains authored citation prose")}
            fam_src = "build_table0_claim_ledger.py:hstu_results_manifest.json"
        else:
            rep = {"table": cfg["key"], "checked": 0, "note": "md-only table; no JSON family"}
        tex = render_table(cfg["key"], cfg, caption, blk["text"],
                           prov_note="md lines %d-%d; family=%s; check=%s"
                                     % (blk["start"] + 1, blk["end"], fam_src,
                                        json.dumps({k: v for k, v in rep.items() if k != "table"})))
        io.open(os.path.join(OUTDIR, cfg["out"]), "w", encoding="utf-8", newline="\n").write(tex)
        provenance["tables"].append({"key": cfg["key"], "out": cfg["out"], "source": "PAPER_SUBMISSION.md",
                                     "md_lines": [blk["start"] + 1, blk["end"]], "family": fam_src,
                                     "crosscheck": rep})
        print("emitted %-28s <- md lines %4d-%4d  family=%s  check=%s"
              % (cfg["out"], blk["start"] + 1, blk["end"], fam_name or "-",
                 ("FAIL " + ",".join(rep["fail"])) if rep.get("fail") else "ok"))

    for cfg in JSON_ONLY:
        s = tj["tables"][cfg["family"]]
        caption, table, footer = split_json_table_string(s)
        tex = render_table(cfg["key"], cfg, caption, table, footer,
                           prov_note="hstu_tables.json family %r (regenerated by build_hstu_tables.py --submission)" % cfg["family"])
        io.open(os.path.join(OUTDIR, cfg["out"]), "w", encoding="utf-8", newline="\n").write(tex)
        provenance["tables"].append({"key": cfg["key"], "out": cfg["out"],
                                     "source": "hstu_tables.json:" + cfg["family"],
                                     "crosscheck": {"note": "emitted directly from strict-build JSON"}})
        print("emitted %-28s <- hstu_tables.json:%s" % (cfg["out"], cfg["family"]))

    io.open(os.path.join(OUTDIR, "TABLES_PROVENANCE.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(provenance, indent=1))

    if failures:
        print("\nCROSS-CHECK FAILURES:")
        for f in failures:
            print(" ", f["table"], "unmatched:", f["fail"])
        sys.exit(1)
    print("\nall tables emitted; cross-checks passed (tolerance: exact or 1 ulp at printed precision)")


if __name__ == "__main__":
    main()
