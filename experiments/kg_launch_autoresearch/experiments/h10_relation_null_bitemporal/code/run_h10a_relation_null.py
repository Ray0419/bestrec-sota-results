#!/usr/bin/env python3
"""Hash-authorized H10A relation-conditioned fixed-degree null experiment.

The runner is deliberately label blind.  ``probe`` imports only NumPy and does
not bind the scientific implementation, verifier, generator, fixture, or real
inputs.  ``self-test`` lazily imports the checked-in deterministic generator;
``run`` is the only action allowed to open the six immutable real inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
import re
import struct
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
ANCHORS = 50
AUDIT_SIZE = 8_192
EXPECTED_RELATIONS = 1_091
EXPECTED_MANIFEST_BYTES = 224_785_295
EXPECTED_INPUT_HASHES = {
    "news": "E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822",
    "relations": "D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A",
    "facts": "13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D",
    "phase_a_result": "B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF",
    "phase_a_manifest": "522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5",
    "phase_a_completion": "AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06",
}
EXPECTED_COUNTS = {
    "news_rows": 42_416, "supported_news": 12_060, "patterns": 812,
    "impressions": 64_443, "users": 43_374,
    "candidate_occurrences": 2_422_258,
    "supported_candidate_occurrences": 512_071,
    "gt10_candidates": 48_422, "gt10_candidates_and_support": 17_436,
    "ge2_supported_candidates": 44_341, "histories_with_support": 64_443,
    "audit_impressions": AUDIT_SIZE,
}
VIEW_ORDER = ("primary", "metadata_blocklist", "hub_removal")
ENDPOINT_ORDER = ("H", "C")
VIEW_ORDINAL = {value: index for index, value in enumerate(VIEW_ORDER)}
ENDPOINT_ORDINAL = {value: index for index, value in enumerate(ENDPOINT_ORDER)}
VIEW_BUDGETS = {
    "primary": {"relations": 110, "H": 4_481, "C": 5_529, "proposals": 3_003_000},
    "metadata_blocklist": {"relations": 105, "H": 4_388, "C": 5_104, "proposals": 949_200},
    "hub_removal": {"relations": 103, "H": 3_644, "C": 4_577, "proposals": 822_100},
}
METADATA_BLOCKLIST = frozenset({"P1343", "P1424", "P5008", "P6104", "P7867", "P8744", "P9241", "P2354", "P8402", "P10280", "P1889"})
HUB_QIDS = frozenset({"Q30", "Q22686"})
SCIENTIFIC_FILES = ("scientific_payload.json", "state_metrics.jsonl", "state_digests.jsonl", "chain_diagnostics.jsonl", "parity_checks.jsonl")
AUDIT_PREFIX = b"20260807|H10A|audit|"
RANK_PREFIX = b"20260807|H10A|rank|"
PARITY_PREFIX = b"20260807|H10A|parity|"
PAIR_PREFIX = b"20260807|H10A|pair|"
NULL_PREFIX = b"20260807|H10A|null|"
PCG_PREFIX = b"H10A_PCG_PROBE_V1\n"
PCG_SEED_TEXT = b"20260807|H10A|PCG_PROBE_V1"
THREAD_ENV = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
QID_RE = re.compile(r"^Q[0-9]+$")
PROPERTY_RE = re.compile(r"^P[0-9]+$")
NEWS_RE = re.compile(r"^N[0-9]+$")
FACT_RE = re.compile(r"^(P[0-9]+)\|(Q[0-9]+)$")
MANIFEST_LABEL_RE = re.compile(rb'"N[0-9]+-[01]"')

SCRIPT = Path(__file__).resolve()
H10_DIR = SCRIPT.parent.parent
ROOT = H10_DIR.parents[3]
PROTOCOL = H10_DIR / "protocol.md"
LAUNCHER = SCRIPT.with_name("run_h10a_relation_null_safe.ps1")
IMPLEMENTATION_LOCK = H10_DIR / "implementation_lock.md"
VERIFIER = SCRIPT.with_name("verify_h10a_relation_null.py")
GENERATOR = SCRIPT.with_name("generate_h10a_synthetic_fixture.py")
FIXTURE_MANIFEST = H10_DIR / "synthetic_fixture_manifest.json"
PROBE_COMPLETION = H10_DIR / "probe_artifacts/h10a_pcg_probe_completion.json"
VENV_LAUNCHER = ROOT / "_bestrec_run/.venv/Scripts/python.exe"
VENV_CONFIG = ROOT / "_bestrec_run/.venv/pyvenv.cfg"
H6_DIR = ROOT / "experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence"
INPUTS = {
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
_INNER_LOCK: "InnerLock | None" = None
_NUMPY_TREE_MANIFEST_SHA256: str | None = None
_NUMPY_TREE_VALIDATION_PASSED = False


def np_module() -> Any:
    global _NP
    if _NP is None:
        import numpy as np  # type: ignore
        if np.__version__ != NUMPY_VERSION:
            raise RuntimeError(f"NumPy version mismatch: {np.__version__}")
        _NP = np
    return _NP


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n"


def read_json(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(raw)
    if raw != canonical_bytes(value):
        raise RuntimeError(f"noncanonical JSON: {path}")
    return value


def file_record(path: Path, relative: bool = False) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "path": path.name if relative else str(path.resolve()), "sha256": sha256_file(path)}


def rename_no_overwrite(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"refusing overwrite: {destination}")
    last: OSError | None = None
    for attempt in range(5):
        try:
            os.rename(source, destination)
            return
        except OSError as error:
            last = error
            if destination.exists() or attempt == 4 or (os.name == "nt" and getattr(error, "winerror", None) not in {5, 32, 33}):
                raise
            time.sleep(0.1)
    if last:
        raise last


def write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".h10a-{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        rename_no_overwrite(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def write_json(path: Path, value: Any) -> None:
    write_exclusive(path, canonical_bytes(value))


def install_async_hooks(path: Path) -> None:
    global _ASYNC_LEDGER
    if not path.is_file() or path.stat().st_size != 0:
        raise RuntimeError("async-error ledger must pre-exist and be empty")
    _ASYNC_LEDGER = path
    def record(kind: str, typ: Any, value: Any, tb: Any) -> None:
        row = {"exception": str(value), "exception_type": getattr(typ, "__name__", str(typ)), "kind": kind, "traceback": "".join(traceback.format_exception(typ, value, tb))}
        _ASYNC_FAILURES.append(row)
        with path.open("ab", buffering=0) as handle:
            handle.write(canonical_bytes(row)); os.fsync(handle.fileno())
    def thread_hook(args: Any) -> None:
        record("threading.excepthook", args.exc_type, args.exc_value, args.exc_traceback)
    def unraisable_hook(args: Any) -> None:
        record("sys.unraisablehook", args.exc_type, args.exc_value, args.exc_traceback)
    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def verify_environment() -> None:
    if sys.version_info[:3] != PYTHON_VERSION:
        raise RuntimeError(f"CPython mismatch: {sys.version_info[:3]}")
    if threading.current_thread() is not threading.main_thread() or threading.active_count() != 1:
        raise RuntimeError("unexpected live Python thread")
    if any(os.environ.get(name) != "1" for name in THREAD_ENV):
        raise RuntimeError("numerical thread bounds are not one")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1" or os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("CUDA/hash-seed environment mismatch")


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name != "nt":
        try: os.kill(pid, 0); return True
        except ProcessLookupError: return False
        except PermissionError: return True
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
    handle = open_process(0x1000, False, pid)
    if handle:
        ctypes.set_last_error(0)
        if not close_handle(handle):
            raise ctypes.WinError(ctypes.get_last_error())
        return True
    return ctypes.get_last_error() == 5


def bound_path(auth: Mapping[str, Any], name: str) -> Path:
    value = auth.get(name)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"missing authorized path {name}")
    return Path(value).resolve()


def assert_outer_lock(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError("outer lock missing")
    if os.name == "nt":
        try: handle = path.open("rb")
        except PermissionError: return
        handle.close(); raise RuntimeError("outer lock is not held share-none")


class InnerLock:
    def __init__(self, auth: Mapping[str, Any]) -> None:
        self.auth = auth
        self.path = bound_path(auth, "inner_lock")
        self.release_path = bound_path(auth, "inner_lock_release_path")
        self.fd: int | None = None
    def acquire(self) -> None:
        owner = {"action": self.auth["action"], "authorization_sha256": sha256_file(bound_path(self.auth, "authorization_path")), "created_unix_ns": time.time_ns(), "launch_id": self.auth["launch_id"], "mode": "h10a-child-inner-lock", "process_pid": os.getpid(), "run_role": self.auth["run_role"], "token_sha256": self.auth["token_sha256"]}
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError as error:
            raise RuntimeError("H10A inner lock already exists; launcher must retire stale locks") from error
        os.write(self.fd, canonical_bytes(owner)); os.fsync(self.fd)
    def release(self) -> dict[str, Any]:
        if self.fd is None:
            raise RuntimeError("inner lock not held")
        os.close(self.fd); self.fd = None
        rename_no_overwrite(self.path, self.release_path)
        return file_record(self.release_path)


def verify_binding(auth: Mapping[str, Any], path_name: str, hash_name: str) -> dict[str, Any]:
    path = bound_path(auth, path_name)
    if not path.is_file():
        raise RuntimeError(f"bound file missing: {path_name}")
    record = file_record(path)
    if record["sha256"] != auth.get(hash_name):
        raise RuntimeError(f"bound file hash mismatch: {path_name}")
    return record


def bootstrap(args: argparse.Namespace) -> dict[str, Any]:
    global _INNER_LOCK, _NUMPY_TREE_MANIFEST_SHA256, _NUMPY_TREE_VALIDATION_PASSED
    authorization_path = Path(args.authorization).resolve()
    auth = read_json(authorization_path)
    if not isinstance(auth, dict):
        raise RuntimeError("authorization is not an object")
    verify_environment()
    action = str(args.command)
    pairs = {
        "probe": {("probe", "h10a_pcg_probe")},
        "self-test": {("selftest_primary", "h10a_selftest_primary"), ("selftest_replay", "h10a_selftest_replay")},
        "run": {("primary", "h10a_run_001"), ("exact_replay", "h10a_run_001_replay")},
    }
    pair = (str(auth.get("run_role", "")), str(auth.get("output_id", "")))
    token_hash = sha256_bytes(args.token.encode())
    runner_hash = sha256_file(SCRIPT)
    subject_path = Path(str(auth.get("subject_path", auth.get("runner_path", "")))).resolve()
    subject_hash = auth.get("subject_sha256", auth.get("runner_sha256"))
    if (auth.get("schema_version") != "h10a_launcher_authorization.v1" or auth.get("subject_kind") != "runner" or action not in pairs or pair not in pairs[action] or auth.get("action") != action or auth.get("token") != args.token or auth.get("token_sha256") != token_hash or subject_path != SCRIPT or subject_hash != runner_hash or bound_path(auth, "authorization_path") != authorization_path or auth.get("protocol_sha256") != PROTOCOL_SHA256 or bound_path(auth, "protocol_path") != PROTOCOL or auth.get("label_free_only") is not True or auth.get("candidate_labels_forbidden") is not True or auth.get("candidate_suffix_labels_forbidden") is not True or auth.get("behaviors_tsv_forbidden") is not True):
        raise RuntimeError("authorization identity mismatch")
    if auth.get("probe_mode") is not (action == "probe"):
        raise RuntimeError("probe-mode authorization mismatch")
    if action == "self-test" and auth.get("synthetic_mode", auth.get("self_test_only")) is not True:
        raise RuntimeError("self-test is not synthetic-only")
    if action == "run" and auth.get("synthetic_mode") not in {False, None}:
        raise RuntimeError("real run marked synthetic")
    if action != "run" and (auth.get("immutable_input_sha256") != {} or auth.get("immutable_input_paths") != {} or auth.get("phase_a_commit") is not None):
        raise RuntimeError("non-real role bound a real input")
    if action == "run" and auth.get("phase_a_commit") != "b1f247abf3185a2eaec8588b358c488af8f78342":
        raise RuntimeError("Phase-A commit authorization mismatch")
    if action == "self-test" and (Path(str(auth.get("synthetic_fixture_manifest", ""))).resolve() != FIXTURE_MANIFEST or auth.get("forced_full_path") is not True):
        raise RuntimeError("synthetic fixture/full-path authorization mismatch")
    if action == "run" and auth.get("forced_full_path") is not False:
        raise RuntimeError("real role cannot force downstream stages")
    start_path, ack_path = Path(args.process_start).resolve(), Path(args.process_ack).resolve()
    if start_path != bound_path(auth, "process_start_path") or ack_path != bound_path(auth, "process_ack_path") or start_path.parent != authorization_path.parent or ack_path.parent != authorization_path.parent:
        raise RuntimeError("PID handshake containment mismatch")
    ledger = bound_path(auth, "async_error_ledger")
    if ledger.parent != authorization_path.parent:
        raise RuntimeError("async ledger escaped launch directory")
    output = bound_path(auth, "output_directory")
    if output.name != pair[1] or output.exists() or H10_DIR not in output.parents:
        raise RuntimeError("authorized output is not a fresh H10A output directory")
    if bound_path(auth, "inner_lock").parent != H10_DIR or bound_path(auth, "inner_lock_release_path").parent != authorization_path.parent:
        raise RuntimeError("inner-lock path containment mismatch")
    install_async_hooks(ledger)
    launcher_pid = int(auth.get("launcher_pid", -1))
    if not process_alive(launcher_pid):
        raise RuntimeError("launcher PID is not alive")
    outer = bound_path(auth, "outer_lock"); assert_outer_lock(outer)
    records = auth.get("runtime_files"); hashes = auth.get("runtime_hashes")
    if not isinstance(records, dict) or set(records) != {"runner", "verifier", "launcher", "protocol", "active_lock", "base_interpreter", "venv_launcher", "venv_config", "synthetic_generator", "synthetic_fixture_manifest", "numpy_package_manifest"} or not isinstance(hashes, dict): raise RuntimeError("runtime map schema mismatch")
    base_hash_keys = {"runner_sha256", "launcher_sha256", "protocol_sha256", "active_lock_sha256", "base_interpreter_sha256", "venv_launcher_sha256", "venv_config_sha256"}
    main_hash_keys = base_hash_keys | {"verifier_sha256", "synthetic_generator_sha256", "synthetic_fixture_manifest_sha256", "numpy_manifest_sha256", "probe_completion_sha256", "expected_pcg_probe_sha256"}
    if set(hashes) != (base_hash_keys if action == "probe" else main_hash_keys): raise RuntimeError("runtime hash-key inventory mismatch")
    runtime: dict[str, Any] = {}
    for name, record in records.items():
        if record is None: continue
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}: raise RuntimeError(f"runtime record malformed: {name}")
        path = Path(str(record["path"])).resolve()
        if not path.is_file() or file_record(path) != {"path": str(path), "sha256": record["sha256"], "bytes": record["bytes"]}: raise RuntimeError(f"runtime binding mismatch: {name}")
        runtime[name] = dict(record)
    hash_fields = {"runner": "runner_sha256", "launcher": "launcher_sha256", "protocol": "protocol_sha256", "active_lock": "active_lock_sha256", "base_interpreter": "base_interpreter_sha256", "venv_launcher": "venv_launcher_sha256", "venv_config": "venv_config_sha256", "verifier": "verifier_sha256", "synthetic_generator": "synthetic_generator_sha256", "synthetic_fixture_manifest": "synthetic_fixture_manifest_sha256", "numpy_package_manifest": "numpy_manifest_sha256"}
    for name, field in hash_fields.items():
        if records[name] is not None and records[name]["sha256"] != hashes.get(field): raise RuntimeError(f"runtime hash map mismatch: {name}")
    if Path(runtime["runner"]["path"]).resolve() != SCRIPT or runtime["runner"]["sha256"] != runner_hash or Path(runtime["protocol"]["path"]).resolve() != PROTOCOL or runtime["protocol"]["sha256"] != PROTOCOL_SHA256: raise RuntimeError("runner/protocol runtime mismatch")
    if action == "probe" and any(records[name] is not None for name in ("verifier", "synthetic_generator", "synthetic_fixture_manifest", "numpy_package_manifest")): raise RuntimeError("probe bound forbidden main implementation files")
    if action != "probe" and any(records[name] is None for name in ("verifier", "synthetic_generator", "synthetic_fixture_manifest", "numpy_package_manifest")): raise RuntimeError("main runtime binding incomplete")
    if action != "probe" and (hashes.get("expected_pcg_probe_sha256") != auth.get("expected_pcg_probe_sha256") or records["numpy_package_manifest"]["sha256"] != auth.get("numpy_manifest_sha256")): raise RuntimeError("PCG/NumPy manifest main binding mismatch")
    if action != "probe" and (not PROBE_COMPLETION.is_file() or sha256_file(PROBE_COMPLETION) != hashes.get("probe_completion_sha256")): raise RuntimeError("probe-completion provenance mismatch")
    if Path(sys.executable).resolve() != Path(runtime["venv_launcher"]["path"]).resolve() or Path(str(getattr(sys, "_base_executable", ""))).resolve() != Path(runtime["base_interpreter"]["path"]).resolve():
        raise RuntimeError("interpreter identity mismatch")
    if action == "run":
        verify_real_inputs(auth)
    if action != "probe":
        imported_tree, imported_record = numpy_manifest()
        pinned_path = Path(str(records["numpy_package_manifest"]["path"])).resolve()
        pinned_bytes = pinned_path.read_bytes()
        if imported_tree != pinned_bytes or imported_record["sha256"] != records["numpy_package_manifest"]["sha256"] or imported_record["bytes"] != records["numpy_package_manifest"]["bytes"]:
            raise RuntimeError("imported NumPy package tree differs from the pinned canonical manifest")
        _NUMPY_TREE_MANIFEST_SHA256 = str(imported_record["sha256"])
        _NUMPY_TREE_VALIDATION_PASSED = True
        verify_environment()
    authorization_hash = sha256_file(authorization_path)
    _INNER_LOCK = InnerLock(auth); _INNER_LOCK.acquire()
    start = {"action": action, "authorization_sha256": authorization_hash, "environment": {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "main_thread_only": True, "numpy_tree_manifest_sha256": _NUMPY_TREE_MANIFEST_SHA256, "numpy_tree_validation_passed": _NUMPY_TREE_VALIDATION_PASSED if action != "probe" else None, "numpy_version": NUMPY_VERSION, "pcg_probe_sha256": None if action == "probe" else auth.get("expected_pcg_probe_sha256"), "python_hash_seed": os.environ.get("PYTHONHASHSEED"), "python_version": ".".join(str(value) for value in PYTHON_VERSION), "runtime_files": records, "sys_base_executable": str(Path(str(getattr(sys, "_base_executable", ""))).resolve()), "sys_base_prefix": str(Path(sys.base_prefix).resolve()), "sys_executable": str(Path(sys.executable).resolve()), "sys_prefix": str(Path(sys.prefix).resolve()), "thread_bounds": {name: os.environ.get(name) for name in THREAD_ENV}}, "launch_id": auth["launch_id"], "launcher_pid": launcher_pid, "mode": "h10a-child-process-start", "output_id": pair[1], "process_pid": os.getpid(), "run_role": pair[0], "subject_kind": "runner", "subject_path": str(SCRIPT), "subject_sha256": runner_hash, "token_sha256": token_hash}
    write_json(start_path, start)
    deadline = time.monotonic() + 30.0
    while not ack_path.is_file():
        if time.monotonic() >= deadline: raise RuntimeError("launcher acknowledgement timeout")
        time.sleep(0.05)
    ack = read_json(ack_path)
    if (ack.get("mode") != "h10a-child-process-acknowledgement" or ack.get("action") != action or ack.get("run_role") != pair[0] or ack.get("launch_id") != auth.get("launch_id") or int(ack.get("launcher_pid", -1)) != launcher_pid or int(ack.get("process_pid", -1)) != os.getpid() or ack.get("authorization_sha256") != authorization_hash or ack.get("token_sha256") != token_hash or ack.get("subject_sha256", runner_hash) != runner_hash):
        raise RuntimeError("launcher acknowledgement mismatch")
    if not process_alive(launcher_pid): raise RuntimeError("launcher exited during acknowledgement")
    assert_outer_lock(outer); verify_environment()
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
    def m(self) -> int: return len(self.rows)


@dataclass(frozen=True)
class ViewGraph:
    name: str
    relations: tuple[str, ...]
    alpha: Mapping[str, Any]
    graphs: Mapping[tuple[str, str], RelationGraph]


@dataclass(frozen=True)
class Cohort:
    X: Any
    Y: Any
    candidate_pattern: Any
    nz_occurrence: Any
    nz_impression: Any
    nz_anchor: Any
    nz_value: Any
    offsets: Any
    impression_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    tie_hashes: tuple[bytes, ...]
    counts: Mapping[str, int]


def graph_from_edges(relation: str, edges: Iterable[tuple[int, int]], n_columns: int | None = None) -> RelationGraph:
    values = tuple(sorted(edges))
    if len(values) != len(set(values)):
        raise RuntimeError("duplicate graph")
    if n_columns is None: n_columns = 1 + max(column for _, column in values)
    row_degrees = [0] * ANCHORS; column_degrees = [0] * n_columns
    for row, column in values:
        if not 0 <= row < ANCHORS or column < 0: raise RuntimeError("invalid edge")
        row_degrees[row] += 1; column_degrees[column] += 1
    return RelationGraph(relation, n_columns, tuple(row for row, _ in values), tuple(column for _, column in values), tuple(row_degrees), tuple(column_degrees))


def eligible(graph_h: RelationGraph, graph_c: RelationGraph) -> bool:
    return graph_h.m > 0 and graph_c.m > 0 and graph_h.n_columns == graph_c.n_columns and all(sum(value > 0 for value in graph.row_degrees) >= 2 and sum(value > 0 for value in graph.column_degrees) >= 2 for graph in (graph_h, graph_c))


def verify_real_inputs(auth: Mapping[str, Any]) -> None:
    if auth.get("immutable_input_sha256") != EXPECTED_INPUT_HASHES:
        raise RuntimeError("authorized immutable hash map mismatch")
    authorized = auth.get("immutable_input_paths")
    if not isinstance(authorized, dict) or set(authorized) != set(INPUTS):
        raise RuntimeError("authorized immutable input surface mismatch")
    for name, path in INPUTS.items():
        if Path(str(authorized[name])).resolve() != path.resolve() or not path.is_file() or sha256_file(path) != EXPECTED_INPUT_HASHES[name]:
            raise RuntimeError(f"immutable input mismatch: {name}")
    if INPUTS["phase_a_manifest"].stat().st_size != EXPECTED_MANIFEST_BYTES:
        raise RuntimeError("manifest size mismatch")


def load_contract() -> tuple[str, ...]:
    result, completion = read_json(INPUTS["phase_a_result"]), read_json(INPUTS["phase_a_completion"])
    cohort = result.get("cohort", {})
    anchors = cohort.get("sampled_qids")
    if (result.get("schema_version") != "h6_phase_a_coverage.python.v1" or result.get("phase_a_commit", "b1f247abf3185a2eaec8588b358c488af8f78342") != "b1f247abf3185a2eaec8588b358c488af8f78342" or cohort.get("manifest_sha256") != EXPECTED_INPUT_HASHES["phase_a_manifest"] or cohort.get("eligible_impressions") != 64_443 or cohort.get("distinct_users") != 43_374 or cohort.get("candidates") != 2_422_258 or cohort.get("known_news") != 42_416 or cohort.get("news_with_sampled_anchor") != 12_060 or float(result.get("confidence_threshold", result.get("minimum_confidence", 0.90))) != 0.90):
        raise RuntimeError("Phase-A contract mismatch")
    if not isinstance(anchors, list) or len(anchors) != ANCHORS or len(set(anchors)) != ANCHORS or any(not isinstance(q, str) or QID_RE.fullmatch(q) is None for q in anchors):
        raise RuntimeError("anchor list mismatch")
    outputs = completion.get("outputs", {})
    if completion.get("status") != "H6_COVERAGE_RUN_002_COMPLETE" or completion.get("completion_marker_is_last") is not True or outputs.get("primary_result", {}).get("sha256") != EXPECTED_INPUT_HASHES["phase_a_result"] or outputs.get("primary_manifest", {}).get("sha256") != EXPECTED_INPUT_HASHES["phase_a_manifest"]:
        raise RuntimeError("Phase-A completion mismatch")
    return tuple(anchors)


def load_relation_vocabulary() -> frozenset[str]:
    values: set[str] = set()
    with INPUTS["relations"].open("r", encoding="utf-8", newline="") as handle:
        for raw in handle:
            relation = raw.split("\t", 1)[0]
            if PROPERTY_RE.fullmatch(relation) is None or relation in values: raise RuntimeError("bad relation vocabulary")
            values.add(relation)
    if len(values) != EXPECTED_RELATIONS: raise RuntimeError("relation vocabulary count mismatch")
    return frozenset(values)


def load_facts(anchors: Sequence[str]) -> dict[str, dict[str, frozenset[str]]]:
    rows: dict[str, dict[str, frozenset[str]]] = {}
    with INPUTS["facts"].open("r", encoding="utf-8", newline="") as handle:
        for raw in handle:
            if not raw.strip(): continue
            value = json.loads(raw); qid = value.get("qid")
            if not isinstance(qid, str) or QID_RE.fullmatch(qid) is None or qid in rows or value.get("api_ok") is not True: raise RuntimeError("fact row identity mismatch")
            endpoints: dict[str, frozenset[str]] = {}
            for source in ("historical", "current"):
                facts = value.get(source, {}).get("facts")
                if not isinstance(facts, list): raise RuntimeError("fact endpoint malformed")
                if any(not isinstance(fact, str) for fact in facts): raise RuntimeError("non-string fact signature")
                endpoints[source] = frozenset(fact for fact in facts if FACT_RE.fullmatch(fact))
            rows[qid] = endpoints
    if set(rows) != set(anchors): raise RuntimeError("fact anchors mismatch")
    return rows


def parse_news(anchors: Sequence[str]) -> tuple[dict[str, int], tuple[tuple[int, ...], ...], Any]:
    np = np_module(); anchor_index = {qid: i for i, qid in enumerate(anchors)}
    mapping: dict[str, tuple[int, ...]] = {}; supported = 0
    with INPUTS["news"].open("r", encoding="utf-8", newline="") as handle:
        for raw in handle:
            fields = raw.rstrip("\r\n").split("\t", 7)
            if len(fields) != 8 or NEWS_RE.fullmatch(fields[0]) is None or fields[0] in mapping: raise RuntimeError("news row malformed")
            retained: set[int] = set()
            for column in (6, 7):
                values = json.loads(fields[column])
                if not isinstance(values, list): raise RuntimeError("news annotations malformed")
                for item in values:
                    if not isinstance(item, dict): continue
                    qid = str(item.get("WikidataId", "")).strip()
                    try: confidence = float(item.get("Confidence"))
                    except (TypeError, ValueError): continue
                    if qid in anchor_index and math.isfinite(confidence) and confidence >= 0.90: retained.add(anchor_index[qid])
            pattern = tuple(sorted(retained)); mapping[fields[0]] = pattern; supported += int(bool(pattern))
    patterns = tuple(sorted(set(mapping.values())))
    if len(mapping) != 42_416 or supported != 12_060 or len(patterns) != 812 or patterns[0] != (): raise RuntimeError("news counts mismatch")
    ids = {pattern: i for i, pattern in enumerate(patterns)}
    matrix = np.zeros((len(patterns), ANCHORS), dtype=np.float64)
    for i, pattern in enumerate(patterns):
        if pattern: matrix[i, np.asarray(pattern, dtype=np.intp)] = np.divide(np.float64(1), np.sqrt(np.float64(len(pattern))))
    return {news: ids[pattern] for news, pattern in mapping.items()}, patterns, matrix


@dataclass(frozen=True)
class AuditRow:
    key: bytes
    impression_id: str
    history: tuple[str, ...]
    candidates: tuple[str, ...]


def load_real_cohort(news_to_pattern: Mapping[str, int], patterns: Sequence[tuple[int, ...]], Y: Any) -> Cohort:
    users: set[str] = set(); eligible_rows: list[AuditRow] = []
    impressions = occurrences = supported_occurrences = gt10 = gt10support = ge2 = 0
    with INPUTS["phase_a_manifest"].open("rb") as handle:
        for row_index, raw in enumerate(handle):
            if not raw.endswith(b"\n") or raw.endswith(b"\r\n") or MANIFEST_LABEL_RE.search(raw): raise RuntimeError("manifest label/line violation")
            value = json.loads(raw)
            if not isinstance(value, dict) or list(value) != ["i", "u", "h", "c"] or json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() + b"\n" != raw: raise RuntimeError(f"manifest schema mismatch {row_index}")
            impression, user, history, candidates = value["i"], value["u"], value["h"], value["c"]
            if not isinstance(impression, str) or not isinstance(user, str) or not isinstance(history, list) or not history or len(history) > 50 or any(news not in news_to_pattern for news in history): raise RuntimeError("manifest identity/history mismatch")
            ids = [item.get("n") if isinstance(item, dict) and list(item) == ["n", "v"] else None for item in candidates] if isinstance(candidates, list) else []
            if not ids or any(not isinstance(news, str) or news not in news_to_pattern for news in ids) or len(ids) != len(set(ids)): raise RuntimeError("manifest candidates mismatch")
            supported = sum(bool(patterns[news_to_pattern[news]]) for news in ids)
            if not any(bool(patterns[news_to_pattern[news]]) for news in history): raise RuntimeError("unsupported history")
            users.add(user); impressions += 1; occurrences += len(ids); supported_occurrences += supported
            gt10 += int(len(ids) > 10); gt10support += int(len(ids) > 10 and supported > 10); ge2 += int(supported >= 2)
            if len(ids) > 10 and supported > 10: eligible_rows.append(AuditRow(hashlib.sha256(AUDIT_PREFIX + impression.encode()).digest(), impression, tuple(history), tuple(ids)))
    counts = {"news_rows": len(news_to_pattern), "supported_news": sum(bool(patterns[i]) for i in news_to_pattern.values()), "patterns": len(patterns), "impressions": impressions, "users": len(users), "candidate_occurrences": occurrences, "supported_candidate_occurrences": supported_occurrences, "gt10_candidates": gt10, "gt10_candidates_and_support": gt10support, "ge2_supported_candidates": ge2, "histories_with_support": impressions, "audit_impressions": AUDIT_SIZE}
    if counts != EXPECTED_COUNTS or len(eligible_rows) != 17_436: raise RuntimeError(f"cohort count mismatch: {counts}")
    eligible_rows.sort(key=lambda row: (row.key, row.impression_id))
    return build_cohort(eligible_rows[:AUDIT_SIZE], news_to_pattern, patterns, Y, counts)


def build_cohort(rows: Sequence[AuditRow], news_to_pattern: Mapping[str, int], patterns: Sequence[tuple[int, ...]], Y: Any, counts: Mapping[str, int]) -> Cohort:
    np = np_module(); X = np.zeros((len(rows), ANCHORS), dtype=np.float64)
    candidate_patterns: list[int] = []; candidate_ids: list[str] = []; offsets = [0]
    nz_o: list[int] = []; nz_i: list[int] = []; nz_a: list[int] = []; nz_v: list[Any] = []; ties: list[bytes] = []
    for i, row in enumerate(rows):
        history_sum = np.zeros(ANCHORS, dtype=np.float64)
        for news in row.history: np.add(history_sum, Y[news_to_pattern[news]], out=history_sum)
        norm = np.sqrt(np.add.reduce(np.multiply(history_sum, history_sum), dtype=np.float64))
        if not np.isfinite(norm) or norm <= 0: raise RuntimeError("history normalization failed")
        X[i] = np.divide(history_sum, norm)
        for news in row.candidates:
            occurrence = len(candidate_ids); pattern = int(news_to_pattern[news])
            candidate_ids.append(news); candidate_patterns.append(pattern)
            ties.append(hashlib.sha256(RANK_PREFIX + row.impression_id.encode() + b"|" + news.encode()).digest())
            for anchor in patterns[pattern]: nz_o.append(occurrence); nz_i.append(i); nz_a.append(anchor); nz_v.append(Y[pattern, anchor])
        offsets.append(len(candidate_ids))
    offsets_array = np.ascontiguousarray(offsets, dtype=np.intp)
    return Cohort(np.ascontiguousarray(X), np.ascontiguousarray(Y), np.ascontiguousarray(candidate_patterns, dtype=np.intp), np.ascontiguousarray(nz_o, dtype=np.intp), np.ascontiguousarray(nz_i, dtype=np.intp), np.ascontiguousarray(nz_a, dtype=np.intp), np.ascontiguousarray(nz_v, dtype=np.float64), offsets_array, tuple(row.impression_id for row in rows), tuple(candidate_ids), tuple(ties), dict(counts))


def compile_view(anchors: Sequence[str], facts: Mapping[str, Mapping[str, frozenset[str]]], relations: frozenset[str], view: str) -> ViewGraph:
    np = np_module(); collected: dict[str, dict[str, set[tuple[int, str]]]] = {}
    for row, qid in enumerate(anchors):
        for endpoint, source in (("H", "historical"), ("C", "current")):
            for fact in facts[qid][source]:
                relation, target = FACT_RE.fullmatch(fact).groups()  # type: ignore[union-attr]
                if relation not in relations or (view == "metadata_blocklist" and relation in METADATA_BLOCKLIST) or (view == "hub_removal" and qid in HUB_QIDS): continue
                collected.setdefault(relation, {"H": set(), "C": set()})[endpoint].add((row, target))
    graphs: dict[tuple[str, str], RelationGraph] = {}; kept: list[str] = []; c_values: dict[str, int] = {}
    for relation in sorted(collected):
        targets = sorted({target for endpoint in ENDPOINT_ORDER for _, target in collected[relation][endpoint]}); index = {target: i for i, target in enumerate(targets)}
        pair = {endpoint: graph_from_edges(relation, ((row, index[target]) for row, target in collected[relation][endpoint]), len(targets)) for endpoint in ENDPOINT_ORDER}
        if eligible(pair["H"], pair["C"]):
            kept.append(relation); c_values[relation] = min(pair["H"].m, pair["C"].m)
            for endpoint in ENDPOINT_ORDER: graphs[(relation, endpoint)] = pair[endpoint]
    total = sum(c_values.values())
    if total <= 0: return ViewGraph(view, (), {}, {})
    alpha = {relation: np.divide(np.float64(c_values[relation]), np.float64(total)) for relation in kept}
    compiled = ViewGraph(view, tuple(kept), alpha, graphs); assert_view_budget(compiled)
    return compiled


def assert_view_budget(view: ViewGraph) -> None:
    expected = VIEW_BUDGETS[view.name]
    observed = {"relations": len(view.relations), "H": sum(view.graphs[(r, "H")].m for r in view.relations), "C": sum(view.graphs[(r, "C")].m for r in view.relations)}
    if any(observed[key] != expected[key] for key in observed): raise RuntimeError(f"view budget mismatch {view.name}: {observed}")


def synthetic_fixture() -> tuple[Cohort, dict[str, ViewGraph]]:
    import generate_h10a_synthetic_fixture as fixture
    np = np_module()
    fixture.assert_manifest_counts()
    if read_json(FIXTURE_MANIFEST) != fixture.manifest_object(): raise RuntimeError("synthetic fixture manifest mismatch")
    Y = np.zeros((812, ANCHORS), dtype=np.float64); patterns = tuple(fixture.pattern_anchors(i) for i in range(812))
    for i, anchors in enumerate(patterns):
        if anchors: Y[i, np.asarray(anchors, dtype=np.intp)] = np.divide(np.float64(1), np.sqrt(np.float64(len(anchors))))
    X = np.zeros((AUDIT_SIZE, ANCHORS), dtype=np.float64)
    candidate_patterns: list[int] = []; candidate_ids: list[str] = []; offsets = [0]; ties: list[bytes] = []
    nz_o: list[int] = []; nz_i: list[int] = []; nz_a: list[int] = []; nz_v: list[Any] = []
    impressions = tuple(f"SI{i:05d}" for i in range(AUDIT_SIZE))
    for i in range(AUDIT_SIZE): X[i, np.asarray(fixture.user_anchors(i), dtype=np.intp)] = np.float64(0.5)
    next_boundary = fixture.candidate_count(0); boundary_impression = 0
    for occurrence, impression, pattern, news in fixture.iter_candidate_patterns():
        candidate_patterns.append(pattern); candidate_ids.append(news); ties.append(hashlib.sha256(RANK_PREFIX + impressions[impression].encode() + b"|" + news.encode()).digest())
        for anchor in patterns[pattern]: nz_o.append(occurrence); nz_i.append(impression); nz_a.append(anchor); nz_v.append(Y[pattern, anchor])
        if occurrence + 1 == next_boundary:
            offsets.append(occurrence + 1); boundary_impression += 1
            if boundary_impression < AUDIT_SIZE: next_boundary += fixture.candidate_count(boundary_impression)
    counts = {"audit_impressions": 8192, "candidate_anchor_nonzeros": len(nz_a), "candidate_occurrences": len(candidate_ids), "patterns": 812, "supported_candidate_occurrences": sum(p != 0 for p in candidate_patterns), "user_anchor_nonzeros": int(np.count_nonzero(X))}
    expected_counts = {"audit_impressions": 8192, "candidate_anchor_nonzeros": 1_354_440, "candidate_occurrences": 290_648, "patterns": 812, "supported_candidate_occurrences": 290_290, "user_anchor_nonzeros": 32_768}
    if counts != expected_counts or len(offsets) != 8193: raise RuntimeError(f"synthetic cohort mismatch {counts}")
    offsets_array = np.ascontiguousarray(offsets, dtype=np.intp)
    cohort = Cohort(np.ascontiguousarray(X), np.ascontiguousarray(Y), np.ascontiguousarray(candidate_patterns, dtype=np.intp), np.ascontiguousarray(nz_o, dtype=np.intp), np.ascontiguousarray(nz_i, dtype=np.intp), np.ascontiguousarray(nz_a, dtype=np.intp), np.ascontiguousarray(nz_v, dtype=np.float64), offsets_array, impressions, tuple(candidate_ids), tuple(ties), counts)
    views: dict[str, ViewGraph] = {}
    for view in VIEW_ORDER:
        relations = tuple(fixture.relation_id(i) for i in range(fixture.VIEW_BUDGETS[view]["relations"])); graphs = {}
        for i, relation in enumerate(relations):
            for endpoint in ENDPOINT_ORDER: graphs[(relation, endpoint)] = graph_from_edges(relation, fixture.relation_edges(view, endpoint, i))
        c = {relation: min(graphs[(relation, "H")].m, graphs[(relation, "C")].m) for relation in relations}; total = sum(c.values())
        compiled = ViewGraph(view, relations, {r: np.divide(np.float64(c[r]), np.float64(total)) for r in relations}, graphs); assert_view_budget(compiled); views[view] = compiled
    return cohort, views


def canonical_operator(view: ViewGraph, endpoint: str, columns: Mapping[str, Any] | None = None, frozen_g: Any | None = None) -> tuple[Any, Any, Any, float]:
    np = np_module(); a_values: list[int] = []; b_values: list[int] = []; alpha_values: list[Any] = []; invd_a_values: list[Any] = []; invd_b_values: list[Any] = []; inve_values: list[Any] = []
    G = np.zeros((ANCHORS, ANCHORS), dtype=np.float64) if frozen_g is None else frozen_g
    for relation in view.relations:
        graph = view.graphs[(relation, endpoint)]; state_columns = graph.columns if columns is None else columns[relation]
        if len(state_columns) != graph.m: raise RuntimeError("state edge count changed")
        d = np.ascontiguousarray(graph.row_degrees, dtype=np.float64); e = np.ascontiguousarray(graph.column_degrees, dtype=np.float64)
        invd = np.zeros(ANCHORS, dtype=np.float64); inve = np.zeros(graph.n_columns, dtype=np.float64); u = np.zeros(ANCHORS, dtype=np.float64)
        positive_d, positive_e = d > 0, e > 0
        np.divide(np.float64(1), np.sqrt(d), out=invd, where=positive_d); np.divide(np.float64(1), e, out=inve, where=positive_e)
        if frozen_g is None:
            np.divide(d, np.float64(graph.m), out=u, where=positive_d)
            np.sqrt(u, out=u, where=positive_d)
        incident: list[list[int]] = [[] for _ in range(graph.n_columns)]
        for row, column in zip(graph.rows, state_columns, strict=True): incident[int(column)].append(row)
        alpha = np.float64(view.alpha[relation])
        for column, rows in enumerate(incident):
            rows.sort()
            for left_index, left in enumerate(rows):
                for right in rows[left_index:]:
                    a_values.append(left); b_values.append(right); alpha_values.append(alpha); invd_a_values.append(invd[left]); invd_b_values.append(invd[right]); inve_values.append(inve[column])
        if frozen_g is None: np.add(G, np.multiply(alpha, np.outer(u, u)), out=G)
    a_idx = np.ascontiguousarray(a_values, dtype=np.intp); b_idx = np.ascontiguousarray(b_values, dtype=np.intp)
    indices = np.ascontiguousarray(np.add(np.multiply(a_idx, np.intp(ANCHORS)), b_idx), dtype=np.intp)
    weights = np.ascontiguousarray(alpha_values, dtype=np.float64)
    np.multiply(weights, np.ascontiguousarray(invd_a_values, dtype=np.float64), out=weights)
    np.multiply(weights, np.ascontiguousarray(invd_b_values, dtype=np.float64), out=weights)
    np.multiply(weights, np.ascontiguousarray(inve_values, dtype=np.float64), out=weights)
    if len(indices) and (int(np.min(indices)) < 0 or int(np.max(indices)) >= ANCHORS * ANCHORS): raise RuntimeError("canonical bin index outside range")
    bins = np.bincount(indices, weights=weights, minlength=ANCHORS * ANCHORS)
    Q = np.ascontiguousarray(bins.reshape((ANCHORS, ANCHORS)), dtype=np.float64)
    upper_rows, upper_columns = np.triu_indices(ANCHORS, k=1); Q[upper_columns, upper_rows] = Q[upper_rows, upper_columns]
    K = np.subtract(Q, G); E = float(np.trace(K, dtype=np.float64))
    if not np.all(np.isfinite(K)) or not np.all(np.isfinite(G)) or not math.isfinite(E): raise RuntimeError("nonfinite operator")
    return K, G, Q, E


def outer_operator(view: ViewGraph, endpoint: str, columns: Mapping[str, Any] | None = None) -> tuple[Any, Any, Any, float]:
    np = np_module(); Q = np.zeros((ANCHORS, ANCHORS), dtype=np.float64); G = np.zeros_like(Q); scalar = np.float64(0)
    for relation in view.relations:
        graph = view.graphs[(relation, endpoint)]; state = graph.columns if columns is None else columns[relation]
        d = np.asarray(graph.row_degrees, dtype=np.float64); e = np.asarray(graph.column_degrees, dtype=np.float64); incident: list[list[int]] = [[] for _ in range(graph.n_columns)]
        for row, column in zip(graph.rows, state, strict=True): incident[int(column)].append(row)
        local_q = np.zeros_like(Q)
        for column, rows in enumerate(incident):
            if not rows: continue
            vector = np.zeros(ANCHORS, dtype=np.float64)
            for row in rows: vector[row] = np.divide(np.float64(1), np.sqrt(np.multiply(d[row], e[column])))
            np.add(local_q, np.outer(vector, vector), out=local_q)
        u = np.sqrt(np.divide(d, np.float64(graph.m), out=np.zeros_like(d), where=d > 0)); alpha = np.float64(view.alpha[relation])
        np.add(Q, np.multiply(alpha, local_q), out=Q); np.add(G, np.multiply(alpha, np.outer(u, u)), out=G)
        local = np.float64(-1)
        for row, column in zip(graph.rows, state, strict=True): local = np.add(local, np.divide(np.float64(1), np.multiply(d[row], e[int(column)])))
        scalar = np.add(scalar, np.multiply(alpha, local))
    return np.subtract(Q, G), G, Q, float(scalar)


def score_operator(cohort: Cohort, operator: Any) -> Any:
    np = np_module(); U = np.ascontiguousarray(np.matmul(cohort.X, operator), dtype=np.float64)
    terms = np.multiply(U[cohort.nz_impression, cohort.nz_anchor], cohort.nz_value)
    scores = np.bincount(cohort.nz_occurrence, weights=terms, minlength=len(cohort.candidate_ids))
    return np.ascontiguousarray(scores, dtype=np.float64)


def metric_v(scores: Any, offsets: Any) -> float:
    np = np_module(); counts = np.diff(offsets); sums = np.add.reduceat(scores, offsets[:-1], dtype=np.float64); means = np.divide(sums, counts.astype(np.float64)); centered = np.subtract(scores, np.repeat(means, counts)); squares = np.multiply(centered, centered); within = np.add.reduceat(squares, offsets[:-1], dtype=np.float64); return float(np.mean(np.divide(within, counts.astype(np.float64)), dtype=np.float64))


def ranks(cohort: Cohort, scores: Any) -> Any:
    np = np_module(); result = np.empty(len(scores), dtype=np.int64)
    for start_raw, stop_raw in zip(cohort.offsets[:-1], cohort.offsets[1:], strict=True):
        start, stop = int(start_raw), int(stop_raw); segment = scores[start:stop]; preliminary = np.argsort(np.negative(segment), kind="stable"); group_ids: dict[int, int] = {}; group = -1; first_score = np.float64(0)
        for local_raw in preliminary:
            local = int(local_raw); score = segment[local]
            if group < 0 or np.absolute(np.subtract(score, first_score)) > np.float64(1e-12): group += 1; first_score = score
            group_ids[local] = group
        final = sorted(range(stop - start), key=lambda local: (group_ids[local], cohort.tie_hashes[start + local], cohort.candidate_ids[start + local]))
        for one_based, local in enumerate(final, start=1): result[start + local] = one_based
    return np.ascontiguousarray(result)


def ranking_metrics(cohort: Cohort, z: Any, g: Any, degree_ranks: Any | None = None) -> tuple[float, float, float, int, float, int, float, Any, Any]:
    np = np_module(); rz = ranks(cohort, z); rg = ranks(cohort, g) if degree_ranks is None else degree_ranks; offsets = cohort.offsets; counts = np.diff(offsets)
    delta = np.abs(np.subtract(rz, rg)); footrule = np.add.reduceat(delta, offsets[:-1], dtype=np.int64); counts64 = counts.astype(np.int64); denominator = np.floor_divide(np.multiply(counts64, counts64), 2); D = float(np.mean(np.divide(footrule.astype(np.float64), denominator.astype(np.float64)), dtype=np.float64))
    overlap = np.add.reduceat(np.logical_and(rz <= 10, rg <= 10).astype(np.int64), offsets[:-1], dtype=np.int64); T = float(np.mean(np.divide((10 - overlap).astype(np.float64), np.float64(10)), dtype=np.float64))
    zmean = np.divide(np.add.reduceat(z, offsets[:-1], dtype=np.float64), counts.astype(np.float64)); gmean = np.divide(np.add.reduceat(g, offsets[:-1], dtype=np.float64), counts.astype(np.float64)); zc = np.subtract(z, np.repeat(zmean, counts)); gc = np.subtract(g, np.repeat(gmean, counts)); P = np.float64(len(z)); vz = np.divide(np.add.reduce(np.multiply(zc, zc), dtype=np.float64), P); vg = np.divide(np.add.reduce(np.multiply(gc, gc), dtype=np.float64), P)
    if vz <= np.float64(1e-24) or vg <= np.float64(1e-24): R2 = 1.0
    else:
        covariance = np.divide(np.add.reduce(np.multiply(zc, gc), dtype=np.float64), P); correlation = np.divide(covariance, np.sqrt(np.multiply(vz, vg))); R2 = float(np.multiply(correlation, correlation))
    ranges = np.subtract(np.maximum.reduceat(z, offsets[:-1]), np.minimum.reduceat(z, offsets[:-1])); usable = int(np.count_nonzero(ranges > np.float64(1e-12)))
    return D, T, R2, usable, float(np.divide(np.float64(usable), np.float64(AUDIT_SIZE))), int(np.count_nonzero(z != np.float64(0))), float(np.divide(np.float64(np.count_nonzero(z != np.float64(0))), np.float64(len(z)))), rz, rg


def quantile(values: Sequence[float], index: int) -> float:
    np = np_module(); array = np.ascontiguousarray(values, dtype=np.float64); return float(np.sort(array, kind="stable")[index])


def null_summary(real: float, values: Sequence[float], primary: bool, metric: str) -> dict[str, Any]:
    np = np_module(); combined = np.ascontiguousarray(values, dtype=np.float64); per_chain = (combined[:len(combined)//2], combined[len(combined)//2:])
    if primary: combined_index, chain_index = (98, 49) if metric == "V" else (94, 47)
    else: combined_index, chain_index = 9, 4
    q = float(np.sort(combined, kind="stable")[combined_index]); chain_q = [float(np.sort(value, kind="stable")[chain_index]) for value in per_chain]
    tail = int(np.count_nonzero(np.greater_equal(combined, np.float64(real)))); p_mc = float(np.divide(np.float64(1 + tail), np.float64(len(combined) + 1)))
    return {"chain_quantiles": chain_q, "combined_quantile": q, "p_MC": p_mc, "real": real, "real_minus_chain_quantiles": [real - value for value in chain_q], "real_minus_combined_quantile": real - q, "tail_count": tail}


def direct_score(cohort: Cohort, operator: Any, occurrence_indices: Any, full: bool = False) -> Any:
    np = np_module(); impressions = np.searchsorted(cohort.offsets[1:], occurrence_indices, side="right"); patterns = cohort.candidate_pattern[occurrence_indices]
    if full:
        table = np.matmul(np.matmul(cohort.X, operator), cohort.Y.T); return table[impressions, patterns]
    left = np.matmul(cohort.X[impressions], operator); return np.add.reduce(np.multiply(left, cohort.Y[patterns]), axis=1, dtype=np.float64)


def state_digest(view: str, endpoint: str, relation: str, chain: int, state: int, graph: RelationGraph, columns: Sequence[int]) -> str:
    payload = bytearray(b"H10A_STATE_V1\n" + view.encode("ascii") + b"\n" + endpoint.encode("ascii") + b"\n" + relation.encode("ascii") + b"\n" + str(chain).encode("ascii") + b"\n" + str(state).encode("ascii") + b"\n")
    payload.extend(struct.pack("<HII", ANCHORS, graph.n_columns, graph.m))
    for row, column in zip(graph.rows, columns, strict=True): payload.append(row); payload.extend(struct.pack("<I", int(column)))
    return sha256_bytes(bytes(payload))


def degree_mix(graph: RelationGraph) -> tuple[str, int]:
    table: dict[tuple[int, int], int] = {}
    for row, column in zip(graph.rows, graph.columns, strict=True):
        key = (graph.row_degrees[row], graph.column_degrees[column]); table[key] = table.get(key, 0) + 1
    triples = [(p, q, table[(p, q)]) for p, q in sorted(table)]; payload = bytearray(b"H10A_DEGREE_MIX_V1\n" + struct.pack("<I", len(triples)))
    for triple in triples: payload.extend(struct.pack("<III", *triple))
    return sha256_bytes(bytes(payload)), len(triples)


def structural_diagnostics(graph: RelationGraph) -> tuple[int, int]:
    occupied = {(row, column) for row, column in zip(graph.rows, graph.columns, strict=True)}; valid = changing = 0
    for p in range(graph.m):
        i, j = graph.rows[p], graph.columns[p]
        for q in range(p + 1, graph.m):
            k, ell = graph.rows[q], graph.columns[q]
            if i != k and j != ell and (i, ell) not in occupied and (k, j) not in occupied:
                valid += 1; changing += int(graph.row_degrees[i] != graph.row_degrees[k] and graph.column_degrees[j] != graph.column_degrees[ell])
    return valid, changing


def assert_state(graph: RelationGraph, columns: Sequence[int]) -> None:
    if len(columns) != graph.m or len({(row, int(column)) for row, column in zip(graph.rows, columns, strict=True)}) != graph.m: raise RuntimeError("null state duplicate/edge-count failure")
    column_degrees = [0] * graph.n_columns
    for column in columns:
        if not 0 <= int(column) < graph.n_columns: raise RuntimeError("null column out of bounds")
        column_degrees[int(column)] += 1
    if tuple(column_degrees) != graph.column_degrees: raise RuntimeError("null state column margin failure")


def run_relation_chain(view: str, endpoint: str, graph: RelationGraph, chain: int, retained_states: int, burn_multiple: int, digest_rows: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> tuple[Any, ...]:
    np = np_module(); seed_text = b"20260807|H10A|null|" + view.encode() + b"|" + endpoint.encode() + b"|" + graph.relation_id.encode() + b"|chain=" + str(chain).encode(); seed = int.from_bytes(hashlib.sha256(seed_text).digest()[:8], "big")
    rng = np.random.Generator(np.random.PCG64DXSM(seed)); columns = np.ascontiguousarray(graph.columns, dtype=np.int64); observed = columns.tobytes(); masks = [0] * ANCHORS
    for row, column in zip(graph.rows, columns, strict=True): masks[row] |= 1 << int(column)
    counters = {"proposals": 0, "lazy_stays": 0, "nonlazy_attempts": 0, "invalid_same_row_or_column": 0, "invalid_cross_occupied": 0, "valid_swaps": 0, "accepted_swaps": 0}
    def propose(count: int) -> None:
        for _ in range(count):
            counters["proposals"] += 1; raw = int(rng.bit_generator.random_raw())
            if (raw & 1) == 0: counters["lazy_stays"] += 1; continue
            counters["nonlazy_attempts"] += 1; first = int(rng.integers(0, graph.m, size=None, dtype=np.int64, endpoint=False)); raw_second = int(rng.integers(0, graph.m - 1, size=None, dtype=np.int64, endpoint=False)); second = raw_second + int(raw_second >= first); p, q = min(first, second), max(first, second)
            i, k = graph.rows[p], graph.rows[q]; j, ell = int(columns[p]), int(columns[q])
            if i == k or j == ell: counters["invalid_same_row_or_column"] += 1; continue
            if (masks[i] & (1 << ell)) or (masks[k] & (1 << j)): counters["invalid_cross_occupied"] += 1; continue
            masks[i] ^= (1 << j) | (1 << ell); masks[k] ^= (1 << ell) | (1 << j); columns[p], columns[q] = ell, j; counters["valid_swaps"] += 1; counters["accepted_swaps"] += 1
    digest_rows.append({"chain": chain, "digest_sha256": state_digest(view, endpoint, graph.relation_id, chain, 0, graph, columns), "endpoint": endpoint, "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint], "m": graph.m, "n_columns": graph.n_columns, "n_rows": ANCHORS, "relation_id": graph.relation_id, "schema": "h10a_state_digest.v1", "state": 0, "view": view, "view_ordinal": VIEW_ORDINAL[view]})
    propose(burn_multiple * graph.m); snapshots: list[Any] = []; seen: set[bytes] = set(); duplicate = returned = 0
    for state in range(1, retained_states + 1):
        propose(2 * graph.m); assert_state(graph, columns); raw = columns.tobytes(); duplicate += int(raw in seen); returned += int(raw == observed); seen.add(raw); snapshot = np.ascontiguousarray(columns.copy(), dtype=np.int64); snapshots.append(snapshot)
        digest_rows.append({"chain": chain, "digest_sha256": state_digest(view, endpoint, graph.relation_id, chain, state, graph, snapshot), "endpoint": endpoint, "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint], "m": graph.m, "n_columns": graph.n_columns, "n_rows": ANCHORS, "relation_id": graph.relation_id, "schema": "h10a_state_digest.v1", "state": state, "view": view, "view_ordinal": VIEW_ORDINAL[view]})
    valid_initial, changing = structural_diagnostics(graph); mixing, cells = degree_mix(graph); self_transitions = counters["lazy_stays"] + counters["invalid_same_row_or_column"] + counters["invalid_cross_occupied"]
    if counters["proposals"] != self_transitions + counters["accepted_swaps"] or counters["valid_swaps"] != counters["accepted_swaps"]: raise RuntimeError("chain counter identity failed")
    row = {"E_changing_switches": changing, "accepted_swaps": counters["accepted_swaps"], "chain": chain, "degree_mixing_digest_sha256": mixing, "degree_mixing_nonzero_cells": cells, "distinct_positive_column_degrees": len(set(value for value in graph.column_degrees if value > 0)), "distinct_positive_row_degrees": len(set(value for value in graph.row_degrees if value > 0)), "endpoint": endpoint, "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint], "final_state_digest": state_digest(view, endpoint, graph.relation_id, chain, retained_states, graph, snapshots[-1]), "initial_valid_unordered_switches": valid_initial, "invalid_cross_occupied": counters["invalid_cross_occupied"], "invalid_same_row_or_column": counters["invalid_same_row_or_column"], "lazy_stays": counters["lazy_stays"], "m": graph.m, "nonlazy_attempts": counters["nonlazy_attempts"], "proposals": counters["proposals"], "relation_id": graph.relation_id, "retained_duplicate_count": duplicate, "returned_to_observed_count": returned, "schedule": {"burn_in_multiple": burn_multiple, "burn_in_proposals": burn_multiple * graph.m, "retained_states": retained_states, "thin_multiple": 2, "thin_proposals": 2 * graph.m, "total_proposals": counters["proposals"]}, "schema": "h10a_chain_diagnostics.v1", "seed": seed, "self_transitions": self_transitions, "structurally_immobile": valid_initial == 0, "valid_swaps": counters["valid_swaps"], "view": view, "view_ordinal": VIEW_ORDINAL[view], "zero_acceptance": counters["accepted_swaps"] == 0}
    diagnostics.append(row); return tuple(snapshots)


def generate_null_states(view: ViewGraph, endpoint: str, digest_rows: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    retained, burn = (50, 50) if view.name == "primary" else (10, 30); per_relation: dict[tuple[int, str], tuple[Any, ...]] = {}
    for chain in (0, 1):
        for relation in view.relations: per_relation[(chain, relation)] = run_relation_chain(view.name, endpoint, view.graphs[(relation, endpoint)], chain, retained, burn, digest_rows, diagnostics)
    return {(chain, state): {relation: per_relation[(chain, relation)][state - 1] for relation in view.relations} for chain in (0, 1) for state in range(1, retained + 1)}


def parity_record(view: str, endpoint: str, kind: str, chain: int, state: int, check: str, observed: Any, threshold: Any, passed: bool, reference: str, relation: str = "", impression: str = "", news: str = "") -> dict[str, Any]:
    return {"chain": chain, "check_name": check, "endpoint": endpoint, "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint], "impression_id": impression, "kind_ordinal": 0 if kind == "real" else 1, "news_id": news, "observed": observed, "passed": bool(passed), "reference": reference, "relation_id": relation, "schema": "h10a_parity_check.v1", "state": state, "threshold": threshold, "view": view, "view_ordinal": VIEW_ORDINAL[view]}


def operator_parity(view: ViewGraph, endpoint: str, K: Any, G: Any, Q: Any, E: float, columns: Mapping[str, Any] | None, kind: str, chain: int, state: int, records: list[dict[str, Any]]) -> None:
    np = np_module(); outer_k, outer_g, outer_q, scalar_e = outer_operator(view, endpoint, columns)
    detailed = {"Bv_inf": np.float64(0), "BTu_inf": np.float64(0), "relation_decomposition_max_abs": np.float64(0)}
    for relation in view.relations:
        graph = view.graphs[(relation, endpoint)]; state_columns = graph.columns if columns is None else columns[relation]; d = np.asarray(graph.row_degrees, dtype=np.float64); e = np.asarray(graph.column_degrees, dtype=np.float64); N = np.zeros((ANCHORS, graph.n_columns), dtype=np.float64)
        for row, column in zip(graph.rows, state_columns, strict=True): N[row, int(column)] = np.divide(np.float64(1), np.sqrt(np.multiply(d[row], e[int(column)])))
        u = np.sqrt(np.divide(d, np.float64(graph.m), out=np.zeros_like(d), where=d > 0)); v = np.sqrt(np.divide(e, np.float64(graph.m), out=np.zeros_like(e), where=e > 0)); B = np.subtract(N, np.outer(u, v)); detailed["Bv_inf"] = np.maximum(detailed["Bv_inf"], np.max(np.abs(B @ v), initial=np.float64(0))); detailed["BTu_inf"] = np.maximum(detailed["BTu_inf"], np.max(np.abs(B.T @ u), initial=np.float64(0))); detailed["relation_decomposition_max_abs"] = np.maximum(detailed["relation_decomposition_max_abs"], np.max(np.abs(B @ B.T - (N @ N.T - np.outer(u, u))), initial=np.float64(0)))
    checks = (("BTu_inf", float(detailed["BTu_inf"]), 1e-12, "<="), ("Bv_inf", float(detailed["Bv_inf"]), 1e-12, "<="), ("K_symmetry_max_abs", float(np.max(np.abs(K - K.T), initial=np.float64(0))), 1e-12, "<="), ("W_decomposition_max_abs", float(np.max(np.abs(Q - (K + G)), initial=np.float64(0))), 1e-12, "<="), ("canonical_vs_outer_G_max_abs", float(np.max(np.abs(G - outer_g), initial=np.float64(0))), 1e-12, "<="), ("canonical_vs_outer_K_max_abs", float(np.max(np.abs(K - outer_k), initial=np.float64(0))), 1e-12, "<="), ("canonical_vs_outer_W_max_abs", float(np.max(np.abs(Q - outer_q), initial=np.float64(0))), 1e-12, "<="), ("canonical_vs_scalar_E_abs", abs(E - scalar_e), 1e-12, "<="), ("minimum_symmetric_eigenvalue", float(np.min(np.linalg.eigvalsh((K + K.T) * np.float64(0.5)))), -1e-10, ">="), ("relation_decomposition_max_abs", float(detailed["relation_decomposition_max_abs"]), 1e-12, "<="))
    for name, value, threshold, comparison in checks:
        passed = value <= threshold if comparison == "<=" else value >= threshold; records.append(parity_record(view.name, endpoint, kind, chain, state, name, value, threshold, passed, comparison))
        if not passed: raise RuntimeError(f"operator parity failed: {name}")


def score_parity(cohort: Cohort, view: str, endpoint: str, kind: str, chain: int, state: int, K: Any, G: Any, Q: Any, z: Any, g: Any, records: list[dict[str, Any]], selected_only: bool) -> None:
    np = np_module(); a = score_operator(cohort, Q)
    if selected_only:
        prefix = PAIR_PREFIX + view.encode() + b"|" + endpoint.encode() + b"|" + str(chain).encode() + b"|" + str(state).encode() + b"|"; occurrence_impression = np.repeat(np.arange(AUDIT_SIZE, dtype=np.intp), np.diff(cohort.offsets))
        def pair_key(occurrence: int) -> tuple[bytes, str, str, int]:
            impression = cohort.impression_ids[int(occurrence_impression[occurrence])]; news = cohort.candidate_ids[occurrence]; return hashlib.sha256(prefix + impression.encode() + b"|" + news.encode()).digest(), impression, news, occurrence
        chosen = np.ascontiguousarray([value[3] for value in heapq.nsmallest(256, (pair_key(occurrence) for occurrence in range(len(z))))], dtype=np.intp)
    else: chosen = np.arange(len(z), dtype=np.intp)
    direct_z, direct_g, direct_a = direct_score(cohort, K, chosen, not selected_only), direct_score(cohort, G, chosen, not selected_only), direct_score(cohort, Q, chosen, not selected_only)
    if not selected_only:
        checks = {"a_equals_z_plus_g_max_abs": float(np.max(np.abs(a - (z + g)), initial=np.float64(0))), "degree_sparse_vs_direct_max_abs": float(np.max(np.abs(g[chosen] - direct_g), initial=np.float64(0))), "raw_sparse_vs_direct_max_abs": float(np.max(np.abs(a[chosen] - direct_a), initial=np.float64(0))), "residual_sparse_vs_direct_max_abs": float(np.max(np.abs(z[chosen] - direct_z), initial=np.float64(0)))}
        for name in sorted(checks): records.append(parity_record(view, endpoint, kind, chain, state, name, checks[name], 1e-12, checks[name] <= 1e-12, "<="))
        if any(value > 1e-12 for value in checks.values()): raise RuntimeError("real score parity failed")
    else:
        for local, occurrence_raw in enumerate(chosen):
            occurrence = int(occurrence_raw); impression_index = int(np.searchsorted(cohort.offsets[1:], occurrence, side="right")); differences = {"pair_a_equals_z_plus_g_abs": abs(float(a[occurrence]) - float(np.add(z[occurrence], g[occurrence]))), "pair_degree_sparse_vs_direct_abs": abs(float(g[occurrence]) - float(direct_g[local])), "pair_raw_sparse_vs_direct_abs": abs(float(a[occurrence]) - float(direct_a[local])), "pair_residual_sparse_vs_direct_abs": abs(float(z[occurrence]) - float(direct_z[local]))}
            for name in sorted(differences):
                difference = differences[name]; records.append(parity_record(view, endpoint, kind, chain, state, name, difference, 1e-12, difference <= 1e-12, "<=", impression=cohort.impression_ids[impression_index], news=cohort.candidate_ids[occurrence]))
                if difference > 1e-12: raise RuntimeError("selected null score parity failed")


def metric_record(view: str, endpoint: str, kind: str, chain: int, state: int, metrics: Mapping[str, float]) -> dict[str, Any]:
    return {"chain": chain, "endpoint": endpoint, "endpoint_ordinal": ENDPOINT_ORDINAL[endpoint], "kind": kind, "kind_ordinal": 0 if kind == "real" else 1, "metrics": dict(metrics), "schema": "h10a_state_metrics.v1", "state": state, "view": view, "view_ordinal": VIEW_ORDINAL[view]}


def describe_null(real: float, rows: Mapping[tuple[int, int], Mapping[str, Any]], metric: str, primary: bool) -> dict[str, Any]:
    chain_values = [[float(rows[(chain, state)]["metrics"][metric]) for state in range(1, (50 if primary else 10) + 1)] for chain in (0, 1)]; combined = chain_values[0] + chain_values[1]
    combined_indices = {"q0.50": 49, "q0.95": 94, "q0.99": 98} if primary else {"q0.50": 9, "q0.95": 18, "q0.99": 19}
    summary: dict[str, Any] = {"chain_0": {}, "chain_1": {}, "combined": {"maximum": max(combined), "minimum": min(combined)}, "real": float(real)}
    for label, index in combined_indices.items():
        value = quantile(combined, index); summary["combined"][label] = value; summary["combined"][f"real_minus_{label}"] = real - value
    chain_indices = (("q0.95", 47), ("q0.99", 49)) if primary else (("q0.50", 4),)
    for chain in (0, 1):
        for label, index in chain_indices:
            value = quantile(chain_values[chain], index); summary[f"chain_{chain}"][label] = value; summary[f"chain_{chain}"][f"real_minus_{label}"] = real - value
    np = np_module(); tail = int(np.count_nonzero(np.greater_equal(np.asarray(combined, dtype=np.float64), np.float64(real)))); summary["combined"]["tail_count"] = tail; summary["combined"]["p_MC"] = float(np.divide(np.float64(1 + tail), np.float64(len(combined) + 1)))
    return summary


def v_pass(summary: Mapping[str, Any], primary: bool) -> bool:
    if primary: return summary["combined"]["real_minus_q0.99"] > 0 and summary["chain_0"]["real_minus_q0.99"] > 0 and summary["chain_1"]["real_minus_q0.99"] > 0 and summary["combined"]["p_MC"] <= 0.01
    return summary["combined"]["real_minus_q0.50"] > 0 and summary["chain_0"]["real_minus_q0.50"] > 0 and summary["chain_1"]["real_minus_q0.50"] > 0


def rank_pass(summary: Mapping[str, Any], primary: bool) -> bool:
    label = "q0.95" if primary else "q0.50"
    return all(summary[key][f"real_minus_{label}"] > 0 for key in ("combined", "chain_0", "chain_1"))


def nearest_quantiles(values: Any) -> dict[str, float]:
    np = np_module(); ordered = np.sort(np.ascontiguousarray(values, dtype=np.float64), kind="stable"); result = {}
    for probability in (0.0, 0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99, 1.0):
        index = 0 if probability == 0 else len(ordered) - 1 if probability == 1 else math.ceil(probability * len(ordered)) - 1; result[f"q{probability:.2f}"] = float(ordered[index])
    return result


def representation_digest(cohort: Cohort) -> str:
    digest = hashlib.sha256(); digest.update(b"H10A_REPRESENTATION_V1\n")
    for array in (cohort.X, cohort.Y, cohort.candidate_pattern, cohort.nz_occurrence, cohort.nz_impression, cohort.nz_anchor, cohort.nz_value, cohort.offsets):
        contiguous = np_module().ascontiguousarray(array); dtype = contiguous.dtype.str.encode("ascii"); digest.update(len(dtype).to_bytes(2, "little")); digest.update(dtype); digest.update(contiguous.ndim.to_bytes(2, "little"))
        for dimension in contiguous.shape: digest.update(int(dimension).to_bytes(8, "little"))
        digest.update(contiguous.tobytes(order="C"))
    for values in (cohort.impression_ids, cohort.candidate_ids):
        digest.update(len(values).to_bytes(8, "little"))
        for value in values:
            encoded = value.encode("ascii"); digest.update(len(encoded).to_bytes(4, "little")); digest.update(encoded)
    return digest.hexdigest().upper()


def pcg_probe_digest() -> str:
    np = np_module(); seed = int.from_bytes(hashlib.sha256(PCG_SEED_TEXT).digest()[:8], "big"); rng = np.random.Generator(np.random.PCG64DXSM(seed)); payload = bytearray(PCG_PREFIX); values = (2, 3, 17, 40, 41, 44, 45, 48, 49, 50, 51, 64)
    for index in range(128):
        m = values[index % len(values)]; raw = int(rng.bit_generator.random_raw()); payload.extend(struct.pack("<Q", raw))
        if (raw & 1) == 0: payload.append(0)
        else:
            payload.append(1); first = int(rng.integers(0, m, size=None, dtype=np.int64, endpoint=False)); raw_second = int(rng.integers(0, m - 1, size=None, dtype=np.int64, endpoint=False)); second = raw_second + int(raw_second >= first); payload.extend(struct.pack("<QQ", first, second))
    return sha256_bytes(bytes(payload))


def selected_primary_states() -> frozenset[tuple[str, int, int]]:
    values = []
    for endpoint in ENDPOINT_ORDER:
        for chain in (0, 1):
            for state in range(1, 51): values.append((hashlib.sha256(PARITY_PREFIX + endpoint.encode() + b"|" + str(chain).encode() + b"|" + str(state).encode()).digest(), endpoint, chain, state))
    values.sort(); return frozenset((endpoint, chain, state) for _, endpoint, chain, state in values[:64])


PRIMARY_PARITY = selected_primary_states()


def endpoint_coverage(cohort: Cohort, z_h: Any, z_c: Any) -> dict[str, Any]:
    np = np_module(); offsets = cohort.offsets; ranges_h = np.maximum.reduceat(z_h, offsets[:-1]) - np.minimum.reduceat(z_h, offsets[:-1]); ranges_c = np.maximum.reduceat(z_c, offsets[:-1]) - np.minimum.reduceat(z_c, offsets[:-1]); endpoint = np.logical_and(ranges_h > np.float64(1e-12), ranges_c > np.float64(1e-12)); robust = np.minimum(z_h, z_c); ranges_r = np.maximum.reduceat(robust, offsets[:-1]) - np.minimum.reduceat(robust, offsets[:-1]); robust_usable = ranges_r > np.float64(1e-12); endpoint_count = int(np.count_nonzero(endpoint)); robust_count = int(np.count_nonzero(robust_usable))
    occurrence_count = len(cohort.candidate_ids); supported = int(np.count_nonzero(cohort.candidate_pattern)); nonzero = {"H": int(np.count_nonzero(z_h != np.float64(0))), "C": int(np.count_nonzero(z_c != np.float64(0)))}
    return {"endpoint_usable_count": endpoint_count, "endpoint_usable_rate": float(np.divide(np.float64(endpoint_count), np.float64(AUDIT_SIZE))), "nonzero_score_rates": {endpoint_name: float(np.divide(np.float64(count), np.float64(occurrence_count))) for endpoint_name, count in nonzero.items()}, "nonzero_scores": nonzero, "robust_usable_count": robust_count, "robust_usable_rate": float(np.divide(np.float64(robust_count), np.float64(AUDIT_SIZE))), "supported_candidate_occurrences": supported, "supported_candidate_rate": float(np.divide(np.float64(supported), np.float64(occurrence_count))), "z_rob_dispersion": metric_v(robust, offsets)}


def top10_disagreement(cohort: Cohort, left: Any, right: Any) -> float:
    np = np_module(); overlap = np.add.reduceat(np.logical_and(left <= 10, right <= 10).astype(np.int64), cohort.offsets[:-1], dtype=np.int64); return float(np.mean(np.divide((10 - overlap).astype(np.float64), np.float64(10)), dtype=np.float64))


def graph_budget(view: ViewGraph) -> dict[str, int]:
    report = {"relations": len(view.relations), "H": sum(view.graphs[(relation, "H")].m for relation in view.relations), "C": sum(view.graphs[(relation, "C")].m for relation in view.relations)}; factor = 300 if view.name == "primary" else 100; report["proposals"] = factor * (report["H"] + report["C"])
    if report != VIEW_BUDGETS[view.name]: raise RuntimeError(f"graph budget mismatch: {report}")
    return report


def degree_shares(view: ViewGraph, endpoint: str) -> tuple[dict[str, float], float]:
    np = np_module(); shares = {}; numerator = np.float64(0); denominator = np.float64(0)
    for relation in view.relations:
        one = ViewGraph(view.name, (relation,), {relation: np.float64(1)}, {(relation, side): view.graphs[(relation, side)] for side in ENDPOINT_ORDER}); K, _, _, _ = canonical_operator(one, endpoint); energy = np.add.reduce(np.multiply(K.ravel(), K.ravel()), dtype=np.float64); shares[relation] = float(np.divide(np.float64(1), np.add(np.float64(1), energy))); alpha = np.float64(view.alpha[relation]); numerator = np.add(numerator, alpha); denominator = np.add(denominator, np.multiply(alpha, np.add(np.float64(1), energy)))
    return shares, float(np.divide(numerator, denominator))


def evaluate_view(view: ViewGraph, cohort: Cohort, metrics: list[dict[str, Any]], digests: list[dict[str, Any]], diagnostics: list[dict[str, Any]], parity: list[dict[str, Any]], forced_full: bool, precomputed: Mapping[str, Mapping[str, Any]] | None = None) -> tuple[dict[str, Any], bool, str]:
    np = np_module(); primary = view.name == "primary"; real: dict[str, dict[str, Any]] = {}
    for endpoint in ENDPOINT_ORDER:
        if precomputed is None:
            K, G, Q, E = canonical_operator(view, endpoint); z, g, a = score_operator(cohort, K), score_operator(cohort, G), score_operator(cohort, Q); V = metric_v(z, cohort.offsets)
        else:
            K, G, Q, E, z, g, a, V = (precomputed[endpoint][key] for key in ("K", "G", "Q", "E", "z", "g", "a", "V"))
        record = metric_record(view.name, endpoint, "real", -1, 0, {"E": float(E), "V": float(V)}); metrics.append(record); operator_parity(view, endpoint, K, G, Q, float(E), None, "real", -1, 0, parity); score_parity(cohort, view.name, endpoint, "real", -1, 0, K, G, Q, z, g, parity, False)
        real[endpoint] = {"K": K, "G": G, "Q": Q, "E": float(E), "z": z, "g": g, "a": a, "V": float(V), "record": record}
    nulls: dict[str, dict[tuple[int, int], dict[str, Any]]] = {}
    for endpoint in ENDPOINT_ORDER:
        state_columns = generate_null_states(view, endpoint, digests, diagnostics); nulls[endpoint] = {}
        for chain in (0, 1):
            for state in range(1, (50 if primary else 10) + 1):
                columns = state_columns[(chain, state)]; K, _, Q, E = canonical_operator(view, endpoint, columns, real[endpoint]["G"]); z = score_operator(cohort, K); V = metric_v(z, cohort.offsets); record = metric_record(view.name, endpoint, "null", chain, state, {"E": E, "V": V}); metrics.append(record); nulls[endpoint][(chain, state)] = {"K": K, "E": E, "V": V, "metrics": record["metrics"]}
                if primary and (endpoint, chain, state) in PRIMARY_PARITY:
                    operator_parity(view, endpoint, K, real[endpoint]["G"], Q, E, columns, "null", chain, state, parity); score_parity(cohort, view.name, endpoint, "null", chain, state, K, real[endpoint]["G"], Q, z, real[endpoint]["g"], parity, True)
    summary: dict[str, Any] = {"budget": graph_budget(view), "degree_mode_share": {}, "endpoint": {}, "relations": list(view.relations), "relation_weights": {relation: float(view.alpha[relation]) for relation in view.relations}}
    all_v = True
    for endpoint in ENDPOINT_ORDER:
        shares, rho = degree_shares(view, endpoint); v_summary = describe_null(real[endpoint]["V"], nulls[endpoint], "V", primary); e_summary = describe_null(real[endpoint]["E"], nulls[endpoint], "E", primary); passed = v_pass(v_summary, primary); all_v = all_v and passed
        summary["degree_mode_share"][endpoint] = {"aggregate_rho": rho, "relation_rho": shares}; summary["endpoint"][endpoint] = {"E_descriptive": e_summary, "V": v_summary, "V_gate_passed": passed}
    if not all_v and not forced_full:
        summary["gate"] = {"all_V_passed": False, "remaining_gate_stage_reached": False}; return summary, False, "V"
    residual_ranks: dict[str, Any] = {}
    for endpoint in ENDPOINT_ORDER:
        D, T, R2, _, _, _, _, residual_ranks[endpoint], degree_ranks = ranking_metrics(cohort, real[endpoint]["z"], real[endpoint]["g"]); real[endpoint]["record"]["metrics"].update({"D": D, "R2_deg": R2, "T": T})
        for chain in (0, 1):
            for state in range(1, (50 if primary else 10) + 1):
                null = nulls[endpoint][(chain, state)]; z = score_operator(cohort, null["K"]); Dn, Tn, _, _, _, _, _, _, _ = ranking_metrics(cohort, z, real[endpoint]["g"], degree_ranks); null["metrics"].update({"D": Dn, "T": Tn})
        d_summary, t_summary = describe_null(D, nulls[endpoint], "D", primary), describe_null(T, nulls[endpoint], "T", primary); d_ok, t_ok, r2_ok = rank_pass(d_summary, primary), rank_pass(t_summary, primary), R2 < 0.80
        summary["endpoint"][endpoint].update({"D": d_summary, "D_gate_passed": d_ok, "R2_deg": R2, "R2_gate_passed": r2_ok, "T": t_summary, "T_gate_passed": t_ok})
    coverage = endpoint_coverage(cohort, real["H"]["z"], real["C"]["z"]); minimum_count, minimum_rate = (5000, 0.50) if primary else (2500, 0.25); coverage_ok = coverage["endpoint_usable_count"] >= minimum_count and coverage["endpoint_usable_rate"] >= minimum_rate and coverage["robust_usable_count"] >= minimum_count and coverage["robust_usable_rate"] >= minimum_rate
    accepted = {f"{endpoint}_chain_{chain}": sum(int(row["accepted_swaps"]) for row in diagnostics if row["view"] == view.name and row["endpoint"] == endpoint and row["chain"] == chain) > 0 for endpoint in ENDPOINT_ORDER for chain in (0, 1)}; parity_ok = all(bool(row["passed"]) for row in parity if row["view"] == view.name)
    remaining = all(summary["endpoint"][endpoint][key] for endpoint in ENDPOINT_ORDER for key in ("D_gate_passed", "T_gate_passed", "R2_gate_passed")); all_pass = all_v and remaining and coverage_ok and all(accepted.values()) and parity_ok and bool(view.relations)
    robust = np.minimum(real["H"]["z"], real["C"]["z"]); summary.update({"coverage": coverage, "coverage_gate_passed": coverage_ok, "gate": {"accepted_swap_by_endpoint_chain": accepted, "accepted_swap_gate_passed": all(accepted.values()), "all_V_passed": all_v, "all_scientific_gates_passed": all_pass, "parity_gate_passed": parity_ok, "relation_eligibility_gate_passed": bool(view.relations), "remaining_gate_stage_reached": True}, "score_summary": {"endpoint_top10_disagreement": top10_disagreement(cohort, residual_ranks["H"], residual_ranks["C"]), "quantiles": {endpoint: {"degree": nearest_quantiles(real[endpoint]["g"]), "raw": nearest_quantiles(real[endpoint]["a"]), "residual": nearest_quantiles(real[endpoint]["z"])} for endpoint in ENDPOINT_ORDER}, "robust_quantiles": nearest_quantiles(robust)}})
    return summary, all_pass, "complete"


def exercise_synthetic_branches() -> dict[str, Any]:
    np = np_module(); mobile = graph_from_edges("SMOBILE", ((0, 0), (1, 1), (2, 2), (3, 3))); immobile = graph_from_edges("SIMMOBILE", ((0, 0), (0, 1), (1, 0), (1, 1))); mobile_valid, _ = structural_diagnostics(mobile); immobile_valid, _ = structural_diagnostics(immobile)
    if mobile_valid == 0 or immobile_valid != 0: raise RuntimeError("synthetic mobility branch failure")
    scores = np.asarray([0.0, 0.75e-12, 1.5e-12], dtype=np.float64); membership = [bool(np.absolute(np.subtract(value, scores[0])) <= np.float64(1e-12)) for value in scores]
    if membership != [True, True, False]: raise RuntimeError("anchored tie fixture failed")
    temporary_digests: list[dict[str, Any]] = []; temporary_diagnostics: list[dict[str, Any]] = []; run_relation_chain("primary", "H", mobile, 0, 50, 50, temporary_digests, temporary_diagnostics); run_relation_chain("primary", "H", immobile, 0, 50, 50, temporary_digests, temporary_diagnostics); mobile_row, immobile_row = temporary_diagnostics
    if mobile_row["accepted_swaps"] <= 0 or immobile_row["accepted_swaps"] != 0 or immobile_row["lazy_stays"] <= 0 or immobile_row["invalid_same_row_or_column"] <= 0 or immobile_row["invalid_cross_occupied"] <= 0 or immobile_row["retained_duplicate_count"] <= 0 or immobile_row["returned_to_observed_count"] <= 0: raise RuntimeError("synthetic chain branch failure")
    minimum = float(np.divide(np.float64(1), np.float64(101)))
    strict = {"combined": {"real_minus_q0.99": 0.0, "p_MC": 0.0}, "chain_0": {"real_minus_q0.99": 1.0}, "chain_1": {"real_minus_q0.99": 1.0}}
    if v_pass(strict, True): raise RuntimeError("strict scientific futility boundary failure")
    def initial(graph: RelationGraph) -> dict[str, Any]:
        valid, changing = structural_diagnostics(graph); digest, cells = degree_mix(graph)
        return {"E_changing_switches": changing, "degree_mixing_digest_sha256": digest, "degree_mixing_nonzero_cells": cells, "distinct_positive_column_degrees": len({value for value in graph.column_degrees if value > 0}), "distinct_positive_row_degrees": len({value for value in graph.row_degrees if value > 0}), "initial_valid_unordered_switches": valid, "structurally_immobile": valid == 0}
    return {"anchored_tie_membership": membership, "immobile_chain": {key: immobile_row[key] for key in ("invalid_cross_occupied", "invalid_same_row_or_column", "lazy_stays", "retained_duplicate_count", "returned_to_observed_count")}, "immobile": initial(immobile), "mobile": initial(mobile), "mobile_accepted_swaps": mobile_row["accepted_swaps"], "p_MC_minimum": minimum, "quantile_q0.99_fixture": quantile([float(i) for i in range(100)], 98), "slot_order_distinguished": True, "strict_futility_boundary_passed": True}


def compute_science(auth: Mapping[str, Any], synthetic: bool) -> tuple[dict[str, Any], dict[str, bytes], dict[str, int]]:
    timing: dict[str, int] = {}; input_hashes: dict[str, str] = {}; branch = {}
    if synthetic:
        timing["module_region_1_start_ns"] = time.perf_counter_ns(); cohort, views = synthetic_fixture(); primary_real = {}
        for endpoint in ENDPOINT_ORDER:
            K, G, Q, E = canonical_operator(views["primary"], endpoint); primary_real[endpoint] = {"K": K, "G": G, "Q": Q, "E": E}
        timing["module_region_1_stop_ns"] = time.perf_counter_ns(); branch = exercise_synthetic_branches()
    else:
        anchors = load_contract(); relations = load_relation_vocabulary(); facts = load_facts(anchors); timing["module_region_1_start_ns"] = time.perf_counter_ns(); news_map, patterns, Y = parse_news(anchors); cohort = load_real_cohort(news_map, patterns, Y); primary = compile_view(anchors, facts, relations, "primary"); views = {"primary": primary}; primary_real = {}
        for endpoint in ENDPOINT_ORDER:
            K, G, Q, E = canonical_operator(primary, endpoint); primary_real[endpoint] = {"K": K, "G": G, "Q": Q, "E": E}
        timing["module_region_1_stop_ns"] = time.perf_counter_ns(); input_hashes = dict(EXPECTED_INPUT_HASHES)
    timing["module_region_2_start_ns"] = time.perf_counter_ns()
    for endpoint in ENDPOINT_ORDER:
        values = primary_real[endpoint]; values["z"] = score_operator(cohort, values["K"]); values["g"] = score_operator(cohort, values["G"]); values["a"] = score_operator(cohort, values["Q"]); values["V"] = metric_v(values["z"], cohort.offsets)
        if synthetic and not np_module().all(values["z"][cohort.candidate_pattern == 0] == np_module().float64(0)): raise RuntimeError("synthetic unsupported candidates did not score exact zero")
    timing["module_region_2_stop_ns"] = time.perf_counter_ns(); timing["module_region_1_delta_ns"] = timing["module_region_1_stop_ns"] - timing["module_region_1_start_ns"]; timing["module_region_2_delta_ns"] = timing["module_region_2_stop_ns"] - timing["module_region_2_start_ns"]; timing["module_ns"] = timing["module_region_1_delta_ns"] + timing["module_region_2_delta_ns"]
    if not synthetic:
        for view_name in VIEW_ORDER[1:]: views[view_name] = compile_view(anchors, facts, relations, view_name)
    metrics: list[dict[str, Any]] = []; digests: list[dict[str, Any]] = []; diagnostics: list[dict[str, Any]] = []; parity: list[dict[str, Any]] = []; summaries = {}; reached = {}; structural = True
    for view_name in VIEW_ORDER:
        if not synthetic and not structural: reached[view_name] = "skipped_by_preceding_failed_conjunct"; continue
        if view_name not in views:
            views[view_name] = compile_view(anchors, facts, relations, view_name)  # type: ignore[possibly-undefined]
        summary, passed, stage = evaluate_view(views[view_name], cohort, metrics, digests, diagnostics, parity, synthetic, primary_real if view_name == "primary" else None); summaries[view_name] = summary; reached[view_name] = stage
        if not synthetic and not passed: structural = False
    total_proposals = sum(int(row["proposals"]) for row in diagnostics); retained = sum(row["kind"] == "null" for row in metrics)
    if synthetic and (total_proposals != 4_774_300 or retained != 280): raise RuntimeError("synthetic schedule totals mismatch")
    verdict = "SYNTHETIC_FORCED_FULL_PATH_PASS" if synthetic else ("PASS_H10A_RELATION_NULL_FEASIBILITY" if structural and len(summaries) == 3 else "KILL_H10_RELATION_NULL_DIRECTION")
    payload = {"branch_preflight": branch, "cohort_counts": dict(cohort.counts), "fixed_graph_counts": {name: graph_budget(view) for name, view in views.items()}, "inputs_sha256": input_hashes, "labels_opened": False, "pcg_probe_digest_sha256": pcg_probe_digest(), "protocol_sha256": PROTOCOL_SHA256, "reached_stage": reached, "representation_digest_sha256": representation_digest(cohort), "schema": "h10a_scientific_payload.v1", "structural_verdict": verdict, "synthetic": synthetic, "total_proposals": total_proposals, "retained_endpoint_states": retained, "views": summaries}
    metrics.sort(key=lambda row: (row["view_ordinal"], row["endpoint_ordinal"], row["kind_ordinal"], row["chain"], row["state"])); digests.sort(key=lambda row: (row["view_ordinal"], row["endpoint_ordinal"], row["chain"], row["state"], row["relation_id"])); diagnostics.sort(key=lambda row: (row["view_ordinal"], row["endpoint_ordinal"], row["relation_id"], row["chain"])); parity.sort(key=lambda row: (row["view_ordinal"], row["endpoint_ordinal"], row["kind_ordinal"], row["chain"], row["state"], row["relation_id"], row["check_name"], row["impression_id"], row["news_id"]))
    raw = {"state_metrics.jsonl": b"".join(canonical_bytes(row) for row in metrics), "state_digests.jsonl": b"".join(canonical_bytes(row) for row in digests), "chain_diagnostics.jsonl": b"".join(canonical_bytes(row) for row in diagnostics), "parity_checks.jsonl": b"".join(canonical_bytes(row) for row in parity)}; payload["raw_four_file_records"] = {name: {"bytes": len(value), "sha256": sha256_bytes(value)} for name, value in sorted(raw.items())}; raw["scientific_payload.json"] = canonical_bytes(payload)
    return payload, raw, timing


def peak_resident_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True); get_current_process = kernel32.GetCurrentProcess; get_current_process.argtypes = []; get_current_process.restype = wintypes.HANDLE
        try: get_process_memory_info = kernel32.K32GetProcessMemoryInfo
        except AttributeError:
            psapi = ctypes.WinDLL("psapi", use_last_error=True); get_process_memory_info = psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]; get_process_memory_info.restype = wintypes.BOOL
        counters = ProcessMemoryCounters(); counters.cb = ctypes.sizeof(ProcessMemoryCounters); process = get_current_process(); ctypes.set_last_error(0)
        if not get_process_memory_info(process, ctypes.byref(counters), counters.cb): raise ctypes.WinError(ctypes.get_last_error())
        peak = int(counters.PeakWorkingSetSize)
        if peak <= 0: raise RuntimeError("Windows peak working-set counter is not positive")
        return peak
    import resource
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss); return value if sys.platform == "darwin" else value * 1024


def stage_directory(output: Path) -> Path:
    stage = output.parent / f".stage-{output.name}-{uuid.uuid4().hex}"
    stage.mkdir(parents=False, exist_ok=False)
    return stage


def numpy_manifest() -> tuple[bytes, dict[str, Any]]:
    np = np_module(); package = Path(np.__file__).resolve().parent; rows = []
    for path in sorted(package.rglob("*"), key=lambda item: item.relative_to(package).as_posix()):
        if path.is_symlink(): raise RuntimeError(f"NumPy package symlink forbidden: {path}")
        stat = path.lstat()
        if os.name == "nt" and getattr(stat, "st_file_attributes", 0) & 0x400: raise RuntimeError(f"NumPy package reparse point forbidden: {path}")
        if path.is_file(): rows.append({"bytes": stat.st_size, "path": path.relative_to(package).as_posix(), "sha256": sha256_file(path)})
    raw = b"".join(canonical_bytes(row) for row in rows)
    return raw, {"bytes": len(raw), "file_count": len(rows), "package_root": str(package), "sha256": sha256_bytes(raw)}


def publish_probe(auth: Mapping[str, Any], perf_start: int) -> dict[str, Any]:
    global _NUMPY_TREE_MANIFEST_SHA256, _NUMPY_TREE_VALIDATION_PASSED
    output = bound_path(auth, "output_directory"); stage = stage_directory(output); raw_manifest, manifest = numpy_manifest(); digest = pcg_probe_digest()
    _NUMPY_TREE_MANIFEST_SHA256 = str(manifest["sha256"]); _NUMPY_TREE_VALIDATION_PASSED = True
    manifest_path = stage / "numpy_package_manifest.jsonl"; write_exclusive(manifest_path, raw_manifest)
    if auth.get("publish_numpy_manifest_path") and Path(str(auth["publish_numpy_manifest_path"])).resolve() != output / "numpy_package_manifest.jsonl": raise RuntimeError("probe manifest publication path mismatch")
    result_value = {"environment": {"numpy_package": manifest, "numpy_version": NUMPY_VERSION, "python_version": ".".join(str(value) for value in PYTHON_VERSION), "thread_bounds": {name: os.environ.get(name) for name in THREAD_ENV}}, "numpy_tree_manifest_sha256": _NUMPY_TREE_MANIFEST_SHA256, "numpy_tree_validation_passed": _NUMPY_TREE_VALIDATION_PASSED, "output_id": auth["output_id"], "pcg_probe_sha256": digest, "protocol_sha256": PROTOCOL_SHA256, "run_role": auth["run_role"], "schema": "h10a_probe_result.v1", "synthetic": True}
    write_json(stage / "result.json", result_value)
    if set(path.name for path in stage.iterdir()) != {"numpy_package_manifest.jsonl", "result.json"}: raise RuntimeError("probe publication inventory mismatch")
    if manifest_path.read_bytes() != raw_manifest or read_json(stage / "result.json") != result_value: raise RuntimeError("staged probe publication validation failed")
    rename_no_overwrite(stage, output)
    if _ASYNC_FAILURES or (_ASYNC_LEDGER is not None and _ASYNC_LEDGER.stat().st_size != 0): raise RuntimeError("asynchronous failure before release")
    if _INNER_LOCK is None: raise RuntimeError("inner lock missing")
    _INNER_LOCK.release()
    peak = peak_resident_bytes(); perf_stop = time.perf_counter_ns()
    return {"module_ns": 0, "numpy_tree_manifest_sha256": _NUMPY_TREE_MANIFEST_SHA256, "numpy_tree_validation_passed": _NUMPY_TREE_VALIDATION_PASSED, "output_directory": str(output), "output_id": auth["output_id"], "pcg_probe_sha256": digest, "peak_resident_bytes": peak, "perf_delta_ns": perf_stop - perf_start, "perf_start_ns": perf_start, "perf_stop_ns": perf_stop, "process_pid": os.getpid(), "result": str(output / "result.json"), "run_role": auth["run_role"], "scientific_verdict": "PROBE_ONLY_NON_SCIENTIFIC", "status": "H10A_PROBE_COMPLETE"}


def publish_run(auth: Mapping[str, Any], synthetic: bool, perf_start: int) -> dict[str, Any]:
    digest = pcg_probe_digest()
    if auth.get("expected_pcg_probe_sha256") != digest or auth.get("pcg_probe_digest_sha256") != digest: raise RuntimeError("locked PCG64DXSM probe mismatch")
    if not _NUMPY_TREE_VALIDATION_PASSED or _NUMPY_TREE_MANIFEST_SHA256 != auth.get("numpy_manifest_sha256"): raise RuntimeError("NumPy tree validation evidence is absent")
    payload, raw, module_timing = compute_science(auth, synthetic); output = bound_path(auth, "output_directory"); stage = stage_directory(output)
    for name in SCIENTIFIC_FILES:
        write_exclusive(stage / name, raw[name])
    artifact_records = {name: {"bytes": len(raw[name]), "name": name, "sha256": sha256_bytes(raw[name])} for name in SCIENTIFIC_FILES}
    module_ns = int(module_timing["module_ns"]); structural = str(payload["structural_verdict"])
    if synthetic: decision = "SYNTHETIC_FORCED_FULL_PATH_NON_EVIDENCE"
    elif structural != "PASS_H10A_RELATION_NULL_FEASIBILITY" or module_ns > 30_000_000_000: decision = "KILL_H10_RELATION_NULL_DIRECTION"
    else: decision = structural
    result_value = {"artifacts": artifact_records, "decision": decision, "numpy_tree_manifest_sha256": _NUMPY_TREE_MANIFEST_SHA256, "numpy_tree_validation_passed": _NUMPY_TREE_VALIDATION_PASSED, "output_id": auth["output_id"], "protocol_sha256": PROTOCOL_SHA256, "provenance": {"authorization_sha256": sha256_file(bound_path(auth, "authorization_path")), "implementation_lock_sha256": auth.get("active_lock_sha256"), "pcg_probe_sha256": digest, "protocol_sha256": PROTOCOL_SHA256, "runner_sha256": sha256_file(SCRIPT)}, "publication_directory": str(output), "run_role": auth["run_role"], "schema": "h10a_result.v1", "structural_verdict": structural, "synthetic": synthetic, "timing": module_timing}
    write_json(stage / "result.json", result_value)
    if set(path.name for path in stage.iterdir()) != set(SCIENTIFIC_FILES) | {"result.json"}: raise RuntimeError("scientific publication inventory mismatch")
    for name, record in artifact_records.items():
        if file_record(stage / name, relative=True) != {"bytes": record["bytes"], "path": name, "sha256": record["sha256"]}: raise RuntimeError("staged artifact hash mismatch")
    if read_json(stage / "result.json") != result_value: raise RuntimeError("staged result validation failed")
    rename_no_overwrite(stage, output)
    if _ASYNC_FAILURES or (_ASYNC_LEDGER is not None and _ASYNC_LEDGER.stat().st_size != 0): raise RuntimeError("asynchronous failure before release")
    if _INNER_LOCK is None: raise RuntimeError("inner lock missing")
    _INNER_LOCK.release()
    peak = peak_resident_bytes(); perf_stop = time.perf_counter_ns()
    return {"module_ns": module_ns, "numpy_tree_manifest_sha256": _NUMPY_TREE_MANIFEST_SHA256, "numpy_tree_validation_passed": _NUMPY_TREE_VALIDATION_PASSED, "output_directory": str(output), "output_id": auth["output_id"], "pcg_probe_sha256": digest, "peak_resident_bytes": peak, "perf_delta_ns": perf_stop - perf_start, "perf_start_ns": perf_start, "perf_stop_ns": perf_stop, "process_pid": os.getpid(), "result": str(output / "result.json"), "run_role": auth["run_role"], "scientific_verdict": structural, "status": "H10A_RUN_COMPLETE"}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__); subparsers = parser.add_subparsers(dest="command", required=True)
    for action in ("probe", "self-test", "run"):
        child = subparsers.add_parser(action); child.add_argument("--authorization", required=True); child.add_argument("--token", required=True); child.add_argument("--process-start", required=True); child.add_argument("--process-ack", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments(); auth = bootstrap(args)
    perf_start = time.perf_counter_ns()
    if args.command == "probe": summary = publish_probe(auth, perf_start)
    else:
        synthetic = args.command == "self-test"
        summary = publish_run(auth, synthetic, perf_start)
    sys.stdout.write(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"); sys.stdout.flush(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
