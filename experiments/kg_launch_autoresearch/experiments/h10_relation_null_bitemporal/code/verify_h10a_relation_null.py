#!/usr/bin/env python3
"""Independent verifier for the prospectively locked H10A experiment.

This module deliberately imports no runner code.  It reconstructs the H10A
cohort, relation graphs, PCG64DXSM switch chains, canonical binary64 operators,
scores, metrics, reached stages, and scientific verdict.  It also performs
separately accumulated outer-product, direct-score, and scalar-inertia checks.

The file is intended to be invoked only by the hash-binding Windows launcher;
it is not a convenience command-line evaluator.  ``self-test`` is synthetic
only and cannot open a real H10 input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


PROTOCOL_SHA256 = "D6083A0BE49DF3C8771F99882DC0A957E81B3DB7E60BFADA47E770CC52E4CEF3"
PYTHON_VERSION = (3, 12, 13)
NUMPY_VERSION = "2.4.4"
ANCHOR_COUNT = 50
AUDIT_SIZE = 8_192
EXPECTED_RELATIONS = 1_091
EXPECTED_MANIFEST_BYTES = 224_785_295
EXPECTED_COUNTS = {
    "news_rows": 42_416,
    "supported_news": 12_060,
    "patterns": 812,
    "impressions": 64_443,
    "users": 43_374,
    "candidate_occurrences": 2_422_258,
    "supported_candidate_occurrences": 512_071,
    "gt10_candidates": 48_422,
    "gt10_candidates_and_support": 17_436,
    "ge2_supported_candidates": 44_341,
    "histories_with_support": 64_443,
    "audit_impressions": AUDIT_SIZE,
}
EXPECTED_INPUT_HASHES = {
    "news": "E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822",
    "relations": "D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A",
    "facts": "13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D",
    "phase_a_result": "B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF",
    "phase_a_manifest": "522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5",
    "phase_a_completion": "AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06",
}

VIEW_ORDER = ("primary", "metadata_blocklist", "hub_removal")
ENDPOINT_ORDER = ("H", "C")
VIEW_ORDINAL = {name: index for index, name in enumerate(VIEW_ORDER)}
ENDPOINT_ORDINAL = {name: index for index, name in enumerate(ENDPOINT_ORDER)}
METADATA_BLOCKLIST = frozenset(
    {"P1343", "P1424", "P5008", "P6104", "P7867", "P8744", "P9241",
     "P2354", "P8402", "P10280", "P1889"}
)
HUB_QIDS = frozenset({"Q30", "Q22686"})
VIEW_BUDGETS = {
    "primary": {"relations": 110, "H": 4_481, "C": 5_529, "proposals": 3_003_000},
    "metadata_blocklist": {
        "relations": 105, "H": 4_388, "C": 5_104, "proposals": 949_200,
    },
    "hub_removal": {"relations": 103, "H": 3_644, "C": 4_577, "proposals": 822_100},
}
SCIENTIFIC_FILES = (
    "scientific_payload.json",
    "state_metrics.jsonl",
    "state_digests.jsonl",
    "chain_diagnostics.jsonl",
    "parity_checks.jsonl",
)
EXPECTED_PHASE_A_COMMIT = "b1f247abf3185a2eaec8588b358c488af8f78342"
AUDIT_PREFIX = b"20260807|H10A|audit|"
RANK_PREFIX = b"20260807|H10A|rank|"
PARITY_PREFIX = b"20260807|H10A|parity|"
PAIR_PREFIX = b"20260807|H10A|pair|"
NULL_PREFIX = b"20260807|H10A|null|"
PCG_PROBE_PREFIX = b"H10A_PCG_PROBE_V1\n"
PCG_PROBE_SEED_TEXT = b"20260807|H10A|PCG_PROBE_V1"
QID_RE = re.compile(r"^Q[0-9]+$")
PROPERTY_RE = re.compile(r"^P[0-9]+$")
NEWS_RE = re.compile(r"^N[0-9]+$")
FACT_RE = re.compile(r"^(P[0-9]+)\|(Q[0-9]+)$")
MANIFEST_LABEL_RE = re.compile(rb'"N[0-9]+-[01]"')
HASH_RE = re.compile(r"^[0-9A-F]{64}$")
THREAD_ENV_NAMES = (
    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)

SCRIPT_PATH = Path(__file__).resolve()
H10_DIR = SCRIPT_PATH.parent.parent
ROOT = H10_DIR.parents[3]
PROTOCOL_PATH = H10_DIR / "protocol.md"
IMPLEMENTATION_LOCK_PATH = H10_DIR / "implementation_lock.md"
LAUNCHER_PATH = SCRIPT_PATH.with_name("run_h10a_relation_null_safe.ps1")
RUNNER_PATH = SCRIPT_PATH.with_name("run_h10a_relation_null.py")
GENERATOR_PATH = SCRIPT_PATH.with_name("generate_h10a_synthetic_fixture.py")
FIXTURE_MANIFEST_PATH = H10_DIR / "synthetic_fixture_manifest.json"
PROBE_COMPLETION_PATH = H10_DIR / "probe_artifacts/h10a_pcg_probe_completion.json"
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
_ASYNC_LEDGER: Path | None = None
_ASYNC_FAILURES: list[dict[str, Any]] = []
_INNER_LOCK_FD: int | None = None
_INNER_LOCK_RECORD: dict[str, Any] | None = None
_BOOTSTRAP_INPUT_HASHES: dict[str, str] | None = None

RUNTIME_FILE_KEYS = frozenset(
    {
        "runner", "verifier", "launcher", "protocol", "active_lock",
        "base_interpreter", "venv_launcher", "venv_config",
        "synthetic_generator", "synthetic_fixture_manifest",
        "numpy_package_manifest",
    }
)
RUNTIME_HASH_FIELDS = {
    "runner": "runner_sha256",
    "verifier": "verifier_sha256",
    "launcher": "launcher_sha256",
    "protocol": "protocol_sha256",
    "active_lock": "active_lock_sha256",
    "base_interpreter": "base_interpreter_sha256",
    "venv_launcher": "venv_launcher_sha256",
    "venv_config": "venv_config_sha256",
    "synthetic_generator": "synthetic_generator_sha256",
    "synthetic_fixture_manifest": "synthetic_fixture_manifest_sha256",
    "numpy_package_manifest": "numpy_manifest_sha256",
}
RUNTIME_HASH_KEYS = frozenset(RUNTIME_HASH_FIELDS.values()) | {
    "expected_pcg_probe_sha256", "probe_completion_sha256"
}
AUTHORIZATION_KEYS = frozenset(
    {
        "schema_version", "action", "run_role", "output_id",
        "output_directory", "subject_kind", "subject_path", "subject_sha256",
        "synthetic_mode", "probe_mode", "launch_id", "launcher_pid", "token",
        "token_sha256", "authorization_path", "launch_directory", "outer_lock",
        "inner_lock", "inner_lock_release_path",
        "resource_inner_lock_release_path", "async_error_ledger",
        "process_start_path", "process_ack_path", "protocol_path",
        "protocol_sha256", "launcher_path", "launcher_sha256",
        "active_lock_path", "active_lock_sha256", "base_interpreter",
        "base_interpreter_sha256", "venv_launcher", "venv_launcher_sha256",
        "venv_config", "venv_config_sha256", "synthetic_generator_path",
        "synthetic_generator_sha256", "synthetic_fixture_manifest_path",
        "synthetic_fixture_manifest_sha256", "runtime_files", "runtime_hashes",
        "expected_pcg_probe_sha256", "pcg_probe_digest_sha256",
        "numpy_manifest_path", "numpy_manifest_sha256", "immutable_input_sha256",
        "immutable_input_paths", "phase_a_commit", "label_free_only",
        "candidate_labels_forbidden", "candidate_suffix_labels_forbidden",
        "behaviors_tsv_forbidden", "authorized_unix_ns", "verification_path",
        "verification_crosslink", "primary_directory", "replay_directory",
        "primary_output_directory", "replay_output_directory",
    }
)
RUNNER_AUTHORIZATION_KEYS = (
    AUTHORIZATION_KEYS
    - {
        "verification_path", "verification_crosslink", "primary_directory",
        "replay_directory", "primary_output_directory", "replay_output_directory",
    }
    | {"synthetic_fixture_manifest", "forced_full_path"}
)


def np_module() -> Any:
    global _NP
    if _NP is None:
        import numpy as np  # type: ignore

        if np.__version__ != NUMPY_VERSION:
            raise RuntimeError(f"NumPy version mismatch: {np.__version__}")
        _NP = np
    return _NP


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_object_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_canonical_json(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(raw)
    if canonical_object_bytes(value) != raw:
        raise RuntimeError(f"noncanonical JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for index, raw in enumerate(handle):
            if not raw.endswith(b"\n") or raw.endswith(b"\r\n"):
                raise RuntimeError(f"non-LF JSONL record {index}: {path}")
            value = json.loads(raw)
            if not isinstance(value, dict) or canonical_object_bytes(value) != raw:
                raise RuntimeError(f"noncanonical JSONL record {index}: {path}")
            result.append(value)
    return result


def file_record(path: Path) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def require_file_record_shape(record: Any, label: str) -> Mapping[str, Any]:
    if (
        not isinstance(record, dict)
        or set(record) != {"bytes", "path", "sha256"}
        or not isinstance(record.get("bytes"), int)
        or isinstance(record.get("bytes"), bool)
        or int(record["bytes"]) < 0
        or not isinstance(record.get("path"), str)
        or not str(record["path"])
        or not Path(str(record["path"])).is_absolute()
        or not isinstance(record.get("sha256"), str)
        or HASH_RE.fullmatch(str(record["sha256"])) is None
    ):
        raise RuntimeError(f"file record is malformed: {label}")
    return record


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
    temporary = path.parent / f".verify-{uuid.uuid4().hex}.tmp"
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
    write_exclusive_bytes(path, canonical_object_bytes(value))


def install_async_hooks(ledger: Path) -> None:
    global _ASYNC_LEDGER
    if not ledger.is_file() or ledger.stat().st_size != 0:
        raise RuntimeError("asynchronous-error ledger must pre-exist and be empty")
    _ASYNC_LEDGER = ledger

    def record(kind: str, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        row = {
            "exception": str(exc_value),
            "exception_type": getattr(exc_type, "__name__", str(exc_type)),
            "kind": kind,
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        }
        _ASYNC_FAILURES.append(row)
        with ledger.open("ab", buffering=0) as handle:
            handle.write(canonical_object_bytes(row))
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
        raise RuntimeError(f"{len(_ASYNC_FAILURES)} asynchronous failures recorded")
    if _ASYNC_LEDGER is not None and _ASYNC_LEDGER.stat().st_size:
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
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    open_process.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    ctypes.set_last_error(0)
    handle = open_process(0x1000, False, process_id)
    if handle:
        ctypes.set_last_error(0)
        if not close_handle(handle):
            raise ctypes.WinError(ctypes.get_last_error())
        return True
    error = ctypes.get_last_error()
    if error == 5:  # Access denied still proves that the PID exists.
        return True
    if error in {0, 87, 1168}:
        return False
    raise ctypes.WinError(error)


def process_peak_resident_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
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
        handle = get_current_process()
        ctypes.set_last_error(0)
        if not get_process_memory_info(handle, ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        peak = int(counters.PeakWorkingSetSize)
        if peak <= 0:
            raise RuntimeError("Windows peak working-set counter is not positive")
        return peak
    import resource

    usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return usage if sys.platform == "darwin" else usage * 1024


def verify_native_process_api() -> None:
    """Exercise the typed native calls without starting another process."""
    if not process_is_alive(os.getpid()):
        raise RuntimeError("native process liveness self-test failed")
    if process_is_alive(0) or process_is_alive(-1):
        raise RuntimeError("native invalid-PID self-test failed")
    if process_peak_resident_bytes() <= 0:
        raise RuntimeError("native peak-working-set self-test failed")


def verify_single_thread_environment() -> None:
    if sys.version_info[:3] != PYTHON_VERSION:
        raise RuntimeError(f"CPython version mismatch: {sys.version_info[:3]}")
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("verifier is not on MainThread")
    live = [thread for thread in threading.enumerate() if thread.is_alive()]
    if len(live) != 1 or live[0] is not threading.main_thread():
        raise RuntimeError("unexpected live Python thread")
    if any(os.environ.get(name) != "1" for name in THREAD_ENV_NAMES):
        raise RuntimeError("numerical thread bounds are not all one")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1":
        raise RuntimeError("CUDA must be disabled")
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("PYTHONHASHSEED must be zero")


def assert_outer_lock(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError("outer launcher lock is absent")
    if os.name == "nt":
        try:
            probe = path.open("rb")
        except PermissionError:
            return
        probe.close()
        raise RuntimeError("outer launcher lock is not held share-none")


def resolve_bound_path(auth: Mapping[str, Any], field: str) -> Path:
    raw = auth.get(field)
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"missing bound path: {field}")
    return Path(raw).resolve()


def verify_file_binding(auth: Mapping[str, Any], path_field: str, hash_field: str) -> dict[str, Any]:
    path = resolve_bound_path(auth, path_field)
    if not path.is_file():
        raise RuntimeError(f"bound file is missing: {path_field}")
    record = file_record(path)
    if record["sha256"] != auth.get(hash_field):
        raise RuntimeError(f"bound hash mismatch: {path_field}")
    return record


def expected_synthetic_manifest() -> dict[str, Any]:
    """Independent literal reconstruction of the generator's semantic contract."""
    return {
        "V_score_passes": 280,
        "candidate_anchor_nonzeros": 1_354_440,
        "candidate_count_formula": "11+(impression_ordinal mod 50)",
        "candidate_id_formula": "SYN{impression_ordinal:04d}_{candidate_ordinal:02d}",
        "candidate_occurrences": 290_648,
        "candidate_pattern_formula": "global_occurrence mod 812",
        "edge_allocation": (
            "floor(M/R)+1 for relation ordinal < M mod R; "
            "floor(M/R) otherwise"
        ),
        "edge_column_formula": "(3*t+11*r+5*endpoint_ordinal) mod 17",
        "edge_row_formula": "(t+7*r+3*endpoint_ordinal) mod 50",
        "endpoint_ordinals": {"C": 1, "H": 0},
        "hub_row_formula": "2+((t+7*r+3*endpoint_ordinal) mod 48)",
        "impressions": 8_192,
        "news_patterns": 812,
        "pattern_formula": "distinct ten-bit masks p=0..811 over anchors 0..9",
        "proposals": 4_774_300,
        "ranking_score_passes": 280,
        "relation_id_formula": "S000 onward",
        "retained_endpoint_states": 280,
        "schema_version": "h10a_synthetic_fixture.v1",
        "supported_candidate_occurrences": 290_290,
        "target_columns_per_relation": 17,
        "user_anchor_nonzeros": 32_768,
        "user_formula": (
            "anchors (i+13*t) mod 50 for t=0..3, each value binary64 0.5"
        ),
        "views": {
            "hub_removal": {"C_edges": 4_577, "H_edges": 3_644, "relations": 103},
            "metadata_blocklist": {
                "C_edges": 5_104,
                "H_edges": 4_388,
                "relations": 105,
            },
            "primary": {"C_edges": 5_529, "H_edges": 4_481, "relations": 110},
        },
    }


def regenerate_numpy_manifest() -> bytes:
    np = np_module()
    package = Path(np.__file__).resolve().parent
    rows: list[dict[str, Any]] = []
    for path in sorted(
        package.rglob("*"), key=lambda item: item.relative_to(package).as_posix()
    ):
        if path.is_symlink():
            raise RuntimeError(f"NumPy package symlink forbidden: {path}")
        stat = path.lstat()
        if os.name == "nt" and getattr(stat, "st_file_attributes", 0) & 0x400:
            raise RuntimeError(f"NumPy package reparse point forbidden: {path}")
        if path.is_file():
            rows.append(
                {
                    "bytes": stat.st_size,
                    "path": path.relative_to(package).as_posix(),
                    "sha256": sha256_file(path),
                }
            )
    return b"".join(canonical_object_bytes(row) for row in rows)


def validate_runtime_contract(auth: Mapping[str, Any]) -> dict[str, Any]:
    records = auth.get("runtime_files")
    hashes = auth.get("runtime_hashes")
    if (
        not isinstance(records, dict)
        or set(records) != RUNTIME_FILE_KEYS
        or not isinstance(hashes, dict)
        or set(hashes) != RUNTIME_HASH_KEYS
        or any(records[name] is None for name in RUNTIME_FILE_KEYS)
    ):
        raise RuntimeError("verifier runtime-map schema/null semantics mismatch")
    observed: dict[str, Any] = {}
    for name in sorted(RUNTIME_FILE_KEYS):
        record = require_file_record_shape(records[name], f"runtime/{name}")
        path = Path(str(record["path"])).resolve()
        if not path.is_file():
            raise RuntimeError(f"runtime file missing: {name}")
        actual = file_record(path)
        if actual != record:
            raise RuntimeError(f"runtime file binding changed: {name}")
        hash_field = RUNTIME_HASH_FIELDS[name]
        if record["sha256"] != hashes.get(hash_field):
            raise RuntimeError(f"runtime hash-map mismatch: {name}")
        observed[name] = dict(record)
    expected_paths = {
        "runner": RUNNER_PATH,
        "verifier": SCRIPT_PATH,
        "launcher": LAUNCHER_PATH,
        "protocol": PROTOCOL_PATH,
        "active_lock": IMPLEMENTATION_LOCK_PATH,
        "venv_launcher": VENV_LAUNCHER_PATH,
        "venv_config": VENV_CONFIG_PATH,
        "synthetic_generator": GENERATOR_PATH,
        "synthetic_fixture_manifest": FIXTURE_MANIFEST_PATH,
    }
    for name, expected in expected_paths.items():
        if Path(str(records[name]["path"])).resolve() != expected.resolve():
            raise RuntimeError(f"runtime path mismatch: {name}")
    if records["protocol"]["sha256"] != PROTOCOL_SHA256:
        raise RuntimeError("locked protocol bytes changed")
    top_level_hashes = {
        "launcher": "launcher_sha256",
        "protocol": "protocol_sha256",
        "active_lock": "active_lock_sha256",
        "base_interpreter": "base_interpreter_sha256",
        "venv_launcher": "venv_launcher_sha256",
        "venv_config": "venv_config_sha256",
        "synthetic_generator": "synthetic_generator_sha256",
        "synthetic_fixture_manifest": "synthetic_fixture_manifest_sha256",
        "numpy_package_manifest": "numpy_manifest_sha256",
    }
    for name, field in top_level_hashes.items():
        if auth.get(field) != records[name]["sha256"]:
            raise RuntimeError(f"authorization/runtime hash mismatch: {name}")
    top_level_paths = {
        "launcher": "launcher_path",
        "protocol": "protocol_path",
        "active_lock": "active_lock_path",
        "base_interpreter": "base_interpreter",
        "venv_launcher": "venv_launcher",
        "venv_config": "venv_config",
        "synthetic_generator": "synthetic_generator_path",
        "synthetic_fixture_manifest": "synthetic_fixture_manifest_path",
        "numpy_package_manifest": "numpy_manifest_path",
    }
    for name, field in top_level_paths.items():
        if resolve_bound_path(auth, field) != Path(str(records[name]["path"])).resolve():
            raise RuntimeError(f"authorization/runtime path mismatch: {name}")
    if (
        auth.get("subject_sha256") != records["verifier"]["sha256"]
        or hashes.get("expected_pcg_probe_sha256")
        != auth.get("expected_pcg_probe_sha256")
        or auth.get("expected_pcg_probe_sha256")
        != auth.get("pcg_probe_digest_sha256")
        or records["numpy_package_manifest"]["sha256"]
        != auth.get("numpy_manifest_sha256")
        or not PROBE_COMPLETION_PATH.is_file()
        or hashes.get("probe_completion_sha256") != sha256_file(PROBE_COMPLETION_PATH)
    ):
        raise RuntimeError("verifier/PCG/NumPy main binding mismatch")
    if (
        resolve_bound_path(auth, "numpy_manifest_path")
        != Path(str(records["numpy_package_manifest"]["path"])).resolve()
        or resolve_bound_path(auth, "synthetic_fixture_manifest_path")
        != FIXTURE_MANIFEST_PATH.resolve()
        or resolve_bound_path(auth, "synthetic_generator_path")
        != GENERATOR_PATH.resolve()
    ):
        raise RuntimeError("top-level runtime path aliases differ")
    if read_canonical_json(FIXTURE_MANIFEST_PATH) != expected_synthetic_manifest():
        raise RuntimeError("synthetic fixture semantic manifest mismatch")
    regenerated_manifest = regenerate_numpy_manifest()
    manifest_path = resolve_bound_path(auth, "numpy_manifest_path")
    if (
        regenerated_manifest != manifest_path.read_bytes()
        or sha256_bytes(regenerated_manifest) != auth.get("numpy_manifest_sha256")
    ):
        raise RuntimeError("installed NumPy tree differs from bound probe manifest")
    return observed


