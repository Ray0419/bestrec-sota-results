# Claude (e) audit — reviewer attacks and numeric claim fidelity

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-01. Reviewed commit `4a0eb5e5` (working tree dirty; manuscript/cover letter carry
uncommitted Codex edits, audited as-is).

```text
WORKSTREAM:        queue item (e) — reviewer-style attacks + evidence-class consistency
OBJECTIVE:         trace every asserted number to its committed adjudication; then attack
EVIDENCE QUESTION: does any claim surface assert a number the artifacts do not support,
                   and does any surface invite a reviewer misreading?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist
EXPECTED OUTPUT:   fidelity result + named reviewer attacks + proposed fixes
STOP CONDITION:    memo committed and pushed
```

An earlier memo of mine claimed "5/5 every numeric claim" and the 2026-07-31 22:11 audit found that
false **as completeness** — a sixth claim existed. So this pass enumerates exhaustively and reports
its own weaknesses.

---

## 1. Numeric fidelity — **clean, with the strength of the test stated**

**Coarse pass.** Every distinct value quoted to ≥4 decimal places across the three claim surfaces
was matched against the pooled numeric contents of all 15 committed `*adjudication*.json` files
(1,403 distinct values):

| surface | distinct ≥4dp claims | traced |
|---|---:|---:|
| abstract | 18 | **18/18** |
| conclusion (§7) | 58 | **58/58** |
| cover letter | 12 | **12/12** |
| **total** | **88** | **88/88** |

**Why the coarse pass is not sufficient, stated plainly.** Pool matching only proves a number
appears *somewhere*. Its discriminating power collapses for small values: `+0.000000` matches 13 of
15 files and `−0.000074` matches 8, because rounding to 4–6 dp makes many distinct raw values
collide. **The near-zero values are exactly where the paper's null and negative results live, so
the coarse test is weakest precisely where it would matter most.** That is a limitation of my
check, not a defect in the paper.

**Strong pass — each headline claim against its *named* source.** Twelve headline claims were
re-verified inside the specific adjudication artifact the manuscript attributes them to, recording
the exact JSON path:

| claim | named source | path | result |
|---|---|---|---|
| MI learned−identity +0.002265 | `fir_v3` | `/contrasts[0]/est` | ✅ |
| MI CI [0.001928, 0.002602] | `fir_v3` | `/contrasts[0]/ci[0]`, `ci[1]` | ✅ |
| learned−pointwise +0.001941 | `fir_pointwise_v1` | `/contrasts/learned-pointwise/mean` | ✅ |
| learned−shared −0.000081 | `fir_controls` | `/family_b/learned-shared/mean` | ✅ |
| ML-1M learned−pointwise +0.000035 | `fir_efficiency_ml1m_v1` | `/replication/learned-pointwise/mean` | ✅ |
| AlphaFuse V4 +0.005207 | `ee_v4` | `/contrasts/v3_alphafuse_zero_minus_v4_…` | ✅ |
| IS breadth +0.002110 | `fir_canonical_breadth` | `/per_category/Industrial_and_Scientific/…` | ✅ |
| CDs breadth +0.006150 | `fir_canonical_breadth` | `/per_category/CDs_and_Vinyl/paired_mean` | ✅ |
| Software V3 +0.005062 | `fir_prospective_sw_v3` | `/primary_contrast/mean` | ✅ |
| WEARec mean 0.059184 | `wearec_baseline_v1` | `/wearec_ndcg10/mean` | ✅ |

**12/12 present in the correct named source. No claim surface asserts a number the artifacts do not
support.**

**One caveat against my own harness.** The ML-1M learned−identity claim (`+0.000000`) matched
`/filter_trainable_parameters/identity` — a *parameter count* of 0, not the effect estimate. A
coincidental hit. The semantically correct value does exist at
`/replication/learned-identity/mean = 2.0248e-07`, verified separately in yesterday's A4 pass, so
the claim is sound — but **11 of 12 matched a semantically correct path, not 12 of 12**, and I am
recording that distinction rather than reporting a clean sweep.

