# H8 fallback screen: revision-induced cycle flow

Date: 2026-08-07

Status: exploratory, label-blind, and inactive unless H6 kills the shared-fact
direction. This is not confirmatory evidence or a novelty claim.

## Structural observation

An independent PowerShell recomputation formed the bipartite graph between the
fixed 50 H5 anchor QIDs and MIND-vocabulary `property|Qtarget` facts. For each
graph, the cycle-space dimension is `beta1 = E - V + C`, counting the anchor
vertices incident to an edge. Adding isolated fixed anchors increases `V` and
`C` equally and leaves `beta1` unchanged.

| View | Graph | Edges | Fact vertices | Components | beta1 |
|---|---|---:|---:|---:|---:|
| primary | historical | 4,575 | 3,771 | 2 | 756 |
| primary | current | 5,886 | 4,724 | 1 | 1,113 |
| primary | historical-only edits | 194 | 187 | 33 | 0 |
| primary | current-only edits | 1,505 | 1,258 | 17 | 214 |
| blocklist + remove Q30/Q22686 | historical | 3,633 | 3,168 | 2 | 419 |
| blocklist + remove Q30/Q22686 | current | 4,504 | 3,907 | 2 | 551 |
| blocklist + remove Q30/Q22686 | historical-only edits | 151 | 147 | 33 | 0 |
| blocklist + remove Q30/Q22686 | current-only edits | 1,022 | 964 | 29 | 39 |

Thus deleted transaction-time edges form a forest in both views, whereas
post-cutoff additions contain a nonzero cycle space even after both frozen
robustness restrictions. This says that the drift includes correlated shared
fact structure rather than only independent leaves. It does not say that the
cycles improve or harm recommendation.

## Possible module and hostile boundary

A bounded fallback would orient the signed add/delete edge flow, project it
onto the graph cycle space, and use anchor-level cycle energy only to shrink or
route an otherwise frozen additive KG residual. The hypothesis is that
revision-induced cyclic redundancy identifies correlated provenance risk that
edge counts, degree, or independent masking miss.

HodgeRank/pairwise-preference decomposition, Hodge graph methods, hypergraph
recommenders, and sheaf recommenders are established. Therefore neither a
Hodge projection nor a cycle score is new. The only potentially distinct
package is external-KG transaction-time edit flow used as a cold-start residual
risk router. Current novelty confidence is low-to-moderate and conditional on
a ranking effect.

If activated on a fresh scorer/dataset, freeze gates before outcomes: at least
10 percent cycle-space energy after both robustness restrictions, a rank gate
at least as strong as H6, and a gain over degree, resource-allocation, PPR, and
matched edit-mask controls. Otherwise kill this fallback rather than tuning a
new graph operator.
