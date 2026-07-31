# Claude A4 memo — what the MovieLens result permits, and the honest narrowing

Role: scientific red-team (`CODEX_CLAUDE_COLLABORATION_GUIDE.md` §3; queue item d).
Reviewed at HEAD `792efb6c`: `PREREG_FIR_EFFICIENCY_ML1M_V1.md`,
`_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json` (verdict
`ML1M-NO-FIR-REPLICATION`). Date: 2026-07-31. Author: Claude. Advisory only.

```text
WORKSTREAM:        A4 external validity — what the ML-1M outcome does and does not permit
OBJECTIVE:         draft the honest narrowing; test the null before narrating it
EVIDENCE QUESTION: is the ML-1M null a domain finding, or an inert-module artifact?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, PAPER_SUBMISSION.md, TeX, COVER_LETTER_TORS.md,
                   preregs, adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   blocking diagnostic finding + conditional narrowing text + permits/forbids
STOP CONDITION:    memo committed and pushed; Codex runs the discriminating check
```

---

## F1 (BLOCKING, must be resolved before the paper narrates MovieLens)

**On 3 of 8 seeds the learned-FIR arm and the identity arm produced bit-identical
NDCG@10.** Read from the committed adjudication artifact (the adjudicator has already run;
no sealed endpoint was opened):

| seed | identity | learned | diff |
|---|---|---|---|
| s2 | 0.047012017140 | 0.047012017140 | **0.000e+00** |
| s4 | 0.046056306397 | 0.046056306397 | **0.000e+00** |
| s6 | 0.050821479159 | 0.050821479159 | **0.000e+00** |

and the same pattern across the other parameterizations — bit-identical-to-identity counts:
`lowrank 3/8`, `learned 3/8`, `grouped 2/8`, `pointwise 2/8`, `shared 0/8`.

With ~6,040 evaluation users, a bit-identical NDCG@10 means **not one user's top-10 changed**.
That is not a small effect; it is *no effect on the ranking at all*. Three candidate
explanations, which the paper must distinguish **before** interpreting the null:

1. **The optimizer drove the taps to a functional no-op on ML-1M** — the model "voted the
   filter off." This would be scientifically *interesting* and consistent with the paper's
   own central asymmetry (capacity-adding levers get switched off by their own free
   parameters); it would make the null mechanistically interpretable rather than merely
   disappointing.
2. **Metric/tie granularity** — score perturbations too small to reorder any top-10.
3. **A pipeline fault** — the module not actually active on those runs. This would make the
   null an **artifact**, and the study would need re-running rather than narrating.

**Discriminating check (cheap, Codex-owned, no new training):** the runner already records
the final tap norm `fir_v3_final_l2`, and the E-A/breadth adjudicators already gate the
identity control on it being exactly 0. Read `fir_v3_final_l2` for the ML-1M `learned` arm
per seed. If ≈0 → explanation 1 (or 3). If clearly non-zero while NDCG is bit-identical →
explanation 2. If exactly 0 on the *learned* arm, that is explanation 3 territory and is an
integrity question, not a result.

**Until this is resolved, the paper should not assert what the MovieLens null means.** A
reviewer who notices three bit-identical arms will ask "was your module even switched on?",
and that question must already be answered in the text.

## F2 (substantive). The compression claim is close to vacuous on this corpus

The frozen Q2 asks whether shared/grouped/low-rank parameterizations are **noninferior** to
per-channel within ±0.000500 NDCG@10. On ML-1M they are — but **so is doing nothing**: no arm
separates from identity (all arm means fall in 0.05212–0.05221). Noninferiority among arms
that are each indistinguishable from the identity control carries **no information about
parameter efficiency**; it only says that several inert parameterizations are equally inert.

The abstract's "the parsimonious FIR arms support only conditional coefficient-count
compression" therefore rests on a comparison whose informativeness is destroyed by the Q1
null. It is not *false* — it is pre-declared and technically satisfied — but it should be
stated with the dependency visible, or a reviewer will read it as a salvaged positive.
Compression is only meaningful where the thing being compressed does something; on ML-1M
nothing does.

---

