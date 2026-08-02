# EGSP research decision — 2026-08-02

## Decision

**Clear gap worth a prospective shot; not yet locked for large-scale Tier-A work.**

The surviving candidate is **Energy-Gated Spectral Projection (EGSP)**. Train an
expressive per-channel temporal filter normally. For each trained filter matrix
`W`, compute

```text
rho_1(W) = sigma_1(W)^2 / sum_j sigma_j(W)^2.
```

If `rho_1 >= 0.905`, replace only that layer by its exact rank-1 SVD
projection. Otherwise leave it unchanged. The operation is label-free,
training-free, layer-local, and applies to both frequency-by-channel complex
filters and tap-by-channel real FIR filters.

The nested-user mechanism study further narrows the surviving algorithm to
**depth-conditioned EGSP**: intervene only on a collapsed late filter. A
943-user cohort produced early-layer collapse but a slightly negative
projection delta, whereas a 4,000-user cohort produced late-layer collapse and
improved validation NDCG@10 by `0.002265` with a positive paired-user interval.
Energy-only routing is therefore not promoted.

The threshold is discovery-derived and therefore exploratory on the current
ML-1M evidence. It was frozen before the prospective Sports & Outdoors pilot;
see `PREREG_EGSP_PROSPECTIVE_V1.md`. That pilot was aborted after epoch 30
because repeated host scheduling stalls made completion impractical. No test
metric was accessed. The validation-selected checkpoint at abort had rank-1
energies `0.8742` and `0.7901`, so the frozen rule would have abstained even if
training had stopped there. This is an incomplete mechanism-gate abstention,
not a completed prospective result.

A second preregistered pilot on independently prepared ML-100K completed under
a no-test runner. Its validation-selected filters retained only `0.8371` and
`0.8328` rank-1 energy, so the frozen rule abstained and the test split remained
unqueried. See `ML100K_PROSPECTIVE_DECISION_2026-08-02.md`.

## Evidence that survived falsification

| setting | split | seeds | mean delta NDCG@10 | sign |
|---|---|---:|---:|---:|
| FMLP-Rec spectral filter, ML-1M | validation | 5 | +0.006919 | 5/5 |
| FMLP-Rec spectral filter, ML-1M | test | 5 | +0.006959 | 5/5 |
| Causal depthwise FIR, ML-1M | test | 4 finalized | +0.005176 | 4/4 |
| FMLP-Rec spectral filter, ML-1M 4,000-user cohort | validation | 1 | +0.002265 | 1/1 |
| BEST-Rec FIR rank-1 smoke | validation, 1,000 users | 8 | -0.000295 | 3/8 |

Every individual ML-1M spectral test seed has a positive paired-user 95%
bootstrap interval. The same is true for the four finalized causal-FIR
checkpoints. Correctly masking seen items with negative infinity gives exactly
the same rankings and effects as the inherited zero-mask evaluator.

The optimization/deployment gap is large. Training FMLP-Rec with a rank-1
filter from scratch averages about `0.1005` NDCG@10 on ML-1M, versus `0.1095`
for the full filter. Training full and projecting only the rank-collapsed late
layer reaches about `0.1165`. Thus the result is not evidence that a low-rank
parameterization suffices during optimization.

## Evidence that killed broader claims

- Unconditional rank-1 projection slightly harms all five Beauty seeds and
  four of five Toys seeds.
- An 85% energy gate still projects their first layers and retains those
  losses. It is rejected.
- The frozen 90.5% gate abstains on Beauty, Toys, LastFM, and all eight released
  BEST-Rec learned-FIR checkpoints.
- The incomplete fresh-seed Sports pilot also sat well below the mechanism
  threshold at its validation-selected epoch-30 checkpoint. No test result was
  queried, so it supplies no performance evidence.
- The completed fresh ML-100K pilot abstained despite having greater matrix
  density than ML-1M. Density alone is therefore not a sufficient activation
  explanation.
- Nested ML-1M cohorts reveal a possible depth migration: first-layer collapse
  at 943 users, no collapse at 2,000, and late-layer collapse at 4,000. The
  preregistered scale rule was formally inconclusive, and only the late-layer
  projection improved validation.
- Ignoring that abstention and projecting BEST-Rec anyway gives a negative
  eight-seed validation smoke mean. That branch is closed.
- Exact rank-1 FIR deployment reduces a selected `64 x 16` tap bank from 1,024
  to 80 scalars (92.2%), but the tested factorized CPU implementation is slower.
  EGSP currently has no wall-clock efficiency claim.
- Group-delay factorization, terminal-only FIR, orthogonal-history FIR,
  item/position decomposition, and a frozen-backbone post-hoc FIR adapter all
  failed their empirical gates.
