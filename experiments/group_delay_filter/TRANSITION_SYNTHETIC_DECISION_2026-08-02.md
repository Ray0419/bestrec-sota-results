# Shared-transition synthetic decision - 2026-08-02

## Decision

**Preregistered mechanism fail. Both projection gates abstained. No synthetic
test item was accessed.**

The label-safe screen authorized training: first-order-transition minus
popularity validation NDCG@10 was `0.815953` in the high-reuse condition and
`0.121610` in the low-reuse condition, a gap of `0.694343` against the frozen
minimum of `0.10`.

The validation-selected checkpoints then gave the opposite filter ordering
from the causal prediction:

| condition | best epoch | validation NDCG@10 | early rho | final rho | final uniform cosine |
|---|---:|---:|---:|---:|---:|
| high transition reuse | 0 | 0.798581 | 0.344987 | 0.344590 | 0.872738 |
| low transition reuse | 41 | 0.048065 | 0.490009 | 0.676076 | 0.892376 |

The frozen primary rule defined failure as `rho_H <= rho_L`. Here,
`0.344590 <= 0.676076`, so the mechanism fails. Neither final layer met the
`rho >= 0.905` and uniform-cosine `>= 0.97` projection gate. No validation
projection or test evaluation was performed.

## Interpretation

Population-level reuse of first-order item transitions is not sufficient to
produce MovieLens-like channel sharing. In this controlled intervention, more
reuse produced substantially *less* final-filter concentration.

There is an informative endpoint confound rather than a reason to relabel the
decision. The highly predictable task selected its first trained epoch and its
centered item-embedding effective rank remained `57.98`. The low-reuse task
trained for 42 epochs before its selected checkpoint; its centered embedding
effective rank fell to `29.80`. Thus the intervention changed both the target
structure and how long optimization remained useful. Earlier real-domain data
show that selected epoch alone does not explain filter concentration, but this
synthetic pair cannot isolate that factor.

The more important architectural explanation is that a deterministic
first-order successor can be represented from the most recent item embedding.
It does not require FMLP-Rec's temporal mixer. The preregistered
history-dependent follow-up therefore compares matched processes where lag 2
is either redundant with lag 1 or necessary for prediction.

## Audit trail

- Preregistration SHA-256:
  `d4541a28f6522a6814d962c90801a781da697b88c5144f902a9bc24436ae9e87`
- Generator SHA-256:
  `72be0f2f4b3dbae7d3ed1547a8ded1964734c7b5aff13b889f3779cd75492251`
- High data SHA-256:
  `5b5a594e54db89144fa51586a76851734c4e0bb5824fee4f38e3f52d99532002`
- Low data SHA-256:
  `0bde16adf1a76885bd4997b7e57a164ea5ea175b2de36fefe09bfd484669c417`
- High checkpoint SHA-256:
  `13ae912d9fd486a226d9fbab5a9f3e4475da3f6d4531431da0030e58c9e57875`
- Low checkpoint SHA-256:
  `c5f5e2c6541588b5e9a6b5090b6b6d6b0d8b425c1876cb0d39bd8f696c7c259e`
- High no-test artifact SHA-256:
  `e7021e7ed44a9d68650f34f006a18da885bbb1cdfd6713658677155c988cdc2c`
- Low no-test artifact SHA-256:
  `95a42c84aee3b8e57471e29e0294bb0d8f72e5e1429268715ff2d0965b30973d`
- Low log SHA-256:
  `b703b5c315eaf0612c2ba546353b51afa8c9a9e7f146734253313cb4e2436b62`
- Test access: none for both conditions.