**A second self-caveat.** My first harness run returned `0/0` for the abstract and conclusion — a
missing `re.MULTILINE` meant the section extractor silently matched nothing. A `0/0` reads as a
pass. Had I reported it, I would have certified two surfaces I had not examined. Fixed and rerun
before any conclusion was drawn.

## 2. Reviewer attack — **the three Musical_Instruments values**

This is the finding worth acting on. A reviewer reading §5.2 sequentially encounters three
different values for what looks like one quantity — *learned FIR minus identity on
Musical_Instruments*:

| value | study | estimator | seed block |
|---|---|---|---|
| **+0.002265** [0.001928, 0.002602] | `PREREG_FIR_V3` (E-A) | independent-arm **Welch**, df 13.939 | V3 blocks |
| **+0.002116** [0.001910, 0.002322] | `PREREG_FIR_CONTROLS` | ordinary **paired** | 20260901–08 |
| **+0.001872** [0.001737, 0.002007] | `PREREG_FIR_POINTWISE_V1` | ordinary **paired** | 20261001–08 |

The abstract and §7 quote only **+0.002265**, the largest of the three.

**This is not concealment.** Each paragraph names its own protocol, estimator, seeds and evidence
class, and the difference is fully explained by different seed blocks and two different estimators.
I checked, and the manuscript is internally accurate everywhere.

**But no single passage juxtaposes them,** so the reviewer must reconstruct the explanation
themselves — and a reviewer who does not will read "which number is the effect, and why does the
abstract use the biggest one?" That question is hostile to the paper and easy to defuse.

**The defusal is favourable to the paper, which is why leaving it implicit is a wasted asset.**
Three separate seed blocks under two different estimators produce estimates spanning
**+0.001872 to +0.002265** — a spread of **0.000393** — and **all three intervals exclude zero and
mutually overlap** (pairwise overlaps: 0.001928–0.002322, 0.001910–0.002007, 0.001928–0.002007).
That is internal stability evidence the paper currently earns and does not state.

**Proposed sentence (Codex-owned; I edited nothing):**

> The learned-minus-identity contrast on Musical_Instruments was estimated three times under
> separate frozen protocols: +0.002265 [0.001928, 0.002602] (E-A, independent-arm Welch),
> +0.002116 [0.001910, 0.002322] (active-control study, paired), and +0.001872 [0.001737, 0.002007]
> (pointwise-placebo study, paired). The estimates use different seed blocks and two different
> estimators, span 0.000393, and mutually overlap while excluding zero. They are repeated
> outcome-known internal estimates on one category, **not** independent replication.

**Label discipline:** these are same-investigator, same-category, same-code-lineage repetitions.
They must not be called replication, confirmation, or independent, and the proposed wording says so
explicitly. The abstract's use of +0.002265 is defensible because it is the E-A registered primary,
but the abstract should not be the only place a reader meets the number.

## 3. Attacks that did **not** land

- *"A CI crossing zero is treated as equivalence."* — Checked again across all six shared-filter
  mentions. It is not; every one carries "not equivalence."
- *"The abstract hides the negative."* — It does not: the MovieLens null appears in the abstract,
  contributions, §5, §6, §7 and the cover letter.
- *"Numbers drift between markdown and TeX."* — Out of my lane (Codex owns parity) and the
  generated-table provenance already gates it; I found no counterexample in the surfaces I read.

## 4. Disposition

No claim requires retraction, narrowing, or reclassification. The counted boundary is unchanged and
I propose no widening. One presentational fix is recommended (§2), costing one sentence and no new
runs. Checklist rows: nothing moves on this audit — *Outcome-independent reporting* was already
proposed PASS two ticks ago and this pass independently supports that, without changing it.

## Limits

Fidelity was checked on the abstract, §7 and the cover letter — the three surfaces a reviewer and
editor read first — not on every number in §5. Pool matching is weak for near-zero values, as
stated. I read committed adjudication artifacts only; no sealed endpoint was inspected, and Codex
retains recomputation authority. Advisory only; no artifact modified.
