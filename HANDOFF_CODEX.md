# CLAUDE TICK — patch register: findings converted to applyable text (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `6e427366` (ninth
consecutive tick); A0/A1 still BLOCKED. Files added: `CLAUDE_PATCH_REGISTER_2026-07-31.md` +
this section. Preserved (NOT staged): every file named in the patches, plus
`PAPER_REVIEW_AUDIT.md`, adjudication JSONs, `paper_tex/tables/*`, `RELEASE_MANIFEST.json`,
`qa_final*/`, `tmp/`, `temp/`.

**No new findings this tick — deliberately.** Nine ticks produced twelve findings as analysis
and none has been actioned; a thirteenth would dilute, not help. This tick converts the
applyable subset into **exact anchored replacements** so the backlog can land in one
mechanical pass: **P1** cover-letter counts, **P2** cover-letter pointwise sentence, **P3** pin
the canonical weight-decay definition (C1), **P4** split-protocol disclosure paragraph (M1,
new text, no experiment), **P5** MovieLens precise-null/bound wording (E1), **P6** remove the
"Thus" non sequitur + opaque jargon (E2), **P7** precise evidence class for the breadth
campaign (E4). Optional **P8** records the refuted budget hypothesis as exploratory.

**Anchor discipline (learned this tick):** `COVER_LETTER_TORS.md` and `PAPER_SUBMISSION.md` are
HARD-WRAPPED. My first anchor check returned 0 matches for two real strings purely because they
span line breaks; re-verified with whitespace-flattened matching and all anchors are confirmed
present (192/18 at L47–48, 282 assets at L51, 751/751 at L52). Apply with a flatten-aware edit
or re-wrap afterwards, or the patch will silently fail to match.

**P1 deliberately supplies NO replacement numbers.** I cannot authoritatively derive the
cell/family/manifest counts, and hardcoding a second set of hand-typed values would repeat
exactly the failure E5 identifies. The instruction is to regenerate from
`rebuild_hstu_submission.py --strict` and `RELEASE_MANIFEST.json` at submission time — and the
handoff's own `201/25` and `1,073/407` must likewise be re-derived, not copied.

**P5 status:** I withdrew this wording at `faaad07d` pending F3/F4 and **restored it at
`6e427366`** after F5 refuted them. Bound framing legitimate; "equivalent" still forbidden.

**NOT in the register** (design judgment, not text): W1/W2 tuning-matrix fairness, D1/D2
dataset gate, F1 (`fir_v3_final_l2`), and the four checklist status downgrades.

**Open risks:** scientific — F1 (mechanism); C1; M1; F2; A3 W1/W2; A2 not isolated. venue —
A0; E5 stale cover letter (now patch-ready); E3 under-claiming. human — A0, A1, A4
licence/custody, AI-use statement. **process — twelve findings and a patch register now await
a Codex pass; the loop's marginal value is low until they land or a human gate opens.**

**Next safe action:** Codex applies or rebuts P1–P7 patch-by-patch (P1 and P2 are the cheapest
editor-facing wins). Claude next tick: hold on new findings; re-audit anything Codex lands.
**Expressly forbidden:** hardcoding regenerated counts into P1; strengthening P4 into a
robustness claim; treating P8 as pre-declared; citing F3/F4 as live threats; calling any venue
Tier A before A0.

---

# CLAUDE TICK — F5: I REFUTE MY OWN F3/F4 from existing artifacts (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `fc24438f` (eighth
consecutive tick); A0/A1 still BLOCKED. Files added: `CLAUDE_F5_F3_F4_REFUTED_2026-07-31.md`
+ this section. Preserved (NOT staged): `PAPER_REVIEW_AUDIT.md`, `PAPER_SUBMISSION.md`,
`COVER_LETTER_TORS.md`, TeX, checklist, preregs, adjudication JSONs, `paper_tex/tables/*`,
`RELEASE_MANIFEST.json`, `qa_final*/`, `tmp/`, `temp/`.

**Executed the F4 discriminating test with ZERO GPU cost, using the decision rule I
pre-declared at `fc24438f` BEFORE running it** (so this is not a post-hoc rescue). Every result
JSON carries a 20-entry `history` of PER-EPOCH VALIDATION metrics for both arms at every seed;
since steps/epoch = ceil(users/batch), an early epoch IS a low-budget run. Used **validation,
not test** (using test curves here would be metric-mining).

Paired learned−identity validation gap at the epoch matching ML-1M's ENTIRE ~472-step budget:
MI epoch 2 (~448 steps) **+0.001386, 8/8 seeds positive** (62% of final);
IS epoch 2 (~400) **+0.001415, 8/8** (61% of final);
CDs epoch 1 (~484) **+0.000891, 8/8** (+0.005516 by ~968). Even at HALF ML-1M's budget
(MI epoch 1, ~224 steps) the gap is +0.000460, 8/8 positive.

**VERDICT: F4 RETRACTED; F3's inference RETRACTED.** On all three Amazon corpora the FIR effect
is already clear and unanimous at ML-1M-equivalent budget, so the 8.5×–20.5× step deficit does
NOT explain the MovieLens null. My central inference was wrong.

**Survives:** the factual step-count table (disclose as a protocol asymmetry, not an
explanation); ρ=+1.000 as a true description of four points, causal reading refuted.
**Restored and stronger:** the ML-1M null reads as a genuine corpus/domain difference and now
carries MORE weight, because a serious alternative was tested and failed; **my E1 withdrawal is
LIFTED** — the bound framing is legitimate again (still a bound, still NOT equivalence); the
three-corpus breadth result is unaffected and better supported. **I withdraw last tick's
request for a step-matched down-budget campaign — it is now redundant. No new GPU work needed
for this question.**

**F1 still open** but "under-trained" is now the LEAST likely explanation; live candidates are
little short-range temporal structure in ML-1M, or tie/plateau granularity on a much smaller
catalog (~3.7k movies vs 24.6k–124k items). The `fir_v3_final_l2` check remains worth doing —
now diagnostic of MECHANISM, not of validity.

**Incidental (descriptive, exploratory, post-hoc, licenses NOTHING):** the gap is non-monotone
in training time — MI peaks epoch 7 (+0.002879) → settles +0.002224; CDs peaks epoch 3
(+0.008895) → settles +0.005822. Consistent with the module acting partly as an OPTIMIZATION
ACCELERANT rather than purely a final-quality gain. Would need its own frozen protocol to enter
the paper.

**Open risks:** scientific — F1 (mechanism, not validity); C1; M1; F2; A3 W1/W2; A2 not
isolated. venue — A0; E5 stale cover letter; E3 under-claiming. human — A0, A1, A4
licence/custody, AI-use statement.

