# H10A relation-null dual-transaction-time feasibility protocol

Status: **prospectively locked before implementation or H10 computation**

Date locked: 2026-08-07 (Australia/Sydney)

Classification: prospective, label-blind mechanism test with an explicit kill rule

The original unimplemented draft had SHA-256
`228B0C3EA9FEE5A88D0DB1B3C41C2C215E06A4B0809CB34C2110973B3502EBA8`.
Independent audit declared those bytes `NO-GO` before any H10 score, null state,
or implementation existed. This amendment fixes the audit findings
prospectively; it is not a response to experimental results.

## Decision in one sentence

H10A asks whether relation-wise removal of the bipartite configuration-degree
mode exposes anchor-to-anchor KG structure that is both outside a fixed-degree
switch-chain reference and consequential for candidate rankings at historical
and current transaction-time endpoints. H10A is a diagnostic feasibility test,
not evidence of recommendation accuracy, strict cold-start performance, or a
Tier-A novelty claim.

The frozen research question is:

> Does a relation-wise configuration-null residual, weighted only by evidence
> available at both transaction-time endpoints, retain fixed-degree-null-
> exceptional KG structure that produces nondegenerate and degree-distinct
> recommendation scores separately at H and C, while its endpoint-worst
> residual score remains nondegenerate?

If every gate below passes, H10B may test a modular recommendation component:
**relation-null residualization (RNR)** followed by a frozen dual-endpoint
score. RNR is only a local name, not a novelty claim. If any admissible
scientific or module-runtime gate misses, the only decision is
`KILL_H10_RELATION_NULL_DIRECTION`; labels remain unopened and the research
loop must pivot.

## Claim boundary and binding collision screen

The central subtraction in H10A is not novel. Put `P=A/m`, `r=d/m`, and
`c=e/m`. The correspondence-analysis (CA) standardized residual is exactly

```text
D_r^(-1/2)(P-r c^T)D_c^(-1/2)
  = D_d^(-1/2)(A-d e^T/m)D_e^(-1/2)
  = N-u v^T = B.
```

Thus `B` is the classical CA residual, `||B||_F^2` is CA total inertia, and
`BB^T` is its row standardized-residual Gram kernel. The same subtraction is
the normalized counterpart of bipartite modularity, and relation-wise use is
close to multilayer configuration-null modularity. The following are binding
collisions, not optional related work:

