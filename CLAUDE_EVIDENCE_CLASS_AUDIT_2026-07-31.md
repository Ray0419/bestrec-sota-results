# Claude evidence-class consistency audit — manuscript claim surfaces

Role: scientific red-team (`CODEX_CLAUDE_COLLABORATION_GUIDE.md` §3, queue item e).
Closes the checklist row *"Outcome-independent reporting — Claude must verify that title,
abstract, contribution list, conclusion, and cover letter do not selectively upgrade
favorable outcomes."*
Reviewed at HEAD `81a9bcfb`. Date: 2026-07-31. Author: Claude. Advisory only.

```text
WORKSTREAM:        A6/outcome-independent reporting — evidence-class consistency
OBJECTIVE:         do the claim surfaces express the SAME evidence class as the artifacts?
EVIDENCE QUESTION: is any favorable outcome upgraded, or any label imprecise in either
                   direction?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_SUBMISSION.md, TeX, TORS_METHODOLOGY_CHECKLIST.md,
                   PAPER_REVIEW_AUDIT.md, preregs, adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   pass/fail on selective upgrading + precision defects + proposed wording
STOP CONDITION:    memo committed and pushed; Codex applies wording or rebuts
```

---

## Verdict on the assigned question: **PASS — no selective upgrading detected**

I went looking for the standard failure (favorable results promoted, unfavorable buried) and
did not find it. This is a genuine, checkable result, so I state it plainly rather than
manufacture a criticism:

- **The MovieLens null is in the abstract, with its numbers** — not deferred to §6 or the
  supplement. Most papers would not do this.
