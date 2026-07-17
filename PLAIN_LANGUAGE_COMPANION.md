# The Plain-Language Companion

*A non-technical guide to the paper "Pre-Registered, Artifact-Gated Evaluation for Sequential
Recommendation: Causal FIR Filtering and Dataset-Conditional Text Benefits on Amazon Reviews 2023."*

This document explains, without jargon, **what we built, how it works, why it works, and why you
can trust the numbers** — using everyday examples and analogies. It is documentation for
readers, not part of the submission; the paper (`PAPER_SUBMISSION.md` / `paper_tex/PAPER_TORS.pdf`)
is the authoritative source, and every number quoted here is copied from it verbatim. An
interactive version with figures and hands-on demos lives at `companion_site/explainer.html`.

---

## 1. The problem: guess the next thing someone will buy

Imagine a friend's shopping history on Amazon: guitar strings in January, a capo in March, a
clip-on tuner last week. **What will they buy next?** That is the whole task, called *sequential
recommendation*: given the ordered list of things a person interacted with, predict the very next
one.

Two details make our version of the game honest and hard:

- **The model must pick from the entire catalog.** Some evaluation setups are like a multiple-choice
  quiz: "here's the right answer hidden among 99 decoys — find it." Ours is an open exam: the
  model must rank **every product in the catalog** (25,612 items for Video Games; 77,551 for
  Office Products) and we check where the true next purchase landed. Open exams are much harder
  than multiple choice, and scores are much lower — which is normal and expected.
- **The last item of every person's history is hidden from training.** The model never sees the
  answers it will be graded on. (The second-to-last item is held out too, as a practice exam used
  to pick settings — so the real exam stays untouched.)

**How scoring works (NDCG@10):** think of the model's output as a search-results page. If the
true next purchase appears in the top 10, the model earns credit — more credit the higher it
appears, on a sliding scale (position 1 earns the most). A score of 1.0 would mean "always ranked
the right item #1 out of the whole catalog." On these open-exam benchmarks, good scores look
small: 0.03–0.07 is the competitive range. Differences in the third decimal place are real and
meaningful here, the way a tenth of a second is meaningful in a 100 m sprint.

## 2. How the model thinks

The model reads a shopping history the way you read a sentence — in order, with some words
mattering more than others.

- **Attention = a highlighter** (drawn as Fig. A in the interactive explainer). For each prediction, the model decides which past purchases to
  highlight. Buying a *capo* makes the earlier *guitar strings* very relevant and the two-year-old
  *phone case* irrelevant. The "attention" mechanism is just a learned highlighter: it assigns
  each past item a weight and blends the highlighted items into a guess about what comes next.
- **Recency and timing = "fresher clues count more."** A purchase from last week usually says more
  about your next purchase than one from last year. The model gets the timestamps and learns how
  quickly relevance fades — like a detective trusting fresh footprints over old ones.
- **Product descriptions = every item gets a "scent."** Each product's title and description is
  converted — once, up front, by a separate language model that is never trained further —
  into a numeric fingerprint. Similar products
  end up with similar fingerprints — two different brands of guitar tuner "smell alike" — so the
  model can reason about a product it has rarely or never seen sold. This is how it handles the
  huge tail of obscure items with only a handful of purchases each.
- Everything above is small by modern standards: **11.6 million parameters** (the model's
  internal adjustable dials) and **about 10 minutes of training per run on one consumer
  graphics card.** No giant language model does the
  recommending; the language model only supplies the frozen "scents" beforehand.

## 3. The novel component: a causal FIR filter (the "shock absorber")

Our main modeling contribution is a tiny, old-school signal-processing idea transplanted into
this modern recommender.

**The problem it fixes:** the signal flowing through the model — "what is this person into right
now?" — is noisy. One impulse buy (a gag gift, a purchase for someone else) can jerk the model's
picture of you sideways, like one pothole jolting a car.

**The fix:** an FIR filter ("finite impulse response" — the engineering term for a *fixed-length
weighted average*). Before the signal moves on, each position is replaced by a small learned blend
of itself and the last few positions before it. Three everyday versions of the same idea:

- a **shock absorber**: bumps still register, but they stop rattling the whole frame;
- a **coffee filter**: flavor through, grounds held back;
- a **moving average** on a stock chart: the wiggly daily line becomes a readable trend.

Three properties make our version safe and honest:

1. **Causal (leak-free):** the blend only ever looks *backward* in time. Like a weather
   forecaster who may use yesterday's data but never tomorrow's. This matters because a filter
   that peeks even slightly ahead would be cheating — leaking the future into the prediction —
   and inflated scores from subtle future-leakage are a known way papers fool themselves.
2. **Zero-initialized:** the filter starts switched **off** (it initially passes the signal
   through unchanged), and training only turns it up where it genuinely helps. It cannot hurt by
   default; it has to earn its influence.
