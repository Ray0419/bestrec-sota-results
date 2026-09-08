# H9A RevKron-Cert label-blind feasibility protocol

Status: locked before H9 implementation or H9 score/certificate computation

Date locked: 2026-08-07 (Australia/Sydney)

Classification: prospective label-blind mechanism and certificate-coverage gate

## Research question and claim boundary

H9 asks whether a page/source-aware, anchor-grounded Kron residual can remove
the private-fact degree artifact observed in H6, propagate through shared
external-KG fact signatures, and provide useful deterministic Top-10 invariance
certificates under a transaction-time endpoint-disagreement envelope.

H9A is a label-blind feasibility study of a standard regularized terminal
hypergraph energy and a sufficient Loewner endpoint-box certificate. It claims
no novel ranker, certificate theorem, provenance model, or cold-start outcome.
Kron reduction, inverse-Laplacian ranking, hypergraph/star-expansion
recommendation, singleton cancellation, Loewner monotonicity, graph-perturbation
certification, provably robust recommendation/Top-K, possible-world/x-relation/
lineage Top-K processing, and dynamic/transaction-time KG history maintenance
are prior art. Binding families include Bojchevski-Gunnemann and PORE;
ULDB/x-relation and certain/possible ranking; and HUKA, Wikidated, and
DBpedia-TKG. H9A only decides whether the mechanism is nondegenerate enough to
justify H9B.

H9B's candidate novelty is a provenance-native exact/anytime algorithm for
coupled inverse terminal-hypergraph Top-K invariance across finite, mutually
exclusive page-revision worlds, with a new group-exclusive admissible Kron bound
and search rule plus exact witness worlds. Possible-world semantics,
certain/possible Top-K queries, graph/recommender certification, Kron reduction,
and low-rank inverse updates are independently prior art. H9B must show its
group-exclusive bound is materially tighter than independent-edge envelopes and
generic incremental branch-and-bound, prove a hardness result, and measure real
downstream materialization ambiguity. H9A cannot support that claim by itself.

This experiment concerns a co-fact hypergraph over 50 retained news anchors. It
does not represent outgoing multi-hop Wikidata neighborhoods, and it must not be
described as full-KG multi-hop reasoning. The current manifest also lacks a
frozen train split, so H9A cannot make a strict-cold-item claim.

## Immutable inputs

H9A may open only these inputs:

- MIND-small development `news.tsv`, SHA-256
  `E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822`;
- MIND `relation_embedding.vec`, used only for its 1,091 relation identifiers,
  SHA-256 `D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A`;
- H5 run-003 `facts.jsonl`, SHA-256
  `13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D`;
- committed H6 Phase-A result, SHA-256
  `B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF`;
- committed H6 label-free cohort manifest, 224,785,295 bytes, SHA-256
  `522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5`;
- committed H6 Phase-A completion marker, SHA-256
  `AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06`.

The runner must reject access to `behaviors.tsv`, H6 Phase-B outcome artifacts,
candidate suffix labels, or any other interaction outcome. H6 manifest candidate
records contain news IDs and label-free H6 structural scores/ranks only. H9 may
read the IDs and may use the H6 ranks only as a declared structural baseline.

The exact ordered top-50 anchor list is read from the committed H6 Phase-A
result. Title and abstract annotations retain an anchor when confidence is at
least 0.90. H9A must reproduce all of these label-free audit counts:

- 42,416 news rows;
- 12,060 news with at least one retained anchor;
- 812 distinct retained-anchor incidence patterns, including the empty pattern;
- 64,443 manifest impressions and 43,374 users;
- 2,422,258 candidate occurrences, with uniqueness only within an impression;
- 512,071 supported candidate occurrences;
- 48,422 impressions with more than 10 total candidates;
- 17,436 of those with more than 10 supported candidates;
- 44,341 of those with at least two supported candidates;
- all 64,443 histories with at least one supported news item.

## Frozen graph compiler

Let the fixed boundary vertex set `A` be the ordered 50 anchors. A fact signature
is `f=(property_id,target_qid)`. Retain only facts whose property is in the
frozen 1,091-relation MIND vocabulary. For graph state `G`, let `X_G` be the
binary anchor-by-fact incidence matrix on the union fact universe, `D_A` its
anchor-degree diagonal, and `D_F` its fact-degree diagonal. Degree-zero fact
columns remain in the common universe and contribute zero.

