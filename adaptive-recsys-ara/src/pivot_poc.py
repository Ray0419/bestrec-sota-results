"""Prospectively locked producer for the cycle-six PIVOT MovieLens-10M PoC.

The default modes (``--validate-config`` and ``--self-test``) are deliberately
outcome blind: they reject archive and output arguments and use synthetic data
only.  ``--run`` is a one-shot, fail-closed producer.  It publishes a
non-authoritative completion candidate; only the separate source-bound verifier
may replay G1--G8 and create the authoritative completion marker required by G9.

PIVOT (Preference-Informed Vector-partition Offsets for Traversal) learns one
bounded user-to-cell potential and reuses it for both four-shard routing and
cross-shard ranking.  Item embeddings, capacity-balanced spherical cells, and
FAISS IndexFlatIP shards are immutable.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import dataclasses
import datetime as dt
import hashlib
import io
import importlib.metadata as importlib_metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import random
import statistics
import sys
import tempfile
import threading
import time
import traceback
from typing import Any, Iterable, Mapping, Sequence
import zipfile

import numpy as np


ARCHIVE_BYTES = 65_566_137
ARCHIVE_SHA256 = "813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862"
ARCHIVE_MD5 = "ce571fd55effeba0271552578f2648bd"
SEMANTIC_SHA256 = "8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768"
CYCLE5_COHORT_SHA256 = "eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126"
QUESTION_RELATIVE = Path("literature") / "research-question-cycle6.md"

SEEDS = (20260861, 20260862, 20260863)
EPOCHS = (5, 10, 20, 40)
METHODS = (
    "popularity",
    "raw_full_exact_semantic",
    "balanced_geometric_ivf",
    "pivot_route_only",
    "pivot_rerank_only",
    "pivot_full",
    "shuffled_pivot",
    "aligned_full_exact",
)
FIXED_WORK_METHODS = METHODS[2:7]
METRICS = (
    "future_liked_recall_at_100",
    "cpe_at_100",
    "cross_cell_cpe_at_100",
    "aligned_oracle_overlap_at_100",
    "spce_at_10",
    "ndcg_at_10",
    "recall_at_10",
    "low_rating_intrusion_at_10",
)

LOCKED_CONFIG: Mapping[str, Any] = {
    "protocol": "pivot-ml10m-poc-v1-cycle6",
    "archive": {
        "bytes": ARCHIVE_BYTES,
        "sha256": ARCHIVE_SHA256,
        "md5": ARCHIVE_MD5,
        "allowed_inputs": ["ratings.dat", "movies.dat"],
        "forbidden_inputs": ["tags.dat"],
    },
    "cohort": {
        "size": 600,
        "minimum_events": 80,
        "maximum_events": 300,
        "minimum_timestamp_groups": 4,
        "minimum_A_likes": 5,
        "order_salt": "20260861:{user_id}",
        "split_fractions": [0.60, 0.20, 0.10, 0.10],
        "positive_rating_min": 4.0,
        "dislike_rating_max": 2.0,
    },
    "embedding": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
        "template": "{title} [SEP] {genres}",
        "batch_size": 128,
        "local_files_only": True,
        "reusable_sha256": SEMANTIC_SHA256,
    },
    "partition": {
        "cells": 32,
        "initial_seed": 20260861,
        "batch_size": 1024,
        "n_init": 5,
        "max_iter": 100,
        "reassignment_ratio": 0.0,
        "real_capacity_first_25": 334,
        "real_capacity_last_7": 333,
        "physical_slots": 334,
        "probes": 4,
    },
    "model": {
        "input_dimension": 1153,
        "hidden_dimension": 32,
        "output_dimension": 32,
        "offset_scale": 0.05,
        "learning_rate": 0.003,
        "weight_decay": 1.0e-4,
        "gradient_clip": 1.0,
        "beta": 5.0,
        "margin": 0.05,
        "epochs": list(EPOCHS),
        "seeds": list(SEEDS),
    },
    "pairs": {
        "rating_gap": 2.0,
        "R_cap": 64,
        "R_salt": "20260862:{user_id}:{low_item_id}:{high_item_id}",
        "shuffle_salt": "20260863:{user_id}:{low_item_id}:{high_item_id}",
        "V_checkpoint_cap": 64,
        "V_checkpoint_salt": "20260867:{user_id}:{low_item_id}:{high_item_id}",
        "V_estimand_cap": 100,
        "V_estimand_salt": "20260869:{user_id}:{low_item_id}:{high_item_id}",
        "T_estimand_cap": 100,
        "T_estimand_salt": "20260865:{user_id}:{low_item_id}:{high_item_id}",
    },
    "retrieval": {
        "kind": "IndexFlatIP",
        "top_k": 100,
        "tie_break": "score_desc_then_numeric_movie_id_asc",
        "faiss_threads": 1,
        "matrix_tolerance": {"rtol": 2.0e-6, "atol": 2.0e-6},
    },
    "bootstrap": {"draws": 5000, "alpha": 0.05, "seed": 20260864},
    "power": {
        "outer_draws": 500,
        "inner_draws": 500,
        "effect": 0.010,
        "minimum_detection": 0.80,
        "seed": 20260866,
    },
    "latency": {
        "requests": 512,
        "request_salt": "20260868:{user_id}",
        "warmups": 32,
        "repetitions": 7,
        "maximum_p95_ms": 3.0,
        "maximum_ratio": 1.5,
    },
}


class IntegrityError(RuntimeError):
    """A prospectively locked construction or stage invariant was violated."""


@dataclasses.dataclass(frozen=True)
class Movie:
    movie_id: int
    title: str
    genres: str


@dataclasses.dataclass(frozen=True)
class Skeleton:
    user_id: int
    timestamp: int
    ordinal: int


@dataclasses.dataclass(frozen=True)
class Interaction:
    user_id: int
    item_index: int
    movie_id: int
    rating: float
    timestamp: int
    ordinal: int


@dataclasses.dataclass(frozen=True)
class Layout:
    user_id: int
    counts: tuple[int, int, int, int]
    minimum_timestamps: tuple[int, int, int, int]
    maximum_timestamps: tuple[int, int, int, int]
    fingerprint: str


@dataclasses.dataclass(frozen=True)
class Descriptor:
    query: np.ndarray
    liked: np.ndarray
    disliked: np.ndarray
    a_count_scaled: float


@dataclasses.dataclass(frozen=True)
class Pair:
    user_id: int
    preferred: int
    rejected: int
    preferred_movie_id: int
    rejected_movie_id: int
    cross_cell: bool


@dataclasses.dataclass(frozen=True)
class Partitions:
    assignment: np.ndarray
    centroids: np.ndarray
    shard_item_indices: tuple[np.ndarray, ...]
    shard_movie_ids: tuple[np.ndarray, ...]
    indexes: tuple[Any, ...]
    initial_centroid_hashes: tuple[str, ...]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def hash_int(template: str, **values: int) -> tuple[int, str]:
    text = template.format(**values)
    digest = hashlib.sha256(text.encode("ascii")).hexdigest()
    return int(digest, 16), digest


def normalise(vector: np.ndarray) -> np.ndarray:
    result = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(result))
    if not math.isfinite(norm) or norm <= 0.0:
        raise IntegrityError("Cannot normalize a zero or nonfinite vector")
    return np.ascontiguousarray(result / np.float32(norm), dtype=np.float32)


def npz_bytes(**arrays: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def publish_bytes(path: Path, payload: bytes) -> str:
    """Atomic, no-overwrite publication used for every immutable artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntegrityError(f"Refusing to overwrite artifact: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A hard-link is an atomic exclusive publication: unlike replace(),
            # it cannot overwrite a concurrently published immutable artifact.
            os.link(temporary, path)
        except FileExistsError as error:
            raise IntegrityError(f"Refusing to overwrite artifact: {path}") from error
        with contextlib.suppress(OSError):
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
    return sha256_bytes(payload)


def publish_json(path: Path, value: Any) -> str:
    return publish_bytes(path, canonical_json_bytes(value))


def publish_npz(path: Path, **arrays: np.ndarray) -> str:
    return publish_bytes(path, npz_bytes(**arrays))


def append_ledger(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value)
    with path.open("ab", buffering=0) as handle:
        handle.write(payload)
        os.fsync(handle.fileno())


def install_async_error_hooks(path: Path) -> None:
    """Persist uncaught main-thread, worker-thread, and unraisable failures."""
    def main_hook(error_type: type[BaseException], error: BaseException, trace: Any) -> None:
        append_ledger(path, {"utc": utc_now(), "hook": "sys.excepthook", "type": error_type.__name__, "message": str(error), "traceback": "".join(traceback.format_exception(error_type, error, trace))})

    def thread_hook(arguments: threading.ExceptHookArgs) -> None:
        append_ledger(path, {"utc": utc_now(), "hook": "threading.excepthook", "thread": getattr(arguments.thread, "name", None), "type": arguments.exc_type.__name__, "message": str(arguments.exc_value), "traceback": "".join(traceback.format_exception(arguments.exc_type, arguments.exc_value, arguments.exc_traceback))})

    def unraisable_hook(arguments: Any) -> None:
        append_ledger(path, {"utc": utc_now(), "hook": "sys.unraisablehook", "type": type(arguments.exc_value).__name__, "message": str(arguments.exc_value), "object": repr(arguments.object)})

    sys.excepthook = main_hook
    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def validate_locked_config() -> Mapping[str, Any]:
    if tuple(LOCKED_CONFIG["model"]["seeds"]) != SEEDS or tuple(LOCKED_CONFIG["model"]["epochs"]) != EPOCHS:
        raise IntegrityError("Seed/epoch lock mismatch")
    if int(LOCKED_CONFIG["partition"]["cells"]) != 32:
        raise IntegrityError("PIVOT requires 32 cells")
    capacities = [334] * 25 + [333] * 7
    if sum(capacities) != 10_681 or len(capacities) != 32:
        raise IntegrityError("Locked real-cell capacities do not cover ML-10M")
    if int(LOCKED_CONFIG["partition"]["probes"]) * int(LOCKED_CONFIG["partition"]["physical_slots"]) != 1336:
        raise IntegrityError("Fixed shard work lock mismatch")
    if int(LOCKED_CONFIG["model"]["input_dimension"]) != 3 * 384 + 1:
        raise IntegrityError("Descriptor dimension lock mismatch")
    return {"schema": "pivot-locked-config-validation-v1", "valid": True, "locked_config_sha256": sha256_bytes(canonical_json_bytes(LOCKED_CONFIG))}


def load_external_config(path: Path, expected_sha256: str) -> Mapping[str, Any]:
    if len(expected_sha256) != 64 or any(character not in "0123456789abcdef" for character in expected_sha256):
        raise IntegrityError("--expect-config-sha256 must be a lowercase SHA-256")
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise IntegrityError(f"External config SHA-256 mismatch: {observed}")
    value = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(value, sort_keys=True)
    if "PREAUTHORIZATION_BINDING_REQUIRED" in serialized:
        raise IntegrityError("External config still contains an unresolved preauthorization binding")
    checks = {
        "archive_sha": value["dataset"]["expected_archive_sha256"] == ARCHIVE_SHA256,
        "archive_md5": value["dataset"]["expected_official_sidecar_md5"] == ARCHIVE_MD5,
        "exclusion_sha": value["dataset"]["prior_cycle_exclusion"]["record_sha256"] == CYCLE5_COHORT_SHA256,
        "semantic_sha": value["embedding"]["required_reuse_candidate_sha256"] == SEMANTIC_SHA256,
        "cohort": value["dataset"]["cohort"]["required_users"] == 600,
        "methods": tuple(value["methods"]["registered_order"]) == METHODS,
        "seeds": tuple(value["alignment"]["optimization_seeds"]) == SEEDS,
        "epochs": tuple(value["alignment"]["checkpoint_epochs"]) == EPOCHS,
        "cells": value["partition"]["num_cells"] == 32,
        "slots": value["retrieval"]["physical_shard_slots_searched"] == 1336,
    }
    if not all(checks.values()):
        raise IntegrityError(f"External config selected-value assertions failed: {checks}")
    return value


def verify_archive(path: Path) -> Mapping[str, Any]:
    resolved = path.resolve(strict=True)
    observed = {"bytes": resolved.stat().st_size, "sha256": sha256_file(resolved), "md5": md5_file(resolved)}
    expected = LOCKED_CONFIG["archive"]
    if any(observed[name] != expected[name] for name in ("bytes", "sha256", "md5")):
        raise IntegrityError(f"Official archive binding failed: {observed}")
    return {"path": str(resolved), **observed}


def _safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts:
        raise IntegrityError("Unsafe archive member")
    return member


def extract_allowed(archive: Path, destination: Path, *, authorized: bool) -> Mapping[str, Path]:
    if not authorized:
        raise IntegrityError("Archive extraction requires explicit run authorization")
    wanted = {"ratings.dat", "movies.dat"}
    result: dict[str, Path] = {}
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            member = _safe_member(info.filename)
            if member.name not in wanted:
                continue
            if member.name in result:
                raise IntegrityError(f"Duplicate {member.name} in archive")
            target = destination / member.name
            with bundle.open(info, "r") as source, target.open("xb") as sink:
                while block := source.read(1 << 20):
                    sink.write(block)
            result[member.name] = target
    if set(result) != wanted:
        raise IntegrityError("Official archive lacks required inputs")
    return result


def parse_movie(line: str) -> Movie:
    fields = line.rstrip("\r\n").split("::")
    if len(fields) != 3:
        raise IntegrityError("Malformed movies.dat row")
    movie = Movie(int(fields[0]), fields[1], fields[2])
    if movie.movie_id <= 0:
        raise IntegrityError("Invalid movie ID")
    return movie


def load_movies(path: Path) -> tuple[tuple[Movie, ...], Mapping[int, int]]:
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        movies = sorted((parse_movie(line) for line in handle), key=lambda value: value.movie_id)
    if len(movies) != 10_681 or len({movie.movie_id for movie in movies}) != len(movies):
        raise IntegrityError("Unexpected MovieLens-10M catalog")
    return tuple(movies), {movie.movie_id: index for index, movie in enumerate(movies)}


def parse_skeleton(line: str, ordinal: int) -> Skeleton:
    stripped = line.rstrip("\r\n")
    if stripped.count("::") != 3:
        raise IntegrityError("Malformed ratings.dat row")
    first = stripped.find("::")
    last = stripped.rfind("::")
    row = Skeleton(int(stripped[:first]), int(stripped[last + 2:]), ordinal)
    if row.user_id <= 0 or row.timestamp < 0:
        raise IntegrityError("Invalid structural rating row")
    return row


def parse_interaction(row: Skeleton, movie_to_index: Mapping[int, int], line: str) -> Interaction:
    fields = line.rstrip("\r\n").split("::")
    if len(fields) != 4:
        raise IntegrityError("Malformed ratings.dat row")
    user_id, movie_id, timestamp = int(fields[0]), int(fields[1]), int(fields[3])
    rating = float(fields[2])
    if (user_id, timestamp) != (row.user_id, row.timestamp) or movie_id not in movie_to_index:
        raise IntegrityError("Structural/full ratings parse disagreement")
    if not (0.5 <= rating <= 5.0 and math.isclose(rating * 2.0, round(rating * 2.0))):
        raise IntegrityError("Invalid MovieLens half-star rating")
    return Interaction(user_id, movie_to_index[movie_id], movie_id, rating, timestamp, row.ordinal)


def _nearest_boundary(cumulative: Sequence[int], target: float, low: int, high: int) -> int:
    if low > high:
        raise IntegrityError("No valid timestamp-group boundary")
    # On an exact distance tie, the boundary after the additional timestamp
    # group assigns that indivisible group to the earlier temporal block.
    return min(range(low, high + 1), key=lambda index: (abs(cumulative[index - 1] - target), -index))


def split_rows(rows: Sequence[Skeleton]) -> tuple[tuple[Skeleton, ...], ...]:
    ordered = sorted(rows, key=lambda row: (row.timestamp, row.ordinal))
    groups: list[list[Skeleton]] = []
    for row in ordered:
        if not groups or groups[-1][0].timestamp != row.timestamp:
            groups.append([row])
        else:
            groups[-1].append(row)
    if len(groups) < 4:
        return (tuple(), tuple(), tuple(), tuple())
    cumulative = np.cumsum([len(group) for group in groups]).tolist()
    total = len(ordered)
    a_cut = _nearest_boundary(cumulative, .60 * total, 1, len(groups) - 3)
    r_cut = _nearest_boundary(cumulative, .80 * total, a_cut + 1, len(groups) - 2)
    v_cut = _nearest_boundary(cumulative, .90 * total, r_cut + 1, len(groups) - 1)
    blocks = tuple(tuple(item for group in selected for item in group) for selected in (groups[:a_cut], groups[a_cut:r_cut], groups[r_cut:v_cut], groups[v_cut:]))
    if any(not block for block in blocks):
        raise IntegrityError("Temporal splitter produced an empty block")
    if not all(max(row.timestamp for row in blocks[index]) < min(row.timestamp for row in blocks[index + 1]) for index in range(3)):
        raise IntegrityError("Timestamp group crossed a stage boundary")
    return blocks


def layout_for(user_id: int, blocks: Sequence[Sequence[Skeleton]]) -> Layout:
    counts = tuple(len(block) for block in blocks)
    minima = tuple(min(row.timestamp for row in block) for block in blocks)
    maxima = tuple(max(row.timestamp for row in block) for block in blocks)
    payload = {"user_id": user_id, "counts": counts, "minimum_timestamps": minima, "maximum_timestamps": maxima}
    return Layout(user_id, counts, minima, maxima, sha256_bytes(canonical_json_bytes(payload)))


def cycle5_excluded_users(path: Path) -> tuple[frozenset[int], Mapping[str, Any]]:
    if sha256_file(path) != CYCLE5_COHORT_SHA256:
        raise IntegrityError("Cycle-5 exclusion cohort hash mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    candidates: Any = value.get("user_ids") if isinstance(value, dict) else value
    if candidates is None and isinstance(value, dict):
        candidates = value.get("selected_user_ids")
    if not isinstance(candidates, list) or not all(isinstance(item, int) for item in candidates):
        raise IntegrityError("Cycle-5 cohort record has no integer user list")
    users = frozenset(candidates)
    if len(users) != len(candidates):
        raise IntegrityError("Cycle-5 cohort contains duplicate users")
    return users, {"path": str(path.resolve()), "sha256": CYCLE5_COHORT_SHA256, "users": len(users)}


def select_cohort(ratings_path: Path, movie_to_index: Mapping[int, int], excluded: frozenset[int]) -> tuple[tuple[int, ...], Mapping[int, Layout], Mapping[int, tuple[Interaction, ...]], int, int]:
    """Two passes: structure only, then A-only eligibility/value join."""
    structural: dict[int, Layout] = {}

    def consider(rows: list[Skeleton]) -> None:
        if not rows:
            return
        user_id = rows[0].user_id
        if user_id in excluded or not (80 <= len(rows) <= 300) or len({row.timestamp for row in rows}) < 4:
            return
        blocks = split_rows(rows)
        if all(blocks):
            structural[user_id] = layout_for(user_id, blocks)

    current: int | None = None
    rows: list[Skeleton] = []
    seen: set[int] = set()
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton(line, ordinal)
            if current is None:
                current = row.user_id
            if row.user_id != current:
                if row.user_id in seen:
                    raise IntegrityError("ratings.dat is not grouped by user")
                consider(rows)
                seen.add(current)
                current, rows = row.user_id, []
            rows.append(row)
    consider(rows)

    ordered = sorted(structural, key=lambda user_id: (hash_int("20260861:{user_id}", user_id=user_id)[0], user_id))
    eligible_A: dict[int, tuple[Interaction, ...]] = {}
    wanted = set(ordered)

    def consider_A(user_id: int | None, skeletons: list[Skeleton], events: list[Interaction]) -> None:
        if user_id is None or user_id not in wanted:
            return
        blocks = split_rows(skeletons)
        if layout_for(user_id, blocks) != structural[user_id]:
            raise IntegrityError("A rescan changed structural layout")
        events.sort(key=lambda value: (value.timestamp, value.ordinal))
        if len(events) != structural[user_id].counts[0] or len({value.item_index for value in events}) != len(events):
            raise IntegrityError("A event count or uniqueness failed")
        if len({value.item_index for value in events if value.rating >= 4.0}) >= 5:
            eligible_A[user_id] = tuple(events)

    current = None
    rows, a_events = [], []
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton(line, ordinal)
            if current is None:
                current = row.user_id
            if row.user_id != current:
                consider_A(current, rows, a_events)
                current, rows, a_events = row.user_id, [], []
            if row.user_id in wanted:
                rows.append(row)
                layout = structural[row.user_id]
                if layout.minimum_timestamps[0] <= row.timestamp <= layout.maximum_timestamps[0]:
                    a_events.append(parse_interaction(row, movie_to_index, line))
    consider_A(current, rows, a_events)
    selected = tuple(user_id for user_id in ordered if user_id in eligible_A)[:600]
    if len(selected) != 600:
        raise IntegrityError(f"Only {len(selected)} cycle-6 users meet the A-only filter")
    return selected, {user_id: structural[user_id] for user_id in selected}, {user_id: eligible_A[user_id] for user_id in selected}, len(structural), len(eligible_A)


def load_stage(ratings_path: Path, user_ids: Sequence[int], layouts: Mapping[int, Layout], movie_to_index: Mapping[int, int], stage: str) -> Mapping[int, tuple[Interaction, ...]]:
    stage_index = {"A": 0, "R": 1, "V": 2, "T": 3}.get(stage)
    if stage_index is None:
        raise ValueError(stage)
    selected = frozenset(user_ids)
    result: dict[int, tuple[Interaction, ...]] = {}

    def consume(user_id: int | None, skeletons: list[Skeleton], events: list[Interaction]) -> None:
        if user_id is None or user_id not in selected:
            return
        blocks = split_rows(skeletons)
        if layout_for(user_id, blocks) != layouts[user_id]:
            raise IntegrityError(f"{stage} rescan changed structural layout")
        events.sort(key=lambda value: (value.timestamp, value.ordinal))
        if len(events) != layouts[user_id].counts[stage_index] or len({value.item_index for value in events}) != len(events):
            raise IntegrityError(f"{stage} event count or uniqueness failed")
        result[user_id] = tuple(events)

    current: int | None = None
    rows: list[Skeleton] = []
    events: list[Interaction] = []
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton(line, ordinal)
            if current is None:
                current = row.user_id
            if row.user_id != current:
                consume(current, rows, events)
                current, rows, events = row.user_id, [], []
            if row.user_id in selected:
                rows.append(row)
                layout = layouts[row.user_id]
                if layout.minimum_timestamps[stage_index] <= row.timestamp <= layout.maximum_timestamps[stage_index]:
                    events.append(parse_interaction(row, movie_to_index, line))
    consume(current, rows, events)
    if set(result) != selected:
        raise IntegrityError(f"Stage {stage} did not load all users")
    return result


def history_for(user_id: int, stage: str, A: Mapping[int, Sequence[Interaction]], R: Mapping[int, Sequence[Interaction]] | None = None, V: Mapping[int, Sequence[Interaction]] | None = None) -> tuple[Interaction, ...]:
    if stage == "R":
        result = tuple(A[user_id])
    elif stage == "V" and R is not None:
        result = (*A[user_id], *R[user_id])
    elif stage == "T" and R is not None and V is not None:
        result = (*A[user_id], *R[user_id], *V[user_id])
    else:
        raise IntegrityError(f"Unavailable history for {stage}")
    if len({event.item_index for event in result}) != len(result):
        raise IntegrityError("Repeated user/item across temporal stages")
    return tuple(result)


def assert_cross_stage_unique(user_ids: Sequence[int], *stages: Mapping[int, Sequence[Interaction]]) -> None:
    for user_id in user_ids:
        item_indices = [event.item_index for stage in stages for event in stage[user_id]]
        if len(item_indices) != len(set(item_indices)):
            raise IntegrityError("Repeated (user,item) interaction across temporal blocks")


def encode_movies(movies: Sequence[Movie]) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as error:
        raise IntegrityError("sentence-transformers is required") from error
    model = SentenceTransformer(str(LOCKED_CONFIG["embedding"]["model"]), local_files_only=True, device="cpu")
    rendered = [f"{movie.title} [SEP] {movie.genres}" for movie in movies]
    vectors = model.encode(rendered, batch_size=128, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    if vectors.shape != (len(movies), 384) or not np.isfinite(vectors).all():
        raise IntegrityError("Invalid sentence-transformer matrix")
    return vectors


def load_or_encode_vectors(path: Path | None, movies: Sequence[Movie]) -> tuple[np.ndarray, Mapping[str, Any]]:
    rendered = [f"{movie.title} [SEP] {movie.genres}" for movie in movies]
    rendered_sha256 = sha256_bytes(canonical_json_bytes(rendered))
    movie_id_order = np.asarray([movie.movie_id for movie in movies], dtype=np.int64)
    movie_id_order_sha256 = sha256_bytes(np.ascontiguousarray(movie_id_order, dtype="<i8").tobytes())
    if path is not None and path.is_file() and sha256_file(path) == SEMANTIC_SHA256:
        vectors = np.load(path, allow_pickle=False)
        source = "hash-qualified-cache"
    else:
        vectors = encode_movies(movies)
        source = "local-reencode"
    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    buffer = io.BytesIO(); np.save(buffer, vectors, allow_pickle=False)
    observed = sha256_bytes(buffer.getvalue())
    if vectors.shape != (10_681, 384) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=2e-5):
        raise IntegrityError("Semantic vector invariants failed")
    if source == "hash-qualified-cache" and observed != SEMANTIC_SHA256:
        raise IntegrityError("Loaded semantic array bytes differ from qualified file")
    return vectors, {
        "source": source,
        "encoder_id": str(LOCKED_CONFIG["embedding"]["model"]),
        "sentence_transformers_version": importlib_metadata.version("sentence-transformers"),
        "rendered_text_sha256": rendered_sha256,
        "movie_id_order_sha256": movie_id_order_sha256,
        "npy_sha256": observed,
        "expected_cache_sha256": SEMANTIC_SHA256,
    }


def _imports() -> tuple[Any, Any, Any, Any]:
    try:
        import faiss
        import torch
        from torch import nn
        import torch.nn.functional as functional
    except Exception as error:
        raise IntegrityError("FAISS and PyTorch are required") from error
    return faiss, torch, nn, functional


def build_partitions(vectors: np.ndarray, movie_ids: np.ndarray) -> Partitions:
    try:
        from sklearn.cluster import MiniBatchKMeans
    except Exception as error:
        raise IntegrityError("scikit-learn is required") from error
    faiss, _torch, _nn, _functional = _imports()
    old_threads = os.environ.get("OMP_NUM_THREADS")
    os.environ["OMP_NUM_THREADS"] = "1"
    try:
        estimator = MiniBatchKMeans(n_clusters=32, random_state=20260861, batch_size=1024, n_init=5, max_iter=100, reassignment_ratio=0.0)
        estimator.fit(vectors)
    finally:
        if old_threads is None:
            os.environ.pop("OMP_NUM_THREADS", None)
        else:
            os.environ["OMP_NUM_THREADS"] = old_threads
    raw = np.stack([normalise(row) for row in estimator.cluster_centers_]).astype(np.float32)
    hashes = tuple(sha256_bytes(np.ascontiguousarray(row, dtype="<f4").tobytes()) for row in raw)
    canonical_order = sorted(range(32), key=lambda cell: (hashes[cell], cell))
    initial = np.ascontiguousarray(raw[canonical_order], dtype=np.float32)
    canonical_hashes = tuple(hashes[cell] for cell in canonical_order)
    capacities = np.asarray([334] * 25 + [333] * 7, dtype=np.int64)
    score_matrix = np.asarray(vectors @ initial.T, dtype=np.float32)
    item_grid = np.repeat(np.arange(len(vectors), dtype=np.int64), 32)
    cell_grid = np.tile(np.arange(32, dtype=np.int64), len(vectors))
    flat_scores = score_matrix.reshape(-1)
    order = np.lexsort((cell_grid, movie_ids[item_grid], -flat_scores))
    assignment = np.full(len(vectors), -1, dtype=np.int16)
    counts = np.zeros(32, dtype=np.int64)
    remaining = len(vectors)
    for edge in order:
        item, cell = int(item_grid[edge]), int(cell_grid[edge])
        if assignment[item] < 0 and counts[cell] < capacities[cell]:
            assignment[item] = cell
            counts[cell] += 1
            remaining -= 1
            if remaining == 0:
                break
    if remaining or not np.array_equal(counts, capacities):
        raise IntegrityError("Balanced greedy assignment failed")
    centroids = np.stack([normalise(vectors[assignment == cell].mean(axis=0)) for cell in range(32)]).astype(np.float32)
    shard_indices: list[np.ndarray] = []
    shard_movie_ids: list[np.ndarray] = []
    indexes: list[Any] = []
    faiss.omp_set_num_threads(1)
    for cell in range(32):
        indices = np.flatnonzero(assignment == cell).astype(np.int64)
        indices = indices[np.argsort(movie_ids[indices], kind="stable")]
        ids = movie_ids[indices].astype(np.int64)
        shard_vectors = vectors[indices]
        if len(indices) == 333:
            indices = np.concatenate([indices, np.asarray([-1], dtype=np.int64)])
            ids = np.concatenate([ids, np.asarray([-(cell + 1)], dtype=np.int64)])
            shard_vectors = np.vstack([shard_vectors, np.zeros((1, vectors.shape[1]), dtype=np.float32)])
        if len(indices) != 334:
            raise IntegrityError("Physical shard is not 334 slots")
        index = faiss.IndexFlatIP(vectors.shape[1]); index.add(np.ascontiguousarray(shard_vectors, dtype=np.float32))
        if index.ntotal != 334:
            raise IntegrityError("FAISS physical shard size mismatch")
        shard_indices.append(indices); shard_movie_ids.append(ids); indexes.append(index)
    return Partitions(assignment, centroids, tuple(shard_indices), tuple(shard_movie_ids), tuple(indexes), canonical_hashes)


def descriptor(history: Sequence[Interaction], vectors: np.ndarray) -> Descriptor:
    liked_items = [event.item_index for event in history if event.rating >= 4.0]
    disliked_items = [event.item_index for event in history if event.rating <= 2.0]
    if len(set(liked_items)) < 5:
        raise IntegrityError("A descriptor lacks five distinct likes")
    liked = normalise(vectors[liked_items].mean(axis=0))
    disliked = normalise(vectors[disliked_items].mean(axis=0)) if disliked_items else np.zeros(384, dtype=np.float32)
    query = normalise(liked - np.float32(.25) * disliked)
    return Descriptor(query, liked, disliked, min(len(history), 300) / 300.0)


def descriptor_vector(value: Descriptor) -> np.ndarray:
    result = np.concatenate([value.query, value.liked, value.disliked, np.asarray([value.a_count_scaled], dtype=np.float32)]).astype(np.float32)
    if result.shape != (1153,) or not np.isfinite(result).all():
        raise IntegrityError("Descriptor shape/finite invariant failed")
    return result


def make_offset_model(seed: int) -> Any:
    _faiss, torch, nn, _functional = _imports()
    torch.manual_seed(seed); random.seed(seed); np.random.seed(seed % (2**32))
    torch.use_deterministic_algorithms(True)
    model = nn.Sequential(nn.Linear(1153, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh())
    with torch.no_grad():
        model[2].weight.zero_(); model[2].bias.zero_()
    return model


def offset_tensor(model: Any, features: Any) -> Any:
    z = model(features)
    return .05 * (z - z.mean(dim=-1, keepdim=True))


def offset_numpy(model: Any | None, features: np.ndarray) -> np.ndarray:
    if model is None:
        return np.zeros(32, dtype=np.float32)
    _faiss, torch, _nn, _functional = _imports()
    with torch.no_grad():
        value = offset_tensor(model, torch.as_tensor(features.reshape(1, -1), dtype=torch.float32))[0].cpu().numpy()
    if not np.isfinite(value).all() or abs(float(value.mean())) > 2e-7 or float(value.max() - value.min()) > .100001:
        raise IntegrityError("Offset centering/bound failed")
    return np.asarray(value, dtype=np.float32)


def natural_pairs(events: Sequence[Interaction], assignment: np.ndarray, cap: int, salt: str, *, cross_cell_only: bool = False) -> tuple[Pair, ...]:
    candidates: list[tuple[int, int, Pair]] = []
    for low_index, low in enumerate(events):
        for high in events[low_index + 1:]:
            if low.item_index == high.item_index or abs(high.rating - low.rating) < 2.0:
                continue
            preferred, rejected = (high, low) if high.rating > low.rating else (low, high)
            cross = int(assignment[preferred.item_index]) != int(assignment[rejected.item_index])
            if cross_cell_only and not cross:
                continue
            key, _ = hash_int(salt, user_id=preferred.user_id, low_item_id=rejected.movie_id, high_item_id=preferred.movie_id)
            pair = Pair(preferred.user_id, preferred.item_index, rejected.item_index, preferred.movie_id, rejected.movie_id, cross)
            candidates.append((key, min(preferred.movie_id, rejected.movie_id), pair))
    candidates.sort(key=lambda value: (value[0], value[1], value[2].preferred_movie_id, value[2].rejected_movie_id))
    return tuple(value[2] for value in candidates[:cap])


def pair_identity_hash(pairs: Sequence[Pair]) -> str:
    return sha256_bytes(canonical_json_bytes([(p.user_id, p.preferred_movie_id, p.rejected_movie_id, p.cross_cell) for p in pairs]))


def train_models(features: Mapping[int, np.ndarray], queries: Mapping[int, np.ndarray], R: Mapping[int, Sequence[Interaction]], vectors: np.ndarray, assignment: np.ndarray) -> tuple[Mapping[int, Mapping[int, Any]], Mapping[int, Mapping[int, Any]], Mapping[str, Any]]:
    _faiss, torch, _nn, functional = _imports()
    # The registered cap applies to cross-cell pairs.  Same-cell pairs are
    # retained only as diagnostics because their centered cell-offset gradient
    # is identically zero; they cannot consume the training cap.
    by_user = {user_id: natural_pairs(events, assignment, 64, "20260862:{user_id}:{low_item_id}:{high_item_id}", cross_cell_only=True) for user_id, events in R.items()}
    uncapped_diagnostic = {user_id: natural_pairs(events, assignment, 100_000, "20260862:{user_id}:{low_item_id}:{high_item_id}") for user_id, events in R.items()}
    cross_pairs = sum(sum(pair.cross_cell for pair in pairs) for pairs in by_user.values())
    cross_users = sum(any(pair.cross_cell for pair in pairs) for pairs in by_user.values())
    natural_states: dict[int, dict[int, Any]] = {}
    shuffled_states: dict[int, dict[int, Any]] = {}
    diagnostics: dict[str, Any] = {
        "cross_cell_pairs": cross_pairs,
        "cross_cell_users": cross_users,
        "same_cell_diagnostic_pairs": sum(sum(not pair.cross_cell for pair in pairs) for pairs in uncapped_diagnostic.values()),
        "training_pair_identity_sha256": pair_identity_hash(tuple(pair for pairs in by_user.values() for pair in pairs)),
        "seeds": {},
    }

    for seed in SEEDS:
        initial = make_offset_model(seed).state_dict()
        seed_diag: dict[str, Any] = {}
        for shuffled, destination, label in ((False, natural_states, "natural"), (True, shuffled_states, "shuffled")):
            model = make_offset_model(seed); model.load_state_dict(initial)
            optimizer = torch.optim.Adam(model.parameters(), lr=.003, weight_decay=1e-4)
            destination[seed] = {}
            losses: list[float] = []
            for epoch in range(1, 41):
                optimizer.zero_grad(set_to_none=True)
                user_losses = []
                for user_id in sorted(by_user):
                    pairs = by_user[user_id]
                    if not pairs:
                        continue
                    values = offset_tensor(model, torch.as_tensor(features[user_id].reshape(1, -1), dtype=torch.float32))[0]
                    pair_losses = []
                    query = queries[user_id]
                    for pair in pairs:
                        preferred, rejected = pair.preferred, pair.rejected
                        if shuffled:
                            coin, _ = hash_int("20260863:{user_id}:{low_item_id}:{high_item_id}", user_id=user_id, low_item_id=pair.rejected_movie_id, high_item_id=pair.preferred_movie_id)
                            if coin & 1:
                                preferred, rejected = rejected, preferred
                        base = float(query @ vectors[preferred] - query @ vectors[rejected])
                        advantage = torch.as_tensor(base, dtype=torch.float32) + values[int(assignment[preferred])] - values[int(assignment[rejected])]
                        pair_losses.append(functional.softplus(5.0 * (.05 - advantage)))
                    user_losses.append(torch.stack(pair_losses).mean())
                if not user_losses:
                    raise IntegrityError("No R training pairs")
                loss = torch.stack(user_losses).mean(); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
                losses.append(float(loss.detach()))
                if epoch in EPOCHS:
                    destination[seed][epoch] = {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
            seed_diag[label] = {"optimizer_steps": 40, "loss_first": losses[0], "loss_last": losses[-1], "checkpoint_epochs": list(destination[seed])}
        diagnostics["seeds"][str(seed)] = seed_diag
    return natural_states, shuffled_states, diagnostics


def load_model_state(seed: int, state: Mapping[str, Any]) -> Any:
    model = make_offset_model(seed); model.load_state_dict(state); model.eval(); return model


def stable_rank(indices: np.ndarray, scores: np.ndarray, movie_ids: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    if len(indices) != len(scores) or not np.isfinite(scores).all():
        raise IntegrityError("Invalid ranking inputs")
    order = np.lexsort((movie_ids[indices], -np.asarray(scores, dtype=np.float32)))[:k]
    return indices[order].astype(np.int64), np.asarray(scores, dtype=np.float32)[order]


def select_cells(query: np.ndarray, centroids: np.ndarray, offsets: np.ndarray, use_offsets: bool) -> np.ndarray:
    logits = np.asarray(centroids @ query, dtype=np.float32)
    if use_offsets:
        logits = np.asarray(logits + offsets, dtype=np.float32)
    cells = np.arange(32, dtype=np.int64)
    return cells[np.lexsort((cells, -logits))[:4]]


def retrieve(query: np.ndarray, history_items: frozenset[int], partitions: Partitions, movie_ids: np.ndarray, offsets: np.ndarray, method: str, *, k: int = 100) -> tuple[np.ndarray, np.ndarray, np.ndarray, Mapping[str, int]]:
    if method not in METHODS:
        raise ValueError(method)
    if method == "popularity":
        raise ValueError("Popularity is produced separately")
    all_cells = method in ("raw_full_exact_semantic", "aligned_full_exact")
    route_offset = method in ("pivot_route_only", "pivot_full", "shuffled_pivot", "aligned_full_exact")
    rank_offset = method in ("pivot_rerank_only", "pivot_full", "shuffled_pivot", "aligned_full_exact")
    cells = np.arange(32, dtype=np.int64) if all_cells else select_cells(query, partitions.centroids, offsets, route_offset)
    gathered_items: list[int] = []
    gathered_scores: list[float] = []
    for cell in cells:
        scores, positions = partitions.indexes[int(cell)].search(np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32), 334)
        if positions.shape != (1, 334):
            raise IntegrityError("FAISS did not return every shard slot")
        for position, score in zip(positions[0], scores[0]):
            item = int(partitions.shard_item_indices[int(cell)][int(position)])
            if item < 0 or item in history_items:
                continue
            gathered_items.append(item)
            gathered_scores.append(float(np.float32(score + (offsets[int(cell)] if rank_offset else 0.0))))
    indices = np.asarray(gathered_items, dtype=np.int64)
    scores = np.asarray(gathered_scores, dtype=np.float32)
    selected, selected_scores = stable_rank(indices, scores, movie_ids, k)
    if len(selected) != k or len(set(map(int, selected))) != k or any(int(item) in history_items for item in selected):
        raise IntegrityError("Retrieval did not return 100 unique unseen real items")
    work = {"coarse_dots": 32, "shard_slot_dots": int(len(cells) * 334), "probes": int(len(cells)), "sentinels": int(sum(np.any(partitions.shard_item_indices[int(cell)] < 0) for cell in cells))}
    if method in FIXED_WORK_METHODS and work["shard_slot_dots"] != 1336:
        raise IntegrityError("Unequal fixed-work retrieval")
    return selected, selected_scores, cells, work


def matrix_score_audit(query: np.ndarray, partitions: Partitions, vectors: np.ndarray, movie_ids: np.ndarray, offsets: np.ndarray) -> Mapping[str, float | int]:
    """Tolerance-only, item-ID-aligned audit over every real catalog item."""
    canonical = np.full(len(vectors), np.nan, dtype=np.float32)
    for cell in range(32):
        scores, positions = partitions.indexes[cell].search(np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32), 334)
        for position, score in zip(positions[0], scores[0]):
            item = int(partitions.shard_item_indices[cell][int(position)])
            if item >= 0:
                if math.isfinite(float(canonical[item])):
                    raise IntegrityError("Item appears in more than one FAISS shard")
                canonical[item] = np.float32(score + offsets[cell])
    if not np.isfinite(canonical).all():
        raise IntegrityError("Canonical FAISS audit did not cover every real item")
    matrix = np.asarray(vectors @ query + offsets[partitions.assignment], dtype=np.float32)
    error = np.abs(matrix - canonical)
    tolerance = 2e-6 + 2e-6 * np.abs(matrix)
    if not np.all(error <= tolerance):
        raise IntegrityError("FAISS/matrix score audit exceeds registered tolerance")
    indices = np.arange(len(movie_ids), dtype=np.int64)
    order = np.lexsort((movie_ids, -canonical))
    sorted_scores = canonical[order]
    margin = float(sorted_scores[99] - sorted_scores[100])
    threshold = float(sorted_scores[99])
    near = int(np.sum(np.abs(canonical - threshold) <= (2e-6 + 2e-6 * abs(threshold))))
    return {"items_aligned_by_movie_id": int(len(movie_ids)), "movie_id_order_sha256": sha256_bytes(np.ascontiguousarray(movie_ids, dtype="<i8").tobytes()), "maximum_absolute_error": float(error.max(initial=0.0)), "rank_100_101_margin": margin, "near_tie_set_size": near}


def skeleton_stage_arrays(ratings_path: Path, user_ids: Sequence[int], layouts: Mapping[int, Layout], stage: str) -> Mapping[str, np.ndarray]:
    """Read user/timestamp/ordinal only; item identity and rating stay unopened."""
    stage_index = {"R": 1, "V": 2, "T": 3}.get(stage)
    if stage_index is None:
        raise ValueError(stage)
    selected = frozenset(user_ids)
    rows: list[tuple[int, int, int]] = []
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton(line, ordinal)
            layout = layouts.get(row.user_id)
            if row.user_id in selected and layout is not None and layout.minimum_timestamps[stage_index] <= row.timestamp <= layout.maximum_timestamps[stage_index]:
                rows.append((row.user_id, row.timestamp, row.ordinal))
    expected = sum(layouts[user_id].counts[stage_index] for user_id in user_ids)
    if len(rows) != expected:
        raise IntegrityError(f"Target-blind {stage} basis count mismatch")
    values = np.asarray(rows, dtype=np.int64)
    return {"user_id": values[:, 0], "timestamp": values[:, 1], "source_row_ordinal": values[:, 2]}


def prefix_arrays(user_ids: Sequence[int], histories: Mapping[int, Sequence[Interaction]], width: int = 300) -> Mapping[str, np.ndarray]:
    items = np.full((len(user_ids), width), -1, dtype=np.int64)
    movie_ids = np.full_like(items, -1)
    counts = np.zeros(len(user_ids), dtype=np.int16)
    for row, user_id in enumerate(user_ids):
        history = histories[user_id]
        if len(history) > width:
            raise IntegrityError("History exceeds registered 300-event maximum")
        counts[row] = len(history)
        items[row, :len(history)] = [event.item_index for event in history]
        movie_ids[row, :len(history)] = [event.movie_id for event in history]
    return {"history_item_index": items, "history_movie_id": movie_ids, "history_count": counts}


def model_state_bytes(state: Mapping[str, Any]) -> bytes:
    _faiss, torch, _nn, _functional = _imports()
    buffer = io.BytesIO(); torch.save(dict(state), buffer); return buffer.getvalue()


def publish_partition_artifacts(directory: Path, partitions: Partitions, vectors: np.ndarray, movie_ids: np.ndarray) -> Mapping[str, Any]:
    faiss, _torch, _nn, _functional = _imports()
    files: dict[str, str] = {}
    files["partition_arrays.npz"] = publish_npz(
        directory / "partition_arrays.npz",
        assignment=partitions.assignment,
        centroids=partitions.centroids,
        movie_ids=movie_ids,
        semantic_vectors=vectors,
        initial_centroid_hashes=np.asarray(partitions.initial_centroid_hashes, dtype="S64"),
    )
    for cell, index in enumerate(partitions.indexes):
        payload = bytes(faiss.serialize_index(index))
        files[f"shard_{cell:02d}.faiss"] = publish_bytes(directory / f"shard_{cell:02d}.faiss", payload)
        files[f"shard_{cell:02d}_map.npz"] = publish_npz(
            directory / f"shard_{cell:02d}_map.npz",
            item_index=partitions.shard_item_indices[cell], movie_id=partitions.shard_movie_ids[cell],
        )
    return {
        "schema": "pivot-partition-inventory-v1",
        "files": files,
        "assignment_sha256": sha256_bytes(np.ascontiguousarray(partitions.assignment).tobytes()),
        "centroids_sha256": sha256_bytes(np.ascontiguousarray(partitions.centroids, dtype="<f4").tobytes()),
        "physical_slots": [int(index.ntotal) for index in partitions.indexes],
        "real_counts": [int(np.sum(partitions.assignment == cell)) for cell in range(32)],
    }


def popularity_order(A: Mapping[int, Sequence[Interaction]], movie_ids: np.ndarray) -> np.ndarray:
    counts = np.zeros(len(movie_ids), dtype=np.int64)
    for events in A.values():
        for event in events:
            counts[event.item_index] += 1
    indices = np.arange(len(movie_ids), dtype=np.int64)
    return indices[np.lexsort((movie_ids, -counts))]


def popularity_retrieve(order: np.ndarray, history: frozenset[int], k: int = 100) -> tuple[np.ndarray, np.ndarray]:
    result = np.asarray([int(item) for item in order if int(item) not in history][:k], dtype=np.int64)
    if len(result) != k:
        raise IntegrityError("Popularity underfilled")
    return result, np.arange(k, 0, -1, dtype=np.float32)


def state_hash(state: Mapping[str, Any]) -> str:
    return sha256_bytes(model_state_bytes(state))


def build_candidate_bank(
    user_ids: Sequence[int],
    descriptors: Mapping[int, Descriptor],
    histories: Mapping[int, Sequence[Interaction]],
    partitions: Partitions,
    movie_ids: np.ndarray,
    A: Mapping[int, Sequence[Interaction]],
    natural_states: Mapping[int, Mapping[int, Mapping[str, Any]]],
    shuffled_states: Mapping[int, Mapping[int, Mapping[str, Any]]],
    epochs: Sequence[int],
) -> tuple[Mapping[str, np.ndarray], Mapping[str, Any]]:
    """Build every candidate/score bank before the current outcome join."""
    shape = (len(SEEDS), len(epochs), len(METHODS), len(user_ids), 100)
    candidates = np.full(shape, -1, dtype=np.int32)
    scores = np.full(shape, np.nan, dtype=np.float32)
    routes = np.full((len(SEEDS), len(epochs), len(METHODS), len(user_ids), 32), -1, dtype=np.int8)
    work = np.zeros((len(SEEDS), len(epochs), len(METHODS), len(user_ids), 4), dtype=np.int32)
    natural_offsets = np.zeros((len(SEEDS), len(epochs), len(user_ids), 32), dtype=np.float32)
    shuffled_offsets = np.zeros_like(natural_offsets)
    popularity = popularity_order(A, movie_ids)

    for seed_index, seed in enumerate(SEEDS):
        for epoch_index, epoch in enumerate(epochs):
            natural_model = load_model_state(seed, natural_states[seed][epoch])
            shuffled_model = load_model_state(seed, shuffled_states[seed][epoch])
            for user_index, user_id in enumerate(user_ids):
                feature = descriptor_vector(descriptors[user_id])
                natural = offset_numpy(natural_model, feature)
                shuffled = offset_numpy(shuffled_model, feature)
                natural_offsets[seed_index, epoch_index, user_index] = natural
                shuffled_offsets[seed_index, epoch_index, user_index] = shuffled
                history = frozenset(event.item_index for event in histories[user_id])
                for method_index, method in enumerate(METHODS):
                    if method == "popularity":
                        selected, selected_scores = popularity_retrieve(popularity, history)
                        cells = np.asarray([], dtype=np.int64); observed_work = {"coarse_dots": 0, "shard_slot_dots": 0, "probes": 0, "sentinels": 0}
                    else:
                        selected_offsets = shuffled if method == "shuffled_pivot" else natural
                        selected, selected_scores, cells, observed_work = retrieve(descriptors[user_id].query, history, partitions, movie_ids, selected_offsets, method)
                    candidates[seed_index, epoch_index, method_index, user_index] = selected
                    scores[seed_index, epoch_index, method_index, user_index] = selected_scores
                    routes[seed_index, epoch_index, method_index, user_index, :len(cells)] = cells.astype(np.int8)
                    work[seed_index, epoch_index, method_index, user_index] = [observed_work[name] for name in ("coarse_dots", "shard_slot_dots", "probes", "sentinels")]
    arrays = {
        "seeds": np.asarray(SEEDS, dtype=np.int64),
        "epochs": np.asarray(epochs, dtype=np.int16),
        "methods": np.asarray(METHODS, dtype="S32"),
        "user_ids": np.asarray(user_ids, dtype=np.int64),
        "candidate_item_index": candidates,
        "candidate_movie_id": movie_ids[candidates],
        "candidate_score": scores,
        "route_cell": routes,
        "work_counts": work,
        "natural_offset": natural_offsets,
        "shuffled_offset": shuffled_offsets,
    }
    invariants = {
        "candidate_shape": list(shape),
        "fixed_work_exact": bool(np.all(work[:, :, 2:7, :, 0] == 32) and np.all(work[:, :, 2:7, :, 1] == 1336) and np.all(work[:, :, 2:7, :, 2] == 4)),
        "candidate_unique_unseen": True,
        "score_audits_deferred_to_explicit_tolerance_only_check": True,
    }
    if not invariants["fixed_work_exact"]:
        raise IntegrityError("Candidate bank fixed-work invariant failed")
    return arrays, invariants


def complete_score_audit(user_ids: Sequence[int], descriptors: Mapping[int, Descriptor], partitions: Partitions, vectors: np.ndarray, movie_ids: np.ndarray, offsets: np.ndarray) -> Mapping[str, np.ndarray]:
    """Audit all seed×user×item scores by aligned item ID, never by rank IDs."""
    if offsets.shape != (len(SEEDS), len(user_ids), 32):
        raise IntegrityError("Complete score-audit offset shape mismatch")
    max_error = np.full((len(SEEDS), len(user_ids)), np.nan, dtype=np.float64)
    margins = np.full_like(max_error, np.nan)
    near_ties = np.zeros((len(SEEDS), len(user_ids)), dtype=np.int32)
    for seed_index in range(len(SEEDS)):
        for user_index, user_id in enumerate(user_ids):
            record = matrix_score_audit(descriptors[user_id].query, partitions, vectors, movie_ids, offsets[seed_index, user_index])
            max_error[seed_index, user_index] = record["maximum_absolute_error"]
            margins[seed_index, user_index] = record["rank_100_101_margin"]
            near_ties[seed_index, user_index] = record["near_tie_set_size"]
    if not np.isfinite(max_error).all() or not np.isfinite(margins).all():
        raise IntegrityError("Incomplete/nonfinite all-request score audit")
    return {"score_audit_max_abs_error": max_error, "score_audit_rank100_101_margin": margins, "score_audit_near_tie_count": near_ties}


def publish_bank(directory: Path, stage: str, arrays: Mapping[str, np.ndarray], metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    bank_name = f"{stage}_candidate_score_bank.npz"
    bank_hash = publish_npz(directory / bank_name, **arrays)
    manifest = {
        "schema": "pivot-target-blind-candidate-manifest-v1",
        "stage": stage,
        "published_utc": utc_now(),
        "target_item_identities_opened": False,
        "target_ratings_opened": False,
        "bank_file": bank_name,
        "bank_sha256": bank_hash,
        "array_schema": {name: {"dtype": str(value.dtype), "shape": list(value.shape)} for name, value in arrays.items()},
        **metadata,
    }
    manifest_hash = publish_json(directory / f"{stage}_manifest.json", manifest)
    return {**manifest, "manifest_sha256": manifest_hash}


def selected_bank_epoch(arrays: Mapping[str, np.ndarray], epoch: int) -> Mapping[str, np.ndarray]:
    epochs = list(map(int, arrays["epochs"]))
    index = epochs.index(epoch)
    result: dict[str, np.ndarray] = {}
    for name, value in arrays.items():
        if name in ("candidate_item_index", "candidate_movie_id", "candidate_score", "route_cell", "work_counts"):
            result[name] = value[:, index]
        elif name in ("natural_offset", "shuffled_offset"):
            result[name] = value[:, index]
        elif name == "epochs":
            result[name] = np.asarray([epoch], dtype=np.int16)
        else:
            result[name] = value
    return result


def validation_epoch_accuracy(user_ids: Sequence[int], V: Mapping[int, Sequence[Interaction]], descriptors: Mapping[int, Descriptor], partitions: Partitions, vectors: np.ndarray, natural_states: Mapping[int, Mapping[int, Mapping[str, Any]]]) -> tuple[int, Mapping[str, Any]]:
    pairs_by_user = {user_id: natural_pairs(V[user_id], partitions.assignment, 64, "20260867:{user_id}:{low_item_id}:{high_item_id}", cross_cell_only=True) for user_id in user_ids}
    results: dict[int, float] = {}
    seed_values: dict[int, list[float]] = {}
    for epoch in EPOCHS:
        per_seed: list[float] = []
        for seed in SEEDS:
            model = load_model_state(seed, natural_states[seed][epoch])
            per_user: list[float] = []
            for user_id in user_ids:
                pairs = pairs_by_user[user_id]
                if not pairs:
                    continue
                offsets = offset_numpy(model, descriptor_vector(descriptors[user_id]))
                query = descriptors[user_id].query
                correct = [float(query @ vectors[pair.preferred] + offsets[int(partitions.assignment[pair.preferred])] > query @ vectors[pair.rejected] + offsets[int(partitions.assignment[pair.rejected])]) for pair in pairs]
                per_user.append(float(np.mean(correct)))
            per_seed.append(float(np.mean(per_user)) if per_user else float("nan"))
        seed_values[epoch] = per_seed
        results[epoch] = float(np.mean(per_seed))
    if not all(math.isfinite(value) for value in results.values()):
        raise IntegrityError("Validation checkpoint accuracy lacks support")
    selected = max(EPOCHS, key=lambda epoch: (results[epoch], -epoch))
    support_pairs = sum(map(len, pairs_by_user.values()))
    support_users = sum(bool(value) for value in pairs_by_user.values())
    return selected, {"mean_accuracy": {str(key): value for key, value in results.items()}, "seed_accuracy": {str(key): value for key, value in seed_values.items()}, "selected_epoch": selected, "pair_count": support_pairs, "user_count": support_users, "pair_identity_sha256": pair_identity_hash(tuple(pair for values in pairs_by_user.values() for pair in values))}


def fixed_pairs_by_user(user_ids: Sequence[int], events: Mapping[int, Sequence[Interaction]], assignment: np.ndarray, stage: str) -> Mapping[int, tuple[Pair, ...]]:
    if stage == "V":
        salt = "20260869:{user_id}:{low_item_id}:{high_item_id}"
    elif stage == "T":
        salt = "20260865:{user_id}:{low_item_id}:{high_item_id}"
    else:
        raise ValueError(stage)
    return {user_id: natural_pairs(events[user_id], assignment, 100, salt) for user_id in user_ids}


def binary_ndcg(top_items: Sequence[int], relevant: frozenset[int], k: int = 10) -> float:
    gains = np.asarray([1.0 if int(item) in relevant else 0.0 for item in top_items[:k]], dtype=np.float64)
    discounts = 1.0 / np.log2(np.arange(2, k + 2, dtype=np.float64))
    ideal = float(discounts[:min(k, len(relevant))].sum())
    return float((gains * discounts).sum() / ideal) if ideal > 0 else float("nan")


def evaluate_bank(user_ids: Sequence[int], bank: Mapping[str, np.ndarray], outcomes: Mapping[int, Sequence[Interaction]], pairs_by_user: Mapping[int, Sequence[Pair]], assignment: np.ndarray) -> tuple[np.ndarray, Mapping[str, Any], Mapping[str, np.ndarray]]:
    values = np.full((len(SEEDS), len(METHODS), len(user_ids), len(METRICS)), np.nan, dtype=np.float64)
    metric_index = {name: index for index, name in enumerate(METRICS)}
    pair_rows: list[tuple[int, int, int, int]] = []
    for user_index, user_id in enumerate(user_ids):
        pairs = tuple(pairs_by_user[user_id])
        for pair in pairs:
            pair_rows.append((user_index, pair.preferred, pair.rejected, int(pair.cross_cell)))
        relevant = frozenset(event.item_index for event in outcomes[user_id] if event.rating >= 4.0)
        low = frozenset(event.item_index for event in outcomes[user_id] if event.rating <= 2.0)
        for seed_index in range(len(SEEDS)):
            oracle = set(map(int, bank["candidate_item_index"][seed_index, METHODS.index("aligned_full_exact"), user_index]))
            for method_index, method in enumerate(METHODS):
                candidates = list(map(int, bank["candidate_item_index"][seed_index, method_index, user_index]))
                candidate_set = set(candidates); top10 = candidates[:10]
                if relevant:
                    values[seed_index, method_index, user_index, metric_index["future_liked_recall_at_100"]] = len(candidate_set & relevant) / len(relevant)
                    values[seed_index, method_index, user_index, metric_index["recall_at_10"]] = len(set(top10) & relevant) / len(relevant)
                    values[seed_index, method_index, user_index, metric_index["ndcg_at_10"]] = binary_ndcg(top10, relevant)
                if pairs:
                    exposures = [float(pair.preferred in candidate_set) - float(pair.rejected in candidate_set) for pair in pairs]
                    values[seed_index, method_index, user_index, metric_index["cpe_at_100"]] = float(np.mean(exposures))
                    cross = [value for value, pair in zip(exposures, pairs) if pair.cross_cell]
                    if cross:
                        values[seed_index, method_index, user_index, metric_index["cross_cell_cpe_at_100"]] = float(np.mean(cross))
                    ranks = {item: rank + 1 for rank, item in enumerate(top10)}
                    spce = [float(ranks.get(pair.preferred, 11) < ranks.get(pair.rejected, 11)) for pair in pairs]
                    values[seed_index, method_index, user_index, metric_index["spce_at_10"]] = float(np.mean(spce))
                if method == "pivot_full":
                    values[seed_index, method_index, user_index, metric_index["aligned_oracle_overlap_at_100"]] = len(candidate_set & oracle) / 100.0
                values[seed_index, method_index, user_index, metric_index["low_rating_intrusion_at_10"]] = len(set(top10) & low) / 10.0
    pair_array = np.asarray(pair_rows, dtype=np.int64).reshape(-1, 4)
    support = {
        "relevant_users": sum(any(event.rating >= 4.0 for event in outcomes[user_id]) for user_id in user_ids),
        "fixed_pairs": int(len(pair_rows)),
        "pair_users": sum(bool(pairs_by_user[user_id]) for user_id in user_ids),
        "pair_identity_sha256": pair_identity_hash(tuple(pair for user_id in user_ids for pair in pairs_by_user[user_id])),
    }
    raw_pairs = {"pair_user_row": pair_array[:, 0], "pair_preferred_item": pair_array[:, 1], "pair_rejected_item": pair_array[:, 2], "pair_cross_cell": pair_array[:, 3]}
    return values, support, raw_pairs


def finite_user_difference(metrics: np.ndarray, left_method: str, right_method: str, metric: str) -> tuple[np.ndarray, np.ndarray]:
    def seed_mean(values: np.ndarray) -> np.ndarray:
        finite = np.isfinite(values)
        counts = finite.sum(axis=0)
        result = np.full(values.shape[1], np.nan, dtype=np.float64)
        np.divide(np.where(finite, values, 0.0).sum(axis=0), counts, out=result, where=counts > 0)
        return result
    left = seed_mean(metrics[:, METHODS.index(left_method), :, METRICS.index(metric)])
    right = seed_mean(metrics[:, METHODS.index(right_method), :, METRICS.index(metric)])
    supported = np.isfinite(left) & np.isfinite(right)
    return left[supported] - right[supported], np.flatnonzero(supported)


def paired_summary(differences: np.ndarray, *, draws: int = 5000, seed: int = 20260864) -> Mapping[str, Any]:
    values = np.asarray(differences, dtype=np.float64)
    values = values[np.isfinite(values)]
    if not len(values):
        return {"users": 0, "mean": None, "lower": None, "upper": None, "support_failed": True}
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    for start in range(0, draws, 128):
        stop = min(draws, start + 128)
        indices = rng.integers(0, len(values), size=(stop - start, len(values)))
        means[start:stop] = values[indices].mean(axis=1)
    return {"users": int(len(values)), "mean": float(values.mean()), "lower": float(np.quantile(means, .025, method="linear")), "upper": float(np.quantile(means, .975, method="linear")), "support_failed": False}


def centered_power(metrics: np.ndarray) -> Mapping[str, Any]:
    records: dict[str, Any] = {}
    rng = np.random.default_rng(20260866)
    for metric in ("future_liked_recall_at_100", "cpe_at_100"):
        values, _rows = finite_user_difference(metrics, "pivot_full", "balanced_geometric_ivf", metric)
        if not len(values) or not np.isfinite(values).all():
            records[metric] = {"users": 0, "detection": 0.0, "passed": False}
            continue
        synthetic = values - values.mean() + .010
        detected = 0
        for _outer in range(500):
            outer = synthetic[rng.integers(0, len(synthetic), size=len(synthetic))]
            inner_means = np.empty(500, dtype=np.float64)
            for start in range(0, 500, 100):
                stop = min(500, start + 100)
                inner = rng.integers(0, len(outer), size=(stop - start, len(outer)))
                inner_means[start:stop] = outer[inner].mean(axis=1)
            detected += float(np.quantile(inner_means, .025, method="linear")) > 0.0
        fraction = detected / 500.0
        records[metric] = {"users": int(len(values)), "detection": fraction, "passed": fraction >= .80}
    return {"schema": "pivot-validation-power-v1", "seed": 20260866, "records": records, "passed": all(value["passed"] for value in records.values())}


def choose_comparator(metrics: np.ndarray) -> str:
    candidates = ("balanced_geometric_ivf", "raw_full_exact_semantic")
    summaries: dict[str, float] = {}
    for method in candidates:
        values = metrics[:, METHODS.index(method), :, METRICS.index("ndcg_at_10")]
        finite = values[np.isfinite(values)]
        summaries[method] = float(finite.mean()) if len(finite) else float("nan")
    if not all(math.isfinite(value) for value in summaries.values()):
        raise IntegrityError("Validation comparator lacks NDCG support")
    return max(candidates, key=lambda method: (summaries[method], -candidates.index(method)))


def action_surface(bank: Mapping[str, np.ndarray], pair_raw: Mapping[str, np.ndarray]) -> Mapping[str, float]:
    pivot = bank["candidate_item_index"][:, METHODS.index("pivot_full")]
    geometric = bank["candidate_item_index"][:, METHODS.index("balanced_geometric_ivf")]
    pivot_routes = bank["route_cell"][:, METHODS.index("pivot_full"), :, :4]
    geo_routes = bank["route_cell"][:, METHODS.index("balanced_geometric_ivf"), :, :4]
    route_changed = float(np.mean(np.any(np.sort(pivot_routes, axis=-1) != np.sort(geo_routes, axis=-1), axis=-1)))
    changed = 0; total = 0; jaccards: list[float] = []
    endpoints_by_user: dict[int, set[int]] = {}
    for user_row, preferred, rejected in zip(pair_raw["pair_user_row"], pair_raw["pair_preferred_item"], pair_raw["pair_rejected_item"]):
        endpoints_by_user.setdefault(int(user_row), set()).update((int(preferred), int(rejected)))
    for seed_index in range(len(SEEDS)):
        for user_row in range(pivot.shape[1]):
            left = set(map(int, pivot[seed_index, user_row])); right = set(map(int, geometric[seed_index, user_row]))
            union = left | right; jaccards.append(1.0 - len(left & right) / len(union))
        for user_row, endpoints in endpoints_by_user.items():
            left = set(map(int, pivot[seed_index, user_row])); right = set(map(int, geometric[seed_index, user_row]))
            for endpoint in endpoints:
                changed += (endpoint in left) != (endpoint in right); total += 1
    return {"route_change_fraction": route_changed, "endpoint_membership_xor_fraction": changed / total if total else 0.0, "mean_candidate_jaccard_distance": float(np.mean(jaccards)) if jaccards else 0.0, "endpoint_rows": total}


@contextlib.contextmanager
def pinned_single_thread() -> Iterable[Mapping[str, Any]]:
    faiss, torch, _nn, _functional = _imports()
    faiss.omp_set_num_threads(1); torch.set_num_threads(1)
    record: dict[str, Any] = {"affinity_supported": False, "affinity": None}
    process = None; old_affinity = None
    windows_handle: Any | None = None
    windows_old_mask: int | None = None
    try:
        import psutil
        process = psutil.Process(); old_affinity = process.cpu_affinity()
        if old_affinity:
            process.cpu_affinity([old_affinity[0]])
            record.update({"affinity_supported": True, "affinity": [old_affinity[0]]})
    except Exception as error:
        record["psutil_affinity_error"] = type(error).__name__
        if os.name != "nt":
            raise IntegrityError("CPU affinity is unavailable") from error
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
        kernel32.GetProcessAffinityMask.restype = ctypes.c_int
        kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        kernel32.SetProcessAffinityMask.restype = ctypes.c_int
        process_mask = ctypes.c_size_t(); system_mask = ctypes.c_size_t()
        windows_handle = kernel32.GetCurrentProcess()
        if not kernel32.GetProcessAffinityMask(windows_handle, ctypes.byref(process_mask), ctypes.byref(system_mask)):
            raise IntegrityError(f"GetProcessAffinityMask failed: {ctypes.get_last_error()}")
        windows_old_mask = int(process_mask.value)
        pinned_mask = windows_old_mask & -windows_old_mask
        if not pinned_mask or not kernel32.SetProcessAffinityMask(windows_handle, ctypes.c_size_t(pinned_mask)):
            raise IntegrityError(f"SetProcessAffinityMask failed: {ctypes.get_last_error()}")
        record.update({"affinity_supported": True, "affinity_mask": pinned_mask, "affinity_backend": "windows_kernel32"})
    if not record["affinity_supported"]:
        raise IntegrityError("CPU affinity was not pinned")
    try:
        yield record
    finally:
        if process is not None and old_affinity:
            with contextlib.suppress(Exception):
                process.cpu_affinity(old_affinity)
        elif windows_handle is not None and windows_old_mask is not None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
            kernel32.SetProcessAffinityMask.restype = ctypes.c_int
            if not kernel32.SetProcessAffinityMask(windows_handle, ctypes.c_size_t(windows_old_mask)):
                raise IntegrityError(f"Failed to restore process affinity: {ctypes.get_last_error()}")


def peak_rss_bytes() -> int:
    """Return the process peak working set without a psutil dependency."""
    try:
        import psutil
        memory = psutil.Process().memory_info()
        value = int(getattr(memory, "peak_wset", memory.rss))
        if value > 0:
            return value
    except Exception:
        pass
    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessMemoryCounters), ctypes.c_ulong]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        counters = ProcessMemoryCounters(); counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise IntegrityError(f"GetProcessMemoryInfo failed: {ctypes.get_last_error()}")
        if int(counters.PeakWorkingSetSize) > 0:
            return int(counters.PeakWorkingSetSize)
    raise IntegrityError("Peak RSS is unavailable")


def measure_latency(user_ids: Sequence[int], A: Mapping[int, Sequence[Interaction]], test_histories: Mapping[int, Sequence[Interaction]], vectors: np.ndarray, partitions: Partitions, movie_ids: np.ndarray, natural_states: Mapping[int, Mapping[int, Mapping[str, Any]]], selected_epoch: int) -> tuple[Mapping[str, np.ndarray], Mapping[str, Any]]:
    selected_users = sorted(user_ids, key=lambda user_id: (hash_int("20260868:{user_id}", user_id=user_id)[0], user_id))[:512]
    durations = np.full((len(SEEDS), 2, len(selected_users), 7), np.nan, dtype=np.float64)
    methods = ("balanced_geometric_ivf", "pivot_full")
    environment: Mapping[str, Any]
    with pinned_single_thread() as environment:
        for seed_index, seed in enumerate(SEEDS):
            model = load_model_state(seed, natural_states[seed][selected_epoch])

            def one(user_id: int, method: str) -> None:
                # Rebuild the A-only descriptor and offset on every measured
                # request; no test-user offset or descriptor is cached.
                value = descriptor(A[user_id], vectors)
                offsets = offset_numpy(model, descriptor_vector(value)) if method == "pivot_full" else np.zeros(32, dtype=np.float32)
                retrieve(value.query, frozenset(event.item_index for event in test_histories[user_id]), partitions, movie_ids, offsets, method)

            for warmup in range(32):
                one(selected_users[warmup % len(selected_users)], methods[warmup & 1])
            for repetition in range(7):
                ordered_methods = methods if repetition % 2 == 0 else tuple(reversed(methods))
                for method in ordered_methods:
                    for user_index, user_id in enumerate(selected_users):
                        start = time.perf_counter_ns(); one(user_id, method); elapsed = (time.perf_counter_ns() - start) / 1e6
                        durations[seed_index, methods.index(method), user_index, repetition] = elapsed
    medians = np.median(durations, axis=-1)
    p95 = np.quantile(medians, .95, axis=-1, method="linear")
    ratios = p95[:, 1] / p95[:, 0]
    passed = bool(np.all(p95[:, 1] <= 3.0) and np.all(ratios <= 1.5))
    raw = {
        "seeds": np.asarray(SEEDS, dtype=np.int64),
        "methods": np.asarray(methods, dtype="S32"),
        "user_ids": np.asarray(selected_users, dtype=np.int64),
        "durations_ms": durations,
        "per_request_median_ms": medians,
        "p95_ms": p95,
        "p95_ratio": ratios,
    }
    peak_rss = peak_rss_bytes()
    report = {
        "schema": "pivot-latency-result-v1",
        "requests": len(selected_users), "warmups": 32, "repetitions": 7,
        "p95_ms": p95.tolist(), "p95_ratio": ratios.tolist(), "passed": passed,
        "timed_scope": "A descriptor/query + uncached MLP when applicable + 32 coarse + 4x334 FAISS + sentinel/history mask + merge/stable top100",
        "environment": {**dict(environment), "platform": platform.platform(), "processor": platform.processor(), "python": sys.version, "packages": package_versions(), "peak_rss_bytes_observed": peak_rss},
    }
    return raw, report


def event_arrays(user_ids: Sequence[int], outcomes: Mapping[int, Sequence[Interaction]], width: int) -> Mapping[str, np.ndarray]:
    item = np.full((len(user_ids), width), -1, dtype=np.int32)
    movie = np.full((len(user_ids), width), -1, dtype=np.int64)
    rating = np.full((len(user_ids), width), np.nan, dtype=np.float32)
    timestamp = np.full((len(user_ids), width), -1, dtype=np.int64)
    ordinal = np.full((len(user_ids), width), -1, dtype=np.int64)
    count = np.zeros(len(user_ids), dtype=np.int16)
    for row, user_id in enumerate(user_ids):
        events = outcomes[user_id]
        if len(events) > width:
            raise IntegrityError("Outcome array width under-allocated")
        count[row] = len(events)
        item[row, :len(events)] = [event.item_index for event in events]
        movie[row, :len(events)] = [event.movie_id for event in events]
        rating[row, :len(events)] = [event.rating for event in events]
        timestamp[row, :len(events)] = [event.timestamp for event in events]
        ordinal[row, :len(events)] = [event.ordinal for event in events]
    return {"event_item_index": item, "event_movie_id": movie, "event_rating": rating, "event_timestamp": timestamp, "event_source_row_ordinal": ordinal, "event_count": count}


def _gate_comparison(metrics: np.ndarray, left: str, right: str, metric: str) -> Mapping[str, Any]:
    values, rows = finite_user_difference(metrics, left, right, metric)
    return {**paired_summary(values), "left": left, "right": right, "metric": metric, "common_user_rows_sha256": sha256_bytes(np.ascontiguousarray(rows, dtype="<i8").tobytes())}


def compute_gates(
    metrics: np.ndarray,
    R_diagnostics: Mapping[str, Any],
    V_support: Mapping[str, Any],
    T_support: Mapping[str, Any],
    power: Mapping[str, Any],
    surface: Mapping[str, Any],
    comparator: str,
    latency: Mapping[str, Any],
    g1_invariants: Mapping[str, bool],
) -> tuple[Mapping[str, bool], Mapping[str, Any]]:
    comparisons: dict[str, Mapping[str, Any]] = {}
    for metric in ("future_liked_recall_at_100", "cpe_at_100"):
        comparisons[f"g2_{metric}"] = _gate_comparison(metrics, "pivot_full", "balanced_geometric_ivf", metric)
        for control in ("pivot_route_only", "pivot_rerank_only"):
            comparisons[f"g3_{control}_{metric}"] = _gate_comparison(metrics, "pivot_full", control, metric)
    comparisons["g3_shuffled_cpe"] = _gate_comparison(metrics, "pivot_full", "shuffled_pivot", "cpe_at_100")
    for metric in ("ndcg_at_10", "recall_at_10", "spce_at_10"):
        comparisons[f"g5_{metric}"] = _gate_comparison(metrics, "pivot_full", comparator, metric)
    comparisons["g5_intrusion"] = _gate_comparison(metrics, "pivot_full", "balanced_geometric_ivf", "low_rating_intrusion_at_10")

    g2 = all(comparisons[f"g2_{metric}"]["mean"] is not None and comparisons[f"g2_{metric}"]["mean"] >= .010 and comparisons[f"g2_{metric}"]["lower"] > 0.0 for metric in ("future_liked_recall_at_100", "cpe_at_100"))
    g3 = True
    for metric in ("future_liked_recall_at_100", "cpe_at_100"):
        for control in ("pivot_route_only", "pivot_rerank_only"):
            record = comparisons[f"g3_{control}_{metric}"]
            g3 &= record["mean"] is not None and record["mean"] >= .002 and record["lower"] > 0.0
    shuffled = comparisons["g3_shuffled_cpe"]
    g3 &= shuffled["mean"] is not None and shuffled["mean"] >= .010 and shuffled["lower"] > 0.0

    def finite_scalar_mean(values: np.ndarray) -> float:
        finite = values[np.isfinite(values)]
        return float(finite.mean()) if len(finite) else float("nan")
    pivot_recall = finite_scalar_mean(metrics[:, METHODS.index("pivot_full"), :, METRICS.index("future_liked_recall_at_100")])
    raw_recall = finite_scalar_mean(metrics[:, METHODS.index("raw_full_exact_semantic"), :, METRICS.index("future_liked_recall_at_100")])
    overlap = finite_scalar_mean(metrics[:, METHODS.index("pivot_full"), :, METRICS.index("aligned_oracle_overlap_at_100")])
    retention = pivot_recall / raw_recall if raw_recall > 0 else float("nan")
    g4 = math.isfinite(overlap) and overlap >= .90 and math.isfinite(retention) and retention >= .95
    ndcg = comparisons["g5_ndcg_at_10"]; recall = comparisons["g5_recall_at_10"]; spce = comparisons["g5_spce_at_10"]; intrusion = comparisons["g5_intrusion"]
    g5_records_supported = all(record.get("mean") is not None and record.get("lower") is not None and record.get("upper") is not None for record in (ndcg, recall, spce, intrusion))
    g5 = bool(g5_records_supported and ndcg["mean"] >= -.002 and ndcg["lower"] > -.005 and recall["mean"] >= -.005 and recall["lower"] > -.010 and spce["mean"] >= 0.0 and intrusion["upper"] <= .002)
    g6 = bool(R_diagnostics["cross_cell_pairs"] >= 5000 and R_diagnostics["cross_cell_users"] >= 400 and V_support["relevant_users"] >= 400 and V_support["fixed_pairs"] >= 1500 and V_support["pair_users"] >= 300 and T_support["relevant_users"] >= 400 and T_support["fixed_pairs"] >= 1500 and T_support["pair_users"] >= 300 and power["passed"] and surface["route_change_fraction"] >= .10 and surface["endpoint_membership_xor_fraction"] >= .05)
    stable = 0; seed_records: dict[str, Any] = {}
    g7 = True
    for seed_index, seed in enumerate(SEEDS):
        record: dict[str, float] = {}
        primary_positive = True
        for metric in ("future_liked_recall_at_100", "cpe_at_100"):
            left = metrics[seed_index, METHODS.index("pivot_full"), :, METRICS.index(metric)]
            right = metrics[seed_index, METHODS.index("balanced_geometric_ivf"), :, METRICS.index(metric)]
            supported = np.isfinite(left) & np.isfinite(right)
            delta = float(np.mean(left[supported] - right[supported])) if np.any(supported) else float("nan")
            record[metric] = delta; primary_positive &= math.isfinite(delta) and delta > 0.0; g7 &= math.isfinite(delta) and delta >= 0.0
        left = metrics[seed_index, METHODS.index("pivot_full"), :, METRICS.index("ndcg_at_10")]
        right = metrics[seed_index, METHODS.index(comparator), :, METRICS.index("ndcg_at_10")]
        supported = np.isfinite(left) & np.isfinite(right); ndcg_delta = float(np.mean(left[supported] - right[supported])) if np.any(supported) else float("nan")
        record["ndcg_at_10"] = ndcg_delta; g7 &= math.isfinite(ndcg_delta) and ndcg_delta >= -.005
        stable += int(primary_positive); seed_records[str(seed)] = record
    g7 &= stable >= 2
    gates = {"G1": bool(g1_invariants and all(g1_invariants.values())), "G2": bool(g2), "G3": bool(g3), "G4": bool(g4), "G5": bool(g5), "G6": bool(g6), "G7": bool(g7), "G8": bool(latency["passed"])}
    details = {"comparisons": comparisons, "aligned_overlap": overlap, "raw_exact_retention": retention, "raw_exact_recall_denominator": raw_recall, "raw_exact_supported_users": int(np.sum(np.isfinite(metrics[0, METHODS.index("raw_full_exact_semantic"), :, METRICS.index("future_liked_recall_at_100")]))), "seed_records": seed_records, "g1_invariants": dict(g1_invariants), "R_support": dict(R_diagnostics), "V_support": dict(V_support), "T_support": dict(T_support), "power": dict(power), "surface": dict(surface), "latency": dict(latency)}
    return gates, details


def package_versions() -> Mapping[str, str]:
    result: dict[str, str] = {}
    for name in ("numpy", "scipy", "faiss-cpu", "torch", "scikit-learn", "threadpoolctl", "sentence-transformers", "transformers", "huggingface-hub", "psutil"):
        try:
            result[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            result[name] = "not-installed"
    return result


def recursive_hashes(root: Path, excluded: Iterable[Path] = ()) -> Mapping[str, str]:
    ignored = {path.resolve() for path in excluded}
    return {path.relative_to(root).as_posix(): sha256_file(path) for path in sorted(root.rglob("*")) if path.is_file() and path.resolve() not in ignored}


def acquire_lock(path: Path) -> str:
    token = sha256_bytes(os.urandom(32))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii") as handle:
        handle.write(token + "\n"); handle.flush(); os.fsync(handle.fileno())
    return token


def release_lock(path: Path, token: str) -> None:
    if path.read_text(encoding="ascii").strip() != token:
        raise IntegrityError("Runner lock token changed")
    path.unlink()


def common_record(schema: str, run_id: str, execution_fingerprint: str, **values: Any) -> Mapping[str, Any]:
    return {"schema": schema, "run_id": run_id, "execution_fingerprint_sha256": execution_fingerprint, **values}


def publish_runner_terminal(root: Path, run_id: str, execution_fingerprint: str, gates: Mapping[str, bool], details: Mapping[str, Any], termination_stage: str) -> Path:
    lock = root / "RUNNER.lock"
    before = recursive_hashes(root, excluded=(lock, root / "runner_completion_candidate.json", root / "runner_recursive_inventory.json"))
    closure_hash = sha256_bytes(canonical_json_bytes(before))
    all_g1_g8 = set(gates) == {f"G{index}" for index in range(1, 9)} and all(gates.values())
    candidate = common_record(
        "pivot-runner-candidate-v1", run_id, execution_fingerprint,
        produced_utc=utc_now(), producer_pid=os.getpid(), runner_lock_path=str(lock.resolve()),
        termination_stage=termination_stage, producer_gates=dict(gates), producer_gate_details=details,
        candidate_all_G1_G8=bool(all_g1_g8), external_G9=False, PROMISING=False,
        authoritative=False, may_publish_authoritative_marker=False,
        artifact_closure_before_candidate=before, artifact_closure_before_candidate_sha256=closure_hash,
        expected_final_inventory_file="runner_recursive_inventory.json",
    )
    candidate_path = root / "runner_completion_candidate.json"
    candidate_sha = publish_json(candidate_path, candidate)
    members = recursive_hashes(root, excluded=(lock, root / "runner_recursive_inventory.json"))
    inventory = common_record(
        "pivot-runner-inventory-v1", run_id, execution_fingerprint,
        created_utc=utc_now(), inventory_excludes=["RUNNER.lock", "runner_recursive_inventory.json"],
        files=members, file_count=len(members), runner_candidate_sha256=candidate_sha,
        members_sha256=sha256_bytes(canonical_json_bytes(members)),
    )
    publish_json(root / "runner_recursive_inventory.json", inventory)
    return candidate_path


def execute_authorized(
    config_path: Path,
    expected_config_sha256: str,
    expected_source_sha256: str,
    protocol_path: Path,
    output_dir: Path,
    archive_path: Path,
    cycle5_cohort_path: Path,
    semantic_path: Path | None,
    run_id: str,
) -> Mapping[str, Any]:
    """Execute the one-shot producer.  The external launcher owns authorization."""
    validate_locked_config(); full_config = load_external_config(config_path, expected_config_sha256)
    if not protocol_path.is_file() or not run_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in run_id):
        raise IntegrityError("Invalid protocol path or run ID")
    source_path = Path(__file__).resolve()
    observed_source_sha256 = sha256_file(source_path)
    if len(expected_source_sha256) != 64 or expected_source_sha256 != observed_source_sha256:
        raise IntegrityError(
            f"Runner source SHA-256 mismatch: expected {expected_source_sha256}, observed {observed_source_sha256}"
        )
    archive_binding = verify_archive(archive_path)
    excluded_users, exclusion_binding = cycle5_excluded_users(cycle5_cohort_path)
    source_files: dict[str, str] = {
        "runner": observed_source_sha256, "config": expected_config_sha256,
        "protocol": sha256_file(protocol_path),
    }
    project = source_path.parent.parent
    for label, path in (
        ("question", project / QUESTION_RELATIVE),
        ("architecture", project / "architecture-pivot.md"),
        ("launcher_verifier", source_path.parent / "launch_pivot_and_verify.py"),
    ):
        if path.is_file():
            source_files[label] = sha256_file(path)
    environment = {
        "python_executable": str(Path(sys.executable).resolve()), "python_version": sys.version,
        "platform": platform.platform(), "processor": platform.processor(), "packages": package_versions(),
        "thread_environment": {name: os.environ.get(name) for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS", "CUDA_VISIBLE_DEVICES", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "TOKENIZERS_PARALLELISM")},
    }
    execution_fingerprint = sha256_bytes(canonical_json_bytes({"run_id": run_id, "sources": source_files, "archive": archive_binding, "exclusion": exclusion_binding, "environment": environment}))
    if output_dir.exists():
        raise IntegrityError("Run directory already exists; resume/overwrite is forbidden")
    output_dir.mkdir(parents=True, exist_ok=False)
    lock_path = output_dir / "RUNNER.lock"; token = acquire_lock(lock_path)
    error_ledger = output_dir / "async_error_ledger.jsonl"; error_ledger.touch(exist_ok=False)
    install_async_error_hooks(error_ledger)
    completed = False
    try:
        publish_json(output_dir / "RUN_STARTED.json", common_record("pivot-run-started-v1", run_id, execution_fingerprint, started_utc=utc_now(), producer_pid=os.getpid(), runner_source_sha256=source_files["runner"], config_sha256=expected_config_sha256, protocol_sha256=source_files["protocol"], top_level_PROMISING=False))
        publish_json(output_dir / "environment.json", common_record("pivot-environment-v1", run_id, execution_fingerprint, **environment))
        publish_json(output_dir / "source_inventory.json", common_record("pivot-source-inventory-v1", run_id, execution_fingerprint, source_files=source_files, full_config_protocol_name=full_config["protocol_name"]))

        with tempfile.TemporaryDirectory(prefix="pivot_ml10m_extract_") as temporary:
            extracted = extract_allowed(archive_path, Path(temporary) / "extracted", authorized=True)
            extraction = {name: {"sha256": sha256_file(path), "bytes": path.stat().st_size} for name, path in extracted.items()}
            publish_json(output_dir / "archive_and_extraction.json", common_record("pivot-archive-v1", run_id, execution_fingerprint, archive=archive_binding, extracted_members=extraction, forbidden_tags_opened=False))
            movies, movie_to_index = load_movies(extracted["movies.dat"])
            movie_ids = np.asarray([movie.movie_id for movie in movies], dtype=np.int64)
            vectors, vector_binding = load_or_encode_vectors(semantic_path, movies)
            partitions = build_partitions(vectors, movie_ids)
            repeated = build_partitions(vectors, movie_ids)
            repeat_identity = bool(np.array_equal(partitions.assignment, repeated.assignment) and np.array_equal(partitions.centroids, repeated.centroids) and partitions.initial_centroid_hashes == repeated.initial_centroid_hashes)
            if not repeat_identity:
                raise IntegrityError("Repeated real-embedding partition construction changed hashes")
            representation_dir = output_dir / "immutable"
            partition_inventory = publish_partition_artifacts(representation_dir, partitions, vectors, movie_ids)
            publish_json(
                output_dir / "representation_and_shards.json",
                common_record(
                    "pivot-representation-v1",
                    run_id,
                    execution_fingerprint,
                    vector_binding=vector_binding,
                    semantic_npy_sha256=vector_binding["npy_sha256"],
                    partition_arrays_file="immutable/partition_arrays.npz",
                    partition_arrays_sha256=partition_inventory["files"]["partition_arrays.npz"],
                    partition_inventory=partition_inventory,
                    repeated_construction_hash_identity=repeat_identity,
                    outcome_accessed=False,
                ),
            )

            user_ids, layouts, A, structural_count, a_eligible_count = select_cohort(extracted["ratings.dat"], movie_to_index, excluded_users)
            if structural_count != 21_931:
                raise IntegrityError(f"Structural target-blind cohort count changed: {structural_count}")
            descriptors = {user_id: descriptor(A[user_id], vectors) for user_id in user_ids}
            features = {user_id: descriptor_vector(descriptors[user_id]) for user_id in user_ids}
            queries = {user_id: descriptors[user_id].query for user_id in user_ids}
            cohort_record = common_record(
                "pivot-cohort-layout-v1", run_id, execution_fingerprint,
                selected_user_ids=list(user_ids), cycle5_exclusion=exclusion_binding,
                structurally_eligible_after_exclusion=structural_count, A_eligible_count=a_eligible_count,
                order_rule="SHA256(20260861:{user_id}) then numeric user ID; first 600 passing A-only five-like predicate",
                layouts={str(user_id): dataclasses.asdict(layouts[user_id]) for user_id in user_ids},
            )
            publish_json(output_dir / "cohort_and_layout.json", cohort_record)
            a_routes = np.stack([select_cells(queries[user_id], partitions.centroids, np.zeros(32, dtype=np.float32), False) for user_id in user_ids]).astype(np.int8)
            a_route_scores = np.stack([partitions.centroids @ queries[user_id] for user_id in user_ids]).astype(np.float32)
            a_arrays = {
                "user_ids": np.asarray(user_ids, dtype=np.int64),
                "descriptor": np.stack([features[user_id] for user_id in user_ids]),
                "query": np.stack([queries[user_id] for user_id in user_ids]),
                "liked_centroid": np.stack([descriptors[user_id].liked for user_id in user_ids]),
                "disliked_centroid": np.stack([descriptors[user_id].disliked for user_id in user_ids]),
                "raw_route_score": a_route_scores, "raw_selected_cells": a_routes,
                **prefix_arrays(user_ids, A),
            }
            a_hash = publish_npz(output_dir / "stage_A_arrays.npz", **a_arrays)
            publish_json(output_dir / "stage_A_manifest.json", common_record("pivot-stage-a-v1", run_id, execution_fingerprint, arrays_file="stage_A_arrays.npz", arrays_sha256=a_hash, array_schema={name: {"dtype": str(value.dtype), "shape": list(value.shape)} for name, value in a_arrays.items()}, current_R_V_T_identities_or_ratings_opened=False))
            r_basis = skeleton_stage_arrays(extracted["ratings.dat"], user_ids, layouts, "R")
            r_basis_hash = publish_npz(output_dir / "stage_R_target_blind_basis.npz", **r_basis)
            r_basis_published_utc = utc_now()
            publish_json(output_dir / "stage_R_basis_manifest.json", common_record("pivot-stage-r-basis-v1", run_id, execution_fingerprint, arrays_file="stage_R_target_blind_basis.npz", arrays_sha256=r_basis_hash, row_key=["user_id", "timestamp", "source_row_ordinal"], item_identity_or_rating_retained=False, published_before_R_join=True, basis_published_utc=r_basis_published_utc))

            R = load_stage(extracted["ratings.dat"], user_ids, layouts, movie_to_index, "R")
            r_joined_utc = utc_now()
            assert_cross_stage_unique(user_ids, A, R)
            natural_states, shuffled_states, training_diagnostics = train_models(features, queries, R, vectors, partitions.assignment)
            checkpoint_files: dict[str, str] = {}
            for seed in SEEDS:
                for epoch in EPOCHS:
                    for label, states in (("natural", natural_states), ("shuffled", shuffled_states)):
                        name = f"checkpoints/{label}_seed{seed}_epoch{epoch}.pt"
                        checkpoint_files[name] = publish_bytes(output_dir / name, model_state_bytes(states[seed][epoch]))
            publish_json(output_dir / "training_manifest.json", common_record("pivot-training-v1", run_id, execution_fingerprint, R_opened_after_basis=True, R_basis_published_utc=r_basis_published_utc, R_joined_utc=r_joined_utc, diagnostics=training_diagnostics, checkpoint_files=checkpoint_files, optimizer="Adam", simpo_reference_model_forward_passes=0))

            V_histories = {user_id: history_for(user_id, "V", A, R) for user_id in user_ids}
            v_basis = skeleton_stage_arrays(extracted["ratings.dat"], user_ids, layouts, "V")
            v_basis_hash = publish_npz(output_dir / "stage_V_target_blind_basis.npz", **v_basis)
            v_bank, v_bank_invariants = build_candidate_bank(user_ids, descriptors, V_histories, partitions, movie_ids, A, natural_states, shuffled_states, EPOCHS)
            v_bank_hash = publish_npz(output_dir / "stage_V_candidate_score_bank.npz", **v_bank)
            v_bank_published_utc = utc_now()
            publish_json(output_dir / "stage_V_candidate_bank_manifest.json", common_record("pivot-stage-v-bank-v1", run_id, execution_fingerprint, basis_file="stage_V_target_blind_basis.npz", basis_sha256=v_basis_hash, bank_file="stage_V_candidate_score_bank.npz", bank_sha256=v_bank_hash, array_schema={name: {"dtype": str(value.dtype), "shape": list(value.shape), "byte_order": value.dtype.byteorder} for name, value in v_bank.items()}, axes={"candidate_item_index": ["seed", "epoch", "method", "user", "rank"], "route_cell": ["seed", "epoch", "method", "user", "route_slot"]}, invariants=v_bank_invariants, V_item_identities_or_ratings_opened=False, bank_published_utc=v_bank_published_utc))

            V = load_stage(extracted["ratings.dat"], user_ids, layouts, movie_to_index, "V")
            v_joined_utc = utc_now()
            assert_cross_stage_unique(user_ids, A, R, V)
            selected_epoch, checkpoint_selection = validation_epoch_accuracy(user_ids, V, descriptors, partitions, vectors, natural_states)
            selected_v_bank = selected_bank_epoch(v_bank, selected_epoch)
            empty_v_pairs = {user_id: tuple() for user_id in user_ids}
            relevance_only_metrics, _relevance_support, _relevance_pair_raw = evaluate_bank(
                user_ids, selected_v_bank, V, empty_v_pairs, partitions.assignment
            )
            comparator = choose_comparator(relevance_only_metrics)
            selected_hashes = {f"natural_seed{seed}": checkpoint_files[f"checkpoints/natural_seed{seed}_epoch{selected_epoch}.pt"] for seed in SEEDS}
            selected_hashes.update({f"shuffled_seed{seed}": checkpoint_files[f"checkpoints/shuffled_seed{seed}_epoch{selected_epoch}.pt"] for seed in SEEDS})
            choices_frozen_utc = utc_now()
            publish_json(output_dir / "frozen_choices.json", common_record("pivot-frozen-choices-v1", run_id, execution_fingerprint, V_bank_published_utc=v_bank_published_utc, V_joined_utc=v_joined_utc, frozen_utc=choices_frozen_utc, selected_epoch=selected_epoch, checkpoint_selection=checkpoint_selection, relevance_comparator=comparator, selected_checkpoint_sha256=selected_hashes, T_opened=False))
            # Only the already frozen epoch/comparator may enter the fixed
            # all-pair V estimand and registered centered power audit.
            v_pairs = fixed_pairs_by_user(user_ids, V, partitions.assignment, "V")
            v_metrics, v_support, v_pair_raw = evaluate_bank(user_ids, selected_v_bank, V, v_pairs, partitions.assignment)
            power = centered_power(v_metrics)
            # An indivisible equal-timestamp group can make a nominal 10% block
            # larger than 40 events.  The cohort lock itself supplies the only
            # valid upper bound (300 total events per user).
            v_event_raw = event_arrays(user_ids, V, 300)
            validation_raw = {
                "seeds": np.asarray(SEEDS, dtype=np.int64), "methods": np.asarray(METHODS, dtype="S32"), "metrics": np.asarray(METRICS, dtype="S48"), "user_ids": np.asarray(user_ids, dtype=np.int64),
                "per_user_metrics": v_metrics, "selected_epoch": np.asarray([selected_epoch], dtype=np.int16), "selected_comparator_index": np.asarray([METHODS.index(comparator)], dtype=np.int16),
                **{f"V_{name}": value for name, value in v_event_raw.items()}, **{f"V_{name}": value for name, value in v_pair_raw.items()},
            }
            validation_hash = publish_npz(output_dir / "raw_validation_metrics.npz", **validation_raw)
            power_audit_completed_utc = utc_now()
            publish_json(output_dir / "power_audit.json", common_record("pivot-power-audit-v1", run_id, execution_fingerprint, choices_frozen_utc=choices_frozen_utc, power_audit_completed_utc=power_audit_completed_utc, validation_support=v_support, checkpoint_support={"pairs": checkpoint_selection["pair_count"], "users": checkpoint_selection["user_count"]}, power=power, raw_validation_file="raw_validation_metrics.npz", raw_validation_sha256=validation_hash, T_opened=False))

            pre_T_pass = bool(training_diagnostics["cross_cell_pairs"] >= 5000 and training_diagnostics["cross_cell_users"] >= 400 and v_support["relevant_users"] >= 400 and v_support["fixed_pairs"] >= 1500 and v_support["pair_users"] >= 300 and power["passed"])
            if not pre_T_pass:
                gates = {f"G{index}": False for index in range(1, 9)}
                gates["G1"] = True
                publish_runner_terminal(output_dir, run_id, execution_fingerprint, gates, {"pre_T_support_power_failed": True, "R": training_diagnostics, "V": v_support, "power": power}, "pre_T_support_power_kill")
                completed = True
                return {"run_id": run_id, "termination_stage": "pre_T_support_power_kill", "PROMISING": False}

            T_histories = {user_id: history_for(user_id, "T", A, R, V) for user_id in user_ids}
            t_basis = skeleton_stage_arrays(extracted["ratings.dat"], user_ids, layouts, "T")
            t_basis_hash = publish_npz(output_dir / "stage_T_target_blind_basis.npz", **t_basis)
            t_bank_full, t_bank_invariants = build_candidate_bank(user_ids, descriptors, T_histories, partitions, movie_ids, A, natural_states, shuffled_states, (selected_epoch,))
            t_bank = selected_bank_epoch(t_bank_full, selected_epoch)
            score_raw = complete_score_audit(user_ids, descriptors, partitions, vectors, movie_ids, t_bank["natural_offset"])
            score_hash = publish_npz(output_dir / "score_audit_raw.npz", seeds=np.asarray(SEEDS, dtype=np.int64), user_ids=np.asarray(user_ids, dtype=np.int64), **score_raw)
            t_bank_hash = publish_npz(output_dir / "stage_T_candidate_score_bank.npz", **t_bank)
            t_bank_published_utc = utc_now()
            publish_json(output_dir / "stage_T_candidate_bank_manifest.json", common_record("pivot-stage-t-bank-v1", run_id, execution_fingerprint, choices_frozen_utc=choices_frozen_utc, power_audit_completed_utc=power_audit_completed_utc, basis_file="stage_T_target_blind_basis.npz", basis_sha256=t_basis_hash, bank_file="stage_T_candidate_score_bank.npz", bank_sha256=t_bank_hash, score_audit_file="score_audit_raw.npz", score_audit_sha256=score_hash, array_schema={name: {"dtype": str(value.dtype), "shape": list(value.shape), "byte_order": value.dtype.byteorder} for name, value in t_bank.items()}, axes={"candidate_item_index": ["seed", "method", "user", "rank"], "route_cell": ["seed", "method", "user", "route_slot"]}, invariants=t_bank_invariants, T_item_identities_or_ratings_opened=False, bank_published_utc=t_bank_published_utc))

            latency_raw, latency_report = measure_latency(user_ids, A, T_histories, vectors, partitions, movie_ids, natural_states, selected_epoch)
            latency_hash = publish_npz(output_dir / "latency_raw.npz", **latency_raw)
            publish_json(output_dir / "latency_raw_manifest.json", common_record("pivot-latency-raw-v1", run_id, execution_fingerprint, raw_file="latency_raw.npz", raw_sha256=latency_hash, axes={"durations_ms": ["seed", "method", "user", "repetition"]}, array_schema={name: {"dtype": str(value.dtype), "shape": list(value.shape), "byte_order": value.dtype.byteorder} for name, value in latency_raw.items()}, result=latency_report, outcome_access=False))
            if not latency_report["passed"]:
                gates = {f"G{index}": False for index in range(1, 9)}; gates["G1"] = True
                publish_runner_terminal(output_dir, run_id, execution_fingerprint, gates, {"pre_T_latency_failed": True, "latency": latency_report}, "pre_T_latency_kill")
                completed = True
                return {"run_id": run_id, "termination_stage": "pre_T_latency_kill", "PROMISING": False}

            T = load_stage(extracted["ratings.dat"], user_ids, layouts, movie_to_index, "T")
            t_joined_utc = utc_now()
            assert_cross_stage_unique(user_ids, A, R, V, T)
            t_pairs = fixed_pairs_by_user(user_ids, T, partitions.assignment, "T")
            t_metrics, t_support, t_pair_raw = evaluate_bank(user_ids, t_bank, T, t_pairs, partitions.assignment)
            surface = action_surface(t_bank, t_pair_raw)
            t_event_raw = event_arrays(user_ids, T, 300)
            test_raw = {
                "seeds": np.asarray(SEEDS, dtype=np.int64), "methods": np.asarray(METHODS, dtype="S32"), "metrics": np.asarray(METRICS, dtype="S48"), "user_ids": np.asarray(user_ids, dtype=np.int64),
                "per_user_metrics": t_metrics, "selected_epoch": np.asarray([selected_epoch], dtype=np.int16), "selected_comparator_index": np.asarray([METHODS.index(comparator)], dtype=np.int16),
                **{f"T_{name}": value for name, value in t_event_raw.items()}, **{f"T_{name}": value for name, value in t_pair_raw.items()},
            }
            test_hash = publish_npz(output_dir / "raw_test_metrics.npz", **test_raw)
            g1_invariants = {
                "fresh_600_users": len(user_ids) == 600 and not (set(user_ids) & excluded_users),
                "balanced_real_cells": [int(np.sum(partitions.assignment == cell)) for cell in range(32)] == [334] * 25 + [333] * 7,
                "physical_334_each": all(index.ntotal == 334 for index in partitions.indexes),
                "repeat_partition_identity": repeat_identity,
                "V_bank_fixed_work": bool(v_bank_invariants["fixed_work_exact"]),
                "T_bank_fixed_work": bool(t_bank_invariants["fixed_work_exact"]),
                "all_three_seeds": tuple(map(int, t_bank["seeds"])) == SEEDS,
                "score_audit_complete_finite": bool(np.isfinite(score_raw["score_audit_max_abs_error"]).all() and score_raw["score_audit_max_abs_error"].shape == (3, 600)),
            }
            gates, gate_details = compute_gates(t_metrics, training_diagnostics, v_support, t_support, power, surface, comparator, latency_report, g1_invariants)
            raw_manifest = common_record(
                "pivot-raw-arrays-v1", run_id, execution_fingerprint,
                validation_file="raw_validation_metrics.npz", validation_sha256=validation_hash,
                test_file="raw_test_metrics.npz", test_sha256=test_hash,
                candidate_bank_files={"V": "stage_V_candidate_score_bank.npz", "T": "stage_T_candidate_score_bank.npz"},
                candidate_bank_sha256={"V": v_bank_hash, "T": t_bank_hash}, score_audit_file="score_audit_raw.npz", score_audit_sha256=score_hash,
                validation_axes={"per_user_metrics": ["seed", "method", "user", "metric"]}, test_axes={"per_user_metrics": ["seed", "method", "user", "metric"]},
                metric_names=list(METRICS), method_names=list(METHODS), seed_values=list(SEEDS), user_ids_file_field="user_ids",
                fixed_pair_row_keys={"V": ["V_pair_user_row", "V_pair_preferred_item", "V_pair_rejected_item", "V_pair_cross_cell"], "T": ["T_pair_user_row", "T_pair_preferred_item", "T_pair_rejected_item", "T_pair_cross_cell"]},
                stage_barrier_times={"R_basis_published_utc": r_basis_published_utc, "R_joined_utc": r_joined_utc, "V_bank_published_utc": v_bank_published_utc, "V_joined_utc": v_joined_utc, "choices_frozen_utc": choices_frozen_utc, "power_audit_completed_utc": power_audit_completed_utc, "T_bank_published_utc": t_bank_published_utc, "T_joined_utc": t_joined_utc},
                producer_gates=gates, producer_gate_details=gate_details,
            )
            publish_json(output_dir / "raw_metric_arrays_manifest.json", raw_manifest)
            publish_runner_terminal(output_dir, run_id, execution_fingerprint, gates, gate_details, "post_T_producer_gates")
            completed = True
            return {"run_id": run_id, "termination_stage": "post_T_producer_gates", "candidate_all_G1_G8": all(gates.values()), "PROMISING": False, "external_G9": False}
    except BaseException as error:
        append_ledger(error_ledger, {"utc": utc_now(), "type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
        raise
    finally:
        release_lock(lock_path, token)
        if completed and error_ledger.stat().st_size:
            raise IntegrityError("Error ledger is nonempty after runner terminal publication")


def configure_numerical_threads(*, require_locked_environment: bool) -> Mapping[str, Any]:
    """Bind the numerical runtime before any model or FAISS work."""
    required = (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    )
    if require_locked_environment:
        mismatches = {name: os.environ.get(name) for name in required if os.environ.get(name) != "1"}
        offline = {
            name: os.environ.get(name)
            for name in ("CUDA_VISIBLE_DEVICES", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
        }
        if mismatches or offline != {
            "CUDA_VISIBLE_DEVICES": "-1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"
        }:
            raise IntegrityError(f"Launcher did not bind the numerical/offline environment: {mismatches}, {offline}")
    else:
        for name in required:
            os.environ.setdefault(name, "1")
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    faiss, torch, _nn, _functional = _imports()
    faiss.omp_set_num_threads(1)
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_interop_threads() != 1:
            raise IntegrityError("Torch inter-op threads were initialized above one")
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise IntegrityError("Torch thread binding failed")
    return {
        "faiss_threads": 1,
        "torch_intraop_threads": int(torch.get_num_threads()),
        "torch_interop_threads": int(torch.get_num_interop_threads()),
        "environment": {name: os.environ.get(name) for name in required},
    }


def synthetic_partitions(seed: int = 20260861) -> tuple[np.ndarray, np.ndarray, Partitions]:
    """Construct a small-code-path, full-cardinality synthetic serving index."""
    faiss, _torch, _nn, _functional = _imports()
    rng = np.random.default_rng(seed)
    vectors = rng.standard_normal((10_681, 384), dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    movie_ids = np.arange(1, 10_682, dtype=np.int64) * 2 + 1
    capacities = [334] * 25 + [333] * 7
    assignment = np.concatenate(
        [np.full(capacity, cell, dtype=np.int16) for cell, capacity in enumerate(capacities)]
    )
    centroids = np.stack(
        [normalise(vectors[assignment == cell].mean(axis=0)) for cell in range(32)]
    ).astype(np.float32)
    shard_indices: list[np.ndarray] = []
    shard_ids: list[np.ndarray] = []
    indexes: list[Any] = []
    for cell, capacity in enumerate(capacities):
        indices = np.flatnonzero(assignment == cell).astype(np.int64)
        ids = movie_ids[indices].copy()
        shard_vectors = vectors[indices]
        if capacity == 333:
            indices = np.concatenate([indices, np.asarray([-1], dtype=np.int64)])
            ids = np.concatenate([ids, np.asarray([-(cell + 1)], dtype=np.int64)])
            shard_vectors = np.vstack([shard_vectors, np.zeros((1, 384), dtype=np.float32)])
        index = faiss.IndexFlatIP(384)
        index.add(np.ascontiguousarray(shard_vectors, dtype=np.float32))
        shard_indices.append(indices)
        shard_ids.append(ids)
        indexes.append(index)
    partitions = Partitions(
        assignment=assignment,
        centroids=centroids,
        shard_item_indices=tuple(shard_indices),
        shard_movie_ids=tuple(shard_ids),
        indexes=tuple(indexes),
        initial_centroid_hashes=tuple(sha256_bytes(centroids[cell].astype("<f4").tobytes()) for cell in range(32)),
    )
    return vectors, movie_ids, partitions


def synthetic_self_test() -> Mapping[str, Any]:
    """Outcome-free adversarial tests for the producer's scientific operators."""
    validate_locked_config()
    configure_numerical_threads(require_locked_environment=False)
    tests: dict[str, bool] = {}

    rows = [Skeleton(7, timestamp, ordinal) for ordinal, timestamp in enumerate(
        (10, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 100)
    )]
    blocks = split_rows(rows)
    tests["timestamp_groups_indivisible"] = all(
        set(row.timestamp for row in blocks[left]).isdisjoint(row.timestamp for row in blocks[right])
        for left in range(4) for right in range(left + 1, 4)
    ) and sum(map(len, blocks)) == len(rows)
    tests["cutoff_tie_assigns_group_to_earlier_block"] = _nearest_boundary([4, 8, 12, 16], 6.0, 1, 3) == 2

    vectors, movie_ids, partitions = synthetic_partitions()
    query = normalise(vectors[:7].mean(axis=0))
    zeros = np.zeros(32, dtype=np.float32)
    cells = select_cells(query, partitions.centroids, zeros, False)
    selected_pool = np.concatenate([partitions.shard_item_indices[int(cell)] for cell in cells])
    adversarial_history = frozenset(map(int, selected_pool[selected_pool >= 0][:300]))
    geometric = retrieve(query, adversarial_history, partitions, movie_ids, zeros, "balanced_geometric_ivf")
    pivot_zero = retrieve(query, adversarial_history, partitions, movie_ids, zeros, "pivot_full")
    tests["balanced_physical_work"] = all(index.ntotal == 334 for index in partitions.indexes) and geometric[3]["shard_slot_dots"] == 1336
    tests["adversarial_300_history_still_returns_100"] = len(geometric[0]) == 100 and not (set(map(int, geometric[0])) & adversarial_history)
    tests["zero_offsets_equal_geometric"] = all(np.array_equal(left, right) for left, right in zip(geometric[:3], pivot_zero[:3]))
    audit = matrix_score_audit(query, partitions, vectors, movie_ids, zeros)
    tests["full_item_id_score_audit"] = audit["items_aligned_by_movie_id"] == 10_681 and audit["maximum_absolute_error"] <= 4e-6

    indices = np.asarray([2, 0, 1], dtype=np.int64)
    tie_ids = np.asarray([50, 10, 30], dtype=np.int64)
    ranked, _ = stable_rank(indices, np.ones(3, dtype=np.float32), tie_ids, 3)
    tests["stable_numeric_movie_id_tie_break"] = ranked.tolist() == [1, 2, 0]

    _faiss, torch, _nn, functional = _imports()
    raw = torch.zeros(32, dtype=torch.float32, requires_grad=True)
    centered = .05 * (raw - raw.mean())
    same_loss = functional.softplus(5.0 * (.05 - centered[3] + centered[3]))
    same_loss.backward()
    same_gradient = raw.grad.detach().clone()
    raw.grad.zero_()
    centered = .05 * (raw - raw.mean())
    cross_before = functional.softplus(5.0 * (.05 - centered[3] + centered[9]))
    cross_before.backward()
    cross_gradient = raw.grad.detach().clone()
    with torch.no_grad():
        updated = raw - .1 * cross_gradient
        updated_centered = .05 * (updated - updated.mean())
        cross_after = functional.softplus(5.0 * (.05 - updated_centered[3] + updated_centered[9]))
    tests["same_cell_zero_gradient"] = bool(torch.equal(same_gradient, torch.zeros_like(same_gradient)))
    tests["cross_cell_step_lowers_loss"] = float(cross_after) < float(cross_before.detach()) and float(cross_gradient.abs().sum()) > 0
    shifted = raw.detach() + 13.0
    tests["centering_removes_common_shift"] = bool(torch.allclose(.05 * (shifted - shifted.mean()), .05 * (raw.detach() - raw.detach().mean()), atol=1e-7, rtol=0))

    toy_candidates = np.zeros((3, len(METHODS), 1, 100), dtype=np.int32)
    rejected_list = np.asarray([102, *range(99)], dtype=np.int32)
    preferred_list = np.asarray([101, *range(99)], dtype=np.int32)
    for seed_index in range(3):
        for method_index, method in enumerate(METHODS):
            toy_candidates[seed_index, method_index, 0] = preferred_list if method in ("pivot_full", "aligned_full_exact") else rejected_list
    toy_bank = {"candidate_item_index": toy_candidates}
    toy_outcomes = {1: (Interaction(1, 101, 203, 5.0, 20, 1), Interaction(1, 102, 205, 1.0, 21, 2))}
    toy_pairs = {1: (Pair(1, 101, 102, 203, 205, True),)}
    toy_metrics, toy_support, _toy_raw = evaluate_bank((1,), toy_bank, toy_outcomes, toy_pairs, partitions.assignment)
    tests["toy_metrics"] = bool(
        toy_support["fixed_pairs"] == 1
        and toy_metrics[0, METHODS.index("pivot_full"), 0, METRICS.index("cpe_at_100")] == 1.0
        and toy_metrics[0, METHODS.index("balanced_geometric_ivf"), 0, METRICS.index("cpe_at_100")] == -1.0
    )
    tests["empty_support_fails_closed"] = bool(paired_summary(np.asarray([], dtype=np.float64))["support_failed"])

    with tempfile.TemporaryDirectory(prefix="pivot_publish_test_") as temporary:
        target = Path(temporary) / "once.json"
        publish_json(target, {"ok": True})
        collision_failed = False
        try:
            publish_json(target, {"ok": False})
        except (FileExistsError, IntegrityError):
            collision_failed = True
        tests["append_only_publication"] = collision_failed

    if not all(tests.values()):
        raise IntegrityError(f"Synthetic PIVOT self-test failed: {tests}")
    return {
        "schema": "pivot-producer-self-test-v1",
        "passed": True,
        "tests": tests,
        "archive_opened": False,
        "outcomes_accessed": False,
    }


def qualify_real_embeddings(
    semantic_path: Path,
    output_path: Path,
    config_path: Path,
    expected_config_sha256: str,
) -> Mapping[str, Any]:
    """Outcome-free real-matrix construction and machine timing qualification."""
    load_external_config(config_path, expected_config_sha256)
    configure_numerical_threads(require_locked_environment=False)
    if sha256_file(semantic_path) != SEMANTIC_SHA256:
        raise IntegrityError("Qualification semantic matrix hash mismatch")
    vectors = np.ascontiguousarray(np.load(semantic_path, allow_pickle=False), dtype=np.float32)
    if vectors.shape != (10_681, 384) or not np.isfinite(vectors).all():
        raise IntegrityError("Qualification semantic matrix shape/finite mismatch")
    # The registered matrix is in ascending numeric movie-ID order.  A strictly
    # increasing surrogate preserves every movie-ID tie break without opening
    # movies.dat or any user outcome.
    movie_ids = np.arange(10_681, dtype=np.int64)
    first = build_partitions(vectors, movie_ids)
    second = build_partitions(vectors, movie_ids)
    faiss, _torch, _nn, _functional = _imports()
    first_index_hashes = [sha256_bytes(bytes(faiss.serialize_index(index))) for index in first.indexes]
    second_index_hashes = [sha256_bytes(bytes(faiss.serialize_index(index))) for index in second.indexes]
    repeat_identity = bool(
        np.array_equal(first.assignment, second.assignment)
        and np.array_equal(first.centroids, second.centroids)
        and first.initial_centroid_hashes == second.initial_centroid_hashes
        and first_index_hashes == second_index_hashes
    )
    if not repeat_identity:
        raise IntegrityError("Real-matrix repeated partition construction changed")
    query = normalise(vectors[:180].mean(axis=0))
    cells = select_cells(query, first.centroids, np.zeros(32, dtype=np.float32), False)
    pool = np.concatenate([first.shard_item_indices[int(cell)] for cell in cells])
    history = frozenset(map(int, pool[pool >= 0][:300]))
    result = retrieve(query, history, first, movie_ids, np.zeros(32, dtype=np.float32), "balanced_geometric_ivf")
    if len(result[0]) != 100 or result[3]["shard_slot_dots"] != 1336:
        raise IntegrityError("Real-matrix adversarial-history qualification failed")

    user_ids = tuple(range(1, 513))
    A: dict[int, tuple[Interaction, ...]] = {}
    test_histories: dict[int, tuple[Interaction, ...]] = {}
    for user_id in user_ids:
        a_events = tuple(
            Interaction(user_id, item, int(movie_ids[item]), 5.0 if item < 120 else 2.0, item + 1, item)
            for item in range(180)
        )
        A[user_id] = a_events
        test_histories[user_id] = tuple(
            Interaction(user_id, item, int(movie_ids[item]), 5.0, item + 1, item)
            for item in range(300)
        )
    states: dict[int, dict[int, Mapping[str, Any]]] = {}
    for seed in SEEDS:
        states[seed] = {5: {name: value.detach().cpu().clone() for name, value in make_offset_model(seed).state_dict().items()}}
    latency_raw, latency = measure_latency(user_ids, A, test_histories, vectors, first, movie_ids, states, 5)
    if not latency["passed"]:
        raise IntegrityError(f"Outcome-free machine latency qualification failed: {latency}")
    record = {
        "schema": "pivot-real-embedding-qualification-v1",
        "qualified_utc": utc_now(),
        "semantic_path": str(semantic_path.resolve()),
        "semantic_npy_sha256": SEMANTIC_SHA256,
        "config_path": str(config_path.resolve()),
        "config_sha256": expected_config_sha256,
        "runner_source_sha256": sha256_file(Path(__file__).resolve()),
        "assignment_sha256": sha256_bytes(np.ascontiguousarray(first.assignment, dtype="<i2").tobytes()),
        "centroids_sha256": sha256_bytes(np.ascontiguousarray(first.centroids, dtype="<f4").tobytes()),
        "index_sha256": first_index_hashes,
        "repeat_index_sha256": second_index_hashes,
        "real_counts": [int(np.sum(first.assignment == cell)) for cell in range(32)],
        "physical_slots": [int(index.ntotal) for index in first.indexes],
        "repeat_construction_identity": repeat_identity,
        "adversarial_history_count": 300,
        "candidate_count": 100,
        "work": dict(result[3]),
        "latency": latency,
        "latency_raw_sha256": sha256_bytes(npz_bytes(**latency_raw)),
        "archive_opened": False,
        "user_outcomes_accessed": False,
        "passed": True,
    }
    publish_json(output_path, record)
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PIVOT one-shot PoC producer")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-config", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--qualify", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--expect-config-sha256")
    parser.add_argument("--expect-source-sha256")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--cycle5-cohort", type=Path)
    parser.add_argument("--semantic-vectors", type=Path)
    parser.add_argument("--qualification-output", type=Path)
    parser.add_argument("--run-id")
    return parser


def _require(arguments: argparse.Namespace, *names: str) -> None:
    missing = [name for name in names if getattr(arguments, name) is None]
    if missing:
        raise IntegrityError(f"Mode is missing required arguments: {missing}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate_config:
        _require(args, "config", "expect_config_sha256")
        if any(getattr(args, name) is not None for name in ("expect_source_sha256", "protocol", "output_dir", "archive", "cycle5_cohort", "semantic_vectors", "qualification_output", "run_id")):
            raise IntegrityError("Config validation refuses archive/output/run arguments")
        report = {**validate_locked_config(), "external_config": load_external_config(args.config, args.expect_config_sha256)["protocol_name"]}
    elif args.self_test:
        _require(args, "config", "expect_config_sha256")
        if any(getattr(args, name) is not None for name in ("expect_source_sha256", "protocol", "output_dir", "archive", "cycle5_cohort", "semantic_vectors", "qualification_output", "run_id")):
            raise IntegrityError("Self-test refuses archive/output/run arguments")
        load_external_config(args.config, args.expect_config_sha256)
        report = synthetic_self_test()
    elif args.qualify:
        _require(args, "config", "expect_config_sha256", "semantic_vectors", "qualification_output")
        if any(getattr(args, name) is not None for name in ("expect_source_sha256", "protocol", "output_dir", "archive", "cycle5_cohort", "run_id")):
            raise IntegrityError("Qualification refuses archive/outcome/run arguments")
        report = qualify_real_embeddings(args.semantic_vectors, args.qualification_output, args.config, args.expect_config_sha256)
    else:
        _require(args, "config", "expect_config_sha256", "expect_source_sha256", "protocol", "output_dir", "archive", "cycle5_cohort", "semantic_vectors", "run_id")
        if args.qualification_output is not None:
            raise IntegrityError("Authorized run refuses qualification output")
        configure_numerical_threads(require_locked_environment=True)
        report = execute_authorized(
            args.config, args.expect_config_sha256, args.expect_source_sha256, args.protocol, args.output_dir,
            args.archive, args.cycle5_cohort, args.semantic_vectors, args.run_id,
        )
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
