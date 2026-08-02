# ML-1M sparse-support interaction decision - 2026-08-02

## Decision

**Reject the consensus-dependent interaction hypothesis and promote post-
training sparse impulse support as the primary algorithmic lead.** Channel
consensus and temporal pruning are both useful, but pruning does not require
consensus; their combination has diminishing rather than amplifying returns.

The fixed boundary-8 support is at least as good as adaptive top-8 on this
dataset. It becomes a prospectively testable structural hypothesis, not a
confirmed universal rule, because its support was derived from ML-1M weights.

## Frozen result

Strict-mask validation mean NDCG@10 across seeds 42-46:

| cell | final late filter | mean NDCG@10 |
|---|---|---:|
| F | original frequency-by-channel | 0.1186238833 |
| T | original plus aggregate-energy top-8 impulse support | 0.1267873614 |
| S | channel-mean consensus | 0.1258977884 |
| A | consensus plus adaptive top-8 | 0.1286371163 |
| R | consensus plus fixed recent-8 | 0.1282034813 |
| B | consensus plus fixed boundary-8 | **0.1287040178** |

Primary contrasts:

| contrast | mean delta | positive seeds | positive bootstrap lower bounds |
|---|---:|---:|---:|
| T - F | **+0.0081634781** | 5/5 | 5/5 |
| A - S | +0.0027393280 | 5/5 | 4/5 |
| interaction `(A-S)-(T-F)` | **-0.0054241501** | 0/5 | 0/5 |
| A - R | +0.0004336351 | 3/5 | 0/5 |
| A - B | -0.0000669015 | 1 positive, 1 negative, 3 ties | 0/5 |
| B - S | +0.0028062295 | 5/5 | 4/5 |
| B - R | +0.0005005366 | 4/5 | 0/5 |

All five channel-specific aggregate-energy masks select the same indices as
the corresponding shared adaptive masks. The result is therefore not caused
by comparing different supports. The channel-specific top-8 filters retain
about 88.4-89.5% impulse energy, yet improve every seed with all paired-user
confidence intervals above zero.

## Preregistered rules

- **Independent temporal-pruning effect:** passed strongly.
- **Consensus-pruning interaction:** failed with the opposite sign in 5/5.
- **Adaptive-support value:** failed.
- **Fixed boundary law:** passed on ML-1M, with retrospective-support caveat.
- **Old-history contribution:** passed at the frozen threshold by a narrow
  margin; this remains descriptive until transferred prospectively.

## Scientific interpretation

The strongest supported statement is now: an overparameterized late spectral
filter can benefit from post-training projection onto sparse impulse support,
and that projection can improve ranking rather than merely preserve it. The
removed response is not low-energy approximation noise alone: K=8 previously
outperformed K=16, and the full channel-specific K=8 projection discards about
11% impulse energy while improving NDCG@10 by 0.00816.

The recurring support geometry is a second lead. Useful coefficients lie at
the two circular-convolution boundaries: recent lags and a small number of
oldest sequence positions, while weak middle lags are removed. Whether this is
a transferable sequential-recommendation law or an ML-1M artifact is the next
falsifiable question.

## Novelty and value boundary

This result raises feasibility and effect-size confidence but lowers confidence
in a broad novelty claim: generic impulse-response pruning is close to AIRE-
Prune, and magnitude pruning itself is mature. The exact validation-improving
late-filter projection and direct final-output compilation in sequential
recommendation remain apparently unoccupied, but are not yet enough for a
Tier-A contribution by themselves.

The candidate becomes substantially stronger only if at least one of these is
confirmed:

1. adaptive sparse support transfers across multiple real recommendation
   datasets with frozen K=8;
2. the fixed boundary mask transfers prospectively, revealing a domain-
   specific support law; or
3. direct final-output execution gives a material measured efficiency gain
   with numerical parity.

No large training campaign is authorized yet. Run the existing-checkpoint
transfer panel, exact compiler benchmark, and nearest-prior audit first.

## Provenance

- Preregistration SHA-256:
  `5b119e305a583ed2df849b0299ae4a8b057d42eda952d96e2cf0c54f58ea79bc`.
- Compact record: `ml1m_sparse_support_interaction_summary.json`.
- All new outcomes are full-catalog validation results.
- No ML-1M test result was accessed for T, A, R, or B in this experiment.

