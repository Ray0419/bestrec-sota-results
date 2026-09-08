#!/usr/bin/env python3
"""Vectorized, label-blind H6 Phase-A coverage runner and deep verifier."""

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
from array import array
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RUN_ID = "coverage_run_002"
REPLAY_ID = "coverage_run_002_replay"
SEED = "20260807"
SAMPLE_SIZE = 50
MINIMUM_CONFIDENCE = 0.90
SCORE_TOLERANCE = 1e-12
EXPECTED_CUTOFF = "2019-11-15T23:58:03Z"
EXPECTED_NEWS_ROWS = 42_416
EXPECTED_BEHAVIOR_ROWS = 73_152
EXPECTED_RELATIONS = 1_091
EXPECTED_HASHES = {
    "news": "E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822",
    "behaviors": "B6C460E33B1A8693252DED6E626DA7D3CCF78920EEA2EC11889020BB7D8443EF",
    "facts": "13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D",
    "entities": "45B83B0AFCB6C1348080984B1373CE50912219DFE247F48E97F7FB09009595ED",
    "relations": "D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A",
}
METADATA_BLOCKLIST_IDS = (
    "P1343",
    "P1424",
    "P5008",
    "P6104",
    "P7867",
    "P8744",
    "P9241",
    "P2354",
    "P8402",
    "P10280",
    "P1889",
)
METADATA_BLOCKLIST = frozenset(METADATA_BLOCKLIST_IDS)
REMOVED_ANCHOR_IDS = ("Q30", "Q22686")
REMOVED_ANCHORS = frozenset(REMOVED_ANCHOR_IDS)
VIEW_NAMES = (
    "primary_relation_vocabulary",
    "metadata_blocklist",
    "remove_q30_q22686",
)
QID_PATTERN = re.compile(r"^Q[1-9][0-9]*$")
PROPERTY_PATTERN = re.compile(r"^P[1-9][0-9]*$")
FACT_PATTERN = re.compile(r"^(P[1-9][0-9]*)\|Q[1-9][0-9]*$")
NEWS_ID_PATTERN = re.compile(r"^N[0-9]+$")
CANDIDATE_PATTERN = re.compile(r"^N[0-9]+-[01]$")
MANIFEST_SUFFIX_PATTERN = re.compile(rb'"N[0-9]+-[01]"')

SCRIPT_PATH = Path(__file__).resolve()
H6_DIR = SCRIPT_PATH.parent.parent
ROOT = H6_DIR.parents[3]
PROTOCOL_PATH = H6_DIR / "protocol.md"
CORRECTION_PATH = H6_DIR / "correction_run_002_runtime.md"
LAUNCHER_PATH = SCRIPT_PATH.with_name("run_h6_phase_a_coverage_safe.ps1")
RESULTS_ROOT = H6_DIR / "results"
SELFTEST_ROOT = H6_DIR / "selftest_artifacts"
INNER_LOCK_PATH = H6_DIR / "H6_COVERAGE_RUN_002_INNER.lock"
OUTER_LOCK_PATH = H6_DIR / "H6_COVERAGE_RUN_002_LAUNCH.lock"
SELFTEST_OUTER_LOCK_PATH = H6_DIR / "H6_PYTHON_SELFTEST_LAUNCH.lock"
VENV_LAUNCHER_PATH = ROOT / "_bestrec_run/.venv/Scripts/python.exe"
VENV_CONFIG_PATH = ROOT / "_bestrec_run/.venv/pyvenv.cfg"
INPUT_PATHS = {
    "news": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/news.tsv",
    "behaviors": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/behaviors.tsv",
    "facts": ROOT / "experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/facts.jsonl",
    "entities": ROOT / "experiments/kg_launch_autoresearch/experiments/h5_bitemporal_drift/results/run_003/entities.csv",
    "relations": ROOT / "experiments/kg_launch_autoresearch/data/MINDsmall_dev/MINDsmall_dev/relation_embedding.vec",
}

_ASYNC_FAILURES: list[dict[str, Any]] = []
_ASYNC_LEDGER: Path | None = None
_NP: Any = None


def load_numpy() -> Any:
    global _NP
    if _NP is None:
        import numpy as np  # type: ignore

        _NP = np
    return _NP


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def fsync_file(handle: Any) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def rename_no_overwrite(source: Path, destination: Path) -> None:
    """Atomically rename once, retrying only transient Windows sharing errors."""
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
            if (
                os.name != "nt"
                or getattr(error, "winerror", None) not in {5, 32, 33}
                or attempt == 4
            ):
                raise
            time.sleep(0.1)
    if last_error is None:
        raise RuntimeError("unreachable rename retry state")
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
        raise RuntimeError(f"unauthorized output id: {output_id}")
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    stage = RESULTS_ROOT / f".{output_id}.tmp.{uuid.uuid4().hex}"
    if stage.parent.resolve() != RESULTS_ROOT.resolve():
        raise RuntimeError("stage escaped results root")
    if not re.fullmatch(rf"\.{re.escape(output_id)}\.tmp\.[0-9a-f]{{32}}", stage.name):
        raise RuntimeError("stage naming invariant failed")
    return stage


def remove_safe_stage(stage: Path, output_id: str) -> None:
    if not stage.exists():
        return
    if stage.parent.resolve() != RESULTS_ROOT.resolve() or not re.fullmatch(
        rf"\.{re.escape(output_id)}\.tmp\.[0-9a-f]{{32}}", stage.name
    ):
        raise RuntimeError(f"refusing unsafe stage cleanup: {stage}")
    shutil.rmtree(stage)


def _record_async_failure(kind: str, exc_type: type[BaseException], exc: BaseException, tb: Any) -> None:
    record = {
        "kind": kind,
        "pid": os.getpid(),
        "time_ns": time.time_ns(),
        "exception_type": getattr(exc_type, "__name__", str(exc_type)),
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(exc_type, exc, tb)),
    }
    _ASYNC_FAILURES.append(record)
    if _ASYNC_LEDGER is not None:
        encoded = canonical_bytes(record) + b"\n"
        with _ASYNC_LEDGER.open("ab", buffering=0) as handle:
            handle.write(encoded)
            os.fsync(handle.fileno())


def install_async_hooks(ledger: Path | None) -> None:
    global _ASYNC_LEDGER
    _ASYNC_LEDGER = ledger
    if ledger is not None:
        if not ledger.is_file() or ledger.stat().st_size != 0:
            raise RuntimeError("fresh asynchronous-error ledger is missing or nonempty")

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        _record_async_failure("threading.excepthook", args.exc_type, args.exc_value, args.exc_traceback)

    def unraisable_hook(args: Any) -> None:
        exc = args.exc_value if args.exc_value is not None else RuntimeError(str(args.err_msg))
        _record_async_failure("sys.unraisablehook", type(exc), exc, args.exc_traceback)

    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def require_no_async_failures() -> None:
    if _ASYNC_FAILURES:
        raise RuntimeError(f"{len(_ASYNC_FAILURES)} asynchronous/unraisable exception(s) recorded")
    if _ASYNC_LEDGER is not None and _ASYNC_LEDGER.stat().st_size != 0:
        raise RuntimeError("asynchronous-error ledger is nonempty")


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

    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, process_id)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    error = ctypes.windll.kernel32.GetLastError()
    if error == 5:
        return True
    return False


