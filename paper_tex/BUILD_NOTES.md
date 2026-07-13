# BUILD_NOTES — ACM TORS LaTeX derivative (`paper_tex/`)

Generated 2026-07-12; synced to the round-7 canonical md (commit `f141cf7`: Figs. 1–3
embedded, new §10 Ethics and Data Governance, Table-0 parity-row rewording, GrIT + FEARec
citations) **+ round-8 packaging** (12:34 audit: two-target class-option restructure +
verified BibTeX metadata fill — see the round-8 sections below); subsequent audit rounds and
the **2026-07-13 FIR-BREADTH sync** (below) are tracked incrementally. **The markdown remains
canonical** (`CANONICAL_SUBMISSION.md` governs; `PAPER_SUBMISSION.md` is the source of
record). This directory is a *derived* typeset format per `VENUE_PLAN.md`: format conversion
only — no content was cut, added, or reworded (two presentation-only additions are disclosed
under "Conversion decisions" below). Compiled outputs:
**`paper_tex/PAPER_TORS.pdf` — the gated review artifact — 40 pages, single-column
`[manuscript,review,anonymous]` acmart format, Figs. 1–3 embedded**, plus the untracked
production preview `PAPER_TORS_acmsmall.pdf` (40 pages, `[acmsmall,screen,review,anonymous]`).

## 2026-07-13 sync (2): OFFICE V3 pre-registered campaign PASSED

Mirrors the canonical md's Office-V3 working-tree deltas (6 hunks, all covered):
(1) abstract apparatus item (iv) gains the redesigned-successor-passed clause, and the results
paragraph gains the "second category passed the redesigned pre-registration" sentence
(K=16 CI-LB 0.03033 / K=8 CI-LB 0.03024, 10/10 seeds above both references); (2) §5.2 gains
the verbatim "Office_Products V3 (redesigned pre-registration) — PASSED." paragraph
(`PREREG_OFFICE_V3.md` / `OFFICE_V3_RESULTS.md`; frozen claim wording kept exactly, incl. the
explicit not-SOTA sentence); (3) the §6.4 category-scope bullet now records V1-VOID-stands +
V3-passed-and-counted + FIR-breadth internal-contrast scope; (4) Appendix A.0's tail sentence
is now V1-scoped with the parenthetical V3 note; (5) the §4.1 dataset-role table Office row
("V1 prereg VOID …; redesigned V3 prereg PASSED") regenerated from the md by the emitter, and
the §4.1 trailing prose sentence is now "Every pre-registered campaign in this version is
fully adjudicated (verdicts in §5.2 and Appendix A.0)."; (6) no new references. The scan's
informational review list grew 14 → 18 — the additions are the new paragraph's explicit SOTA
*non-claims* and negated superiority wording, as designed; failures remain 0.

## 2026-07-13 sync: FIR-BREADTH campaign + convolutional novelty boundary

Mirrors the canonical md's FIR-BREADTH working-tree deltas (7 hunks, all covered):
(1) abstract gained the pre-registered breadth clause (IS +0.0024 / CDs +0.0057, four
categories in total); (2) §2.2 FIR bullet now "confirmed on four categories, two via the
pre-registered breadth campaign of §5.2"; (3) §2.3 gained the Caser/NextItNet
convolutional-prior-art passage (`\citep{tang2018caser}`, `\citep{yuan2019nextitnet}`);
(4) Table 0 FIR row (prior-art + evidence columns) and the §4.1 dataset-role table rows
(IS/CDs now "pre-registered FIR-breadth: CONFIRMED") regenerate from the md via the emitter;
the §4.1 trailing sentence is now Office-V3-only; (5) §5.2 gained the verbatim
"Pre-registered breadth (two further categories)" paragraph (references
`PREREG_FIR_BREADTH.md` / `FIR_BREADTH_RESULTS.md`); (6) §8 sidecar sentence now covers Office
and FIR-breadth sidecars ("hashed into each run's embedded manifest"); (7) `references.bib`
gained tang2018caser and yuan2019nextitnet — transcribed from the md, with Crossref-verified
pages/publisher/DOI (10.1145/3159652.3159656 pp. 565–573; 10.1145/3289600.3290975
pp. 582–590, both ACM/WSDM, checked 2026-07-13). Fidelity repair in passing: the round-14
WPGRec citation had dropped the md's inline `arXiv:2604.21305` (the bst does not render
`eprint` on `@misc`) — restored as a `\citep` postnote + in the bib note; the whole-document
numeral check is back to zero missing md tokens.

