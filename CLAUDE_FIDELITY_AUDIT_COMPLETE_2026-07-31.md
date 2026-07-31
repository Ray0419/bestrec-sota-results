# Claude — numerical fidelity audit COMPLETE across both editor-facing surfaces

Role: scientific red-team (queue item e). HEAD `eedc4639`. Date: 2026-07-31. Advisory only.
Deliberately short: this tick closes a verification, it does not open a finding.

```text
WORKSTREAM:        A6 — finish fidelity verification of the cover letter
OBJECTIVE:         close the one surface audited for staleness but not for result accuracy
FILES I MAY EDIT:  this note; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: every file in the patch register, PAPER_REVIEW_AUDIT.md, adjudicators,
                   graph, tables, manifest
EXPECTED OUTPUT:   pass/fail; no new finding unless one is actually found
STOP CONDITION:    audit closed
```

## Result: **PASS.** Both claim surfaces are numerically faithful.

| surface | checks | verdict |
|---|---|---|
| Abstract (last tick) | 5 numeric claims vs `fir_v3`, `fir_pointwise_v1`, `fir_controls`, `fir_efficiency_ml1m_v1` | **5/5 exact** |
| Cover letter (this tick) | MI/IS/CDs estimates + all six interval bounds vs `fir_canonical_breadth_adjudication` and `fir_v3` | **exact** |
| Cover letter qualitative | "every temporally active arm improves identity after its frozen Holm procedures" vs `fir_controls` family_a | **accurate** — all five CIs exclude zero |

## Precise scope of the cover-letter defect (E5)

The cover letter is **accurate on every result number and on its qualitative claims**. Its
defects are bounded to exactly two things, both already patch-ready in
`CLAUDE_PATCH_REGISTER_2026-07-31.md`:

1. **Stale derived counts** (cells/families, manifest files, release assets) — P1.
2. **The pointwise sentence** that reads globally and contradicts the abstract — P2.

This is worth stating plainly because it changes the remediation: the cover letter does **not**
need rewriting. It needs two surgical edits. Anyone reading E5 without this note might have
concluded the document was broadly unreliable. It is not.

## What this closes

Queue item (e) — evidence-class and numerical consistency across title, abstract,
contributions, conclusion, and cover letter — is now **complete**, with one substantive
framing finding (F6, the under-sold 16-parameter result) and the E1–E5 precision defects, all
of which are in the patch register or their own memos.

## Limits

All numbers read from committed adjudication artifacts; no sealed endpoint opened, nothing
executed, no file modified. Derived counts were deliberately not re-derived here (see P1).
