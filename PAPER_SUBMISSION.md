# Artifact-Gated Evaluation of a Causal FIR Module for Sequential Recommendation

**Authors**: [maintainer to supply before submission — TORS review is single-blind and the manuscript must carry real author/affiliation/contact metadata; withheld only in this public working copy]

*Reader edition — rendered from the canonical markdown source and retaining the full evidence record. The focused ACM TORS package is `paper_tex/PAPER_TORS.pdf` (review rendering), `paper_tex/PAPER_TORS_acmsmall.pdf` (journal-layout main), and `paper_tex/PAPER_TORS_SUPPLEMENT.pdf` (reviewer supplement; see `VENUE_PLAN.md`); venue metadata (CCS concepts, keywords) lives in the TeX artifacts.*


---

## Abstract

We test whether a small, identity-initialized causal finite-impulse-response (FIR) residual provides a robust modular gain in sequential recommendation.
On three outcome-known Amazon Reviews 2023 category/split settings, learned FIR minus identity estimates are positive; on Musical_Instruments the effect is +0.002265, ordinary Welch 95% CI [0.001928, 0.002602].
The learned filter also exceeds an equal-parameter current-position-only placebo (+0.001941 [+0.001788, +0.002095]), but does not separate from a 16-parameter shared causal filter (-0.000081 [-0.000337, +0.000175]), limiting any claim of per-channel-tap necessity.
A prospectively frozen same-investigator MovieLens 1M study is negative: learned minus identity +0.000000 [-0.000074, +0.000075] and learned minus pointwise +0.000035 [-0.000057, +0.000127].
Thus the parsimonious FIR arms support only conditional coefficient-count compression, not practical efficiency or cross-domain replication.
Outcome-known same-evaluator AlphaFuse-style and WEARec studies improve comparator coverage but remain whole-package, unequal-model evidence below the paper's existing reference.
Overall, the contribution is a narrow detachable implementation and an artifact-gated evaluation record, not a new architecture, general FIR benefit, SOTA result, or independent confirmation.
A fail-closed graph preserves positive, null, deviated, and VOID outcomes under one reporting rule.

---

## 1. Introduction

Sequential recommendation models predict a user's next item from their interaction history. Self-Attentive Sequential Recommendation (SASRec; Kang & McAuley, 2018) and its bidirectional cousin BERT4Rec (Sun et al., 2019) established Transformer-based sequential recommenders as competitive baselines. Subsequent work integrated pre-trained language models for richer item-text representations (ZESRec — Ding et al., 2021; UniSRec — Hou et al., 2022; RecFormer — Li et al., 2023; BLaIR — Hou et al., 2024) and explored generative-retrieval architectures with discrete semantic IDs (TIGER — Rajput et al., 2023; LIGER — Yang et al., 2024).

Recent benchmarks consolidate evaluation around the Amazon Reviews 2023 (AR2023) dataset (Hou et al., 2024), but superficially similar “5-core” labels hide different preprocessing contracts. Our pipeline iteratively filters both users and items to at least five retained interactions and then applies leave-last-out. LIGER reports user-and-item filtering, whereas the TIGER paper states filtering users with fewer than five reviews; the exact geometry of TIGER's released preprocessing is not established here. Both use Amazon Reviews 2014 rather than AR2023. Their holdout chronology is related to ours, but their dataset and filtering geometry are not numerically interchangeable. Hou et al.'s AR2023 reference repository instead uses a **0-core** variant (`external/AmazonReviews2023/seq_rec_results/`). Numbers across these variants are not directly comparable.

Recommender evaluation is vulnerable to mistuned baselines, incompatible protocols, and irreproducible result selection (Ferrari Dacrema et al., 2019; Ferrari Dacrema et al., 2021). We therefore pair the method with a per-paper discipline: git-frozen protocols, a fail-closed graph that recomputes 200 reported cells across 24 claim families, environment-caveated comparator regeneration, and symmetric adjudication. Failures are retained. In particular, the original Office_Products protocol remains VOID after its own floor check exposed an environment mismatch, although a redesigned fresh-seed protocol later passed (§5.2; Appendix A.0).

Using an HSTU-style pure-PyTorch encoder based on Zhai et al. (2024), we ask whether one small causal filtering component survives matched controls and remains positive under an untuned cross-category reuse. Our contribution ledger is deliberately limited to three items:

1. **A canonical causal FIR module.** We adapt earlier bidirectional frequency filters to a strictly left-causal, depthwise residual that is identity-initialized and gradient-active under the all-position objective (§3). This is a modular component, not a new recommender architecture.
2. **Internal evidence, a negative non-Amazon test, and a mechanism boundary.** Learned FIR–identity estimates are positive on three outcome-known Amazon category/split settings, and a frozen Software attempt produced +0.005062 [+0.004591, +0.005533] but remains outcome-known same-team robustness (§5.2). On Musical_Instruments, learned taps do not separate from a shared causal filter, but they beat an equal-parameter current-position-only DCT/GELU placebo by +0.001941 [+0.001788, +0.002095]. A prospectively frozen MovieLens 1M study then failed to replicate learned FIR against identity or pointwise. Its shared/grouped/low-rank arms met a pre-declared noninferiority margin versus learned FIR only conditionally on that failed replication gate. Together these results do not support a unique per-channel-tap requirement and prevent a general filtering or cross-domain claim; they do not prove that per-channel taps are unnecessary. Frozen current-comparator studies add a positive contrast between an AlphaFuse-style package and a zero-initialized upstream-class SASRec-ID control, plus a negative WEARec-versus-existing-reference contrast, under the shared evaluator; they strengthen comparator coverage without isolating a component or supplying independent confirmation.
3. **An auditable evaluation record.** Released protocols, artifacts, sidecars where available, comparator-regeneration code, and a strict rebuild preserve positive, null, deviated, and VOID outcomes under the same reporting rule (§8). The apparatus certifies reconstruction and protocol history; it does not strengthen the estimand.

TAPE, late fusion, sparse-warm redistribution, titrations, probe screens, and earlier Beauty results are supporting studies. All borrowed architectures and training recipes are attributed in §2.

## 2. Related Work and Attribution

We summarize prior work that our experiments directly build on. A complete attribution table for every component used in our experiments appears at the end of this section.

**SASRec** (Kang & McAuley, 2018) is the base Transformer sequential recommender we re-implement. SASRec models a user's history with a causal-masked Transformer encoder and scores the next item via dot product with a learned item-embedding table.

**BERT4Rec** (Sun et al., 2019) adapts BERT-style bidirectional masked-item modeling for sequential recommendation. We implement BERT4Rec as one of our 20 ablation baselines on Beauty_and_PC.

**SBERT / MiniLM** (Reimers & Gurevych, 2019; Wang et al., 2020) provide pre-trained sentence embeddings. We use `sentence-transformers/all-MiniLM-L6-v2` (384-d) as the default frozen item-text encoder (checkpoint: the `sentence-transformers/all-MiniLM-L6-v2` model card — the checkpoint carries its own contrastive fine-tuning and lives in a mutable repository, so we pin the realized embeddings by the SHA-256 text-cache hashes in `RELEASE_MANIFEST.json`).

**UniSRec** (Hou et al., 2022) is an early, widely-adopted text-based sequential recommender that uses a pre-trained language model to embed item text and learns a parametric adaptor to project these embeddings into the sequential model's hidden space; **ZESRec** (Ding et al., 2021) precedes it in representing items from natural-language descriptions with a pre-trained encoder for zero-shot sequential recommendation, and **RecFormer** (Li et al., 2023) subsequently studies language representations for sequential recommendation including low-resource and cold-start evaluation — we make no priority claim in this line. The SASRec-with-frozen-text-encoder pattern we use is a strict simplification of UniSRec.

**BLaIR** (Hou et al., 2024) is a RoBERTa-base model continually pretrained on 10% of (item-metadata, review) pairs from Amazon Reviews 2023. We use `hyp1231/blair-roberta-base` (768-d) as an alternative frozen item-text encoder. Hou et al. also publish a reference implementation, **SASRecText**, that pairs SASRec with BLaIR via a 2-layer MLP adaptor `[768, 300, 64]` with Dropout(0.2) + ReLU; we adopt this adaptor design verbatim (see Supplement S.1).

**TIGER** (Rajput et al., 2023) reformulates sequential recommendation as autoregressive generation over discrete semantic IDs produced by a residual-quantized variational autoencoder over item-text embeddings. TIGER reports strong results on Amazon Reviews 5-core benchmarks.

**LIGER** (Yang et al., 2024) extends TIGER with a dense-retrieval refinement step and reports further gains.

**Amazon Reviews 2023** (Hou et al., 2024) is the source dataset for the Amazon experiments. Our **iterative user-and-item 5-core leave-last-out** protocol (§3) shares chronological leave-out structure with TIGER and LIGER. LIGER states user-and-item filtering; the TIGER paper states user filtering, but we do not infer the exact geometry of its released preprocessing from that sentence. Both use Amazon Reviews 2014, whereas our study uses AR2023. Hou et al.'s `seq_rec_results/` reference implementation instead uses the `0core_timestamp_w_his_*` HuggingFace subset.

**Evaluation practice and reproducibility in recommender systems.** A supporting contribution responds to a documented evaluation-trust problem in this field. Ferrari Dacrema et al. (2019) examined 18 recent neural recommenders and could reproduce only 7 with reasonable effort, 6 of which were often outperformed by comparably simple heuristic baselines; the extended journal analysis (Ferrari Dacrema et al., 2021) corroborates the pattern in greater depth and attributes it in part to the choice and optimization of the baselines used for comparison. Sun et al. (2020) respond at the community level with standardized benchmarking for reproducible evaluation and fair comparison. These works diagnose the problem and propose field-level remedies; what this paper adds is complementary and *per-paper*: the executable, artifact-gated discipline detailed in §1 — pre-declaration, a fail-closed recompute gate, comparator regeneration, and symmetric self-VOIDing adjudication — which certifies that printed numbers are what the released artifacts recompute and strengthens no empirical claim.

### 2.1 Attribution table

| Component | Source | Where in our work |
|---|---|---|
| SASRec architecture | Kang & McAuley, 2018 | base `SASRecSBERT` model |
| BERT4Rec | Sun et al., 2019 | one of 20 ablation baselines |
| MiniLM `all-MiniLM-L6-v2` (384-d) | Reimers & Gurevych, 2019; Wang et al., 2020 | default frozen item-text encoder |
| BLaIR `blair-roberta-base` (768-d) | Hou et al., 2024 (arXiv:2403.03952) | alternative frozen item-text encoder |
| 2-layer MLP adaptor `[768, 300, 64]` Dropout+ReLU | Hou et al., 2024 (SASRecText, in `external/AmazonReviews2023/seq_rec_results/`) | `--mlp-adaptor` flag |
| Rich-text content concatenation (title + categories + store name) | derived from Hou et al., 2024 preprocessing | `encode_richtext_5core.py` |
| Amazon Reviews 2023 dataset | Hou et al., 2024 | all benchmarks |
| TIGER / LIGER | Rajput et al., 2023 / Yang et al., 2024 | published comparator numbers |

### 2.2 Our additions to the above prior art

We do not claim a wholly new recommender architecture. Our two architectural additions (§1) are deliberately small: a causal FIR adaptation of prior frequency-filter ideas and a soft text-prototype additive term. Beyond the three headline contributions (§1), the study also provides these supporting engineering and empirical artifacts:

- An **open-source iterative user-and-item 5-core preprocessing pipeline** (`preprocess_5core_standard.py`). Its leave-out chronology resembles TIGER and LIGER and its two-sided filtering resembles LIGER, but it does not claim exact TIGER/LIGER protocol identity and differs from Hou et al.'s 0-core repository path.
- A **memory-efficient chunked-full-softmax loss** that enables proper full-catalog cross-entropy training at 207k-item catalogs on a single 16 GB GPU.
- An **eval optimization** (caching `all_item_features()` once per `evaluate()` call) that gives ~10× speedup at d=64 with the MLP adaptor.
- A **cross-pipeline transfer study**: empirically testing which published architectural choices help on the 5-core protocol.
- **Negative-result documentation** for 18 of 20 tested variants on Beauty_and_Personal_Care 5-core.
- The **competitive Video_Games 5-core result** on the HSTU-style pure-PyTorch stack (6-seed NDCG@10 = **0.0673 ± 0.0003**, +17.5% over published SASRec 0.0573), shown to be architectural (ID-only ≈0.0656), with no SOTA claim. *(The earlier v1-era SASRec-SBERT number 0.05509 ± 0.00035 has been retired from Table 1a: its raw per-seed artifacts predate the artifact manifest and cannot be recomputed, so it survives only as a RETIRED provenance row in the manifest, not as a paper claim.)*
- The two added components — the **strictly causal FIR temporal filter** (positive internal identity contrasts on three outcome-visible categories plus a positive outcome-known Software robustness contrast; learned FIR separates from one equal-parameter compound non-temporal placebo in MI, while the shared causal control prevents per-channel-tap attribution; §5.2) and **TAPE** — plus the **MI frequency-5 tail case** (§5.3) and its **interaction-thinning titration** level-contrast result (§5.4). The novelty boundary for each is stated explicitly in Table 0 (§2.3).

### 2.3 Claim boundary

Table 0 separates prior work from the paper's actual claim boundary. Frequency filtering (including FEARec, FreqRec, WEARec, and WPGRec), causal convolution (including Caser and NextItNet), residual identity initialization, HSTU, frozen text encoders, and label smoothing all predate this work (Du et al., 2023; He et al., 2026; Xu et al., 2026; Liu et al., 2026; Tang & Wang, 2018; Yuan et al., 2019). Our claim is limited to the gradient-active left-causal depthwise-FIR residual used before an HSTU-style stack under an all-position objective, together with its outcome-known internal evaluation. The historical zero-gated realization is singular at initialization and remains package-attributed. In the nonsingular studies, learned FIR separates from one equal-parameter current-position-only DCT/GELU placebo, but that compound contrast does not isolate temporal access; a shared causal filter also prevents attribution to learned per-channel taps (§3, §5.2).

<!-- BEGIN GENERATED TABLE 0: build_table0_claim_ledger.py -->

**Table 0: Claim boundary — reused basis, specific change, and supported evidence.**

| Component and reused basis | Specific change | Evidence and boundary |
|---|---|---|
| **HSTU base** — Zhai et al. (2024): pointwise `silu(QKᵀ + rab) V`, per-block normalization, and relative biases | Pure-PyTorch implementation; two spurious normalizations removed | Core-block parity only at a mirrored aligned configuration; no pinned end-to-end reproduction (§3.2, §5.6, §6.3). Prior-work implementation. |
| **BLaIR/SBERT text** — Hou et al. (2024), Reimers & Gurevych (2019), Wang et al. (2020) | Frozen off-the-shelf text features and Hou et al.'s MLP adaptor; no method change | Table 1a encoder comparison. Prior work. |
| **AlphaFuse-style text+ID package** — Hu et al. (2025) | Official upstream AlphaFuse/SASRec classes under one frozen configuration, with MiniLM-384 substituted for the published text vectors and the paper's complete-history-masked evaluator | AlphaFuse-style NDCG@10 0.048273 [0.048129,0.048416] versus zero-initialized upstream-class SASRec-ID control 0.039024; delta +0.009249 [+0.008329,+0.010169], but -0.019065 versus the existing 0.067337 reference. Countable outcome-known same-investigator whole-package evidence; not a published-table reproduction, null-space-fusion isolation, equal architecture/capacity/tuning, independent confirmation, or SOTA. |
| **Label smoothing/time bias** — Szegedy et al. (2016); TiSASRec; HSTU (Zhai et al., 2024) | Integrated with this backbone and full-catalog chunked softmax | +0.0013 and +0.0027 single flags (Table 1). Prior work. |
| **Sequence/frequency and linear-time operators** — FMLP-Rec, BSARec, FreqRec, WEARec, TimeWeaver, TV-Rec, HyenaRec, ConvRec, and Mamba4Rec; causal convolutions include Caser, NextItNet, C3SASR, and AdaMCT | The official WEARec model/training code is evaluated under our split, complete-history mask, full-catalog evaluator, cutoff, and tie rule; the others are not inserted as-is | WEARec official-code/equal-evaluation mean 0.059184 [0.058674,0.059693] versus reference 0.067337; `WEAREC-BELOW-EXISTING-REFERENCE`. Outcome-known same-investigator feasibility baseline, not equal architecture/loss/schedule/tuning, independent confirmation, or SOTA. Filtering, frequency modeling, and causal convolution are prior art. |
| **Causal FIR adaptation (ours)** — the filtering/convolution line above | Minimal leak-free, gradient-active, identity-initialized left-causal depthwise residual before an HSTU-style all-position stack | Outcome-known FIR−identity estimates: MI +0.002265, IS +0.002110, CDs +0.006150. Software robustness: +0.005062 [+0.004591,+0.005533]. Learned beats the equal-parameter current-only placebo by +0.001941 but does not separate from shared FIR (-0.000081 [-0.000337,+0.000175]). Prospective MovieLens: learned minus identity +0.000000 [-0.000074,+0.000075] and learned minus pointwise +0.000035 [-0.000057,+0.000127]; neither gate passed, so parsimonious-arm NI is conditional only. **Incremental modular contribution; no general FIR benefit or independent confirmation.** |
| **TAPE (ours)** — TIGER, VQ-Rec, ProtoMF; prototype/semantic-ID motivation | Frozen soft assignments gate a zero-initialized additive prototype table | +0.0009 single flag; +0.0004 four-seed check. Supporting ablation (§5.1). |
| **Tail/thinning analysis (ours)** — standard popularity strata, MELT, DropoutNet, CLCRec | Per-dataset text−ID tail contrast and matched-R1 interaction/user thinning | MI +0.000420 (outcome-visible); VG null; cross-dataset p=.13; user-mode p=.058. Secondary empirical boundary (§5.3–§5.4). |
<!-- END GENERATED TABLE 0 -->

**Closest filtering and linear-time operator systems.** FMLP-Rec and BSARec establish learnable sequence filtering and frequency-rescaled attention; BSARec's Theorem 1 concerns repeatedly applied softmax attention, not our HSTU-style operator. C3SASR and AdaMCT already combine causal/local convolutions with attention. TimeWeaver combines a reparameterized large-kernel convolution with time-aware augmentation and dual temporal/EMA streams (Liu et al., 2025). TV-Rec replaces fixed kernels and self-attention with position-specific time-variant filters (Shin et al., 2025); HyenaRec parameterizes long convolution kernels with Legendre polynomials and short-term gates (Liu et al., 2026); ConvRec uses hierarchical strided convolution for attribute-aware sequence aggregation (Elsayed et al., 2026); and Mamba4Rec applies a selective state-space operator with a local convolutional path (Liu et al., 2024). Current frequency systems are broader still: FreqRec (He et al., 2026) couples inter- and intra-session spectral paths with a frequency-consistency loss, while WEARec (Xu et al., 2026) uses sequence-adaptive frequency filters and wavelet enhancement. These systems differ in backbone, attributes, sequence length, candidate protocol, and efficiency target, so their reported numbers are not inserted as if protocol-matched. Their existence rules out broad filtering, convolution, temporal-specificity, or efficiency novelty. Our distinction is only the small gradient-active, identity-initialized **left-causal depthwise FIR residual** placed before one HSTU-style all-position, full-catalog stack, together with the bounded evaluation reported here.

**Closest text/ID systems.** AlphaFuse (Hu et al., 2025) learns ID embeddings in the null space of language embeddings and is the closest frozen-text-plus-ID comparator. The first AlphaFuse-style MiniLM port on our Video_Games split used mismatched seen-item masking; its repaired V2 factorial remained outcome-visible, capacity/initialization-confounded, incompletely masked for long histories, and non-rank-reconstructive. Its governed adjudicator therefore permanently marks V2 `NONCOUNTABLE` and `manuscript_allowed=false`. The separately frozen V3 comparison used eight fresh seeds per arm, complete-history-masked validation selection, and sealed TEST evaluation. Its adjudicator returned `EEV3-REPORTABLE-OUTCOME-KNOWN`: the AlphaFuse-style MiniLM package scored **0.048273 [0.048129, 0.048416]** versus **0.039024 [0.038106, 0.039941]** for a zero-initialized upstream-class SASRec-ID control, a descriptive independent-arm Welch difference of **+0.009249 [+0.008329, +0.010169]**, but remained **−0.019065 [−0.019347, −0.018783]** below our existing 0.067337 reference. This counts as current-comparator evidence under shared data/evaluation and a frozen training configuration, not a comparison with the parser-default `Normal(0,1)` initialization. That parser setting is not a universal upstream recipe: official recipes may override initialization by dataset. This is also not a reproduction of AlphaFuse's published text encoder, an isolation of null-space fusion, equal architecture/capacity/tuning, independent confirmation, or SOTA. DWSRec, SIDSRec, LLM-ESR, LLM2Rec, and FAERec further show that whitening, channel separation, and adaptive semantic/ID fusion are active prior lines. Our own text findings remain construction-specific; an item-text permutation control remains open.

Two concurrent 2026 preprints reinforce that this is an active modular-content line rather than a priority claim: SISA-Rec injects frozen BERT semantics through gated input fusion and a semantic attention term (Abbasi et al., 2026), while ASER adds review-distilled sensory representations to four existing sequential backbones (Yoon et al., 2026). Their Amazon Reviews 2014 protocols and representation interventions are not numerically interchangeable with our AR2023 FIR study; we cite them for mechanism-family coverage only.

