#!/usr/bin/env python3
"""Reproducible MovieLens-100K proof of concept for RIPPLE.

The outcome-producing entry point is deliberately CPU-only and append-only.
It compares a frozen SentenceTransformer/FAISS retriever, matched adapters
trained with random, exact-full-matrix, or deployed-IVF-boundary rejected
items, and a standard BPR-MF baseline over three registered seeds.  All query
adapters use a reference-free SimPO-derived margin loss and never modify item
vectors or the FAISS index.

This runner creates a runner-completion candidate with recursive artifact
hashes.  Under the repository's Windows execution contract, an external
launcher/verifier must still observe process exit and lock release, and must
hash its persistent stdout/stderr before declaring the run complete.
"""

from __future__ import annotations

# The execution contract requires these bounds before importing NumPy, SciPy,
# scikit-learn, or PyTorch.  Assignment (rather than setdefault) prevents an
# inherited high-thread setting from escaping the protocol.
import os

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
import gc
import hashlib
import io
import json
import math
import random
import re
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
GENRE_NAMES = (
    "unknown",
    "Action",
    "Adventure",
    "Animation",
    "Children's",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Film-Noir",
    "Horror",
    "Musical",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Thriller",
    "War",
    "Western",
)


class IntegrityError(RuntimeError):
    """Raised when append-only or provenance invariants are violated."""


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
    validation_window: tuple[Interaction, ...]
    test_window: tuple[Interaction, ...]
    validation: Interaction
    test: Interaction
    test_history: tuple[Interaction, ...]


@dataclass(frozen=True)
class TrainCorpus:
    queries: np.ndarray
    chosen_items: np.ndarray
    excluded_items: tuple[frozenset[int], ...]
    explicit_dislikes: tuple[tuple[int, ...], ...]
    user_ids: np.ndarray


@dataclass(frozen=True)
class EvalCorpus:
    queries: np.ndarray
    user_ids: np.ndarray
    targets: np.ndarray
    quality_blocked: tuple[frozenset[int], ...]
    safety_blocked: tuple[frozenset[int], ...]
    known_dislikes: tuple[frozenset[int], ...]


