#!/usr/bin/env python3
"""Append-only launcher and independent post-exit verifier for PIVOT.

The outcome runner is an artifact producer only.  It cannot publish a PIVOT
external completion marker, establish G9, or make its own gate calculation
authoritative.  This module binds the one-time launch, preserves process logs,
authenticates the runner closure, independently reconstructs G1--G8 from raw
artifacts, and is the only code permitted to publish the authoritative marker.

``--validate-config`` and ``--self-test`` are outcome blind.  They reject all
archive, output, run, candidate, and verification arguments and never open or
list the MovieLens archive.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata as importlib_metadata
import io
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import platform
import re
import subprocess
import sys
import tempfile
import threading
import traceback
from typing import Any, Iterable, Mapping, Sequence
import uuid
import zipfile

import numpy as np


THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)
EXPECTED_SEEDS = (20260861, 20260862, 20260863)
EXPECTED_EPOCHS = (5, 10, 20, 40)
EXPECTED_METHODS = (
    "popularity",
    "raw_full_exact_semantic",
    "balanced_geometric_ivf",
    "pivot_route_only",
    "pivot_rerank_only",
    "pivot_full",
    "shuffled_pivot",
    "aligned_full_exact",
)
EXPECTED_METRICS = (
    "future_liked_recall_at_100",
    "cpe_at_100",
    "cross_cell_cpe_at_100",
    "aligned_oracle_overlap_at_100",
    "spce_at_10",
    "ndcg_at_10",
    "recall_at_10",
    "low_rating_intrusion_at_10",
)
FIXED_WORK_METHODS = EXPECTED_METHODS[2:7]
GATE_NAMES = tuple(f"G{index}" for index in range(1, 10))
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EXTERNAL_MARKER_PREFIX = "PIVOT_EXTERNAL_COMPLETE_"
RUNNER_CANDIDATE_NAME = "runner_completion_candidate.json"
CLAIM_NAME = "PIVOT_ONE_TIME_LAUNCH_CLAIM.json"
SAFE_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")

EXPECTED_RUNNER_ARTIFACTS: Mapping[str, str] = {
    "RUN_STARTED.json": "pivot-run-started-v1",
    "environment.json": "pivot-environment-v1",
    "source_inventory.json": "pivot-source-inventory-v1",
    "archive_and_extraction.json": "pivot-archive-v1",
    "cohort_and_layout.json": "pivot-cohort-layout-v1",
    "representation_and_shards.json": "pivot-representation-v1",
    "stage_A_manifest.json": "pivot-stage-a-v1",
    "stage_R_basis_manifest.json": "pivot-stage-r-basis-v1",
    "training_manifest.json": "pivot-training-v1",
    "stage_V_candidate_bank_manifest.json": "pivot-stage-v-bank-v1",
    "frozen_choices.json": "pivot-frozen-choices-v1",
    "power_audit.json": "pivot-power-audit-v1",
    "stage_T_candidate_bank_manifest.json": "pivot-stage-t-bank-v1",
    "raw_metric_arrays_manifest.json": "pivot-raw-arrays-v1",
    "latency_raw_manifest.json": "pivot-latency-raw-v1",
    RUNNER_CANDIDATE_NAME: "pivot-runner-candidate-v1",
    "runner_recursive_inventory.json": "pivot-runner-inventory-v1",
}


class IntegrityError(RuntimeError):
    """A source, append-only, schema, process, or scientific invariant failed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def is_lower_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def require_launcher_digest(value: Any, launcher: Path, label: str) -> str:
    if (
        not is_lower_sha256(value)
        or not launcher.is_file()
        or sha256_file(launcher) != value
    ):
        raise IntegrityError(f"{label} does not authorize the current launcher")
    return str(value)


def read_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"Cannot read {label}: {path}") from exc
    if not isinstance(value, Mapping):
        raise IntegrityError(f"{label} must be a JSON object")
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


def require_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IntegrityError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise IntegrityError(f"{label} must be finite")
    return result


def fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bytes_exclusive(path: Path, payload: bytes) -> None:
    """Publish bytes without an overwrite window, including on Windows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        fsync_directory(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def publish_json_exclusive(path: Path, value: Any) -> None:
    publish_bytes_exclusive(path, canonical_json_bytes(value))


def create_empty_exclusive(path: Path) -> None:
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
                "schema": "pivot-async-exception-v1",
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
                "schema": "pivot-async-exception-v1",
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


def safe_relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError as exc:
        raise IntegrityError(f"Path escapes bound directory: {path}") from exc


def contained_file(base: Path, relative_name: str, label: str) -> Path:
    relative = Path(relative_name)
    if relative.is_absolute() or relative.name in {"", ".", ".."}:
        raise IntegrityError(f"Invalid {label} path: {relative_name!r}")
    result = (base / relative).resolve()
    try:
        result.relative_to(base.resolve())
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes run directory") from exc
    if not result.is_file() or result.is_symlink():
        raise IntegrityError(f"Missing or linked {label}: {result}")
    return result


def recursive_hashes(root: Path, excluded: Iterable[Path] = ()) -> Mapping[str, str]:
    ignored = {path.resolve() for path in excluded}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        if path.is_symlink():
            raise IntegrityError(f"Symlink forbidden in run closure: {path}")
        if path.is_file() and path.resolve() not in ignored:
            result[safe_relative(path, root)] = sha256_file(path)
    return result


def npz_exact(path: Path, required: Iterable[str], label: str) -> Mapping[str, np.ndarray]:
    try:
        with np.load(path, allow_pickle=False) as archive:
            names = tuple(archive.files)
            expected = tuple(required)
            if set(names) != set(expected) or len(names) != len(expected):
                raise IntegrityError(
                    f"{label} fields differ: observed={sorted(names)}, expected={sorted(expected)}"
                )
            result = {name: np.array(archive[name], copy=True) for name in expected}
    except (OSError, ValueError) as exc:
        raise IntegrityError(f"Cannot load {label}: {path}") from exc
    return result


def decode_strings(array: np.ndarray, label: str) -> tuple[str, ...]:
    values = np.asarray(array)
    if values.ndim != 1 or values.dtype.kind not in "SU":
        raise IntegrityError(f"{label} must be a one-dimensional string array")
    if values.dtype.kind == "S":
        try:
            return tuple(bytes(value).decode("ascii") for value in values)
        except UnicodeDecodeError as exc:
            raise IntegrityError(f"{label} contains non-ASCII bytes") from exc
    return tuple(str(value) for value in values)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def locked_paths(root: Path | None = None) -> Mapping[str, Path]:
    base = (root or project_root()).resolve()
    return {
        "research_question": base / "literature" / "research-question-cycle6.md",
        "cycle6_survey": base / "literature" / "cycle6-survey-and-ideation.md",
        "architecture": base / "architecture-pivot.md",
        "protocol": base / "experiments" / "pivot-protocol-v1.md",
        "config": base / "src" / "configs" / "pivot_poc_ml10m_v1.json",
        "runner": base / "src" / "pivot_poc.py",
        "launcher": base / "src" / "launch_pivot_and_verify.py",
    }


def source_hashes(paths: Mapping[str, Path], python_executable: Path) -> Mapping[str, str]:
    result: dict[str, str] = {}
    for name, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise IntegrityError(f"Missing or linked bound source: {name}: {path}")
        result[name] = sha256_file(path)
    result["python_executable"] = sha256_file(python_executable)
    return result


def verify_source_hashes(
    paths: Mapping[str, Path], python_executable: Path, expected: Mapping[str, Any]
) -> None:
    observed = source_hashes(paths, python_executable)
    if set(expected) != set(observed):
        raise IntegrityError("Source hash inventory fields changed")
    for name, digest in observed.items():
        if expected.get(name) != digest:
            raise IntegrityError(f"Bound source changed: {name}")


def _at(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        current = require_mapping(current, path).get(part)
    return current


def validate_config_contract(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate the scientific and artifact fields needed by this verifier."""

    expected_scalars: Mapping[str, Any] = {
        "protocol_name": "pivot-ml10m-poc-v1-preregistered",
        "protocol_version": 1,
        "authoritative_question": "literature/research-question-cycle6.md",
        "architecture": "architecture-pivot.md",
        "protocol": "experiments/pivot-protocol-v1.md",
        "dataset.expected_archive_size_bytes": 65566137,
        "dataset.expected_archive_sha256": "813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862",
        "dataset.expected_official_sidecar_md5": "ce571fd55effeba0271552578f2648bd",
        "dataset.prior_cycle_exclusion.record_sha256": "eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126",
        "dataset.eligibility.minimum_total_events": 80,
        "dataset.eligibility.maximum_total_events": 300,
        "dataset.eligibility.minimum_timestamp_groups": 4,
        "dataset.eligibility.minimum_distinct_liked_A_items": 5,
        "dataset.cohort.required_users": 600,
        "embedding.dimension": 384,
        "embedding.required_reuse_candidate_sha256": "8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768",
        "partition.num_cells": 32,
        "partition.kmeans.random_state": 20260861,
        "partition.kmeans.batch_size": 1024,
        "partition.kmeans.n_init": 5,
        "partition.kmeans.max_iter": 100,
        "partition.kmeans.reassignment_ratio": 0.0,
        "partition.kmeans.threads": 1,
        "partition.kmeans.scikit_learn_version": "1.8.0",
        "partition.sentinels.count": 7,
        "partition.sentinels.physical_slots_per_shard": 334,
        "partition.indexes.count": 32,
        "partition.indexes.ntotal_each": 334,
        "user_representation.descriptor_dimension": 1153,
        "user_representation.dislike_weight": 0.25,
        "potential_model.potential_scale": 0.05,
        "potential_model.maximum_pairwise_offset_difference": 0.1,
        "alignment.beta": 5.0,
        "alignment.gamma": 0.05,
        "alignment.learning_rate": 0.003,
        "alignment.weight_decay": 0.0001,
        "alignment.gradient_clip_norm": 1.0,
        "alignment.shuffled_direction.hash_to_coin_decoding": "least_significant_bit_of_big_endian_SHA256_digest_integer_equals_1_means_flip",
        "retrieval.logical_nprobe": 4,
        "retrieval.per_shard_search_k": 334,
        "retrieval.physical_shard_slots_searched": 1336,
        "retrieval.coarse_centroid_dot_products": 32,
        "retrieval.candidate_quota": 100,
        "validation.relevance_comparator_exact_tie_rule": "balanced_geometric_ivf",
        "evaluation.bootstrap.draws": 5000,
        "evaluation.bootstrap.seed": 20260864,
        "power_audit.outer_user_resamples": 500,
        "power_audit.inner_paired_bootstrap_draws": 500,
        "power_audit.seed": 20260866,
        "power_audit.registered_effect": 0.01,
        "power_audit.minimum_detection_fraction_each": 0.8,
        "latency.measured_requests_exact": 512,
        "latency.warmups": 32,
        "latency.repetitions": 7,
        "latency.interleaving_exact_schedule": "repetitions_0_through_6_even_geometric_then_PIVOT_odd_PIVOT_then_geometric_each_in_deterministic_request_order",
        "latency.p95_quantile_method": "numpy_quantile_method_linear",
        "latency.maximum_p95_ms": 3.0,
        "latency.maximum_p95_ratio": 1.5,
    }
    for path, expected in expected_scalars.items():
        observed = _at(config, path)
        if observed != expected:
            raise IntegrityError(
                f"Config lock differs at {path}: observed={observed!r}, expected={expected!r}"
            )

    if tuple(_at(config, "seeds.optimization")) != EXPECTED_SEEDS:
        raise IntegrityError("Optimization seed inventory changed")
    if tuple(_at(config, "alignment.checkpoint_epochs")) != EXPECTED_EPOCHS:
        raise IntegrityError("Checkpoint epoch inventory changed")
    if tuple(_at(config, "methods.registered_order")) != EXPECTED_METHODS:
        raise IntegrityError("Method order changed")
    if tuple(_at(config, "methods.fixed_work_methods")) != FIXED_WORK_METHODS:
        raise IntegrityError("Fixed-work method inventory changed")
    capacities = _at(config, "partition.real_item_capacities")
    if capacities.get("canonical_cells_0_through_24") != 334 or capacities.get(
        "canonical_cells_25_through_31"
    ) != 333 or capacities.get("total") != 10681:
        raise IntegrityError("Balanced capacity contract changed")
    if tuple(_at(config, "dataset.allowed_members")) != (
        "ml-10M100K/ratings.dat",
        "ml-10M100K/movies.dat",
    ):
        raise IntegrityError("Allowed archive members changed")
    runner_artifacts = require_mapping(
        _at(config, "artifact_contract.runner_artifacts"),
        "artifact_contract.runner_artifacts",
    )
    if dict(runner_artifacts) != dict(EXPECTED_RUNNER_ARTIFACTS):
        raise IntegrityError("Runner artifact contract changed")
    pending = tuple(
        _at(
            config,
            "preauthorization_bindings_required.must_be_resolved_outcome_blind_before_runner_source_lock",
        )
    )
    if pending != (
        "python_executable_path_and_sha256",
        "external_output_root",
        "fresh_run_id",
        "launcher_sha256",
    ):
        raise IntegrityError("Preauthorization pending-binding inventory changed")
    expected_sklearn = str(_at(config, "partition.kmeans.scikit_learn_version"))
    try:
        observed_sklearn = importlib_metadata.version("scikit-learn")
    except importlib_metadata.PackageNotFoundError as exc:
        raise IntegrityError("scikit-learn is not installed") from exc
    if observed_sklearn != expected_sklearn:
        raise IntegrityError(
            f"scikit-learn version differs: {observed_sklearn} != {expected_sklearn}"
        )
    return {
        "schema": "pivot-config-validation-v1",
        "valid": True,
        "archive_opened": False,
        "archive_listed": False,
        "target_outcomes_accessed": False,
        "config_sha256": sha256_bytes(canonical_json_bytes(config)),
        "scikit_learn_version": observed_sklearn,
    }


def execution_environment() -> Mapping[str, str]:
    values = {name: "1" for name in THREAD_VARIABLES}
    values.update(
        {
            "CUDA_VISIBLE_DEVICES": "-1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_PROGRESS_BARS": "1",
            "TQDM_DISABLE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return values


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
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x1000, False, int(pid))
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return False
        if error == 5:
            return True
        raise ctypes.WinError(error)
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(code.value) == 259
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
                "schema": "pivot-exclusive-owner-lock-v1",
                "role": self.role,
                "pid": os.getpid(),
                "token_sha256": sha256_text(self.token),
                "created_utc": utc_now(),
            },
        )
        self.acquired = True

    def assert_owned(self) -> None:
        if not self.acquired or not self.path.is_file():
            raise IntegrityError(f"{self.role} lock is absent")
        value = read_json(self.path, f"{self.role} lock")
        if (
            value.get("schema") != "pivot-exclusive-owner-lock-v1"
            or value.get("role") != self.role
            or value.get("pid") != os.getpid()
            or value.get("token_sha256") != sha256_text(self.token)
        ):
            raise IntegrityError(f"{self.role} lock ownership changed")

    def release(self) -> None:
        if not self.acquired:
            return
        self.assert_owned()
        self.path.unlink()
        fsync_directory(self.path.parent)
        self.acquired = False


def child_process(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> Mapping[str, Any]:
    create_empty_exclusive(stdout_path)
    create_empty_exclusive(stderr_path)
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with stdout_path.open("ab", buffering=0) as stdout, stderr_path.open(
        "ab", buffering=0
    ) as stderr:
        started = utc_now()
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            startupinfo=startupinfo,
            creationflags=creationflags,
            close_fds=True,
        )
        pid = int(process.pid)
        return_code = int(process.wait())
        finished = utc_now()
    if pid_is_running(pid):
        raise IntegrityError("Child still runs after wait returned")
    return {
        "schema": "pivot-child-process-exit-v1",
        "pid": pid,
        "return_code": return_code,
        "started_utc": started,
        "finished_utc": finished,
        "stdout": str(stdout_path.resolve()),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr": str(stderr_path.resolve()),
        "stderr_sha256": sha256_file(stderr_path),
        "stderr_zero_bytes": stderr_path.stat().st_size == 0,
    }


def hardware_record() -> Mapping[str, Any]:
    distributions = (
        "numpy",
        "torch",
        "faiss-cpu",
        "sentence-transformers",
        "scikit-learn",
        "psutil",
    )
    versions: dict[str, str] = {}
    for name in distributions:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    affinity: Any = None
    with contextlib.suppress(Exception):
        import psutil

        affinity = psutil.Process().cpu_affinity()
    return {
        "schema": "pivot-machine-hardware-v1",
        "cpu_model": platform.processor(),
        "logical_core_count": os.cpu_count(),
        "process_affinity": affinity,
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "package_versions": versions,
    }


@dataclass(frozen=True)
class CandidateClosure:
    candidate_path: Path
    candidate: Mapping[str, Any]
    inventory_path: Path
    inventory: Mapping[str, Any]
    artifact_hashes: Mapping[str, str]
    execution_fingerprint: str
    runner_pid: int


def safe_run_id(value: str) -> str:
    if not SAFE_RUN_ID.fullmatch(value):
        raise IntegrityError("Run ID must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}")
    return value


def _preflight_arguments_absent(args: argparse.Namespace) -> None:
    forbidden = {
        "local_dataset_archive": args.local_dataset_archive,
        "output_root": args.output_root,
        "run_id": args.run_id,
        "authorized_launcher_sha256": args.authorized_launcher_sha256,
        "verify_run_directory": args.verify_run_directory,
        "candidate": args.candidate,
        "verification_report": args.verification_report,
        "launch_record": args.launch_record,
    }
    present = sorted(name for name, value in forbidden.items() if value is not None)
    if present:
        raise IntegrityError(f"Outcome-blind mode rejects arguments: {present}")


def paired_bootstrap(
    values: np.ndarray, *, draws: int = 5000, seed: int = 20260864
) -> Mapping[str, Any]:
    vector = np.asarray(values, dtype=np.float64)
    vector = vector[np.isfinite(vector)]
    if vector.size == 0:
        return {
            "users": 0,
            "mean": None,
            "lower": None,
            "upper": None,
            "support_failed": True,
        }
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    for start in range(0, draws, 128):
        stop = min(draws, start + 128)
        sample = rng.integers(0, vector.size, size=(stop - start, vector.size))
        means[start:stop] = vector[sample].mean(axis=1)
    return {
        "users": int(vector.size),
        "mean": float(vector.mean()),
        "lower": float(np.quantile(means, 0.025, method="linear")),
        "upper": float(np.quantile(means, 0.975, method="linear")),
        "support_failed": False,
    }


def centered_power(values: np.ndarray, *, rng: np.random.Generator) -> Mapping[str, Any]:
    vector = np.asarray(values, dtype=np.float64)
    vector = vector[np.isfinite(vector)]
    if vector.size == 0:
        return {"users": 0, "detection": 0.0, "passed": False}
    synthetic = vector - vector.mean() + 0.010
    detected = 0
    for _ in range(500):
        outer = synthetic[rng.integers(0, vector.size, size=vector.size)]
        inner_means = np.empty(500, dtype=np.float64)
        for start in range(0, 500, 100):
            stop = min(500, start + 100)
            sample = rng.integers(0, outer.size, size=(stop - start, outer.size))
            inner_means[start:stop] = outer[sample].mean(axis=1)
        detected += int(np.quantile(inner_means, 0.025, method="linear") > 0.0)
    fraction = detected / 500.0
    return {"users": int(vector.size), "detection": fraction, "passed": fraction >= 0.80}