**Tail and reproducibility boundary.** SimRec and LLM-ESR already target text-supported sparse/long-tail recommendation, so our tail contribution is a measured, dataset-specific frequency-5 case rather than a method claim. LLM2Rec also uses Amazon Reviews 2023 with 5-core leave-one-out/full ranking, but its length-10 histories and resulting item universe prevent direct numeric comparison. Elliot, DaisyRec 2.0, accountability workflows, and reproduction audits predate our artifact apparatus; we claim only this paper's combination of per-cell recomputation, provenance tripwires, and symmetric self-VOIDing, not evaluation infrastructure generally.

## 3. Method

### 3.1 Preprocessing pipeline

We preprocess Amazon Reviews 2023 (Hou et al., 2024) into 5-core leave-last-out splits. For each category we:
1. Load raw user-item review interactions from the `raw_review_<category>` HuggingFace subset.
2. Apply a 5-core filter iteratively until no user or item has fewer than 5 interactions.
3. Sort each user's interactions chronologically.
4. Hold out the last interaction as test, the second-to-last as validation, the rest as training.
5. Encode item metadata (`meta_<category>.jsonl`) with the chosen frozen text encoder.

This protocol shares chronological leave-last-out structure with TIGER (Rajput et al., 2023) and LIGER (Yang et al., 2024), but it is not identical to either: our iterative filtering applies to users and items, matching LIGER's stated k-core dimension. The TIGER paper states user filtering, but the exact geometry of its released preprocessing is not established here; both comparator papers use Amazon Reviews 2014 rather than AR2023. Hou et al. (2024)'s AR2023 reference repo (`external/AmazonReviews2023/seq_rec_results/`) uses the `0core_timestamp_w_his_*` HuggingFace subset. These pipelines produce different catalogs and cannot support direct numerical comparisons.

**Estimand and construct boundary.** Each review event is treated as an implicit positive interaction regardless of its 1–5-star rating or verified-purchase flag. The estimand is therefore *ranking the next recorded review event among the fixed post-filter catalog*, not predicting preference, satisfaction, purchase, or deployment engagement. Five-core eligibility, item indices, and the candidate catalog are computed from complete histories before splitting, so future events can affect inclusion even though their identities are not used as training targets. Rating-threshold, verified-purchase, genuine implicit-event, and global-time/query-time-catalog sensitivities have not been run; conclusions do not extend to those constructs or deployment regimes.

**Pre-core deduplication (disclosed 2026-07-19).** Before k-core filtering, duplicate `(user, item)` interactions are collapsed to a single event, keeping the **earliest** timestamped occurrence (first-exposure convention). This step is material and was previously undocumented in the paper: it removes 41,888 of 3,017,439 raw rows on Musical_Instruments (1.39%), 69,115 of 4,624,615 on Video_Games (1.49%), 320,078 of 23,911,390 on Beauty_and_PC (1.34%), and 156,363 of 12,845,712 on Office_Products (1.22%); the FIR-breadth categories were preprocessed from AR2023 rating-only exports whose (user, item) pairs are already unique (0 rows removed on Industrial_and_Scientific and CDs_and_Vinyl). Deduplication can change k-core membership, sequence order, and held-out targets; sensitivity to a keep-latest rule is untested (a disclosed limitation). (The MI/Office counts are from the retained preprocessing logs; the VG/Beauty logs were not retained, and their counts were regenerated 2026-07-19 from the raw dumps with the released deterministic script.)

**Timestamp-tie policies (disclosed 2026-07-19; two distinct deterministic rules).** Two tie-breaking rules operate at different stages and were previously undocumented. (i) Preprocessing stable-sorts each user's interactions by timestamp only, so for equal-timestamp events the raw-file order decides both which duplicate survives deduplication and which event lands on a leave-two-out split boundary. (ii) The trainer later re-sorts each user's train sequence by `(timestamp, item_index)`, so within-train equal-timestamp order is decided by reindexed item ID. Both rules are deterministic given the released raw dumps and code. Measured scale (2026-07-19, from the released splits): on Musical_Instruments, 3 of 57,439 users (0.01%) have test-target timestamp equal to the validation-target timestamp, 3 have validation equal to the last train timestamp, and 12 (user, timestamp) groups cover 24 of 511,836 rows; on Video_Games the counts are 4 and 8 of 94,762 users and 61 groups covering 122 of 814,586 rows (0.01%). At this scale the tie policies cannot materially affect any reported number; we nevertheless document them as part of the exact preprocessing contract.

### 3.2 Model architecture

**Shared item-feature construction (both encoder families).** For each item `i`:
- A learned per-item embedding `e_i ∈ R^d` (initialized N(0, 0.02), padding-aware).
- A frozen text embedding `s_i ∈ R^k` from MiniLM (k=384) or BLaIR (k=768).
- A learnable projection `Φ : R^k → R^d`.

The item feature passed into the encoder is `f_i = e_i + Φ(s_i)`. Sequences are right-padded with a dedicated pad token and processed with a causal-only attention mask (no key-padding mask — see §3.4). The output logits for position `t` are `h_t · all_items.T` where `all_items` is the (n_items, d) item-features table.

**Headline encoder — HSTU-style (every §5 result).** All headline experiments use the **HSTU-style pure-PyTorch pointwise-attention encoder**, described in full in §3.7: pointwise `silu(QKᵀ + rab) V` aggregation with the published per-block normalization — no softmax, no 1/√d scaling — with the core block verified exactly (max abs diff 0.0) against the reference research implementation at a mirrored, aligned, dropout-free configuration (`HSTU_PARITY_REPORT.md` discloses the alignment: identity affine norms, zeroed extra `uvqk` bias, ε 1e-6, eval mode; the trained configuration is a strict-superset HSTU-style variant — §6.3). Configuration, stated here and in §4.4: **4 layers, 2 heads, d = 64, dropout 0.5**.

**Baseline encoder — SASRec-SBERT (protocol parity and the superseded Supplement S.1 scans only).** The SASRec-family baseline follows Kang & McAuley (2018): a 2-layer pre-norm Transformer encoder (d=64, n_heads=2, FFN dim=4d, GELU activation) followed by a final LayerNorm, using the same item-feature construction. **No headline number uses this encoder**; it appears as the per-category parity/floor baseline and in the superseded Beauty scan (Supplement S.1).

### 3.3 Choice of projection Φ

Following our cross-pipeline transfer study (Supplement S.1), we compare two designs for `Φ`:
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

Memory-efficient exact cross-entropy has published precedent (Cut Cross-Entropy, ICLR 2025, computes exact CE without materializing the full logit matrix); our chunked variant is independent implementation engineering in the same spirit, claimed only as engineering. 

### 3.6 Evaluation protocol

We score each user against the **full catalog** of 207k items (Beauty_and_PC) or 25k items (Video_Games). For the held-out test item, we compute the rank under dot-product scoring (after masking train+val items the user has already seen) and report NDCG@10, HR@10, MRR. We use the standard SASRec test-time convention of including the validation item in the input sequence (Kang & McAuley, 2018).

For our default 16 GB GPU, the optimized evaluation caches the (n_items, d) item-features table once per `evaluate()` call rather than recomputing it per batch — this is critical with the MLP adaptor, which would otherwise recompute the 207k-item × 768 → 300 → 64 MLP forward 1,400+ times per evaluation.

### 3.7 Added components (deliberately small adaptations)

Our two architectural additions (the novelty boundary is stated in §2.3) are deliberately simple, default-OFF, and zero-initialized so that each is a *bit-identical no-op at initialization* and reduces the design to a single controlled lever. Both sit on top of the HSTU-style encoder of §3.2 (Zhai et al., 2024) — the pointwise `silu(QKᵀ + rab) V` interaction with the published per-block normalization — for which we diagnosed and removed two spurious normalizations (a 1/√d score scaling and a 1/(i+1) row averaging) in our initial reimplementation that had collapsed HSTU's pointwise attention into weak mean-pooling. Core-block parity (max abs diff 0.0) and the hardware-incompatibility of the official kernel stack are as stated in §3.2 and §7 (`HSTU_PARITY_REPORT.md`).

**(a) Text-Anchored Prototype Embeddings (TAPE).** TAPE is a simple soft text-prototype additive capacity term inspired by semantic-ID and prototype methods (TIGER, VQ-Rec, ProtoMF); it provides a small but not headline gain (§5.1). Let `t_i ∈ ℝ^{d_text}` be item *i*'s frozen text embedding (MiniLM or BLaIR). We k-means the L2-normalized text embeddings into *K* centroids `{c_1,…,c_K}` once, offline, and form a **frozen soft assignment** `A_i = softmax(⟨t_i, c⟩ / τ) ∈ Δ^{K}` (τ = 0.05). We add a **learnable prototype table** `P ∈ ℝ^{K×d}` (zero-initialized) to each item's feature:

  `e_i = id_i + Φ(t_i) + A_i P`,

where `id_i` is the learned per-item embedding and `Φ` the learned projection of the frozen text embeddings. Items in the same semantic neighborhood share the learnable capacity `A_i P` — the shared-structure benefit of TIGER-style semantic IDs (Rajput et al., 2023) without discrete codes or an autoregressive decoder. Because `A` is frozen and `P` is zero-init, TAPE is an exact no-op at initialization and recovers the baseline. TAPE is adjacent to TIGER (discrete RQ-VAE IDs), VQ-Rec (PQ codes), and ProtoMF (prototype matrix factorization for explainability); it differs only in realization — a frozen text-derived soft assignment gating a learnable prototype table inside a sequential recommender — and we present it as a small adaptation of these prior ideas tested as a secondary ablation, not as a headline contribution. Default K = 512.

**(b) Canonical causal FIR temporal filter (the proposed module).** BSARec (Shin et al., 2024, Theorem 1) proves a low-pass limit for repeatedly applied softmax self-attention. That result does not cover the non-softmax HSTU-style pointwise operator used here; it supplies motivation only. We test whether adding an explicit local left-causal residual benefits this backbone. Learned FIR separates from one equal-parameter current-position-only DCT/GELU residual, a compound contrast that does not isolate temporal access, while a competitive shared causal filter prevents attribution to per-channel taps (§5.1–§5.2). The proposed module is a single **per-channel learnable FIR residual** on the sequence embeddings `x ∈ ℝ^{B×L×d}`, in a **nonsingular, gradient-active** parameterization:

  `x ← x + DWConv_Δ(pad_left(x, K−1))`,  with `Δ` initialized to `0`,

implemented as depthwise `Conv1d(d, d, K, groups=d, bias=False)`. With `Δ=0` and left-only padding, it is an **exact identity at initialization**, is gradient-active on the first update, and makes output position *t* depend only on inputs ≤*t*; the all-position objective therefore receives no future-label leakage. Primary taps used backbone weight decay. The registered E-A A2−A1 Welch sensitivity is +0.000010 [−0.000339, +0.000360], p=.95; this is neither equivalence nor a pathway test (§5.2).

FMLP-Rec and BSARec use bidirectional sequence filters in their original formulations, which cannot be inserted before our per-position predictions without future mixing. FreqRec and WEARec further establish that learned spectral paths, adaptive filters, and wavelet enhancement predate this paper. Our novelty claim is only the minimal gradient-active, identity-initialized **left-causal depthwise FIR residual** before an HSTU-style stack under full-catalog all-position LLOO—not filtering, causal convolution, or frequency modeling generally.

**Legacy realization.** Historical Video_Games and breadth runs used `x ← x + g ⊙ (y−x)` with a delta kernel and `g=0`. That start is singular: task gradients initially vanish and Adam weight decay perturbs the tap. Those contrasts therefore identify a FIR-plus-initialization/optimizer package. The canonical K=16 form was tested on three already outcome-visible category/split settings and one subsequently frozen Software attempt. Positive estimates support the tested FIR arms over identity only in those Amazon settings; the Software attempt remains outcome-known same-team robustness. On Musical_Instruments, a later equal-parameter pointwise placebo discriminates learned FIR from that compound current-only residual without isolating temporal access, and the shared causal control prevents learned-per-channel-tap attribution. A prospectively frozen MovieLens 1M test then returned no learned-FIR replication versus identity or pointwise, blocking a general or cross-domain benefit claim (§5.2). Historical kernels span K∈{4,8,16,50}; the canonical primary configuration fixes K=16.

Both components are leak-free by construction and add negligible parameters (TAPE: K×d ≈ 33k; filter: K×d ≈ 0.5–3k). Two further regularizers we use are *not* claimed novel: **label smoothing** (Szegedy et al., 2016) on the full-softmax CE target, and the standard time / text-similarity / relative-position attention biases (TiSASRec; HSTU; Shaw et al., 2018), each cited at the point of use.

## 4. Experiments

### 4.1 Datasets

The primary development and comparator studies use AR2023 5-core categories under the
full-catalog LLOO protocol (§3.6). A separate prospective robustness/efficiency study uses
MovieLens 1M under a frozen global-time split. AR2023 counts below are total 5-core
interactions (train = total − 2 × users); the MovieLens row reports its filtered primary
view and training-observed catalog:

| Category | Role in this paper | Users | Items | Interactions (total) |
|---|---|---|---|---|
| **Video_Games** | descriptive system context (§5.1); tail-pattern null (equivalence claim retracted §5.3) | 94,762 | 25,612 | 814,586 |
| **Musical_Instruments** | outcome-known FIR internal study + pre-declared per-category point-estimate comparison (§5.2) | 57,439 | 24,587 | 511,836 |
| **Office_Products** | V1 prereg **VOID** (descriptive; Appendix A.0); **redesigned V3 prereg PASSED** (§5.2; `OFFICE_V3_RESULTS.md`) | 223,308 | 77,551 | 1,800,878 |
| **Beauty_and_Personal_Care** | tail-pattern exploratory 3-seed estimate (§5.3); superseded cross-pipeline scan (Supplement S.1) | 729,576 | 207,649 | 6,624,441 |
| Industrial_and_Scientific | **pre-declared FIR-breadth: artifact-PASS** (frozen rule fired; paired premise withdrawn; post-hoc independent-arm estimate — §5.2; `FIR_BREADTH_RESULTS.md`) | 50,985 | 25,848 | 412,947 |
| CDs_and_Vinyl | **pre-declared FIR-breadth: artifact-PASS** (frozen rule fired; paired premise withdrawn; post-hoc independent-arm estimate — §5.2; `FIR_BREADTH_RESULTS.md`) | 123,876 | 89,370 | 1,552,764 |
| MovieLens 1M, rating≥4 | **prospectively frozen non-Amazon FIR replication/efficiency study; negative verdict** (§5.2; Harper & Konstan, 2015) | 1,033 | 2,359 training-observed | 575,281 filtered events; 135,131 train rows |

Video_Games/Musical_Instruments/Office_Products match the HSTU-BLaIR comparator pipeline's own
statistics exactly on users/items (interactions within ±1; §5.2). The Beauty_and_PC catalog is
8× larger than Video_Games, with median user history of only 5 interactions — a harder
benchmark. Every pre-declared campaign that has completed is mechanically adjudicated (verdicts at the relevant result blocks: §5.2, §5.7, §5.8, and Appendix A.0).

The MovieLens primary cohort is explicitly conditional rather than population-representative: after the rating and global-time filters, 1,102 candidate users enter the fixed-point training-catalog filter and 1,033 remain. The all-ratings branch is a construct sensitivity, not a second independent dataset.

![MovieLens cohort flow (unnumbered): the official 1,000,209-rating, 6,040-user source branches into the primary rating-at-least-4 view and the all-ratings sensitivity. Each applies a global 90% time boundary, requires at least six pre-cutoff and one post-cutoff events, and then iterates a user/training-catalog filter to a fixed point. The primary branch moves from 575,281 filtered events to 1,102 candidate users and 1,033 retained users with 2,359 training-observed items, producing 135,131 TRAIN, 1,033 VALID, and 1,033 TEST rows. The all-ratings branch retains 1,129 users and 3,015 items, producing 252,332 TRAIN and 1,129 rows in each held-out split. Exact public aggregates are in `figures/fig_movielens_cohort_flow_data.csv`.](figures/fig_movielens_cohort_flow.png)

*MovieLens cohort flow (unnumbered). The primary estimand is conditional on eligible pre-cutoff history and a training-observed item catalog; it is not a random sample of all users or movies.*

### 4.2 Baselines

- Popularity (trivial floor)
- SASRec with sampled-512 softmax (our "original" baseline)
- SASRec with chunked-full-softmax (improved baseline)
- BERT4Rec (Sun et al., 2019)
- Published comparators: TIGER (Rajput et al., 2023), BLaIR (Hou et al., 2024), LIGER (Yang et al., 2024)

**Comparator-design matrix.** This matrix separates the dimensions that are actually aligned from those that remain unmatched; a shared evaluator is not treated as an equal-model experiment.

| Comparator use | Aligned dimensions | Known unmatched dimensions | Supported scope |
|---|---|---|---|
| FIR vs identity, Amazon canonical campaigns | same data, evaluator, backbone, schedule, and exact per-seed backbone initialization | +1,024 FIR parameters; outcome-known categories; TEST access differs by campaign | internal modular contrast on the named settings |
| Learned FIR vs pointwise placebo, MI | same data/evaluator/backbone/init and exactly 1,024 trainable component parameters | temporal history versus a compound DCT/GELU/current-position operator; outcome-known | learned FIR versus this tested placebo, not temporal access alone |
| Learned FIR vs shared causal filter, MI | same data/evaluator/backbone/init and causal-history access | 1,024 per-channel versus 16 shared parameters; outcome-known | per-channel-tap necessity not established |
| MovieLens six-arm study | same frozen split/evaluator/backbone/init, schedule, seed blocks, and sealed endpoint timing | parameter counts and filter parameterizations differ; same investigator; record-level endpoints private | negative transfer test; parsimonious-arm NI is conditional only |
| Official WEARec under our evaluator | official model/training code; same split, mask, catalog, cutoff, and tie rule | architecture, loss, schedule, capacity, and tuning budget unequal; private endpoints | equal-evaluation feasibility baseline only |
| AlphaFuse-style package | official upstream classes; one frozen configuration; same split/evaluator | MiniLM substitutes for published vectors; architecture, capacity, initialization, and tuning history unequal | whole-package comparator coverage only |
| Published/local HSTU-BLaIR reference | users/items match and interactions differ by one; local regeneration uses the reference code | single-run/unpaired reference; pinned environment unavailable; no equal tuning budget | per-category point threshold and environment-caveated context |

### 4.3 Experimental design (headline runs)

All headline results (§5.1–§5.4) use the HSTU-style pure-PyTorch encoder (§3.2) under the fixed AR2023 5-core full-catalog LLOO protocol (§3.6). Each configuration is trained for **40 epochs** (the §5.1 Video_Games headline; the pre-declared-file MI/Office V3/FIR-breadth campaigns train 20 epochs per their frozen configurations) at batch size 256 (d_model 64, 4 layers, 2 heads, dropout 0.5) with the memory-efficient chunked-full-softmax loss (§3.5, item chunk 32,768) and a warmup-cosine learning-rate schedule. On top of the bias stack (TAPE-512 + time bias + text-similarity bias + pos-rab) the winning configuration adds label smoothing (ε=0.2) and the causal FIR filter (K=8). We run **6 seeds (20260608–20260613)** for the full-model headline and **5 seeds (20260608–20260612)** for every per-component ablation rung, reporting mean ± sample-std; the reported test number is always selected by best validation NDCG@10 (best-by-val), never by test. **Fixed-split inference scope (stated prominently, 2026-07-20):** the training seed is the only randomized unit; every interval in this paper quantifies optimization variability on one fixed public split per category — nothing here estimates user-resampling, split-choice, category-sampling, or cross-dataset uncertainty, and all claims are scoped to these exact datasets and splits. Evaluation is full-catalog (n_eval = 94,762 on Video_Games), with all train+val items masked (§3.6).

The tail analysis (§5.3–§5.4) rests on two arm comparisons, each toggling one named configuration flag on the same split and seed numbers (bundled interventions: the arms are not initialization-paired and optimizer paths differ) and reporting `by_popularity` NDCG@10 / HR@10 on leak-free train-frequency terciles (terciles frozen at full density):
- **text vs ID-only:** the full text stack against an ID-only ablation (`--no-sbert`, no prototypes, no text-similarity bias).
- **density / connectivity titration (§5.4):** training-only sub-sampling that thins either interactions (interaction-mode) or whole users (user-mode) to match a sparser reference category's resource levels, with the evaluation set held fixed.

A separate **20-variant cross-pipeline transfer scan on Beauty_and_PC** — supporting reproducibility material, not part of the headline spine — is reported in Supplement S.1. The MovieLens study instead used six exact matched-initialization arms over eight pre-specified seed blocks: identity, channel-shared K=16, eight-group K=16, rank≤8 tangent-factorized K=16, per-channel K=16, and an equal-parameter current-position-only placebo. Acquisition had already read the official ratings file, constructed and hash-bound the TEST split, and used target-in-training-catalog eligibility to define the primary cohort. During fitting and validation selection, the trainers consumed TRAIN+VALID only and emitted no TEST scores; after all 96 training runs completed, each selected checkpoint received one sealed TEST evaluation. The primary estimand was NDCG@10 on rating≥4 events after a global 90% time boundary; all ratings, user/item cluster bootstraps, and resource readings were frozen sensitivities. The three-candidate noninferiority family used margin 0.000500 and Holm-adjusted one-sided tests.

