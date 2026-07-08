"""Build an ASIN-based HSTU-BLaIR to BEST-Rec Video_Games item-id map.

Run inside WSL from the HSTU-BLaIR source checkout. HSTU's data_maps item ids
are zero-based in the saved map and shifted to one-based ids by its dataloader.
BEST-Rec uses its own zero-based ASIN-sorted ids. Because the orders differ,
teacher exports and ensembles must translate ids through ASINs.
"""

from __future__ import annotations

import argparse
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


def load_hstu_item_map(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "item2id" in payload:
        raw = payload["item2id"]
    elif "item_id" in payload:
        raw = payload["item_id"]
    else:
        dict_values = [value for value in payload.values() if isinstance(value, dict)]
        candidates: list[dict[str, Any]] = []
        for block in dict_values:
            sample = list(block.items())[:5]
            if sample and all(isinstance(key, str) and isinstance(value, int) for key, value in sample):
                candidates.append(block)
        if not candidates:
            raise ValueError(f"Could not find item map in {path}; keys={list(payload)[:20]}")
        raw = max(candidates, key=len)
    return {str(key): int(value) for key, value in raw.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-data-maps", default="tmp/amzn23_game/data_maps")
    parser.add_argument("--bestrec-asin2idx", default="/mnt/c/Users/rayxc/Documents/R/cache_5core/asin2idx_Video_Games.json")
    parser.add_argument("--out", default="/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json")
    args = parser.parse_args()

    hstu_path = Path(args.hstu_data_maps)
    bestrec_path = Path(args.bestrec_asin2idx)
    out_path = Path(args.out)

    hstu_asin_to_zero = load_hstu_item_map(hstu_path)
    bestrec_asin_to_zero = {str(key): int(value) for key, value in json.loads(bestrec_path.read_text(encoding="utf-8")).items()}

    hstu_asins = set(hstu_asin_to_zero)
    bestrec_asins = set(bestrec_asin_to_zero)
    common_asins = hstu_asins & bestrec_asins
    missing_from_hstu = sorted(bestrec_asins - hstu_asins)
    missing_from_bestrec = sorted(hstu_asins - bestrec_asins)

    if missing_from_hstu or missing_from_bestrec:
        status = "incomplete_item_set_overlap"
    else:
        status = "complete_bijection"

    max_hstu_zero = max(hstu_asin_to_zero.values()) if hstu_asin_to_zero else -1
    max_bestrec_zero = max(bestrec_asin_to_zero.values()) if bestrec_asin_to_zero else -1
    hstu_one_based_to_bestrec_zero_based: list[int | None] = [None] * (max_hstu_zero + 2)
    bestrec_zero_based_to_hstu_one_based: list[int | None] = [None] * (max_bestrec_zero + 1)

    translated_pairs = []
    for asin in sorted(common_asins):
        hstu_zero = hstu_asin_to_zero[asin]
        hstu_one = hstu_zero + 1
        bestrec_zero = bestrec_asin_to_zero[asin]
        hstu_one_based_to_bestrec_zero_based[hstu_one] = bestrec_zero
        bestrec_zero_based_to_hstu_one_based[bestrec_zero] = hstu_one
        translated_pairs.append((asin, hstu_zero, hstu_one, bestrec_zero))

    unmapped_hstu_ids = [idx for idx, value in enumerate(hstu_one_based_to_bestrec_zero_based[1:], start=1) if value is None]
    unmapped_bestrec_ids = [idx for idx, value in enumerate(bestrec_zero_based_to_hstu_one_based) if value is None]
    if unmapped_hstu_ids or unmapped_bestrec_ids:
        status = "incomplete_id_bijection"

    naive_mismatches = [
        {"asin": asin, "hstu_one_based": hstu_one, "hstu_zero_based": hstu_zero, "bestrec_zero_based": bestrec_zero}
        for asin, hstu_zero, hstu_one, bestrec_zero in translated_pairs
        if hstu_one - 1 != bestrec_zero
    ]

    payload = {
        "schema_version": 1,
        "dataset": "Video_Games",
        "status": status,
        "id_spaces": {
            "hstu_data_maps_item_ids": "zero_based",
            "hstu_export_item_ids": "one_based_after_loader_shift",
            "bestrec_item_ids": "zero_based",
        },
        "tested_naive_rule": "bestrec_item_id = hstu_item_id - 1",
        "naive_rule_valid": not naive_mismatches and status == "complete_bijection",
        "required_translation": "bestrec_item_id = bestrec_asin2idx[hstu_id2asin[hstu_item_id - 1]]",
        "counts": {
            "hstu_items": len(hstu_asin_to_zero),
            "bestrec_items": len(bestrec_asin_to_zero),
            "common_items": len(common_asins),
            "hstu_one_based_to_bestrec_zero_based_entries": len(hstu_one_based_to_bestrec_zero_based) - 1,
            "bestrec_zero_based_to_hstu_one_based_entries": len(bestrec_zero_based_to_hstu_one_based),
            "naive_rule_mismatches": len(naive_mismatches),
        },
        "hstu_one_based_to_bestrec_zero_based": hstu_one_based_to_bestrec_zero_based,
        "bestrec_zero_based_to_hstu_one_based": bestrec_zero_based_to_hstu_one_based,
        "sample_first10_by_asin": [
            {
                "asin": asin,
                "hstu_zero_based": hstu_zero,
                "hstu_one_based": hstu_one,
                "bestrec_zero_based": bestrec_zero,
            }
            for asin, hstu_zero, hstu_one, bestrec_zero in translated_pairs[:10]
        ],
        "naive_mismatches_first20": naive_mismatches[:20],
        "missing_from_hstu_first20": missing_from_hstu[:20],
        "missing_from_bestrec_first20": missing_from_bestrec[:20],
        "unmapped_hstu_one_based_ids_first20": unmapped_hstu_ids[:20],
        "unmapped_bestrec_zero_based_ids_first20": unmapped_bestrec_ids[:20],
        "inputs": {
            "hstu_data_maps": sha256_file(hstu_path),
            "bestrec_asin2idx": sha256_file(bestrec_path),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("schema_version", "dataset", "status", "naive_rule_valid", "counts")}, indent=2, sort_keys=True))
    return 0 if status == "complete_bijection" else 1


if __name__ == "__main__":
    raise SystemExit(main())
