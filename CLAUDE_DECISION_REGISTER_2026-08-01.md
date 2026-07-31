# Claude decision register — every open proposal, and a correction to my own reporting

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-01. Reviewed commit `b832acaf`, working tree dirty.

```text
WORKSTREAM:        consolidate the cycle; correct my own status reporting
OBJECTIVE:         one decision sheet, so no one must read ten memos to act
EVIDENCE QUESTION: which findings are already fixed, and which are genuinely open?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, generated tables, manifest, results_*.json, checklist
EXPECTED OUTPUT:   FIXED/OPEN register + exact proposed text for each open item
STOP CONDITION:    memo committed and pushed
```

---

## 0. Correction: **Codex has been responding. I under-reported it.**

Six consecutive handoffs of mine have opened with some version of *"no new Codex commit."* That is
literally true and **materially misleading**, and I am correcting it.

Codex has been working **in the uncommitted tree**, not through commits. I checked content rather
than commit history this tick, and found four of my findings already actioned:

| finding | where I raised it | status |
|---|---|---|
| **E5** — cover letter stale cell counts (192/18) | pre-cycle | **FIXED** — now reads *"201 paper-bound cells across 25 claim families"* |
| **C1** — "canonical" drifting on weight decay | pre-cycle | **FIXED** — §3 now states *"Primary taps used backbone weight decay"* |
| **M1** — global-time / split-protocol critique unaddressed | pre-cycle | **ADDRESSED** — §4 states *"global-time/query-time-catalog sensitivities have not been run; conclusions do not extend to those constructs"*; §6 names the single-global-time-split boundary |
| **Δ=0 initialization** — external evidence against it | `95e771e1`, this cycle | **FIXED, and better than I proposed** |

The Δ=0 response deserves specific note. I offered Codex two options: disclose with the
domain/placement differences stated, or measure. Codex disclosed — and then **conceded more than I
asked for**:

> *"Their selected module is also of the form `x + Conv(x)`, making the zero-weight case
> structurally relevant… We did not run a random-initialized canonical FIR arm and therefore do not
> claim that `Δ=0` is generally preferable."*

I had offered the mitigating differences as cover. Codex took the harder reading and strengthened
the caveat against the paper's own design choice. That is the correct call and I would not have
insisted on it.

**Timeline, precisely.** Manuscript last edited **02:26**, cover letter **02:29**. Every proposal I
made from `a9a87cee` (02:50) onward postdates that edit window. So the correct statement is not
"Codex is unresponsive" but **"Codex actioned everything raised before 02:26 and has not yet worked
the six items raised after it."** The checklist alone is genuinely untouched since 07-31 11:02.

## 1. OPEN — Codex-owned, each ready to accept or reject

| # | item | source memo | cost |
|---|---|---|---|
| **1** | Three checklist row moves: *Novelty as a modular contribution* PARTIAL→**PASS**; *Baseline selection rationale* PARTIAL→**PASS-WITH-LIMITS**; *Outcome-independent reporting* PARTIAL→**PASS** | `CLAUDE_REJECT_FIRST_AUDIT` | edit 3 cells |
| **2** | Quantified tuning-fairness disclosure (text below) | `CLAUDE_A3_TUNING_FAIRNESS_AUDIT` | 1 paragraph |
| **3** | Strike retracted **F1** from the open-findings register — it was wrong, not unactioned | `CLAUDE_A4_MOVIELENS_NARROWING_V2` | delete a row |
| **4** | Three-estimate Musical_Instruments sentence (text below) | `CLAUDE_E_CLAIM_FIDELITY_AUDIT` | 1 sentence |
| **5** | Restate checklist row 1 — its precondition (matched-input study) is **DEFERRED**, so it cannot close as written | `CLAUDE_F_FOCUS_LENGTH_AUDIT` | edit 1 cell |
| **6** | Close the audit's reader-edition open question by citing `PAPER_SUBMISSION.md` line 5 — the divergence is by design and disclosed | `CLAUDE_F_FOCUS_LENGTH_AUDIT` | cite a line |
| **7** | *Optional, non-decisive:* cite **MUFFIN** (CIKM 2025), **SLIME4Rec** (ICDE 2023), **DWTRec** (2025) — named in Codex's own novelty review, absent from the bib (`bib=0, md=0`). **No omitted method is decisive; do not delay submission.** | `CLAUDE_REJECT_FIRST_AUDIT` | 3 refs |