def bootstrap_handshake(args: argparse.Namespace) -> dict[str, Any]:
    global _BOOTSTRAP_INPUT_HASHES, _INNER_LOCK_RECORD
    authorization_path = Path(args.authorization).resolve()
    auth = read_json(authorization_path)
    if not isinstance(auth, dict):
        raise RuntimeError("authorization is not an object")
    if set(auth) != AUTHORIZATION_KEYS:
        raise RuntimeError("authorization key set differs from locked verifier schema")
    verify_single_thread_environment()
    verify_native_process_api()
    action = str(args.command)
    authorization_sha = sha256_file(authorization_path)
    token_sha = sha256_bytes(args.token.encode("utf-8"))
    subject_path = resolve_bound_path(auth, "subject_path")
    if (
        auth.get("schema_version") != "h10a_launcher_authorization.v1"
        or auth.get("action") != action
        or auth.get("run_role") != "verifier"
        or auth.get("output_id") != "deep_verification"
        or auth.get("token") != args.token
        or auth.get("token_sha256") != token_sha
        or auth.get("subject_kind") != "verifier"
        or subject_path != SCRIPT_PATH
        or auth.get("subject_sha256") != sha256_file(SCRIPT_PATH)
        or resolve_bound_path(auth, "authorization_path") != authorization_path
        or auth.get("protocol_sha256") != PROTOCOL_SHA256
        or resolve_bound_path(auth, "protocol_path") != PROTOCOL_PATH
        or auth.get("probe_mode") is not False
        or auth.get("label_free_only") is not True
        or auth.get("candidate_labels_forbidden") is not True
        or auth.get("candidate_suffix_labels_forbidden") is not True
        or auth.get("behaviors_tsv_forbidden") is not True
        or not isinstance(auth.get("authorized_unix_ns"), int)
        or isinstance(auth.get("authorized_unix_ns"), bool)
        or int(auth["authorized_unix_ns"]) <= 0
        or not isinstance(auth.get("launch_id"), str)
        or not auth.get("launch_id")
    ):
        raise RuntimeError("verifier authorization identity mismatch")
    synthetic = action == "self-test"
    if auth.get("synthetic_mode") is not synthetic:
        raise RuntimeError("verifier action/synthetic authorization mismatch")
    if synthetic:
        if (
            auth.get("immutable_input_sha256") != {}
            or auth.get("immutable_input_paths") != {}
            or auth.get("phase_a_commit") is not None
        ):
            raise RuntimeError("synthetic verifier bound a real input")
    elif auth.get("phase_a_commit") != EXPECTED_PHASE_A_COMMIT:
        raise RuntimeError("real verifier Phase-A commit mismatch")
    start_path = Path(args.process_start).resolve()
    ack_path = Path(args.process_ack).resolve()
    if (
        start_path != resolve_bound_path(auth, "process_start_path")
        or ack_path != resolve_bound_path(auth, "process_ack_path")
        or start_path.parent != authorization_path.parent
        or ack_path.parent != authorization_path.parent
        or authorization_path.name != "verifier_authorization.json"
        or start_path.name != "verifier_process_start.json"
        or ack_path.name != "verifier_process_ack.json"
    ):
        raise RuntimeError("PID handshake path mismatch")
    launch_directory = resolve_bound_path(auth, "launch_directory")
    if (
        authorization_path.parent != launch_directory
        or launch_directory.parent
        != (H10_DIR / ("selftest_artifacts" if synthetic else "results")).resolve()
        or not launch_directory.name.startswith("h10st_" if synthetic else "h10_")
    ):
        raise RuntimeError("verifier launch-directory containment mismatch")
    async_path = resolve_bound_path(auth, "async_error_ledger")
    if async_path.parent != launch_directory or async_path.name != "verifier_async_errors.jsonl":
        raise RuntimeError("async ledger escaped launch directory")
    output = resolve_bound_path(auth, "output_directory")
    if (
        output.parent != launch_directory
        or output.name != "deep_verification"
        or output.exists()
        or resolve_bound_path(auth, "verification_path")
        != (output / "verification.json").resolve()
    ):
        raise RuntimeError("verifier output authorization is not fresh/exact")
    if (
        resolve_bound_path(auth, "active_lock_path") != IMPLEMENTATION_LOCK_PATH.resolve()
        or resolve_bound_path(auth, "inner_lock").parent != H10_DIR.resolve()
        or resolve_bound_path(auth, "inner_lock").name
        != ("H10A_SELFTEST_INNER.lock" if synthetic else "H10A_RUN_001_INNER.lock")
        or resolve_bound_path(auth, "inner_lock_release_path").parent != launch_directory
        or resolve_bound_path(auth, "inner_lock_release_path").name
        != "verifier_inner_lock_released.json"
        or resolve_bound_path(auth, "resource_inner_lock_release_path").parent
        != launch_directory
        or resolve_bound_path(auth, "resource_inner_lock_release_path").name
        != "verifier_inner_lock_resource_released.json"
        or resolve_bound_path(auth, "outer_lock")
        != (
            H10_DIR
            / ("H10A_SELFTEST_LAUNCH.lock" if synthetic else "H10A_RUN_001_LAUNCH.lock")
        ).resolve()
    ):
        raise RuntimeError("lock path containment mismatch")
    install_async_hooks(async_path)
    launcher_pid = int(auth.get("launcher_pid", -1))
    if not process_is_alive(launcher_pid):
        raise RuntimeError("authorized launcher PID is not alive")
    outer_lock = resolve_bound_path(auth, "outer_lock")
    assert_outer_lock(outer_lock)

    runtime = validate_runtime_contract(auth)
    if Path(sys.executable).resolve() != resolve_bound_path(auth, "venv_launcher"):
        raise RuntimeError("workspace virtual-environment launcher mismatch")
    if Path(str(getattr(sys, "_base_executable", ""))).resolve() != resolve_bound_path(auth, "base_interpreter"):
        raise RuntimeError("base interpreter mismatch")

    verify_authorized_input_surface(auth, synthetic)
    _BOOTSTRAP_INPUT_HASHES = {} if synthetic else verify_real_input_hashes()

    _INNER_LOCK_RECORD = acquire_verifier_inner_lock(auth)

    record = {
        "action": action,
        "authorization_sha256": authorization_sha,
        "environment": {
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "main_thread_only": True,
            "numpy_tree_manifest_sha256": auth.get("numpy_manifest_sha256"),
            "numpy_tree_validation_passed": True,
            "numpy_version": NUMPY_VERSION,
            "pcg_probe_sha256": auth.get("expected_pcg_probe_sha256"),
            "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
            "python_version": ".".join(str(value) for value in PYTHON_VERSION),
            "runtime_files": runtime,
            "sys_base_executable": str(Path(str(getattr(sys, "_base_executable", ""))).resolve()),
            "sys_base_prefix": str(Path(sys.base_prefix).resolve()),
            "sys_executable": str(Path(sys.executable).resolve()),
            "sys_prefix": str(Path(sys.prefix).resolve()),
            "thread_bounds": {name: os.environ.get(name) for name in THREAD_ENV_NAMES},
        },
        "launch_id": auth["launch_id"],
        "launcher_pid": launcher_pid,
        "mode": "h10a-child-process-start",
        "output_id": auth["output_id"],
        "process_pid": os.getpid(),
        "run_role": "verifier",
        "subject_kind": "verifier",
        "subject_path": str(SCRIPT_PATH),
        "subject_sha256": auth["subject_sha256"],
        "token_sha256": token_sha,
    }
    write_exclusive_json(start_path, record)
    deadline = time.monotonic() + 30.0
    while not ack_path.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError("launcher PID acknowledgement timed out")
        if not process_is_alive(launcher_pid):
            raise RuntimeError("launcher exited before acknowledgement")
        time.sleep(0.05)
    ack = read_json(ack_path)
    if (
        not isinstance(ack, dict)
        or set(ack)
        != {
            "mode", "action", "run_role", "launch_id", "launcher_pid",
            "process_pid", "authorization_sha256", "token_sha256",
            "subject_sha256", "acknowledged_unix_ns",
        }
        or ack.get("mode") != "h10a-child-process-acknowledgement"
        or ack.get("action") != action
        or ack.get("run_role") != "verifier"
        or ack.get("launch_id") != auth.get("launch_id")
        or int(ack.get("launcher_pid", -1)) != launcher_pid
        or int(ack.get("process_pid", -1)) != os.getpid()
        or ack.get("authorization_sha256") != authorization_sha
        or ack.get("token_sha256") != token_sha
        or ack.get("subject_sha256") != auth.get("subject_sha256")
        or not isinstance(ack.get("acknowledged_unix_ns"), int)
        or isinstance(ack.get("acknowledged_unix_ns"), bool)
        or int(ack["acknowledged_unix_ns"]) <= 0
    ):
        raise RuntimeError("launcher PID acknowledgement mismatch")
    owner = read_canonical_json(resolve_bound_path(auth, "inner_lock"))
    if (
        not isinstance(owner, dict)
        or set(owner)
        != {
            "action", "authorization_sha256", "created_unix_ns", "launch_id",
            "mode", "process_pid", "run_role", "token_sha256",
        }
        or owner.get("action") != action
        or owner.get("authorization_sha256") != authorization_sha
        or owner.get("launch_id") != auth.get("launch_id")
        or owner.get("mode") != "h10a-child-inner-lock"
        or int(owner.get("process_pid", -1)) != os.getpid()
        or owner.get("run_role") != "verifier"
        or owner.get("token_sha256") != token_sha
        or not isinstance(owner.get("created_unix_ns"), int)
        or isinstance(owner.get("created_unix_ns"), bool)
        or not (
            int(auth["authorized_unix_ns"])
            <= int(owner["created_unix_ns"])
            <= int(ack["acknowledged_unix_ns"])
        )
    ):
        raise RuntimeError("verifier inner-lock owner changed at acknowledgement")
    if not process_is_alive(launcher_pid):
        raise RuntimeError("launcher exited during acknowledgement")
    assert_outer_lock(outer_lock)
    verify_single_thread_environment()
    return auth


@dataclass(frozen=True)
class RelationGraph:
    relation_id: str
    n_columns: int
    rows: tuple[int, ...]
    columns: tuple[int, ...]
    row_degrees: tuple[int, ...]
    column_degrees: tuple[int, ...]

    @property
    def m(self) -> int:
        return len(self.rows)

    @property
    def slots(self) -> tuple[tuple[int, int], ...]:
        return tuple(zip(self.rows, self.columns, strict=True))


@dataclass(frozen=True)
class CompiledView:
    name: str
    relations: tuple[str, ...]
    c_values: Mapping[str, int]
    alpha: Mapping[str, Any]
    graphs: Mapping[tuple[str, str], RelationGraph]


@dataclass(frozen=True)
class Cohort:
    X: Any
    pattern_matrix: Any
    candidate_pattern: Any
    candidate_occurrence: Any
    nz_occurrence: Any
    nz_impression: Any
    nz_anchor: Any
    nz_value: Any
    offsets: Any
    impression_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    counts: Mapping[str, int]


def graph_from_slots(
    relation_id: str,
    n_columns: int,
    slots: Sequence[tuple[int, int]],
    *,
    preserve_order: bool = False,
) -> RelationGraph:
    converted = tuple((int(row), int(column)) for row, column in slots)
    ordered = converted if preserve_order else tuple(sorted(converted))
    if len(set(ordered)) != len(ordered):
        raise RuntimeError(f"duplicate incidence edge in {relation_id}")
    if any(row < 0 or row >= ANCHOR_COUNT or column < 0 or column >= n_columns for row, column in ordered):
        raise RuntimeError(f"incidence index outside shape in {relation_id}")
    row_degrees = [0] * ANCHOR_COUNT
    column_degrees = [0] * n_columns
    for row, column in ordered:
        row_degrees[row] += 1
        column_degrees[column] += 1
    return RelationGraph(
        relation_id=relation_id,
        n_columns=n_columns,
        rows=tuple(row for row, _ in ordered),
        columns=tuple(column for _, column in ordered),
        row_degrees=tuple(row_degrees),
        column_degrees=tuple(column_degrees),
    )


def eligible_pair(h_graph: RelationGraph, c_graph: RelationGraph) -> bool:
    if h_graph.m <= 0 or c_graph.m <= 0 or h_graph.n_columns != c_graph.n_columns:
        return False
    return (
        sum(value > 0 for value in h_graph.row_degrees) >= 2
        and sum(value > 0 for value in c_graph.row_degrees) >= 2
        and sum(value > 0 for value in h_graph.column_degrees) >= 2
        and sum(value > 0 for value in c_graph.column_degrees) >= 2
    )


def compile_endpoint_graphs(
    anchors: Sequence[str],
    facts: Mapping[str, Mapping[str, frozenset[str]]],
    relations: frozenset[str],
    view: str,
) -> CompiledView:
    np = np_module()
    relation_targets: dict[str, dict[str, set[tuple[int, str]]]] = {}
    for anchor_index, qid in enumerate(anchors):
        for endpoint, source_name in (("H", "historical"), ("C", "current")):
            for fact in facts[qid][source_name]:
                match = FACT_RE.fullmatch(fact)
                if match is None:
                    raise RuntimeError("fact signature is malformed")
                relation_id, target = match.groups()
                if relation_id not in relations:
                    continue
                if view == "metadata_blocklist" and relation_id in METADATA_BLOCKLIST:
                    continue
                if view == "hub_removal" and qid in HUB_QIDS:
                    continue
                relation_targets.setdefault(relation_id, {"H": set(), "C": set()})[endpoint].add(
                    (anchor_index, target)
                )
    graphs: dict[tuple[str, str], RelationGraph] = {}
    eligible: list[str] = []
    c_values: dict[str, int] = {}
    for relation_id in sorted(relation_targets):
        by_endpoint = relation_targets[relation_id]
        targets = sorted({target for values in by_endpoint.values() for _, target in values})
        target_index = {target: index for index, target in enumerate(targets)}
        pair: dict[str, RelationGraph] = {}
        for endpoint in ENDPOINT_ORDER:
            slots = sorted(
                (row, target_index[target]) for row, target in by_endpoint[endpoint]
            )
            pair[endpoint] = graph_from_slots(relation_id, len(targets), slots)
        if eligible_pair(pair["H"], pair["C"]):
            eligible.append(relation_id)
            c_values[relation_id] = min(pair["H"].m, pair["C"].m)
            graphs[(relation_id, "H")] = pair["H"]
            graphs[(relation_id, "C")] = pair["C"]
    c_total = sum(c_values[relation_id] for relation_id in eligible)
    if c_total <= 0:
        return CompiledView(view, (), {}, {}, {})
    alpha = {
        relation_id: np.divide(np.float64(c_values[relation_id]), np.float64(c_total))
        for relation_id in eligible
    }
    return CompiledView(view, tuple(eligible), c_values, alpha, graphs)


def canonical_operator(
    compiled: CompiledView,
    endpoint: str,
    state_slots: Mapping[str, Sequence[tuple[int, int]]] | None = None,
) -> tuple[Any, Any, Any, float, dict[str, tuple[Any, Any, Any, Any]]]:
    """Build Q/K/G through the protocol's single-bincount path."""
    np = np_module()
    bin_a: list[int] = []
    bin_b: list[int] = []
    weight_alpha: list[Any] = []
    weight_left: list[Any] = []
    weight_right: list[Any] = []
    weight_column: list[Any] = []
    G = np.zeros((ANCHOR_COUNT, ANCHOR_COUNT), dtype=np.float64, order="C")
    relation_cache: dict[str, tuple[Any, Any, Any, Any]] = {}
    for relation_id in compiled.relations:
        observed = compiled.graphs[(relation_id, endpoint)]
        slots = observed.slots if state_slots is None else tuple(state_slots[relation_id])
        graph = graph_from_slots(
            relation_id, observed.n_columns, slots, preserve_order=True
        )
        if graph.row_degrees != observed.row_degrees or graph.column_degrees != observed.column_degrees:
            raise RuntimeError("fixed-degree state changed a margin")
        d64 = np.ascontiguousarray(graph.row_degrees, dtype=np.float64)
        e64 = np.ascontiguousarray(graph.column_degrees, dtype=np.float64)
        u = np.zeros(ANCHOR_COUNT, dtype=np.float64)
        inv_sqrt_d = np.zeros(ANCHOR_COUNT, dtype=np.float64)
        inv_e = np.zeros(graph.n_columns, dtype=np.float64)
        d_mask = d64 > 0
        e_mask = e64 > 0
        np.divide(d64, np.float64(graph.m), out=u, where=d_mask)
        np.sqrt(u, out=u, where=d_mask)
        np.divide(np.float64(1.0), np.sqrt(d64), out=inv_sqrt_d, where=d_mask)
        np.divide(np.float64(1.0), e64, out=inv_e, where=e_mask)
        alpha = np.float64(compiled.alpha[relation_id])
        incident: list[list[int]] = [[] for _ in range(graph.n_columns)]
        for row, column in graph.slots:
            incident[column].append(row)
        for column in range(graph.n_columns):
            rows = sorted(incident[column])
            for left_position, left in enumerate(rows):
                for right in rows[left_position:]:
                    bin_a.append(left)
                    bin_b.append(right)
                    weight_alpha.append(alpha)
                    weight_left.append(inv_sqrt_d[left])
                    weight_right.append(inv_sqrt_d[right])
                    weight_column.append(inv_e[column])
        term = np.multiply(alpha, np.outer(u, u))
        np.add(G, term, out=G)
        relation_cache[relation_id] = (graph, d64, e64, u)
    a_idx = np.ascontiguousarray(bin_a, dtype=np.intp)
    b_idx = np.ascontiguousarray(bin_b, dtype=np.intp)
    indices = np.ascontiguousarray(
        np.add(np.multiply(a_idx, np.intp(ANCHOR_COUNT)), b_idx), dtype=np.intp
    )
    weights = np.ascontiguousarray(weight_alpha, dtype=np.float64)
    np.multiply(
        weights, np.ascontiguousarray(weight_left, dtype=np.float64), out=weights
    )
    np.multiply(
        weights, np.ascontiguousarray(weight_right, dtype=np.float64), out=weights
    )
    np.multiply(
        weights, np.ascontiguousarray(weight_column, dtype=np.float64), out=weights
    )
    if len(indices) and (int(np.min(indices)) < 0 or int(np.max(indices)) >= ANCHOR_COUNT ** 2):
        raise RuntimeError("canonical bin index outside range")
    bins = np.bincount(indices, weights=weights, minlength=ANCHOR_COUNT ** 2)
    Q = np.ascontiguousarray(bins.reshape((ANCHOR_COUNT, ANCHOR_COUNT)), dtype=np.float64)
    upper_rows, upper_columns = np.triu_indices(ANCHOR_COUNT, k=1)
    Q[upper_columns, upper_rows] = Q[upper_rows, upper_columns]
    K = np.subtract(Q, G)
    W = Q
    E = float(np.trace(K, dtype=np.float64))
    if not all(np.all(np.isfinite(value)) for value in (Q, K, G)) or not math.isfinite(E):
        raise RuntimeError("canonical operator is nonfinite")
    return K, G, W, E, relation_cache


def independent_outer_operator(
    compiled: CompiledView,
    endpoint: str,
    state_slots: Mapping[str, Sequence[tuple[int, int]]] | None = None,
) -> tuple[Any, Any, Any, float]:
    """Independent per-column outer-product construction (no bincount)."""
    np = np_module()
    Q = np.zeros((ANCHOR_COUNT, ANCHOR_COUNT), dtype=np.float64)
    G = np.zeros_like(Q)
    scalar_e = np.float64(0.0)
    for relation_id in compiled.relations:
        observed = compiled.graphs[(relation_id, endpoint)]
        slots = observed.slots if state_slots is None else tuple(state_slots[relation_id])
        graph = graph_from_slots(
            relation_id, observed.n_columns, slots, preserve_order=True
        )
        d = np.asarray(graph.row_degrees, dtype=np.float64)
        e = np.asarray(graph.column_degrees, dtype=np.float64)
        u = np.zeros(ANCHOR_COUNT, dtype=np.float64)
        positive_d = d > 0
        np.sqrt(np.divide(d, np.float64(graph.m), out=np.zeros_like(d), where=positive_d), out=u)
        alpha = np.float64(compiled.alpha[relation_id])
        incident: list[list[int]] = [[] for _ in range(graph.n_columns)]
        for row, column in graph.slots:
            incident[column].append(row)
        local_q = np.zeros_like(Q)
        for column, rows in enumerate(incident):
            if not rows:
                continue
            vector = np.zeros(ANCHOR_COUNT, dtype=np.float64)
            for row in rows:
                vector[row] = np.divide(
                    np.float64(1.0), np.sqrt(np.multiply(d[row], e[column]))
                )
            np.add(local_q, np.outer(vector, vector), out=local_q)
        np.add(Q, np.multiply(alpha, local_q), out=Q)
        np.add(G, np.multiply(alpha, np.outer(u, u)), out=G)
        local_e = np.float64(-1.0)
        for row, column in graph.slots:
            local_e = np.add(
                local_e,
                np.divide(np.float64(1.0), np.multiply(d[row], e[column])),
            )
        scalar_e = np.add(scalar_e, np.multiply(alpha, local_e))
    return np.subtract(Q, G), G, Q, float(scalar_e)


