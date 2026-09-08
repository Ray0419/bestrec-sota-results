#!/usr/bin/env python3
"""Launch CAPER with the current venv Python and verify it after exit.

The outcome runner cannot prove that its own process has exited or that its
exclusive lock has been released.  This wrapper binds persistent stdout and
stderr, waits for the child, verifies both possible Windows PIDs have exited,
checks every hash bound by the runner-completion candidate, and only then
publishes the sole authoritative external CAPER completion marker.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


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
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, int(pid)
        )
        if not handle:
            error_code = ctypes.get_last_error()
            if error_code == 87:  # ERROR_INVALID_PARAMETER: PID does not exist.
                return False
            if error_code == 5:  # ERROR_ACCESS_DENIED: cannot prove process exit.
                return True
            raise ctypes.WinError(error_code)
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                raise ctypes.WinError(ctypes.get_last_error())
            return int(exit_code.value) == still_active
        finally:
            if not kernel32.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def publish_json_exclusive(path: Path, value: Any) -> None:
    """Publish fsynced JSON exactly once, without replacing an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def contained_file(base: Path, relative_name: str, label: str) -> Path:
    """Resolve a candidate-supplied relative artifact without path escape."""
    relative = Path(relative_name)
    if relative.is_absolute() or relative.name in {"", ".", ".."}:
        raise RuntimeError(f"Invalid {label} path: {relative_name!r}")
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes the run directory: {relative_name}") from exc
    return resolved


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Launch and externally verify a CAPER PoC outcome run."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "caper_poc_ml1m_v1.json",
    )
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=project_root / "experiments" / "runs",
    )
    parser.add_argument("--run-id", default=None)
    return parser.parse_args(argv)


