# Write the Paper Yourself — A Guided Template

*A section-by-section scaffold for writing "Pre-Registered, Artifact-Gated Evaluation for
Sequential Recommendation" in your own words. Companion documents:
[`PLAIN_LANGUAGE_COMPANION.md`](PLAIN_LANGUAGE_COMPANION.md) explains the ideas;
this file teaches you to write them. The current gated paper
([`PAPER_SUBMISSION.md`](PAPER_SUBMISSION.md)) is your **answer key** — draft each section
yourself first, then diff against it. This guide is documentation, not submission material.*

---

## Part 0 — How to use this template

1. **Write in the order given in Part 2, not in reading order.** Papers are read
   front-to-back but written inside-out: tables first, then the sections that explain them,
   and the abstract/title dead last. Writing the intro first is the classic way to stall.
2. **One session per block.** Each section block below is sized for one sitting (45–90 min).
   Ten sittings ≈ a full draft. Don't polish during drafting; polish is Part 3.
3. **Draft blind, then diff.** For each section: read the block's *Job*, *Recipe*, and
   *Ingredients*; write your version; only then open the answer key and compare. Where the
   answer key is better, ask *why* (usually: a caveat you dropped, or a number you rounded).
   Where yours is better — keep yours.
4. **Never retype a number from memory.** Every number in this guide is copied verbatim from
   the gated paper. When you write, copy from here or from `_bestrec_run/hstu_tables.json`.
   The build gate will catch a wrong digit, but the habit matters more than the net.

## Part 1 — Ground rules that protect you (read before every session)

**The claim boundary.** These are enforced by the build-time hygiene scanner and by the
standing audit; internalize them as *writing* rules:

- Never write **"state of the art" / SOTA** about this work — on any category, any dataset,
  or in general. On Video_Games we are *below* the published comparator (0.0673 vs 0.0760):
  the word is "competitive."
- Never write **"significantly better than HSTU-BLaIR"** or any paired/distributional
  superiority claim. Their numbers are single runs; the honest sentence shape is: *"our
  fresh multi-seed mean and its 95% CI lower bound exceed the published point estimate."*
- Never present **Office V1 as passed** — its VOID is permanent. Never present **Office V3
  beyond its frozen wording**: a per-category point-estimate comparison, nothing more.
- The FIR-breadth results are an **internal paired filter-vs-no-filter contrast** — never a
  comparator claim.
- Reference-implementation runs are **"environment-caveated single-run regenerations"** —
  never "official reproduction" or "pinned reproduction."
- When in doubt: **narrower is always allowed, broader never is.**

**The evidence rule.** If you write a number, you must be able to name the artifact it comes
from. If you write a claim, you must be able to name the pre-registration or label it
exploratory/descriptive. If you can't — the sentence doesn't go in.

**The caveat rule.** A caveat is part of the result, not an apology after it. Write the
finding and its boundary in the same breath ("X holds, under Y, measured by Z"), never in
separate paragraphs a reviewer can quote apart.

## Part 2 — The sections, in writing order

### Block 1 · The results tables (before any prose)

- **Job:** Fix the skeleton of facts the whole paper hangs on. Tables are the paper; prose
  is commentary.
- **Recipe:** (1) List every claim you intend to make. (2) For each, pick the one table that
  proves it. (3) Sketch each table's rows/columns on paper before touching LaTeX/markdown.
  (4) Check each printed value against `hstu_tables.json`.
- **Your ingredients:** Table 1 (VG headline + ablation ladder), Table 1a/1b (baseline
  parity + comparator evidence), the §5.2 confirmation blocks (MI, Office V3), the FIR
  breadth paired deltas, Table 2 (negative-result map), the §4.1 dataset table (all six
  categories, roles, total interactions).
- **Pitfall:** A table that supports no claim is decoration — cut it or move it to an
  appendix. A claim with no table is an anecdote — demote or delete it.

### Block 2 · §3 Method

