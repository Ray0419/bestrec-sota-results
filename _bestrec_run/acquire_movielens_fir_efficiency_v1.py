# -*- coding: utf-8 -*-
"""Acquire and deterministically split MovieLens 1M after protocol freeze.

The MovieLens 1M README prohibits redistribution without separate permission.
Accordingly, every record-level artifact is written below the ignored private
directory.  Only aggregate provenance and cryptographic digests may be copied
into the public evidence graph after adjudication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
import urllib.request
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"
OFFICIAL_MD5 = "c4d9eecfca2ab87c1945afe126590906"
PRIVATE_ROOT = HERE / "private_ml1m_v1"
VIEWS = {
    "MovieLens1M_R4": 4,
    "MovieLens1M_ALL": 1,
}
TIME_FRACTION = 0.90
MIN_TRAIN_EVENTS = 5
MIN_TRAIN_ITEM_COUNT = 5


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_events(path: Path, min_rating: int):
    events = []
    with path.open("r", encoding="latin-1") as fh:
        for line_no, line in enumerate(fh, 1):
            fields = line.rstrip("\n").split("::")
            if len(fields) != 4:
                raise RuntimeError(f"malformed ratings.dat line {line_no}")
            user, movie, rating, timestamp = map(int, fields)
            if rating >= min_rating:
                events.append((timestamp, user, movie, rating))
    if not events:
        raise RuntimeError("rating filter produced no events")
    events.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    return events


def build_view(events, category: str, split_root: Path):
    cutoff_index = int(math.ceil(TIME_FRACTION * len(events))) - 1
    cutoff = events[cutoff_index][0]
    by_user = defaultdict(list)
    for event in events:
        by_user[event[1]].append(event)

    candidates = {}
    item_counts = Counter()
    for user, rows in by_user.items():
        pre = [row for row in rows if row[0] <= cutoff]
        post = [row for row in rows if row[0] > cutoff]
        if len(pre) < MIN_TRAIN_EVENTS + 1 or not post:
            continue
        train, valid, test = pre[:-1], pre[-1], post[0]
        candidates[user] = (train, valid, test)
        item_counts.update(row[2] for row in train)

    catalog = {
        item for item, count in item_counts.items()
        if count >= MIN_TRAIN_ITEM_COUNT
    }
    retained = {}
    for user, (train, valid, test) in candidates.items():
        train = [row for row in train if row[2] in catalog]
        if (len(train) >= MIN_TRAIN_EVENTS
                and valid[2] in catalog and test[2] in catalog):
            retained[user] = (train, valid, test)
    # Close the catalog/user eligibility loop using only pre-cutoff training
    # events.  This guarantees the eventual TRAIN file itself contains every
    # VALID/TEST item and user, so training can construct its maps without ever
    # opening TEST.  Iterate to a fixed point because removing users can lower
    # an item's retained-training count below the five-event floor.
    while retained:
        retained_counts = Counter(
            row[2] for train, _, _ in retained.values() for row in train)
        retained_catalog = {
            item for item, count in retained_counts.items()
            if count >= MIN_TRAIN_ITEM_COUNT
        }
        updated = {}
        for user, (train, valid, test) in retained.items():
            train = [row for row in train if row[2] in retained_catalog]
            if (len(train) >= MIN_TRAIN_EVENTS
                    and valid[2] in retained_catalog
                    and test[2] in retained_catalog):
                updated[user] = (train, valid, test)
        if (set(updated) == set(retained)
                and all(len(updated[user][0]) == len(retained[user][0])
                        for user in updated)):
            retained = updated
            catalog = retained_catalog
            break
        retained = updated
    if not retained:
        raise RuntimeError(f"{category}: deterministic split retained no users")
    train_users = set(retained)
    train_items = {row[2] for train, _, _ in retained.values() for row in train}
    if any(user not in train_users or valid[2] not in train_items
           or test[2] not in train_items
           for user, (_, valid, test) in retained.items()):
        raise RuntimeError(f"{category}: sealed-map closure invariant failed")

    split_root.mkdir(parents=True, exist_ok=True)
    paths = {
        split: split_root / f"{category}.{split}.csv"
        for split in ("train", "valid", "test")
    }
    collision = [str(path) for path in paths.values() if path.exists()]
    if collision:
        raise FileExistsError("refusing to overwrite split(s): " + ", ".join(collision))

    header = ["user_id", "parent_asin", "rating", "timestamp"]
    counts = {}
    for split, path in paths.items():
        n = 0
        with path.open("x", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=header)
            writer.writeheader()
            for user in sorted(retained):
                rows = retained[user][{"train": 0, "valid": 1, "test": 2}[split]]
                if split != "train":
                    rows = [rows]
                for timestamp, _, movie, rating in rows:
                    writer.writerow({
                        "user_id": f"ml1m_u{user}",
                        "parent_asin": f"ml1m_i{movie}",
                        "rating": rating,
                        # The inherited trainer expects milliseconds on disk.
                        "timestamp": timestamp * 1000,
                    })
                    n += 1
        counts[split] = n

    return {
        "category": category,
        "time_fraction": TIME_FRACTION,
        "cutoff_timestamp_s": cutoff,
        "min_train_events": MIN_TRAIN_EVENTS,
        "min_train_item_count": MIN_TRAIN_ITEM_COUNT,
        "n_filtered_events": len(events),
        "n_candidate_users": len(candidates),
        "n_users": len(retained),
        "n_train_catalog_items": len(catalog),
        "n_rows": counts,
        "split_sha256": {name: digest(path) for name, path in paths.items()},
    }


def acquire(private_root: Path):
    private_root.mkdir(parents=True, exist_ok=True)
    archive = private_root / "ml-1m.zip"
    if archive.exists():
        if digest(archive, "md5") != OFFICIAL_MD5:
            raise RuntimeError("existing ml-1m.zip fails the official MD5")
    else:
        tmp = private_root / "ml-1m.zip.part"
        if tmp.exists():
            raise RuntimeError("incomplete .part download exists; inspect it manually")
        urllib.request.urlretrieve(URL, tmp)
        if digest(tmp, "md5") != OFFICIAL_MD5:
            raise RuntimeError("downloaded ml-1m.zip fails the official MD5")
        os.replace(tmp, archive)

    ratings = private_root / "ml-1m" / "ratings.dat"
    if not ratings.exists():
        with zipfile.ZipFile(archive) as zf:
            member = "ml-1m/ratings.dat"
            if member not in zf.namelist():
                raise RuntimeError("archive lacks ml-1m/ratings.dat")
            zf.extract(member, private_root)

    split_root = private_root / "splits"
    view_records = {}
    for category, threshold in VIEWS.items():
        view_records[category] = build_view(
            read_events(ratings, threshold), category, split_root)
        view_records[category]["minimum_rating"] = threshold

    provenance = {
        "protocol": "PREREG_FIR_EFFICIENCY_ML1M_V1",
        "source_url": URL,
        "source_official_md5": OFFICIAL_MD5,
        "source_observed_md5": digest(archive, "md5"),
        "source_observed_sha256": digest(archive),
        "ratings_dat_sha256": digest(ratings),
        "redistribution": "record-level artifacts remain private under the ML-1M README",
        "views": view_records,
    }
    path = private_root / "split_provenance.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, indent=2))


def preflight(private_root: Path):
    print("MovieLens 1M acquisition preflight")
    print("  URL:", URL)
    print("  official MD5:", OFFICIAL_MD5)
    print("  private root:", private_root)
    print("  record redistribution: prohibited without separate permission")
    existing = [p for p in (
        private_root / "ml-1m.zip",
        private_root / "ml-1m" / "ratings.dat",
        private_root / "split_provenance.json",
    ) if p.exists()]
    print("  existing protected artifacts:", len(existing))
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, default=PRIVATE_ROOT)
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    if not args.acquire:
        return preflight(args.private_root)
    acquire(args.private_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
