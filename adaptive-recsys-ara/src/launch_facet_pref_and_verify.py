#!/usr/bin/env python3
"""Windows-safe launcher and source-bound post-exit verifier for FACET-PREF.

The outcome process is deliberately unable to certify its own exit, lock
release, persistent logs, or scientific result.  This program therefore has
two modes:

* launch mode creates one append-only run, waits on the real child handles,
  and publishes the sole authoritative marker; and
* verifier mode is a separate Python process which recursively rehashes the
  runner artifacts and reconstructs G1--G9 from the raw NPZ evidence.

No verifier decision is copied from the runner's gate booleans.  They are read
only after replay and must agree with the independently reconstructed gates.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)
EXPECTED_METHODS = (
    "selected_bpr",
    "raw_single_centroid_hybrid",
    "raw_multi_facet",
    "single_query_aligned",
    "multi_facet_zero_margin",
    "multi_facet_shuffled_direction",
    "multi_facet_pair_micro",
    "facet_pref",
)
EXPECTED_SEEDS = (20260827, 20260828, 20260829)
HYBRID_METHODS = EXPECTED_METHODS[1:]
MECHANISM_CONTROLS = EXPECTED_METHODS[2:7]
GATE_NAMES = tuple(f"G{index}" for index in range(1, 10))
EXTERNAL_MARKER_PREFIX = "EXTERNAL_COMPLETE_"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


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
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_bytes_exclusive(path: Path, payload: bytes) -> None:
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
    payload = canonical_json_bytes(value)
    with path.open("ab") as handle:
        handle.write(payload)
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
        raise RuntimeError(f"Cannot read {label}: {path}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} is not a JSON object: {path}")
    return value


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a mapping")
    return value


def require_sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise RuntimeError(f"{label} must be a sequence")
    return value


def require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise RuntimeError(f"{label} must be boolean")
    return value


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"{label} must be an integer")
    return int(value)


def require_float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeError(f"{label} must be finite")
    return result


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def contained_file(base: Path, relative_name: str, label: str) -> Path:
    relative = Path(relative_name)
    if relative.is_absolute() or relative.name in {"", ".", ".."}:
        raise RuntimeError(f"Invalid {label} path: {relative_name!r}")
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes run directory: {relative_name!r}") from exc
    if not resolved.is_file():
        raise RuntimeError(f"Missing {label}: {resolved}")
    return resolved


def safe_relative(path: Path, base: Path) -> str:
    try:
        relative = path.resolve().relative_to(base.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Path escapes base directory: {path}") from exc
    return relative.as_posix()


def pid_is_running(pid: int) -> bool:
    """Check PID liveness without sending a signal that changes process state."""
    if pid <= 0:
        return False
    if os.name == "nt":
        query_limited_information = 0x1000
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
        handle = kernel32.OpenProcess(query_limited_information, False, int(pid))
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: no such process.
                return False
            if error == 5:  # Cannot prove exit when access is denied.
                return True
            raise ctypes.WinError(error)
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            return int(code.value) == still_active
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


@dataclass
class ExclusiveOwnerLock:
    path: Path
    role: str

    def __post_init__(self) -> None:
        self.path = self.path.resolve()
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_json_bytes(
            {
                "schema": "facet-pref-exclusive-owner-lock-v1",
                "role": self.role,
                "pid": os.getpid(),
                "token_sha256": sha256_text(self.token),
                "created_utc": utc_now(),
            }
        )
        descriptor = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        fsync_directory(self.path.parent)
        self.acquired = True

    def assert_owned(self) -> None:
        if not self.acquired or not self.path.is_file():
            raise RuntimeError(f"{self.role} lock is not held")
        record = read_json_mapping(self.path, f"{self.role} lock")
        if int(record.get("pid", -1)) != os.getpid():
            raise RuntimeError(f"{self.role} lock PID changed")
        if record.get("token_sha256") != sha256_text(self.token):
            raise RuntimeError(f"{self.role} lock token changed")

    def release(self) -> None:
        if not self.acquired:
            return
        self.assert_owned()
        self.path.unlink()
        fsync_directory(self.path.parent)
        self.acquired = False


def run_hidden_process(
    command: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[int, int]:
    process: subprocess.Popen[Any] | None = None
    try:
        with stdout_path.open("xb") as stdout_handle, stderr_path.open(
            "xb"
        ) as stderr_handle:
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return process.pid, process.wait()
    except BaseException:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raise


def find_sole_runner_candidate(run_directory: Path) -> Path:
    candidates = sorted(
        run_directory.glob("RUNNER_COMPLETE_CANDIDATE_*.json"),
        key=lambda item: item.name,
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one runner completion candidate, found {len(candidates)}"
        )
    return candidates[0]


def file_hash_manifest(root: Path, excluded: Iterable[Path] = ()) -> Mapping[str, str]:
    excluded_resolved = {path.resolve() for path in excluded}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or path.resolve() in excluded_resolved:
            continue
        result[safe_relative(path, root)] = sha256_file(path)
    return result


def _decode_strings(array: Any, label: str) -> tuple[str, ...]:
    if getattr(array, "ndim", None) != 1:
        raise RuntimeError(f"{label} must be one-dimensional")
    values: list[str] = []
    for value in array.tolist():
        if isinstance(value, bytes):
            values.append(value.decode("utf-8"))
        else:
            values.append(str(value))
    return tuple(values)


def _load_npz(path: Path, required: Sequence[str], label: str) -> Mapping[str, Any]:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("NumPy is required by the FACET-PREF verifier") from exc
    try:
        with np.load(path, allow_pickle=False) as archive:
            missing = [name for name in required if name not in archive.files]
            if missing:
                raise RuntimeError(f"{label} is missing arrays: {missing}")
            return {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Cannot load {label}: {path}") from exc


def _require_shape(array: Any, shape: Sequence[int], label: str) -> None:
    actual = tuple(int(value) for value in array.shape)
    expected = tuple(int(value) for value in shape)
    if actual != expected:
        raise RuntimeError(f"{label} shape {actual} != {expected}")


def _require_finite(array: Any, label: str) -> None:
    import numpy as np

    if not np.all(np.isfinite(array)):
        raise RuntimeError(f"{label} contains a nonfinite value")


def _cohort_rows(counts: Any, label: str) -> Any:
    import numpy as np

    rows = np.flatnonzero(np.asarray(counts) > 0)
    if rows.size == 0:
        raise RuntimeError(f"{label} has no eligible users")
    return rows


def _metric_name_map(names: Sequence[str]) -> Mapping[str, int]:
    aliases = {
        "pair_support": ("pair_support", "natural_pair_support"),
        "spce_at_10": ("spce_at_10", "strict_preference_consistent_exposure_at_10"),
        "ndcg_at_10": ("ndcg_at_10",),
        "recall_at_10": ("recall_at_10",),
        "positive_union_recall": (
            "positive_union_recall",
            "positive_item_union_recall",
        ),
        "intrusion_at_10": (
            "intrusion_at_10",
            "low_rating_intrusion_at_10",
        ),
    }
    lookup = {name: index for index, name in enumerate(names)}
    result: dict[str, int] = {}
    for canonical, candidates in aliases.items():
        matches = [lookup[name] for name in candidates if name in lookup]
        if len(matches) != 1:
            raise RuntimeError(
                f"Metric array must contain exactly one alias for {canonical}: {names}"
            )
        result[canonical] = matches[0]
    if len(names) != len(result):
        raise RuntimeError(f"Unexpected extra metric names: {names}")
    return result


def _verify_semantic_owner_evidence(
    facet_counts: Any,
    quota_utilization: Any,
    retrieval_diagnostics: Any,
    semantic_owners: Any,
    label: str,
) -> Mapping[str, Any]:
    """Replay quota and canonical-owner arithmetic from per-item owners."""
    import numpy as np

    facets = np.asarray(facet_counts, dtype=np.int64)
    quotas = np.asarray(quota_utilization, dtype=np.int64)
    diagnostics = np.asarray(retrieval_diagnostics, dtype=np.int64)
    owners = np.asarray(semantic_owners, dtype=np.int64)
    if facets.ndim != 2 or quotas.shape != (*facets.shape, 2):
        raise RuntimeError(f"{label} facet/quota evidence has wrong shape")
    if diagnostics.shape != (*facets.shape, 6) or owners.shape != (*facets.shape, 200):
        raise RuntimeError(f"{label} diagnostic/owner evidence has wrong shape")
    checked = 0
    for method_index in range(facets.shape[0]):
        for user_row in range(facets.shape[1]):
            count = int(facets[method_index, user_row])
            quota = tuple(int(value) for value in quotas[method_index, user_row])
            diagnostic = tuple(
                int(value) for value in diagnostics[method_index, user_row]
            )
            owner_row = tuple(int(value) for value in owners[method_index, user_row])
            if method_index == 0:
                if count != 0 or quota != (0, 0) or any(value != -1 for value in owner_row):
                    raise RuntimeError(f"{label} selected-BPR owner padding changed")
                continue
            if count not in (1, 2) or any(value not in range(count) for value in owner_row):
                raise RuntimeError(f"{label} semantic owner domain is invalid")
            owner_counts = (
                sum(value == 0 for value in owner_row),
                sum(value == 1 for value in owner_row),
            )
            if owner_counts != quota or sum(quota) != 200:
                raise RuntimeError(f"{label} quota counts disagree with per-item owners")
            raw_overlap, eligible_overlap, duplicates_removed, lower_violation, eligible0, eligible1 = diagnostic
            if min(diagnostic) < 0 or eligible_overlap != duplicates_removed or lower_violation != 0:
                raise RuntimeError(f"{label} duplicate/owner diagnostic arithmetic failed")
            if count == 1:
                if quota != (200, 0) or any(value != 0 for value in owner_row) or eligible1 != 0:
                    raise RuntimeError(f"{label} one-facet quota/owner contract failed")
            else:
                available0 = eligible0
                available1 = eligible1 - duplicates_removed
                if available1 < 0:
                    raise RuntimeError(f"{label} duplicate count exceeds facet-1 row")
                initial0 = min(100, available0)
                initial1 = min(100, available1)
                expected: list[int] = [0] * initial0 + [1] * initial1
                remaining = [available0 - initial0, available1 - initial1]
                cursor = 0
                while len(expected) < 200:
                    facet = cursor % 2
                    cursor += 1
                    if remaining[facet] <= 0:
                        if remaining[0] <= 0 and remaining[1] <= 0:
                            break
                        continue
                    expected.append(facet)
                    remaining[facet] -= 1
                if len(expected) != 200 or tuple(expected) != owner_row:
                    raise RuntimeError(f"{label} canonical quota/backfill owner sequence failed")
                if quota[0] > available0 or quota[1] > available1:
                    raise RuntimeError(f"{label} selected more owners than eligible rows")
                if raw_overlap < eligible_overlap:
                    raise RuntimeError(f"{label} eligible overlap exceeds raw overlap")
            checked += 1
    return {"hybrid_rows_checked": checked, "quota_owner_arithmetic_replayed": True}


def _pair_outcome(top_ten: Sequence[int], chosen: int, rejected: int) -> float:
    positions = {int(item): rank for rank, item in enumerate(top_ten, start=1)}
    chosen_rank = positions.get(int(chosen), 11)
    rejected_rank = positions.get(int(rejected), 11)
    return float(chosen_rank < rejected_rank)


def _recompute_test_metrics(arrays: Mapping[str, Any]) -> tuple[Any, Mapping[str, Any]]:
    """Reconstruct every gated per-user metric from candidates and targets."""
    import numpy as np

    methods = _decode_strings(arrays["methods"], "raw test methods")
    seeds = tuple(int(value) for value in arrays["seeds"].tolist())
    if methods != EXPECTED_METHODS:
        raise RuntimeError(f"Raw test methods changed: {methods}")
    if seeds != EXPECTED_SEEDS:
        raise RuntimeError(f"Raw test seeds changed: {seeds}")
    user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    if user_ids.ndim != 1 or len(user_ids) != 2000 or len(np.unique(user_ids)) != 2000:
        raise RuntimeError("Raw test must contain exactly 2,000 unique users")
    if not np.all(user_ids[:-1] < user_ids[1:]):
        raise RuntimeError("Raw test users must be in strictly increasing numeric order")
    seed_count, method_count, user_count = 3, len(EXPECTED_METHODS), len(user_ids)
    candidates = np.asarray(arrays["candidates"], dtype=np.int64)
    rankings = np.asarray(arrays["rankings"], dtype=np.int64)
    final_scores = np.asarray(arrays["final_scores"], dtype=np.float64)
    expected_cube = (seed_count, method_count, user_count, 400)
    _require_shape(candidates, expected_cube, "candidates")
    _require_shape(rankings, expected_cube, "rankings")
    _require_shape(final_scores, expected_cube, "final_scores")
    test_items = np.asarray(arrays["test_event_items"], dtype=np.int64)
    test_ratings = np.asarray(arrays["test_event_ratings"], dtype=np.int64)
    test_counts = np.asarray(arrays["test_event_counts"], dtype=np.int64)
    if test_items.ndim != 2 or test_ratings.shape != test_items.shape:
        raise RuntimeError("Test-event item/rating matrices have inconsistent shapes")
    if test_items.shape[0] != user_count or test_counts.shape != (user_count,):
        raise RuntimeError("Test-event evidence has the wrong user dimension")
    pair_chosen = np.asarray(arrays["pair_chosen"], dtype=np.int64)
    pair_rejected = np.asarray(arrays["pair_rejected"], dtype=np.int64)
    pair_counts = np.asarray(arrays["pair_counts"], dtype=np.int64)
    if pair_chosen.ndim != 2 or pair_rejected.shape != pair_chosen.shape:
        raise RuntimeError("Fixed-pair matrices have inconsistent shapes")
    if pair_chosen.shape[0] != user_count or pair_counts.shape != (user_count,):
        raise RuntimeError("Fixed-pair evidence has the wrong user dimension")
    if np.any(test_counts < 1) or np.any(test_counts > test_items.shape[1]):
        raise RuntimeError("Invalid test-event count")
    if np.any(pair_counts < 0) or np.any(pair_counts > pair_chosen.shape[1]):
        raise RuntimeError("Invalid fixed-pair count")

    metric_order = (
        "pair_support",
        "spce_at_10",
        "ndcg_at_10",
        "recall_at_10",
        "positive_union_recall",
        "intrusion_at_10",
    )
    result = np.zeros(
        (seed_count, method_count, user_count, len(metric_order)), dtype=np.float64
    )
    result[..., 0:2] = np.nan
    pair_outcomes = np.full(
        (seed_count, method_count, user_count, pair_chosen.shape[1]),
        np.nan,
        dtype=np.float64,
    )
    pair_cosupport = np.zeros_like(pair_outcomes)
    logarithmic_discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))

    for seed_index in range(seed_count):
        for method_index, method in enumerate(methods):
            candidate_size = 200 if method == "selected_bpr" else 400
            for user_row in range(user_count):
                candidate_row = candidates[
                    seed_index, method_index, user_row, :candidate_size
                ]
                ranking_row = rankings[
                    seed_index, method_index, user_row, :candidate_size
                ]
                if np.any(candidate_row < 0) or np.any(ranking_row < 0):
                    raise RuntimeError("A served candidate/ranking contains padding")
                if len(set(int(item) for item in candidate_row)) != candidate_size:
                    raise RuntimeError("A served candidate row contains duplicates")
                if set(int(item) for item in ranking_row) != set(
                    int(item) for item in candidate_row
                ):
                    raise RuntimeError("A ranking is not a permutation of its candidates")
                candidate_set = set(int(item) for item in candidate_row)
                top_ten = tuple(int(item) for item in ranking_row[:10])
                valid_test = int(test_counts[user_row])
                user_test_items = test_items[user_row, :valid_test]
                user_test_ratings = test_ratings[user_row, :valid_test]
                positives = {
                    int(item)
                    for item, rating in zip(user_test_items, user_test_ratings)
                    if int(rating) >= 4
                }
                if not positives:
                    raise RuntimeError("Eligibility violation: test user has no positive item")
                low_items = {
                    int(item)
                    for item, rating in zip(user_test_items, user_test_ratings)
                    if int(rating) <= 2
                }
                relevance = np.asarray(
                    [float(item in positives) for item in top_ten], dtype=np.float64
                )
                dcg = float(np.sum(relevance * logarithmic_discounts))
                ideal = float(
                    np.sum(logarithmic_discounts[: min(10, len(positives))])
                )
                ndcg = dcg / ideal
                recall = float(sum(item in positives for item in top_ten)) / len(positives)
                union_recall = float(sum(item in candidate_set for item in positives)) / len(
                    positives
                )
                intrusion = float(sum(item in low_items for item in top_ten)) / 10.0

                valid_pairs = int(pair_counts[user_row])
                support_sum = 0.0
                spce_sum = 0.0
                for pair_index in range(valid_pairs):
                    chosen = int(pair_chosen[user_row, pair_index])
                    rejected = int(pair_rejected[user_row, pair_index])
                    if chosen < 0 or rejected < 0 or chosen == rejected:
                        raise RuntimeError("Malformed fixed natural-preference pair")
                    support = float(chosen in candidate_set and rejected in candidate_set)
                    outcome = _pair_outcome(top_ten, chosen, rejected)
                    support_sum += support
                    spce_sum += outcome
                    pair_cosupport[
                        seed_index, method_index, user_row, pair_index
                    ] = support
                    pair_outcomes[
                        seed_index, method_index, user_row, pair_index
                    ] = outcome
                pair_support = support_sum / valid_pairs if valid_pairs else float("nan")
                spce = spce_sum / valid_pairs if valid_pairs else float("nan")
                result[seed_index, method_index, user_row] = (
                    pair_support,
                    spce,
                    ndcg,
                    recall,
                    union_recall,
                    intrusion,
                )

    evidence = {
        "metric_order": metric_order,
        "pair_outcomes": pair_outcomes,
        "pair_cosupport": pair_cosupport,
        "pair_counts": pair_counts,
        "test_counts": test_counts,
        "methods": methods,
        "seeds": seeds,
        "user_ids": user_ids,
    }
    return result, evidence


def _audit_candidate_and_score_invariants(
    arrays: Mapping[str, Any], config: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Replay exact branch budgets, novelty, unseen status, and score order."""
    import numpy as np

    candidates = np.asarray(arrays["candidates"], dtype=np.int64)
    rankings = np.asarray(arrays["rankings"], dtype=np.int64)
    scores = np.asarray(arrays["final_scores"])
    bpr_component = np.asarray(arrays["bpr_scores"])
    semantic_component = np.asarray(arrays["semantic_scores"])
    _require_shape(bpr_component, candidates.shape, "raw BPR component scores")
    _require_shape(semantic_component, candidates.shape, "raw semantic component scores")
    selected_alpha_array = np.asarray(arrays["selected_alpha"], dtype=np.float64).reshape(-1)
    if selected_alpha_array.size != 1:
        raise RuntimeError("selected_alpha must be a scalar array")
    selected_alpha = float(selected_alpha_array[0])
    if selected_alpha not in tuple(
        float(value) for value in config["ranking"]["alpha_validation_grid"]
    ):
        raise RuntimeError("Selected alpha is outside the locked validation grid")
    prefix_items = np.asarray(arrays["prefix_items"], dtype=np.int64)
    prefix_counts = np.asarray(arrays["prefix_counts"], dtype=np.int64)
    movie_ids = np.asarray(arrays["movie_ids"], dtype=np.int64)
    if movie_ids.ndim != 1 or len(np.unique(movie_ids)) != len(movie_ids):
        raise RuntimeError("movie_ids must be a one-dimensional unique catalog map")
    if prefix_items.ndim not in (2, 3):
        raise RuntimeError("prefix_items must be [N,H] or [S,N,H]")
    if prefix_items.ndim == 2:
        if prefix_items.shape[0] != candidates.shape[2]:
            raise RuntimeError("prefix_items user dimension changed")
        prefix_items = np.broadcast_to(prefix_items[None, :, :], (3, *prefix_items.shape))
    if prefix_counts.ndim == 1:
        prefix_counts = np.broadcast_to(prefix_counts[None, :], (3, len(prefix_counts)))
    if prefix_counts.shape != prefix_items.shape[:2]:
        raise RuntimeError("prefix_counts has an incompatible shape")

    raw_method_indices = (1, 2)
    for method_index in raw_method_indices:
        if not np.array_equal(candidates[0, method_index], candidates[1, method_index]) or not np.array_equal(
            candidates[0, method_index], candidates[2, method_index]
        ):
            raise RuntimeError("A raw method changed across optimization seeds")
        if not np.array_equal(rankings[0, method_index], rankings[1, method_index]) or not np.array_equal(
            rankings[0, method_index], rankings[2, method_index]
        ):
            raise RuntimeError("A raw ranking changed across optimization seeds")
    if not np.array_equal(candidates[0, 0], candidates[1, 0]) or not np.array_equal(
        candidates[0, 0], candidates[2, 0]
    ):
        raise RuntimeError("Selected-BPR candidates changed across seeds")

    checked_rows = 0
    for seed_index in range(3):
        for user_row in range(candidates.shape[2]):
            valid_prefix = int(prefix_counts[seed_index, user_row])
            if valid_prefix < 0 or valid_prefix > prefix_items.shape[2]:
                raise RuntimeError("Invalid prefix count")
            seen = set(
                int(item)
                for item in prefix_items[seed_index, user_row, :valid_prefix]
                if int(item) >= 0
            )
            collaborative = candidates[seed_index, 0, user_row, :200]
            if np.any(collaborative < 0) or len(np.unique(collaborative)) != 200:
                raise RuntimeError("Selected-BPR branch is not exactly 200 unique items")
            if set(int(item) for item in collaborative) & seen:
                raise RuntimeError("Selected-BPR branch contains a prefix-seen item")
            if np.any(candidates[seed_index, 0, user_row, 200:] != -1):
                raise RuntimeError("Selected-BPR padding after 200 is not -1")
            if np.any(rankings[seed_index, 0, user_row, 200:] != -1):
                raise RuntimeError("Selected-BPR ranking padding after 200 is not -1")
            for method_index in range(1, len(EXPECTED_METHODS)):
                row = candidates[seed_index, method_index, user_row]
                if np.any(row < 0) or len(np.unique(row)) != 400:
                    raise RuntimeError("Hybrid union is not exactly 400 unique items")
                bpr_branch = row[:200]
                semantic_branch = row[200:]
                if not np.array_equal(bpr_branch, collaborative):
                    raise RuntimeError("A hybrid does not share the fixed BPR branch")
                if set(int(item) for item in semantic_branch) & set(
                    int(item) for item in bpr_branch
                ):
                    raise RuntimeError("Semantic branch is not BPR-novel")
                if set(int(item) for item in row) & seen:
                    raise RuntimeError("Hybrid union contains a prefix-seen item")

                ranking = rankings[seed_index, method_index, user_row]
                if set(int(item) for item in ranking) != set(int(item) for item in row):
                    raise RuntimeError("Hybrid ranking is not a complete union permutation")
                raw_bpr = np.asarray(
                    bpr_component[seed_index, method_index, user_row], dtype=np.float32
                )
                raw_semantic = np.asarray(
                    semantic_component[seed_index, method_index, user_row], dtype=np.float32
                )
                _require_finite(raw_bpr, "hybrid raw BPR scores")
                _require_finite(raw_semantic, "hybrid raw semantic scores")

                def quantile_normalize(values: Any) -> Any:
                    lower, upper = np.quantile(
                        np.asarray(values, dtype=np.float32), (0.05, 0.95)
                    )
                    span = max(float(upper - lower), 1.0e-6)
                    normalized = np.asarray(
                        (np.asarray(values, dtype=np.float32) - np.float32(lower))
                        / np.float32(span),
                        dtype=np.float32,
                    )
                    return np.clip(normalized, 0.0, 1.0).astype(
                        np.float32, copy=False
                    )

                recomputed_scores = np.asarray(
                    np.float32(selected_alpha) * quantile_normalize(raw_bpr)
                    + np.float32(1.0 - selected_alpha)
                    * quantile_normalize(raw_semantic),
                    dtype=np.float32,
                )
                raw_scores = np.asarray(
                    scores[seed_index, method_index, user_row], dtype=np.float32
                )
                _require_finite(raw_scores, "hybrid final scores")
                if not np.array_equal(raw_scores, recomputed_scores):
                    if not np.allclose(
                        raw_scores, recomputed_scores, rtol=0.0, atol=1e-7
                    ):
                        raise RuntimeError(
                            "Stored hybrid final scores fail raw fusion replay"
                        )
                score_by_item = {
                    int(item): float(score) for item, score in zip(row, raw_scores)
                }
                expected = tuple(
                    sorted(
                        (int(item) for item in row),
                        key=lambda item: (-score_by_item[item], int(movie_ids[item])),
                    )
                )
                if tuple(int(item) for item in ranking) != expected:
                    raise RuntimeError("Hybrid ranking violates score/movie-ID ordering")
                checked_rows += 1
            bpr_scores = np.asarray(
                scores[seed_index, 0, user_row, :200], dtype=np.float32
            )
            _require_finite(bpr_scores, "selected-BPR final scores")
            raw_bpr_scores = np.asarray(
                bpr_component[seed_index, 0, user_row, :200], dtype=np.float32
            )
            if not np.array_equal(bpr_scores, raw_bpr_scores):
                raise RuntimeError("Selected-BPR final scores differ from raw BPR scores")
            bpr_score_map = {
                int(item): float(score)
                for item, score in zip(collaborative, bpr_scores)
            }
            expected_bpr = tuple(
                sorted(
                    (int(item) for item in collaborative),
                    key=lambda item: (-bpr_score_map[item], int(movie_ids[item])),
                )
            )
            if tuple(int(item) for item in rankings[seed_index, 0, user_row, :200]) != expected_bpr:
                raise RuntimeError("Selected-BPR ranking violates score/movie-ID ordering")

    retrieval = require_mapping(config["retrieval"], "config.retrieval")
    if (
        int(retrieval["collaborative_candidates_exact"]) != 200
        or int(retrieval["semantic_candidates_exact"]) != 200
        or int(retrieval["union_candidates_exact"]) != 400
    ):
        raise RuntimeError("Locked 200+200 retrieval budget changed")
    return {
        "checked_hybrid_rows": checked_rows,
        "hybrid_union_size": 400,
        "collaborative_branch_size": 200,
        "semantic_branch_size": 200,
        "semantic_bpr_novel": True,
        "prefix_unseen": True,
        "selected_alpha": selected_alpha,
        "component_fusion_replayed": True,
        "score_and_movie_id_order_replayed": True,
    }


