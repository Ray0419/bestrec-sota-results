#!/usr/bin/env python3
"""Preregistered MovieLens-1M proof of concept for CAPER.

CAPER (Coverage-Anchored Preference-Exception Reranking) keeps independent
SentenceTransformer and collaborative FAISS indexes immutable after they are
built.  It forms an exact union that contains every collaborative candidate,
learns a bounded reference-free preference residual only from naturally rated
pairs present in the alignment union, and projects the proposed top ten into a
hard cumulative normalized-BPR-regret budget.

The runner is deliberately CPU-only, append-only, and fail-closed.  It creates
a runner-completion candidate; an external launcher must still bind persistent
stdout/stderr, observe process exit and lock release, and publish the final
post-exit completion marker required by the Windows execution contract.
"""

from __future__ import annotations

import os

# These assignments must precede NumPy, PyTorch, SentenceTransformers, or FAISS.
for _name in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ[_name] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import math
import platform
import random
import shutil
import sys
import threading
import time
import traceback
import urllib.request
import uuid
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

torch.set_num_threads(1)
torch.set_num_interop_threads(1)


THREAD_ENVIRONMENT = {
    key: os.environ[key]
    for key in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
        "CUDA_VISIBLE_DEVICES",
    )
}


class IntegrityError(RuntimeError):
    """A preregistered provenance, safety, or append-only invariant failed."""


@dataclass(frozen=True)
class Interaction:
    user_id: int
    item_index: int
    rating: int
    timestamp: int
    ordinal: int


@dataclass(frozen=True)
class UserSplit:
    user_id: int
    train: tuple[Interaction, ...]
    alignment: tuple[Interaction, ...]
    validation: tuple[Interaction, ...]
    test: tuple[Interaction, ...]


@dataclass(frozen=True)
class BPRArtifacts:
    variant: str
    user_ids: tuple[int, ...]
    user_to_row: Mapping[int, int]
    user_vectors: np.ndarray
    item_vectors: np.ndarray
    training_diagnostics: Mapping[str, Any]


@dataclass(frozen=True)
class CandidateContext:
    user_id: int
    collaborative: tuple[int, ...]
    semantic: tuple[int, ...]
    union: tuple[int, ...]
    semantic_query: np.ndarray
    dislike_query: np.ndarray
    collaborative_query: np.ndarray
    history_log_feature: float
    bpr_min: float
    bpr_span: float
    semantic_min: float
    semantic_span: float
    collaborative_rank: Mapping[int, int]
    semantic_rank: Mapping[int, int]
    regret_scale_degenerate: bool


@dataclass(frozen=True)
class CandidateManifestEntry:
    context: CandidateContext
    implicit_candidates: tuple[int, ...]
    rating_aware_candidates: tuple[int, ...]
    implicit_query: np.ndarray
    rating_aware_query: np.ndarray