**Next safe action:** Codex works the standing register (E5 cover letter is the cheapest
editor-facing win; then C1, M1). Claude next tick: queue item (f) unless Codex responds.
**Expressly forbidden:** citing F3/F4 as live threats (they are retracted); requesting the
step-matched campaign; treating the non-monotone-gap observation as a claim; calling any venue
Tier A before A0.

---

# CLAUDE TICK — F3 CONFIRMED from measured metadata; F4: effect tracks budget (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `faaad07d` (seventh
consecutive tick); A0/A1 still BLOCKED. Files added:
`CLAUDE_F4_EFFECT_TRACKS_BUDGET_2026-07-31.md` + this section. Preserved (NOT staged):
`PAPER_REVIEW_AUDIT.md`, `PAPER_SUBMISSION.md`, `COVER_LETTER_TORS.md`, TeX, checklist,
preregs, adjudication JSONs, `paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`,
`tmp/`, `temp/`. **This tick stress-tested MY OWN F3 before it triggers an expensive re-run.**

**F3 CONFIRMED from measured run metadata** (previously prereg arithmetic only). Trainer
`augment_factor` defaults to 1 — in-source: "number of training examples per user per epoch"
(`run_sasrec_sbert.py:178`) — so steps/epoch = ceil(users/batch) and the ratio is exactly the
user-count ratio. Read `n_users`/`epochs`/`batch_size` from committed result JSONs:
ML-1M 6,040 users → **~472 steps**; IS 50,985 → ~4,000; MI 57,439 → ~4,500; CDs 123,876 →
~9,680. Ratio vs ML-1M spans **8.5×–20.5×**, not merely 9.5×.

**F4 (NEW; argues AGAINST our own positive result — filed for that reason).** Pairing each
corpus's measured effect with its step count: ML-1M 472→+0.0000002; IS 4,000→+0.002110;
MI 4,500→+0.002265; CDs 9,680→+0.006150. **Spearman ρ(steps, effect) = +1.000**, perfect rank
concordance; exact two-sided permutation **p = 0.083**, which at n=4 is the MINIMUM ATTAINABLE
p — **not significant at α=0.05 and not described as such.** This supplies a single unified
alternative explanation for the paper's whole cross-corpus pattern: an identity-initialized
module needs steps to depart from zero, so effect size grows with budget — reproducing the
observed ordering INCLUDING the ML-1M null without any appeal to domain, temporal structure,
or our claimed mechanism.

**Precise scope. NOT threatened:** within-corpus contrasts stand — both arms shared one
verified init AND the same budget within each corpus, so `a1learned − a0ident` inside MI/IS/CDs
remains valid and **`CANON-BREADTH-POS` is NOT retracted.** **Threatened:** (1) the breadth
result read as transfer/generalization (budget varies 2.4× among the three Amazon corpora and
correlates perfectly with effect); (2) the ML-1M null as a domain finding; (3) any
domain-dependent framing. **Honestly stated:** step count is collinear with user count, catalog
size, density and domain; I do NOT claim budget causes the ordering; n=4 is tiny; this is a
hypothesis the paper currently contains nothing to exclude.

**Discriminating test (cheap by construction — short runs are short):** step-matched
DOWN-budget replication on one Amazon corpus. Hold everything fixed, cut MI (or IS) to
ML-1M-like ~472 steps (20 epochs → ~2, or subsample to ~6k users with frozen seed), run
`a0ident` vs `a1learned` matched-init, ≥5 fresh seeds. Effect COLLAPSES → budget explanation,
rewrite the cross-corpus narrative. Effect PERSISTS → **F3/F4 refuted, the ML-1M null survives
as domain-conditional, and the breadth story is STRENGTHENED because we tried to break it and
failed.** Needs a NEW frozen identifier + committed adjudicator + fresh reject-first memo;
never a re-analysis of existing campaigns; all existing records retained.

**Manuscript must not say (until resolved):** ML-1M as a domain-conditional negative; the
breadth as transfer/generalization without disclosing the budget confound; my withdrawn E1
bound wording. The abstract needs: *training budget was not matched across corpora, and
measured effect size is monotone in budget across the four corpora tested.*

**Open risks:** scientific — F4/F3 (unified alternative explanation for the whole pattern);
F1/F2; C1; M1; A3 W1/W2; A2 not isolated. venue — A0; E5 stale cover letter; E3. human — A0,
A1, A4 licence/custody, AI-use statement.

**Next safe action:** Codex confirms no campaign overrode `augment_factor`, verifies the step
table, and decides on the step-matched down-budget protocol. Claude next tick: queue item (f)
unless Codex responds. **Expressly forbidden:** describing ρ=+1.000 / p=0.083 as significant;
retracting `CANON-BREADTH-POS` on the basis of F4 (within-corpus contrasts are unaffected);
narrating ML-1M as a domain finding; re-analysing existing campaigns instead of a new frozen
protocol; calling any venue Tier A before A0.

---

# CLAUDE TICK — F3: the ML-1M null is confounded with a ~9.5x smaller optimizer budget (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `5b69e514` (sixth
consecutive tick); A0/A1 still BLOCKED. Files added:
`CLAUDE_F3_ML1M_TRAINING_BUDGET_2026-07-31.md` + this section. Preserved (NOT staged):
`PAPER_REVIEW_AUDIT.md`, `PAPER_SUBMISSION.md`, `COVER_LETTER_TORS.md`, TeX, checklist,
preregs, adjudication JSONs, `paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`,
`tmp/`, `temp/`.

**F3 (BLOCKING for any external-validity claim; supersedes my F1 framing).**
`PREREG_FIR_EFFICIENCY_ML1M_V1` transfers the MI configuration "unchanged": 20 epochs, batch
256, **one training example per user per epoch**. Transferring EPOCHS is not transferring
OPTIMIZER STEPS, because steps/epoch scale with user count:
MI ~57,439 users -> ~224 batches/epoch -> **~4,488 steps** (~10 min/seed, §3);
ML-1M 6,040 users -> ~24 batches/epoch -> **~472 steps** (**7.7 s/seed**, recorded in the
adjudication `resource_summary`). **≈9.5x fewer optimizer steps**, corroborated independently
by wall-clock (7.7 s vs ~600 s).

This matters because the canonical FIR is **identity-initialized** — taps start at exactly
zero and must be LEARNED AWAY from a no-op. With ~472 steps (minus warmup-cosine warmup) and
best-of-20 validation points, the taps may never depart meaningfully from zero. That single
mechanism explains all three anomalies at once: F1's bit-identical seeds; no arm separating
from identity (all six means 0.05212–0.05221); and F2's near-vacuous noninferiority
(compressed vs full is trivial when neither has left its initialization). **The study may
have tested six near-identical copies of the identity backbone rather than the FIR.**

Irony worth recording: the prereg's "No MovieLens hyperparameter tuning is permitted" is the
right instinct against fishing, but **fairness-by-transfer produced an unfairness** — holding
epochs fixed across corpora with ~9.5x different user counts silently under-trains the
smaller one.

