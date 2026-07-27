#!/usr/bin/env python3
"""Acquire frozen Software V2 rating and metadata objects without overwrite."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data_raw_proper" / "software"
MANIFEST = ROOT / "_bestrec_run" / "software_acquisition_manifest.json"
HF_REVISION = "2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e"
RATING_URL = "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/benchmark/5core/rating_only/Software.csv.gz"
META_URL = (
    "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/"
    f"{HF_REVISION}/raw/meta_categories/meta_Software.jsonl"
)
FILES = {
    "Software.csv.gz": {
        "url": RATING_URL,
        "bytes": 19_079_096,
        "sha256": None,
        "etag": '"1231fb8-62bd9beebcd77"',
        "last_modified": "Thu, 16 Jan 2025 21:47:51 GMT",
    },
    "meta_Software.jsonl": {
        "url": META_URL,
        "bytes": 256_220_771,
        "sha256": "7c52cce1bf3bff33f965fe117e3e8fac18a1839f88b215efa50b31a8230a5f58",
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
    if size != spec["bytes"]:
        raise RuntimeError(f"size mismatch for {path}: {size} != {spec['bytes']}")
    if spec.get("sha256") and digest != spec["sha256"]:
        raise RuntimeError(f"SHA-256 mismatch for {path}: {digest} != {spec['sha256']}")
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest}


def acquire(name: str, spec: dict[str, object]) -> dict[str, object]:
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / name
    if target.exists():
        record = verify(target, spec)
        record["url"] = spec["url"]
        return record
    partial = target.with_suffix(target.suffix + ".part")
    if partial.exists():
        raise RuntimeError(f"partial object exists; refusing reuse: {partial}")
    request = urllib.request.Request(str(spec["url"]), headers={"User-Agent": "bestrec-prospective-v2/1"})
    print(f"downloading {spec['url']} -> {target}")
    try:
        with urllib.request.urlopen(request) as src:
            if spec.get("etag") and src.headers.get("ETag") != spec["etag"]:
                raise RuntimeError(f"ETag mismatch: {src.headers.get('ETag')} != {spec['etag']}")
            if spec.get("last_modified") and src.headers.get("Last-Modified") != spec["last_modified"]:
                raise RuntimeError(
                    f"Last-Modified mismatch: {src.headers.get('Last-Modified')} != {spec['last_modified']}"
                )
            with partial.open("xb") as dst:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
        verify(partial, spec)
        os.replace(partial, target)
    except Exception:
        raise
    record = verify(target, spec)
    record["url"] = spec["url"]
    return record


def main() -> int:
    records = {name: acquire(name, spec) for name, spec in FILES.items()}
    payload = {
        "protocol": "PREREG_FIR_PROSPECTIVE_SW_V2_PREPARATION",
        "hf_revision": HF_REVISION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": records,
    }
    if MANIFEST.exists():
        old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        old.pop("created_utc", None)
        comparison = dict(payload)
        comparison.pop("created_utc", None)
        if old != comparison:
            raise RuntimeError(f"existing manifest differs; refusing overwrite: {MANIFEST}")
        print(f"verified existing manifest: {MANIFEST}")
    else:
        with MANIFEST.open("x", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
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
