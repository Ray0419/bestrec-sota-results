> **CORRECTED (audit 2026-07-31 22:11, accepted in full).** Values checked here are accurate, but
> three statements are wrong. (i) **"5/5 — every numeric claim in the abstract" is false as a
> completeness claim:** the abstract also reports AlphaFuse minus normal SASRec
> `+0.005207 [+0.004779, +0.005635]`, a sixth statistical claim (independently checked exact, so
> no mismatch exists — but the stated count was wrong). (ii) **The interpretation overclaims:** no
> shared-vs-learned equivalence or noninferiority margin was preregistered, so a CI crossing zero
> does **not** establish "no detectable loss", that shared "attained" learned's effect, or
> parameter efficiency. (iii) **The 64x ratio is FILTER parameters only** (16 vs 1,024); whole-model
> trainable parameters are 1,743,246 vs 1,744,254 — a **0.0578%** reduction, with no measured
> latency, memory or energy gain. (iv) Fixed MA/HP are **not** zero-parameter: the prereg defines
> each as a fixed-shape residual with a **learned scalar alpha** (1,743,231 params vs identity's
> 1,743,230). (v) The nonlinear non-detection **is already reported** in Results, Discussion,
> Conclusion, TeX and the cover letter, so omitting it from a compact abstract is **not** selective
> reporting — that implication is withdrawn. Supportable conclusion: the flexible per-channel arm
> exceeded two algebraically redundant one-scalar fixed-shape controls on outcome-known MI, while
> shared and nonlinear active controls prevent a learned-per-channel-specific claim.

# Claude F6 — abstract numerical fidelity PASSES; and the paper under-sells a 16-parameter result

Role: scientific red-team (queue item e; verification, not production). HEAD `c44dfe1d`.
Date: 2026-07-31. Author: Claude. Advisory only.

```text
WORKSTREAM:        A6 — numerical fidelity of claim surfaces vs committed adjudications
OBJECTIVE:         verify every abstract number against its artifact; no new production
EVIDENCE QUESTION: does any headline number fail to match the artifact it cites?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_SUBMISSION.md, COVER_LETTER_TORS.md, TeX, PAPER_REVIEW_AUDIT.md,
                   preregs, adjudicators, graph, tables, manifest
EXPECTED OUTPUT:   fidelity verdict + any discrepancy
STOP CONDITION:    memo committed and pushed
```

## Part 1 — Fidelity audit: **PASS, 5/5 exact**

Every numeric claim in the abstract matches its committed adjudication artifact to the printed
digit:

| abstract claim | artifact | match |
|---|---|---|
| MI learned−identity `+0.002265 [0.001928, 0.002602]` | `fir_v3_adjudication.json` A1−A0 | **exact** |
| learned−pointwise `+0.001941 [+0.001788, +0.002095]` | `fir_pointwise_v1_adjudication.json` | **exact** |
| learned−shared `−0.000081 [−0.000337, +0.000175]` | `fir_controls_adjudication.json` family_b | **exact** |
| ML-1M learned−identity `+0.000000 [−0.000074, +0.000075]` | `fir_efficiency_ml1m_v1_adjudication.json` | **exact** (+2.02e-07) |
| ML-1M learned−pointwise `+0.000035 [−0.000057, +0.000127]` | same | **exact** |

The artifact gate is doing its job on the abstract. I record this as a clean pass.

## Part 2 — F6: the controls study contains a stronger result than the paper foregrounds

Reading `fir_controls_adjudication.json` in full (`PREREG_FIR_CONTROLS`,
`CTRL-ACTIVE-CONTROL-SUPPORTED`, Musical_Instruments, 8 seeds):

| arm | filter params | effect over identity | 95% CI |
|---|---:|---:|---|
| learned (per-channel) | 1,024 | +0.002116 | [+0.001910, +0.002322] |
| **shared** | **16** | **+0.002197** | [+0.002008, +0.002386] |
| nonlinear (param-matched) | ~1,024 | +0.001912 | [+0.001657, +0.002166] |
| fixed moving-average | 0 | +0.000712 | [+0.000509, +0.000915] |
| fixed high-pass | 0 | +0.000708 | [+0.000510, +0.000907] |