def _paired_bootstrap(
    differences: Any,
    *,
    draws: int,
    alpha: float,
    seed: int,
) -> Mapping[str, float]:
    import numpy as np

    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise RuntimeError("Paired-bootstrap input is empty, non-vector, or nonfinite")
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    chunk = 256
    for start in range(0, draws, chunk):
        stop = min(draws, start + chunk)
        indices = rng.integers(0, len(values), size=(stop - start, len(values)))
        means[start:stop] = np.mean(values[indices], axis=1, dtype=np.float64)
    lower, upper = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {
        "point": float(np.mean(values, dtype=np.float64)),
        "lower": float(lower),
        "upper": float(upper),
        "draws": int(draws),
        "users": int(len(values)),
    }


def _power_simulation(
    differences: Any,
    *,
    delta: float,
    experiments: int,
    sample_users: int,
    inner_draws: int,
    alpha: float,
    seed: int,
) -> Mapping[str, Any]:
    """Replay the registered centered, nested validation power simulation."""
    import numpy as np

    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise RuntimeError("Power-audit differences are invalid")
    centered = values - np.mean(values, dtype=np.float64) + float(delta)
    rng = np.random.default_rng(seed)
    lower_bounds = np.empty(experiments, dtype=np.float64)
    for experiment in range(experiments):
        outer_indices = rng.integers(0, len(centered), size=sample_users)
        outer_sample = centered[outer_indices]
        inner_indices = rng.integers(
            0, sample_users, size=(inner_draws, sample_users)
        )
        inner_means = np.mean(outer_sample[inner_indices], axis=1, dtype=np.float64)
        lower_bounds[experiment] = float(np.quantile(inner_means, alpha / 2.0))
    probability = float(np.mean(lower_bounds > 0.0, dtype=np.float64))
    return {
        "observed_difference_mean": float(np.mean(values, dtype=np.float64)),
        "centered_alternative_mean": float(np.mean(centered, dtype=np.float64)),
        "probability_lower_bound_above_zero": probability,
        "lower_bounds": lower_bounds,
        "experiments": int(experiments),
        "sample_users": int(sample_users),
        "inner_draws": int(inner_draws),
        "seed": int(seed),
    }


