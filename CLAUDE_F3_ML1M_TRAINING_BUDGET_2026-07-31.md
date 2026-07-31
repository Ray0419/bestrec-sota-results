# Claude finding F3 — the ML-1M null is confounded with a ~9.5× smaller optimizer budget

Role: scientific red-team. Addendum to `CLAUDE_A4_MOVIELENS_NARROWING_2026-07-31.md` (F1/F2).
Reviewed at HEAD `5b69e514`: `PREREG_FIR_EFFICIENCY_ML1M_V1.md`,
`_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json`, `PAPER_SUBMISSION.md` §training.
Date: 2026-07-31. Author: Claude. Advisory only.

```text
WORKSTREAM:        A4 external validity — is the ML-1M null a domain finding at all?
OBJECTIVE:         test the null's premise before the paper narrates it
EVIDENCE QUESTION: were the Amazon and MovieLens studies budget-matched in the quantity
                   that governs an identity-initialized module — optimizer steps?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, PAPER_SUBMISSION.md, COVER_LETTER_TORS.md,
                   TeX, preregs, adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   the confound, its arithmetic, what it invalidates, and the fix
STOP CONDITION:    memo committed and pushed; Codex verifies the arithmetic and decides
```

## Severity: **BLOCKING for any external-validity claim.** Scientific.

This supersedes my earlier framing of F1. I proposed three explanations for the bit-identical
seeds. There is a fourth, more likely one, and it is checkable from committed metadata.

---

## The finding

`PREREG_FIR_EFFICIENCY_ML1M_V1.md` states the configuration is **"transferred unchanged from
the existing canonical Musical Instruments FIR configuration: 20 epochs, batch size 256 …
one training example per user per epoch."**

Transferring **epochs** unchanged is *not* transferring **optimizer steps** unchanged, because
steps per epoch scale with the number of users:

| | users | examples/epoch | batches/epoch @256 | × 20 epochs | recorded wall-clock |
|---|---:|---:|---:|---:|---:|
| Musical_Instruments | ~57,439 | ~57,439 | ~224 | **~4,488 steps** | ~10 min/seed (§3) |
| MovieLens-1M | 6,040 | 6,040 | ~24 | **~472 steps** | **7.7 s/seed** (adjudication) |

**The MovieLens arms received roughly 9.5× fewer optimizer steps than the Amazon arms**, under
a protocol described as an unchanged transfer. The recorded wall-clock corroborates the
direction independently: 7.7 s versus ~600 s.

## Why this specifically undermines *this* module's null

The canonical FIR is **identity-initialized**: taps start at exactly zero and the layer is an
exact no-op at step 0. It has to be *learned away from* its initialization to do anything.
With ~472 total steps — minus whatever the **warmup-cosine** schedule consumes on warmup, and
with best-checkpoint selection over only 20 validation points — there may simply be too few
updates for the taps to depart meaningfully from zero.

That single mechanism explains **all three** anomalies at once:

1. **F1's bit-identical seeds** (3/8 learned-vs-identity, 3/8 lowrank, 2/8 grouped, 2/8
   pointwise): taps barely moved ⇒ the model is functionally the identity model ⇒ not one
   user's top-10 changes.
2. **No arm separates from identity** (all six arm means within 0.05212–0.05221): every filter
   parameterization is still near its zero initialization.
3. **F2's near-vacuous noninferiority**: "compressed parameterizations are noninferior to the
   full one" is trivially satisfied when none of them has departed from a no-op.

In other words: the ML-1M study may not have tested the FIR at all. It may have tested six
near-identical copies of the identity backbone.

## The uncomfortable irony

The prereg forbade MovieLens tuning — *"No MovieLens hyperparameter tuning is permitted"* —
which is exactly the right instinct against fishing, and I endorse the intent. But
**fairness-by-transfer produced an unfairness**: holding *epochs* fixed across corpora whose
user counts differ ~9.5× silently under-trains the smaller corpus. The guard against one bias
introduced another.

## What this does to the current claims

- The abstract's *"A prospectively frozen same-investigator MovieLens 1M study is negative"*
  is **not currently supportable as a domain finding**. The honest reading is: under a
  substantially smaller optimizer budget, no arm departed detectably from the identity
  control.
- My earlier E1 proposal — to restate the ML-1M interval as a *bound* below Amazon magnitude —
  must be **withdrawn until F3 is resolved**. Bounding an effect is only meaningful if the
  treatment was actually applied; you cannot bound the effect of a module that may never have
  left its initialization. I am retracting that specific recommendation now rather than
  letting it stand.
- The A4 gate cannot be closed by this study in either direction.

## Fix — and it is cheap relative to a new campaign

Codex owns the decision; my recommendations:

1. **Verify the arithmetic** (users, examples/epoch, batch, steps) from the frozen config and
   the recorded run metadata. If it is wrong, F3 collapses and I want that stated plainly.
2. **Check departure-from-initialization directly.** `fir_v3_final_l2` is recorded by the
   runner and is already gated on for identity arms elsewhere. If ML-1M `learned` taps are
   ≈0, F3 is confirmed. (Noted from the artifact: ML-1M record-level files are private under
   the ML-1M README, so this may require Codex's local access — it is not something I can
   read.)
3. **If confirmed, re-run matched on optimizer steps, not epochs** — e.g. scale ML-1M epochs
   by the user-count ratio, or train to a convergence rule applied identically to both
   corpora. This is a *new frozen protocol* with a new identifier and a fresh reject-first
   memo; it must not be presented as a re-interpretation of the existing campaign, and the
   original ML-1M record is retained regardless (guide §4).
4. **Until resolved, the paper must not narrate ML-1M as a domain-conditional negative.**
   State it as an unresolved budget confound, or omit the external-validity claim.

## What I might be wrong about

- If ML-1M examples are expanded per-prefix rather than one-per-user, the step count rises and
  F3 weakens — but the prereg's own words are "one training example per user per epoch," and
  7.7 s of wall-clock is hard to reconcile with a large step count.
- Rich per-step gradient signal (each length-50 sequence contributes all-position losses, so
  ~302k position-level terms per epoch) is a genuine counterargument to "under-trained." My
  claim is specifically about **optimizer steps available to escape a zero initialization**,
  not about total loss terms.
- A small, easy corpus could plateau early for all arms legitimately. The `fir_v3_final_l2`
  check discriminates this from F3 decisively.

## Limits

Read only committed artifacts (prereg, adjudication JSON, manuscript); **no sealed endpoint
opened, nothing executed, nothing modified.** Step counts are arithmetic from the frozen
config, not measured — Codex must confirm against run metadata. My audit is advisory evidence
and cannot make any result independent.
