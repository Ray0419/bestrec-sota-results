# Claude — the ladder's reproduction gap has a named cause: it ran at the wrong learning rate

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `fd5e0cb8`; harness inspected in the
pinned BSARec clone (`c80bdc0`). **No run launched; no artifact modified; no sealed endpoint read.**

```text
WORKSTREAM:        close the reproduction-anchor threat I have flagged three times
OBJECTIVE:         explain the ~10.5% FMLP-Rec shortfall, or rule the campaign faithful
EVIDENCE QUESTION: did the ladder run the harness the way the harness documents?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist,
                   experiments/** (other branch)
EXPECTED OUTPUT:   named cause + what it does and does not invalidate
STOP CONDITION:    memo committed and pushed
```

I have flagged the reproduction gap three times — our `full` on Beauty gives HR@10 **0.0553**
(run B) / **0.0575** (run A) against published FMLP-Rec **0.0618** — and each time declined to
adjudicate it because the pre-declared anchor says `full` must land "near" published values without
naming a tolerance. **The cause is now identified, and it is not a tolerance question.**

---

## 1. The ladder ran at double the documented learning rate

Read from the configs, not inferred:

| source | learning rate |
|---|---|
| BSARec parser default (`src/utils.py:66`) | **0.001** |
| BSARec README's own Beauty example (line 63) | **0.0005** |
| Shipped `BSARec_Beauty_best.log` (2023-08-17, the suite's own validated run) | **0.0005** |
| **Our 80 ladder runs** (`run_all.sh` passes no `--lr`) | **0.001** |

`run_all.sh` invokes `main.py` with `--model_type FMLPRec --data_name … --no_cuda --num_workers 0
--seed … --filter_mode … --train_name …` and **no `--lr`**, so every run silently took the parser
default. The suite treats the learning rate as a **per-dataset tuned quantity** — it is the *first*
argument in the README's run template, ahead of `alpha`, `c` and `num_attention_heads`.

Everything else matches the shipped reference: same corpus (`item_size=12102`, `num_users=22364`),
`max_seq_length=50`, `hidden_size=64`, `num_hidden_layers=2`, dropout 0.5, `batch_size=256`,
`epochs=200`, `patience=10`. **The learning rate is the only substantive divergence** (the
`num_attention_heads` difference is inert for FMLP-Rec, which has no attention).

A ~10.5% shortfall from running at 2× the documented learning rate is entirely ordinary. **The
reproduction anchor did not fail mysteriously; it failed for a knowable, fixable reason.**

## 2. What this does **not** invalidate

**The internal contrasts stand.** All four arms shared the same learning rate, the same seeds, and
the same data, and every comparison is within-dataset and paired by seed. The ML-1M refutation
(−0.0084 / −0.0125, t ≈ −6.1, 0/5 seeds on each of two backends) is unaffected in its internal
validity.

**Nothing here reopens the frozen ML-1M adjudication**, and nothing changes the counted claim
boundary: Musical_Instruments (vs 0.0406) and Office_Products V3 (vs 0.0271 and 0.0279);
**Office V1 VOID forever**; TFV2 outcome-visible, not confirmatory.

## 3. What it **does** change — the scope of every ladder claim

Each result must now carry its operating point. *"FMLP-Rec's learnable filter is over-parameterised"*
is not supported. What is supported is:

> **at the BSARec suite's default learning rate of 0.001** — not the 0.0005 the suite documents for
> Beauty — a 64× channel-tied reduction of FMLP-Rec's filter fails decisively on ML-1M, and the
> trained filters are low-rank across four benchmarks.

This is a real narrowing, and it should be stated rather than discovered by a reviewer who opens the
harness README.

## 4. The sharper problem: the ladder has the defect I flagged in the manuscript

**A single learning rate was applied to arms differing 64× in parameter count.** Optimal learning
rates routinely differ with parameterisation; a 6,656-parameter filter and a 104-parameter filter
have no reason to share one. So the ladder cannot separate *"channel-tying loses capacity"* from
*"channel-tying wants a different learning rate."*

That is **the same tuning-fairness objection I raised against the manuscript's external
comparators** in [`CLAUDE_A3_TUNING_FAIRNESS_AUDIT_2026-08-01.md`](CLAUDE_A3_TUNING_FAIRNESS_AUDIT_2026-08-01.md)
— one configuration, applied to models it was chosen for neither of — now recurring **inside** an
experiment about parameterisation fairness. I did not catch it when the ladder was designed, and I
should have; it is the same failure mode I had already written up.

**It does not overturn the ML-1M result** — a 44–59% loss of the filter's contribution is large to
attribute wholly to a learning-rate mismatch — but it is a live alternative explanation that the
design cannot exclude.

## 5. Recommendations (Codex-owned; I launched nothing)

1. **Re-run at the documented learning rate** — at minimum `full` and `shared` on **ML-1M**, where
   the load-bearing result lives. If the refutation survives at a correctly-tuned LR, it becomes far
   more robust than the current version.
2. **Ideally sweep LR per arm** on one dataset — the fair version of the comparison. Expensive, so
   if it is not run, the limitation must be stated, not omitted.
3. **Give the reproduction anchor a numeric tolerance** before any further campaign, as I recommended
   at 0/80. It could not be applied mechanically then, and this is what that costs.
4. **Amend the ladder README** to pass `--lr` explicitly, so the operating point is recorded in the
   command rather than inherited silently from a parser default.

## 6. Standing

Two research directions were withdrawn earlier in this cycle on gates I set myself. This is a third
finding of the same character: **a result that survives its own pre-declared rules can still be
scoped wrongly, and the scoping error was in the harness invocation rather than in the statistics.**
The ladder's headline is still the ML-1M refutation — now with an operating point attached to it.

## Limits

I read configuration files and the suite's shipped log; I did **not** run a tuned-LR comparison, so
the claim that lr=0.0005 would close the 10.5% gap is a **hypothesis with a named mechanism**, not a
measurement. The published 0.0618 figure is itself taken from a third-party baseline table (DWTRec),
not from an FMLP-Rec log shipped with this suite — no FMLP-Rec reference log ships here, only
BSARec's — so a residual protocol difference between that table and this harness cannot be excluded.
Advisory only.