The anchor-grounded Kron/Dirichlet operator is

```text
R_G = D_A - X_G D_F^dagger X_G^T
    = sum_f [Diag(a_f) - a_f a_f^T / d_f],  d_f > 0,
Q_G(gamma) = gamma I_50 + R_G.
```

Here `a_f` is a fact's anchor-incidence vector and `d_f=1^T a_f`. A singleton
fact contributes exactly zero. This anchor-only grounding is frozen as primary;
the degree-sensitive all-node-grounded alternative may be reported only as an
ablation and cannot rescue a miss.

The primary grounding is `gamma=1` exactly: one unit of anchor grounding for
unit incidence conductances. Fixed `gamma=0.1` and `gamma=10` runs are
non-selective sensitivity reports. They may not select or rescue the primary.
Normalized Laplacians, state-dependent normalization, TF-IDF, learned weights,
graph-dependent gamma, or graph-dependent news/user vectors are forbidden.

For a fixed boundary potential `v`,

```text
v^T R_G v = min_y sum_(q,f in E_G) (v_q-y_f)^2.
```

Therefore edge inclusion `E_1 subset E_2` implies `R_1 <= R_2` in Loewner
order. Adding anchor `a` to a fact of existing degree `d` is the PSD update

```text
d/(d+1) * (e_a-a_f/d)(e_a-a_f/d)^T.
```

## Frozen user, item, and residual score

For news incidence `z in {0,1}^50`, define `x=z/||z||_1` when nonempty and
`x=0` otherwise. For each manifest history, retain its supplied last 50 news
items, convert every nonempty item to its fixed simplex vector, preserve
duplicates and positions, and let `p` be their arithmetic mean. Empty history
patterns do not enter the mean. The locked cohort guarantees that `p` exists.

For candidate `i`, let `b_ui=p_u-x_i`, `g_i=1[x_i is nonempty]`, and

```text
E_0(u,i) = ||b_ui||_2^2 / gamma,
E_G(u,i) = b_ui^T Q_G(gamma)^(-1) b_ui,
r_G(u,i) = g_i * (E_0(u,i)-E_G(u,i)),
z_ui = -E_0(u,i),
S_G(u,i) = z_ui + r_G(u,i).
```

For supported candidates, `S_G=-E_G`. For unsupported candidates, the KG
residual is exactly zero and `S_G=z_ui`; they are retained in the full catalog
and never silently filtered. Since `Q_G >= gamma I`, `r_G` is nonnegative in
exact arithmetic.

This exposes the intended modular interface: a later KG-independent base score
`B_ui` may use `B_ui + lambda r_G` for fixed `lambda>=0`. H9A fixes the
graph-independent entity-distance baseline `z_ui` and `lambda=1`; it performs
no tuning and reads no outcomes.

Call `S_G` a ridge-regularized terminal Green-energy score, not a Rayleigh
quotient or classical effective resistance.

## Endpoint-disagreement envelope

For every anchor page, H5 supplies a historical endpoint `H` and current
endpoint `C`. Construct four states on the fixed universe:

```text
I = H intersection C,
H = historical,
C = current,
U = H union C.
```

Thus `R_I <= R_H,R_C <= R_U` and
`Q_U^(-1) <= Q_H^(-1),Q_C^(-1) <= Q_I^(-1)`.

This is sound for the declared endpoint-sandwich edge box
`{G: E_I subset E_G subset E_U}`. It is not claimed to cover transient facts
absent from both endpoints, nor to be the exact set of revision-feasible or
materialization-feasible histories.

For a supported candidate, exact-arithmetic score bounds are

```text
lower_i = -b_i^T Q_I^(-1) b_i,
upper_i = -b_i^T Q_U^(-1) b_i.
```

Equivalently, the unified residual bounds are

```text
lower_i = z_ui + g_i(E_0-E_I),
upper_i = z_ui + g_i(E_0-E_U).
```

For an unsupported candidate, these reduce to `lower_i=upper_i=z_ui`. A future
fixed base `B_ui+lambda r_G`, `lambda>=0`, inherits the same bounds after
replacing `z_ui` by `B_ui` and multiplying the residual terms by `lambda`.

## Frozen robustness views

