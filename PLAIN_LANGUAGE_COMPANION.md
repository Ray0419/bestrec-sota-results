# The Plain-Language Companion

*A non-technical guide to the paper "Artifact-Gated Evaluation of Text-Augmented Sequential Recommendation: An FIR-Optimizer Package and a Musical-Instruments Frequency-5 Case Study on Amazon Reviews 2023."*

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
text gives the model a head start on items it has seen only a handful of times in training. (Important honesty note: for items with ZERO training exposure the paper found text does NOT help at all — zero hits through rank 100 in every rerun category — so no cold-start ability is claimed.)
- Everything above is small by modern standards: **11.6 million parameters** (the model's
  internal adjustable dials) and **about 10 minutes of training per run on one consumer
  graphics card.** No giant language model does the
  recommending; the language model only supplies the frozen "scents" beforehand.

## 3. The FIR add-on (the "shock absorber") — one of two small additions

One of the paper's two small architectural additions (self-graded incremental) is a tiny, old-school signal-processing idea transplanted into this modern recommender. Important caveat from the paper: the measured gain is a bundled package effect — filter + starting state + optimizer path — not the filter alone (attribution is open work).

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
   through unchanged), and training only turns it up where it genuinely helps. It starts as an exact no-op; its influence is
   learned (and the measured gain is a package effect — see the paper's §3 caveat).
3. **Tiny:** for each internal signal stream it learns just 8 or 16 blending weights — knobs
   bolted onto the existing engine, not a new engine.

**Does it help?** The **package arm** (filter + starting state + optimizer path — the paper is explicit that these cannot be separated yet) showed positive estimates on **all four categories tested**. The two breadth categories were re-run as fully independent 8-vs-8 arms under a Git-committed plan whose rerun was **outcome-visible** (paper §5.3): Industrial & Scientific **+0.0021** NDCG@10 (Welch 95% CI **+0.0019 to +0.0024**) and CDs & Vinyl **+0.0058** (**+0.0053 to +0.0063**). An earlier paired reading of the original runs was **withdrawn** (the arms were never initialization-paired) — the numbers above are the repaired, independent-arm ones.

**Update (matched-twin rerun, E-A):** we later retrained the model 24 more times under a frozen, committed-in-advance plan in which the filter-equipped copy and a no-filter twin start from *byte-identical* weights (verified by checksum). The filter twin won by +0.0023 (95% CI +0.0019 to +0.0026) on Musical Instruments — the first direct evidence that the filter itself, not its starting-state side effects, carries a benefit at this configuration. (This does not re-split the older bundled numbers above.)

**Update 2 (recipe add-on, E-F):** under a second frozen, committed-in-advance plan, we blended the model's scores with a classic “customers who bought X also bought Y” matrix (EASE, Steck 2019) — fitted only on training data, blend weight chosen only on validation. On five brand-new seeds it helped every category tested: Musical Instruments 0.0415→0.0440 (the blend's five-seed average now sits above the published 0.0406 single run), Industrial & Scientific 0.0334→0.0360, Video Games 0.0671→0.0703 (still below the published 0.0760). A five-model ensemble of the blend reached 0.0456 on Musical Instruments (ensembles compare only to other ensembles).

**Update 3 (rare-item helper, E-G):** we added a third, fit-free signal — “which items *sound like* what this user already bought,” from product-text similarity — applied ONLY to items bought five-or-fewer times in training (weight picked on validation). Under a third frozen plan, five brand-new seeds per category, it raised rare-item accuracy on **all five catalogs** (deltas +0.0011 to +0.0048 on the ≤5-purchase bin; the biggest win on CDs & Vinyl) with overall accuracy essentially unchanged. Three honest footnotes: it did nothing for items with ZERO training purchases (nothing in our system retrieves those); popular items pay a small, measured price — the gain is a *redistribution* toward rare items, not free accuracy; and every run picked the largest allowed weight, so the true best weight may be larger (untested). **And one big asterisk added after an external-style audit:** on this experiment we broke one of our own rules — we looked at (and published) early results before all categories finished, and we fixed a broken checking rule after seeing most of the results. So this one counts as a *strong hint*, not a confirmed finding, and we are redoing it from scratch under stricter machinery.

## 4. A finding, not just a gadget: text helps some catalogs and not others

The "scent" fingerprints from product text are not uniformly useful, and one of the paper's main
points is *when* they help:

- On **small, sparse catalogs** (Musical Instruments, Office Products), text helps clearly —
  especially for **obscure items**. Analogy: in a small-town library with no borrowing records
  for most books, a librarian leans on the blurbs. Text is the blurb. (This picture is a **hypothesis**, not deployment advice: the cross-dataset difference was NOT statistically established — p = 0.13 — and the thinning experiment below did not reproduce it.)
- On **large, dense catalogs** (Video Games, Beauty), text adds roughly nothing on the same
  measurements. The big-city library has so much borrowing history that the blurbs are redundant.

We went beyond correlation (drawn schematically as Fig. B in the interactive explainer): we **thinned** dense datasets on purpose (training the same model on
artificially sparsified versions while grading on the same exam) to test whether scarcity itself
flips text from useless to useful. The paper reports these as bundled interventions on one fixed subset draw (many things change together when you thin) — we changed one
thing on purpose and watched the effect — not just observations. The practical upshot for practitioners: *whether to bother wiring product text into
your recommender depends on your catalog's density — measure it first.*

## 5. Why you can trust the numbers (the part we care about most)