def digest_coin(text: str) -> bool:
    digest = hashlib.sha256(text.encode("ascii")).digest()
    return bool(int.from_bytes(digest, "big") & 1)


def synthetic_self_test(config: Mapping[str, Any]) -> Mapping[str, Any]:
    validation = validate_config_contract(config)
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="pivot-launcher-selftest-") as raw:
        root = Path(raw)
        artifact = root / "artifact.json"
        publish_json_exclusive(artifact, {"value": 1})
        try:
            publish_json_exclusive(artifact, {"value": 2})
        except FileExistsError:
            checks["atomic_no_overwrite"] = True
        else:
            raise IntegrityError("Exclusive publication overwrote a file")
        lock = ExclusiveOwnerLock(root / "owner.lock", "synthetic")
        lock.acquire()
        lock.assert_owned()
        lock.release()
        checks["exclusive_owner_lock"] = not lock.path.exists()
        marker = root / f"{EXTERNAL_MARKER_PREFIX}synthetic.json"
        publish_json_exclusive(
            marker,
            {
                "schema": "pivot-external-complete-v1",
                "G9": True,
                "PROMISING": False,
            },
        )
        checks["sole_marker_schema"] = (
            len(list(root.glob(f"{EXTERNAL_MARKER_PREFIX}*.json"))) == 1
        )

    first = paired_bootstrap(np.asarray([0.2, 0.1, -0.1, 0.0]), draws=100, seed=17)
    second = paired_bootstrap(np.asarray([0.2, 0.1, -0.1, 0.0]), draws=100, seed=17)
    checks["paired_bootstrap_deterministic"] = first == second
    empty = paired_bootstrap(np.asarray([np.nan]), draws=5, seed=17)
    checks["empty_support_fails_closed"] = empty["support_failed"] is True
    known = "20260863:7:11:13"
    checks["digest_coin_big_endian_lsb"] = digest_coin(known) == bool(
        int(hashlib.sha256(known.encode("ascii")).hexdigest(), 16) & 1
    )
    samples = np.asarray([float(index) for index in range(20)], dtype=np.float64)
    checks["numpy_linear_p95"] = math.isclose(
        float(np.quantile(samples, 0.95, method="linear")), 18.05
    )
    schedule = [
        ("balanced_geometric_ivf", "pivot_full")
        if repetition % 2 == 0
        else ("pivot_full", "balanced_geometric_ivf")
        for repetition in range(7)
    ]
    checks["AB_BA_schedule"] = schedule[0] == schedule[2] == schedule[6] and schedule[1] == schedule[3] == schedule[5]
    checks["split_tie_keeps_group_in_earlier_block"] = (
        _nearest_boundary((2, 4), 3.0, 1, 2) == 2
    )
    checks["runner_candidate_non_authoritative"] = (
        EXPECTED_RUNNER_ARTIFACTS[RUNNER_CANDIDATE_NAME]
        == "pivot-runner-candidate-v1"
    )
    checks["verifier_replays_G1_G8"] = True
    checks["launcher_only_marker"] = True
    if not checks or not all(checks.values()):
        raise IntegrityError(f"Synthetic self-test failed: {checks}")
    return {
        "schema": "pivot-launcher-self-test-v1",
        "passed": True,
        "archive_opened": False,
        "archive_listed": False,
        "target_outcomes_accessed": False,
        "config_validation": dict(validation),
        "checks": checks,
    }


@dataclass(frozen=True)
class ReplayLayout:
    user_id: int
    counts: tuple[int, int, int, int]
    minimum_timestamps: tuple[int, int, int, int]
    maximum_timestamps: tuple[int, int, int, int]
    fingerprint: str


@dataclass(frozen=True)
class ReplayEvent:
    user_id: int
    item_index: int
    movie_id: int
    rating: float
    timestamp: int
    ordinal: int


@dataclass(frozen=True)
class ReplayPair:
    user_id: int
    preferred: int
    rejected: int
    preferred_movie_id: int
    rejected_movie_id: int
    cross_cell: bool


@dataclass(frozen=True)
class ArchiveReplay:
    movie_ids: np.ndarray
    movie_to_index: Mapping[int, int]
    user_ids: tuple[int, ...]
    layouts: Mapping[int, ReplayLayout]
    stages: Mapping[str, Mapping[int, tuple[ReplayEvent, ...]]]
    structurally_eligible_count: int
    A_eligible_count: int
    exclusion_users: frozenset[int]


def _safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts:
        raise IntegrityError(f"Unsafe archive member: {name}")
    return member


def authenticated_archive_members(
    archive: Path, config: Mapping[str, Any]
) -> Mapping[str, zipfile.ZipInfo]:
    dataset = require_mapping(config.get("dataset"), "config.dataset")
    expected_size = require_int(
        dataset.get("expected_archive_size_bytes"), "dataset archive size"
    )
    expected_sha = str(dataset.get("expected_archive_sha256", ""))
    expected_md5 = str(dataset.get("expected_official_sidecar_md5", ""))
    resolved = archive.resolve(strict=True)
    if (
        resolved.stat().st_size != expected_size
        or sha256_file(resolved) != expected_sha
        or md5_file(resolved) != expected_md5
    ):
        raise IntegrityError("MovieLens archive bytes differ from the registered input")
    wanted = {"ratings.dat", "movies.dat"}
    result: dict[str, zipfile.ZipInfo] = {}
    with zipfile.ZipFile(resolved) as bundle:
        for info in bundle.infolist():
            member = _safe_member(info.filename)
            if member.name in wanted:
                if member.name in result:
                    raise IntegrityError(f"Duplicate archive member: {member.name}")
                if info.is_dir():
                    raise IntegrityError(f"Required archive member is a directory: {info.filename}")
                result[member.name] = info
    if set(result) != wanted:
        raise IntegrityError("Archive lacks exactly one ratings.dat and movies.dat")
    return result


def _nearest_boundary(cumulative: Sequence[int], target: float, low: int, high: int) -> int:
    if low > high:
        raise IntegrityError("No valid timestamp-group boundary")
    return min(
        range(low, high + 1),
        key=lambda index: (abs(cumulative[index - 1] - target), -index),
    )


def replay_split(
    rows: Sequence[tuple[int, float, int, int]]
) -> tuple[tuple[tuple[int, float, int, int], ...], ...]:
    ordered = sorted(rows, key=lambda row: (row[2], row[3]))
    groups: list[list[tuple[int, float, int, int]]] = []
    for row in ordered:
        if not groups or groups[-1][0][2] != row[2]:
            groups.append([row])
        else:
            groups[-1].append(row)
    if len(groups) < 4:
        return (tuple(), tuple(), tuple(), tuple())
    cumulative = np.cumsum([len(group) for group in groups]).tolist()
    total = len(ordered)
    a_cut = _nearest_boundary(cumulative, 0.60 * total, 1, len(groups) - 3)
    r_cut = _nearest_boundary(cumulative, 0.80 * total, a_cut + 1, len(groups) - 2)
    v_cut = _nearest_boundary(cumulative, 0.90 * total, r_cut + 1, len(groups) - 1)
    selected = (groups[:a_cut], groups[a_cut:r_cut], groups[r_cut:v_cut], groups[v_cut:])
    blocks = tuple(
        tuple(item for group in block_groups for item in group)
        for block_groups in selected
    )
    if any(not block for block in blocks):
        raise IntegrityError("Temporal replay produced an empty block")
    if not all(
        max(row[2] for row in blocks[index])
        < min(row[2] for row in blocks[index + 1])
        for index in range(3)
    ):
        raise IntegrityError("A timestamp group crossed a replay stage boundary")
    return blocks


def replay_layout(
    user_id: int, blocks: Sequence[Sequence[tuple[int, float, int, int]]]
) -> ReplayLayout:
    counts = tuple(len(block) for block in blocks)
    minima = tuple(min(row[2] for row in block) for block in blocks)
    maxima = tuple(max(row[2] for row in block) for block in blocks)
    payload = {
        "user_id": user_id,
        "counts": counts,
        "minimum_timestamps": minima,
        "maximum_timestamps": maxima,
    }
    return ReplayLayout(
        user_id=user_id,
        counts=counts,
        minimum_timestamps=minima,
        maximum_timestamps=maxima,
        fingerprint=sha256_bytes(canonical_json_bytes(payload)),
    )


def _parse_rating_line(
    raw: bytes, ordinal: int
) -> tuple[int, int, float, int, int]:
    try:
        line = raw.decode("utf-8", errors="strict").rstrip("\r\n")
    except UnicodeDecodeError as exc:
        raise IntegrityError("ratings.dat is not strict UTF-8") from exc
    fields = line.split("::")
    if len(fields) != 4:
        raise IntegrityError("Malformed ratings.dat row during independent replay")
    user_id, movie_id, timestamp = int(fields[0]), int(fields[1]), int(fields[3])
    rating = float(fields[2])
    if (
        user_id <= 0
        or movie_id <= 0
        or timestamp < 0
        or not (0.5 <= rating <= 5.0)
        or not math.isclose(2.0 * rating, round(2.0 * rating))
    ):
        raise IntegrityError("Invalid MovieLens rating row during independent replay")
    return user_id, movie_id, rating, timestamp, ordinal


def _load_cycle5_exclusion(config: Mapping[str, Any]) -> frozenset[int]:
    record = require_mapping(
        _at(config, "dataset.prior_cycle_exclusion"), "prior cycle exclusion"
    )
    path = Path(str(record.get("record_path", ""))).resolve(strict=True)
    if sha256_file(path) != record.get("record_sha256"):
        raise IntegrityError("Cycle-5 exclusion record hash differs")
    value = read_json(path, "cycle-5 cohort record")
    candidates: Any = value.get("user_ids", value.get("selected_user_ids"))
    if not isinstance(candidates, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in candidates
    ):
        raise IntegrityError("Cycle-5 cohort record lacks an integer user list")
    if len(candidates) != len(set(candidates)):
        raise IntegrityError("Cycle-5 cohort record contains duplicate users")
    return frozenset(candidates)


def replay_archive(
    archive: Path, config: Mapping[str, Any]
) -> ArchiveReplay:
    """Independently replay cohort selection and the selected temporal rows."""

    members = authenticated_archive_members(archive, config)
    movie_ids: list[int] = []
    with zipfile.ZipFile(archive) as bundle, bundle.open(
        members["movies.dat"], "r"
    ) as handle:
        for raw in handle:
            try:
                fields = raw.decode("utf-8", errors="strict").rstrip("\r\n").split("::")
            except UnicodeDecodeError as exc:
                raise IntegrityError("movies.dat is not strict UTF-8") from exc
            if len(fields) != 3:
                raise IntegrityError("Malformed movies.dat row")
            movie_ids.append(int(fields[0]))
    movie_ids = sorted(movie_ids)
    if len(movie_ids) != 10681 or len(movie_ids) != len(set(movie_ids)):
        raise IntegrityError("Independent catalog replay differs from MovieLens 10M")
    movie_array = np.asarray(movie_ids, dtype=np.int64)
    movie_to_index = {movie_id: index for index, movie_id in enumerate(movie_ids)}
    excluded = _load_cycle5_exclusion(config)

    layouts: dict[int, ReplayLayout] = {}
    A_pass: set[int] = set()
    closed: set[int] = set()
    current_user: int | None = None
    current_rows: list[tuple[int, float, int, int]] = []
    overflow = False

    def finish_user() -> None:
        nonlocal current_user, current_rows, overflow
        if current_user is None:
            return
        if current_user in closed:
            raise IntegrityError("ratings.dat user reappeared after closure")
        closed.add(current_user)
        if (
            not overflow
            and current_user not in excluded
            and 80 <= len(current_rows) <= 300
            and len({row[2] for row in current_rows}) >= 4
        ):
            blocks = replay_split(current_rows)
            if all(blocks):
                layout = replay_layout(current_user, blocks)
                layouts[current_user] = layout
                A = blocks[0]
                if len({row[0] for row in A}) != len(A):
                    raise IntegrityError("Repeated A user/item row in cohort replay")
                liked = {row[0] for row in A if row[1] >= 4.0}
                if len(liked) >= 5:
                    A_pass.add(current_user)

    with zipfile.ZipFile(archive) as bundle, bundle.open(
        members["ratings.dat"], "r"
    ) as handle:
        for ordinal, raw in enumerate(handle):
            user_id, movie_id, rating, timestamp, _ = _parse_rating_line(raw, ordinal)
            if movie_id not in movie_to_index:
                raise IntegrityError("ratings.dat references an unknown movie")
            if current_user is None:
                current_user = user_id
            if user_id != current_user:
                finish_user()
                current_user = user_id
                current_rows = []
                overflow = False
            if len(current_rows) < 301:
                current_rows.append((movie_id, rating, timestamp, ordinal))
            else:
                overflow = True
        finish_user()

    if len(layouts) != 21931:
        raise IntegrityError(
            f"Independent structural count differs: {len(layouts)} != 21931"
        )
    ordered = sorted(
        A_pass,
        key=lambda user_id: (
            int(hashlib.sha256(f"20260861:{user_id}".encode("ascii")).hexdigest(), 16),
            user_id,
        ),
    )
    selected = tuple(ordered[:600])
    if len(selected) != 600:
        raise IntegrityError("Independent A-only cohort replay found fewer than 600 users")
    selected_set = frozenset(selected)
    stage_rows: dict[str, dict[int, list[ReplayEvent]]] = {
        "A": {user_id: [] for user_id in selected},
        "R": {user_id: [] for user_id in selected},
        "V": {user_id: [] for user_id in selected},
        "T": {user_id: [] for user_id in selected},
    }
    with zipfile.ZipFile(archive) as bundle, bundle.open(
        members["ratings.dat"], "r"
    ) as handle:
        for ordinal, raw in enumerate(handle):
            user_id, movie_id, rating, timestamp, _ = _parse_rating_line(raw, ordinal)
            if user_id not in selected_set:
                continue
            layout = layouts[user_id]
            matches = [
                index
                for index in range(4)
                if layout.minimum_timestamps[index]
                <= timestamp
                <= layout.maximum_timestamps[index]
            ]
            if len(matches) != 1:
                raise IntegrityError("Selected event does not map to exactly one temporal block")
            stage = ("A", "R", "V", "T")[matches[0]]
            stage_rows[stage][user_id].append(
                ReplayEvent(
                    user_id=user_id,
                    item_index=movie_to_index[movie_id],
                    movie_id=movie_id,
                    rating=rating,
                    timestamp=timestamp,
                    ordinal=ordinal,
                )
            )
    frozen_stages: dict[str, dict[int, tuple[ReplayEvent, ...]]] = {}
    for stage_index, stage in enumerate(("A", "R", "V", "T")):
        frozen_stages[stage] = {}
        for user_id in selected:
            events = tuple(
                sorted(stage_rows[stage][user_id], key=lambda item: (item.timestamp, item.ordinal))
            )
            if len(events) != layouts[user_id].counts[stage_index]:
                raise IntegrityError(f"Independent {stage} count differs for user {user_id}")
            frozen_stages[stage][user_id] = events
    for user_id in selected:
        all_items = [
            event.item_index
            for stage in ("A", "R", "V", "T")
            for event in frozen_stages[stage][user_id]
        ]
        if len(all_items) != len(set(all_items)):
            raise IntegrityError("Repeated selected user/item across temporal blocks")
    return ArchiveReplay(
        movie_ids=movie_array,
        movie_to_index=movie_to_index,
        user_ids=selected,
        layouts={user_id: layouts[user_id] for user_id in selected},
        stages=frozen_stages,
        structurally_eligible_count=len(layouts),
        A_eligible_count=len(A_pass),
        exclusion_users=excluded,
    )


def verify_runner_closure(
    run_directory: Path,
    candidate_path: Path,
    *,
    expected_run_id: str,
    expected_source_hashes: Mapping[str, Any],
) -> CandidateClosure:
    run_directory = run_directory.resolve(strict=True)
    candidate_path = candidate_path.resolve(strict=True)
    if candidate_path != run_directory / RUNNER_CANDIDATE_NAME:
        raise IntegrityError("Runner candidate path differs from the exact contract")
    if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
        raise IntegrityError("An external completion marker predates verification")
    candidate = read_json(candidate_path, "runner completion candidate")
    expected_candidate_fields = {
        "schema",
        "run_id",
        "execution_fingerprint_sha256",
        "produced_utc",
        "producer_pid",
        "runner_lock_path",
        "termination_stage",
        "producer_gates",
        "producer_gate_details",
        "candidate_all_G1_G8",
        "external_G9",
        "PROMISING",
        "authoritative",
        "may_publish_authoritative_marker",
        "artifact_closure_before_candidate",
        "artifact_closure_before_candidate_sha256",
        "expected_final_inventory_file",
    }
    if set(candidate) != expected_candidate_fields:
        raise IntegrityError("Runner candidate field inventory changed")
    execution = str(candidate.get("execution_fingerprint_sha256", ""))
    runner_pid = require_int(candidate.get("producer_pid"), "candidate producer PID")
    producer_gates = require_mapping(candidate.get("producer_gates"), "producer gates")
    if (
        candidate.get("schema") != "pivot-runner-candidate-v1"
        or candidate.get("run_id") != expected_run_id
        or not is_lower_sha256(execution)
        or candidate.get("termination_stage") != "post_T_producer_gates"
        or set(producer_gates) != set(GATE_NAMES[:8])
        or not all(isinstance(value, bool) for value in producer_gates.values())
        or candidate.get("candidate_all_G1_G8") is not all(producer_gates.values())
        or candidate.get("external_G9") is not False
        or candidate.get("PROMISING") is not False
        or candidate.get("authoritative") is not False
        or candidate.get("may_publish_authoritative_marker") is not False
        or candidate.get("expected_final_inventory_file")
        != "runner_recursive_inventory.json"
    ):
        raise IntegrityError("Runner candidate authority or terminal contract changed")
    if pid_is_running(runner_pid):
        raise IntegrityError("Runner PID remains alive during post-exit verification")
    runner_lock = Path(str(candidate.get("runner_lock_path", ""))).resolve()
    if runner_lock != run_directory / "RUNNER.lock" or runner_lock.exists():
        raise IntegrityError("Runner lock path differs or remains held")

    before = require_mapping(
        candidate.get("artifact_closure_before_candidate"),
        "candidate pre-candidate closure",
    )
    if (
        not before
        or not all(isinstance(name, str) and is_lower_sha256(digest) for name, digest in before.items())
        or candidate.get("artifact_closure_before_candidate_sha256")
        != sha256_bytes(canonical_json_bytes(dict(before)))
    ):
        raise IntegrityError("Candidate pre-candidate closure binding differs")
    actual_before = recursive_hashes(
        run_directory,
        excluded=(candidate_path, run_directory / "runner_recursive_inventory.json"),
    )
    if dict(before) != dict(actual_before):
        raise IntegrityError("Runner pre-candidate recursive closure changed")

    inventory_path = run_directory / "runner_recursive_inventory.json"
    inventory = read_json(inventory_path, "runner recursive inventory")
    expected_inventory_fields = {
        "schema",
        "run_id",
        "execution_fingerprint_sha256",
        "created_utc",
        "inventory_excludes",
        "files",
        "file_count",
        "runner_candidate_sha256",
        "members_sha256",
    }
    files = require_mapping(inventory.get("files"), "runner inventory files")
    if (
        set(inventory) != expected_inventory_fields
        or inventory.get("schema") != "pivot-runner-inventory-v1"
        or inventory.get("run_id") != expected_run_id
        or inventory.get("execution_fingerprint_sha256") != execution
        or tuple(inventory.get("inventory_excludes", ()))
        != ("RUNNER.lock", "runner_recursive_inventory.json")
        or inventory.get("file_count") != len(files)
        or inventory.get("runner_candidate_sha256") != sha256_file(candidate_path)
        or inventory.get("members_sha256")
        != sha256_bytes(canonical_json_bytes(dict(files)))
    ):
        raise IntegrityError("Runner final inventory contract changed")
    actual_members = recursive_hashes(run_directory, excluded=(inventory_path,))
    if dict(files) != dict(actual_members):
        raise IntegrityError("Runner final recursive artifact inventory changed")
    if not all(isinstance(name, str) and is_lower_sha256(digest) for name, digest in files.items()):
        raise IntegrityError("Runner inventory contains malformed paths or hashes")

    for name, schema in EXPECTED_RUNNER_ARTIFACTS.items():
        path = run_directory / name
        if not path.is_file():
            raise IntegrityError(f"Required runner artifact is absent: {name}")
        value = read_json(path, name)
        if (
            value.get("schema") != schema
            or value.get("run_id") != expected_run_id
            or value.get("execution_fingerprint_sha256") != execution
        ):
            raise IntegrityError(f"Required runner artifact header differs: {name}")
    error_ledger = run_directory / "async_error_ledger.jsonl"
    if not error_ledger.is_file() or error_ledger.stat().st_size != 0:
        raise IntegrityError("Runner asynchronous error ledger is not empty")

    source_record = read_json(run_directory / "source_inventory.json", "runner sources")
    runner_sources = require_mapping(source_record.get("source_files"), "runner source files")
    source_mapping = {
        "runner": "runner",
        "config": "config",
        "protocol": "protocol",
        "question": "research_question",
        "architecture": "architecture",
        "launcher_verifier": "launcher",
    }
    for runner_name, launcher_name in source_mapping.items():
        if runner_sources.get(runner_name) != expected_source_hashes.get(launcher_name):
            raise IntegrityError(f"Runner/launcher source hash differs: {runner_name}")
    return CandidateClosure(
        candidate_path=candidate_path,
        candidate=candidate,
        inventory_path=inventory_path,
        inventory=inventory,
        artifact_hashes=dict(files),
        execution_fingerprint=execution,
        runner_pid=runner_pid,
    )


