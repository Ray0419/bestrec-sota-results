# Claude reject-first methodology audit — TORS checklist

Role: scientific red-team / venue-methodology owner (`CODEX_CLAUDE_COLLABORATION_GUIDE.md`
§3, §9 item 2). Deliverable requested by `TORS_METHODOLOGY_CHECKLIST.md` §3.
Date: 2026-07-31. Author: Claude. Advisory only — not peer review, not independent evidence.

```text
WORKSTREAM:        A5/A6 methodology audit — fill the reject-first form; challenge prefill
OBJECTIVE:         adversarial pass over Codex's checklist statuses + find missing rows
EVIDENCE QUESTION: are any PASS statuses stronger than the evidence supports, and is any
                   reviewer-critical methodological axis absent from the matrix entirely?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, TORS_METHODOLOGY_CHECKLIST.md (Codex's file —
                   status changes are PROPOSED here), preregs, adjudicators, artifact graph,
                   generated tables, manuscript, TeX, release manifest
EXPECTED OUTPUT:   completed audit form + proposed status downgrades + one missing row
STOP CONDITION:    memo committed and pushed; Codex applies or rebuts the proposals
```

---

## Part 1. NEW FINDING **M1 — the matrix has no row for split-protocol validity**

Severity: **high.** Scientific + venue. This is the single largest gap I found.

Every row of the matrix concerns what we do *within* the chosen evaluation protocol.
Nothing in the matrix — and, as far as I can find, **nothing in the manuscript** — addresses
whether the protocol *itself* is methodologically defensible.

The paper evaluates throughout with **iterative 5-core leave-last-out (LLOO)**. LLOO holds
out each user's final interaction independently of global time, so the training set can
contain events that occur **after** some users' test events. Whether one calls that
"leakage" or "a different estimand," it is one of the most frequently raised criticisms in
recommender-systems offline evaluation, and the checklist's own stated primary reference is
a TORS paper titled *"Improving Methodological Standards in Recommender Systems Offline
Evaluation."* A methodology-focused reviewer at that venue is **likely** to ask about it.

Evidence of the gap (mechanical):
- `grep -c "chronological split|global temporal split|temporal leakage|future information|
  time-based split"` over `PAPER_SUBMISSION.md` → **0**.
- LLOO appears only in comparability contexts (vs TIGER/LIGER's AR2014 protocols; vs BLaIR's
  by-timestamp split), never as a methodological exposure of *our* design.

This is sharpened by our own claim. We argue for a **temporal** inductive bias. A reviewer
can reasonably ask: *if temporal structure is what your module exploits, why is your
evaluation protocol not temporally coherent?* That is an uncomfortable pairing, and it is
better answered by us, first, than by a reviewer.

**Required (cheap, no new experiment): add a row + a manuscript paragraph** that (a) states
the protocol explicitly, (b) acknowledges the global-time critique rather than only the
comparability framing, (c) justifies LLOO as the choice that makes our numbers comparable to
the HSTU-BLaIR/TIGER/LIGER protocol family, and (d) records a chronological-split
sensitivity as declared future work. **Do not** claim robustness we have not measured — a
chronological-cutoff replication was proposed earlier in this project and was never run.
Status: **OPEN**.

## Part 2. Proposed status downgrades (Codex to apply or rebut)

I am not editing Codex's file. Four prefilled statuses look stronger than the evidence.

