# GSCE literature and novelty boundary

Audit date: 2026-08-06 (Australia/Sydney)

## Verdict

GSCE clears the 45% exploration gate as a **recommender-evaluation package**,
not as a new graph algorithm or generic split optimizer.

- Probability the exact recsys package is unoccupied: **57%**.
- Probability the graph split/optimizer alone is novel: **12%**.
- Probability of a non-vacuous K0 with the cached domains: **78%**.
- Tier-A relevance conditional on a K1 model-ranking reversal or a large
  interpolation/extrapolation gap across domains: **48%**.
- Tier-A relevance if K1 only confirms that distant items are harder: **15%**.

The defensible possible claim is:

> A content-graph support audit and paired family-purge protocol reveal which
> nominally cold recommendation targets are semantic interpolation versus
> family-level extrapolation, while preserving temporal target identity.

Do not claim a new probability theorem, the first similarity-aware split, the
first OOD recommender evaluation, or that legitimate warm analogues constitute
data leakage.

## Closest collisions

- DataSAIL gives a generic formal objective for minimizing inter-split
  similarity, supports one- and two-entity datasets, preserves class ratios,
  proves the problem NP-hard, and uses clustering plus ILP. It occupies the
  broad similarity-aware constrained-splitting contribution:
  https://doi.org/10.1038/s41467-025-58606-8
- Guo et al. show that random and even scaffold splits can leave highly similar
  training analogues and inflate virtual-screening results. This is a close
  cross-domain conceptual precedent for interpolation/extrapolation audits:
  https://arxiv.org/abs/2406.00873
- Ji et al. establish global-time leakage in recommender evaluation and require
  a timeline-respecting protocol, occupying broad temporal-leakage claims:
  https://arxiv.org/abs/2010.11060
- TDRO explicitly studies temporal item-feature shifts and clusters warm items
  by features, occupying broad distribution-shift and feature-group cold-start
  claims, but it does not construct graph-separated test families:
  https://arxiv.org/abs/2312.09901
- Equivariant Learning for OOD Cold-start Recommendation directly targets
  underrepresented cold-item feature regions, but simulates shifts by feature
  interpolation rather than measuring or removing warm semantic support:
  https://doi.org/10.1145/3581783.3612522
- ColdGenRec provides a unified 2026 generative cold-start evaluation and uses
  the first 90% of interactions for training, defining a cold item by first
  appearance after the cutoff. It does not report train-cold semantic distance
  or hold out semantic families:
  https://arxiv.org/abs/2603.29845
- HORIZON evaluates temporal, cross-domain, and unseen-user generalization in
  sequential behavior modeling. Its cold-start focus is new users, not
  graph-separated new-item semantic families:
  https://openreview.net/forum?id=Kpt0qegTx7

## Remaining gap

The inspected recommender work does not jointly provide:

1. a label-independent content graph frozen before collaborative outcomes;
2. the exact random-split warm-neighbor exposure calculation;
3. per-target semantic-support strata for nominally cold items;
4. a whole-family purge evaluated on the same temporal cold targets; and
5. covariate-preserving paired comparison of model rankings under semantic
   interpolation and extrapolation.

This conjunction, plus a consequential empirical result, is the GSCE novelty
boundary. Generic graph clustering, connected components, matching, ILP, and
the elementary exposure identity are prior-art primitives.