**I am RETRACTING my earlier E1 recommendation** (restate the ML-1M interval as a bound below
Amazon magnitude) **until F3 resolves.** Bounding an effect is only meaningful if the
treatment was actually applied; you cannot bound the effect of a module that may never have
left its initialization.

**Required of Codex:** (1) verify the step arithmetic against frozen config + run metadata —
if wrong, say so plainly and F3 collapses; (2) read `fir_v3_final_l2` for the ML-1M `learned`
arm (NOTE: ML-1M record-level files are private under the ML-1M README, so this likely needs
Codex's local access — I cannot read them); (3) if confirmed, re-run **matched on optimizer
steps, not epochs**, under a NEW frozen identifier with a fresh reject-first memo — never as a
re-interpretation of the existing campaign, and the original ML-1M record is retained
regardless (guide §4); (4) until resolved, **the paper must not narrate ML-1M as a
domain-conditional negative** — state it as an unresolved budget confound or omit the
external-validity claim.

**Open risks:** scientific — F3 (may invalidate the only non-Amazon evidence); F1/F2; C1; M1;
A3 W1/W2; A2 not isolated. venue — A0 unverified; E5 stale cover letter; E3 under-claiming.
human — A0, A1, A4 licence/custody, AI-use statement.

**Next safe action:** Codex verifies F3 arithmetic + tap norms. Claude next tick: queue item
(f) manuscript focus/length work touching no generated table or graph, unless Codex responds.
**Expressly forbidden:** narrating the ML-1M null as a domain finding before F3 resolves;
using my withdrawn E1 bound wording; re-interpreting the existing ML-1M campaign instead of
re-running under a new identifier; calling any venue Tier A before A0.

---

# CLAUDE TICK — A4 narrowing + F1: ML-1M arms bit-identical on 3/8 seeds (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `792efb6c` (fifth
consecutive tick); A0/A1 still BLOCKED (4 `[Maintainer:` placeholders remain in both
`paper_tex/paper-shared.tex` and `COVER_LETTER_TORS.md`). Files added:
`CLAUDE_A4_MOVIELENS_NARROWING_2026-07-31.md` + this section. Preserved (NOT staged):
`PAPER_REVIEW_AUDIT.md`, `PAPER_SUBMISSION.md`, `COVER_LETTER_TORS.md`, TeX, checklist,
adjudication JSONs, `paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`, `tmp/`,
`temp/`.

**F1 (BLOCKING — check before the paper narrates MovieLens).** Read from the COMMITTED
`fir_efficiency_ml1m_v1_adjudication.json` (adjudicator already ran; no sealed endpoint
opened): on **3 of 8 seeds the learned-FIR arm and the identity arm produced BIT-IDENTICAL
NDCG@10** (s2 0.047012017140, s4 0.046056306397, s6 0.050821479159 — diff exactly 0.000e+00).
Same pattern elsewhere: bit-identical-to-identity counts `lowrank 3/8`, `learned 3/8`,
`grouped 2/8`, `pointwise 2/8`, `shared 0/8`. With ~6,040 eval users, bit-identical NDCG@10
means NOT ONE user's top-10 changed. Three candidate explanations, which must be
distinguished BEFORE interpreting the null: (1) the optimizer drove the taps to a functional
no-op — scientifically interesting and consistent with the paper's own capacity-adding-levers
-get-voted-off asymmetry; (2) metric/tie granularity; (3) **a pipeline fault — the module not
active on those runs, which would make the null an ARTIFACT, not a result.**
**Discriminating check (cheap, Codex-owned, no retraining):** the runner already records
`fir_v3_final_l2`, and the E-A/breadth adjudicators already gate the identity arm on it being
exactly 0. Read it for the ML-1M `learned` arm per seed. ≈0 ⇒ (1)/(3); clearly non-zero with
bit-identical NDCG ⇒ (2); exactly 0 on the LEARNED arm ⇒ integrity question, not a result.

**F2.** The compression claim is near-vacuous on this corpus: Q2 noninferiority (±0.000500)
holds, but no arm separates from identity (all means 0.05212–0.05221), so noninferiority among
inert arms says nothing about parameter efficiency. Not false — pre-declared and satisfied —
but the dependency on the Q1 null must be visible or it reads as a salvaged positive.

**Honest narrowing drafted, conditional on F1.** If (1)/(2): domain-conditional wording with
the ML-1M interval stated as a BOUND (upper bound `+0.000075` is >10× below the Amazon
estimates `+0.002110`…`+0.006150`), explicitly NOT equivalence (no margin pre-declared; CI
covers zero). If (3): the study is not interpretable as a domain finding — report as an
execution defect or re-run; do not narrate an artifact as a null. Enumerated what it does NOT
permit: not equivalence; not "FIR doesn't work" (n=1 domain); not parameter efficiency (F2);
not a refutation of the Amazon results; not "temporal structure doesn't matter" — which makes
the A4 **temporal-diagnosticity dimension (D1) doubly important**, since a pre-selection
diagnosticity screen would have told us whether ML-1M was a corpus where the mechanism could
show itself at all.

**Consolidated register added to the memo** — five ticks of memos, none yet actioned:
F1(blocking/very-low-cost), E5(cover letter stale), C1(canonical wd drift), M1(split
protocol), F2, E1–E4(under-claiming), W1/W2(tuning fairness), D1/D2(dataset gate),
A0/A1/A4-legal(human-only).

**Open risks:** scientific — F1 possible artifact; C1; M1; F2; A3 W1/W2; A2 not isolated.
venue — A0 unverified; E5 editor-facing staleness; E3 under-claiming. human — A0, A1, A4
licence/custody, AI-use statement.

**Next safe action:** Codex runs the F1 `fir_v3_final_l2` check and applies/rebuts the
register. Claude next tick: queue item (f) manuscript focus/length work that touches no
generated table or graph, unless Codex responds first. **Expressly forbidden:** narrating the
ML-1M null before F1 resolves; phrasing E1/F1 as equivalence; freezing either draft prereg;
calling any venue Tier A before A0.

---

# CLAUDE TICK — evidence-class audit: PASS on upgrading, 4 precision defects (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `81a9bcfb`; A0 still
BLOCKED (third consecutive tick). Files added: `CLAUDE_EVIDENCE_CLASS_AUDIT_2026-07-31.md` +
this section. Files deliberately preserved (NOT staged): `PAPER_REVIEW_AUDIT.md`,
`PAPER_SUBMISSION.md`, TeX, `TORS_METHODOLOGY_CHECKLIST.md`, adjudication JSONs,
`paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`, `tmp/`, `temp/`.

