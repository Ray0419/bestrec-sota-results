# Citation Audit

**Audit time:** 2026-06-08 12:31:01 +10:00

## Verdict

Reject as a final paper in its current form unless the citation/source issues
below are fixed in the manuscript source and regenerated outputs.

## Existing BEST-Rec PDF Audit

Target PDF:
`BERT-Embedded Self-attention Transformer Recommender (BEST-Rec)_ Tackling Sparsity and Cold-Starts.pdf`

Extraction via `pypdf` found:

| Term | Count |
|---|---:|
| SASRec | 1 |
| Kang | 1 |
| McAuley | 2 |
| BLaIR | 0 |
| SBERT | 0 |
| Sentence-BERT | 0 |
| TIGER | 0 |
| LIGER | 0 |
| Amazon Reviews 2023 | 0 |
| DropoutNet | 0 |
| CLCRec | 0 |

This means the old PDF is not acceptable as a publication artifact for the
current line of work. It does not visibly attribute the key modern components
used in the repository. I did not modify the binary PDF because the editable
source was not found in the workspace; the fix is to update the source document
and regenerate the PDF.

## Code And Markdown Fixes Applied

| File | Fix |
|---|---|
| `_bestrec_run/run_sasrec_sbert.py` | Added top-level attribution for SASRec, SBERT/MiniLM, BLaIR/Amazon Reviews 2023, and Hou et al. SASRecText MLP adaptor. |
| `_bestrec_run/encode_blair_5core.py` | Added attribution for BLaIR and Amazon Reviews 2023. |
| `_bestrec_run/encode_blair_richtext_5core.py` | Added attribution for BLaIR and rich-text preprocessing lineage. |
| `_bestrec_run/encode_richtext_5core.py` | Added attribution for SBERT/MiniLM and rich-text preprocessing lineage. |
| `_bestrec_run/CITATIONS.md` | Added source-of-truth citation table for all external methods/components. |
| `_bestrec_run/README.md` | Added strict claim scope and reproducibility notes. |
| `SOTA_VIDEO_GAMES_RESULT.md` | Downgraded overstrong leaderboard language to a strong-internal-baseline claim with no SOTA wording. |
| `SOTA_FINAL_HONEST.md` | Added explicit attribution statement and removed unsupported camera-ready SOTA wording. |
| `SOTA_GOAL_FINAL.md` | Added attribution/protocol guardrail and softened conditional SOTA status. |
| `BEAUTY_GAP_FINAL_HONEST.md` | Reframed MLP adaptor as Hou et al. prior work and marked the gain as non-publication-significant. |
| `BEAUTY_GAP_CAMPAIGN_RESULTS.md` | Added attribution/protocol guardrail for BLaIR, SASRecText adaptor, and published target ranges. |
| `_bestrec_sota_lab/paper_draft/lc2c_retrieval_ltr_paper.md` | Added explicit component-attribution paragraph. |

## Required Citations

Any manuscript derived from this work must cite at least:

- Kang and McAuley, 2018, SASRec.
- Reimers and Gurevych, 2019, Sentence-BERT.
- Hou et al., 2024, BLaIR / Amazon Reviews 2023 / SASRecText reference code.
- Sun et al., 2019, BERT4Rec, if BERT4Rec baselines are discussed.
- Rajput et al., 2023, TIGER, if semantic-ID generative retrieval is discussed.
- Yang et al., 2024, LIGER, if LIGER comparisons or claims are discussed.
- Volkovs et al., 2017, DropoutNet, if cold-start baselines are discussed.
- Steck, 2019, EASE, if EASE baselines are discussed.
- He et al., 2020, LightGCN, if graph baselines are discussed.
- Hu, Koren, and Volinsky, 2008, iALS, if implicit matrix factorization is discussed.
- Liang et al., 2018, MultiVAE, if VAE baselines are discussed.
- Wei et al., 2021, CLCRec, if contrastive cold-start baselines are discussed.

## Remaining Blockers

- Regenerate or replace the old BEST-Rec PDF from an editable source with full
  citations. The current PDF is not publication-safe.
- Pin exact external comparator tables and protocols. Approximate remembered
  TIGER/BLaIR/LIGER numbers are not enough for a final SOTA claim.
- Add per-user records for Wilcoxon/bootstrap tests before claiming statistical
  superiority over external baselines.

## Phase-2 Update: Verified Comparator Numbers (2026-05-30)

After a second pass of fetching and inspecting the actual PDFs of TIGER, LIGER,
and BLaIR papers, the following authoritative numbers and protocols apply.

### BEST-Rec PDF SASRec citation error (page 6)

The BEST-Rec PDF on page 6 reads:

> "SASRec (Self-Attentive Sequential Recommendation) demonstrated that
> self-attention could effectively model user preference evolution without the
> sequential processing constraints of RNNs (Chen et al., 2022)."

This citation is **wrong**. The correct citation is:

