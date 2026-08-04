"""Build an ASIN/user-id based HSTU-BLaIR to BEST-Rec Video_Games user map.

Run inside WSL from the HSTU-BLaIR source checkout. HSTU's data_maps user ids
are zero-based internal ids. BEST-Rec's sequential runner rebuilds zero-based
user ids by sorting the raw user_id strings from the train/valid/test splits.
Per-user comparisons or ensembles must translate HSTU user ids through the raw
user ids, just as item ids are translated through ASINs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    record.update({"sha256": digest.hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return record


def load_hstu_user_map(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "user2id" in payload:
        raw = payload["user2id"]
    elif "user_id" in payload:
        raw = payload["user_id"]
    else:
        dict_values = [value for value in payload.values() if isinstance(value, dict)]
        candidates: list[dict[str, Any]] = []
        for block in dict_values:
            sample = list(block.items())[:5]
            if sample and all(isinstance(key, str) and isinstance(value, int) for key, value in sample):
                candidates.append(block)
        if not candidates:
            raise ValueError(f"Could not find user map in {path}; keys={list(payload)[:20]}")
        raw = max(candidates, key=len)
    return {str(key): int(value) for key, value in raw.items()}


def load_bestrec_user_map(split_dir: Path, category: str) -> dict[str, int]:
    users: set[str] = set()
    for split in ("train", "valid", "test"):
        path = split_dir / f"{category}.{split}.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if "user_id" not in (reader.fieldnames or []):
                raise ValueError(f"{path} missing user_id column")
            for row in reader:
                users.add(str(row["user_id"]))
    return {user_id: idx for idx, user_id in enumerate(sorted(users))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-data-maps", default="tmp/amzn23_game/data_maps")
    parser.add_argument("--bestrec-split-dir", default="/mnt/c/Users/rayxc/Documents/R/data_5core/5core/last_out")
    parser.add_argument("--category", default="Video_Games")
    parser.add_argument("--out", default="/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json")
    args = parser.parse_args()

    hstu_path = Path(args.hstu_data_maps)
    split_dir = Path(args.bestrec_split_dir)
    out_path = Path(args.out)

    hstu_user_to_zero = load_hstu_user_map(hstu_path)
    bestrec_user_to_zero = load_bestrec_user_map(split_dir, args.category)
    hstu_users = set(hstu_user_to_zero)
    bestrec_users = set(bestrec_user_to_zero)
    common_users = hstu_users & bestrec_users
    missing_from_hstu = sorted(bestrec_users - hstu_users)
    missing_from_bestrec = sorted(hstu_users - bestrec_users)

    status = "complete_bijection" if not missing_from_hstu and not missing_from_bestrec else "incomplete_user_set_overlap"

    max_hstu_zero = max(hstu_user_to_zero.values()) if hstu_user_to_zero else -1
    max_bestrec_zero = max(bestrec_user_to_zero.values()) if bestrec_user_to_zero else -1
    hstu_zero_based_to_bestrec_zero_based: list[int | None] = [None] * (max_hstu_zero + 1)
    bestrec_zero_based_to_hstu_zero_based: list[int | None] = [None] * (max_bestrec_zero + 1)

    translated_pairs = []
    for raw_user_id in sorted(common_users):
        hstu_zero = hstu_user_to_zero[raw_user_id]
        bestrec_zero = bestrec_user_to_zero[raw_user_id]
        hstu_zero_based_to_bestrec_zero_based[hstu_zero] = bestrec_zero
        bestrec_zero_based_to_hstu_zero_based[bestrec_zero] = hstu_zero
        translated_pairs.append((raw_user_id, hstu_zero, bestrec_zero))

    unmapped_hstu_ids = [idx for idx, value in enumerate(hstu_zero_based_to_bestrec_zero_based) if value is None]
    unmapped_bestrec_ids = [idx for idx, value in enumerate(bestrec_zero_based_to_hstu_zero_based) if value is None]
    if unmapped_hstu_ids or unmapped_bestrec_ids:
        status = "incomplete_id_bijection"

    naive_mismatches = [
        {"raw_user_id": raw_user_id, "hstu_zero_based": hstu_zero, "bestrec_zero_based": bestrec_zero}
        for raw_user_id, hstu_zero, bestrec_zero in translated_pairs
        if hstu_zero != bestrec_zero
    ]

    payload = {
        "schema_version": 1,
        "dataset": args.category,
        "status": status,
        "id_spaces": {
            "hstu_user_ids": "zero_based_internal_ids",
            "bestrec_user_ids": "zero_based_sorted_raw_user_ids",
        },
        "tested_naive_rule": "bestrec_user_id = hstu_user_id",
        "naive_rule_valid": not naive_mismatches and status == "complete_bijection",
        "required_translation": "bestrec_user_id = bestrec_user2idx[hstu_id2user[hstu_user_id]]",
        "counts": {
            "hstu_users": len(hstu_user_to_zero),
            "bestrec_users": len(bestrec_user_to_zero),
            "common_users": len(common_users),
            "hstu_zero_based_to_bestrec_zero_based_entries": len(hstu_zero_based_to_bestrec_zero_based),
            "bestrec_zero_based_to_hstu_zero_based_entries": len(bestrec_zero_based_to_hstu_zero_based),
            "naive_rule_mismatches": len(naive_mismatches),
        },
        "hstu_zero_based_to_bestrec_zero_based": hstu_zero_based_to_bestrec_zero_based,
        "bestrec_zero_based_to_hstu_zero_based": bestrec_zero_based_to_hstu_zero_based,
        "sample_first10_by_raw_user_id": [
            {
                "raw_user_id": raw_user_id,
                "hstu_zero_based": hstu_zero,
                "bestrec_zero_based": bestrec_zero,
            }
            for raw_user_id, hstu_zero, bestrec_zero in translated_pairs[:10]
        ],
        "naive_mismatches_first20": naive_mismatches[:20],
        "missing_from_hstu_first20": missing_from_hstu[:20],
        "missing_from_bestrec_first20": missing_from_bestrec[:20],
        "unmapped_hstu_zero_based_ids_first20": unmapped_hstu_ids[:20],
        "unmapped_bestrec_zero_based_ids_first20": unmapped_bestrec_ids[:20],
        "inputs": {
            "hstu_data_maps": sha256_file(hstu_path),
            "bestrec_train_csv": sha256_file(split_dir / f"{args.category}.train.csv"),
            "bestrec_valid_csv": sha256_file(split_dir / f"{args.category}.valid.csv"),
            "bestrec_test_csv": sha256_file(split_dir / f"{args.category}.test.csv"),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("schema_version", "dataset", "status", "naive_rule_valid", "counts")}, indent=2, sort_keys=True))
    return 0 if status == "complete_bijection" else 1


if __name__ == "__main__":
    raise SystemExit(main())