### 4.4 Training details and hardware

Headline runs use Adam (lr 1e-3, weight decay 1e-5) with gradient clipping (norm 5.0) under the 40-epoch warmup-cosine schedule above. Hardware: a single NVIDIA RTX 5060 Ti (16 GB, Blackwell sm_120). Video_Games training takes ~10 min/seed; Beauty_and_PC ~1.5–2 hr/seed with the chunked-full-softmax loss. (The Supplement S.1 Beauty scan used a shorter 15–20-epoch budget and seeds 42/43; those details are local to that supporting study.)

## 5. Results

**AlphaFuse pipeline boundary.** Because the upstream offline preprocessing code was unavailable, both official classes consumed training rows produced by our frozen per-prefix adapter. This is upstream-class/training-code transfer, not reproduction of the upstream data pipeline.

**Statistical reporting conventions.** Unless stated otherwise: the sample unit is the training seed; means are reported ± sample standard deviation over seeds; confidence intervals are two-sided 95% Student-t intervals with df = n−1 (the six-seed Video_Games headline is n = 6; controlled ablation rungs are generally n = 5; every other exception is named at the point of use); comparisons between our own arms use same-numbered seeds and are analyzed as independent arms (Welch/Satterthwaite) unless exact matched backbone initialization and a paired analysis are explicitly named, as in canonical breadth, active controls, pointwise placebo, and prospective Software V3; comparisons against published numbers are point-estimate comparisons (the comparator is single-seed and unpaired); pooled tail hit-counts are reported as descriptive counts only — the same tail users recur under every seed and under both arms, so two-proportion z statistics over seed-summed pseudo-trials are invalid and are retracted (2026-07-19); the accompanying inference treats the five trained models per arm as the units (independent-arm Welch, §5.2/Appendix A.0); p-values are uncorrected unless a correction is named — cells labeled *confirmatory* in the artifact manifest are pre-declared prospective campaigns or their frozen-protocol locks — selection timing and protocol integrity, not seed count or external independence, are the criterion — while multi-seed post-hoc results improve precision without becoming confirmatory, and *exploratory* cells carry no confirmatory weight.


### 5.1 Video_Games — descriptive system context (not FIR inference; NOT SOTA)

Table 1 locates the historical **HSTU-style pure-PyTorch encoder** and component stack within the paper's system context. It is not the inferential basis for the modular FIR contribution: its ladder mixes n=1, five-seed, and six-seed arms, lacks one pre-declared contrast family, and contains separately summarized rather than initialization-paired arms. The FIR claim instead rests on the explicitly named matched-control and transfer studies in §5.2. Table 1a retains the traceable within-paper SASRec-family floor; Table 1b combines reported HSTU-BLaIR evidence, our SM120 compatibility port, an official-code WEARec equal-evaluation feasibility run, and the frozen AlphaFuse-style whole-package comparison.

**Table 1: Descriptive system-context component ladder — NDCG@10 on AR2023 Video_Games 5-core LLOO (full-catalog eval, n_eval = 94,762; 5 seeds = 20260608…20260612 unless noted; the full-model row is 6-seed 20260608…20260613; one flag added per row).**

| Configuration | NDCG@10 | seeds | Δ |
|---|---:|---:|---|
| HSTU-style encoder, plain | 0.0588 | 1 | — |
| + TAPE-512 (sub-additive text component) | 0.0597 | 1 | +0.0009 |
| + full bias stack (TAPE + time + text-sim + pos-rab) | 0.0637 ± 0.0003 | 5 | +0.0049 vs plain (+8.3%) |
| + label smoothing ε=0.2 (Szegedy 2016) | 0.0649 ± 0.0003 | 5 | +0.0012 descriptive mean contrast |
| **+ causal FIR filter K=8 (ours) → full model** | **0.0673 ± 0.0003** | **6** | **+0.0024 descriptive mean contrast** |
| *(single-arm)* FIR package arm (filter component; attribution open), no label smoothing | 0.0652 ± 0.0003 | 5 | +0.0015 vs the 0.0637 stack |
| *(single-arm)* ID-only (no SBERT / no text-sim / no prototypes) | ≈0.0656 ± 0.0002 | 5 | text adds only +0.0018 (+2.7%) overall |

Here and throughout Table 1, “±” denotes the sample standard deviation across the listed optimizer seeds, not a confidence interval. The Δ column contains arithmetic differences between separately summarized arms; those rows are not paired tests and “band non-overlap” is not used as an inferential rule.

The full model is **+17.5%** over the published SASRec point estimate (0.0573, Table 1b) on the same reported Video_Games dataset geometry, but published training/evaluation equivalence is not established — and **this difference is architectural, not text-driven**: the ID-only ablation already reaches ≈0.0656 (itself +14% over published SASRec), and the entire frozen-text stack (SBERT features + text-sim bias + prototypes) adds only **+0.00178 ± 0.00021 (5-seed, +2.7%)** overall. The two supported regularizers stack with a combined lift whose excess over the component sum is 33% — additivity and orthogonality were NOT tested (loss target vs. embedding spectrum): label smoothing alone +0.0012, causal filter alone +0.0015, combined +0.0036 over the bias stack. Per-component single-flag attribution on the HSTU-style implementation: the **time bias is the largest classical component (+0.0027)**, label smoothing +0.0013, causal filter +0.0015, while **text-similarity bias shows no observed benefit (±0.0001, removable candidate)** and **TAPE is sub-additive (+0.0009)**. *(The time-bias, text-sim, and TAPE single-flag figures here are the single-seed seed-20260608 DECOMP values, honestly flagged n=1 (reported inline here, not in a table). A 4-seed multi-seed cross-check — DECOMP5, seeds 20260609–12, HSTU-style base 0.0594 — confirms the ordering: time bias +0.0030 (largest classical component, ≥ the single-seed +0.0027), pos-rab +0.0012, TAPE +0.0004, text-sim −0.00005 (no benefit observed at tested power). The qualitative attribution is unchanged; the only number that materially moves is TAPE, whose multi-seed single-flag lift (+0.0004) is smaller still than the single-seed +0.0009 — further support for its demotion from a headline component.)* The causal filter's gain is robust across kernel lengths K∈{4,8,16,50} (k16 marginally best & tightest, 5-seed 0.0676 ± 0.0002; low kernel sensitivity, §5.4). Every capacity-*adding* probe we tried instead (continuous time-decay kernel, expert heads, text-distillation, dual-text, EMA, CL4SRec, James–Stein shrinkage, niche-competition loss, heat-kernel label smoothing, spectral-shrink, cue-fusion, forced ID→text routing) was neutral or harmful — several with a learned scalar the model itself drove to zero (the negative-result map, tabulated in Table S1, §5.5).

**Table 1a: Traceable within-paper SASRec-family floor (full-catalog eval).**

| Method | NDCG@10 | HR@10 | Notes |
|---|---:|---:|---|
| popularity | 0.0125 | 0.0248 | trivial floor (traceable: `results_5core_Video_Games.json`) |

*The v1-era SASRec/SBERT/BLaIR baseline rows and the observations derived from them have been REMOVED per the artifact-graph gate: their per-seed artifacts were not retained and the values are untraceable. Exact user/item counts, ±1 interaction agreement, frozen split hashes, and per-category floor runs establish dataset identity and local split traceability only; they do not establish training, implementation, or evaluation parity with a published system.*

**Table 1b: Reported, locally regenerated, and current-comparator evidence** (Liu, 2025; Hu et al., 2025; Xu et al., 2026):

The HSTU-BLaIR paper reports the same Video_Games item and user counts as ours (25,612 items / 94,762 users), but 814,585 interactions—one fewer than our 814,586—under its AR2023 5-core LLOO geometry. They train for **100 epochs** following Zhai et al.'s HSTU protocol. Their single-seed numbers:

| Method | NDCG@10 | HR@10 | Comparison to ours |
|---|---:|---:|---|
| SASRec (Liu, 2025, single seed, 100 epochs) | **0.0573** | 0.1028 | −15% below our full model 0.0673 ± 0.0003 |
| HSTU (Zhai et al., 2024) | 0.0741 | 0.1315 | +10% above our full model |
| HSTU-OpenAI (TE3L) | 0.0742 | 0.1328 | +10% above our full model |
| **HSTU-BLaIR (Liu, 2025)** | **0.0760** | **0.1353** | **+13% above our full model; stronger reported reference** |
| HSTU-BLaIR local SM120 compatibility port (this audit) | 0.07382 final full-eval (exported artifact; the higher best-epoch reading survives only in an unretained WSL log and is excluded from the artifact graph) | 0.13234 final | stronger than ours; not a faithful pinned-environment reproduction |
| AlphaFuse-style MiniLM representation package (8 fresh seeds; this audit) | 0.04827 [0.04813, 0.04842] | 0.08976 [0.08935, 0.09016] | `EEV3-REPORTABLE-OUTCOME-KNOWN`; +0.00925 [0.00833, 0.01017] vs zero-initialized upstream-class SASRec-ID, but −0.01906 [−0.01935, −0.01878] vs our reference |
| Zero-initialized upstream-class SASRec-ID control (8 fresh seeds; this audit) | 0.03902 [0.03811, 0.03994] | 0.07363 [0.07235, 0.07491] | frozen V3 ID-only control; parser-default `Normal(0,1)` not tested; official recipes may override initialization by dataset; not paired with the package arm |
| WEARec official model/training code (8 assessment seeds; this audit) | 0.05918 [0.05867, 0.05969] | — | `WEAREC-BELOW-EXISTING-REFERENCE`; −0.00815 [−0.00869, −0.00762] vs our six-seed 0.06734 reference under the shared evaluator |

**Our full model (0.0673) exceeds their published SASRec (0.0573) but does not reach their HSTU (0.0741) or HSTU-BLaIR (0.0760) on Video_Games.** Our local compatibility-port HSTU-BLaIR run reached final full-eval NDCG@10 `0.07382` (the best-epoch reading exists only in an unretained WSL log and is excluded from the artifact graph); the run is stronger than SASRec-SBERT but carries SM120/fbgemm validity caveats.

The separately frozen WEARec campaign used the official AAAI 2026 repository at commit `2087335339b1ead87da6e066ce14e2d33880a95e`. Two official-domain presets were selected by one tuning seed using validation NDCG@10 only; the selected `official_beauty` preset then trained on eight fresh assessment seeds with TEST scoring suppressed until all checkpoints existed. The committed adjudicator's first authorized endpoint read returned **`WEAREC-BELOW-EXISTING-REFERENCE`**: WEARec mean NDCG@10 **0.059184, 95% CI [0.058674, 0.059693]**, versus the existing six-seed full-model reference **0.067337 [0.067063, 0.067611]**. The descriptive outcome-known unpaired Welch contrast is **−0.008154 [−0.008689, −0.007618], p=1.16×10⁻¹¹**. This is narrow official-model/equal-evaluation evidence by the same investigators on an outcome-known split—not independent confirmation, SOTA, a paired experiment, or equality of architecture, loss, schedule, or tuning budgets. The graph replays the released NDCG vectors and Welch arithmetic; private endpoint extraction and HR/MRR raw-vector arithmetic are not publicly replayed.

The clean E-E V3 campaign froze the AlphaFuse upstream at commit `b501a0540b609370df995ad06fb245859b10a18a`, the official repository `AlphaFuse` and `SASRec` classes, one shared training configuration, and eight fresh seeds per arm. MiniLM-384 title vectors replace AlphaFuse's published OpenAI text vectors, so this is an AlphaFuse-style port rather than a published-table reproduction. Prelaunch preparation opened the pre-existing outcome-known combined TRAIN/VALID/TEST export but wrote a training input containing only user IDs, TRAIN histories, and VALID targets. Model fitting and complete-history-masked VALID selection did not load, hash, or score TEST; after all 16 selected checkpoints were bound into the family-wide READY record, 16 sealed one-shot TEST evaluations preceded the unchanged committed adjudicator. Its exact verdict, **`EEV3-REPORTABLE-OUTCOME-KNOWN`**, is countable as current-comparator evidence: AlphaFuse-style NDCG@10 **0.048273 [0.048129, 0.048416]**, zero-initialized upstream-class SASRec-ID control **0.039024 [0.038106, 0.039941]**, and descriptive independent-arm Welch difference **+0.009249 [0.008329, 0.010169], p=3.48×10⁻⁸**. The fixed-split user and target-item-cluster bootstrap sensitivities are also positive, but are not optimizer- or population-level inference. The package remains **−0.019065 [−0.019347, −0.018783]** below the existing 0.067337 full-model reference. Because text availability, initialization, trainable capacity, parameter allocation, and architectures differ, and the parser-default `Normal(0,1)` setting was not tested, this is a whole representation-package contrast. Official recipes may override initialization by dataset, so the parser setting is not a universal upstream default. The contrast is not null-space-fusion isolation, equal-tuning evidence, a paired experiment, independent confirmation, or SOTA. The public graph recomputes released aggregate vectors and Welch arithmetic and checks endpoint/sidecar ledger shape, 64-hex syntax, and uniqueness; it does not read or hash the private endpoint/sidecar files or replay record-level bootstraps. The local adjudicator, which had access to the private files, checked their recorded digests.

Relative to HSTU-BLaIR, this paper contributes multi-seed internal ablations, a released preprocessing path, and implementation diagnostics—not a leaderboard result. The reported 0.0760 remains the stronger Video_Games reference. Core-block equality at one aligned configuration (§3.2) and environment-caveated local regenerations (§5.6) do not constitute a pinned end-to-end reproduction.

**Older published baselines on different protocols** (NOT directly comparable; for context only):

| Method | NDCG@10 | Dataset | Protocol |
|---|---:|---|---|
| SASRec (in TIGER paper) | 0.0318 | Amazon Beauty **2014** | their 5-core (different category, different dataset year) |
| TIGER (Rajput et al., 2023) | 0.0384 | Amazon Beauty **2014** | their 5-core |
| SASRec (in LIGER paper) | 0.02179±0.00023 | Amazon Beauty **2014** | their 5-core |
| LIGER (K=20, Yang et al., 2024) | 0.04020±0.00044 | Amazon Beauty **2014** | their 5-core |
| LIGER (K=N, full retrieval) | 0.04738±0.00151 | Amazon Beauty **2014** | their 5-core |
| Best LLM-encoder in BLaIR (Hou et al., 2024) Table 8 | 0.0138 | AR2023 Video_Games | **by-timestamp 8:1:1, no k-core**, UniSRec downstream |

**Comparability caveat**: TIGER and LIGER evaluate on the older Amazon Reviews 2014 dataset, not AR2023. The BLaIR paper does evaluate on AR2023 Video_Games but uses a by-timestamp split (no k-core filter) and a different downstream architecture (UniSRec), producing numbers ~3-4× lower than our 5-core LLOO numbers. The 5-core filter guarantees ≥5 interactions per user and item in the full filtered sequence (which substantially eases the benchmark relative to the by-timestamp variant); note that after the leave-last-out split a small set of items retains zero *training* occurrences (§5.3 cohort disclosure). We therefore do **not** claim SOTA over TIGER/LIGER/BLaIR. HSTU-BLaIR is the relevant stronger AR2023 Video_Games 5-core reference and blocks a SASRec-SBERT SOTA claim.

**Concurrent protocol landscape.** SID-MLP, Latte, and GrIT report same-statistics AR2023 LLOO results; ReSID and ChronoSID use a different filtered universe; *Augment or Not?*, DiffuReason, and SILLM4Rec use non-interchangeable filtering or sampled-ranking setups; UniSGR uses private logs; and DIGER and ACERec address related semantic-ID problems outside this exact public protocol. We cite these works for coverage and make **no comparison against concurrent preprints**. HSTU-BLaIR remains the published external anchor for the counted point-estimate comparisons (§5.2).

Within our own full-catalog runs, the 11.6M-parameter model trains in about 10 minutes on one consumer GPU and reaches ≈5.4× the popularity floor (0.0125). These are efficiency and sanity-check observations, not priority or SOTA claims.

### 5.2 Canonical causal FIR internal contrasts and untuned category reuse (legacy-package attribution caveat §3)

The single most important robustness observation for the package arm is that its gain appears on a *second* category (no component-transfer claim), and does so *more strongly than label smoothing*. On Musical_Instruments (a sparser AR2023 category), the full V2 stack reaches **NDCG@10 = 0.0413 ± 0.0005 (5-seed)**, **+7.9%** over a matched HSTU+TAPE base (0.0383 ± 0.0004) and **+57%** over a plain ID-only SASRec (0.0264). A two-arm comparison (not a controlled isolation — §3 initialization caveat) (best-by-val, vs the MI SBERT+TAPE base 0.0383, four 20-epoch seeds 20260609–12) separates the two supported regularizers at the arm level (bundled arms; no component isolation):

**Table 1c: Musical_Instruments arm-by-arm comparison (NDCG@10, best-by-val, vs MI SBERT+TAPE base; shares are of the 5-seed V2 combined lift +0.0032).**

| Configuration | NDCG@10 | Δ vs base | share of combined lift |
|---|---:|---:|---:|
| MI SBERT+TAPE base (four 20-epoch seeds) | 0.0383 | — | — |
| + label smoothing only (5-seed) | 0.0391 ± 0.0001 | +0.0008 | 26% |
| **+ FIR package arm (filter component; attribution open) (k16, 5-seed)** | **0.0408** | **+0.0025** | **77%** |
| + both = V2 (k16, 5-seed) | 0.0415 | +0.0032 | 100% |

