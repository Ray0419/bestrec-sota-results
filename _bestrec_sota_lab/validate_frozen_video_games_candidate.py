"""Strict gate for the frozen Video_Games multi-RRF development candidate.

This validator is intentionally conservative. It verifies that the frozen
manifest matches the generated artifacts, recomputes metrics from the streamed
JSONL records, and writes an approval gate report. The current candidate is
expected to fail publication approval because it is development-only and uses a
top-50 union reranking scope rather than a fresh full-catalog confirmatory run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (
    ROOT
    / "_bestrec_sota_lab"
    / "frozen_candidates"
    / "video_games_multi_rrf_candidate_20260609.json"
)
DEFAULT_OUT = (
    ROOT
    / "_bestrec_sota_lab"
    / "frozen_candidates"
    / "video_games_multi_rrf_candidate_20260609_gate.json"
)
DEFAULT_FULL_CATALOG_SUMMARY = (
    ROOT
    / "_bestrec_sota_lab"
    / "runs"
    / "video_games_sparse_rrf_full_catalog_replay_20260609"
    / "sparse_rrf_full_catalog_frozen_test_summary.json"
)
REQUIRED_RECORD_FIELDS = {
    "dataset",
    "fold_id",
    "seed",
    "method",
    "user_id",
    "target_item_id",
    "candidate_scope",
    "ndcg10",
    "hr10",
    "rr",
    "publication_grade",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_from_rank(rank: int | None) -> dict[str, float]:
    if rank is None:
        return {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    rank0 = int(rank) - 1
    return {
        "ndcg10": 1.0 / math.log2(rank0 + 2) if rank0 < 10 else 0.0,
        "hr10": 1.0 if rank0 < 10 else 0.0,
        "rr": 1.0 / float(rank0 + 1),
    }


def close_enough(left: float, right: float, tol: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tol


def validate_records(path: Path) -> dict[str, Any]:
    counts = {
        "records": 0,
        "ndcg10_sum": 0.0,
        "hr10_sum": 0.0,
        "rr_sum": 0.0,
        "publication_grade_true": 0,
    }
    users: set[int] = set()
    candidate_scopes: set[str] = set()
    methods: set[str] = set()
    seeds: set[int] = set()
    folds: set[int] = set()
    problems: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = REQUIRED_RECORD_FIELDS - set(row)
            if missing:
                problems.append(f"line {line_no}: missing fields {sorted(missing)}")
                continue
            if row["dataset"] != "Video_Games":
                problems.append(f"line {line_no}: dataset={row['dataset']!r}")
            user_id = int(row["user_id"])
            if user_id in users:
                problems.append(f"line {line_no}: duplicate user_id={user_id}")
            users.add(user_id)
            candidate_scopes.add(str(row["candidate_scope"]))
            methods.add(str(row["method"]))
            seeds.add(int(row["seed"]))
            folds.add(int(row["fold_id"]))
            if bool(row["publication_grade"]):
                counts["publication_grade_true"] += 1

            recomputed = metric_from_rank(row.get("rank"))
            for metric in ("ndcg10", "hr10", "rr"):
                value = float(row[metric])
                if not math.isfinite(value) or value < 0.0 or value > 1.0:
                    problems.append(f"line {line_no}: {metric}={value} outside [0,1]")
                if not close_enough(value, recomputed[metric]):
                    problems.append(
                        f"line {line_no}: {metric}={value} but rank recomputes to {recomputed[metric]}"
                    )
                counts[f"{metric}_sum"] += value
            counts["records"] += 1

    n = counts["records"]
    metrics = {
        "ndcg10": counts["ndcg10_sum"] / n if n else None,
        "hr10": counts["hr10_sum"] / n if n else None,
        "rr": counts["rr_sum"] / n if n else None,
    }
    return {
        "records": n,
        "unique_users": len(users),
        "candidate_scopes": sorted(candidate_scopes),
        "methods": sorted(methods),
        "seeds": sorted(seeds),
        "folds": sorted(folds),
        "publication_grade_true": counts["publication_grade_true"],
        "metrics": metrics,
        "problems": problems[:50],
        "problem_count": len(problems),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--full-catalog-summary", default=str(DEFAULT_FULL_CATALOG_SUMMARY))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_path = Path(args.out)
    manifest = read_json(manifest_path)
    blockers: list[str] = []
    warnings: list[str] = []

    if manifest.get("status") != "frozen_development_candidate_not_publication_evidence":
        blockers.append(f"unexpected manifest status: {manifest.get('status')!r}")
    else:
        blockers.append("candidate is explicitly marked as development-only, not publication evidence")
    if manifest.get("approval_gate", {}).get("can_claim_sota_from_this_run") is not False:
        blockers.append("manifest approval gate does not explicitly block SOTA claims")

    artifact_reports: dict[str, Any] = {}
    for name, artifact in manifest.get("artifacts", {}).items():
        path = ROOT / artifact["path"]
        if not path.exists():
            blockers.append(f"{name} artifact missing: {path}")
            artifact_reports[name] = {"path": str(path), "exists": False}
            continue
        actual_hash = sha256_file(path)
        expected_hash = str(artifact.get("sha256", "")).lower()
        if actual_hash.lower() != expected_hash:
            blockers.append(f"{name} hash mismatch: expected {expected_hash}, got {actual_hash}")
        artifact_reports[name] = {
            "path": str(path),
            "exists": True,
            "sha256": actual_hash,
            "hash_matches_manifest": actual_hash.lower() == expected_hash,
        }

    summary_path = ROOT / manifest["artifacts"]["summary"]["path"]
    records_path = ROOT / manifest["artifacts"]["test_records"]["path"]
    summary = read_json(summary_path)
    record_report = validate_records(records_path)
    full_catalog_report: dict[str, Any] = {"present": False, "valid": False}
    full_catalog_summary_path = Path(args.full_catalog_summary)
    if full_catalog_summary_path.exists():
        fc_summary = read_json(full_catalog_summary_path)
        fc_records_raw = fc_summary.get("outputs", {}).get("records", {}).get("path")
        fc_records_path = ROOT / fc_records_raw if fc_records_raw else None
        fc_problems: list[str] = []
        if fc_summary.get("candidate_scope") != "full_catalog":
            fc_problems.append(f"summary candidate_scope={fc_summary.get('candidate_scope')!r}")
        if fc_summary.get("publication_grade") is not False:
            fc_problems.append("summary publication_grade is not false")
        if fc_summary.get("target_mismatches_first20"):
            fc_problems.append("summary reports target mismatches")
        if not fc_records_path or not fc_records_path.exists():
            fc_problems.append(f"full-catalog records missing: {fc_records_path}")
            fc_record_report = {}
        else:
            expected_hash = str(fc_summary.get("outputs", {}).get("records", {}).get("sha256", "")).lower()
            actual_hash = sha256_file(fc_records_path).lower()
            if expected_hash != actual_hash:
                fc_problems.append(f"full-catalog record hash mismatch: expected {expected_hash}, got {actual_hash}")
            fc_record_report = validate_records(fc_records_path)
            if fc_record_report["candidate_scopes"] != ["full_catalog"]:
                fc_problems.append(f"record candidate scopes={fc_record_report['candidate_scopes']}")
            if fc_record_report["publication_grade_true"]:
                fc_problems.append("some full-catalog records are marked publication_grade=true")
            if fc_record_report["problem_count"]:
                fc_problems.append(f"full-catalog record metric/schema problems: {fc_record_report['problem_count']}")
        full_catalog_report = {
            "present": True,
            "valid": not fc_problems,
            "summary": str(full_catalog_summary_path),
            "summary_sha256": sha256_file(full_catalog_summary_path),
            "records": str(fc_records_path) if fc_records_path else None,
            "record_report": fc_record_report,
            "problems": fc_problems,
        }

    expected = manifest.get("development_metrics", {})
    actual = record_report["metrics"]
    for key in ("ndcg10", "hr10", "rr"):
        manifest_key = f"test_{key}" if key != "rr" else "test_rr"
        if not close_enough(actual[key], expected[manifest_key]):
            blockers.append(f"{key} metric mismatch: records={actual[key]} manifest={expected[manifest_key]}")
    if not close_enough(summary.get("test_metrics", {}).get("ndcg10"), expected.get("test_ndcg10")):
        blockers.append("summary test NDCG@10 does not match frozen manifest")

    if record_report["problem_count"]:
        blockers.append(f"record schema/metric problems: {record_report['problem_count']}")
    if record_report["records"] != int(manifest["artifacts"]["test_records"]["records"]):
        blockers.append("record count does not match manifest")
    if record_report["unique_users"] != int(manifest["artifacts"]["test_records"]["unique_users"]):
        blockers.append("unique user count does not match manifest")
    if record_report["publication_grade_true"]:
        blockers.append("some records are marked publication_grade=true")

    if record_report["candidate_scopes"] != ["full_catalog"] and not full_catalog_report.get("valid"):
        blockers.append(
            "candidate scope is not full_catalog and no valid sparse full-catalog replay is present"
        )
    seed_source = full_catalog_report.get("record_report", record_report) if full_catalog_report.get("valid") else record_report
    if len(seed_source.get("seeds", [])) < 5:
        blockers.append("candidate has fewer than five fresh confirmatory seeds")
    if record_report["folds"] != [0]:
        warnings.append("candidate records do not cover the expected confirmatory fold grid")

    report = {
        "schema_version": 1,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "approval": "reject_for_publication_claim",
        "can_claim_sota": False,
        "artifact_reports": artifact_reports,
        "record_report": record_report,
        "full_catalog_sparse_replay": full_catalog_report,
        "summary_selected_config": summary.get("selected_config"),
        "frozen_config": manifest.get("fusion_config"),
        "blockers": blockers,
        "warnings": warnings,
        "required_fix": [
            "Rerun the frozen recipe on fresh confirmatory seeds/splits before inspecting outcomes.",
            "Use the sparse full-catalog replay path for the frozen top-50 RRF scoring function; do not use the top-50-union development artifact as publication evidence.",
            "Compare against the modern baseline suite with per-user Holm-corrected tests and clustered bootstrap intervals.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"approval": report["approval"], "blockers": blockers, "out": str(out_path)}, indent=2))
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
