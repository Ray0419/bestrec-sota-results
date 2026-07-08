"""Convert HSTU-BLaIR per-user JSONL exports to BEST-Rec item ids.

The HSTU exporter records HSTU's internal user ids and one-based shifted item
ids. This converter streams those records, translates user ids through the raw
user-id map, translates target and optional teacher top-k item ids through the
ASIN-based item map, and writes canonical BEST-Rec zero-based ids. Metrics are
copied unchanged because ranks are invariant to id naming.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


METRIC_FIELDS = ("ndcg10", "hr10", "rr")


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


def load_hstu_to_bestrec(path: Path) -> list[int | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete_bijection":
        raise ValueError(f"Item map is not a complete bijection: {payload.get('status')}")
    mapping = payload.get("hstu_one_based_to_bestrec_zero_based")
    if not isinstance(mapping, list) or not mapping:
        raise ValueError(f"Missing hstu_one_based_to_bestrec_zero_based in {path}")
    return [None if value is None else int(value) for value in mapping]


def load_hstu_users_to_bestrec(path: Path) -> list[int | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete_bijection":
        raise ValueError(f"User map is not a complete bijection: {payload.get('status')}")
    mapping = payload.get("hstu_zero_based_to_bestrec_zero_based")
    if not isinstance(mapping, list) or not mapping:
        raise ValueError(f"Missing hstu_zero_based_to_bestrec_zero_based in {path}")
    return [None if value is None else int(value) for value in mapping]


def translate_item(mapping: list[int | None], hstu_one_based_id: int) -> int:
    if hstu_one_based_id <= 0 or hstu_one_based_id >= len(mapping):
        raise ValueError(f"HSTU item id {hstu_one_based_id} is outside map range 1..{len(mapping) - 1}")
    translated = mapping[hstu_one_based_id]
    if translated is None:
        raise ValueError(f"HSTU item id {hstu_one_based_id} is unmapped")
    return translated


def translate_user(mapping: list[int | None], hstu_zero_based_id: int) -> int:
    if hstu_zero_based_id < 0 or hstu_zero_based_id >= len(mapping):
        raise ValueError(f"HSTU user id {hstu_zero_based_id} is outside map range 0..{len(mapping) - 1}")
    translated = mapping[hstu_zero_based_id]
    if translated is None:
        raise ValueError(f"HSTU user id {hstu_zero_based_id} is unmapped")
    return translated


def convert_record(
    record: dict[str, Any],
    item_mapping: list[int | None],
    item_map_path: Path,
    user_mapping: list[int | None],
    user_map_path: Path,
) -> dict[str, Any]:
    if "target_item_id" not in record:
        raise ValueError("Record is missing target_item_id")
    if "user_id" not in record:
        raise ValueError("Record is missing user_id")
    source_target = int(record["target_item_id"])
    source_user = int(record["user_id"])
    converted = dict(record)
    converted["source_item_id_convention"] = record.get("item_id_convention", "hstu_one_based_shifted_item_ids")
    converted["item_id_convention"] = "bestrec_zero_based_item_ids"
    converted["source_user_id_convention"] = record.get("user_id_convention", "hstu_zero_based_internal_user_ids")
    converted["user_id_convention"] = "bestrec_zero_based_user_ids"
    converted["id_translation"] = {
        "item_source": "hstu_one_based_shifted_item_ids",
        "item_target": "bestrec_zero_based_item_ids",
        "item_map": str(item_map_path),
        "user_source": "hstu_zero_based_internal_user_ids",
        "user_target": "bestrec_zero_based_user_ids",
        "user_map": str(user_map_path),
    }
    converted["hstu_user_id"] = source_user
    converted["user_id"] = translate_user(user_mapping, source_user)
    converted["hstu_target_item_id"] = source_target
    converted["target_item_id"] = translate_item(item_mapping, source_target)

    if "teacher_top_ids" in record:
        source_top_ids = [int(value) for value in record["teacher_top_ids"]]
        converted["hstu_teacher_top_ids"] = source_top_ids
        converted["teacher_top_ids"] = [translate_item(item_mapping, item_id) for item_id in source_top_ids]
    return converted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--item-map", required=True)
    parser.add_argument("--user-map", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    input_path = Path(args.input_jsonl)
    map_path = Path(args.item_map)
    user_map_path = Path(args.user_map)
    output_path = Path(args.output_jsonl)
    summary_path = Path(args.summary)
    item_mapping = load_hstu_to_bestrec(map_path)
    user_mapping = load_hstu_users_to_bestrec(user_map_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    metric_sums = {field: 0.0 for field in METRIC_FIELDS}
    records = 0
    translated_user_rows = 0
    translated_teacher_rows = 0
    first_converted_samples: list[dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line_number, line in enumerate(src, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            converted = convert_record(record, item_mapping, map_path, user_mapping, user_map_path)
            for field in METRIC_FIELDS:
                value = float(converted.get(field, 0.0))
                if not math.isfinite(value):
                    raise ValueError(f"Non-finite {field} at line {line_number}: {value}")
                metric_sums[field] += value
            if "teacher_top_ids" in converted:
                translated_teacher_rows += 1
            if "hstu_user_id" in converted:
                translated_user_rows += 1
            if len(first_converted_samples) < 3:
                first_converted_samples.append(
                    {
                        "user_id": converted.get("user_id"),
                        "hstu_user_id": converted.get("hstu_user_id"),
                        "hstu_target_item_id": converted["hstu_target_item_id"],
                        "target_item_id": converted["target_item_id"],
                        "teacher_top_ids": converted.get("teacher_top_ids", [])[:10],
                    }
                )
            dst.write(json.dumps(converted, sort_keys=True) + "\n")
            records += 1

    if records == 0:
        raise ValueError(f"No records converted from {input_path}")

    summary = {
        "schema_version": 1,
        "status": "complete",
        "records": records,
        "translated_user_rows": translated_user_rows,
        "translated_teacher_rows": translated_teacher_rows,
        "item_id_convention": "bestrec_zero_based_item_ids",
        "source_item_id_convention": "hstu_one_based_shifted_item_ids",
        "user_id_convention": "bestrec_zero_based_user_ids",
        "source_user_id_convention": "hstu_zero_based_internal_user_ids",
        "metrics": {field: metric_sums[field] / records for field in METRIC_FIELDS},
        "samples": first_converted_samples,
        "inputs": {
            "input_jsonl": sha256_file(input_path),
            "item_map": sha256_file(map_path),
            "user_map": sha256_file(user_map_path),
        },
        "outputs": {
            "output_jsonl": sha256_file(output_path),
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
