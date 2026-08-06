#!/usr/bin/env python3
"""Held-fixed H6 Phase-B outcome runner, exact replay, and deep verifier.

The real-data path is deliberately unreachable without a launcher-issued
authorization that binds the passed Phase-A artifact and result commit.  The
self-test path is synthetic and never opens MIND, H5, or Phase-A artifacts.
"""

from __future__ import annotations

import os

# These assignments intentionally precede every numerical-library import.
for _thread_variable in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import threading
import time
import traceback
import uuid
from array import array
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SEED_TEXT = "20260807"
BOOTSTRAP_SEED = 20_260_807
BOOTSTRAP_REPLICATES = 5_000
NULL_REPLICATES = 100
NULL_BATCH_SIZE = 10
IMPRESSION_BATCH_SIZE = 512
SCORE_TOLERANCE = 1e-12
MINIMUM_CONFIDENCE = 0.90
EXPECTED_NEWS_ROWS = 42_416
EXPECTED_BEHAVIOR_ROWS = 73_152
EXPECTED_ENTITY_EMBEDDING_ROWS = 22_893
EXPECTED_RELATIONS = 1_091
EXPECTED_ELIGIBLE = 64_443
EXPECTED_USERS = 43_374
EXPECTED_CANDIDATES = 2_422_258
EXPECTED_AFFECTED = 35_445
EXPECTED_NEWS_PATTERNS = 812
EXPECTED_CUTOFF = "2019-11-15T23:58:03Z"
PHASE_A_COMMIT = "b1f247abf3185a2eaec8588b358c488af8f78342"
PHASE_A_MANIFEST_SHA256 = "522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5"
PHASE_A_MANIFEST_BYTES = 224_785_295
PHASE_A_RESULT_SHA256 = "B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF"
PHASE_A_COMPLETION_SHA256 = "AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06"
PROTOCOL_SHA256 = "53EAE6D5D19982DD5E6926F563A6D327A5A1AF47DFC5CF58DA4D54D1D61DB0A4"
OUTCOME_RUN_ID = "outcome_run_001"
OUTCOME_REPLAY_ID = "outcome_run_001_replay"
PASS_VERDICT = "ADVANCE_H6_TO_REPLICATION"
KILL_VERDICT = "KILL_H6_OUTCOME_DIRECTION"

EXPECTED_HASHES = {
    "news": "E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822",
    "behaviors": "B6C460E33B1A8693252DED6E626DA7D3CCF78920EEA2EC11889020BB7D8443EF",
    "facts": "13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D",
    "entities": "45B83B0AFCB6C1348080984B1373CE50912219DFE247F48E97F7FB09009595ED",
    "relations": "D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A",
    "entity_embedding": "F1A0818A7C0136DD94F22AC003841C6DCCBAC2287C668B35402BB436EB400FB9",
    "phase_a_manifest": PHASE_A_MANIFEST_SHA256,
    "phase_a_result": PHASE_A_RESULT_SHA256,
    "phase_a_completion": PHASE_A_COMPLETION_SHA256,
}

METADATA_BLOCKLIST_IDS = (
    "P1343", "P1424", "P5008", "P6104", "P7867", "P8744",
    "P9241", "P2354", "P8402", "P10280", "P1889",
)
REMOVED_ANCHOR_IDS = ("Q30", "Q22686")
VIEW_NAMES = (
    "primary_relation_vocabulary",
    "metadata_blocklist",
    "remove_q30_q22686",
)
FIXED_ARM_NAMES = (
    "historical_shared_fact_primary",
    "current_shared_fact_primary",
    "historical_shared_fact_metadata_blocklist",
    "current_shared_fact_metadata_blocklist",
    "historical_shared_fact_remove_q30_q22686",
    "current_shared_fact_remove_q30_q22686",
    "entity_only_frozen_top50",
    "mind_transe_frozen_top50",
)
METRIC_CHANNELS = (
    "ndcg10", "ndcg5", "mrr", "auc", "pair_credit", "pair_total", "pair_tolerance_ties"
)
QID_PATTERN = re.compile(r"^Q[1-9][0-9]*$")
PROPERTY_PATTERN = re.compile(r"^P[1-9][0-9]*$")
FACT_PATTERN = re.compile(r"^(P[1-9][0-9]*)\|(Q[1-9][0-9]*)$")
NEWS_ID_PATTERN = re.compile(r"^N[0-9]+$")
CANDIDATE_PATTERN = re.compile(r"^(N[0-9]+)-([01])$")

SCRIPT_PATH = Path(__file__).resolve()
H6_DIR = SCRIPT_PATH.parent.parent
ROOT = H6_DIR.parents[3]
PROTOCOL_PATH = H6_DIR / "protocol.md"
IMPLEMENTATION_LOCK_PATH = H6_DIR / "phase_b_implementation_lock.md"
LAUNCHER_PATH = SCRIPT_PATH.with_name("run_h6_phase_b_outcome_safe.ps1")
RESULTS_ROOT = H6_DIR / "results"
SELFTEST_ROOT = H6_DIR / "phase_b_selftest_artifacts"
INNER_LOCK_PATH = H6_DIR / "H6_PHASE_B_OUTCOME_RUN_001_INNER.lock"
OUTER_LOCK_PATH = H6_DIR / "H6_PHASE_B_OUTCOME_RUN_001_LAUNCH.lock"
SELFTEST_OUTER_LOCK_PATH = H6_DIR / "H6_PHASE_B_SELFTEST_LAUNCH.lock"
VENV_LAUNCHER_PATH = ROOT / "_bestrec_run/.venv/Scripts/python.exe"
VENV_CONFIG_PATH = ROOT / "_bestrec_run/.venv/pyvenv.cfg"
INPUT_PATHS = {
    "news": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/news.tsv",
    "behaviors": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/behaviors.tsv",
    "entity_embedding": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/entity_embedding.vec",
    "relations": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/relation_embedding.vec",
    "facts": ROOT / "experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/facts.jsonl",
    "entities": ROOT / "experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/entities.csv",
    "phase_a_manifest": H6_DIR / "results/coverage_run_002/cohort_manifest.jsonl",
    "phase_a_result": H6_DIR / "results/coverage_run_002/result.json",
    "phase_a_completion": H6_DIR / "results/coverage_run_002_completion.json",
}

_NP: Any = None
_SPARSE: Any = None
_ASYNC_LEDGER: Path | None = None
_ASYNC_FAILURES: list[dict[str, Any]] = []


def load_numpy() -> Any:
    global _NP
    if _NP is None:
        import numpy as np  # type: ignore
        _NP = np
    return _NP


