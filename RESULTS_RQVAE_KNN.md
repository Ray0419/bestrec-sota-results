# RQ-VAE Semantic-ID kNN Retrieval: TIGER-inspired Closed-Form Proxy

Produced 2026-05-22 (in-progress; final numbers populated after the run completes).

## 1. What this is — and what it is not

This report documents a **TIGER-inspired closed-form proxy** for the BEST-Rec /
LC2C strict-confirmatory pipeline. It is **NOT** a faithful reproduction of
TIGER (Rajput et al., NeurIPS 2023) nor of LIGER (Yang et al., 2024). Per
`RESEARCH_TIGER_LIGER.md`, a full reproduction would have cost roughly
$120–$450 in GPU rentals and weeks of integration with `facebookresearch/liger`.
We instead implement section 4 of that research note — the "minimum-viable
closed-form proxy":

1. Train an **RQ-VAE** on warm SBERT title embeddings (4-layer residual VQ,
   EMA codebook updates, straight-through estimator).
2. Quantize every item (warm + cold) to an L-token **semantic ID**.
3. Build an item–item semantic similarity matrix S_semantic from the
   semantic IDs (one of: Hamming on codes, cosine on decoder reconstruction,
   cosine on quantized continuous vector). Best option chosen per dataset
   on inner validation.
4. Score `score(u, j) = Σ_{w in user_history} S_semantic[w, j]` for all
   items `j` (the same shape as the existing `content_direct` baseline).

The proxy strips out the autoregressive Transformer decoder that gives TIGER
its sequential modelling power, **and** strips out the dense-text refinement
that LIGER uses to recover cold-start performance. What remains is the
discrete-semantic-ID content prior: the simplest test of "does the RQ-VAE
quantization step itself contribute over raw SBERT cosine similarity?".

### Honest disclaimer

The strict-pipeline baseline audit should mark this method as:

    fidelity: rqvae_semantic_id_knn_proxy_not_official_tiger_or_liger

This is the same fidelity tier used for the simplified DropoutNet. A faithful
TIGER (Transformer decoder, beam search, autoregressive semantic-ID
generation) and a faithful LIGER (TIGER + dense text refinement) remain
camera-ready follow-ups.

## 2. Method details

- **Encoder/decoder.** 2-layer MLP: `384 -> 256 -> 128 (latent) -> 256 -> 384`.
- **Bottleneck.** L residual VQ layers, each with `num_codes` codewords of
  dimension 128. EMA codebook updates with decay 0.99, Laplace-smoothed
  cluster normalisation, dead-code reset every 20 epochs (codewords idle
  for > 100 steps are reseeded from a current encoder-output sample).
- **Loss.** Reconstruction MSE + `commitment_cost · Σ_l ‖z_l − e_l.detach()‖²`
  (codebook updates are EMA, not gradient-based).
- **Optimizer.** Adam, lr 1e-3, batch size 512.
- **Training schedule.**
  - Inner HP sweep: 150 epochs per `(L, num_codes, commitment_cost)` triple.
  - Final per-fold model: 200–400 epochs depending on dataset
    (`beauty`/`fashion`: 400; `instruments`: 250; `books`: 200).
- **HP grid.** `L ∈ {2, 4, 6}` × `num_codes ∈ {128, 256}` ×
  `commitment_cost ∈ {0.1, 0.25}` × `sim_option ∈ {Hamming, cos-recon, cos-quant}`.
  Per-fold inner validation: 20% of warm items held out; train RQ-VAE on the
  remaining warm; score the held-out items against full catalog; pick the
  4-tuple with highest inner-val NDCG@10.
- **Multi-seed.** 3 seeds (20260521, 20260522, 20260523) on
  beauty/fashion/instruments; single seed on books (compute budget).

## 3. Evaluation protocol

Full-catalog cold-item evaluation, identical to the strict confirmatory
pipeline (`_bestrec_run/run_all_confirmatory.py::eval_full_catalog`):