## Round-8: two build targets (class options)

Per ACM's general author workflow (initial journal review submissions in single-column
`manuscript` format; VENUE_PLAN.md: "TORS: `manuscript`/`acmsmall` journal format"):

- `main.tex` — **default review target**: `\documentclass[manuscript,review,anonymous]{acmart}`
  → `PAPER_TORS.pdf` (the manifest-gated review artifact; letter-size 612×792 pt page).
- `main-acmsmall.tex` — **production preview**: `[acmsmall,screen,review,anonymous]`
  → `PAPER_TORS_acmsmall.pdf` (6.75in×10in page; **untracked**, see `paper_tex/.gitignore`).
- Both are two-line drivers sharing every preamble command and the full body via
  `paper-shared.tex`; `build.sh`/`build.ps1` compile both and hygiene-scan the review artifact.

Page-count note: acmart's `manuscript` **and** `acmsmall` are both *single-column* formats, so
the review manuscript does not balloon relative to acmsmall — it lands at 35 pages vs
acmsmall's 36 (manuscript uses a larger letter-size text block). The format switch is real and
verified by page geometry (612×792 pt vs 486×720 pt) and the class option.

## Round-8: BibTeX metadata fill (verified only; nothing invented)

Missing volume/number/pages/publisher/DOI fields were filled **only** where verifiable from
authoritative listings on 2026-07-12: the Crossref registry (publisher-deposited metadata,
`api.crossref.org`, exact title+author+year matches), the ACL Anthology page (devlin2019bert),
and the PMLR v235 page (zhai2024hstu). **21 entries gained fields**:

- ACM venues (pages+publisher+doi): sun2019bert4rec, hou2022unisrec, hou2023vqrec,
  zhou2022fmlprec, li2020tisasrec, kim2023melt, wei2021clcrec, melchiorre2022protomf,
  du2023fearec; he2016ups (publisher = IW3C2 Steering Committee, per registry).
- IEEE venues (pages+publisher+doi): kang2018sasrec, szegedy2016rethinking;
  gavish2014optimal (+volume 60, number 8).
- ACL venues (pages+publisher+doi): reimers2019sbert (registry pages 3980–3990),
  shaw2018relative, devlin2019bert (ACL Anthology: 4171–4186, doi 10.18653/v1/N19-1423).
- AAAI: shin2024bsarec (volume 38, number 8, pages 8984–8992, doi 10.1609/aaai.v38i8.28747).
- NeurIPS 2023 proceedings deposit: rajput2023tiger (pages 10299–10315, doi
  10.52202/075280-0452 — the Curran/NeurIPS-Foundation registry record).
- Journals: efron1973stein (JASA 68(341):117–130, Taylor & Francis, doi
  10.1080/01621459.1973.10481350); baik2005bbp (Ann. Probab. 33(5), IMS, doi
  10.1214/009117905000000233 — the registry record carries **no page field**, so pages were
  deliberately not filled).
- PMLR: zhai2024hstu (volume 235, pages 58484–58509, publisher PMLR; PMLR registers no DOI).

**Left as-is (no unambiguous authoritative record; noted, not guessed):**
- wang2020minilm, volkovs2017dropoutnet — NeurIPS 2020/2017 papers with no Crossref record
  under exact title+author queries; the entries keep the md's venue + (for MiniLM) arXiv note.
- marchenko1967mp — the 1967 Russian *Matematicheskii Sbornik* original is not DOI-registered;
  only the English-translation record exists (a different publication object) — left untouched.
- james1961estimation — the 1961 Berkeley Symposium original is not registered; Crossref only
  carries the 1992 Springer reprint (different object) — left untouched.
- hou2024blair, liu2025hstublair, yang2024liger and the five 2026 concurrent preprints
  (guo2026sidmlp, hou2026latte, huang2026chronosid, liang2026resid, shyam2026grit) — arXiv-only
  by design; no venue metadata exists.

