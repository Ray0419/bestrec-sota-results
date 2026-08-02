# Claude audit — the SASRec result: ML-1M null strengthened, Beauty inversion should not be relied on

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `f901a8f0`; evidence read from
`claude/filter-overparam-experiments` @ `0225e220`. **No run launched; no artifact modified; no
sealed endpoint read.**

```text
WORKSTREAM:        audit the SASRec claim proposed against the manuscript
OBJECTIVE:         what do "null replicates" and "Amazon positive inverts" actually license?
EVIDENCE QUESTION: was the budget confound resolved, and does the Beauty result survive my own floor?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist, experiments/**
EXPECTED OUTPUT:   per-claim verdict + corrected labels
STOP CONDITION:    memo committed and pushed
```

The relaunched, placement-corrected SASRec ladder reports: **ML-1M null replicates** (learned
t=+0.65, shared t=+0.74) and **Beauty inverts** (−0.00130, t=−3.04, 0/5 seeds, CI excludes zero).

---

## 1. **My budget confound is substantially resolved — in the manuscript's favour**

Two ticks ago I argued the ML-1M null might be a training-budget artifact: our prereg gives ~100
optimizer updates while the BSARec harness gives ~28,000–55,000, a 283×–555× gap, and I flagged that
the announced SASRec test would be uninterpretable unless budgets were matched.

The checkpoint paths in `sasrec_ml1m_s42_channel_shared_gate_summary.json` resolve where these ran:

```
/private/tmp/claude-501/…/scratchpad/BSARec/src/output/SASFIR_ML-1M_learned_s42.pt
```

That is the **BSARec harness** on the macOS machine — so the SASRec arms trained at **harness
budget**, not at our ~100 updates. Therefore:

| setting | backbone | budget | ML-1M FIR result |
|---|---|---|---|
| our prereg | HSTU-style (residual on attention) | **~100 updates** | **null** |
| SASRec ladder | plain SASRec (attention) | **~28,000–55,000** | **null** (t=+0.65 / +0.74) |
| FMLP-Rec probe | filter is the *only* mixer | ~28,000–55,000 | **+0.01877, t=7.84** |

**The null now holds across a 283×–555× budget range.** That is the single most useful thing in this
commit, and it is stronger than the commit itself claims: **the budget explanation I raised is
substantially weakened**, and the "training budget" candidate should drop from first place in the
ranked list I proposed two ticks ago. The **backbone** explanation, which I ranked third, now has
positive evidence: two attention-based backbones give null at wildly different budgets, while the
one backbone where the filter is the sole sequence mixer gives a large positive.

I raised the confound; the evidence has substantially answered it against my concern, and I record
that rather than defend the concern.

## 2. **Do not rely on the Beauty inversion — my own instrument says it is below the floor**

The Beauty result is **−0.00130**. Last tick I measured, on **this same harness**, a cross-backend
paired standard deviation for **Beauty of 0.00198** — and the ladder's Beauty contrast **flipped
sign** between MPS and CPU (−0.00138 → +0.00040).

> The SASRec Beauty inversion is **smaller in magnitude than the backend noise it would have to
> survive**, on the same harness and the same dataset where a same-magnitude contrast already
> inverted.

t=−3.04 with 0/5 seeds is a real within-backend signal — I am not calling it noise inside its own
run. But my measured floor says **a single-backend Beauty contrast at this magnitude is exactly the
class of result that does not reproduce.** It ran on MPS only.

**Recommendation: do not cite the Beauty inversion as a scope condition until it is reproduced on a
second backend.** That is one arm pair on one dataset — the cheapest check in this whole programme,
and the "Amazon positive inverts" headline is the most consequential-sounding claim on the branch.

## 3. Two label corrections

**(a) "Independent" must not survive into the manuscript.** The commit says the null replicates *"in
an independent harness, independent implementation and a different split."* Harness and
implementation independence are real and worth stating. But under the project's claim vocabulary,
**never convert a same-team result into "independent"** — the same investigator designed, ran and
interpreted both. The supported label is:

> **same-investigator replication in a different codebase, implementation and split** — not
> independent replication, and not independent confirmation.

The distinction matters because "independently replicates" is precisely the phrase a reader will
carry away, and `A4`/external-validity remains OPEN for exactly this reason.

**(b) The result is in tension with FMLP-Rec's Figure 3, and that should be said.** The earlier memo
argued *against* the backbone explanation by citing FMLP-Rec's own Figure 3, which reports their
filter improving SASRec. Our SASRec measurement finds FIR **null on ML-1M and significantly negative
on Beauty**. That is not a strict contradiction — their filter is a **circular/bidirectional
frequency** filter and ours is a **left-causal FIR**, which is a substantive operator difference —
but the Figure 3 argument can no longer be used to dismiss the backbone hypothesis, and the tension
should be disclosed rather than passed over.

## 4. What this licenses, precisely

**Licensed:** the prospectively frozen ML-1M null is **not** an artifact of our code, our split, or
our training budget — it reproduces in a different implementation, on a different split (6,040 LLOO
vs 1,033 at r≥4 global cutoff), at a budget two-to-three orders of magnitude larger.

**Not licensed:** that FIR harms Amazon categories (Beauty is **not** a counted category, ran on one
backend, and sits below the measured reproducibility floor); that the replication is *independent*;
that the backbone explanation is *established* rather than newly supported; any change to the
counted claim boundary — **Musical_Instruments (vs 0.0406) and Office_Products V3 (vs 0.0271 and
0.0279) stand; Office V1 VOID forever; TFV2 outcome-visible, not confirmatory.**

**Manuscript sentence I would support now**, replacing the narrower one I proposed two ticks ago:

> The MovieLens-1M null reproduces in a separate implementation on a plain SASRec backbone under a
> different split and a training budget two to three orders of magnitude larger, so it is not
> attributable to our code, our split, or our optimizer exposure. It remains same-investigator
> evidence and does not establish a domain moderator.

## 5. The SBERT hypothesis is the right next test, and it is cheap

The proposed cause of the Beauty inversion — BEST-Rec initialises from SBERT text embeddings while
this SASRec is ID-only, and a filter that smooths a semantic trajectory may damage an ID one — is a
**plausible, testable hypothesis, correctly labelled "suspected."** Adding SBERT init to the same
SASRec and re-running is the decisive follow-up. **Run it on two backends**, so the answer does not
inherit the reproducibility problem in §2.

## Limits

Budgets for the SASRec arms are inferred from the harness the checkpoints were written by, not from
a logged optimizer-step count; if those runs overrode the epoch cap, the range changes though the
direction does not. The 0.00198 Beauty backend sd is from 20 paired ladder cells and is itself
imprecise. I did not re-run or re-analyse the SASRec runs; I audited the claim against committed
artifacts. All of this is same-investigator and none of it is independent replication.
