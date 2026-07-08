# Bulletproof plan — remove plagiarism/inflated-claim accusations without weakening results

**Strategy**: Re-frame what's ours vs what's prior work, add proper attribution everywhere, add validation runs that strengthen statistical defensibility. **Do NOT change any actual numbers** — the numbers are real and reproducible.

**Total scope**: ~15 concrete sub-tasks across 6 phases. Estimated 6-12 GPU-hours + 2-4 hrs of doc/citation work.

---

## What's ACTUALLY ours (claim aggressively, with evidence)

1. **5-core Amazon Reviews 2023 preprocessing**: `_bestrec_run/preprocess_5core_standard.py` — built from scratch, different from Hou et al. 2024's `0core_timestamp_w_his_*` HF subset.
2. **Memory-efficient chunked-full-softmax**: `chunked_full_softmax_loss()` in `run_sasrec_sbert.py` — incremental logsumexp over item chunks, enables full-catalog CE loss at 207K items.
3. **Eval optimization (cache `all_item_features()`)**: gives ~10× speedup at d=64 by computing item features once per eval call rather than once per batch.
4. **NaN-trap diagnosis**: identified that left-padding + key_padding_mask + norm_first → NaN propagation through residuals (documented in `SOTA_FINAL_HONEST.md`).
5. **Standard SASRec eval-convention discovery**: include val item in input at test time (+30% NDCG@10 vs the buggy variant).
6. **20+ documented experiments** on the 5-core benchmark with full-catalog eval — most are negative results that filter the design space.
7. **Multi-seed (n=2 so far) verification** that Hou et al.'s published SASRecText adaptor design transfers to a different preprocessing pipeline.
8. **Video_Games historical strong internal result**: later audit updates this to NDCG@10 = 0.05509 +/- 0.00035 (5-seed mean) on Amazon Reviews 2023 Video_Games 5-core. This is not approved SOTA language because HSTU-BLaIR is stronger.

## What's NOT ours and needs proper attribution

| Component | Source | Where it's used in our work |
|---|---|---|
| SASRec architecture | Kang & McAuley, ICDM 2018 | `run_sasrec_sbert.py:SASRecSBERT` |
| SBERT / MiniLM-L6-v2 | Reimers & Gurevych, EMNLP 2019 | text encoder for items |
| BLaIR encoder (`hyp1231/blair-roberta-base`) | Hou et al. 2024 (arXiv:2403.03952) | `cache_5core/blair_titles_*.npy` |
| 2-layer MLP adaptor `[768→300→64]` Dropout+ReLU | Hou et al. 2024 SASRecText (`external/AmazonReviews2023/seq_rec_results/model/sasrectext.py`) | `--mlp-adaptor` flag in `run_sasrec_sbert.py` |
| Rich-text content concatenation (title + features + categories + description) | Hou et al. 2024 preprocessing (`features_needed = [...]`) | `encode_richtext_5core.py`, `encode_blair_richtext_5core.py` |
| Amazon Reviews 2023 dataset | Hou et al. 2024 | `data_raw_proper/`, `data_5core/` |
| TIGER (semantic IDs + AR decoder) — comparator | Rajput et al., NeurIPS 2023 | only cited as comparator number |
| LIGER (TIGER + dense retrieval) — comparator | Yang et al. 2024 | only cited as comparator number |
| RoBERTa, BERT, DistilBERT (in BEST-Rec PDF) | Liu et al. 2019 / Devlin et al. 2019 / Sanh et al. 2019 | text encoders |
| iALS, EASE, LightGCN, DropoutNet, CLCRec, MultiVAE (in `_bestrec_run/`) | various published papers | baselines |

---

## Phase 1 — Citation audit (no result change; 2-3 hrs)

### Task 1.1 — Fix SASRec mis-citation in BEST-Rec PDF
**Current state**: Page 6 of the BEST-Rec PDF reads "SASRec (Self-Attentive Sequential Recommendation) demonstrated that self-attention could effectively model user preference evolution... (Chen et al., 2022)".

**Action**: Replace "Chen et al., 2022" with "Kang & McAuley, ICDM 2018".

**Files**: original BEST-Rec source (DOCX/LaTeX) — verify against `BERT-Embedded Self-attention Transformer Recommender (BEST-Rec)_ Tackling Sparsity and Cold-Starts.pdf`.

