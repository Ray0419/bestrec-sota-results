"""Prospectively locked CPU PoC runner for CABLE-PREF (cycle 5).

The default CLI is outcome-blind: ``--validate-config`` and ``--self-test``
never open, list, extract, or parse MovieLens.  A real run requires the four
explicit launcher arguments (config, protocol, output directory, and the
SHA-locked local archive).  The runner implements the source-side producer
contract; a separately source-bound launcher/verifier must own the
authoritative G1--G9 verdict.

Ratings are floats because MovieLens 10M contains half-star values.  Movie
metadata is decoded as strict UTF-8.  Current-block item identities and ratings
are loaded only after that block's complete target-blind manifests are durable.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime as dt
import gc
import hashlib
import heapq
import io
import inspect
import importlib.metadata as importlib_metadata
import json
import math
import os
import platform
from pathlib import Path, PurePosixPath
import random
import shutil
import sys
import tempfile
import threading
import time
import traceback
from typing import Any, Iterable, Iterator, Mapping, Sequence
import zipfile

import numpy as np


ARCHIVE_BYTES = 65_566_137
ARCHIVE_SHA256 = "813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862"
ARCHIVE_MD5 = "ce571fd55effeba0271552578f2648bd"
EXPECTED_EXTERNAL_CONFIG_SHA256 = (
    "81b2bdc2645ee11e26f1e95b2c68cf4fb9412b3da7b6363bb7bc7d0e5c658cf4"
)
ARCHIVE_URL = "https://files.grouplens.org/datasets/movielens/ml-10m.zip"
QUESTION_RELATIVE = Path("literature") / "research-question-cycle5.md"

METHODS = (
    "bpr",
    "raw_hybrid",
    "order_only",
    "admission_only",
    "cable_pref",
    "shuffled_direction",
    "uib_boundary",
    "wrong_boundary",
)
HYBRID_METHODS = METHODS[1:]
TRAINED_METHODS = METHODS[2:]
SEEDS = (20260835, 20260836, 20260837)
ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)
METRICS = (
    "conditional_admission_at_200",
    "net_new_preferred_support",
    "net_admission_advantage",
    "spce_at_10",
    "preferred_exposure_at_10",
    "ndcg_at_10",
    "recall_at_10",
    "low_rating_intrusion_at_10",
)

RAW_VALIDATION_FIELDS = (
    "schema", "protocol_fingerprint_sha256", "execution_fingerprint_sha256",
    "methods", "seeds", "metrics", "alphas", "user_ids", "catalog_movie_ids",
    "per_user_metrics", "selected_alpha_index", "selected_alpha",
    "stronger_relevance_method", "power_comparison_names",
    "power_detection_fractions", "power_passed", "V_manifest_files",
    "V_manifest_sha256", "semantic_matrix_file", "semantic_matrix_sha256",
    "semantic_index_file", "semantic_index_sha256", "bpr_item_matrix_file",
    "bpr_item_matrix_sha256", "bpr_index_file", "bpr_index_sha256",
    "collaborative_mask_file", "collaborative_mask_sha256",
    "V_event_items", "V_event_movie_ids", "V_event_ratings",
    "V_event_timestamps", "V_event_ordinals", "V_event_counts",
    "V_pair_preferred", "V_pair_rejected", "V_pair_low_movie_ids",
    "V_pair_high_movie_ids", "V_pair_counts", "V_pair_identity_sha256",
    "R_event_items", "R_event_movie_ids", "R_event_ratings",
    "R_event_timestamps", "R_event_ordinals", "R_event_counts",
    "R_pair_preferred", "R_pair_rejected", "R_pair_low_movie_ids",
    "R_pair_high_movie_ids", "R_pair_counts", "R_pair_identity_sha256",
    "R_selected_pairs", "R_selected_pair_users", "V_fixed_pairs",
    "V_pair_users", "V_unique_bpr_missed_preferred_endpoints",
    "V_missed_endpoint_users", "V_admission_changed_count_by_seed",
    "V_admission_total_by_seed", "V_spce_changed_count_by_seed",
    "V_spce_total_by_seed", "training_methods", "training_optimizer_steps",
    "training_pair_presentations", "training_admission_presentations",
    "adapter_initial_memory_sha256", "adapter_final_memory_sha256",
    "V_manifest_published_utc", "V_binary_relevance_opened_utc",
    "choices_frozen_utc", "V_exact_preference_opened_utc",
    "target_blind_before_binary_relevance", "choices_before_exact_preferences",
)

RAW_TEST_FIELDS = (
    "schema", "protocol_fingerprint_sha256", "execution_fingerprint_sha256",
    "methods", "seeds", "metrics", "alphas", "user_ids", "catalog_movie_ids",
    "per_user_metrics", "selected_alpha_index", "selected_alpha",
    "stronger_relevance_method", "T_manifest_files", "T_manifest_sha256",
    "semantic_matrix_file", "semantic_matrix_sha256", "semantic_index_file",
    "semantic_index_sha256", "bpr_item_matrix_file", "bpr_item_matrix_sha256",
    "bpr_index_file", "bpr_index_sha256", "collaborative_mask_file",
    "collaborative_mask_sha256", "T_event_items", "T_event_movie_ids",
    "T_event_ratings", "T_event_timestamps", "T_event_ordinals",
    "T_event_counts", "T_pair_preferred", "T_pair_rejected",
    "T_pair_low_movie_ids", "T_pair_high_movie_ids", "T_pair_counts",
    "T_pair_identity_sha256", "T_fixed_pairs", "T_pair_users",
    "T_unique_bpr_missed_preferred_endpoints", "T_missed_endpoint_users",
    "T_admission_changed_count_by_seed", "T_admission_total_by_seed",
    "T_spce_changed_count_by_seed", "T_spce_total_by_seed",
    "action_checked", "action_violations", "action_tie_boundaries",
    "action_passed", "g1_invariant_names", "g1_invariant_values",
    "gate_names", "gate_values", "T_manifest_published_utc",
    "T_opened_utc", "test_opened",
)

RAW_LATENCY_FIELDS = (
    "schema", "protocol_fingerprint_sha256", "execution_fingerprint_sha256",
    "seeds", "methods", "user_ids", "durations_ms", "per_request_median_ms",
    "p95_ms", "p99_ms", "p95_ratio_by_seed", "worst_cable_p95_ms",
    "worst_p95_ratio", "passed",
)

LOCKED_CONFIG: Mapping[str, Any] = {
    "protocol": "cable-pref-ml10m-poc-v1",
    "archive": {
        "bytes": ARCHIVE_BYTES,
        "sha256": ARCHIVE_SHA256,
        "md5": ARCHIVE_MD5,
        "allowed_inputs": ["ratings.dat", "movies.dat"],
        "forbidden_inputs": ["tags.dat"],
    },
    "dataset": {
        "split_fractions": [0.60, 0.20, 0.10, 0.10],
        "minimum_total_events": 80,
        "minimum_timestamp_groups": 4,
        "minimum_A_events": 20,
        "minimum_distinct_positive_A_items": 5,
        "positive_rating_min": 4.0,
        "dislike_rating_max": 2.0,
        "minimum_longest_prefix_unseen": 700,
        "cohort_size": 2000,
        "cohort_hash": "20260835:{user_id}",
        "pair_rating_gap": 2.0,
        "maximum_pairs_per_user": 100,
        "maximum_R_pairs_per_user": 32,
        "maximum_R_pairs_global": 30_000,
        "pair_hash": "20263503:{user_id}:{low_item_id}:{high_item_id}",
    },
    "embedding": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
        "batch_size": 128,
        "template": "{title} [SEP] {genres}",
        "local_files_only": True,
    },
    "bpr": {
        "dimension": 64,
        "epochs": 8,
        "batch_size": 2048,
        "learning_rate": 0.025,
        "weight_decay": 1.0e-4,
        "maximum_pairs": 200_000,
        "positive_rating_min": 4.0,
        "minimum_item_positive_support": 5,
        "seed": 20260835,
        "prefix_update_weight": 0.5,
    },
    "adapter": {
        "hidden_dimension": 32,
        "displacement_bound": 0.25,
        "epochs": 12,
        "batch_users": 128,
        "learning_rate": 0.003,
        "weight_decay": 1.0e-4,
        "gradient_clip": 1.0,
        "beta": 5.0,
        "admission_margin": 0.02,
        "order_margin": 0.10,
        "admission_weight": 0.5,
        "order_weight": 0.5,
    },
    "retrieval": {
        "kind": "IndexFlatIP",
        "bpr_exact": 200,
        "semantic_exact": 200,
        "union_exact": 400,
        "manifest_query_batch_size": 64,
        "semantic_minimum_complement": 500,
        "tie_break": "score_desc_then_numeric_movie_id_asc",
        "faiss_threads": 1,
    },
    "validation": {
        "alpha_grid": list(ALPHAS),
        "selection": "raw_hybrid_user_macro_ndcg_then_recall_then_higher_alpha",
    },
    "bootstrap": {"draws": 10_000, "alpha": 0.05, "seed": 20263504},
    "power": {
        "experiments": 1000,
        "minimum_pass_probability": 0.80,
        "admission_delta": 0.020,
        "spce_delta": 0.005,
        "seed": 20263508,
    },
    "latency": {
        "requests": 512,
        "request_hash": "20263509:latency:{user_id}",
        "warmups": 32,
        "repetitions": 7,
        "order_seed": 20263506,
        "maximum_p95_ms": 10.0,
        "maximum_p95_ratio": 1.25,
    },
    "support": {
        "minimum_R_pairs": 20_000,
        "minimum_R_pair_users": 1000,
        "minimum_T_pairs": 5000,
        "minimum_T_missed_preferred": 5000,
        "minimum_T_pair_users": 1000,
        "minimum_T_missed_users": 1000,
        "minimum_admission_change_fraction": 0.05,
        "minimum_spce_change_fraction": 0.02,
    },
    "gates": {
        "admission_raw_gain": 0.020,
        "admission_order_gain": 0.010,
        "net_support_raw_gain": 0.010,
        "spce_gain": 0.005,
        "ndcg_point_floor": -0.0002,
        "ndcg_lower_strict": -0.001,
        "recall_lower_strict": -0.002,
        "intrusion_upper": 0.002,
        "minimum_stable_seeds": 2,
        "per_seed_ndcg_floor": -0.001,
    },
}


class IntegrityError(RuntimeError):
    """Fail-closed protocol or artifact-integrity violation."""


@dataclasses.dataclass(frozen=True)
class Movie:
    movie_id: int
    title: str
    genres: str


@dataclasses.dataclass(frozen=True)
class SkeletonLine:
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
class StageLayout:
    user_id: int
    counts: tuple[int, int, int, int]
    minimum_timestamps: tuple[int, int, int, int]
    maximum_timestamps: tuple[int, int, int, int]
    structural_hash: str


@dataclasses.dataclass(frozen=True)
class UserBlocks:
    user_id: int
    A: tuple[Interaction, ...]
    R: tuple[Interaction, ...]
    V: tuple[Interaction, ...]
    T: tuple[Interaction, ...]


@dataclasses.dataclass(frozen=True)
class BPRArtifacts:
    user_ids: tuple[int, ...]
    user_to_row: Mapping[int, int]
    user_vectors: np.ndarray
    item_vectors: np.ndarray
    collaborative_mask: np.ndarray
    training_trace: tuple[float, ...]


@dataclasses.dataclass(frozen=True)
class QueryDescriptor:
    raw_query: np.ndarray
    liked_centroid: np.ndarray
    dislike_centroid: np.ndarray
    history_feature: float


@dataclasses.dataclass(frozen=True)
class PairRow:
    user_id: int
    preferred: int
    rejected: int
    low_movie_id: int
    high_movie_id: int


@dataclasses.dataclass(frozen=True)
class RetrievalRow:
    bpr_items: tuple[int, ...]
    semantic_items: tuple[int, ...]
    union: tuple[int, ...]
    raw_bpr_scores: np.ndarray
    raw_semantic_scores: np.ndarray
    ranking: tuple[int, ...]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def publish_bytes_no_overwrite(path: Path, payload: bytes) -> None:
    """Crash-atomic same-directory publication with no-overwrite semantics."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise
        with contextlib.suppress(OSError):
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def publish_json(path: Path, value: Any) -> None:
    publish_bytes_no_overwrite(path, canonical_json_bytes(value))