> Kang, W.-C., & McAuley, J. (2018). Self-Attentive Sequential Recommendation.
> 2018 IEEE International Conference on Data Mining (ICDM). arXiv:1808.09781.

**Required fix**: replace "(Chen et al., 2022)" with "(Kang & McAuley, 2018)"
in the source document, and add a corresponding reference entry.

### BEST-Rec PDF BERT4Rec missing citation (page 6)

The BEST-Rec PDF on page 6 mentions:

> "BERT4Rec adapted the bidirectional encoder representations from transformers
> (BERT) for recommendation tasks... The success of BERT4Rec inspired numerous
> extensions incorporating masked language modeling objectives and multi-task
> learning frameworks for recommendation (Noorian et al., 2024)."

BERT4Rec itself is mentioned but **not cited**. The correct citation for
BERT4Rec is:

> Sun, F., Liu, J., Wu, J., Pei, C., Lin, X., Ou, W., & Jiang, P. (2019).
> BERT4Rec: Sequential Recommendation with Bidirectional Encoder
> Representations from Transformer. CIKM 2019. arXiv:1904.06690.

**Required fix**: add an inline citation `(Sun et al., 2019)` immediately
after the first mention of "BERT4Rec", and add a corresponding reference
entry.

### Total citations found in BEST-Rec PDF

A regex sweep of the PDF text identified 33 unique inline citations of the
form `(Author et al., Year)` or `(Author et al., Year; ...)`. Two were
verified as wrong/missing above; the remaining 31 still need cross-checking
against the references section of the BEST-Rec PDF.

### Citation suite to cross-check

For a full audit, codex should:

1. Extract the references list at the end of the BEST-Rec PDF.
2. For each inline citation `(Author, Year)`, look up the matching reference
   in the references list and verify:
   - The author list begins with the author named in the inline cite.
   - The year matches.
   - The cited paper is actually about the topic claimed by the surrounding text.
3. Flag any cite where the inline cite has no matching reference entry, or
   where the cited paper does not match the topic of the surrounding text.

The two errors above were found by spot-checking the SASRec and BERT4Rec
contexts only. Other errors may exist elsewhere in the manuscript.

### TIGER (Rajput et al., 2023, NeurIPS, arXiv:2305.05065) Table 1

Dataset: **Amazon Reviews 2014** (Beauty, Sports, Toys), 5-core, LLOO.

| Method | Beauty NDCG@10 | Sports NDCG@10 | Toys NDCG@10 |
|---|---:|---:|---:|
| SASRec | 0.0318 | 0.0192 | 0.0374 |
| TIGER  | 0.0384 | 0.0225 | 0.0432 |

**Not comparable to AR2023 5-core LLOO numbers.** Earlier session notes that
claimed "TIGER ~0.042 on Video_Games" or "TIGER ~0.031 on Beauty_and_PC" are
incorrect — TIGER reports on Amazon 2014, not AR2023, and does not have a
Video_Games subset (it has Toys and Games, a different category).

### LIGER (Yang et al., 2024, arXiv:2411.18814) Table 2

Dataset: **Amazon Reviews 2014** (Beauty, Sports, Toys, Steam), 5-core, LLOO,
mean ± std across 3 seeds.

| Method | Beauty in-set NDCG@10 | Sports | Toys | Steam |
|---|---:|---:|---:|---:|
| SASRec | 0.02179 ± 0.00023 | 0.01160 ± 0.00038 | 0.02756 ± 0.00079 | 0.14763 ± 0.00051 |
| UniSRec | 0.03346 ± 0.00057 | 0.01814 ± 0.00041 | 0.03622 ± 0.00056 | — |
| TIGER  | 0.03216 ± 0.00084 | 0.01989 ± 0.00085 | 0.02949 ± 0.00049 | 0.15034 ± 0.00064 |
| **LIGER (K=20)** | **0.04020 ± 0.00044** | **0.02430 ± 0.00075** | **0.03756 ± 0.00151** | **0.14951 ± 0.00158** |
| LIGER (K=N) | 0.04738 ± 0.00151 | 0.02962 ± 0.00053 | 0.04680 ± 0.00086 | — |

**Not comparable to AR2023 5-core LLOO numbers.** Earlier session notes that
claimed "LIGER ~0.045+ on Beauty_and_PC" or framed our work as having a "57%
gap to LIGER" compared 2014 Beauty (LIGER) to 2023 Beauty_and_Personal_Care
(ours). The framing is invalid and must be retracted from any paper draft.

### BLaIR (Hou et al., 2024, arXiv:2403.03952) Table 8

Dataset: **AR2023** (All_Beauty, Video_Games, Baby_Products, ML1M, Yelp).

Protocol: **by-timestamp 8:1:1 split with NO k-core filter**; downstream model
is **UniSRec** (not SASRec); evaluating different LLM encoders as the frozen
text encoder.