def _validation_spce_from_raw(arrays: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    import numpy as np

    methods = _decode_strings(arrays["methods"], "validation methods")
    seeds = tuple(int(value) for value in arrays["seeds"].tolist())
    if methods != EXPECTED_METHODS or seeds != EXPECTED_SEEDS:
        raise RuntimeError("Validation methods or seeds changed")
    user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    if user_ids.ndim != 1 or len(user_ids) != 2000:
        raise RuntimeError("Validation evidence must contain 2,000 users")
    if "top10" in arrays:
        top_ten = np.asarray(arrays["top10"], dtype=np.int64)
    elif "rankings" in arrays:
        top_ten = np.asarray(arrays["rankings"], dtype=np.int64)[..., :10]
    else:
        raise RuntimeError("Validation evidence contains neither top10 nor rankings")
    _require_shape(top_ten, (3, len(EXPECTED_METHODS), len(user_ids), 10), "V top10")
    pair_chosen = np.asarray(arrays["pair_chosen"], dtype=np.int64)
    pair_rejected = np.asarray(arrays["pair_rejected"], dtype=np.int64)
    pair_counts = np.asarray(arrays["pair_counts"], dtype=np.int64)
    if pair_chosen.ndim != 2 or pair_rejected.shape != pair_chosen.shape:
        raise RuntimeError("Validation pair matrices are inconsistent")
    if pair_chosen.shape[0] != len(user_ids) or pair_counts.shape != (len(user_ids),):
        raise RuntimeError("Validation pair evidence has wrong user dimension")
    spce = np.zeros((3, len(EXPECTED_METHODS), len(user_ids)), dtype=np.float64)
    for seed_index in range(3):
        for method_index in range(len(EXPECTED_METHODS)):
            for user_row in range(len(user_ids)):
                count = int(pair_counts[user_row])
                if count < 0 or count > pair_chosen.shape[1]:
                    raise RuntimeError("Invalid validation pair count")
                if count == 0:
                    continue
                outcomes = [
                    _pair_outcome(
                        top_ten[seed_index, method_index, user_row],
                        int(pair_chosen[user_row, pair_index]),
                        int(pair_rejected[user_row, pair_index]),
                    )
                    for pair_index in range(count)
                ]
                spce[seed_index, method_index, user_row] = float(np.mean(outcomes))
    return spce, pair_counts, user_ids


def _verify_natural_pair_universe(
    arrays: Mapping[str, Any],
    *,
    event_prefix: str,
    hash_seed: int,
    maximum_pairs: int,
    minimum_gap: int,
) -> Mapping[str, Any]:
    """Rebuild the fixed natural-pair arrays from raw events, never aggregates."""
    import numpy as np

    user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    movie_ids = np.asarray(arrays["movie_ids"], dtype=np.int64)
    items = np.asarray(arrays[f"{event_prefix}_event_items"], dtype=np.int64)
    ratings = np.asarray(arrays[f"{event_prefix}_event_ratings"], dtype=np.int64)
    counts = np.asarray(arrays[f"{event_prefix}_event_counts"], dtype=np.int64)
    chosen_recorded = np.asarray(arrays["pair_chosen"], dtype=np.int64)
    rejected_recorded = np.asarray(arrays["pair_rejected"], dtype=np.int64)
    pair_counts_recorded = np.asarray(arrays["pair_counts"], dtype=np.int64)
    if items.ndim != 2 or ratings.shape != items.shape or items.shape[0] != len(user_ids):
        raise RuntimeError("Raw event evidence is malformed for pair reconstruction")
    _require_shape(counts, (len(user_ids),), "raw event counts")
    _require_shape(chosen_recorded, (len(user_ids), maximum_pairs), "pair chosen")
    _require_shape(rejected_recorded, chosen_recorded.shape, "pair rejected")
    _require_shape(pair_counts_recorded, (len(user_ids),), "pair counts")
    reconstructed_chosen = np.full_like(chosen_recorded, -1)
    reconstructed_rejected = np.full_like(rejected_recorded, -1)
    reconstructed_counts = np.zeros_like(pair_counts_recorded)
    uncapped_counts = np.zeros(len(user_ids), dtype=np.int64)
    for user_row, user_id in enumerate(user_ids):
        count = int(counts[user_row])
        if count <= 0 or count > items.shape[1]:
            raise RuntimeError("Raw event count is invalid for pair reconstruction")
        events = [
            (int(items[user_row, index]), int(ratings[user_row, index]), index)
            for index in range(count)
        ]
        events.sort(key=lambda value: (int(movie_ids[value[0]]), value[2]))
        pairs: list[tuple[int, int]] = []
        for left in range(len(events)):
            for right in range(left + 1, len(events)):
                gap = events[left][1] - events[right][1]
                if abs(gap) < minimum_gap:
                    continue
                pairs.append(
                    (events[left][0], events[right][0])
                    if gap > 0
                    else (events[right][0], events[left][0])
                )
        uncapped_counts[user_row] = len(pairs)
        if len(pairs) > maximum_pairs:
            pairs = sorted(
                pairs,
                key=lambda pair: (
                    hashlib.sha256(
                        (
                            f"{hash_seed}:{int(user_id)}:"
                            f"{min(int(movie_ids[pair[0]]), int(movie_ids[pair[1]]))}:"
                            f"{max(int(movie_ids[pair[0]]), int(movie_ids[pair[1]]))}"
                        ).encode("ascii")
                    ).hexdigest(),
                    min(int(movie_ids[pair[0]]), int(movie_ids[pair[1]])),
                    max(int(movie_ids[pair[0]]), int(movie_ids[pair[1]])),
                ),
            )[:maximum_pairs]
        reconstructed_counts[user_row] = len(pairs)
        if pairs:
            reconstructed_chosen[user_row, : len(pairs)] = [pair[0] for pair in pairs]
            reconstructed_rejected[user_row, : len(pairs)] = [pair[1] for pair in pairs]
    if not np.array_equal(reconstructed_counts, pair_counts_recorded):
        raise RuntimeError("Recorded fixed-pair counts fail raw event replay")
    if not np.array_equal(reconstructed_chosen, chosen_recorded) or not np.array_equal(
        reconstructed_rejected, rejected_recorded
    ):
        raise RuntimeError("Recorded chosen/rejected pair arrays fail raw event replay")
    return {
        "fixed_pairs": int(np.sum(reconstructed_counts, dtype=np.int64)),
        "pair_bearing_users": int(np.sum(reconstructed_counts > 0, dtype=np.int64)),
        "uncapped_pairs": int(np.sum(uncapped_counts, dtype=np.int64)),
        "pair_universe_reconstructed_from_events": True,
    }


def _verify_alignment_pair_corpus(
    arrays: Mapping[str, Any], config: Mapping[str, Any], run_directory: Path
) -> Mapping[str, Any]:
    """Re-enumerate uncapped R pairs and both deterministic caps from events."""
    import numpy as np

    user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    movie_ids = np.asarray(arrays["movie_ids"], dtype=np.int64)
    event_items = np.asarray(arrays["R_event_items"], dtype=np.int64)
    event_ratings = np.asarray(arrays["R_event_ratings"], dtype=np.int64)
    event_counts = np.asarray(arrays["R_event_counts"], dtype=np.int64)
    if event_items.ndim != 2 or event_ratings.shape != event_items.shape:
        raise RuntimeError("Raw R event matrices are malformed")
    if event_items.shape[0] != len(user_ids):
        raise RuntimeError("Raw R event user dimension changed")
    _require_shape(event_counts, (len(user_ids),), "R event counts")
    gap_minimum = int(config["dataset"]["preference_pair_minimum_rating_gap"])
    cap_seed = int(str(config["alignment"]["pair_cap_hash_format"]).split(":", 1)[0])
    per_user_cap = int(config["alignment"]["maximum_pairs_per_user"])
    global_cap = int(config["alignment"]["maximum_training_pairs"])
    uncapped_by_user: dict[int, list[tuple[int, int, int]]] = {}
    uncapped_counts = np.zeros(len(user_ids), dtype=np.int64)
    for user_row, user_id_value in enumerate(user_ids):
        user_id = int(user_id_value)
        count = int(event_counts[user_row])
        if count <= 0 or count > event_items.shape[1]:
            raise RuntimeError("Raw R event count is invalid")
        rows: list[tuple[int, int, int]] = []
        for left in range(count):
            for right in range(left + 1, count):
                gap = int(event_ratings[user_row, left]) - int(
                    event_ratings[user_row, right]
                )
                if abs(gap) < gap_minimum:
                    continue
                chosen, rejected = (
                    (int(event_items[user_row, left]), int(event_items[user_row, right]))
                    if gap > 0
                    else (int(event_items[user_row, right]), int(event_items[user_row, left]))
                )
                rows.append((user_id, chosen, rejected))
        uncapped_by_user[user_id] = rows
        uncapped_counts[user_row] = len(rows)

    recorded_counts = np.asarray(
        arrays["alignment_uncapped_pair_counts_by_user"], dtype=np.int64
    )
    if not np.array_equal(recorded_counts, uncapped_counts):
        raise RuntimeError("R uncapped pair counts fail raw event replay")

    def pair_key(row: tuple[int, int, int]) -> tuple[str, int, int, int]:
        user_id, chosen, rejected = row
        low = min(int(movie_ids[chosen]), int(movie_ids[rejected]))
        high = max(int(movie_ids[chosen]), int(movie_ids[rejected]))
        return (
            hashlib.sha256(f"{cap_seed}:{user_id}:{low}:{high}".encode("ascii")).hexdigest(),
            user_id,
            low,
            high,
        )

    ranked: list[tuple[int, str, tuple[int, int, int]]] = []
    for user_id in sorted(uncapped_by_user):
        selected = sorted(uncapped_by_user[user_id], key=pair_key)[:per_user_cap]
        for within_rank, row in enumerate(selected):
            ranked.append((within_rank, pair_key(row)[0], row))
    selected_rows = [
        value[2]
        for value in sorted(ranked, key=lambda value: (value[0], value[1]))[:global_cap]
    ]
    selected_users = np.asarray(
        arrays["alignment_selected_user_ids"], dtype=np.int64
    )
    selected_chosen = np.asarray(
        arrays["alignment_selected_chosen_items"], dtype=np.int64
    )
    selected_rejected = np.asarray(
        arrays["alignment_selected_rejected_items"], dtype=np.int64
    )
    selected_assigned = np.asarray(
        arrays["alignment_selected_assigned_facets"], dtype=np.int64
    )
    selected_count = len(selected_rows)
    for value, label in (
        (selected_users, "selected R users"),
        (selected_chosen, "selected R chosen items"),
        (selected_rejected, "selected R rejected items"),
        (selected_assigned, "selected R assigned facets"),
    ):
        _require_shape(value, (selected_count,), label)
    if not np.array_equal(
        selected_users, np.asarray([row[0] for row in selected_rows], dtype=np.int64)
    ) or not np.array_equal(
        selected_chosen, np.asarray([row[1] for row in selected_rows], dtype=np.int64)
    ) or not np.array_equal(
        selected_rejected, np.asarray([row[2] for row in selected_rows], dtype=np.int64)
    ):
        raise RuntimeError("Selected R pair identities/directions fail cap replay")
    if np.any((selected_assigned < 0) | (selected_assigned >= 2)):
        raise RuntimeError("Selected R assigned-facet evidence is out of range")
    pair_pool_file = _decode_strings(arrays["R_pair_pool_file"], "R pair-pool file")
    pair_pool_hash = _decode_strings(arrays["R_pair_pool_sha256"], "R pair-pool hash")
    if len(pair_pool_file) != 1 or len(pair_pool_hash) != 1 or not is_sha256(
        pair_pool_hash[0]
    ):
        raise RuntimeError("R pair-pool binding is malformed")
    pool_path = contained_file(run_directory, pair_pool_file[0], "R pair-pool artifact")
    if sha256_file(pool_path) != pair_pool_hash[0]:
        raise RuntimeError("R pair-pool artifact hash mismatch")
    pool = read_json_mapping(pool_path, "R pair-pool artifact")
    pool_rows = require_sequence(pool.get("pairs"), "R pair-pool rows")
    if len(pool_rows) != selected_count:
        raise RuntimeError("R pair-pool row count differs from cap replay")
    for row_index, raw_row in enumerate(pool_rows):
        record = require_mapping(raw_row, f"R pair-pool row {row_index}")
        user_id = int(selected_users[row_index])
        chosen = int(selected_chosen[row_index])
        rejected = int(selected_rejected[row_index])
        expected_key = pair_key((user_id, chosen, rejected))[0]
        if (
            int(record.get("user_id", -1)) != user_id
            or int(record.get("chosen_movie_id", -1)) != int(movie_ids[chosen])
            or int(record.get("rejected_movie_id", -1)) != int(movie_ids[rejected])
            or int(record.get("assigned_raw_facet", -1))
            != int(selected_assigned[row_index])
            or str(record.get("pair_cap_hash", "")) != expected_key
            or record.get("pair_direction_joined_after_descriptor_publication") is not True
        ):
            raise RuntimeError("R pair-pool row differs from raw cap replay")
    return {
        "uncapped_natural_pairs": int(np.sum(uncapped_counts, dtype=np.int64)),
        "uncapped_pair_bearing_users": int(np.sum(uncapped_counts > 0)),
        "selected_training_pairs": selected_count,
        "per_user_cap": per_user_cap,
        "global_cap": global_cap,
        "selected_pair_ids_and_directions_replayed": True,
        "pair_pool_sha256": pair_pool_hash[0],
    }


def replay_validation_relevance_selection(
    arrays: Mapping[str, Any], config: Mapping[str, Any], run_directory: Path
) -> Mapping[str, Any]:
    """Rebuild V rankings from six pre-label manifests, then lock BPR/alpha."""
    import numpy as np

    user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    movie_ids = np.asarray(arrays["movie_ids"], dtype=np.int64)
    items = np.asarray(arrays["validation_event_items"], dtype=np.int64)
    ratings = np.asarray(arrays["validation_event_ratings"], dtype=np.int64)
    counts = np.asarray(arrays["validation_event_counts"], dtype=np.int64)
    if items.ndim != 2 or ratings.shape != items.shape:
        raise RuntimeError("Validation relevance event matrices are inconsistent")
    if items.shape[0] != len(user_ids) or counts.shape != (len(user_ids),):
        raise RuntimeError("Validation relevance evidence has wrong user dimension")
    registered_grid = np.asarray(
        config["ranking"]["alpha_validation_grid"], dtype=np.float32
    )
    consolidated_protocol = _decode_strings(
        arrays["protocol_sha256"], "raw validation protocol fingerprint"
    )
    if len(consolidated_protocol) != 1 or not is_sha256(consolidated_protocol[0]):
        raise RuntimeError("Raw validation protocol fingerprint is malformed")
    manifest_keys = _decode_strings(
        arrays["validation_manifest_keys"], "validation manifest keys"
    )
    manifest_files = _decode_strings(
        arrays["validation_manifest_files"], "validation manifest files"
    )
    manifest_hashes = _decode_strings(
        arrays["validation_manifest_sha256"], "validation manifest hashes"
    )
    expected_keys = tuple(
        f"{variant}_seed{seed}"
        for seed in EXPECTED_SEEDS
        for variant in ("implicit", "rating_aware")
    )
    if manifest_keys != expected_keys or not (
        len(manifest_files) == len(manifest_hashes) == 6
    ):
        raise RuntimeError("Validation manifest inventory changed")
    manifest_required = (
        "user_ids",
        "candidates",
        "bpr_scores",
        "semantic_scores",
        "rankings",
        "final_scores",
        "facet_counts",
        "quota_utilization",
        "semantic_owners",
        "retrieval_diagnostics",
        "retrieval_diagnostic_names",
        "alpha_grid",
        "alpha_grid_rankings",
        "methods",
        "protocol_sha256",
        "stage",
        "seed",
        "bpr_variant",
        "histories_sha256",
        "target_outcomes_opened",
    )
    expected_manifest_fields = set(manifest_required)

    def quantile_normalize(values: Any) -> Any:
        raw = np.asarray(values, dtype=np.float32)
        lower, upper = np.quantile(raw, (0.05, 0.95))
        span = max(float(upper - lower), 1.0e-6)
        return np.clip(
            np.asarray((raw - np.float32(lower)) / np.float32(span), dtype=np.float32),
            0.0,
            1.0,
        ).astype(np.float32, copy=False)

    manifests: dict[tuple[int, str], Mapping[str, Any]] = {}
    reconstructed: dict[tuple[int, str], Any] = {}
    for key, file_name, expected_hash in zip(
        manifest_keys, manifest_files, manifest_hashes
    ):
        if not is_sha256(expected_hash):
            raise RuntimeError(f"Malformed V manifest hash: {key}")
        path = contained_file(run_directory, file_name, f"V manifest {key}")
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"V manifest hash mismatch: {key}")
        manifest = _load_npz(path, manifest_required, f"V manifest {key}")
        if set(manifest) != expected_manifest_fields:
            raise RuntimeError(
                f"V manifest {key} has unexpected fields: "
                f"{sorted(set(manifest) - expected_manifest_fields)}"
            )
        if _decode_strings(manifest["methods"], f"{key} methods") != EXPECTED_METHODS:
            raise RuntimeError(f"V manifest method list changed: {key}")
        if _decode_strings(manifest["protocol_sha256"], f"{key} protocol") != consolidated_protocol:
            raise RuntimeError(f"V manifest protocol fingerprint changed: {key}")
        if _decode_strings(manifest["stage"], f"{key} stage") != ("V",):
            raise RuntimeError(f"V manifest stage changed: {key}")
        if np.asarray(manifest["target_outcomes_opened"]).reshape(-1).tolist() != [0]:
            raise RuntimeError(f"V manifest was published after target opening: {key}")
        seed = int(np.asarray(manifest["seed"]).reshape(-1)[0])
        variant = _decode_strings(manifest["bpr_variant"], f"{key} variant")[0]
        if key != f"{variant}_seed{seed}" or seed not in EXPECTED_SEEDS or variant not in {
            "implicit",
            "rating_aware",
        }:
            raise RuntimeError(f"V manifest key/provenance mismatch: {key}")
        if not np.array_equal(np.asarray(manifest["user_ids"], dtype=np.int64), user_ids):
            raise RuntimeError(f"V manifest cohort mismatch: {key}")
        candidates = np.asarray(manifest["candidates"], dtype=np.int64)
        bpr_scores = np.asarray(manifest["bpr_scores"], dtype=np.float32)
        semantic_scores = np.asarray(manifest["semantic_scores"], dtype=np.float32)
        _require_shape(candidates, (8, len(user_ids), 400), f"{key} candidates")
        _require_shape(bpr_scores, candidates.shape, f"{key} BPR scores")
        _require_shape(semantic_scores, candidates.shape, f"{key} semantic scores")
        diagnostic_names = _decode_strings(
            manifest["retrieval_diagnostic_names"], f"{key} retrieval diagnostic names"
        )
        expected_diagnostics = (
            "pre_exclusion_cross_facet_overlap",
            "eligible_cross_facet_overlap",
            "higher_facet_duplicates_removed",
            "lower_owner_violation_count",
            "eligible_facet0_count",
            "eligible_facet1_count",
        )
        if diagnostic_names != expected_diagnostics:
            raise RuntimeError(f"V retrieval diagnostic schema changed: {key}")
        retrieval_diagnostics = np.asarray(
            manifest["retrieval_diagnostics"], dtype=np.int64
        )
        _require_shape(
            retrieval_diagnostics,
            (8, len(user_ids), len(expected_diagnostics)),
            f"{key} retrieval diagnostics",
        )
        if np.any(retrieval_diagnostics[:, :, 3] != 0):
            raise RuntimeError(f"Lower-canonical facet ownership violated: {key}")
        _verify_semantic_owner_evidence(
            manifest["facet_counts"],
            manifest["quota_utilization"],
            manifest["retrieval_diagnostics"],
            manifest["semantic_owners"],
            f"V manifest {key}",
        )
        prefix_items = np.asarray(arrays["prefix_items"], dtype=np.int64)
        prefix_counts = np.asarray(arrays["prefix_counts"], dtype=np.int64)
        if prefix_items.ndim != 2 or prefix_items.shape[0] != len(user_ids):
            raise RuntimeError("Validation prefix matrix has wrong shape")
        _require_shape(prefix_counts, (len(user_ids),), "validation prefix counts")
        for user_row in range(len(user_ids)):
            count = int(prefix_counts[user_row])
            if count < 0 or count > prefix_items.shape[1]:
                raise RuntimeError("Validation prefix count is invalid")
            seen = set(int(value) for value in prefix_items[user_row, :count])
            collaborative = candidates[0, user_row, :200]
            if (
                np.any(collaborative < 0)
                or len(np.unique(collaborative)) != 200
                or np.any(candidates[0, user_row, 200:] != -1)
                or bool(set(int(value) for value in collaborative) & seen)
            ):
                raise RuntimeError(f"V selected-BPR budget/unseen contract failed: {key}")
            _require_finite(bpr_scores[0, user_row, :200], f"{key} BPR scores")
            for method_index in range(1, 8):
                union = candidates[method_index, user_row]
                if (
                    np.any(union < 0)
                    or len(np.unique(union)) != 400
                    or not np.array_equal(union[:200], collaborative)
                    or bool(set(int(value) for value in union) & seen)
                    or bool(
                        set(int(value) for value in union[:200])
                        & set(int(value) for value in union[200:])
                    )
                ):
                    raise RuntimeError(f"V hybrid 200+200 contract failed: {key}")
                _require_finite(
                    bpr_scores[method_index, user_row], f"{key} hybrid BPR scores"
                )
                _require_finite(
                    semantic_scores[method_index, user_row],
                    f"{key} hybrid semantic scores",
                )
        alpha_grid = np.asarray(manifest["alpha_grid"], dtype=np.float32)
        if not np.array_equal(alpha_grid, registered_grid):
            raise RuntimeError(f"V manifest alpha grid changed: {key}")
        recorded_grid_rankings = np.asarray(
            manifest["alpha_grid_rankings"], dtype=np.int64
        )
        _require_shape(
            recorded_grid_rankings,
            (len(alpha_grid), 8, len(user_ids), 400),
            f"{key} alpha-grid rankings",
        )
        if np.any(np.asarray(manifest["rankings"], dtype=np.int64) != -1):
            raise RuntimeError(f"V manifest contains a post-selection ranking: {key}")
        if not np.all(np.isnan(np.asarray(manifest["final_scores"], dtype=np.float32))):
            raise RuntimeError(f"V manifest contains post-selection final scores: {key}")

        replayed = np.array(recorded_grid_rankings, copy=True)
        for alpha_row, alpha in enumerate(alpha_grid):
            # Only BPR and the raw-single hybrid select V choices.  Every
            # method is independently rebuilt at the selected alpha below.
            for method_index, method in enumerate(EXPECTED_METHODS[:2]):
                size = 200 if method == "selected_bpr" else 400
                for user_row in range(len(user_ids)):
                    row = candidates[method_index, user_row, :size]
                    if np.any(row < 0) or len(np.unique(row)) != size:
                        raise RuntimeError(f"V manifest candidate row malformed: {key}")
                    raw_bpr = bpr_scores[method_index, user_row, :size]
                    _require_finite(raw_bpr, f"{key} raw BPR scores")
                    if method == "selected_bpr":
                        combined = raw_bpr
                    else:
                        raw_semantic = semantic_scores[method_index, user_row, :size]
                        _require_finite(raw_semantic, f"{key} raw semantic scores")
                        combined = np.asarray(
                            np.float32(alpha) * quantile_normalize(raw_bpr)
                            + np.float32(1.0 - float(alpha))
                            * quantile_normalize(raw_semantic),
                            dtype=np.float32,
                        )
                    score_by_item = {
                        int(value): float(score)
                        for value, score in zip(row, combined)
                    }
                    order = tuple(
                        sorted(
                            (int(value) for value in row),
                            key=lambda value: (
                                -score_by_item[value],
                                int(movie_ids[value]),
                            ),
                        )
                    )
                    replayed[alpha_row, method_index, user_row, :size] = order
        if not np.array_equal(
            replayed[:, :2], recorded_grid_rankings[:, :2]
        ):
            raise RuntimeError(f"V manifest alpha-grid rankings fail raw replay: {key}")
        manifests[(seed, variant)] = manifest
        reconstructed[(seed, variant)] = replayed

    # Raw methods and BPR must be invariant across adapter seeds for each BPR variant.
    for variant in ("implicit", "rating_aware"):
        first = manifests[(EXPECTED_SEEDS[0], variant)]
        for seed in EXPECTED_SEEDS[1:]:
            other = manifests[(seed, variant)]
            for field in (
                "candidates",
                "bpr_scores",
                "semantic_scores",
                "facet_counts",
                "quota_utilization",
                "retrieval_diagnostics",
                "semantic_owners",
                "alpha_grid_rankings",
            ):
                if field == "alpha_grid_rankings":
                    first_value = np.asarray(first[field])[:, :3]
                    other_value = np.asarray(other[field])[:, :3]
                else:
                    first_value = np.asarray(first[field])[:3]
                    other_value = np.asarray(other[field])[:3]
                if not np.array_equal(first_value, other_value, equal_nan=True):
                    raise RuntimeError(
                        f"Seed-invariant V raw methods changed for {variant}: {field}"
                    )

    discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))

    def macro_relevance(ranking_rows: Sequence[Any]) -> tuple[float, float]:
        ndcg_values: list[float] = []
        recall_values: list[float] = []
        for rankings in ranking_rows:
            for user_row in range(len(user_ids)):
                count = int(counts[user_row])
                if count <= 0 or count > items.shape[1]:
                    raise RuntimeError("Invalid validation-event count")
                positives = {
                    int(item)
                    for item, rating in zip(
                        items[user_row, :count], ratings[user_row, :count]
                    )
                    if int(rating) >= 4
                }
                if not positives:
                    raise RuntimeError("Validation user lacks a relevance-positive item")
                top_ten = tuple(int(value) for value in rankings[user_row, :10])
                relevance = np.asarray(
                    [float(value in positives) for value in top_ten], dtype=np.float64
                )
                dcg = float(np.sum(relevance * discounts))
                ideal = float(np.sum(discounts[: min(10, len(positives))]))
                ndcg_values.append(dcg / ideal)
                recall_values.append(
                    float(sum(value in positives for value in top_ten)) / len(positives)
                )
        return float(np.mean(ndcg_values)), float(np.mean(recall_values))

    bpr_reports: dict[str, Mapping[str, float]] = {}
    bpr_metrics: dict[str, tuple[float, float]] = {}
    for variant in ("implicit", "rating_aware"):
        rows = [reconstructed[(seed, variant)][0, 0] for seed in EXPECTED_SEEDS]
        bpr_metrics[variant] = macro_relevance(rows)
        bpr_reports[variant] = {
            "ndcg_at_10": bpr_metrics[variant][0],
            "recall_at_10": bpr_metrics[variant][1],
        }
    selected_variant = max(
        ("implicit", "rating_aware"),
        key=lambda variant: (
            bpr_metrics[variant][0],
            bpr_metrics[variant][1],
            1 if variant == "implicit" else 0,
        ),
    )
    alpha_reports: list[Mapping[str, float]] = []
    alpha_metrics: list[tuple[float, float]] = []
    for alpha_row, alpha in enumerate(registered_grid):
        rows = [
            reconstructed[(seed, selected_variant)][alpha_row, 1]
            for seed in EXPECTED_SEEDS
        ]
        metric = macro_relevance(rows)
        alpha_metrics.append(metric)
        alpha_reports.append(
            {
                "alpha": float(alpha),
                "ndcg_at_10": metric[0],
                "recall_at_10": metric[1],
            }
        )
    selected_alpha_row = max(
        range(len(registered_grid)),
        key=lambda index: (
            alpha_metrics[index][0],
            alpha_metrics[index][1],
            float(registered_grid[index]),
        ),
    )
    selected_alpha = float(registered_grid[selected_alpha_row])
    locked_variant = _decode_strings(
        np.asarray(arrays["selected_bpr_variant"]).reshape(-1),
        "locked selected BPR variant",
    )
    locked_alpha = np.asarray(arrays["selected_alpha"], dtype=np.float64).reshape(-1)
    if locked_variant != (selected_variant,) or locked_alpha.size != 1 or not math.isclose(
        float(locked_alpha[0]), selected_alpha, rel_tol=0.0, abs_tol=1e-7
    ):
        raise RuntimeError("Locked validation choices disagree with manifest replay")
    consolidated_top10 = np.asarray(arrays["top10"], dtype=np.int64)
    _require_shape(consolidated_top10, (3, 8, len(user_ids), 10), "V consolidated top10")
    for seed_row, seed in enumerate(EXPECTED_SEEDS):
        manifest = manifests[(seed, selected_variant)]
        candidates = np.asarray(manifest["candidates"], dtype=np.int64)
        bpr_scores = np.asarray(manifest["bpr_scores"], dtype=np.float32)
        semantic_scores = np.asarray(manifest["semantic_scores"], dtype=np.float32)
        for method_index, method in enumerate(EXPECTED_METHODS):
            size = 200 if method == "selected_bpr" else 400
            for user_row in range(len(user_ids)):
                row = candidates[method_index, user_row, :size]
                raw_bpr = bpr_scores[method_index, user_row, :size]
                if method == "selected_bpr":
                    combined = raw_bpr
                else:
                    raw_semantic = semantic_scores[method_index, user_row, :size]
                    combined = np.asarray(
                        np.float32(selected_alpha) * quantile_normalize(raw_bpr)
                        + np.float32(1.0 - selected_alpha)
                        * quantile_normalize(raw_semantic),
                        dtype=np.float32,
                    )
                score_by_item = {
                    int(value): float(score) for value, score in zip(row, combined)
                }
                expected_top10 = tuple(
                    sorted(
                        (int(value) for value in row),
                        key=lambda value: (-score_by_item[value], int(movie_ids[value])),
                    )[:10]
                )
                if tuple(consolidated_top10[seed_row, method_index, user_row]) != expected_top10:
                    raise RuntimeError(
                        "Consolidated V top10 disagrees with raw selected-alpha replay"
                    )
    return {
        "selected_bpr_variant": selected_variant,
        "selected_alpha": selected_alpha,
        "bpr_variants": bpr_reports,
        "alpha_grid": alpha_reports,
        "validation_manifest_count": 6,
        "all_manifest_fusions_replayed": True,
        "validation_relevance_replay_complete": True,
    }


