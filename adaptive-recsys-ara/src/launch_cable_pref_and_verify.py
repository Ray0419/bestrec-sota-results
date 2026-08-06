#!/usr/bin/env python3
"""Windows-safe launcher and independent verifier for CABLE-PREF.

This module is intentionally the only authority allowed to publish a
``CABLE_EXTERNAL_COMPLETE_*.json`` marker.  The outcome runner may publish a
candidate closure, but it cannot certify its own process exit, lock release,
persistent logs, or scientific verdict.

The process/integrity chain and exact scientific raw-array replay are complete.
The launcher prospectively binds the frozen CABLE-PREF research objects,
requires outcome-blind synthetic preflights, and independently replays G1--G9
after the runner exits before it can publish the sole external marker.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import heapq
import importlib.metadata as importlib_metadata
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tempfile
import threading
import traceback
from typing import Any, Iterable, Mapping, Sequence
import uuid
import zipfile


THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)
GATE_NAMES = tuple(f"G{index}" for index in range(1, 10))
EXPECTED_METHODS = (
    "bpr",
    "raw_hybrid",
    "order_only",
    "admission_only",
    "cable_pref",
    "shuffled_direction",
    "uib_boundary",
    "wrong_boundary",
)
EXPECTED_SEEDS = (20260835, 20260836, 20260837)
EXPECTED_ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)
EXPECTED_METRICS = (
    "conditional_admission_at_200",
    "net_new_preferred_support",
    "net_admission_advantage",
    "spce_at_10",
    "preferred_exposure_at_10",
    "ndcg_at_10",
    "recall_at_10",
    "low_rating_intrusion_at_10",
)
MANIFEST_FIELDS = (
    "schema",
    "protocol_sha256",
    "execution_fingerprint_sha256",
    "stage",
    "seed",
    "methods",
    "alphas",
    "user_ids",
    "candidates",
    "bpr_scores",
    "semantic_scores",
    "bpr_queries",
    "semantic_queries",
    "learned_boundaries",
    "history_items",
    "history_counts",
    "complement_counts",
    "oracle_agreement",
    "target_fields_accessed",
)
R_MANIFEST_FIELDS = (
    "schema",
    "protocol_sha256",
    "execution_fingerprint_sha256",
    "user_ids",
    "bpr_items",
    "raw_semantic_items",
    "raw_queries",
    "bpr_queries",
    "history_items",
    "history_counts",
    "complement_counts",
    "raw_cutoff_items",
    "raw_cutoff_scores",
    "target_fields_accessed",
)
RAW_VALIDATION_FIELDS = (
    "schema",
    "protocol_fingerprint_sha256",
    "execution_fingerprint_sha256",
    "methods",
    "seeds",
    "metrics",
    "alphas",
    "user_ids",
    "catalog_movie_ids",
    "per_user_metrics",
    "selected_alpha_index",
    "selected_alpha",
    "stronger_relevance_method",
    "power_comparison_names",
    "power_detection_fractions",
    "power_passed",
    "V_manifest_files",
    "V_manifest_sha256",
    "semantic_matrix_file",
    "semantic_matrix_sha256",
    "semantic_index_file",
    "semantic_index_sha256",
    "bpr_item_matrix_file",
    "bpr_item_matrix_sha256",
    "bpr_index_file",
    "bpr_index_sha256",
    "collaborative_mask_file",
    "collaborative_mask_sha256",
    "V_event_items",
    "V_event_movie_ids",
    "V_event_ratings",
    "V_event_timestamps",
    "V_event_ordinals",
    "V_event_counts",
    "V_pair_preferred",
    "V_pair_rejected",
    "V_pair_low_movie_ids",
    "V_pair_high_movie_ids",
    "V_pair_counts",
    "V_pair_identity_sha256",
    "R_event_items",
    "R_event_movie_ids",
    "R_event_ratings",
    "R_event_timestamps",
    "R_event_ordinals",
    "R_event_counts",
    "R_pair_preferred",
    "R_pair_rejected",
    "R_pair_low_movie_ids",
    "R_pair_high_movie_ids",
    "R_pair_counts",
    "R_pair_identity_sha256",
    "R_selected_pairs",
    "R_selected_pair_users",
    "V_fixed_pairs",
    "V_pair_users",
    "V_unique_bpr_missed_preferred_endpoints",
    "V_missed_endpoint_users",
    "V_admission_changed_count_by_seed",
    "V_admission_total_by_seed",
    "V_spce_changed_count_by_seed",
    "V_spce_total_by_seed",
    "training_methods",
    "training_optimizer_steps",
    "training_pair_presentations",
    "training_admission_presentations",
    "adapter_initial_memory_sha256",
    "adapter_final_memory_sha256",
    "V_manifest_published_utc",
    "V_binary_relevance_opened_utc",
    "choices_frozen_utc",
    "V_exact_preference_opened_utc",
    "target_blind_before_binary_relevance",
    "choices_before_exact_preferences",
)
RAW_TEST_FIELDS = (
    "schema",
    "protocol_fingerprint_sha256",
    "execution_fingerprint_sha256",
    "methods",
    "seeds",
    "metrics",
    "alphas",
    "user_ids",
    "catalog_movie_ids",
    "per_user_metrics",
    "selected_alpha_index",
    "selected_alpha",
    "stronger_relevance_method",
    "T_manifest_files",
    "T_manifest_sha256",
    "semantic_matrix_file",
    "semantic_matrix_sha256",
    "semantic_index_file",
    "semantic_index_sha256",
    "bpr_item_matrix_file",
    "bpr_item_matrix_sha256",
    "bpr_index_file",
    "bpr_index_sha256",
    "collaborative_mask_file",
    "collaborative_mask_sha256",
    "T_event_items",
    "T_event_movie_ids",
    "T_event_ratings",
    "T_event_timestamps",
    "T_event_ordinals",
    "T_event_counts",
    "T_pair_preferred",
    "T_pair_rejected",
    "T_pair_low_movie_ids",
    "T_pair_high_movie_ids",
    "T_pair_counts",
    "T_pair_identity_sha256",
    "T_fixed_pairs",
    "T_pair_users",
    "T_unique_bpr_missed_preferred_endpoints",
    "T_missed_endpoint_users",
    "T_admission_changed_count_by_seed",
    "T_admission_total_by_seed",
    "T_spce_changed_count_by_seed",
    "T_spce_total_by_seed",
    "action_checked",
    "action_violations",
    "action_tie_boundaries",
    "action_passed",
    "g1_invariant_names",
    "g1_invariant_values",
    "gate_names",
    "gate_values",
    "T_manifest_published_utc",
    "T_opened_utc",
    "test_opened",
)
RAW_LATENCY_FIELDS = (
    "schema",
    "protocol_fingerprint_sha256",
    "execution_fingerprint_sha256",
    "seeds",
    "methods",
    "user_ids",
    "durations_ms",
    "per_request_median_ms",
    "p95_ms",
    "p99_ms",
    "p95_ratio_by_seed",
    "worst_cable_p95_ms",
    "worst_p95_ratio",
    "passed",
)
IMMUTABLE_NAMES = (
    "semantic_matrix",
    "semantic_index",
    "bpr_item_matrix",
    "bpr_user_matrix",
    "collaborative_mask",
    "bpr_index",
)
EXPECTED_RUNNER_SELF_TEST_CHECKS = frozenset(
    {
        "admission_preferred_endpoint_deduplicated_after_cap",
        "all_trainable_controls_match_steps_and_pair_presentations",
        "base_top201_matches_naive_all_ties",
        "base_topk_plus_one_matches_naive_random",
        "batch_single_query_equivalence",
        "bootstrap_seed_deterministic",
        "capacity_199_collaborative_fails",
        "capacity_200_collaborative_plus_500_semantic_passes",
        "capacity_499_semantic_fails",
        "cross_stage_duplicate_user_movie_fails",
        "exact_200_plus_200_union",
        "empty_metric_support_fails_gates_without_nonfinite_output",
        "faiss_matrix_all_equal_ties",
        "faiss_matrix_random_exact_ids_and_order",
        "half_star_rating_is_float",
        "leaveout_tie_action_equivalence",
        "manifest_batch_64_plus_tail_matches_single",
        "offline_sentence_transformer_preflight",
        "raw_latency_schema_unique",
        "raw_test_schema_unique",
        "raw_validation_schema_unique",
        "retrieval_branches_disjoint",
        "seen_501_of_first_701_still_exact_200",
        "seen_or_future_high_scores_are_masked",
        "strict_utf8_metadata",
        "structural_row_retains_no_rating_payload",
        "target_poisoning_leaves_R_manifest_arrays_identical",
        "target_blind_manifest_api_accepts_prefix_not_current_outcomes",
        "deterministic_full_G1_G9_replay",
        "uib_two_sided_boundary_gradients",
        "unsupported_bpr_factors_exact_zero",
        "zero_output_adapter_identity",
    }
)
FROZEN_SOURCE_SHA256 = {
    "runner": "e73e19fed6d13efa7752ee6a603fba9f8f935f76b864fcb9e252be39a1866dc5",
    "config": "81b2bdc2645ee11e26f1e95b2c68cf4fb9412b3da7b6363bb7bc7d0e5c658cf4",
    "protocol": "9789d57dc6675ff16cbd7bfbf2f8d8879b1f8e9dc4599e30de3804ce7ae83ae4",
    "research_question": "38c4ba4f21c3ed989dbf525280b71dcbd0ac1460e0adc8f84d6b8caa25df244e",
    "cycle5_survey": "a85a7059776412cdd82b39f621c19efcbbc693207fba4e75ff76982a0ac01f61",
    "architecture": "038c74b2d258d5dae871b9d3d40cae7c36d4eeb69a1d5199fc3bb51d4dbef919",
}
EXTERNAL_MARKER_PREFIX = "CABLE_EXTERNAL_COMPLETE_"
RUNNER_CANDIDATE_GLOB = "CABLE_RUNNER_COMPLETE_CANDIDATE_*.json"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class IntegrityError(RuntimeError):
    """Raised whenever an append-only, source, or replay invariant fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def fsync_directory(path: Path) -> None:
    # Python does not expose a portable Windows directory-fsync primitive.
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bytes_exclusive(path: Path, payload: bytes) -> None:
    """Crash-safe, no-overwrite publication using a same-directory hard link."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    )
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def publish_json_exclusive(path: Path, value: Any) -> None:
    publish_bytes_exclusive(path, canonical_json_bytes(value))


def create_empty_file_exclusive(path: Path) -> None:
    publish_bytes_exclusive(path, b"")


def append_json_line(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def install_async_exception_hooks(ledger: Path) -> None:
    def thread_hook(arguments: threading.ExceptHookArgs) -> None:
        append_json_line(
            ledger,
            {
                "kind": "threading.excepthook",
                "utc": utc_now(),
                "thread": getattr(arguments.thread, "name", None),
                "exception_type": getattr(arguments.exc_type, "__name__", None),
                "exception": str(arguments.exc_value),
                "traceback": "".join(
                    traceback.format_exception(
                        arguments.exc_type,
                        arguments.exc_value,
                        arguments.exc_traceback,
                    )
                ),
            },
        )

    def unraisable_hook(arguments: Any) -> None:
        append_json_line(
            ledger,
            {
                "kind": "sys.unraisablehook",
                "utc": utc_now(),
                "exception_type": type(arguments.exc_value).__name__,
                "exception": str(arguments.exc_value),
                "object": repr(arguments.object),
                "traceback": "".join(
                    traceback.format_exception(
                        type(arguments.exc_value),
                        arguments.exc_value,
                        arguments.exc_traceback,
                    )
                ),
            },
        )

    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def read_json_mapping(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"Cannot read {label}: {path}") from exc
    if not isinstance(value, Mapping):
        raise IntegrityError(f"{label} is not a JSON object: {path}")
    return value


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IntegrityError(f"{label} must be a mapping")
    return value


def require_sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise IntegrityError(f"{label} must be a sequence")
    return value


def require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise IntegrityError(f"{label} must be boolean")
    return value


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise IntegrityError(f"{label} must be an integer")
    return int(value)


def require_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntegrityError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise IntegrityError(f"{label} must be finite")
    return result


def contained_file(base: Path, relative_name: str, label: str) -> Path:
    relative = Path(relative_name)
    if relative.is_absolute() or relative.name in {"", ".", ".."}:
        raise IntegrityError(f"Invalid {label} path: {relative_name!r}")
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes run directory") from exc
    if not resolved.is_file():
        raise IntegrityError(f"Missing {label}: {resolved}")
    return resolved


def safe_relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError as exc:
        raise IntegrityError(f"Path escapes run directory: {path}") from exc


def file_hash_manifest(root: Path, excluded: Iterable[Path] = ()) -> Mapping[str, str]:
    excluded_resolved = {path.resolve() for path in excluded}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        if path.is_symlink():
            raise IntegrityError(f"Symlink forbidden in run closure: {path}")
        if path.is_file() and path.resolve() not in excluded_resolved:
            result[safe_relative(path, root)] = sha256_file(path)
    return result


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
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
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: no such process.
            return False
        if error == 5:  # Access denied means exit cannot be proved.
            return True
        raise ctypes.WinError(error)
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(exit_code.value) == still_active
    finally:
        if not kernel32.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())


class ExclusiveOwnerLock:
    def __init__(self, path: Path, role: str) -> None:
        self.path = path.resolve()
        self.role = role
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        if self.acquired:
            raise IntegrityError(f"{self.role} lock acquired twice")
        publish_json_exclusive(
            self.path,
            {
                "schema": "cable-pref-exclusive-owner-lock-v1",
                "role": self.role,
                "pid": os.getpid(),
                "token_sha256": sha256_text(self.token),
                "created_utc": utc_now(),
            },
        )
        self.acquired = True

    def assert_owned(self) -> None:
        if not self.acquired or not self.path.is_file():
            raise IntegrityError(f"{self.role} lock is not held")
        record = read_json_mapping(self.path, f"{self.role} lock")
        if record.get("schema") != "cable-pref-exclusive-owner-lock-v1":
            raise IntegrityError(f"{self.role} lock schema changed")
        if int(record.get("pid", -1)) != os.getpid():
            raise IntegrityError(f"{self.role} lock owner changed")
        if record.get("token_sha256") != sha256_text(self.token):
            raise IntegrityError(f"{self.role} lock token changed")

    def release(self) -> None:
        if not self.acquired:
            return
        self.assert_owned()
        self.path.unlink()
        fsync_directory(self.path.parent)
        self.acquired = False


def _process_affinity_record() -> Mapping[str, Any]:
    if os.name != "nt":
        if hasattr(os, "sched_getaffinity"):
            values = sorted(os.sched_getaffinity(0))
            return {"cpu_indices": values, "source": "sched_getaffinity"}
        raise IntegrityError("Process affinity cannot be recorded on this platform")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetProcessAffinityMask.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    )
    kernel32.GetProcessAffinityMask.restype = wintypes.BOOL
    process_mask = ctypes.c_size_t()
    system_mask = ctypes.c_size_t()
    if not kernel32.GetProcessAffinityMask(
        kernel32.GetCurrentProcess(),
        ctypes.byref(process_mask),
        ctypes.byref(system_mask),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    width = ctypes.sizeof(ctypes.c_size_t) * 8
    return {
        "process_mask_hex": hex(int(process_mask.value)),
        "system_mask_hex": hex(int(system_mask.value)),
        "cpu_indices": [
            index
            for index in range(width)
            if int(process_mask.value) & (1 << index)
        ],
        "source": "GetProcessAffinityMask",
    }


def _active_power_policy_record() -> Mapping[str, Any]:
    if os.name != "nt":
        return {"platform": os.name, "visible": False, "value": "not-windows"}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    completed = subprocess.run(
        ["powercfg", "/getactivescheme"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=10,
        startupinfo=startupinfo,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise IntegrityError("Windows active power policy cannot be recorded cleanly")
    value = completed.stdout.strip()
    if not value:
        raise IntegrityError("Windows active power policy is empty")
    return {"platform": "windows", "visible": True, "value": value}


def machine_hardware_record() -> Mapping[str, Any]:
    try:
        versions = {
            distribution: importlib_metadata.version(distribution)
            for distribution in (
                "numpy",
                "torch",
                "faiss-cpu",
                "sentence-transformers",
            )
        }
    except importlib_metadata.PackageNotFoundError as exc:
        raise IntegrityError("Required package version is not installed") from exc
    try:
        import numpy as np
        import faiss
    except ImportError as exc:
        raise IntegrityError("NumPy/FAISS hardware provenance is unavailable") from exc
    try:
        blas_raw = np.show_config(mode="dicts")
    except TypeError:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            np.show_config()
        blas_raw = {"text": buffer.getvalue()}
    blas = json.loads(json.dumps(blas_raw, sort_keys=True, default=str))
    cpu_model = platform.processor().strip()
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                cpu_model = str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError as exc:
            raise IntegrityError("Windows CPU model cannot be read") from exc
    logical_cores = os.cpu_count()
    if not cpu_model or logical_cores is None or logical_cores <= 0:
        raise IntegrityError("CPU model/logical-core provenance is incomplete")
    return {
        "schema": "cable-pref-machine-hardware-v1",
        "cpu_model": cpu_model,
        "logical_core_count": int(logical_cores),
        "process_affinity": dict(_process_affinity_record()),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "package_versions": versions,
        "faiss_version": str(getattr(faiss, "__version__", versions["faiss-cpu"])),
        "numpy_blas_configuration": blas,
        "visible_power_policy_metadata": dict(_active_power_policy_record()),
    }


def _child_process_memory_record(process: subprocess.Popen[Any]) -> Mapping[str, Any]:
    if os.name != "nt":
        return {
            "source": "not-windows-no-individual-post-exit-counter",
            "peak_working_set_bytes": None,
        }

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = (
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
        )

    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    handle = wintypes.HANDLE(int(process._handle))  # noqa: SLF001 - Windows handle.
    if not psapi.GetProcessMemoryInfo(
        handle, ctypes.byref(counters), ctypes.sizeof(counters)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    peak = int(counters.PeakWorkingSetSize)
    if peak <= 0:
        raise IntegrityError("Child peak working set was not recorded")
    return {
        "source": "GetProcessMemoryInfo",
        "peak_working_set_bytes": peak,
        "page_fault_count": int(counters.PageFaultCount),
        "peak_pagefile_bytes": int(counters.PeakPagefileUsage),
    }


def run_hidden_process(
    command: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[int, int, Mapping[str, Any]]:
    create_empty_file_exclusive(stdout_path)
    create_empty_file_exclusive(stderr_path)
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with stdout_path.open("ab", buffering=0) as stdout_handle, stderr_path.open(
        "ab", buffering=0
    ) as stderr_handle:
        started_utc = utc_now()
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            startupinfo=startupinfo,
            creationflags=creationflags,
            close_fds=True,
        )
        pid = int(process.pid)
        return_code = int(process.wait())
        memory = _child_process_memory_record(process)
        finished_utc = utc_now()
    return pid, return_code, {
        "schema": "cable-pref-child-process-exit-v1",
        "pid": pid,
        "return_code": return_code,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "memory": dict(memory),
    }


def execution_environment() -> Mapping[str, str]:
    result = {name: "1" for name in THREAD_VARIABLES}
    result.update(
        {
            "CUDA_VISIBLE_DEVICES": "-1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_PROGRESS_BARS": "1",
            "TQDM_DISABLE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    return result


def environment_sha256(values: Mapping[str, str]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(values)))


def verify_config_contract(config: Mapping[str, Any]) -> None:
    """Bind the machine-readable constants that determine replay semantics."""

    if config.get("protocol_name") != "cable-pref-ml10m-poc-v1-preregistered":
        raise IntegrityError("Unexpected CABLE-PREF protocol name")
    if tuple(config.get("optimization_seeds", ())) != EXPECTED_SEEDS:
        raise IntegrityError("Optimization seed inventory changed")
    dataset = require_mapping(config.get("dataset"), "config.dataset")
    if (
        int(dataset.get("expected_archive_size_bytes", -1)) != 65_566_137
        or str(dataset.get("expected_archive_sha256", "")).lower()
        != "813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862"
        or str(dataset.get("expected_official_sidecar_md5", "")).lower()
        != "ce571fd55effeba0271552578f2648bd"
        or tuple(dataset.get("allowed_members", ()))
        != ("ml-10M100K/ratings.dat", "ml-10M100K/movies.dat")
    ):
        raise IntegrityError("Dataset archive/input binding changed")
    loading = require_mapping(dataset.get("loading"), "config.dataset.loading")
    if loading.get("strategy") != "one_structural_pass_plus_stage_authorized_rescans":
        raise IntegrityError("Dataset loading strategy differs from the reconciled lock")
    if tuple(loading.get("stage_rescans", ())) != (
        "A_eligibility_and_value_rescan_before_final_cohort_lock",
        "R_after_R_base_manifest",
        "V_binary_relevance_after_V_manifest",
        "V_exact_preference_after_choices_freeze",
        "T_after_T_manifest",
    ):
        raise IntegrityError("Stage-authorized rescan inventory/order changed")
    if (
        loading.get("pass_1")
        != "structural_user_summaries_and_timestamp_group_layouts_only_without_rating_payload_retention"
        or loading.get("structural_candidates_after_pass_1") is not True
        or loading.get("final_cohort_after_A_only_eligibility_rescan") is not True
        or loading.get("stage_rescan_policy")
        != "parse_selected_users_current_stage_only_and_verify_pass_1_layout"
        or loading.get("forbid_all_ratings_in_memory") is not True
    ):
        raise IntegrityError("Outcome-blind loader semantics changed")
    eligibility = require_mapping(
        dataset.get("eligibility"), "config.dataset.eligibility"
    )
    if (
        int(eligibility.get("minimum_total_events", -1)) != 80
        or int(eligibility.get("minimum_timestamp_groups", -1)) != 4
        or int(eligibility.get("minimum_A_events", -1)) != 20
        or int(eligibility.get("minimum_distinct_positive_A_items", -1)) != 5
        or float(eligibility.get("positive_rating_min", float("nan"))) != 4.0
        or int(
            eligibility.get("minimum_semantic_catalog_minus_A_R_V_event_count", -1)
        )
        != 700
    ):
        raise IntegrityError("Cohort eligibility constants changed")
    cohort = require_mapping(dataset.get("cohort"), "config.dataset.cohort")
    if (
        cohort.get("eligible_user_hash_format") != "20260835:{user_id}"
        or int(cohort.get("required_users", -1)) != 2000
        or cohort.get("fewer_users_policy") != "fail_closed"
    ):
        raise IntegrityError("Cohort selection contract changed")
    controls = require_mapping(config.get("controls"), "config.controls")
    if tuple(controls.get("registered_methods_in_fixed_order", ())) != EXPECTED_METHODS:
        raise IntegrityError("Registered method inventory/order changed")
    bpr = require_mapping(config.get("bpr"), "config.bpr")
    if require_int(
        bpr.get("maximum_training_examples_per_epoch"),
        "config.bpr.maximum_training_examples_per_epoch",
    ) != 200_000:
        raise IntegrityError("BPR training cap differs from the protocol")
    if (
        int(bpr.get("embedding_dimension", -1)) != 64
        or int(bpr.get("epochs", -1)) != 8
        or int(bpr.get("training_seed", -1)) != 20260835
        or float(bpr.get("positive_rating_min", float("nan"))) != 4.0
    ):
        raise IntegrityError("BPR geometry/schedule changed")
    retrieval = require_mapping(config.get("retrieval"), "config.retrieval")
    if (
        int(retrieval.get("collaborative_candidates_exact", -1)) != 200
        or int(retrieval.get("semantic_candidates_exact", -1)) != 200
        or int(retrieval.get("union_candidates_exact", -1)) != 400
    ):
        raise IntegrityError("Exact 200+200 retrieval contract changed")
    if (
        retrieval.get("semantic_index_kind") != "IndexFlatIP"
        or retrieval.get("collaborative_index_kind") != "IndexFlatIP"
        or retrieval.get("canonical_score_dtype") != "float32"
        or retrieval.get("outcome_backend")
        != "faiss_full_result_row_then_request_mask_and_stable_rerank"
        or int(retrieval.get("manifest_query_batch_size", -1)) != 64
        or int(retrieval.get("minimum_semantic_complement_slack", -1)) != 500
        or retrieval.get("underfill_policy")
        != "fail_closed_before_target_access"
    ):
        raise IntegrityError("Exact retrieval/oracle semantics changed")
    ranking = require_mapping(config.get("ranking"), "config.ranking")
    if tuple(ranking.get("alpha_validation_grid", ())) != EXPECTED_ALPHAS:
        raise IntegrityError("Shared validation alpha grid changed")
    alignment = require_mapping(config.get("alignment"), "config.alignment")
    if (
        int(alignment.get("epochs", -1)) != 12
        or float(alignment.get("beta", float("nan"))) != 5.0
        or float(alignment.get("admission_margin", float("nan"))) != 0.02
        or float(alignment.get("order_margin", float("nan"))) != 0.10
    ):
        raise IntegrityError("Reference-free alignment constants changed")
    evaluation = require_mapping(config.get("evaluation"), "config.evaluation")
    if (
        evaluation.get("pair_hash_format")
        != "20263503:{user_id}:{low_item_id}:{high_item_id}"
        or int(evaluation.get("maximum_pairs_per_user", -1)) != 100
        or float(evaluation.get("minimum_pair_rating_gap", float("nan"))) != 2.0
        or int(evaluation.get("bootstrap_draws", -1)) != 10_000
        or float(evaluation.get("bootstrap_alpha", float("nan"))) != 0.05
        or int(evaluation.get("bootstrap_seed", -1)) != 20263504
        or evaluation.get("bootstrap_interval")
        != "two_sided_percentile_2.5_and_97.5"
        or evaluation.get("paired_comparison_users")
        != "finite_common_user_intersection"
    ):
        raise IntegrityError("Evaluation/bootstrap semantics changed")
    power = require_mapping(config.get("power_audit"), "config.power_audit")
    power_seeds = require_mapping(
        power.get("experiment_seeds"), "config.power_audit.experiment_seeds"
    )
    if (
        int(power.get("maximum_pairs_per_user", -1)) != 100
        or power.get("center_observed_user_differences_before_injection") is not True
        or power.get("clip_centered_differences") is not False
        or int(power.get("bootstrap_experiments", -1)) != 1000
        or int(power.get("inner_user_bootstrap_draws", -1)) != 1000
        or float(power.get("bootstrap_alpha", float("nan"))) != 0.05
        or float(power.get("minimum_detection_fraction_each", float("nan")))
        != 0.8
        or dict(power_seeds)
        != {
            "admission_vs_raw": 20263505,
            "admission_vs_order_only": 20263506,
            "spce_vs_raw": 20263507,
            "spce_vs_bpr": 20263508,
        }
    ):
        raise IntegrityError("Validation power-audit contract changed")
    latency = require_mapping(config.get("latency"), "config.latency")
    if latency.get("request_hash_format") != "20263509:latency:{user_id}":
        raise IntegrityError("Latency cohort hash changed")
    if (
        int(latency.get("measured_requests_exact", -1)) != 512
        or int(latency.get("cpu_threads", -1)) != 1
        or int(latency.get("warmups", -1)) != 32
        or int(latency.get("repetitions", -1)) != 7
        or latency.get("p95_quantile_method") != "higher"
        or float(latency.get("maximum_p95_ms", float("nan"))) != 10.0
        or float(latency.get("maximum_p95_ratio", float("nan"))) != 1.25
        or set(latency.get("record_hardware", ()))
        != {
            "cpu_model",
            "logical_core_count",
            "process_affinity",
            "python_faiss_blas_versions",
            "visible_power_policy_metadata",
        }
    ):
        raise IntegrityError("Latency measurement contract changed")
    execution = require_mapping(config.get("execution"), "config.execution")
    if execution.get("sole_authoritative_marker_prefix") != EXTERNAL_MARKER_PREFIX:
        raise IntegrityError("External marker prefix differs from configuration")
    if execution.get("sole_authoritative_marker_schema") != (
        "cable-pref-external-complete-v1"
    ):
        raise IntegrityError("External marker schema differs from configuration")
    promise = require_mapping(config.get("promise_gate"), "config.promise_gate")
    if not set(GATE_NAMES).issubset(promise):
        raise IntegrityError("Configuration does not contain all G1-G9 gates")
    g2 = require_mapping(promise["G2"], "config.promise_gate.G2")
    g3 = require_mapping(promise["G3"], "config.promise_gate.G3")
    g4 = require_mapping(promise["G4"], "config.promise_gate.G4")
    g6 = require_mapping(promise["G6"], "config.promise_gate.G6")
    g7 = require_mapping(promise["G7"], "config.promise_gate.G7")
    if (
        require_mapping(
            g2.get("conditional_admission_minimum_point_gain"), "G2 gains"
        )
        != {"raw_hybrid": 0.02, "order_only": 0.01}
        or float(g2.get("net_new_preferred_support_minimum_point_gain_over_raw", -1))
        != 0.01
        or float(g3.get("spce_at_10_minimum_point_gain_each", -1)) != 0.005
        or float(g4.get("minimum_ndcg_at_10_point_delta", float("nan")))
        != -0.0002
        or float(g4.get("minimum_ndcg_at_10_lower_bound_strict", float("nan")))
        != -0.001
        or float(g4.get("minimum_recall_at_10_lower_bound_strict", float("nan")))
        != -0.002
        or float(
            g4.get("maximum_low_rating_intrusion_at_10_increase_upper_bound", float("nan"))
        )
        != 0.002
        or int(g6.get("minimum_R_fixed_pairs", -1)) != 20_000
        or int(g6.get("minimum_R_pair_bearing_users", -1)) != 1000
        or int(g6.get("minimum_T_fixed_natural_pairs", -1)) != 5000
        or int(g6.get("minimum_T_pair_bearing_users", -1)) != 1000
        or int(g6.get("minimum_T_unique_BPR_missed_preferred_endpoints", -1))
        != 5000
        or int(g6.get("minimum_T_missed_endpoint_users", -1)) != 1000
        or float(
            g6.get("minimum_admission_membership_changed_vs_raw_fraction", -1)
        )
        != 0.05
        or float(g6.get("minimum_spce_pair_outcome_changed_vs_raw_fraction", -1))
        != 0.02
        or int(g7.get("minimum_independently_stable_seeds", -1)) != 2
        or g7.get("stable_seed_ndcg_comparator") != "raw_hybrid"
        or float(g7.get("stable_seed_minimum_ndcg_delta", float("nan")))
        != -0.0002
        or float(g7.get("minimum_any_seed_ndcg_delta", float("nan"))) != -0.001
    ):
        raise IntegrityError("Registered G2-G7 thresholds changed")


def safe_run_id(value: str) -> str:
    if Path(value).name != value or value in {"", ".", ".."}:
        raise ValueError("run-id must be one safe path component")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if any(character not in allowed for character in value):
        raise ValueError("run-id contains an unsafe character")
    return value


def locked_paths(project_root: Path) -> Mapping[str, Path]:
    return {
        "launcher": Path(__file__).resolve(),
        "runner": (project_root / "src" / "cable_pref_poc.py").resolve(),
        "config": (
            project_root / "src" / "configs" / "cable_pref_poc_ml10m_v1.json"
        ).resolve(),
        "protocol": (
            project_root / "experiments" / "cable-pref-protocol-v1.md"
        ).resolve(),
        "research_question": (
            project_root / "literature" / "research-question-cycle5.md"
        ).resolve(),
        "cycle5_survey": (
            project_root / "literature" / "cycle5-survey-and-ideation.md"
        ).resolve(),
        "architecture": (
            project_root / "literature" / "cable-pref-architecture.md"
        ).resolve(),
    }


def verify_frozen_source_files(paths: Mapping[str, Path]) -> None:
    for name, expected in FROZEN_SOURCE_SHA256.items():
        path = paths.get(name)
        if path is None or not path.is_file() or sha256_file(path) != expected:
            raise IntegrityError(f"Prospectively frozen source differs: {name}")


def find_sole_runner_candidate(run_directory: Path) -> Path:
    matches = list(run_directory.glob(RUNNER_CANDIDATE_GLOB))
    if len(matches) != 1:
        raise IntegrityError(
            f"Expected one runner completion candidate, found {len(matches)}"
        )
    return matches[0].resolve()


@dataclass(frozen=True)
class CandidateClosure:
    candidate_path: Path
    candidate: Mapping[str, Any]
    result_path: Path
    raw_validation_path: Path
    raw_test_path: Path | None
    latency_path: Path | None
    runner_ledger: Path
    runner_lock: Path
    runner_pid: int
    termination_stage: str
    test_opened: bool
    artifact_hashes: Mapping[str, str]


@dataclass(frozen=True)
class ReplayEvent:
    user_id: int
    item_index: int
    movie_id: int
    rating: float
    timestamp: int
    ordinal: int


@dataclass(frozen=True)
class ReplayLayout:
    user_id: int
    counts: tuple[int, int, int, int]
    minimum_timestamps: tuple[int, int, int, int]
    maximum_timestamps: tuple[int, int, int, int]
    structural_hash: str


def _candidate_file(
    candidate: Mapping[str, Any],
    run_directory: Path,
    field: str,
    hash_field: str,
    label: str,
) -> Path:
    path = contained_file(run_directory, str(candidate.get(field, "")), label)
    expected = str(candidate.get(hash_field, "")).lower()
    if not is_sha256(expected) or sha256_file(path) != expected:
        raise IntegrityError(f"{label} dedicated hash mismatch")
    return path


def verify_candidate_closure(
    *,
    run_directory: Path,
    candidate_path: Path,
    source_hashes: Mapping[str, str],
    expected_archive_sha256: str,
) -> CandidateClosure:
    candidate = read_json_mapping(candidate_path, "runner completion candidate")
    if candidate.get("schema") != "cable-pref-runner-completion-candidate-v1":
        raise IntegrityError("Unexpected runner completion candidate schema")
    base_candidate_fields = {
        "schema",
        "created_utc",
        "run_directory",
        "pid",
        "runner_lock",
        "runner_lock_release_pending",
        "external_post_exit_verification_required",
        "source_sha256",
        "dataset_archive_sha256",
        "execution_fingerprint_sha256",
        "termination_stage",
        "test_opened",
        "asynchronous_error_ledger",
        "asynchronous_error_ledger_sha256",
        "artifact_sha256",
        "result_file",
        "result_sha256",
        "raw_validation_file",
        "raw_validation_sha256",
    }
    expected_candidate_fields = set(base_candidate_fields)
    if candidate.get("termination_stage") == "post_T_all_gates":
        expected_candidate_fields.update(
            {"raw_test_file", "raw_test_sha256", "latency_file", "latency_sha256"}
        )
    if set(candidate) != expected_candidate_fields:
        raise IntegrityError("Runner candidate field inventory changed")
    if Path(str(candidate.get("run_directory", ""))).resolve() != run_directory:
        raise IntegrityError("Runner candidate names a different run directory")
    runner_pid = int(candidate.get("pid", -1))
    if runner_pid <= 0 or pid_is_running(runner_pid):
        raise IntegrityError(f"Runner PID is active or invalid: {runner_pid}")
    if candidate.get("runner_lock_release_pending") is not True:
        raise IntegrityError("Runner did not declare lock release pending")
    if candidate.get("external_post_exit_verification_required") is not True:
        raise IntegrityError("Runner did not require post-exit verification")
    runner_lock_value = Path(str(candidate.get("runner_lock", "")))
    runner_lock = (
        runner_lock_value.resolve()
        if runner_lock_value.is_absolute()
        else (run_directory / runner_lock_value).resolve()
    )
    if runner_lock.exists():
        raise IntegrityError("Runner lock remains after process exit")

    candidate_sources = require_mapping(
        candidate.get("source_sha256"), "candidate.source_sha256"
    )
    required_sources = {
        "runner",
        "config",
        "protocol",
        "research_question",
        "cycle5_survey",
        "architecture",
    }
    if set(candidate_sources) != required_sources:
        raise IntegrityError("Candidate source inventory is incomplete or changed")
    for name in required_sources:
        if str(candidate_sources[name]).lower() != str(source_hashes[name]).lower():
            raise IntegrityError(f"Candidate {name} source hash mismatch")
    if str(candidate.get("dataset_archive_sha256", "")).lower() != str(
        expected_archive_sha256
    ).lower():
        raise IntegrityError("Candidate archive hash mismatch")
    execution_fingerprint = str(
        candidate.get("execution_fingerprint_sha256", "")
    ).lower()
    if (
        not is_sha256(execution_fingerprint)
        or candidate_path.name
        != f"CABLE_RUNNER_COMPLETE_CANDIDATE_{execution_fingerprint[:16]}.json"
    ):
        raise IntegrityError("Runner candidate filename/fingerprint binding differs")

    runner_ledger = contained_file(
        run_directory,
        str(candidate.get("asynchronous_error_ledger", "")),
        "runner asynchronous-error ledger",
    )
    if runner_ledger.stat().st_size != 0 or sha256_file(runner_ledger) != EMPTY_SHA256:
        raise IntegrityError("Runner asynchronous-error ledger is nonempty")
    if str(candidate.get("asynchronous_error_ledger_sha256", "")).lower() != EMPTY_SHA256:
        raise IntegrityError("Candidate ledger hash is not the empty-file hash")

    artifact_raw = require_mapping(
        candidate.get("artifact_sha256"), "candidate.artifact_sha256"
    )
    artifact_hashes: dict[str, str] = {}
    for relative_name, expected_hash in artifact_raw.items():
        name = str(relative_name)
        digest = str(expected_hash).lower()
        if not is_sha256(digest):
            raise IntegrityError(f"Malformed recursive artifact hash: {name}")
        path = contained_file(run_directory, name, "candidate-bound artifact")
        if sha256_file(path) != digest:
            raise IntegrityError(f"Candidate artifact hash mismatch: {name}")
        artifact_hashes[name] = digest
    actual = file_hash_manifest(run_directory, excluded=(candidate_path,))
    if dict(actual) != artifact_hashes:
        missing = sorted(set(artifact_hashes) - set(actual))
        extra = sorted(set(actual) - set(artifact_hashes))
        changed = sorted(
            name
            for name in set(actual) & set(artifact_hashes)
            if actual[name] != artifact_hashes[name]
        )
        raise IntegrityError(
            "Recursive candidate closure mismatch: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )

    result_path = _candidate_file(
        candidate, run_directory, "result_file", "result_sha256", "result file"
    )
    raw_validation_path = _candidate_file(
        candidate,
        run_directory,
        "raw_validation_file",
        "raw_validation_sha256",
        "raw validation arrays",
    )
    termination_stage = str(candidate.get("termination_stage", ""))
    test_opened = require_bool(candidate.get("test_opened"), "candidate.test_opened")
    raw_test_path: Path | None = None
    latency_path: Path | None = None
    if termination_stage == "pre_T_power_audit":
        if test_opened:
            raise IntegrityError("Pre-T candidate claims test_opened=true")
        forbidden = {
            "raw_test_file",
            "raw_test_sha256",
            "latency_file",
            "latency_sha256",
        }
        if forbidden & set(candidate):
            raise IntegrityError("Pre-T candidate binds test or latency artifacts")
    elif termination_stage == "post_T_all_gates":
        if not test_opened:
            raise IntegrityError("Post-T candidate claims test_opened=false")
        raw_test_path = _candidate_file(
            candidate,
            run_directory,
            "raw_test_file",
            "raw_test_sha256",
            "raw test arrays",
        )
        latency_path = _candidate_file(
            candidate,
            run_directory,
            "latency_file",
            "latency_sha256",
            "raw latency arrays",
        )
    else:
        raise IntegrityError(f"Unknown termination stage: {termination_stage!r}")

    return CandidateClosure(
        candidate_path=candidate_path,
        candidate=candidate,
        result_path=result_path,
        raw_validation_path=raw_validation_path,
        raw_test_path=raw_test_path,
        latency_path=latency_path,
        runner_ledger=runner_ledger,
        runner_lock=runner_lock,
        runner_pid=runner_pid,
        termination_stage=termination_stage,
        test_opened=test_opened,
        artifact_hashes=artifact_hashes,
    )


def _load_npz_exact(
    path: Path, required: Sequence[str], label: str
) -> Mapping[str, Any]:
    # Imported only after fixed environment variables have been validated.
    import numpy as np

    try:
        with np.load(path, allow_pickle=False) as archive:
            names = tuple(archive.files)
            if set(names) != set(required):
                raise IntegrityError(
                    f"{label} schema changed: missing={sorted(set(required)-set(names))}, "
                    f"extra={sorted(set(names)-set(required))}"
                )
            return {name: archive[name].copy() for name in names}
    except (OSError, ValueError) as exc:
        raise IntegrityError(f"Cannot load {label}: {path}") from exc


def _decode_scalar_string(value: Any, label: str) -> str:
    import numpy as np

    array = np.asarray(value)
    if array.size != 1:
        raise IntegrityError(f"{label} must be one scalar string")
    item = array.reshape(-1)[0]
    if isinstance(item, bytes):
        return item.decode("utf-8")
    return str(item)


def _decode_strings(value: Any, label: str) -> tuple[str, ...]:
    import numpy as np

    array = np.asarray(value)
    if array.ndim != 1:
        raise IntegrityError(f"{label} must be a one-dimensional string array")
    result: list[str] = []
    for raw in array:
        if isinstance(raw, bytes):
            result.append(raw.decode("utf-8"))
        else:
            result.append(str(raw))
    return tuple(result)


def _scalar_int(value: Any, label: str) -> int:
    import numpy as np

    array = np.asarray(value)
    if array.size != 1 or array.dtype.kind not in "iub":
        raise IntegrityError(f"{label} must be one integer scalar")
    return int(array.reshape(-1)[0])


def _scalar_float(value: Any, label: str) -> float:
    import numpy as np

    array = np.asarray(value)
    if array.size != 1:
        raise IntegrityError(f"{label} must be one numeric scalar")
    result = float(array.reshape(-1)[0])
    if not math.isfinite(result):
        raise IntegrityError(f"{label} must be finite")
    return result


def _scalar_bool(value: Any, label: str) -> bool:
    integer = _scalar_int(value, label)
    if integer not in (0, 1):
        raise IntegrityError(f"{label} must be encoded as zero or one")
    return bool(integer)


def _same_array(
    left: Any,
    right: Any,
    label: str,
    *,
    rtol: float = 0.0,
    atol: float = 0.0,
) -> None:
    import numpy as np

    first = np.asarray(left)
    second = np.asarray(right)
    if first.shape != second.shape:
        raise IntegrityError(
            f"{label} shape mismatch: {first.shape} != {second.shape}"
        )
    if first.dtype.kind in "fc" or second.dtype.kind in "fc":
        same = np.allclose(first, second, rtol=rtol, atol=atol, equal_nan=True)
    else:
        same = np.array_equal(first, second)
    if not bool(same):
        raise IntegrityError(f"{label} values differ")


def _array_memory_sha256(value: Any) -> str:
    import numpy as np

    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(canonical_json_bytes(list(array.shape)))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _load_npy_exact(path: Path, label: str) -> Any:
    import numpy as np

    try:
        value = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise IntegrityError(f"Cannot load {label}: {path}") from exc
    if not isinstance(value, np.ndarray):
        raise IntegrityError(f"{label} is not one NumPy array")
    return value


def _raw_scalar_path_and_hash(
    raw: Mapping[str, Any],
    run_directory: Path,
    file_field: str,
    hash_field: str,
    label: str,
) -> Path:
    name = _decode_scalar_string(raw[file_field], file_field)
    path = contained_file(run_directory, name, label)
    expected = _decode_scalar_string(raw[hash_field], hash_field).lower()
    if not is_sha256(expected) or sha256_file(path) != expected:
        raise IntegrityError(f"{label} hash differs from raw binding")
    return path


def _verify_common_raw_contract(
    raw: Mapping[str, Any],
    *,
    schema: str,
    protocol_fingerprint: str,
    execution_fingerprint: str,
) -> tuple[Any, Any]:
    import numpy as np

    if _decode_scalar_string(raw["schema"], "raw schema") != schema:
        raise IntegrityError(f"Unexpected raw schema: expected {schema}")
    if (
        _decode_scalar_string(
            raw["protocol_fingerprint_sha256"], "raw protocol fingerprint"
        )
        != protocol_fingerprint
    ):
        raise IntegrityError("Raw protocol fingerprint differs")
    if (
        _decode_scalar_string(
            raw["execution_fingerprint_sha256"], "raw execution fingerprint"
        )
        != execution_fingerprint
    ):
        raise IntegrityError("Raw execution fingerprint differs")
    if _decode_strings(raw["methods"], "raw methods") != EXPECTED_METHODS:
        raise IntegrityError("Raw method inventory/order changed")
    if tuple(map(int, np.asarray(raw["seeds"]).tolist())) != EXPECTED_SEEDS:
        raise IntegrityError("Raw seed inventory/order changed")
    if _decode_strings(raw["metrics"], "raw metrics") != EXPECTED_METRICS:
        raise IntegrityError("Raw metric inventory/order changed")
    if not np.array_equal(
        np.asarray(raw["alphas"], dtype=np.float32),
        np.asarray(EXPECTED_ALPHAS, dtype=np.float32),
    ):
        raise IntegrityError("Raw alpha grid changed")
    user_ids = np.asarray(raw["user_ids"], dtype=np.int64)
    movie_ids = np.asarray(raw["catalog_movie_ids"], dtype=np.int64)
    if (
        user_ids.ndim != 1
        or user_ids.size != 2000
        or len(set(map(int, user_ids))) != user_ids.size
    ):
        raise IntegrityError("Raw cohort must contain 2,000 unique users")
    if (
        movie_ids.ndim != 1
        or movie_ids.size < 700
        or len(set(map(int, movie_ids))) != movie_ids.size
        or np.any(movie_ids <= 0)
        or not np.all(movie_ids[:-1] < movie_ids[1:])
    ):
        raise IntegrityError("Raw catalog IDs are not unique positive sorted IDs")
    return user_ids, movie_ids


def _safe_zip_member(name: str) -> PurePosixPath:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise IntegrityError(f"Unsafe authenticated ZIP member path: {name!r}")
    return pure


def _authorized_zip_inputs(archive: Path) -> tuple[zipfile.ZipInfo, zipfile.ZipInfo]:
    selected: dict[str, zipfile.ZipInfo] = {}
    exact_members = {
        "ratings.dat": "ml-10M100K/ratings.dat",
        "movies.dat": "ml-10M100K/movies.dat",
    }
    try:
        with zipfile.ZipFile(archive, "r") as handle:
            for member in handle.infolist():
                pure = _safe_zip_member(member.filename)
                unix_mode = (member.external_attr >> 16) & 0o170000
                if unix_mode == 0o120000:
                    raise IntegrityError("Authenticated ZIP contains a symlink")
                if member.flag_bits & 0x1:
                    raise IntegrityError("Authenticated ZIP contains encryption")
                if pure.name in {"ratings.dat", "movies.dat"}:
                    if pure.as_posix() != exact_members[pure.name]:
                        raise IntegrityError(
                            f"Required-member basename alias is forbidden: {member.filename}"
                        )
                    if pure.name in selected or member.is_dir():
                        raise IntegrityError(
                            f"Authenticated ZIP has ambiguous {pure.name}"
                        )
                    selected[pure.name] = member
    except (OSError, zipfile.BadZipFile) as exc:
        raise IntegrityError("Cannot inspect authenticated MovieLens archive") from exc
    if set(selected) != {"ratings.dat", "movies.dat"}:
        raise IntegrityError("Authenticated ZIP lacks the exact required inputs")
    return selected["movies.dat"], selected["ratings.dat"]


def _read_archive_catalog(archive: Path, member: zipfile.ZipInfo) -> tuple[Any, ...]:
    movie_ids: list[int] = []
    seen: set[int] = set()
    try:
        with zipfile.ZipFile(archive, "r") as handle, handle.open(member, "r") as binary:
            with io.TextIOWrapper(
                binary, encoding="utf-8", errors="strict", newline=""
            ) as text_handle:
                for line in text_handle:
                    fields = line.rstrip("\r\n").split("::", 2)
                    if len(fields) != 3:
                        raise IntegrityError("Malformed authenticated movies.dat row")
                    movie_id = int(fields[0])
                    if movie_id <= 0 or not fields[1] or not fields[2] or movie_id in seen:
                        raise IntegrityError("Invalid authenticated movies.dat field")
                    seen.add(movie_id)
                    movie_ids.append(movie_id)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        if isinstance(exc, IntegrityError):
            raise
        raise IntegrityError("Cannot parse authenticated movies.dat") from exc
    movie_ids.sort()
    if len(movie_ids) < 700:
        raise IntegrityError("Authenticated semantic catalog is too small")
    return tuple(movie_ids)


def _parse_rating_skeleton(line: str, ordinal: int) -> tuple[int, int, int, str]:
    fields = line.rstrip("\r\n").split("::")
    if len(fields) != 4:
        raise IntegrityError("Malformed authenticated ratings.dat row")
    try:
        user_id = int(fields[0])
        timestamp = int(fields[3])
    except ValueError as exc:
        raise IntegrityError("Invalid ratings.dat user/timestamp") from exc
    if user_id <= 0 or timestamp < 0:
        raise IntegrityError("Invalid ratings.dat user/timestamp")
    return user_id, timestamp, ordinal, line


def _nearest_split_boundary(
    cumulative: Sequence[int], target: float, low: int, high: int
) -> int:
    if low > high:
        raise IntegrityError("No feasible timestamp-group split boundary")
    return min(
        range(low, high + 1),
        key=lambda index: (abs(cumulative[index - 1] - target), index),
    )


def _split_rating_rows(
    rows: Sequence[tuple[int, int, int, str]],
) -> tuple[tuple[tuple[int, int, int, str], ...], ...]:
    if not rows:
        raise IntegrityError("Cannot split an empty authenticated user")
    ordered = sorted(rows, key=lambda row: (row[1], row[2]))
    groups: list[list[tuple[int, int, int, str]]] = []
    for row in ordered:
        if not groups or groups[-1][0][1] != row[1]:
            groups.append([row])
        else:
            groups[-1].append(row)
    if len(groups) < 4:
        return (tuple(), tuple(), tuple(), tuple())
    cumulative: list[int] = []
    running = 0
    for group in groups:
        running += len(group)
        cumulative.append(running)
    total = len(ordered)
    a_cut = _nearest_split_boundary(cumulative, 0.60 * total, 1, len(groups) - 3)
    r_cut = _nearest_split_boundary(
        cumulative, 0.80 * total, a_cut + 1, len(groups) - 2
    )
    v_cut = _nearest_split_boundary(
        cumulative, 0.90 * total, r_cut + 1, len(groups) - 1
    )
    blocks = (
        tuple(value for group in groups[:a_cut] for value in group),
        tuple(value for group in groups[a_cut:r_cut] for value in group),
        tuple(value for group in groups[r_cut:v_cut] for value in group),
        tuple(value for group in groups[v_cut:] for value in group),
    )
    if any(not block for block in blocks):
        raise IntegrityError("Authenticated temporal split produced an empty block")
    minimums = tuple(min(row[1] for row in block) for block in blocks)
    maximums = tuple(max(row[1] for row in block) for block in blocks)
    if not all(maximums[index] < minimums[index + 1] for index in range(3)):
        raise IntegrityError("Authenticated timestamp groups cross a split boundary")
    return blocks


def _layout_from_rows(
    user_id: int,
    blocks: Sequence[Sequence[tuple[int, int, int, str]]],
) -> ReplayLayout:
    counts = tuple(len(block) for block in blocks)
    minimums = tuple(min(row[1] for row in block) for block in blocks)
    maximums = tuple(max(row[1] for row in block) for block in blocks)
    structural = {
        "user_id": user_id,
        "counts": counts,
        "minimum_timestamps": minimums,
        "maximum_timestamps": maximums,
    }
    return ReplayLayout(
        user_id,
        counts,
        minimums,
        maximums,
        sha256_bytes(canonical_json_bytes(structural)),
    )


def _parse_replay_event(
    row: tuple[int, int, int, str], movie_to_index: Mapping[int, int]
) -> ReplayEvent:
    fields = row[3].rstrip("\r\n").split("::")
    if len(fields) != 4:
        raise IntegrityError("Malformed authenticated ratings.dat row")
    try:
        user_id = int(fields[0])
        movie_id = int(fields[1])
        rating = float(fields[2])
        timestamp = int(fields[3])
    except ValueError as exc:
        raise IntegrityError("Invalid authenticated ratings.dat value") from exc
    if user_id != row[0] or timestamp != row[1] or movie_id not in movie_to_index:
        raise IntegrityError("Authenticated skeleton/full parse disagrees")
    if (
        not math.isfinite(rating)
        or rating < 0.5
        or rating > 5.0
        or not math.isclose(rating * 2.0, round(rating * 2.0))
    ):
        raise IntegrityError("Authenticated rating is not a valid half-star value")
    return ReplayEvent(
        user_id,
        movie_to_index[movie_id],
        movie_id,
        rating,
        timestamp,
        row[2],
    )


def _replay_archive_cohort(
    archive: Path,
) -> tuple[
    tuple[int, ...],
    tuple[int, ...],
    Mapping[int, ReplayLayout],
    int,
    Mapping[str, Mapping[int, tuple[ReplayEvent, ...]]],
]:
    """Independently reconstruct the registered cohort and temporal blocks."""

    movies_member, ratings_member = _authorized_zip_inputs(archive)
    movie_ids = _read_archive_catalog(archive, movies_member)
    movie_to_index = {movie_id: index for index, movie_id in enumerate(movie_ids)}
    limit = 2000
    heap: list[tuple[int, int, int, ReplayLayout]] = []
    eligible_count = 0
    completed_users: set[int] = set()

    def consider(rows: list[tuple[int, int, int, str]]) -> None:
        nonlocal eligible_count
        if not rows:
            return
        blocks = _split_rating_rows(rows)
        if len(blocks) != 4 or any(not block for block in blocks):
            return
        total = sum(map(len, blocks))
        timestamp_count = len({row[1] for block in blocks for row in block})
        if total < 80 or timestamp_count < 4 or len(blocks[0]) < 20:
            return
        a_events = tuple(
            _parse_replay_event(row, movie_to_index) for row in blocks[0]
        )
        if len({event.item_index for event in a_events}) != len(a_events):
            raise IntegrityError("Authenticated A block repeats an item")
        if len({event.item_index for event in a_events if event.rating >= 4.0}) < 5:
            return
        if len(movie_ids) - (len(blocks[0]) + len(blocks[1]) + len(blocks[2])) < 700:
            return
        user_id = a_events[0].user_id
        layout = _layout_from_rows(user_id, blocks)
        eligible_count += 1
        key = int(
            hashlib.sha256(f"20260835:{user_id}".encode("ascii")).hexdigest(), 16
        )
        entry = (-key, -user_id, user_id, layout)
        if len(heap) < limit:
            heapq.heappush(heap, entry)
        else:
            current_largest = (-heap[0][0], -heap[0][1])
            if (key, user_id) < current_largest:
                heapq.heapreplace(heap, entry)

    current_user: int | None = None
    current_rows: list[tuple[int, int, int, str]] = []
    try:
        with zipfile.ZipFile(archive, "r") as handle, handle.open(
            ratings_member, "r"
        ) as binary:
            with io.TextIOWrapper(
                binary, encoding="utf-8", errors="strict", newline=""
            ) as text_handle:
                for ordinal, line in enumerate(text_handle):
                    row = _parse_rating_skeleton(line, ordinal)
                    if current_user is None:
                        current_user = row[0]
                    if row[0] != current_user:
                        if row[0] in completed_users:
                            raise IntegrityError("Authenticated ratings are not user-grouped")
                        consider(current_rows)
                        completed_users.add(current_user)
                        current_user, current_rows = row[0], []
                    current_rows.append(row)
    except (OSError, UnicodeError, zipfile.BadZipFile) as exc:
        raise IntegrityError("Cannot scan authenticated ratings.dat") from exc
    consider(current_rows)
    if len(heap) != limit:
        raise IntegrityError(f"Authenticated cohort has only {len(heap)} eligible users")
    records = [(entry[2], entry[3]) for entry in heap]
    records.sort(
        key=lambda value: (
            int(
                hashlib.sha256(f"20260835:{value[0]}".encode("ascii")).hexdigest(),
                16,
            ),
            value[0],
        )
    )
    user_ids = tuple(record[0] for record in records)
    layouts = {record[0]: record[1] for record in records}
    selected = frozenset(user_ids)
    selected_rows: dict[int, tuple[tuple[tuple[int, int, int, str], ...], ...]] = {}

    def retain(rows: list[tuple[int, int, int, str]]) -> None:
        if not rows or rows[0][0] not in selected:
            return
        user_id = rows[0][0]
        blocks = _split_rating_rows(rows)
        if _layout_from_rows(user_id, blocks) != layouts[user_id]:
            raise IntegrityError("Authenticated second scan changed temporal layout")
        selected_rows[user_id] = blocks

    current_user = None
    current_rows = []
    try:
        with zipfile.ZipFile(archive, "r") as handle, handle.open(
            ratings_member, "r"
        ) as binary:
            with io.TextIOWrapper(
                binary, encoding="utf-8", errors="strict", newline=""
            ) as text_handle:
                for ordinal, line in enumerate(text_handle):
                    row = _parse_rating_skeleton(line, ordinal)
                    if current_user is None:
                        current_user = row[0]
                    if row[0] != current_user:
                        retain(current_rows)
                        current_user, current_rows = row[0], []
                    if row[0] in selected:
                        current_rows.append(row)
    except (OSError, UnicodeError, zipfile.BadZipFile) as exc:
        raise IntegrityError("Cannot rescan authenticated ratings.dat") from exc
    retain(current_rows)
    if set(selected_rows) != set(selected):
        raise IntegrityError("Authenticated rescan omitted a selected user")
    stages: dict[str, dict[int, tuple[ReplayEvent, ...]]] = {
        stage: {} for stage in ("A", "R", "V", "T")
    }
    for user_id in user_ids:
        for index, stage in enumerate(("A", "R", "V", "T")):
            events = tuple(
                _parse_replay_event(row, movie_to_index)
                for row in selected_rows[user_id][index]
            )
            if len({event.item_index for event in events}) != len(events):
                raise IntegrityError(f"Authenticated {stage} block repeats an item")
            stages[stage][user_id] = events
        all_items = [
            event.item_index
            for stage in ("A", "R", "V", "T")
            for event in stages[stage][user_id]
        ]
        if len(set(all_items)) != len(all_items):
            raise IntegrityError("Authenticated user/movie repeats across temporal stages")
    return movie_ids, user_ids, layouts, eligible_count, stages


def _require_shape(value: Any, shape: Sequence[int], label: str) -> None:
    import numpy as np

    actual = tuple(np.asarray(value).shape)
    if actual != tuple(shape):
        raise IntegrityError(f"{label} shape {actual} != {tuple(shape)}")


def _require_finite(value: Any, label: str) -> None:
    import numpy as np

    if not np.isfinite(np.asarray(value)).all():
        raise IntegrityError(f"{label} contains a nonfinite value")


def _quantile_scale(values: Any) -> Any:
    import numpy as np

    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise IntegrityError("Quantile scaling requires one finite score row")
    lower = np.quantile(array, 0.05, method="linear")
    upper = np.quantile(array, 0.95, method="linear")
    denominator = max(float(upper - lower), 1.0e-6)
    return np.asarray(
        np.clip((array - np.float32(lower)) / np.float32(denominator), 0.0, 1.0),
        dtype=np.float32,
    )


def _stable_rank(item_indices: Any, scores: Any, movie_ids: Any) -> tuple[int, ...]:
    import numpy as np

    items = np.asarray(item_indices, dtype=np.int64)
    values = np.asarray(scores, dtype=np.float32)
    catalog_ids = np.asarray(movie_ids, dtype=np.int64)
    if items.ndim != 1 or values.shape != items.shape:
        raise IntegrityError("Stable ranking inputs have incompatible shapes")
    if np.any(items < 0) or np.any(items >= catalog_ids.size):
        raise IntegrityError("Stable ranking contains an out-of-catalog item")
    if len(set(map(int, items))) != items.size or not np.isfinite(values).all():
        raise IntegrityError("Stable ranking inputs are duplicated or nonfinite")
    order = np.lexsort((catalog_ids[items], -values))
    return tuple(map(int, items[order]))


def _expected_natural_pairs(
    events_by_user: Mapping[int, Sequence[ReplayEvent]], stage: str
) -> tuple[tuple[tuple[int, int, int, int, int], ...], Mapping[str, Any]]:
    per_user_cap = 32 if stage == "R" else 100
    by_user: dict[int, list[tuple[str, tuple[int, int, int, int, int]]]] = {}
    raw_pairs = 0
    raw_users = 0
    for user_id in sorted(events_by_user):
        events = sorted(
            events_by_user[user_id], key=lambda event: (event.movie_id, event.ordinal)
        )
        if len({event.item_index for event in events}) != len(events):
            raise IntegrityError(f"Replay {stage} pair universe repeats an item")
        rows: list[tuple[str, tuple[int, int, int, int, int]]] = []
        for left_index in range(len(events)):
            for right_index in range(left_index + 1, len(events)):
                left = events[left_index]
                right = events[right_index]
                difference = left.rating - right.rating
                if abs(difference) < 2.0:
                    continue
                preferred, rejected = (
                    (left, right) if difference > 0.0 else (right, left)
                )
                low_id = min(preferred.movie_id, rejected.movie_id)
                high_id = max(preferred.movie_id, rejected.movie_id)
                digest = hashlib.sha256(
                    f"20263503:{user_id}:{low_id}:{high_id}".encode("ascii")
                ).hexdigest()
                rows.append(
                    (
                        digest,
                        (
                            user_id,
                            preferred.item_index,
                            rejected.item_index,
                            low_id,
                            high_id,
                        ),
                    )
                )
        raw_pairs += len(rows)
        raw_users += int(bool(rows))
        rows.sort(key=lambda value: (value[0], value[1][3], value[1][4]))
        by_user[user_id] = rows[:per_user_cap]
    if stage == "R":
        round_rows: list[
            tuple[int, str, tuple[int, int, int, int, int]]
        ] = []
        for user_id, rows in by_user.items():
            del user_id
            for round_index, (digest, row) in enumerate(rows):
                round_rows.append((round_index, digest, row))
        round_rows.sort(key=lambda value: (value[0], value[1], value[2][0]))
        selected = tuple(value[2] for value in round_rows[:30_000])
    else:
        selected = tuple(
            row
            for user_id in sorted(by_user)
            for _digest, row in by_user[user_id]
        )
    identities = [(row[0], row[3], row[4]) for row in selected]
    if len(set(identities)) != len(identities):
        raise IntegrityError(f"Replay {stage} pair cap produced duplicates")
    return selected, {
        "stage": stage,
        "raw_pairs": int(raw_pairs),
        "raw_pair_users": int(raw_users),
        "selected_pairs": len(selected),
        "selected_pair_users": len({row[0] for row in selected}),
        "pair_identity_sha256": sha256_bytes(
            canonical_json_bytes(
                [[stage, user_id, low_id, high_id] for user_id, low_id, high_id in identities]
            )
        ),
    }


def _verify_stage_outcome_arrays(
    raw: Mapping[str, Any],
    *,
    prefix: str,
    user_ids: Any,
    movie_ids: Any,
    source_events: Mapping[int, Sequence[ReplayEvent]],
) -> tuple[tuple[tuple[int, int, int, int, int], ...], Mapping[str, Any]]:
    import numpy as np

    users = np.asarray(user_ids, dtype=np.int64)
    catalog = np.asarray(movie_ids, dtype=np.int64)
    event_items = np.asarray(raw[f"{prefix}_event_items"], dtype=np.int64)
    event_movie_ids = np.asarray(
        raw[f"{prefix}_event_movie_ids"], dtype=np.int64
    )
    event_ratings = np.asarray(raw[f"{prefix}_event_ratings"], dtype=np.float64)
    event_timestamps = np.asarray(
        raw[f"{prefix}_event_timestamps"], dtype=np.int64
    )
    event_ordinals = np.asarray(raw[f"{prefix}_event_ordinals"], dtype=np.int64)
    event_counts = np.asarray(raw[f"{prefix}_event_counts"], dtype=np.int64)
    event_shape = event_items.shape
    if (
        event_items.ndim != 2
        or event_shape[0] != users.size
        or event_movie_ids.shape != event_shape
        or event_ratings.shape != event_shape
        or event_timestamps.shape != event_shape
        or event_ordinals.shape != event_shape
        or event_counts.shape != (users.size,)
    ):
        raise IntegrityError(f"Raw {prefix} event-array shapes differ")
    replay_events: dict[int, tuple[ReplayEvent, ...]] = {}
    for user_row, raw_user_id in enumerate(users):
        user_id = int(raw_user_id)
        count = int(event_counts[user_row])
        if count < 0 or count > event_shape[1]:
            raise IntegrityError(f"Raw {prefix} event count is out of bounds")
        items = event_items[user_row, :count]
        ids = event_movie_ids[user_row, :count]
        ratings = event_ratings[user_row, :count]
        timestamps = event_timestamps[user_row, :count]
        ordinals = event_ordinals[user_row, :count]
        if (
            np.any(items < 0)
            or np.any(items >= catalog.size)
            or len(set(map(int, items))) != count
            or not np.isfinite(ratings).all()
            or np.any(ratings < 0.5)
            or np.any(ratings > 5.0)
            or not np.allclose(ratings * 2.0, np.rint(ratings * 2.0))
            or np.any(timestamps < 0)
            or np.any(ordinals < 0)
            or not np.array_equal(catalog[items], ids)
        ):
            raise IntegrityError(f"Raw {prefix} event row is invalid")
        if any(
            (int(timestamps[index]), int(ordinals[index]))
            >= (int(timestamps[index + 1]), int(ordinals[index + 1]))
            for index in range(max(0, count - 1))
        ):
            raise IntegrityError(f"Raw {prefix} events are not temporally ordered")
        if count < event_shape[1] and (
            not np.all(event_items[user_row, count:] == -1)
            or not np.all(event_movie_ids[user_row, count:] == -1)
            or not np.all(np.isnan(event_ratings[user_row, count:]))
            or not np.all(event_timestamps[user_row, count:] == -1)
            or not np.all(event_ordinals[user_row, count:] == -1)
        ):
            raise IntegrityError(f"Raw {prefix} event padding changed")
        replay = tuple(
            ReplayEvent(
                user_id,
                int(items[index]),
                int(ids[index]),
                float(ratings[index]),
                int(timestamps[index]),
                int(ordinals[index]),
            )
            for index in range(count)
        )
        expected = tuple(source_events[user_id])
        if replay != expected:
            raise IntegrityError(f"Raw {prefix} events differ from authenticated source")
        replay_events[user_id] = replay

    selected, diagnostics = _expected_natural_pairs(replay_events, prefix)
    by_user: dict[int, list[tuple[int, int, int, int, int]]] = {}
    for row in selected:
        by_user.setdefault(row[0], []).append(row)
    pair_preferred = np.asarray(raw[f"{prefix}_pair_preferred"], dtype=np.int64)
    pair_rejected = np.asarray(raw[f"{prefix}_pair_rejected"], dtype=np.int64)
    pair_low = np.asarray(raw[f"{prefix}_pair_low_movie_ids"], dtype=np.int64)
    pair_high = np.asarray(raw[f"{prefix}_pair_high_movie_ids"], dtype=np.int64)
    pair_counts = np.asarray(raw[f"{prefix}_pair_counts"], dtype=np.int64)
    pair_shape = pair_preferred.shape
    if (
        pair_preferred.ndim != 2
        or pair_shape != (users.size, 100)
        or pair_rejected.shape != pair_shape
        or pair_low.shape != pair_shape
        or pair_high.shape != pair_shape
        or pair_counts.shape != (users.size,)
    ):
        raise IntegrityError(f"Raw {prefix} pair-array shapes differ")
    for user_row, raw_user_id in enumerate(users):
        expected_rows = by_user.get(int(raw_user_id), [])
        count = int(pair_counts[user_row])
        if count != len(expected_rows):
            raise IntegrityError(f"Raw {prefix} pair count differs from replay")
        expected_preferred = [row[1] for row in expected_rows]
        expected_rejected = [row[2] for row in expected_rows]
        expected_low = [row[3] for row in expected_rows]
        expected_high = [row[4] for row in expected_rows]
        if (
            pair_preferred[user_row, :count].tolist() != expected_preferred
            or pair_rejected[user_row, :count].tolist() != expected_rejected
            or pair_low[user_row, :count].tolist() != expected_low
            or pair_high[user_row, :count].tolist() != expected_high
        ):
            raise IntegrityError(f"Raw {prefix} pair identities/directions differ")
        if count < 100 and not all(
            np.all(array[user_row, count:] == -1)
            for array in (pair_preferred, pair_rejected, pair_low, pair_high)
        ):
            raise IntegrityError(f"Raw {prefix} pair padding changed")
    recorded_identity = _decode_scalar_string(
        raw[f"{prefix}_pair_identity_sha256"], f"{prefix} pair identity"
    )
    if recorded_identity != diagnostics["pair_identity_sha256"]:
        raise IntegrityError(f"Raw {prefix} pair-identity hash differs")
    return selected, diagnostics


def _verify_faiss_matrix(path: Path, expected: Any, label: str) -> None:
    import numpy as np

    try:
        import faiss
    except ImportError as exc:
        raise IntegrityError("faiss-cpu is required for independent index replay") from exc
    try:
        index = faiss.read_index(str(path))
        matrix = np.ascontiguousarray(expected, dtype=np.float32)
        if (
            int(index.ntotal) != matrix.shape[0]
            or int(index.d) != matrix.shape[1]
            or int(index.metric_type) != int(faiss.METRIC_INNER_PRODUCT)
        ):
            raise IntegrityError(f"{label} index metadata differs from its matrix")
        reconstructed = np.asarray(index.reconstruct_n(0, int(index.ntotal)))
    except (RuntimeError, ValueError) as exc:
        if isinstance(exc, IntegrityError):
            raise
        raise IntegrityError(f"Cannot replay {label} serialized index") from exc
    if not np.array_equal(reconstructed, matrix):
        raise IntegrityError(f"{label} serialized index vectors differ from matrix")


def _verify_immutable_artifacts(
    *,
    raw: Mapping[str, Any],
    result: Mapping[str, Any],
    run_directory: Path,
    user_count: int,
    catalog_count: int,
) -> Mapping[str, Any]:
    import numpy as np

    records = require_mapping(result.get("immutable_records"), "immutable records")
    if set(records) != set(IMMUTABLE_NAMES):
        raise IntegrityError("Immutable artifact inventory changed")
    raw_fields = {
        "semantic_matrix": ("semantic_matrix_file", "semantic_matrix_sha256"),
        "semantic_index": ("semantic_index_file", "semantic_index_sha256"),
        "bpr_item_matrix": ("bpr_item_matrix_file", "bpr_item_matrix_sha256"),
        "bpr_index": ("bpr_index_file", "bpr_index_sha256"),
        "collaborative_mask": (
            "collaborative_mask_file",
            "collaborative_mask_sha256",
        ),
    }
    paths: dict[str, Path] = {}
    for name in IMMUTABLE_NAMES:
        record = require_mapping(records[name], f"immutable record {name}")
        if set(record) != {
            "file",
            "file_sha256_before",
            "memory_sha256_before",
            "file_sha256_after",
            "memory_sha256_after",
            "unchanged",
        }:
            raise IntegrityError(f"Immutable {name} record schema changed")
        path = contained_file(
            run_directory, str(record["file"]), f"immutable {name}"
        )
        digest = sha256_file(path)
        before = str(record["file_sha256_before"]).lower()
        after = str(record["file_sha256_after"]).lower()
        memory_before = str(record["memory_sha256_before"]).lower()
        memory_after = str(record["memory_sha256_after"]).lower()
        if (
            not all(is_sha256(value) for value in (before, after, memory_before, memory_after))
            or digest != before
            or before != after
            or memory_before != memory_after
            or record["unchanged"] is not True
        ):
            raise IntegrityError(f"Immutable {name} before/after binding failed")
        if name.endswith("index") and memory_before != digest:
            raise IntegrityError(f"Immutable {name} serialized memory hash differs")
        paths[name] = path
        if name in raw_fields:
            file_field, hash_field = raw_fields[name]
            raw_path = _raw_scalar_path_and_hash(
                raw, run_directory, file_field, hash_field, f"raw-bound {name}"
            )
            if raw_path != path or _decode_scalar_string(raw[hash_field], hash_field) != digest:
                raise IntegrityError(f"Raw/result immutable {name} bindings differ")

    semantic = _load_npy_exact(paths["semantic_matrix"], "semantic matrix")
    bpr_items = _load_npy_exact(paths["bpr_item_matrix"], "BPR item matrix")
    bpr_users = _load_npy_exact(paths["bpr_user_matrix"], "BPR user matrix")
    collaborative_mask = _load_npy_exact(
        paths["collaborative_mask"], "collaborative mask"
    )
    if semantic.dtype != np.float32 or semantic.shape != (catalog_count, 384):
        raise IntegrityError("Semantic matrix dtype/shape changed")
    if bpr_items.dtype != np.float32 or bpr_items.shape != (catalog_count, 64):
        raise IntegrityError("BPR item matrix dtype/shape changed")
    if bpr_users.dtype != np.float32 or bpr_users.shape != (user_count, 64):
        raise IntegrityError("BPR user matrix dtype/shape changed")
    if collaborative_mask.dtype != np.bool_ or collaborative_mask.shape != (
        catalog_count,
    ):
        raise IntegrityError("Collaborative-mask dtype/shape changed")
    for name, value in (
        ("semantic_matrix", semantic),
        ("bpr_item_matrix", bpr_items),
        ("bpr_user_matrix", bpr_users),
        ("collaborative_mask", collaborative_mask),
    ):
        record = require_mapping(records[name], f"immutable record {name}")
        if _array_memory_sha256(value) != str(record["memory_sha256_before"]):
            raise IntegrityError(f"Immutable {name} memory hash cannot be replayed")
    if (
        not np.isfinite(semantic).all()
        or not np.allclose(
            np.linalg.norm(semantic, axis=1), 1.0, rtol=0.0, atol=2.0e-5
        )
        or not np.isfinite(bpr_items).all()
        or not np.isfinite(bpr_users).all()
        or int(np.sum(collaborative_mask)) < 200
        or not np.all(bpr_items[~collaborative_mask] == 0.0)
    ):
        raise IntegrityError("Immutable representation invariants failed")
    _verify_faiss_matrix(paths["semantic_index"], semantic, "semantic")
    _verify_faiss_matrix(paths["bpr_index"], bpr_items, "BPR")
    bpr_state_path = contained_file(
        run_directory, "immutable/bpr_state.pt", "BPR state checkpoint"
    )
    try:
        import torch

        state = torch.load(bpr_state_path, map_location="cpu", weights_only=True)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise IntegrityError("Cannot independently load BPR state checkpoint") from exc
    if not isinstance(state, Mapping) or set(state) != {"users.weight", "items.weight"}:
        raise IntegrityError("BPR state checkpoint schema changed")
    state_users = np.ascontiguousarray(state["users.weight"].detach().cpu().numpy())
    state_items = np.ascontiguousarray(state["items.weight"].detach().cpu().numpy())
    if not np.array_equal(state_users, bpr_users) or not np.array_equal(
        state_items, bpr_items
    ):
        raise IntegrityError("BPR checkpoint factors differ from deployed matrices")
    if not np.all(state_items[~collaborative_mask] == 0.0):
        raise IntegrityError("BPR checkpoint has nonzero unsupported factors")
    return {
        "semantic_matrix": semantic,
        "bpr_item_matrix": bpr_items,
        "bpr_user_matrix": bpr_users,
        "collaborative_mask": collaborative_mask,
        "bpr_checkpoint_sha256": sha256_file(bpr_state_path),
        "paths": paths,
    }


def _verify_same_immutable_raw_binding(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> None:
    for stem in (
        "semantic_matrix",
        "semantic_index",
        "bpr_item_matrix",
        "bpr_index",
        "collaborative_mask",
    ):
        for suffix in ("file", "sha256"):
            field = f"{stem}_{suffix}"
            if _decode_scalar_string(first[field], field) != _decode_scalar_string(
                second[field], field
            ):
                raise IntegrityError(f"Validation/test immutable binding differs: {field}")


def _verify_exact_topk(
    *,
    scores: Any,
    eligible: Any,
    selected: Any,
    movie_ids: Any,
    k: int,
    label: str,
) -> None:
    """Certify exact stable top-k without trusting a stored oracle flag."""

    import numpy as np

    score_row = np.asarray(scores, dtype=np.float32)
    allowed = np.asarray(eligible, dtype=np.bool_)
    chosen = np.asarray(selected, dtype=np.int64)
    catalog_ids = np.asarray(movie_ids, dtype=np.int64)
    if score_row.shape != allowed.shape or score_row.shape != catalog_ids.shape:
        raise IntegrityError(f"{label} full-score/mask/catalog shapes differ")
    if chosen.shape != (k,) or len(set(map(int, chosen))) != k:
        raise IntegrityError(f"{label} does not contain {k} unique items")
    if np.any(chosen < 0) or np.any(chosen >= score_row.size) or not np.all(allowed[chosen]):
        raise IntegrityError(f"{label} selected an ineligible item")
    selected_scores = score_row[chosen]
    _require_finite(selected_scores, f"{label} selected scores")
    canonical = _stable_rank(chosen, selected_scores, catalog_ids)
    if canonical != tuple(map(int, chosen)):
        raise IntegrityError(f"{label} selected row violates stable score/ID order")
    cutoff_item = int(chosen[-1])
    cutoff_score = np.float32(score_row[cutoff_item])
    cutoff_movie = int(catalog_ids[cutoff_item])
    remaining = allowed.copy()
    remaining[chosen] = False
    outranks = remaining & (
        (score_row > cutoff_score)
        | ((score_row == cutoff_score) & (catalog_ids < cutoff_movie))
    )
    if np.any(outranks):
        raise IntegrityError(f"{label} omitted an item ahead of its cutoff")


def _normalise_replay(vector: Any, label: str) -> Any:
    import numpy as np

    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if not math.isfinite(norm) or norm <= 1.0e-12:
        raise IntegrityError(f"Cannot normalize {label}")
    return np.ascontiguousarray(value / norm, dtype=np.float32)


def _expected_prefix_queries(
    *,
    user_ids: Any,
    histories: Mapping[int, Sequence[ReplayEvent]],
    semantic_matrix: Any,
    bpr_user_matrix: Any,
    bpr_item_matrix: Any,
    collaborative_mask: Any,
) -> tuple[Any, Any]:
    import numpy as np

    users = np.asarray(user_ids, dtype=np.int64)
    semantic = np.asarray(semantic_matrix, dtype=np.float32)
    bpr_users = np.asarray(bpr_user_matrix, dtype=np.float32)
    bpr_items = np.asarray(bpr_item_matrix, dtype=np.float32)
    collaborative = np.asarray(collaborative_mask, dtype=np.bool_)
    raw_queries = np.empty((users.size, 384), dtype=np.float32)
    bpr_queries = np.empty((users.size, 64), dtype=np.float32)
    for user_row, raw_user_id in enumerate(users):
        events = tuple(histories[int(raw_user_id)])
        positive = sorted(
            {event.item_index for event in events if event.rating >= 4.0}
        )
        disliked = sorted(
            {event.item_index for event in events if event.rating <= 2.0}
        )
        if not positive:
            raise IntegrityError("Authenticated prefix has no semantic positive")
        liked = _normalise_replay(
            np.mean(semantic[np.asarray(positive, dtype=np.int64)], axis=0),
            "liked centroid",
        )
        dislike = (
            _normalise_replay(
                np.mean(semantic[np.asarray(disliked, dtype=np.int64)], axis=0),
                "disliked centroid",
            )
            if disliked
            else np.zeros(384, dtype=np.float32)
        )
        raw_queries[user_row] = _normalise_replay(
            liked - np.float32(0.25) * dislike, "raw semantic query"
        )
        base = np.asarray(bpr_users[user_row], dtype=np.float32)
        selected = [event for event in events if collaborative[event.item_index]]
        if selected:
            weights = np.asarray(
                [
                    np.clip((event.rating - 3.0) / 2.0, -1.0, 1.0)
                    for event in selected
                ],
                dtype=np.float32,
            )
            if float(np.sum(np.abs(weights))) > 0.0:
                indices = np.asarray(
                    [event.item_index for event in selected], dtype=np.int64
                )
                aggregate = np.sum(
                    bpr_items[indices] * weights[:, None], axis=0
                )
                aggregate /= float(np.sum(np.abs(weights)))
                base = base + 0.5 * aggregate
        if not np.isfinite(base).all() or float(np.linalg.norm(base)) <= 1.0e-12:
            raise IntegrityError("Authenticated prefix yields an invalid BPR query")
        bpr_queries[user_row] = np.ascontiguousarray(base, dtype=np.float32)
    return raw_queries, bpr_queries


def _load_stage_manifests(
    *,
    raw: Mapping[str, Any],
    prefix: str,
    run_directory: Path,
    protocol_fingerprint: str,
    execution_fingerprint: str,
    user_ids: Any,
) -> Mapping[int, Mapping[str, Any]]:
    import numpy as np

    names = _decode_strings(raw[f"{prefix}_manifest_files"], f"{prefix} manifests")
    hashes = _decode_strings(
        raw[f"{prefix}_manifest_sha256"], f"{prefix} manifest hashes"
    )
    if len(names) != len(EXPECTED_SEEDS) or len(hashes) != len(EXPECTED_SEEDS):
        raise IntegrityError(f"{prefix} must bind one manifest per seed")
    manifests: dict[int, Mapping[str, Any]] = {}
    for expected_seed, name, expected_hash in zip(
        EXPECTED_SEEDS, names, hashes, strict=True
    ):
        path = contained_file(run_directory, name, f"{prefix} manifest")
        if not is_sha256(expected_hash) or sha256_file(path) != expected_hash:
            raise IntegrityError(f"{prefix} manifest hash differs")
        manifest = _load_npz_exact(path, MANIFEST_FIELDS, f"{prefix} manifest")
        if (
            _decode_scalar_string(manifest["schema"], "manifest schema")
            != "cable-pref-target-blind-manifest-v1"
            or _decode_scalar_string(
                manifest["protocol_sha256"], "manifest protocol fingerprint"
            )
            != protocol_fingerprint
            or _decode_scalar_string(
                manifest["execution_fingerprint_sha256"],
                "manifest execution fingerprint",
            )
            != execution_fingerprint
            or _decode_scalar_string(manifest["stage"], "manifest stage") != prefix
            or _scalar_int(manifest["seed"], "manifest seed") != expected_seed
            or _decode_strings(manifest["methods"], "manifest methods")
            != EXPECTED_METHODS
            or not np.array_equal(
                np.asarray(manifest["alphas"], dtype=np.float32),
                np.asarray(EXPECTED_ALPHAS, dtype=np.float32),
            )
            or not np.array_equal(
                np.asarray(manifest["user_ids"], dtype=np.int64),
                np.asarray(user_ids, dtype=np.int64),
            )
            or _scalar_int(
                manifest["target_fields_accessed"], "manifest target access"
            )
            != 0
        ):
            raise IntegrityError(f"{prefix} manifest metadata differs")
        manifests[expected_seed] = manifest
    return manifests


def _verify_manifest_oracles(
    *,
    manifests: Mapping[int, Mapping[str, Any]],
    prefix: str,
    user_ids: Any,
    movie_ids: Any,
    expected_histories: Mapping[int, Sequence[ReplayEvent]],
    semantic_matrix: Any,
    bpr_user_matrix: Any,
    bpr_item_matrix: Any,
    collaborative_mask: Any,
    action_pairs: Sequence[tuple[int, int, int, int, int]] | None = None,
) -> Mapping[str, Any]:
    import numpy as np

    users = np.asarray(user_ids, dtype=np.int64)
    catalog = np.asarray(movie_ids, dtype=np.int64)
    semantic = np.asarray(semantic_matrix, dtype=np.float32)
    bpr_items_matrix = np.asarray(bpr_item_matrix, dtype=np.float32)
    collaborative = np.asarray(collaborative_mask, dtype=np.bool_)
    user_count = users.size
    catalog_count = catalog.size
    action_by_user: dict[int, tuple[int, ...]] = {}
    if action_pairs is not None:
        temporary: dict[int, set[int]] = {}
        for row in action_pairs:
            temporary.setdefault(row[0], set()).add(row[1])
        action_by_user = {
            user_id: tuple(sorted(values)) for user_id, values in temporary.items()
        }
    action_checked = 0
    action_violations = 0
    action_ties = 0
    reference_history: Any | None = None
    reference_history_counts: Any | None = None
    reference_bpr_queries: Any | None = None
    expected_raw_queries, expected_bpr_queries = _expected_prefix_queries(
        user_ids=users,
        histories=expected_histories,
        semantic_matrix=semantic,
        bpr_user_matrix=bpr_user_matrix,
        bpr_item_matrix=bpr_items_matrix,
        collaborative_mask=collaborative,
    )

    for seed in EXPECTED_SEEDS:
        manifest = manifests[seed]
        candidates = np.asarray(manifest["candidates"], dtype=np.int64)
        bpr_scores = np.asarray(manifest["bpr_scores"], dtype=np.float32)
        semantic_scores = np.asarray(manifest["semantic_scores"], dtype=np.float32)
        bpr_queries = np.asarray(manifest["bpr_queries"], dtype=np.float32)
        semantic_queries = np.asarray(manifest["semantic_queries"], dtype=np.float32)
        learned_boundaries = np.asarray(
            manifest["learned_boundaries"], dtype=np.float32
        )
        history_items = np.asarray(manifest["history_items"], dtype=np.int64)
        history_counts = np.asarray(manifest["history_counts"], dtype=np.int64)
        complement_counts = np.asarray(
            manifest["complement_counts"], dtype=np.int64
        )
        oracle_agreement = np.asarray(manifest["oracle_agreement"], dtype=np.uint8)
        history_width = history_items.shape[1] if history_items.ndim == 2 else -1
        expected_shapes = {
            "candidates": (len(EXPECTED_METHODS), user_count, 400),
            "bpr_scores": (len(EXPECTED_METHODS), user_count, 400),
            "semantic_scores": (len(EXPECTED_METHODS), user_count, 400),
            "bpr_queries": (user_count, 64),
            "semantic_queries": (len(EXPECTED_METHODS), user_count, 384),
            "learned_boundaries": (len(EXPECTED_METHODS), user_count),
            "history_counts": (user_count,),
            "complement_counts": (user_count,),
            "oracle_agreement": (len(EXPECTED_METHODS), user_count),
        }
        for name, shape in expected_shapes.items():
            _require_shape(manifest[name], shape, f"{prefix}/{seed} {name}")
        if history_items.shape != (user_count, history_width) or history_width <= 0:
            raise IntegrityError(f"{prefix}/{seed} history array is malformed")
        if (
            not np.isfinite(bpr_queries).all()
            or not np.all(np.isnan(semantic_queries[0]))
            or not np.isfinite(semantic_queries[1:]).all()
            or not np.allclose(
                np.linalg.norm(semantic_queries[1:], axis=2),
                1.0,
                rtol=0.0,
                atol=2.0e-5,
            )
            or not np.all(np.isnan(learned_boundaries[0]))
            or not np.isfinite(learned_boundaries[1:]).all()
            or not np.all(oracle_agreement == 1)
            or np.any(complement_counts < 500)
        ):
            raise IntegrityError(f"{prefix}/{seed} query/boundary/oracle arrays are invalid")
        if not np.allclose(
            bpr_queries,
            expected_bpr_queries,
            rtol=0.0,
            atol=2.0e-6,
        ) or not np.allclose(
            semantic_queries[1],
            expected_raw_queries,
            rtol=0.0,
            atol=2.0e-6,
        ):
            raise IntegrityError(
                f"{prefix}/{seed} prefix query construction differs from replay"
            )
        if (
            np.any(candidates[0, :, :200] < 0)
            or not np.all(candidates[0, :, 200:] == -1)
            or not np.isfinite(bpr_scores[0, :, :200]).all()
            or not np.all(np.isnan(bpr_scores[0, :, 200:]))
            or not np.all(np.isnan(semantic_scores[0]))
            or np.any(candidates[1:] < 0)
            or not np.isfinite(bpr_scores[1:]).all()
            or not np.isfinite(semantic_scores[1:]).all()
        ):
            raise IntegrityError(f"{prefix}/{seed} candidate/score padding is invalid")
        for user_row, raw_user_id in enumerate(users):
            count = int(history_counts[user_row])
            if count < 1 or count > history_width:
                raise IntegrityError(f"{prefix}/{seed} history count is out of bounds")
            expected = tuple(
                event.item_index for event in expected_histories[int(raw_user_id)]
            )
            actual = tuple(map(int, history_items[user_row, :count]))
            if actual != expected or len(set(actual)) != len(actual):
                raise IntegrityError(
                    f"{prefix}/{seed} history differs from authenticated prefix"
                )
            if count < history_width and not np.all(history_items[user_row, count:] == -1):
                raise IntegrityError(f"{prefix}/{seed} history padding changed")
        if reference_history is None:
            reference_history = history_items.copy()
            reference_history_counts = history_counts.copy()
            reference_bpr_queries = bpr_queries.copy()
        else:
            _same_array(reference_history, history_items, f"{prefix} seed histories")
            _same_array(
                reference_history_counts,
                history_counts,
                f"{prefix} seed history counts",
            )
            _same_array(
                reference_bpr_queries,
                bpr_queries,
                f"{prefix} seed BPR queries",
            )

        batch_size = 32
        for start in range(0, user_count, batch_size):
            stop = min(user_count, start + batch_size)
            full_bpr_batch = np.stack(
                [
                    np.asarray(
                        bpr_items_matrix @ bpr_queries[user_row], dtype=np.float32
                    )
                    for user_row in range(start, stop)
                ],
                axis=0,
            )
            for local, user_row in enumerate(range(start, stop)):
                count = int(history_counts[user_row])
                history = np.zeros(catalog_count, dtype=np.bool_)
                history[history_items[user_row, :count]] = True
                bpr_eligible = collaborative & ~history
                selected_bpr = candidates[0, user_row, :200]
                full_bpr = full_bpr_batch[local]
                _verify_exact_topk(
                    scores=full_bpr,
                    eligible=bpr_eligible,
                    selected=selected_bpr,
                    movie_ids=catalog,
                    k=200,
                    label=f"{prefix}/{seed}/u{user_row} BPR",
                )
                if not np.allclose(
                    bpr_scores[0, user_row, :200],
                    full_bpr[selected_bpr],
                    rtol=2.0e-6,
                    atol=2.0e-6,
                ):
                    raise IntegrityError(f"{prefix}/{seed} stored BPR scores differ")
                semantic_eligible = ~history
                semantic_eligible[selected_bpr] = False
                if int(np.sum(semantic_eligible)) != int(complement_counts[user_row]):
                    raise IntegrityError(f"{prefix}/{seed} complement count differs")
                for method_index in range(1, len(EXPECTED_METHODS)):
                    union = candidates[method_index, user_row]
                    if (
                        not np.array_equal(union[:200], selected_bpr)
                        or len(set(map(int, union))) != 400
                        or np.any(history[union])
                    ):
                        raise IntegrityError(
                            f"{prefix}/{seed} hybrid union invariant failed"
                        )
                    if not np.allclose(
                        bpr_scores[method_index, user_row],
                        full_bpr[union],
                        rtol=2.0e-6,
                        atol=2.0e-6,
                    ):
                        raise IntegrityError(
                            f"{prefix}/{seed} hybrid BPR components differ"
                        )

        for method_index in range(1, len(EXPECTED_METHODS)):
            for start in range(0, user_count, batch_size):
                stop = min(user_count, start + batch_size)
                full_semantic_batch = np.stack(
                    [
                        np.asarray(
                            semantic
                            @ semantic_queries[method_index, user_row],
                            dtype=np.float32,
                        )
                        for user_row in range(start, stop)
                    ],
                    axis=0,
                )
                for local, user_row in enumerate(range(start, stop)):
                    count = int(history_counts[user_row])
                    history = np.zeros(catalog_count, dtype=np.bool_)
                    history[history_items[user_row, :count]] = True
                    selected_bpr = candidates[0, user_row, :200]
                    eligible = ~history
                    eligible[selected_bpr] = False
                    selected_semantic = candidates[method_index, user_row, 200:400]
                    full_scores = full_semantic_batch[local]
                    _verify_exact_topk(
                        scores=full_scores,
                        eligible=eligible,
                        selected=selected_semantic,
                        movie_ids=catalog,
                        k=200,
                        label=(
                            f"{prefix}/{seed}/m{method_index}/u{user_row} semantic"
                        ),
                    )
                    union = candidates[method_index, user_row]
                    if not np.allclose(
                        semantic_scores[method_index, user_row],
                        full_scores[union],
                        rtol=2.0e-6,
                        atol=2.0e-6,
                    ):
                        raise IntegrityError(
                            f"{prefix}/{seed} semantic components differ"
                        )
                    if method_index == 4 and action_pairs is not None:
                        eligible_indices = np.flatnonzero(eligible)
                        order = np.lexsort(
                            (catalog[eligible_indices], -full_scores[eligible_indices])
                        )
                        top201 = eligible_indices[order[:201]]
                        selected_set = set(map(int, selected_semantic))
                        for endpoint in action_by_user.get(int(users[user_row]), ()):
                            if not eligible[endpoint]:
                                continue
                            endpoint_selected = endpoint in selected_set
                            boundary = int(top201[200] if endpoint_selected else top201[199])
                            expected = (
                                -float(full_scores[endpoint]), int(catalog[endpoint])
                            ) < (-float(full_scores[boundary]), int(catalog[boundary]))
                            action_checked += 1
                            action_violations += int(expected != endpoint_selected)
                            action_ties += int(
                                full_scores[endpoint] == full_scores[boundary]
                            )
    return {
        "exact_candidate_counts": True,
        "unique_unseen_candidates": True,
        "semantic_branch_bpr_novel": True,
        "shared_bpr_branch": True,
        "faiss_matrix_oracle_exact": True,
        "action": {
            "checked": int(action_checked),
            "violations": int(action_violations),
            "tie_boundaries": int(action_ties),
            "passed": bool(action_pairs is not None and action_checked > 0 and action_violations == 0),
        },
    }


def _verify_R_target_blind_manifest(
    *,
    training_record: Mapping[str, Any],
    run_directory: Path,
    protocol_fingerprint: str,
    execution_fingerprint: str,
    user_ids: Any,
    movie_ids: Any,
    A_events: Mapping[int, Sequence[ReplayEvent]],
    semantic_matrix: Any,
    bpr_user_matrix: Any,
    bpr_item_matrix: Any,
    collaborative_mask: Any,
) -> Mapping[str, Any]:
    import numpy as np

    if training_record.get("schema") != "cable-pref-training-diagnostics-v1":
        raise IntegrityError("Training diagnostics schema changed")
    path = contained_file(
        run_directory,
        str(training_record.get("R_target_blind_manifest", "")),
        "R target-blind manifest",
    )
    expected_hash = str(
        training_record.get("R_target_blind_manifest_sha256", "")
    ).lower()
    if not is_sha256(expected_hash) or sha256_file(path) != expected_hash:
        raise IntegrityError("R target-blind manifest hash differs")
    manifest = _load_npz_exact(path, R_MANIFEST_FIELDS, "R target-blind manifest")
    users = np.asarray(user_ids, dtype=np.int64)
    catalog = np.asarray(movie_ids, dtype=np.int64)
    semantic = np.asarray(semantic_matrix, dtype=np.float32)
    bpr_matrix = np.asarray(bpr_item_matrix, dtype=np.float32)
    collaborative = np.asarray(collaborative_mask, dtype=np.bool_)
    if (
        _decode_scalar_string(manifest["schema"], "R manifest schema")
        != "cable-pref-R-target-blind-v1"
        or _decode_scalar_string(
            manifest["protocol_sha256"], "R protocol fingerprint"
        )
        != protocol_fingerprint
        or _decode_scalar_string(
            manifest["execution_fingerprint_sha256"], "R execution fingerprint"
        )
        != execution_fingerprint
        or not np.array_equal(
            np.asarray(manifest["user_ids"], dtype=np.int64), users
        )
        or _scalar_int(manifest["target_fields_accessed"], "R target access") != 0
    ):
        raise IntegrityError("R target-blind manifest metadata differs")
    bpr_items = np.asarray(manifest["bpr_items"], dtype=np.int64)
    semantic_items = np.asarray(manifest["raw_semantic_items"], dtype=np.int64)
    raw_queries = np.asarray(manifest["raw_queries"], dtype=np.float32)
    bpr_queries = np.asarray(manifest["bpr_queries"], dtype=np.float32)
    history_items = np.asarray(manifest["history_items"], dtype=np.int64)
    history_counts = np.asarray(manifest["history_counts"], dtype=np.int64)
    complement_counts = np.asarray(manifest["complement_counts"], dtype=np.int64)
    cutoff_items = np.asarray(manifest["raw_cutoff_items"], dtype=np.int64)
    cutoff_scores = np.asarray(manifest["raw_cutoff_scores"], dtype=np.float32)
    user_count = users.size
    history_width = history_items.shape[1] if history_items.ndim == 2 else -1
    for name, shape in {
        "bpr_items": (user_count, 200),
        "raw_semantic_items": (user_count, 200),
        "raw_queries": (user_count, 384),
        "bpr_queries": (user_count, 64),
        "history_counts": (user_count,),
        "complement_counts": (user_count,),
        "raw_cutoff_items": (user_count,),
        "raw_cutoff_scores": (user_count,),
    }.items():
        _require_shape(manifest[name], shape, f"R manifest {name}")
    if (
        history_items.shape != (user_count, history_width)
        or history_width <= 0
        or not np.isfinite(raw_queries).all()
        or not np.isfinite(bpr_queries).all()
        or not np.isfinite(cutoff_scores).all()
        or not np.allclose(
            np.linalg.norm(raw_queries, axis=1), 1.0, rtol=0.0, atol=2.0e-5
        )
        or np.any(complement_counts < 500)
    ):
        raise IntegrityError("R target-blind query/history arrays are invalid")
    expected_raw_queries, expected_bpr_queries = _expected_prefix_queries(
        user_ids=users,
        histories=A_events,
        semantic_matrix=semantic,
        bpr_user_matrix=bpr_user_matrix,
        bpr_item_matrix=bpr_matrix,
        collaborative_mask=collaborative,
    )
    if not np.allclose(
        raw_queries, expected_raw_queries, rtol=0.0, atol=2.0e-6
    ) or not np.allclose(
        bpr_queries, expected_bpr_queries, rtol=0.0, atol=2.0e-6
    ):
        raise IntegrityError("R prefix query construction differs from replay")
    batch_size = 32
    for start in range(0, user_count, batch_size):
        stop = min(user_count, start + batch_size)
        bpr_full_batch = np.asarray(
            bpr_queries[start:stop] @ bpr_matrix.T, dtype=np.float32
        )
        semantic_full_batch = np.asarray(
            raw_queries[start:stop] @ semantic.T, dtype=np.float32
        )
        for local, user_row in enumerate(range(start, stop)):
            user_id = int(users[user_row])
            count = int(history_counts[user_row])
            expected_history = tuple(event.item_index for event in A_events[user_id])
            actual_history = tuple(map(int, history_items[user_row, :count]))
            if count != len(expected_history) or actual_history != expected_history:
                raise IntegrityError("R target-blind history differs from A")
            if count < history_width and not np.all(history_items[user_row, count:] == -1):
                raise IntegrityError("R target-blind history padding changed")
            history = np.zeros(catalog.size, dtype=np.bool_)
            history[list(actual_history)] = True
            bpr_eligible = collaborative & ~history
            _verify_exact_topk(
                scores=bpr_full_batch[local],
                eligible=bpr_eligible,
                selected=bpr_items[user_row],
                movie_ids=catalog,
                k=200,
                label=f"R/u{user_row} BPR",
            )
            semantic_eligible = ~history
            semantic_eligible[bpr_items[user_row]] = False
            if int(np.sum(semantic_eligible)) != int(complement_counts[user_row]):
                raise IntegrityError("R complement count differs")
            full_scores = semantic_full_batch[local]
            _verify_exact_topk(
                scores=full_scores,
                eligible=semantic_eligible,
                selected=semantic_items[user_row],
                movie_ids=catalog,
                k=200,
                label=f"R/u{user_row} semantic",
            )
            if (
                int(cutoff_items[user_row]) != int(semantic_items[user_row, -1])
                or not np.isclose(
                    cutoff_scores[user_row],
                    full_scores[int(cutoff_items[user_row])],
                    rtol=2.0e-6,
                    atol=2.0e-6,
                )
            ):
                raise IntegrityError("R stored semantic cutoff differs")
    manifest_utc = str(training_record.get("R_target_blind_manifest_published_utc", ""))
    opened_utc = str(training_record.get("R_opened_utc", ""))
    if not manifest_utc or not opened_utc or manifest_utc > opened_utc:
        raise IntegrityError("R target-blind manifest did not precede target access")
    return {
        "file": safe_relative(path, run_directory),
        "sha256": expected_hash,
        "target_fields_accessed": 0,
        "published_before_R_open": True,
    }


def _manifest_ranking(
    manifest: Mapping[str, Any],
    *,
    method_index: int,
    user_index: int,
    alpha_index: int,
    movie_ids: Any,
) -> tuple[int, ...]:
    import numpy as np

    size = 200 if method_index == 0 else 400
    items = np.asarray(
        manifest["candidates"][method_index, user_index, :size], dtype=np.int64
    )
    if method_index == 0:
        scores = np.asarray(
            manifest["bpr_scores"][method_index, user_index, :size],
            dtype=np.float32,
        )
    else:
        bpr = _quantile_scale(
            manifest["bpr_scores"][method_index, user_index, :size]
        )
        semantic = _quantile_scale(
            manifest["semantic_scores"][method_index, user_index, :size]
        )
        alpha = np.float32(EXPECTED_ALPHAS[alpha_index])
        scores = np.asarray(alpha * bpr + np.float32(1.0 - alpha) * semantic, dtype=np.float32)
    return _stable_rank(items, scores, movie_ids)


def _evaluate_stage_from_raw(
    *,
    manifest: Mapping[str, Any],
    raw: Mapping[str, Any],
    stage_prefix: str,
    alpha_index: int,
) -> tuple[Any, Mapping[str, int]]:
    """Recompute all eight registered user-level metrics from IDs/ratings."""

    import numpy as np

    movie_ids = np.asarray(raw["catalog_movie_ids"], dtype=np.int64)
    user_ids = np.asarray(raw["user_ids"], dtype=np.int64)
    user_count = user_ids.size
    metric_index = {name: index for index, name in enumerate(EXPECTED_METRICS)}
    values = np.full(
        (len(EXPECTED_METHODS), user_count, len(EXPECTED_METRICS)),
        np.nan,
        dtype=np.float64,
    )
    event_items = np.asarray(raw[f"{stage_prefix}_event_items"], dtype=np.int64)
    event_ratings = np.asarray(raw[f"{stage_prefix}_event_ratings"], dtype=np.float64)
    event_counts = np.asarray(raw[f"{stage_prefix}_event_counts"], dtype=np.int64)
    pair_preferred = np.asarray(raw[f"{stage_prefix}_pair_preferred"], dtype=np.int64)
    pair_rejected = np.asarray(raw[f"{stage_prefix}_pair_rejected"], dtype=np.int64)
    pair_counts = np.asarray(raw[f"{stage_prefix}_pair_counts"], dtype=np.int64)
    if event_items.shape != event_ratings.shape or event_items.shape[0] != user_count:
        raise IntegrityError(f"{stage_prefix} event arrays have incompatible shapes")
    if pair_preferred.shape != pair_rejected.shape or pair_preferred.shape[0] != user_count:
        raise IntegrityError(f"{stage_prefix} pair arrays have incompatible shapes")

    admission_changed = 0
    admission_total = 0
    spce_changed = 0
    spce_total = 0
    missed_total = 0
    missed_users = 0
    pair_users = 0
    fixed_pairs = 0

    for user_row in range(user_count):
        ec = int(event_counts[user_row])
        pc = int(pair_counts[user_row])
        if ec < 0 or ec > event_items.shape[1] or pc < 0 or pc > pair_preferred.shape[1]:
            raise IntegrityError(f"{stage_prefix} ragged count is out of bounds")
        items = np.asarray(event_items[user_row, :ec], dtype=np.int64)
        ratings = np.asarray(event_ratings[user_row, :ec], dtype=np.float64)
        preferred_row = np.asarray(pair_preferred[user_row, :pc], dtype=np.int64)
        rejected_row = np.asarray(pair_rejected[user_row, :pc], dtype=np.int64)
        if (
            len(set(map(int, items))) != ec
            or np.any(items < 0)
            or np.any(items >= movie_ids.size)
            or not np.isfinite(ratings).all()
        ):
            raise IntegrityError(f"{stage_prefix} event row is invalid")
        if pc and (
            np.any(preferred_row < 0)
            or np.any(rejected_row < 0)
            or np.any(preferred_row >= movie_ids.size)
            or np.any(rejected_row >= movie_ids.size)
        ):
            raise IntegrityError(f"{stage_prefix} pair endpoint is invalid")
        preferred_unique = sorted(set(map(int, preferred_row)))
        bpr_set = set(
            map(int, manifest["candidates"][0, user_row, :200])
        )
        missed = [item for item in preferred_unique if item not in bpr_set]
        missed_total += len(missed)
        missed_users += int(bool(missed))
        fixed_pairs += pc
        pair_users += int(pc > 0)
        positives = set(map(int, items[ratings >= 4.0]))
        dislikes = set(map(int, items[ratings <= 2.0]))
        raw_semantic = set(
            map(int, manifest["candidates"][1, user_row, 200:400])
        )
        cable_semantic = set(
            map(int, manifest["candidates"][4, user_row, 200:400])
        )
        admission_total += len(missed)
        admission_changed += sum(
            (item in raw_semantic) != (item in cable_semantic) for item in missed
        )
        raw_top10 = _manifest_ranking(
            manifest,
            method_index=1,
            user_index=user_row,
            alpha_index=alpha_index,
            movie_ids=movie_ids,
        )[:10]
        cable_top10 = _manifest_ranking(
            manifest,
            method_index=4,
            user_index=user_row,
            alpha_index=alpha_index,
            movie_ids=movie_ids,
        )[:10]
        raw_positions = {item: rank for rank, item in enumerate(raw_top10)}
        cable_positions = {item: rank for rank, item in enumerate(cable_top10)}
        for preferred, rejected in zip(preferred_row, rejected_row, strict=True):
            raw_outcome = raw_positions.get(int(preferred), 10) < raw_positions.get(
                int(rejected), 10
            )
            cable_outcome = cable_positions.get(
                int(preferred), 10
            ) < cable_positions.get(int(rejected), 10)
            spce_changed += int(raw_outcome != cable_outcome)
            spce_total += 1

        for method_index in range(len(EXPECTED_METHODS)):
            ranking = _manifest_ranking(
                manifest,
                method_index=method_index,
                user_index=user_row,
                alpha_index=alpha_index,
                movie_ids=movie_ids,
            )
            top10 = ranking[:10]
            top10_set = set(top10)
            semantic_set = (
                set()
                if method_index == 0
                else set(
                    map(
                        int,
                        manifest["candidates"][method_index, user_row, 200:400],
                    )
                )
            )
            if missed:
                values[
                    method_index,
                    user_row,
                    metric_index["conditional_admission_at_200"],
                ] = np.mean([item in semantic_set for item in missed])
            if preferred_unique:
                values[
                    method_index,
                    user_row,
                    metric_index["net_new_preferred_support"],
                ] = np.mean(
                    [item not in bpr_set and item in semantic_set for item in preferred_unique]
                )
                values[
                    method_index,
                    user_row,
                    metric_index["preferred_exposure_at_10"],
                ] = np.mean([item in top10_set for item in preferred_unique])
            if pc:
                values[
                    method_index,
                    user_row,
                    metric_index["net_admission_advantage"],
                ] = np.mean(
                    [
                        float(int(preferred) in semantic_set)
                        - float(int(rejected) in semantic_set)
                        for preferred, rejected in zip(
                            preferred_row, rejected_row, strict=True
                        )
                    ]
                )
                positions = {item: rank for rank, item in enumerate(top10)}
                values[
                    method_index, user_row, metric_index["spce_at_10"]
                ] = np.mean(
                    [
                        positions.get(int(preferred), 10)
                        < positions.get(int(rejected), 10)
                        for preferred, rejected in zip(
                            preferred_row, rejected_row, strict=True
                        )
                    ]
                )
            if positives:
                discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
                gains = np.asarray(
                    [1.0 if item in positives else 0.0 for item in top10],
                    dtype=np.float64,
                )
                ideal = float(np.sum(discounts[: min(10, len(positives))]))
                values[method_index, user_row, metric_index["ndcg_at_10"]] = float(
                    np.sum(gains * discounts)
                ) / ideal
                values[
                    method_index, user_row, metric_index["recall_at_10"]
                ] = sum(item in positives for item in top10) / len(positives)
            values[
                method_index,
                user_row,
                metric_index["low_rating_intrusion_at_10"],
            ] = sum(item in dislikes for item in top10) / 10.0

    return values, {
        "fixed_pairs": int(fixed_pairs),
        "pair_users": int(pair_users),
        "unique_bpr_missed_preferred_endpoints": int(missed_total),
        "missed_endpoint_users": int(missed_users),
        "admission_changed_count": int(admission_changed),
        "admission_total": int(admission_total),
        "spce_changed_count": int(spce_changed),
        "spce_total": int(spce_total),
    }


def _validation_choice_replay(
    *,
    manifests: Mapping[int, Mapping[str, Any]],
    raw: Mapping[str, Any],
    movie_ids: Any,
) -> tuple[int, float, str, Mapping[str, Any]]:
    import numpy as np

    catalog = np.asarray(movie_ids, dtype=np.int64)
    users = np.asarray(raw["user_ids"], dtype=np.int64)
    event_items = np.asarray(raw["V_event_items"], dtype=np.int64)
    event_ratings = np.asarray(raw["V_event_ratings"], dtype=np.float64)
    event_counts = np.asarray(raw["V_event_counts"], dtype=np.int64)
    positives: list[set[int]] = []
    for row in range(users.size):
        count = int(event_counts[row])
        positives.append(
            set(map(int, event_items[row, :count][event_ratings[row, :count] >= 4.0]))
        )
    grid: list[Mapping[str, float]] = []
    for alpha_index, alpha in enumerate(EXPECTED_ALPHAS):
        ndcg_seed: list[float] = []
        recall_seed: list[float] = []
        for seed in EXPECTED_SEEDS:
            manifest = manifests[seed]
            ndcg_users: list[float] = []
            recall_users: list[float] = []
            for user_row, relevant in enumerate(positives):
                if not relevant:
                    continue
                top10 = _manifest_ranking(
                    manifest,
                    method_index=1,
                    user_index=user_row,
                    alpha_index=alpha_index,
                    movie_ids=catalog,
                )[:10]
                discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
                gains = np.asarray(
                    [item in relevant for item in top10], dtype=np.float64
                )
                ideal = float(np.sum(discounts[: min(10, len(relevant))]))
                ndcg_users.append(float(np.sum(gains * discounts)) / ideal)
                recall_users.append(sum(item in relevant for item in top10) / len(relevant))
            if not ndcg_users:
                raise IntegrityError("No validation relevance user for alpha selection")
            ndcg_seed.append(float(np.mean(ndcg_users)))
            recall_seed.append(float(np.mean(recall_users)))
        grid.append(
            {
                "alpha": float(alpha),
                "ndcg": float(np.mean(ndcg_seed)),
                "recall": float(np.mean(recall_seed)),
            }
        )
    selected_index = max(
        range(len(grid)),
        key=lambda index: (
            grid[index]["ndcg"],
            grid[index]["recall"],
            grid[index]["alpha"],
        ),
    )

    relevance: dict[str, Mapping[str, float]] = {}
    for method, method_index in (("raw_hybrid", 1), ("bpr", 0)):
        ndcg_seed = []
        recall_seed = []
        for seed in EXPECTED_SEEDS:
            ndcg_users = []
            recall_users = []
            manifest = manifests[seed]
            for user_row, relevant in enumerate(positives):
                if not relevant:
                    continue
                top10 = _manifest_ranking(
                    manifest,
                    method_index=method_index,
                    user_index=user_row,
                    alpha_index=selected_index,
                    movie_ids=catalog,
                )[:10]
                discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
                gains = np.asarray(
                    [item in relevant for item in top10], dtype=np.float64
                )
                ideal = float(np.sum(discounts[: min(10, len(relevant))]))
                ndcg_users.append(float(np.sum(gains * discounts)) / ideal)
                recall_users.append(sum(item in relevant for item in top10) / len(relevant))
            ndcg_seed.append(float(np.mean(ndcg_users)))
            recall_seed.append(float(np.mean(recall_users)))
        relevance[method] = {
            "ndcg": float(np.mean(ndcg_seed)),
            "recall": float(np.mean(recall_seed)),
        }
    stronger = max(
        ("raw_hybrid", "bpr"),
        key=lambda name: (
            relevance[name]["ndcg"],
            relevance[name]["recall"],
            int(name == "bpr"),
        ),
    )
    return (
        selected_index,
        float(EXPECTED_ALPHAS[selected_index]),
        stronger,
        {
            "alpha_grid": grid,
            "relevance_candidates": relevance,
        },
    )


def _verify_frozen_choices(
    *,
    run_directory: Path,
    execution_fingerprint: str,
    selected_index: int,
    selected_alpha: float,
    stronger: str,
    replay: Mapping[str, Any],
) -> Mapping[str, Any]:
    record = read_json_mapping(
        contained_file(
            run_directory,
            "frozen_validation_choices.json",
            "frozen validation choices",
        ),
        "frozen validation choices",
    )
    if (
        record.get("schema") != "cable-pref-frozen-validation-choices-v1"
        or record.get("execution_fingerprint_sha256") != execution_fingerprint
        or int(record.get("selected_alpha_index", -1)) != selected_index
        or float(record.get("selected_alpha", float("nan"))) != selected_alpha
        or record.get("stronger_G4_relevance_method") != stronger
        or record.get("component_normalization")
        != "per_request_5th_95th_linear_clip"
        or record.get("tie_break") != "score_desc_then_numeric_movie_id_asc"
    ):
        raise IntegrityError("Frozen validation choice metadata differs")
    alpha_record = require_mapping(record.get("alpha_selection"), "alpha selection")
    grid = require_sequence(alpha_record.get("grid"), "alpha-selection grid")
    if int(alpha_record.get("selected_index", -1)) != selected_index or len(grid) != 5:
        raise IntegrityError("Frozen alpha-selection record differs")
    for observed, expected in zip(grid, replay["alpha_grid"], strict=True):
        row = require_mapping(observed, "alpha-selection row")
        for field in ("alpha", "ndcg", "recall"):
            if not math.isclose(
                float(row.get(field, float("nan"))),
                float(expected[field]),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise IntegrityError("Frozen alpha-selection scores differ")
    relevance_record = require_mapping(
        record.get("relevance_selection"), "relevance selection"
    )
    candidates = require_mapping(
        relevance_record.get("candidates"), "relevance candidates"
    )
    if relevance_record.get("selected") != stronger or set(candidates) != {
        "raw_hybrid",
        "bpr",
    }:
        raise IntegrityError("Frozen stronger-baseline record differs")
    for method, expected in replay["relevance_candidates"].items():
        observed = require_mapping(candidates[method], f"{method} relevance record")
        for field in ("ndcg", "recall"):
            if not math.isclose(
                float(observed.get(field, float("nan"))),
                float(expected[field]),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise IntegrityError("Frozen stronger-baseline scores differ")
    if not str(record.get("frozen_utc", "")):
        raise IntegrityError("Frozen validation choices lack a timestamp")
    return record


def _verify_metric_tensor(observed: Any, expected: Any, label: str) -> None:
    import numpy as np

    first = np.asarray(observed, dtype=np.float64)
    second = np.asarray(expected, dtype=np.float64)
    if first.shape != second.shape:
        raise IntegrityError(f"{label} metric tensor shape differs")
    if not np.array_equal(np.isnan(first), np.isnan(second)):
        raise IntegrityError(f"{label} metric missingness differs")
    finite = np.isfinite(second)
    if not np.isfinite(first[finite]).all() or not np.allclose(
        first[finite], second[finite], rtol=0.0, atol=1.0e-12
    ):
        raise IntegrityError(f"{label} per-user metrics differ from replay")


def _nanmean_over_seeds(values: Any) -> Any:
    import numpy as np

    array = np.asarray(values, dtype=np.float64)
    count = np.sum(np.isfinite(array), axis=0)
    total = np.nansum(array, axis=0)
    result = np.full(total.shape, np.nan, dtype=np.float64)
    np.divide(total, count, out=result, where=count > 0)
    return result


def _power_audit_replay(validation_metrics: Any) -> Mapping[str, Any]:
    import numpy as np

    metric_index = {name: index for index, name in enumerate(EXPECTED_METRICS)}
    averaged = _nanmean_over_seeds(validation_metrics)
    comparisons = {
        "admission_vs_raw": (
            averaged[4, :, metric_index["conditional_admission_at_200"]]
            - averaged[1, :, metric_index["conditional_admission_at_200"]],
            0.020,
            20263505,
        ),
        "admission_vs_order_only": (
            averaged[4, :, metric_index["conditional_admission_at_200"]]
            - averaged[2, :, metric_index["conditional_admission_at_200"]],
            0.020,
            20263506,
        ),
        "spce_vs_raw": (
            averaged[4, :, metric_index["spce_at_10"]]
            - averaged[1, :, metric_index["spce_at_10"]],
            0.005,
            20263507,
        ),
        "spce_vs_bpr": (
            averaged[4, :, metric_index["spce_at_10"]]
            - averaged[0, :, metric_index["spce_at_10"]],
            0.005,
            20263508,
        ),
    }
    results = {
        name: _centered_power_detection(values, delta=delta, seed=seed)
        for name, (values, delta, seed) in comparisons.items()
    }
    return {
        "comparisons": results,
        "passed": bool(all(result["passed"] for result in results.values())),
    }


def _verify_stage_diagnostics(
    raw: Mapping[str, Any],
    *,
    prefix: str,
    diagnostics: Sequence[Mapping[str, int]],
) -> None:
    import numpy as np

    if len(diagnostics) != len(EXPECTED_SEEDS):
        raise IntegrityError(f"{prefix} diagnostic seed count differs")
    first = diagnostics[0]
    scalar_fields = {
        f"{prefix}_fixed_pairs": "fixed_pairs",
        f"{prefix}_pair_users": "pair_users",
        f"{prefix}_unique_bpr_missed_preferred_endpoints": (
            "unique_bpr_missed_preferred_endpoints"
        ),
        f"{prefix}_missed_endpoint_users": "missed_endpoint_users",
    }
    for field, key in scalar_fields.items():
        if _scalar_int(raw[field], field) != int(first[key]):
            raise IntegrityError(f"Raw {field} differs from metric replay")
    vector_fields = {
        f"{prefix}_admission_changed_count_by_seed": "admission_changed_count",
        f"{prefix}_admission_total_by_seed": "admission_total",
        f"{prefix}_spce_changed_count_by_seed": "spce_changed_count",
        f"{prefix}_spce_total_by_seed": "spce_total",
    }
    for field, key in vector_fields.items():
        expected = np.asarray([value[key] for value in diagnostics], dtype=np.int64)
        if not np.array_equal(np.asarray(raw[field], dtype=np.int64), expected):
            raise IntegrityError(f"Raw {field} differs from metric replay")


def _verify_training_evidence(
    *,
    raw: Mapping[str, Any],
    training_record: Mapping[str, Any],
    run_directory: Path,
    R_diagnostics: Mapping[str, Any],
) -> Mapping[str, Any]:
    import numpy as np

    recorded_R = require_mapping(
        training_record.get("R_pair_diagnostics"), "training R pair diagnostics"
    )
    for field in (
        "stage",
        "raw_pairs",
        "raw_pair_users",
        "selected_pairs",
        "selected_pair_users",
        "pair_identity_sha256",
    ):
        if recorded_R.get(field) != R_diagnostics[field]:
            raise IntegrityError(f"Training R diagnostic differs: {field}")
    if (
        _scalar_int(raw["R_selected_pairs"], "R selected pairs")
        != int(R_diagnostics["selected_pairs"])
        or _scalar_int(raw["R_selected_pair_users"], "R pair users")
        != int(R_diagnostics["selected_pair_users"])
        or _decode_scalar_string(raw["R_pair_identity_sha256"], "R pair identity")
        != R_diagnostics["pair_identity_sha256"]
    ):
        raise IntegrityError("Raw R support differs from pair replay")
    trained_methods = EXPECTED_METHODS[2:]
    if _decode_strings(raw["training_methods"], "training methods") != trained_methods:
        raise IntegrityError("Training method inventory/order changed")
    optimizer_steps = np.asarray(raw["training_optimizer_steps"], dtype=np.int64)
    pair_presentations = np.asarray(
        raw["training_pair_presentations"], dtype=np.int64
    )
    admission_presentations = np.asarray(
        raw["training_admission_presentations"], dtype=np.int64
    )
    initial_hashes = _decode_strings(
        raw["adapter_initial_memory_sha256"], "adapter initial hashes"
    )
    final_hashes = np.asarray(raw["adapter_final_memory_sha256"])
    for name, value in (
        ("training optimizer steps", optimizer_steps),
        ("training pair presentations", pair_presentations),
        ("training admission presentations", admission_presentations),
        ("adapter final hashes", final_hashes),
    ):
        _require_shape(value, (3, 6), name)
    if len(initial_hashes) != 3 or not all(is_sha256(value) for value in initial_hashes):
        raise IntegrityError("Adapter initial hashes are malformed")
    if not all(is_sha256(str(value)) for value in final_hashes.reshape(-1)):
        raise IntegrityError("Adapter final hashes are malformed")
    controls = require_mapping(training_record.get("controls"), "training controls")
    initial_record = require_mapping(
        training_record.get("initial_memory_sha256"), "initial-memory hashes"
    )
    checkpoints = require_mapping(
        training_record.get("checkpoints"), "checkpoint records"
    )
    expected_checkpoint_keys = {
        f"{seed}:{method}"
        for seed in EXPECTED_SEEDS
        for method in ("raw_hybrid", *trained_methods)
    }
    if set(checkpoints) != expected_checkpoint_keys:
        raise IntegrityError("Checkpoint inventory changed")
    for seed_row, seed in enumerate(EXPECTED_SEEDS):
        if str(initial_record.get(str(seed), "")) != initial_hashes[seed_row]:
            raise IntegrityError("Training initial-memory hash differs")
        seed_controls = require_mapping(controls.get(str(seed)), f"controls seed {seed}")
        if set(seed_controls) != set(trained_methods):
            raise IntegrityError("Training control inventory changed")
        if (
            len(set(map(int, optimizer_steps[seed_row]))) != 1
            or len(set(map(int, pair_presentations[seed_row]))) != 1
            or np.any(optimizer_steps[seed_row] <= 0)
            or np.any(pair_presentations[seed_row] <= 0)
            or np.any(admission_presentations[seed_row] < 0)
        ):
            raise IntegrityError("Matched training exposure invariant failed")
        parameter_counts: set[int] = set()
        for method_row, method in enumerate(trained_methods):
            diagnostic = require_mapping(
                seed_controls[method], f"training diagnostic {seed}/{method}"
            )
            if (
                diagnostic.get("method") != method
                or int(diagnostic.get("seed", -1)) != seed
                or int(diagnostic.get("epochs", -1)) != 12
                or int(diagnostic.get("optimizer_steps", -1))
                != int(optimizer_steps[seed_row, method_row])
                or int(diagnostic.get("pair_presentations", -1))
                != int(pair_presentations[seed_row, method_row])
                or int(diagnostic.get("admission_presentations", -1))
                != int(admission_presentations[seed_row, method_row])
                or diagnostic.get("final_epoch_only") is not True
                or diagnostic.get("reference_model_used") is not False
                or diagnostic.get("checkpoint_sha256")
                != str(final_hashes[seed_row, method_row])
            ):
                raise IntegrityError("Training diagnostic differs from raw evidence")
            parameter_counts.add(int(diagnostic.get("parameter_count", -1)))
            trace = require_sequence(
                diagnostic.get("trace"), f"training trace {seed}/{method}"
            )
            if len(trace) != 12:
                raise IntegrityError("Training trace does not contain 12 epochs")
            for epoch in trace:
                epoch_record = require_mapping(epoch, "training trace epoch")
                if set(epoch_record) != {"loss", "admission", "order"} or not all(
                    math.isfinite(float(epoch_record[field]))
                    for field in ("loss", "admission", "order")
                ):
                    raise IntegrityError("Training trace contains invalid values")
        if len(parameter_counts) != 1 or next(iter(parameter_counts)) <= 0:
            raise IntegrityError("Trainable controls do not have matched parameter counts")
        for method in ("raw_hybrid", *trained_methods):
            checkpoint = require_mapping(
                checkpoints[f"{seed}:{method}"], f"checkpoint {seed}/{method}"
            )
            path = contained_file(
                run_directory,
                str(checkpoint.get("file", "")),
                f"checkpoint {seed}/{method}",
            )
            digest = str(checkpoint.get("file_sha256", "")).lower()
            if not is_sha256(digest) or sha256_file(path) != digest:
                raise IntegrityError("Checkpoint file hash differs")
            expected_memory = (
                initial_hashes[seed_row]
                if method == "raw_hybrid"
                else str(final_hashes[seed_row, trained_methods.index(method)])
            )
            if (
                checkpoint.get("memory_sha256") != expected_memory
                or bool(checkpoint.get("trained")) != (method != "raw_hybrid")
            ):
                raise IntegrityError("Checkpoint memory/training binding differs")
    return {
        "matched_optimizer_steps": True,
        "matched_pair_presentations": True,
        "R_selected_pairs": int(R_diagnostics["selected_pairs"]),
        "R_selected_pair_users": int(R_diagnostics["selected_pair_users"]),
    }


def _verify_provenance_and_replay_archive(
    *,
    config: Mapping[str, Any],
    result: Mapping[str, Any],
    closure: CandidateClosure,
    run_directory: Path,
    archive_path: Path,
    source_hashes: Mapping[str, str],
    raw_user_ids: Any,
    raw_movie_ids: Any,
) -> Mapping[str, Any]:
    import numpy as np

    if result.get("schema") != "cable-pref-result-v1":
        raise IntegrityError("Result schema changed")
    candidate_sources = require_mapping(
        closure.candidate.get("source_sha256"), "candidate sources"
    )
    result_sources = require_mapping(result.get("source_sha256"), "result sources")
    if dict(candidate_sources) != dict(result_sources):
        raise IntegrityError("Result/candidate source hashes differ")
    for name, digest in candidate_sources.items():
        if str(source_hashes.get(name, "")).lower() != str(digest).lower():
            raise IntegrityError(f"Launch/result source hash differs: {name}")
    protocol_payload = {
        "schema": "cable-pref-protocol-fingerprint-v1",
        "protocol_name": config.get("protocol_name"),
        "source_sha256": dict(candidate_sources),
    }
    protocol_fingerprint = sha256_bytes(canonical_json_bytes(protocol_payload))
    if (
        result.get("protocol_fingerprint_payload") != protocol_payload
        or result.get("protocol_fingerprint_sha256") != protocol_fingerprint
    ):
        raise IntegrityError("Protocol fingerprint cannot be independently replayed")

    catalog, users, layouts, eligible_count, stages = _replay_archive_cohort(
        archive_path
    )
    if tuple(map(int, np.asarray(raw_movie_ids).tolist())) != catalog:
        raise IntegrityError("Raw catalog differs from authenticated archive")
    if tuple(map(int, np.asarray(raw_user_ids).tolist())) != users:
        raise IntegrityError("Raw cohort differs from authenticated replay")
    cohort_hash = sha256_bytes(canonical_json_bytes(list(users)))
    expected_environment = execution_environment()
    executable = Path(sys.executable).resolve()
    execution_payload = {
        "schema": "cable-pref-execution-fingerprint-v1",
        "protocol_fingerprint_sha256": protocol_fingerprint,
        "dataset_archive_sha256": str(
            require_mapping(config.get("dataset"), "config.dataset").get(
                "expected_archive_sha256"
            )
        ).lower(),
        "cohort_user_ids_sha256": cohort_hash,
        "optimization_seeds": list(EXPECTED_SEEDS),
        "python_executable_sha256": sha256_file(executable),
        "environment_sha256": environment_sha256(expected_environment),
    }
    execution_fingerprint = sha256_bytes(canonical_json_bytes(execution_payload))
    if (
        result.get("execution_fingerprint_payload") != execution_payload
        or result.get("execution_fingerprint_sha256") != execution_fingerprint
        or closure.candidate.get("execution_fingerprint_sha256")
        != execution_fingerprint
    ):
        raise IntegrityError("Execution fingerprint cannot be independently replayed")
    environment_record = read_json_mapping(
        contained_file(run_directory, "environment.json", "environment record"),
        "environment record",
    )
    if (
        environment_record.get("schema") != "cable-pref-environment-v1"
        or Path(str(environment_record.get("python_executable", ""))).resolve()
        != executable
        or environment_record.get("python_executable_sha256")
        != sha256_file(executable)
        or require_mapping(
            environment_record.get("fixed_environment"), "fixed environment"
        )
        != expected_environment
        or environment_record.get("fixed_environment_sha256")
        != environment_sha256(expected_environment)
        or require_mapping(environment_record.get("source_sha256"), "environment sources")
        != candidate_sources
        or environment_record.get("dataset_archive_sha256")
        != execution_payload["dataset_archive_sha256"]
        or environment_record.get("protocol_fingerprint_payload") != protocol_payload
        or environment_record.get("protocol_fingerprint_sha256")
        != protocol_fingerprint
        or environment_record.get("execution_fingerprint_payload")
        != execution_payload
        or environment_record.get("execution_fingerprint_sha256")
        != execution_fingerprint
        or Path(str(environment_record.get("prefix", ""))).resolve()
        == Path(str(environment_record.get("base_prefix", ""))).resolve()
    ):
        raise IntegrityError("Environment record differs from independent replay")
    versions = require_mapping(
        environment_record.get("package_versions"), "package versions"
    )
    if set(versions) != {
        "numpy",
        "torch",
        "faiss-cpu",
        "sentence-transformers",
    } or any(not str(value) or str(value) == "MISSING" for value in versions.values()):
        raise IntegrityError("Required runtime package inventory is incomplete")
    if any(os.environ.get(name, "") != value for name, value in expected_environment.items()):
        raise IntegrityError("Verifier process environment differs from fixed contract")

    archive_record = require_mapping(result.get("dataset_archive"), "result archive")
    dataset_config = require_mapping(config.get("dataset"), "config.dataset")
    if archive_record != {
        "bytes": int(dataset_config["expected_archive_size_bytes"]),
        "sha256": str(dataset_config["expected_archive_sha256"]).lower(),
        "md5": str(dataset_config["expected_official_sidecar_md5"]).lower(),
    }:
        raise IntegrityError("Result archive record differs from authenticated input")
    cohort_record = read_json_mapping(
        contained_file(run_directory, "cohort.json", "cohort record"),
        "cohort record",
    )
    expected_layouts = {
        str(user_id): {
            "user_id": user_id,
            "counts": list(layouts[user_id].counts),
            "minimum_timestamps": list(layouts[user_id].minimum_timestamps),
            "maximum_timestamps": list(layouts[user_id].maximum_timestamps),
            "structural_hash": layouts[user_id].structural_hash,
        }
        for user_id in users
    }
    if (
        cohort_record.get("schema") != "cable-pref-cohort-v1"
        or cohort_record.get("execution_fingerprint_sha256")
        != execution_fingerprint
        or int(cohort_record.get("eligible_user_count", -1)) != eligible_count
        or int(cohort_record.get("selected_user_count", -1)) != 2000
        or cohort_record.get("selected_user_ids") != list(users)
        or cohort_record.get("selected_user_ids_sha256") != cohort_hash
        or cohort_record.get("layouts") != expected_layouts
        or cohort_record.get("ratings_loading_strategy")
        != "one_structural_pass_plus_stage_authorized_rescans"
    ):
        raise IntegrityError("Cohort/layout record differs from archive replay")

    support = np.zeros(len(catalog), dtype=np.int32)
    for user_id in users:
        for event in stages["A"][user_id]:
            if event.rating >= 4.0:
                support[event.item_index] += 1
    collaborative_mask = np.ascontiguousarray(support >= 5, dtype=np.bool_)
    return {
        "protocol_fingerprint": protocol_fingerprint,
        "execution_fingerprint": execution_fingerprint,
        "catalog": catalog,
        "users": users,
        "layouts": layouts,
        "eligible_user_count": eligible_count,
        "stages": stages,
        "collaborative_mask": collaborative_mask,
        "cohort_user_ids_sha256": cohort_hash,
        "archive_replayed": True,
    }


def _pair_outcome(top_ten: Sequence[int], chosen: int, rejected: int) -> float:
    positions = {int(item): index for index, item in enumerate(top_ten)}
    chosen_rank = positions.get(int(chosen), 10)
    rejected_rank = positions.get(int(rejected), 10)
    return float(chosen_rank < rejected_rank)


def _paired_bootstrap(
    differences: Any, *, draws: int, alpha: float, seed: int
) -> Mapping[str, float]:
    import numpy as np

    raw = np.asarray(differences, dtype=np.float64)
    if raw.ndim != 1:
        raise IntegrityError("Bootstrap differences must be one-dimensional")
    values = raw[np.isfinite(raw)]
    if values.size == 0:
        raise IntegrityError("Bootstrap differences must be a finite nonempty vector")
    generator = np.random.default_rng(seed)
    estimates = np.empty(draws, dtype=np.float64)
    chunk = 128
    for start in range(0, draws, chunk):
        size = min(chunk, draws - start)
        sample = generator.integers(
            0, values.size, size=(size, values.size), endpoint=False
        )
        estimates[start : start + size] = np.mean(values[sample], axis=1)
    return {
        "point": float(values.mean()),
        "lower": float(np.quantile(estimates, alpha / 2.0, method="linear")),
        "upper": float(
            np.quantile(estimates, 1.0 - alpha / 2.0, method="linear")
        ),
        "users": int(values.size),
    }


def _centered_power_detection(
    differences: Any,
    *,
    delta: float,
    seed: int,
    experiments: int = 1000,
    inner_draws: int = 1000,
    alpha: float = 0.05,
) -> Mapping[str, Any]:
    """Registered two-level centered user-bootstrap power simulation."""

    import numpy as np

    raw = np.asarray(differences, dtype=np.float64)
    values = raw[np.isfinite(raw)]
    if values.ndim != 1 or values.size < 2:
        return {
            "finite_common_users": int(values.size),
            "delta": float(delta),
            "experiments": int(experiments),
            "inner_draws": int(inner_draws),
            "detected": 0,
            "detection_fraction": 0.0,
            "passed": False,
        }
    centered = values - float(values.mean()) + float(delta)
    generator = np.random.default_rng(seed)
    detected = 0
    for _experiment in range(experiments):
        synthetic = centered[
            generator.integers(0, centered.size, size=centered.size, endpoint=False)
        ]
        inner = np.empty(inner_draws, dtype=np.float64)
        chunk = 100
        for start in range(0, inner_draws, chunk):
            size = min(chunk, inner_draws - start)
            indices = generator.integers(
                0,
                synthetic.size,
                size=(size, synthetic.size),
                endpoint=False,
            )
            inner[start : start + size] = np.mean(synthetic[indices], axis=1)
        lower = float(np.quantile(inner, alpha / 2.0, method="linear"))
        detected += int(lower > 0.0)
    fraction = detected / experiments
    return {
        "finite_common_users": int(values.size),
        "delta": float(delta),
        "seed": int(seed),
        "experiments": int(experiments),
        "inner_draws": int(inner_draws),
        "detected": int(detected),
        "detection_fraction": float(fraction),
        "passed": bool(fraction >= 0.80),
    }


def _verify_latency_replay(
    *,
    raw: Mapping[str, Any],
    protocol_fingerprint: str,
    execution_fingerprint: str,
    cohort_user_ids: Any,
    catalog_count: int,
    runner_process_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    import numpy as np

    if (
        _decode_scalar_string(raw["schema"], "latency schema")
        != "cable-pref-raw-latency-v1"
        or _decode_scalar_string(
            raw["protocol_fingerprint_sha256"], "latency protocol fingerprint"
        )
        != protocol_fingerprint
        or _decode_scalar_string(
            raw["execution_fingerprint_sha256"], "latency execution fingerprint"
        )
        != execution_fingerprint
        or tuple(map(int, np.asarray(raw["seeds"]).tolist())) != EXPECTED_SEEDS
        or _decode_strings(raw["methods"], "latency methods")
        != ("raw_hybrid", "cable_pref")
    ):
        raise IntegrityError("Latency raw metadata differs")
    expected_users = sorted(
        map(int, np.asarray(cohort_user_ids).tolist()),
        key=lambda user_id: (
            hashlib.sha256(
                f"20263509:latency:{user_id}".encode("ascii")
            ).hexdigest(),
            user_id,
        ),
    )[:512]
    users = np.asarray(raw["user_ids"], dtype=np.int64)
    if users.tolist() != expected_users:
        raise IntegrityError("Latency request cohort differs from registered hash order")
    durations = np.asarray(raw["durations_ms"], dtype=np.float64)
    _require_shape(durations, (3, 2, 512, 7), "latency durations")
    if not np.isfinite(durations).all() or np.any(durations <= 0.0):
        raise IntegrityError("Latency durations must be finite and positive")
    per_request = np.median(durations, axis=3)
    p50 = np.quantile(per_request, 0.50, axis=2, method="higher")
    p95 = np.quantile(per_request, 0.95, axis=2, method="higher")
    p99 = np.quantile(per_request, 0.99, axis=2, method="higher")
    ratios = p95[:, 1] / np.maximum(p95[:, 0], 1.0e-12)
    worst_p95 = float(np.max(p95[:, 1]))
    worst_ratio = float(np.max(ratios))
    for field, expected in (
        ("per_request_median_ms", per_request),
        ("p95_ms", p95),
        ("p99_ms", p99),
        ("p95_ratio_by_seed", ratios),
    ):
        _same_array(raw[field], expected, f"latency {field}", rtol=0.0, atol=1e-12)
    if (
        not math.isclose(
            _scalar_float(raw["worst_cable_p95_ms"], "worst cable p95"),
            worst_p95,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or not math.isclose(
            _scalar_float(raw["worst_p95_ratio"], "worst p95 ratio"),
            worst_ratio,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    ):
        raise IntegrityError("Latency worst-case summaries differ")
    passed = bool(worst_p95 <= 10.0 and worst_ratio <= 1.25)
    if _scalar_bool(raw["passed"], "latency passed") != passed:
        raise IntegrityError("Latency pass flag differs from independent replay")
    measured_invocations = 3 * 2 * 512 * 7
    vectors_scored = measured_invocations * 2 * int(catalog_count)
    vector_payload_bytes = measured_invocations * int(catalog_count) * (64 + 384) * 4
    memory = require_mapping(
        runner_process_record.get("memory"), "latency runner memory record"
    )
    return {
        "user_ids_sha256": sha256_bytes(
            canonical_json_bytes(list(map(int, users)))
        ),
        "worst_cable_p95_ms": worst_p95,
        "worst_p95_ratio": worst_ratio,
        "p50_ms_by_seed_method": p50.tolist(),
        "p95_ms_by_seed_method": p95.tolist(),
        "p99_ms_by_seed_method": p99.tolist(),
        "p95_ratio_by_seed": ratios.tolist(),
        "measured_invocations": measured_invocations,
        "vectors_scored": vectors_scored,
        "vector_payload_bytes_scored": vector_payload_bytes,
        "bytes_read": vector_payload_bytes,
        "bytes_read_definition": "model_vector_payload_bytes_for_timed_full_score_paths",
        "peak_resident_memory_bytes": memory.get("peak_working_set_bytes"),
        "passed": passed,
    }


def _finite_mean(values: Any, label: str) -> float:
    """Mean of finite cells, or conservative zero when support is absent."""

    import numpy as np

    array = np.asarray(values, dtype=np.float64)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return 0.0
    return float(np.mean(finite))


def _compute_test_gates_replay(
    *,
    test_metrics: Any,
    test_diagnostics: Sequence[Mapping[str, Any]],
    R_diagnostics: Mapping[str, Any],
    power: Mapping[str, Any],
    latency: Mapping[str, Any],
    stronger_relevance_method: str,
    g1_invariants: Mapping[str, bool],
    g9_passed: bool,
) -> tuple[Mapping[str, bool], Mapping[str, Any]]:
    import numpy as np

    metric_index = {name: index for index, name in enumerate(EXPECTED_METRICS)}
    method_index = {name: index for index, name in enumerate(EXPECTED_METHODS)}
    values = np.asarray(test_metrics, dtype=np.float64)
    _require_shape(
        values,
        (3, len(EXPECTED_METHODS), values.shape[2], len(EXPECTED_METRICS)),
        "test metric tensor",
    )
    averaged = _nanmean_over_seeds(values)
    bootstrap: dict[str, Mapping[str, Any]] = {}

    def comparison(metric: str, left: str, right: str) -> Mapping[str, Any]:
        key = f"{metric}:{left}-minus-{right}"
        left_values = averaged[method_index[left], :, metric_index[metric]]
        right_values = averaged[method_index[right], :, metric_index[metric]]
        common = np.isfinite(left_values) & np.isfinite(right_values)
        if not np.any(common):
            # Registered metrics are bounded in [-1, 1].  This finite sentinel
            # fails every affected threshold without emitting non-JSON values.
            record = {
                "point": 0.0,
                "lower": -1.0,
                "upper": 1.0,
                "users": 0,
                "support_failed": True,
            }
        else:
            record = {
                **_paired_bootstrap(
                    left_values - right_values,
                    draws=10_000,
                    alpha=0.05,
                    seed=20263504,
                ),
                "support_failed": False,
            }
        bootstrap[key] = record
        return record

    required_metric_series = (
        ("cable_pref", "conditional_admission_at_200"),
        ("raw_hybrid", "conditional_admission_at_200"),
        ("order_only", "conditional_admission_at_200"),
        ("uib_boundary", "conditional_admission_at_200"),
        ("wrong_boundary", "conditional_admission_at_200"),
        ("shuffled_direction", "conditional_admission_at_200"),
        ("cable_pref", "net_new_preferred_support"),
        ("raw_hybrid", "net_new_preferred_support"),
        ("cable_pref", "net_admission_advantage"),
        ("raw_hybrid", "net_admission_advantage"),
        ("cable_pref", "spce_at_10"),
        ("raw_hybrid", "spce_at_10"),
        ("bpr", "spce_at_10"),
        ("admission_only", "spce_at_10"),
        ("order_only", "spce_at_10"),
        ("uib_boundary", "spce_at_10"),
        ("wrong_boundary", "spce_at_10"),
        ("shuffled_direction", "spce_at_10"),
        ("cable_pref", "preferred_exposure_at_10"),
        ("raw_hybrid", "preferred_exposure_at_10"),
        ("cable_pref", "ndcg_at_10"),
        (stronger_relevance_method, "ndcg_at_10"),
        ("cable_pref", "recall_at_10"),
        (stronger_relevance_method, "recall_at_10"),
        ("cable_pref", "low_rating_intrusion_at_10"),
        ("raw_hybrid", "low_rating_intrusion_at_10"),
    )
    required_metric_support_complete = bool(
        all(
            np.any(
                np.isfinite(
                    averaged[method_index[method], :, metric_index[metric]]
                )
            )
            for method, metric in required_metric_series
        )
    )

    admission_raw = comparison(
        "conditional_admission_at_200", "cable_pref", "raw_hybrid"
    )
    admission_order = comparison(
        "conditional_admission_at_200", "cable_pref", "order_only"
    )
    net_support = comparison(
        "net_new_preferred_support", "cable_pref", "raw_hybrid"
    )
    net_advantage = comparison(
        "net_admission_advantage", "cable_pref", "raw_hybrid"
    )
    spce_raw = comparison("spce_at_10", "cable_pref", "raw_hybrid")
    spce_bpr = comparison("spce_at_10", "cable_pref", "bpr")
    preferred_exposure = comparison(
        "preferred_exposure_at_10", "cable_pref", "raw_hybrid"
    )
    ndcg = comparison(
        "ndcg_at_10", "cable_pref", stronger_relevance_method
    )
    recall = comparison(
        "recall_at_10", "cable_pref", stronger_relevance_method
    )
    intrusion = comparison(
        "low_rating_intrusion_at_10", "cable_pref", "raw_hybrid"
    )
    g1 = bool(g1_invariants and all(g1_invariants.values()))
    g2 = bool(
        admission_raw["point"] >= 0.020
        and admission_raw["lower"] > 0.0
        and admission_order["point"] >= 0.010
        and admission_order["lower"] > 0.0
        and net_support["point"] >= 0.010
        and net_support["lower"] > 0.0
        and net_advantage["point"] > 0.0
    )
    g3 = bool(
        spce_raw["point"] >= 0.005
        and spce_raw["lower"] > 0.0
        and spce_bpr["point"] >= 0.005
        and spce_bpr["lower"] > 0.0
        and preferred_exposure["point"] > 0.0
    )
    g4 = bool(
        ndcg["point"] >= -0.0002
        and ndcg["lower"] > -0.001
        and recall["lower"] > -0.002
        and intrusion["upper"] <= 0.002
    )
    cable_admission = _finite_mean(
        averaged[4, :, metric_index["conditional_admission_at_200"]],
        "CABLE admission",
    )
    cable_spce = _finite_mean(
        averaged[4, :, metric_index["spce_at_10"]], "CABLE sPCE"
    )
    g5 = bool(
        required_metric_support_complete
        and all(
            cable_admission
            > _finite_mean(
                averaged[
                    method_index[name],
                    :,
                    metric_index["conditional_admission_at_200"],
                ],
                f"{name} admission",
            )
            for name in (
                "order_only",
                "uib_boundary",
                "wrong_boundary",
                "shuffled_direction",
            )
        )
        and all(
            cable_spce
            > _finite_mean(
                averaged[method_index[name], :, metric_index["spce_at_10"]],
                f"{name} sPCE",
            )
            for name in (
                "admission_only",
                "order_only",
                "uib_boundary",
                "wrong_boundary",
                "shuffled_direction",
            )
        )
    )
    first = test_diagnostics[0]
    admission_changed = sum(
        int(record["admission_changed_count"]) for record in test_diagnostics
    )
    admission_total = sum(
        int(record["admission_total"]) for record in test_diagnostics
    )
    spce_changed = sum(
        int(record["spce_changed_count"]) for record in test_diagnostics
    )
    spce_total = sum(int(record["spce_total"]) for record in test_diagnostics)
    g6 = bool(
        int(R_diagnostics["selected_pairs"]) >= 20_000
        and int(R_diagnostics["selected_pair_users"]) >= 1000
        and int(first["fixed_pairs"]) >= 5000
        and int(first["pair_users"]) >= 1000
        and int(first["unique_bpr_missed_preferred_endpoints"]) >= 5000
        and int(first["missed_endpoint_users"]) >= 1000
        and admission_total > 0
        and admission_changed / admission_total >= 0.05
        and spce_total > 0
        and spce_changed / spce_total >= 0.02
        and bool(power["passed"])
    )
    stable_count = 0
    seed_records: list[Mapping[str, Any]] = []
    for seed_row, seed in enumerate(EXPECTED_SEEDS):
        seed_values = values[seed_row]
        admission_vs_raw = _finite_mean(
            seed_values[4, :, metric_index["conditional_admission_at_200"]]
            - seed_values[1, :, metric_index["conditional_admission_at_200"]],
            f"seed {seed} admission versus raw",
        )
        admission_vs_order = _finite_mean(
            seed_values[4, :, metric_index["conditional_admission_at_200"]]
            - seed_values[2, :, metric_index["conditional_admission_at_200"]],
            f"seed {seed} admission versus order",
        )
        spce_vs_raw = _finite_mean(
            seed_values[4, :, metric_index["spce_at_10"]]
            - seed_values[1, :, metric_index["spce_at_10"]],
            f"seed {seed} sPCE versus raw",
        )
        ndcg_vs_raw = _finite_mean(
            seed_values[4, :, metric_index["ndcg_at_10"]]
            - seed_values[1, :, metric_index["ndcg_at_10"]],
            f"seed {seed} NDCG versus raw",
        )
        stable = bool(
            admission_vs_raw > 0.0
            and admission_vs_order > 0.0
            and spce_vs_raw > 0.0
            and ndcg_vs_raw >= -0.0002
        )
        stable_count += int(stable)
        seed_records.append(
            {
                "seed": seed,
                "admission_vs_raw": admission_vs_raw,
                "admission_vs_order": admission_vs_order,
                "spce_vs_raw": spce_vs_raw,
                "ndcg_vs_raw": ndcg_vs_raw,
                "stable": stable,
            }
        )
    g7 = bool(
        required_metric_support_complete
        and stable_count >= 2
        and all(record["ndcg_vs_raw"] >= -0.001 for record in seed_records)
    )
    g8 = bool(latency["passed"])
    g9 = bool(g9_passed)
    gates = {
        "G1": g1,
        "G2": g2,
        "G3": g3,
        "G4": g4,
        "G5": g5,
        "G6": g6,
        "G7": g7,
        "G8": g8,
        "G9": g9,
    }
    return gates, {
        "bootstrap": bootstrap,
        "seed_stability": seed_records,
        "support": {
            "R": dict(R_diagnostics),
            "T": dict(first),
            "admission_change_fraction": admission_changed / max(1, admission_total),
            "spce_change_fraction": spce_changed / max(1, spce_total),
        },
        "power": power,
        "latency": latency,
        "G1_invariants": dict(g1_invariants),
        "stronger_relevance_method": stronger_relevance_method,
        "required_metric_support_complete": required_metric_support_complete,
    }


def replay_scientific_gates(
    *,
    config: Mapping[str, Any],
    result: Mapping[str, Any],
    closure: CandidateClosure,
    run_directory: Path,
    archive_path: Path,
    source_hashes: Mapping[str, str],
    runner_process_record: Mapping[str, Any],
) -> tuple[Mapping[str, bool], Mapping[str, Any]]:
    """Independently reconstruct raw evidence, choices, metrics, and G1--G9."""

    import numpy as np

    protocol_fingerprint = str(result.get("protocol_fingerprint_sha256", ""))
    execution_fingerprint = str(result.get("execution_fingerprint_sha256", ""))
    if not is_sha256(protocol_fingerprint) or not is_sha256(execution_fingerprint):
        raise IntegrityError("Result fingerprints are malformed")
    if (
        result.get("external_post_exit_verification_required") is not True
        or contained_file(
            run_directory,
            str(result.get("raw_validation_file", "")),
            "result-bound raw validation",
        )
        != closure.raw_validation_path
        or str(result.get("raw_validation_sha256", "")).lower()
        != sha256_file(closure.raw_validation_path)
    ):
        raise IntegrityError("Result raw-validation binding differs from closure")
    if closure.termination_stage == "post_T_all_gates":
        if closure.raw_test_path is None or closure.latency_path is None:
            raise IntegrityError("Post-T result lacks closure evidence")
        if (
            contained_file(
                run_directory,
                str(result.get("raw_test_file", "")),
                "result-bound raw test",
            )
            != closure.raw_test_path
            or str(result.get("raw_test_sha256", "")).lower()
            != sha256_file(closure.raw_test_path)
            or contained_file(
                run_directory,
                str(result.get("latency_file", "")),
                "result-bound raw latency",
            )
            != closure.latency_path
            or str(result.get("latency_sha256", "")).lower()
            != sha256_file(closure.latency_path)
        ):
            raise IntegrityError("Result test/latency bindings differ from closure")
    validation = _load_npz_exact(
        closure.raw_validation_path,
        RAW_VALIDATION_FIELDS,
        "raw validation arrays",
    )
    user_ids, movie_ids = _verify_common_raw_contract(
        validation,
        schema="cable-pref-raw-validation-v1",
        protocol_fingerprint=protocol_fingerprint,
        execution_fingerprint=execution_fingerprint,
    )
    provenance = _verify_provenance_and_replay_archive(
        config=config,
        result=result,
        closure=closure,
        run_directory=run_directory,
        archive_path=archive_path,
        source_hashes=source_hashes,
        raw_user_ids=user_ids,
        raw_movie_ids=movie_ids,
    )
    if (
        provenance["protocol_fingerprint"] != protocol_fingerprint
        or provenance["execution_fingerprint"] != execution_fingerprint
    ):
        raise IntegrityError("Raw/result provenance fingerprints differ")
    stages = require_mapping(provenance["stages"], "authenticated stage replay")
    immutable = _verify_immutable_artifacts(
        raw=validation,
        result=result,
        run_directory=run_directory,
        user_count=user_ids.size,
        catalog_count=movie_ids.size,
    )
    _same_array(
        immutable["collaborative_mask"],
        provenance["collaborative_mask"],
        "A-derived collaborative mask",
    )
    R_pairs, R_diagnostics = _verify_stage_outcome_arrays(
        validation,
        prefix="R",
        user_ids=user_ids,
        movie_ids=movie_ids,
        source_events=require_mapping(stages["R"], "authenticated R events"),
    )
    V_pairs, V_pair_diagnostics = _verify_stage_outcome_arrays(
        validation,
        prefix="V",
        user_ids=user_ids,
        movie_ids=movie_ids,
        source_events=require_mapping(stages["V"], "authenticated V events"),
    )
    del R_pairs, V_pairs
    training_record = read_json_mapping(
        contained_file(
            run_directory,
            "training_diagnostics.json",
            "training diagnostics",
        ),
        "training diagnostics",
    )
    R_manifest_report = _verify_R_target_blind_manifest(
        training_record=training_record,
        run_directory=run_directory,
        protocol_fingerprint=protocol_fingerprint,
        execution_fingerprint=execution_fingerprint,
        user_ids=user_ids,
        movie_ids=movie_ids,
        A_events=require_mapping(stages["A"], "authenticated A events"),
        semantic_matrix=immutable["semantic_matrix"],
        bpr_user_matrix=immutable["bpr_user_matrix"],
        bpr_item_matrix=immutable["bpr_item_matrix"],
        collaborative_mask=immutable["collaborative_mask"],
    )
    training_report = _verify_training_evidence(
        raw=validation,
        training_record=training_record,
        run_directory=run_directory,
        R_diagnostics=R_diagnostics,
    )
    V_histories = {
        int(user_id): (
            *require_mapping(stages["A"], "authenticated A events")[int(user_id)],
            *require_mapping(stages["R"], "authenticated R events")[int(user_id)],
        )
        for user_id in user_ids
    }
    V_manifests = _load_stage_manifests(
        raw=validation,
        prefix="V",
        run_directory=run_directory,
        protocol_fingerprint=protocol_fingerprint,
        execution_fingerprint=execution_fingerprint,
        user_ids=user_ids,
    )
    V_manifest_report = _verify_manifest_oracles(
        manifests=V_manifests,
        prefix="V",
        user_ids=user_ids,
        movie_ids=movie_ids,
        expected_histories=V_histories,
        semantic_matrix=immutable["semantic_matrix"],
        bpr_user_matrix=immutable["bpr_user_matrix"],
        bpr_item_matrix=immutable["bpr_item_matrix"],
        collaborative_mask=immutable["collaborative_mask"],
    )
    selected_index, selected_alpha, stronger, choice_replay = (
        _validation_choice_replay(
            manifests=V_manifests, raw=validation, movie_ids=movie_ids
        )
    )
    if (
        _scalar_int(validation["selected_alpha_index"], "selected alpha index")
        != selected_index
        or not math.isclose(
            _scalar_float(validation["selected_alpha"], "selected alpha"),
            selected_alpha,
            rel_tol=0.0,
            abs_tol=1.0e-7,
        )
        or _decode_scalar_string(
            validation["stronger_relevance_method"], "stronger relevance method"
        )
        != stronger
        or int(result.get("selected_alpha_index", -1)) != selected_index
        or float(result.get("selected_alpha", float("nan"))) != selected_alpha
        or result.get("stronger_relevance_method") != stronger
    ):
        raise IntegrityError("Validation-selected choice differs from independent replay")
    frozen_choices = _verify_frozen_choices(
        run_directory=run_directory,
        execution_fingerprint=execution_fingerprint,
        selected_index=selected_index,
        selected_alpha=selected_alpha,
        stronger=stronger,
        replay=choice_replay,
    )
    V_manifest_utc = _decode_scalar_string(
        validation["V_manifest_published_utc"], "V manifest timestamp"
    )
    V_binary_utc = _decode_scalar_string(
        validation["V_binary_relevance_opened_utc"], "V binary timestamp"
    )
    choices_utc = _decode_scalar_string(
        validation["choices_frozen_utc"], "choice-freeze timestamp"
    )
    V_exact_utc = _decode_scalar_string(
        validation["V_exact_preference_opened_utc"], "V exact timestamp"
    )
    if (
        not (V_manifest_utc <= V_binary_utc <= choices_utc <= V_exact_utc)
        or frozen_choices.get("frozen_utc") != choices_utc
        or not _scalar_bool(
            validation["target_blind_before_binary_relevance"],
            "V target-blind chronology",
        )
        or not _scalar_bool(
            validation["choices_before_exact_preferences"],
            "V choice chronology",
        )
    ):
        raise IntegrityError("Validation target-blind chronology differs")

    V_metric_rows: list[Any] = []
    V_diagnostics: list[Mapping[str, int]] = []
    for seed in EXPECTED_SEEDS:
        values, diagnostics = _evaluate_stage_from_raw(
            manifest=V_manifests[seed],
            raw=validation,
            stage_prefix="V",
            alpha_index=selected_index,
        )
        V_metric_rows.append(values)
        V_diagnostics.append(diagnostics)
    V_metrics = np.stack(V_metric_rows, axis=0)
    _verify_metric_tensor(
        validation["per_user_metrics"], V_metrics, "validation"
    )
    _verify_stage_diagnostics(validation, prefix="V", diagnostics=V_diagnostics)
    if (
        _scalar_int(validation["V_fixed_pairs"], "V fixed pairs")
        != int(V_pair_diagnostics["selected_pairs"])
        or _scalar_int(validation["V_pair_users"], "V pair users")
        != int(V_pair_diagnostics["selected_pair_users"])
    ):
        raise IntegrityError("Raw V pair support differs from pair replay")
    power = _power_audit_replay(V_metrics)
    comparison_names = (
        "admission_vs_raw",
        "admission_vs_order_only",
        "spce_vs_raw",
        "spce_vs_bpr",
    )
    if _decode_strings(
        validation["power_comparison_names"], "power comparisons"
    ) != comparison_names:
        raise IntegrityError("Power comparison inventory/order changed")
    recorded_fractions = np.asarray(
        validation["power_detection_fractions"], dtype=np.float64
    )
    expected_fractions = np.asarray(
        [power["comparisons"][name]["detection_fraction"] for name in comparison_names],
        dtype=np.float64,
    )
    if (
        not np.array_equal(recorded_fractions, expected_fractions)
        or _scalar_bool(validation["power_passed"], "power passed")
        != bool(power["passed"])
    ):
        raise IntegrityError("Validation power audit differs from independent replay")
    result_power = require_mapping(result.get("power_audit"), "result power audit")
    result_comparisons = require_mapping(
        result_power.get("comparisons"), "result power comparisons"
    )
    if set(result_comparisons) != set(comparison_names) or bool(
        result_power.get("passed")
    ) != bool(power["passed"]):
        raise IntegrityError("Result power inventory/pass flag differs")
    for name in comparison_names:
        observed = require_mapping(result_comparisons[name], f"result power {name}")
        expected = power["comparisons"][name]
        for field in ("detection_fraction", "experiments", "detected", "passed"):
            if observed.get(field) != expected[field]:
                raise IntegrityError(f"Result power replay differs: {name}/{field}")

    R_support_passed = bool(
        int(R_diagnostics["selected_pairs"]) >= 20_000
        and int(R_diagnostics["selected_pair_users"]) >= 1000
    )
    common_report: dict[str, Any] = {
        "schema": "cable-pref-independent-scientific-replay-v1",
        "protocol_fingerprint_sha256": protocol_fingerprint,
        "execution_fingerprint_sha256": execution_fingerprint,
        "archive_cohort_temporal_replay": {
            "passed": True,
            "eligible_user_count": int(provenance["eligible_user_count"]),
            "selected_user_count": int(user_ids.size),
            "catalog_item_count": int(movie_ids.size),
            "cohort_user_ids_sha256": provenance["cohort_user_ids_sha256"],
        },
        "R_target_blind_manifest": R_manifest_report,
        "V_manifest_oracle": V_manifest_report,
        "training": training_report,
        "validation_choices": {
            "selected_alpha_index": selected_index,
            "selected_alpha": selected_alpha,
            "stronger_relevance_method": stronger,
        },
        "validation_power": power,
        "R_support_passed": R_support_passed,
        "raw_validation_metrics_replayed": True,
        "immutable_artifacts_replayed": True,
        "hardware_provenance": {
            "machine_record_reverified": True,
            "runner_peak_resident_memory_bytes": require_mapping(
                runner_process_record.get("memory"), "runner memory"
            ).get("peak_working_set_bytes"),
        },
    }
    if closure.termination_stage == "pre_T_power_audit":
        if bool(power["passed"]) and R_support_passed:
            raise IntegrityError("Runner stopped before T despite passing pre-T gates")
        if (
            result.get("kill_project") is not True
            or result.get("runner_candidate_promising") is not False
            or result.get("R_support_passed") is not R_support_passed
        ):
            raise IntegrityError("Pre-T result disposition differs from replay")
        expected_reason = (
            "validation_power_audit_failed"
            if not bool(power["passed"])
            else "registered_R_support_failed"
        )
        if result.get("kill_reason") != expected_reason:
            raise IntegrityError("Pre-T kill reason differs from replay")
        gates = {name: False for name in GATE_NAMES}
        common_report.update(
            {
                "termination_stage": "pre_T_power_audit",
                "test_opened": False,
                "kill_before_T_independently_justified": True,
                "gates": gates,
            }
        )
        return gates, common_report

    if not bool(power["passed"]) or not R_support_passed:
        raise IntegrityError("Post-T artifacts exist despite a failed pre-T kill gate")
    if closure.raw_test_path is None or closure.latency_path is None:
        raise IntegrityError("Post-T closure lacks raw test/latency evidence")
    test = _load_npz_exact(closure.raw_test_path, RAW_TEST_FIELDS, "raw test arrays")
    test_user_ids, test_movie_ids = _verify_common_raw_contract(
        test,
        schema="cable-pref-raw-test-v1",
        protocol_fingerprint=protocol_fingerprint,
        execution_fingerprint=execution_fingerprint,
    )
    _same_array(user_ids, test_user_ids, "validation/test cohort")
    _same_array(movie_ids, test_movie_ids, "validation/test catalog")
    _verify_same_immutable_raw_binding(validation, test)
    if (
        _scalar_int(test["selected_alpha_index"], "test selected alpha index")
        != selected_index
        or not math.isclose(
            _scalar_float(test["selected_alpha"], "test selected alpha"),
            selected_alpha,
            rel_tol=0.0,
            abs_tol=1.0e-7,
        )
        or _decode_scalar_string(
            test["stronger_relevance_method"], "test stronger method"
        )
        != stronger
        or not _scalar_bool(test["test_opened"], "test-opened flag")
    ):
        raise IntegrityError("Test raw choices/open flag differ")
    T_pairs, T_pair_diagnostics = _verify_stage_outcome_arrays(
        test,
        prefix="T",
        user_ids=user_ids,
        movie_ids=movie_ids,
        source_events=require_mapping(stages["T"], "authenticated T events"),
    )
    T_histories = {
        int(user_id): (
            *require_mapping(stages["A"], "authenticated A events")[int(user_id)],
            *require_mapping(stages["R"], "authenticated R events")[int(user_id)],
            *require_mapping(stages["V"], "authenticated V events")[int(user_id)],
        )
        for user_id in user_ids
    }
    T_manifests = _load_stage_manifests(
        raw=test,
        prefix="T",
        run_directory=run_directory,
        protocol_fingerprint=protocol_fingerprint,
        execution_fingerprint=execution_fingerprint,
        user_ids=user_ids,
    )
    T_manifest_report = _verify_manifest_oracles(
        manifests=T_manifests,
        prefix="T",
        user_ids=user_ids,
        movie_ids=movie_ids,
        expected_histories=T_histories,
        semantic_matrix=immutable["semantic_matrix"],
        bpr_user_matrix=immutable["bpr_user_matrix"],
        bpr_item_matrix=immutable["bpr_item_matrix"],
        collaborative_mask=immutable["collaborative_mask"],
        action_pairs=T_pairs,
    )
    T_metric_rows: list[Any] = []
    T_diagnostics: list[Mapping[str, int]] = []
    for seed in EXPECTED_SEEDS:
        values, diagnostics = _evaluate_stage_from_raw(
            manifest=T_manifests[seed],
            raw=test,
            stage_prefix="T",
            alpha_index=selected_index,
        )
        T_metric_rows.append(values)
        T_diagnostics.append(diagnostics)
    T_metrics = np.stack(T_metric_rows, axis=0)
    _verify_metric_tensor(test["per_user_metrics"], T_metrics, "test")
    _verify_stage_diagnostics(test, prefix="T", diagnostics=T_diagnostics)
    if (
        _scalar_int(test["T_fixed_pairs"], "T fixed pairs")
        != int(T_pair_diagnostics["selected_pairs"])
        or _scalar_int(test["T_pair_users"], "T pair users")
        != int(T_pair_diagnostics["selected_pair_users"])
    ):
        raise IntegrityError("Raw T pair support differs from pair replay")
    action = require_mapping(T_manifest_report["action"], "action replay")
    for raw_field, replay_field in (
        ("action_checked", "checked"),
        ("action_violations", "violations"),
        ("action_tie_boundaries", "tie_boundaries"),
    ):
        if _scalar_int(test[raw_field], raw_field) != int(action[replay_field]):
            raise IntegrityError("Raw leave-out action diagnostic differs")
    if _scalar_bool(test["action_passed"], "action passed") != bool(
        action["passed"]
    ):
        raise IntegrityError("Raw leave-out action pass flag differs")
    T_manifest_utc = _decode_scalar_string(
        test["T_manifest_published_utc"], "T manifest timestamp"
    )
    T_opened_utc = _decode_scalar_string(test["T_opened_utc"], "T opened timestamp")
    if not T_manifest_utc or not T_opened_utc or T_manifest_utc > T_opened_utc:
        raise IntegrityError("T manifest did not precede target opening")
    g1_invariants = {
        "exact_candidate_counts": True,
        "unique_unseen_candidates": True,
        "semantic_branch_bpr_novel": True,
        "shared_bpr_branch": True,
        "faiss_matrix_oracle_exact": True,
        "leaveout_action_consistency": bool(action["passed"]),
        "immutable_geometry": True,
        "target_blind_manifest_precedes_T": True,
        "unsupported_bpr_factors_zero": True,
    }
    if _decode_strings(test["g1_invariant_names"], "G1 invariant names") != tuple(
        g1_invariants
    ) or not np.array_equal(
        np.asarray(test["g1_invariant_values"], dtype=np.uint8),
        np.asarray(tuple(g1_invariants.values()), dtype=np.uint8),
    ):
        raise IntegrityError("Raw G1 invariants differ from independent replay")
    latency_raw = _load_npz_exact(
        closure.latency_path, RAW_LATENCY_FIELDS, "raw latency arrays"
    )
    latency = _verify_latency_replay(
        raw=latency_raw,
        protocol_fingerprint=protocol_fingerprint,
        execution_fingerprint=execution_fingerprint,
        cohort_user_ids=user_ids,
        catalog_count=movie_ids.size,
        runner_process_record=runner_process_record,
    )
    gates, gate_details = _compute_test_gates_replay(
        test_metrics=T_metrics,
        test_diagnostics=T_diagnostics,
        R_diagnostics=R_diagnostics,
        power=power,
        latency=latency,
        stronger_relevance_method=stronger,
        g1_invariants=g1_invariants,
        g9_passed=True,
    )
    if _decode_strings(test["gate_names"], "raw gate names") != GATE_NAMES or not np.array_equal(
        np.asarray(test["gate_values"], dtype=np.uint8),
        np.asarray([gates[name] for name in GATE_NAMES], dtype=np.uint8),
    ):
        raise IntegrityError("Raw gate values differ from independent replay")
    if (
        result.get("kill_project") is not (not all(gates.values()))
        or result.get("kill_reason")
        != (None if all(gates.values()) else "one_or_more_registered_G1_G9_gates_failed")
    ):
        raise IntegrityError("Post-T project disposition differs from replay")
    common_report.update(
        {
            "termination_stage": "post_T_all_gates",
            "test_opened": True,
            "T_manifest_oracle": T_manifest_report,
            "raw_test_metrics_replayed": True,
            "latency": latency,
            "gate_details": gate_details,
            "gates": gates,
        }
    )
    return gates, common_report


def _extract_result_gates(result: Mapping[str, Any]) -> Mapping[str, bool]:
    gate_container = result.get("promise_gate", result.get("gates"))
    gate_mapping = require_mapping(gate_container, "result promise gates")
    if set(gate_mapping) != set(GATE_NAMES):
        raise IntegrityError("Result gate inventory is not exactly G1--G9")
    return {name: require_bool(gate_mapping[name], f"result.{name}") for name in GATE_NAMES}


def verify_gate_equality(
    result: Mapping[str, Any], replayed: Mapping[str, bool]
) -> bool:
    if set(replayed) != set(GATE_NAMES):
        raise IntegrityError("Verifier gate inventory is not exactly G1--G9")
    recorded = _extract_result_gates(result)
    if dict(recorded) != dict(replayed):
        raise IntegrityError("Runner and independent verifier gate values differ")
    verdict = all(bool(replayed[name]) for name in GATE_NAMES)
    # The runner is never allowed to make its own result authoritative.
    if result.get("PROMISING") is not False:
        raise IntegrityError("Runner PROMISING must remain false/non-authoritative")
    candidate_verdict = result.get("runner_candidate_promising")
    if candidate_verdict is not None and require_bool(
        candidate_verdict, "runner_candidate_promising"
    ) != verdict:
        raise IntegrityError("Runner candidate verdict disagrees with replay")
    return verdict


def verify_outer_authorization(
    *, outer_lock: Path, owner_pid: int, token: str
) -> Mapping[str, Any]:
    record = read_json_mapping(outer_lock, "outer launch lock")
    if record.get("schema") != "cable-pref-exclusive-owner-lock-v1":
        raise IntegrityError("Outer lock schema changed")
    if int(record.get("pid", -1)) != owner_pid or not pid_is_running(owner_pid):
        raise IntegrityError("Outer launcher owner is not alive")
    if record.get("token_sha256") != sha256_text(token):
        raise IntegrityError("Outer launcher token mismatch")
    return record


def verify_launch_record(
    *,
    launch_record_path: Path,
    project_root: Path,
    run_directory: Path,
    expected_paths: Mapping[str, Path],
    expected_environment: Mapping[str, str],
    expected_launcher_sha256: str,
) -> Mapping[str, Any]:
    verify_frozen_source_files(expected_paths)
    record = read_json_mapping(launch_record_path, "launch record")
    if record.get("schema") != "cable-pref-external-launch-v1":
        raise IntegrityError("Launch record schema changed")
    if Path(str(record.get("project_root", ""))).resolve() != project_root:
        raise IntegrityError("Launch record project root mismatch")
    if Path(str(record.get("run_directory", ""))).resolve() != run_directory:
        raise IntegrityError("Launch record run directory mismatch")
    python_executable = Path(str(record.get("python_executable", ""))).resolve()
    if python_executable != Path(sys.executable).resolve():
        raise IntegrityError("Launch interpreter path differs")
    expected_preflight_command = [
        str(python_executable),
        "-B",
        "-u",
        str(expected_paths["runner"]),
        "--self-test",
        "--config",
        str(expected_paths["config"]),
    ]
    if record.get("preflight_command") != expected_preflight_command:
        raise IntegrityError("Runner preflight command differs")
    expected_outcome_command = [
        str(python_executable),
        "-B",
        "-u",
        str(expected_paths["runner"]),
        "--config",
        str(expected_paths["config"]),
        "--protocol",
        str(expected_paths["protocol"]),
        "--output-dir",
        str(run_directory),
        "--local-dataset-archive",
        str(Path(str(record.get("local_dataset_archive", ""))).resolve()),
    ]
    if record.get("command") != expected_outcome_command:
        raise IntegrityError("Outcome command differs from source-bound invocation")
    fixed = require_mapping(record.get("execution_environment"), "launch environment")
    if dict(fixed) != dict(expected_environment):
        raise IntegrityError("Launch environment contract changed")
    if record.get("execution_environment_sha256") != environment_sha256(
        expected_environment
    ):
        raise IntegrityError("Launch environment fingerprint mismatch")
    source_hashes = require_mapping(record.get("source_sha256"), "launch source hashes")
    for name, path in expected_paths.items():
        if not path.is_file():
            raise IntegrityError(f"Bound source disappeared: {path}")
        actual = sha256_file(path)
        if str(source_hashes.get(name, "")).lower() != actual:
            raise IntegrityError(f"Launch source changed: {name}")
    if str(source_hashes.get("launcher", "")).lower() != expected_launcher_sha256:
        raise IntegrityError("Verifier launcher hash differs from parent binding")
    if str(source_hashes.get("python_executable", "")).lower() != sha256_file(
        python_executable
    ):
        raise IntegrityError("Launch interpreter hash differs")
    launcher_preflight = require_mapping(
        record.get("launcher_synthetic_preflight"), "launcher synthetic preflight"
    )
    if (
        launcher_preflight.get("scientific_schema_bound") is not True
        or launcher_preflight.get("outcome_launch_authorized") is not True
        or not all(value is True for value in launcher_preflight.values())
    ):
        raise IntegrityError("Launch record lacks a passing launcher preflight")
    runner_preflight = require_mapping(
        record.get("runner_synthetic_preflight"), "runner synthetic preflight"
    )
    checks = require_mapping(runner_preflight.get("checks"), "runner preflight checks")
    if (
        runner_preflight.get("schema") != "cable-pref-runner-self-test-v1"
        or runner_preflight.get("passed") is not True
        or runner_preflight.get("archive_opened") is not False
        or runner_preflight.get("archive_listed") is not False
        or runner_preflight.get("target_outcomes_accessed") is not False
        or set(checks) != EXPECTED_RUNNER_SELF_TEST_CHECKS
        or not all(value is True for value in checks.values())
        or tuple(runner_preflight.get("raw_validation_fields", ()))
        != RAW_VALIDATION_FIELDS
        or tuple(runner_preflight.get("raw_test_fields", ())) != RAW_TEST_FIELDS
        or tuple(runner_preflight.get("raw_latency_fields", ())) != RAW_LATENCY_FIELDS
    ):
        raise IntegrityError("Launch record runner preflight differs")
    preflight_stdout = Path(str(record.get("runner_preflight_stdout", ""))).resolve()
    preflight_stderr = Path(str(record.get("runner_preflight_stderr", ""))).resolve()
    expected_launch_directory = launch_record_path.resolve().parent
    run_id = str(record.get("run_id", ""))
    if (
        preflight_stdout
        != expected_launch_directory / f"{run_id}.preflight.stdout.log"
        or preflight_stderr
        != expected_launch_directory / f"{run_id}.preflight.stderr.log"
    ):
        raise IntegrityError("Runner preflight log paths differ from launch identity")
    if (
        not preflight_stdout.is_file()
        or not preflight_stderr.is_file()
        or sha256_file(preflight_stdout)
        != str(record.get("runner_preflight_stdout_sha256", "")).lower()
        or preflight_stderr.stat().st_size != 0
        or sha256_file(preflight_stderr) != EMPTY_SHA256
        or record.get("runner_preflight_stderr_zero_bytes") is not True
        or record.get("runner_preflight_stderr_sha256") != EMPTY_SHA256
    ):
        raise IntegrityError("Runner preflight persistent logs differ")
    try:
        persisted_preflight = json.loads(preflight_stdout.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("Persisted runner preflight is not JSON") from exc
    if persisted_preflight != runner_preflight:
        raise IntegrityError("Persisted/recorded runner preflight reports differ")
    return record


def run_verifier(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[1]
    paths = locked_paths(project_root)
    verify_frozen_source_files(paths)
    run_directory = args.verify_run_directory.resolve()
    candidate_path = args.candidate.resolve()
    report_path = args.verification_report.resolve()
    ledger_path = args.verifier_ledger.resolve()
    verifier_lock_path = run_directory / "cable_pref_post_exit_verifier.lock"
    if report_path.exists() or ledger_path.exists() or verifier_lock_path.exists():
        raise IntegrityError("Append-only verifier artifact collision")
    if candidate_path.parent != run_directory:
        raise IntegrityError("Candidate is outside the run directory")
    if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
        raise IntegrityError("An external marker already exists")

    expected_environment = execution_environment()
    launch_record = verify_launch_record(
        launch_record_path=args.launch_record.resolve(),
        project_root=project_root,
        run_directory=run_directory,
        expected_paths=paths,
        expected_environment=expected_environment,
        expected_launcher_sha256=str(args.expected_launcher_sha256).lower(),
    )
    recorded_hardware = require_mapping(
        launch_record.get("machine_hardware"), "launch machine hardware"
    )
    if (
        launch_record.get("machine_hardware_sha256")
        != sha256_bytes(canonical_json_bytes(recorded_hardware))
        or dict(recorded_hardware) != dict(machine_hardware_record())
    ):
        raise IntegrityError("Machine hardware/power-policy record changed after outcome")
    one_time_claim = Path(
        str(launch_record.get("one_time_launch_claim", ""))
    ).resolve()
    if (
        not one_time_claim.is_file()
        or sha256_file(one_time_claim)
        != str(launch_record.get("one_time_launch_claim_sha256", "")).lower()
    ):
        raise IntegrityError("One-time launch claim is missing or changed")
    claim = read_json_mapping(one_time_claim, "one-time launch claim")
    if (
        claim.get("schema") != "cable-pref-one-time-launch-claim-v1"
        or Path(str(claim.get("run_directory", ""))).resolve() != run_directory
        or claim.get("automatic_retry_or_resume_forbidden") is not True
    ):
        raise IntegrityError("One-time launch claim content differs")
    verify_outer_authorization(
        outer_lock=args.outer_lock.resolve(),
        owner_pid=int(args.outer_lock_owner_pid),
        token=str(args.outer_lock_token),
    )
    launcher_child_pid = int(args.launcher_child_pid)
    if launcher_child_pid <= 0 or pid_is_running(launcher_child_pid):
        raise IntegrityError("Outcome child has not exited")
    if args.runner_stderr.resolve().stat().st_size != 0:
        raise IntegrityError("Runner stderr is nonempty")
    runner_process_record_path = args.runner_process_record.resolve()
    expected_process_record_path = args.launch_record.resolve().with_name(
        f"{launch_record.get('run_id')}.runner-process.json"
    )
    if runner_process_record_path != expected_process_record_path:
        raise IntegrityError("Runner process record path differs from launch identity")
    runner_process_record = read_json_mapping(
        runner_process_record_path, "runner process record"
    )
    memory_record = require_mapping(
        runner_process_record.get("memory"), "runner process memory"
    )
    if (
        runner_process_record.get("schema") != "cable-pref-child-process-exit-v1"
        or int(runner_process_record.get("pid", -1)) != launcher_child_pid
        or int(runner_process_record.get("return_code", -1)) != 0
        or not str(runner_process_record.get("started_utc", ""))
        or not str(runner_process_record.get("finished_utc", ""))
        or (
            os.name == "nt"
            and int(memory_record.get("peak_working_set_bytes") or 0) <= 0
        )
    ):
        raise IntegrityError("Runner process exit/memory record is incomplete")

    config = read_json_mapping(paths["config"], "CABLE-PREF config")
    verify_config_contract(config)
    dataset = require_mapping(config.get("dataset"), "config.dataset")
    expected_archive = str(dataset.get("expected_archive_sha256", "")).lower()
    if not is_sha256(expected_archive):
        raise IntegrityError("Configured archive SHA-256 is malformed")
    expected_archive_size = require_int(
        dataset.get("expected_archive_size_bytes"),
        "config.dataset.expected_archive_size_bytes",
    )
    expected_archive_md5 = str(
        dataset.get("expected_official_sidecar_md5", "")
    ).lower()
    if len(expected_archive_md5) != 32:
        raise IntegrityError("Configured archive MD5 is malformed")
    if str(launch_record.get("local_dataset_archive_sha256", "")).lower() != expected_archive:
        raise IntegrityError("Launch archive hash is not the registered archive")
    if int(launch_record.get("local_dataset_archive_size_bytes", -1)) != expected_archive_size:
        raise IntegrityError("Launch archive size is not the registered size")
    if str(launch_record.get("local_dataset_archive_md5", "")).lower() != expected_archive_md5:
        raise IntegrityError("Launch archive MD5 is not the registered sidecar")
    archive_path = Path(str(launch_record.get("local_dataset_archive", ""))).resolve()
    if (
        not archive_path.is_file()
        or archive_path.stat().st_size != expected_archive_size
        or sha256_file(archive_path) != expected_archive
        or md5_file(archive_path) != expected_archive_md5
    ):
        raise IntegrityError("Registered archive changed during outcome execution")
    source_hashes = require_mapping(launch_record.get("source_sha256"), "source hashes")
    closure = verify_candidate_closure(
        run_directory=run_directory,
        candidate_path=candidate_path,
        source_hashes=source_hashes,
        expected_archive_sha256=expected_archive,
    )

    # Candidate closure must be complete before verifier-owned files are added.
    create_empty_file_exclusive(ledger_path)
    install_async_exception_hooks(ledger_path)
    verifier_lock = ExclusiveOwnerLock(verifier_lock_path, "post-exit-verifier")
    verifier_lock.acquire()
    try:
        verifier_lock.assert_owned()
        result = read_json_mapping(closure.result_path, "CABLE-PREF result")
        if result.get("termination_stage") != closure.termination_stage:
            raise IntegrityError("Result/candidate termination-stage mismatch")
        if result.get("test_opened") is not closure.test_opened:
            raise IntegrityError("Result/candidate test-opened mismatch")
        gates, replay_report = replay_scientific_gates(
            config=config,
            result=result,
            closure=closure,
            run_directory=run_directory,
            archive_path=archive_path,
            source_hashes=source_hashes,
            runner_process_record=runner_process_record,
        )
        verdict = verify_gate_equality(result, gates)
        if ledger_path.stat().st_size != 0:
            raise IntegrityError("Verifier asynchronous-error ledger is nonempty")
        report = {
            "schema": "cable-pref-post-exit-verification-v1",
            "verified_utc": utc_now(),
            "verifier_pid": os.getpid(),
            "runner_pid": closure.runner_pid,
            "termination_stage": closure.termination_stage,
            "test_opened": closure.test_opened,
            "source_sha256": dict(source_hashes),
            "execution_fingerprint_sha256": closure.candidate.get(
                "execution_fingerprint_sha256"
            ),
            "verified_recursive_artifact_count": len(closure.artifact_hashes),
            "verified_recursive_artifact_sha256": dict(closure.artifact_hashes),
            "scientific_replay": replay_report,
            "runner_process_record": str(runner_process_record_path),
            "runner_process_record_sha256": sha256_file(runner_process_record_path),
            "gates": dict(gates),
            "promise_gate_passed": verdict,
            "runner_lock": str(closure.runner_lock),
            "runner_lock_released": True,
            "verifier_lock": str(verifier_lock.path),
            "verifier_lock_release_pending": True,
            "verifier_async_ledger": ledger_path.name,
            "verifier_async_ledger_sha256": EMPTY_SHA256,
            "external_marker_publication_authorized": True,
        }
        publish_json_exclusive(report_path, report)
    finally:
        verifier_lock.release()
    if verifier_lock_path.exists():
        raise IntegrityError("Verifier lock remains after verifier exit")
    return 0


def run_launch(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[1]
    paths = locked_paths(project_root)
    config_path = args.config.resolve()
    protocol_path = args.protocol.resolve()
    if config_path != paths["config"] or protocol_path != paths["protocol"]:
        raise IntegrityError("Only the project-locked config/protocol paths are authorized")
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing bound {name}: {path}")
    verify_frozen_source_files(paths)
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise IntegrityError("Launcher must run from the workspace virtual environment")
    python_executable = Path(sys.executable).resolve()
    config = read_json_mapping(config_path, "CABLE-PREF config")
    verify_config_contract(config)
    dataset = require_mapping(config.get("dataset"), "config.dataset")
    expected_archive = str(dataset.get("expected_archive_sha256", "")).lower()
    if not is_sha256(expected_archive):
        raise IntegrityError("Configured archive SHA-256 is malformed")
    expected_archive_size = require_int(
        dataset.get("expected_archive_size_bytes"),
        "config.dataset.expected_archive_size_bytes",
    )
    expected_archive_md5 = str(
        dataset.get("expected_official_sidecar_md5", "")
    ).lower()
    if len(expected_archive_md5) != 32:
        raise IntegrityError("Configured archive MD5 is malformed")
    if args.local_dataset_archive is None:
        raise IntegrityError("A registered local dataset archive is required")
    local_archive = args.local_dataset_archive.resolve()
    if (
        not local_archive.is_file()
        or local_archive.stat().st_size != expected_archive_size
        or sha256_file(local_archive) != expected_archive
        or md5_file(local_archive) != expected_archive_md5
    ):
        raise IntegrityError("Local dataset archive fails registered SHA-256")

    run_id = safe_run_id(
        args.run_id
        or (
            "cable-pref-poc-v1-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            + "-"
            + uuid.uuid4().hex[:12]
        )
    )
    output_root = args.output_root.resolve()
    run_parent = output_root / "cable_pref_poc_runs"
    run_directory = (run_parent / run_id).resolve()
    if run_directory.exists():
        raise FileExistsError(f"Run directory already exists: {run_directory}")
    run_parent.mkdir(parents=True, exist_ok=True)
    outer_lock = ExclusiveOwnerLock(
        output_root / "cable_pref_outer_launch.lock", "outer-launch"
    )

    launch_directory = project_root / "experiments" / "launches"
    launch_directory.mkdir(parents=True, exist_ok=True)
    runner_stdout = launch_directory / f"{run_id}.stdout.log"
    runner_stderr = launch_directory / f"{run_id}.stderr.log"
    preflight_stdout = launch_directory / f"{run_id}.preflight.stdout.log"
    preflight_stderr = launch_directory / f"{run_id}.preflight.stderr.log"
    verifier_stdout = launch_directory / f"{run_id}.verifier.stdout.log"
    verifier_stderr = launch_directory / f"{run_id}.verifier.stderr.log"
    launcher_ledger = launch_directory / f"{run_id}.launcher.async-errors.jsonl"
    launch_record = launch_directory / f"{run_id}.launch.json"
    runner_process_record = launch_directory / f"{run_id}.runner-process.json"
    failure_path = launch_directory / f"{run_id}.external_failure.json"
    for path in (
        runner_stdout,
        runner_stderr,
        preflight_stdout,
        preflight_stderr,
        verifier_stdout,
        verifier_stderr,
        launcher_ledger,
        launch_record,
        runner_process_record,
        failure_path,
    ):
        if path.exists():
            raise FileExistsError(f"Append-only launch artifact collision: {path}")

    create_empty_file_exclusive(launcher_ledger)
    install_async_exception_hooks(launcher_ledger)
    fixed_environment = execution_environment()
    environment = os.environ.copy()
    environment.update(fixed_environment)
    source_hashes = {name: sha256_file(path) for name, path in paths.items()}
    source_hashes["python_executable"] = sha256_file(python_executable)
    hardware_record = machine_hardware_record()
    command = [
        str(python_executable),
        "-B",
        "-u",
        str(paths["runner"]),
        "--config",
        str(config_path),
        "--protocol",
        str(protocol_path),
        "--output-dir",
        str(run_directory),
        "--local-dataset-archive",
        str(local_archive),
    ]
    preflight_command = [
        str(python_executable),
        "-B",
        "-u",
        str(paths["runner"]),
        "--self-test",
        "--config",
        str(config_path),
    ]

    outer_lock.acquire()
    child_pid: int | None = None
    child_return_code: int | None = None
    child_process_metrics: Mapping[str, Any] | None = None
    verifier_child_pid: int | None = None
    verifier_return_code: int | None = None
    verifier_process_metrics: Mapping[str, Any] | None = None
    marker: Path | None = None
    result_path: Path | None = None
    verdict: bool | None = None
    try:
        outer_lock.assert_owned()
        one_time_claim = output_root / "CABLE_PREF_ONE_TIME_LAUNCH_CLAIM.json"
        launcher_preflight = synthetic_self_test()
        if (
            launcher_preflight.get("scientific_schema_bound") is not True
            or launcher_preflight.get("outcome_launch_authorized") is not True
            or not all(bool(value) for value in launcher_preflight.values())
        ):
            raise IntegrityError("Launcher synthetic preflight did not authorize outcome")
        (
            preflight_pid,
            preflight_return_code,
            preflight_process_metrics,
        ) = run_hidden_process(
            preflight_command,
            project_root,
            environment,
            preflight_stdout,
            preflight_stderr,
        )
        if (
            preflight_return_code != 0
            or preflight_pid <= 0
            or pid_is_running(preflight_pid)
            or preflight_stderr.stat().st_size != 0
        ):
            raise IntegrityError("Runner synthetic preflight process failed")
        try:
            preflight_report = json.loads(preflight_stdout.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IntegrityError("Runner synthetic preflight output is not one JSON value") from exc
        if (
            not isinstance(preflight_report, Mapping)
            or preflight_report.get("schema") != "cable-pref-runner-self-test-v1"
            or preflight_report.get("passed") is not True
            or preflight_report.get("archive_opened") is not False
            or preflight_report.get("archive_listed") is not False
            or preflight_report.get("target_outcomes_accessed") is not False
        ):
            raise IntegrityError("Runner synthetic preflight attestation differs")
        preflight_checks = require_mapping(
            preflight_report.get("checks"), "runner preflight checks"
        )
        if set(preflight_checks) != EXPECTED_RUNNER_SELF_TEST_CHECKS or not all(
            value is True for value in preflight_checks.values()
        ):
            raise IntegrityError("Runner preflight named-check inventory did not pass")
        if (
            tuple(preflight_report.get("raw_validation_fields", ()))
            != RAW_VALIDATION_FIELDS
            or tuple(preflight_report.get("raw_test_fields", ())) != RAW_TEST_FIELDS
            or tuple(preflight_report.get("raw_latency_fields", ()))
            != RAW_LATENCY_FIELDS
        ):
            raise IntegrityError("Runner preflight raw schema differs from verifier")
        publish_json_exclusive(
            one_time_claim,
            {
                "schema": "cable-pref-one-time-launch-claim-v1",
                "claimed_utc": utc_now(),
                "run_id": run_id,
                "run_directory": str(run_directory),
                "launcher_pid": os.getpid(),
                "source_sha256": source_hashes,
                "outer_lock": str(outer_lock.path),
                "automatic_retry_or_resume_forbidden": True,
            },
        )
        publish_json_exclusive(
            launch_record,
            {
                "schema": "cable-pref-external-launch-v1",
                "created_utc": utc_now(),
                "project_root": str(project_root),
                "launcher_pid": os.getpid(),
                "run_id": run_id,
                "run_directory": str(run_directory),
                "python_executable": str(python_executable),
                "command": command,
                "preflight_command": preflight_command,
                "launcher_synthetic_preflight": launcher_preflight,
                "runner_synthetic_preflight": preflight_report,
                "runner_preflight_process": preflight_process_metrics,
                "runner_preflight_stdout": str(preflight_stdout),
                "runner_preflight_stdout_sha256": sha256_file(preflight_stdout),
                "runner_preflight_stderr": str(preflight_stderr),
                "runner_preflight_stderr_zero_bytes": True,
                "runner_preflight_stderr_sha256": EMPTY_SHA256,
                "source_sha256": source_hashes,
                "execution_environment": fixed_environment,
                "execution_environment_sha256": environment_sha256(fixed_environment),
                "machine_hardware": hardware_record,
                "machine_hardware_sha256": sha256_bytes(
                    canonical_json_bytes(hardware_record)
                ),
                "local_dataset_archive": str(local_archive),
                "local_dataset_archive_sha256": expected_archive,
                "local_dataset_archive_size_bytes": expected_archive_size,
                "local_dataset_archive_md5": expected_archive_md5,
                "outer_lock": str(outer_lock.path),
                "outer_lock_token_sha256": sha256_text(outer_lock.token),
                "one_time_launch_claim": str(one_time_claim),
                "one_time_launch_claim_sha256": sha256_file(one_time_claim),
            },
        )
        child_pid, child_return_code, child_process_metrics = run_hidden_process(
            command,
            project_root,
            environment,
            runner_stdout,
            runner_stderr,
        )
        publish_json_exclusive(runner_process_record, child_process_metrics)
        if child_return_code != 0:
            raise IntegrityError(f"Outcome runner exited with code {child_return_code}")
        if child_pid <= 0 or pid_is_running(child_pid):
            raise IntegrityError("Outcome child remains active")
        if not run_directory.is_dir():
            raise IntegrityError("Runner did not create the authorized run directory")
        candidate_path = find_sole_runner_candidate(run_directory)
        candidate_preview = read_json_mapping(candidate_path, "runner candidate")
        execution_hash = str(
            candidate_preview.get("execution_fingerprint_sha256", "")
        ).lower()
        if not is_sha256(execution_hash):
            raise IntegrityError("Runner execution fingerprint is malformed")
        if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
            raise IntegrityError("External marker exists before verification")

        nonce = uuid.uuid4().hex[:12]
        verifier_ledger = run_directory / (
            f"verifier_async_errors_{execution_hash[:16]}_{nonce}.jsonl"
        )
        verifier_report = run_directory / (
            f"POST_EXIT_VERIFIER_{execution_hash[:16]}_{nonce}.json"
        )
        verifier_command = [
            str(python_executable),
            "-B",
            "-u",
            str(paths["launcher"]),
            "--verify-run-directory",
            str(run_directory),
            "--candidate",
            str(candidate_path),
            "--verification-report",
            str(verifier_report),
            "--verifier-ledger",
            str(verifier_ledger),
            "--runner-stderr",
            str(runner_stderr),
            "--runner-process-record",
            str(runner_process_record),
            "--launcher-child-pid",
            str(child_pid),
            "--outer-lock",
            str(outer_lock.path),
            "--outer-lock-owner-pid",
            str(os.getpid()),
            "--outer-lock-token",
            outer_lock.token,
            "--launch-record",
            str(launch_record),
            "--expected-launcher-sha256",
            source_hashes["launcher"],
        ]
        (
            verifier_child_pid,
            verifier_return_code,
            verifier_process_metrics,
        ) = run_hidden_process(
            verifier_command,
            project_root,
            environment,
            verifier_stdout,
            verifier_stderr,
        )
        if verifier_return_code != 0:
            raise IntegrityError(
                f"Post-exit verifier exited with code {verifier_return_code}"
            )
        if verifier_child_pid <= 0 or pid_is_running(verifier_child_pid):
            raise IntegrityError("Verifier child remains active")
        if not verifier_report.is_file():
            raise IntegrityError("Verifier did not publish a report")
        report = read_json_mapping(verifier_report, "post-exit verifier report")
        if report.get("schema") != "cable-pref-post-exit-verification-v1":
            raise IntegrityError("Verifier report schema changed")
        verifier_pid = int(report.get("verifier_pid", -1))
        if verifier_pid <= 0 or pid_is_running(verifier_pid):
            raise IntegrityError("Verifier PID is active or invalid")
        if report.get("external_marker_publication_authorized") is not True:
            raise IntegrityError("Verifier did not authorize marker publication")
        verifier_lock_path = Path(str(report.get("verifier_lock", ""))).resolve()
        if verifier_lock_path.exists():
            raise IntegrityError("Verifier lock remains after verifier process exit")
        for path, label in (
            (runner_stderr, "runner stderr"),
            (verifier_stderr, "verifier stderr"),
            (verifier_ledger, "verifier asynchronous-error ledger"),
            (launcher_ledger, "launcher asynchronous-error ledger"),
        ):
            if path.stat().st_size != 0:
                raise IntegrityError(f"{label} is nonempty")
        for name, path in paths.items():
            if sha256_file(path) != source_hashes[name]:
                raise IntegrityError(f"Bound source changed during run: {name}")
        outer_lock.assert_owned()

        candidate = read_json_mapping(candidate_path, "runner candidate after replay")
        result_path = contained_file(
            run_directory, str(candidate.get("result_file", "")), "result file"
        )
        verdict = require_bool(report.get("promise_gate_passed"), "verifier verdict")
        marker = run_directory / f"{EXTERNAL_MARKER_PREFIX}{execution_hash[:16]}.json"
        publish_json_exclusive(
            marker,
            {
                "schema": "cable-pref-external-complete-v1",
                "verified_utc": utc_now(),
                "termination_stage": report["termination_stage"],
                "test_opened": report["test_opened"],
                "launcher_pid": os.getpid(),
                "launcher_child_pid": child_pid,
                "launcher_child_exit_code": child_return_code,
                "runner_process_has_exited": True,
                "runner_process_record": str(runner_process_record),
                "runner_process_record_sha256": sha256_file(runner_process_record),
                "runner_process_metrics": child_process_metrics,
                "verifier_child_pid": verifier_child_pid,
                "verifier_child_exit_code": verifier_return_code,
                "verifier_process_metrics": verifier_process_metrics,
                "verifier_pid": verifier_pid,
                "verifier_process_has_exited": True,
                "runner_lock": report["runner_lock"],
                "runner_lock_released": True,
                "verifier_lock": str(verifier_lock_path),
                "verifier_lock_released": True,
                "outer_lock": str(outer_lock.path),
                "outer_lock_held_through_marker_publication": True,
                "outer_lock_release_pending_on_launcher_return": True,
                "source_sha256": source_hashes,
                "launch_record": str(launch_record),
                "launch_record_sha256": sha256_file(launch_record),
                "candidate_marker": candidate_path.name,
                "candidate_marker_sha256": sha256_file(candidate_path),
                "post_exit_verifier_report": verifier_report.name,
                "post_exit_verifier_report_sha256": sha256_file(verifier_report),
                "runner_stdout": str(runner_stdout),
                "runner_stdout_sha256": sha256_file(runner_stdout),
                "runner_preflight_stdout": str(preflight_stdout),
                "runner_preflight_stdout_sha256": sha256_file(preflight_stdout),
                "runner_preflight_stderr": str(preflight_stderr),
                "runner_preflight_stderr_zero_bytes": True,
                "runner_preflight_stderr_sha256": EMPTY_SHA256,
                "runner_stderr": str(runner_stderr),
                "runner_stderr_zero_bytes": True,
                "runner_stderr_sha256": EMPTY_SHA256,
                "verifier_stdout": str(verifier_stdout),
                "verifier_stdout_sha256": sha256_file(verifier_stdout),
                "verifier_stderr": str(verifier_stderr),
                "verifier_stderr_zero_bytes": True,
                "verifier_stderr_sha256": EMPTY_SHA256,
                "runner_asynchronous_error_ledger_empty": True,
                "verifier_asynchronous_error_ledger_empty": True,
                "launcher_asynchronous_error_ledger_empty": True,
                "result_file": result_path.name,
                "result_sha256": sha256_file(result_path),
                "execution_environment_sha256": environment_sha256(fixed_environment),
                "execution_fingerprint_sha256": execution_hash,
                "gates": report["gates"],
                "scientific_replay": report["scientific_replay"],
                "promise_gate_passed": verdict,
            },
        )
        if len(list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json"))) != 1:
            raise IntegrityError("External marker publication was not singular")
    except BaseException as exc:
        if not failure_path.exists():
            publish_json_exclusive(
                failure_path,
                {
                    "schema": "cable-pref-external-verification-failure-v1",
                    "utc": utc_now(),
                    "exception_type": type(exc).__name__,
                    "exception": str(exc),
                    "traceback": "".join(
                        traceback.format_exception(type(exc), exc, exc.__traceback__)
                    ),
                    "launcher_pid": os.getpid(),
                    "launcher_child_pid": child_pid,
                    "launcher_child_exit_code": child_return_code,
                    "verifier_child_pid": verifier_child_pid,
                    "verifier_child_exit_code": verifier_return_code,
                    "run_directory": str(run_directory),
                    "outer_lock": str(outer_lock.path),
                    "outer_lock_held_at_failure": outer_lock.acquired,
                },
            )
        raise
    finally:
        outer_lock.release()

    if outer_lock.path.exists():
        raise IntegrityError("Outer launch lock remains")
    if marker is None or result_path is None or verdict is None:
        raise IntegrityError("Launch reached an incomplete terminal state")
    print(f"EXTERNAL_COMPLETION_MARKER={marker}", flush=True)
    print(f"RESULT_FILE={result_path}", flush=True)
    print(f"PROMISE_GATE_PASSED={str(verdict).lower()}", flush=True)
    print("OUTER_LOCK_RELEASED=true", flush=True)
    return 0


def synthetic_self_test() -> Mapping[str, Any]:
    project_root = Path(__file__).resolve().parents[1]
    frozen_paths = locked_paths(project_root)
    verify_frozen_source_files(frozen_paths)
    if _pair_outcome((10, 20, 30), 20, 30) != 1.0:
        raise IntegrityError("Synthetic positive sPCE case failed")
    if _pair_outcome((10, 20, 30), 40, 30) != 0.0:
        raise IntegrityError("Synthetic hidden-chosen sPCE case failed")
    if _pair_outcome((10, 20, 30), 40, 50) != 0.0:
        raise IntegrityError("Synthetic both-hidden sPCE case failed")

    import numpy as np

    values = np.asarray([0.1, 0.2, -0.1, 0.0], dtype=np.float64)
    first = _paired_bootstrap(values, draws=100, alpha=0.05, seed=17)
    second = _paired_bootstrap(values, draws=100, alpha=0.05, seed=17)
    if first != second or not math.isclose(first["point"], 0.05, abs_tol=1e-15):
        raise IntegrityError("Synthetic bootstrap is not deterministic")
    finite_intersection = _paired_bootstrap(
        np.asarray([0.2, np.nan, 0.2]), draws=20, alpha=0.05, seed=17
    )
    if finite_intersection["users"] != 2 or finite_intersection["point"] != 0.2:
        raise IntegrityError("Synthetic bootstrap finite-intersection rule failed")
    power_first = _centered_power_detection(
        values, delta=0.02, seed=23, experiments=5, inner_draws=20
    )
    power_second = _centered_power_detection(
        values, delta=0.02, seed=23, experiments=5, inner_draws=20
    )
    if power_first != power_second:
        raise IntegrityError("Synthetic centered power replay is not deterministic")
    movie_ids = np.arange(1, 702, dtype=np.int64)
    full_scores = np.linspace(1.0, 0.0, movie_ids.size, dtype=np.float32)
    eligible = np.ones(movie_ids.size, dtype=np.bool_)
    eligible[:501] = False
    selected = np.arange(501, 701, dtype=np.int64)
    _verify_exact_topk(
        scores=full_scores,
        eligible=eligible,
        selected=selected,
        movie_ids=movie_ids,
        k=200,
        label="synthetic seen-prefix top-k",
    )
    tie_scores = np.zeros(250, dtype=np.float32)
    tie_ids = np.arange(1, 251, dtype=np.int64)
    _verify_exact_topk(
        scores=tie_scores,
        eligible=np.ones(250, dtype=np.bool_),
        selected=np.arange(200, dtype=np.int64),
        movie_ids=tie_ids,
        k=200,
        label="synthetic stable tie top-k",
    )

    synthetic_metrics = np.zeros((3, 8, 8, 8), dtype=np.float64)
    metric_index = {name: index for index, name in enumerate(EXPECTED_METRICS)}
    synthetic_metrics[:, 4, :, metric_index["conditional_admission_at_200"]] = 0.20
    synthetic_metrics[:, 4, :, metric_index["net_new_preferred_support"]] = 0.10
    synthetic_metrics[:, 4, :, metric_index["net_admission_advantage"]] = 0.10
    synthetic_metrics[:, 4, :, metric_index["spce_at_10"]] = 0.20
    synthetic_metrics[:, 4, :, metric_index["preferred_exposure_at_10"]] = 0.10
    synthetic_metrics[:, :, :, metric_index["ndcg_at_10"]] = 0.50
    synthetic_metrics[:, :, :, metric_index["recall_at_10"]] = 0.50
    synthetic_metrics[:, :, :, metric_index["low_rating_intrusion_at_10"]] = 0.0
    synthetic_diagnostic = {
        "fixed_pairs": 6000,
        "pair_users": 1200,
        "unique_bpr_missed_preferred_endpoints": 6000,
        "missed_endpoint_users": 1200,
        "admission_changed_count": 100,
        "admission_total": 1000,
        "spce_changed_count": 50,
        "spce_total": 1000,
    }
    synthetic_gates, synthetic_details = _compute_test_gates_replay(
        test_metrics=synthetic_metrics,
        test_diagnostics=[dict(synthetic_diagnostic) for _seed in EXPECTED_SEEDS],
        R_diagnostics={"selected_pairs": 20_000, "selected_pair_users": 1000},
        power={"passed": True},
        latency={"passed": True},
        stronger_relevance_method="raw_hybrid",
        g1_invariants={"synthetic": True},
        g9_passed=True,
    )
    if not all(synthetic_gates.values()):
        raise IntegrityError(f"Synthetic passing G1-G9 replay failed: {synthetic_gates}")
    if (
        synthetic_details.get("required_metric_support_complete") is not True
        or any(
            record.get("support_failed") is not False
            for record in require_mapping(
                synthetic_details.get("bootstrap"), "synthetic bootstrap details"
            ).values()
        )
    ):
        raise IntegrityError("Synthetic supported-metric replay lacks support flags")
    failed_gates, _details = _compute_test_gates_replay(
        test_metrics=synthetic_metrics,
        test_diagnostics=[dict(synthetic_diagnostic) for _seed in EXPECTED_SEEDS],
        R_diagnostics={"selected_pairs": 20_000, "selected_pair_users": 1000},
        power={"passed": True},
        latency={"passed": False},
        stronger_relevance_method="raw_hybrid",
        g1_invariants={"synthetic": True},
        g9_passed=True,
    )
    if failed_gates["G8"] is not False or any(
        failed_gates[name] is not True for name in GATE_NAMES if name != "G8"
    ):
        raise IntegrityError("Synthetic single-gate failure isolation failed")
    unsupported_gates, unsupported_details = _compute_test_gates_replay(
        test_metrics=np.full_like(synthetic_metrics, np.nan),
        test_diagnostics=[dict(synthetic_diagnostic) for _seed in EXPECTED_SEEDS],
        R_diagnostics={"selected_pairs": 20_000, "selected_pair_users": 1000},
        power={"passed": True},
        latency={"passed": True},
        stronger_relevance_method="raw_hybrid",
        g1_invariants={"synthetic": True},
        g9_passed=True,
    )
    expected_sentinel = {
        "point": 0.0,
        "lower": -1.0,
        "upper": 1.0,
        "users": 0,
        "support_failed": True,
    }
    unsupported_bootstrap = require_mapping(
        unsupported_details.get("bootstrap"), "unsupported bootstrap details"
    )
    if (
        unsupported_details.get("required_metric_support_complete") is not False
        or unsupported_gates["G5"] is not False
        or unsupported_gates["G7"] is not False
        or not unsupported_bootstrap
        or any(record != expected_sentinel for record in unsupported_bootstrap.values())
    ):
        raise IntegrityError("Missing metric support did not fail gates conservatively")
    try:
        json.dumps(unsupported_details, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise IntegrityError("Unsupported-metric replay emitted nonfinite details") from exc
    with tempfile.TemporaryDirectory(prefix="cable-verifier-selftest-") as temp:
        root = Path(temp)
        target = root / "atomic.json"
        publish_json_exclusive(target, {"value": 1})
        try:
            publish_json_exclusive(target, {"value": 2})
        except FileExistsError:
            pass
        else:
            raise IntegrityError("Exclusive publication overwrote an artifact")
        if read_json_mapping(target, "synthetic atomic artifact")["value"] != 1:
            raise IntegrityError("Exclusive artifact changed after collision")
        lock = ExclusiveOwnerLock(root / "owner.lock", "synthetic")
        lock.acquire()
        lock.assert_owned()
        lock.release()
        if lock.path.exists():
            raise IntegrityError("Synthetic owner lock was not released")
        marker = root / f"{EXTERNAL_MARKER_PREFIX}synthetic.json"
        publish_json_exclusive(
            marker,
            {
                "schema": "cable-pref-external-complete-v1",
                "promise_gate_passed": True,
            },
        )
        if len(list(root.glob(f"{EXTERNAL_MARKER_PREFIX}*.json"))) != 1:
            raise IntegrityError("Synthetic external marker is not singular")
    config_path = frozen_paths["config"]
    if config_path.is_file():
        verify_config_contract(read_json_mapping(config_path, "synthetic config check"))
    return {
        "atomic_no_overwrite": True,
        "all_gates_replayed": True,
        "config_contract": config_path.is_file(),
        "centered_power": True,
        "exclusive_lock": True,
        "external_marker_schema": True,
        "empty_metric_support_fails_closed": True,
        "finite_common_user_bootstrap": True,
        "frozen_source_files": True,
        "paired_bootstrap": True,
        "raw_R_V_T_schema_bound": (
            "R_event_items" in RAW_VALIDATION_FIELDS
            and "V_event_items" in RAW_VALIDATION_FIELDS
            and "T_event_items" in RAW_TEST_FIELDS
        ),
        "strict_spce": True,
        "stable_exact_topk": True,
        "scientific_schema_bound": True,
        "outcome_launch_authorized": True,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "cable_pref_poc_ml10m_v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=project_root / "experiments" / "cable-pref-protocol-v1.md",
    )
    parser.add_argument(
        "--output-root", type=Path, default=project_root / "experiments" / "runs"
    )
    parser.add_argument("--local-dataset-archive", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--self-test", action="store_true")

    # Internal post-exit verifier mode. These arguments are issued only by the
    # outer launch mode and are deliberately explicit/source-bound.
    parser.add_argument("--verify-run-directory", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--verification-report", type=Path)
    parser.add_argument("--verifier-ledger", type=Path)
    parser.add_argument("--runner-stderr", type=Path)
    parser.add_argument("--runner-process-record", type=Path)
    parser.add_argument("--launcher-child-pid", type=int)
    parser.add_argument("--outer-lock", type=Path)
    parser.add_argument("--outer-lock-owner-pid", type=int)
    parser.add_argument("--outer-lock-token")
    parser.add_argument("--launch-record", type=Path)
    parser.add_argument("--expected-launcher-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    for name, value in execution_environment().items():
        os.environ[name] = value
    args = parse_args(argv)
    if args.self_test:
        print(json.dumps(synthetic_self_test(), sort_keys=True), flush=True)
        return 0
    if args.verify_run_directory is not None:
        required = (
            "candidate",
            "verification_report",
            "verifier_ledger",
            "runner_stderr",
            "runner_process_record",
            "launcher_child_pid",
            "outer_lock",
            "outer_lock_owner_pid",
            "outer_lock_token",
            "launch_record",
            "expected_launcher_sha256",
        )
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise IntegrityError(f"Verifier arguments missing: {missing}")
        return run_verifier(args)
    return run_launch(args)


if __name__ == "__main__":
    raise SystemExit(main())