def max_abs_difference(left: Any, right: Any) -> float:
    np = np_module()
    if left.shape != right.shape:
        return math.inf
    return float(np.max(np.absolute(np.subtract(left, right)), initial=np.float64(0.0)))


def verify_operator_semantics(
    compiled: CompiledView,
    endpoint: str,
    K: Any,
    G: Any,
    W: Any,
    E: float,
    state_slots: Mapping[str, Sequence[tuple[int, int]]] | None,
    detailed: bool,
) -> dict[str, Any]:
    np = np_module()
    outer_k, outer_g, outer_w, scalar_e = independent_outer_operator(
        compiled, endpoint, state_slots
    )
    checks: dict[str, Any] = {
        "canonical_vs_outer_K_max_abs": max_abs_difference(K, outer_k),
        "canonical_vs_outer_G_max_abs": max_abs_difference(G, outer_g),
        "canonical_vs_outer_W_max_abs": max_abs_difference(W, outer_w),
        "canonical_vs_scalar_E_abs": float(abs(E - scalar_e)),
        "K_symmetry_max_abs": max_abs_difference(K, K.T),
        "W_decomposition_max_abs": max_abs_difference(W, np.add(K, G)),
        "minimum_symmetric_eigenvalue": float(np.min(np.linalg.eigvalsh((K + K.T) * np.float64(0.5)))),
    }
    if (
        checks["canonical_vs_outer_K_max_abs"] > 1e-12
        or checks["canonical_vs_outer_G_max_abs"] > 1e-12
        or checks["canonical_vs_outer_W_max_abs"] > 1e-12
        or checks["canonical_vs_scalar_E_abs"] > 1e-12
        or checks["K_symmetry_max_abs"] > 1e-12
        or checks["W_decomposition_max_abs"] > 1e-12
        or checks["minimum_symmetric_eigenvalue"] < -1e-10
    ):
        raise RuntimeError("operator semantic check failed")
    if detailed:
        b_v_max = np.float64(0.0)
        bt_u_max = np.float64(0.0)
        decomposition_max = np.float64(0.0)
        for relation_id in compiled.relations:
            observed = compiled.graphs[(relation_id, endpoint)]
            slots = observed.slots if state_slots is None else tuple(state_slots[relation_id])
            graph = graph_from_slots(
                relation_id, observed.n_columns, slots, preserve_order=True
            )
            d = np.asarray(graph.row_degrees, dtype=np.float64)
            e = np.asarray(graph.column_degrees, dtype=np.float64)
            n_matrix = np.zeros((ANCHOR_COUNT, graph.n_columns), dtype=np.float64)
            for row, column in graph.slots:
                n_matrix[row, column] = np.divide(
                    np.float64(1.0), np.sqrt(np.multiply(d[row], e[column]))
                )
            u = np.sqrt(np.divide(d, np.float64(graph.m), out=np.zeros_like(d), where=d > 0))
            v = np.sqrt(np.divide(e, np.float64(graph.m), out=np.zeros_like(e), where=e > 0))
            B = np.subtract(n_matrix, np.outer(u, v))
            b_v_max = np.maximum(b_v_max, np.max(np.abs(B @ v), initial=np.float64(0.0)))
            bt_u_max = np.maximum(bt_u_max, np.max(np.abs(B.T @ u), initial=np.float64(0.0)))
            lhs = B @ B.T
            rhs = np.subtract(n_matrix @ n_matrix.T, np.outer(u, u))
            decomposition_max = np.maximum(
                decomposition_max,
                np.max(np.abs(np.subtract(lhs, rhs)), initial=np.float64(0.0)),
            )
        checks.update(
            {
                "Bv_inf": float(b_v_max),
                "BTu_inf": float(bt_u_max),
                "relation_decomposition_max_abs": float(decomposition_max),
            }
        )
        if b_v_max > 1e-12 or bt_u_max > 1e-12 or decomposition_max > 1e-12:
            raise RuntimeError("detailed relation algebra check failed")
    return checks


def verify_real_input_hashes() -> dict[str, str]:
    if set(INPUT_PATHS) != set(EXPECTED_INPUT_HASHES):
        raise RuntimeError("immutable-input inventory is incomplete")
    observed: dict[str, str] = {}
    for name, path in INPUT_PATHS.items():
        if not path.is_file():
            raise RuntimeError(f"immutable input is missing: {name}")
        observed[name] = sha256_file(path)
        if observed[name] != EXPECTED_INPUT_HASHES[name]:
            raise RuntimeError(f"immutable input hash mismatch: {name}")
    if INPUT_PATHS["phase_a_manifest"].stat().st_size != EXPECTED_MANIFEST_BYTES:
        raise RuntimeError("Phase-A manifest byte count mismatch")
    return observed


def verify_authorized_input_surface(auth: Mapping[str, Any], synthetic: bool) -> None:
    if synthetic:
        if auth.get("synthetic_mode") is not True:
            raise RuntimeError("synthetic verifier lacks synthetic-only authorization")
        return
    if auth.get("immutable_input_sha256") != EXPECTED_INPUT_HASHES:
        raise RuntimeError("authorization immutable-input hash map mismatch")
    authorized = auth.get("immutable_input_paths")
    if not isinstance(authorized, dict) or set(authorized) != set(INPUT_PATHS):
        raise RuntimeError("authorization immutable-input path surface mismatch")
    for name, expected in INPUT_PATHS.items():
        if Path(str(authorized[name])).resolve() != expected.resolve():
            raise RuntimeError(f"authorization immutable-input path mismatch: {name}")


def load_phase_a_contract() -> tuple[dict[str, Any], tuple[str, ...]]:
    result = read_json(INPUT_PATHS["phase_a_result"])
    completion = read_json(INPUT_PATHS["phase_a_completion"])
    if not isinstance(result, dict) or not isinstance(completion, dict):
        raise RuntimeError("Phase-A contract is malformed")
    cohort = result.get("cohort")
    if not isinstance(cohort, dict):
        raise RuntimeError("Phase-A cohort is absent")
    anchors = cohort.get("sampled_qids")
    threshold = result.get("confidence_threshold", result.get("minimum_confidence", 0.90))
    if (
        result.get("schema_version") != "h6_phase_a_coverage.python.v1"
        or result.get("phase_a_commit", EXPECTED_PHASE_A_COMMIT) != EXPECTED_PHASE_A_COMMIT
        or cohort.get("manifest_sha256") != EXPECTED_INPUT_HASHES["phase_a_manifest"]
        or cohort.get("eligible_impressions") != EXPECTED_COUNTS["impressions"]
        or cohort.get("distinct_users") != EXPECTED_COUNTS["users"]
        or cohort.get("candidates") != EXPECTED_COUNTS["candidate_occurrences"]
        or cohort.get("known_news") != EXPECTED_COUNTS["news_rows"]
        or cohort.get("news_with_sampled_anchor") != EXPECTED_COUNTS["supported_news"]
        or float(threshold) != 0.90
    ):
        raise RuntimeError("Phase-A result contract mismatch")
    if (
        not isinstance(anchors, list)
        or len(anchors) != ANCHOR_COUNT
        or len(set(anchors)) != ANCHOR_COUNT
        or any(not isinstance(value, str) or QID_RE.fullmatch(value) is None for value in anchors)
    ):
        raise RuntimeError("ordered anchor list is malformed")
    outputs = completion.get("outputs")
    if (
        completion.get("status") != "H6_COVERAGE_RUN_002_COMPLETE"
        or completion.get("completion_marker_is_last") is not True
        or not isinstance(outputs, dict)
        or outputs.get("primary_result", {}).get("sha256") != EXPECTED_INPUT_HASHES["phase_a_result"]
        or outputs.get("primary_manifest", {}).get("sha256") != EXPECTED_INPUT_HASHES["phase_a_manifest"]
    ):
        raise RuntimeError("Phase-A completion chain mismatch")
    return result, tuple(str(value) for value in anchors)


def load_relation_vocabulary() -> frozenset[str]:
    values: set[str] = set()
    rows = 0
    with INPUT_PATHS["relations"].open("r", encoding="utf-8", newline="") as handle:
        for raw in handle:
            rows += 1
            relation_id = raw.split("\t", 1)[0]
            if PROPERTY_RE.fullmatch(relation_id) is None or relation_id in values:
                raise RuntimeError("relation vocabulary contains invalid/duplicate ID")
            values.add(relation_id)
    if rows != EXPECTED_RELATIONS or len(values) != EXPECTED_RELATIONS:
        raise RuntimeError("relation vocabulary cardinality mismatch")
    return frozenset(values)


def load_fact_ledger(anchors: Sequence[str]) -> dict[str, dict[str, frozenset[str]]]:
    rows: dict[str, dict[str, frozenset[str]]] = {}
    with INPUT_PATHS["facts"].open("r", encoding="utf-8", newline="") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise RuntimeError("fact-ledger row is not an object")
            qid = value.get("qid")
            if (
                not isinstance(qid, str)
                or QID_RE.fullmatch(qid) is None
                or qid in rows
                or value.get("api_ok") is not True
            ):
                raise RuntimeError("fact-ledger anchor identity is invalid")
            endpoint: dict[str, frozenset[str]] = {}
            for source_name in ("historical", "current"):
                facts = value.get(source_name, {}).get("facts")
                if not isinstance(facts, list):
                    raise RuntimeError("fact-ledger endpoint facts are malformed")
                retained: set[str] = set()
                for raw_fact in facts:
                    if not isinstance(raw_fact, str):
                        raise RuntimeError("non-string fact signature")
                    match = FACT_RE.fullmatch(raw_fact)
                    if match is not None:
                        retained.add(raw_fact)
                endpoint[source_name] = frozenset(retained)
            rows[qid] = endpoint
    if set(rows) != set(anchors) or len(rows) != ANCHOR_COUNT:
        raise RuntimeError("fact ledger does not match frozen anchors")
    return rows


def parse_news(anchors: Sequence[str]) -> tuple[dict[str, int], tuple[tuple[int, ...], ...], Any]:
    np = np_module()
    anchor_index = {qid: index for index, qid in enumerate(anchors)}
    news_to_tuple: dict[str, tuple[int, ...]] = {}
    supported = 0
    with INPUT_PATHS["news"].open("r", encoding="utf-8", newline="") as handle:
        for raw in handle:
            fields = raw.rstrip("\r\n").split("\t", 7)
            if len(fields) != 8:
                raise RuntimeError("news row does not contain eight columns")
            news_id = fields[0]
            if NEWS_RE.fullmatch(news_id) is None or news_id in news_to_tuple:
                raise RuntimeError("news ID is invalid or duplicated")
            retained: set[int] = set()
            for column in (6, 7):
                annotations = json.loads(fields[column])
                if not isinstance(annotations, list):
                    raise RuntimeError("news annotation column is not an array")
                for annotation in annotations:
                    if not isinstance(annotation, dict):
                        continue
                    qid = str(annotation.get("WikidataId", "")).strip()
                    if qid not in anchor_index:
                        continue
                    try:
                        confidence = float(annotation.get("Confidence"))
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(confidence) and confidence >= 0.90:
                        retained.add(anchor_index[qid])
            pattern = tuple(sorted(retained))
            news_to_tuple[news_id] = pattern
            supported += int(bool(pattern))
    patterns = tuple(sorted(set(news_to_tuple.values())))
    if (
        len(news_to_tuple) != EXPECTED_COUNTS["news_rows"]
        or supported != EXPECTED_COUNTS["supported_news"]
        or len(patterns) != EXPECTED_COUNTS["patterns"]
        or not patterns
        or patterns[0] != ()
    ):
        raise RuntimeError("news support/pattern counts do not reproduce")
    pattern_id = {pattern: index for index, pattern in enumerate(patterns)}
    news_to_pattern = {news_id: pattern_id[pattern] for news_id, pattern in news_to_tuple.items()}
    matrix = np.zeros((len(patterns), ANCHOR_COUNT), dtype=np.float64, order="C")
    for index, pattern in enumerate(patterns):
        if pattern:
            value = np.divide(np.float64(1.0), np.sqrt(np.float64(len(pattern))))
            matrix[index, np.asarray(pattern, dtype=np.intp)] = value
    return news_to_pattern, patterns, matrix


@dataclass(frozen=True)
class AuditRow:
    audit_hash: bytes
    impression_id: str
    history: tuple[str, ...]
    candidate_ids: tuple[str, ...]


def parse_manifest_row(
    raw: bytes,
    news_to_pattern: Mapping[str, int],
    row_index: int,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], int]:
    if not raw.endswith(b"\n") or raw.endswith(b"\r\n"):
        raise RuntimeError("manifest row lacks exact LF terminator")
    if MANIFEST_LABEL_RE.search(raw):
        raise RuntimeError("candidate outcome suffix leaked into label-free manifest")
    value = json.loads(raw)
    if not isinstance(value, dict) or list(value) != ["i", "u", "h", "c"]:
        raise RuntimeError("manifest top-level schema/order mismatch")
    if (
        json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        + b"\n"
        != raw
    ):
        raise RuntimeError("manifest row is not exact compact JSON")
    impression_id, user_id = value["i"], value["u"]
    history, candidates = value["h"], value["c"]
    if not isinstance(impression_id, str) or not impression_id or not isinstance(user_id, str) or not user_id:
        raise RuntimeError(f"manifest identity invalid at row {row_index}")
    if (
        not isinstance(history, list)
        or not history
        or len(history) > 50
        or any(not isinstance(news_id, str) or NEWS_RE.fullmatch(news_id) is None for news_id in history)
    ):
        raise RuntimeError("manifest history is malformed")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("manifest candidate slate is malformed")
    candidate_ids: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or list(candidate) != ["n", "v"]:
            raise RuntimeError("manifest candidate schema/order mismatch")
        news_id = candidate["n"]
        if not isinstance(news_id, str) or NEWS_RE.fullmatch(news_id) is None:
            raise RuntimeError("manifest candidate ID is invalid")
        candidate_ids.append(news_id)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise RuntimeError("manifest contains a duplicated candidate ID")
    if any(news_id not in news_to_pattern for news_id in history):
        raise RuntimeError("manifest history references unknown news")
    if any(news_id not in news_to_pattern for news_id in candidate_ids):
        raise RuntimeError("manifest candidate references unknown news")
    supported = sum(bool(news_to_pattern[news_id]) for news_id in candidate_ids)
    if not any(bool(news_to_pattern[news_id]) for news_id in history):
        raise RuntimeError("manifest history has no supported news")
    return (
        impression_id,
        user_id,
        tuple(str(news_id) for news_id in history),
        tuple(candidate_ids),
        supported,
    )


def load_real_cohort(
    news_to_pattern: Mapping[str, int],
    patterns: Sequence[tuple[int, ...]],
    pattern_matrix: Any,
) -> Cohort:
    users: set[str] = set()
    eligible: list[AuditRow] = []
    impressions = 0
    occurrences = 0
    supported_occurrences = 0
    gt10 = 0
    gt10_supported = 0
    ge2_supported = 0
    with INPUT_PATHS["phase_a_manifest"].open("rb") as handle:
        for row_index, raw in enumerate(handle):
            impression_id, user_id, history, candidate_ids, supported = parse_manifest_row(
                raw, news_to_pattern, row_index
            )
            users.add(user_id)
            impressions += 1
            occurrences += len(candidate_ids)
            supported_occurrences += supported
            gt10 += int(len(candidate_ids) > 10)
            gt10_supported += int(len(candidate_ids) > 10 and supported > 10)
            ge2_supported += int(supported >= 2)
            if len(candidate_ids) > 10 and supported > 10:
                audit_hash = hashlib.sha256(AUDIT_PREFIX + impression_id.encode("utf-8")).digest()
                eligible.append(AuditRow(audit_hash, impression_id, history, candidate_ids))
    counts = {
        "news_rows": len(news_to_pattern),
        "supported_news": sum(bool(patterns[index]) for index in news_to_pattern.values()),
        "patterns": len(patterns),
        "impressions": impressions,
        "users": len(users),
        "candidate_occurrences": occurrences,
        "supported_candidate_occurrences": supported_occurrences,
        "gt10_candidates": gt10,
        "gt10_candidates_and_support": gt10_supported,
        "ge2_supported_candidates": ge2_supported,
        "histories_with_support": impressions,
        "audit_impressions": AUDIT_SIZE,
    }
    if counts != EXPECTED_COUNTS or len(eligible) != EXPECTED_COUNTS["gt10_candidates_and_support"]:
        raise RuntimeError(f"frozen cohort counts do not reproduce: {counts}")
    eligible.sort(key=lambda row: (row.audit_hash, row.impression_id))
    selected = eligible[:AUDIT_SIZE]
    if len(selected) != AUDIT_SIZE:
        raise RuntimeError("audit selection cardinality mismatch")
    return build_cohort_arrays(selected, news_to_pattern, pattern_matrix, counts)


def build_cohort_arrays(
    selected: Sequence[AuditRow],
    news_to_pattern: Mapping[str, int],
    pattern_matrix: Any,
    counts: Mapping[str, int],
) -> Cohort:
    np = np_module()
    X = np.zeros((len(selected), ANCHOR_COUNT), dtype=np.float64, order="C")
    impression_ids: list[str] = []
    candidate_ids: list[str] = []
    candidate_patterns: list[int] = []
    offsets = [0]
    nz_occurrence: list[int] = []
    nz_impression: list[int] = []
    nz_anchor: list[int] = []
    nz_value: list[Any] = []
    for impression_index, row in enumerate(selected):
        impression_ids.append(row.impression_id)
        history_sum = np.zeros(ANCHOR_COUNT, dtype=np.float64)
        for news_id in row.history:
            np.add(history_sum, pattern_matrix[news_to_pattern[news_id]], out=history_sum)
        history_ss = np.add.reduce(
            np.multiply(history_sum, history_sum), dtype=np.float64
        )
        history_norm = np.sqrt(history_ss)
        if not np.isfinite(history_norm) or history_norm <= 0:
            raise RuntimeError("selected history normalization failed")
        X[impression_index] = np.divide(history_sum, history_norm)
        for news_id in row.candidate_ids:
            occurrence = len(candidate_ids)
            pattern_id = int(news_to_pattern[news_id])
            candidate_ids.append(news_id)
            candidate_patterns.append(pattern_id)
            for anchor in np.flatnonzero(pattern_matrix[pattern_id]):
                nz_occurrence.append(occurrence)
                nz_impression.append(impression_index)
                nz_anchor.append(int(anchor))
                nz_value.append(pattern_matrix[pattern_id, anchor])
        offsets.append(len(candidate_ids))
    if not X.flags.c_contiguous or not np.all(np.isfinite(X)):
        raise RuntimeError("canonical user matrix is invalid")
    return Cohort(
        X=X,
        pattern_matrix=np.ascontiguousarray(pattern_matrix, dtype=np.float64),
        candidate_pattern=np.ascontiguousarray(candidate_patterns, dtype=np.intp),
        candidate_occurrence=np.arange(len(candidate_ids), dtype=np.intp),
        nz_occurrence=np.ascontiguousarray(nz_occurrence, dtype=np.intp),
        nz_impression=np.ascontiguousarray(nz_impression, dtype=np.intp),
        nz_anchor=np.ascontiguousarray(nz_anchor, dtype=np.intp),
        nz_value=np.ascontiguousarray(nz_value, dtype=np.float64),
        offsets=np.ascontiguousarray(offsets, dtype=np.intp),
        impression_ids=tuple(impression_ids),
        candidate_ids=tuple(candidate_ids),
        counts=dict(counts),
    )


def allocate_synthetic_edges(total: int, relations: int) -> tuple[int, ...]:
    quotient, remainder = divmod(total, relations)
    return tuple(quotient + int(index < remainder) for index in range(relations))


def synthetic_compiled_view(view: str) -> CompiledView:
    np = np_module()
    budget = VIEW_BUDGETS[view]
    relation_count = budget["relations"]
    relation_ids = tuple(f"S{index:03d}" for index in range(relation_count))
    allocations = {
        endpoint: allocate_synthetic_edges(budget[endpoint], relation_count)
        for endpoint in ENDPOINT_ORDER
    }
    graphs: dict[tuple[str, str], RelationGraph] = {}
    c_values: dict[str, int] = {}
    for relation_index, relation_id in enumerate(relation_ids):
        for endpoint_index, endpoint in enumerate(ENDPOINT_ORDER):
            m = allocations[endpoint][relation_index]
            slots: list[tuple[int, int]] = []
            for edge_index in range(m):
                if view == "hub_removal":
                    row = 2 + ((edge_index + 7 * relation_index + 3 * endpoint_index) % 48)
                else:
                    row = (edge_index + 7 * relation_index + 3 * endpoint_index) % 50
                column = (3 * edge_index + 11 * relation_index + 5 * endpoint_index) % 17
                slots.append((row, column))
            graph = graph_from_slots(relation_id, 17, slots)
            graphs[(relation_id, endpoint)] = graph
        c_values[relation_id] = min(
            graphs[(relation_id, "H")].m, graphs[(relation_id, "C")].m
        )
    if any(not eligible_pair(graphs[(relation_id, "H")], graphs[(relation_id, "C")]) for relation_id in relation_ids):
        raise RuntimeError("synthetic fixture unexpectedly produced an ineligible relation")
    c_total = sum(c_values.values())
    alpha = {
        relation_id: np.divide(np.float64(c_values[relation_id]), np.float64(c_total))
        for relation_id in relation_ids
    }
    return CompiledView(view, relation_ids, c_values, alpha, graphs)


