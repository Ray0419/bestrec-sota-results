#!/usr/bin/env python3
"""Acquire the revision-pinned AR2023 Digital Music inputs without overwrite."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data_raw_proper" / "digital_music"
MANIFEST = ROOT / "_bestrec_run" / "digital_music_acquisition_manifest.json"
REVISION = "2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e"
BASE = f"https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/{REVISION}"
FILES = {
    "Digital_Music.jsonl": {
        "path": "raw/review_categories/Digital_Music.jsonl",
        "bytes": 78_823_304,
        "sha256": "9ac137137e55e34fce290670fdf44acee5afa2ffae541f4f3b366a835930a7c3",
    },
    "meta_Digital_Music.jsonl": {
        "path": "raw/meta_categories/meta_Digital_Music.jsonl",
        "bytes": 67_097_002,
        "sha256": "7f5387e99b70631d919c87005269c555e8886ae9a60c4c59a9b6ed7881acbbec",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(path: Path, spec: dict[str, object]) -> dict[str, object]:
    size = path.stat().st_size
    digest = sha256(path)
    if size != spec["bytes"] or digest != spec["sha256"]:
        raise RuntimeError(
            f"integrity mismatch for {path}: bytes={size}, sha256={digest}; "
            f"expected bytes={spec['bytes']}, sha256={spec['sha256']}"
        )
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest}


def acquire(name: str, spec: dict[str, object]) -> dict[str, object]:
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / name
    url = f"{BASE}/{spec['path']}"
    if target.exists():
        record = verify(target, spec)
        record.update({"url": url})
        return record

    partial = target.with_suffix(target.suffix + ".part")
    if partial.exists():
        raise RuntimeError(f"partial download already exists; refusing reuse: {partial}")
    print(f"downloading {url} -> {target}")
    try:
        with urllib.request.urlopen(url) as src, partial.open("xb") as dst:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
        record = verify(partial, spec)
        os.replace(partial, target)
        record = verify(target, spec)
        record.update({"url": url})
        return record
    except Exception:
        # Preserve a partial object as forensic evidence; never silently retry it.
        raise


def main() -> int:
    records = {name: acquire(name, spec) for name, spec in FILES.items()}
    payload = {
        "protocol": "PREREG_FIR_PROSPECTIVE_DM_V1_SELECTION",
        "upstream_repository": "McAuley-Lab/Amazon-Reviews-2023",
        "upstream_revision": REVISION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": records,
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if MANIFEST.exists():
        old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        old.pop("created_utc", None)
        comparable = dict(payload)
        comparable.pop("created_utc", None)
        if old != comparable:
            raise RuntimeError(f"existing manifest differs; refusing overwrite: {MANIFEST}")
        print(f"verified existing manifest: {MANIFEST}")
    else:
        with MANIFEST.open("xb") as fh:
            fh.write(encoded)
        print(f"wrote {MANIFEST}")
    for name, record in records.items():
        print(f"verified {name}: {record['bytes']} bytes {record['sha256']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