@dataclass(frozen=True)
class AlignmentCorpus:
    chosen_features: np.ndarray
    rejected_features: np.ndarray
    chosen_base_scores: np.ndarray
    rejected_base_scores: np.ndarray
    user_ids: np.ndarray
    contradiction_mask: np.ndarray
    diagnostics: Mapping[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


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


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def publish_bytes_no_overwrite(path: Path, payload: bytes) -> None:
    """Atomically publish fsynced bytes without replacing an existing path."""
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
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def publish_json_no_overwrite(path: Path, value: Any) -> None:
    publish_bytes_no_overwrite(path, canonical_json_bytes(value))


def append_json_line(path: Path, value: Any) -> None:
    with path.open("ab") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def save_numpy_no_overwrite(path: Path, array: np.ndarray) -> None:
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    publish_bytes_no_overwrite(path, buffer.getvalue())


def save_torch_no_overwrite(path: Path, value: Any) -> None:
    buffer = io.BytesIO()
    torch.save(value, buffer)
    publish_bytes_no_overwrite(path, buffer.getvalue())


def process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class RunnerLock:
    """One CPU runner owner, with one atomic dead-owner retirement attempt."""

    def __init__(self, path: Path, protocol_hash: str) -> None:
        self.path = path
        self.protocol_hash = protocol_hash
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            payload = {
                "schema": "caper-runner-lock-v1",
                "pid": os.getpid(),
                "token": self.token,
                "protocol_sha256": self.protocol_hash,
                "created_utc": utc_now(),
            }
            try:
                publish_json_no_overwrite(self.path, payload)
                self.acquired = True
                return
            except FileExistsError:
                if attempt:
                    raise IntegrityError(f"Racing runner lock: {self.path}")
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                    owner_pid = int(existing["pid"])
                    owner_token = str(existing["token"])
                except Exception as exc:
                    raise IntegrityError(
                        f"Malformed runner lock; refusing: {self.path}"
                    ) from exc
                if not owner_token or process_is_alive(owner_pid):
                    raise IntegrityError(
                        f"Runner lock belongs to live PID {owner_pid}: {self.path}"
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
                    raise IntegrityError("Dead-lock retirement raced") from exc
        raise AssertionError("unreachable")

    def release(self) -> None:
        if not self.acquired:
            return
        current = json.loads(self.path.read_text(encoding="utf-8"))
        if current.get("token") != self.token or int(current.get("pid", -1)) != os.getpid():
            raise IntegrityError("Runner-lock ownership changed")
        self.path.unlink()
        fsync_directory(self.path.parent)
        self.acquired = False


def install_async_exception_hooks(error_ledger: Path) -> None:
    original_thread = threading.excepthook
    original_unraisable = sys.unraisablehook

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        append_json_line(
            error_ledger,
            {
                "kind": "threading.excepthook",
                "utc": utc_now(),
                "thread": getattr(args.thread, "name", None),
                "exception_type": getattr(args.exc_type, "__name__", str(args.exc_type)),
                "exception": str(args.exc_value),
                "traceback": "".join(
                    traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
                ),
            },
        )
        original_thread(args)

    def unraisable_hook(args: Any) -> None:
        append_json_line(
            error_ledger,
            {
                "kind": "sys.unraisablehook",
                "utc": utc_now(),
                "object": repr(args.object),
                "exception_type": type(args.exc_value).__name__,
                "exception": str(args.exc_value),
                "traceback": "".join(
                    traceback.format_exception(
                        type(args.exc_value), args.exc_value, args.exc_traceback
                    )
                ),
            },
        )
        original_unraisable(args)

    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def deterministic_setup(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


def validate_config(config: Mapping[str, Any]) -> None:
    required = (
        "dataset",
        "embedding",
        "retrieval",
        "bpr",
        "residual",
        "evaluation",
        "promise_gate",
    )
    for section in required:
        if not isinstance(config.get(section), Mapping):
            raise ValueError(f"Missing configuration section: {section}")
    seeds = [int(seed) for seed in config.get("replicate_seeds", [])]
    if len(seeds) != 3 or len(set(seeds)) != 3 or any(seed < 0 for seed in seeds):
        raise ValueError("Exactly three distinct nonnegative replicate seeds are required")
    fractions = [float(value) for value in config["dataset"]["split_fractions"]]
    if fractions != [0.6, 0.2, 0.1, 0.1] or not math.isclose(sum(fractions), 1.0):
        raise ValueError("The sealed split must be timestamp-group 60/20/10/10")
    if config["dataset"].get("split_unit") != "per-user indivisible timestamp groups":
        raise ValueError("Timestamp groups must be indivisible")
    if config["retrieval"].get("index_kind") != "IndexFlatIP":
        raise ValueError("The sealed CAPER PoC requires FAISS IndexFlatIP")
    if config["retrieval"].get("metric") != "inner_product":
        raise ValueError("CAPER requires inner-product retrieval")
    branch_total = int(config["retrieval"]["collaborative_candidates"]) + int(
        config["retrieval"]["semantic_candidates"]
    )
    if int(config["retrieval"]["maximum_union_candidates"]) != branch_total:
        raise ValueError("maximum_union_candidates must equal both branch budgets")
    if int(config["retrieval"]["collaborative_candidate_recall_k"]) != int(
        config["retrieval"]["collaborative_candidates"]
    ):
        raise ValueError("BPR candidate recall must be measured over B@200")
    if int(config["retrieval"]["union_candidate_maximum_size"]) != branch_total:
        raise ValueError("Union candidate recall must be measured over the full bounded C")
    if int(config["dataset"]["minimum_test_users"]) < 500:
        raise ValueError("The test cohort must contain at least 500 users")
    if int(config["dataset"]["minimum_heldout_preference_pairs"]) < 500:
        raise ValueError("At least 500 held-out preference pairs are required")
    for key, minimum in (
        ("minimum_total_events", 50),
        ("minimum_pair_bearing_users", 300),
        ("minimum_bpr_agreement_pairs", 100),
        ("minimum_bpr_contradiction_pairs", 100),
        ("minimum_pair_bearing_test_users", 300),
        ("minimum_test_bpr_agreement_pairs", 100),
        ("minimum_test_bpr_contradiction_pairs", 100),
    ):
        if int(config["dataset"][key]) < minimum:
            raise ValueError(f"dataset.{key} must be at least {minimum}")
    if int(config["retrieval"]["collaborative_candidates"]) != 200:
        raise ValueError("The sealed B branch size is 200")
    if int(config["retrieval"]["semantic_candidates"]) != 200:
        raise ValueError("The sealed semantic branch size is 200")
    if int(config["retrieval"]["maximum_union_candidates"]) != 400:
        raise ValueError("The sealed union maximum is 400")
    contradiction_fraction = float(config["residual"]["bpr_contradiction_fraction"])
    if not math.isclose(contradiction_fraction, 0.5):
        raise ValueError("Exactly half the selected alignment pairs must be contradictions")
    if float(config["residual"]["residual_bound"]) <= 0.0:
        raise ValueError("Residual bound must be positive")
    if float(config["residual"]["hard_cumulative_normalized_bpr_regret_budget"]) < 0.0:
        raise ValueError("Regret budget must be nonnegative")
    if config["residual"].get("regret_scale_source") != "immutable_bpr_anchor_scores_only":
        raise ValueError("Regret scale must use immutable BPR anchor scores only")
    lower = float(config["residual"]["regret_scale_lower_quantile"])
    upper = float(config["residual"]["regret_scale_upper_quantile"])
    if not (0.0 <= lower < upper <= 1.0):
        raise ValueError("Invalid regret-scale quantiles")
    if float(config["residual"]["regret_scale_floor"]) <= 0.0:
        raise ValueError("regret_scale_floor must be positive")
    if config["bpr"].get("prefix_query_update") != (
        "trained_user_plus_rating_weighted_frozen_item_aggregate"
    ):
        raise ValueError("Unregistered BPR prefix query update")
    if not (0.0 <= float(config["embedding"]["dislike_centroid_weight"]) <= 1.0):
        raise ValueError("dislike_centroid_weight must be in [0,1]")
    if int(config["evaluation"]["bootstrap_repetitions"]) < 1000:
        raise ValueError("At least 1,000 bootstrap repetitions are required")


def acquire_official_zip(destination: Path, url: str, expected_sha256: str | None) -> str:
    """Download a fresh official archive into this unique run directory."""
    temporary = destination.with_name(
        f".{destination.name}.download.{os.getpid()}.{uuid.uuid4().hex}"
    )
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "CAPER-research-poc/1.0"}
        )
        with temporary.open("xb") as output, urllib.request.urlopen(
            request, timeout=180
        ) as source:
            shutil.copyfileobj(source, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        digest = sha256_file(temporary)
        if expected_sha256 and digest.lower() != str(expected_sha256).lower():
            raise IntegrityError(
                f"Dataset SHA-256 mismatch: expected {expected_sha256}, got {digest}"
            )
        os.link(temporary, destination)
        fsync_directory(destination.parent)
        return digest
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def extract_movielens(zip_path: Path, output_directory: Path) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(zip_path, "r") as archive:
        by_name = {Path(name).name: name for name in archive.namelist()}
        missing = {"ratings.dat", "movies.dat"} - set(by_name)
        if missing:
            raise IntegrityError(f"MovieLens archive missing {sorted(missing)}")
        result: dict[str, Path] = {}
        for base in ("ratings.dat", "movies.dat"):
            info = archive.getinfo(by_name[base])
            if info.is_dir() or info.file_size <= 0:
                raise IntegrityError(f"Invalid archive member: {by_name[base]}")
            destination = output_directory / base
            publish_bytes_no_overwrite(destination, archive.read(info))
            result[base] = destination
    return result["ratings.dat"], result["movies.dat"]


def load_movie_metadata(path: Path, template: str) -> tuple[list[int], list[str]]:
    records: list[tuple[int, str]] = []
    with path.open("r", encoding="latin-1", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            fields = line.rstrip("\r\n").split("::")
            if len(fields) != 3:
                raise IntegrityError(f"Malformed movies.dat line {line_number}")
            movie_id = int(fields[0])
            records.append(
                (
                    movie_id,
                    template.format(title=fields[1].strip(), genres=fields[2].strip()),
                )
            )
    records.sort(key=lambda value: value[0])
    ids = [value[0] for value in records]
    if len(ids) != len(set(ids)):
        raise IntegrityError("Duplicate MovieLens item IDs")
    return ids, [value[1] for value in records]


def load_ratings(path: Path, item_to_index: Mapping[int, int]) -> list[Interaction]:
    interactions: list[Interaction] = []
    with path.open("r", encoding="ascii", newline="") as handle:
        for ordinal, line in enumerate(handle):
            fields = line.rstrip("\r\n").split("::")
            if len(fields) != 4:
                raise IntegrityError(f"Malformed ratings.dat row {ordinal + 1}")
            user_id, item_id, rating, timestamp = map(int, fields)
            if item_id not in item_to_index:
                raise IntegrityError(f"Rating references missing item {item_id}")
            interactions.append(
                Interaction(
                    user_id=user_id,
                    item_index=item_to_index[item_id],
                    rating=rating,
                    timestamp=timestamp,
                    ordinal=ordinal,
                )
            )
    return interactions


def _nearest_group_cut(
    cumulative: np.ndarray, target: float, minimum: int, maximum: int
) -> int:
    if minimum > maximum:
        raise IntegrityError("Insufficient timestamp groups for the sealed split")
    choices = np.arange(minimum, maximum + 1, dtype=np.int64)
    distances = np.abs(cumulative[choices - 1] - target)
    return int(choices[int(np.argmin(distances))])


def chronological_timestamp_group_splits(
    interactions: Sequence[Interaction], dataset: Mapping[str, Any]
) -> tuple[list[UserSplit], Mapping[str, Any]]:
    """Split 60/20/10/10 without breaking equal-timestamp groups."""
    grouped: dict[int, list[Interaction]] = defaultdict(list)
    for event in interactions:
        grouped[event.user_id].append(event)
    positive_min = int(dataset["positive_rating_min"])
    minimum_train = int(dataset["minimum_train_events"])
    minimum_positive_history = int(dataset["minimum_positive_history"])
    eligible: list[UserSplit] = []
    excluded_reasons: dict[str, int] = defaultdict(int)
    achieved_fractions: list[tuple[float, float, float, float]] = []
    for user_id in sorted(grouped):
        events = sorted(
            grouped[user_id], key=lambda event: (event.timestamp, event.ordinal)
        )
        if len(events) < int(dataset["minimum_total_events"]):
            excluded_reasons["fewer_than_minimum_total_events"] += 1
            continue
        timestamp_groups: list[list[Interaction]] = []
        for event in events:
            if not timestamp_groups or timestamp_groups[-1][0].timestamp != event.timestamp:
                timestamp_groups.append([])
            timestamp_groups[-1].append(event)
        if len(timestamp_groups) < 4:
            excluded_reasons["fewer_than_four_timestamp_groups"] += 1
            continue
        cumulative = np.cumsum([len(group) for group in timestamp_groups])
        total = len(events)
        first = _nearest_group_cut(cumulative, 0.6 * total, 1, len(timestamp_groups) - 3)
        second = _nearest_group_cut(
            cumulative, 0.8 * total, first + 1, len(timestamp_groups) - 2
        )
        third = _nearest_group_cut(
            cumulative, 0.9 * total, second + 1, len(timestamp_groups) - 1
        )

        def flatten(start: int, end: int) -> tuple[Interaction, ...]:
            return tuple(event for group in timestamp_groups[start:end] for event in group)

        train = flatten(0, first)
        alignment = flatten(first, second)
        validation = flatten(second, third)
        test = flatten(third, len(timestamp_groups))
        if min(map(len, (train, alignment, validation, test))) <= 0:
            raise IntegrityError("A timestamp-group split block is empty")
        if len(train) < minimum_train:
            excluded_reasons["insufficient_train_events"] += 1
            continue
        if sum(event.rating >= positive_min for event in train) < minimum_positive_history:
            excluded_reasons["insufficient_positive_history"] += 1
            continue
        if not any(event.rating >= positive_min for event in validation):
            excluded_reasons["no_validation_positive"] += 1
            continue
        if not any(event.rating >= positive_min for event in test):
            excluded_reasons["no_test_positive"] += 1
            continue
        boundaries = (
            max(event.timestamp for event in train),
            min(event.timestamp for event in alignment),
            max(event.timestamp for event in alignment),
            min(event.timestamp for event in validation),
            max(event.timestamp for event in validation),
            min(event.timestamp for event in test),
        )
        if not (boundaries[0] < boundaries[1] and boundaries[2] < boundaries[3] and boundaries[4] < boundaries[5]):
            raise IntegrityError("Timestamp-group temporal separation failed")
        if set(event.timestamp for event in train) & set(event.timestamp for event in alignment):
            raise IntegrityError("Train/alignment timestamp leakage")
        if set(event.timestamp for event in alignment) & set(event.timestamp for event in validation):
            raise IntegrityError("Alignment/validation timestamp leakage")
        if set(event.timestamp for event in validation) & set(event.timestamp for event in test):
            raise IntegrityError("Validation/test timestamp leakage")
        eligible.append(UserSplit(user_id, train, alignment, validation, test))
        achieved_fractions.append(
            tuple(len(block) / total for block in (train, alignment, validation, test))
        )

    maximum_users = dataset.get("maximum_users")
    if maximum_users is not None and len(eligible) > int(maximum_users):
        subset_seed = int(dataset["stable_subset_seed"])

        def subset_key(split: UserSplit) -> tuple[str, int]:
            digest = hashlib.sha256(
                f"{subset_seed}:{split.user_id}".encode("ascii")
            ).hexdigest()
            return digest, split.user_id

        eligible = sorted(eligible, key=subset_key)[: int(maximum_users)]
        eligible.sort(key=lambda split: split.user_id)
    if len(eligible) < int(dataset["minimum_test_users"]):
        raise IntegrityError(
            f"Only {len(eligible)} eligible users; at least "
            f"{dataset['minimum_test_users']} are required"
        )
    means = (
        np.mean(np.asarray(achieved_fractions), axis=0).tolist()
        if achieved_fractions
        else []
    )
    return eligible, {
        "users_considered": int(sum(excluded_reasons.values()) + len(achieved_fractions)),
        "eligible_before_subset": len(achieved_fractions),
        "eligible_after_subset": len(eligible),
        "excluded_reasons": dict(sorted(excluded_reasons.items())),
        "mean_achieved_split_fractions_before_subset": means,
        "timestamp_groups_indivisible": True,
        "strict_temporal_boundaries": True,
        "stable_subset_applied": maximum_users is not None,
        "stable_subset_seed": int(dataset["stable_subset_seed"]),
    }


def encode_item_metadata(
    metadata: Sequence[str], embedding: Mapping[str, Any]
) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("sentence-transformers is required") from exc
    model = SentenceTransformer(
        str(embedding["model_name"]),
        device="cpu",
        local_files_only=bool(embedding.get("local_files_only", True)),
    )
    encoded = model.encode(
        list(metadata),
        batch_size=int(embedding["batch_size"]),
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=bool(embedding.get("normalize", True)),
    )
    vectors = np.ascontiguousarray(encoded, dtype=np.float32)
    if vectors.shape[0] != len(metadata) or vectors.ndim != 2:
        raise IntegrityError(f"Unexpected semantic matrix shape: {vectors.shape}")
    if not np.all(np.isfinite(vectors)):
        raise IntegrityError("Semantic matrix contains nonfinite values")
    if float(np.max(np.abs(np.linalg.norm(vectors, axis=1) - 1.0))) > 1e-4:
        raise IntegrityError("Semantic item vectors are not unit normalized")
    return vectors


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, np.float32(1e-12))
    normalized = np.ascontiguousarray(matrix / norms, dtype=np.float32)
    if not np.all(np.isfinite(normalized)):
        raise IntegrityError("Normalized matrix contains nonfinite values")
    return normalized


def build_faiss_index(vectors: np.ndarray, retrieval: Mapping[str, Any]) -> Any:
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError(
            "faiss-cpu is required; CAPER refuses a brute-force substitute"
        ) from exc
    faiss.omp_set_num_threads(1)
    if retrieval["index_kind"] == "IndexFlatIP":
        index = faiss.IndexFlatIP(int(vectors.shape[1]))
    else:
        nlist = min(64, max(4, int(math.sqrt(vectors.shape[0]))))
        quantizer = faiss.IndexFlatIP(int(vectors.shape[1]))
        index = faiss.IndexIVFFlat(
            quantizer, int(vectors.shape[1]), nlist, faiss.METRIC_INNER_PRODUCT
        )
        index.train(np.ascontiguousarray(vectors, dtype=np.float32))
        index.nprobe = min(8, nlist)
    index.add(np.ascontiguousarray(vectors, dtype=np.float32))
    if index.ntotal != vectors.shape[0]:
        raise IntegrityError("FAISS index did not ingest the full item matrix")
    return index


def serialize_faiss(index: Any) -> bytes:
    import faiss

    return np.asarray(faiss.serialize_index(index), dtype=np.uint8).tobytes()


def semantic_history_queries(
    history: Sequence[Interaction],
    semantic_vectors: np.ndarray,
    positive_min: int,
    dislike_max: int,
    dislike_weight: float,
) -> tuple[np.ndarray, np.ndarray]:
    positive = [event.item_index for event in history if event.rating >= positive_min]
    if not positive:
        raise IntegrityError("Semantic query has no positive history")
    positive_centroid = np.mean(
        semantic_vectors[np.asarray(positive, dtype=np.int64)], axis=0
    )
    dislikes = [event.item_index for event in history if event.rating <= dislike_max]
    if dislikes:
        dislike_centroid = np.mean(
            semantic_vectors[np.asarray(dislikes, dtype=np.int64)], axis=0
        )
        dislike_norm = float(np.linalg.norm(dislike_centroid))
        dislike_query = (
            dislike_centroid / dislike_norm
            if dislike_norm > 0.0
            else np.zeros_like(positive_centroid)
        )
    else:
        dislike_query = np.zeros_like(positive_centroid)
    centroid = positive_centroid - dislike_weight * dislike_query
    norm = float(np.linalg.norm(centroid))
    if not math.isfinite(norm) or norm <= 0.0:
        raise IntegrityError("Invalid semantic history centroid")
    return (
        np.ascontiguousarray(centroid / norm, dtype=np.float32),
        np.ascontiguousarray(dislike_query, dtype=np.float32),
    )


class BPRMatrixFactorization(nn.Module):
    def __init__(self, user_count: int, item_count: int, dimension: int) -> None:
        super().__init__()
        self.users = nn.Embedding(user_count, dimension)
        self.items = nn.Embedding(item_count, dimension)
        nn.init.normal_(self.users.weight, mean=0.0, std=0.05)
        nn.init.normal_(self.items.weight, mean=0.0, std=0.05)

    def pair_scores(
        self, users: torch.Tensor, chosen: torch.Tensor, rejected: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        query = self.users(users)
        return (
            torch.sum(query * self.items(chosen), dim=1),
            torch.sum(query * self.items(rejected), dim=1),
        )


def _sample_unseen(
    rng: np.random.Generator, seen: frozenset[int], item_count: int
) -> int:
    for _ in range(128):
        candidate = int(rng.integers(0, item_count))
        if candidate not in seen:
            return candidate
    available = np.asarray(sorted(set(range(item_count)) - set(seen)), dtype=np.int64)
    if not len(available):
        raise IntegrityError("A user has no unseen item for BPR training")
    return int(available[int(rng.integers(0, len(available)))])


def build_bpr_training_pairs(
    splits: Sequence[UserSplit],
    item_count: int,
    variant: str,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Mapping[str, Any]]:
    if variant not in {"implicit", "rating_aware"}:
        raise ValueError(variant)
    rng = np.random.default_rng(seed + (0 if variant == "implicit" else 100003))
    user_to_row = {split.user_id: row for row, split in enumerate(splits)}
    implicit: list[tuple[int, int, int, float]] = []
    natural: list[tuple[int, int, int, float]] = []
    positive_min = int(config["implicit_positive_rating_min"])
    minimum_gap = int(config["rating_aware_minimum_gap"])
    for split in splits:
        row = user_to_row[split.user_id]
        seen = frozenset(event.item_index for event in split.train)
        for event in split.train:
            if event.rating >= positive_min:
                implicit.append(
                    (row, event.item_index, _sample_unseen(rng, seen, item_count), 1.0)
                )
        if variant == "rating_aware":
            candidates: list[tuple[int, int, int, float]] = []
            train = split.train
            for left in range(len(train)):
                for right in range(left + 1, len(train)):
                    gap = train[left].rating - train[right].rating
                    if abs(gap) < minimum_gap:
                        continue
                    chosen, rejected = (
                        (train[left], train[right]) if gap > 0 else (train[right], train[left])
                    )
                    candidates.append(
                        (row, chosen.item_index, rejected.item_index, abs(gap) / 4.0)
                    )
            if len(candidates) > 250:
                selected = rng.choice(len(candidates), size=250, replace=False)
                candidates = [candidates[int(index)] for index in sorted(selected)]
            natural.extend(candidates)
    maximum = int(config["maximum_training_pairs"])
    if variant == "implicit":
        pool = implicit
    else:
        target_natural = int(round(maximum * float(config["rating_aware_natural_pair_fraction"])))
        target_implicit = maximum - target_natural

        def sample_pool(
            values: Sequence[tuple[int, int, int, float]], count: int
        ) -> list[tuple[int, int, int, float]]:
            if not values or count <= 0:
                return []
            indices = rng.choice(len(values), size=count, replace=len(values) < count)
            return [values[int(index)] for index in indices]

        pool = sample_pool(natural, target_natural) + sample_pool(implicit, target_implicit)
        rng.shuffle(pool)
    if len(pool) > maximum:
        selected = rng.choice(len(pool), size=maximum, replace=False)
        pool = [pool[int(index)] for index in selected]
    if not pool:
        raise IntegrityError(f"No {variant} BPR pairs")
    users, chosen, rejected, weights = zip(*pool, strict=True)
    return (
        np.asarray(users, dtype=np.int64),
        np.asarray(chosen, dtype=np.int64),
        np.asarray(rejected, dtype=np.int64),
        np.asarray(weights, dtype=np.float32),
        {
            "variant": variant,
            "selected_pairs": len(pool),
            "available_implicit_pairs": len(implicit),
            "available_natural_rating_gap_pairs": len(natural),
        },
    )


def train_bpr(
    splits: Sequence[UserSplit],
    item_count: int,
    variant: str,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[BPRArtifacts, Mapping[str, torch.Tensor]]:
    deterministic_setup(seed + (0 if variant == "implicit" else 100003))
    users, chosen, rejected, weights, diagnostics = build_bpr_training_pairs(
        splits, item_count, variant, config, seed
    )
    model = BPRMatrixFactorization(
        len(splits), item_count, int(config["embedding_dimension"])
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["l2_regularization"]),
    )
    batch_size = int(config["batch_size"])
    rng = np.random.default_rng(seed + 700001)
    trace: list[float] = []
    model.train()
    for _epoch in range(int(config["epochs"])):
        order = rng.permutation(len(users))
        losses: list[float] = []
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            user_tensor = torch.from_numpy(users[rows])
            chosen_tensor = torch.from_numpy(chosen[rows])
            rejected_tensor = torch.from_numpy(rejected[rows])
            weight_tensor = torch.from_numpy(weights[rows])
            positive, negative = model.pair_scores(
                user_tensor, chosen_tensor, rejected_tensor
            )
            loss = torch.mean(F.softplus(-(positive - negative)) * weight_tensor)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(config["gradient_clip_norm"])
            )
            optimizer.step()
            losses.append(float(loss.detach()))
        trace.append(float(np.mean(losses)))
    model.eval()
    user_vectors = np.ascontiguousarray(
        model.users.weight.detach().cpu().numpy(), dtype=np.float32
    )
    item_vectors = np.ascontiguousarray(
        model.items.weight.detach().cpu().numpy(), dtype=np.float32
    )
    if not np.all(np.isfinite(user_vectors)) or not np.all(np.isfinite(item_vectors)):
        raise IntegrityError("Raw trained BPR factors contain nonfinite values")
    user_ids = tuple(split.user_id for split in splits)
    artifacts = BPRArtifacts(
        variant=variant,
        user_ids=user_ids,
        user_to_row={user_id: row for row, user_id in enumerate(user_ids)},
        user_vectors=user_vectors,
        item_vectors=item_vectors,
        training_diagnostics={**diagnostics, "epoch_mean_losses": trace},
    )
    state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    return artifacts, state


def updated_bpr_query(
    bpr: BPRArtifacts,
    user_id: int,
    history: Sequence[Interaction],
    bpr_config: Mapping[str, Any],
) -> np.ndarray:
    """Update the user side from the same prefix while freezing item factors."""
    if bpr_config.get("prefix_query_update") != (
        "trained_user_plus_rating_weighted_frozen_item_aggregate"
    ):
        raise ValueError("Unregistered BPR prefix-query update")
    row = int(bpr.user_to_row[user_id])
    base = np.asarray(bpr.user_vectors[row], dtype=np.float32)
    if bpr.variant == "implicit":
        selected = [
            event for event in history if event.rating >= int(bpr_config["implicit_positive_rating_min"])
        ]
        weights = np.ones(len(selected), dtype=np.float32)
    else:
        selected = list(history)
        weights = np.asarray([event.rating - 3.0 for event in selected], dtype=np.float32)
    if selected and float(np.sum(np.abs(weights))) > 0.0:
        indices = np.asarray([event.item_index for event in selected], dtype=np.int64)
        aggregate = np.sum(bpr.item_vectors[indices] * weights[:, None], axis=0)
        aggregate /= float(np.sum(np.abs(weights)))
        query = base + float(bpr_config["prefix_query_update_weight"]) * aggregate
    else:
        query = base.copy()
    if not np.all(np.isfinite(query)) or float(np.linalg.norm(query)) <= 0.0:
        raise IntegrityError("Invalid prefix-updated BPR query")
    return np.ascontiguousarray(query, dtype=np.float32)


def search_unseen(
    index: Any,
    query: np.ndarray,
    blocked: frozenset[int],
    count: int,
    search_k: int,
) -> tuple[int, ...]:
    requested = min(index.ntotal, max(search_k, count + len(blocked)))
    _scores, indices = index.search(
        np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32), requested
    )
    selected: list[int] = []
    for raw in indices[0]:
        item = int(raw)
        if item < 0 or item in blocked or item in selected:
            continue
        selected.append(item)
        if len(selected) == count:
            break
    if len(selected) < count and requested < index.ntotal:
        _scores, indices = index.search(
            np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32), index.ntotal
        )
        selected = []
        for raw in indices[0]:
            item = int(raw)
            if item < 0 or item in blocked or item in selected:
                continue
            selected.append(item)
            if len(selected) == count:
                break
    if len(selected) < count:
        raise IntegrityError(
            f"Only {len(selected)} unseen candidates available; expected {count}"
        )
    return tuple(selected)


