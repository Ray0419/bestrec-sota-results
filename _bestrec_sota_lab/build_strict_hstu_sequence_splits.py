"""Build HSTU-compatible sequence files with a genuine validation holdout.

The upstream HSTU-BLaIR Amazon wrapper trains on the second-last item and
evaluates on the last item. For BEST-Rec, the second-last item is validation,
so that protocol contaminates validation-selected fusion. This script builds
strict sequence CSVs from BEST-Rec last-out splits:

  - train sequence excludes validation and test targets;
  - validation sequence includes train history plus validation target;
  - test sequence includes train + validation history plus test target.

The files use HSTU's `sasrec_format.csv` column style and BEST-Rec raw id
strings mapped into HSTU's internal user/item ids through the validated ASIN and
raw-user maps. They are a data artifact for future HSTU-compatible retraining;
they do not by themselves produce a scored comparator.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import defaultdict
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


def read_split(path: Path) -> list[tuple[str, str, float, int]]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append((row["user_id"], row["parent_asin"], float(row["rating"]), int(row["timestamp"])))
    return rows


def load_map(path: Path, key: str) -> list[int | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete_bijection":
        raise ValueError(f"{path} status is {payload.get('status')}, expected complete_bijection")
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError(f"{path} missing {key}")
    return [None if value is None else int(value) for value in values]


def bestrec_maps(rows: list[tuple[str, str, float, int]]) -> tuple[dict[str, int], dict[str, int]]:
    users = sorted({row[0] for row in rows})
    items = sorted({row[1] for row in rows})
    return {user: idx for idx, user in enumerate(users)}, {item: idx for idx, item in enumerate(items)}


def invert(values: list[int | None]) -> dict[int, int]:
    out = {}
    for idx, value in enumerate(values):
        if value is not None:
            out[value] = idx
    return out


def write_hstu_sequence_csv(path: Path, user_sequences: dict[int, list[tuple[int, float, int]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["user_id", "sequence_item_ids", "sequence_ratings", "sequence_timestamps"])
        writer.writeheader()
        for hstu_user_id in sorted(user_sequences):
            seq = sorted(user_sequences[hstu_user_id], key=lambda row: row[2])
            writer.writerow(
                {
                    "user_id": hstu_user_id,
                    "sequence_item_ids": ",".join(str(item_id) for item_id, _, _ in seq),
                    "sequence_ratings": ",".join(str(float(rating)) for _, rating, _ in seq),
                    "sequence_timestamps": ",".join(str(timestamp) for _, _, timestamp in seq),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-dir", default="data_5core/5core/last_out")
    parser.add_argument("--category", default="Video_Games")
    parser.add_argument("--item-map", default="_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json")
    parser.add_argument("--user-map", default="_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json")
    parser.add_argument("--out-dir", default="_bestrec_sota_lab/runs/hstu_strict_protocol_data_20260609")
    args = parser.parse_args()

    split_dir = Path(args.split_dir)
    train_path = split_dir / f"{args.category}.train.csv"
    valid_path = split_dir / f"{args.category}.valid.csv"
    test_path = split_dir / f"{args.category}.test.csv"
    train_rows = read_split(train_path)
    valid_rows = read_split(valid_path)
    test_rows = read_split(test_path)
    all_rows = train_rows + valid_rows + test_rows
    bestrec_user, bestrec_item = bestrec_maps(all_rows)
    hstu_item_to_bestrec = load_map(Path(args.item_map), "hstu_one_based_to_bestrec_zero_based")
    hstu_user_to_bestrec = load_map(Path(args.user_map), "hstu_zero_based_to_bestrec_zero_based")
    bestrec_item_to_hstu_zero = {bestrec_id: hstu_one - 1 for bestrec_id, hstu_one in invert(hstu_item_to_bestrec).items()}
    bestrec_user_to_hstu_zero = invert(hstu_user_to_bestrec)

    by_user: dict[int, list[tuple[int, float, int, str]]] = defaultdict(list)
    for user_raw, asin, rating, timestamp in all_rows:
        bu = bestrec_user[user_raw]
        bi = bestrec_item[asin]
        hstu_user = bestrec_user_to_hstu_zero[bu]
        hstu_item = bestrec_item_to_hstu_zero[bi]
        by_user[hstu_user].append((hstu_item, rating, timestamp, asin))

    strict_train: dict[int, list[tuple[int, float, int]]] = {}
    strict_valid: dict[int, list[tuple[int, float, int]]] = {}
    strict_test: dict[int, list[tuple[int, float, int]]] = {}
    too_short = []
    validation_targets = {}
    test_targets = {}
    for hstu_user, rows in by_user.items():
        ordered = sorted(rows, key=lambda row: row[2])
        if len(ordered) < 5:
            too_short.append(hstu_user)
            continue
        strict_train[hstu_user] = [(item, rating, timestamp) for item, rating, timestamp, _ in ordered[:-2]]
        strict_valid[hstu_user] = [(item, rating, timestamp) for item, rating, timestamp, _ in ordered[:-1]]
        strict_test[hstu_user] = [(item, rating, timestamp) for item, rating, timestamp, _ in ordered]
        validation_targets[hstu_user] = ordered[-2][0]
        test_targets[hstu_user] = ordered[-1][0]

    out_dir = Path(args.out_dir)
    train_out = out_dir / "sasrec_format_train_strict.csv"
    valid_out = out_dir / "sasrec_format_valid_strict.csv"
    test_out = out_dir / "sasrec_format_test_strict.csv"
    write_hstu_sequence_csv(train_out, strict_train)
    write_hstu_sequence_csv(valid_out, strict_valid)
    write_hstu_sequence_csv(test_out, strict_test)

    payload = {
        "schema_version": 1,
        "status": "complete",
        "dataset": args.category,
        "generated_at_unix": time.time(),
        "purpose": "Strict HSTU-compatible data files with a real BEST-Rec validation holdout.",
        "protocol": {
            "train_file": "history excludes BEST-Rec validation and test targets",
            "valid_file": "history includes train plus validation target; DatasetV2(ignore_last_n=0) predicts validation",
            "test_file": "history includes train plus validation plus test target; DatasetV2(ignore_last_n=0) predicts test",
            "recommended_training": "Train on train_file with DatasetV2(ignore_last_n=0), select on valid_file, final report on test_file.",
        },
        "counts": {
            "users": len(by_user),
            "strict_train_users": len(strict_train),
            "strict_valid_users": len(strict_valid),
            "strict_test_users": len(strict_test),
            "too_short_users": len(too_short),
            "items": len(bestrec_item),
        },
        "outputs": {
            "train": sha256_file(train_out),
            "valid": sha256_file(valid_out),
            "test": sha256_file(test_out),
        },
        "inputs": {
            "bestrec_train_csv": sha256_file(train_path),
            "bestrec_valid_csv": sha256_file(valid_path),
            "bestrec_test_csv": sha256_file(test_path),
            "item_map": sha256_file(Path(args.item_map)),
            "user_map": sha256_file(Path(args.user_map)),
        },
        "leakage_note": (
            "These files are not compatible with the already-trained HSTU checkpoint. "
            "They are for a future retrain where validation targets are not training labels."
        ),
        "sample": {
            "first_user": next(iter(sorted(strict_train))) if strict_train else None,
        },
    }
    summary_path = out_dir / "strict_hstu_sequence_splits_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
