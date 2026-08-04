# Claude (f) audit — manuscript focus and length

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-01. Reviewed commit `d850ac66` (working tree dirty; manuscript, TeX and rebuilt PDFs
carry uncommitted Codex edits, audited as-is).

```text
WORKSTREAM:        queue item (f) — focus/length work touching no table and no graph
OBJECTIVE:         locate where the article spends its length; say what may and may not be cut
EVIDENCE QUESTION: is length a real blocker, and would the obvious cut damage the contribution?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, generated tables, manifest, results_*.json, checklist
EXPECTED OUTPUT:   measured length profile + a recommendation, including what NOT to cut
STOP CONDITION:    memo committed and pushed
```

---

## 1. Headline: **length is not currently a blocker, and I recommend no cuts for length**

Rebuilt page counts:

| artifact | pages |
|---|---:|
| `paper_tex/PAPER_TORS.pdf` (review rendering) | **33** |
| `paper_tex/PAPER_TORS_acmsmall.pdf` (journal main) | **34** |
| `paper_tex/PAPER_TORS_SUPPLEMENT.pdf` (reviewer supplement) | **18** |
| `PAPER_SUBMISSION.pdf` (reader edition) | **57** |

A 34-page journal-layout main article is within normal range for an ACM journal submission. **I did
not verify a hard page limit for the target venue and will not assert one** — that touches A0, which
is BLOCKED. Absent a stated limit, cutting for page count would be optimising against a constraint
nobody has established.

**Two of the audit's numbers have moved since it was written.** The 2026-07-31 22:23 audit recorded
40-page TORS PDFs and a 45-page `PAPER_SUBMISSION.pdf`. They are now **33/34** and **57**. Codex's
uncommitted rebuild has both shrunk the focused package and grown the reader edition; the gap went
from 5 pages to **23**. Any decision based on the old figures should be re-taken on these.

## 2. One of the audit's open questions is already answered by the manuscript itself

The audit asks:

> *"Is `PAPER_SUBMISSION.pdf` still a live deliverable now that it is 45 pages while both TORS PDFs
> are 40 pages?"*

`PAPER_SUBMISSION.md` line 5 answers it:

> *"Reader edition — rendered from the canonical markdown source and retaining the full evidence
> record. The focused ACM TORS package is `paper_tex/PAPER_TORS.pdf` … `PAPER_TORS_acmsmall.pdf` …
> `PAPER_TORS_SUPPLEMENT.pdf`."*

The divergence is **by design and disclosed**: one document is the complete evidence record, the
other is the focused submission. **This is not a defect and needs no reconciliation** — Codex can
close the open question by citing this header. The only thing the growth changes is that the word
"focused" now carries 23 pages of weight rather than 5, so the header's claim should stay accurate
as the gap widens.

## 3. Where the length actually is

25,039 words across 963 lines. Section 5 alone is **36.9%**:

| section | words | share |
|---|---:|---:|
| 5. Results | **9,235** | **36.9%** |
| References | 2,619 | 10.5% |
| Supplementary Material | 2,572 | 10.3% |
| 2. Related Work and Attribution | 2,337 | 9.3% |
| 3. Method | 2,148 | 8.6% |
| 4. Experiments | 1,301 | 5.2% |
| 6. Discussion | 1,338 | 5.3% |
| everything else | ~3,500 | ~14% |

Inside §5:

| subsection | words | what it is |
|---|---:|---|
| 5.2 canonical FIR internal contrasts | **3,162** | **load-bearing — the FIR claim** |
| 5.1 Video_Games system context | 2,068 | declared *"not FIR inference; NOT SOTA"* |
| 5.4 titration | 807 | level-contrast result |
| 5.5 screening log | 724 | declared *"a search record, not powered exclusions"* |
| 5.3 MI frequency-5 tail case | 721 | heterogeneity case |
| 5.6 local comparator regeneration | 632 | environment-caveated |
| 5.7 hybrid late fusion | 526 | declared **outcome-visible** |
| 5.8 sparse-warm text fusion | 339 | declared **outcome-visible, protocol-deviated** |
| preamble + statistical conventions | 253 | |

## 4. **The obvious cut would damage the contribution. Do not make it.**

The natural length edit is to move §5.5, §5.7 and §5.8 — roughly 1,600 words that support **no
counted claim** and are labelled search-record / outcome-visible / protocol-deviated — into the
supplement. A reviewer-minded editor would suggest exactly that.

**It would be a mistake, and this is the main finding of this audit.** The abstract states the
contribution as *"a narrow detachable implementation and an artifact-gated evaluation record"* whose
graph *"preserves positive, null, deviated, and VOID outcomes under one reporting rule."* Relegating
the deviated and outcome-visible material to a supplement while the positive FIR contrasts stay in
the main text **is** the selective-reporting asymmetry the paper claims to have eliminated. It would
convert the paper's distinguishing feature into a claim the document's own structure contradicts.

The same logic protects Appendix A.0 (942 words, Office_Products VOID evidence). **VOID records
stay.**

## 5. What could compress, if focus rather than length is the goal

**§5.1 (2,068 words) is the only substantial candidate.** It is explicitly non-inferential — *"not
FIR inference; NOT SOTA"* — and much of it is related-work in character: older published baselines
on different protocols, the TIGER/LIGER comparability caveat, the concurrent protocol landscape.
Moving that material adjacent to §2, or to the supplement, removes **no outcome record** and so does
not trip the §4 objection: nothing there is a preserved null, deviation, or VOID.

I am **not** recommending it be done now. It is a judgement call about readability, it touches
generated tables (Table 1a/1b live there, so it is outside my lane and outside item (f)'s
constraint), and no venue constraint currently motivates it.

## 6. A checklist defect: row 1's required closure depends on a deferred study

`TORS_METHODOLOGY_CHECKLIST.md` row **Research question and hypotheses** is PARTIAL, with required
closure:

> *"Compress the article around one primary temporal-input question **after the matched-input
> study**; preserve outcome-conditional wording."*

But the row **Exact-input temporal isolation** is **DEFERRED** — I rejected the repeated-current V1
as collapsing to one functional degree of freedom, Codex accepted the no-run verdict, and any V2
*"needs a new identifier, nondegenerate controls, a fresh reject-first memo, and human
authorization."*

**Row 1 therefore cannot close as written: its precondition is a study that is not scheduled and
requires human authorization to exist.** This is a live blocker hiding as a PARTIAL. Proposed
restatement — **Codex-owned; I did not edit the checklist:**

> Compress the article around one primary temporal-input question. Because the matched-input study
> is DEFERRED, closure does not depend on it: state the primary question and the boundary the
> deferred study would have tested, and preserve outcome-conditional wording.

That converts an unclosable row into one that can actually be discharged with prose.

## 7. Disposition

No claim, table, or graph touched. **No cuts recommended.** Length is not a blocker on the evidence
available, and the cut that a length-minded editor would propose is the one the paper's own
contribution forbids. Two audit figures are stale and one audit open question is already answered by
the manuscript header. One checklist row needs restating because its precondition is deferred.

## Limits

I did not verify any venue page limit — A0 is BLOCKED and I assert no venue constraint. Page counts
are read from PDFs rebuilt in an uncommitted working tree and will change on the next build. Word
counts are markdown-source counts, which do not map linearly to typeset pages. §5.1 compression
touches generated tables and is therefore flagged, not proposed. Advisory only; no artifact
modified.