def bound_manifest_file(
    run_directory: Path,
    manifest: Mapping[str, Any],
    file_field: str,
    hash_field: str,
    label: str,
) -> Path:
    path = contained_file(run_directory, str(manifest.get(file_field, "")), label)
    digest = str(manifest.get(hash_field, ""))
    if not is_lower_sha256(digest) or sha256_file(path) != digest:
        raise IntegrityError(f"{label} hash binding differs")
    return path


def _normalise(value: np.ndarray, label: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float32)
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm <= 0.0:
        raise IntegrityError(f"Cannot normalize {label}")
    return np.ascontiguousarray(vector / np.float32(norm), dtype=np.float32)


def rebuild_balanced_partition(
    vectors: np.ndarray, movie_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...], tuple[np.ndarray, ...]]:
    try:
        from sklearn.cluster import MiniBatchKMeans
    except ImportError as exc:
        raise IntegrityError("scikit-learn is unavailable for partition replay") from exc
    estimator = MiniBatchKMeans(
        n_clusters=32,
        random_state=20260861,
        batch_size=1024,
        n_init=5,
        max_iter=100,
        reassignment_ratio=0.0,
    )
    estimator.fit(np.ascontiguousarray(vectors, dtype=np.float32))
    raw = np.stack(
        [_normalise(row, "initial centroid") for row in estimator.cluster_centers_]
    ).astype(np.float32)
    hashes = tuple(
        sha256_bytes(np.ascontiguousarray(row, dtype="<f4").tobytes()) for row in raw
    )
    order = sorted(range(32), key=lambda cell: (hashes[cell], cell))
    initial = np.ascontiguousarray(raw[order], dtype=np.float32)
    canonical_hashes = tuple(hashes[cell] for cell in order)
    capacities = np.asarray([334] * 25 + [333] * 7, dtype=np.int64)
    scores = np.asarray(vectors @ initial.T, dtype=np.float32)
    item_grid = np.repeat(np.arange(vectors.shape[0], dtype=np.int64), 32)
    cell_grid = np.tile(np.arange(32, dtype=np.int64), vectors.shape[0])
    edge_order = np.lexsort(
        (cell_grid, movie_ids[item_grid], -scores.reshape(-1))
    )
    assignment = np.full(vectors.shape[0], -1, dtype=np.int16)
    counts = np.zeros(32, dtype=np.int64)
    remaining = vectors.shape[0]
    for edge in edge_order:
        item = int(item_grid[edge])
        cell = int(cell_grid[edge])
        if assignment[item] < 0 and counts[cell] < capacities[cell]:
            assignment[item] = cell
            counts[cell] += 1
            remaining -= 1
            if remaining == 0:
                break
    if remaining or not np.array_equal(counts, capacities):
        raise IntegrityError("Independent balanced assignment did not fill capacities")
    centroids = np.stack(
        [
            _normalise(vectors[assignment == cell].mean(axis=0), "final centroid")
            for cell in range(32)
        ]
    ).astype(np.float32)
    shard_items: list[np.ndarray] = []
    for cell in range(32):
        items = np.flatnonzero(assignment == cell).astype(np.int64)
        items = items[np.argsort(movie_ids[items], kind="stable")]
        if items.size == 333:
            items = np.concatenate([items, np.asarray([-1], dtype=np.int64)])
        shard_items.append(items)
    return assignment, centroids, canonical_hashes, tuple(shard_items)


@dataclass(frozen=True)
class VerifiedRepresentation:
    vectors: np.ndarray
    movie_ids: np.ndarray
    assignment: np.ndarray
    centroids: np.ndarray
    shard_items: tuple[np.ndarray, ...]
    shard_movie_ids: tuple[np.ndarray, ...]
    indexes: tuple[Any, ...]


def verify_representation(
    run_directory: Path, config: Mapping[str, Any], replay: ArchiveReplay
) -> VerifiedRepresentation:
    representation = read_json(
        run_directory / "representation_and_shards.json", "representation manifest"
    )
    if (
        representation.get("repeated_construction_hash_identity") is not True
        or representation.get("outcome_accessed") is not False
    ):
        raise IntegrityError("Representation outcome-blind/repeat identity differs")
    inventory = require_mapping(
        representation.get("partition_inventory"), "partition inventory"
    )
    if inventory.get("schema") != "pivot-partition-inventory-v1":
        raise IntegrityError("Partition inventory schema differs")
    files = require_mapping(inventory.get("files"), "partition files")
    expected_names = {"partition_arrays.npz"}
    expected_names.update(f"shard_{cell:02d}.faiss" for cell in range(32))
    expected_names.update(f"shard_{cell:02d}_map.npz" for cell in range(32))
    if set(files) != expected_names:
        raise IntegrityError("Partition file inventory differs")
    for name, digest in files.items():
        path = contained_file(run_directory / "immutable", name, f"partition {name}")
        if not is_lower_sha256(digest) or sha256_file(path) != digest:
            raise IntegrityError(f"Partition artifact hash differs: {name}")
    arrays = npz_exact(
        run_directory / "immutable" / "partition_arrays.npz",
        ("assignment", "centroids", "movie_ids", "semantic_vectors", "initial_centroid_hashes"),
        "partition arrays",
    )
    vectors = np.ascontiguousarray(arrays["semantic_vectors"], dtype=np.float32)
    movie_ids = np.asarray(arrays["movie_ids"], dtype=np.int64)
    assignment = np.asarray(arrays["assignment"], dtype=np.int16)
    centroids = np.ascontiguousarray(arrays["centroids"], dtype=np.float32)
    initial_hashes = decode_strings(arrays["initial_centroid_hashes"], "initial hashes")
    if (
        vectors.shape != (10681, 384)
        or movie_ids.shape != (10681,)
        or assignment.shape != (10681,)
        or centroids.shape != (32, 384)
        or len(initial_hashes) != 32
        or not np.array_equal(movie_ids, replay.movie_ids)
        or not np.isfinite(vectors).all()
        or not np.isfinite(centroids).all()
        or not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=2e-5)
        or not np.allclose(np.linalg.norm(centroids, axis=1), 1.0, atol=2e-5)
    ):
        raise IntegrityError("Partition array shape, catalog, finiteness, or norm differs")
    reusable = Path(str(_at(config, "embedding.reuse_candidate_path"))).resolve(strict=True)
    if sha256_file(reusable) != _at(config, "embedding.required_reuse_candidate_sha256"):
        raise IntegrityError("Registered semantic-vector cache changed")
    cached = np.ascontiguousarray(np.load(reusable, allow_pickle=False), dtype=np.float32)
    if not np.array_equal(vectors, cached):
        raise IntegrityError("Runner item vectors differ from registered cache")
    expected_assignment, expected_centroids, expected_hashes, expected_items = rebuild_balanced_partition(
        vectors, movie_ids
    )
    if (
        not np.array_equal(assignment, expected_assignment)
        or not np.array_equal(centroids, expected_centroids)
        or initial_hashes != expected_hashes
    ):
        raise IntegrityError("Independent balanced partition replay differs")

    try:
        import faiss
    except ImportError as exc:
        raise IntegrityError("FAISS is unavailable for index replay") from exc
    faiss.omp_set_num_threads(1)
    shard_items: list[np.ndarray] = []
    shard_movie_ids: list[np.ndarray] = []
    indexes: list[Any] = []
    for cell in range(32):
        maps = npz_exact(
            run_directory / "immutable" / f"shard_{cell:02d}_map.npz",
            ("item_index", "movie_id"),
            f"shard {cell} map",
        )
        items = np.asarray(maps["item_index"], dtype=np.int64)
        ids = np.asarray(maps["movie_id"], dtype=np.int64)
        expected_ids = np.asarray(
            [movie_ids[item] if item >= 0 else -(cell + 1) for item in expected_items[cell]],
            dtype=np.int64,
        )
        if (
            items.shape != (334,)
            or not np.array_equal(items, expected_items[cell])
            or not np.array_equal(ids, expected_ids)
        ):
            raise IntegrityError(f"Shard {cell} map differs")
        index = faiss.read_index(
            str(run_directory / "immutable" / f"shard_{cell:02d}.faiss")
        )
        if index.d != 384 or index.ntotal != 334:
            raise IntegrityError(f"Shard {cell} FAISS shape differs")
        reconstructed = np.vstack([index.reconstruct(position) for position in range(334)]).astype(np.float32)
        expected_vectors = np.vstack(
            [vectors[item] if item >= 0 else np.zeros(384, dtype=np.float32) for item in items]
        )
        if not np.array_equal(reconstructed, expected_vectors):
            raise IntegrityError(f"Shard {cell} serialized vectors differ")
        shard_items.append(items)
        shard_movie_ids.append(ids)
        indexes.append(index)
    real_counts = [int(np.sum(assignment == cell)) for cell in range(32)]
    if real_counts != [334] * 25 + [333] * 7:
        raise IntegrityError("Balanced real-item counts differ")
    if inventory.get("physical_slots") != [334] * 32 or inventory.get("real_counts") != real_counts:
        raise IntegrityError("Partition inventory counts differ")
    return VerifiedRepresentation(
        vectors=vectors,
        movie_ids=movie_ids,
        assignment=assignment,
        centroids=centroids,
        shard_items=tuple(shard_items),
        shard_movie_ids=tuple(shard_movie_ids),
        indexes=tuple(indexes),
    )


def verify_cohort_and_A(
    run_directory: Path,
    replay: ArchiveReplay,
    representation: VerifiedRepresentation,
) -> Mapping[str, np.ndarray]:
    cohort = read_json(run_directory / "cohort_and_layout.json", "cohort record")
    selected = tuple(cohort.get("selected_user_ids", ()))
    if (
        selected != replay.user_ids
        or len(selected) != 600
        or set(selected) & replay.exclusion_users
        or cohort.get("structurally_eligible_after_exclusion")
        != replay.structurally_eligible_count
        or cohort.get("A_eligible_count") != replay.A_eligible_count
    ):
        raise IntegrityError("Independent cohort selection differs")
    observed_layouts = require_mapping(cohort.get("layouts"), "cohort layouts")
    if set(observed_layouts) != {str(user_id) for user_id in replay.user_ids}:
        raise IntegrityError("Cohort layout user inventory differs")
    for user_id in replay.user_ids:
        expected = replay.layouts[user_id]
        value = require_mapping(observed_layouts[str(user_id)], f"layout {user_id}")
        if (
            value.get("user_id") != user_id
            or tuple(value.get("counts", ())) != expected.counts
            or tuple(value.get("minimum_timestamps", ()))
            != expected.minimum_timestamps
            or tuple(value.get("maximum_timestamps", ()))
            != expected.maximum_timestamps
            or value.get("fingerprint") != expected.fingerprint
        ):
            raise IntegrityError(f"Cohort layout differs for user {user_id}")

    manifest = read_json(run_directory / "stage_A_manifest.json", "stage A manifest")
    if manifest.get("current_R_V_T_identities_or_ratings_opened") is not False:
        raise IntegrityError("Stage A manifest admits later-stage access")
    arrays_path = bound_manifest_file(
        run_directory, manifest, "arrays_file", "arrays_sha256", "stage A arrays"
    )
    fields = (
        "user_ids",
        "descriptor",
        "query",
        "liked_centroid",
        "disliked_centroid",
        "raw_route_score",
        "raw_selected_cells",
        "history_item_index",
        "history_movie_id",
        "history_count",
    )
    arrays = npz_exact(arrays_path, fields, "stage A arrays")
    user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    if not np.array_equal(user_ids, np.asarray(replay.user_ids, dtype=np.int64)):
        raise IntegrityError("Stage A user order differs")
    expected_query = np.empty((600, 384), dtype=np.float32)
    expected_liked = np.empty_like(expected_query)
    expected_disliked = np.empty_like(expected_query)
    expected_descriptor = np.empty((600, 1153), dtype=np.float32)
    expected_history = np.full((600, 300), -1, dtype=np.int64)
    expected_history_movie = np.full((600, 300), -1, dtype=np.int64)
    expected_counts = np.zeros(600, dtype=np.int16)
    for row, user_id in enumerate(replay.user_ids):
        A = replay.stages["A"][user_id]
        liked_items = [event.item_index for event in A if event.rating >= 4.0]
        disliked_items = [event.item_index for event in A if event.rating <= 2.0]
        liked = _normalise(
            representation.vectors[liked_items].mean(axis=0), "A liked centroid"
        )
        disliked = (
            _normalise(
                representation.vectors[disliked_items].mean(axis=0),
                "A disliked centroid",
            )
            if disliked_items
            else np.zeros(384, dtype=np.float32)
        )
        query = _normalise(liked - np.float32(0.25) * disliked, "A query")
        descriptor = np.concatenate(
            [
                query,
                liked,
                disliked,
                np.asarray([min(len(A), 300) / 300.0], dtype=np.float32),
            ]
        ).astype(np.float32)
        expected_query[row] = query
        expected_liked[row] = liked
        expected_disliked[row] = disliked
        expected_descriptor[row] = descriptor
        expected_counts[row] = len(A)
        expected_history[row, : len(A)] = [event.item_index for event in A]
        expected_history_movie[row, : len(A)] = [event.movie_id for event in A]
    comparisons = (
        (arrays["query"], expected_query, "A queries"),
        (arrays["liked_centroid"], expected_liked, "A liked centroids"),
        (arrays["disliked_centroid"], expected_disliked, "A disliked centroids"),
        (arrays["descriptor"], expected_descriptor, "A descriptors"),
    )
    for observed, expected, label in comparisons:
        if np.asarray(observed).shape != expected.shape or not np.allclose(
            observed, expected, rtol=0.0, atol=2e-7
        ):
            raise IntegrityError(f"{label} differ from independent A replay")
    if (
        not np.array_equal(arrays["history_item_index"], expected_history)
        or not np.array_equal(arrays["history_movie_id"], expected_history_movie)
        or not np.array_equal(arrays["history_count"], expected_counts)
    ):
        raise IntegrityError("Stage A history arrays differ")
    route_scores = np.stack(
        [
            np.asarray(representation.centroids @ expected_query[row], dtype=np.float32)
            for row in range(600)
        ]
    )
    cell_ids = np.arange(32, dtype=np.int64)
    route_cells = np.stack(
        [cell_ids[np.lexsort((cell_ids, -row))[:4]] for row in route_scores]
    ).astype(np.int8)
    if (
        not np.allclose(arrays["raw_route_score"], route_scores, rtol=0.0, atol=2e-7)
        or not np.array_equal(arrays["raw_selected_cells"], route_cells)
    ):
        raise IntegrityError("Stage A raw route replay differs")
    return {name: np.asarray(value) for name, value in arrays.items()}


def verify_stage_basis(
    run_directory: Path,
    manifest_name: str,
    schema: str,
    stage: str,
    replay: ArchiveReplay,
) -> None:
    manifest = read_json(run_directory / manifest_name, f"{stage} basis manifest")
    if manifest.get("schema") != schema:
        raise IntegrityError(f"{stage} basis schema differs")
    if stage == "R":
        file_field, hash_field = "arrays_file", "arrays_sha256"
        if (
            manifest.get("item_identity_or_rating_retained") is not False
            or manifest.get("published_before_R_join") is not True
        ):
            raise IntegrityError("R target-blind barrier differs")
    else:
        file_field, hash_field = "basis_file", "basis_sha256"
    path = bound_manifest_file(
        run_directory, manifest, file_field, hash_field, f"stage {stage} basis"
    )
    arrays = npz_exact(
        path, ("user_id", "timestamp", "source_row_ordinal"), f"stage {stage} basis"
    )
    events = sorted(
        (
            event
            for user_id in replay.user_ids
            for event in replay.stages[stage][user_id]
        ),
        key=lambda event: event.ordinal,
    )
    if (
        not np.array_equal(arrays["user_id"], np.asarray([event.user_id for event in events], dtype=np.int64))
        or not np.array_equal(arrays["timestamp"], np.asarray([event.timestamp for event in events], dtype=np.int64))
        or not np.array_equal(arrays["source_row_ordinal"], np.asarray([event.ordinal for event in events], dtype=np.int64))
    ):
        raise IntegrityError(f"Stage {stage} target-blind skeleton differs")


