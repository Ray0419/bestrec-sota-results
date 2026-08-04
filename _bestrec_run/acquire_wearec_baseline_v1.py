#!/usr/bin/env python3
"""Acquire and verify the exact official WEARec source used by V1."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "ee_baselines" / "WEARec"
URL = "https://github.com/xhy963319431/WEARec.git"
COMMIT = "2087335339b1ead87da6e066ce14e2d33880a95e"
SOURCE_HASHES = {
    "src/model/__init__.py": "8cf81baaa0626586caa130fe6b6f5269e5afa18a8269509bc520e36ef947afa4",
    "src/model/wearec.py": "77d9012dfed909db88fff824d0a2126b921ab234029943a2172bb4b0c77f3d01",
    "src/model/_abstract_model.py": "525a86904354c6a6acb513a0d93cffdd44e9e4bde4dcc39fb4cc04a0c9dbc544",
    "src/model/_modules.py": "11c34e5cc094e4b903f9779e878fcbd5c7cf687b23a24f161ccdd174ad8a1d0c",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8"
    ).strip()


def main() -> int:
    if not DEST.exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", URL, str(DEST)], cwd=ROOT, check=True)
        subprocess.run(["git", "checkout", "--detach", COMMIT], cwd=DEST, check=True)
    if not (DEST / ".git").exists():
        raise SystemExit(f"refusing non-git upstream path: {DEST}")
    head = git("rev-parse", "HEAD", cwd=DEST)
    if head != COMMIT:
        raise SystemExit(f"WEARec HEAD mismatch: {head} != {COMMIT}")
    dirty = git("status", "--porcelain", "--untracked-files=no", cwd=DEST)
    if dirty:
        raise SystemExit("WEARec checkout is dirty; refusing modified upstream source")
    remote = git("remote", "get-url", "origin", cwd=DEST)
    if remote.rstrip("/").removesuffix(".git") != URL.rstrip("/").removesuffix(".git"):
        raise SystemExit(f"WEARec origin mismatch: {remote}")
    for rel, expected in SOURCE_HASHES.items():
        path = DEST / rel
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"WEARec source hash mismatch: {rel}")
    print(f"WEARec acquisition OK: {URL}@{COMMIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
