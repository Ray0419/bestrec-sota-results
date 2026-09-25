# Consolidated inventory — everything this program has, ranked (2026-09-09)

One page to rule the sprawl. Every asset below is classified **ALIVE** (publishable, with venue),
**SUPPORTING** (feeds an ALIVE asset, not standalone), or **DEAD** (refuted/pre-empted — never claim).
Authority order for numbers: `poc_out/*.json` via the frozen analyzers > section docs > skeleton.

## Tier 1 — submission-ready publications

| # | Asset | State | Where | Blocking items (all human) |
|---|---|---|---|---|
| 1 | **TORS measurement paper** (exchange-rate p\*, offset-matched efficiency ratio 1.61±0.07, within-pool AUC instrument, temporal protocol with MI/VG/Steam crossover prediction, knowledge≠rankability across 2 loss families × 5 arms × SID replication, SXL §6.8) | **strict rebuild gate PASS** (201 cells, 25 families, manifest 1081 files); PR #1 carries manuscript v3.8 | main checkout `paper_tex/`, PR #1 | authorship; gate-A0 ranking spot-check; submit |
| 2 | **ρ(k)/π\* RecSys short** — "Coverage Was Never the Binding Constraint" | **typeset 4pp ACM sigconf, anonymous, zero overfull**; C1 supported (both datasets, Steam n=5); pre-registered E2 refutation as first-class result | worktree `paper_tex_rhok/` (+ `PAPER_RHO_K_SHORT_V1.md`, skeleton v3) | complete 11 bib placeholder entries; resolve the two [HAS/HAS NOT] boxes in `AUTHORSHIP_AI_STATEMENT.md`; RecSys 2027 CFP re-check (~Apr) |

## Tier 2 — supporting assets (fold, cite, or reuse; not standalone papers)

- **Best empirical result we hold:** HSTU-BLaIR per-category 5-seed CI lower bounds **0.04096 (MI) / 0.03033 (Office)** vs highest published anchors 0.0406 / 0.0271 (`COMPARATOR_LANDSCAPE_2026-09-08.md`; SID-MLP 0.0332 / Latte 0.0331 are sequence-truncated, not interchangeable). **Licensed wording only:** "no published NDCG@10 above the anchors located as of <date>" — "SOTA" is forbidden vocabulary per CANONICAL_SUBMISSION. Lives inside the TORS paper.
- **Novel experimental-design algorithms** (our only surviving "algorithms"; both are procedures, not models):
  (a) **multi-dose single-run knockdown** — disjoint item groups at different degree-caps inside ONE run; 6× cheaper and kills the capacity-reallocation confound;
  (b) **forced-coverage ρ(k) measurement** — gold-injected pools, degree-resolved conditional conversion, structural gates G1/G2; plus the quota-mix `poc_coverage_trade.py` validation harness.
- **SXL level effect** (gBCE tail = 6–79% of full-CE in all 10 cells) → TORS §6.8 via `SECTION_SXL_DRAFT.md`.
- Instruments: within-pool AUC; degree-sliced eval (`by_degree`); 378 per-user sidecars (zero-GPU retro-analysis); temporal global-time protocol (credited to the parallel session).
- E2's competition-displacement finding (measured ΔS positive at λ=0.1–0.5 while segment-additive prediction is negative) — the short paper's §4 centrepiece.

## Tier 3 — dead. Never claim; cite the corrections log instead

- **Every trained/algorithmic fix attempted (6 logged failures):** EB posterior gate; text-kNN/ridge imputation as deployable; content-anchor T1; pseudo-cold dropout T2a/T2b (within-pool CE as loss); z-fusion at any weight; spectral denoising (GD1/X1); moonshots BBP & CR-UOT.
- **β-attribution of tail damage** (refuted on Steam: sCE tail = 4× fCE); **H2 scale×loss interaction beyond lr=1e-3**; **aggregate-blindness selectivity beyond MI**; **H4 amplification estimator** (ratio blows up, 38.9×/69.7× at d128); **π\*(k,K) as a deployable slot-mix rule** (P1 refuted 0/5 both datasets — screen only); **√N law** (design artifact; true exponent 0.843±0.015); "text improves coarse but not top-rank" (survives only as ~4× asymmetry); k-dial threshold as discovery (pre-empted by arXiv:2508.07856).
- Pre-empted framings never to claim: coverage×conversion decomposition; gold-injection protocol; "downstream-utility-aware allocation"; "aggregate hides popularity bands"; suppression-axis mechanism as discovery.

## Direct answer to "strongest methodology/algorithm we can publish"

1. **Strongest overall: Tier-1 #1 (TORS paper).** Deepest evidence base (hundreds of runs, three
   datasets, crossover prediction validated in sign at/below/above break-even), gated, manifested.
2. **Strongest per-page and fastest out the door: Tier-1 #2 (ρ(k) short).** Single novel instrument
   with per-claim verified boundaries and a pre-registered refutation that strengthens it.
3. **A novel model/training algorithm: we do not have one.** Six attempts, six logged refutations —
   that record is itself part of Tier-1 #1's argument. The surviving algorithm-shaped contributions
   are the two experimental-design procedures in Tier 2, published as methodology inside #1/#2.

## Housekeeping state (2026-09-09)

PRs #1/#2/#3 all OPEN + CLEAN. Worktree tree clean after this commit (`paper_tex_rhok/build.log`
now ignored). Strict rebuild gate PASS at `codex/cleanresearchwithskill` HEAD. Heavy artifacts
(18.6 GB `.pt`, 444 MB sidecars, 2.1 GB filter_overparam, 345 MB npy) intentionally untracked.
