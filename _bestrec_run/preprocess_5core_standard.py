"""Standard 5-core preprocessing for Amazon Reviews 2023, matching the
official `hyp1231/AmazonReviews2023/benchmark_scripts/kcore_filtering.py`
pipeline. Produces the same CSV format used by published benchmarks.

Adapts the official script to:
  - read the user's existing `.jsonl` files (one record per line)
  - use the actual `timestamp` key (the official script uses `sortTimestamp`
    which is a synonym for the same field in the newer dataset releases)
  - write outputs under `data_5core/<category>/{rating_only,last_out}/`
    so it doesn't interfere with the existing k-core caches

Run on All_Beauty first (smallest, ~700K reviews) to validate:
    cd _bestrec_run
    uv run python preprocess_5core_standard.py All_Beauty

Then on the bigger benchmarks:
    uv run python preprocess_5core_standard.py All_Beauty Amazon_Fashion Musical_Instruments

The standard 5-core leaves users with ≥5 interactions AND items with ≥5
interactions (recursively until stable). This is THE benchmark used by
TIGER, LIGER, BLaIR, etc.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data"
OUT_DIR = ROOT / "data_5core"

# Map of category name (used both as raw subdir and output prefix) -> raw jsonl filename
CATEGORIES = {
    # Original (small) subcategories — kept for backward compat
    "All_Beauty":           ("beauty",      "All_Beauty.jsonl"),
    "Amazon_Fashion":       ("fashion",     "Amazon_Fashion.jsonl"),
    "Musical_Instruments":  ("instruments", "Musical_Instruments.jsonl"),
    "Books":                ("books",       "Books.jsonl"),
    # PROPER published-benchmark categories used by TIGER/LIGER/BLaIR
    # (downloaded from McAuley Lab to data_raw_proper/)
    "Video_Games":               ("../data_raw_proper/video_games",          "Video_Games.jsonl"),
    "Beauty_and_Personal_Care":  ("../data_raw_proper/beauty_and_pc",        "Beauty_and_Personal_Care.jsonl"),
    "Sports_and_Outdoors":       ("../data_raw_proper/sports",               "Sports_and_Outdoors.jsonl"),
    "Toys_and_Games":            ("../data_raw_proper/toys",                 "Toys_and_Games.jsonl"),
    # 4th HSTU-BLaIR benchmark category (novelty-audit N7/N13 response; their
    # published Office NDCG@10: SASRec .0153 / HSTU .0223 / HSTU-BLaIR .0271)
    "Office_Products":           ("../data_raw_proper/office",               "Office_Products.jsonl"),
}


def load_ratings(path: Path) -> list[tuple]:
    """Return list of (user_id, parent_asin, rating, timestamp)."""
    inters = []
    n_skipped = 0
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            try:
                dp = json.loads(line.strip())
                inters.append((
                    dp["user_id"],
                    dp["parent_asin"],
                    float(dp["rating"]),
                    int(dp.get("timestamp") or dp.get("sortTimestamp")),
                ))
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                n_skipped += 1
    if n_skipped:
        print(f"  skipped {n_skipped:,} malformed lines")
    return inters


def make_inters_in_order(inters: list[tuple]) -> list[tuple]:
    """Deduplicate (user, item) pairs — keep earliest by timestamp."""
    user2inters = collections.defaultdict(list)
    for inter in inters:
        user2inters[inter[0]].append(inter)
    new_inters = []
    for user, lst in user2inters.items():
        lst.sort(key=lambda d: d[3])
        seen_items = set()
        for inter in lst:
            if inter[1] in seen_items:
                continue
            seen_items.add(inter[1])
            new_inters.append(inter)
    return new_inters


def get_user2count(inters):
    c = collections.defaultdict(int)
    for u, _, _, _ in inters: c[u] += 1
    return c


def get_item2count(inters):
    c = collections.defaultdict(int)
    for _, i, _, _ in inters: c[i] += 1
    return c


def filter_kcore(inters: list[tuple], k_user: int, k_item: int) -> list[tuple]:
    """Recursive k-core filtering: drop users/items with < k_user/k_item interactions
    until the set is stable."""
    if not k_user and not k_item:
        return inters
    epoch = 0
    while True:
        epoch += 1
        u2c = get_user2count(inters)
        i2c = get_item2count(inters)
        good_users = {u for u, c in u2c.items() if c >= k_user}
        good_items = {i for i, c in i2c.items() if c >= k_item}
        n_drop_u = len(u2c) - len(good_users)
        n_drop_i = len(i2c) - len(good_items)
        if n_drop_u == 0 and n_drop_i == 0:
            break
        new = [t for t in inters if t[0] in good_users and t[1] in good_items]
        print(f"    epoch {epoch}: dropped {n_drop_u:,} users / {n_drop_i:,} items -> "
              f"{len(new):,} inters / {len(good_users):,} users / {len(good_items):,} items")
        if len(new) == len(inters):
            break
        inters = new
    return inters


def write_rating_only(out_path: Path, inters: list[tuple]) -> None:
    """Write user_id,parent_asin,rating,timestamp CSV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["user_id", "parent_asin", "rating", "timestamp"])
        for u, i, r, t in inters:
            w.writerow([u, i, r, t])
    print(f"  wrote {out_path}  ({len(inters):,} rows, {out_path.stat().st_size/1e6:.1f} MB)")