| LLM Encoder | All_Beauty NDCG@10 | Video_Games NDCG@10 | Baby_Products NDCG@10 |
|---|---:|---:|---:|
| RoBERTa-large | 0.0177 | 0.0113 | 0.0070 |
| Qwen3-Embedding-0.6B | 0.0224 | 0.0126 | 0.0072 |
| sup-simcse-roberta-large | 0.0232 | 0.0114 | 0.0069 |
| sentence-t5-large | 0.0212 | 0.0125 | 0.0075 |
| Qwen3-Embedding-4B | 0.0212 | 0.0127 | 0.0075 |
| Qwen3-Embedding-8B | 0.0216 | **0.0138** | 0.0072 |
| SFR-Embedding-Mistral | 0.0231 | 0.0131 | 0.0076 |
| e5-mistral-7b-instruct | 0.0238 | 0.0136 | 0.0072 |
| GritLM-7B | 0.0216 | 0.0133 | 0.0074 |
| gemini-embedding-001 | **0.0241** | 0.0136 | 0.0073 |
| text-embedding-3-large | 0.0237 | 0.0135 | **0.0078** |

**Not directly comparable to our 5-core LLOO numbers.** The 5-core filter
removes cold users/items, substantially easing the benchmark. Our 0.0514
(Video_Games) vs. their max 0.0138 is largely a preprocessing artifact, not a
fair architectural comparison.

Also note: BLaIR's "Beauty" subset is "All_Beauty", a smaller and different
subset than our "Beauty_and_Personal_Care".

### Verified MiniLM citation

The base architecture for `sentence-transformers/all-MiniLM-L6-v2` is:

> Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., & Zhou, M. (2020). MiniLM:
> Deep Self-Attention Distillation for Task-Agnostic Compression of
> Pre-Trained Transformers. NeurIPS 2020. arXiv:2002.10957.

The SBERT framework used to fine-tune it into sentence embeddings is:

> Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using
> Siamese BERT-Networks. EMNLP. arXiv:1908.10084.

Both should be cited when referencing `all-MiniLM-L6-v2`.

### Verified UniSRec citation (for BLaIR-paper protocol)

> Hou, Y., Mu, S., Zhao, W. X., Li, Y., Ding, B., & Wen, J.-R. (2022). Towards
> Universal Sequence Representation Learning for Recommender Systems. KDD 2022.

UniSRec is the downstream architecture used in the BLaIR benchmark Table 8.

### HSTU-BLaIR (Liu, 2025) — DIRECTLY COMPARABLE published number

> Liu, Y. (2025). HSTU-BLaIR: Lightweight Contrastive Text Embedding for
> Generative Recommender. KDD 2025 LLM4ECommerce Workshop. arXiv:2504.10545.

This paper evaluates on AR2023 Video Games 5-core LLOO with **identical
dataset stats to ours**: 25,612 items, 94,762 users, 814,585 interactions
(their Table 1). They train for **100 epochs** following the Zhai et al. HSTU
protocol with leave-one-out evaluation.

Their Table 2 (Video Games, single-seed):

| Method | NDCG@10 | HR@10 | MRR |
|---|---:|---:|---:|
| SASRec | 0.0573 | 0.1028 | 0.0518 |
| HSTU (Zhai et al., 2024) | 0.0741 | 0.1315 | 0.0658 |
| HSTU-OpenAI (text-embedding-3-large) | 0.0742 | 0.1328 | 0.0658 |
| **HSTU-BLaIR** | **0.0760** | **0.1353** | **0.0674** |

**Our 5-seed SASRec-SBERT mean = 0.0551 ± 0.0003** — we do NOT beat their
SASRec single-seed baseline (0.0573), and we do NOT beat HSTU-BLaIR (0.0760).

**Required action**: any paper must:
- Cite Liu (2025) HSTU-BLaIR as the published SOTA on this protocol.
- Cite Zhai et al. (2024) for the HSTU architecture.
- Acknowledge that our SASRec-SBERT does not beat the published SASRec
  baseline (possibly due to training-length difference: 30 vs 100 epochs).
- Retract any "SOTA" wording for the Video_Games claim.

## What This Audit Changes

1. **Retracted**: any claim of "SOTA over TIGER" — TIGER reports on Amazon 2014, not AR2023.
2. **Retracted**: any claim of "SOTA over LIGER" — LIGER reports on Amazon 2014, not AR2023.
3. **Retracted**: the "57% gap to LIGER on Beauty_and_PC" framing — apples-to-oranges across dataset versions.
4. **Modified**: BLaIR comparison is now annotated with preprocessing (by-timestamp, no k-core) and downstream-model (UniSRec) caveats.
5. **Re-framed**: Our 0.0514 ± 0.0021 (Video_Games) and 0.01946 (Beauty_and_PC 2-seed mean) are **reference numbers** on a specific AR2023 5-core LLOO protocol, not SOTA improvements.

## Required Source-Document Fix

- Replace "(Chen et al., 2022)" with "(Kang & McAuley, 2018)" on page 6 of
  the BEST-Rec PDF source.
- Add the Kang & McAuley 2018 reference entry to the BEST-Rec references list
  (if not already present).
