# Claude — the "single source of truth" carries a stale cell count that E5 already fixed elsewhere

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `6eb426f8`. **No artifact modified — this
one is claim-bearing and stays propose-only.**

```text
WORKSTREAM:        audit CANONICAL_SUBMISSION.md, the last unaudited source of truth
OBJECTIVE:         is the self-declared single source of truth current?
EVIDENCE QUESTION: do its numbers agree with the authoritative claim map?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: CANONICAL_SUBMISSION.md (claim-bearing), PAPER_REVIEW_AUDIT.md,
                   manuscript, TeX, cover letter, preregs, adjudicators, graph, tables,
                   manifest, results_*.json, checklist, experiments/**
EXPECTED OUTPUT:   defect + severity + proposed patch, unapplied
STOP CONDITION:    memo committed and pushed
```

`CANONICAL_SUBMISSION.md` is the only source-of-truth document I had never audited, and it is the
oldest in the set (mtime 07-31 05:47; header dated **2026-07-11**).

---

## 1. The defect

| document | count |
|---|---|
| **`CANONICAL_SUBMISSION.md`** (item 5) | *"the **196 declared empirical cells** recompute from graph-bound artifacts"* |
| `CLAIM_ARTIFACT_MAP.md` (authoritative) | *"**201 active cells** mapped exactly once"*, *"201 active cells, 8 retired, 5 external literature cells"* |
| `TIER_A_PUBLICATION_ROADMAP.md` | *"201 active cells across 25 claim families"* |
| `COVER_LETTER_TORS.md` | *"201 paper-bound cells across 25 claim families"* |

**These are the same quantity, not different metrics.** `AUDIT_RESPONSE_2026-07-27.md` records the
progression explicitly:

> *"196 active cells across **20** claim families"* → *"200 cells across **24** families"* →
> *"201 active cells across **25** required families recomputed"*

So **196 is the 20-family-era value of the count that is now 201/25.** `CANONICAL_SUBMISSION.md`
carries the superseded figure.

## 2. Why this matters more than the number itself

This is **the same defect class as E5** — stale cell counts, which I raised before this cycle and
Codex **fixed in the cover letter** (192/18 → 201/25) and which the roadmap also carries correctly.
**The fix was applied in two places and missed in the third — the one document that titles itself
"single source of truth"** and whose §"The canonical claim set" begins *"nothing broader is claimed
anywhere."*

A document asserting exclusive authority over the claim set should not be the last to be updated.

## 3. Severity: **LOW-MEDIUM, and I will not inflate it**

The stale number is **lower** than the true one. It **understates** artifact coverage, so it cannot
mislead a reviewer in the paper's favour — it is an accuracy and consistency defect, **not an
integrity risk and not an overclaim**. Nothing counted depends on it.

Two properties keep it worth fixing anyway: an auditor comparing the four documents will find the
disagreement in under a minute, and the disagreeing document is the one that claims to govern.

## 4. Secondary: the header is three weeks stale relative to its own body

The title line reads *"updated for round-2 audit F1, **2026-07-11**"*, but the body already
describes **Office V3**, **EE V3/V4**, the **canonical breadth** campaign, **ML-1M**, and the
**WEARec** baseline — all of which postdate 2026-07-11. So the content has been maintained while the
header has not. Minor, but in a source-of-truth document the header is what a reader trusts for
currency.

## 5. Proposed patch **P12 — NOT applied**

**File:** `CANONICAL_SUBMISSION.md`, item 5 under "The canonical claim set".
**Change:** `196 declared empirical cells` → `201 declared empirical cells`, and update the header
date to the actual last content update.
**Verify first:** confirm against `CLAIM_ARTIFACT_MAP.md` at the time of edit, since the count has
moved three times already (196 → 200 → 201) and may move again.

**Why I am not applying this one, having applied P1 last tick.** Last tick I edited the roadmap and
stated the scope was *deliberately minimal — one planning document*, explicitly excluding anything
claim-bearing. **`CANONICAL_SUBMISSION.md` is claim-bearing by its own definition**: it enumerates
the canonical claim set and asserts nothing broader is claimed anywhere. That places it firmly on
the propose-only side of the line I drew, and the line decides this case without my having to
re-argue it — which is some evidence it was drawn in the right place.

## 6. What does not change

Counted claim boundary unchanged: Musical_Instruments (vs 0.0406) and Office_Products V3 (vs 0.0271
and 0.0279); **Office V1 VOID forever**; TFV2 outcome-visible, not confirmatory. The **substance**
of `CANONICAL_SUBMISSION.md`'s claim set was audited against the manuscript and is accurate — items
1–5 correctly describe the MI and Office V3 counted comparisons, the V1 VOID, the package-arm
caveats, the withdrawn paired interpretation, and the sidecar deposit policy. **Only the count and
the header date are stale.**

## Limits

I compared four documents and the audit-response history; I did not recount the cells from the graph
myself, so "201" is taken from `CLAIM_ARTIFACT_MAP.md` and the roadmap/cover letter rather than
independently recomputed — Codex owns recomputation. If the true current count is neither 196 nor
201, then three documents are wrong rather than one, which would be a larger finding than this memo
claims. The header-date observation assumes the listed campaigns postdate 2026-07-11, which I read
from their presence in the body rather than from commit timestamps.
