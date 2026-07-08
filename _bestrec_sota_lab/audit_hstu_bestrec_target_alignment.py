"""Audit HSTU-BLaIR target alignment against the BEST-Rec Video_Games test split.

The corrected HSTU export is in BEST-Rec user/item id space, but the HSTU
preprocessor may still choose a different leave-last target for a tiny number
of users because of protocol or timestamp-tie differences. This script compares
HSTU target_item_id values directly against BEST-Rec's test CSV target after
reconstructing BEST-Rec's sorted user/item id maps.
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


def read_split(path: Path) -> list[tuple[str, str, float, int]]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append((row["user_id"], row["parent_asin"], float(row["rating"]), int(row["timestamp"])))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-jsonl", required=True)
    parser.add_argument("--split-dir", default="data_5core/5core/last_out")
    parser.add_argument("--category", default="Video_Games")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    hstu_path = Path(args.hstu_jsonl)
    split_dir = Path(args.split_dir)
    out_path = Path(args.out)
    train_path = split_dir / f"{args.category}.train.csv"
    valid_path = split_dir / f"{args.category}.valid.csv"
    test_path = split_dir / f"{args.category}.test.csv"

    train_rows = read_split(train_path)
    valid_rows = read_split(valid_path)
    test_rows = read_split(test_path)
    all_rows = train_rows + valid_rows + test_rows
    users = sorted({row[0] for row in all_rows})
    items = sorted({row[1] for row in all_rows})
    user_to_bestrec = {user: idx for idx, user in enumerate(users)}
    item_to_bestrec = {item: idx for idx, item in enumerate(items)}
    bestrec_to_user = {idx: user for user, idx in user_to_bestrec.items()}
    bestrec_to_item = {idx: item for item, idx in item_to_bestrec.items()}
    bestrec_test_targets = {user_to_bestrec[user]: item_to_bestrec[item] for user, item, _, _ in test_rows}

    hstu_targets: dict[int, int] = {}
    with hstu_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("user_id_convention") != "bestrec_zero_based_user_ids":
                raise ValueError(f"HSTU row {line_number} is not in BEST-Rec user id space")
            if row.get("item_id_convention") != "bestrec_zero_based_item_ids":
                raise ValueError(f"HSTU row {line_number} is not in BEST-Rec item id space")
            user_id = int(row["user_id"])
            if user_id in hstu_targets:
                raise ValueError(f"Duplicate HSTU user_id={user_id}")
            hstu_targets[user_id] = int(row["target_item_id"])

    mismatches = []
    missing_from_hstu = sorted(set(bestrec_test_targets) - set(hstu_targets))
    extra_in_hstu = sorted(set(hstu_targets) - set(bestrec_test_targets))
    for user_id in sorted(set(bestrec_test_targets) & set(hstu_targets)):
        expected = bestrec_test_targets[user_id]
        observed = hstu_targets[user_id]
        if expected != observed:
            mismatches.append(
                {
                    "bestrec_user_id": user_id,
                    "raw_user_id": bestrec_to_user[user_id],
                    "bestrec_test_target_item_id": expected,
                    "bestrec_test_target_asin": bestrec_to_item[expected],
                    "hstu_target_item_id": observed,
                    "hstu_target_asin": bestrec_to_item[observed],
                }
            )

    payload = {
        "schema_version": 1,
        "status": "complete" if not missing_from_hstu and not extra_in_hstu else "incomplete_user_overlap",
        "dataset": args.category,
        "counts": {
            "bestrec_test_users": len(bestrec_test_targets),
            "hstu_users": len(hstu_targets),
            "common_users": len(set(bestrec_test_targets) & set(hstu_targets)),
            "target_mismatches": len(mismatches),
            "missing_from_hstu": len(missing_from_hstu),
            "extra_in_hstu": len(extra_in_hstu),
        },
        "target_mismatches_first20": mismatches[:20],
        "missing_from_hstu_first20": missing_from_hstu[:20],
        "extra_in_hstu_first20": extra_in_hstu[:20],
        "interpretation": (
            "HSTU and BEST-Rec have matching user coverage after id translation, "
            "but any target mismatch means paired diagnostics must exclude or explicitly disclose those users."
        ),
        "inputs": {
            "hstu_jsonl": sha256_file(hstu_path),
            "train_csv": sha256_file(train_path),
            "valid_csv": sha256_file(valid_path),
            "test_csv": sha256_file(test_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
