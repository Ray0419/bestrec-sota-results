#!/usr/bin/env python3
"""Launch RAVEL safely on Windows and commit it only after post-exit verification.

The outcome runner cannot prove its own process exit or lock release.  This
launcher therefore owns persistent logs and an outer lock, waits on the actual
child process handle, starts this file again in a no-target verifier mode, and
publishes the sole ``EXTERNAL_COMPLETE`` marker only after both possible
Windows PIDs are dead, the runner's hash closure verifies, and the scientific
gate is replayed from sealed aggregate artifacts.

Verifier mode never parses MovieLens ratings or reruns a model.  After closing
the recursive artifact hash set, it imports only the hash-bound snapshots of
the runner and its CAPER dependency so that the registered gate implementation
can be rerun over the persisted per-user metrics.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import threading
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)
RUNNER_CANDIDATE_PREFIX = "RUNNER_COMPLETE"
EXTERNAL_MARKER_PREFIX = "EXTERNAL_COMPLETE_"
EXPECTED_GATE_KEYS = (
    "G1_strong_default_relevance",
    "G2_primary_relevance_noninferiority",
    "G3_primary_preference_gain",
    "G4_selective_mechanism",
    "G5_nontrivial_calibrated_coverage",
    "G6_top_rank_and_exposure_safety",
    "G7_candidate_support_and_exact_fallback",
    "G8_seed_stability",
    "G9_serving_budget",
    "G10_integrity",
)
EXPECTED_METHODS = (
    "selected_bpr",
    "linear",
    "always_on",
    "near_tie_only",
    "uncertainty_only",
    "random_matched",
    "single_head_selector_diagnostic",
    "ravel",
)
POLICY_OUTPUT_METHODS = EXPECTED_METHODS[1:]
EXPECTED_EVENT_ORDER = (
    "run_started",
    "sha_locked_data_and_disjoint_cohort_derived",
    "all_A_models_and_immutable_indexes_fitted",
    "all_R_manifests_persisted_before_R_label_join",
    "all_R_pair_pools_persisted_before_default_lock",
    "all_V_manifests_persisted_before_first_V_use",
    "segregated_V_use_1_default_identity_and_alpha_locked",
    "uniform_R_residuals_trained_and_frozen",
    "all_registered_V_proposals_persisted_before_full_V_label_join",
    "segregated_V_use_2_selector_and_controls_locked",
    "all_seed_T_output_manifests_persisted_before_any_T_label_join",
    "target_blind_latency_evidence_persisted_before_T_label_join",
    "sealed_T_opened_once_for_final_evaluation",
    "result_published",
    "runner_artifacts_finalized",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def require_canonical_equal(actual: Any, expected: Any, label: str) -> None:
    try:
        actual_bytes = canonical_json_bytes(actual)
        expected_bytes = canonical_json_bytes(expected)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} contains a noncanonical JSON value") from exc
    if actual_bytes != expected_bytes:
        raise RuntimeError(f"Canonical {label} replay mismatch")


def is_sha256(value: object) -> bool:
    text = str(value)
    return len(text) == 64 and all(character in "0123456789abcdefABCDEF" for character in text)


def fsync_directory(path: Path) -> None:
    """Best-effort directory flush; Windows does not expose portable dir fsync."""
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_json_exclusive(path: Path, value: Any) -> None:
    """Atomically publish fsynced JSON once without replacing a final path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    )
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard-link publication is atomic and refuses an existing target on
        # both NTFS and POSIX filesystems.  Removing the temporary name leaves
        # the already-fsynced inode at the final append-only path.
        os.link(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_empty_file_exclusive(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def append_json_line(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
    with path.open("ab", buffering=0) as handle:
        handle.write(payload)
        os.fsync(handle.fileno())


def install_async_exception_hooks(ledger: Path) -> None:
    """Record background-thread and unraisable exceptions append-only."""

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        append_json_line(
            ledger,
            {
                "utc": utc_now(),
                "kind": "threading.excepthook",
                "thread": getattr(args.thread, "name", None),
                "exception_type": getattr(args.exc_type, "__name__", str(args.exc_type)),
                "exception": str(args.exc_value),
                "traceback": "".join(
                    traceback.format_exception(
                        args.exc_type, args.exc_value, args.exc_traceback
                    )
                ),
            },
        )

    def unraisable_hook(args: Any) -> None:
        append_json_line(
            ledger,
            {
                "utc": utc_now(),
                "kind": "sys.unraisablehook",
                "object": repr(getattr(args, "object", None)),
                "exception_type": type(args.exc_value).__name__,
                "exception": str(args.exc_value),
                "traceback": "".join(
                    traceback.format_exception(
                        type(args.exc_value), args.exc_value, args.exc_traceback
                    )
                ),
            },
        )

    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


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
            if error_code == 5:  # ERROR_ACCESS_DENIED: exit cannot be proved.
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


class OuterLaunchLock:
    """Owner-PID outer lock held across runner, verifier, and marker commit."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            try:
                publish_json_exclusive(
                    self.path,
                    {
                        "schema": "ravel-outer-launch-lock-v1",
                        "pid": os.getpid(),
                        "token": self.token,
                        "created_utc": utc_now(),
                    },
                )
                self.acquired = True
                return
            except FileExistsError:
                if attempt:
                    raise RuntimeError(f"Racing RAVEL outer lock: {self.path}")
                try:
                    existing = read_json_mapping(self.path, "outer lock")
                    owner_pid = int(existing["pid"])
                    owner_token = str(existing["token"])
                except Exception as exc:
                    raise RuntimeError(f"Malformed RAVEL outer lock: {self.path}") from exc
                if not owner_token or pid_is_running(owner_pid):
                    raise RuntimeError(
                        f"RAVEL outer lock belongs to live/unverifiable PID {owner_pid}: "
                        f"{self.path}"
                    )
                retired = self.path.with_name(
                    f"{self.path.name}.retired."
                    f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}."
                    f"{uuid.uuid4().hex}.json"
                )
                try:
                    os.rename(self.path, retired)
                    fsync_directory(self.path.parent)
                except OSError as exc:
                    raise RuntimeError("RAVEL outer-lock retirement raced") from exc
        raise AssertionError("unreachable")

    def assert_owned(self) -> None:
        if not self.acquired:
            raise RuntimeError("RAVEL outer lock is not held")
        value = read_json_mapping(self.path, "outer lock")
        if int(value.get("pid", -1)) != os.getpid() or value.get("token") != self.token:
            raise RuntimeError("RAVEL outer-lock ownership changed")

    def release(self) -> None:
        if not self.acquired:
            return
        self.assert_owned()
        self.path.unlink()
        fsync_directory(self.path.parent)
        self.acquired = False


def read_json_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Missing {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Malformed {label}: {path}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} is not a JSON object: {path}")
    return value


def contained_file(base: Path, relative_name: str, label: str) -> Path:
    """Resolve a candidate-supplied relative artifact without path escape."""
    relative = Path(relative_name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise RuntimeError(f"Invalid {label} path: {relative_name!r}")
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} escapes the run directory: {relative_name}") from exc
    return resolved


def find_sole_runner_candidate(run_directory: Path) -> Path:
    candidates = sorted(
        path
        for path in run_directory.glob(f"{RUNNER_CANDIDATE_PREFIX}*.json")
        if path.is_file()
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected one runner completion candidate, found {len(candidates)}"
        )
    return candidates[0]


def verify_outer_authorization(
    path: Path, expected_owner_pid: int, expected_token: str
) -> None:
    value = read_json_mapping(path.resolve(), "active outer lock")
    if value.get("schema") != "ravel-outer-launch-lock-v1":
        raise RuntimeError("Unexpected outer-lock schema")
    if int(value.get("pid", -1)) != expected_owner_pid:
        raise RuntimeError("Verifier outer-lock owner PID mismatch")
    if str(value.get("token", "")) != expected_token:
        raise RuntimeError("Verifier outer-lock authorization token mismatch")
    if not pid_is_running(expected_owner_pid):
        raise RuntimeError("Verifier cannot prove the authorizing launcher is active")


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} is not a mapping")
    return value


def require_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} is not a JSON array")
    return value


def parse_bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text == "true":
        return True
    if text == "false":
        return False
    raise RuntimeError(f"Invalid Boolean {label}: {value!r}")


def parse_int(value: Any, label: str) -> int:
    text = str(value).strip()
    try:
        parsed = int(text)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid integer {label}: {value!r}") from exc
    if str(parsed) != text and not (text.startswith("+") and str(parsed) == text[1:]):
        raise RuntimeError(f"Noncanonical integer {label}: {value!r}")
    return parsed


def parse_float(value: Any, label: str, *, allow_nan: bool = False) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid float {label}: {value!r}") from exc
    if math.isinf(parsed) or (math.isnan(parsed) and not allow_nan):
        raise RuntimeError(f"Nonfinite float {label}: {value!r}")
    return parsed


def load_module_from_verified_snapshot(
    module_name: str, path: Path, expected_sha256: str
) -> Any:
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"Hash changed before importing snapshot: {path.name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load verified source snapshot: {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        raise
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"Hash changed while importing snapshot: {path.name}")
    return module


def load_bound_runner_module(
    run_directory: Path, result: Mapping[str, Any]
) -> tuple[Any, Mapping[str, Path]]:
    provenance = require_mapping(result.get("provenance"), "result provenance")
    source_hashes = require_mapping(
        provenance.get("source_hashes"), "result source hashes"
    )
    if set(source_hashes) != {
        "config",
        "protocol_document",
        "ravel_runner",
        "caper_dependency",
        "research_question",
        "cycle3_survey",
    }:
        raise RuntimeError("Result source-hash registry is not the locked source set")
    environment_path = contained_file(
        run_directory,
        str(provenance.get("environment_file", "")),
        "environment artifact",
    )
    environment = read_json_mapping(environment_path, "environment artifact")
    snapshots_raw = require_mapping(
        environment.get("source_snapshots"), "environment source snapshots"
    )
    snapshot_paths: dict[str, Path] = {}
    for label in (
        "ravel_runner",
        "caper_dependency",
        "protocol_document",
        "research_question",
        "cycle3_survey",
    ):
        record = require_mapping(snapshots_raw.get(label), f"{label} snapshot record")
        expected_hash = str(source_hashes.get(label, "")).lower()
        if not is_sha256(expected_hash):
            raise RuntimeError(f"Malformed bound source hash: {label}")
        if str(record.get("sha256", "")).lower() != expected_hash:
            raise RuntimeError(f"Environment/source hash mismatch: {label}")
        path = contained_file(
            run_directory, str(record.get("file", "")), f"{label} snapshot"
        )
        if sha256_file(path) != expected_hash:
            raise RuntimeError(f"Source snapshot hash mismatch: {label}")
        snapshot_paths[label] = path

    previous_caper = sys.modules.get("caper_poc")
    caper_module = load_module_from_verified_snapshot(
        "caper_poc",
        snapshot_paths["caper_dependency"],
        str(source_hashes["caper_dependency"]).lower(),
    )
    runner_name = f"_verified_ravel_poc_{str(result['protocol_sha256'])[:16]}"
    try:
        runner_module = load_module_from_verified_snapshot(
            runner_name,
            snapshot_paths["ravel_runner"],
            str(source_hashes["ravel_runner"]).lower(),
        )
    finally:
        if previous_caper is None:
            sys.modules.pop("caper_poc", None)
        else:
            sys.modules["caper_poc"] = previous_caper
    if getattr(runner_module, "core", None) is not caper_module:
        raise RuntimeError("Verified runner did not bind the verified CAPER snapshot")
    for function_name in (
        "evaluate_ten_part_gate",
        "summarize_rows",
        "validate_config",
    ):
        if not callable(getattr(runner_module, function_name, None)):
            raise RuntimeError(f"Verified runner lacks {function_name}")
    return runner_module, snapshot_paths


def parse_per_user_metrics(
    path: Path, expected_seeds: Sequence[int]
) -> Mapping[int, Mapping[str, list[Mapping[str, Any]]]]:
    expected_fields = (
        "seed",
        "method",
        "user_id",
        "ndcg_at_10",
        "recall_at_10",
        "preference_pair_accuracy",
        "preference_pairs",
        "preference_correct",
        "future_dislike_intrusion_at_10",
        "candidate_recall",
        "union_candidate_recall_at_most_400",
        "collaborative_candidate_recall_at_200",
        "candidate_support_inclusion",
        "accepted",
        "exact_fallback",
        "ndcg_delta_vs_linear",
        "preference_delta_vs_linear",
        "harmful_intervention",
    )
    numeric = (
        "ndcg_at_10",
        "recall_at_10",
        "preference_pair_accuracy",
        "preference_pairs",
        "preference_correct",
        "future_dislike_intrusion_at_10",
        "candidate_recall",
        "union_candidate_recall_at_most_400",
        "collaborative_candidate_recall_at_200",
        "accepted",
        "ndcg_delta_vs_linear",
        "preference_delta_vs_linear",
    )
    grouped: dict[int, dict[str, list[Mapping[str, Any]]]] = {
        int(seed): {method: [] for method in EXPECTED_METHODS}
        for seed in expected_seeds
    }
    seen: set[tuple[int, str, int]] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise RuntimeError("Per-user metrics CSV schema mismatch")
        for line_number, source in enumerate(reader, start=2):
            seed = parse_int(source["seed"], f"CSV seed at line {line_number}")
            method = str(source["method"])
            user_id = parse_int(
                source["user_id"], f"CSV user_id at line {line_number}"
            )
            if seed not in grouped or method not in EXPECTED_METHODS:
                raise RuntimeError(f"Unregistered CSV seed/method at line {line_number}")
            key = (seed, method, user_id)
            if key in seen:
                raise RuntimeError(f"Duplicate per-user metric row: {key}")
            seen.add(key)
            row: dict[str, Any] = {"user_id": user_id}
            for field in numeric:
                row[field] = parse_float(
                    source[field],
                    f"CSV {field} at line {line_number}",
                    allow_nan=field
                    in {"preference_pair_accuracy", "preference_delta_vs_linear"},
                )
            row["candidate_support_inclusion"] = parse_bool(
                source["candidate_support_inclusion"],
                f"CSV candidate support at line {line_number}",
            )
            row["exact_fallback"] = parse_bool(
                source["exact_fallback"],
                f"CSV exact fallback at line {line_number}",
            )
            row["harmful_intervention"] = parse_bool(
                source["harmful_intervention"],
                f"CSV harmful intervention at line {line_number}",
            )
            if row["preference_pairs"] < 0.0 or row["preference_correct"] < 0.0:
                raise RuntimeError("Negative preference count in per-user CSV")
            if row["preference_correct"] > row["preference_pairs"] + 1e-12:
                raise RuntimeError("Preference correct count exceeds pair count")
            if row["accepted"] not in {0.0, 1.0}:
                raise RuntimeError("Acceptance indicator is not binary")
            grouped[seed][method].append(row)
    if not seen:
        raise RuntimeError("Per-user metrics CSV is empty")
    reference_users: set[int] | None = None
    for seed in expected_seeds:
        seed_users: set[int] | None = None
        for method in EXPECTED_METHODS:
            rows = grouped[int(seed)][method]
            users = {int(row["user_id"]) for row in rows}
            if len(users) != len(rows) or not users:
                raise RuntimeError(f"Incomplete user rows for seed={seed}, method={method}")
            if seed_users is None:
                seed_users = users
            elif users != seed_users:
                raise RuntimeError(f"Method user cohorts differ for seed {seed}")
            rows.sort(key=lambda row: int(row["user_id"]))
        if reference_users is None:
            reference_users = seed_users
        elif seed_users != reference_users:
            raise RuntimeError("Per-user metric cohorts differ across seeds")
    return grouped


def replay_accepted_pair_bearing_support(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
) -> float:
    """Replay sum_u mean_s[accepted(u,s) * 1(pair-bearing(u,s))]."""
    seeds = sorted(per_seed_rows)
    if not seeds:
        raise RuntimeError("Accepted pair-bearing support has no seeds")
    user_sets = [
        {int(row["user_id"]) for row in per_seed_rows[seed]["ravel"]}
        for seed in seeds
    ]
    if any(users != user_sets[0] for users in user_sets[1:]):
        raise RuntimeError("Accepted pair-bearing support cohorts differ by seed")
    return float(
        sum(
            float(row["accepted"])
            * float(float(row["preference_pairs"]) > 0.0)
            for seed in seeds
            for row in per_seed_rows[seed]["ravel"]
        )
        / len(seeds)
    )


def decode_score_bits(bits: Any, label: str) -> tuple[bytes, float]:
    text = str(bits)
    if len(text) != 8:
        raise RuntimeError(f"{label} is not one float32 bit pattern")
    try:
        payload = bytes.fromhex(text)
    except ValueError as exc:
        raise RuntimeError(f"Malformed float32 bits in {label}") from exc
    if len(payload) != 4:
        raise RuntimeError(f"Malformed float32 width in {label}")
    value = struct.unpack("<f", payload)[0]
    if not math.isfinite(value):
        raise RuntimeError(f"Nonfinite float32 bits in {label}")
    return payload, float(value)


def canonical_ranking_record(
    union: Sequence[int], ranking: Sequence[int], score_bits: Sequence[Any], label: str
) -> bytes:
    union_items = [int(item) for item in union]
    ranked_items = [int(item) for item in ranking]
    if len(set(union_items)) != len(union_items):
        raise RuntimeError(f"Duplicate union item in {label}")
    if len(ranked_items) != len(union_items) or set(ranked_items) != set(union_items):
        raise RuntimeError(f"Full ranking is not a union permutation in {label}")
    if len(score_bits) != len(union_items):
        raise RuntimeError(f"Score-bit vector length mismatch in {label}")
    by_item: dict[int, bytes] = {}
    for item, bits in zip(union_items, score_bits):
        by_item[item] = decode_score_bits(bits, f"{label} score for item {item}")[0]
    try:
        item_bytes = b"".join(struct.pack("<i", item) for item in ranked_items)
    except struct.error as exc:
        raise RuntimeError(f"Out-of-range item index in {label}") from exc
    return item_bytes + b"".join(by_item[item] for item in ranked_items)


def top_score_bits(
    union: Sequence[int], ranking: Sequence[int], score_bits: Sequence[Any], k: int = 10
) -> list[str]:
    by_item = {int(item): str(bits) for item, bits in zip(union, score_bits)}
    return [by_item[int(item)] for item in ranking[:k]]


def canonical_top_record(
    union: Sequence[int], ranking: Sequence[int], score_bits: Sequence[Any], k: int = 10
) -> bytes:
    ranked_items = [int(item) for item in ranking[:k]]
    if len(ranked_items) != k or len(set(ranked_items)) != k:
        raise RuntimeError("Canonical top-k record has duplicate or missing items")
    by_item: dict[int, bytes] = {}
    if len(union) != len(score_bits):
        raise RuntimeError("Canonical top-k score-bit vector length mismatch")
    for item, bits in zip(union, score_bits):
        by_item[int(item)] = decode_score_bits(bits, "canonical top-k score")[0]
    if not set(ranked_items).issubset(by_item):
        raise RuntimeError("Canonical top-k record contains a non-union item")
    return b"".join(struct.pack("<i", item) for item in ranked_items) + b"".join(
        by_item[item] for item in ranked_items
    )


def require_hex_record(
    record: bytes, claimed_hex: Any, claimed_sha256: Any, label: str
) -> None:
    if str(claimed_hex).casefold() != record.hex():
        raise RuntimeError(f"Canonical record bytes mismatch: {label}")
    if str(claimed_sha256).casefold() != sha256_bytes(record):
        raise RuntimeError(f"Canonical record SHA-256 mismatch: {label}")


def require_projection_invariants(
    *,
    union: Sequence[int],
    default_ranking: Sequence[int],
    proposal_ranking: Sequence[int],
    linear_values: Sequence[float],
    proposal_values: Sequence[float],
    scale: float,
    tie_width: float,
    projection_k: int,
    label: str,
) -> None:
    linear_by_item = {int(item): float(value) for item, value in zip(union, linear_values)}
    adjusted_by_item = {
        int(item): float(value) for item, value in zip(union, proposal_values)
    }
    residual_by_item = {
        item: adjusted_by_item[item] - linear_by_item[item] for item in linear_by_item
    }
    selected = [int(item) for item in proposal_ranking[:projection_k]]
    default = [int(item) for item in default_ranking[:projection_k]]
    rank = {item: position for position, item in enumerate(selected)}
    protected_gap = tie_width * scale
    if math.isfinite(tie_width):
        for higher in selected:
            for lower in selected:
                if linear_by_item[higher] > linear_by_item[lower] + protected_gap:
                    if rank[higher] > rank[lower]:
                        raise RuntimeError(f"Protected linear precedence violated: {label}")
    incoming = sorted(set(selected) - set(default))
    outgoing = sorted(set(default) - set(selected))
    if len(incoming) != len(outgoing):
        raise RuntimeError(f"Membership swap cardinality mismatch: {label}")
    edges: dict[int, list[int]] = {}
    for candidate in incoming:
        edges[candidate] = [
            removed
            for removed in outgoing
            if (
                (not math.isfinite(tie_width))
                or abs(linear_by_item[candidate] - linear_by_item[removed]) / scale
                <= tie_width + 1e-12
            )
            and residual_by_item[candidate] - residual_by_item[removed] > 0.0
            and adjusted_by_item[candidate] - adjusted_by_item[removed] > 0.0
        ]
    matched_outgoing: dict[int, int] = {}

    def augment(candidate: int, visited: set[int]) -> bool:
        for removed in edges[candidate]:
            if removed in visited:
                continue
            visited.add(removed)
            if removed not in matched_outgoing or augment(
                matched_outgoing[removed], visited
            ):
                matched_outgoing[removed] = candidate
                return True
        return False

    if any(not augment(candidate, set()) for candidate in incoming):
        raise RuntimeError(f"No valid perfect matching for proposal swaps: {label}")
    linear_rank = {int(item): position for position, item in enumerate(default_ranking)}
    if math.isfinite(tie_width):
        # Finite proposals have authority only over the constrained top-k.  The
        # rest of the immutable union must retain the frozen linear order.
        tail_source = list(map(int, default_ranking))
    else:
        # Infinite width is retained only for local implementation diagnostics;
        # it is not a registered gate comparator.
        tail_source = sorted(
            map(int, union),
            key=lambda item: (
                -adjusted_by_item[item],
                linear_rank[item],
                item,
            ),
        )
    expected_tail = [item for item in tail_source if item not in set(selected)]
    if list(map(int, proposal_ranking[projection_k:])) != expected_tail:
        tail_semantics = "frozen-linear" if math.isfinite(tie_width) else "adjusted-score"
        raise RuntimeError(
            f"Proposal tail is not in registered {tail_semantics} order: {label}"
        )


def require_selected_finite_always_on_alias(
    *,
    proposal_ranking: Sequence[int],
    proposal_bits: Sequence[Any],
    always_ranking: Sequence[int],
    always_bits: Sequence[Any],
    binding_flag: Any,
    accepted: bool | None = None,
    exact_fallback: bool | None = None,
    label: str,
) -> None:
    if binding_flag is not True:
        raise RuntimeError(
            f"Always-on control is not bound to the selected finite proposal: {label}"
        )
    if list(map(int, always_ranking)) != list(map(int, proposal_ranking)) or list(
        always_bits
    ) != list(proposal_bits):
        raise RuntimeError(
            f"Always-on control is not the exact selected finite proposal: {label}"
        )
    if accepted is not None and accepted is not True:
        raise RuntimeError(
            f"Always-on control did not serve the finite proposal unconditionally: {label}"
        )
    if exact_fallback is not None and exact_fallback is not False:
        raise RuntimeError(f"Always-on control was marked as a fallback: {label}")


def audit_float32_array_evidence(
    raw: Any, label: str, expected_length: int
) -> bytes:
    record = require_mapping(raw, f"{label} float32 evidence")
    if record.get("dtype") != "little-endian-float32":
        raise RuntimeError(f"Unexpected dtype in {label} query evidence")
    shape = [
        parse_int(value, f"{label} shape")
        for value in require_sequence(record.get("shape"), f"{label} shape")
    ]
    if shape != [expected_length]:
        raise RuntimeError(f"Unexpected query shape for {label}: {shape}")
    try:
        payload = bytes.fromhex(str(record.get("bytes_hex", "")))
    except ValueError as exc:
        raise RuntimeError(f"Malformed query bytes for {label}") from exc
    if len(payload) != expected_length * 4:
        raise RuntimeError(f"Query byte length mismatch for {label}")
    if str(record.get("sha256", "")).casefold() != sha256_bytes(payload):
        raise RuntimeError(f"Query SHA-256 mismatch for {label}")
    values = struct.unpack(f"<{expected_length}f", payload)
    if not all(math.isfinite(value) for value in values):
        raise RuntimeError(f"Nonfinite query value for {label}")
    return payload


def stable_branch_union(
    collaborative: Sequence[int], semantic: Sequence[int]
) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for item in (*collaborative, *semantic):
        value = int(item)
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def audit_candidate_context_record(
    candidate: Mapping[str, Any],
    *,
    expected_collaborative_index_sha256: str,
    expected_semantic_index_sha256: str,
    collaborative_dimension: int,
    semantic_dimension: int,
    additional_query_names: Sequence[str] = (),
    selected_bpr_variant: str | None = None,
    label: str,
) -> None:
    collaborative = [
        int(item)
        for item in require_sequence(
            candidate.get("selected_bpr_candidates_B"), f"{label} collaborative branch"
        )
    ]
    semantic = [
        int(item)
        for item in require_sequence(
            candidate.get("semantic_candidates_S"), f"{label} semantic branch"
        )
    ]
    union = [
        int(item)
        for item in require_sequence(
            candidate.get("union_candidates_C"), f"{label} candidate union"
        )
    ]
    if (
        len(set(collaborative)) != len(collaborative)
        or len(set(semantic)) != len(semantic)
        or len(set(union)) != len(union)
        or union != stable_branch_union(collaborative, semantic)
        or candidate.get("B_subset_C") is not True
    ):
        raise RuntimeError(f"Branch/union construction mismatch: {label}")
    provenance = require_mapping(
        candidate.get("candidate_context_provenance"),
        f"{label} candidate context provenance",
    )
    index_hashes = require_mapping(
        provenance.get("index_sha256"), f"{label} index hashes"
    )
    if (
        str(index_hashes.get("collaborative_memory", "")).casefold()
        != expected_collaborative_index_sha256.casefold()
        or str(index_hashes.get("semantic_memory", "")).casefold()
        != expected_semantic_index_sha256.casefold()
    ):
        raise RuntimeError(f"Candidate context/index hash mismatch: {label}")
    ranks = require_mapping(
        provenance.get("branch_rank_by_union_position"), f"{label} branch ranks"
    )
    memberships = require_mapping(
        provenance.get("branch_membership_by_union_position"),
        f"{label} branch membership",
    )
    collaborative_rank = {item: position for position, item in enumerate(collaborative)}
    semantic_rank = {item: position for position, item in enumerate(semantic)}
    expected_ranks = {
        "collaborative": [collaborative_rank.get(item, -1) for item in union],
        "semantic": [semantic_rank.get(item, -1) for item in union],
    }
    expected_membership = {
        "collaborative": [item in collaborative_rank for item in union],
        "semantic": [item in semantic_rank for item in union],
    }
    require_canonical_equal(ranks, expected_ranks, f"{label} branch ranks")
    require_canonical_equal(
        memberships, expected_membership, f"{label} branch membership"
    )
    seen_filter = require_mapping(
        provenance.get("seen_filter"), f"{label} seen-filter evidence"
    )
    seen = [
        int(item)
        for item in require_sequence(
            seen_filter.get("seen_item_indices"), f"{label} seen items"
        )
    ]
    actual_overlap = len((set(collaborative) | set(semantic)) & set(seen))
    if (
        seen != sorted(set(seen))
        or int(seen_filter.get("candidate_seen_overlap_count", -1)) != actual_overlap
        or actual_overlap != 0
        or seen_filter.get("all_candidates_unseen") is not True
        or not is_sha256(seen_filter.get("prefix_rows_sha256"))
    ):
        raise RuntimeError(f"Seen-item filtering evidence failed: {label}")
    history_count = parse_int(candidate.get("history_event_count"), f"{label} history count")
    if history_count < len(seen):
        raise RuntimeError(f"Seen-set cardinality exceeds history length: {label}")
    features = require_mapping(
        provenance.get("target_blind_context_features"),
        f"{label} target-blind context features",
    )
    for name in (
        "history_log_feature",
        "bpr_q05",
        "bpr_q95_minus_q05",
        "semantic_q05",
        "semantic_q95_minus_q05",
    ):
        parse_float(features.get(name), f"{label} {name}")
    if not isinstance(features.get("regret_scale_degenerate"), bool):
        raise RuntimeError(f"Malformed regret-scale flag: {label}")

    query_records = require_mapping(
        provenance.get("query_records"), f"{label} query records"
    )
    expected_names = {"collaborative", "semantic", "dislike", *additional_query_names}
    if set(query_records) != expected_names:
        raise RuntimeError(f"Query record set mismatch: {label}")
    query_bytes = {
        "collaborative": audit_float32_array_evidence(
            query_records["collaborative"], f"{label} collaborative", collaborative_dimension
        ),
        "semantic": audit_float32_array_evidence(
            query_records["semantic"], f"{label} semantic", semantic_dimension
        ),
        "dislike": audit_float32_array_evidence(
            query_records["dislike"], f"{label} dislike", semantic_dimension
        ),
    }
    for name in additional_query_names:
        query_bytes[name] = audit_float32_array_evidence(
            query_records[name], f"{label} {name}", collaborative_dimension
        )
    if selected_bpr_variant is not None:
        selected_name = (
            "implicit_bpr" if selected_bpr_variant == "implicit" else "rating_aware_bpr"
        )
        if selected_name not in query_bytes or query_bytes["collaborative"] != query_bytes[
            selected_name
        ]:
            raise RuntimeError(f"Selected collaborative query alias mismatch: {label}")


def audit_prefix_candidate_manifests(
    run_directory: Path,
    result: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    provenance = require_mapping(result.get("provenance"), "result provenance")
    manifests = require_mapping(
        provenance.get("candidate_manifests"), "candidate manifest provenance"
    )
    files = [
        str(value) for value in require_sequence(manifests.get("files"), "manifest files")
    ]
    hashes = require_mapping(manifests.get("sha256"), "manifest hashes")
    paths = [
        contained_file(run_directory, name, "prefix candidate manifest")
        for name in files
        if name.startswith("alignment_manifest_")
        or name.startswith("validation_manifest_")
    ]
    expected_seeds = {int(seed) for seed in config["replicate_seeds"]}
    expected_keys = {
        (stage, variant, seed)
        for stage in ("alignment", "validation")
        for variant in ("implicit", "rating_aware")
        for seed in expected_seeds
    }
    seen_keys: set[tuple[str, str, int]] = set()
    semantic_indexes = list(run_directory.glob("semantic_index_*_seq001.faiss"))
    if len(semantic_indexes) != 1:
        raise RuntimeError("Expected one semantic index for candidate audit")
    semantic_hash = sha256_file(semantic_indexes[0])
    request_rows = 0
    cohort: set[int] | None = None
    for path in paths:
        if str(hashes.get(path.name, "")).casefold() != sha256_file(path):
            raise RuntimeError("Prefix candidate manifest hash mismatch")
        manifest = read_json_mapping(path, "prefix candidate manifest")
        schema = str(manifest.get("schema", ""))
        if schema == "ravel-target-blind-alignment-manifest-v1":
            stage = "alignment"
            if manifest.get("created_before_R_label_join") is not True:
                raise RuntimeError("Alignment manifest target barrier failed")
        elif schema == "ravel-target-blind-validation-manifest-v1":
            stage = "validation"
            if manifest.get("created_before_V_label_join") is not True:
                raise RuntimeError("Validation manifest target barrier failed")
        else:
            raise RuntimeError("Unexpected prefix candidate manifest schema")
        variant = str(manifest.get("variant", ""))
        seed = parse_int(manifest.get("seed"), "prefix manifest seed")
        key = (stage, variant, seed)
        if key not in expected_keys or key in seen_keys:
            raise RuntimeError("Duplicate or unregistered prefix candidate manifest")
        seen_keys.add(key)
        bpr_indexes = list(
            run_directory.glob(f"bpr_{variant}_index_seed{seed}_*_seq001.faiss")
        )
        if len(bpr_indexes) != 1:
            raise RuntimeError("Expected one BPR index for prefix candidate manifest")
        collaborative_hash = sha256_file(bpr_indexes[0])
        if (
            str(manifest.get("collaborative_index_memory_sha256", "")).casefold()
            != collaborative_hash
            or str(manifest.get("semantic_index_memory_sha256", "")).casefold()
            != semantic_hash
        ):
            raise RuntimeError("Prefix manifest/index file hash mismatch")
        entries = require_sequence(manifest.get("entries"), "prefix manifest entries")
        users: set[int] = set()
        for entry_raw in entries:
            entry = require_mapping(entry_raw, "prefix candidate entry")
            user_id = parse_int(entry.get("user_id"), "prefix candidate user")
            if user_id in users:
                raise RuntimeError("Duplicate user in prefix candidate manifest")
            users.add(user_id)
            if (
                entry.get("stage") != stage
                or entry.get("bpr_variant") != variant
                or entry.get("future_block_labels_joined") is not False
            ):
                raise RuntimeError("Prefix candidate entry target barrier mismatch")
            audit_candidate_context_record(
                entry,
                expected_collaborative_index_sha256=collaborative_hash,
                expected_semantic_index_sha256=semantic_hash,
                collaborative_dimension=int(config["bpr"]["embedding_dimension"]),
                semantic_dimension=384,
                label=f"{stage}/{variant}/seed{seed}/user{user_id}",
            )
        if cohort is None:
            cohort = users
        elif users != cohort:
            raise RuntimeError("Prefix candidate manifest cohorts differ")
        request_rows += len(entries)
    if seen_keys != expected_keys or cohort is None:
        raise RuntimeError("Prefix candidate manifest coverage is incomplete")
    return {
        "manifest_count": len(paths),
        "request_rows": request_rows,
        "cohort_users": len(cohort),
        "query_bytes_and_hashes_verified": True,
        "branch_ranks_membership_seen_filter_verified": True,
        "index_hashes_verified": True,
    }


def audit_test_manifests(
    run_directory: Path,
    result: Mapping[str, Any],
    config: Mapping[str, Any],
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
    runner_module: Any,
) -> tuple[Mapping[int, Mapping[str, Any]], Sequence[Path]]:
    provenance = require_mapping(result.get("provenance"), "result provenance")
    manifests = require_mapping(
        provenance.get("candidate_manifests"), "candidate manifest provenance"
    )
    declared_files = [
        str(value) for value in require_sequence(manifests.get("files"), "manifest files")
    ]
    declared_hashes = require_mapping(manifests.get("sha256"), "manifest hashes")
    test_records = require_mapping(manifests.get("test"), "test manifest records")
    selection_locks = require_mapping(
        result.get("selection_locks"), "result selection locks"
    )
    selection = require_mapping(
        selection_locks.get("selector_and_controls"), "selected policy"
    )
    selected_budget = parse_float(
        selection.get("linear_regret_budget"), "selected linear-regret budget"
    )
    selected_tie_width = parse_float(
        selection.get("tie_width"), "selected near-tie width"
    )
    if selected_budget < 0.0:
        raise RuntimeError("Selected linear-regret budget is negative")
    proposal_config = require_mapping(config.get("proposal"), "proposal config")
    quantiles = (
        parse_float(
            proposal_config.get("linear_score_scale_lower_quantile"),
            "proposal lower quantile",
        ),
        parse_float(
            proposal_config.get("linear_score_scale_upper_quantile"),
            "proposal upper quantile",
        ),
    )
    scale_floor = parse_float(
        proposal_config.get("linear_score_scale_floor"), "proposal scale floor"
    )
    projection_k = parse_int(
        proposal_config.get("projection_k"), "proposal projection k"
    )
    if projection_k != 10:
        raise RuntimeError("Verifier supports only the registered top-10 projection")
    expected_seed_keys = {str(seed) for seed in per_seed_rows}
    if set(map(str, test_records)) != expected_seed_keys:
        raise RuntimeError("Test-manifest seed keys do not match the CSV seeds")
    audit_by_seed: dict[int, Mapping[str, Any]] = {}
    paths: list[Path] = []
    for seed in sorted(per_seed_rows):
        record = require_mapping(
            test_records.get(str(seed)), f"test manifest record for seed {seed}"
        )
        path = contained_file(
            run_directory, str(record.get("file", "")), "test output manifest"
        )
        if path.name not in declared_files:
            raise RuntimeError("Test manifest is absent from the declared manifest set")
        actual_hash = sha256_file(path)
        if (
            str(record.get("sha256", "")).casefold() != actual_hash
            or str(declared_hashes.get(path.name, "")).casefold() != actual_hash
        ):
            raise RuntimeError(f"Test manifest hash mismatch for seed {seed}")
        manifest = read_json_mapping(path, f"test output manifest seed {seed}")
        if manifest.get("schema") != "ravel-target-blind-test-output-manifest-v1":
            raise RuntimeError("Unexpected test-output manifest schema")
        if int(manifest.get("seed", -1)) != seed:
            raise RuntimeError("Test-output manifest seed mismatch")
        if str(manifest.get("protocol_sha256", "")).casefold() != str(
            result.get("protocol_sha256", "")
        ).casefold():
            raise RuntimeError("Test-output manifest protocol mismatch")
        if (
            manifest.get("created_before_T_label_join") is not True
            or manifest.get("full_union_ranking_and_score_bits_persisted") is not True
        ):
            raise RuntimeError("Test-output manifest is not target-blind and complete")
        if str(manifest.get("selector_lock_file", "")) != str(
            selection_locks.get("selector_lock_file", "")
        ) or str(manifest.get("selector_lock_sha256", "")).casefold() != str(
            selection_locks.get("selector_lock_sha256", "")
        ).casefold():
            raise RuntimeError("Test manifest names a different selector lock")
        selected_variant = str(selection_locks.get("selected_bpr_variant", ""))
        if (
            selected_variant not in {"implicit", "rating_aware"}
            or manifest.get("selected_bpr_variant") != selected_variant
        ):
            raise RuntimeError("Test manifest selected-BPR identity mismatch")
        semantic_index_paths = list(
            run_directory.glob("semantic_index_*_seq001.faiss")
        )
        implicit_index_paths = list(
            run_directory.glob(f"bpr_implicit_index_seed{seed}_*_seq001.faiss")
        )
        rating_index_paths = list(
            run_directory.glob(
                f"bpr_rating_aware_index_seed{seed}_*_seq001.faiss"
            )
        )
        if (
            len(semantic_index_paths) != 1
            or len(implicit_index_paths) != 1
            or len(rating_index_paths) != 1
        ):
            raise RuntimeError("Test manifest index-file cardinality mismatch")
        semantic_index_hash = sha256_file(semantic_index_paths[0])
        implicit_index_hash = sha256_file(implicit_index_paths[0])
        rating_index_hash = sha256_file(rating_index_paths[0])
        collaborative_index_hash = (
            implicit_index_hash if selected_variant == "implicit" else rating_index_hash
        )
        expected_index_fields = {
            "collaborative_index_memory_sha256": collaborative_index_hash,
            "implicit_index_memory_sha256": implicit_index_hash,
            "rating_aware_index_memory_sha256": rating_index_hash,
            "semantic_index_memory_sha256": semantic_index_hash,
        }
        for field, expected_hash in expected_index_fields.items():
            if str(manifest.get(field, "")).casefold() != expected_hash:
                raise RuntimeError(f"Test manifest index hash mismatch: {field}")
        entries = require_sequence(manifest.get("entries"), "test manifest entries")
        if int(record.get("entries", -1)) != len(entries):
            raise RuntimeError("Test manifest entry count mismatch")
        csv_users = {
            int(row["user_id"]) for row in per_seed_rows[seed]["ravel"]
        }
        by_method_user = {
            method: {int(row["user_id"]): row for row in per_seed_rows[seed][method]}
            for method in EXPECTED_METHODS
        }
        seen_users: set[int] = set()
        maximum_regret = 0.0
        exact_fallback = True
        support = True
        for position, entry_raw in enumerate(entries):
            entry = require_mapping(entry_raw, f"test entry {position}")
            user_id = parse_int(entry.get("user_id"), "test-manifest user ID")
            if user_id in seen_users or user_id not in csv_users:
                raise RuntimeError("Duplicate or unregistered test-manifest user")
            seen_users.add(user_id)
            if (
                entry.get("target_labels_joined") is not False
                or entry.get("all_choices_frozen_before_test_manifest") is not True
            ):
                raise RuntimeError("A test entry is not explicitly target blind")
            forbidden = {
                "test_targets",
                "test_ratings",
                "target_items",
                "target_ratings",
                "heldout_ratings",
            }
            if forbidden & set(map(str, entry)):
                raise RuntimeError("A test entry contains forbidden target-label fields")
            candidate_record = require_mapping(
                entry.get("candidate_manifest"), "embedded test candidate manifest"
            )
            if (
                parse_int(candidate_record.get("user_id"), "embedded candidate user")
                != user_id
                or candidate_record.get("target_labels_joined") is not False
                or candidate_record.get(
                    "queries_use_same_train_alignment_validation_prefix"
                )
                is not True
            ):
                raise RuntimeError("Embedded test candidate target barrier mismatch")
            audit_candidate_context_record(
                candidate_record,
                expected_collaborative_index_sha256=collaborative_index_hash,
                expected_semantic_index_sha256=semantic_index_hash,
                collaborative_dimension=int(config["bpr"]["embedding_dimension"]),
                semantic_dimension=384,
                additional_query_names=("implicit_bpr", "rating_aware_bpr"),
                selected_bpr_variant=selected_variant,
                label=f"test/seed{seed}/user{user_id}",
            )
            collaborative = [
                int(item)
                for item in require_sequence(
                    entry.get("selected_bpr_candidates_B"), "collaborative candidates"
                )
            ]
            semantic = [
                int(item)
                for item in require_sequence(
                    entry.get("semantic_candidates_S"), "semantic candidates"
                )
            ]
            union = [
                int(item)
                for item in require_sequence(
                    entry.get("union_candidates_C"), "union candidates"
                )
            ]
            if (
                collaborative
                != [
                    int(item)
                    for item in candidate_record["selected_bpr_candidates_B"]
                ]
                or semantic
                != [int(item) for item in candidate_record["semantic_candidates_S"]]
                or union != [int(item) for item in candidate_record["union_candidates_C"]]
            ):
                raise RuntimeError("Policy/candidate branch records disagree")
            provenance_record = require_mapping(
                candidate_record.get("candidate_context_provenance"),
                "embedded test candidate provenance",
            )
            seen_indices = set(
                int(item)
                for item in require_sequence(
                    require_mapping(
                        provenance_record.get("seen_filter"), "test seen filter"
                    ).get("seen_item_indices"),
                    "test seen items",
                )
            )
            for branch_name in (
                "implicit_bpr_candidates",
                "rating_aware_bpr_candidates",
            ):
                branch = [
                    int(item)
                    for item in require_sequence(
                        candidate_record.get(branch_name), branch_name
                    )
                ]
                if (
                    len(branch) > int(config["retrieval"]["collaborative_candidates"])
                    or len(set(branch)) != len(branch)
                    or set(branch) & seen_indices
                ):
                    raise RuntimeError(f"Test auxiliary branch evidence failed: {branch_name}")
            if (
                not union
                or len(union) > int(config["retrieval"]["maximum_union_candidates"])
                or len(collaborative)
                > int(config["retrieval"]["collaborative_candidates"])
                or len(semantic) > int(config["retrieval"]["semantic_candidates"])
                or len(set(union)) != len(union)
                or len(set(collaborative)) != len(collaborative)
                or len(set(semantic)) != len(semantic)
            ):
                raise RuntimeError("Invalid candidate cardinality or duplicate item")
            actual_support = set(collaborative).issubset(union)
            semantic_support = set(semantic).issubset(union)
            if entry.get("B_subset_C") is not True or not actual_support or not semantic_support:
                raise RuntimeError("Candidate manifest violates branch support inclusion")
            support = support and actual_support

            linear_ranking = [
                int(item)
                for item in require_sequence(
                    entry.get("linear_full_union_ranking"), "linear full ranking"
                )
            ]
            linear_bits = require_sequence(
                entry.get("linear_union_score_bits_by_union_item"),
                "linear union score bits",
            )
            linear_record = canonical_ranking_record(
                union, linear_ranking, linear_bits, "linear output"
            )
            require_hex_record(
                linear_record,
                entry.get("linear_canonical_full_union_record_hex"),
                entry.get("linear_canonical_full_union_record_sha256"),
                "linear full union",
            )
            linear_top = [
                int(item)
                for item in require_sequence(entry.get("linear_top10"), "linear top10")
            ]
            if linear_top != linear_ranking[:10] or [
                str(value) for value in require_sequence(
                    entry.get("linear_top10_score_bits"), "linear top10 score bits"
                )
            ] != top_score_bits(union, linear_ranking, linear_bits):
                raise RuntimeError("Linear top10 is inconsistent with its full record")
            require_hex_record(
                canonical_top_record(union, linear_ranking, linear_bits),
                entry.get("linear_canonical_top10_record_hex"),
                entry.get("linear_canonical_top10_record_sha256"),
                "linear top10",
            )

            proposal_ranking = [
                int(item)
                for item in require_sequence(
                    entry.get("proposal_full_union_ranking"), "proposal full ranking"
                )
            ]
            proposal_bits = require_sequence(
                entry.get("proposal_union_score_bits_by_union_item"),
                "proposal union score bits",
            )
            canonical_ranking_record(union, proposal_ranking, proposal_bits, "proposal")
            proposal_top = [
                int(item)
                for item in require_sequence(entry.get("proposal_top10"), "proposal top10")
            ]
            if proposal_top != proposal_ranking[:10] or [
                str(value) for value in require_sequence(
                    entry.get("proposal_top10_score_bits"), "proposal top10 score bits"
                )
            ] != top_score_bits(union, proposal_ranking, proposal_bits):
                raise RuntimeError("Proposal top10 is inconsistent with its full record")
            proposal_changed = parse_bool(
                entry.get("proposal_changed"), "proposal_changed"
            )
            if proposal_changed != (proposal_top != linear_top):
                raise RuntimeError("proposal_changed disagrees with the top10 records")

            always_ranking = [
                int(item)
                for item in require_sequence(
                    entry.get("always_on_full_union_ranking"), "always-on full ranking"
                )
            ]
            always_bits = require_sequence(
                entry.get("always_on_union_score_bits_by_union_item"),
                "always-on score bits",
            )
            canonical_ranking_record(union, always_ranking, always_bits, "always-on")
            require_selected_finite_always_on_alias(
                proposal_ranking=proposal_ranking,
                proposal_bits=proposal_bits,
                always_ranking=always_ranking,
                always_bits=always_bits,
                binding_flag=entry.get(
                    "always_on_uses_same_selected_finite_proposal"
                ),
                label=f"seed {seed}, user {user_id}, manifest",
            )
            if [
                int(item)
                for item in require_sequence(entry.get("always_on_top10"), "always top10")
            ] != always_ranking[:10]:
                raise RuntimeError("Always-on top10 is inconsistent with its full record")

            linear_values = [
                decode_score_bits(bits, "linear score")[1] for bits in linear_bits
            ]
            proposal_values = [
                decode_score_bits(bits, "proposal score")[1] for bits in proposal_bits
            ]
            scale_values = runner_module.np.asarray(linear_values, dtype=runner_module.np.float64)
            lower, upper = runner_module.np.quantile(scale_values, list(quantiles))
            scale = max(float(upper - lower), scale_floor)
            linear_by_item = dict(zip(union, linear_values))
            default_sum = sum(linear_by_item[item] for item in linear_ranking[:projection_k])

            def replay_regret(ranking: Sequence[int]) -> float:
                return max(
                    0.0,
                    (
                        default_sum
                        - sum(linear_by_item[int(item)] for item in ranking[:projection_k])
                    )
                    / scale,
                )

            proposal_regret = replay_regret(proposal_ranking)
            claimed_regret = parse_float(
                entry.get("proposal_linear_regret"), "proposal linear regret"
            )
            if not math.isclose(
                proposal_regret, claimed_regret, rel_tol=1e-7, abs_tol=1e-7
            ):
                raise RuntimeError("Proposal linear regret does not replay")
            if proposal_regret > selected_budget + 1e-7:
                raise RuntimeError("Proposal exceeds the selected linear-regret budget")
            always_regret = replay_regret(always_ranking)
            if always_regret > selected_budget + 1e-7:
                raise RuntimeError("Always-on proposal exceeds the selected regret budget")
            fail_reason = entry.get("proposal_fail_closed_reason")
            if fail_reason is not None:
                if (
                    proposal_ranking != linear_ranking
                    or list(proposal_bits) != list(linear_bits)
                    or claimed_regret != 0.0
                ):
                    raise RuntimeError("Fail-closed proposal is not the exact linear record")
            else:
                require_projection_invariants(
                    union=union,
                    default_ranking=linear_ranking,
                    proposal_ranking=proposal_ranking,
                    linear_values=linear_values,
                    proposal_values=proposal_values,
                    scale=scale,
                    tie_width=selected_tie_width,
                    projection_k=projection_k,
                    label=f"seed {seed}, user {user_id}, selected proposal",
                )
            maximum_regret = max(maximum_regret, claimed_regret)

            decisions = require_mapping(entry.get("decisions"), "test decisions")
            outputs = require_mapping(entry.get("outputs"), "test outputs")
            if set(decisions) != set(POLICY_OUTPUT_METHODS) or set(outputs) != set(
                POLICY_OUTPUT_METHODS
            ):
                raise RuntimeError("Test output method set is not the registered set")
            for method in POLICY_OUTPUT_METHODS:
                output = require_mapping(outputs[method], f"{method} output")
                accepted = parse_bool(output.get("accepted"), f"{method} accepted")
                if accepted != parse_bool(decisions[method], f"{method} decision"):
                    raise RuntimeError(f"Decision/output acceptance mismatch: {method}")
                output_ranking = [
                    int(item)
                    for item in require_sequence(
                        output.get("full_union_ranking"), f"{method} full ranking"
                    )
                ]
                output_bits = require_sequence(
                    output.get("union_score_bits_by_union_item"),
                    f"{method} score bits",
                )
                output_record = canonical_ranking_record(
                    union, output_ranking, output_bits, f"{method} output"
                )
                require_hex_record(
                    output_record,
                    output.get("canonical_full_union_record_hex"),
                    output.get("canonical_full_union_record_sha256"),
                    f"{method} full union",
                )
                output_top = [
                    int(item)
                    for item in require_sequence(output.get("top10"), f"{method} top10")
                ]
                output_top_bits = [
                    str(value)
                    for value in require_sequence(
                        output.get("top10_score_bits"), f"{method} top10 bits"
                    )
                ]
                if output_top != output_ranking[:10] or output_top_bits != top_score_bits(
                    union, output_ranking, output_bits
                ):
                    raise RuntimeError(f"Top10/full-output mismatch: {method}")
                require_hex_record(
                    canonical_top_record(union, output_ranking, output_bits),
                    output.get("canonical_top10_record_hex"),
                    output.get("canonical_top10_record_sha256"),
                    f"{method} top10",
                )
                expected_ranking = (
                    always_ranking
                    if method == "always_on"
                    else proposal_ranking
                    if accepted
                    else linear_ranking
                )
                expected_bits = (
                    always_bits
                    if method == "always_on"
                    else proposal_bits
                    if accepted
                    else linear_bits
                )
                fallback = parse_bool(
                    output.get("exact_fallback"), f"{method} exact fallback"
                )
                if method == "always_on":
                    require_selected_finite_always_on_alias(
                        proposal_ranking=proposal_ranking,
                        proposal_bits=proposal_bits,
                        always_ranking=output_ranking,
                        always_bits=output_bits,
                        binding_flag=entry.get(
                            "always_on_uses_same_selected_finite_proposal"
                        ),
                        accepted=accepted,
                        exact_fallback=fallback,
                        label=f"seed {seed}, user {user_id}, served output",
                    )
                if output_ranking != list(expected_ranking) or list(output_bits) != list(
                    expected_bits
                ):
                    raise RuntimeError(f"Accepted/rejected alias mismatch: {method}")
                if fallback != (not accepted):
                    raise RuntimeError(f"Fallback flag disagrees with acceptance: {method}")
                if not accepted:
                    exact_fallback = exact_fallback and output_record == linear_record
                csv_row = by_method_user[method][user_id]
                if float(csv_row["accepted"]) != float(accepted):
                    raise RuntimeError(f"Manifest/CSV acceptance mismatch: {method}")
                if bool(csv_row["exact_fallback"]) != fallback:
                    raise RuntimeError(f"Manifest/CSV fallback mismatch: {method}")
                if bool(csv_row["candidate_support_inclusion"]) != actual_support:
                    raise RuntimeError(f"Manifest/CSV support mismatch: {method}")
            selected_bpr_row = by_method_user["selected_bpr"][user_id]
            if (
                float(selected_bpr_row["accepted"]) != 0.0
                or not bool(selected_bpr_row["candidate_support_inclusion"])
            ):
                raise RuntimeError("Selected-BPR CSV control flags are invalid")
        if seen_users != csv_users:
            raise RuntimeError(f"Test manifest does not cover seed {seed}'s CSV users")
        ravel_rows = per_seed_rows[seed]["ravel"]
        audit_by_seed[seed] = {
            "candidate_support_inclusion_all_requests": support,
            "union_candidate_recall_never_below_collaborative": all(
                float(row["union_candidate_recall_at_most_400"]) + 1e-12
                >= float(row["collaborative_candidate_recall_at_200"])
                for row in ravel_rows
            ),
            "exact_fallback_all_rejected_requests": exact_fallback,
            "maximum_linear_anchor_regret": maximum_regret,
            "candidate_targets_injected": False,
        }
        paths.append(path)
    return audit_by_seed, paths


def replay_selector_lock(
    run_directory: Path,
    result: Mapping[str, Any],
    config: Mapping[str, Any],
    runner_module: Any,
) -> tuple[Mapping[str, Any], Path, Path]:
    selection_locks = require_mapping(
        result.get("selection_locks"), "result selection locks"
    )
    lock_path = contained_file(
        run_directory,
        str(selection_locks.get("selector_lock_file", "")),
        "selector lock",
    )
    expected_hash = str(selection_locks.get("selector_lock_sha256", "")).casefold()
    if not is_sha256(expected_hash) or sha256_file(lock_path) != expected_hash:
        raise RuntimeError("Selector-lock SHA-256 mismatch")
    lock = read_json_mapping(lock_path, "selector lock")
    if (
        lock.get("schema") != "ravel-validation-locked-selector-v1"
        or lock.get("created_before_any_T_manifest") is not True
        or lock.get("test_outcomes_used") is not False
        or lock.get("label_reliability_features_used") is not False
    ):
        raise RuntimeError("Selector lock violates the registered target barrier")
    if str(lock.get("protocol_sha256", "")).casefold() != str(
        result.get("protocol_sha256", "")
    ).casefold():
        raise RuntimeError("Selector-lock protocol mismatch")
    selection = require_mapping(lock.get("selection"), "selector-lock selection")
    require_canonical_equal(
        selection,
        selection_locks.get("selector_and_controls"),
        "selector-lock selection",
    )
    if selection_locks.get("all_locked_before_any_T_manifest") is not True:
        raise RuntimeError("Result does not bind selector choices before T manifests")

    provenance = require_mapping(result.get("provenance"), "result provenance")
    manifest_provenance = require_mapping(
        provenance.get("candidate_manifests"), "candidate manifest provenance"
    )
    manifest_files = [
        str(value)
        for value in require_sequence(
            manifest_provenance.get("files"), "candidate manifest files"
        )
    ]
    manifest_hashes = require_mapping(
        manifest_provenance.get("sha256"), "candidate manifest hashes"
    )

    all_evidence_path = contained_file(
        run_directory,
        str(lock.get("all_validation_oof_evidence_file", "")),
        "all validation OOF evidence",
    )
    all_evidence_hash = str(
        lock.get("all_validation_oof_evidence_sha256", "")
    ).casefold()
    if (
        not is_sha256(all_evidence_hash)
        or sha256_file(all_evidence_path) != all_evidence_hash
        or all_evidence_path.name not in manifest_files
        or str(manifest_hashes.get(all_evidence_path.name, "")).casefold()
        != all_evidence_hash
    ):
        raise RuntimeError("All-spec validation OOF evidence hash mismatch")
    all_evidence = read_json_mapping(
        all_evidence_path, "all-spec validation OOF evidence"
    )
    if (
        all_evidence.get("schema") != "ravel-all-validation-oof-evidence-v1"
        or all_evidence.get("test_outcomes_used") is not False
        or str(all_evidence.get("protocol_sha256", "")).casefold()
        != str(result.get("protocol_sha256", "")).casefold()
    ):
        raise RuntimeError("Unexpected all-spec validation evidence schema")
    expected_seeds = [int(seed) for seed in config.get("replicate_seeds", [])]
    registered_specs = {
        runner_module.proposal_spec_key(float(tie), float(regret))
        for tie in config["proposal"]["near_tie_width_grid"]
        for regret in config["proposal"]["linear_regret_budget_grid"]
    }
    records_by_seed_spec: dict[int, dict[str, list[Mapping[str, Any]]]] = {
        seed: {spec: [] for spec in registered_specs} for seed in expected_seeds
    }
    oof_by_seed_spec: dict[
        int, dict[str, dict[tuple[int, int], Mapping[str, float]]]
    ] = {seed: {spec: {} for spec in registered_specs} for seed in expected_seeds}
    seen_all: set[tuple[int, str, int]] = set()
    for position, raw in enumerate(
        require_sequence(all_evidence.get("rows"), "all-spec validation OOF rows")
    ):
        row = require_mapping(raw, f"all-spec validation OOF row {position}")
        seed = parse_int(row.get("seed"), "all-spec validation seed")
        spec = str(row.get("specification", ""))
        user_id = parse_int(row.get("user_id"), "all-spec validation user")
        key = (seed, spec, user_id)
        if (
            seed not in records_by_seed_spec
            or spec not in registered_specs
            or key in seen_all
        ):
            raise RuntimeError("Duplicate or unregistered all-spec validation row")
        seen_all.add(key)
        preference_delta = (
            float("nan")
            if row.get("preference_delta") is None
            else parse_float(
                row.get("preference_delta"), "all-spec validation preference delta"
            )
        )
        ndcg_delta = parse_float(
            row.get("ndcg_delta"), "all-spec validation NDCG delta"
        )
        harmful = parse_bool(row.get("harmful"), "all-spec validation harmful")
        if harmful != (ndcg_delta < 0.0):
            raise RuntimeError("All-spec validation harmful label does not replay")
        record_row = {
            "seed": seed,
            "user_id": user_id,
            "proposal_changed": parse_bool(
                row.get("proposal_changed"), "all-spec proposal_changed"
            ),
            "near_tie_tightness": parse_float(
                row.get("near_tie_tightness"), "all-spec near-tie tightness"
            ),
            "uncertainty_score": parse_float(
                row.get("uncertainty_score"), "all-spec uncertainty score"
            ),
            "preference_delta": preference_delta,
            "ndcg_delta": ndcg_delta,
            "harmful": harmful,
        }
        prediction = {
            "benefit_probability": parse_float(
                row.get("benefit_probability"), "all-spec benefit probability"
            ),
            "harm_probability": parse_float(
                row.get("harm_probability"), "all-spec harm probability"
            ),
            "single_head_probability": parse_float(
                row.get("single_head_probability"),
                "all-spec single-head probability",
            ),
        }
        if any(value < 0.0 or value > 1.0 for value in prediction.values()):
            raise RuntimeError("All-spec selector probability is outside [0,1]")
        records_by_seed_spec[seed][spec].append(record_row)
        oof_by_seed_spec[seed][spec][(seed, user_id)] = prediction
    reference_users: set[int] | None = None
    for seed in expected_seeds:
        for spec in registered_specs:
            rows = records_by_seed_spec[seed][spec]
            predictions = oof_by_seed_spec[seed][spec]
            users = {int(row["user_id"]) for row in rows}
            if not users or len(users) != len(rows) or len(predictions) != len(rows):
                raise RuntimeError("Incomplete all-spec validation OOF evidence")
            if reference_users is None:
                reference_users = users
            elif users != reference_users:
                raise RuntimeError("All-spec validation OOF cohorts differ")
            rows.sort(key=lambda row: int(row["user_id"]))
    replayed_selection = runner_module.select_validation_policy(
        records_by_seed_spec, oof_by_seed_spec, config
    )
    require_canonical_equal(
        replayed_selection, selection, "all-spec validation policy selection"
    )

    evidence_path = contained_file(
        run_directory,
        str(lock.get("selected_validation_oof_evidence_file", "")),
        "selected validation OOF evidence",
    )
    evidence_hash = str(
        lock.get("selected_validation_oof_evidence_sha256", "")
    ).casefold()
    if not is_sha256(evidence_hash) or sha256_file(evidence_path) != evidence_hash:
        raise RuntimeError("Selected validation OOF evidence hash mismatch")
    if evidence_path.name not in manifest_files or str(
        manifest_hashes.get(evidence_path.name, "")
    ).casefold() != evidence_hash:
        raise RuntimeError("Selected validation evidence is outside the manifest lock")
    evidence = read_json_mapping(evidence_path, "selected validation OOF evidence")
    if (
        evidence.get("schema") != "ravel-selected-validation-oof-evidence-v1"
        or evidence.get("test_outcomes_used") is not False
    ):
        raise RuntimeError("Unexpected selected validation OOF evidence schema")
    if str(evidence.get("protocol_sha256", "")).casefold() != str(
        result.get("protocol_sha256", "")
    ).casefold():
        raise RuntimeError("Validation OOF evidence protocol mismatch")
    tie_width = parse_float(selection.get("tie_width"), "selected tie width")
    regret_budget = parse_float(
        selection.get("linear_regret_budget"), "selected regret budget"
    )
    selected_spec = f"tie={tie_width:.12g}|linear_regret={regret_budget:.12g}"
    if str(evidence.get("selected_specification", "")) != selected_spec:
        raise RuntimeError("Validation evidence specification mismatch")
    benefit_threshold = parse_float(
        selection.get("benefit_probability_threshold"), "benefit threshold"
    )
    maximum_harm = parse_float(
        selection.get("maximum_harm_probability"), "maximum harm probability"
    )
    if not math.isclose(
        parse_float(evidence.get("benefit_probability_threshold"), "evidence benefit threshold"),
        benefit_threshold,
        rel_tol=0.0,
        abs_tol=0.0,
    ) or not math.isclose(
        parse_float(evidence.get("maximum_harm_probability"), "evidence harm threshold"),
        maximum_harm,
        rel_tol=0.0,
        abs_tol=0.0,
    ):
        raise RuntimeError("Validation evidence threshold mismatch")
    rows_raw = require_sequence(evidence.get("rows"), "validation OOF rows")
    expected_seed_set = set(expected_seeds)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for position, raw in enumerate(rows_raw):
        row = require_mapping(raw, f"validation OOF row {position}")
        seed = parse_int(row.get("seed"), "validation seed")
        user_id = parse_int(row.get("user_id"), "validation user")
        if seed not in expected_seed_set or (seed, user_id) in seen:
            raise RuntimeError("Duplicate or unregistered validation OOF row")
        seen.add((seed, user_id))
        changed = parse_bool(row.get("proposal_changed"), "validation proposal_changed")
        preference_pairs = parse_int(
            row.get("preference_pairs"), "validation preference-pair count"
        )
        preference_delta = (
            float("nan")
            if row.get("preference_delta") is None
            else parse_float(row.get("preference_delta"), "validation preference delta")
        )
        ndcg_delta = parse_float(row.get("ndcg_delta"), "validation NDCG delta")
        harmful = parse_bool(row.get("harmful"), "validation harmful label")
        benefit_probability = parse_float(
            row.get("benefit_probability"), "validation benefit probability"
        )
        harm_probability = parse_float(
            row.get("harm_probability"), "validation harm probability"
        )
        if not (
            0.0 <= benefit_probability <= 1.0 and 0.0 <= harm_probability <= 1.0
        ):
            raise RuntimeError("Validation selector probability is outside [0,1]")
        accepted = bool(
            changed
            and benefit_probability >= benefit_threshold
            and harm_probability <= maximum_harm
        )
        if accepted != parse_bool(row.get("accepted"), "validation accepted"):
            raise RuntimeError("Validation OOF acceptance does not replay")
        if harmful != (ndcg_delta < 0.0):
            raise RuntimeError("Validation harmful label does not replay")
        if (preference_pairs > 0) != math.isfinite(preference_delta):
            raise RuntimeError("Validation pair count/delta missingness mismatch")
        rows.append(
            {
                "seed": seed,
                "user_id": user_id,
                "proposal_changed": changed,
                "preference_delta": preference_delta,
                "ndcg_delta": ndcg_delta,
                "harmful": harmful,
                "accepted": accepted,
            }
        )
    by_seed: dict[int, set[int]] = defaultdict(set)
    by_user: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_seed[int(row["seed"])].add(int(row["user_id"]))
        by_user[int(row["user_id"])].append(row)
    if set(by_seed) != expected_seed_set or len({len(users) for users in by_seed.values()}) != 1:
        raise RuntimeError("Validation OOF evidence does not cover every seed equally")
    reference_users = next(iter(by_seed.values()))
    if any(users != reference_users for users in by_seed.values()):
        raise RuntimeError("Validation OOF user cohorts differ across seeds")
    accepted_count = sum(bool(row["accepted"]) for row in rows)
    coverage = accepted_count / max(len(rows), 1)
    accepted_pair_rows = [
        row
        for row in rows
        if bool(row["accepted"]) and math.isfinite(float(row["preference_delta"]))
    ]
    accepted_pair_users = {
        int(row["user_id"]) for row in accepted_pair_rows
    }
    policy_ndcg = float(
        sum(
            sum(
                float(row["ndcg_delta"]) if bool(row["accepted"]) else 0.0
                for row in user_rows
            )
            / len(user_rows)
            for user_rows in by_user.values()
        )
        / len(by_user)
    )
    preference_user_values: list[float] = []
    acceptance_by_user: list[float] = []
    harmful_acceptance_by_user: list[float] = []
    for user_rows in by_user.values():
        finite = [
            row
            for row in user_rows
            if math.isfinite(float(row["preference_delta"]))
        ]
        if finite:
            preference_user_values.append(
                sum(
                    float(row["preference_delta"])
                    if bool(row["accepted"])
                    else 0.0
                    for row in finite
                )
                / len(finite)
            )
        acceptance_by_user.append(
            sum(bool(row["accepted"]) for row in user_rows) / len(user_rows)
        )
        harmful_acceptance_by_user.append(
            sum(
                bool(row["accepted"]) and bool(row["harmful"])
                for row in user_rows
            )
            / len(user_rows)
        )
    policy_preference = (
        sum(preference_user_values) / len(preference_user_values)
        if preference_user_values
        else float("nan")
    )
    conditional_preference = (
        sum(float(row["preference_delta"]) for row in accepted_pair_rows)
        / len(accepted_pair_rows)
        if accepted_pair_rows
        else float("nan")
    )
    harmful_rate = sum(harmful_acceptance_by_user) / max(
        sum(acceptance_by_user), 1e-12
    )
    replayed = {
        "coverage": coverage,
        "validation_request_rows": len(rows),
        "validation_accepted_request_rows": accepted_count,
        "validation_accepted_pair_bearing_distinct_users": len(accepted_pair_users),
        "policy_ndcg_delta": policy_ndcg,
        "policy_preference_delta": policy_preference,
        "accepted_conditional_preference_delta": conditional_preference,
        "harmful_intervention_rate": harmful_rate,
        "validation_oof_harmful_intervention_rate": harmful_rate,
    }
    for field, replayed_value in replayed.items():
        selected_value = parse_float(selection.get(field), f"selection {field}")
        if not math.isclose(
            selected_value, float(replayed_value), rel_tol=1e-12, abs_tol=1e-12
        ):
            raise RuntimeError(f"Selected validation statistic does not replay: {field}")
    selector = require_mapping(config.get("selector"), "selector config")
    feasible = bool(
        float(selector["minimum_validation_coverage"])
        <= coverage
        <= float(selector["maximum_validation_coverage"])
        and accepted_count >= int(selector["minimum_validation_accepted_requests"])
        and len(accepted_pair_users)
        >= int(selector["minimum_validation_accepted_pair_users"])
        and policy_ndcg >= float(selector["minimum_validation_ndcg_delta"])
        and math.isfinite(conditional_preference)
        and conditional_preference > 0.0
    )
    if selection.get("validation_selection_feasible") is not feasible or not feasible:
        raise RuntimeError("Selected validation operating point is not feasible on replay")
    return selection, lock_path, evidence_path


def validate_per_user_science(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
    manifest_audit: Mapping[int, Mapping[str, Any]],
    result: Mapping[str, Any],
    runner_module: Any,
) -> Mapping[int, Mapping[str, Any]]:
    result_summaries = require_mapping(
        result.get("per_seed_method_summaries"), "result per-seed summaries"
    )
    result_diagnostics = require_mapping(
        result.get("per_seed_diagnostics"), "result per-seed diagnostics"
    )
    diagnostics: dict[int, Mapping[str, Any]] = {}
    for seed, methods in per_seed_rows.items():
        if set(methods) != set(EXPECTED_METHODS):
            raise RuntimeError("Per-seed method set mismatch")
        by_method_user = {
            method: {int(row["user_id"]): row for row in rows}
            for method, rows in methods.items()
        }
        users = set(by_method_user["linear"])
        for user_id in users:
            linear = by_method_user["linear"][user_id]
            for method in EXPECTED_METHODS:
                row = by_method_user[method][user_id]
                expected_ndcg_delta = float(row["ndcg_at_10"]) - float(
                    linear["ndcg_at_10"]
                )
                if not math.isclose(
                    float(row["ndcg_delta_vs_linear"]),
                    expected_ndcg_delta,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise RuntimeError("Per-user NDCG delta does not replay")
                row_accuracy = float(row["preference_pair_accuracy"])
                linear_accuracy = float(linear["preference_pair_accuracy"])
                expected_preference_delta = (
                    row_accuracy - linear_accuracy
                    if math.isfinite(row_accuracy) and math.isfinite(linear_accuracy)
                    else float("nan")
                )
                actual_preference_delta = float(row["preference_delta_vs_linear"])
                if not (
                    math.isnan(expected_preference_delta)
                    and math.isnan(actual_preference_delta)
                ) and not math.isclose(
                    actual_preference_delta,
                    expected_preference_delta,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise RuntimeError("Per-user preference delta does not replay")
                if float(row["preference_pairs"]) == 0.0:
                    if not math.isnan(row_accuracy):
                        raise RuntimeError("Pair-free user has finite preference accuracy")
                elif not math.isclose(
                    row_accuracy,
                    float(row["preference_correct"])
                    / float(row["preference_pairs"]),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise RuntimeError("Per-user preference accuracy does not replay")
                expected_harm = bool(
                    float(row["accepted"]) > 0.0 and expected_ndcg_delta < 0.0
                )
                if bool(row["harmful_intervention"]) != expected_harm:
                    raise RuntimeError("Per-user harmful-intervention label does not replay")
        recomputed_summaries = {
            method: runner_module.summarize_rows(methods[method])
            for method in EXPECTED_METHODS
        }
        require_canonical_equal(
            recomputed_summaries,
            require_mapping(
                result_summaries.get(str(seed)), f"result summaries for seed {seed}"
            ),
            f"per-seed summaries for {seed}",
        )
        ravel_rows = methods["ravel"]
        accepted = [row for row in ravel_rows if float(row["accepted"]) > 0.0]
        accepted_pair = [
            row
            for row in accepted
            if math.isfinite(float(row["preference_delta_vs_linear"]))
        ]
        derived = {
            "heldout_preference_pairs": int(
                sum(float(row["preference_pairs"]) for row in ravel_rows)
            ),
            "pair_bearing_test_users": sum(
                float(row["preference_pairs"]) > 0.0 for row in ravel_rows
            ),
            "accepted_requests": len(accepted),
            "accepted_pair_bearing_requests": len(accepted_pair),
            "accepted_conditional_preference_uplift": (
                float(
                    runner_module.np.mean(
                        [
                            float(row["preference_delta_vs_linear"])
                            for row in accepted_pair
                        ]
                    )
                )
                if accepted_pair
                else None
            ),
            "harmful_intervention_rate": (
                float(
                    runner_module.np.mean(
                        [bool(row["harmful_intervention"]) for row in accepted]
                    )
                )
                if accepted
                else None
            ),
            **dict(manifest_audit[seed]),
        }
        require_canonical_equal(
            derived,
            require_mapping(
                result_diagnostics.get(str(seed)), f"result diagnostics for seed {seed}"
            ),
            f"per-seed diagnostics for {seed}",
        )
        diagnostics[seed] = derived
    return diagnostics


def validate_latency_evidence(
    run_directory: Path,
    result: Mapping[str, Any],
    config: Mapping[str, Any],
    runner_module: Any,
) -> tuple[Mapping[int, Mapping[str, Any]], Mapping[str, Any]]:
    result_raw = require_mapping(result.get("latency_by_seed"), "latency by seed")
    provenance = require_mapping(result.get("provenance"), "result provenance")
    manifests = require_mapping(
        provenance.get("candidate_manifests"), "candidate manifest provenance"
    )
    manifest_files = [
        str(value) for value in require_sequence(manifests.get("files"), "manifest files")
    ]
    latency_files = [
        name
        for name in manifest_files
        if name.startswith("target_blind_latency_evidence_")
    ]
    if len(latency_files) != 1:
        raise RuntimeError("Expected one pre-T target-blind latency evidence file")
    evidence_path = contained_file(
        run_directory, latency_files[0], "target-blind latency evidence"
    )
    expected_evidence_hash = str(
        require_mapping(manifests.get("sha256"), "manifest hashes").get(
            evidence_path.name, ""
        )
    ).casefold()
    if sha256_file(evidence_path) != expected_evidence_hash:
        raise RuntimeError("Target-blind latency evidence hash mismatch")
    evidence = read_json_mapping(evidence_path, "target-blind latency evidence")
    if (
        evidence.get("schema") != "ravel-target-blind-latency-evidence-v1"
        or evidence.get("created_before_T_label_join") is not True
        or evidence.get("test_labels_or_item_identities_joined") is not False
        or str(evidence.get("protocol_sha256", "")).casefold()
        != str(result.get("protocol_sha256", "")).casefold()
    ):
        raise RuntimeError("Latency evidence violates the pre-T target barrier")
    raw = require_mapping(
        evidence.get("per_seed_raw_user_medians_and_summaries"),
        "latency evidence per-seed rows",
    )
    require_canonical_equal(raw, result_raw, "latency evidence/result summaries")
    expected_seeds = [int(seed) for seed in config.get("replicate_seeds", [])]
    if set(raw) != {str(seed) for seed in expected_seeds}:
        raise RuntimeError("Latency seed keys do not match the registered seeds")
    cohort_path = contained_file(
        run_directory, str(provenance.get("cohort_file", "")), "cohort lock"
    )
    cohort = read_json_mapping(cohort_path, "cohort lock")
    cohort_users = sorted(
        int(user)
        for user in require_sequence(cohort.get("ravel_user_ids"), "cohort users")
    )
    expected_users = min(
        len(cohort_users), int(config["evaluation"]["latency_measured_users"])
    )
    measured_ids = [
        parse_int(value, "latency measured user")
        for value in require_sequence(
            evidence.get("measured_user_ids_numeric_order"), "latency measured users"
        )
    ]
    warmup_ids = [
        parse_int(value, "latency warmup user")
        for value in require_sequence(
            evidence.get("warmup_user_ids_also_measured"), "latency warmup users"
        )
    ]
    if (
        measured_ids != cohort_users[:expected_users]
        or warmup_ids
        != measured_ids[: int(config["evaluation"]["latency_warmup_users"])]
        or int(evidence.get("repetitions", -1))
        != int(config["evaluation"]["latency_repetitions"])
        or evidence.get("interleaving")
        != "AB/BA by (repetition + numeric-user-position) parity"
    ):
        raise RuntimeError("Latency user schedule or interleaving mismatch")
    latency: dict[int, Mapping[str, Any]] = {}
    for seed in expected_seeds:
        record = require_mapping(raw[str(seed)], f"latency seed {seed}")
        if (
            record.get("single_thread_cpu") is not True
            or record.get(
                "includes_both_searches_union_features_default_residual_proposal_selector_sort"
            )
            is not True
            or record.get("abba_interleaving") is not True
            or int(record.get("measured_users", -1)) != expected_users
            or int(record.get("repetitions", -1))
            != int(config["evaluation"]["latency_repetitions"])
        ):
            raise RuntimeError("Latency protocol metadata mismatch")
        replayed_p95: dict[str, float] = {}
        for method in ("linear", "ravel"):
            method_record = require_mapping(record.get(method), f"{method} latency")
            values = [
                parse_float(value, f"{method} per-user median")
                for value in require_sequence(
                    method_record.get("per_user_median_ms"),
                    f"{method} per-user latency medians",
                )
            ]
            if len(values) != expected_users or any(value <= 0.0 for value in values):
                raise RuntimeError("Latency median array has the wrong support")
            array = runner_module.np.asarray(values, dtype=runner_module.np.float64)
            replayed = {
                "p50_ms": float(runner_module.np.percentile(array, 50.0)),
                "p95_ms": float(runner_module.np.percentile(array, 95.0)),
                "mean_of_user_medians_ms": float(runner_module.np.mean(array)),
            }
            for field, value in replayed.items():
                if not math.isclose(
                    parse_float(method_record.get(field), f"{method} {field}"),
                    value,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise RuntimeError(f"Latency summary does not replay: {method}.{field}")
            if method_record.get("aggregation") != (
                "median_across_repetitions_per_user_then_percentile_across_users"
            ):
                raise RuntimeError("Latency aggregation label mismatch")
            replayed_p95[method] = replayed["p95_ms"]
        ratio = replayed_p95["ravel"] / max(replayed_p95["linear"], 1e-12)
        if not math.isclose(
            parse_float(record.get("ravel_to_linear_p95_ratio"), "latency ratio"),
            ratio,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise RuntimeError("Latency p95 ratio does not replay")
        latency[seed] = record
    return latency, {
        "file": evidence_path.name,
        "sha256": expected_evidence_hash,
        "created_before_T_label_join": True,
        "measured_users": expected_users,
        "warmup_users": len(warmup_ids),
        "per_user_medians_and_summaries_replayed": True,
    }


def parse_event_log(path: Path, expected_pid: int) -> Sequence[Mapping[str, Any]]:
    events: list[Mapping[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.endswith("\n"):
                raise RuntimeError("Event log has a nonterminated record")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Malformed event-log line {line_number}") from exc
            event = require_mapping(value, f"event-log line {line_number}")
            if int(event.get("pid", -1)) != expected_pid:
                raise RuntimeError("Event-log PID differs from the runner PID")
            if not isinstance(event.get("utc"), str) or not isinstance(
                event.get("event"), str
            ):
                raise RuntimeError("Event-log record lacks timestamp or event")
            events.append(event)
    names = [str(event["event"]) for event in events]
    positions: list[int] = []
    for name in EXPECTED_EVENT_ORDER:
        matches = [index for index, value in enumerate(names) if value == name]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one event-log occurrence: {name}")
        positions.append(matches[0])
    if positions != sorted(positions):
        raise RuntimeError("Target-blind stage events are out of order")
    if any(
        str(events[index]["utc"]) > str(events[index + 1]["utc"])
        for index in range(len(events) - 1)
    ):
        raise RuntimeError("Event-log timestamps are not monotone")
    return events


def verify_launch_binding(
    *,
    launch_record_path: Path,
    run_directory: Path,
    expected_config: Path,
    expected_protocol: Path,
    expected_runner: Path,
    expected_launcher_sha256: str,
    local_dataset_archive: Path | None,
    result: Mapping[str, Any],
    outer_lock_owner_pid: int,
) -> Mapping[str, Any]:
    record = read_json_mapping(launch_record_path, "external launch record")
    if record.get("schema") != "ravel-external-launch-v1":
        raise RuntimeError("Unexpected external launch-record schema")
    if Path(str(record.get("run_directory", ""))).resolve() != run_directory.resolve():
        raise RuntimeError("Launch record names a different run directory")
    if str(record.get("run_id", "")) != run_directory.name:
        raise RuntimeError("Launch-record run ID mismatch")
    if int(record.get("launcher_pid", -1)) != outer_lock_owner_pid:
        raise RuntimeError("Launch-record launcher PID mismatch")
    if Path(str(record.get("python_executable", ""))).resolve() != Path(
        sys.executable
    ).resolve():
        raise RuntimeError("Launch-record Python executable mismatch")
    expected_command = [
        str(Path(sys.executable).absolute()),
        "-B",
        "-u",
        str(expected_runner),
        "--config",
        str(expected_config),
        "--protocol",
        str(expected_protocol),
        "--output-root",
        str(run_directory.parent.parent),
        "--run-id",
        run_directory.name,
    ]
    if local_dataset_archive is not None:
        expected_command.extend(
            ["--local-dataset-archive", str(local_dataset_archive.resolve())]
        )
    if record.get("command") != expected_command:
        raise RuntimeError("Launch-record runner command mismatch")
    sources = require_mapping(record.get("source_sha256"), "launch source hashes")
    expected = {
        "python_executable": sha256_file(Path(sys.executable).resolve()),
        "runner": sha256_file(expected_runner),
        "config": sha256_file(expected_config),
        "protocol": sha256_file(expected_protocol),
        "launcher": sha256_file(Path(__file__).resolve()),
    }
    if not is_sha256(expected_launcher_sha256) or expected["launcher"] != str(
        expected_launcher_sha256
    ).casefold():
        raise RuntimeError("Verifier source changed after the launch hash was bound")
    for name, digest in expected.items():
        if str(sources.get(name, "")).casefold() != digest:
            raise RuntimeError(f"Launch-record source hash mismatch: {name}")
    recorded_archive_path = record.get("local_dataset_archive")
    recorded_archive_hash = record.get("local_dataset_archive_sha256")
    if local_dataset_archive is None:
        if recorded_archive_path is not None or recorded_archive_hash is not None:
            raise RuntimeError("Launch record unexpectedly binds a local archive")
        local_hash = None
    else:
        archive = local_dataset_archive.resolve()
        if not archive.is_file():
            raise RuntimeError("Bound local dataset archive disappeared")
        if Path(str(recorded_archive_path)).resolve() != archive:
            raise RuntimeError("Launch record names a different local archive")
        local_hash = sha256_file(archive)
        if str(recorded_archive_hash).casefold() != local_hash or str(
            sources.get("local_dataset_archive", "")
        ).casefold() != local_hash:
            raise RuntimeError("Local archive changed after launch binding")
    provenance = require_mapping(result.get("provenance"), "result provenance")
    if local_hash is not None and str(
        require_mapping(
            provenance.get("dataset_source_hashes"), "dataset source hashes"
        ).get("archive", "")
    ).casefold() != local_hash:
        raise RuntimeError("Runner archive differs from the launch-bound local archive")
    return {
        "launch_record_sha256": sha256_file(launch_record_path),
        "launcher_sha256": expected["launcher"],
        "local_dataset_archive_sha256": local_hash,
    }


def verify_immutable_artifacts(
    run_directory: Path,
    result: Mapping[str, Any],
    config: Mapping[str, Any],
    runner_module: Any,
) -> bool:
    immutability = require_mapping(result.get("immutability"), "immutability record")
    semantic_before = require_mapping(
        immutability.get("semantic_before"), "semantic before hashes"
    )
    semantic_after = require_mapping(
        immutability.get("semantic_after"), "semantic after hashes"
    )
    if semantic_before != semantic_after or immutability.get("semantic_unchanged") is not True:
        raise RuntimeError("Semantic before/after immutability hashes differ")
    semantic_matrices = list(run_directory.glob("semantic_item_matrix_*_seq001.npy"))
    semantic_indexes = list(run_directory.glob("semantic_index_*_seq001.faiss"))
    if len(semantic_matrices) != 1 or len(semantic_indexes) != 1:
        raise RuntimeError("Expected exactly one semantic matrix and index")
    semantic_matrix = runner_module.np.load(
        semantic_matrices[0], allow_pickle=False
    )
    semantic_actual = {
        "matrix_file": sha256_file(semantic_matrices[0]),
        "matrix_memory": sha256_bytes(semantic_matrix.tobytes(order="C")),
        "index_file": sha256_file(semantic_indexes[0]),
        "index_memory": sha256_file(semantic_indexes[0]),
    }
    require_canonical_equal(
        semantic_actual, semantic_before, "semantic immutability hashes"
    )
    collaborative = require_sequence(
        immutability.get("collaborative"), "collaborative immutability records"
    )
    seen: set[tuple[int, str]] = set()
    for raw in collaborative:
        record = require_mapping(raw, "collaborative immutability record")
        seed = parse_int(record.get("seed"), "immutability seed")
        variant = str(record.get("variant", ""))
        if variant not in {"implicit", "rating_aware"} or (seed, variant) in seen:
            raise RuntimeError("Duplicate or unknown collaborative immutability record")
        seen.add((seed, variant))
        matrix_path = contained_file(
            run_directory, str(record.get("matrix_file", "")), "BPR item matrix"
        )
        index_path = contained_file(
            run_directory, str(record.get("index_file", "")), "BPR FAISS index"
        )
        matrix = runner_module.np.load(matrix_path, allow_pickle=False)
        actual_matrix_file = sha256_file(matrix_path)
        actual_matrix_memory = sha256_bytes(matrix.tobytes(order="C"))
        actual_index = sha256_file(index_path)
        expected_pairs = {
            "matrix_file_before": actual_matrix_file,
            "matrix_file_after": actual_matrix_file,
            "matrix_memory_before": actual_matrix_memory,
            "matrix_memory_after": actual_matrix_memory,
            "index_file_before": actual_index,
            "index_file_after": actual_index,
            "index_memory_before": actual_index,
            "index_memory_after": actual_index,
        }
        for field, expected in expected_pairs.items():
            if str(record.get(field, "")).casefold() != expected:
                raise RuntimeError(f"Collaborative immutability mismatch: {field}")
        if record.get("unchanged") is not True:
            raise RuntimeError("Collaborative immutability record is not unchanged")
    expected_seeds = {int(seed) for seed in config["replicate_seeds"]}
    if seen != {
        (seed, variant)
        for seed in expected_seeds
        for variant in ("implicit", "rating_aware")
    }:
        raise RuntimeError("Collaborative immutability matrix coverage mismatch")
    if immutability.get("all_unchanged") is not True:
        raise RuntimeError("Runner immutability aggregate is false")
    return True


def rebuild_integrity_and_fingerprints(
    *,
    run_directory: Path,
    candidate: Mapping[str, Any],
    result: Mapping[str, Any],
    config: Mapping[str, Any],
    expected_config: Path,
    expected_protocol: Path,
    expected_runner: Path,
    snapshot_paths: Mapping[str, Path],
    runner_module: Any,
    runner_ledger: Path,
    selector_lock_path: Path,
    test_manifest_paths: Sequence[Path],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    provenance = require_mapping(result.get("provenance"), "result provenance")
    source_hashes = require_mapping(
        provenance.get("source_hashes"), "result source hashes"
    )
    project_root = expected_runner.parents[1]
    live_sources = {
        "config": expected_config,
        "protocol_document": expected_protocol,
        "ravel_runner": expected_runner,
        "caper_dependency": expected_runner.parent / "caper_poc.py",
        "research_question": project_root / "research-question-cycle3.md",
        "cycle3_survey": project_root / "literature" / "cycle3-survey-and-ideation.md",
    }
    for label, path in live_sources.items():
        if not path.is_file() or sha256_file(path) != str(source_hashes.get(label, "")):
            raise RuntimeError(f"Live bound source hash mismatch: {label}")
        if label != "config" and label in snapshot_paths and sha256_file(
            snapshot_paths[label]
        ) != sha256_file(path):
            raise RuntimeError(f"Live/snapshot source mismatch: {label}")
    effective_config = contained_file(
        run_directory,
        str(provenance.get("effective_config_file", "")),
        "effective config",
    )
    if effective_config.read_bytes() != expected_config.read_bytes():
        raise RuntimeError("Effective config differs byte-for-byte from launch config")
    runner_module.validate_config(config)
    expected_protocol_sha = sha256_bytes(
        canonical_json_bytes(
            {
                "protocol_name": config["protocol_name"],
                "source_sha256": dict(source_hashes),
            }
        )
    )
    if (
        str(result.get("protocol_sha256", "")).casefold() != expected_protocol_sha
        or str(candidate.get("protocol_sha256", "")).casefold()
        != expected_protocol_sha
    ):
        raise RuntimeError("Composite protocol fingerprint does not replay")

    dataset_hashes = require_mapping(
        provenance.get("dataset_source_hashes"), "dataset source hashes"
    )
    archive = run_directory / "ml-1m.sha-locked.zip"
    archive_hash = sha256_file(archive)
    expected_archive = str(config["dataset"]["expected_sha256"]).casefold()
    if (
        archive_hash != expected_archive
        or str(result.get("dataset_sha256", "")).casefold() != archive_hash
        or str(dataset_hashes.get("archive", "")).casefold() != archive_hash
    ):
        raise RuntimeError("SHA-locked dataset archive mismatch")
    extracted = run_directory / "sha_locked_ml1m_extracted"
    ratings = list(extracted.rglob("ratings.dat"))
    movies = list(extracted.rglob("movies.dat"))
    if len(ratings) != 1 or len(movies) != 1:
        raise RuntimeError("Extracted MovieLens source-file cardinality mismatch")
    # This is a byte-level provenance hash only; the verifier never parses ratings.
    if sha256_file(ratings[0]) != str(dataset_hashes.get("ratings.dat", "")):
        raise RuntimeError("Extracted ratings.dat provenance hash mismatch")
    if sha256_file(movies[0]) != str(dataset_hashes.get("movies.dat", "")):
        raise RuntimeError("Extracted movies.dat provenance hash mismatch")

    cohort_path = contained_file(
        run_directory, str(provenance.get("cohort_file", "")), "cohort lock"
    )
    cohort = read_json_mapping(cohort_path, "cohort lock")
    if cohort.get("schema") != "ravel-prospective-disjoint-cohort-v1":
        raise RuntimeError("Unexpected cohort-lock schema")
    cohort_users = [
        int(user)
        for user in require_sequence(cohort.get("ravel_user_ids"), "RAVEL cohort users")
    ]
    if len(cohort_users) != 1000 or len(set(cohort_users)) != 1000:
        raise RuntimeError("RAVEL cohort lock is not 1,000 unique users")
    cohort_diagnostics = require_mapping(
        cohort.get("diagnostics"), "cohort diagnostics"
    )
    if (
        cohort.get("test_outcomes_inspected_for_replacement") is not False
        or cohort_diagnostics.get("cohorts_disjoint") is not True
        or int(cohort_diagnostics.get("slice_intersection_count", -1)) != 0
        or cohort_diagnostics.get("caper_slice") != [0, 1000]
        or cohort_diagnostics.get("ravel_slice") != [1000, 2000]
    ):
        raise RuntimeError("Prospective cohort-disjointness evidence failed")
    data_counts = require_mapping(result.get("data_counts"), "result data counts")
    require_canonical_equal(
        cohort_diagnostics,
        data_counts.get("split_diagnostics"),
        "cohort split diagnostics",
    )
    if int(data_counts.get("ravel_users", -1)) != len(cohort_users):
        raise RuntimeError("Result/cohort user count mismatch")

    event_paths = list(run_directory.glob("events_*_seq001.jsonl"))
    if len(event_paths) != 1:
        raise RuntimeError("Expected exactly one runner event log")
    events = parse_event_log(event_paths[0], int(candidate["pid"]))
    first = events[0]
    if str(first.get("protocol_sha256", "")).casefold() != expected_protocol_sha:
        raise RuntimeError("Run-start event protocol mismatch")
    require_canonical_equal(
        first.get("source_hashes"), source_hashes, "run-start source hashes"
    )
    selector_events = [
        event
        for event in events
        if event.get("event") == "segregated_V_use_2_selector_and_controls_locked"
    ]
    if str(selector_events[0].get("selector_lock_sha256", "")).casefold() != sha256_file(
        selector_lock_path
    ):
        raise RuntimeError("Selector-lock event hash mismatch")

    manifest_provenance = require_mapping(
        provenance.get("candidate_manifests"), "candidate manifest provenance"
    )
    manifest_files = [
        str(value)
        for value in require_sequence(manifest_provenance.get("files"), "manifest files")
    ]
    manifest_hashes = require_mapping(
        manifest_provenance.get("sha256"), "manifest hashes"
    )
    latency_names = [
        name
        for name in manifest_files
        if name.startswith("target_blind_latency_evidence_")
    ]
    latency_events = [
        event
        for event in events
        if event.get("event")
        == "target_blind_latency_evidence_persisted_before_T_label_join"
    ]
    if (
        len(latency_names) != 1
        or len(latency_events) != 1
        or latency_events[0].get("file") != latency_names[0]
        or str(latency_events[0].get("sha256", "")).casefold()
        != str(manifest_hashes.get(latency_names[0], "")).casefold()
    ):
        raise RuntimeError("Pre-T latency evidence event/hash mismatch")
    if len(manifest_files) != len(set(name.casefold() for name in manifest_files)):
        raise RuntimeError("Duplicate manifest artifact name")
    for name in manifest_files:
        path = contained_file(run_directory, name, "target-blind manifest")
        if str(manifest_hashes.get(name, "")).casefold() != sha256_file(path):
            raise RuntimeError(f"Target-blind manifest hash mismatch: {name}")
    if not set(path.name for path in test_manifest_paths).issubset(manifest_files):
        raise RuntimeError("Audited test manifests are absent from manifest provenance")
    if (
        manifest_provenance.get("R_persisted_before_R_label_join") is not True
        or manifest_provenance.get("V_persisted_before_V_label_join") is not True
        or manifest_provenance.get("T_outputs_persisted_before_T_label_join") is not True
        or int(manifest_provenance.get("target_injection_count", -1)) != 0
    ):
        raise RuntimeError("Manifest-stage target barrier evidence failed")

    immutable = verify_immutable_artifacts(
        run_directory, result, config, runner_module
    )
    integrity = {
        "cohort_disjointness": True,
        "immutable": immutable,
        "manifests_stable": True,
        "temporal_and_provenance": bool(
            cohort_diagnostics.get("timestamp_groups_indivisible")
            and cohort_diagnostics.get("strict_temporal_boundaries")
            and config["dataset"]["exclude_demographics"]
            and archive_hash == expected_archive
        ),
        "source_hashes_stable": True,
        "async_ledger_empty": runner_ledger.stat().st_size == 0,
    }
    if not all(integrity.values()):
        raise RuntimeError("Independent integrity replay failed")
    require_canonical_equal(integrity, result.get("integrity"), "result integrity")

    selection_locks = require_mapping(
        result.get("selection_locks"), "result selection locks"
    )
    selection = require_mapping(
        selection_locks.get("selector_and_controls"), "result selection"
    )
    seeds = [int(seed) for seed in config["replicate_seeds"]]
    execution_sha = sha256_bytes(
        canonical_json_bytes(
            {
                "protocol_sha256": expected_protocol_sha,
                "dataset_sha256": archive_hash,
                "cohort_sha256": sha256_file(cohort_path),
                "selected_bpr_variant": selection_locks["selected_bpr_variant"],
                "selection": selection,
                "seeds": seeds,
            }
        )
    )
    if (
        str(result.get("execution_fingerprint_sha256", "")).casefold()
        != execution_sha
        or str(candidate.get("execution_fingerprint_sha256", "")).casefold()
        != execution_sha
    ):
        raise RuntimeError("Execution fingerprint does not replay")
    return integrity, {
        "protocol_sha256": expected_protocol_sha,
        "execution_fingerprint_sha256": execution_sha,
        "dataset_sha256": archive_hash,
        "cohort_sha256": sha256_file(cohort_path),
        "event_log_sha256": sha256_file(event_paths[0]),
        "manifest_count": len(manifest_files),
    }


def replay_scientific_result(
    *,
    run_directory: Path,
    candidate: Mapping[str, Any],
    result: Mapping[str, Any],
    expected_config: Path,
    expected_protocol: Path,
    expected_runner: Path,
    runner_ledger: Path,
) -> Mapping[str, Any]:
    try:
        config = json.loads(expected_config.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("Cannot parse launch-bound RAVEL config") from exc
    config = require_mapping(config, "launch-bound RAVEL config")
    runner_module, snapshot_paths = load_bound_runner_module(run_directory, result)
    if tuple(getattr(runner_module, "METHODS", ())) != EXPECTED_METHODS:
        raise RuntimeError("Hash-bound runner method registry mismatch")
    expected_seeds = [int(seed) for seed in config.get("replicate_seeds", [])]
    artifacts = require_mapping(result.get("artifacts"), "result artifacts")
    metrics_path = contained_file(
        run_directory,
        str(artifacts.get("per_user_metrics", "")),
        "per-user metrics CSV",
    )
    per_seed_rows = parse_per_user_metrics(metrics_path, expected_seeds)
    prefix_candidate_audit = audit_prefix_candidate_manifests(
        run_directory, result, config
    )
    selection, selector_lock_path, selected_oof_path = replay_selector_lock(
        run_directory, result, config, runner_module
    )
    manifest_audit, test_manifest_paths = audit_test_manifests(
        run_directory, result, config, per_seed_rows, runner_module
    )
    per_seed_diagnostics = validate_per_user_science(
        per_seed_rows, manifest_audit, result, runner_module
    )
    latency_by_seed, latency_evidence_audit = validate_latency_evidence(
        run_directory, result, config, runner_module
    )
    integrity, fingerprints = rebuild_integrity_and_fingerprints(
        run_directory=run_directory,
        candidate=candidate,
        result=result,
        config=config,
        expected_config=expected_config,
        expected_protocol=expected_protocol,
        expected_runner=expected_runner,
        snapshot_paths=snapshot_paths,
        runner_module=runner_module,
        runner_ledger=runner_ledger,
        selector_lock_path=selector_lock_path,
        test_manifest_paths=test_manifest_paths,
    )
    cohort_path = contained_file(
        run_directory,
        str(require_mapping(result["provenance"], "result provenance").get(
            "cohort_file", ""
        )),
        "cohort lock",
    )
    cohort = read_json_mapping(cohort_path, "cohort lock")
    cohort_users = {
        int(user)
        for user in require_sequence(cohort.get("ravel_user_ids"), "cohort users")
    }
    csv_users = {
        int(row["user_id"])
        for row in per_seed_rows[expected_seeds[0]]["ravel"]
    }
    if cohort_users != csv_users:
        raise RuntimeError("Per-user metrics cohort differs from the cohort lock")
    replayed_gate = runner_module.evaluate_ten_part_gate(
        per_seed_rows,
        per_seed_diagnostics,
        latency_by_seed,
        selection,
        integrity,
        config,
    )
    replayed_gates = require_mapping(
        replayed_gate.get("gates"), "replayed promise gates"
    )
    if set(replayed_gates) != set(EXPECTED_GATE_KEYS):
        raise RuntimeError("Replayed gate names are not exactly G1--G10")
    g5 = require_mapping(
        replayed_gates.get("G5_nontrivial_calibrated_coverage"),
        "replayed G5 gate",
    )
    accepted_pair_support = replay_accepted_pair_bearing_support(per_seed_rows)
    claimed_accepted_pair_support = parse_float(
        g5.get("accepted_pair_requests_seed_averaged"),
        "G5 accepted pair-bearing support",
    )
    if not math.isclose(
        accepted_pair_support,
        claimed_accepted_pair_support,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise RuntimeError("G5 same-seed accepted pair-bearing support does not replay")
    if g5.get("accepted_pair_support_formula") != (
        "sum_u mean_s[accepted(u,s) * 1(preference_pairs(u,s)>0)]"
    ):
        raise RuntimeError("G5 accepted pair-bearing support formula is not registered")
    require_canonical_equal(
        replayed_gate, result.get("promise_gate"), "scientific promise gate"
    )
    return {
        "scientific_replay_passed": True,
        "per_user_metrics_file": metrics_path.name,
        "per_user_metrics_sha256": sha256_file(metrics_path),
        "per_user_metric_rows": sum(
            len(rows)
            for methods in per_seed_rows.values()
            for rows in methods.values()
        ),
        "replayed_seed_count": len(per_seed_rows),
        "replayed_method_count": len(EXPECTED_METHODS),
        "audited_test_manifest_count": len(test_manifest_paths),
        "audited_test_request_rows": sum(
            len(per_seed_rows[seed]["ravel"]) for seed in per_seed_rows
        ),
        "prefix_candidate_audit": prefix_candidate_audit,
        "selector_lock_file": selector_lock_path.name,
        "selector_lock_sha256": sha256_file(selector_lock_path),
        "selected_validation_oof_evidence_file": selected_oof_path.name,
        "selected_validation_oof_evidence_sha256": sha256_file(selected_oof_path),
        "latency_per_user_medians_replayed": True,
        "latency_evidence": latency_evidence_audit,
        "independent_integrity": integrity,
        "fingerprints": fingerprints,
        "gate_keys": list(EXPECTED_GATE_KEYS),
        "g5_same_seed_accepted_pair_support": accepted_pair_support,
        "promise_gate_passed": bool(replayed_gate["passed"]),
        "canonical_gate_equality": True,
        "movieLens_target_files_parsed": False,
        "models_rerun": False,
    }


def validate_result(
    result_path: Path,
    candidate: Mapping[str, Any],
    run_directory: Path,
    expected_config_sha256: str,
    expected_protocol_document_sha256: str,
    expected_runner_sha256: str,
) -> tuple[Mapping[str, Any], bool, int]:
    result = read_json_mapping(result_path, "RAVEL result")
    if result.get("schema") != "ravel-poc-result-v1":
        raise RuntimeError("Unexpected RAVEL result schema")
    if result.get("status") != "COMPLETE_RUNNER_RESULT":
        raise RuntimeError("RAVEL result is not a complete runner result")
    if Path(str(result.get("run_directory", ""))).resolve() != run_directory.resolve():
        raise RuntimeError("RAVEL result names a different run directory")
    for field in ("protocol_sha256", "execution_fingerprint_sha256"):
        if str(result.get(field, "")).lower() != str(candidate[field]).lower():
            raise RuntimeError(f"RAVEL result/candidate {field} mismatch")
    promise_gate = result.get("promise_gate")
    if not isinstance(promise_gate, Mapping) or not isinstance(
        promise_gate.get("passed"), bool
    ):
        raise RuntimeError("RAVEL result has no boolean promise_gate.passed")
    gates = promise_gate.get("gates")
    if not isinstance(gates, Mapping) or set(gates) != set(EXPECTED_GATE_KEYS):
        raise RuntimeError(
            "RAVEL result does not contain exactly the named G1--G10 gate keys"
        )
    gate_values: list[bool] = []
    for gate_name, gate_value in gates.items():
        if not isinstance(gate_value, Mapping):
            raise RuntimeError(f"Malformed RAVEL gate: {gate_name}")
        if not isinstance(gate_value.get("passed"), bool):
            raise RuntimeError(f"RAVEL gate lacks a boolean verdict: {gate_name}")
        gate_values.append(bool(gate_value["passed"]))
    if bool(promise_gate["passed"]) != all(gate_values):
        raise RuntimeError("RAVEL aggregate gate disagrees with its ten component gates")
    integrity = result.get("integrity")
    if not isinstance(integrity, Mapping) or integrity.get("async_ledger_empty") is not True:
        raise RuntimeError("RAVEL result does not attest an empty runner async ledger")
    provenance = result.get("provenance")
    source_hashes = provenance.get("source_hashes") if isinstance(provenance, Mapping) else None
    if not isinstance(source_hashes, Mapping):
        raise RuntimeError("RAVEL result has no bound source-hash mapping")
    expected_sources = {
        "config": expected_config_sha256,
        "protocol_document": expected_protocol_document_sha256,
        "ravel_runner": expected_runner_sha256,
    }
    for name, expected_hash in expected_sources.items():
        if str(source_hashes.get(name, "")).lower() != expected_hash:
            raise RuntimeError(f"RAVEL result source hash mismatch: {name}")
    return result, bool(promise_gate["passed"]), len(gate_values)


def validate_candidate_and_closure(
    candidate_path: Path,
    run_directory: Path,
    verifier_ledger: Path,
    launcher_child_pid: int,
    expected_config: Path,
    expected_protocol: Path,
    expected_runner: Path,
    launch_record: Path,
    expected_launcher_sha256: str,
    local_dataset_archive: Path | None,
    outer_lock_owner_pid: int,
    runner_stdout: Path,
    runner_stderr: Path,
) -> Mapping[str, Any]:
    candidate = read_json_mapping(candidate_path, "runner completion candidate")
    if candidate.get("schema") != "ravel-runner-completion-candidate-v1":
        raise RuntimeError("Unexpected runner completion candidate schema")
    runner_pid = int(candidate.get("pid", -1))
    if runner_pid <= 0:
        raise RuntimeError("Runner completion candidate contains an invalid PID")
    if pid_is_running(launcher_child_pid):
        raise RuntimeError(f"Launcher child PID is still active: {launcher_child_pid}")
    if pid_is_running(runner_pid):
        raise RuntimeError(f"Recorded runner PID is still active: {runner_pid}")
    recorded_directory = Path(str(candidate.get("run_directory", ""))).resolve()
    if recorded_directory != run_directory.resolve():
        raise RuntimeError("Runner completion candidate names a different run directory")
    if candidate.get("runner_lock_release_pending") is not True:
        raise RuntimeError("Runner candidate did not declare lock release pending")
    if candidate.get("external_post_exit_verification_required") is not True:
        raise RuntimeError("Runner candidate did not require external verification")

    expected_hashes = {
        "config_sha256": sha256_file(expected_config),
        "runner_sha256": sha256_file(expected_runner),
    }
    for field, expected_hash in expected_hashes.items():
        value = candidate.get(field)
        if not is_sha256(value) or str(value).lower() != expected_hash:
            raise RuntimeError(f"Runner candidate {field} does not match the launch input")
    if not is_sha256(candidate.get("protocol_sha256")):
        raise RuntimeError("Malformed composite protocol SHA-256")
    execution_hash = candidate.get("execution_fingerprint_sha256")
    if not is_sha256(execution_hash):
        raise RuntimeError("Malformed execution fingerprint SHA-256")

    expected_runner_lock = run_directory.parent.parent / "ravel_poc.lock"
    runner_lock = Path(str(candidate.get("runner_lock", ""))).resolve()
    if runner_lock != expected_runner_lock.resolve():
        raise RuntimeError("Runner candidate names an unexpected runner lock")
    if runner_lock.exists():
        raise RuntimeError(f"Runner lock still exists after exit: {runner_lock}")
    if not str(candidate.get("runner_lock_token", "")):
        raise RuntimeError("Runner candidate has no lock token")

    runner_ledger = contained_file(
        run_directory,
        str(candidate.get("asynchronous_error_ledger", "")),
        "runner asynchronous-error ledger",
    )
    if not runner_ledger.is_file() or runner_ledger.stat().st_size != 0:
        raise RuntimeError("Runner asynchronous-error ledger is missing or nonempty")
    runner_ledger_hash = sha256_file(runner_ledger)
    if runner_ledger_hash != str(
        candidate.get("asynchronous_error_ledger_sha256", "")
    ).lower():
        raise RuntimeError("Runner asynchronous-error ledger hash mismatch")

    artifact_hashes_raw = candidate.get("artifact_sha256")
    if not isinstance(artifact_hashes_raw, Mapping) or not artifact_hashes_raw:
        raise RuntimeError("Runner candidate has no artifact hash manifest")
    artifact_hashes: dict[str, str] = {}
    casefold_names: set[str] = set()
    for relative_name_raw, expected_hash_raw in artifact_hashes_raw.items():
        relative_name = str(relative_name_raw)
        expected_hash = str(expected_hash_raw).lower()
        if relative_name.casefold() in casefold_names:
            raise RuntimeError(f"Case-colliding artifact name: {relative_name}")
        casefold_names.add(relative_name.casefold())
        if not is_sha256(expected_hash):
            raise RuntimeError(f"Malformed artifact SHA-256: {relative_name}")
        artifact = contained_file(run_directory, relative_name, "candidate artifact")
        if not artifact.is_file():
            raise RuntimeError(f"Missing candidate-bound artifact: {artifact}")
        if sha256_file(artifact) != expected_hash:
            raise RuntimeError(f"Artifact hash mismatch: {relative_name}")
        artifact_hashes[Path(relative_name).as_posix()] = expected_hash

    excluded = {
        candidate_path.resolve(),
        verifier_ledger.resolve(),
    }
    recursive_files = {
        path.relative_to(run_directory).as_posix()
        for path in run_directory.rglob("*")
        if path.is_file() and path.resolve() not in excluded
    }
    if recursive_files != set(artifact_hashes):
        missing = sorted(set(artifact_hashes) - recursive_files)
        unbound = sorted(recursive_files - set(artifact_hashes))
        raise RuntimeError(
            "Recursive artifact closure mismatch; "
            f"missing={missing[:5]}, unbound={unbound[:5]}"
        )

    result_path = contained_file(
        run_directory, str(candidate.get("result_file", "")), "result file"
    )
    result_hash = sha256_file(result_path)
    if result_hash != str(candidate.get("result_sha256", "")).lower():
        raise RuntimeError("Result hash does not match runner completion candidate")
    result, promise_gate_passed, gate_count = validate_result(
        result_path,
        candidate,
        run_directory,
        expected_config_sha256=expected_hashes["config_sha256"],
        expected_protocol_document_sha256=sha256_file(expected_protocol),
        expected_runner_sha256=expected_hashes["runner_sha256"],
    )
    launch_binding = verify_launch_binding(
        launch_record_path=launch_record,
        run_directory=run_directory,
        expected_config=expected_config,
        expected_protocol=expected_protocol,
        expected_runner=expected_runner,
        expected_launcher_sha256=expected_launcher_sha256,
        local_dataset_archive=local_dataset_archive,
        result=result,
        outer_lock_owner_pid=outer_lock_owner_pid,
    )
    scientific_replay = replay_scientific_result(
        run_directory=run_directory,
        candidate=candidate,
        result=result,
        expected_config=expected_config,
        expected_protocol=expected_protocol,
        expected_runner=expected_runner,
        runner_ledger=runner_ledger,
    )
    if bool(scientific_replay["promise_gate_passed"]) != promise_gate_passed:
        raise RuntimeError("Scientific replay verdict disagrees with the result")

    if not runner_stdout.is_file() or not runner_stderr.is_file():
        raise RuntimeError("Persistent runner logs are missing")
    if runner_stderr.stat().st_size != 0:
        raise RuntimeError("Clean RAVEL runner stderr is nonempty")
    if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
        raise RuntimeError("An external completion marker already exists")

    return {
        "candidate": candidate,
        "runner_pid": runner_pid,
        "runner_lock": runner_lock,
        "runner_ledger": runner_ledger,
        "artifact_count": len(artifact_hashes),
        "result_path": result_path,
        "promise_gate_passed": promise_gate_passed,
        "gate_count": gate_count,
        "execution_hash": str(execution_hash).lower(),
        "runner_stdout_sha256": sha256_file(runner_stdout),
        "runner_stderr_sha256": sha256_file(runner_stderr),
        "launch_binding": launch_binding,
        "scientific_replay": scientific_replay,
    }


def run_verifier(args: argparse.Namespace) -> int:
    run_directory = args.verify_run_directory.resolve()
    candidate_path = args.candidate.resolve()
    report_path = args.verification_report.resolve()
    ledger_path = args.verifier_ledger.resolve()
    if not run_directory.is_dir():
        raise FileNotFoundError(run_directory)
    if candidate_path.parent.resolve() != run_directory:
        raise RuntimeError("Verifier candidate is outside the run directory")
    if find_sole_runner_candidate(run_directory).resolve() != candidate_path:
        raise RuntimeError("Verifier was not given the sole runner candidate")
    for path, label in (
        (report_path, "verification report"),
        (ledger_path, "verifier ledger"),
    ):
        if path.parent.resolve() != run_directory:
            raise RuntimeError(f"{label} must be inside the run directory")
        if path.exists():
            raise FileExistsError(f"Append-only {label} collision: {path}")

    create_empty_file_exclusive(ledger_path)
    install_async_exception_hooks(ledger_path)
    verify_outer_authorization(
        args.outer_lock.resolve(),
        int(args.outer_lock_owner_pid),
        str(args.outer_lock_token),
    )
    verified = validate_candidate_and_closure(
        candidate_path=candidate_path,
        run_directory=run_directory,
        verifier_ledger=ledger_path,
        launcher_child_pid=int(args.launcher_child_pid),
        expected_config=args.config.resolve(),
        expected_protocol=args.protocol.resolve(),
        expected_runner=args.runner.resolve(),
        launch_record=args.launch_record.resolve(),
        expected_launcher_sha256=str(args.expected_launcher_sha256),
        local_dataset_archive=(
            args.local_dataset_archive.resolve()
            if args.local_dataset_archive is not None
            else None
        ),
        outer_lock_owner_pid=int(args.outer_lock_owner_pid),
        runner_stdout=args.runner_stdout.resolve(),
        runner_stderr=args.runner_stderr.resolve(),
    )
    if ledger_path.stat().st_size != 0:
        raise RuntimeError("Verifier asynchronous-error ledger is nonempty")

    candidate = verified["candidate"]
    publish_json_exclusive(
        report_path,
        {
            "schema": "ravel-post-exit-verification-v1",
            "verified_utc": utc_now(),
            "verifier_pid": os.getpid(),
            "authorizing_outer_lock": str(args.outer_lock.resolve()),
            "authorizing_outer_lock_owner_pid": int(args.outer_lock_owner_pid),
            "authorizing_outer_lock_active": True,
            "launcher_child_pid": int(args.launcher_child_pid),
            "launcher_child_process_has_exited": True,
            "runner_pid": int(verified["runner_pid"]),
            "runner_process_has_exited": True,
            "windows_shim_pid_mismatch": (
                int(args.launcher_child_pid) != int(verified["runner_pid"])
            ),
            "windows_shim_pid_mismatch_allowed_only_because_both_are_dead": True,
            "runner_lock": str(verified["runner_lock"]),
            "runner_lock_released": True,
            "candidate_marker": candidate_path.name,
            "candidate_marker_sha256": sha256_file(candidate_path),
            "verified_recursive_artifact_count": int(verified["artifact_count"]),
            "recursive_artifact_hash_closure": True,
            "runner_asynchronous_error_ledger": verified["runner_ledger"].name,
            "runner_asynchronous_error_ledger_empty": True,
            "runner_asynchronous_error_ledger_sha256": sha256_file(
                verified["runner_ledger"]
            ),
            "verifier_asynchronous_error_ledger": ledger_path.name,
            "verifier_asynchronous_error_ledger_empty_at_report": True,
            "verifier_asynchronous_error_ledger_sha256_at_report": sha256_file(
                ledger_path
            ),
            "runner_stdout": str(args.runner_stdout.resolve()),
            "runner_stdout_sha256": verified["runner_stdout_sha256"],
            "runner_stderr": str(args.runner_stderr.resolve()),
            "runner_stderr_zero_bytes": True,
            "runner_stderr_sha256": verified["runner_stderr_sha256"],
            "result_file": verified["result_path"].name,
            "result_sha256": sha256_file(verified["result_path"]),
            "protocol_sha256": str(candidate["protocol_sha256"]).lower(),
            "protocol_document_sha256": sha256_file(args.protocol.resolve()),
            "config_sha256": str(candidate["config_sha256"]).lower(),
            "runner_sha256": str(candidate["runner_sha256"]).lower(),
            "execution_fingerprint_sha256": verified["execution_hash"],
            "promise_gate_passed": bool(verified["promise_gate_passed"]),
            "verified_gate_count": int(verified["gate_count"]),
            "launch_binding": verified["launch_binding"],
            "scientific_replay": verified["scientific_replay"],
            "external_marker_publication_authorized": True,
        },
    )
    print(f"POST_EXIT_VERIFICATION_REPORT={report_path}", flush=True)
    return 0


def terminate_and_wait(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)


def run_hidden_process(
    command: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[int, int]:
    process: subprocess.Popen[Any] | None = None
    with stdout_path.open("xb") as stdout_handle, stderr_path.open("xb") as stderr_handle:
        try:
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
            if process is not None:
                terminate_and_wait(process)
            raise


def require_launch_mode_args(args: argparse.Namespace) -> None:
    if args.run_id is not None and (
        Path(args.run_id).name != args.run_id or args.run_id in {"", ".", ".."}
    ):
        raise ValueError("run-id must be one safe path component")


def run_launch(args: argparse.Namespace) -> int:
    require_launch_mode_args(args)
    project_root = Path(__file__).resolve().parents[1]
    runner = (project_root / "src" / "ravel_poc.py").resolve()
    config = args.config.resolve()
    protocol = args.protocol.resolve()
    output_root = args.output_root.resolve()
    python_executable = Path(sys.executable).absolute()
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise RuntimeError(
            "RAVEL launcher must be invoked by the workspace virtual-environment Python"
        )
    for path, label in (
        (python_executable, "current virtual-environment Python"),
        (runner, "RAVEL outcome runner"),
        (config, "RAVEL configuration"),
        (protocol, "RAVEL human protocol"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Missing {label}: {path}")
    local_archive = (
        args.local_dataset_archive.resolve()
        if args.local_dataset_archive is not None
        else None
    )
    if local_archive is not None and not local_archive.is_file():
        raise FileNotFoundError(f"Missing local dataset archive: {local_archive}")

    run_id = args.run_id or (
        "ravel-poc-v1-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid.uuid4().hex[:12]
    )
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ValueError("run-id must be one safe path component")
    run_directory = output_root / "ravel_poc_runs" / run_id
    if run_directory.exists():
        raise FileExistsError(f"Run directory already exists: {run_directory}")

    outer_lock = OuterLaunchLock(output_root / "ravel_outer_launch.lock")
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
            raise FileExistsError(f"Append-only launcher artifact collision: {path}")

    create_empty_file_exclusive(launcher_ledger)
    install_async_exception_hooks(launcher_ledger)
    environment = os.environ.copy()
    for key in THREAD_VARIABLES:
        environment[key] = "1"
    environment["CUDA_VISIBLE_DEVICES"] = "-1"
    environment["HF_HUB_OFFLINE"] = "1"
    environment["TRANSFORMERS_OFFLINE"] = "1"
    environment["TOKENIZERS_PARALLELISM"] = "false"
    environment["PYTHONHASHSEED"] = "20260817"

    command = [
        str(python_executable),
        "-B",
        "-u",
        str(runner),
        "--config",
        str(config),
        "--protocol",
        str(protocol),
        "--output-root",
        str(output_root),
        "--run-id",
        run_id,
    ]
    if local_archive is not None:
        command.extend(["--local-dataset-archive", str(local_archive)])
    launch_hashes = {
        "python_executable": sha256_file(python_executable),
        "launcher": sha256_file(Path(__file__).resolve()),
        "runner": sha256_file(runner),
        "config": sha256_file(config),
        "protocol": sha256_file(protocol),
        "local_dataset_archive": (
            sha256_file(local_archive) if local_archive is not None else None
        ),
    }
    publish_json_exclusive(
        launch_record,
        {
            "schema": "ravel-external-launch-v1",
            "created_utc": utc_now(),
            "launcher_pid": os.getpid(),
            "run_id": run_id,
            "run_directory": str(run_directory),
            "python_executable": str(python_executable),
            "command": command,
            "source_sha256": launch_hashes,
            "local_dataset_archive": (
                str(local_archive) if local_archive is not None else None
            ),
            "local_dataset_archive_sha256": launch_hashes[
                "local_dataset_archive"
            ],
            "outer_lock": str(outer_lock.path),
            "outer_lock_token_sha256": sha256_text(outer_lock.token),
            "thread_environment": {key: environment[key] for key in THREAD_VARIABLES},
            "cuda_visible_devices": environment["CUDA_VISIBLE_DEVICES"],
        },
    )
    # No outcome process exists before this acquisition.  From this point the
    # outer lock remains held across runner, verifier, and marker publication.
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
        child_pid, child_return_code = run_hidden_process(
            command,
            project_root,
            environment,
            runner_stdout,
            runner_stderr,
        )
        if child_return_code != 0:
            raise RuntimeError(f"RAVEL outcome runner exited with code {child_return_code}")
        if pid_is_running(child_pid):
            raise RuntimeError(f"Launcher child PID is still active: {child_pid}")
        if not run_directory.is_dir():
            raise RuntimeError(f"Runner did not create {run_directory}")
        candidate_path = find_sole_runner_candidate(run_directory)
        candidate_preview = read_json_mapping(candidate_path, "runner candidate")
        execution_hash = candidate_preview.get("execution_fingerprint_sha256")
        if not is_sha256(execution_hash):
            raise RuntimeError("Runner candidate has a malformed execution fingerprint")
        if list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json")):
            raise RuntimeError("An external completion marker already exists")

        verification_nonce = uuid.uuid4().hex
        verifier_ledger = run_directory / (
            f"verifier_async_errors_{str(execution_hash)[:16]}_"
            f"{verification_nonce[:12]}.jsonl"
        )
        verifier_report = run_directory / (
            f"POST_EXIT_VERIFIER_{str(execution_hash)[:16]}_"
            f"{verification_nonce[:12]}.json"
        )
        verifier_command = [
            str(python_executable),
            "-B",
            "-u",
            str(Path(__file__).resolve()),
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
            str(launch_hashes["launcher"]),
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
                f"RAVEL post-exit verifier exited with code {verifier_return_code}"
            )
        if pid_is_running(verifier_child_pid):
            raise RuntimeError(f"Verifier child PID is still active: {verifier_child_pid}")
        report = read_json_mapping(verifier_report, "post-exit verifier report")
        if report.get("schema") != "ravel-post-exit-verification-v1":
            raise RuntimeError("Unexpected post-exit verifier report schema")
        verifier_pid = int(report.get("verifier_pid", -1))
        if verifier_pid <= 0 or pid_is_running(verifier_pid):
            raise RuntimeError(f"Verifier PID is still active or invalid: {verifier_pid}")
        if report.get("external_marker_publication_authorized") is not True:
            raise RuntimeError("Post-exit verifier did not authorize marker publication")
        scientific_report = require_mapping(
            report.get("scientific_replay"), "post-exit scientific replay"
        )
        if (
            scientific_report.get("scientific_replay_passed") is not True
            or scientific_report.get("canonical_gate_equality") is not True
            or scientific_report.get("movieLens_target_files_parsed") is not False
            or scientific_report.get("models_rerun") is not False
        ):
            raise RuntimeError("Post-exit scientific replay is incomplete")
        report_launch_binding = require_mapping(
            report.get("launch_binding"), "post-exit launch binding"
        )
        if str(report_launch_binding.get("launcher_sha256", "")).casefold() != str(
            launch_hashes["launcher"]
        ).casefold():
            raise RuntimeError("Post-exit report launcher-source binding mismatch")
        if report_launch_binding.get("local_dataset_archive_sha256") != launch_hashes[
            "local_dataset_archive"
        ]:
            raise RuntimeError("Post-exit report local-archive binding mismatch")
        if not verifier_ledger.is_file() or verifier_ledger.stat().st_size != 0:
            raise RuntimeError("Post-exit verifier asynchronous ledger is nonempty")
        if verifier_stderr.stat().st_size != 0:
            raise RuntimeError("Clean post-exit verifier stderr is nonempty")
        if launcher_ledger.stat().st_size != 0:
            raise RuntimeError("Launcher asynchronous-error ledger is nonempty")
        outer_lock.assert_owned()

        candidate = read_json_mapping(candidate_path, "runner candidate after verifier")
        result_path = contained_file(
            run_directory, str(candidate["result_file"]), "result file"
        )
        promise_gate_passed = bool(report["promise_gate_passed"])
        if sha256_file(Path(__file__).resolve()) != launch_hashes["launcher"]:
            raise RuntimeError("RAVEL launcher source changed during execution")
        external_marker = run_directory / (
            f"{EXTERNAL_MARKER_PREFIX}{str(execution_hash)[:16]}.json"
        )
        publish_json_exclusive(
            external_marker,
            {
                "schema": "ravel-external-completion-v1",
                "verified_utc": utc_now(),
                "python_executable": str(python_executable),
                "python_executable_sha256": sha256_file(python_executable),
                "launcher_sha256": launch_hashes["launcher"],
                "launcher_pid": os.getpid(),
                "launcher_child_pid": child_pid,
                "launcher_child_exit_code": child_return_code,
                "launcher_child_process_has_exited": True,
                "runner_pid": int(report["runner_pid"]),
                "runner_process_has_exited": True,
                "runner_shim_pid_mismatch": child_pid != int(report["runner_pid"]),
                "runner_shim_pid_mismatch_allowed_only_because_both_are_dead": True,
                "verifier_child_pid": verifier_child_pid,
                "verifier_child_exit_code": verifier_return_code,
                "verifier_child_process_has_exited": True,
                "verifier_pid": verifier_pid,
                "verifier_process_has_exited": True,
                "verifier_shim_pid_mismatch": verifier_child_pid != verifier_pid,
                "verifier_shim_pid_mismatch_allowed_only_because_both_are_dead": True,
                "runner_lock": report["runner_lock"],
                "runner_lock_released": True,
                "outer_lock": str(outer_lock.path),
                "outer_lock_token_sha256": sha256_text(outer_lock.token),
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
                "runner_asynchronous_error_ledger_sha256": report[
                    "runner_asynchronous_error_ledger_sha256"
                ],
                "verifier_asynchronous_error_ledger": verifier_ledger.name,
                "verifier_asynchronous_error_ledger_empty": True,
                "verifier_asynchronous_error_ledger_sha256": sha256_file(
                    verifier_ledger
                ),
                "launcher_asynchronous_error_ledger": str(launcher_ledger),
                "launcher_asynchronous_error_ledger_empty": True,
                "launcher_asynchronous_error_ledger_sha256": sha256_file(
                    launcher_ledger
                ),
                "runner_stdout": str(runner_stdout),
                "runner_stdout_sha256": sha256_file(runner_stdout),
                "runner_stderr": str(runner_stderr),
                "runner_stderr_zero_bytes": True,
                "runner_stderr_sha256": sha256_file(runner_stderr),
                "verifier_stdout": str(verifier_stdout),
                "verifier_stdout_sha256": sha256_file(verifier_stdout),
                "verifier_stderr": str(verifier_stderr),
                "verifier_stderr_zero_bytes": True,
                "verifier_stderr_sha256": sha256_file(verifier_stderr),
                "result_file": result_path.name,
                "result_sha256": sha256_file(result_path),
                "protocol_sha256": report["protocol_sha256"],
                "protocol_document_sha256": report[
                    "protocol_document_sha256"
                ],
                "config_sha256": report["config_sha256"],
                "runner_sha256": report["runner_sha256"],
                "execution_fingerprint_sha256": str(execution_hash).lower(),
                "promise_gate_passed": promise_gate_passed,
                "scientific_replay": report["scientific_replay"],
                "launch_binding": report["launch_binding"],
            },
        )
        if len(list(run_directory.glob(f"{EXTERNAL_MARKER_PREFIX}*.json"))) != 1:
            raise RuntimeError("External completion marker publication was not singular")
    except BaseException as exc:
        if not failure_path.exists():
            publish_json_exclusive(
                failure_path,
                {
                    "schema": "ravel-external-verification-failure-v1",
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
                    "python_executable": str(python_executable),
                    "run_directory": str(run_directory),
                    "outer_lock": str(outer_lock.path),
                    "outer_lock_held_at_failure": outer_lock.acquired,
                    "runner_stdout": str(runner_stdout),
                    "runner_stderr": str(runner_stderr),
                    "verifier_stdout": str(verifier_stdout),
                    "verifier_stderr": str(verifier_stderr),
                    "launcher_async_ledger": str(launcher_ledger),
                },
            )
        raise
    finally:
        outer_lock.release()

    if outer_lock.path.exists():
        raise RuntimeError("RAVEL outer lock remains after launcher completion")
    if external_marker is None or result_path is None or promise_gate_passed is None:
        raise RuntimeError("RAVEL launcher reached an incomplete terminal state")
    print(f"EXTERNAL_COMPLETION_MARKER={external_marker}", flush=True)
    print(f"RESULT_FILE={result_path}", flush=True)
    print(
        "PROMISE_GATE_PASSED=" + str(promise_gate_passed).lower(),
        flush=True,
    )
    print("OUTER_LOCK_RELEASED=true", flush=True)
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Launch a RAVEL outcome under the Windows-safe contract, or verify "
            "an exited runner from sealed aggregates without opening raw targets."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "ravel_poc_ml1m_v1.json",
        help="Locked RAVEL JSON configuration.",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=project_root / "experiments" / "ravel-protocol-v1.md",
        help="Locked human-readable RAVEL protocol.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=project_root / "experiments" / "runs",
        help="Root for the runner lock and append-only RAVEL run directories.",
    )
    parser.add_argument("--run-id", default=None, help="Optional safe unique run ID.")
    parser.add_argument(
        "--local-dataset-archive",
        type=Path,
        default=None,
        help="Optional local SHA-locked ML-1M archive passed to the runner.",
    )
    parser.add_argument(
        "--verify-run-directory",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Internal/no-outcome mode: verify one exited runner candidate. "
            "Requires the authorization arguments supplied by the outer launcher."
        ),
    )
    parser.add_argument("--candidate", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--verification-report", type=Path, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--verifier-ledger", type=Path, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--runner-stdout", type=Path, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--runner-stderr", type=Path, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--launcher-child-pid", type=int, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument("--outer-lock", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--outer-lock-owner-pid", type=int, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--outer-lock-token", default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--runner",
        type=Path,
        default=project_root / "src" / "ravel_poc.py",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--launch-record", type=Path, default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--expected-launcher-sha256", default=None, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run synthetic no-outcome replay-helper checks and exit.",
    )
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


def synthetic_self_test() -> Mapping[str, Any]:
    try:
        import numpy as local_np
    except ImportError as exc:
        raise RuntimeError("NumPy is required for the replay self-test") from exc
    with tempfile.TemporaryDirectory(prefix="ravel-verifier-selftest-") as temporary:
        csv_path = Path(temporary) / "per_user_metrics.csv"
        fields = (
            "seed",
            "method",
            "user_id",
            "ndcg_at_10",
            "recall_at_10",
            "preference_pair_accuracy",
            "preference_pairs",
            "preference_correct",
            "future_dislike_intrusion_at_10",
            "candidate_recall",
            "union_candidate_recall_at_most_400",
            "collaborative_candidate_recall_at_200",
            "candidate_support_inclusion",
            "accepted",
            "exact_fallback",
            "ndcg_delta_vs_linear",
            "preference_delta_vs_linear",
            "harmful_intervention",
        )
        with csv_path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for seed in (1, 2, 3):
                for method in EXPECTED_METHODS:
                    writer.writerow(
                        {
                            "seed": seed,
                            "method": method,
                            "user_id": 7,
                            "ndcg_at_10": 0.5,
                            "recall_at_10": 0.5,
                            "preference_pair_accuracy": 1.0,
                            "preference_pairs": 1,
                            "preference_correct": 1,
                            "future_dislike_intrusion_at_10": 0.0,
                            "candidate_recall": 1.0,
                            "union_candidate_recall_at_most_400": 1.0,
                            "collaborative_candidate_recall_at_200": 1.0,
                            "candidate_support_inclusion": True,
                            "accepted": 0.0,
                            "exact_fallback": True,
                            "ndcg_delta_vs_linear": 0.0,
                            "preference_delta_vs_linear": 0.0,
                            "harmful_intervention": False,
                        }
                    )
        parsed = parse_per_user_metrics(csv_path, (1, 2, 3))
        if sum(len(rows) for methods in parsed.values() for rows in methods.values()) != 24:
            raise AssertionError("Synthetic per-user CSV replay count failed")

    union = list(range(12))
    ranking = list(range(12))
    score_values = [1.0 - index / 20.0 for index in range(12)]
    score_bits = [struct.pack("<f", value).hex() for value in score_values]
    record = canonical_ranking_record(union, ranking, score_bits, "synthetic")
    require_hex_record(record, record.hex(), sha256_bytes(record), "synthetic")
    require_projection_invariants(
        union=union,
        default_ranking=ranking,
        proposal_ranking=ranking,
        linear_values=score_values,
        proposal_values=score_values,
        scale=1.0,
        tie_width=0.1,
        projection_k=10,
        label="synthetic identity projection",
    )
    finite_values = list(score_values)
    finite_values[9] = 0.35
    finite_values[10] = 0.70
    finite_ranking = list(range(8)) + [10, 8, 9, 11]
    require_projection_invariants(
        union=union,
        default_ranking=ranking,
        proposal_ranking=finite_ranking,
        linear_values=score_values,
        proposal_values=finite_values,
        scale=1.0,
        tie_width=0.1,
        projection_k=10,
        label="synthetic finite proposal with frozen-linear tail",
    )
    adjusted_tail_was_rejected = False
    try:
        require_projection_invariants(
            union=union,
            default_ranking=ranking,
            proposal_ranking=finite_ranking[:10] + [11, 9],
            linear_values=score_values,
            proposal_values=finite_values,
            scale=1.0,
            tie_width=0.1,
            projection_k=10,
            label="synthetic forbidden adjusted-score tail",
        )
    except RuntimeError:
        adjusted_tail_was_rejected = True
    if not adjusted_tail_was_rejected:
        raise AssertionError("Finite proposal accepted a non-frozen tail")
    finite_bits = [struct.pack("<f", value).hex() for value in finite_values]
    require_selected_finite_always_on_alias(
        proposal_ranking=finite_ranking,
        proposal_bits=finite_bits,
        always_ranking=finite_ranking,
        always_bits=finite_bits,
        binding_flag=True,
        accepted=True,
        exact_fallback=False,
        label="synthetic always-on alias",
    )
    synthetic_pair_rows = {
        1: {
            "ravel": [
                {"user_id": 7, "accepted": 1.0, "preference_pairs": 1.0},
                {"user_id": 8, "accepted": 1.0, "preference_pairs": 0.0},
            ]
        },
        2: {
            "ravel": [
                {"user_id": 7, "accepted": 0.0, "preference_pairs": 1.0},
                {"user_id": 8, "accepted": 1.0, "preference_pairs": 1.0},
            ]
        },
    }
    if replay_accepted_pair_bearing_support(synthetic_pair_rows) != 1.0:
        raise AssertionError("Same-seed accepted pair-bearing support replay failed")
    query_payload = struct.pack("<3f", 0.25, -0.5, 1.0)
    if audit_float32_array_evidence(
        {
            "dtype": "little-endian-float32",
            "shape": [3],
            "bytes_hex": query_payload.hex(),
            "sha256": sha256_bytes(query_payload),
        },
        "synthetic query",
        3,
    ) != query_payload:
        raise AssertionError("Float32 query-evidence replay failed")

    class SyntheticRunner:
        np = local_np

    latency_result = {
        "latency_by_seed": {
            "1": {
                "single_thread_cpu": True,
                "includes_both_searches_union_features_default_residual_proposal_selector_sort": True,
                "measured_users": 1,
                "repetitions": 3,
                "abba_interleaving": True,
                "linear": {
                    "p50_ms": 1.0,
                    "p95_ms": 1.0,
                    "mean_of_user_medians_ms": 1.0,
                    "per_user_median_ms": [1.0],
                    "aggregation": "median_across_repetitions_per_user_then_percentile_across_users",
                },
                "ravel": {
                    "p50_ms": 1.2,
                    "p95_ms": 1.2,
                    "mean_of_user_medians_ms": 1.2,
                    "per_user_median_ms": [1.2],
                    "aggregation": "median_across_repetitions_per_user_then_percentile_across_users",
                },
                "ravel_to_linear_p95_ratio": 1.2,
            }
        }
    }
    latency_config = {
        "replicate_seeds": [1],
        "dataset": {"minimum_test_users": 1},
        "evaluation": {
            "latency_measured_users": 1,
            "latency_warmup_users": 1,
            "latency_repetitions": 3,
        },
    }
    with tempfile.TemporaryDirectory(prefix="ravel-latency-selftest-") as temporary:
        directory = Path(temporary)
        cohort_path = directory / "cohort.json"
        publish_json_exclusive(cohort_path, {"ravel_user_ids": [7]})
        evidence_path = directory / "target_blind_latency_evidence_synthetic.json"
        publish_json_exclusive(
            evidence_path,
            {
                "schema": "ravel-target-blind-latency-evidence-v1",
                "protocol_sha256": "0" * 64,
                "created_before_T_label_join": True,
                "test_labels_or_item_identities_joined": False,
                "measured_user_ids_numeric_order": [7],
                "warmup_user_ids_also_measured": [7],
                "repetitions": 3,
                "interleaving": "AB/BA by (repetition + numeric-user-position) parity",
                "per_seed_raw_user_medians_and_summaries": latency_result[
                    "latency_by_seed"
                ],
            },
        )
        latency_result["protocol_sha256"] = "0" * 64
        latency_result["provenance"] = {
            "cohort_file": cohort_path.name,
            "candidate_manifests": {
                "files": [evidence_path.name],
                "sha256": {evidence_path.name: sha256_file(evidence_path)},
            },
        }
        validate_latency_evidence(
            directory, latency_result, latency_config, SyntheticRunner()
        )
    return {
        "per_user_csv_replay": True,
        "canonical_full_union_record": True,
        "projection_invariants": True,
        "finite_proposal_frozen_linear_tail": True,
        "always_on_exact_selected_finite_proposal": True,
        "g5_same_seed_accepted_pair_support": True,
        "float32_query_evidence": True,
        "latency_summary_replay": True,
        "outcomes_accessed": False,
        "models_rerun": False,
    }


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
