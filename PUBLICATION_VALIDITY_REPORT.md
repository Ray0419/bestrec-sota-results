# Publication Validity Report

## Bottom Line

The validation-selected LC2C++ variant is publication-valid for the existing secondary
`cold_fold_only` protocol, but it is **not** valid as a SOTA claim because the required
full-catalog cold-item evaluation and modern baseline set are still incomplete.

The validated-margin LC2C++ result is significantly better than LC2C V2 on all four
datasets after Holm correction for the current cold_fold_only artifacts.

Important audit note: this candidate was developed after exploratory runs in this
workspace. For a clean publication submission, freeze this algorithm and rerun the
documented pipeline on fresh seeds/splits before presenting it as final confirmatory
evidence.

## Validation-Selected LC2C++ vs LC2C V2

| Dataset | LC2C V2 | LC2C++ validated-margin | Delta | p raw | Holm marker |
|---|---:|---:|---:|---:|---:|
| Beauty | 0.173113 | 0.173825 | 0.000712 | 0.0264 | * |
| Fashion | 0.154837 | 0.157852 | 0.003015 | 0.006789 | ** |
| Instruments | 0.057515 | 0.057949 | 0.000434 | 0.003865 | ** |
| Books | 0.065286 | 0.066741 | 0.001456 | 2.56e-46 | *** |

## Allowed Claims

- LC2C++ validated-margin improves the cold-fold-only NDCG@10 point estimate on all four datasets.
- The improvement is Holm-significant on Beauty, Fashion, Instruments, and Books in the current artifacts.
- LC2C V2 and LC2C++ validated remain significantly stronger than content-direct and the simplified DropoutNet-style baseline where those markers are recorded.

## Disallowed Claims

- Do not present the current result as a fresh confirmatory test; the algorithm was developed through exploratory iterations in this workspace.
- Do not claim SOTA.
- Do not use the fixed 0.95 z-fusion weight as a publication-valid result; it was found by exploratory test-set grid search.
- Do not present cold_fold_only ranking as the primary full-catalog cold-item metric.

## Remaining SOTA Blockers

- Books warm-user evaluation is capped at 5000 each instead of the full 14407 users per fold.
- Core modern SOTA baseline audit is incomplete; SOTA claims must be removed.
- LC2C++ win condition has not passed under the predeclared protocol.