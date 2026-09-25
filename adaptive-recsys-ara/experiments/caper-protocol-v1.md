# CAPER PoC v1: Preregistered Protocol

Status: outcome-blind and locked before downloading or parsing MovieLens 1M. The executable JSON configuration is `src/configs/caper_poc_ml1m_v1.json`; where a numeric value differs, the committed JSON is authoritative and the discrepancy must be reported as a protocol failure rather than silently repaired after test access.

## Research decision

CAPER tests whether a small, reference-model-free preference residual can correct errors inside the naturally served union of immutable collaborative and semantic FAISS branches, while a deterministic per-request constraint limits regret under the validation-selected BPR score surrogate.

The PoC is promising only if every G1–G9 condition below passes. A failure kills CAPER, prohibits Phase 5, and returns the sprint to Phase 1. There is no discretionary override and no post-test hyperparameter change.

## Fresh dataset and claim boundary

- Dataset: official GroupLens MovieLens 1M archive from `https://files.grouplens.org/datasets/movielens/ml-1m.zip`.
- Inputs: `ratings.dat` plus movie title and genre fields from `movies.dat`. Demographics are excluded.
- Eligible users have at least 50 events. A deterministic seed-20260817 subset of at most 1,000 eligible users is used; fewer than 500 eligible test users fails closed.
- This is an exposed-item, explicit-feedback offline study. It is not a causal utility test and cannot establish million-item production latency.
- The downloaded archive, extracted source files, effective configuration, source, environment, embeddings, factors, indexes, candidate manifests, results, and completion markers are SHA-256 bound.

## Temporal blocks and target blindness

For each retained user, sort interactions by `(timestamp, original_row_id)` and keep equal-timestamp events in an indivisible group. Split groups chronologically into core `A` (60%), alignment `R` (20%), validation `V` (10%), and sealed test `T` (10%), following the deterministic implementation recorded in the effective configuration. Assert strict group order between adjacent blocks. Any empty block or temporal violation excludes the user before the stable subset is selected.

The following sequence is mandatory:

1. Fit BPR item/user factors, popularity, metadata embeddings, feature normalizers, and the two FAISS indexes without `R`, `V`, or `T` labels.
2. Generate and persist the alignment candidate union from `A` history before joining `R` ratings. Only naturally retrieved `R` items may form training pairs.
3. Generate validation candidates from the available `A+R` prefix before joining `V` ratings. Use `V` only to select the stronger BPR identity, the strongest mechanism comparator identity, and registered-grid choices.
4. Freeze identities and choices. Generate test candidates from the available `A+R+V` prefix before joining `T` ratings. Open `T` labels once for final evaluation only.

Targets are never appended to a candidate set. All methods use the same target-blind candidate manifests. The PoC uses temporally prior labels from the same user as legitimate request history; it does not claim user-level out-of-sample generalization.

## Representation and retrieval

Encode each item as `"{title} [SEP] {genres}"` with the locally cached frozen `sentence-transformers/all-MiniLM-L6-v2`, producing L2-normalized 384-dimensional vectors. A user's semantic query is a normalized prefix-only positive centroid with an optional registered low-rating subtraction. Collaborative queries and item factors come from two frozen BPR candidates: implicit BPR and rating-aware BPR. The stronger baseline identity is selected on validation, never by test performance.

Create two immutable `faiss.IndexFlatIP` indexes. After deterministic over-fetching and prefix-seen filtering:

```text
B_u = collaborative top 200
S_u = semantic top 200
C_u = stable_union(B_u, S_u), BPR items first, no post-union truncation
```

Thus `|C_u| <= 400` and `B_u ⊆ C_u`. Candidate recall is reported as `Recall(C_u)` and `Recall(B_u)` with the same future-positive denominator; the variable union is never called Recall@200.

## Preference examples and residual

Within the alignment manifest, form an unordered pair only when both later-rated items were naturally present and their explicit ratings differ by at least two. The higher rating is chosen. A contradiction is a pair on which frozen BPR orders the lower-rated item at least as high. Before any replacement sampling, fail closed unless the raw alignment pool contains at least 300 pair-bearing users, 100 contradictions, and 100 non-contradictions. Cap one common even training-example count deterministically for every residual variant; the balanced schedule may replacement-sample a deficient stratum to reach an exact 50/50 mix, while the uniform ablation uses the identical total count. Report unique and sampled counts.

Every residual variant shares candidate sets, features, architecture, capacity, initialization, batch order, optimizer, epochs, and three seeds. The bounded score is

```text
s_phi(u,i) = standardized_bpr(u,i) + alpha * tanh(g_phi(x_ui)).
```

Features use target-blind scalar context: BPR score, semantic like/dislike cosine, item popularity, user-history length, branch membership, and branch rank. Feature statistics are learned without `V` or `T` labels.