Effect: 20 `https://doi.org/...` links now render in the bibliography; BibTeX warnings reduced
to "empty address" (conference cities are not in the registry data pulled and were not
invented) plus the deliberately-left entries above.

## Toolchain

| Tool | Version | Location | Notes |
|---|---|---|---|
| Tectonic | 0.16.9 | `C:\Users\rayxc\AppData\Local\tectonic\tectonic.exe` | winget has no Tectonic package ("No package found"); installed the official prebuilt `x86_64-pc-windows-msvc` binary from the GitHub release `tectonic@0.16.9`. Self-contained; fetches TeX packages on demand. MiKTeX was NOT needed. |
| acmart class | v2.03 (2024/02/04) | vendored `paper_tex/acmart.cls` | Tectonic's bundled acmart predates the TORS journal option ("Incorrect journal TORS"), so the class is vendored from the TeX Live 2023-final package archive (matches Tectonic's kernel era; the current CTAN acmart v2.1x targets the newer tagging-enabled LaTeX kernel). `ACM-Reference-Format.bst` vendored from the same package. |
| pandoc | 3.10 | `C:\Users\rayxc\AppData\Local\Pandoc\pandoc` | `-f gfm+smart -t latex` for all md→tex conversion. |
| Python | 3.12.13 | `_bestrec_run/.venv/Scripts/python.exe` | pypdf 6.10.2 for the hygiene scan. |

Build entry points: `build.sh` (bash) / `build.ps1` (PowerShell). Pipeline (fail-closed):
`emit_latex_tables.py` (table regeneration + numeric cross-check) → `tectonic main.tex` →
copy to `PAPER_TORS.pdf` → `scan_pdf.py` (placeholder + forbidden-claim hygiene scan; nonzero
exit on any hit). Tool paths overridable via `PYTHON` / `TECTONIC` env vars.

## Document class / anonymization

