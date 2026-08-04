# Claude calibration memo — the 35–50% forecast, and my own inflated estimates

Role: venue-methodology owner (`CODEX_CLAUDE_COLLABORATION_GUIDE.md` §3). HEAD `2cb6db24`.
Date: 2026-07-31. Author: Claude. Advisory only.

Addresses the one item flagged by **both** the 16:09 and 22:11 audits that nobody has acted
on. It also examines my own acceptance estimates, which are higher than the audits' and which
I have been quoting to the maintainer.

```text
WORKSTREAM:        venue calibration — the unsupported acceptance forecast
OBJECTIVE:         resolve a twice-flagged, still-open item; audit my own numbers too
EVIDENCE QUESTION: is any acceptance figure in this repository defensible as stated?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: TIER_A_PUBLICATION_ROADMAP.md (Codex-maintained — change PROPOSED),
                   PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   defect statement, estimand analysis, self-audit, proposed replacement
STOP CONDITION:    memo committed and pushed
```

## 1. The defect, stated precisely

`TIER_A_PUBLICATION_ROADMAP.md` §1 says:

> The working conditional estimate remains about 35–50% at a well-matched strong journal after
> human metadata are completed; 65% is not yet a defensible estimate.

Two problems, both independent of whether the number is *right*:

1. **No basis is given.** Grep for reference class, base rate, model, assumptions, prior →
   **nothing**. A bare interval with no estimand, no reference class, and no uncertainty is not
   a forecast; it is a mood.
2. **It is internally contradictory.** The document's own status line, eleven lines earlier,
   says *"This is not an acceptance forecast."* It then issues one. Whichever sentence is
   intended, they cannot both stand.

The audits are right to demand removal or grounding. **This is unaddressed after two flags,
which is why I am taking it this tick.**

## 2. The estimand nobody has defined — and it explains part of the gap

The audits calibrate **"direct TORS/top-journal acceptance"**: ~3–8% after metadata and
release fixes, ~12–20% after the full study program, ~20–30% with independent replication.

I have been quoting the maintainer **eventual acceptance after a normal journal
major-revision cycle** — a materially different quantity. At journals like TORS, most accepted
papers arrive via major revision; a figure conditioned on "direct" acceptance and one
conditioned on "eventual, post-revision" acceptance should differ substantially, and the
second should be larger.

**Neither the roadmap nor my own statements ever named which one they meant.** That ambiguity
alone makes every number in this repository non-comparable, including the audits' and mine.
Any retained figure must state: *acceptance of what, at which venue class, conditional on
what, by when.*

## 3. Self-audit: my numbers to the maintainer were optimistic

Stated plainly, because I have quoted these repeatedly:

| what I said | when | my assessment now |
|---|---|---|
| "~25–35% eventual acceptance at TORS as-is" | before the plan | **Too high.** |
| "~10–15% top-tier conference" | same | Roughly defensible. |
| "~45–55% expected after the full program" (vs the plan's 55–65%) | plan review | **Too high**, though I did shade the plan's own number down. |
| "~15–25% with full repairs / ~50–70% mid-tier" | earlier session | **Too high**, and "mid-tier" was never defined. |

Even correcting for the direct-vs-eventual estimand difference, I do not think my figures were
adequately conditioned on what the paper actually lacks: no independent replication, no
external custody, unequal baseline tuning, one negative external replication, a modest
incremental module, and an unverified venue. The audits have also demonstrated *better local
accuracy than me* this week — they caught several concrete errors in my own memos. On the
specific question of "direct acceptance today", I now regard **their range as better supported
than mine**, and I am not going to defend my earlier numbers by appealing to the estimand
difference alone.

Where I still differ: for **eventual** acceptance after a full revision cycle at a
well-matched venue, conditional on the whole study program landing *and* the results holding,
I would put it meaningfully above 3–8% — but I cannot ground that with a reference class
either, so **I should stop quoting it as a number.** That is the honest conclusion, and it
applies to me first.

## 4. Proposed replacement for the roadmap (Codex applies)

Delete the 35–50% sentence. Replace with:

> **Acceptance likelihood is not forecast in this document.** No reference class, base rate, or
> model has been specified, and the target venue is unverified (gate A0), so any single figure
> would be unfounded. What can be stated is directional and conditional: the package is
> currently **not submittable** (author/legal placeholders, stale cover-letter counts, no
> immutable deposit); the strongest remaining scientific gaps are optimizer-exposure
> asymmetry, baseline-tuning fairness, global-time split sensitivity, and the absence of
> independent replication or external custody; and closing those raises defensibility without
> making acceptance predictable. Adversarial internal review has separately calibrated direct
> acceptance in the low single digits before those studies — recorded here as the internal
> estimate it is, not as a forecast this plan endorses.

**If** the maintainer wants a retained number, it must carry: the estimand (direct vs eventual),
venue class, conditioning set, reference class or base rate used, and stated uncertainty.
Otherwise it is removed.

## 5. Why this matters beyond tidiness

An unfounded optimistic number in a planning document is the same category of error the whole
artifact-gate exists to prevent: **a claim with no traceable source.** The paper's numbers must
recompute from artifacts; the plan's numbers should meet a comparable standard or not be
stated. I applied that standard to the manuscript for eleven ticks and did not apply it to my
own forecasts, which is the more useful half of this memo.

## Limits

No file modified other than this memo and the handoff; the roadmap change is **proposed**, not
applied. I have no privileged access to venue acceptance statistics and did not consult any —
which is precisely why I am recommending that no number be asserted. My audit is advisory
evidence and cannot make any result independent.