- 5-fold item GroupKFold (`run_cold_item.make_item_kfold`).
- For each fold, hold out 20% of items as "cold"; train on the remaining
  warm items + their interactions.
- For each (user, cold-item-target) test pair: rank that target against
  ALL items, mask only the user's training items, compute NDCG@10/HR@10/MRR.
- Same semantic-similarity `S_semantic` is used for warm and cold items —
  i.e. **no EASE warm head is bolted on**. This is the honest TIGER-style
  retrieval comparator (TIGER itself does not get a closed-form warm head).

## 4. Headline results

_Filled in after the run completes; see `_bestrec_run/results_rqvae_knn.json`._

### NDCG@10, mean ± std

| Dataset | n_users | n_items | RQ-VAE-kNN (proxy) | content_direct (ref) | CDR_validated (ref) |
|---|---|---|---|---|---|
| beauty | 253 | 356 | TBD | 0.1449 | 0.1461 ± 0.0069 |
| fashion | 513 | 614 | TBD | 0.1338 | 0.1353 ± 0.0142 |
| instruments | 3,911 | 2,269 | TBD | 0.0355 | 0.0534 ± 0.0020 |
| books | 14,407 | 13,164 | TBD | 0.0272 | 0.0535 ± 0.0013 |

### Per-USER paired Wilcoxon vs content_direct (Holm-corrected over 4 datasets)

_Filled in after the run completes. Test: one-sided, target > baseline.
Per-user NDCG@10 is averaged over folds (and seeds for beauty/fashion/instruments)._

### Chosen hyperparameters per dataset

_Filled in after the run. Pattern emerging from beauty fold-0 inner sweep:
small L (2) with large codebook (256), commitment_cost ≈ 0.1, Hamming
similarity. Each fold selects independently; we report the modal selection._

## 5. Comparison & interpretation

(To be filled in after the run.) Headline points planned:
- The proxy quantizes 384-d SBERT into L tokens of 128-d codewords each;
  semantic-ID kNN inherits the SBERT semantic prior modulo the quantization
  bottleneck. **It is therefore expected to be in the same neighbourhood as
  `content_direct`**, not to dominate the EASE-fused `CDR_validated`.
- Where it beats `content_direct`, the gain is attributable to the
  RQ-VAE bottleneck discovering useful semantic clusters (the discrete
  Hamming-style similarity collapses noise that the raw cosine retains).
- Where it loses to `CDR_validated`, the gap is the EASE warm head and
  validated alpha-blend that the proxy intentionally does not include.

## 6. Reproducing

```
cd C:/Users/rayxc/Documents/R
_bestrec_run/.venv/Scripts/python _bestrec_run/run_rqvae_knn.py \
    beauty fashion instruments books \
    --seeds 20260521,20260522,20260523
```

Artefacts written:
- `_bestrec_run/results_rqvae_knn.json` — per-(dataset, seed, fold) metrics +
  chosen HPs + per-user mean NDCG@10.
- `_bestrec_run/results_rqvae_knn_perpair_<dataset>.jsonl` — one record per
  (seed, fold, user_id, target_item_id) with `ndcg10`/`hr10`/`rr` and the
  chosen HP tuple.

## 7. Citations

- TIGER: Rajput et al., *Recommender Systems with Generative Retrieval*,
  NeurIPS 2023 ([paper](https://papers.neurips.cc/paper_files/paper/2023/file/20dcab0f14046a5c6b02b61da9f13229-Paper-Conference.pdf)).
- LIGER: Yang et al., *Unifying Generative and Dense Retrieval for Sequential
  Recommendation*, 2024 ([arxiv 2411.18814](https://arxiv.org/abs/2411.18814)).
- Research note: `RESEARCH_TIGER_LIGER.md` (this proxy implements section 4).
- Baseline audit fidelity flag aligns with the simplified DropoutNet pattern
  documented in `_bestrec_run/artifact_utils.py::FIDELITY_FLAGS`.