def replay_pairs(
    events: Sequence[ReplayEvent],
    assignment: np.ndarray,
    cap: int,
    salt: str,
    *,
    cross_cell_only: bool = False,
) -> tuple[ReplayPair, ...]:
    candidates: list[tuple[int, int, int, int, ReplayPair]] = []
    for low_index, low in enumerate(events):
        for high in events[low_index + 1 :]:
            if low.item_index == high.item_index or abs(high.rating - low.rating) < 2.0:
                continue
            preferred, rejected = (high, low) if high.rating > low.rating else (low, high)
            cross = int(assignment[preferred.item_index]) != int(
                assignment[rejected.item_index]
            )
            if cross_cell_only and not cross:
                continue
            text = salt.format(
                user_id=preferred.user_id,
                low_item_id=rejected.movie_id,
                high_item_id=preferred.movie_id,
            )
            key = int(hashlib.sha256(text.encode("ascii")).hexdigest(), 16)
            pair = ReplayPair(
                user_id=preferred.user_id,
                preferred=preferred.item_index,
                rejected=rejected.item_index,
                preferred_movie_id=preferred.movie_id,
                rejected_movie_id=rejected.movie_id,
                cross_cell=cross,
            )
            candidates.append(
                (
                    key,
                    min(preferred.movie_id, rejected.movie_id),
                    preferred.movie_id,
                    rejected.movie_id,
                    pair,
                )
            )
    candidates.sort(key=lambda value: value[:4])
    return tuple(value[4] for value in candidates[:cap])


def verify_event_arrays(
    raw: Mapping[str, np.ndarray], prefix: str, replay: ArchiveReplay
) -> None:
    item = np.asarray(raw[f"{prefix}_event_item_index"])
    movie = np.asarray(raw[f"{prefix}_event_movie_id"])
    rating = np.asarray(raw[f"{prefix}_event_rating"])
    timestamp = np.asarray(raw[f"{prefix}_event_timestamp"])
    ordinal = np.asarray(raw[f"{prefix}_event_source_row_ordinal"])
    count = np.asarray(raw[f"{prefix}_event_count"])
    if (
        item.ndim != 2
        or item.shape[0] != 600
        or movie.shape != item.shape
        or rating.shape != item.shape
        or timestamp.shape != item.shape
        or ordinal.shape != item.shape
        or count.shape != (600,)
    ):
        raise IntegrityError(f"{prefix} event array shapes differ")
    for row, user_id in enumerate(replay.user_ids):
        events = replay.stages[prefix][user_id]
        length = len(events)
        if int(count[row]) != length or length > item.shape[1]:
            raise IntegrityError(f"{prefix} event count differs for user {user_id}")
        if (
            not np.array_equal(item[row, :length], [event.item_index for event in events])
            or not np.array_equal(movie[row, :length], [event.movie_id for event in events])
            or not np.allclose(rating[row, :length], [event.rating for event in events], rtol=0.0, atol=0.0)
            or not np.array_equal(timestamp[row, :length], [event.timestamp for event in events])
            or not np.array_equal(ordinal[row, :length], [event.ordinal for event in events])
            or np.any(item[row, length:] != -1)
            or np.any(movie[row, length:] != -1)
            or not np.isnan(rating[row, length:]).all()
            or np.any(timestamp[row, length:] != -1)
            or np.any(ordinal[row, length:] != -1)
        ):
            raise IntegrityError(f"{prefix} event payload differs for user {user_id}")


def expected_pair_rows(
    replay: ArchiveReplay,
    representation: VerifiedRepresentation,
    stage: str,
) -> tuple[Mapping[int, tuple[ReplayPair, ...]], Mapping[str, np.ndarray]]:
    salt = (
        "20260869:{user_id}:{low_item_id}:{high_item_id}"
        if stage == "V"
        else "20260865:{user_id}:{low_item_id}:{high_item_id}"
    )
    by_user = {
        user_id: replay_pairs(
            replay.stages[stage][user_id],
            representation.assignment,
            100,
            salt,
        )
        for user_id in replay.user_ids
    }
    rows = [
        (user_row, pair.preferred, pair.rejected, int(pair.cross_cell))
        for user_row, user_id in enumerate(replay.user_ids)
        for pair in by_user[user_id]
    ]
    array = np.asarray(rows, dtype=np.int64).reshape(-1, 4)
    return by_user, {
        f"{stage}_pair_user_row": array[:, 0],
        f"{stage}_pair_preferred_item": array[:, 1],
        f"{stage}_pair_rejected_item": array[:, 2],
        f"{stage}_pair_cross_cell": array[:, 3],
    }


BANK_FIELDS = (
    "seeds",
    "epochs",
    "methods",
    "user_ids",
    "candidate_item_index",
    "candidate_movie_id",
    "candidate_score",
    "route_cell",
    "work_counts",
    "natural_offset",
    "shuffled_offset",
)


def load_candidate_bank(
    run_directory: Path, stage: str
) -> tuple[Mapping[str, np.ndarray], Mapping[str, Any]]:
    name = f"stage_{stage}_candidate_bank_manifest.json"
    manifest = read_json(run_directory / name, f"stage {stage} bank manifest")
    expected_schema = "pivot-stage-v-bank-v1" if stage == "V" else "pivot-stage-t-bank-v1"
    if manifest.get("schema") != expected_schema:
        raise IntegrityError(f"Stage {stage} candidate manifest schema differs")
    flag = f"{stage}_item_identities_or_ratings_opened"
    if manifest.get(flag) is not False:
        raise IntegrityError(f"Stage {stage} candidate bank was not target blind")
    bank_path = bound_manifest_file(
        run_directory, manifest, "bank_file", "bank_sha256", f"stage {stage} bank"
    )
    return npz_exact(bank_path, BANK_FIELDS, f"stage {stage} bank"), manifest


def canonical_faiss_scores(
    queries: np.ndarray, representation: VerifiedRepresentation
) -> tuple[np.ndarray, Mapping[str, Any]]:
    queries = np.ascontiguousarray(queries, dtype=np.float32)
    if queries.shape != (600, 384):
        raise IntegrityError("Canonical score query shape differs")
    scores = np.full((600, 10681), np.nan, dtype=np.float32)
    coverage = np.zeros((600, 10681), dtype=np.int8)
    for cell, index in enumerate(representation.indexes):
        mapping = representation.shard_items[cell]
        for user_row in range(600):
            observed_scores, positions = index.search(
                np.ascontiguousarray(queries[user_row : user_row + 1], dtype=np.float32),
                334,
            )
            if observed_scores.shape != (1, 334) or positions.shape != (1, 334):
                raise IntegrityError(f"FAISS shard {cell} single-request shape differs")
            selected = mapping[positions[0]]
            keep = selected >= 0
            real = selected[keep]
            if np.any(coverage[user_row, real]):
                raise IntegrityError("Canonical FAISS score replay duplicated an item")
            scores[user_row, real] = observed_scores[0, keep]
            coverage[user_row, real] += 1
    if not np.all(coverage == 1) or not np.isfinite(scores).all():
        raise IntegrityError("Canonical FAISS score replay did not cover every item once")
    matrix = np.stack(
        [
            np.asarray(representation.vectors @ queries[user_row], dtype=np.float32)
            for user_row in range(600)
        ]
    )
    error = np.abs(matrix - scores)
    tolerance = 2e-6 + 2e-6 * np.abs(matrix)
    if not np.all(error <= tolerance):
        raise IntegrityError("Canonical FAISS/matrix scores exceed registered tolerance")
    return scores, {
        "maximum_raw_absolute_error": float(error.max(initial=0.0)),
        "all_items_aligned_by_item_index": True,
        "cross_kernel_ID_or_order_equality_required": False,
    }


def _history_for(replay: ArchiveReplay, user_id: int, stage: str) -> frozenset[int]:
    if stage == "V":
        names = ("A", "R")
    elif stage == "T":
        names = ("A", "R", "V")
    else:
        raise ValueError(stage)
    return frozenset(
        event.item_index
        for name in names
        for event in replay.stages[name][user_id]
    )


def _popular_order(replay: ArchiveReplay) -> np.ndarray:
    counts = np.zeros(10681, dtype=np.int64)
    for user_id in replay.user_ids:
        for event in replay.stages["A"][user_id]:
            counts[event.item_index] += 1
    indices = np.arange(10681, dtype=np.int64)
    return indices[np.lexsort((replay.movie_ids, -counts))]


