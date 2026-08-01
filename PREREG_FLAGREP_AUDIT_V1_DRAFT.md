# PREREG (DRAFT) — Flag-Replication Audit V1 — drafted 2026-08-01

**STATUS: DRAFT — NOT FROZEN.** Freezes only after user go/no-go (standing 95%-checkpoint rule). Until frozen, nothing here binds; after freezing, deviations require errata, per repo convention.

## Research question

**RQ1 (headline, clean data):** Do the interaction sets flagged as noise by published denoising recommenders replicate across training seeds — at the methods' own operating points, under their own published configurations?
**RQ2 (selection profile):** What do the flags select — injected-noise capture under multiple noise models, and degree/popularity profile of flagged sets?
**RQ3 (consequence):** Does a method's flag stability predict its robustness gain over properly tuned ERM (the RecSys 2025 audit axis), mechanistically linking non-replication to the tuned-ERM-parity finding?

## Positioning (from verified screens, tasks `wqnz0f2qa` + `wfko4i2l0`)
- Unoccupied in recsys; phenomenon + Jaccard metric precedented in vision by f-INE (ICLR 2026) — contribution is the recsys instantiation (no ground-truth labels, popularity confounds, loss-based rather than influence-based flags) + field consequences. Mandatory citation stack: f-INE; Summers & Dinneen (ICML 2021); Nguyen et al. (NeurIPS 2023); Basu et al.; Karthikeyan & Søgaard (arXiv); Deng et al. (workshop); Epifano et al. (2023); RecSys 2025 audit (10.1145/3705328.3748153).
- Never claim the phenomenon, the metric, or "first fragility result" as novel.

## Design

**Audited methods (official code wherever it exists; commit-pinned):** ADT (T-CE and R-CE; WSDM 2021), DeCA, DCF (Double Correction), SVV (KDD 2025). Stretch: BOD. Reference flaggers (controls): random matched-size subsets; degree heuristic (−item-degree; must appear per CRI-pilot lesson); plain high-loss ranking.
**Backbones:** as in the original papers (GMF, NeuMF; LightGCN where the official code supports it). No home-grown simplifications for audited methods.
**Datasets:** the audited papers' own — ML-1M, Yelp, Adressa; Taobao-buy as out-of-suite addition.
**Seeds:** 5 per (method × dataset) → 10 pairwise comparisons; everything else pinned to published configs.

**Endpoints:**
- **E1 (headline; clean data, no injection):** cross-seed flag-set Jaccard at each method's own drop rate; distribution over 10 pairs vs matched-size random baseline k/(2−k). Declared reading: median Jaccard < 2× random ⇒ "does not replicate"; > 0.5 ⇒ "replicates"; between ⇒ "partially", reported as measured.
- **E2:** score-level agreement — Spearman, Kendall, and top-k overlap curves (k ∈ {1, 5, 10, 20}%).
- **E3 (injection arms only for selection profile):** uniform, popularity-matched, and exposure-model noise; capture precision/recall @ method operating point.
- **E4 (consequence):** per method × dataset, robustness gain over tuned ERM (RecSys 2025 protocol) vs E1 stability; report association, no causal claim beyond correlation + mechanism narrative.
- **Epifano-proofing:** (i) headline on clean data (no retraining-based ground truth involved); (ii) multiple agreement metrics; (iii) positive control — the degree flagger must show near-1 Jaccard (protocol CAN register stability); (iv) negative control — random flagger at baseline.

**Pre-declared gates:**
- **A1 reproduction:** each audited method's official code reproduces its published headline metric within the tolerance its own paper's variance implies, before any stability claim about it. Failures excluded and reported as reproduction failures, not instability.
- **A2 decisiveness:** E1 verdict consistent across ≥2 datasets for ≥3 methods, else the paper is not claimed and results are logged.
- **A3 compute:** ≤ 40 GPU-hours total on M4 Max (est. well under; probe extrapolation ~10–15h). Overrun ⇒ scope cut is logged before, not after.

**Out of scope:** proposing a new denoiser; unlearning claims; natural-noise ground-truth claims; any per-interaction detector claim (CRI lesson).

**Venue target:** RecSys (reproducibility/audit track) primary; TORS alternate. Pre-submission kill-query re-screen mandatory (moving field; f-INE is 4 months old).

## Escalation
User approves ⇒ freeze this file (strip DRAFT), then A1 reproduction phase first; E1–E4 only after A1. Results adjudicated mechanically; paper drafting only if A2 passes.
