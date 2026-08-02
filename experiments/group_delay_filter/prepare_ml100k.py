#!/usr/bin/env python3
"""Prepare the preregistered ML-100K sequence file with provenance hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ARCHIVE_URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
README_URL = "https://files.grouplens.org/datasets/movielens/ml-100k-README.txt"
OFFICIAL_MD5 = "0e33842e24a9c977be4e0107933c0723"


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_archive(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ARCHIVE_URL) as response, path.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)


def read_rows(archive: Path) -> list[tuple[int, int, int]]:
    with zipfile.ZipFile(archive) as bundle:
        with bundle.open("ml-100k/u.data") as handle:
            rows = []
            for raw in handle:
                user, item, _rating, timestamp = raw.decode("ascii").split("\t")
                rows.append((int(user), int(item), int(timestamp)))
    return rows


def iterative_k_core(
    rows: list[tuple[int, int, int]], k: int
) -> tuple[list[tuple[int, int, int]], int]:
    retained = rows
    rounds = 0
    while True:
        user_count = Counter(user for user, _item, _time in retained)
        item_count = Counter(item for _user, item, _time in retained)
        filtered = [
            row for row in retained
            if user_count[row[0]] >= k and item_count[row[1]] >= k
        ]
        if len(filtered) == len(retained):
            return retained, rounds
        retained = filtered
        rounds += 1


def write_sequences(rows: list[tuple[int, int, int]], output: Path) -> dict:
    original_users = sorted({user for user, _item, _time in rows})
    original_items = sorted({item for _user, item, _time in rows})
    user_map = {value: index + 1 for index, value in enumerate(original_users)}
    item_map = {value: index + 1 for index, value in enumerate(original_items)}
    grouped: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for user, item, timestamp in rows:
        grouped[user].append((timestamp, item))

    lengths = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="ascii") as handle:
        for original_user in original_users:
            ordered = sorted(grouped[original_user], key=lambda pair: (pair[0], pair[1]))
            items = [item_map[item] for _timestamp, item in ordered]
            lengths.append(len(items))
            handle.write(f"{user_map[original_user]} {' '.join(map(str, items))}\n")

    return {
        "users": len(original_users),
        "items": len(original_items),
        "interactions": len(rows),
        "mean_sequence_length": sum(lengths) / len(lengths),
        "min_sequence_length": min(lengths),
        "max_sequence_length": max(lengths),
        "matrix_density": len(rows) / (len(original_users) * len(original_items)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--k-core", type=int, default=5)
    args = parser.parse_args()

    download_archive(args.archive)
    archive_md5 = file_hash(args.archive, "md5")
    if archive_md5 != OFFICIAL_MD5:
        raise RuntimeError(
            f"archive MD5 mismatch: expected {OFFICIAL_MD5}, found {archive_md5}")

    raw_rows = read_rows(args.archive)
    retained, rounds = iterative_k_core(raw_rows, args.k_core)
    stats = write_sequences(retained, args.output)
    manifest = {
        "protocol": "EGSP_ML100K_DATA_V1",
        "preregistration": str(args.preregistration.resolve()),
        "preregistration_sha256": file_hash(args.preregistration, "sha256"),
        "source": {
            "archive_url": ARCHIVE_URL,
            "readme_url": README_URL,
            "official_archive_md5": OFFICIAL_MD5,
            "archive_md5": archive_md5,
            "archive_sha256": file_hash(args.archive, "sha256"),
        },
        "preprocessing": {
            "include_all_ratings": True,
            "sort_key": ["timestamp", "original_item_id"],
            "iterative_user_item_k_core": args.k_core,
            "k_core_filter_rounds": rounds,
            "id_mapping": "ascending retained original IDs, one-indexed",
            "split": "leave-last-two-out in downstream repository loader",
        },
        "raw_interactions": len(raw_rows),
        "retained": stats,
        "sequence_file": str(args.output.resolve()),
        "sequence_file_sha256": file_hash(args.output, "sha256"),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
