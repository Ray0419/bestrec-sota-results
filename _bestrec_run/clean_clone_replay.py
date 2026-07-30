#!/usr/bin/env python
"""Run and verify a hash-bound clean-clone submission replay.

Strict mode accepts no metadata waiver. ``--draft-metadata-waiver`` exists only
to document a mechanically clean pre-submission replay while human metadata is
pending; that record is always marked ``release_ready=false``.

The record is written after verifying the subject tree. It can therefore be
committed in one attestation-only child commit without recursive self-hashing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "bestrec.clean-clone-replay.v1"
DEFAULT_OUTPUT = ROOT / "CLEAN_CLONE_ATTESTATION.json"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, check=False
    )
    if check and result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}): "
            + result.stderr.decode("utf-8", "replace").strip()
        )
    return result


def git_text(*args: str) -> str:
    return git(*args).stdout.decode("utf-8", "replace").strip()


def tracked_dirty() -> list[str]:
    body = git_text("status", "--porcelain", "--untracked-files=no")
    return [line for line in body.splitlines() if line.strip()]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def powershell_build(draft_reason: str | None) -> list[str]:
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "paper_tex" / "build.ps1"),
    ]
    if draft_reason:
        cmd.extend(["-Draft", draft_reason])
    return cmd


def stage_specs(source_root: Path | None, draft_reason: str | None) -> list[dict]:
    py = sys.executable
    bootstrap = [py, str(ROOT / "bootstrap_public_clone.py")]
    if source_root:
        bootstrap.extend(["--source-root", str(source_root.resolve())])
    return [
        {"name": "closure_ledger",
         "argv": [py, str(ROOT / "_bestrec_run" / "closure_ledger.py")],
         "sentinel": "CLOSURE LEDGER: PASS"},
        {"name": "release_asset_hydration_and_hash_verification",
         "argv": bootstrap, "sentinel": "PASS: installed="},
        {"name": "strict_empirical_rebuild",
         "argv": [py, str(ROOT / "_bestrec_run" / "rebuild_hstu_submission.py"),
                  "--strict"],
         "sentinel": "SUBMISSION REBUILD: PASS"},
        {"name": "reader_pdf_rebuild",
         "argv": [py, str(ROOT / "_bestrec_run" / "render_paper_pdf.py")],
         "sentinel": "scan: CLEAN"},
        {"name": "venue_pdf_rebuild", "argv": powershell_build(draft_reason),
         "sentinel": "BUILD OK:"},
        {"name": "release_manifest_worktree_verification",
         "argv": [py, str(ROOT / "_bestrec_run" / "update_release_manifest.py"),
                  "--verify"], "sentinel": None},
        {"name": "release_manifest_subject_commit_verification",
         "argv": [py, str(ROOT / "_bestrec_run" / "update_release_manifest.py"),
                  "--verify-git", "HEAD"], "sentinel": None},
    ]


def normalization_rules(source_root: Path | None) -> list[tuple[str, str]]:
    values = [(str(ROOT.resolve()), "<REPO>"), (str(Path.home().resolve()), "<HOME>")]
    if source_root:
        values.append((str(source_root.resolve()), "<VERIFIED_SOURCE>"))
    expanded: list[tuple[str, str]] = []
    for original, replacement in values:
        expanded.extend(((original, replacement),
                         (original.replace("\\", "/"), replacement)))
    return sorted(set(expanded), key=lambda pair: len(pair[0]), reverse=True)


def normalize_text(value: str, rules: list[tuple[str, str]]) -> str:
    for original, replacement in rules:
        value = value.replace(original, replacement)
    return value


def public_remote_url(value: str) -> str:
    """Remove HTTPS credentials while preserving a reproducible public locator."""
    parts = urlsplit(value)
    if parts.scheme and "@" in parts.netloc:
        host = parts.netloc.rsplit("@", 1)[1]
        return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    return value


def run_stage(spec: dict, rules: list[tuple[str, str]]) -> dict:
    started = utc_now()
    tick = time.perf_counter()
    env = dict(os.environ)
    env.pop("DRAFT_WAIVER", None)
    result = subprocess.run(
        spec["argv"], cwd=ROOT, env=env, capture_output=True, check=False
    )
    stdout = normalize_text(result.stdout.decode("utf-8", "replace"), rules)
    stderr = normalize_text(result.stderr.decode("utf-8", "replace"), rules)
    stdout_bytes = stdout.encode("utf-8")
    stderr_bytes = stderr.encode("utf-8")
    sentinel = spec.get("sentinel")
    sentinel_found = sentinel is None or sentinel in stdout + stderr
    record = {
        "name": spec["name"],
        "argv": [normalize_text(str(x), rules) for x in spec["argv"]], "cwd": ".",
        "started_utc": started, "finished_utc": utc_now(),
        "elapsed_seconds": round(time.perf_counter() - tick, 6),
        "exit_code": result.returncode, "required_sentinel": sentinel,
        "sentinel_found": sentinel_found,
        "stdout_bytes": len(stdout_bytes), "stdout_sha256": sha_bytes(stdout_bytes),
        "stdout": stdout,
        "stderr_bytes": len(stderr_bytes), "stderr_sha256": sha_bytes(stderr_bytes),
        "stderr": stderr,
    }
    print(f"[{spec['name']}] exit={result.returncode} sentinel={sentinel_found}")
    if stdout:
        print(stdout[-1200:].rstrip())
    if stderr:
        print(stderr[-800:].rstrip(), file=sys.stderr)
    if result.returncode or not sentinel_found:
        raise RuntimeError(
            f"stage {spec['name']} failed: exit={result.returncode}, "
            f"sentinel_found={sentinel_found}"
        )
    return record


def tool_output(argv: list[str]) -> str:
    try:
        result = subprocess.run(argv, capture_output=True, check=False)
        text = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
        return text.splitlines()[0] if text else f"exit={result.returncode}"
    except OSError as exc:
        return f"unavailable: {exc}"


def graph_summary(stages: list[dict]) -> dict:
    text = "\n".join(stage["stdout"] + stage["stderr"] for stage in stages)
    patterns = [
        re.compile(
            r"cells recomputed OK\s*:\s*(?P<active>\d+).*?"
            r"retired cells\s*:\s*(?P<retired>\d+).*?"
            r"['\"]exact['\"]\s*:\s*(?P<exact>\d+).*?"
            r"['\"]within_rounding['\"]\s*:\s*(?P<rounding>\d+).*?"
            r"['\"]MISMATCH['\"]\s*:\s*(?P<mismatch>\d+).*?"
            r"['\"]UNTRACEABLE['\"]\s*:\s*(?P<untraceable>\d+).*?"
            r"all\s+(?P<families>\d+)\s+declared claim families", re.I | re.S),
        re.compile(
            r"(?P<active>\d+)\s+active cells.*?(?P<retired>\d+)\s+retired.*?"
            r"(?P<exact>\d+)\s+exact\s*\+\s*(?P<rounding>\d+)\s+rounding.*?"
            r"(?:all\s+)?(?P<families>\d+)\s+(?:required\s+)?families", re.I | re.S),
        re.compile(
            r"(?P<active>\d+)\s+(?:paper-bound|reported|active) cells.*?"
            r"(?P<families>\d+)\s+(?:required\s+)?(?:claim\s+)?families", re.I | re.S),
    ]
    match = None
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            break
    if not match:
        raise RuntimeError("could not parse graph cell/family summary from replay output")
    values = {key: int(value) for key, value in match.groupdict().items() if value}
    if "mismatch" not in values or "untraceable" not in values:
        if not (re.search(r"(?:zero|0)\s+(?:paper\s+)?mismatch", text, re.I)
                and re.search(r"(?:zero|0)\s+untraceable", text, re.I)):
            raise RuntimeError("graph summary did not explicitly report zero mismatch/untraceable")
        values.update({"mismatch": 0, "untraceable": 0})
    if values["mismatch"] != 0 or values["untraceable"] != 0:
        raise RuntimeError("graph summary reports mismatch or untraceable cells")
    return values


def artifact_record(subject: str, rel: str) -> dict:
    path = ROOT / rel
    if not path.is_file():
        raise RuntimeError(f"required replay artifact missing: {rel}")
    tracked = git("cat-file", "-e", f"{subject}:{rel}", check=False).returncode == 0
    return {
        "path": rel, "bytes": path.stat().st_size, "sha256": sha_file(path),
        "binding": "subject_commit_blob" if tracked else "verified_worktree_preview_only",
    }


def validate_record_shape(record: dict) -> list[str]:
    errors: list[str] = []
    if record.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    for key in ("subject_commit", "subject_tree"):
        if not HASH_RE.fullmatch(str(record.get(key, ""))):
            errors.append(f"{key} is not a 64-hex digest")
    if record.get("clean_tracked_tree_at_start") is not True:
        errors.append("clean_tracked_tree_at_start is not true")
    if record.get("clean_tracked_tree_at_end") is not True:
        errors.append("clean_tracked_tree_at_end is not true")
    required = {
        "closure_ledger", "release_asset_hydration_and_hash_verification",
        "strict_empirical_rebuild", "reader_pdf_rebuild", "venue_pdf_rebuild",
        "release_manifest_worktree_verification",
        "release_manifest_subject_commit_verification",
    }
    stages = record.get("stages")
    if not isinstance(stages, list):
        errors.append("stages is not a list")
        stages = []
    names = {stage.get("name") for stage in stages if isinstance(stage, dict)}
    if names != required:
        errors.append(f"stage set mismatch: {sorted(str(x) for x in names)}")
    if len(stages) != len(required):
        errors.append(f"stage count mismatch: {len(stages)} != {len(required)}")
    for stage in stages:
        if not isinstance(stage, dict):
            errors.append("non-object stage")
            continue
        if stage.get("exit_code") != 0 or stage.get("sentinel_found") is not True:
            errors.append(f"stage not successful: {stage.get('name')}")
        for stream in ("stdout", "stderr"):
            raw = str(stage.get(stream, "")).encode("utf-8")
            if stage.get(f"{stream}_sha256") != sha_bytes(raw):
                errors.append(f"{stage.get('name')} {stream} hash mismatch")
            if stage.get(f"{stream}_bytes") != len(raw):
                errors.append(f"{stage.get('name')} {stream} byte count mismatch")
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts missing")
    else:
        for item in artifacts:
            if not HASH_RE.fullmatch(str(item.get("sha256", ""))):
                errors.append(f"bad artifact hash: {item.get('path')}")
            if item.get("binding") not in {"subject_commit_blob", "verified_worktree_preview_only"}:
                errors.append(f"unknown artifact binding: {item.get('binding')}")
            if record.get("release_ready") is True and item.get("binding") != "subject_commit_blob":
                errors.append(f"release artifact is not subject-commit-bound: {item.get('path')}")
    graph = record.get("graph_summary", {})
    for key in ("active", "families", "mismatch", "untraceable"):
        if not isinstance(graph.get(key), int):
            errors.append(f"graph_summary.{key} missing/non-integer")
    if graph.get("mismatch") != 0 or graph.get("untraceable") != 0:
        errors.append("graph summary is not fail-closed green")
    if bool(record.get("draft_metadata_waiver")) == bool(record.get("release_ready")):
        errors.append("release_ready must be false exactly when a draft waiver is present")
    return errors


def verify_record(path: Path) -> int:
    record = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_record_shape(record)
    subject = str(record.get("subject_commit", ""))
    if HASH_RE.fullmatch(subject):
        if git("cat-file", "-e", f"{subject}^{{commit}}", check=False).returncode:
            errors.append("subject commit is unavailable")
        else:
            if git_text("rev-parse", f"{subject}^{{tree}}") != record.get("subject_tree"):
                errors.append("subject tree mismatch")
            if git("merge-base", "--is-ancestor", subject, "HEAD", check=False).returncode:
                errors.append("subject commit is not an ancestor of HEAD")
            allowed = {path.resolve().relative_to(ROOT.resolve()).as_posix()}
            changed = set(git_text("diff", "--name-only", f"{subject}..HEAD").splitlines())
            if not changed.issubset(allowed):
                errors.append("post-attestation subject drift outside the record: "
                              + ", ".join(sorted(changed - allowed)))
            for item in record.get("artifacts", []):
                if item.get("binding") == "verified_worktree_preview_only":
                    preview = ROOT / item["path"]
                    if (not preview.is_file() or sha_file(preview) != item.get("sha256")
                            or preview.stat().st_size != item.get("bytes")):
                        errors.append(f"worktree preview artifact mismatch: {item['path']}")
                    continue
                if item.get("binding") != "subject_commit_blob":
                    errors.append(f"unknown artifact binding: {item.get('binding')}")
                    continue
                blob = git("show", f"{subject}:{item['path']}", check=False)
                if blob.returncode or sha_bytes(blob.stdout) != item.get("sha256"):
                    errors.append(f"subject artifact mismatch: {item['path']}")
    if errors:
        for error in errors:
            print("FAIL:", error)
        print("CLEAN CLONE ATTESTATION: FAIL")
        return 2
    print("CLEAN CLONE ATTESTATION: PASS -- "
          f"subject={subject[:12]} active={record['graph_summary']['active']} "
          f"families={record['graph_summary']['families']} "
          f"release_ready={record['release_ready']}")
    return 0


def self_test() -> int:
    stream = "synthetic output\n"
    names = [
        "closure_ledger", "release_asset_hydration_and_hash_verification",
        "strict_empirical_rebuild", "reader_pdf_rebuild", "venue_pdf_rebuild",
        "release_manifest_worktree_verification",
        "release_manifest_subject_commit_verification",
    ]
    sample = {
        "schema": SCHEMA, "subject_commit": "a" * 64, "subject_tree": "b" * 64,
        "clean_tracked_tree_at_start": True, "clean_tracked_tree_at_end": True,
        "draft_metadata_waiver": "metadata pending", "release_ready": False,
        "stages": [{
            "name": name, "exit_code": 0, "sentinel_found": True,
            "stdout": stream, "stdout_bytes": len(stream.encode()),
            "stdout_sha256": sha_bytes(stream.encode()), "stderr": "",
            "stderr_bytes": 0, "stderr_sha256": sha_bytes(b""),
        } for name in names],
        "artifacts": [{"path": "x", "sha256": "c" * 64,
                       "binding": "verified_worktree_preview_only"}],
        "graph_summary": {"active": 1, "families": 1, "mismatch": 0,
                          "untraceable": 0},
    }
    if validate_record_shape(sample):
        raise RuntimeError("valid synthetic attestation was rejected")
    sample["stages"][0]["stdout"] += "tamper"
    if not any("hash mismatch" in e for e in validate_record_shape(sample)):
        raise RuntimeError("tampered transcript was not rejected")
    sample["stages"][0]["stdout"] = stream
    sample["draft_metadata_waiver"] = None
    sample["release_ready"] = True
    if not any("not subject-commit-bound" in e for e in validate_record_shape(sample)):
        raise RuntimeError("strict attestation accepted a worktree-only preview")
    print("clean-clone attestation self-test: PASS")
    return 0


def run_replay(args: argparse.Namespace) -> int:
    dirty = tracked_dirty()
    if dirty:
        raise RuntimeError("subject checkout has tracked changes before replay: "
                           + "; ".join(dirty))
    subject = git_text("rev-parse", "HEAD")
    subject_tree = git_text("rev-parse", "HEAD^{tree}")
    started = utc_now()
    rules = normalization_rules(args.source_root)
    stages = [run_stage(spec, rules) for spec in
              stage_specs(args.source_root, args.draft_metadata_waiver)]
    end_dirty = tracked_dirty()
    if end_dirty:
        raise RuntimeError("replay changed tracked bytes (build is not byte-stable): "
                           + "; ".join(end_dirty))
    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    artifacts = [artifact_record(subject, rel) for rel in (
        "RELEASE_MANIFEST.json", "PAPER_SUBMISSION.pdf",
        "paper_tex/PAPER_TORS.pdf", "paper_tex/PAPER_TORS_acmsmall.pdf")]
    record = {
        "schema": SCHEMA,
        "classification": ("clean_clone_draft_metadata_replay"
                           if args.draft_metadata_waiver else "clean_clone_release_replay"),
        "release_ready": not bool(args.draft_metadata_waiver),
        "draft_metadata_waiver": args.draft_metadata_waiver,
        "subject_commit": subject, "subject_tree": subject_tree,
        "origin_url": public_remote_url(git_text("remote", "get-url", "origin")),
        "started_utc": started, "finished_utc": utc_now(),
        "clean_tracked_tree_at_start": True, "clean_tracked_tree_at_end": True,
        "release_asset_source": ({"mode": "verified_local_source",
                                  "path": "<VERIFIED_SOURCE>"}
                                 if args.source_root else
                                 {"mode": "release_download", "path": None}),
        "transcript_normalization": {
            "absolute_repository_path": "<REPO>",
            "absolute_home_path": "<HOME>",
            "verified_source_path": "<VERIFIED_SOURCE>" if args.source_root else None,
            "credentialed_remote_urls": "credentials removed",
        },
        "toolchain": {
            "platform": platform.platform(), "python": platform.python_version(),
            "git": tool_output(["git", "--version"]),
            "powershell": tool_output(["powershell", "-NoProfile", "-Command",
                                        "$PSVersionTable.PSVersion.ToString()"]),
            "tectonic": tool_output([
                str(Path(os.environ.get("LOCALAPPDATA", "")) / "tectonic" / "tectonic.exe"),
                "--version"]),
        },
        "manifest_declared_commit": manifest.get("git_commit"),
        "manifest_intended_deposit_tag": manifest.get("intended_deposit_tag"),
        "graph_summary": graph_summary(stages), "artifacts": artifacts, "stages": stages,
    }
    errors = validate_record_shape(record)
    if errors:
        raise RuntimeError("generated attestation failed validation: " + "; ".join(errors))
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("attestation output must be inside the repository") from exc
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"CLEAN CLONE REPLAY: PASS -- wrote {output}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-record", type=Path)
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--draft-metadata-waiver", metavar="REASON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()
    if args.verify_record:
        return verify_record(args.verify_record.resolve())
    if args.draft_metadata_waiver is not None and not args.draft_metadata_waiver.strip():
        raise RuntimeError("--draft-metadata-waiver requires a nonempty reason")
    return run_replay(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"CLEAN CLONE REPLAY: FAIL -- {exc}", file=sys.stderr)
        raise SystemExit(2)
