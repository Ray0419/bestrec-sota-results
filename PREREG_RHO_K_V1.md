# PREREG: degree-indexed conversion ratio ρ(k) and the coverage break-even π*(k,K) (V1)

**Frozen 2026-08-18, before the confirmatory matrix runs and before any π\* value is computed.**

**Disclosure of what was seen before freezing.** The falsification rule below was frozen in
`DESIGN_RHO_K_MATCHED_COVERAGE.md` *before any evaluation ran*. Instrument validation then ran ONE
checkpoint (fce_d256_MI_seed20260736, stride 4): both structural gates passed; R_forced was observed
increasing in k with R(k=0) ≈ 0.0003. No π\* value has been computed, no other seed or dataset has
been read, and the falsification rule is retained unchanged from the design doc.

## 1. Claims under test

- **C1 (primary).** Under forced coverage, the conversion ratio ρ(k) = R(k)/R_warm is < 0.5 in every
  bucket k ≤ 10, on MI and Steam (fCE arm, primary LR). Equivalently: the low-degree buckets convert
  at less than half the warm rate even when coverage is handed to them for free.
- **C2.** Substituting ρ(k) into π\*(k, K) = c_cov / (g_cov·ρ(k) + c_cov) with arXiv:2606.29947's
  published coverage trade (Yelp g=+10pp, c=−4.5pp; VideoGames g=+2.2pp, c=−4.7pp) yields
  π\*(k≤10, K=200) > 90% on both datasets — i.e. no plausible cold-target prevalence justifies buying
  coverage for sub-threshold items.
- **C3 (instrument, descriptive).** R_nat > R_forced in mid buckets — the natural-coverage selection
  bias of weakness 5.1 is directly measurable and materially large (reported, no significance test).

## 2. Falsification (carried unchanged from the design doc)

The thesis "conversion, not coverage, is the binding constraint" is **refuted** if ρ(k) > 0.5 for any
bucket at k ≤ 10 on either dataset (n-weighted seed mean). If refuted, we report that coverage-side
allocation can pay for those buckets and the position paper is not written.

## 3. Matrix (confirmatory)

| set | checkpoints | n |
|---|---|---|
| MI primary | `results_SXL_fce_d256_MI_seed{20260736..40}` | 5 |
| MI secondary | `results_SXL_fce_d64_MI_seed{20260736..40}` | 5 |
| Steam | `results_SXL_fce_d256_STEAM_seed{20260736..38}` | 3 |

All at `--event-stride 2`, K ∈ {100, 200, 500, 1000}, K=200 primary, both retrievers (text, pop),
text primary. Seed 736 MI is re-run at stride 2 (the stride-4 smoke read is discarded from analysis).
R_warm = event-weighted pooled hit over k ≥ 51 within the same retriever's pools. gBCE/sCE arms are a
robustness appendix only, not confirmatory.

## 4. Analysis rules

- ρ(k) per bucket: n-weighted across seeds; CI from per-seed values (t, df = n−1), two-sided α=0.05.
- C1 decision: upper CI bound of ρ(k) < 0.5 for every k ≤ 10 bucket → supported; point estimate < 0.5
  but CI crossing → "directionally consistent, underpowered" (no claim); any point estimate > 0.5 →
  refuted per §2.
- C2 is arithmetic on C1's estimates plus cited constants; no new test. Reported as a table over
  (k, K) with both datasets' constants.
- k = 0 reported but flagged as the degenerate bucket (prior work: exactly-zero cold NDCG).
- Both structural gates (G1 pool ≥ full; G2 monotone in K) must pass in every run; a gate failure
  drops that run and is reported.

## 5. Positioning constraints from the novelty verdicts (2026-08-18)

- Do NOT claim "downstream-utility-aware allocation" (CAPTS arXiv:2602.12564 owns the framing;
  verified CLEAR on the closed-form break-even and the degree axis specifically).
- Do NOT claim the gold-injection protocol (arXiv:2604.16318's positive-controlled regime; ours is
  the degree-sliced ρ(k) read on top of it).
- arXiv:1601.04745 verified CLEAR (POMDP exploration budget per single cold target; unrelated
  structure). arXiv:2605.27439 verified NOT A THREAT (LLM brand nomination; prominence ≠ degree; no
  decision rule; conversions 25–52%).
- Cite arXiv:2508.07856 for cold-warm thresholds; our π\*(k,K) is an admission RULE, their k is a
  measured transition point.

## 5a. AMENDMENT A1 — internal-consistency endgame E1–E4 (frozen 2026-08-19, before any E-run)

**Why.** The main π\* table combines OUR ρ (MI/Steam) with 2606.29947's coverage trades (Yelp/VG) —
the mirror image of the transplant our own weakness 5.4 forbids. E1–E4 close this and validate the
rule end-to-end. All predictions below are frozen before any E-cell runs.

- **E1 (own-dataset coverage trade).** Quota-mix retriever at K=200: text slots take priority with
  n_text = round(λ·K), remainder filled from popularity ranking skipping duplicates (declared,
  exact). λ ∈ {0, 0.1, …, 1.0}. NO forced gold. Measure Cov_b(λ) per degree bucket and end-to-end
  success S(λ) (gold in pool AND top-10 of pool). g/c defined vs λ=0.
- **E2 (PRIMARY validation).** Predicted ΔS_pred(λ) = Σ_b w_b·ΔCov_b(λ)·R_b, with R_b the
  FORCED-coverage per-bucket conversion from the confirmatory matrix and w_b event shares.
  **P1 frozen: sign(ΔS_meas(λ)) = sign(ΔS_pred(λ)) for every λ with |ΔS_pred| above seed noise, on
  MI and Steam.** P2 (secondary, loose): magnitude ratio pred/meas ∈ [0.5, 2] at the largest-|ΔS| λ.
  **If P1 fails, forced-coverage R does not transfer to realistic pools and the rule's
  DEPLOYABILITY is refuted — reported as such, headline demoted to the measurement claims.**
  Note the direction is NOT presumed negative: the text retriever also covers warm targets better
  than popularity, so mixing may raise warm coverage; the formula predicts whatever it predicts.
- **E3 (Steam n=5).** Add seeds 20260739/40 (full 12-cell steam stage-2 for the SXL section as a
  side benefit). Prediction: new-seed ρ(k) within the n=3 CIs; C1 unchanged.
- **E4 (coverage-unit drift).** Re-run pool_conv on the inner window (0.60–0.75 band). Prediction
  (conservative): π\*(k) moves by >5pp in at least half the k ≤ 20 buckets; direction recorded and
  compared with F01's always-optimistic NDCG-unit finding, not presumed.
- Appendix: ρ(k) for gBCE/sCE d256 MI checkpoints (robustness, descriptive).

**Not permitted:** re-tuning λ grid, K, bucket edges, or the C1/C2 definitions after seeing E-data;
using E1's trades to retroactively soften the reported C2 partial failure (C2 stays failed as
registered; E1 gets its own fresh table).

## 6. Cost

13 eval passes, no training, ~3–5 min each. One overnight fraction; runs in background with
skip-if-exists resume.