def synthetic_cohort() -> Cohort:
    np = np_module()
    patterns: list[tuple[int, ...]] = []
    matrix = np.zeros((812, ANCHOR_COUNT), dtype=np.float64)
    for pattern_id in range(812):
        pattern = tuple(bit for bit in range(10) if pattern_id & (1 << bit))
        patterns.append(pattern)
        if pattern:
            value = np.divide(np.float64(1.0), np.sqrt(np.float64(len(pattern))))
            matrix[pattern_id, np.asarray(pattern, dtype=np.intp)] = value
    selected: list[AuditRow] = []
    occurrence = 0
    for impression_index in range(AUDIT_SIZE):
        impression_id = f"SI{impression_index:05d}"
        count = 11 + (impression_index % 50)
        candidate_ids = tuple(
            f"SYN{impression_index:04d}_{candidate_index:02d}"
            for candidate_index in range(count)
        )
        history = tuple(f"SH{impression_index:05d}_{j}" for j in range(4))
        selected.append(AuditRow(b"", impression_id, history, candidate_ids))
        occurrence += count
    # Synthetic history/candidate IDs are mapped independently of real-news syntax.
    synthetic_news_to_pattern: dict[str, int] = {}
    running_occurrence = 0
    for impression_index, row in enumerate(selected):
        for t, history_id in enumerate(row.history):
            # A private four-anchor pattern with exact value 0.5 is represented by
            # constructing X directly below; these IDs only satisfy array-builder lookup.
            synthetic_news_to_pattern[history_id] = 0
        for candidate_id in row.candidate_ids:
            synthetic_news_to_pattern[candidate_id] = running_occurrence % 812
            running_occurrence += 1
    X = np.zeros((AUDIT_SIZE, ANCHOR_COUNT), dtype=np.float64)
    for impression_index in range(AUDIT_SIZE):
        anchors = tuple((impression_index + 13 * t) % 50 for t in range(4))
        X[impression_index, np.asarray(anchors, dtype=np.intp)] = np.float64(0.5)
    candidate_ids: list[str] = []
    candidate_patterns: list[int] = []
    offsets = [0]
    nz_occurrence: list[int] = []
    nz_impression: list[int] = []
    nz_anchor: list[int] = []
    nz_value: list[Any] = []
    for impression_index, row in enumerate(selected):
        for candidate_id in row.candidate_ids:
            occurrence_index = len(candidate_ids)
            pattern_id = synthetic_news_to_pattern[candidate_id]
            candidate_ids.append(candidate_id)
            candidate_patterns.append(pattern_id)
            for anchor in patterns[pattern_id]:
                nz_occurrence.append(occurrence_index)
                nz_impression.append(impression_index)
                nz_anchor.append(anchor)
                nz_value.append(matrix[pattern_id, anchor])
        offsets.append(len(candidate_ids))
    synthetic_counts = {
        "audit_impressions": AUDIT_SIZE,
        "candidate_anchor_nonzeros": len(nz_anchor),
        "candidate_occurrences": len(candidate_ids),
        "patterns": 812,
        "supported_candidate_occurrences": sum(value != 0 for value in candidate_patterns),
        "user_anchor_nonzeros": int(np.count_nonzero(X)),
    }
    expected = {
        "audit_impressions": 8_192,
        "candidate_anchor_nonzeros": 1_354_440,
        "candidate_occurrences": 290_648,
        "patterns": 812,
        "supported_candidate_occurrences": 290_290,
        "user_anchor_nonzeros": 32_768,
    }
    if synthetic_counts != expected or occurrence != expected["candidate_occurrences"]:
        raise RuntimeError(f"synthetic cohort counts mismatch: {synthetic_counts}")
    return Cohort(
        X=np.ascontiguousarray(X),
        pattern_matrix=np.ascontiguousarray(matrix),
        candidate_pattern=np.ascontiguousarray(candidate_patterns, dtype=np.intp),
        candidate_occurrence=np.arange(len(candidate_ids), dtype=np.intp),
        nz_occurrence=np.ascontiguousarray(nz_occurrence, dtype=np.intp),
        nz_impression=np.ascontiguousarray(nz_impression, dtype=np.intp),
        nz_anchor=np.ascontiguousarray(nz_anchor, dtype=np.intp),
        nz_value=np.ascontiguousarray(nz_value, dtype=np.float64),
        offsets=np.ascontiguousarray(offsets, dtype=np.intp),
        impression_ids=tuple(row.impression_id for row in selected),
        candidate_ids=tuple(candidate_ids),
        counts=synthetic_counts,
    )


def representation_digest(cohort: Cohort) -> str:
    digest = hashlib.sha256()
    digest.update(b"H10A_REPRESENTATION_V1\n")
    for array in (
        cohort.X,
        cohort.pattern_matrix,
        cohort.candidate_pattern,
        cohort.nz_occurrence,
        cohort.nz_impression,
        cohort.nz_anchor,
        cohort.nz_value,
        cohort.offsets,
    ):
        contiguous = np_module().ascontiguousarray(array)
        dtype_text = contiguous.dtype.str.encode("ascii")
        digest.update(len(dtype_text).to_bytes(2, "little"))
        digest.update(dtype_text)
        digest.update(contiguous.ndim.to_bytes(2, "little"))
        for dimension in contiguous.shape:
            digest.update(int(dimension).to_bytes(8, "little"))
        digest.update(contiguous.tobytes(order="C"))
    for values in (cohort.impression_ids, cohort.candidate_ids):
        digest.update(len(values).to_bytes(8, "little"))
        for value in values:
            encoded = value.encode("ascii")
            digest.update(len(encoded).to_bytes(4, "little"))
            digest.update(encoded)
    return digest.hexdigest().upper()


def pcg_probe_digest() -> str:
    np = np_module()
    seed = int.from_bytes(hashlib.sha256(PCG_PROBE_SEED_TEXT).digest()[:8], "big")
    rng = np.random.Generator(np.random.PCG64DXSM(seed))
    payload = bytearray(PCG_PROBE_PREFIX)
    m_values = (2, 3, 17, 40, 41, 44, 45, 48, 49, 50, 51, 64)
    for index in range(128):
        m = m_values[index % len(m_values)]
        raw = int(rng.bit_generator.random_raw())
        payload.extend(raw.to_bytes(8, "little", signed=False))
        if raw & 1 == 0:
            payload.append(0)
            continue
        payload.append(1)
        first = int(rng.integers(0, m, size=None, dtype=np.int64, endpoint=False))
        raw_second = int(rng.integers(0, m - 1, size=None, dtype=np.int64, endpoint=False))
        second = raw_second + int(raw_second >= first)
        payload.extend(first.to_bytes(8, "little", signed=False))
        payload.extend(second.to_bytes(8, "little", signed=False))
    return sha256_bytes(bytes(payload))


def switch_seed(view: str, endpoint: str, relation_id: str, chain: int) -> int:
    text = (
        NULL_PREFIX
        + view.encode("ascii")
        + b"|"
        + endpoint.encode("ascii")
        + b"|"
        + relation_id.encode("ascii")
        + b"|chain="
        + str(chain).encode("ascii")
    )
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "big")


def state_digest(
    view: str,
    endpoint: str,
    relation_id: str,
    chain: int,
    state: int,
    n_columns: int,
    slots: Sequence[tuple[int, int]],
) -> str:
    payload = bytearray(b"H10A_STATE_V1\n")
    for value in (view, endpoint, relation_id, str(chain), str(state)):
        payload.extend(value.encode("ascii"))
        payload.extend(b"\n")
    payload.extend(ANCHOR_COUNT.to_bytes(2, "little", signed=False))
    payload.extend(n_columns.to_bytes(4, "little", signed=False))
    payload.extend(len(slots).to_bytes(4, "little", signed=False))
    for row, column in slots:
        payload.append(row)
        payload.extend(column.to_bytes(4, "little", signed=False))
    return sha256_bytes(bytes(payload))


def degree_mix_digest(graph: RelationGraph) -> tuple[str, tuple[tuple[int, int, int], ...]]:
    counts: dict[tuple[int, int], int] = {}
    for row, column in graph.slots:
        key = (graph.row_degrees[row], graph.column_degrees[column])
        counts[key] = counts.get(key, 0) + 1
    triples = tuple((left, right, count) for (left, right), count in sorted(counts.items()))
    payload = bytearray(b"H10A_DEGREE_MIX_V1\n")
    payload.extend(len(triples).to_bytes(4, "little", signed=False))
    for left, right, count in triples:
        payload.extend(left.to_bytes(4, "little", signed=False))
        payload.extend(right.to_bytes(4, "little", signed=False))
        payload.extend(count.to_bytes(4, "little", signed=False))
    return sha256_bytes(bytes(payload)), triples


def switch_is_valid(
    first: tuple[int, int],
    second: tuple[int, int],
    membership: set[tuple[int, int]],
) -> bool:
    i, j = first
    k, ell = second
    return i != k and j != ell and (i, ell) not in membership and (k, j) not in membership


def initial_switch_diagnostics(graph: RelationGraph) -> dict[str, Any]:
    slots = graph.slots
    membership = set(slots)
    valid = 0
    e_changing = 0
    for first_index in range(len(slots)):
        first = slots[first_index]
        for second_index in range(first_index + 1, len(slots)):
            second = slots[second_index]
            if not switch_is_valid(first, second, membership):
                continue
            valid += 1
            i, j = first
            k, ell = second
            if (
                graph.row_degrees[i] != graph.row_degrees[k]
                and graph.column_degrees[j] != graph.column_degrees[ell]
            ):
                e_changing += 1
    mixing_digest, triples = degree_mix_digest(graph)
    return {
        "E_changing_switches": e_changing,
        "degree_mixing_digest_sha256": mixing_digest,
        "degree_mixing_nonzero_cells": len(triples),
        "distinct_positive_column_degrees": len({value for value in graph.column_degrees if value > 0}),
        "distinct_positive_row_degrees": len({value for value in graph.row_degrees if value > 0}),
        "initial_valid_unordered_switches": valid,
        "structurally_immobile": valid == 0,
    }


@dataclass(frozen=True)
class ChainResult:
    retained: tuple[tuple[tuple[int, int], ...], ...]
    diagnostics: Mapping[str, Any]
    digest_records: tuple[dict[str, Any], ...]


def run_switch_chain(
    view: str,
    endpoint: str,
    graph: RelationGraph,
    chain: int,
) -> ChainResult:
    np = np_module()
    if view == "primary":
        burn_multiple, retained_count, thin_multiple = 50, 50, 2
    else:
        burn_multiple, retained_count, thin_multiple = 30, 10, 2
    burn = burn_multiple * graph.m
    thin = thin_multiple * graph.m
    total = burn + retained_count * thin
    seed = switch_seed(view, endpoint, graph.relation_id, chain)
    rng = np.random.Generator(np.random.PCG64DXSM(seed))
    slots = list(graph.slots)
    observed = tuple(slots)
    membership = set(slots)
    counters = {
        "accepted_swaps": 0,
        "invalid_cross_occupied": 0,
        "invalid_same_row_or_column": 0,
        "lazy_stays": 0,
        "nonlazy_attempts": 0,
        "proposals": 0,
        "self_transitions": 0,
        "valid_swaps": 0,
    }
    retained: list[tuple[tuple[int, int], ...]] = []
    digest_records: list[dict[str, Any]] = [
        {
            "chain": chain,
            "digest_sha256": state_digest(
                view, endpoint, graph.relation_id, chain, 0, graph.n_columns, slots
            ),
            "endpoint": endpoint,
            "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint],
            "m": graph.m,
            "n_columns": graph.n_columns,
            "n_rows": ANCHOR_COUNT,
            "relation_id": graph.relation_id,
            "schema": "h10a_state_digest.v1",
            "state": 0,
            "view": view,
            "view_ordinal": VIEW_ORDINAL[view],
        }
    ]
    next_retain = burn + thin
    m = graph.m
    random_raw = rng.bit_generator.random_raw
    integers = rng.integers
    for proposal in range(1, total + 1):
        counters["proposals"] += 1
        raw = int(random_raw())
        if raw & 1 == 0:
            counters["lazy_stays"] += 1
            counters["self_transitions"] += 1
        else:
            counters["nonlazy_attempts"] += 1
            first = int(integers(0, m, size=None, dtype=np.int64, endpoint=False))
            raw_second = int(integers(0, m - 1, size=None, dtype=np.int64, endpoint=False))
            second = raw_second + int(raw_second >= first)
            p = min(first, second)
            q = max(first, second)
            i, j = slots[p]
            k, ell = slots[q]
            if i == k or j == ell:
                counters["invalid_same_row_or_column"] += 1
                counters["self_transitions"] += 1
            elif (i, ell) in membership or (k, j) in membership:
                counters["invalid_cross_occupied"] += 1
                counters["self_transitions"] += 1
            else:
                membership.remove((i, j))
                membership.remove((k, ell))
                slots[p] = (i, ell)
                slots[q] = (k, j)
                membership.add(slots[p])
                membership.add(slots[q])
                counters["valid_swaps"] += 1
                counters["accepted_swaps"] += 1
        if proposal == next_retain:
            frozen = tuple(slots)
            retained.append(frozen)
            state = len(retained)
            digest_records.append(
                {
                    "chain": chain,
                    "digest_sha256": state_digest(
                        view, endpoint, graph.relation_id, chain, state, graph.n_columns, frozen
                    ),
                    "endpoint": endpoint,
                    "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint],
                    "m": graph.m,
                    "n_columns": graph.n_columns,
                    "n_rows": ANCHOR_COUNT,
                    "relation_id": graph.relation_id,
                    "schema": "h10a_state_digest.v1",
                    "state": state,
                    "view": view,
                    "view_ordinal": VIEW_ORDINAL[view],
                }
            )
            next_retain += thin
    if len(retained) != retained_count or counters["proposals"] != total:
        raise RuntimeError("switch-chain schedule did not finish exactly")
    if counters["proposals"] != counters["self_transitions"] + counters["accepted_swaps"]:
        raise RuntimeError("switch-chain counter partition failed")
    if counters["valid_swaps"] != counters["accepted_swaps"]:
        raise RuntimeError("valid/accepted swap counters differ")
    if len(membership) != graph.m or membership != set(slots):
        raise RuntimeError("switch-chain membership structure diverged")
    final_graph = graph_from_slots(
        graph.relation_id, graph.n_columns, slots, preserve_order=True
    )
    if final_graph.row_degrees != graph.row_degrees or final_graph.column_degrees != graph.column_degrees:
        raise RuntimeError("switch chain failed fixed-degree preservation")
    seen_retained: set[tuple[tuple[int, int], ...]] = set()
    duplicate_count = 0
    returned_count = 0
    for frozen in retained:
        duplicate_count += int(frozen in seen_retained)
        seen_retained.add(frozen)
        returned_count += int(frozen == observed)
    diagnostics = {
        "chain": chain,
        "endpoint": endpoint,
        "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint],
        "final_state_digest": state_digest(
            view,
            endpoint,
            graph.relation_id,
            chain,
            retained_count,
            graph.n_columns,
            retained[-1],
        ),
        **initial_switch_diagnostics(graph),
        "m": graph.m,
        **counters,
        "relation_id": graph.relation_id,
        "retained_duplicate_count": duplicate_count,
        "returned_to_observed_count": returned_count,
        "schedule": {
            "burn_in_multiple": burn_multiple,
            "burn_in_proposals": burn,
            "retained_states": retained_count,
            "thin_multiple": thin_multiple,
            "thin_proposals": thin,
            "total_proposals": total,
        },
        "schema": "h10a_chain_diagnostics.v1",
        "seed": seed,
        "view": view,
        "view_ordinal": VIEW_ORDINAL[view],
        "zero_acceptance": counters["accepted_swaps"] == 0,
    }
    return ChainResult(tuple(retained), diagnostics, tuple(digest_records))


@dataclass(frozen=True)
class RankingCache:
    counts: Any
    occurrence_impression: Any
    rank_hashes: tuple[bytes, ...]


def make_ranking_cache(cohort: Cohort) -> RankingCache:
    np = np_module()
    counts = np.diff(cohort.offsets)
    occurrence_impression = np.repeat(
        np.arange(len(cohort.impression_ids), dtype=np.intp), counts
    )
    rank_hashes: list[bytes] = []
    for occurrence, news_id in enumerate(cohort.candidate_ids):
        impression = int(occurrence_impression[occurrence])
        impression_id = cohort.impression_ids[impression]
        rank_hashes.append(
            hashlib.sha256(
                RANK_PREFIX
                + impression_id.encode("ascii")
                + b"|"
                + news_id.encode("ascii")
            ).digest()
        )
    return RankingCache(
        counts=np.ascontiguousarray(counts, dtype=np.intp),
        occurrence_impression=np.ascontiguousarray(occurrence_impression, dtype=np.intp),
        rank_hashes=tuple(rank_hashes),
    )


def canonical_scores(cohort: Cohort, operator: Any) -> Any:
    np = np_module()
    U = np.matmul(cohort.X, operator)
    terms = np.multiply(
        U[cohort.nz_impression, cohort.nz_anchor], cohort.nz_value
    )
    scores = np.bincount(
        cohort.nz_occurrence,
        weights=terms,
        minlength=len(cohort.candidate_ids),
    )
    scores = np.ascontiguousarray(scores, dtype=np.float64)
    if not np.all(np.isfinite(scores)):
        raise RuntimeError("candidate scores are nonfinite")
    return scores


def direct_scores(
    cohort: Cohort,
    ranking: RankingCache,
    operator: Any,
    occurrences: Any | None = None,
) -> Any:
    np = np_module()
    if occurrences is None:
        table = np.matmul(np.matmul(cohort.X, operator), cohort.pattern_matrix.T)
        return table[ranking.occurrence_impression, cohort.candidate_pattern]
    occurrence_array = np.ascontiguousarray(occurrences, dtype=np.intp)
    impressions = ranking.occurrence_impression[occurrence_array]
    patterns = cohort.candidate_pattern[occurrence_array]
    left = np.matmul(cohort.X[impressions], operator)
    return np.add.reduce(
        np.multiply(left, cohort.pattern_matrix[patterns]), axis=1, dtype=np.float64
    )


def within_impression_variance(scores: Any, cohort: Cohort, ranking: RankingCache) -> float:
    np = np_module()
    sums = np.add.reduceat(scores, cohort.offsets[:-1], dtype=np.float64)
    counts64 = ranking.counts.astype(np.float64)
    means = np.divide(sums, counts64)
    centered = np.subtract(scores, np.repeat(means, ranking.counts))
    squares = np.multiply(centered, centered)
    within = np.add.reduceat(squares, cohort.offsets[:-1], dtype=np.float64)
    per_impression = np.divide(within, counts64)
    return float(np.mean(per_impression, dtype=np.float64))


def deterministic_ranks(scores: Any, cohort: Cohort, ranking: RankingCache) -> Any:
    np = np_module()
    ranks = np.empty(len(scores), dtype=np.int64)
    for impression, (start, stop) in enumerate(zip(cohort.offsets[:-1], cohort.offsets[1:], strict=True)):
        begin, end = int(start), int(stop)
        segment = scores[begin:end]
        preliminary = np.argsort(np.negative(segment), kind="stable")
        group_ids: dict[int, int] = {}
        group = -1
        first_score = np.float64(0.0)
        for local_index in preliminary:
            index = int(local_index)
            score = segment[index]
            if group < 0 or np.absolute(np.subtract(score, first_score)) > np.float64(1e-12):
                group += 1
                first_score = score
            group_ids[index] = group
        final = sorted(
            range(end - begin),
            key=lambda local: (
                group_ids[local],
                ranking.rank_hashes[begin + local],
                cohort.candidate_ids[begin + local],
            ),
        )
        for one_based, local in enumerate(final, start=1):
            ranks[begin + local] = one_based
    return np.ascontiguousarray(ranks, dtype=np.int64)


