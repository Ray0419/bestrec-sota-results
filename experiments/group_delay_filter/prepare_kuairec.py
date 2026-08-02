#!/usr/bin/env python3
"""Prepare the preregistered KuaiRec big-matrix sequence with provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


ARCHIVE_URL = "https://zenodo.org/api/records/18164998/files/KuaiRec.zip/content"
ZENODO_DOI = "https://doi.org/10.5281/zenodo.18164998"
OFFICIAL_MD5 = "261550d472c48eff4990fb13c0e5bcf7"


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ARCHIVE_URL) as response, path.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)


def find_big_matrix(archive: zipfile.ZipFile) -> str:
    matches = [name for name in archive.namelist() if name.endswith("big_matrix.csv")]
    if len(matches) != 1:
        raise RuntimeError(f"expected one big_matrix.csv, found {matches}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--minimum-unique-items", type=int, default=5)
    args = parser.parse_args()

    download(args.archive)
    archive_md5 = file_hash(args.archive, "md5")
    if archive_md5 != OFFICIAL_MD5:
        raise RuntimeError(
            f"archive MD5 mismatch: expected {OFFICIAL_MD5}, found {archive_md5}")

    with zipfile.ZipFile(args.archive) as bundle:
        member = find_big_matrix(bundle)
        with bundle.open(member) as handle:
            frame = pd.read_csv(
                handle,
                usecols=["user_id", "video_id", "timestamp"],
                dtype={"user_id": "int32", "video_id": "int32", "timestamp": "float64"},
            )
    raw_rows = len(frame)
    if frame.isna().any().any():
        raise RuntimeError("required KuaiRec columns contain missing values")
    frame.sort_values(
        ["user_id", "timestamp", "video_id"], kind="mergesort", inplace=True)
    duplicate_pairs = int(frame.duplicated(["user_id", "video_id"]).sum())
    frame.drop_duplicates(["user_id", "video_id"], keep="first", inplace=True)
    counts = frame.groupby("user_id", sort=False).size()
    retained_users = counts[counts >= args.minimum_unique_items].index
    frame = frame[frame["user_id"].isin(retained_users)].copy()

    users = np.sort(frame["user_id"].unique())
    videos = np.sort(frame["video_id"].unique())
    video_map = {int(value): index + 1 for index, value in enumerate(videos)}
    lengths = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="ascii") as output:
        for new_user, (original_user, group) in enumerate(
            frame.groupby("user_id", sort=True), start=1
        ):
            items = [video_map[int(value)] for value in group["video_id"].to_numpy()]
            lengths.append(len(items))
            output.write(f"{new_user} {' '.join(map(str, items))}\n")

    lengths_array = np.asarray(lengths)
    artifact = {
        "protocol": "DEPTH_EGSP_KUAIREC_DATA_V1",
        "preregistration": str(args.preregistration.resolve()),
        "preregistration_sha256": file_hash(args.preregistration),
        "source": {
            "archive_url": ARCHIVE_URL,
            "zenodo_doi": ZENODO_DOI,
            "license": "CC BY 4.0",
            "archive_member": member,
            "official_archive_md5": OFFICIAL_MD5,
            "archive_md5": archive_md5,
            "archive_sha256": file_hash(args.archive),
        },
        "preprocessing": {
            "columns": ["user_id", "video_id", "timestamp"],
            "watch_ratio_threshold": None,
            "sort_key": ["user_id", "timestamp", "video_id"],
            "duplicate_pair_policy": "retain earliest event",
            "minimum_unique_items_per_user": args.minimum_unique_items,
            "id_mapping": "ascending retained original IDs, one-indexed",
            "split": "leave-last-two-out in downstream repository loader",
        },
        "raw_rows": raw_rows,
        "duplicate_user_video_rows_removed": duplicate_pairs,
        "retained": {
            "users": len(users),
            "items": len(videos),
            "interactions": int(lengths_array.sum()),
            "mean_sequence_length": float(lengths_array.mean()),
            "median_sequence_length": float(np.median(lengths_array)),
            "min_sequence_length": int(lengths_array.min()),
            "max_sequence_length": int(lengths_array.max()),
            "matrix_density": float(lengths_array.sum() / (len(users) * len(videos))),
        },
        "sequence_file": str(args.output.resolve()),
        "sequence_file_sha256": file_hash(args.output),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
