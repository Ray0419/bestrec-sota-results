# Filter-parameterisation ladder — result: the 64× claim is REFUTED, an 18× version survives

**STATUS: EXPLORATORY, NOT PREREGISTERED. Licenses no manuscript claim.**
Date: 2026-08-02. Branch `claude/filter-overparam-experiments`. 80/80 runs complete.
Decision rules were declared at 0/80 in
[`CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md`](CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md) and are
applied here **as written**.

```text
WORKSTREAM:        run the filter-parameterisation ladder and report it
OBJECTIVE:         answer the RQ against pre-declared gates, pass or fail
EVIDENCE QUESTION: does FMLP-Rec's learnable filter need its per-channel parameterisation?
FILES I MAY EDIT:  this memo; experiments/**; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   verdict per pre-declared rule + mechanism reading
STOP CONDITION:    results committed and pushed
```

Harness: official BSARec suite pinned at `c80bdc0`, patch verified by exact arm parameter counts
(6656 / 360 / 104 / 0). 4 datasets × 4 arms × 5 seeds, CPU, `--no_cuda`.

---

## 1. Headline: **the strong claim dies on ML-1M**

The RQ asked whether a channel-tied filter with **64× fewer parameters** is noninferior *across
standard benchmarks*. It is not.

| dataset | `full − none` | validity gate | Δ = 0.10×(full−none) | `shared` − `full` | verdict |
|---|---:|---|---:|---|---|
| LastFM | +0.0056 | **VOID** (CI includes 0) | — | −0.0014 | n/a |
| Beauty | +0.0049 | pass | 0.00049 | +0.0004 (t=+0.48) | FAIL — underpowered |
| Toys_and_Games | +0.0105 | pass | 0.00105 | −0.0012 (t=−0.86) | FAIL — underpowered |
| **ML-1M** | **+0.0189** | pass | 0.00189 | **−0.0084 (t=−6.11)** | **FAIL — real loss** |

On ML-1M the 104-parameter channel-tied filter loses **−0.0084 NDCG@10**, CI
**[−0.0122, −0.0046]**, **0/5 seeds favouring it**. That interval excludes zero on the wrong side:
this is not a power problem, it is a loss. HR@10 agrees (−0.0135, t=−5.54, 0/5).

**Noninferiority is not established on any dataset** — one VOID, two underpowered, one refuted.

## 2. But an 18× reduction survives everywhere

`rank1` (separable: one frequency profile ⊗ a learned per-channel gain, **360 params**) is not
refuted on any dataset:

| dataset | `rank1` − `full` (NDCG@10) | CI | seeds+ |
|---|---:|---|---:|
| Beauty | +0.0009 | [−0.0021, +0.0039] | 3/5 |
| Toys_and_Games | −0.0002 | [−0.0034, +0.0031] | 2/5 |
| ML-1M | −0.0035 | [−0.0090, +0.0021] | 1/5 |

Every interval covers zero. **This is "no detected loss", NOT noninferiority** — the formal test
fails on power for `rank1` too (upper bounds +0.0021 / +0.0034 / +0.0090 against margins 0.00049 /
0.00105 / 0.00189). ML-1M's −0.0035 with 1/5 seeds is the weakest of the three and should not be
waved through.

## 3. The mechanism predicted exactly this — including which reduction fails

SVD of every trained `full` filter `[26, 64]`, all datasets × 5 seeds × 2 layers:

| dataset | top-1 energy | effective rank (of 26) | inter-channel \|cos\| |
|---|---|---|---|
| LastFM | 0.80 – 0.84 | 1.41 – 1.54 | 0.866 – 0.898 |
| Beauty | 0.80 – 0.87 | 1.32 – 1.56 | 0.878 – 0.904 |
| Toys_and_Games | 0.78 – 0.90 | 1.24 – 1.64 | 0.868 – 0.922 |
| **ML-1M** | **0.87 – 0.92** | **1.19 – 1.32** | **0.922 – 0.955** |

