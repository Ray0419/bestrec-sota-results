#!/usr/bin/env python
"""Hydrate every immutable release asset into a fresh public clone.

The manifest records raw SHA-256 and byte length for large files intentionally
absent from Git.  This helper downloads the named release assets, or optionally
hard-links/copies them from another verified checkout, and refuses to overwrite
any mismatched local file.

Usage:
  python bootstrap_public_clone.py
  python bootstrap_public_clone.py --source-root C:\\path\\to\\verified-checkout
  python bootstrap_public_clone.py --sections splits text_caches
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = (
    "https://github.com/Ray0419/bestrec-sota-results/releases/download/"
    "v0.9-audit-evidence/"
)
SECTIONS = (
    "splits",
    "text_caches",
    "pinned_parity_artifacts",
    "tfv2_sidecars",
    "fir_control_finaleval",
    "fir_control_sidecars",
    "fir_control_checkpoints",
    "fir_pointwise_finaleval",
    "fir_pointwise_sidecars",
    "fir_pointwise_checkpoints",
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path: Path, meta: dict) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    if size != int(meta["bytes"]):
        return False, f"size {size} != {meta['bytes']}"
    actual = digest(path)
    if actual != meta["sha256"]:
        return False, f"sha256 {actual} != {meta['sha256']}"
    return True, "ok"


def records(manifest: dict, selected: set[str]):
    for section in SECTIONS:
        if section not in selected:
            continue
        payload = manifest[section]
        if section == "pinned_parity_artifacts":
            payload = payload["files"]
        for name, meta in payload.items():
            if section == "splits":
                rel = Path("data_5core/5core/last_out") / f"{name}.csv"
                asset = f"{name}.csv"
            elif section == "text_caches":
                rel = Path("cache_5core") / name
                asset = name
            elif section == "pinned_parity_artifacts":
                rel = Path("_bestrec_run/theirs_runs/tmp/pinned_parity") / name
                asset = name
            else:
                rel = Path("_bestrec_run") / name
                asset = name
            yield section, name, rel, asset, meta


def install_from_source(source: Path, destination: Path, meta: dict) -> None:
    ok, why = verify(source, meta)
    if not ok:
        raise RuntimeError(f"source verification failed for {source}: {why}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def install_from_release(asset: str, destination: Path, meta: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".part", dir=destination.parent
    )
    os.close(fd)
    temp = Path(temp_name)
    try:
        url = URL + urllib.parse.quote(asset)
        print(f"DOWNLOAD {url}")
        with urllib.request.urlopen(url, timeout=300) as response, temp.open("wb") as out:
            shutil.copyfileobj(response, out, length=1 << 20)
        ok, why = verify(temp, meta)
        if not ok:
            raise RuntimeError(f"download verification failed for {asset}: {why}")
        os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        help="verified checkout to hard-link/copy from instead of downloading",
    )
    parser.add_argument(
        "--sections",
        nargs="+",
        choices=SECTIONS,
        default=list(SECTIONS),
        help="manifest sections to hydrate (default: all release-only sections)",
    )
    args = parser.parse_args()
    source_root = args.source_root.resolve() if args.source_root else None
    if source_root == ROOT:
        parser.error("--source-root must be a different checkout")

    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    installed = already = 0
    for section, name, rel, asset, meta in records(manifest, set(args.sections)):
        destination = ROOT / rel
        ok, why = verify(destination, meta)
        if ok:
            already += 1
            print(f"OK       {section}/{name}")
            continue
        if destination.exists():
            raise RuntimeError(
                f"refusing to overwrite mismatched {destination}: {why}"
            )
        if source_root:
            install_from_source(source_root / rel, destination, meta)
        else:
            install_from_release(asset, destination, meta)
        ok, why = verify(destination, meta)
        if not ok:
            raise RuntimeError(f"installed verification failed for {destination}: {why}")
        installed += 1
        print(f"INSTALLED {section}/{name}")

    print(f"PASS: installed={installed}, already_valid={already}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