- Qi, Hessen, and van der Heijden, *Improving information retrieval through
  correspondence analysis instead of latent semantic analysis* (2024),
  [DOI](https://doi.org/10.1007/s10844-023-00815-y), states the CA
  standardized-residual formula and total-inertia identity occupied by `B` and
  `E`.
- Iyer et al., *A Correspondence Analysis Framework for Author-Conference
  Recommendations* (2020), [arXiv](https://arxiv.org/abs/2001.02669), already
  uses CA explicitly for recommendation.
- Dhillon, *Co-clustering documents and words using bipartite spectral graph
  partitioning* (KDD 2001),
  [author page](https://bigdata.oden.utexas.edu/publication/co-clustering-documents-and-words-using-bipartite-spectral-graph-partitioning/),
  occupies normalized bipartite spectral analysis through the nontrivial
  singular subspace after the leading degree mode.

- Barber, *Modularity and community detection in bipartite networks* (2007),
  [DOI](https://doi.org/10.1103/PhysRevE.76.066102) and
  [arXiv](https://arxiv.org/abs/0707.1616), occupies the bipartite
  configuration-null residual itself.
- Newman, *Modularity and community structure in networks* (2006),
  [arXiv](https://arxiv.org/abs/physics/0605087), occupies the general
  configuration-null modularity-matrix idea.
- Paul and Chen, *Null Models and Community Detection in Multi-Layer Networks*
  (2016), [arXiv](https://arxiv.org/abs/1608.00623), occupies layer-wise
  configuration-null modularity.
- Zhang et al., *Alleviating New User Cold-Start in User-Based Collaborative
  Filtering via Bipartite Network* (IEEE TCSS 2020),
  [DOI](https://doi.org/10.1109/TCSS.2020.2971942), already applies weighted,
  normalized bipartite modularity to cold-start recommendation. H10 cannot
  claim the first normalized-modularity recommender or the first such use in
  cold start.
- Leinwand and Pipiras, *Augmented degree correction for bipartite networks
  with applications to recommender systems* (2024),
  [DOI](https://doi.org/10.1007/s41109-024-00630-6), is a direct bipartite
  degree-correction recommender collision.
- Kojaku et al., *Residual2Vec: Debiasing graph embedding with random graphs*
  (NeurIPS 2021),
  [official proceedings](https://proceedings.neurips.cc/paper/2021/hash/ca9541826e97c4530b07dda2eba0e013-Abstract.html),
  occupies graph-representation debiasing against a soft configuration null.
- Wang et al., *DSKReG: Differentiable Sampling on Knowledge Graph for
  Recommendation with Relational GNN* (CIKM 2021),
  [DOI](https://doi.org/10.1145/3459637.3482092) and
  [arXiv](https://arxiv.org/abs/2108.11883), directly targets skewed KG node
  degrees and irrelevant KG interactions in recommendation. H10 therefore
  cannot claim to be the first degree-debiased KG recommender.
- Glaviano and Micciche, *Unbiased randomization of weighted bipartite networks
  with exact degree and strength sequences* (2026),
  [APS](https://journals.aps.org/pre/abstract/10.1103/rn1f-zsgb), occupies
  current exact-marginal bipartite randomization methodology. H10's binary
  finite switch reference is a diagnostic device, not a new sampler.
- The endpoint maximin identity used below is elementary affine robust
  optimization. It is not an algorithmic novelty.

Additional work makes the empirical motivation plausible but narrows the claim:
KG4RecEval reports that removing or distorting KG information often does not
hurt recommendation, including cold-start evaluation
([DOI](https://doi.org/10.1145/3713071)); KGCL addresses noisy and long-tail KG
recommendation ([arXiv](https://arxiv.org/abs/2205.00976)); KGTrimmer prunes
task-irrelevant KG content ([arXiv](https://arxiv.org/abs/2405.11531)); and
causal KG recommendation already targets bias pathways
([arXiv](https://arxiv.org/abs/2212.10046)). ATOM distinguishes observation time
from validity time in temporal KG construction
([ACL Anthology](https://aclanthology.org/2026.findings-eacl.49/)), but H10A uses
only two observed transaction-time endpoints and does not claim a full temporal
KG model.

No technical claim in this protocol relies on *Knowledge Graph-Based Debiasing
for Trustworthy Recommendation Systems* (DOI
`10.1109/TKDE.2026.3702349`), because its primary full text was not verified at
protocol lock. It must not be used as a negative or positive novelty assertion
until independently checked.

The only potentially unoccupied combination found before lock is:

1. relation-wise normalized configuration residualization of a recommender KG;
2. relation weights calibrated by the smaller marginal edge count across
   historical/current observation endpoints; and
3. an endpoint-worst-case modular score.

No exact collision for that literal combination was found in the primary
sources inspected, but it is a composition of occupied pieces and absence of a
found collision is not proof of novelty. Pre-experiment confidence that the
exact combination is unoccupied is `0.55` (reasonable range `0.50--0.60`).
Present Tier-A publishability confidence for H10A itself is only `0.125`
(reasonable range `0.10--0.15`). A pass can raise feasibility; it cannot make
RNR, the CA kernel, CA inertia, or endpoint minimum a novel contribution.

An independent mathematical audit also fixes the interpretation of `E` before
implementation. For a binary relation,

```text
||B||_F^2 = ||N||_F^2 - 1
            = sum_((i,j) in edges) 1/(d_i e_j) - 1.
```

If `M_ab` is the number of edges joining row degree `a` to column degree `b`,
then `||B||_F^2+1=sum_(a,b) M_ab/(ab)`. A valid switch
`(i,j),(k,l) -> (i,l),(k,j)` changes this value by exactly

```text
(1/d_i - 1/d_k)(1/e_l - 1/e_j).
```

Consequently `E` is a degree-class mixing diagnostic, not an omnibus measure
of residual topology. It is invariant for a regular positive-degree side and
can be invariant while anchor-oriented operators and recommendation scores
change. `E` is therefore descriptive below and is forbidden from deciding
futility. Candidate-projected `V` is the first hard null-calibrated gate.

## Immutable inputs and forbidden information

H10A may open only these inputs:

- MIND-small development `news.tsv`, SHA-256
  `E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822`;
- MIND `relation_embedding.vec`, used only for its frozen 1,091 relation IDs,
  SHA-256 `D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A`;
- H5 run-003 `facts.jsonl`, SHA-256
  `13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D`;
- committed H6 Phase-A result, SHA-256
  `B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF`;
- committed H6 label-free cohort manifest, 224,785,295 bytes, SHA-256
  `522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5`;
- committed H6 Phase-A completion marker, SHA-256
  `AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06`.

The H6 Phase-A artifact was committed at
`b1f247abf3185a2eaec8588b358c488af8f78342`.

The runner must reject access to `behaviors.tsv`, candidate suffixes/labels,
H6 Phase-B outcomes, or any interaction-outcome artifact. From the H6 manifest
it may read only impression IDs, user IDs, supplied history news IDs, and
candidate news IDs; the stored H6 scores/ranks are ignored. Supplied histories
are prior clicked feedback and candidate slates are exposure-conditioned, so
H10A is not click-free or exposure-free. No target-candidate outcome label,
dwell signal, outcome-derived popularity, train/test assignment, or downstream
metric may select any H10 choice.

Before computation, the runner must reproduce these label-free counts exactly:

- 42,416 news rows;
- 12,060 news with at least one retained anchor;
- 812 distinct retained-anchor patterns, including the empty pattern;
- 64,443 manifest impressions and 43,374 users;
- 2,422,258 candidate occurrences;
- 512,071 supported candidate occurrences;
- 48,422 impressions with more than 10 candidates;
- 17,436 impressions with more than 10 candidates and more than 10 supported
  candidates;
- 44,341 impressions with at least two supported candidates;
- all 64,443 histories containing at least one supported news item.

A mismatch, forbidden-file access, input-hash change, parse error, or inability
to establish provenance makes the run `INCONCLUSIVE_INVALID_RUN`; it is not
scientific evidence for or against H10.

Before cohort selection, independently reject any manifest impression that
contains a duplicate candidate news ID. Any duplicate makes the entire run
`INCONCLUSIVE_INVALID_RUN`. Candidate lists are therefore ordered lists of
unique IDs. History duplicates remain preserved as specified below.

## Frozen cohort, anchors, and news/user vectors

Read the exact ordered 50-anchor list and confidence threshold `0.90` from the
committed H6 Phase-A result. A news item has binary anchor vector
`a_n in {0,1}^50` from its retained title and abstract entity annotations. Set

```text
y_n = a_n / ||a_n||_2,  if ||a_n||_2 > 0;
y_n = 0,                otherwise.
```

For an impression, retain the supplied final 50 history news IDs in manifest
order, preserving duplicates. Let `h_i` be the sum of their `y_n` vectors and
set `x_i=h_i/||h_i||_2`. The frozen count above guarantees a nonzero history;
otherwise the run is invalid. These vectors are computed once and are identical
for historical/current endpoints and for every null replicate.

The canonical representation path is binary64 and exact. Encode every anchor
set as its ascending tuple of zero-based indices in the frozen 50-anchor order;
assign the 812 pattern IDs by ascending tuple, with the empty tuple first. For a
nonempty tuple of length `k`, compute one value as

```text
value = numpy.divide(numpy.float64(1.0),
                     numpy.sqrt(numpy.float64(k)))
```

and assign that identical bit pattern to its coordinates in an initially zero,
C-contiguous `numpy.float64[50]` row. For each history, initialize a zero
binary64 row and apply `numpy.add(history_sum,y_news,out=history_sum)` once per
news ID in preserved manifest order. Compute its norm as

```text
history_ss = numpy.add.reduce(
    numpy.multiply(history_sum,history_sum), dtype=numpy.float64)
history_norm = numpy.sqrt(history_ss)
x_i = numpy.divide(history_sum,history_norm)
```

Store `X` as C-contiguous `numpy.float64[8192,50]` in ascending
`(audit_hash,impression_id)` order. Candidate occurrences follow that impression
order and then manifest order. Their sparse nonzeros follow ascending anchor
index and use C-contiguous `numpy.intp` occurrence/impression/anchor arrays and
a C-contiguous binary64 value array. Primary and replay must reproduce every
representation bit; the independent verifier's canonical construction must be
bit-equal, while its separately accumulated mathematical check uses `1e-12`.

The H10 audit cohort is the exactly 8,192 impressions with smallest ascending

```text
SHA256("20260807|H10A|audit|" + impression_id)
```

among the frozen 17,436 impressions having more than 10 total candidates and
more than 10 supported candidates. Break a hash collision by ascending literal
`impression_id`. Keep all candidate IDs in each selected impression, including
unsupported candidates. The selection is made without scores or labels.

## Relation-wise graph compiler

Let `s in {H,C}` denote historical and current observation endpoints. For each
analysis view and property/relation `r`, construct a binary incidence matrix
`A_(r,s)`. Rows are the ordered retained anchors. After the view-specific edge
removal, columns are the lexicographically ordered union of remaining target
QIDs observed for relation `r` at either endpoint. Entry `(i,j)` is one
iff H5 contains fact `r|target_j` for anchor `i` at endpoint `s`. Duplicate
facts collapse to one. Non-QID targets and properties outside the frozen
1,091-ID vocabulary are excluded. A union column absent at an endpoint is a
degree-zero column there and contributes zero.

For an endpoint matrix write

```text
d = A 1,      e = A^T 1,      m = 1^T A 1.
```

On positive-degree row/column support, define

```text
N = D_d^(-1/2) A D_e^(-1/2),
u = sqrt(d/m),
v = sqrt(e/m),
B = N - u v^T.
```

Square roots and division are elementwise. Coordinates of zero degree are zero.
The implementation must use these equations directly; TF-IDF, learned weights,
embedding similarity, outcome-calibrated weights, smoothing, added self-loops,
and alternate normalizations are forbidden.

### Exact algebra and unique feasible deflation

On positive support, `||u||_2=||v||_2=1`, `Nv=u`, and `N^T u=v`. Hence

```text
B = (I-u u^T)N = N(I-v v^T)
  = (I-u u^T)N(I-v v^T),
Bv = 0,       B^T u = 0.
```

The removed matrix `u v^T` is not merely a convenient rank-one choice. It is
the unique minimum-Frobenius correction among **all** feasible corrections:

```text
minimize_C ||C||_F
subject to (N-C)v=0 and (N-C)^T u=0.
```

The constraints are `Cv=u` and `C^T u=v`. Every feasible `C` has the unique
form `C=u v^T+Z` with `Zv=0` and `Z^T u=0`. Moreover,

```text
<u v^T,Z>_F = u^T Z v = 0,
||C||_F^2 = ||u v^T||_F^2 + ||Z||_F^2 = 1 + ||Z||_F^2.
```

Therefore `C*=u v^T` is the unique minimizer over all feasible matrices, not
only over rank-one matrices.

For the bipartite configuration multigraph conditioned on degrees,
`E[A_ij|d,e]=d_i e_j/m`, so `E[N|d,e]=u v^T` and `E[B|d,e]=0`. That exact
expectation is not asserted for the uniform simple fixed-degree graph. H10A
therefore uses the explicit finite switch-chain reference below and makes no
claim that a finite burn-in produces IID uniform samples.

The raw normalized two-hop operator decomposes exactly:

```text
B B^T = N N^T - u u^T,
N N^T = B B^T + u u^T.
```

The terms are Frobenius-orthogonal because `B B^T u=0`, and
`||u u^T||_F^2=1`. Thus the per-relation, per-endpoint squared-Frobenius share
attributable to the degree mode is

```text
rho_(r,s) = 1 / (1 + ||B_(r,s) B_(r,s)^T||_F^2).
```

This is reported descriptively; it is not a significance test.

## Frozen evidence calibration and operators

For each analysis view, a relation is eligible iff, at **both** endpoints, it
has positive incidence on at least two anchor rows, at least two target columns,
and at least one edge. Define the minimum endpoint-marginal evidence and weights
by

```text
c_r = min(m_(r,H), m_(r,C)),
alpha_r = c_r / sum_(q in R*) c_q.
```

`c_r` is not shared-fact overlap: it is only the smaller of the two endpoint
edge counts. `R*` and `alpha` are computed once per view from real endpoint
degrees, before any null state. They use no target-candidate outcome and are
invariant under the fixed-degree switches. If `R*` is empty, the applicable
scientific gate misses.

For a given view and relation, first apply that view's edge removal to both
endpoints. Its target-column universe is then the ascending literal-QID union
of targets remaining at either endpoint. The identical universe is used for H,
C, and both chains. A target absent at one endpoint remains as a zero-degree
column there; a target absent from both post-removal endpoints is not a column.

For `s in {H,C}`, define

```text
K_s = sum_(r in R*) alpha_r B_(r,s) B_(r,s)^T,
G_s = sum_(r in R*) alpha_r u_(r,s) u_(r,s)^T,
W_s = K_s + G_s
    = sum_(r in R*) alpha_r N_(r,s) N_(r,s)^T.
```

`K_s` is positive semidefinite since
`x^T K_s x=sum_r alpha_r ||B_(r,s)^T x||_2^2 >= 0`.

This operation removes one normalized degree mode inside each eligible
relation. It does not remove all aggregate degree or popularity information:
cross-relation frequency, anchor activity, and downstream aggregation can
still carry such structure.

The evidence-weighted, relation-stratified degree-mode share is

```text
rho_s = [sum_r alpha_r]
        / [sum_r alpha_r {1 + ||B_(r,s)B_(r,s)^T||_F^2}].
```

This is deliberately defined as a weighted relation-wise energy summary. It is
not described as the Frobenius decomposition of the summed operator, because
cross-relation terms would invalidate that interpretation.

For a user/candidate pair, compute

```text
z_(i,n,s) = x_i^T K_s y_n               residual score,
g_(i,n,s) = x_i^T G_s y_n               degree-mode score,
a_(i,n,s) = x_i^T W_s y_n = z+g         raw score.
```

The exact identity `a=z+g` is a hard numerical/parity check.

The frozen endpoint-robust diagnostic is

```text
z_rob(i,n) = min(z_(i,n,H), z_(i,n,C)).
```

Equivalently, with `K_0=(K_H+K_C)/2` and
`Delta=(K_C-K_H)/2`,

```text
x^T K_0 y - |x^T Delta y|
  = min(x^T K_H y, x^T K_C y)
  = min_(theta in [0,1]) x^T[(1-theta)K_H+theta K_C]y.
```

This equality is classical endpoint algebra. H10 makes no novelty claim for it.
No harmonic mean, parallel sum, outcome-selected interpolation, or learned
endpoint weight is allowed.

### Sparse implementation contract

The implementation must not materialize an anchor-by-global-target dense
matrix. For a vector `x`, use

```text
B^T x = N^T x - v(u^T x),
B q   = N q   - u(v^T q).
```

Thus `K_s x` requires two sparse incidence passes per eligible relation plus
linear support work: time
`O(sum_r nnz(A_(r,s)) + support)` and sparse storage
`O(sum_r nnz(A_(r,s)))` per vector (or the same multiplied by a fixed batch
width). The final 50-by-50 `K_s`, `G_s`, and `W_s` may be dense. Cache the 812
news patterns, batch the 8,192 user vectors, precompute tie keys, and update
switch states in place. These are runtime requirements, not algorithmic claims.

The canonical binary64 operator path uses no SciPy object and does not form a
dense anchor-by-target matrix. For every real or retained aggregate state,
enumerate eligible relations by ascending literal relation ID, target columns
by ascending local index, and the upper-triangle pairs of rows incident to a
column in lexicographic `(a,b)` order with `a<=b`. Accumulate every integer
`c_r` in ascending relation order into an exact Python integer `c_total`, then
set `alpha_r=numpy.divide(numpy.float64(c_r),numpy.float64(c_total))`. Cast
degrees to C-contiguous binary64. Initialize `u`, `inv_sqrt_d`, and `inv_e` as
zero binary64 arrays and use the exact masked calls

```text
numpy.divide(d64,numpy.float64(m),out=u,where=d64>0)
numpy.sqrt(u,out=u,where=d64>0)
numpy.divide(numpy.float64(1.0),numpy.sqrt(d64),
             out=inv_sqrt_d,where=d64>0)
numpy.divide(numpy.float64(1.0),e64,out=inv_e,where=e64>0)
```

Concatenate contributions in the stated order and make exactly one
`numpy.bincount(indices,weights=weights,minlength=2500)` call, where
`a_idx=numpy.ascontiguousarray(a,dtype=numpy.intp)` and
`b_idx=numpy.ascontiguousarray(b,dtype=numpy.intp)` are cast **before**
arithmetic, and

```text
indices = numpy.add(numpy.multiply(a_idx,numpy.intp(50)),b_idx)
```

is C-contiguous, in the same order, and checked to lie in `[0,2499]`. The
weights are formed from
`numpy.float64(alpha_r)` by three left-associated binary64 `numpy.multiply`
calls:

```text
alpha_r * inv_sqrt_d[a] * inv_sqrt_d[b] * inv_e[j].
```

Unused lower-triangle bins remain zero. Reshape the 2,500 bins row-major and
mirror the strict upper triangle by assignment, without re-summing, to obtain
`Q_s=sum_r alpha_r N_r N_r^T`. Precompute `G_s` by accumulating
`numpy.multiply(numpy.float64(alpha_r),numpy.outer(u_r,u_r))` with
`numpy.add(G_s,term,out=G_s)` into an initially zero C-contiguous binary64
matrix in ascending relation order. Then compute, in this order,

```text
K_s = numpy.subtract(Q_s, G_s),
W_s = Q_s,
E_s = float(numpy.trace(K_s, dtype=numpy.float64)).
```

Primary and replay must match the canonical result bit for bit. The independent
verifier must reproduce this path without importing runner code and must also
compare it within `1e-12` to a separately written per-column outer-product
construction. Its direct scalar check is
`sum_r alpha_r[sum_((i,j) in edges_r)1/(d_i e_j)-1]` within `1e-12` of canonical
`E_s`.

The canonical score path orders selected impressions by ascending
`(audit_hash,impression_id)`, candidate occurrences by that impression order and
then their manifest order, and nonzero candidate anchors by ascending anchor
index. For operator `L` in `{K_s,G_s,W_s}`, compute

```text
U = numpy.matmul(X, L)
terms = numpy.multiply(U[nz_impression,nz_anchor], nz_value)
scores = numpy.bincount(nz_occurrence, weights=terms,
                        minlength=n_candidate_occurrences)
```

in binary64. Empty occurrences receive exact zero. `z`, `g`, and `a` are
computed separately with `K_s`, `G_s`, and `W_s`; `a` is not constructed as
`z+g`. Primary and replay must match all canonical score bits. The verifier
repeats this path independently and compares it to direct dense pattern scoring
within `1e-12`.

## Deterministic ranks and frozen metrics

For each impression, first order candidates by descending exact finite
binary64 score. Traverse that order: the first candidate opens a tie group and
each following candidate joins that group iff its absolute score difference
from the group's first score is at most `1e-12`; otherwise it opens the next
group. Within each group, order by ascending hexadecimal

```text
SHA256("20260807|H10A|rank|" + impression_id + "|" + news_id).
```

Break a rank-hash collision by ascending literal `news_id`.

The canonical preliminary order is
`numpy.argsort(numpy.negative(score_segment),kind="stable")`. Traverse its
integer indices in that order, compute each membership test as

```text
numpy.absolute(numpy.subtract(score,current_group_first_score))
    <= numpy.float64(1e-12)
```

and assign monotonically increasing integer group IDs.
The final order is ascending `(group_id,rank_hash_hex,news_id)` and its inverse
is stored as one-based C-contiguous `numpy.int64` ranks. Primary, replay, and
the verifier's canonical metric path must reproduce those ranks exactly.

Every selected impression has more than 10 candidates, so Top-10 always means
exactly 10 candidates. Unsupported candidates remain and receive the score
induced by `y_n=0`, namely zero.

For endpoint `s`, let `C_i` be impression `i`'s complete ordered list of unique
candidates and write `M_i=|C_i|`. Let `rank_z` and `rank_g` be the resulting one-based complete
permutations under residual and degree-mode scores. Define the normalized
Spearman footrule departure

```text
D_s = mean_i [ sum_(n in C_i) |rank_z(i,n,s)-rank_g(i,n,s)|
               / floor(M_i^2/2) ].
```

The denominator is the maximum footrule distance between two permutations of
length `M_i`, so each impression contribution lies in `[0,1]`. Define the other
primary metrics:

```text
E_s = sum_r alpha_r ||B_(r,s)||_F^2,

V_s = mean_i [ |C_i|^(-1) sum_(n in C_i)
                (z_(i,n,s)-mean_(q in C_i) z_(i,q,s))^2 ],

T_s = mean_i [1 - |Top10_i(z_s) intersect Top10_i(g_s)|/10].
```

`E_s` is descriptive residual correspondence inertia and degree-class mixing;
`V_s` is within-impression residual score dispersion; `D_s` is full-ranking departure; and `T_s` is Top-10
departure from the degree-only component. All are computed on the selected
cohort and fixed before any null output.

The canonical metric path uses C-contiguous score arrays in candidate-occurrence
order, C-contiguous `numpy.intp` offsets of length 8,193, and
`counts=numpy.diff(offsets)`. For any residual score array `scores`, compute `V`
through exactly

```text
sums = numpy.add.reduceat(scores, offsets[:-1], dtype=numpy.float64)
means = numpy.divide(sums, counts.astype(numpy.float64))
centered = numpy.subtract(scores, numpy.repeat(means, counts))
squares = numpy.multiply(centered, centered)
within = numpy.add.reduceat(squares, offsets[:-1], dtype=numpy.float64)
per_impression = numpy.divide(within, counts.astype(numpy.float64))
V = float(numpy.mean(per_impression, dtype=numpy.float64))
```

Final one-based ranks are C-contiguous `numpy.int64` arrays in the same
occurrence order. Compute `D` with `rank_delta=numpy.abs(rank_z-rank_g)`,
`footrule=numpy.add.reduceat(rank_delta,offsets[:-1],dtype=numpy.int64)`,
`counts64=counts.astype(numpy.int64)`,
`denominator=numpy.floor_divide(numpy.multiply(counts64,counts64),2)`, binary64
`per_impression=numpy.divide(footrule.astype(numpy.float64),
denominator.astype(numpy.float64))`, and
`D=float(numpy.mean(per_impression,dtype=numpy.float64))`. Compute the
integer Top-10 overlap for each impression from those final ranks, then compute
`t_per=numpy.divide((10-overlap).astype(numpy.float64),numpy.float64(10.0))`
and `T=float(numpy.mean(t_per,dtype=numpy.float64))`.

Define `R2_deg,s` as squared Pearson correlation after separately centering `z`
and `g` within every impression and pooling all candidate occurrences. If either
pooled variance is at most `1e-24`, set `R2_deg,s=1` so the gate fails rather
than creating a favorable undefined value.

For the canonical `R2_deg` path, obtain both impression means with the exact
`add.reduceat`/`divide` operations used for `V`, center via `numpy.repeat`, and
let `P=n_candidate_occurrences`. Compute, in order,

```text
var_z = numpy.divide(numpy.add.reduce(zc*zc,dtype=numpy.float64),
                     numpy.float64(P))
var_g = numpy.divide(numpy.add.reduce(gc*gc,dtype=numpy.float64),
                     numpy.float64(P))
cov_zg = numpy.divide(numpy.add.reduce(zc*gc,dtype=numpy.float64),
                      numpy.float64(P))
corr = numpy.divide(cov_zg,numpy.sqrt(numpy.multiply(var_z,var_g)))
R2_deg = float(numpy.multiply(corr,corr))
```

Here each `*` in the three reductions is one `numpy.multiply` call. Test the two
variances before computing `corr`; if either is `<=1e-24`, assign exact
binary64 `1.0`.

An impression is endpoint-usable when its candidate residual score range
exceeds `1e-12` at both H and C. It is robust-usable when its `z_rob` range
exceeds `1e-12`. Report endpoint-usable, robust-usable, supported-candidate, and
nonzero-score counts/rates. Also report `rho_(r,s)`, `rho_s`, endpoint Top-10
disagreement, `z_rob` dispersion, and all raw/residual/degree score quantiles.
These secondary reports cannot rescue a gate.

Compute `z_rob=numpy.minimum(z_H,z_C)`. Compute every per-impression range with
`numpy.maximum.reduceat(scores,offsets[:-1]) -
numpy.minimum.reduceat(scores,offsets[:-1])`; `nonzero-score` means the exact
comparison `scores != numpy.float64(0.0)`. Define `z_rob` dispersion by the
same canonical `V` path applied to `z_rob`, and endpoint Top-10 disagreement by
the same overlap reduction used for `T`. Report nearest-rank score quantiles at
`p in {0,0.01,0.05,0.25,0.50,0.75,0.95,0.99,1}` after stable ascending sort,
using the minimum for `p=0`, the maximum for `p=1`, and one-based index
`ceil(pP)` otherwise. For descriptive real/null `E`, report `Q_0.50`, `Q_0.95`,
`Q_0.99`, the minimum, maximum, real-minus-quantile values, and the tail count
and `p_MC`. All are secondary unless explicitly named in a gate.

## Fixed-degree lazy double-edge-swap reference

Null randomization is performed separately for every `(view, endpoint,
relation)` binary incidence matrix and never across relations or endpoints.
One proposal is:

1. with probability `1/2`, remain at the current graph;
2. otherwise choose an ordered pair of distinct current edges uniformly;
3. if the edges are `(i,j)` and `(k,l)`, require `i!=k`, `j!=l`, and absence of
   `(i,l)` and `(k,j)`; if all conditions hold, replace the old edges by the
   crossed pair, else remain at the current graph.

The transition is symmetric, preserves the exact row and column degrees, and
never introduces a duplicate edge. Relations with no valid swap remain fixed
and are reported, never silently removed. This is a finite lazy switch-chain
reference, not an assertion of exact uniform sampling or independent samples.

Use two independently seeded chains. Seeds are the first eight bytes,
big-endian, of

```text
SHA256("20260807|H10A|null|" + view + "|" + endpoint + "|" +
       relation_id + "|chain=" + chain_id)
```

Interpret the seed as an unsigned 64-bit integer and initialize
`numpy.random.Generator(numpy.random.PCG64DXSM(seed))`. Iterate relations in
ascending literal relation ID. The lazy/stay decision is
`(bit_generator.random_raw() & 1)==0`. Every proposal makes exactly one scalar
`bit_generator.random_raw()` call. If its low bit is zero, make no integer
draw. Otherwise make exactly these two scalar calls, in this order:

```text
first = int(rng.integers(0, m, size=None,
                         dtype=numpy.int64, endpoint=False))
raw_second = int(rng.integers(0, m-1, size=None,
                              dtype=numpy.int64, endpoint=False))
second = raw_second + int(raw_second >= first)
```

This samples a distinct ordered edge pair uniformly. Batched or cached draws,
`choice`, `random`, vector-valued draws, and every extra RNG draw are forbidden.

The exact string values are `view in {primary,metadata_blocklist,hub_removal}`,
`endpoint in {H,C}`, the literal relation ID, and `chain_id in {0,1}`. Each
stream starts from the corresponding real matrix. Its edge array is initially
ordered row-major by anchor index and then target-column index. After sampling
two distinct indices, set `p=min(first,second)` and `q=max(first,second)`. For
slots `p<q` containing `(i,j)` and `(k,l)`, an accepted proposal overwrites slot
`p` with `(i,l)` and slot `q` with `(k,j)`. The array is never re-sorted;
membership structures are updated without changing slot order. Retained states
are numbered from 1 after burn-in.

Counter semantics are exact. Every proposal increments `proposals`. A low-bit
lazy decision increments `lazy_stays` and consumes no integer draw. A nonlazy
proposal increments `nonlazy_attempts`. If `i==k` or `j==l`, it increments
`invalid_same_row_or_column`. Otherwise, if either crossed edge is occupied, it
increments `invalid_cross_occupied`. Otherwise it increments both
`valid_swaps` and `accepted_swaps` and performs the switch. Therefore

```text
self_transitions = lazy_stays + invalid_same_row_or_column
                  + invalid_cross_occupied,
proposals = self_transitions + accepted_swaps,
valid_swaps = accepted_swaps.
```

For each observed relation state, `structurally_immobile` is true iff exhaustive
inspection of every unordered edge-slot pair finds no valid switch.
`zero_acceptance` is reported separately and is not called immobility. Report
the number of initially valid unordered switches, the number among them whose
two row degrees and two column degrees both differ (`E_changing_switches`), the
distinct positive row- and column-degree counts, and the degree-mixing-table
digest.

For the degree-mixing digest, form sorted triples `(p,q,count)` for every
positive count, where `p` is row degree, `q` is column degree, and `count` is the
number of edges joining those degree classes. Hash ASCII
`H10A_DEGREE_MIX_V1\n`, then unsigned `LE4(number_of_triples)`, then each triple
in ascending `(p,q)` order as `LE4(p)+LE4(q)+LE4(count)`. This table and digest
refer to the observed post-view-removal graph before either chain starts.

The canonical state digest is SHA-256 over the following exact byte expression,
where every string is strict ASCII, `LE2`/`LE4` are unsigned little-endian
fixed-width encodings, and `+` is byte concatenation:

```text
b"H10A_STATE_V1\n"
+ ASCII(view) + b"\n" + ASCII(endpoint) + b"\n"
+ ASCII(relation_id) + b"\n" + ASCII(str(chain_id)) + b"\n"
+ ASCII(str(state_id)) + b"\n"
+ LE2(n_rows) + LE4(n_columns) + LE4(m)
+ concat_slots(bytes([row_index]) + LE4(column_index))
```

`state_id=0` denotes the observed start and retained states use their one-based
index. `retained_duplicate_count` counts retained states whose exact slot arrays
equal an earlier retained state in the same chain; the observed start is
excluded. `returned_to_observed_count` uses exact slot-array equality, not
edge-set equality, and is reported separately. All row/column indices are
zero-based. Hash integers, including `chain_id` and `state_id`, as unpadded
ASCII decimal. Digest equality never substitutes for exact array equality when
counting duplicates.

For a primary-view relation with `m` edges, each chain receives exactly `50m`
burn-in proposals and then one retained state after every `2m` proposals. The
primary view retains 50 states per chain, hence 100 combined null replicas. A
replica is formed by joining the same chain/state index across all eligible
relations; relations use independent deterministic streams. On the frozen real
graphs this schedule contains exactly 3,003,000 primary proposals. Record
all counters and diagnostics defined above for every
`(view,endpoint,relation,chain)`.

For `B` scalar null values sorted ascending, define the noninterpolated
quantile

```text
Q_p = value_[ceil(pB)]                 (one-indexed).
```

The canonical path constructs a C-contiguous binary64 array in chain 0/state
order followed by chain 1/state order and calls
`numpy.sort(values,kind="stable")`. The exact zero-based indices used by gates
are: combined-primary `Q_0.99 -> 98` and `Q_0.95 -> 94`, primary per-chain
`Q_0.99 -> 49` and `Q_0.95 -> 47`, combined-robustness `Q_0.50 -> 9`, and
robustness per-chain `Q_0.50 -> 4`. No interpolation is permitted.

The one-sided Monte Carlo tail value is

```text
p_MC = (1 + count(null >= real)) / (B+1).
```

Compute the count with
`numpy.count_nonzero(numpy.greater_equal(values,numpy.float64(real)))`, then
perform the integer additions and one binary64 `numpy.divide`.

For any 100 combined primary scalar null values, the minimum possible value is
`1/101=0.009900990099...`; therefore `p_MC<=0.01` is possible only when no null
value reaches the real value. With 50 values, each chain's `Q_0.99` is its
maximum.

Because retained switch states need not be independent or uniformly mixed,
`p_MC` is a frozen finite-chain tail statistic, not an exact inferential
p-value.

The two chains are a frozen dependence/mixing diagnostic. They are not pooled
silently: all gates below compare against both chain-specific references as
well as the combined reference. Both chains begin at the same observed graph,
so this remains a weak mixing diagnostic. Practical switch-chain mixing bounds
are often unavailable and edge-multiple schedules are heuristic; no inferential
or uniform-sampling claim is permitted. The schedule is explicitly a bounded
POC heuristic, consistent with the practical-mixing caveat in current
[SEA 2026 switch-chain work](https://doi.org/10.4230/LIPIcs.SEA.2026.2).

## Frozen robustness views

All views rebuild relation eligibility and evidence weights by the identical
label-free rule after the stated removal. News/user vectors retain the original
50 coordinates and normalization; removed-anchor coordinates remain present,
but their graph rows are zero.

1. **Primary:** every property in the frozen relation vocabulary.
2. **Metadata blocklist:** remove `P1343, P1424, P5008, P6104, P7867, P8744,
   P9241, P2354, P8402, P10280, P1889` at both endpoints.
3. **Hub removal:** remove all graph edges incident to anchor rows `Q30` and
   `Q22686` at both endpoints.

Each robustness view uses the same two-chain construction, but gives every
relation `30m` burn-in proposals and retains 10 states per chain after `2m`
proposals between states, giving 20 combined null replicas per view. On the
frozen real graphs this is exactly 949,200 metadata-blocklist proposals and
822,100 hub-removal proposals. The full preregistered schedule is therefore
4,774,300 proposals and 280 endpoint-null metric states. Robustness may diagnose
sensitivity but cannot replace the primary result.

The fixed-input compiler must reproduce this pre-implementation budget audit
before randomization:

| View | Eligible relations | H edges | C edges | Proposals |
|---|---:|---:|---:|---:|
| Primary | 110 | 4,481 | 5,529 | 3,003,000 |
| Metadata blocklist | 105 | 4,388 | 5,104 | 949,200 |
| Hub removal | 103 | 3,644 | 4,577 | 822,100 |

A mismatch is `INCONCLUSIVE_INVALID_RUN`, not a scientific miss.

## Numerical and provenance checks

All scientific quantities are binary64 NumPy outputs from one canonical sparse
path, with a direct dense 50-by-50 reference used only for verification. Graph,
degree, edge, operator, and `E` checks apply to every reached real graph and
retained null state. Detailed algebraic parity applies to real H/C states in
every reached view and to the 64 reached primary null states selected by
smallest ascending
`SHA256("20260807|H10A|parity|"+endpoint+"|"+chain+"|"+state)`, breaking a
hash collision by ascending literal `(endpoint,chain,state)`:

Here and in the candidate-pair hash below, `chain` and `state` are unpadded
ASCII decimal and all tuple indices retain the zero-/one-based conventions
frozen above.

- exact preservation of matrix shape, binary entries, edge count, row degrees,
  column degrees, relation set, and frozen `alpha` under every null state;
- no duplicate edges;
- `||Bv||_inf <= 1e-12` and `||B^T u||_inf <= 1e-12` per eligible relation;
- `max_abs(BB^T-(NN^T-uu^T)) <= 1e-12` per relation;
- `max_abs(W_s-(K_s+G_s)) <= 1e-12`;
- `max_abs(K_s-K_s^T) <= 1e-12` and smallest symmetric eigenvalue
  `>= -1e-10`;
- finite values throughout and exact replication of all frozen cohort counts.

Only after a candidate-scoring stage is reached, that stage additionally
requires maximum candidate-level `|a-(z+g)| <= 1e-12` and maximum
sparse-versus-direct score difference `<=1e-12` on every selected
impression/candidate for real states and on the 256 candidate pairs selected for
each reached selected null state by smallest ascending
`SHA256("20260807|H10A|pair|"+view+"|"+endpoint+"|"+chain+"|"+state+"|"+
impression_id+"|"+news_id)`, breaking a hash collision by ascending literal
`(impression_id,news_id)`. Candidate IDs are unique within an impression, so
the pair key is unique. Robustness checks apply only to reached
robustness views. A stage skipped by the frozen futility rule is intentionally
absent, not a parity failure; the verifier must prove that the immediately
preceding failed conjunct required that absence.

The runner writes sorted-key canonical JSON with UTF-8, LF line endings, and no
NaN/Infinity. Its timing-free scientific files are exactly
`scientific_payload.json`, `state_metrics.jsonl`, `state_digests.jsonl`,
`chain_diagnostics.jsonl`, and `parity_checks.jsonl`. A clean replay must
reproduce all five files byte for byte, with all reported SHA-256 hashes equal.
They contain deterministic scientific gates, reached-stage decisions, and
scientific reasons, but no role name, PID, path, timestamp, elapsed value,
resident-memory value, or timing-dependent verdict. Those fields live only in
the separate per-role `result.json` and launcher records. JSONL records use the
same canonical object encoding, exactly one object and one LF per line.

Canonical object bytes are exactly

```text
json.dumps(object,sort_keys=True,separators=(",",":"),
           ensure_ascii=True,allow_nan=False).encode("utf-8") + b"\n"
```

A single-object JSON file contains exactly those bytes. Every JSONL record contains its explicit integer/string
ordering fields and files are emitted in these tuple orders, using view order
`primary < metadata_blocklist < hub_removal`, endpoint order `H < C`, literal
relation-ID order, and ascending integer fields:

```text
state_metrics:      (view_ordinal, endpoint_ordinal, kind_ordinal, chain, state)
state_digests:      (view_ordinal, endpoint_ordinal, chain, state, relation_id)
chain_diagnostics:  (view_ordinal, endpoint_ordinal, relation_id, chain)
parity_checks:      (view_ordinal, endpoint_ordinal, kind_ordinal, chain, state,
                     relation_id_or_empty, check_name,
                     impression_id_or_empty, news_id_or_empty)
```

For aggregate real `state_metrics` and real `parity_checks` records only, use
`kind_ordinal=0,chain=-1,state=0`; aggregate null records use
`kind_ordinal=1`, their nonnegative chain, and
positive retained-state index. Every observed-start `state_digests` record uses
its actual chain `0` or `1` and `state=0`; there is no chain-minus-one state
digest. The ordinal view/endpoint/kind keys, not locale-dependent string
collation, perform the first three sorts. Primary, replay, and the verifier's
canonical path must agree on every scientific value bit and every canonical
record. Only separately named independent
outer-product, direct-score, and scalar-loop semantic checks use `1e-12`.

After normally completed primary and replay roles, a separately hash-authorized verifier must use
an independently written validation path to reconstruct cohort selection and
candidate uniqueness; graph matrices, degrees, relation eligibility, and
weights; every reached deterministic chain and retained-state digest; every
reached raw retained-state metric; numerical identities and fixed-degree
preservation; every reached gate; ordered futility and every intentionally
absent downstream stage; and the terminal verdict. It must bind
primary/replay raw artifacts, authorizations, token/SHA/PID start-and-ack
records, persistent logs, zero-byte asynchronous-error ledgers, and both inner
lock releases for primary and replay. Replay is not a substitute for this
verifier. The verifier has its own inner lock but cannot attest its own release
while running. After it exits, the wrapper must validate and bind the verifier
artifacts and verifier inner-lock release, then release the outer lock before
the completion marker, which is the final filesystem mutation. Nonempty
stderr, a nonempty asynchronous-error ledger, an orphaned owned process, hash
mismatch, or parity failure makes the run `INCONCLUSIVE_INVALID_RUN`. Missing
scientific completion is invalid except for the authenticated resource-terminal
path defined below.

## Preregistered gates and terminal rule

The comparison operators below are literal: `>` and `<` are strict, while
`<=` and `>=` include equality. Every following condition must hold:

### Primary structural gates, separately for H and C

- `V_real > Q_0.99` for the combined 100-null reference and for each 50-null
  chain, and `p_MC <= 0.01` in the combined reference.
- `D_real > Q_0.95` for the combined reference and for each chain.
- `T_real > Q_0.95` for the combined reference and for each chain.
- `R2_deg < 0.80`.

`E` and its null distribution are reported with the same quantiles and tail
count but are descriptive and cannot pass, fail, or rescue a gate.

### Primary coverage gates

- at least 5,000 and at least 50% of the 8,192 impressions are endpoint-usable;
- at least 5,000 and at least 50% are robust-usable;
- `R*` is nonempty at both endpoints by construction, every exact/parity check
  passes, and every `(primary,endpoint,chain)` contains at least one accepted
  swap.

### Robustness no-reversal gates

For each of metadata blocklist and hub removal, separately for H and C:

- real minus `Q_0.5` is strictly positive for `V`, `D`, and `T` in the
  combined reference and separately in each chain-specific reference;
- `R2_deg < 0.80`;
- at least 2,500 and at least 25% of the cohort are endpoint-usable, and at
  least 2,500 and at least 25% are robust-usable;
- relation eligibility is nonempty, every exact/parity check passes, and every
  `(view,endpoint,chain)` contains at least one accepted swap.

### Ordered futility rule

The execution order is frozen because every decision gate is conjunctive:

1. compile the primary real graphs and cohort representations, compute primary
   real operators, descriptive `E`, scores, and `V`, then generate the primary
   chains and compute every primary null operator, descriptive `E`, score, and
   `V`;
2. if any mandatory primary `V` gate misses, serialize all reached `V` and
   descriptive `E` evidence, terminal scientific kill, and skip `D`, `T`,
   `R2_deg`, coverage, and robustness calculations;
3. only after every primary `V` gate passes, compute primary `D`, `T`,
   `R2_deg`, coverage, and the required null ranking metrics; if any primary
   gate misses, terminal scientific kill and skip robustness;
4. only after every primary gate passes, compute metadata blocklist and then hub
   removal. Within a reached view, first compute all H and C real/null operators,
   descriptive `E`, scores, `V`, and required parity, then jointly evaluate all
   H/C `V` conjuncts. Only if all pass, compute all H/C `D`, `T`, `R2_deg`,
   coverage, and required ranking parity and jointly evaluate those remaining
   conjuncts. Any failed joint stage terminally kills the scientific direction
   and skips the next view. `E` remains descriptive in every stage; no
   endpoint-specific early exit is permitted.

Primary and clean replay independently follow this deterministic order. The separate verifier
must reproduce the reached stage and prove that every skipped stage was
downstream of an already-failed conjunct. Futility can save runtime but cannot
change `PASS` into `KILL` or vice versa.

### Module runtime and evaluation-resource gates

For a full primary evaluation, `module_ns` is the sum of two disjoint timed
regions after immutable-input parsing and count validation: (a) construction of
the 50-dimensional news/user representations, selected-cohort sparse candidate
arrays, rank buckets and tie keys, primary real relation compilation,
eligibility/weight construction, operators, and descriptive real `E`; and (b)
primary real residual/degree/raw cohort score generation and primary real `V`.
Rank sorting, `D`, `T`, `R2_deg`, coverage evaluation, null-chain proposals,
null metrics, serialization, and robustness are excluded. Both regions are
always completed before the first `V` futility decision, and their sum must be
at most 30 seconds wall time. A
completed primary module above 30 seconds ultimately emits
`KILL_H10_RELATION_NULL_DIRECTION`.

The authoritative completed-run module measure is the sum of integer
`time.perf_counter_ns()` deltas at those exact boundaries, compared to
`30,000,000,000` without float conversion. Only deterministic scientific and
coverage gates determine a role's reached scientific stage and the contents of
the five byte-identical scientific files. Module timing is recorded separately
and adjudicated only after that deterministic stage has been serialized. If
all primary scientific gates pass, both primary and replay execute the same
robustness path even if either measured module time exceeds 30 seconds. Replay
must reproduce all scientific bytes, not timing bytes. The independent
verifier validates both roles' recorded boundaries, integer arithmetic, and
launcher cross-links; it does not replace either module measurement with a
newly timed verifier execution. A within-harness-budget module-runtime miss
never authorizes the wrapper to skip replay or verification.

The complete evaluation harness through its reached futility stage must finish
in at most 180 seconds wall time in one Python compute process with one
numerical-library thread and no GPU. Primary and clean replay each have that
limit and a 2 GiB peak-resident-memory limit, and the independent verifier has
its own 180-second/2-GiB limits. Harness time excludes only immutable input
hashing and environment capture; it includes manifest streaming, graph
compilation, cohort selection, every reached switch proposal and metric, parity
sampling, serialization, and cleanup. Exceeding a harness time or memory limit
emits `INCONCLUSIVE_RESOURCE_BUDGET`, not scientific evidence against the
mechanism; only implementation optimization that leaves this protocol and all
scientific bytes unchanged may repair it.

For a normally completed role, record integer `time.perf_counter_ns()` start,
stop, and delta values. Launcher enforcement is independently bound to one
`.NET Stopwatch` start/stop record and exact tick/frequency integer comparison.
Authoritative resident memory is the maximum observed Windows
`Process.PeakWorkingSet64` in bytes from the exact authenticated process handle,
sampled once while acknowledgement proves the child is alive, every 100 ms
thereafter, and once after process exit but before disposing the materialized
native process handle. Inability to establish a role's peak from that exact
handle is `INCONCLUSIVE_INVALID_RUN`; it may not silently weaken the 2-GiB gate.

An authenticated resource overrun is a separate valid transport terminal:

1. the wrapper records the authorized role, token/SHA/PID start-and-ack,
   monotonic cutoff evidence, maximum observed `PeakWorkingSet64`, reason
   (`timeout` or `rss`), persistent stdout/stderr, asynchronous-error ledger,
   and a hash/length inventory of every safely published partial artifact;
2. it terminates and waits for the exact owned process tree and proves no owned
   process survives;
3. it releases any held inner lock and the outer lock to append-only evidence;
4. it skips every downstream role: a primary overrun skips replay/verifier, a
   replay overrun skips verifier, and a verifier overrun skips success
   completion; and
5. it writes a distinct `INCONCLUSIVE_RESOURCE_BUDGET` terminal marker last,
   binding the partial inventory and all release evidence. The interrupted
   role's scientific completion and skipped roles are then expected absent.

The resource terminal is admissible only when provenance through the cutoff is
valid, stderr and the asynchronous-error ledger contain no independent error,
all owned processes are dead, and releases/partial hashes verify. Otherwise the
higher-priority result is `INCONCLUSIVE_INVALID_RUN`. Neither a resource marker
nor an invalid run can be used as scientific evidence.

Decision precedence is frozen: invalid execution/provenance first emits
`INCONCLUSIVE_INVALID_RUN`; a valid but exceeded harness time/memory limit next
emits `INCONCLUSIVE_RESOURCE_BUDGET`; only a valid, within-budget reached chain
is scientifically adjudicated. If all full scientific, coverage, and robustness
gates match and pass in primary, clean replay, and independent verification,
and both primary and replay module-runtime gates pass, emit
`PASS_H10A_RELATION_NULL_FEASIBILITY`. **Any admissible
scientific, coverage, robustness, or completed-module-runtime miss emits
`KILL_H10_RELATION_NULL_DIRECTION`; no label or H6 Phase-B artifact may then be
opened.** Either inconclusive state must be repaired and replayed without
changing this protocol or its scientific implementation.

### Environment and count-faithful preflight

The prospective implementation lock must pin SHA-256 for the protocol, runner,
independent verifier, launcher, base interpreter, virtual-environment launcher,
and `pyvenv.cfg`; exact Python and NumPy versions; and one canonical sorted
manifest of every file under the imported NumPy package with relative path,
byte length, and SHA-256. It must also pin a deterministic PCG64DXSM probe digest
covering `random_raw` and the exact `Generator.integers` range pattern used by
the switch chain. The intended environment is CPython `3.12.13` and NumPy
`2.4.4`; any mismatch is invalid, not an alternate run.

The probe seed is the first eight bytes, big-endian, of
`SHA256("20260807|H10A|PCG_PROBE_V1")`. Initialize one PCG64DXSM generator and
execute 128 proposal-shaped probes, cycling `m` through
`(2,3,17,40,41,44,45,48,49,50,51,64)`. For each probe append unsigned LE8
`random_raw()` to a byte buffer and append byte `0x00` if its low bit is zero.
If the low bit is one, append `0x01` followed by unsigned LE8 encodings of
`first` and `second` produced by the exact two scalar `Generator.integers` calls
and increment rule frozen above. Prefix the buffer with ASCII
`H10A_PCG_PROBE_V1\n` and SHA-256 the result. A separately hash-authorized probe
and the independent verifier must agree; the exact expected digest is recorded
in the implementation lock before any launcher preflight or real-input run and
cannot thereafter change without a new protocol amendment.

Before real H10A execution, a launcher-level synthetic performance preflight
must exercise exactly 4,774,300 proposals under the frozen lazy-chain rule, 280 retained endpoint-state
kernel constructions, and 50-by-50 operator arithmetic. The performance fixture
is generated without RNG. For each row of the fixed budget table, number
relations from zero and allocate endpoint edges as `floor(M/R)+1` to the first
`M mod R` relations and `floor(M/R)` to the rest. Use synthetic relation IDs
`S000` onward and 17 columns. For edge slot `t` of relation `r`, use

```text
row = (t + 7*r + 3*endpoint_ordinal) mod 50
column = (3*t + 11*r + 5*endpoint_ordinal) mod 17
```

where `endpoint_ordinal=0` for H and `1` for C. In the hub-removal fixture replace
the row equation by
`row=2+((t+7*r+3*endpoint_ordinal) mod 48)`, explicitly mapping onto rows 2
through 49. This produces unique edges and mobile graphs at the exact view,
endpoint, relation, and edge totals in the table.

The 812 synthetic news patterns are the distinct ten-bit masks for integers
`p=0..811`: anchor `b in {0,...,9}` is present iff bit `b` of `p` is one, so
pattern 0 is empty. Synthetic user row `i` has the four anchors
`(i+13*t) mod 50`, `t=0..3`, each with exact binary64 value `0.5`. Impression
`i=0..8191` has `11+(i mod 50)` unique candidate IDs. In global
impression/candidate occurrence order, occurrence `o` uses pattern `o mod 812`.
Thus the workload has exactly 290,648 candidate occurrences, 290,290 supported
occurrences, 1,354,440 candidate-anchor nonzeros, and 32,768 user-anchor nonzeros.
For each retained state, score only those actual slate occurrences through `V`,
not the 8,192-by-812 Cartesian product. The forced-full-path performance mode
then rescores every cached state through `D/T`, for exactly 280 V score passes
and 280 ranking score passes; its forced control flow is marked synthetic and
can never be interpreted as a scientific gate result.

The implementation lock must bind the checked-in generator and a canonical
fixture manifest containing every count above. The preflight must open no
permitted real input or outcome file, publish only to a separate self-test
directory, and complete primary/replay/verifier roles under 150 seconds and
2 GiB each with exact replay and empty stderr/ledgers. It must also exercise
every counter branch, an immobile relation, repeated retained states and return
to the observed slot array; degree and slot-order preservation; canonical-bin
versus independent-outer-product kernels; sparse scoring and unsupported zero
scores; first-score-anchored non-transitive ties; metric/quantile/tail
boundaries; deterministic scientific futility fixtures; and exact owned-process
cleanup. A
failure authorizes implementation-only optimization and a new implementation
hash/lock; it cannot alter this protocol, seeds, schedule, gates, or scientific
method. Static audit must precede the preflight, and its successful artifact
hashes must be recorded before the real launch.

## Windows-safe execution contract

Implementation is intentionally deferred until after this protocol is committed.
The checked-in PowerShell wrapper launches hash-bound primary, exact-replay,
and separately authorized verifier roles with
`Start-Process -WindowStyle Hidden -PassThru`, the direct hash-bound base
interpreter with `-B -u`, `__PYVENV_LAUNCHER__`, a normalized environment, and
unique persistent `-RedirectStandardOutput` and `-RedirectStandardError` files.
A token/SHA-bound PID start-and-ack record must equal the returned process
handle. `uv run`, nested `cmd`, shell pipelines, command-string interpolation,
and captured transient pipes are forbidden. Set BLAS/OpenMP thread counts to
one before process creation. On timeout or cancellation, terminate and wait for
the exact owned process tree and prove no owned process survives. The outer lock
spans all three roles; per-role inner locks, asynchronous-error ledgers, and
append-only release evidence are mandatory. A success completion marker must
bind primary, replay, and verifier authorizations/start-acks/logs/ledgers,
primary/replay/verifier inner-lock releases, the verifier result, and the outer
lock release; it is published last. The distinct resource-terminal marker has
the analogous reached-role binding specified above. This is the established
pattern that avoids recurrence of the prior Windows thread/pipe exception.

## What a pass would and would not justify

A pass would justify one outcome-aware H10B study; it would show only that RNR
is a fast, nondegenerate structural module on this frozen artifact and that its
effect is not reproduced by the declared finite fixed-degree references. It
would not show that scores improve recommendations, that the switch chains are
uniformly mixed, that the method is causally debiased, or that the method solves
strict cold start. The current manifest has no frozen training split, so H10A
is at most cold-start-compatible.

Before a Tier-A submission claim, H10B must add a genuinely new learned or
certified component beyond the occupied residual and maximin algebra; compare
against KGAT, KGIN, DSKReG, KGCL, KGTrimmer, and strong KG-free recommenders;
use strict debut-item cold-start splits on at least three public datasets and at
least three backbones; include historical/current or controlled revision
snapshots; and demonstrate accuracy, calibration, robustness, runtime, and
component-specific ablations. A fresh post-result primary-source collision
search is mandatory. H10A deliberately cannot declare the contribution
publishable by itself.