- **Job:** Let a competent stranger rebuild your system without reading the code.
- **Recipe:** (1) One paragraph of shared architecture (what every run uses). (2) The
  headline configuration with every hyperparameter (d_model 64, 4 layers, 2 heads, dropout
  0.5, 40 epochs, batch 256, chunked-full-softmax with item chunk 32,768, warmup-cosine).
  (3) One subsection per *component you claim something about* — for you that is the causal
  FIR filter above all: define it in one equation, then state the three safety properties
  (strictly causal/left-only; zero-initialized so it starts as identity; depthwise and tiny,
  K∈{8,16}). (4) The evaluation protocol (§3.6): AR2023 5-core, full-catalog
  leave-last-one-out, best-by-validation selection, train+val items masked at test.
- **Skeleton:** *"All headline runs share ___. The winning configuration adds ___ and ___.
  The causal FIR filter replaces each position's representation with a learned weighted
  average of itself and the K−1 positions before it: [equation]. Three properties keep it
  leak-free: ___, ___, ___. Evaluation ranks the held-out item against the entire catalog
  (n_eval = ___ on ___)."*
- **Pitfalls:** Don't argue *why it's good* here (that's §5/§6); don't hide any setting a
  reproducer would need; the words "leak-free" and "zero-initialized" must appear — they are
  the novelty boundary.

### Block 3 · §4 Experiments

- **Job:** State what was run, on what data, so that §5 can be read without trust.
- **Recipe:** (1) Dataset table with *roles* — which categories serve which claim (VG =
  multi-seed reference numbers; MI + Office = pre-registered comparisons; IS + CDs =
  pre-registered breadth; Beauty = hard transfer/appendix). (2) Baselines, including the
  published comparators you compare *descriptively*. (3) The experimental design: 6 seeds
  (20260608–13) for the headline, 5 for each ablation rung, mean ± sample std, best-by-val.
  (4) Hardware honesty: one consumer GPU (RTX 5060 Ti, 16 GB), ~10 min/seed on VG; the model
  is 11.6M parameters.
- **Your key numbers:** VG 94,762 users / 25,612 items; MI 57,439 / 24,587; Office 223,308
  / 77,551; the comparator pipeline's statistics match ours exactly on users/items,
  interactions within ±1.
- **Pitfall:** Every pre-registered campaign must be traceable here to its frozen document
  (`SOTA_CONFIRM_PREREG_V2.md`, `PREREG_OFFICE_V3.md`, `PREREG_FIR_BREADTH.md`) — the
  reader should be able to check that the design you describe is the design you froze.

### Block 4 · §5 Results

- **Job:** Report what happened — findings first, mechanics second, caveats welded on.
- **Recipe:** Write §5.1 (VG reference numbers, explicitly NOT SOTA) → §5.2 (the two counted
  confirmations + the breadth paragraph) → §5.3–5.4 (tail pattern + thinning interventions)
  → §5.5 (negative-result map — publish your dead ends; it is credibility, not weakness) →
  §5.6 (theirs-on-ours regenerations, environment-caveated).
- **Your load-bearing sentences (verbatim-safe forms):**
  - MI: *"fresh 5-seed 0.04152 ± 0.00045 (95% CI lower bound 0.04096, K=16) and 0.04120 ±
    0.00030 (CI-LB 0.04083, K=8) — both CI lower bounds above the published 0.0406, 10/10
    seeds above."*
  - Office V3: *"K=16 0.03047 ± 0.00011 (CI-LB 0.03033) and K=8 0.03029 ± 0.00005 (CI-LB
    0.03024), 10/10 seeds above both the environment-matched local regeneration 0.0279 and
    the published 0.0271."* Always in the same breath: per-category point-estimate
    comparison; no paired superiority; not SOTA.
  - FIR breadth (paper-printed precision; full 5-dp values live in `FIR_BREADTH_RESULTS.md`):
    *"Industrial_and_Scientific paired Δ = +0.0024 ± 0.0005 (95% CI [+0.0018, +0.0030]);
    CDs_and_Vinyl +0.0057 ± 0.0006 (95% CI [+0.0049, +0.0064]); 5/5 seeds positive each;
    zero per-category tuning."*
  - Attribution honesty: the VG win over published SASRec (+17.5%) is *architectural, not
    text-driven* — ID-only already reaches ≈0.0656; the whole text stack adds +0.00178 ±
    0.00021 (+2.7%); time bias is the largest classical component (+0.0027); text-sim bias
    is dead weight (±0.0001); TAPE is sub-additive.
