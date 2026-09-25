# RAVEL v1 PoC Result: Killed

Date: 2026-08-07

## Authoritative decision

RAVEL v1 is killed. Phase 5 is prohibited and the autoresearch outer loop returns to Phase 1, cycle 4. There will be no outcome rerun, threshold repair, cohort substitution, or post-outcome source change.

The source-bound runner completed once on the prospectively disjoint MovieLens 1M cohort and produced a hash-valid candidate result with `PROMISING=false`. The post-exit verifier then failed closed before scientific replay because the runner stderr contained a SentenceTransformer weight-loading progress bar. Therefore no `EXTERNAL_COMPLETE` marker exists, external G10 fails, and the numerical results below are explicitly **runner-candidate evidence, not an externally verified completion**. This distinction cannot rescue the project: the locked runner already failed four scientific/operational gates, and incomplete external verification independently kills it.

## Run provenance

- Preregistration commit: `9ac91ade030c5c2acdec7a1bffb76532e264560a`
- Run ID: `ravel-poc-v1-20260806T180639143183Z-f9e6c2ffb44c`
- Runner result: `result_988c7b9ed28db689_seq001.json`
- Result SHA-256: `535bbb68bf3ff045f92eeaab0d0c5d7631ccd85495781a12f3b50c02d253573a`
- Runner completion candidate SHA-256: `de73d1d2e09a9fb5606e6fbba8fc12d0742aa7967f4a1100729d324a2242274b`
- External failure record SHA-256: `710a100366e52da1a15b3c0ac1d9f6f3466057af21304268b7c650be19c4f4ca`
- Runner candidate/result hash match: true
- Runner asynchronous-error ledger: zero bytes
- Runner, verifier, and launcher processes: exited
- Runner and outer locks: released
- External completion marker: absent by design after fail-closed verification

## Locked gate outcome

| Gate | Runner candidate | Evidence |
|---|---:|---|
| G1 strong default relevance | **Fail** | Linear-over-BPR relative NDCG gain `0.01851 < 0.02`; paired 95% CI for absolute gain `[-0.001135, 0.003425]` crosses zero. |
| G2 relevance non-inferiority | Pass | RAVEL-minus-linear NDCG `+0.0000527`; 95% lower bound `-0.000179 > -0.001`. |
| G3 primary preference gain | **Fail** | User-macro gain `+0.000146`, far below `+0.005`; 95% CI `[-0.0000636, 0.000515]` crosses zero. |
| G4 selective mechanism | Pass | RAVEL point NDCG exceeded exact same-proposal always-on; preference exceeded every locked heuristic; accepted conditional uplift `+0.002238`. |
| G5 nontrivial calibrated coverage | **Fail** | Coverage `0.08567 < 0.10`; seed-averaged accepted requests `85.67 < 100`; accepted-and-pair-bearing support `45.67 < 100`. |
| G6 top-rank/exposure safety | Pass | Recall lower bound `-0.000152 > -0.002`; dislike-intrusion upper bound `0.0 <= 0.002`. |
| G7 support/exact fallback | Pass | Pointwise `B subset C`, union recall dominance, and exact full-order fallback all true in runner evidence. |
| G8 seed stability | Pass | Two of three seeds met the joint NDCG/preference sign condition. |
| G9 serving budget | **Fail** | Worst RAVEL p95 `3.151 ms` is fast in absolute terms but `1.543x` linear, above the locked `1.25x` ratio. |
| G10 integrity | **Fail externally** | Runner reported internal integrity true, but the external verifier correctly rejected nonempty runner stderr and published no completion marker. |

The all-or-nothing conjunction is false.

## Main runner-candidate summaries

| Method | NDCG@10 | User-macro preference accuracy | Recall@10 | Coverage |
|---|---:|---:|---:|---:|
| Selected BPR | 0.059670 | 0.622762 | 0.045182 | 0.0000 |
| Frozen linear default | 0.060775 | 0.616255 | 0.046187 | 0.0000 |
| Same-proposal always-on | 0.060808 | 0.616479 | 0.046239 | 1.0000 |
| Near-tie-only | 0.060873 | 0.616265 | 0.046315 | 0.0917 |
| Uncertainty-only | 0.060794 | 0.616135 | 0.046270 | 0.0957 |
| Random matched | 0.060826 | 0.615989 | 0.046279 | 0.0990 |
| RAVEL | 0.060827 | 0.616401 | 0.046419 | 0.0857 |

The validation lock selected implicit BPR, linear weight `0.75`, near-tie width `0.025`, linear-regret budget `0.03`, benefit threshold `0.50`, and harm ceiling `0.50`. Validation coverage was `0.101`, but test coverage fell below the registered floor. The useful signal is narrow: accepted interventions had positive conditional preference uplift and preserved relevance, but the intervention was too rare, the aggregate preference effect was about 34 times smaller than required, the linear default itself missed its strength gate, and selector overhead missed the relative latency budget.

## Failure interpretation for cycle 4

1. Request-level selection cannot manufacture a large aggregate preference gain when the constrained proposal itself changes too few evaluated pair relations.
2. Preserving a strong top-10 and frozen tail gives clean attribution, but it sharply limits the preference surface available to a residual trained only on naturally retrieved pairs.
3. The validation acceptance floor transferred poorly (`10.1%` to `8.57%`), despite harm-rate transfer being accurate; coverage shift, not harm calibration, was the selector's operational weakness.
4. A two-head selector added roughly `51-54%` p95 overhead to a very fast exact-index linear path even though absolute latency stayed near `3.15 ms`.
5. The next direction must alter where preference-relevant candidates enter or how list-level preference is optimized, not add another request gate around the same weak proposal.