All views keep the same 50 coordinates and the same `p,x,b` vectors.

1. Primary: all frozen MIND relation IDs.
2. Metadata blocklist: remove properties `P1343, P1424, P5008, P6104,
   P7867, P8744, P9241, P2354, P8402, P10280, P1889` from all four states.
3. Hub removal: delete every graph edge incident to anchors `Q30` and `Q22686`
   from all four states. Do not remove their coordinates and do not renormalize
   any news/user vector.

The pre-protocol label-blind support audit found 401 historical and 487 current
multi-anchor fact nodes in the primary view (1,205 and 1,649 shared incidence
edges). Hub removal retains 221 and 324 multi-anchor fact nodes (727 and 1,123
shared incidences). These figures authorize implementation but are not H9
algorithm results.

## Deterministic ranking and numerical certificate

The mathematical `Q_G` is assembled as an exact `Fraction` 50-by-50 matrix from
integer incidences and rational `1/d_f` weights. Every non-dyadic rational enters
`mpmath.iv` only as `iv.mpf(integer_numerator)/iv.mpf(integer_denominator)`.
It must never pass through float, decimal, or an `mpf` point first; only integers
and dyadic rationals may enter as degenerate intervals. Interval Gaussian
elimination at 80 decimal digits, repeated independently at 160 digits, must
return a finite entrywise inverse enclosure `K_box=[K_lo,K_hi]`. The 160-digit
box is the decision box; it must be a subset of the 80-digit box and have maximum
entry width at most `2^-80`. Failure invalidates the run rather than weakening a
certificate.

Let `Khat` be the nearest-binary64 midpoint of the 160-digit decision box and
let `Delta_K` be the smallest outward-binary64 nonnegative radius for which
`[Khat-Delta_K,Khat+Delta_K]` contains that box entrywise. Extract every interval
endpoint as its exact binary `mpf` tuple, compare it to `Fraction.from_float`,
and apply `nextafter(.,+infinity)` until containment is exact. This check covers
both midpoint and radius conversion; merely rounding either one is insufficient.

`Khat` is the one and only canonical nominal inverse. The optimized cache below
computed from `Khat` supplies nominal scores, `tau_score` groups, and ranks.
Float64 Cholesky solves of rational `Q` and an independent 160-digit point solve
are parity checks only; neither may replace or selectively alter a canonical
score.

The score enclosure must cover the actual cached path. Let `u=2^-53`,
`gamma_n=n*u/(1-n*u)`, `Zhat` be the binary64 pattern matrix, and `Delta_Z` the
smallest elementwise outward radius enclosing every exact rational pattern entry,
verified with `Fraction.from_float`. Let

```text
Bhat = fl(Zhat Khat)
Ahat = fl(Bhat Zhat^T)
z1 = max_s ||Zhat[s,:]||_1
kmax = max_ab |Khat[a,b]|
dkmax = max_ab Delta_K[a,b]
bmax = max_ab |Bhat[a,b]|
eB = gamma_100 z1 kmax
eA = eB z1 + gamma_100 bmax z1
```

Here and below every displayed nonnegative bound is accumulated upward with
`nextafter`; `gamma_100` conservatively covers every length-50 BLAS dot product,
including multiplication, addition, reassociation, and FMA. IEEE-754 round-to-
nearest and finite operands are runtime assertions.

For a history, aggregate its nonempty pattern counts into exact weights `w`,
convert them to `what`, and construct an outward `Delta_w` by exact-Fraction
comparison. For candidate pattern `t`, define

```text
rw1 = ||Delta_w||_1
rz1 = max_s ||Delta_Z[s,:]||_1
rp1 = rw1 + ||what||_1 rz1
rb1 = rp1 + ||Delta_Z[t,:]||_1
v1 = ||what||_1 + 1
vb1 = v1 z1
vabs1 = vb1 + rb1
kabsmax = kmax + dkmax
delta_input = rb1 kabsmax vabs1
            + vb1 dkmax vabs1
            + vb1 kmax rb1
delta_cache = eA v1^2
```

`v1` is an upward real-arithmetic bound on `||what-e_t||_1`; no rounded
subtraction `what-e_t` is used in an enclosure bound.

Compute the canonical cached center exactly through