- Label-free optimal singular-value hard thresholding of the final filter was
  positive on ML-1M seed 42 but weaker than EGSP, then harmed LastFM by
  `0.001449` validation NDCG@10. It is rejected as a broader replacement; see
  `SVHT_FEASIBILITY_DECISION_2026-08-02.md`.

## Novelty audit

The sequential-recommendation-specific question appears unoccupied at high
confidence. The prior audit scanned full text for six nearest filter papers and
titles/abstracts of 400 FMLP-Rec forward citations without finding
channel-sharing or post-training rank-collapse analysis. The current targeted
search likewise found no post-training SVD projection of learned sequential
recommendation filters.

The broad method is **not novel**. Truncated-SVD compression of pretrained
weights is established prior art. Important nearby work includes:

- [TRP](https://arxiv.org/abs/2004.14566), which alternates low-rank projection
  and training;
- [Decomposable-Net](https://arxiv.org/abs/1910.13141), which jointly trains
  full and low-rank subnetworks and performs rank selection;
- [Low-Rank Prehab](https://arxiv.org/abs/2512.01980), which fine-tunes before
  SVD and normally recovers after compression;
- [Spectral Surgery](https://arxiv.org/abs/2603.03995), which uses calibration
  gradients to edit trained LoRA singular values;
- [FMLP-Rec](https://arxiv.org/abs/2202.13556), which motivates learned filters
  as noise attenuation but does not test post-training rank projection.
- [Shortcuts in the Tail](https://arxiv.org/abs/2606.07596), which post-hoc
  truncates fine-tuning updates to reduce shortcut reliance and reports that
  matched low-rank training does not reproduce the effect. This is a close
  conceptual precedent for the optimization/deployment mismatch, although it
  does not study recommendation or temporal filters.
- [SOLAR](https://arxiv.org/abs/2603.02561), which exploits low-rank user-sequence
  representations for efficient attention but does not project learned
  temporal-filter weights.
- [SpecFormer](https://arxiv.org/abs/2607.24025), which treats low effective
  rank in recommender embeddings and attention as harmful and softens their
  spectra during training. It does not analyze temporal-filter weight matrices
  or beneficial post-training collapse.
- [RankElastor](https://arxiv.org/abs/2605.23191), which models effective-rank
  trajectories of RankMixer representations and redesigns train-time mixing to
  prevent embedding collapse; its object and intervention are different.
- [TONE](https://openreview.net/forum?id=sfe6KFGRlD), which adds a learnable
  full-rank matrix to preserve the rank of frequency-domain attention during
  generative-recommender training. This is scientifically close terminology
  but the opposite operation: rank preservation of activations rather than
  post-training rank reduction of temporal-filter weights.
- [On Embedding Collapse when Scaling up Recommendation Models](https://arxiv.org/abs/2310.04400),
  which studies low-rank embedding representations as a harmful scaling
  pathology rather than a compressible filter-weight state.

Accordingly, confidence that the **exact recommendation/filter phenomenon is
unoccupied is at least 95%**, but confidence that the current one-line
algorithm is sufficiently non-obvious and valuable for a Tier-A journal is
only **about 60–70%** after accounting for the closer cross-domain post-hoc
compression precedent, the crowded 2026 rank-collapse literature, and two
prospective non-activations. The defensible novelty claim is deliberately
narrow: beneficial collapse in learned late temporal-filter weights, coupled
to a label-free post-training intervention. Large-scale performance work is not
authorized yet.

## Gates before scale-up

1. A fresh larger dataset must select a late layer under the frozen `0.905`
   rule and pass a preregistered nonnegative feasibility rule. Neither Sports
   nor ML-100K satisfies this gate.
2. The apparent first-to-late migration with user scale must replicate across
   fresh seeds before being claimed as a law.
3. A pass must replicate across at least five fresh seeds without changing rank
   or threshold, followed by a causal-FIR replication.
4. At least one further dataset must remain held out until that first
   prospective decision is complete.
5. The method must be compared with validation-selected rank, energy-ungated
   SVD, trained-low-rank, and at least one calibration-aware SVD baseline.
6. A paper claim must focus on generalization and the optimization/deployment
   rank gap. Filter parameter counts may be secondary; whole-model speed may
   not be claimed without an idle-device benchmark showing it.

## Tier-A shape if the gates pass

The publishable contribution would not be "we applied SVD." It would be the
cross-domain empirical law that late temporal filters can undergo rank collapse
after expressive training, that the collapse predicts when one-shot projection
improves held-out recommendation, and that imposing the same rank during
training fails. That requires prospective breadth and a mechanism analysis;
the current MovieLens discovery alone is not enough.