Closes the checklist's outcome-independent-reporting clause. **VERDICT: PASS — no selective
upgrading detected.** I looked for the standard failure (favorable results promoted,
unfavorable buried) and did not find it: the MovieLens null is in the ABSTRACT with numbers;
the shared-filter non-separation is in the abstract AND used to limit our own per-channel-tap
claim; contribution 1 says "modular component, not a new architecture"; explicit non-claims
present; title is module-scoped. Proposed checklist change: outcome-independent reporting
PARTIAL → PASS, conditional on the four precision fixes below.

**The paper now errs in the OPPOSITE direction. The guide's rule ("strongest label actually
supported, never the most attractive") is symmetric — under-claiming is also a mislabel.**

- **E1 (substantive):** "negative" mislabels a PRECISE NULL and discards information.
  MovieLens learned−identity `+0.000000 [−0.000074, +0.000075]` is a non-detection with a
  TIGHT interval whose upper bound is ~30× below the MI estimate (+0.002265). That BOUNDS the
  MovieLens effect well below Amazon magnitude — materially stronger domain-conditionality
  evidence than "negative". MUST be phrased as a bound, never equivalence (CI crossing zero
  is not equivalence; no margin was pre-declared). Proposed wording in the memo.
- **E2 (minor):** "Thus" is a non sequitur (compression finding does not follow from the
  MovieLens null); "conditional coefficient-count compression" is opaque jargon in an abstract.
- **E3 (substantive, venue):** the abstract is in audit-response register — ~7 of 9 sentences
  are hedges/negations/non-claims, and NO sentence says why a reader should care. The
  distinguishing fact (matched-init, per-seed-verified isolation replicated across categories
  under one frozen config with zero per-category tuning, inside a fail-closed gate) is absent
  from the first three sentences. NOT a request to weaken any caveat — keep every number and
  non-claim; add one motivating sentence and one naming what WAS established.
- **E4 (precision):** "outcome-known" is wrong for the canonical breadth in the HARSH
  direction — that campaign was committed-before-launch with fresh unused seeds (20260810–17);
  what was outcome-known was the LEGACY category result at DESIGN time. Accurate class:
  "prospectively frozen, same-investigator execution on categories whose legacy outcomes were
  known at design time." Collapsing it with the genuinely outcome-visible V2/V4 campaigns
  erases a methodological difference we actually earned.

**E5 (substantive) — `COVER_LETTER_TORS.md` is MATERIALLY STALE on three counts.** It exists
(my first pass missed it) and it is the first document an editor reads. (i) "192 paper-bound
cells across 18 claim families" vs current **201 cells / 25 families**. (ii) "751/751
manifested files" and "282 release-only assets" vs current **1,073 manifest files / 407
release-only assets**. (iii) It states "no active lag-0 or **pointwise** parameter-matched
non-temporal placebo **was run**" — but the pointwise placebo WAS run and adjudicated
`POINTWISE-FIR-DISCRIMINATED`. In fairness the sentence is scoped to the six-arm control
study, but the plain reading is global and it **contradicts the abstract**, which reports the
learned filter exceeding that placebo (+0.001941). It also UNDER-reports us: the pointwise
campaign is exactly the evidence addressing generic trainable-residual capacity. Required:
regenerate every count from the live graph/manifest at submission time, and rescope the
placebo sentence while citing the pointwise verdict. General rule: **the artifact gate
protects the manuscript's numbers, not the cover letter's — any hand-typed count in a
persuasion surface must be regenerated, not retyped.**

**Open risks:** scientific — M1 split-protocol gap; C1 canonical weight-decay drift; A3
W1/W2; A2 mechanism not isolated. venue — A0 unverified; E3 under-claiming reads as authors
doubting their own contribution. human — A0, A1, A4 licence/custody, AI-use statement.

**Next safe action:** Codex applies/rebuts E1–E4 and the earlier four status downgrades + M1
row; Claude next tick audits the cover letter if one exists, else queue item (f) manuscript
focus/length work that does not touch generated tables or the graph. **Expressly forbidden:**
phrasing E1 as equivalence; weakening any caveat while fixing E3; freezing either draft
prereg; calling any venue Tier A before A0.

---

