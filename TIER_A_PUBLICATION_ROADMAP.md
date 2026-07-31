# Tier-A journal publication roadmap

Status: active risk-reduction plan, updated 2026-07-31. This is not an acceptance
forecast and does not upgrade any evidence class.

## 1. Current position

The repository and paper are mechanically unusually strong: the V4 result is
integrated; 201 active cells across 25 claim families recompute with zero
mismatch/untraceable cells; all governed PDFs build; and a separately hydrated
clean-clone attestation passes. The scientific package is still mixed:

- positive outcome-known Amazon FIR estimates and matched-control evidence;
- one favorable but same-investigator, cross-campaign normal-init comparator
  sensitivity;
- a prospectively frozen negative MovieLens transfer result;
- unequal architecture/capacity/tuning in several current-system comparisons;
- no external custody or independent replication.

That is credible for a bounded modular-contribution paper, but not yet a safe
Tier-A submission. The working conditional estimate remains about 35–50% at a
well-matched strong journal after human metadata are completed; 65% is not yet a
defensible estimate.

## 2. Venue gate

There is no universal Tier-A label. The target is not final until the maintainer
records the ranking system and edition used by the institution. The 2025 ABDC
review is itself a changing list process, and a new specialist journal may not
yet appear even when its scientific quality is high.

Provisional scientific-fit shortlist:

| Journal | Scientific fit | Ranking treatment |
|---|---|---|
| ACM Transactions on Recommender Systems (TORS) | Highest topical fit; explicit focus on rigorous recommender evaluation | Do not call Tier A until exact institutional list/edition and ISSN 2770-6699 are verified |
| ACM Transactions on Information Systems (TOIS) | Strong if reframed around information access/retrieval significance beyond one module | Verify exact institutional ranking; higher breadth/impact burden than TORS |
| Information Processing & Management | Plausible information-retrieval/recommendation fit | Verify exact list/edition and scope before conversion |
| Decision Support Systems | Possible only with a credible decision-support contribution, not benchmark accuracy alone | Verify exact list/edition; current paper may be a scope mismatch |

Primary-source venue requirements and ranking evidence must be saved in a
target-specific checklist before submission. The current `VENUE_PLAN.md` remains
TORS-first for scientific fit, but that choice alone does not satisfy the new
Tier-A constraint.

## 3. Why the next work is scientific, not cosmetic

The 2026 TORS methodological guidance places special weight on complete
experimental-pipeline artifacts and systematic baseline selection/tuning. This
repository is strong on artifact completeness but still exposed on comparison
fairness. More polishing cannot repair that. The highest-value work is:

1. isolate the core FIR temporal-access question with a closer control;
2. equalize and document tuning/search budgets for strong simple and current
   baselines;
3. add a genuinely new non-Amazon domain, preferably under external custody;
4. only then perform the final journal-specific rewrite.

Reference: ACM TORS, "Improving Methodological Standards in Recommender Systems
Offline Evaluation" (2026), <https://doi.org/10.1145/3800587>.

## 4. Phase plan

### Phase A — exact-input temporal control

Draft protocol: `PREREG_FIR_TEMPORAL_ISOLATION_V1_DRAFT.md`.

Keep the parameter tensor, zero initialization, activation, channel map,
optimizer, backbone initialization, data, selection rule, evaluator, and budget
identical. Change only the input tensor supplied to those K tap weights:

- lagged arm: the K true left-causal states;
- repeated-current control: K copies of the current state.

This is a much closer test than the prior DCT/GELU pointwise placebo. It can show
whether the lagged-input arm outperforms that exact repeated-current control. It
still cannot establish universal temporal necessity, dataset generalization, or
independence. Claude must approve the estimand and identify any residual
identifiability objection before freeze.

### Phase B — fair tuning matrix

For each selected dataset, preregister equal validation-only search budgets and
search spaces for:

- popularity and nearest-neighbor/linear baselines;
- SASRec and the paper's HSTU-style identity backbone;
- the FIR intervention and exact-input control;
- at least one current frequency/long-convolution/state-space method whose
  official implementation supports the same task.

Record search space, number of configurations, seeds, early-stopping rule,
wall-clock/GPU budget, selected values, failed configurations, and full-catalog
evaluation semantics. No method receives a result-dependent rescue budget.

### Phase C — new non-Amazon study

Dataset selection must occur before inspection of the target split outcome and
must pass license, retention, redistribution, and cohort-definition review.
Prefer an established public sequential-recommendation dataset with enough
items/users for meaningful full-catalog evaluation. Freeze preprocessing,
cutoff(s), inclusion rules, candidate universe, tuning budget, primary contrast,
and all negative/null wording. If feasible, an external collaborator should
hold the TEST key/endpoints and run or attest the adjudication.

MovieLens remains in the paper regardless; a new positive result does not erase
its negative outcome.

### Phase D — checklist and manuscript compression

Claude audits the complete study against the TORS methodology checklist. Codex
closes reproducibility gaps. The main article is then rewritten around:

1. one primary question about what temporal FIR input contributes;
2. the closest matched control;
3. heterogeneous Amazon and non-Amazon outcomes;
4. fair-baseline results;
5. a concise boundary explaining when the module should be optional.

Historical campaign chronology remains in the supplement/artifact, not the
main narrative.

### Phase E — human and archival closure

The maintainer supplies real author/contact/ranking/legal fields. Rebuild without
the draft waiver, approve an accurate venue-compliant disclosure of AI use in
research design, code, analysis, validation, and writing, obtain Claude's final
red-team memo and Codex's clean-clone attestation, create an immutable
release/tag, download/hash-verify it, and submit to only one venue at a time.

## 5. Advancement rule

Do not claim the paper has reached a 65% acceptance probability merely because
these phases are executed. Re-estimate only after their outcomes are known. A
reasonable advancement gate is:

- matched temporal-control primary contrast adjudicated;
- symmetric tuning matrix complete with no baseline rescue asymmetry;
- at least one new non-Amazon study complete and MovieLens retained;
- full TORS/target checklist audited;
- ranking authority, all human/legal metadata, and the AI-use disclosure supplied;
- waiver-free clean-clone release passes.

If Phase A or C is null/negative, publish the falsification boundary honestly and
reconsider venue/claim scope rather than adding seeds or changing the hypothesis.