- **Pitfalls:** Never bury which numbers are confirmatory vs exploratory — label per cell.
  Never compare across protocols (the SID-line universe differs; Amazon-2014 differs) except
  to say the comparison is invalid.

### Block 5 · §6 Discussion + Limitations (and the Office story)

- **Job:** Interpret, bound, and disclose — this section is where a skeptical reviewer
  decides you are trustworthy.
- **Recipe:** (1) What the results mean (density-conditional text; a cheap safe regularizer;
  apparatus as practice). (2) The scope bullets: what is counted (MI, Office V3 — each under
  its frozen wording), what is VOID forever (Office V1), what is internal-only (FIR
  breadth). (3) Limitations that are *genuinely yours*: both counted comparisons gate
  against single-seed published values and a single-run local regeneration, so
  distributional comparator uncertainty is unquantified; the pinned official environment
  cannot execute locally, so reference runs are environment-caveated.
- **How to tell the Office story (the paper's honesty centerpiece):** three beats, always
  together — (i) V1 passed numerically but its pre-registered floor check failed (our
  plain-SASRec floor landed +44% above their published SASRec), so V1 is VOID and stays
  VOID; (ii) running the comparator's own unmodified code in our environment produced 0.0279
  vs their published 0.0271, explaining the tilt; (iii) the redesigned V3 pre-registration
  gated against that environment-matched reference on fresh seeds and passed. Never let a
  paragraph contain only beat (iii).
- **Pitfall:** A limitation you name is a footnote; a limitation a reviewer finds is a
  rejection. Spend your best sentences here, not in the abstract.

### Block 6 · §2 Related Work

- **Job:** Position, don't survey. Each cited line answers "why is our thing still needed?"
- **Recipe:** (1) The protocol families and why numbers don't transfer across them (§2.1).
  (2) The novelty boundary paragraph (§2.3): FIR vs FMLP-Rec/BSARec/FEARec (frequency-domain
  prior art) and Caser/NextItNet (convolutional prior art) — your claim is only the
  leak-free, left-causal, zero-init depthwise regularizer *inside this artifact-gated HSTU
  setting*. (3) The concurrent-2026 fence: cite SID-MLP, Latte, ReSID, ChronoSID, GrIT,
  UniSGR, DIGER, ACERec, SILLM4Rec — and make **no comparative claim** against any of them.
- **Pitfall:** Never cite from memory — every entry in `references.bib` was
  metadata-verified (Crossref/arXiv); keep that discipline for anything you add.

### Block 7 · §1 Introduction

- **Job:** Earn the read: problem → why hard → what you did → contributions, one page.
- **Recipe:** (1) Open with the field's credibility problem (tiny deltas, many knobs,
  selective reporting) — that motivates the *apparatus as contribution 1*. (2) State the
  demonstrations: the FIR filter, the two pre-registered confirmations, the
  dataset-conditional text finding. (3) A numbered contributions list where every item maps
  to a section and a table. (4) End with the scope sentence (what this paper does not
  claim) — putting it in §1 disarms the reviewer early.
- **Skeleton:** *"Sequential recommendation results are notoriously hard to trust because
  ___. We present ___, an evaluation discipline consisting of (i) ___, (ii) ___, (iii) ___,
  (iv) ___, and demonstrate it end-to-end on ___. Our contributions: 1) ___ (§_, Table _);
  2) ___ … We explicitly do not claim ___."*
