"""Prepare a verifier manifest for the multi-GB raw cold-record JSONL files.

The script does not upload or compress the raw files by default. It streams the
canonical raw JSONL records, computes byte sizes, SHA-256 hashes, and row
counts, and ties them to the independent clean-rebuild multiset evidence. The
output manifest can be uploaded alongside the raw files to Zenodo, OSF, Git LFS,
or another archival store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sota_common import DATASET_LABELS, DATASETS, LAB_DIR, ROOT, RUNS_DIR, write_json


DEFAULT_CANONICAL_RUN_ID = "confirmatory_masked_candidate_20260701_20260705_candidate_only"
DEFAULT_REBUILD_RUN_ID = "full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705"
DEFAULT_OUT_DIR = LAB_DIR / "publication_artifacts" / "raw_record_release"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def stream_file_stats(path: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    row_count = 0
    byte_count = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            byte_count += len(chunk)
            h.update(chunk)
            row_count += chunk.count(b"\n")
    return {
        "path": rel(path),
        "bytes": int(byte_count),
        "rows": int(row_count),
        "sha256": h.hexdigest(),
    }


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_markdown(payload: dict[str, Any]) -> str:
    records = payload["records"]
    rows = []
    for dataset in DATASETS:
        rec = records[dataset]
        rows.append(
            f"| {DATASET_LABELS[dataset]} | `{Path(rec['path']).name}` | "
            f"{rec['bytes']:,} | {rec['rows']:,} | `{rec['sha256']}` |"
        )
    archive = payload["external_archive"]
    lines = [
        "# Raw Record Release Manifest",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "This manifest covers the canonical per-record JSONL files required for adversarial reanalysis of the approved full-catalog cold-item claim. It is intentionally small and suitable for Git; the raw JSONL files are not committed because they total more than 5 GB.",
        "",
        f"- Canonical run id: `{payload['canonical_run_id']}`",
        f"- Independent rebuild run id: `{payload['rebuild_run_id']}`",
        f"- Total bytes: `{payload['total_bytes']:,}`",
        f"- Total rows: `{payload['total_rows']:,}`",
        f"- External archive status: `{archive['status']}`",
        f"- External archive URL: `{archive.get('url') or 'pending'}`",
        f"- External archive DOI: `{archive.get('doi') or 'pending'}`",
        "",
        "| Dataset | File | Bytes | Rows | SHA256 |",
        "| --- | --- | ---: | ---: | --- |",
        *rows,
        "",
        "## Clean-Rebuild Evidence",
        "",
        "The independent full clean rebuild can append records in a different order, so byte hashes are not expected to match across runs. The order-independent row-multiset comparison must match:",
        "",
        f"- `full_clean_rebuild_compare.json` passed: `{payload['clean_rebuild']['passed']}`",
        f"- `max_metric_abs_diff`: `{payload['clean_rebuild']['max_metric_abs_diff']}`",
        f"- `record_multisets_match`: `{payload['clean_rebuild']['record_multisets_match']}`",
        "",
        "## Verification",
        "",
        "After downloading the raw files into the canonical run directory, rerun:",
        "",
        "```powershell",
        "uv --project _bestrec_run run python _bestrec_sota_lab/prepare_raw_record_release.py --verify-only",
        "```",
        "",
        "A public submission should replace the pending archive URL/DOI above by rerunning this script with `--archive-url` and/or `--archive-doi` after upload.",
    ]
    return "\n".join(lines) + "\n"


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    canonical_dir = RUNS_DIR / args.canonical_run_id
    rebuild_dir = RUNS_DIR / args.rebuild_run_id
    compare_path = rebuild_dir / "full_clean_rebuild_compare.json"
    if not canonical_dir.exists():
        raise FileNotFoundError(canonical_dir)
    if not compare_path.exists():
        raise FileNotFoundError(compare_path)
    records: dict[str, Any] = {}
    for dataset in DATASETS:
        path = canonical_dir / f"cold_full_catalog_records_{dataset}.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        records[dataset] = stream_file_stats(path)
    compare = read_json(compare_path)
    archive_uploaded = bool(args.archive_url or args.archive_doi)
    archive_note = (
        "Raw JSONL files are published at the recorded archive URL/DOI; verify downloaded files against this manifest before reanalysis."
        if archive_uploaded
        else "Upload raw JSONL files and this manifest to a durable public archive before final external submission."
    )
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "canonical_run_id": args.canonical_run_id,
        "rebuild_run_id": args.rebuild_run_id,
        "records": records,
        "total_bytes": sum(int(row["bytes"]) for row in records.values()),
        "total_rows": sum(int(row["rows"]) for row in records.values()),
        "clean_rebuild": {
            "compare_path": rel(compare_path),
            "passed": bool(compare.get("passed")),
            "max_metric_abs_diff": compare.get("max_metric_abs_diff"),
            "record_multisets_match": bool(compare.get("record_multisets_match")),
            "record_multiset_fingerprints": compare.get("record_multiset_fingerprints", []),
        },
        "external_archive": {
            "status": "uploaded" if archive_uploaded else "not_uploaded",
            "url": args.archive_url or None,
            "doi": args.archive_doi or None,
            "note": archive_note,
        },
    }
    if not payload["clean_rebuild"]["passed"] or not payload["clean_rebuild"]["record_multisets_match"]:
        raise RuntimeError("Clean-rebuild comparison is not publication-grade")
    return payload


def verify_manifest(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for dataset, expected in payload.get("records", {}).items():
        path = ROOT / expected["path"]
        if not path.exists():
            failures.append(f"{dataset}: missing {path}")
            continue
        actual = stream_file_stats(path)
        for key in ("bytes", "rows", "sha256"):
            if actual[key] != expected[key]:
                failures.append(f"{dataset}: {key} mismatch expected={expected[key]} actual={actual[key]}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-run-id", default=DEFAULT_CANONICAL_RUN_ID)
    parser.add_argument("--rebuild-run-id", default=DEFAULT_REBUILD_RUN_ID)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--archive-url", default="")
    parser.add_argument("--archive-doi", default="")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    manifest_path = out_dir / "raw_record_release_manifest.json"
    if args.verify_only:
        payload = read_json(manifest_path)
        failures = verify_manifest(payload)
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        print(f"Raw record release manifest verified: {manifest_path}")
        return 0

    payload = build_payload(args)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, payload)
    md_path = out_dir / "RAW_RECORD_RELEASE.md"
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    failures = verify_manifest(payload)
    if failures:
        raise RuntimeError("; ".join(failures))
    print(f"Wrote {manifest_path}")
    print(f"Wrote {md_path}")
    print(f"Total bytes: {payload['total_bytes']:,}")
    print(f"Total rows: {payload['total_rows']:,}")
    print(f"External archive status: {payload['external_archive']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