```text
qhat = fl(Ahat[supp(w),supp(w)] what)
phat = fl(what^T qhat)
chat = fl(what^T Ahat[supp(w),t])
Ehat = fl(phat - 2 chat + Ahat[t,t]).
```

With `h=|supp(w)|`, `amax=max_ab|Ahat[a,b]|`, and all norms below evaluated on
the displayed binary64 operands, the frozen arithmetic bound is

```text
eq = gamma_(2h) amax ||what||_1
ep = ||what||_1 eq + gamma_(2h) ||what||_1 ||qhat||_infinity
ec = gamma_(2h) ||what||_1 amax
ef = gamma_8 (|phat| + 2|chat| + |Ahat[t,t]|)
delta_round = ep + 2 ec + ef
delta_E = delta_input + delta_cache + delta_round
epsilon_cap = 2^-38 * max(1,1/gamma).
```

These inequalities follow by three add-and-subtract perturbation terms for
`b^T K b`, followed by the standard dot-product `gamma_n` bound. Every score is
invalid unless its upward-rounded `delta_E <= epsilon_cap/4`. An independent
160-digit direct `b^T K b` audit must fall inside the resulting interval for
every distinct supported candidate pattern in the fixed 1,024-row audit and for
all 812 pattern self-energies; its maximum center discrepancy must also be at
most `epsilon_cap/4`.

The global-path cross term uses the already-computed `chat`, never a nominal-only
comparison. With `rx1=||Delta_Z[t,:]||_1`, `px1=||what||_1 z1`,
`xx1=||Zhat[t,:]||_1`, `pabs1=px1+rp1`, and `xabs1=xx1+rx1`, define

```text
delta_path_input = rp1 kabsmax xabs1
                 + px1 dkmax xabs1
                 + px1 kmax rx1
delta_path_cache = eA ||what||_1
delta_path_round = gamma_(2h) ||what||_1 amax
delta_path = delta_path_input + delta_path_cache + delta_path_round.
```

All terms are rounded upward. The path audit is invalid unless
`delta_path <= epsilon_cap/4`; its rigorous interval is
`[nextdown(chat-delta_path),nextup(chat+delta_path)]`.

The audit rows are frozen as follows. Number manifest rows from zero in committed
file order and compute
`SHA256(UTF8("H9A-AUDIT|20260807|") || UTF8(impression_id) || 0x00 ||
ASCII(decimal(row_index)))`. Sort by `(32-byte digest,row_index)` and take the
first 1,024 rows. No seed, ordering, or audit row may be implementation-selected.

For supported candidates the point-state score interval is

```text
[s_G^lo,s_G^hi] = [nextdown(-(Ehat+delta_E)),
                    nextup(-(Ehat-delta_E))].
```

For unsupported candidates, compute `E_0` as an exact `Fraction`, use its nearest
binary64 value as the canonical nominal score, and take the adjacent outward
binary64 endpoints proved by `Fraction.from_float` comparison to contain the
exact `-E_0`. Use that same interval in every graph state. The generic cached
`E_G` expression must never bypass this residual gate for the empty pattern.

Every float check is frozen at these scale-aware tolerances:

```text
tau_score = 1e-10 * max(1,1/gamma),
tau_matrix = 1e-12 * max(1,||R_U||_2),
tau_residual = 1e-12 * max(1,||Q||_2),
tau_parity = tau_score/8.
```

Exact edge/fact inclusion and singleton identities are checked exactly.
Row-sum, symmetry, PSD/Loewner eigendiagnostics, Cholesky residuals, independent
matrix assembly, endpoint containment, and pattern/direct-score parity use the
corresponding frozen tolerance above. The interval enclosure, not a float
eigenvalue, supplies certificate soundness.

Canonical nominal H9 rankings use descending `Khat`-cache scores grouped by the
same deterministic
first-score-anchored `tau_score` rule in every process. Within a group, use
ascending SHA-256 of `20260807|impression_id|news_id`, with news ID as collision
fallback. A rank is valid only if float64 Cholesky, exact replay, and the
160-digit independent point solve reproduce every group and total order.

Top-10 metrics and certificates use exactly the 48,422 impressions with more
than 10 candidates. Rows with at most 10 candidates are reported but excluded,
not called certified.

Let `T_H` be the nominal historical Top-10. A sufficient membership certificate
uses `lower_i=s_I^lo` and `upper_i=s_U^hi`. It passes only when