@dataclass(frozen=True)
class NegativeSelection:
    item_indices: np.ndarray
    # 1=explicit, 2=random confusion, 3=exact confusion,
    # 4=genuine IVF boundary, 5=fallback confusion.
    source_codes: np.ndarray
    fallback: np.ndarray


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(block_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    """Best-effort directory fsync; Windows does not expose it uniformly."""
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
    """Publish fully-fsynced bytes atomically without replacing a target.

    A same-directory temporary file is hard-linked to the final path.  Link
    creation is atomic and fails if the destination already exists on NTFS.
    """
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


def publish_json_no_overwrite(path: Path, value: Any) -> None:
    publish_bytes_no_overwrite(path, canonical_json_bytes(value))


def append_json_line(path: Path, value: Any) -> None:
    payload = canonical_json_bytes(value)
    with path.open("ab") as handle:
        handle.write(payload)
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
    """Single-owner CPU runner lock with one dead-owner retirement retry."""

    def __init__(self, path: Path, protocol_hash: str) -> None:
        self.path = path
        self.protocol_hash = protocol_hash
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(2):
            payload = {
                "schema": "ripple-runner-lock-v1",
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
                if attempt != 0:
                    raise IntegrityError(
                        f"Concurrent or racing runner lock: {self.path}"
                    )
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                    owner_pid = int(existing["pid"])
                    owner_token = str(existing["token"])
                except Exception as exc:
                    raise IntegrityError(
                        f"Unreadable or malformed live lock; refusing: {self.path}"
                    ) from exc
                if not owner_token or process_is_alive(owner_pid):
                    raise IntegrityError(
                        f"Runner lock is held by live PID {owner_pid}: {self.path}"
                    )
                retired = self.path.with_name(
                    f"{self.path.name}.retired.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.{uuid.uuid4().hex}.json"
                )
                try:
                    os.rename(self.path, retired)
                    fsync_directory(self.path.parent)
                except OSError as exc:
                    raise IntegrityError(
                        "Dead-owner lock retirement raced; refusing acquisition"
                    ) from exc
        raise AssertionError("unreachable")

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise IntegrityError(
                f"Cannot verify owned lock before release: {self.path}"
            ) from exc
        if current.get("token") != self.token or int(current.get("pid", -1)) != os.getpid():
            raise IntegrityError("Runner lock ownership changed; refusing to remove it")
        self.path.unlink()
        fsync_directory(self.path.parent)
        self.acquired = False


def install_async_exception_hooks(error_ledger: Path) -> None:
    original_thread_hook = threading.excepthook
    original_unraisable_hook = sys.unraisablehook

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        append_json_line(
            error_ledger,
            {
                "kind": "threading.excepthook",
                "utc": utc_now(),
                "thread_name": getattr(args.thread, "name", None),
                "exception_type": getattr(args.exc_type, "__name__", str(args.exc_type)),
                "exception": str(args.exc_value),
                "traceback": "".join(
                    traceback.format_exception(
                        args.exc_type, args.exc_value, args.exc_traceback
                    )
                ),
            },
        )
        original_thread_hook(args)

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
        original_unraisable_hook(args)

    threading.excepthook = thread_hook
    sys.unraisablehook = unraisable_hook


def validate_config(config: Mapping[str, Any]) -> None:
    required_sections = (
        "dataset",
        "embedding",
        "index",
        "adapter",
        "bpr",
        "evaluation",
        "promise_gate",
    )
    for section in required_sections:
        if section not in config or not isinstance(config[section], Mapping):
            raise ValueError(f"Missing configuration section: {section}")
    if config["index"].get("kind") != "IndexIVFFlat":
        raise ValueError("The registered PoC requires FAISS IndexIVFFlat")
    if config["index"].get("metric") != "inner_product":
        raise ValueError("The registered PoC requires normalized inner-product search")
    if int(config["seed"]) < 0:
        raise ValueError("seed must be nonnegative")
    seeds = [int(value) for value in config.get("replicate_seeds", [config["seed"]])]
    if not seeds or len(seeds) != len(set(seeds)) or any(seed < 0 for seed in seeds):
        raise ValueError("replicate_seeds must be a nonempty unique nonnegative list")
    if len(seeds) != 3:
        raise ValueError("The registered mechanism/stability gate requires exactly 3 seeds")
    train_fraction = float(config["dataset"]["train_fraction"])
    validation_fraction = float(config["dataset"]["validation_fraction"])
    if not (0.0 < train_fraction < 1.0):
        raise ValueError("dataset.train_fraction must be in (0, 1)")
    if not (0.0 < validation_fraction < 1.0 - train_fraction):
        raise ValueError(
            "dataset.validation_fraction must leave a nonempty future test window"
        )
    for key in ("nlist", "nprobe", "hard_negative_search_k", "evaluation_search_k"):
        if int(config["index"][key]) <= 0:
            raise ValueError(f"index.{key} must be positive")
    if int(config["adapter"]["rank"]) <= 0:
        raise ValueError("adapter.rank must be positive")
    if int(config["adapter"]["epochs"]) <= 0:
        raise ValueError("adapter.epochs must be positive")
    for key in (
        "explicit_margin",
        "confusion_margin",
        "explicit_weight",
        "confusion_weight",
        "anchor_coefficient",
    ):
        if float(config["adapter"][key]) < 0.0:
            raise ValueError(f"adapter.{key} must be nonnegative")
    if int(config["adapter"].get("maximum_training_pairs", 1)) <= 0:
        raise ValueError("adapter.maximum_training_pairs must be positive")
    if int(config["evaluation"]["bootstrap_repetitions"]) < 100:
        raise ValueError("At least 100 paired bootstrap repetitions are required")


def deterministic_setup(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


def acquire_input_zip(
    destination: Path,
    url: str,
    local_zip: Path | None,
    expected_sha256: str | None,
) -> str:
    temporary = destination.with_name(
        f".{destination.name}.download.{os.getpid()}.{uuid.uuid4().hex}"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temporary.open("xb") as output:
            if local_zip is not None:
                with local_zip.open("rb") as source:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
            else:
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": "RIPPLE-research-poc/1.0"},
                )
                with urllib.request.urlopen(request, timeout=120) as source:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        digest = sha256_file(temporary)
        if expected_sha256 and digest.lower() != expected_sha256.lower():
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


def extract_movielens_files(zip_path: Path, output_directory: Path) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = {Path(name).name: name for name in archive.namelist()}
        missing = {"u.data", "u.item"} - set(members)
        if missing:
            raise IntegrityError(f"MovieLens archive is missing: {sorted(missing)}")
        paths: dict[str, Path] = {}
        for base_name in ("u.data", "u.item"):
            info = archive.getinfo(members[base_name])
            if info.is_dir() or info.file_size <= 0:
                raise IntegrityError(f"Invalid archive member: {members[base_name]}")
            data = archive.read(info)
            destination = output_directory / base_name
            publish_bytes_no_overwrite(destination, data)
            paths[base_name] = destination
    return paths["u.data"], paths["u.item"]


def load_item_metadata(item_path: Path) -> tuple[list[int], list[str]]:
    records: list[tuple[int, str]] = []
    with item_path.open("r", encoding="latin-1", newline="") as handle:
        reader = csv.reader(handle, delimiter="|")
        for fields in reader:
            if len(fields) < 24:
                raise IntegrityError(f"Malformed u.item row with {len(fields)} fields")
            item_id = int(fields[0])
            title = fields[1].strip()
            genre_flags = [int(value) for value in fields[5:24]]
            genres = [
                genre
                for genre, enabled in zip(GENRE_NAMES, genre_flags, strict=True)
                if enabled
            ]
            genre_text = " | ".join(genres) if genres else "unknown"
            records.append((item_id, f"{title} [SEP] {genre_text}"))
    records.sort(key=lambda value: value[0])
    item_ids = [value[0] for value in records]
    if len(item_ids) != len(set(item_ids)):
        raise IntegrityError("Duplicate item IDs in u.item")
    return item_ids, [value[1] for value in records]


def load_interactions(
    data_path: Path, item_id_to_index: Mapping[int, int]
) -> list[Interaction]:
    interactions: list[Interaction] = []
    with data_path.open("r", encoding="ascii", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for ordinal, fields in enumerate(reader):
            if len(fields) != 4:
                raise IntegrityError(f"Malformed u.data row: {fields!r}")
            user_id, item_id, rating, timestamp = map(int, fields)
            if item_id not in item_id_to_index:
                raise IntegrityError(f"Interaction references missing item {item_id}")
            interactions.append(
                Interaction(
                    user_id=user_id,
                    item_index=item_id_to_index[item_id],
                    rating=rating,
                    timestamp=timestamp,
                    ordinal=ordinal,
                )
            )
    return interactions


def chronological_user_splits(
    interactions: Sequence[Interaction], dataset_config: Mapping[str, Any]
) -> list[UserSplit]:
    positive_min = int(dataset_config["positive_rating_min"])
    minimum_total_positives = int(dataset_config["minimum_total_positives"])
    minimum_train_events = int(dataset_config["minimum_train_events"])
    train_fraction = float(dataset_config["train_fraction"])
    validation_fraction = float(dataset_config["validation_fraction"])
    grouped: dict[int, list[Interaction]] = defaultdict(list)
    for event in interactions:
        grouped[event.user_id].append(event)
    splits: list[UserSplit] = []
    for user_id in sorted(grouped):
        events = sorted(
            grouped[user_id],
            key=lambda event: (event.timestamp, event.ordinal),
        )
        if sum(event.rating >= positive_min for event in events) < minimum_total_positives:
            continue
        train_end = int(math.floor(len(events) * train_fraction))
        validation_end = int(
            math.floor(len(events) * (train_fraction + validation_fraction))
        )
        if train_end < minimum_train_events or validation_end <= train_end:
            continue
        if validation_end >= len(events):
            continue
        train = tuple(events[:train_end])
        validation_window = tuple(events[train_end:validation_end])
        test_window = tuple(events[validation_end:])
        validation_positives = [
            event for event in validation_window if event.rating >= positive_min
        ]
        test_positives = [event for event in test_window if event.rating >= positive_min]
        if not validation_positives or not test_positives:
            continue
        if sum(event.rating >= positive_min for event in train) < int(
            dataset_config["minimum_query_positives"]
        ):
            continue
        validation = validation_positives[0]
        test = test_positives[0]
        test_history = tuple(events[:validation_end])
        if train[-1].timestamp > validation.timestamp or validation.timestamp > test.timestamp:
            raise IntegrityError("Temporal split ordering invariant failed")
        splits.append(
            UserSplit(
                user_id=user_id,
                train=train,
                validation_window=validation_window,
                test_window=test_window,
                validation=validation,
                test=test,
                test_history=test_history,
            )
        )
    if not splits:
        raise IntegrityError("No users satisfy the chronological split contract")
    return splits


def normalized_centroid(
    history: Sequence[Interaction], item_vectors: np.ndarray, positive_min: int
) -> np.ndarray:
    positive_items = [
        event.item_index for event in history if event.rating >= positive_min
    ]
    if not positive_items:
        raise IntegrityError("A query has no positive history")
    centroid = np.mean(item_vectors[np.asarray(positive_items, dtype=np.int64)], axis=0)
    norm = float(np.linalg.norm(centroid))
    if not math.isfinite(norm) or norm <= 0.0:
        raise IntegrityError("Invalid history centroid")
    return np.asarray(centroid / norm, dtype=np.float32)


def build_train_corpus(
    splits: Sequence[UserSplit],
    item_vectors: np.ndarray,
    dataset_config: Mapping[str, Any],
) -> TrainCorpus:
    positive_min = int(dataset_config["positive_rating_min"])
    dislike_max = int(dataset_config["dislike_rating_max"])
    minimum_query_positives = int(dataset_config["minimum_query_positives"])
    queries: list[np.ndarray] = []
    chosen: list[int] = []
    excluded: list[frozenset[int]] = []
    dislikes: list[tuple[int, ...]] = []
    user_ids: list[int] = []
    for split in splits:
        prefix: list[Interaction] = []
        for event in split.train:
            positive_count = sum(
                previous.rating >= positive_min for previous in prefix
            )
            if event.rating >= positive_min and positive_count >= minimum_query_positives:
                queries.append(normalized_centroid(prefix, item_vectors, positive_min))
                chosen.append(event.item_index)
                excluded.append(
                    frozenset(
                        [previous.item_index for previous in prefix]
                        + [event.item_index]
                    )
                )
                dislikes.append(
                    tuple(
                        sorted(
                            {
                                previous.item_index
                                for previous in prefix
                                if previous.rating <= dislike_max
                            }
                        )
                    )
                )
                user_ids.append(split.user_id)
            prefix.append(event)
    if not queries:
        raise IntegrityError("No preference-training examples were constructed")
    return TrainCorpus(
        queries=np.stack(queries).astype(np.float32, copy=False),
        chosen_items=np.asarray(chosen, dtype=np.int64),
        excluded_items=tuple(excluded),
        explicit_dislikes=tuple(dislikes),
        user_ids=np.asarray(user_ids, dtype=np.int64),
    )


def deterministic_subsample_train_corpus(
    corpus: TrainCorpus, maximum_pairs: int, seed: int
) -> TrainCorpus:
    if len(corpus.chosen_items) <= maximum_pairs:
        return corpus
    # Round-robin across deterministically shuffled per-user queues preserves
    # broad user coverage while bounding the small-scale PoC runtime.
    rng = np.random.default_rng(seed)
    by_user: dict[int, list[int]] = defaultdict(list)
    for row, user_id in enumerate(corpus.user_ids):
        by_user[int(user_id)].append(row)
    for rows in by_user.values():
        rng.shuffle(rows)
    users = np.asarray(sorted(by_user), dtype=np.int64)
    rng.shuffle(users)
    selected: list[int] = []
    depth = 0
    while len(selected) < maximum_pairs:
        added = False
        for user_id in users:
            rows = by_user[int(user_id)]
            if depth < len(rows):
                selected.append(rows[depth])
                added = True
                if len(selected) == maximum_pairs:
                    break
        if not added:
            break
        depth += 1
    indices = np.asarray(sorted(selected), dtype=np.int64)
    return TrainCorpus(
        queries=corpus.queries[indices],
        chosen_items=corpus.chosen_items[indices],
        excluded_items=tuple(corpus.excluded_items[index] for index in indices),
        explicit_dislikes=tuple(corpus.explicit_dislikes[index] for index in indices),
        user_ids=corpus.user_ids[indices],
    )


def build_eval_corpus(
    splits: Sequence[UserSplit],
    item_vectors: np.ndarray,
    dataset_config: Mapping[str, Any],
    stage: str,
) -> EvalCorpus:
    if stage not in {"validation", "test"}:
        raise ValueError(f"Unsupported evaluation stage: {stage}")
    positive_min = int(dataset_config["positive_rating_min"])
    dislike_max = int(dataset_config["dislike_rating_max"])
    queries: list[np.ndarray] = []
    user_ids: list[int] = []
    targets: list[int] = []
    quality_blocked: list[frozenset[int]] = []
    safety_blocked: list[frozenset[int]] = []
    known_dislikes: list[frozenset[int]] = []
    for split in splits:
        if stage == "validation":
            history = split.train
            target = split.validation
            future_window = split.validation_window
        else:
            history = split.test_history
            target = split.test
            future_window = split.test_window
        query = normalized_centroid(history, item_vectors, positive_min)
        all_seen = {event.item_index for event in history}
        dislikes = {
            event.item_index
            for event in future_window
            if event.rating <= dislike_max
        }
        queries.append(query)
        user_ids.append(split.user_id)
        targets.append(target.item_index)
        quality_blocked.append(frozenset(all_seen))
        # Safety is evaluated against low ratings in the untouched future
        # window, so those items are not past-seen and require no special
        # unsuppression.  This avoids the trivial zero obtained by measuring
        # already-filtered historical dislikes.
        safety_blocked.append(frozenset(all_seen))
        known_dislikes.append(frozenset(dislikes))
    return EvalCorpus(
        queries=np.stack(queries).astype(np.float32, copy=False),
        user_ids=np.asarray(user_ids, dtype=np.int64),
        targets=np.asarray(targets, dtype=np.int64),
        quality_blocked=tuple(quality_blocked),
        safety_blocked=tuple(safety_blocked),
        known_dislikes=tuple(known_dislikes),
    )


def encode_item_metadata(
    metadata: Sequence[str], embedding_config: Mapping[str, Any]
) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for this registered PoC"
        ) from exc
    model = SentenceTransformer(
        str(embedding_config["model_name"]),
        device="cpu",
        local_files_only=bool(embedding_config.get("local_files_only", True)),
    )
    embeddings = model.encode(
        list(metadata),
        batch_size=int(embedding_config["batch_size"]),
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    vectors = np.ascontiguousarray(embeddings, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(metadata):
        raise IntegrityError(f"Unexpected embedding shape: {vectors.shape}")
    if not np.all(np.isfinite(vectors)):
        raise IntegrityError("Item embeddings contain nonfinite values")
    norms = np.linalg.norm(vectors, axis=1)
    if float(np.max(np.abs(norms - 1.0))) > 1e-4:
        raise IntegrityError("SentenceTransformer embeddings are not normalized")
    return vectors


def build_faiss_index(
    item_vectors: np.ndarray, index_config: Mapping[str, Any], seed: int
) -> tuple[Any, Any]:
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError(
            "faiss-cpu is required. The PoC refuses a sklearn or brute-force "
            "substitute masquerading as FAISS."
        ) from exc
    faiss.omp_set_num_threads(1)
    dimension = int(item_vectors.shape[1])
    nlist = int(index_config["nlist"])
    if nlist >= item_vectors.shape[0]:
        raise ValueError("index.nlist must be smaller than the catalog")
    quantizer = faiss.IndexFlatIP(dimension)
    index = faiss.IndexIVFFlat(
        quantizer,
        dimension,
        nlist,
        faiss.METRIC_INNER_PRODUCT,
    )
    if hasattr(index, "cp"):
        index.cp.seed = int(seed)
        index.cp.niter = 20
    index.train(item_vectors)
    if not index.is_trained:
        raise IntegrityError("FAISS IVF training did not complete")
    index.add(item_vectors)
    index.nprobe = int(index_config["nprobe"])
    if int(index.ntotal) != int(item_vectors.shape[0]):
        raise IntegrityError("FAISS index item count mismatch")
    return faiss, index


class LowRankQueryAdapter(nn.Module):
    """Identity-initialized low-rank residual transform over user queries."""

    def __init__(self, dimension: int, rank: int, residual_scale: float) -> None:
        super().__init__()
        self.down = nn.Linear(dimension, rank, bias=False)
        self.up = nn.Linear(rank, dimension, bias=False)
        self.residual_scale = float(residual_scale)
        nn.init.normal_(self.down.weight, mean=0.0, std=0.02)
        nn.init.zeros_(self.up.weight)

    def forward(self, query: torch.Tensor) -> torch.Tensor:
        residual = self.up(torch.tanh(self.down(query)))
        return F.normalize(query + self.residual_scale * residual, dim=-1)


def export_adapter(adapter: LowRankQueryAdapter | None) -> dict[str, Any] | None:
    if adapter is None:
        return None
    return {
        "down": adapter.down.weight.detach().cpu().numpy().astype(np.float32),
        "up": adapter.up.weight.detach().cpu().numpy().astype(np.float32),
        "residual_scale": float(adapter.residual_scale),
    }


def adapt_queries_numpy(
    queries: np.ndarray, adapter_state: Mapping[str, Any] | None
) -> np.ndarray:
    base = np.asarray(queries, dtype=np.float32)
    if adapter_state is None:
        output = base.copy()
    else:
        down = np.asarray(adapter_state["down"], dtype=np.float32)
        up = np.asarray(adapter_state["up"], dtype=np.float32)
        hidden = np.tanh(base @ down.T)
        output = base + float(adapter_state["residual_scale"]) * (hidden @ up.T)
    norms = np.linalg.norm(output, axis=1, keepdims=True)
    if np.any(norms <= 0.0) or not np.all(np.isfinite(norms)):
        raise IntegrityError("Adapter produced an invalid query")
    return np.ascontiguousarray(output / norms, dtype=np.float32)


def choose_random_rejections(
    corpus: TrainCorpus, catalog_size: int, seed: int
) -> NegativeSelection:
    rng = np.random.default_rng(seed)
    rejected = np.empty(len(corpus.chosen_items), dtype=np.int64)
    source_codes = np.empty(len(corpus.chosen_items), dtype=np.uint8)
    fallback = np.zeros(len(corpus.chosen_items), dtype=np.uint8)
    for index, excluded in enumerate(corpus.excluded_items):
        explicit = corpus.explicit_dislikes[index]
        if explicit:
            rejected[index] = explicit[int(rng.integers(0, len(explicit)))]
            source_codes[index] = 1
            continue
        if len(excluded) >= catalog_size:
            raise IntegrityError("A training example excludes the entire catalog")
        for _ in range(10_000):
            candidate = int(rng.integers(0, catalog_size))
            if candidate not in excluded:
                rejected[index] = candidate
                source_codes[index] = 2
                break
        else:
            candidates = [item for item in range(catalog_size) if item not in excluded]
            rejected[index] = candidates[int(rng.integers(0, len(candidates)))]
            source_codes[index] = 2
    return NegativeSelection(rejected, source_codes, fallback)


def choose_exact_full_matrix_rejections(
    corpus: TrainCorpus,
    adapted_queries: np.ndarray,
    item_vectors: np.ndarray,
    chunk_size: int = 256,
) -> NegativeSelection:
    """Mine the exact highest-score valid rejection over the whole catalog.

    This A2 control uses the same adapter/loss/schedule as random and RIPPLE;
    it changes only negative selection and therefore isolates approximation at
    the deployed IVF boundary from generic hard-negative benefits.
    """
    rejected = np.empty(len(corpus.chosen_items), dtype=np.int64)
    source_codes = np.empty(len(corpus.chosen_items), dtype=np.uint8)
    fallback = np.zeros(len(corpus.chosen_items), dtype=np.uint8)
    for start in range(0, len(corpus.chosen_items), chunk_size):
        end = min(start + chunk_size, len(corpus.chosen_items))
        scores = adapted_queries[start:end] @ item_vectors.T
        for offset, row in enumerate(range(start, end)):
            explicit = corpus.explicit_dislikes[row]
            if explicit:
                candidates = np.asarray(explicit, dtype=np.int64)
                rejected[row] = int(candidates[int(np.argmax(scores[offset, candidates]))])
                source_codes[row] = 1
                continue
            blocked = np.fromiter(
                corpus.excluded_items[row], dtype=np.int64, count=len(corpus.excluded_items[row])
            )
            scores[offset, blocked] = -np.inf
            candidate = int(np.argmax(scores[offset]))
            if not math.isfinite(float(scores[offset, candidate])):
                raise IntegrityError("Exact hard-negative row has no valid item")
            rejected[row] = candidate
            source_codes[row] = 3
    return NegativeSelection(rejected, source_codes, fallback)


def choose_index_boundary_rejections(
    corpus: TrainCorpus,
    adapted_queries: np.ndarray,
    item_vectors: np.ndarray,
    index: Any,
    search_k: int,
    candidate_count: int,
) -> NegativeSelection:
    k = min(int(search_k), int(item_vectors.shape[0]))
    _, neighbors = index.search(adapted_queries, k)
    rejected = np.empty(len(corpus.chosen_items), dtype=np.int64)
    source_codes = np.empty(len(corpus.chosen_items), dtype=np.uint8)
    fallback = np.zeros(len(corpus.chosen_items), dtype=np.uint8)
    for row in range(len(corpus.chosen_items)):
        explicit = set(corpus.explicit_dislikes[row])
        selected: int | None = None
        if explicit:
            # Prefer the highest-ranked known dislike *within the deployed IVF
            # traversal*.  If IVF does not expose one, use the exact hardest
            # explicit rejection rather than discard reliable feedback.
            for candidate in neighbors[row]:
                candidate_int = int(candidate)
                if candidate_int in explicit:
                    selected = candidate_int
                    break
            if selected is None:
                explicit_array = np.asarray(sorted(explicit), dtype=np.int64)
                scores = item_vectors[explicit_array] @ adapted_queries[row]
                selected = int(explicit_array[int(np.argmax(scores))])
                fallback[row] = 1
            source_codes[row] = 1
        else:
            excluded = corpus.excluded_items[row]
            valid_neighbors = [
                int(candidate)
                for candidate in neighbors[row]
                if int(candidate) >= 0 and int(candidate) not in excluded
            ]
            chosen = int(corpus.chosen_items[row])
            raw_neighbors = [int(candidate) for candidate in neighbors[row]]
            if chosen in raw_neighbors:
                positive_position = raw_neighbors.index(chosen)
                above_positive = [
                    candidate
                    for candidate in raw_neighbors[:positive_position]
                    if candidate >= 0 and candidate not in excluded
                ]
                if positive_position < candidate_count and above_positive:
                    selected = above_positive[-1]
            if selected is None and valid_neighbors:
                selected = valid_neighbors[min(candidate_count - 1, len(valid_neighbors) - 1)]
            if selected is not None:
                source_codes[row] = 4
        if selected is None:
            scores = item_vectors @ adapted_queries[row]
            blocked = np.fromiter(
                corpus.excluded_items[row], dtype=np.int64, count=len(corpus.excluded_items[row])
            )
            scores[blocked] = -np.inf
            selected = int(np.argmax(scores))
            if not math.isfinite(float(scores[selected])):
                raise IntegrityError("ANN fallback has no valid rejected item")
            source_codes[row] = 5
            fallback[row] = 1
        rejected[row] = selected
    return NegativeSelection(rejected, source_codes, fallback)


def exact_reranked_candidates(
    query: np.ndarray,
    item_vectors: np.ndarray,
    index: Any,
    search_k: int,
) -> list[int]:
    k = min(int(search_k), int(item_vectors.shape[0]))
    _, approximate = index.search(query.reshape(1, -1), k)
    candidates = np.asarray(
        sorted({int(value) for value in approximate[0] if int(value) >= 0}),
        dtype=np.int64,
    )
    if candidates.size == 0:
        return []
    scores = item_vectors[candidates] @ query
    order = np.lexsort((candidates, -scores))
    return [int(value) for value in candidates[order]]


def filter_ranking(ranking: Iterable[int], blocked: frozenset[int]) -> list[int]:
    return [item for item in ranking if item not in blocked]


def evaluate_vector_method(
    corpus: EvalCorpus,
    adapter_state: Mapping[str, Any] | None,
    item_vectors: np.ndarray,
    index: Any,
    search_k: int,
    ndcg_k: int,
    recall_k: int,
) -> dict[str, Any]:
    adapted = adapt_queries_numpy(corpus.queries, adapter_state)
    per_user: list[dict[str, Any]] = []
    for row, query in enumerate(adapted):
        candidate_order = exact_reranked_candidates(
            query, item_vectors, index, search_k
        )
        quality = filter_ranking(candidate_order, corpus.quality_blocked[row])
        safety = filter_ranking(candidate_order, corpus.safety_blocked[row])
        target = int(corpus.targets[row])
        try:
            rank = quality.index(target) + 1
        except ValueError:
            rank = None
        ndcg = (
            1.0 / math.log2(rank + 1.0)
            if rank is not None and rank <= ndcg_k
            else 0.0
        )
        recall = float(rank is not None and rank <= recall_k)
        dislikes = corpus.known_dislikes[row]
        intrusion = (
            sum(item in dislikes for item in safety[:ndcg_k]) / float(ndcg_k)
            if dislikes
            else None
        )
        per_user.append(
            {
                "user_id": int(corpus.user_ids[row]),
                "target_item_index": target,
                "target_rank": rank,
                "ndcg_at_10": float(ndcg),
                "recall_at_50": float(recall),
                "dislike_intrusion_at_10": (
                    None if intrusion is None else float(intrusion)
                ),
            }
        )
    safety_values = [
        row["dislike_intrusion_at_10"]
        for row in per_user
        if row["dislike_intrusion_at_10"] is not None
    ]
    return {
        "ndcg_at_10": float(np.mean([row["ndcg_at_10"] for row in per_user])),
        "recall_at_50": float(
            np.mean([row["recall_at_50"] for row in per_user])
        ),
        "dislike_intrusion_at_10": (
            float(np.mean(safety_values)) if safety_values else None
        ),
        "users": len(per_user),
        "users_with_known_dislikes": len(safety_values),
        "per_user": per_user,
    }


def train_adapter_variant(
    variant: str,
    initial_state: Mapping[str, torch.Tensor],
    corpus: TrainCorpus,
    validation_corpus: EvalCorpus,
    item_vectors: np.ndarray,
    index: Any,
    config: Mapping[str, Any],
    seed: int,
    run_directory: Path,
    execution_short: str,
    error_ledger: Path,
) -> tuple[LowRankQueryAdapter, list[dict[str, Any]], Path, dict[str, Any]]:
    if variant not in {"random", "exact_hard", "index_boundary"}:
        raise ValueError(f"Unsupported adapter variant: {variant}")
    adapter_config = config["adapter"]
    evaluation_config = config["evaluation"]
    index_config = config["index"]
    adapter = LowRankQueryAdapter(
        dimension=item_vectors.shape[1],
        rank=int(adapter_config["rank"]),
        residual_scale=float(adapter_config["residual_scale"]),
    )
    adapter.load_state_dict(initial_state)
    optimizer = torch.optim.AdamW(
        adapter.parameters(),
        lr=float(adapter_config["learning_rate"]),
        weight_decay=float(adapter_config["weight_decay"]),
    )
    item_tensor = torch.from_numpy(np.array(item_vectors, copy=True))
    beta = float(adapter_config["simpo_beta"])
    temperature = float(adapter_config["temperature"])
    batch_size = int(adapter_config["batch_size"])
    traces: list[dict[str, Any]] = []
    boundary_intended_total = 0
    boundary_genuine_total = 0
    fallback_total = 0
    epochs = int(adapter_config["epochs"])
    for epoch in range(1, epochs + 1):
        adapter.eval()
        adapted_queries = adapt_queries_numpy(corpus.queries, export_adapter(adapter))
        if variant == "random":
            selection = choose_random_rejections(
                corpus,
                catalog_size=item_vectors.shape[0],
                seed=seed + epoch * 1009,
            )
        elif variant == "exact_hard":
            selection = choose_exact_full_matrix_rejections(
                corpus,
                adapted_queries,
                item_vectors,
            )
        else:
            index.nprobe = int(index_config["nprobe"])
            selection = choose_index_boundary_rejections(
                corpus,
                adapted_queries,
                item_vectors,
                index,
                int(index_config["hard_negative_search_k"]),
                int(index_config["candidate_count"]),
            )
        # Explicit low-rating pairs are held identical across all mechanism
        # variants; only the implicit-confusion selector may differ.
        for row, explicit_items in enumerate(corpus.explicit_dislikes):
            if explicit_items:
                shared_position = (seed + epoch + row) % len(explicit_items)
                selection.item_indices[row] = explicit_items[shared_position]
                selection.source_codes[row] = 1
                selection.fallback[row] = 0
        rejected = selection.item_indices
        implicit_mask = np.asarray(
            [not bool(values) for values in corpus.explicit_dislikes], dtype=bool
        )
        if variant == "index_boundary":
            boundary_intended = int(np.sum(implicit_mask))
            boundary_genuine = int(
                np.sum((selection.source_codes == 4) & implicit_mask)
            )
            boundary_intended_total += boundary_intended
            boundary_genuine_total += boundary_genuine
        else:
            boundary_intended = 0
            boundary_genuine = 0
        fallback_total += int(np.sum(selection.fallback))
        pair_records = np.empty(
            len(corpus.chosen_items),
            dtype=[
                ("user_id", "<i4"),
                ("chosen_item", "<i4"),
                ("rejected_item", "<i4"),
                ("source_code", "u1"),
                ("fallback", "u1"),
                ("epoch", "<i2"),
            ],
        )
        pair_records["user_id"] = corpus.user_ids.astype(np.int32)
        pair_records["chosen_item"] = corpus.chosen_items.astype(np.int32)
        pair_records["rejected_item"] = rejected.astype(np.int32)
        pair_records["source_code"] = selection.source_codes
        pair_records["fallback"] = selection.fallback
        pair_records["epoch"] = epoch
        save_numpy_no_overwrite(
            run_directory
            / f"pair_ids_{variant}_seed{seed}_{execution_short}_seq{epoch:03d}.npy",
            pair_records,
        )
        permutation = np.random.default_rng(seed + epoch * 65537).permutation(
            len(corpus.chosen_items)
        )
        epoch_losses: list[float] = []
        adapter.train()
        for start in range(0, len(permutation), batch_size):
            batch_indices = permutation[start : start + batch_size]
            query_tensor = torch.from_numpy(corpus.queries[batch_indices])
            chosen_tensor = item_tensor[
                torch.from_numpy(corpus.chosen_items[batch_indices])
            ]
            rejected_tensor = item_tensor[
                torch.from_numpy(rejected[batch_indices])
            ]
            source_tensor = torch.from_numpy(
                selection.source_codes[batch_indices].astype(np.int64)
            )
            adapted_tensor = adapter(query_tensor)
            chosen_score = torch.sum(adapted_tensor * chosen_tensor, dim=-1)
            rejected_score = torch.sum(adapted_tensor * rejected_tensor, dim=-1)
            explicit_pair = source_tensor == 1
            margin = torch.where(
                explicit_pair,
                torch.full_like(chosen_score, float(adapter_config["explicit_margin"])),
                torch.full_like(chosen_score, float(adapter_config["confusion_margin"])),
            )
            reliability_weight = torch.where(
                explicit_pair,
                torch.full_like(chosen_score, float(adapter_config["explicit_weight"])),
                torch.full_like(chosen_score, float(adapter_config["confusion_weight"])),
            )
            shifted_preference_logit = (
                (beta / temperature) * (chosen_score - rejected_score) - margin
            )
            pair_loss = -reliability_weight * F.logsigmoid(shifted_preference_logit)
            anchor_loss = float(adapter_config["anchor_coefficient"]) * (
                1.0 - torch.sum(adapted_tensor * query_tensor, dim=-1)
            )
            # With one chosen/rejected item, this SimPO-derived reference-free
            # objective is algebraically margin-shifted weighted BPR/RankNet.
            loss = (pair_loss + anchor_loss).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                adapter.parameters(),
                float(adapter_config["gradient_clip_norm"]),
            )
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))
        adapter.eval()
        validation = evaluate_vector_method(
            validation_corpus,
            export_adapter(adapter),
            item_vectors,
            index,
            int(index_config["evaluation_search_k"]),
            int(evaluation_config["ndcg_k"]),
            int(evaluation_config["recall_k"]),
        )
        trace = {
            "variant": variant,
            "epoch": epoch,
            "fixed_registered_epochs": epochs,
            "mean_simpo_loss": float(np.mean(epoch_losses)),
            "validation_ndcg_at_10": validation["ndcg_at_10"],
            "validation_recall_at_50": validation["recall_at_50"],
            "explicit_pair_count": int(np.sum(selection.source_codes == 1)),
            "confusion_pair_count": int(np.sum(selection.source_codes != 1)),
            "boundary_intended_count": boundary_intended,
            "boundary_genuine_count": boundary_genuine,
            "boundary_source_rate": (
                None
                if boundary_intended == 0
                else float(boundary_genuine / boundary_intended)
            ),
            "fallback_count": int(np.sum(selection.fallback)),
            "test_was_evaluated": False,
            "utc": utc_now(),
        }
        traces.append(trace)
        trace_path = run_directory / (
            f"training_trace_{variant}_seed{seed}_{execution_short}_seq{epoch:03d}.json"
        )
        publish_json_no_overwrite(trace_path, trace)
        if error_ledger.stat().st_size != 0:
            raise IntegrityError(
                "Asynchronous-error ledger is nonempty; refusing further training"
            )
    checkpoint_path = run_directory / (
        f"adapter_{variant}_seed{seed}_{execution_short}_seq{epochs:03d}.pt"
    )
    save_torch_no_overwrite(
        checkpoint_path,
        {
            "schema": "ripple-query-adapter-v1",
            "variant": variant,
            "seed": seed,
            "execution_fingerprint": execution_short,
            "registered_final_epoch": epochs,
            "state_dict": adapter.state_dict(),
            "dimension": int(item_vectors.shape[1]),
            "rank": int(adapter_config["rank"]),
            "residual_scale": float(adapter_config["residual_scale"]),
        },
    )
    diagnostics = {
        "variant": variant,
        "seed": seed,
        "boundary_intended_total": boundary_intended_total,
        "boundary_genuine_total": boundary_genuine_total,
        "boundary_source_rate": (
            None
            if boundary_intended_total == 0
            else float(boundary_genuine_total / boundary_intended_total)
        ),
        "fallback_total": fallback_total,
    }
    return adapter, traces, checkpoint_path, diagnostics


class BPRMatrixFactorization(nn.Module):
    def __init__(self, users: int, items: int, dimension: int) -> None:
        super().__init__()
        self.user = nn.Embedding(users, dimension)
        self.item = nn.Embedding(items, dimension)
        nn.init.normal_(self.user.weight, std=0.05)
        nn.init.normal_(self.item.weight, std=0.05)


def train_bpr_baseline(
    splits: Sequence[UserSplit],
    catalog_size: int,
    dataset_config: Mapping[str, Any],
    bpr_config: Mapping[str, Any],
    seed: int,
    run_directory: Path,
    execution_short: str,
) -> tuple[BPRMatrixFactorization, dict[int, int], Path]:
    user_to_row = {split.user_id: row for row, split in enumerate(splits)}
    positive_min = int(dataset_config["positive_rating_min"])
    positive_sets: dict[int, set[int]] = {}
    pairs: list[tuple[int, int]] = []
    for split in splits:
        user_row = user_to_row[split.user_id]
        positives = {
            event.item_index
            for event in split.train
            if event.rating >= positive_min
        }
        positive_sets[user_row] = positives
        pairs.extend((user_row, item) for item in sorted(positives))
    if not pairs:
        raise IntegrityError("BPR baseline has no positive training pairs")
    pair_array = np.asarray(pairs, dtype=np.int64)
    model = BPRMatrixFactorization(
        users=len(splits),
        items=catalog_size,
        dimension=int(bpr_config["embedding_dimension"]),
    )
    optimizer = torch.optim.Adam(
        model.parameters(), lr=float(bpr_config["learning_rate"])
    )
    batch_size = int(bpr_config["batch_size"])
    regularization = float(bpr_config["l2_regularization"])
    epochs = int(bpr_config["epochs"])
    for epoch in range(1, epochs + 1):
        rng = np.random.default_rng(seed + 700_001 + epoch * 1013)
        negatives = np.empty(len(pair_array), dtype=np.int64)
        for row, (user_row, _) in enumerate(pair_array):
            while True:
                candidate = int(rng.integers(0, catalog_size))
                if candidate not in positive_sets[int(user_row)]:
                    negatives[row] = candidate
                    break
        permutation = np.random.default_rng(
            seed + 900_001 + epoch * 65537
        ).permutation(len(pair_array))
        losses: list[float] = []
        for start in range(0, len(permutation), batch_size):
            indices = permutation[start : start + batch_size]
            users_tensor = torch.from_numpy(pair_array[indices, 0])
            positives_tensor = torch.from_numpy(pair_array[indices, 1])
            negatives_tensor = torch.from_numpy(negatives[indices])
            user_vector = model.user(users_tensor)
            positive_vector = model.item(positives_tensor)
            negative_vector = model.item(negatives_tensor)
            positive_score = torch.sum(user_vector * positive_vector, dim=-1)
            negative_score = torch.sum(user_vector * negative_vector, dim=-1)
            ranking_loss = -F.logsigmoid(positive_score - negative_score).mean()
            penalty = regularization * (
                user_vector.square().mean()
                + positive_vector.square().mean()
                + negative_vector.square().mean()
            )
            loss = ranking_loss + penalty
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        publish_json_no_overwrite(
            run_directory
            / f"training_trace_bpr_seed{seed}_{execution_short}_seq{epoch:03d}.json",
            {
                "variant": "bpr_mf",
                "epoch": epoch,
                "fixed_registered_epochs": epochs,
                "mean_loss": float(np.mean(losses)),
                "test_was_evaluated": False,
                "utc": utc_now(),
            },
        )
    checkpoint = (
        run_directory / f"bpr_mf_seed{seed}_{execution_short}_seq{epochs:03d}.pt"
    )
    save_torch_no_overwrite(
        checkpoint,
        {
            "schema": "bpr-mf-baseline-v1",
            "execution_fingerprint": execution_short,
            "seed": seed,
            "registered_final_epoch": epochs,
            "state_dict": model.state_dict(),
            "user_to_row": user_to_row,
        },
    )
    return model, user_to_row, checkpoint


def evaluate_bpr(
    model: BPRMatrixFactorization,
    user_to_row: Mapping[int, int],
    corpus: EvalCorpus,
    ndcg_k: int,
    recall_k: int,
) -> dict[str, Any]:
    user_matrix = model.user.weight.detach().cpu().numpy()
    item_matrix = model.item.weight.detach().cpu().numpy()
    per_user: list[dict[str, Any]] = []
    for row, user_id in enumerate(corpus.user_ids):
        scores = item_matrix @ user_matrix[user_to_row[int(user_id)]]
        item_indices = np.arange(len(scores), dtype=np.int64)
        order = np.lexsort((item_indices, -scores))
        ranking = [int(value) for value in order]
        quality = filter_ranking(ranking, corpus.quality_blocked[row])
        safety = filter_ranking(ranking, corpus.safety_blocked[row])
        target = int(corpus.targets[row])
        try:
            rank = quality.index(target) + 1
        except ValueError:
            rank = None
        ndcg = (
            1.0 / math.log2(rank + 1.0)
            if rank is not None and rank <= ndcg_k
            else 0.0
        )
        recall = float(rank is not None and rank <= recall_k)
        dislikes = corpus.known_dislikes[row]
        intrusion = (
            sum(item in dislikes for item in safety[:ndcg_k]) / float(ndcg_k)
            if dislikes
            else None
        )
        per_user.append(
            {
                "user_id": int(user_id),
                "target_item_index": target,
                "target_rank": rank,
                "ndcg_at_10": float(ndcg),
                "recall_at_50": float(recall),
                "dislike_intrusion_at_10": (
                    None if intrusion is None else float(intrusion)
                ),
            }
        )
    safety_values = [
        row["dislike_intrusion_at_10"]
        for row in per_user
        if row["dislike_intrusion_at_10"] is not None
    ]
    return {
        "ndcg_at_10": float(np.mean([row["ndcg_at_10"] for row in per_user])),
        "recall_at_50": float(
            np.mean([row["recall_at_50"] for row in per_user])
        ),
        "dislike_intrusion_at_10": (
            float(np.mean(safety_values)) if safety_values else None
        ),
        "users": len(per_user),
        "users_with_known_dislikes": len(safety_values),
        "per_user": per_user,
    }


def benchmark_vector_latency(
    corpus: EvalCorpus,
    adapter_state: Mapping[str, Any] | None,
    item_vectors: np.ndarray,
    index: Any,
    search_k: int,
    warmup_rounds: int,
    measured_rounds: int,
) -> dict[str, Any]:
    samples_ms: list[float] = []
    total_rounds = warmup_rounds + measured_rounds
    for round_index in range(total_rounds):
        for row, base_query in enumerate(corpus.queries):
            start_ns = time.perf_counter_ns()
            query = adapt_queries_numpy(
                base_query.reshape(1, -1), adapter_state
            )[0]
            ranking = exact_reranked_candidates(
                query, item_vectors, index, search_k
            )
            _ = filter_ranking(ranking, corpus.quality_blocked[row])[:50]
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            if round_index >= warmup_rounds:
                samples_ms.append(float(elapsed_ms))
    if not samples_ms:
        raise IntegrityError("Latency benchmark produced no samples")
    return {
        "p50_ms": float(np.percentile(samples_ms, 50)),
        "p95_ms": float(np.percentile(samples_ms, 95)),
        "mean_ms": float(np.mean(samples_ms)),
        "sample_count": len(samples_ms),
        "warmup_rounds": int(warmup_rounds),
        "measured_rounds": int(measured_rounds),
        "scope": "query_adapter_plus_faiss_ivf_search_plus_exact_candidate_rerank",
    }


def paired_bootstrap_difference(
    proposed: Sequence[float],
    baseline: Sequence[float],
    repetitions: int,
    alpha: float,
    seed: int,
) -> dict[str, float]:
    proposed_array = np.asarray(proposed, dtype=np.float64)
    baseline_array = np.asarray(baseline, dtype=np.float64)
    if proposed_array.shape != baseline_array.shape or proposed_array.ndim != 1:
        raise ValueError("Paired bootstrap arrays must be aligned one-dimensional data")
    differences = proposed_array - baseline_array
    rng = np.random.default_rng(seed)
    bootstrap_means = np.empty(repetitions, dtype=np.float64)
    for repetition in range(repetitions):
        sample = rng.integers(0, len(differences), size=len(differences))
        bootstrap_means[repetition] = float(np.mean(differences[sample]))
    return {
        "mean_absolute_difference": float(np.mean(differences)),
        "ci_lower": float(np.quantile(bootstrap_means, alpha / 2.0)),
        "ci_upper": float(np.quantile(bootstrap_means, 1.0 - alpha / 2.0)),
        "repetitions": int(repetitions),
        "alpha": float(alpha),
    }


def metric_values(result: Mapping[str, Any], metric: str) -> list[float]:
    return [float(row[metric]) for row in result["per_user"]]


def without_per_user(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "per_user"}


def aggregate_seed_results(
    seed_results: Mapping[int, Mapping[str, Any]]
) -> dict[str, Any]:
    if not seed_results:
        raise ValueError("Cannot aggregate an empty seed result set")
    ordered_seeds = sorted(seed_results)
    reference_rows = seed_results[ordered_seeds[0]]["per_user"]
    aggregate_rows: list[dict[str, Any]] = []
    for row_index, reference in enumerate(reference_rows):
        aligned = [seed_results[seed]["per_user"][row_index] for seed in ordered_seeds]
        if any(
            row["user_id"] != reference["user_id"]
            or row["target_item_index"] != reference["target_item_index"]
            for row in aligned
        ):
            raise IntegrityError("Per-seed user metrics are not aligned")
        intrusions = [
            row["dislike_intrusion_at_10"]
            for row in aligned
            if row["dislike_intrusion_at_10"] is not None
        ]
        aggregate_rows.append(
            {
                "user_id": reference["user_id"],
                "target_item_index": reference["target_item_index"],
                "target_rank": None,
                "target_ranks_by_seed": {
                    str(seed): seed_results[seed]["per_user"][row_index]["target_rank"]
                    for seed in ordered_seeds
                },
                "ndcg_at_10": float(np.mean([row["ndcg_at_10"] for row in aligned])),
                "recall_at_50": float(
                    np.mean([row["recall_at_50"] for row in aligned])
                ),
                "dislike_intrusion_at_10": (
                    None if not intrusions else float(np.mean(intrusions))
                ),
            }
        )
    safety_values = [
        row["dislike_intrusion_at_10"]
        for row in aggregate_rows
        if row["dislike_intrusion_at_10"] is not None
    ]
    return {
        "ndcg_at_10": float(np.mean([row["ndcg_at_10"] for row in aggregate_rows])),
        "recall_at_50": float(
            np.mean([row["recall_at_50"] for row in aggregate_rows])
        ),
        "dislike_intrusion_at_10": (
            None if not safety_values else float(np.mean(safety_values))
        ),
        "users": len(aggregate_rows),
        "users_with_known_dislikes": len(safety_values),
        "per_seed": {
            str(seed): without_per_user(seed_results[seed]) for seed in ordered_seeds
        },
        "per_user": aggregate_rows,
    }


def benchmark_abba_latency(
    corpus: EvalCorpus,
    ripple_adapter_state: Mapping[str, Any],
    item_vectors: np.ndarray,
    index: Any,
    search_k: int,
    nprobe: int,
    warmup_rounds: int,
    measured_rounds: int,
) -> dict[str, Any]:
    def serve_one(row: int, state: Mapping[str, Any] | None) -> None:
        query = adapt_queries_numpy(corpus.queries[row : row + 1], state)[0]
        ranking = exact_reranked_candidates(query, item_vectors, index, search_k)
        _ = filter_ranking(ranking, corpus.quality_blocked[row])[:10]

    index.nprobe = int(nprobe)
    for _ in range(warmup_rounds):
        for row in range(len(corpus.user_ids)):
            serve_one(row, None)
            serve_one(row, ripple_adapter_state)
    samples: dict[str, list[float]] = {"frozen": [], "ripple": []}
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for repetition in range(measured_rounds):
            schedule = (
                ("frozen", "ripple", "ripple", "frozen")
                if repetition % 2 == 0
                else ("ripple", "frozen", "frozen", "ripple")
            )
            for row in range(len(corpus.user_ids)):
                for method in schedule:
                    state = None if method == "frozen" else ripple_adapter_state
                    start_ns = time.perf_counter_ns()
                    serve_one(row, state)
                    samples[method].append(
                        float((time.perf_counter_ns() - start_ns) / 1_000_000.0)
                    )
    finally:
        if gc_was_enabled:
            gc.enable()

    def summarize(values: Sequence[float]) -> dict[str, Any]:
        if not values:
            raise IntegrityError("ABBA latency benchmark produced no samples")
        return {
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "p99_ms": float(np.percentile(values, 99)),
            "mean_ms": float(np.mean(values)),
            "sample_count": len(values),
        }

    frozen = summarize(samples["frozen"])
    ripple = summarize(samples["ripple"])
    return {
        "frozen": frozen,
        "ripple": ripple,
        "ripple_to_frozen_p95_ratio": float(ripple["p95_ms"] / frozen["p95_ms"]),
        "warmup_full_passes": int(warmup_rounds),
        "measured_repetitions_per_query": int(measured_rounds),
        "schedule": "ABBA with alternating BAAB repetition",
        "nprobe": int(nprobe),
        "scope": "adapter_or_identity_plus_one_ivf_search_plus_filter_plus_exact_rerank_plus_top10",
    }


def relative_gain(value: float, baseline: float) -> float | None:
    if baseline <= 0.0:
        return None
    return float((value - baseline) / baseline)


def evaluate_promise_gate(
    methods: Mapping[str, Mapping[str, Any]],
    per_seed_methods: Mapping[int, Mapping[str, Mapping[str, Any]]],
    latency_by_seed: Mapping[int, Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
    gate_config: Mapping[str, Any],
    immutable_hashes: bool,
    ann_boundary_source_rate: float | None,
    minimum_boundary_source_rate: float,
    minimum_dislike_audit_users: int,
    asynchronous_error_ledger_empty: bool,
) -> dict[str, Any]:
    frozen = methods["frozen"]
    random_adapter = methods["random_adapter"]
    exact_hard = methods["exact_hard_adapter"]
    ripple = methods["ripple"]
    bpr = methods["bpr_mf"]
    gain_frozen = relative_gain(ripple["ndcg_at_10"], frozen["ndcg_at_10"])
    gain_random = relative_gain(
        ripple["ndcg_at_10"], random_adapter["ndcg_at_10"]
    )
    gain_exact = relative_gain(ripple["ndcg_at_10"], exact_hard["ndcg_at_10"])
    frozen_intrusion = frozen["dislike_intrusion_at_10"]
    ripple_intrusion = ripple["dislike_intrusion_at_10"]
    bpr_fraction = (
        None
        if bpr["ndcg_at_10"] <= 0.0
        else float(ripple["ndcg_at_10"] / bpr["ndcg_at_10"])
    )
    latency_ratios = {
        str(seed): float(result["ripple_to_frozen_p95_ratio"])
        for seed, result in latency_by_seed.items()
    }
    seeds_beating_frozen = sum(
        per_seed_methods[seed]["ripple"]["ndcg_at_10"] > frozen["ndcg_at_10"]
        for seed in per_seed_methods
    )
    core_gates = {
        "G1_quality_over_frozen_and_positive_ci": bool(
            gain_frozen is not None
            and gain_frozen
            >= float(gate_config["minimum_relative_ndcg_gain_over_frozen"])
            and bootstrap["ripple_minus_frozen_ndcg_at_10"]["ci_lower"] > 0.0
        ),
        "G2_mechanism_over_random_and_exact": bool(
            gain_random is not None
            and gain_random
            >= float(
                gate_config["minimum_relative_ndcg_gain_over_random_adapter"]
            )
            and gain_exact is not None
            and gain_exact
            >= float(
                gate_config["minimum_relative_ndcg_gain_over_exact_hard_adapter"]
            )
        ),
        "G3_bpr_noninferiority": bool(
            bpr_fraction is not None
            and bpr_fraction >= float(gate_config["minimum_fraction_of_bpr_ndcg"])
        ),
        "G4_recall_not_lower_than_frozen": bool(
            ripple["recall_at_50"] - frozen["recall_at_50"]
            >= float(gate_config["minimum_absolute_recall50_change"])
        ),
        "G5_dislike_intrusion_not_worse": bool(
            frozen_intrusion is not None
            and ripple_intrusion is not None
            and ripple_intrusion - frozen_intrusion
            <= float(
                gate_config["maximum_absolute_dislike_intrusion10_change"]
            )
        ),
        "G6_every_seed_p95_latency_within_budget": bool(
            len(latency_ratios) == 3
            and all(
                ratio <= float(gate_config["maximum_p95_latency_ratio"])
                for ratio in latency_ratios.values()
            )
        ),
        "G7_item_and_index_hashes_unchanged": bool(immutable_hashes),
        "G8_seed_stability": bool(
            seeds_beating_frozen
            >= int(gate_config["minimum_ripple_seeds_beating_frozen"])
        ),
    }
    required_methods = ("frozen", "random_adapter", "exact_hard_adapter", "ripple", "bpr_mf")
    metrics_complete = True
    for method in required_methods:
        for metric in ("ndcg_at_10", "recall_at_50", "dislike_intrusion_at_10"):
            value = methods[method].get(metric)
            if value is None or not math.isfinite(float(value)):
                metrics_complete = False
    for seed_results in per_seed_methods.values():
        for method in required_methods:
            for metric in ("ndcg_at_10", "recall_at_50", "dislike_intrusion_at_10"):
                value = seed_results[method].get(metric)
                if value is None or not math.isfinite(float(value)):
                    metrics_complete = False
    if any(not math.isfinite(ratio) for ratio in latency_ratios.values()):
        metrics_complete = False
    fail_closed_checks = {
        "all_required_metrics_finite": metrics_complete,
        "asynchronous_error_ledger_empty": bool(asynchronous_error_ledger_empty),
        "ann_boundary_source_rate_sufficient": bool(
            ann_boundary_source_rate is not None
            and math.isfinite(ann_boundary_source_rate)
            and ann_boundary_source_rate >= minimum_boundary_source_rate
        ),
        "future_dislike_audit_cohort_sufficient": bool(
            int(ripple["users_with_known_dislikes"]) >= minimum_dislike_audit_users
            and int(frozen["users_with_known_dislikes"]) >= minimum_dislike_audit_users
        ),
        "all_three_seed_results_present": len(per_seed_methods) == 3,
    }
    passed = all(core_gates.values()) and all(fail_closed_checks.values())
    return {
        "passed": passed,
        "core_eight_gates": core_gates,
        "fail_closed_checks": fail_closed_checks,
        "relative_ndcg_gain_over_frozen": gain_frozen,
        "relative_ndcg_gain_over_random_adapter": gain_random,
        "relative_ndcg_gain_over_exact_hard_adapter": gain_exact,
        "ripple_fraction_of_bpr_ndcg": bpr_fraction,
        "per_seed_p95_latency_ratios": latency_ratios,
        "ripple_seeds_beating_frozen": int(seeds_beating_frozen),
        "ann_boundary_source_rate": ann_boundary_source_rate,
        "future_dislike_audit_users": int(ripple["users_with_known_dislikes"]),
        "mandatory_action_if_failed": (
            "Proceed to Phase 5 with evidence-limited claims."
            if passed
            else "KILL RIPPLE and return to Phase 1; Phase 5 is forbidden."
        ),
    }


def per_user_csv(methods: Mapping[str, Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "method",
            "user_id",
            "target_item_index",
            "target_rank",
            "ndcg_at_10",
            "recall_at_50",
            "dislike_intrusion_at_10",
        ]
    )
    for method, result in methods.items():
        for row in result["per_user"]:
            writer.writerow(
                [
                    method,
                    row["user_id"],
                    row["target_item_index"],
                    "" if row["target_rank"] is None else row["target_rank"],
                    f"{row['ndcg_at_10']:.17g}",
                    f"{row['recall_at_50']:.17g}",
                    (
                        ""
                        if row["dislike_intrusion_at_10"] is None
                        else f"{row['dislike_intrusion_at_10']:.17g}"
                    ),
                ]
            )
    return output.getvalue().encode("utf-8")


def collect_artifact_hashes(run_directory: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for path in sorted(run_directory.rglob("*")):
        if path.is_file() and ".tmp." not in path.name:
            artifacts[path.relative_to(run_directory).as_posix()] = sha256_file(path)
    return artifacts


def execute(args: argparse.Namespace) -> Path:
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    source_path = Path(__file__).resolve()
    runner_sha = sha256_file(source_path)
    config_sha = sha256_bytes(canonical_json_bytes(config))
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
    deterministic_setup(int(config["seed"]))

    experiments_root = args.experiments_root.resolve()
    runs_root = experiments_root / "ripple_poc_runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    lock = RunnerLock(experiments_root / "ripple_poc.runner.lock", protocol_sha)
    run_directory: Path | None = None
    error_ledger: Path | None = None
    lock.acquire()
    try:
        if args.run_id:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", args.run_id):
                raise ValueError("--run-id contains unsupported characters")
            run_id = args.run_id
        else:
            run_id = (
                f"ripple_{protocol_short}_"
                f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_"
                f"pid{os.getpid()}_{uuid.uuid4().hex[:8]}"
            )
        run_directory = runs_root / run_id
        run_directory.mkdir(parents=False, exist_ok=False)
        error_ledger = (
            run_directory / f"async_errors_{protocol_short}_seq000.jsonl"
        )
        with error_ledger.open("xb") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        install_async_exception_hooks(error_ledger)
        event_log = run_directory / f"events_{protocol_short}_seq000.jsonl"
        with event_log.open("xb") as handle:
            handle.flush()
            os.fsync(handle.fileno())

        def log_event(kind: str, **fields: Any) -> None:
            append_json_line(
                event_log,
                {"kind": kind, "utc": utc_now(), "pid": os.getpid(), **fields},
            )

        print(f"RUN_DIRECTORY={run_directory}", flush=True)
        log_event("run_started", protocol_sha256=protocol_sha)
        environment_path = (
            run_directory / f"environment_{protocol_short}_seq000.json"
        )
        publish_json_no_overwrite(
            environment_path,
            {
                "schema": "ripple-environment-v1",
                "python": sys.version,
                "python_executable": sys.executable,
                "platform": sys.platform,
                "pid": os.getpid(),
                "thread_environment": THREAD_ENVIRONMENT,
                "torch_version": torch.__version__,
                "torch_num_threads": torch.get_num_threads(),
                "torch_num_interop_threads": torch.get_num_interop_threads(),
                "cuda_available": torch.cuda.is_available(),
                "runner_sha256": runner_sha,
                "config_sha256": config_sha,
                "protocol_sha256": protocol_sha,
            },
        )
        config_snapshot = (
            run_directory / f"effective_config_{protocol_short}_seq000.json"
        )
        publish_json_no_overwrite(config_snapshot, config)

        input_directory = run_directory / "inputs"
        input_directory.mkdir(parents=False, exist_ok=False)
        zip_path = input_directory / f"ml-100k_{protocol_short}_seq000.zip"
        dataset_sha = acquire_input_zip(
            zip_path,
            str(config["dataset"]["url"]),
            args.data_zip.resolve() if args.data_zip else None,
            config["dataset"].get("expected_sha256"),
        )
        execution_sha = sha256_bytes(
            canonical_json_bytes(
                {
                    "protocol_sha256": protocol_sha,
                    "dataset_sha256": dataset_sha,
                }
            )
        )
        execution_short = execution_sha[:16]
        data_path, item_path = extract_movielens_files(
            zip_path, input_directory / "ml-100k"
        )
        log_event(
            "dataset_ready",
            dataset_sha256=dataset_sha,
            execution_fingerprint=execution_sha,
        )

        item_ids, metadata = load_item_metadata(item_path)
        item_id_to_index = {item_id: row for row, item_id in enumerate(item_ids)}
        interactions = load_interactions(data_path, item_id_to_index)
        splits = chronological_user_splits(interactions, config["dataset"])
        split_path = run_directory / f"split_manifest_{execution_short}_seq001.json"
        publish_json_no_overwrite(
            split_path,
            {
                "schema": "ripple-chronological-split-v1",
                "rule": (
                    "Per eligible user, events are split into a strict 80% train, "
                    "10% validation, and 10% untouched test window. The first "
                    "positive in each held-out window is its relevance target; "
                    "future low ratings in that window form the dislike audit."
                ),
                "train_fraction": config["dataset"]["train_fraction"],
                "validation_fraction": config["dataset"]["validation_fraction"],
                "eligible_users": len(splits),
                "catalog_items": len(item_ids),
                "interactions": len(interactions),
                "positive_rating_min": config["dataset"]["positive_rating_min"],
                "dislike_rating_max": config["dataset"]["dislike_rating_max"],
                "test_not_used_for_tuning": True,
                "user_ids": [split.user_id for split in splits],
                "validation_timestamps": {
                    str(split.user_id): split.validation.timestamp for split in splits
                },
                "test_timestamps": {
                    str(split.user_id): split.test.timestamp for split in splits
                },
            },
        )
        metadata_path = (
            run_directory / f"item_metadata_{execution_short}_seq001.jsonl"
        )
        metadata_payload = b"".join(
            canonical_json_bytes(
                {"item_id": item_id, "item_index": row, "text": metadata[row]}
            )
            for row, item_id in enumerate(item_ids)
        )
        publish_bytes_no_overwrite(metadata_path, metadata_payload)

        log_event("embedding_started", model=config["embedding"]["model_name"])
        item_vectors = encode_item_metadata(metadata, config["embedding"])
        item_vector_path = (
            run_directory / f"item_vectors_{execution_short}_seq001.npy"
        )
        save_numpy_no_overwrite(item_vector_path, item_vectors)
        item_file_sha_before = sha256_file(item_vector_path)
        item_memory_sha_before = sha256_bytes(item_vectors.tobytes(order="C"))
        item_vectors.flags.writeable = False

        faiss, index = build_faiss_index(
            item_vectors, config["index"], int(config["seed"])
        )
        index_bytes_before = np.asarray(
            faiss.serialize_index(index), dtype=np.uint8
        ).tobytes()
        index_path = run_directory / f"faiss_ivf_{execution_short}_seq001.index"
        publish_bytes_no_overwrite(index_path, index_bytes_before)
        index_sha_before = sha256_file(index_path)
        log_event(
            "frozen_catalog_ready",
            item_vectors_sha256=item_file_sha_before,
            faiss_index_sha256=index_sha_before,
        )

        full_train_corpus = build_train_corpus(
            splits, item_vectors, config["dataset"]
        )
        train_corpus = deterministic_subsample_train_corpus(
            full_train_corpus,
            int(config["adapter"]["maximum_training_pairs"]),
            int(config["seed"]),
        )
        validation_corpus = build_eval_corpus(
            splits, item_vectors, config["dataset"], "validation"
        )
        test_corpus = build_eval_corpus(
            splits, item_vectors, config["dataset"], "test"
        )
        corpus_manifest = (
            run_directory / f"preference_corpus_{execution_short}_seq001.json"
        )
        publish_json_no_overwrite(
            corpus_manifest,
            {
                "training_pairs_before_registered_poc_cap": int(
                    len(full_train_corpus.chosen_items)
                ),
                "training_pairs": int(len(train_corpus.chosen_items)),
                "pairs_with_explicit_dislikes": int(
                    sum(bool(values) for values in train_corpus.explicit_dislikes)
                ),
                "validation_users": int(len(validation_corpus.user_ids)),
                "test_users": int(len(test_corpus.user_ids)),
                "implicit_negative_semantics": (
                    "An unseen FAISS-boundary neighbor is a hard confusion, not an "
                    "asserted dislike. Explicit ratings <= dislike_rating_max are "
                    "preferred rejected items when available."
                ),
            },
        )

        seeds = [int(value) for value in config["replicate_seeds"]]
        index.nprobe = int(config["index"]["nprobe"])
        frozen_validation = evaluate_vector_method(
            validation_corpus,
            None,
            item_vectors,
            index,
            int(config["index"]["evaluation_search_k"]),
            int(config["evaluation"]["ndcg_k"]),
            int(config["evaluation"]["recall_k"]),
        )
        publish_json_no_overwrite(
            run_directory / f"validation_frozen_{execution_short}_seq001.json",
            without_per_user(frozen_validation),
        )
        trained_adapters: dict[int, dict[str, LowRankQueryAdapter]] = {}
        trained_bpr: dict[int, tuple[BPRMatrixFactorization, dict[int, int]]] = {}
        training_diagnostics: dict[str, Any] = {
            "frozen_validation": without_per_user(frozen_validation),
            "by_seed": {},
        }
        checkpoint_manifest: dict[str, Any] = {}
        boundary_intended_total = 0
        boundary_genuine_total = 0
        parameter_count: int | None = None
        if not bool(config["bpr"]["enabled"]):
            raise IntegrityError("The registered eight-part gate requires BPR-MF")
        for seed in seeds:
            deterministic_setup(seed)
            initial_adapter = LowRankQueryAdapter(
                dimension=item_vectors.shape[1],
                rank=int(config["adapter"]["rank"]),
                residual_scale=float(config["adapter"]["residual_scale"]),
            )
            seed_parameter_count = sum(
                parameter.numel() for parameter in initial_adapter.parameters()
            )
            if parameter_count is None:
                parameter_count = seed_parameter_count
            elif parameter_count != seed_parameter_count:
                raise IntegrityError("Adapter parameter count changed across seeds")
            initial_state = {
                key: value.detach().clone()
                for key, value in initial_adapter.state_dict().items()
            }
            trained_adapters[seed] = {}
            training_diagnostics["by_seed"][str(seed)] = {}
            checkpoint_manifest[str(seed)] = {}
            for variant in ("random", "exact_hard", "index_boundary"):
                log_event("adapter_training_started", variant=variant, seed=seed)
                adapter, traces, checkpoint, diagnostics = train_adapter_variant(
                    variant,
                    initial_state,
                    train_corpus,
                    validation_corpus,
                    item_vectors,
                    index,
                    config,
                    seed,
                    run_directory,
                    execution_short,
                    error_ledger,
                )
                trained_adapters[seed][variant] = adapter
                training_diagnostics["by_seed"][str(seed)][variant] = {
                    "trace": traces,
                    "selection": diagnostics,
                }
                checkpoint_manifest[str(seed)][variant] = checkpoint.name
                if variant == "index_boundary":
                    boundary_intended_total += int(
                        diagnostics["boundary_intended_total"]
                    )
                    boundary_genuine_total += int(
                        diagnostics["boundary_genuine_total"]
                    )
                log_event("adapter_training_finished", variant=variant, seed=seed)
            log_event("bpr_training_started", seed=seed)
            bpr_model, user_to_row, bpr_checkpoint = train_bpr_baseline(
                splits,
                len(item_ids),
                config["dataset"],
                config["bpr"],
                seed,
                run_directory,
                execution_short,
            )
            trained_bpr[seed] = (bpr_model, user_to_row)
            checkpoint_manifest[str(seed)]["bpr_mf"] = bpr_checkpoint.name
            log_event("bpr_training_finished", seed=seed)

        item_file_sha_before_test = sha256_file(item_vector_path)
        item_memory_sha_before_test = sha256_bytes(item_vectors.tobytes(order="C"))
        index_sha_before_test = sha256_file(index_path)
        log_event(
            "immutable_artifacts_verified_before_test",
            item_sha256=item_file_sha_before_test,
            index_sha256=index_sha_before_test,
        )

        index.nprobe = int(config["index"]["nprobe"])
        frozen_test = evaluate_vector_method(
            test_corpus,
            None,
            item_vectors,
            index,
            int(config["index"]["evaluation_search_k"]),
            int(config["evaluation"]["ndcg_k"]),
            int(config["evaluation"]["recall_k"]),
        )
        per_seed_methods: dict[int, dict[str, dict[str, Any]]] = {}
        random_seed_results: dict[int, dict[str, Any]] = {}
        exact_seed_results: dict[int, dict[str, Any]] = {}
        ripple_seed_results: dict[int, dict[str, Any]] = {}
        bpr_seed_results: dict[int, dict[str, Any]] = {}
        for seed in seeds:
            index.nprobe = int(config["index"]["nprobe"])
            random_result = evaluate_vector_method(
                test_corpus,
                export_adapter(trained_adapters[seed]["random"]),
                item_vectors,
                index,
                int(config["index"]["evaluation_search_k"]),
                int(config["evaluation"]["ndcg_k"]),
                int(config["evaluation"]["recall_k"]),
            )
            exact_result = evaluate_vector_method(
                test_corpus,
                export_adapter(trained_adapters[seed]["exact_hard"]),
                item_vectors,
                index,
                int(config["index"]["evaluation_search_k"]),
                int(config["evaluation"]["ndcg_k"]),
                int(config["evaluation"]["recall_k"]),
            )
            ripple_result = evaluate_vector_method(
                test_corpus,
                export_adapter(trained_adapters[seed]["index_boundary"]),
                item_vectors,
                index,
                int(config["index"]["evaluation_search_k"]),
                int(config["evaluation"]["ndcg_k"]),
                int(config["evaluation"]["recall_k"]),
            )
            bpr_model, user_to_row = trained_bpr[seed]
            bpr_result = evaluate_bpr(
                bpr_model,
                user_to_row,
                test_corpus,
                int(config["evaluation"]["ndcg_k"]),
                int(config["evaluation"]["recall_k"]),
            )
            random_seed_results[seed] = random_result
            exact_seed_results[seed] = exact_result
            ripple_seed_results[seed] = ripple_result
            bpr_seed_results[seed] = bpr_result
            per_seed_methods[seed] = {
                "frozen": without_per_user(frozen_test),
                "random_adapter": without_per_user(random_result),
                "exact_hard_adapter": without_per_user(exact_result),
                "ripple": without_per_user(ripple_result),
                "bpr_mf": without_per_user(bpr_result),
            }

        methods: dict[str, dict[str, Any]] = {
            "frozen": frozen_test,
            "random_adapter": aggregate_seed_results(random_seed_results),
            "exact_hard_adapter": aggregate_seed_results(exact_seed_results),
            "ripple": aggregate_seed_results(ripple_seed_results),
            "bpr_mf": aggregate_seed_results(bpr_seed_results),
        }
        latency_by_seed: dict[int, dict[str, Any]] = {}
        for seed in seeds:
            latency_by_seed[seed] = benchmark_abba_latency(
                test_corpus,
                export_adapter(trained_adapters[seed]["index_boundary"]),
                item_vectors,
                index,
                int(config["index"]["evaluation_search_k"]),
                int(config["index"]["nprobe"]),
                int(config["evaluation"]["latency_warmup_rounds"]),
                int(config["evaluation"]["latency_measured_rounds"]),
            )

        bootstrap_seed = int(config["evaluation"]["bootstrap_seed"])
        bootstrap = {
            "ripple_minus_frozen_ndcg_at_10": paired_bootstrap_difference(
                metric_values(methods["ripple"], "ndcg_at_10"),
                metric_values(methods["frozen"], "ndcg_at_10"),
                int(config["evaluation"]["bootstrap_repetitions"]),
                float(config["evaluation"]["bootstrap_alpha"]),
                bootstrap_seed,
            ),
            "ripple_minus_random_adapter_ndcg_at_10": paired_bootstrap_difference(
                metric_values(methods["ripple"], "ndcg_at_10"),
                metric_values(methods["random_adapter"], "ndcg_at_10"),
                int(config["evaluation"]["bootstrap_repetitions"]),
                float(config["evaluation"]["bootstrap_alpha"]),
                bootstrap_seed + 1,
            ),
            "ripple_minus_exact_hard_adapter_ndcg_at_10": paired_bootstrap_difference(
                metric_values(methods["ripple"], "ndcg_at_10"),
                metric_values(methods["exact_hard_adapter"], "ndcg_at_10"),
                int(config["evaluation"]["bootstrap_repetitions"]),
                float(config["evaluation"]["bootstrap_alpha"]),
                bootstrap_seed + 2,
            ),
        }

        item_file_sha_after_latency = sha256_file(item_vector_path)
        item_memory_sha_after_latency = sha256_bytes(
            item_vectors.tobytes(order="C")
        )
        # Hash the immutable saved artifact. Runtime nprobe changes are never
        # reserialized and therefore cannot manufacture a false mismatch.
        index_sha_after_latency = sha256_file(index_path)
        immutable_hashes = bool(
            item_file_sha_before
            == item_file_sha_before_test
            == item_file_sha_after_latency
            and item_memory_sha_before
            == item_memory_sha_before_test
            == item_memory_sha_after_latency
            and index_sha_before == index_sha_before_test == index_sha_after_latency
        )
        ann_boundary_source_rate = (
            None
            if boundary_intended_total == 0
            else float(boundary_genuine_total / boundary_intended_total)
        )
        gate = evaluate_promise_gate(
            {name: without_per_user(result) for name, result in methods.items()},
            per_seed_methods,
            latency_by_seed,
            bootstrap,
            config["promise_gate"],
            immutable_hashes,
            ann_boundary_source_rate,
            float(config["evaluation"]["minimum_ann_boundary_source_rate"]),
            int(config["evaluation"]["minimum_dislike_audit_users"]),
            error_ledger.stat().st_size == 0,
        )

        per_user_path = run_directory / f"per_user_metrics_{execution_short}_seq001.csv"
        publish_bytes_no_overwrite(per_user_path, per_user_csv(methods))
        summary_methods = {
            name: without_per_user(result) for name, result in methods.items()
        }
        result = {
            "schema": "ripple-poc-result-v1",
            "status": "COMPLETE_RUNNER_RESULT",
            "protocol_name": config["protocol_name"],
            "protocol_sha256": protocol_sha,
            "execution_fingerprint_sha256": execution_sha,
            "runner_sha256": runner_sha,
            "config_sha256": config_sha,
            "dataset_sha256": dataset_sha,
            "created_utc": utc_now(),
            "run_directory": str(run_directory),
            "scientific_protocol": {
                "split": "chronological per-user 80/10/10 windows",
                "test_used_for_tuning": False,
                "adapter_epoch_selection": "fixed preregistered final epoch",
                "replicate_seeds": seeds,
                "item_encoder": config["embedding"]["model_name"],
                "item_vectors_normalized": True,
                "query": "normalized positive-history item-vector centroid",
                "retrieval": "FAISS IndexIVFFlat inner product",
                "alignment_loss": (
                    "SimPO-derived reference-free weighted margin objective; "
                    "for one chosen/rejected item it is algebraically a "
                    "target-margin-shifted BPR/RankNet loss plus query anchor"
                ),
                "matched_adapter_parameter_count": int(parameter_count),
                "random_exact_and_ripple_initialization_identical_within_seed": True,
                "random_exact_and_ripple_optimizer_and_epochs_identical": True,
                "quality_evaluation": (
                    "Whole catalog is searched through the registered IVF index; "
                    "returned candidates are exactly dot-product reranked; all "
                    "historical interactions are suppressed."
                ),
                "dislike_intrusion_evaluation": (
                    "Low-rated items in the untouched future window define the "
                    "safety cohort; earlier interactions are commonly suppressed."
                ),
            },
            "data_counts": {
                "catalog_items": len(item_ids),
                "interactions": len(interactions),
                "eligible_users": len(splits),
                "training_preference_pairs": int(len(train_corpus.chosen_items)),
            },
            "methods": summary_methods,
            "per_seed_methods": {
                str(seed): per_seed_methods[seed] for seed in seeds
            },
            "latency_by_seed": {
                str(seed): latency_by_seed[seed] for seed in seeds
            },
            "paired_bootstrap": bootstrap,
            "ann_boundary_pair_source": {
                "intended_confusion_pairs": boundary_intended_total,
                "genuine_ivf_boundary_pairs": boundary_genuine_total,
                "source_rate": ann_boundary_source_rate,
            },
            "immutability": {
                "item_vector_file_sha256_before": item_file_sha_before,
                "item_vector_file_sha256_before_test": item_file_sha_before_test,
                "item_vector_file_sha256_after_latency": item_file_sha_after_latency,
                "item_vector_memory_sha256_before": item_memory_sha_before,
                "item_vector_memory_sha256_before_test": item_memory_sha_before_test,
                "item_vector_memory_sha256_after_latency": item_memory_sha_after_latency,
                "faiss_index_sha256_before": index_sha_before,
                "faiss_index_sha256_before_test": index_sha_before_test,
                "faiss_index_sha256_after_latency": index_sha_after_latency,
                "saved_index_was_not_reserialized_after_runtime_nprobe_changes": True,
                "unchanged": immutable_hashes,
            },
            "promise_gate": gate,
            "training_diagnostics": training_diagnostics,
            "checkpoints": checkpoint_manifest,
            "per_user_metrics_file": per_user_path.name,
            "completion_semantics": (
                "This result becomes a completed outcome only after the process "
                "exits, the external launcher confirms lock release, all marker "
                "hashes verify, and persistent stdout/stderr are bound."
            ),
        }
        result_path = run_directory / f"result_{execution_short}_seq001.json"
        publish_json_no_overwrite(result_path, result)
        log_event(
            "result_published",
            result_file=result_path.name,
            promise_gate_passed=gate["passed"],
        )
        if error_ledger.stat().st_size != 0:
            raise IntegrityError(
                "Asynchronous-error ledger is nonempty; refusing completion marker"
            )
        log_event("runner_artifacts_finalized")
        artifact_hashes = collect_artifact_hashes(run_directory)
        completion_marker = run_directory / (
            f"RUNNER_COMPLETE_{execution_short}_seq001.json"
        )
        publish_json_no_overwrite(
            completion_marker,
            {
                "schema": "ripple-runner-completion-candidate-v1",
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
                f"synchronous_error_{protocol_short}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid.uuid4().hex}.json"
            )
            try:
                publish_json_no_overwrite(
                    error_path,
                    {
                        "schema": "ripple-synchronous-error-v1",
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
        description="Run the preregistered RIPPLE MovieLens-100K proof of concept."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "src" / "configs" / "ripple_poc_ml100k.json",
        help="Immutable JSON protocol configuration.",
    )
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=project_root / "experiments",
        help="Root containing the runner lock and unique append-only run dirs.",
    )
    parser.add_argument(
        "--data-zip",
        type=Path,
        default=None,
        help="Optional predownloaded ml-100k.zip; it is copied into the run dir.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional unique run-directory name for a hash-binding launcher.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    completion_marker = execute(args)
    if not completion_marker.exists():
        raise IntegrityError("Runner returned without its completion candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
