"""Strict final gate for public paper submission.

This is intentionally stricter than `audit_real_fair_reproducible.py`. The
artifact audit can approve the local cold-item claim, while this gate blocks a
public submission until the raw per-record JSONL files have a durable external
archive URL or DOI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sota_common import LAB_DIR, ROOT, RUNS_DIR, write_json


DEFAULT_RUN_ID = "full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705"
RAW_MANIFEST = LAB_DIR / "publication_artifacts" / "raw_record_release" / "raw_record_release_manifest.json"
RAW_UPLOAD_PARTS_MANIFEST = LAB_DIR / "publication_artifacts" / "raw_record_release" / "raw_record_upload_parts_manifest.json"
RAW_RELEASE_DIR = LAB_DIR / "publication_artifacts" / "raw_record_release"
PAPER_MD = LAB_DIR / "paper_draft" / "lc2c_retrieval_ltr_paper.md"
PAPER_PDF = LAB_DIR / "paper_draft" / "build" / "lc2c_retrieval_ltr_paper.pdf"
PAPER_HTML = LAB_DIR / "paper_draft" / "build" / "lc2c_retrieval_ltr_paper.html"
STRICT_REPORT_NAME = "STRICT_REAL_FAIR_REPRO_REVIEW_CURRENT.md"
OUT_JSON = LAB_DIR / "publication_artifacts" / "public_submission_gate.json"
OUT_MD = LAB_DIR / "publication_artifacts" / "PUBLIC_SUBMISSION_GATE.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def command_ok(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": int(proc.returncode),
        "stdout_tail": proc.stdout.splitlines()[-20:],
        "stderr_tail": proc.stderr.splitlines()[-20:],
        "passed": proc.returncode == 0,
    }


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def has_external_archive(raw_manifest: dict[str, Any]) -> tuple[bool, str]:
    archive = raw_manifest.get("external_archive", {})
    status = archive.get("status")
    url = archive.get("url")
    doi = archive.get("doi")
    if status != "uploaded":
        return False, f"external_archive.status={status!r}; expected 'uploaded'"
    if not (url or doi):
        return False, "external archive is marked uploaded but has neither URL nor DOI"
    return True, "external archive URL/DOI present"


def github_release_tag(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"/releases/tag/([^/?#]+)", url)
    if not match:
        return None
    return match.group(1)


def expected_release_assets() -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    fixed_files = [
        RAW_RELEASE_DIR / "raw_record_release_manifest.json",
        RAW_RELEASE_DIR / "raw_record_upload_parts_manifest.json",
        RAW_RELEASE_DIR / "RAW_RECORD_RELEASE.md",
        RAW_RELEASE_DIR / "RAW_RECORD_UPLOAD_PARTS.md",
    ]
    for path in fixed_files:
        assets[path.name] = {
            "size": path.stat().st_size,
            "sha256": sha256_path(path),
            "path": rel(path),
        }
    parts_manifest = read_json(RAW_UPLOAD_PARTS_MANIFEST, {})
    for entry in parts_manifest.get("datasets", {}).values():
        for part in entry.get("parts", []):
            assets[part["name"]] = {
                "size": int(part["bytes"]),
                "sha256": part["sha256"],
                "path": part["path"],
            }
    return assets


def verify_github_release_assets(raw_manifest: dict[str, Any]) -> dict[str, Any]:
    archive = raw_manifest.get("external_archive", {})
    tag = github_release_tag(archive.get("url"))
    result: dict[str, Any] = {
        "name": "github_release_assets_match_manifests",
        "release_url": archive.get("url"),
        "tag": tag,
        "passed": False,
    }
    if not tag:
        result["reason"] = "external archive URL is not a GitHub release tag URL"
        return result
    proc = subprocess.run(
        ["gh", "release", "view", tag, "--json", "url,assets"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    result["command"] = ["gh", "release", "view", tag, "--json", "url,assets"]
    result["returncode"] = int(proc.returncode)
    if proc.returncode != 0:
        result["reason"] = "gh release view failed"
        result["stdout_tail"] = proc.stdout.splitlines()[-20:]
        result["stderr_tail"] = proc.stderr.splitlines()[-20:]
        return result
    release = json.loads(proc.stdout)
    expected = expected_release_assets()
    actual = {asset["name"]: asset for asset in release.get("assets", [])}
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatches: list[str] = []
    for name, exp in expected.items():
        asset = actual.get(name)
        if not asset:
            continue
        if int(asset.get("size", -1)) != int(exp["size"]):
            mismatches.append(f"{name}: size expected={exp['size']} actual={asset.get('size')}")
        digest = asset.get("digest") or ""
        if digest.startswith("sha256:") and digest.split(":", 1)[1] != exp["sha256"]:
            mismatches.append(f"{name}: sha256 expected={exp['sha256']} actual={digest}")
        if asset.get("state") != "uploaded":
            mismatches.append(f"{name}: state expected=uploaded actual={asset.get('state')}")
    result.update(
        {
            "asset_count_expected": len(expected),
            "asset_count_actual": len(actual),
            "missing_assets": missing,
            "unexpected_assets": unexpected,
            "mismatches": mismatches,
            "passed": not missing and not unexpected and not mismatches,
        }
    )
    if result["passed"]:
        result["reason"] = "GitHub release assets match local manifests by name, size, and available SHA256 digest"
    else:
        result["reason"] = "GitHub release assets do not match local manifests"
    return result


def check_public_submission(run_id: str, deep_verify_raw: bool, verify_github_release: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    run_dir = RUNS_DIR / run_id
    strict_report = run_dir / STRICT_REPORT_NAME
    strict_text = read_text(strict_report)
    strict_ok = "Decision: **Approve" in strict_text and "No blocking findings were detected" in strict_text
    checks.append(
        {
            "name": "strict_artifact_audit_approved",
            "path": rel(strict_report) if strict_report.exists() else str(strict_report),
            "passed": strict_ok,
        }
    )
    if not strict_ok:
        failures.append("strict artifact audit is not currently approved")

    raw_manifest = read_json(RAW_MANIFEST, {})
    raw_exists = bool(raw_manifest)
    archive_ok, archive_reason = has_external_archive(raw_manifest) if raw_exists else (False, "raw manifest missing")
    checks.append(
        {
            "name": "raw_records_externally_archived",
            "path": rel(RAW_MANIFEST),
            "passed": archive_ok,
            "reason": archive_reason,
            "total_bytes": raw_manifest.get("total_bytes"),
            "total_rows": raw_manifest.get("total_rows"),
        }
    )
    if not archive_ok:
        failures.append("raw per-record JSONL files are not yet externally archived")

    if verify_github_release:
        release_check = verify_github_release_assets(raw_manifest)
        checks.append(release_check)
        if not release_check["passed"]:
            failures.append("GitHub release assets do not match the local raw-record upload manifests")

    if deep_verify_raw:
        verify = command_ok([sys.executable, str(LAB_DIR / "prepare_raw_record_release.py"), "--verify-only"])
        verify["name"] = "raw_record_manifest_deep_verify"
        checks.append(verify)
        if not verify["passed"]:
            failures.append("raw record release manifest failed deep verification")

    paper_text = read_text(PAPER_MD)
    build_fresh = PAPER_MD.exists() and PAPER_PDF.exists() and PAPER_HTML.exists() and PAPER_PDF.stat().st_mtime >= PAPER_MD.stat().st_mtime and PAPER_HTML.stat().st_mtime >= PAPER_MD.stat().st_mtime
    checks.append(
        {
            "name": "paper_rendered_outputs_present_and_fresh",
            "paths": [rel(PAPER_MD), rel(PAPER_PDF), rel(PAPER_HTML)],
            "passed": build_fresh,
        }
    )
    if not build_fresh:
        failures.append("rendered paper outputs are missing or older than the Markdown source")

    required_phrases = [
        "full-catalog cold-item",
        "external_archive.status=\"not_uploaded\"" if not archive_ok else "raw-record archive",
        "does not establish general recommender SOTA",
        "not claimed as completed full-catalog cold-item baselines",
    ]
    missing_phrases = [phrase for phrase in required_phrases if phrase not in paper_text]
    checks.append(
        {
            "name": "paper_claim_boundaries_present",
            "passed": not missing_phrases,
            "missing_phrases": missing_phrases,
        }
    )
    if missing_phrases:
        failures.append("paper is missing required claim-boundary/raw-archive language")

    stale_patterns = [
        r"62 source files",
        r"1742da4a",
        r"Current strict gate still fails",
        r"publication gate remains failed",
        r"best recorded modern cold-start baseline",
    ]
    if archive_ok:
        stale_patterns.append(r"external_archive\.status=\"not_uploaded\"")
    stale_hits = []
    for pattern in stale_patterns:
        if re.search(pattern, paper_text, re.IGNORECASE):
            stale_hits.append(pattern)
    checks.append({"name": "paper_no_stale_rejection_or_provenance_text", "passed": not stale_hits, "stale_hits": stale_hits})
    if stale_hits:
        failures.append("paper contains stale rejection/provenance wording")

    return {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "run_id": run_id,
        "passed": not failures,
        "decision": "approve_public_submission" if not failures else "block_public_submission",
        "failures": failures,
        "checks": checks,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Public Submission Gate",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        f"Run id: `{payload['run_id']}`",
        "",
        f"Decision: **{payload['decision']}**",
        "",
    ]
    if payload["failures"]:
        lines.extend(["## Blocking Failures", ""])
        lines.extend(f"- {failure}" for failure in payload["failures"])
        lines.append("")
    lines.extend(["## Checks", "", "| Check | Passed | Detail |", "| --- | ---: | --- |"])
    for check in payload["checks"]:
        detail = check.get("reason") or check.get("path") or ""
        if check.get("missing_phrases"):
            detail = "missing: " + ", ".join(check["missing_phrases"])
        if check.get("stale_hits"):
            detail = "stale hits: " + ", ".join(check["stale_hits"])
        lines.append(f"| `{check['name']}` | `{check.get('passed')}` | {detail} |")
    lines.append("")
    if payload["passed"]:
        lines.append(
            "This gate is intentionally stricter than the local artifact audit. Passing means the strict artifact report, local raw records, external release assets, rendered paper, and claim-boundary language all agreed at generation time."
        )
    else:
        lines.append(
            "This gate is intentionally stricter than the local artifact audit. It should remain blocked until the raw JSONL records are uploaded to a durable external archive and the raw-record release manifest is regenerated with the archive URL or DOI."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--deep-verify-raw", action="store_true")
    parser.add_argument("--verify-github-release", action="store_true")
    args = parser.parse_args()

    payload = check_public_submission(args.run_id, args.deep_verify_raw, args.verify_github_release)
    write_json(OUT_JSON, payload)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print("Public submission gate:", "PASSED" if payload["passed"] else "BLOCKED")
    for failure in payload["failures"]:
        print(f"- {failure}")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
