# Claude memo — the decomposition question: two caveats cleared, one open

> **SUPERSEDED IN PART, SAME DAY.** The full prior-art sweep this memo demanded was run and
> **refutes** its Caveat-1 verdict: all four axes are occupied by prior work (TV-Rec,
> NeurIPS 2025; MUFFIN, CIKM 2025; FMLP-Rec/BSARec; a public depthwise-conv preprint), and the necessity
> framing itself is occupied by arXiv:2512.17442. **Caveat 1 is CLOSED, not partially cleared.**
> The "strongest research direction available" judgment below is **WITHDRAWN**. The Caveat-2
> convergence measurement stands unchanged. See
> [`CLAUDE_DECOMPOSITION_PRIOR_ART_SWEEP_2026-08-01.md`](CLAUDE_DECOMPOSITION_PRIOR_ART_SWEEP_2026-08-01.md).

**STATUS: EXPLORATORY. Not preregistered. Licenses no manuscript claim.**
Date: 2026-08-01. Role: scientific red-team. Advisory only.

Context: the maintainer proposed a research question —

> *Under a fixed strong backbone, evaluator, initialization, optimization exposure and candidate
> set, do ranking gains come from access to ordered causal lags itself, or from channel-specific,
> position-specific, user-adaptive, or spectral parameterization?*

I raised three caveats. Two have now moved materially. This records both, including a
correction to my own framing.

```text
WORKSTREAM:        assess the decomposition question before any prereg
OBJECTIVE:         test the two caveats I raised against it
EVIDENCE QUESTION: is a within-corpus necessity claim optimisation-confounded, and is the
                   question's fine-grained axis occupied?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   status of each caveat + what remains required
STOP CONDITION:    memo committed and pushed
```

---

## Caveat 2 — optimizer exposure. **SUBSTANTIALLY CLEARED. I overstated it.**

**Correction 1 — I applied a confound from the wrong comparison.** The 45x–96.8x asymmetry is
*cross-corpus* (ML-1M's ~100 optimizer updates vs Amazon's 4,000–9,680). The decomposition
question compares arms **within one corpus at one budget**, where equal optimizer exposure holds
**by construction**. That objection does not apply as stated.

**Correction 2 — the real residual risk is differential convergence, and it is now measured.**
Under a fixed 20-epoch budget, do parameterizations converge at different rates? If some arms
were still improving at the edge while others plateaued, a necessity claim would be
optimisation-confounded rather than architectural.

Read from the committed `FIRCTRL` campaign (Musical_Instruments, 6 arms x 8 seeds, validation
only — using test curves here would be metric-mining):

| arm | best epoch | best | final | final/best | gain last 5 ep | seeds still rising |
|---|---:|---:|---:|---:|---:|---:|
| identity | 19 | 0.04379 | 0.04378 | 0.9999 | +0.00009 | 1/8 |
| fixed_ma | 19 | 0.04432 | 0.04430 | 0.9996 | +0.00009 | 1/8 |
| fixed_hp | 19 | 0.04431 | 0.04430 | 0.9996 | +0.00009 | 1/8 |
| nonlinear | 18 | 0.04581 | 0.04579 | 0.9995 | +0.00007 | 1/8 |
| learned | 18 | 0.04600 | 0.04597 | 0.9995 | +0.00001 | 2/8 |
| shared | 18 | 0.04619 | 0.04617 | 0.9996 | +0.00011 | 2/8 |

**Finding.** Every arm sits at **99.95–99.99% of its own peak** at the budget edge, with
near-zero late gains and a **uniform** 1–2/8 still-rising rate. What matters for a necessity
claim is not whether arms are fully converged but whether they are **differentially** converged.
They are not. **Equal epochs ~ equal convergence here.**

**What survives is a disclosure, not a confound:** peaks land at epoch 18–19 of 20, so the budget
is adequate-but-not-generous. A prereg should either extend the budget or state this explicitly.

*(Incidental, consistent with earlier work: `shared` (16 params) has the highest validation peak
0.04619, above `learned` (1,024 params) at 0.04600.)*

## Caveat 1 — prior art. **PARTIALLY CLEARED; the framing must narrow.**

Two searches run.

- **The coarse question is taken.** Order-shuffling studies exist — one randomly shuffled
  item-level sequences and found late-fusion models degrade more than early-fusion. So *"does
  temporal order matter at all"* is answered and is **not** the question to ask.
- **The fine-grained axis was not surfaced.** No hit on decomposing gains across
  channel-specific / position-specific / user-adaptive / spectral parameterization under a
  matched harness. Nearest neighbour: **MixFormer** (arXiv:2602.14110), which addresses parameter
  *allocation* between sequence and dense features — not necessity of temporal parameterization.

**I will not call this novel on two searches.** Recorded honestly: the coarse question is
occupied; the fine decomposition is not *visibly* occupied. The defensible framing is therefore
the **narrow** one — and it is where our evidence already lives, since `learned − shared` crossing
zero is what makes the question non-trivial rather than rhetorical.

**Required before any prereg:** a full sweep — arXiv listings, SIGIR/RecSys/WWW 2025–26
proceedings, and forward-citations of BSARec / FMLP-Rec / ConvFormer, which is where such a study
would sit.

## Caveat 3 — sequencing. **OPEN. Human-only; not technical.**

Proposed concrete gate:

> The FIR manuscript is **submitted (or explicitly abandoned)** before any decomposition prereg
> is frozen.

This keeps the question alive as paper #3 without it becoming the sixth reason nothing ships.
Reversing the order is a legitimate choice — but it should be a stated decision, not drift.

## Standing of the question

With caveat 2 largely removed, this is now the **strongest research direction available**:
it reuses the FIR work rather than starting fresh (unlike paper #2's unlearning angle), four
cells of its answer table are already measured under matched initialization, and its hardest
methodological objection failed to materialise when tested.

It remains a **measurement** contribution, not a method one, and it does not change the FIR
manuscript's own claim boundary.

## Limits

Exploratory, post-hoc, not preregistered. Convergence evidence is one corpus
(Musical_Instruments), one budget, validation only. Prior-art searching is **not exhaustive** —
absence of a hit is not evidence of absence. Nothing here licenses a manuscript claim; it
licenses only the decision about whether to write a preregistration.