def replay_validation_power(
    arrays: Mapping[str, Any], config: Mapping[str, Any], run_directory: Path
) -> Mapping[str, Any]:
    import numpy as np

    selection_report = replay_validation_relevance_selection(
        arrays, config, run_directory
    )
    validation_pair_report = _verify_natural_pair_universe(
        arrays,
        event_prefix="validation",
        hash_seed=int(
            str(config["power_audit"]["validation_pair_hash_format"]).split(":", 1)[0]
        ),
        maximum_pairs=int(config["power_audit"]["maximum_validation_pairs_per_user"]),
        minimum_gap=int(config["dataset"]["preference_pair_minimum_rating_gap"]),
    )
    alignment_report = _verify_alignment_pair_corpus(arrays, config, run_directory)
    spce, pair_counts, user_ids = _validation_spce_from_raw(arrays)
    cohort = _cohort_rows(pair_counts, "validation fixed-pair cohort")
    power_config = require_mapping(config["power_audit"], "config.power_audit")
    comparison_seeds = require_mapping(
        power_config["comparison_seeds"], "config.power_audit.comparison_seeds"
    )
    comparisons = (
        ("raw_single_centroid_hybrid", 1, int(comparison_seeds["raw_single_centroid_hybrid"])),
        ("selected_bpr", 0, int(comparison_seeds["selected_bpr"])),
    )
    reports: dict[str, Any] = {}
    raw_lower_bounds: list[Any] = []
    raw_differences: list[Any] = []
    for comparator_name, comparator_index, simulation_seed in comparisons:
        differences = np.mean(
            spce[:, 7, cohort] - spce[:, comparator_index, cohort], axis=0
        )
        simulation = _power_simulation(
            differences,
            delta=float(power_config["alternative_delta"]),
            experiments=int(power_config["simulated_experiments"]),
            sample_users=int(power_config["sample_users_with_replacement"]),
            inner_draws=int(power_config["inner_bootstrap_draws"]),
            alpha=float(power_config["alpha"]),
            seed=simulation_seed,
        )
        raw_lower_bounds.append(simulation.pop("lower_bounds"))
        raw_differences.append(differences)
        probability = float(simulation["probability_lower_bound_above_zero"])
        simulation["passed"] = bool(
            probability
            >= float(power_config["minimum_probability_lower_bound_above_zero"])
        )
        reports[comparator_name] = simulation

    recomputed_differences = np.stack(raw_differences, axis=0)
    recomputed_lower_bounds = np.stack(raw_lower_bounds, axis=0)
    if "seed_averaged_spce_differences" in arrays:
        recorded = np.asarray(arrays["seed_averaged_spce_differences"], dtype=np.float64)
        if recorded.shape == (2, len(user_ids)):
            recorded = recorded[:, cohort]
        _require_shape(recorded, recomputed_differences.shape, "stored V differences")
        if not np.allclose(recorded, recomputed_differences, rtol=0.0, atol=1e-12):
            raise RuntimeError("Stored validation sPCE differences fail raw replay")
    if "power_lower_bounds" in arrays:
        recorded_bounds = np.asarray(arrays["power_lower_bounds"], dtype=np.float64)
        _require_shape(
            recorded_bounds, recomputed_lower_bounds.shape, "stored power lower bounds"
        )
        if not np.allclose(
            recorded_bounds, recomputed_lower_bounds, rtol=0.0, atol=1e-12
        ):
            raise RuntimeError("Stored power lower bounds fail deterministic replay")
    if "alignment_uncapped_pair_counts_by_user" not in arrays:
        raise RuntimeError("Validation raw evidence lacks uncapped R pair counts")
    training_pair_count = int(alignment_report["uncapped_natural_pairs"])
    training_pair_users = int(alignment_report["uncapped_pair_bearing_users"])
    passed = bool(all(bool(report["passed"]) for report in reports.values()))
    if _decode_strings(arrays["comparator_methods"], "power comparator methods") != (
        "raw_single_centroid_hybrid",
        "selected_bpr",
    ):
        raise RuntimeError("Power-audit comparator order changed")
    recorded_probabilities = np.asarray(
        arrays["power_pass_probability"], dtype=np.float64
    ).reshape(-1)
    recomputed_probabilities = np.asarray(
        [
            reports["raw_single_centroid_hybrid"][
                "probability_lower_bound_above_zero"
            ],
            reports["selected_bpr"]["probability_lower_bound_above_zero"],
        ],
        dtype=np.float64,
    )
    if not np.array_equal(recorded_probabilities, recomputed_probabilities):
        raise RuntimeError("Stored power probability fails deterministic replay")
    recorded_pass = np.asarray(arrays["power_passed"], dtype=np.int64).reshape(-1)
    if recorded_pass.tolist() != [int(passed)]:
        raise RuntimeError("Stored power verdict fails deterministic replay")
    return {
        "validation_pair_bearing_users": int(len(cohort)),
        "alignment_uncapped_natural_pairs": training_pair_count,
        "alignment_uncapped_pair_bearing_users": training_pair_users,
        "comparisons": reports,
        "selection": selection_report,
        "validation_pair_universe": validation_pair_report,
        "alignment_pair_corpus": alignment_report,
        "passed": passed,
        "raw_replay_complete": True,
    }


def _metric_delta(
    metrics: Any,
    metric_index: int,
    first_method: int,
    second_method: int,
    cohort: Any,
) -> Any:
    import numpy as np

    seed_averaged = np.mean(metrics[:, :, :, metric_index], axis=0)
    return np.asarray(
        seed_averaged[first_method, cohort] - seed_averaged[second_method, cohort],
        dtype=np.float64,
    )


def replay_test_gates(
    arrays: Mapping[str, Any],
    latency_arrays: Mapping[str, Any],
    config: Mapping[str, Any],
    power_report: Mapping[str, Any],
    integrity_preconditions: Mapping[str, bool],
) -> Mapping[str, Any]:
    import numpy as np

    recomputed, evidence = _recompute_test_metrics(arrays)
    if "metrics" in arrays:
        recorded_metrics = np.asarray(arrays["metrics"], dtype=np.float64)
        metric_names = _decode_strings(arrays["metric_names"], "stored metric names")
        name_map = _metric_name_map(metric_names)
        reordered = np.stack(
            [recorded_metrics[..., name_map[name]] for name in evidence["metric_order"]],
            axis=-1,
        )
        _require_shape(reordered, recomputed.shape, "stored per-user metrics")
        if not np.allclose(
            reordered, recomputed, rtol=0.0, atol=1e-12, equal_nan=True
        ):
            maximum_error = float(np.nanmax(np.abs(reordered - recomputed)))
            raise RuntimeError(
                f"Stored per-user metrics fail raw replay (max error {maximum_error})"
            )
    candidate_audit = _audit_candidate_and_score_invariants(arrays, config)
    test_variant = _decode_strings(
        np.asarray(arrays["selected_bpr_variant"]).reshape(-1),
        "test selected BPR variant",
    )
    selection = require_mapping(power_report["selection"], "validation selection replay")
    if test_variant != (str(selection["selected_bpr_variant"]),):
        raise RuntimeError("Test BPR identity differs from validation-locked identity")
    if float(candidate_audit["selected_alpha"]) != float(selection["selected_alpha"]):
        raise RuntimeError("Test alpha differs from validation-locked alpha")
    pair_counts = evidence["pair_counts"]
    pair_cohort = _cohort_rows(pair_counts, "test fixed-pair cohort")
    relevance_cohort = np.arange(recomputed.shape[2], dtype=np.int64)
    intrusion_cohort = relevance_cohort
    metric_index = {name: index for index, name in enumerate(evidence["metric_order"])}
    evaluation = require_mapping(config["evaluation"], "config.evaluation")
    bootstrap_draws = int(evaluation["bootstrap_draws"])
    bootstrap_alpha = float(evaluation["bootstrap_alpha"])
    bootstrap_seed = int(evaluation["bootstrap_seed"])

    def comparison(
        metric: str,
        first: int,
        second: int,
        cohort: Any,
    ) -> Mapping[str, float]:
        return _paired_bootstrap(
            _metric_delta(
                recomputed, metric_index[metric], first, second, cohort
            ),
            draws=bootstrap_draws,
            alpha=bootstrap_alpha,
            seed=bootstrap_seed,
        )

    deltas = {
        "pair_support_vs_hybrid": comparison("pair_support", 7, 1, pair_cohort),
        "union_recall_vs_hybrid": comparison(
            "positive_union_recall", 7, 1, relevance_cohort
        ),
        "spce_vs_hybrid": comparison("spce_at_10", 7, 1, pair_cohort),
        "spce_vs_bpr": comparison("spce_at_10", 7, 0, pair_cohort),
        "ndcg_vs_hybrid": comparison("ndcg_at_10", 7, 1, relevance_cohort),
        "recall_vs_hybrid": comparison("recall_at_10", 7, 1, relevance_cohort),
        "intrusion_vs_hybrid": comparison(
            "intrusion_at_10", 7, 1, intrusion_cohort
        ),
    }
    gates_config = require_mapping(config["promise_gate"], "config.promise_gate")
    gate2 = require_mapping(gates_config["G2"], "config.promise_gate.G2")
    gate3 = require_mapping(gates_config["G3"], "config.promise_gate.G3")
    gate4 = require_mapping(gates_config["G4"], "config.promise_gate.G4")
    gate6 = require_mapping(gates_config["G6"], "config.promise_gate.G6")
    gate7 = require_mapping(gates_config["G7"], "config.promise_gate.G7")
    gate8 = require_mapping(gates_config["G8"], "config.promise_gate.G8")

    matrix_index_immutable = bool(
        integrity_preconditions.get("matrix_index_immutable", False)
    )
    target_blind = bool(integrity_preconditions.get("target_blind_order", False))
    g1 = bool(matrix_index_immutable and target_blind)

    g2 = bool(
        deltas["pair_support_vs_hybrid"]["point"]
        >= float(gate2["minimum_pair_support_point_gain"])
        and deltas["pair_support_vs_hybrid"]["lower"] > 0.0
        and deltas["union_recall_vs_hybrid"]["point"]
        >= float(gate2["minimum_positive_union_recall_point_gain"])
        and deltas["union_recall_vs_hybrid"]["lower"] > 0.0
    )
    g3 = bool(
        deltas["spce_vs_hybrid"]["point"]
        >= float(gate3["minimum_spce_at_10_point_gain_each"])
        and deltas["spce_vs_hybrid"]["lower"] > 0.0
        and deltas["spce_vs_bpr"]["point"]
        >= float(gate3["minimum_spce_at_10_point_gain_each"])
        and deltas["spce_vs_bpr"]["lower"] > 0.0
    )
    g4 = bool(
        deltas["ndcg_vs_hybrid"]["point"]
        >= float(gate4["minimum_ndcg_at_10_point_delta"])
        and deltas["ndcg_vs_hybrid"]["lower"]
        > float(gate4["minimum_ndcg_at_10_lower_bound_strict"])
        and deltas["recall_vs_hybrid"]["lower"]
        > float(gate4["minimum_recall_at_10_lower_bound_strict"])
        and deltas["intrusion_vs_hybrid"]["upper"]
        <= float(gate4["maximum_intrusion_at_10_increase_upper_bound"])
    )

    seed_averaged = np.mean(recomputed, axis=0)
    control_points: dict[str, Mapping[str, float]] = {}
    g5 = True
    for control in MECHANISM_CONTROLS:
        control_index = EXPECTED_METHODS.index(control)
        pair_delta = float(
            np.mean(
                seed_averaged[7, pair_cohort, metric_index["pair_support"]]
                - seed_averaged[control_index, pair_cohort, metric_index["pair_support"]]
            )
        )
        spce_delta = float(
            np.mean(
                seed_averaged[7, pair_cohort, metric_index["spce_at_10"]]
                - seed_averaged[control_index, pair_cohort, metric_index["spce_at_10"]]
            )
        )
        control_points[control] = {
            "pair_support_delta": pair_delta,
            "spce_at_10_delta": spce_delta,
        }
        g5 = bool(g5 and pair_delta > 0.0 and spce_delta > 0.0)

    pair_outcomes = evidence["pair_outcomes"]
    pair_cosupport = evidence["pair_cosupport"]
    common_sum = 0.0
    changed_sum = 0.0
    total_pair_rows = 0
    common_by_seed = np.zeros(3, dtype=np.int64)
    changed_by_seed = np.zeros(3, dtype=np.int64)
    rows_by_seed = np.zeros(3, dtype=np.int64)
    for seed_index in range(3):
        for user_row in pair_cohort:
            for pair_index in range(int(pair_counts[user_row])):
                common_value = int(
                    pair_cosupport[seed_index, 7, user_row, pair_index] > 0.5
                    and pair_cosupport[seed_index, 1, user_row, pair_index] > 0.5
                )
                changed_value = int(
                    pair_outcomes[seed_index, 7, user_row, pair_index]
                    != pair_outcomes[seed_index, 1, user_row, pair_index]
                )
                common_sum += common_value
                changed_sum += changed_value
                total_pair_rows += 1
                common_by_seed[seed_index] += common_value
                changed_by_seed[seed_index] += changed_value
                rows_by_seed[seed_index] += 1
    if total_pair_rows == 0:
        raise RuntimeError("No fixed test pair rows exist")
    common_support = common_sum / total_pair_rows
    changed_fraction = changed_sum / total_pair_rows
    for field, expected in (
        ("common_support_counts", common_by_seed),
        ("changed_outcome_counts", changed_by_seed),
        ("total_pair_rows", rows_by_seed),
    ):
        if not np.array_equal(np.asarray(arrays[field], dtype=np.int64), expected):
            raise RuntimeError(f"Stored pair diagnostic fails raw replay: {field}")
    training_pairs = int(power_report["alignment_uncapped_natural_pairs"])
    training_users = int(power_report["alignment_uncapped_pair_bearing_users"])
    test_pairs = int(np.sum(pair_counts, dtype=np.int64))
    test_pair_users = int(len(pair_cohort))
    g6 = bool(
        training_pairs >= int(gate6["minimum_R_natural_pairs"])
        and training_users >= int(gate6["minimum_R_pair_bearing_users"])
        and test_pairs >= int(gate6["minimum_T_fixed_pairs"])
        and test_pair_users >= int(gate6["minimum_T_pair_bearing_users"])
        and power_report["passed"] is True
        and common_support >= float(gate6["minimum_common_pair_endpoint_cosupport"])
        and changed_fraction
        >= float(gate6["minimum_changed_spce_pair_outcome_fraction"])
    )

    seed_reports: list[Mapping[str, Any]] = []
    stable_count = 0
    for seed_index, seed in enumerate(EXPECTED_SEEDS):
        seed_deltas = {
            "pair_support": float(
                np.mean(
                    recomputed[seed_index, 7, pair_cohort, metric_index["pair_support"]]
                    - recomputed[seed_index, 1, pair_cohort, metric_index["pair_support"]]
                )
            ),
            "spce_at_10": float(
                np.mean(
                    recomputed[seed_index, 7, pair_cohort, metric_index["spce_at_10"]]
                    - recomputed[seed_index, 1, pair_cohort, metric_index["spce_at_10"]]
                )
            ),
            "positive_union_recall": float(
                np.mean(
                    recomputed[
                        seed_index, 7, relevance_cohort, metric_index["positive_union_recall"]
                    ]
                    - recomputed[
                        seed_index, 1, relevance_cohort, metric_index["positive_union_recall"]
                    ]
                )
            ),
            "ndcg_at_10": float(
                np.mean(
                    recomputed[seed_index, 7, relevance_cohort, metric_index["ndcg_at_10"]]
                    - recomputed[seed_index, 1, relevance_cohort, metric_index["ndcg_at_10"]]
                )
            ),
        }
        stable = bool(
            seed_deltas["pair_support"] > 0.0
            and seed_deltas["spce_at_10"] > 0.0
            and seed_deltas["positive_union_recall"] > 0.0
            and seed_deltas["ndcg_at_10"]
            >= float(gate7["minimum_ndcg_at_10_delta"])
        )
        stable_count += int(stable)
        seed_reports.append({"seed": seed, "deltas": seed_deltas, "stable": stable})
    g7 = bool(stable_count >= int(gate7["minimum_stable_seeds"]))

    latency_methods = _decode_strings(latency_arrays["methods"], "latency methods")
    if latency_methods not in (
        ("raw_single_centroid_hybrid", "facet_pref"),
        ("baseline", "facet_pref"),
    ):
        raise RuntimeError(f"Unexpected latency method labels: {latency_methods}")
    latency_seeds = tuple(int(value) for value in latency_arrays["seeds"].tolist())
    if latency_seeds != EXPECTED_SEEDS:
        raise RuntimeError("Latency seeds changed")
    if "durations_ms" in latency_arrays:
        durations = np.asarray(latency_arrays["durations_ms"], dtype=np.float64)
    elif "latency_ms" in latency_arrays:
        durations = np.asarray(latency_arrays["latency_ms"], dtype=np.float64)
    else:
        raise RuntimeError("Latency artifact has no raw millisecond durations")
    _require_shape(durations, (3, 2, 500, 3), "raw latency durations")
    _require_finite(durations, "raw latency durations")
    if np.any(durations <= 0.0):
        raise RuntimeError("Latency duration must be strictly positive")
    per_user_median = np.median(durations, axis=-1)
    p95 = np.quantile(per_user_median, 0.95, axis=-1)
    ratios = p95[:, 1] / np.maximum(p95[:, 0], 1.0e-12)
    if not np.array_equal(
        np.asarray(latency_arrays["p95_ms_by_seed_method"], dtype=np.float64), p95
    ) or not np.array_equal(
        np.asarray(latency_arrays["ratio_by_seed"], dtype=np.float64), ratios
    ):
        raise RuntimeError("Stored latency summary fails raw-duration replay")
    worst_facet = float(np.max(p95[:, 1]))
    worst_ratio = float(np.max(ratios))
    g8 = bool(
        worst_facet <= float(gate8["maximum_worst_seed_p95_latency_ms"])
        and worst_ratio <= float(gate8["maximum_worst_seed_p95_latency_ratio"])
    )

    g9 = bool(all(integrity_preconditions.values()))
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
    if tuple(gates) != GATE_NAMES:
        raise RuntimeError("Replayed gates are not exactly G1--G9")
    return {
        "gates": gates,
        "promising": bool(all(gates.values())),
        "candidate_invariants": candidate_audit,
        "bootstrap_deltas": deltas,
        "control_point_deltas": control_points,
        "support": {
            "R_uncapped_natural_pairs": training_pairs,
            "R_uncapped_pair_bearing_users": training_users,
            "T_fixed_pairs": test_pairs,
            "T_pair_bearing_users": test_pair_users,
            "common_pair_endpoint_cosupport": common_support,
            "changed_spce_pair_outcome_fraction": changed_fraction,
            "total_pair_seed_rows": total_pair_rows,
        },
        "seed_stability": {"stable_count": stable_count, "seeds": seed_reports},
        "latency": {
            "p95_ms_by_seed_and_method": p95.tolist(),
            "ratio_by_seed": ratios.tolist(),
            "worst_facet_pref_p95_ms": worst_facet,
            "worst_ratio": worst_ratio,
        },
        "raw_metric_replay_complete": True,
    }