Default review target (`main.tex`): `\documentclass[manuscript,review,anonymous]{acmart}` —
ACM's single-column review format, producing the manifest-gated `PAPER_TORS.pdf`. Production
preview (`main-acmsmall.tex`, untracked output `PAPER_TORS_acmsmall.pdf`):
`\documentclass[acmsmall,screen,review,anonymous]{acmart}`. Both drivers share
`paper-shared.tex`, which sets `\acmJournal{TORS}`,
`\citestyle{acmauthoryear}`, `\setcopyright{none}`, `\settopmatter{printacmref=false}`,
`\acmDOI{}` (suppresses the class's `10.1145/nnnnnnn` stub on the review manuscript).
`\author{[anonymized for review]}` — the `anonymous` option renders the byline as
"ANONYMOUS AUTHOR(S)"; no identifying information exists anywhere in the source. Review mode
prints line numbers, as TORS expects for submission.

## File map (md section → tex file)

| PAPER_SUBMISSION.md | tex file |
|---|---|
| Title + Authors line | `main.tex` (`\title`, `\author`) |
| Abstract | `sections/abstract.tex` (inside `abstract` env) |
| §1 Introduction | `sections/01-introduction.tex` |
| §2 Related Work and Attribution (2.1–2.3) | `sections/02-related.tex` |
| §3 Method (3.1–3.7) | `sections/03-method.tex` |
| §4 Experiments (4.1–4.4) | `sections/04-experiments.tex` |
| §5 Results (5.1–5.6, 5.4.1–5.4.2) | `sections/05-results.tex` |
| §6 Discussion (6.1–6.5) | `sections/06-discussion.tex` |
| §7 Conclusion | `sections/07-conclusion.tex` |
| §8 Code and Data Availability | `sections/08-availability.tex` |
| §9 Acknowledgments | `sections/09-acknowledgments.tex` |
| §10 Ethics and Data Governance (round-7) | `sections/10-ethics.tex` |
| References | `references.bib` (+ `\nocite{*}` in `main.tex`; see below) |
| Appendix A.0 (Office_Products) | `sections/appendix-a0.tex` |
| Appendix A (A.1–A.3, Beauty) | `sections/appendix-a.tex` |

Section numbering matches the md exactly (LaTeX auto-numbers reproduce 1–10, 5.4.1/5.4.2, etc.);
`§X.Y` prose references became `\S\ref{sec:X.Y}` with labels on every heading, so printed
references resolve to the same numbers as the md. Appendix headings are unnumbered `\section*`
with the md's literal titles ("Appendix A.0 — …", "Appendix A — …", "A.1 …"), preserving the md's
canonical appendix numbering (A.0 alongside A.1–A.3 — not reproducible with LaTeX appendix
counters, and appendix cross-references in the text are literal strings anyway).

## Table provenance (STANDING AUDIT REQUIREMENT: no gated number retyped by hand)

All 16 table includes under `paper_tex/tables/` are **generated** by
`_bestrec_run/emit_latex_tables.py` (re-run on every build; header comment in each file carries
per-table provenance + cross-check summary; machine-readable copy in
`tables/TABLES_PROVENANCE.json`).

**Emitted directly from the strict-build JSON** (`_bestrec_run/hstu_tables.json`, the output of
`build_hstu_tables.py --submission`, 0 MISMATCH / 0 UNTRACEABLE):

| include | JSON family | rendered at |
|---|---|---|
| `tableV2conf.tex` | `tableV2conf` | §5.2, after the pre-registered-confirmation paragraph |
| `office_confirmation.tex` | `office_confirmation` | Appendix A.0, after the gate paragraph |

**Extracted mechanically from the canonical md** (pipe-table blocks located by header
fingerprint, converted via `pandoc -f gfm+smart -t latex`, then reshaped; the md caption
paragraph travels with its table) — with **numeric cross-check against the JSON family** where
one exists (every result-grade token, ≥3 fractional digits, must match the family's regenerated
tokens exactly or within 1 ulp at the printed precision — the same "within rounding" grade the
strict build uses; any other token aborts the build unless it is on a per-table allowlist with an
inline justification comment):

| include | md table | JSON cross-check family |
|---|---|---|
| `table_attribution.tex` | §2.1 attribution table | — (md-only prose table) |
| `table0_novelty.tex` | §2.3 Table 0 | — (md-only prose table) |
| `table1.tex` | §5.1 Table 1 | `table1` (allowlist: 0.0012 = diff-of-rounded-prints; strict build grades it within-rounding) |
| `table1a.tex` | §5.1 Table 1a | `table1a` |
| `table1b.tex` | §5.1 Table 1b | `table1b` + `table1` (comparison column cites the Table 1 headline; allowlist: published HR/HSTU-OpenAI constants that exist only as md-cited EXTERNAL_PUBLISHED values) |
| `table_older_baselines.tex` | §5.1 older-protocols table | — (external published constants) |
| `table1c.tex` | §5.2 Table 1c | `table1c` |
| `table1d.tex` | §5.3 Table 1d | `table1d` |
| `table1e.tex` | §5.4 Table 1e | `table1e` (all 42 numeric cells exact) |
| `table541.tex` | §5.4.1 arm-ratio table | `table541` (allowlist: 3 tail-Δ tokens restated from `table1d`/`table1e`) |
| `table542.tex` | §5.4.2 user-mode table | `table542` |
| `table2.tex` | §5.5 Table 2 | `table2` (allowlist: base-band/context numerals the JSON stores in row labels/notes) |
| `table56_theirs.tex` | §5.6 theirs-on-ours table | `hstu_results_manifest.json` family `theirs_on_ours` + published constants (all 15 numerals matched) |
| `tableA1.tex` | Appendix A.1 Table A1 | — (superseded supporting scan; single-seed) |

The authoritative numeral gate remains `rebuild_hstu_submission.py --strict` /
`build_hstu_tables.py --submission` on the canonical md; the emitter's cross-check is an
additional md→tex extraction-fidelity layer for this derivative.

**End-to-end numeral fidelity check (whole document):** multiset comparison of every numeric
token (`\d+\.\d{2,}`) in `PAPER_SUBMISSION.md` vs the text extracted from `PAPER_TORS.pdf`:
**no md token is missing or reduced in the PDF** (md-only set = NONE). The PDF-only extras are
exactly the numerals contributed by the two JSON-emitted tables above (V2-confirmation and
Office per-seed/CI values, already present in the md as prose for the V2 numbers and as
appendix prose for Office gate values; per-seed Office columns come from the gated JSON) —
plus nothing else.

## Conversion decisions / caveats

1. **Two presentation-only table additions (disclosed).** The md carries the §5.2 dual-kernel
   confirmation and the Appendix A.0 Office confirmation as *prose*; the TORS version
   additionally renders the strict-build's regenerated tables (`tableV2conf.tex`,
   `office_confirmation.tex`) at those positions, captioned "(regenerated)" as in
   `hstu_tables.json`. No prose was removed or altered; the tables restate the same gated
   numbers (deliverable requirement: generated table includes for these families).
