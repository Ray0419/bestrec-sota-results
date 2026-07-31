# Claude response — audit 2026-07-31 22:11

Role: scientific red-team. **Verdict accepted in full. No finding disputed.** Several errors
are mine; I have bannered my own memos rather than defend them. Advisory only.

```text
WORKSTREAM:        respond to the 22:11 audit of my own six commits
OBJECTIVE:         accept, correct the record, stop the incorrect claims propagating
FILES I MAY EDIT:  my own CLAUDE_* memos, the patch register, HANDOFF_CODEX.md, this response
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md (user-owned), manuscript, TeX, cover letter,
                   preregs, adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   point-by-point acceptance + banners applied + register corrected
STOP CONDITION:    committed and pushed
```

## Point-by-point

| # | Audit finding | My response |
|---|---|---|
| 1 | **F3/F4 used the wrong MovieLens population.** Primary cohort is **1,033 retained users**, not the 6,040 source population; budget is **100 updates**, not ~472; ratios are **45x/40x/96.8x** | **Accepted.** Banners applied to F3 and F4. |
| 2 | **F4 claimed it read `n_users` from committed result JSONs; the JSONs contradict it** | **Accepted — the error I most regret.** No ML-1M result JSON exists in the repo; I used the prereg's dataset-level figure and then described it as read from run metadata. That is a misstatement of my own method, and exactly the provenance slippage I audit others for. |
| 3 | **F3's wall-clock corroboration is invalid** (~10 min is the manuscript's Video_Games statement, not matched MI timing; MI history records ~117 s for one learned seed) | **Accepted.** Bannered. |
| 4 | **F5 does not execute the test F4 specified** — prefixes are 4.0–4.84x the real budget, no Amazon boundary exists near 100 updates, an early prefix of a long cosine schedule is not equivalent LR exposure to a completed 5+95-step schedule, and validation curves do not replace the promised fresh TEST contrast | **Accepted in full.** F5 downgraded to an exploratory Amazon learning-curve observation. **My "refutation" of F3/F4 is withdrawn — and so is my consequent restoration of P5's bound wording.** The optimizer-budget question is **unresolved, not refuted.** |
| 5 | **F5 arithmetic error:** CDs gap peaks at **epoch 5 (+0.0114316)**, not epoch 3 | **Accepted.** I scanned only epochs 1, 2, 3 and 20 and asserted a peak from four points. Bannered. |
| 6 | **F1 mis-specified the diagnostic.** MovieLens uses `fir_control=learned`, `fir_v3=off`, so `fir_v3_final_l2` is null by construction; correct `fir_control_final_l2` is **nonzero (0.192596–0.216180)** on all eight learned runs | **Accepted.** I asked for the wrong field. |
| 7 | **Equal aggregate NDCG does not imply identical rankings.** On the three equal-NDCG seeds, **125/115/109 of 1,033** target ranks change (by ≤3) — top-k cutoff granularity | **Accepted.** My "not one user's top-10 changed" inference was wrong; I conflated an aggregate with a ranking. F1's inactive-module branch is refuted by these diagnostics — not by F5. |
| 8 | **F6's "5/5 every numeric claim" is false as completeness** — a sixth claim exists (AlphaFuse +0.005207), independently checked exact | **Accepted.** No mismatch exists, but my count and completeness statement were wrong. Bannered. |
| 9 | **"Both surfaces numerically faithful" contradicts my own E5** | **Accepted.** Correct status: *checked empirical effect estimates are exact; whole-document numeric fidelity FAILS until derived counts are regenerated.* Bannered. |
| 10 | **F6's interpretation overclaims:** no shared-vs-learned margin was preregistered, so a CI crossing zero establishes neither "no detectable loss" nor that shared "attained" learned's effect | **Accepted, and this one stings** — it is precisely the rule I have enforced on others. I applied a standard to the paper and then broke it myself. |
| 11 | **The 64x ratio is filter-only.** Whole-model trainable parameters are 1,743,246 vs 1,744,254 = **0.0578%**, with no measured latency/memory/energy gain | **Accepted.** Presenting a filter-only ratio as parameter efficiency was misleading. |
| 12 | **Fixed MA/HP are not zero-parameter** — each carries a learned scalar alpha | **Accepted.** My table's "0 params" was wrong. |
| 13 | **The nonlinear non-detection is already reported** in Results, Discussion, Conclusion, TeX and cover letter | **Accepted; my selective-reporting implication is withdrawn.** Omitting one control from a compact abstract is not selective reporting, and I should have checked the other surfaces before implying it. |
| 14 | **The patch register must not be applied mechanically**; P4 rejected as written, P3/P5/P6/P7 narrowed, P8 not applied | **Accepted.** Register bannered with the per-item disposition. |
| 15 | **P4 asserted a falsehood** — MovieLens is global-time, so "we evaluate throughout with LLOO" is false, and the commensurability claim contradicts the manuscript's own caveats | **Accepted, and the most serious of my errors:** I proposed manuscript text that would have inserted a false statement into the paper, inside a memo about protocol honesty. |
| 16 | **Governance gap:** the six new memos plus `HANDOFF_CODEX.md` are absent from every manifest/deposit list; only 1 of 16 root `CLAUDE*`/Handoff records is governed, though the guide makes Handoff source-of-truth #2 | **Accepted — Codex-owned.** Flagged as a real scope defect; I should not have assumed my own outputs were governed by default. |

## What survives, stated without inflation

The audit confirms the checked effect estimates and intervals are exact and the F6 control
values accurate. And F3's *original concern* — that optimizer exposure is a large unresolved
cross-corpus asymmetry — **stands, and is larger than I calculated** (45x–96.8x, not
9.5x–20.5x). That asymmetry means the MovieLens result cannot be labelled a pure
corpus/domain/temporal-structure effect. The null itself remains valid **under its frozen
20-epoch / 100-update / fixed-split transferred protocol**.

So the net scientific position is *not* "Claude was wrong and the paper is fine." It is: my
arithmetic and my refutation were wrong, and the underlying asymmetry I stumbled onto is worse
than I said — which makes a frozen duration/convergence sensitivity **more** necessary, not
less.

## The resolution path the audit specifies (endorsed, Codex-owned)

Preregister fresh matched-initialization duration/convergence sensitivities **before** reading
new TEST endpoints. Report passes over users *and* exact updates, valid positions/tokens,
integrated LR, tap norm, score deltas, target-rank/top-10 disagreement, HR/MRR/NDCG, and
overfitting. Extend MovieLens over multiple update budgets; if an Amazon down-budget arm is
used, define exact deterministic 100-update exposure rather than pretending a different
fraction of a much larger population is identical. One multiplicity family. Retain the original
null whatever happens.

## Process lesson recorded against myself

Across six commits I escalated an alarm on arithmetic I had not sourced correctly, then
"refuted" it with a test that did not match the budget it claimed to match, then reported a
fidelity PASS that was not exhaustive and an interpretation that broke my own equivalence rule.
**Volume on unchanged state degraded my accuracy.** The corrective is the discipline I
committed to last tick and did not hold firmly enough: on unchanged state, verify and stop.
When I do produce, source every number to an artifact I actually opened, and check the other
claim surfaces before alleging an omission.

## Limits

I edited only my own memos, the patch register, this response, and the handoff. The user-owned
audit was not touched. No sealed endpoint opened, nothing executed, and no manuscript, TeX,
cover letter, prereg, adjudicator, table, graph or manifest file modified.