# CLAUDE TICK — TORS methodology audit; M1 split-protocol gap (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. No new Codex commits since `9b5221eb`; A0 still
BLOCKED. Files added: `CLAUDE_TORS_METHODOLOGY_AUDIT_2026-07-31.md` + this section. Files
deliberately preserved (NOT staged): `PAPER_REVIEW_AUDIT.md`, `TORS_METHODOLOGY_CHECKLIST.md`
(Codex's file — status changes are PROPOSED, not applied), all adjudication JSONs,
`paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`, `tmp/`, `temp/`.

Delivered the reject-first audit form requested by `TORS_METHODOLOGY_CHECKLIST.md` §3, fully
completed, plus two red-team outputs:

**NEW FINDING M1 (high, scientific+venue) — the matrix has NO ROW for split-protocol
validity, and the manuscript never addresses it.** Everything in the checklist audits what we
do WITHIN the protocol; nothing audits the protocol. We evaluate throughout with iterative
5-core leave-last-out, which holds out each user's final event independently of global time,
so training can contain events occurring AFTER some users' test events. Mechanical evidence:
`grep -c "chronological split|global temporal split|temporal leakage|future information|
time-based split"` over `PAPER_SUBMISSION.md` = **0**; LLOO appears only in comparability
framing (vs TIGER/LIGER/BLaIR), never as an exposure of our own design. This is sharpened by
our own claim — we argue for a TEMPORAL inductive bias while the protocol is not temporally
coherent, which a methodology reviewer can reasonably press. Required (cheap, no experiment):
add a row + a manuscript paragraph stating the protocol, acknowledging the global-time
critique, justifying LLOO as protocol-family comparability, and recording a chronological
-split sensitivity as declared future work. Do NOT claim robustness we have not measured —
the chronological-cutoff replication was proposed earlier in this project and never run.

**Proposed status downgrades (Codex to apply or rebut — I did not edit the checklist):**
Proposed-method implementation PASS→PARTIAL (C1 unresolved: the method's DEFINITION is
drifting on weight decay); Evaluation protocol PASS→PARTIAL (E-E V3 prelaunch opened the
combined TRAIN/VALID/TEST export; sequestration limited to fitting/selection — a disclosed
caveat, but PASS reads unqualified); Reproducibility PASS→PARTIAL (private/local-only
sidecars and endpoints mean a third party cannot rerun every claim — Codex's own closure
column concedes this; PASS should mean a third party can rerun, not that we can);
Statistical analysis PASS-WITH-LIMITS→PARTIAL (Holm holds WITHIN each family, but selective
emphasis ACROSS many campaign families is uncontrolled — multiplicity within a family does
not address a garden of forking paths across families).

**AI-use disclosure flagged as material and broad** — two AI systems contributed to protocol
design, drivers, adjudicators, analysis choices, literature positioning, and manuscript
prose. A "used for editing" statement would be inaccurate. Wording is human-only.

**Open risks:** scientific — M1 split protocol; C1 canonical weight-decay drift; A3 W1/W2
fairness asymmetries favoring our own method; A2 mechanism still not isolated. venue — A0
unverified. human — A0, A1, A4 licence/custody, AI-use statement.

**Next safe action:** Codex applies/rebuts the four status downgrades and adds the M1 row;
Claude next tick does queue item (e) — reviewer-style attack on the current manuscript claim
set with line-by-line evidence-class consistency (title/abstract/contributions/conclusion vs
supplement labels). **Expressly forbidden:** claiming any chronological-split robustness we
have not measured; citing DOI 10.1145/3800587 for specific wording until its primary text is
verified; freezing either draft prereg; calling any venue Tier A before A0.

---

# CLAUDE TICK — A4 dataset-gate red-team; diagnosticity + exposure-bias gaps (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. Claude (red-team) tick; no new Codex commits
since `62c9326f`, and A0 remains BLOCKED (the roadmap cites the 2025 ABDC review only as an
example of a changing list process, not as a named controlling authority — so no venue may
be called Tier A). Files added: `CLAUDE_DESIGN_MEMO_NON_AMAZON_SELECTION_GATE.md` + this
section. Files deliberately preserved (NOT staged): `PAPER_REVIEW_AUDIT.md`, all
adjudication JSONs, `paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`, `tmp/`,
`temp/`.

**A4 verdict: APPROVE THE STRUCTURE, two additions REQUIRED before any candidate reaches
human legal review.** The hard-gate/scorecard/stop-rule design is sound (UNKNOWN blocks
rather than permits; repository-licence ≠ data-licence; no post-hoc substitution). The gap
is that it selects for lawfulness/logistics/"distinctness" but never asks whether a
candidate can DISCRIMINATE a short-range causal temporal filter.

- **D1 (blocking): no mechanism-relevance dimension.** For a 16-lag recency filter,
  diagnosticity is set by temporal structure, not product vertical. Far-stronger short-range
  structure ⇒ a positive result is near-guaranteed and weak; far-weaker ⇒ a null is
  uninformative. Add a metadata/TRAIN-only temporal-diagnosticity dimension (inter-event gap
  distribution, session burstiness, repeat rate, sequence length vs K) and PRE-DECLARE what
  each regime would make a positive/null result mean.
- **D2 (blocking): KuaiRand's exposure/policy confound is hypothesis-specific**, currently
  listed only as an open question. Recommender-logged data means "next item" is largely what
  the platform showed; a 16-lag filter can fit the LOGGING POLICY's temporal autocorrelation
  rather than user recency. The KuaiRand family ships a randomly-exposed portion precisely
  for this; whether it supports a full-catalog next-item task at usable scale is
  metadata-answerable and must be settled BEFORE selection. Add a hard exposure-bias gate.
- Candidate flags: KuaiRand ~7.6k catalog ⇒ metrics NOT comparable across blocks (declare
  direction/significance only) and repeat-consumption interacts directly with a recency
  filter. **MIND-small: recommend hard exclusion** — time-varying item availability means a
  causal filter would partly learn availability, not preference dynamics (an estimand
  failure specific to our mechanism). **Yelp:** weeks-to-months gaps ⇒ poor diagnosticity
  for K=16 even if licence resolves.
- D3 custody definition is looser than the guide's `externally custodied` bar (require: not
  an author, not supervised by an author, dated attestation naming what was controlled).
  D4 gate 6 protects the dataset but not the method — the new block tests transfer of an
  Amazon-selected configuration; decide and freeze whether it tests the MECHANISM or the
  CONFIGURATION (interacts with A3 finding W2).

**Sequencing (actionable):** do NOT send KuaiRand to human legal review yet. D1/D2 are
metadata-only and need no licence decision — add them, re-score all three candidates from
public metadata, then send only the surviving top candidate to the human with the exposure
question already answered. Human decision cycles are scarce and A0/A1 are already queued on
them.

**Open risks:** scientific — D1/D2 diagnosticity+exposure; C1 canonical weight-decay drift
(unresolved); A3 W1/W2 fairness asymmetries favoring our own method. venue — A0 unverified.
human — A0 ranking authority, A1 author/legal metadata, A4 licence/custody; A4 is the
binding constraint on A3 because W2 routes the fair-comparison claim through the new block.

**Next safe action:** Codex adds D1/D2 and re-scores from metadata; Claude next tick starts
`TORS_METHODOLOGY_CHECKLIST.md` row-by-row PASS/PARTIAL/FAIL (guide §9 item 2).
**Expressly forbidden:** acquiring/downloading/inspecting any candidate dataset; freezing
`DRAFT_TIER_A_TUNING_MATRIX_V1` or `DRAFT_FIR_TEMPORAL_ISOLATION_V1`; calling any venue
Tier A before A0; reading `A2 − A1` as equivalence.

---

# CLAUDE TICK — A3 tuning-matrix memo delivered; C1 canonical-drift finding (2026-07-31)

Branch `codex/bestrec-sota-results`, pushed. Claude (red-team) tick after Codex's
`d9bc3278`. Files added: `CLAUDE_DESIGN_MEMO_TIER_A_TUNING_MATRIX_V1.md` + this section.
Files deliberately preserved (NOT staged): `PAPER_REVIEW_AUDIT.md`, all adjudication
JSONs, `paper_tex/tables/*`, `RELEASE_MANIFEST.json`, `qa_final*/`, `tmp/`, `temp/`.

**Accepted both Codex corrections to my V1 memo.** B1's LayerNorm-duplication sentence is
withdrawn (the FIR residual precedes `norm_in`, LayerNorm couples channels, the affine acts
post-normalization) — the one-DOF collapse alone carries the rejection. B3's coupled-L2
argument does not apply when `fir_v3_wd == "zero"` (separate zero-decay param group); the
gradient-lockstep / effective-step half stands.

**NEW FINDING C1 (scientific, medium-high) — "canonical" is drifting on weight decay.**
Codex's response calls `fir_v3_wd == "zero"` the *intended canonical* configuration, but
every positive result we hold ran `backbone`: E-A `a1learned` (MI, W-POS) and the canonical
breadth campaign (IS + CDs, CANON-BREADTH-POS). The manuscript is currently CONSISTENT
("Primary taps used backbone weight decay") so there is no live defect — the risk is
forward-looking. The bridge is forbidden: E-A's `A2 − A1 = +0.000010, p = .95` **crosses
zero**, and CIs crossing zero are not equivalence, so we may not claim the decay choice is
immaterial. Resolve before any freeze: (1) define canonical = `backbone` (recommended, free,
matches evidence), or (2) define canonical = `zero` and re-run breadth under it.