## What the MovieLens result permits — proposed wording

**Conditional on F1 resolving to explanation 1 or 2** (a genuine null, module active):

> On MovieLens-1M, under a preregistration frozen before data acquisition, the causal FIR
> residual did not improve full-catalog NDCG@10 over its matched identity control
> (learned − identity `+0.000000`, 95% CI `[−0.000074, +0.000075]`, eight matched seeds).
> The interval's upper bound is more than an order of magnitude below the estimates observed
> on the Amazon categories (`+0.002110` to `+0.006150`), so an effect of the Amazon-observed
> magnitude is **not supported** on this corpus. This is a bound on the effect size, **not**
> a demonstration of equivalence: no equivalence margin was pre-declared for this contrast,
> and a confidence interval covering zero does not establish that the effect is zero.
> Accordingly, the modular gain reported here is **domain-conditional**: it is established on
> the tested Amazon Reviews 2023 categories and did not appear on the one non-Amazon corpus
> tested.

**Conditional on F1 resolving to explanation 3** (module inactive on some runs): the study is
**not interpretable as a domain finding** and must be reported as an execution defect with
the affected seeds identified, or re-run. Do not narrate an artifact as a null.

## What it does NOT permit — enumerated

- **Not equivalence.** No margin was pre-declared for Q1; the CI covers zero.
- **Not "the FIR does not work."** One corpus, one configuration transferred from Amazon,
  one protocol. n=1 domain cannot support a general negative any more than three Amazon
  categories support a general positive.
- **Not a parameter-efficiency claim** (F2).
- **Not a refutation of the Amazon results**, which are separately adjudicated under their
  own frozen rules and stand at their own evidence class.
- **Not a "temporal structure doesn't matter" conclusion** — the ML-1M rating-based positive
  event definition, session structure, and inter-event gaps differ from Amazon in ways this
  study did not measure. That gap is precisely what the A4 **temporal-diagnosticity
  dimension** (memo `CLAUDE_DESIGN_MEMO_NON_AMAZON_SELECTION_GATE.md`, finding D1) is meant
  to make measurable *before* the next dataset is chosen. **This is now doubly important:
  had a diagnosticity screen been applied to ML-1M in advance, we would already know whether
  it was a corpus where the mechanism could show itself.**

---

## Consolidated register of open Claude findings

Five ticks of memos, none yet actioned. Ordered by (blocking × cost-to-fix); all Codex-owned
unless marked.

| ID | Finding | Severity | Cost | Status |
|---|---|---|---|---|
| **F1** | 3/8 ML-1M seeds bit-identical to identity — null may be an artifact | **blocking** | very low (read a recorded field) | new, this tick |
| **E5** | Cover letter stale: 192/18 vs 201/25 cells; 751→1,073 files; says pointwise placebo "was run"… it was | high (editor-facing) | low | open |
| **C1** | "canonical" drifting on weight decay vs all positive evidence (`backbone`) | high | low (pick one, state it) | open |
| **M1** | No split-protocol row; LLOO global-time critique unaddressed anywhere | high | low (a paragraph) | open |
| **F2** | Compression claim near-vacuous given the Q1 null | medium | low (add dependency) | new, this tick |
| **E1–E4** | Under-claiming: "negative"→precise null/bound; non sequitur; audit register; "outcome-known" mislabel | medium | low | open |
| **W1/W2** | Tuning matrix: 12-configs-each favors *our* low-dim method; backbone carries prior tuning | high | design change | open |
| **D1/D2** | Dataset gate: no diagnosticity dimension; exposure-bias gate missing | high | design change | open |
| **A0/A1/A4-legal** | ranking authority; author+legal metadata; licence/custody; AI-use statement | blocking | **human-only** | open |

## Limits

I read a **committed adjudication artifact**, not a sealed endpoint — the adjudicator was the
first reader, as required. F1 is an observation about recorded numbers plus three candidate
explanations; I have **not** established which holds, and Codex owns the discriminating check
and any recomputation. All wording above is **proposed**; I modified no manuscript, cover
letter, prereg, adjudicator, table, graph, or manifest file. My audit is advisory evidence
and cannot make any result independent.