def ranking_metrics(
    residual_scores: Any,
    degree_scores: Any,
    cohort: Cohort,
    ranking: RankingCache,
    degree_ranks: Any | None = None,
) -> tuple[float, float, Any, Any]:
    np = np_module()
    residual_ranks = deterministic_ranks(residual_scores, cohort, ranking)
    if degree_ranks is None:
        degree_ranks = deterministic_ranks(degree_scores, cohort, ranking)
    rank_delta = np.abs(residual_ranks - degree_ranks)
    footrule = np.add.reduceat(rank_delta, cohort.offsets[:-1], dtype=np.int64)
    counts64 = ranking.counts.astype(np.int64)
    denominator = np.floor_divide(np.multiply(counts64, counts64), 2)
    per_impression = np.divide(
        footrule.astype(np.float64), denominator.astype(np.float64)
    )
    D = float(np.mean(per_impression, dtype=np.float64))
    overlap = np.empty(len(ranking.counts), dtype=np.int64)
    for impression, (start, stop) in enumerate(zip(cohort.offsets[:-1], cohort.offsets[1:], strict=True)):
        begin, end = int(start), int(stop)
        overlap[impression] = int(
            np.count_nonzero(
                np.logical_and(
                    residual_ranks[begin:end] <= 10,
                    degree_ranks[begin:end] <= 10,
                )
            )
        )
    t_per = np.divide(
        (10 - overlap).astype(np.float64), np.float64(10.0)
    )
    T = float(np.mean(t_per, dtype=np.float64))
    return D, T, residual_ranks, degree_ranks


def degree_r2(
    residual_scores: Any,
    degree_scores: Any,
    cohort: Cohort,
    ranking: RankingCache,
) -> float:
    np = np_module()
    counts64 = ranking.counts.astype(np.float64)
    z_sums = np.add.reduceat(residual_scores, cohort.offsets[:-1], dtype=np.float64)
    g_sums = np.add.reduceat(degree_scores, cohort.offsets[:-1], dtype=np.float64)
    z_means = np.divide(z_sums, counts64)
    g_means = np.divide(g_sums, counts64)
    zc = np.subtract(residual_scores, np.repeat(z_means, ranking.counts))
    gc = np.subtract(degree_scores, np.repeat(g_means, ranking.counts))
    P = np.float64(len(residual_scores))
    var_z = np.divide(np.add.reduce(np.multiply(zc, zc), dtype=np.float64), P)
    var_g = np.divide(np.add.reduce(np.multiply(gc, gc), dtype=np.float64), P)
    if var_z <= np.float64(1e-24) or var_g <= np.float64(1e-24):
        return 1.0
    cov_zg = np.divide(np.add.reduce(np.multiply(zc, gc), dtype=np.float64), P)
    corr = np.divide(cov_zg, np.sqrt(np.multiply(var_z, var_g)))
    return float(np.multiply(corr, corr))


def impression_ranges(scores: Any, cohort: Cohort) -> Any:
    np = np_module()
    return np.subtract(
        np.maximum.reduceat(scores, cohort.offsets[:-1]),
        np.minimum.reduceat(scores, cohort.offsets[:-1]),
    )


def nearest_rank_quantiles(values: Any) -> dict[str, float]:
    np = np_module()
    sorted_values = np.sort(np.ascontiguousarray(values, dtype=np.float64), kind="stable")
    if len(sorted_values) == 0:
        raise RuntimeError("cannot quantify an empty score array")
    result: dict[str, float] = {}
    for probability in (0.0, 0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99, 1.0):
        if probability == 0.0:
            index = 0
        elif probability == 1.0:
            index = len(sorted_values) - 1
        else:
            index = math.ceil(probability * len(sorted_values)) - 1
        result[f"q{probability:.2f}"] = float(sorted_values[index])
    return result


def null_quantile(values: Sequence[float], index: int) -> float:
    np = np_module()
    array = np.ascontiguousarray(values, dtype=np.float64)
    return float(np.sort(array, kind="stable")[index])


def monte_carlo_tail(values: Sequence[float], real: float) -> tuple[int, float]:
    np = np_module()
    array = np.ascontiguousarray(values, dtype=np.float64)
    count = int(np.count_nonzero(np.greater_equal(array, np.float64(real))))
    p_mc = np.divide(np.float64(1 + count), np.float64(len(array) + 1))
    return count, float(p_mc)


def selected_primary_parity_states() -> frozenset[tuple[str, int, int]]:
    ranked: list[tuple[bytes, str, int, int]] = []
    for endpoint in ENDPOINT_ORDER:
        for chain in (0, 1):
            for state in range(1, 51):
                digest = hashlib.sha256(
                    PARITY_PREFIX
                    + endpoint.encode("ascii")
                    + b"|"
                    + str(chain).encode("ascii")
                    + b"|"
                    + str(state).encode("ascii")
                ).digest()
                ranked.append((digest, endpoint, chain, state))
    ranked.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    return frozenset((endpoint, chain, state) for _, endpoint, chain, state in ranked[:64])


PRIMARY_PARITY_STATES = selected_primary_parity_states()


def parity_record(
    view: str,
    endpoint: str,
    kind_ordinal: int,
    chain: int,
    state: int,
    check_name: str,
    observed: Any,
    threshold: Any,
    reference: Any,
    passed: bool,
    relation_id: str = "",
    impression_id: str = "",
    news_id: str = "",
) -> dict[str, Any]:
    return {
        "chain": chain,
        "check_name": check_name,
        "endpoint": endpoint,
        "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint],
        "impression_id": impression_id,
        "kind_ordinal": kind_ordinal,
        "news_id": news_id,
        "observed": observed,
        "passed": bool(passed),
        "reference": reference,
        "relation_id": relation_id,
        "schema": "h10a_parity_check.v1",
        "state": state,
        "threshold": threshold,
        "view": view,
        "view_ordinal": VIEW_ORDINAL[view],
    }


def state_metric_record(
    view: str,
    endpoint: str,
    kind: str,
    chain: int,
    state: int,
    metrics: Mapping[str, float],
) -> dict[str, Any]:
    kind_ordinal = 0 if kind == "real" else 1
    return {
        "chain": chain,
        "endpoint": endpoint,
        "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint],
        "kind": kind,
        "kind_ordinal": kind_ordinal,
        "metrics": dict(metrics),
        "schema": "h10a_state_metrics.v1",
        "state": state,
        "view": view,
        "view_ordinal": VIEW_ORDINAL[view],
    }


def parity_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["view_ordinal"]),
        int(row["endpoint_ordinal"]),
        int(row["kind_ordinal"]),
        int(row["chain"]),
        int(row["state"]),
        str(row["relation_id"]),
        str(row["check_name"]),
        str(row["impression_id"]),
        str(row["news_id"]),
    )


def metric_sort_key(row: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        int(row["view_ordinal"]),
        int(row["endpoint_ordinal"]),
        int(row["kind_ordinal"]),
        int(row["chain"]),
        int(row["state"]),
    )


def digest_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["view_ordinal"]),
        int(row["endpoint_ordinal"]),
        int(row["chain"]),
        int(row["state"]),
        str(row["relation_id"]),
    )


def diagnostic_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["view_ordinal"]),
        int(row["endpoint_ordinal"]),
        str(row["relation_id"]),
        int(row["chain"]),
    )


def selected_pair_occurrences(
    cohort: Cohort,
    ranking: RankingCache,
    view: str,
    endpoint: str,
    chain: int,
    state: int,
) -> Any:
    import heapq

    prefix = (
        PAIR_PREFIX
        + view.encode("ascii")
        + b"|"
        + endpoint.encode("ascii")
        + b"|"
        + str(chain).encode("ascii")
        + b"|"
        + str(state).encode("ascii")
        + b"|"
    )

    def key(occurrence: int) -> tuple[bytes, str, str]:
        impression_id = cohort.impression_ids[int(ranking.occurrence_impression[occurrence])]
        news_id = cohort.candidate_ids[occurrence]
        digest = hashlib.sha256(
            prefix + impression_id.encode("ascii") + b"|" + news_id.encode("ascii")
        ).digest()
        return digest, impression_id, news_id

    selected = heapq.nsmallest(256, range(len(cohort.candidate_ids)), key=key)
    selected.sort(key=key)
    return np_module().ascontiguousarray(selected, dtype=np_module().intp)


def relation_degree_mode_shares(
    compiled: CompiledView,
    endpoint: str,
) -> tuple[dict[str, float], float]:
    np = np_module()
    shares: dict[str, float] = {}
    numerator = np.float64(0.0)
    denominator = np.float64(0.0)
    for relation_id in compiled.relations:
        one = CompiledView(
            compiled.name,
            (relation_id,),
            {relation_id: compiled.c_values[relation_id]},
            {relation_id: np.float64(1.0)},
            {
                (relation_id, "H"): compiled.graphs[(relation_id, "H")],
                (relation_id, "C"): compiled.graphs[(relation_id, "C")],
            },
        )
        K, _, _, _, _ = canonical_operator(one, endpoint)
        energy = np.add.reduce(
            np.multiply(K.ravel(order="C"), K.ravel(order="C")), dtype=np.float64
        )
        shares[relation_id] = float(
            np.divide(np.float64(1.0), np.add(np.float64(1.0), energy))
        )
        numerator = np.add(numerator, np.float64(compiled.alpha[relation_id]))
        denominator = np.add(
            denominator,
            np.multiply(
                np.float64(compiled.alpha[relation_id]),
                np.add(np.float64(1.0), energy),
            ),
        )
    rho = float(np.divide(numerator, denominator))
    return shares, rho


@dataclass
class EndpointEvaluation:
    K: Any
    G: Any
    W: Any
    E: float
    z: Any
    g: Any
    a: Any
    V: float
    metric_record: dict[str, Any]
    residual_ranks: Any | None = None
    degree_ranks: Any | None = None


@dataclass
class NullEvaluation:
    K: Any
    E: float
    z: Any
    V: float
    metric_record: dict[str, Any]


@dataclass
class ArtifactAccumulator:
    state_metrics: list[dict[str, Any]]
    state_digests: list[dict[str, Any]]
    chain_diagnostics: list[dict[str, Any]]
    parity_checks: list[dict[str, Any]]

    @classmethod
    def empty(cls) -> "ArtifactAccumulator":
        return cls([], [], [], [])


def append_operator_checks(
    accumulator: ArtifactAccumulator,
    view: str,
    endpoint: str,
    kind_ordinal: int,
    chain: int,
    state: int,
    checks: Mapping[str, Any],
) -> None:
    for name in sorted(checks):
        observed = checks[name]
        if name == "minimum_symmetric_eigenvalue":
            threshold, reference = -1e-10, ">="
            passed = float(observed) >= -1e-10
        else:
            threshold, reference = 1e-12, "<="
            passed = float(observed) <= 1e-12
        accumulator.parity_checks.append(
            parity_record(
                view,
                endpoint,
                kind_ordinal,
                chain,
                state,
                name,
                float(observed),
                threshold,
                reference,
                passed,
            )
        )


def evaluate_real_endpoint(
    compiled: CompiledView,
    endpoint: str,
    cohort: Cohort,
    ranking: RankingCache,
    accumulator: ArtifactAccumulator,
) -> EndpointEvaluation:
    np = np_module()
    K, G, W, E, _ = canonical_operator(compiled, endpoint)
    checks = verify_operator_semantics(compiled, endpoint, K, G, W, E, None, True)
    append_operator_checks(accumulator, compiled.name, endpoint, 0, -1, 0, checks)
    z = canonical_scores(cohort, K)
    g = canonical_scores(cohort, G)
    a = canonical_scores(cohort, W)
    direct_z = direct_scores(cohort, ranking, K)
    direct_g = direct_scores(cohort, ranking, G)
    direct_a = direct_scores(cohort, ranking, W)
    score_checks = {
        "a_equals_z_plus_g_max_abs": float(
            np.max(np.abs(np.subtract(a, np.add(z, g))), initial=np.float64(0.0))
        ),
        "degree_sparse_vs_direct_max_abs": float(
            np.max(np.abs(np.subtract(g, direct_g)), initial=np.float64(0.0))
        ),
        "raw_sparse_vs_direct_max_abs": float(
            np.max(np.abs(np.subtract(a, direct_a)), initial=np.float64(0.0))
        ),
        "residual_sparse_vs_direct_max_abs": float(
            np.max(np.abs(np.subtract(z, direct_z)), initial=np.float64(0.0))
        ),
    }
    if any(value > 1e-12 for value in score_checks.values()):
        raise RuntimeError("real candidate score parity failed")
    append_operator_checks(accumulator, compiled.name, endpoint, 0, -1, 0, score_checks)
    V = within_impression_variance(z, cohort, ranking)
    record = state_metric_record(compiled.name, endpoint, "real", -1, 0, {"E": E, "V": V})
    accumulator.state_metrics.append(record)
    return EndpointEvaluation(K, G, W, E, z, g, a, V, record)


def run_null_endpoint(
    compiled: CompiledView,
    endpoint: str,
    cohort: Cohort,
    ranking: RankingCache,
    accumulator: ArtifactAccumulator,
) -> dict[tuple[int, int], NullEvaluation]:
    np = np_module()
    chains: dict[tuple[str, int], ChainResult] = {}
    for relation_id in compiled.relations:
        graph = compiled.graphs[(relation_id, endpoint)]
        for chain in (0, 1):
            result = run_switch_chain(compiled.name, endpoint, graph, chain)
            chains[(relation_id, chain)] = result
            accumulator.chain_diagnostics.append(dict(result.diagnostics))
            accumulator.state_digests.extend(dict(row) for row in result.digest_records)
    retained_count = 50 if compiled.name == "primary" else 10
    evaluations: dict[tuple[int, int], NullEvaluation] = {}
    for chain in (0, 1):
        for state in range(1, retained_count + 1):
            slots = {
                relation_id: chains[(relation_id, chain)].retained[state - 1]
                for relation_id in compiled.relations
            }
            K, G, W, E, _ = canonical_operator(compiled, endpoint, slots)
            detailed = (
                compiled.name == "primary"
                and (endpoint, chain, state) in PRIMARY_PARITY_STATES
            )
            checks = verify_operator_semantics(
                compiled, endpoint, K, G, W, E, slots, detailed
            )
            if detailed:
                append_operator_checks(accumulator, compiled.name, endpoint, 1, chain, state, checks)
            z = canonical_scores(cohort, K)
            V = within_impression_variance(z, cohort, ranking)
            record = state_metric_record(
                compiled.name, endpoint, "null", chain, state, {"E": E, "V": V}
            )
            accumulator.state_metrics.append(record)
            evaluation = NullEvaluation(K, E, None, V, record)
            evaluations[(chain, state)] = evaluation
            if detailed:
                selected = selected_pair_occurrences(
                    cohort, ranking, compiled.name, endpoint, chain, state
                )
                g_scores = canonical_scores(cohort, G)
                a_scores = canonical_scores(cohort, W)
                direct_z = direct_scores(cohort, ranking, K, selected)
                direct_g = direct_scores(cohort, ranking, G, selected)
                direct_a = direct_scores(cohort, ranking, W, selected)
                for local, occurrence_raw in enumerate(selected):
                    occurrence = int(occurrence_raw)
                    impression_index = int(ranking.occurrence_impression[occurrence])
                    impression_id = cohort.impression_ids[impression_index]
                    news_id = cohort.candidate_ids[occurrence]
                    differences = {
                        "pair_a_equals_z_plus_g_abs": abs(
                            float(a_scores[occurrence])
                            - float(np.add(z[occurrence], g_scores[occurrence]))
                        ),
                        "pair_degree_sparse_vs_direct_abs": abs(
                            float(g_scores[occurrence]) - float(direct_g[local])
                        ),
                        "pair_raw_sparse_vs_direct_abs": abs(
                            float(a_scores[occurrence]) - float(direct_a[local])
                        ),
                        "pair_residual_sparse_vs_direct_abs": abs(
                            float(z[occurrence]) - float(direct_z[local])
                        ),
                    }
                    for name in sorted(differences):
                        difference = differences[name]
                        if difference > 1e-12:
                            raise RuntimeError("selected null candidate score parity failed")
                        accumulator.parity_checks.append(
                            parity_record(
                                compiled.name,
                                endpoint,
                                1,
                                chain,
                                state,
                                name,
                                difference,
                                1e-12,
                                "<=",
                                True,
                                impression_id=impression_id,
                                news_id=news_id,
                            )
                        )
    return evaluations


def chain_values(
    evaluations: Mapping[tuple[int, int], NullEvaluation],
    metric: str,
    chain: int,
) -> list[float]:
    states = 50 if len(evaluations) == 100 else 10
    result: list[float] = []
    for state in range(1, states + 1):
        evaluation = evaluations[(chain, state)]
        if metric not in evaluation.metric_record["metrics"]:
            raise RuntimeError(f"requested unreached null metric: {metric}")
        result.append(float(evaluation.metric_record["metrics"][metric]))
    return result


def describe_null_metric(
    real: float,
    evaluations: Mapping[tuple[int, int], NullEvaluation],
    metric: str,
    primary: bool,
) -> dict[str, Any]:
    chain_zero = chain_values(evaluations, metric, 0)
    chain_one = chain_values(evaluations, metric, 1)
    combined = chain_zero + chain_one
    if primary:
        indices = {"q0.50": 49, "q0.95": 94, "q0.99": 98}
    else:
        indices = {"q0.50": 9, "q0.95": 18, "q0.99": 19}
    summary: dict[str, Any] = {
        "chain_0": {},
        "chain_1": {},
        "combined": {
            "maximum": max(combined),
            "minimum": min(combined),
        },
        "real": float(real),
    }
    for label, index in indices.items():
        value = null_quantile(combined, index)
        summary["combined"][label] = value
        summary["combined"][f"real_minus_{label}"] = float(real - value)
    if primary:
        for chain_label, values in (("chain_0", chain_zero), ("chain_1", chain_one)):
            for label, index in (("q0.95", 47), ("q0.99", 49)):
                value = null_quantile(values, index)
                summary[chain_label][label] = value
                summary[chain_label][f"real_minus_{label}"] = float(real - value)
    else:
        for chain_label, values in (("chain_0", chain_zero), ("chain_1", chain_one)):
            value = null_quantile(values, 4)
            summary[chain_label]["q0.50"] = value
            summary[chain_label]["real_minus_q0.50"] = float(real - value)
    tail_count, p_mc = monte_carlo_tail(combined, real)
    summary["combined"]["tail_count"] = tail_count
    summary["combined"]["p_MC"] = p_mc
    return summary


def v_gate_passed(summary: Mapping[str, Any], primary: bool) -> bool:
    if primary:
        return (
            summary["combined"]["real_minus_q0.99"] > 0
            and summary["chain_0"]["real_minus_q0.99"] > 0
            and summary["chain_1"]["real_minus_q0.99"] > 0
            and summary["combined"]["p_MC"] <= 0.01
        )
    return (
        summary["combined"]["real_minus_q0.50"] > 0
        and summary["chain_0"]["real_minus_q0.50"] > 0
        and summary["chain_1"]["real_minus_q0.50"] > 0
    )


def ranking_gate_passed(summary: Mapping[str, Any], primary: bool) -> bool:
    if primary:
        return (
            summary["combined"]["real_minus_q0.95"] > 0
            and summary["chain_0"]["real_minus_q0.95"] > 0
            and summary["chain_1"]["real_minus_q0.95"] > 0
        )
    return (
        summary["combined"]["real_minus_q0.50"] > 0
        and summary["chain_0"]["real_minus_q0.50"] > 0
        and summary["chain_1"]["real_minus_q0.50"] > 0
    )


def accepted_swap_gate(
    accumulator: ArtifactAccumulator,
    view: str,
    endpoint: str,
    chain: int,
) -> bool:
    return sum(
        int(row["accepted_swaps"])
        for row in accumulator.chain_diagnostics
        if row["view"] == view and row["endpoint"] == endpoint and row["chain"] == chain
    ) > 0


def coverage_report(
    real: Mapping[str, EndpointEvaluation],
    cohort: Cohort,
    ranking: RankingCache,
) -> dict[str, Any]:
    np = np_module()
    h_ranges = impression_ranges(real["H"].z, cohort)
    c_ranges = impression_ranges(real["C"].z, cohort)
    endpoint_usable = np.logical_and(
        h_ranges > np.float64(1e-12), c_ranges > np.float64(1e-12)
    )
    robust_scores = np.minimum(real["H"].z, real["C"].z)
    robust_ranges = impression_ranges(robust_scores, cohort)
    robust_usable = robust_ranges > np.float64(1e-12)
    endpoint_count = int(np.count_nonzero(endpoint_usable))
    robust_count = int(np.count_nonzero(robust_usable))
    supported_count = int(np.count_nonzero(cohort.candidate_pattern))
    nonzero_counts = {
        endpoint: int(
            np.count_nonzero(np.not_equal(evaluation.z, np.float64(0.0)))
        )
        for endpoint, evaluation in real.items()
    }
    return {
        "endpoint_usable_count": endpoint_count,
        "endpoint_usable_rate": float(
            np.divide(np.float64(endpoint_count), np.float64(AUDIT_SIZE))
        ),
        "nonzero_score_rates": {
            endpoint: float(
                np.divide(np.float64(count), np.float64(len(cohort.candidate_ids)))
            )
            for endpoint, count in nonzero_counts.items()
        },
        "nonzero_scores": nonzero_counts,
        "robust_usable_count": robust_count,
        "robust_usable_rate": float(
            np.divide(np.float64(robust_count), np.float64(AUDIT_SIZE))
        ),
        "supported_candidate_occurrences": supported_count,
        "supported_candidate_rate": float(
            np.divide(
                np.float64(supported_count), np.float64(len(cohort.candidate_ids))
            )
        ),
        "z_rob_dispersion": within_impression_variance(
            robust_scores, cohort, ranking
        ),
    }


