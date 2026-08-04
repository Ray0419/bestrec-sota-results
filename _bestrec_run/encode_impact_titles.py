#!/usr/bin/env python
"""MiniLM title-cache builder for the IMPACT program categories.

Reproduces EXACTLY the encode path of the paper's standard script
(`run_5core_benchmark.py --encode-titles`, which produced every existing
cache_5core/sbert_titles_*.npy) by IMPORTING its functions -- load_split_csv,
reindex, load_titles, encode_titles_sbert -- and running the same block
(load splits -> sorted-item reindex -> titles from raw meta jsonl ->
all-MiniLM-L6-v2 encode -> save npy + asin2idx json). The only difference is
that it STOPS after writing the cache instead of continuing into the EASE
benchmark (whose dense n_users x n_items allocation MemoryErrors on large
categories -- see encode_Office_Products.log). The tracked script's hardcoded
META_PATHS map is not consulted; the meta path is passed explicitly.

Row i of the saved .npy corresponds to sorted(item asins)[i], the exact
alignment run_sasrec_sbert.py assumes when it loads the cache.

Usage:
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/encode_impact_titles.py \
      Industrial_and_Scientific data_raw_proper/industrial_sci/meta_Industrial_and_Scientific.jsonl
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import numpy as np

from run_5core_benchmark import (SPLIT_DIR, EMB_CACHE_DIR, load_split_csv,
                                 load_titles, encode_titles_sbert, reindex)


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    assert len(sys.argv) == 3, "usage: encode_impact_titles.py <Category> <meta_jsonl_path>"
    cat = sys.argv[1]
    meta_path = (ROOT / sys.argv[2]) if not Path(sys.argv[2]).is_absolute() else Path(sys.argv[2])
    assert meta_path.exists(), f"meta jsonl missing: {meta_path}"

    emb_path = EMB_CACHE_DIR / f"sbert_titles_{cat}.npy"
    asin2idx_path = EMB_CACHE_DIR / f"asin2idx_{cat}.json"
    if emb_path.exists() and asin2idx_path.exists():
        emb = np.load(emb_path)
        print(f"cache already exists: {emb_path} shape={emb.shape}; keeping (never overwrite)")
        return 0

    print(f"=== {cat}: load splits ===")
    t0 = time.time()
    train_rows = load_split_csv(SPLIT_DIR / f"{cat}.train.csv")
    valid_rows = load_split_csv(SPLIT_DIR / f"{cat}.valid.csv")
    test_rows = load_split_csv(SPLIT_DIR / f"{cat}.test.csv")
    _, _, _, user_list, item_list = reindex(train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    print(f"  n_users={n_users:,}  n_items={n_items:,}  [{time.time()-t0:.1f}s]")

    # identical to run_5core_benchmark.main() encode block ------------------
    EMB_CACHE_DIR.mkdir(exist_ok=True)
    print(f"\n=== {cat}: Load titles from metadata ===")
    t0 = time.time()
    titles = load_titles(meta_path, set(item_list))
    print(f"  {len(titles):,} / {n_items:,} items have titles  [{time.time()-t0:.1f}s]")
    title_strings = [titles.get(asin, "") for asin in item_list]
    n_empty = sum(1 for t in title_strings if not t.strip())
    if n_empty:
        print(f"  WARN: {n_empty:,} items have empty title; using empty string")

    print(f"\n=== {cat}: SBERT encoding ({n_items:,} items) ===")
    t0 = time.time()
    emb = encode_titles_sbert(title_strings)
    print(f"  encoded {n_items:,} items -> {emb.shape}  [{time.time()-t0:.1f}s]")
    np.save(emb_path, emb)
    with asin2idx_path.open("w") as fp:
        json.dump({a: i for i, a in enumerate(item_list)}, fp)
    print(f"  cached to {emb_path}")
    print(f"  sha256 {sha256(emb_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
