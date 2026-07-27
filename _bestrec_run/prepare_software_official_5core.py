#!/usr/bin/env python3
"""Materialize the frozen Software official 5-core chronological LOO split."""

from __future__ import annotations

import csv
import gzip
import os
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data_raw_proper" / "software" / "Software.csv.gz"
RATING_OUT = ROOT / "data_5core" / "5core" / "rating_only" / "Software.csv"
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
FIELDS = ["user_id", "parent_asin", "rating", "timestamp"]


def atomic_csv(path: Path, rows) -> None:
    if path.exists():
        raise RuntimeError(f"output exists; refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    if partial.exists():
        raise RuntimeError(f"partial output exists; refusing reuse: {partial}")
    with partial.open("x", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows(rows)
    os.replace(partial, path)


def main() -> int:
    if not SOURCE.is_file():
        raise RuntimeError(f"missing source: {SOURCE}")
    histories: dict[str, list[tuple[int, int, tuple[str, str, str, str]]]] = defaultdict(list)
    rating_rows: list[tuple[str, str, str, str]] = []
    pairs: set[tuple[str, str]] = set()
    with gzip.open(SOURCE, "rt", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != FIELDS:
            raise RuntimeError(f"unexpected columns: {reader.fieldnames}")
        for order, row in enumerate(reader):
            user = row["user_id"]
            item = row["parent_asin"]
            pair = (user, item)
            if pair in pairs:
                raise RuntimeError(f"duplicate (user,item) pair at source row {order + 2}: {pair}")
            pairs.add(pair)
            timestamp = int(row["timestamp"])
            record = (user, item, row["rating"], row["timestamp"])
            rating_rows.append(record)
            histories[user].append((timestamp, order, record))
    if not rating_rows:
        raise RuntimeError("source contains no rows")

    train, valid, test = [], [], []
    for user in sorted(histories):
        history = sorted(histories[user], key=lambda value: (value[0], value[1]))
        if len(history) < 5:
            raise RuntimeError(f"official 5-core user has fewer than five interactions: {user}")
        records = [value[2] for value in history]
        train.extend(records[:-2])
        valid.append(records[-2])
        test.append(records[-1])

    atomic_csv(RATING_OUT, rating_rows)
    atomic_csv(SPLIT_DIR / "Software.train.csv", train)
    atomic_csv(SPLIT_DIR / "Software.valid.csv", valid)
    atomic_csv(SPLIT_DIR / "Software.test.csv", test)
    print(
        f"prepared Software: interactions={len(rating_rows)}, users={len(histories)}, "
        f"items={len({item for _, item in pairs})}, train={len(train)}, "
        f"valid={len(valid)}, test={len(test)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
