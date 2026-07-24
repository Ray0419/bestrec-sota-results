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
| `train_data.df` | pandas pickle | rows = training next-item examples: `seq` (left-padded fixed-len history, pad=item_num), `len_seq` (true length), `next` (single target item id). Row-expansion convention (per-user vs per-prefix) is the one open item — see "Open question" below; default per-prefix, disclosed. |
| `val_data.df` | pandas pickle | one row per user: `seq` = full train history, `len_seq`, `next` = the val target. |
| `test_data.df` | pandas pickle | one row per user: `seq` = train+val history, `len_seq`, `next` = the test target (LLOO). |
| `data_statis.df` | pandas pickle | `seq_size` (max history length, e.g. 50 to match ours), `item_num` (= n_items). |
| `minilm_emb.pickle` | pandas pickle | **NOT a `.npy`.** AlphaFuse reads item text embeddings via `pd.read_pickle(<language_model_type> + '_emb.pickle')` then `np.stack(...)` ([`backbone_SASRec.py:76`], `embedding.py:72/191`). Ship a pandas **Series** (RangeIndex `0..n_items-1`) whose element `i` is item `i`'s `float32` vector. Row-aligned to **export** item ids via the re-index join below. Pass `--language_model_type minilm`; the loader is string-generic, so **no code patch is needed** (it just reads `minilm_emb.pickle`). |

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
# ship as a pandas Series (element i = item i's vector), NOT np.save:
pd.Series(list(E)).to_pickle('minilm_emb.pickle')   # AlphaFuse: pd.read_pickle + np.stack
```

**Sequence & pad contract (confirmed from the backbone).** `data_statis['seq_size']`
= the fixed padded length `L`; pad id = `item_num` (the `+1` embedding row). The
backbone takes the LAST position as the sequence state (`ff_out[:,-1]`,
`backbone_SASRec.py:211`) and masks positions equal to `item_num`
(`torch.ne(sequences, item_num)`, `:204`), with absolute position ids
`0..L-1`. Therefore each `seq` MUST be **left-padded**: the most recent real
item sits at index `L-1`, pads fill the front. Truncate longer histories to the
last `L`; `len_seq = min(true_len, L)`. Set `L` to our own maxlen (the SASRec
runs used 50) so the two systems see the same history budget. Eval scores
`item_embs[:-1]` = all `item_num` items (full catalog), matching ours.

Both sides have exactly `n_items` rows for Office (77,551) and VG (25,612)
(confirmed against the caches), and `asin2idx` covers every export parent_asin,
so the join is total; assert no `KeyError` and `E.shape == (n_items, 384)`.

## Open question to close BEFORE building the adapter

The one thing the repo does NOT pin is how `train_data.df` turns a user's
history into training rows: one row per user (last train item as `next`) vs the
DreamRec/DiffuRec-family **per-prefix** expansion (a row for every
`prefix -> next` step). Their offline data-prep ships only as Google-Drive
pickles, not code. Close it by downloading ONE AlphaFuse sample dataset (e.g.
ATV) and inspecting `train_data.df` (row count vs #users, seq dtype, pad
side/value) so our adapter reproduces their exact convention. Until confirmed,
default to per-prefix expansion (the family norm) and DISCLOSE it.

## Build order (next ticks; local, free)

1. Download one AlphaFuse sample dataset; inspect `train_data.df` /
   `data_statis.df` / `*_emb.pickle` to lock the exact schema (esp. the
   train-row expansion above and the pad side this spec infers).
2. `build_alphafuse_dataset.py`: read `export/<cat>/*.jsonl` +
   `cache_5core/sbert_titles_<cat>.npy` + `cache_5core/asin2idx_<cat>.json` →
   write `train/val/test_data.df` + `data_statis.df` + `minilm_emb.pickle` into
   `ee_baselines/AlphaFuse/ourdata/<cat>/` using the re-index join + left-pad
   contract above; assert join totality (no KeyError), `E.shape==(n_items,384)`,
   `item_num==our n_items`, and every `seq` left-padded to `L` with pad=item_num.
3. Local **smoke test**: `python train.py --data ourdata/Video_Games
   --model_type AlphaFuse --language_model_type minilm --hidden_dim 128
   --null_dim 64 --loss_type infoNCE ...` for a few epochs; confirm it trains and
   full-catalog NDCG@10/HR@10 print. **No loader patch needed** (string-generic).
4. FREEZE `PREREG_EE.md` + `adjudicate_ee.py` BEFORE any reported number
   (frozen metric, seeds, export hashes, the three disclosed deviations + the
   confirmed train-expansion convention, the comparison wording). Endpoints obey
   the seal rules.
5. Final multi-seed runs (Office_Products = counted category, Video_Games) —
   the only part that wants a rented GPU, and only after the smoke test passes.

## Status
- [x] AlphaFuse cloned + code read; data contract + eval protocol pinned
      (embeddings = `*_emb.pickle` not `.npy`; pad=item_num, left-pad, last-pos
      state; loader string-generic so no patch)
- [x] comparability decision: **head-to-head feasible** (3 disclosed deviations)
- [ ] download one sample dataset to lock the train-row expansion convention
- [ ] `build_alphafuse_dataset.py` (re-index join + left-pad) + local smoke test
- [ ] freeze PREREG_EE / adjudicate_ee → final runs
