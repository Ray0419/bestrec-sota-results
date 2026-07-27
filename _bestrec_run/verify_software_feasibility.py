#!/usr/bin/env python3
"""Mechanical outcome-free feasibility adjudicator for Software V2."""

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
OUT = ROOT / "_bestrec_run" / "software_feasibility.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> list[tuple[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        expected = ["user_id", "parent_asin", "rating", "timestamp"]
        if reader.fieldnames != expected:
            raise RuntimeError(f"unexpected columns in {path}: {reader.fieldnames}")
        return [(row["user_id"], row["parent_asin"]) for row in reader]


def main() -> int:
    paths = {
        "rating_only": BASE / "rating_only" / "Software.csv",
        "train": BASE / "last_out" / "Software.train.csv",
        "valid": BASE / "last_out" / "Software.valid.csv",
        "test": BASE / "last_out" / "Software.test.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing prepared files: {missing}")
    rows = {name: load(path) for name, path in paths.items()}
    split_names = ("train", "valid", "test")
    rating = rows["rating_only"]
    rating_set = set(rating)
    split_sets = {name: set(rows[name]) for name in split_names}
    users = {u for u, _ in rating}
    items = {i for _, i in rating}
    user_sets = {name: {u for u, _ in rows[name]} for name in split_names}
    train_counts = Counter(u for u, _ in rows["train"])
    checks = {
        "minimum_users": len(users) >= 50_000,
        "minimum_items": len(items) >= 10_000,
        "minimum_interactions": len(rating) >= 400_000,
        "rating_pairs_unique": len(rating_set) == len(rating),
        "valid_one_per_user": len(rows["valid"]) == len(user_sets["valid"]),
        "test_one_per_user": len(rows["test"]) == len(user_sets["test"]),
        "identical_split_user_sets": user_sets["train"] == user_sets["valid"] == user_sets["test"],
        "minimum_three_train_per_user": bool(train_counts) and min(train_counts.values()) >= 3,
        "no_train_valid_pair_overlap": split_sets["train"].isdisjoint(split_sets["valid"]),
        "no_train_test_pair_overlap": split_sets["train"].isdisjoint(split_sets["test"]),
        "no_valid_test_pair_overlap": split_sets["valid"].isdisjoint(split_sets["test"]),
        "split_rows_sum_to_rating_only": sum(len(rows[name]) for name in split_names) == len(rating),
        "split_pair_union_equals_rating_only": set().union(*(split_sets[n] for n in split_names)) == rating_set,
    }
    passed = all(checks.values())
    payload = {
        "protocol": "PREREG_FIR_PROSPECTIVE_SW_V2_PREPARATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "category": "Software",
        "verdict": "SW-V2-FEASIBLE" if passed else "SW-V2-FEASIBILITY-VOID",
        "counts": {
            "users": len(users),
            "items": len(items),
            "interactions": len(rating),
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
                "sha256": digest(path),
            }
            for name, path in paths.items()
        },
    }
    if OUT.exists():
        raise RuntimeError(f"feasibility output exists; refusing overwrite: {OUT}")
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": payload["verdict"], "counts": payload["counts"], "checks": checks}, indent=2))
    return 0 if passed else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