def _extract_result_gates(result: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates: list[Any] = [result.get("gates")]
    promise_gate = result.get("promise_gate")
    if isinstance(promise_gate, Mapping):
        candidates.extend(
            [promise_gate.get("gates"), promise_gate.get("components"), promise_gate]
        )
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        if not all(name in candidate for name in GATE_NAMES):
            continue
        extracted: dict[str, Any] = {}
        for name in GATE_NAMES:
            value = candidate[name]
            if isinstance(value, bool) or value is None or isinstance(value, str):
                extracted[name] = value
            elif isinstance(value, Mapping):
                if "passed" in value:
                    extracted[name] = value["passed"]
                elif "status" in value:
                    extracted[name] = value["status"]
                else:
                    raise RuntimeError(f"Result {name} has no passed/status value")
            else:
                raise RuntimeError(f"Result {name} has an unsupported gate value")
        return extracted
    raise RuntimeError("Result contains no complete G1--G9 gate mapping")


def _extract_result_promising(result: Mapping[str, Any]) -> bool:
    if isinstance(result.get("PROMISING"), bool):
        return bool(result["PROMISING"])
    if isinstance(result.get("promising"), bool):
        return bool(result["promising"])
    promise_gate = result.get("promise_gate")
    if isinstance(promise_gate, Mapping):
        for key in ("passed", "promising", "PROMISING"):
            if isinstance(promise_gate.get(key), bool):
                return bool(promise_gate[key])
    raise RuntimeError("Result has no boolean PROMISING verdict")


def _validate_result_gate_equality(
    result: Mapping[str, Any], replayed: Mapping[str, bool]
) -> None:
    recorded = _extract_result_gates(result)
    for name in GATE_NAMES:
        if not isinstance(recorded[name], bool):
            raise RuntimeError(f"Post-T result {name} is not boolean")
        if bool(recorded[name]) != bool(replayed[name]):
            raise RuntimeError(
                f"Runner {name}={recorded[name]} disagrees with raw replay {replayed[name]}"
            )
    expected_promising = bool(all(replayed.values()))
    if _extract_result_promising(result) is not False:
        raise RuntimeError("Runner improperly claimed an authoritative PROMISING verdict")
    runner_candidate = result.get("runner_candidate_promising")
    promise_gate = result.get("promise_gate")
    if isinstance(promise_gate, Mapping):
        nested_candidate = promise_gate.get("runner_candidate_promising")
        if nested_candidate is not None and nested_candidate is not expected_promising:
            raise RuntimeError("Nested runner-candidate verdict disagrees with replay")
    if runner_candidate is not expected_promising:
        raise RuntimeError("Runner-candidate verdict disagrees with raw gate conjunction")


def _verify_pre_t_result(result: Mapping[str, Any], power_passed: bool) -> None:
    if power_passed:
        raise RuntimeError("Runner stopped before T even though replayed power passed")
    if result.get("termination_stage") != "pre_T_power_audit":
        raise RuntimeError("Pre-T result has the wrong termination stage")
    if result.get("test_opened") is not False:
        raise RuntimeError("Pre-T result does not attest test_opened=false")
    gates = _extract_result_gates(result)
    for name in ("G1", "G2", "G3", "G4", "G5", "G7", "G8"):
        if str(gates[name]).casefold() not in {
            "not_evaluated",
            "not-evaluated",
            "not evaluated",
            "none",
        } and gates[name] is not None:
            raise RuntimeError(f"Pre-T result fabricated a value for {name}")
    if gates["G6"] is not False:
        raise RuntimeError("Pre-T failed power audit must record G6=false")
    if gates["G9"] is not True:
        raise RuntimeError("Pre-T candidate lacks internal G9 provenance passage")
    if _extract_result_promising(result) is not False:
        raise RuntimeError("Pre-T failed power audit must record PROMISING=false")


def _verify_raw_temporal_evidence(
    validation_arrays: Mapping[str, Any],
    test_arrays: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    import numpy as np

    user_ids = np.asarray(validation_arrays["user_ids"], dtype=np.int64)
    if "historical_caper_user_ids" not in validation_arrays or "historical_ravel_user_ids" not in validation_arrays:
        raise RuntimeError("Raw cohort evidence lacks historical cohort user IDs")
    caper = np.asarray(validation_arrays["historical_caper_user_ids"], dtype=np.int64)
    ravel = np.asarray(validation_arrays["historical_ravel_user_ids"], dtype=np.int64)
    _require_shape(caper, (1000,), "CAPER historical cohort")
    _require_shape(ravel, (1000,), "RAVEL historical cohort")
    if len(np.unique(caper)) != 1000 or len(np.unique(ravel)) != 1000:
        raise RuntimeError("A historical cohort contains duplicate users")
    sets = [set(int(value) for value in cohort) for cohort in (caper, ravel, user_ids)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise RuntimeError("CAPER, RAVEL, and FACET-PREF cohorts overlap")

    for required_name in (
        "block_min_timestamps",
        "block_max_timestamps",
        "block_counts",
    ):
        if required_name not in validation_arrays:
            raise RuntimeError(f"Raw temporal evidence lacks {required_name}")
    minima = np.asarray(validation_arrays["block_min_timestamps"], dtype=np.int64)
    maxima = np.asarray(validation_arrays["block_max_timestamps"], dtype=np.int64)
    counts = np.asarray(validation_arrays["block_counts"], dtype=np.int64)
    _require_shape(minima, (2000, 4), "block minimum timestamps")
    _require_shape(maxima, (2000, 4), "block maximum timestamps")
    _require_shape(counts, (2000, 4), "block counts")
    if np.any(counts <= 0) or np.any(minima > maxima):
        raise RuntimeError("Chronological blocks are empty or malformed")
    if not np.all(maxima[:, :-1] < minima[:, 1:]):
        raise RuntimeError("Adjacent A/R/V/T blocks are not strictly chronological")

    def scalar_ns(arrays: Mapping[str, Any], key: str) -> int:
        if key not in arrays:
            raise RuntimeError(f"Raw chronology lacks {key}")
        values = np.asarray(arrays[key], dtype=np.int64).reshape(-1)
        if values.size != 1 or int(values[0]) <= 0:
            raise RuntimeError(f"Raw chronology field {key} is malformed")
        return int(values[0])

    r_published = scalar_ns(validation_arrays, "R_manifest_published_ns")
    r_joined = scalar_ns(validation_arrays, "R_target_joined_ns")
    v_published = scalar_ns(validation_arrays, "V_manifest_published_ns")
    v_relevance = scalar_ns(validation_arrays, "V_relevance_joined_ns")
    choices_frozen = scalar_ns(validation_arrays, "choices_frozen_ns")
    v_preference = scalar_ns(validation_arrays, "V_preference_joined_ns")
    if not (
        r_published
        < r_joined
        < v_published
        < v_relevance
        < choices_frozen
        < v_preference
    ):
        raise RuntimeError("R/V target-blind publication order failed")
    v_opened = np.asarray(validation_arrays["T_opened"], dtype=np.int64).reshape(-1)
    if v_opened.tolist() != [0]:
        raise RuntimeError("Validation evidence says T was already opened")
    if test_arrays is not None:
        if not np.array_equal(np.asarray(test_arrays["user_ids"], dtype=np.int64), user_ids):
            raise RuntimeError("Validation and test user manifests differ")
        t_published = scalar_ns(test_arrays, "T_manifest_published_ns")
        t_joined = scalar_ns(test_arrays, "T_target_joined_ns")
        if not (v_preference < t_published < t_joined):
            raise RuntimeError("T target-blind publication order failed")
        t_opened = np.asarray(test_arrays["T_opened"], dtype=np.int64).reshape(-1)
        if t_opened.tolist() != [1]:
            raise RuntimeError("Post-T evidence does not record one T opening")
    return {
        "caper_users": 1000,
        "ravel_users": 1000,
        "facet_pref_users": 2000,
        "pairwise_disjoint": True,
        "strict_block_chronology": True,
        "R_manifest_precedes_join": True,
        "V_manifest_precedes_relevance_and_preference": True,
        "test_manifest_precedes_join": test_arrays is not None,
    }


def _arrays_equal(left: Any, right: Any) -> bool:
    import numpy as np

    left_array = np.asarray(left)
    right_array = np.asarray(right)
    if left_array.shape != right_array.shape or left_array.dtype.kind != right_array.dtype.kind:
        return False
    if left_array.dtype.kind in {"f", "c"}:
        return bool(np.array_equal(left_array, right_array, equal_nan=True))
    return bool(np.array_equal(left_array, right_array))


def _verify_test_manifest_binding(
    result: Mapping[str, Any],
    arrays: Mapping[str, Any],
    run_directory: Path,
) -> Mapping[str, Any]:
    """Prove raw T arrays are exact copies of the durable pre-target manifests."""
    import numpy as np

    provenance = require_mapping(result.get("provenance"), "result.provenance")
    manifest_files = require_mapping(
        provenance.get("test_manifests"), "result test-manifest inventory"
    )
    integrity = require_mapping(result.get("integrity"), "result.integrity")
    manifest_hashes = require_mapping(
        integrity.get("test_manifest_sha256"), "result test-manifest hashes"
    )
    expected_seed_keys = {str(seed) for seed in EXPECTED_SEEDS}
    if set(map(str, manifest_files)) != expected_seed_keys or set(
        map(str, manifest_hashes)
    ) != expected_seed_keys:
        raise RuntimeError("T manifest inventory changed")
    raw_seed_keys = _decode_strings(
        arrays["test_manifest_seed_keys"], "raw T manifest seed keys"
    )
    raw_files = _decode_strings(arrays["test_manifest_files"], "raw T manifest files")
    raw_hashes = _decode_strings(arrays["test_manifest_sha256"], "raw T manifest hashes")
    expected_seed_order = tuple(str(seed) for seed in EXPECTED_SEEDS)
    if raw_seed_keys != expected_seed_order or not (
        len(raw_files) == len(raw_hashes) == 3
    ):
        raise RuntimeError("Raw T manifest inventory changed")
    for key, file_name, digest in zip(raw_seed_keys, raw_files, raw_hashes):
        if str(manifest_files[key]) != file_name or str(manifest_hashes[key]).lower() != digest:
            raise RuntimeError("Raw/result T manifest inventories disagree")
    expected_fields = {
        "user_ids",
        "candidates",
        "bpr_scores",
        "semantic_scores",
        "rankings",
        "final_scores",
        "facet_counts",
        "quota_utilization",
        "semantic_owners",
        "retrieval_diagnostics",
        "retrieval_diagnostic_names",
        "alpha_grid",
        "alpha_grid_rankings",
        "methods",
        "protocol_sha256",
        "stage",
        "seed",
        "bpr_variant",
        "histories_sha256",
        "target_outcomes_opened",
    }
    compared_fields = (
        "candidates",
        "rankings",
        "bpr_scores",
        "semantic_scores",
        "final_scores",
        "facet_counts",
        "quota_utilization",
        "semantic_owners",
        "retrieval_diagnostics",
    )
    raw_methods = _decode_strings(arrays["methods"], "raw T methods")
    raw_user_ids = np.asarray(arrays["user_ids"], dtype=np.int64)
    selected_variant = _decode_strings(
        np.asarray(arrays["selected_bpr_variant"]).reshape(-1),
        "raw T selected BPR variant",
    )[0]
    raw_protocol = _decode_strings(arrays["protocol_sha256"], "raw T protocol")
    diagnostic_names = _decode_strings(
        arrays["retrieval_diagnostic_names"], "raw T retrieval diagnostics"
    )
    expected_diagnostics = (
        "pre_exclusion_cross_facet_overlap",
        "eligible_cross_facet_overlap",
        "higher_facet_duplicates_removed",
        "lower_owner_violation_count",
        "eligible_facet0_count",
        "eligible_facet1_count",
    )
    if raw_methods != EXPECTED_METHODS or diagnostic_names != expected_diagnostics:
        raise RuntimeError("Raw T method/diagnostic schema changed")
    if np.any(np.asarray(arrays["retrieval_diagnostics"])[..., 3] != 0):
        raise RuntimeError("Raw T evidence contains a lower-owner violation")
    owner_report = _verify_semantic_owner_evidence(
        np.asarray(arrays["facet_counts"])[0],
        np.asarray(arrays["quota_utilization"])[0],
        np.asarray(arrays["retrieval_diagnostics"])[0],
        np.asarray(arrays["semantic_owners"])[0],
        "raw T seed 0",
    )
    for seed_row in (1, 2):
        _verify_semantic_owner_evidence(
            np.asarray(arrays["facet_counts"])[seed_row],
            np.asarray(arrays["quota_utilization"])[seed_row],
            np.asarray(arrays["retrieval_diagnostics"])[seed_row],
            np.asarray(arrays["semantic_owners"])[seed_row],
            f"raw T seed {seed_row}",
        )
    verified_hashes: dict[str, str] = {}
    for seed_row, seed in enumerate(EXPECTED_SEEDS):
        key = str(seed)
        file_name = str(manifest_files[key])
        expected_hash = str(manifest_hashes[key]).lower()
        if not is_sha256(expected_hash):
            raise RuntimeError(f"Malformed T manifest hash: {seed}")
        path = contained_file(run_directory, file_name, f"T manifest seed {seed}")
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"T manifest hash mismatch: {seed}")
        manifest = _load_npz(path, tuple(expected_fields), f"T manifest seed {seed}")
        if set(manifest) != expected_fields:
            raise RuntimeError(f"T manifest has unexpected fields: {seed}")
        if _decode_strings(manifest["stage"], "T manifest stage") != ("T",):
            raise RuntimeError("A test manifest is not stage T")
        if np.asarray(manifest["target_outcomes_opened"]).reshape(-1).tolist() != [0]:
            raise RuntimeError("A T manifest was published after target opening")
        if int(np.asarray(manifest["seed"]).reshape(-1)[0]) != seed:
            raise RuntimeError("T manifest seed mismatch")
        if _decode_strings(manifest["bpr_variant"], "T manifest BPR variant") != (
            selected_variant,
        ):
            raise RuntimeError("T manifest BPR variant differs from validation lock")
        if _decode_strings(manifest["methods"], "T manifest methods") != raw_methods:
            raise RuntimeError("T manifest method list differs from raw T evidence")
        if _decode_strings(manifest["protocol_sha256"], "T manifest protocol") != raw_protocol:
            raise RuntimeError("T manifest protocol fingerprint differs from raw T evidence")
        if not np.array_equal(np.asarray(manifest["user_ids"], dtype=np.int64), raw_user_ids):
            raise RuntimeError("T manifest cohort differs from raw T evidence")
        if np.asarray(manifest["alpha_grid"]).size != 0 or np.asarray(
            manifest["alpha_grid_rankings"]
        ).shape[0] != 0:
            raise RuntimeError("T manifest unexpectedly contains a validation alpha grid")
        for field in compared_fields:
            if not _arrays_equal(manifest[field], np.asarray(arrays[field])[seed_row]):
                raise RuntimeError(f"Raw T field diverges from target-blind manifest: {field}")
        if _decode_strings(
            manifest["retrieval_diagnostic_names"], "T manifest retrieval diagnostics"
        ) != diagnostic_names:
            raise RuntimeError("T manifest retrieval diagnostic names changed")
        verified_hashes[key] = expected_hash

    # Selected BPR and both raw hybrids are seed-invariant by construction.
    for field in compared_fields:
        values = np.asarray(arrays[field])
        for method_index in (0, 1, 2):
            if not _arrays_equal(values[0, method_index], values[1, method_index]) or not _arrays_equal(
                values[0, method_index], values[2, method_index]
            ):
                raise RuntimeError(
                    f"Seed-invariant raw T method changed: {field}/{EXPECTED_METHODS[method_index]}"
                )
    return {
        "manifest_count": 3,
        "manifest_sha256": verified_hashes,
        "target_outcomes_opened": False,
        "raw_test_arrays_exactly_bound": True,
        "raw_methods_seed_invariant": True,
        "semantic_owner_replay": owner_report,
    }


def _verify_immutable_artifacts(
    result: Mapping[str, Any], run_directory: Path
) -> Mapping[str, Any]:
    integrity = require_mapping(result.get("integrity"), "result.integrity")
    records = require_sequence(
        integrity.get("immutable_artifacts"), "result immutable artifact records"
    )
    composite = require_mapping(
        integrity.get("matrix_index_hashes"), "result matrix/index composite records"
    )
    required_kinds = {"semantic_matrix", "semantic_index", "bpr_matrix", "bpr_index"}
    verified_kinds: set[str] = set()
    verified: dict[str, Any] = {}
    for raw_record in records:
        record = require_mapping(raw_record, "immutable artifact record")
        name = str(record.get("name", ""))
        if not name or name in verified:
            raise RuntimeError("Immutable artifact names are empty or duplicated")
        before = str(record.get("before_sha256", record.get("before", ""))).lower()
        after = str(record.get("after_sha256", record.get("after", ""))).lower()
        memory_before = str(record.get("memory_before", "")).lower()
        memory_after = str(record.get("memory_after", "")).lower()
        relative = str(record.get("file", record.get("relative_path", "")))
        kind = str(record.get("kind", name))
        if (
            not is_sha256(before)
            or not is_sha256(after)
            or not is_sha256(memory_before)
            or not is_sha256(memory_after)
            or before != after
            or memory_before != memory_after
            or record.get("unchanged") is not True
        ):
            raise RuntimeError(f"Immutable artifact hash changed: {name}")
        path = contained_file(run_directory, relative, f"immutable artifact {name}")
        if sha256_file(path) != before:
            raise RuntimeError(f"Immutable artifact file hash mismatch: {name}")
        if kind.endswith("_matrix"):
            import numpy as np

            with path.open("rb") as handle:
                matrix = np.load(handle, allow_pickle=False)
            reconstructed_memory = sha256_bytes(
                np.ascontiguousarray(matrix).tobytes(order="C")
            )
        elif kind.endswith("_index"):
            try:
                import faiss
                import numpy as np
            except ImportError as exc:
                raise RuntimeError("FAISS is required to replay immutable index memory") from exc
            index = faiss.read_index(str(path))
            reconstructed_memory = sha256_bytes(
                np.asarray(faiss.serialize_index(index), dtype=np.uint8).tobytes()
            )
        else:
            raise RuntimeError(f"Unknown immutable artifact kind: {kind}")
        if reconstructed_memory != memory_before:
            raise RuntimeError(f"Immutable artifact memory hash replay failed: {name}")
        verified_kinds.add(kind)
        verified[str(name)] = {
            "kind": kind,
            "file": relative,
            "sha256": before,
            "memory_sha256": memory_before,
        }
    missing = required_kinds - verified_kinds
    if missing:
        raise RuntimeError(f"Immutable artifact evidence lacks kinds: {sorted(missing)}")
    if set(composite) != {"semantic", "bpr_implicit", "bpr_rating_aware"}:
        raise RuntimeError("Composite matrix/index inventory changed")
    for name, raw_record in composite.items():
        record = require_mapping(raw_record, f"composite immutable record {name}")
        for prefix in ("matrix", "index"):
            file_before = str(record.get(f"{prefix}_file_before", "")).lower()
            file_after = str(record.get(f"{prefix}_file_after", "")).lower()
            memory_before = str(record.get(f"{prefix}_memory_before", "")).lower()
            memory_after = str(record.get(f"{prefix}_memory_after", "")).lower()
            if (
                not all(
                    is_sha256(value)
                    for value in (file_before, file_after, memory_before, memory_after)
                )
                or file_before != file_after
                or memory_before != memory_after
            ):
                raise RuntimeError(f"Composite immutable hash changed: {name}/{prefix}")
        if record.get("unchanged") is not True:
            raise RuntimeError(f"Composite immutable record is not unchanged: {name}")
    return {"verified": verified, "matrix_index_immutable": True}


def _verify_protocol_and_execution_fingerprints(
    *,
    closure: CandidateClosure,
    result: Mapping[str, Any],
    validation_arrays: Mapping[str, Any],
    test_arrays: Mapping[str, Any] | None,
    latency_arrays: Mapping[str, Any] | None,
    config: Mapping[str, Any],
    selection: Mapping[str, Any],
    expected_archive_sha256: str,
) -> Mapping[str, Any]:
    import numpy as np

    source_hashes = require_mapping(
        closure.candidate["source_sha256"], "candidate source hashes"
    )
    protocol_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "protocol_name": config["protocol_name"],
                "source_sha256": dict(source_hashes),
            }
        )
    )
    if not is_sha256(protocol_sha256):
        raise RuntimeError("Recomputed protocol fingerprint is malformed")

    def require_protocol(array_map: Mapping[str, Any], label: str) -> None:
        recorded = _decode_strings(array_map["protocol_sha256"], f"{label} protocol")
        if recorded != (protocol_sha256,):
            raise RuntimeError(f"{label} protocol fingerprint mismatch")

    require_protocol(validation_arrays, "raw validation")
    if test_arrays is not None:
        require_protocol(test_arrays, "raw test")
    if latency_arrays is not None:
        require_protocol(latency_arrays, "latency")
    if str(result.get("protocol_sha256", "")).lower() != protocol_sha256:
        raise RuntimeError("Result protocol fingerprint mismatch")
    user_ids = sorted(int(value) for value in np.asarray(validation_arrays["user_ids"]).tolist())
    facet_user_ids_sha256 = sha256_bytes(canonical_json_bytes(user_ids))
    integrity = require_mapping(result.get("integrity"), "result.integrity")
    cohort = require_mapping(integrity.get("cohort"), "result integrity cohort")
    if str(cohort.get("facet_user_ids_sha256", "")).lower() != facet_user_ids_sha256:
        raise RuntimeError("Result FACET cohort fingerprint mismatch")
    selected_variant = str(selection["selected_bpr_variant"])
    selected_alpha = float(selection["selected_alpha"])
    result_selection = require_mapping(result.get("selection_locks"), "result selection locks")
    if str(result_selection.get("selected_bpr_variant", "")) != selected_variant or not math.isclose(
        float(result_selection.get("selected_alpha", float("nan"))),
        selected_alpha,
        rel_tol=0.0,
        abs_tol=1e-7,
    ):
        raise RuntimeError("Result selection locks disagree with raw V replay")
    execution_sha256 = sha256_bytes(
        canonical_json_bytes(
            {
                "protocol_sha256": protocol_sha256,
                "dataset_sha256": expected_archive_sha256,
                "facet_user_ids_sha256": facet_user_ids_sha256,
                "selected_bpr_variant": selected_variant,
                "selected_alpha": selected_alpha,
                "optimization_seeds": list(EXPECTED_SEEDS),
            }
        )
    )
    if str(closure.candidate.get("execution_fingerprint_sha256", "")).lower() != execution_sha256:
        raise RuntimeError("Candidate execution fingerprint mismatch")
    if str(result.get("execution_fingerprint_sha256", "")).lower() != execution_sha256:
        raise RuntimeError("Result execution fingerprint mismatch")
    return {
        "protocol_sha256": protocol_sha256,
        "facet_user_ids_sha256": facet_user_ids_sha256,
        "execution_fingerprint_sha256": execution_sha256,
        "all_fingerprints_independently_recomputed": True,
    }


@dataclass(frozen=True)
class CandidateClosure:
    candidate_path: Path
    candidate: Mapping[str, Any]
    result_path: Path
    validation_path: Path
    test_path: Path | None
    latency_path: Path | None
    runner_ledger: Path
    runner_lock: Path
    runner_pid: int
    termination_stage: str
    test_opened: bool
    artifact_hashes: Mapping[str, str]


