"""Encode 5-core Amazon Reviews 2023 items with a RICH text representation
(title + category hierarchy + main_category + brand) using SBERT MiniLM.
Caches to `cache_5core/richtext_titles_<category>.npy`.

Citations:
- MiniLM / SBERT family: Reimers & Gurevych (2019), "Sentence-BERT:
  Sentence Embeddings using Siamese BERT-Networks", EMNLP.
- Rich-text fields (title + features/categories/description-style metadata):
  the composition is derived from Hou et al. (2024)'s Amazon Reviews 2023
  preprocessing practice of constructing item text from structured metadata.
- Amazon Reviews 2023 dataset: Hou et al. (2024), arXiv:2403.03952.

Motivation: cryptic Beauty SKU titles like "Shiyeen 10 Colors Hair Chalk..."
benefit hugely from added categorical context. By concatenating
  "{title} | {main_category} > {cat1} > {cat2} > {cat3} | brand: {store}"
we give MiniLM both lexical and categorical signal in one embedding, without
needing Amazon-domain pretraining.

Output schema matches `encode_blair_5core.py`: float32 (n_items, 384) for
MiniLM, written to `cache_5core/richtext_titles_<category>.npy`, with a
sibling `asin2idx_richtext_<category>.json`.

Usage:
    uv run python encode_richtext_5core.py Beauty_and_Personal_Care
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
EMB_CACHE_DIR = ROOT / "cache_5core"
META_PATHS = {
    "Video_Games":              ROOT / "data_raw_proper" / "video_games" / "meta_Video_Games.jsonl",
    "Beauty_and_Personal_Care": ROOT / "data_raw_proper" / "beauty_and_pc" / "meta_Beauty_and_Personal_Care.jsonl",
}
MINILM_CHECKPOINT = "sentence-transformers/all-MiniLM-L6-v2"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
ENCODE_BATCH = 128
MAX_TEXT_LEN = 256  # longer than title-only because we append categories


def load_item_list(category: str) -> list[str]:
    """Return the sorted list of parent_asin strings in the 5-core split."""
    train_csv = SPLIT_DIR / f"{category}.train.csv"
    valid_csv = SPLIT_DIR / f"{category}.valid.csv"
    test_csv = SPLIT_DIR / f"{category}.test.csv"
    items = set()
    for path in (train_csv, valid_csv, test_csv):
        with path.open("r", encoding="utf-8") as fp:
            rdr = csv.DictReader(fp)
            for r in rdr:
                items.add(r["parent_asin"])
    return sorted(items)


def build_rich_text(d: dict) -> str:
    """Build a rich text representation from a meta dict."""
    parts = []
    title = d.get("title") or ""
    if isinstance(title, list):
        title = " ".join(str(x) for x in title)
    title = str(title).strip()
    if title:
        parts.append(title)

    main_cat = d.get("main_category") or ""
    cats = d.get("categories") or []
    if not isinstance(cats, list):
        cats = []
    cat_chain = []
    if main_cat:
        cat_chain.append(str(main_cat).strip())
    for c in cats:
        c = str(c).strip()
        if c and c not in cat_chain:
            cat_chain.append(c)
    if cat_chain:
        parts.append(" > ".join(cat_chain))

    store = d.get("store") or ""
    if isinstance(store, list):
        store = " ".join(str(x) for x in store)
    store = str(store).strip()
    if store:
        parts.append(f"brand: {store}")

    return " | ".join(parts) if parts else "unknown"


def load_rich_text(meta_path: Path, asin_set: set[str]) -> dict[str, str]:
    rich = {}
    n_read = 0
    with meta_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            pa = d.get("parent_asin")
            if pa is None or pa not in asin_set:
                continue
            rich[pa] = build_rich_text(d)
            n_read += 1
    return rich


def encode_with_minilm(texts: list[str]) -> np.ndarray:
    """Encode texts with MiniLM (mean-pool + L2-norm), returns float32 (N, 384)."""
    from sentence_transformers import SentenceTransformer
    print(f"  loading {MINILM_CHECKPOINT}...")
    model = SentenceTransformer(MINILM_CHECKPOINT, device=DEVICE)
    print(f"  model loaded; max seq len = {model.max_seq_length}")
    model.max_seq_length = MAX_TEXT_LEN

    n = len(texts)
    t0 = time.time()
    emb = model.encode(
        texts,
        batch_size=ENCODE_BATCH,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    rate = n / max(time.time() - t0, 0.1)
    print(f"  encoded {n:,} items in {time.time()-t0:.1f}s ({rate:.1f}/s)")
    return emb.astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("categories", nargs="+")
    args = ap.parse_args()
    EMB_CACHE_DIR.mkdir(exist_ok=True)
    for cat in args.categories:
        print(f"\n=== {cat} ===")
        if cat not in META_PATHS or not META_PATHS[cat].exists():
            print(f"  metadata file missing: {META_PATHS.get(cat)}")
            continue
        item_list = load_item_list(cat)
        n_items = len(item_list)
        print(f"  {n_items:,} items in 5-core split")
        rich = load_rich_text(META_PATHS[cat], set(item_list))
        texts = [rich.get(asin, "unknown") for asin in item_list]
        n_nonempty = sum(1 for t in texts if t and t != "unknown")
        print(f"  {n_nonempty:,} items with non-empty rich text")
        # Print a couple examples for sanity
        print(f"  example[0]: {texts[0][:200]}")
        print(f"  example[1]: {texts[1][:200]}")
        emb = encode_with_minilm(texts)
        out_path = EMB_CACHE_DIR / f"richtext_titles_{cat}.npy"
        np.save(out_path, emb)
        asin2idx_path = EMB_CACHE_DIR / f"asin2idx_richtext_{cat}.json"
        with asin2idx_path.open("w") as fp:
            json.dump({a: i for i, a in enumerate(item_list)}, fp)
        print(f"  wrote {out_path}  ({emb.shape}, {out_path.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