For a chosen/rejected pair, CAPER uses the SimPO-derived reference-free margin objective

```text
-log sigmoid((beta / temperature) * (s_chosen - s_rejected) - margin)
```

plus the registered soft BPR anchor. The shared union-policy normalizer cancels; no DPO reference model or online language-model decoding is used.

## Constraint and matched controls

Regret normalization uses only immutable BPR-anchor scores:

```text
R_u = max(Q95({b_ui: i in B_u}) - Q05({b_ui: i in B_u}), 1e-6).
```

Semantic-only candidates cannot change this scale. The deterministic feasible projection starts from the BPR top-10 and accepts only positive proposal-gain swaps while the final top-10 loss in summed normalized BPR score remains within the registered `0.12` budget. Movie ID breaks ties; a degenerate scale or failed assertion returns the BPR list. This is a greedy feasible map rather than an optimal constrained solver, and it bounds a BPR surrogate rather than true relevance.

Primary controls are implicit BPR, rating-aware BPR, projected tuned linear fusion, projected zero-margin residual, projected unanchored residual, projected uniform-pair residual, and full projected CAPER. Unprojected soft-anchor-only and unanchored variants are safety diagnostics. The G2 comparator is the strongest constraint-matched ablation selected on `V`, not the maximum observed on `T`.

## Evaluation

- Relevance cohort: fixed test users with at least one `T` item rated at least 4. Report binary NDCG@10 and Recall@10 against all such future items.
- Preference cohort: within-user, naturally retrieved `T` pairs with rating gap at least two. If a user has more than 100 eligible pairs, choose 100 by a preregistered seed-and-user keyed hash rather than item-ID order; report raw and selected counts. Compare pre-projection scalar scores; ties score 0.5. User-macro accuracy is primary and pair-micro accuracy diagnostic.
- Dislike intrusion@10: fraction of the returned top 10 that appears among that user's `T` items rated at most 2. Unknown items are not dislikes.
- Inference: 10,000 paired user-cluster bootstrap draws with seed 20260917. Average each user's metric over the three registered residual seeds, then resample users. Seeds and pairs are not treated as independent observations. Use two-sided percentile 95% intervals.
- Latency: CPU only and one thread for Python numerical libraries, PyTorch, and FAISS. After warm-up, include query lookup, both searches, seen filtering, union, features, scoring, projection, and sorting; exclude training, item encoding, index construction, and disk I/O. Interleave methods on the same registered users. Compare worst-seed CAPER p95 with the identically instrumented dual-index linear-fusion path.

## All-or-nothing promise gate

1. **G1 relevance:** CAPER mean NDCG@10 is at least 2% relatively above the validation-locked stronger BPR, and the paired 95% lower bound of the absolute difference is positive.
2. **G2 mechanism:** CAPER point NDCG@10 exceeds every constraint-matched projected ablation, and its paired lower bound versus the validation-locked strongest ablation is positive.
3. **G3 alignment:** user-macro held-out pair accuracy is at least 0.03 absolute above the locked BPR and the paired lower bound is positive.
4. **G4 top-rank safety:** the paired lower bound for CAPER-minus-BPR Recall@10 is greater than -0.005.
5. **G5 support:** `B_u ⊆ C_u` pointwise and `Recall(C_u) >= Recall(B_u)` pointwise, with the registered 200/400 bounds.
6. **G6 dislike safety:** the paired 95% upper bound for CAPER-minus-BPR dislike intrusion@10 is at most 0.002.
7. **G7 stability:** at least two of three CAPER seeds beat both the locked BPR and locked G2 comparator in NDCG@10.
8. **G8 latency:** worst-seed CAPER p95 is at most 20 ms and at most 1.25 times matched linear fusion.
9. **G9 integrity:** matrix/index hashes are unchanged, target injection count is zero, temporal/provenance assertions pass, the runner has exited, its exclusive lock is released, all completion-bound artifact hashes verify externally, and the asynchronous error ledger is empty.

Missing/nonfinite values, fewer than 500 eligible test users, fewer than 500 preference pairs, fewer than 300 pair-bearing users, fewer than 100 BPR-agreement pairs, fewer than 100 BPR-contradiction pairs, an empty comparison cohort, or any integrity failure fails closed.

```text
PROMISING = G1 and G2 and G3 and G4 and G5 and G6 and G7 and G8 and G9
```

## Windows-safe execution contract

The outcome is launched by the configured venv Python with `-u`, CPU-only/single-thread environment variables, persistent stdout/stderr, an exclusive protocol lock, a new append-only run directory, an empty asynchronous-error ledger, and candidate/final completion markers. An external verifier runs only after process exit, verifies lock release and every bound hash, and publishes the sole authoritative external completion marker.
