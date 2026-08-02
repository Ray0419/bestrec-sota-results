# History-dependent synthetic intervention decision

Date: 2026-08-02

## Decision: inconclusive

The preregistered lag-2 intervention produced the predicted directional rise
in final-filter rank concentration, but it did not reach the frozen activation
threshold. The experiment therefore neither establishes the proposed
mechanism nor falsifies its directional component.

| condition | best epoch | validation NDCG@10 | early energy | final energy |
|---|---:|---:|---:|---:|
| independent phase, lag-2 required | 97 | 0.890533 | 0.926783 | 0.832853 |
| coupled phase, lag-1 sufficient | 1 | 0.999631 | 0.765255 | 0.759173 |

The optimization sanity check passes. The primary contrast is
`rho_2 - rho_1 = 0.073680`, exceeding the frozen `0.04` directional margin,
but `rho_2 = 0.832853` is below the required `0.905`. Under the preregistration
this is **inconclusive**. It is not a mechanism pass, and it is not a failure
because `rho_2 > rho_1`.

The independent final layer also fails the projection gate, so no projected
validation or test evaluation was run. Neither condition's test split was
accessed.

## Secondary geometry

The early independent filter crosses the energy threshold, but its dominant
channel vector is not close to uniform:

| condition | early uniform cosine | final uniform cosine |
|---|---:|---:|
| independent | 0.600033 | 0.839652 |
| coupled | 0.985806 | 0.986983 |

Thus the only energy-selected filter in the lag-2 condition is low-rank, not
channel-shared. Its item embeddings are also much more concentrated: centered
top-singular energy is `0.195069`, versus `0.033654` in the coupled control.
This makes representation collapse a plausible mediator or confounder in this
synthetic task. It does not reproduce the useful late, uniform collapse seen
in the real ML-1M checkpoints.

## Consequence

A shared higher-order transition rule is not sufficient to cause the specific
late channel-consensus endpoint required by depth-gated EGSP. Together with
the failed first-order transition intervention, this closes transition order
as the leading mechanism explanation. Further causal experiments should vary
optimization scale or representation symmetry directly rather than construct
another Markov-order dataset.

## Provenance

- Preregistration SHA-256:
  `932bd6fe01f5d540239292752af1eba5ccdafcb909102c060f02e441feb8ecb2`.
- Generator manifest SHA-256:
  `7734c71c73252b2819dc8a7be2616cf2f73dd6629f3577929113188b1c2db48d`.
- Independent no-test artifact SHA-256:
  `0abc5c68b52cce78060a5ee24646a4d3beee527dee21ca49a94148f953346362`.
- Coupled no-test artifact SHA-256:
  `6dd780dde1179e8821bd6909d79585aa7b6c901572999cc29b8c948a4c1becee`.
- Filter-geometry artifact SHA-256:
  `ba8aca3094c37fc78ed4ee2d9033f47c6006990d1e8f9f3526167bce66b7a51e`.
- Embedding-geometry artifact SHA-256:
  `8ee18bb27cd498e6fde01e431ec4e06b92d335b9a0ad53c158e7257ec3d56761`.
