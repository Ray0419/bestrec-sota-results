# CAPER v1: Verified Negative Result and Kill Decision

## Decision

**CAPER v1 is killed.** The externally verified PoC returned `PROMISE_GATE_PASSED=false`. G1, G2, G3, and G7 failed, so Phase 5 is prohibited and the sprint returns immediately to Phase 1, cycle 3. No threshold, seed, comparator, or test-set choice will be changed for CAPER.

## Immutable outcome identity

- Protocol commit: `cf1cc67e50098336781b9264926c3a162ad7f362`
- Run: `caper-poc-v1-20260806T161807162018Z-80045825ddc4`
- Result SHA-256: `ab702a1f1ea16b39c2575190e5658397d9a145e3f55673d86c299384d3f60ac1`
- Runner marker SHA-256: `8d56d2633ed78cdf1afbb6c7790d3531c7bfae72bd203a471629b0f9472d2e15`
- External marker SHA-256: `1a7a56ef2c4c322513d8b8d06a8000a9d4206f3b3a12c869f18f38f663d0495c`
- Externally verified candidate-bound artifacts: 65
- Runner process exited, exclusive lock released, and asynchronous-error ledger empty.

## Gate outcome

| Gate | Result | Evidence |
|---|---|---|
| G1 relevance | **Fail** | CAPER NDCG@10 `0.0631915` vs validation-selected BPR `0.0631124`: only `+0.125%` relative, below the locked `+2%` threshold, although the absolute paired CI was positive (`[0.0000038, 0.0001809]`). |
| G2 mechanism | **Fail** | Projected linear fusion reached `0.0648461`; CAPER-minus-linear was `-0.0016546`, paired CI `[-0.0034252, 0.0000769]`. CAPER did not beat all projected ablations. |
| G3 preference | **Fail** | User-macro pair accuracy fell from BPR `0.624748` to CAPER `0.619234`, difference `-0.005514`, CI `[-0.017659, 0.006551]`. |
| G4 Recall safety | Pass | Recall@10 `0.048682` vs BPR `0.048567`; paired lower bound `0.0 > -0.005`. |
| G5 candidate support | Pass | `B_u` was always contained in `C_u`; union candidate recall `0.469663` exceeded BPR-branch recall `0.391750`. |
| G6 dislike safety | Pass | Mean future-low intrusion matched BPR; paired upper bound for the increase was `0.0`. |
| G7 stability | **Fail** | Only one of three registered seeds beat both BPR and the locked comparator. |
| G8 latency | Pass | Worst CAPER p95 `2.307 ms`; worst ratio to projected linear fusion `1.083x`. |
| G9 integrity | Pass | All manifest, provenance, temporal, immutability, regret, lock, ledger, and external-verification checks passed. |

## Mechanistic diagnosis

1. The hard support/regret envelope worked operationally: coverage, Recall, dislike exposure, latency, and immutability all passed.
2. The contradiction-focused SimPO residual was not the useful component. Its preference accuracy was below BPR, and the positive margin produced the same aggregate NDCG as the zero-margin residual.
3. The simple projected linear semantic/collaborative fusion was the strongest relevance method (`0.0648461`, about `+2.75%` over BPR).
4. The uniform-pair projected residual was the strongest preference ablation (`0.636662` user-macro accuracy), about `+1.19` percentage points over BPR, but it surrendered relevance.
5. The next direction should therefore anchor to the empirically dominant linear hybrid, use natural uniform pairs rather than contradiction oversampling, and apply preference corrections selectively rather than globally.

## Cycle-3 constraint

Cycle 3 must use a disjoint, prospectively selected user cohort not evaluated by CAPER v1. It must test a genuinely different hypothesis: whether validation-calibrated selective preference adaptation can achieve a Pareto improvement over the linear hybrid, rather than trying another globally applied residual.
