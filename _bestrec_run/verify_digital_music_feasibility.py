#!/usr/bin/env python3
"""Mechanical, outcome-free feasibility gate for prospective Digital Music V1."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "data_5core" / "5core"
OUT = ROOT / "_bestrec_run" / "digital_music_feasibility.json"
CATEGORY = "Digital_Music"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> list[tuple[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != ["user_id", "parent_asin", "rating", "timestamp"]:
            raise RuntimeError(f"unexpected columns in {path}: {reader.fieldnames}")
        return [(row["user_id"], row["parent_asin"]) for row in reader]


def main() -> int:
    paths = {
        "rating_only": BASE / "rating_only" / f"{CATEGORY}.csv",
        "train": BASE / "last_out" / f"{CATEGORY}.train.csv",
        "valid": BASE / "last_out" / f"{CATEGORY}.valid.csv",
        "test": BASE / "last_out" / f"{CATEGORY}.test.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing split files: {missing}")
    rows = {name: load(path) for name, path in paths.items()}

    rating_pairs = rows["rating_only"]
    split_names = ("train", "valid", "test")
    split_pairs = {name: set(rows[name]) for name in split_names}
    rating_users = {u for u, _ in rating_pairs}
    rating_items = {i for _, i in rating_pairs}
    train_counts = Counter(u for u, _ in rows["train"])
    user_sets = {name: {u for u, _ in rows[name]} for name in split_names}

    checks = {
        "minimum_users": len(rating_users) >= 1_000,
        "minimum_items": len(rating_items) >= 1_000,
        "minimum_interactions": len(rating_pairs) >= 10_000,
        "rating_pairs_unique": len(set(rating_pairs)) == len(rating_pairs),
        "valid_one_per_user": len(rows["valid"]) == len(user_sets["valid"]),
        "test_one_per_user": len(rows["test"]) == len(user_sets["test"]),
        "identical_split_user_sets": user_sets["train"] == user_sets["valid"] == user_sets["test"],
        "minimum_three_train_per_user": bool(train_counts) and min(train_counts.values()) >= 3,
        "no_train_valid_pair_overlap": split_pairs["train"].isdisjoint(split_pairs["valid"]),
        "no_train_test_pair_overlap": split_pairs["train"].isdisjoint(split_pairs["test"]),
        "no_valid_test_pair_overlap": split_pairs["valid"].isdisjoint(split_pairs["test"]),
        "split_rows_sum_to_rating_only": sum(len(rows[n]) for n in split_names) == len(rating_pairs),
        "split_pair_union_equals_rating_only": set().union(*(split_pairs[n] for n in split_names)) == set(rating_pairs),
    }
    passed = all(checks.values())
    payload = {
        "protocol": "PREREG_FIR_PROSPECTIVE_DM_V1_SELECTION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "category": CATEGORY,
        "verdict": "DM-V1-FEASIBLE" if passed else "DM-V1-FEASIBILITY-VOID",
        "counts": {
            "users": len(rating_users),
            "items": len(rating_items),
            "interactions": len(rating_pairs),
            "train": len(rows["train"]),
            "valid": len(rows["valid"]),
            "test": len(rows["test"]),
            "minimum_train_interactions_per_user": min(train_counts.values()) if train_counts else 0,
        },
        "checks": checks,
        "files": {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for name, path in paths.items()
        },
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if OUT.exists():
        raise RuntimeError(f"feasibility output already exists; refusing overwrite: {OUT}")
    OUT.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": payload["verdict"], "counts": payload["counts"], "checks": checks}, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