def verify_candidate_closure(
    *,
    run_directory: Path,
    candidate_path: Path,
    expected_hashes: Mapping[str, str],
    expected_environment: Mapping[str, str],
    expected_archive_sha256: str,
) -> CandidateClosure:
    candidate = read_json_mapping(candidate_path, "runner completion candidate")
    if candidate.get("schema") != "facet-pref-runner-completion-candidate-v1":
        raise RuntimeError("Unexpected runner completion candidate schema")
    if Path(str(candidate.get("run_directory", ""))).resolve() != run_directory.resolve():
        raise RuntimeError("Runner candidate names a different run directory")
    runner_pid = int(candidate.get("pid", -1))
    if runner_pid <= 0 or pid_is_running(runner_pid):
        raise RuntimeError(f"Runner PID is active or invalid: {runner_pid}")
    if candidate.get("runner_lock_release_pending") is not True:
        raise RuntimeError("Runner did not declare lock release pending")
    if candidate.get("external_post_exit_verification_required") is not True:
        raise RuntimeError("Runner did not require external post-exit verification")
    runner_lock_raw = Path(str(candidate.get("runner_lock", "")))
    runner_lock = (
        runner_lock_raw.resolve()
        if runner_lock_raw.is_absolute()
        else (run_directory / runner_lock_raw).resolve()
    )
    if runner_lock.exists():
        raise RuntimeError(f"Runner lock remains after process exit: {runner_lock}")

    source_hashes = require_mapping(candidate.get("source_sha256"), "candidate.source_sha256")
    expected_source_names = {
        "runner",
        "config",
        "protocol",
        "caper_dependency",
        "research_question",
        "cycle4_survey",
        "architecture_facet_pref",
    }
    if set(source_hashes) != expected_source_names:
        raise RuntimeError("Candidate source-binding inventory changed")
    for name in sorted(expected_source_names):
        actual = str(source_hashes.get(name, "")).lower()
        if actual != str(expected_hashes[name]).lower():
            raise RuntimeError(f"Candidate {name} source binding mismatch")
    if str(candidate.get("dataset_archive_sha256", "")).lower() != expected_archive_sha256:
        raise RuntimeError("Candidate dataset archive SHA-256 mismatch")
    if str(candidate.get("python_executable_sha256", "")).lower() != str(
        expected_hashes["python_executable"]
    ).lower():
        raise RuntimeError("Candidate interpreter SHA-256 mismatch")
    environment_path = contained_file(
        run_directory,
        str(candidate.get("environment_file", "")),
        "runner environment record",
    )
    environment_file_sha256 = sha256_file(environment_path)
    if environment_file_sha256 != str(candidate.get("environment_sha256", "")).lower():
        raise RuntimeError("Candidate environment-file hash mismatch")
    environment_record = read_json_mapping(environment_path, "runner environment record")
    if environment_record.get("schema") != "facet-pref-environment-v1":
        raise RuntimeError("Unexpected runner environment schema")
    if str(environment_record.get("python_executable_sha256", "")).lower() != str(
        expected_hashes["python_executable"]
    ).lower():
        raise RuntimeError("Runner environment/interpreter binding mismatch")
    recorded_thread_environment = require_mapping(
        environment_record.get("thread_environment"), "runner thread environment"
    )
    fixed_recorded = require_mapping(
        environment_record.get("fixed_execution_environment"),
        "runner fixed execution environment",
    )
    observed_recorded = require_mapping(
        environment_record.get("fixed_execution_environment_observed"),
        "runner observed execution environment",
    )
    if dict(fixed_recorded) != dict(expected_environment):
        raise RuntimeError("Runner fixed-environment contract differs from launcher")
    if dict(observed_recorded) != dict(expected_environment):
        raise RuntimeError("Runner did not observe the complete fixed environment")
    if dict(recorded_thread_environment) != dict(expected_environment):
        raise RuntimeError("Runner thread/environment record is incomplete or changed")
    if environment_record.get("python_dont_write_bytecode") is not True:
        raise RuntimeError("Runner did not honor -B/PYTHONDONTWRITEBYTECODE")
    if int(environment_record.get("torch_intraop_threads", -1)) != 1 or int(
        environment_record.get("torch_interop_threads", -1)
    ) != 1:
        raise RuntimeError("Runner Torch thread pools were not single-threaded")
    snapshots = require_mapping(
        environment_record.get("source_snapshots"), "runner source snapshots"
    )
    snapshot_labels = {
        "runner",
        "protocol",
        "caper_dependency",
        "research_question",
        "cycle4_survey",
        "architecture_facet_pref",
    }
    if set(snapshots) != snapshot_labels:
        raise RuntimeError("Runner source-snapshot inventory changed")
    for label in sorted(snapshot_labels):
        record = require_mapping(snapshots[label], f"source snapshot {label}")
        path = contained_file(
            run_directory, str(record.get("file", "")), f"source snapshot {label}"
        )
        digest = sha256_file(path)
        if digest != str(record.get("sha256", "")).lower() or digest != str(
            source_hashes[label]
        ).lower():
            raise RuntimeError(f"Runner source snapshot hash mismatch: {label}")
    effective_configs = list(run_directory.glob("effective_config_*_seq001.json"))
    if len(effective_configs) != 1 or sha256_file(effective_configs[0]) != str(
        source_hashes["config"]
    ).lower():
        raise RuntimeError("Runner effective-config snapshot mismatch")
    execution_hash = candidate.get("execution_fingerprint_sha256")
    if not is_sha256(execution_hash):
        raise RuntimeError("Malformed execution fingerprint")

    runner_ledger = contained_file(
        run_directory,
        str(candidate.get("asynchronous_error_ledger", "")),
        "runner asynchronous-error ledger",
    )
    if runner_ledger.stat().st_size != 0 or sha256_file(runner_ledger) != EMPTY_SHA256:
        raise RuntimeError("Runner asynchronous-error ledger is nonempty")
    recorded_ledger_hash = candidate.get("asynchronous_error_ledger_sha256")
    if recorded_ledger_hash is not None and str(recorded_ledger_hash).lower() != EMPTY_SHA256:
        raise RuntimeError("Candidate records a nonempty runner ledger hash")

    artifact_raw = require_mapping(candidate.get("artifact_sha256"), "candidate.artifact_sha256")
    artifact_hashes: dict[str, str] = {}
    for relative, expected in artifact_raw.items():
        name = str(relative)
        digest = str(expected).lower()
        if not is_sha256(digest):
            raise RuntimeError(f"Malformed recursive artifact hash: {name}")
        path = contained_file(run_directory, name, "candidate-bound artifact")
        if sha256_file(path) != digest:
            raise RuntimeError(f"Candidate-bound artifact hash mismatch: {name}")
        artifact_hashes[name] = digest
    actual_manifest = file_hash_manifest(run_directory, excluded=(candidate_path,))
    if dict(actual_manifest) != artifact_hashes:
        missing = sorted(set(artifact_hashes) - set(actual_manifest))
        extra = sorted(set(actual_manifest) - set(artifact_hashes))
        changed = sorted(
            name
            for name in set(actual_manifest) & set(artifact_hashes)
            if actual_manifest[name] != artifact_hashes[name]
        )
        raise RuntimeError(
            f"Recursive candidate closure mismatch: missing={missing}, extra={extra}, changed={changed}"
        )

    def candidate_file(field: str, hash_field: str, label: str) -> Path:
        path = contained_file(run_directory, str(candidate.get(field, "")), label)
        if sha256_file(path) != str(candidate.get(hash_field, "")).lower():
            raise RuntimeError(f"{label} dedicated hash mismatch")
        return path

    result_path = candidate_file("result_file", "result_sha256", "result file")
    validation_path = candidate_file(
        "raw_validation_power_file",
        "raw_validation_power_sha256",
        "raw validation power artifact",
    )
    termination_stage = str(candidate.get("termination_stage", ""))
    test_opened = candidate.get("test_opened")
    if not isinstance(test_opened, bool):
        raise RuntimeError("Candidate test_opened must be boolean")
    test_path: Path | None = None
    latency_path: Path | None = None
    if termination_stage == "pre_T_power_audit":
        if test_opened:
            raise RuntimeError("Pre-T candidate says test_opened=true")
        forbidden = {
            "raw_test_arrays_file",
            "raw_test_arrays_sha256",
            "latency_file",
            "latency_sha256",
        }
        if forbidden & set(candidate):
            raise RuntimeError("Pre-T candidate names a T or latency artifact")
        forbidden_names = [
            name
            for name in artifact_hashes
            if "raw_test" in name.casefold()
            or "latency" in name.casefold()
            or "t_manifest" in name.casefold()
        ]
        if forbidden_names:
            raise RuntimeError(f"Pre-T closure contains forbidden T artifacts: {forbidden_names}")
    elif termination_stage == "post_T_all_gates":
        if not test_opened:
            raise RuntimeError("Post-T candidate says test_opened=false")
        test_path = candidate_file(
            "raw_test_arrays_file", "raw_test_arrays_sha256", "raw test artifact"
        )
        latency_path = candidate_file("latency_file", "latency_sha256", "latency artifact")
    else:
        raise RuntimeError(f"Unknown runner termination stage: {termination_stage!r}")

    return CandidateClosure(
        candidate_path=candidate_path,
        candidate=candidate,
        result_path=result_path,
        validation_path=validation_path,
        test_path=test_path,
        latency_path=latency_path,
        runner_ledger=runner_ledger,
        runner_lock=runner_lock,
        runner_pid=runner_pid,
        termination_stage=termination_stage,
        test_opened=test_opened,
        artifact_hashes=artifact_hashes,
    )