Recommendation-systems research has a credibility problem: tiny improvements, many knobs,
and every incentive to report your best run. Our machinery exists to make that structurally
impossible for us. Three mechanisms:

### 5.1 Pre-declaration = calling your shot

For the **counted claims** we write the contract into version control first: exact command, settings, fresh seeds, pass/fail rule, and the exact sentence we may claim. *Then* we run it. Honesty note: not everything in the paper had that timing — development results are labeled post-hoc, and the biggest rerun (TFV2) was **outcome-visible** while it ran (the paper's §5.3 discloses the exact chronology). Misses are published either way — the VOID Office V1 campaign is the standing example.

### 5.2 The fail-closed artifact gate = a printer that refuses to bluff

Every one of the **175 artifact-gated table cells** is wired to the raw result files it came
from. At every change, a build script recomputes all 175 gated cells from those files (two expository tables are conventional prose) and **refuses to build
the paper** if even one printed digit disagrees with its evidence, one number's origin can't be
traced, or one required family of evidence is missing. A separate manifest pins **276 files (current count; the release manifest is authoritative) by digital
fingerprint (hash)**, so evidence can't quietly change after the fact. And since mid-July,
each counted result has its own referee wired into that same build: the Office V3 and
filter-breadth adjudicators re-run every time, and the paper refuses to build unless both
say PASS — a counted claim can never silently outlive its evidence. Analogy: a spreadsheet that
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

**Act 1 — the disallowed goal.** We pre-declared a second-category attempt on Office Products
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
  above, under a sealed pre-declaration.
- On **Office Products (V3)**: as told above — CI lower bounds **0.03033** / **0.03024**, above
  both 0.0279 (matched reference) and 0.0271 (published), 10/10 seeds, sealed pre-declaration.
- The **FIR package arm** shows positive estimates on all four categories tested (two under a
  Git-committed pre-declaration whose rerun is outcome-visible — paper §5.2/§5.3), as an internal
  with-vs-without comparison (same seed numbers; arms not initialization-paired).
- **Text tail benefit: one MI frequency-5 case** (paper §4/§5.3) — cross-dataset heterogeneity is NOT established (interaction p = 0.13) and the thinning intervention did NOT reproduce it (one fixed draw; mechanism unresolved).
  is a contribution other researchers can copy.

**We deliberately do NOT claim:**

- **"State of the art"** — on anything. On Video Games our 0.0673 sits below the published 0.0760
  of the strongest comparator; we say "competitive," and the claim boundary is enforced by an
  automatic scan for forbidden phrases at every build.
- **Statistical superiority over the comparator.** Their published numbers are single runs. We
  can say our multi-seed average clears their point value; we cannot honestly say "significantly
  better," because a single run has no error bars to compare against. (Analogy: our five-roll average beat the single roll they wrote down — that is exactly what we say, and no more.)
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
| Pre-declaration | The sealed contract written before the experiment: command, seeds, pass rule, claim sentence. |
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
- [x] Geometry QA pass on all explainer SVGs (2026-07-18): programmatic getBBox audit of every
      text element in all six figures (overflow vs viewBox + pairwise overlap). Found and fixed:
      clipped legend + axis label on the CI chart (viewBox too short), an off-canvas reference
      label in the sealed-seeds demo, and an overflowing/overlapping two-line caption on Fig. B.
      Re-audit after fixes: ALL 6 SVGS GEOMETRY-CLEAN (with the seeds demo fully rendered).
- [x] WCAG contrast audit of the explainer design tokens, both themes (2026-07-18): dark theme
      passed everywhere; light theme had 4 failures (muted footnote text 3.69:1, amber callout
      4.03:1, orange noise dots 2.25:1 worsened by 0.75 opacity). Fixed: muted #7a8699->#626e84,
      amber #9a6b00->#7d5600, light chart-orange #E69F00->#9c6500 (dark keeps Okabe-Ito orange,
      which passes on dark surfaces), dot opacity ->0.85. Re-audit: ALL PASS both themes
      (text pairs >=4.5:1, graphical marks >=3:1).
- [ ] (standing) Re-run the contrast audit alongside the geometry audit after any future
      token/figure change.
- [ ] (standing) Re-run the SVG geometry audit after any future figure edit (the getBBox
      overflow/overlap script lives in the session log; three of five initial figures had
      invisible defects — this class of bug does not announce itself).
- [ ] (standing) Cross-check every number in the companion files and PAPER_WRITING_TEMPLATE.md
      against its DECLARED SOURCE after each future results/paper change. Source map (codified
      2026-07-18 after the GrIT-fence commit's sweep): result values and comparator numbers ->
      PAPER_SUBMISSION.md verbatim (at the paper's printed precision); Office V3 per-seed
      finals -> OFFICE_V3_RESULTS.md (the explainer names this source in its own text); the
      175-cell count -> the strict gate's own BUILD GREEN output (mirrored in
      CANONICAL_SUBMISSION.md); the 276-file count -> the strict gate's manifest-verification
      output. Last full check: 2026-07-18 post-GrIT-fence — every number verified against its
      source; no drift.
- [x] Optional: add a "try different seeds" animation to the FIR demo showing run-to-run spread
      vs the CI-lower-bound idea (2026-07-18: sealed-seeds demo added to explainer sec 3 using the
      five REAL Office V3 K=16 per-seed finals from OFFICE_V3_RESULTS.md — dots drop one by one,
      then the mean and the green CI-lower-bound marker land above the two reference bars;
      respects prefers-reduced-motion; verified live in-browser).
