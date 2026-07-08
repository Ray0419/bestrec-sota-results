"""Package the Video_Games sparse-RRF five-seed confirmatory evidence.

This script is deliberately narrower than the four-dataset publication
finalizer. It verifies and records the local Video_Games component-comparator
evidence without upgrading it into a broad SOTA claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = ROOT / "_bestrec_sota_lab"
RUNS_DIR = LAB_DIR / "runs"
DEFAULT_SEEDS = [20260801, 20260802, 20260803, 20260804, 20260805]
COMPONENTS = ["dev4", "dev5", "dev9", "dev10", "dev13", "sasrec"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    record.update({"sha256": digest.hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return record


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def replay_dir(seed: int) -> Path:
    return RUNS_DIR / f"video_games_sparse_rrf_full_catalog_confirmatory_seed{seed}"


def replay_summary_path(seed: int) -> Path:
    return replay_dir(seed) / "sparse_rrf_full_catalog_frozen_test_summary.json"


def replay_records_path(seed: int) -> Path:
    return replay_dir(seed) / "full_catalog_records_Video_Games_sparse_rrf_frozen_test.jsonl"


def component_records_path(seed: int, component: str) -> Path:
    if component == "sasrec":
        return (
            RUNS_DIR
            / f"video_games_confirmatory_seed{seed}_sasrec_export_test"
            / "warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl"
        )
    return (
        RUNS_DIR
        / f"video_games_confirmatory_seed{seed}_{component}_export_test"
        / "warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl"
    )


def component_summary_path(seed: int, component: str) -> Path:
    if component == "sasrec":
        return RUNS_DIR / f"video_games_confirmatory_seed{seed}_sasrec_export_test" / "sasrec_sbert_export_summary.json"
    return RUNS_DIR / f"video_games_confirmatory_seed{seed}_{component}_export_test" / "strict_hstu_export_test_summary.json"


def metric_from_rank(rank: int) -> dict[str, float]:
    rank0 = int(rank) - 1
    return {
        "ndcg10": 1.0 / math.log2(rank0 + 2) if rank0 < 10 else 0.0,
        "hr10": 1.0 if rank0 < 10 else 0.0,
        "rr": 1.0 / float(rank0 + 1),
    }


def stream_recompute(path: Path, *, expected_seed: int) -> dict[str, Any]:
    sums = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    records = 0
    users: set[int] = set()
    targets: set[int] = set()
    scopes: set[str] = set()
    methods: set[str] = set()
    publication_grade_values: set[bool] = set()
    evidence_stage_values: set[str] = set()
    problems: list[str] = []
    required = {
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
        "rank",
    }
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = sorted(required - set(row))
            if missing:
                problems.append(f"line {line_no}: missing {missing}")
                continue
            if row["dataset"] != "Video_Games":
                problems.append(f"line {line_no}: dataset={row['dataset']!r}")
            if int(row["seed"]) != int(expected_seed):
                problems.append(f"line {line_no}: seed={row['seed']!r}, expected {expected_seed}")
            if int(row["fold_id"]) != 0:
                problems.append(f"line {line_no}: fold_id={row['fold_id']!r}")
            scopes.add(str(row["candidate_scope"]))
            methods.add(str(row["method"]))
            users.add(int(row["user_id"]))
            targets.add(int(row["target_item_id"]))
            if "publication_grade" in row:
                publication_grade_values.add(bool(row["publication_grade"]))
            if "evidence_stage" in row:
                evidence_stage_values.add(str(row["evidence_stage"]))
            recomputed = metric_from_rank(int(row["rank"]))
            for metric in sums:
                value = float(row[metric])
                if not math.isfinite(value) or value < 0.0 or value > 1.0:
                    problems.append(f"line {line_no}: {metric}={value}")
                if abs(value - recomputed[metric]) > 1e-12:
                    problems.append(f"line {line_no}: {metric}={value}, recomputed={recomputed[metric]}")
                sums[metric] += value
            records += 1
    return {
        "records": records,
        "unique_users": len(users),
        "unique_targets": len(targets),
        "candidate_scopes": sorted(scopes),
        "methods": sorted(methods),
        "raw_publication_grade_values": sorted(publication_grade_values),
        "raw_evidence_stage_values": sorted(evidence_stage_values),
        "metrics": {metric: sums[metric] / records if records else None for metric in sums},
        "problem_count": len(problems),
        "problems": problems[:20],
    }


def close_enough(left: float | None, right: float | None, tol: float = 1e-12) -> bool:
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tol


def missing_count(value: Any) -> int:
    if value is None:
        return -1
    if isinstance(value, list):
        return len(value)
    return int(value)


def build_seed_report(seed: int) -> dict[str, Any]:
    summary_path = replay_summary_path(seed)
    records_path = replay_records_path(seed)
    summary = read_json(summary_path)
    recomputed = stream_recompute(records_path, expected_seed=seed)
    summary_metrics = summary.get("metrics", {})
    metric_matches = {
        metric: close_enough(recomputed["metrics"].get(metric), summary_metrics.get(metric))
        for metric in ("ndcg10", "hr10", "rr")
    }
    problems: list[str] = []
    if summary.get("candidate_scope") != "full_catalog":
        problems.append(f"summary candidate_scope={summary.get('candidate_scope')!r}")
    if summary.get("target_mismatches_first20"):
        problems.append("summary reports target mismatches")
    if recomputed["candidate_scopes"] != ["full_catalog"]:
        problems.append(f"record scopes={recomputed['candidate_scopes']}")
    if recomputed["methods"] != ["multi_rrf_sparse_full_catalog_frozen"]:
        problems.append(f"record methods={recomputed['methods']}")
    if recomputed["records"] != 94762:
        problems.append(f"records={recomputed['records']}, expected 94762")
    if recomputed["problem_count"]:
        problems.append(f"record metric/schema problems={recomputed['problem_count']}")
    if not all(metric_matches.values()):
        problems.append(f"summary metrics do not match recomputed metrics: {metric_matches}")
    return {
        "seed": seed,
        "status": "valid" if not problems else "invalid",
        "summary": sha256_file(summary_path),
        "records": sha256_file(records_path),
        "summary_metrics": summary_metrics,
        "recomputed": recomputed,
        "metric_matches": metric_matches,
        "target_mismatches_first20": summary.get("target_mismatches_first20", []),
        "problems": problems,
    }


def component_report(seed: int, component: str) -> dict[str, Any]:
    records_path = component_records_path(seed, component)
    summary_path = component_summary_path(seed, component)
    report = {
        "seed": seed,
        "component": component,
        "records": sha256_file(records_path),
        "summary": sha256_file(summary_path),
    }
    if summary_path.exists():
        summary = read_json(summary_path)
        report["status"] = summary.get("status")
        if component == "sasrec":
            report["metrics"] = summary.get("export", {}).get("metrics")
            report["raw_publication_grade"] = summary.get("publication_grade")
            report["raw_evidence_stage"] = summary.get("evidence_stage")
        else:
            report["best_epoch"] = summary.get("best_epoch")
            report["best_valid"] = summary.get("best_valid")
            report["test"] = summary.get("test")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(RUNS_DIR / "video_games_sparse_rrf_confirmatory_20260801_20260805_audit"))
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    args = parser.parse_args()

    seeds = [int(part.strip()) for part in args.seeds.split(",") if part.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    protocol_path = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_protocol_20260609.json"
    frozen_manifest_path = LAB_DIR / "frozen_candidates" / "video_games_multi_rrf_candidate_20260609.json"
    input_check_path = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_input_check.json"
    job_manifest_path = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_jobs.json"
    job_status_path = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_job_status.jsonl"
    significance_path = out_dir / "video_games_confirmatory_component_significance.json"
    local_report_path = out_dir / "STRICT_LOCAL_VIDEO_GAMES_GATE_REPORT.md"

    seed_reports = [build_seed_report(seed) for seed in seeds]
    components = [component_report(seed, component) for seed in seeds for component in COMPONENTS]
    significance = read_json(significance_path)
    local_gate = significance.get("gate_local_video_games", {})
    input_check = read_json(input_check_path)
    component_missing = [
        item
        for item in components
        if not item.get("records", {}).get("exists") or not item.get("summary", {}).get("exists")
    ]
    blockers: list[str] = []
    warnings: list[str] = []
    input_missing_count = missing_count(input_check.get("missing_component_files"))
    input_ready = input_check.get("status") == "ready" or bool(input_check.get("ready_to_replay_confirmatory"))
    if not input_ready or input_missing_count != 0:
        blockers.append("confirmatory input checker is not ready")
    if component_missing:
        blockers.append(f"{len(component_missing)} component record/summary artifacts are missing")
    bad_seeds = [report for report in seed_reports if report["status"] != "valid"]
    if bad_seeds:
        blockers.append(f"{len(bad_seeds)} replay seeds failed schema/metric validation")
    if not local_gate.get("passed_local_video_games_component_gate"):
        blockers.append("local Video_Games component-comparator gate did not pass")
    for report in seed_reports:
        if report["recomputed"]["raw_publication_grade_values"] == [False]:
            warnings.append(
                f"seed {report['seed']} raw replay records predate evidence-stage metadata and keep publication_grade=false"
            )
    for item in components:
        if item["component"] == "sasrec" and item.get("raw_publication_grade") is False:
            warnings.append(
                f"seed {item['seed']} SASRec summary predates evidence-stage metadata and keeps publication_grade=false"
            )

    local_claim_allowed = not blockers
    manifest = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "command": [sys.executable, *sys.argv],
        "evidence_scope": "Video_Games-only frozen sparse-RRF component-comparator confirmatory replay",
        "claim_scope": {
            "allowed_local_claim": (
                "The frozen sparse RRF candidate improves over its strongest frozen Video_Games component "
                "baseline across five fresh full-catalog replay seeds."
            )
            if local_claim_allowed
            else None,
            "broad_sota_publication_claim_allowed": False,
            "broad_sota_publication_blockers": [
                "Evidence covers Video_Games only, not the four BEST-Rec datasets.",
                "Comparators are frozen components, not the full modern baseline suite.",
                "Official four-dataset baseline records and publication finalizer gates remain separate.",
                "Raw SASRec/replay artifacts produced before this repair use conservative publication_grade=false metadata.",
            ],
        },
        "local_gate_passed": local_claim_allowed,
        "protocol": sha256_file(protocol_path),
        "frozen_candidate_manifest": sha256_file(frozen_manifest_path),
        "confirmatory_input_check": {
            "artifact": sha256_file(input_check_path),
            "status": input_check.get("status"),
            "ready_to_replay_confirmatory": input_check.get("ready_to_replay_confirmatory"),
            "missing_component_files": input_check.get("missing_component_files"),
            "missing_component_file_count": input_missing_count,
        },
        "job_manifest": sha256_file(job_manifest_path),
        "job_status_log": sha256_file(job_status_path),
        "significance": sha256_file(significance_path),
        "strict_local_report": sha256_file(local_report_path),
        "seeds": seed_reports,
        "components": components,
        "metadata_repair_policy": {
            "raw_artifacts_mutated": False,
            "new_source_metadata_fields": [
                "evidence_stage",
                "evidence_scope",
                "claim_scope",
                "protocol_manifest",
                "publication_grade",
            ],
            "interpretation": (
                "This manifest is the canonical provenance layer for the completed five-seed local evidence. "
                "It preserves hashes of raw artifacts instead of editing them after the fact."
            ),
        },
        "warnings": warnings[:80],
        "blockers": blockers,
    }
    out_path = out_dir / "video_games_confirmatory_provenance_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed" if local_claim_allowed else "failed", "out": rel(out_path), "blockers": blockers}, indent=2))
    return 0 if local_claim_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