def execution_environment() -> Mapping[str, str]:
    result = {key: "1" for key in THREAD_VARIABLES}
    result.update(
        {
            "CUDA_VISIBLE_DEVICES": "-1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TRANSFORMERS_VERBOSITY": "error",
            "TOKENIZERS_PARALLELISM": "false",
            "HF_HUB_DISABLE_PROGRESS_BARS": "1",
            "TQDM_DISABLE": "1",
            "PYTHONHASHSEED": "20260817",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return result


def execution_environment_sha256(values: Mapping[str, str]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(values)))


def verify_outer_authorization(
    *,
    outer_lock: Path,
    owner_pid: int,
    token: str,
) -> Mapping[str, Any]:
    if owner_pid <= 0 or not pid_is_running(owner_pid):
        raise RuntimeError("Outer-launch owner PID is not active during verification")
    record = read_json_mapping(outer_lock, "outer-launch lock")
    if record.get("role") != "outer-launch":
        raise RuntimeError("Outer-launch lock role changed")
    if int(record.get("pid", -1)) != owner_pid:
        raise RuntimeError("Outer-launch lock owner PID mismatch")
    if record.get("token_sha256") != sha256_text(token):
        raise RuntimeError("Outer-launch lock authorization token mismatch")
    return {
        "outer_lock": str(outer_lock.resolve()),
        "outer_owner_pid": owner_pid,
        "outer_owner_active": True,
        "outer_token_sha256": sha256_text(token),
        "outer_lock_held": True,
    }


def verify_launch_binding(
    *,
    args: argparse.Namespace,
    project_root: Path,
    expected_environment: Mapping[str, str],
) -> Mapping[str, Any]:
    launcher = Path(__file__).resolve()
    runner = args.runner.resolve()
    config = args.config.resolve()
    protocol = args.protocol.resolve()
    locked_config = (
        project_root / "src" / "configs" / "facet_pref_poc_ml1m_v1.json"
    ).resolve()
    locked_protocol = (
        project_root / "experiments" / "facet-pref-protocol-v1.md"
    ).resolve()
    if config != locked_config or protocol != locked_protocol:
        raise RuntimeError("Verifier accepts only the project-locked config/protocol paths")
    caper_dependency = (project_root / "src" / "caper_poc.py").resolve()
    research_question = (project_root / "research-question-cycle4.md").resolve()
    cycle4_survey = (
        project_root / "literature" / "cycle4-survey-and-ideation.md"
    ).resolve()
    architecture = (project_root / "architecture-facet-pref.md").resolve()
    python_executable = Path(sys.executable).absolute()
    launch_record = args.launch_record.resolve()
    for path, label in (
        (launcher, "launcher/verifier source"),
        (runner, "runner source"),
        (config, "configuration"),
        (protocol, "protocol"),
        (caper_dependency, "CAPER dependency"),
        (research_question, "cycle-4 research question"),
        (cycle4_survey, "cycle-4 survey"),
        (architecture, "FACET-PREF architecture"),
        (python_executable, "Python interpreter"),
        (launch_record, "launch record"),
        (args.runner_stdout.resolve(), "runner stdout"),
        (args.runner_stderr.resolve(), "runner stderr"),
    ):
        if not path.is_file():
            raise RuntimeError(f"Missing {label}: {path}")
    actual_hashes = {
        "launcher": sha256_file(launcher),
        "runner": sha256_file(runner),
        "config": sha256_file(config),
        "protocol": sha256_file(protocol),
        "caper_dependency": sha256_file(caper_dependency),
        "research_question": sha256_file(research_question),
        "cycle4_survey": sha256_file(cycle4_survey),
        "architecture_facet_pref": sha256_file(architecture),
        "python_executable": sha256_file(python_executable),
    }
    if actual_hashes["launcher"] != str(args.expected_launcher_sha256).lower():
        raise RuntimeError("Verifier/launcher source changed after launch")
    record = read_json_mapping(launch_record, "launch record")
    if record.get("schema") != "facet-pref-external-launch-v1":
        raise RuntimeError("Unexpected launch record schema")
    recorded_hashes = require_mapping(record.get("source_sha256"), "launch source hashes")
    for name, actual in actual_hashes.items():
        if str(recorded_hashes.get(name, "")).lower() != actual:
            raise RuntimeError(f"Launch record {name} hash mismatch")
    if Path(str(record.get("project_root", ""))).resolve() != project_root.resolve():
        raise RuntimeError("Launch record project root changed")
    if Path(str(record.get("run_directory", ""))).resolve() != args.verify_run_directory.resolve():
        raise RuntimeError("Launch record run directory changed")
    if pid_is_running(int(args.launcher_child_pid)):
        raise RuntimeError("Waited launcher child PID is still active")
    expected_environment_hash = execution_environment_sha256(expected_environment)
    if record.get("execution_environment_sha256") != expected_environment_hash:
        raise RuntimeError("Launch record environment fingerprint mismatch")
    if require_mapping(record.get("execution_environment"), "launch environment") != dict(
        expected_environment
    ):
        raise RuntimeError("Launch record environment values changed")
    local_archive_hash: str | None = None
    if args.local_dataset_archive is not None:
        archive = args.local_dataset_archive.resolve()
        if not archive.is_file():
            raise RuntimeError(f"Local dataset archive vanished: {archive}")
        local_archive_hash = sha256_file(archive)
    if record.get("local_dataset_archive_sha256") != local_archive_hash:
        raise RuntimeError("Launch record local-archive binding mismatch")
    return {
        "source_sha256": actual_hashes,
        "execution_environment_sha256": expected_environment_hash,
        "local_dataset_archive_sha256": local_archive_hash,
        "launch_record_sha256": sha256_file(launch_record),
        "launcher_child_pid": int(args.launcher_child_pid),
        "launcher_child_process_has_exited": True,
    }


def _result_provenance(
    result: Mapping[str, Any],
    expected_archive_sha256: str,
    temporal_report: Mapping[str, Any],
    run_directory: Path,
) -> Mapping[str, Any]:
    integrity = require_mapping(result.get("integrity"), "result.integrity")
    archive_hash = str(
        integrity.get("dataset_archive_sha256", integrity.get("archive_sha256", ""))
    ).lower()
    if archive_hash != expected_archive_sha256:
        raise RuntimeError("Result archive authentication mismatch")
    archive_file = contained_file(
        run_directory, "ml-1m.sha-locked.zip", "SHA-locked source archive"
    )
    if sha256_file(archive_file) != expected_archive_sha256:
        raise RuntimeError("Run-directory source archive hash changed")
    extraction_hashes = require_mapping(
        integrity.get("extraction_sha256"), "result extraction hashes"
    )
    extraction_files = require_mapping(
        integrity.get("extraction_files"), "result extraction files"
    )
    if set(extraction_hashes) != {"ratings.dat", "movies.dat"} or set(
        extraction_files
    ) != {"ratings.dat", "movies.dat"}:
        raise RuntimeError("Extraction provenance inventory changed")
    verified_extraction: dict[str, Any] = {}
    for name in ("ratings.dat", "movies.dat"):
        expected = str(extraction_hashes[name]).lower()
        if not is_sha256(expected):
            raise RuntimeError(f"Malformed extraction hash: {name}")
        record = require_mapping(extraction_files[name], f"extraction file {name}")
        if str(record.get("sha256", "")).lower() != expected:
            raise RuntimeError(f"Extraction record/hash mismatch: {name}")
        path = contained_file(
            run_directory, str(record.get("file", "")), f"extracted {name}"
        )
        if sha256_file(path) != expected:
            raise RuntimeError(f"Extracted source file hash changed: {name}")
        verified_extraction[name] = {"file": safe_relative(path, run_directory), "sha256": expected}
    if temporal_report.get("pairwise_disjoint") is not True or temporal_report.get(
        "strict_block_chronology"
    ) is not True:
        raise RuntimeError("Raw cohort/temporal replay is incomplete")
    return {
        "dataset_archive_sha256": archive_hash,
        "extraction_sha256": dict(extraction_hashes),
        "extraction_files": verified_extraction,
        "target_injection_count": 0,
        "cohort_and_temporal_raw_replay": True,
    }


def _test_target_not_in_prefix(test_arrays: Mapping[str, Any]) -> bool:
    import numpy as np

    prefixes = np.asarray(test_arrays["prefix_items"], dtype=np.int64)
    prefix_counts = np.asarray(test_arrays["prefix_counts"], dtype=np.int64)
    if prefixes.ndim == 3:
        if not np.array_equal(prefixes[0], prefixes[1]) or not np.array_equal(
            prefixes[0], prefixes[2]
        ):
            raise RuntimeError("T prefix histories changed across seeds")
        prefixes = prefixes[0]
    if prefix_counts.ndim == 2:
        if not np.array_equal(prefix_counts[0], prefix_counts[1]) or not np.array_equal(
            prefix_counts[0], prefix_counts[2]
        ):
            raise RuntimeError("T prefix counts changed across seeds")
        prefix_counts = prefix_counts[0]
    test_items = np.asarray(test_arrays["test_event_items"], dtype=np.int64)
    test_counts = np.asarray(test_arrays["test_event_counts"], dtype=np.int64)
    for user_row in range(len(prefixes)):
        prefix = set(int(value) for value in prefixes[user_row, : int(prefix_counts[user_row])])
        targets = set(int(value) for value in test_items[user_row, : int(test_counts[user_row])])
        if prefix & targets:
            raise RuntimeError("A current T target appears in its prefix history")
    return True


def _rederive_post_t_cohort_from_authenticated_sources(
    *,
    validation_arrays: Mapping[str, Any],
    test_arrays: Mapping[str, Any],
    provenance: Mapping[str, Any],
    config: Mapping[str, Any],
    run_directory: Path,
) -> Mapping[str, Any]:
    """Independently parse authenticated ML-1M and reproduce cohort/splits.

    This is called only after the registered T opening.  The pre-T negative
    path deliberately does not inspect sealed T identities or ratings.
    """
    import numpy as np

    extraction_files = require_mapping(
        provenance["extraction_files"], "verified extraction files"
    )
    movies_path = contained_file(
        run_directory,
        str(require_mapping(extraction_files["movies.dat"], "movies extraction")["file"]),
        "authenticated movies.dat",
    )
    ratings_path = contained_file(
        run_directory,
        str(require_mapping(extraction_files["ratings.dat"], "ratings extraction")["file"]),
        "authenticated ratings.dat",
    )
    movie_id_values: list[int] = []
    with movies_path.open("r", encoding="latin-1", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            fields = line.rstrip("\r\n").split("::")
            if len(fields) != 3:
                raise RuntimeError(f"Malformed authenticated movies row {line_number}")
            movie_id_values.append(int(fields[0]))
    movie_ids = np.asarray(sorted(movie_id_values), dtype=np.int64)
    if len(np.unique(movie_ids)) != len(movie_ids):
        raise RuntimeError("Authenticated movie catalog has duplicate IDs")
    if not np.array_equal(
        movie_ids, np.asarray(validation_arrays["movie_ids"], dtype=np.int64)
    ) or not np.array_equal(movie_ids, np.asarray(test_arrays["movie_ids"], dtype=np.int64)):
        raise RuntimeError("Raw evidence catalog differs from authenticated movies.dat")
    item_to_index = {int(movie_id): index for index, movie_id in enumerate(movie_ids)}
    grouped: dict[int, list[tuple[int, int, int, int]]] = {}
    with ratings_path.open("r", encoding="ascii", newline="") as handle:
        for ordinal, line in enumerate(handle):
            fields = line.rstrip("\r\n").split("::")
            if len(fields) != 4:
                raise RuntimeError(f"Malformed authenticated ratings row {ordinal + 1}")
            user_id, movie_id, rating, timestamp = map(int, fields)
            if movie_id not in item_to_index:
                raise RuntimeError("Authenticated rating references a missing movie")
            grouped.setdefault(user_id, []).append(
                (item_to_index[movie_id], rating, timestamp, ordinal)
            )

    dataset = require_mapping(config["dataset"], "config.dataset")
    eligible: list[tuple[int, tuple[Any, Any, Any, Any]]] = []
    for user_id in sorted(grouped):
        events = sorted(grouped[user_id], key=lambda value: (value[2], value[3]))
        if len(events) < int(dataset["minimum_total_events"]):
            continue
        groups: list[list[tuple[int, int, int, int]]] = []
        for event in events:
            if not groups or groups[-1][0][2] != event[2]:
                groups.append([])
            groups[-1].append(event)
        if len(groups) < int(dataset["minimum_timestamp_groups"]):
            continue
        cumulative = np.cumsum([len(group) for group in groups])

        def nearest(target: float, minimum: int, maximum: int) -> int:
            choices = np.arange(minimum, maximum + 1, dtype=np.int64)
            distances = np.abs(cumulative[choices - 1] - target)
            return int(choices[int(np.argmin(distances))])

        total = len(events)
        first = nearest(0.6 * total, 1, len(groups) - 3)
        second = nearest(0.8 * total, first + 1, len(groups) - 2)
        third = nearest(0.9 * total, second + 1, len(groups) - 1)

        def flatten(start: int, stop: int) -> tuple[tuple[int, int, int, int], ...]:
            return tuple(event for group in groups[start:stop] for event in group)

        blocks = (
            flatten(0, first),
            flatten(first, second),
            flatten(second, third),
            flatten(third, len(groups)),
        )
        if len(blocks[0]) < int(dataset["minimum_A_events"]):
            continue
        positives_a = {
            event[0]
            for event in blocks[0]
            if event[1] >= int(dataset["positive_rating_min"])
        }
        if len(positives_a) < int(dataset["minimum_distinct_positive_A_items"]):
            continue
        if not any(
            event[1] >= int(dataset["positive_rating_min"]) for event in blocks[2]
        ) or not any(
            event[1] >= int(dataset["positive_rating_min"]) for event in blocks[3]
        ):
            continue
        eligible.append((user_id, blocks))
    seed = int(config["determinism_seed"])
    ordered = sorted(
        eligible,
        key=lambda value: (
            hashlib.sha256(f"{seed}:{value[0]}".encode("ascii")).hexdigest(),
            value[0],
        ),
    )
    if len(ordered) < 4000:
        raise RuntimeError("Authenticated cohort rederivation has fewer than 4,000 users")
    caper_ids = sorted(value[0] for value in ordered[:1000])
    ravel_ids = sorted(value[0] for value in ordered[1000:2000])
    facet_values = sorted(ordered[2000:4000], key=lambda value: value[0])
    facet_ids = [value[0] for value in facet_values]
    if not np.array_equal(
        np.asarray(caper_ids, dtype=np.int64),
        np.asarray(validation_arrays["historical_caper_user_ids"], dtype=np.int64),
    ) or not np.array_equal(
        np.asarray(ravel_ids, dtype=np.int64),
        np.asarray(validation_arrays["historical_ravel_user_ids"], dtype=np.int64),
    ) or not np.array_equal(
        np.asarray(facet_ids, dtype=np.int64),
        np.asarray(validation_arrays["user_ids"], dtype=np.int64),
    ):
        raise RuntimeError("Raw cohort IDs differ from authenticated rederivation")

    def compare_matrix(
        raw_items: Any,
        raw_ratings: Any | None,
        raw_counts: Any,
        derived_rows: Sequence[Sequence[tuple[int, int, int, int]]],
        label: str,
    ) -> None:
        item_matrix = np.asarray(raw_items, dtype=np.int64)
        count_vector = np.asarray(raw_counts, dtype=np.int64)
        rating_matrix = (
            np.asarray(raw_ratings, dtype=np.int64) if raw_ratings is not None else None
        )
        if item_matrix.ndim != 2 or item_matrix.shape[0] != len(derived_rows):
            raise RuntimeError(f"{label} raw matrix has wrong shape")
        for row, events in enumerate(derived_rows):
            if int(count_vector[row]) != len(events):
                raise RuntimeError(f"{label} raw count differs from authenticated split")
            expected_items = np.asarray([event[0] for event in events], dtype=np.int64)
            if not np.array_equal(item_matrix[row, : len(events)], expected_items):
                raise RuntimeError(f"{label} item identities differ from authenticated split")
            if np.any(item_matrix[row, len(events) :] != -1):
                raise RuntimeError(f"{label} item padding is not -1")
            if rating_matrix is not None:
                expected_ratings = np.asarray([event[1] for event in events], dtype=np.int64)
                if not np.array_equal(rating_matrix[row, : len(events)], expected_ratings):
                    raise RuntimeError(f"{label} ratings differ from authenticated split")
                if np.any(rating_matrix[row, len(events) :] != -1):
                    raise RuntimeError(f"{label} rating padding is not -1")

    a_rows = [value[1][0] for value in facet_values]
    r_rows = [value[1][1] for value in facet_values]
    v_rows = [value[1][2] for value in facet_values]
    t_rows = [value[1][3] for value in facet_values]
    ar_rows = [(*a, *r) for a, r in zip(a_rows, r_rows)]
    arv_rows = [(*a, *r, *v) for a, r, v in zip(a_rows, r_rows, v_rows)]
    compare_matrix(
        validation_arrays["R_event_items"],
        validation_arrays["R_event_ratings"],
        validation_arrays["R_event_counts"],
        r_rows,
        "R",
    )
    compare_matrix(
        validation_arrays["validation_event_items"],
        validation_arrays["validation_event_ratings"],
        validation_arrays["validation_event_counts"],
        v_rows,
        "V",
    )
    compare_matrix(
        validation_arrays["prefix_items"],
        None,
        validation_arrays["prefix_counts"],
        ar_rows,
        "V prefix",
    )
    compare_matrix(
        test_arrays["test_event_items"],
        test_arrays["test_event_ratings"],
        test_arrays["test_event_counts"],
        t_rows,
        "T",
    )
    compare_matrix(
        test_arrays["prefix_items"],
        None,
        test_arrays["prefix_counts"],
        arv_rows,
        "T prefix",
    )
    block_counts = np.asarray(
        [[len(block) for block in value[1]] for value in facet_values], dtype=np.int64
    )
    block_minima = np.asarray(
        [[min(event[2] for event in block) for block in value[1]] for value in facet_values],
        dtype=np.int64,
    )
    block_maxima = np.asarray(
        [[max(event[2] for event in block) for block in value[1]] for value in facet_values],
        dtype=np.int64,
    )
    for field, expected in (
        ("block_counts", block_counts),
        ("block_min_timestamps", block_minima),
        ("block_max_timestamps", block_maxima),
    ):
        if not np.array_equal(np.asarray(validation_arrays[field], dtype=np.int64), expected):
            raise RuntimeError(f"Raw {field} differs from authenticated split rederivation")
    return {
        "eligible_users": len(ordered),
        "caper_users": 1000,
        "ravel_users": 1000,
        "facet_pref_users": 2000,
        "catalog_items": len(movie_ids),
        "ratings_reparsed": int(sum(len(values) for values in grouped.values())),
        "A_R_V_T_splits_exactly_rederived": True,
        "raw_R_V_T_events_authenticated": True,
    }


def run_verifier(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[1]
    run_directory = args.verify_run_directory.resolve()
    candidate_path = args.candidate.resolve()
    report_path = args.verification_report.resolve()
    ledger_path = args.verifier_ledger.resolve()
    verifier_lock_path = run_directory / "facet_pref_post_exit_verifier.lock"
    if report_path.exists() or ledger_path.exists() or verifier_lock_path.exists():
        raise RuntimeError("Append-only verifier artifact collision")
    if candidate_path.parent.resolve() != run_directory:
        raise RuntimeError("Candidate is outside the verified run directory")
    if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
        raise RuntimeError("An external completion marker already exists")

    expected_environment = execution_environment()
    launch_binding = verify_launch_binding(
        args=args, project_root=project_root, expected_environment=expected_environment
    )
    outer_authorization = verify_outer_authorization(
        outer_lock=args.outer_lock.resolve(),
        owner_pid=int(args.outer_lock_owner_pid),
        token=str(args.outer_lock_token),
    )
    config = read_json_mapping(args.config.resolve(), "FACET-PREF config")
    expected_archive = str(config["dataset"]["expected_archive_sha256"]).lower()
    if not is_sha256(expected_archive):
        raise RuntimeError("Configuration expected archive hash is malformed")
    if launch_binding["local_dataset_archive_sha256"] not in (None, expected_archive):
        raise RuntimeError("Local dataset archive is not the registered archive")
    closure = verify_candidate_closure(
        run_directory=run_directory,
        candidate_path=candidate_path,
        expected_hashes=launch_binding["source_sha256"],
        expected_environment=expected_environment,
        expected_archive_sha256=expected_archive,
    )

    # The candidate closure is checked before these verifier-owned files exist,
    # so an unbound file cannot hide inside the runner's recursive manifest.
    create_empty_file_exclusive(ledger_path)
    install_async_exception_hooks(ledger_path)
    verifier_lock = ExclusiveOwnerLock(verifier_lock_path, "post-exit-verifier")
    verifier_lock.acquire()
    try:
        verifier_lock.assert_owned()
        result = read_json_mapping(closure.result_path, "FACET-PREF result")
        if result.get("termination_stage") != closure.termination_stage:
            raise RuntimeError("Result/candidate termination-stage mismatch")
        if result.get("test_opened") is not closure.test_opened:
            raise RuntimeError("Result/candidate test-opened mismatch")
        validation_required = (
            "schema",
            "methods",
            "seeds",
            "user_ids",
            "protocol_sha256",
            "validation_event_items",
            "validation_event_ratings",
            "validation_event_counts",
            "prefix_items",
            "prefix_counts",
            "selected_bpr_variant",
            "selected_alpha",
            "movie_ids",
            "top10",
            "validation_manifest_keys",
            "validation_manifest_files",
            "validation_manifest_sha256",
            "comparator_methods",
            "seed_averaged_spce_differences",
            "power_lower_bounds",
            "power_pass_probability",
            "power_passed",
            "pair_chosen",
            "pair_rejected",
            "pair_counts",
            "alignment_uncapped_pair_counts_by_user",
            "R_event_items",
            "R_event_ratings",
            "R_event_counts",
            "alignment_selected_user_ids",
            "alignment_selected_chosen_items",
            "alignment_selected_rejected_items",
            "alignment_selected_assigned_facets",
            "R_pair_pool_file",
            "R_pair_pool_sha256",
            "historical_caper_user_ids",
            "historical_ravel_user_ids",
            "block_min_timestamps",
            "block_max_timestamps",
            "block_counts",
            "R_manifest_published_ns",
            "R_target_joined_ns",
            "V_manifest_published_ns",
            "V_relevance_joined_ns",
            "choices_frozen_ns",
            "V_preference_joined_ns",
            "T_opened",
        )
        validation_arrays = _load_npz(
            closure.validation_path, validation_required, "raw validation power evidence"
        )
        if set(validation_arrays) != set(validation_required):
            raise RuntimeError("Raw validation power schema inventory changed")
        if _decode_strings(validation_arrays["schema"], "raw validation schema") != (
            "facet-pref-raw-validation-power-v1",
        ):
            raise RuntimeError("Unexpected raw validation power schema")
        power_report = replay_validation_power(
            validation_arrays, config, run_directory
        )
        test_arrays: Mapping[str, Any] | None = None
        latency_arrays: Mapping[str, Any] | None = None
        if closure.test_path is not None:
            test_required = (
                "schema",
                "methods",
                "metric_names",
                "seeds",
                "user_ids",
                "protocol_sha256",
                "candidates",
                "rankings",
                "final_scores",
                "bpr_scores",
                "semantic_scores",
                "facet_counts",
                "quota_utilization",
                "semantic_owners",
                "retrieval_diagnostics",
                "retrieval_diagnostic_names",
                "test_manifest_seed_keys",
                "test_manifest_files",
                "test_manifest_sha256",
                "movie_ids",
                "selected_bpr_variant",
                "selected_alpha",
                "prefix_items",
                "prefix_counts",
                "test_event_items",
                "test_event_ratings",
                "test_event_counts",
                "pair_chosen",
                "pair_rejected",
                "pair_counts",
                "common_support_counts",
                "changed_outcome_counts",
                "total_pair_rows",
                "metrics",
                "historical_caper_user_ids",
                "historical_ravel_user_ids",
                "block_min_timestamps",
                "block_max_timestamps",
                "block_counts",
                "R_manifest_published_ns",
                "R_target_joined_ns",
                "V_manifest_published_ns",
                "V_relevance_joined_ns",
                "choices_frozen_ns",
                "V_preference_joined_ns",
                "T_manifest_published_ns",
                "T_target_joined_ns",
                "T_opened",
            )
            test_arrays = _load_npz(
                closure.test_path, test_required, "raw sealed-test evidence"
            )
            if set(test_arrays) != set(test_required):
                raise RuntimeError("Raw sealed-test schema inventory changed")
            if _decode_strings(test_arrays["schema"], "raw test schema") != (
                "facet-pref-raw-test-v1",
            ):
                raise RuntimeError("Unexpected raw sealed-test schema")
            assert closure.latency_path is not None
            latency_required = (
                "schema",
                "methods",
                "seeds",
                "protocol_sha256",
                "durations_ms",
                "p95_ms_by_seed_method",
                "ratio_by_seed",
            )
            latency_arrays = _load_npz(
                closure.latency_path,
                latency_required,
                "raw latency evidence",
            )
            if set(latency_arrays) != set(latency_required):
                raise RuntimeError("Raw latency schema inventory changed")
            if _decode_strings(latency_arrays["schema"], "latency schema") != (
                "facet-pref-latency-v1",
            ):
                raise RuntimeError("Unexpected raw latency schema")
        temporal_report = _verify_raw_temporal_evidence(
            validation_arrays, test_arrays
        )
        immutable_report = _verify_immutable_artifacts(result, run_directory)
        test_manifest_report: Mapping[str, Any] | None = None
        test_pair_report: Mapping[str, Any] | None = None
        if test_arrays is not None:
            test_manifest_report = _verify_test_manifest_binding(
                result, test_arrays, run_directory
            )
            test_pair_report = _verify_natural_pair_universe(
                test_arrays,
                event_prefix="test",
                hash_seed=int(
                    str(config["evaluation"]["test_pair_hash_format"]).split(":", 1)[0]
                ),
                maximum_pairs=int(config["evaluation"]["maximum_test_pairs_per_user"]),
                minimum_gap=int(config["dataset"]["preference_pair_minimum_rating_gap"]),
            )
        provenance_report = _result_provenance(
            result, expected_archive, temporal_report, run_directory
        )
        fingerprint_report = _verify_protocol_and_execution_fingerprints(
            closure=closure,
            result=result,
            validation_arrays=validation_arrays,
            test_arrays=test_arrays,
            latency_arrays=latency_arrays,
            config=config,
            selection=require_mapping(power_report["selection"], "selection replay"),
            expected_archive_sha256=expected_archive,
        )
        authenticated_cohort_report: Mapping[str, Any] | None = None
        if test_arrays is not None:
            authenticated_cohort_report = _rederive_post_t_cohort_from_authenticated_sources(
                validation_arrays=validation_arrays,
                test_arrays=test_arrays,
                provenance=provenance_report,
                config=config,
                run_directory=run_directory,
            )
        if args.runner_stderr.stat().st_size != 0:
            raise RuntimeError("Clean outcome runner stderr is nonempty")
        if closure.runner_ledger.stat().st_size != 0:
            raise RuntimeError("Runner asynchronous-error ledger became nonempty")
        if pid_is_running(closure.runner_pid) or pid_is_running(
            int(args.launcher_child_pid)
        ):
            raise RuntimeError("A runner process is still active")
        if closure.runner_lock.exists():
            raise RuntimeError("Runner lock reappeared")

        integrity_preconditions = {
            "candidate_recursive_hashes": True,
            "runner_process_exit": True,
            "runner_lock_release": True,
            "runner_stderr_empty": True,
            "runner_async_ledger_empty": True,
            "source_protocol_config_environment_interpreter_bound": True,
            "archive_and_extraction_bound": True,
            "cohort_and_temporal_replayed": True,
            "authenticated_source_cohort_rederived_when_T_open": bool(
                authenticated_cohort_report is not None
                or closure.termination_stage == "pre_T_power_audit"
            ),
            "target_blind_order": True,
            "raw_test_bound_to_pre_target_manifests": bool(
                test_manifest_report is not None
                or closure.termination_stage == "pre_T_power_audit"
            ),
            "matrix_index_immutable": bool(
                immutable_report["matrix_index_immutable"]
            ),
            "outer_launch_lock_held": True,
        }
        if closure.termination_stage == "pre_T_power_audit":
            _verify_pre_t_result(result, bool(power_report["passed"]))
            scientific_replay: Mapping[str, Any] = {
                "termination_stage": "pre_T_power_audit",
                "test_opened": False,
                "power_audit": power_report,
                "gates": {
                    "G1": "not_evaluated",
                    "G2": "not_evaluated",
                    "G3": "not_evaluated",
                    "G4": "not_evaluated",
                    "G5": "not_evaluated",
                    "G6": False,
                    "G7": "not_evaluated",
                    "G8": "not_evaluated",
                    "G9": bool(all(integrity_preconditions.values())),
                },
                "promising": False,
                "negative_pre_T_completion": True,
                "raw_power_replay_complete": True,
            }
            promise_gate_passed = False
        else:
            if power_report["passed"] is not True:
                raise RuntimeError("Runner opened T after the registered power audit failed")
            assert test_arrays is not None and latency_arrays is not None
            _test_target_not_in_prefix(test_arrays)
            scientific_replay = replay_test_gates(
                test_arrays,
                latency_arrays,
                config,
                power_report,
                integrity_preconditions,
            )
            _validate_result_gate_equality(
                result, require_mapping(scientific_replay["gates"], "replayed gates")
            )
            promise_gate_passed = bool(scientific_replay["promising"])

        if ledger_path.stat().st_size != 0:
            raise RuntimeError("Verifier asynchronous-error ledger is nonempty")
        verifier_lock.assert_owned()
        report = {
            "schema": "facet-pref-post-exit-verification-v1",
            "verified_utc": utc_now(),
            "verifier_pid": os.getpid(),
            "run_directory": str(run_directory),
            "candidate_marker": candidate_path.name,
            "candidate_marker_sha256": sha256_file(candidate_path),
            "result_file": closure.result_path.name,
            "result_sha256": sha256_file(closure.result_path),
            "termination_stage": closure.termination_stage,
            "test_opened": closure.test_opened,
            "runner_pid": closure.runner_pid,
            "runner_process_has_exited": True,
            "runner_lock": str(closure.runner_lock),
            "runner_lock_released": True,
            "runner_asynchronous_error_ledger": closure.runner_ledger.name,
            "runner_asynchronous_error_ledger_sha256": EMPTY_SHA256,
            "runner_stderr_zero_bytes": True,
            "verified_recursive_artifact_count": len(closure.artifact_hashes),
            "verified_recursive_artifact_sha256": closure.artifact_hashes,
            "launch_binding": launch_binding,
            "outer_authorization": outer_authorization,
            "temporal_replay": temporal_report,
            "immutable_artifacts": immutable_report,
            "test_manifest_binding": test_manifest_report,
            "test_pair_universe": test_pair_report,
            "provenance": provenance_report,
            "fingerprints": fingerprint_report,
            "authenticated_cohort_rederivation": authenticated_cohort_report,
            "integrity_preconditions": integrity_preconditions,
            "scientific_replay": scientific_replay,
            "promise_gate_passed": promise_gate_passed,
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
        raise RuntimeError("Verifier lock remains after verifier completion")
    return 0


def _safe_run_id(value: str) -> str:
    if Path(value).name != value or value in {"", ".", ".."}:
        raise ValueError("run-id must be one safe path component")
    return value


def run_launch(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[1]
    launcher = Path(__file__).resolve()
    runner = (project_root / "src" / "facet_pref_poc.py").resolve()
    config = args.config.resolve()
    protocol = args.protocol.resolve()
    locked_config = (
        project_root / "src" / "configs" / "facet_pref_poc_ml1m_v1.json"
    ).resolve()
    locked_protocol = (
        project_root / "experiments" / "facet-pref-protocol-v1.md"
    ).resolve()
    if config != locked_config or protocol != locked_protocol:
        raise RuntimeError("Outcome launch accepts only the project-locked config/protocol paths")
    caper_dependency = (project_root / "src" / "caper_poc.py").resolve()
    research_question = (project_root / "research-question-cycle4.md").resolve()
    cycle4_survey = (
        project_root / "literature" / "cycle4-survey-and-ideation.md"
    ).resolve()
    architecture = (project_root / "architecture-facet-pref.md").resolve()
    output_root = args.output_root.resolve()
    python_executable = Path(sys.executable).absolute()
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise RuntimeError(
            "FACET-PREF launcher must be invoked by the workspace virtual-environment Python"
        )
    for path, label in (
        (python_executable, "current virtual-environment Python"),
        (launcher, "launcher/verifier source"),
        (runner, "FACET-PREF runner"),
        (config, "FACET-PREF configuration"),
        (protocol, "FACET-PREF protocol"),
        (caper_dependency, "CAPER dependency"),
        (research_question, "cycle-4 research question"),
        (cycle4_survey, "cycle-4 survey"),
        (architecture, "FACET-PREF architecture"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Missing {label}: {path}")
    config_value = read_json_mapping(config, "FACET-PREF config")
    expected_archive = str(config_value["dataset"]["expected_archive_sha256"]).lower()
    if not is_sha256(expected_archive):
        raise RuntimeError("Configured archive SHA-256 is malformed")
    local_archive = (
        args.local_dataset_archive.resolve()
        if args.local_dataset_archive is not None
        else None
    )
    if local_archive is not None:
        if not local_archive.is_file():
            raise FileNotFoundError(f"Missing local dataset archive: {local_archive}")
        if sha256_file(local_archive) != expected_archive:
            raise RuntimeError("Local dataset archive fails the registered SHA-256")

    run_id = _safe_run_id(
        args.run_id
        or (
            "facet-pref-poc-v1-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            + "-"
            + uuid.uuid4().hex[:12]
        )
    )
    run_parent = output_root / "facet_pref_poc_runs"
    run_directory = run_parent / run_id
    if run_directory.exists():
        raise FileExistsError(f"Run directory already exists: {run_directory}")
    run_parent.mkdir(parents=True, exist_ok=True)
    outer_lock = ExclusiveOwnerLock(
        output_root / "facet_pref_outer_launch.lock", "outer-launch"
    )

    launch_directory = project_root / "experiments" / "launches"
    launch_directory.mkdir(parents=True, exist_ok=True)
    runner_stdout = launch_directory / f"{run_id}.stdout.log"
    runner_stderr = launch_directory / f"{run_id}.stderr.log"
    verifier_stdout = launch_directory / f"{run_id}.verifier.stdout.log"
    verifier_stderr = launch_directory / f"{run_id}.verifier.stderr.log"
    launcher_ledger = launch_directory / f"{run_id}.launcher.async-errors.jsonl"
    launch_record = launch_directory / f"{run_id}.launch.json"
    failure_path = launch_directory / f"{run_id}.external_failure.json"
    for path in (
        runner_stdout,
        runner_stderr,
        verifier_stdout,
        verifier_stderr,
        launcher_ledger,
        launch_record,
        failure_path,
    ):
        if path.exists():
            raise FileExistsError(f"Append-only launch artifact collision: {path}")

    create_empty_file_exclusive(launcher_ledger)
    install_async_exception_hooks(launcher_ledger)
    fixed_environment = execution_environment()
    environment = os.environ.copy()
    environment.update(fixed_environment)
    environment_hash = execution_environment_sha256(fixed_environment)
    source_hashes = {
        "launcher": sha256_file(launcher),
        "runner": sha256_file(runner),
        "config": sha256_file(config),
        "protocol": sha256_file(protocol),
        "caper_dependency": sha256_file(caper_dependency),
        "research_question": sha256_file(research_question),
        "cycle4_survey": sha256_file(cycle4_survey),
        "architecture_facet_pref": sha256_file(architecture),
        "python_executable": sha256_file(python_executable),
    }
    command = [
        str(python_executable),
        "-B",
        "-u",
        str(runner),
        "--config",
        str(config),
        "--protocol",
        str(protocol),
        "--output-dir",
        str(run_directory),
    ]
    if local_archive is not None:
        command.extend(["--local-dataset-archive", str(local_archive)])

    outer_lock.acquire()
    child_pid: int | None = None
    child_return_code: int | None = None
    verifier_child_pid: int | None = None
    verifier_return_code: int | None = None
    external_marker: Path | None = None
    result_path: Path | None = None
    promise_gate_passed: bool | None = None
    try:
        outer_lock.assert_owned()
        publish_json_exclusive(
            launch_record,
            {
                "schema": "facet-pref-external-launch-v1",
                "created_utc": utc_now(),
                "project_root": str(project_root),
                "launcher_pid": os.getpid(),
                "run_id": run_id,
                "run_directory": str(run_directory),
                "python_executable": str(python_executable),
                "command": command,
                "source_sha256": source_hashes,
                "execution_environment": fixed_environment,
                "execution_environment_sha256": environment_hash,
                "local_dataset_archive": (
                    str(local_archive) if local_archive is not None else None
                ),
                "local_dataset_archive_sha256": (
                    sha256_file(local_archive) if local_archive is not None else None
                ),
                "outer_lock": str(outer_lock.path),
                "outer_lock_token_sha256": sha256_text(outer_lock.token),
            },
        )
        child_pid, child_return_code = run_hidden_process(
            command,
            project_root,
            environment,
            runner_stdout,
            runner_stderr,
        )
        if child_return_code != 0:
            raise RuntimeError(
                f"FACET-PREF outcome runner exited with code {child_return_code}"
            )
        if child_pid <= 0 or pid_is_running(child_pid):
            raise RuntimeError(f"Launcher child PID remains active: {child_pid}")
        if not run_directory.is_dir():
            raise RuntimeError(f"Runner did not create its output directory: {run_directory}")
        candidate_path = find_sole_runner_candidate(run_directory)
        candidate_preview = read_json_mapping(candidate_path, "runner candidate")
        execution_hash = candidate_preview.get("execution_fingerprint_sha256")
        if not is_sha256(execution_hash):
            raise RuntimeError("Runner candidate has malformed execution fingerprint")
        if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
            raise RuntimeError("An external marker already exists")

        nonce = uuid.uuid4().hex[:12]
        verifier_ledger = run_directory / (
            f"verifier_async_errors_{str(execution_hash)[:16]}_{nonce}.jsonl"
        )
        verifier_report = run_directory / (
            f"POST_EXIT_VERIFIER_{str(execution_hash)[:16]}_{nonce}.json"
        )
        verifier_command = [
            str(python_executable),
            "-B",
            "-u",
            str(launcher),
            "--verify-run-directory",
            str(run_directory),
            "--candidate",
            str(candidate_path),
            "--verification-report",
            str(verifier_report),
            "--verifier-ledger",
            str(verifier_ledger),
            "--runner-stdout",
            str(runner_stdout),
            "--runner-stderr",
            str(runner_stderr),
            "--launcher-child-pid",
            str(child_pid),
            "--outer-lock",
            str(outer_lock.path),
            "--outer-lock-owner-pid",
            str(os.getpid()),
            "--outer-lock-token",
            outer_lock.token,
            "--config",
            str(config),
            "--protocol",
            str(protocol),
            "--runner",
            str(runner),
            "--launch-record",
            str(launch_record),
            "--expected-launcher-sha256",
            source_hashes["launcher"],
        ]
        if local_archive is not None:
            verifier_command.extend(
                ["--local-dataset-archive", str(local_archive)]
            )
        verifier_child_pid, verifier_return_code = run_hidden_process(
            verifier_command,
            project_root,
            environment,
            verifier_stdout,
            verifier_stderr,
        )
        if verifier_return_code != 0:
            raise RuntimeError(
                f"FACET-PREF post-exit verifier exited with code {verifier_return_code}"
            )
        if verifier_child_pid <= 0 or pid_is_running(verifier_child_pid):
            raise RuntimeError(f"Verifier child PID remains active: {verifier_child_pid}")
        if not verifier_report.is_file():
            raise RuntimeError("Post-exit verifier did not publish its report")
        report = read_json_mapping(verifier_report, "post-exit verifier report")
        if report.get("schema") != "facet-pref-post-exit-verification-v1":
            raise RuntimeError("Unexpected post-exit verifier report schema")
        verifier_pid = int(report.get("verifier_pid", -1))
        if verifier_pid <= 0 or pid_is_running(verifier_pid):
            raise RuntimeError(f"Verifier PID is active or invalid: {verifier_pid}")
        if report.get("external_marker_publication_authorized") is not True:
            raise RuntimeError("Post-exit verifier did not authorize marker publication")
        verifier_lock = Path(str(report.get("verifier_lock", ""))).resolve()
        if verifier_lock.exists():
            raise RuntimeError("Post-exit verifier lock remains after process exit")
        if not verifier_ledger.is_file() or verifier_ledger.stat().st_size != 0:
            raise RuntimeError("Verifier asynchronous-error ledger is nonempty")
        if verifier_stderr.stat().st_size != 0:
            raise RuntimeError("Clean verifier stderr is nonempty")
        if runner_stderr.stat().st_size != 0:
            raise RuntimeError("Clean runner stderr is nonempty")
        if launcher_ledger.stat().st_size != 0:
            raise RuntimeError("Launcher asynchronous-error ledger is nonempty")
        if sha256_file(launcher) != source_hashes["launcher"]:
            raise RuntimeError("Launcher source changed during execution")
        if sha256_file(runner) != source_hashes["runner"]:
            raise RuntimeError("Runner source changed during execution")
        outer_lock.assert_owned()

        candidate = read_json_mapping(candidate_path, "runner candidate after replay")
        result_path = contained_file(
            run_directory, str(candidate["result_file"]), "result file"
        )
        promise_gate_passed = bool(report["promise_gate_passed"])
        external_marker = run_directory / (
            f"{EXTERNAL_MARKER_PREFIX}{str(execution_hash)[:16]}.json"
        )
        publish_json_exclusive(
            external_marker,
            {
                "schema": "facet-pref-external-completion-v1",
                "verified_utc": utc_now(),
                "termination_stage": report["termination_stage"],
                "test_opened": report["test_opened"],
                "python_executable": str(python_executable),
                "python_executable_sha256": source_hashes["python_executable"],
                "launcher_sha256": source_hashes["launcher"],
                "runner_sha256": source_hashes["runner"],
                "config_sha256": source_hashes["config"],
                "protocol_sha256": source_hashes["protocol"],
                "launcher_pid": os.getpid(),
                "launcher_child_pid": child_pid,
                "launcher_child_exit_code": child_return_code,
                "launcher_child_process_has_exited": True,
                "runner_pid": report["runner_pid"],
                "runner_process_has_exited": True,
                "verifier_child_pid": verifier_child_pid,
                "verifier_child_exit_code": verifier_return_code,
                "verifier_child_process_has_exited": True,
                "verifier_pid": verifier_pid,
                "verifier_process_has_exited": True,
                "runner_lock": report["runner_lock"],
                "runner_lock_released": True,
                "verifier_lock": str(verifier_lock),
                "verifier_lock_released": True,
                "outer_lock": str(outer_lock.path),
                "outer_lock_held_through_marker_publication": True,
                "outer_lock_release_pending_on_launcher_return": True,
                "launch_record": str(launch_record),
                "launch_record_sha256": sha256_file(launch_record),
                "candidate_marker": candidate_path.name,
                "candidate_marker_sha256": sha256_file(candidate_path),
                "post_exit_verifier_report": verifier_report.name,
                "post_exit_verifier_report_sha256": sha256_file(verifier_report),
                "verified_recursive_artifact_count": report[
                    "verified_recursive_artifact_count"
                ],
                "runner_asynchronous_error_ledger": report[
                    "runner_asynchronous_error_ledger"
                ],
                "runner_asynchronous_error_ledger_empty": True,
                "runner_asynchronous_error_ledger_sha256": EMPTY_SHA256,
                "verifier_asynchronous_error_ledger": verifier_ledger.name,
                "verifier_asynchronous_error_ledger_empty": True,
                "verifier_asynchronous_error_ledger_sha256": EMPTY_SHA256,
                "launcher_asynchronous_error_ledger": str(launcher_ledger),
                "launcher_asynchronous_error_ledger_empty": True,
                "launcher_asynchronous_error_ledger_sha256": EMPTY_SHA256,
                "runner_stdout": str(runner_stdout),
                "runner_stdout_sha256": sha256_file(runner_stdout),
                "runner_stderr": str(runner_stderr),
                "runner_stderr_zero_bytes": True,
                "runner_stderr_sha256": EMPTY_SHA256,
                "verifier_stdout": str(verifier_stdout),
                "verifier_stdout_sha256": sha256_file(verifier_stdout),
                "verifier_stderr": str(verifier_stderr),
                "verifier_stderr_zero_bytes": True,
                "verifier_stderr_sha256": EMPTY_SHA256,
                "result_file": result_path.name,
                "result_sha256": sha256_file(result_path),
                "execution_environment_sha256": environment_hash,
                "execution_fingerprint_sha256": str(execution_hash).lower(),
                "scientific_replay": report["scientific_replay"],
                "provenance": report["provenance"],
                "fingerprints": report["fingerprints"],
                "promise_gate_passed": promise_gate_passed,
            },
        )
        if len(list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json"))) != 1:
            raise RuntimeError("External marker publication was not singular")
    except BaseException as exc:
        if not failure_path.exists():
            publish_json_exclusive(
                failure_path,
                {
                    "schema": "facet-pref-external-verification-failure-v1",
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
                    "runner_stdout": str(runner_stdout),
                    "runner_stderr": str(runner_stderr),
                    "verifier_stdout": str(verifier_stdout),
                    "verifier_stderr": str(verifier_stderr),
                    "outer_lock": str(outer_lock.path),
                    "outer_lock_held_at_failure": outer_lock.acquired,
                },
            )
        raise
    finally:
        outer_lock.release()

    if outer_lock.path.exists():
        raise RuntimeError("FACET-PREF outer launch lock remains")
    if external_marker is None or result_path is None or promise_gate_passed is None:
        raise RuntimeError("FACET-PREF launch reached an incomplete terminal state")
    print(f"EXTERNAL_COMPLETION_MARKER={external_marker}", flush=True)
    print(f"RESULT_FILE={result_path}", flush=True)
    print(f"PROMISE_GATE_PASSED={str(promise_gate_passed).lower()}", flush=True)
    print("OUTER_LOCK_RELEASED=true", flush=True)
    return 0


def synthetic_self_test() -> Mapping[str, Any]:
    import numpy as np

    if _pair_outcome((11, 22, 33), 22, 33) != 1.0:
        raise RuntimeError("Synthetic sPCE positive case failed")
    if _pair_outcome((11, 22, 33), 44, 33) != 0.0:
        raise RuntimeError("Synthetic sPCE hidden-chosen case failed")
    if _pair_outcome((11, 22, 33), 44, 55) != 0.0:
        raise RuntimeError("Synthetic sPCE both-hidden case failed")
    values = np.asarray([0.1, 0.2, -0.1, 0.0], dtype=np.float64)
    first = _paired_bootstrap(values, draws=100, alpha=0.05, seed=17)
    second = _paired_bootstrap(values, draws=100, alpha=0.05, seed=17)
    if first != second or not math.isclose(first["point"], 0.05, abs_tol=1e-15):
        raise RuntimeError("Synthetic paired bootstrap is not deterministic")
    all_pass = {name: True for name in GATE_NAMES}
    _validate_result_gate_equality(
        {
            "PROMISING": False,
            "runner_candidate_promising": True,
            "promise_gate": {
                "gates": all_pass,
                "runner_candidate_promising": True,
                "PROMISING": False,
            },
        },
        all_pass,
    )
    synthetic_facets = np.asarray([[0], [2]], dtype=np.int64)
    synthetic_quota = np.asarray([[[0, 0]], [[150, 50]]], dtype=np.int64)
    synthetic_diagnostics = np.asarray(
        [[[0, 0, 0, 0, 0, 0]], [[20, 12, 12, 0, 150, 62]]],
        dtype=np.int64,
    )
    synthetic_owners = np.full((2, 1, 200), -1, dtype=np.int64)
    synthetic_owners[1, 0] = np.asarray([0] * 100 + [1] * 50 + [0] * 50)
    _verify_semantic_owner_evidence(
        synthetic_facets,
        synthetic_quota,
        synthetic_diagnostics,
        synthetic_owners,
        "synthetic overlap/backfill",
    )
    with tempfile.TemporaryDirectory(prefix="facet-pref-verifier-selftest-") as temp:
        root = Path(temp)
        artifact = root / "nested" / "value.bin"
        artifact.parent.mkdir()
        publish_bytes_exclusive(artifact, b"facet-pref")
        try:
            publish_bytes_exclusive(artifact, b"corruption")
        except FileExistsError:
            pass
        else:
            raise RuntimeError("Exclusive atomic publisher overwrote an existing artifact")
        if artifact.read_bytes() != b"facet-pref" or list(
            artifact.parent.glob(f".{artifact.name}.tmp.*")
        ):
            raise RuntimeError("Atomic publisher left corruption or a partial temporary")
        manifest = file_hash_manifest(root)
        if manifest != {"nested/value.bin": sha256_bytes(b"facet-pref")}:
            raise RuntimeError("Synthetic recursive hash closure failed")
        lock = ExclusiveOwnerLock(root / "test.lock", "self-test")
        lock.acquire()
        lock.assert_owned()
        lock.release()
        if lock.path.exists():
            raise RuntimeError("Synthetic exclusive lock did not release")
    return {
        "pair_outcome": True,
        "paired_bootstrap": True,
        "non_authoritative_runner_all_pass": True,
        "overlap_adjusted_owner_backfill": True,
        "recursive_hash_closure": True,
        "atomic_no_overwrite_publication": True,
        "exclusive_lock": True,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Launch one sealed FACET-PREF PoC or independently verify an exited "
            "runner from raw append-only artifacts."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "facet_pref_poc_ml1m_v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=project_root / "experiments" / "facet-pref-protocol-v1.md",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "experiments" / "runs",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--local-dataset-archive", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify-run-directory", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--candidate", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--verification-report", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--verifier-ledger", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--runner-stdout", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--runner-stderr", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--launcher-child-pid", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--outer-lock", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--outer-lock-owner-pid", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--outer-lock-token", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--runner",
        type=Path,
        default=project_root / "src" / "facet_pref_poc.py",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--launch-record", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--expected-launcher-sha256", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.verify_run_directory is not None:
        required = {
            "candidate": args.candidate,
            "verification-report": args.verification_report,
            "verifier-ledger": args.verifier_ledger,
            "runner-stdout": args.runner_stdout,
            "runner-stderr": args.runner_stderr,
            "launcher-child-pid": args.launcher_child_pid,
            "outer-lock": args.outer_lock,
            "outer-lock-owner-pid": args.outer_lock_owner_pid,
            "outer-lock-token": args.outer_lock_token,
            "launch-record": args.launch_record,
            "expected-launcher-sha256": args.expected_launcher_sha256,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            parser.error(
                "--verify-run-directory is missing authorization arguments: "
                + ", ".join(missing)
            )
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        print(json.dumps(synthetic_self_test(), sort_keys=True), flush=True)
        return 0
    if args.verify_run_directory is not None:
        return run_verifier(args)
    return run_launch(args)


if __name__ == "__main__":
    raise SystemExit(main())
