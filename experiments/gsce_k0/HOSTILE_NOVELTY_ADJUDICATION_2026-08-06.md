# GSCE hostile novelty adjudication

Date: 2026-08-06 (Australia/Sydney)  
Status: **ELIMINATED BEFORE OUTCOME EXECUTION**  
Ledger position: mechanism 36; Loop 7  

No GSCE extraction, topology diagnostic, recommender outcome, or Python
experiment was run. The frozen K0 preregistration is retained only as an audit
trail; it is not authorized for execution as a lead research direction.

## Decision

An independent hostile audit reduced the probability that the exact GSCE
package is materially unoccupied to **24--32%**, below the preregistered 45%
novelty gate. Confidence in the elimination decision is approximately 88%.

The useful residual is an evaluation module for a future algorithm, not a
stand-alone Tier-A contribution. In particular, warm semantic analogues must be
described as legitimate *interpolation* when they existed at serving time, not
categorically as leakage.

## Decisive prior-art boundary

1. DataSAIL already accepts arbitrary similarities, clusters related samples,
   minimizes cross-split similarity, preserves specified distributions, and
   assigns clusters by constrained optimization. This occupies the generic
   similarity-aware matched splitter:
   <https://doi.org/10.1038/s41467-025-58606-8>.
2. Zhan et al. already formulate separate interpolation/extrapolation
   evaluation, resample embedded examples by similarity, and show model-ranking
   changes:
   <https://arxiv.org/abs/2204.11447>.
3. Peng et al. already argue that item-level temporal coldness is insufficient
   and stratify future cold items by semantic-token and prefix support:
   <https://arxiv.org/abs/2607.21101>.
4. Artist-aware music evaluation and ACARec already distinguish family-level
   semi-cold cases from genuinely new-family cases:
   <https://ceur-ws.org/Vol-4045/paper8.pdf> and
   <https://arxiv.org/abs/2604.07090>.
5. Meehan and Pauwels already use nearest-warm content similarity in a
   cold-item diagnostic:
   <https://arxiv.org/abs/2510.11402>.

The identities `1 - p**d` and their fixed-size hypergeometric counterpart are
elementary sampling calculations, not theorem-level novelty.

## Reuse rule

GSCE may be reused only as a preregistered diagnostic or stress test attached
to a different lead algorithm. A future benchmark-only paper would require a
public multi-domain release, natural absolute-time cohorts, multiple independent
content encoders, several model families, and consequential rank reversals; the
present repositories alone do not justify that investment.