3. **Tiny:** for each internal signal stream it learns just 8 or 16 blending weights — knobs
   bolted onto the existing engine, not a new engine.

**Does it help?** Yes, consistently. Adding the filter improved results on **all four categories
we tested**. On two of them the test was run under a sealed pre-registration (see §5): on
Industrial & Scientific, the filter added **+0.0024** NDCG@10 (95% confidence interval
**+0.0018 to +0.0030**), and on CDs & Vinyl **+0.0057** (**+0.0049 to +0.0064**) — in both
cases the filter won on **5 out of 5** paired random restarts, with **zero per-category tuning**
(the settings were transplanted as-is). In sprint terms: a small but repeatable shave off the lap
time, on tracks the tuning never saw.

## 4. A finding, not just a gadget: text helps some catalogs and not others

The "scent" fingerprints from product text are not uniformly useful, and one of the paper's main
points is *when* they help:

- On **small, sparse catalogs** (Musical Instruments, Office Products), text helps clearly —
  especially for **obscure items**. Analogy: in a small-town library with no borrowing records
  for most books, a librarian leans on the blurbs. Text is the blurb.
- On **large, dense catalogs** (Video Games, Beauty), text adds roughly nothing on the same
  measurements. The big-city library has so much borrowing history that the blurbs are redundant.

We went beyond correlation (drawn schematically as Fig. B in the interactive explainer): we **thinned** dense datasets on purpose (training the same model on
artificially sparsified versions while grading on the same exam) to test whether scarcity itself
flips text from useless to useful. The paper reports these as controlled experiments — we changed one
thing on purpose and watched the effect — not just observations. The practical upshot for practitioners: *whether to bother wiring product text into
your recommender depends on your catalog's density — measure it first.*

## 5. Why you can trust the numbers (the part we care about most)

Recommendation-systems research has a credibility problem: tiny improvements, many knobs,
and every incentive to report your best run. Our machinery exists to make that structurally
impossible for us. Three mechanisms:

### 5.1 Pre-registration = calling your shot

Before running an experiment that could become a claim, we write a sealed contract into version
control: the exact command, the exact settings, the random seeds (chosen fresh, **never previously
run**), the pass/fail rule, and the exact sentence we would be allowed to claim if it passes.
*Then* we run it — calling the pocket before the pool shot. If the result misses, we publish
the miss; the contract is already public, so there is no quiet way to discard it.

### 5.2 The fail-closed artifact gate = a printer that refuses to bluff

Every number printed in the paper — **168 of them** — is wired to the raw result files it came
from. At every change, a build script recomputes all 168 from those files and **refuses to build
the paper** if even one printed digit disagrees with its evidence, one number's origin can't be
traced, or one required family of evidence is missing. A separate manifest pins **153 files by digital
fingerprint (hash)**, so evidence can't quietly change after the fact. Analogy: a spreadsheet that
physically cannot display a figure it can't re-derive from receipts.

### 5.3 A rival referee audits us every hour

A *different* AI system (Codex) re-audits the whole project on a schedule — re-running the
gates, hunting contradictions, fact-checking our citations against the live web — and appends
its complaints to a public file. We must answer every
complaint in writing, and both the complaints and the answers are part of the repository. Dozens
of rounds of this adversarial ping-pong have already happened; several real defects were caught
and fixed this way. It's a chess player whose moves are checked by the opposing team's engine,
every hour, in public.

## 6. The Office Products story: the system catching *us*

This is the paper's honesty centerpiece, and the best illustration of why the machinery matters.

**Act 1 — the disallowed goal.** We pre-registered a second-category attempt on Office Products
(the first, Musical Instruments, had passed cleanly). The results looked great — comfortably
above the published comparator. But the sealed contract contained a **comparability tripwire**: a
sanity check that our simple-baseline score should roughly match the comparator paper's
simple-baseline score on the same data. Ours came in **44% higher** — the "field was tilted."
Something about our environment made *everything* score higher there, so beating the published
number proved nothing. Under the contract as written, the pass was **VOID**. We recorded the
disallowed goal, permanently. It still says VOID in the paper today, and always will.

**Act 2 — leveling the field.** Why was the floor inflated? We took the comparator's **own
published code** and ran it, unmodified, inside our environment (with careful, disclosed
compatibility shims — think adapters for a foreign plug). Their method, our field. Their code
scored **0.0279** here — noticeably above their published **0.0271** — confirming the
environment itself was generous and explaining the tilt. (These reference runs are honest but
environment-caveated single runs, and the paper labels them exactly that way.)

