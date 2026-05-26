"""Encode 5-core Amazon Reviews 2023 item titles with the official BLaIR
checkpoint (`hyp1231/blair-roberta-base`). Caches to
`cache_5core/blair_titles_<category>.npy`.

This is the BLaIR equivalent of the MiniLM encoding done by
`_bestrec_run/run_5core_benchmark.py --encode-titles`. We need it so that
`run_sasrec_sbert.py` can swap MiniLM for BLaIR if model-scaling alone
isn't enough to reach SOTA on Beauty_and_Personal_Care.

Usage:
    uv run python encode_blair_5core.py Video_Games Beauty_and_Personal_Care
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
BLAIR_CHECKPOINT = "hyp1231/blair-roberta-base"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
ENCODE_BATCH = 64  # smaller than MiniLM because RoBERTa-base is heavier
MAX_TEXT_LEN = 128


def load_item_list(category: str) -> list[str]:
    """Return the sorted list of parent_asin strings in the 5-core split,
    matching the order used by run_sasrec_sbert.py's `reindex()`."""
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


def load_titles(meta_path: Path, asin_set: set[str]) -> dict[str, str]:
    titles = {}
    with meta_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            pa = d.get("parent_asin")
            if pa is None or pa not in asin_set:
                continue
            title = d.get("title") or ""
            if isinstance(title, list):
                title = " ".join(str(x) for x in title)
            titles[pa] = str(title).strip()
    return titles


def encode_with_blair(texts: list[str]) -> np.ndarray:
    """Encode texts with BLaIR (CLS-pool + L2-norm), returns float32 (N, 768)."""
    from transformers import AutoModel, AutoTokenizer
    print(f"  loading {BLAIR_CHECKPOINT}...")
    tok = AutoTokenizer.from_pretrained(BLAIR_CHECKPOINT)
    model = AutoModel.from_pretrained(BLAIR_CHECKPOINT).eval().to(DEVICE)
    print(f"  model loaded; hidden_size={model.config.hidden_size}")

    out_chunks = []
    n = len(texts)
    t0 = time.time()
    with torch.no_grad():
        for s in range(0, n, ENCODE_BATCH):
            chunk = [t if t else "unknown" for t in texts[s:s + ENCODE_BATCH]]
            enc = tok(chunk, padding=True, truncation=True,
                      max_length=MAX_TEXT_LEN, return_tensors="pt")
            enc = {k: v.to(DEVICE) for k, v in enc.items()}
            hs = model(**enc, return_dict=True).last_hidden_state
            v = hs[:, 0]
            v = torch.nn.functional.normalize(v, dim=1)
            out_chunks.append(v.cpu().numpy().astype(np.float32))
            if (s // ENCODE_BATCH) % 200 == 0:
                rate = (s + ENCODE_BATCH) / max(time.time() - t0, 0.1)
                eta = (n - s) / rate
                print(f"    [{s:,}/{n:,}  {rate:.1f}/s  ETA {eta/60:.1f} min]")
    return np.concatenate(out_chunks, axis=0)


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
        titles = load_titles(META_PATHS[cat], set(item_list))
        title_strings = [titles.get(asin, "") for asin in item_list]
        print(f"  {sum(1 for t in title_strings if t.strip())} items with non-empty title")
        emb = encode_with_blair(title_strings)
        out_path = EMB_CACHE_DIR / f"blair_titles_{cat}.npy"
        np.save(out_path, emb)
        asin2idx_path = EMB_CACHE_DIR / f"asin2idx_blair_{cat}.json"
        with asin2idx_path.open("w") as fp:
            json.dump({a: i for i, a in enumerate(item_list)}, fp)
        print(f"  wrote {out_path}  ({emb.shape}, {out_path.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