- **The shared-filter non-separation is in the abstract** (`−0.000081 [−0.000337,
  +0.000175]`) *and* is used to actively limit our own claim ("limiting any claim of
  per-channel-tap necessity"). That is a negative reported against interest, unprompted.
- **The contribution list does not upgrade**: contribution 1 says "a modular component, not
  a new architecture"; contribution 2 leads with "Internal evidence, a negative non-Amazon
  test, and a mechanism boundary."
- **Explicit non-claims are present**: "not a new architecture, general FIR benefit, SOTA
  result, or independent confirmation."
- The title is module-scoped and does not assert benefit.

Checklist row **Outcome-independent reporting: PARTIAL → I propose PASS**, conditional on
the four precision fixes below (which are about accuracy, not about upgrading).

---

## But the paper now errs in the *other* direction — four precision defects

The guide says: *"Use the strongest label actually supported, never the most attractive
label."* That rule is symmetric. **Under-claiming is also a mislabel**, and three of the four
defects below are cases where the paper describes its own evidence as weaker or vaguer than
the artifacts support.

### E1 (substantive). "negative" mislabels a *precise null*, and discards real information

The abstract says the MovieLens 1M study "is **negative**: learned minus identity
`+0.000000 [−0.000074, +0.000075]`."

A point estimate of exactly zero with a tight symmetric interval is a **null / non-detection**,
not a negative effect. "Negative" ordinarily means the effect ran the wrong way. More
importantly, the current wording **throws away the most useful thing about this result**: the
interval is tight, and its upper bound (`+0.000075`) is roughly **30× smaller** than the
Musical_Instruments estimate (`+0.002265`). So the study does not merely "fail to find"
something — it **bounds** the MovieLens effect well below the Amazon-observed magnitude.

That is materially stronger domain-conditionality evidence than "negative," and it is what
makes the MovieLens result scientifically valuable rather than merely disappointing.

**Constraint on the fix:** this must be phrased as a **bound**, never as equivalence. A CI
crossing zero is not equivalence (guide §7), and no equivalence margin was pre-declared.
Bounding language ("the 95% interval excludes effects larger than X") is a legitimate reading
of an interval; "equivalent to zero" is not.

*Proposed wording:* "A prospectively frozen same-investigator MovieLens 1M study did not
detect the effect: learned minus identity `+0.000000 [−0.000074, +0.000075]`, an interval
whose upper bound is far below the Musical_Instruments estimate — so an Amazon-magnitude
effect is not supported on this corpus (a bound, not an equivalence claim)."

### E2 (minor). "Thus" is a non sequitur, and the abstract carries unexplained jargon

"**Thus** the parsimonious FIR arms support only conditional coefficient-count compression,
not practical efficiency or cross-domain replication." The compression finding does not
follow from the MovieLens null; they are separate results. Replace "Thus" with a neutral
connective, and either define or drop "conditional coefficient-count compression" — it is
opaque in an abstract and will read as evasion rather than precision.

### E3 (substantive, venue). The abstract is written in audit-response register, and that is itself a rejection risk

Roughly seven of nine sentences carry a hedge, a negation, or an explicit non-claim. There
is **no sentence stating why a reader should care.** A reviewer skimming it encounters, in
order: outcome-known settings → does not separate from a shared filter → negative MovieLens →
package results "below the paper's existing reference" → "not a new architecture, general FIR
benefit, SOTA result, or independent confirmation."

The honest content is right; the *framing* sells a null. What actually distinguishes this
work — a **matched-initialization, per-seed-verified isolation of a modular effect,
replicated across categories under one frozen configuration with zero per-category tuning,
inside a fail-closed artifact gate** — is present in the paper but absent from the abstract's
first three sentences.

This is a venue-methodology judgment, and I want to be explicit that it is **not** a request
to weaken a caveat: keep every number and every non-claim exactly as they are. Add one
opening sentence of motivation and one sentence naming what *was* established, then let the
existing bounds do their work. Over-hedging is not a safety margin; at a strong journal it
reads as the authors themselves doubting the contribution.

### E4 (precision). "outcome-known" is the wrong label for the canonical breadth campaign

The abstract says "three **outcome-known** Amazon Reviews 2023 category/split settings."
For the canonical-breadth campaign (Industrial_and_Scientific, CDs_and_Vinyl) that is
imprecise in the *harsh* direction: the protocol and adjudicator were **committed before
launch**, and it used **fresh unused seeds** (20260810–17). What was outcome-known was the
*legacy* category-level result at **design** time — not the campaign's execution.

Per the guide's vocabulary the accurate description separates the two:
**"prospectively frozen, same-investigator execution on categories whose legacy outcomes were
known at design time."** That is longer, but it is the true class, and it is the one that
distinguishes this campaign from the genuinely outcome-visible ones (V2/V4). Collapsing both
into "outcome-known" erases a real methodological difference we actually earned.

---

## E5 (substantive) — the cover letter is materially STALE, on three counts

`COVER_LETTER_TORS.md` does exist (my first pass missed it). I predicted above that the
cover letter is "the surface most prone to drift." It is — and this is the most concrete
defect in this memo, because **the cover letter is the first document an editor reads.**

| Cover letter says | Current state | Source |
|---|---|---|
| "recomputes **192** paper-bound cells across **18** claim families" | **201** active cells across **25** required families | `HANDOFF_CODEX.md`; graph output |
| "verified **751/751** manifested files"; "**282** release-only assets" | **1,073** manifest files; **407** release-only assets | `HANDOFF_CODEX.md` V4 replay record |
| "**no** active lag-0 or **pointwise** parameter-matched non-temporal placebo **was run**" | the pointwise placebo **was run and adjudicated**: `POINTWISE-FIR-DISCRIMINATED` | `fir_pointwise_v1_adjudication.json` |

The third row is the serious one. In fairness to the drafter, the sentence is *scoped* to the
six-arm control study ("the study does not isolate…"), and within that study no such arm was
included — so it is arguably technically true. But the plain reading is global, and it
**directly contradicts the abstract**, which states the learned filter "exceeds an
equal-parameter current-position-only placebo (+0.001941 [+0.001788, +0.002095])." An editor
comparing cover letter against abstract sees a contradiction on the paper's central mechanism
claim. Worse, it under-reports us: the pointwise campaign is precisely the evidence that
addresses "generic trainable-residual capacity," and the letter says it does not exist.

**Required:** re-derive all counts in the cover letter from the current graph/manifest at the
time of submission (they will drift again), and rewrite the placebo sentence to scope it
explicitly to the six-arm study while citing the separate pointwise campaign and its verdict.

This also generalises: **any hand-maintained count in a persuasion surface should be
regenerated, not retyped.** The artifact gate protects the manuscript's numbers; it does not
protect the cover letter's.

## Limits

This is a documentary audit of claim surfaces against committed adjudication artifacts. I did
not recompute any number, inspect any endpoint, or execute anything, and I modified no
manuscript, TeX, checklist, table, graph, or manifest file — all wording above is
**proposed** for Codex. The E1 bound statement must be checked by Codex against the exact
adjudication artifact before it is used. My audit is advisory evidence and cannot make any
result independent.

**Codex may apply or rebut E1–E4 and the proposed PARTIAL → PASS status change for
outcome-independent reporting.**
