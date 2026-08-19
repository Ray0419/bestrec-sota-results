# Design: measuring ρ(k) under matched (forced) coverage

**2026-08-18. Answers weakness 5.1 of `DERIVATION_COVERAGE_BREAKEVEN.md`. No training required —
this is an eval-only pass over checkpoints that already exist.**

## 1. What must be measured and why the naive version is biased

`ρ(k) = R_cold(k) / R_warm`, where `R_s = P(gold ∈ top-10 of the pool | gold ∈ pool)`.

Measuring `R` at each arm's *natural* coverage is biased: a retriever covers the **easy** cold items
first, so `R_cold | covered` is computed on a favourable subset and rises artificially as coverage
expands. The bias runs **toward** our own conclusion, which makes it disqualifying rather than merely
untidy.

**Fix: force coverage to 1 for every event.** Inject the gold item into the pool unconditionally, for
every segment. Coverage is then identical (= 1) across all degree buckets by construction, so no
retriever-induced selection can enter `R`. This is the "positive-controlled regime" of
arXiv:2604.16318, used here as a measurement instrument rather than as a benchmark.

**Direction of the residual bias, stated as a one-sided bound.** Forced coverage averages `R` over
*all* items in a bucket, including items a real retriever would never reach. An intervention that
expands coverage adds items from the currently-*uncovered* set, which are plausibly harder than
average. So forced-coverage `R` **overestimates** the marginal item's `R`, hence **overestimates ρ**,
hence **underestimates π\***. Our claim is `π* → 1`. Therefore:

> if even this optimistic ρ yields π\* near 1, the conclusion holds a fortiori.

The residual bias is one-sided and in our disfavour. That is the property to state in the paper.

## 2. The trap: in a single-stage system the decomposition collapses

First design attempt was to build the pool from **the model's own top-(K−1)** plus the injected gold.
That is degenerate. Let `r` be gold's full-catalogue rank under our scorer:

- `r ≤ K−1` → gold is already inside the model's top-(K−1); pool = top-(K−1), in-pool rank = `r`;
  hit@10 ⟺ `r ≤ 10`.
- `r > K−1` → gold is appended last; in-pool rank = K; never a hit.

So pool-hit@10 ≡ full-catalogue hit@10, and `R` carries no information beyond what we already have.

**The general lesson, which belongs in the paper:** *coverage and conversion are only separable when
the retriever and the ranker are different models.* In a single-stage full-catalogue scorer they are
the same event, and the coverage/conversion decomposition is vacuous. This is why the decomposition is
a statement about **two-stage pipelines**, and it explains why arXiv:2606.29947 could see the split at
all — their generators and rerankers are distinct.

## 3. Design

**Pipeline under test.** Retriever `Q` (produces the pool) ≠ Ranker `M` (our trained checkpoint).

- Pool for a test event: `top_{K−1}(Q) ∪ {gold}` — forced coverage.
- `M` scores the pool; endpoint is `hit@10` of gold within the pool.
- Degree buckets: the existing `DEG_BINS` in `poc_temporal_eval.py`
  `(0,0), (1,2), (3,5), (6,10), (11,20), (21,50), (51,200), (201,∞)`, keyed on the target item's
  pre-cutoff training degree — the same instrument used throughout this program.

**Retrievers `Q` (pre-registered, both reported).**
- `Q_text` — text-kNN over the cached frozen SBERT title embeddings. The natural cold-capable
  content retriever, and the family 2606.29947's dense retrievers belong to.
- `Q_pop` — global popularity. The standard baseline, and the one that structurally cannot reach
  cold items.

**Pool sizes.** `K ∈ {100, 200, 500, 1000}`; `K = 200` is primary because that is 2606.29947's setting.
`π*` is reported as `π*(k, K)`, never as a scalar (weakness 5.3).

**Reference for the ratio.** `R_warm` = event-weighted `hit@10` pooled over `k ≥ 51`.
`ρ(k) = R(k) / R_warm`. `k = 0` is reported but flagged: it is the degenerate bucket where our own
prior work already has cold NDCG exactly 0.

**Checkpoints.** Reuse what exists — 60 MI ladder cells (lr 1e-3), 60 at lr 5e-4, 18 Steam, 6 R1.
For this measurement the primary is the **full-CE arm at the primary LR**, n=5, MI and Steam. Loss
family is not a factor of interest here; the other arms are a robustness appendix.

## 4. Endpoints and the decision that follows

1. `R(k)` and `ρ(k)` per bucket, per `K`, per retriever, n=5, with CIs.
2. `π*(k, K)` computed by substituting `ρ(k)` into
   `π* = c_cov / (g_cov·ρ(k) + c_cov)` using arXiv:2606.29947's **published** trade
   (Yelp `g_cov=+10pp, c_cov=−4.5pp`; Video Games `g_cov=+2.2pp, c_cov=−4.7pp`).
   Their numbers are used as-is and cited; we do not re-estimate them.
3. **Admission threshold** `k̂(K)` = the smallest degree bucket at which `π*(k, K)` falls below a
   plausible deployment prevalence. This is the deliverable of claim (b).

**Falsification, frozen now.** The claim dies if `ρ(k)` is **not** near zero in the low-`k` buckets
under forced coverage — because then `π*` stays far from 1 and coverage-side allocation can pay after
all. Concretely: if `ρ(k) > 0.5` for any bucket at `k ≤ 10` on either dataset, the thesis
"conversion is the binding constraint" is refuted and we report that instead.

**Sanity gate.** ~~`ρ` must be ≈ 1 for `k ≥ 51` by construction of the reference~~ **[SUPERSEDED
2026-08-18 at implementation: only the *pooled* k ≥ 51 reference is ≈ 1 by construction — the
individual warm buckets legitimately differ (head ρ ≈ 1.1–1.5). Replaced by two structural gates,
carried into PREREG_RHO_K_V1 §4: G1 pool-hit ≥ full-catalogue hit (pool ⊆ catalogue), G2 hit rate
monotone non-increasing in K. The prereg's definition governs.]**

## 5. Cost

Eval-only. No training. Scoring a `K`-sized pool per test event is far cheaper than the full-catalogue
pass already run for every one of these checkpoints. Expect the whole matrix (2 retrievers × 4 `K` ×
n=5 × 2 datasets) to be a small fraction of one training run.

## 6. Order of work

1. Implement `poc_pool_conversion.py`: forced-coverage pool construction, both retrievers, degree-
   sliced `hit@10`. Validate on one checkpoint against the sanity gate.
2. Run the matrix on MI, then Steam.
3. Only then write `PREREG_RHO_K_V1.md` — the confirmatory statement of the falsification rule above,
   frozen before the `π*` table is computed.

Step 3 comes last on purpose: steps 1–2 produce an *instrument reading*, and the instrument has a
sanity gate that can fail. The confirmatory claim is about `π*`, and that is what gets pre-registered.
