"""Audit HSTU-BLaIR item-id alignment against BEST-Rec Video_Games ids.

Run inside WSL from the HSTU-BLaIR source checkout. The script reads HSTU's
`tmp/amzn23_game/data_maps` and the local BEST-Rec `asin2idx_Video_Games.json`
file, then tests whether HSTU's shifted one-based ids map to BEST-Rec's
zero-based sorted item ids by the naive rule `bestrec_id = hstu_id - 1`.
If this hypothesis fails, downstream exports must use an explicit ASIN-based
translation map rather than arithmetic ID conversion.
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
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    stat = path.stat()
    record.update({"sha256": h.hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return record


def load_hstu_item_map(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "item2id" in payload:
        raw = payload["item2id"]
    elif "item_id" in payload:
        raw = payload["item_id"]
    else:
        dict_values = [v for v in payload.values() if isinstance(v, dict)]
        candidates = []
        for block in dict_values:
            sample = list(block.items())[:5]
            if sample and all(isinstance(k, str) and isinstance(v, int) for k, v in sample):
                candidates.append(block)
        if not candidates:
            raise ValueError(f"Could not find item map in {path}; keys={list(payload)[:20]}")
        raw = max(candidates, key=len)
    return {str(k): int(v) for k, v in raw.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-data-maps", default="tmp/amzn23_game/data_maps")
    parser.add_argument("--bestrec-asin2idx", default="/mnt/c/Users/rayxc/Documents/R/cache_5core/asin2idx_Video_Games.json")
    parser.add_argument("--out", default="/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_item_alignment_audit.json")
    parser.add_argument("--fail-on-mismatch", action="store_true", help="Return nonzero when the naive alignment hypothesis fails.")
    args = parser.parse_args()

    hstu_path = Path(args.hstu_data_maps)
    bestrec_path = Path(args.bestrec_asin2idx)
    out_path = Path(args.out)
    hstu_map = load_hstu_item_map(hstu_path)
    bestrec_map = {str(k): int(v) for k, v in json.loads(bestrec_path.read_text(encoding="utf-8")).items()}
    common = set(hstu_map) & set(bestrec_map)
    missing_from_hstu = sorted(set(bestrec_map) - set(hstu_map))[:20]
    missing_from_bestrec = sorted(set(hstu_map) - set(bestrec_map))[:20]
    mismatches = []
    for asin in sorted(common):
        # HSTU dataset rows are shifted by +1 at load time, but data_maps item ids
        # are expected to be zero-based like BEST-Rec's asin2idx map.
        if hstu_map[asin] != bestrec_map[asin]:
            mismatches.append({"asin": asin, "hstu_zero_based": hstu_map[asin], "bestrec_zero_based": bestrec_map[asin]})
            if len(mismatches) >= 20:
                break

    payload = {
        "schema_version": 2,
        "tested_naive_rule": "bestrec_item_id = hstu_item_id - 1",
        "naive_rule_valid": not mismatches and len(hstu_map) == len(bestrec_map) == len(common),
        "hstu_zero_based_order_matches_bestrec_zero_based_order": not mismatches and len(hstu_map) == len(bestrec_map) == len(common),
        "required_translation": "bestrec_item_id = bestrec_asin2idx[hstu_id2asin[hstu_item_id - 1]]",
        "counts": {
            "hstu_items": len(hstu_map),
            "bestrec_items": len(bestrec_map),
            "common_items": len(common),
        },
        "mismatches_first20": mismatches,
        "missing_from_hstu_first20": missing_from_hstu,
        "missing_from_bestrec_first20": missing_from_bestrec,
        "sample": [
            {"asin": asin, "hstu_zero_based": hstu_map[asin], "hstu_one_based": hstu_map[asin] + 1, "bestrec_zero_based": bestrec_map[asin]}
            for asin in sorted(common)[:10]
        ],
        "inputs": {
            "hstu_data_maps": sha256_file(hstu_path),
            "bestrec_asin2idx": sha256_file(bestrec_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.fail_on_mismatch and not payload["naive_rule_valid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