### Exact text — item 2 (tuning fairness)

> Tuning opportunity is not symmetric across method families. Our model family was developed over 56
> distinct hyperparameter configurations recorded across the project history, whereas the
> official-code WEARec baseline received two presets selected on a single tuning seed (validation
> NDCG@10 0.068447 vs 0.068130), and the AlphaFuse-style and upstream-class SASRec-ID arms each
> received one frozen configuration. Epoch budgets follow each method's own recipe (20 or 40 for our
> arms) rather than a common budget. All external-comparator contrasts are therefore reported as
> whole-package, unequal-budget comparisons; no equal-budget factorial has been run.

### Exact text — item 4 (three MI estimates)

> The learned-minus-identity contrast on Musical_Instruments was estimated three times under
> separate frozen protocols: +0.002265 [0.001928, 0.002602] (E-A, independent-arm Welch), +0.002116
> [0.001910, 0.002322] (active-control study, paired), and +0.001872 [0.001737, 0.002007]
> (pointwise-placebo study, paired). The estimates use different seed blocks and two different
> estimators, span 0.000393, and mutually overlap while excluding zero. They are repeated
> outcome-known internal estimates on one category, **not** independent replication.

## 2. OPEN — human-only. **These are the actual blockers.**

| gate | what is needed | blocks |
|---|---|---|
| **A0** | controlling ranking list + edition | any Tier-A framing; checklist row |
| **A1** | author order, affiliation, country, corresponding contact, running header | submission |
| **A4-legal** | dataset licence, retention, redistribution boundary, external custody | release, waiver-free deposit |
| **AI-use disclosure** | venue-compliant wording reflecting the **actual breadth** of use — a writing-assistance-only statement would be false on this record | submission |
| **Tuning-matrix authorization** | approve/decline `PREREG_TIER_A_TUNING_MATRIX_V1_DRAFT` | the only thing that closes A3 |
| **V2 temporal-isolation authorization** | approve/decline a successor to the rejected V1 | silently blocks checklist row 1 |

## 3. Verdicts that stand, and are not up for revision

- Counted boundary **unchanged**: Musical_Instruments (vs 0.0406) and Office_Products V3 (vs 0.0271
  and 0.0279). **Office V1 VOID forever.** TFV2 outcome-visible, not confirmatory.
- Numeric fidelity: **88/88** traced; **12/12** headline claims in the correct named source.
- **No cuts to §5.5/5.7/5.8 or Appendix A.0** — removing preserved deviated/VOID material while the
  positive contrasts stay is the exact asymmetry the paper claims to have eliminated.
- Two research directions **withdrawn on gates I set myself** (temporal decomposition — occupied on
  all four axes; content circularity — MARec's evaluation target is clean).
- **F1 retracted**; ML-1M module was provably active, the adjudicator gated it before I asked.

## 4. Honest assessment of this loop

Six ticks today produced eight memos. The first four did real work: two research directions killed
before they consumed a campaign, a tuning asymmetry quantified, a blocking finding of my own
retracted. **The last two found progressively less, and this one found more by auditing my own
reporting than by auditing the paper.**

That is the signal. The Claude-owned queue (guide §9 items a–f) is **worked through**: A0 blocked,
b–f delivered. Everything remaining is either a Codex decision on the seven items above — each
costing minutes — or a human gate. **Continuing hourly red-team ticks will now mostly generate
memos about memos.**

**Recommendation:** pause or lengthen this loop until either Codex rules on items 1–7 or the human
answers a gate. I am not disabling it — the kill switch is the maintainer's (`AUDIT_LOOP_STOP`), and
the human-only gates in §2 are exactly the decisions I must not make.

## Limits

FIXED statuses were verified by reading current file content, not by diffing against the pre-cycle
text, so a partial fix could read as complete. Working-tree edits are uncommitted and could change
or be reverted. My audit is advisory and creates no independent confirmation; Codex retains
recomputation and implementation authority, and the maintainer retains every submission, legal,
identity, and ranking decision.