def endpoint_top10_disagreement(
    left_ranks: Any,
    right_ranks: Any,
    cohort: Cohort,
    ranking: RankingCache,
) -> float:
    np = np_module()
    overlap = np.empty(len(ranking.counts), dtype=np.int64)
    for impression, (start, stop) in enumerate(zip(cohort.offsets[:-1], cohort.offsets[1:], strict=True)):
        begin, end = int(start), int(stop)
        overlap[impression] = int(
            np.count_nonzero(
                np.logical_and(left_ranks[begin:end] <= 10, right_ranks[begin:end] <= 10)
            )
        )
    t_per = np.divide((10 - overlap).astype(np.float64), np.float64(10.0))
    return float(np.mean(t_per, dtype=np.float64))


def rank_view_states(
    compiled: CompiledView,
    real: Mapping[str, EndpointEvaluation],
    nulls: Mapping[str, Mapping[tuple[int, int], NullEvaluation]],
    cohort: Cohort,
    ranking: RankingCache,
) -> None:
    for endpoint in ENDPOINT_ORDER:
        real_eval = real[endpoint]
        D, T, z_ranks, g_ranks = ranking_metrics(
            real_eval.z, real_eval.g, cohort, ranking
        )
        real_eval.residual_ranks = z_ranks
        real_eval.degree_ranks = g_ranks
        real_eval.metric_record["metrics"].update(
            {"D": D, "R2_deg": degree_r2(real_eval.z, real_eval.g, cohort, ranking), "T": T}
        )
        for chain in (0, 1):
            state_count = 50 if compiled.name == "primary" else 10
            for state in range(1, state_count + 1):
                null_eval = nulls[endpoint][(chain, state)]
                # Frozen two-stage flow: score once for V, discard; after V passes,
                # score the cached operator again for D/T.
                residual_scores = canonical_scores(cohort, null_eval.K)
                D_null, T_null, _, _ = ranking_metrics(
                    residual_scores,
                    real_eval.g,
                    cohort,
                    ranking,
                    degree_ranks=g_ranks,
                )
                null_eval.metric_record["metrics"].update({"D": D_null, "T": T_null})


def graph_budget_report(compiled: CompiledView) -> dict[str, int]:
    report = {
        "relations": len(compiled.relations),
        "H": sum(compiled.graphs[(relation_id, "H")].m for relation_id in compiled.relations),
        "C": sum(compiled.graphs[(relation_id, "C")].m for relation_id in compiled.relations),
    }
    proposals = 0
    if compiled.name == "primary":
        factor = 2 * (50 + 50 * 2)
    else:
        factor = 2 * (30 + 10 * 2)
    proposals = factor * (report["H"] + report["C"])
    report["proposals"] = proposals
    if report != VIEW_BUDGETS[compiled.name]:
        raise RuntimeError(f"fixed graph budget mismatch for {compiled.name}: {report}")
    return report


def score_summary(
    real: Mapping[str, EndpointEvaluation],
    cohort: Cohort,
    ranking: RankingCache,
) -> dict[str, Any]:
    np = np_module()
    if real["H"].residual_ranks is None or real["C"].residual_ranks is None:
        raise RuntimeError("score summary requested before ranks")
    robust = np.minimum(real["H"].z, real["C"].z)
    return {
        "endpoint_top10_disagreement": endpoint_top10_disagreement(
            real["H"].residual_ranks,
            real["C"].residual_ranks,
            cohort,
            ranking,
        ),
        "quantiles": {
            endpoint: {
                "degree": nearest_rank_quantiles(evaluation.g),
                "raw": nearest_rank_quantiles(evaluation.a),
                "residual": nearest_rank_quantiles(evaluation.z),
            }
            for endpoint, evaluation in real.items()
        },
        "robust_quantiles": nearest_rank_quantiles(robust),
    }


def stage_thresholds(primary: bool) -> tuple[int, float]:
    return (5_000, 0.50) if primary else (2_500, 0.25)


def evaluate_view(
    compiled: CompiledView,
    cohort: Cohort,
    ranking: RankingCache,
    accumulator: ArtifactAccumulator,
    forced_full_path: bool,
) -> tuple[dict[str, Any], bool, str]:
    primary = compiled.name == "primary"
    budget = graph_budget_report(compiled)
    real = {
        endpoint: evaluate_real_endpoint(compiled, endpoint, cohort, ranking, accumulator)
        for endpoint in ENDPOINT_ORDER
    }
    nulls = {
        endpoint: run_null_endpoint(compiled, endpoint, cohort, ranking, accumulator)
        for endpoint in ENDPOINT_ORDER
    }
    summaries: dict[str, Any] = {
        "budget": budget,
        "degree_mode_share": {},
        "endpoint": {},
        "relations": list(compiled.relations),
        "relation_weights": {
            relation_id: float(compiled.alpha[relation_id])
            for relation_id in compiled.relations
        },
    }
    v_pass = True
    for endpoint in ENDPOINT_ORDER:
        shares, aggregate_share = relation_degree_mode_shares(compiled, endpoint)
        v_summary = describe_null_metric(
            real[endpoint].V, nulls[endpoint], "V", primary
        )
        e_summary = describe_null_metric(
            real[endpoint].E, nulls[endpoint], "E", primary
        )
        endpoint_v_pass = v_gate_passed(v_summary, primary)
        v_pass = v_pass and endpoint_v_pass
        summaries["degree_mode_share"][endpoint] = {
            "aggregate_rho": aggregate_share,
            "relation_rho": shares,
        }
        summaries["endpoint"][endpoint] = {
            "E_descriptive": e_summary,
            "V": v_summary,
            "V_gate_passed": endpoint_v_pass,
        }
    if not v_pass and not forced_full_path:
        summaries["gate"] = {
            "all_V_passed": False,
            "remaining_gate_stage_reached": False,
        }
        return summaries, False, "V"

    rank_view_states(compiled, real, nulls, cohort, ranking)
    remaining_pass = True
    for endpoint in ENDPOINT_ORDER:
        endpoint_record = real[endpoint].metric_record["metrics"]
        d_summary = describe_null_metric(
            float(endpoint_record["D"]), nulls[endpoint], "D", primary
        )
        t_summary = describe_null_metric(
            float(endpoint_record["T"]), nulls[endpoint], "T", primary
        )
        d_pass = ranking_gate_passed(d_summary, primary)
        t_pass = ranking_gate_passed(t_summary, primary)
        r2_pass = float(endpoint_record["R2_deg"]) < 0.80
        summaries["endpoint"][endpoint].update(
            {
                "D": d_summary,
                "D_gate_passed": d_pass,
                "R2_deg": float(endpoint_record["R2_deg"]),
                "R2_gate_passed": r2_pass,
                "T": t_summary,
                "T_gate_passed": t_pass,
            }
        )
        remaining_pass = remaining_pass and d_pass and t_pass and r2_pass
    coverage = coverage_report(real, cohort, ranking)
    minimum_count, minimum_rate = stage_thresholds(primary)
    coverage_pass = (
        coverage["endpoint_usable_count"] >= minimum_count
        and coverage["endpoint_usable_rate"] >= minimum_rate
        and coverage["robust_usable_count"] >= minimum_count
        and coverage["robust_usable_rate"] >= minimum_rate
    )
    accepted = {
        f"{endpoint}_chain_{chain}": accepted_swap_gate(
            accumulator, compiled.name, endpoint, chain
        )
        for endpoint in ENDPOINT_ORDER
        for chain in (0, 1)
    }
    accepted_pass = all(accepted.values())
    parity_pass = all(
        bool(row["passed"])
        for row in accumulator.parity_checks
        if row["view"] == compiled.name
    )
    report = score_summary(real, cohort, ranking)
    summaries.update(
        {
            "coverage": coverage,
            "coverage_gate_passed": coverage_pass,
            "gate": {
                "accepted_swap_by_endpoint_chain": accepted,
                "accepted_swap_gate_passed": accepted_pass,
                "all_V_passed": v_pass,
                "parity_gate_passed": parity_pass,
                "relation_eligibility_gate_passed": bool(compiled.relations),
                "remaining_gate_stage_reached": True,
            },
            "score_summary": report,
        }
    )
    all_pass = (
        v_pass
        and remaining_pass
        and coverage_pass
        and accepted_pass
        and parity_pass
        and bool(compiled.relations)
    )
    summaries["gate"]["all_scientific_gates_passed"] = all_pass
    return summaries, all_pass, "complete"


def exercise_synthetic_branches() -> dict[str, Any]:
    """Small deterministic cases covering branches not guaranteed by the bulk fixture."""
    mobile = graph_from_slots("SMOBILE", 4, ((0, 0), (1, 1), (2, 2), (3, 3)))
    immobile = graph_from_slots("SIMMOBILE", 2, ((0, 0), (0, 1), (1, 0), (1, 1)))
    mobile_diagnostic = initial_switch_diagnostics(mobile)
    immobile_diagnostic = initial_switch_diagnostics(immobile)
    if mobile_diagnostic["structurally_immobile"] or not immobile_diagnostic["structurally_immobile"]:
        raise RuntimeError("synthetic mobility branch fixture failed")
    # Exact slot equality, not edge-set equality, distinguishes return/order cases.
    observed = mobile.slots
    reordered = tuple(reversed(observed))
    if set(observed) != set(reordered) or observed == reordered:
        raise RuntimeError("synthetic slot-order branch fixture failed")
    # First-score-anchored grouping is non-transitive at exactly the declared tolerance.
    np = np_module()
    scores = np.asarray([0.0, 0.75e-12, 1.5e-12], dtype=np.float64)
    first_group = [
        bool(
            np.absolute(np.subtract(score, scores[0]))
            <= np.float64(1e-12)
        )
        for score in scores
    ]
    if first_group != [True, True, False]:
        raise RuntimeError("synthetic anchored-tie boundary fixture failed")
    mobile_chain = run_switch_chain("primary", "H", mobile, 0)
    immobile_chain = run_switch_chain("primary", "H", immobile, 0)
    mobile_counters = mobile_chain.diagnostics
    immobile_counters = immobile_chain.diagnostics
    if (
        int(mobile_counters["accepted_swaps"]) <= 0
        or int(immobile_counters["accepted_swaps"]) != 0
        or int(immobile_counters["lazy_stays"]) <= 0
        or int(immobile_counters["invalid_same_row_or_column"]) <= 0
        or int(immobile_counters["invalid_cross_occupied"]) <= 0
        or int(immobile_counters["retained_duplicate_count"]) <= 0
        or int(immobile_counters["returned_to_observed_count"]) <= 0
    ):
        raise RuntimeError("synthetic switch-counter branch fixture failed")
    quantile_fixture = [float(value) for value in range(100)]
    if null_quantile(quantile_fixture, 98) != 98.0:
        raise RuntimeError("synthetic quantile boundary fixture failed")
    tail_count, tail_value = monte_carlo_tail(quantile_fixture, 100.0)
    if tail_count != 0 or tail_value != float(np.divide(np.float64(1), np.float64(101))):
        raise RuntimeError("synthetic Monte Carlo boundary fixture failed")
    strict_fixture = {
        "combined": {"real_minus_q0.99": 0.0, "p_MC": 0.0},
        "chain_0": {"real_minus_q0.99": 1.0},
        "chain_1": {"real_minus_q0.99": 1.0},
    }
    if v_gate_passed(strict_fixture, True):
        raise RuntimeError("synthetic strict-gate futility fixture failed")
    return {
        "anchored_tie_membership": first_group,
        "immobile_chain": {
            "invalid_cross_occupied": immobile_counters["invalid_cross_occupied"],
            "invalid_same_row_or_column": immobile_counters["invalid_same_row_or_column"],
            "lazy_stays": immobile_counters["lazy_stays"],
            "retained_duplicate_count": immobile_counters["retained_duplicate_count"],
            "returned_to_observed_count": immobile_counters["returned_to_observed_count"],
        },
        "immobile": immobile_diagnostic,
        "mobile": mobile_diagnostic,
        "mobile_accepted_swaps": mobile_counters["accepted_swaps"],
        "p_MC_minimum": tail_value,
        "quantile_q0.99_fixture": 98.0,
        "slot_order_distinguished": True,
        "strict_futility_boundary_passed": True,
    }


def compute_scientific_artifacts(synthetic: bool) -> tuple[dict[str, Any], ArtifactAccumulator]:
    if synthetic:
        input_hashes: dict[str, str] = {}
        cohort = synthetic_cohort()
        compiled_by_view = {
            view: synthetic_compiled_view(view) for view in VIEW_ORDER
        }
        branch_report = exercise_synthetic_branches()
    else:
        if _BOOTSTRAP_INPUT_HASHES != EXPECTED_INPUT_HASHES:
            raise RuntimeError("bootstrap immutable-input hashes are absent or changed")
        input_hashes = dict(_BOOTSTRAP_INPUT_HASHES)
        _, anchors = load_phase_a_contract()
        relations = load_relation_vocabulary()
        facts = load_fact_ledger(anchors)
        news_to_pattern, patterns, pattern_matrix = parse_news(anchors)
        cohort = load_real_cohort(news_to_pattern, patterns, pattern_matrix)
        compiled_by_view = {
            view: compile_endpoint_graphs(anchors, facts, relations, view)
            for view in VIEW_ORDER
        }
        branch_report = {}
    ranking = make_ranking_cache(cohort)
    accumulator = ArtifactAccumulator.empty()
    view_summaries: dict[str, Any] = {}
    reached_stage: dict[str, str] = {}
    structural_pass = True
    for view in VIEW_ORDER:
        if not synthetic and not structural_pass:
            reached_stage[view] = "skipped_by_preceding_failed_conjunct"
            continue
        summary, passed, terminal_stage = evaluate_view(
            compiled_by_view[view],
            cohort,
            ranking,
            accumulator,
            forced_full_path=synthetic,
        )
        view_summaries[view] = summary
        reached_stage[view] = terminal_stage
        if not synthetic and not passed:
            structural_pass = False
    total_proposals = sum(
        int(row["proposals"]) for row in accumulator.chain_diagnostics
    )
    retained_endpoint_states = sum(
        1 for row in accumulator.state_metrics if row["kind"] == "null"
    )
    if synthetic:
        if total_proposals != 4_774_300 or retained_endpoint_states != 280:
            raise RuntimeError("synthetic schedule totals do not reproduce")
        structural_verdict = "SYNTHETIC_FORCED_FULL_PATH_PASS"
    else:
        structural_verdict = (
            "PASS_H10A_RELATION_NULL_FEASIBILITY"
            if structural_pass and len(view_summaries) == 3
            else "KILL_H10_RELATION_NULL_DIRECTION"
        )
    payload = {
        "branch_preflight": branch_report,
        "cohort_counts": dict(cohort.counts),
        "fixed_graph_counts": {
            view: graph_budget_report(compiled)
            for view, compiled in compiled_by_view.items()
        },
        "inputs_sha256": input_hashes,
        "labels_opened": False,
        "pcg_probe_digest_sha256": pcg_probe_digest(),
        "protocol_sha256": PROTOCOL_SHA256,
        "reached_stage": reached_stage,
        "representation_digest_sha256": representation_digest(cohort),
        "schema": "h10a_scientific_payload.v1",
        "structural_verdict": structural_verdict,
        "synthetic": bool(synthetic),
        "total_proposals": total_proposals,
        "retained_endpoint_states": retained_endpoint_states,
        "views": view_summaries,
    }
    return payload, accumulator


def jsonl_bytes(records: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_object_bytes(dict(record)) for record in records)


def render_scientific_artifacts(
    payload: Mapping[str, Any],
    accumulator: ArtifactAccumulator,
) -> dict[str, bytes]:
    state_metrics = sorted(accumulator.state_metrics, key=metric_sort_key)
    state_digests = sorted(accumulator.state_digests, key=digest_sort_key)
    chain_diagnostics = sorted(accumulator.chain_diagnostics, key=diagnostic_sort_key)
    parity_checks = sorted(accumulator.parity_checks, key=parity_sort_key)
    raw = {
        "state_metrics.jsonl": jsonl_bytes(state_metrics),
        "state_digests.jsonl": jsonl_bytes(state_digests),
        "chain_diagnostics.jsonl": jsonl_bytes(chain_diagnostics),
        "parity_checks.jsonl": jsonl_bytes(parity_checks),
    }
    complete_payload = dict(payload)
    complete_payload["raw_four_file_records"] = {
        name: {"bytes": len(content), "sha256": sha256_bytes(content)}
        for name, content in sorted(raw.items())
    }
    raw["scientific_payload.json"] = canonical_object_bytes(complete_payload)
    return raw


def validate_scientific_file_bytes(directory: Path) -> dict[str, bytes]:
    if not directory.is_dir():
        raise RuntimeError(f"scientific result directory is absent: {directory}")
    if {path.name for path in directory.iterdir()} != set(SCIENTIFIC_FILES) | {"result.json"}:
        raise RuntimeError(f"scientific output inventory differs: {directory}")
    result: dict[str, bytes] = {}
    for name in SCIENTIFIC_FILES:
        path = directory / name
        if not path.is_file():
            raise RuntimeError(f"scientific artifact is absent: {path}")
        content = path.read_bytes()
        if name.endswith(".jsonl"):
            read_jsonl(path)
        else:
            read_canonical_json(path)
        result[name] = content
    return result


def verify_artifact_inventory(
    envelope: Mapping[str, Any],
    directory: Path,
    scientific: Mapping[str, bytes],
) -> None:
    inventory = envelope.get("artifacts")
    if not isinstance(inventory, dict) or set(inventory) != set(SCIENTIFIC_FILES):
        raise RuntimeError("result envelope lacks scientific artifact inventory")
    for name in SCIENTIFIC_FILES:
        record = inventory.get(name)
        if (
            not isinstance(record, dict)
            or set(record) != {"bytes", "name", "sha256"}
            or not isinstance(record.get("bytes"), int)
            or isinstance(record.get("bytes"), bool)
            or int(record["bytes"]) < 0
            or not isinstance(record.get("name"), str)
            or not isinstance(record.get("sha256"), str)
            or HASH_RE.fullmatch(str(record["sha256"])) is None
        ):
            raise RuntimeError(f"result inventory lacks {name}")
        if (
            record.get("sha256") != sha256_bytes(scientific[name])
            or int(record.get("bytes", -1)) != len(scientific[name])
        ):
            raise RuntimeError(f"result inventory mismatch: {name}")
        if record["name"] != name:
            raise RuntimeError(f"result artifact name mismatch: {name}")


def require_integer_delta(container: Mapping[str, Any], start: str, stop: str, delta: str) -> None:
    values = (container.get(start), container.get(stop), container.get(delta))
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        raise RuntimeError(f"timing boundary is not integral: {start}/{stop}/{delta}")
    if (
        int(values[0]) < 0
        or int(values[1]) < int(values[0])
        or int(values[2]) != int(values[1]) - int(values[0])
    ):
        raise RuntimeError(f"timing integer arithmetic mismatch: {start}/{stop}/{delta}")


def validate_timing_envelope(envelope: Mapping[str, Any]) -> None:
    timing = envelope.get("timing")
    expected = {
        "module_region_1_start_ns", "module_region_1_stop_ns",
        "module_region_1_delta_ns", "module_region_2_start_ns",
        "module_region_2_stop_ns", "module_region_2_delta_ns", "module_ns",
    }
    if not isinstance(timing, dict) or set(timing) != expected:
        raise RuntimeError("result envelope lacks exact module timing boundaries")
    require_integer_delta(
        timing, "module_region_1_start_ns", "module_region_1_stop_ns",
        "module_region_1_delta_ns",
    )
    require_integer_delta(
        timing, "module_region_2_start_ns", "module_region_2_stop_ns",
        "module_region_2_delta_ns",
    )
    if (
        not isinstance(timing.get("module_ns"), int)
        or isinstance(timing.get("module_ns"), bool)
        or int(timing["module_ns"])
        != int(timing["module_region_1_delta_ns"])
        + int(timing["module_region_2_delta_ns"])
        or not (
            int(timing["module_region_1_start_ns"])
            <= int(timing["module_region_1_stop_ns"])
            <= int(timing["module_region_2_start_ns"])
            <= int(timing["module_region_2_stop_ns"])
        )
    ):
        raise RuntimeError("module timing order/sum mismatch")


