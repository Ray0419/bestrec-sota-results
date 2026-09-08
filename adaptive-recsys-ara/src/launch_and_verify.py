#!/usr/bin/env python3
"""Launch the RIPPLE outcome runner and verify post-exit completion.

This small wrapper exists because the experiment runner cannot prove its own
PID has exited or its lock has been released. It binds persistent stdout and
stderr, waits for the child, verifies every candidate-marker hash, checks the
empty asynchronous ledger and released lock, and then publishes one immutable
external completion marker.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


THREAD_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def pid_is_running(pid: int) -> bool:
    """Return whether a PID is active without signalling or mutating it."""
    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, int(pid)
        )
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                raise OSError("GetExitCodeProcess failed")
            return int(exit_code.value) == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def publish_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Launch and externally verify a RIPPLE PoC outcome run."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "ripple_poc_ml100k.json",
    )
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=project_root / "experiments" / "runs",
    )
    parser.add_argument("--data-zip", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    runner = project_root / "src" / "ripple_poc.py"
    config = args.config.resolve()
    experiments_root = args.experiments_root.resolve()
    run_id = args.run_id or (
        "ripple-poc-v1-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid.uuid4().hex[:12]
    )
    if Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("run-id must be one safe path component")
    # The runner intentionally isolates its append-only attempts beneath a
    # protocol-specific subdirectory while keeping the lock at experiments_root.
    run_directory = experiments_root / "ripple_poc_runs" / run_id
    if run_directory.exists():
        raise FileExistsError(f"Run directory already exists: {run_directory}")

    launch_directory = project_root / "experiments" / "launches"
    launch_directory.mkdir(parents=True, exist_ok=True)
    stdout_path = launch_directory / f"{run_id}.stdout.log"
    stderr_path = launch_directory / f"{run_id}.stderr.log"
    failure_path = launch_directory / f"{run_id}.external_failure.json"
    if stdout_path.exists() or stderr_path.exists() or failure_path.exists():
        raise FileExistsError("Append-only launcher artifact collision")

    environment = os.environ.copy()
    for key in THREAD_VARS:
        environment[key] = "1"
    environment["CUDA_VISIBLE_DEVICES"] = "-1"
    environment["HF_HUB_OFFLINE"] = "1"
    environment["PYTHONHASHSEED"] = "20260807"

    command = [
        sys.executable,
        "-u",
        str(runner),
        "--config",
        str(config),
        "--experiments-root",
        str(experiments_root),
        "--run-id",
        run_id,
    ]
    if args.data_zip is not None:
        command.extend(["--data-zip", str(args.data_zip.resolve())])

    child_pid: int | None = None
    try:
        with stdout_path.open("xb") as stdout_handle, stderr_path.open(
            "xb"
        ) as stderr_handle:
            process = subprocess.Popen(
                command,
                cwd=project_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            child_pid = process.pid
            return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(f"Outcome runner exited with code {return_code}")
        if not run_directory.is_dir():
            raise RuntimeError(f"Runner did not create {run_directory}")
        candidates = sorted(run_directory.glob("RUNNER_COMPLETE_*.json"))
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected one runner completion candidate, found {len(candidates)}"
            )
        candidate_path = candidates[0]
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        runner_pid = int(candidate["pid"])
        # Some Windows venv launchers create a short-lived shim process, so the
        # waited child PID need not equal the actual interpreter PID recorded by
        # the runner. The completion invariant is that both have exited.
        if pid_is_running(runner_pid):
            raise RuntimeError(f"Runner PID is still active after child exit: {runner_pid}")
        lock_path = Path(candidate["runner_lock"])
        if lock_path.exists():
            raise RuntimeError(f"Runner lock still exists after exit: {lock_path}")

        ledger_path = run_directory / candidate["asynchronous_error_ledger"]
        if not ledger_path.is_file() or ledger_path.stat().st_size != 0:
            raise RuntimeError("Asynchronous error ledger is missing or nonempty")

        artifact_hashes = candidate["artifact_sha256"]
        for relative_name, expected_hash in artifact_hashes.items():
            artifact = run_directory / relative_name
            if not artifact.is_file():
                raise RuntimeError(f"Missing candidate-bound artifact: {artifact}")
            actual_hash = sha256_file(artifact)
            if actual_hash != expected_hash:
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
                "launcher_child_pid": child_pid,
                "child_exit_code": return_code,
                "child_process_has_exited": True,
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
    except BaseException as exc:
        publish_json_exclusive(
            failure_path,
            {
                "schema": "ripple-external-verification-failure-v1",
                "utc": utc_now(),
                "child_pid": child_pid,
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "run_directory": str(run_directory),
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
