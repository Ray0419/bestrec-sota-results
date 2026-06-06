"""Create a hash-checked source archive for the isolated SOTA lab.

The archive intentionally excludes generated run outputs. It captures the lab
source/config files and the external LIGER source files used by the strict
manifest helper, then writes a JSON manifest that the strict review can verify.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from protocol import external_code_inputs, lab_code_inputs
from sota_common import LAB_DIR, ROOT, utc_now, write_json


ARCHIVE_DIR = LAB_DIR / "source_archives"
MANIFEST_PATH = LAB_DIR / "source_archive_manifest.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def git_commit(path: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def build_archive(run_id: str) -> dict[str, Any]:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    source_files = []
    seen: set[str] = set()
    for path in [*lab_code_inputs(), *external_code_inputs()]:
        key = rel(path)
        if key in seen:
            continue
        seen.add(key)
        source_files.append(path)
    source_files = sorted(source_files, key=rel)
    file_hashes = {rel(path): sha256_file(path) for path in source_files}
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "run_id": run_id,
        "source_file_count": len(source_files),
        "source_hashes": file_hashes,
        "external_revisions": {
            "external/liger": git_commit(ROOT / "external" / "liger"),
        },
    }
    archive_name = f"bestrec_sota_lab_source_{run_id}.zip"
    archive_path = ARCHIVE_DIR / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_files:
            zf.write(path, rel(path))
        zf.writestr("SOURCE_ARCHIVE_MANIFEST.json", json.dumps(payload, indent=2, sort_keys=True))
    payload["archive_path"] = rel(archive_path)
    payload["archive_sha256"] = sha256_file(archive_path)
    write_json(MANIFEST_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="confirmatory_masked_candidate_20260701_20260705_candidate_only")
    args = parser.parse_args()
    payload = build_archive(args.run_id)
    print(f"Wrote {payload['archive_path']}")
    print(f"Archive sha256: {payload['archive_sha256']}")
    print(f"Source files: {payload['source_file_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