2. **Table headings are verbatim md captions** (bold paragraph above each table), not LaTeX
   `\caption` counters — the md's canonical names (Table 0, 1, 1a–1e, 2, A1) cannot be
   reproduced by LaTeX table counters, and all in-text references use those literal names.
   Tables are set inline (non-floating) in md order; Table 0 uses `longtable` so it can break
   across pages.
3. **Unicode → LaTeX macros** per the conversion spec (±, ≈, ×, →, ←, ↔, ⇒, §, Δ, ⊙, √, ρ, α,
   β, ε, τ, λ, Φ, ℝ, ∈, ≤, ≥, ≪, ⊂, ≠, ⊕, ℓ, ⟨⟩, ᵀ, ·, −, ⁻⁷, …, é, ö → `\ensuremath{...}` /
   text macros). One en-dash inside a `\texttt` filename pattern
   (`results_MI_lsonly_seed{08–12}`) is kept as a raw character (renders correctly under
   XeTeX/Inconsolata).
4. **Code-fenced formulas became proper math** (task spec): §3.2 item-feature definitions,
   §3.3 Φ designs, §3.7 TAPE assignment/prototype equations and the causal-FIR update (display
   `equation*`), and the HSTU pointwise form `silu(QKᵀ + rab) V`. The md writes `R^d` in §3.2
   and `ℝ^{...}` in §3.7; both are set as `\mathbb{R}` for glyph consistency with the md's own
   §3.7 usage. The §3.5 chunked-softmax pseudocode stays a verbatim block.
5. **Citations**: `(Author, year)` → `\citep`, inline names → `\citet`/name+`\citealp`,
   with `acmauthoryear` style (renders `[Author year]`). The five concurrent 2026 preprints
   (incl. GrIT, round-7) are cited with their arXiv IDs as postnotes (`\citep[arXiv:...]{...}`).
   `references.bib` transcribes the md reference list **exactly** — 32 entries after round-7
   (FEARec in the main list; GrIT in the concurrent block) — authors/initials/venues as
   printed; nothing invented (hence BibTeX warnings about missing volume/pages, see below).
   The md's per-entry parenthetical annotations are `note` fields; the md's
   *concurrent-preprint fence paragraph* is carried verbatim-in-substance in the note field of
   each of the five 2026 entries (allowed packaging: "footnote or note field"). `\nocite{*}`
   prints the full list so the bibliography contains exactly the md's entries, including the
   ones the md cites by name only (Devlin, Efron–Morris, James–Stein, VQ-Rec, ProtoMF).
   ACM-Reference-Format sorts alphabetically, so the preprints interleave with the main list
   (the md prints them as a separate trailing group); their notes preserve the fence wording.