class InnerLock:
    def __init__(self, release_path: Path, role: str, authorization: Mapping[str, Any]) -> None:
        self.release_path = release_path
        self.role = role
        self.fd: int | None = None
        self.retired: dict[str, Any] | None = None
        self.owner = {
            "mode": "h6-phase-a-inner-lock",
            "pid": os.getpid(),
            "role": role,
            "launch_id": str(authorization["launch_id"]),
            "launcher_pid": int(authorization["launcher_pid"]),
            "token_sha256": sha256_bytes(str(authorization["token"]).encode("utf-8")),
            "runner_sha256": str(authorization["runner_sha256"]),
            "launcher_sha256": str(authorization["launcher_sha256"]),
            "correction_sha256": str(authorization["correction_sha256"]),
            "base_interpreter_path": str(authorization["base_interpreter_path"]),
            "base_interpreter_sha256": str(authorization["base_interpreter_sha256"]),
            "venv_launcher_path": str(authorization["venv_launcher_path"]),
            "venv_launcher_sha256": str(authorization["venv_launcher_sha256"]),
            "created_time_ns": time.time_ns(),
        }

    def acquire(self) -> None:
        for attempt in range(2):
            try:
                self.fd = os.open(INNER_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                payload = canonical_bytes(self.owner) + b"\n"
                os.write(self.fd, payload)
                os.fsync(self.fd)
                return
            except FileExistsError:
                if attempt != 0:
                    raise RuntimeError("inner lock acquisition raced after one stale-lock retirement")
                try:
                    existing = read_json(INNER_LOCK_PATH)
                except Exception as error:
                    raise RuntimeError("existing inner lock is unreadable or malformed; refusing retirement") from error
                if not isinstance(existing, dict) or not isinstance(existing.get("pid"), int):
                    raise RuntimeError("existing inner lock has invalid owner record")
                if process_is_alive(int(existing["pid"])):
                    raise RuntimeError(f"active H6 inner lock is owned by PID {existing['pid']}")
                retired_path = self.release_path.parent / f"stale_inner_{uuid.uuid4().hex[:20]}.json"
                rename_no_overwrite(INNER_LOCK_PATH, retired_path)
                self.retired = file_record(retired_path)
        raise AssertionError("unreachable")

    def release(self, failed: bool = False) -> dict[str, Any]:
        if self.fd is None:
            raise RuntimeError("inner lock was not acquired")
        os.close(self.fd)
        self.fd = None
        destination = self.release_path
        if failed:
            destination = destination.with_name(f"inner_fail_{self.role}_{uuid.uuid4().hex[:20]}.json")
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite inner-lock release {destination}")
        rename_no_overwrite(INNER_LOCK_PATH, destination)
        return file_record(destination)


def assert_outer_lock_held(path: Path, expected_path: Path) -> None:
    if path.resolve() != expected_path.resolve():
        raise RuntimeError("outer launcher lock path is not the fixed mode-specific lock")
    if not path.is_file():
        raise RuntimeError("outer launcher lock is missing")
    if os.name == "nt":
        try:
            handle = path.open("rb")
        except PermissionError:
            return
        else:
            handle.close()
            raise RuntimeError("outer launcher lock is not held share-none")


def verify_python_thread_state() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("H6 process is not executing on MainThread")
    live = [thread for thread in threading.enumerate() if thread.is_alive()]
    if len(live) != 1 or live[0] is not threading.main_thread() or threading.active_count() != 1:
        raise RuntimeError("unexpected live Python thread detected")


def verify_live_launcher_contract(authorization: Mapping[str, Any]) -> None:
    launcher_pid = int(authorization.get("launcher_pid", -1))
    if launcher_pid <= 0 or not process_is_alive(launcher_pid):
        raise RuntimeError("authorized launcher PID is not alive")
    expected_lock = (
        SELFTEST_OUTER_LOCK_PATH if authorization.get("action") == "self-test" else OUTER_LOCK_PATH
    )
    assert_outer_lock_held(Path(str(authorization["outer_lock"])).resolve(), expected_lock)


def verify_authorized_runtime(authorization: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    fixed = {
        "runner": SCRIPT_PATH,
        "protocol": PROTOCOL_PATH.resolve(),
        "correction": CORRECTION_PATH.resolve(),
        "launcher": LAUNCHER_PATH.resolve(),
        "venv_launcher": VENV_LAUNCHER_PATH.resolve(),
        "venv_config": VENV_CONFIG_PATH.resolve(),
        "base_interpreter": Path(str(getattr(sys, "_base_executable", ""))).resolve(),
    }
    expected = {
        "runner": ("runner_sha256", str(SCRIPT_PATH)),
        "protocol": ("protocol_sha256", str(PROTOCOL_PATH.resolve())),
        "correction": ("correction_sha256", str(CORRECTION_PATH.resolve())),
        "launcher": ("launcher_sha256", str(LAUNCHER_PATH.resolve())),
        "venv_launcher": ("venv_launcher_sha256", str(VENV_LAUNCHER_PATH.resolve())),
        "venv_config": (
            "venv_config_sha256",
            str(Path(str(authorization["venv_config_path"])).resolve()),
        ),
        "base_interpreter": (
            "base_interpreter_sha256",
            str(Path(str(authorization["base_interpreter_path"])).resolve()),
        ),
    }
    records: dict[str, dict[str, Any]] = {}
    for name, path in fixed.items():
        hash_field, expected_path = expected[name]
        if not path.is_file() or str(path) != expected_path:
            raise RuntimeError(f"authorized {name} path mismatch")
        record = file_record(path)
        if record["sha256"] != authorization.get(hash_field):
            raise RuntimeError(f"authorized {name} hash mismatch")
        records[name] = record
    if Path(sys.executable).resolve() != VENV_LAUNCHER_PATH.resolve():
        raise RuntimeError("sys.executable is not the authorized venv launcher")
    if Path(sys.prefix).resolve() != VENV_LAUNCHER_PATH.parent.parent.resolve():
        raise RuntimeError("sys.prefix is not the authorized venv")
    if Path(sys.base_prefix).resolve() != fixed["base_interpreter"].parent:
        raise RuntimeError("sys.base_prefix is not the authorized base interpreter home")
    return records


def bootstrap_handshake(args: argparse.Namespace) -> Mapping[str, Any]:
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
        authorization.get("mode") != "h6-launcher-authorization"
        or authorization.get("action") != args.command
        or authorization.get("token") != args.token
        or authorization.get("runner_sha256") != runner_hash
        or authorization.get("authorization_path") != str(authorization_path)
    ):
        raise RuntimeError("launcher authorization identity mismatch")
    launch_directory = Path(str(authorization.get("launch_directory", ""))).resolve()
    if args.command == "self-test":
        expected_launch_parent = SELFTEST_ROOT.resolve()
        expected_launch_prefix = "st_"
    else:
        expected_launch_parent = RESULTS_ROOT.resolve()
        expected_launch_prefix = "r2_"
    if (
        launch_directory.parent != expected_launch_parent
        or re.fullmatch(re.escape(expected_launch_prefix) + r"[0-9a-f]{20}", launch_directory.name) is None
        or authorization_path.parent != launch_directory
        or Path(str(authorization.get("async_error_ledger", ""))).resolve().parent != launch_directory
    ):
        raise RuntimeError("launcher artifact containment mismatch")
    start_path = Path(args.process_start).resolve()
    ack_path = Path(args.process_ack).resolve()
    if (
        start_path != Path(str(authorization.get("process_start_path", ""))).resolve()
        or ack_path != Path(str(authorization.get("process_ack_path", ""))).resolve()
        or start_path.parent != launch_directory
        or ack_path.parent != launch_directory
    ):
        raise RuntimeError("PID-handshake path mismatch")
    verify_live_launcher_contract(authorization)
    runtime_records = verify_authorized_runtime(authorization)
    record = {
        "mode": "h6-child-process-start",
        "action": args.command,
        "launch_id": authorization["launch_id"],
        "launcher_pid": int(authorization["launcher_pid"]),
        "process_pid": os.getpid(),
        "authorization_sha256": authorization_hash,
        "token_sha256": token_hash,
        "runner_sha256": runner_hash,
        "environment": {
            "sys_executable": str(Path(sys.executable).resolve()),
            "sys_base_executable": str(Path(str(getattr(sys, "_base_executable", ""))).resolve()),
            "sys_prefix": str(Path(sys.prefix).resolve()),
            "sys_base_prefix": str(Path(sys.base_prefix).resolve()),
            "runtime_files": runtime_records,
            "main_thread_only": True,
            "thread_bounds": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                    "BLIS_NUM_THREADS",
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
        acknowledgement.get("mode") != "h6-child-process-acknowledgement"
        or acknowledgement.get("action") != args.command
        or acknowledgement.get("launch_id") != authorization["launch_id"]
        or int(acknowledgement.get("process_pid", -1)) != os.getpid()
        or acknowledgement.get("authorization_sha256") != authorization_hash
        or acknowledgement.get("token_sha256") != token_hash
    ):
        raise RuntimeError("launcher PID acknowledgement mismatch")
    verify_live_launcher_contract(authorization)
    verify_python_thread_state()
    return authorization


def verify_thread_environment() -> None:
    for name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ):
        if os.environ.get(name) != "1":
            raise RuntimeError(f"thread bound is not one: {name}")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        raise RuntimeError("CUDA_VISIBLE_DEVICES is not -1")
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("PYTHONHASHSEED is not the fixed value 0")


def verify_immutable_hashes() -> dict[str, str]:
    actual: dict[str, str] = {}
    for name, path in INPUT_PATHS.items():
        if not path.is_file():
            raise RuntimeError(f"immutable input is missing: {path}")
        actual[name] = sha256_file(path)
        if actual[name] != EXPECTED_HASHES[name]:
            raise RuntimeError(f"immutable input hash mismatch: {name}")
    return actual


def acquire_fact_sets() -> tuple[list[str], list[set[str]], list[set[str]], list[set[str]], list[set[str]], set[str]]:
    relations: set[str] = set()
    relation_rows = 0
    with INPUT_PATHS["relations"].open("r", encoding="utf-8", newline="") as handle:
        for line in handle:
            relation_rows += 1
            relation_id = line.split("\t", 1)[0]
            if not PROPERTY_PATTERN.fullmatch(relation_id) or relation_id in relations:
                raise RuntimeError("relation vocabulary has an invalid or duplicate property ID")
            relations.add(relation_id)
    if relation_rows != EXPECTED_RELATIONS or len(relations) != EXPECTED_RELATIONS:
        raise RuntimeError("relation vocabulary cardinality mismatch")

    qids: list[str] = []
    current_primary: list[set[str]] = []
    historical_primary: list[set[str]] = []
    current_block: list[set[str]] = []
    historical_block: list[set[str]] = []
    with INPUT_PATHS["facts"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            qid = str(row.get("qid", ""))
            if not QID_PATTERN.fullmatch(qid) or qid in qids or row.get("api_ok") is not True:
                raise RuntimeError("H5 anchor ledger has an invalid, duplicate, or unresolved entity")
            qids.append(qid)
            snapshot_sets: dict[str, set[str]] = {}
            for snapshot in ("current", "historical"):
                source = row[snapshot]["facts"]
                if not isinstance(source, list) or len(source) != len(set(source)):
                    raise RuntimeError("H5 fact list is malformed or contains duplicates")
                filtered: set[str] = set()
                for fact in source:
                    match = FACT_PATTERN.fullmatch(str(fact))
                    if match is None:
                        raise RuntimeError("H5 fact signature is invalid")
                    if match.group(1) in relations:
                        filtered.add(str(fact))
                snapshot_sets[snapshot] = filtered
            current_primary.append(snapshot_sets["current"])
            historical_primary.append(snapshot_sets["historical"])
            current_block.append(
                {fact for fact in snapshot_sets["current"] if fact.split("|", 1)[0] not in METADATA_BLOCKLIST}
            )
            historical_block.append(
                {fact for fact in snapshot_sets["historical"] if fact.split("|", 1)[0] not in METADATA_BLOCKLIST}
            )
    if len(qids) != SAMPLE_SIZE or len(set(qids)) != SAMPLE_SIZE:
        raise RuntimeError("H5 anchor sample cardinality mismatch")

    with INPUT_PATHS["entities"].open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    entity_qids = [str(row.get("qid", "")) for row in rows]
    if (
        len(rows) != SAMPLE_SIZE
        or len(set(entity_qids)) != SAMPLE_SIZE
        or set(entity_qids) != set(qids)
        or any(row.get("api_ok") != "True" for row in rows)
    ):
        raise RuntimeError("H5 entity summary does not reproduce the anchor sample")
    return qids, current_primary, historical_primary, current_block, historical_block, relations


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


def parse_news(qids: Sequence[str], grams: Sequence[tuple[Any, Any]]) -> tuple[list[str], dict[str, int], Any, list[tuple[Any, Any]], int]:
    np = load_numpy()
    qid_to_index = {qid: index for index, qid in enumerate(qids)}
    news_ids: list[str] = []
    news_index: dict[str, int] = {}
    incidence = np.zeros((EXPECTED_NEWS_ROWS, SAMPLE_SIZE), dtype=np.float64)
    row_count = 0
    with INPUT_PATHS["news"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            if row_count >= EXPECTED_NEWS_ROWS:
                raise RuntimeError("news input exceeds locked row count")
            fields = raw_line.rstrip("\r\n").split("\t", 7)
            if len(fields) != 8:
                raise RuntimeError("news row does not have exactly eight fields")
            news_id = fields[0]
            if not NEWS_ID_PATTERN.fullmatch(news_id) or news_id in news_index:
                raise RuntimeError("news input has an invalid or duplicate news ID")
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
                    if not QID_PATTERN.fullmatch(qid) or qid not in qid_to_index:
                        continue
                    try:
                        confidence = float(annotation.get("Confidence"))
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(confidence) and confidence >= MINIMUM_CONFIDENCE:
                        retained.add(qid_to_index[qid])
            if retained:
                incidence[row_count, list(retained)] = 1.0
            news_index[news_id] = row_count
            news_ids.append(news_id)
            row_count += 1
    if row_count != EXPECTED_NEWS_ROWS or len(news_index) != EXPECTED_NEWS_ROWS:
        raise RuntimeError("news row-count reproduction failed")

    removed_mask = np.ones(SAMPLE_SIZE, dtype=np.float64)
    for qid in REMOVED_ANCHORS:
        if qid not in qid_to_index:
            raise RuntimeError(f"predeclared removed anchor is absent: {qid}")
        removed_mask[qid_to_index[qid]] = 0.0
    caches: list[tuple[Any, Any]] = []
    for view_index, (historical_gram, current_gram) in enumerate(grams):
        view_incidence = incidence if view_index != 2 else incidence * removed_mask[None, :]
        snapshot_cache: list[Any] = []
        for gram in (historical_gram, current_gram):
            active = view_incidence * (np.diag(gram) > 0.0)[None, :]
            norm_squared = np.sum((active @ gram) * active, axis=1)
            if not np.all(np.isfinite(norm_squared)) or np.any(norm_squared < -SCORE_TOLERANCE):
                raise RuntimeError("cached news-vector squared norm is invalid")
            coefficients = np.zeros_like(active, dtype=np.float64)
            nonzero = norm_squared > 0.0
            coefficients[nonzero] = active[nonzero] / np.sqrt(norm_squared[nonzero, None])
            if np.any(nonzero):
                norms = np.sum((coefficients[nonzero] @ gram) * coefficients[nonzero], axis=1)
                if not np.allclose(norms, 1.0, rtol=0.0, atol=1e-10):
                    raise RuntimeError("cached news vectors are not unit normalized")
            projection = coefficients @ gram
            snapshot_cache.append((coefficients, projection))
        caches.append((snapshot_cache[0], snapshot_cache[1]))
    return news_ids, news_index, incidence, caches, int(np.count_nonzero(np.any(incidence != 0.0, axis=1)))


def recover_candidate_id(token: str) -> str:
    if CANDIDATE_PATTERN.fullmatch(token) is None:
        raise RuntimeError("malformed candidate token encountered")
    return token.rsplit("-", 1)[0]


def validate_candidate_scores(scores: Any) -> Any:
    np = load_numpy()
    if not np.all(np.isfinite(scores)):
        raise RuntimeError("candidate score vector contains a nonfinite value")
    return scores


def frozen_tolerance_groups(scores: Any) -> list[list[int]]:
    """Group descending exact-score buckets against each group's first score."""
    buckets: dict[float, list[int]] = defaultdict(list)
    for index, value in enumerate(scores.tolist()):
        buckets[float(value)].append(index)
    groups: list[list[int]] = []
    pending: list[int] = []
    group_reference: float | None = None
    for score in sorted(buckets, reverse=True):
        if group_reference is None:
            group_reference = score
        elif abs(group_reference - score) > SCORE_TOLERANCE:
            groups.append(pending)
            pending = []
            group_reference = score
        pending.extend(buckets[score])
    if pending:
        groups.append(pending)
    return groups


def frozen_ranking(news_ids: Sequence[str], scores: Any, impression_id: str) -> tuple[list[int], list[int]]:
    np = load_numpy()
    validate_candidate_scores(scores)
    if len(news_ids) != len(scores) or len(news_ids) != len(set(news_ids)):
        raise RuntimeError("ranking IDs/scores have inconsistent or duplicate cardinality")
    tie_hashes = [hashlib.sha256(f"{SEED}|{impression_id}|{news_id}".encode("utf-8")).hexdigest().upper() for news_id in news_ids]
    order: list[int] = []
    for group in frozen_tolerance_groups(scores):
        group.sort(key=lambda index: (tie_hashes[index], news_ids[index]))
        order.extend(group)
    ranks = [0] * len(news_ids)
    for rank, candidate_index in enumerate(order, start=1):
        ranks[candidate_index] = rank
    return order, ranks


class ViewAccumulator:
    def __init__(self, name: str) -> None:
        self.name = name
        self.candidates = 0
        self.historical_nonzero = 0
        self.current_nonzero = 0
        self.score_changed = 0
        self.order_changed = 0
        self.top1_changed = 0
        self.top10_changed = 0
        self.signed_deltas = array("d")
        self.absolute_deltas = array("d")
        self.max_absolute_deltas = array("d")


def quantile_summary(values: array) -> dict[str, float] | None:
    if not values:
        return None
    np = load_numpy()
    source = np.frombuffer(values, dtype=np.float64)
    quantiles = np.asarray((0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0), dtype=np.float64)
    measured = np.quantile(source, quantiles, method="linear")
    return {
        f"q{round(float(quantile) * 100):02d}": float(value)
        for quantile, value in zip(quantiles, measured, strict=True)
    }


def accumulator_result(accumulator: ViewAccumulator, eligible: int) -> dict[str, Any]:
    candidate_denominator = accumulator.candidates
    return {
        "eligible_impressions": eligible,
        "candidates": accumulator.candidates,
        "candidate_nonzero_score": {
            "historical_count": accumulator.historical_nonzero,
            "historical_rate": accumulator.historical_nonzero / candidate_denominator if candidate_denominator else None,
            "current_count": accumulator.current_nonzero,
            "current_rate": accumulator.current_nonzero / candidate_denominator if candidate_denominator else None,
        },
        "score_vector_changed": {
            "count": accumulator.score_changed,
            "rate": accumulator.score_changed / eligible if eligible else None,
        },
        "total_order_changed": {
            "count": accumulator.order_changed,
            "rate": accumulator.order_changed / eligible if eligible else None,
        },
        "top1_changed": {
            "count": accumulator.top1_changed,
            "rate": accumulator.top1_changed / eligible if eligible else None,
        },
        "top_min10_set_changed": {
            "count": accumulator.top10_changed,
            "rate": accumulator.top10_changed / eligible if eligible else None,
        },
        "score_delta_quantiles": {
            "candidate_signed_current_minus_historical": quantile_summary(accumulator.signed_deltas),
            "candidate_absolute": quantile_summary(accumulator.absolute_deltas),
            "impression_max_absolute": quantile_summary(accumulator.max_absolute_deltas),
            "interpolation": "linear at (n-1)q",
        },
    }


def parse_behavior_time(value: str) -> datetime:
    return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=timezone.utc)


def run_phase_a(authorization: Mapping[str, Any]) -> dict[str, Any]:
    async_ledger = Path(str(authorization["async_error_ledger"])).resolve()
    install_async_hooks(async_ledger)
    np = load_numpy()
    verify_thread_environment()
    verify_python_thread_state()
    output_id = str(authorization["output_id"])
    role = str(authorization["run_role"])
    if (output_id, role) not in {(RUN_ID, "primary"), (REPLAY_ID, "exact_replay")}:
        raise RuntimeError("unauthorized Phase-A output identity")
    output_directory = RESULTS_ROOT / output_id
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite {output_directory}")
    launch_directory = Path(str(authorization["launch_directory"])).resolve()
    verify_live_launcher_contract(authorization)
    runtime_records = verify_authorized_runtime(authorization)
    input_hashes_start = verify_immutable_hashes()
    runner_hash = sha256_file(SCRIPT_PATH)
    protocol_hash = sha256_file(PROTOCOL_PATH)
    correction_hash = sha256_file(CORRECTION_PATH)
    if (
        runner_hash != authorization["runner_sha256"]
        or protocol_hash != authorization["protocol_sha256"]
        or correction_hash != authorization["correction_sha256"]
    ):
        raise RuntimeError("runner/protocol/correction hash differs from launcher authorization")

    release_path = launch_directory / f"{role}_inner_lock_released.json"
    inner_lock = InnerLock(release_path, role, authorization)
    inner_lock.acquire()
    stage: Path | None = None
    published = False
    release_record: dict[str, Any] | None = None
    try:
        stage = safe_stage_path(output_id)
        stage.mkdir()
        manifest_path = stage / "cohort_manifest.jsonl"
        qids, current_primary, historical_primary, current_block, historical_block, relations = acquire_fact_sets()
        primary_historical_gram = gram_from_fact_sets(historical_primary)
        primary_current_gram = gram_from_fact_sets(current_primary)
        block_historical_gram = gram_from_fact_sets(historical_block)
        block_current_gram = gram_from_fact_sets(current_block)
        grams = (
            (primary_historical_gram, primary_current_gram),
            (block_historical_gram, block_current_gram),
            (primary_historical_gram, primary_current_gram),
        )
        news_ids, news_index, incidence, caches, news_with_anchor = parse_news(qids, grams)
        has_anchor = np.any(incidence != 0.0, axis=1)
        accumulators = [ViewAccumulator(name) for name in VIEW_NAMES]
        eligible_users: set[str] = set()
        seen_impressions: set[str] = set()
        eligible_impressions = 0
        total_candidates = 0
        behavior_rows = 0
        maximum_time = datetime.min.replace(tzinfo=timezone.utc)
        manifest_hash = hashlib.sha256()
        manifest_lines = 0
        suffix_leak_lines = 0

        with manifest_path.open("xb", buffering=1 << 20) as manifest_handle, INPUT_PATHS["behaviors"].open(
            "r", encoding="utf-8", newline=""
        ) as behavior_handle:
            for raw_line in behavior_handle:
                behavior_rows += 1
                fields = raw_line.rstrip("\r\n").split("\t", 4)
                if len(fields) != 5:
                    raise RuntimeError("behavior row does not have exactly five fields")
                impression_id, user_id = fields[0], fields[1]
                if (
                    not impression_id.strip()
                    or not user_id.strip()
                    or impression_id in seen_impressions
                ):
                    raise RuntimeError("behavior input has a missing or duplicate impression/user ID")
                seen_impressions.add(impression_id)
                impression_time = parse_behavior_time(fields[2])
                maximum_time = max(maximum_time, impression_time)

                history_ids = fields[3].split() if fields[3].strip() else []
                for news_id in history_ids:
                    if NEWS_ID_PATTERN.fullmatch(news_id) is None or news_id not in news_index:
                        raise RuntimeError("unknown or malformed history news ID")

                raw_candidate_tokens = fields[4].split()
                if not raw_candidate_tokens:
                    raise RuntimeError("impression has no candidate tokens")
                candidate_ids = [recover_candidate_id(token) for token in raw_candidate_tokens]
                raw_candidate_tokens = []
                fields[4] = ""
                raw_line = ""
                if len(candidate_ids) != len(set(candidate_ids)):
                    raise RuntimeError("duplicate candidate news ID")
                if any(candidate_id not in news_index for candidate_id in candidate_ids):
                    raise RuntimeError("unknown candidate news ID")

                retained_history_ids = history_ids[-50:]
                history_indices = np.fromiter(
                    (news_index[news_id] for news_id in retained_history_ids), dtype=np.int64
                )
                if len(candidate_ids) < 2 or history_indices.size == 0 or not bool(np.any(has_anchor[history_indices])):
                    continue
                candidate_indices = np.fromiter(
                    (news_index[news_id] for news_id in candidate_ids), dtype=np.int64
                )
                eligible_impressions += 1
                total_candidates += len(candidate_ids)
                eligible_users.add(user_id)

                historical_scores_by_view: list[Any] = []
                current_scores_by_view: list[Any] = []
                historical_ranks_by_view: list[list[int]] = []
                current_ranks_by_view: list[list[int]] = []
                for view_index, ((historical_gram, current_gram), cache, accumulator) in enumerate(
                    zip(grams, caches, accumulators, strict=True)
                ):
                    snapshot_scores: list[Any] = []
                    for gram, (coefficients, projection) in (
                        (historical_gram, cache[0]),
                        (current_gram, cache[1]),
                    ):
                        user_raw = np.sum(coefficients[history_indices], axis=0)
                        norm_squared = float(user_raw @ gram @ user_raw)
                        if not math.isfinite(norm_squared) or norm_squared < -SCORE_TOLERANCE:
                            raise RuntimeError("user-vector squared norm is invalid")
                        if norm_squared > 0.0:
                            scores = (projection[candidate_indices] @ user_raw) / math.sqrt(norm_squared)
                        else:
                            scores = np.zeros(candidate_indices.shape[0], dtype=np.float64)
                        snapshot_scores.append(validate_candidate_scores(scores))
                    historical_scores, current_scores = snapshot_scores
                    historical_order, historical_ranks = frozen_ranking(
                        candidate_ids, historical_scores, impression_id
                    )
                    current_order, current_ranks = frozen_ranking(
                        candidate_ids, current_scores, impression_id
                    )
                    historical_scores_by_view.append(historical_scores)
                    current_scores_by_view.append(current_scores)
                    historical_ranks_by_view.append(historical_ranks)
                    current_ranks_by_view.append(current_ranks)

                    accumulator.candidates += len(candidate_ids)
                    accumulator.historical_nonzero += int(
                        np.count_nonzero(np.abs(historical_scores) > SCORE_TOLERANCE)
                    )
                    accumulator.current_nonzero += int(
                        np.count_nonzero(np.abs(current_scores) > SCORE_TOLERANCE)
                    )
                    deltas = current_scores - historical_scores
                    absolute_deltas = np.abs(deltas)
                    maximum_delta = float(np.max(absolute_deltas))
                    accumulator.signed_deltas.extend(deltas.tolist())
                    accumulator.absolute_deltas.extend(absolute_deltas.tolist())
                    accumulator.max_absolute_deltas.append(maximum_delta)
                    accumulator.score_changed += int(maximum_delta > SCORE_TOLERANCE)
                    accumulator.order_changed += int(historical_order != current_order)
                    accumulator.top1_changed += int(historical_order[0] != current_order[0])
                    top_count = min(10, len(candidate_ids))
                    accumulator.top10_changed += int(
                        set(historical_order[:top_count]) != set(current_order[:top_count])
                    )

                canonical_candidate_indices = sorted(
                    range(len(candidate_ids)), key=lambda index: candidate_ids[index]
                )
                manifest_candidates: list[dict[str, Any]] = []
                for candidate_position in canonical_candidate_indices:
                    view_tuples = [
                        [
                            float(historical_scores_by_view[view_index][candidate_position]),
                            float(current_scores_by_view[view_index][candidate_position]),
                            int(historical_ranks_by_view[view_index][candidate_position]),
                            int(current_ranks_by_view[view_index][candidate_position]),
                        ]
                        for view_index in range(len(VIEW_NAMES))
                    ]
                    manifest_candidates.append(
                        {"n": candidate_ids[candidate_position], "v": view_tuples}
                    )
                manifest_record = {
                    "i": impression_id,
                    "u": user_id,
                    "h": retained_history_ids,
                    "c": manifest_candidates,
                }
                encoded_line = json.dumps(
                    manifest_record,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                suffix_leak_lines += int(MANIFEST_SUFFIX_PATTERN.search(encoded_line) is not None)
                manifest_handle.write(encoded_line)
                manifest_handle.write(b"\n")
                manifest_hash.update(encoded_line)
                manifest_hash.update(b"\n")
                manifest_lines += 1
            fsync_file(manifest_handle)

        if behavior_rows != EXPECTED_BEHAVIOR_ROWS or len(seen_impressions) != EXPECTED_BEHAVIOR_ROWS:
            raise RuntimeError("behavior row-count or impression-uniqueness reproduction failed")
        maximum_time_text = maximum_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if maximum_time_text != EXPECTED_CUTOFF:
            raise RuntimeError("behavior cutoff does not match lock")
        manifest_sha256 = manifest_hash.hexdigest().upper()
        if manifest_sha256 != sha256_file(manifest_path) or manifest_lines != eligible_impressions:
            raise RuntimeError("streamed manifest hash/count integrity failed")
        if suffix_leak_lines != 0:
            raise RuntimeError("candidate suffix leaked into Phase-A manifest")

        views = {
            accumulator.name: accumulator_result(accumulator, eligible_impressions)
            for accumulator in accumulators
        }
        primary = views[VIEW_NAMES[0]]
        impression_gate = eligible_impressions >= 5_000
        user_gate = len(eligible_users) >= 2_000
        score_change_gate = primary["score_vector_changed"]["rate"] is not None and primary[
            "score_vector_changed"
        ]["rate"] >= 0.20
        rank_change_gate = (
            primary["total_order_changed"]["rate"] is not None
            and primary["total_order_changed"]["rate"] >= 0.05
        ) or (
            primary["top_min10_set_changed"]["rate"] is not None
            and primary["top_min10_set_changed"]["rate"] >= 0.02
        )
        verdict = (
            "PASS_COVERAGE_AND_OPEN_LABELS"
            if impression_gate and user_gate and score_change_gate and rank_change_gate
            else "KILL_H6_SHARED_FACT_DIRECTION"
        )
        input_hashes_publication = verify_immutable_hashes()
        if input_hashes_publication != input_hashes_start:
            raise RuntimeError("immutable input changed during run")
        require_no_async_failures()

        metric_payload = {
            "eligible_impressions": eligible_impressions,
            "distinct_users": len(eligible_users),
            "candidates": total_candidates,
            "views": views,
            "gates": {
                "eligible_impressions_gate": impression_gate,
                "distinct_users_gate": user_gate,
                "primary_score_vector_change_gate": score_change_gate,
                "primary_rank_change_gate": rank_change_gate,
            },
            "verdict": verdict,
        }
        metrics_sha256 = sha256_bytes(canonical_bytes(metric_payload))
        result = {
            "schema_version": "h6_phase_a_coverage.python.v1",
            "run_id": RUN_ID,
            "output_id": output_id,
            "run_role": role,
            "classification": "confirmatory label-blind feasibility gate",
            "cutoff_utc": EXPECTED_CUTOFF,
            "protocol": {
                "sample_size": SAMPLE_SIZE,
                "confidence_threshold": MINIMUM_CONFIDENCE,
                "maximum_history_articles": 50,
                "score_tolerance": SCORE_TOLERANCE,
                "tie_rule": "ascending hexadecimal SHA-256 of 20260807|impression_id|news_id",
                "primary_relation_policy": "properties in frozen MIND relation_embedding.vec vocabulary",
                "metadata_blocklist": list(METADATA_BLOCKLIST_IDS),
                "removed_anchor_robustness": list(REMOVED_ANCHOR_IDS),
                "graph_implementation": "NumPy-vectorized exact 50-anchor Gram kernel",
            },
            "provenance": {
                "runner": runtime_records["runner"],
                "committed_protocol": runtime_records["protocol"],
                "runtime_correction": runtime_records["correction"],
                "launcher": runtime_records["launcher"],
                "base_interpreter": runtime_records["base_interpreter"],
                "venv_launcher": runtime_records["venv_launcher"],
                "venv_config": runtime_records["venv_config"],
                "authorization": file_record(Path(str(authorization["authorization_path"]))),
                "launch_id": str(authorization["launch_id"]),
                "launcher_pid": int(authorization["launcher_pid"]),
                "authorization_token_sha256": sha256_bytes(str(authorization["token"]).encode("utf-8")),
                "process_pid": os.getpid(),
                "input_sha256_at_start": input_hashes_start,
                "input_sha256_before_publication": input_hashes_publication,
                "async_error_ledger": file_record(async_ledger),
                "inner_lock": {"owner": inner_lock.owner, "retired_stale_lock": inner_lock.retired},
            },
            "inputs": {
                name: {"path": str(path.resolve()), "sha256": input_hashes_start[name]}
                for name, path in INPUT_PATHS.items()
            },
            "cohort": {
                "behavior_rows": behavior_rows,
                "eligible_impressions": eligible_impressions,
                "distinct_users": len(eligible_users),
                "candidates": total_candidates,
                "known_news": len(news_ids),
                "news_with_sampled_anchor": news_with_anchor,
                "sampled_qids": qids,
                "distinct_relation_ids": len(relations),
                "manifest": "cohort_manifest.jsonl",
                "manifest_sha256": manifest_sha256,
                "manifest_schema": {
                    "version": "h6_phase_a_manifest.compact.v1",
                    "line_format": "one compact JSON object followed by LF",
                    "line_order": "immutable behaviors.tsv row order, eligible rows only",
                    "top_level_field_order": ["i", "u", "h", "c"],
                    "top_level_fields": {
                        "i": "impression_id",
                        "u": "user_id",
                        "h": "retained last-50 history news IDs in supplied order",
                        "c": "candidate records in ordinal news_id order",
                    },
                    "candidate_record": {"n": "news_id", "v": "view tuples in view_order"},
                    "view_order": list(VIEW_NAMES),
                    "view_tuple_order": [
                        "historical_score",
                        "current_score",
                        "historical_rank",
                        "current_rank",
                    ],
                },
                "manifest_contains_candidate_suffix": False,
            },
            "views": views,
            "metric_payload_sha256": metrics_sha256,
            "sanity_checks": [
                {"name": "immutable_input_hashes", "passed": True, "observed": input_hashes_publication},
                {"name": "news_rows", "passed": len(news_ids) == EXPECTED_NEWS_ROWS, "observed": len(news_ids)},
                {"name": "behavior_rows", "passed": behavior_rows == EXPECTED_BEHAVIOR_ROWS, "observed": behavior_rows},
                {"name": "sample_qids", "passed": len(qids) == SAMPLE_SIZE, "observed": len(qids)},
                {"name": "relation_ids", "passed": len(relations) == EXPECTED_RELATIONS, "observed": len(relations)},
                {"name": "manifest_hash", "passed": True, "observed": manifest_sha256},
                {"name": "candidate_suffix_absent", "passed": suffix_leak_lines == 0, "observed": suffix_leak_lines},
                {"name": "async_error_ledger_empty", "passed": async_ledger.stat().st_size == 0, "observed": async_ledger.stat().st_size},
            ],
            "decision": {
                "verdict": verdict,
                "all_sanity_checks_passed": True,
                **metric_payload["gates"],
                "labels_may_be_opened": verdict == "PASS_COVERAGE_AND_OPEN_LABELS",
            },
            "artifacts": {"result": "result.json", "cohort_manifest": "cohort_manifest.jsonl"},
        }
        write_exclusive_json(stage / "result.json", result)
        if sha256_file(manifest_path) != manifest_sha256:
            raise RuntimeError("manifest changed before directory publication")
        verify_live_launcher_contract(authorization)
        verify_thread_environment()
        verify_python_thread_state()
        if verify_authorized_runtime(authorization) != runtime_records:
            raise RuntimeError("authorized runtime changed before result publication")
        if verify_immutable_hashes() != input_hashes_start:
            raise RuntimeError("immutable input changed immediately before result publication")
        require_no_async_failures()
        if output_directory.exists():
            raise FileExistsError(f"result appeared during computation: {output_directory}")
        rename_no_overwrite(stage, output_directory)
        published = True
        release_record = inner_lock.release(failed=False)
        require_no_async_failures()
        return {
            "status": "H6_PHASE_A_RUN_COMPLETE",
            "process_pid": os.getpid(),
            "output_id": output_id,
            "run_role": role,
            "result_path": str((output_directory / "result.json").resolve()),
            "result_sha256": sha256_file(output_directory / "result.json"),
            "manifest_path": str((output_directory / "cohort_manifest.jsonl").resolve()),
            "manifest_sha256": manifest_sha256,
            "metric_payload_sha256": metrics_sha256,
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
                "H6 Phase-A computation and cleanup both failed",
                [error, *cleanup_errors],
            ) from error
        raise


def verifier_frozen_ranks(news_ids: Sequence[str], scores: Any, impression_id: str) -> tuple[list[int], list[int]]:
    """Independent verifier implementation of the frozen first-score-anchored ranking."""
    np = load_numpy()
    if len(news_ids) != len(scores) or len(news_ids) != len(set(news_ids)) or not np.all(np.isfinite(scores)):
        raise RuntimeError("verifier ranking input is invalid")
    exact_buckets: dict[float, list[int]] = {}
    for position, raw_score in enumerate(scores.tolist()):
        exact_buckets.setdefault(float(raw_score), []).append(position)
    ranked: list[int] = []
    group: list[int] = []
    reference: float | None = None
    for exact_score in sorted(exact_buckets.keys(), reverse=True):
        if reference is None:
            reference = exact_score
        elif abs(reference - exact_score) > SCORE_TOLERANCE:
            group.sort(
                key=lambda position: (
                    hashlib.sha256(
                        f"{SEED}|{impression_id}|{news_ids[position]}".encode("utf-8")
                    ).hexdigest().upper(),
                    news_ids[position],
                )
            )
            ranked.extend(group)
            group = []
            reference = exact_score
        group.extend(exact_buckets[exact_score])
    group.sort(
        key=lambda position: (
            hashlib.sha256(
                f"{SEED}|{impression_id}|{news_ids[position]}".encode("utf-8")
            ).hexdigest().upper(),
            news_ids[position],
        )
    )
    ranked.extend(group)
    ranks = [0] * len(news_ids)
    for one_based_rank, position in enumerate(ranked, start=1):
        ranks[position] = one_based_rank
    return ranked, ranks


def accumulate_manifest_metrics(manifest_path: Path, expected_view_names: Sequence[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    np = load_numpy()
    accumulators = [ViewAccumulator(name) for name in expected_view_names]
    users: set[str] = set()
    impressions: set[str] = set()
    candidate_total = 0
    line_count = 0
    with manifest_path.open("rb") as handle:
        for raw_line in handle:
            line_count += 1
            if not raw_line.endswith(b"\n") or raw_line.endswith(b"\r\n"):
                raise RuntimeError("manifest line is not terminated by exactly LF")
            if MANIFEST_SUFFIX_PATTERN.search(raw_line):
                raise RuntimeError("candidate suffix found in manifest during verification")
            row = json.loads(raw_line)
            if not isinstance(row, dict) or list(row) != ["i", "u", "h", "c"]:
                raise RuntimeError("manifest top-level schema/order mismatch")
            if raw_line != json.dumps(
                row, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8") + b"\n":
                raise RuntimeError("manifest line is not exact compact UTF-8 JSON plus LF")
            impression_id = row["i"]
            user_id = row["u"]
            if (
                not isinstance(impression_id, str)
                or not impression_id.strip()
                or not isinstance(user_id, str)
                or not user_id.strip()
                or impression_id in impressions
            ):
                raise RuntimeError("manifest impression/user integrity failed")
            impressions.add(impression_id)
            users.add(user_id)
            if (
                not isinstance(row["h"], list)
                or len(row["h"]) > 50
                or any(not isinstance(value, str) or NEWS_ID_PATTERN.fullmatch(value) is None for value in row["h"])
            ):
                raise RuntimeError("manifest history integrity failed")
            candidates = row["c"]
            if not isinstance(candidates, list) or len(candidates) < 2:
                raise RuntimeError("manifest candidate list integrity failed")
            for candidate in candidates:
                if (
                    not isinstance(candidate, dict)
                    or list(candidate) != ["n", "v"]
                    or not isinstance(candidate["n"], str)
                    or NEWS_ID_PATTERN.fullmatch(candidate["n"]) is None
                    or not isinstance(candidate["v"], list)
                    or len(candidate["v"]) != len(VIEW_NAMES)
                ):
                    raise RuntimeError("manifest candidate record schema/order mismatch")
                for view_tuple in candidate["v"]:
                    if (
                        not isinstance(view_tuple, list)
                        or len(view_tuple) != 4
                        or isinstance(view_tuple[0], bool)
                        or not isinstance(view_tuple[0], (int, float))
                        or isinstance(view_tuple[1], bool)
                        or not isinstance(view_tuple[1], (int, float))
                        or isinstance(view_tuple[2], bool)
                        or not isinstance(view_tuple[2], int)
                        or isinstance(view_tuple[3], bool)
                        or not isinstance(view_tuple[3], int)
                    ):
                        raise RuntimeError("manifest view tuple schema mismatch")
            candidate_ids = [candidate["n"] for candidate in candidates]
            if candidate_ids != sorted(candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
                raise RuntimeError("manifest candidate ordering/cardinality failed")
            candidate_total += len(candidates)
            for view_index, accumulator in enumerate(accumulators):
                historical = np.asarray([candidate["v"][view_index][0] for candidate in candidates], dtype=np.float64)
                current = np.asarray([candidate["v"][view_index][1] for candidate in candidates], dtype=np.float64)
                historical_ranks = [int(candidate["v"][view_index][2]) for candidate in candidates]
                current_ranks = [int(candidate["v"][view_index][3]) for candidate in candidates]
                if not np.all(np.isfinite(historical)) or not np.all(np.isfinite(current)):
                    raise RuntimeError("manifest has a nonfinite score")
                historical_order, recomputed_historical_ranks = verifier_frozen_ranks(
                    candidate_ids, historical, impression_id
                )
                current_order, recomputed_current_ranks = verifier_frozen_ranks(
                    candidate_ids, current, impression_id
                )
                if (
                    historical_ranks != recomputed_historical_ranks
                    or current_ranks != recomputed_current_ranks
                ):
                    raise RuntimeError("manifest ranks differ from independent frozen-ranking recomputation")
                accumulator.candidates += len(candidates)
                accumulator.historical_nonzero += int(np.count_nonzero(np.abs(historical) > SCORE_TOLERANCE))
                accumulator.current_nonzero += int(np.count_nonzero(np.abs(current) > SCORE_TOLERANCE))
                deltas = current - historical
                absolute = np.abs(deltas)
                maximum = float(np.max(absolute))
                accumulator.signed_deltas.extend(deltas.tolist())
                accumulator.absolute_deltas.extend(absolute.tolist())
                accumulator.max_absolute_deltas.append(maximum)
                accumulator.score_changed += int(maximum > SCORE_TOLERANCE)
                accumulator.order_changed += int(historical_order != current_order)
                accumulator.top1_changed += int(historical_order[0] != current_order[0])
                top_count = min(10, len(candidates))
                accumulator.top10_changed += int(
                    set(historical_order[:top_count]) != set(current_order[:top_count])
                )
    views = {accumulator.name: accumulator_result(accumulator, line_count) for accumulator in accumulators}
    primary = views[expected_view_names[0]]
    gates = {
        "eligible_impressions_gate": line_count >= 5_000,
        "distinct_users_gate": len(users) >= 2_000,
        "primary_score_vector_change_gate": primary["score_vector_changed"]["rate"] is not None
        and primary["score_vector_changed"]["rate"] >= 0.20,
        "primary_rank_change_gate": (
            primary["total_order_changed"]["rate"] is not None
            and primary["total_order_changed"]["rate"] >= 0.05
        )
        or (
            primary["top_min10_set_changed"]["rate"] is not None
            and primary["top_min10_set_changed"]["rate"] >= 0.02
        ),
    }
    verdict = (
        "PASS_COVERAGE_AND_OPEN_LABELS"
        if all(gates.values())
        else "KILL_H6_SHARED_FACT_DIRECTION"
    )
    payload = {
        "eligible_impressions": line_count,
        "distinct_users": len(users),
        "candidates": candidate_total,
        "views": views,
        "gates": gates,
        "verdict": verdict,
    }
    counts = {
        "eligible_impressions": line_count,
        "distinct_users": len(users),
        "candidates": candidate_total,
    }
    return payload, counts


def independently_parse_news_anchor_flags(qids: Sequence[str]) -> dict[str, bool]:
    """Fresh label-free news scan used only by the verifier's cohort reconstruction."""
    qid_set = set(qids)
    news_anchor_flags: dict[str, bool] = {}
    with INPUT_PATHS["news"].open("r", encoding="utf-8", newline="") as handle:
        for raw_line in handle:
            fields = raw_line.rstrip("\r\n").split("\t", 7)
            if len(fields) != 8:
                raise RuntimeError("verifier news row does not have exactly eight fields")
            news_id = fields[0]
            if NEWS_ID_PATTERN.fullmatch(news_id) is None or news_id in news_anchor_flags:
                raise RuntimeError("verifier news ID is invalid or duplicate")
            anchored = False
            for encoded_annotations in (fields[6], fields[7]):
                annotations = json.loads(encoded_annotations)
                if not isinstance(annotations, list):
                    raise RuntimeError("verifier news annotations are not an array")
                for annotation in annotations:
                    if not isinstance(annotation, dict):
                        continue
                    qid = str(annotation.get("WikidataId", "")).strip()
                    try:
                        confidence = float(annotation.get("Confidence"))
                    except (TypeError, ValueError):
                        continue
                    if qid in qid_set and math.isfinite(confidence) and confidence >= MINIMUM_CONFIDENCE:
                        anchored = True
            news_anchor_flags[news_id] = anchored
    if len(news_anchor_flags) != EXPECTED_NEWS_ROWS:
        raise RuntimeError("verifier news row-count reproduction failed")
    return news_anchor_flags


def verify_manifest_cohort_against_inputs(
    manifest_path: Path, news_anchor_flags: Mapping[str, bool]
) -> dict[str, int]:
    """Bind every manifest identity field to a fresh, label-blind behavior scan."""
    manifest_handle = manifest_path.open("r", encoding="utf-8", newline="")
    behavior_rows = 0
    eligible_rows = 0
    seen_impressions: set[str] = set()
    users: set[str] = set()
    candidates = 0
    maximum_time = datetime.min.replace(tzinfo=timezone.utc)
    try:
        with INPUT_PATHS["behaviors"].open("r", encoding="utf-8", newline="") as behavior_handle:
            for raw_behavior in behavior_handle:
                behavior_rows += 1
                fields = raw_behavior.rstrip("\r\n").split("\t", 4)
                if len(fields) != 5:
                    raise RuntimeError("verifier behavior row does not have exactly five fields")
                impression_id, user_id = fields[0], fields[1]
                if (
                    not impression_id.strip()
                    or not user_id.strip()
                    or impression_id in seen_impressions
                ):
                    raise RuntimeError("verifier behavior impression/user integrity failed")
                seen_impressions.add(impression_id)
                maximum_time = max(maximum_time, parse_behavior_time(fields[2]))
                history = fields[3].split() if fields[3].strip() else []
                if any(
                    NEWS_ID_PATTERN.fullmatch(news_id) is None
                    or news_id not in news_anchor_flags
                    for news_id in history
                ):
                    raise RuntimeError("verifier behavior history contains an unknown/invalid ID")
                raw_tokens = fields[4].split()
                if not raw_tokens:
                    raise RuntimeError("verifier impression has no candidate tokens")
                candidate_ids = [recover_candidate_id(token) for token in raw_tokens]
                raw_tokens = []
                fields[4] = ""
                raw_behavior = ""
                if (
                    len(candidate_ids) != len(set(candidate_ids))
                    or any(candidate_id not in news_anchor_flags for candidate_id in candidate_ids)
                ):
                    raise RuntimeError("verifier behavior candidates are duplicate or unknown")
                retained_history = history[-50:]
                if (
                    len(candidate_ids) < 2
                    or not retained_history
                    or not any(news_anchor_flags[news_id] for news_id in retained_history)
                ):
                    continue
                manifest_line = manifest_handle.readline()
                if manifest_line == "":
                    raise RuntimeError("manifest ended before fresh eligible-cohort scan")
                manifest_row = json.loads(manifest_line)
                expected_candidate_ids = sorted(candidate_ids)
                observed_candidate_ids = [candidate["n"] for candidate in manifest_row["c"]]
                if (
                    manifest_row["i"] != impression_id
                    or manifest_row["u"] != user_id
                    or manifest_row["h"] != retained_history
                    or observed_candidate_ids != expected_candidate_ids
                ):
                    raise RuntimeError("manifest cohort identity differs from fresh label-blind input scan")
                eligible_rows += 1
                users.add(user_id)
                candidates += len(candidate_ids)
        if manifest_handle.readline() != "":
            raise RuntimeError("manifest has extra rows after fresh eligible-cohort scan")
    finally:
        manifest_handle.close()
    if (
        behavior_rows != EXPECTED_BEHAVIOR_ROWS
        or len(seen_impressions) != EXPECTED_BEHAVIOR_ROWS
        or maximum_time.strftime("%Y-%m-%dT%H:%M:%SZ") != EXPECTED_CUTOFF
    ):
        raise RuntimeError("verifier behavior count/cutoff reproduction failed")
    return {
        "eligible_impressions": eligible_rows,
        "distinct_users": len(users),
        "candidates": candidates,
    }


def verify_result_directory(
    path: Path,
    expected_output_id: str,
    expected_role: str,
    news_anchor_flags: Mapping[str, bool],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if path != (RESULTS_ROOT / expected_output_id).resolve():
        raise RuntimeError("result directory is not the fixed authorized output")
    if not path.is_dir() or {entry.name for entry in path.iterdir()} != {"result.json", "cohort_manifest.jsonl"}:
        raise RuntimeError(f"result directory artifact set is invalid: {path}")
    result_path = path / "result.json"
    manifest_path = path / "cohort_manifest.jsonl"
    result = read_json(result_path)
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != "h6_phase_a_coverage.python.v1"
        or result.get("run_id") != RUN_ID
        or result.get("output_id") != expected_output_id
        or result.get("run_role") != expected_role
        or result.get("cutoff_utc") != EXPECTED_CUTOFF
    ):
        raise RuntimeError("result identity/schema mismatch")
    expected_protocol = {
        "sample_size": SAMPLE_SIZE,
        "confidence_threshold": MINIMUM_CONFIDENCE,
        "maximum_history_articles": 50,
        "score_tolerance": SCORE_TOLERANCE,
        "tie_rule": "ascending hexadecimal SHA-256 of 20260807|impression_id|news_id",
        "primary_relation_policy": "properties in frozen MIND relation_embedding.vec vocabulary",
        "metadata_blocklist": list(METADATA_BLOCKLIST_IDS),
        "removed_anchor_robustness": list(REMOVED_ANCHOR_IDS),
        "graph_implementation": "NumPy-vectorized exact 50-anchor Gram kernel",
    }
    if result.get("protocol") != expected_protocol:
        raise RuntimeError("result protocol declaration mismatch")
    if result.get("artifacts") != {
        "result": "result.json",
        "cohort_manifest": "cohort_manifest.jsonl",
    }:
        raise RuntimeError("result artifact declaration mismatch")
    manifest_hash = sha256_file(manifest_path)
    if result["cohort"]["manifest_sha256"] != manifest_hash:
        raise RuntimeError("result/manifest hash mismatch")
    expected_manifest_schema = {
        "version": "h6_phase_a_manifest.compact.v1",
        "line_format": "one compact JSON object followed by LF",
        "line_order": "immutable behaviors.tsv row order, eligible rows only",
        "top_level_field_order": ["i", "u", "h", "c"],
        "top_level_fields": {
            "i": "impression_id",
            "u": "user_id",
            "h": "retained last-50 history news IDs in supplied order",
            "c": "candidate records in ordinal news_id order",
        },
        "candidate_record": {"n": "news_id", "v": "view tuples in view_order"},
        "view_order": list(VIEW_NAMES),
        "view_tuple_order": [
            "historical_score",
            "current_score",
            "historical_rank",
            "current_rank",
        ],
    }
    if result["cohort"].get("manifest_schema") != expected_manifest_schema:
        raise RuntimeError("manifest schema declaration mismatch")
    view_order = result["cohort"]["manifest_schema"]["view_order"]
    payload, counts = accumulate_manifest_metrics(manifest_path, view_order)
    fresh_counts = verify_manifest_cohort_against_inputs(manifest_path, news_anchor_flags)
    if fresh_counts != counts:
        raise RuntimeError("fresh label-blind cohort reconstruction count mismatch")
    if sha256_bytes(canonical_bytes(payload)) != result["metric_payload_sha256"]:
        raise RuntimeError("deep metric recomputation hash mismatch")
    if (
        payload["views"] != result["views"]
        or payload["verdict"] != result["decision"]["verdict"]
        or any(payload["gates"][name] != result["decision"][name] for name in payload["gates"])
        or result["decision"]["labels_may_be_opened"]
        != (payload["verdict"] == "PASS_COVERAGE_AND_OPEN_LABELS")
    ):
        raise RuntimeError("deep metric recomputation content mismatch")
    if any(counts[key] != result["cohort"][key] for key in counts):
        raise RuntimeError("deep cohort count mismatch")
    for name, expected in EXPECTED_HASHES.items():
        if (
            result["inputs"][name]["path"] != str(INPUT_PATHS[name].resolve())
            or result["inputs"][name]["sha256"] != expected
            or sha256_file(INPUT_PATHS[name]) != expected
        ):
            raise RuntimeError("result or current immutable input hash mismatch")
    if (
        set(result.get("inputs", {})) != set(EXPECTED_HASHES)
        or result["provenance"].get("input_sha256_at_start") != EXPECTED_HASHES
        or result["provenance"].get("input_sha256_before_publication") != EXPECTED_HASHES
    ):
        raise RuntimeError("result immutable-input provenance mismatch")
    expected_provenance = {
        "runner": file_record(SCRIPT_PATH),
        "committed_protocol": file_record(PROTOCOL_PATH),
        "runtime_correction": file_record(CORRECTION_PATH),
        "launcher": file_record(LAUNCHER_PATH),
        "base_interpreter": file_record(Path(str(getattr(sys, "_base_executable", ""))).resolve()),
        "venv_launcher": file_record(VENV_LAUNCHER_PATH),
        "venv_config": file_record(VENV_CONFIG_PATH),
    }
    for name, expected_record in expected_provenance.items():
        if result["provenance"].get(name) != expected_record:
            raise RuntimeError(f"result provenance mismatch: {name}")
    authorization_record = result["provenance"].get("authorization")
    if (
        not isinstance(authorization_record, dict)
        or file_record(Path(str(authorization_record.get("path", ""))).resolve()) != authorization_record
    ):
        raise RuntimeError("result authorization provenance mismatch")
    ledger = Path(result["provenance"]["async_error_ledger"]["path"])
    if (
        not ledger.is_file()
        or ledger.stat().st_size != 0
        or file_record(ledger) != result["provenance"]["async_error_ledger"]
    ):
        raise RuntimeError("runner asynchronous-error ledger is missing or nonempty")
    if (
        result["decision"].get("all_sanity_checks_passed") is not True
        or not isinstance(result.get("sanity_checks"), list)
        or any(check.get("passed") is not True for check in result["sanity_checks"])
        or result["cohort"].get("manifest_contains_candidate_suffix") is not False
    ):
        raise RuntimeError("result sanity declaration mismatch")
    expected_sanity_names = {
        "immutable_input_hashes",
        "news_rows",
        "behavior_rows",
        "sample_qids",
        "relation_ids",
        "manifest_hash",
        "candidate_suffix_absent",
        "async_error_ledger_empty",
    }
    if {check.get("name") for check in result["sanity_checks"]} != expected_sanity_names:
        raise RuntimeError("result sanity-check inventory mismatch")
    return result, {
        "directory": str(path.resolve()),
        "result": file_record(result_path),
        "manifest": file_record(manifest_path),
        "metric_payload_sha256": result["metric_payload_sha256"],
        "counts": counts,
    }


def verify_replays(authorization: Mapping[str, Any]) -> dict[str, Any]:
    verify_thread_environment()
    verify_python_thread_state()
    async_ledger = Path(str(authorization["async_error_ledger"])).resolve()
    install_async_hooks(async_ledger)
    verify_live_launcher_contract(authorization)
    runtime_records = verify_authorized_runtime(authorization)
    immutable_hashes = verify_immutable_hashes()
    qids, _, _, _, _, _ = acquire_fact_sets()
    news_anchor_flags = independently_parse_news_anchor_flags(qids)
    primary_path = Path(str(authorization["primary_directory"])).resolve()
    replay_path = Path(str(authorization["replay_directory"])).resolve()
    if (
        primary_path != (RESULTS_ROOT / RUN_ID).resolve()
        or replay_path != (RESULTS_ROOT / REPLAY_ID).resolve()
    ):
        raise RuntimeError("verifier result path authorization mismatch")
    primary, primary_record = verify_result_directory(
        primary_path, RUN_ID, "primary", news_anchor_flags
    )
    replay, replay_record = verify_result_directory(
        replay_path, REPLAY_ID, "exact_replay", news_anchor_flags
    )
    if (
        primary_record["manifest"]["sha256"] != replay_record["manifest"]["sha256"]
        or primary_record["metric_payload_sha256"] != replay_record["metric_payload_sha256"]
        or primary["views"] != replay["views"]
        or primary["decision"] != replay["decision"]
    ):
        raise RuntimeError("exact replay did not reproduce manifest and metrics")
    require_no_async_failures()
    verification_path = Path(str(authorization["verification_path"])).resolve()
    launch_directory = Path(str(authorization["launch_directory"])).resolve()
    if verification_path.parent != launch_directory or verification_path.name != "deep_verification.json":
        raise RuntimeError("verification publication path is not fixed inside launch directory")
    verification = {
        "schema_version": "h6_phase_a_verification.v1",
        "status": "VERIFIED_EXACT_REPLAY",
        "process_pid": os.getpid(),
        "runtime": runtime_records,
        "authorization": file_record(Path(str(authorization["authorization_path"]))),
        "launch_id": str(authorization["launch_id"]),
        "launcher_pid": int(authorization["launcher_pid"]),
        "authorization_token_sha256": sha256_bytes(str(authorization["token"]).encode("utf-8")),
        "immutable_input_sha256": immutable_hashes,
        "primary": primary_record,
        "replay": replay_record,
        "identical_manifest_sha256": primary_record["manifest"]["sha256"],
        "identical_metric_payload_sha256": primary_record["metric_payload_sha256"],
        "async_error_ledger": file_record(async_ledger),
        "verified_time_ns": time.time_ns(),
    }
    verify_live_launcher_contract(authorization)
    verify_thread_environment()
    verify_python_thread_state()
    if verify_authorized_runtime(authorization) != runtime_records:
        raise RuntimeError("authorized runtime changed before verifier publication")
    if verify_immutable_hashes() != immutable_hashes:
        raise RuntimeError("immutable input changed before verifier publication")
    require_no_async_failures()
    write_exclusive_json(verification_path, verification)
    require_no_async_failures()
    return {
        "status": "H6_PHASE_A_VERIFY_COMPLETE",
        "process_pid": os.getpid(),
        "verification_path": str(verification_path),
        "verification_sha256": sha256_file(verification_path),
        "manifest_sha256": verification["identical_manifest_sha256"],
        "metric_payload_sha256": verification["identical_metric_payload_sha256"],
    }


def self_test() -> None:
    np = load_numpy()
    verify_thread_environment()
    verify_python_thread_state()
    expected_h6 = ROOT / "experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence"
    if H6_DIR != expected_h6.resolve() or set(INPUT_PATHS) != set(EXPECTED_HASHES):
        raise RuntimeError("self-test repository/input path anchoring failed")
    if verify_immutable_hashes() != EXPECTED_HASHES:
        raise RuntimeError("self-test immutable input-path/hash fixture failed")

    fact_sets = [
        {"a", "b"},
        {"b", "c"},
        set(),
        {"a", "b"},
    ]
    gram = gram_from_fact_sets(fact_sets)
    expected_gram = np.asarray(
        [
            [1.0, 0.5, 0.0, 1.0],
            [0.5, 1.0, 0.0, 0.5],
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.5, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    if not np.allclose(gram, expected_gram, rtol=0.0, atol=1e-15):
        raise RuntimeError("self-test Gram kernel failed")

    # Exhaustively compare the 4-anchor Gram scorer with a direct fact-space scorer.
    fact_universe = sorted(set().union(*fact_sets))
    direct_entities = np.zeros((len(fact_sets), len(fact_universe)), dtype=np.float64)
    for entity_index, facts in enumerate(fact_sets):
        if facts:
            for fact in facts:
                direct_entities[entity_index, fact_universe.index(fact)] = 1.0
            direct_entities[entity_index] /= np.linalg.norm(direct_entities[entity_index])
    if not np.allclose(direct_entities @ direct_entities.T, gram, rtol=0.0, atol=1e-15):
        raise RuntimeError("self-test direct/Gram entity parity failed")
    incidence = np.asarray(
        [[float((mask >> index) & 1) for index in range(4)] for mask in range(16)],
        dtype=np.float64,
    )
    active = incidence * (np.diag(gram) > 0.0)[None, :]
    norm_squared = np.sum((active @ gram) * active, axis=1)
    coefficients = np.zeros_like(active)
    nonzero = norm_squared > 0.0
    coefficients[nonzero] = active[nonzero] / np.sqrt(norm_squared[nonzero, None])
    projection = coefficients @ gram
    direct_news_raw = active @ direct_entities
    direct_news = np.zeros_like(direct_news_raw)
    direct_norms = np.linalg.norm(direct_news_raw, axis=1)
    direct_news[direct_norms > 0.0] = (
        direct_news_raw[direct_norms > 0.0] / direct_norms[direct_norms > 0.0, None]
    )
    if not np.allclose(projection @ coefficients.T, direct_news @ direct_news.T, rtol=0.0, atol=2e-15):
        raise RuntimeError("self-test direct/Gram news parity failed")
    all_candidate_indices = np.arange(16, dtype=np.int64)
    for first_history, second_history in itertools.product(range(16), repeat=2):
        user_raw = coefficients[[first_history, second_history]].sum(axis=0)
        user_norm_squared = float(user_raw @ gram @ user_raw)
        gram_scores = (
            projection[all_candidate_indices] @ user_raw / math.sqrt(user_norm_squared)
            if user_norm_squared > 0.0
            else np.zeros(16, dtype=np.float64)
        )
        direct_user_raw = direct_news[[first_history, second_history]].sum(axis=0)
        direct_user_norm = float(np.linalg.norm(direct_user_raw))
        direct_scores = (
            direct_news @ (direct_user_raw / direct_user_norm)
            if direct_user_norm > 0.0
            else np.zeros(16, dtype=np.float64)
        )
        if not np.allclose(gram_scores, direct_scores, rtol=0.0, atol=3e-15):
            raise RuntimeError("self-test exhaustive direct/Gram user-score parity failed")

    if recover_candidate_id("N10-0") != "N10" or recover_candidate_id("N10-1") != "N10":
        raise RuntimeError("self-test label-blind candidate recovery failed")
    historical_probe = validate_candidate_scores(np.asarray([0.9e-12], dtype=np.float64))
    current_probe = validate_candidate_scores(np.asarray([1.1e-12], dtype=np.float64))
    if (
        historical_probe[0] != 0.9e-12
        or current_probe[0] != 1.1e-12
        or abs(float(current_probe[0] - historical_probe[0])) > SCORE_TOLERANCE
        or not (abs(float(historical_probe[0])) <= SCORE_TOLERANCE < abs(float(current_probe[0])))
    ):
        raise RuntimeError("self-test raw sub-tolerance score preservation failed")
    chain_scores = np.asarray([2.0e-12, 1.1e-12, 0.2e-12], dtype=np.float64)
    if frozen_tolerance_groups(chain_scores) != [[0, 1], [2]]:
        raise RuntimeError("self-test first-score-anchored nontransitive grouping failed")
    scores = np.asarray([0.5, 0.5], dtype=np.float64)
    first_order, _ = frozen_ranking(["N10", "N20"], scores, "I1")
    reverse_order, _ = frozen_ranking(["N20", "N10"], scores, "I1")
    if [(["N10", "N20"])[index] for index in first_order] != [
        (["N20", "N10"])[index] for index in reverse_order
    ]:
        raise RuntimeError("self-test tie ranking is candidate-order dependent")
    ranking_palette = (-2.0e-12, -1.1e-12, -0.9e-12, 0.0, 0.9e-12, 1.1e-12, 2.0e-12)
    ranking_ids = ["N1", "N2", "N3", "N4"]
    for fixture in itertools.product(ranking_palette, repeat=4):
        fixture_scores = np.asarray(fixture, dtype=np.float64)
        if frozen_ranking(ranking_ids, fixture_scores, "SELFTEST") != verifier_frozen_ranks(
            ranking_ids, fixture_scores, "SELFTEST"
        ):
            raise RuntimeError("self-test exhaustive runner/verifier ranking parity failed")
    temporary_root = Path(os.environ.get("TEMP", str(H6_DIR))) / f"provicold-h6-python-selftest-{uuid.uuid4().hex}"
    temporary_root.mkdir()
    try:
        target = temporary_root / "artifact.json"
        write_exclusive_json(target, {"passed": True})
        if read_json(target) != {"passed": True}:
            raise RuntimeError("self-test atomic JSON publication failed")
        valid_manifest_row = {
            "i": "SELFTEST-I",
            "u": "SELFTEST-U",
            "h": ["N9"],
            "c": [
                {"n": "N1", "v": [[0.5, 0.4, 1, 1], [0.5, 0.4, 1, 1], [0.5, 0.4, 1, 1]]},
                {"n": "N2", "v": [[0.1, 0.2, 2, 2], [0.1, 0.2, 2, 2], [0.1, 0.2, 2, 2]]},
            ],
        }
        valid_manifest = temporary_root / "valid.jsonl"
        write_exclusive_bytes(valid_manifest, json.dumps(valid_manifest_row, separators=(",", ":")).encode("utf-8") + b"\n")
        accumulate_manifest_metrics(valid_manifest, VIEW_NAMES)

        mutations: list[bytes] = []
        extra_key = json.loads(json.dumps(valid_manifest_row))
        extra_key["c"][0]["x"] = 1
        mutations.append(json.dumps(extra_key, separators=(",", ":")).encode("utf-8") + b"\n")
        wrong_rank = json.loads(json.dumps(valid_manifest_row))
        wrong_rank["c"][0]["v"][0][2] = 2
        mutations.append(json.dumps(wrong_rank, separators=(",", ":")).encode("utf-8") + b"\n")
        mutations.append(json.dumps(valid_manifest_row, separators=(", ", ": ")).encode("utf-8") + b"\r\n")
        for mutation_index, mutation in enumerate(mutations):
            mutation_path = temporary_root / f"mutation_{mutation_index}.jsonl"
            write_exclusive_bytes(mutation_path, mutation)
            try:
                accumulate_manifest_metrics(mutation_path, VIEW_NAMES)
            except RuntimeError:
                pass
            else:
                raise RuntimeError("self-test verifier mutation fixture was accepted")
    finally:
        if temporary_root.parent.resolve() not in {
            Path(os.environ.get("TEMP", str(H6_DIR))).resolve(),
            H6_DIR.resolve(),
        } or not temporary_root.name.startswith("provicold-h6-python-selftest-"):
            raise RuntimeError("refusing unsafe self-test cleanup")
        shutil.rmtree(temporary_root)
    require_no_async_failures()
    print("H6_PHASE_A_PYTHON_SELFTEST_OK", flush=True)


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
    if args.command == "self-test":
        if authorization.get("self_test_only") is not True:
            raise RuntimeError("self-test authorization is not strictly isolated")
        async_ledger = Path(str(authorization["async_error_ledger"])).resolve()
        install_async_hooks(async_ledger)
        verify_live_launcher_contract(authorization)
        self_test()
        verify_live_launcher_contract(authorization)
        verify_thread_environment()
        verify_python_thread_state()
        require_no_async_failures()
        summary = {
            "status": "H6_PHASE_A_PYTHON_SELFTEST_COMPLETE",
            "process_pid": os.getpid(),
            "runner_sha256": sha256_file(SCRIPT_PATH),
            "launcher_sha256": sha256_file(LAUNCHER_PATH),
            "protocol_sha256": sha256_file(PROTOCOL_PATH),
            "correction_sha256": sha256_file(CORRECTION_PATH),
            "async_error_ledger": file_record(async_ledger),
        }
    elif args.command == "run":
        summary = run_phase_a(authorization)
    else:
        summary = verify_replays(authorization)
    print(json.dumps(summary, separators=(",", ":"), allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