| Row | Prefill | Proposed | Reason |
|---|---|---|---|
| Proposed-method implementation | PASS | **PARTIAL** | Finding **C1** is unresolved: the *definition* of the canonical module is drifting on weight decay. Codex's response calls `fir_v3_wd="zero"` canonical; all positive evidence (E-A `a1learned`; canonical breadth IS+CDs) ran `backbone`. Implementation cannot be PASS while the method's definition is in flux. |
| Evaluation protocol | PASS | **PARTIAL** | The handoff records that E-E V3 prelaunch "opened the combined TRAIN/VALID/TEST export while retaining only TRAIN/VALID fields," limiting sequestration to fitting/selection. That is a disclosed, bounded caveat — but it is a caveat, and PASS reads as unqualified. |
| Reproducibility and artifact graph | PASS | **PARTIAL** | 201/25 recomputation with clean-clone replay is genuinely strong and I do not dispute it. But per-user sidecars and campaign endpoints remain local-only/private, so an external reviewer cannot reconstruct every claim unaided — which Codex's own "required closure" column concedes. Reproducibility PASS should mean *a third party can rerun*, not *we can*. |
| Statistical analysis | PASS-WITH-LIMITS | **PARTIAL** | Each campaign is Holm-controlled *within* its family, and negatives are retained — both good. What is uncontrolled is **selective emphasis across families**: many campaigns have run, and which ones reach the abstract/contribution list is outcome-dependent. Multiplicity within a family does not address a garden-of-forking-paths across families. |

The remaining PASS rows (claim/manuscript/TeX parity) I agree with on the evidence I can see.

## Part 3. Completed reject-first audit form (checklist §3)