def write_last_out_split(out_dir: Path, prefix: str, inters: list[tuple]) -> None:
    """Leave-last-out per user: last interaction = test, 2nd-last = valid, rest = train."""
    out_dir.mkdir(parents=True, exist_ok=True)
    user2inters = collections.defaultdict(list)
    for inter in inters:
        user2inters[inter[0]].append(inter)
    train, valid, test = [], [], []
    for user, lst in user2inters.items():
        lst.sort(key=lambda d: d[3])
        if len(lst) < 3:
            # skip users with < 3 interactions — they have no train+valid+test
            continue
        train.extend(lst[:-2])
        valid.append(lst[-2])
        test.append(lst[-1])

    for split_name, split_inters in [("train", train), ("valid", valid), ("test", test)]:
        path = out_dir / f"{prefix}.{split_name}.csv"
        with path.open("w", encoding="utf-8", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(["user_id", "parent_asin", "rating", "timestamp"])
            for u, i, r, t in split_inters:
                w.writerow([u, i, r, t])
        print(f"  {split_name:>5}: {len(split_inters):,} rows -> {path.name}")


def process_category(category: str, k: int = 5) -> None:
    if category not in CATEGORIES:
        print(f"!! Unknown category {category}; known: {list(CATEGORIES)}")
        return
    subdir, fname = CATEGORIES[category]
    # subdir is interpreted relative to the OLD raw dir (`data/`) for the
    # original 4 categories; the proper benchmark categories use `../data_raw_proper/`
    # in their subdir, which resolves to `data_raw_proper/` from the repo root.
    raw_path = (RAW_DIR / subdir / fname).resolve()
    if not raw_path.exists():
        print(f"!! Raw file missing: {raw_path}")
        return

    t0 = time.time()
    print(f"\n{'='*70}\n  {category}  (raw: {raw_path}, {raw_path.stat().st_size/1e6:.0f} MB)\n{'='*70}")

    print(f"\n  [1/4] Loading raw reviews...")
    raw = load_ratings(raw_path)
    print(f"        {len(raw):,} raw interactions  ({time.time()-t0:.1f}s)")

    print(f"\n  [2/4] Deduplicating (user, item) pairs...")
    raw = make_inters_in_order(raw)
    print(f"        {len(raw):,} after dedup")

    print(f"\n  [3/4] {k}-core filtering (recursive, user_k={k}, item_k={k})...")
    kc = filter_kcore(raw, k_user=k, k_item=k)
    n_users = len({t[0] for t in kc}); n_items = len({t[1] for t in kc})
    print(f"        {len(kc):,} interactions / {n_users:,} users / {n_items:,} items")

    print(f"\n  [4/4] Writing rating_only + last_out splits...")
    out_root = OUT_DIR / f"{k}core"
    write_rating_only(out_root / "rating_only" / f"{category}.csv", kc)
    write_last_out_split(out_root / "last_out", category, kc)

    print(f"\n  Total: {time.time()-t0:.1f}s")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("categories", nargs="*",
                     default=list(CATEGORIES),
                     help="Categories to process (default: all known)")
    ap.add_argument("-k", type=int, default=5, help="k-core threshold (default 5)")
    args = ap.parse_args()
    for cat in args.categories:
        process_category(cat, k=args.k)
    print(f"\nAll done. Outputs under {OUT_DIR}/")


if __name__ == "__main__":
    main()