```text
min_(i in T_H) lower_i > max_(j outside T_H) upper_j + tau_score.
```

Certificate failure is `UNKNOWN`, not a counterexample, because separate scalar
extrema can require incompatible graph states.

Define the certified lower bound on item `i`'s structural envelope width as
`w_i=max(0,s_U^lo(i)-s_I^hi(i))`. An impression is uncertainty-exposed iff

```text
max_(i in T_H) w_i + max_(j outside T_H) w_j > tau_score.
```

This ranges over every cross-boundary pair and cannot be triggered by numerical
padding alone. The exposed denominator is zero only if there are no such rows;
that case fails the exposed-scale and certificate gates.

A score vector has a guarded H/C change iff at least one candidate's H and C
point intervals are separated by more than `tau_score`. An H/C Top-10 change is
counted only when the canonical sets differ and there exist
`i in T_H\T_C`, `j in T_C\T_H` satisfying both explicit inequalities

```text
s_H^lo(i) > s_H^hi(j) + tau_score,
s_C^lo(j) > s_C^hi(i) + tau_score.
```

H9-versus-baseline Top-10 disagreement uses the identical two-inequality
resolved-swap rule, substituting the outward exact-`Fraction` interval for the
graph-free `z_ui` score on the baseline side.

## Optimized computation

Assemble each 50-by-50 `R_G` directly from fact hyperedge contributions. Do not
construct a candidate-by-fact tensor or a full dense fact Laplacian.

Let `Zhat` contain the binary64 representations of the 812 fixed simplex news
patterns. Cache the unique nominal center block:

```text
Ahat_G = fl(fl(Zhat Khat_G) Zhat^T).
```

For a history represented by normalized pattern weights `w` and candidate
pattern `t`, compute

```text
Ehat_G(t) = fl(phat - 2 chat + Ahat_G[t,t]).
```

For each distinct candidate pattern, compute `delta_input`, `delta_cache`, and
`delta_round` from the frozen formulas above. The cache is usable only with this
outward bound; an empirical parity tolerance is never a certificate.

Process the 224,785,295-byte manifest as a stream and score only distinct
candidate patterns per impression. Retain at most the state/view blocks needed
for the current pass. Primary code uses the 160-digit inverse-box midpoint cache;
float64 Cholesky is an independent rank-parity audit. The deep verifier uses
direct fact-clique assembly plus symmetric eigendecomposition.
For the empty candidate pattern, branch to the fixed `z=-E_0` interval before
using the cached graph-energy expression.

The frozen direct one-hyperedge diagnostic is

```text
C_G = X_G D_F^dagger X_G^T,
d_G(u,i) = p_u^T C_G x_i.
```

It and the label-free H6 shared-fact ranks are reported only to distinguish the
resolvent from direct co-fact overlap; neither is a novel baseline or a rescue
gate.

## H9A hard gates

Every gate uses `gamma=1`. Any valid miss produces
`KILL_H9_KRON_DIRECTION`. All gates are conjunctive. Neither alternate gamma,
all-node grounding, a filtered cohort, nor a changed threshold may rescue H9A.

1. **Integrity and theorem.** All input hashes, schemas, exact audit counts,
   rational/float/interval assemblies, interval-inverse nesting and width,
   inclusion relations, PSD/row-sum checks at their frozen tolerances,
   Cholesky residuals, independent clique assembly, Loewner inequalities,
   endpoint containment, residual nonnegativity, empty-pattern gating, leakage
   guards, and primary/replay/deep-verifier comparisons pass. Synthetic
   exhaustive tests cover singleton invariance, Schur/Dirichlet equality, all
   subgraphs of a three-anchor envelope, strict certificate preservation
   including an equality failure, and rejection of a deliberately
   state-normalized counterexample.
2. **Supported scale.** The single subset
   `{impressions: total candidates > 10 and supported candidates > 10}` must
   contain at least 5,000 rows and at least 10 percent of the fixed 48,422-row
   nonvacuous cohort. Integrity must reproduce its exact locked size of 17,436
   (36.0084 percent).
3. **Revision sensitivity.** Primary historical/current score vectors have a
   guarded change, as defined above, on at least 20 percent of all 64,443
   impressions. Guard-resolved Top-10 membership changes occur on at least 2
   percent of the 48,422 nonvacuous impressions.