```text
AUDIT DATE:                       2026-07-31
REVIEWED COMMIT:                  9b5221eb
TARGET JOURNAL + RANKING AUTHORITY/EDITION:
                                  NOT SUPPLIED — A0 BLOCKED-RANKING. No venue may be
                                  called Tier A. TORS is the strongest topical fit only.
DECISION:                         APPROVE WITH REQUIRED CHANGES (checklist);
                                  NOT READY FOR SUBMISSION (agrees with checklist §4)

STRONGEST NOVELTY OBJECTION:
  "A zero-initialized depthwise causal convolution is not a contribution." Prior art is
  dense and adjacent (Caser, NextItNet, FMLP-Rec, BSARec, C3SASR, AdaMCT, ConvFormer,
  TV-Rec). Our defensible claim is narrow — a leak-free left-causal depthwise FIR residual
  under an all-position next-item objective, plus controlled matched-init evidence. The
  manuscript must lead with the *evidence design*, not the operator, or the operator will
  be judged alone and dismissed.

STRONGEST IDENTIFIABILITY/CONFOUNDING OBJECTION:
  Two, jointly. (i) M1: the evaluation protocol is not temporally coherent while the claim
  is about temporal structure. (ii) The mechanism is still not isolated — A2 is deferred,
  and the completed pointwise study discriminates the FIR from ONE current-only placebo,
  which is not temporal isolation, per-channel necessity, or order necessity.

STRONGEST BASELINE-FAIRNESS OBJECTION:
  A3 findings W1/W2. "12 configurations per method" equalizes count, not coverage, and so
  favors low-dimensional methods — i.e. our own intervention, which adds ~one knob to a
  fixed backbone. Separately, the HSTU-style backbone carries undisclosed prior tuning on
  the very Amazon categories used for comparison. Both currently favor us.

STRONGEST STATISTICAL OBJECTION:
  Seeds are the only randomized unit on fixed splits, so no interval quantifies dataset,
  split, user, or population uncertainty — correctly stated in the paper, but it caps what
  any result can support. Compounding it: selective emphasis across many campaign families
  is uncontrolled (see Part 2), and with three dataset blocks no generalization inference
  is available (A3 finding W3).

STRONGEST EXTERNAL-VALIDITY OBJECTION:
  There is no positive non-Amazon replication, and the MovieLens replication is NEGATIVE
  and unresolved. Until A4 completes, the honest position is that the effect is
  demonstrated on Amazon categories and did not replicate on the one non-Amazon corpus
  tested. That sentence must appear in the paper whether or not A4 later succeeds.

STRONGEST REPRODUCIBILITY/DATA-LEGAL OBJECTION:
  Private/local-only sidecars and endpoints mean external reconstruction of every claim is
  not currently possible; candidate-dataset licence and redistribution boundaries are
  unresolved (A4 gates 2–3, human-only).

AI-USE DISCLOSURE CHECK:
  MATERIAL AND BROAD — must not be minimized to writing assistance. Two AI systems
  (Codex, Claude) have materially contributed to protocol design, experiment drivers,
  adjudicators, statistical analysis choices, literature positioning, manuscript prose,
  and this audit. The design of several campaigns was AI-proposed and AI-red-teamed. A
  disclosure that says "AI was used for editing" would be inaccurate. Human authors retain
  responsibility and must verify. BLOCKED-HUMAN — wording is the maintainer's to approve.

MANDATORY CHANGES BEFORE FREEZE/SUBMISSION:
  1. Resolve C1 (define canonical weight-decay treatment = the one the evidence used).
  2. Add the M1 split-protocol row + manuscript paragraph; no unmeasured robustness claim.
  3. Apply A3 W1/W2 fixes (FIR gets zero extra search; backbone takes the full ladder on
     the new block) and W3/W4 (no n=3 generalization inference; MovieLens evidence class
     fixed one way).
  4. Apply A4 D1/D2 (temporal-diagnosticity dimension; exposure-bias hard gate) before any
     candidate reaches human legal review.
  5. Human: A0 ranking authority; A1 identity/legal; AI-use statement.

OPTIONAL IMPROVEMENTS:
  Per-method efficiency table (params/time/memory) — cheap and helps a small module;
  learned-tap/frequency-response figure; a causality unit test as a proposition.

CLAIMS PERMITTED IF POSITIVE (A3+A4 complete, FIR competitive on a new lawful block):
  "Under symmetric validation-only selection, the FIR intervention remained competitive
  with strong tuned baselines on a dataset new to this work, in addition to matched-init
  gains on three Amazon categories." Evidence class: prospectively frozen,
  same-investigator. NOT SOTA, NOT generalization, NOT independent confirmation.

CLAIMS PERMITTED IF NULL:
  "The study did not discriminate the arms on this block." NOT equivalence. The Amazon
  results stand at their own evidence class; the paper narrows to a domain-conditional
  claim.

CLAIMS PERMITTED IF NEGATIVE (a tuned baseline wins, or the new block reverses):
  The transfer claim is falsified and must be withdrawn — reported with the same
  prominence as the positives, alongside the MovieLens negative, with NO additional FIR
  tuning in response (tuning-matrix §7). The paper then rests on the evaluation-discipline
  contribution and the honest boundary of where the module does and does not help. That
  remains publishable and is the outcome our own gates were built to survive.

FILES AND PRIMARY SOURCES REVIEWED:
  TORS_METHODOLOGY_CHECKLIST.md; CODEX_CLAUDE_COLLABORATION_GUIDE.md; HANDOFF_CODEX.md;
  TIER_A_PUBLICATION_ROADMAP.md; TIER_A_NON_AMAZON_SELECTION_GATE.md;
  PREREG_TIER_A_TUNING_MATRIX_V1_DRAFT.md; PREREG_FIR_TEMPORAL_ISOLATION_V1_DRAFT.md;
  CODEX_RESPONSE_TO_CLAUDE_DESIGN_MEMO.md; PREREG_FIR_POINTWISE_V1.md;
  fir_pointwise_v1_adjudication.json; fir_canonical_breadth_adjudication.json;
  PAPER_SUBMISSION.md (targeted greps: split protocol, weight decay, LLOO).
  NOT reviewed: DOI 10.1145/3800587 primary text (see limits).
```

## Limits

I did **not** read the primary text of DOI 10.1145/3800587. My M1 argument rests on the
LLOO/global-time critique being long-established in the recommender-systems offline
-evaluation literature and on the checklist's own framing of that reference — **Codex or the
human must verify the primary source** before the manuscript cites it in support of any
specific wording. Part 2 downgrades are judgments about status semantics, not claims that
any recorded number is wrong; Codex is the authority on recomputation and provenance and may
rebut. No endpoint inspected, nothing executed, no protocol frozen, no manuscript, table,
graph, checklist, or manifest file modified. My audit is advisory evidence and cannot make
any result independent.
