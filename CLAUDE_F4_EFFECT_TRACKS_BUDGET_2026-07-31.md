# Claude finding F4 — the measured FIR effect is perfectly rank-correlated with optimizer budget

Role: scientific red-team. Escalation of `CLAUDE_F3_ML1M_TRAINING_BUDGET_2026-07-31.md`.
Reviewed at HEAD `faaad07d`. Date: 2026-07-31. Author: Claude. Advisory only.
**This finding argues against our own positive result. That is why it is being filed.**

```text
WORKSTREAM:        A4/A2 — stress-test my own F3 before it triggers an expensive re-run
OBJECTIVE:         verify F3 from measured run metadata, not prereg arithmetic
EVIDENCE QUESTION: does the FIR effect track the corpus, or track the training budget?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, PAPER_SUBMISSION.md, COVER_LETTER_TORS.md,
                   TeX, preregs, adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   verified step counts, the correlation, its precise scope, and a cheap
                   discriminating test
STOP CONDITION:    memo committed and pushed; Codex owns verification and any new protocol
```

## Part 1. F3 is CONFIRMED from measured metadata (not just prereg arithmetic)

Last tick I derived step counts from the prereg. I have now read `n_users`, `epochs`, and
`batch_size` from the **committed result JSONs** of each campaign. The trainer's
`augment_factor` defaults to **1** — documented in-source as "number of training examples per
user per epoch" (`run_sasrec_sbert.py:178`) — so steps/epoch = ⌈users/batch⌉ and the ratio is
exactly the user-count ratio:

| corpus | users | epochs | batch | ≈ optimizer steps | vs ML-1M |
|---|---:|---:|---:|---:|---:|
| MovieLens-1M | 6,040 | 20 | 256 | **~472** | 1.0× |
| Industrial_and_Scientific | 50,985 | 20 | 256 | ~4,000 | 8.5× |
| Musical_Instruments | 57,439 | 20 | 256 | ~4,500 | 9.5× |
| CDs_and_Vinyl | 123,876 | 20 | 256 | ~9,680 | 20.5× |

F3 stands, with the ratio spanning **8.5×–20.5×**, not merely 9.5×.

## Part 2. F4 — the effect size tracks the budget, monotonically

Pairing each corpus's measured FIR effect (from its committed adjudication) with its step
count:

| corpus | ≈ steps | learned − identity |
|---|---:|---:|
| MovieLens-1M | 472 | +0.0000002 |
| Industrial_and_Scientific | 4,000 | +0.002110 |
| Musical_Instruments | 4,500 | +0.002265 |
| CDs_and_Vinyl | 9,680 | +0.006150 |

**Spearman ρ(steps, effect) = +1.000** — perfect rank concordance across all four corpora.
Exact two-sided permutation **p = 0.083**, which at n=4 is the *minimum attainable p*; it is
**not significant at α=0.05**, and I will not describe it as significant.

This supplies a **single unified alternative explanation** for the paper's entire cross-corpus
evidence pattern: if an identity-initialized module needs optimizer steps to depart from its
zero initialization, then measured effect size should grow with step count — producing exactly
the observed ordering, including the ML-1M null, **without any appeal to domain, temporal
structure, or the mechanism we claim.**

That is the construction a hostile reviewer would build. Better that we build it first.

## Part 3. Precise scope — what this does and does NOT threaten

**NOT threatened — the within-corpus contrasts stand.** In every campaign both arms shared
one verified backbone initialization *and the same step budget within that corpus*. So
`a1learned − a0ident` inside MI, IS, or CDs remains a valid matched contrast; the canonical
breadth verdict `CANON-BREADTH-POS` is **not retracted** by this finding, and I am not
proposing that it be.

**Threatened — the cross-corpus story.** Three specific claims become unsafe:
1. **The breadth result as "transfer/generalization across categories."** Step budget varies
   2.4× among the three Amazon corpora and correlates perfectly with effect size; corpus
   identity and budget are confounded.
2. **The ML-1M null as a domain-conditional finding** (already F3).
3. **Any statement that the effect is domain-dependent** rather than budget-dependent.

**Also confounded, honestly stated:** step count is not a clean variable here — it is
collinear with user count, catalog size, density, and domain. I cannot and do not claim that
budget *causes* the effect ordering. n=4 is tiny. The correlation is a **hypothesis that has
not been excluded**, and the paper currently contains nothing that excludes it.

## Part 4. The discriminating test — cheap, because short runs are short

**Step-matched down-budget replication on one Amazon corpus.** Take MI (or IS), hold
everything fixed, and reduce the budget to ML-1M-like step count (~472 steps: 20 epochs → ~2
epochs, or subsample users to ~6k with the seed frozen). Run `a0ident` vs `a1learned` at
matched init, ≥5 fresh seeds.

- If the FIR effect **collapses toward zero** at ML-1M-like budget → the budget explanation is
  supported, the ML-1M null is not a domain finding, and the paper's cross-corpus narrative
  must be rewritten around training budget.
- If the effect **persists** at ~472 steps → F3/F4 are refuted, the ML-1M null survives as a
  domain-conditional result, and the breadth transfer story is strengthened *because we tried
  to break it and failed*.

This is genuinely inexpensive: the runs are ~1/10 the length of a normal seed by construction.
It requires a **new frozen preregistration and identifier**, a committed adjudicator before
launch, and a fresh reject-first memo — it must not be presented as a re-analysis of existing
campaigns, and every existing record is retained regardless (guide §4, §6).

Either outcome is publishable, and the second one would materially *strengthen* the paper.

## Part 5. What the manuscript must not say until this resolves

- Do not narrate ML-1M as a domain-conditional negative (F3).
- Do not describe the three-category breadth as evidence of **transfer** or
  **generalization** across domains without disclosing the budget confound.
- My withdrawn E1 bound-wording stays withdrawn.
- The abstract's cross-corpus framing needs a stated limitation: *training budget was not
  matched across corpora, and measured effect size is monotone in budget across the four
  corpora tested.*

## Limits and what I may be wrong about

Read only committed artifacts (result JSONs, adjudication JSONs, prereg, trainer source); **no
sealed endpoint opened, nothing executed, nothing modified.** Step counts are computed from
`n_users`/`epochs`/`batch_size` assuming `augment_factor=1`; Codex should confirm no campaign
overrode it. ρ=+1.000 at n=4 is fragile — a single additional corpus could destroy it, and
p=0.083 is not significance. The ordering is also exactly what one would expect if larger,
denser corpora simply afford larger measurable effects for *any* reason; budget is one
candidate among several, and I am not asserting it is the right one. My audit is advisory
evidence and cannot make any result independent.
