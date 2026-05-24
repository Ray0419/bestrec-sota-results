# Research Report: TIGER / LIGER Implementation Feasibility for BEST-Rec

Produced by a research agent on 2026-05-22. The agent did not implement anything — this is just the recommendation.

## 1. What TIGER and LIGER are

**TIGER** (Rajput et al., NeurIPS 2023, [arxiv 2305.05065](https://arxiv.org/abs/2305.05065)) introduces *generative retrieval* for recommendations:
- Train an **RQ-VAE** (Residual-Quantized VAE) to convert each item's content embedding into discrete "semantic IDs" (typically 4-6 tokens per item).
- Train a **Transformer encoder–decoder** on user history sequences to autoregressively predict the next item's semantic ID, token by token.
- At inference: beam search or greedy generation (< 10 tokens, < 1 ms per GPU step).

Key claim: semantic IDs allow cold-start generalisation because new/rare items share token prefixes with similar items, transferring information without an item-ID lookup table.

**LIGER** (Yang et al., [arxiv 2411.18814](https://arxiv.org/abs/2411.18814), Meta, Dec 2024) addresses a key TIGER limitation:
- TIGER fails at cold-start items (near-zero performance on most datasets except Amazon Sports).
- LIGER hybridises: generative retrieval (RQ-VAE + Transformer) proposes a candidate set, then **dense retrieval refines using item text embeddings**.
- Key insight: combining semantic IDs with text representations of cold items recovers cold-start performance.

## 2. Public reference implementations

| Source | Repo | Status | Notes |
|--------|------|--------|-------|
| Unofficial TIGER | [NonameUntitled/tiger](https://github.com/NonameUntitled/tiger) | Complete | PyTorch; Beauty/Sports/Toys Amazon; 5M params; straightforward pip setup |
| RQ-VAE standalone | [EdoardoBotta/RQ-VAE-Recommender](https://github.com/EdoardoBotta/RQ-VAE-Recommender) | Complete | Two-stage train; well documented |
| **LIGER (Official, Meta)** | [facebookresearch/liger](https://github.com/facebookresearch/liger) | Complete | Hydra-config; Amazon + Steam; CC-BY-NC |
| BLaIR (fallback) | [hyp1231/AmazonReviews2023](https://github.com/hyp1231/AmazonReviews2023) | Complete | Pre-trained for Amazon Reviews 2023; RecBole-integrated |

**Authoritative path:** LIGER (Meta, official).

## 3. Compute cost on Books (14K users, 13K items, 600K interactions)

| Stage | Cost (H100, ~$2-2.50/hr) |
|---|---|
| RQ-VAE training | 4–12 GPU-hours |
| Transformer decoder training | 8–24 GPU-hours |
| Total per fold | 12–36 GPU-hours |
| 5-fold cross-validation | 60–180 GPU-hours = $120–$450 (spot pricing) |
| Memory | Single 40GB A100/H100; no distributed training |

Comparison: EASE+SBERT trains in minutes per fold.

## 4. Minimum-viable closed-form proxy

**RQ-VAE Semantic ID kNN Retrieval** (no Transformer decoder):
1. Train RQ-VAE on item SBERT embeddings (frozen).
2. Quantize all items to semantic IDs.
3. Compute semantic-ID-based similarity matrix S between items (Hamming/cosine on the discrete codes; or use the RQ-VAE decoder reconstructions).
4. Inference for cold item j:
   ```
   score(u, j_cold) = sum_w in user_history of S[w, j_cold]
   ```
   Mirrors the existing `content_direct` baseline but with discrete semantic IDs replacing continuous SBERT cosines.

- **Advantages:** no Transformer training, closed-form retrieval, ~300 LOC PyTorch, identical cold-start logic to existing LC2C pipeline.
- **Disadvantage:** loses autoregressive sequential modelling — likely worse on warm items, but for cold-item evaluation isolates the "semantic-ID content prior" cleanly.

## 5. LIGER vs TIGER

LIGER's edge:
- Fixes TIGER's cold-start failure by adding dense text retrieval to semantic-ID candidates.
- Same RQ-VAE stage 1.
- Modified Transformer stage 2 that uses text repr alongside semantic IDs.
- Official Meta repo, maintained, integrated with Amazon Reviews 2023.

Reproduction complexity: roughly the same as TIGER (still two stages) but avoids the near-zero cold-item failure cliff.

## Decision

1. **If compute budget > $200 and timeline allows weeks:** LIGER via `facebookresearch/liger`. Faithful, cold-aware, Amazon-Reviews-native.
2. **If budget tight ($50-150):** RQ-VAE semantic-ID kNN proxy, ~300 LOC, ~2-3 days. Defensible as TIGER-inspired proxy.
3. **If TIGER/LIGER fundamentally infeasible:** BLaIR fallback from [hyp1231/AmazonReviews2023](https://github.com/hyp1231/AmazonReviews2023), pre-trained checkpoint for Amazon Reviews 2023, < 1 GPU-hour. Mark TIGER/LIGER as "out of scope, replaced with dense-retrieval baseline (BLaIR)".

**Most realistic path for this submission window:** ship the RQ-VAE kNN proxy + the proper BLaIR baseline; mark LIGER as a camera-ready follow-up.

## Citations

- TIGER: [Recommender Systems with Generative Retrieval](https://papers.neurips.cc/paper_files/paper/2023/file/20dcab0f14046a5c6b02b61da9f13229-Paper-Conference.pdf), Rajput et al., NeurIPS 2023.
- LIGER: [Unifying Generative and Dense Retrieval for Sequential Recommendation](https://arxiv.org/abs/2411.18814), Yang et al., 2024.
- BLaIR: [Bridging Language and Items for Retrieval and Recommendation](https://arxiv.org/abs/2403.03952).