def validate_candidate(
    candidate: Mapping[str, Any], run_directory: Path, candidate_path: Path
) -> tuple[int, Path, Path, Mapping[str, str]]:
    """Validate candidate metadata and every candidate-bound artifact hash."""
    runner_pid = int(candidate["pid"])
    if runner_pid <= 0:
        raise RuntimeError("Runner completion candidate contains an invalid PID")

    recorded_directory = Path(str(candidate["run_directory"])).resolve()
    if recorded_directory != run_directory.resolve():
        raise RuntimeError("Runner completion candidate names a different run directory")
    if candidate.get("runner_lock_release_pending") is not True:
        raise RuntimeError("Runner candidate did not declare lock release pending")
    if candidate.get("external_post_exit_verification_required") is not True:
        raise RuntimeError("Runner candidate did not require external verification")

    ledger_path = contained_file(
        run_directory,
        str(candidate["asynchronous_error_ledger"]),
        "asynchronous error ledger",
    )
    if not ledger_path.is_file() or ledger_path.stat().st_size != 0:
        raise RuntimeError("Asynchronous error ledger is missing or nonempty")

    artifact_hashes_raw = candidate["artifact_sha256"]
    if not isinstance(artifact_hashes_raw, Mapping) or not artifact_hashes_raw:
        raise RuntimeError("Runner candidate has no artifact hash manifest")
    artifact_hashes = {
        str(relative_name): str(expected_hash)
        for relative_name, expected_hash in artifact_hashes_raw.items()
    }
    for relative_name, expected_hash in artifact_hashes.items():
        if len(expected_hash) != 64:
            raise RuntimeError(f"Malformed artifact SHA-256: {relative_name}")
        artifact = contained_file(run_directory, relative_name, "candidate artifact")
        if not artifact.is_file():
            raise RuntimeError(f"Missing candidate-bound artifact: {artifact}")
        if sha256_file(artifact) != expected_hash.lower():
            raise RuntimeError(f"Artifact hash mismatch: {relative_name}")

    ledger_expected = candidate.get("asynchronous_error_ledger_sha256")
    if ledger_expected is not None and sha256_file(ledger_path) != str(
        ledger_expected
    ).lower():
        raise RuntimeError("Asynchronous error ledger hash mismatch")

    result_path = contained_file(
        run_directory, str(candidate["result_file"]), "result file"
    )
    if not result_path.is_file():
        raise RuntimeError(f"Result file is missing: {result_path}")
    result_sha256 = sha256_file(result_path)
    if result_sha256 != str(candidate["result_sha256"]).lower():
        raise RuntimeError("Result hash does not match completion candidate")

    # The completion candidate itself cannot be included in its own manifest,
    # but must remain in the same immutable append-only run directory.
    if candidate_path.parent.resolve() != run_directory.resolve():
        raise RuntimeError("Runner completion candidate is outside the run directory")
    return runner_pid, ledger_path, result_path, artifact_hashes


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    runner = (project_root / "src" / "caper_poc.py").resolve()
    config = args.config.resolve()
    experiments_root = args.experiments_root.resolve()
    python_executable = Path(sys.executable).resolve()
    if not python_executable.is_file():
        raise FileNotFoundError(f"Current Python executable is missing: {python_executable}")
    if not runner.is_file():
        raise FileNotFoundError(f"CAPER outcome runner is missing: {runner}")
    if not config.is_file():
        raise FileNotFoundError(f"CAPER configuration is missing: {config}")

    run_id = args.run_id or (
        "caper-poc-v1-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid.uuid4().hex[:12]
    )
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ValueError("run-id must be one safe path component")
    run_directory = experiments_root / "caper_poc_runs" / run_id
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
    environment["TRANSFORMERS_OFFLINE"] = "1"
    environment["TOKENIZERS_PARALLELISM"] = "false"
    environment["PYTHONHASHSEED"] = "20260817"

    command = [
        str(python_executable),
        "-u",
        str(runner),
        "--config",
        str(config),
        "--experiments-root",
        str(experiments_root),
        "--run-id",
        run_id,
    ]

    child_pid: int | None = None
    return_code: int | None = None
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
            raise RuntimeError(f"CAPER outcome runner exited with code {return_code}")
        if child_pid is None or child_pid <= 0 or pid_is_running(child_pid):
            raise RuntimeError(f"Launcher child PID is still active: {child_pid}")
        if not run_directory.is_dir():
            raise RuntimeError(f"Runner did not create {run_directory}")

        candidates = sorted(run_directory.glob("RUNNER_COMPLETE_*.json"))
        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected one runner completion candidate, found {len(candidates)}"
            )
        candidate_path = candidates[0]
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        if not isinstance(candidate, Mapping):
            raise RuntimeError("Runner completion candidate is not a JSON object")
        runner_pid, ledger_path, result_path, artifact_hashes = validate_candidate(
            candidate, run_directory, candidate_path
        )

        # A Windows venv executable may be a short-lived shim.  The waited
        # child PID therefore need not equal the interpreter PID recorded by
        # the runner; both must independently be inactive before publication.
        if pid_is_running(runner_pid):
            raise RuntimeError(f"Runner PID is still active after child exit: {runner_pid}")
        lock_path = Path(str(candidate["runner_lock"])).resolve()
        if lock_path.exists():
            raise RuntimeError(f"Runner lock still exists after exit: {lock_path}")

        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(result, Mapping):
            raise RuntimeError("CAPER result is not a JSON object")
        promise_gate = result.get("promise_gate")
        if not isinstance(promise_gate, Mapping) or not isinstance(
            promise_gate.get("passed"), bool
        ):
            raise RuntimeError("CAPER result has no boolean promise_gate.passed")

        existing_external = list(run_directory.glob("EXTERNAL_COMPLETE_*.json"))
        if existing_external:
            raise RuntimeError("An external completion marker already exists")
        execution_hash = str(candidate["execution_fingerprint_sha256"])
        protocol_hash = str(candidate["protocol_sha256"])
        if len(execution_hash) != 64 or len(protocol_hash) != 64:
            raise RuntimeError("Malformed protocol or execution fingerprint SHA-256")
        external_marker = run_directory / (
            "EXTERNAL_COMPLETE_" + execution_hash[:16] + ".json"
        )
        publish_json_exclusive(
            external_marker,
            {
                "schema": "caper-external-completion-v1",
                "verified_utc": utc_now(),
                "python_executable": str(python_executable),
                "launcher_child_pid": child_pid,
                "child_exit_code": return_code,
                "child_process_has_exited": True,
                "runner_pid": runner_pid,
                "runner_process_has_exited": True,
                "windows_shim_pid_mismatch_allowed": True,
                "runner_lock": str(lock_path),
                "runner_lock_released": True,
                "candidate_marker": candidate_path.name,
                "candidate_marker_sha256": sha256_file(candidate_path),
                "verified_candidate_artifact_count": len(artifact_hashes),
                "asynchronous_error_ledger": ledger_path.name,
                "asynchronous_error_ledger_empty": True,
                "asynchronous_error_ledger_sha256": sha256_file(ledger_path),
                "stdout_log": str(stdout_path),
                "stdout_sha256": sha256_file(stdout_path),
                "stderr_log": str(stderr_path),
                "stderr_sha256": sha256_file(stderr_path),
                "result_file": result_path.name,
                "result_sha256": sha256_file(result_path),
                "protocol_sha256": protocol_hash,
                "execution_fingerprint_sha256": execution_hash,
                "promise_gate_passed": bool(promise_gate["passed"]),
            },
        )
        if len(list(run_directory.glob("EXTERNAL_COMPLETE_*.json"))) != 1:
            raise RuntimeError("External marker publication was not singular")
        print(f"EXTERNAL_COMPLETION_MARKER={external_marker}", flush=True)
        print(f"RESULT_FILE={result_path}", flush=True)
        print(
            "PROMISE_GATE_PASSED=" + str(bool(promise_gate["passed"])).lower(),
            flush=True,
        )
        return 0
    except BaseException as exc:
        publish_json_exclusive(
            failure_path,
            {
                "schema": "caper-external-verification-failure-v1",
                "utc": utc_now(),
                "child_pid": child_pid,
                "child_exit_code": return_code,
                "exception_type": type(exc).__name__,
                "exception": str(exc),
                "python_executable": str(python_executable),
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "run_directory": str(run_directory),
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
