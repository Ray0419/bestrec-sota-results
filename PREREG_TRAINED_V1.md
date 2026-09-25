# PREREG: trained cold-start arms, and the metric-as-loss test (V1)

**Frozen 2026-08-12, before any run of this design.** Answers rigor-review finding **F04** (no trained cold-start baseline anywhere in the program) and tests the maintainer's hypothesis: *can our offset-invariant evaluation metric be used as a training objective to produce a genuinely better cold-start model?*

## 1. Novelty position (checked 2026-08-12, before GPU)

Occupied and credited: **DropoutNet** (NeurIPS 2017) randomly swaps CF for content embeddings during training; **"Let It Go? Not Quite"** (RecSys 2025) uses frozen content + a norm-clipped trainable delta; sampled-softmax analyses (TOIS 2024) study negative-sampling effects on long-tail; contrastive cold-item work (2604.12990) induces sparsity in predicted probabilities.

**Not found in any search:** a loss that restricts the softmax competitor set to a *simulated cold pool* so that cross-pool score offsets cancel in the gradient — i.e. the offset-invariant evaluation quantity used directly as the training objective. That is arm **T2b** and it is the novel element; T1 and T2a are credited reimplementations serving as baselines.

## 2. Arms (all on the identical backbone, temporal protocol, initialization-paired)

| arm | description | status |
|---|---|---|
| **B0** | stock text backbone (existing `results_TEMP_*`) | reference |
| **T1** | content anchor: base = text projection + trainable delta, L2-clipped at δmax = 0.1 | credited reimplementation ("Let It Go"-style) |
| **T2a** | pseudo-cold **replacement** dropout: each epoch a random 15% of items are represented by their text projection *instead of* their ID row (replacement, not addition — mandated by our k=0 finding that cold rows are corrupted, not merely missing) | credited (DropoutNet-style), adapted |
| **T2b** | **T2a + within-pool CE**: for targets that are pseudo-cold this batch, an auxiliary cross-entropy over *only* the pseudo-cold pool, weight λ = 0.5. Cross-pool offsets cancel by construction, so the gradient can only improve within-pool ordering — the exact quantity our within-pool AUC instrument measures | **novel element under test** |

## 3. Hypotheses and decision rules

Evaluated with the frozen temporal instrument battery (E1 within-pool AUC, E2 efficiency ratio, E4 aggregate at observed π_t), **plus** post-hoc kNN imputation applied on top of each arm so the comparison is like-for-like with the measurement paper.

- **H1 (F04 answer):** T1 and T2a are measurable under the instruments and place somewhere on the efficiency-ratio scale. *No directional prediction — this is the missing baseline, not a horse race.*
- **H2 (primary, the maintainer's hypothesis):** T2b > T2a on **cold NDCG@10 at equal or better warm NDCG@10**, i.e. the within-pool loss converts genuine signal into actual rankability. **Confirmed iff** the cold gain is positive in ≥4/5 seeds with a 95% CI excluding 0 *and* warm loss is not worse than T2a's by more than 0.001 absolute.
- **H3 (mechanism):** if H2 holds, T2b's **within-pool AUC** should rise relative to T2a — showing the loss acted on the quantity it targets, not via a pool offset. If cold NDCG rises while within-pool AUC does not, the gain is an offset artifact and **H2 is withdrawn** (our own §3 result applied to ourselves).

**Kill criteria.** No weight tuning beyond the single pre-declared λ = 0.5 and dropout fraction 15%; no seed additions beyond 3→5 if a CI straddles the decision boundary by <1 SD; if T2b fails, it is reported as the fifth failed algorithmic attempt in the program's corrections log — this program's record is 0-for-4 on algorithms and that prior is stated here in advance.

## 4. Budget

MI, 3 seeds × 3 arms (T1, T2a, T2b) ≈ 9 runs ≈ 40 min GPU; evaluation reuses the existing per-event harness. Steam replication only if H2 confirms on MI (~1.5 GPU-h). Total within the one-day envelope the maintainer authorized.

## 5. What this cannot establish

Whether T2b beats *tuned* production cold-start systems (out of scope); anything about non-sequential architectures; and — if H2 confirms on MI only — cross-domain generality, which the Steam replication would then be required to claim.
