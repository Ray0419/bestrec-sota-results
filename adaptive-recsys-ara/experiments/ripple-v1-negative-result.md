# RIPPLE v1 PoC — Verified Negative Result

**Decision:** `DEAD_END`; design killed under the preregistered rule. Phase 5 is forbidden for RIPPLE v1.

## Provenance

- Protocol commits: `72c932fc`, verifier-only patches `6dd04251` and `59cb0709`.
- Completed run: `ripple-poc-v1-20260806T151915122332Z-3c42fceedbb9`.
- Result SHA-256: `69c7c14c2b76bf48abf363a3cd3eea5273982df931a866ba875004faea960e10`.
- External completion marker SHA-256: `784c8bda20ea514db45f39bde9902fa7a6ed837682cecd87f8d7e1186147cd1d`.
- Completion checks: runner PID exited; lock released; async ledger empty; 447 candidate-bound artifacts verified; stdout/stderr bound; item and index hashes unchanged.
- Scope: 100,000 MovieLens ratings, 1,682 items, 801 eligible users, 12,000 training preference examples, three optimization seeds.

## Aggregate test metrics

| Method | NDCG@10 | Recall@50 | Future-dislike intrusion@10 |
|---|---:|---:|---:|
| Frozen SentenceTransformer + FAISS | 0.005729 | 0.093633 | 0.003689 |
| Random-negative adapter | 0.008499 | 0.051186 | 0.000342 |
| Exact-hard adapter | 0.011554 | 0.070745 | 0.001776 |
| RIPPLE ANN-boundary adapter | 0.011350 | 0.068664 | 0.000273 |
| BPR-MF | 0.062559 | 0.347066 | 0.005874 |

RIPPLE nearly doubled NDCG over the weak frozen semantic baseline (+98.1%) and reduced held-out dislike intrusion, but its Recall@50 fell 26.7% relative to frozen and its NDCG reached only 18.1% of BPR-MF. It was 1.76% below the exact-hard adapter. The paired bootstrap interval for RIPPLE minus frozen NDCG was `[-0.000654, 0.012244]`, so the apparent gain was not statistically resolved.

## Preregistered gate

| Gate | Result | Evidence |
|---|---|---|
| G1: ≥5% NDCG gain and positive CI | **FAIL** | Relative gain +98.1%, but bootstrap lower bound −0.000654. |
| G2: ≥1% over random and exact-hard | **FAIL** | +33.5% over random; −1.76% versus exact-hard. |
| G3: ≥90% of BPR-MF NDCG | **FAIL** | 18.1%. |
| G4: Recall@50 not below frozen | **FAIL** | 0.0687 versus 0.0936. |
| G5: dislike intrusion not worse | PASS | 0.000273 versus 0.003689. |
| G6: every-seed p95 ratio ≤1.25× | PASS | Ratios 0.932, 0.959, 0.952. |
| G7: item/index hashes unchanged | PASS | All before/before-test/after hashes identical. |
| G8: ≥2/3 seeds beat frozen NDCG | PASS | 3/3. |

All fail-closed integrity checks passed, including a 100% genuine IVF-boundary source rate and a 488-user future-dislike cohort.

## Diagnosis without post-hoc tuning

1. **Representation bottleneck dominates.** Text-only title/genre embeddings contain little collaborative information; a global query rotation cannot reconstruct user–item interaction structure learned by BPR.
2. **Preference discrimination traded away candidate coverage.** Every adapter increased top-10 concentration while lowering Recall@50, indicating the pairwise objective sharpened local ordering but damaged retrieval support.
3. **ANN conditioning was not the active ingredient.** Exact full-matrix hard negatives slightly outperformed IVF-boundary negatives; the proposed systems-specific mechanism did not survive its matched control.
4. **The systems premise was feasible, not the learning premise.** Latency, immutable indexing, and dislike safety passed, so a successor should preserve fixed-index serving while replacing the text-only representation/alignment mechanism.

## Mandatory action

RIPPLE v1 is permanently marked `dead_end`. No Phase 5 abstract or contribution claim may be based on it. The autoresearch outer loop returns to Phase 1 and must select a direction that retains collaborative signal and explicitly prevents preference alignment from reducing candidate coverage.
