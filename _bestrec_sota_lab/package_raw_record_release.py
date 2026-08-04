"""Create and verify upload-ready chunks for the raw-record release.

The publication gate requires the multi-GB per-user JSONL records to be
available outside the local workspace. This helper makes that upload practical:
it splits the canonical raw JSONL files into deterministic binary parts,
records per-part SHA-256 hashes, and verifies that concatenating the parts
reconstructs the manifest-pinned original bytes.

The script never edits experiment outputs. It only writes under
``publication_artifacts/raw_record_release/upload_parts`` by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sota_common import LAB_DIR, ROOT, write_json


RAW_RELEASE_DIR = LAB_DIR / "publication_artifacts" / "raw_record_release"
RAW_MANIFEST_PATH = RAW_RELEASE_DIR / "raw_record_release_manifest.json"
DEFAULT_PARTS_DIR = RAW_RELEASE_DIR / "upload_parts"
DEFAULT_PART_BYTES = 1_500_000_000
READ_BYTES = 8 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(READ_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()


def part_name(source_name: str, part_index: int, part_count: int) -> str:
    width = max(3, len(str(part_count)))
    return f"{source_name}.part{part_index:0{width}d}of{part_count:0{width}d}"


def expected_part_count(byte_count: int, part_bytes: int) -> int:
    return max(1, (byte_count + part_bytes - 1) // part_bytes)


def split_source(source_path: Path, out_dir: Path, part_bytes: int) -> dict[str, Any]:
    source_bytes = source_path.stat().st_size
    count = expected_part_count(source_bytes, part_bytes)
    parts: list[dict[str, Any]] = []
    with source_path.open("rb") as src:
        for index in range(1, count + 1):
            name = part_name(source_path.name, index, count)
            path = out_dir / name
            h = hashlib.sha256()
            written = 0
            with path.open("wb") as dst:
                remaining = min(part_bytes, source_bytes - sum(int(p["bytes"]) for p in parts))
                while remaining > 0:
                    chunk = src.read(min(READ_BYTES, remaining))
                    if not chunk:
                        break
                    dst.write(chunk)
                    h.update(chunk)
                    written += len(chunk)
                    remaining -= len(chunk)
            parts.append(
                {
                    "name": name,
                    "path": rel(path),
                    "bytes": written,
                    "sha256": h.hexdigest(),
                    "part_index": index,
                    "part_count": count,
                }
            )
    return {
        "source_path": rel(source_path),
        "source_name": source_path.name,
        "source_bytes": source_bytes,
        "source_sha256": sha256_path(source_path),
        "part_bytes_limit": part_bytes,
        "parts": parts,
    }


def verify_split(entry: dict[str, Any], raw_record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    h = hashlib.sha256()
    total_bytes = 0
    part_count = len(entry.get("parts", []))
    for expected_index, part in enumerate(entry.get("parts", []), start=1):
        path = ROOT / part["path"]
        if not path.exists():
            failures.append(f"missing part: {path}")
            continue
        actual_bytes = path.stat().st_size
        actual_sha = sha256_path(path)
        if int(part["part_index"]) != expected_index:
            failures.append(f"{part['name']}: part_index is out of order")
        if int(part["part_count"]) != part_count:
            failures.append(f"{part['name']}: part_count mismatch")
        if actual_bytes != int(part["bytes"]):
            failures.append(f"{part['name']}: bytes expected={part['bytes']} actual={actual_bytes}")
        if actual_sha != part["sha256"]:
            failures.append(f"{part['name']}: sha256 expected={part['sha256']} actual={actual_sha}")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(READ_BYTES), b""):
                h.update(chunk)
        total_bytes += actual_bytes
    expected_bytes = int(raw_record["bytes"])
    expected_sha = raw_record["sha256"]
    if total_bytes != expected_bytes:
        failures.append(f"{entry['source_name']}: reassembled bytes expected={expected_bytes} actual={total_bytes}")
    actual_combined_sha = h.hexdigest()
    if actual_combined_sha != expected_sha:
        failures.append(
            f"{entry['source_name']}: reassembled sha256 expected={expected_sha} actual={actual_combined_sha}"
        )
    if entry.get("source_sha256") != expected_sha:
        failures.append(f"{entry['source_name']}: source_sha256 does not match raw manifest")
    return failures


def build_manifest(
    raw_manifest: dict[str, Any],
    raw_manifest_path: Path,
    parts_dir: Path,
    part_bytes: int,
    overwrite: bool,
) -> dict[str, Any]:
    parts_dir.mkdir(parents=True, exist_ok=True)
    entries: dict[str, Any] = {}
    for dataset, raw_record in raw_manifest["records"].items():
        source = ROOT / raw_record["path"]
        if not source.exists():
            raise FileNotFoundError(source)
        count = expected_part_count(int(raw_record["bytes"]), part_bytes)
        expected_paths = [parts_dir / part_name(source.name, index, count) for index in range(1, count + 1)]
        if not overwrite and any(path.exists() for path in expected_paths):
            raise FileExistsError(f"Refusing to overwrite existing parts for {dataset}; pass --overwrite")
        for path in expected_paths:
            if path.exists():
                path.unlink()
        entries[dataset] = split_source(source, parts_dir, part_bytes)
    total_part_bytes = sum(int(part["bytes"]) for entry in entries.values() for part in entry["parts"])
    return {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "raw_record_manifest": rel(raw_manifest_path),
        "raw_record_manifest_sha256": sha256_path(raw_manifest_path),
        "part_bytes_limit": part_bytes,
        "parts_dir": rel(parts_dir),
        "total_part_bytes": total_part_bytes,
        "total_parts": sum(len(entry["parts"]) for entry in entries.values()),
        "datasets": entries,
    }


def verify_manifest(parts_manifest: dict[str, Any], raw_manifest: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    raw_manifest_path = ROOT / parts_manifest["raw_record_manifest"]
    if not raw_manifest_path.exists():
        failures.append(f"missing raw manifest: {raw_manifest_path}")
    else:
        actual_manifest_sha = sha256_path(raw_manifest_path)
        if actual_manifest_sha != parts_manifest["raw_record_manifest_sha256"]:
            failures.append(
                "raw manifest sha256 mismatch "
                f"expected={parts_manifest['raw_record_manifest_sha256']} actual={actual_manifest_sha}"
            )
    for dataset, entry in parts_manifest.get("datasets", {}).items():
        if dataset not in raw_manifest.get("records", {}):
            failures.append(f"{dataset}: not present in raw record manifest")
            continue
        failures.extend(verify_split(entry, raw_manifest["records"][dataset]))
    return failures


def render_markdown(parts_manifest: dict[str, Any]) -> str:
    rows = []
    for dataset, entry in parts_manifest["datasets"].items():
        rows.append(
            f"| {dataset} | `{entry['source_name']}` | {entry['source_bytes']:,} | "
            f"{len(entry['parts'])} | `{entry['source_sha256']}` |"
        )
    part_rows = []
    for dataset, entry in parts_manifest["datasets"].items():
        for part in entry["parts"]:
            part_rows.append(
                f"| {dataset} | `{part['name']}` | {part['bytes']:,} | `{part['sha256']}` |"
            )
    return "\n".join(
        [
            "# Upload Parts Manifest",
            "",
            f"Generated UTC: `{parts_manifest['generated_utc']}`",
            "",
            "These files are deterministic binary chunks of the canonical raw JSONL records. Upload every part, `raw_record_release_manifest.json`, and `raw_record_upload_parts_manifest.json` to the same public archive/release.",
            "",
            f"- Part byte limit: `{parts_manifest['part_bytes_limit']:,}`",
            f"- Total parts: `{parts_manifest['total_parts']}`",
            f"- Total part bytes: `{parts_manifest['total_part_bytes']:,}`",
            f"- Raw manifest SHA256: `{parts_manifest['raw_record_manifest_sha256']}`",
            "",
            "| Dataset | Source | Source bytes | Parts | Source SHA256 |",
            "| --- | --- | ---: | ---: | --- |",
            *rows,
            "",
            "## Part Files",
            "",
            "| Dataset | Part | Bytes | SHA256 |",
            "| --- | --- | ---: | --- |",
            *part_rows,
            "",
            "## Verify After Download",
            "",
            "Place the parts under the recorded `upload_parts` directory and run:",
            "",
            "```powershell",
            "uv --project _bestrec_run run python _bestrec_sota_lab/package_raw_record_release.py --verify-parts",
            "```",
            "",
            "The verifier checks each part hash and streams the parts in order to confirm that they reconstruct the exact raw JSONL SHA256 values from `raw_record_release_manifest.json`.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-manifest", default=str(RAW_MANIFEST_PATH))
    parser.add_argument("--parts-dir", default=str(DEFAULT_PARTS_DIR))
    parser.add_argument("--part-bytes", type=int, default=DEFAULT_PART_BYTES)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verify-parts", action="store_true")
    args = parser.parse_args()

    raw_manifest_path = Path(args.raw_manifest)
    parts_dir = Path(args.parts_dir)
    parts_manifest_path = parts_dir.parent / "raw_record_upload_parts_manifest.json"
    parts_md_path = parts_dir.parent / "RAW_RECORD_UPLOAD_PARTS.md"
    raw_manifest = read_json(raw_manifest_path)

    if args.verify_parts:
        parts_manifest = read_json(parts_manifest_path)
        failures = verify_manifest(parts_manifest, raw_manifest)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        print(f"Raw record upload parts verified: {parts_manifest_path}")
        return 0

    if args.part_bytes <= 0:
        raise ValueError("--part-bytes must be positive")
    parts_manifest = build_manifest(raw_manifest, raw_manifest_path, parts_dir, args.part_bytes, args.overwrite)
    write_json(parts_manifest_path, parts_manifest)
    parts_md_path.write_text(render_markdown(parts_manifest), encoding="utf-8")
    failures = verify_manifest(parts_manifest, raw_manifest)
    if failures:
        raise RuntimeError("; ".join(failures))
    print(f"Wrote {parts_manifest_path}")
    print(f"Wrote {parts_md_path}")
    print(f"Wrote {parts_manifest['total_parts']} parts under {parts_dir}")
    print(f"Total part bytes: {parts_manifest['total_part_bytes']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