**A3 verdict: REVISE — do not freeze `DRAFT_TIER_A_TUNING_MATRIX_V1`.** Architecture
endorsed (S0 outside the count, non-adaptive pre-generated configs, sealed S3,
adjudicator-first, retained negatives, realized-cost reporting). Four blocking objections:
W1 "12 configs per method" equalizes count, not coverage, and therefore favors
low-dimensional methods — i.e. **us** (FIR adds ~one knob); fix by giving the FIR arm
**zero extra search** (inherit the backbone's selected config, `K` fixed a priori) and
making baseline budgets coverage-based. W2 the HSTU-style backbone carries undisclosed
prior tuning on the Amazon categories, so it must take the full ladder on the new
non-Amazon block. W3 three dataset blocks cannot support a generalization inference (n=3);
pre-declare that no such claim will be made. W4 the MovieLens block mixes evidence classes —
re-run it inside the matrix or import it as historical, not both. Secondary: S2 winner's-curse
asymmetry, single post-hoc current comparator, OOM disposition must be fixed before any
failure is observed.

**Open risks:** scientific — C1; W1/W2 fairness asymmetries favoring our own method.
venue — A0 unverified, no venue may be called Tier A. human — A0 ranking authority and A1
author/legal metadata still BLOCKED; A4 dataset licence/custody unresolved, and W2 routes
the entire fair-comparison claim through that block.

**Next safe action:** Codex revises the tuning matrix against W1–W4 and resolves C1; Claude
red-teams `TIER_A_NON_AMAZON_SELECTION_GATE.md` next tick. **Expressly forbidden:** freezing
or launching `DRAFT_TIER_A_TUNING_MATRIX_V1` or `DRAFT_FIR_TEMPORAL_ISOLATION_V1`; calling
any venue Tier A before A0; reading `A2 − A1` as equivalence.

---

# CURRENT HANDOFF — Tier-A journal upgrade program opened (2026-07-31)

The human maintainer now requires publication in a journal recognized as Tier A
or higher. The exact ranking authority/edition is not yet supplied, so ACM TORS
remains the best scientific-fit candidate but is not represented as formally
Tier A. Read `CODEX_CLAUDE_COLLABORATION_GUIDE.md` first, then
`TIER_A_PUBLICATION_ROADMAP.md` and `TORS_METHODOLOGY_CHECKLIST.md`. The
checklist is a Codex prefill that Claude must audit with a dated reject/approve
memo; it is not independent review. The collaboration contract assigns Claude the
scientific red-team/venue-methodology role and Codex the freeze, execution,
artifact-graph, build, and release-integrity role. Neither agent may approve its
own work or modify the user-owned `PAPER_REVIEW_AUDIT.md`.

Claude completed the reject-first review at commit `17e489af` and returned
`REVISE — do not freeze`. The repeated-current arm collapses to one functional
degree of freedom and is weaker than the completed nonlinear pointwise control.
Codex accepted the no-run verdict in `CODEX_RESPONSE_TO_CLAUDE_DESIGN_MEMO.md`,
while correcting two overstatements: pre-LayerNorm channel rescaling is not an
exact duplicate of the post-normalization affine, and the intended canonical FIR
parameter group has zero weight decay. `PREREG_FIR_TEMPORAL_ISOLATION_V1_DRAFT.md`
is retained as rejected design history; no V1 implementation or run is allowed.

The completed V4/release boundary remains commit `2560e7f9`: V4 was adjudicated
and narrowly integrated, the 201-cell/25-family strict gate passed, a separately
hydrated clean-clone replay passed, the attestation verified, the branch was
pushed, and the release manifest was uploaded then re-downloaded with exact
SHA-256 equality. The attestation remains `release_ready=false` because real
author/contact/legal metadata are absent. Do not rerun or reinterpret V4.

Immediate safe work: verify the maintainer's ranking list; have Claude audit the
TORS methodology checklist, `PREREG_TIER_A_TUNING_MATRIX_V1_DRAFT.md`, and
`TIER_A_NON_AMAZON_SELECTION_GATE.md`. A3 tuning fairness and A4 non-Amazon
validity now precede any revised A2 mechanism study. The
maintainer must also approve an accurate venue-compliant AI-use disclosure that
covers research design, code, analysis, validation, and writing assistance. No
new experiment is active.

---

# Previous handoff — E-E V4 integrated and clean-clone verified (2026-07-31)

The latest manuscript/audit phase has completed its local substantive work. The frozen
pointwise mechanism result remains `POINTWISE-FIR-DISCRIMINATED`: learned FIR minus
identity +0.001872 [+0.001737,+0.002007], pointwise minus identity -0.000069
[-0.000200,+0.000061], and learned FIR minus pointwise +0.001941
[+0.001788,+0.002095] in one frozen three-test Holm family. This is outcome-known
Musical_Instruments evidence against one equal-parameter compound current-only placebo;
it is not temporal isolation, per-channel necessity, generalization, SOTA, or independent
confirmation.

The July 30 22:07 audit corrections are now mirrored across `PAPER_SUBMISSION.md`, ACM
TeX, generated tables, the bibliography, the graph/claim-map generators, and
`AUDIT_RESPONSE_2026-07-27.md` without modifying the user-owned audit. The paper now:

- distinguishes our AR2023 iterative user+item 5-core path from TIGER/LIGER's Amazon
  Reviews 2014 protocols and corrects LIGER's author metadata;
- states the true MovieLens acquisition/training chronology and covers both datasets in
  the ethics/governance section;
- positions the modular claim against TimeWeaver, TV-Rec, HyenaRec, ConvRec, and
  Mamba4Rec at mechanism level;
- removes sample-SD band-overlap inference and labels MovieLens parsimony as conditional
  coefficient-count compression, not compute optimization;
- fixes figure numbering and the acmsmall dataset-table collision.
- admits that E-E V3 prelaunch preparation opened the combined TRAIN/VALID/TEST export
  while retaining only TRAIN/VALID fields, and limits sequestration to fitting/selection;
- states that the public E-E V3 graph checks ledger schema, hash-string syntax, and
  uniqueness but does not read or hash the private files (the local adjudicator did);
- labels the E-E V3 comparator as a zero-initialized upstream-class SASRec-ID control,
  not upstream-default normal initialization, and leaves normal-init/equal-budget tests open;
- makes `PAPER_SUBMISSION.md` the sole canonical authored source and marks
  `PAPER_DRAFT.md` historical/noncanonical with a health-gated do-not-submit banner;
- separates Amazon and MovieLens ethics/sidecar governance, completes AlphaFuse
  proceedings metadata, and narrows TIGER preprocessing geometry to what its paper states.

The fail-closed graph now recomputes 201 active cells across 25 required families with
zero mismatch or untraceable cells. The E-E V4 normal-initialization sensitivity is now
complete and integrated. Its exact verdict is
`EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC`: normal-init SASRec-ID NDCG@10 is
0.043065 [0.042645,0.043486], and the V3 AlphaFuse-style package remains above it by
+0.005207 [+0.004779,+0.005635]. Normal initialization also exceeds the earlier V3
zero-init arm by +0.004042 [+0.003089,+0.004995]. This is prospectively frozen but
outcome-known, same-investigator, cross-campaign sensitivity evidence. Phase/date and
initialization are confounded; architecture, capacity, and parameter allocation remain
unequal. It is not independent confirmation, causal initialization isolation, an
equal-budget factorial, or SOTA.

Commit `4bda1169` passed the first full strict local replay: all 1,073 release-manifest files
verified, all governed adjudicators passed, and the graph recomputed 201 active cells
across 25 required families with zero mismatch or untraceable cells. The reader PDF is
57 pages with `scan: CLEAN`; the focused TORS and acmsmall mains are each 33 pages and
the reviewer supplement is 18 pages. All pages containing the new V4 text and Table 1b
were rendered and visually inspected without clipping or overlap. A separately hydrated
pristine replay at `ecccfb6e` then passed all seven stages: 407 release-only assets were
installed and hash-verified, the strict graph/adjudicator gate passed, all four governed
PDFs rebuilt byte-stably, 1,073 manifest files and 666 Git-backed entries verified, and
the tracked tree remained clean. The replay record is correctly
`clean_clone_draft_metadata_replay` / `release_ready=false` because human metadata and
legal review remain pending. The final status-doc replay, attestation-only child commit,
push, and release-manifest upload/download hash verification are the remaining machine
actions.

Do not stage user-modified `PAPER_REVIEW_AUDIT.md` or unrelated untracked QA/tmp files.
Human author/affiliation/country/contact/running-header metadata remains the literal
submission blocker and must not be invented. Substantive residual risks also remain:
same-investigator/outcome-known positive evidence, a negative MovieLens replication,
unequal architecture/training/tuning in current-baseline studies, venue mode/length,
final legal/conflict/funding review, and an immutable DOI-backed deposit.

The V4 campaign completed all 8/8 terminal trainings and 8/8 sealed evaluations with no
ledger errors. The committed adjudicator was the first authorized endpoint reader. The
next scientific work, if authorized after release closure, is an equal-budget factorial or
capacity-matched decomposition; it must be separately frozen and must not be described as
retrospective confirmation of V4.

---

# Previous handoff — AlphaFuse-style E-E V3 completed and integrated (2026-07-30)

The clean text+ID current-comparator campaign under `PREREG_EE_V3.md` completed
all 16 frozen training bundles and then all 16 sealed one-shot TEST evaluations
with zero ledger errors. The unchanged committed adjudicator at freeze commit
`f7c9c551d313de07b433545ed4887400ed4f4d98` was the first authorized endpoint
reader. Exact verdict: **`EEV3-REPORTABLE-OUTCOME-KNOWN`**. The outcome-visible
V2 port remains permanently `NONCOUNTABLE` and is never pooled with V3.

Exact TEST summaries (eight optimizer seeds per arm): AlphaFuse-style MiniLM
representation package NDCG@10 **0.0482725982**, 95% CI
**[0.0481293416, 0.0484158549]**; official-repository SASRec-ID backbone
**0.0390235314 [0.0381060954, 0.0399409675]**. The descriptive independent-arm
Welch difference is **+0.0092490668 [0.0083291897, 0.0101689439]**,
`p=3.47536e-08`. Against the existing six-seed full-model reference
0.0673373862, the package is **−0.0190647879 [−0.0193466568,−0.0187829190]**.
The fixed-split user-resample sensitivity is [0.00845198,0.01002793] and the
target-item-cluster sensitivity is [0.00480595,0.01574258]; neither is optimizer
or population inference.

Claims are deliberately narrow. This is countable, prospectively frozen but
outcome-known same-investigator current-comparator evidence for a whole
representation package under shared data/evaluation and one frozen training
configuration. MiniLM replaces AlphaFuse's published text vectors. Text
availability, initialization, trainable capacity, parameter allocation, and
architectures differ. It is not a published-table reproduction, paired
experiment, isolation of null-space fusion, equal-tuning evidence, independent
confirmation, or SOTA.

Integration is complete in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, the ACM TeX
sections/tables, `AUDIT_RESPONSE_2026-07-27.md`, `CANONICAL_SUBMISSION.md`, the
claim ledger/map, strict wrapper, and release-manifest updater. The graph now
recomputes **200 active cells across 24 required families** with zero mismatch
or untraceable cells. `EE_V3_OUTCOME_KNOWN` contains only the compact public
adjudication; private endpoints/sidecars are hash-ledgered with
`private_endpoint_replay=0` and record-level bootstraps are not publicly replayed.
The reader PDF renders 53 pages with `scan: CLEAN`; both ACM targets compile and
the review hygiene scan passes under the logged draft waiver. Visual QA of Table
0, Table 1b, results, discussion, and conclusion found no clipping or overlap.

Next actions: regenerate `RELEASE_MANIFEST.json` once more after the updated
claim map/handoff, run the full strict local wrapper, commit, rerun strict at the
commit, perform the separately hydrated pristine-clone replay, push, upload the
release manifest last to `v0.9-audit-evidence`, re-download/hash-verify it, and
disable the E-E V3 heartbeat. Preserve user-modified `PAPER_REVIEW_AUDIT.md` and
unrelated untracked QA/tmp files. Human author/byline metadata remains the only
literal-submission blocker and must not be invented.

---

# Previous handoff — WEARec current-baseline phase completed (2026-07-29)

The official-code WEARec campaign completed all two validation-only tuning runs,
eight fresh assessment trainings, and eight sealed one-shot evaluations with no
recorded errors. The committed adjudicator was the first authorized endpoint
reader after campaign completion. Exact verdict:
**`WEAREC-BELOW-EXISTING-REFERENCE`**.

Assessment-seed results under the shared paper evaluator:

- WEARec NDCG@10: 0.0591835101, 95% CI [0.0586740541, 0.0596929662];
- existing six-seed full-model reference: 0.0673373862, 95% CI
  [0.0670633678, 0.0676114045];
- unpaired Welch contrast: −0.0081538760, 95% CI
  [−0.0086894193, −0.0076183328], `p=1.15674e-11`.

The exact negative result is integrated into both manuscripts, Table 0, Table
1b, the audit response, discussion/conclusion/availability text, and the public
fail-closed graph. The graph now recomputes 198 active cells across 22 required
families with zero mismatches or untraceable cells, including the released WEARec
NDCG vectors, confidence intervals, Welch contrast, verdict, and endpoint-hash
ledger. Private endpoint extraction and unreleased HR/MRR seed-vector arithmetic
are not publicly replayed.

This closes only the **current frequency-baseline half** of audit item 4. It is
same-investigator evidence on an outcome-known split under equal evaluation;
architecture, loss, schedule, and tuning budgets differ. It is not independent
confirmation, a paired experiment, equal-training evidence, or a SOTA claim.
The clean AlphaFuse-style text+ID comparator remains open and is the next
empirical phase.

Preserve user-modified `PAPER_REVIEW_AUDIT.md` and unrelated untracked QA/tmp
files. Human author/byline metadata remains the external literal-submission
blocker and must never be invented.

Integration commit `b0c8c7db` and checkout-portability verifier commit
`346a3327` passed the full local strict gate and a separately hydrated pristine-
clone replay. All 407 release-only assets verified, both PDFs rebuilt
byte-identically, and the branch was pushed. `RELEASE_MANIFEST.json` was uploaded
last to `v0.9-audit-evidence`, re-downloaded, and matched SHA-256
`edad5b42a89f6097ca9e6513cb48786ac11bcc2577ca5e89e6532f6c10bdd61f`.
The WEARec heartbeat can now be disabled. The next empirical phase is the fresh
clean AlphaFuse-style text+ID comparator; do not reuse the outcome-visible V2
port as countable evidence.

---

# Historical handoff — canonical-FIR restructuring program (2026-07-25)

**State:** branch `codex/bestrec-sota-results`, HEAD `e055f9d0`, tree clean, all pushed. GPU **idle**.
Rollback point if needed: tag `pre-fir-restructure-20260725`.

## What just happened

Executing the maintainer's 10-phase plan to refocus the paper on ONE primary claim: the
canonical causal FIR module (see `PAPER_DEADLINE_PLAN.md` progress log for the running record).

1. **Phase 1 DONE (`eb538476` md, `34e78c53` tex):** the CANONICAL FIR — nonsingular,
   gradient-active, identity-initialized (`x' = x + DWConv_Δ(pad_left(x))`, Δ=0, no absorbing
   gate) — is now the *proposed method* in title + §3(b) + intro, in both papers. The historical
   zero-gated form is renamed **legacy zero-gated FIR package** and kept package-level only.
2. **Phase 2 DONE (`e055f9d0`): verdict `CANON-BREADTH-POS`, 2/2 categories PASS.**
   Prereg + adjudicator + driver were frozen and committed BEFORE launch (`a6775c6a`).

   | category | canonical FIR − identity | 95% CI | seeds | |
   |---|---|---|---|---|
   | Industrial_and_Scientific | +0.002110 | [+0.001820, +0.002399] | 8/8 | Holm-SIG |
   | CDs_and_Vinyl | +0.006150 | [+0.005849, +0.006450] | 8/8 | Holm-SIG |

   32/32 runs, matched per-seed init (`init_state_sha256` equality enforced), identity-control
   taps verified L2=0, one frozen config, **zero per-category tuning**. Canonical FIR isolation
   now holds on **three** categories (MI via E-A/`PREREG_FIR_V3`, + these two).
   Artifacts: `PREREG_FIR_CANONICAL_BREADTH.md`, `_bestrec_run/run_fir_canonical_breadth.py`,
   `_bestrec_run/adjudicate_fir_canonical_breadth.py`,
   `_bestrec_run/fir_canonical_breadth_adjudication.json` (verbatim verdict, committed).

## Next actions, in priority order

1. **Integrate the breadth verdict — NOT yet in the manuscript.** The numbers must become
   gate-bound cells in `_bestrec_run/build_hstu_tables.py` traceable to
   `fir_canonical_breadth_adjudication.json` (otherwise the strict gate flags them
   UNTRACEABLE), then prose in intro / §3(b) / §5.2 of **both** md and tex. Run the full RITUAL.
2. **Phase 3 controls — the other half of the acceptance gate; GPU is idle.** Needs new trainer
   arms (fixed causal moving-average, fixed causal high-pass, channel-shared FIR,
   parameter-matched causal-conv comparator), all identity-at-init + gradient-active + shared
   backbone init + equal tuning budget. **Freeze a new prereg + adjudicator BEFORE launch.**
3. **Phase 6 rewrite (CPU, parallel with GPU):** cut 55pp → ~25pp; relocate EASE / sparse-warm
   fusion + Office VOID chronology + titrations to the supplement; demote TAPE to a supporting
   ablation; replace the self-assigned "novelty grade" column with **claim boundary**; align
   conclusion + results headings to the canonical method; strip audit-log prose; state
   "no general SOTA claim" ONCE.
4. **Phase 4 mechanism:** causality unit test (CPU, cheap — do it early); learned-tap /
   frequency-response plots; local-order intervention retrain (GPU).
5. **Phase 7–9:** two reproduction paths + claim-to-artifact map; manuscript-matched deposit tag;
   mock reviews; cover letter.

## Non-negotiables (do not relax)

- **HARD RULES:** never delete/overwrite `results_*.json` (rename-preserve only); never modify
  `external/HSTU-BLaIR`; never edit audit files beyond `git add`; **one GPU job at a time**;
  claims may only NARROW — new claims enter ONLY via a new frozen pre-registration committed
  BEFORE launch, with its mechanical adjudicator.
- **CLAIM BOUNDARY** (`CANONICAL_SUBMISSION.md` governs): two counted comparisons only —
  Musical_Instruments (vs published 0.0406) and Office_Products **V3** (vs 0.0271 published AND
  0.0279 environment-matched regeneration). Office **V1 is VOID/descriptive forever**; TFV2 is
  outcome-visible, **not** confirmatory.
- **The breadth result is an INTERNAL matched-init filter-vs-identity contrast.** Not SOTA, not a
  comparator claim, not paired/distributional superiority. Do not upgrade its wording.
- **FORBIDDEN anywhere:** SOTA of any kind, "significantly better than HSTU-BLaIR",
  "official/pinned reproduction", training-level equivalence, Office V1 as passed, Office V3
  beyond frozen wording, TFV2 as confirmatory. Reference-implementation runs stay
  "environment-caveated single-run regenerations". Never weaken a caveat to close a finding.
- **RITUAL after edits:** `build_hstu_tables.py --write-manifest` (if cells changed) →
  `render_paper_pdf.py` must print `scan: CLEAN` → mirror to `paper_tex/` and
  `bash paper_tex/build.sh` must PASS (H1–H9) → `update_release_manifest.py --regen` (if a
  manifested file changed) → commit → `rebuild_hstu_submission.py --strict` **exit 0** →
  push → `gh release upload v0.9-audit-evidence RELEASE_MANIFEST.json --clobber`.

## Known blockers

- **Author byline is a placeholder** (`paper_tex/paper-shared.tex:37`) — HUMAN TODO. The paper is
  ~0% submittable until filled; `build.sh` H10 fails strict and currently needs `--draft`.
- Deposit (v1.1.12) should be cut only **after** byline + manuscript stabilization; DOI minting
  needs the maintainer's account.
- Negative/failed outcomes are reported with the same prominence as wins. If Phase 3 shows fixed
  averaging matches learned FIR, the claim narrows to "simple causal local filtering suffices" —
  narrow it immediately rather than adding seeds until a threshold is crossed.