def build_candidate_context(
    split: UserSplit,
    history: Sequence[Interaction],
    bpr: BPRArtifacts,
    collaborative_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    bpr_config: Mapping[str, Any],
    embedding_config: Mapping[str, Any],
    dataset: Mapping[str, Any],
    retrieval: Mapping[str, Any],
    residual_config: Mapping[str, Any],
) -> CandidateContext:
    collaborative_query = updated_bpr_query(
        bpr, split.user_id, history, bpr_config
    )
    semantic_query, dislike_query = semantic_history_queries(
        history,
        semantic_vectors,
        int(dataset["positive_rating_min"]),
        int(dataset["dislike_rating_max"]),
        float(embedding_config["dislike_centroid_weight"]),
    )
    blocked = frozenset(event.item_index for event in history)
    collaborative = search_unseen(
        collaborative_index,
        collaborative_query,
        blocked,
        int(retrieval["collaborative_candidates"]),
        int(retrieval["search_k"]),
    )
    semantic = search_unseen(
        semantic_index,
        semantic_query,
        blocked,
        int(retrieval["semantic_candidates"]),
        int(retrieval["search_k"]),
    )
    # One-way support contract: B is copied first, never truncated, and the
    # semantic branch only appends previously unseen IDs.
    union = tuple(dict.fromkeys((*collaborative, *semantic)))
    if not set(collaborative).issubset(union):
        raise IntegrityError("B_u is not a subset of C_u")
    if len(union) > int(retrieval["maximum_union_candidates"]):
        raise IntegrityError("Hybrid union exceeds its registered bound")
    collaborative_scores = bpr.item_vectors[
        np.asarray(collaborative, dtype=np.int64)
    ] @ collaborative_query
    semantic_scores = semantic_vectors[np.asarray(semantic, dtype=np.int64)] @ semantic_query
    # The regret scale is derived only from immutable BPR-anchor candidates B,
    # never from the semantic union C.  This prevents semantic arrivals from
    # dilating the safety budget.
    lower_quantile = 100.0 * float(residual_config["regret_scale_lower_quantile"])
    upper_quantile = 100.0 * float(residual_config["regret_scale_upper_quantile"])
    scale_floor = float(residual_config["regret_scale_floor"])
    bpr_p5, bpr_p95 = np.percentile(
        collaborative_scores, [lower_quantile, upper_quantile]
    )
    raw_bpr_span = float(bpr_p95 - bpr_p5)
    semantic_p5, semantic_p95 = np.percentile(semantic_scores, [5.0, 95.0])
    return CandidateContext(
        user_id=split.user_id,
        collaborative=collaborative,
        semantic=semantic,
        union=union,
        semantic_query=semantic_query,
        dislike_query=dislike_query,
        collaborative_query=collaborative_query,
        history_log_feature=float(min(1.0, math.log1p(len(history)) / 8.0)),
        bpr_min=float(bpr_p5),
        bpr_span=max(raw_bpr_span, scale_floor),
        semantic_min=float(semantic_p5),
        semantic_span=max(float(semantic_p95 - semantic_p5), 1e-6),
        collaborative_rank={item: rank for rank, item in enumerate(collaborative)},
        semantic_rank={item: rank for rank, item in enumerate(semantic)},
        regret_scale_degenerate=raw_bpr_span <= scale_floor,
    )


def item_features(
    context: CandidateContext,
    items: Sequence[int],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    retrieval: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    indices = np.asarray(items, dtype=np.int64)
    bpr_raw = bpr.item_vectors[indices] @ context.collaborative_query
    semantic_raw = semantic_vectors[indices] @ context.semantic_query
    dislike_similarity = semantic_vectors[indices] @ context.dislike_query
    bpr_normalized = (bpr_raw - context.bpr_min) / context.bpr_span
    semantic_normalized = (semantic_raw - context.semantic_min) / context.semantic_span
    collaborative_denominator = max(1, int(retrieval["collaborative_candidates"]) - 1)
    semantic_denominator = max(1, int(retrieval["semantic_candidates"]) - 1)
    collaborative_rank = np.asarray(
        [
            context.collaborative_rank.get(int(item), collaborative_denominator)
            / collaborative_denominator
            for item in indices
        ],
        dtype=np.float32,
    )
    semantic_rank = np.asarray(
        [
            context.semantic_rank.get(int(item), semantic_denominator)
            / semantic_denominator
            for item in indices
        ],
        dtype=np.float32,
    )
    collaborative_membership = np.asarray(
        [float(int(item) in context.collaborative_rank) for item in indices],
        dtype=np.float32,
    )
    semantic_membership = np.asarray(
        [float(int(item) in context.semantic_rank) for item in indices],
        dtype=np.float32,
    )
    features = np.stack(
        (
            semantic_normalized,
            bpr_normalized,
            semantic_normalized * bpr_normalized,
            semantic_normalized - bpr_normalized,
            collaborative_rank,
            semantic_rank,
            collaborative_membership,
            semantic_membership,
            popularity[indices],
            dislike_similarity.astype(np.float32),
            np.full(len(indices), context.history_log_feature, dtype=np.float32),
            np.ones(len(indices), dtype=np.float32),
        ),
        axis=1,
    ).astype(np.float32, copy=False)
    if not np.all(np.isfinite(features)):
        raise IntegrityError("CAPER feature matrix contains nonfinite values")
    return features, bpr_normalized.astype(np.float32), semantic_normalized.astype(np.float32)


def compute_train_popularity(
    splits: Sequence[UserSplit], item_count: int
) -> np.ndarray:
    counts = np.zeros(item_count, dtype=np.float64)
    for split in splits:
        for event in split.train:
            counts[event.item_index] += 1.0
    transformed = np.log1p(counts)
    maximum = float(np.max(transformed))
    if maximum > 0.0:
        transformed /= maximum
    return transformed.astype(np.float32)


def build_prefix_candidate_manifest(
    splits: Sequence[UserSplit],
    bpr: BPRArtifacts,
    collaborative_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    config: Mapping[str, Any],
    stage: str,
) -> tuple[Mapping[int, CandidateContext], list[Mapping[str, Any]]]:
    """Build label-blind A or A+R manifests for later exclusive publication."""
    if stage not in {"alignment", "validation"}:
        raise ValueError(stage)
    contexts: dict[int, CandidateContext] = {}
    serializable: list[Mapping[str, Any]] = []
    for split in splits:
        history = split.train if stage == "alignment" else (*split.train, *split.alignment)
        context = build_candidate_context(
            split,
            history,
            bpr,
            collaborative_index,
            semantic_vectors,
            semantic_index,
            config["bpr"],
            config["embedding"],
            config["dataset"],
            config["retrieval"],
            config["residual"],
        )
        contexts[split.user_id] = context
        serializable.append(
            {
                "stage": stage,
                "bpr_variant": bpr.variant,
                "user_id": split.user_id,
                "history_event_count": len(history),
                "history_max_timestamp": max(event.timestamp for event in history),
                "selected_bpr_candidates_B": list(context.collaborative),
                "semantic_candidates_S": list(context.semantic),
                "union_candidates_C": list(context.union),
                "B_subset_C": set(context.collaborative).issubset(context.union),
                "future_block_labels_joined": False,
            }
        )
    return contexts, serializable


def build_alignment_corpora(
    splits: Sequence[UserSplit],
    candidate_manifest: Mapping[int, CandidateContext],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[AlignmentCorpus, AlignmentCorpus]:
    """Return contradiction-balanced and uniform natural-pair corpora."""
    dataset = config["dataset"]
    retrieval = config["retrieval"]
    gap_min = int(dataset["preference_pair_minimum_rating_gap"])
    rows: list[tuple[np.ndarray, np.ndarray, float, float, int, bool]] = []
    users_with_natural_pairs: set[int] = set()
    union_rated_items = 0
    alignment_rated_items = 0
    for split in splits:
        context = candidate_manifest[split.user_id]
        ratings: dict[int, int] = {}
        for event in split.alignment:
            alignment_rated_items += 1
            if event.item_index in context.union:
                ratings[event.item_index] = event.rating
                union_rated_items += 1
        items = sorted(ratings)
        user_rows: list[tuple[np.ndarray, np.ndarray, float, float, int, bool]] = []
        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                gap = ratings[items[left]] - ratings[items[right]]
                if abs(gap) < gap_min:
                    continue
                chosen, rejected = (
                    (items[left], items[right]) if gap > 0 else (items[right], items[left])
                )
                if chosen not in context.union or rejected not in context.union:
                    raise IntegrityError("An alignment target was injected outside the union")
                features, base, _semantic = item_features(
                    context,
                    [chosen, rejected],
                    bpr,
                    semantic_vectors,
                    popularity,
                    retrieval,
                )
                contradiction = bool(base[0] <= base[1])
                user_rows.append(
                    (
                        features[0].copy(),
                        features[1].copy(),
                        float(base[0]),
                        float(base[1]),
                        split.user_id,
                        contradiction,
                    )
                )
        if user_rows:
            users_with_natural_pairs.add(split.user_id)
            rows.extend(user_rows)
    if not rows:
        raise IntegrityError("No natural rating-gap pairs were present in alignment unions")
    contradiction_indices = np.asarray(
        [index for index, row in enumerate(rows) if row[5]], dtype=np.int64
    )
    ordinary_indices = np.asarray(
        [index for index, row in enumerate(rows) if not row[5]], dtype=np.int64
    )
    if not len(contradiction_indices) or not len(ordinary_indices):
        raise IntegrityError("Exact half-contradiction scheduling is impossible")
    if len(users_with_natural_pairs) < int(dataset["minimum_pair_bearing_users"]):
        raise IntegrityError(
            "Raw alignment cohort has too few pair-bearing users before oversampling"
        )
    if len(contradiction_indices) < int(dataset["minimum_bpr_contradiction_pairs"]):
        raise IntegrityError(
            "Raw alignment cohort has too few BPR contradictions before oversampling"
        )
    if len(ordinary_indices) < int(dataset["minimum_bpr_agreement_pairs"]):
        raise IntegrityError(
            "Raw alignment cohort has too few BPR agreements before oversampling"
        )
    rng = np.random.default_rng(seed + 900001)
    maximum = int(config["residual"]["maximum_alignment_pairs"])
    matched_count = min(maximum, len(rows))
    matched_count -= matched_count % 2
    if matched_count < 2:
        raise IntegrityError("Matched alignment pair budget is empty")
    half = matched_count // 2
    selected_contradictions = rng.choice(
        contradiction_indices, size=half, replace=len(contradiction_indices) < half
    )
    selected_ordinary = rng.choice(
        ordinary_indices, size=half, replace=len(ordinary_indices) < half
    )
    balanced_indices = np.concatenate((selected_contradictions, selected_ordinary))
    rng.shuffle(balanced_indices)
    uniform_indices = rng.choice(len(rows), size=matched_count, replace=False)

    def materialize(indices: np.ndarray, schedule: str) -> AlignmentCorpus:
        selected = [rows[int(index)] for index in indices]
        contradiction_count = sum(bool(row[5]) for row in selected)
        return AlignmentCorpus(
            chosen_features=np.stack([row[0] for row in selected]).astype(np.float32),
            rejected_features=np.stack([row[1] for row in selected]).astype(np.float32),
            chosen_base_scores=np.asarray([row[2] for row in selected], dtype=np.float32),
            rejected_base_scores=np.asarray([row[3] for row in selected], dtype=np.float32),
            user_ids=np.asarray([row[4] for row in selected], dtype=np.int64),
            contradiction_mask=np.asarray([row[5] for row in selected], dtype=np.bool_),
            diagnostics={
                "schedule": schedule,
                "selected_pairs": len(selected),
                "selected_unique_raw_pairs": len(set(map(int, indices))),
                "replacement_duplicates": len(selected) - len(set(map(int, indices))),
                "matched_pair_budget_across_schedules": matched_count,
                "selected_contradictions": contradiction_count,
                "selected_contradiction_fraction": contradiction_count / len(selected),
                "raw_natural_pairs": len(rows),
                "raw_contradictions": len(contradiction_indices),
                "raw_noncontradictions": len(ordinary_indices),
                "users_with_natural_pairs": len(users_with_natural_pairs),
                "alignment_rated_items": alignment_rated_items,
                "alignment_rated_items_in_union": union_rated_items,
                "all_pairs_are_natural_and_union_present": True,
                "targets_injected": False,
            },
        )

    balanced = materialize(balanced_indices, "half_bpr_contradictions")
    uniform = materialize(uniform_indices, "uniform_natural_pairs")
    if not math.isclose(
        float(balanced.diagnostics["selected_contradiction_fraction"]), 0.5
    ):
        raise IntegrityError("Balanced corpus is not exactly half contradictions")
    return balanced, uniform


class BoundedResidual(nn.Module):
    def __init__(self, feature_count: int, hidden: int, bound: float) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(feature_count, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )
        self.bound = float(bound)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.bound * torch.tanh(self.network(features).squeeze(1))


def train_residual(
    corpus: AlignmentCorpus,
    initial_state: Mapping[str, torch.Tensor],
    residual_config: Mapping[str, Any],
    seed: int,
    margin: float,
    anchor_coefficient: float,
) -> tuple[BoundedResidual, Mapping[str, Any]]:
    deterministic_setup(seed)
    model = BoundedResidual(
        int(corpus.chosen_features.shape[1]),
        int(residual_config["hidden_dimension"]),
        float(residual_config["residual_bound"]),
    )
    model.load_state_dict(initial_state)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(residual_config["learning_rate"]),
        weight_decay=float(residual_config["weight_decay"]),
    )
    rng = np.random.default_rng(seed + 950001)
    batch_size = int(residual_config["batch_size"])
    beta = float(residual_config["simpo_beta"])
    temperature = float(residual_config["temperature"])
    traces: list[Mapping[str, float]] = []
    model.train()
    for _epoch in range(int(residual_config["epochs"])):
        order = rng.permutation(len(corpus.user_ids))
        epoch_loss: list[float] = []
        epoch_pref: list[float] = []
        epoch_anchor: list[float] = []
        epoch_kl: list[float] = []
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            chosen_features = torch.from_numpy(corpus.chosen_features[rows])
            rejected_features = torch.from_numpy(corpus.rejected_features[rows])
            chosen_base = torch.from_numpy(corpus.chosen_base_scores[rows])
            rejected_base = torch.from_numpy(corpus.rejected_base_scores[rows])
            contradiction_mask = torch.from_numpy(corpus.contradiction_mask[rows])
            chosen_residual = model(chosen_features)
            rejected_residual = model(rejected_features)
            score_gap = (
                chosen_base
                + chosen_residual
                - rejected_base
                - rejected_residual
            ) / temperature
            # For a one-step item policy, the log-normalizer cancels from the
            # chosen/rejected log-probability ratio.  This is the SimPO margin
            # objective without a DPO reference model.
            preference_loss = -F.logsigmoid(beta * score_gap - margin).mean()
            l2_anchor = 0.5 * (
                chosen_residual.square().mean() + rejected_residual.square().mean()
            )
            base_probability = torch.sigmoid(
                (chosen_base - rejected_base).detach() / temperature
            ).clamp(1e-6, 1.0 - 1e-6)
            adjusted_probability = torch.sigmoid(score_gap).clamp(1e-6, 1.0 - 1e-6)
            pair_kl = (
                base_probability
                * (torch.log(base_probability) - torch.log(adjusted_probability))
                + (1.0 - base_probability)
                * (
                    torch.log(1.0 - base_probability)
                    - torch.log(1.0 - adjusted_probability)
                )
            )
            noncontradiction = (~contradiction_mask).to(pair_kl.dtype)
            masked_kl = torch.sum(pair_kl * noncontradiction) / torch.clamp(
                torch.sum(noncontradiction), min=1.0
            )
            anchor_loss = l2_anchor + float(
                residual_config["soft_anchor_kl_relative_weight"]
            ) * masked_kl
            loss = preference_loss + anchor_coefficient * anchor_loss
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(residual_config["gradient_clip_norm"])
            )
            optimizer.step()
            epoch_loss.append(float(loss.detach()))
            epoch_pref.append(float(preference_loss.detach()))
            epoch_anchor.append(float(anchor_loss.detach()))
            epoch_kl.append(float(masked_kl.detach()))
        traces.append(
            {
                "loss": float(np.mean(epoch_loss)),
                "preference_loss": float(np.mean(epoch_pref)),
                "anchor_loss": float(np.mean(epoch_anchor)),
                "noncontradiction_kl": float(np.mean(epoch_kl)),
            }
        )
    model.eval()
    return model, {
        "simpo_derived": True,
        "reference_model": False,
        "margin": margin,
        "anchor_coefficient": anchor_coefficient,
        "anchor_components": "bounded_residual_L2_plus_noncontradiction_masked_pairwise_KL",
        "epoch_trace": traces,
        "corpus": dict(corpus.diagnostics),
    }