The filter is consistently **rank ≈ 1.2–1.6 of a possible 26**. FMLP-Rec's own account — the filter
converges to a low-pass shape — is confirmed structurally.

**The apparent paradox is the most informative part.** ML-1M is the *most* rank-1 of the four
(effective rank 1.19–1.32, alignment up to 0.955), yet it is exactly where channel-tying fails
hardest. That is not a contradiction, it is the resolution:

> A rank-1 filter is **one frequency shape × a per-channel gain vector**. High inter-channel cosine
> means the *shapes* agree; it says nothing about the *gains*. `rank1` keeps the learned gains;
> `shared` forces them constant. So on ML-1M the shapes are nearly identical (hence near-rank-1,
> hence `rank1` is safe) while the gains still carry signal — and because ML-1M's filter does the
> most work of any dataset (`full − none` = +0.0189, 3.9× Beauty's), discarding those gains costs
> the most.

The structural probe therefore has **predictive content**: it says which reduction is safe (drop to
rank 1) and which is not (drop the per-channel gains). That is a stronger result than either arm's
behavioural number alone.

## 4. Applying the pre-declared kill conditions honestly

> *"`shared` loses beyond the noise floor on a majority of datasets → strong claim dies."*

`shared` loses beyond noise on **1 of 3 valid datasets**, not a majority. **The literal kill
condition is not triggered** — and I decline to pretend it is. But the claim as *stated* was
noninferiority **across standard benchmarks**, and that is refuted by a single decisive failure. A
64× reduction that breaks on the densest standard benchmark is not a usable claim.

> *"Everything within seed noise → report as underpowered with the detectable effect size."*

This applies to Beauty, Toys, and to `rank1` everywhere. Paired-difference sd ≈ 0.0019 implies
roughly **20 seeds**, not 5, to resolve a margin of 10% of the filter effect.

## 5. What this does and does not license

**Licensed:** FMLP-Rec's learned frequency filter is empirically low-rank (≈1.2–1.6 of 26) across
four benchmarks and five seeds; its per-frequency × per-channel parameterisation carries far more
degrees of freedom than the learned solution uses; an 18× separable reduction shows no detected
loss on any tested benchmark.

**NOT licensed:** that a 64× channel-tied reduction is free (**refuted on ML-1M**); that `rank1` is
noninferior (**not established — the formal test fails on power everywhere**); that any of this is
equivalence (no CI crossing zero is equivalence); that the parameter saving matters practically —
6,552 parameters is ~2% of a ~324k model, with no measured speed or memory benefit.

## 6. Threats

1. **Reproduction gap, unresolved.** Our `full` on Beauty is HR@10 **0.0553** vs published FMLP-Rec
   **0.0618** — **10.5% low**. The pre-declared anchor says `full` must land "near" published values
   but **declares no numeric tolerance**, so it cannot be applied mechanically. I therefore neither
   pass nor void the campaign on this criterion, and flag that the tolerance should have been
   declared at 0/80 alongside the margin. Every conclusion above is conditional on our `full` being
   a faithful FMLP-Rec.
2. **LastFM VOID** — the filter does not clear its own floor there on NDCG@10.
3. **n=5 throughout**; the design cannot certify its own margin.
4. Single harness, single config (L=50, d=64, 2 layers), CPU only.

## 7. Correction to the RQ memo's framing

§1 of the RQ memo states *"What is solid is **equivalence**… 16 parameters buy everything 1,024
do."* The supporting rows are `shared − learned` = +0.000081, CI [−0.000175, +0.000338], **4/8
seeds**, and +0.000060, CI [−0.000055, +0.000175], **4/8**. Those intervals cross zero: that is **no
detected difference**, not equivalence, and "buy everything" states a null as a positive finding.
The ladder's own design is correct on this point — it pre-declares a margin and tests against it —
but the prose overreaches, and this result shows why it matters: the analogous 64× claim in the
published-model setting **failed** when a fourth dataset was added.
