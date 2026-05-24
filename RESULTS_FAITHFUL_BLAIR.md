# Faithful BLaIR baseline (official `hyp1231/blair-roberta-base` checkpoint)

Run script: `_bestrec_run/run_faithful_blair.py`
Per-pair records: `_bestrec_run/results_faithful_blair_perpair_<dataset>.jsonl`
Aggregate results: `_bestrec_run/results_faithful_blair.json`
Significance: `_bestrec_run/results_faithful_blair_significance.json`
Run log: `_bestrec_run/run_faithful_blair_run.log`

## Model card

| Field | Value |
|-------|-------|
| Checkpoint | `hyp1231/blair-roberta-base` (Hugging Face) |
| Paper | Hou et al., 2024. *Bridging Language and Items for Retrieval and Recommendation.* [arXiv:2403.03952](https://arxiv.org/abs/2403.03952) |
| Architecture | RoBERTa-base, fine-tuned on Amazon Reviews 2023 (item metadata, user review) pairs |
| Hidden size | 768 |
| Pooling | `last_hidden_state[:, 0]` (CLS), then L2-normalise (per official model card) |
| Tokenizer max length | 512 |
| Status | `is_official_blair=true`, `fallback_used=false` |
| Faithful encoder load | confirmed at session start; embeddings encoded with CUDA |
| Embedding cache | `cache/<dataset>/v5/item_title_blair_k{K}_dedup.pt` (768-d L2-normalised) |

Item-side input is **title only**, matching the simplified `blair_text` proxy
so the comparison is apples-to-apples on input text. User profile is the
L2-normalised mean of BLaIR embeddings over each user's training items
(single-tower retrieval). Score is cosine over the full catalog (warm + cold),
with the user's own training items masked to -inf before ranking.

## Honest deviations from the paper

The official BLaIR paper's strongest recommendation results use:
1. A **language-context tower** that consumes user-review history text, not
   just an averaged item-embedding profile.
2. Item-metadata input concatenating title + features + description.

This baseline drops both:
- Uses item TITLE only (cached metadata in this repo only consistently has
  `title` across the four datasets).
- User profile is the L2-norm mean of item embeddings (no review-text
  encoding for the user, since the cold-item splits drop reviews of held-out
  items along with the items).

This is therefore a **same-tower, title-only BLaIR retrieval baseline**: the
faithful part is that the encoder is the actual pre-trained BLaIR
checkpoint, replacing the simplified proxy's `all-MiniLM-L6-v2`. The
simplified deviations (title-only, mean-pool user profile) match the
existing `blair_text` proxy in
`_bestrec_run/run_all_confirmatory.make_blair_text_full` so the only
varied factor is the encoder.

## Protocol

- Full-catalog cold-item evaluation (same protocol as
  `_bestrec_run/run_poc_cdr_books.py::eval_full`): per held-out (user,
  target_item) pair, mask the user's training items, rank the target
  against the entire catalog, score NDCG@10 / HR@10 / MRR.
- Seeds: 20260521, 20260522, 20260523 for Beauty / Fashion / Instruments;
  seed 20260521 only for Books.
- 5-fold item-GroupKFold per seed (15 folds for Beauty/Fashion/Instruments,
  5 folds for Books).

## Per-dataset NDCG@10 (mean +/- std across all folds)

| Dataset | Seeds | Folds | Faithful BLaIR (this run) | Simplified `blair_text` (5-seed confirmatory) | `content_direct` (5-seed confirmatory) | `CDR_validated` (3-seed POC) |
|---------|-------|-------|---------------------------|-----------------------------------------------|----------------------------------------|------------------------------|
| Beauty      | 3 | 15 | **0.0428 +/- 0.0120** | 0.0409 | 0.0409 | 0.1461 +/- 0.0069 |
| Fashion     | 3 | 15 | **0.0376 +/- 0.0061** | 0.0411 | 0.0411 | 0.1353 +/- 0.0142 |
| Instruments | 3 | 15 | **0.0072 +/- 0.0014** | 0.0094 | 0.0094 | 0.0534 +/- 0.0020 |
| Books       | 1 |  5 | **0.0077 +/- 0.0005** | 0.0099 | 0.0099 | 0.0535 +/- 0.0013 |

Notes:
- The simplified `blair_text` proxy in the confirmatory run uses cached
  `all-MiniLM-L6-v2` title embeddings; algebraically it is the same as
  `content_direct` (mean-pooled user profile cosine over normalised item
  embeddings is equivalent to summing per-item cosines up to a row scale),
  which is why those two columns are numerically identical in the
  confirmatory output. This is an additional reason to swap in the
  faithful encoder as the comparator: the previous "BLaIR" entry was
  effectively rebranded `content_direct`.
- `CDR_validated` numbers are from `_bestrec_run/results_poc_cdr.json`.

## Per-USER paired Wilcoxon (one-sided, faithful BLaIR > comparator), Holm-corrected within dataset

Pairing is at the (seed, fold_id, user_id, target_item_id) level so each
comparator competes on exactly the same held-out pairs. Holm correction is
applied across the 3 (or 2 for Books) comparators within each dataset.

| Dataset | vs `blair_text` (simplified) | vs `content_direct` | vs `CDR_validated` |
|---------|-------------------------------|----------------------|---------------------|
| Beauty      | delta = +0.0026, n=253, p=4.23e-01 (n.s.) | delta = +0.0026, n=253, p=4.23e-01 (n.s.) | delta = -0.1048, n=253, p=1.00 (n.s.) |
| Fashion     | delta = -0.0039, n=513, p=8.99e-01 (n.s.) | delta = -0.0039, n=513, p=8.99e-01 (n.s.) | delta = -0.1152, n=513, p=1.00 (n.s.) |
| Instruments | delta = -0.0022, n=3911, p=1.00 (n.s.)      | delta = -0.0022, n=3911, p=1.00 (n.s.)      | delta = -0.0462, n=3911, p=1.00 (n.s.) |
| Books       | delta = -0.0026, n=14407, p=1.00 (n.s.)     | delta = -0.0026, n=14407, p=1.00 (n.s.)     | n/a (no per-pair CDR_validated for Books) |

The one-sided alternative is `faithful_blair > baseline`, so a near-1.0
p-value indicates the baseline is *higher* than faithful BLaIR. The
takeaway is that faithful BLaIR is **statistically indistinguishable from
the simplified blair_text/content_direct proxy** under our protocol (one
trivial mean win on Beauty, three trivial mean losses elsewhere), and it
is **substantially worse than CDR_validated** on every dataset.

## Headline interpretations

1. **Does faithful BLaIR beat the simplified `blair_text` proxy?** Only
   on Beauty (delta +0.0026, p=0.42, not significant). On Fashion,
   Instruments, and Books faithful BLaIR is slightly worse. No dataset
   reaches the conventional p<0.05 threshold.
2. **Does it beat `content_direct`?** Same answer as `blair_text` -- the
   two are numerically identical in the confirmatory run, so there is no
   difference between the two comparisons. Faithful BLaIR does not show a
   significant content-quality advantage over MiniLM SBERT in this
   single-tower title-only setup.
3. **Does it beat `CDR_validated`?** No. CDR_validated is 2-3x stronger on
   Beauty/Fashion and 5-7x stronger on Instruments/Books. This is expected
   because CDR_validated builds an EASE warm matrix and learns a Ridge
   B-imputer over the same SBERT embeddings; even with a stronger text
   encoder, single-tower title cosine cannot match a CF-grounded scorer.
4. **Implication for the strict-confirmatory baseline audit.** The
   `blair_text` slot in the strict pipeline can now point to the
   `faithful_blair` records (and the `fidelity` field can be updated to
   `official_blair_roberta_base_checkpoint_title_only_single_tower`), but
   doing so will not change the LC2C++ verdict in either direction: the
   faithful baseline is essentially the same strength as the simplified
   one for these k-core slices.

## Files written

| Path | Contents |
|------|----------|
| `_bestrec_run/run_faithful_blair.py` | Implementation (encoder load, embedding, eval). |
| `_bestrec_run/run_faithful_blair_compare.py` | Per-user Wilcoxon vs comparators. |
| `_bestrec_run/results_faithful_blair.json` | Per-(dataset, seed, fold) NDCG@10/HR@10/MRR plus model card. |
| `_bestrec_run/results_faithful_blair_perpair_<ds>.jsonl` | Per-(seed, fold, user_id, target_item_id) NDCG records for each dataset. |
| `_bestrec_run/results_faithful_blair_significance.json` | Holm-corrected paired Wilcoxon vs all three comparators. |
| `_bestrec_run/run_faithful_blair_run.log` | Raw runtime log. |
| `cache/<dataset>/v5/item_title_blair_k{K}_dedup.pt` | Cached 768-d L2-normalised BLaIR title embeddings (one tensor per dataset). |