def residual_numpy(model: BoundedResidual, features: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        result = model(torch.from_numpy(np.ascontiguousarray(features, dtype=np.float32)))
    values = result.cpu().numpy().astype(np.float32, copy=False)
    if not np.all(np.isfinite(values)):
        raise IntegrityError("Residual scorer produced nonfinite values")
    return values


def rank_descending(items: Sequence[int], scores: np.ndarray) -> list[int]:
    if len(items) != len(scores):
        raise ValueError("items/scores length mismatch")
    order = sorted(
        range(len(items)), key=lambda index: (-float(scores[index]), int(items[index]))
    )
    return [int(items[index]) for index in order]


def hard_regret_projection(
    items: Sequence[int],
    proposed_scores: np.ndarray,
    anchor_scores: np.ndarray,
    k: int,
    budget: float,
    regret_scale_degenerate: bool = False,
) -> tuple[list[int], Mapping[str, Any]]:
    """Greedily project top-k membership under cumulative BPR-score regret."""
    if len(items) < k:
        raise IntegrityError("Candidate union is smaller than projection k")
    anchor_order = rank_descending(items, anchor_scores)
    proposal_order = rank_descending(items, proposed_scores)
    if regret_scale_degenerate or budget <= 0.0:
        return anchor_order, {
            "normalized_bpr_regret": 0.0,
            "budget": float(budget),
            "accepted_preference_exceptions": 0,
            "normalizer_source": "registered_immutable_BPR_quantile_span",
            "degenerate_scale_fallback_to_bpr": bool(regret_scale_degenerate),
            "zero_budget_exact_anchor_recovery": bool(budget <= 0.0),
        }
    anchor_by_item = {
        int(item): float(anchor_scores[index]) for index, item in enumerate(items)
    }
    proposal_by_item = {
        int(item): float(proposed_scores[index]) for index, item in enumerate(items)
    }
    anchor_top = anchor_order[:k]
    selected = set(anchor_top)
    permanently_removed: set[int] = set()
    anchor_sum = sum(anchor_by_item[item] for item in anchor_top)
    accepted_exceptions = 0
    for proposed in proposal_order:
        if proposed in selected or proposed in permanently_removed:
            continue
        current_anchor_sum = sum(anchor_by_item[item] for item in selected)
        feasible: list[tuple[float, float, float, int]] = []
        for removable in selected:
            proposal_gain = proposal_by_item[proposed] - proposal_by_item[removable]
            if proposal_gain <= 0.0:
                continue
            tentative_sum = (
                current_anchor_sum - anchor_by_item[removable] + anchor_by_item[proposed]
            )
            regret = max(0.0, anchor_sum - tentative_sum)
            if regret > budget + 1e-9:
                continue
            incremental_cost = max(
                0.0, anchor_by_item[removable] - anchor_by_item[proposed]
            )
            efficiency = proposal_gain / (incremental_cost + 1e-12)
            feasible.append((efficiency, proposal_gain, -incremental_cost, removable))
        if feasible:
            _efficiency, _gain, _negative_cost, removable = max(
                feasible, key=lambda value: (value[0], value[1], value[2], -value[3])
            )
            selected.remove(removable)
            permanently_removed.add(removable)
            selected.add(proposed)
            accepted_exceptions += 1
    final_regret = max(
        0.0, anchor_sum - sum(anchor_by_item[item] for item in selected)
    )
    if final_regret > budget + 1e-7:
        raise IntegrityError("Hard regret projection exceeded its budget")
    top = sorted(selected, key=lambda item: (-proposal_by_item[item], item))
    tail = [item for item in proposal_order if item not in selected]
    return top + tail, {
        "normalized_bpr_regret": float(final_regret),
        "budget": float(budget),
        "accepted_preference_exceptions": accepted_exceptions,
        "normalizer_source": "P95_minus_P5_of_immutable_BPR_anchor_candidates_only",
    }


def binary_ndcg(ranking: Sequence[int], positives: frozenset[int], k: int) -> float:
    if not positives:
        return float("nan")
    dcg = sum(
        (1.0 / math.log2(rank + 2.0))
        for rank, item in enumerate(ranking[:k])
        if item in positives
    )
    ideal_hits = min(k, len(positives))
    ideal = sum(1.0 / math.log2(rank + 2.0) for rank in range(ideal_hits))
    return float(dcg / ideal)


def recall_at_k(ranking: Sequence[int], positives: frozenset[int], k: int) -> float:
    if not positives:
        return float("nan")
    return float(len(set(ranking[:k]) & set(positives)) / len(positives))


def preference_pairs(
    events: Sequence[Interaction],
    minimum_gap: int,
    maximum: int,
    subsample_seed: int,
    user_id: int,
) -> tuple[list[tuple[int, int]], int]:
    pairs: list[tuple[int, int]] = []
    ordered = sorted(events, key=lambda event: (event.item_index, event.ordinal))
    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            gap = ordered[left].rating - ordered[right].rating
            if abs(gap) < minimum_gap:
                continue
            pairs.append(
                (
                    ordered[left].item_index,
                    ordered[right].item_index,
                )
                if gap > 0
                else (
                    ordered[right].item_index,
                    ordered[left].item_index,
                )
            )
    raw_count = len(pairs)
    if len(pairs) > maximum:
        pairs = sorted(
            pairs,
            key=lambda pair: (
                hashlib.sha256(
                    f"{subsample_seed}:{user_id}:{pair[0]}:{pair[1]}".encode("ascii")
                ).hexdigest(),
                pair,
            ),
        )[:maximum]
    return pairs, raw_count


def validation_ndcg_for_bpr(
    splits: Sequence[UserSplit],
    candidate_manifest: Mapping[int, CandidateContext],
    config: Mapping[str, Any],
) -> float:
    values: list[float] = []
    positive_min = int(config["dataset"]["positive_rating_min"])
    for split in splits:
        ranking = candidate_manifest[split.user_id].collaborative
        targets = frozenset(
            event.item_index for event in split.validation if event.rating >= positive_min
        )
        values.append(binary_ndcg(ranking, targets, int(config["evaluation"]["ndcg_k"])))
    return float(np.nanmean(values))


def choose_linear_alpha(
    splits: Sequence[UserSplit],
    candidate_manifest: Mapping[int, CandidateContext],
    bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    config: Mapping[str, Any],
) -> tuple[float, Mapping[str, float]]:
    grid = [float(value) for value in config["residual"]["linear_fusion_validation_grid"]]
    by_alpha: dict[str, list[float]] = {str(alpha): [] for alpha in grid}
    positive_min = int(config["dataset"]["positive_rating_min"])
    for split in splits:
        context = candidate_manifest[split.user_id]
        _features, base, semantic = item_features(
            context,
            context.union,
            bpr,
            semantic_vectors,
            popularity,
            config["retrieval"],
        )
        targets = frozenset(
            event.item_index for event in split.validation if event.rating >= positive_min
        )
        for alpha in grid:
            scores = alpha * base + (1.0 - alpha) * semantic
            ranking, _projection = hard_regret_projection(
                context.union,
                scores,
                base,
                int(config["residual"]["projection_k"]),
                float(config["residual"]["hard_cumulative_normalized_bpr_regret_budget"]),
                context.regret_scale_degenerate,
            )
            by_alpha[str(alpha)].append(
                binary_ndcg(ranking, targets, int(config["evaluation"]["ndcg_k"]))
            )
    means = {key: float(np.nanmean(values)) for key, values in by_alpha.items()}
    selected = max(grid, key=lambda alpha: (means[str(alpha)], alpha))
    return float(selected), means


def method_scores_for_items(
    method: str,
    context: CandidateContext,
    items: Sequence[int],
    bpr: BPRArtifacts,
    implicit_bpr: BPRArtifacts,
    rating_bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    retrieval: Mapping[str, Any],
    residual_models: Mapping[str, BoundedResidual],
    linear_alpha: float,
    implicit_query: np.ndarray | None = None,
    rating_query: np.ndarray | None = None,
) -> np.ndarray:
    features, base, semantic = item_features(
        context, items, bpr, semantic_vectors, popularity, retrieval
    )
    indices = np.asarray(items, dtype=np.int64)
    if method == "implicit_bpr":
        query = (
            implicit_query
            if implicit_query is not None
            else implicit_bpr.user_vectors[int(implicit_bpr.user_to_row[context.user_id])]
        )
        return implicit_bpr.item_vectors[indices] @ query
    if method == "rating_aware_bpr":
        query = (
            rating_query
            if rating_query is not None
            else rating_bpr.user_vectors[int(rating_bpr.user_to_row[context.user_id])]
        )
        return rating_bpr.item_vectors[indices] @ query
    if method == "selected_bpr":
        return base
    if method in {"linear_fusion_projected", "linear_fusion_unprojected"}:
        return linear_alpha * base + (1.0 - linear_alpha) * semantic
    model_key = {
        "zero_margin_projected": "zero_margin",
        "unanchored_projected": "unanchored",
        "unanchored_unprojected": "unanchored",
        "uniform_pair_projected": "uniform_pair",
        "soft_anchor_only": "caper",
        "caper": "caper",
    }.get(method)
    if model_key is None:
        raise ValueError(method)
    return base + residual_numpy(residual_models[model_key], features)


def build_test_candidate_manifest(
    splits: Sequence[UserSplit],
    selected_bpr: BPRArtifacts,
    selected_index: Any,
    implicit_bpr: BPRArtifacts,
    implicit_index: Any,
    rating_bpr: BPRArtifacts,
    rating_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    config: Mapping[str, Any],
) -> tuple[Mapping[int, CandidateManifestEntry], list[Mapping[str, Any]]]:
    """Materialize target-blind test candidates before any B-block label join."""
    manifest: dict[int, CandidateManifestEntry] = {}
    serializable: list[Mapping[str, Any]] = []
    for split in splits:
        # Only the chronological A-prefix is visible here.  This function does
        # not read split.test, its ratings, targets, or dislike labels.
        history = (*split.train, *split.alignment, *split.validation)
        blocked = frozenset(event.item_index for event in history)
        context = build_candidate_context(
            split,
            history,
            selected_bpr,
            selected_index,
            semantic_vectors,
            semantic_index,
            config["bpr"],
            config["embedding"],
            config["dataset"],
            config["retrieval"],
            config["residual"],
        )
        implicit_query = updated_bpr_query(
            implicit_bpr, split.user_id, history, config["bpr"]
        )
        rating_query = updated_bpr_query(
            rating_bpr, split.user_id, history, config["bpr"]
        )
        implicit_candidates = search_unseen(
            implicit_index,
            implicit_query,
            blocked,
            int(config["retrieval"]["collaborative_candidates"]),
            int(config["retrieval"]["search_k"]),
        )
        rating_candidates = search_unseen(
            rating_index,
            rating_query,
            blocked,
            int(config["retrieval"]["collaborative_candidates"]),
            int(config["retrieval"]["search_k"]),
        )
        if not set(context.collaborative).issubset(context.union):
            raise IntegrityError("Candidate manifest violates B subset C")
        entry = CandidateManifestEntry(
            context,
            implicit_candidates,
            rating_candidates,
            implicit_query,
            rating_query,
        )
        if split.user_id in manifest:
            raise IntegrityError("Duplicate user in candidate manifest")
        manifest[split.user_id] = entry
        serializable.append(
            {
                "user_id": split.user_id,
                "history_event_count": len(history),
                "history_max_timestamp": max(event.timestamp for event in history),
                "implicit_bpr_candidates": list(implicit_candidates),
                "rating_aware_bpr_candidates": list(rating_candidates),
                "selected_bpr_candidates_B": list(context.collaborative),
                "semantic_candidates_S": list(context.semantic),
                "union_candidates_C": list(context.union),
                "B_subset_C": True,
                "target_labels_joined": False,
                "queries_use_same_train_alignment_validation_prefix": True,
            }
        )
    if set(manifest) != {split.user_id for split in splits}:
        raise IntegrityError("Candidate manifest does not cover the sealed cohort")
    return manifest, serializable


def select_mechanism_comparator_on_validation(
    splits: Sequence[UserSplit],
    candidate_manifest: Mapping[int, CandidateContext],
    selected_bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    residual_models: Mapping[str, BoundedResidual],
    linear_alpha: float,
    implicit_bpr: BPRArtifacts,
    rating_bpr: BPRArtifacts,
    config: Mapping[str, Any],
) -> tuple[str, Mapping[str, float]]:
    comparators = (
        "linear_fusion_projected",
        "zero_margin_projected",
        "unanchored_projected",
        "unanchored_unprojected",
        "uniform_pair_projected",
    )
    values: dict[str, list[float]] = {method: [] for method in comparators}
    positive_min = int(config["dataset"]["positive_rating_min"])
    for split in splits:
        context = candidate_manifest[split.user_id]
        _features, anchor, _semantic = item_features(
            context,
            context.union,
            selected_bpr,
            semantic_vectors,
            popularity,
            config["retrieval"],
        )
        targets = frozenset(
            event.item_index for event in split.validation if event.rating >= positive_min
        )
        for method in comparators:
            scores = method_scores_for_items(
                method,
                context,
                context.union,
                selected_bpr,
                implicit_bpr,
                rating_bpr,
                semantic_vectors,
                popularity,
                config["retrieval"],
                residual_models,
                linear_alpha,
            )
            ranking, _diagnostics = hard_regret_projection(
                context.union,
                scores,
                anchor,
                int(config["residual"]["projection_k"]),
                float(config["residual"]["hard_cumulative_normalized_bpr_regret_budget"]),
                context.regret_scale_degenerate,
            )
            values[method].append(
                binary_ndcg(ranking, targets, int(config["evaluation"]["ndcg_k"]))
            )
    means = {method: float(np.nanmean(scores)) for method, scores in values.items()}
    selected = max(comparators, key=lambda method: (means[method], method))
    return selected, means


def evaluate_seed(
    splits: Sequence[UserSplit],
    candidate_manifest: Mapping[int, CandidateManifestEntry],
    selected_bpr: BPRArtifacts,
    implicit_bpr: BPRArtifacts,
    rating_bpr: BPRArtifacts,
    semantic_vectors: np.ndarray,
    popularity: np.ndarray,
    residual_models: Mapping[str, BoundedResidual],
    linear_alpha: float,
    config: Mapping[str, Any],
) -> tuple[Mapping[str, list[Mapping[str, Any]]], Mapping[str, Any]]:
    methods = (
        "implicit_bpr",
        "rating_aware_bpr",
        "selected_bpr",
        "linear_fusion_projected",
        "linear_fusion_unprojected",
        "zero_margin_projected",
        "unanchored_projected",
        "uniform_pair_projected",
        "soft_anchor_only",
        "caper",
    )
    projected = {
        "linear_fusion_projected",
        "zero_margin_projected",
        "unanchored_projected",
        "uniform_pair_projected",
        "caper",
    }
    rows: dict[str, list[Mapping[str, Any]]] = {method: [] for method in methods}
    inclusion_all = True
    max_regret: dict[str, float] = {method: 0.0 for method in projected}
    total_pairs = 0
    raw_total_pairs_before_cap = 0
    pair_bearing_users = 0
    bpr_agreement_pairs = 0
    bpr_contradiction_pairs = 0
    bpr_tied_pairs = 0
    for split in splits:
        entry = candidate_manifest[split.user_id]
        context = entry.context
        inclusion = set(context.collaborative).issubset(context.union)
        inclusion_all = inclusion_all and inclusion
        implicit_ranking = entry.implicit_candidates
        rating_ranking = entry.rating_aware_candidates
        targets = frozenset(
            event.item_index
            for event in split.test
            if event.rating >= int(config["dataset"]["positive_rating_min"])
        )
        dislikes = frozenset(
            event.item_index
            for event in split.test
            if event.rating <= int(config["dataset"]["dislike_rating_max"])
        )
        pairs, raw_pair_count = preference_pairs(
            [event for event in split.test if event.item_index in context.union],
            int(config["dataset"]["preference_pair_minimum_rating_gap"]),
            int(config["evaluation"]["maximum_preference_pairs_per_user"]),
            int(config["evaluation"]["preference_pair_subsample_seed"]),
            split.user_id,
        )
        total_pairs += len(pairs)
        raw_total_pairs_before_cap += raw_pair_count
        pair_bearing_users += int(bool(pairs))
        _features, anchor_scores, _semantic = item_features(
            context,
            context.union,
            selected_bpr,
            semantic_vectors,
            popularity,
            config["retrieval"],
        )
        rankings: dict[str, list[int]] = {
            "implicit_bpr": list(implicit_ranking),
            "rating_aware_bpr": list(rating_ranking),
            "selected_bpr": list(context.collaborative),
        }
        method_union_scores: dict[str, np.ndarray] = {}
        for method in methods:
            if method in rankings:
                continue
            scores = method_scores_for_items(
                method,
                context,
                context.union,
                selected_bpr,
                implicit_bpr,
                rating_bpr,
                semantic_vectors,
                popularity,
                config["retrieval"],
                residual_models,
                linear_alpha,
            )
            method_union_scores[method] = scores
            if method in projected:
                ranking, projection = hard_regret_projection(
                    context.union,
                    scores,
                    anchor_scores,
                    int(config["residual"]["projection_k"]),
                    float(
                        config["residual"][
                            "hard_cumulative_normalized_bpr_regret_budget"
                        ]
                    ),
                    context.regret_scale_degenerate,
                )
                max_regret[method] = max(
                    max_regret[method], float(projection["normalized_bpr_regret"])
                )
                rankings[method] = ranking
            else:
                rankings[method] = rank_descending(context.union, scores)

        for method in methods:
            ranking = rankings[method]
            correct = 0
            for chosen, rejected in pairs:
                pair_scores = method_scores_for_items(
                    method,
                    context,
                    [chosen, rejected],
                    selected_bpr,
                    implicit_bpr,
                    rating_bpr,
                    semantic_vectors,
                    popularity,
                    config["retrieval"],
                    residual_models,
                    linear_alpha,
                    implicit_query=entry.implicit_query,
                    rating_query=entry.rating_aware_query,
                )
                gap = float(pair_scores[0]) - float(pair_scores[1])
                correct += 1.0 if gap > 0.0 else (0.5 if gap == 0.0 else 0.0)
                if method == "selected_bpr":
                    if gap > 0.0:
                        bpr_agreement_pairs += 1
                    elif gap < 0.0:
                        bpr_contradiction_pairs += 1
                    else:
                        bpr_tied_pairs += 1
            if method == "implicit_bpr":
                candidate_recall = recall_at_k(
                    implicit_ranking, targets, len(implicit_ranking)
                )
            elif method == "rating_aware_bpr":
                candidate_recall = recall_at_k(rating_ranking, targets, len(rating_ranking))
            elif method == "selected_bpr":
                candidate_recall = recall_at_k(
                    context.collaborative, targets, len(context.collaborative)
                )
            else:
                candidate_recall = recall_at_k(context.union, targets, len(context.union))
            rows[method].append(
                {
                    "user_id": split.user_id,
                    "ndcg_at_10": binary_ndcg(
                        ranking, targets, int(config["evaluation"]["ndcg_k"])
                    ),
                    "recall_at_10": recall_at_k(
                        ranking, targets, int(config["evaluation"]["recall_k"])
                    ),
                    "candidate_recall": candidate_recall,
                    "union_candidate_recall_at_most_400": recall_at_k(
                        context.union, targets, len(context.union)
                    ),
                    "bpr_anchor_candidate_recall_at_200": recall_at_k(
                        context.collaborative, targets, len(context.collaborative)
                    ),
                    "preference_pairs": len(pairs),
                    "raw_natural_preference_pairs_before_cap": raw_pair_count,
                    "preference_correct": float(correct),
                    "preference_pair_accuracy": (
                        float(correct / len(pairs)) if pairs else float("nan")
                    ),
                    "future_dislike_intrusion_at_10": float(
                        len(set(ranking[:10]) & set(dislikes)) / 10.0
                    ),
                    "candidate_support_inclusion": inclusion,
                    "candidate_union_size": len(context.union),
                }
            )
    return rows, {
        "candidate_support_inclusion_all_requests": inclusion_all,
        "heldout_preference_pairs": total_pairs,
        "raw_heldout_preference_pairs_before_hash_cap": raw_total_pairs_before_cap,
        "pair_bearing_test_users": pair_bearing_users,
        "test_bpr_agreement_pairs": bpr_agreement_pairs,
        "test_bpr_contradiction_pairs": bpr_contradiction_pairs,
        "test_bpr_tied_pairs": bpr_tied_pairs,
        "maximum_normalized_bpr_regret": max_regret,
        "regret_budget": float(
            config["residual"]["hard_cumulative_normalized_bpr_regret_budget"]
        ),
        "candidate_targets_injected": False,
    }


NUMERIC_USER_METRICS = (
    "ndcg_at_10",
    "recall_at_10",
    "candidate_recall",
    "union_candidate_recall_at_most_400",
    "bpr_anchor_candidate_recall_at_200",
    "preference_pair_accuracy",
    "future_dislike_intrusion_at_10",
    "candidate_union_size",
)


def summarize_rows(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    summary: dict[str, Any] = {"users": len(rows)}
    for metric in NUMERIC_USER_METRICS:
        values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
        finite = values[np.isfinite(values)]
        summary[metric] = float(np.mean(finite)) if len(finite) else None
        summary[f"{metric}_cohort_users"] = int(len(finite))
    summary["preference_pair_accuracy_aggregation"] = "user_macro_ties_half"
    summary["preference_pairs"] = float(
        sum(float(row["preference_pairs"]) for row in rows)
    )
    if rows and all("preference_correct" in row for row in rows):
        total_pairs = float(sum(float(row["preference_pairs"]) for row in rows))
        total_correct = float(sum(float(row["preference_correct"]) for row in rows))
        summary["preference_pair_accuracy_pair_micro_diagnostic"] = (
            float(total_correct / total_pairs) if total_pairs else None
        )
    else:
        summary["preference_pair_accuracy_pair_micro_diagnostic"] = None
    summary["candidate_support_inclusion_all"] = all(
        bool(row["candidate_support_inclusion"]) for row in rows
    )
    return summary


def average_rows_across_seeds(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
    method_by_seed: Mapping[int, str],
) -> list[Mapping[str, Any]]:
    by_user: dict[int, dict[str, list[float]]] = defaultdict(
        lambda: {metric: [] for metric in NUMERIC_USER_METRICS}
    )
    support: dict[int, list[bool]] = defaultdict(list)
    pair_counts: dict[int, list[int]] = defaultdict(list)
    correct_counts: dict[int, list[float]] = defaultdict(list)
    for seed, methods in per_seed_rows.items():
        method = method_by_seed[seed]
        for row in methods[method]:
            user_id = int(row["user_id"])
            for metric in NUMERIC_USER_METRICS:
                value = float(row[metric])
                if math.isfinite(value):
                    by_user[user_id][metric].append(value)
            support[user_id].append(bool(row["candidate_support_inclusion"]))
            pair_counts[user_id].append(int(row["preference_pairs"]))
            correct_counts[user_id].append(float(row["preference_correct"]))
    averaged: list[Mapping[str, Any]] = []
    for user_id in sorted(by_user):
        row: dict[str, Any] = {"user_id": user_id}
        for metric in NUMERIC_USER_METRICS:
            values = by_user[user_id][metric]
            row[metric] = float(np.mean(values)) if values else float("nan")
        row["candidate_support_inclusion"] = all(support[user_id])
        row["preference_pairs"] = float(np.mean(pair_counts[user_id]))
        row["preference_correct"] = float(np.mean(correct_counts[user_id]))
        averaged.append(row)
    return averaged


def paired_user_cluster_bootstrap(
    proposed: Sequence[Mapping[str, Any]],
    baseline: Sequence[Mapping[str, Any]],
    metric: str,
    repetitions: int,
    alpha: float,
    seed: int,
) -> Mapping[str, Any]:
    proposed_by_user = {int(row["user_id"]): float(row[metric]) for row in proposed}
    baseline_by_user = {int(row["user_id"]): float(row[metric]) for row in baseline}
    users = sorted(set(proposed_by_user) & set(baseline_by_user))
    differences = np.asarray(
        [proposed_by_user[user] - baseline_by_user[user] for user in users],
        dtype=np.float64,
    )
    differences = differences[np.isfinite(differences)]
    if not len(differences):
        return {
            "metric": metric,
            "cohort_users": 0,
            "mean_difference": None,
            "lower": None,
            "upper": None,
            "failed_closed": True,
        }
    rng = np.random.default_rng(seed)
    draws = np.empty(repetitions, dtype=np.float64)
    for repetition in range(repetitions):
        sample = rng.integers(0, len(differences), size=len(differences))
        draws[repetition] = float(np.mean(differences[sample]))
    return {
        "metric": metric,
        "cohort_users": int(len(differences)),
        "mean_difference": float(np.mean(differences)),
        "lower": float(np.quantile(draws, alpha / 2.0)),
        "upper": float(np.quantile(draws, 1.0 - alpha / 2.0)),
        "repetitions": repetitions,
        "seed": seed,
        "unit": "user_cluster_after_within_user_seed_average",
        "failed_closed": False,
    }


def benchmark_serving_latency(
    splits: Sequence[UserSplit],
    selected_bpr: BPRArtifacts,
    selected_index: Any,
    semantic_vectors: np.ndarray,
    semantic_index: Any,
    popularity: np.ndarray,
    caper_model: BoundedResidual,
    linear_alpha: float,
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    warmup_count = min(int(config["evaluation"]["latency_warmup_users"]), len(splits))
    measured_count = min(
        int(config["evaluation"]["latency_measured_users"]), len(splits)
    )
    measured_splits = list(splits[:measured_count])
    budget = float(config["residual"]["hard_cumulative_normalized_bpr_regret_budget"])

    def run_one(split: UserSplit, method: str) -> None:
        history = (*split.train, *split.alignment, *split.validation)
        context = build_candidate_context(
            split,
            history,
            selected_bpr,
            selected_index,
            semantic_vectors,
            semantic_index,
            config["bpr"],
            config["embedding"],
            config["dataset"],
            config["retrieval"],
            config["residual"],
        )
        features, anchor, semantic = item_features(
            context,
            context.union,
            selected_bpr,
            semantic_vectors,
            popularity,
            config["retrieval"],
        )
        scores = (
            linear_alpha * anchor + (1.0 - linear_alpha) * semantic
            if method == "linear_fusion_projected"
            else anchor + residual_numpy(caper_model, features)
        )
        hard_regret_projection(
            context.union,
            scores,
            anchor,
            int(config["residual"]["projection_k"]),
            budget,
            context.regret_scale_degenerate,
        )

    for split in measured_splits[:warmup_count]:
        run_one(split, "linear_fusion_projected")
        run_one(split, "caper")
    timings: dict[str, list[list[float]]] = {
        "linear_fusion_projected": [[] for _ in measured_splits],
        "caper": [[] for _ in measured_splits],
    }
    repetitions = int(config["evaluation"]["latency_repetitions"])
    for repetition in range(repetitions):
        for position, split in enumerate(measured_splits):
            order = (
                ("linear_fusion_projected", "caper")
                if (repetition + position) % 2 == 0
                else ("caper", "linear_fusion_projected")
            )
            for method in order:
                started = time.perf_counter_ns()
                run_one(split, method)
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                timings[method][position].append(float(elapsed_ms))
    result: dict[str, Any] = {
        "single_thread_cpu": True,
        "includes_two_faiss_searches_dedup_features_projection_sort": True,
        "measured_users": measured_count,
        "repetitions": repetitions,
        "abba_interleaving": True,
    }
    for method, per_user_values in timings.items():
        per_user_medians = np.asarray(
            [float(np.median(values)) for values in per_user_values], dtype=np.float64
        )
        result[method] = {
            "requests": int(sum(len(values) for values in per_user_values)),
            "per_user_median_count": len(per_user_medians),
            "aggregation": "median_across_repetitions_per_user_then_percentile_across_users",
            "p50_ms": float(np.percentile(per_user_medians, 50.0)),
            "p95_ms": float(np.percentile(per_user_medians, 95.0)),
            "mean_of_user_medians_ms": float(np.mean(per_user_medians)),
        }
    result["caper_to_linear_p95_ratio"] = float(
        result["caper"]["p95_ms"]
        / max(result["linear_fusion_projected"]["p95_ms"], 1e-12)
    )
    return result


def evaluate_nine_part_gate(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]],
    comparator_by_seed: Mapping[int, str],
    per_seed_diagnostics: Mapping[int, Mapping[str, Any]],
    latency_by_seed: Mapping[int, Mapping[str, Any]],
    integrity: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Mapping[str, Any]:
    seeds = sorted(per_seed_rows)
    caper_methods = {seed: "caper" for seed in seeds}
    bpr_methods = {seed: "selected_bpr" for seed in seeds}
    caper_rows = average_rows_across_seeds(per_seed_rows, caper_methods)
    bpr_rows = average_rows_across_seeds(per_seed_rows, bpr_methods)
    comparator_rows = average_rows_across_seeds(per_seed_rows, comparator_by_seed)
    caper_summary = summarize_rows(caper_rows)
    bpr_summary = summarize_rows(bpr_rows)
    comparator_summary = summarize_rows(comparator_rows)
    projected_ablation_names = (
        "linear_fusion_projected",
        "zero_margin_projected",
        "unanchored_projected",
        "uniform_pair_projected",
    )
    projected_ablation_summaries = {
        method: summarize_rows(
            average_rows_across_seeds(
                per_seed_rows, {seed: method for seed in seeds}
            )
        )
        for method in projected_ablation_names
    }
    repetitions = int(config["evaluation"]["bootstrap_repetitions"])
    alpha = float(config["evaluation"]["bootstrap_alpha"])
    bootstrap_seed = int(config["evaluation"]["bootstrap_seed"])
    bootstraps = {
        "caper_minus_validation_selected_bpr_ndcg": paired_user_cluster_bootstrap(
            caper_rows, bpr_rows, "ndcg_at_10", repetitions, alpha, bootstrap_seed
        ),
        "caper_minus_validation_selected_comparator_ndcg": paired_user_cluster_bootstrap(
            caper_rows,
            comparator_rows,
            "ndcg_at_10",
            repetitions,
            alpha,
            bootstrap_seed + 1,
        ),
        "caper_minus_validation_selected_bpr_preference_accuracy": paired_user_cluster_bootstrap(
            caper_rows,
            bpr_rows,
            "preference_pair_accuracy",
            repetitions,
            alpha,
            bootstrap_seed + 2,
        ),
        "caper_minus_validation_selected_bpr_recall10": paired_user_cluster_bootstrap(
            caper_rows,
            bpr_rows,
            "recall_at_10",
            repetitions,
            alpha,
            bootstrap_seed + 3,
        ),
        "caper_minus_validation_selected_bpr_dislike_intrusion": paired_user_cluster_bootstrap(
            caper_rows,
            bpr_rows,
            "future_dislike_intrusion_at_10",
            repetitions,
            alpha,
            bootstrap_seed + 4,
        ),
    }
    gate_config = config["promise_gate"]
    bpr_ndcg = bpr_summary["ndcg_at_10"]
    caper_ndcg = caper_summary["ndcg_at_10"]
    relative_gain = (
        None
        if bpr_ndcg is None or caper_ndcg is None or float(bpr_ndcg) <= 0.0
        else float((float(caper_ndcg) - float(bpr_ndcg)) / float(bpr_ndcg))
    )
    g1_bootstrap = bootstraps["caper_minus_validation_selected_bpr_ndcg"]
    g1_pass = bool(
        relative_gain is not None
        and relative_gain
        >= float(gate_config["minimum_relative_ndcg_gain_over_stronger_bpr"])
        and g1_bootstrap["lower"] is not None
        and float(g1_bootstrap["lower"]) > 0.0
    )
    g2_bootstrap = bootstraps[
        "caper_minus_validation_selected_comparator_ndcg"
    ]
    point_above_all_projected_ablations = all(
        caper_summary["ndcg_at_10"] is not None
        and projected_ablation_summaries[method]["ndcg_at_10"] is not None
        and float(caper_summary["ndcg_at_10"])
        > float(projected_ablation_summaries[method]["ndcg_at_10"])
        for method in projected_ablation_names
    )
    g2_pass = bool(
        caper_summary["ndcg_at_10"] is not None
        and comparator_summary["ndcg_at_10"] is not None
        and float(caper_summary["ndcg_at_10"])
        > float(comparator_summary["ndcg_at_10"])
        and g2_bootstrap["lower"] is not None
        and float(g2_bootstrap["lower"]) > 0.0
        and point_above_all_projected_ablations
        and len(set(comparator_by_seed.values())) == 1
    )
    g3_bootstrap = bootstraps[
        "caper_minus_validation_selected_bpr_preference_accuracy"
    ]
    preference_gain = (
        None
        if caper_summary["preference_pair_accuracy"] is None
        or bpr_summary["preference_pair_accuracy"] is None
        else float(
            caper_summary["preference_pair_accuracy"]
            - bpr_summary["preference_pair_accuracy"]
        )
    )
    g3_pass = bool(
        preference_gain is not None
        and preference_gain
        >= float(gate_config["minimum_absolute_preference_accuracy_gain"])
        and g3_bootstrap["lower"] is not None
        and float(g3_bootstrap["lower"]) > 0.0
    )
    g4_bootstrap = bootstraps["caper_minus_validation_selected_bpr_recall10"]
    g4_pass = bool(
        g4_bootstrap["lower"] is not None
        and float(g4_bootstrap["lower"])
        > float(gate_config["minimum_recall10_lower_bound"])
    )
    support_all = all(
        bool(row["candidate_support_inclusion"])
        for seed in seeds
        for row in per_seed_rows[seed]["caper"]
    )
    candidate_recall_non_degraded = all(
        float(row["union_candidate_recall_at_most_400"])
        + 1e-12
        >= float(row["bpr_anchor_candidate_recall_at_200"])
        for seed in seeds
        for row in per_seed_rows[seed]["caper"]
    )
    g5_pass = bool(support_all and candidate_recall_non_degraded)
    g6_bootstrap = bootstraps[
        "caper_minus_validation_selected_bpr_dislike_intrusion"
    ]
    g6_pass = bool(
        g6_bootstrap["upper"] is not None
        and float(g6_bootstrap["upper"])
        <= float(gate_config["maximum_absolute_dislike_intrusion_increase"])
    )
    seed_wins: dict[str, bool] = {}
    for seed in seeds:
        caper_seed = summarize_rows(per_seed_rows[seed]["caper"])["ndcg_at_10"]
        bpr_seed = summarize_rows(per_seed_rows[seed]["selected_bpr"])["ndcg_at_10"]
        comparator_seed = summarize_rows(
            per_seed_rows[seed][comparator_by_seed[seed]]
        )["ndcg_at_10"]
        seed_wins[str(seed)] = bool(
            caper_seed is not None
            and bpr_seed is not None
            and comparator_seed is not None
            and float(caper_seed) > float(bpr_seed)
            and float(caper_seed) > float(comparator_seed)
        )
    g7_pass = sum(seed_wins.values()) >= int(
        gate_config["minimum_caper_seeds_beating_both_bpr_and_ablation"]
    )
    maximum_caper_p95 = max(
        float(latency_by_seed[seed]["caper"]["p95_ms"]) for seed in seeds
    )
    maximum_latency_ratio = max(
        float(latency_by_seed[seed]["caper_to_linear_p95_ratio"]) for seed in seeds
    )
    g8_pass = bool(
        maximum_caper_p95 <= float(gate_config["maximum_p95_latency_ms"])
        and maximum_latency_ratio
        <= float(gate_config["maximum_p95_latency_ratio_to_linear_fusion"])
    )
    minimum_pairs = int(config["dataset"]["minimum_heldout_preference_pairs"])
    minimum_pair_users = int(config["dataset"]["minimum_pair_bearing_test_users"])
    minimum_agreement = int(config["dataset"]["minimum_test_bpr_agreement_pairs"])
    minimum_contradictions = int(
        config["dataset"]["minimum_test_bpr_contradiction_pairs"]
    )
    cohorts_pass = all(
        int(per_seed_diagnostics[seed]["heldout_preference_pairs"]) >= minimum_pairs
        and int(per_seed_diagnostics[seed]["pair_bearing_test_users"])
        >= minimum_pair_users
        and int(per_seed_diagnostics[seed]["test_bpr_agreement_pairs"])
        >= minimum_agreement
        and int(per_seed_diagnostics[seed]["test_bpr_contradiction_pairs"])
        >= minimum_contradictions
        for seed in seeds
    )
    regret_pass = all(
        float(per_seed_diagnostics[seed]["maximum_normalized_bpr_regret"][method])
        <= float(per_seed_diagnostics[seed]["regret_budget"]) + 1e-7
        for seed in seeds
        for method in per_seed_diagnostics[seed]["maximum_normalized_bpr_regret"]
    )
    g9_checks = {
        "minimum_test_users": len(caper_rows)
        >= int(config["dataset"]["minimum_test_users"]),
        "preference_cohort_thresholds": cohorts_pass,
        "immutable_semantic_and_collaborative_matrices_and_indexes": bool(
            integrity.get("immutable", False)
        ),
        "target_blind_candidate_manifests_persisted_and_hashed": bool(
            integrity.get("target_blind_candidate_manifests", False)
        ),
        "candidate_targets_never_injected": all(
            not bool(per_seed_diagnostics[seed]["candidate_targets_injected"])
            for seed in seeds
        ),
        "temporal_and_provenance_checks": bool(
            integrity.get("temporal_and_provenance", False)
        ),
        "asynchronous_error_ledger_empty": bool(
            integrity.get("async_error_ledger_empty", False)
        ),
        "hard_regret_budget_respected": regret_pass,
        "config_and_runner_hashes_stable": bool(
            integrity.get("source_hashes_stable", False)
        ),
    }
    g9_pass = all(g9_checks.values())
    gates = {
        "G1_relevance_gain": {
            "passed": g1_pass,
            "relative_ndcg_gain": relative_gain,
            "bootstrap": g1_bootstrap,
        },
        "G2_validation_locked_mechanism": {
            "passed": g2_pass,
            "comparator_by_seed": {str(seed): comparator_by_seed[seed] for seed in seeds},
            "single_validation_locked_comparator_identity": len(
                set(comparator_by_seed.values())
            )
            == 1,
            "point_above_all_four_projected_ablations": point_above_all_projected_ablations,
            "projected_ablation_summaries": projected_ablation_summaries,
            "bootstrap": g2_bootstrap,
        },
        "G3_preference_accuracy": {
            "passed": g3_pass,
            "absolute_user_macro_gain": preference_gain,
            "bootstrap": g3_bootstrap,
            "preprojection_scalar_scores": True,
            "ties_receive_half_credit": True,
        },
        "G4_top_rank_safety": {"passed": g4_pass, "bootstrap": g4_bootstrap},
        "G5_candidate_support": {
            "passed": g5_pass,
            "B_subset_C_all_requests": support_all,
            "union_C_recall_never_below_BPR_B_recall": candidate_recall_non_degraded,
            "B_size": int(config["retrieval"]["collaborative_candidates"]),
            "C_maximum_size": int(config["retrieval"]["maximum_union_candidates"]),
        },
        "G6_dislike_safety": {
            "passed": g6_pass,
            "paired_bootstrap_upper_bound": g6_bootstrap,
        },
        "G7_seed_stability": {"passed": g7_pass, "seed_wins": seed_wins},
        "G8_serving_budget": {
            "passed": g8_pass,
            "worst_caper_p95_ms": maximum_caper_p95,
            "worst_p95_ratio_to_projected_linear": maximum_latency_ratio,
        },
        "G9_integrity": {"passed": g9_pass, "checks": g9_checks},
    }
    return {
        "passed": all(bool(gate["passed"]) for gate in gates.values()),
        "formula": "PROMISING = G1 & G2 & G3 & G4 & G5 & G6 & G7 & G8 & G9",
        "gates": gates,
        "seed_averaged_user_macro": {
            "caper": caper_summary,
            "validation_selected_bpr": bpr_summary,
            "validation_selected_projected_comparator": comparator_summary,
        },
        "paired_bootstraps": bootstraps,
        "test_method_selection_used": False,
    }


def per_user_csv_bytes(
    per_seed_rows: Mapping[int, Mapping[str, list[Mapping[str, Any]]]]
) -> bytes:
    buffer = io.StringIO(newline="")
    fields = (
        "seed",
        "method",
        "user_id",
        "ndcg_at_10",
        "recall_at_10",
        "candidate_recall",
        "union_candidate_recall_at_most_400",
        "bpr_anchor_candidate_recall_at_200",
        "preference_pairs",
        "preference_correct",
        "preference_pair_accuracy",
        "future_dislike_intrusion_at_10",
        "candidate_support_inclusion",
        "candidate_union_size",
    )
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for seed in sorted(per_seed_rows):
        for method in sorted(per_seed_rows[seed]):
            for row in per_seed_rows[seed][method]:
                writer.writerow(
                    {"seed": seed, "method": method, **{key: row[key] for key in fields[2:]}}
                )
    return buffer.getvalue().encode("utf-8")


def collect_artifact_hashes(run_directory: Path) -> dict[str, str]:
    return {
        path.relative_to(run_directory).as_posix(): sha256_file(path)
        for path in sorted(run_directory.rglob("*"))
        if path.is_file() and not path.name.startswith("RUNNER_COMPLETE_")
    }


def execute(args: argparse.Namespace) -> Path:
    config_path = args.config.resolve()
    experiments_root = args.experiments_root.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode("utf-8"))
    validate_config(config)
    config_sha = sha256_bytes(config_bytes)
    runner_path = Path(__file__).resolve()
    runner_sha = sha256_file(runner_path)
    protocol_sha = sha256_bytes(
        canonical_json_bytes(
            {
                "config_sha256": config_sha,
                "runner_sha256": runner_sha,
                "protocol_name": config["protocol_name"],
            }
        )
    )
    protocol_short = protocol_sha[:16]
    lock = RunnerLock(experiments_root / "caper_poc.lock", protocol_sha)
    lock.acquire()
    run_directory: Path | None = None
    try:
        run_id = args.run_id or (
            "caper-poc-v1-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            + "-"
            + uuid.uuid4().hex[:12]
        )
        if Path(run_id).name != run_id or run_id in {".", ".."}:
            raise ValueError("run-id must be one safe path component")
        run_directory = experiments_root / "caper_poc_runs" / run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        runner_snapshot = run_directory / f"runner_source_{runner_sha[:16]}_seq001.py"
        publish_bytes_no_overwrite(runner_snapshot, runner_path.read_bytes())
        human_protocol_source = runner_path.parents[1] / "experiments" / "caper-protocol-v1.md"
        if not human_protocol_source.is_file():
            raise FileNotFoundError(
                f"Locked human protocol is missing: {human_protocol_source}"
            )
        human_protocol_sha = sha256_file(human_protocol_source)
        human_protocol_snapshot = run_directory / (
            f"human_protocol_{human_protocol_sha[:16]}_seq001.md"
        )
        publish_bytes_no_overwrite(
            human_protocol_snapshot, human_protocol_source.read_bytes()
        )
        try:
            import faiss

            faiss_version = getattr(faiss, "__version__", "unknown")
        except ImportError:
            faiss_version = "missing"
        environment_path = run_directory / f"environment_{protocol_short}_seq001.json"
        publish_json_no_overwrite(
            environment_path,
            {
                "schema": "caper-environment-v1",
                "created_utc": utc_now(),
                "python_executable": sys.executable,
                "python_version": sys.version,
                "platform": platform.platform(),
                "numpy_version": np.__version__,
                "torch_version": torch.__version__,
                "faiss_version": faiss_version,
                "sentence_transformers_version": importlib.metadata.version(
                    "sentence-transformers"
                ),
                "thread_environment": THREAD_ENVIRONMENT,
                "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
                "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
                "runner_source_snapshot": runner_snapshot.name,
                "runner_source_sha256": runner_sha,
                "human_protocol_snapshot": human_protocol_snapshot.name,
                "human_protocol_sha256": human_protocol_sha,
            },
        )
        error_ledger = run_directory / f"async_errors_{protocol_short}_seq001.jsonl"
        with error_ledger.open("xb") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        install_async_exception_hooks(error_ledger)
        event_log = run_directory / f"events_{protocol_short}_seq001.jsonl"
        with event_log.open("xb") as handle:
            handle.flush()
            os.fsync(handle.fileno())

        def log_event(event: str, **values: Any) -> None:
            append_json_line(
                event_log,
                {"utc": utc_now(), "event": event, "pid": os.getpid(), **values},
            )

        log_event(
            "run_started",
            protocol_sha256=protocol_sha,
            runner_sha256=runner_sha,
            config_sha256=config_sha,
            thread_environment=THREAD_ENVIRONMENT,
        )
        effective_config_path = run_directory / f"effective_config_{config_sha[:16]}.json"
        publish_bytes_no_overwrite(effective_config_path, config_bytes)
        archive_path = run_directory / "ml-1m.official.zip"
        dataset_sha = acquire_official_zip(
            archive_path,
            str(config["dataset"]["official_url"]),
            config["dataset"].get("expected_sha256"),
        )
        extracted_directory = run_directory / "official_ml1m_extracted"
        ratings_path, movies_path = extract_movielens(
            archive_path, extracted_directory
        )
        source_hashes = {
            "archive": dataset_sha,
            "ratings.dat": sha256_file(ratings_path),
            "movies.dat": sha256_file(movies_path),
        }
        item_ids, metadata = load_movie_metadata(
            movies_path, str(config["embedding"]["metadata_template"])
        )
        item_to_index = {item_id: index for index, item_id in enumerate(item_ids)}
        interactions = load_ratings(ratings_path, item_to_index)
        splits, split_diagnostics = chronological_timestamp_group_splits(
            interactions, config["dataset"]
        )
        popularity = compute_train_popularity(splits, len(item_ids))
        popularity_path = run_directory / f"train_A_popularity_{protocol_short}_seq001.npy"
        save_numpy_no_overwrite(popularity_path, popularity)
        log_event(
            "fresh_official_data_parsed",
            dataset_sha256=dataset_sha,
            item_count=len(item_ids),
            interaction_count=len(interactions),
            retained_users=len(splits),
        )

        semantic_vectors = encode_item_metadata(metadata, config["embedding"])
        semantic_matrix_path = run_directory / (
            f"semantic_item_matrix_{protocol_short}_seq001.npy"
        )
        save_numpy_no_overwrite(semantic_matrix_path, semantic_vectors)
        semantic_index = build_faiss_index(semantic_vectors, config["retrieval"])
        semantic_index_path = run_directory / (
            f"semantic_index_{protocol_short}_seq001.faiss"
        )
        publish_bytes_no_overwrite(semantic_index_path, serialize_faiss(semantic_index))
        semantic_immutability = {
            "matrix_file_before": sha256_file(semantic_matrix_path),
            "matrix_memory_before": sha256_bytes(semantic_vectors.tobytes(order="C")),
            "index_file_before": sha256_file(semantic_index_path),
            "index_memory_before": sha256_bytes(serialize_faiss(semantic_index)),
        }
        log_event(
            "semantic_representation_and_index_frozen",
            matrix_sha256=semantic_immutability["matrix_file_before"],
            index_sha256=semantic_immutability["index_file_before"],
        )

        seeds = [int(seed) for seed in config["replicate_seeds"]]
        seed_state: dict[int, dict[str, Any]] = {}
        all_manifest_paths: list[Path] = []
        manifest_hashes_at_publication: dict[str, str] = {}
        all_immutability_records: list[dict[str, Any]] = []
        # Stage 1: fit both BPR candidates on A, then publish both A-only R
        # manifests and both A+R V manifests before either future label join.
        for seed in seeds:
            log_event("bpr_seed_started", seed=seed)
            bprs: dict[str, BPRArtifacts] = {}
            indexes: dict[str, Any] = {}
            alignment_manifests: dict[str, Mapping[int, CandidateContext]] = {}
            validation_manifests: dict[str, Mapping[int, CandidateContext]] = {}
            checkpoint_files: dict[str, str] = {}
            for variant in ("implicit", "rating_aware"):
                bpr, state = train_bpr(
                    splits, len(item_ids), variant, config["bpr"], seed
                )
                bprs[variant] = bpr
                index = build_faiss_index(bpr.item_vectors, config["retrieval"])
                indexes[variant] = index
                matrix_path = run_directory / (
                    f"bpr_{variant}_item_matrix_seed{seed}_{protocol_short}_seq001.npy"
                )
                user_path = run_directory / (
                    f"bpr_{variant}_user_matrix_seed{seed}_{protocol_short}_seq001.npy"
                )
                index_path = run_directory / (
                    f"bpr_{variant}_index_seed{seed}_{protocol_short}_seq001.faiss"
                )
                checkpoint_path = run_directory / (
                    f"bpr_{variant}_checkpoint_seed{seed}_{protocol_short}_seq001.pt"
                )
                save_numpy_no_overwrite(matrix_path, bpr.item_vectors)
                save_numpy_no_overwrite(user_path, bpr.user_vectors)
                publish_bytes_no_overwrite(index_path, serialize_faiss(index))
                save_torch_no_overwrite(
                    checkpoint_path,
                    {
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "state_dict": state,
                        "diagnostics": dict(bpr.training_diagnostics),
                    },
                )
                checkpoint_files[f"bpr_{variant}"] = checkpoint_path.name
                all_immutability_records.append(
                    {
                        "seed": seed,
                        "variant": variant,
                        "matrix_path": matrix_path,
                        "matrix_memory": bpr.item_vectors,
                        "index_path": index_path,
                        "index": index,
                        "matrix_file_before": sha256_file(matrix_path),
                        "matrix_memory_before": sha256_bytes(
                            bpr.item_vectors.tobytes(order="C")
                        ),
                        "index_file_before": sha256_file(index_path),
                        "index_memory_before": sha256_bytes(serialize_faiss(index)),
                    }
                )
            seed_state[seed] = {
                "bprs": bprs,
                "indexes": indexes,
                "alignment_manifests": alignment_manifests,
                "validation_manifests": validation_manifests,
                "checkpoint_files": checkpoint_files,
            }

        # All A-only BPR/index training is complete. Only now generate and
        # persist every A-only alignment manifest, still without reading R.
        for seed in seeds:
            state = seed_state[seed]
            for variant in ("implicit", "rating_aware"):
                alignment_contexts, alignment_serializable = build_prefix_candidate_manifest(
                    splits,
                    state["bprs"][variant],
                    state["indexes"][variant],
                    semantic_vectors,
                    semantic_index,
                    config,
                    "alignment",
                )
                alignment_path = run_directory / (
                    f"alignment_manifest_{variant}_seed{seed}_{protocol_short}_seq001.json"
                )
                publish_json_no_overwrite(
                    alignment_path,
                    {
                        "schema": "caper-target-blind-alignment-manifest-v1",
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "created_before_alignment_label_join": True,
                        "entries": alignment_serializable,
                    },
                )
                all_manifest_paths.append(alignment_path)
                manifest_hashes_at_publication[alignment_path.name] = sha256_file(
                    alignment_path
                )
                state["alignment_manifests"][variant] = alignment_contexts
                log_event(
                    "alignment_manifest_persisted_before_R_label_join",
                    seed=seed,
                    variant=variant,
                    path=alignment_path.name,
                    sha256=sha256_file(alignment_path),
                )
        log_event(
            "all_seed_alignment_manifests_persisted_before_any_R_label_join",
            seed_count=len(seed_state),
        )
        # R history is now allowed. Publish every A+R validation manifest
        # before joining any V target label for model identity selection.
        for seed in seeds:
            state = seed_state[seed]
            for variant in ("implicit", "rating_aware"):
                validation_contexts, validation_serializable = build_prefix_candidate_manifest(
                    splits,
                    state["bprs"][variant],
                    state["indexes"][variant],
                    semantic_vectors,
                    semantic_index,
                    config,
                    "validation",
                )
                validation_path = run_directory / (
                    f"validation_manifest_{variant}_seed{seed}_{protocol_short}_seq001.json"
                )
                publish_json_no_overwrite(
                    validation_path,
                    {
                        "schema": "caper-target-blind-validation-manifest-v1",
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "created_before_validation_label_join": True,
                        "entries": validation_serializable,
                    },
                )
                all_manifest_paths.append(validation_path)
                manifest_hashes_at_publication[validation_path.name] = sha256_file(
                    validation_path
                )
                state["validation_manifests"][variant] = validation_contexts
                log_event(
                    "validation_manifest_persisted_before_V_label_join",
                    seed=seed,
                    variant=variant,
                    path=validation_path.name,
                    sha256=sha256_file(validation_path),
                )
        log_event(
            "all_seed_validation_manifests_persisted_before_any_V_label_join",
            seed_count=len(seed_state),
        )
        for seed in seeds:
            state = seed_state[seed]
            state["validation_bpr_scores"] = {
                variant: validation_ndcg_for_bpr(
                    splits, state["validation_manifests"][variant], config
                )
                for variant in ("implicit", "rating_aware")
            }
            log_event(
                "bpr_seed_validation_scored",
                seed=seed,
                validation_scores=state["validation_bpr_scores"],
            )

        bpr_validation_means = {
            variant: float(
                np.mean(
                    [seed_state[seed]["validation_bpr_scores"][variant] for seed in seeds]
                )
            )
            for variant in ("implicit", "rating_aware")
        }
        selected_bpr_variant = max(
            ("implicit", "rating_aware"),
            key=lambda variant: (bpr_validation_means[variant], variant),
        )
        log_event(
            "global_bpr_identity_locked_on_validation",
            selected_variant=selected_bpr_variant,
            validation_means=bpr_validation_means,
        )
        for seed in seeds:
            state = seed_state[seed]
            state["alignment_manifests"] = {
                selected_bpr_variant: state["alignment_manifests"][
                    selected_bpr_variant
                ]
            }
            state["validation_manifests"] = {
                selected_bpr_variant: state["validation_manifests"][
                    selected_bpr_variant
                ]
            }

        validation_ablation_means_by_seed: dict[int, Mapping[str, float]] = {}
        training_diagnostics: dict[str, Any] = {}
        # Stage 2: only after the R manifests exist, join R labels to the
        # validation-locked BPR manifest, train matched residuals, and score V.
        for seed in seeds:
            state = seed_state[seed]
            selected_bpr: BPRArtifacts = state["bprs"][selected_bpr_variant]
            selected_index = state["indexes"][selected_bpr_variant]
            balanced, uniform = build_alignment_corpora(
                splits,
                state["alignment_manifests"][selected_bpr_variant],
                selected_bpr,
                semantic_vectors,
                popularity,
                config,
                seed,
            )
            state["alignment_manifests"].clear()
            deterministic_setup(seed + 1100001)
            initial_model = BoundedResidual(
                int(balanced.chosen_features.shape[1]),
                int(config["residual"]["hidden_dimension"]),
                float(config["residual"]["residual_bound"]),
            )
            initial_state = {
                key: value.detach().clone()
                for key, value in initial_model.state_dict().items()
            }
            shared_order_seed = seed + 1200001
            residual_specs = {
                "caper": (
                    balanced,
                    float(config["residual"]["simpo_margin"]),
                    float(config["residual"]["soft_anchor_coefficient"]),
                ),
                "zero_margin": (
                    balanced,
                    0.0,
                    float(config["residual"]["soft_anchor_coefficient"]),
                ),
                "unanchored": (
                    balanced,
                    float(config["residual"]["simpo_margin"]),
                    0.0,
                ),
                "uniform_pair": (
                    uniform,
                    float(config["residual"]["simpo_margin"]),
                    float(config["residual"]["soft_anchor_coefficient"]),
                ),
            }
            residual_models: dict[str, BoundedResidual] = {}
            residual_diagnostics: dict[str, Any] = {}
            for variant, (corpus, margin, anchor) in residual_specs.items():
                model, diagnostics = train_residual(
                    corpus,
                    initial_state,
                    config["residual"],
                    shared_order_seed,
                    margin,
                    anchor,
                )
                residual_models[variant] = model
                residual_diagnostics[variant] = diagnostics
                checkpoint_path = run_directory / (
                    f"residual_{variant}_seed{seed}_{protocol_short}_seq001.pt"
                )
                save_torch_no_overwrite(
                    checkpoint_path,
                    {
                        "protocol_sha256": protocol_sha,
                        "seed": seed,
                        "variant": variant,
                        "state_dict": {
                            key: value.detach().cpu()
                            for key, value in model.state_dict().items()
                        },
                        "diagnostics": diagnostics,
                    },
                )
                state["checkpoint_files"][f"residual_{variant}"] = checkpoint_path.name
            selected_validation_manifest = state["validation_manifests"][
                selected_bpr_variant
            ]
            linear_alpha, linear_grid_scores = choose_linear_alpha(
                splits,
                selected_validation_manifest,
                selected_bpr,
                semantic_vectors,
                popularity,
                config,
            )
            _seed_local_comparator, validation_ablation_means = (
                select_mechanism_comparator_on_validation(
                    splits,
                    selected_validation_manifest,
                    selected_bpr,
                    semantic_vectors,
                    popularity,
                    residual_models,
                    linear_alpha,
                    state["bprs"]["implicit"],
                    state["bprs"]["rating_aware"],
                    config,
                )
            )
            validation_ablation_means_by_seed[seed] = validation_ablation_means
            state["validation_manifests"].clear()
            state["selected_bpr"] = selected_bpr
            state["selected_index"] = selected_index
            state["residual_models"] = residual_models
            state["linear_alpha"] = linear_alpha
            training_diagnostics[str(seed)] = {
                "bpr": {
                    variant: dict(state["bprs"][variant].training_diagnostics)
                    for variant in ("implicit", "rating_aware")
                },
                "validation_bpr_scores": state["validation_bpr_scores"],
                "alignment_balanced": dict(balanced.diagnostics),
                "alignment_uniform": dict(uniform.diagnostics),
                "residuals": residual_diagnostics,
                "projected_linear_alpha": linear_alpha,
                "projected_linear_validation_grid": linear_grid_scores,
                "projected_ablation_validation_means": validation_ablation_means,
                "checkpoint_files": dict(state["checkpoint_files"]),
            }
            log_event(
                "residual_seed_trained_and_validation_scored",
                seed=seed,
                linear_alpha=linear_alpha,
                validation_ablation_means=validation_ablation_means,
            )

        comparator_validation_means = {
            method: float(
                np.mean(
                    [
                        validation_ablation_means_by_seed[seed][method]
                        for seed in seeds
                    ]
                )
            )
            for method in (
                "linear_fusion_projected",
                "zero_margin_projected",
                "unanchored_projected",
                "uniform_pair_projected",
            )
        }
        selected_comparator = max(
            comparator_validation_means,
            key=lambda method: (comparator_validation_means[method], method),
        )
        comparator_by_seed = {seed: selected_comparator for seed in seeds}
        log_event(
            "single_global_mechanism_comparator_locked_on_validation",
            selected_comparator=selected_comparator,
            validation_means=comparator_validation_means,
        )

        # Stage 3: identities and grid choices are now frozen.  Publish each
        # A+R+V test manifest before opening any T rating or target label.
        per_seed_rows: dict[int, Mapping[str, list[Mapping[str, Any]]]] = {}
        per_seed_diagnostics: dict[int, Mapping[str, Any]] = {}
        latency_by_seed: dict[int, Mapping[str, Any]] = {}
        test_manifest_records: dict[str, Any] = {}
        test_manifests: dict[int, Mapping[int, CandidateManifestEntry]] = {}
        for seed in seeds:
            state = seed_state[seed]
            manifest, serializable = build_test_candidate_manifest(
                splits,
                state["selected_bpr"],
                state["selected_index"],
                state["bprs"]["implicit"],
                state["indexes"]["implicit"],
                state["bprs"]["rating_aware"],
                state["indexes"]["rating_aware"],
                semantic_vectors,
                semantic_index,
                config,
            )
            manifest_path = run_directory / (
                f"test_manifest_seed{seed}_{protocol_short}_seq001.json"
            )
            publish_json_no_overwrite(
                manifest_path,
                {
                    "schema": "caper-target-blind-test-manifest-v1",
                    "protocol_sha256": protocol_sha,
                    "seed": seed,
                    "selected_bpr_variant": selected_bpr_variant,
                    "selected_comparator": selected_comparator,
                    "created_before_test_label_join": True,
                    "entries": serializable,
                },
            )
            all_manifest_paths.append(manifest_path)
            manifest_hashes_at_publication[manifest_path.name] = sha256_file(
                manifest_path
            )
            test_manifest_records[str(seed)] = {
                "file": manifest_path.name,
                "sha256": sha256_file(manifest_path),
                "entries": len(serializable),
                "persisted_before_test_label_join": True,
            }
            log_event(
                "test_manifest_persisted_before_T_label_join",
                seed=seed,
                path=manifest_path.name,
                sha256=sha256_file(manifest_path),
            )
            test_manifests[seed] = manifest
        log_event(
            "all_seed_test_manifests_persisted_before_any_T_label_join",
            seed_count=len(test_manifests),
        )
        for seed in seeds:
            state = seed_state[seed]
            rows, diagnostics = evaluate_seed(
                splits,
                test_manifests[seed],
                state["selected_bpr"],
                state["bprs"]["implicit"],
                state["bprs"]["rating_aware"],
                semantic_vectors,
                popularity,
                state["residual_models"],
                float(state["linear_alpha"]),
                config,
            )
            per_seed_rows[seed] = rows
            per_seed_diagnostics[seed] = diagnostics
            del test_manifests[seed]
            latency_by_seed[seed] = benchmark_serving_latency(
                splits,
                state["selected_bpr"],
                state["selected_index"],
                semantic_vectors,
                semantic_index,
                popularity,
                state["residual_models"]["caper"],
                float(state["linear_alpha"]),
                config,
            )
            log_event(
                "sealed_test_seed_evaluated",
                seed=seed,
                heldout_preference_pairs=diagnostics["heldout_preference_pairs"],
            )

        semantic_immutability.update(
            {
                "matrix_file_after": sha256_file(semantic_matrix_path),
                "matrix_memory_after": sha256_bytes(
                    semantic_vectors.tobytes(order="C")
                ),
                "index_file_after": sha256_file(semantic_index_path),
                "index_memory_after": sha256_bytes(serialize_faiss(semantic_index)),
            }
        )
        semantic_immutability["unchanged"] = bool(
            semantic_immutability["matrix_file_before"]
            == semantic_immutability["matrix_file_after"]
            and semantic_immutability["matrix_memory_before"]
            == semantic_immutability["matrix_memory_after"]
            and semantic_immutability["index_file_before"]
            == semantic_immutability["index_file_after"]
            and semantic_immutability["index_memory_before"]
            == semantic_immutability["index_memory_after"]
        )
        serializable_immutability: list[Mapping[str, Any]] = []
        for record in all_immutability_records:
            matrix_path = record["matrix_path"]
            index_path = record["index_path"]
            matrix = record["matrix_memory"]
            index = record["index"]
            after = {
                "matrix_file_after": sha256_file(matrix_path),
                "matrix_memory_after": sha256_bytes(matrix.tobytes(order="C")),
                "index_file_after": sha256_file(index_path),
                "index_memory_after": sha256_bytes(serialize_faiss(index)),
            }
            unchanged = bool(
                record["matrix_file_before"] == after["matrix_file_after"]
                and record["matrix_memory_before"] == after["matrix_memory_after"]
                and record["index_file_before"] == after["index_file_after"]
                and record["index_memory_before"] == after["index_memory_after"]
            )
            serializable_immutability.append(
                {
                    "seed": record["seed"],
                    "variant": record["variant"],
                    "matrix_file": matrix_path.name,
                    "index_file": index_path.name,
                    "matrix_file_before": record["matrix_file_before"],
                    "matrix_memory_before": record["matrix_memory_before"],
                    "index_file_before": record["index_file_before"],
                    "index_memory_before": record["index_memory_before"],
                    **after,
                    "unchanged": unchanged,
                }
            )
        immutable = bool(
            semantic_immutability["unchanged"]
            and all(record["unchanged"] for record in serializable_immutability)
        )
        manifest_hashes_stable = all(
            path.is_file()
            and manifest_hashes_at_publication.get(path.name) == sha256_file(path)
            for path in all_manifest_paths
        ) and len(manifest_hashes_at_publication) == len(all_manifest_paths)
        source_hashes_stable = bool(
            sha256_file(config_path) == config_sha
            and sha256_file(runner_path) == runner_sha
            and sha256_file(runner_snapshot) == runner_sha
            and sha256_file(human_protocol_source) == human_protocol_sha
            and sha256_file(human_protocol_snapshot) == human_protocol_sha
            and sha256_file(ratings_path) == source_hashes["ratings.dat"]
            and sha256_file(movies_path) == source_hashes["movies.dat"]
        )
        integrity = {
            "immutable": immutable,
            "target_blind_candidate_manifests": manifest_hashes_stable,
            "temporal_and_provenance": bool(
                split_diagnostics["timestamp_groups_indivisible"]
                and split_diagnostics["strict_temporal_boundaries"]
                and config["dataset"]["exclude_demographics"]
                and str(config["dataset"]["official_url"]).startswith(
                    "https://files.grouplens.org/"
                )
            ),
            "async_error_ledger_empty": error_ledger.stat().st_size == 0,
            "source_hashes_stable": source_hashes_stable,
        }
        gate = evaluate_nine_part_gate(
            per_seed_rows,
            comparator_by_seed,
            per_seed_diagnostics,
            latency_by_seed,
            integrity,
            config,
        )
        execution_sha = sha256_bytes(
            canonical_json_bytes(
                {
                    "protocol_sha256": protocol_sha,
                    "dataset_sha256": dataset_sha,
                    "source_hashes": source_hashes,
                    "seeds": seeds,
                    "selected_bpr_variant": selected_bpr_variant,
                    "selected_comparator": selected_comparator,
                }
            )
        )
        execution_short = execution_sha[:16]
        per_user_path = run_directory / (
            f"per_user_metrics_{execution_short}_seq001.csv"
        )
        publish_bytes_no_overwrite(per_user_path, per_user_csv_bytes(per_seed_rows))
        per_seed_method_summaries = {
            str(seed): {
                method: summarize_rows(rows)
                for method, rows in per_seed_rows[seed].items()
            }
            for seed in seeds
        }
        result = {
            "schema": "caper-poc-result-v1",
            "status": "COMPLETE_RUNNER_RESULT",
            "protocol_name": config["protocol_name"],
            "protocol_sha256": protocol_sha,
            "execution_fingerprint_sha256": execution_sha,
            "runner_sha256": runner_sha,
            "config_sha256": config_sha,
            "dataset_sha256": dataset_sha,
            "created_utc": utc_now(),
            "run_directory": str(run_directory),
            "thread_environment": THREAD_ENVIRONMENT,
            "scientific_protocol": {
                "dataset": "fresh official GroupLens MovieLens 1M",
                "inputs": "ratings.dat plus title and genres; demographics excluded",
                "split": "per-user indivisible timestamp groups, 60/20/10/10 A/R/V/T",
                "stable_user_subset": {
                    "maximum_users": config["dataset"]["maximum_users"],
                    "seed": config["dataset"]["stable_subset_seed"],
                    "minimum_total_events": config["dataset"]["minimum_total_events"],
                },
                "semantic_encoder": config["embedding"]["model_name"],
                "semantic_item_vectors_l2_normalized": True,
                "bpr_item_factors_are_raw_trained_inner_product_factors": True,
                "bpr_prefix_query_update": config["bpr"]["prefix_query_update"],
                "two_indexes": "FAISS IndexFlatIP semantic and collaborative",
                "candidate_contract": "B@200 subset C=stable_union(B@200,S@200), |C|<=400",
                "alignment_loss": (
                    "reference-free SimPO-derived -logsigmoid(beta*score_gap/temperature-margin) "
                    "plus bounded residual L2 and noncontradiction-masked pairwise KL anchor"
                ),
                "regret_scale": (
                    "registered Q95-Q05 of immutable BPR anchor candidate scores only; "
                    "degenerate scale returns BPR order"
                ),
                "preference_accuracy": (
                    "naturally retrieved test pairs only, preprojection scalar scores, "
                    "user macro primary, pair micro diagnostic, ties half"
                ),
                "user_cross_fitting": (
                    "not used: the claim is same-user temporal adaptation, and every label "
                    "used for training is in A/R strictly before sealed V/T labels; no claim "
                    "of unseen-user generalization is made"
                ),
                "test_set_used_for_selection": False,
            },
            "data_counts": {
                "catalog_items": len(item_ids),
                "interactions": len(interactions),
                "eligible_test_users": len(splits),
                "split_diagnostics": split_diagnostics,
                "per_seed_preference_cohorts": {
                    str(seed): {
                        key: per_seed_diagnostics[seed][key]
                        for key in (
                            "heldout_preference_pairs",
                            "raw_heldout_preference_pairs_before_hash_cap",
                            "pair_bearing_test_users",
                            "test_bpr_agreement_pairs",
                            "test_bpr_contradiction_pairs",
                            "test_bpr_tied_pairs",
                        )
                    }
                    for seed in seeds
                },
            },
            "selection_locks": {
                "global_validation_selected_bpr_variant": selected_bpr_variant,
                "bpr_validation_means": bpr_validation_means,
                "global_validation_selected_projected_comparator": selected_comparator,
                "projected_comparator_validation_means": comparator_validation_means,
                "linear_alpha_by_seed": {
                    str(seed): seed_state[seed]["linear_alpha"] for seed in seeds
                },
                "all_locked_before_test_manifest_generation": True,
            },
            "per_seed_method_summaries": per_seed_method_summaries,
            "per_seed_diagnostics": {
                str(seed): per_seed_diagnostics[seed] for seed in seeds
            },
            "latency_by_seed": {str(seed): latency_by_seed[seed] for seed in seeds},
            "promise_gate": gate,
            "training_diagnostics": training_diagnostics,
            "provenance": {
                "official_url": config["dataset"]["official_url"],
                "source_hashes": source_hashes,
                "runner_source_snapshot": runner_snapshot.name,
                "runner_source_sha256": runner_sha,
                "human_protocol_snapshot": human_protocol_snapshot.name,
                "human_protocol_sha256": human_protocol_sha,
                "environment_snapshot": environment_path.name,
                "environment_sha256": sha256_file(environment_path),
                "effective_config_file": effective_config_path.name,
                "candidate_manifests": {
                    "all_manifest_files": [path.name for path in all_manifest_paths],
                    "all_manifest_sha256": {
                        path.name: sha256_file(path) for path in all_manifest_paths
                    },
                    "test": test_manifest_records,
                    "alignment_persisted_before_R_labels": True,
                    "validation_persisted_before_V_labels": True,
                    "test_persisted_before_T_labels": True,
                    "target_injection_count": 0,
                },
            },
            "immutability": {
                "semantic": semantic_immutability,
                "collaborative": serializable_immutability,
                "all_unchanged": immutable,
            },
            "integrity": integrity,
            "artifacts": {
                "per_user_metrics": per_user_path.name,
                "checkpoints": {
                    str(seed): seed_state[seed]["checkpoint_files"] for seed in seeds
                },
            },
            "completion_semantics": (
                "This runner result is only a completion candidate. The authoritative "
                "outcome additionally requires process exit, runner-lock release, empty "
                "async ledger, recursive artifact-hash verification, and an external marker."
            ),
        }
        result_path = run_directory / f"result_{execution_short}_seq001.json"
        publish_json_no_overwrite(result_path, result)
        log_event(
            "result_published",
            result_file=result_path.name,
            promise_gate_passed=bool(gate["passed"]),
        )
        if error_ledger.stat().st_size != 0:
            raise IntegrityError(
                "Asynchronous-error ledger is nonempty; refusing completion candidate"
            )
        log_event("runner_artifacts_finalized")
        artifact_hashes = collect_artifact_hashes(run_directory)
        completion_marker = run_directory / (
            f"RUNNER_COMPLETE_{execution_short}_seq001.json"
        )
        publish_json_no_overwrite(
            completion_marker,
            {
                "schema": "caper-runner-completion-candidate-v1",
                "created_utc": utc_now(),
                "pid": os.getpid(),
                "run_directory": str(run_directory),
                "protocol_sha256": protocol_sha,
                "execution_fingerprint_sha256": execution_sha,
                "result_file": result_path.name,
                "result_sha256": artifact_hashes[result_path.name],
                "asynchronous_error_ledger": error_ledger.name,
                "asynchronous_error_ledger_sha256": artifact_hashes[
                    error_ledger.name
                ],
                "asynchronous_error_ledger_must_be_empty_after_process_exit": True,
                "artifact_sha256": artifact_hashes,
                "runner_lock": str(lock.path),
                "runner_lock_token": lock.token,
                "runner_lock_release_pending": True,
                "external_post_exit_verification_required": True,
            },
        )
        print(f"RESULT_FILE={result_path}", flush=True)
        print(f"RUNNER_COMPLETION_MARKER={completion_marker}", flush=True)
        return completion_marker
    except BaseException as exc:
        if run_directory is not None and run_directory.exists():
            error_path = run_directory / (
                f"synchronous_error_{protocol_short}_"
                f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_"
                f"{uuid.uuid4().hex}.json"
            )
            try:
                publish_json_no_overwrite(
                    error_path,
                    {
                        "schema": "caper-synchronous-error-v1",
                        "utc": utc_now(),
                        "pid": os.getpid(),
                        "exception_type": type(exc).__name__,
                        "exception": str(exc),
                        "traceback": "".join(
                            traceback.format_exception(type(exc), exc, exc.__traceback__)
                        ),
                    },
                )
            except Exception:
                pass
        raise
    finally:
        lock.release()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Run the preregistered CAPER MovieLens-1M proof of concept."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "caper_poc_ml1m_v1.json",
        help="Immutable JSON protocol configuration.",
    )
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=project_root / "experiments" / "runs",
        help="Root containing the exclusive CPU lock and append-only run directories.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional unique safe run-directory component supplied by the launcher.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    completion_marker = execute(parse_args(argv))
    if not completion_marker.is_file():
        raise IntegrityError("Runner returned without a completion candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
