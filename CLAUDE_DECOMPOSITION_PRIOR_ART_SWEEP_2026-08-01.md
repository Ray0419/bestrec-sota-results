# Claude memo — decomposition question: prior-art sweep. **Caveat 1 does NOT clear.**

**STATUS: EXPLORATORY. Not preregistered. Licenses no manuscript claim.**
Date: 2026-08-01. Role: scientific red-team. Advisory only.
Supersedes the "Caveat 1 — PARTIALLY CLEARED" section of
[`CLAUDE_DECOMPOSITION_CAVEATS_2026-08-01.md`](CLAUDE_DECOMPOSITION_CAVEATS_2026-08-01.md).

```text
WORKSTREAM:        full prior-art sweep on the decomposition axis
OBJECTIVE:         the sweep that memo listed as REQUIRED before any prereg
EVIDENCE QUESTION: is the fine-grained axis (channel / position / user-adaptive /
                   spectral parameterization, and learned-vs-fixed necessity) occupied?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   per-axis occupancy verdict + a decision on the question
STOP CONDITION:    memo committed and pushed
```

Method: 6 searches + 4 full-record reads across the three fronts the previous memo named —
arXiv listings, 2025–26 proceedings, and the BSARec / FMLP-Rec / ConvFormer neighbourhood.

---

## Result: every one of the four axes is already occupied by a published method.

| axis | occupying work | venue | what it does |
|---|---|---|---|
| **position-specific** | **TV-Rec** (arXiv:2510.25259) | **NeurIPS 2025** | time-variant filters capturing *position-dependent* temporal variation; explicitly replaces **fixed kernels** and self-attention |
| **user-adaptive** | **MUFFIN** (arXiv:2508.13670) | **CIKM 2025** | user-adaptive filter generating a **personalized** frequency filter per user, vs. one filter for all |
| **spectral** | FMLP-Rec (WWW 2022), BSARec (AAAI 2024), wavelet AFF (arXiv:2511.07028) | published | learnable frequency-domain filters |
| **channel-specific** | depthwise-Conv1D report (arXiv:2607.18413) | arXiv, Jul 2026 | per-channel conv as lightweight local inductive bias; 17 insertion points ablated |

I did not merely fail to refute occupancy — I **found** it, on each axis, in a single sweep.

## Worse: the *necessity framing itself* is occupied.

**"A Systematic Reproducibility Study of BSARec for Sequential Recommendation"**
(arXiv:2512.17442, Dec 2025) states verbatim in its abstract:

> "the overall effectiveness of BSARec and the roles of its individual components have yet to be
> systematically validated"

— which is our motivating sentence — and concludes:

> "DSP methods provide no clear advantage over simple residual connections"

That is a **published negative necessity result on the spectral axis**, reached before we asked
the question. Our decomposition would be re-asking, on a different backbone, something already
answered in the direction we would likely find.

## Verdict: **the decomposition question is NOT novel. I am withdrawing my recommendation.**

The previous memo called it "the strongest research direction available." That judgment rested on
caveat 1 being partially clear. It is not clear; it is **closed**. Withdrawn.

What remains genuinely unoccupied is narrow and honest: **no single study compares all four
parameterizations plus identity under one matched harness** (shared init hash, equal budget, equal
evaluator, equal candidate set). That is a real gap, but it is a **reproducibility/measurement**
contribution — the same class as arXiv:2512.17442, which is an **unvenued preprint eight months
after posting**. That is the most informative fact in this sweep: it is direct evidence of the
venue ceiling for this contribution class. It is not a Tier-A paper.

## A finding that lands on the CURRENT manuscript, not the future one

arXiv:2607.18413 ablated initialization for depthwise conv added to a Transformer and reports:

> "Random initialization of both weights and biases gives the lowest reported loss and perplexity.
> The bias-free, zero-weight setting performs substantially worse."

Mean loss 2.4795 (random) vs **3.0065** (zero-weight); perplexity 12.79 vs **61.52**.

Our canonical FIR module uses **Δ=0 identity initialization**. This is external published evidence
pointing the other way on a design choice we made. Mitigating differences are real — different
domain (language modeling, Qwen3), different placement (they favour QKV-projection insertion), and
their zero-weight arm is *bias-free zero* rather than an exact-identity residual — but a reviewer
who finds this will ask, and our answer must be measured rather than argued. Two responses are
available and neither is expensive:

1. **Disclose it.** Cite arXiv:2607.18413, state the domain/placement difference, and note that
   our zero-init is exact-identity-plus-residual, not a zeroed layer.
2. **Measure it.** A random-init FIR arm on Musical_Instruments, matched seeds and budget, is a
   small run and would settle it directly. This is a **Codex-owned** decision and requires a new
   frozen prereg if any resulting number is to be countable.

I rate this a **moderate** reviewer risk, not a threat to the claim boundary: our counted
comparisons are against published baselines, not against alternative FIR initializations.

## Standing recommendation — unchanged, and now with one fewer alternative

Fill the byline, fix cover-letter P1/P2, and submit the FIR manuscript to a reproducibility-fit
venue. The decomposition question was the strongest reason to delay; it no longer is.

Caveat 3 (sequencing) is now moot for this direction — there is nothing to sequence against.

## Limits

Six searches and four full-record reads are a sweep, not an exhaustive review; absence of a hit
still is not evidence of absence, though in this case the sweep produced **presence**, which is the
stronger direction of evidence. Two records (MUFFIN, MARS) returned truncated abstracts, so their
internal ablations are characterized from partial text — the occupancy verdict for the
user-adaptive axis rests on MUFFIN's stated mechanism, which was legible. I did not verify
TV-Rec's NeurIPS 2025 acceptance beyond the conference listing. Nothing here licenses a manuscript
claim; it licenses one decision — **not to preregister the decomposition question.**

Sources: [arXiv:2512.17442](https://arxiv.org/abs/2512.17442) ·
[TV-Rec, arXiv:2510.25259](https://arxiv.org/abs/2510.25259) ·
[MUFFIN, arXiv:2508.13670](https://arxiv.org/abs/2508.13670) ·
[arXiv:2607.18413](https://arxiv.org/html/2607.18413) ·
[wavelet AFF, arXiv:2511.07028](https://arxiv.org/pdf/2511.07028) ·
[MARS, arXiv:2606.03718](https://arxiv.org/abs/2606.03718) ·
[FMLP-Rec, WWW 2022](https://dl.acm.org/doi/10.1145/3485447.3512111) ·
[ConvFormer, arXiv:2308.02925](https://arxiv.org/pdf/2308.02925)