- **Pitfall:** No result may appear in the intro that §5 doesn't prove, in the same wording.

### Block 8 · §7 Conclusion + §8 Availability + Ethics

- **Job:** §7: land the plane in half a page — restate the apparatus arc (it caught our own
  flaw, the redesign removed it by construction, the fixed protocol passed) and one future
  direction. §8: the reproducibility contract — tracked artifacts, the one strict-gate
  command, the sidecar deposit policy, the data non-redistribution boundary. Ethics: public
  dataset, no personal data beyond it, per-user sidecars contain only evaluation records.
- **Pitfall:** Zero new claims after §6. The conclusion may only shrink.

### Block 9 · Abstract (now, not earlier)

- **Job:** The whole paper in ~250 words: problem, apparatus (i)–(iv), the three
  demonstration findings with their strongest honest numbers, the scope sentence.
- **Recipe:** Write one sentence per: credibility problem → apparatus → FIR result → MI
  confirmation (CI-LBs 0.04096/0.04083 > 0.0406) → Office V3 pass (CI-LBs 0.03033/0.03024 >
  0.0279 > 0.0271) with the V1-VOID clause → breadth clause → text-conditionality → the
  boundary ("no SOTA claim; single-run comparators; point-estimate comparisons").
- **Pitfall:** The abstract is the most-quoted text in review. Every forbidden wording rule
  applies at double strength; if a sentence feels impressive, check it against Part 1 twice.

### Block 10 · Title + last look

- **Job:** The title states the contribution class honestly: methodology first, findings
  second. Current form — *"Pre-Registered, Artifact-Gated Evaluation for Sequential
  Recommendation: Causal FIR Filtering and Dataset-Conditional Text Benefits on Amazon
  Reviews 2023"* — is a good pattern: apparatus : findings : dataset. Yours may differ, but
  keep that order of emphasis.

## Part 3 — The polish passes (after the full draft, in this order)

1. **The reviewer-2 pass.** Read each section asking one question: §1 "so what?" · §2 "isn't
   this just X?" · §3 "could I rebuild it?" · §4 "what did they hide?" · §5 "which numbers
   are confirmatory?" · §6 "what aren't they telling me?" Fix what you can't answer.
2. **The quote-apart pass.** For every strong sentence, check the sentence *alone*, out of
   context, still respects Part 1 (reviewers quote single sentences).
3. **The number pass.** Every printed number against `hstu_tables.json` / the results docs.
4. **The mechanical pass (your infrastructure — use it):**
   ```powershell
   # rebuild the reader PDF + placeholder/forbidden-wording scan (must print "scan: CLEAN")
   uv --project _bestrec_run run python _bestrec_run/render_paper_pdf.py
   # LaTeX twin + hygiene scan (must print PASS)
   bash paper_tex/build.sh
   # the full fail-closed gate (must exit 0)
   uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict
   ```
   If you hand-write your own version in `PAPER_SUBMISSION.md`, these three commands make
   the machinery re-verify *your* text exactly as it verified the current one — that's the
   point of the apparatus: it doesn't care who wrote the prose.
5. **The read-aloud pass.** Anything you stumble over aloud, a tired reviewer stumbles over
   in print.

## Part 4 — A realistic schedule

| Sitting | Block | Output |
|---|---|---|
| 1 | Part 0–1 + Block 1 | claim→table map, table skeletons |
| 2–3 | Blocks 2–3 | Method + Experiments drafts |
| 4–5 | Block 4 | Results draft (two sittings; it's the longest) |
| 6 | Block 5 | Discussion + Limitations + Office story |
| 7 | Block 6 | Related work |
| 8 | Block 7 | Introduction |
| 9 | Blocks 8–10 | Conclusion, availability, abstract, title |
| 10 | Part 3 | all five polish passes |

Diff against the answer key at the end of each sitting, not the start. When your version
and the gated paper disagree on a *fact*, the gate wins. When they disagree on *voice* —
yours wins; that's the goal.