4. **Graph dependence.** H9 has a guard-resolved Top-10 disagreement against the
   explicitly frozen graph-free `z_ui=-E_0` score on at least 5 percent of the
   48,422 nonvacuous rows, separately in historical and current states.
5. **Global co-fact paths.** Separately in historical and current states, at
   least 1 percent of the locked 512,071 supported candidate occurrences and at
   least 1,000 distinct manifest impressions have
   an outward lower bound `nextdown(chat-delta_path) > tau_score` for
   `p^T Q_G^(-1) x_i`, where `delta_path` is obtained from the same frozen
   inverse-box, rational-conversion, cache, and dot-product bounds, while user
   and candidate supports share
   neither an anchor nor a direct fact signature. A direct fact signature means
   `N_G(supp(p)) intersection N_G(supp(x_i))` is nonempty. Report `d_G` and H6
   shared-fact Top-10 disagreement; neither may be described as a new baseline.
6. **Certificate utility.** At least 20 percent of all 48,422 nonvacuous
   impressions are certified. The uncertainty-exposed subset must itself contain
   at least 1,000 rows and at least 2 percent of 48,422, and at least 10 percent
   of that subset must be certified. Every certified row must have identical
   canonical historical/current Top-10 membership, with zero exceptions.
7. **Structural robustness.** Separately for the metadata-blocklist and
   hub-removal views: guarded score-vector changes cover at least 10 percent of
   all 64,443 impressions; guard-resolved Top-10 changes cover at least 1 percent
   of the 48,422 nonvacuous rows; certificates cover at least 10 percent of those
   48,422 rows; and guard-resolved H9-versus-`z_ui` Top-10 disagreement covers at
   least 2.5 percent of those rows in both H and C.
8. **Fixed-gamma audit.** `gamma=0.1` and `gamma=10` must pass every numerical,
   inclusion, containment, and certificate-soundness check. Their structural
   rates are fully reported but do not gate or rescue `gamma=1`.
9. **Runtime.** Each primary and exact replay completes within 300 seconds on
   this machine, with peak resident memory at most 2 GiB, one numerical thread,
   and no GPU.

## Reproducibility and Windows safety

The code and separate PowerShell launcher must be hash-locked and committed
before the confirmatory H9A run. A synthetic self-test cannot open any real
input. The launcher must follow
`experiments/WINDOWS_SAFE_EXECUTION_CONTRACT_2026-08-05.md`: direct base/workspace
venv execution (never `uv run`), `-B -u`, all numerical thread bounds set before
NumPy, `CUDA_VISIBLE_DEVICES=-1`, hidden children, persistent stdout/stderr,
PID start/ack handshakes, outer and inner locks, atomic no-overwrite publication,
completion marker last, exact child kill/wait on failure, and invalidation for
any stderr or asynchronous-error-ledger content.

Primary and exact replay must produce identical scientific payloads and
byte-identical compact row manifests. The deep verifier independently assembles
every `R_G`, uses eigendecomposition rather than Cholesky, verifies every state
and outward bound, exhaustively checks 812-pattern/direct-50D score parity,
recomputes all ranks, gates, and certificates, and confirms exact raw-artifact
hashes. No H9 conclusion is valid without all three processes.

## Next-stage decision

If any H9A gate fails, eliminate this direction without switching grounding,
gamma, support filtering, or certificate semantics.

If every gate passes, labels remain closed. The next step is H9B, not an outcome
claim: acquire admissible page-revision states and real materialization-lag
evidence; prove hardness; implement exact/anytime provenance-group branch-and-
bound with low-rank updates; require exact enumeration agreement on small worlds,
zero false certificates, material coverage gain over the endpoint envelope, and
substantial pruning over generic branch-and-bound.

Only a separately locked Phase B may later open labels. It must first acquire a
frozen train/dev temporal split because this development manifest does not prove
strict cold-item status. The future outcome gate requires at least 0.005
nDCG@10 gain with paired user confidence intervals over both graph-free/entity
distance and the committed H6 shared-fact kernel, improvement under the worse of
historical/current states, matched-null attribution, consistent direction in
both robustness views, and positive certificate-controlled fallback value. No
gamma or model selection may use the confirmatory labels.