def validate_result_directory(
    directory: Path,
    expected_role: str,
    synthetic: bool,
    auth: Mapping[str, Any],
    authorization_sha256: str,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    scientific = validate_scientific_file_bytes(directory)
    result_path = directory / "result.json"
    if not result_path.is_file():
        raise RuntimeError("result envelope is absent")
    envelope = read_canonical_json(result_path)
    if not isinstance(envelope, dict):
        raise RuntimeError("result envelope is malformed")
    if set(envelope) != {
        "artifacts", "decision", "numpy_tree_manifest_sha256",
        "numpy_tree_validation_passed", "output_id", "protocol_sha256",
        "provenance", "publication_directory", "run_role", "schema",
        "structural_verdict", "synthetic", "timing",
    }:
        raise RuntimeError("result envelope key set differs")
    expected_output_id = {
        "primary": "h10a_run_001",
        "exact_replay": "h10a_run_001_replay",
        "selftest_primary": "h10a_selftest_primary",
        "selftest_replay": "h10a_selftest_replay",
    }[expected_role]
    if (
        envelope.get("run_role") != expected_role
        or envelope.get("output_id") != expected_output_id
        or envelope.get("synthetic") is not synthetic
        or envelope.get("protocol_sha256") != PROTOCOL_SHA256
        or envelope.get("schema") != "h10a_result.v1"
        or Path(str(envelope.get("publication_directory", ""))).resolve()
        != directory.resolve()
        or envelope.get("numpy_tree_manifest_sha256")
        != auth.get("numpy_manifest_sha256")
        or envelope.get("numpy_tree_validation_passed") is not True
    ):
        raise RuntimeError("result envelope role/mode/protocol mismatch")
    payload = json.loads(scientific["scientific_payload.json"])
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "h10a_scientific_payload.v1"
        or payload.get("synthetic") is not synthetic
        or payload.get("protocol_sha256") != PROTOCOL_SHA256
        or payload.get("labels_opened") is not False
        or envelope.get("structural_verdict") != payload.get("structural_verdict")
    ):
        raise RuntimeError("result/scientific structural verdict mismatch")
    raw_records = payload.get("raw_four_file_records")
    raw_names = set(SCIENTIFIC_FILES) - {"scientific_payload.json"}
    if not isinstance(raw_records, dict) or set(raw_records) != raw_names:
        raise RuntimeError("scientific payload raw-file inventory mismatch")
    for name in raw_names:
        if raw_records[name] != {
            "bytes": len(scientific[name]),
            "sha256": sha256_bytes(scientific[name]),
        }:
            raise RuntimeError(f"scientific payload raw-file record mismatch: {name}")
    verify_artifact_inventory(envelope, directory, scientific)
    validate_timing_envelope(envelope)
    provenance = envelope.get("provenance")
    runtime_files = auth["runtime_files"]
    if (
        not isinstance(provenance, dict)
        or set(provenance)
        != {
            "authorization_sha256", "implementation_lock_sha256",
            "pcg_probe_sha256", "protocol_sha256", "runner_sha256",
        }
        or provenance.get("authorization_sha256") != authorization_sha256
        or provenance.get("implementation_lock_sha256")
        != auth.get("active_lock_sha256")
        or provenance.get("pcg_probe_sha256") != auth.get("expected_pcg_probe_sha256")
        or provenance.get("protocol_sha256") != PROTOCOL_SHA256
        or provenance.get("runner_sha256") != runtime_files["runner"]["sha256"]
    ):
        raise RuntimeError("result provenance mismatch")
    module_ns = int(envelope["timing"]["module_ns"])
    structural = str(envelope["structural_verdict"])
    expected_decision = (
        "SYNTHETIC_FORCED_FULL_PATH_NON_EVIDENCE"
        if synthetic
        else (
            "PASS_H10A_RELATION_NULL_FEASIBILITY"
            if structural == "PASS_H10A_RELATION_NULL_FEASIBILITY"
            and module_ns <= 30_000_000_000
            else "KILL_H10_RELATION_NULL_DIRECTION"
        )
    )
    if envelope.get("decision") != expected_decision:
        raise RuntimeError("result decision differs from locked module/science rule")
    return envelope, scientific


def bound_upstream_paths(auth: Mapping[str, Any], role: str) -> dict[str, Path]:
    upstream = auth.get("upstream_roles")
    if isinstance(upstream, dict) and isinstance(upstream.get(role), dict):
        source: Mapping[str, Any] = upstream[role]
        fields = {
            "authorization": "authorization_path",
            "process_start": "process_start_path",
            "process_ack": "process_ack_path",
            "stdout": "stdout_path",
            "stderr": "stderr_path",
            "async": "async_error_ledger",
            "inner_release": "inner_lock_release_path",
        }
        return {label: Path(str(source[field])).resolve() for label, field in fields.items()}
    launch_directory = resolve_bound_path(auth, "launch_directory")
    prefix = role
    return {
        "authorization": launch_directory / f"{prefix}_authorization.json",
        "process_start": launch_directory / f"{prefix}_process_start.json",
        "process_ack": launch_directory / f"{prefix}_process_ack.json",
        "stdout": launch_directory / f"{prefix}_stdout.log",
        "stderr": launch_directory / f"{prefix}_stderr.log",
        "async": launch_directory / f"{prefix}_async_errors.jsonl",
        "inner_release": launch_directory / f"{prefix}_inner_lock_released.json",
    }


def read_verification_crosslink(auth: Mapping[str, Any]) -> dict[str, Any]:
    bound = require_file_record_shape(
        auth.get("verification_crosslink"), "verification_crosslink"
    )
    path = Path(str(bound["path"])).resolve()
    if (
        not path.is_file()
        or path.parent != resolve_bound_path(auth, "launch_directory")
        or path.name != "verification_crosslink.json"
        or path.stat().st_size != int(bound["bytes"])
        or sha256_file(path) != bound["sha256"]
    ):
        raise RuntimeError("verification crosslink file binding mismatch")
    value = read_json(path)
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema_version", "launch_id", "mode", "execution_mode",
            "protocol_sha256", "implementation_lock", "primary",
            "exact_replay", "required_scientific_files",
            "scientific_files_byte_identical", "created_unix_ns",
        }
        or value.get("schema_version") != "h10a_verification_crosslink.v1"
        or value.get("mode") != "h10a-verification-crosslink"
        or value.get("execution_mode")
        != ("SelfTest" if auth.get("action") == "self-test" else "Real")
        or value.get("launch_id") != auth.get("launch_id")
        or value.get("protocol_sha256") != PROTOCOL_SHA256
        or value.get("required_scientific_files") != list(SCIENTIFIC_FILES)
        or value.get("scientific_files_byte_identical") is not True
        or not isinstance(value.get("created_unix_ns"), int)
        or isinstance(value.get("created_unix_ns"), bool)
        or int(value["created_unix_ns"]) <= 0
        or int(value["created_unix_ns"]) > int(auth["authorized_unix_ns"])
    ):
        raise RuntimeError("verification crosslink identity mismatch")
    lock_record = require_file_record_shape(
        value.get("implementation_lock"), "crosslink/implementation_lock"
    )
    active_lock = resolve_bound_path(auth, "active_lock_path")
    if (
        Path(str(lock_record.get("path", ""))).resolve() != active_lock
        or lock_record.get("sha256") != auth.get("active_lock_sha256")
        or int(lock_record.get("bytes", -1)) != active_lock.stat().st_size
        or file_record(active_lock) != lock_record
    ):
        raise RuntimeError("verification crosslink implementation-lock mismatch")
    return value


def crosslink_role_entry(
    crosslink: Mapping[str, Any], expected_role: str
) -> Mapping[str, Any]:
    key = "primary" if expected_role in {"primary", "selftest_primary"} else "exact_replay"
    value = crosslink.get(key)
    if not isinstance(value, dict) or value.get("role") != expected_role:
        raise RuntimeError(f"crosslink role entry is absent/ambiguous: {expected_role}")
    return value


def path_record(record: Any, label: str) -> Path:
    record = require_file_record_shape(record, f"crosslink/{label}")
    path = Path(str(record["path"])).resolve()
    if (
        not path.is_file()
        or path.stat().st_size != int(record["bytes"])
        or sha256_file(path) != record["sha256"]
    ):
        raise RuntimeError(f"crosslink file record mismatch: {label}")
    return path


def validate_crosslink_runtime(
    entry: Mapping[str, Any],
    expected_role: str,
    expected_directory: Path,
    synthetic: bool,
) -> dict[str, Path]:
    transport = entry.get("transport")
    runtime = entry.get("runtime")
    outputs = entry.get("outputs")
    if (
        set(entry) != {"role", "output_directory", "transport", "runtime", "outputs"}
        or entry.get("role") != expected_role
        or Path(str(entry.get("output_directory", ""))).resolve() != expected_directory
        or not isinstance(transport, dict)
        or not isinstance(runtime, dict)
        or not isinstance(outputs, dict)
    ):
        raise RuntimeError(f"crosslink role envelope mismatch: {expected_role}")
    expected_transport_keys = {
        "label", "pid", "exit_code", "launcher_elapsed_ticks",
        "stopwatch_frequency", "launcher_peak_resident_bytes",
        "live_peak_samples", "post_exit_peak_query",
        "post_exit_peak_query_succeeded", "job_active_processes_after_exit",
        "authorization", "process_start", "process_ack", "stdout", "stderr",
        "async_error_ledger", "inner_lock_release",
    }
    expected_runtime_keys = {
        "perf_start_ns", "perf_stop_ns", "perf_delta_ns", "module_ns",
        "runner_peak_resident_bytes", "launcher_elapsed_ticks",
        "stopwatch_frequency", "launcher_peak_resident_bytes",
        "authoritative_peak_resident_bytes", "module_passed",
    }
    if set(transport) != expected_transport_keys or set(runtime) != expected_runtime_keys:
        raise RuntimeError(f"crosslink transport/runtime schema mismatch: {expected_role}")
    for name in (
        "pid", "exit_code", "launcher_elapsed_ticks", "stopwatch_frequency",
        "launcher_peak_resident_bytes", "live_peak_samples", "job_active_processes_after_exit",
    ):
        if not isinstance(transport.get(name), int) or isinstance(transport.get(name), bool):
            raise RuntimeError(f"crosslink transport integer is malformed: {expected_role}/{name}")
    if (
        transport.get("label") != expected_role
        or int(transport["exit_code"]) != 0
        or int(transport["pid"]) <= 0
        or process_is_alive(int(transport["pid"]))
        or int(transport["launcher_elapsed_ticks"]) < 0
        or int(transport["stopwatch_frequency"]) <= 0
        or int(transport["launcher_peak_resident_bytes"]) <= 0
        or int(transport["launcher_peak_resident_bytes"]) > 2 * 1024 ** 3
        or int(transport["live_peak_samples"]) < 1
        or transport.get("post_exit_peak_query") != "success"
        or transport.get("post_exit_peak_query_succeeded") is not True
        or int(transport["job_active_processes_after_exit"]) != 0
        or int(transport["launcher_elapsed_ticks"]) * 1_000_000_000
        > (150_000_000_000 if synthetic else 180_000_000_000)
        * int(transport["stopwatch_frequency"])
    ):
        raise RuntimeError(f"crosslink transport/resource gate failed: {expected_role}")
    require_integer_delta(runtime, "perf_start_ns", "perf_stop_ns", "perf_delta_ns")
    for name in (
        "module_ns", "runner_peak_resident_bytes", "launcher_peak_resident_bytes",
        "authoritative_peak_resident_bytes", "launcher_elapsed_ticks", "stopwatch_frequency",
    ):
        if not isinstance(runtime.get(name), int) or isinstance(runtime.get(name), bool):
            raise RuntimeError(f"crosslink runtime integer is malformed: {expected_role}/{name}")
    if (
        int(runtime["perf_delta_ns"])
        > (150_000_000_000 if synthetic else 180_000_000_000)
        or int(runtime["module_ns"]) < 0
        or int(runtime["module_ns"]) > int(runtime["perf_delta_ns"])
        or int(runtime["runner_peak_resident_bytes"]) <= 0
        or int(runtime["launcher_peak_resident_bytes"]) <= 0
        or int(runtime["authoritative_peak_resident_bytes"])
        != max(
            int(runtime["runner_peak_resident_bytes"]),
            int(runtime["launcher_peak_resident_bytes"]),
        )
        or int(runtime["authoritative_peak_resident_bytes"]) > 2 * 1024 ** 3
        or int(runtime["launcher_peak_resident_bytes"]) != int(transport["launcher_peak_resident_bytes"])
        or int(runtime["launcher_elapsed_ticks"]) != int(transport["launcher_elapsed_ticks"])
        or int(runtime["stopwatch_frequency"]) != int(transport["stopwatch_frequency"])
        or int(runtime["perf_delta_ns"]) * int(runtime["stopwatch_frequency"])
        > int(runtime["launcher_elapsed_ticks"]) * 1_000_000_000
        or runtime.get("module_passed") is not (int(runtime["module_ns"]) <= 30_000_000_000)
    ):
        raise RuntimeError(f"crosslink runtime/resource arithmetic failed: {expected_role}")
    transport_paths: dict[str, Path] = {}
    for label in (
        "authorization", "process_start", "process_ack", "stdout", "stderr",
        "async_error_ledger", "inner_lock_release",
    ):
        transport_paths[label] = path_record(transport.get(label), f"{expected_role}/{label}")
    if (
        transport_paths["stderr"].stat().st_size != 0
        or transport_paths["async_error_ledger"].stat().st_size != 0
    ):
        raise RuntimeError(f"crosslink stderr/async evidence is nonempty: {expected_role}")
    expected_output_names = set(SCIENTIFIC_FILES) | {"result.json"}
    if set(outputs) != expected_output_names:
        raise RuntimeError(f"crosslink output inventory mismatch: {expected_role}")
    for name in expected_output_names:
        path = path_record(outputs[name], f"{expected_role}/outputs/{name}")
        if path != (expected_directory / name).resolve():
            raise RuntimeError(f"crosslink output path mismatch: {expected_role}/{name}")
    return transport_paths


def optional_bound_record_check(
    auth: Mapping[str, Any], role: str, label: str, path: Path
) -> None:
    upstream = auth.get("upstream_roles")
    if not isinstance(upstream, dict) or not isinstance(upstream.get(role), dict):
        return
    source = upstream[role]
    record = source.get(f"{label}_record")
    if record is None:
        return
    if (
        not isinstance(record, dict)
        or record.get("sha256") != sha256_file(path)
        or int(record.get("bytes", -1)) != path.stat().st_size
    ):
        raise RuntimeError(f"verifier authorization upstream record mismatch: {role}/{label}")