def npz_bytes(**arrays: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def publish_npz(path: Path, **arrays: np.ndarray) -> str:
    publish_bytes_no_overwrite(path, npz_bytes(**arrays))
    return sha256_file(path)


def hash_key(template: str, **values: int) -> tuple[int, str]:
    text = template.format(**values)
    digest = hashlib.sha256(text.encode("ascii")).hexdigest()
    return int(digest, 16), digest


def normalise(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if not math.isfinite(norm) or norm <= 1.0e-12:
        raise IntegrityError("Cannot normalize a zero or nonfinite vector")
    result = np.ascontiguousarray(value / norm, dtype=np.float32)
    if not np.all(np.isfinite(result)):
        raise IntegrityError("Normalized vector is nonfinite")
    return result


def validate_locked_config() -> Mapping[str, Any]:
    if tuple(METHODS) != (
        "bpr", "raw_hybrid", "order_only", "admission_only", "cable_pref",
        "shuffled_direction", "uib_boundary", "wrong_boundary",
    ):
        raise ValueError("Registered control names changed")
    if tuple(SEEDS) != (20260835, 20260836, 20260837):
        raise ValueError("Registered seeds changed")
    if tuple(map(float, LOCKED_CONFIG["validation"]["alpha_grid"])) != ALPHAS:
        raise ValueError("Shared alpha grid changed")
    retrieval = LOCKED_CONFIG["retrieval"]
    if (retrieval["kind"], retrieval["bpr_exact"], retrieval["semantic_exact"], retrieval["union_exact"]) != (
        "IndexFlatIP", 200, 200, 400
    ):
        raise ValueError("Exact 200+200 retrieval contract changed")
    if retrieval["manifest_query_batch_size"] != 64:
        raise ValueError("Manifest query batch size changed")
    adapter = LOCKED_CONFIG["adapter"]
    expected = (32, 0.25, 12, 5.0, 0.02, 0.10, 0.5, 0.5)
    actual = (
        adapter["hidden_dimension"], adapter["displacement_bound"], adapter["epochs"],
        adapter["beta"], adapter["admission_margin"], adapter["order_margin"],
        adapter["admission_weight"], adapter["order_weight"],
    )
    if actual != expected:
        raise ValueError("CABLE loss/adapter constants changed")
    if LOCKED_CONFIG["bpr"]["dimension"] != 64:
        raise ValueError("BPR dimension changed")
    if LOCKED_CONFIG["archive"] != {
        "bytes": ARCHIVE_BYTES,
        "sha256": ARCHIVE_SHA256,
        "md5": ARCHIVE_MD5,
        "allowed_inputs": ["ratings.dat", "movies.dat"],
        "forbidden_inputs": ["tags.dat"],
    }:
        raise ValueError("Authenticated archive binding changed")
    return {
        "schema": "cable-pref-config-validation-v1",
        "config_sha256": sha256_bytes(canonical_json_bytes(LOCKED_CONFIG)),
        "methods": list(METHODS),
        "seeds": list(SEEDS),
        "archive_opened": False,
        "target_outcomes_accessed": False,
    }


def load_and_validate_external_config(path: Path) -> Mapping[str, Any]:
    actual_sha256 = sha256_file(path)
    if actual_sha256 != EXPECTED_EXTERNAL_CONFIG_SHA256:
        raise IntegrityError(
            "External configuration SHA-256 differs from the prospectively "
            f"frozen file: {actual_sha256}"
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrityError(f"Cannot load locked CABLE configuration: {path}") from exc
    if not isinstance(value, Mapping):
        raise IntegrityError("CABLE configuration root must be a mapping")
    checks = {
        "protocol_name": value.get("protocol_name") == "cable-pref-ml10m-poc-v1-preregistered",
        "seeds": value.get("optimization_seeds") == list(SEEDS),
        "archive_size": value.get("dataset", {}).get("expected_archive_size_bytes") == ARCHIVE_BYTES,
        "archive_sha": value.get("dataset", {}).get("expected_archive_sha256") == ARCHIVE_SHA256,
        "archive_md5": value.get("dataset", {}).get("expected_official_sidecar_md5") == ARCHIVE_MD5,
        "methods": value.get("controls", {}).get("registered_methods_in_fixed_order") == list(METHODS),
        "bpr_dimension": value.get("bpr", {}).get("embedding_dimension") == 64,
        "bpr_epochs": value.get("bpr", {}).get("epochs") == 8,
        "bpr_maximum": value.get("bpr", {}).get("maximum_training_examples_per_epoch") == 200_000,
        "bpr_seed": value.get("bpr", {}).get("training_seed") == 20260835,
        "adapter_input": value.get("adapter", {}).get("input_dimension") == 1153,
        "adapter_hidden": value.get("adapter", {}).get("hidden_dimension") == 32,
        "adapter_output": value.get("adapter", {}).get("output_dimension") == 385,
        "displacement": value.get("adapter", {}).get("query_displacement_bound") == 0.25,
        "alignment_epochs": value.get("alignment", {}).get("epochs") == 12,
        "alignment_beta": value.get("alignment", {}).get("beta") == 5.0,
        "admission_margin": value.get("alignment", {}).get("admission_margin") == 0.02,
        "order_margin": value.get("alignment", {}).get("order_margin") == 0.1,
        "user_group": value.get("alignment", {}).get("user_group_size") == 128,
        "retrieval_backend": value.get("retrieval", {}).get("outcome_backend")
        == "faiss_full_result_row_then_request_mask_and_stable_rerank",
        "candidate_counts": (
            value.get("retrieval", {}).get("collaborative_candidates_exact"),
            value.get("retrieval", {}).get("semantic_candidates_exact"),
            value.get("retrieval", {}).get("union_candidates_exact"),
        )
        == (200, 200, 400),
        "manifest_query_batch_size": value.get("retrieval", {}).get(
            "manifest_query_batch_size"
        )
        == 64,
        "alpha_grid": value.get("ranking", {}).get("alpha_validation_grid") == list(ALPHAS),
        "latency_hash": value.get("latency", {}).get("request_hash_format")
        == "20263509:latency:{user_id}",
        "latency_contract": (
            value.get("latency", {}).get("measured_requests_exact"),
            value.get("latency", {}).get("warmups"),
            value.get("latency", {}).get("repetitions"),
            value.get("latency", {}).get("maximum_p95_ms"),
            value.get("latency", {}).get("maximum_p95_ratio"),
        )
        == (512, 32, 7, 10.0, 1.25),
        "stage_authorized_loading": (
            value.get("dataset", {}).get("loading", {}).get("strategy")
            == "one_structural_pass_plus_stage_authorized_rescans"
            and value.get("dataset", {}).get("loading", {}).get("stage_rescan_policy")
            == "parse_selected_users_current_stage_only_and_verify_pass_1_layout"
        ),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise IntegrityError(f"External configuration differs from runner constants: {failed}")
    validate_locked_config()
    return value


THREAD_ENVIRONMENT_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)


def fixed_execution_environment() -> Mapping[str, str]:
    result = {name: "1" for name in THREAD_ENVIRONMENT_VARIABLES}
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


def validate_execution_environment() -> Mapping[str, str]:
    expected = fixed_execution_environment()
    actual = {name: os.environ.get(name, "") for name in expected}
    if actual != expected:
        differences = sorted(name for name in expected if actual[name] != expected[name])
        raise IntegrityError(f"Runner execution environment differs from launcher: {differences}")
    return actual


def verify_archive_binding(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise IntegrityError("Authorized MovieLens archive path is not a file")
    size = path.stat().st_size
    if size != ARCHIVE_BYTES:
        raise IntegrityError(f"MovieLens archive size mismatch: {size}")
    sha = sha256_file(path)
    md5 = md5_file(path)
    if sha != ARCHIVE_SHA256 or md5 != ARCHIVE_MD5:
        raise IntegrityError("MovieLens 10M archive digest mismatch")
    return {"bytes": size, "sha256": sha, "md5": md5}


def _safe_member_name(name: str) -> PurePosixPath:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise IntegrityError(f"Unsafe ZIP member path: {name!r}")
    return pure


def safe_extract_allowed_inputs(archive: Path, destination: Path, authorized: bool) -> Mapping[str, Path]:
    if not authorized:
        raise IntegrityError("Archive listing/extraction requires explicit launcher authorization")
    if destination.exists():
        raise IntegrityError("Extraction destination already exists")
    destination.mkdir(parents=True, exist_ok=False)
    selected: dict[str, zipfile.ZipInfo] = {}
    exact_members = {
        "ratings.dat": "ml-10M100K/ratings.dat",
        "movies.dat": "ml-10M100K/movies.dat",
    }
    with zipfile.ZipFile(archive, "r") as handle:
        for member in handle.infolist():
            pure = _safe_member_name(member.filename)
            unix_mode = (member.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                raise IntegrityError("ZIP symlinks are forbidden")
            if member.flag_bits & 0x1:
                raise IntegrityError("Encrypted ZIP members are forbidden")
            basename = pure.name
            if basename in {"ratings.dat", "movies.dat"}:
                if pure.as_posix() != exact_members[basename]:
                    raise IntegrityError(f"Required-member basename alias is forbidden: {member.filename}")
                if basename in selected or member.is_dir():
                    raise IntegrityError(f"Archive has ambiguous {basename}")
                selected[basename] = member
        if set(selected) != {"ratings.dat", "movies.dat"}:
            raise IntegrityError("Archive lacks the exact allowed MovieLens inputs")
        output: dict[str, Path] = {}
        for basename in ("ratings.dat", "movies.dat"):
            target = destination / basename
            with handle.open(selected[basename], "r") as source, target.open("xb") as sink:
                shutil.copyfileobj(source, sink, length=1 << 20)
                sink.flush()
                os.fsync(sink.fileno())
            output[basename] = target
    return output


def parse_movie_line(line: str) -> Movie:
    fields = line.rstrip("\r\n").split("::", 2)
    if len(fields) != 3:
        raise IntegrityError("Malformed UTF-8 movies.dat row")
    movie_id = int(fields[0])
    if movie_id <= 0 or not fields[1] or not fields[2]:
        raise IntegrityError("Invalid movies.dat field")
    return Movie(movie_id, fields[1], fields[2])


def load_movies(path: Path) -> tuple[tuple[Movie, ...], Mapping[int, int]]:
    movies: list[Movie] = []
    seen: set[int] = set()
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for line in handle:
            movie = parse_movie_line(line)
            if movie.movie_id in seen:
                raise IntegrityError("movies.dat contains a duplicate movie ID")
            seen.add(movie.movie_id)
            movies.append(movie)
    movies.sort(key=lambda movie: movie.movie_id)
    if len(movies) < 700:
        raise IntegrityError("Semantic catalog is too small")
    return tuple(movies), {movie.movie_id: index for index, movie in enumerate(movies)}


def parse_skeleton_line(line: str, ordinal: int) -> SkeletonLine:
    stripped = line.rstrip("\r\n")
    if stripped.count("::") != 3:
        raise IntegrityError("Malformed ratings.dat row")
    first_separator = stripped.find("::")
    last_separator = stripped.rfind("::")
    user_id = int(stripped[:first_separator])
    timestamp = int(stripped[last_separator + 2 :])
    if user_id <= 0 or timestamp < 0:
        raise IntegrityError("Invalid ratings.dat user/timestamp")
    return SkeletonLine(user_id, timestamp, ordinal)


def parse_interaction(
    row: SkeletonLine,
    movie_to_index: Mapping[int, int],
    raw_line: str,
) -> Interaction:
    fields = raw_line.rstrip("\r\n").split("::")
    if len(fields) != 4:
        raise IntegrityError("Malformed ratings.dat row")
    user_id, movie_id, timestamp = int(fields[0]), int(fields[1]), int(fields[3])
    rating = float(fields[2])
    if user_id != row.user_id or timestamp != row.timestamp:
        raise IntegrityError("Skeleton/full rating parse disagreement")
    if movie_id not in movie_to_index:
        raise IntegrityError("ratings.dat refers to missing movie metadata")
    if not math.isfinite(rating) or rating < 0.5 or rating > 5.0 or not math.isclose(rating * 2.0, round(rating * 2.0)):
        raise IntegrityError("MovieLens 10M rating is not a valid half-star value")
    return Interaction(user_id, movie_to_index[movie_id], movie_id, rating, timestamp, row.ordinal)


def _nearest_boundary(cumulative: Sequence[int], target: float, low: int, high: int) -> int:
    if low > high:
        raise IntegrityError("No feasible timestamp-group split boundary")
    candidates = range(low, high + 1)
    return min(candidates, key=lambda index: (abs(cumulative[index - 1] - target), index))


def split_skeleton_rows(rows: Sequence[SkeletonLine]) -> tuple[tuple[SkeletonLine, ...], ...]:
    if not rows:
        raise IntegrityError("Cannot split an empty user")
    ordered = sorted(rows, key=lambda row: (row.timestamp, row.ordinal))
    groups: list[list[SkeletonLine]] = []
    for row in ordered:
        if not groups or groups[-1][0].timestamp != row.timestamp:
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
    blocks = (
        tuple(item for group in groups[:a_cut] for item in group),
        tuple(item for group in groups[a_cut:r_cut] for item in group),
        tuple(item for group in groups[r_cut:v_cut] for item in group),
        tuple(item for group in groups[v_cut:] for item in group),
    )
    if any(not block for block in blocks):
        raise IntegrityError("Temporal splitter produced an empty block")
    maximums = [max(row.timestamp for row in block) for block in blocks]
    minimums = [min(row.timestamp for row in block) for block in blocks]
    if not all(maximums[index] < minimums[index + 1] for index in range(3)):
        raise IntegrityError("Timestamp groups crossed a temporal boundary")
    return blocks


def _layout_from_blocks(user_id: int, blocks: Sequence[Sequence[SkeletonLine]]) -> StageLayout:
    counts = tuple(len(block) for block in blocks)
    minimums = tuple(min(row.timestamp for row in block) for block in blocks)
    maximums = tuple(max(row.timestamp for row in block) for block in blocks)
    structural = {
        "user_id": user_id,
        "counts": counts,
        "minimum_timestamps": minimums,
        "maximum_timestamps": maximums,
    }
    return StageLayout(user_id, counts, minimums, maximums, sha256_bytes(canonical_json_bytes(structural)))


def _eligible_user(
    blocks: Sequence[Sequence[SkeletonLine]], movie_to_index: Mapping[int, int]
) -> tuple[bool, StageLayout | None]:
    """Structural eligibility only; A values are joined in an authorized rescan."""
    dataset = LOCKED_CONFIG["dataset"]
    if len(blocks) != 4 or any(not block for block in blocks):
        return False, None
    total = sum(map(len, blocks))
    timestamps = {row.timestamp for block in blocks for row in block}
    if total < int(dataset["minimum_total_events"]) or len(timestamps) < int(dataset["minimum_timestamp_groups"]):
        return False, None
    if len(blocks[0]) < int(dataset["minimum_A_events"]):
        return False, None
    # Official ML-10M has one user/movie row.  Capacity is conservatively
    # checked from prefix event count only, without reading later identities.
    longest_prefix_count = len(blocks[0]) + len(blocks[1]) + len(blocks[2])
    if len(movie_to_index) - longest_prefix_count < int(dataset["minimum_longest_prefix_unseen"]):
        return False, None
    return True, _layout_from_blocks(blocks[0][0].user_id, blocks)


def select_cohort_streaming(
    ratings_path: Path, movie_to_index: Mapping[int, int]
) -> tuple[
    tuple[int, ...],
    Mapping[int, StageLayout],
    int,
    Mapping[int, tuple[Interaction, ...]],
]:
    """Structural pass followed by an A-only eligibility/value rescan."""
    limit = int(LOCKED_CONFIG["dataset"]["cohort_size"])
    template = str(LOCKED_CONFIG["dataset"]["cohort_hash"])
    structural_layouts: dict[int, StageLayout] = {}
    completed_users: set[int] = set()

    def consider_structure(user_rows: list[SkeletonLine]) -> None:
        if not user_rows:
            return
        blocks = split_skeleton_rows(user_rows)
        eligible, layout = _eligible_user(blocks, movie_to_index)
        if eligible and layout is not None:
            structural_layouts[layout.user_id] = layout

    current_user: int | None = None
    current_rows: list[SkeletonLine] = []
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton_line(line, ordinal)
            if current_user is None:
                current_user = row.user_id
            if row.user_id != current_user:
                if row.user_id in completed_users:
                    raise IntegrityError("ratings.dat is not grouped by user ID")
                consider_structure(current_rows)
                completed_users.add(current_user)
                current_user, current_rows = row.user_id, []
            current_rows.append(row)
    consider_structure(current_rows)
    if current_user is not None:
        completed_users.add(current_user)

    # A-authorized rescan: parse only rows whose timestamps lie in the frozen A
    # block.  Keep A values only for the current user and the hash-reservoir.
    heap: list[
        tuple[int, int, int, StageLayout, tuple[Interaction, ...]]
    ] = []
    eligible_count = 0

    def consider_A(
        user_id: int | None,
        structural_rows: list[SkeletonLine],
        a_events: list[Interaction],
    ) -> None:
        nonlocal eligible_count
        if user_id is None or user_id not in structural_layouts:
            return
        blocks = split_skeleton_rows(structural_rows)
        layout = _layout_from_blocks(user_id, blocks)
        if layout != structural_layouts[user_id]:
            raise IntegrityError("A rescan disagrees with frozen structural layout")
        ordered_A = tuple(sorted(a_events, key=lambda event: (event.timestamp, event.ordinal)))
        if len(ordered_A) != layout.counts[0]:
            raise IntegrityError("A rescan event count differs from frozen layout")
        if len({event.item_index for event in ordered_A}) != len(ordered_A):
            raise IntegrityError("A contains repeated user/movie interactions")
        positives = {
            event.item_index
            for event in ordered_A
            if event.rating >= float(LOCKED_CONFIG["dataset"]["positive_rating_min"])
        }
        if len(positives) < int(LOCKED_CONFIG["dataset"]["minimum_distinct_positive_A_items"]):
            return
        eligible_count += 1
        key, _digest = hash_key(template, user_id=user_id)
        entry = (-key, -user_id, user_id, layout, ordered_A)
        if len(heap) < limit:
            heapq.heappush(heap, entry)
        else:
            current_largest = (-heap[0][0], -heap[0][1])
            if (key, user_id) < current_largest:
                heapq.heapreplace(heap, entry)

    current_user = None
    current_rows = []
    current_A: list[Interaction] = []
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton_line(line, ordinal)
            if current_user is None:
                current_user = row.user_id
            if row.user_id != current_user:
                consider_A(current_user, current_rows, current_A)
                current_user, current_rows, current_A = row.user_id, [], []
            layout = structural_layouts.get(row.user_id)
            if layout is not None:
                current_rows.append(row)
                if layout.minimum_timestamps[0] <= row.timestamp <= layout.maximum_timestamps[0]:
                    current_A.append(parse_interaction(row, movie_to_index, line))
    consider_A(current_user, current_rows, current_A)
    if len(heap) != limit:
        raise IntegrityError(f"Only {len(heap)} fully eligible users; expected {limit}")
    records = [(entry[2], entry[3], entry[4]) for entry in heap]
    records.sort(key=lambda value: (hash_key(template, user_id=value[0])[0], value[0]))
    user_ids = tuple(record[0] for record in records)
    layouts = {record[0]: record[1] for record in records}
    A = {record[0]: record[2] for record in records}
    if len(user_ids) != len(set(user_ids)) or len(layouts) != limit:
        raise IntegrityError("Cohort selection contains duplicate users")
    return user_ids, layouts, eligible_count, A


def load_selected_stage(
    ratings_path: Path,
    selected_users: frozenset[int],
    layouts: Mapping[int, StageLayout],
    movie_to_index: Mapping[int, int],
    stage: str,
    *,
    rating_view: str = "full",
) -> Mapping[int, tuple[Interaction, ...]]:
    """Rescan and parse item/rating fields only for one authorized stage."""
    stage_index = {"A": 0, "R": 1, "V": 2, "T": 3}.get(stage)
    if stage_index is None:
        raise ValueError(stage)
    result: dict[int, tuple[Interaction, ...]] = {}

    def consume(
        user_id: int | None,
        rows: list[SkeletonLine],
        parsed: list[Interaction],
    ) -> None:
        if user_id is None or user_id not in selected_users:
            return
        blocks = split_skeleton_rows(rows)
        layout = _layout_from_blocks(user_id, blocks)
        if layout != layouts[user_id]:
            raise IntegrityError("Stage rescan disagrees with locked temporal layout")
        parsed.sort(key=lambda event: (event.timestamp, event.ordinal))
        if len(parsed) != layout.counts[stage_index]:
            raise IntegrityError(f"Stage {stage} rescan count differs from frozen layout")
        if rating_view == "binary_relevance":
            positive_min = float(LOCKED_CONFIG["dataset"]["positive_rating_min"])
            if any(event.rating not in (0.0, positive_min) for event in parsed):
                raise IntegrityError("Binary relevance rescan retained an exact rating")
        elif rating_view != "full":
            raise ValueError(rating_view)
        events = tuple(parsed)
        if len({event.item_index for event in events}) != len(events):
            raise IntegrityError(f"{stage} contains repeated user/movie interactions")
        result[user_id] = events

    current_user: int | None = None
    current_rows: list[SkeletonLine] = []
    current_events: list[Interaction] = []
    with ratings_path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for ordinal, line in enumerate(handle):
            row = parse_skeleton_line(line, ordinal)
            if current_user is None:
                current_user = row.user_id
            if row.user_id != current_user:
                consume(current_user, current_rows, current_events)
                current_user, current_rows, current_events = row.user_id, [], []
            if row.user_id in selected_users:
                current_rows.append(row)
                layout = layouts[row.user_id]
                if (
                    layout.minimum_timestamps[stage_index]
                    <= row.timestamp
                    <= layout.maximum_timestamps[stage_index]
                ):
                    event = parse_interaction(row, movie_to_index, line)
                    if rating_view == "binary_relevance":
                        threshold = float(
                            LOCKED_CONFIG["dataset"]["positive_rating_min"]
                        )
                        event = dataclasses.replace(
                            event,
                            rating=threshold if event.rating >= threshold else 0.0,
                        )
                    current_events.append(event)
    consume(current_user, current_rows, current_events)
    if set(result) != set(selected_users):
        raise IntegrityError(f"Stage {stage} failed to load every selected user")
    return result


def stage_history(
    user_id: int,
    stage: str,
    A: Mapping[int, tuple[Interaction, ...]],
    R: Mapping[int, tuple[Interaction, ...]] | None = None,
    V: Mapping[int, tuple[Interaction, ...]] | None = None,
) -> tuple[Interaction, ...]:
    if stage == "R":
        history = A[user_id]
    elif stage == "V" and R is not None:
        history = (*A[user_id], *R[user_id])
    elif stage == "T" and R is not None and V is not None:
        history = (*A[user_id], *R[user_id], *V[user_id])
    else:
        raise IntegrityError(f"Unavailable or invalid stage history: {stage}")
    if len({event.item_index for event in history}) != len(history):
        raise IntegrityError("Available prefix repeats a user/movie row across stages")
    return tuple(history)


def assert_stage_items_disjoint(
    earlier: Mapping[int, Sequence[Interaction]],
    current: Mapping[int, Sequence[Interaction]],
    *,
    current_stage: str,
) -> None:
    """Fail as soon as an opened stage repeats an earlier prefix item."""
    if set(earlier) != set(current):
        raise IntegrityError(f"{current_stage} user set differs from its prefix")
    for user_id in earlier:
        earlier_items = {event.item_index for event in earlier[user_id]}
        current_items = {event.item_index for event in current[user_id]}
        if earlier_items & current_items:
            raise IntegrityError(
                f"{current_stage} repeats a user/movie row from an earlier stage"
            )


def encode_movies(movies: Sequence[Movie]) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("sentence-transformers is required for an authorized CABLE run") from exc
    config = LOCKED_CONFIG["embedding"]
    texts = [str(config["template"]).format(title=movie.title, genres=movie.genres) for movie in movies]
    model = SentenceTransformer(
        str(config["model"]),
        device="cpu",
        local_files_only=bool(config["local_files_only"]),
    )
    values = model.encode(
        texts,
        batch_size=int(config["batch_size"]),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    matrix = np.ascontiguousarray(values, dtype=np.float32)
    if matrix.shape != (len(movies), int(config["dimension"])):
        raise IntegrityError(f"Unexpected semantic matrix shape: {matrix.shape}")
    if not np.all(np.isfinite(matrix)) or not np.allclose(
        np.linalg.norm(matrix, axis=1), 1.0, rtol=0.0, atol=2.0e-5
    ):
        raise IntegrityError("Semantic vectors are nonfinite or not unit normalized")
    return matrix


def build_faiss_flat_ip(vectors: np.ndarray) -> Any:
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError("faiss-cpu is required for CABLE exact retrieval") from exc
    faiss.omp_set_num_threads(int(LOCKED_CONFIG["retrieval"]["faiss_threads"]))
    index = faiss.IndexFlatIP(int(vectors.shape[1]))
    index.add(np.ascontiguousarray(vectors, dtype=np.float32))
    if index.ntotal != vectors.shape[0]:
        raise IntegrityError("IndexFlatIP did not ingest the complete matrix")
    return index


def serialize_faiss(index: Any) -> bytes:
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError("faiss-cpu is required") from exc
    return np.asarray(faiss.serialize_index(index), dtype=np.uint8).tobytes()


def stable_order(
    scores: np.ndarray,
    eligible_mask: np.ndarray,
    movie_ids: np.ndarray,
    count: int,
) -> tuple[int, ...]:
    values = np.asarray(scores, dtype=np.float32).reshape(-1)
    mask = np.asarray(eligible_mask, dtype=np.bool_).reshape(-1)
    ids = np.asarray(movie_ids, dtype=np.int64).reshape(-1)
    if values.shape != mask.shape or values.shape != ids.shape:
        raise IntegrityError("Score/mask/movie-ID shapes differ")
    if np.any(~np.isfinite(values)):
        raise IntegrityError("Retrieval score contains NaN or infinity")
    eligible = np.flatnonzero(mask)
    if len(eligible) < count:
        raise IntegrityError(f"Only {len(eligible)} eligible items; required {count}")
    # np.lexsort uses the last key as primary: score descending, ID ascending.
    ordering = np.lexsort((ids[eligible], -values[eligible]))
    selected = eligible[ordering[:count]]
    return tuple(map(int, selected))


def exact_matrix_masked_topk(
    vectors: np.ndarray,
    query: np.ndarray,
    eligible_mask: np.ndarray,
    movie_ids: np.ndarray,
    count: int,
) -> tuple[tuple[int, ...], np.ndarray]:
    scores = np.asarray(
        np.ascontiguousarray(vectors, dtype=np.float32)
        @ np.ascontiguousarray(query.reshape(-1), dtype=np.float32),
        dtype=np.float32,
    )
    return stable_order(scores, eligible_mask, movie_ids, count), scores


def exact_faiss_masked_topk(
    index: Any,
    query: np.ndarray,
    eligible_mask: np.ndarray,
    movie_ids: np.ndarray,
    count: int,
) -> tuple[tuple[int, ...], np.ndarray]:
    """Complete IndexFlatIP row, then exact mask and canonical tie rerank."""
    total = int(index.ntotal)
    raw_scores, raw_indices = index.search(
        np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32), total
    )
    if raw_scores.shape != (1, total) or raw_indices.shape != (1, total):
        raise IntegrityError("IndexFlatIP did not return a complete row")
    labels = np.asarray(raw_indices[0], dtype=np.int64)
    if (
        np.any(labels < 0)
        or np.any(labels >= total)
        or len(np.unique(labels)) != total
    ):
        raise IntegrityError("Complete FAISS row has invalid, duplicate, or omitted labels")
    scores = np.full(total, np.nan, dtype=np.float32)
    scores[labels] = np.asarray(raw_scores[0], dtype=np.float32)
    selected = stable_order(scores, eligible_mask, movie_ids, count)
    return selected, scores


def exact_faiss_masked_topk_batch(
    index: Any,
    queries: np.ndarray,
    eligible_masks: np.ndarray,
    movie_ids: np.ndarray,
    count: int,
    *,
    oracle_vectors: np.ndarray | None = None,
) -> tuple[tuple[tuple[int, ...], ...], np.ndarray]:
    """Batched complete-row FAISS search with exact masks and oracle replay."""
    total = int(index.ntotal)
    query_matrix = np.ascontiguousarray(queries, dtype=np.float32)
    masks = np.ascontiguousarray(eligible_masks, dtype=np.bool_)
    if query_matrix.ndim != 2 or masks.shape != (len(query_matrix), total):
        raise IntegrityError("Batched query/mask shapes differ from the FAISS index")
    raw_scores, raw_indices = index.search(query_matrix, total)
    expected_shape = (len(query_matrix), total)
    if raw_scores.shape != expected_shape or raw_indices.shape != expected_shape:
        raise IntegrityError("Batched IndexFlatIP did not return complete rows")
    labels = np.asarray(raw_indices, dtype=np.int64)
    if np.any(labels < 0) or np.any(labels >= total):
        raise IntegrityError("Batched complete FAISS rows contain invalid labels")
    canonical_labels = np.arange(total, dtype=np.int64)
    if not np.all(np.sort(labels, axis=1) == canonical_labels[None, :]):
        raise IntegrityError("Batched complete FAISS rows duplicate or omit labels")
    scores = np.full(expected_shape, np.nan, dtype=np.float32)
    rows = np.arange(len(query_matrix), dtype=np.int64)[:, None]
    scores[rows, labels] = np.asarray(raw_scores, dtype=np.float32)
    selected = tuple(
        stable_order(scores[row], masks[row], movie_ids, count)
        for row in range(len(query_matrix))
    )
    if oracle_vectors is not None:
        vectors = np.ascontiguousarray(oracle_vectors, dtype=np.float32)
        if vectors.shape[0] != total or vectors.shape[1] != query_matrix.shape[1]:
            raise IntegrityError("Batched oracle matrix shape differs")
        oracle_scores = np.asarray(query_matrix @ vectors.T, dtype=np.float32)
        if not np.allclose(scores, oracle_scores, rtol=2.0e-6, atol=2.0e-6):
            raise IntegrityError("Batched FAISS scores disagree with matrix oracle")
        oracle_selected = tuple(
            stable_order(oracle_scores[row], masks[row], movie_ids, count)
            for row in range(len(query_matrix))
        )
        if selected != oracle_selected:
            raise IntegrityError(
                "Batched full-row FAISS retrieval disagrees with matrix lexsort oracle"
            )
    return selected, scores


def assert_oracle_identity(
    index: Any,
    vectors: np.ndarray,
    query: np.ndarray,
    eligible_mask: np.ndarray,
    movie_ids: np.ndarray,
    count: int,
) -> tuple[tuple[int, ...], np.ndarray]:
    main_items, main_scores = exact_faiss_masked_topk(
        index, query, eligible_mask, movie_ids, count
    )
    oracle_items, oracle_scores = exact_matrix_masked_topk(
        vectors, query, eligible_mask, movie_ids, count
    )
    if main_items != oracle_items:
        raise IntegrityError("Full-row FAISS retrieval disagrees with matrix lexsort oracle")
    if not np.allclose(main_scores, oracle_scores, rtol=2.0e-6, atol=2.0e-6):
        raise IntegrityError("Full-row FAISS scores disagree with matrix oracle")
    return main_items, main_scores


def _torch_imports() -> tuple[Any, Any, Any]:
    try:
        import torch
        from torch import nn
        import torch.nn.functional as functional
    except ImportError as exc:
        raise RuntimeError("PyTorch is required for CABLE-PREF") from exc
    return torch, nn, functional


def deterministic_setup(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch, _nn, _functional = _torch_imports()
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    with contextlib.suppress(RuntimeError):
        torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def build_collaborative_mask(
    user_ids: Sequence[int], A: Mapping[int, tuple[Interaction, ...]], item_count: int
) -> np.ndarray:
    support = np.zeros(item_count, dtype=np.int32)
    positive_min = float(LOCKED_CONFIG["bpr"]["positive_rating_min"])
    for user_id in user_ids:
        for event in A[user_id]:
            if event.rating >= positive_min:
                support[event.item_index] += 1
    mask = support >= int(LOCKED_CONFIG["bpr"]["minimum_item_positive_support"])
    if int(np.sum(mask)) < 200:
        raise IntegrityError("A-frozen collaborative catalog has fewer than 200 items")
    return np.ascontiguousarray(mask, dtype=np.bool_)


def _bpr_training_pairs(
    user_ids: Sequence[int],
    A: Mapping[int, tuple[Interaction, ...]],
    collaborative_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    config = LOCKED_CONFIG["bpr"]
    rng = np.random.default_rng(int(config["seed"]))
    collaborative = np.flatnonzero(collaborative_mask).astype(np.int64)
    user_rows: list[int] = []
    positive_rows: list[int] = []
    negative_rows: list[int] = []
    user_to_row = {user_id: row for row, user_id in enumerate(user_ids)}
    candidates: list[tuple[str, int, int]] = []
    positive_by_user: dict[int, set[int]] = {}
    for user_id in user_ids:
        positives = {
            event.item_index
            for event in A[user_id]
            if event.rating >= float(config["positive_rating_min"])
            and collaborative_mask[event.item_index]
        }
        positive_by_user[user_id] = positives
        for item in positives:
            key = hashlib.sha256(f"{config['seed']}:{user_id}:{item}".encode("ascii")).hexdigest()
            candidates.append((key, user_id, item))
    candidates.sort()
    maximum = int(config["maximum_pairs"])
    for _key, user_id, positive in candidates[:maximum]:
        positives = positive_by_user[user_id]
        if len(positives) >= len(collaborative):
            continue
        while True:
            negative = int(collaborative[int(rng.integers(0, len(collaborative)))])
            if negative not in positives:
                break
        user_rows.append(user_to_row[user_id])
        positive_rows.append(positive)
        negative_rows.append(negative)
    if not user_rows:
        raise IntegrityError("BPR training pair corpus is empty")
    return (
        np.asarray(user_rows, dtype=np.int64),
        np.asarray(positive_rows, dtype=np.int64),
        np.asarray(negative_rows, dtype=np.int64),
    )


def train_bpr(
    user_ids: Sequence[int],
    A: Mapping[int, tuple[Interaction, ...]],
    item_count: int,
    collaborative_mask: np.ndarray,
) -> tuple[BPRArtifacts, Mapping[str, Any]]:
    torch, nn, functional = _torch_imports()
    config = LOCKED_CONFIG["bpr"]
    deterministic_setup(int(config["seed"]))

    class BPRModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.users = nn.Embedding(len(user_ids), int(config["dimension"]))
            self.items = nn.Embedding(item_count, int(config["dimension"]))
            nn.init.normal_(self.users.weight, std=0.05)
            nn.init.normal_(self.items.weight, std=0.05)

    model = BPRModel()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    users, positives, negatives = _bpr_training_pairs(user_ids, A, collaborative_mask)
    trace: list[float] = []
    batch_size = int(config["batch_size"])
    for epoch in range(int(config["epochs"])):
        order = np.random.default_rng(int(config["seed"]) + epoch).permutation(len(users))
        losses: list[float] = []
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            user_tensor = torch.from_numpy(users[rows])
            positive_tensor = torch.from_numpy(positives[rows])
            negative_tensor = torch.from_numpy(negatives[rows])
            query = model.users(user_tensor)
            positive_score = torch.sum(query * model.items(positive_tensor), dim=1)
            negative_score = torch.sum(query * model.items(negative_tensor), dim=1)
            loss = functional.softplus(-(positive_score - negative_score)).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        trace.append(float(np.mean(losses)))
    # The registered fusion semantics assign unsupported semantic items an
    # exact all-zero collaborative factor.  Apply this to the model itself so
    # the serialized checkpoint and the deployed NumPy/FAISS geometry are the
    # same object semantically, then take independent contiguous copies.
    with torch.no_grad():
        unsupported = torch.from_numpy(~collaborative_mask)
        model.items.weight[unsupported] = 0.0
    user_vectors = np.array(
        model.users.weight.detach().cpu().numpy(), dtype=np.float32, order="C", copy=True
    )
    item_vectors = np.array(
        model.items.weight.detach().cpu().numpy(), dtype=np.float32, order="C", copy=True
    )
    if not np.all(np.isfinite(user_vectors)) or not np.all(np.isfinite(item_vectors)):
        raise IntegrityError("Trained BPR factors are nonfinite")
    artifacts = BPRArtifacts(
        tuple(map(int, user_ids)),
        {int(user_id): row for row, user_id in enumerate(user_ids)},
        user_vectors,
        item_vectors,
        np.ascontiguousarray(collaborative_mask, dtype=np.bool_),
        tuple(trace),
    )
    state = {
        name: tensor.detach().cpu().clone()
        for name, tensor in model.state_dict().items()
    }
    return artifacts, state


def updated_bpr_query(
    artifacts: BPRArtifacts, user_id: int, history: Sequence[Interaction]
) -> np.ndarray:
    base = np.asarray(artifacts.user_vectors[artifacts.user_to_row[user_id]], dtype=np.float32)
    selected = [event for event in history if artifacts.collaborative_mask[event.item_index]]
    if selected:
        weights = np.asarray(
            [np.clip((event.rating - 3.0) / 2.0, -1.0, 1.0) for event in selected],
            dtype=np.float32,
        )
        if float(np.sum(np.abs(weights))) > 0.0:
            indices = np.asarray([event.item_index for event in selected], dtype=np.int64)
            aggregate = np.sum(artifacts.item_vectors[indices] * weights[:, None], axis=0)
            aggregate /= float(np.sum(np.abs(weights)))
            base = base + float(LOCKED_CONFIG["bpr"]["prefix_update_weight"]) * aggregate
    if not np.all(np.isfinite(base)) or float(np.linalg.norm(base)) <= 1.0e-12:
        raise IntegrityError("Invalid prefix-updated BPR query")
    return np.ascontiguousarray(base, dtype=np.float32)


def query_descriptor(history: Sequence[Interaction], semantic_vectors: np.ndarray) -> QueryDescriptor:
    positive_min = float(LOCKED_CONFIG["dataset"]["positive_rating_min"])
    dislike_max = float(LOCKED_CONFIG["dataset"]["dislike_rating_max"])
    positive = sorted({event.item_index for event in history if event.rating >= positive_min})
    disliked = sorted({event.item_index for event in history if event.rating <= dislike_max})
    if not positive:
        raise IntegrityError("Prefix has no positive item for its semantic query")
    liked = normalise(np.mean(semantic_vectors[np.asarray(positive, dtype=np.int64)], axis=0))
    dislike = (
        normalise(np.mean(semantic_vectors[np.asarray(disliked, dtype=np.int64)], axis=0))
        if disliked
        else np.zeros(semantic_vectors.shape[1], dtype=np.float32)
    )
    raw = normalise(liked - np.float32(0.25) * dislike)
    positive_fraction = len(positive) / max(1, len(history))
    prefix_fraction = min(len(history), 500) / 500.0
    del positive_fraction
    return QueryDescriptor(raw, liked, dislike, float(prefix_fraction))


def descriptor_array(descriptor: QueryDescriptor) -> np.ndarray:
    return np.ascontiguousarray(
        np.concatenate(
            [
                descriptor.raw_query,
                descriptor.liked_centroid,
                descriptor.dislike_centroid,
                np.asarray([descriptor.history_feature], dtype=np.float32),
            ]
        ),
        dtype=np.float32,
    )


def new_adapter(seed: int) -> Any:
    torch, nn, _functional = _torch_imports()
    deterministic_setup(seed)

    class CableAdapter(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.hidden = nn.Linear(1153, int(LOCKED_CONFIG["adapter"]["hidden_dimension"]))
            self.residual = nn.Linear(int(LOCKED_CONFIG["adapter"]["hidden_dimension"]), 384)
            self.boundary = nn.Linear(int(LOCKED_CONFIG["adapter"]["hidden_dimension"]), 1)
            nn.init.zeros_(self.residual.weight)
            nn.init.zeros_(self.residual.bias)
            nn.init.zeros_(self.boundary.weight)
            nn.init.zeros_(self.boundary.bias)

        def forward(self, features: Any) -> tuple[Any, Any]:
            hidden = torch.tanh(self.hidden(features))
            return self.residual(hidden), self.boundary(hidden).squeeze(1)

    return CableAdapter()


def adapter_state_copy(model: Any) -> Mapping[str, Any]:
    return {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}


def adapter_memory_sha256(model: Any) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        array = np.ascontiguousarray(tensor.detach().cpu().numpy())
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(canonical_json_bytes(list(array.shape)))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def adapted_query_tensor(model: Any, features: Any, raw_queries: Any) -> tuple[Any, Any]:
    torch, _nn, _functional = _torch_imports()
    residual, learned_boundary = model(features)
    residual_norm = torch.linalg.vector_norm(residual, dim=1, keepdim=True)
    residual = residual / torch.clamp(residual_norm, min=1.0)
    displaced = raw_queries + float(LOCKED_CONFIG["adapter"]["displacement_bound"]) * residual
    queries = displaced / torch.clamp(torch.linalg.vector_norm(displaced, dim=1, keepdim=True), min=1.0e-12)
    return queries, learned_boundary


def apply_adapter_numpy(descriptor: QueryDescriptor, model: Any | None) -> tuple[np.ndarray, float]:
    if model is None:
        return descriptor.raw_query.copy(), 0.0
    torch, _nn, _functional = _torch_imports()
    model.eval()
    with torch.no_grad():
        features = torch.from_numpy(descriptor_array(descriptor).reshape(1, -1))
        raw = torch.from_numpy(descriptor.raw_query.reshape(1, -1))
        query, boundary = adapted_query_tensor(model, features, raw)
    value = np.ascontiguousarray(query[0].cpu().numpy(), dtype=np.float32)
    if not np.all(np.isfinite(value)) or not math.isclose(float(np.linalg.norm(value)), 1.0, abs_tol=2.0e-5):
        raise IntegrityError("Adapter produced invalid normalized query")
    displacement = float(np.linalg.norm(value - descriptor.raw_query))
    # Normalization can enlarge Euclidean displacement modestly; the bounded
    # pre-normalization residual is separately enforced in adapted_query_tensor.
    if displacement > 0.55:
        raise IntegrityError("Adapter query moved outside its registered envelope")
    return value, float(boundary[0])


def _pair_hash(user_id: int, low_movie_id: int, high_movie_id: int) -> str:
    template = str(LOCKED_CONFIG["dataset"]["pair_hash"])
    return hashlib.sha256(
        template.format(
            user_id=user_id, low_item_id=low_movie_id, high_item_id=high_movie_id
        ).encode("ascii")
    ).hexdigest()


def natural_pairs(
    stage_events: Mapping[int, tuple[Interaction, ...]], stage: str
) -> tuple[tuple[PairRow, ...], Mapping[str, Any]]:
    gap = float(LOCKED_CONFIG["dataset"]["pair_rating_gap"])
    per_user_cap = (
        int(LOCKED_CONFIG["dataset"]["maximum_R_pairs_per_user"])
        if stage == "R"
        else int(LOCKED_CONFIG["dataset"]["maximum_pairs_per_user"])
    )
    by_user: dict[int, list[tuple[str, PairRow]]] = {}
    raw_count = 0
    raw_users = 0
    for user_id in sorted(stage_events):
        events = sorted(stage_events[user_id], key=lambda event: (event.movie_id, event.ordinal))
        if len({event.item_index for event in events}) != len(events):
            raise IntegrityError(f"{stage} pair universe contains repeated items")
        rows: list[tuple[str, PairRow]] = []
        for left in range(len(events)):
            for right in range(left + 1, len(events)):
                difference = events[left].rating - events[right].rating
                if abs(difference) < gap:
                    continue
                preferred, rejected = (
                    (events[left], events[right]) if difference > 0.0 else (events[right], events[left])
                )
                low_id = min(preferred.movie_id, rejected.movie_id)
                high_id = max(preferred.movie_id, rejected.movie_id)
                row = PairRow(user_id, preferred.item_index, rejected.item_index, low_id, high_id)
                rows.append((_pair_hash(user_id, low_id, high_id), row))
        raw_count += len(rows)
        raw_users += int(bool(rows))
        rows.sort(key=lambda value: (value[0], value[1].low_movie_id, value[1].high_movie_id))
        by_user[user_id] = rows[:per_user_cap]
    if stage == "R":
        round_rows: list[tuple[int, str, PairRow]] = []
        for user_id, rows in by_user.items():
            for round_index, (digest, row) in enumerate(rows):
                round_rows.append((round_index, digest, row))
        round_rows.sort(key=lambda value: (value[0], value[1], value[2].user_id))
        selected = tuple(
            value[2]
            for value in round_rows[: int(LOCKED_CONFIG["dataset"]["maximum_R_pairs_global"])]
        )
    else:
        selected = tuple(row for user_id in sorted(by_user) for _digest, row in by_user[user_id])
    if len({(row.user_id, row.low_movie_id, row.high_movie_id) for row in selected}) != len(selected):
        raise IntegrityError("Natural pair cap produced duplicate pair identities")
    return selected, {
        "stage": stage,
        "raw_pairs": raw_count,
        "raw_pair_users": raw_users,
        "selected_pairs": len(selected),
        "selected_pair_users": len({row.user_id for row in selected}),
        "pair_identity_sha256": sha256_bytes(
            canonical_json_bytes(
                [
                    [stage, row.user_id, row.low_movie_id, row.high_movie_id]
                    for row in selected
                ]
            )
        ),
    }


@dataclasses.dataclass(frozen=True)
class RequestContext:
    user_id: int
    descriptor: QueryDescriptor
    bpr_query: np.ndarray
    bpr_items: tuple[int, ...]
    history_mask: np.ndarray
    semantic_mask: np.ndarray
    wrong_boundary_mask: np.ndarray


def assert_request_capacity(
    *, bpr_available: int | None = None, semantic_complement_available: int | None = None
) -> None:
    if (
        bpr_available is not None
        and bpr_available < int(LOCKED_CONFIG["retrieval"]["bpr_exact"])
    ):
        raise IntegrityError("Prefix has fewer than 200 unseen collaborative items")
    if (
        semantic_complement_available is not None
        and semantic_complement_available
        < int(LOCKED_CONFIG["retrieval"]["semantic_minimum_complement"])
    ):
        raise IntegrityError("Semantic complement contains fewer than 500 items")


def build_request_context(
    user_id: int,
    history: Sequence[Interaction],
    bpr: BPRArtifacts,
    bpr_index: Any,
    semantic_vectors: np.ndarray,
    movie_ids: np.ndarray,
    *,
    verify_oracle: bool = True,
) -> RequestContext:
    item_count = len(movie_ids)
    history_mask = np.zeros(item_count, dtype=np.bool_)
    history_mask[[event.item_index for event in history]] = True
    bpr_eligible = np.asarray(bpr.collaborative_mask & ~history_mask, dtype=np.bool_)
    assert_request_capacity(bpr_available=int(np.sum(bpr_eligible)))
    bpr_query = updated_bpr_query(bpr, user_id, history)
    if verify_oracle:
        bpr_items, _bpr_scores = assert_oracle_identity(
            bpr_index,
            bpr.item_vectors,
            bpr_query,
            bpr_eligible,
            movie_ids,
            int(LOCKED_CONFIG["retrieval"]["bpr_exact"]),
        )
    else:
        bpr_items, _bpr_scores = exact_faiss_masked_topk(
            bpr_index,
            bpr_query,
            bpr_eligible,
            movie_ids,
            int(LOCKED_CONFIG["retrieval"]["bpr_exact"]),
        )
    semantic_mask = ~history_mask
    semantic_mask[np.asarray(bpr_items, dtype=np.int64)] = False
    assert_request_capacity(
        semantic_complement_available=int(np.sum(semantic_mask))
    )
    return RequestContext(
        user_id,
        query_descriptor(history, semantic_vectors),
        bpr_query,
        bpr_items,
        np.ascontiguousarray(history_mask),
        np.ascontiguousarray(semantic_mask),
        np.ascontiguousarray(~history_mask),
    )


def build_request_contexts_batch(
    user_ids: Sequence[int],
    histories: Mapping[int, tuple[Interaction, ...]],
    bpr: BPRArtifacts,
    bpr_index: Any,
    semantic_vectors: np.ndarray,
    movie_ids: np.ndarray,
) -> tuple[RequestContext, ...]:
    """Construct a manifest batch while preserving the single-request oracle."""
    item_count = len(movie_ids)
    history_masks: list[np.ndarray] = []
    bpr_masks: list[np.ndarray] = []
    bpr_queries: list[np.ndarray] = []
    descriptors: list[QueryDescriptor] = []
    for user_id in user_ids:
        history = histories[int(user_id)]
        history_mask = np.zeros(item_count, dtype=np.bool_)
        history_mask[[event.item_index for event in history]] = True
        bpr_mask = np.asarray(
            bpr.collaborative_mask & ~history_mask, dtype=np.bool_
        )
        assert_request_capacity(bpr_available=int(np.sum(bpr_mask)))
        history_masks.append(history_mask)
        bpr_masks.append(bpr_mask)
        bpr_queries.append(updated_bpr_query(bpr, int(user_id), history))
        descriptors.append(query_descriptor(history, semantic_vectors))
    selected_rows, _score_rows = exact_faiss_masked_topk_batch(
        bpr_index,
        np.stack(bpr_queries),
        np.stack(bpr_masks),
        movie_ids,
        int(LOCKED_CONFIG["retrieval"]["bpr_exact"]),
        oracle_vectors=bpr.item_vectors,
    )
    contexts: list[RequestContext] = []
    for row, user_id in enumerate(user_ids):
        semantic_mask = ~history_masks[row]
        semantic_mask[np.asarray(selected_rows[row], dtype=np.int64)] = False
        assert_request_capacity(
            semantic_complement_available=int(np.sum(semantic_mask))
        )
        contexts.append(
            RequestContext(
                int(user_id),
                descriptors[row],
                np.ascontiguousarray(bpr_queries[row], dtype=np.float32),
                selected_rows[row],
                np.ascontiguousarray(history_masks[row]),
                np.ascontiguousarray(semantic_mask),
                np.ascontiguousarray(~history_masks[row]),
            )
        )
    return tuple(contexts)


def stable_leaveout_boundary_index(
    scores: np.ndarray,
    eligible_mask: np.ndarray,
    endpoint: int,
    movie_ids: np.ndarray,
    count: int = 200,
) -> int:
    mask = np.asarray(eligible_mask, dtype=np.bool_).copy()
    if endpoint < 0 or endpoint >= len(mask) or not mask[endpoint]:
        raise IntegrityError("Leave-out preferred endpoint is outside the deployed domain")
    mask[endpoint] = False
    ordered = stable_order(scores, mask, movie_ids, count)
    return int(ordered[-1])


def leaveout_boundaries_from_base_topk(
    scores: np.ndarray,
    eligible_mask: np.ndarray,
    endpoints: Iterable[int],
    movie_ids: np.ndarray,
    count: int = 200,
) -> Mapping[int, int]:
    """Exact endpoint leave-out cutoffs from one canonical base top-(k+1)."""
    unique = tuple(sorted(set(map(int, endpoints))))
    if not unique:
        return {}
    mask = np.asarray(eligible_mask, dtype=np.bool_)
    if any(endpoint < 0 or endpoint >= len(mask) or not mask[endpoint] for endpoint in unique):
        raise IntegrityError("Leave-out endpoint is outside the deployed domain")
    base = stable_order(scores, mask, movie_ids, count + 1)
    admitted = set(base[:count])
    rank_k = int(base[count - 1])
    rank_k_plus_one = int(base[count])
    return {
        endpoint: rank_k_plus_one if endpoint in admitted else rank_k
        for endpoint in unique
    }


def admission_from_boundary_key(
    scores: np.ndarray, endpoint: int, boundary: int, movie_ids: np.ndarray
) -> bool:
    endpoint_key = (-float(scores[endpoint]), int(movie_ids[endpoint]))
    boundary_key = (-float(scores[boundary]), int(movie_ids[boundary]))
    return endpoint_key < boundary_key


def train_adapter_control(
    method: str,
    seed: int,
    contexts: Mapping[int, RequestContext],
    pairs: Sequence[PairRow],
    semantic_vectors: np.ndarray,
    movie_ids: np.ndarray,
    initial_state: Mapping[str, Any],
) -> tuple[Any, Mapping[str, Any], Mapping[str, Any]]:
    if method not in TRAINED_METHODS:
        raise ValueError(method)
    torch, _nn, functional = _torch_imports()
    config = LOCKED_CONFIG["adapter"]
    deterministic_setup(seed)
    model = new_adapter(seed)
    model.load_state_dict(initial_state, strict=True)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    by_user: dict[int, list[PairRow]] = {}
    for pair in pairs:
        by_user.setdefault(pair.user_id, []).append(pair)
    users = sorted(user_id for user_id in by_user if user_id in contexts)
    if not users:
        raise IntegrityError("No R pair-bearing user has a request context")
    # The immutable NumPy matrix is deliberately read-only.  Give PyTorch its
    # own writable training view so `torch.from_numpy` cannot emit the
    # non-writable-buffer UserWarning that would poison fail-closed stderr.
    semantic_tensor = torch.from_numpy(
        np.array(semantic_vectors, dtype=np.float32, order="C", copy=True)
    )
    trace: list[Mapping[str, float]] = []
    optimizer_steps = 0
    pair_presentations = 0
    admission_presentations = 0

    for epoch in range(int(config["epochs"])):
        users_epoch = sorted(
            users,
            key=lambda user_id: (
                hashlib.sha256(f"20263502:train:{seed}:{epoch}:{user_id}".encode("ascii")).hexdigest(),
                user_id,
            ),
        )
        epoch_losses: list[float] = []
        epoch_admit: list[float] = []
        epoch_order: list[float] = []
        for start in range(0, len(users_epoch), int(config["batch_users"])):
            batch_users = users_epoch[start : start + int(config["batch_users"])]
            features = torch.from_numpy(
                np.stack([descriptor_array(contexts[user_id].descriptor) for user_id in batch_users])
            )
            raw_queries = torch.from_numpy(
                np.stack([contexts[user_id].descriptor.raw_query for user_id in batch_users])
            )
            queries, learned_boundaries = adapted_query_tensor(model, features, raw_queries)
            full_scores = queries @ semantic_tensor.T
            admit_user_losses: list[Any] = []
            order_user_losses: list[Any] = []
            for row_index, user_id in enumerate(batch_users):
                context = contexts[user_id]
                score_row = full_scores[row_index]
                detached_scores = np.ascontiguousarray(score_row.detach().cpu().numpy(), dtype=np.float32)
                admit_by_endpoint: dict[int, Any] = {}
                uib_rejected_pairs: list[Any] = []
                order_pairs: list[Any] = []
                ordered_pairs = sorted(
                    by_user[user_id],
                    key=lambda pair: (_pair_hash(pair.user_id, pair.low_movie_id, pair.high_movie_id), pair.low_movie_id),
                )
                effective_pairs: list[PairRow] = []
                for pair_index, original in enumerate(ordered_pairs):
                    pair = original
                    if method == "shuffled_direction" and pair_index % 2 == 0:
                        pair = PairRow(
                            original.user_id,
                            original.rejected,
                            original.preferred,
                            original.low_movie_id,
                            original.high_movie_id,
                        )
                    effective_pairs.append(pair)
                boundary_by_endpoint: Mapping[int, int] = {}
                if method != "uib_boundary":
                    boundary_mask = (
                        context.wrong_boundary_mask
                        if method == "wrong_boundary"
                        else context.semantic_mask
                    )
                    boundary_by_endpoint = leaveout_boundaries_from_base_topk(
                        detached_scores,
                        boundary_mask,
                        (
                            pair.preferred
                            for pair in effective_pairs
                            if context.semantic_mask[pair.preferred]
                        ),
                        movie_ids,
                        int(LOCKED_CONFIG["retrieval"]["semantic_exact"]),
                    )
                for pair in effective_pairs:
                    preferred_score = score_row[pair.preferred]
                    rejected_score = score_row[pair.rejected]
                    order_pairs.append(
                        functional.softplus(
                            float(config["beta"])
                            * (float(config["order_margin"]) - preferred_score + rejected_score)
                        )
                    )
                    pair_presentations += 1
                    if context.semantic_mask[pair.preferred]:
                        if method == "uib_boundary":
                            boundary_score = learned_boundaries[row_index]
                        else:
                            boundary_index = boundary_by_endpoint[pair.preferred]
                            # The nonparametric cutoff is intentionally detached.
                            boundary_score = score_row[boundary_index].detach()
                        if pair.preferred not in admit_by_endpoint:
                            admit_by_endpoint[pair.preferred] = functional.softplus(
                                float(config["beta"])
                                * (
                                    boundary_score
                                    + float(config["admission_margin"])
                                    - preferred_score
                                )
                            )
                            admission_presentations += 1
                        if method == "uib_boundary":
                            # Matched learned-interest-boundary control: prefer
                            # i+ above and i- below the same request scalar.
                            uib_rejected_pairs.append(
                                functional.softplus(
                                    float(config["beta"])
                                    * (
                                        float(config["admission_margin"])
                                        - boundary_score
                                        + rejected_score
                                    )
                                )
                            )
                if admit_by_endpoint:
                    preferred_term = torch.stack(list(admit_by_endpoint.values())).mean()
                    if method == "uib_boundary":
                        if not uib_rejected_pairs:
                            raise IntegrityError("UIB active preferred rows lack rejected-boundary rows")
                        rejected_term = torch.stack(uib_rejected_pairs).mean()
                        admit_user_losses.append(0.5 * preferred_term + 0.5 * rejected_term)
                    else:
                        admit_user_losses.append(preferred_term)
                if order_pairs:
                    order_user_losses.append(torch.stack(order_pairs).mean())
            zero = sum((parameter.sum() * 0.0 for parameter in model.parameters()))
            admit_loss = torch.stack(admit_user_losses).mean() if admit_user_losses else zero
            order_loss = torch.stack(order_user_losses).mean() if order_user_losses else zero
            if method == "order_only":
                loss = order_loss
            elif method == "admission_only":
                loss = admit_loss
            else:
                loss = (
                    float(config["admission_weight"]) * admit_loss
                    + float(config["order_weight"]) * order_loss
                )
            if not bool(torch.isfinite(loss)):
                raise IntegrityError(f"{method} training loss is nonfinite")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(config["gradient_clip"]))
            optimizer.step()
            optimizer_steps += 1
            epoch_losses.append(float(loss.detach()))
            epoch_admit.append(float(admit_loss.detach()))
            epoch_order.append(float(order_loss.detach()))
        trace.append(
            {
                "loss": float(np.mean(epoch_losses)),
                "admission": float(np.mean(epoch_admit)),
                "order": float(np.mean(epoch_order)),
            }
        )
    model.eval()
    diagnostics = {
        "method": method,
        "seed": seed,
        "epochs": int(config["epochs"]),
        "optimizer_steps": optimizer_steps,
        "pair_presentations": pair_presentations,
        "admission_presentations": admission_presentations,
        "final_epoch_only": True,
        "reference_model_used": False,
        "trace": trace,
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "checkpoint_sha256": adapter_memory_sha256(model),
    }
    return model, diagnostics, adapter_state_copy(model)


def quantile_scale(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    lower, upper = np.percentile(array.astype(np.float64), [5.0, 95.0])
    span = max(float(upper - lower), 1.0e-6)
    return np.ascontiguousarray(np.clip((array - np.float32(lower)) / np.float32(span), 0.0, 1.0), dtype=np.float32)


def rank_items(items: Sequence[int], scores: np.ndarray, movie_ids: np.ndarray) -> tuple[int, ...]:
    item_array = np.asarray(items, dtype=np.int64)
    score_array = np.asarray(scores, dtype=np.float32)
    if len(item_array) != len(score_array) or np.any(~np.isfinite(score_array)):
        raise IntegrityError("Ranking item/score arrays are malformed")
    order = np.lexsort((movie_ids[item_array], -score_array))
    return tuple(map(int, item_array[order]))


def retrieve_hybrid(
    context: RequestContext,
    semantic_query: np.ndarray,
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: np.ndarray,
    alpha: float,
    *,
    verify_oracle: bool = True,
) -> RetrievalRow:
    if verify_oracle:
        semantic_items, _complete_semantic_scores = assert_oracle_identity(
            semantic_index,
            semantic_vectors,
            semantic_query,
            context.semantic_mask,
            movie_ids,
            int(LOCKED_CONFIG["retrieval"]["semantic_exact"]),
        )
    else:
        semantic_items, _complete_semantic_scores = exact_faiss_masked_topk(
            semantic_index,
            semantic_query,
            context.semantic_mask,
            movie_ids,
            int(LOCKED_CONFIG["retrieval"]["semantic_exact"]),
        )
    union = (*context.bpr_items, *semantic_items)
    if (
        len(union) != int(LOCKED_CONFIG["retrieval"]["union_exact"])
        or len(set(union)) != len(union)
        or set(context.bpr_items) & set(semantic_items)
        or set(union) & set(np.flatnonzero(context.history_mask))
    ):
        raise IntegrityError("Exact 200+200 union invariant failed")
    indices = np.asarray(union, dtype=np.int64)
    raw_bpr = np.asarray(bpr.item_vectors[indices] @ context.bpr_query, dtype=np.float32)
    raw_semantic = np.asarray(semantic_vectors[indices] @ semantic_query, dtype=np.float32)
    normalized_bpr = quantile_scale(raw_bpr)
    normalized_semantic = quantile_scale(raw_semantic)
    final = np.asarray(
        np.float32(alpha) * normalized_bpr + np.float32(1.0 - alpha) * normalized_semantic,
        dtype=np.float32,
    )
    ranking = rank_items(union, final, movie_ids)
    return RetrievalRow(
        tuple(context.bpr_items),
        tuple(semantic_items),
        tuple(union),
        raw_bpr,
        raw_semantic,
        ranking,
    )


@dataclasses.dataclass(frozen=True)
class StageManifest:
    stage: str
    seed: int
    user_ids: np.ndarray
    candidates: np.ndarray
    bpr_scores: np.ndarray
    semantic_scores: np.ndarray
    bpr_queries: np.ndarray
    semantic_queries: np.ndarray
    learned_boundaries: np.ndarray
    history_items: np.ndarray
    history_counts: np.ndarray
    complement_counts: np.ndarray
    oracle_agreement: np.ndarray


def build_stage_manifest(
    stage: str,
    seed: int,
    user_ids: Sequence[int],
    histories: Mapping[int, tuple[Interaction, ...]],
    models: Mapping[str, Any],
    bpr: BPRArtifacts,
    bpr_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: np.ndarray,
) -> StageManifest:
    user_count = len(user_ids)
    method_count = len(METHODS)
    maximum_history = max(len(histories[user_id]) for user_id in user_ids)
    candidates = np.full((method_count, user_count, 400), -1, dtype=np.int32)
    bpr_scores = np.full((method_count, user_count, 400), np.nan, dtype=np.float32)
    semantic_scores = np.full_like(bpr_scores, np.nan)
    bpr_queries = np.full((user_count, 64), np.nan, dtype=np.float32)
    semantic_queries = np.full((method_count, user_count, 384), np.nan, dtype=np.float32)
    learned_boundaries = np.full((method_count, user_count), np.nan, dtype=np.float32)
    history_items = np.full((user_count, maximum_history), -1, dtype=np.int32)
    history_counts = np.zeros(user_count, dtype=np.int16)
    complement_counts = np.zeros(user_count, dtype=np.int16)
    oracle_agreement = np.ones((method_count, user_count), dtype=np.uint8)

    batch_size = int(LOCKED_CONFIG["retrieval"]["manifest_query_batch_size"])
    for start in range(0, user_count, batch_size):
        stop = min(user_count, start + batch_size)
        batch_user_ids = tuple(map(int, user_ids[start:stop]))
        contexts = build_request_contexts_batch(
            batch_user_ids,
            histories,
            bpr,
            bpr_index,
            semantic_vectors,
            movie_ids,
        )
        for local_row, (user_id, context) in enumerate(
            zip(batch_user_ids, contexts, strict=True)
        ):
            user_row = start + local_row
            history = histories[user_id]
            history_counts[user_row] = len(history)
            history_items[user_row, : len(history)] = [
                event.item_index for event in history
            ]
            bpr_queries[user_row] = context.bpr_query
            complement_counts[user_row] = int(np.sum(context.semantic_mask))
            bpr_row = tuple(context.bpr_items)
            candidates[0, user_row, :200] = bpr_row
            bpr_scores[0, user_row, :200] = np.asarray(
                bpr.item_vectors[np.asarray(bpr_row, dtype=np.int64)]
                @ context.bpr_query,
                dtype=np.float32,
            )

        semantic_masks = np.stack(
            [context.semantic_mask for context in contexts]
        )
        for method_index, method in enumerate(HYBRID_METHODS, start=1):
            model = None if method == "raw_hybrid" else models[method]
            query_rows: list[np.ndarray] = []
            boundary_rows: list[float] = []
            for context in contexts:
                query, learned_boundary = apply_adapter_numpy(
                    context.descriptor, model
                )
                query_rows.append(query)
                boundary_rows.append(learned_boundary)
            query_matrix = np.stack(query_rows)
            selected_rows, _complete_scores = exact_faiss_masked_topk_batch(
                semantic_index,
                query_matrix,
                semantic_masks,
                movie_ids,
                int(LOCKED_CONFIG["retrieval"]["semantic_exact"]),
                oracle_vectors=semantic_vectors,
            )
            for local_row, (context, semantic_items) in enumerate(
                zip(contexts, selected_rows, strict=True)
            ):
                user_row = start + local_row
                semantic_query = query_matrix[local_row]
                semantic_queries[method_index, user_row] = semantic_query
                learned_boundaries[method_index, user_row] = boundary_rows[local_row]
                union = (*context.bpr_items, *semantic_items)
                if (
                    len(union) != int(LOCKED_CONFIG["retrieval"]["union_exact"])
                    or len(set(union)) != len(union)
                    or set(context.bpr_items) & set(semantic_items)
                    or set(union) & set(np.flatnonzero(context.history_mask))
                ):
                    raise IntegrityError("Batched exact 200+200 union invariant failed")
                indices = np.asarray(union, dtype=np.int64)
                candidates[method_index, user_row] = indices
                bpr_scores[method_index, user_row] = np.asarray(
                    bpr.item_vectors[indices] @ context.bpr_query,
                    dtype=np.float32,
                )
                semantic_scores[method_index, user_row] = np.asarray(
                    semantic_vectors[indices] @ semantic_query,
                    dtype=np.float32,
                )
    if np.any(candidates[1:, :, :] < 0) or np.any(candidates[0, :, :200] < 0):
        raise IntegrityError("Stage manifest has incomplete candidate rows")
    return StageManifest(
        stage,
        seed,
        np.asarray(user_ids, dtype=np.int64),
        candidates,
        bpr_scores,
        semantic_scores,
        bpr_queries,
        semantic_queries,
        learned_boundaries,
        history_items,
        history_counts,
        complement_counts,
        oracle_agreement,
    )


def manifest_npz_arrays(
    manifest: StageManifest,
    protocol_sha256: str,
    execution_fingerprint: str,
) -> Mapping[str, np.ndarray]:
    return {
        "schema": np.asarray(["cable-pref-target-blind-manifest-v1"], dtype="U48"),
        "protocol_sha256": np.asarray([protocol_sha256], dtype="U64"),
        "execution_fingerprint_sha256": np.asarray([execution_fingerprint], dtype="U64"),
        "stage": np.asarray([manifest.stage], dtype="U1"),
        "seed": np.asarray([manifest.seed], dtype=np.int64),
        "methods": np.asarray(METHODS, dtype="U32"),
        "alphas": np.asarray(ALPHAS, dtype=np.float32),
        "user_ids": manifest.user_ids,
        "candidates": manifest.candidates,
        "bpr_scores": manifest.bpr_scores,
        "semantic_scores": manifest.semantic_scores,
        "bpr_queries": manifest.bpr_queries,
        "semantic_queries": manifest.semantic_queries,
        "learned_boundaries": manifest.learned_boundaries,
        "history_items": manifest.history_items,
        "history_counts": manifest.history_counts,
        "complement_counts": manifest.complement_counts,
        "oracle_agreement": manifest.oracle_agreement,
        "target_fields_accessed": np.asarray([0], dtype=np.uint8),
    }


def build_R_target_blind_arrays(
    user_ids: Sequence[int],
    A: Mapping[int, tuple[Interaction, ...]],
    bpr: BPRArtifacts,
    bpr_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: np.ndarray,
    protocol_sha256: str,
    execution_fingerprint: str,
) -> tuple[Mapping[int, RequestContext], Mapping[str, np.ndarray]]:
    contexts: dict[int, RequestContext] = {}
    bpr_items = np.full((len(user_ids), 200), -1, dtype=np.int32)
    raw_semantic_items = np.full_like(bpr_items, -1)
    raw_queries = np.zeros((len(user_ids), 384), dtype=np.float32)
    bpr_queries = np.zeros((len(user_ids), 64), dtype=np.float32)
    history_maximum = max(len(A[user_id]) for user_id in user_ids)
    history_items = np.full((len(user_ids), history_maximum), -1, dtype=np.int32)
    history_counts = np.zeros(len(user_ids), dtype=np.int16)
    complement_counts = np.zeros(len(user_ids), dtype=np.int16)
    cutoff_items = np.full(len(user_ids), -1, dtype=np.int32)
    cutoff_scores = np.full(len(user_ids), np.nan, dtype=np.float32)
    batch_size = int(LOCKED_CONFIG["retrieval"]["manifest_query_batch_size"])
    for start in range(0, len(user_ids), batch_size):
        stop = min(len(user_ids), start + batch_size)
        batch_user_ids = tuple(map(int, user_ids[start:stop]))
        batch_contexts = build_request_contexts_batch(
            batch_user_ids,
            A,
            bpr,
            bpr_index,
            semantic_vectors,
            movie_ids,
        )
        query_matrix = np.stack(
            [context.descriptor.raw_query for context in batch_contexts]
        )
        semantic_rows, complete_score_rows = exact_faiss_masked_topk_batch(
            semantic_index,
            query_matrix,
            np.stack([context.semantic_mask for context in batch_contexts]),
            movie_ids,
            200,
            oracle_vectors=semantic_vectors,
        )
        for local_row, (user_id, context, semantic) in enumerate(
            zip(batch_user_ids, batch_contexts, semantic_rows, strict=True)
        ):
            row = start + local_row
            contexts[user_id] = context
            bpr_items[row] = context.bpr_items
            raw_queries[row] = context.descriptor.raw_query
            bpr_queries[row] = context.bpr_query
            history_counts[row] = len(A[user_id])
            history_items[row, : len(A[user_id])] = [
                event.item_index for event in A[user_id]
            ]
            complement_counts[row] = int(np.sum(context.semantic_mask))
            raw_semantic_items[row] = semantic
            cutoff_items[row] = semantic[-1]
            cutoff_scores[row] = complete_score_rows[local_row, semantic[-1]]
    arrays = {
        "schema": np.asarray(["cable-pref-R-target-blind-v1"], dtype="U40"),
        "protocol_sha256": np.asarray([protocol_sha256], dtype="U64"),
        "execution_fingerprint_sha256": np.asarray([execution_fingerprint], dtype="U64"),
        "user_ids": np.asarray(user_ids, dtype=np.int64),
        "bpr_items": bpr_items,
        "raw_semantic_items": raw_semantic_items,
        "raw_queries": raw_queries,
        "bpr_queries": bpr_queries,
        "history_items": history_items,
        "history_counts": history_counts,
        "complement_counts": complement_counts,
        "raw_cutoff_items": cutoff_items,
        "raw_cutoff_scores": cutoff_scores,
        "target_fields_accessed": np.asarray([0], dtype=np.uint8),
    }
    return contexts, arrays


def _selected_ranking(
    manifest: StageManifest,
    method_index: int,
    user_row: int,
    alpha_index: int,
    movie_ids: np.ndarray,
) -> tuple[int, ...]:
    size = 200 if method_index == 0 else 400
    items = np.asarray(manifest.candidates[method_index, user_row, :size], dtype=np.int64)
    if np.any(items < 0) or len(set(map(int, items))) != size:
        raise IntegrityError("Manifest candidate row is incomplete or duplicated")
    if method_index == 0:
        scores = np.asarray(manifest.bpr_scores[method_index, user_row, :size], dtype=np.float32)
    else:
        normalized_bpr = quantile_scale(manifest.bpr_scores[method_index, user_row, :size])
        normalized_semantic = quantile_scale(manifest.semantic_scores[method_index, user_row, :size])
        alpha = float(ALPHAS[alpha_index])
        scores = np.asarray(
            np.float32(alpha) * normalized_bpr
            + np.float32(1.0 - alpha) * normalized_semantic,
            dtype=np.float32,
        )
    return rank_items(items, scores, movie_ids)


def _user_stage_pairs(pairs: Sequence[PairRow]) -> Mapping[int, tuple[PairRow, ...]]:
    result: dict[int, list[PairRow]] = {}
    for pair in pairs:
        result.setdefault(pair.user_id, []).append(pair)
    return {user_id: tuple(rows) for user_id, rows in result.items()}


def evaluate_manifest(
    manifest: StageManifest,
    stage_events: Mapping[int, tuple[Interaction, ...]],
    pairs: Sequence[PairRow],
    selected_alpha_index: int,
    movie_ids: np.ndarray,
) -> tuple[np.ndarray, Mapping[str, Any]]:
    metric_index = {name: index for index, name in enumerate(METRICS)}
    values = np.full((len(METHODS), len(manifest.user_ids), len(METRICS)), np.nan, dtype=np.float64)
    pairs_by_user = _user_stage_pairs(pairs)
    admission_changed = 0
    admission_total = 0
    spce_changed = 0
    spce_total = 0
    missed_unique_total = 0
    missed_unique_users = 0

    for user_row, raw_user_id in enumerate(manifest.user_ids):
        user_id = int(raw_user_id)
        events = stage_events[user_id]
        user_pairs = pairs_by_user.get(user_id, tuple())
        preferred = sorted({pair.preferred for pair in user_pairs})
        bpr_set = set(map(int, manifest.candidates[0, user_row, :200]))
        missed = [item for item in preferred if item not in bpr_set]
        missed_unique_total += len(missed)
        missed_unique_users += int(bool(missed))
        positives = {event.item_index for event in events if event.rating >= float(LOCKED_CONFIG["dataset"]["positive_rating_min"])}
        dislikes = {event.item_index for event in events if event.rating <= float(LOCKED_CONFIG["dataset"]["dislike_rating_max"])}
        raw_semantic = set(map(int, manifest.candidates[1, user_row, 200:400]))
        cable_semantic = set(map(int, manifest.candidates[4, user_row, 200:400]))
        for item in missed:
            admission_total += 1
            admission_changed += int((item in raw_semantic) != (item in cable_semantic))

        raw_rank10 = {
            item: rank + 1
            for rank, item in enumerate(_selected_ranking(manifest, 1, user_row, selected_alpha_index, movie_ids)[:10])
        }
        cable_rank10 = {
            item: rank + 1
            for rank, item in enumerate(_selected_ranking(manifest, 4, user_row, selected_alpha_index, movie_ids)[:10])
        }
        for pair in user_pairs:
            raw_outcome = int(raw_rank10.get(pair.preferred, 11) < raw_rank10.get(pair.rejected, 11))
            cable_outcome = int(cable_rank10.get(pair.preferred, 11) < cable_rank10.get(pair.rejected, 11))
            spce_total += 1
            spce_changed += int(raw_outcome != cable_outcome)

        for method_index in range(len(METHODS)):
            ranking = _selected_ranking(manifest, method_index, user_row, selected_alpha_index, movie_ids)
            top10 = ranking[:10]
            semantic_set = (
                set()
                if method_index == 0
                else set(map(int, manifest.candidates[method_index, user_row, 200:400]))
            )
            if missed:
                values[method_index, user_row, metric_index["conditional_admission_at_200"]] = np.mean(
                    [item in semantic_set for item in missed]
                )
            if preferred:
                values[method_index, user_row, metric_index["net_new_preferred_support"]] = np.mean(
                    [item not in bpr_set and item in semantic_set for item in preferred]
                )
                values[method_index, user_row, metric_index["preferred_exposure_at_10"]] = np.mean(
                    [item in set(top10) for item in preferred]
                )
            if user_pairs:
                values[method_index, user_row, metric_index["net_admission_advantage"]] = np.mean(
                    [
                        float(pair.preferred in semantic_set) - float(pair.rejected in semantic_set)
                        for pair in user_pairs
                    ]
                )
                rank10 = {item: rank + 1 for rank, item in enumerate(top10)}
                values[method_index, user_row, metric_index["spce_at_10"]] = np.mean(
                    [
                        rank10.get(pair.preferred, 11) < rank10.get(pair.rejected, 11)
                        for pair in user_pairs
                    ]
                )
            if positives:
                gains = np.asarray([1.0 if item in positives else 0.0 for item in top10], dtype=np.float64)
                discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
                dcg = float(np.sum(gains * discounts))
                ideal = float(np.sum(discounts[: min(10, len(positives))]))
                values[method_index, user_row, metric_index["ndcg_at_10"]] = dcg / ideal
                values[method_index, user_row, metric_index["recall_at_10"]] = sum(
                    item in positives for item in top10
                ) / len(positives)
            values[method_index, user_row, metric_index["low_rating_intrusion_at_10"]] = sum(
                item in dislikes for item in top10
            ) / 10.0
    diagnostics = {
        "fixed_pairs": len(pairs),
        "pair_users": len({pair.user_id for pair in pairs}),
        "unique_bpr_missed_preferred_endpoints": missed_unique_total,
        "missed_endpoint_users": missed_unique_users,
        "admission_changed_count": admission_changed,
        "admission_total": admission_total,
        "spce_changed_count": spce_changed,
        "spce_total": spce_total,
    }
    return values, diagnostics


def select_shared_alpha(
    manifests: Mapping[int, StageManifest],
    V: Mapping[int, tuple[Interaction, ...]],
    movie_ids: np.ndarray,
) -> tuple[int, float, Mapping[str, Any]]:
    scores: list[Mapping[str, float]] = []
    for alpha_index, alpha in enumerate(ALPHAS):
        ndcg_seed: list[float] = []
        recall_seed: list[float] = []
        for seed in SEEDS:
            manifest = manifests[seed]
            ndcg_users: list[float] = []
            recall_users: list[float] = []
            for user_row, raw_user_id in enumerate(manifest.user_ids):
                user_id = int(raw_user_id)
                positives = {
                    event.item_index
                    for event in V[user_id]
                    if event.rating >= float(LOCKED_CONFIG["dataset"]["positive_rating_min"])
                }
                if not positives:
                    continue
                top10 = _selected_ranking(manifest, 1, user_row, alpha_index, movie_ids)[:10]
                discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
                gains = np.asarray([item in positives for item in top10], dtype=np.float64)
                ideal = float(np.sum(discounts[: min(10, len(positives))]))
                ndcg_users.append(float(np.sum(gains * discounts)) / ideal)
                recall_users.append(sum(item in positives for item in top10) / len(positives))
            if not ndcg_users or not recall_users:
                raise IntegrityError(
                    "Validation relevance has no positive-bearing users for alpha selection"
                )
            ndcg_seed.append(float(np.mean(ndcg_users)))
            recall_seed.append(float(np.mean(recall_users)))
        scores.append(
            {
                "alpha": float(alpha),
                "ndcg": float(np.mean(ndcg_seed)),
                "recall": float(np.mean(recall_seed)),
            }
        )
    selected = max(range(len(scores)), key=lambda index: (scores[index]["ndcg"], scores[index]["recall"], scores[index]["alpha"]))
    return selected, float(ALPHAS[selected]), {"grid": scores, "selected_index": selected}


def paired_bootstrap(
    left: np.ndarray,
    right: np.ndarray,
    *,
    draws: int = 10_000,
    alpha: float = 0.05,
    seed: int = 20263504,
) -> Mapping[str, float | int]:
    difference = np.asarray(left, dtype=np.float64) - np.asarray(right, dtype=np.float64)
    finite = np.isfinite(difference)
    values = difference[finite]
    if not len(values):
        raise IntegrityError("Paired bootstrap has no finite common users")
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    chunk = 128
    for start in range(0, draws, chunk):
        size = min(chunk, draws - start)
        indices = rng.integers(0, len(values), size=(size, len(values)), endpoint=False)
        means[start : start + size] = np.mean(values[indices], axis=1)
    return {
        "point": float(np.mean(values)),
        "lower": float(np.quantile(means, alpha / 2.0)),
        "upper": float(np.quantile(means, 1.0 - alpha / 2.0)),
        "users": int(len(values)),
    }


def centered_power_detection(values: np.ndarray, delta: float, seed: int) -> Mapping[str, Any]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if len(finite) < 2:
        return {"detection_fraction": 0.0, "experiments": 1000, "passed": False}
    centered = finite - float(np.mean(finite)) + float(delta)
    experiments = int(LOCKED_CONFIG["power"]["experiments"])
    rng = np.random.default_rng(seed)
    detected = 0
    # A percentile user bootstrap is repeated on each synthetic experiment.
    # The inner draw count is fixed at 1,000 by the protocol; chunks bound RAM.
    for experiment in range(experiments):
        synthetic = centered[rng.integers(0, len(centered), size=len(centered), endpoint=False)]
        inner = np.empty(1000, dtype=np.float64)
        for start in range(0, 1000, 100):
            indices = rng.integers(0, len(synthetic), size=(100, len(synthetic)), endpoint=False)
            inner[start : start + 100] = np.mean(synthetic[indices], axis=1)
        detected += int(float(np.quantile(inner, 0.025)) > 0.0)
    fraction = detected / experiments
    return {
        "detection_fraction": fraction,
        "experiments": experiments,
        "detected": detected,
        "passed": bool(fraction >= float(LOCKED_CONFIG["power"]["minimum_pass_probability"])),
    }


def power_audit(validation_metrics: np.ndarray) -> Mapping[str, Any]:
    metric_index = {name: index for index, name in enumerate(METRICS)}
    # Some user/metric cells are structurally undefined for every seed (for
    # example conditional admission when BPR missed no preferred endpoint).
    # The explicit finite-count reducer preserves those NaNs without emitting
    # a RuntimeWarning to the runner's fail-closed stderr stream.
    averaged = _nanmean_seed(validation_metrics)
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
        name: centered_power_detection(values, delta, seed)
        for name, (values, delta, seed) in comparisons.items()
    }
    return {"comparisons": results, "passed": bool(all(result["passed"] for result in results.values()))}


def stage_outcome_arrays(
    user_ids: Sequence[int],
    events: Mapping[int, tuple[Interaction, ...]],
    pairs: Sequence[PairRow],
) -> Mapping[str, np.ndarray]:
    maximum_events = max(len(events[user_id]) for user_id in user_ids)
    event_items = np.full((len(user_ids), maximum_events), -1, dtype=np.int32)
    event_movie_ids = np.full((len(user_ids), maximum_events), -1, dtype=np.int32)
    event_ratings = np.full((len(user_ids), maximum_events), np.nan, dtype=np.float32)
    event_timestamps = np.full((len(user_ids), maximum_events), -1, dtype=np.int64)
    event_ordinals = np.full((len(user_ids), maximum_events), -1, dtype=np.int64)
    event_counts = np.zeros(len(user_ids), dtype=np.int16)
    user_to_row = {int(user_id): row for row, user_id in enumerate(user_ids)}
    for user_id in user_ids:
        row = user_to_row[int(user_id)]
        values = events[int(user_id)]
        event_counts[row] = len(values)
        event_items[row, : len(values)] = [event.item_index for event in values]
        event_movie_ids[row, : len(values)] = [event.movie_id for event in values]
        event_ratings[row, : len(values)] = [event.rating for event in values]
        event_timestamps[row, : len(values)] = [event.timestamp for event in values]
        event_ordinals[row, : len(values)] = [event.ordinal for event in values]
    maximum_pairs = int(LOCKED_CONFIG["dataset"]["maximum_pairs_per_user"])
    pair_preferred = np.full((len(user_ids), maximum_pairs), -1, dtype=np.int32)
    pair_rejected = np.full_like(pair_preferred, -1)
    pair_low_movie_ids = np.full_like(pair_preferred, -1)
    pair_high_movie_ids = np.full_like(pair_preferred, -1)
    pair_counts = np.zeros(len(user_ids), dtype=np.int16)
    by_user = _user_stage_pairs(pairs)
    for user_id, rows in by_user.items():
        user_row = user_to_row[user_id]
        if len(rows) > maximum_pairs:
            raise IntegrityError("Fixed evaluation pair cap exceeded")
        pair_counts[user_row] = len(rows)
        pair_preferred[user_row, : len(rows)] = [pair.preferred for pair in rows]
        pair_rejected[user_row, : len(rows)] = [pair.rejected for pair in rows]
        pair_low_movie_ids[user_row, : len(rows)] = [pair.low_movie_id for pair in rows]
        pair_high_movie_ids[user_row, : len(rows)] = [pair.high_movie_id for pair in rows]
    return {
        "event_items": event_items,
        "event_movie_ids": event_movie_ids,
        "event_ratings": event_ratings,
        "event_timestamps": event_timestamps,
        "event_ordinals": event_ordinals,
        "event_counts": event_counts,
        "pair_preferred": pair_preferred,
        "pair_rejected": pair_rejected,
        "pair_low_movie_ids": pair_low_movie_ids,
        "pair_high_movie_ids": pair_high_movie_ids,
        "pair_counts": pair_counts,
    }


def _nanmean_seed(values: np.ndarray) -> np.ndarray:
    finite_count = np.sum(np.isfinite(values), axis=0)
    total = np.nansum(values, axis=0)
    result = np.full(total.shape, np.nan, dtype=np.float64)
    np.divide(total, finite_count, out=result, where=finite_count > 0)
    return result


def _finite_mean(values: np.ndarray) -> float:
    """Mean of finite cells, or a conservative finite zero for failed support."""
    array = np.asarray(values, dtype=np.float64)
    finite = array[np.isfinite(array)]
    return float(np.mean(finite)) if len(finite) else 0.0


def compute_gates(
    test_metrics: np.ndarray,
    test_diagnostics: Sequence[Mapping[str, Any]],
    R_diagnostics: Mapping[str, Any],
    power: Mapping[str, Any],
    latency: Mapping[str, Any],
    stronger_relevance_method: str,
    g1_invariants: Mapping[str, bool],
) -> tuple[Mapping[str, bool], Mapping[str, Any]]:
    metric_index = {name: index for index, name in enumerate(METRICS)}
    method_index = {name: index for index, name in enumerate(METHODS)}
    averaged = _nanmean_seed(test_metrics)
    bootstrap_records: dict[str, Mapping[str, Any]] = {}

    def comparison(metric: str, left: str, right: str, seed_offset: int) -> Mapping[str, Any]:
        key = f"{metric}:{left}-minus-{right}"
        del seed_offset
        left_values = averaged[method_index[left], :, metric_index[metric]]
        right_values = averaged[method_index[right], :, metric_index[metric]]
        common = np.isfinite(left_values) & np.isfinite(right_values)
        if not np.any(common):
            # Differences are bounded in [-1, 1].  This finite sentinel makes
            # every affected threshold fail and remains JSON-replayable.
            result = {
                "point": 0.0,
                "lower": -1.0,
                "upper": 1.0,
                "users": 0,
                "support_failed": True,
            }
        else:
            result = {
                **paired_bootstrap(
                    left_values,
                    right_values,
                    seed=int(LOCKED_CONFIG["bootstrap"]["seed"]),
                ),
                "support_failed": False,
            }
        bootstrap_records[key] = result
        return result

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
    metric_support_complete = bool(
        all(
            np.any(
                np.isfinite(
                    averaged[method_index[method], :, metric_index[metric]]
                )
            )
            for method, metric in required_metric_series
        )
    )

    admission_raw = comparison("conditional_admission_at_200", "cable_pref", "raw_hybrid", 0)
    admission_order = comparison("conditional_admission_at_200", "cable_pref", "order_only", 1)
    net_support = comparison("net_new_preferred_support", "cable_pref", "raw_hybrid", 2)
    net_advantage = comparison("net_admission_advantage", "cable_pref", "raw_hybrid", 3)
    spce_raw = comparison("spce_at_10", "cable_pref", "raw_hybrid", 4)
    spce_bpr = comparison("spce_at_10", "cable_pref", "bpr", 5)
    preferred_exposure = comparison("preferred_exposure_at_10", "cable_pref", "raw_hybrid", 6)
    ndcg = comparison("ndcg_at_10", "cable_pref", stronger_relevance_method, 7)
    recall = comparison("recall_at_10", "cable_pref", stronger_relevance_method, 8)
    intrusion = comparison("low_rating_intrusion_at_10", "cable_pref", "raw_hybrid", 9)

    gate_config = LOCKED_CONFIG["gates"]
    g1 = bool(all(g1_invariants.values()))
    g2 = bool(
        admission_raw["point"] >= float(gate_config["admission_raw_gain"])
        and admission_raw["lower"] > 0.0
        and admission_order["point"] >= float(gate_config["admission_order_gain"])
        and admission_order["lower"] > 0.0
        and net_support["point"] >= float(gate_config["net_support_raw_gain"])
        and net_support["lower"] > 0.0
        and net_advantage["point"] > 0.0
    )
    g3 = bool(
        spce_raw["point"] >= float(gate_config["spce_gain"])
        and spce_raw["lower"] > 0.0
        and spce_bpr["point"] >= float(gate_config["spce_gain"])
        and spce_bpr["lower"] > 0.0
        and preferred_exposure["point"] > 0.0
    )
    g4 = bool(
        ndcg["point"] >= float(gate_config["ndcg_point_floor"])
        and ndcg["lower"] > float(gate_config["ndcg_lower_strict"])
        and recall["lower"] > float(gate_config["recall_lower_strict"])
        and intrusion["upper"] <= float(gate_config["intrusion_upper"])
    )
    cable_admission_point = _finite_mean(
        averaged[4, :, metric_index["conditional_admission_at_200"]]
    )
    cable_spce_point = _finite_mean(averaged[4, :, metric_index["spce_at_10"]])
    g5 = bool(
        metric_support_complete
        and all(
            cable_admission_point
            > _finite_mean(
                averaged[
                    method_index[name], :, metric_index["conditional_admission_at_200"]
                ]
            )
            for name in ("order_only", "uib_boundary", "wrong_boundary", "shuffled_direction")
        )
        and all(
            cable_spce_point
            > _finite_mean(averaged[method_index[name], :, metric_index["spce_at_10"]])
            for name in ("admission_only", "order_only", "uib_boundary", "wrong_boundary", "shuffled_direction")
        )
    )
    first_diagnostic = test_diagnostics[0]
    admission_changed = sum(int(value["admission_changed_count"]) for value in test_diagnostics)
    admission_total = sum(int(value["admission_total"]) for value in test_diagnostics)
    spce_changed = sum(int(value["spce_changed_count"]) for value in test_diagnostics)
    spce_total = sum(int(value["spce_total"]) for value in test_diagnostics)
    support = LOCKED_CONFIG["support"]
    g6 = bool(
        int(R_diagnostics["selected_pairs"]) >= int(support["minimum_R_pairs"])
        and int(R_diagnostics["selected_pair_users"]) >= int(support["minimum_R_pair_users"])
        and int(first_diagnostic["fixed_pairs"]) >= int(support["minimum_T_pairs"])
        and int(first_diagnostic["pair_users"]) >= int(support["minimum_T_pair_users"])
        and int(first_diagnostic["unique_bpr_missed_preferred_endpoints"]) >= int(support["minimum_T_missed_preferred"])
        and int(first_diagnostic["missed_endpoint_users"]) >= int(support["minimum_T_missed_users"])
        and admission_total > 0
        and admission_changed / admission_total >= float(support["minimum_admission_change_fraction"])
        and spce_total > 0
        and spce_changed / spce_total >= float(support["minimum_spce_change_fraction"])
        and bool(power["passed"])
    )
    stable = 0
    seed_records: list[Mapping[str, Any]] = []
    for seed_row, seed in enumerate(SEEDS):
        seed_values = test_metrics[seed_row]
        admission_vs_raw = _finite_mean(
            seed_values[4, :, metric_index["conditional_admission_at_200"]]
            - seed_values[1, :, metric_index["conditional_admission_at_200"]]
        )
        admission_vs_order = _finite_mean(
            seed_values[4, :, metric_index["conditional_admission_at_200"]]
            - seed_values[2, :, metric_index["conditional_admission_at_200"]]
        )
        spce_vs_raw_seed = _finite_mean(
            seed_values[4, :, metric_index["spce_at_10"]]
            - seed_values[1, :, metric_index["spce_at_10"]]
        )
        ndcg_vs_raw_seed = _finite_mean(
            seed_values[4, :, metric_index["ndcg_at_10"]]
            - seed_values[1, :, metric_index["ndcg_at_10"]]
        )
        passed = bool(
            admission_vs_raw > 0.0
            and admission_vs_order > 0.0
            and spce_vs_raw_seed > 0.0
            and ndcg_vs_raw_seed >= float(gate_config["ndcg_point_floor"])
        )
        stable += int(passed)
        seed_records.append(
            {
                "seed": seed,
                "admission_vs_raw": admission_vs_raw,
                "admission_vs_order": admission_vs_order,
                "spce_vs_raw": spce_vs_raw_seed,
                "ndcg_vs_raw": ndcg_vs_raw_seed,
                "stable": passed,
            }
        )
    g7 = bool(
        metric_support_complete
        and stable >= int(gate_config["minimum_stable_seeds"])
        and all(record["ndcg_vs_raw"] >= float(gate_config["per_seed_ndcg_floor"]) for record in seed_records)
    )
    g8 = bool(latency.get("passed", False))
    # This producer-side bit means only that the runner reached its provenance
    # handoff.  The top-level runner verdict remains non-authoritative and
    # PROMISING=false; the post-exit verifier alone establishes external G9.
    g9 = True
    gates = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6, "G7": g7, "G8": g8, "G9": g9}
    details = {
        "bootstrap": bootstrap_records,
        "seed_stability": seed_records,
        "support": {
            "R": dict(R_diagnostics),
            "T": dict(first_diagnostic),
            "admission_change_fraction": admission_changed / max(1, admission_total),
            "spce_change_fraction": spce_changed / max(1, spce_total),
        },
        "power": power,
        "latency": latency,
        "G1_invariants": dict(g1_invariants),
        "stronger_relevance_method": stronger_relevance_method,
        "required_metric_support_complete": metric_support_complete,
        "runner_G9_scope": "producer_handoff_only_external_G9_pending",
    }
    return gates, details


def replay_action_consistency(
    manifests: Mapping[int, StageManifest],
    pairs: Sequence[PairRow],
    semantic_vectors: np.ndarray,
    movie_ids: np.ndarray,
) -> Mapping[str, Any]:
    pairs_by_user = _user_stage_pairs(pairs)
    checked = 0
    violations = 0
    tie_boundaries = 0
    for seed in SEEDS:
        manifest = manifests[seed]
        for user_row, raw_user_id in enumerate(manifest.user_ids):
            user_id = int(raw_user_id)
            preferred = sorted({pair.preferred for pair in pairs_by_user.get(user_id, tuple())})
            if not preferred:
                continue
            history = set(
                map(int, manifest.history_items[user_row, : int(manifest.history_counts[user_row])])
            )
            bpr_items = set(map(int, manifest.candidates[0, user_row, :200]))
            eligible = np.ones(len(movie_ids), dtype=np.bool_)
            eligible[list(history | bpr_items)] = False
            query = manifest.semantic_queries[4, user_row]
            scores = np.asarray(semantic_vectors @ query, dtype=np.float32)
            selected = set(map(int, manifest.candidates[4, user_row, 200:400]))
            active_preferred = [endpoint for endpoint in preferred if eligible[endpoint]]
            boundaries = leaveout_boundaries_from_base_topk(
                scores, eligible, active_preferred, movie_ids, 200
            )
            for endpoint in preferred:
                if not eligible[endpoint]:
                    continue
                boundary = boundaries[endpoint]
                expected = admission_from_boundary_key(scores, endpoint, boundary, movie_ids)
                actual = endpoint in selected
                checked += 1
                violations += int(expected != actual)
                tie_boundaries += int(scores[endpoint] == scores[boundary])
    return {
        "checked": checked,
        "violations": violations,
        "tie_boundaries": tie_boundaries,
        "passed": bool(checked > 0 and violations == 0),
    }


def measure_latency(
    user_ids: Sequence[int],
    histories: Mapping[int, tuple[Interaction, ...]],
    models_by_seed: Mapping[int, Mapping[str, Any]],
    bpr: BPRArtifacts,
    bpr_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    movie_ids: np.ndarray,
    selected_alpha: float,
) -> tuple[np.ndarray, Mapping[str, Any]]:
    config = LOCKED_CONFIG["latency"]
    selected = sorted(
        user_ids,
        key=lambda user_id: (
            hashlib.sha256(str(config["request_hash"]).format(user_id=user_id).encode("ascii")).hexdigest(),
            user_id,
        ),
    )[: int(config["requests"])]
    if len(selected) != int(config["requests"]):
        raise IntegrityError("Latency cohort has fewer than 512 requests")
    durations = np.zeros((len(SEEDS), 2, len(selected), int(config["repetitions"])), dtype=np.float64)

    def invoke(user_id: int, model: Any | None) -> None:
        history = histories[user_id]
        context = build_request_context(
            user_id,
            history,
            bpr,
            bpr_index,
            semantic_vectors,
            movie_ids,
            verify_oracle=False,
        )
        query, _boundary = apply_adapter_numpy(context.descriptor, model)
        retrieve_hybrid(
            context,
            query,
            bpr,
            semantic_vectors,
            semantic_index,
            movie_ids,
            selected_alpha,
            verify_oracle=False,
        )

    for seed_row, seed in enumerate(SEEDS):
        cable = models_by_seed[seed]["cable_pref"]
        for user_id in selected[: int(config["warmups"])]:
            invoke(user_id, None)
            invoke(user_id, cable)
        for user_row, user_id in enumerate(selected):
            for repetition in range(int(config["repetitions"])):
                order = (0, 1) if (user_row + repetition + seed_row) % 2 == 0 else (1, 0)
                for method_row in order:
                    start = time.perf_counter_ns()
                    invoke(user_id, None if method_row == 0 else cable)
                    durations[seed_row, method_row, user_row, repetition] = (
                        time.perf_counter_ns() - start
                    ) / 1_000_000.0
    per_request = np.median(durations, axis=3)
    p95 = np.quantile(per_request, 0.95, axis=2, method="higher")
    p99 = np.quantile(per_request, 0.99, axis=2, method="higher")
    ratios = p95[:, 1] / np.maximum(p95[:, 0], 1.0e-12)
    worst_p95 = float(np.max(p95[:, 1]))
    worst_ratio = float(np.max(ratios))
    summary = {
        "user_ids": selected,
        "p95_ms_by_seed_method": p95.tolist(),
        "p99_ms_by_seed_method": p99.tolist(),
        "p95_ratio_by_seed": ratios.tolist(),
        "worst_cable_p95_ms": worst_p95,
        "worst_p95_ratio": worst_ratio,
        "passed": bool(
            worst_p95 <= float(config["maximum_p95_ms"])
            and worst_ratio <= float(config["maximum_p95_ratio"])
        ),
    }
    return durations, summary


def array_memory_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(canonical_json_bytes(list(value.shape)))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def npy_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(array), allow_pickle=False)
    return buffer.getvalue()


def publish_npy(path: Path, array: np.ndarray) -> str:
    publish_bytes_no_overwrite(path, npy_bytes(array))
    return sha256_file(path)


def publish_torch_state(path: Path, state: Mapping[str, Any]) -> str:
    torch, _nn, _functional = _torch_imports()
    buffer = io.BytesIO()
    torch.save(dict(state), buffer)
    publish_bytes_no_overwrite(path, buffer.getvalue())
    return sha256_file(path)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise IntegrityError(f"Artifact escapes run directory: {path}") from exc


def recursive_file_hashes(root: Path, excluded: Iterable[Path] = ()) -> Mapping[str, str]:
    excluded_resolved = {path.resolve() for path in excluded}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        if path.is_symlink():
            raise IntegrityError(f"Symlink forbidden in run closure: {path}")
        if path.is_file() and path.resolve() not in excluded_resolved:
            result[safe_relative(path, root)] = sha256_file(path)
    return result


def source_path_inventory(config_path: Path, protocol_path: Path) -> Mapping[str, Path]:
    runner = Path(__file__).resolve()
    project_root = runner.parent.parent
    expected_config = (project_root / "src" / "configs" / "cable_pref_poc_ml10m_v1.json").resolve()
    expected_protocol = (project_root / "experiments" / "cable-pref-protocol-v1.md").resolve()
    if config_path.resolve() != expected_config or protocol_path.resolve() != expected_protocol:
        raise IntegrityError("Runner requires the source-bound registered config and protocol paths")
    paths = {
        "runner": runner,
        "config": expected_config,
        "protocol": expected_protocol,
        "research_question": (project_root / "literature" / "research-question-cycle5.md").resolve(),
        "cycle5_survey": (project_root / "literature" / "cycle5-survey-and-ideation.md").resolve(),
        "architecture": (project_root / "literature" / "cable-pref-architecture.md").resolve(),
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise IntegrityError(f"Required source files are missing: {missing}")
    return paths


def make_protocol_fingerprint(
    external_config: Mapping[str, Any], source_hashes: Mapping[str, str]
) -> tuple[str, Mapping[str, Any]]:
    payload = {
        "schema": "cable-pref-protocol-fingerprint-v1",
        "protocol_name": external_config["protocol_name"],
        "source_sha256": dict(source_hashes),
    }
    return sha256_bytes(canonical_json_bytes(payload)), payload


def package_versions() -> Mapping[str, str]:
    versions: dict[str, str] = {}
    for distribution in ("numpy", "torch", "faiss-cpu", "sentence-transformers"):
        try:
            versions[distribution] = importlib_metadata.version(distribution)
        except importlib_metadata.PackageNotFoundError:
            versions[distribution] = "MISSING"
    return versions


def environment_sha256(values: Mapping[str, str]) -> str:
    return sha256_bytes(canonical_json_bytes(dict(values)))


def make_execution_fingerprint(
    protocol_fingerprint: str,
    user_ids: Sequence[int],
    fixed_environment: Mapping[str, str],
) -> tuple[str, Mapping[str, Any]]:
    executable = Path(sys.executable).resolve()
    if not executable.is_file():
        raise IntegrityError("Python executable cannot be source-bound")
    payload = {
        "schema": "cable-pref-execution-fingerprint-v1",
        "protocol_fingerprint_sha256": protocol_fingerprint,
        "dataset_archive_sha256": ARCHIVE_SHA256,
        "cohort_user_ids_sha256": sha256_bytes(
            canonical_json_bytes(list(map(int, user_ids)))
        ),
        "optimization_seeds": list(SEEDS),
        "python_executable_sha256": sha256_file(executable),
        "environment_sha256": environment_sha256(fixed_environment),
    }
    return sha256_bytes(canonical_json_bytes(payload)), payload


def make_environment_record(
    fixed_environment: Mapping[str, str],
    source_hashes: Mapping[str, str],
    protocol_fingerprint: str,
    protocol_payload: Mapping[str, Any],
    execution_fingerprint: str,
    execution_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    executable = Path(sys.executable).resolve()
    return {
        "schema": "cable-pref-environment-v1",
        "created_utc": utc_now(),
        "python_executable": str(executable),
        "python_executable_sha256": sha256_file(executable),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "package_versions": dict(package_versions()),
        "fixed_environment": dict(fixed_environment),
        "fixed_environment_sha256": environment_sha256(fixed_environment),
        "source_sha256": dict(source_hashes),
        "dataset_archive_sha256": ARCHIVE_SHA256,
        "protocol_fingerprint_sha256": protocol_fingerprint,
        "protocol_fingerprint_payload": dict(protocol_payload),
        "execution_fingerprint_sha256": execution_fingerprint,
        "execution_fingerprint_payload": dict(execution_payload),
    }


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
                        arguments.exc_type, arguments.exc_value, arguments.exc_traceback
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


def acquire_runner_lock(path: Path) -> str:
    token = os.urandom(32).hex()
    publish_json(
        path,
        {
            "schema": "cable-pref-exclusive-owner-lock-v1",
            "role": "outcome-runner",
            "pid": os.getpid(),
            "token_sha256": sha256_bytes(token.encode("ascii")),
            "created_utc": utc_now(),
        },
    )
    return token


def release_runner_lock(path: Path, token: str) -> None:
    if not path.is_file():
        raise IntegrityError("Runner lock disappeared before release")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("schema") != "cable-pref-exclusive-owner-lock-v1"
        or int(record.get("pid", -1)) != os.getpid()
        or record.get("token_sha256") != sha256_bytes(token.encode("ascii"))
    ):
        raise IntegrityError("Runner lock ownership changed")
    path.unlink()


def choose_stronger_relevance_method(
    manifests: Mapping[int, StageManifest],
    V_binary: Mapping[int, tuple[Interaction, ...]],
    movie_ids: np.ndarray,
    selected_alpha_index: int,
) -> tuple[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, float]] = {}
    for name, method_index in (("raw_hybrid", 1), ("bpr", 0)):
        ndcg_seeds: list[float] = []
        recall_seeds: list[float] = []
        for seed in SEEDS:
            manifest = manifests[seed]
            ndcg_users: list[float] = []
            recall_users: list[float] = []
            for user_row, raw_user_id in enumerate(manifest.user_ids):
                positives = {
                    event.item_index
                    for event in V_binary[int(raw_user_id)]
                    if event.rating >= float(LOCKED_CONFIG["dataset"]["positive_rating_min"])
                }
                if not positives:
                    continue
                ranking = _selected_ranking(
                    manifest, method_index, user_row, selected_alpha_index, movie_ids
                )[:10]
                discounts = 1.0 / np.log2(np.arange(2, 12, dtype=np.float64))
                gains = np.asarray([item in positives for item in ranking], dtype=np.float64)
                ideal = float(np.sum(discounts[: min(10, len(positives))]))
                ndcg_users.append(float(np.sum(gains * discounts)) / ideal)
                recall_users.append(sum(item in positives for item in ranking) / len(positives))
            if not ndcg_users or not recall_users:
                raise IntegrityError(
                    "Validation relevance has no positive-bearing users for comparator selection"
                )
            ndcg_seeds.append(float(np.mean(ndcg_users)))
            recall_seeds.append(float(np.mean(recall_users)))
        records[name] = {
            "ndcg": float(np.mean(ndcg_seeds)),
            "recall": float(np.mean(recall_seeds)),
        }
    # The registered final tie-break chooses BPR.
    selected = max(
        ("raw_hybrid", "bpr"),
        key=lambda name: (
            records[name]["ndcg"],
            records[name]["recall"],
            int(name == "bpr"),
        ),
    )
    return selected, {"candidates": records, "selected": selected}


def publish_stage_manifests(
    output_dir: Path,
    stage: str,
    manifests: Mapping[int, StageManifest],
    protocol_fingerprint: str,
    execution_fingerprint: str,
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    files: list[str] = []
    hashes: list[str] = []
    for seed in SEEDS:
        path = output_dir / "manifests" / f"{stage}_target_blind_seed_{seed}.npz"
        digest = publish_npz(
            path,
            **manifest_npz_arrays(
                manifests[seed], protocol_fingerprint, execution_fingerprint
            ),
        )
        files.append(safe_relative(path, output_dir))
        hashes.append(digest)
    return tuple(files), tuple(hashes), utc_now()


def immutable_reference_arrays(
    output_dir: Path,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    bpr: BPRArtifacts,
    bpr_index: Any,
) -> tuple[Mapping[str, Mapping[str, str]], Mapping[str, Any]]:
    artifact_dir = output_dir / "immutable"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    specifications = {
        "semantic_matrix": (artifact_dir / "semantic_vectors.npy", npy_bytes(semantic_vectors)),
        "semantic_index": (artifact_dir / "semantic_index.faiss", serialize_faiss(semantic_index)),
        "bpr_item_matrix": (artifact_dir / "bpr_item_vectors.npy", npy_bytes(bpr.item_vectors)),
        "bpr_user_matrix": (artifact_dir / "bpr_user_vectors.npy", npy_bytes(bpr.user_vectors)),
        "collaborative_mask": (artifact_dir / "collaborative_mask.npy", npy_bytes(bpr.collaborative_mask)),
        "bpr_index": (artifact_dir / "bpr_index.faiss", serialize_faiss(bpr_index)),
    }
    records: dict[str, Mapping[str, str]] = {}
    for name, (path, payload) in specifications.items():
        publish_bytes_no_overwrite(path, payload)
        memory_digest = (
            sha256_bytes(payload)
            if name.endswith("index")
            else array_memory_sha256(
                {
                    "semantic_matrix": semantic_vectors,
                    "bpr_item_matrix": bpr.item_vectors,
                    "bpr_user_matrix": bpr.user_vectors,
                    "collaborative_mask": bpr.collaborative_mask,
                }[name]
            )
        )
        records[name] = {
            "file": safe_relative(path, output_dir),
            "file_sha256_before": sha256_file(path),
            "memory_sha256_before": memory_digest,
        }
    handles = {
        "semantic_matrix": semantic_vectors,
        "semantic_index": semantic_index,
        "bpr_item_matrix": bpr.item_vectors,
        "bpr_user_matrix": bpr.user_vectors,
        "collaborative_mask": bpr.collaborative_mask,
        "bpr_index": bpr_index,
    }
    return records, handles


def finalize_immutable_records(
    output_dir: Path,
    before: Mapping[str, Mapping[str, str]],
    handles: Mapping[str, Any],
) -> Mapping[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for name, initial in before.items():
        path = output_dir / initial["file"]
        memory_after = (
            sha256_bytes(serialize_faiss(handles[name]))
            if name.endswith("index")
            else array_memory_sha256(handles[name])
        )
        file_after = sha256_file(path)
        result[name] = {
            **dict(initial),
            "file_sha256_after": file_after,
            "memory_sha256_after": memory_after,
            "unchanged": bool(
                file_after == initial["file_sha256_before"]
                and memory_after == initial["memory_sha256_before"]
            ),
        }
    return result


def immutable_npz_bindings(
    records: Mapping[str, Mapping[str, str]],
) -> Mapping[str, np.ndarray]:
    return {
        "semantic_matrix_file": np.asarray([records["semantic_matrix"]["file"]], dtype="U160"),
        "semantic_matrix_sha256": np.asarray(
            [records["semantic_matrix"]["file_sha256_before"]], dtype="U64"
        ),
        "semantic_index_file": np.asarray([records["semantic_index"]["file"]], dtype="U160"),
        "semantic_index_sha256": np.asarray(
            [records["semantic_index"]["file_sha256_before"]], dtype="U64"
        ),
        "bpr_item_matrix_file": np.asarray([records["bpr_item_matrix"]["file"]], dtype="U160"),
        "bpr_item_matrix_sha256": np.asarray(
            [records["bpr_item_matrix"]["file_sha256_before"]], dtype="U64"
        ),
        "bpr_index_file": np.asarray([records["bpr_index"]["file"]], dtype="U160"),
        "bpr_index_sha256": np.asarray(
            [records["bpr_index"]["file_sha256_before"]], dtype="U64"
        ),
        "collaborative_mask_file": np.asarray(
            [records["collaborative_mask"]["file"]], dtype="U160"
        ),
        "collaborative_mask_sha256": np.asarray(
            [records["collaborative_mask"]["file_sha256_before"]], dtype="U64"
        ),
    }


def validation_raw_arrays(
    *,
    protocol_fingerprint: str,
    execution_fingerprint: str,
    user_ids: Sequence[int],
    movie_ids: np.ndarray,
    metrics: np.ndarray,
    selected_alpha_index: int,
    selected_alpha: float,
    stronger_relevance_method: str,
    power: Mapping[str, Any],
    manifest_files: Sequence[str],
    manifest_hashes: Sequence[str],
    immutable_records: Mapping[str, Mapping[str, str]],
    R_outcome_arrays: Mapping[str, np.ndarray],
    outcome_arrays: Mapping[str, np.ndarray],
    R_diagnostics: Mapping[str, Any],
    V_diagnostics: Sequence[Mapping[str, Any]],
    V_pair_diagnostics: Mapping[str, Any],
    training_diagnostics: Mapping[int, Mapping[str, Mapping[str, Any]]],
    initial_hashes: Mapping[int, str],
    final_hashes: Mapping[int, Mapping[str, str]],
    timestamps: Mapping[str, str],
) -> Mapping[str, np.ndarray]:
    comparison_names = (
        "admission_vs_raw",
        "admission_vs_order_only",
        "spce_vs_raw",
        "spce_vs_bpr",
    )
    training_methods = tuple(TRAINED_METHODS)
    arrays: dict[str, np.ndarray] = {
        "schema": np.asarray(["cable-pref-raw-validation-v1"], dtype="U48"),
        "protocol_fingerprint_sha256": np.asarray([protocol_fingerprint], dtype="U64"),
        "execution_fingerprint_sha256": np.asarray([execution_fingerprint], dtype="U64"),
        "methods": np.asarray(METHODS, dtype="U32"),
        "seeds": np.asarray(SEEDS, dtype=np.int64),
        "metrics": np.asarray(METRICS, dtype="U48"),
        "alphas": np.asarray(ALPHAS, dtype=np.float32),
        "user_ids": np.asarray(user_ids, dtype=np.int64),
        "catalog_movie_ids": np.asarray(movie_ids, dtype=np.int64),
        "per_user_metrics": np.asarray(metrics, dtype=np.float64),
        "selected_alpha_index": np.asarray([selected_alpha_index], dtype=np.int16),
        "selected_alpha": np.asarray([selected_alpha], dtype=np.float32),
        "stronger_relevance_method": np.asarray([stronger_relevance_method], dtype="U32"),
        "power_comparison_names": np.asarray(comparison_names, dtype="U40"),
        "power_detection_fractions": np.asarray(
            [power["comparisons"][name]["detection_fraction"] for name in comparison_names],
            dtype=np.float64,
        ),
        "power_passed": np.asarray([power["passed"]], dtype=np.uint8),
        "V_manifest_files": np.asarray(manifest_files, dtype="U160"),
        "V_manifest_sha256": np.asarray(manifest_hashes, dtype="U64"),
        "V_pair_identity_sha256": np.asarray(
            [V_pair_diagnostics["pair_identity_sha256"]], dtype="U64"
        ),
        "R_pair_identity_sha256": np.asarray(
            [R_diagnostics["pair_identity_sha256"]], dtype="U64"
        ),
        "R_selected_pairs": np.asarray([R_diagnostics["selected_pairs"]], dtype=np.int64),
        "R_selected_pair_users": np.asarray(
            [R_diagnostics["selected_pair_users"]], dtype=np.int64
        ),
        "V_fixed_pairs": np.asarray([V_diagnostics[0]["fixed_pairs"]], dtype=np.int64),
        "V_pair_users": np.asarray([V_diagnostics[0]["pair_users"]], dtype=np.int64),
        "V_unique_bpr_missed_preferred_endpoints": np.asarray(
            [V_diagnostics[0]["unique_bpr_missed_preferred_endpoints"]], dtype=np.int64
        ),
        "V_missed_endpoint_users": np.asarray(
            [V_diagnostics[0]["missed_endpoint_users"]], dtype=np.int64
        ),
        "V_admission_changed_count_by_seed": np.asarray(
            [value["admission_changed_count"] for value in V_diagnostics], dtype=np.int64
        ),
        "V_admission_total_by_seed": np.asarray(
            [value["admission_total"] for value in V_diagnostics], dtype=np.int64
        ),
        "V_spce_changed_count_by_seed": np.asarray(
            [value["spce_changed_count"] for value in V_diagnostics], dtype=np.int64
        ),
        "V_spce_total_by_seed": np.asarray(
            [value["spce_total"] for value in V_diagnostics], dtype=np.int64
        ),
        "training_methods": np.asarray(training_methods, dtype="U32"),
        "training_optimizer_steps": np.asarray(
            [[training_diagnostics[seed][name]["optimizer_steps"] for name in training_methods]
             for seed in SEEDS],
            dtype=np.int64,
        ),
        "training_pair_presentations": np.asarray(
            [[training_diagnostics[seed][name]["pair_presentations"] for name in training_methods]
             for seed in SEEDS],
            dtype=np.int64,
        ),
        "training_admission_presentations": np.asarray(
            [[training_diagnostics[seed][name]["admission_presentations"] for name in training_methods]
             for seed in SEEDS],
            dtype=np.int64,
        ),
        "adapter_initial_memory_sha256": np.asarray(
            [initial_hashes[seed] for seed in SEEDS], dtype="U64"
        ),
        "adapter_final_memory_sha256": np.asarray(
            [[final_hashes[seed][name] for name in training_methods] for seed in SEEDS],
            dtype="U64",
        ),
        "V_manifest_published_utc": np.asarray([timestamps["manifest"]], dtype="U48"),
        "V_binary_relevance_opened_utc": np.asarray([timestamps["binary"]], dtype="U48"),
        "choices_frozen_utc": np.asarray([timestamps["choices"]], dtype="U48"),
        "V_exact_preference_opened_utc": np.asarray([timestamps["exact"]], dtype="U48"),
        "target_blind_before_binary_relevance": np.asarray(
            [timestamps["manifest"] <= timestamps["binary"]], dtype=np.uint8
        ),
        "choices_before_exact_preferences": np.asarray(
            [timestamps["choices"] <= timestamps["exact"]], dtype=np.uint8
        ),
    }
    arrays.update(immutable_npz_bindings(immutable_records))
    arrays.update({f"R_{name}": value for name, value in R_outcome_arrays.items()})
    arrays.update({f"V_{name}": value for name, value in outcome_arrays.items()})
    if set(arrays) != set(RAW_VALIDATION_FIELDS):
        raise IntegrityError(
            f"Raw validation schema drift: missing={sorted(set(RAW_VALIDATION_FIELDS)-set(arrays))}, "
            f"extra={sorted(set(arrays)-set(RAW_VALIDATION_FIELDS))}"
        )
    return arrays


def test_raw_arrays(
    *,
    protocol_fingerprint: str,
    execution_fingerprint: str,
    user_ids: Sequence[int],
    movie_ids: np.ndarray,
    metrics: np.ndarray,
    selected_alpha_index: int,
    selected_alpha: float,
    stronger_relevance_method: str,
    manifest_files: Sequence[str],
    manifest_hashes: Sequence[str],
    immutable_records: Mapping[str, Mapping[str, str]],
    outcome_arrays: Mapping[str, np.ndarray],
    pair_diagnostics: Mapping[str, Any],
    diagnostics: Sequence[Mapping[str, Any]],
    action: Mapping[str, Any],
    g1_invariants: Mapping[str, bool],
    gates: Mapping[str, bool],
    manifest_utc: str,
    opened_utc: str,
) -> Mapping[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {
        "schema": np.asarray(["cable-pref-raw-test-v1"], dtype="U48"),
        "protocol_fingerprint_sha256": np.asarray([protocol_fingerprint], dtype="U64"),
        "execution_fingerprint_sha256": np.asarray([execution_fingerprint], dtype="U64"),
        "methods": np.asarray(METHODS, dtype="U32"),
        "seeds": np.asarray(SEEDS, dtype=np.int64),
        "metrics": np.asarray(METRICS, dtype="U48"),
        "alphas": np.asarray(ALPHAS, dtype=np.float32),
        "user_ids": np.asarray(user_ids, dtype=np.int64),
        "catalog_movie_ids": np.asarray(movie_ids, dtype=np.int64),
        "per_user_metrics": np.asarray(metrics, dtype=np.float64),
        "selected_alpha_index": np.asarray([selected_alpha_index], dtype=np.int16),
        "selected_alpha": np.asarray([selected_alpha], dtype=np.float32),
        "stronger_relevance_method": np.asarray([stronger_relevance_method], dtype="U32"),
        "T_manifest_files": np.asarray(manifest_files, dtype="U160"),
        "T_manifest_sha256": np.asarray(manifest_hashes, dtype="U64"),
        "T_pair_identity_sha256": np.asarray(
            [pair_diagnostics["pair_identity_sha256"]], dtype="U64"
        ),
        "T_fixed_pairs": np.asarray([diagnostics[0]["fixed_pairs"]], dtype=np.int64),
        "T_pair_users": np.asarray([diagnostics[0]["pair_users"]], dtype=np.int64),
        "T_unique_bpr_missed_preferred_endpoints": np.asarray(
            [diagnostics[0]["unique_bpr_missed_preferred_endpoints"]], dtype=np.int64
        ),
        "T_missed_endpoint_users": np.asarray(
            [diagnostics[0]["missed_endpoint_users"]], dtype=np.int64
        ),
        "T_admission_changed_count_by_seed": np.asarray(
            [value["admission_changed_count"] for value in diagnostics], dtype=np.int64
        ),
        "T_admission_total_by_seed": np.asarray(
            [value["admission_total"] for value in diagnostics], dtype=np.int64
        ),
        "T_spce_changed_count_by_seed": np.asarray(
            [value["spce_changed_count"] for value in diagnostics], dtype=np.int64
        ),
        "T_spce_total_by_seed": np.asarray(
            [value["spce_total"] for value in diagnostics], dtype=np.int64
        ),
        "action_checked": np.asarray([action["checked"]], dtype=np.int64),
        "action_violations": np.asarray([action["violations"]], dtype=np.int64),
        "action_tie_boundaries": np.asarray([action["tie_boundaries"]], dtype=np.int64),
        "action_passed": np.asarray([action["passed"]], dtype=np.uint8),
        "g1_invariant_names": np.asarray(tuple(g1_invariants), dtype="U64"),
        "g1_invariant_values": np.asarray(tuple(g1_invariants.values()), dtype=np.uint8),
        "gate_names": np.asarray(tuple(gates), dtype="U4"),
        "gate_values": np.asarray(tuple(gates.values()), dtype=np.uint8),
        "T_manifest_published_utc": np.asarray([manifest_utc], dtype="U48"),
        "T_opened_utc": np.asarray([opened_utc], dtype="U48"),
        "test_opened": np.asarray([1], dtype=np.uint8),
    }
    arrays.update(immutable_npz_bindings(immutable_records))
    arrays.update({f"T_{name}": value for name, value in outcome_arrays.items()})
    if set(arrays) != set(RAW_TEST_FIELDS):
        raise IntegrityError(
            f"Raw test schema drift: missing={sorted(set(RAW_TEST_FIELDS)-set(arrays))}, "
            f"extra={sorted(set(arrays)-set(RAW_TEST_FIELDS))}"
        )
    return arrays


def latency_raw_arrays(
    *,
    protocol_fingerprint: str,
    execution_fingerprint: str,
    durations: np.ndarray,
    summary: Mapping[str, Any],
) -> Mapping[str, np.ndarray]:
    per_request = np.median(durations, axis=3)
    p95 = np.quantile(per_request, 0.95, axis=2, method="higher")
    p99 = np.quantile(per_request, 0.99, axis=2, method="higher")
    arrays = {
        "schema": np.asarray(["cable-pref-raw-latency-v1"], dtype="U48"),
        "protocol_fingerprint_sha256": np.asarray([protocol_fingerprint], dtype="U64"),
        "execution_fingerprint_sha256": np.asarray([execution_fingerprint], dtype="U64"),
        "seeds": np.asarray(SEEDS, dtype=np.int64),
        "methods": np.asarray(("raw_hybrid", "cable_pref"), dtype="U32"),
        "user_ids": np.asarray(summary["user_ids"], dtype=np.int64),
        "durations_ms": np.asarray(durations, dtype=np.float64),
        "per_request_median_ms": np.asarray(per_request, dtype=np.float64),
        "p95_ms": np.asarray(p95, dtype=np.float64),
        "p99_ms": np.asarray(p99, dtype=np.float64),
        "p95_ratio_by_seed": np.asarray(summary["p95_ratio_by_seed"], dtype=np.float64),
        "worst_cable_p95_ms": np.asarray([summary["worst_cable_p95_ms"]], dtype=np.float64),
        "worst_p95_ratio": np.asarray([summary["worst_p95_ratio"]], dtype=np.float64),
        "passed": np.asarray([summary["passed"]], dtype=np.uint8),
    }
    if set(arrays) != set(RAW_LATENCY_FIELDS):
        raise IntegrityError("Raw latency schema drift")
    return arrays


def manifest_exact_invariants(manifests: Mapping[int, StageManifest]) -> Mapping[str, bool]:
    exact_counts = True
    unique_unseen = True
    branch_disjoint = True
    shared_bpr = True
    oracle = True
    for seed in SEEDS:
        manifest = manifests[seed]
        oracle = oracle and bool(np.all(manifest.oracle_agreement == 1))
        for user_row in range(len(manifest.user_ids)):
            history = set(
                map(int, manifest.history_items[user_row, : int(manifest.history_counts[user_row])])
            )
            reference_bpr = tuple(map(int, manifest.candidates[0, user_row, :200]))
            exact_counts = exact_counts and len(reference_bpr) == 200
            unique_unseen = unique_unseen and len(set(reference_bpr)) == 200 and not (
                set(reference_bpr) & history
            )
            for method_index in range(1, len(METHODS)):
                union = tuple(map(int, manifest.candidates[method_index, user_row]))
                bpr_items, semantic_items = union[:200], union[200:]
                exact_counts = exact_counts and len(union) == 400
                unique_unseen = unique_unseen and len(set(union)) == 400 and not (
                    set(union) & history
                )
                branch_disjoint = branch_disjoint and not (set(bpr_items) & set(semantic_items))
                shared_bpr = shared_bpr and bpr_items == reference_bpr
    return {
        "exact_candidate_counts": bool(exact_counts),
        "unique_unseen_candidates": bool(unique_unseen),
        "semantic_branch_bpr_novel": bool(branch_disjoint),
        "shared_bpr_branch": bool(shared_bpr),
        "faiss_matrix_oracle_exact": bool(oracle),
    }


def publish_runner_candidate(
    *,
    output_dir: Path,
    runner_lock: Path,
    ledger: Path,
    source_hashes: Mapping[str, str],
    execution_fingerprint: str,
    termination_stage: str,
    test_opened: bool,
    result_path: Path,
    raw_validation_path: Path,
    raw_test_path: Path | None = None,
    latency_path: Path | None = None,
) -> Path:
    if ledger.stat().st_size != 0:
        raise IntegrityError("Runner asynchronous-error ledger is nonempty")
    candidate_path = output_dir / (
        f"CABLE_RUNNER_COMPLETE_CANDIDATE_{execution_fingerprint[:16]}.json"
    )
    artifacts = recursive_file_hashes(
        output_dir, excluded=(runner_lock, candidate_path)
    )
    candidate: dict[str, Any] = {
        "schema": "cable-pref-runner-completion-candidate-v1",
        "created_utc": utc_now(),
        "run_directory": str(output_dir.resolve()),
        "pid": os.getpid(),
        "runner_lock": safe_relative(runner_lock, output_dir),
        "runner_lock_release_pending": True,
        "external_post_exit_verification_required": True,
        "source_sha256": dict(source_hashes),
        "dataset_archive_sha256": ARCHIVE_SHA256,
        "execution_fingerprint_sha256": execution_fingerprint,
        "termination_stage": termination_stage,
        "test_opened": test_opened,
        "asynchronous_error_ledger": safe_relative(ledger, output_dir),
        "asynchronous_error_ledger_sha256": sha256_file(ledger),
        "artifact_sha256": artifacts,
        "result_file": safe_relative(result_path, output_dir),
        "result_sha256": sha256_file(result_path),
        "raw_validation_file": safe_relative(raw_validation_path, output_dir),
        "raw_validation_sha256": sha256_file(raw_validation_path),
    }
    if termination_stage == "post_T_all_gates":
        if raw_test_path is None or latency_path is None:
            raise IntegrityError("Post-T closure lacks test or latency arrays")
        candidate.update(
            {
                "raw_test_file": safe_relative(raw_test_path, output_dir),
                "raw_test_sha256": sha256_file(raw_test_path),
                "latency_file": safe_relative(latency_path, output_dir),
                "latency_sha256": sha256_file(latency_path),
            }
        )
    elif termination_stage != "pre_T_power_audit":
        raise IntegrityError("Unknown runner termination stage")
    publish_json(candidate_path, candidate)
    return candidate_path


def execute_authorized(
    *,
    config_path: Path,
    protocol_path: Path,
    output_dir: Path,
    archive_path: Path,
) -> Mapping[str, Any]:
    external_config = load_and_validate_external_config(config_path)
    try:
        protocol_text = protocol_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise IntegrityError("Cannot read the registered protocol as strict UTF-8") from exc
    if "CABLE-PREF" not in protocol_text or "G1" not in protocol_text or "G9" not in protocol_text:
        raise IntegrityError("Registered protocol content is incomplete")
    source_paths = source_path_inventory(config_path, protocol_path)
    source_hashes = {name: sha256_file(path) for name, path in source_paths.items()}
    fixed_environment = validate_execution_environment()
    archive_record = verify_archive_binding(archive_path.resolve())
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Run directory already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    runner_lock = output_dir / "runner.lock.json"
    lock_token = acquire_runner_lock(runner_lock)
    ledger = output_dir / "runner_async_errors.jsonl"
    publish_bytes_no_overwrite(ledger, b"")
    install_async_exception_hooks(ledger)
    candidate_published = False
    try:
        protocol_fingerprint, protocol_payload = make_protocol_fingerprint(
            external_config, source_hashes
        )
        with tempfile.TemporaryDirectory(prefix="cable-pref-input-") as temporary_name:
            extracted = safe_extract_allowed_inputs(
                archive_path.resolve(), Path(temporary_name) / "allowed", authorized=True
            )
            movies, movie_to_index = load_movies(extracted["movies.dat"])
            movie_ids = np.asarray([movie.movie_id for movie in movies], dtype=np.int64)

            # The structural pass freezes cohort membership and split structure.
            # Each later rescan parses selected users and only the authorized stage.
            user_ids, layouts, eligible_count, A = select_cohort_streaming(
                extracted["ratings.dat"], movie_to_index
            )
            selected_users = frozenset(user_ids)
            execution_fingerprint, execution_payload = make_execution_fingerprint(
                protocol_fingerprint, user_ids, fixed_environment
            )
            environment_record = make_environment_record(
                fixed_environment,
                source_hashes,
                protocol_fingerprint,
                protocol_payload,
                execution_fingerprint,
                execution_payload,
            )
            publish_json(output_dir / "environment.json", environment_record)
            publish_json(
                output_dir / "cohort.json",
                {
                    "schema": "cable-pref-cohort-v1",
                    "execution_fingerprint_sha256": execution_fingerprint,
                    "eligible_user_count": eligible_count,
                    "selected_user_count": len(user_ids),
                    "selected_user_ids": list(user_ids),
                    "selected_user_ids_sha256": execution_payload["cohort_user_ids_sha256"],
                    "layouts": {
                        str(user_id): dataclasses.asdict(layouts[user_id])
                        for user_id in user_ids
                    },
                    "ratings_loading_strategy": "one_structural_pass_plus_stage_authorized_rescans",
                },
            )

            semantic_vectors = encode_movies(movies)
            semantic_index = build_faiss_flat_ip(semantic_vectors)
            collaborative_mask = build_collaborative_mask(
                user_ids, A, len(movies)
            )
            bpr, bpr_state = train_bpr(
                user_ids, A, len(movies), collaborative_mask
            )
            semantic_vectors.setflags(write=False)
            bpr.user_vectors.setflags(write=False)
            bpr.item_vectors.setflags(write=False)
            bpr.collaborative_mask.setflags(write=False)
            bpr_index = build_faiss_flat_ip(bpr.item_vectors)
            immutable_before, immutable_handles = immutable_reference_arrays(
                output_dir, semantic_vectors, semantic_index, bpr, bpr_index
            )
            publish_torch_state(output_dir / "immutable" / "bpr_state.pt", bpr_state)
            publish_json(
                output_dir / "bpr_diagnostics.json",
                {
                    "schema": "cable-pref-bpr-diagnostics-v1",
                    "training_trace": list(bpr.training_trace),
                    "collaborative_catalog_items": int(np.sum(bpr.collaborative_mask)),
                    "unsupported_item_vectors_exact_zero": bool(
                        np.all(bpr.item_vectors[~bpr.collaborative_mask] == 0.0)
                    ),
                },
            )

            # R is not parsed until its complete A-prefix target-blind artifact is durable.
            R_contexts, R_blind_arrays = build_R_target_blind_arrays(
                user_ids,
                A,
                bpr,
                bpr_index,
                semantic_vectors,
                semantic_index,
                movie_ids,
                protocol_fingerprint,
                execution_fingerprint,
            )
            R_manifest_path = output_dir / "manifests" / "R_target_blind.npz"
            R_manifest_sha = publish_npz(R_manifest_path, **R_blind_arrays)
            R_manifest_utc = utc_now()
            R = load_selected_stage(
                extracted["ratings.dat"], selected_users, layouts, movie_to_index, "R"
            )
            R_opened_utc = utc_now()
            if R_manifest_utc > R_opened_utc:
                raise IntegrityError("R targets opened before target-blind manifest publication")
            assert_stage_items_disjoint(A, R, current_stage="R")
            R_pairs, R_diagnostics = natural_pairs(R, "R")
            R_support_passed = bool(
                int(R_diagnostics["selected_pairs"])
                >= int(LOCKED_CONFIG["support"]["minimum_R_pairs"])
                and int(R_diagnostics["selected_pair_users"])
                >= int(LOCKED_CONFIG["support"]["minimum_R_pair_users"])
            )
            if not R_support_passed:
                raise IntegrityError(
                    "Registered R pair support failed before training: "
                    f"pairs={int(R_diagnostics['selected_pairs'])}/"
                    f"{int(LOCKED_CONFIG['support']['minimum_R_pairs'])}, "
                    f"users={int(R_diagnostics['selected_pair_users'])}/"
                    f"{int(LOCKED_CONFIG['support']['minimum_R_pair_users'])}; "
                    "CABLE-PREF is killed"
                )

            checkpoint_dir = output_dir / "checkpoints"
            checkpoint_dir.mkdir(parents=True, exist_ok=False)
            models_by_seed: dict[int, dict[str, Any]] = {}
            training_diagnostics: dict[int, dict[str, Mapping[str, Any]]] = {}
            initial_hashes: dict[int, str] = {}
            final_hashes: dict[int, dict[str, str]] = {}
            checkpoint_records: dict[str, Mapping[str, Any]] = {}
            for seed in SEEDS:
                initial_model = new_adapter(seed)
                initial_state = adapter_state_copy(initial_model)
                initial_hashes[seed] = adapter_memory_sha256(initial_model)
                raw_path = checkpoint_dir / f"seed_{seed}_raw_hybrid_zero_adapter.pt"
                raw_sha = publish_torch_state(raw_path, initial_state)
                checkpoint_records[f"{seed}:raw_hybrid"] = {
                    "file": safe_relative(raw_path, output_dir),
                    "file_sha256": raw_sha,
                    "memory_sha256": initial_hashes[seed],
                    "trained": False,
                }
                models: dict[str, Any] = {"raw_hybrid": None}
                seed_diagnostics: dict[str, Mapping[str, Any]] = {}
                seed_final_hashes: dict[str, str] = {}
                for method in TRAINED_METHODS:
                    model, diagnostics, final_state = train_adapter_control(
                        method,
                        seed,
                        R_contexts,
                        R_pairs,
                        semantic_vectors,
                        movie_ids,
                        initial_state,
                    )
                    models[method] = model
                    seed_diagnostics[method] = diagnostics
                    seed_final_hashes[method] = adapter_memory_sha256(model)
                    checkpoint_path = checkpoint_dir / f"seed_{seed}_{method}.pt"
                    checkpoint_sha = publish_torch_state(checkpoint_path, final_state)
                    checkpoint_records[f"{seed}:{method}"] = {
                        "file": safe_relative(checkpoint_path, output_dir),
                        "file_sha256": checkpoint_sha,
                        "memory_sha256": seed_final_hashes[method],
                        "trained": True,
                    }
                if len({value["optimizer_steps"] for value in seed_diagnostics.values()}) != 1:
                    raise IntegrityError("Matched controls have unequal optimizer steps")
                if len({value["pair_presentations"] for value in seed_diagnostics.values()}) != 1:
                    raise IntegrityError("Matched controls have unequal pair presentations")
                models_by_seed[seed] = models
                training_diagnostics[seed] = seed_diagnostics
                final_hashes[seed] = seed_final_hashes
            publish_json(
                output_dir / "training_diagnostics.json",
                {
                    "schema": "cable-pref-training-diagnostics-v1",
                    "R_target_blind_manifest": safe_relative(R_manifest_path, output_dir),
                    "R_target_blind_manifest_sha256": R_manifest_sha,
                    "R_target_blind_manifest_published_utc": R_manifest_utc,
                    "R_opened_utc": R_opened_utc,
                    "R_pair_diagnostics": dict(R_diagnostics),
                    "initial_memory_sha256": initial_hashes,
                    "controls": training_diagnostics,
                    "checkpoints": checkpoint_records,
                },
            )

            V_histories = {
                user_id: stage_history(user_id, "V", A, R)
                for user_id in user_ids
            }
            V_manifests = {
                seed: build_stage_manifest(
                    "V",
                    seed,
                    user_ids,
                    V_histories,
                    models_by_seed[seed],
                    bpr,
                    bpr_index,
                    semantic_vectors,
                    semantic_index,
                    movie_ids,
                )
                for seed in SEEDS
            }
            V_manifest_files, V_manifest_hashes, V_manifest_utc = publish_stage_manifests(
                output_dir,
                "V",
                V_manifests,
                protocol_fingerprint,
                execution_fingerprint,
            )
            V_binary = load_selected_stage(
                extracted["ratings.dat"],
                selected_users,
                layouts,
                movie_to_index,
                "V",
                rating_view="binary_relevance",
            )
            V_binary_utc = utc_now()
            if V_manifest_utc > V_binary_utc:
                raise IntegrityError("V relevance opened before target-blind manifests")
            assert_stage_items_disjoint(
                V_histories, V_binary, current_stage="V binary relevance"
            )
            selected_alpha_index, selected_alpha, alpha_record = select_shared_alpha(
                V_manifests, V_binary, movie_ids
            )
            stronger_method, relevance_record = choose_stronger_relevance_method(
                V_manifests, V_binary, movie_ids, selected_alpha_index
            )
            choices_path = output_dir / "frozen_validation_choices.json"
            choices_utc = utc_now()
            publish_json(
                choices_path,
                {
                    "schema": "cable-pref-frozen-validation-choices-v1",
                    "frozen_utc": choices_utc,
                    "execution_fingerprint_sha256": execution_fingerprint,
                    "selected_alpha_index": selected_alpha_index,
                    "selected_alpha": selected_alpha,
                    "alpha_selection": alpha_record,
                    "stronger_G4_relevance_method": stronger_method,
                    "relevance_selection": relevance_record,
                    "component_normalization": "per_request_5th_95th_linear_clip",
                    "tie_break": "score_desc_then_numeric_movie_id_asc",
                },
            )
            del V_binary
            V = load_selected_stage(
                extracted["ratings.dat"], selected_users, layouts, movie_to_index, "V"
            )
            V_exact_utc = utc_now()
            if choices_utc > V_exact_utc:
                raise IntegrityError("Exact V preferences opened before choices were frozen")
            assert_stage_items_disjoint(V_histories, V, current_stage="V exact")
            V_pairs, V_pair_diagnostics = natural_pairs(V, "V")
            V_metric_rows: list[np.ndarray] = []
            V_diagnostics: list[Mapping[str, Any]] = []
            for seed in SEEDS:
                values, diagnostics = evaluate_manifest(
                    V_manifests[seed], V, V_pairs, selected_alpha_index, movie_ids
                )
                V_metric_rows.append(values)
                V_diagnostics.append(diagnostics)
            V_metrics = np.stack(V_metric_rows, axis=0)
            power = power_audit(V_metrics)
            R_outcomes = stage_outcome_arrays(user_ids, R, R_pairs)
            V_outcomes = stage_outcome_arrays(user_ids, V, V_pairs)
            validation_path = output_dir / "raw_validation.npz"
            validation_sha = publish_npz(
                validation_path,
                **validation_raw_arrays(
                    protocol_fingerprint=protocol_fingerprint,
                    execution_fingerprint=execution_fingerprint,
                    user_ids=user_ids,
                    movie_ids=movie_ids,
                    metrics=V_metrics,
                    selected_alpha_index=selected_alpha_index,
                    selected_alpha=selected_alpha,
                    stronger_relevance_method=stronger_method,
                    power=power,
                    manifest_files=V_manifest_files,
                    manifest_hashes=V_manifest_hashes,
                    immutable_records=immutable_before,
                    R_outcome_arrays=R_outcomes,
                    outcome_arrays=V_outcomes,
                    R_diagnostics=R_diagnostics,
                    V_diagnostics=V_diagnostics,
                    V_pair_diagnostics=V_pair_diagnostics,
                    training_diagnostics=training_diagnostics,
                    initial_hashes=initial_hashes,
                    final_hashes=final_hashes,
                    timestamps={
                        "manifest": V_manifest_utc,
                        "binary": V_binary_utc,
                        "choices": choices_utc,
                        "exact": V_exact_utc,
                    },
                ),
            )
            del R_outcomes, V_outcomes

            if not bool(power["passed"]):
                immutable_final = finalize_immutable_records(
                    output_dir, immutable_before, immutable_handles
                )
                gates = {f"G{index}": False for index in range(1, 10)}
                result_path = output_dir / "result.json"
                result = {
                    "schema": "cable-pref-result-v1",
                    "created_utc": utc_now(),
                    "termination_stage": "pre_T_power_audit",
                    "test_opened": False,
                    "PROMISING": False,
                    "runner_candidate_promising": False,
                    "kill_project": True,
                    "kill_reason": "validation_power_audit_failed",
                    "promise_gate": gates,
                    "protocol_fingerprint_sha256": protocol_fingerprint,
                    "protocol_fingerprint_payload": protocol_payload,
                    "execution_fingerprint_sha256": execution_fingerprint,
                    "execution_fingerprint_payload": execution_payload,
                    "source_sha256": source_hashes,
                    "dataset_archive": archive_record,
                    "selected_alpha": selected_alpha,
                    "selected_alpha_index": selected_alpha_index,
                    "stronger_relevance_method": stronger_method,
                    "power_audit": power,
                    "R_support_passed": R_support_passed,
                    "immutable_records": immutable_final,
                    "raw_validation_file": safe_relative(validation_path, output_dir),
                    "raw_validation_sha256": validation_sha,
                    "external_post_exit_verification_required": True,
                }
                publish_json(result_path, result)
                candidate = publish_runner_candidate(
                    output_dir=output_dir,
                    runner_lock=runner_lock,
                    ledger=ledger,
                    source_hashes=source_hashes,
                    execution_fingerprint=execution_fingerprint,
                    termination_stage="pre_T_power_audit",
                    test_opened=False,
                    result_path=result_path,
                    raw_validation_path=validation_path,
                )
                candidate_published = True
                return {
                    "termination_stage": "pre_T_power_audit",
                    "candidate": str(candidate),
                    "runner_candidate_promising": False,
                }

            # Power passed: only now may a T manifest be created and T values opened.
            del V_manifests, V_metrics, V_diagnostics
            gc.collect()
            T_histories = {
                user_id: stage_history(user_id, "T", A, R, V)
                for user_id in user_ids
            }
            T_manifests = {
                seed: build_stage_manifest(
                    "T",
                    seed,
                    user_ids,
                    T_histories,
                    models_by_seed[seed],
                    bpr,
                    bpr_index,
                    semantic_vectors,
                    semantic_index,
                    movie_ids,
                )
                for seed in SEEDS
            }
            T_manifest_files, T_manifest_hashes, T_manifest_utc = publish_stage_manifests(
                output_dir,
                "T",
                T_manifests,
                protocol_fingerprint,
                execution_fingerprint,
            )
            T = load_selected_stage(
                extracted["ratings.dat"], selected_users, layouts, movie_to_index, "T"
            )
            T_opened_utc = utc_now()
            if T_manifest_utc > T_opened_utc:
                raise IntegrityError("T outcomes opened before target-blind manifests")
            assert_stage_items_disjoint(T_histories, T, current_stage="T")
            T_pairs, T_pair_diagnostics = natural_pairs(T, "T")
            T_metric_rows: list[np.ndarray] = []
            T_diagnostics: list[Mapping[str, Any]] = []
            for seed in SEEDS:
                values, diagnostics = evaluate_manifest(
                    T_manifests[seed], T, T_pairs, selected_alpha_index, movie_ids
                )
                T_metric_rows.append(values)
                T_diagnostics.append(diagnostics)
            T_metrics = np.stack(T_metric_rows, axis=0)
            action = replay_action_consistency(
                T_manifests, T_pairs, semantic_vectors, movie_ids
            )
            durations, latency = measure_latency(
                user_ids,
                T_histories,
                models_by_seed,
                bpr,
                bpr_index,
                semantic_vectors,
                semantic_index,
                movie_ids,
                selected_alpha,
            )
            immutable_final = finalize_immutable_records(
                output_dir, immutable_before, immutable_handles
            )
            g1_invariants = {
                **manifest_exact_invariants(T_manifests),
                "leaveout_action_consistency": bool(action["passed"]),
                "immutable_geometry": bool(
                    all(record["unchanged"] for record in immutable_final.values())
                ),
                "target_blind_manifest_precedes_T": bool(T_manifest_utc <= T_opened_utc),
                "unsupported_bpr_factors_zero": bool(
                    np.all(bpr.item_vectors[~bpr.collaborative_mask] == 0.0)
                ),
            }
            gates, gate_details = compute_gates(
                T_metrics,
                T_diagnostics,
                R_diagnostics,
                power,
                latency,
                stronger_method,
                g1_invariants,
            )
            T_outcomes = stage_outcome_arrays(user_ids, T, T_pairs)
            test_path = output_dir / "raw_test.npz"
            test_sha = publish_npz(
                test_path,
                **test_raw_arrays(
                    protocol_fingerprint=protocol_fingerprint,
                    execution_fingerprint=execution_fingerprint,
                    user_ids=user_ids,
                    movie_ids=movie_ids,
                    metrics=T_metrics,
                    selected_alpha_index=selected_alpha_index,
                    selected_alpha=selected_alpha,
                    stronger_relevance_method=stronger_method,
                    manifest_files=T_manifest_files,
                    manifest_hashes=T_manifest_hashes,
                    immutable_records=immutable_before,
                    outcome_arrays=T_outcomes,
                    pair_diagnostics=T_pair_diagnostics,
                    diagnostics=T_diagnostics,
                    action=action,
                    g1_invariants=g1_invariants,
                    gates=gates,
                    manifest_utc=T_manifest_utc,
                    opened_utc=T_opened_utc,
                ),
            )
            latency_path = output_dir / "raw_latency.npz"
            latency_sha = publish_npz(
                latency_path,
                **latency_raw_arrays(
                    protocol_fingerprint=protocol_fingerprint,
                    execution_fingerprint=execution_fingerprint,
                    durations=durations,
                    summary=latency,
                ),
            )
            runner_verdict = bool(all(gates.values()))
            result_path = output_dir / "result.json"
            result = {
                "schema": "cable-pref-result-v1",
                "created_utc": utc_now(),
                "termination_stage": "post_T_all_gates",
                "test_opened": True,
                "PROMISING": False,
                "runner_candidate_promising": runner_verdict,
                "kill_project": not runner_verdict,
                "kill_reason": None if runner_verdict else "one_or_more_registered_G1_G9_gates_failed",
                "promise_gate": dict(gates),
                "promise_gate_details": gate_details,
                "protocol_fingerprint_sha256": protocol_fingerprint,
                "protocol_fingerprint_payload": protocol_payload,
                "execution_fingerprint_sha256": execution_fingerprint,
                "execution_fingerprint_payload": execution_payload,
                "source_sha256": source_hashes,
                "dataset_archive": archive_record,
                "selected_alpha": selected_alpha,
                "selected_alpha_index": selected_alpha_index,
                "stronger_relevance_method": stronger_method,
                "power_audit": power,
                "immutable_records": immutable_final,
                "raw_validation_file": safe_relative(validation_path, output_dir),
                "raw_validation_sha256": validation_sha,
                "raw_test_file": safe_relative(test_path, output_dir),
                "raw_test_sha256": test_sha,
                "latency_file": safe_relative(latency_path, output_dir),
                "latency_sha256": latency_sha,
                "external_post_exit_verification_required": True,
            }
            publish_json(result_path, result)
            candidate = publish_runner_candidate(
                output_dir=output_dir,
                runner_lock=runner_lock,
                ledger=ledger,
                source_hashes=source_hashes,
                execution_fingerprint=execution_fingerprint,
                termination_stage="post_T_all_gates",
                test_opened=True,
                result_path=result_path,
                raw_validation_path=validation_path,
                raw_test_path=test_path,
                latency_path=latency_path,
            )
            candidate_published = True
            return {
                "termination_stage": "post_T_all_gates",
                "candidate": str(candidate),
                "runner_candidate_promising": runner_verdict,
            }
    finally:
        # A candidate is written while the lock is held and explicitly declares
        # pending release; the independent verifier proves absence post-exit.
        release_runner_lock(runner_lock, lock_token)
        if candidate_published and ledger.stat().st_size != 0:
            raise IntegrityError("Asynchronous error recorded after candidate publication")


def run_self_tests(config_path: Path | None = None) -> Mapping[str, Any]:
    """Archive-free executable protocol tests; never inspect a dataset path."""
    checks: dict[str, bool] = {}

    def require(name: str, condition: bool) -> None:
        if not condition:
            raise AssertionError(name)
        checks[name] = True

    validate_locked_config()
    if config_path is not None:
        load_and_validate_external_config(config_path)
    require("raw_validation_schema_unique", len(RAW_VALIDATION_FIELDS) == len(set(RAW_VALIDATION_FIELDS)))
    require("raw_test_schema_unique", len(RAW_TEST_FIELDS) == len(set(RAW_TEST_FIELDS)))
    require("raw_latency_schema_unique", len(RAW_LATENCY_FIELDS) == len(set(RAW_LATENCY_FIELDS)))

    rating_line = "1::10::3.5::123\n"
    row = parse_skeleton_line(rating_line, 7)
    event = parse_interaction(row, {10: 0}, rating_line)
    require("half_star_rating_is_float", event.rating == 3.5 and isinstance(event.rating, float))
    require("structural_row_retains_no_rating_payload", not hasattr(row, "raw_line"))
    movie = parse_movie_line("10::Amélie (2001)::Comedy|Romance\n")
    require("strict_utf8_metadata", movie.title == "Amélie (2001)")
    synthetic_embedding = encode_movies(
        (Movie(1, "Synthetic Preflight (2000)", "Drama"),)
    )
    require(
        "offline_sentence_transformer_preflight",
        synthetic_embedding.shape == (1, 384)
        and np.isfinite(synthetic_embedding).all()
        and math.isclose(
            float(np.linalg.norm(synthetic_embedding[0])), 1.0, abs_tol=2.0e-5
        ),
    )

    movie_ids = np.arange(1, 902, dtype=np.int64)
    scores = np.arange(901, 0, -1, dtype=np.float32)
    mask = np.ones(901, dtype=np.bool_)
    mask[:501] = False
    selected = stable_order(scores, mask, movie_ids, 200)
    require("seen_501_of_first_701_still_exact_200", selected == tuple(range(501, 701)))
    assert_request_capacity(bpr_available=200, semantic_complement_available=500)
    require("capacity_200_collaborative_plus_500_semantic_passes", True)
    for name, bpr_available, semantic_available in (
        ("capacity_199_collaborative_fails", 199, 500),
        ("capacity_499_semantic_fails", 200, 499),
    ):
        failed = False
        try:
            assert_request_capacity(
                bpr_available=bpr_available,
                semantic_complement_available=semantic_available,
            )
        except IntegrityError:
            failed = True
        require(name, failed)
    top_mask = np.ones(10, dtype=np.bool_)
    top_mask[:2] = False
    require(
        "seen_or_future_high_scores_are_masked",
        stable_order(np.arange(10, 0, -1, dtype=np.float32), top_mask, np.arange(10), 2)
        == (2, 3),
    )
    duplicate_failed = False
    try:
        stage_history(
            1,
            "V",
            {1: (Interaction(1, 2, 3, 5.0, 1, 0),)},
            {1: (Interaction(1, 2, 3, 1.0, 2, 1),)},
        )
    except IntegrityError:
        duplicate_failed = True
    require("cross_stage_duplicate_user_movie_fails", duplicate_failed)

    rng = np.random.default_rng(20260835)
    vectors = rng.normal(size=(64, 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    query = normalise(rng.normal(size=8).astype(np.float32))
    faiss_index = build_faiss_flat_ip(vectors)
    oracle_mask = np.ones(64, dtype=np.bool_)
    oracle_mask[[0, 7, 11]] = False
    random_items, _ = assert_oracle_identity(
        faiss_index, vectors, query, oracle_mask, np.arange(1, 65), 20
    )
    require("faiss_matrix_random_exact_ids_and_order", len(random_items) == 20)
    tied_vectors = np.zeros((64, 8), dtype=np.float32)
    tied_index = build_faiss_flat_ip(tied_vectors)
    tied_items, _ = assert_oracle_identity(
        tied_index,
        tied_vectors,
        query,
        np.ones(64, dtype=np.bool_),
        np.arange(100, 164, dtype=np.int64),
        20,
    )
    require("faiss_matrix_all_equal_ties", tied_items == tuple(range(20)))
    manifest_queries = np.stack(
        [
            normalise(rng.normal(size=8).astype(np.float32))
            for _ in range(65)
        ]
    )
    manifest_masks = np.broadcast_to(oracle_mask, (65, 64)).copy()
    loop_rows = tuple(
        assert_oracle_identity(
            faiss_index, vectors, value, oracle_mask, np.arange(1, 65), 20
        )[0]
        for value in manifest_queries
    )
    batch_rows: list[tuple[int, ...]] = []
    observed_batch_sizes: list[int] = []
    for start in range(
        0, len(manifest_queries),
        int(LOCKED_CONFIG["retrieval"]["manifest_query_batch_size"]),
    ):
        stop = min(
            len(manifest_queries),
            start
            + int(LOCKED_CONFIG["retrieval"]["manifest_query_batch_size"]),
        )
        rows, _scores = exact_faiss_masked_topk_batch(
            faiss_index,
            manifest_queries[start:stop],
            manifest_masks[start:stop],
            np.arange(1, 65, dtype=np.int64),
            20,
            oracle_vectors=vectors,
        )
        observed_batch_sizes.append(stop - start)
        batch_rows.extend(rows)
    require("batch_single_query_equivalence", tuple(batch_rows[:2]) == loop_rows[:2])
    require(
        "manifest_batch_64_plus_tail_matches_single",
        tuple(batch_rows) == loop_rows and observed_batch_sizes == [64, 1],
    )

    item_count = 720
    semantic = rng.normal(size=(item_count, 384)).astype(np.float32)
    semantic /= np.linalg.norm(semantic, axis=1, keepdims=True)
    semantic_index = build_faiss_flat_ip(semantic)
    bpr_items = tuple(range(200))
    semantic_mask = np.ones(item_count, dtype=np.bool_)
    semantic_mask[:200] = False
    bpr_items_matrix = rng.normal(size=(item_count, 64)).astype(np.float32)
    bpr_query = rng.normal(size=64).astype(np.float32)
    synthetic_bpr = BPRArtifacts(
        (1,), {1: 0}, bpr_query.reshape(1, -1), bpr_items_matrix,
        np.ones(item_count, dtype=np.bool_), tuple()
    )
    raw_query = normalise(rng.normal(size=384).astype(np.float32))
    descriptor = QueryDescriptor(raw_query, raw_query.copy(), np.zeros(384, dtype=np.float32), 0.1)
    context = RequestContext(
        1,
        descriptor,
        bpr_query,
        bpr_items,
        np.zeros(item_count, dtype=np.bool_),
        semantic_mask,
        np.ones(item_count, dtype=np.bool_),
    )
    union = retrieve_hybrid(
        context,
        raw_query,
        synthetic_bpr,
        semantic,
        semantic_index,
        np.arange(1, item_count + 1, dtype=np.int64),
        0.5,
    ).union
    require("exact_200_plus_200_union", len(union) == 400 and len(set(union)) == 400)
    require("retrieval_branches_disjoint", not (set(union[:200]) & set(union[200:])))

    tie_scores = np.zeros(250, dtype=np.float32)
    tie_ids = np.arange(1, 251, dtype=np.int64)
    tie_eligible = np.ones(250, dtype=np.bool_)
    first_boundary = stable_leaveout_boundary_index(tie_scores, tie_eligible, 0, tie_ids, 200)
    last_boundary = stable_leaveout_boundary_index(tie_scores, tie_eligible, 249, tie_ids, 200)
    tied_fast = leaveout_boundaries_from_base_topk(
        tie_scores, tie_eligible, (0, 50, 199, 200, 249), tie_ids, 200
    )
    require(
        "base_top201_matches_naive_all_ties",
        all(
            boundary
            == stable_leaveout_boundary_index(tie_scores, tie_eligible, endpoint, tie_ids, 200)
            for endpoint, boundary in tied_fast.items()
        ),
    )
    property_scores = rng.normal(size=320).astype(np.float32)
    property_ids = rng.permutation(np.arange(1000, 1320, dtype=np.int64))
    property_mask = np.ones(320, dtype=np.bool_)
    property_mask[rng.choice(320, size=30, replace=False)] = False
    property_endpoints = tuple(map(int, np.flatnonzero(property_mask)[::29]))
    random_fast = leaveout_boundaries_from_base_topk(
        property_scores, property_mask, property_endpoints, property_ids, 50
    )
    require(
        "base_topk_plus_one_matches_naive_random",
        all(
            boundary
            == stable_leaveout_boundary_index(
                property_scores, property_mask, endpoint, property_ids, 50
            )
            for endpoint, boundary in random_fast.items()
        ),
    )
    require(
        "leaveout_tie_action_equivalence",
        admission_from_boundary_key(tie_scores, 0, first_boundary, tie_ids)
        and not admission_from_boundary_key(tie_scores, 249, last_boundary, tie_ids),
    )

    history = (
        Interaction(1, 1, 2, 5.0, 1, 0),
        Interaction(1, 2, 3, 1.0, 2, 1),
    )
    before = descriptor_array(query_descriptor(history, semantic))
    poisoned_current_outcomes = {
        1: (Interaction(1, 719, 720, 0.5, 3, 2),)
    }
    poisoned_current_outcomes[1] = (
        Interaction(1, 718, 719, 5.0, 3, 2),
    )
    after = descriptor_array(query_descriptor(history, semantic))
    manifest_inputs = set(inspect.signature(build_stage_manifest).parameters)
    require(
        "target_blind_manifest_api_accepts_prefix_not_current_outcomes",
        np.array_equal(before, after)
        and not (
            manifest_inputs
            & {"stage_events", "pairs", "targets", "outcomes", "ratings"}
        ),
    )
    synthetic_bpr_index = build_faiss_flat_ip(synthetic_bpr.item_vectors)
    _contexts_a, blind_arrays_a = build_R_target_blind_arrays(
        (1,),
        {1: history},
        synthetic_bpr,
        synthetic_bpr_index,
        semantic,
        semantic_index,
        np.arange(1, item_count + 1, dtype=np.int64),
        "0" * 64,
        "1" * 64,
    )
    poisoned_current_outcomes[1] = (
        Interaction(1, 717, 718, 0.5, 4, 3),
    )
    _contexts_b, blind_arrays_b = build_R_target_blind_arrays(
        (1,),
        {1: history},
        synthetic_bpr,
        synthetic_bpr_index,
        semantic,
        semantic_index,
        np.arange(1, item_count + 1, dtype=np.int64),
        "0" * 64,
        "1" * 64,
    )

    def arrays_identical(left_arrays: Mapping[str, np.ndarray], right_arrays: Mapping[str, np.ndarray]) -> bool:
        if tuple(left_arrays) != tuple(right_arrays):
            return False
        for name in left_arrays:
            left_value = np.asarray(left_arrays[name])
            right_value = np.asarray(right_arrays[name])
            if left_value.dtype != right_value.dtype or left_value.shape != right_value.shape:
                return False
            if np.issubdtype(left_value.dtype, np.inexact):
                if not np.array_equal(left_value, right_value, equal_nan=True):
                    return False
            elif not np.array_equal(left_value, right_value):
                return False
        return True

    require(
        "target_poisoning_leaves_R_manifest_arrays_identical",
        arrays_identical(blind_arrays_a, blind_arrays_b)
        and poisoned_current_outcomes[1][0].item_index not in set(
            map(int, blind_arrays_b["history_items"][0])
        ),
    )

    initial = new_adapter(20260835)
    adapted, boundary = apply_adapter_numpy(descriptor, initial)
    require("zero_output_adapter_identity", np.array_equal(adapted, descriptor.raw_query) and boundary == 0.0)
    initial_state = adapter_state_copy(initial)
    training_context = RequestContext(
        1,
        descriptor,
        bpr_query,
        bpr_items,
        np.zeros(item_count, dtype=np.bool_),
        np.ones(item_count, dtype=np.bool_),
        np.ones(item_count, dtype=np.bool_),
    )
    duplicate_endpoint_pairs = (
        PairRow(1, 0, 1, 1, 2),
        PairRow(1, 0, 2, 1, 3),
    )
    synthetic_training: dict[str, Mapping[str, Any]] = {}
    for method in TRAINED_METHODS:
        _model, diagnostics, _state = train_adapter_control(
            method,
            20260835,
            {1: training_context},
            duplicate_endpoint_pairs,
            semantic,
            np.arange(1, item_count + 1, dtype=np.int64),
            initial_state,
        )
        synthetic_training[method] = diagnostics
    cable_diagnostics = synthetic_training["cable_pref"]
    require(
        "all_trainable_controls_match_steps_and_pair_presentations",
        len(
            {value["optimizer_steps"] for value in synthetic_training.values()}
        )
        == 1
        and len(
            {value["pair_presentations"] for value in synthetic_training.values()}
        )
        == 1
        and all(
            isinstance(value["checkpoint_sha256"], str)
            and len(value["checkpoint_sha256"]) == 64
            for value in synthetic_training.values()
        ),
    )
    require(
        "admission_preferred_endpoint_deduplicated_after_cap",
        cable_diagnostics["admission_presentations"]
        == int(LOCKED_CONFIG["adapter"]["epochs"]),
    )
    torch, _nn, functional = _torch_imports()
    learned_boundary = torch.tensor(0.2, requires_grad=True)
    preferred_penalty = functional.softplus(5.0 * (0.02 - (torch.tensor(0.6) - learned_boundary)))
    preferred_penalty.backward()
    preferred_gradient = float(learned_boundary.grad)
    learned_boundary.grad = None
    rejected_penalty = functional.softplus(5.0 * (0.02 - (learned_boundary - torch.tensor(-0.1))))
    rejected_penalty.backward()
    rejected_gradient = float(learned_boundary.grad)
    require("uib_two_sided_boundary_gradients", preferred_gradient > 0.0 and rejected_gradient < 0.0)

    supported = np.asarray([True, False, True, False])
    factors = np.ones((4, 3), dtype=np.float32)
    factors[~supported] = 0.0
    require("unsupported_bpr_factors_exact_zero", np.all(factors[~supported] == 0.0))
    left = np.asarray([1.0, 0.0, 1.0, 1.0])
    right = np.asarray([0.0, 0.0, 0.0, 1.0])
    bootstrap_a = paired_bootstrap(left, right, draws=250, seed=20263504)
    bootstrap_b = paired_bootstrap(left, right, draws=250, seed=20263504)
    require("bootstrap_seed_deterministic", bootstrap_a == bootstrap_b)

    synthetic_users = 16
    synthetic_metrics = np.full(
        (len(SEEDS), len(METHODS), synthetic_users, len(METRICS)),
        0.1,
        dtype=np.float64,
    )
    synthetic_metric_index = {name: index for index, name in enumerate(METRICS)}
    synthetic_metrics[:, 4, :, synthetic_metric_index["conditional_admission_at_200"]] = 0.14
    synthetic_metrics[:, 4, :, synthetic_metric_index["net_new_preferred_support"]] = 0.12
    synthetic_metrics[:, 4, :, synthetic_metric_index["net_admission_advantage"]] = 0.12
    synthetic_metrics[:, 4, :, synthetic_metric_index["spce_at_10"]] = 0.12
    synthetic_metrics[:, 4, :, synthetic_metric_index["preferred_exposure_at_10"]] = 0.12
    synthetic_diagnostics = tuple(
        {
            "fixed_pairs": 6000,
            "pair_users": 1200,
            "unique_bpr_missed_preferred_endpoints": 6000,
            "missed_endpoint_users": 1200,
            "admission_changed_count": 600,
            "admission_total": 6000,
            "spce_changed_count": 180,
            "spce_total": 6000,
        }
        for _seed in SEEDS
    )
    synthetic_R_diagnostics = {
        "selected_pairs": 21_000,
        "selected_pair_users": 1200,
    }
    synthetic_power = {"passed": True}
    synthetic_latency = {"passed": True}
    synthetic_g1 = {"exact_union": True, "immutable_geometry": True}
    gates_a, gate_details_a = compute_gates(
        synthetic_metrics,
        synthetic_diagnostics,
        synthetic_R_diagnostics,
        synthetic_power,
        synthetic_latency,
        "raw_hybrid",
        synthetic_g1,
    )
    gates_b, gate_details_b = compute_gates(
        synthetic_metrics,
        synthetic_diagnostics,
        synthetic_R_diagnostics,
        synthetic_power,
        synthetic_latency,
        "raw_hybrid",
        synthetic_g1,
    )
    gates_bad, _gate_details_bad = compute_gates(
        synthetic_metrics,
        synthetic_diagnostics,
        synthetic_R_diagnostics,
        synthetic_power,
        {"passed": False},
        "raw_hybrid",
        {"exact_union": False, "immutable_geometry": True},
    )
    empty_gates, empty_gate_details = compute_gates(
        np.full_like(synthetic_metrics, np.nan),
        synthetic_diagnostics,
        synthetic_R_diagnostics,
        synthetic_power,
        synthetic_latency,
        "raw_hybrid",
        synthetic_g1,
    )
    require(
        "deterministic_full_G1_G9_replay",
        all(gates_a.values())
        and gates_a == gates_b
        and gate_details_a == gate_details_b
        and gates_bad["G1"] is False
        and gates_bad["G8"] is False,
    )
    require(
        "empty_metric_support_fails_gates_without_nonfinite_output",
        not all(empty_gates.values())
        and empty_gate_details["required_metric_support_complete"] is False
        and all(
            record["users"] == 0 and record["support_failed"] is True
            for record in empty_gate_details["bootstrap"].values()
        )
        and bool(canonical_json_bytes(empty_gate_details)),
    )

    return {
        "schema": "cable-pref-runner-self-test-v1",
        "passed": True,
        "checks": checks,
        "archive_opened": False,
        "archive_listed": False,
        "target_outcomes_accessed": False,
        "raw_validation_fields": list(RAW_VALIDATION_FIELDS),
        "raw_test_fields": list(RAW_TEST_FIELDS),
        "raw_latency_fields": list(RAW_LATENCY_FIELDS),
    }


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--local-dataset-archive", type=Path)
    parser.add_argument("--validate-config", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    if args.validate_config or args.self_test:
        if args.output_dir is not None or args.local_dataset_archive is not None:
            raise IntegrityError("Outcome-blind validation/self-test forbids archive and output arguments")
        if args.protocol is not None and not args.protocol.is_file():
            raise IntegrityError("Named protocol file does not exist")
        if args.validate_config and not args.self_test:
            report: Mapping[str, Any]
            report = (
                {
                    **validate_locked_config(),
                    "external_config_validated": True,
                    "external_config_sha256": sha256_file(args.config.resolve()),
                }
                if args.config is not None and load_and_validate_external_config(args.config.resolve())
                else validate_locked_config()
            )
        else:
            report = run_self_tests(args.config.resolve() if args.config is not None else None)
        sys.stdout.buffer.write(canonical_json_bytes(report))
        return 0
    required = {
        "--config": args.config,
        "--protocol": args.protocol,
        "--output-dir": args.output_dir,
        "--local-dataset-archive": args.local_dataset_archive,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise IntegrityError(f"Authorized execution requires all launcher arguments: {missing}")
    report = execute_authorized(
        config_path=args.config.resolve(),
        protocol_path=args.protocol.resolve(),
        output_dir=args.output_dir.resolve(),
        archive_path=args.local_dataset_archive.resolve(),
    )
    sys.stdout.buffer.write(canonical_json_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
