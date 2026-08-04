#!/usr/bin/env python3
"""Create the frozen private catalog map for the WEARec comparator phase.

This is a pre-freeze preparation step.  It reads all three already outcome-known
Video_Games split files solely to freeze the transductive catalog identity map.
The private map contains ASINs and is never deposited; the public manifest
contains only counts and cryptographic identities.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
PRIVATE = ROOT / "_bestrec_run" / "wearec_baseline_v1_private"
CATALOG = PRIVATE / "catalog.json"
MANIFEST = ROOT / "_bestrec_run" / "wearec_baseline_v1_catalog_manifest.json"
SPLIT_HASHES = {
    "train": "536866c7b3cb21ff4a1c2139ecb1e393c2ea468c4efe63ff1cfde51b0bcaa8d3",
    "valid": "b70d195ab3b9f76082854671e0e6a94c444302db6169d4074f112695d1467711",
    "test": "5a21bbcb5106d48cca21e90bbb6c417e1b95ac406321cd300c7800759dbaa496",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(tmp, path)


def main() -> int:
    if CATALOG.exists() or MANIFEST.exists():
        raise SystemExit("refusing to overwrite an existing V1 catalog or manifest")
    items: set[str] = set()
    users_by_split: dict[str, set[str]] = {}
    items_by_split: dict[str, set[str]] = {}
    rows: dict[str, int] = {}
    for split, expected in SPLIT_HASHES.items():
        path = SPLIT_DIR / f"Video_Games.{split}.csv"
        if sha256(path) != expected:
            raise SystemExit(f"split hash mismatch: {path}")
        split_users: set[str] = set()
        split_items: set[str] = set()
        n = 0
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                n += 1
                split_users.add(row["user_id"])
                split_items.add(row["parent_asin"])
        users_by_split[split] = split_users
        items_by_split[split] = split_items
        rows[split] = n
        items.update(split_items)
    train_valid_users = users_by_split["train"] | users_by_split["valid"]
    train_valid_items = items_by_split["train"] | items_by_split["valid"]
    catalog = {
        "protocol": "PREREG_WEAREC_BASELINE_V1",
        "mapping": "one_based_lexicographic_asin; zero_reserved_for_padding",
        "items": sorted(items),
    }
    atomic_json(CATALOG, catalog)
    catalog_hash = sha256(CATALOG)
    manifest = {
        "protocol": "PREREG_WEAREC_BASELINE_V1",
        "scope": "prefreeze transductive catalog identity only; no endpoint values",
        "split_sha256": SPLIT_HASHES,
        "rows": rows,
        "users": {key: len(value) for key, value in users_by_split.items()},
        "items": {key: len(value) for key, value in items_by_split.items()},
        "catalog_items": len(items),
        "test_only_users_vs_train_valid": len(users_by_split["test"] - train_valid_users),
        "test_only_items_vs_train_valid": len(items_by_split["test"] - train_valid_items),
        "private_catalog_sha256": catalog_hash,
    }
    atomic_json(MANIFEST, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
