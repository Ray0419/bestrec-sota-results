# Claude — seed-level cross-backend analysis: only ML-1M survives a backend swap

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `30b0deda`; data read from
`claude/filter-overparam-experiments` @ `df0851f0`.

```text
WORKSTREAM:        close the stated limit of my own cross-backend reconciliation
OBJECTIVE:         is the MPS-vs-CPU difference SYSTEMATIC, or seed-level noise?
EVIDENCE QUESTION: which ladder results survive a change of compute backend?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist
EXPECTED OUTPUT:   noise floor + which findings clear it
STOP CONDITION:    memo committed and pushed
```

My reconciliation memo declared a limit: *"Run A's per-run scores were not available to me as a
machine-readable file… seed-level pairing across backends was therefore not possible."* Run A's
per-run scores have now been exported (`results_ladder_runA_2026-08-01.csv`), so that limit is
closed. 80 ladder cells per run, **80 in common** by (dataset, arm, seed).

---

## 1. The backend difference is **not systematic** — it is noise

Paired per cell, MPS minus CPU on NDCG@10:

| dataset | n | mean Δ | sd | majority sign |
|---|---:|---:|---:|---:|
| Beauty | 20 | +0.00033 | 0.00198 | 12/20 |
| LastFM | 20 | +0.00003 | 0.00287 | 13/20 |
| ML-1M | 20 | +0.00012 | 0.00470 | 11/20 |
| Toys_and_Games | 20 | −0.00024 | 0.00176 | 12/20 |

Every mean is within ±0.00033 while every sd is **5×–20× larger**, and the sign splits are 11–13 of
20 — coin flips. **Neither backend is biased.** The disagreement between runs is run-to-run
variance, not an MPS artifact, which is the more useful and more uncomfortable answer.

## 2. Which conclusions survive a backend swap

`shared − full`, paired by seed, computed separately on each backend:

| dataset | backend | mean | t | seeds+ |
|---|---|---:|---:|---:|
| **ML-1M** | A/mps | **−0.01248** | **−6.08** | **0/5** |
| **ML-1M** | B/cpu | **−0.00836** | **−6.11** | **0/5** |
| Toys | A/mps | −0.00154 | −2.10 | 1/5 |
| Toys | B/cpu | −0.00124 | −0.86 | 1/5 |
| Beauty | A/mps | −0.00138 | −1.68 | 1/5 |
| Beauty | B/cpu | **+0.00040** | **+0.48** | 3/5 |
| LastFM | A/mps | **+0.00212** | **+2.60** | 4/5 |
| LastFM | B/cpu | **−0.00142** | **−0.74** | 2/5 |

- **ML-1M is invariant.** Both backends: t ≈ −6.1, **0/5 seeds**, same direction, same magnitude
  class. The 64× refutation is backend-independent.
- **Beauty flips sign.**
- **LastFM flips sign *and* crosses t = 2.60 on MPS** — a value that, reported alone, would read as
  a real effect favouring `shared`. On CPU the same contrast is −0.00142. LastFM is VOID under the
  validity gate in both runs, so nothing rests on it, but it is the sharpest available warning
  against reporting a single-backend t.
- **Toys is directionally stable** but its significance is not: t = −2.10 on MPS, −0.86 on CPU.

## 3. A reusable threshold, and it is the point of this memo

Backend-swap sd is **0.00176–0.00470** NDCG@10. Compare the effects being claimed:

| claimed effect | magnitude | vs its backend sd | survives? |
|---|---:|---:|---|
| ML-1M `shared` loss | 0.0084–0.0125 | **1.8×–2.7×** | **yes** |
| Toys `shared` loss | 0.0012–0.0015 | 0.7×–0.9× | no |
| Beauty `shared` loss | 0.0014 → +0.0004 | 0.7× | **no — inverts** |

> **In this harness at n=5, a contrast smaller than roughly 0.005 NDCG@10 is not reproducible
> across a change of compute backend.** Only ML-1M clears it.

This is a sharper statement of the underpowering already noted, and it is *measured* rather than
inferred from a variance estimate. It also gives a concrete design rule for any follow-up: either
exceed ~0.005, or run ≥2 backends, or raise seeds until the paired CI is narrower than the
backend-swap sd.

## 4. Consequence for how the ladder is reported

The per-dataset percentage framing (Beauty 24%, Toys 15%, ML-1M 59%) presents four measurements of
one quantity. **Three of the four are below the reproducibility floor** established above, and one
of those three inverts in sign. The defensible report is:

> The 64× channel-tied reduction fails decisively on ML-1M (−0.0084 to −0.0125 NDCG@10, t ≈ −6.1,
> 0/5 seeds on each of two independent compute backends). On Beauty and Toys_and_Games the contrast
> lies below this harness's demonstrated cross-backend reproducibility floor and is not interpreted.
> LastFM is VOID under the pre-declared validity gate.

That is a *stronger* claim than the percentage range, because every part of it survives replication.

## 5. On the retracted SASRec result — correct call, and it reinforces the open confound

The SASRec ML-1M replication claim was withdrawn because the FIR was applied to the encoder
**output** rather than the **embeddings** before the transformer blocks, so it measured a
configuration BEST-Rec does not use. The 27 affected runs were **archived, not deleted**, the
corrected implementation was verified before relaunch (zero-init exact no-op, max abs diff 0.0;
parameter counts 1024/16 matching `FIRCTRL`), and the process failure was recorded. That is the
right handling and I endorse it.

Its consequence matters for my previous tick: **backbone-vs-split is OPEN again.** Combined with the
283×–555× training-budget confound I documented in
[`CLAUDE_ML1M_CONFOUND_AUDIT_2026-08-02.md`](CLAUDE_ML1M_CONFOUND_AUDIT_2026-08-02.md), the ML-1M
null now has **three** live candidate explanations and **zero** eliminated ones. The relaunched
30-run ladder still needs the budget arm to separate budget from backbone; placement fidelity was
necessary but is not sufficient.

## 6. What does not change

Counted claim boundary unchanged: Musical_Instruments (vs 0.0406) and Office_Products V3 (vs 0.0271
and 0.0279); **Office V1 VOID forever**; TFV2 outcome-visible, not confirmatory. Nothing here is
preregistered, nothing reopens a sealed endpoint, and none of it licenses a manuscript claim. The
ML-1M FIR null still licenses neither equivalence nor a domain moderator.

## Limits

Two runs is a backend *pair*, not a sample of backends; the sd estimates are from 20 paired cells
per dataset and are themselves imprecise. Both runs are same-investigator and same harness commit,
so this is reproducibility across compute, **not** independent replication. The ~0.005 threshold is
specific to this harness, dataset set, and n=5, and should not be transported without re-measuring.
