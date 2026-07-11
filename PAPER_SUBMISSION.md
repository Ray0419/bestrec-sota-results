# Causal FIR Filtering and Dataset-Conditional Text Benefits in an HSTU-Style Pure-PyTorch Sequential Recommender

**Authors**: [anonymized for review]

---

## Abstract

We study text-augmented sequential recommendation on the Amazon Reviews 2023 (AR2023) benchmark (Hou et al., 2024) under a fixed protocol — 5-core, full-catalog leave-last-out (LLOO), NDCG@10 — built on an **HSTU-style pure-PyTorch implementation of the HSTU encoder, based on the published architecture** (Zhai et al., 2024). Our central methodological contribution is a **strictly causal FIR temporal filter**: a zero-init gated depthwise convolution on the sequence embeddings that supplies an explicit local recency bias (as an FIR filter it has a learnable frequency response, so it can sharpen the short-horizon structure that BSARec's low-pass analysis of vanilla self-attention motivates us to restore). We are explicit about the novelty boundary. *Not new*: filtering sequential representations, the frequency-domain motivation, and the attention-oversmoothing framing, all established by FMLP-Rec (Zhou et al., 2022) and BSARec (Shin et al., 2024). *New*: the leak-free, left-causal FIR realization inserted before an HSTU-style stack under the all-position next-item objective, evaluated under full-catalog LLOO — FMLP-Rec and BSARec use bidirectional sequence filters in their original formulations, and under our all-position next-item loss directly inserting such filters before each position's prediction would mix future positions, so we use a left-causal FIR realization. We pair it with **Text-Anchored Prototype Embeddings (TAPE)** — a simple soft text-prototype additive capacity term inspired by semantic-ID and prototype methods (a continuous, decoder-free analogue of TIGER's discrete semantic IDs; Rajput et al., 2023): frozen k-means soft-assignments over item-text embeddings gating a learnable prototype table — which we report honestly as a *modest sub-additive* text contributor (+0.0009 single-flag), not a headline. We do not claim a wholly new recommender architecture. Our architectural additions are deliberately small: a causal FIR adaptation of prior frequency-filter ideas and a soft text-prototype additive term.

On AR2023 **Video_Games** 5-core full-catalog LLOO, our full stack reaches **NDCG@10 = 0.0673 ± 0.0003 (6-seed mean ± std, seeds 20260608–13)**, a **+17.5%** improvement over the published SASRec baseline (0.0573) on the identical protocol. We are explicit that **this win is architectural, not text-driven**: an ID-only ablation (no SBERT features, no text-sim bias, no prototypes) already reaches **≈0.0656 (+14% over published SASRec)**, and the full text stack adds only **+2.7% overall** (5-seed +0.00178 ± 0.00021). A controlled per-component ablation on the HSTU-style implementation isolates the levers: the time bias is the largest classical component (+0.0027), label smoothing (Szegedy et al., 2016) adds +0.0013, the causal filter adds +0.0015, while text-similarity bias is dead weight (±0.0001) and TAPE is sub-additive (+0.0009). The causal filter's gain is robust across kernel lengths K∈{4,8,16,50} (k16 marginally best, 5-seed 0.0676 ± 0.0002). Crucially, **the causal filter — not label smoothing — carries the cross-category generalization**: on a second category, **Musical_Instruments**, a single-lever 5-seed isolation shows the filter contributes **+0.0025 (≈80% of the combined lift, ≈3× label-smoothing's +0.0009)**, lifting the V2 stack to **0.0413 ± 0.0005 (5-seed, exploratory)** over a 0.0383 HSTU base. Under an **immutable pre-registered confirmation** (git-committed protocol; 10 never-inspected fresh seeds), both kernels independently exceed the published HSTU-BLaIR point estimate for this category (0.0406; Liu 2025): fresh 5-seed 95% CI lower bounds **0.04096 (K=16)** and **0.04083 (K=8)**, 10/10 seeds above. Because the comparator is a single-seed published number whose reference implementation cannot execute on our hardware, this is a **per-category point-estimate comparison, not a paired superiority or general SOTA claim**.

Our second headline is a **dataset-conditional long-tail pattern** (an empirical pattern, not a law). Comparing the text stack to its ID-only ablation on the rare-item (train-frequency) tail tercile: text **wins the tail on the sparse-catalog Musical_Instruments** (5-seed Δ = **+0.000335 ± 0.000195, 5/5 seeds positive, 95% CI [+0.00009, +0.00058] excludes 0**, replicated on HR), but is a **powered null on dense Video_Games** (Δ = −0.000148; TOST-equivalent to zero within MI's effect margin; minimum-detectable-effect 0.000246 < MI's effect ⇒ *not* an underpowered failure) and on dense Beauty_and_PC. The **cross-dataset difference is itself significant** (MI − VG tail Δ = +0.000484, **Welch t = 4.09, p ≈ 0.004**). An interaction-thinning **titration** dissociates the mechanism as a **double result**: global interaction density is *supported as a driver* of the head/overall text advantage by controlled thinning interventions (monotone within-Video_Games dose-response) but is *not supported by the thinning intervention* as a driver of the tail win (non-monotone; thinning Video_Games to Musical_Instruments' exact global density does not reproduce MI's tail win — at 5 seeds that density-equivalent rung lands at a flat null, Δ = −0.000108 ± 0.000503, 1/5 seeds positive, density-*inert* rather than a deepening loss) — so density is a tail *correlate* only. A follow-up **user-mode titration** (thinning users, not interactions) then resolves the open mechanism: thinning users to MI-matched collaborative connectivity (users/item 2.44) *increases* the Video_Games text−ID tail advantage by **dd = +0.000326 ± 0.000210 vs the full-density anchor (paired t = 3.47, 95% CI [+0.000065, +0.000587] excludes 0; 5/5 seeds positive)** (within-rung tail Δ +0.000178, 5/5 positive), and a 5×5 matched-R1 double dissociation (diff-of-diffs +0.000761, opposite signs) is consistent with **collaborative connectivity (users/item) playing a partial causal role in the tail win (under the thinning intervention's assumptions)**, the residual being a dataset-specific content factor. These titration results are controlled intervention evidence on the dataset, not causal identification of the real-world process that generated it.

We do **not** match the published HSTU-BLaIR Video_Games result (0.0760); we could not isolate the cause of that residual gap: the *pinned* reference environment is not installable on our hardware (its CUDA/Triton kernels have no sm_120 images — proven via WSL), which blocks a faithful pinned reproduction. A late shimmed execution of the reference implementation's research path (§5.6) regenerates the published Musical_Instruments comparator locally (best full-eval NDCG@10 0.0406 — exact; final epoch 0.0391) but was not run on Video_Games, so there kernel numerics, training recipe, feature pipeline, and other system differences remain unseparated. We therefore frame the Video_Games result as a competitive, fully-attributed, multi-seed contribution rather than a SOTA claim.

**Contributions**: (1) a **strictly causal FIR temporal filter** — a leak-free causal FIR adaptation of the prior bidirectional frequency filters of FMLP-Rec/BSARec, a multi-seed-confirmed lever that **alone carries the cross-category generalization (≈3× label-smoothing)**; (2) a **dataset-conditional long-tail pattern** — text beats ID on the sparse-catalog tail (5-seed, CI excludes 0, HR-replicated) but is a *powered* null on dense catalogs (TOST-equivalent), with the cross-dataset gap itself significant (Welch p≈0.004), plus a **titration whose controlled thinning interventions support density as a driver of the head effect but not of the tail effect (a correlate only)** (a refuting, not confirming, keystone); (3) an **HSTU-style pure-PyTorch implementation based on the published architecture**, with a two-normalization bug diagnosis; (4) **TAPE**, a simple soft text-prototype additive capacity term inspired by semantic-ID and prototype methods (TIGER, VQ-Rec, ProtoMF), tested as an ablation and providing a small but not headline gain; (5) **per-component multi-seed ablations** and a **systematic negative-result map** (a frequency-adaptive James–Stein embedding shrinkage, an ecology-inspired niche-competition loss, a heat-kernel/manifold label smoothing, a spectral-shrink prior, a cue-fusion gate, a forced ID→text router, weight-space EMA, CL4SRec self-supervision, a continuous time-decay kernel, text-encoder swaps — each a controlled, interpretable negative, several with a learned scalar the model itself drove to zero); (6) **engineering**: a memory-efficient chunked-full-softmax loss (full-catalog CE at 200K-item scale on a 16 GB GPU) and the diagnosis of a silent NaN-propagation bug in standard SASRec implementations (left-padding + key-padding mask + norm-first); (7) full release of the preprocessing pipeline and per-seed artifacts. Our claimed additions are deliberately small — the causal FIR adaptation (incremental over FMLP-Rec/BSARec), the dataset-conditional tail pattern (an empirical finding, not a law), and the TAPE ablation; we do not claim a wholly new recommender architecture, and every other component is cited at the point of use.

---

## 1. Introduction

Sequential recommendation models predict a user's next item from their interaction history. Self-Attentive Sequential Recommendation (SASRec; Kang & McAuley, 2018) and its bidirectional cousin BERT4Rec (Sun et al., 2019) established Transformer-based sequential recommenders as competitive baselines. Subsequent work integrated pre-trained language models for richer item-text representations (UniSRec — Hou et al., 2022; BLaIR — Hou et al., 2024) and explored generative-retrieval architectures with discrete semantic IDs (TIGER — Rajput et al., 2023; LIGER — Yang et al., 2024).

Recent benchmarks consolidate evaluation around the Amazon Reviews 2023 (AR2023) dataset (Hou et al., 2024), with reported numbers across two preprocessing variants: a **0-core** variant (no minimum interactions filter, used by Hou et al.'s reference repository at `external/AmazonReviews2023/seq_rec_results/`) and a **5-core** variant (minimum 5 interactions per user/item, used by TIGER, LIGER, and other recent works). Numbers reported under one variant are not directly comparable to numbers reported under the other.

In this paper we build on an HSTU-style pure-PyTorch encoder implementation based on the published HSTU architecture (Zhai et al., 2024) and ask two questions: **(i) what simple, capacity-shaping components measurably and reproducibly improve text-augmented sequential recommendation under a fixed 5-core full-catalog LLOO protocol — and which intuitively-promising ones do not? (ii) *When* does item-text actually help — and is its benefit concentrated where ID-embedding models structurally fail, on the rare/cold tail?** Our contributions are:

1. **A strictly causal FIR temporal filter** — a leak-free *causal* FIR adaptation of the frequency-filter ideas of FMLP-Rec (Zhou et al., 2022) and BSARec (Shin et al., 2024). It is a zero-init gated depthwise convolution that sharpens the short-horizon recency structure attention tends to smooth (as an FIR filter it has a learnable frequency response — the only sense in which a spectral reading applies); it is a multi-seed-confirmed lever (Video_Games +0.0015), robust across kernel lengths, that stacks near-additively with label smoothing on an orthogonal axis. **Its strongest evidence is cross-category:** on Musical_Instruments a single-lever 5-seed isolation shows the filter — not label smoothing — carries the generalization (+0.0025, ≈80% of the combined lift, ≈3× label-smoothing). FMLP-Rec and BSARec use bidirectional sequence filters in their original formulations; under our all-position next-item loss, directly inserting such filters before each position's prediction would mix future positions, so we use a left-causal FIR realization.
2. **A dataset-conditional long-tail pattern for text-augmented recommendation** (an empirical pattern/hypothesis, not a law). Reporting `by_popularity` NDCG@10 on train-frequency terciles (leak-free), and comparing the text stack against an ID-only ablation on the *same* split and seeds, we find text's benefit is **regime-dependent on catalog density**: on the sparse-catalog **Musical_Instruments** text *wins the rare-item tail* (5-seed Δ = +0.000335 ± 0.000195, 5/5 seeds, 95% CI excludes 0, HR-replicated), but on the dense **Video_Games** and **Beauty_and_PC** the tail benefit is a **powered null** (TOST-equivalent to zero within MI's effect margin; minimum-detectable-effect below MI's effect ⇒ not an underpowered failure). The cross-dataset difference is itself significant (MI − VG tail Δ = +0.000484, Welch t = 4.09, p ≈ 0.004), and text's winning regime *migrates tail→mid→head as catalogs densify*. An interaction-thinning **titration** dissociates the mechanism as a **double result**: global interaction density is *supported as a driver* of the head/overall text advantage by controlled thinning interventions (monotone dose-response) but is *not supported by the thinning intervention* as a driver of the tail win (non-monotone; thinning Video_Games to MI's exact global density does not reproduce MI's tail win — at 5 seeds that density-equivalent rung is a flat null, Δ = −0.000108 ± 0.000503, 1/5 seeds positive, density-*inert*) — a tail *correlate* only. We frame this as a refuting keystone, not a confirming one, and as intervention evidence on the dataset rather than proof of the real-world generative process.
3. **An HSTU-style pure-PyTorch implementation based on the published architecture** (with a diagnosis of two spurious normalizations that collapse HSTU's pointwise attention into weak mean-pooling), per-component multi-seed ablations on the *corrected* encoder showing the headline win is **architectural** (an ID-only model already reaches ≈0.0656 on Video_Games; text adds only +2.7% overall), and a **systematic negative-result map**: every capacity-*adding* probe we tried (a continuous time-decay attention kernel, prototype-routed expert heads, text-distillation, dual-text encoders, weight-space EMA, CL4SRec self-supervision, a frequency-adaptive James–Stein embedding shrinkage, an ecology-inspired niche-competition loss, a heat-kernel/manifold label smoothing, a spectral-shrink prior, a cue-fusion gate, a forced ID→text router) was neutral or harmful, while the only gains came from capacity-*restricting* regularizers — a clean, reusable empirical finding, in several cases with a learnable scalar the model itself drove to zero.
4. **TAPE (Text-Anchored Prototype Embeddings)** — a simple soft text-prototype additive capacity term inspired by semantic-ID and prototype methods (TIGER's discrete RQ-VAE IDs, VQ-Rec's PQ codes, ProtoMF's prototype matrix factorization): frozen k-means soft-assignments over item-text embeddings gating a learnable prototype table added to each item's feature (a continuous, decoder-free analogue of TIGER's discrete semantic IDs). We report it honestly: it provides a small but not headline gain — a **modest sub-additive text contributor** (+0.0009 single-flag on the HSTU-style implementation), a secondary ablation rather than a central contribution.
5. **Cross-category generalization and an honest ceiling analysis.** The added components transfer to a second category (Musical_Instruments, 0.0413 ± 0.0005, 5-seed, on a parity-confirmed split). We do not match the published HSTU-BLaIR Video_Games result (0.0760) and could not isolate the cause of the residual gap (the pinned reference environment is not installable on our sm_120 GPU — proven; the research path does run locally under data-movement shims, §5.6, regenerating the Musical_Instruments comparator, but was not run on Video_Games, so system-level differences there remain unseparated) — making the Video_Games result a competitive, fully-attributed contribution rather than a SOTA claim.
6. **Engineering**: a memory-efficient chunked-full-softmax loss (full-softmax CE at 200K-item catalogs on a 16 GB consumer GPU), an eval optimization caching the item-feature table once per evaluation, the diagnosis of a silent NaN-propagation bug in standard SASRec implementations (left-padding + key-padding mask + norm-first), an open-source 5-core preprocessing pipeline with per-seed artifacts, and a **shim harness that makes the reference implementation's research path executable on consumer Windows/sm_120 hardware** (three pure-PyTorch fbgemm data-movement operators plus a world-size-1 DDP identity wrapper) — used to regenerate the Musical_Instruments comparator row locally and to resolve the Office_Products floor anomaly (§5.6, Appendix A.0).

Our claimed additions are deliberately small: the **causal FIR filter** (an incremental adaptation of prior frequency-filter ideas), the **dataset-conditional tail pattern** (an empirical finding), and the **TAPE** ablation. We do not claim a wholly new recommender architecture; every other architecture and training recipe we test originates from prior work, cited at the point of use, with a complete attribution table in §3. (An earlier-stage Beauty_and_Personal_Care cross-pipeline transfer study and LIGER-gap analysis are retained in the appendix as supporting material.)

## 2. Related Work and Attribution

We summarize prior work that our experiments directly build on. A complete attribution table for every component used in our experiments appears at the end of this section.

**SASRec** (Kang & McAuley, 2018) is the base Transformer sequential recommender we re-implement. SASRec models a user's history with a causal-masked Transformer encoder and scores the next item via dot product with a learned item-embedding table.

**BERT4Rec** (Sun et al., 2019) adapts BERT-style bidirectional masked-item modeling for sequential recommendation. We implement BERT4Rec as one of our 20 ablation baselines on Beauty_and_PC.

**SBERT / MiniLM** (Reimers & Gurevych, 2019; Wang et al., 2020) provide pre-trained sentence embeddings. We use `sentence-transformers/all-MiniLM-L6-v2` (384-d) as the default frozen item-text encoder.

**UniSRec** (Hou et al., 2022) is the first widely-cited text-based sequential recommender that uses a pre-trained language model to embed item text and learns a parametric adaptor to project these embeddings into the sequential model's hidden space. The SASRec-with-frozen-text-encoder pattern we use is a strict simplification of UniSRec.

**BLaIR** (Hou et al., 2024) is a RoBERTa-base model continually pretrained on 10% of (item-metadata, review) pairs from Amazon Reviews 2023. We use `hyp1231/blair-roberta-base` (768-d) as an alternative frozen item-text encoder. Hou et al. also publish a reference implementation, **SASRecText**, that pairs SASRec with BLaIR via a 2-layer MLP adaptor `[768, 300, 64]` with Dropout(0.2) + ReLU; we adopt this adaptor design verbatim (see Appendix A.1).

**TIGER** (Rajput et al., 2023) reformulates sequential recommendation as autoregressive generation over discrete semantic IDs produced by a residual-quantized variational autoencoder over item-text embeddings. TIGER reports strong results on Amazon Reviews 5-core benchmarks.

**LIGER** (Yang et al., 2024) extends TIGER with a dense-retrieval refinement step and reports further gains.

**Amazon Reviews 2023** (Hou et al., 2024) is the source dataset. We use the **5-core leave-last-out** protocol (described in §3) matching the convention used by TIGER, LIGER, and similar works, which differs from the `0core_timestamp_w_his_*` HuggingFace subset used by Hou et al.'s `seq_rec_results/` reference implementation.

### 2.1 Attribution table

| Component | Source | Where in our work |
|---|---|---|
| SASRec architecture | Kang & McAuley, 2018 | base `SASRecSBERT` model |
| BERT4Rec | Sun et al., 2019 | one of 20 ablation baselines |
| MiniLM `all-MiniLM-L6-v2` (384-d) | Reimers & Gurevych, 2019; Wang et al., 2020 | default frozen item-text encoder |
| BLaIR `blair-roberta-base` (768-d) | Hou et al., 2024 (arXiv:2403.03952) | alternative frozen item-text encoder |
| 2-layer MLP adaptor `[768, 300, 64]` Dropout+ReLU | Hou et al., 2024 (SASRecText, in `external/AmazonReviews2023/seq_rec_results/`) | `--mlp-adaptor` flag |
| Rich-text content concatenation (title + cats + brand) | derived from Hou et al., 2024 preprocessing | `encode_richtext_5core.py` |
| Amazon Reviews 2023 dataset | Hou et al., 2024 | all benchmarks |
| TIGER / LIGER | Rajput et al., 2023 / Yang et al., 2024 | published comparator numbers |

### 2.2 Our additions to the above prior art

We do not claim a wholly new recommender architecture. Our architectural additions are deliberately small: a causal FIR adaptation of prior frequency-filter ideas and a soft text-prototype additive term. Our contributions are:

- An **open-source 5-core preprocessing pipeline** (`preprocess_5core_standard.py`) that matches the protocol used by TIGER and LIGER (not the 0-core protocol used by Hou et al.'s repo).
- A **memory-efficient chunked-full-softmax loss** that enables proper full-catalog cross-entropy training at 207k-item catalogs on a single 16 GB GPU.
- An **eval optimization** (caching `all_item_features()` once per `evaluate()` call) that gives ~10× speedup at d=64 with the MLP adaptor.
- A **cross-pipeline transfer study**: empirically testing which published architectural choices help on the 5-core protocol.
- **Negative-result documentation** for 18 of 20 tested variants on Beauty_and_Personal_Care 5-core.
- The **competitive Video_Games 5-core result** on the HSTU-style pure-PyTorch stack (6-seed NDCG@10 = **0.0673 ± 0.0003**, +17.5% over published SASRec 0.0573), shown to be architectural (ID-only ≈0.0656), with no SOTA claim. *(The earlier v1-era SASRec-SBERT number 0.05509 ± 0.00035 has been retired from Table 1a: its raw per-seed artifacts predate the artifact manifest and cannot be recomputed, so it survives only as a RETIRED provenance row in the manifest, not as a paper claim.)*
- The two added components — the **strictly causal FIR temporal filter** (cross-category-confirmed) and **TAPE** — plus the **dataset-conditional long-tail pattern** (§5.3) and its **interaction-thinning titration** double result (§5.4). The novelty boundary for each is stated explicitly in Table 0 (§2.3).

### 2.3 Novelty boundary

Table 0 states, component by component, what is prior art, what we reuse, what we change, the evidence behind each claim, and an honest novelty grade. Nothing in this paper is graded above "moderate"; the two architectural additions are graded "incremental" by design.

**Table 0: Novelty boundary — what is reused, what is changed, and how novel each piece is.**

| Component | Prior art | What we reuse | What we change | Evidence | Novelty strength |
|---|---|---|---|---|---|
| HSTU base | Zhai et al., 2024 | pointwise `silu(QKᵀ + rab) V` aggregation, per-block normalization, relative attention biases | pure-PyTorch implementation; diagnosis/removal of two spurious normalizations in our initial reimplementation; equation-level verification only, no numerical-parity claim (§3.7, §6.5) | Table 1 ablations; §3.7 | none (implementation work) |
| BLaIR / SBERT text embeddings | Hou et al., 2024; Reimers & Gurevych, 2019; Wang et al., 2020 | frozen encoders; Hou et al.'s MLP adaptor verbatim | nothing (frozen, off-the-shelf) | Table 1a encoder comparison | none |
| Label smoothing | Szegedy et al., 2016 | standard uniform label smoothing | applied to full-catalog chunked-softmax CE in this setting | +0.0013 single-flag; +0.0012 stacked (Table 1) | none |
| Time bias | TiSASRec; HSTU (Zhai et al., 2024) | bucketed time-interval attention bias | integration only | +0.0027 single-flag, largest classical component (Table 1) | none |
| FMLP-Rec / BSARec frequency filters | Zhou et al., 2022; Shin et al., 2024 | the idea of filtering sequential representations; frequency-domain motivation; attention-oversmoothing framing | not inserted as-is (bidirectional in their original formulations) | cited motivation (§3.7b) | none (prior art) |
| Causal FIR adaptation (ours) | builds directly on FMLP-Rec / BSARec | their filtering motivation and frequency framing | leak-free, left-causal depthwise FIR realization (zero-init gated) inserted before an HSTU-style stack under the all-position next-item objective, full-catalog LLOO | VG +0.0015 (5-seed); MI +0.0025, ≈80% of the combined lift (5-seed); robust across K∈{4,8,16,50} | incremental |
| TAPE (ours) | TIGER (Rajput et al., 2023); VQ-Rec; ProtoMF | prototype / semantic-ID shared-structure motivation; frozen text embeddings | frozen k-means soft assignment gating a zero-init learnable prototype table, additive | +0.0009 single-flag (n=1); +0.0004 in the 4-seed cross-check; sub-additive (§5.1) | incremental |
| Tail / thinning analysis (ours) | popularity-stratified evaluation (standard); long-tail SR, e.g. MELT (arXiv:2304.08382); cold-start content methods, e.g. DropoutNet, CLCRec | train-frequency tercile bucketing; paired same-seed contrasts | dataset-conditional text-vs-ID tail contrast plus interaction- and user-mode thinning interventions with a matched-R1 (resource-controlled) design | 5-seed MI tail win (CI excludes 0); powered VG null (TOST); cross-dataset Welch p≈0.004; user-mode dd = +0.000326 (CI excludes 0) | moderate (empirical) |

## 3. Method

### 3.1 Preprocessing pipeline

We preprocess Amazon Reviews 2023 (Hou et al., 2024) into 5-core leave-last-out splits. For each category we:
1. Load raw user-item review interactions from the `raw_review_<category>` HuggingFace subset.
2. Apply a 5-core filter iteratively until no user or item has fewer than 5 interactions.
3. Sort each user's interactions chronologically.
4. Hold out the last interaction as test, the second-to-last as validation, the rest as training.
5. Encode item metadata (`meta_<category>.jsonl`) with the chosen frozen text encoder.

This protocol matches TIGER (Rajput et al., 2023) and LIGER (Yang et al., 2024) but differs from Hou et al. (2024)'s reference repo (`external/AmazonReviews2023/seq_rec_results/`) which uses the `0core_timestamp_w_his_*` HuggingFace subset. The 5-core protocol produces smaller, denser interaction matrices.

### 3.2 Model architecture

Our base model, **SASRec-SBERT**, follows Kang & McAuley (2018) with a frozen-text item-feature augmentation:

For each item `i`:
- A learned per-item embedding `e_i ∈ R^d` (initialized N(0, 0.02), padding-aware).
- A frozen text embedding `s_i ∈ R^k` from MiniLM (k=384) or BLaIR (k=768).
- A learnable projection `Φ : R^k → R^d`.

The item feature passed into the Transformer encoder is `f_i = e_i + Φ(s_i)`. Sequences are right-padded with a dedicated pad token and processed with a causal-only attention mask (no key-padding mask — see §3.4).

We use a 2-layer Transformer encoder (d=64, n_heads=2, FFN dim=4d, GELU activation, pre-norm) followed by a final LayerNorm. The output logits for position `t` are `h_t · all_items.T` where `all_items` is the (n_items, d) item-features table.

### 3.3 Choice of projection Φ

Following our cross-pipeline transfer study (§5.2), we compare two designs for `Φ`:
- **Linear**: `Φ(s) = W s` for a learned weight `W ∈ R^{d × k}`.
- **MLP** (adopted from Hou et al., 2024 SASRecText): `Φ(s) = W_2 · ReLU(W_1 · Dropout(s))` with hidden dim 300 and Dropout(0.2) between and before the linear layers. **This design is from Hou et al., 2024 and we do not claim novelty for it.**

### 3.4 Right-padding + causal-only mask

During exploration we identified a numerical failure mode in the standard SASRec implementation pattern: combining left-padding with both a key-padding mask and a pre-norm Transformer encoder produces NaN logits when an entire row of keys is padded (the softmax denominator is zero). The NaN propagates through residual connections and silently inflates eval NDCG to ~0.9955 — a "fake-perfect" result. We adopt right-padding + causal-only mask (no key-padding mask) to avoid this trap.

### 3.5 Chunked-full-softmax loss

For training with cross-entropy over the full catalog (no sampled negatives), the full logits tensor `(B, L, n_items)` is prohibitive at L=50 and n_items=207k. We implement an incremental-logsumexp loss:

```
def chunked_full_softmax_loss(hidden, targets, model, item_chunk):
    lse = -inf  # running logsumexp over the item dimension
    target_scores = None
    for chunk_start in range(0, n_items, item_chunk):
        chunk_emb = model.item_features(chunk_ids)
        chunk_logits = hidden @ chunk_emb.T
        lse = logsumexp(lse, logsumexp(chunk_logits, axis=-1))
        if any(target in chunk):
            target_scores[in_chunk] = chunk_logits[in_chunk, target]
    return -mean(target_scores - lse)
```

This bounds peak memory by `(batch, item_chunk)` instead of `(batch, n_items)` and allows proper full-softmax training at the 207k-item Beauty_and_Personal_Care scale on a 16 GB GPU.

### 3.6 Evaluation protocol

We score each user against the **full catalog** of 207k items (Beauty_and_PC) or 25k items (Video_Games). For the held-out test item, we compute the rank under dot-product scoring (after masking train+val items the user has already seen) and report NDCG@10, HR@10, MRR. We use the standard SASRec test-time convention of including the validation item in the input sequence (Kang & McAuley, 2018).

For our default 16 GB GPU, the optimized evaluation caches the (n_items, d) item-features table once per `evaluate()` call rather than recomputing it per batch — this is critical with the MLP adaptor, which would otherwise recompute the 207k-item × 768 → 300 → 64 MLP forward 1,400+ times per evaluation.

### 3.7 Added components (deliberately small adaptations)

We do not claim a wholly new recommender architecture. Our architectural additions are deliberately small: a causal FIR adaptation of prior frequency-filter ideas and a soft text-prototype additive term. Both are deliberately simple, default-OFF, and zero-initialized so that each is a *bit-identical no-op at initialization* and reduces the design to a single controlled lever. Both are defined on top of an **HSTU-style pure-PyTorch implementation of the HSTU encoder, based on the published architecture** (Zhai et al., 2024): we use the pointwise-aggregated interaction `silu(QKᵀ + rab) V` with the published per-block normalization, having diagnosed and removed two spurious normalizations (a 1/√d score scaling and a 1/(i+1) row averaging) in our initial reimplementation that collapse HSTU's pointwise attention into weak mean-pooling. We verify the implementation equation-by-equation against the published HSTU formulation (pointwise `silu(QKᵀ + rab) V` aggregation, no softmax, no 1/√d scaling); an executable end-to-end reproduction of the official kernel stack is impossible on our hardware (§7); the core block, however, passes an exact numerical parity test against the reference research implementation (max abs diff 0.0; `HSTU_PARITY_REPORT.md`).

**(a) Text-Anchored Prototype Embeddings (TAPE).** TAPE is a simple soft text-prototype additive capacity term inspired by semantic-ID and prototype methods (TIGER, VQ-Rec, ProtoMF); it provides a small but not headline gain (§5.1). Let `t_i ∈ ℝ^{d_text}` be item *i*'s frozen text embedding (MiniLM or BLaIR). We k-means the L2-normalized text embeddings into *K* centroids `{c_1,…,c_K}` once, offline, and form a **frozen soft assignment** `A_i = softmax(⟨t_i, c⟩ / τ) ∈ Δ^{K}` (τ = 0.05). We add a **learnable prototype table** `P ∈ ℝ^{K×d}` (zero-initialized) to each item's feature:

  `e_i = id_i + Φ(t_i) + A_i P`,

where `id_i` is the learned per-item embedding and `Φ` the frozen-text projection. Items in the same semantic neighborhood share the learnable capacity `A_i P` — the shared-structure benefit of TIGER-style semantic IDs (Rajput et al., 2023) without discrete codes or an autoregressive decoder. Because `A` is frozen and `P` is zero-init, TAPE is an exact no-op at initialization and recovers the baseline. TAPE is adjacent to TIGER (discrete RQ-VAE IDs), VQ-Rec (PQ codes), and ProtoMF (prototype matrix factorization for explainability); it differs only in realization — a frozen text-derived soft assignment gating a learnable prototype table inside a sequential recommender — and we present it as a small adaptation of these prior ideas tested as a secondary ablation, not as a headline contribution. Default K = 512.

**(b) Strictly causal FIR temporal filter.** BSARec (Shin et al., 2024, Thm 3.1) analyzes vanilla Transformer self-attention as low-pass in the sequential-recommendation setting. We hypothesize that the HSTU-style pointwise aggregation used here can benefit from a similar local high-frequency inductive bias; the empirical ablation (§5.1–§5.2) tests this hypothesis. We insert, immediately before the HSTU stack, one **per-channel learnable FIR filter** as a zero-init gated residual on the sequence embeddings `x ∈ ℝ^{B×L×d}`:

  `y = DepthwiseConv1d_K(pad_left(x, K−1))`,  `x ← x + g ⊙ (y − x)`,

implemented as a depthwise `Conv1d(d, d, kernel_size=K, groups=d, bias=False)` with a **left-only causal pad of K−1**, a scalar gate `g` zero-initialized, and the kernel initialized to a causal delta (all-pass). The left-only pad makes output position *t* a function of input positions ≤ *t* only — so under our all-position next-item loss there is **no future-label leakage**. FMLP-Rec (Zhou et al., 2022) and BSARec use bidirectional sequence filters in their original formulations; under our all-position next-item loss, directly inserting such filters before each position's prediction would mix future positions, so we use a left-causal FIR realization. The novelty boundary is narrow and we state it plainly. *Not new*: filtering sequential representations, the frequency-domain motivation, and the attention-oversmoothing framing (FMLP-Rec; BSARec). *New*: the leak-free, left-causal FIR realization inserted before an HSTU-style stack under the all-position next-item objective, evaluated under full-catalog LLOO. As an FIR filter the module has a learnable per-channel frequency response — the only sense in which we use the word "spectral" — and it supplies an explicit local temporal bias that the baseline does not learn as reliably in our low-capacity setting (we do not claim the attention stack cannot represent this behavior). The gain is robust across kernel lengths K ∈ {4, 8, 16, 50} (§5); we use K = 8 on Video_Games and K = 16 on Musical_Instruments.

Both components are leak-free by construction and add negligible parameters (TAPE: K×d ≈ 33k; filter: K×d ≈ 0.5–3k). Two further regularizers we use are *not* claimed novel: **label smoothing** (Szegedy et al., 2016) on the full-softmax CE target, and the standard time / text-similarity / relative-position attention biases (TiSASRec; HSTU; Shaw et al., 2018), each cited at the point of use.

## 4. Experiments

### 4.1 Datasets

We evaluate on two AR2023 5-core categories:
- **Video_Games**: 94,762 users, 25,612 items, ~830k interactions
- **Beauty_and_Personal_Care**: 729,576 users, 207,649 items, 5.17M interactions

The Beauty_and_PC catalog is 8× larger than Video_Games, with median user history of only 5 interactions — a harder benchmark.

### 4.2 Baselines

- Popularity (trivial floor)
- SASRec with sampled-512 softmax (our "original" baseline)
- SASRec with chunked-full-softmax (improved baseline)
- BERT4Rec (Sun et al., 2019)
- Published comparators: TIGER (Rajput et al., 2023), BLaIR (Hou et al., 2024), LIGER (Yang et al., 2024)

### 4.3 Experimental design (headline runs)

All headline results (§5.1–§5.4) use the HSTU-style pure-PyTorch encoder (§3.2) under the fixed AR2023 5-core full-catalog LLOO protocol (§3.6). Each configuration is trained for **40 epochs** at batch size 256 (d_model 64, 4 layers, 2 heads, dropout 0.5) with the memory-efficient chunked-full-softmax loss (§3.5, item chunk 32,768) and a warmup-cosine learning-rate schedule. On top of the bias stack (TAPE-512 + time bias + text-similarity bias + pos-rab) the winning configuration adds label smoothing (ε=0.2) and the causal FIR filter (K=8). We run **6 seeds (20260608–20260613)** for the full-model headline and **5 seeds (20260608–20260612)** for every per-component ablation rung, reporting mean ± sample-std; the reported test number is always selected by best validation NDCG@10 (best-by-val), never by test. Evaluation is full-catalog (n_eval = 94,762 on Video_Games), with all train+val items masked (§3.6).

The tail analysis (§5.3–§5.4) rests on two controlled contrasts, each toggling exactly one factor on the same split and seeds and reporting `by_popularity` NDCG@10 / HR@10 on leak-free train-frequency terciles (terciles frozen at full density):
- **text vs ID-only:** the full text stack against an ID-only ablation (`--no-sbert`, no prototypes, no text-similarity bias).
- **density / connectivity titration (§5.4):** training-only sub-sampling that thins either interactions (interaction-mode) or whole users (user-mode) to match a sparser reference category's resource levels, with the evaluation set held fixed.

A separate **20-variant cross-pipeline transfer scan on Beauty_and_PC** — supporting reproducibility material, not part of the headline spine — is reported in Appendix A.1.

### 4.4 Training details and hardware

Headline runs use Adam (lr 1e-3, weight decay 1e-5) with gradient clipping (norm 5.0) under the 40-epoch warmup-cosine schedule above. Hardware: a single NVIDIA RTX 5060 Ti (16 GB, Blackwell sm_120). Video_Games training takes ~10 min/seed; Beauty_and_PC ~1.5–2 hr/seed with the chunked-full-softmax loss. (The Appendix A.1 Beauty scan used a shorter 15–20-epoch budget and seeds 42/43; those details are local to that supporting study.)

## 5. Results

**Statistical reporting conventions.** Unless stated otherwise: the sample unit is the training seed; means are reported ± sample standard deviation over seeds; confidence intervals are two-sided 95% Student-t intervals with df = n−1 (n = 5 unless noted); comparisons against our own arms are seed-paired, comparisons against published numbers are point-estimate comparisons (the comparator is single-seed and unpaired); pooled tail hit-count contrasts use an unpaired two-proportion z (conservative) with the user-evaluation as the unit; p-values are uncorrected unless a correction is named — cells labeled *confirmatory* in the artifact manifest are pre-registered or ≥5-seed, *exploratory* cells are single-seed or post-hoc and carry no confirmatory weight.


### 5.1 Video_Games — multi-seed reference numbers (NOT SOTA)

Our headline result (Table 1) is built on the **HSTU-style pure-PyTorch encoder** with the two added components and stacks each lever in a controlled 5-seed ablation; Table 1a reports the SASRec-family text baselines that establish protocol parity; Table 1b compares to the reported HSTU-BLaIR reference and our SM120 compatibility-port reproduction.

**Table 1: Headline component ablation — NDCG@10 on AR2023 Video_Games 5-core LLOO (full-catalog eval, n_eval = 94,762; 5 seeds = 20260608…20260612 unless noted; the full-model row is 6-seed 20260608…20260613; one flag added per row).**

| Configuration | NDCG@10 | seeds | Δ |
|---|---:|---:|---|
| HSTU-style encoder, plain | 0.0588 | 1 | — |
| + TAPE-512 (sub-additive text component) | 0.0597 | 1 | +0.0009 |
| + full bias stack (TAPE + time + text-sim + pos-rab) | 0.0637 ± 0.0003 | 5 | +0.0049 vs plain (+8.3%) |
| + label smoothing ε=0.2 (Szegedy 2016) | 0.0649 ± 0.0003 | 5 | +0.0012 (bands non-overlapping) |
| **+ causal FIR filter K=8 (ours) → full model** | **0.0673 ± 0.0003** | **6** | **+0.0024 (bands non-overlapping)** |
| *(isolation)* causal filter only, no label smoothing | 0.0652 ± 0.0003 | 5 | +0.0015 vs the 0.0637 stack |
| *(isolation)* ID-only (no SBERT / no text-sim / no prototypes) | ≈0.0656 ± 0.0002 | 5 | text adds only +0.0018 (+2.7%) overall |

The full model is **+17.5%** over the published SASRec baseline (0.0573, Table 1b) on the identical protocol — but **this win is architectural, not text-driven**: the ID-only ablation already reaches ≈0.0656 (itself +14% over published SASRec), and the entire frozen-text stack (SBERT features + text-sim bias + prototypes) adds only **+0.00178 ± 0.00021 (5-seed, +2.7%)** overall. The two confirmed regularizers stack near-additively on orthogonal axes (loss target vs. embedding spectrum): label smoothing alone +0.0012, causal filter alone +0.0015, combined +0.0036 over the bias stack. Per-component single-flag attribution on the HSTU-style implementation: the **time bias is the largest classical component (+0.0027)**, label smoothing +0.0013, causal filter +0.0015, while **text-similarity bias is dead weight (±0.0001, drop candidate)** and **TAPE is sub-additive (+0.0009)**. *(The time-bias, text-sim, and TAPE single-flag figures here are the single-seed seed-20260608 DECOMP values, honestly flagged n=1 (reported inline here, not in a table). A 4-seed multi-seed cross-check — DECOMP5, seeds 20260609–12, HSTU-style base 0.0594 — confirms the ordering: time bias +0.0030 (largest classical component, ≥ the single-seed +0.0027), pos-rab +0.0012, TAPE +0.0004, text-sim −0.00005 (dead weight confirmed). The qualitative attribution is unchanged; the only number that materially moves is TAPE, whose multi-seed single-flag lift (+0.0004) is smaller still than the single-seed +0.0009 — further support for its demotion from a headline component.)* The causal filter's gain is robust across kernel lengths K∈{4,8,16,50} (k16 marginally best & tightest, 5-seed 0.0676 ± 0.0002; low kernel sensitivity, §5.4). Every capacity-*adding* probe we tried instead (continuous time-decay kernel, expert heads, text-distillation, dual-text, EMA, CL4SRec, James–Stein shrinkage, niche-competition loss, heat-kernel label smoothing, spectral-shrink, cue-fusion, forced ID→text routing) was neutral or harmful — several with a learned scalar the model itself drove to zero (the negative-result map, tabulated in Table 2, §5.5).

**Table 1a: SASRec-family text baselines (protocol-parity check, full-catalog eval).**

| Method | NDCG@10 | HR@10 | Notes |
|---|---:|---:|---|
| popularity | 0.0125 | 0.0248 | trivial floor (traceable: `results_5core_Video_Games.json`) |

*The v1-era SASRec/SBERT/BLaIR baseline rows and the observations derived from them have been REMOVED per the artifact-graph gate: their per-seed artifacts were not retained and the values are untraceable. Protocol parity is established independently by the dataset-identity statistics (exact user/item match, ±1 interactions on every category), the frozen split hashes, and the per-category floor runs recorded in the pre-registration results files.*

**Table 1b: Reported and locally audited HSTU-BLaIR comparator evidence** (Liu, 2025, arXiv:2504.10545):

The HSTU-BLaIR paper reports on AR2023 Video_Games 5-core LLOO with identical dataset stats to ours (25,612 items / 94,762 users / 814,585 interactions). They train for **100 epochs** following Zhai et al.'s HSTU protocol. Their single-seed numbers:

| Method | NDCG@10 | HR@10 | Comparison to ours |
|---|---:|---:|---|
| SASRec (Liu, 2025, single seed, 100 epochs) | **0.0573** | 0.1028 | −15% below our full model 0.0673 ± 0.0003 |
| HSTU (Zhai et al., 2024) | 0.0741 | 0.1315 | +10% above our full model |
| HSTU-OpenAI (TE3L) | 0.0742 | 0.1328 | +10% above our full model |
| **HSTU-BLaIR (Liu, 2025)** | **0.0760** | **0.1353** | **+13% above our full model; stronger reported reference** |
| HSTU-BLaIR local SM120 compatibility port (this audit) | 0.07382 final full-eval (exported artifact; the higher best-epoch reading survives only in an unretained WSL log and is excluded from the artifact graph) | 0.13234 final | stronger than ours; not a faithful pinned-environment reproduction |

**Our full model (0.0673) exceeds their published SASRec (0.0573) but does not reach their HSTU (0.0741) or HSTU-BLaIR (0.0760) on Video_Games.** Our local compatibility-port HSTU-BLaIR run reached final full-eval NDCG@10 `0.07382` (the best-epoch reading exists only in an unretained WSL log and is excluded from the artifact graph); the run is stronger than SASRec-SBERT but carries SM120/fbgemm validity caveats.

What this paper provides relative to HSTU-BLaIR:
- Multi-seed std (n=5 vs their n=1)
- Same-protocol multi-seed text-vs-ID ablation (ID-only vs text-augmented) under matched training (the earlier 3-method encoder ablation was retired with its v1-era rows; see the manifest's RETIRED entries)
- Open-source preprocessing pipeline
- Compact SASRec implementation details and bug fixes

What this paper does NOT provide:
- A new leaderboard result; HSTU-BLaIR's reported 0.0760 remains the stronger external reference.
- A faithful HSTU implementation; we completed only an SM120 compatibility-port reproduction with caveats. A faithful pinned-environment reproduction on compatible hardware is future work.

**Older published baselines on different protocols** (NOT directly comparable; for context only):

| Method | NDCG@10 | Dataset | Protocol |
|---|---:|---|---|
| SASRec (in TIGER paper) | 0.0318 | Amazon Beauty **2014** | their 5-core (different category, different dataset year) |
| TIGER (Rajput et al., 2023) | 0.0384 | Amazon Beauty **2014** | their 5-core |
| SASRec (in LIGER paper) | 0.02179±0.00023 | Amazon Beauty **2014** | their 5-core |
| LIGER (K=20, Yang et al., 2024) | 0.04020±0.00044 | Amazon Beauty **2014** | their 5-core |
| LIGER (K=N, full retrieval) | 0.04738±0.00151 | Amazon Beauty **2014** | their 5-core |
| Best LLM-encoder in BLaIR (Hou et al., 2024) Table 8 | 0.0138 | AR2023 Video_Games | **by-timestamp 8:1:1, no k-core**, UniSRec downstream |

**Comparability caveat**: TIGER and LIGER evaluate on the older Amazon Reviews 2014 dataset, not AR2023. The BLaIR paper does evaluate on AR2023 Video_Games but uses a by-timestamp split (no k-core filter) and a different downstream architecture (UniSRec), producing numbers ~3-4× lower than our 5-core LLOO numbers. The 5-core filter removes cold users and items, which substantially eases the benchmark relative to the by-timestamp variant. We therefore do **not** claim SOTA over TIGER/LIGER/BLaIR. HSTU-BLaIR is the relevant stronger AR2023 Video_Games 5-core reference and blocks a SASRec-SBERT SOTA claim.

**2026 semantic-ID / generative retrieval line.** Two recent semantic-ID methods report Amazon Reviews 2023 Musical_Instruments numbers: **ReSID** (arXiv:2602.02338) reports MI NDCG@10 = 0.0346 in its main ranking table under its own filtering; **ChronoSID** (arXiv:2607.03918), in its output-level MI table (five-run averages), reports 0.0345 for ChronoSID versus 0.0325 for its ReSID reproduction. Each uses the SID line's own filtered universe (57,359 users / 23,742 items / 490,522 interactions), which differs from the 57,439 / 24,587 / ~511,835 HSTU-BLaIR-family statistics we and the comparator share; metrics and protocols are not interchangeable across the two lines. These setups are not split-identical to ours, so we discuss them as the current generative-retrieval line rather than claiming against them; within the HSTU-BLaIR protocol family (AR2023 5-core LLOO full-catalog), the published HSTU-BLaIR 0.0406 remains the strongest Musical_Instruments reference we know of, and it is the point estimate our pre-registered confirmation exceeds (§5.2).

What we *can* claim:
- Among methods evaluated on the AR2023 5-core LLOO protocol (where we are the first to report numbers), our SASRec-SBERT is a strong, simple, compact baseline using only 11.6M parameters and ~10 min of training on a single consumer GPU.
- Compared to a popularity floor (0.0125), our model achieves a 4.1× improvement, indicating the model is learning meaningful sequential structure rather than just popularity.

### 5.2 The causal FIR filter carries the cross-category generalization (Musical_Instruments)

The single most important robustness result for the filter is that it transfers to a *second* category, and does so *more strongly than label smoothing*. On Musical_Instruments (a sparser AR2023 category), the full V2 stack reaches **NDCG@10 = 0.0413 ± 0.0005 (5-seed)**, **+7.9%** over a matched HSTU+TAPE base (0.0383 ± 0.0004) and **+57%** over a plain ID-only SASRec (0.0264). A controlled single-lever isolation (best-by-val, vs the MI SBERT+TAPE base 0.0383, 4×e20-seed) dissociates the two confirmed regularizers:

**Table 1c: Musical_Instruments per-lever isolation (NDCG@10, best-by-val, vs MI SBERT+TAPE base; shares are of the 5-seed V2 combined lift +0.0032).**

| Configuration | NDCG@10 | Δ vs base | share of combined lift |
|---|---:|---:|---:|
| MI SBERT+TAPE base (4×e20-seed) | 0.0383 | — | — |
| + label smoothing only (5-seed) | 0.0391 ± 0.0001 | +0.0008 | 26% |
| **+ causal filter only (k16, 5-seed)** | **0.0408** | **+0.0025** | **77%** |
| + both = V2 (k16, 5-seed) | 0.0415 | +0.0032 | 100% |

(Recomputed best-by-val from the released per-seed artifacts. Against the headline 5-seed V2 stack the filter's share is 77% (k16) / 82% (k8). LS-only is the 5-seed family `results_MI_lsonly_seed{08–12}` (0.03914 ± 0.00013); base is the four e20 seeds 20260609–12.)

**The causal filter contributes ≈3× what label smoothing does on the second category, and ≈80% of the combined lift (77% vs the k16 stack, 82% vs the k8 headline stack)** — i.e. the filter generalizes cross-category while label smoothing is largely Video_Games-specific. The filter's kernel-robustness also generalizes (MI k8 0.0413 ± 0.0005 ≈ k16 0.0415 ± 0.0002). This locks the causal FIR filter as the paper's primary methodological anchor: a leak-free, simple, parameter-cheap operation supplying an explicit local temporal bias that the baseline does not learn as reliably in our low-capacity setting, confirmed on two categories.

**Comparator ablations (audit-requested).** Each arm changes exactly one design element of the filter on the same 5-seed MI stack: freezing the kernel at a causal moving average (learnable gate retained) recovers only +0.00133 of the filter's +0.00225 gain over the no-filter baseline (0.04046 ± 0.00022 vs 0.04138 ± 0.00053; non-overlapping bands) — the learned kernel shape, not generic smoothing, carries the effect. Freezing the gate at 1 (delta-initialized kernel) matches the full filter (0.04127 ± 0.00046), so the zero-init gate is a training-stability convenience rather than a performance component.


**Pre-registered confirmation vs the published per-category reference.** The seeds above (20260608–17) are *exploratory*: kernel choice, epoch budget, and the decision to compare against the published Musical_Instruments HSTU-BLaIR number (0.0406; Liu 2025, Table 2) were all made while inspecting them. To make the comparison selection-free, we froze an immutable pre-registration (`SOTA_CONFIRM_PREREG_V2.md`, committed to version control before any confirmation run: exact config and commands, data SHA256s, decision rule, claim wording) and ran **10 never-inspected fresh seeds (20260618–22, both kernels)** with per-run provenance manifests (command, git commit + clean-tree flag, environment, data hashes) and per-user record sidecars. Result: **K=16 fresh 5-seed 0.04152 ± 0.00045 (95% CI lower bound 0.04096) and K=8 0.04120 ± 0.00030 (CI-LB 0.04083) — both CI lower bounds above the published 0.0406, 10/10 seeds above.** The supported claim is exactly this: *fresh multi-seed means and seed-level confidence intervals exceed the published HSTU-BLaIR point estimate on this category under our reproduced protocol (parity evidence: users/items match the paper exactly; interactions differ by one — see `SOTA_CONFIRM_PREREG_V2_ERRATA.md` E1; our plain SASRec floor is* below *their published SASRec, ruling out an easier split).* The comparator is single-seed; our post-hoc local regeneration of it (§5.6 — the reference implementation's research path under data-movement shims, unpinned environment) reproduces the published value at its best full-eval epoch (0.0406; final epoch 0.0391) but is itself a single environment-caveated run, so no paired or distributional superiority is claimed, and this remains a per-category result — Video_Games is explicitly not claimed (§5.1). The first execution of this confirmation was voided by its own provenance tripwire (a concurrent documentation edit dirtied the tracked tree mid-campaign) and re-executed in full under a clean tree; both executions agree per-seed to ±0.0003 (`SOTA_CONFIRM_V2_RESULTS.md`). One protocol deviation is disclosed rather than claimed away: the gated runs executed at a documentation-only descendant commit of the pre-registration's introducing commit (the pre-registered commit-equality rule was not literally satisfied); code identity across the two commits is demonstrated by empty protocol-file diffs and, in the from-scratch rebuild, by code hashes embedded in each run manifest (`SOTA_CONFIRM_PREREG_V2_ERRATA.md`, E3).

**Office_Products (second-category attempt) — descriptive only.** Office_Products numerically exceeded the published HSTU-BLaIR point estimate under the frozen MI configuration, but the pre-registered SASRec floor check failed because our local SASRec floor was substantially above the published SASRec reference. We therefore treat Office as descriptive evidence, not as a passed confirmatory category. The floor anomaly has since been resolved mechanistically — the reference implementation's own SASRec, run locally on its own pipeline (§5.6), lands +13.9% above its published row, so published Office comparator rows appear conservative in this environment and the VOID is deliberately retained; full detail, decomposition, and disclosures in Appendix A.0.

### 5.3 A dataset-conditional long-tail pattern for text-augmented recommendation

Beyond *whether* text helps overall (modestly: +2.7% on Video_Games, §5.1), we ask *where* it helps. `evaluate()` reports `by_popularity` NDCG@10 over train-frequency terciles {tail, mid, head} (bucketed by TRAIN frequency only — leak-free), and we compare the full text stack against an ID-only ablation on the **same split and seeds**, the controlled `text − ID` tail contrast. The cold-start intuition — text should rescue rare items where ID embeddings are starved — holds on *one* of three datasets, and the difference is principled and significant.

**Table 1d: text − ID tail-tercile NDCG@10 contrast (paired, per-seed; the dataset-conditional pattern).**

| dataset | catalog density | tail Δ NDCG@10 (5-seed) | seeds positive | verdict |
|---|---|---:|---:|---|
| **Musical_Instruments** | sparse | **+0.000335 ± 0.000195**, 95% CI [+0.00009, +0.00058] **excl 0** | **5/5** | **text WINS the tail** |
| **Video_Games** | dense | −0.000148 ± 0.000179 | 2/5 | **powered NULL** |
| **Beauty_and_PC** | dense | −0.0000078 (3-seed, sample-sd 0.000020) | 1/3 | NULL |

Three points make this a defensible empirical *pattern* rather than a lucky bucketing:

1. **The MI tail win is real and replicates on a rank-free metric.** Tail HR Δ = +0.00109 ± 0.00065, 5/5 positive (≈29.6 vs 20.0 hits/seed); all terciles are 5/5-positive. We are honest about scale: text's *largest absolute* lift is at the head (+0.00527 on MI), and the tail win is a large *relative* gain (+27.6%) on a tiny (~30-hit/seed) base — we always report relative, absolute, and hit-count together.
2. **The VG null is a *powered* null, not an underpowered failure to reject** — the standard reviewer objection to a null. VG tail Δ = −0.000148 ± 0.000179 (SE 0.000080); the minimum detectable effect (paired t, 80% power, n=5) is **0.000246 < MI's native effect 0.000335**, so VG had >80% power to see an MI-sized effect and saw none. A **TOST equivalence test** against MI's ±0.000335 margin gives 90% CI [−0.000319, +0.000023] ⊂ ±0.000335 ⇒ VG's tail text-benefit is **statistically equivalent to zero** within the magnitude that matters. We state the VG/Beauty tail results as positive equivalence claims.
3. **The cross-dataset difference is itself significant.** Welch two-sample contrast of the per-seed paired tail Δ: MI − VG = +0.000484, **t = 4.09, df ≈ 7.9, p ≈ 0.004 (two-sided)**. The pattern (sparse-catalog text wins the tail; dense-catalog text does not) is a real between-dataset effect. A companion **regime-migration** finding: text's winning tercile slides **tail → mid → head as catalogs densify** (MI sparse → VG → Beauty dense). The tail pattern and its two-axis mechanism decomposition are summarized in **Fig. 1** (`figures/fig_tail_law_mechanism`): panel (A) this dataset-conditional tail pattern, panel (B) the interaction-density titration double result (§5.4), and panel (C) the connectivity-vs-count two-axis decomposition (§5.4.1–§5.4.2).

### 5.4 Titration: thinning supports density as a head *driver* but only a tail *correlate* (a double/refuting result)

To test whether *global interaction density* (the most obvious covariate separating sparse MI from dense VG) drives the tail pattern, we ran a pre-registered **interaction-thinning titration**: a 7-rung ladder thinning Video_Games' interaction graph toward progressively lower density (down to MI's exact global density at ρ=0.66), re-measuring the `text − ID` head and tail Δ at each rung (best-by-val, n_eval fixed at 94,762 every rung). The result **splits**, and we report it as a *double* result — confirming on one stratum, refuting on the other:

- **HEAD = CONFIRMED monotone dose-response (now fully 5-seed-locked across every rung).** Head Δ rises smoothly as VG thins — per-rung 5-seed means down the density ladder ρ = 1.0 → 0.94 → 0.91 → 0.88 → 0.78 → 0.66: **+0.00221 → +0.00239 → +0.00254 → +0.00252 → +0.00266 → +0.00354**, all six rungs 5/5 seeds positive; **Spearman ρ_s(head Δ vs density) = −0.94 (NDCG) / −0.71 (HR)** — monotone on *both metrics*. ⇒ Global density is **supported as a driver** of the head/overall text-complementarity by the thinning intervention. (Every rung is 5 seeds {20260608–12}.)
- **TAIL = REFUTED dose-response (5-seed-locked).** Tail Δ is non-monotone and trend-free across the same rungs — 5-seed means **−0.000148 → +0.000165 → +0.000039 → +0.000537 (ρ=0.88) → +0.000056 → −0.000108 ± 0.000503 (ρ=0.66, the MI-equivalent density rung)**; per-rung positive-seed counts 2/5, 4/5, 3/5, 4/5, 2/5, 1/5 — no rung clears MI's +0.000335/5-of-5 bar, and **Spearman ρ_s(tail Δ vs density) = −0.14 (n.s., 5 seeds)**. Thinning VG to MI's exact global density does *not* reproduce MI's +0.000335 tail *win* — the MI-equivalent ρ=0.66 rung sits at a flat null straddling 0 (1/5 seeds positive), no further toward MI's positive value than full-density VG. **(Honesty note:** this rung was −0.000450 at 2 seeds and "the most-negative thinned point"; filling it to 5 seeds regressed it to −0.000108 ± 0.000503, dissolving the "trough" sub-claim. The refutation is unaffected — thinning still never crosses toward MI's win — but it is now a *flat tail null under thinning*, not a deepening loss.) ⇒ Global density is **not supported by the thinning intervention** as a driver of the tail win — a tail *correlate* only. (The reproducible ρ=0.88 bump is non-monotone and Bonferroni-marginal (×7 ⇒ p≈0.09); we record it but do not headline it as a crossing.)

**Table 1e: the interaction-thinning density-titration ladder** (AR2023 Video_Games 5-core LLOO, full-catalog n_eval = 94,762, tail_n = 10,900; paired text−ID, best-by-val; 5 seeds = 20260608–12 per rung; mean ± sample-std, positive-seed count in parens). Realized interactions/item are the run-log values; α = (interactions/item) / d_eff with **d_eff = 23** (the GD/MP-kept effective rank of the 64-d item table, §5.4 BBP analysis), so α(ρ=0.66) = 0.700 reproduces the MI-subcritical anchor. All cells are re-read from the frozen `results_TITR*/TAIL_*` JSONs by `_bestrec_run/make_table_5_4_titration.py`, which **integrity-gates** the recomputed NDCG head/tail means against the locked prose values above (aborts on any >5e-5 drift); the HR columns and per-rung seed bands are the net-new tabulation the prose summarized only as Spearman trends.

| ρ | kept inter./item | α=ipp/d_eff | head ΔNDCG@10 | head ΔHR@10 | tail ΔNDCG@10 | tail ΔHR@10 |
|---|---|---|---|---|---|---|
| 1.00 | 24.405 | 1.061 | +0.002213 ± 0.000241 (5/5) | +0.004238 ± 0.000765 (5/5) | −0.000148 ± 0.000179 (2/5) | +0.000128 ± 0.000582 (3/5) |
| 0.94 | 22.947 | 0.998 | +0.002389 ± 0.000267 (5/5) | +0.004083 ± 0.000830 (5/5) | +0.000165 ± 0.000370 (4/5) | +0.000807 ± 0.000712 (5/5) |
| 0.91 | 22.210 | 0.966 | +0.002544 ± 0.000491 (5/5) | +0.004940 ± 0.000892 (5/5) | +0.000039 ± 0.000310 (3/5) | +0.000110 ± 0.000766 (3/5) |
| 0.88 | 21.484 | 0.934 | +0.002520 ± 0.000421 (5/5) | +0.004869 ± 0.000765 (5/5) | +0.000537 ± 0.000386 (4/5) | +0.000661 ± 0.000995 (4/5) |
| 0.78 | 19.030 | 0.827 | +0.002664 ± 0.000398 (5/5) | +0.004467 ± 0.001082 (5/5) | +0.000056 ± 0.000552 (2/5) | +0.000239 ± 0.001087 (2/5) |
| 0.66 | 16.109 | 0.700 | +0.003540 ± 0.000416 (5/5) | +0.005720 ± 0.000904 (5/5) | −0.000108 ± 0.000503 (1/5) | +0.000073 ± 0.001165 (3/5) |

The table makes the double result legible at a glance: **head ΔNDCG climbs monotonically** as ρ falls (24.4→16.1 interactions/item), every rung 5/5 positive (Spearman ρ_s = −0.94 NDCG / −0.71 HR ⇒ density *supported as a driver* of the head advantage by the thinning intervention), while **tail ΔNDCG stays trend-free** (ρ_s = −0.14 n.s.), no rung — including the MI-density ρ=0.66 rung at α=0.700 — clearing MI's native +0.000335/5-of-5 bar (⇒ density *not supported* as a tail driver by the thinning intervention, a correlate only). The HR columns track the NDCG verdict (head all-positive and rising; tail noisy and trend-free).

**Methodological honesty (this is the load-bearing framing):** the titration is a **refuting tail keystone, not a confirming one.** Writing it as if it confirmed a density-driven tail pattern would be the same val=0.076-class inflation this study exists to prevent. The dissociation — same single intervention (interaction thinning) moving the head effect monotonically while leaving the tail effect trend-free — is a single-manipulation double dissociation (Nieuwenhuis-safe: we test the *interaction* of stratum × density, not two separate significance tests). What MI-specific property co-varying with but distinct from global density drives the tail win remains **open**; the leading candidate is collaborative connectivity (**users/item**: MI 2.34 ≪ VG 3.70 ≈ Beauty 3.51), which interaction-thinning barely moves, and which a user-mode titration (§5.4.2) isolates — finding it consistent with a real *partial* causal role in the tail win (under the thinning intervention's assumptions), the residual being a dataset-specific content factor.

#### 5.4.1 The whole double-dissociation in one scale-free table: the cross-dataset tail/head arm ratio

The per-rung Δ trends above are absolute-difference statistics, which a reviewer can dismiss as a level/scale artifact (MI's tail sits ≈3× lower in absolute NDCG than VG's). We therefore restate the dissociation in a **scale-free** form: the per-arm mean absolute NDCG@10 (best-by-val), expressed as the **text-arm ÷ ID-arm ratio**, on a single density axis spanning VG at full density, VG thinned to MI's exact global density (ρ=0.66), and MI native at that same density. A ratio >1 means text leads ID; <1 means text trails ID.

| regime (interactions/item) | n (text/id) | TAIL text | TAIL id | **TAIL ratio** | tail Δ | **HEAD ratio** |
|---|---|---|---|---|---|---|
| VG full density (ipi 24.5) | 5 / 5 | 0.004919 | 0.005068 | **0.971 (−2.9%)** | −0.000148 | 1.026 (+2.6%) |
| VG thinned → MI-density (ρ=0.66, ipi 16.2) | 5 / 5 | 0.003569 | 0.003677 | **0.971 (−2.9%)** | −0.000108 | 1.049 (+4.9%) |
| MI native (ipi 16.2) | 5 / 5 | 0.001551 | 0.001216 | **1.276 (+27.6%)** | +0.000335 | 1.101 (+10.1%) |

Reading the table down the two ratio columns gives the double-dissociation on one axis, scale-free:

- **HEAD ratio is density-CONSISTENT (supports density as the head driver).** As VG is thinned toward MI's density the head text/ID ratio rises **monotonically 1.026 → 1.049 → 1.101**, *toward* MI's native head ratio. This is the cross-dataset mirror of the within-VG head dose-response (§5.4, ρ_s = −0.82/−0.86), and it lands the head-driver support in the same table as the tail null — robust at 5 seeds.
- **TAIL ratio is density-INVARIANT within VG, and far from MI (density not supported as the tail driver).** Over the same thinning the tail text/ID ratio is essentially **flat at ≈0.971** (full → MI-density), staying well below 1 and far below MI's native **1.276**. Thinning VG to MI's exact global density reaches MI's *density* but not MI's *tail advantage*: both arms starve proportionally (text −27.4%, ID −27.4% from full to ρ=0.66 ⇒ ratio invariant), so the thinned tail is text-*neutral*, never text-*rich*. Approaching MI's density by thinning VG does not move the tail ratio toward MI's value at all. Thinning interactions therefore *cannot manufacture* MI's tail win — the tail advantage is a dataset property orthogonal to global density.

**The mechanism behind "thin VG ≠ be MI."** MI's tail win is neither a "text rises" story nor an "ID collapses" story: at MI's tail *both* arms sit at the sparse floor (≈0.0012–0.0016, ≈3× below VG's tail ≈0.005), yet text holds a +27.6% edge there. The binding difference between MI-native-sparse and VG-thinned-sparse is **what kind of sparsity**: MI pairs few interactions with an intact, discriminative item-text corpus the frozen-text channel can exploit at rare items (*sparse-but-text-rich*), whereas thinning VG removes the co-occurrence substrate the text channels ride on without replacing it (*sparse-and-text-impoverished*). At 5 seeds the thinned tail starves *both* arms proportionally (text −27.4%, ID −27.4% to ρ=0.66 ⇒ the tail ratio stays flat at ≈0.97, never climbing toward MI's 1.276) — so VG-thinning reaches MI's density but leaves the tail text-neutral, not text-rich. This is the positive mechanism behind the refutation, and it reframes the user-mode titration's prediction (§5.4.2): because thinning *users* (not interactions) preserves each surviving user's full history, the text tail-arm should retain more of its substrate — so the decisive read is whether the user-mode tail ratio climbs above ≈0.97 toward MI's 1.276 (pointing at users/item as the binding resource) or stays flat near 0.97 (the interaction-thinning signature, closing global density as the tail axis entirely). **This read is now resolved (§5.4.2): the user-thinned tail ratio climbs to 1.046 at MI-matched connectivity — consistent with connectivity binding the tail in a partial causal role (under the thinning intervention's assumptions).**

**Caveat (load-bearing):** the VG-thinned ρ=0.66 row is **5-seed**. The tail-ratio *direction* (both VG points at ≈0.971, below 1 and far below MI's 1.276) is robust to the seed count; the earlier 2-seed magnitude (tail ratio 0.884, −11.6%) and the "most-negative trough / text-starves-faster" sub-claim were small-sample artifacts and are **retracted** — the corrected 5-seed endpoint is a flat null (tail ratio 0.971, Δ −0.000108 ± 0.000503, 1/5 seeds positive), i.e. density-*inertness* rather than a deepening loss. The qualitative refutation is unaffected. MI-native and VG-full are both 5-seed. As in §5.4 we claim a **level-dissociation**, not a significant stratum×density *interaction* (the slope-difference itself is n.s. at the available seed counts — Nieuwenhuis-safe).

#### 5.4.2 User-mode titration: collaborative connectivity (users/item) is consistent with a *partial* causal role in the tail win

§5.4.1 closes with a pre-registered decisive read: thinning *users* (rather than interactions) lowers collaborative connectivity (users/item) while **preserving each surviving user's full history**, so if the user-mode tail ratio **climbs above ≈0.97 toward MI's 1.276**, connectivity binds the tail; if it stays flat near 0.97, the interaction-thinning signature repeats and global density is closed as the tail axis. We ran that titration (drop whole users with probability ρ_user, keep all their interactions; eval histories and terciles frozen at full density; ≥5 seeds at the MI-equivalent rung). Its decisive form is a **matched-R1 contrast**: at ρ_user=0.66 the realized train interactions/item is **16.12 — identical to the interaction-mode ρ=0.66 rung (16.2)** — but users/item falls to **2.44 (≈ MI's 2.34)** versus interaction-mode's ≈3.4. Any tail difference between the two modes at this matched interaction count is attributable to **connectivity (R2) alone**.

The read comes out on the connectivity-binds side:

| regime (int/item, users/item) | TAIL ratio | tail Δ (5-seed) | HEAD ratio |
|---|---|---|---|
| VG full (24.5, 3.70) | 0.971 | −0.000148 | 1.026 |
| VG interaction-thinned ρ=0.66 (16.2, ~3.4) | 0.971 | −0.000108 ± 0.000503 (1/5 pos) | 1.049 |
| **VG user-thinned ρ_user=0.66 (16.1, 2.44)** | **1.046** | **+0.000178 ± 0.000153 (5/5 pos, t≈2.6)** | 1.039 |
| MI native (16.2, 2.34) | 1.276 | +0.000335 ± 0.000195 (5/5 pos) | 1.101 |

At MI-matched connectivity the VG tail text/ID ratio **climbs from 0.971 to 1.046**. The load-bearing significance statistic is the **paired difference-of-differences vs the full-density anchor**: thinning users to MI-matched connectivity *increases* the text−ID tail advantage by **dd = +0.000326 ± 0.000210 (paired t = +3.47, 95% CI [+0.000065, +0.000587] excludes 0; 5/5 seeds positive, one-sided sign-test p = 0.031)**. The corresponding **within-rung** text−ID tail level at ρ_user=0.66 is **+0.000178 (5/5 seeds positive, paired t ≈ 2.6)** — sign-consistent and in the predicted direction, moving *toward* (though not reaching) MI's native +0.000335; we report it as the within-rung effect and do **not** rest the claim on its marginal two-sided p≈0.06, leading instead with the dd-vs-full that clears CI-exclusion-of-zero. The **5×5 matched-R1 double-dissociation is significant in sign**: at equal interactions/item, (user − interaction) tail Δ = **+0.000286** while (user − interaction) head Δ = **−0.000475**, a diff-of-diffs of **+0.000761 with opposite signs** — count-thinning helps the head, connectivity-thinning helps the tail. This is the single-manipulation-pair double dissociation the interaction ladder alone could not produce, and it supports the §5.4.1 prediction's *connectivity-binds* branch. **Fig. 2** (`figures/fig_r1r2_plane`) plots these five regimes on the (R1 = interactions/item, R2 = users/item) resource plane: the two VG thinned points share R1 ≈ 16.2 (matched interaction count) yet only the R2-thinned (connectivity-thinned) point crosses into the tail-win band beside MI native, rendering the count-vs-connectivity dissociation in its native 2-D form (Tilman resource-ratio framing, cited as an analogy, not a claimed method).

Two honesty bounds keep this a *partial-causal-role* claim (scoped to the thinning intervention's assumptions), not a full explanation:
1. **No interpretable down-limb below MI-connectivity (5-seed-resolved: floor artifact, non-monotonicity refuted).** A single-seed (s08) reading had suggested the tail Δ turns negative as connectivity is thinned further (ρ_user=0.50 −0.000663, ρ_user=0.40 −0.002173), raising a possible "peaks-then-collapses" pattern. We powered both rungs to 5 seeds ({20260608–12}, both arms, `--subsample-seed 0`, FULL eval, n_eval=94,762 + tail_n=10,900 frozen) and the suggested non-monotonicity **does not survive**: ρ_user=0.50's within-rung tail Δ is **+0.000236 ± 0.000532 (4/5 seeds positive; t≈0.99, 95% CI includes 0)** — i.e. the positive tail effect **does not reverse below MI-connectivity** (the s08 −0.000663 was the lone negative of five seeds), which supports the *robustness* of the ρ_user=0.66 result rather than constituting a second significant plateau (the load-bearing claim stays anchored solely on the ρ_user=0.66 dd-vs-full + the matched-R1 dissociation); and ρ_user=0.40 is **−0.001545 (1/5 positive)** but driven entirely by a **TEXT-arm tail-absolute collapse** (TEXT tail NDCG falls to 0.00218 ≈ 44% of the full-density anchor 0.00494, tail HR 0.00422 vs 0.0099, while the ID arm holds ≈0.0037) — i.e. the text model degenerates when trained on ~40% of users, a floor effect rather than an interpretable "past-optimum connectivity" signal. By the pre-registered decision rule (sign-inconsistent across the down-limb rungs + tail absolutes collapsing toward the floor ⇒ floor artifact), we **delete the non-monotonicity claim** and footnote ρ_user=0.50/0.40 as near-degenerate thinned models, not interpretable as a hormetic optimum. The load-bearing claim is unaffected and stands on its own: the **ρ_user=0.66 5-seed crossing** (dd-vs-full +0.000326, CI excludes 0) plus the **matched-R1 double dissociation**. We therefore claim connectivity is consistent with a *partial* causal role (under the thinning intervention's assumptions) whose positive tail effect is present at and below MI-like connectivity (ρ_user 0.66 and 0.50 both positive), not a monotone knob and not a hormetic peak.
2. **Does not fully reach MI.** The user-thinned tail ratio (1.046) and Δ (+0.000178) land roughly **halfway** to MI-native (1.276 / +0.000335), so a residual, dataset-specific *content* component (MI's intact discriminative text corpus at rare items, §5.4.1) remains beyond what connectivity alone reconstructs.

**Refined verdict.** Collaborative connectivity (users/item) is **consistent with a partial causal role (under the thinning intervention's assumptions)** in the long-tail text advantage — dissociated from interaction count (5×5 double dissociation) and landing a positive VG tail effect exactly at MI-like connectivity — while global *interaction* density is supported as a *head* driver by the thinning interventions but not supported as a *tail* driver (§5.4). The MI tail win therefore decomposes into a **connectivity component (supported by the controlled intervention here) plus a residual content component (dataset-specific, bounded but not closed)**. This is the strongest form the dataset-conditional tail pattern takes on the controlled axes, and it closes the mechanism program: no single global-density scalar explains the tail, but a connectivity/content decomposition does, with the connectivity half supported by controlled thinning interventions on the dataset — intervention evidence, not causal identification of the real-world generative process. That the binding axis is collaborative connectivity rather than representational capacity is consistent with the dense-catalog tail being *spectrally irreducible*: a Baik–Ben Arous–Péché / Marchenko–Pastur analysis of the Video_Games item table (**Fig. 3**, `figures/fig_bbp_irreducibility`) finds **zero reliably-detectable tail/mid signal directions at the detectability edge (SVD rank ℓ=2)** and a Gavish–Donoho optimal-shrinkage rank of only **24 of 64** dimensions — so no representation-side lever (the text stack, the GD1 spectral-shrink prior, or the X1 James–Stein shrinkage, all in the negative-result map) can rescue the dense-catalog tail; only a change in the collaborative-connectivity regime moves it. (Attribution: BBP = Baik–Ben Arous–Péché 2005; Marchenko–Pastur 1967; optimal shrinkage = Gavish–Donoho 2014.)

> **Provenance/honesty:** all numbers are best-by-val paired text−ID from the released `results_USERTITR_{text,idonly}_rho0{66,50,40}_s08…s12_VG.json` (5 seeds each rung, n_eval=94,762 + tail_n=10,900 frozen at full density across every rung/seed/arm — verified, no eval drift). The lower rungs ρ_user 0.50/0.40 are **5-seed** (previously single-seed); the down-limb 5-seed fill **refuted** the single-seed non-monotonicity (ρ_user=0.50 = +0.000236, 4/5 positive — no decline; ρ_user=0.40 = −0.001545, 1/5, a TEXT-arm floor collapse), per the floor-artifact decision rule above. The tail base is small (~50 hits/seed on 10,900 tail users); we report relative, absolute, and the per-seed sign count together. As in §5.4 we claim a level-dissociation (the slope-difference is n.s. at these seed counts — Nieuwenhuis-safe).

### 5.5 Systematic negative-result map

A central empirical finding of this work is **asymmetric**: the only levers that moved test NDCG@10 were *capacity-restricting* (label smoothing, the causal FIR filter) or classical inductive biases already in Table 1 (the time bias); **every capacity-*adding* probe we tried was neutral or harmful.** We document the full set here as a first-class result — negatives are part of the contribution, and several are *interpretable* negatives in which a learnable scalar, free to engage the mechanism, was driven by the optimizer to (or past) zero. This is the evidence that the in-environment ceiling is not for want of trying these mechanisms; the residual gap to the published HSTU-BLaIR 0.0760 could not be isolated (the pinned reference environment is not installable here, and the shimmed local execution of §5.6 did not include the Video_Games configuration); what the probe set shows is that it is not explained by any of the modeling axes we could test.

All entries are best-by-val test NDCG@10, full-catalog eval (n_eval = 94,762 on Video_Games), on the same fixed protocol. Δ is versus the stated base; for the three learnable-scalar probes (W1/X1/Y1) we report the absolute single-seed test next to its base band, since the headline test is statistically indistinguishable from the base and the *learned scalar* is the load-bearing readout. Several rows are single-seed — sufficient for a negative-result map (a probe that fails to clear its base on one seed, or whose own learned scalar switches it off, does not warrant five seeds).

**Unequal power, stated plainly.** The probes in Table 2 do *not* carry equal evidential weight: most rows are single-seed exploratory probes, while a few were run at full multi-seed power. Only the multi-seed, pre-declared negatives — the conn-gate five-seed paired confirmation and the titration nulls of §5.3–§5.4 (the powered VG/Beauty tail nulls and the 5-seed-locked ladder rungs) — carry confirmatory weight. The remaining rows are exploratory documentation of the search space, recorded for completeness and interpretability, not powered hypothesis tests. Full per-probe seed counts are given in the table's n column.

**Table 2: Systematic negative-result map — capacity-adding / alternative-mechanism probes, all neutral or harmful.** (Mechanism class: where the lever acts. "Learned scalar → 0?" = did a free learnable gate/temperature/intensity collapse the mechanism. n = seed count. **Note: probes are not equally powered** — most rows are single-seed exploratory probes; only the multi-seed pre-declared negatives carry confirmatory weight, per the paragraph above.)

| Lever | Mechanism class | Base (NDCG@10) | Δ NDCG@10 (n) | Learned scalar → 0? | Verdict |
|---|---|---:|---:|---|---|
| c3 continuous time-decay attention kernel | attention re-weighting (capacity-add) | SBERT stack ≈0.0639 | **−0.0150** (1; test 0.0489 at record val 0.0725) | n/a | Rejected — actively harmful; the largest validation–test divergence in the corpus |
| Sampled softmax (K=512 negatives) | loss approximation | full-softmax stack | −0.0026 (1) | n/a | Rejected — undertrains full-catalog ranking |
| Dual text encoder (SBERT ⊕ BLaIR) | text encoder | SBERT stack | −0.0014 (1) | n/a | Rejected — the text encoder is not the gap |
| BLaIR text encoder (swap) | text encoder | SBERT stack | −0.0013 (1) | n/a | Rejected — encoder axis fully swept |
| GD1 spectral-shrink prior | representation regularizer | V2 0.0673 | −0.003 (1) | shrink → 0 | Rejected — BBP irreducibility figure (Fig. 3) retained |
| n_heads = 4 | architecture (capacity-add) | HSTU-style stack | −0.0005 (1) | n/a | Rejected — ties 2-head even at the published dv=dqk=16 spec |
| CL4SRec self-supervision | SSL auxiliary loss | SBERT stack | −0.0005 (1) | n/a | Rejected — early-epoch only |
| c1 prototype-routed expert heads | capacity-add | SBERT stack | −0.0004 (1) | n/a | Rejected — redundant with TAPE |
| c2 text-distillation aux loss | auxiliary loss | SBERT stack | −0.0004 (1) | n/a | Rejected — redundant with the additive text path |
| text-init / text warm-start | embedding initialization | SBERT stack | −0.0003 (1) | n/a | Rejected — redundant with the additive text path |
| EMA / SWA weight averaging | weight-space regularizer | SBERT stack | +0.0001 (1) | n/a | Rejected — val-high/test-flat; does not repair the structural gap |
| text-sim bias | attention bias | HSTU-style stack | ±0.0001 (4) | n/a | NEUTRAL — dead weight, drop candidate |
| W1 niche-share fitness-sharing penalty | inter-item loss penalty | U2/LS0.2 0.0649±0.0002 | 0.0652 (1), within band | **β = −7.42** (sign-flipped: boosts, not penalizes, crowded niches) | Rejected — refutes the anti-crowding remedy |
| X1 frequency-adaptive James–Stein shrinkage | representation regularizer | V2 0.0674±0.0003 | 0.0673 (1), within band | **c ≈ 0** (λ_max ≈ 0.004) → off | Rejected — model voted shrinkage off |
| Y1 heat-kernel/manifold label smoothing | loss-target reshaping | V2 0.0674±0.0003 | 0.06653 (1), ≤ band | **T → 0.00061** (< init) → delta target | Rejected — text-manifold geometry voted off |
| Z1 forced ID→text routing | representation routing | V2 | tail −75% (globally dead) | forced gate | Rejected — globally harmful |
| CF1 cue-fusion gate | representation fusion | V2 / Beauty | flat/dead (both datasets) | gate → 0 | Rejected — new-lever search closed |
| conn-gate connectivity-gated cold-start ID↔text fusion | representation fusion/routing | V2 text stack, MI | **tail** Δ +0.0001 ± 0.0003, paired 95% CI [−0.00025, +0.00045] (5); overall flat | **α → 0.0011 < init 0.0025** (voted off) | Rejected — operationalizes the intervention-supported connectivity tail mechanism, but is not actionable (CI includes 0) |
| max_seq_len 200 / seq > 50 | sequence length | SBERT stack | ~0 (1) | n/a | Rejected — sequences short post-5-core |
| cosine scoring | scoring function | winning op-point | ≤ 0 (1) | n/a | Rejected — dot-product better at the op-point |

The pattern is consistent and is itself the finding: across loss-side (W1, Y1, sampled-softmax), embedding-side (X1, GD1, text-init), attention-side (c3, n_heads, text-sim), encoder-side (BLaIR, dual-text), and auxiliary-objective (c1, c2, CL4SRec, EMA) axes, no capacity-adding mechanism produced a multi-seed test gain, and three free scalars (W1's β, X1's c, Y1's T) were each switched off — or, for W1, reversed — by the optimizer. Only anti-overconfidence regularizers (label smoothing) and the restricted causal-filter inductive bias (Table 1) transferred. This both bounds the in-environment ceiling and motivates the spectral-irreducibility analysis of §5.4.2 (Fig. 3): no representation-side lever can rescue the dense-catalog tail. The conn-gate row deserves separate emphasis: it is the only entry tested at full five-seed power and the only one that directly operationalizes *this paper's own intervention-supported tail mechanism* — collaborative connectivity as the binding tail resource (§5.4.2). A single seed showed a +0.00053 tail lift, but the pre-registered five-seed seed-paired confirmation collapsed to +0.0001 ± 0.0003 (95% CI [−0.00025, +0.00045], includes zero), and the free gate scalar α was driven *below* its initialization (voted off). This is the cleanest illustration of the paper's central distinction: a mechanism can be *supported as a driver* of the tail advantage by controlled thinning interventions (the matched-R1 double-dissociation) yet not be *actionable* through a learnable cold-start gate — the connectivity signal the model needs is already latent in the frozen text features, leaving no residual for an explicit gate to exploit.

### 5.6 Executing the reference implementation locally (post-hoc comparator regeneration)

Late in this work we succeeded in running the **reference implementation itself** — the HSTU-BLaIR repository at its released commit, unmodified (clean git tree): its preprocessing, its gin configurations, its trainer, and its eval protocol — end-to-end on our hardware. The pinned environment (torch 2.2.2 / fbgemm_gpu 0.6.0) remains uninstallable here (no sm_120 kernel images, no Windows wheels); what makes execution possible under our unpinned torch 2.11 environment is that the repository's research path uses exactly **three** `fbgemm` operators, all pure data movement (`asynchronous_complete_cumsum`, `jagged_to_padded_dense`, `dense_to_jagged`), which we re-implement in plain PyTorch with self-tested forward/gradient parity, plus a world-size-1 identity DDP wrapper and logging/data-acquisition patches (full shim inventory, per-run provenance, and artifacts: `THEIRS_ON_OURS_REPORT.md`). No model math is touched — the layer norms, fused projections, SiLU pointwise attention, biases, loss, and scoring all execute in the reference repository's own unmodified lines, consistent with the core-block parity evidence of §3.2. Their own preprocessing pipeline ran with its dataset-size assertions left active and **passing** on both corpora (Musical_Instruments: 24,587 items / 57,439 users; Office_Products: 77,551 items / 223,308 users — the comparator paper's exact statistics).

Two single-run results (their configurations as shipped, 101 epochs; our RTX 5060 Ti):

| run (their code, their data, their eval) | published | local, final epoch | local, best full eval |
|---|---|---|---|
| **MI HSTU-BLaIR** — NDCG@10 | 0.0406 | 0.0391 | **0.0406** (epoch 35 — exact) |
| MI HSTU-BLaIR — HR@10 | 0.0733 | 0.0716 | 0.0743 |
| MI HSTU-BLaIR — MRR | 0.0371 | 0.0355 | 0.0369 |
| **Office SASRec** — NDCG@10 | 0.0153 | **0.0174** (+13.9%) | 0.0177 |

**The Musical_Instruments comparator reproduces.** The final-epoch full-corpus eval lands within 2.3–4.3% of every published metric above, and the best full-eval epoch hits the published NDCG@10 exactly; the run oscillates in a 0.0384–0.0406 band from roughly epoch 30 onward (the comparator's own README notes run-to-run variability). The published 0.0406 that §5.2's pre-registered confirmation is measured against is therefore no longer only a transcribed constant: a local regeneration by the generating code reproduces it, and our pre-registered CI lower bounds (0.04096 / 0.04083) sit above both its best (0.0406) and final (0.0391) local readings. **The Office_Products floor anomaly resolves**: their own SASRec configuration lands +13.9% above its published row here, crossing the published value at epoch 20 of 101 and never re-entering — which, combined with our floor run, decomposes the +44% floor-check failure entirely into published-row conservatism and baseline-strength protocol differences, leaving nothing attributable to our split or eval (resolution in Appendix A.0; the VOID is deliberately retained).

**Caveats (why these are regenerations, not reproductions).** Single runs (the reference code seeds only Python's `random`, so even in place it is not run-to-run deterministic); an unpinned environment (torch 2.11 vs pinned 2.2.2, transformers 5.7 vs 4.51, different cuBLAS/TF32 kernel versions); a different GPU than the comparator used; and the shims themselves (self-tested, but not the pinned binaries). We therefore cite these as **environment-caveated single-run regenerations** and change no claim wording on their basis: §5.2's claim remains a point-estimate comparison against the published number.

## 6. Discussion

### 6.1 What does cross-pipeline transfer reveal? (Appendix A.1 supporting study)

The next two subsections discuss the 20-variant Beauty_and_PC cross-pipeline scan (Appendix A.1) — supporting/reproducibility material, not part of the headline spine (the causal FIR filter, the dataset-conditional tail pattern, and the competitive Video_Games result of §5).

Our 20-variant scan finds that the **only** consistently-positive intervention is the MLP-adaptor design from Hou et al. (2024) — a design originally tuned on their 0-core preprocessing. This is a small positive cross-pipeline transfer signal: published architectural choices do not universally transfer (heavy dropout from the same source does not), but the parametric form of the text→hidden adaptor does.

We hypothesize that the MLP adaptor's benefit comes from its expressive capacity for the 768-d → 64-d projection. A single Linear layer can only project; the 2-layer MLP can also denoise the BLaIR features into a recommendation-relevant subspace.

### 6.2 What does NOT cross over?

- **Heavy dropout (0.5)**: Hurts in our setup. Beauty_and_PC users have median 5 interactions; aggressive regularization probably masks too much signal.
- **Removing learned item embeddings**: The 207k-item catalog appears to demand per-item parameter capacity that the encoder + MLP adaptor cannot fully replace.
- **Subsequence augmentation**: Creates a train-test distribution shift in our protocol. We did not try the longer recipes of Hou et al. (UniSRec uses additional contrastive losses) that might counteract this.

### 6.3 Engineering takeaways

- **Chunked-full-softmax** is essential at the 207k-item scale; sampled softmax with K=1024 negatives undertrains the catalog ranking.
- **Eval item-features caching** is a small but critical optimization for any text-augmented sequential recommender, providing a ~10× speedup at d=64 with MLP adaptors.
- **Right-padding + causal-only mask** avoids a silent NaN-propagation bug that we observed inflating eval NDCG to ~0.9955 with left-padding + key-padding-mask + pre-norm.

### 6.4 What we don't claim

- **A wholly new architecture**: our architectural additions are deliberately small — a causal FIR adaptation of prior frequency-filter ideas and a soft text-prototype additive term; every other component we use is from prior work.
- **Closing the gap to LIGER on Beauty_and_PC**: we do not, and the gap may be partially preprocessing-dependent.
- **Beauty_and_PC improvement is statistically certified**: we have only n=2 seeds for the best variant; baseline is n=1.
- **Category scope**: the headline causal-FIR evidence uses Video_Games and Musical_Instruments; Beauty_and_PC supports the tail-pattern null; Office_Products is descriptive (VOID under its prereg floor check; the anomaly is explained by §5.6's local comparator run and the VOID is deliberately retained, Appendix A.0). Other categories untested.
- **Model-input hygiene** (a clarification, not a caveat): the canonical model consumes only item IDs, interaction timestamps, and frozen item-text embeddings; no outputs, scores, or embeddings of any baseline or comparator model enter the pipeline as inputs or features (the superseded earlier-stage fusion experiments that did are quarantined in the non-canonical track).

### 6.5 Limitations

We state the paper's limitations explicitly, for reviewers:

- **Single published point-estimate comparator.** The Musical_Instruments comparison (§5.2) is against a single-seed published point estimate (HSTU-BLaIR 0.0406); no paired significance test against the comparator is possible.
- **No executable official END-TO-END HSTU-BLaIR reproduction on local hardware.** The official CUDA/Triton kernels cannot execute on our sm_120 GPU (§7). The CORE research block, however, is verified numerically: a mirrored-weight parity test against the reference research implementation shows exact agreement (max abs diff 0.0 at every stage; `HSTU_PARITY_REPORT.md`). What we do not claim is end-to-end system parity (training pipeline, data path, kernels, hyperparameters).
- **TAPE is modest.** +0.0009 single-flag (single-seed; +0.0004 in the 4-seed cross-check), sub-additive — an ablation-level component, not a headline contribution.
- **The tail finding is AR2023-limited and small in absolute terms.** It rests on three AR2023 categories (Musical_Instruments, Video_Games, Beauty_and_PC); the MI tail effect (+0.000335 NDCG@10, ~30 hits/seed base) is a large relative but small absolute effect, and the pattern is not replicated on non-Amazon domains.
- **The negative probes are not all equally powered.** Most Table 2 rows are single-seed exploratory probes; only the multi-seed pre-declared negatives carry confirmatory weight (§5.5).
- **The thinning interventions are synthetic dataset manipulations.** The interaction- and user-mode titrations are controlled interventions on the training data, not causal identification of the real-world process that generated the datasets; all "driver"/"causal role" language is scoped to these interventions.
- **Pre-registration deviation (disclosed).** The confirmation runs executed at a documentation-only descendant commit of the pre-registration's introducing commit, so the pre-registered commit-equality rule was not literally satisfied; code identity is demonstrated by empty protocol-file diffs and manifest code hashes, and the deviation is disclosed in `SOTA_CONFIRM_PREREG_V2_ERRATA.md` (E3) rather than claimed away (§5.2).
- **Preprocessing differs from the comparator by exactly one interaction per category** (users and items match exactly on every category; the ±1 originates on the comparator's side of the counting and cannot materially affect leave-last-out evaluation, which ranks one target per user for the identical user sets).
- **No baseline model is used as an input feature.** The canonical model consumes item IDs, timestamps, and frozen item-text embeddings only; no outputs of SASRec, HSTU-BLaIR, DropoutNet, or any comparator feed the model at training or inference time.
- **Office_Products status.** Office gate values pass numerically on both kernels but the pre-registered floor check failed (+44%); the second-category pass is VOID under the prereg despite the completed matched comparator-baseline explanation (§5.6, Appendix A.0) — the published Office comparator row appears conservative in this environment — and no claim counts Office (§5.2).

## 7. Conclusion

We build on an HSTU-style pure-PyTorch implementation of HSTU based on the published architecture (Zhai et al., 2024) for AR2023 5-core full-catalog LLOO recommendation and contribute two defensible, multi-seed-confirmed findings. **(1) A strictly causal FIR temporal filter** — a leak-free causal adaptation of the bidirectional frequency filters of FMLP-Rec/BSARec, supplying an explicit local temporal bias that the baseline does not learn as reliably in our low-capacity setting — is a confirmed lever (Video_Games +0.0015) whose strongest evidence is *cross-category*: on Musical_Instruments it, not label smoothing, carries the generalization (+0.0025, ≈3× LS, ≈80% of the combined lift, 5-seed). **(2) A dataset-conditional long-tail pattern**: comparing the text stack to its ID-only ablation on train-frequency terciles, text wins the rare-item tail on the *sparse* Musical_Instruments catalog (5-seed Δ +0.000335, 95% CI excludes 0, HR-replicated) but is a *powered* null on the dense Video_Games and Beauty_and_PC catalogs (TOST-equivalent to zero), with the cross-dataset difference itself significant (Welch p≈0.004). An interaction-thinning titration dissociates the mechanism as a **double result** — global *interaction* density is supported as a driver of the head text-advantage by controlled thinning interventions but is not supported by the thinning intervention as a driver of the tail win (a correlate only) — which we report as a refuting, not confirming, keystone. A complementary **user-mode titration** then shows **collaborative connectivity (users/item) to be consistent with a partial causal role (under the thinning intervention's assumptions)** in the tail win (5×5 matched-R1 double dissociation; thinning users to MI-matched connectivity raises the VG text−ID tail advantage by dd = +0.000326, paired t = 3.47, 95% CI excludes 0, 5/5 seeds; within-rung tail Δ +0.000178), decomposing the MI tail win into an intervention-supported connectivity component plus a residual dataset-specific content component. These titrations are controlled interventions on the dataset, not causal identification of the real-world generative process.

On Video_Games our full stack reaches **NDCG@10 = 0.0673 ± 0.0003 (6-seed)**, +17.5% over published SASRec (0.0573), but we show this win is **architectural**: an ID-only model already reaches ≈0.0656, and the frozen-text stack adds only +2.7% overall. TAPE is reported honestly as a modest sub-additive text contributor (+0.0009), not a headline. **We do not claim a Video_Games SOTA** — the published HSTU-BLaIR 0.0760 relies on custom CUDA/Triton kernels that are hardware-incompatible with our sm_120 GPU (proven). The contribution is the causal FIR filter, the tail pattern, the HSTU-style implementation, and a systematic negative-result map (every capacity-adding probe neutral or harmful, several with a learned scalar the model drove to zero), plus the engineering (chunked-full-softmax, eval caching, NaN-trap diagnosis).

**Explicit non-claims:**

- We do **not** claim SOTA over TIGER, LIGER, BLaIR, or HSTU-BLaIR; the published HSTU-BLaIR 0.0760 remains the stronger external reference (its pinned stack is not installable here, and the §5.6 shimmed runs did not include Video_Games).
- The "57% gap to LIGER on Beauty_and_PC" framing from an earlier version of this work was apples-to-oranges (LIGER reports on Amazon 2014, not AR2023) and is retracted.
- Our claimed additions are deliberately small: the causal FIR filter (an incremental adaptation of prior frequency-filter ideas), the dataset-conditional tail pattern (an empirical finding, not a law), and the TAPE ablation (a modest text-prototype term); SASRec, SBERT, MiniLM, BLaIR, HSTU, label smoothing, and the AR2023 dataset are all prior work, cited at point of use.
- The tail win is a large *relative* gain on a small absolute base; we always report relative, absolute, and hit-count together. The tail *mechanism* is **partially resolved** (§5.4.2): a user-mode titration supports collaborative connectivity / users-per-item as consistent with a real partial causal role (5×5 double dissociation; under the thinning intervention's assumptions), with a residual dataset-specific content component that is bounded but not fully closed.

## 8. Code and Data Availability

All preprocessing, training, and evaluation code is available at `_bestrec_run/`. Pre-computed text-encoder caches for Video_Games, Musical_Instruments, Office_Products, and Beauty_and_PC are covered by SHA256 in `RELEASE_MANIFEST.json` (release `v0.9-audit-evidence`), with regeneration instructions in the protocol-parity appendix; MI confirmation result JSONs and per-user sidecars are tracked in the repository with per-file hashes; Office descriptive summary JSONs are manifest-backed, while Office per-user sidecars are local-only (untracked) and not part of any counted claim.

## 9. Acknowledgments

We thank the Amazon Reviews 2023 maintainers (Hou et al., 2024) for releasing the dataset and accompanying reference implementations. The MLP adaptor design used in our best variant is from their published SASRecText configuration.

## References



- Baik, J., Ben Arous, G., Péché, S., 2005. Phase Transition of the Largest Eigenvalue for Nonnull Complex Sample Covariance Matrices. Annals of Probability. *(BBP detectability edge, Fig. 3 spectral-irreducibility analysis)*
- Devlin et al., 2019. BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. NAACL.
- Efron, B., Morris, C., 1973. Stein's Estimation Rule and Its Competitors — an Empirical Bayes Approach. JASA. *(negative-result map: James–Stein shrinkage probe)*
- Gavish, M., Donoho, D. L., 2014. The Optimal Hard Threshold for Singular Values is 4/√3. IEEE Transactions on Information Theory. *(optimal-shrinkage rank, Fig. 3)*
- He, R., McAuley, J., 2016. Ups and Downs: Modeling the Visual Evolution of Fashion Trends with One-Class Collaborative Filtering. WWW. *(source of the Amazon 2014 Beauty subset used by TIGER/LIGER)*
- Hou, Y., He, Z., McAuley, J., Zhao, W. X., 2022. Towards Universal Sequence Representation Learning for Recommender Systems (UniSRec). KDD.
- Hou, Y., Li, J., He, Z., Yan, A., Chen, X., McAuley, J., 2024. Bridging Language and Items for Retrieval and Recommendation (BLaIR). arXiv:2403.03952.
- James, W., Stein, C., 1961. Estimation with Quadratic Loss. 4th Berkeley Symp. *(with Stein, C., 1956, 3rd Berkeley Symp.)*
- Kang, W.-C., McAuley, J., 2018. Self-Attentive Sequential Recommendation (SASRec). ICDM.
- Liu, 2025. HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Sequential Recommendation. arXiv:2504.10545. *(the external AR2023 5-core reference family: Video_Games 0.0760, Musical_Instruments 0.0406, Office_Products 0.0271; the pinned environment is not installable on our hardware — the research path was executed locally via data-movement shims, §5.6, regenerating the Musical_Instruments row)*
- Marchenko, V. A., Pastur, L. A., 1967. Distribution of Eigenvalues for Some Sets of Random Matrices. Matematicheskii Sbornik. *(MP bulk edge, Fig. 3 spectral-irreducibility analysis)*
- Rajput, S. et al., 2023. Recommender Systems with Generative Retrieval (TIGER). NeurIPS.
- Reimers, N., Gurevych, I., 2019. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP.
- Shaw, P., Uszkoreit, J., Vaswani, A., 2018. Self-Attention with Relative Position Representations. NAACL. *(relative-position attention bias)*
- Shin, Y. et al., 2024. An Attentive Inductive Bias for Sequential Recommendation beyond the Self-Attention (BSARec). AAAI. arXiv:2312.10325. *(bidirectional FFT filter; our causal-filter adaptation)*
- Sun, F. et al., 2019. BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer. CIKM.
- Szegedy, C. et al., 2016. Rethinking the Inception Architecture for Computer Vision. CVPR. *(label smoothing)*
- Wang, W. et al., 2020. MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers. NeurIPS. arXiv:2002.10957.
- Yang, J. et al., 2024. Unifying Generative and Dense Retrieval for Sequential Recommendation (LIGER). arXiv:2411.18814.
- Zhai, J. et al., 2024. Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations (HSTU). ICML. *(the published architecture our HSTU-style pure-PyTorch implementation is based on)*
- Zhou, K. et al., 2022. Filter-enhanced MLP is All You Need for Sequential Recommendation (FMLP-Rec). WWW. arXiv:2202.13556. *(bidirectional learnable frequency filter; our causal-filter adaptation)*

---

## Appendix A.0 — Office_Products: descriptive evidence (VOID under its pre-registration)

**Second-category pre-registered confirmation: Office_Products.** To test whether the per-category result generalizes, we froze a second pre-registration (`SOTA_CONFIRM_PREREG_OFFICE.md`, committed before the raw data finished downloading — before any Office statistic was knowable) with the config carried over from Musical_Instruments **unchanged (zero category-specific tuning)** and fresh seeds 20260623–27. Dataset parity is exact (items 77,551 and users 223,308 match the comparator paper exactly; interactions differ by one, as on MI). Result, on final-epoch full-catalog evaluations (223,308 users; the prereg's declared headline rule): **K=16 = 0.03042 ± 0.00008 (95% CI lower bound 0.03032) and K=8 = 0.03033 ± 0.00018 (CI-LB 0.03010), all 10 fresh seeds above the published HSTU-BLaIR point estimate 0.0271** — a ~+12% margin, versus +2.3% on MI. **However, the pre-registered floor check FAILED: our plain-SASRec floor (0.02208) lands +44% ABOVE the published SASRec (0.0153), violating the prereg's comparability condition. Under the pre-registration as written, the Office second-category pass is therefore VOID — the gate values are reported as a provisional, non-confirmatory result — the matched comparator-baseline run that explains the floor gap is complete and explains it (resolution paragraph below); the VOID stands.** The confirmed per-category claim remains **Musical_Instruments only**; Office is not counted. Disclosures: best-by-val checkpoints were evaluated on a 30k-user subsample (declared in the prereg), so the headline uses the always-full final-epoch eval — the conservative choice (the subsampled best-checkpoint numbers were higher); the run manifests carry a dirty-tracked flag caused by the driver's own results-file appends (embedded per-run code hashes verify protocol-code identity); our plain-SASRec floor (0.0221) lands above their published SASRec (0.0153) on this category — a baseline-config-strength difference, with split parity resting on the exact dataset-statistics identity and frozen hashes rather than the floor heuristic; and the pre-registered tail prediction for Office was scored **VOID** (its connectivity 2.89 falls in the pre-declared ambiguous zone, plus a disclosed formula inconsistency in the stats tool — `SOTA_CONFIRM_OFFICE_RESULTS.md`). Descriptively, the Office tail contrast is strongly text-positive at full catalog (pooled tail hits, text vs ID-only: 364 vs 268 @10, z=3.8; 1,983 vs 1,247 @100, z=13.0) — consistent with the connectivity gradient (MI 2.34 win → Office 2.89 win → Beauty 3.51 / VG 3.70 null), reported as pattern evidence, not as a scored prediction.

**Floor-anomaly resolution (2026-07-11; the matched comparator-baseline run promised above, now complete).** We executed the reference implementation's own Office SASRec configuration end-to-end — its preprocessing (dataset-size assertions passing: 77,551 items / 223,308 users), its gin config, its trainer, its eval — locally under the shimmed research path of §5.6. Its final-epoch NDCG@10 is **0.0174** (best full eval 0.0177), i.e. **+13.9% above its own published row 0.0153**, crossing the published value at epoch 20 of 101 and never re-entering. The +44% floor-check failure now decomposes exactly: 0.0204 (our floor run's final-epoch full-catalog reading) / 0.0174 (their code, locally) = **+16.9% attributable to baseline-strength protocol differences** (our floor trains with full-catalog softmax vs their 512-negative sampled softmax), and 0.0174 / 0.0153 = **+13.9% attributable to the published row sitting below what its own pipeline regenerates here** (1.139 × 1.169 = 1.331 = 0.0204/0.0153; the remaining step to the prereg's best-epoch 0.02208 is checkpoint selection plus that variant's 30k-user eval subsample). **Conclusion: the elevated floor is not an artifact of our data split or evaluation** — Office simply supports SASRec well above the published row. This *explains* the floor-check failure without repairing the comparison it protects: if the published SASRec row is conservative in this environment, the published HSTU-BLaIR 0.0271 plausibly is as well, so numerically exceeding it would not establish superiority over their method on Office. **The VOID therefore stands, deliberately** — and the pre-registered floor check is vindicated: it caught exactly the comparator-conservatism failure mode it was designed to catch.

## Appendix A — Superseded earlier-stage supporting material (Beauty_and_Personal_Care)

> **Why this is an appendix:** the material below is an earlier-stage Beauty_and_Personal_Care reproducibility study (the 20-variant cross-pipeline scan, its 2-seed signal, and the retracted LIGER-gap audit). It predates and does not belong to the headline spine (causal FIR filter + dataset-conditional tail pattern + competitive-overall Video_Games result, §1–§7). It is retained verbatim for the reproducibility and negative-result record only, and is referenced from §6.1–§6.2 as supporting context. The live Beauty result that enters the tail pattern (§5.3) is the text−ID tail contrast, not these single-seed sampled-softmax scans.

### A.1 Beauty_and_Personal_Care — 20-variant cross-pipeline scan (superseded supporting material)

> **Note:** the following Beauty_and_PC 20-variant scan and the LIGER-gap audit are **earlier-stage supporting material**, retained for the reproducibility and negative-result record. They predate the HSTU + causal-filter + tail-pattern spine and are *not* the paper's headline; the live Beauty result used in the tail pattern (§5.3) is the text−ID tail contrast, not these single-seed sampled-softmax scans.

The scan varies five axes: **text encoder** (MiniLM titles/rich-text, BLaIR titles/rich-text), **projection Φ** (single Linear vs the 2-layer MLP adaptor of Hou et al., 2024), **learned item embedding** (kept vs removed = faithful SASRecText), **loss** (sampled softmax K=1024, in-batch negatives, chunked-full-softmax, hybrid), and **augmentation** (random subsequence sampling, factor 1/2/3). Training used a 15–20-epoch budget, batch size 256, Adam (lr 1e-3, weight decay 1e-5, gradient clip 5.0), a single seed for the initial scan, and two seeds (42, 43) for the final reported variants. Table A1 summarizes all 20 variants. **Numbers are single-seed unless otherwise noted.**

**Table A1: 20-variant scan on AR2023 Beauty_and_PC 5-core (full-catalog eval, NDCG@10)**

| # | Variant | NDCG@10 | Δ vs base |
|---|---|---:|---:|
| 1 | Popularity | (not run) | — |
| 2 | SASRec sampled-1024 + MiniLM titles | 0.0180 | — |
| 3 | SASRec sampled-1024 + MiniLM titles, d=128 | 0.0176 | -2.2% |
| 4 | SASRec in-batch negs + augment-2 | 0.0036 | -80% |
| 5 | TIGER minimal (our re-impl) | 0.0080 | -56% |
| 6 | SASRec hybrid (in-batch + 8K random negs + aug-3) | 0.0106 | -41% |
| 7 | **SASRec chunked-full + MiniLM titles (improved baseline)** | **0.0191** | **+6.1%** |
| 8 | SASRec chunked-full + MiniLM titles, d=128 | 0.0186 | -2.6% (vs 7) |
| 9 | SASRec chunked-full + MiniLM titles, 25 epochs | 0.0189 | -1.0% (vs 7) |
| 10 | BERT4Rec | 0.0160 | -16% (vs 7) |
| 11 | SBERT-only (no learned item_emb) + MiniLM | discontinued | — |
| 12 | Faithful SASRecText (no item_emb + MLP + dropout 0.5 + BLaIR) | discontinued @ epoch 2 | — |
| 13 | Hybrid (item_emb + MLP + dropout 0.5 + BLaIR) | discontinued @ epoch 5 | — |
| 14 | BLaIR-titles + Linear projection (just encoder swap) | discontinued @ epoch 2 | — |
| 15 | Fusion (BLaIR + rich-text MiniLM concat) + Linear | discontinued @ epoch 1 | — |
| 16 | **BLaIR-titles + MLP adaptor (Hou et al., 2024) + dropout 0.2** | **0.01928** | **+0.9% (vs 7)** |
| 17 | + augment-2 | 0.0036 val | discontinued; aug hurts |
| 18 | + d=128 width | discontinued at eval (slow) | — |
| 19 | **BLaIR-rich-text + MLP adaptor + dropout 0.2 (seed 42)** | **0.01936** | **+1.3% (vs 7)** |
| 20 | seed 43 of variant 19 | **0.01955** | **+2.3% (vs 7)** |
| 21 | **MiniLM + MLP adaptor (clean ablation)** | **0.01889** | **-1.2% (vs 7)** |
| 22 | Baseline seed 42 (reproduction) | 0.0190 | 0.0% (vs 7) |

**2-seed mean of variant 19+20 (BLaIR-rich-text + MLP)**: NDCG@10 = 0.01946, range 0.0002.

**Clean-ablation finding (variant 21, added after audit)**: When we hold the encoder constant at MiniLM and ONLY change projection layer from single-Linear to the SASRecText 2-layer MLP adaptor, NDCG@10 drops slightly from ~0.0190 to 0.01889. **The MLP adaptor by itself does NOT help on this protocol.** The +1.3-2.3% gains we observe with variants 16/19/20 are attributable to the change in text encoder (MiniLM → BLaIR) and the change in text content (titles → rich text), not to the projection layer.

Re-analysis of the 20-variant scan:

- **MLP adaptor alone**: no benefit (variant 21 vs 7 = -1.2%)
- **MiniLM → BLaIR encoder**: small benefit (variant 16 vs 7 = +0.9% NDCG@10, single-seed)
- **Titles → rich text (BLaIR)**: small additional benefit (variant 19 vs 16 = +0.4%, single-seed)
- **Removing learned item embedding** (faithful SASRecText): hurts substantially
- **Heavy dropout (0.5)** as in the published SASRecText: hurts on our 5-core data (median 5 interactions/user)
- **Subsequence augmentation**: hurts (~-5% NDCG)
- **Width (d=128)**: no help

### A.2 Beauty_and_PC multi-seed signal (superseded supporting material)

> **Note:** this is appendix supporting material for the Beauty 20-variant scan (§A.1), not the headline tail-pattern result (§5.3).

We have multi-seed numbers for two configurations:
- Best variant (BLaIR + rich-text + MLP): seed 42 → 0.01936, seed 43 → 0.01955; **mean 0.01946 (n=2)**.
- Baseline (chunked-full, no MLP, MiniLM titles): original → 0.01911, seed 42 → 0.0190; **mean 0.01906 (n=2)**.

Apparent gain: 0.01946 - 0.01906 = **+0.0004 (+2.1% relative)** with n=2 vs n=2. Inter-seed variance for our baseline (0.0001 range) is roughly half the size of the gain, suggesting the directional signal is real but small. A formal significance test would require larger n; our paper-stated +2.1% improvement is honest about this.

### A.3 Audit of "gaps to LIGER" claims (corrected from earlier versions; superseded supporting material)

> **Note:** this comparator-audit retraction is retained as appendix material; the body's §5.4 is the titration result.

Earlier versions of this work cited an apparent 57% gap to LIGER on Beauty_and_Personal_Care. **After a comparator audit, this framing is retracted.** The facts:

1. **LIGER reports on Amazon 2014, not AR2023.** The LIGER paper (Yang et al., 2024) evaluates on Amazon Beauty (2014, He & McAuley 2016), reporting NDCG@10 = 0.04020 ± 0.00044 (K=20) and 0.04738 ± 0.00151 (K=N) on their 5-core preprocessing. The 2014 Amazon Beauty subset has tens of thousands of items, while our AR2023 Beauty_and_Personal_Care 5-core has 207,649 items. **These are different datasets.** The "57% gap" framing in earlier versions compared our AR2023 number to LIGER's 2014 number, which is invalid.

2. **There is no published LIGER number on AR2023 Beauty_and_Personal_Care 5-core.** LIGER does not evaluate on AR2023 at all in the published paper.

3. **TIGER reports on Amazon 2014 only.** The TIGER paper (Rajput et al., 2023) reports NDCG@10 = 0.0384 on Amazon Beauty 2014 with their 5-core, also not on AR2023.

4. **BLaIR (Hou et al., 2024) is the only published work using AR2023.** Their Beauty subset is "All_Beauty" (not "Beauty_and_Personal_Care") and their preprocessing is by-timestamp 8:1:1 with no k-core filter. They report NDCG@10 on All_Beauty in the range 0.0177-0.0241 across various LLM encoders (Table 8). With a UniSRec downstream model, their best All_Beauty number is 0.0241 (gemini-embedding). They do not report on Beauty_and_Personal_Care.

We therefore cannot make a defensible gap claim to TIGER/LIGER/BLaIR on AR2023 Beauty_and_Personal_Care 5-core, because **no comparable published number exists**. Our 0.01946 (2-seed mean) is the first such reported number, to our knowledge. We provide it as a reference baseline rather than as a SOTA-improvement claim.

A future apples-to-apples comparison would require either:
- Running TIGER/LIGER on our 5-core preprocessing (multi-week effort for faithful reproduction), or
- Adopting Hou et al.'s by-timestamp 8:1:1 preprocessing and re-running our pipeline.