**Verification**:
- `pypdf` extract page 6, grep for "SASRec", confirm citation is now correct.
- Cross-check references section: there should be an entry "Kang, W.-C., & McAuley, J. (2018). Self-Attentive Sequential Recommendation. ICDM."

### Task 1.2 — Audit every citation in the BEST-Rec PDF
**Action**: Use `pypdf` to extract every "(Author, Year)" or "(Author et al., Year)" citation. Cross-reference each one against:
- The references section at the end of the PDF
- The actual paper it cites (by quick web search or paper title verification)

Flag any miscredited citations (like the SASRec one) and produce a list of fixes needed.

**Output**: `CITATION_AUDIT.md` with one row per citation: `(claim_in_paper, citation_in_text, correct_citation, status)`.

### Task 1.3 — Add a clear "Attribution Statement" to all BEST-Rec docs
**Action**: Add a short section near the start of:
- The BEST-Rec PDF (if a revision is possible)
- `_bestrec_run/README.md` (or create one)
- `SOTA_GOAL_FINAL.md`
- `BEAUTY_GAP_FINAL_HONEST.md`
- Any future paper

with this text (or equivalent):

> **Attribution and Prior Art**: This work builds on:
> - SASRec (Kang & McAuley, 2018) — the base sequential recommender architecture, which we reimplemented in PyTorch.
> - BLaIR (Hou et al., 2024, arXiv:2403.03952) — the Amazon-domain pretrained text encoder used for item-text features.
> - SASRecText (Hou et al., 2024) — the 2-layer MLP adaptor design `[768→300→64]` with Dropout(0.2)+ReLU, copied from `external/AmazonReviews2023/seq_rec_results/model/sasrectext.py` with attribution.
> - Amazon Reviews 2023 (Hou et al., 2024) — the source dataset.
>
> Our specific contributions are: (a) the 5-core preprocessing pipeline (vs. Hou et al.'s 0-core), (b) a memory-efficient chunked-full-softmax loss for 207K-item catalogs, (c) the empirical evidence that the published SASRecText adaptor design transfers to 5-core, (d) negative-result documentation across 20+ ablations, (e) multi-seed verification on the 5-core protocol, (f) a strong internal Video_Games 5-core baseline, not a SOTA result.

### Task 1.4 — Update existing docs with attribution
**Action**: Search and replace in:
- `SOTA_GOAL_FINAL.md`
- `BEAUTY_GAP_FINAL_HONEST.md`
- `BEAUTY_GAP_CAMPAIGN_RESULTS.md`
- `SOTA_VIDEO_GAMES_RESULT.md`
- `SOTA_FINAL_HONEST.md`

Every mention of:
- "MLP adaptor" → "MLP adaptor (Hou et al. 2024)"
- "BLaIR" → "BLaIR (Hou et al. 2024)" (first mention per doc)
- "rich text" / "rich-text" → "rich-text concatenation (derived from Hou et al. 2024 preprocessing)"
- "the published SASRecText" → keep, but add citation on first mention.

---

## Phase 2 — Re-frame contributions in docs (no result change; 1-2 hrs)

### Task 2.1 — Replace "first positive intervention" language
**Current**: `SOTA_GOAL_FINAL.md` and `BEAUTY_GAP_CAMPAIGN_RESULTS.md` use phrases like "the only positive intervention from 20 attempts".

**Action**: Replace with one of:
- "the published SASRecText adaptor design (Hou et al. 2024) was the only one of 20 tested variants that gave a directionally consistent improvement on our 5-core benchmark"
- "of the 20 variants tested, only the SASRecText recipe (Hou et al. 2024) carried over to our setup"

**Rationale**: Same number, same observation, but explicitly credits the source.

### Task 2.2 — Add a "Preprocessing-protocol mismatch" caveat
**Action**: In `SOTA_GOAL_FINAL.md` and `BEAUTY_GAP_FINAL_HONEST.md`, add a callout box near each "gap to LIGER" or "gap to published" mention:

> ⚠️ **Preprocessing mismatch**: Our 5-core leave-last-out is NOT the same as the protocol Hou et al. 2024's `seq_rec_results/` repo uses, which is `0core_timestamp_w_his_*` from HuggingFace. Published TIGER and LIGER numbers may use yet another protocol (verify against the actual papers). The "57% gap" framing assumes apples-to-apples comparability that is not established. To enable rigorous comparison, either (a) re-run the published methods on our 5-core preprocessing, or (b) re-run our method on the published 0-core preprocessing — see Phase 4.

### Task 2.3 — Strengthen the Video_Games claim
**Historical pre-audit state**: `SOTA_VIDEO_GAMES_RESULT.md` claimed 0.0514 ± 0.0021 (3-seed mean) against approximate TIGER/BLaIR target values. Later HSTU-BLaIR evidence invalidates SOTA wording.

**Action**: Verify those exact comparator numbers against the TIGER, BLaIR, and HSTU-BLaIR evidence. The SOTA claim does not stand unless the method beats the strongest protocol-matched comparator.

**Files to check**:
- TIGER: Rajput et al., "Recommender Systems with Generative Retrieval", NeurIPS 2023, arXiv:2305.05065
- BLaIR: Hou et al., 2024, arXiv:2403.03952 — Table with SASRec, SASRec+BLaIR, etc. on Video_Games
- LIGER: Yang et al., 2024 — find arXiv ID and verify number

Add the verified citations to `SOTA_VIDEO_GAMES_RESULT.md`. If our method does not beat the strongest protocol-matched published/reproduced comparator, keep the claim as a strong internal baseline only.

---

## Phase 3 — Code-level attribution (no result change; 1 hr)

### Task 3.1 — Add docstring attribution to the MLP adaptor code
**File**: `_bestrec_run/run_sasrec_sbert.py`

**Current state** (already partially done):
```python
ap.add_argument("--mlp-adaptor", action="store_true",
                 help="Replace single-Linear projection with 2-layer MLP "
                      "Dropout->Linear(sbert_dim, mlp_hidden)->ReLU->Dropout->"
                      "Linear(mlp_hidden, d_model). Matches the faithful "
                      "SASRecText AdaptorLayer in external/AmazonReviews2023.")
```

**Action**: Strengthen the citation in the `SASRecSBERT.__init__` docstring and the class-level comment:

```python
# The MLP adaptor design (2-layer MLP [768, 300, 64] with Dropout(0.2) + ReLU)
# is adopted verbatim from the SASRecText `AdaptorLayer` published by
# Hou et al. 2024 in `external/AmazonReviews2023/seq_rec_results/model/sasrectext.py`.
# We do not claim novelty for this architecture choice — our contribution is
# the empirical demonstration that it transfers to our 5-core preprocessing.
# See: Hou et al. (2024), arXiv:2403.03952.
```

### Task 3.2 — Add docstring attribution to encoder caches
**Files**: `encode_blair_5core.py`, `encode_blair_richtext_5core.py`, `encode_richtext_5core.py`

**Action**: At the top of each file, add a CITATIONS block:
```python
"""
Citations:
- BLaIR encoder: Hou et al. (2024). "Bridging Language and Items for Retrieval
  and Recommendation." arXiv:2403.03952. Checkpoint: hyp1231/blair-roberta-base.
- Rich-text fields (title + features + categories + description): the
  composition follows Hou et al. (2024)'s preprocessing in
  `external/AmazonReviews2023/seq_rec_results/dataset/process_amazon_2023.py`.
- MiniLM (sentence-transformers/all-MiniLM-L6-v2): Reimers & Gurevych (2019),
  Sentence-BERT, EMNLP.
"""
```

### Task 3.3 — Add a `CITATIONS.md` in `_bestrec_run/`
**Action**: Create a single source-of-truth file with full citations for every external component used:

```markdown
# Citations for `_bestrec_run/`

| Component | Citation | Used by |
|---|---|---|
| SASRec | Kang, W.-C., & McAuley, J. (2018). Self-Attentive Sequential Recommendation. ICDM. | `run_sasrec_sbert.py` |
| BLaIR | Hou, Y., Li, J., He, Z., Yan, A., Chen, X., & McAuley, J. (2024). Bridging Language and Items for Retrieval and Recommendation. arXiv:2403.03952. | encoders + `--mlp-adaptor` design |
| SASRecText | Hou et al. (2024), `external/AmazonReviews2023/seq_rec_results/`. | `--mlp-adaptor` design |
| BERT4Rec | Sun, F., Liu, J., Wu, J., Pei, C., Lin, X., Ou, W., & Jiang, P. (2019). BERT4Rec. CIKM. | `run_bert4rec.py` |
| SBERT / MiniLM-L6-v2 | Reimers, N., & Gurevych, I. (2019). Sentence-BERT. EMNLP. | encoders |
| TIGER | Rajput, S., et al. (2023). Recommender Systems with Generative Retrieval. NeurIPS. | comparator + `run_tiger_minimal.py` |
| LIGER | Yang, J., et al. (2024). LIGER. arXiv:... | comparator |
| Amazon Reviews 2023 | Hou et al. (2024). | dataset |
| UniSRec | Hou, Y., He, Z., McAuley, J., Zhao, W. X. (2022). Towards Universal Sequence Representation Learning for Recommender Systems. KDD. | prior text-based sequential rec |
| iALS, EASE, LightGCN, DropoutNet, CLCRec, MultiVAE | (case-by-case) | baselines |
```

Codex must verify each citation by web search or paper-title lookup.

---

## Phase 4 — Validation runs (strengthens defensibility; 6-10 GPU-hours)

### Task 4.1 — Multi-seed baseline (CRITICAL for rigorous comparison)
**Why**: Currently the baseline 0.01911 is a single-seed run. The 0.01946 (2-seed mean of our best) cannot be rigorously compared to a single-seed baseline.

**Action**: Re-run the chunked-full no-MLP baseline with seeds 42, 43, 44.

**Command** (per seed):
```bash
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py \
  Beauty_and_Personal_Care --epochs 15 --batch-size 256 --d-model 64 \
  --n-layers 2 --n-heads 2 --dropout 0.2 --chunked-full-softmax \
  --item-chunk 32768 --seed <SEED> --eval-every 5 --eval-subsample 10000 \
  --out _bestrec_run/results_sasrec_chunkedfull_Beauty_seed<SEED>.json
```

**Expected**: 3 seed results × 1.5 hrs = 4.5 hrs GPU.

**Output**: 3 JSON files with seed-specific results. Then:
```bash
_bestrec_run/.venv/Scripts/python -c "
import json, numpy as np
seeds = [42, 43, 44]
ndcgs = []
for s in seeds:
    d = json.load(open(f'_bestrec_run/results_sasrec_chunkedfull_Beauty_seed{s}.json'))
    ndcgs.append(d['best_test']['NDCG@10'])
print(f'baseline mean: {np.mean(ndcgs):.5f}, std: {np.std(ndcgs):.5f}, n={len(ndcgs)}')
"
```

This gives the **multi-seed baseline mean and std**, which is the proper comparator for our 2-seed best.

### Task 4.2 — Third seed of the new best
**Action**: Re-run BLaIR-rich-text + MLP with seed 44.

**Command**:
```bash
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py \
  Beauty_and_Personal_Care --epochs 15 --batch-size 256 --d-model 64 \
  --n-layers 2 --n-heads 2 --dropout 0.2 --chunked-full-softmax \
  --item-chunk 32768 --encoder-cache cache_5core/blair_richtext_titles_Beauty_and_Personal_Care.npy \
  --mlp-adaptor --mlp-hidden 300 --mlp-dropout 0.2 --seed 44 \
  --eval-every 5 --eval-subsample 10000 \
  --out _bestrec_run/results_sasrec_blair_richtext_mlp_seed44_Beauty.json
```

Combined with the existing seed 42 (0.01936) and seed 43 (0.01955), this gives a 3-seed mean for the new best.

### Task 4.3 — Pure-MLP ablation (clean attribution)
**Why**: The current "+1.3% gain" entangles two changes — encoder MiniLM→BLaIR + projection Linear→MLP. To attribute the gain cleanly, we need MiniLM+MLP (without BLaIR) as an ablation.

**Action**: Run BLaIR-titles encoder + MLP — already done (0.01928). Plus run **MiniLM + MLP** to isolate the MLP contribution from the encoder change.

**Command**:
```bash
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py \
  Beauty_and_Personal_Care --epochs 15 --batch-size 256 --d-model 64 \
  --n-layers 2 --n-heads 2 --dropout 0.2 --chunked-full-softmax \
  --item-chunk 32768 \
  --mlp-adaptor --mlp-hidden 300 --mlp-dropout 0.2 --seed 42 \
  --eval-every 5 --eval-subsample 10000 \
  --out _bestrec_run/results_sasrec_minilm_mlp_Beauty.json
```

Note: no `--encoder-cache` arg → uses default MiniLM cache (`sbert_titles_Beauty_and_Personal_Care.npy`).

**Expected**: ~1.5 hrs. Result will show whether MLP alone (without BLaIR) gives the gain or whether BLaIR is required.

### Task 4.4 — Verify the SASRec implementation matches a reference
**Why**: We claim our SASRec works correctly. Codex should sanity-check it against a reference implementation (e.g. recbole's SASRec or the public Kang & McAuley TensorFlow code).

**Action**: Spot-check 3 things:
- Causal mask is correct (test: model.encode([1,2,3,pad,pad]) shouldn't attend to future positions)
- Item embedding is right-padded with a separate pad slot (test: model.item_emb(pad_id).abs().max() ≈ 0)
- Eval scoring uses dot product with the full item table (test: shape sanity check)

Document in a new `_bestrec_run/SASREC_IMPLEMENTATION_VERIFICATION.md`.

### Task 4.5 — Apples-to-apples LIGER comparison (optional, expensive)
**Why**: The "57% gap to LIGER" is currently unverified — LIGER may use different preprocessing/eval.

**Action**: Either:
- (Easy) Re-read LIGER paper, extract their exact Beauty_and_PC eval protocol, document any mismatch with ours. Update the "gap" framing accordingly.
- (Expensive) Run LIGER official code on our 5-core preprocessing. Multi-week effort; likely out of scope.

---

## Phase 5 — Cross-paper plagiarism check (1-2 hrs)

### Task 5.1 — Self-plagiarism check on BEST-Rec PDF
**Action**: Use a similarity tool (e.g. `difflib` for naive check, or paste sections into a plagiarism checker if available) to verify the BEST-Rec PDF text isn't verbatim-copied from any single source.

**Specific sections to check**:
- Page 2-7 (related work) — high risk of paraphrasing-too-close to existing surveys
- Page 9-13 (methodology) — check the math/equations aren't directly lifted from prior papers
- Tables — confirm originals, not screenshots from other papers

**Tool**: use `difflib.SequenceMatcher` to compare sliding windows of the BEST-Rec text against:
- The SASRec paper (Kang & McAuley 2018) for sequential-rec sections
- The BLaIR paper (Hou et al. 2024) for text-encoder sections
- The BERT4Rec paper (Sun et al. 2019) for bidirectional sections

Flag any windows with > 70% similarity.

### Task 5.2 — Verify figures and equations are original
**Action**: For each figure in the BEST-Rec PDF, confirm it's a freshly drawn diagram and not lifted from a source paper. Same for equations — check they're stated in our notation, not copied symbol-for-symbol from a source.

---

## Phase 6 — Final writeup (2-3 hrs)

### Task 6.1 — Generate the "publication-ready claim"
**Action**: Write a one-page `PUBLISHABLE_CLAIM.md` that states exactly what we can defend:

```markdown
# Publishable claims (after Phase 4 completes)

## Claim 1 (Video_Games): strong internal baseline on Amazon Reviews 2023 Video_Games 5-core
The original draft claim below has been retracted by the later HSTU-BLaIR audit.
The defensible statement is that SASRec-SBERT reaches NDCG@10 = 0.05509 ±
0.00035 (5-seed mean) on this repository's Amazon Reviews 2023 Video_Games
5-core leave-last-out, full-catalog eval. This:
- Beats same-run SASRec-BLaIR and no-text SASRec ablations
- Does not beat the upstream HSTU-BLaIR report
- Does not beat the completed local SM120 compatibility-port HSTU-BLaIR run

The architecture is a 2-layer Transformer (d=64) with frozen MiniLM-SBERT item-text
projection — strictly simpler than TIGER/LIGER. Training takes ~10 minutes on a
single consumer GPU.

## Claim 2 (Beauty_and_PC): empirical transfer of the SASRecText adaptor
We empirically demonstrate that the 2-layer MLP adaptor design from Hou et al.'s
SASRecText (published in their AR2023 reference repo) transfers to a different
preprocessing pipeline (5-core, vs their 0-core), giving a directionally consistent
+X.X% NDCG@10 improvement (3-seed mean, statistically significant at p < 0.05)
on Amazon Reviews 2023 Beauty_and_PC 5-core.

We do NOT claim:
- A new architecture (we use existing components from Kang & McAuley 2018 + Hou et al. 2024)
- That the gap to LIGER is closed (it is not — 57% remains in the most generous reading)
- That our +X.X% gain on Beauty_and_PC represents fundamental algorithmic progress
  (it is a small empirical observation about cross-pipeline transferability)

## Claim 3: negative result documentation
We provide systematic negative-result evidence for 18+ ablations on Beauty_and_PC
5-core, including ... [enumerate]. This narrows the search space for future work.

## Claim 4: engineering contributions
- Chunked-full-softmax loss implementation for 207K-item catalogs at d=64
- Cached `all_item_features()` eval optimization
- Open-source 5-core preprocessing pipeline matching the Hou et al. 2024 hyperparameters
```

### Task 6.2 — Update BEST-Rec PDF revision plan
**Action**: If the BEST-Rec paper will be revised, draft a "REVISION_PLAN.md" that lists:
- All citation fixes from Phase 1
- Self-plagiarism fixes from Phase 5
- Any factual corrections from Phase 4 (multi-seed baseline result, etc.)

This goes to the corresponding author for the actual paper revision.

---

## Phase 7 — Final verification (30 min)

### Task 7.1 — Cross-check all docs are consistent
**Action**: Final consistency check across:
- `SOTA_GOAL_FINAL.md`
- `BEAUTY_GAP_FINAL_HONEST.md`
- `BEAUTY_GAP_CAMPAIGN_RESULTS.md`
- `SOTA_VIDEO_GAMES_RESULT.md`
- `SOTA_FINAL_HONEST.md`
- `_bestrec_run/CITATIONS.md`
- `PUBLISHABLE_CLAIM.md`

Verify:
- Every numeric result appears with the same precision everywhere
- Every cite is consistent (Hou et al. 2024 → arXiv:2403.03952 in all docs)
- The MLP adaptor is attributed everywhere
- The "57% gap" claim has the preprocessing-mismatch caveat everywhere

### Task 7.2 — Run the leaderboard comparator
**Action**:
```bash
_bestrec_run/.venv/Scripts/python _bestrec_run/compare_beauty_results.py
```

Verify the leaderboard correctly shows:
- All 3-seed means (after Phase 4 completes)
- Std reported
- Attribution column added

---

## Acceptance criteria (codex completes when all green)

- [ ] Phase 1.1: SASRec citation in BEST-Rec PDF fixed (Chen → Kang & McAuley 2018)
- [ ] Phase 1.2: `CITATION_AUDIT.md` exists with every BEST-Rec citation cross-checked
- [ ] Phase 1.3: Attribution Statement added to all 5 listed docs
- [ ] Phase 1.4: "MLP adaptor (Hou et al. 2024)" replaces "MLP adaptor" everywhere
- [ ] Phase 2.1: "first positive intervention" reframed
- [ ] Phase 2.2: Preprocessing-mismatch caveat added to all "gap" mentions
- [ ] Phase 2.3: Video_Games comparator numbers verified against papers
- [ ] Phase 3.1: MLP adaptor code has strengthened attribution comment
- [ ] Phase 3.2: Encoder scripts have CITATIONS docstring
- [ ] Phase 3.3: `_bestrec_run/CITATIONS.md` exists and is complete
- [ ] Phase 4.1: 3-seed baseline runs produced; `baseline_mean ± std` reported
- [ ] Phase 4.2: Seed 44 of new best produced; `best_mean ± std` reported
- [ ] Phase 4.3: MiniLM + MLP ablation produced; isolates MLP contribution
- [ ] Phase 4.4: SASRec implementation verification doc written
- [ ] Phase 4.5: LIGER comparator verified against actual paper, gap framing updated
- [ ] Phase 5.1: Self-plagiarism check completed for BEST-Rec PDF text
- [ ] Phase 5.2: Figures/equations confirmed original
- [ ] Phase 6.1: `PUBLISHABLE_CLAIM.md` written
- [ ] Phase 6.2: `REVISION_PLAN.md` written for BEST-Rec PDF
- [ ] Phase 7.1: Final cross-doc consistency verified
- [ ] Phase 7.2: Leaderboard comparator output captured

## Critical preservation guarantees

Codex MUST NOT:
- Change any actual numeric results
- Re-run experiments that already have JSON outputs (those numbers are final)
- Remove the negative-result documentation (it's part of our contribution)
- Reintroduce Video_Games SOTA wording without beating or faithfully
  protocol-excluding HSTU-BLaIR

Codex MAY add but not subtract from:
- The number of attribution footnotes
- The number of caveats around comparator numbers
- The number of seeds (more seeds = stronger claim)
- The number of ablations (more ablations = cleaner attribution)

End of plan.
