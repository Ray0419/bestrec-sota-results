# PREREG: global-time re-verification of the three verified results (V1)

**Frozen 2026-08-07, before any run of this design.** Loop 3 of [PROJECT_LOOP_PLAN.md](PROJECT_LOOP_PLAN.md); scoped in [LOOP3_SCOPE.md](LOOP3_SCOPE.md).

**Protocol attribution.** The global-time protocol — pooled interaction-time quantile cutoffs, first-observed-interaction as catalog-arrival proxy, cold = first appearance after cutoff, and the first-availability candidate constraint — is the parallel session's design, implemented by them in `_bestrec_run/run_poc_temporal_lc2c_v1.py`. This work **ports their protocol semantics** to a sequential backbone at larger scale. The protocol contribution is theirs and is cited as such; nothing here claims it.

---

## 1. Questions

**Q1 (validity).** Do the three verified results — within-pool AUC gain, offset-matched efficiency ratio > 1, and the break-even p\* — survive a temporally valid protocol, or were they artifacts of leave-one-out evaluation?

**Q2 (decision-relevance, new and primary).** Under *observed* cold prevalence, does text-kNN imputation actually pay? Leave-one-out could not ask this: cold prevalence had to be imposed. The global-time protocol makes π_t observable (measured: **MI 20.6%, VG 52.4%** at q=0.75), so the aggregate effect on realistic mixed traffic is directly measurable.

## 2. Design

- **Datasets:** Musical_Instruments (primary), Video_Games (second regime — π_t = 52.4% vs 20.6%).
- **Cutoffs:** two-stage, pooled interaction-time quantiles. **q=0.60 for any selection**, **q=0.75 for reporting.** No quantity reported at q=0.75 may be used to choose anything.
- **Cold:** natural arrival only — an item is cold iff its first observed interaction falls after the cutoff. **No artificial capping.**
- **Training set:** interactions with timestamp ≤ cutoff. User histories built from pre-cutoff interactions only.
- **Evaluation set:** post-cutoff events whose user has ≥1 pre-cutoff interaction (users without history are excluded, not scored as cold-start users).
- **First-availability constraint (enforced):** at an event with time *t*, an item may be a candidate only if its first observed interaction ≤ *t*. Scoring against items that did not yet exist is the primary validity threat this protocol removes.
- **Arms:** text (`--text-sim-bias --text-prototypes 512`) and ID-only (`--no-sbert`), initialization-paired within seed.
- **Seeds:** MI 5 (20260736–40), VG 3 (20260736–38).
- **Declared limitation (adopted from their PoC):** the 5-core property was established globally; under a time cut some items/users fall below 5 pre-cutoff interactions. Re-coring inside the window would change the item population and break comparability with every prior run, so the existing 5-core files are used and this is stated, not hidden. First-appearance is a catalog-arrival *proxy*, likewise declared.

## 3. Endpoints and decision rules

All statistics are across-seed t-intervals on per-seed means with sign counts (house convention). Both instruments are already pool-size- and offset-invariant, so they are used unchanged.

**E1 — within-pool AUC gain** (offset-invariant genuine cold relevance).
*Confirmed iff* mean > 0 with all seeds positive and the 95% CI excluding 0.

**E2 — offset-matched efficiency ratio.**
*Confirmed iff* the 95% CI **excludes 1.0** with all seeds > 1.0.

**E3 — break-even p\*** = |c|/(g+|c|), reported with its CI.

**E4 — PRIMARY: aggregate effect at observed prevalence.** The temporal eval already carries natural π_t, so the overall NDCG@10 change from applying imputation to the full mixed-traffic eval **is** the answer; no extrapolation is required.
*Imputation pays iff* the mean overall change > 0 with all seeds positive and the 95% CI excluding 0. The consistency check π_t vs p\* must agree in sign with E4; disagreement indicates a measurement error and blocks reporting until resolved.

**Pre-declared interpretations — all three are results, none is a failure:**
- E1/E2 replicate → the instruments and the coarse-signal finding are temporally valid.
- E1/E2 shrink or vanish → **that is the finding.** This protocol is more honest than LOO; a shrinkage result is reported as the headline, not buried.
- E4 negative at π_t = 20.6% but positive at 52.4% (or vice versa) → prevalence regime, not method quality, decides; report the crossover.

**Kill criteria.** No re-cutting of quantiles, no dropping seeds, no switching datasets, and no post-hoc metric substitution to rescue any endpoint. If the smoke test (§4) fails, the pipeline is fixed and the campaign restarts from seed 1 — partial results from a broken pipeline are discarded, not patched.

## 4. Validity gate before the campaign

A single-seed MI smoke run at q=0.75 must produce **sane absolute metrics** (overall NDCG@10 within roughly 2× of the LOO-era MI values, ≈0.03–0.05). A temporally split model scoring near zero means the pipeline is wrong — not that cold start is hard. The campaign does not start until this passes.

## 5. Complexity budget

Bucketed availability masking (availability is monotone in time; one mask per time bucket via `searchsorted`, O(buckets × items) rather than O(events × items)). MI: 10 runs ≈ 1.5 GPU-h. VG: 6 runs ≈ 2.5 GPU-h. Decompositions ≈ 1 GPU-h. Text-arm checkpoints only. GPU probe before every launch; the parallel session's lock stays untouched.

## 6. What this still cannot establish

Generality beyond two Amazon categories; any method other than text-kNN imputation; and — because first-appearance is an arrival proxy rather than a true catalog-availability record — exact deployment timing semantics.
