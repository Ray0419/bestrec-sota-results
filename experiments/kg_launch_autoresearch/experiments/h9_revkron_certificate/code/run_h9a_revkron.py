#!/usr/bin/env python3
"""Locked, label-blind H9A RevKron-Cert runner and deep verifier.

The real-data paths are reachable only through the hash-bound Windows launcher.
The self-test is synthetic and deliberately does not open any immutable input.
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
import hashlib
import itertools
import json
import math
import re
import shutil
import sys
import threading
import time
import traceback
import uuid
from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SEED_TEXT = "20260807"
AUDIT_PREFIX = b"H9A-AUDIT|20260807|"
SAMPLE_SIZE = 50
MINIMUM_CONFIDENCE = 0.90
EXPECTED_NEWS_ROWS = 42_416
EXPECTED_RELATIONS = 1_091
EXPECTED_PATTERNS = 812
EXPECTED_IMPRESSIONS = 64_443
EXPECTED_USERS = 43_374
EXPECTED_CANDIDATES = 2_422_258
EXPECTED_SUPPORTED = 512_071
EXPECTED_NONVACUOUS = 48_422
EXPECTED_SUPPORTED_GT10 = 17_436
EXPECTED_SUPPORTED_GE2 = 44_341
EXPECTED_MANIFEST_BYTES = 224_785_295
AUDIT_ROWS = 1_024
PROTOCOL_SHA256 = "B1D52DE0A454F8B29A1DB4A6E0627EFC6A60E96010730C7D9427276D6D4C11C9"
RUN_ID = "h9a_run_001"
REPLAY_ID = "h9a_run_001_replay"
PASS_VERDICT = "ADVANCE_TO_H9B_PROVENANCE_WORLDS"
KILL_VERDICT = "KILL_H9_KRON_DIRECTION"

EXPECTED_HASHES = {
    "news": "E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822",
    "relations": "D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A",
    "facts": "13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D",
    "phase_a_result": "B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF",
    "phase_a_manifest": "522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5",
    "phase_a_completion": "AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06",
}
METADATA_BLOCKLIST_IDS = (
    "P1343", "P1424", "P5008", "P6104", "P7867", "P8744",
    "P9241", "P2354", "P8402", "P10280", "P1889",
)
METADATA_BLOCKLIST = frozenset(METADATA_BLOCKLIST_IDS)
REMOVED_ANCHOR_IDS = ("Q30", "Q22686")
VIEW_NAMES = (
    "primary_relation_vocabulary",
    "metadata_blocklist",
    "remove_q30_q22686",
)
STATE_NAMES = ("intersection", "historical", "current", "union")
GAMMAS = (Fraction(1, 1), Fraction(1, 10), Fraction(10, 1))
PRIMARY_GAMMA = Fraction(1, 1)
QID_PATTERN = re.compile(r"^Q[1-9][0-9]*$")
PROPERTY_PATTERN = re.compile(r"^P[1-9][0-9]*$")
FACT_PATTERN = re.compile(r"^(P[1-9][0-9]*)\|(Q[1-9][0-9]*)$")
NEWS_ID_PATTERN = re.compile(r"^N[0-9]+$")
MANIFEST_SUFFIX_PATTERN = re.compile(rb'"N[0-9]+-[01]"')

SCRIPT_PATH = Path(__file__).resolve()
H9_DIR = SCRIPT_PATH.parent.parent
ROOT = H9_DIR.parents[3]
PROTOCOL_PATH = H9_DIR / "protocol.md"
IMPLEMENTATION_LOCK_PATH = H9_DIR / "implementation_lock.md"
LAUNCHER_PATH = SCRIPT_PATH.with_name("run_h9a_revkron_safe.ps1")
RESULTS_ROOT = H9_DIR / "results"
SELFTEST_ROOT = H9_DIR / "selftest_artifacts"
INNER_LOCK_PATH = H9_DIR / "H9A_RUN_001_INNER.lock"
OUTER_LOCK_PATH = H9_DIR / "H9A_RUN_001_LAUNCH.lock"
SELFTEST_OUTER_LOCK_PATH = H9_DIR / "H9A_SELFTEST_LAUNCH.lock"
VENV_LAUNCHER_PATH = ROOT / "_bestrec_run/.venv/Scripts/python.exe"
VENV_CONFIG_PATH = ROOT / "_bestrec_run/.venv/pyvenv.cfg"
H6_DIR = ROOT / "experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence"
INPUT_PATHS = {
    "news": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/news.tsv",
    "relations": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/relation_embedding.vec",
    "facts": ROOT / "experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/facts.jsonl",
    "phase_a_result": H6_DIR / "results/coverage_run_002/result.json",
    "phase_a_manifest": H6_DIR / "results/coverage_run_002/cohort_manifest.jsonl",
    "phase_a_completion": H6_DIR / "results/coverage_run_002_completion.json",
}

_NP: Any = None
_MP: Any = None
_IV: Any = None
_ASYNC_LEDGER: Path | None = None
_ASYNC_FAILURES: list[dict[str, Any]] = []


def load_numpy() -> Any:
    global _NP
    if _NP is None:
        import numpy as np  # type: ignore
        _NP = np
    return _NP


def load_mpmath() -> tuple[Any, Any]:
    global _MP, _IV
    if _MP is None:
        from mpmath import iv, mp  # type: ignore
        _MP, _IV = mp, iv
    return _MP, _IV


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
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
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
    if last_error is not None:
        raise last_error


def write_exclusive_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".p{uuid.uuid4().hex[:20]}"
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


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_stage_path(output_id: str) -> Path:
    if output_id not in {RUN_ID, REPLAY_ID}:
        raise RuntimeError("unauthorized H9A output ID")
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    stage = RESULTS_ROOT / f".{output_id}.tmp.{uuid.uuid4().hex}"
    if stage.parent.resolve() != RESULTS_ROOT.resolve() or re.fullmatch(
        rf"\.{re.escape(output_id)}\.tmp\.[0-9a-f]{{32}}", stage.name
    ) is None:
        raise RuntimeError("unsafe H9A stage path")
    return stage


def remove_safe_stage(stage: Path, output_id: str) -> None:
    if not stage.exists():
        return
    if stage.parent.resolve() != RESULTS_ROOT.resolve() or re.fullmatch(
        rf"\.{re.escape(output_id)}\.tmp\.[0-9a-f]{{32}}", stage.name
    ) is None:
        raise RuntimeError("refusing unsafe H9A stage cleanup")
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
        raise RuntimeError("H9A is not executing on MainThread")
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


def assert_outer_lock_held(path: Path, expected: Path) -> None:
    if path.resolve() != expected.resolve() or not path.is_file():
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
    def __init__(self, release_path: Path, authorization: Mapping[str, Any]) -> None:
        self.release_path = release_path
        self.authorization = authorization
        self.fd: int | None = None
        self.owner: dict[str, Any] | None = None
        self.retired: dict[str, Any] | None = None

    def acquire(self) -> None:
        role = str(self.authorization["run_role"])
        self.owner = {
            "schema_version": "h9a_inner_lock.v1",
            "mode": "h9a-inner-lock",
            "pid": os.getpid(),
            "launcher_pid": int(self.authorization["launcher_pid"]),
            "launch_id": str(self.authorization["launch_id"]),
            "role": role,
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
                    existing = read_json(INNER_LOCK_PATH)
                except Exception as error:
                    raise RuntimeError("existing inner lock unreadable; refusing retirement") from error
                expected_fields = {
                    "schema_version", "mode", "pid", "launcher_pid", "launch_id", "role",
                    "runner_sha256", "token_sha256", "created_time_ns",
                }
                if (
                    not isinstance(existing, dict)
                    or set(existing) != expected_fields
                    or existing.get("schema_version") != "h9a_inner_lock.v1"
                    or existing.get("mode") != "h9a-inner-lock"
                    or not isinstance(existing.get("pid"), int) or int(existing["pid"]) <= 0
                    or not isinstance(existing.get("launcher_pid"), int) or int(existing["launcher_pid"]) <= 0
                    or not isinstance(existing.get("launch_id"), str) or not existing["launch_id"]
                    or existing.get("role") not in {"primary", "exact_replay"}
                    or re.fullmatch(r"[0-9A-F]{64}", str(existing.get("runner_sha256", ""))) is None
                    or re.fullmatch(r"[0-9A-F]{64}", str(existing.get("token_sha256", ""))) is None
                    or not isinstance(existing.get("created_time_ns"), int)
                ):
                    raise RuntimeError("existing inner lock owner is invalid")
                if process_is_alive(int(existing["pid"])):
                    raise RuntimeError(f"active H9A inner lock is owned by PID {existing['pid']}")
                retired = self.release_path.parent / f"stale_inner_{uuid.uuid4().hex[:20]}.json"
                rename_no_overwrite(INNER_LOCK_PATH, retired)
                self.retired = file_record(retired)
        raise AssertionError("unreachable inner lock state")

    def release(self, failed: bool = False) -> dict[str, Any]:
        if self.fd is None:
            raise RuntimeError("inner lock was not acquired")
        os.close(self.fd)
        self.fd = None
        destination = self.release_path
        if failed:
            destination = destination.with_name(
                f"inner_fail_{self.authorization['run_role']}_{uuid.uuid4().hex[:20]}.json"
            )
        rename_no_overwrite(INNER_LOCK_PATH, destination)
        return file_record(destination)


def verify_bound_provenance(authorization: Mapping[str, Any]) -> dict[str, Any]:
    fixed = {
        "runner": (SCRIPT_PATH, "runner_sha256"),
        "launcher": (LAUNCHER_PATH, "launcher_sha256"),
        "protocol": (PROTOCOL_PATH, "protocol_sha256"),
        "implementation_lock": (IMPLEMENTATION_LOCK_PATH, "lock_sha256"),
        "venv_launcher": (VENV_LAUNCHER_PATH, "venv_launcher_sha256"),
        "venv_config": (VENV_CONFIG_PATH, "venv_config_sha256"),
        "base_interpreter": (Path(str(authorization.get("base_interpreter", ""))).resolve(), "base_interpreter_sha256"),
    }
    records: dict[str, Any] = {}
    for name, (path, hash_field) in fixed.items():
        if not path.is_file():
            raise RuntimeError(f"authorized provenance file is missing: {name}")
        record = file_record(path)
        if record["sha256"] != authorization.get(hash_field):
            raise RuntimeError(f"authorized provenance hash mismatch: {name}")
        records[name] = record
    base = fixed["base_interpreter"][0]
    if (
        Path(sys.executable).resolve() != VENV_LAUNCHER_PATH.resolve()
        or Path(str(getattr(sys, "_base_executable", ""))).resolve() != base
        or Path(sys.prefix).resolve() != VENV_LAUNCHER_PATH.parent.parent.resolve()
        or Path(sys.base_prefix).resolve() != base.parent.resolve()
    ):
        raise RuntimeError("CPython base/workspace-venv identity mismatch")
    return records


def bootstrap_handshake(args: argparse.Namespace) -> dict[str, Any]:
    authorization_path = Path(args.authorization).resolve()
    authorization = read_json(authorization_path)
    if not isinstance(authorization, dict):
        raise RuntimeError("launcher authorization is malformed")
    verify_thread_environment()
    verify_python_thread_state()
    runner_hash = sha256_file(SCRIPT_PATH)
    authorization_hash = sha256_file(authorization_path)
    token_hash = sha256_bytes(args.token.encode("utf-8"))
    if (
        authorization.get("mode") != "h9a-launcher-authorization"
        or authorization.get("action") != args.command
        or authorization.get("token") != args.token
        or authorization.get("token_sha256") != token_hash
        or authorization.get("runner_sha256") != runner_hash
        or Path(str(authorization.get("launcher_path", ""))).resolve() != LAUNCHER_PATH.resolve()
        or Path(str(authorization.get("authorization_path", ""))).resolve() != authorization_path
        or authorization.get("phase_a_commit_tree_result_sha256") != EXPECTED_HASHES["phase_a_result"]
        or authorization.get("immutable_input_sha256") != EXPECTED_HASHES
        or authorization.get("label_free_only") is not True
        or authorization.get("candidate_suffix_labels_forbidden") is not True
        or Path(str(authorization.get("inner_lock", ""))).resolve() != INNER_LOCK_PATH.resolve()
    ):
        raise RuntimeError("launcher authorization identity mismatch")
    allowed = {
        "self-test": ("selftest", "synthetic_selftest"),
        "run": None,
        "verify": ("verifier", "deep_verification"),
    }
    pair = (str(authorization.get("run_role", "")), str(authorization.get("output_id", "")))
    if args.command not in allowed:
        raise RuntimeError("unknown authorized action")
    if args.command == "run" and pair not in {("primary", RUN_ID), ("exact_replay", REPLAY_ID)}:
        raise RuntimeError("run role/output authorization mismatch")
    if args.command != "run" and pair != allowed[args.command]:
        raise RuntimeError("action role/output authorization mismatch")
    if args.command == "self-test" and authorization.get("self_test_only") is not True:
        raise RuntimeError("self-test is not explicitly synthetic-only")

    launch_directory = Path(str(authorization.get("launch_directory", ""))).resolve()
    if args.command == "self-test":
        expected_parent, prefix, outer = SELFTEST_ROOT.resolve(), "h9st_", SELFTEST_OUTER_LOCK_PATH
    else:
        expected_parent, prefix, outer = RESULTS_ROOT.resolve(), "h9_", OUTER_LOCK_PATH
    if (
        launch_directory.parent != expected_parent
        or re.fullmatch(re.escape(prefix) + r"[0-9a-f]{20}", launch_directory.name) is None
        or authorization_path.parent != launch_directory
    ):
        raise RuntimeError("launcher artifact containment mismatch")
    label = pair[0]
    exact_names = {
        "authorization_path": f"{label}_authorization.json",
        "async_error_ledger": f"{label}_async_errors.jsonl",
        "process_start_path": f"{label}_process_start.json",
        "process_ack_path": f"{label}_process_ack.json",
    }
    paths: list[Path] = []
    for field_name, expected_name in exact_names.items():
        candidate = Path(str(authorization.get(field_name, ""))).resolve()
        if candidate.parent != launch_directory or candidate.name != expected_name:
            raise RuntimeError(f"authorized child artifact filename mismatch: {field_name}")
        paths.append(candidate)
    if len(set(paths)) != len(paths):
        raise RuntimeError("authorized child artifact paths are not distinct")
    if args.command == "run":
        expected_release = launch_directory / f"{label}_inner_lock_released.json"
        if Path(str(authorization.get("inner_lock_release_path", ""))).resolve() != expected_release.resolve():
            raise RuntimeError("inner-lock release authorization mismatch")
    if args.command == "verify":
        verification_path = Path(str(authorization.get("verification_path", ""))).resolve()
        if verification_path.parent != launch_directory or verification_path.name != "deep_verification.json":
            raise RuntimeError("deep-verification path escaped launch directory")
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
    runtime = verify_bound_provenance(authorization)
    if authorization.get("protocol_sha256") != PROTOCOL_SHA256:
        raise RuntimeError("authorization does not bind the locked H9A protocol")
    record = {
        "mode": "h9a-child-process-start",
        "action": args.command,
        "run_role": pair[0],
        "output_id": pair[1],
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
            "runtime_files": runtime,
            "main_thread_only": True,
            "thread_bounds": {
                name: os.environ.get(name) for name in (
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
    acknowledgement = read_json(ack_path)
    if (
        acknowledgement.get("mode") != "h9a-child-process-acknowledgement"
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
    if set(INPUT_PATHS) != set(EXPECTED_HASHES):
        raise RuntimeError("H9A input allowlist changed")
    forbidden_fragments = ("behaviors.tsv", "outcome_run_001", "phase_b_")
    for path in INPUT_PATHS.values():
        lowered = str(path).lower()
        if any(fragment in lowered for fragment in forbidden_fragments):
            raise RuntimeError("forbidden outcome-bearing path entered H9A allowlist")
    observed: dict[str, str] = {}
    for name, expected in EXPECTED_HASHES.items():
        path = INPUT_PATHS[name]
        if not path.is_file():
            raise RuntimeError(f"missing immutable H9A input: {name}")
        observed[name] = sha256_file(path)
        if observed[name] != expected:
            raise RuntimeError(f"immutable H9A input hash mismatch: {name}")
    if INPUT_PATHS["phase_a_manifest"].stat().st_size != EXPECTED_MANIFEST_BYTES:
        raise RuntimeError("Phase-A manifest byte count mismatch")
    if sha256_file(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise RuntimeError("locked protocol hash mismatch")
    return observed


def load_phase_a_contract() -> tuple[dict[str, Any], list[str]]:
    result = read_json(INPUT_PATHS["phase_a_result"])
    completion = read_json(INPUT_PATHS["phase_a_completion"])
    cohort = result.get("cohort", {})
    qids = cohort.get("sampled_qids")
    if (
        result.get("schema_version") != "h6_phase_a_coverage.python.v1"
        or cohort.get("manifest_sha256") != EXPECTED_HASHES["phase_a_manifest"]
        or cohort.get("eligible_impressions") != EXPECTED_IMPRESSIONS
        or cohort.get("distinct_users") != EXPECTED_USERS
        or cohort.get("candidates") != EXPECTED_CANDIDATES
        or cohort.get("manifest_contains_candidate_suffix") is not False
        or cohort.get("known_news") != EXPECTED_NEWS_ROWS
        or cohort.get("news_with_sampled_anchor") != 12_060
    ):
        raise RuntimeError("Phase-A result contract mismatch")
    if not isinstance(qids, list) or len(qids) != SAMPLE_SIZE or len(set(qids)) != SAMPLE_SIZE:
        raise RuntimeError("Phase-A ordered anchor list is malformed")
    if any(not isinstance(qid, str) or QID_PATTERN.fullmatch(qid) is None for qid in qids):
        raise RuntimeError("Phase-A ordered anchor identifier is invalid")
    outputs = completion.get("outputs", {})
    if (
        completion.get("status") != "H6_COVERAGE_RUN_002_COMPLETE"
        or completion.get("completion_marker_is_last") is not True
        or outputs.get("primary_result", {}).get("sha256") != EXPECTED_HASHES["phase_a_result"]
        or outputs.get("primary_manifest", {}).get("sha256") != EXPECTED_HASHES["phase_a_manifest"]
    ):
        raise RuntimeError("Phase-A completion chain mismatch")
    return result, [str(qid) for qid in qids]


def load_relations() -> frozenset[str]:
    values: set[str] = set()
    rows = 0
    with INPUT_PATHS["relations"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            rows += 1
            relation = raw_line.split("\t", 1)[0]
            if PROPERTY_PATTERN.fullmatch(relation) is None or relation in values:
                raise RuntimeError("relation vocabulary contains an invalid or duplicate property")
            values.add(relation)
    if rows != EXPECTED_RELATIONS or len(values) != EXPECTED_RELATIONS:
        raise RuntimeError("relation vocabulary cardinality mismatch")
    return frozenset(values)


@dataclass(frozen=True)
class GraphState:
    view: str
    state: str
    anchor_facts: tuple[frozenset[str], ...]
    r_exact: tuple[tuple[Fraction, ...], ...]
    c_exact: tuple[tuple[Fraction, ...], ...]
    diagnostic: Mapping[str, int]
    anchor_fact_overlap: tuple[tuple[bool, ...], ...]


def fact_anchors(anchor_facts: Sequence[Iterable[str]]) -> dict[str, tuple[int, ...]]:
    mapping: dict[str, list[int]] = {}
    for anchor, facts in enumerate(anchor_facts):
        for fact in facts:
            mapping.setdefault(fact, []).append(anchor)
    return {fact: tuple(indices) for fact, indices in mapping.items()}


def assemble_rational_operator(
    anchor_facts: Sequence[frozenset[str]],
) -> tuple[tuple[tuple[Fraction, ...], ...], tuple[tuple[Fraction, ...], ...], dict[str, int]]:
    by_fact = fact_anchors(anchor_facts)
    r = [[Fraction(0) for _ in range(SAMPLE_SIZE)] for _ in range(SAMPLE_SIZE)]
    c = [[Fraction(0) for _ in range(SAMPLE_SIZE)] for _ in range(SAMPLE_SIZE)]
    shared_nodes = 0
    shared_incidences = 0
    maximum_degree = 0
    for anchors in by_fact.values():
        degree = len(anchors)
        maximum_degree = max(maximum_degree, degree)
        if degree > 1:
            shared_nodes += 1
            shared_incidences += degree
        inverse = Fraction(1, degree)
        for first in anchors:
            r[first][first] += 1
            for second in anchors:
                c[first][second] += inverse
                r[first][second] -= inverse
        if degree == 1:
            only = anchors[0]
            if r[only][only] < 0:
                raise RuntimeError("singleton contribution identity failed")

    # Independent clique expansion: sum_{a<b}(e_a-e_b)(e_a-e_b)^T/d.
    independent = [[Fraction(0) for _ in range(SAMPLE_SIZE)] for _ in range(SAMPLE_SIZE)]
    for anchors in by_fact.values():
        inverse = Fraction(1, len(anchors))
        for left_position, left in enumerate(anchors):
            for right in anchors[left_position + 1 :]:
                independent[left][left] += inverse
                independent[right][right] += inverse
                independent[left][right] -= inverse
                independent[right][left] -= inverse
    if independent != r:
        raise RuntimeError("exact incidence and clique operator assemblies differ")
    if any(r[row][column] != r[column][row] for row in range(SAMPLE_SIZE) for column in range(SAMPLE_SIZE)):
        raise RuntimeError("exact operator is asymmetric")
    if any(sum(r[row], Fraction(0)) != 0 for row in range(SAMPLE_SIZE)):
        raise RuntimeError("exact operator row sum is nonzero")
    diagnostic = {
        "edges": sum(len(facts) for facts in anchor_facts),
        "fact_nodes": len(by_fact),
        "shared_fact_nodes": shared_nodes,
        "shared_incidences": shared_incidences,
        "maximum_fact_degree": maximum_degree,
    }
    return tuple(tuple(row) for row in r), tuple(tuple(row) for row in c), diagnostic


def load_graph_states(qids: Sequence[str], relations: frozenset[str]) -> dict[tuple[str, str], GraphState]:
    rows_by_qid: dict[str, Any] = {}
    with INPUT_PATHS["facts"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            qid = str(row.get("qid", ""))
            if QID_PATTERN.fullmatch(qid) is None or qid in rows_by_qid or row.get("api_ok") is not True:
                raise RuntimeError("H5 fact ledger has invalid, duplicate, or unresolved anchor")
            rows_by_qid[qid] = row
    if set(rows_by_qid) != set(qids) or len(rows_by_qid) != SAMPLE_SIZE:
        raise RuntimeError("H5 fact ledger does not match the frozen ordered anchors")

    endpoint: dict[str, list[frozenset[str]]] = {"historical": [], "current": []}
    for qid in qids:
        row = rows_by_qid[qid]
        for state in ("historical", "current"):
            source = row.get(state, {}).get("facts")
            if not isinstance(source, list) or len(source) != len(set(source)):
                raise RuntimeError("H5 endpoint fact list is malformed or duplicated")
            retained: set[str] = set()
            for raw_fact in source:
                match = FACT_PATTERN.fullmatch(str(raw_fact))
                if match is None:
                    raise RuntimeError("H5 fact signature is invalid")
                if match.group(1) in relations:
                    retained.add(str(raw_fact))
            endpoint[state].append(frozenset(retained))

    removed_indices = {qids.index(qid) for qid in REMOVED_ANCHOR_IDS}
    result: dict[tuple[str, str], GraphState] = {}
    expected_counts = {
        ("primary_relation_vocabulary", "historical"): (4575, 3771, 401, 1205),
        ("primary_relation_vocabulary", "current"): (5886, 4724, 487, 1649),
        ("primary_relation_vocabulary", "intersection"): (4381, 3606, 391, 1166),
        ("primary_relation_vocabulary", "union"): (6080, 4884, 501, 1697),
        ("metadata_blocklist", "historical"): (4482, 3723, 392, 1151),
        ("metadata_blocklist", "current"): (5457, 4516, 458, 1399),
        ("metadata_blocklist", "intersection"): (4300, 3565, 382, 1117),
        ("metadata_blocklist", "union"): (5639, 4670, 471, 1440),
        ("remove_q30_q22686", "historical"): (3714, 3208, 221, 727),
        ("remove_q30_q22686", "current"): (4891, 4092, 324, 1123),
        ("remove_q30_q22686", "intersection"): (3554, 3075, 209, 688),
        ("remove_q30_q22686", "union"): (5051, 4221, 339, 1169),
    }
    for view in VIEW_NAMES:
        historical: list[frozenset[str]] = []
        current: list[frozenset[str]] = []
        for index in range(SAMPLE_SIZE):
            old = endpoint["historical"][index]
            new = endpoint["current"][index]
            if view == "metadata_blocklist":
                old = frozenset(fact for fact in old if fact.split("|", 1)[0] not in METADATA_BLOCKLIST)
                new = frozenset(fact for fact in new if fact.split("|", 1)[0] not in METADATA_BLOCKLIST)
            elif view == "remove_q30_q22686" and index in removed_indices:
                old, new = frozenset(), frozenset()
            historical.append(old)
            current.append(new)
        states = {
            "intersection": tuple(historical[i] & current[i] for i in range(SAMPLE_SIZE)),
            "historical": tuple(historical),
            "current": tuple(current),
            "union": tuple(historical[i] | current[i] for i in range(SAMPLE_SIZE)),
        }
        for index in range(SAMPLE_SIZE):
            if not states["intersection"][index].issubset(states["historical"][index]):
                raise RuntimeError("exact I subset H inclusion failed")
            if not states["intersection"][index].issubset(states["current"][index]):
                raise RuntimeError("exact I subset C inclusion failed")
            if not states["historical"][index].issubset(states["union"][index]):
                raise RuntimeError("exact H subset U inclusion failed")
            if not states["current"][index].issubset(states["union"][index]):
                raise RuntimeError("exact C subset U inclusion failed")
        for state, anchor_facts in states.items():
            r, c, diagnostic = assemble_rational_operator(anchor_facts)
            locked = expected_counts[(view, state)]
            observed = (
                diagnostic["edges"], diagnostic["fact_nodes"],
                diagnostic["shared_fact_nodes"], diagnostic["shared_incidences"],
            )
            if observed != locked:
                raise RuntimeError(f"locked graph audit count mismatch for {view}/{state}: {observed}")
            overlap = tuple(
                tuple(bool(anchor_facts[left].intersection(anchor_facts[right])) for right in range(SAMPLE_SIZE))
                for left in range(SAMPLE_SIZE)
            )
            result[(view, state)] = GraphState(
                view, state, anchor_facts, r, c, diagnostic, overlap
            )
    return result


@dataclass(frozen=True)
class NewsPatterns:
    news_to_pattern: Mapping[str, int]
    patterns: tuple[tuple[int, ...], ...]
    z_exact: tuple[tuple[Fraction, ...], ...]
    zhat: Any
    delta_z: Any
    z_l1_up: Any
    delta_z_l1_up: Any


def nearest_float_radius(exact: Fraction, center: float | None = None) -> tuple[float, float]:
    np = load_numpy()
    chosen = float(exact) if center is None else float(center)
    if not math.isfinite(chosen):
        raise RuntimeError("nonfinite rational-to-binary64 center")
    delta = abs(Fraction.from_float(chosen) - exact)
    radius = float(delta)
    while Fraction.from_float(radius) < delta:
        radius = float(np.nextafter(radius, math.inf))
    if Fraction.from_float(radius) < delta:
        raise RuntimeError("outward binary64 radius construction failed")
    return chosen, radius


def outward_fraction_interval(exact: Fraction) -> tuple[float, float, float]:
    np = load_numpy()
    center = float(exact)
    represented = Fraction.from_float(center)
    lower = center if represented <= exact else float(np.nextafter(center, -math.inf))
    upper = center if represented >= exact else float(np.nextafter(center, math.inf))
    if Fraction.from_float(lower) > exact or Fraction.from_float(upper) < exact:
        raise RuntimeError("outward exact-Fraction interval failed")
    return center, lower, upper


def parse_news_patterns(qids: Sequence[str]) -> NewsPatterns:
    np = load_numpy()
    qid_index = {qid: index for index, qid in enumerate(qids)}
    news_to_pattern: dict[str, int] = {}
    pattern_to_id: dict[tuple[int, ...], int] = {}
    patterns: list[tuple[int, ...]] = []
    rows = 0
    supported = 0
    with INPUT_PATHS["news"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            fields = raw_line.rstrip("\r\n").split("\t", 7)
            if len(fields) != 8:
                raise RuntimeError("news row does not have exactly eight fields")
            news_id = fields[0]
            if NEWS_ID_PATTERN.fullmatch(news_id) is None or news_id in news_to_pattern:
                raise RuntimeError("news input has invalid or duplicate news ID")
            anchors: set[int] = set()
            for column in (6, 7):
                annotations = json.loads(fields[column])
                if not isinstance(annotations, list):
                    raise RuntimeError("news annotation JSON is not an array")
                for annotation in annotations:
                    if not isinstance(annotation, dict):
                        continue
                    qid = str(annotation.get("WikidataId", "")).strip()
                    if qid not in qid_index:
                        continue
                    try:
                        confidence = float(annotation.get("Confidence"))
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(confidence) and confidence >= MINIMUM_CONFIDENCE:
                        anchors.add(qid_index[qid])
            pattern = tuple(sorted(anchors))
            if pattern not in pattern_to_id:
                pattern_to_id[pattern] = len(patterns)
                patterns.append(pattern)
            news_to_pattern[news_id] = pattern_to_id[pattern]
            supported += bool(pattern)
            rows += 1
    if rows != EXPECTED_NEWS_ROWS or len(news_to_pattern) != EXPECTED_NEWS_ROWS or supported != 12_060:
        raise RuntimeError("locked news support counts do not reproduce")
    if len(patterns) != EXPECTED_PATTERNS or () not in pattern_to_id:
        raise RuntimeError("locked first-occurrence news patterns do not reproduce")
    z_exact: list[tuple[Fraction, ...]] = []
    zhat = np.zeros((len(patterns), SAMPLE_SIZE), dtype=np.float64)
    delta_z = np.zeros_like(zhat)
    for pattern_id, anchors in enumerate(patterns):
        row = [Fraction(0) for _ in range(SAMPLE_SIZE)]
        if anchors:
            value = Fraction(1, len(anchors))
            for anchor in anchors:
                row[anchor] = value
                center, radius = nearest_float_radius(value)
                zhat[pattern_id, anchor] = center
                delta_z[pattern_id, anchor] = radius
        z_exact.append(tuple(row))
    if not np.all(np.isfinite(zhat)) or not np.all(np.isfinite(delta_z)):
        raise RuntimeError("news-pattern binary64 conversion is nonfinite")
    z_l1_up = np.asarray(
        [up_sum(abs(float(value)) for value in row) for row in zhat], dtype=np.float64
    )
    delta_z_l1_up = np.asarray(
        [up_sum(float(value) for value in row) for row in delta_z], dtype=np.float64
    )
    return NewsPatterns(
        news_to_pattern, tuple(patterns), tuple(z_exact), zhat, delta_z,
        z_l1_up, delta_z_l1_up,
    )


def exact_matrix_key(matrix: Sequence[Sequence[Fraction]], gamma: Fraction) -> tuple[Any, ...]:
    return (gamma.numerator, gamma.denominator) + tuple(
        (value.numerator, value.denominator) for row in matrix for value in row
    )


def exact_q(r_exact: Sequence[Sequence[Fraction]], gamma: Fraction) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(
        tuple(value + (gamma if row == column else 0) for column, value in enumerate(source))
        for row, source in enumerate(r_exact)
    )


def fraction_matrix_float(matrix: Sequence[Sequence[Fraction]]) -> Any:
    np = load_numpy()
    return np.asarray([[float(value) for value in row] for row in matrix], dtype=np.float64)


def mpf_tuple_fraction(value: Any) -> Fraction:
    if not isinstance(value, tuple) or len(value) != 4:
        raise RuntimeError("unexpected mpmath binary tuple")
    sign, mantissa, exponent, bit_count = value
    if not all(isinstance(int(item), int) for item in (sign, mantissa, exponent, bit_count)):
        raise RuntimeError("non-integral mpmath tuple component")
    sign_i, mantissa_i, exponent_i, bit_count_i = int(sign), int(mantissa), int(exponent), int(bit_count)
    if sign_i not in (0, 1) or mantissa_i < 0 or bit_count_i < 0:
        raise RuntimeError("nonfinite or malformed mpmath tuple")
    result = Fraction(mantissa_i)
    result = result * (2 ** exponent_i) if exponent_i >= 0 else result / (2 ** (-exponent_i))
    return -result if sign_i else result


def interval_inverse_box(
    q_exact: Sequence[Sequence[Fraction]], digits: int
) -> tuple[list[list[Fraction]], list[list[Fraction]]]:
    _, iv = load_mpmath()
    iv.dps = digits
    source = iv.matrix([
        [iv.mpf(value.numerator) / iv.mpf(value.denominator) for value in row]
        for row in q_exact
    ])
    inverse = iv.inverse(source)
    lower: list[list[Fraction]] = []
    upper: list[list[Fraction]] = []
    for row in range(SAMPLE_SIZE):
        lower_row: list[Fraction] = []
        upper_row: list[Fraction] = []
        for column in range(SAMPLE_SIZE):
            interval = inverse[row, column]
            lo, hi = interval._mpi_
            lo_fraction = mpf_tuple_fraction(lo)
            hi_fraction = mpf_tuple_fraction(hi)
            if lo_fraction > hi_fraction:
                raise RuntimeError("interval inverse has reversed endpoint")
            lower_row.append(lo_fraction)
            upper_row.append(hi_fraction)
        lower.append(lower_row)
        upper.append(upper_row)
    # Direct interval residual enclosure: exact Q times the returned box contains I.
    for row in range(SAMPLE_SIZE):
        for column in range(SAMPLE_SIZE):
            lo_sum = Fraction(0)
            hi_sum = Fraction(0)
            for inner in range(SAMPLE_SIZE):
                coefficient = q_exact[row][inner]
                if coefficient >= 0:
                    lo_sum += coefficient * lower[inner][column]
                    hi_sum += coefficient * upper[inner][column]
                else:
                    lo_sum += coefficient * upper[inner][column]
                    hi_sum += coefficient * lower[inner][column]
            target = Fraction(int(row == column))
            if not (lo_sum <= target <= hi_sum):
                raise RuntimeError("interval inverse does not enclose an identity residual")
    return lower, upper


def point_inverse(q_exact: Sequence[Sequence[Fraction]], digits: int = 160) -> list[list[Any]]:
    mp, _ = load_mpmath()
    with mp.workdps(digits):
        source = mp.matrix([
            [mp.mpf(value.numerator) / mp.mpf(value.denominator) for value in row]
            for row in q_exact
        ])
        inverse = mp.inverse(source)
        return [[+inverse[row, column] for column in range(SAMPLE_SIZE)] for row in range(SAMPLE_SIZE)]


def next_up(value: float) -> float:
    np = load_numpy()
    result = float(np.nextafter(float(value), math.inf))
    if not math.isfinite(result):
        raise RuntimeError("nonfinite upward bound")
    return result


def next_down(value: float) -> float:
    np = load_numpy()
    result = float(np.nextafter(float(value), -math.inf))
    if not math.isfinite(result):
        raise RuntimeError("nonfinite downward bound")
    return result


def array_up(values: Any) -> Any:
    np = load_numpy()
    source = np.asarray(values, dtype=np.float64)
    if np.any(~np.isfinite(source)) or np.any(source < 0.0):
        raise RuntimeError("invalid vectorized nonnegative bound")
    result = np.nextafter(source, math.inf)
    if np.any(~np.isfinite(result)):
        raise RuntimeError("nonfinite vectorized upward bound")
    return result


def up_sum(values: Iterable[float]) -> float:
    total = 0.0
    for value in values:
        if value < 0.0 or not math.isfinite(value):
            raise RuntimeError("invalid nonnegative bound term")
        total = next_up(total + float(value))
    return total


def up_product(*values: float) -> float:
    result = 1.0
    for value in values:
        if value < 0.0 or not math.isfinite(value):
            raise RuntimeError("invalid nonnegative bound factor")
        result = next_up(result * float(value))
    return result


def gamma_bound(length: int) -> float:
    exact = Fraction(length, 2 ** 53 - length)
    value = float(exact)
    while Fraction.from_float(value) < exact:
        value = next_up(value)
    return value


@dataclass
class InverseCache:
    key_sha256: str
    gamma: Fraction
    q_float: Any
    khat: Any
    delta_k: Any
    ahat: Any
    acholesky: Any
    apoint: Any
    aeigen: Any | None
    kpoint: list[list[Any]]
    tau_residual: float
    tau_score: float
    epsilon_cap: float
    z1: float
    rz1: float
    kmax: float
    dkmax: float
    bmax: float
    amax: float
    e_a: float
    diagnostics: dict[str, Any]


def exact_key_sha256(key: tuple[Any, ...]) -> str:
    return sha256_bytes(canonical_bytes(key))


def matrix_float_diagnostics(
    graphs: Mapping[tuple[str, str], GraphState]
) -> dict[str, Any]:
    np = load_numpy()
    result: dict[str, Any] = {}
    for view in VIEW_NAMES:
        matrices = {
            state: fraction_matrix_float(graphs[(view, state)].r_exact) for state in STATE_NAMES
        }
        tau_matrix = 1e-12 * max(1.0, float(np.linalg.norm(matrices["union"], ord=2)))
        view_report: dict[str, Any] = {"tau_matrix": tau_matrix, "states": {}}
        for state, matrix in matrices.items():
            symmetry = float(np.max(np.abs(matrix - matrix.T)))
            row_sum = float(np.max(np.abs(np.sum(matrix, axis=1))))
            minimum_eigenvalue = float(np.min(np.linalg.eigvalsh((matrix + matrix.T) * 0.5)))
            exact_float = fraction_matrix_float(graphs[(view, state)].r_exact)
            assembly_error = float(np.max(np.abs(matrix - exact_float)))
            if (
                symmetry > tau_matrix
                or row_sum > tau_matrix
                or minimum_eigenvalue < -tau_matrix
                or assembly_error > tau_matrix
            ):
                raise RuntimeError(f"operator numerical theorem check failed for {view}/{state}")
            view_report["states"][state] = {
                **dict(graphs[(view, state)].diagnostic),
                "maximum_symmetry_error": symmetry,
                "maximum_row_sum_error": row_sum,
                "minimum_eigenvalue": minimum_eigenvalue,
                "independent_assembly_error": assembly_error,
            }
        loewner: dict[str, float] = {}
        for lower, upper in (
            ("intersection", "historical"), ("intersection", "current"),
            ("historical", "union"), ("current", "union"),
        ):
            difference = matrices[upper] - matrices[lower]
            minimum = float(np.min(np.linalg.eigvalsh((difference + difference.T) * 0.5)))
            if minimum < -tau_matrix:
                raise RuntimeError(f"Loewner eigendiagnostic failed for {view}/{lower}/{upper}")
            loewner[f"{lower}_to_{upper}_minimum_eigenvalue"] = minimum
        view_report["loewner"] = loewner
        result[view] = view_report
    return result


def build_inverse_cache(
    r_exact: Sequence[Sequence[Fraction]],
    gamma: Fraction,
    patterns: NewsPatterns,
    include_eigen: bool,
) -> InverseCache:
    np = load_numpy()
    q_exact = exact_q(r_exact, gamma)
    key = exact_matrix_key(r_exact, gamma)
    key_hash = exact_key_sha256(key)
    low80, high80 = interval_inverse_box(q_exact, 80)
    low160, high160 = interval_inverse_box(q_exact, 160)
    khat = np.empty((SAMPLE_SIZE, SAMPLE_SIZE), dtype=np.float64)
    delta_k = np.empty_like(khat)
    maximum_width = Fraction(0)
    for row in range(SAMPLE_SIZE):
        for column in range(SAMPLE_SIZE):
            if low160[row][column] < low80[row][column] or high160[row][column] > high80[row][column]:
                raise RuntimeError("160-digit inverse box is not nested in 80-digit box")
            width = high160[row][column] - low160[row][column]
            maximum_width = max(maximum_width, width)
            midpoint = (low160[row][column] + high160[row][column]) / 2
            center, _ = nearest_float_radius(midpoint)
            lower_neighbor = float(np.nextafter(center, -math.inf))
            upper_neighbor = float(np.nextafter(center, math.inf))
            center_error = abs(Fraction.from_float(center) - midpoint)
            if (
                abs(Fraction.from_float(lower_neighbor) - midpoint) < center_error
                or abs(Fraction.from_float(upper_neighbor) - midpoint) < center_error
            ):
                raise RuntimeError("inverse-box midpoint is not nearest binary64")
            needed = max(
                abs(Fraction.from_float(center) - low160[row][column]),
                abs(high160[row][column] - Fraction.from_float(center)),
            )
            radius = float(needed)
            while Fraction.from_float(radius) < needed:
                radius = next_up(radius)
            if (
                Fraction.from_float(center) - Fraction.from_float(radius) > low160[row][column]
                or Fraction.from_float(center) + Fraction.from_float(radius) < high160[row][column]
            ):
                raise RuntimeError("outward Khat radius does not contain decision box")
            khat[row, column] = center
            delta_k[row, column] = radius
    if maximum_width > Fraction(1, 2 ** 80):
        raise RuntimeError("160-digit inverse box exceeds frozen width")

    q_float = fraction_matrix_float(q_exact)
    r_float = fraction_matrix_float(r_exact)
    tau_score = 1e-10 * max(1.0, 1.0 / float(gamma))
    tau_residual = 1e-12 * max(1.0, float(np.linalg.norm(q_float, ord=2)))
    cholesky = np.linalg.cholesky(q_float)
    identity = np.eye(SAMPLE_SIZE, dtype=np.float64)
    k_cholesky = np.linalg.solve(cholesky.T, np.linalg.solve(cholesky, identity))
    cholesky_residual = float(np.max(np.abs(q_float @ k_cholesky - identity)))
    if cholesky_residual > tau_residual:
        raise RuntimeError("float64 Cholesky inverse residual exceeds frozen tolerance")
    kpoint = point_inverse(q_exact, 160)
    kpoint_float = np.asarray(
        [[float(kpoint[row][column]) for column in range(SAMPLE_SIZE)] for row in range(SAMPLE_SIZE)],
        dtype=np.float64,
    )
    point_residual = float(np.max(np.abs(q_float @ kpoint_float - identity)))
    if point_residual > tau_residual:
        raise RuntimeError("independent 160-digit point inverse residual exceeds frozen tolerance")
    eigen_cache = None
    if include_eigen:
        eigenvalues, eigenvectors = np.linalg.eigh((q_float + q_float.T) * 0.5)
        if float(np.min(eigenvalues)) <= 0.0:
            raise RuntimeError("deep-verifier eigendecomposition found nonpositive Q")
        k_eigen = (eigenvectors * (1.0 / eigenvalues)[None, :]) @ eigenvectors.T
        eigen_residual = float(np.max(np.abs(q_float @ k_eigen - identity)))
        if eigen_residual > tau_residual:
            raise RuntimeError("deep-verifier eigen inverse residual exceeds tolerance")
        eigen_cache = patterns.zhat @ k_eigen @ patterns.zhat.T
    ahat = (patterns.zhat @ khat) @ patterns.zhat.T
    acholesky = patterns.zhat @ k_cholesky @ patterns.zhat.T
    apoint = patterns.zhat @ kpoint_float @ patterns.zhat.T
    if not all(np.all(np.isfinite(value)) for value in (khat, delta_k, ahat, acholesky, apoint)):
        raise RuntimeError("inverse or pattern cache is nonfinite")
    tau_parity = tau_score / 8.0
    pattern_cholesky_parity = float(np.max(np.abs(ahat - acholesky)))
    pattern_point_parity = float(np.max(np.abs(ahat - apoint)))
    pattern_eigen_parity = (
        float(np.max(np.abs(ahat - eigen_cache))) if eigen_cache is not None else None
    )
    if (
        pattern_cholesky_parity > tau_parity
        or pattern_point_parity > tau_parity
        or (pattern_eigen_parity is not None and pattern_eigen_parity > tau_parity)
    ):
        raise RuntimeError("exhaustive pattern-cache parity exceeds tau_parity")

    z1 = float(np.max(patterns.z_l1_up))
    rz1 = float(np.max(patterns.delta_z_l1_up))
    kmax = next_up(float(np.max(np.abs(khat))))
    dkmax = next_up(float(np.max(delta_k)))
    b_hat = patterns.zhat @ khat
    bmax = next_up(float(np.max(np.abs(b_hat))))
    amax = next_up(float(np.max(np.abs(ahat))))
    gamma100 = gamma_bound(100)
    e_b = up_product(gamma100, z1, kmax)
    e_a = up_sum((up_product(e_b, z1), up_product(gamma100, bmax, z1)))
    epsilon_cap = (2.0 ** -38) * max(1.0, 1.0 / float(gamma))

    # Exhaustive 812-pattern w=0, b=-z_t self-energy interval audit.  The empty
    # incidence pattern is the protocol's exact graph-free zero branch.
    mp, _ = load_mpmath()
    maximum_self_discrepancy = 0.0
    maximum_self_delta_input = 0.0
    maximum_self_delta_round = 0.0
    maximum_self_delta_e = 0.0
    all_self_intervals_contained = True
    first_uncontained_pattern: int | None = None
    self_energy_supported_patterns = 0
    self_energy_empty_patterns = 0
    gamma8 = gamma_bound(8)
    self_kabsmax = next_up(kmax + dkmax)
    with mp.workdps(160):
        for pattern_id, anchors in enumerate(patterns.patterns):
            center = float(ahat[pattern_id, pattern_id])
            if not anchors:
                direct = mp.mpf(0)
                if center != 0.0:
                    raise RuntimeError("empty-pattern self-energy center is not graph-free zero")
                delta_e = 0.0
                lower = 0.0
                upper = 0.0
                self_energy_empty_patterns += 1
            else:
                degree = len(anchors)
                direct = mp.fsum(
                    kpoint[left][right] / (degree * degree)
                    for left in anchors for right in anchors
                )

                # Frozen specialization of the score enclosure: what=0 gives
                # rw1=rp1=0, v1=1, h=0, and delta_cache=eA.  Only the
                # candidate's own conversion radius enters rb1.
                rb1 = next_up(float(patterns.delta_z_l1_up[pattern_id]))
                vb1 = next_up(z1)
                vabs1 = up_sum((vb1, rb1))
                term_one = up_product(rb1, self_kabsmax, vabs1)
                term_two = up_product(vb1, dkmax, vabs1)
                term_three = up_product(vb1, kmax, rb1)
                delta_input = up_sum((term_one, term_two, term_three))
                delta_round = next_up(gamma8 * abs(center))
                delta_e = up_sum((delta_input, e_a, delta_round))
                lower = next_down(center - delta_e)
                upper = next_up(center + delta_e)
                maximum_self_delta_input = max(maximum_self_delta_input, delta_input)
                maximum_self_delta_round = max(maximum_self_delta_round, delta_round)
                maximum_self_delta_e = max(maximum_self_delta_e, delta_e)
                self_energy_supported_patterns += 1

            if delta_e > epsilon_cap / 4.0:
                raise RuntimeError("812-pattern self-energy delta_E exceeds epsilon cap")
            if not (mp.mpf(lower) <= direct <= mp.mpf(upper)):
                all_self_intervals_contained = False
                if first_uncontained_pattern is None:
                    first_uncontained_pattern = pattern_id
            discrepancy = float(abs(direct - mp.mpf(center)))
            maximum_self_discrepancy = max(maximum_self_discrepancy, discrepancy)
    if not all_self_intervals_contained:
        raise RuntimeError(
            f"812-pattern direct self-energy escaped outward interval at pattern "
            f"{first_uncontained_pattern}"
        )
    if maximum_self_discrepancy > epsilon_cap / 4.0:
        raise RuntimeError("812-pattern direct-50D self-energy audit exceeds epsilon cap")

    return InverseCache(
        key_hash, gamma, q_float, khat, delta_k, ahat, acholesky, apoint, eigen_cache,
        kpoint, tau_residual, tau_score, epsilon_cap, z1, rz1, kmax, dkmax, bmax,
        amax, e_a,
        {
            "key_sha256": key_hash,
            "gamma": f"{gamma.numerator}/{gamma.denominator}",
            "maximum_inverse_box_width_numerator": maximum_width.numerator,
            "maximum_inverse_box_width_denominator": maximum_width.denominator,
            "maximum_inverse_box_width": float(maximum_width),
            "cholesky_residual_max": cholesky_residual,
            "point160_residual_max": point_residual,
            "maximum_self_energy_center_discrepancy": maximum_self_discrepancy,
            "maximum_self_energy_delta_input": maximum_self_delta_input,
            "maximum_self_energy_delta_round": maximum_self_delta_round,
            "maximum_self_energy_delta_E": maximum_self_delta_e,
            "all_self_energy_intervals_contained": all_self_intervals_contained,
            "self_energy_patterns_checked": len(patterns.patterns),
            "self_energy_supported_patterns_checked": self_energy_supported_patterns,
            "self_energy_empty_patterns_checked": self_energy_empty_patterns,
            "tau_score": tau_score,
            "tau_parity": tau_parity,
            "tau_residual": tau_residual,
            "epsilon_cap": epsilon_cap,
            "r_spectral_norm": float(np.linalg.norm(r_float, ord=2)),
            "eA": e_a,
            "pattern_cache_parity": {
                "cholesky_max": pattern_cholesky_parity,
                "point160_max": pattern_point_parity,
            },
        },
    )


def build_all_caches(
    graphs: Mapping[tuple[str, str], GraphState],
    patterns: NewsPatterns,
    include_eigen: bool,
) -> tuple[dict[tuple[str, Fraction, str], InverseCache], dict[str, Any]]:
    unique: dict[tuple[Any, ...], InverseCache] = {}
    assigned: dict[tuple[str, Fraction, str], InverseCache] = {}
    for view in VIEW_NAMES:
        for gamma in GAMMAS:
            for state in STATE_NAMES:
                graph = graphs[(view, state)]
                key = exact_matrix_key(graph.r_exact, gamma)
                cache = unique.get(key)
                if cache is None:
                    cache = build_inverse_cache(graph.r_exact, gamma, patterns, include_eigen)
                    unique[key] = cache
                assigned[(view, gamma, state)] = cache
    return assigned, {
        "requested_state_caches": len(VIEW_NAMES) * len(GAMMAS) * len(STATE_NAMES),
        "unique_inverse_boxes": len(unique),
        "unique": [unique[key].diagnostics for key in sorted(unique, key=exact_key_sha256)],
    }


def validate_manifest_row(row: Any, raw_line: bytes, row_index: int) -> tuple[str, str, list[str], list[Any]]:
    if not raw_line.endswith(b"\n") or raw_line.endswith(b"\r\n"):
        raise RuntimeError("manifest line is not terminated by exactly LF")
    if MANIFEST_SUFFIX_PATTERN.search(raw_line):
        raise RuntimeError("candidate outcome suffix leaked into H9A manifest")
    if not isinstance(row, dict) or list(row) != ["i", "u", "h", "c"]:
        raise RuntimeError("manifest top-level schema/order mismatch")
    if json.dumps(
        row, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8") + b"\n" != raw_line:
        raise RuntimeError("manifest is not exact compact canonical JSON plus LF")
    impression_id, user_id = row["i"], row["u"]
    history, candidates = row["h"], row["c"]
    if not isinstance(impression_id, str) or not impression_id or not isinstance(user_id, str) or not user_id:
        raise RuntimeError(f"manifest identity is invalid at row {row_index}")
    if not isinstance(history, list) or not history or len(history) > 50:
        raise RuntimeError("manifest retained history is invalid")
    if any(not isinstance(item, str) or NEWS_ID_PATTERN.fullmatch(item) is None for item in history):
        raise RuntimeError("manifest history contains invalid news ID")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("manifest candidate list is empty or malformed")
    candidate_ids: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or list(candidate) != ["n", "v"]:
            raise RuntimeError("manifest candidate record schema/order mismatch")
        news_id = candidate["n"]
        views = candidate["v"]
        if not isinstance(news_id, str) or NEWS_ID_PATTERN.fullmatch(news_id) is None:
            raise RuntimeError("manifest candidate news ID is invalid")
        if not isinstance(views, list) or len(views) != len(VIEW_NAMES):
            raise RuntimeError("manifest H6 view list is malformed")
        for value in views:
            if (
                not isinstance(value, list) or len(value) != 4
                or not all(isinstance(rank, int) and rank >= 1 for rank in value[2:])
                or not all(isinstance(score, (int, float)) and math.isfinite(float(score)) for score in value[:2])
            ):
                raise RuntimeError("manifest H6 view tuple is malformed")
        candidate_ids.append(news_id)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise RuntimeError("candidate IDs are not unique within impression")
    return impression_id, user_id, [str(item) for item in history], candidates


def select_audit_rows() -> set[int]:
    ranked: list[tuple[bytes, int]] = []
    rows = 0
    with INPUT_PATHS["phase_a_manifest"].open("rb") as handle:
        for row_index, raw_line in enumerate(handle):
            row = json.loads(raw_line)
            impression_id, _, _, _ = validate_manifest_row(row, raw_line, row_index)
            digest = hashlib.sha256(
                AUDIT_PREFIX + impression_id.encode("utf-8") + b"\x00" + str(row_index).encode("ascii")
            ).digest()
            ranked.append((digest, row_index))
            rows += 1
    if rows != EXPECTED_IMPRESSIONS:
        raise RuntimeError("manifest row count mismatch during audit selection")
    ranked.sort(key=lambda item: (item[0], item[1]))
    selected = {row_index for _, row_index in ranked[:AUDIT_ROWS]}
    if len(selected) != AUDIT_ROWS:
        raise RuntimeError("fixed audit-row selection cardinality mismatch")
    return selected


@dataclass(frozen=True)
class HistoryProfile:
    support_patterns: tuple[int, ...]
    weights_exact: tuple[Fraction, ...]
    weights_float: Any
    delta_weights: Any
    p_exact: tuple[Fraction, ...]
    anchor_support: frozenset[int]
    p_norm_exact: Fraction


def make_history_profile(history: Sequence[str], patterns: NewsPatterns) -> HistoryProfile:
    np = load_numpy()
    counts: Counter[int] = Counter()
    nonempty = 0
    for news_id in history:
        if news_id not in patterns.news_to_pattern:
            raise RuntimeError("manifest history references unknown news")
        pattern_id = int(patterns.news_to_pattern[news_id])
        if patterns.patterns[pattern_id]:
            counts[pattern_id] += 1
            nonempty += 1
    if nonempty == 0:
        raise RuntimeError("locked history unexpectedly has no supported news")
    support = tuple(sorted(counts))
    weights_exact = tuple(Fraction(counts[index], nonempty) for index in support)
    weights_float = np.empty(len(support), dtype=np.float64)
    delta_weights = np.empty(len(support), dtype=np.float64)
    for position, exact in enumerate(weights_exact):
        center, radius = nearest_float_radius(exact)
        weights_float[position] = center
        delta_weights[position] = radius
    p = [Fraction(0) for _ in range(SAMPLE_SIZE)]
    for weight, pattern_id in zip(weights_exact, support, strict=True):
        anchors = patterns.patterns[pattern_id]
        value = Fraction(1, len(anchors))
        for anchor in anchors:
            p[anchor] += weight * value
    anchor_support = frozenset(index for index, value in enumerate(p) if value != 0)
    if not anchor_support or sum(p, Fraction(0)) != 1:
        raise RuntimeError("exact history simplex construction failed")
    p_norm = sum((p[index] * p[index] for index in anchor_support), Fraction(0))
    return HistoryProfile(
        support, weights_exact, weights_float, delta_weights, tuple(p), anchor_support, p_norm
    )


def exact_baseline(
    profile: HistoryProfile, candidate_pattern: int, gamma: Fraction, patterns: NewsPatterns
) -> tuple[Fraction, float, float, float]:
    p_norm = profile.p_norm_exact
    anchors = patterns.patterns[candidate_pattern]
    if anchors:
        degree = len(anchors)
        cross = sum((profile.p_exact[index] for index in anchors), Fraction(0)) / degree
        e0 = (p_norm - 2 * cross + Fraction(1, degree)) / gamma
    else:
        e0 = p_norm / gamma
    center, lower, upper = outward_fraction_interval(-e0)
    return e0, center, lower, upper


@dataclass
class StateScores:
    nominal: Any
    lower: Any
    upper: Any
    cholesky: Any
    point160: Any
    eigen: Any | None
    path_lower: Any
    path_upper: Any
    direct: Any
    maximum_delta_e: float
    maximum_delta_path: float
    maximum_audit_discrepancy: float
    maximum_parity_error: float


def cached_energy(
    cache_matrix: Any, support: Sequence[int], weights: Any, candidates: Any
) -> tuple[Any, Any, Any, float]:
    np = load_numpy()
    block = cache_matrix[np.ix_(support, support)]
    qhat = block @ weights
    phat = float(weights @ qhat)
    chats = weights @ cache_matrix[np.ix_(support, candidates)]
    energies = phat - 2.0 * chats + cache_matrix[candidates, candidates]
    return np.asarray(energies, dtype=np.float64), np.asarray(chats, dtype=np.float64), qhat, phat


def direct_mp_checks(
    cache: InverseCache,
    profile: HistoryProfile,
    candidate_patterns: Sequence[int],
    patterns: NewsPatterns,
    score_lower: Any,
    score_upper: Any,
    nominal: Any,
    path_lower: Any,
    path_upper: Any,
) -> float:
    mp, _ = load_mpmath()
    maximum = 0.0
    with mp.workdps(160):
        p = [mp.mpf(value.numerator) / mp.mpf(value.denominator) for value in profile.p_exact]
        support = tuple(profile.anchor_support)
        p_energy = mp.fsum(
            p[left] * cache.kpoint[left][right] * p[right]
            for left in support for right in support
        )
        for position, pattern_id in enumerate(candidate_patterns):
            anchors = patterns.patterns[pattern_id]
            if not anchors:
                continue
            degree = len(anchors)
            cross = mp.fsum(
                p[left] * cache.kpoint[left][right]
                for left in support for right in anchors
            ) / degree
            self_energy = mp.fsum(
                cache.kpoint[left][right] for left in anchors for right in anchors
            ) / (degree * degree)
            energy = p_energy - 2 * cross + self_energy
            score = -energy
            if not (mp.mpf(score_lower[position]) <= score <= mp.mpf(score_upper[position])):
                raise RuntimeError("160-digit direct score escaped outward cache interval")
            if not (mp.mpf(path_lower[position]) <= cross <= mp.mpf(path_upper[position])):
                raise RuntimeError("160-digit direct path term escaped outward cache interval")
            maximum = max(maximum, abs(float(score) - float(nominal[position])))
    return maximum


def score_state(
    cache: InverseCache,
    profile: HistoryProfile,
    unique_patterns: Sequence[int],
    patterns: NewsPatterns,
    direct_pattern_cache: Any,
    baseline_by_pattern: Mapping[int, tuple[Fraction, float, float, float]],
    audit: bool,
) -> StateScores:
    np = load_numpy()
    candidates = np.asarray(unique_patterns, dtype=np.int64)
    support = tuple(profile.support_patterns)
    what = profile.weights_float
    energies, chats, qhat, phat = cached_energy(cache.ahat, support, what, candidates)
    chol_energies, _, _, _ = cached_energy(cache.acholesky, support, what, candidates)
    point_energies, _, _, _ = cached_energy(cache.apoint, support, what, candidates)
    eigen_energies = None
    if cache.aeigen is not None:
        eigen_energies, _, _, _ = cached_energy(cache.aeigen, support, what, candidates)
    direct_values = what @ direct_pattern_cache[np.ix_(support, candidates)]

    count = len(unique_patterns)
    nominal = np.empty(count, dtype=np.float64)
    lower = np.empty(count, dtype=np.float64)
    upper = np.empty(count, dtype=np.float64)
    cholesky_scores = np.empty(count, dtype=np.float64)
    point_scores = np.empty(count, dtype=np.float64)
    eigen_scores = np.empty(count, dtype=np.float64) if eigen_energies is not None else None
    path_lower = np.empty(count, dtype=np.float64)
    path_upper = np.empty(count, dtype=np.float64)

    what1 = up_sum(abs(float(value)) for value in what)
    rw1 = up_sum(float(value) for value in profile.delta_weights)
    rp1 = up_sum((rw1, up_product(what1, cache.rz1)))
    v1 = next_up(what1 + 1.0)
    vb1 = up_product(v1, cache.z1)
    kabsmax = next_up(cache.kmax + cache.dkmax)
    delta_cache = up_product(cache.e_a, v1, v1)
    path_cache = up_product(cache.e_a, what1)
    h = len(support)
    gamma2h = gamma_bound(2 * h)
    qinf = next_up(float(np.max(np.abs(qhat)))) if len(qhat) else 0.0
    eq = up_product(gamma2h, cache.amax, what1)
    ep = up_sum((up_product(what1, eq), up_product(gamma2h, what1, qinf)))
    ec = up_product(gamma2h, what1, cache.amax)
    supported = np.asarray([bool(patterns.patterns[index]) for index in unique_patterns], dtype=np.bool_)
    unsupported = ~supported
    baseline_center = np.asarray([baseline_by_pattern[index][1] for index in unique_patterns], dtype=np.float64)
    baseline_lower = np.asarray([baseline_by_pattern[index][2] for index in unique_patterns], dtype=np.float64)
    baseline_upper = np.asarray([baseline_by_pattern[index][3] for index in unique_patterns], dtype=np.float64)
    e0_float = np.asarray([float(baseline_by_pattern[index][0]) for index in unique_patterns], dtype=np.float64)
    rx1 = patterns.delta_z_l1_up[candidates]
    rb1 = array_up(rp1 + rx1)
    vabs1 = array_up(vb1 + rb1)
    term_one = array_up(array_up(rb1 * kabsmax) * vabs1)
    term_two = array_up(array_up(vb1 * cache.dkmax) * vabs1)
    term_three = array_up(array_up(vb1 * cache.kmax) * rb1)
    delta_input = array_up(array_up(term_one + term_two) + term_three)
    ef_sum = array_up(array_up(abs(phat) + array_up(2.0 * np.abs(chats))) + np.abs(cache.ahat[candidates, candidates]))
    ef = array_up(gamma_bound(8) * ef_sum)
    delta_round = array_up(array_up(ep + up_product(2.0, ec)) + ef)
    delta_e = array_up(array_up(delta_input + delta_cache) + delta_round)
    px1 = up_product(what1, cache.z1)
    xx1 = patterns.z_l1_up[candidates]
    xabs1 = array_up(xx1 + rx1)
    path_one = array_up(array_up(rp1 * kabsmax) * xabs1)
    path_two = array_up(array_up(px1 * cache.dkmax) * xabs1)
    path_three = array_up(array_up(px1 * cache.kmax) * rx1)
    path_round = up_product(gamma2h, what1, cache.amax)
    delta_path = array_up(
        array_up(array_up(array_up(path_one + path_two) + path_three) + path_cache) + path_round
    )
    if np.any(delta_e[supported] > cache.epsilon_cap / 4.0) or np.any(
        delta_path[supported] > cache.epsilon_cap / 4.0
    ):
        raise RuntimeError("frozen score/path enclosure exceeds epsilon cap")
    maximum_delta_e = float(np.max(delta_e[supported])) if np.any(supported) else 0.0
    maximum_delta_path = float(np.max(delta_path[supported])) if np.any(supported) else 0.0
    nominal[:] = -energies
    lower[:] = np.nextafter(-(energies + delta_e), -math.inf)
    upper[:] = np.nextafter(-(energies - delta_e), math.inf)
    cholesky_scores[:] = -chol_energies
    point_scores[:] = -point_energies
    if eigen_scores is not None and eigen_energies is not None:
        eigen_scores[:] = -eigen_energies
    path_lower[:] = np.nextafter(chats - delta_path, -math.inf)
    path_upper[:] = np.nextafter(chats + delta_path, math.inf)
    nominal[unsupported] = baseline_center[unsupported]
    lower[unsupported] = baseline_lower[unsupported]
    upper[unsupported] = baseline_upper[unsupported]
    cholesky_scores[unsupported] = baseline_center[unsupported]
    point_scores[unsupported] = baseline_center[unsupported]
    if eigen_scores is not None:
        eigen_scores[unsupported] = baseline_center[unsupported]
    path_lower[unsupported] = 0.0
    path_upper[unsupported] = 0.0
    if np.any(energies[supported] > e0_float[supported] + cache.tau_residual):
        raise RuntimeError("KG residual is negative beyond frozen tolerance")
    if not all(np.all(np.isfinite(value)) for value in (
        nominal, lower, upper, cholesky_scores, point_scores, path_lower, path_upper, direct_values
    )):
        raise RuntimeError("nonfinite state score or bound")
    parity_values = [
        float(np.max(np.abs(nominal - cholesky_scores))),
        float(np.max(np.abs(nominal - point_scores))),
    ]
    if eigen_scores is not None:
        eigen_parity = float(np.max(np.abs(nominal - eigen_scores)))
        if eigen_parity > cache.tau_score / 8.0:
            raise RuntimeError("deep eigen row-score parity exceeds tau_parity")
    maximum_parity = max(parity_values, default=0.0)
    if maximum_parity > cache.tau_score / 8.0:
        raise RuntimeError("exhaustive row-score parity exceeds tau_parity")
    maximum_audit = 0.0
    if audit:
        maximum_audit = direct_mp_checks(
            cache, profile, unique_patterns, patterns, lower, upper, nominal, path_lower, path_upper
        )
        if maximum_audit > cache.epsilon_cap / 4.0:
            raise RuntimeError("fixed-row 160-digit direct audit exceeds epsilon cap")
    return StateScores(
        nominal, lower, upper, cholesky_scores, point_scores, eigen_scores,
        path_lower, path_upper, np.asarray(direct_values, dtype=np.float64),
        maximum_delta_e, maximum_delta_path, maximum_audit,
        maximum_parity,
    )


def tolerance_groups(scores: Sequence[float], tau: float) -> list[list[int]]:
    order = sorted(range(len(scores)), key=lambda index: float(scores[index]), reverse=True)
    groups: list[list[int]] = []
    pending: list[int] = []
    reference: float | None = None
    for index in order:
        score = float(scores[index])
        if not math.isfinite(score):
            raise RuntimeError("ranking score is nonfinite")
        if reference is None:
            reference = score
        elif abs(reference - score) > tau:
            groups.append(pending)
            pending = []
            reference = score
        pending.append(index)
    if pending:
        groups.append(pending)
    return groups


def frozen_ranking(
    news_ids: Sequence[str], scores: Sequence[float], impression_id: str, tau: float,
    tie_hashes: Sequence[bytes] | None = None,
) -> tuple[list[int], tuple[tuple[int, ...], ...]]:
    if len(news_ids) != len(scores) or len(news_ids) != len(set(news_ids)):
        raise RuntimeError("ranking identifiers/scores have invalid cardinality")
    hashes = list(tie_hashes) if tie_hashes is not None else [
        hashlib.sha256(f"{SEED_TEXT}|{impression_id}|{news_id}".encode("utf-8")).digest()
        for news_id in news_ids
    ]
    if len(hashes) != len(news_ids):
        raise RuntimeError("precomputed ranking tie-key cardinality mismatch")
    groups = tolerance_groups(scores, tau)
    order: list[int] = []
    canonical_groups: list[tuple[int, ...]] = []
    for group in groups:
        canonical_group = tuple(sorted(group))
        canonical_groups.append(canonical_group)
        group.sort(key=lambda index: (hashes[index], news_ids[index]))
        order.extend(group)
    return order, tuple(canonical_groups)


def assert_rank_parity(
    news_ids: Sequence[str], impression_id: str, state_scores: StateScores, tau: float
) -> tuple[list[int], tuple[tuple[int, ...], ...]]:
    canonical = frozen_ranking(news_ids, state_scores.nominal, impression_id, tau)
    for label, scores in (
        ("float64 Cholesky", state_scores.cholesky),
        ("160-digit point", state_scores.point160),
        ("deep eigen", state_scores.eigen),
    ):
        if scores is not None and frozen_ranking(news_ids, scores, impression_id, tau) != canonical:
            raise RuntimeError(f"{label} ranking does not reproduce canonical groups/order")
    return canonical


def resolved_swap(
    top_left: set[int], top_right: set[int],
    left_lower: Sequence[float], left_upper: Sequence[float],
    right_lower: Sequence[float], right_upper: Sequence[float], tau: float,
) -> bool:
    if top_left == top_right:
        return False
    return any(
        float(left_lower[left]) > float(left_upper[right]) + tau
        and float(right_lower[right]) > float(right_upper[left]) + tau
        for left in top_left - top_right for right in top_right - top_left
    )


def top_hash(news_ids: Sequence[str], top: set[int]) -> str:
    payload = b"\x00".join(sorted((news_ids[index].encode("utf-8") for index in top)))
    return sha256_bytes(payload)


@dataclass
class ConfigAccumulator:
    view: str
    gamma: Fraction
    impressions: int = 0
    nonvacuous: int = 0
    guarded_score_changes: int = 0
    resolved_hc_top10_changes: int = 0
    resolved_baseline_h: int = 0
    resolved_baseline_c: int = 0
    certified: int = 0
    exposed: int = 0
    exposed_certified: int = 0
    certified_hc_disagreements: int = 0
    global_path_occurrences_h: int = 0
    global_path_occurrences_c: int = 0
    global_path_impressions_h: int = 0
    global_path_impressions_c: int = 0
    direct_positive_occurrences_h: int = 0
    direct_positive_occurrences_c: int = 0
    h6_top10_disagreements_h: int = 0
    h6_top10_disagreements_c: int = 0
    maximum_delta_e: float = 0.0
    maximum_delta_path: float = 0.0
    maximum_audit_discrepancy: float = 0.0
    maximum_parity_error: float = 0.0

    def report(self) -> dict[str, Any]:
        def rate(count: int, denominator: int) -> float | None:
            return count / denominator if denominator else None

        exposed_rate = rate(self.exposed_certified, self.exposed)
        return {
            "view": self.view,
            "gamma": f"{self.gamma.numerator}/{self.gamma.denominator}",
            "impressions": self.impressions,
            "nonvacuous_impressions": self.nonvacuous,
            "guarded_score_vector_change": {
                "count": self.guarded_score_changes,
                "rate": rate(self.guarded_score_changes, self.impressions),
            },
            "resolved_historical_current_top10_change": {
                "count": self.resolved_hc_top10_changes,
                "rate": rate(self.resolved_hc_top10_changes, self.nonvacuous),
            },
            "resolved_h9_vs_graph_free_top10": {
                "historical_count": self.resolved_baseline_h,
                "historical_rate": rate(self.resolved_baseline_h, self.nonvacuous),
                "current_count": self.resolved_baseline_c,
                "current_rate": rate(self.resolved_baseline_c, self.nonvacuous),
            },
            "certificate": {
                "count": self.certified,
                "rate": rate(self.certified, self.nonvacuous),
                "uncertainty_exposed_count": self.exposed,
                "uncertainty_exposed_rate": rate(self.exposed, self.nonvacuous),
                "exposed_certified_count": self.exposed_certified,
                "exposed_certified_rate": exposed_rate,
                "certified_historical_current_disagreements": self.certified_hc_disagreements,
            },
            "global_cofact_path": {
                "historical_occurrences": self.global_path_occurrences_h,
                "historical_occurrence_rate": rate(self.global_path_occurrences_h, EXPECTED_SUPPORTED),
                "historical_impressions": self.global_path_impressions_h,
                "current_occurrences": self.global_path_occurrences_c,
                "current_occurrence_rate": rate(self.global_path_occurrences_c, EXPECTED_SUPPORTED),
                "current_impressions": self.global_path_impressions_c,
            },
            "direct_one_hyperedge_diagnostic": {
                "historical_positive_occurrences": self.direct_positive_occurrences_h,
                "current_positive_occurrences": self.direct_positive_occurrences_c,
            },
            "h6_shared_fact_top10_disagreement": {
                "historical_count": self.h6_top10_disagreements_h,
                "historical_rate": rate(self.h6_top10_disagreements_h, self.nonvacuous),
                "current_count": self.h6_top10_disagreements_c,
                "current_rate": rate(self.h6_top10_disagreements_c, self.nonvacuous),
            },
            "numerical_enclosure": {
                "maximum_delta_E": self.maximum_delta_e,
                "maximum_delta_path": self.maximum_delta_path,
                "maximum_audit_center_discrepancy": self.maximum_audit_discrepancy,
                "maximum_score_parity_error": self.maximum_parity_error,
            },
        }


def direct_fact_overlap(
    graph: GraphState, history_support: frozenset[int], candidate_support: Sequence[int]
) -> bool:
    return any(
        graph.anchor_fact_overlap[left][right]
        for left in history_support for right in candidate_support
    )


@dataclass
class BatchCaches:
    order: tuple[tuple[str, Fraction, str], ...]
    index: Mapping[tuple[str, Fraction, str], int]
    caches: tuple[InverseCache, ...]
    ahat: Any
    acholesky: Any
    apoint: Any
    aeigen: Any | None
    tau_score: Any
    epsilon_cap: Any
    z1: Any
    rz1: Any
    kmax: Any
    dkmax: Any
    amax: Any
    e_a: Any
    gamma_index: Any


@dataclass
class BatchedRowScores:
    nominal: Any
    lower: Any
    upper: Any
    cholesky: Any
    point160: Any
    eigen: Any | None
    path_lower: Any
    path_upper: Any
    maximum_delta_e: Any
    maximum_delta_path: Any
    maximum_audit_discrepancy: Any
    maximum_parity_error: Any
    nominal_groups: tuple[tuple[tuple[int, ...], ...], ...]


@dataclass
class DirectBatch:
    order: tuple[tuple[str, str], ...]
    index: Mapping[tuple[str, str], int]
    matrices: Any


def prepare_batch_caches(
    caches: Mapping[tuple[str, Fraction, str], InverseCache], include_eigen: bool
) -> BatchCaches:
    np = load_numpy()
    order = tuple(
        (view, gamma, state)
        for view in VIEW_NAMES for gamma in GAMMAS for state in STATE_NAMES
    )
    sequence = tuple(caches[key] for key in order)
    ahat = np.stack([cache.ahat for cache in sequence], axis=0)
    acholesky = np.stack([cache.acholesky for cache in sequence], axis=0)
    apoint = np.stack([cache.apoint for cache in sequence], axis=0)
    aeigen = np.stack([cache.aeigen for cache in sequence], axis=0) if include_eigen else None
    result = BatchCaches(
        order,
        {key: position for position, key in enumerate(order)},
        sequence,
        ahat,
        acholesky,
        apoint,
        aeigen,
        np.asarray([cache.tau_score for cache in sequence], dtype=np.float64),
        np.asarray([cache.epsilon_cap for cache in sequence], dtype=np.float64),
        np.asarray([cache.z1 for cache in sequence], dtype=np.float64),
        np.asarray([cache.rz1 for cache in sequence], dtype=np.float64),
        np.asarray([cache.kmax for cache in sequence], dtype=np.float64),
        np.asarray([cache.dkmax for cache in sequence], dtype=np.float64),
        np.asarray([cache.amax for cache in sequence], dtype=np.float64),
        np.asarray([cache.e_a for cache in sequence], dtype=np.float64),
        np.asarray([GAMMAS.index(cache.gamma) for cache in sequence], dtype=np.int64),
    )
    # The stacked arrays are the sole hot-path caches. Release duplicate per-key
    # matrices so the deep verifier remains comfortably below 2 GiB.
    for cache in {id(item): item for item in sequence}.values():
        cache.ahat = None
        cache.acholesky = None
        cache.apoint = None
        cache.aeigen = None
    return result


def prepare_direct_batch(
    graphs: Mapping[tuple[str, str], GraphState], patterns: NewsPatterns
) -> DirectBatch:
    np = load_numpy()
    order = tuple((view, state) for view in VIEW_NAMES for state in STATE_NAMES)
    matrices = np.stack([
        (patterns.zhat @ fraction_matrix_float(graphs[key].c_exact)) @ patterns.zhat.T
        for key in order
    ], axis=0)
    return DirectBatch(order, {key: position for position, key in enumerate(order)}, matrices)


def batched_energy(
    matrices: Any, support: Sequence[int], weights: Any, candidates: Any
) -> tuple[Any, Any, Any, Any]:
    np = load_numpy()
    support_array = np.asarray(support, dtype=np.int64)
    block = matrices[:, support_array[:, None], support_array[None, :]]
    qhat = block @ weights
    phat = qhat @ weights
    cross_block = matrices[:, support_array[:, None], candidates[None, :]]
    chats = np.einsum("i,kiu->ku", weights, cross_block, optimize=False)
    diagonal = matrices[:, candidates, candidates]
    energies = phat[:, None] - 2.0 * chats + diagonal
    return energies, chats, qhat, phat


def groups_from_preorder(
    scores: Any, order: Sequence[int], tau: float
) -> tuple[tuple[int, ...], ...]:
    groups: list[tuple[int, ...]] = []
    pending: list[int] = []
    reference: float | None = None
    for raw_index in order:
        index = int(raw_index)
        score = float(scores[index])
        if reference is None:
            reference = score
        elif abs(reference - score) > tau:
            groups.append(tuple(sorted(pending)))
            pending = []
            reference = score
        pending.append(index)
    if pending:
        groups.append(tuple(sorted(pending)))
    return tuple(groups)


def batched_rank_group_parity(
    batch: BatchCaches,
    nominal: Any,
    cholesky: Any,
    point160: Any,
    eigen: Any | None,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    np = load_numpy()
    rank_indices = [
        position for position, (_, _, state) in enumerate(batch.order)
        if state in {"historical", "current"}
    ]
    sources = [nominal, cholesky, point160] + ([eigen] if eigen is not None else [])
    source_orders = [np.argsort(-source[rank_indices], axis=1, kind="stable") for source in sources]
    all_groups: list[tuple[tuple[int, ...], ...]] = [tuple() for _ in batch.order]
    for local, cache_index in enumerate(rank_indices):
        tau = float(batch.tau_score[cache_index])
        canonical = groups_from_preorder(
            nominal[cache_index], source_orders[0][local], tau
        )
        for label, source, orders in zip(
            ("Cholesky", "point160", "eigen"), sources[1:], source_orders[1:], strict=False
        ):
            if groups_from_preorder(source[cache_index], orders[local], tau) != canonical:
                raise RuntimeError(f"batched {label} first-score groups differ from canonical")
        all_groups[cache_index] = canonical
    return tuple(all_groups)


def score_batched_row(
    batch: BatchCaches,
    profile: HistoryProfile,
    unique_patterns: Sequence[int],
    patterns: NewsPatterns,
    baselines: Mapping[Fraction, tuple[Any, Any, Any, Any, Any]],
    audit: bool,
) -> BatchedRowScores:
    np = load_numpy()
    candidates = np.asarray(unique_patterns, dtype=np.int64)
    support = tuple(profile.support_patterns)
    what = profile.weights_float
    energies, chats, qhat, phat = batched_energy(batch.ahat, support, what, candidates)
    chol_energies, _, _, _ = batched_energy(batch.acholesky, support, what, candidates)
    point_energies, _, _, _ = batched_energy(batch.apoint, support, what, candidates)
    eigen_energies = None
    if batch.aeigen is not None:
        eigen_energies, _, _, _ = batched_energy(batch.aeigen, support, what, candidates)
    cache_count, candidate_count = energies.shape
    supported = np.asarray([bool(patterns.patterns[index]) for index in unique_patterns], dtype=np.bool_)
    unsupported = ~supported

    by_gamma_float: list[tuple[Any, Any, Any, Any]] = []
    for gamma in GAMMAS:
        mapping = baselines[gamma][4]
        by_gamma_float.append((
            np.asarray([float(mapping[index][0]) for index in unique_patterns], dtype=np.float64),
            np.asarray([mapping[index][1] for index in unique_patterns], dtype=np.float64),
            np.asarray([mapping[index][2] for index in unique_patterns], dtype=np.float64),
            np.asarray([mapping[index][3] for index in unique_patterns], dtype=np.float64),
        ))
    e0 = np.stack([item[0] for item in by_gamma_float], axis=0)[batch.gamma_index]
    baseline_centers = np.stack([item[1] for item in by_gamma_float], axis=0)[batch.gamma_index]
    baseline_lowers = np.stack([item[2] for item in by_gamma_float], axis=0)[batch.gamma_index]
    baseline_uppers = np.stack([item[3] for item in by_gamma_float], axis=0)[batch.gamma_index]

    what1 = up_sum(abs(float(value)) for value in what)
    rw1 = up_sum(float(value) for value in profile.delta_weights)
    rp1 = array_up(rw1 + array_up(what1 * batch.rz1))
    v1 = next_up(what1 + 1.0)
    vb1 = array_up(v1 * batch.z1)
    kabsmax = array_up(batch.kmax + batch.dkmax)
    delta_cache = array_up(array_up(batch.e_a * v1) * v1)
    path_cache = array_up(batch.e_a * what1)
    h = len(support)
    gamma2h = gamma_bound(2 * h)
    qinf = array_up(np.max(np.abs(qhat), axis=1))
    eq = array_up(array_up(gamma2h * batch.amax) * what1)
    ep = array_up(array_up(what1 * eq) + array_up(array_up(gamma2h * what1) * qinf))
    ec = array_up(array_up(gamma2h * what1) * batch.amax)
    rx1 = patterns.delta_z_l1_up[candidates][None, :]
    rb1 = array_up(rp1[:, None] + rx1)
    vabs1 = array_up(vb1[:, None] + rb1)
    delta_input = array_up(
        array_up(
            array_up(array_up(rb1 * kabsmax[:, None]) * vabs1)
            + array_up(array_up(vb1[:, None] * batch.dkmax[:, None]) * vabs1)
        )
        + array_up(array_up(vb1[:, None] * batch.kmax[:, None]) * rb1)
    )
    ef_sum = array_up(
        array_up(np.abs(phat)[:, None] + array_up(2.0 * np.abs(chats)))
        + np.abs(batch.ahat[:, candidates, candidates])
    )
    ef = array_up(gamma_bound(8) * ef_sum)
    delta_round = array_up(array_up(ep[:, None] + array_up(2.0 * ec)[:, None]) + ef)
    delta_e = array_up(array_up(delta_input + delta_cache[:, None]) + delta_round)
    px1 = array_up(what1 * batch.z1)
    xx1 = patterns.z_l1_up[candidates][None, :]
    xabs1 = array_up(xx1 + rx1)
    delta_path = array_up(
        array_up(
            array_up(
                array_up(array_up(rp1[:, None] * kabsmax[:, None]) * xabs1)
                + array_up(array_up(px1[:, None] * batch.dkmax[:, None]) * xabs1)
            )
            + array_up(array_up(px1[:, None] * batch.kmax[:, None]) * rx1)
        )
        + array_up(path_cache + array_up(array_up(gamma2h * what1) * batch.amax))[:, None]
    )
    if np.any(delta_e[:, supported] > batch.epsilon_cap[:, None] / 4.0) or np.any(
        delta_path[:, supported] > batch.epsilon_cap[:, None] / 4.0
    ):
        raise RuntimeError("batched frozen score/path enclosure exceeds epsilon cap")
    nominal = -energies
    lower = np.nextafter(-(energies + delta_e), -math.inf)
    upper = np.nextafter(-(energies - delta_e), math.inf)
    cholesky = -chol_energies
    point160 = -point_energies
    eigen = -eigen_energies if eigen_energies is not None else None
    path_lower = np.nextafter(chats - delta_path, -math.inf)
    path_upper = np.nextafter(chats + delta_path, math.inf)
    nominal[:, unsupported] = baseline_centers[:, unsupported]
    lower[:, unsupported] = baseline_lowers[:, unsupported]
    upper[:, unsupported] = baseline_uppers[:, unsupported]
    cholesky[:, unsupported] = baseline_centers[:, unsupported]
    point160[:, unsupported] = baseline_centers[:, unsupported]
    if eigen is not None:
        eigen[:, unsupported] = baseline_centers[:, unsupported]
    path_lower[:, unsupported] = 0.0
    path_upper[:, unsupported] = 0.0
    if np.any(energies[:, supported] > e0[:, supported] + np.asarray(
        [cache.tau_residual for cache in batch.caches], dtype=np.float64
    )[:, None]):
        raise RuntimeError("batched KG residual is negative beyond tolerance")

    parity = np.maximum(
        np.max(np.abs(nominal - cholesky), axis=1),
        np.max(np.abs(nominal - point160), axis=1),
    )
    if np.any(parity > batch.tau_score / 8.0):
        raise RuntimeError("batched exhaustive score parity exceeds tau_parity")
    if eigen is not None and np.any(np.max(np.abs(nominal - eigen), axis=1) > batch.tau_score / 8.0):
        raise RuntimeError("batched deep-eigen score parity exceeds tau_parity")
    nominal_groups = batched_rank_group_parity(
        batch, nominal, cholesky, point160, eigen
    )
    maximum_audit = np.zeros(cache_count, dtype=np.float64)
    if audit:
        first_by_identity: dict[int, int] = {}
        for cache_index, cache in enumerate(batch.caches):
            identity = id(cache)
            if identity in first_by_identity:
                first = first_by_identity[identity]
                if not (
                    np.array_equal(nominal[cache_index], nominal[first])
                    and np.array_equal(lower[cache_index], lower[first])
                    and np.array_equal(upper[cache_index], upper[first])
                    and np.array_equal(path_lower[cache_index], path_lower[first])
                    and np.array_equal(path_upper[cache_index], path_upper[first])
                ):
                    raise RuntimeError("deduplicated inverse cache produced nonidentical score rows")
                maximum_audit[cache_index] = maximum_audit[first]
                continue
            first_by_identity[identity] = cache_index
            maximum_audit[cache_index] = direct_mp_checks(
                cache, profile, unique_patterns, patterns,
                lower[cache_index], upper[cache_index], nominal[cache_index],
                path_lower[cache_index], path_upper[cache_index],
            )
            if maximum_audit[cache_index] > cache.epsilon_cap / 4.0:
                raise RuntimeError("batched fixed-row direct audit exceeds epsilon cap")
    maximum_delta_e = np.max(np.where(supported[None, :], delta_e, 0.0), axis=1)
    maximum_delta_path = np.max(np.where(supported[None, :], delta_path, 0.0), axis=1)
    return BatchedRowScores(
        nominal, lower, upper, cholesky, point160, eigen, path_lower, path_upper,
        maximum_delta_e, maximum_delta_path, maximum_audit, parity, nominal_groups,
    )


def score_direct_batched_row(
    direct: DirectBatch, profile: HistoryProfile, unique_patterns: Sequence[int]
) -> Any:
    np = load_numpy()
    candidates = np.asarray(unique_patterns, dtype=np.int64)
    support = np.asarray(profile.support_patterns, dtype=np.int64)
    block = direct.matrices[:, support[:, None], candidates[None, :]]
    values = np.einsum("i,kiu->ku", profile.weights_float, block, optimize=False)
    if np.any(~np.isfinite(values)):
        raise RuntimeError("batched direct one-hyperedge diagnostic is nonfinite")
    return values


def process_configuration_row(
    accumulator: ConfigAccumulator,
    batch: BatchCaches,
    row_scores: BatchedRowScores,
    direct_batch: DirectBatch,
    direct_scores: Any,
    patterns: NewsPatterns,
    impression_id: str,
    news_ids: Sequence[str],
    candidate_records: Sequence[Any],
    candidate_patterns: Sequence[int],
    unique_patterns: Sequence[int],
    occurrence_positions: Any,
    occurrences_by_unique: Sequence[Sequence[int]],
    tie_hashes: Sequence[bytes],
    baseline_center: Sequence[float],
    baseline_lower: Sequence[float],
    baseline_upper: Sequence[float],
    baseline_order: Sequence[int],
    global_eligibility: Mapping[tuple[str, str], Any],
) -> list[Any]:
    np = load_numpy()
    view, gamma = accumulator.view, accumulator.gamma
    expanded: dict[str, dict[str, Any]] = {}
    for state in STATE_NAMES:
        cache_index = batch.index[(view, gamma, state)]
        direct_index = direct_batch.index[(view, state)]
        expanded[state] = {
            "nominal": row_scores.nominal[cache_index, occurrence_positions],
            "lower": row_scores.lower[cache_index, occurrence_positions],
            "upper": row_scores.upper[cache_index, occurrence_positions],
            "path_lower": row_scores.path_lower[cache_index, occurrence_positions],
            "path_upper": row_scores.path_upper[cache_index, occurrence_positions],
            "direct": direct_scores[direct_index, occurrence_positions],
        }
        accumulator.maximum_delta_e = max(
            accumulator.maximum_delta_e, float(row_scores.maximum_delta_e[cache_index])
        )
        accumulator.maximum_delta_path = max(
            accumulator.maximum_delta_path, float(row_scores.maximum_delta_path[cache_index])
        )
        accumulator.maximum_audit_discrepancy = max(
            accumulator.maximum_audit_discrepancy,
            float(row_scores.maximum_audit_discrepancy[cache_index]),
        )
        accumulator.maximum_parity_error = max(
            accumulator.maximum_parity_error, float(row_scores.maximum_parity_error[cache_index])
        )

    tau = float(batch.tau_score[batch.index[(view, gamma, "historical")]])
    # Pointwise endpoint containment, tolerant only to the frozen numerical guard.
    for state in ("historical", "current"):
        if (
            np.any(expanded["intersection"]["lower"] > expanded[state]["lower"] + tau)
            or np.any(expanded[state]["upper"] > expanded["union"]["upper"] + tau)
        ):
            raise RuntimeError("endpoint score containment failed")

    for state in ("historical", "current"):
        cache_index = batch.index[(view, gamma, state)]
        order = expand_unique_ranking(
            news_ids, occurrences_by_unique, row_scores.nominal_groups[cache_index], tie_hashes
        )
        expanded[state]["order"] = order

    historical = expanded["historical"]
    current = expanded["current"]
    guarded = bool(np.any(
        (historical["lower"] > current["upper"] + tau)
        | (current["lower"] > historical["upper"] + tau)
    ))
    accumulator.impressions += 1
    accumulator.guarded_score_changes += int(guarded)
    nonvacuous = len(news_ids) > 10
    supported_count = sum(bool(patterns.patterns[index]) for index in candidate_patterns)
    top_h = set(historical["order"][:10]) if nonvacuous else set(range(len(news_ids)))
    top_c = set(current["order"][:10]) if nonvacuous else set(range(len(news_ids)))
    top_z = set(baseline_order[:10]) if nonvacuous else set(range(len(news_ids)))
    hc_resolved = False
    baseline_h_resolved = False
    baseline_c_resolved = False
    certified = False
    exposed = False
    if nonvacuous:
        accumulator.nonvacuous += 1
        hc_resolved = resolved_swap(
            top_h, top_c, historical["lower"], historical["upper"],
            current["lower"], current["upper"], tau,
        )
        baseline_h_resolved = resolved_swap(
            top_h, top_z, historical["lower"], historical["upper"],
            baseline_lower, baseline_upper, tau,
        )
        baseline_c_resolved = resolved_swap(
            top_c, top_z, current["lower"], current["upper"],
            baseline_lower, baseline_upper, tau,
        )
        accumulator.resolved_hc_top10_changes += int(hc_resolved)
        accumulator.resolved_baseline_h += int(baseline_h_resolved)
        accumulator.resolved_baseline_c += int(baseline_c_resolved)
        outside_h = set(range(len(news_ids))) - top_h
        certified = (
            min(float(expanded["intersection"]["lower"][index]) for index in top_h)
            > max(float(expanded["union"]["upper"][index]) for index in outside_h) + tau
        )
        widths = np.maximum(
            0.0, expanded["union"]["lower"] - expanded["intersection"]["upper"]
        )
        exposed = (
            max(float(widths[index]) for index in top_h)
            + max(float(widths[index]) for index in outside_h) > tau
        )
        accumulator.certified += int(certified)
        accumulator.exposed += int(exposed)
        accumulator.exposed_certified += int(exposed and certified)
        if certified and top_h != top_c:
            accumulator.certified_hc_disagreements += 1
            raise RuntimeError("certified row has historical/current Top-10 disagreement")

        view_index = VIEW_NAMES.index(view)
        h6_h = {index for index, row in enumerate(candidate_records) if int(row["v"][view_index][2]) <= 10}
        h6_c = {index for index, row in enumerate(candidate_records) if int(row["v"][view_index][3]) <= 10}
        accumulator.h6_top10_disagreements_h += int(top_h != h6_h)
        accumulator.h6_top10_disagreements_c += int(top_c != h6_c)

    global_counts: dict[str, int] = {"historical": 0, "current": 0}
    for state in ("historical", "current"):
        state_scores = expanded[state]
        direct_positive = int(np.count_nonzero(state_scores["direct"] > tau))
        eligible = global_eligibility[(view, state)]
        global_counts[state] = int(np.count_nonzero(eligible & (state_scores["path_lower"] > tau)))
        if state == "historical":
            accumulator.direct_positive_occurrences_h += direct_positive
            accumulator.global_path_occurrences_h += global_counts[state]
            accumulator.global_path_impressions_h += int(global_counts[state] > 0)
        else:
            accumulator.direct_positive_occurrences_c += direct_positive
            accumulator.global_path_occurrences_c += global_counts[state]
            accumulator.global_path_impressions_c += int(global_counts[state] > 0)

    return [
        int(guarded), int(hc_resolved), int(baseline_h_resolved), int(baseline_c_resolved),
        int(certified), int(exposed), top_hash(news_ids, top_h), top_hash(news_ids, top_c),
        global_counts["historical"], global_counts["current"], supported_count,
    ]


def expand_unique_ranking(
    news_ids: Sequence[str],
    occurrences_by_unique: Sequence[Sequence[int]],
    unique_groups: Sequence[Sequence[int]],
    tie_hashes: Sequence[bytes],
) -> list[int]:
    order: list[int] = []
    for group in unique_groups:
        occurrences: list[int] = []
        for position in group:
            occurrences.extend(occurrences_by_unique[int(position)])
        occurrences.sort(key=lambda index: (tie_hashes[index], news_ids[index]))
        order.extend(occurrences)
    if len(order) != len(news_ids) or len(set(order)) != len(news_ids):
        raise RuntimeError("unique-pattern rank expansion failed")
    return order


def global_eligibility_row(
    graphs: Mapping[tuple[str, str], GraphState],
    profile: HistoryProfile,
    unique_patterns: Sequence[int],
    occurrence_positions: Any,
    patterns: NewsPatterns,
) -> dict[tuple[str, str], Any]:
    np = load_numpy()
    result: dict[tuple[str, str], Any] = {}
    for view in VIEW_NAMES:
        for state in ("historical", "current"):
            graph = graphs[(view, state)]
            unique_values = np.zeros(len(unique_patterns), dtype=np.bool_)
            for position, pattern_id in enumerate(unique_patterns):
                anchors = patterns.patterns[pattern_id]
                unique_values[position] = bool(
                    anchors
                    and not profile.anchor_support.intersection(anchors)
                    and not direct_fact_overlap(graph, profile.anchor_support, anchors)
                )
            result[(view, state)] = unique_values[occurrence_positions]
    return result


def source_cache_tau(
    caches: Mapping[tuple[str, Fraction, str], InverseCache],
    view: str, gamma: Fraction, state: str,
) -> float:
    return caches[(view, gamma, state)].tau_score


def baseline_row(
    profile: HistoryProfile,
    candidate_patterns: Sequence[int],
    unique_patterns: Sequence[int],
    gamma: Fraction,
    patterns: NewsPatterns,
    news_ids: Sequence[str],
    impression_id: str,
    tie_hashes: Sequence[bytes],
) -> tuple[
    list[float], list[float], list[float], list[int],
    dict[int, tuple[Fraction, float, float, float]],
]:
    by_pattern: dict[int, tuple[Fraction, float, float, float]] = {}
    for pattern_id in unique_patterns:
        by_pattern[pattern_id] = exact_baseline(profile, pattern_id, gamma, patterns)
    center: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    for pattern_id in candidate_patterns:
        item = by_pattern[pattern_id]
        center.append(item[1])
        lower.append(item[2])
        upper.append(item[3])
    tau = 1e-10 * max(1.0, 1.0 / float(gamma))
    order, _ = frozen_ranking(news_ids, center, impression_id, tau, tie_hashes)
    return center, lower, upper, order, by_pattern


def direct_pattern_caches(
    graphs: Mapping[tuple[str, str], GraphState], patterns: NewsPatterns
) -> dict[tuple[str, str], Any]:
    result: dict[tuple[str, str], Any] = {}
    for key, graph in graphs.items():
        c_float = fraction_matrix_float(graph.c_exact)
        result[key] = (patterns.zhat @ c_float) @ patterns.zhat.T
    return result


def adjudicate(config_reports: Sequence[Mapping[str, Any]], cohort: Mapping[str, int]) -> dict[str, Any]:
    by_key = {(item["view"], item["gamma"]): item for item in config_reports}
    gates: list[dict[str, Any]] = []

    def add(name: str, passed: bool, observed: Any) -> None:
        gates.append({"name": name, "passed": bool(passed), "observed": observed})

    add(
        "supported_scale",
        cohort["supported_gt10"] == EXPECTED_SUPPORTED_GT10
        and cohort["supported_gt10"] >= 5_000
        and cohort["supported_gt10"] / EXPECTED_NONVACUOUS >= 0.10,
        cohort["supported_gt10"],
    )
    primary = by_key[(VIEW_NAMES[0], "1/1")]
    add(
        "primary_revision_sensitivity",
        primary["guarded_score_vector_change"]["rate"] >= 0.20
        and primary["resolved_historical_current_top10_change"]["rate"] >= 0.02,
        {
            "score": primary["guarded_score_vector_change"],
            "top10": primary["resolved_historical_current_top10_change"],
        },
    )
    graph_dependence = primary["resolved_h9_vs_graph_free_top10"]
    add(
        "primary_graph_dependence",
        graph_dependence["historical_rate"] >= 0.05 and graph_dependence["current_rate"] >= 0.05,
        graph_dependence,
    )
    global_path = primary["global_cofact_path"]
    add(
        "primary_global_cofact_paths",
        global_path["historical_occurrence_rate"] >= 0.01
        and global_path["current_occurrence_rate"] >= 0.01
        and global_path["historical_impressions"] >= 1_000
        and global_path["current_impressions"] >= 1_000,
        global_path,
    )
    certificate = primary["certificate"]
    add(
        "primary_certificate_utility",
        certificate["rate"] >= 0.20
        and certificate["uncertainty_exposed_count"] >= 1_000
        and certificate["uncertainty_exposed_rate"] >= 0.02
        and certificate["exposed_certified_rate"] is not None
        and certificate["exposed_certified_rate"] >= 0.10
        and certificate["certified_historical_current_disagreements"] == 0,
        certificate,
    )
    for view in VIEW_NAMES[1:]:
        report = by_key[(view, "1/1")]
        dependence = report["resolved_h9_vs_graph_free_top10"]
        add(
            f"robustness_{view}",
            report["guarded_score_vector_change"]["rate"] >= 0.10
            and report["resolved_historical_current_top10_change"]["rate"] >= 0.01
            and report["certificate"]["rate"] >= 0.10
            and dependence["historical_rate"] >= 0.025
            and dependence["current_rate"] >= 0.025,
            report,
        )
    add(
        "fixed_gamma_numerical_audit",
        all(
            item["certificate"]["certified_historical_current_disagreements"] == 0
            for item in config_reports if item["gamma"] in {"1/10", "10/1"}
        ),
        {"audited_configurations": sum(item["gamma"] != "1/1" for item in config_reports)},
    )
    passed = all(gate["passed"] for gate in gates)
    return {
        "all_structural_gates_passed": passed,
        "labels_opened": False,
        "gates": gates,
        "verdict": PASS_VERDICT if passed else KILL_VERDICT,
    }


def peak_resident_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = wintypes.HANDLE
        try:
            get_process_memory_info = kernel32.K32GetProcessMemoryInfo
        except AttributeError:
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            get_process_memory_info = psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        get_process_memory_info.restype = wintypes.BOOL

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        process = get_current_process()
        ctypes.set_last_error(0)
        if not get_process_memory_info(process, ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        peak = int(counters.PeakWorkingSetSize)
        if peak <= 0:
            raise RuntimeError("Windows peak working-set counter is not positive")
        return peak
    import resource
    usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return usage if sys.platform == "darwin" else usage * 1024


def compute_scientific_payload(
    row_manifest_path: Path | None,
    include_eigen: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    np = load_numpy()
    input_hashes = verify_real_input_hashes()
    phase_a, qids = load_phase_a_contract()
    relations = load_relations()
    graphs = load_graph_states(qids, relations)
    graph_report = matrix_float_diagnostics(graphs)
    patterns = parse_news_patterns(qids)
    selected_audit = select_audit_rows()
    caches, cache_report = build_all_caches(graphs, patterns, include_eigen)
    batch = prepare_batch_caches(caches, include_eigen)
    direct_batch = prepare_direct_batch(graphs, patterns)
    configurations = [(view, gamma) for view in VIEW_NAMES for gamma in GAMMAS]
    accumulators = [ConfigAccumulator(view, gamma) for view, gamma in configurations]

    manifest_hash = hashlib.sha256()
    manifest_handle = None
    if row_manifest_path is not None:
        row_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_handle = row_manifest_path.open("xb", buffering=1 << 20)
    row_count = 0
    users: set[str] = set()
    candidate_total = 0
    supported_total = 0
    nonvacuous = 0
    supported_gt10 = 0
    supported_ge2 = 0
    histories_supported = 0
    try:
        with INPUT_PATHS["phase_a_manifest"].open("rb") as source:
            for row_index, raw_line in enumerate(source):
                row = json.loads(raw_line)
                impression_id, user_id, history, candidate_records = validate_manifest_row(
                    row, raw_line, row_index
                )
                profile = make_history_profile(history, patterns)
                histories_supported += 1
                news_ids = [str(record["n"]) for record in candidate_records]
                if any(news_id not in patterns.news_to_pattern for news_id in news_ids):
                    raise RuntimeError("manifest candidate references unknown news")
                candidate_patterns = [int(patterns.news_to_pattern[news_id]) for news_id in news_ids]
                unique_patterns = tuple(dict.fromkeys(candidate_patterns))
                unique_position = {pattern_id: position for position, pattern_id in enumerate(unique_patterns)}
                occurrence_positions = np.asarray(
                    [unique_position[value] for value in candidate_patterns], dtype=np.int64
                )
                occurrences_by_unique: list[list[int]] = [list() for _ in unique_patterns]
                for occurrence, position in enumerate(occurrence_positions):
                    occurrences_by_unique[int(position)].append(occurrence)
                tie_hashes = [
                    hashlib.sha256(f"{SEED_TEXT}|{impression_id}|{news_id}".encode("utf-8")).digest()
                    for news_id in news_ids
                ]
                baselines = {
                    gamma: baseline_row(
                        profile, candidate_patterns, unique_patterns, gamma, patterns,
                        news_ids, impression_id, tie_hashes,
                    )
                    for gamma in GAMMAS
                }
                row_scores = score_batched_row(
                    batch, profile, unique_patterns, patterns, baselines,
                    row_index in selected_audit,
                )
                direct_scores = score_direct_batched_row(direct_batch, profile, unique_patterns)
                eligibility = global_eligibility_row(
                    graphs, profile, unique_patterns, occurrence_positions, patterns
                )
                supported = sum(bool(patterns.patterns[pattern_id]) for pattern_id in candidate_patterns)
                candidate_total += len(news_ids)
                supported_total += supported
                users.add(user_id)
                if len(news_ids) > 10:
                    nonvacuous += 1
                    supported_gt10 += int(supported > 10)
                    supported_ge2 += int(supported >= 2)
                config_rows: list[Any] = []
                for accumulator in accumulators:
                    baseline = baselines[accumulator.gamma]
                    config_rows.append(process_configuration_row(
                        accumulator, batch, row_scores, direct_batch, direct_scores, patterns,
                        impression_id, news_ids, candidate_records, candidate_patterns,
                        unique_patterns, occurrence_positions, occurrences_by_unique, tie_hashes,
                        baseline[0], baseline[1], baseline[2], baseline[3],
                        eligibility,
                    ))
                output_row = {
                    "g": config_rows,
                    "i": impression_id,
                    "n": len(news_ids),
                    "s": supported,
                }
                encoded = canonical_bytes(output_row) + b"\n"
                manifest_hash.update(encoded)
                if manifest_handle is not None:
                    manifest_handle.write(encoded)
                row_count += 1
        if manifest_handle is not None:
            fsync_file(manifest_handle)
    finally:
        if manifest_handle is not None:
            manifest_handle.close()

    cohort = {
        "impressions": row_count,
        "users": len(users),
        "candidate_occurrences": candidate_total,
        "supported_candidate_occurrences": supported_total,
        "nonvacuous_impressions": nonvacuous,
        "supported_gt10": supported_gt10,
        "supported_ge2": supported_ge2,
        "histories_with_support": histories_supported,
        "news_rows": len(patterns.news_to_pattern),
        "supported_news": sum(bool(patterns.patterns[index]) for index in patterns.news_to_pattern.values()),
        "distinct_patterns": len(patterns.patterns),
        "audit_rows": len(selected_audit),
    }
    expected_cohort = {
        "impressions": EXPECTED_IMPRESSIONS,
        "users": EXPECTED_USERS,
        "candidate_occurrences": EXPECTED_CANDIDATES,
        "supported_candidate_occurrences": EXPECTED_SUPPORTED,
        "nonvacuous_impressions": EXPECTED_NONVACUOUS,
        "supported_gt10": EXPECTED_SUPPORTED_GT10,
        "supported_ge2": EXPECTED_SUPPORTED_GE2,
        "histories_with_support": EXPECTED_IMPRESSIONS,
        "news_rows": EXPECTED_NEWS_ROWS,
        "supported_news": 12_060,
        "distinct_patterns": EXPECTED_PATTERNS,
        "audit_rows": AUDIT_ROWS,
    }
    if cohort != expected_cohort:
        raise RuntimeError(f"locked H9A cohort audit mismatch: {cohort}")
    row_manifest_sha256 = manifest_hash.hexdigest().upper()
    if row_manifest_path is not None and sha256_file(row_manifest_path) != row_manifest_sha256:
        raise RuntimeError("streamed H9A row-manifest hash mismatch")
    config_reports = [accumulator.report() for accumulator in accumulators]
    decision = adjudicate(config_reports, cohort)
    scientific_payload = {
        "schema_version": "h9a_revkron_scientific_payload.v1",
        "classification": "prospective label-blind mechanism and certificate-coverage gate",
        "claim_boundary": {
            "novel_ranker_claimed": False,
            "novel_certificate_claimed": False,
            "strict_cold_start_claimed": False,
            "labels_opened": False,
            "next_stage_on_pass": "H9B provenance-group exact/anytime algorithm",
        },
        "protocol": {
            "sha256": PROTOCOL_SHA256,
            "anchor_count": SAMPLE_SIZE,
            "confidence_threshold": MINIMUM_CONFIDENCE,
            "views": list(VIEW_NAMES),
            "states": list(STATE_NAMES),
            "gammas": [f"{value.numerator}/{value.denominator}" for value in GAMMAS],
            "audit_selection": "SHA256(H9A-AUDIT|20260807| || impression_id || NUL || row_index)",
        },
        "inputs_sha256": input_hashes,
        "ordered_anchors": qids,
        "cohort": cohort,
        "graph_theorem_audit": graph_report,
        "inverse_cache_audit": cache_report,
        "configurations": config_reports,
        "row_manifest": {
            "schema_version": "h9a_row_manifest.compact.v1",
            "rows": row_count,
            "sha256": row_manifest_sha256,
            "format": "canonical compact JSON plus LF; g follows view-major/gamma order",
        },
        "decision": decision,
    }
    auxiliary = {
        "phase_a_sample_hash": sha256_bytes(canonical_bytes(phase_a["cohort"]["sampled_qids"])),
        "row_manifest_sha256": row_manifest_sha256,
        "row_manifest_bytes": row_manifest_path.stat().st_size if row_manifest_path is not None else None,
    }
    return scientific_payload, auxiliary


def scientific_payload_sha256(payload: Mapping[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(payload))


def run_experiment(authorization: Mapping[str, Any]) -> dict[str, Any]:
    start_time = time.perf_counter()
    role = str(authorization["run_role"])
    output_id = str(authorization["output_id"])
    if (role, output_id) not in {("primary", RUN_ID), ("exact_replay", REPLAY_ID)}:
        raise RuntimeError("unauthorized H9A run identity")
    output_directory = RESULTS_ROOT / output_id
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite {output_directory}")
    launch_directory = Path(str(authorization["launch_directory"])).resolve()
    release_path = Path(str(authorization["inner_lock_release_path"])).resolve()
    expected_release = launch_directory / f"{role}_inner_lock_released.json"
    if release_path != expected_release.resolve():
        raise RuntimeError("authorized inner-lock release path mismatch")
    inner_lock = InnerLock(release_path, authorization)
    stage = safe_stage_path(output_id)
    published = False
    try:
        stage.mkdir()
        inner_lock.acquire()
        startup_provenance = verify_bound_provenance(authorization)
        input_hashes_start = verify_real_input_hashes()
        payload, auxiliary = compute_scientific_payload(stage / "row_manifest.jsonl", include_eigen=False)
        elapsed = time.perf_counter() - start_time
        peak = peak_resident_bytes()
        runtime_passed = elapsed <= 300.0 and peak <= 2 * 1024 ** 3
        structural_verdict = payload["decision"]["verdict"]
        payload_hash = scientific_payload_sha256(payload)
        if verify_real_input_hashes() != input_hashes_start:
            raise RuntimeError("immutable inputs changed during H9A run")
        if verify_bound_provenance(authorization) != startup_provenance:
            raise RuntimeError("authorized provenance changed during H9A run")
        require_no_async_failures()
        result = {
            "schema_version": "h9a_revkron_result.v1",
            "output_id": output_id,
            "run_role": role,
            "scientific_payload": payload,
            "scientific_payload_sha256": payload_hash,
            "execution": {
                "elapsed_seconds": elapsed,
                "peak_resident_bytes": peak,
                "elapsed_limit_seconds": 300.0,
                "peak_resident_limit_bytes": 2 * 1024 ** 3,
                "one_thread": True,
                "gpu_disabled": True,
                "passed": runtime_passed,
            },
            "decision": {
                "structural_verdict": structural_verdict,
                "prepublication_runtime_diagnostic_passed": runtime_passed,
                "final_runtime_adjudication": "PENDING_LAUNCHER_AND_DEEP_VERIFIER",
                "labels_opened": False,
            },
            "artifacts": {
                "result": "result.json",
                "row_manifest": {
                    "name": "row_manifest.jsonl",
                    "sha256": auxiliary["row_manifest_sha256"],
                    "bytes": auxiliary["row_manifest_bytes"],
                },
            },
            "provenance": {
                "launch_id": authorization["launch_id"],
                "launcher_pid": int(authorization["launcher_pid"]),
                "process_pid": os.getpid(),
                "authorization_token_sha256": authorization["token_sha256"],
                "runtime_files": startup_provenance,
                "input_sha256_at_start": input_hashes_start,
                "input_sha256_before_publication": verify_real_input_hashes(),
                "async_error_ledger": file_record(Path(str(authorization["async_error_ledger"]))),
                "inner_lock": {"owner": inner_lock.owner, "retired_stale_lock": inner_lock.retired},
            },
        }
        write_exclusive_json(stage / "result.json", result)
        if set(path.name for path in stage.iterdir()) != {"result.json", "row_manifest.jsonl"}:
            raise RuntimeError("H9A stage artifact inventory mismatch")
        if sha256_file(stage / "row_manifest.jsonl") != auxiliary["row_manifest_sha256"]:
            raise RuntimeError("row manifest changed before publication")
        if not process_is_alive(int(authorization["launcher_pid"])):
            raise RuntimeError("launcher exited before H9A publication")
        assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), OUTER_LOCK_PATH)
        require_no_async_failures()
        rename_no_overwrite(stage, output_directory)
        published = True
        release_record = inner_lock.release(failed=False)
        assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), OUTER_LOCK_PATH)
        if not process_is_alive(int(authorization["launcher_pid"])):
            raise RuntimeError("launcher exited after H9A publication")
        require_no_async_failures()
        full_elapsed = time.perf_counter() - start_time
        full_peak = peak_resident_bytes()
        full_runtime_passed = full_elapsed <= 300.0 and full_peak <= 2 * 1024 ** 3
        verdict = structural_verdict if full_runtime_passed else KILL_VERDICT
        return {
            "status": "H9A_RUN_COMPLETE",
            "process_pid": os.getpid(),
            "output_id": output_id,
            "run_role": role,
            "output_directory": str(output_directory.resolve()),
            "result": str((output_directory / "result.json").resolve()),
            "row_manifest": str((output_directory / "row_manifest.jsonl").resolve()),
            "result_sha256": sha256_file(output_directory / "result.json"),
            "row_manifest_sha256": sha256_file(output_directory / "row_manifest.jsonl"),
            "scientific_payload_sha256": payload_hash,
            "structural_verdict": structural_verdict,
            "elapsed_seconds": full_elapsed,
            "peak_resident_bytes": full_peak,
            "runtime_passed": full_runtime_passed,
            "verdict": verdict,
            "inner_lock_release": release_record,
        }
    except BaseException:
        if inner_lock.fd is not None:
            try:
                inner_lock.release(failed=True)
            except Exception:
                pass
        if not published:
            remove_safe_stage(stage, output_id)
        raise


def verify_result_directory(path: Path, output_id: str, role: str) -> dict[str, Any]:
    if not path.is_dir() or {item.name for item in path.iterdir()} != {"result.json", "row_manifest.jsonl"}:
        raise RuntimeError("H9A result-directory inventory mismatch")
    result = read_json(path / "result.json")
    if (
        result.get("schema_version") != "h9a_revkron_result.v1"
        or result.get("output_id") != output_id
        or result.get("run_role") != role
        or scientific_payload_sha256(result.get("scientific_payload", {}))
        != result.get("scientific_payload_sha256")
    ):
        raise RuntimeError("H9A result identity/payload hash mismatch")
    artifact = result.get("artifacts", {}).get("row_manifest", {})
    manifest = path / "row_manifest.jsonl"
    if artifact.get("sha256") != sha256_file(manifest) or artifact.get("bytes") != manifest.stat().st_size:
        raise RuntimeError("H9A row-manifest artifact hash/size mismatch")
    return result


def deep_verify(authorization: Mapping[str, Any]) -> dict[str, Any]:
    startup_provenance = verify_bound_provenance(authorization)
    input_hashes_start = verify_real_input_hashes()
    primary = verify_result_directory(RESULTS_ROOT / RUN_ID, RUN_ID, "primary")
    replay = verify_result_directory(RESULTS_ROOT / REPLAY_ID, REPLAY_ID, "exact_replay")
    if primary["scientific_payload_sha256"] != replay["scientific_payload_sha256"]:
        raise RuntimeError("primary/replay scientific payload hashes differ")
    if primary["scientific_payload"] != replay["scientific_payload"]:
        raise RuntimeError("primary/replay scientific payloads differ")
    primary_manifest = RESULTS_ROOT / RUN_ID / "row_manifest.jsonl"
    replay_manifest = RESULTS_ROOT / REPLAY_ID / "row_manifest.jsonl"
    if (
        primary_manifest.stat().st_size != replay_manifest.stat().st_size
        or sha256_file(primary_manifest) != sha256_file(replay_manifest)
    ):
        raise RuntimeError("primary/replay compact row manifests differ")
    recomputed, auxiliary = compute_scientific_payload(None, include_eigen=True)
    recomputed_hash = scientific_payload_sha256(recomputed)
    if recomputed_hash != primary["scientific_payload_sha256"] or recomputed != primary["scientific_payload"]:
        raise RuntimeError("deep-verifier scientific recomputation differs")
    if auxiliary["row_manifest_sha256"] != sha256_file(primary_manifest):
        raise RuntimeError("deep-verifier raw row-manifest hash differs")
    if verify_real_input_hashes() != input_hashes_start:
        raise RuntimeError("immutable inputs changed during deep verification")
    if verify_bound_provenance(authorization) != startup_provenance:
        raise RuntimeError("authorized provenance changed during deep verification")
    require_no_async_failures()
    structural_verdict = str(primary["scientific_payload"]["decision"]["verdict"])
    runtime_fields = {
        "primary_launcher_elapsed_seconds": authorization.get("primary_launcher_elapsed_seconds"),
        "replay_launcher_elapsed_seconds": authorization.get("replay_launcher_elapsed_seconds"),
        "primary_peak_resident_bytes": authorization.get("primary_peak_resident_bytes"),
        "replay_peak_resident_bytes": authorization.get("replay_peak_resident_bytes"),
    }
    if (
        any(not isinstance(runtime_fields[name], (int, float)) for name in (
            "primary_launcher_elapsed_seconds", "replay_launcher_elapsed_seconds"
        ))
        or any(not isinstance(runtime_fields[name], int) for name in (
            "primary_peak_resident_bytes", "replay_peak_resident_bytes"
        ))
    ):
        raise RuntimeError("launcher runtime evidence is missing or malformed")
    runtime_gate = {
        "limit_seconds": 300.0,
        "limit_peak_resident_bytes": 2 * 1024 ** 3,
        **runtime_fields,
    }
    runtime_gate["primary_passed"] = bool(
        float(runtime_fields["primary_launcher_elapsed_seconds"]) <= 300.0
        and int(runtime_fields["primary_peak_resident_bytes"]) <= 2 * 1024 ** 3
    )
    runtime_gate["replay_passed"] = bool(
        float(runtime_fields["replay_launcher_elapsed_seconds"]) <= 300.0
        and int(runtime_fields["replay_peak_resident_bytes"]) <= 2 * 1024 ** 3
    )
    runtime_gate["passed"] = bool(runtime_gate["primary_passed"] and runtime_gate["replay_passed"])
    verdict = structural_verdict if runtime_gate["passed"] else KILL_VERDICT
    verification = {
        "schema_version": "h9a_deep_verification.v1",
        "status": "H9A_DEEP_VERIFY_COMPLETE",
        "output_id": "deep_verification",
        "run_role": "verifier",
        "process_pid": os.getpid(),
        "scientific_payload_sha256": recomputed_hash,
        "row_manifest_sha256": auxiliary["row_manifest_sha256"],
        "primary_replay_exact": True,
        "independent_clique_assembly": True,
        "eigendecomposition_rank_parity": True,
        "all_outward_bounds_recomputed": True,
        "structural_verdict": structural_verdict,
        "runtime_gate": runtime_gate,
        "verdict": verdict,
    }
    path = Path(str(authorization["verification_path"])).resolve()
    launch_directory = Path(str(authorization["launch_directory"])).resolve()
    if path.parent != launch_directory or path.name != "deep_verification.json":
        raise RuntimeError("deep-verification path escaped authorization")
    write_exclusive_json(path, verification)
    require_no_async_failures()
    return {
        "status": "H9A_VERIFY_COMPLETE",
        "output_id": "deep_verification",
        "run_role": "verifier",
        "process_pid": os.getpid(),
        "verification_path": str(path),
        "verification_sha256": sha256_file(path),
        "scientific_payload_sha256": recomputed_hash,
        "structural_verdict": structural_verdict,
        "runtime_gate": runtime_gate,
        "verdict": verdict,
    }


def strict_membership_certificate(
    top: set[int], lower: Sequence[float], upper: Sequence[float], tau: float
) -> bool:
    outside = set(range(len(lower))) - top
    if not top or not outside:
        return False
    return min(float(lower[index]) for index in top) > max(float(upper[index]) for index in outside) + tau


def run_selftest(authorization: Mapping[str, Any]) -> dict[str, Any]:
    np = load_numpy()
    verify_thread_environment()
    verify_python_thread_state()
    require_no_async_failures()
    startup = verify_bound_provenance(authorization)
    synthetic_peak = peak_resident_bytes()
    if not isinstance(synthetic_peak, int) or synthetic_peak <= 0:
        raise RuntimeError("synthetic peak-memory transport self-test failed")

    empty = [frozenset() for _ in range(SAMPLE_SIZE)]
    singleton = list(empty)
    singleton[0] = frozenset({"P1|Q10"})
    r_empty, _, _ = assemble_rational_operator(tuple(empty))
    r_singleton, _, _ = assemble_rational_operator(tuple(singleton))
    if r_empty != r_singleton or any(value != 0 for row in r_singleton for value in row):
        raise RuntimeError("synthetic singleton invariance failed")

    shared = list(empty)
    shared[0] = frozenset({"P1|Q10", "P2|Q20"})
    shared[1] = frozenset({"P1|Q10"})
    shared[2] = frozenset({"P1|Q10", "P2|Q20"})
    r_shared, _, _ = assemble_rational_operator(tuple(shared))
    potential = [Fraction(index - 1, 3) if index < 3 else Fraction(0) for index in range(SAMPLE_SIZE)]
    quadratic = sum(
        potential[row] * r_shared[row][column] * potential[column]
        for row in range(SAMPLE_SIZE) for column in range(SAMPLE_SIZE)
    )
    dirichlet = Fraction(0)
    for anchors in fact_anchors(shared).values():
        mean = sum((potential[index] for index in anchors), Fraction(0)) / len(anchors)
        dirichlet += sum(((potential[index] - mean) ** 2 for index in anchors), Fraction(0))
    if quadratic != dirichlet:
        raise RuntimeError("synthetic Schur/Dirichlet equality failed")

    envelope_edges = ((0, "P1|Q10"), (1, "P1|Q10"), (1, "P2|Q20"), (2, "P2|Q20"))
    union_sets = [set() for _ in range(SAMPLE_SIZE)]
    for anchor, fact in envelope_edges:
        union_sets[anchor].add(fact)
    r_union, _, _ = assemble_rational_operator(tuple(frozenset(values) for values in union_sets))
    r_union_float = fraction_matrix_float(r_union)
    q_union = np.eye(SAMPLE_SIZE) + r_union_float
    k_union = np.linalg.inv(q_union)
    p = np.zeros(SAMPLE_SIZE, dtype=np.float64)
    p[0] = 1.0
    candidate_good = p.copy()
    candidate_bad = np.zeros(SAMPLE_SIZE, dtype=np.float64)
    candidate_bad[2] = 1.0
    b_good = p - candidate_good
    b_bad = p - candidate_bad
    union_scores = np.asarray((-b_good @ k_union @ b_good, -b_bad @ k_union @ b_bad))
    lower = union_scores.copy()
    upper = np.asarray((0.0, -2.0), dtype=np.float64)  # empty/intersection score upper box
    # The actual endpoint envelope is [-E_I,-E_U].
    exact_lower = np.minimum(union_scores, upper)
    exact_upper = np.maximum(union_scores, upper)
    if not strict_membership_certificate({0}, exact_lower, exact_upper, 0.0):
        raise RuntimeError("synthetic strict certificate fixture did not certify")
    for mask in range(1 << len(envelope_edges)):
        state_sets = [set() for _ in range(SAMPLE_SIZE)]
        for edge_index, (anchor, fact) in enumerate(envelope_edges):
            if (mask >> edge_index) & 1:
                state_sets[anchor].add(fact)
        r_state, _, _ = assemble_rational_operator(tuple(frozenset(values) for values in state_sets))
        difference = r_union_float - fraction_matrix_float(r_state)
        if float(np.min(np.linalg.eigvalsh((difference + difference.T) * 0.5))) < -1e-12:
            raise RuntimeError("synthetic all-subgraph Loewner check failed")
        inverse = np.linalg.inv(np.eye(SAMPLE_SIZE) + fraction_matrix_float(r_state))
        scores = np.asarray((-b_good @ inverse @ b_good, -b_bad @ inverse @ b_bad))
        if int(np.argmax(scores)) != 0:
            raise RuntimeError("synthetic certificate failed to preserve Top-1 in a subgraph")
    if strict_membership_certificate({0}, [1.0, 0.0], [1.0, 1.0], 0.0):
        raise RuntimeError("synthetic equality boundary was incorrectly certified")

    # Deliberately state-normalized grounding: adding a singleton changes the
    # anchor degree and destroys both singleton invariance and Loewner order.
    base = list(empty)
    base[0] = frozenset({"P1|Q10"})
    base[1] = frozenset({"P1|Q10"})
    expanded = list(base)
    expanded[0] = frozenset({"P1|Q10", "P2|Q20"})
    r_base, _, _ = assemble_rational_operator(tuple(base))
    r_expanded, _, _ = assemble_rational_operator(tuple(expanded))
    degrees_base = np.asarray([max(1, len(values)) for values in base], dtype=np.float64)
    degrees_expanded = np.asarray([max(1, len(values)) for values in expanded], dtype=np.float64)
    normalized_base = fraction_matrix_float(r_base) / np.sqrt(degrees_base[:, None] * degrees_base[None, :])
    normalized_expanded = fraction_matrix_float(r_expanded) / np.sqrt(
        degrees_expanded[:, None] * degrees_expanded[None, :]
    )
    if float(np.min(np.linalg.eigvalsh(normalized_expanded - normalized_base))) >= -1e-6:
        raise RuntimeError("synthetic state-normalized counterexample was not rejected")

    ranking_ids = ("N1", "N2", "N3", "N4")
    palette = (-2e-10, -1e-10, 0.0, 1e-10, 2e-10)
    tie_hashes = [hashlib.sha256(f"{SEED_TEXT}|SYNTHETIC|{news_id}".encode()).digest() for news_id in ranking_ids]
    for scores in itertools.product(palette, repeat=4):
        first = frozen_ranking(ranking_ids, scores, "SYNTHETIC", 1e-10, tie_hashes)
        second = frozen_ranking(ranking_ids, scores, "SYNTHETIC", 1e-10, tie_hashes)
        if first != second:
            raise RuntimeError("synthetic ranking determinism failed")

    # Exercise the actual 36-slot batched scorer with a supported pattern, the
    # mandatory empty-pattern residual gate, and a duplicated occurrence.
    synthetic_pattern_tuples = ((), (0,), (1,))
    synthetic_z_exact = (
        tuple(Fraction(0) for _ in range(SAMPLE_SIZE)),
        tuple(Fraction(int(index == 0)) for index in range(SAMPLE_SIZE)),
        tuple(Fraction(int(index == 1)) for index in range(SAMPLE_SIZE)),
    )
    synthetic_zhat = np.zeros((3, SAMPLE_SIZE), dtype=np.float64)
    synthetic_zhat[1, 0] = 1.0
    synthetic_zhat[2, 1] = 1.0
    synthetic_delta = np.zeros_like(synthetic_zhat)
    synthetic_patterns = NewsPatterns(
        {"N1": 1, "N2": 0, "N3": 2, "N4": 1},
        synthetic_pattern_tuples,
        synthetic_z_exact,
        synthetic_zhat,
        synthetic_delta,
        np.asarray([up_sum(abs(float(value)) for value in row) for row in synthetic_zhat]),
        np.asarray([up_sum(float(value) for value in row) for row in synthetic_delta]),
    )
    synthetic_a = synthetic_zhat @ synthetic_zhat.T
    synthetic_cache = InverseCache(
        "0" * 64, Fraction(1), np.eye(SAMPLE_SIZE), np.eye(SAMPLE_SIZE),
        np.zeros((SAMPLE_SIZE, SAMPLE_SIZE)), synthetic_a.copy(), synthetic_a.copy(),
        synthetic_a.copy(), synthetic_a.copy(),
        [[None for _ in range(SAMPLE_SIZE)] for _ in range(SAMPLE_SIZE)],
        1e-12, 1e-10, 2.0 ** -38,
        float(np.max(synthetic_patterns.z_l1_up)),
        float(np.max(synthetic_patterns.delta_z_l1_up)),
        next_up(1.0), 0.0, next_up(1.0), next_up(1.0), 0.0, {},
    )
    synthetic_mapping = {
        (view, gamma, state): synthetic_cache
        for view in VIEW_NAMES for gamma in GAMMAS for state in STATE_NAMES
    }
    synthetic_batch = prepare_batch_caches(synthetic_mapping, include_eigen=True)
    synthetic_profile = HistoryProfile(
        (1,), (Fraction(1),), np.asarray([1.0]), np.asarray([0.0]),
        synthetic_z_exact[1], frozenset({0}), Fraction(1),
    )
    synthetic_news = ("N1", "N2", "N3", "N4")
    synthetic_candidate_patterns = (1, 0, 2, 1)
    synthetic_unique = (1, 0, 2)
    synthetic_hashes = [
        hashlib.sha256(f"{SEED_TEXT}|BATCH|{news_id}".encode()).digest()
        for news_id in synthetic_news
    ]
    synthetic_baselines = {
        gamma: baseline_row(
            synthetic_profile, synthetic_candidate_patterns, synthetic_unique, gamma,
            synthetic_patterns, synthetic_news, "BATCH", synthetic_hashes,
        )
        for gamma in GAMMAS
    }
    synthetic_scores = score_batched_row(
        synthetic_batch, synthetic_profile, synthetic_unique, synthetic_patterns,
        synthetic_baselines, audit=False,
    )
    first_cache = synthetic_batch.index[(VIEW_NAMES[0], Fraction(1), "historical")]
    if not np.allclose(
        synthetic_scores.nominal[first_cache], np.asarray([0.0, -1.0, -2.0]),
        rtol=0.0, atol=1e-14,
    ):
        raise RuntimeError("synthetic batched supported/empty score parity failed")
    occurrence_positions = np.asarray([0, 1, 2, 0], dtype=np.int64)
    occurrences_by_unique = ([0, 3], [1], [2])
    expanded_order = expand_unique_ranking(
        synthetic_news, occurrences_by_unique,
        synthetic_scores.nominal_groups[first_cache], synthetic_hashes,
    )
    if set(expanded_order[:2]) != {0, 3} or expanded_order[2:] != [1, 2]:
        raise RuntimeError("synthetic batched group/tie expansion failed")
    if not np.array_equal(
        synthetic_scores.nominal[first_cache, occurrence_positions],
        np.asarray([0.0, -1.0, -2.0, 0.0]),
    ):
        raise RuntimeError("synthetic duplicated-occurrence expansion failed")

    temporary = Path(os.environ.get("TEMP", str(H9_DIR))) / f"provicold-h9a-selftest-{uuid.uuid4().hex}"
    temporary.mkdir()
    try:
        target = temporary / "artifact.json"
        write_exclusive_json(target, {"passed": True})
        try:
            write_exclusive_json(target, {"passed": False})
        except FileExistsError:
            pass
        else:
            raise RuntimeError("synthetic no-overwrite publication failed")
    finally:
        if temporary.parent.resolve() not in {
            Path(os.environ.get("TEMP", str(H9_DIR))).resolve(), H9_DIR.resolve()
        } or not temporary.name.startswith("provicold-h9a-selftest-"):
            raise RuntimeError("unsafe synthetic temporary directory")
        shutil.rmtree(temporary)

    if verify_bound_provenance(authorization) != startup:
        raise RuntimeError("authorized provenance changed during self-test")
    verify_python_thread_state()
    require_no_async_failures()
    return {
        "status": "H9A_SELFTEST_COMPLETE",
        "output_id": "synthetic_selftest",
        "run_role": "selftest",
        "process_pid": os.getpid(),
        "runner_sha256": sha256_file(SCRIPT_PATH),
        "launcher_sha256": sha256_file(LAUNCHER_PATH),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "lock_sha256": sha256_file(IMPLEMENTATION_LOCK_PATH),
        "real_input_files_opened": False,
        "candidate_labels_opened": False,
        "async_error_ledger": file_record(Path(str(authorization["async_error_ledger"]))),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("self-test", "run", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("--authorization", required=True)
        child.add_argument("--token", required=True)
        child.add_argument("--process-start", required=True)
        child.add_argument("--process-ack", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    authorization = bootstrap_handshake(args)
    async_ledger = Path(str(authorization["async_error_ledger"])).resolve()
    install_async_hooks(async_ledger)
    if args.command == "self-test":
        summary = run_selftest(authorization)
        assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), SELFTEST_OUTER_LOCK_PATH)
    elif args.command == "run":
        summary = run_experiment(authorization)
    else:
        summary = deep_verify(authorization)
        assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), OUTER_LOCK_PATH)
    verify_thread_environment()
    verify_python_thread_state()
    require_no_async_failures()
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