6. **Figures (round-7: embedded).** The md now embeds Figs. 1–3 as image lines with caption
   text (plus a duplicate italic caption line for the md/Chrome pipeline). The LaTeX renders
   them as `figure` floats — `\includegraphics[width=\linewidth]` of the **canonical PDF
   vector figures** via `\graphicspath{{../figures/}}` (`fig_tail_law_mechanism.pdf` after the
   §5.3 cross-dataset-significance block = Fig. 1; `fig_r1r2_plane.pdf` after the §5.4.2
   MI-matched-connectivity paragraph = Fig. 2; `fig_bbp_irreducibility.pdf` after the
   "Refined verdict" paragraph = Fig. 3) — with `\caption` = the md caption text (the md's
   duplicated italic caption line collapses into the single LaTeX caption; LaTeX supplies the
   "Fig. N." prefix, so the md's "Fig. N:" prefix is not repeated inside the caption body).
   Float numbering reproduces the md's Fig. 1/2/3 names, and every in-text "Fig. N" mention
   (incl. Table 2's GD1 cell, wired inside the table generator) is a `cleveref` `\cref` with
   `\crefname{figure}{Fig.}{Figs.}`, so the printed text is exactly the md's "Fig. N" and all
   references resolve. Note for verification tooling: the figures are **vector PDFs**, so they
   embed as PDF *Form XObjects* (3 of them, ~30–36 KB each), not raster Image XObjects —
   `pypdf`'s `page.images` reports 0 by design; count `/XObject` entries with
   `/Subtype /Form` instead.
7. **§-references**: `§X.Y` → `\S\ref{sec:X.Y}`; the md's `§7` references (pointing at the
   Conclusion) resolve to section 7 as in the md. `§A.1` is set as literal `\S{}A.1` (appendix
   sections are unnumbered by design, see above).
8. **Long-identifier line breaking**: `\allowbreak` hints inserted in
   `external/AmazonReviews2023/seq_rec_results/`, `Beauty_and_Personal_Care`,
   `SOTA_CONFIRM_PREREG_OFFICE.md` (typography only; extracted text unchanged).
9. **Prose conversion provenance**: section bodies were converted once with pandoc
   (`gfm+smart`, `--wrap=none`) via a scripted splitter (heading→`\section`+label, table
   blocks replaced by `\input{tables/...}`, unicode/citation/§-ref post-passes), then
   hand-reviewed file by file; the table includes are the part that regenerates mechanically
   on every build, per the venue plan's standing requirement.
10. **Round-7 md deltas mirrored** (canonical commit `f141cf7`): (a) Figs. 1–3 embedded (see
   caveat 6); (b) new §10 Ethics and Data Governance (`sections/10-ethics.tex`, verbatim
   conversion, input between §9 and the References); (c) Table 0 HSTU-base row now reads
   "core-block parity demonstrated bitwise against the reference research implementation
   (§3.2); no pinned end-to-end system reproduction (§5.6, §6.5)" — picked up automatically by
   the table generator from the md; (d) §2.3 novelty paragraph gained the FEARec
   frequency-line-broadening sentence (`\citep{du2023fearec}`); (e) §5.1 concurrent-preprint
   paragraph gained the GrIT sentence (`\citep[arXiv:2602.19728]{shyam2026grit}`, VG 0.0588
   point-estimate observation with comparability caveats) and "We cite them" → "We cite these
   works"; (f) two new reference entries (FEARec, GrIT).

## Compile status

- Review target `tectonic main.tex` (`manuscript`): **0 errors, 0 undefined
  references/citations**; 35 pages; **one accepted cosmetic overfull** (4.45 pt ≈ 1.6 mm, a
  bold enumerate header in §5.4.2 — invisible protrusion; every other overfull was fixed with
  typography-only `\allowbreak` hints, incl. the long `results_USERTITR_...json` artifact name
  and `Beauty_and_PC`).
- Preview target `tectonic main-acmsmall.tex` (`acmsmall`): 0 errors, **0 overfull boxes**,
  36 pages.
- Remaining warnings (accepted):
  - BibTeX "empty address" warnings — conference cities are not in the registry data pulled
    and were not invented (round-8 fill covers volume/number/pages/publisher/DOI); plus the
    deliberately-unfilled entries listed in the round-8 section.
  - acmart "CCS concepts / keywords not provided" — the canonical md has neither; adding them
    would be new content. To be supplied at actual submission time if TORS requires them.
  - Underfull `\vbox`/`\hbox` cosmetics from the review-mode line-number grid and one
    `\vspace` class warning from the `longtable` header — no visual defect.
  - A Fontconfig stderr note from tectonic on Windows (harmless, upstream tectonic issue).

## Hygiene scan (final output, PASS)

Scanner: `paper_tex/scan_pdf.py` (pypdf text extraction; pattern family of
`_bestrec_run/render_paper_pdf.py` + the VENUE_PLAN forbidden-wordings sweep). Hard-fail:
TODO/TBD/FIXME/XXX/PLACEHOLDER/lorem/`???`/`\bDEAD\b`/killed/`0.0100`/`(v3.x)`/`[TK`;
"statistically significantly better than HSTU-BLaIR" (unconditional); "paired superiority",
"official reproduction", "pinned[-…] reproduction" without a preceding negation cue.
SOTA / state-of-the-art mentions are flagged with ±80-char context for manual review and never
hard-fail (the paper contains explicit SOTA *non-claims* by design). Full output also in
`paper_tex/hygiene_scan_output.txt`.

```
hygiene scan: PAPER_TORS.pdf | pages: 35
placeholder+forbidden failures: 0
review list (SOTA mentions + negated claim-wordings): 14
  REVIEW negated-ok: paired\s+superiority :: ... this is a per-category point-estimate comparison, not a paired superiority or general SOTA claim ...
  REVIEW negated-ok: pinned(?:[-\s]\w+)?[-\s]reproduction :: ... no sm_120 images — proven via WSL), which blocks a faithful pinned reproduction ...
  REVIEW negated-ok: pinned(?:[-\s]\w+)?[-\s]reproduction :: ... 0.13234 final stronger than ours; not a faithful pinned-environment reproduction ...
  REVIEW negated-ok: pinned\s+reproduction :: ... which blocks a faithful pinned reproduction ...
  REVIEW SOTA-mention :: ... not a paired superiority or general SOTA claim ...
  REVIEW SOTA-mention :: ... multi-seed contribution rather than a SOTA claim ...
  REVIEW SOTA-mention :: ... fully-attributed contribution rather than a SOTA claim ...
  REVIEW SOTA-mention :: ... shown to be architectural (ID-only ≈0.0656), with no SOTA claim ...
  REVIEW SOTA-mention :: ... 5.1 Video_Games — multi-seed reference numbers (NOT SOTA) ...
  REVIEW SOTA-mention :: ... We therefore do not claim SOTA over TIGER/LIGER/BLaIR ...
  REVIEW SOTA-mention :: ... blocks a SASRec-SBERT SOTA claim ...
  REVIEW SOTA-mention :: ... We do not claim a Video_Games SOTA — the published HSTU-BLaIR 0.0760 ...
  REVIEW SOTA-mention :: ... Explicit non-claims: • We do not claim SOTA over TIGER, LIGER, BLaIR, or HSTU-BLaIR ...
  REVIEW SOTA-mention :: ... as a reference baseline rather than as a SOTA-improvement claim ...
verdict: PASS (review list above is informational)
```

Every SOTA mention is an explicit non-claim; every claim-wording occurrence sits in a negation
context — consistent with the canonical claim set (no broad SOTA, no paired superiority, no
official/pinned-reproduction language, Office never a passed category).

## Directory inventory

```
paper_tex/
├── main.tex                  # REVIEW driver: [manuscript,review,anonymous] (round-8 default target)
├── main-acmsmall.tex         # PREVIEW driver: [acmsmall,screen,review,anonymous] (untracked output)
├── paper-shared.tex          # shared preamble commands + full document body (both drivers input this)
├── references.bib            # transcribed md list (32 entries incl. 5 concurrent preprints; round-8 verified metadata)
├── acmart.cls                # vendored v2.03 (TL2023-final) — TORS-capable, tectonic-compatible
├── ACM-Reference-Format.bst  # vendored ACM bibliography style
├── .gitignore                # main.pdf, main-acmsmall.pdf, PAPER_TORS_acmsmall.pdf + TeX intermediates
├── sections/*.tex            # 13 converted section files (see file map; incl. round-7 10-ethics.tex)
├── tables/*.tex              # 16 GENERATED includes + TABLES_PROVENANCE.json (never edit by hand)
├── build.sh / build.ps1      # regenerate tables → compile BOTH targets → package → hygiene scan
├── scan_pdf.py               # hygiene scanner (exit 1 on any failure)
├── hygiene_scan_output.txt   # last scan output (PASS)
├── main.pdf                  # tectonic output of the review driver (untracked; = PAPER_TORS.pdf)
├── PAPER_TORS.pdf            # DELIVERABLE (35 pp, manuscript format, Figs. 1–3 embedded as vector Form XObjects)
└── PAPER_TORS_acmsmall.pdf   # production preview (36 pp; untracked)
```

Generator script (allowed new file outside `paper_tex/`): `_bestrec_run/emit_latex_tables.py`.
No canonical file (`PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `results_*.json`,
`RELEASE_MANIFEST.json`, `external/HSTU-BLaIR`, audits/responses) was modified.