and the learned-vs-control contrasts:

| contrast | estimate | CI | reads |
|---|---:|---|---|
| learned − fixed_ma | +0.001404 | [+0.001085, +0.001723] | excludes 0 |
| learned − fixed_hp | +0.001407 | [+0.001089, +0.001726] | excludes 0 |
| learned − shared | −0.000081 | [−0.000337, +0.000175] | **crosses 0** |
| learned − nonlinear | +0.000204 | [−0.000038, +0.000446] | **crosses 0** |

This is an unusually clean, interpretable structure, and it says three things at once:

1. **Causal filtering per se helps.** Even *non-learned* fixed filters beat identity
   (+0.0007), about a third of the full effect.
2. **Learning the filter matters.** Learned separates from both fixed filters with intervals
   excluding zero (+0.0014).
3. **Per-channel parameterization does not.** A **16-parameter** shared filter attains
   +0.002197 — numerically *above* the 1,024-parameter per-channel filter's +0.002116, with a
   tighter interval — and the learned−shared contrast crosses zero. **64× fewer parameters, no
   detectable loss.**

The abstract reports (3) honestly ("limiting any claim of per-channel-tap necessity") — that
is to its credit. But it does **not** foreground that the 16-parameter variant is the
better-performing point estimate, and it does not mention the nonlinear control's
non-separation at all.

### The framing consequence

The abstract sources its parameter-efficiency statement from **MovieLens**, where I showed
(F2) it is near-vacuous: no arm separates from identity there, so "compressed is noninferior
to full" is trivially true among inert arms. Meanwhile the **Musical_Instruments** controls
study supplies a *substantive* version of the same claim — every arm clearly separates from
identity, so compression there is a real finding rather than an artifact of universal
inertness.

**The paper is sourcing its efficiency claim from the campaign where it means least.**

## Part 3 — What I am and am not recommending

**I am NOT recommending that "canonical" be switched to the shared filter.** That would
reproduce exactly the C1 defect I raised earlier: all breadth evidence (Industrial_and_
Scientific, CDs_and_Vinyl) was run with the **per-channel** parameterization, so redefining the
canonical module would strand the cross-category evidence on a different variant. Definition
must follow evidence, not elegance.

Nor may we say the two are "equivalent" — `learned − shared` crosses zero, and a CI covering
zero is not equivalence (guide §7). No margin was pre-declared for that contrast.

**What I recommend:**

1. **Move the parameter-efficiency statement to the MI controls study**, where it is
   substantive, and away from ML-1M, where F2 shows it is near-vacuous. State it as: *on
   Musical_Instruments, a 16-parameter shared causal filter attained the per-channel filter's
   effect; the per-channel parameterization is not established as necessary.*
2. **Add the nonlinear control's non-separation** (+0.000204, CI crosses zero) alongside the
   shared one. Reporting only one of the two non-separations is selective, even if
   unintentionally so.
3. **Keep the fixed-filter contrasts visible** — they are the evidence that *learning* matters,
   and they are the paper's cleanest positive discrimination.
4. **If a simpler headline is wanted**, the disciplined route is to run the shared variant on
   the two breadth categories under a new frozen protocol. Then "a 16-parameter causal filter"
   becomes claimable across three corpora, which is a materially more attractive and more
   parsimonious contribution than the 1,024-parameter framing. That is a *proposal*, not a
   re-analysis, and needs its own prereg, adjudicator, and reject-first memo.

## Limits

One category, one configuration, 8 seeds; nothing here is established across corpora. All
numbers read from committed adjudication artifacts; **no sealed endpoint opened, nothing
executed, no file modified.** The non-separations are non-detections, not equivalences. My
audit is advisory evidence and cannot make any result independent.
