# E-E — AlphaFuse adapter spec + comparability decision (from reading the real code)

Derived by inspecting the cloned `ee_baselines/AlphaFuse/` (SIGIR 2025,
Hugo-Chinn/AlphaFuse) — `train.py`, `utils.py`, `models/embedding.py`. This
pins exactly what the adapter must produce and settles the
benchmark-or-exclusion question.

## Decision: a faithful head-to-head is FEASIBLE (not an exclusion)

**The evaluation protocol is compatible with ours.** `utils.evaluate()` scores
every item (item-embedding table sized `item_num+1`), takes `topk(100)`, and
computes HR / NDCG / MRR @{1,5,10,20,50} on the leave-last-out `next` target —
i.e. **full-catalog LLOO next-item ranking**, the same estimand as our runs.
So AlphaFuse-on-our-data vs ours-on-our-data is a meaningful head-to-head on
NDCG@10 / HR@10.

**Three deviations must be disclosed (they do not block the comparison):**
1. **Item text embeddings.** AlphaFuse expects OpenAI `text-embedding-3`
   (`--language_model_type 3small`=1536-d / `3large`=3072-d). We have no OpenAI
   key, so we substitute our **frozen MiniLM title embeddings** (384-d,
   `cache_5core/sbert_titles_<cat>.npy`). Still frozen language embeddings;
   AlphaFuse's null-space construction is dimension-agnostic. **Disclosed as a
   substitution**, and applied identically to any arm we compare.
2. **Training loss.** AlphaFuse trains with infoNCE/BCE + sampled negatives
   (`--neg_ratio 64`); ours uses chunked full softmax. A training-side choice;
   the eval is full-catalog either way. Disclosed.
3. **Split.** We NEVER compare to AlphaFuse's paper numbers (their ATV/ATG/ASO
   splits). We run AlphaFuse on OUR AR2023 5-core LLOO split via the adapter —
   the only apples-to-apples framing.

No SOTA/superiority wording; the result is a point-estimate comparison under
the environment caveats (same class as the two counted comparisons).

## What the adapter must produce (per category, in `ee_baselines/AlphaFuse/<ourdata>/<cat>/`)

From `train.py` + `models/embedding.py`, `--data <X>` reads
`../ours_DiT/data/<X>/`:

| File | Format | Content (from our export) |
|---|---|---|
| `train_data.df` | pandas pickle | rows = training next-item examples: `seq` (left-padded fixed-len history of item ids), `len_seq` (true length), `next` (target item id). Built from each user's train prefix (all-position or last-position — match AlphaFuse's own preprocessing; default next-only). |
| `val_data.df` | pandas pickle | one row per user: `seq` = full train history, `len_seq`, `next` = the val target. |
| `test_data.df` | pandas pickle | one row per user: `seq` = train+val history, `len_seq`, `next` = the test target (LLOO). |
| `data_statis.df` | pandas pickle | `seq_size` (max history length, e.g. 50 to match ours), `item_num` (= n_items). |
| `<lm_type>_language_embs.npy` | float32 `.npy` | item text embeddings row-aligned to **export** item ids `0..n_items-1`. See the re-index join below — do NOT slice `[:n_items]`. Loader path is `language_embs_path=data_directory`, keyed by `language_model_type`; set `--language_model_type minilm` (add the key to `load_language_embeddings`) or reuse the `3small` slot with our matrix. |

**Embedding re-index join (verified, load-bearing).** The cache is NOT already in
export order. `cache_5core/sbert_titles_<cat>.npy` is `(n_items, 384)` keyed by
`cache_5core/asin2idx_<cat>.json` (a verified `parent_asin → 0..n_items-1`
permutation). Our export builds its OWN contiguous item map (first appearance
across train+valid+test). The two orderings differ, so a `[:n_items]` slice would
silently mis-pair every item's text with the wrong embedding. The adapter MUST
re-index through `parent_asin`:

```
items = read export/<cat>/<cat>.items.jsonl        # export_id -> parent_asin
a2i   = json cache_5core/asin2idx_<cat>.json        # parent_asin -> cache_row
sbert = np.load cache_5core/sbert_titles_<cat>.npy  # (n_items, 384)
E = np.empty((n_items, 384), float32)
for it in range(n_items):
    E[it] = sbert[a2i[items[it].parent_asin]]       # KeyError => hard fail, never guess
np.save(<lm_type>_language_embs.npy, E)
```

Both sides have exactly `n_items` rows for Office (77,551) and VG (25,612)
(confirmed against the caches), and `asin2idx` covers every export parent_asin,
so the join is total; assert no `KeyError` and `E.shape == (n_items, 384)`.

## Build order (next ticks; local, free)

1. `build_alphafuse_dataset.py`: read `export/<cat>/*.jsonl` +
   `cache_5core/sbert_titles_<cat>.npy` + `cache_5core/asin2idx_<cat>.json` →
   write the 4 `.df` + `_language_embs.npy` into
   `ee_baselines/AlphaFuse/ourdata/<cat>/` using the re-index join above; assert
   the join is total (no KeyError), `E.shape == (n_items, 384)`, and
   `item_num == our n_items`.
2. Minimal patch to `AlphaFuse/models/embedding.py` `load_language_embeddings`
   to accept a `minilm` key (kept in a committed `alphafuse_minilm.patch`, so
   we never silently edit the upstream clone).
3. Local **smoke test**: `python train.py --data ourdata/Video_Games
   --model_type AlphaFuse --language_model_type minilm --hidden_dim 128
   --null_dim 64 ...` for a few epochs; confirm it trains and its full-catalog
   NDCG@10/HR@10 print. (Tiny models; local GPU suffices.)
4. FREEZE `PREREG_EE.md` + `adjudicate_ee.py` BEFORE any reported number
   (frozen metric, seeds, export hashes, the three disclosed deviations, the
   comparison wording). Endpoints obey the seal rules.
5. Final multi-seed runs (Office_Products = counted category, Video_Games) —
   these are the only part that wants a rented GPU, and only after the smoke
   test passes.

## Status
- [x] AlphaFuse cloned + code read; data contract + eval protocol pinned
- [x] comparability decision: **head-to-head feasible** (3 disclosed deviations)
- [ ] `build_alphafuse_dataset.py` + embedding patch + local smoke test
- [ ] freeze PREREG_EE / adjudicate_ee → final runs
