# Claude patch set — every pending proposal as an executable edit

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `111dc42c`. **No artifact modified; I
propose, Codex applies.**

```text
WORKSTREAM:        convert ten memos of recommendations into applicable edits
OBJECTIVE:         lower the cost of acting from "read ten memos" to "apply N edits"
EVIDENCE QUESTION: which pending proposals are exactly specifiable, and what is the anchor?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: everything else — every patch below is a PROPOSAL
EXPECTED OUTPUT:   ordered patch list with file, anchor, replacement, and cost
STOP CONDITION:    memo committed and pushed
```

Codex actioned every finding raised before the 02:26 manuscript edit window and none of the eleven
raised since. The likely bottleneck is that recommendations sit in prose across ten memos. This
converts them into anchored edits. **Nothing here is applied.**

---

## P1 — Roadmap contradicts a committed memo. **New finding this tick.**

`TIER_A_PUBLICATION_ROADMAP.md` line 3 states *"This is not an acceptance forecast"* and line 21
then issues one:

> *"The working conditional estimate remains about 35–50% at a well-matched strong journal after
> human metadata are completed; 65% is not yet a defensible estimate."*

My committed calibration memo (`CLAUDE_CALIBRATION_MEMO_2026-07-31.md`, 2026-07-31) called this
**indefensible** — *"it is not a forecast; it is a mood"* — and proposed exact replacement text. **Two
days later the roadmap still carries it.** Two committed documents disagree, and the roadmap is the
one that directs work.

**Patch:** replace the sentence at `TIER_A_PUBLICATION_ROADMAP.md:20–23` with the block already
drafted at `CLAUDE_CALIBRATION_MEMO_2026-07-31.md:87–97` (begins *"Acceptance likelihood is not
forecast in this document."*). **Cost: one paste.** *(§5's "Advancement rule" at line 135 is
consistent with the fix and needs no change.)*

## P2 — Abstract: "robust modular gain"

**File:** `PAPER_SUBMISSION.md:12`. **Anchor:** *"provides a robust modular gain in sequential
recommendation."* **Issue:** "robust" + "modular" implies backbone portability that our own SASRec
probe contradicts; §6:569 defines the term operationally but a reader meets line 12 first.
**Patch (option a):** delete "robust". **Or (option b):** keep and add the §6 sentence in P3.
**Pick one.** Cost: one word, or one sentence.

## P3 — §6: disclose the SASRec probe

**File:** `PAPER_SUBMISSION.md`, §6 near line 569. **Add:**

> An exploratory probe attaching the same residual to a plain SASRec backbone found no gain on
> MovieLens-1M and a negative contrast on Beauty; both are single-backend exploratory results below
> our measured cross-backend reproducibility floor, and neither is a counted category. They indicate
> that the reported gain should not be assumed portable across backbones.

## P4 — ML-1M: the null is now much better supported

**File:** `PAPER_SUBMISSION.md` §5/§6 and `COVER_LETTER_TORS.md`. **Add:**

> The MovieLens-1M null reproduces in a separate implementation on a plain SASRec backbone under a
> different split and a training budget two to three orders of magnitude larger, so it is not
> attributable to our code, our split, or our optimizer exposure. It remains same-investigator
> evidence and does not establish a domain moderator.

**Do not** write "independently replicates".

## P5 — Quantified tuning-fairness disclosure (A3)

**File:** `PAPER_SUBMISSION.md` §4 or the comparator matrix. Text as drafted in
`CLAUDE_A3_TUNING_FAIRNESS_AUDIT_2026-08-01.md` §"exact text": 56 configurations for our family
versus two presets on one tuning seed for WEARec and one frozen configuration each for the
AlphaFuse-style and SASRec-ID arms; epoch budgets per-recipe.

## P6 — The three Musical_Instruments estimates

**File:** `PAPER_SUBMISSION.md` §5.2. Text as drafted in
`CLAUDE_E_CLAIM_FIDELITY_AUDIT_2026-08-01.md` §2: the three frozen estimates (+0.002265 Welch,
+0.002116 paired, +0.001872 paired), their different seed blocks and estimators, the 0.000393 span,
mutual overlap, and the explicit label *repeated outcome-known internal estimates, **not**
independent replication*.

## P7 — Checklist rows

**File:** `TORS_METHODOLOGY_CHECKLIST.md` §1.

| row | proposed |
|---|---|
| Novelty as a modular contribution | PARTIAL → **PASS** |
| Baseline selection rationale | PARTIAL → **PASS-WITH-LIMITS** |
| Outcome-independent reporting | PARTIAL → **PASS**, **now AT RISK** pending P2/P3 |
| Research question and hypotheses | restate: its precondition (matched-input study) is **DEFERRED**, so it cannot close as written |

*Hyperparameter tuning fairness* stays **OPEN**; *External validity* stays **OPEN**; *Exact-input
temporal isolation* stays **DEFERRED**.

## P8 — Strike retracted F1 from the open-findings register

F1 was **wrong**, not unactioned — the committed ML-1M adjudicator already gated tap norms before I
raised it. See `CLAUDE_A4_MOVIELENS_NARROWING_V2_2026-08-01.md`. **Delete the row**, do not carry it.

## P9 — Close the reader-edition audit question

The 22:23 audit asks whether `PAPER_SUBMISSION.pdf` is still a live deliverable given the page
divergence. `PAPER_SUBMISSION.md:5` already answers it — reader edition versus focused TORS package,
by design. **Cite the line and close the question.**

## P10 — Ladder runner records its operating point

**File (experiment branch):** `experiments/filter_overparam/run_all.sh`. Pass `--lr` explicitly so
the learning rate is in the command rather than inherited from the parser default of 0.001, and note
the suite documents 0.0005 for Beauty. Also give the reproduction anchor a **numeric tolerance**.

## P11 — Non-decisive citations

**File:** `paper_tex/references.bib` + §2. Add **MUFFIN** (CIKM 2025), **SLIME4Rec** (ICDE 2023),
**DWTRec** (2025) — named in the project's own novelty review, verified absent (`bib=0, md=0`).
**No omitted method is decisive; do not delay submission for this.**

---

## Ordering

**Zero-cost, do first:** P1, P8, P9 — each is a paste or a deletion, and P1 resolves a contradiction
between two committed documents.
**One sentence each:** P2, P3, P4, P6.
**One paragraph:** P5.
**Cell edits:** P7.
**Other branch:** P10, P11.

**None of these changes the counted claim boundary**: Musical_Instruments (vs 0.0406) and
Office_Products V3 (vs 0.0271 and 0.0279); **Office V1 VOID forever**; TFV2 outcome-visible, not
confirmatory. None reopens a frozen analysis. None is a human-only gate — **A0, A1, A4 licence and
custody, the AI-use statement, and tuning-matrix authorization remain BLOCKED and are not in this
list.**

## Limits

Anchors are line numbers and quoted strings as of `111dc42c` in a working tree with uncommitted
Codex edits; they may drift. P2/P3 are alternatives — applying both is acceptable but only one is
required. Every item is a proposal; I have applied none, and Codex retains implementation authority.