def validate_upstream_launch_role(
    auth: Mapping[str, Any],
    role: str,
    result_directory: Path,
    synthetic: bool,
    paths_override: Mapping[str, Path] | None = None,
    transport: Mapping[str, Any] | None = None,
    runtime: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if paths_override is None:
        paths = bound_upstream_paths(auth, role)
    else:
        paths = {
            "authorization": paths_override["authorization"],
            "process_start": paths_override["process_start"],
            "process_ack": paths_override["process_ack"],
            "stdout": paths_override["stdout"],
            "stderr": paths_override["stderr"],
            "async": paths_override["async_error_ledger"],
            "inner_release": paths_override["inner_lock_release"],
        }
    launch_directory = resolve_bound_path(auth, "launch_directory")
    expected_paths = bound_upstream_paths(auth, role)
    for label, path in paths.items():
        if not path.is_file() or path.resolve() != expected_paths[label].resolve():
            raise RuntimeError(f"upstream launcher artifact is absent: {role}/{label}")
    if paths["stderr"].stat().st_size != 0 or paths["async"].stat().st_size != 0:
        raise RuntimeError(f"upstream stderr/async ledger is nonempty: {role}")
    authorization = read_json(paths["authorization"])
    start = read_json(paths["process_start"])
    ack = read_json(paths["process_ack"])
    release = read_canonical_json(paths["inner_release"])
    authorization_sha = sha256_file(paths["authorization"])
    expected_action = "self-test" if synthetic else "run"
    expected_output_id = {
        "primary": "h10a_run_001",
        "exact_replay": "h10a_run_001_replay",
        "selftest_primary": "h10a_selftest_primary",
        "selftest_replay": "h10a_selftest_replay",
    }[role]
    if not isinstance(authorization, dict) or set(authorization) != RUNNER_AUTHORIZATION_KEYS:
        raise RuntimeError(f"upstream authorization schema differs: {role}")
    for field in (
        "protocol_path", "protocol_sha256", "launcher_path", "launcher_sha256",
        "active_lock_path", "active_lock_sha256", "base_interpreter",
        "base_interpreter_sha256", "venv_launcher", "venv_launcher_sha256",
        "venv_config", "venv_config_sha256", "synthetic_generator_path",
        "synthetic_generator_sha256", "synthetic_fixture_manifest_path",
        "synthetic_fixture_manifest_sha256", "numpy_manifest_path",
        "numpy_manifest_sha256",
    ):
        if authorization.get(field) != auth.get(field):
            raise RuntimeError(f"upstream common runtime alias differs: {role}/{field}")
    if (
        authorization.get("schema_version") != "h10a_launcher_authorization.v1"
        or authorization.get("run_role") != role
        or authorization.get("output_id") != expected_output_id
        or authorization.get("action") != expected_action
        or authorization.get("synthetic_mode") is not synthetic
        or authorization.get("probe_mode") is not False
        or authorization.get("protocol_sha256") != PROTOCOL_SHA256
        or authorization.get("launch_id") != auth.get("launch_id")
        or int(authorization.get("launcher_pid", -1)) != int(auth["launcher_pid"])
        or authorization.get("subject_kind") != "runner"
        or Path(str(authorization.get("subject_path", ""))).resolve() != RUNNER_PATH
        or authorization.get("subject_sha256")
        != auth["runtime_files"]["runner"]["sha256"]
        or Path(str(authorization.get("output_directory", ""))).resolve()
        != result_directory
        or Path(str(authorization.get("authorization_path", ""))).resolve()
        != paths["authorization"]
        or Path(str(authorization.get("launch_directory", ""))).resolve()
        != launch_directory
        or Path(str(authorization.get("process_start_path", ""))).resolve()
        != paths["process_start"]
        or Path(str(authorization.get("process_ack_path", ""))).resolve()
        != paths["process_ack"]
        or Path(str(authorization.get("async_error_ledger", ""))).resolve()
        != paths["async"]
        or Path(str(authorization.get("inner_lock_release_path", ""))).resolve()
        != paths["inner_release"]
        or Path(str(authorization.get("resource_inner_lock_release_path", ""))).resolve()
        != (launch_directory / f"{role}_inner_lock_resource_released.json").resolve()
        or Path(str(authorization.get("inner_lock", ""))).resolve()
        != resolve_bound_path(auth, "inner_lock")
        or Path(str(authorization.get("outer_lock", ""))).resolve()
        != resolve_bound_path(auth, "outer_lock")
        or authorization.get("runtime_files") != auth.get("runtime_files")
        or authorization.get("runtime_hashes") != auth.get("runtime_hashes")
        or authorization.get("expected_pcg_probe_sha256")
        != auth.get("expected_pcg_probe_sha256")
        or authorization.get("pcg_probe_digest_sha256")
        != auth.get("pcg_probe_digest_sha256")
        or authorization.get("numpy_manifest_sha256")
        != auth.get("numpy_manifest_sha256")
        or authorization.get("label_free_only") is not True
        or authorization.get("candidate_labels_forbidden") is not True
        or authorization.get("candidate_suffix_labels_forbidden") is not True
        or authorization.get("behaviors_tsv_forbidden") is not True
        or authorization.get("forced_full_path") is not synthetic
        or not isinstance(authorization.get("token"), str)
        or authorization.get("token_sha256")
        != sha256_bytes(str(authorization.get("token", "")).encode("utf-8"))
        or not isinstance(authorization.get("authorized_unix_ns"), int)
        or isinstance(authorization.get("authorized_unix_ns"), bool)
        or int(authorization["authorized_unix_ns"]) <= 0
    ):
        raise RuntimeError(f"upstream authorization identity mismatch: {role}")
    if synthetic:
        if (
            authorization.get("immutable_input_sha256") != {}
            or authorization.get("immutable_input_paths") != {}
            or authorization.get("phase_a_commit") is not None
            or Path(str(authorization.get("synthetic_fixture_manifest", ""))).resolve()
            != FIXTURE_MANIFEST_PATH.resolve()
        ):
            raise RuntimeError(f"synthetic upstream input surface differs: {role}")
    elif (
        authorization.get("immutable_input_sha256") != EXPECTED_INPUT_HASHES
        or authorization.get("phase_a_commit") != EXPECTED_PHASE_A_COMMIT
        or authorization.get("synthetic_fixture_manifest") is not None
    ):
        raise RuntimeError(f"real upstream input surface differs: {role}")
    if not synthetic:
        authorized_inputs = authorization.get("immutable_input_paths")
        if not isinstance(authorized_inputs, dict) or set(authorized_inputs) != set(INPUT_PATHS):
            raise RuntimeError(f"real upstream input-path schema differs: {role}")
        for name, expected_path in INPUT_PATHS.items():
            if Path(str(authorized_inputs[name])).resolve() != expected_path.resolve():
                raise RuntimeError(f"real upstream input path differs: {role}/{name}")
    expected_start_keys = {
        "action", "authorization_sha256", "environment", "launch_id",
        "launcher_pid", "mode", "output_id", "process_pid", "run_role",
        "subject_kind", "subject_path", "subject_sha256", "token_sha256",
    }
    expected_ack_keys = {
        "mode", "action", "run_role", "launch_id", "launcher_pid",
        "process_pid", "authorization_sha256", "token_sha256",
        "subject_sha256", "acknowledged_unix_ns",
    }
    environment = start.get("environment") if isinstance(start, dict) else None
    if (
        not isinstance(start, dict)
        or set(start) != expected_start_keys
        or start.get("mode") != "h10a-child-process-start"
        or start.get("action") != expected_action
        or start.get("run_role") != role
        or start.get("output_id") != expected_output_id
        or start.get("subject_kind") != "runner"
        or Path(str(start.get("subject_path", ""))).resolve() != RUNNER_PATH
        or start.get("subject_sha256") != authorization.get("subject_sha256")
        or start.get("authorization_sha256") != authorization_sha
        or not isinstance(ack, dict)
        or set(ack) != expected_ack_keys
        or ack.get("mode") != "h10a-child-process-acknowledgement"
        or ack.get("action") != expected_action
        or ack.get("run_role") != role
        or ack.get("authorization_sha256") != authorization_sha
        or ack.get("launch_id") != authorization.get("launch_id")
        or start.get("launch_id") != authorization.get("launch_id")
        or int(ack.get("process_pid", -1)) != int(start.get("process_pid", -2))
        or ack.get("token_sha256") != authorization.get("token_sha256")
        or start.get("token_sha256") != authorization.get("token_sha256")
        or ack.get("subject_sha256") != authorization.get("subject_sha256")
        or int(start.get("launcher_pid", -1)) != int(auth["launcher_pid"])
        or int(ack.get("launcher_pid", -1)) != int(auth["launcher_pid"])
        or not isinstance(ack.get("acknowledged_unix_ns"), int)
        or isinstance(ack.get("acknowledged_unix_ns"), bool)
        or int(ack["acknowledged_unix_ns"]) <= 0
        or not isinstance(environment, dict)
        or set(environment)
        != {
            "cuda_visible_devices", "main_thread_only", "numpy_version",
            "numpy_tree_manifest_sha256", "numpy_tree_validation_passed",
            "pcg_probe_sha256", "python_hash_seed", "python_version",
            "runtime_files", "sys_base_executable", "sys_base_prefix",
            "sys_executable", "sys_prefix", "thread_bounds",
        }
        or environment.get("cuda_visible_devices") != "-1"
        or environment.get("main_thread_only") is not True
        or environment.get("numpy_version") != NUMPY_VERSION
        or environment.get("numpy_tree_manifest_sha256")
        != auth.get("numpy_manifest_sha256")
        or environment.get("numpy_tree_validation_passed") is not True
        or environment.get("pcg_probe_sha256") != auth.get("expected_pcg_probe_sha256")
        or environment.get("python_hash_seed") != "0"
        or environment.get("python_version") != "3.12.13"
        or environment.get("runtime_files") != auth.get("runtime_files")
        or Path(str(environment.get("sys_executable", ""))).resolve()
        != VENV_LAUNCHER_PATH.resolve()
        or Path(str(environment.get("sys_base_executable", ""))).resolve()
        != resolve_bound_path(auth, "base_interpreter")
        or Path(str(environment.get("sys_prefix", ""))).resolve()
        != VENV_LAUNCHER_PATH.parent.parent.resolve()
        or Path(str(environment.get("sys_base_prefix", ""))).resolve()
        != resolve_bound_path(auth, "base_interpreter").parent.resolve()
        or environment.get("thread_bounds") != {name: "1" for name in THREAD_ENV_NAMES}
    ):
        raise RuntimeError(f"upstream launcher identity mismatch: {role}")
    child_pid = int(start.get("process_pid", -1))
    if child_pid <= 0 or process_is_alive(child_pid):
        raise RuntimeError(f"upstream child process still survives: {role}/{child_pid}")
    if (
        not isinstance(release, dict)
        or set(release)
        != {
            "action", "authorization_sha256", "created_unix_ns", "launch_id",
            "mode", "process_pid", "run_role", "token_sha256",
        }
        or release.get("mode") != "h10a-child-inner-lock"
        or release.get("action") != expected_action
        or release.get("run_role") != role
        or release.get("launch_id") != authorization.get("launch_id")
        or int(release.get("process_pid", -1)) != child_pid
        or release.get("authorization_sha256") != authorization_sha
        or release.get("token_sha256") != authorization.get("token_sha256")
        or not isinstance(release.get("created_unix_ns"), int)
        or isinstance(release.get("created_unix_ns"), bool)
        or not (
            int(authorization["authorized_unix_ns"])
            <= int(release["created_unix_ns"])
            <= int(ack["acknowledged_unix_ns"])
        )
    ):
        raise RuntimeError(f"upstream inner-lock release mismatch: {role}")
    stdout_raw = paths["stdout"].read_bytes()
    stdout_lines = stdout_raw.splitlines(keepends=True)
    if len(stdout_lines) != 1:
        raise RuntimeError(f"upstream stdout does not contain one summary: {role}")
    summary = json.loads(stdout_lines[0])
    if not isinstance(summary, dict):
        raise RuntimeError(f"upstream stdout summary is not an object: {role}")
    expected_summary_keys = {
        "module_ns", "numpy_tree_manifest_sha256",
        "numpy_tree_validation_passed", "output_directory", "output_id",
        "pcg_probe_sha256", "peak_resident_bytes", "perf_delta_ns",
        "perf_start_ns", "perf_stop_ns", "process_pid", "result", "run_role",
        "scientific_verdict", "status",
    }
    for name in (
        "module_ns", "peak_resident_bytes", "perf_delta_ns", "perf_start_ns",
        "perf_stop_ns", "process_pid",
    ):
        if not isinstance(summary.get(name), int) or isinstance(summary.get(name), bool):
            raise RuntimeError(f"upstream stdout integer malformed: {role}/{name}")
    if (
        not isinstance(summary, dict)
        or set(summary) != expected_summary_keys
        or stdout_raw
        not in {
            canonical_object_bytes(summary),
            canonical_object_bytes(summary)[:-1] + b"\r\n",
        }
        or summary.get("status") != "H10A_RUN_COMPLETE"
        or summary.get("run_role") != role
        or summary.get("output_id") != expected_output_id
        or Path(str(summary.get("output_directory", ""))).resolve()
        != result_directory
        or Path(str(summary.get("result", ""))).resolve()
        != (result_directory / "result.json").resolve()
        or int(summary.get("process_pid", -1)) != child_pid
        or summary.get("pcg_probe_sha256") != auth.get("expected_pcg_probe_sha256")
        or summary.get("numpy_tree_manifest_sha256")
        != auth.get("numpy_manifest_sha256")
        or summary.get("numpy_tree_validation_passed") is not True
        or int(summary["peak_resident_bytes"]) <= 0
        or int(summary["module_ns"]) < 0
    ):
        raise RuntimeError(f"upstream stdout summary mismatch: {role}")
    require_integer_delta(summary, "perf_start_ns", "perf_stop_ns", "perf_delta_ns")
    if transport is not None and (
        int(transport.get("pid", -1)) != child_pid
        or int(transport.get("exit_code", -1)) != 0
    ):
        raise RuntimeError(f"upstream transport PID/exit mismatch: {role}")
    if runtime is not None and (
        int(runtime.get("perf_start_ns", -1)) != int(summary["perf_start_ns"])
        or int(runtime.get("perf_stop_ns", -1)) != int(summary["perf_stop_ns"])
        or int(runtime.get("perf_delta_ns", -1)) != int(summary["perf_delta_ns"])
        or int(runtime.get("module_ns", -1)) != int(summary["module_ns"])
        or int(runtime.get("runner_peak_resident_bytes", -1))
        != int(summary["peak_resident_bytes"])
    ):
        raise RuntimeError(f"upstream runtime/stdout mismatch: {role}")
    return {
        "async_error_ledger": file_record(paths["async"]),
        "authorization": file_record(paths["authorization"]),
        "inner_lock_release": file_record(paths["inner_release"]),
        "process_ack": file_record(paths["process_ack"]),
        "process_start": file_record(paths["process_start"]),
        "stderr": file_record(paths["stderr"]),
        "stdout": file_record(paths["stdout"]),
    }


def acquire_verifier_inner_lock(auth: Mapping[str, Any]) -> dict[str, Any]:
    global _INNER_LOCK_FD
    path = resolve_bound_path(auth, "inner_lock")
    release_path = resolve_bound_path(auth, "inner_lock_release_path")
    if path.parent != H10_DIR.resolve() or release_path.parent != resolve_bound_path(auth, "launch_directory"):
        raise RuntimeError("verifier inner-lock containment mismatch")
    if release_path.exists():
        raise RuntimeError("verifier inner-lock release pre-exists")
    owner = {
        "action": auth["action"],
        "authorization_sha256": sha256_file(resolve_bound_path(auth, "authorization_path")),
        "created_unix_ns": time.time_ns(),
        "launch_id": auth["launch_id"],
        "mode": "h10a-child-inner-lock",
        "process_pid": os.getpid(),
        "run_role": "verifier",
        "token_sha256": auth["token_sha256"],
    }
    try:
        _INNER_LOCK_FD = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    except FileExistsError as error:
        raise RuntimeError("verifier inner lock pre-exists") from error
    os.write(_INNER_LOCK_FD, canonical_object_bytes(owner))
    os.fsync(_INNER_LOCK_FD)
    return file_record(path)


def publish_verification_directory(
    auth: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> tuple[Path, dict[str, Any]]:
    output = resolve_bound_path(auth, "output_directory")
    allowed_parent = resolve_bound_path(auth, "launch_directory")
    if output.parent != allowed_parent or output.name != str(auth.get("output_id")):
        raise RuntimeError("verifier output directory is not exactly authorized")
    if resolve_bound_path(auth, "verification_path") != (output / "verification.json").resolve():
        raise RuntimeError("verifier result path is not exactly authorized")
    if output.exists():
        raise RuntimeError("verifier output directory already exists")
    stage = allowed_parent / f".{output.name}.tmp.{uuid.uuid4().hex}"
    if stage.exists():
        raise RuntimeError("verifier stage unexpectedly exists")
    stage.mkdir(parents=False)
    try:
        write_exclusive_json(stage / "verification.json", dict(verification))
        require_no_async_failures()
        rename_no_overwrite(stage, output)
    except BaseException:
        if stage.exists():
            staged_result = stage / "verification.json"
            if staged_result.is_file():
                staged_result.unlink()
            stage.rmdir()
        raise
    result_path = output / "verification.json"
    return output, file_record(result_path)


def verification_run(
    auth: Mapping[str, Any], synthetic: bool, perf_start_ns: int
) -> dict[str, Any]:
    global _INNER_LOCK_RECORD
    np = np_module()
    if auth.get("synthetic_mode") is not synthetic:
        raise RuntimeError("authorization/command synthetic-mode mismatch")
    verify_authorized_input_surface(auth, synthetic)
    expected_probe = auth.get("pcg_probe_digest_sha256")
    observed_probe = pcg_probe_digest()
    if not isinstance(expected_probe, str) or expected_probe != observed_probe:
        raise RuntimeError("PCG64DXSM probe digest mismatch")
    if _INNER_LOCK_RECORD is None or _INNER_LOCK_FD is None:
        raise RuntimeError("verifier inner lock was not acquired before process-start")
    inner_lock_record = dict(_INNER_LOCK_RECORD)
    primary_directory = resolve_bound_path(auth, "primary_output_directory")
    replay_directory = resolve_bound_path(auth, "replay_output_directory")
    expected_primary_role = "selftest_primary" if synthetic else "primary"
    expected_replay_role = "selftest_replay" if synthetic else "exact_replay"
    launch_directory = resolve_bound_path(auth, "launch_directory")
    result_parent = launch_directory if synthetic else (H10_DIR / "results").resolve()
    if (
        primary_directory == replay_directory
        or resolve_bound_path(auth, "primary_directory") != primary_directory
        or resolve_bound_path(auth, "replay_directory") != replay_directory
        or primary_directory.parent != result_parent
        or replay_directory.parent != result_parent
        or primary_directory.name
        != ("h10a_selftest_primary" if synthetic else "h10a_run_001")
        or replay_directory.name
        != ("h10a_selftest_replay" if synthetic else "h10a_run_001_replay")
    ):
        raise RuntimeError("primary/replay result-directory authorization differs")
    crosslink = read_verification_crosslink(auth)
    primary_entry = crosslink_role_entry(crosslink, expected_primary_role)
    replay_entry = crosslink_role_entry(crosslink, expected_replay_role)
    primary_paths = validate_crosslink_runtime(
        primary_entry, expected_primary_role, primary_directory, synthetic
    )
    replay_paths = validate_crosslink_runtime(
        replay_entry, expected_replay_role, replay_directory, synthetic
    )
    primary_launch = validate_upstream_launch_role(
        auth, expected_primary_role, primary_directory, synthetic, primary_paths,
        primary_entry["transport"], primary_entry["runtime"],
    )
    replay_launch = validate_upstream_launch_role(
        auth, expected_replay_role, replay_directory, synthetic, replay_paths,
        replay_entry["transport"], replay_entry["runtime"],
    )
    primary_envelope, primary_bytes = validate_result_directory(
        primary_directory, expected_primary_role, synthetic, auth,
        primary_launch["authorization"]["sha256"],
    )
    replay_envelope, replay_bytes = validate_result_directory(
        replay_directory, expected_replay_role, synthetic, auth,
        replay_launch["authorization"]["sha256"],
    )
    primary_summary = json.loads(primary_paths["stdout"].read_bytes())
    replay_summary = json.loads(replay_paths["stdout"].read_bytes())
    for label, summary, envelope in (
        (expected_primary_role, primary_summary, primary_envelope),
        (expected_replay_role, replay_summary, replay_envelope),
    ):
        module_timing = envelope["timing"]
        if (
            summary.get("scientific_verdict") != envelope.get("structural_verdict")
            or int(summary.get("module_ns", -1)) != int(module_timing["module_ns"])
            or not (
                int(summary["perf_start_ns"])
                <= int(module_timing["module_region_1_start_ns"])
                <= int(module_timing["module_region_1_stop_ns"])
                <= int(module_timing["module_region_2_start_ns"])
                <= int(module_timing["module_region_2_stop_ns"])
                <= int(summary["perf_stop_ns"])
            )
            or summary.get("numpy_tree_manifest_sha256")
            != envelope.get("numpy_tree_manifest_sha256")
            or summary.get("numpy_tree_validation_passed")
            != envelope.get("numpy_tree_validation_passed")
        ):
            raise RuntimeError(f"upstream stdout/result mismatch: {label}")
    for name in SCIENTIFIC_FILES:
        if primary_bytes[name] != replay_bytes[name]:
            raise RuntimeError(f"primary/replay scientific bytes differ: {name}")
    payload, accumulator = compute_scientific_artifacts(synthetic)
    regenerated = render_scientific_artifacts(payload, accumulator)
    for name in SCIENTIFIC_FILES:
        if regenerated[name] != primary_bytes[name]:
            raise RuntimeError(f"independent verifier artifact mismatch: {name}")
    if not all(row.get("passed") is True for row in accumulator.parity_checks):
        raise RuntimeError("independent parity record failed")
    require_no_async_failures()
    if not process_is_alive(int(auth["launcher_pid"])):
        raise RuntimeError("launcher exited before verifier publication")
    assert_outer_lock(resolve_bound_path(auth, "outer_lock"))
    scientific_records = {
        name: {"bytes": len(regenerated[name]), "sha256": sha256_bytes(regenerated[name])}
        for name in SCIENTIFIC_FILES
    }
    structural_verdict = str(primary_envelope["structural_verdict"])
    if structural_verdict != replay_envelope["structural_verdict"]:
        raise RuntimeError("primary/replay structural verdict differs")
    primary_module_passed = primary_entry["runtime"].get("module_passed") is True
    replay_module_passed = replay_entry["runtime"].get("module_passed") is True
    if synthetic:
        if (
            structural_verdict != "SYNTHETIC_FORCED_FULL_PATH_PASS"
            or not primary_module_passed
            or not replay_module_passed
        ):
            raise RuntimeError("synthetic full-path/module preflight did not pass")
        scientific_verdict = "SYNTHETIC_NOT_SCIENTIFIC"
        final_verdict = "PASS_H10A_PREFLIGHT"
    else:
        if structural_verdict not in {
            "PASS_H10A_RELATION_NULL_FEASIBILITY",
            "KILL_H10_RELATION_NULL_DIRECTION",
        }:
            raise RuntimeError("real structural verdict is outside locked values")
        scientific_verdict = structural_verdict
        final_verdict = (
            "PASS_H10A_RELATION_NULL_FEASIBILITY"
            if structural_verdict == "PASS_H10A_RELATION_NULL_FEASIBILITY"
            and primary_module_passed
            and replay_module_passed
            else "KILL_H10_RELATION_NULL_DIRECTION"
        )
    # Re-hash all immutable implementation/runtime records, including a second
    # byte-for-byte NumPy tree regeneration, immediately before publication.
    validate_runtime_contract(auth)
    verification_compute_stop_ns = time.perf_counter_ns()
    result = {
        "authorization_sha256": sha256_file(resolve_bound_path(auth, "authorization_path")),
        "decision": {
            "primary_module_passed": primary_module_passed,
            "replay_module_passed": replay_module_passed,
            "scientific_verdict": scientific_verdict,
            "verdict": final_verdict,
        },
        "independent_outer_product_checks_passed": True,
        "independent_reconstruction_passed": True,
        "independent_scalar_checks_passed": True,
        "inner_lock_owner": inner_lock_record,
        "labels_opened": False,
        "launch_id": auth["launch_id"],
        "mode": "h10a-independent-verification",
        "numpy_tree_manifest_sha256": auth["numpy_manifest_sha256"],
        "numpy_tree_validation_passed": True,
        "numpy_version": np.__version__,
        "output_id": auth["output_id"],
        "pcg_probe_digest_sha256": observed_probe,
        "process_pid": os.getpid(),
        "primary": {
            "launch_artifacts": primary_launch,
            "result": file_record(primary_directory / "result.json"),
            "structural_verdict": primary_envelope["structural_verdict"],
        },
        "protocol_sha256": PROTOCOL_SHA256,
        "replay": {
            "launch_artifacts": replay_launch,
            "result": file_record(replay_directory / "result.json"),
            "structural_verdict": replay_envelope["structural_verdict"],
        },
        "run_role": "verifier",
        "schema_version": "h10a_independent_verification.v1",
        "scientific_artifacts": scientific_records,
        "scientific_bytes_identical": True,
        "scientific_payload_sha256": scientific_records["scientific_payload.json"]["sha256"],
        "structural_verdict": structural_verdict,
        "synthetic": synthetic,
        "verification_compute_timing": {
            "perf_delta_ns": verification_compute_stop_ns - perf_start_ns,
            "perf_start_ns": perf_start_ns,
            "perf_stop_ns": verification_compute_stop_ns,
        },
        "verification_crosslink": dict(auth["verification_crosslink"]),
        "verifier_inner_release_deferred_to_launcher": True,
    }
    output, record = publish_verification_directory(auth, result)
    verification_path = output / "verification.json"
    if (
        {path.name for path in output.iterdir()} != {"verification.json"}
        or read_canonical_json(verification_path) != result
    ):
        raise RuntimeError("published verifier inventory/bytes differ")
    record = file_record(verification_path)
    require_no_async_failures()
    if not process_is_alive(int(auth["launcher_pid"])):
        raise RuntimeError("launcher exited after verifier publication")
    assert_outer_lock(resolve_bound_path(auth, "outer_lock"))
    if not resolve_bound_path(auth, "inner_lock").is_file() or _INNER_LOCK_FD is None:
        raise RuntimeError("verifier inner lock disappeared before process exit")
    peak_resident_bytes = process_peak_resident_bytes()
    perf_stop_ns = time.perf_counter_ns()
    return {
        "numpy_tree_manifest_sha256": auth["numpy_manifest_sha256"],
        "numpy_tree_validation_passed": True,
        "output_directory": str(output),
        "output_id": auth["output_id"],
        "peak_resident_bytes": peak_resident_bytes,
        "perf_delta_ns": perf_stop_ns - perf_start_ns,
        "perf_start_ns": perf_start_ns,
        "perf_stop_ns": perf_stop_ns,
        "process_pid": os.getpid(),
        "run_role": "verifier",
        "scientific_payload_sha256": scientific_records["scientific_payload.json"]["sha256"],
        "scientific_verdict": scientific_verdict,
        "status": "H10A_SELFTEST_VERIFY_COMPLETE" if synthetic else "H10A_VERIFY_COMPLETE",
        "verdict": final_verdict,
        "verification_path": str(verification_path),
        "verification_sha256": record["sha256"],
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Independent verifier for locked H10A")
    parser.add_argument("command", choices=("self-test", "verify"))
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--process-start", required=True)
    parser.add_argument("--process-ack", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    try:
        auth = bootstrap_handshake(args)
        perf_start_ns = time.perf_counter_ns()
        result = verification_run(
            auth, synthetic=args.command == "self-test", perf_start_ns=perf_start_ns
        )
        require_no_async_failures()
        sys.stdout.write(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        )
        sys.stdout.flush()
        return 0
    except BaseException as error:
        traceback.print_exc(file=sys.stderr)
        print(
            json.dumps(
                {
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "status": "INCONCLUSIVE_INVALID_RUN",
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