def load_sparse() -> Any:
    global _SPARSE
    if _SPARSE is None:
        from scipy import sparse  # type: ignore
        _SPARSE = sparse
    return _SPARSE


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def fsync_file(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def rename_no_overwrite(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    last_error: OSError | None = None
    for attempt in range(5):
        if not source.exists():
            raise FileNotFoundError(f"rename source is missing: {source}")
        try:
            os.rename(source, destination)
            return
        except OSError as error:
            if destination.exists():
                raise FileExistsError(f"refusing to overwrite {destination}") from error
            last_error = error
            if os.name != "nt" or getattr(error, "winerror", None) not in {5, 32, 33} or attempt == 4:
                raise
            time.sleep(0.1)
    assert last_error is not None
    raise last_error


def write_exclusive_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".b{uuid.uuid4().hex[:20]}"
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(payload)
            fsync_file(handle)
        rename_no_overwrite(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def write_exclusive_json(path: Path, value: Any) -> None:
    write_exclusive_bytes(path, canonical_bytes(value) + b"\n")


def safe_stage_path(output_id: str) -> Path:
    if output_id not in {OUTCOME_RUN_ID, OUTCOME_REPLAY_ID}:
        raise RuntimeError("unauthorized Phase-B output ID")
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    stage = RESULTS_ROOT / f".{output_id}.tmp.{uuid.uuid4().hex}"
    if stage.parent.resolve() != RESULTS_ROOT.resolve() or re.fullmatch(
        rf"\.{re.escape(output_id)}\.tmp\.[0-9a-f]{{32}}", stage.name
    ) is None:
        raise RuntimeError("unsafe Phase-B stage path")
    return stage


def remove_safe_stage(stage: Path, output_id: str) -> None:
    if not stage.exists():
        return
    if stage.parent.resolve() != RESULTS_ROOT.resolve() or re.fullmatch(
        rf"\.{re.escape(output_id)}\.tmp\.[0-9a-f]{{32}}", stage.name
    ) is None:
        raise RuntimeError("refusing unsafe Phase-B stage cleanup")
    shutil.rmtree(stage)


def install_async_hooks(ledger: Path) -> None:
    global _ASYNC_LEDGER
    if not ledger.is_file() or ledger.stat().st_size != 0:
        raise RuntimeError("asynchronous-error ledger must exist and be empty")
    _ASYNC_LEDGER = ledger

    def record(kind: str, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        row = {
            "kind": kind,
            "exception_type": getattr(exc_type, "__name__", str(exc_type)),
            "exception": str(exc_value),
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        }
        _ASYNC_FAILURES.append(row)
        with ledger.open("ab", buffering=0) as handle:
            handle.write(canonical_bytes(row) + b"\n")
            os.fsync(handle.fileno())

    def thread_hook(args: Any) -> None:
        record("threading.excepthook", args.exc_type, args.exc_value, args.exc_traceback)

    def unraisable_hook(args: Any) -> None:
        exc = args.exc_value if args.exc_value is not None else RuntimeError(str(args.err_msg))
        record("sys.unraisablehook", type(exc), exc, args.exc_traceback)

    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def require_no_async_failures() -> None:
    if _ASYNC_FAILURES:
        raise RuntimeError(f"{len(_ASYNC_FAILURES)} asynchronous/unraisable exception(s) recorded")
    if _ASYNC_LEDGER is not None and _ASYNC_LEDGER.stat().st_size != 0:
        raise RuntimeError("asynchronous-error ledger is nonempty")


def verify_thread_environment() -> None:
    for name in (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    ):
        if os.environ.get(name) != "1":
            raise RuntimeError(f"unbounded numerical thread environment: {name}")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1" or os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("CUDA/Python hash seed environment mismatch")


def verify_python_thread_state() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("H6 Phase B is not executing on MainThread")
    live = [thread for thread in threading.enumerate() if thread.is_alive()]
    if len(live) != 1 or live[0] is not threading.main_thread() or threading.active_count() != 1:
        raise RuntimeError("unexpected live Python thread detected")


def process_is_alive(process_id: int) -> bool:
    if process_id <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(process_id, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    import ctypes
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, process_id)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return ctypes.windll.kernel32.GetLastError() == 5


def assert_outer_lock_held(path: Path, expected_path: Path) -> None:
    if path.resolve() != expected_path.resolve() or not path.is_file():
        raise RuntimeError("outer launcher lock path/availability mismatch")
    if os.name == "nt":
        try:
            handle = path.open("rb")
        except PermissionError:
            return
        else:
            handle.close()
            raise RuntimeError("outer launcher lock is not held share-none")


class InnerLock:
    def __init__(self, release_path: Path, role: str, authorization: Mapping[str, Any]) -> None:
        self.release_path = release_path
        self.role = role
        self.authorization = authorization
        self.fd: int | None = None
        self.retired: dict[str, Any] | None = None
        self.owner: dict[str, Any] | None = None
        launch_directory = Path(str(authorization["launch_directory"])).resolve()
        expected = (launch_directory / f"{role}_inner_lock_released.json").resolve()
        if release_path.resolve() != expected or release_path.parent.resolve() != launch_directory:
            raise RuntimeError("inner-lock release path escaped authorized launch directory")

    def acquire(self) -> None:
        self.owner = {
            "schema_version": "h6_phase_b_inner_lock.v1",
            "mode": "h6-phase-b-outcome-inner-lock",
            "pid": os.getpid(),
            "launcher_pid": int(self.authorization["launcher_pid"]),
            "launch_id": str(self.authorization["launch_id"]),
            "role": str(self.authorization["run_role"]),
            "runner_sha256": str(self.authorization["runner_sha256"]),
            "token_sha256": str(self.authorization["token_sha256"]),
            "created_time_ns": time.time_ns(),
        }
        for attempt in range(2):
            try:
                self.fd = os.open(INNER_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                os.write(self.fd, canonical_bytes(self.owner) + b"\n")
                os.fsync(self.fd)
                return
            except FileExistsError:
                if attempt != 0:
                    raise RuntimeError("inner lock acquisition raced after stale-lock retirement")
                try:
                    existing = json.loads(INNER_LOCK_PATH.read_text(encoding="utf-8"))
                except Exception as error:
                    raise RuntimeError("existing inner lock unreadable; refusing retirement") from error
                if not isinstance(existing, dict) or not isinstance(existing.get("pid"), int):
                    raise RuntimeError("existing inner lock owner is invalid")
                if process_is_alive(int(existing["pid"])):
                    raise RuntimeError(f"active Phase-B inner lock is owned by PID {existing['pid']}")
                retired_path = self.release_path.parent / f"stale_inner_{uuid.uuid4().hex[:20]}.json"
                rename_no_overwrite(INNER_LOCK_PATH, retired_path)
                self.retired = file_record(retired_path)
        raise AssertionError("unreachable inner-lock state")

    def release(self, failed: bool = False) -> dict[str, Any]:
        if self.fd is None or self.owner is None:
            raise RuntimeError("inner lock was not acquired")
        os.close(self.fd)
        self.fd = None
        destination = self.release_path
        if failed:
            destination = destination.with_name(f"inner_fail_{self.role}_{uuid.uuid4().hex[:20]}.json")
        rename_no_overwrite(INNER_LOCK_PATH, destination)
        return file_record(destination)


def verify_authorized_runtime(authorization: Mapping[str, Any]) -> dict[str, Any]:
    base = Path(str(authorization["base_interpreter"])).resolve()
    venv = Path(str(authorization["venv_launcher"])).resolve()
    config = Path(str(authorization["venv_config"])).resolve()
    if (
        SCRIPT_PATH.parent.resolve() != (H6_DIR / "code").resolve()
        or ROOT.resolve() != Path(r"C:\Users\rayxc\Documents\R").resolve()
        or venv != VENV_LAUNCHER_PATH.resolve()
        or config != VENV_CONFIG_PATH.resolve()
    ):
        raise RuntimeError("authorized workspace-venv path mismatch")
    records = {"base_interpreter": file_record(base), "venv_launcher": file_record(venv), "venv_config": file_record(config)}
    for name, record in records.items():
        if record["sha256"] != authorization[f"{name}_sha256"]:
            raise RuntimeError(f"authorized runtime hash mismatch: {name}")
    actual_base = Path(str(getattr(sys, "_base_executable", ""))).resolve()
    if (
        actual_base != base
        or Path(sys.executable).resolve() != venv
        or Path(sys.prefix).resolve() != venv.parent.parent.resolve()
        or Path(sys.base_prefix).resolve() != base.parent.resolve()
    ):
        raise RuntimeError("CPython base/venv identity mismatch")
    return records


def verify_bound_provenance(authorization: Mapping[str, Any]) -> dict[str, Any]:
    records = verify_authorized_runtime(authorization)
    fixed = {
        "runner": (SCRIPT_PATH, "runner_sha256"),
        "launcher": (LAUNCHER_PATH, "launcher_sha256"),
        "protocol": (PROTOCOL_PATH, "protocol_sha256"),
        "implementation_lock": (IMPLEMENTATION_LOCK_PATH, "lock_sha256"),
        "authorization": (Path(str(authorization["authorization_path"])).resolve(), "authorization_sha256"),
    }
    for name, (path, hash_field) in fixed.items():
        record = file_record(path)
        expected = authorization.get(hash_field)
        if name == "authorization":
            # The launcher cannot include a file's hash inside that same file;
            # the child-start/ack chain binds this record instead.
            expected = record["sha256"]
        if record["sha256"] != expected:
            raise RuntimeError(f"authorized provenance hash mismatch: {name}")
        records[name] = record
    return records


def bootstrap_handshake(args: argparse.Namespace) -> dict[str, Any]:
    authorization_path = Path(args.authorization).resolve()
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if not isinstance(authorization, dict):
        raise RuntimeError("launcher authorization is malformed")
    verify_thread_environment()
    verify_python_thread_state()
    runner_hash = sha256_file(SCRIPT_PATH)
    authorization_hash = sha256_file(authorization_path)
    token_hash = sha256_bytes(args.token.encode("utf-8"))
    if (
        authorization.get("mode") != "h6-phase-b-launcher-authorization"
        or authorization.get("action") != args.command
        or authorization.get("token") != args.token
        or authorization.get("token_sha256") != token_hash
        or authorization.get("runner_sha256") != runner_hash
        or Path(str(authorization.get("launcher_path", ""))).resolve() != LAUNCHER_PATH.resolve()
        or Path(str(authorization.get("authorization_path", ""))).resolve() != authorization_path
        or authorization.get("phase_a_commit") != PHASE_A_COMMIT
        or authorization.get("phase_a_commit_tree_result_sha256") != PHASE_A_RESULT_SHA256
    ):
        raise RuntimeError("launcher authorization identity mismatch")
    mapping = {
        "self-test": (("selftest", "synthetic_selftest"),),
        "run": (("primary", OUTCOME_RUN_ID), ("exact_replay", OUTCOME_REPLAY_ID)),
        "verify": (("verifier", "deep_verification"),),
    }
    role_output = (str(authorization.get("run_role", "")), str(authorization.get("output_id", "")))
    if args.command not in mapping or role_output not in mapping[args.command]:
        raise RuntimeError("action/role/output authorization mismatch")
    if args.command == "self-test" and authorization.get("self_test_only") is not True:
        raise RuntimeError("self-test authorization is not explicitly synthetic-only")
    launch_directory = Path(str(authorization.get("launch_directory", ""))).resolve()
    if args.command == "self-test":
        expected_parent, prefix, outer = SELFTEST_ROOT.resolve(), "bst_", SELFTEST_OUTER_LOCK_PATH
    else:
        expected_parent, prefix, outer = RESULTS_ROOT.resolve(), "b1_", OUTER_LOCK_PATH
    if (
        launch_directory.parent != expected_parent
        or re.fullmatch(re.escape(prefix) + r"[0-9a-f]{20}", launch_directory.name) is None
        or authorization_path.parent != launch_directory
    ):
        raise RuntimeError("launcher artifact containment mismatch")
    artifact_fields = ("async_error_ledger", "process_start_path", "process_ack_path")
    for field in artifact_fields:
        if Path(str(authorization.get(field, ""))).resolve().parent != launch_directory:
            raise RuntimeError(f"authorized child artifact escaped launch directory: {field}")
    label = role_output[0]
    exact_names = {
        "authorization_path": f"{label}_authorization.json",
        "async_error_ledger": f"{label}_async_errors.jsonl",
        "process_start_path": f"{label}_process_start.json",
        "process_ack_path": f"{label}_process_ack.json",
    }
    resolved_artifacts = []
    for field, expected_name in exact_names.items():
        candidate = Path(str(authorization.get(field, ""))).resolve()
        if candidate.parent != launch_directory or candidate.name != expected_name:
            raise RuntimeError(f"authorized artifact filename mismatch: {field}")
        resolved_artifacts.append(candidate)
    if len(set(resolved_artifacts)) != len(resolved_artifacts):
        raise RuntimeError("authorized child artifact paths are not distinct")
    if args.command == "run":
        expected_release = launch_directory / f"{role_output[0]}_inner_lock_released.json"
        if Path(str(authorization.get("inner_lock_release_path", ""))).resolve() != expected_release.resolve():
            raise RuntimeError("inner-lock release authorization mismatch")
    start_path = Path(args.process_start).resolve()
    ack_path = Path(args.process_ack).resolve()
    if (
        start_path != Path(str(authorization["process_start_path"])).resolve()
        or ack_path != Path(str(authorization["process_ack_path"])).resolve()
    ):
        raise RuntimeError("PID-handshake path mismatch")
    launcher_pid = int(authorization.get("launcher_pid", -1))
    if launcher_pid <= 0 or not process_is_alive(launcher_pid):
        raise RuntimeError("authorized launcher PID is not alive")
    assert_outer_lock_held(Path(str(authorization.get("outer_lock", ""))).resolve(), outer)
    runtime_records = verify_bound_provenance(authorization)
    if sha256_file(LAUNCHER_PATH) != authorization.get("launcher_sha256"):
        raise RuntimeError("authorized launcher hash mismatch")
    if sha256_file(IMPLEMENTATION_LOCK_PATH) != authorization.get("lock_sha256"):
        raise RuntimeError("authorized implementation-lock hash mismatch")
    if sha256_file(PROTOCOL_PATH) != authorization.get("protocol_sha256"):
        raise RuntimeError("authorized protocol hash mismatch")
    record = {
        "mode": "h6-phase-b-child-process-start",
        "action": args.command,
        "run_role": role_output[0],
        "output_id": role_output[1],
        "launch_id": authorization["launch_id"],
        "launcher_pid": launcher_pid,
        "process_pid": os.getpid(),
        "authorization_sha256": authorization_hash,
        "token_sha256": token_hash,
        "runner_sha256": runner_hash,
        "environment": {
            "sys_executable": str(Path(sys.executable).resolve()),
            "sys_base_executable": str(Path(str(getattr(sys, "_base_executable", ""))).resolve()),
            "sys_prefix": str(Path(sys.prefix).resolve()),
            "sys_base_prefix": str(Path(sys.base_prefix).resolve()),
            "main_thread_only": True,
            "runtime_files": runtime_records,
            "thread_bounds": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
                )
            },
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        },
    }
    write_exclusive_json(start_path, record)
    deadline = time.monotonic() + 30.0
    while not ack_path.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError("launcher PID acknowledgement timed out")
        time.sleep(0.05)
    acknowledgement = json.loads(ack_path.read_text(encoding="utf-8"))
    if (
        acknowledgement.get("mode") != "h6-phase-b-child-process-acknowledgement"
        or acknowledgement.get("action") != args.command
        or acknowledgement.get("launch_id") != authorization["launch_id"]
        or int(acknowledgement.get("process_pid", -1)) != os.getpid()
        or acknowledgement.get("authorization_sha256") != authorization_hash
        or acknowledgement.get("token_sha256") != token_hash
    ):
        raise RuntimeError("launcher PID acknowledgement mismatch")
    if not process_is_alive(launcher_pid):
        raise RuntimeError("launcher exited during handshake")
    assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), outer)
    verify_python_thread_state()
    return authorization


def verify_real_input_hashes() -> dict[str, str]:
    observed: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = INPUT_PATHS[name]
        if not path.is_file():
            raise RuntimeError(f"missing immutable input: {name}")
        observed[name] = sha256_file(path)
        if observed[name] != expected:
            raise RuntimeError(f"immutable input hash mismatch: {name}")
    if INPUT_PATHS["phase_a_manifest"].stat().st_size != PHASE_A_MANIFEST_BYTES:
        raise RuntimeError("Phase-A manifest byte count mismatch")
    if sha256_file(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise RuntimeError("locked protocol hash mismatch")
    return observed


def load_phase_a_contract() -> tuple[dict[str, Any], list[str]]:
    result = json.loads(INPUT_PATHS["phase_a_result"].read_text(encoding="utf-8"))
    completion = json.loads(INPUT_PATHS["phase_a_completion"].read_text(encoding="utf-8"))
    if result.get("schema_version") != "h6_phase_a_coverage.python.v1":
        raise RuntimeError("Phase-A result schema mismatch")
    if result.get("decision", {}).get("verdict") != "PASS_COVERAGE_AND_OPEN_LABELS":
        raise RuntimeError("Phase A did not authorize label opening")
    cohort = result.get("cohort", {})
    if (
        cohort.get("manifest_sha256") != PHASE_A_MANIFEST_SHA256
        or cohort.get("eligible_impressions") != EXPECTED_ELIGIBLE
        or cohort.get("distinct_users") != EXPECTED_USERS
        or cohort.get("candidates") != EXPECTED_CANDIDATES
        or cohort.get("manifest_contains_candidate_suffix") is not False
    ):
        raise RuntimeError("Phase-A cohort contract mismatch")
    qids = cohort.get("sampled_qids")
    if not isinstance(qids, list) or len(qids) != 50 or len(set(qids)) != 50:
        raise RuntimeError("Phase-A anchor sample mismatch")
    if any(not isinstance(qid, str) or QID_PATTERN.fullmatch(qid) is None for qid in qids):
        raise RuntimeError("Phase-A anchor identifier is invalid")
    outputs = completion.get("outputs", {})
    if (
        completion.get("status") != "H6_COVERAGE_RUN_002_COMPLETE"
        or completion.get("decision", {}).get("verdict") != "PASS_COVERAGE_AND_OPEN_LABELS"
        or outputs.get("primary_manifest", {}).get("sha256") != PHASE_A_MANIFEST_SHA256
        or outputs.get("primary_result", {}).get("sha256") != PHASE_A_RESULT_SHA256
        or completion.get("completion_marker_is_last") is not True
    ):
        raise RuntimeError("Phase-A completion chain mismatch")
    return result, qids


def load_entity_embeddings(anchor_qids: Sequence[str]) -> tuple[Any, dict[str, Any]]:
    np = load_numpy()
    wanted = set(anchor_qids)
    found: dict[str, Any] = {}
    seen: set[str] = set()
    rows = 0
    dimension: int | None = None
    with INPUT_PATHS["entity_embedding"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            fields = raw_line.rstrip("\r\n").split("\t")
            if fields and fields[-1] == "":
                fields.pop()
            if len(fields) < 2:
                raise RuntimeError("entity embedding row is malformed")
            qid = fields[0]
            if QID_PATTERN.fullmatch(qid) is None or qid in seen:
                raise RuntimeError("entity embedding has invalid or duplicate QID")
            seen.add(qid)
            try:
                vector = np.asarray([float(value) for value in fields[1:]], dtype=np.float64)
            except ValueError as error:
                raise RuntimeError("entity embedding contains a nonnumeric value") from error
            if dimension is None:
                dimension = int(vector.size)
            if vector.size != dimension or dimension != 100 or not np.all(np.isfinite(vector)):
                raise RuntimeError("entity embedding dimension/finite check failed")
            if qid in wanted:
                found[qid] = vector
            rows += 1
    if rows != EXPECTED_ENTITY_EMBEDDING_ROWS or len(seen) != rows:
        raise RuntimeError("entity embedding row-count check failed")
    if set(found) != wanted:
        raise RuntimeError("not all frozen anchors have MIND TransE rows")
    matrix = np.stack([found[qid] for qid in anchor_qids], axis=0)
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms <= 0.0) or not np.all(np.isfinite(norms)):
        raise RuntimeError("frozen TransE anchor row has invalid norm")
    report = {
        "rows": rows,
        "dimension": int(matrix.shape[1]),
        "frozen_anchor_coverage": len(found),
        "frozen_anchor_total": len(anchor_qids),
        "raw_row_l2_norm": {
            "minimum": float(np.min(norms)),
            "maximum": float(np.max(norms)),
            "mean": float(np.mean(norms)),
        },
        "per_entity_normalization_applied": False,
    }
    return matrix, report


def load_relations_and_facts(anchor_qids: Sequence[str]) -> tuple[list[set[str]], list[set[str]], set[str]]:
    anchor_set = set(anchor_qids)
    relations: set[str] = set()
    with INPUT_PATHS["relations"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            property_id = raw_line.split("\t", 1)[0]
            if PROPERTY_PATTERN.fullmatch(property_id) is None or property_id in relations:
                raise RuntimeError("relation vocabulary has invalid or duplicate property")
            relations.add(property_id)
    if len(relations) != EXPECTED_RELATIONS:
        raise RuntimeError("relation vocabulary cardinality mismatch")

    rows: dict[str, tuple[set[str], set[str]]] = {}
    with INPUT_PATHS["facts"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            qid = str(row.get("qid", ""))
            if qid in rows or qid not in anchor_set or row.get("api_ok") is not True:
                raise RuntimeError("H5 fact ledger identity mismatch")
            snapshots: list[set[str]] = []
            for snapshot in ("historical", "current"):
                source = row.get(snapshot, {}).get("facts")
                if not isinstance(source, list) or len(source) != len(set(source)):
                    raise RuntimeError("H5 fact list malformed or duplicated")
                retained: set[str] = set()
                for value in source:
                    match = FACT_PATTERN.fullmatch(str(value))
                    if match is None:
                        raise RuntimeError("H5 fact signature is invalid")
                    if match.group(1) in relations:
                        retained.add(str(value))
                snapshots.append(retained)
            rows[qid] = (snapshots[0], snapshots[1])
    if set(rows) != anchor_set:
        raise RuntimeError("H5 fact ledger does not reproduce frozen anchors")

    with INPUT_PATHS["entities"].open("r", encoding="utf-8-sig", newline="") as handle:
        entity_rows = list(csv.DictReader(handle))
    entity_qids = [str(row.get("qid", "")) for row in entity_rows]
    if (
        len(entity_rows) != 50
        or set(entity_qids) != anchor_set
        or len(set(entity_qids)) != 50
        or any(row.get("api_ok") != "True" for row in entity_rows)
    ):
        raise RuntimeError("H5 entity summary does not reproduce frozen anchors")
    historical = [rows[qid][0] for qid in anchor_qids]
    current = [rows[qid][1] for qid in anchor_qids]
    return historical, current, relations


@dataclass
class NewsData:
    ids: list[str]
    index: dict[str, int]
    pattern_index: Any
    pattern_matrix: Any


def parse_news(anchor_qids: Sequence[str]) -> NewsData:
    np = load_numpy()
    anchor_index = {qid: index for index, qid in enumerate(anchor_qids)}
    ids: list[str] = []
    index: dict[str, int] = {}
    pattern_map: dict[tuple[int, ...], int] = {}
    pattern_rows: list[tuple[int, ...]] = []
    pattern_index = np.empty(EXPECTED_NEWS_ROWS, dtype=np.int32)
    with INPUT_PATHS["news"].open("r", encoding="utf-8", newline="") as handle:
        for row_number, raw_line in enumerate(handle):
            if row_number >= EXPECTED_NEWS_ROWS:
                raise RuntimeError("news input exceeds locked row count")
            fields = raw_line.rstrip("\r\n").split("\t", 7)
            if len(fields) != 8:
                raise RuntimeError("news row does not have exactly eight fields")
            news_id = fields[0]
            if NEWS_ID_PATTERN.fullmatch(news_id) is None or news_id in index:
                raise RuntimeError("news input has invalid or duplicate news ID")
            retained: set[int] = set()
            for column in (6, 7):
                try:
                    annotations = json.loads(fields[column])
                except json.JSONDecodeError as error:
                    raise RuntimeError("news annotation JSON is invalid") from error
                if not isinstance(annotations, list):
                    raise RuntimeError("news annotation JSON is not an array")
                for annotation in annotations:
                    if not isinstance(annotation, dict):
                        continue
                    qid = str(annotation.get("WikidataId", "")).strip()
                    try:
                        confidence = float(annotation.get("Confidence"))
                    except (TypeError, ValueError):
                        continue
                    if qid in anchor_index and math.isfinite(confidence) and confidence >= MINIMUM_CONFIDENCE:
                        retained.add(anchor_index[qid])
            pattern = tuple(sorted(retained))
            if pattern not in pattern_map:
                pattern_map[pattern] = len(pattern_rows)
                pattern_rows.append(pattern)
            pattern_index[row_number] = pattern_map[pattern]
            index[news_id] = row_number
            ids.append(news_id)
    if len(ids) != EXPECTED_NEWS_ROWS:
        raise RuntimeError("news row-count reproduction failed")
    patterns = np.zeros((len(pattern_rows), 50), dtype=np.float64)
    if len(pattern_rows) != EXPECTED_NEWS_PATTERNS:
        raise RuntimeError("top-50 news-incidence pattern count differs from label-blind audit")
    for pattern_id, pattern in enumerate(pattern_rows):
        if pattern:
            patterns[pattern_id, list(pattern)] = 1.0
    return NewsData(ids, index, pattern_index, patterns)


@dataclass
class Cohort:
    impression_ids: list[str]
    user_ids: list[str]
    user_index: Any
    history_offsets: Any
    history_news: Any
    candidate_offsets: Any
    candidate_news: Any
    labels: Any
    positive_counts: Any
    shared_scores: Any
    shared_ranks: Any
    affected: Any


def parse_behavior_time(value: str) -> datetime:
    return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=timezone.utc)


def parse_committed_cohort(news: NewsData) -> Cohort:
    np = load_numpy()
    user_index = np.empty(EXPECTED_ELIGIBLE, dtype=np.int32)
    candidate_offsets = np.zeros(EXPECTED_ELIGIBLE + 1, dtype=np.int64)
    candidate_news = np.empty(EXPECTED_CANDIDATES, dtype=np.int32)
    labels = np.empty(EXPECTED_CANDIDATES, dtype=np.uint8)
    positive_counts = np.empty(EXPECTED_ELIGIBLE, dtype=np.int32)
    shared_scores = np.empty((6, EXPECTED_CANDIDATES), dtype=np.float64)
    shared_ranks = np.empty((6, EXPECTED_CANDIDATES), dtype=np.uint16)
    history_offsets = np.zeros(EXPECTED_ELIGIBLE + 1, dtype=np.int64)
    history_news_buffer = array("I")
    impression_ids: list[str] = []
    users: list[str] = []
    user_map: dict[str, int] = {}
    seen_impressions: set[str] = set()
    behavior_rows = 0
    eligible = 0
    candidate_cursor = 0
    maximum_time = datetime.min.replace(tzinfo=timezone.utc)
    pattern_has_anchor = np.any(news.pattern_matrix != 0.0, axis=1)
    has_anchor = pattern_has_anchor[news.pattern_index]

    with INPUT_PATHS["behaviors"].open("r", encoding="utf-8", newline="") as behavior_handle, INPUT_PATHS[
        "phase_a_manifest"
    ].open("r", encoding="utf-8", newline="") as manifest_handle:
        for raw_line in behavior_handle:
            behavior_rows += 1
            fields = raw_line.rstrip("\r\n").split("\t", 4)
            if len(fields) != 5:
                raise RuntimeError("behavior row does not have exactly five fields")
            impression_id, user_id = fields[0], fields[1]
            if not impression_id.strip() or not user_id.strip() or impression_id in seen_impressions:
                raise RuntimeError("behavior input has missing/duplicate impression or user")
            seen_impressions.add(impression_id)
            maximum_time = max(maximum_time, parse_behavior_time(fields[2]))
            history_ids = fields[3].split() if fields[3].strip() else []
            if any(NEWS_ID_PATTERN.fullmatch(value) is None or value not in news.index for value in history_ids):
                raise RuntimeError("unknown or malformed history news ID")
            tokens = fields[4].split()
            if not tokens:
                raise RuntimeError("impression has no candidate tokens")
            matches = [CANDIDATE_PATTERN.fullmatch(token) for token in tokens]
            if any(match is None for match in matches):
                raise RuntimeError("malformed candidate token")
            candidate_ids = [match.group(1) for match in matches if match is not None]
            if len(candidate_ids) != len(set(candidate_ids)):
                raise RuntimeError("duplicate candidate news ID")
            if any(value not in news.index for value in candidate_ids):
                raise RuntimeError("unknown candidate news ID")
            retained_history = history_ids[-50:]
            retained_indices = [news.index[value] for value in retained_history]
            if len(candidate_ids) < 2 or not retained_indices or not bool(np.any(has_anchor[retained_indices])):
                continue

            manifest_line = manifest_handle.readline()
            if not manifest_line:
                raise RuntimeError("Phase-A manifest ended before fixed cohort")
            record = json.loads(manifest_line)
            if list(record) != ["i", "u", "h", "c"]:
                raise RuntimeError("Phase-A manifest top-level schema/order mismatch")
            if record["i"] != impression_id or record["u"] != user_id or record["h"] != retained_history:
                raise RuntimeError("behavior row does not match committed manifest")
            expected_ids = sorted(candidate_ids)
            manifest_candidates = record["c"]
            if not isinstance(manifest_candidates, list) or [item.get("n") for item in manifest_candidates] != expected_ids:
                raise RuntimeError("candidate set/order differs from committed manifest")
            label_by_news = {
                match.group(1): int(match.group(2)) for match in matches if match is not None
            }
            if eligible >= EXPECTED_ELIGIBLE or candidate_cursor + len(expected_ids) > EXPECTED_CANDIDATES:
                raise RuntimeError("cohort exceeds Phase-A dimensions")
            if user_id not in user_map:
                user_map[user_id] = len(users)
                users.append(user_id)
            user_index[eligible] = user_map[user_id]
            impression_ids.append(impression_id)
            history_news_buffer.extend(retained_indices)
            history_offsets[eligible + 1] = len(history_news_buffer)
            start = candidate_cursor
            for local, item in enumerate(manifest_candidates):
                if list(item) != ["n", "v"] or not isinstance(item["v"], list) or len(item["v"]) != 3:
                    raise RuntimeError("Phase-A candidate schema mismatch")
                position = start + local
                candidate_news[position] = news.index[item["n"]]
                labels[position] = label_by_news[item["n"]]
                for view_index, values in enumerate(item["v"]):
                    if not isinstance(values, list) or len(values) != 4:
                        raise RuntimeError("Phase-A view tuple mismatch")
                    historical_score, current_score = float(values[0]), float(values[1])
                    historical_rank, current_rank = int(values[2]), int(values[3])
                    if not math.isfinite(historical_score) or not math.isfinite(current_score):
                        raise RuntimeError("Phase-A manifest has nonfinite score")
                    shared_scores[2 * view_index, position] = historical_score
                    shared_scores[2 * view_index + 1, position] = current_score
                    shared_ranks[2 * view_index, position] = historical_rank
                    shared_ranks[2 * view_index + 1, position] = current_rank
            stop = start + len(expected_ids)
            for arm in range(6):
                observed = sorted(int(value) for value in shared_ranks[arm, start:stop])
                if observed != list(range(1, stop - start + 1)):
                    raise RuntimeError("Phase-A rank vector is not a permutation")
            positive_counts[eligible] = int(np.sum(labels[start:stop]))
            candidate_cursor = stop
            candidate_offsets[eligible + 1] = candidate_cursor
            eligible += 1
        if manifest_handle.readline() != "":
            raise RuntimeError("Phase-A manifest has extra rows")

    if (
        behavior_rows != EXPECTED_BEHAVIOR_ROWS
        or len(seen_impressions) != EXPECTED_BEHAVIOR_ROWS
        or eligible != EXPECTED_ELIGIBLE
        or len(users) != EXPECTED_USERS
        or candidate_cursor != EXPECTED_CANDIDATES
        or maximum_time.strftime("%Y-%m-%dT%H:%M:%SZ") != EXPECTED_CUTOFF
    ):
        raise RuntimeError("held-fixed cohort cardinality/cutoff mismatch")
    history_news = np.frombuffer(history_news_buffer, dtype=np.uint32).astype(np.int32, copy=True)
    affected = np.zeros(EXPECTED_ELIGIBLE, dtype=np.bool_)
    for impression in range(EXPECTED_ELIGIBLE):
        start, stop = int(candidate_offsets[impression]), int(candidate_offsets[impression + 1])
        affected[impression] = bool(np.any(shared_ranks[0, start:stop] != shared_ranks[1, start:stop]))
    if int(np.count_nonzero(affected)) != EXPECTED_AFFECTED:
        raise RuntimeError("primary rank-affected subset differs from committed Phase A")
    return Cohort(
        impression_ids, users, user_index, history_offsets, history_news,
        candidate_offsets, candidate_news, labels, positive_counts,
        shared_scores, shared_ranks, affected,
    )


@dataclass
class ScoringIndex:
    history_pattern_counts: Any
    candidate_patterns: list[Any]
    candidate_inverse: list[Any]
    tie_orders: list[Any]


def build_scoring_index(news: NewsData, cohort: Cohort) -> ScoringIndex:
    np = load_numpy()
    sparse = load_sparse()
    row_indices: list[int] = []
    column_indices: list[int] = []
    values: list[float] = []
    candidate_patterns: list[Any] = []
    candidate_inverse: list[Any] = []
    tie_orders: list[Any] = []
    for impression in range(EXPECTED_ELIGIBLE):
        hs, he = int(cohort.history_offsets[impression]), int(cohort.history_offsets[impression + 1])
        patterns = news.pattern_index[cohort.history_news[hs:he]]
        unique, counts = np.unique(patterns, return_counts=True)
        nonempty = np.any(news.pattern_matrix[unique] != 0.0, axis=1)
        for pattern, count in zip(unique[nonempty], counts[nonempty], strict=True):
            row_indices.append(impression)
            column_indices.append(int(pattern))
            values.append(float(count))

        cs, ce = int(cohort.candidate_offsets[impression]), int(cohort.candidate_offsets[impression + 1])
        local_patterns = news.pattern_index[cohort.candidate_news[cs:ce]]
        candidate_unique, inverse = np.unique(local_patterns, return_inverse=True)
        candidate_patterns.append(candidate_unique.astype(np.int32, copy=False))
        candidate_inverse.append(inverse.astype(np.int32, copy=False))
        local_news_ids = [news.ids[int(news_index)] for news_index in cohort.candidate_news[cs:ce]]
        tie_hashes = [
            hashlib.sha256(
                f"{SEED_TEXT}|{cohort.impression_ids[impression]}|{news_id}".encode("utf-8")
            ).digest()
            for news_id in local_news_ids
        ]
        tie_orders.append(
            np.asarray(
                sorted(range(ce - cs), key=lambda item: (tie_hashes[item], local_news_ids[item])),
                dtype=np.int32,
            )
        )
    history = sparse.csr_matrix(
        (np.asarray(values, dtype=np.float64), (row_indices, column_indices)),
        shape=(EXPECTED_ELIGIBLE, int(news.pattern_matrix.shape[0])),
        dtype=np.float64,
    )
    history.sum_duplicates()
    history.sort_indices()
    if history.nnz == 0 or not np.all(np.isfinite(history.data)):
        raise RuntimeError("history-pattern index is empty or nonfinite")
    return ScoringIndex(history, candidate_patterns, candidate_inverse, tie_orders)


def gram_from_fact_sets(fact_sets: Sequence[set[str]]) -> Any:
    np = load_numpy()
    count = len(fact_sets)
    gram = np.zeros((count, count), dtype=np.float64)
    degrees = np.asarray([len(values) for values in fact_sets], dtype=np.float64)
    for first in range(count):
        if degrees[first] == 0:
            continue
        gram[first, first] = 1.0
        for second in range(first + 1, count):
            if degrees[second] == 0:
                continue
            shared = len(fact_sets[first].intersection(fact_sets[second]))
            value = shared / math.sqrt(float(degrees[first] * degrees[second]))
            gram[first, second] = value
            gram[second, first] = value
    return gram


def pattern_similarity_from_grams(grams: Any, pattern_matrix: Any) -> Any:
    np = load_numpy()
    source = np.asarray(grams, dtype=np.float64)
    if source.ndim == 2:
        source = source[None, :, :]
    if source.ndim != 3 or source.shape[1:] != (50, 50):
        raise RuntimeError("anchor Gram batch has invalid shape")
    batch = source.shape[0]
    patterns = np.asarray(pattern_matrix, dtype=np.float64)
    active = patterns[None, :, :] * (np.diagonal(source, axis1=1, axis2=2) > 0.0)[:, None, :]
    norm_squared = np.einsum("bpa,bac,bpc->bp", active, source, active, optimize=True)
    if not np.all(np.isfinite(norm_squared)) or np.any(norm_squared < -SCORE_TOLERANCE):
        raise RuntimeError("pattern squared norm is invalid")
    coefficients = np.zeros((batch, patterns.shape[0], 50), dtype=np.float64)
    nonzero = norm_squared > 0.0
    coefficients[nonzero] = active[nonzero] / np.sqrt(norm_squared[nonzero, None])
    similarity = np.einsum("bpa,bac,bqc->bpq", coefficients, source, coefficients, optimize=True)
    if not np.all(np.isfinite(similarity)):
        raise RuntimeError("pattern similarity contains nonfinite value")
    similarity[np.abs(similarity) < np.finfo(np.float64).tiny] = 0.0
    return similarity


def pattern_similarity_from_features(anchor_features: Any, pattern_matrix: Any) -> Any:
    np = load_numpy()
    raw = np.asarray(pattern_matrix, dtype=np.float64) @ np.asarray(anchor_features, dtype=np.float64)
    norm = np.linalg.norm(raw, axis=1)
    normalized = np.zeros_like(raw)
    nonzero = norm > 0.0
    normalized[nonzero] = raw[nonzero] / norm[nonzero, None]
    similarity = normalized @ normalized.T
    if not np.all(np.isfinite(similarity)):
        raise RuntimeError("feature-pattern similarity contains nonfinite value")
    return similarity[None, :, :]


def score_similarity_batch(similarities: Any, scoring: ScoringIndex, cohort: Cohort) -> list[Any]:
    """Score only distinct candidate patterns using sparse history-pattern counts."""
    np = load_numpy()
    source = np.asarray(similarities, dtype=np.float64)
    if source.ndim != 3 or source.shape[1] != source.shape[2]:
        raise RuntimeError("pattern similarity batch has invalid shape")
    batch = int(source.shape[0])
    impressions = len(cohort.impression_ids)
    candidates_total = int(cohort.candidate_offsets[-1])
    outputs = [np.empty(candidates_total, dtype=np.float64) for _ in range(batch)]
    history = scoring.history_pattern_counts
    for impression in range(impressions):
        hs, he = int(history.indptr[impression]), int(history.indptr[impression + 1])
        history_patterns = history.indices[hs:he]
        history_counts = history.data[hs:he]
        candidates = scoring.candidate_patterns[impression]
        inverse = scoring.candidate_inverse[impression]
        cs, ce = int(cohort.candidate_offsets[impression]), int(cohort.candidate_offsets[impression + 1])
        if history_patterns.size == 0:
            for arm in outputs:
                arm[cs:ce] = 0.0
            continue
        block = source[:, history_patterns, :][:, :, candidates]
        numerators = np.einsum("j,bjk->bk", history_counts, block, optimize=True)
        history_block = source[:, history_patterns, :][:, :, history_patterns]
        norm_squared = np.einsum("j,bjk,k->b", history_counts, history_block, history_counts, optimize=True)
        if not np.all(np.isfinite(norm_squared)) or np.any(norm_squared < -SCORE_TOLERANCE):
            raise RuntimeError("pattern user squared norm is invalid")
        denominators = np.sqrt(np.maximum(norm_squared, 0.0))
        for batch_index in range(batch):
            if denominators[batch_index] > 0.0:
                outputs[batch_index][cs:ce] = numerators[batch_index, inverse] / denominators[batch_index]
            else:
                outputs[batch_index][cs:ce] = 0.0
    if any(not np.all(np.isfinite(values)) for values in outputs):
        raise RuntimeError("pattern scorer produced nonfinite score")
    return outputs


def frozen_tolerance_groups(scores: Sequence[float]) -> list[list[int]]:
    buckets: dict[float, list[int]] = defaultdict(list)
    for index, value in enumerate(scores):
        buckets[float(value)].append(index)
    groups: list[list[int]] = []
    pending: list[int] = []
    reference: float | None = None
    for score in sorted(buckets, reverse=True):
        if reference is None:
            reference = score
        elif abs(reference - score) > SCORE_TOLERANCE:
            groups.append(pending)
            pending = []
            reference = score
        pending.extend(buckets[score])
    if pending:
        groups.append(pending)
    return groups


def frozen_order(scores: Sequence[float], tie_order: Any) -> list[int]:
    tie_rank = {int(candidate): rank for rank, candidate in enumerate(tie_order.tolist())}
    order: list[int] = []
    for group in frozen_tolerance_groups(scores):
        group.sort(key=lambda candidate: tie_rank[candidate])
        order.extend(group)
    return order


def metric_vector(scores: Any, labels: Any, tie_order: Any) -> tuple[Any, list[int]]:
    np = load_numpy()
    values = np.asarray(scores, dtype=np.float64)
    outcomes = np.asarray(labels, dtype=np.uint8)
    if values.ndim != 1 or outcomes.shape != values.shape or not np.all(np.isfinite(values)):
        raise RuntimeError("metric input shape/finite mismatch")
    if np.any((outcomes != 0) & (outcomes != 1)):
        raise RuntimeError("metric labels are not binary")
    order = frozen_order(values.tolist(), tie_order)
    ordered = outcomes[order]
    positives = int(np.sum(outcomes))
    discounts10 = 1.0 / np.log2(np.arange(2, min(10, values.size) + 2, dtype=np.float64))
    discounts5 = 1.0 / np.log2(np.arange(2, min(5, values.size) + 2, dtype=np.float64))
    ideal10 = float(np.sum(discounts10[: min(positives, discounts10.size)]))
    ideal5 = float(np.sum(discounts5[: min(positives, discounts5.size)]))
    ndcg10 = float(np.sum(ordered[: discounts10.size] * discounts10) / ideal10) if ideal10 > 0.0 else 0.0
    ndcg5 = float(np.sum(ordered[: discounts5.size] * discounts5) / ideal5) if ideal5 > 0.0 else 0.0
    positive_positions = np.flatnonzero(ordered)
    mrr = 1.0 / float(positive_positions[0] + 1) if positive_positions.size else 0.0
    positive_scores = values[outcomes == 1]
    negative_scores = values[outcomes == 0]
    pair_total = int(positive_scores.size * negative_scores.size)
    if pair_total:
        groups = frozen_tolerance_groups(values.tolist())
        group_id = np.empty(values.size, dtype=np.int32)
        for group_number, group in enumerate(groups):
            group_id[np.asarray(group, dtype=np.int32)] = group_number
        positive_groups = group_id[outcomes == 1]
        negative_groups = group_id[outcomes == 0]
        auc_credit = float(np.count_nonzero(positive_groups[:, None] < negative_groups[None, :]))
        tolerance_ties = int(np.count_nonzero(positive_groups[:, None] == negative_groups[None, :]))
        auc_credit += 0.5 * float(tolerance_ties)
        auc = auc_credit / pair_total
        ranks = np.empty(values.size, dtype=np.int32)
        ranks[np.asarray(order, dtype=np.int32)] = np.arange(values.size, dtype=np.int32)
        positive_ranks = ranks[outcomes == 1]
        negative_ranks = ranks[outcomes == 0]
        credit = float(np.count_nonzero(positive_ranks[:, None] < negative_ranks[None, :]))
    else:
        credit = 0.0
        tolerance_ties = 0
        auc = float("nan")
    return np.asarray(
        (ndcg10, ndcg5, mrr, auc, credit, float(pair_total), float(tolerance_ties)), dtype=np.float64
    ), order


def metrics_from_score_arms(
    score_arms: Sequence[Any], scoring: ScoringIndex, cohort: Cohort, verify_shared_ranks: bool = False
) -> Any:
    np = load_numpy()
    impressions = len(cohort.impression_ids)
    metrics = np.empty((len(score_arms), impressions, len(METRIC_CHANNELS)), dtype=np.float64)
    for impression in range(impressions):
        start, stop = int(cohort.candidate_offsets[impression]), int(cohort.candidate_offsets[impression + 1])
        local_labels = cohort.labels[start:stop]
        tie_order = scoring.tie_orders[impression]
        for arm, scores in enumerate(score_arms):
            metrics[arm, impression], order = metric_vector(scores[start:stop], local_labels, tie_order)
            if verify_shared_ranks and arm < 6:
                expected_order = np.argsort(cohort.shared_ranks[arm, start:stop], kind="stable").tolist()
                if order != expected_order:
                    raise RuntimeError("reconstructed shared-fact rank differs from committed manifest")
    return metrics


def relation_stratified_null_grams(
    anchor_qids: Sequence[str], historical: Sequence[set[str]], current: Sequence[set[str]]
) -> tuple[Any, dict[str, Any]]:
    np = load_numpy()
    historical_by_property: list[dict[str, set[str]]] = []
    union_by_property: list[dict[str, set[str]]] = []
    for historical_facts, current_facts in zip(historical, current, strict=True):
        h: dict[str, set[str]] = defaultdict(set)
        union: dict[str, set[str]] = defaultdict(set)
        for fact in historical_facts:
            property_id, target = fact.split("|", 1)
            h[property_id].add(target)
            union[property_id].add(target)
        for fact in current_facts:
            property_id, target = fact.split("|", 1)
            union[property_id].add(target)
        historical_by_property.append(h)
        union_by_property.append(union)
    grams = np.empty((NULL_REPLICATES, 50, 50), dtype=np.float64)
    graph_hashes: list[str] = []
    for replicate in range(NULL_REPLICATES):
        fact_sets: list[set[str]] = []
        digest = hashlib.sha256()
        for anchor_index, qid in enumerate(anchor_qids):
            sampled: set[str] = set()
            for property_id in sorted(historical_by_property[anchor_index]):
                count = len(historical_by_property[anchor_index][property_id])
                candidates = sorted(union_by_property[anchor_index][property_id])
                seed = hashlib.sha256(f"{SEED_TEXT}|{replicate}|{qid}|{property_id}".encode("utf-8")).digest()
                ordered = sorted(
                    candidates,
                    key=lambda target: (hashlib.sha256(seed + b"|" + target.encode("utf-8")).digest(), target),
                )
                if count > len(ordered):
                    raise RuntimeError("null stratum cannot preserve historical degree")
                sampled.update(f"{property_id}|{target}" for target in ordered[:count])
            if len(sampled) != len(historical[anchor_index]):
                raise RuntimeError("null graph failed total source-degree preservation")
            for fact in sorted(sampled):
                digest.update(qid.encode("utf-8") + b"\t" + fact.encode("utf-8") + b"\n")
            fact_sets.append(sampled)
        grams[replicate] = gram_from_fact_sets(fact_sets)
        graph_hashes.append(digest.hexdigest().upper())
    return grams, {
        "replicates": NULL_REPLICATES,
        "replicate_indices": [0, NULL_REPLICATES - 1],
        "seed_text": "SHA256('20260807|b|q|p')",
        "sampler": "k smallest SHA256(seed_digest || '|' || target), target as collision tie-break",
        "without_replacement": True,
        "graph_sha256": graph_hashes,
    }


def write_exclusive_npy(path: Path, values: Any) -> None:
    np = load_numpy()
    temporary = path.parent / f".n{uuid.uuid4().hex[:20]}"
    try:
        with temporary.open("xb") as handle:
            np.save(handle, np.asarray(values), allow_pickle=False)
            fsync_file(handle)
        rename_no_overwrite(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def metric_summary(metrics: Any, mask: Any, cohort: Cohort, arm_names: Sequence[str]) -> dict[str, Any]:
    np = load_numpy()
    selected = np.flatnonzero(mask)
    if selected.size == 0:
        raise RuntimeError("metric scope is empty")
    output: dict[str, Any] = {}
    for arm, name in enumerate(arm_names):
        values = metrics[arm, selected]
        auc_values = values[:, 3]
        valid_auc = np.isfinite(auc_values)
        pair_total = float(np.sum(values[:, 5]))
        tolerance_ties = float(np.sum(values[:, 6]))
        output[name] = {
            "ndcg10": float(np.mean(values[:, 0])),
            "ndcg5": float(np.mean(values[:, 1])),
            "mrr": float(np.mean(values[:, 2])),
            "auc": float(np.mean(auc_values[valid_auc])) if np.any(valid_auc) else None,
            "auc_impressions": int(np.count_nonzero(valid_auc)),
            "pair_accuracy_micro": float(np.sum(values[:, 4]) / pair_total) if pair_total else None,
            "pair_total": int(pair_total),
            "pair_tolerance_tie_fraction": tolerance_ties / pair_total if pair_total else None,
            "pair_tolerance_ties": int(tolerance_ties),
        }
    positives = cohort.positive_counts[selected]
    candidate_counts = cohort.candidate_offsets[selected + 1] - cohort.candidate_offsets[selected]
    return {
        "impressions": int(selected.size),
        "zero_positive_impressions": int(np.count_nonzero(positives == 0)),
        "all_positive_impressions": int(np.count_nonzero(positives == candidate_counts)),
        "arms": output,
    }


def fixed_user_aggregates(metrics: Any, mask: Any, cohort: Cohort) -> Any:
    np = load_numpy()
    arms = int(metrics.shape[0])
    users = len(cohort.user_ids)
    aggregates = np.zeros((users, arms * 6 + 3), dtype=np.float64)
    indices = np.flatnonzero(mask)
    user = cohort.user_index[indices]
    for arm in range(arms):
        values = metrics[arm, indices]
        base = arm * 6
        for channel in range(3):
            np.add.at(aggregates[:, base + channel], user, values[:, channel])
        np.add.at(aggregates[:, base + 3], user, np.nan_to_num(values[:, 3], nan=0.0))
        np.add.at(aggregates[:, base + 4], user, values[:, 4])
        np.add.at(aggregates[:, base + 5], user, values[:, 6])
    np.add.at(aggregates[:, arms * 6], user, 1.0)
    np.add.at(aggregates[:, arms * 6 + 1], user, np.isfinite(metrics[0, indices, 3]).astype(np.float64))
    np.add.at(aggregates[:, arms * 6 + 2], user, metrics[0, indices, 5])
    return aggregates


def null_ndcg_user_aggregates(null_metrics: Any, cohort: Cohort) -> Any:
    np = load_numpy()
    users = len(cohort.user_ids)
    null_arms = int(null_metrics.shape[0])
    aggregates = np.zeros((users, null_arms), dtype=np.float64)
    for arm in range(null_arms):
        np.add.at(aggregates[:, arm], cohort.user_index, null_metrics[arm, :, 0])
    return aggregates


def run_user_cluster_bootstrap(
    fixed_metrics: Any, null_metrics: Any, cohort: Cohort,
    replicates: int = BOOTSTRAP_REPLICATES, seed: int = BOOTSTRAP_SEED,
) -> tuple[Any, Any]:
    np = load_numpy()
    full = np.ones(fixed_metrics.shape[1], dtype=np.bool_)
    full_aggregate = fixed_user_aggregates(fixed_metrics, full, cohort)
    affected_aggregate = fixed_user_aggregates(fixed_metrics, cohort.affected, cohort)
    null_aggregate = null_ndcg_user_aggregates(null_metrics, cohort)
    combined = np.concatenate((full_aggregate, affected_aggregate, null_aggregate), axis=1)
    users = len(cohort.user_ids)
    arms = fixed_metrics.shape[0]
    null_arms = int(null_metrics.shape[0])
    fixed_bootstrap = np.empty((2, arms, 6, replicates), dtype=np.float64)
    null_bootstrap = np.empty((null_arms, replicates), dtype=np.float64)
    generator = np.random.Generator(np.random.PCG64(seed))
    batch_size = 10
    full_width = full_aggregate.shape[1]
    affected_width = affected_aggregate.shape[1]
    for start in range(0, replicates, batch_size):
        stop = min(start + batch_size, replicates)
        draws = generator.integers(0, users, size=(stop - start, users), dtype=np.int32)
        weights = np.zeros((stop - start, users), dtype=np.float64)
        for row in range(stop - start):
            weights[row] = np.bincount(draws[row], minlength=users)
        sampled = weights @ combined
        for scope, offset in ((0, 0), (1, full_width)):
            block = sampled[:, offset : offset + full_width]
            impression_denominator = block[:, arms * 6]
            auc_denominator = block[:, arms * 6 + 1]
            pair_denominator = block[:, arms * 6 + 2]
            if np.any(impression_denominator <= 0.0):
                raise RuntimeError("bootstrap produced empty impression scope")
            for arm in range(arms):
                base = arm * 6
                fixed_bootstrap[scope, arm, 0:3, start:stop] = (
                    block[:, base : base + 3] / impression_denominator[:, None]
                ).T
                fixed_bootstrap[scope, arm, 3, start:stop] = block[:, base + 3] / auc_denominator
                fixed_bootstrap[scope, arm, 4, start:stop] = block[:, base + 4] / pair_denominator
                fixed_bootstrap[scope, arm, 5, start:stop] = block[:, base + 5] / pair_denominator
        null_block = sampled[:, full_width + affected_width :]
        full_denominator = sampled[:, arms * 6]
        null_bootstrap[:, start:stop] = (null_block / full_denominator[:, None]).T
    if not np.all(np.isfinite(fixed_bootstrap)) or not np.all(np.isfinite(null_bootstrap)):
        raise RuntimeError("bootstrap produced nonfinite estimate")
    return fixed_bootstrap, null_bootstrap


def percentile_interval(values: Any) -> list[float]:
    np = load_numpy()
    measured = np.quantile(np.asarray(values, dtype=np.float64), (0.025, 0.975), method="linear")
    return [float(measured[0]), float(measured[1])]


def bootstrap_report(fixed_bootstrap: Any, null_bootstrap: Any) -> dict[str, Any]:
    np = load_numpy()
    fixed: dict[str, Any] = {}
    reported_metrics = ("ndcg10", "ndcg5", "mrr", "auc", "pair_accuracy_micro", "pair_tolerance_tie_fraction")
    for scope_index, scope_name in enumerate(("full", "rank_affected")):
        fixed[scope_name] = {}
        for arm, arm_name in enumerate(FIXED_ARM_NAMES):
            fixed[scope_name][arm_name] = {
                metric: {
                    "estimate_mean_across_bootstrap": float(np.mean(fixed_bootstrap[scope_index, arm, metric_index])),
                    "percentile_95_ci": percentile_interval(fixed_bootstrap[scope_index, arm, metric_index]),
                }
                for metric_index, metric in enumerate(reported_metrics)
            }
    null = [
        {
            "replicate": replicate,
            "ndcg10_percentile_95_ci": percentile_interval(null_bootstrap[replicate]),
        }
        for replicate in range(NULL_REPLICATES)
    ]
    return {
        "engine": "numpy.random.Generator(PCG64(20260807)); users sampled with replacement",
        "replicates": BOOTSTRAP_REPLICATES,
        "shared_resamples_for_every_arm": True,
        "fixed_arms": fixed,
        "null_arms": null,
        "null_secondary_ci_omission": (
            "Predeclared: null arms receive nDCG10 CIs only; all null point secondary metrics are retained. "
            "Fixed arms receive all-metric CIs in both scopes."
        ),
    }


def interval_excludes_zero(interval: Sequence[float]) -> bool:
    return interval[0] > 0.0 or interval[1] < 0.0


def sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def adjudicate(
    fixed_summary: dict[str, Any], affected_summary: dict[str, Any], null_summary: dict[str, Any],
    fixed_bootstrap: Any, null_bootstrap: Any,
) -> dict[str, Any]:
    np = load_numpy()
    full_arms = fixed_summary["arms"]
    affected_arms = affected_summary["arms"]
    historical = full_arms[FIXED_ARM_NAMES[0]]["ndcg10"]
    current = full_arms[FIXED_ARM_NAMES[1]]["ndcg10"]
    entity = full_arms[FIXED_ARM_NAMES[6]]["ndcg10"]
    delta_h = current - historical
    delta_h_boot = fixed_bootstrap[0, 1, 0] - fixed_bootstrap[0, 0, 0]
    delta_h_ci = percentile_interval(delta_h_boot)
    affected_delta = (
        affected_arms[FIXED_ARM_NAMES[1]]["ndcg10"] - affected_arms[FIXED_ARM_NAMES[0]]["ndcg10"]
    )
    null_values = np.asarray(
        [item["arms"][f"matched_null_{replicate:03d}"]["ndcg10"] for replicate, item in enumerate(null_summary["replicates"])],
        dtype=np.float64,
    )
    delta_r = current - null_values
    null_absolute_q95 = float(np.quantile(np.abs(delta_r), 0.95, method="linear"))
    current_entity = current - entity
    historical_entity = historical - entity
    current_entity_boot = fixed_bootstrap[0, 1, 0] - fixed_bootstrap[0, 6, 0]
    historical_entity_boot = fixed_bootstrap[0, 0, 0] - fixed_bootstrap[0, 6, 0]
    current_entity_ci = percentile_interval(current_entity_boot)
    historical_entity_ci = percentile_interval(historical_entity_boot)
    null_reversal_count = int(np.count_nonzero(current_entity * (null_values - entity) < 0.0))
    reversal = (
        current_entity * historical_entity < 0.0
        and abs(current_entity) >= 0.002
        and abs(historical_entity) >= 0.002
        and interval_excludes_zero(current_entity_ci)
        and interval_excludes_zero(historical_entity_ci)
        and null_reversal_count <= 5
    )
    gate1 = abs(delta_h) >= 0.005 and interval_excludes_zero(delta_h_ci)
    gate2 = sign(affected_delta) == sign(delta_h) and sign(delta_h) != 0
    gate3_null = abs(delta_h) > null_absolute_q95
    gate3 = gate3_null or reversal
    robustness_deltas = {
        "metadata_blocklist": full_arms[FIXED_ARM_NAMES[3]]["ndcg10"] - full_arms[FIXED_ARM_NAMES[2]]["ndcg10"],
        "remove_q30_q22686": full_arms[FIXED_ARM_NAMES[5]]["ndcg10"] - full_arms[FIXED_ARM_NAMES[4]]["ndcg10"],
    }
    gate4 = all(sign(value) == sign(delta_h) and sign(delta_h) != 0 for value in robustness_deltas.values())
    gates = {
        "magnitude_and_cluster_ci": gate1,
        "rank_affected_same_sign": gate2,
        "matched_null_or_entity_reversal": gate3,
        "robustness_direction_unchanged": gate4,
        "integrity_and_leakage": True,
    }
    return {
        "verdict": PASS_VERDICT if all(gates.values()) else KILL_VERDICT,
        "gates": gates,
        "contrasts": {
            "D_H_current_minus_historical": delta_h,
            "D_H_percentile_95_ci": delta_h_ci,
            "D_H_rank_affected": affected_delta,
            "D_R_current_minus_null": delta_r.tolist(),
            "D_R_absolute_95th_percentile": null_absolute_q95,
            "current_minus_entity": current_entity,
            "current_minus_entity_percentile_95_ci": current_entity_ci,
            "historical_minus_entity": historical_entity,
            "historical_minus_entity_percentile_95_ci": historical_entity_ci,
            "null_reversal_count": null_reversal_count,
            "entity_reversal_alternative": reversal,
            "robustness_current_minus_historical": robustness_deltas,
        },
    }


def build_fixed_graph_grams(
    anchor_qids: Sequence[str], historical: Sequence[set[str]], current: Sequence[set[str]]
) -> tuple[Any, list[str]]:
    np = load_numpy()
    blocklist = set(METADATA_BLOCKLIST_IDS)
    removed = set(REMOVED_ANCHOR_IDS)
    historical_block = [
        {fact for fact in facts if fact.split("|", 1)[0] not in blocklist} for facts in historical
    ]
    current_block = [
        {fact for fact in facts if fact.split("|", 1)[0] not in blocklist} for facts in current
    ]
    historical_removed = [set() if qid in removed else set(facts) for qid, facts in zip(anchor_qids, historical, strict=True)]
    current_removed = [set() if qid in removed else set(facts) for qid, facts in zip(anchor_qids, current, strict=True)]
    sets = (
        historical, current, historical_block, current_block, historical_removed, current_removed,
    )
    return np.stack([gram_from_fact_sets(values) for values in sets], axis=0), list(FIXED_ARM_NAMES[:6])


def scientific_payload_hash(payload: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(payload))


def run_outcome(authorization: Mapping[str, Any]) -> dict[str, Any]:
    np = load_numpy()
    verify_thread_environment()
    verify_python_thread_state()
    role = str(authorization["run_role"])
    output_id = str(authorization["output_id"])
    if (role, output_id) not in {("primary", OUTCOME_RUN_ID), ("exact_replay", OUTCOME_REPLAY_ID)}:
        raise RuntimeError("unauthorized Phase-B run identity")
    output_directory = RESULTS_ROOT / output_id
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite {output_directory}")
    launch_directory = Path(str(authorization["launch_directory"])).resolve()
    release_path = Path(str(authorization["inner_lock_release_path"])).resolve()
    inner_lock = InnerLock(release_path, role, authorization)
    stage: Path | None = None
    published = False
    try:
        inner_lock.acquire()
        stage = safe_stage_path(output_id)
        stage.mkdir()
        require_no_async_failures()
        startup_records = verify_bound_provenance(authorization)
        input_hashes_start = verify_real_input_hashes()
        phase_a_result, anchor_qids = load_phase_a_contract()
        embedding_matrix, embedding_report = load_entity_embeddings(anchor_qids)
        news = parse_news(anchor_qids)
        historical_facts, current_facts, relations = load_relations_and_facts(anchor_qids)
        cohort = parse_committed_cohort(news)
        scoring = build_scoring_index(news, cohort)

        fixed_grams, _ = build_fixed_graph_grams(anchor_qids, historical_facts, current_facts)
        fixed_graph_similarities = pattern_similarity_from_grams(fixed_grams, news.pattern_matrix)
        reconstructed_shared_scores = score_similarity_batch(fixed_graph_similarities, scoring, cohort)
        parity: list[dict[str, Any]] = []
        for arm in range(6):
            maximum = float(np.max(np.abs(reconstructed_shared_scores[arm] - cohort.shared_scores[arm])))
            if maximum > SCORE_TOLERANCE:
                raise RuntimeError(f"pattern engine score parity failed for {FIXED_ARM_NAMES[arm]}")
            for impression in range(EXPECTED_ELIGIBLE):
                cs = int(cohort.candidate_offsets[impression])
                ce = int(cohort.candidate_offsets[impression + 1])
                reconstructed_order = frozen_order(
                    reconstructed_shared_scores[arm][cs:ce].tolist(), scoring.tie_orders[impression]
                )
                committed_order = np.argsort(
                    cohort.shared_ranks[arm, cs:ce], kind="stable"
                ).tolist()
                if reconstructed_order != committed_order:
                    raise RuntimeError(
                        f"pattern engine exact-rank parity failed for {FIXED_ARM_NAMES[arm]}"
                    )
            parity.append({
                "arm": FIXED_ARM_NAMES[arm],
                "maximum_absolute_score_error": maximum,
                "exact_rank_parity": True,
            })

        identity_similarity = pattern_similarity_from_grams(np.eye(50, dtype=np.float64), news.pattern_matrix)
        entity_scores = score_similarity_batch(identity_similarity, scoring, cohort)[0]
        transe_similarity = pattern_similarity_from_features(embedding_matrix, news.pattern_matrix)
        transe_scores = score_similarity_batch(transe_similarity, scoring, cohort)[0]
        fixed_scores = [cohort.shared_scores[arm] for arm in range(6)] + [entity_scores, transe_scores]
        fixed_metrics = metrics_from_score_arms(fixed_scores, scoring, cohort, verify_shared_ranks=True)

        null_grams, null_sampler_report = relation_stratified_null_grams(
            anchor_qids, historical_facts, current_facts
        )
        null_metrics = np.empty(
            (NULL_REPLICATES, EXPECTED_ELIGIBLE, len(METRIC_CHANNELS)), dtype=np.float64
        )
        for start in range(0, NULL_REPLICATES, NULL_BATCH_SIZE):
            stop = min(start + NULL_BATCH_SIZE, NULL_REPLICATES)
            similarities = pattern_similarity_from_grams(null_grams[start:stop], news.pattern_matrix)
            scores = score_similarity_batch(similarities, scoring, cohort)
            null_metrics[start:stop] = metrics_from_score_arms(scores, scoring, cohort)
            write_exclusive_json(
                stage / f"progress_null_{stop:03d}.json",
                {
                    "schema_version": "h6_phase_b_progress.v1",
                    "output_id": output_id,
                    "completed_null_replicates": stop,
                    "scientific_configuration_sha256": sha256_bytes(
                        canonical_bytes({"null_replicates": NULL_REPLICATES, "bootstrap": BOOTSTRAP_REPLICATES})
                    ),
                },
            )
            require_no_async_failures()

        full_mask = np.ones(EXPECTED_ELIGIBLE, dtype=np.bool_)
        fixed_summary = metric_summary(fixed_metrics, full_mask, cohort, FIXED_ARM_NAMES)
        affected_summary = metric_summary(fixed_metrics, cohort.affected, cohort, FIXED_ARM_NAMES)
        null_replicates: list[dict[str, Any]] = []
        for replicate in range(NULL_REPLICATES):
            name = f"matched_null_{replicate:03d}"
            full_null = metric_summary(null_metrics[replicate : replicate + 1], full_mask, cohort, (name,))
            affected_null = metric_summary(
                null_metrics[replicate : replicate + 1], cohort.affected, cohort, (name,)
            )
            full_null["replicate"] = replicate
            full_null["rank_affected"] = affected_null
            null_replicates.append(full_null)
        null_summary = {"replicates": null_replicates}

        fixed_bootstrap, null_bootstrap = run_user_cluster_bootstrap(fixed_metrics, null_metrics, cohort)
        bootstrap = bootstrap_report(fixed_bootstrap, null_bootstrap)
        decision = adjudicate(
            fixed_summary, affected_summary, null_summary, fixed_bootstrap, null_bootstrap
        )

        candidate_counts = np.diff(cohort.candidate_offsets).astype(np.int32, copy=False)
        raw_values = {
            "fixed_metrics.npy": fixed_metrics,
            "null_metrics.npy": null_metrics,
            "fixed_bootstrap.npy": fixed_bootstrap,
            "null_ndcg10_bootstrap.npy": null_bootstrap,
            "user_index.npy": cohort.user_index,
            "affected.npy": cohort.affected,
            "positive_counts.npy": cohort.positive_counts,
            "candidate_counts.npy": candidate_counts,
        }
        for name, values in raw_values.items():
            write_exclusive_npy(stage / name, values)
        raw_artifacts = {name: file_record(stage / name) for name in sorted(raw_values)}
        raw_payload = {
            name: {"sha256": record["sha256"], "bytes": record["bytes"]}
            for name, record in raw_artifacts.items()
        }
        raw_payload_sha256 = sha256_bytes(canonical_bytes(raw_payload))
        scientific_payload = {
            "schema_version": "h6_phase_b_scientific_payload.v1",
            "phase_a": {
                "commit": PHASE_A_COMMIT,
                "manifest_sha256": PHASE_A_MANIFEST_SHA256,
                "result_sha256": PHASE_A_RESULT_SHA256,
            },
            "cohort": {
                "eligible_impressions": EXPECTED_ELIGIBLE,
                "distinct_users": EXPECTED_USERS,
                "candidates": EXPECTED_CANDIDATES,
                "rank_affected_impressions": EXPECTED_AFFECTED,
                "labels_opened_only_after_manifest_match": True,
                "post_label_filtering": False,
            },
            "implementation": {
                "anchor_scope": "exact Phase-A top-50 retained QIDs for every fixed and null arm",
                "news_anchor_incidence_patterns": int(news.pattern_matrix.shape[0]),
                "history_pattern_csr_nnz": int(scoring.history_pattern_counts.nnz),
                "pattern_engine_parity": parity,
                "entity_only": "identity Gram over frozen top-50 anchors",
                "mind_transe": embedding_report,
                "mind_transe_per_entity_normalization_rejected_prospectively": True,
                "relations": len(relations),
            },
            "metric_definitions": {
                "ndcg_mrr_order": "first-score-anchored 1e-12 groups, SHA256 tie rule",
                "auc": "mean per-impression pairwise AUC; 0.5 within the same first-score-anchored tolerance group; both-class only",
                "pair_accuracy": "micro correctness under frozen deterministic total rank",
                "pair_tolerance_tie_fraction": "eligible positive-negative pairs resolved only by tolerance-group SHA tie",
                "zero_positive_ndcg_mrr": 0,
            },
            "fixed_full": fixed_summary,
            "fixed_rank_affected": affected_summary,
            "matched_null": {"sampler": null_sampler_report, **null_summary},
            "bootstrap": bootstrap,
            "decision": decision,
            "raw_artifact_payload": raw_payload,
            "raw_artifact_payload_sha256": raw_payload_sha256,
        }
        payload_sha256 = scientific_payload_hash(scientific_payload)
        input_hashes_publication = verify_real_input_hashes()
        if input_hashes_publication != input_hashes_start:
            raise RuntimeError("immutable input changed during Phase-B run")
        result = {
            "schema_version": "h6_phase_b_outcome.python.v1",
            "classification": "confirmatory held-fixed outcome test",
            "output_id": output_id,
            "run_role": role,
            "scientific_payload": scientific_payload,
            "scientific_payload_sha256": payload_sha256,
            "provenance": {
                "process_pid": os.getpid(),
                "launcher_pid": int(authorization["launcher_pid"]),
                "launch_id": authorization["launch_id"],
                "runner": file_record(SCRIPT_PATH),
                "launcher": file_record(LAUNCHER_PATH),
                "implementation_lock": file_record(IMPLEMENTATION_LOCK_PATH),
                "inputs_at_start": input_hashes_start,
                "inputs_before_publication": input_hashes_publication,
                "async_error_ledger": file_record(Path(str(authorization["async_error_ledger"]))),
                "authorization": file_record(Path(str(authorization["authorization_path"]))),
            },
        }
        write_exclusive_json(stage / "result.json", result)
        verify_thread_environment()
        verify_python_thread_state()
        if verify_bound_provenance(authorization) != startup_records:
            raise RuntimeError("authorized runtime/provenance changed before Phase-B publication")
        if not process_is_alive(int(authorization["launcher_pid"])):
            raise RuntimeError("launcher exited before Phase-B publication")
        assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), OUTER_LOCK_PATH)
        require_no_async_failures()
        if output_directory.exists():
            raise FileExistsError("Phase-B output appeared during computation")
        rename_no_overwrite(stage, output_directory)
        published = True
        release_record = inner_lock.release(failed=False)
        require_no_async_failures()
        return {
            "status": "H6_PHASE_B_RUN_COMPLETE",
            "process_pid": os.getpid(),
            "output_id": output_id,
            "run_role": role,
            "result_path": str((output_directory / "result.json").resolve()),
            "result_sha256": sha256_file(output_directory / "result.json"),
            "scientific_payload_sha256": payload_sha256,
            "raw_artifact_payload_sha256": raw_payload_sha256,
            "verdict": decision["verdict"],
            "inner_lock_release": release_record,
        }
    except BaseException as error:
        cleanup_errors: list[BaseException] = []
        if not published and stage is not None:
            try:
                remove_safe_stage(stage, output_id)
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if inner_lock.fd is not None:
            try:
                inner_lock.release(failed=True)
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            raise BaseExceptionGroup(
                "H6 Phase-B computation and cleanup both failed", [error, *cleanup_errors]
            ) from error
        raise


def load_bound_npy(directory: Path, name: str, declaration: Mapping[str, Any]) -> Any:
    np = load_numpy()
    path = directory / name
    expected = declaration.get(name)
    if not isinstance(expected, dict) or sha256_file(path) != expected.get("sha256") or path.stat().st_size != expected.get("bytes"):
        raise RuntimeError(f"raw artifact hash/size mismatch: {name}")
    values = np.load(path, allow_pickle=False)
    if not isinstance(values, np.ndarray):
        raise RuntimeError(f"raw artifact is not ndarray: {name}")
    return values


def verify_result_directory(directory: Path, output_id: str, role: str) -> tuple[dict[str, Any], dict[str, Any]]:
    np = load_numpy()
    result_path = directory / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if (
        result.get("schema_version") != "h6_phase_b_outcome.python.v1"
        or result.get("output_id") != output_id
        or result.get("run_role") != role
    ):
        raise RuntimeError("Phase-B result identity/schema mismatch")
    payload = result.get("scientific_payload")
    if not isinstance(payload, dict) or scientific_payload_hash(payload) != result.get("scientific_payload_sha256"):
        raise RuntimeError("Phase-B scientific payload hash mismatch")
    declaration = payload.get("raw_artifact_payload")
    if not isinstance(declaration, dict) or sha256_bytes(canonical_bytes(declaration)) != payload.get(
        "raw_artifact_payload_sha256"
    ):
        raise RuntimeError("raw artifact declaration hash mismatch")
    expected_names = {
        "fixed_metrics.npy", "null_metrics.npy", "fixed_bootstrap.npy", "null_ndcg10_bootstrap.npy",
        "user_index.npy", "affected.npy", "positive_counts.npy", "candidate_counts.npy",
    }
    if set(declaration) != expected_names:
        raise RuntimeError("raw artifact declaration names mismatch")
    arrays = {name: load_bound_npy(directory, name, declaration) for name in sorted(expected_names)}
    if arrays["fixed_metrics.npy"].shape != (8, EXPECTED_ELIGIBLE, len(METRIC_CHANNELS)):
        raise RuntimeError("fixed metric array shape mismatch")
    if arrays["null_metrics.npy"].shape != (NULL_REPLICATES, EXPECTED_ELIGIBLE, len(METRIC_CHANNELS)):
        raise RuntimeError("null metric array shape mismatch")
    if arrays["fixed_bootstrap.npy"].shape != (2, 8, 6, BOOTSTRAP_REPLICATES):
        raise RuntimeError("fixed bootstrap shape mismatch")
    if arrays["null_ndcg10_bootstrap.npy"].shape != (NULL_REPLICATES, BOOTSTRAP_REPLICATES):
        raise RuntimeError("null bootstrap shape mismatch")
    for name in ("user_index.npy", "affected.npy", "positive_counts.npy", "candidate_counts.npy"):
        if arrays[name].shape != (EXPECTED_ELIGIBLE,):
            raise RuntimeError(f"cohort structure shape mismatch: {name}")
    if int(np.count_nonzero(arrays["affected.npy"])) != EXPECTED_AFFECTED:
        raise RuntimeError("raw affected subset cardinality mismatch")
    if int(np.max(arrays["user_index.npy"])) + 1 != EXPECTED_USERS:
        raise RuntimeError("raw user index cardinality mismatch")
    if int(np.sum(arrays["candidate_counts.npy"])) != EXPECTED_CANDIDATES:
        raise RuntimeError("raw candidate count mismatch")
    return result, arrays


def deep_verify(authorization: Mapping[str, Any]) -> dict[str, Any]:
    np = load_numpy()
    startup_records = verify_bound_provenance(authorization)
    verify_real_input_hashes()
    primary_directory = RESULTS_ROOT / OUTCOME_RUN_ID
    replay_directory = RESULTS_ROOT / OUTCOME_REPLAY_ID
    primary, primary_arrays = verify_result_directory(primary_directory, OUTCOME_RUN_ID, "primary")
    replay, replay_arrays = verify_result_directory(replay_directory, OUTCOME_REPLAY_ID, "exact_replay")
    if primary["scientific_payload_sha256"] != replay["scientific_payload_sha256"]:
        raise RuntimeError("primary/replay scientific payload differs")
    if primary["scientific_payload"] != replay["scientific_payload"]:
        raise RuntimeError("primary/replay scientific payload is not exactly equal")
    for name in primary_arrays:
        if not np.array_equal(primary_arrays[name], replay_arrays[name], equal_nan=True):
            raise RuntimeError(f"primary/replay raw array differs: {name}")

    fixed_metrics = primary_arrays["fixed_metrics.npy"]
    null_metrics = primary_arrays["null_metrics.npy"]
    user = primary_arrays["user_index.npy"].astype(np.int32, copy=False)
    affected = primary_arrays["affected.npy"].astype(np.bool_, copy=False)
    positive = primary_arrays["positive_counts.npy"].astype(np.int32, copy=False)
    candidate_counts = primary_arrays["candidate_counts.npy"].astype(np.int64, copy=False)
    offsets = np.concatenate((np.asarray([0], dtype=np.int64), np.cumsum(candidate_counts, dtype=np.int64)))
    cohort = Cohort(
        [str(index) for index in range(EXPECTED_ELIGIBLE)],
        [str(index) for index in range(EXPECTED_USERS)],
        user, None, None, offsets, None, None, positive, None, None, affected,
    )
    full = np.ones(EXPECTED_ELIGIBLE, dtype=np.bool_)
    fixed_summary = metric_summary(fixed_metrics, full, cohort, FIXED_ARM_NAMES)
    affected_summary = metric_summary(fixed_metrics, affected, cohort, FIXED_ARM_NAMES)
    null_replicates: list[dict[str, Any]] = []
    for replicate in range(NULL_REPLICATES):
        name = f"matched_null_{replicate:03d}"
        item = metric_summary(null_metrics[replicate : replicate + 1], full, cohort, (name,))
        item["replicate"] = replicate
        item["rank_affected"] = metric_summary(
            null_metrics[replicate : replicate + 1], affected, cohort, (name,)
        )
        null_replicates.append(item)
    recomputed_fixed_bootstrap, recomputed_null_bootstrap = run_user_cluster_bootstrap(
        fixed_metrics, null_metrics, cohort
    )
    if not np.array_equal(recomputed_fixed_bootstrap, primary_arrays["fixed_bootstrap.npy"]):
        raise RuntimeError("fixed bootstrap raw replay mismatch")
    if not np.array_equal(recomputed_null_bootstrap, primary_arrays["null_ndcg10_bootstrap.npy"]):
        raise RuntimeError("null bootstrap raw replay mismatch")
    recomputed_bootstrap_report = bootstrap_report(recomputed_fixed_bootstrap, recomputed_null_bootstrap)
    recomputed_decision = adjudicate(
        fixed_summary, affected_summary, {"replicates": null_replicates},
        recomputed_fixed_bootstrap, recomputed_null_bootstrap,
    )
    payload = primary["scientific_payload"]
    if (
        fixed_summary != payload.get("fixed_full")
        or affected_summary != payload.get("fixed_rank_affected")
        or null_replicates != payload.get("matched_null", {}).get("replicates")
        or recomputed_bootstrap_report != payload.get("bootstrap")
        or recomputed_decision != payload.get("decision")
    ):
        raise RuntimeError("deep verifier recomputation differs from scientific payload")
    verify_thread_environment()
    verify_python_thread_state()
    if verify_bound_provenance(authorization) != startup_records:
        raise RuntimeError("authorized runtime/provenance changed during deep verification")
    verify_real_input_hashes()
    if not process_is_alive(int(authorization["launcher_pid"])):
        raise RuntimeError("launcher exited during deep verification")
    assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), OUTER_LOCK_PATH)
    require_no_async_failures()
    verification = {
        "schema_version": "h6_phase_b_deep_verification.v1",
        "status": "H6_PHASE_B_DEEP_VERIFY_COMPLETE",
        "process_pid": os.getpid(),
        "scientific_payload_sha256": primary["scientific_payload_sha256"],
        "raw_artifact_payload_sha256": payload["raw_artifact_payload_sha256"],
        "verdict": recomputed_decision["verdict"],
        "primary_replay_exact": True,
        "raw_gate_recomputation": True,
        "bootstrap_recomputation": True,
    }
    path = Path(str(authorization["verification_path"])).resolve()
    launch_directory = Path(str(authorization["launch_directory"])).resolve()
    if path.parent != launch_directory or path.name != "deep_verification.json":
        raise RuntimeError("deep verification path escaped authorization")
    write_exclusive_json(path, verification)
    require_no_async_failures()
    return {
        "status": "H6_PHASE_B_VERIFY_COMPLETE",
        "process_pid": os.getpid(),
        "verification_path": str(path),
        "verification_sha256": sha256_file(path),
        "scientific_payload_sha256": primary["scientific_payload_sha256"],
        "raw_artifact_payload_sha256": payload["raw_artifact_payload_sha256"],
        "verdict": recomputed_decision["verdict"],
    }