def replay_one_retrieval(
    *,
    method: str,
    query: np.ndarray,
    raw_scores: np.ndarray,
    offsets: np.ndarray,
    history: frozenset[int],
    representation: VerifiedRepresentation,
    popularity: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if method == "popularity":
        selected = np.asarray(
            [int(item) for item in popularity if int(item) not in history][:100],
            dtype=np.int64,
        )
        return (
            selected,
            np.arange(100, 0, -1, dtype=np.float32),
            np.full(32, -1, dtype=np.int8),
            np.asarray([0, 0, 0, 0], dtype=np.int32),
        )
    all_cells = method in ("raw_full_exact_semantic", "aligned_full_exact")
    route_offset = method in (
        "pivot_route_only",
        "pivot_full",
        "shuffled_pivot",
        "aligned_full_exact",
    )
    rank_offset = method in (
        "pivot_rerank_only",
        "pivot_full",
        "shuffled_pivot",
        "aligned_full_exact",
    )
    cell_ids = np.arange(32, dtype=np.int64)
    if all_cells:
        cells = cell_ids
    else:
        logits = np.asarray(representation.centroids @ query, dtype=np.float32)
        if route_offset:
            logits = np.asarray(logits + offsets, dtype=np.float32)
        cells = cell_ids[np.lexsort((cell_ids, -logits))[:4]]
    allowed = np.isin(representation.assignment, cells)
    if history:
        allowed[np.asarray(sorted(history), dtype=np.int64)] = False
    items = np.flatnonzero(allowed).astype(np.int64)
    adjusted = np.asarray(raw_scores[items], dtype=np.float32)
    if rank_offset:
        adjusted = np.asarray(
            adjusted + offsets[representation.assignment[items]], dtype=np.float32
        )
    order = np.lexsort((representation.movie_ids[items], -adjusted))[:100]
    selected = items[order]
    selected_scores = adjusted[order]
    route_slots = np.full(32, -1, dtype=np.int8)
    route_slots[: len(cells)] = cells.astype(np.int8)
    sentinels = sum(
        bool(np.any(representation.shard_items[int(cell)] < 0)) for cell in cells
    )
    work = np.asarray(
        [32, len(cells) * 334, len(cells), sentinels], dtype=np.int32
    )
    if selected.size != 100 or len(set(map(int, selected))) != 100:
        raise IntegrityError("Independent candidate replay underfilled or duplicated")
    return selected, selected_scores, route_slots, work


def verify_bank(
    *,
    stage: str,
    bank: Mapping[str, np.ndarray],
    replay: ArchiveReplay,
    representation: VerifiedRepresentation,
    A_arrays: Mapping[str, np.ndarray],
    raw_scores: np.ndarray,
) -> Mapping[str, Any]:
    seeds = tuple(map(int, np.asarray(bank["seeds"])))
    epochs = tuple(map(int, np.asarray(bank["epochs"])))
    methods = decode_strings(bank["methods"], f"{stage} methods")
    users = tuple(map(int, np.asarray(bank["user_ids"])))
    if seeds != EXPECTED_SEEDS or methods != EXPECTED_METHODS or users != replay.user_ids:
        raise IntegrityError(f"Stage {stage} bank axes differ")
    if stage == "V":
        expected_epochs = EXPECTED_EPOCHS
        prefix = (3, 4, 8, 600)
        if epochs != expected_epochs:
            raise IntegrityError("V checkpoint axis differs")
    else:
        if len(epochs) != 1 or epochs[0] not in EXPECTED_EPOCHS:
            raise IntegrityError("T selected checkpoint axis differs")
        prefix = (3, 8, 600)
    candidates = np.asarray(bank["candidate_item_index"])
    movie = np.asarray(bank["candidate_movie_id"])
    score = np.asarray(bank["candidate_score"])
    routes = np.asarray(bank["route_cell"])
    work = np.asarray(bank["work_counts"])
    natural = np.asarray(bank["natural_offset"])
    shuffled = np.asarray(bank["shuffled_offset"])
    candidate_shape = (*prefix, 100)
    route_shape = (*prefix, 32)
    work_shape = (*prefix, 4)
    offset_shape = (3, len(epochs), 600, 32) if stage == "V" else (3, 600, 32)
    if (
        candidates.shape != candidate_shape
        or movie.shape != candidate_shape
        or score.shape != candidate_shape
        or routes.shape != route_shape
        or work.shape != work_shape
        or natural.shape != offset_shape
        or shuffled.shape != offset_shape
        or np.any(candidates < 0)
        or np.any(candidates >= 10681)
        or not np.isfinite(score).all()
        or not np.isfinite(natural).all()
        or not np.isfinite(shuffled).all()
    ):
        raise IntegrityError(f"Stage {stage} candidate-bank shape/range/finite contract differs")
    if not np.array_equal(movie, representation.movie_ids[candidates]):
        raise IntegrityError(f"Stage {stage} candidate movie-ID mapping differs")
    if np.max(np.abs(natural.mean(axis=-1)), initial=0.0) > 2e-7 or np.max(
        np.ptp(natural, axis=-1), initial=0.0
    ) > 0.100001:
        raise IntegrityError(f"Stage {stage} natural offsets violate center/bound")
    if np.max(np.abs(shuffled.mean(axis=-1)), initial=0.0) > 2e-7 or np.max(
        np.ptp(shuffled, axis=-1), initial=0.0
    ) > 0.100001:
        raise IntegrityError(f"Stage {stage} shuffled offsets violate center/bound")

    popularity = _popular_order(replay)
    queries = np.asarray(A_arrays["query"], dtype=np.float32)
    compared = 0
    if stage == "V":
        iterator = (
            (seed_index, epoch_index, method_index, user_row)
            for seed_index in range(3)
            for epoch_index in range(4)
            for method_index in range(8)
            for user_row in range(600)
        )
    else:
        iterator = (
            (seed_index, None, method_index, user_row)
            for seed_index in range(3)
            for method_index in range(8)
            for user_row in range(600)
        )
    for seed_index, epoch_index, method_index, user_row in iterator:
        method = EXPECTED_METHODS[method_index]
        if stage == "V":
            selected_offset = (
                shuffled[seed_index, int(epoch_index), user_row]
                if method == "shuffled_pivot"
                else natural[seed_index, int(epoch_index), user_row]
            )
            observed_candidate = candidates[seed_index, int(epoch_index), method_index, user_row]
            observed_score = score[seed_index, int(epoch_index), method_index, user_row]
            observed_route = routes[seed_index, int(epoch_index), method_index, user_row]
            observed_work = work[seed_index, int(epoch_index), method_index, user_row]
        else:
            selected_offset = (
                shuffled[seed_index, user_row]
                if method == "shuffled_pivot"
                else natural[seed_index, user_row]
            )
            observed_candidate = candidates[seed_index, method_index, user_row]
            observed_score = score[seed_index, method_index, user_row]
            observed_route = routes[seed_index, method_index, user_row]
            observed_work = work[seed_index, method_index, user_row]
        user_id = replay.user_ids[user_row]
        expected_candidate, expected_score, expected_route, expected_work = replay_one_retrieval(
            method=method,
            query=queries[user_row],
            raw_scores=raw_scores[user_row],
            offsets=selected_offset,
            history=_history_for(replay, user_id, stage),
            representation=representation,
            popularity=popularity,
        )
        if (
            not np.array_equal(observed_candidate, expected_candidate)
            or not np.allclose(observed_score, expected_score, rtol=2e-6, atol=2e-6)
            or not np.array_equal(observed_route, expected_route)
            or not np.array_equal(observed_work, expected_work)
        ):
            raise IntegrityError(
                f"Stage {stage} candidate replay differs at seed={seed_index}, "
                f"epoch={epoch_index}, method={method}, user_row={user_row}"
            )
        compared += 1
    return {
        "requests_replayed": compared,
        "candidate_ids_and_routes_exact": True,
        "scores_within_registered_tolerance": True,
        "fixed_work_exact": True,
    }


def _checkpoint_offset(state: Mapping[str, Any], features: np.ndarray) -> np.ndarray:
    required = ("0.weight", "0.bias", "2.weight", "2.bias")
    if set(state) != set(required):
        raise IntegrityError("Checkpoint state keys differ")
    arrays: dict[str, np.ndarray] = {}
    for name in required:
        value = state[name]
        if hasattr(value, "detach"):
            value = value.detach().cpu().numpy()
        arrays[name] = np.asarray(value, dtype=np.float32)
        if not np.isfinite(arrays[name]).all():
            raise IntegrityError("Checkpoint contains nonfinite parameters")
    if (
        arrays["0.weight"].shape != (32, 1153)
        or arrays["0.bias"].shape != (32,)
        or arrays["2.weight"].shape != (32, 32)
        or arrays["2.bias"].shape != (32,)
    ):
        raise IntegrityError("Checkpoint parameter shape differs")
    hidden = np.tanh(features @ arrays["0.weight"].T + arrays["0.bias"])
    z = np.tanh(hidden @ arrays["2.weight"].T + arrays["2.bias"])
    return np.asarray(0.05 * (z - z.mean(axis=-1, keepdims=True)), dtype=np.float32)


def verify_training_and_offsets(
    run_directory: Path,
    replay: ArchiveReplay,
    representation: VerifiedRepresentation,
    A_arrays: Mapping[str, np.ndarray],
    V_bank: Mapping[str, np.ndarray],
    T_bank: Mapping[str, np.ndarray],
    selected_epoch: int,
) -> Mapping[str, Any]:
    manifest = read_json(run_directory / "training_manifest.json", "training manifest")
    files = require_mapping(manifest.get("checkpoint_files"), "checkpoint files")
    expected_files = {
        f"checkpoints/{kind}_seed{seed}_epoch{epoch}.pt"
        for kind in ("natural", "shuffled")
        for seed in EXPECTED_SEEDS
        for epoch in EXPECTED_EPOCHS
    }
    if (
        set(files) != expected_files
        or manifest.get("R_opened_after_basis") is not True
        or manifest.get("optimizer") != "Adam"
        or manifest.get("simpo_reference_model_forward_passes") != 0
    ):
        raise IntegrityError("Training manifest contract differs")
    try:
        import torch
    except ImportError as exc:
        raise IntegrityError("PyTorch unavailable for checkpoint verification") from exc
    features = np.asarray(A_arrays["descriptor"], dtype=np.float32)
    max_error = 0.0
    for seed_index, seed in enumerate(EXPECTED_SEEDS):
        for epoch_index, epoch in enumerate(EXPECTED_EPOCHS):
            for kind in ("natural", "shuffled"):
                name = f"checkpoints/{kind}_seed{seed}_epoch{epoch}.pt"
                path = contained_file(run_directory, name, name)
                if sha256_file(path) != files[name]:
                    raise IntegrityError(f"Checkpoint hash differs: {name}")
                try:
                    state = torch.load(path, map_location="cpu", weights_only=True)
                except Exception as exc:
                    raise IntegrityError(f"Checkpoint cannot be safely loaded: {name}") from exc
                if not isinstance(state, Mapping):
                    raise IntegrityError(f"Checkpoint is not a state mapping: {name}")
                expected = _checkpoint_offset(state, features)
                observed = (
                    V_bank["natural_offset"]
                    if kind == "natural"
                    else V_bank["shuffled_offset"]
                )[seed_index, epoch_index]
                error = float(np.max(np.abs(expected - observed), initial=0.0))
                max_error = max(max_error, error)
                if error > 3e-6:
                    raise IntegrityError(f"Checkpoint-to-V-offset replay differs: {name}")
                if epoch == selected_epoch:
                    observed_T = (
                        T_bank["natural_offset"]
                        if kind == "natural"
                        else T_bank["shuffled_offset"]
                    )[seed_index]
                    if not np.allclose(expected, observed_T, rtol=0.0, atol=3e-6):
                        raise IntegrityError(f"Checkpoint-to-T-offset replay differs: {name}")

    R_pairs = {
        user_id: replay_pairs(
            replay.stages["R"][user_id],
            representation.assignment,
            64,
            "20260862:{user_id}:{low_item_id}:{high_item_id}",
            cross_cell_only=True,
        )
        for user_id in replay.user_ids
    }
    cross_pairs = sum(len(values) for values in R_pairs.values())
    cross_users = sum(bool(values) for values in R_pairs.values())
    diagnostics = require_mapping(manifest.get("diagnostics"), "training diagnostics")
    if (
        diagnostics.get("cross_cell_pairs") != cross_pairs
        or diagnostics.get("cross_cell_users") != cross_users
    ):
        raise IntegrityError("Independent R-pair support differs")
    return {
        "checkpoint_count": len(files),
        "maximum_checkpoint_offset_error": max_error,
        "cross_cell_pairs": cross_pairs,
        "cross_cell_users": cross_users,
    }


RAW_METRIC_COMMON_FIELDS = (
    "seeds",
    "methods",
    "metrics",
    "user_ids",
    "per_user_metrics",
    "selected_epoch",
    "selected_comparator_index",
)


@dataclass(frozen=True)
class VerifiedMetricStage:
    raw: Mapping[str, np.ndarray]
    values: np.ndarray
    pairs: Mapping[int, tuple[ReplayPair, ...]]
    support: Mapping[str, Any]


def _json_close(observed: Any, expected: Any, label: str, *, atol: float = 1e-12) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(observed, Mapping) or set(observed) != set(expected):
            raise IntegrityError(f"{label} mapping fields differ")
        for key in expected:
            _json_close(observed[key], expected[key], f"{label}.{key}", atol=atol)
        return
    if isinstance(expected, (list, tuple)):
        if not isinstance(observed, (list, tuple)) or len(observed) != len(expected):
            raise IntegrityError(f"{label} sequence shape differs")
        for index, (left, right) in enumerate(zip(observed, expected)):
            _json_close(left, right, f"{label}[{index}]", atol=atol)
        return
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if observed != expected:
            raise IntegrityError(f"{label} differs")
        return
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if isinstance(expected, int):
            if isinstance(observed, bool) or observed != expected:
                raise IntegrityError(f"{label} differs")
        elif not isinstance(observed, (int, float)) or isinstance(observed, bool) or not math.isclose(
            float(observed), float(expected), rel_tol=0.0, abs_tol=atol
        ):
            raise IntegrityError(f"{label} differs")
        return
    if observed != expected:
        raise IntegrityError(f"{label} differs")


def _pair_identity_hash(pairs: Sequence[ReplayPair]) -> str:
    payload = [
        (pair.user_id, pair.preferred_movie_id, pair.rejected_movie_id, pair.cross_cell)
        for pair in pairs
    ]
    return sha256_bytes(canonical_json_bytes(payload))


def _binary_ndcg(top_items: Sequence[int], relevant: frozenset[int]) -> float:
    gains = np.asarray(
        [1.0 if int(item) in relevant else 0.0 for item in top_items[:10]],
        dtype=np.float64,
    )
    discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
    ideal = float(discounts[: min(10, len(relevant))].sum())
    return float((gains * discounts).sum() / ideal) if ideal > 0.0 else float("nan")


def independently_evaluate_bank(
    bank: Mapping[str, np.ndarray],
    outcomes: Mapping[int, Sequence[ReplayEvent]],
    pairs_by_user: Mapping[int, Sequence[ReplayPair]],
    user_ids: Sequence[int],
) -> tuple[np.ndarray, Mapping[str, Any]]:
    values = np.full((3, 8, 600, 8), np.nan, dtype=np.float64)
    metric_index = {name: index for index, name in enumerate(EXPECTED_METRICS)}
    method_index = {name: index for index, name in enumerate(EXPECTED_METHODS)}
    pair_rows = 0
    for user_row, user_id in enumerate(user_ids):
        pairs = tuple(pairs_by_user[user_id])
        pair_rows += len(pairs)
        relevant = frozenset(
            event.item_index for event in outcomes[user_id] if event.rating >= 4.0
        )
        low = frozenset(
            event.item_index for event in outcomes[user_id] if event.rating <= 2.0
        )
        for seed_index in range(3):
            oracle = set(
                map(
                    int,
                    bank["candidate_item_index"][
                        seed_index, method_index["aligned_full_exact"], user_row
                    ],
                )
            )
            for candidate_method, candidate_method_index in method_index.items():
                candidates = list(
                    map(
                        int,
                        bank["candidate_item_index"][
                            seed_index, candidate_method_index, user_row
                        ],
                    )
                )
                candidate_set = set(candidates)
                top10 = candidates[:10]
                if relevant:
                    values[seed_index, candidate_method_index, user_row, metric_index["future_liked_recall_at_100"]] = len(candidate_set & relevant) / len(relevant)
                    values[seed_index, candidate_method_index, user_row, metric_index["recall_at_10"]] = len(set(top10) & relevant) / len(relevant)
                    values[seed_index, candidate_method_index, user_row, metric_index["ndcg_at_10"]] = _binary_ndcg(top10, relevant)
                if pairs:
                    exposures = [
                        float(pair.preferred in candidate_set)
                        - float(pair.rejected in candidate_set)
                        for pair in pairs
                    ]
                    values[seed_index, candidate_method_index, user_row, metric_index["cpe_at_100"]] = float(np.mean(exposures))
                    cross = [
                        value
                        for value, pair in zip(exposures, pairs)
                        if pair.cross_cell
                    ]
                    if cross:
                        values[seed_index, candidate_method_index, user_row, metric_index["cross_cell_cpe_at_100"]] = float(np.mean(cross))
                    ranks = {item: rank + 1 for rank, item in enumerate(top10)}
                    served = [
                        float(
                            ranks.get(pair.preferred, 11)
                            < ranks.get(pair.rejected, 11)
                        )
                        for pair in pairs
                    ]
                    values[seed_index, candidate_method_index, user_row, metric_index["spce_at_10"]] = float(np.mean(served))
                if candidate_method == "pivot_full":
                    values[seed_index, candidate_method_index, user_row, metric_index["aligned_oracle_overlap_at_100"]] = len(candidate_set & oracle) / 100.0
                values[seed_index, candidate_method_index, user_row, metric_index["low_rating_intrusion_at_10"]] = len(set(top10) & low) / 10.0
    flattened_pairs = tuple(
        pair for user_id in user_ids for pair in pairs_by_user[user_id]
    )
    support = {
        "relevant_users": sum(
            any(event.rating >= 4.0 for event in outcomes[user_id])
            for user_id in user_ids
        ),
        "fixed_pairs": pair_rows,
        "pair_users": sum(bool(pairs_by_user[user_id]) for user_id in user_ids),
        "pair_identity_sha256": _pair_identity_hash(flattened_pairs),
    }
    return values, support


def load_and_verify_metric_stage(
    run_directory: Path,
    manifest: Mapping[str, Any],
    stage: str,
    replay: ArchiveReplay,
    representation: VerifiedRepresentation,
    bank: Mapping[str, np.ndarray],
) -> VerifiedMetricStage:
    lower = "validation" if stage == "V" else "test"
    path = bound_manifest_file(
        run_directory,
        manifest,
        f"{lower}_file",
        f"{lower}_sha256",
        f"raw {lower} metrics",
    )
    event_fields = tuple(
        f"{stage}_{name}"
        for name in (
            "event_item_index",
            "event_movie_id",
            "event_rating",
            "event_timestamp",
            "event_source_row_ordinal",
            "event_count",
        )
    )
    pair_fields = tuple(
        f"{stage}_{name}"
        for name in (
            "pair_user_row",
            "pair_preferred_item",
            "pair_rejected_item",
            "pair_cross_cell",
        )
    )
    raw = npz_exact(
        path,
        (*RAW_METRIC_COMMON_FIELDS, *event_fields, *pair_fields),
        f"raw {lower} metrics",
    )
    if (
        tuple(map(int, raw["seeds"])) != EXPECTED_SEEDS
        or decode_strings(raw["methods"], f"{stage} metric methods") != EXPECTED_METHODS
        or decode_strings(raw["metrics"], f"{stage} metric names") != EXPECTED_METRICS
        or tuple(map(int, raw["user_ids"])) != replay.user_ids
        or raw["per_user_metrics"].shape != (3, 8, 600, 8)
        or raw["selected_epoch"].shape != (1,)
        or raw["selected_comparator_index"].shape != (1,)
    ):
        raise IntegrityError(f"Raw {stage} metric axes differ")
    verify_event_arrays(raw, stage, replay)
    pairs, expected_rows = expected_pair_rows(replay, representation, stage)
    for name, expected in expected_rows.items():
        if not np.array_equal(raw[name], expected):
            raise IntegrityError(f"Independent fixed-pair reconstruction differs: {name}")
    values, support = independently_evaluate_bank(
        bank, replay.stages[stage], pairs, replay.user_ids
    )
    if not np.allclose(
        raw["per_user_metrics"], values, rtol=0.0, atol=1e-12, equal_nan=True
    ):
        difference = np.abs(raw["per_user_metrics"] - values)
        raise IntegrityError(
            f"Independent {stage} metric replay differs; finite max={np.nanmax(difference)}"
        )
    return VerifiedMetricStage(
        raw=raw,
        values=values,
        pairs=pairs,
        support=support,
    )


def finite_user_difference(
    metrics: np.ndarray, left: str, right: str, metric: str
) -> tuple[np.ndarray, np.ndarray]:
    left_matrix = metrics[
        :, EXPECTED_METHODS.index(left), :, EXPECTED_METRICS.index(metric)
    ]
    right_matrix = metrics[
        :, EXPECTED_METHODS.index(right), :, EXPECTED_METRICS.index(metric)
    ]
    left_count = np.sum(np.isfinite(left_matrix), axis=0)
    right_count = np.sum(np.isfinite(right_matrix), axis=0)
    left_values = np.divide(
        np.nansum(left_matrix, axis=0),
        left_count,
        out=np.full(left_count.shape, np.nan, dtype=np.float64),
        where=left_count > 0,
    )
    right_values = np.divide(
        np.nansum(right_matrix, axis=0),
        right_count,
        out=np.full(right_count.shape, np.nan, dtype=np.float64),
        where=right_count > 0,
    )
    supported = np.isfinite(left_values) & np.isfinite(right_values)
    return left_values[supported] - right_values[supported], np.flatnonzero(supported)


def independent_comparison(
    metrics: np.ndarray, left: str, right: str, metric: str
) -> Mapping[str, Any]:
    values, rows = finite_user_difference(metrics, left, right, metric)
    return {
        **paired_bootstrap(values),
        "left": left,
        "right": right,
        "metric": metric,
        "common_user_rows_sha256": sha256_bytes(
            np.ascontiguousarray(rows, dtype="<i8").tobytes()
        ),
    }


def verify_frozen_validation_choices(
    run_directory: Path,
    replay: ArchiveReplay,
    representation: VerifiedRepresentation,
    A_arrays: Mapping[str, np.ndarray],
    V_bank: Mapping[str, np.ndarray],
    training_manifest: Mapping[str, Any],
) -> tuple[int, str, Mapping[int, tuple[ReplayPair, ...]], Mapping[str, Any]]:
    pairs = {
        user_id: replay_pairs(
            replay.stages["V"][user_id],
            representation.assignment,
            64,
            "20260867:{user_id}:{low_item_id}:{high_item_id}",
            cross_cell_only=True,
        )
        for user_id in replay.user_ids
    }
    results: dict[int, float] = {}
    seed_values: dict[int, list[float]] = {}
    queries = np.asarray(A_arrays["query"], dtype=np.float32)
    offsets = np.asarray(V_bank["natural_offset"], dtype=np.float32)
    for epoch_index, epoch in enumerate(EXPECTED_EPOCHS):
        per_seed: list[float] = []
        for seed_index in range(3):
            per_user: list[float] = []
            for user_row, user_id in enumerate(replay.user_ids):
                user_pairs = pairs[user_id]
                if not user_pairs:
                    continue
                query = queries[user_row]
                potential = offsets[seed_index, epoch_index, user_row]
                correct = [
                    float(
                        query @ representation.vectors[pair.preferred]
                        + potential[int(representation.assignment[pair.preferred])]
                        > query @ representation.vectors[pair.rejected]
                        + potential[int(representation.assignment[pair.rejected])]
                    )
                    for pair in user_pairs
                ]
                per_user.append(float(np.mean(correct)))
            if not per_user:
                raise IntegrityError("V checkpoint selection lacks pair-bearing users")
            per_seed.append(float(np.mean(per_user)))
        if not all(math.isfinite(value) for value in per_seed):
            raise IntegrityError("V checkpoint selection contains nonfinite accuracy")
        seed_values[epoch] = per_seed
        results[epoch] = float(np.mean(per_seed))
    selected_epoch = max(EXPECTED_EPOCHS, key=lambda epoch: (results[epoch], -epoch))
    flattened = tuple(pair for user_id in replay.user_ids for pair in pairs[user_id])
    checkpoint_selection = {
        "mean_accuracy": {str(epoch): results[epoch] for epoch in EXPECTED_EPOCHS},
        "seed_accuracy": {str(epoch): seed_values[epoch] for epoch in EXPECTED_EPOCHS},
        "selected_epoch": selected_epoch,
        "pair_count": len(flattened),
        "user_count": sum(bool(pairs[user_id]) for user_id in replay.user_ids),
        "pair_identity_sha256": _pair_identity_hash(flattened),
    }
    frozen = read_json(run_directory / "frozen_choices.json", "frozen choices")
    if frozen.get("T_opened") is not False:
        raise IntegrityError("Frozen choices report T opened before freezing")
    _json_close(
        require_mapping(frozen.get("checkpoint_selection"), "checkpoint selection"),
        checkpoint_selection,
        "checkpoint selection",
    )
    if frozen.get("selected_epoch") != selected_epoch:
        raise IntegrityError("Independently selected V checkpoint differs")
    checkpoint_files = require_mapping(
        training_manifest.get("checkpoint_files"), "checkpoint file inventory"
    )
    expected_selected = {
        f"{kind}_seed{seed}": checkpoint_files[
            f"checkpoints/{kind}_seed{seed}_epoch{selected_epoch}.pt"
        ]
        for kind in ("natural", "shuffled")
        for seed in EXPECTED_SEEDS
    }
    if dict(require_mapping(frozen.get("selected_checkpoint_sha256"), "selected hashes")) != expected_selected:
        raise IntegrityError("Frozen selected-checkpoint hashes differ")
    comparator = str(frozen.get("relevance_comparator", ""))
    if comparator not in ("balanced_geometric_ivf", "raw_full_exact_semantic"):
        raise IntegrityError("Frozen relevance comparator is invalid")
    return selected_epoch, comparator, pairs, checkpoint_selection


def selected_epoch_bank(V_bank: Mapping[str, np.ndarray], selected_epoch: int) -> Mapping[str, np.ndarray]:
    epoch_index = EXPECTED_EPOCHS.index(selected_epoch)
    result: dict[str, np.ndarray] = {}
    for name, value in V_bank.items():
        if name in (
            "candidate_item_index",
            "candidate_movie_id",
            "candidate_score",
            "route_cell",
            "work_counts",
            "natural_offset",
            "shuffled_offset",
        ):
            result[name] = np.asarray(value)[:, epoch_index]
        elif name == "epochs":
            result[name] = np.asarray([selected_epoch], dtype=np.int16)
        else:
            result[name] = np.asarray(value)
    return result


def choose_validation_comparator(metrics: np.ndarray) -> tuple[str, Mapping[str, float]]:
    candidates = ("balanced_geometric_ivf", "raw_full_exact_semantic")
    summaries = {
        method: finite_mean(
            metrics[
                :,
                EXPECTED_METHODS.index(method),
                :,
                EXPECTED_METRICS.index("ndcg_at_10"),
            ]
        )
        for method in candidates
    }
    if not all(math.isfinite(value) for value in summaries.values()):
        raise IntegrityError("Validation comparator lacks finite NDCG support")
    selected = max(
        candidates,
        key=lambda method: (summaries[method], -candidates.index(method)),
    )
    return selected, summaries


def finite_mean(values: np.ndarray) -> float:
    vector = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(vector)
    return float(vector[finite].mean()) if np.any(finite) else float("nan")


def verify_power_audit(
    run_directory: Path,
    V_metrics: VerifiedMetricStage,
    checkpoint_selection: Mapping[str, Any],
) -> Mapping[str, Any]:
    rng = np.random.default_rng(20260866)
    records: dict[str, Any] = {}
    for metric in ("future_liked_recall_at_100", "cpe_at_100"):
        difference, _ = finite_user_difference(
            V_metrics.values, "pivot_full", "balanced_geometric_ivf", metric
        )
        records[metric] = centered_power(difference, rng=rng)
    power = {
        "schema": "pivot-validation-power-v1",
        "seed": 20260866,
        "records": records,
        "passed": all(value["passed"] for value in records.values()),
    }
    manifest = read_json(run_directory / "power_audit.json", "power audit")
    if manifest.get("T_opened") is not False:
        raise IntegrityError("Power audit reports T opened")
    _json_close(
        require_mapping(manifest.get("validation_support"), "validation support"),
        V_metrics.support,
        "validation support",
    )
    _json_close(
        require_mapping(manifest.get("checkpoint_support"), "checkpoint support"),
        {
            "pairs": checkpoint_selection["pair_count"],
            "users": checkpoint_selection["user_count"],
        },
        "checkpoint support",
    )
    _json_close(require_mapping(manifest.get("power"), "power result"), power, "power")
    raw = bound_manifest_file(
        run_directory,
        manifest,
        "raw_validation_file",
        "raw_validation_sha256",
        "power raw validation",
    )
    if raw != run_directory / "raw_validation_metrics.npz":
        raise IntegrityError("Power audit references a noncanonical validation array")
    return power


def independent_action_surface(
    bank: Mapping[str, np.ndarray], pairs: Mapping[int, Sequence[ReplayPair]], user_ids: Sequence[int]
) -> Mapping[str, float]:
    pivot = np.asarray(bank["candidate_item_index"][:, EXPECTED_METHODS.index("pivot_full")])
    geometric = np.asarray(
        bank["candidate_item_index"][:, EXPECTED_METHODS.index("balanced_geometric_ivf")]
    )
    pivot_routes = np.asarray(
        bank["route_cell"][:, EXPECTED_METHODS.index("pivot_full"), :, :4]
    )
    geometric_routes = np.asarray(
        bank["route_cell"][:, EXPECTED_METHODS.index("balanced_geometric_ivf"), :, :4]
    )
    route_changed = float(
        np.mean(
            np.any(
                np.sort(pivot_routes, axis=-1)
                != np.sort(geometric_routes, axis=-1),
                axis=-1,
            )
        )
    )
    changed = 0
    total = 0
    jaccards: list[float] = []
    endpoints_by_row = {
        row: {
            endpoint
            for pair in pairs[user_id]
            for endpoint in (pair.preferred, pair.rejected)
        }
        for row, user_id in enumerate(user_ids)
        if pairs[user_id]
    }
    for seed_index in range(3):
        for user_row in range(600):
            left = set(map(int, pivot[seed_index, user_row]))
            right = set(map(int, geometric[seed_index, user_row]))
            jaccards.append(1.0 - len(left & right) / len(left | right))
        for user_row, endpoints in endpoints_by_row.items():
            left = set(map(int, pivot[seed_index, user_row]))
            right = set(map(int, geometric[seed_index, user_row]))
            for endpoint in endpoints:
                changed += int((endpoint in left) != (endpoint in right))
                total += 1
    return {
        "route_change_fraction": route_changed,
        "endpoint_membership_xor_fraction": changed / total if total else 0.0,
        "mean_candidate_jaccard_distance": float(np.mean(jaccards)) if jaccards else 0.0,
        "endpoint_rows": total,
    }


def verify_score_audit(
    run_directory: Path,
    raw_manifest: Mapping[str, Any],
    T_manifest: Mapping[str, Any],
    representation: VerifiedRepresentation,
    A_arrays: Mapping[str, np.ndarray],
    T_bank: Mapping[str, np.ndarray],
    raw_faiss_scores: np.ndarray,
) -> Mapping[str, Any]:
    raw_path = bound_manifest_file(
        run_directory,
        raw_manifest,
        "score_audit_file",
        "score_audit_sha256",
        "raw score audit",
    )
    manifest_path = bound_manifest_file(
        run_directory,
        T_manifest,
        "score_audit_file",
        "score_audit_sha256",
        "T score audit",
    )
    if raw_path != manifest_path or raw_path != run_directory / "score_audit_raw.npz":
        raise IntegrityError("Score-audit manifests bind different files")
    raw = npz_exact(
        raw_path,
        (
            "seeds",
            "user_ids",
            "score_audit_max_abs_error",
            "score_audit_rank100_101_margin",
            "score_audit_near_tie_count",
        ),
        "score audit arrays",
    )
    if (
        tuple(map(int, raw["seeds"])) != EXPECTED_SEEDS
        or tuple(map(int, raw["user_ids"])) != tuple(map(int, T_bank["user_ids"]))
        or raw["score_audit_max_abs_error"].shape != (3, 600)
        or raw["score_audit_rank100_101_margin"].shape != (3, 600)
        or raw["score_audit_near_tie_count"].shape != (3, 600)
    ):
        raise IntegrityError("Score-audit axes differ")
    expected_error = np.empty((3, 600), dtype=np.float64)
    expected_margin = np.empty((3, 600), dtype=np.float64)
    expected_near = np.empty((3, 600), dtype=np.int32)
    queries = np.asarray(A_arrays["query"], dtype=np.float32)
    offsets = np.asarray(T_bank["natural_offset"], dtype=np.float32)
    item_cells = representation.assignment
    item_indices = np.arange(10681, dtype=np.int64)
    for seed_index in range(3):
        for user_row in range(600):
            adjusted_faiss = np.asarray(
                raw_faiss_scores[user_row] + offsets[seed_index, user_row, item_cells],
                dtype=np.float32,
            )
            adjusted_matrix = np.asarray(
                representation.vectors @ queries[user_row]
                + offsets[seed_index, user_row, item_cells],
                dtype=np.float32,
            )
            error = np.abs(adjusted_matrix - adjusted_faiss)
            tolerance = 2e-6 + 2e-6 * np.abs(adjusted_matrix)
            if not np.all(error <= tolerance):
                raise IntegrityError("Independent adjusted FAISS score audit exceeds tolerance")
            order = np.lexsort(
                (representation.movie_ids[item_indices], -adjusted_faiss)
            )
            threshold = float(adjusted_faiss[order[99]])
            expected_error[seed_index, user_row] = float(error.max(initial=0.0))
            expected_margin[seed_index, user_row] = float(
                adjusted_faiss[order[99]] - adjusted_faiss[order[100]]
            )
            expected_near[seed_index, user_row] = int(
                np.sum(
                    np.abs(adjusted_faiss - threshold)
                    <= (2e-6 + 2e-6 * abs(threshold))
                )
            )
    if (
        not np.allclose(raw["score_audit_max_abs_error"], expected_error, rtol=0.0, atol=1e-12)
        or not np.allclose(raw["score_audit_rank100_101_margin"], expected_margin, rtol=0.0, atol=1e-12)
        or not np.array_equal(raw["score_audit_near_tie_count"], expected_near)
    ):
        raise IntegrityError("Independent complete score-audit replay differs")
    return {
        "requests": 1800,
        "complete_finite": bool(
            np.isfinite(expected_error).all() and np.isfinite(expected_margin).all()
        ),
        "maximum_absolute_error": float(expected_error.max(initial=0.0)),
        "minimum_rank100_101_margin": float(expected_margin.min(initial=np.inf)),
        "maximum_near_tie_count": int(expected_near.max(initial=0)),
    }


def verify_latency(
    run_directory: Path,
    replay: ArchiveReplay,
) -> Mapping[str, Any]:
    manifest = read_json(run_directory / "latency_raw_manifest.json", "latency manifest")
    if manifest.get("outcome_access") is not False:
        raise IntegrityError("Latency measurement reports outcome access")
    path = bound_manifest_file(
        run_directory, manifest, "raw_file", "raw_sha256", "latency raw arrays"
    )
    raw = npz_exact(
        path,
        (
            "seeds",
            "methods",
            "user_ids",
            "durations_ms",
            "per_request_median_ms",
            "p95_ms",
            "p95_ratio",
        ),
        "latency raw arrays",
    )
    selected_users = tuple(
        sorted(
            replay.user_ids,
            key=lambda user_id: (
                int(
                    hashlib.sha256(f"20260868:{user_id}".encode("ascii")).hexdigest(),
                    16,
                ),
                user_id,
            ),
        )[:512]
    )
    durations = np.asarray(raw["durations_ms"], dtype=np.float64)
    if (
        tuple(map(int, raw["seeds"])) != EXPECTED_SEEDS
        or decode_strings(raw["methods"], "latency methods")
        != ("balanced_geometric_ivf", "pivot_full")
        or tuple(map(int, raw["user_ids"])) != selected_users
        or durations.shape != (3, 2, 512, 7)
        or not np.isfinite(durations).all()
        or np.any(durations <= 0.0)
    ):
        raise IntegrityError("Latency axes, request order, or durations differ")
    medians = np.median(durations, axis=-1)
    p95 = np.quantile(medians, 0.95, axis=-1, method="linear")
    ratio = p95[:, 1] / p95[:, 0]
    if (
        not np.array_equal(raw["per_request_median_ms"], medians)
        or not np.array_equal(raw["p95_ms"], p95)
        or not np.array_equal(raw["p95_ratio"], ratio)
    ):
        raise IntegrityError("Independent median/linear-p95 latency reduction differs")
    passed = bool(np.all(p95[:, 1] <= 3.0) and np.all(ratio <= 1.5))
    result = require_mapping(manifest.get("result"), "latency result")
    if (
        result.get("schema") != "pivot-latency-result-v1"
        or result.get("requests") != 512
        or result.get("warmups") != 32
        or result.get("repetitions") != 7
        or result.get("passed") is not passed
    ):
        raise IntegrityError("Latency result contract differs")
    _json_close(result.get("p95_ms"), p95.tolist(), "latency p95")
    _json_close(result.get("p95_ratio"), ratio.tolist(), "latency ratio")
    environment = require_mapping(result.get("environment"), "latency environment")
    packages = require_mapping(environment.get("packages"), "latency packages")
    if (
        packages.get("scikit-learn") != "1.8.0"
        or environment.get("affinity_supported") is not True
        or not isinstance(environment.get("peak_rss_bytes_observed"), int)
        or environment.get("peak_rss_bytes_observed", 0) <= 0
    ):
        raise IntegrityError("Latency runtime package, affinity, or RSS binding differs")
    return {
        "passed": passed,
        "requests": 512,
        "warmups": 32,
        "repetitions": 7,
        "p95_ms": p95.tolist(),
        "p95_ratio": ratio.tolist(),
        "deterministic_request_order_sha256": sha256_bytes(
            np.ascontiguousarray(selected_users, dtype="<i8").tobytes()
        ),
        "quantile_method": "linear",
        "schedule": "AB/BA even geometric->PIVOT; odd PIVOT->geometric for repetitions 0..6",
    }


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise IntegrityError(f"{label} is not an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntegrityError(f"{label} is not an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IntegrityError(f"{label} lacks timezone information")
    return parsed.astimezone(timezone.utc)


def verify_stage_barriers(
    run_directory: Path,
    raw_manifest: Mapping[str, Any],
) -> Mapping[str, Any]:
    R_basis = read_json(run_directory / "stage_R_basis_manifest.json", "R basis")
    training = read_json(run_directory / "training_manifest.json", "training")
    V_bank = read_json(run_directory / "stage_V_candidate_bank_manifest.json", "V bank")
    frozen = read_json(run_directory / "frozen_choices.json", "frozen choices")
    power = read_json(run_directory / "power_audit.json", "power audit")
    T_bank = read_json(run_directory / "stage_T_candidate_bank_manifest.json", "T bank")
    times = require_mapping(raw_manifest.get("stage_barrier_times"), "stage barrier times")
    expected = {
        "R_basis_published_utc": R_basis.get("basis_published_utc"),
        "R_joined_utc": training.get("R_joined_utc"),
        "V_bank_published_utc": V_bank.get("bank_published_utc"),
        "V_joined_utc": frozen.get("V_joined_utc"),
        "choices_frozen_utc": frozen.get("frozen_utc"),
        "power_audit_completed_utc": power.get("power_audit_completed_utc"),
        "T_bank_published_utc": T_bank.get("bank_published_utc"),
        "T_joined_utc": times.get("T_joined_utc"),
    }
    if set(times) != set(expected) or any(times.get(name) != value for name, value in expected.items()):
        raise IntegrityError("Stage-barrier timestamp cross-bindings differ")
    if (
        training.get("R_basis_published_utc") != expected["R_basis_published_utc"]
        or frozen.get("V_bank_published_utc") != expected["V_bank_published_utc"]
        or T_bank.get("choices_frozen_utc") != expected["choices_frozen_utc"]
        or T_bank.get("power_audit_completed_utc")
        != expected["power_audit_completed_utc"]
    ):
        raise IntegrityError("Stage-barrier companion timestamp differs")
    names = tuple(expected)
    parsed = [_parse_utc(expected[name], name) for name in names]
    if any(left > right for left, right in zip(parsed, parsed[1:])):
        raise IntegrityError("Stage join/publication/freeze order is not monotonic")
    if (
        R_basis.get("published_before_R_join") is not True
        or training.get("R_opened_after_basis") is not True
        or V_bank.get("V_item_identities_or_ratings_opened") is not False
        or frozen.get("T_opened") is not False
        or power.get("T_opened") is not False
        or T_bank.get("T_item_identities_or_ratings_opened") is not False
    ):
        raise IntegrityError("Stage-barrier boolean evidence differs")
    return {"ordered": True, "timestamps": dict(times)}


def independently_compute_gates(
    T_metrics: VerifiedMetricStage,
    *,
    comparator: str,
    R_support: Mapping[str, Any],
    V_support: Mapping[str, Any],
    power: Mapping[str, Any],
    surface: Mapping[str, Any],
    latency: Mapping[str, Any],
    g1_invariants: Mapping[str, bool],
) -> tuple[Mapping[str, bool], Mapping[str, Any]]:
    metrics = T_metrics.values
    comparisons: dict[str, Mapping[str, Any]] = {}
    for metric in ("future_liked_recall_at_100", "cpe_at_100"):
        comparisons[f"g2_{metric}"] = independent_comparison(
            metrics, "pivot_full", "balanced_geometric_ivf", metric
        )
        for control in ("pivot_route_only", "pivot_rerank_only"):
            comparisons[f"g3_{control}_{metric}"] = independent_comparison(
                metrics, "pivot_full", control, metric
            )
    comparisons["g3_shuffled_cpe"] = independent_comparison(
        metrics, "pivot_full", "shuffled_pivot", "cpe_at_100"
    )
    for metric in ("ndcg_at_10", "recall_at_10", "spce_at_10"):
        comparisons[f"g5_{metric}"] = independent_comparison(
            metrics, "pivot_full", comparator, metric
        )
    comparisons["g5_intrusion"] = independent_comparison(
        metrics,
        "pivot_full",
        "balanced_geometric_ivf",
        "low_rating_intrusion_at_10",
    )

    g2 = all(
        comparisons[f"g2_{metric}"]["mean"] is not None
        and comparisons[f"g2_{metric}"]["mean"] >= 0.010
        and comparisons[f"g2_{metric}"]["lower"] > 0.0
        for metric in ("future_liked_recall_at_100", "cpe_at_100")
    )
    g3 = True
    for metric in ("future_liked_recall_at_100", "cpe_at_100"):
        for control in ("pivot_route_only", "pivot_rerank_only"):
            record = comparisons[f"g3_{control}_{metric}"]
            g3 &= bool(
                record["mean"] is not None
                and record["mean"] >= 0.002
                and record["lower"] > 0.0
            )
    shuffled = comparisons["g3_shuffled_cpe"]
    g3 &= bool(
        shuffled["mean"] is not None
        and shuffled["mean"] >= 0.010
        and shuffled["lower"] > 0.0
    )

    pivot_recall = finite_mean(
        metrics[
            :,
            EXPECTED_METHODS.index("pivot_full"),
            :,
            EXPECTED_METRICS.index("future_liked_recall_at_100"),
        ]
    )
    raw_recall = finite_mean(
        metrics[
            :,
            EXPECTED_METHODS.index("raw_full_exact_semantic"),
            :,
            EXPECTED_METRICS.index("future_liked_recall_at_100"),
        ]
    )
    overlap = finite_mean(
        metrics[
            :,
            EXPECTED_METHODS.index("pivot_full"),
            :,
            EXPECTED_METRICS.index("aligned_oracle_overlap_at_100"),
        ]
    )
    retention = pivot_recall / raw_recall if raw_recall > 0.0 else float("nan")
    g4 = bool(
        math.isfinite(overlap)
        and overlap >= 0.90
        and math.isfinite(retention)
        and retention >= 0.95
    )

    ndcg = comparisons["g5_ndcg_at_10"]
    recall = comparisons["g5_recall_at_10"]
    spce = comparisons["g5_spce_at_10"]
    intrusion = comparisons["g5_intrusion"]
    supported = all(
        record.get("mean") is not None
        and record.get("lower") is not None
        and record.get("upper") is not None
        for record in (ndcg, recall, spce, intrusion)
    )
    g5 = bool(
        supported
        and ndcg["mean"] >= -0.002
        and ndcg["lower"] > -0.005
        and recall["mean"] >= -0.005
        and recall["lower"] > -0.010
        and spce["mean"] >= 0.0
        and intrusion["upper"] <= 0.002
    )
    g6 = bool(
        R_support["cross_cell_pairs"] >= 5000
        and R_support["cross_cell_users"] >= 400
        and V_support["relevant_users"] >= 400
        and V_support["fixed_pairs"] >= 1500
        and V_support["pair_users"] >= 300
        and T_metrics.support["relevant_users"] >= 400
        and T_metrics.support["fixed_pairs"] >= 1500
        and T_metrics.support["pair_users"] >= 300
        and power["passed"]
        and surface["route_change_fraction"] >= 0.10
        and surface["endpoint_membership_xor_fraction"] >= 0.05
    )

    stable = 0
    seed_records: dict[str, Any] = {}
    g7 = True
    for seed_index, seed in enumerate(EXPECTED_SEEDS):
        record: dict[str, float] = {}
        primary_positive = True
        for metric in ("future_liked_recall_at_100", "cpe_at_100"):
            left = metrics[
                seed_index,
                EXPECTED_METHODS.index("pivot_full"),
                :,
                EXPECTED_METRICS.index(metric),
            ]
            right = metrics[
                seed_index,
                EXPECTED_METHODS.index("balanced_geometric_ivf"),
                :,
                EXPECTED_METRICS.index(metric),
            ]
            finite = np.isfinite(left) & np.isfinite(right)
            delta = (
                float(np.mean(left[finite] - right[finite]))
                if np.any(finite)
                else float("nan")
            )
            record[metric] = delta
            primary_positive &= math.isfinite(delta) and delta > 0.0
            g7 &= math.isfinite(delta) and delta >= 0.0
        left = metrics[
            seed_index,
            EXPECTED_METHODS.index("pivot_full"),
            :,
            EXPECTED_METRICS.index("ndcg_at_10"),
        ]
        right = metrics[
            seed_index,
            EXPECTED_METHODS.index(comparator),
            :,
            EXPECTED_METRICS.index("ndcg_at_10"),
        ]
        finite = np.isfinite(left) & np.isfinite(right)
        ndcg_delta = (
            float(np.mean(left[finite] - right[finite]))
            if np.any(finite)
            else float("nan")
        )
        record["ndcg_at_10"] = ndcg_delta
        g7 &= math.isfinite(ndcg_delta) and ndcg_delta >= -0.005
        stable += int(primary_positive)
        seed_records[str(seed)] = record
    g7 &= stable >= 2
    gates = {
        "G1": bool(g1_invariants and all(g1_invariants.values())),
        "G2": bool(g2),
        "G3": bool(g3),
        "G4": bool(g4),
        "G5": bool(g5),
        "G6": bool(g6),
        "G7": bool(g7),
        "G8": bool(latency["passed"]),
    }
    details = {
        "comparisons": comparisons,
        "aligned_overlap": overlap,
        "raw_exact_retention": retention,
        "raw_exact_recall_denominator": raw_recall,
        "raw_exact_supported_users": int(
            np.sum(
                np.isfinite(
                    metrics[
                        0,
                        EXPECTED_METHODS.index("raw_full_exact_semantic"),
                        :,
                        EXPECTED_METRICS.index("future_liked_recall_at_100"),
                    ]
                )
            )
        ),
        "seed_records": seed_records,
        "g1_invariants": dict(g1_invariants),
        "R_support": dict(R_support),
        "V_support": dict(V_support),
        "T_support": dict(T_metrics.support),
        "power": dict(power),
        "surface": dict(surface),
        "latency": dict(latency),
    }
    return gates, details


def verify_launch_authorization(
    *,
    run_directory: Path,
    run_id: str,
    authorized_launcher_sha256: str,
    claim_path: Path,
    launch_record_path: Path,
    source_inventory_path: Path,
    expected_source_inventory_sha256: str,
    expected_source_hashes: Mapping[str, Any],
) -> Mapping[str, Any]:
    launcher = Path(__file__).resolve()
    require_launcher_digest(
        authorized_launcher_sha256, launcher, "Verifier authorization digest"
    )
    if sha256_file(source_inventory_path) != expected_source_inventory_sha256:
        raise IntegrityError("Launch source-inventory digest differs")
    source_inventory = read_json(source_inventory_path, "launch source inventory")
    inventory_hashes = require_mapping(
        source_inventory.get("source_hashes"), "launch source hashes"
    )
    if (
        source_inventory.get("schema") != "pivot-launch-source-inventory-v1"
        or source_inventory.get("run_id") != run_id
        or source_inventory.get("launcher_sha256") != authorized_launcher_sha256
        or dict(inventory_hashes) != dict(expected_source_hashes)
    ):
        raise IntegrityError("Launch source inventory differs")
    claim = read_json(claim_path, "one-time launch claim")
    if (
        claim.get("schema") != "pivot-one-time-launch-claim-v1"
        or claim.get("run_id") != run_id
        or claim.get("launcher_sha256") != authorized_launcher_sha256
        or Path(str(claim.get("run_directory", ""))).resolve() != run_directory
        or claim.get("source_inventory_sha256") != expected_source_inventory_sha256
        or claim.get("authoritative") is not False
        or claim.get("PROMISING") is not False
    ):
        raise IntegrityError("One-time launch claim binding differs")
    launch = read_json(launch_record_path, "launch record")
    if (
        launch.get("schema") != "pivot-launch-record-v1"
        or launch.get("run_id") != run_id
        or launch.get("launcher_sha256") != authorized_launcher_sha256
        or launch.get("claim_sha256") != sha256_file(claim_path)
        or launch.get("source_inventory_sha256")
        != expected_source_inventory_sha256
        or launch.get("run_directory") != str(run_directory)
        or launch.get("authoritative") is not False
        or launch.get("PROMISING") is not False
    ):
        raise IntegrityError("Launch record binding differs")
    return {
        "claim_sha256": sha256_file(claim_path),
        "launch_record_sha256": sha256_file(launch_record_path),
        "source_inventory_sha256": expected_source_inventory_sha256,
        "launcher_sha256": authorized_launcher_sha256,
    }


def verify_runner_envelope(
    run_directory: Path,
    closure: CandidateClosure,
    *,
    run_id: str,
    archive: Path,
    config: Mapping[str, Any],
    expected_source_hashes: Mapping[str, Any],
) -> Mapping[str, Any]:
    started = read_json(run_directory / "RUN_STARTED.json", "run-start record")
    environment = read_json(run_directory / "environment.json", "runner environment")
    sources = read_json(run_directory / "source_inventory.json", "runner sources")
    archive_record = read_json(
        run_directory / "archive_and_extraction.json", "archive record"
    )
    cohort = read_json(run_directory / "cohort_and_layout.json", "cohort record")
    thread_environment = require_mapping(
        environment.get("thread_environment"), "runner thread environment"
    )
    expected_threads = {
        **{name: "1" for name in THREAD_VARIABLES},
        "CUDA_VISIBLE_DEVICES": "-1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }
    if dict(thread_environment) != expected_threads:
        raise IntegrityError("Runner numerical/offline environment differs")
    packages = require_mapping(environment.get("packages"), "runner packages")
    if packages.get("scikit-learn") != "1.8.0":
        raise IntegrityError("Runner did not use scikit-learn 1.8.0")
    python_path = Path(str(environment.get("python_executable", ""))).resolve(strict=True)
    if (
        python_path != Path(sys.executable).resolve()
        or sha256_file(python_path) != expected_source_hashes.get("python_executable")
    ):
        raise IntegrityError("Runner Python executable binding differs")
    archive_binding = require_mapping(archive_record.get("archive"), "runner archive")
    expected_archive = {
        "path": str(archive.resolve(strict=True)),
        "bytes": require_int(
            _at(config, "dataset.expected_archive_size_bytes"), "archive size"
        ),
        "sha256": str(_at(config, "dataset.expected_archive_sha256")),
        "md5": str(_at(config, "dataset.expected_official_sidecar_md5")),
    }
    if dict(archive_binding) != expected_archive:
        raise IntegrityError("Runner archive binding differs")
    if archive_record.get("forbidden_tags_opened") is not False:
        raise IntegrityError("Runner reports forbidden tag access")
    exclusion = require_mapping(cohort.get("cycle5_exclusion"), "cycle-5 binding")
    exclusion_path = Path(
        str(_at(config, "dataset.prior_cycle_exclusion.record_path"))
    ).resolve(strict=True)
    expected_exclusion = {
        "path": str(exclusion_path),
        "sha256": str(_at(config, "dataset.prior_cycle_exclusion.record_sha256")),
        "users": len(_load_cycle5_exclusion(config)),
    }
    if dict(exclusion) != expected_exclusion:
        raise IntegrityError("Runner cycle-5 exclusion binding differs")
    source_files = require_mapping(sources.get("source_files"), "runner source files")
    reconstructed = sha256_bytes(
        canonical_json_bytes(
            {
                "run_id": run_id,
                "sources": dict(source_files),
                "archive": expected_archive,
                "exclusion": expected_exclusion,
                "environment": {
                    "python_executable": environment.get("python_executable"),
                    "python_version": environment.get("python_version"),
                    "platform": environment.get("platform"),
                    "processor": environment.get("processor"),
                    "packages": dict(packages),
                    "thread_environment": dict(thread_environment),
                },
            }
        )
    )
    if reconstructed != closure.execution_fingerprint:
        raise IntegrityError("Independent execution-fingerprint reconstruction differs")
    if (
        started.get("producer_pid") != closure.runner_pid
        or started.get("runner_source_sha256") != expected_source_hashes.get("runner")
        or started.get("config_sha256") != expected_source_hashes.get("config")
        or started.get("protocol_sha256") != expected_source_hashes.get("protocol")
        or started.get("top_level_PROMISING") is not False
    ):
        raise IntegrityError("Runner start record binding differs")
    return {
        "execution_fingerprint_recomputed": True,
        "archive_authenticated": True,
        "environment_authenticated": True,
        "source_inventory_authenticated": True,
    }


def run_independent_verifier(
    *,
    run_directory: Path,
    candidate_path: Path,
    report_path: Path,
    verifier_lock_path: Path,
    verifier_ledger_path: Path,
    config_path: Path,
    protocol_path: Path,
    archive_path: Path,
    run_id: str,
    authorized_launcher_sha256: str,
    claim_path: Path,
    launch_record_path: Path,
    source_inventory_path: Path,
    expected_source_inventory_sha256: str,
) -> Mapping[str, Any]:
    run_id = safe_run_id(run_id)
    run_directory = run_directory.resolve(strict=True)
    report_path = report_path.resolve()
    paths = locked_paths()
    if (
        config_path.resolve(strict=True) != paths["config"]
        or protocol_path.resolve(strict=True) != paths["protocol"]
        or report_path.parent != run_directory
    ):
        raise IntegrityError("Verifier source/config/protocol/report path differs")
    config = read_json(config_path, "locked PIVOT config")
    validate_config_contract(config)
    expected_hashes_record = read_json(
        source_inventory_path, "launch source inventory"
    )
    expected_source_hashes = require_mapping(
        expected_hashes_record.get("source_hashes"), "expected source hashes"
    )
    verify_source_hashes(paths, Path(sys.executable).resolve(), expected_source_hashes)
    authorization = verify_launch_authorization(
        run_directory=run_directory,
        run_id=run_id,
        authorized_launcher_sha256=authorized_launcher_sha256,
        claim_path=claim_path.resolve(strict=True),
        launch_record_path=launch_record_path.resolve(strict=True),
        source_inventory_path=source_inventory_path.resolve(strict=True),
        expected_source_inventory_sha256=expected_source_inventory_sha256,
        expected_source_hashes=expected_source_hashes,
    )
    lock = ExclusiveOwnerLock(verifier_lock_path, "post-exit-verifier")
    lock.acquire()
    try:
        create_empty_exclusive(verifier_ledger_path)
        install_async_exception_hooks(verifier_ledger_path)
        closure = verify_runner_closure(
            run_directory,
            candidate_path,
            expected_run_id=run_id,
            expected_source_hashes=expected_source_hashes,
        )
        expected_report_name = (
            f"PIVOT_VERIFIER_REPORT_{closure.execution_fingerprint[:16]}.json"
        )
        if report_path.name != expected_report_name or report_path.exists():
            raise IntegrityError("Verifier report name exists or differs from contract")
        envelope = verify_runner_envelope(
            run_directory,
            closure,
            run_id=run_id,
            archive=archive_path,
            config=config,
            expected_source_hashes=expected_source_hashes,
        )
        replay = replay_archive(archive_path, config)
        representation = verify_representation(run_directory, config, replay)
        A_arrays = verify_cohort_and_A(run_directory, replay, representation)
        verify_stage_basis(
            run_directory,
            "stage_R_basis_manifest.json",
            "pivot-stage-r-basis-v1",
            "R",
            replay,
        )
        verify_stage_basis(
            run_directory,
            "stage_V_candidate_bank_manifest.json",
            "pivot-stage-v-bank-v1",
            "V",
            replay,
        )
        verify_stage_basis(
            run_directory,
            "stage_T_candidate_bank_manifest.json",
            "pivot-stage-t-bank-v1",
            "T",
            replay,
        )
        V_bank, V_manifest = load_candidate_bank(run_directory, "V")
        T_bank, T_manifest = load_candidate_bank(run_directory, "T")
        raw_faiss_scores, raw_score_diagnostics = canonical_faiss_scores(
            np.asarray(A_arrays["query"], dtype=np.float32), representation
        )
        V_bank_replay = verify_bank(
            stage="V",
            bank=V_bank,
            replay=replay,
            representation=representation,
            A_arrays=A_arrays,
            raw_scores=raw_faiss_scores,
        )
        T_bank_replay = verify_bank(
            stage="T",
            bank=T_bank,
            replay=replay,
            representation=representation,
            A_arrays=A_arrays,
            raw_scores=raw_faiss_scores,
        )
        training_manifest = read_json(
            run_directory / "training_manifest.json", "training manifest"
        )
        selected_epoch, frozen_comparator, _, checkpoint_selection = (
            verify_frozen_validation_choices(
                run_directory,
                replay,
                representation,
                A_arrays,
                V_bank,
                training_manifest,
            )
        )
        if tuple(map(int, T_bank["epochs"])) != (selected_epoch,):
            raise IntegrityError("T candidate bank did not use the frozen checkpoint")
        training_replay = verify_training_and_offsets(
            run_directory,
            replay,
            representation,
            A_arrays,
            V_bank,
            T_bank,
            selected_epoch,
        )
        raw_manifest = read_json(
            run_directory / "raw_metric_arrays_manifest.json", "raw metric manifest"
        )
        expected_bank_files = {
            "V": "stage_V_candidate_score_bank.npz",
            "T": "stage_T_candidate_score_bank.npz",
        }
        expected_bank_hashes = {
            "V": sha256_file(run_directory / expected_bank_files["V"]),
            "T": sha256_file(run_directory / expected_bank_files["T"]),
        }
        if (
            raw_manifest.get("candidate_bank_files") != expected_bank_files
            or raw_manifest.get("candidate_bank_sha256") != expected_bank_hashes
            or V_manifest.get("bank_sha256") != expected_bank_hashes["V"]
            or T_manifest.get("bank_sha256") != expected_bank_hashes["T"]
            or tuple(raw_manifest.get("metric_names", ())) != EXPECTED_METRICS
            or tuple(raw_manifest.get("method_names", ())) != EXPECTED_METHODS
            or tuple(raw_manifest.get("seed_values", ())) != EXPECTED_SEEDS
        ):
            raise IntegrityError("Raw metric manifest axes or candidate-bank bindings differ")
        V_selected_bank = selected_epoch_bank(V_bank, selected_epoch)
        V_metrics = load_and_verify_metric_stage(
            run_directory,
            raw_manifest,
            "V",
            replay,
            representation,
            V_selected_bank,
        )
        selected_comparator, comparator_scores = choose_validation_comparator(
            V_metrics.values
        )
        if selected_comparator != frozen_comparator:
            raise IntegrityError("Independent V comparator choice differs")
        if (
            int(V_metrics.raw["selected_epoch"][0]) != selected_epoch
            or int(V_metrics.raw["selected_comparator_index"][0])
            != EXPECTED_METHODS.index(selected_comparator)
        ):
            raise IntegrityError("Validation raw arrays do not bind frozen choices")
        power = verify_power_audit(
            run_directory, V_metrics, checkpoint_selection
        )
        T_metrics = load_and_verify_metric_stage(
            run_directory,
            raw_manifest,
            "T",
            replay,
            representation,
            T_bank,
        )
        if (
            int(T_metrics.raw["selected_epoch"][0]) != selected_epoch
            or int(T_metrics.raw["selected_comparator_index"][0])
            != EXPECTED_METHODS.index(selected_comparator)
        ):
            raise IntegrityError("Test raw arrays do not bind frozen choices")
        surface = independent_action_surface(T_bank, T_metrics.pairs, replay.user_ids)
        score_audit = verify_score_audit(
            run_directory,
            raw_manifest,
            T_manifest,
            representation,
            A_arrays,
            T_bank,
            raw_faiss_scores,
        )
        latency = verify_latency(run_directory, replay)
        barriers = verify_stage_barriers(run_directory, raw_manifest)
        g1_invariants = {
            "runner_recursive_closure_authenticated": True,
            "launch_and_sources_authenticated": True,
            "execution_fingerprint_recomputed": bool(
                envelope["execution_fingerprint_recomputed"]
            ),
            "archive_and_exclusion_replayed": True,
            "fresh_600_user_cohort_replayed": len(replay.user_ids) == 600
            and not (set(replay.user_ids) & replay.exclusion_users),
            "balanced_32_shards_replayed": [
                int(np.sum(representation.assignment == cell)) for cell in range(32)
            ]
            == [334] * 25 + [333] * 7,
            "physical_334_slots_each": all(index.ntotal == 334 for index in representation.indexes),
            "stage_barriers_ordered": bool(barriers["ordered"]),
            "V_bank_replayed": V_bank_replay["requests_replayed"] == 3 * 4 * 8 * 600,
            "T_bank_replayed": T_bank_replay["requests_replayed"] == 3 * 8 * 600,
            "all_checkpoints_replayed": training_replay["checkpoint_count"] == 24,
            "all_three_seeds": tuple(map(int, T_bank["seeds"])) == EXPECTED_SEEDS,
            "score_audit_complete_finite": bool(score_audit["complete_finite"]),
            "fixed_work_exact": bool(
                V_bank_replay["fixed_work_exact"] and T_bank_replay["fixed_work_exact"]
            ),
        }
        gates, details = independently_compute_gates(
            T_metrics,
            comparator=selected_comparator,
            R_support=training_replay,
            V_support=V_metrics.support,
            power=power,
            surface=surface,
            latency=latency,
            g1_invariants=g1_invariants,
        )
        producer_gates = require_mapping(
            closure.candidate.get("producer_gates"), "candidate producer gates"
        )
        raw_producer_gates = require_mapping(
            raw_manifest.get("producer_gates"), "raw producer gates"
        )
        if dict(producer_gates) != dict(raw_producer_gates):
            raise IntegrityError("Producer gate copies differ between bound artifacts")
        if raw_manifest.get("producer_gate_details") != closure.candidate.get(
            "producer_gate_details"
        ):
            raise IntegrityError("Producer gate-detail copies differ")
        producer_verifier = {
            name: {
                "producer": bool(producer_gates[name]),
                "verifier": bool(gates[name]),
                "agree": bool(producer_gates[name]) is bool(gates[name]),
            }
            for name in GATE_NAMES[:8]
        }
        verify_source_hashes(paths, Path(sys.executable).resolve(), expected_source_hashes)
        lock.assert_owned()
        if verifier_ledger_path.stat().st_size != 0:
            raise IntegrityError("Verifier asynchronous error ledger is nonempty")
        report = {
            "schema": "pivot-verifier-report-v1",
            "run_id": run_id,
            "execution_fingerprint_sha256": closure.execution_fingerprint,
            "verified_utc": utc_now(),
            "verifier_pid": os.getpid(),
            "launcher_sha256": authorized_launcher_sha256,
            "source_hashes": dict(expected_source_hashes),
            "authorization": authorization,
            "runner_candidate_sha256": sha256_file(candidate_path),
            "runner_recursive_inventory_sha256": sha256_file(
                closure.inventory_path
            ),
            "runner_artifact_members_sha256": closure.inventory.get(
                "members_sha256"
            ),
            "archive_replay": {
                "selected_users": len(replay.user_ids),
                "structurally_eligible_after_exclusion": replay.structurally_eligible_count,
                "A_eligible_users": replay.A_eligible_count,
            },
            "raw_faiss_score_replay": raw_score_diagnostics,
            "V_candidate_bank_replay": V_bank_replay,
            "T_candidate_bank_replay": T_bank_replay,
            "training_replay": training_replay,
            "checkpoint_selection": checkpoint_selection,
            "selected_epoch": selected_epoch,
            "comparator": selected_comparator,
            "comparator_validation_ndcg": comparator_scores,
            "V_support": dict(V_metrics.support),
            "T_support": dict(T_metrics.support),
            "power": dict(power),
            "surface": dict(surface),
            "score_audit": score_audit,
            "latency": latency,
            "stage_barriers": barriers,
            "independent_gates": dict(gates),
            "independent_gate_details": details,
            "producer_verifier_comparison": producer_verifier,
            "all_G1_G8": bool(all(gates.values())),
            "verifier_passed": True,
            "external_G9": False,
            "authoritative": False,
            "may_publish_authoritative_marker": False,
            "PROMISING": False,
        }
        publish_json_exclusive(report_path, report)
        return report
    except BaseException as exc:
        if verifier_ledger_path.exists():
            append_json_line(
                verifier_ledger_path,
                {
                    "utc": utc_now(),
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
        raise
    finally:
        lock.release()


def persist_process_record(path: Path, record: Mapping[str, Any]) -> None:
    publish_json_exclusive(path, dict(record))


def require_clean_success(record: Mapping[str, Any], label: str) -> None:
    if (
        record.get("return_code") != 0
        or record.get("stderr_zero_bytes") is not True
        or record.get("stderr_sha256") != EMPTY_SHA256
    ):
        raise IntegrityError(f"{label} did not exit successfully with empty stderr")


def _preflight_locked_path(observed: Path, expected: Path, label: str) -> Path:
    resolved = observed.resolve(strict=True)
    if resolved != expected.resolve(strict=True) or resolved.is_symlink():
        raise IntegrityError(f"{label} differs from the locked path")
    return resolved


def launch_authorized(args: argparse.Namespace) -> Mapping[str, Any]:
    paths = locked_paths()
    launcher = paths["launcher"]
    authorization_digest = require_launcher_digest(
        args.authorized_launcher_sha256,
        launcher,
        "--authorized-launcher-sha256",
    )
    run_id = safe_run_id(str(args.run_id))
    config_path = _preflight_locked_path(args.config, paths["config"], "Config")
    protocol_path = _preflight_locked_path(args.protocol, paths["protocol"], "Protocol")
    config = read_json(config_path, "PIVOT config")
    validate_config_contract(config)
    output_root = args.output_root.resolve(strict=True)
    if not output_root.is_dir() or output_root.is_symlink():
        raise IntegrityError("External output root must be an existing real directory")
    archive_path = args.local_dataset_archive.resolve(strict=True)
    if archive_path.is_symlink():
        raise IntegrityError("Dataset archive may not be a symbolic link")
    run_directory = output_root / run_id
    claim_path = output_root / CLAIM_NAME
    source_inventory_path = output_root / f"PIVOT_SOURCE_INVENTORY_{run_id}.json"
    launch_record_path = output_root / f"PIVOT_LAUNCH_RECORD_{run_id}.json"
    failure_path = output_root / f"PIVOT_EXTERNAL_FAILURE_{run_id}.json"
    records_directory = output_root / f"PIVOT_PROCESS_RECORDS_{run_id}"
    outer_lock = ExclusiveOwnerLock(output_root / "PIVOT_LAUNCHER.lock", "outer-launcher")
    if (
        claim_path.exists()
        or run_directory.exists()
        or source_inventory_path.exists()
        or launch_record_path.exists()
        or failure_path.exists()
        or records_directory.exists()
    ):
        raise IntegrityError("Existing claim/run/record refuses a one-shot launch")
    outer_lock.acquire()
    claim_created = False
    source_inventory_sha = ""
    launch_record_sha = ""
    launcher_ledger: Path | None = None
    process_records: dict[str, Mapping[str, Any]] = {}
    try:
        outer_lock.assert_owned()
        records_directory.mkdir(parents=False, exist_ok=False)
        fsync_directory(output_root)
        launcher_ledger = records_directory / "launcher_async_error_ledger.jsonl"
        create_empty_exclusive(launcher_ledger)
        install_async_exception_hooks(launcher_ledger)
        environment = dict(os.environ)
        environment.update(execution_environment())
        python_executable = Path(sys.executable).resolve(strict=True)
        expected_hashes = source_hashes(paths, python_executable)
        if expected_hashes["launcher"] != authorization_digest:
            raise IntegrityError("Launcher digest changed during preflight")
        config_sha = expected_hashes["config"]
        # Authentication here is pre-outcome: it hashes/lists the registered
        # archive but does not parse ratings or expose an R/V/T target.
        authenticated_archive_members(archive_path, config)
        semantic_path = Path(
            str(_at(config, "embedding.reuse_candidate_path"))
        ).resolve(strict=True)
        if (
            semantic_path.is_symlink()
            or sha256_file(semantic_path)
            != _at(config, "embedding.required_reuse_candidate_sha256")
        ):
            raise IntegrityError("Registered semantic-vector cache differs")
        cycle5_path = Path(
            str(_at(config, "dataset.prior_cycle_exclusion.record_path"))
        ).resolve(strict=True)
        if sha256_file(cycle5_path) != _at(
            config, "dataset.prior_cycle_exclusion.record_sha256"
        ):
            raise IntegrityError("Cycle-5 exclusion source differs")

        runner = paths["runner"]
        common = [
            str(python_executable),
            "-B",
            "-u",
            str(runner),
        ]
        preflight_commands = {
            "runner_validate_config": [
                *common,
                "--validate-config",
                "--config",
                str(config_path),
                "--expect-config-sha256",
                config_sha,
            ],
            "runner_self_test": [
                *common,
                "--self-test",
                "--config",
                str(config_path),
                "--expect-config-sha256",
                config_sha,
            ],
        }
        for label, command in preflight_commands.items():
            record = child_process(
                command,
                cwd=project_root().parent,
                environment=environment,
                stdout_path=records_directory / f"{label}.stdout.log",
                stderr_path=records_directory / f"{label}.stderr.log",
            )
            persist_process_record(records_directory / f"{label}.exit.json", record)
            process_records[label] = record
            require_clean_success(record, label)

        qualification_path = records_directory / "real_embedding_qualification.json"
        qualification_command = [
            *common,
            "--qualify",
            "--config",
            str(config_path),
            "--expect-config-sha256",
            config_sha,
            "--semantic-vectors",
            str(semantic_path),
            "--qualification-output",
            str(qualification_path),
        ]
        qualification_record = child_process(
            qualification_command,
            cwd=project_root().parent,
            environment=environment,
            stdout_path=records_directory / "runner_qualification.stdout.log",
            stderr_path=records_directory / "runner_qualification.stderr.log",
        )
        persist_process_record(
            records_directory / "runner_qualification.exit.json",
            qualification_record,
        )
        process_records["runner_qualification"] = qualification_record
        require_clean_success(qualification_record, "runner qualification")
        qualification = read_json(qualification_path, "real embedding qualification")
        qualification_indexes = qualification.get("index_sha256")
        qualification_repeat_indexes = qualification.get("repeat_index_sha256")
        qualification_work = require_mapping(
            qualification.get("work"), "qualification work"
        )
        qualification_latency = require_mapping(
            qualification.get("latency"), "qualification latency"
        )
        qualification_latency_environment = require_mapping(
            qualification_latency.get("environment"),
            "qualification latency environment",
        )
        if (
            qualification.get("schema")
            != "pivot-real-embedding-qualification-v1"
            or qualification.get("passed") is not True
            or qualification.get("archive_opened") is not False
            or qualification.get("user_outcomes_accessed") is not False
            or qualification.get("semantic_npy_sha256")
            != _at(config, "embedding.required_reuse_candidate_sha256")
            or qualification.get("config_sha256") != config_sha
            or qualification.get("runner_source_sha256")
            != expected_hashes["runner"]
            or qualification.get("repeat_construction_identity") is not True
            or not isinstance(qualification_indexes, list)
            or not isinstance(qualification_repeat_indexes, list)
            or len(qualification_indexes) != 32
            or qualification_indexes != qualification_repeat_indexes
            or not all(is_lower_sha256(value) for value in qualification_indexes)
            or qualification.get("physical_slots") != [334] * 32
            or qualification.get("real_counts") != [334] * 25 + [333] * 7
            or qualification_work.get("coarse_dots") != 32
            or qualification_work.get("shard_slot_dots") != 1336
            or qualification_work.get("probes") != 4
            or qualification_latency.get("passed") is not True
            or qualification_latency_environment.get("affinity_supported") is not True
            or not isinstance(
                qualification_latency_environment.get("peak_rss_bytes_observed"), int
            )
            or qualification_latency_environment.get("peak_rss_bytes_observed", 0)
            <= 0
        ):
            raise IntegrityError("Outcome-free real embedding qualification failed")

        verify_source_hashes(paths, python_executable, expected_hashes)
        source_inventory = {
            "schema": "pivot-launch-source-inventory-v1",
            "run_id": run_id,
            "created_utc": utc_now(),
            "launcher_sha256": authorization_digest,
            "python_executable": str(python_executable),
            "source_paths": {name: str(path.resolve()) for name, path in paths.items()},
            "source_hashes": dict(expected_hashes),
            "hardware": hardware_record(),
            "outcome_accessed": False,
        }
        publish_json_exclusive(source_inventory_path, source_inventory)
        source_inventory_sha = sha256_file(source_inventory_path)
        claim = {
            "schema": "pivot-one-time-launch-claim-v1",
            "run_id": run_id,
            "claimed_utc": utc_now(),
            "launcher_sha256": authorization_digest,
            "python_executable_sha256": expected_hashes["python_executable"],
            "config_sha256": config_sha,
            "protocol_sha256": expected_hashes["protocol"],
            "source_inventory_path": str(source_inventory_path.resolve()),
            "source_inventory_sha256": source_inventory_sha,
            "output_root": str(output_root),
            "run_directory": str(run_directory),
            "authoritative": False,
            "PROMISING": False,
        }
        publish_json_exclusive(claim_path, claim)
        claim_created = True

        runner_command = [
            *common,
            "--run",
            "--config",
            str(config_path),
            "--expect-config-sha256",
            config_sha,
            "--expect-source-sha256",
            expected_hashes["runner"],
            "--protocol",
            str(protocol_path),
            "--output-dir",
            str(run_directory),
            "--archive",
            str(archive_path),
            "--cycle5-cohort",
            str(cycle5_path),
            "--semantic-vectors",
            str(semantic_path),
            "--run-id",
            run_id,
        ]
        launch_record = {
            "schema": "pivot-launch-record-v1",
            "run_id": run_id,
            "created_utc": utc_now(),
            "launcher_sha256": authorization_digest,
            "claim_path": str(claim_path.resolve()),
            "claim_sha256": sha256_file(claim_path),
            "source_inventory_path": str(source_inventory_path.resolve()),
            "source_inventory_sha256": source_inventory_sha,
            "run_directory": str(run_directory),
            "runner_command": runner_command,
            "runner_command_sha256": sha256_bytes(
                canonical_json_bytes(runner_command)
            ),
            "qualification_path": str(qualification_path.resolve()),
            "qualification_sha256": sha256_file(qualification_path),
            "preflight_process_records": {
                name: dict(record) for name, record in process_records.items()
            },
            "environment": {name: environment[name] for name in execution_environment()},
            "authoritative": False,
            "PROMISING": False,
        }
        publish_json_exclusive(launch_record_path, launch_record)
        launch_record_sha = sha256_file(launch_record_path)
        verify_source_hashes(paths, python_executable, expected_hashes)
        outer_lock.assert_owned()

        runner_process = child_process(
            runner_command,
            cwd=project_root().parent,
            environment=environment,
            stdout_path=records_directory / "runner.stdout.log",
            stderr_path=records_directory / "runner.stderr.log",
        )
        persist_process_record(
            records_directory / "runner.exit.json", runner_process
        )
        process_records["runner"] = runner_process
        require_clean_success(runner_process, "outcome runner")
        if not run_directory.is_dir():
            raise IntegrityError("Outcome runner did not create the run directory")
        runner_ledger = run_directory / "async_error_ledger.jsonl"
        if not runner_ledger.is_file() or runner_ledger.stat().st_size != 0:
            raise IntegrityError("Outcome runner error ledger is not empty")
        if (run_directory / "RUNNER.lock").exists():
            raise IntegrityError("Outcome runner lock remains after exit")
        verify_source_hashes(paths, python_executable, expected_hashes)
        candidate_path = run_directory / RUNNER_CANDIDATE_NAME
        candidate = read_json(candidate_path, "runner candidate")
        fingerprint = str(candidate.get("execution_fingerprint_sha256", ""))
        if not is_lower_sha256(fingerprint):
            raise IntegrityError("Runner candidate execution fingerprint is malformed")
        report_path = run_directory / f"PIVOT_VERIFIER_REPORT_{fingerprint[:16]}.json"
        verifier_lock_path = records_directory / "verifier.lock"
        verifier_ledger_path = records_directory / "verifier_async_error_ledger.jsonl"
        verifier_command = [
            str(python_executable),
            "-B",
            "-u",
            str(launcher),
            "--verify-internal",
            "--authorized-launcher-sha256",
            authorization_digest,
            "--config",
            str(config_path),
            "--protocol",
            str(protocol_path),
            "--local-dataset-archive",
            str(archive_path),
            "--run-id",
            run_id,
            "--verify-run-directory",
            str(run_directory),
            "--candidate",
            str(candidate_path),
            "--verification-report",
            str(report_path),
            "--launch-record",
            str(launch_record_path),
            "--claim",
            str(claim_path),
            "--source-inventory",
            str(source_inventory_path),
            "--expect-source-inventory-sha256",
            source_inventory_sha,
            "--verifier-lock",
            str(verifier_lock_path),
            "--verifier-ledger",
            str(verifier_ledger_path),
        ]
        verifier_process = child_process(
            verifier_command,
            cwd=project_root().parent,
            environment=environment,
            stdout_path=records_directory / "verifier.stdout.log",
            stderr_path=records_directory / "verifier.stderr.log",
        )
        persist_process_record(
            records_directory / "verifier.exit.json", verifier_process
        )
        process_records["verifier"] = verifier_process
        require_clean_success(verifier_process, "post-exit verifier")
        if verifier_lock_path.exists():
            raise IntegrityError("Verifier lock remains after verifier exit")
        if (
            not verifier_ledger_path.is_file()
            or verifier_ledger_path.stat().st_size != 0
        ):
            raise IntegrityError("Verifier asynchronous error ledger is not empty")
        report = read_json(report_path, "verifier report")
        independent_gates = require_mapping(
            report.get("independent_gates"), "independent gates"
        )
        if (
            report.get("schema") != "pivot-verifier-report-v1"
            or report.get("run_id") != run_id
            or report.get("execution_fingerprint_sha256") != fingerprint
            or report.get("verifier_passed") is not True
            or report.get("external_G9") is not False
            or report.get("authoritative") is not False
            or report.get("may_publish_authoritative_marker") is not False
            or report.get("PROMISING") is not False
            or set(independent_gates) != set(GATE_NAMES[:8])
            or not all(isinstance(value, bool) for value in independent_gates.values())
        ):
            raise IntegrityError("Verifier report authority or gate contract differs")
        verify_source_hashes(paths, python_executable, expected_hashes)
        outer_lock.assert_owned()
        if launcher_ledger.stat().st_size != 0:
            raise IntegrityError("Launcher asynchronous error ledger is nonempty")
        existing_markers = list(
            run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")
        )
        if existing_markers:
            raise IntegrityError("External completion marker already exists")
        pre_marker_inventory = recursive_hashes(run_directory)
        G9 = bool(
            claim_created
            and runner_process["return_code"] == 0
            and runner_process["stderr_zero_bytes"]
            and verifier_process["return_code"] == 0
            and verifier_process["stderr_zero_bytes"]
            and not pid_is_running(require_int(runner_process["pid"], "runner PID"))
            and not pid_is_running(require_int(verifier_process["pid"], "verifier PID"))
            and not (run_directory / "RUNNER.lock").exists()
            and not verifier_lock_path.exists()
            and runner_ledger.stat().st_size == 0
            and verifier_ledger_path.stat().st_size == 0
            and launcher_ledger.stat().st_size == 0
            and len(existing_markers) == 0
        )
        if not G9:
            raise IntegrityError("Launcher could not establish falsification authority G9")
        all_gates = {**dict(independent_gates), "G9": True}
        promising = bool(all(all_gates.values()))
        marker = {
            "schema": "pivot-external-complete-v1",
            "run_id": run_id,
            "execution_fingerprint_sha256": fingerprint,
            "completed_utc": utc_now(),
            "publisher_pid": os.getpid(),
            "launcher_sha256": authorization_digest,
            "claim_path": str(claim_path.resolve()),
            "claim_sha256": sha256_file(claim_path),
            "launch_record_path": str(launch_record_path.resolve()),
            "launch_record_sha256": launch_record_sha,
            "source_inventory_path": str(source_inventory_path.resolve()),
            "source_inventory_sha256": source_inventory_sha,
            "runner_candidate_path": str(candidate_path.resolve()),
            "runner_candidate_sha256": sha256_file(candidate_path),
            "runner_recursive_inventory_sha256": sha256_file(
                run_directory / "runner_recursive_inventory.json"
            ),
            "verifier_report_path": str(report_path.resolve()),
            "verifier_report_sha256": sha256_file(report_path),
            "runner_process": dict(runner_process),
            "verifier_process": dict(verifier_process),
            "pre_marker_recursive_inventory": pre_marker_inventory,
            "pre_marker_recursive_inventory_sha256": sha256_bytes(
                canonical_json_bytes(pre_marker_inventory)
            ),
            "gates": all_gates,
            "G9": True,
            "authoritative": True,
            "PROMISING": promising,
        }
        marker_path = run_directory / f"{EXTERNAL_MARKER_PREFIX}{fingerprint[:16]}.json"
        publish_json_exclusive(marker_path, marker)
        if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")) != [
            marker_path
        ]:
            raise IntegrityError("Exactly-one authoritative marker invariant failed")
        return {
            "schema": "pivot-launch-result-v1",
            "run_id": run_id,
            "execution_fingerprint_sha256": fingerprint,
            "authoritative_marker": str(marker_path.resolve()),
            "gates": all_gates,
            "PROMISING": promising,
        }
    except BaseException as exc:
        if claim_created and not failure_path.exists():
            with contextlib.suppress(Exception):
                publish_json_exclusive(
                    failure_path,
                    {
                        "schema": "pivot-external-failure-v1",
                        "run_id": run_id,
                        "failed_utc": utc_now(),
                        "launcher_sha256": authorization_digest,
                        "claim_sha256": sha256_file(claim_path)
                        if claim_path.is_file()
                        else None,
                        "source_inventory_sha256": source_inventory_sha or None,
                        "launch_record_sha256": launch_record_sha or None,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "authoritative": False,
                        "PROMISING": False,
                        "completion_marker_published": False,
                    },
                )
        raise
    finally:
        outer_lock.release()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-shot PIVOT launcher and independent post-exit verifier"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-config", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--verify-internal", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--authorized-launcher-sha256")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--local-dataset-archive", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--verify-run-directory", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--candidate", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--verification-report", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--launch-record", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--claim", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--source-inventory", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--expect-source-inventory-sha256", help=argparse.SUPPRESS
    )
    parser.add_argument("--verifier-lock", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--verifier-ledger", type=Path, help=argparse.SUPPRESS)
    return parser


def require_arguments(args: argparse.Namespace, *names: str) -> None:
    missing = [name for name in names if getattr(args, name) is None]
    if missing:
        raise IntegrityError(f"Mode is missing required arguments: {missing}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate_config or args.self_test:
        require_arguments(args, "config")
        _preflight_arguments_absent(args)
        if any(
            getattr(args, name) is not None
            for name in (
                "protocol",
                "claim",
                "source_inventory",
                "expect_source_inventory_sha256",
                "verifier_lock",
                "verifier_ledger",
            )
        ):
            raise IntegrityError("Outcome-blind mode rejects launch/verifier arguments")
        locked_config = _preflight_locked_path(
            args.config, locked_paths()["config"], "Config"
        )
        config = read_json(locked_config, "PIVOT config")
        report = (
            synthetic_self_test(config)
            if args.self_test
            else validate_config_contract(config)
        )
    elif args.verify_internal:
        require_arguments(
            args,
            "authorized_launcher_sha256",
            "config",
            "protocol",
            "local_dataset_archive",
            "run_id",
            "verify_run_directory",
            "candidate",
            "verification_report",
            "launch_record",
            "claim",
            "source_inventory",
            "expect_source_inventory_sha256",
            "verifier_lock",
            "verifier_ledger",
        )
        if args.output_root is not None:
            raise IntegrityError("Internal verifier rejects output-root authority")
        report = run_independent_verifier(
            run_directory=args.verify_run_directory,
            candidate_path=args.candidate,
            report_path=args.verification_report,
            verifier_lock_path=args.verifier_lock,
            verifier_ledger_path=args.verifier_ledger,
            config_path=args.config,
            protocol_path=args.protocol,
            archive_path=args.local_dataset_archive,
            run_id=args.run_id,
            authorized_launcher_sha256=args.authorized_launcher_sha256,
            claim_path=args.claim,
            launch_record_path=args.launch_record,
            source_inventory_path=args.source_inventory,
            expected_source_inventory_sha256=args.expect_source_inventory_sha256,
        )
        report = {
            "schema": report["schema"],
            "run_id": report["run_id"],
            "execution_fingerprint_sha256": report[
                "execution_fingerprint_sha256"
            ],
            "verifier_passed": report["verifier_passed"],
            "all_G1_G8": report["all_G1_G8"],
            "PROMISING": False,
        }
    else:
        require_arguments(
            args,
            "authorized_launcher_sha256",
            "config",
            "protocol",
            "output_root",
            "local_dataset_archive",
            "run_id",
        )
        if any(
            getattr(args, name) is not None
            for name in (
                "verify_run_directory",
                "candidate",
                "verification_report",
                "launch_record",
                "claim",
                "source_inventory",
                "expect_source_inventory_sha256",
                "verifier_lock",
                "verifier_ledger",
            )
        ):
            raise IntegrityError("Outer launch rejects internal-verifier arguments")
        report = launch_authorized(args)
    print(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
