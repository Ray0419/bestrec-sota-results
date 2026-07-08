"""Audit HSTU-BLaIR train/eval targets against BEST-Rec valid/test splits.

HSTU-BLaIR's Amazon dataset wrapper builds:
  - train_dataset with ignore_last_n=1, whose target is the second-last item;
  - eval_dataset with ignore_last_n=0, whose target is the last item.

BEST-Rec's leave-last-out files treat the second-last item as validation and
the last item as test. This script compares HSTU's generated targets against
BEST-Rec valid/test targets after translating HSTU user/item ids into BEST-Rec
id space. If the HSTU train target equals BEST-Rec validation, then HSTU has no
clean validation-query export for choosing fusion weights without leakage.
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


def load_mapping(path: Path, key: str) -> list[int | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete_bijection":
        raise ValueError(f"{path} is not a complete bijection: {payload.get('status')}")
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError(f"{path} missing {key}")
    return [None if value is None else int(value) for value in values]


def parse_sequence(value: str) -> list[int]:
    text = value.strip()
    if not text:
        return []
    if text.startswith("["):
        parsed = json.loads(text)
        return [int(item) for item in parsed]
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def translate_item(mapping: list[int | None], hstu_one_based: int) -> int:
    value = mapping[hstu_one_based]
    if value is None:
        raise ValueError(f"Unmapped HSTU item id {hstu_one_based}")
    return value


def translate_user(mapping: list[int | None], hstu_zero_based: int) -> int:
    value = mapping[hstu_zero_based]
    if value is None:
        raise ValueError(f"Unmapped HSTU user id {hstu_zero_based}")
    return value


def hstu_targets_from_sasrec_format(path: Path, item_map: list[int | None], user_map: list[int | None]) -> tuple[dict[int, int], dict[int, int]]:
    train_targets: dict[int, int] = {}
    eval_targets: dict[int, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hstu_user = int(row["user_id"])
            bestrec_user = translate_user(user_map, hstu_user)
            item_seq = parse_sequence(row["sequence_item_ids"])
            if len(item_seq) < 2:
                continue
            # HSTU shifts item ids by +1 inside DatasetV2; map through that convention.
            train_targets[bestrec_user] = translate_item(item_map, int(item_seq[-2]) + 1)
            eval_targets[bestrec_user] = translate_item(item_map, int(item_seq[-1]) + 1)
    return train_targets, eval_targets


def compare_targets(left: dict[int, int], right: dict[int, int], bestrec_to_user: dict[int, str], bestrec_to_item: dict[int, str]) -> dict[str, Any]:
    common = set(left) & set(right)
    mismatches = []
    for user_id in sorted(common):
        if left[user_id] != right[user_id]:
            mismatches.append(
                {
                    "bestrec_user_id": user_id,
                    "raw_user_id": bestrec_to_user[user_id],
                    "left_item_id": left[user_id],
                    "left_asin": bestrec_to_item[left[user_id]],
                    "right_item_id": right[user_id],
                    "right_asin": bestrec_to_item[right[user_id]],
                }
            )
    return {
        "left_users": len(left),
        "right_users": len(right),
        "common_users": len(common),
        "missing_from_left": len(set(right) - set(left)),
        "missing_from_right": len(set(left) - set(right)),
        "target_mismatches": len(mismatches),
        "target_mismatches_first20": mismatches[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-sasrec-format", default="external/HSTU-BLaIR/tmp/amzn23_game/sasrec_format.csv")
    parser.add_argument("--split-dir", default="data_5core/5core/last_out")
    parser.add_argument("--category", default="Video_Games")
    parser.add_argument("--item-map", default="_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json")
    parser.add_argument("--user-map", default="_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    split_dir = Path(args.split_dir)
    train_path = split_dir / f"{args.category}.train.csv"
    valid_path = split_dir / f"{args.category}.valid.csv"
    test_path = split_dir / f"{args.category}.test.csv"
    all_rows = read_split(train_path) + read_split(valid_path) + read_split(test_path)
    users = sorted({row[0] for row in all_rows})
    items = sorted({row[1] for row in all_rows})
    user_to_bestrec = {user: idx for idx, user in enumerate(users)}
    item_to_bestrec = {item: idx for idx, item in enumerate(items)}
    bestrec_to_user = {idx: user for user, idx in user_to_bestrec.items()}
    bestrec_to_item = {idx: item for item, idx in item_to_bestrec.items()}
    bestrec_valid = {user_to_bestrec[user]: item_to_bestrec[item] for user, item, _, _ in read_split(valid_path)}
    bestrec_test = {user_to_bestrec[user]: item_to_bestrec[item] for user, item, _, _ in read_split(test_path)}

    item_map_path = Path(args.item_map)
    user_map_path = Path(args.user_map)
    hstu_sasrec_path = Path(args.hstu_sasrec_format)
    item_map = load_mapping(item_map_path, "hstu_one_based_to_bestrec_zero_based")
    user_map = load_mapping(user_map_path, "hstu_zero_based_to_bestrec_zero_based")
    hstu_train_targets, hstu_eval_targets = hstu_targets_from_sasrec_format(hstu_sasrec_path, item_map, user_map)

    train_vs_valid = compare_targets(hstu_train_targets, bestrec_valid, bestrec_to_user, bestrec_to_item)
    eval_vs_test = compare_targets(hstu_eval_targets, bestrec_test, bestrec_to_user, bestrec_to_item)
    train_vs_test = compare_targets(hstu_train_targets, bestrec_test, bestrec_to_user, bestrec_to_item)

    payload = {
        "schema_version": 1,
        "status": "complete",
        "dataset": args.category,
        "hstu_protocol": {
            "train_dataset_target": "second_last_item_after_ignore_last_n_1",
            "eval_dataset_target": "last_item_after_ignore_last_n_0",
            "item_ids_shifted_by": 1,
        },
        "comparisons": {
            "hstu_train_target_vs_bestrec_valid": train_vs_valid,
            "hstu_eval_target_vs_bestrec_test": eval_vs_test,
            "hstu_train_target_vs_bestrec_test": train_vs_test,
        },
        "interpretation": {
            "hstu_train_equals_bestrec_valid": train_vs_valid["target_mismatches"] == 0,
            "hstu_train_matches_bestrec_valid_except_mismatches": train_vs_valid["target_mismatches"],
            "hstu_eval_equals_bestrec_test_except_tiny_ties": eval_vs_test["target_mismatches"] <= 2,
            "validation_fusion_risk": (
                "HSTU train targets are effectively BEST-Rec validation targets, with only the reported mismatch count. "
                "Do not tune fusion weights on BEST-Rec validation using the trained HSTU checkpoint without disclosing leakage."
            ),
        },
        "inputs": {
            "hstu_sasrec_format": sha256_file(hstu_sasrec_path),
            "item_map": sha256_file(item_map_path),
            "user_map": sha256_file(user_map_path),
            "train_csv": sha256_file(train_path),
            "valid_csv": sha256_file(valid_path),
            "test_csv": sha256_file(test_path),
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