def run_selftest(authorization: Mapping[str, Any]) -> dict[str, Any]:
    np = load_numpy()
    sparse = load_sparse()
    verify_thread_environment()
    verify_python_thread_state()
    require_no_async_failures()
    startup_records = verify_bound_provenance(authorization)
    patterns = np.zeros((4, 50), dtype=np.float64)
    patterns[1, 0] = 1.0
    patterns[2, 1] = 1.0
    patterns[3, (0, 1)] = 1.0
    fact_sets = [set() for _ in range(50)]
    fact_sets[0] = {"P1|Q1", "P2|Q2"}
    fact_sets[1] = {"P1|Q1", "P3|Q3"}
    gram = gram_from_fact_sets(fact_sets)
    similarity = pattern_similarity_from_grams(gram, patterns)
    history = sparse.csr_matrix(
        (np.asarray([1.0, 2.0, 1.0]), (np.asarray([0, 0, 1]), np.asarray([1, 3, 2]))),
        shape=(2, 4), dtype=np.float64,
    )
    scoring = ScoringIndex(
        history,
        [np.asarray([0, 1, 2, 3], dtype=np.int32), np.asarray([1, 2, 3], dtype=np.int32)],
        [np.asarray([1, 2, 3, 0], dtype=np.int32), np.asarray([0, 2, 1], dtype=np.int32)],
        [np.asarray([3, 2, 1, 0], dtype=np.int32), np.asarray([1, 0, 2], dtype=np.int32)],
    )
    cohort = Cohort(
        ["I1", "I2"], ["U1", "U2"], np.asarray([0, 1], dtype=np.int32),
        None, None, np.asarray([0, 4, 7], dtype=np.int64), None,
        np.asarray([0, 1, 0, 1, 1, 0, 0], dtype=np.uint8), np.asarray([2, 1], dtype=np.int32),
        None, None, np.asarray([True, True], dtype=np.bool_),
    )
    synthetic_scores = score_similarity_batch(similarity, scoring, cohort)[0]
    if synthetic_scores.shape != (7,) or not np.all(np.isfinite(synthetic_scores)):
        raise RuntimeError("synthetic pattern scorer failed")
    fact_universe = sorted(set().union(*fact_sets))
    entity_vectors = np.zeros((50, len(fact_universe)), dtype=np.float64)
    for anchor, facts in enumerate(fact_sets):
        if facts:
            for fact in facts:
                entity_vectors[anchor, fact_universe.index(fact)] = 1.0
            entity_vectors[anchor] /= np.linalg.norm(entity_vectors[anchor])
    direct_news = patterns @ entity_vectors
    direct_norm = np.linalg.norm(direct_news, axis=1)
    direct_news[direct_norm > 0.0] /= direct_norm[direct_norm > 0.0, None]
    direct_expected: list[float] = []
    for history_counts, candidate_pattern_ids in (
        (np.asarray([0.0, 1.0, 0.0, 2.0]), [1, 2, 3, 0]),
        (np.asarray([0.0, 0.0, 1.0, 0.0]), [1, 3, 2]),
    ):
        direct_user = history_counts @ direct_news
        user_norm = float(np.linalg.norm(direct_user))
        direct_user = direct_user / user_norm if user_norm > 0.0 else direct_user
        direct_expected.extend((direct_news[candidate_pattern_ids] @ direct_user).tolist())
    if not np.allclose(synthetic_scores, np.asarray(direct_expected), rtol=0.0, atol=1e-15):
        raise RuntimeError("synthetic pattern scorer differs from direct fact-space construction")
    metric, order = metric_vector(
        np.asarray([1.0, 1.0 + 0.5e-12, 0.0]), np.asarray([1, 0, 1], dtype=np.uint8),
        np.asarray([1, 0, 2], dtype=np.int32),
    )
    if order[:2] != [1, 0] or metric[3] != 0.25 or metric[5] != 2.0 or metric[6] != 1.0:
        raise RuntimeError("synthetic tolerance/AUC/pair metric failed")
    fixed_scores = [synthetic_scores, synthetic_scores + np.asarray([0, 0, 0, 1e-3, 0, 0, 0])]
    fixed_metrics = metrics_from_score_arms(fixed_scores, scoring, cohort)
    null_metrics = np.stack((fixed_metrics[0], fixed_metrics[1]), axis=0)
    first = run_user_cluster_bootstrap(fixed_metrics, null_metrics, cohort, replicates=50, seed=BOOTSTRAP_SEED)
    second = run_user_cluster_bootstrap(fixed_metrics, null_metrics, cohort, replicates=50, seed=BOOTSTRAP_SEED)
    if not np.array_equal(first[0], second[0]) or not np.array_equal(first[1], second[1]):
        raise RuntimeError("synthetic shared bootstrap is nondeterministic")
    seed = hashlib.sha256(b"20260807|0|Q1|P1").digest()
    targets = ["Q1", "Q2", "Q3"]
    sample_a = sorted(targets, key=lambda target: hashlib.sha256(seed + b"|" + target.encode()).digest())[:2]
    sample_b = sorted(targets, key=lambda target: hashlib.sha256(seed + b"|" + target.encode()).digest())[:2]
    if sample_a != sample_b or len(set(sample_a)) != 2:
        raise RuntimeError("synthetic null sampler failed")
    verify_python_thread_state()
    if verify_bound_provenance(authorization) != startup_records:
        raise RuntimeError("authorized runtime/provenance changed during self-test")
    if not process_is_alive(int(authorization["launcher_pid"])):
        raise RuntimeError("launcher exited during self-test")
    assert_outer_lock_held(
        Path(str(authorization["outer_lock"])).resolve(), SELFTEST_OUTER_LOCK_PATH
    )
    require_no_async_failures()
    return {
        "status": "H6_PHASE_B_SELFTEST_COMPLETE",
        "process_pid": os.getpid(),
        "real_inputs_opened": False,
        "candidate_labels_opened": False,
        "checks": [
            "pattern_Gram_scoring", "tolerance_hash_ranking", "AUC_vs_micro_pair_distinction",
            "PCG64_shared_cluster_bootstrap", "SHA256_null_sampling_without_replacement",
        ],
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("self-test", "run", "verify"))
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--process-start", required=True)
    parser.add_argument("--process-ack", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    try:
        authorization_path = Path(args.authorization).resolve()
        preliminary = json.loads(authorization_path.read_text(encoding="utf-8"))
        ledger = Path(str(preliminary.get("async_error_ledger", ""))).resolve()
        install_async_hooks(ledger)
        authorization = bootstrap_handshake(args)
        if args.command == "self-test":
            summary = run_selftest(authorization)
        elif args.command == "run":
            summary = run_outcome(authorization)
        else:
            summary = deep_verify(authorization)
        require_no_async_failures()
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False, separators=(",", ":")), flush=True)
        return 0
    except BaseException:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