**Act 3 — the goal that counts.** We then wrote a **new** sealed contract (V3) with the fix built
in: the bar to clear is no longer the published number from a different environment, but the
comparator's **own code re-run on our field** (0.0279) — plus fresh, never-touched random seeds.
The result: both filter variants cleared both bars on **10 out of 10** runs — worst-case
plausible averages (95% CI lower bounds) of **0.03033** (K=16) and **0.03024** (K=8), versus the
matched reference 0.0279 and the published 0.0271. That pass **counts**, and the earlier VOID
**still stands** as its own record. The referee that disallowed our first goal is the same
machinery that makes the second one credible.

## 7. What we claim — and what we refuse to claim

**We claim:**

- On **Musical Instruments**: our fresh 5-seed averages beat the published comparator point value
  (0.0406) with 95% CI lower bounds of **0.04096** (K=16) and **0.04083** (K=8), 10/10 seeds
  above, under a sealed pre-registration.
- On **Office Products (V3)**: as told above — CI lower bounds **0.03033** / **0.03024**, above
  both 0.0279 (matched reference) and 0.0271 (published), 10/10 seeds, sealed pre-registration.
- The **causal FIR filter** helps on all four categories tested (two under sealed
  pre-registration, listed in §3), as an internal with-vs-without comparison.
- **Text benefits are dataset-conditional** (§4), supported by controlled thinning interventions.
- The **evaluation apparatus itself** (pre-registration + fail-closed gate + adversarial audit)
  is a contribution other researchers can copy.

**We deliberately do NOT claim:**

- **"State of the art"** — on anything. On Video Games our 0.0673 sits below the published 0.0760
  of the strongest comparator; we say "competitive," and the claim boundary is enforced by an
  automatic scan for forbidden phrases at every build.
- **Statistical superiority over the comparator.** Their published numbers are single runs. We
  can say our multi-seed average clears their point value; we cannot honestly say "significantly
  better," because a single run has no error bars to compare against. (Analogy: our average of
  five dice rolls beat the one roll they wrote down — that is exactly what we say, and no more.)
- Anything from the **VOID V1 campaign** (§6, Act 1), forever.
- Comparisons against concurrent 2026 preprints whose protocols we haven't audited — we cite
  them, we don't race them.

## 8. Glossary (one-liners)

| Term | Plain meaning |
|---|---|
| NDCG@10 | "How high on the first page of 10 did the right answer appear?" — partial credit by rank. |
| Full-catalog evaluation | The open exam: rank every product, no multiple-choice decoys. |
| Leave-last-one-out | Hide each person's final purchase; grade the model on predicting it. |
| Seed | The shuffle of the random deck; a different seed = an honest re-run of the same experiment. |
| 95% CI lower bound | "Even our unluckiest plausible average still clears this." |
| Pre-registration | The sealed contract written before the experiment: command, seeds, pass rule, claim sentence. |
| VOID | Our own referee disallowed the result under the sealed contract; permanently on record. |
| Fail-closed gate | The build refuses to print any number it cannot recompute from raw evidence. |
| FIR filter | A short, fixed-length weighted average — the shock absorber of §3. |
| Causal / leak-free | Only ever looks backward in time; no peeking at the future. |
| Embedding / "scent" | A numeric fingerprint of a product's text; similar products smell alike. |
| Comparator | The strongest published prior result we measure against (HSTU-BLaIR). |
| Environment-caveated regeneration | We re-ran their code on our machine; honest but single-run, so labeled with care. |

---

## Worklist (for the hourly quiet-tick program; small increments per tick)

- [x] First full draft of this companion document (2026-07-18).
- [x] First version of the interactive explainer `companion_site/explainer.html` (2026-07-18):
      hero, "be the recommender" toy demo, FIR filter slider demo, results figure, V1→V3
      timeline, claim/no-claim panel, FAQ, glossary; light+dark themes; published as an Artifact.
- [ ] Keep PAPER_WRITING_TEMPLATE.md's quoted numbers in sync with the gated paper whenever
      results change (same verbatim rule as this document).
- [x] Add a small SVG "how the model reads a history" figure (highlighter/attention visual) to
      the explainer §2 and link it from this document (2026-07-18: Fig. A, attention arcs with
      weight-as-thickness over a toy history).
- [x] Add a "thinning intervention" mini-figure (dense→thinned bars showing the text benefit
      appearing) to explainer §4 (2026-07-18: Fig. B, two-panel schematic, explicitly labeled
      illustrative — no invented numbers printed).
- [x] Read-aloud pass on this document (2026-07-18): §5 tightened; glossed parameters,
      frozen encoder, channels/kernel, hash; "intervention-scoped" replaced with plain
      language; one analogy per point.
- [ ] (standing) Cross-check every number in the companion files and PAPER_WRITING_TEMPLATE.md
      against the gated paper after each future results change (numbers must stay
      verbatim-identical). Last full check: 2026-07-18, all matched.
- [ ] Optional: add a "try different seeds" animation to the FIR demo showing run-to-run spread
      vs the CI-lower-bound idea.
