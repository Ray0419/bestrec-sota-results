# -*- coding: utf-8 -*-
"""Encode Steam item text with MiniLM (CPU, to keep the GPU free).

Emits (NEW files only):
  <main>/cache_5core/sbert_titles_Steam.npy   (12012, 384) float32,
      row order == sorted(product_id) strings == run_sasrec_sbert.reindex order
  <main>/cache_5core/asin2idx_Steam.json
Same encoder as the Amazon caches: sentence-transformers/all-MiniLM-L6-v2.
"""
import json
import os

import numpy as np

CACHE = r"C:\Users\rayxc\Documents\R\cache_5core"
NPY = os.path.join(CACHE, "sbert_titles_Steam.npy")
IDX = os.path.join(CACHE, "asin2idx_Steam.json")

if os.path.exists(NPY):
    print("REFUSING to overwrite existing cache; delete manually to redo")
    raise SystemExit(1)

text = json.load(open(os.path.join(CACHE, "steam_item_text.json"),
                      encoding="utf-8"))
items = sorted(text.keys())          # must match reindex() string sort
sents = [text[i] if text[i].strip() else "unknown game" for i in items]
print(f"encoding {len(sents):,} item texts on CPU...", flush=True)

from sentence_transformers import SentenceTransformer  # noqa: E402
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2",
                            device="cpu")
emb = model.encode(sents, batch_size=256, show_progress_bar=True,
                   convert_to_numpy=True).astype(np.float32)
print(f"embeddings: {emb.shape}", flush=True)
np.save(NPY, emb)
json.dump({i: k for k, i in zip(range(len(items)), items)} and
          {it: k for k, it in enumerate(items)},
          open(IDX, "w", encoding="utf-8"))
print(f"wrote {NPY} and {IDX}", flush=True)
