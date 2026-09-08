#!/usr/bin/env python3
"""Externally complete an already-exited RIPPLE run after verifier-only failure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from launch_and_verify import (
    pid_is_running,
    publish_json_exclusive,
    sha256_file,
    utc_now,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify one existing, exited RIPPLE run without rerunning it."
    )
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--stdout-log", type=Path, required=True)
    parser.add_argument("--stderr-log", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run_directory = args.run_directory.resolve()
    stdout_path = args.stdout_log.resolve()
    stderr_path = args.stderr_log.resolve()
    candidates = sorted(run_directory.glob("RUNNER_COMPLETE_*.json"))
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected one runner completion candidate, found {len(candidates)}"
        )
    candidate_path = candidates[0]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    runner_pid = int(candidate["pid"])
    if pid_is_running(runner_pid):
        raise RuntimeError(f"Runner PID is still active: {runner_pid}")
    lock_path = Path(candidate["runner_lock"])
    if lock_path.exists():
        raise RuntimeError(f"Runner lock still exists: {lock_path}")
    if not stdout_path.is_file() or not stderr_path.is_file():
        raise RuntimeError("Persistent stdout/stderr log is missing")

    ledger_path = run_directory / candidate["asynchronous_error_ledger"]
    if not ledger_path.is_file() or ledger_path.stat().st_size != 0:
        raise RuntimeError("Asynchronous error ledger is missing or nonempty")

    artifact_hashes = candidate["artifact_sha256"]
    for relative_name, expected_hash in artifact_hashes.items():
        artifact = run_directory / relative_name
        if not artifact.is_file():
            raise RuntimeError(f"Missing candidate-bound artifact: {artifact}")
        if sha256_file(artifact) != expected_hash:
            raise RuntimeError(f"Artifact hash mismatch: {relative_name}")

    result_path = run_directory / candidate["result_file"]
    if sha256_file(result_path) != candidate["result_sha256"]:
        raise RuntimeError("Result hash does not match completion candidate")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    external_marker = run_directory / (
        "EXTERNAL_COMPLETE_" + candidate["execution_fingerprint_sha256"][:16] + ".json"
    )
    publish_json_exclusive(
        external_marker,
        {
            "schema": "ripple-external-completion-v1",
            "verified_utc": utc_now(),
            "verification_mode": "existing_exited_run_after_verifier_only_failure",
            "runner_pid": runner_pid,
            "runner_process_has_exited": True,
            "runner_lock_released": True,
            "candidate_marker": candidate_path.name,
            "candidate_marker_sha256": sha256_file(candidate_path),
            "verified_candidate_artifact_count": len(artifact_hashes),
            "asynchronous_error_ledger_empty": True,
            "stdout_log": str(stdout_path),
            "stdout_sha256": sha256_file(stdout_path),
            "stderr_log": str(stderr_path),
            "stderr_sha256": sha256_file(stderr_path),
            "result_file": result_path.name,
            "result_sha256": sha256_file(result_path),
            "protocol_sha256": candidate["protocol_sha256"],
            "execution_fingerprint_sha256": candidate[
                "execution_fingerprint_sha256"
            ],
            "promise_gate_passed": bool(result["promise_gate"]["passed"]),
        },
    )
    print(f"EXTERNAL_COMPLETION_MARKER={external_marker}", flush=True)
    print(f"RESULT_FILE={result_path}", flush=True)
    print(
        "PROMISE_GATE_PASSED="
        + str(bool(result["promise_gate"]["passed"])).lower(),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