(Recomputed best-by-val from the released per-seed artifacts. Against the headline 5-seed V2 stack the package arm's share is 77% (k16) / 82% (k8). LS-only is the 5-seed family `results_MI_lsonly_seed{08–12}` (0.03914 ± 0.00013); base is the four e20 seeds 20260609–12.)

**The package arm contributes ≈3× what label smoothing does on the second category, and ≈80% of the combined lift in that same-seed decomposition — a package-level share, no component isolation — (77% vs the k16 stack, 82% vs the k8 headline stack)** — i.e. the historical package's gain appears on both development categories while label smoothing's does not (no formal component-by-category interaction was tested). Its kernel-length insensitivity also appears on MI (MI k8 0.0413 ± 0.0005 ≈ k16 0.0415 ± 0.0002). Component attribution for these historical runs remains open; the matched-initialization studies below provide cleaner internal contrasts, subject to their outcome-visibility limits.

**Pre-declared FIR study (`PREREG_FIR_V3.md` / E-A; mechanically adjudicated verdict W-POS; outcome-visible split).** A nonsingular reparameterization, `y = x + conv_Δ(x)` with Δ=0, made the treatment identity-initialized and gradient-active; three arms × eight seed blocks shared one verified initialization within each block. The frozen registered analysis is nevertheless independent-arm Welch/Satterthwaite: learned FIR minus identity is **+0.002265, ordinary 95% Welch CI [+0.001928, +0.002602]** (df=13.939) on Musical_Instruments. The paired-by-seed difference is retained only as descriptive. This is a cleaner within-configuration contrast than the historical package arms, but the category and split had already informed development and the execution record contains the provenance deviations documented in the audit; it is therefore exploratory internal evidence, not fresh confirmation. The registered Welch sensitivity A2−A1 is **+0.000010 [−0.000339, +0.000360], p=.95**: no difference was detected, but neither equivalence nor exclusion of a weight-decay pathway is established. Artifacts: `results_MI_FIRV3_{arm}_seed{seed}.json` (24 runs) and `fir_v3_adjudication.json`.

**Pre-declared canonical reparameterization breadth (`PREREG_FIR_CANONICAL_BREADTH.md`; verdict `CANON-BREADTH-POS`; outcome-known/test-exposed).** With one frozen K=16, 20-epoch configuration, zero category tuning, and exact per-seed matched initialization, learned minus identity is **+0.002110, ordinary paired 95% CI [+0.001820, +0.002399]** on Industrial_and_Scientific (paired t=17.23; Holm-adjusted p=5.44×10⁻⁷; 8/8 positive) and **+0.006150 [+0.005849, +0.006450]** on CDs_and_Vinyl (t=48.39; Holm-adjusted p=8.42×10⁻¹⁰; 8/8 positive). Supportive registered endpoints point in the same direction: HR@10/MRR differences are +0.003474/+0.001819 on Industrial_and_Scientific and +0.010728/+0.005033 on CDs_and_Vinyl; the broader registered cutoff family was not emitted by the trainer and is not claimed. The categories were selected after favorable legacy-package outcomes and TEST was evaluated each epoch, so these estimates are **descriptive robustness of the canonical parameterization, not independent confirmation or population transfer**. The intervals are ordinary paired-t intervals; Holm adjusts decisions/p-values, not confidence limits. All 32 source JSONs and the adjudication record are now hash-bound in the public artifact inventory.

**Pre-declared six-arm active-control study (`PREREG_FIR_CONTROLS.md`; eight matched seed blocks; sealed one-shot final TEST; frozen verdict `CTRL-ACTIVE-CONTROL-SUPPORTED`).** The frozen analysis has two separate Holm families; all confidence intervals below are ordinary paired 95% intervals, not simultaneous intervals. In family A (each trainable left-causal arm minus frozen identity), learned is **+0.002116 [+0.001910, +0.002322], p_Holm=2.04×10⁻⁷**; fixed MA **+0.000712 [+0.000509, +0.000915], p_Holm=1.30×10⁻⁴**; fixed HP **+0.000708 [+0.000510, +0.000907], p_Holm=1.30×10⁻⁴**; channel-shared **+0.002197 [+0.002008, +0.002386], p_Holm=1.08×10⁻⁷**; and parameter-matched nonlinear causal **+0.001912 [+0.001657, +0.002166], p_Holm=1.33×10⁻⁶**. In family B (learned minus each active control), learned exceeds fixed MA by **+0.001404 [+0.001085, +0.001723], p_Holm=6.37×10⁻⁵** and fixed HP by **+0.001407 [+0.001089, +0.001726], p_Holm=6.37×10⁻⁵**, but the fixed arms are algebraically redundant scalar/sign parameterizations. A learned-specific advantage is not established over shared (**−0.000081 [−0.000337, +0.000175], p_Holm=.477**) or nonlinear (**+0.000204 [−0.000038, +0.000446], p_Holm=.174**); retained tests are not equivalence. Thus the tested trainable left-causal residuals improve frozen identity, but learned taps are not uniquely supported. This study alone lacked a parameter-matched non-temporal placebo. It was designed after the learned–identity outcome was known, ran from a dirty evolving tree, and its sidecars were not independently custodied because of a filename-suffix ignore error; we classify it as outcome-known exploratory evidence despite its frozen analysis and sealed evaluator. Human pre-adjudication visibility remains an author-verification item.

**Pre-declared parameter-matched non-temporal placebo (`PREREG_FIR_POINTWISE_V1.md`; eight matched seed blocks; sealed one-shot final TEST; frozen verdict `POINTWISE-FIR-DISCRIMINATED`).** The placebo uses only the current position: a deterministic width-16 orthonormal DCT projection, GELU, and zero-initialized learned 16→64 map. It is identity-initialized, gradient-active, and has exactly 1,024 trainable parameters—the same as the K=16 depthwise FIR—but cannot access earlier positions. In one frozen three-test Holm family, learned FIR minus identity is **+0.001872 [+0.001737, +0.002007], p_Holm=1.87×10⁻⁸**; pointwise minus identity is **−0.000069 [−0.000200, +0.000061], p_Holm=.249**; and learned FIR minus pointwise is **+0.001941 [+0.001788, +0.002095], p_Holm=2.40×10⁻⁸**. All intervals are ordinary paired 95% intervals; the retained pointwise–identity test is not equivalence. This discriminates the learned temporal FIR from the tested equal-parameter non-temporal residual under matched initialization. It does not establish unique per-channel-tap necessity because the earlier shared causal filter remains competitive, and it is still outcome-known Musical_Instruments mechanism evidence—not independent confirmation, cross-domain replication, or a general filtering claim.

**Frozen Software robustness attempt (`PREREG_FIR_PROSPECTIVE_SW_V3.md`; eight matched seed blocks; sealed one-shot final TEST; verdict `SW-V3-PRACTICAL-POS`).** The learned and identity arms used exact per-seed matched backbone initialization.
Training loaded TEST rows only for the explicitly pre-declared transductive item catalog and emitted no TEST scores; checkpoints were selected solely by validation NDCG@10.
After all 16 checkpoints existed, the committed driver created exclusive-created, hash-linked local READY/evaluation seals, evaluated each selected checkpoint once on TEST, and invoked the protocol-designated adjudicator.
Mean TEST NDCG@10 was **0.120200 learned versus 0.115138 identity**; learned minus identity was **+0.005062, ordinary paired 95% CI [+0.004591, +0.005533]**, paired t(7)=25.39, two-sided p=3.75×10⁻⁸, with 8/8 differences positive.
The CI lower bound cleared the frozen +0.000500 reporting threshold, yielding the exact mechanical verdict `SW-V3-PRACTICAL-POS`.
Tracked evidence cannot establish whether earlier V2 validation output was observed before V3 was frozen, and local logs cannot prove first human/tool access; absent an author custody statement, we therefore classify V3 as **outcome-known exploratory same-team robustness**, not confirmation.
It is also same-investigator, same-code-lineage, and same-Amazon-family work under local same-user custody with no external escrow. Finally, the frozen tag binds a CRLF raw digest for one MI lineage-reference JSON while a normal tagged checkout produces LF bytes; direct clean-tag execution therefore fails that raw input assertion until the historical CRLF representation is restored. The reference was not read for runtime configuration, so the defect does not change endpoint arithmetic, but it narrows replayability (documented in `FIR_PROSPECTIVE_SW_V3_REPLAY_ERRATUM.md`).

The paired-difference sample SD was **0.000563779**. In registered seed order, the eight learned-minus-identity differences were **+0.005197548, +0.004308974, +0.005082181, +0.005788969, +0.005439290, +0.005516648, +0.004194543, and +0.004966712**. A post-hoc two-sided exact sign test for 8/8 positive differences gives **p=.0078125**. This sign test is a small-n robustness sensitivity, not the frozen decision rule and not population-level uncertainty across users, cutoffs, categories, or domains.

Figure 1 is a visual index of the released FIR contrasts, arranged to expose both scope and boundary conditions. It is not a pooled estimate: the intervals retain the estimators and evidence classes of their source adjudications and do not form one multiplicity family. The positive Amazon rows are outcome-known internal evidence; the matched MI controls show that learned FIR exceeds the equal-parameter pointwise placebo but not the shared causal filter; and the two prospectively frozen same-investigator MovieLens transfer intervals include zero.

![Fig. 1: FIR evidence map across released adjudications. Four outcome-known internal Amazon learned-minus-identity estimates are positive. On matched MI controls, learned FIR exceeds the equal-parameter pointwise placebo, while learned minus the shared causal filter spans zero. In the prospectively frozen same-investigator MovieLens study, learned minus identity and learned minus pointwise both span zero. Intervals retain their source estimators and are not pooled or one common multiplicity family; exact values and source keys are in `figures/fig_fir_evidence_summary_data.csv`.](figures/fig_fir_evidence_summary.png)

*Fig. 1: FIR evidence map. Positive outcome-known Amazon contrasts coexist with a shared-filter boundary and a negative prospectively frozen MovieLens transfer result; intervals are not pooled.*

**Prospectively frozen non-Amazon replication and efficiency study (`PREREG_FIR_EFFICIENCY_ML1M_V1.md`; MovieLens 1M; verdict `ML1M-NO-FIR-REPLICATION`).** The protocol, acquisition code, six-arm trainer, structural/sequestration tests, runner, evaluator, and adjudicator were committed and pushed before acquiring MovieLens. The rating≥4 primary view used a global 90% time boundary, a training-observed catalog, 1,033 users, 2,359 items, and 135,131 training rows. Acquisition necessarily read and hash-bound TEST and used its target for cohort eligibility; the narrower sequestration claim is that model fitting/selection emitted no TEST scores and all 96 selected checkpoints existed before the 96 sealed one-shot TEST evaluations. Those evaluations preceded the protocol-designated adjudicator's first endpoint read. This is prospectively frozen same-investigator non-Amazon evidence, not independent confirmation or population-wide generalization.

The exact primary verdict is negative. Learned FIR did not replicate against identity (**+0.000000, ordinary paired 95% CI [−0.000074, +0.000075], `p_Holm=.995`**) or the equal-parameter pointwise arm (**+0.000035 [−0.000057, +0.000127], `p_Holm=.796`**). Mean NDCG@10 was 0.052151 for both learned and identity and 0.052116 for pointwise. The all-ratings sensitivity agreed: learned−identity +0.000012 [−0.000107, +0.000131] and learned−pointwise +0.000043 [−0.000082, +0.000168]. All six pre-declared user/item cluster percentile intervals for the parsimonious-arm contrasts included zero.

| arm | filter parameters | mean NDCG@10 | arm − learned | simultaneous lower bound | frozen interpretation |
|---|---:|---:|---:|---:|---|
| identity | 0 | 0.052151 | −0.000000 | — | learned replication failed |
| shared K=16 | 16 | 0.052211 | +0.000060 | −0.000068 | NI-PASS |
| grouped K=16 | 128 | 0.052125 | −0.000027 | −0.000128 | NI-PASS |
| low-rank K=16 | 320 | 0.052211 | +0.000060 | −0.000033 | NI-PASS |
| learned per-channel K=16 | 1,024 | 0.052151 | 0 | — | effect gate failed; no replicated FIR benefit |
| pointwise placebo | 1,024 | 0.052116 | −0.000035 | — | learned−pointwise failed |

Shared, grouped, and low-rank each passed the frozen 0.000500 noninferiority family (`p_Holm=5.20×10⁻⁶`, `5.20×10⁻⁶`, and `1.43×10⁻⁶`). These are conditional coefficient-count compression findings—not a computational optimization and not evidence that a smaller FIR is useful—because the prerequisite learned-FIR replication contrasts failed. There is no bypass implementation, and measured end-to-end latency and memory did not materially improve: median latency per user was 2.076/2.105/2.087/2.132/2.073/2.120 ms in table order; primary-view training peak memory ranged only from 580.94 to 583.28 MiB on one RTX 5060 Ti. The resource plane is therefore descriptive hardware evidence, not a general efficiency ranking. Under the ML-1M README, record-level rows, checkpoints, endpoints, and per-user sidecars remain private; the public graph verifies frozen code hashes and recomputes all reported aggregate-vector arithmetic but cannot independently replay private endpoint extraction.

![Fig. 2: MovieLens 1M R4 aggregate FIR accuracy-resource plane. Panels plot the six arms' primary eight-seed mean NDCG@10 against filter parameters, median latency per user, and median training peak CUDA memory. Learned FIR failed to replicate versus identity and pointwise. The plotted resource readings are descriptive measurements on one GPU; exact aggregate values are in `figures/fig_fir_efficiency_ml1m_v1_data.csv`.](figures/fig_fir_efficiency_ml1m_v1.png)

*Fig. 2: MovieLens 1M accuracy-resource plane. Learned FIR failed to replicate; latency and memory are descriptive measurements on one GPU.*

**Pre-declared breadth (two further categories).** Under `PREREG_FIR_BREADTH.md` (committed before any run; fresh never-inspected seeds 20260713–17; mechanical adjudication in `FIR_BREADTH_RESULTS.md`), the filter was transplanted with **zero per-category tuning** and tested as a same-seed 5-seed filter-vs-no-filter contrast — an internal contrast with no comparator involved — on two categories never used in its development. **Both categories fired the frozen decision rule**: Industrial_and_Scientific same-seed Δ = **+0.0024 ± 0.0005** (pre-declared paired-analysis 95% CI [+0.0018, +0.0030]; 5/5 same-seed differences positive) and CDs_and_Vinyl same-seed Δ = **+0.0057 ± 0.0006** (pre-declared paired-analysis 95% CI [+0.0049, +0.0064]; 5/5). **Analysis-premise correction (2026-07-19):** the frozen rule *as written* is a paired Student-t, but its pairing premise is now known to be false — same-numbered seeds are not initialization-paired (§5.3 randomization disclosure) — so the pre-declared intervals are reported as executed-as-frozen outputs whose *paired interpretation is withdrawn*; the **primary supported statement** is the post-hoc independent-arm Welch analysis (we no longer call it conservative: with correlated arms neither interval has a general conservative ordering, and here the Welch intervals are in fact narrower than the paired ones), under which both effects remain positive with 95% CIs excluding zero (Industrial_and_Scientific [+0.0019, +0.0029], CDs_and_Vinyl [+0.0050, +0.0063]; graphed as `firb.*.welch`, evidence-class exploratory since the Welch analysis is post-hoc). Per the frozen claim wording as narrowed by this correction, each result is exactly: *the causal-FIR-filter arm's 5-seed improvement over the no-filter arm on that category is positive with a 95% CI excluding zero* — an internal same-seed contrast of the FIR-plus-initialization/optimizer package; nothing broader, no SOTA language, no comparator statement. The filter package is thus multi-seed-supported on **four categories**, two of them under this pre-declared breadth campaign — and now **estimated under the valid independent-arm TFV2 pre-declaration (outcome-visible; not confirmatory — §5.3(vii))** (below), which supersedes this campaign's withdrawn paired interpretation as the primary FIR evidence.

**TFV2 independent-arm replication (pre-declared, outcome-visible; adjudicated 2026-07-20).** The `PREREG_TAIL_FIR_V2.md` campaign (Git-committed frozen rules; outcome-visible — OTS chronology in §5.3, disclosure (vii)) reran both breadth categories as fully independent 8-vs-8 arms (fresh never-inspected seeds; no pairing premise; per-run sidecars released): Industrial_and_Scientific overall Δ = **+0.002131** (t = 16.99, 95% CI [+0.001862, +0.002400]) and CDs_and_Vinyl overall Δ = **+0.005770** (t = 26.12, 95% CI [+0.005275, +0.006266]) — **both PASS under Holm** (one family with the tail endpoint E1, §5.3). This replaces the withdrawn paired interpretation with a valid pre-declared independent-arm design; the treatment remains the FIR-plus-initialization/optimizer package. Descriptively, the filter's positive-frequency-tail improvements are +0.000775 (IS, p = 2×10⁻⁴) and +0.002329 (CDs, p = 3×10⁻¹²).

**Comparator ablations (audit-requested).** Each arm targets one named design element of the filter (with the disclosed caveat that the singular headline initialization means these arms also alter the optimization path, §3) on the same 5-seed MI stack: freezing the kernel at a causal moving average (learnable gate retained) recovers only +0.00133 of the filter's +0.00225 descriptive mean gain over the no-filter baseline (0.04046 ± 0.00022 vs 0.04138 ± 0.00053) — an observation confounded by the shared singular start (§3). Here ± denotes sample standard deviation, and no inference is based on visual overlap of those bands; no learned-shape attribution is claimed. Freezing the gate at 1 (delta-initialized kernel) has a similar descriptive mean to the full filter (0.04127 ± 0.00046), so the zero-init gate comparison is confounded by the singular-initialization bootstrap (§3 disclosure) and is not a clean single-factor attribution.


**Pre-declared confirmation vs the published per-category reference.** The seeds above (20260608–17) are *exploratory*: kernel choice, epoch budget, and the decision to compare against the published Musical_Instruments HSTU-BLaIR number (0.0406; Liu 2025, Table 2) were all made while inspecting them. To make the comparison selection-free, we froze a version-controlled pre-declared protocol (`SOTA_CONFIRM_PREREG_V2.md`, committed to version control before any confirmation run: exact config and commands, data SHA256s, decision rule, claim wording) and ran **five pre-specified never-inspected seeds (20260618–22) under each of the two kernels — ten arm-runs** with per-run provenance manifests (command, git commit + clean-tree flag, environment, data hashes) and per-user record sidecars. Result: **K=16 fresh 5-seed 0.04152 ± 0.00045 (95% CI lower bound 0.04096) and K=8 0.04120 ± 0.00030 (CI-LB 0.04083) — both CI lower bounds above the published 0.0406, 10/10 seeds above.** The supported claim is exactly this: *fresh multi-seed means and seed-level confidence intervals exceed the published HSTU-BLaIR point estimate on this category under our reproduced protocol (parity evidence: users/items match the paper exactly; interactions differ by one — see `SOTA_CONFIRM_PREREG_V2_ERRATA.md` E1; our plain SASRec floor is* below *their published SASRec, ruling out an easier split).* The comparator is single-seed; our post-hoc local regeneration of it (§5.6 — the reference implementation's research path under data-movement shims, unpinned environment) regenerates the published value at its best full-eval epoch (0.0406; final epoch 0.0391) but is itself a single environment-caveated run, so no paired or distributional superiority is claimed, and this remains a per-category result — Video_Games is explicitly not claimed (§5.1). The first execution of this confirmation was voided by its own provenance tripwire (a concurrent documentation edit dirtied the tracked tree mid-campaign) and re-executed in full under a clean tree; both executions agree per-seed to ±0.0003 (`SOTA_CONFIRM_V2_RESULTS.md`). One protocol deviation is disclosed rather than claimed away: the gated runs executed at a documentation-only descendant commit of the pre-declaration's introducing commit (the pre-declared commit-equality rule was not literally satisfied); code identity across the two commits is demonstrated by empty protocol-file diffs and, in the from-scratch rebuild, by code hashes embedded in each run manifest (`SOTA_CONFIRM_PREREG_V2_ERRATA.md`, E3).

**Office_Products V1 (the original second-category attempt) — descriptive only; superseded by the counted V3 campaign below.** Office_Products numerically exceeded the published HSTU-BLaIR point estimate under the frozen MI configuration, but the pre-declared SASRec floor check failed because our local SASRec floor was substantially above the published SASRec reference. We therefore treat the V1 Office campaign as descriptive evidence, not as a passed confirmatory category (the separately pre-declared V3 campaign later passed and is counted, §5.2). The floor anomaly has since been resolved mechanistically — the reference implementation's own SASRec, run locally on its own pipeline (§5.6), lands +13.9% above its published row, while a completed run of their Office HSTU-BLaIR configuration regenerates its published row (+1.6%; §5.6) — the conservatism is a property of the published Office SASRec row specifically. The VOID is retained on procedural grounds (the pre-declared floor check failed as written); full detail, decomposition, and disclosures in Appendix A.0.

 **Office_Products V3 (redesigned pre-declaration) — PASSED.** Under `PREREG_OFFICE_V3.md` (committed before any run; fresh never-inspected seeds 20260728–32; gate: each arm's fresh 5-seed 95% CI lower bound must exceed the **environment-matched local regeneration of the comparator** — best full-eval 0.0279, itself above the published 0.0271 — with ≥4/5 seeds individually above), **both kernel arms passed**: K=16 fresh 5-seed **0.03047 ± 0.00011 (CI-LB 0.03033)** and K=8 **0.03029 ± 0.00005 (CI-LB 0.03024)**, 10/10 seeds above both references; dataset identity, reference-artifact hashes, and per-run provenance verified mechanically (`OFFICE_V3_RESULTS.md`). Per the frozen claim wording: *a per-category point-estimate comparison against the published 0.0271 and its environment-matched single-run local regeneration 0.0279; no paired or distributional superiority is claimed; this is not SOTA on Office_Products, not SOTA on Amazon Reviews 2023, and not a general-SOTA claim of any kind.* The V1 VOID above stands unchanged as its own record (Appendix A.0).

### 5.3 The Musical_Instruments frequency-5 tail case (cross-dataset heterogeneity not established)

Beyond *whether* text helps overall (modestly: +2.7% on Video_Games, §5.1), we ask *where this additive frozen-text construction helps* (only early additive fusion of frozen text features is tested — §2.3 scope note). `evaluate()` reports `by_popularity` NDCG@10 over nominal train-frequency terciles {tail, mid, head} (bucketed by TRAIN frequency only, so no validation/test frequencies enter the bucketing; two cohort-definition defects are disclosed below), and we compare the full text stack against an ID-only ablation on the **same split and seed numbers**. The cold-start intuition — text should rescue rare items where ID embeddings are starved — holds on *one* of three datasets, and the MI difference survives an independent-arm analysis.

**Randomization disclosure.** Same-numbered text and ID arms are not initialization-paired: treatment-specific modules consume RNG before the shared backbone is constructed, changing backbone initialization and subsequent stochastic streams. Table 1d's per-seed differences are therefore descriptive, all retained inference is independent-arm Welch/Satterthwaite, and the former paired CI/MDE/TOST analyses are withdrawn.

**Table 1d: text − ID tail-tercile NDCG@10 contrast (same-seed-number arms — NOT initialization-paired; per-dataset estimates — cross-dataset heterogeneity not established, point 3).**

| dataset | catalog density | tail Δ NDCG@10 (5-seed) | seeds positive | verdict |
|---|---|---:|---:|---|
| **Musical_Instruments** | sparse | **+0.000335 ± 0.000195**, Welch 95% CI [+0.000109, +0.000562] **excl 0** | **5/5** | **frequency-5 tail advantage (independent-arm; §5.3)** |
| **Video_Games** | dense | −0.000148 ± 0.000179 | 2/5 | null — equivalence **NOT** established (retraction, point 2) |
| **Beauty_and_PC** | dense | −0.0000078 (3-seed, sample-sd 0.000020) | 1/3 | exploratory (3-seed; mixed eval geometry) |

The historical MI contrast survives independent-arm analysis (Welch t = 3.94, p = 0.014, 95% CI [+0.000109, +0.000562]) and has tail HR Δ = +0.00109 ± 0.00065, but its absolute scale is small (≈29.6 versus 20.0 hits/seed); MI's largest absolute text lift is at the head (+0.00527). On Video_Games, no tail difference is detected (Welch p ≈ 0.22), but equivalence is **not** established. Beauty remains exploratory because one arm pair uses unmatched evaluation geometry. Most importantly, the repaired TFV2 MI−VG contrast is +0.000247 (p = 0.13), so cross-dataset heterogeneity did not replicate and is not claimed (Fig. 1).

**Why Table 1d is historical.** Its nominal terciles mix zero-train-exposure targets with positive-frequency targets and split boundary-frequency ties by item-ID order; the original runs also lack per-row outcome sidecars. These arm-independent defects do not create a treatment-specific cohort, but they prevent the intended rare-item interpretation. TFV2 therefore separates zero exposure, uses whole-frequency-group cohorts, and releases per-user outcomes.

**Repaired-estimand campaign (TFV2; 8 independent seeds/arm).** On the tie-safe MI positive-frequency tail, text − ID is **+0.000420, 95% CI [+0.000181, +0.000660], Welch p = 0.0022**, passing the frozen Holm rule. The [1,6] band (+0.000546, p = 0.0039) and HR@10 (+0.001150, p = 4×10⁻⁵) agree. However, zero-exposure targets produce no hits through rank 100 in any of four categories, the exclude-frequency-5 sensitivity is nonsignificant (+0.000071, p = 0.52), and the frequency-5 group alone is +0.001379. We therefore report a **frequency-5-heavy positive-tail case**, not cold-start capability or a smooth rare-item law. VG is nonsignificant (+0.000173, p = 0.14), as is MI−VG (+0.000247, p = 0.13).

**Evidence status.** TFV2's endpoints were Git-frozen before launch, but interim test values became visible, its first independently verifiable timestamp postdates the first result, and the adjudicator was committed after some outputs existed. The eight-seed size was resource-based rather than prospectively powered, and the run manifests record concurrent tracked-document edits. TFV2 is therefore **outcome-visible, not confirmatory**; its released sidecars and frozen estimator support reproducible estimates, not a claim of blinded confirmation. The repository retains the complete chronology, cohort files, logs, hashes, and errata.

![Fig. 3: (A) TFV2 repaired-estimand tail contrasts — MI, VG, and the MI−VG interaction as Welch 95% CIs (8 fresh seeds per arm; one estimand; outcome-visible campaign, §5.3; cross-dataset heterogeneity not established, p = 0.13). The historical defective-cohort Table 1d values are tabulated, not plotted. (B) Interaction-density titration level contrasts and (C) two-axis descriptive ratios — both on ONE fixed subset draw with no draw/seed uncertainty shown; arms are not initialization-paired (§5.3); the panel-C shift is suggestive only (p = 0.058, CI includes 0). Plotted values, estimator, and analysis IDs: figures/fig_tail_law_mechanism_data.csv.](figures/fig_tail_law_mechanism.png)

*Fig. 3: Tail contrasts and fixed-draw titration summaries. Cross-dataset heterogeneity is not established; the two-axis shift is suggestive only (p = 0.058).*

### 5.4 Titration: thinning tracks the head effect but not the tail effect (level contrasts under a bundled intervention; head trend exploratory and uncorrected; tail inconclusive)

We thinned Video_Games interactions over six rungs down to MI's global density (ρ=0.66), holding n_eval at 94,762 and re-estimating text−ID differences with five seeds per rung. The two strata respond differently:

- **Head:** Δ rises overall from +0.00221 to +0.00354; all rungs are 5/5 positive. Spearman ρ_s versus density is −0.94 (exact p=0.017), with one adjacent reversal; the HR trend is weaker (ρ_s=−0.71, p≈0.14). This is an exploratory uncorrected rank trend on one fixed thinning draw.
- **Tail:** Δ is non-monotone (ρ_s=−0.14). At MI-matched density it is −0.000108 ± 0.000503 (1/5 positive), so thinning does not reproduce MI's +0.000335 tail estimate. Without a prospective equivalence margin this is inconclusive, not evidence of no effect.

The full ladder is Table S2. The head trend and tail non-reproduction are level contrasts under a bundled intervention; their interaction is nonsignificant. Global density is therefore not identified as the tail mechanism.

#### 5.4.1 The level contrasts in one scale-free table: the cross-dataset tail/head arm ratio (descriptive; no interaction-test support)

To separate absolute scale from arm contrast, Table 5 reports the text/ID NDCG ratio at full VG density, VG thinned to MI density, and native MI. Ratios above one favor text.

| regime (interactions/item) | n (text/id) | TAIL text | TAIL id | **TAIL ratio** | tail Δ | **HEAD ratio** |
|---|---|---|---|---|---|---|
| VG full density (ipi 24.5) | 5 / 5 | 0.004919 | 0.005068 | **0.971 (−2.9%)** | −0.000148 | 1.026 (+2.6%) |
| VG thinned → MI-density (ρ=0.66, ipi 16.2) | 5 / 5 | 0.003569 | 0.003677 | **0.971 (−2.9%)** | −0.000108 | 1.049 (+4.9%) |
| MI native (ipi 16.2) | 5 / 5 | 0.001551 | 0.001216 | **1.276 (+27.6%)** | +0.000335 | 1.101 (+10.1%) |

The head ratio rises from 1.026 to 1.049 as VG is thinned, toward MI's 1.101. The tail ratio remains 0.971 at both VG densities, far below MI's 1.276. Thus matching global density does not reproduce the MI tail advantage on this draw. The earlier two-seed “trough” interpretation is retracted; the five-seed endpoint is near zero with a wide interval. This remains a level contrast, not a significant stratum-by-density interaction.

One hypothesis is that user connectivity or item-text quality differs between native MI sparsity and artificially thinned VG. Neither is identified here: user thinning changes several dataset properties at once, and an item-text permutation control has not been run.

#### 5.4.2 User-mode titration: a suggestive tail-level response at MI-matched connectivity (bundled intervention; descriptive)

User thinning preserves each retained user's history while lowering users/item. At ρ_user=0.66 it matches the interaction-thinned rung's interactions/item (16.1 versus 16.2) and approaches MI's users/item (2.44 versus 2.34). Because user composition, degrees, update counts, and topology also change, this is a bundled-scheme contrast, not single-factor identification.

The read comes out on the predicted branch — a positive shift (suggestive):

| regime (int/item, users/item) | TAIL ratio | tail Δ (5-seed) | HEAD ratio |
|---|---|---|---|
| VG full (24.5, 3.70) | 0.971 | −0.000148 | 1.026 |
| VG interaction-thinned ρ=0.66 (16.2, ~3.4) | 0.971 | −0.000108 ± 0.000503 (1/5 pos) | 1.049 |
| **VG user-thinned ρ_user=0.66 (16.1, 2.44)** | **1.046** | **+0.000178 ± 0.000153 (5/5 pos, t≈2.6)** | 1.039 |
| MI native (16.2, 2.34) | 1.276 | +0.000335 ± 0.000195 (5/5 pos) | 1.101 |

The tail ratio moves from 0.971 to 1.046. The independent-arm difference-in-differences is +0.000326 (p=0.058, 95% CI [−0.00001, 0.00067]); the within-rung tail level is +0.000178 (p≈0.16). The former paired analysis is retracted because arms are not initialization-paired. Fig. 4 therefore shows a suggestive direction, not a confirmed effect or connectivity attribution.

![Fig. 4: The (R1 = interactions/item, R2 = users/item) resource plane — the two VG thinned rungs share R1, but only the user-thinned (R2) point moves to a positive tail point estimate beside MI native (suggestive; p = 0.058).](figures/fig_r1r2_plane.png)

*Fig. 4: The (R1 = interactions/item, R2 = users/item) resource plane — the two VG thinned rungs share R1, but only the user-thinned (R2) point moves to a positive tail point estimate beside MI native (suggestive; p = 0.058).*

Lower user-thinning rungs do not support a “peak then collapse” interpretation: ρ_user=0.50 is +0.000236 ± 0.000532, while ρ_user=0.40 exhibits a text-arm floor collapse. The user-thinned estimate also remains below native MI. Overall, interaction thinning tracks the head level, while user thinning gives only a suggestive tail-level shift. Shared intervention draws omit subset uncertainty, the stratum-by-density interaction is nonsignificant, and the mechanism remains unidentified. A prior spectral explanation is retracted because it did not measure the claimed spectrum.



> **Provenance:** released `results_USERTITR_*.json`; five seeds per rung; n_eval=94,762 and tail_n=10,900 fixed. Arms share seed numbers but are not initialization-paired. All model seeds use one intervention draw.

### 5.5 Screening log of capacity-adding probes (a search record, not powered exclusions)

A central empirical finding of this work is **asymmetric**: the only levers that moved test NDCG@10 were *capacity-restricting* (label smoothing, the causal FIR filter) or classical inductive biases already in Table 1 (the time bias); **no capacity-*adding* probe we tried showed a benefit at its tested power (mostly single-seed).** We document the full set here as a first-class result — negatives are part of the contribution, and several are *interpretable* negatives in which a learnable scalar, free to engage the mechanism, was driven by the optimizer to (or past) zero. This is observational evidence — most rows are single-seed probes (power note below) — that the in-environment ceiling was not left unexplored on these axes; the residual gap to the published HSTU-BLaIR 0.0760 could not be isolated (the pinned reference environment is not installable here, and the shimmed local execution of §5.6 did not include the Video_Games configuration); what the probe set shows is that none of the tested probes (mostly single-seed; Table S1 power note) produced a gain — observations that leave the gap unexplained, not exclusions.

All entries are best-by-val test NDCG@10, full-catalog eval (n_eval = 94,762 on Video_Games), on the same fixed protocol. Δ is versus the stated base; for the three learnable-scalar probes (W1/X1/Y1) we report the absolute single-seed test next to its base band, since the headline test is statistically indistinguishable from the base and the *learned scalar* is the load-bearing readout. Several rows are single-seed — sufficient for a negative-result map (a probe that fails to clear its base on one seed, or whose own learned scalar switches it off, does not warrant five seeds).

**Unequal power.** Most rows are single-seed exploratory probes; only the multi-seed pre-declared negatives — the conn-gate five-seed confirmation (cadence-caveated; see the row note) and the §5.3–§5.4 titration nulls — were run at full pre-declared power (no null is thereby confirmed; the equivalence framework is withdrawn). The Beauty near-zero tail estimate is a 3-seed exploratory observation (mixed evaluation geometry, §5.3) carrying no confirmatory weight. Per-probe seed counts are in the table's n column.

The full screening log — all 18 capacity-adding / alternative-mechanism probes with per-probe Δ NDCG@10, seed counts, and learned-scalar readouts — is **Table S1** (Supplement §S.4); it is summarised above and analysed next.

The pattern is consistent and is itself the finding: across loss-side (W1, Y1, sampled-softmax), embedding-side (X1, GD1, text-init), attention-side (c3, n_heads, text-sim), encoder-side (BLaIR, dual-text), and auxiliary-objective (c1, c2, CL4SRec, EMA) axes, no capacity-adding probe produced a test gain at its tested power (mostly single-seed; power note above), and three free scalars (W1's β, X1's c, Y1's T) were each switched off — or, for W1, reversed — by the optimizer. Only anti-overconfidence regularizers (label smoothing) and the restricted causal-filter inductive bias (Table 1) transferred. These are hypothesis-generating observations at their stated (mostly single-seed) power, not powered exclusions; **we do not claim they bound an in-environment ceiling**. (An earlier spectral-irreducibility clause here is retracted — see the §5.4.2 retraction note.) The conn-gate row deserves separate emphasis: it is the only entry tested at full five-seed power and the only one that directly operationalizes *this paper's own intervention-associated tail pattern* — the collaborative-connectivity association of §5.4.2. A single seed showed a +0.00053 tail lift, but the pre-declared five-seed confirmation collapsed to +0.0001 ± 0.0003 (95% CI [−0.00025, +0.00045], includes zero), and the free gate scalar α was driven *below* its initialization (voted off; the learned value is recorded in 4/5 seed logs — the fifth predates the log line, and the graph reports the recovered count). **Cadence caveat (disclosed 2026-07-19):** the conn-gate arms were evaluated only at epochs {10, 20} while their base evaluated every epoch, so best-by-val checkpoint opportunities were unequal across arms; the tail CI-includes-zero verdict is unchanged by this, but the small overall delta is cadence-sensitive and we rest no claim on its sign. This is the cleanest illustration of the paper's central distinction: a mechanism-associated pattern can be *supported* by controlled thinning contrasts (the matched-R1 level contrast) yet not be *actionable* through a learnable cold-start gate — one *interpretation* — a hypothesis, not an identified mechanism — is that the connectivity signal the model needs is already latent in the frozen text features, leaving no residual for an explicit gate to exploit.

### 5.6 Executing the reference implementation locally (post-hoc comparator regeneration)

Late in this work we succeeded in running the **reference implementation itself** — the HSTU-BLaIR repository at its released commit, unmodified (clean git tree): its preprocessing, its gin configurations, its trainer, and its eval protocol — end-to-end on our hardware. The pinned environment (torch 2.2.2 / fbgemm_gpu 0.6.0) remains uninstallable here (no sm_120 kernel images, no Windows wheels); what makes execution possible under our unpinned torch 2.11 environment is that the repository's research path uses exactly **three** `fbgemm` operators, all pure data movement (`asynchronous_complete_cumsum`, `jagged_to_padded_dense`, `dense_to_jagged`), which we re-implement in plain PyTorch with self-tested forward/gradient parity, plus a world-size-1 identity DDP wrapper and logging/data-acquisition patches (full shim inventory, per-run provenance, and artifacts: `THEIRS_ON_OURS_REPORT.md`). No model math is touched — the layer norms, fused projections, SiLU pointwise attention, biases, loss, and scoring all execute in the reference repository's own unmodified lines, consistent with the core-block parity evidence of §3.2. Their own preprocessing pipeline ran with its dataset-size assertions left active and **passing** on both corpora (Musical_Instruments: 24,587 items / 57,439 users; Office_Products: 77,551 items / 223,308 users — the comparator paper's exact statistics).

Two single-run results (their configurations as shipped, 101 epochs; our RTX 5060 Ti):

| run (their code, their data, their eval) | published | local, final epoch | local, best full eval |
|---|---|---|---|
| **MI HSTU-BLaIR** — NDCG@10 | 0.0406 | 0.0391 | **0.0406** (epoch 35 — exact) |
| MI HSTU-BLaIR — HR@10 | 0.0733 | 0.0716 | 0.0743 |
| MI HSTU-BLaIR — MRR | 0.0371 | 0.0355 | 0.0369 |
| **Office SASRec** — NDCG@10 | 0.0153 | **0.0174** (+13.9%) | 0.0177 |
| **Office HSTU-BLaIR** — NDCG@10 | 0.0271 | 0.0275 (+1.6%) | 0.0279 |

**The Musical_Instruments comparator regenerates locally.** The final-epoch full-corpus eval lands within 2.3–4.3% of every published metric above, and the best full-eval epoch hits the published NDCG@10 exactly; the run oscillates in a 0.0384–0.0406 band from roughly epoch 30 onward (the comparator's own README notes run-to-run variability). The published 0.0406 that §5.2's pre-declared confirmation is measured against is therefore no longer only a transcribed constant: a local run of the generating code regenerates it under the unpinned shimmed research path, and our pre-declared CI lower bounds (0.04096 / 0.04083) sit above both its best (0.0406) and final (0.0391) local readings. **The Office_Products floor anomaly resolves**: their own SASRec configuration lands +13.9% above its published row here, crossing the published value at epoch 20 of 101 and never re-entering — which, combined with our floor run, decomposes the +44% floor-check failure entirely into published-row conservatism and baseline-strength protocol differences, leaving nothing attributable to our split or eval (resolution in Appendix A.0; the VOID is deliberately retained).

**Caveats (why these are regenerations, not reproductions).** Single runs (the reference code seeds only Python's `random`, so even in place it is not run-to-run deterministic); an unpinned environment (torch 2.11 vs pinned 2.2.2, transformers 5.7 vs 4.51, different cuBLAS/TF32 kernel versions); a different GPU than the comparator used; and the shims themselves — though the shim risk has since been closed on CPU: under the pinned torch 2.2.2 itself, the real `fbgemm-gpu(-cpu)==0.6.0` operators match our shims **bit-exactly (max abs diff 0.0, forward and gradient)** on every input the pinned binary accepts, the reference block under {pinned torch + real fbgemm} vs {pinned torch + shims} is bit-exact at every stage, and the remaining torch 2.2.2→2.11 block-level numerics drift is bounded at **4.8×10⁻⁷ per stage / 2.4×10⁻⁷ end-to-end**, with negative controls confirming the harness detects 1-ulp perturbations (`PINNED_ENV_PARITY_REPORT.md`); the pinned stack's *GPU* (cu121) kernel numerics remain the one locally untestable component. We therefore cite these as **environment-caveated single-run regenerations** and change no claim wording on their basis: §5.2's claim remains a point-estimate comparison against the published number.

### 5.7 Pre-declared fresh-seed hybrid: late fusion with a closed-form item-item model (E-F; adjudicated 2026-07-23; W-H-POS on all three categories)

**Provenance and system.** An author-operated side campaign (2026-07-22; outcome-visible development on historical seeds, disclosed as such) found that late score fusion of the frozen sequential stack with EASE (Steck 2019) — a closed-form linear item-item model fit on the *train split only* — improved MI test NDCG@10 on every historical seed. `PREREG_HYBRID_V1.md` (frozen and committed before launch, with its mechanical adjudicator) is the fresh-seed replication: per user, fused = z(seq) + w·z(EASE); (l2, w) selected on *validation only* from frozen grids; the fusion stage evaluates test once, at the selected pair (the underlying trainer additionally logs test curves at eval epochs under the pipeline's long-standing best-by-val protocol — a standing test exposure disclosed in §5.3 process disclosure (i), not a fusion-stage selection input); Completed per-seed fusion results were also read for operational monitoring before the full family finished; PREREG_HYBRID_V1 registered no no-interim clause, and the once-only adjudication ran after all files existed (disclosed). Five fresh seeds 20260721–25 per category; integrity gates all passed (per-seed reconstruction fidelity <0.0005 vs the recorded base result; frozen-grid membership; canonical n_eval; mechanical config equality to the per-category frozen reference), adjudicator exit 0.

**Result (frozen wording; 'pre-declared' replaces the prereg's synonym for the manuscript's uniform terminology).** Under the pre-declared fresh-seed replication (PREREG_HYBRID_V1, 5 seeds), late z-score fusion with a train-only EASE model changed test NDCG@10 by **+0.00244 [+0.00219, +0.00268]** on Musical_Instruments, **+0.00261 [+0.00211, +0.00310]** on Industrial_and_Scientific, and **+0.00317 [+0.00286, +0.00348]** on Video_Games. These are ordinary paired 95% CIs; the three paired-test raw p-values (MI 1.0×10⁻⁵, IS 1.3×10⁻⁴, VG 9.0×10⁻⁶) are all significant after Holm adjustment. Holm adjusts the p-values/decisions, not the intervals, and the significance statement attaches to fused-vs-sequential contrasts, never to a published comparator. The hybrid is a two-scorer system; published comparator numbers are single-scorer, single-run values, and every comparison below remains a point-estimate comparison under the environment caveats of §3. Fresh-seed sequential-only means for context: MI 0.04155, IS 0.03340, VG 0.06713.

**Published-comparator rows (frozen wordings).** The fused system's five-fresh-seed mean test NDCG@10 on Musical_Instruments, **0.04399**, exceeds the published single-run HSTU-BLaIR point estimate 0.0406 under our environment-caveated regeneration protocol (point-estimate comparison; no distributional claim). On Video_Games the fused five-fresh-seed mean, 0.07031, remains below the published single-run 0.0760. A five-checkpoint ensemble of the same frozen stack, fused with EASE under the same validation-only rule, scored **0.04557** on Musical_Instruments (single evaluation; ensemble frame — comparable only to other ensembles).

**Attribution and scope.** EASE is Steck (2019); z-score late fusion is standard. The local contribution is empirical: the measured complementarity between a text-augmented sequential scorer and a closed-form co-occurrence scorer under the 5-core LLOO full-catalog protocol, quantified under a frozen plan on fresh seeds. EASE alone is far weaker than the sequential model on these catalogs (side-campaign observation; the gain is complementarity, not a stronger component). The dense closed-form fit is infeasible at Office/CDs/Beauty catalog sizes; that scope exclusion was declared in the prereg, and a content-based third scorer that avoids the item-item inversion was subsequently studied at five-category scale (§5.8; outcome-visible, protocol-deviated — see its classification). Artifacts: results_{MI,IS,VG}_HYBRIDV1_base_seed*.json (+.fusion.json, per-user records), results_MI_HYBRIDV1_ensemble5.json, hybrid_v1_adjudication.json.


### 5.8 Sparse-warm text-fusion study on all five categories (E-G; outcome-visible, protocol-deviated; descriptive estimates, no pre-declared-confirmation status; a near-threshold redistribution, not cold start)

**Classification.** All 25 runs completed, but the campaign is outcome-visible and protocol-deviated. Interim endpoints were exposed, the literal frozen configuration gate fails on MI and VG, and the amended gate postdates outcome visibility. The literal failure governs; the amended PASS is a sensitivity only. A planned replication was also exposed before adjudication. Accordingly, every estimate below is descriptive and conditional on optimizer seeds over one repeatedly used split.

**System.** At evaluation time, a history-centroid text score is added to the sequential score and, where feasible, EASE. Text weights depend only on train-frequency bins and are selected on validation under an overall non-inferiority constraint. The text scorer fits no parameters, but the sequential and EASE components are trained or fit; this is not a training-free recommender.

The repository retains the as-launched gate, later sensitivity gates, their hashes, and the exact chronology. This preserves the defect without converting a post-outcome repair into a frozen decision.

**Descriptive result.** Tail-bin NDCG@10 changes were +0.00217 [0.00196, 0.00239] on MI, +0.00243 [0.00218, 0.00267] on IS, +0.00337 [0.00305, 0.00370] on VG, +0.00114 [0.00105, 0.00123] on Office, and +0.00481 [0.00472, 0.00490] on CDs. Overall changes were near zero. These intervals are retained as descriptive arithmetic, not as pre-declared confirmation.

The gain is entirely frequency 1–5; frequency-zero targets never change at rank 10. Mid and head means decline in every category, so this is a sparse-warm redistribution rather than free overall accuracy. All validation choices hit the text-weight grid ceiling, leaving the optimum unbracketed. With five seeds, the exact two-sided sign-test floor is 0.0625.

Evaluation-time content fusion is established prior art (Wang et al., 2024; Collins et al., 2025; TedRec; SimRec; Lichtenberg et al., 2025; Wang et al., 2025; Liu et al., 2023). We claim no architectural novelty for this element; it is retained only as a protocol-deviated redistribution study on fixed splits. Full operational chronology and artifacts are in the versioned supplement and repository.


## 6. Discussion

### 6.1 Interpretation

The main result is deliberately modular and narrowly identified.
Positive FIR–identity contrasts on three outcome-visible Amazon categories are joined by a positive, thresholded Software robustness contrast.
They show improvement only in those tested Amazon settings: the prospectively frozen MovieLens 1M study did not replicate learned FIR against identity or pointwise.
V3 improves the protocol chronology, but unverified non-visibility of earlier V2 validation output, same investigator/code lineage/Amazon family, and local custody keep it outcome-known and non-independent.
An equal-parameter current-position-only DCT/GELU placebo does not show a detected improvement over identity, and learned FIR exceeds it under matched initialization.
This discriminates learned FIR from that compound residual but does not isolate temporal access because basis/rank, activation, channel mixing, and temporal access change together.
The shared causal filter is also not separated from learned per-channel taps. On MovieLens, shared, grouped, and low-rank FIR arms met the noninferiority margin against learned FIR, but the learned-FIR effect gate failed; parsimony is therefore conditional coefficient-count compression rather than evidence of a useful or computationally cheaper module. No bypass implementation was tested, and measured end-to-end latency and memory did not materially improve.
The official-code WEARec feasibility run also scored below our existing full-model reference under the shared evaluator. The frozen AlphaFuse-style package scored above its zero-initialized upstream-class SASRec-ID control but below that same full-model reference. Together these outcomes improve current-baseline coverage while preserving the mixed ranking. They do not compare against the parser-default `Normal(0,1)` setting, equalize architecture/capacity/tuning, isolate null-space fusion, or supply independent confirmation.
The evidence supports neither uniquely learned FIR coefficients, a universal frequency-filter benefit, cross-domain generalization, nor a new end-to-end architecture.

The supporting text studies sharpen that boundary. Frozen text features add only +2.7% overall on Video_Games, and TAPE is sub-additive (+0.0009 in one seed; +0.0004 in the four-seed check). The repaired MI analysis finds a small frequency-5-heavy benefit rather than cold-start capability: zero-exposure targets receive no hits through rank 100, the exclude-boundary sensitivity is nonsignificant, and the MI−VG contrast does not replicate. In the Beauty_and_PC scan (Supplement S.1), the positive rows bundle BLaIR, richer text, and the MLP adaptor, while the single MiniLM Linear-to-MLP comparison shows no improvement. The scan therefore does not isolate whether encoder, content, projection, or their interactions account for the bundled difference.

### 6.2 Practical implications

The FIR residual is small, causal, and detachable: it can be initialized as the identity and added without changing the item scorer or evaluation protocol. MovieLens resource measurements show no practically meaningful accuracy-resource frontier for learned FIR in the tested setting; latency and peak-memory differences are small, hardware-specific, and subordinate to the failed effect gate. In this implementation, chunked full softmax makes 207k-item training feasible, cached item features substantially reduce evaluation cost, and right-padding with a causal-only mask avoids the NaN failure observed with the former masking path. Conversely, heavy dropout, removal of learned item embeddings, and simple subsequence augmentation did not transfer in the Beauty supporting study; these are observations under this pipeline, not general exclusions.

### 6.3 Claim limits and remaining tests

- **Comparator uncertainty.** The counted Musical_Instruments and Office V3 comparisons are against published single-run point estimates and an environment-matched single-run regeneration; no paired or distributional superiority over HSTU-BLaIR is claimed. The official end-to-end CUDA/Triton system cannot run on the local sm_120 GPU. Only the research block at an explicitly aligned configuration is numerically matched; trained-checkpoint and end-to-end equivalence are not claimed.
- **Historical, canonical, control, and frozen Software evidence.** Same-numbered historical arms were not initialization-paired, so their paired interpretations are withdrawn.
E-A used matched initialization but its frozen registered interval is Welch/Satterthwaite (the paired difference is descriptive); canonical breadth and active controls use ordinary paired intervals.
Those studies reused outcome-visible splits; the breadth categories were selected after favorable package outcomes and TEST was evaluated each epoch.
The six-arm final evaluation was sealed, but that campaign ran across a dirty evolving tree and its sidecars lacked independent custody because the ignore rule covered the wrong suffix.
Fixed MA/HP are algebraically redundant and shared/nonlinear arms prevent a learned-tap-specific claim.
The later pointwise-placebo protocol was precommitted and source-hash-bound but executed from a tracked-dirty tree; it adds only a learned-FIR-versus-compound-current-only contrast on outcome-known MI, not temporal isolation or per-channel necessity.
Software V3 used validation-only selection and sealed final evaluation, but V2-output non-visibility is not independently established; we classify it outcome-known/exploratory. Its local seals are hash-linked rather than immutable external custody, and its frozen tag has a disclosed raw-line-ending reference-hash replay defect.
Office V1 remains **VOID**; Office V3 supports only its frozen point-estimate wording.
- **Prospective MovieLens boundary.** The non-Amazon study improves selection chronology and TEST sequestration, but it is same-investigator and same-code-lineage on one dataset and one global-time split. Its negative verdict blocks a cross-domain FIR-benefit claim. Noninferiority of the parsimonious arms is conditional on the failed learned-FIR replication gate; it is not equivalence to identity, a deployment utility claim, or independent confirmation. User/item bootstrap intervals are fixed-dataset sensitivities. The public graph can recompute the released aggregate seed vectors but cannot independently replay non-redistributable MovieLens records or private endpoint files.
- **WEARec current-baseline boundary.** The official model/training code was run under the paper split, complete-history mask, full-catalog evaluator, cutoff, and tie rule after validation-only preset selection. The resulting `WEAREC-BELOW-EXISTING-REFERENCE` verdict is same-investigator evidence on an outcome-known split. Architecture, loss, schedule, and tuning budgets differ; the unpaired Welch contrast is descriptive, and neither independent confirmation nor a SOTA claim follows. The graph replays NDCG vector arithmetic, not private endpoint extraction or unreleased HR/MRR vectors.
- **AlphaFuse-style current-comparator boundary.** E-E V3 froze the official upstream representation and SASRec classes, shared training configuration, complete-history-masked evaluator, and eight fresh optimizer seeds per arm before launch. MiniLM-384 replaces the published AlphaFuse text vectors. The positive package-minus-ID interval is against a zero-initialized upstream-class SASRec-ID control, not the parser-default `Normal(0,1)` setting; official recipes may override initialization by dataset, so that parser setting is not a universal upstream default. Same-numbered seeds are not paired and the arms differ in text availability, initialization, trainable capacity, parameter allocation, and architecture. A parser-default-normal sensitivity and equal-budget factorial remain open. The negative package-minus-existing-reference interval is reported with equal prominence. Neither contrast isolates null-space fusion, reproduces a published AlphaFuse table, establishes equal tuning, supplies independent confirmation, or permits a SOTA claim. User/item bootstrap intervals are fixed-dataset sensitivities; the public graph validates their recorded aggregate schema/intervals and checks only ledger shape, hash-string syntax, and uniqueness. It cannot read or hash private endpoints/sidecars or replay record-level resampling.
- **Tail and probe scope.** The tail result is AR2023-specific, small in absolute terms, concentrated at train frequency 5, and not replicated on a non-Amazon domain. The original cohorts mixed exposure regimes and split frequency ties; TFV2 repaired those estimands but was outcome-visible and is not classified as confirmatory. Most capacity probes are single-seed screens, and nonsignificance is never interpreted as equivalence.
- **Open controls.** Item-text permutation and objective/target-multiplicity parity controls remain unrun, so the small text-stack gain cannot yet be attributed entirely to semantic alignment. The thinning studies intervene synthetically on one fixed draw and do not identify the real-world data-generating process.
- **Provenance and input scope.** One confirmation campaign ran at a documentation-only descendant of its frozen commit; code hashes and empty protocol-file diffs support code identity, but the literal commit-equality deviation remains disclosed. The canonical model consumes only item IDs, timestamps, and frozen item-text embeddings—never outputs or representations from a comparator model.

## 7. Conclusion

This paper contributes a narrow causal-filter module and an evaluation discipline for
testing it. The discipline combines git-frozen protocols, a fail-closed artifact graph,
environment-caveated comparator regeneration, and symmetric adjudication. Its value is
illustrated by the Office_Products V1 campaign: its own floor check VOIDed the comparison,
and that verdict remains in the record even though a redesigned protocol later passed on
fresh seeds.

The main empirical result is a family of identity-initialized, gradient-active, strictly
left-causal residual modules. Learned FIR–identity estimates are positive on
Musical_Instruments (+0.002265, ordinary Welch 95% CI [0.001928, 0.002602]),
Industrial_and_Scientific (+0.002110 [0.001820, 0.002399]), and CDs_and_Vinyl
(+0.006150 [0.005849, 0.006450]), but these are outcome-visible internal estimates.
A separately frozen Software robustness attempt found learned FIR−identity
+0.005062 [+0.004591, +0.005533], with 8/8 positive paired differences and the
ordinary 95% CI lower bound above its pre-declared +0.000500 reporting threshold.
Because earlier V2 validation-output non-visibility is not independently established and
the work remains same-investigator, same-code-lineage, same-Amazon-family under local
same-user custody, it is outcome-known robustness rather than independent confirmation.
In the active-control study, every trainable left-causal arm improves frozen identity; learned taps
beat the redundant fixed-filter parameterizations but are not separated from the shared causal
filter or parameter-matched nonlinear causal control. In the subsequent equal-parameter
current-position-only placebo study, pointwise minus identity is −0.000069
[−0.000200, +0.000061], while learned FIR minus pointwise is +0.001941
[+0.001788, +0.002095]. This discriminates learned FIR from that compound
current-only residual in outcome-known MI, but does not isolate temporal access.
In the prospectively frozen MovieLens 1M study, however, learned FIR did not replicate
against identity (+0.000000 [−0.000074, +0.000075], `p_Holm=.995`) or pointwise
(+0.000035 [−0.000057, +0.000127], `p_Holm=.796`). Shared, grouped, and low-rank
arms met the pre-declared noninferiority margin against learned FIR only conditionally:
the learned-FIR effect gate failed. The evidence therefore supports neither unique
necessity of learned per-channel FIR coefficients, a general FIR benefit,
superiority over the stronger external reference, nor independent cross-category confirmation.

The official-code WEARec current-baseline campaign reached mean NDCG@10 0.059184
[0.058674, 0.059693], below the existing six-seed full-model reference 0.067337
[0.067063, 0.067611]; the descriptive unpaired contrast was −0.008154
[−0.008689, −0.007618]. This closes only the narrow official-code/equal-evaluation
feasibility check. It does not equalize architectures, losses, schedules, or tuning
budgets and is not independent confirmation or SOTA evidence.

The frozen AlphaFuse-style current-comparator campaign reached NDCG@10 0.048273
[0.048129, 0.048416], above a zero-initialized upstream-class SASRec-ID control at 0.039024
[0.038106, 0.039941] by +0.009249 [+0.008329, +0.010169], but below the existing
full-model reference by −0.019065 [−0.019347, −0.018783]. This countable mixed result
supports the value of the tested whole representation package over that ID backbone;
it does not isolate null-space fusion, equalize architecture/capacity/tuning, reproduce
AlphaFuse's published text setting, or provide independent confirmation or SOTA evidence.

The secondary result is narrower. Frozen text features improve the repaired
Musical_Instruments frequency-tail endpoint (+0.000420 [0.000181, 0.000660]), but the gain
concentrates at train frequency 5; removing that boundary group leaves no detected effect.
The corresponding cross-dataset contrast is nonsignificant, and thinning interventions do
not identify a tail mechanism. We therefore report a dataset-specific frequency-5 case,
not a general cross-dataset result. TAPE, late fusion, sparse-warm redistribution, and the probe
screen are supporting or descriptive studies, not additional headline contributions.

The evidence has important limits: uncertainty is over optimizer seeds on reused fixed
splits; comparator uncertainty is not distributionally matched; several campaigns are
outcome-visible or protocol-deviated; and no item-text permutation control, temporal split
replication, or deployment study has been completed. The defensible contribution is thus
modular rather than architectural: a small causal FIR realization, its measured internal
effect under the stated protocol, and an auditable record that preserves nulls, deviations,
and VOID outcomes alongside positive results.

## 8. Code and Data Availability

Code, frozen protocols, result artifacts, and build scripts are public at
https://github.com/Ray0419/bestrec-sota-results. The tracked
`RELEASE_MANIFEST.json` binds source code, split derivatives, text caches, result JSONs,
released per-user sidecars, and the pinned HSTU-BLaIR submodule by SHA-256. Running
`bootstrap_public_clone.py` fetches and verifies release-class assets; running
`rebuild_hstu_submission.py --strict` then checks HSTU parity, recomputes the 200
artifact-gated cells, verifies the manifest, and executes every governed adjudicator.
The numerical graph and release manifest have different scopes: every declared empirical
cell is graph-bound, but not every transitive graph source is separately enumerated in the
release manifest. Table 0's literature attribution remains citation-checked authored
prose, but its quantitative FIR fields are generated from active graph cells and the
strict rebuild verifies the generated region. Table 0 is not a separate numerical graph
family. We make no broader "every printed claim is hash-manifested" claim.

MovieLens 1M record rows, transformed splits, checkpoints, endpoint files, and
per-user sidecars are not redistributed under the ML-1M README. The public release
contains the frozen acquisition/training/evaluation code, source and split hashes,
aggregate seed vectors/statistics, and adjudication. Consequently, the public graph
recomputes the aggregate MovieLens claims but cannot independently replay the private
record-level endpoint extraction.

The WEARec release contains the frozen official-code adapter, validation-only selection
record, eight-seed aggregate adjudication, reference-vector identities, and private
endpoint hashes. Its graph cell independently recomputes the released NDCG summaries and
descriptive Welch arithmetic. Checkpoints, sealed endpoint files, and per-user sidecars
remain private, and HR/MRR raw-vector arithmetic is therefore not publicly replayed.

The public `v0.9-audit-evidence` release is the working evidence store. Historical
campaigns for which checkpoints or per-user records were not retained are labeled as such
and require regeneration for rank-level reconstruction. Raw Amazon Reviews 2023 archives
are not redistributed; derived splits are tied to their public source and preprocessing
code by hashes. Local-only audit sidecars are outside every printed claim and are
precommitted by digest for reviewer access. A new archival deposit will be cut only after
the manuscript, author metadata, licenses, and clean-clone build are finalized; the older
`v1.1.11-deposit` tag is retained as a historical boundary, not represented as current.

## 9. Acknowledgments

We thank the Amazon Reviews 2023 maintainers (Hou et al., 2024) for releasing the dataset and accompanying reference implementations. The MLP adaptor design used in our best variant is from their published SASRecText configuration. We also acknowledge the GroupLens Research Group for making MovieLens 1M available for research and cite its dataset history (Harper & Konstan, 2015); no endorsement by GroupLens or the University of Minnesota is implied.

## 10. Ethics and Data Governance

This work uses two pre-existing research datasets: **Amazon Reviews 2023** (Hou et al., 2024; McAuley Lab) and **MovieLens 1M** (Harper & Konstan, 2015; GroupLens). For Amazon Reviews 2023, the maintainers state publicly that they are not in a position to assign a license or dictate usage terms; **that statement is not an affirmative permission grant, and we do not treat it as one**. We redistribute derived Amazon interaction-split CSVs (never the raw dataset) with attribution on the basis of the dataset's public research availability, will remove them on maintainer, platform, or venue request, and flag the redistribution basis for venue-level review rather than asserting a legal right. Scope of Amazon data actually consumed: interaction tuples (pseudonymous user identifiers — remapped to dense
integers by our preprocessing — item identifiers, and timestamps) and **item metadata text**
(titles, categories, and store/seller name — the AR2023 `store` field; an earlier label said "brand", corrected 2026-07-20: the frozen cache text template's literal `brand:` prefix is retained as-is inside the cached strings and documented as a misnomer, because regenerating the caches would invalidate every frozen-text result) for the frozen text encoders. We do **not** process review text
bodies, ratings-as-text, or product images, and we make no attempt at re-identification of any
user. Released artifacts follow the same boundary: per-user evaluation sidecars contain only
remapped integer IDs, target item IDs, and rank outcomes; the raw dataset is **not
redistributed** (our releases carry SHA256 hashes and regeneration scripts instead,
`RELEASE_MANIFEST.json`).

For MovieLens 1M, acquisition downloaded the official ZIP and retained it only in private local storage; the study parsed **only `ratings.dat`** (`UserID`, `MovieID`, whole-star `Rating`, and `Timestamp`) and did not consume `users.dat` demographics or `movies.dat` metadata. The experiment thresholded ratings at 4 for its primary view and also reported an all-ratings sensitivity. In accordance with the MovieLens 1M README, neither the archive, transformed record rows, split files, checkpoints, endpoints, nor per-user sidecars are redistributed. The public release contains acquisition/training/evaluation code, source and split hashes, aggregate seed vectors/statistics, and the adjudication only. MovieLens data are used solely for non-commercial research; no GroupLens or University of Minnesota endorsement is stated or implied. The maintainer must review institutional retention, deletion, access-control, and legal requirements before final deposit; the repository does not claim that technical hash controls substitute for that review.

No new data was collected and no interaction with human subjects took
place. Amazon Reviews 2023 is publicly accessible, platform-pseudonymized product-review data; MovieLens 1M is separately governed ratings data subject to the restrictions stated above. No institutional review determination was sought or is claimed, and we do not infer any jurisdiction's requirements; ACM policy places responsibility for applicable institutional, ethical, and legal compliance on authors, and we accept it, with this section's factual basis available as supporting documentation on request. **Released Amazon sidecar identifier surface, stated exactly:** those per-user sidecars carry our preprocessing's dense remapped user indices (`user_id` 0, 1, 2, …), a target-item index, and rank outcomes — not hashes. The dense indices are deterministically linkable to the platform's pseudonymous identifiers through the released Amazon split CSVs, so the sidecars are exactly as pseudonymous as that public dataset, no more; MovieLens per-user sidecars are not released. Released Amazon derivatives are retained under the tagged GitHub release; requests to remove affected Amazon assets will be handled by deleting them and regenerating the release manifest. MovieLens retention and deletion remain governed by its separate private-data review above. Finally, this is an offline evaluation
study: recommender systems deployed on such data can amplify popularity and exposure biases —
our long-tail analyses quantify one aspect of that concern — and nothing in this paper
constitutes a deployment claim.

## References

- Abbasi, S., Shah, S. M., Shaikh, R., Aljawarneh, M., 2026. SISA-Rec: A Semantically Integrated Sequential Recommender with Contrastive Alignment. arXiv:2607.11168. *(concurrent modular semantic-integration work on Amazon Reviews 2014; protocol-family coverage only, §2.3)*
- Yoon, Y. C., Park, C., Koh, K., 2026. Sensory-Aware Sequential Recommendation via Review-Distilled Representations. arXiv:2603.02709. *(concurrent ASER content module on Amazon Reviews 2014; protocol-family coverage only, §2.3)*



- Anelli, V. W., Bellogín, A., Ferrara, A., Malitesta, D., Merra, F. A., Pomo, C., Donini, F. M., Di Noia, T., 2021. Elliot: A Comprehensive and Rigorous Framework for Reproducible Recommender Systems Evaluation. SIGIR. *(reproducible-evaluation framework; §2.3 apparatus positioning)*
- Baik, J., Ben Arous, G., Péché, S., 2005. Phase Transition of the Largest Eigenvalue for Nonnull Complex Sample Covariance Matrices. Annals of Probability. *(annotation removed: the figure this supported is retracted)*
- Bellogín, A., Said, A., 2021. Improving Accountability in Recommender Systems Research Through Reproducibility. User Modeling and User-Adapted Interaction. *(accountability-workflow precedent; §2.3)*
- Brody, S., Lagziel, S., 2024. SimRec: Mitigating the Cold-Start Problem in Sequential Recommendation by Integrating Item Similarity. RecSys 2024 CARS workshop; arXiv:2410.22136. *(text similarity for rare/unseen items; §2.3 novelty boundary)*
- Chen, J., Wu, W., Shi, L., Ji, Y., Hu, W., Chen, X., Zheng, W., He, L., 2022. Self-Attentive Sequential Recommendation with Cheap Causal Convolutions. arXiv:2211.01297. *(causal convolution + self-attention precedent; §2.3)*
- Collins, L., Kumar, B., Ju, C. M., Zhao, T., Loveland, D., Neves, L., Shah, N., 2025. Exploiting ID-Text Complementarity via Ensembling for Sequential Recommendation. arXiv:2512.17820. *(ID/text ensembling; §5.8 positioning)*
- Ding, H., Ma, Y., Deoras, A., Wang, Y., Wang, H., 2021. Zero-Shot Recommender Systems (ZESRec). arXiv:2105.08318. *(pre-UniSRec text-based sequential recommendation precedent; §2)*
- Du, X., Yuan, H., Zhao, P., Qu, J., Zhuang, F., Liu, G., Liu, Y., Sheng, V. S., 2023. Frequency Enhanced Hybrid Attention Network for Sequential Recommendation (FEARec). SIGIR. *(the broader frequency/time-frequency SR line, §2.3)*
- Efron, B., Morris, C., 1973. Stein's Estimation Rule and Its Competitors — an Empirical Bayes Approach. JASA. *(negative-result map: James–Stein shrinkage probe)*
- Ferrari Dacrema, M., Boglio, S., Cremonesi, P., Jannach, D., 2021. A Troubling Analysis of Reproducibility and Progress in Recommender Systems Research. ACM Transactions on Information Systems 39(2). *(journal extension of the evaluation-trust analysis, §2; metadata verified against the arXiv listing 1911.07698 on 2026-07-13)*
- Ferrari Dacrema, M., Cremonesi, P., Jannach, D., 2019. Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches. RecSys. *(the evaluation-trust line motivating our apparatus, §1, §2; metadata verified against the arXiv listing 1907.06902 and dblp on 2026-07-13)*
- Gavish, M., Donoho, D. L., 2014. The Optimal Hard Threshold for Singular Values is 4/√3. IEEE Transactions on Information Theory. *(formerly cited by the retracted spectral figure; retained for the retraction record only)*
- Guo, Z., Hou, Y., Ju, C. M., Shah, N., McAuley, J., 2026. MLPs are Efficient Distilled Generative Recommenders (SID-MLP). arXiv:2605.12617. *(AR2023 5-core LLOO, same MI/VG dataset statistics)*
- He, P., Gan, Y., Dai, T., Lin, R., Li, X., Liu, Y., Liu, Q., 2026. Exploiting Inter-Session Information with Frequency-enhanced Dual-Path Networks for Sequential Recommendation (FreqRec). AAAI 40(17), 14820–14828. doi:10.1609/aaai.v40i17.38502. *(current frequency-domain comparator line; §2.3)*
- He, R., McAuley, J., 2016. Ups and Downs: Modeling the Visual Evolution of Fashion Trends with One-Class Collaborative Filtering. WWW. *(source of the Amazon 2014 Beauty subset used by TIGER/LIGER)*
- He, Y., Liu, X., Zhang, A., Ma, Y., Chua, T.-S., 2025. LLM2Rec: Large Language Models Are Powerful Embedding Models for Sequential Recommendation. KDD 2025. arXiv:2506.21579. doi:10.1145/3711896.3737029.
- Harper, F. M., Konstan, J. A., 2015. The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems 5(4), Article 19. doi:10.1145/2827872. *(MovieLens 1M source and context; §4.1, §5.2)*
- Hou, Y., He, Z., McAuley, J., Zhao, W. X., 2023. Learning Vector-Quantized Item Representation for Transferable Sequential Recommenders (VQ-Rec). WWW. *(PQ-code item representations; TAPE novelty boundary, Table 0)*
- Hou, Y., Kim, H., Ju, C. M., Escoto, E., Shah, N., McAuley, J., 2026. Expressiveness Limits of Autoregressive Semantic ID Generation in Generative Recommendation (Latte). arXiv:2605.06331. *(AR2023 5-core LLOO, same MI/VG dataset statistics; the MI/VG NDCG@10 values quoted in §5.1 are verified against its Table 1)*
- Hou, Y., Li, J., Fu, X., He, Z., Yan, A., Chen, X., McAuley, J., 2026. Bridging Language and Items for Retrieval and Recommendation: Benchmarking LLMs as Semantic Encoders. ACL. *(the later, expanded publication; cited separately from the v1 checkpoint pin)*
- Hou, Y., Li, J., He, Z., Yan, A., Chen, X., McAuley, J., 2024. Bridging Language and Items for Retrieval and Recommendation (BLaIR). arXiv:2403.03952. *(cited at arXiv v1 for checkpoint/configuration facts — the artifacts we consume)*
- Hou, Y., Mu, S., Zhao, W. X., Li, Y., Ding, B., Wen, J.-R., 2022. Towards Universal Sequence Representation Learning for Recommender Systems (UniSRec). KDD. *(author list corrected 2026-07-19; an earlier entry wrongly carried the VQ-Rec author list)*
- Hu, G., Zhang, A., Liu, S., Cai, Z., Yang, X., Wang, X., 2025. AlphaFuse: Learn ID Embeddings for Sequential Recommendation in Null Space of Language Embeddings. Proceedings of SIGIR 2025, pp. 1614–1623. doi:10.1145/3726302.3729894. *(closest frozen-text+ID comparator; V2 is noncountable, while V3 is outcome-known whole-package current-comparator evidence — §2.3)*
- Hu, J., Zhou, W., Liao, J., Zhu, J., Wen, J., Zhang, H., 2026. Balanced Frequency Decoupling: Energy-Aware Multi-Scale Preference Modeling for Sequential Recommendation (BFDRec). SIGIR. *(closest frequency-domain line; §2.3)*
- Huang, C., Gao, T., Huang, H., Sheng, Q. Z., Yao, L., 2026. Beyond Item Order: Temporal Gap Tokenization for Generative Recommendation with Semantic IDs (ChronoSID). arXiv:2607.03918. *(SID-line MI comparator context; own filtered universe)*
- Huang, W.-H., Ke, C.-W., Chiu, W.-N., Su, Y.-X., Yang, C.-C., Cheng, C.-Y., Chen, Y.-N., Cheng, P.-J., 2025. Augment or Not? A Comparative Study of Pure and Augmented Large Language Model Recommenders. arXiv:2505.23053. *(AR2023 MI / Industrial_and_Scientific 5-core LOO LLM-recommender benchmark; non-interchangeable protocol, §5.1)*
- James, W., Stein, C., 1961. Estimation with Quadratic Loss. 4th Berkeley Symp. *(with Stein, C., 1956, 3rd Berkeley Symp.)*
- Jiang, J., Zhang, P., Luo, Y., Li, C., Kim, J. B., Zhang, K., Wang, S., Xie, X., Kim, S., 2023. AdaMCT: Adaptive Mixture of CNN-Transformer for Sequential Recommendation. CIKM. *(local convolution + attention; §2.3)*
- Jiang, J., Wu, Y., Li, Q., Xiong, Y., Su, Y., Huo, J., Lu, L., Zhang, J., Yu, H., 2026. DiffuReason: Bridging Latent Reasoning and Generative Refinement for Sequential Recommendation. arXiv:2602.09744. *(AR2023 "Video & Games" under different filtering/statistics; cited to flag non-comparability, §5.1)*
- Jiang, Y., Ren, X., Xia, L., Luo, D., Lin, K., Huang, C., 2025. RecGPT: A Foundation Model for Sequential Recommendation. EMNLP. *(zero-shot transfer + short-history cold-start; §2.3 distinction)*
- Kang, W.-C., McAuley, J., 2018. Self-Attentive Sequential Recommendation (SASRec). ICDM.
- Kim, H.-y., Choi, M., Lee, S., Baek, I., Lee, J., 2025. DIFF: Dual Side-Information Filtering and Fusion for Sequential Recommendation. SIGIR. *(learnable filtering line; §2.3)*
- Kim, K., Hyun, D., Yun, S., Park, C., 2023. MELT: Mutual Enhancement of Long-Tailed User and Item for Sequential Recommendation. SIGIR. *(long-tail method; earlier-stage proxy experiments, non-canonical track)*
- Elsayed, S., Le, N. S., Rashed, A., Schmidt-Thieme, L., 2026. Rethinking Convolutional Networks for Attribute-Aware Sequential Recommendation (ConvRec). Accepted at IJCAI–ECAI 2026; arXiv:2605.04723. doi:10.48550/arXiv.2605.04723. *(hierarchical strided-convolution operator line; §2.3)*
- Lee, D., Kim, H.-y., Lee, J., 2026. ACE: Anisotropy-Controllable Embedding for LLM-enhanced Sequential Recommendation. SIGIR. *(bounds our negative map to implementation/environment scope; §2.3)*
- Li, J., Han, H., Chen, Z., Shomer, H., Jin, W., Javari, A., Liu, H., 2025. Enhancing ID and Text Fusion via Alternative Training in Session-based Recommendation (AlterRec). IJCNLP-AACL. *(naive ID/text fusion failures; §2.3)*
- Li, J., Wang, M., Li, J., Fu, J., Shen, X., Shang, J., McAuley, J., 2023. Text Is All You Need: Learning Language Representations for Sequential Recommendation (RecFormer). KDD. *(closest language-representation SR line incl. cold-start evaluation; §2)*
- Li, J., Wang, Y., McAuley, J., 2020. Time Interval Aware Self-Attention for Sequential Recommendation (TiSASRec). WSDM. *(time-interval attention; time-bias attribution, Table 0)*
- Liang, Y., Zhang, Z., Zhu, Y., Zhang, K., Guo, Z., Zhou, W., Yang, Z., Wu, K., Ni, Y., Zeng, A., Fu, C., Wang, J., Xia, J., 2026. Rethinking Generative Recommender Tokenizer: Recsys-Native Encoding and Semantic Quantization Beyond LLMs (ReSID). arXiv:2602.02338. *(SID-line MI comparator context; own filtered universe)*
- Lichtenberg, J. M., De Candia, A., Ruffini, M., 2025. DenseRec: Revisiting Dense Content Embeddings for Sequential Transformer-based Recommendation. EARL@RecSys. *(dense content for unseen items; §5.8 positioning)*
- Liu, C., Li, X., Cai, G., Dong, Z., Zhu, H., Shang, L., 2021. Noninvasive Self-attention for Side Information Fusion in Sequential Recommendation (NOVA). AAAI. *(early-fusion harm; §2.3 scope)*
- Liu, C., Lin, J., Wang, J., Liu, H., Caverlee, J., 2024. Mamba4Rec: Towards Efficient Sequential Recommendation with Selective State Space Models. arXiv:2403.03900. doi:10.48550/arXiv.2403.03900. *(selective state-space and local-convolution operator line; §2.3)*
- Liu, Y., Wang, T., Ma, Y., 2025. TimeWeaver: Time-Aware Sequential Recommender System via Dual-Stream Temporal Network. Systems 13(10), Article 857. doi:10.3390/systems13100857. *(large-kernel convolution plus dual temporal/EMA streams; §2.3)*
- Liu, H., Deng, Z., Wang, L., Peng, J., Feng, S., 2023. Distribution-based Learnable Filters with Side Information for Sequential Recommendation (DLFS-Rec). RecSys. *(learnable filtering line; §2.3)*
- Liu, J., Li, L., Li, Z., Hu, K., Shi, K., Yuan, J., 2026. Hyena Operator for Fast Sequential Recommendation (HyenaRec). WWW. doi:10.1145/3774904.3792716. *(polynomial long-convolution and gated short-term operator line; §2.3)*
- Liu, P., Ji, Z., Yan, G., 2026. WPGRec: Wavelet Packet Guided Graph Enhanced Sequential Recommendation. SIGIR 2026 (accepted; arXiv:2604.21305). *(representative of the later frequency/time-frequency SR line invoked in §2.3)*
- Liu, Q., Wu, X., Wang, Y., Zhang, Z., Tian, F., Zheng, Y., Zhao, X., 2024. LLM-ESR: Large Language Models Enhancement for Long-tailed Sequential Recommendation. NeurIPS 2024 (spotlight). arXiv:2405.20646.
- Liu, T., Gao, C., Wang, Z., Li, D., Hao, J., Jin, D., Li, Y., 2023. Uncertainty-aware Consistency Learning for Cold-Start Item Recommendation. SIGIR. *(cold/warm utility precedent; §5.8 positioning)*
- Liu, Y., 2025. HSTU-BLaIR: Lightweight Contrastive Text Embedding for Generative Recommender. KDD 2025 Workshop on LLMs for E-Commerce; arXiv:2504.10545. *(the external AR2023 5-core reference family: Video_Games 0.0760, Musical_Instruments 0.0406, Office_Products 0.0271; the pinned environment is not installable on our hardware — the research path was executed locally via data-movement shims, §5.6, regenerating the Musical_Instruments row)*
- Luo, J., Zhang, W., Zhang, X., Fang, Y., 2026. Time-Aware Adaptive Side Information Fusion for Sequential Recommendation (TASIF). WSDM; arXiv:2512.24246. *(learnable filter + gate + fusion; §2.3)*
- Marchenko, V. A., Pastur, L. A., 1967. Distribution of Eigenvalues for Some Sets of Random Matrices. Matematicheskii Sbornik. *(formerly cited by the retracted spectral figure; retained for the retraction record only)*
- Melchiorre, A. B., Rekabsaz, N., Ganhör, C., Schedl, M., 2022. ProtoMF: Prototype-based Matrix Factorization for Effective and Explainable Recommendations. RecSys. *(prototype methods; TAPE novelty boundary, Table 0)*
- Petrov, A., Macdonald, C., 2022. A Systematic Review and Replicability Study of BERT4Rec for Sequential Recommendation. RecSys. *(reproduction-audit precedent; §2.3)*
- Rajput, S. et al., 2023. Recommender Systems with Generative Retrieval (TIGER). NeurIPS.
- Reimers, N., Gurevych, I., 2019. Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP.
- Shaw, P., Uszkoreit, J., Vaswani, A., 2018. Self-Attention with Relative Position Representations. NAACL. *(relative-position attention bias)*
- Shin, Y. et al., 2024. An Attentive Inductive Bias for Sequential Recommendation beyond the Self-Attention (BSARec). AAAI. arXiv:2312.10325. *(bidirectional FFT filter; our causal-filter adaptation)*
- Shin, Y., Choi, J., Kim, S., Park, N., 2025. TV-Rec: Time-Variant Convolutional Filter for Sequential Recommendation. NeurIPS. *(position-specific time-variant filter replacing fixed kernels and self-attention; §2.3)*
- Shyam, A., Kagita, V. R., Rana, B., Kumar, V., 2026. GrIT: Group Informed Transformer for Sequential Recommendation. arXiv:2602.19728. *(AR2023 5-core Video_Games statistics match ours; full-item-set ranking; the NDCG@10 0.0588 quoted in §5.1 is its published value)*
- Steck, H., 2019. Embarrassingly Shallow Autoencoders for Sparse Data. WWW. *(EASE; the closed-form item-item scorer in the §5.7 pre-declared hybrid)*
- Sun, F. et al., 2019. BERT4Rec: Sequential Recommendation with Bidirectional Encoder Representations from Transformer. CIKM.
- Sun, Z., Fang, H., Yang, J., Qu, X., Liu, H., Yu, D., Ong, Y.-S., Zhang, J., 2022. DaisyRec 2.0: Benchmarking Recommendation for Rigorous Evaluation. TPAMI; arXiv:2206.10848. *(rigorous-evaluation benchmark; §2.3)*
- Sun, Z., Yu, D., Fang, H., Yang, J., Qu, X., Zhang, J., Geng, C., 2020. Are We Evaluating Rigorously? Benchmarking Recommendation for Reproducible Evaluation and Fair Comparison. RecSys. *(standardized-benchmarking response to the evaluation-trust problem, §2; metadata verified against dblp on 2026-07-13)*
- Szegedy, C. et al., 2016. Rethinking the Inception Architecture for Computer Vision. CVPR. *(label smoothing)*
- Tang, J., Wang, K., 2018. Personalized Top-N Sequential Recommendation via Convolutional Sequence Embedding (Caser). WSDM. *(convolutional SR prior art; FIR novelty boundary, §2.3/Table 0)*
- Volkovs, M., Yu, G., Poutanen, T., 2017. DropoutNet: Addressing Cold Start in Recommender Systems. NeurIPS. *(cold-start baseline; earlier-stage experiments, non-canonical track)*
- Wang, H., Lian, J., Wu, M., Li, H., Fan, J., Xu, W., Li, C., Xie, X., 2023. ConvFormer: Revisiting Transformer for Sequential User Modeling. arXiv:2308.02925.
- Wang, S., Ding, H., Gu, Y., Aydore, S., Kalantari, K., Kveton, B., 2024. Language-Model Prior Overcomes Cold-Start Items. arXiv:2411.09065. *(LM similarity prior for cold start; §5.8 positioning)*
- Wang, W. et al., 2020. MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers. NeurIPS. arXiv:2002.10957.
- Wang, Y., Pan, J., Li, X., Wang, M., Wang, Y., Liu, Y., Liu, D., Jiang, J., Zhao, X., 2025. Empowering Large Language Model for Sequential Recommendation via Multimodal Embeddings and Semantic IDs. CIKM. *(frequency-aware multimodal fusion; §5.8 positioning)*
- Wei, Y., Wang, X., Li, Q., Nie, L., Li, Y., Li, X., Chua, T.-S., 2021. Contrastive Learning for Cold-Start Recommendation (CLCRec). ACM MM. *(cold-start baseline; earlier-stage experiments, non-canonical track)*
- Wei, Z., Dang, Y., Guo, G., Zhao, C., Sun, Z., 2026. Fusion and Alignment Enhancement with Large Language Models for Tail-item Sequential Recommendation (FAERec). arXiv:2604.03688.
- Wijmans, E., Huval, B., Hertzberg, A., Koltun, V., Krähenbühl, P., 2025. Cut Your Losses in Large-Vocabulary Language Models. ICLR. *(memory-efficient exact-CE precedent; §3.5)*
- Xie, Y., Zhou, P., Kim, S., 2022. Decoupled Side Information Fusion for Sequential Recommendation (DIF-SR). SIGIR. *(early-fusion limitations; §2.3 scope)*
- Xu, H., Yuan, H., Liu, G., Fang, J., Zhao, L., Zhao, P., 2026. Wavelet Enhanced Adaptive Frequency Filter for Sequential Recommendation (WEARec). AAAI 40(19), 16058–16065. doi:10.1609/aaai.v40i19.38640. *(current adaptive frequency/wavelet comparator line; §2.3)*
- Xu, L., Tian, Z., Li, B., Zhang, J., Wang, J., Cai, M., Zhao, W. X., 2024. Sequence-level Semantic Representation Fusion for Recommender Systems (TedRec). arXiv:2402.18166. *(frequency-domain text-ID fusion; §2.3)*
- Yang, L., Paischer, F., Hassani, K., Li, J., Shao, S., Li, Z. G., He, Y., Feng, X., Noorshams, N., Park, S., Long, B., Nowak, R. D., Gao, X., Eghbalzadeh, H., 2024. Unifying Generative and Dense Retrieval for Sequential Recommendation (LIGER). arXiv:2411.18814. doi:10.48550/arXiv.2411.18814.
- Yuan, F., Karatzoglou, A., Arapakis, I., Jose, J. M., He, X., 2019. A Simple Convolutional Generative Network for Next Item Recommendation (NextItNet). WSDM. *(dilated causal-convolution SR prior art; FIR novelty boundary, §2.3/Table 0)*
- Zhai, J. et al., 2024. Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations (HSTU). ICML. *(the published architecture our HSTU-style pure-PyTorch implementation is based on)*
- Zhang, L., Zhou, X., Zeng, Z., Shen, Z., 2024. Dual-View Whitening on Pre-trained Text Embeddings for Sequential Recommendation (DWSRec). AAAI. *(anisotropy treatment of text embeddings; §2.3)*
- Zheng, Y., Liu, S., Li, Z., Wu, S., 2021. Cold-start Sequential Recommendation via Meta Learner (Mecos). AAAI. *(few-interaction new-item cold start; §2.3 distinction)*
- Zhou, D., Pan, W., Ming, Z., 2026. LLM-based Semantic and ID Representations for Sequential Recommendation (SIDSRec). SIGIR. *(semantic/ID channel separation; §2.3)*
- Zhou, K. et al., 2022. Filter-enhanced MLP is All You Need for Sequential Recommendation (FMLP-Rec). WWW. arXiv:2202.13556. *(bidirectional learnable frequency filter; our causal-filter adaptation)*
## Appendix A.0 — Office_Products: descriptive evidence (VOID under its pre-declaration)

**Second-category pre-declared confirmation: Office_Products.** To test whether the per-category result generalizes, we froze a second pre-declaration (`SOTA_CONFIRM_PREREG_OFFICE.md`, committed before the raw data finished downloading — before any Office statistic was knowable) with the config carried over from Musical_Instruments **unchanged (zero category-specific tuning)** and fresh seeds 20260623–27. Dataset parity is exact (items 77,551 and users 223,308 match the comparator paper exactly; interactions differ by one, as on MI). Result, on final-epoch full-catalog evaluations (223,308 users; the prereg's declared headline rule): **K=16 = 0.03042 ± 0.00008 (95% CI lower bound 0.03032) and K=8 = 0.03033 ± 0.00018 (CI-LB 0.03010), all 10 fresh seeds above the published HSTU-BLaIR point estimate 0.0271** — a ~+12% margin, versus +2.3% on MI. **However, the pre-declared floor check FAILED: our plain-SASRec floor (0.02208) lands +44% ABOVE the published SASRec (0.0153), violating the prereg's comparability condition. Under the pre-declaration as written, the Office second-category pass is therefore VOID — the gate values are reported as a provisional, non-confirmatory result — the matched comparator-baseline run that explains the floor gap is complete and explains it (resolution paragraph below); the VOID stands.** **The V1 Office campaign counts in no claim.** (It leaves the pre-declared Musical_Instruments confirmation of §5.2 untouched, and the separately pre-declared, redesigned **V3** campaign — environment-matched reference, fresh never-inspected seeds — later **passed** and is counted strictly under its frozen per-category point-estimate wording, §5.2. The V1 VOID stands unchanged.) Disclosures: best-by-val checkpoints were evaluated on a 30k-user subsample (declared in the prereg), so the headline uses the always-full final-epoch eval — the conservative choice (the subsampled best-checkpoint numbers were higher); the run manifests carry a dirty-tracked flag caused by the driver's own results-file appends (embedded per-run code hashes verify protocol-code identity); our plain-SASRec floor (0.0221) lands above their published SASRec (0.0153) on this category — a baseline-config-strength difference, with split parity resting on the exact dataset-statistics identity and frozen hashes rather than the floor heuristic; and the pre-declared tail prediction for Office was scored **VOID** (its connectivity 2.89 falls in the pre-declared ambiguous zone, plus a disclosed formula inconsistency in the stats tool — `SOTA_CONFIRM_OFFICE_RESULTS.md`). Descriptively, the Office tail contrast is strongly text-positive at full catalog (pooled tail hits, text vs ID-only: 364 vs 268 @10; 1,983 vs 1,247 @100). **Statistical correction (2026-07-19):** the previously printed pooled two-proportion z statistics (z=3.8 @10, z=13.0 @100) are retracted — the same 36,610 tail users are evaluated under every seed and under both arms, so the 183,050 seed-summed rows are clustered repeated observations, not independent trials, and an unpaired Bernoulli z is not valid (nor conservative) under that dependence. Treating the five trained models per arm as the inferential units instead, independent-arm Welch tests give ΔHR@10 = +0.000524 (t = 7.26, df ≈ 8, p ≈ 9×10⁻⁵, 95% CI [+0.00036, +0.00069]) and ΔHR@100 = +0.004021 (t = 16.75, df ≈ 8, p ≈ 2×10⁻⁷, 95% CI [+0.00347, +0.00457]) — same direction, valid geometry; final-evaluation per-user sidecars for a fully clustered analysis are a queued release item. This remains pattern evidence (the pre-declared tail prediction was VOID), consistent with the connectivity gradient (MI 2.34 win → Office 2.89 win → Beauty 3.51 / VG 3.70 null), not a scored prediction.

**Floor-anomaly resolution (2026-07-11; the matched comparator-baseline run promised above, now complete).** We executed the reference implementation's own Office SASRec configuration end-to-end — its preprocessing (dataset-size assertions passing: 77,551 items / 223,308 users), its gin config, its trainer, its eval — locally under the shimmed research path of §5.6. Its final-epoch NDCG@10 is **0.0174** (best full eval 0.0177), i.e. **+13.9% above its own published row 0.0153**, crossing the published value at epoch 20 of 101 and never re-entering. The +44% floor-check failure now decomposes exactly: 0.0204 (our floor run's final-epoch full-catalog reading) / 0.0174 (their code, locally) = **+16.9% attributable to baseline-strength protocol differences** (our floor trains with full-catalog softmax vs their 512-negative sampled softmax), and 0.0174 / 0.0153 = **+13.9% attributable to the published row sitting below what its own pipeline regenerates here** (1.139 × 1.169 = 1.331 = 0.0204/0.0153; the remaining step to the prereg's best-epoch 0.02208 is checkpoint selection plus that variant's 30k-user eval subsample). **Conclusion: the elevated floor is not an artifact of our data split or evaluation** — Office simply supports SASRec well above the published row. This *explains* the floor-check failure without repairing the comparison it protects: if the published SASRec row is conservative in this environment, the published HSTU-BLaIR 0.0271 plausibly is as well, so numerically exceeding it would not establish superiority over their method on Office. **The VOID therefore stands, deliberately** — and the pre-declared floor check is vindicated: it caught exactly the comparator-conservatism failure mode it was designed to catch.

**Completed HSTU-BLaIR check (2026-07-12).** The resolution above inferred that the published HSTU-BLaIR 0.0271 was "plausibly" conservative as well; running their Office HSTU-BLaIR configuration end-to-end locally **tested and did not support that inference**: it lands at final-epoch NDCG@10 **0.0275** (best full eval 0.0279), i.e. **+1.6%/+2.8% above the published 0.0271** — the flagship comparator row regenerates in this environment (margins comparable to the Musical_Instruments regeneration), unlike the SASRec row (+13.9%). Descriptively, the (VOID) gate values 0.03042/0.03033 sit ≈+9% above both the published value and its local regeneration. **The VOID nonetheless stands**: the pre-declared floor check failed as written, and no post-hoc result — favorable or not — restores a voided pre-declaration. These numbers are environment-caveated single-run regenerations, reported as descriptive evidence only; the V1 campaign recorded in this appendix remains counted in no claim. (A redesigned V3 pre-declaration — new never-inspected seeds, environment-matched reference — subsequently **passed** and is reported in §5.2; the V1 VOID stands unchanged.)

## Supplementary Material

> *This supplement contains (a) **S.1–S.3**: a superseded earlier-stage Beauty_and_Personal_Care supporting study — optional, not required for the main results; and (b) **S.4–S.5**: the full result tables for §5.5 (screening log) and §5.4 (titration ladder), which are CURRENT results relocated here only for main-body length. The superseded/optional qualifier applies to S.1–S.3 only.*

> **Why this is an appendix:** the material below is an earlier-stage Beauty_and_Personal_Care reproducibility study (the 20-variant cross-pipeline scan, its 2-seed signal, and the retracted LIGER-gap audit). It predates and does not belong to the headline spine (causal FIR filter + MI frequency-5 tail case + competitive-overall Video_Games result, §1–§7). It is retained verbatim for the reproducibility and negative-result record only, and is referenced from §6.1–§6.2 as supporting context. The live Beauty result that enters the tail pattern (§5.3) is the text−ID tail contrast, not these single-seed sampled-softmax scans.

### S.1 Beauty_and_Personal_Care — 20-variant cross-pipeline scan (superseded supporting material)

> **Note:** the following Beauty_and_PC 20-variant scan and the LIGER-gap audit are **earlier-stage supporting material**, retained for the reproducibility and negative-result record. They predate the HSTU + causal-filter + tail-pattern spine and are *not* the paper's headline; the live Beauty result used in the tail pattern (§5.3) is the text−ID tail contrast, not these single-seed sampled-softmax scans.

The scan varies five axes: **text encoder** (MiniLM titles/rich-text, BLaIR titles/rich-text), **projection Φ** (single Linear vs the 2-layer MLP adaptor of Hou et al., 2024), **learned item embedding** (kept vs removed = faithful SASRecText), **loss** (sampled softmax K=1024, in-batch negatives, chunked-full-softmax, hybrid), and **augmentation** (random subsequence sampling, factor 1/2/3). Training used a 15–20-epoch budget, batch size 256, Adam (lr 1e-3, weight decay 1e-5, gradient clip 5.0), a single seed for the initial scan, and two seeds (42, 43) for the final reported variants. Table A1 summarizes all 20 variants. **Numbers are single-seed unless otherwise noted.**

**Table A1: Beauty_and_PC 5-core cross-pipeline scan (full-catalog eval, NDCG@10) — 22 numbered rows: 20 distinct variants plus two seed replications (row 20 replicates variant 19; row 22 replicates baseline variant 7)**

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

**Clean-ablation finding (variant 21, added after audit)**: When we hold the encoder constant at MiniLM and ONLY change projection layer from single-Linear to the SASRecText 2-layer MLP adaptor, NDCG@10 drops slightly from ~0.0190 to 0.01889. **No improvement from the MLP adaptor was observed in this single comparison.** The +1.3-2.3% gains in variants 16/19/20 therefore cannot be attributed to the projection layer alone; their bundled encoder/content changes and possible interactions remain unresolved.

Re-analysis of the 20-variant scan:

- **MLP adaptor alone**: no improvement observed in the single comparison (variant 21 vs 7 = -1.2%)
- **MiniLM → BLaIR encoder**: small benefit (variant 16 vs 7 = +0.9% NDCG@10, single-seed)
- **Titles → rich text (BLaIR)**: small additional benefit (variant 19 vs 16 = +0.4%, single-seed)
- **Removing learned item embedding** (faithful SASRecText): hurts substantially
- **Heavy dropout (0.5)** as in the published SASRecText: hurts on our 5-core data (median 5 interactions/user)
- **Subsequence augmentation**: hurts (~-5% NDCG)
- **Width (d=128)**: no help

### S.2 Beauty_and_PC multi-seed signal (superseded supporting material)

> **Note:** this is appendix supporting material for the Beauty 20-variant scan (§S.1), not the headline tail-pattern result (§5.3).

We have multi-seed numbers for two configurations:
- Best variant (BLaIR + rich-text + MLP): seed 42 → 0.01936, seed 43 → 0.01955; **mean 0.01946 (n=2)**.
- Baseline (chunked-full, no MLP, MiniLM titles): original → 0.01911, seed 42 → 0.0190; **mean 0.01906 (n=2)**.

Apparent gain: 0.01946 - 0.01906 = **+0.0004 (+2.1% relative)** with n=2 vs n=2. Inter-seed variance for our baseline (0.0001 range) is roughly half the size of the gain, suggesting the directional signal is real but small. A formal significance test would require larger n; our paper-stated +2.1% improvement is honest about this.

### S.3 Audit of "gaps to LIGER" claims (corrected from earlier versions; superseded supporting material)

> **Note:** this comparator-audit retraction is retained as appendix material; the body's §5.4 is the titration result.

Earlier versions of this work cited an apparent 57% gap to LIGER on Beauty_and_Personal_Care. **After a comparator audit, this framing is retracted.** The facts:

1. **LIGER reports on Amazon 2014, not AR2023.** The LIGER paper (Yang et al., 2024) evaluates on Amazon Beauty (2014, He & McAuley 2016), reporting NDCG@10 = 0.04020 ± 0.00044 (K=20) and 0.04738 ± 0.00151 (K=N) on their 5-core preprocessing. The 2014 Amazon Beauty subset has tens of thousands of items, while our AR2023 Beauty_and_Personal_Care 5-core has 207,649 items. **These are different datasets.** The "57% gap" framing in earlier versions compared our AR2023 number to LIGER's 2014 number, which is invalid.

2. **There is no published LIGER number on AR2023 Beauty_and_Personal_Care 5-core.** LIGER does not evaluate on AR2023 at all in the published paper.

3. **TIGER reports on Amazon 2014 only.** The TIGER paper (Rajput et al., 2023) reports NDCG@10 = 0.0384 on Amazon Beauty 2014 with their 5-core, also not on AR2023.

4. **BLaIR (Hou et al., 2024) introduced AR2023 — historical note, superseded: the AR2023 5-core literature has since grown (HSTU-BLaIR and 2026 preprints; §5.1).** Their Beauty subset is "All_Beauty" (not "Beauty_and_Personal_Care") and their preprocessing is by-timestamp 8:1:1 with no k-core filter. They report NDCG@10 on All_Beauty in the range 0.0177-0.0241 across various LLM encoders (Table 8). With a UniSRec downstream model, their best All_Beauty number is 0.0241 (gemini-embedding). They do not report on Beauty_and_Personal_Care.

We therefore cannot make a defensible gap claim to TIGER/LIGER/BLaIR on AR2023 Beauty_and_Personal_Care 5-core, because **we did not find a comparable published number** (a search statement as of this writing, not a priority claim — AR2023 preprints are appearing rapidly; §5.1). We provide our 0.01946 (2-seed mean) as a reference baseline rather than as a SOTA-improvement claim.

A future apples-to-apples comparison would require either:
- Running TIGER/LIGER on our 5-core preprocessing (multi-week effort for faithful reproduction), or
- Adopting Hou et al.'s by-timestamp 8:1:1 preprocessing and re-running our pipeline.

### S.4 — Screening-log detail (full probe table)

> *Supplement to §5.5 — the full search record. Each row's Δ is versus its stated base; most rows are single-seed exploratory probes (power note in §5.5).*

**Table S1: Screening log — capacity-adding / alternative-mechanism probes; none showed a benefit at tested power (mostly single-seed; allocation was partly outcome-dependent, so this is a search record, not a systematic sweep).** (Mechanism class: where the lever acts. "Learned scalar → 0?" = did a free learnable gate/temperature/intensity collapse the mechanism. n = seed count. Probe powers are unequal — see the paragraph above.)

| Lever | Mechanism class | Base (NDCG@10) | Δ NDCG@10 (n) | Learned scalar → 0? | Verdict (observational at n=1) |
|---|---|---:|---:|---|---|
| c3 continuous time-decay attention kernel | attention re-weighting (capacity-add) | SBERT stack ≈0.0639 | **−0.0150** (1; test 0.0489 at record val 0.0725) | n/a | No benefit observed (single-seed probe) — actively harmful; the largest validation–test divergence in the corpus |
| Sampled softmax (K=512 negatives) | loss approximation | full-softmax stack | −0.0026 (1) | n/a | No benefit observed (single-seed probe) — undertrains full-catalog ranking |
| Dual text encoder (SBERT ⊕ BLaIR) | text encoder | SBERT stack | −0.0014 (1) | n/a | No benefit observed (single-seed probe) — the text encoder is not the gap |
| BLaIR text encoder (swap) | text encoder | SBERT stack | −0.0013 (1) | n/a | No benefit observed (single-seed probe) — encoder axis fully swept |
| GD1 spectral-shrink prior | representation regularizer | V2 0.0673 | −0.003 (1) | shrink → 0 | Rejected (the formerly linked spectral figure is retracted, §5.4 retraction note) |
| n_heads = 4 | architecture (capacity-add) | HSTU-style stack | −0.0005 (1) | n/a | No benefit observed (single-seed probe) — ties 2-head even at the published dv=dqk=16 spec |
| CL4SRec self-supervision | SSL auxiliary loss | SBERT stack | −0.0005 (1) | n/a | No benefit observed (single-seed probe) — early-epoch only |
| c1 prototype-routed expert heads | capacity-add | SBERT stack | −0.0004 (1) | n/a | No benefit observed (single-seed probe) — redundant with TAPE |
| c2 text-distillation aux loss | auxiliary loss | SBERT stack | −0.0004 (1) | n/a | No benefit observed (single-seed probe) — redundant with the additive text path |
| text-init / text warm-start | embedding initialization | SBERT stack | −0.0003 (1) | n/a | No benefit observed (single-seed probe) — redundant with the additive text path |
| EMA / SWA weight averaging | weight-space regularizer | SBERT stack | +0.0001 (1) | n/a | No benefit observed (single-seed probe) — val-high/test-flat; does not repair the structural gap |
| text-sim bias | attention bias | HSTU-style stack | ±0.0001 (4) | n/a | NEUTRAL — no benefit observed; removable candidate |
| W1 niche-share fitness-sharing penalty | inter-item loss penalty | U2/LS0.2 0.0649±0.0002 | 0.0652 (1), within band | **β = −7.42** (sign-flipped: boosts, not penalizes, crowded niches) | No benefit observed (single-seed probe) — refutes the anti-crowding remedy |
| X1 frequency-adaptive James–Stein shrinkage | representation regularizer | V2 0.0674±0.0003 | 0.0673 (1), within band | **c ≈ 0** (λ_max ≈ 0.004) → off | No benefit observed (single-seed probe) — model voted shrinkage off |
| Y1 heat-kernel/manifold label smoothing | loss-target reshaping | V2 0.0674±0.0003 | 0.06653 (1), ≤ band | **T → 0.00061** (< init) → delta target | No benefit observed (single-seed probe) — text-manifold geometry voted off |
| Z1 forced ID→text routing | representation routing | V2 | tail −75% (globally dead) | forced gate | Rejected — globally harmful |
| CF1 cue-fusion gate | representation fusion | V2 / MI | flat/dead (both datasets) | gate → 0 | Rejected — new-lever search closed |
| conn-gate connectivity-gated cold-start ID↔text fusion | representation fusion/routing | V2 text stack, MI | **tail** Δ +0.0001 ± 0.0003, same-seed 95% CI [−0.00025, +0.00045] (5); overall flat (cadence-caveated, §5.5 text) | **α → 0.0011 < init 0.0025** (voted off; recorded in 4/5 seed logs) | Rejected — operationalizes the intervention-associated connectivity tail pattern, but is not actionable (CI includes 0) |
| max_seq_len 200 / seq > 50 | sequence length | SBERT stack | ~0 (1) | n/a | No benefit observed (single-seed probe) — sequences short post-5-core |
| cosine scoring | scoring function | winning op-point | ≤ 0 (1) | n/a | No benefit observed (single-seed probe) — dot-product better at the op-point |

### S.5 — Titration ladder (full six rungs)

> *Supplement to §5.4; integrity-gated against the §5.4 prose values by `_bestrec_run/make_table_5_4_titration.py`.*

**Table S2: the interaction-thinning density-titration ladder** (AR2023 Video_Games 5-core LLOO, full-catalog n_eval = 94,762, tail_n = 10,900; same-seed-number text−ID (not initialization-paired, §5.3), best-by-val; 5 seeds = 20260608–12 per rung; mean ± sample-std, positive-seed count in parens). Realized interactions/item are the run-log values. (The former α = ipi/d_eff column is retracted with the spectral analysis — see the §5.4 retraction note; its cells are removed from the paper and marked REMOVED_FROM_PAPER in the artifact graph.) All cells are re-read from the frozen `results_TITR*/TAIL_*` JSONs by `_bestrec_run/make_table_5_4_titration.py`, which **integrity-gates** the recomputed NDCG head/tail means against the locked prose values above (aborts on any >5e-5 drift); the HR columns and per-rung seed bands are the net-new tabulation the prose summarized only as Spearman trends.

| ρ | kept inter./item | head ΔNDCG@10 | head ΔHR@10 | tail ΔNDCG@10 | tail ΔHR@10 |
|---|---|---|---|---|---|
| 1.00 | 24.405 | +0.002213 ± 0.000241 (5/5) | +0.004238 ± 0.000765 (5/5) | −0.000148 ± 0.000179 (2/5) | +0.000128 ± 0.000582 (3/5) |
| 0.94 | 22.947 | +0.002389 ± 0.000267 (5/5) | +0.004083 ± 0.000830 (5/5) | +0.000165 ± 0.000370 (4/5) | +0.000807 ± 0.000712 (5/5) |
| 0.91 | 22.210 | +0.002544 ± 0.000491 (5/5) | +0.004940 ± 0.000892 (5/5) | +0.000039 ± 0.000310 (3/5) | +0.000110 ± 0.000766 (3/5) |
| 0.88 | 21.484 | +0.002520 ± 0.000421 (5/5) | +0.004869 ± 0.000765 (5/5) | +0.000537 ± 0.000386 (4/5) | +0.000661 ± 0.000995 (4/5) |
| 0.78 | 19.030 | +0.002664 ± 0.000398 (5/5) | +0.004467 ± 0.001082 (5/5) | +0.000056 ± 0.000552 (2/5) | +0.000239 ± 0.001087 (2/5) |
| 0.66 | 16.109 | +0.003540 ± 0.000416 (5/5) | +0.005720 ± 0.000904 (5/5) | −0.000108 ± 0.000503 (1/5) | +0.000073 ± 0.001165 (3/5) |

### S.6 — Software V3 paired-seed detail

![Fig. S1: Software V3 registered paired-seed results. (A) Every matched seed block has higher sealed TEST NDCG@10 under learned FIR than identity. (B) All eight paired differences, the frozen +0.000500 reporting threshold, and the ordinary paired-t mean and 95% CI. The figure visualizes outcome-known exploratory same-team robustness, not independent confirmation; exact plotted values are in `figures/fig_software_v3_pairs_data.csv`.](figures/fig_software_v3_pairs.png)

*Fig. S1: Software V3 paired-seed detail and the frozen +0.000500 reporting threshold. This is outcome-known same-team robustness, not independent confirmation.*

### S.7 — Selected-checkpoint FIR diagnostics

![Fig. S2: Learned residual-tap and effective frequency-response summaries from the eight released selected checkpoints of the outcome-known active-control learned arm. Channels are summarized within each seed; bands are ordinary 95% t intervals over the eight seed summaries. Lag 0 is contemporaneous. These are descriptive fitted-operator diagnostics, not a mechanism or independent-confirmation test; plotted values are released in `figures/fig_fir_response_data.csv`.](figures/fig_fir_response.png)

*Fig. S2: Descriptive FIR diagnostics; neither temporal-access isolation nor learned-tap superiority is established.*
