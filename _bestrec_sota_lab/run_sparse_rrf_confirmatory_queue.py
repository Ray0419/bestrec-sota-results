"""Queue-safe launcher for frozen sparse-RRF confirmatory component jobs.

This helper wraps `run_sparse_rrf_confirmatory_component_jobs.py` without
changing the frozen component definitions. It plans the next runnable jobs,
skips completed exports, respects dependency checkpoints, and refuses to start
new work while the status log contains an unfinished job_started event.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import run_sparse_rrf_confirmatory_component_jobs as jobs_mod


DEFAULT_PLAN = (
    jobs_mod.LAB_DIR
    / "frozen_candidates"
    / "video_games_sparse_rrf_confirmatory_queue_plan.json"
)
TERMINAL_EVENTS = {
    "job_completed",
    "job_failed",
    "job_failed_train",
    "job_failed_export",
    "skip_existing_output",
    "blocked_missing_dependencies",
}


def parse_components(text: str | None) -> set[str] | None:
    if not text:
        return None
    components = {part.strip() for part in text.split(",") if part.strip()}
    allowed = {"dev4", "dev5", "dev9", "dev10", "dev13", "sasrec"}
    unknown = components - allowed
    if unknown:
        raise SystemExit(f"Unknown components: {sorted(unknown)}")
    return components


def read_status_events(status_path: Path) -> list[dict[str, Any]]:
    if not status_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(status_path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            events.append({"event": "malformed_status_line", "line_no": line_no, "raw": line[:500]})
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def active_jobs_from_status(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    active: dict[str, dict[str, Any]] = {}
    for event in events:
        key = str(event.get("job", ""))
        if not key:
            continue
        name = str(event.get("event", ""))
        if name == "job_started":
            active[key] = event
        elif name in TERMINAL_EVENTS:
            active.pop(key, None)
    return active


def classify_jobs(
    jobs: list[dict[str, Any]],
    *,
    seed: int | None,
    components: set[str] | None,
    active_jobs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    completed: list[dict[str, Any]] = []
    active: list[dict[str, Any]] = []
    ready: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for job in jobs:
        if seed is not None and int(job["seed"]) != seed:
            continue
        if components is not None and str(job["component"]) not in components:
            continue
        key = jobs_mod.job_key(job)
        expected = Path(job["expected_output"])
        record = {
            "job": key,
            "seed": int(job["seed"]),
            "component": str(job["component"]),
            "kind": str(job["kind"]),
            "expected_output": str(expected),
        }
        if expected.exists():
            completed.append(record | {"reason": "expected_output_exists"})
            continue
        if key in active_jobs:
            active.append(record | {"reason": "status_log_has_unfinished_job_started"})
            continue
        problems = jobs_mod.dependency_problems(job)
        if problems:
            blocked.append(record | {"problems": problems})
            continue
        ready.append(record)
    return {
        "completed": completed,
        "active": active,
        "ready": ready,
        "blocked": blocked,
    }


def write_plan(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default=str(jobs_mod.DEFAULT_PROTOCOL))
    parser.add_argument("--status-out", default=str(jobs_mod.DEFAULT_STATUS))
    parser.add_argument("--log-dir", default=str(jobs_mod.DEFAULT_LOG_DIR))
    parser.add_argument("--plan-out", default=str(DEFAULT_PLAN))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--components", default=None, help="Comma-separated subset, e.g. dev4,dev5,sasrec.")
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ignore-active-status", action="store_true")
    args = parser.parse_args()

    if args.max_jobs < 1:
        raise SystemExit("--max-jobs must be >= 1")

    protocol = jobs_mod.read_json(Path(args.protocol))
    seeds = [int(seed) for seed in protocol["fresh_confirmatory_seeds"]]
    jobs = jobs_mod.build_jobs(seeds)
    components = parse_components(args.components)
    status_path = Path(args.status_out)
    events = read_status_events(status_path)
    active_jobs = active_jobs_from_status(events)
    classified = classify_jobs(jobs, seed=args.seed, components=components, active_jobs=active_jobs)

    selected: list[dict[str, Any]] = []
    ready_keys = {record["job"] for record in classified["ready"]}
    for job in jobs:
        if jobs_mod.job_key(job) not in ready_keys:
            continue
        selected.append(job)
        if len(selected) >= args.max_jobs:
            break

    plan = {
        "schema_version": 1,
        "generated_at_utc": jobs_mod.utc_now(),
        "protocol": str(Path(args.protocol)),
        "status_log": str(status_path),
        "filters": {"seed": args.seed, "components": sorted(components) if components else None},
        "counts": {
            "completed": len(classified["completed"]),
            "active": len(classified["active"]),
            "ready": len(classified["ready"]),
            "blocked": len(classified["blocked"]),
            "selected": len(selected),
        },
        "active": classified["active"],
        "selected": [
            {
                "job": jobs_mod.job_key(job),
                "seed": int(job["seed"]),
                "component": str(job["component"]),
                "kind": str(job["kind"]),
                "expected_output": str(job["expected_output"]),
            }
            for job in selected
        ],
        "ready": classified["ready"],
        "blocked": classified["blocked"],
        "completed": classified["completed"],
        "execute": bool(args.execute),
    }
    write_plan(Path(args.plan_out), plan)
    print(json.dumps({"status": "planned", "plan_out": str(Path(args.plan_out)), "counts": plan["counts"]}, sort_keys=True))

    if not args.execute:
        return 0
    if classified["active"] and not args.ignore_active_status:
        print(
            json.dumps(
                {
                    "status": "refusing_to_launch_while_active_job_exists",
                    "active": classified["active"],
                    "plan_out": str(Path(args.plan_out)),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    if not selected:
        print(json.dumps({"status": "nothing_ready", "plan_out": str(Path(args.plan_out))}, sort_keys=True))
        return 0

    reports: list[dict[str, Any]] = []
    for job in selected:
        reports.append(
            jobs_mod.run_job(
                job,
                status_path=status_path,
                log_dir=Path(args.log_dir),
                force=bool(args.force),
            )
        )
    print(json.dumps({"status": "executed", "jobs": [report.get("job") for report in reports]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
