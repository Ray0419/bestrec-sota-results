#!/usr/bin/env python3
"""Create hash-selected nested ML-1M user cohorts for the scale mechanism test."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_ids_hash(ids: list[int]) -> str:
    payload = "\n".join(map(str, ids)).encode("ascii") + b"\n"
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--sizes", default="943,4000")
    parser.add_argument("--selection-seed", default="20260802")
    args = parser.parse_args()

    rows = []
    for line in args.source.read_text(encoding="ascii").splitlines():
        user_text, item_text = line.split(" ", 1)
        rows.append((int(user_text), item_text))
    sizes = sorted({int(value) for value in args.sizes.split(",")})
    if not sizes or sizes[0] <= 0 or sizes[-1] > len(rows):
        raise SystemExit("invalid cohort sizes")

    score = lambda user: hashlib.sha256(  # noqa: E731
        f"{args.selection_seed}:{user}".encode("ascii")).digest()
    order = sorted((user for user, _items in rows), key=score)
    by_user = dict(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cohorts = []
    for size in sizes:
        selected = order[:size]
        output = args.output_dir / f"ML-1M-N{size}.txt"
        lengths = []
        active_items = set()
        with output.open("w", encoding="ascii") as handle:
            for new_user, original_user in enumerate(selected, start=1):
                item_text = by_user[original_user]
                items = [int(value) for value in item_text.split()]
                lengths.append(len(items))
                active_items.update(items)
                handle.write(f"{new_user} {item_text}\n")
        cohorts.append({
            "size": size,
            "output": str(output.resolve()),
            "output_sha256": sha256(output),
            "selected_original_user_ids_sha256": selected_ids_hash(selected),
            "interactions": sum(lengths),
            "active_items": len(active_items),
            "max_item_id": max(active_items),
            "mean_sequence_length": statistics.mean(lengths),
            "median_sequence_length": statistics.median(lengths),
            "min_sequence_length": min(lengths),
            "max_sequence_length": max(lengths),
        })

    artifact = {
        "protocol": "EGSP_ML1M_NESTED_USERS_V1",
        "preregistration": str(args.preregistration.resolve()),
        "preregistration_sha256": sha256(args.preregistration),
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "selection": f"ascending SHA-256 of '{args.selection_seed}:<original user id>'",
        "nested": True,
        "cohorts": cohorts,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps(artifact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
